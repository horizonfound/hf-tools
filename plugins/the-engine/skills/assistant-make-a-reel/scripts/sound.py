#!/usr/bin/env python3
"""The Assistant, by Horizon Found. A song's length, and its sound as plain samples, on a Mac or a PC.

    python3 sound.py <song> [<song> ...]            how long each is, and how this computer can hear it
    python3 sound.py --extract <video> <out.m4a>     the sound of a video or screen recording, as a song file

How long a song is: read from the file itself in plain Python, nothing installed, the same on both computers:
M4A / MP4 / MOV, MP3 (its Xing or VBRI header, else its bit rate and size, else every frame counted), WAV,
AIFF, FLAC and raw AAC. It goes by what is inside the file, never by its name: CapCut's library songs are M4A
files with a .mp3 name.

Hearing a song (decode), first that works:
  1. the Mac's own afconvert, exactly as the reel always did;
  2. ffmpeg, if this computer happens to have it;
  3. the ffmpeg that comes inside the imageio-ffmpeg add-on, if that is installed;
  4. a WAV or AIFF file read in plain Python (nothing installed, both computers);
  5. on a PC, Windows' own Media Foundation (what Windows plays music with), through ctypes.
Every route only reads the song. A wrongly named song is given its right name as a link (Mac) or a copy (PC)
in a temporary folder; the song itself is never renamed or changed.

To try the other routes on a Mac: ASSISTANT_NO_AFCONVERT=1 skips afconvert, ASSISTANT_NO_FFMPEG=1 skips both
ffmpegs (then WAV and AIFF are read in plain Python and anything else says so plainly).

Nothing here has run on a real PC (Nov 6, 2026). The Media Foundation code is written from Microsoft's
documentation (Tutorial: Decoding Audio; the IMFSourceReader, IMFAttributes, IMFSample and IMFMediaBuffer
method orders in mfreadwrite.h and mfobjects.h) and is unproven; any failure there comes back as plain
words, never a crash and never a guess.
"""
import array
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

WINDOWS = os.name == "nt"
LONGEST_SONG = 15 * 60          # a decode stops reading after this many seconds; a beat needs far less
LONGEST_VIDEO = 60 * 60         # the most sound pulled out of one video on a PC with nothing installed


# ---------------------------------------------------------------- what kind of file it really is

def _id3_end(head):
    """Where an ID3v2 tag at the very start ends (0 if there is none)."""
    if len(head) >= 10 and head[:3] == b"ID3":
        size = ((head[6] & 0x7F) << 21) | ((head[7] & 0x7F) << 14) | ((head[8] & 0x7F) << 7) | (head[9] & 0x7F)
        return 10 + size + (10 if head[5] & 0x10 else 0)
    return 0


def _is_adts(b, p=0):
    """An AAC frame header (sync 0xFFF, layer 00) at p."""
    return len(b) >= p + 2 and b[p] == 0xFF and (b[p + 1] & 0xF6) == 0xF0


def _is_mpa(b, p=0):
    """An MPEG audio (MP3) frame sync at p: eleven set bits and a layer that is not 00."""
    return len(b) >= p + 2 and b[p] == 0xFF and (b[p + 1] & 0xE0) == 0xE0 and (b[p + 1] >> 1) & 3 != 0


def real_kind(path):
    """The file ending that matches what is inside, from its first bytes, or None.
    CapCut's library songs are saved as M4A with a .mp3 name, and some tools go by the name, so they cannot
    open them until they are told the real kind."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
            skip = _id3_end(head)
            after = head
            if skip:
                f.seek(skip)
                after = f.read(16)
    except OSError:
        return None
    if head[4:8] == b"ftyp":
        return ".m4a"
    if head[:4] in (b"RIFF", b"RF64", b"BW64"):    # RF64 / BW64: the WAV kind for files over 4 GB
        return ".wav"
    if head[:4] == b"FORM":
        return ".aiff"
    if head[:4] == b"fLaC" or after[:4] == b"fLaC":
        return ".flac"
    if skip:                                     # an ID3 tag: what follows decides (almost always MP3)
        return ".aac" if _is_adts(after) else ".mp3"
    if _is_adts(head):
        return ".aac"
    if _is_mpa(head):
        return ".mp3"
    return None


def _wants_alias(path, kind):
    """True when a tool that goes by the name would be misled by this file's name."""
    p = str(path).lower()
    return bool(kind) and not p.endswith(kind) and not (kind == ".aiff" and p.endswith((".aif", ".aifc")))


# ---------------------------------------------------------------- how long it is

def duration(path):
    """The song's length in seconds, read from the file itself, or None when it cannot be told. A measurement
    only, so a damaged or half-downloaded file of any kind gives None (callers then ask afinfo or ffprobe),
    never a crash: Python's own readers raise more kinds of error than they document (on Python 3.9, wave
    raises RuntimeError for a WAV whose chunk names are damaged)."""
    try:
        kind = real_kind(path)
        reader = {".m4a": _mp4_duration, ".mp3": _mp3_duration, ".wav": _wav_duration, ".aiff": _aiff_duration,
                  ".flac": _flac_duration, ".aac": _adts_duration}.get(kind)
        d = reader(str(path)) if reader else None
        return float(d) if d and d > 0 and math.isfinite(d) else None
    except Exception:  # noqa: BLE001  (a length nobody can read is "unknown", never a crash)
        return None


# M4A, MP4, MOV: boxes inside boxes. moov holds the lengths; it may sit after the sound itself.

def _file_boxes(f, start, end):
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        hdr = f.read(8)
        if len(hdr) < 8:
            return
        size, kind = struct.unpack(">I4s", hdr)
        head = 8
        if size == 1:
            big = f.read(8)
            if len(big) < 8:
                return
            size, head = struct.unpack(">Q", big)[0], 16
        elif size == 0:
            size = end - pos
        if size < head or pos + size > end:
            return
        yield kind, pos + head, pos + size
        pos += size


def _boxes(b, start, end):
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack_from(">I4s", b, pos)
        head = 8
        if size == 1:
            if pos + 16 > end:
                return
            size, head = struct.unpack_from(">Q", b, pos + 8)[0], 16
        elif size == 0:
            size = end - pos
        if size < head or pos + size > end:
            return
        yield kind, pos + head, pos + size
        pos += size


def _child(b, s, e, kind):
    return next(((cs, ce) for k, cs, ce in _boxes(b, s, e) if k == kind), None)


def _scale_and_length(b, s):
    """(timescale, duration) of an mvhd or mdhd box; duration None when the file says 'unknown'."""
    if b[s] == 1:
        scale, dur = struct.unpack_from(">IQ", b, s + 20)
        unknown = dur == 0xFFFFFFFFFFFFFFFF
    else:
        scale, dur = struct.unpack_from(">II", b, s + 12)
        unknown = dur == 0xFFFFFFFF
    return scale, (None if unknown else dur)


def _edits(b, s, e):
    """The edit list's entries: (segment duration in the movie's timescale, media time; -1 is a pause)."""
    out = []
    version = b[s]
    n = struct.unpack_from(">I", b, s + 4)[0]
    p = s + 8
    for _ in range(min(n, 1000)):
        if version == 1:
            if p + 20 > e:
                break
            seg, media = struct.unpack_from(">Qq", b, p)
            p += 20
        else:
            if p + 12 > e:
                break
            seg, media = struct.unpack_from(">Ii", b, p)
            p += 12
        out.append((seg, media))
    return out


def _itunes_samples(b):
    """The number of samples really played, from the iTunes gapless note (iTunSMPB), or None. The note is
    text: " 00000000 <encoder delay> <padding> <samples played> ...", in hex. AAC songs made by Apple's tools
    carry it instead of an edit list, and the Mac's own afinfo goes by it."""
    for k, s, e in _boxes(b, 0, len(b)):
        if k != b"udta":
            continue
        meta = _child(b, s, e, b"meta")
        if not meta:
            continue
        ilst = _child(b, meta[0] + 4, meta[1], b"ilst")      # meta is a "full box": 4 bytes before its children
        for k2, s2, e2 in _boxes(b, *ilst) if ilst else []:
            if k2 != b"----":
                continue
            name = _child(b, s2, e2, b"name")
            data = _child(b, s2, e2, b"data")
            if name and data and b[name[0] + 4:name[1]] == b"iTunSMPB":
                words = b[data[0] + 8:data[1]].decode("latin-1").split()
                try:
                    return int(words[3], 16) or None
                except (IndexError, ValueError):
                    return None
    return None


def _fragments_length(f, size, track_id, default_dur):
    """A fragmented file (moov says nothing; each moof says what follows it): the sound track's sample
    durations added up, in its own timescale. Only the small moof boxes are read."""
    total = 0
    for k, s, e in _file_boxes(f, 0, size):
        if k != b"moof" or e - s > 16 * 1024 * 1024:
            continue
        f.seek(s)
        b = f.read(e - s)
        for k2, s2, e2 in _boxes(b, 0, len(b)):
            if k2 != b"traf":
                continue
            tfhd = _child(b, s2, e2, b"tfhd")
            if not tfhd:
                continue
            flags = int.from_bytes(b[tfhd[0] + 1:tfhd[0] + 4], "big")
            if struct.unpack_from(">I", b, tfhd[0] + 4)[0] != track_id:
                continue
            p, dflt = tfhd[0] + 8, default_dur
            p += 8 if flags & 0x01 else 0
            p += 4 if flags & 0x02 else 0
            if flags & 0x08:
                dflt = struct.unpack_from(">I", b, p)[0]
            for k3, s3, e3 in _boxes(b, s2, e2):
                if k3 != b"trun":
                    continue
                tflags = int.from_bytes(b[s3 + 1:s3 + 4], "big")
                count = struct.unpack_from(">I", b, s3 + 4)[0]
                q = s3 + 8 + (4 if tflags & 0x01 else 0) + (4 if tflags & 0x04 else 0)
                if not tflags & 0x100:
                    total += count * (dflt or 0)
                    continue
                step = 4 * sum(1 for bit in (0x100, 0x200, 0x400, 0x800) if tflags & bit)
                for i in range(min(count, (e3 - q) // max(1, step))):
                    total += struct.unpack_from(">I", b, q + i * step)[0]
    return total


def _mp4_duration(path):
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        moov = next(((s, e) for k, s, e in _file_boxes(f, 0, size) if k == b"moov"), None)
        if not moov or moov[1] - moov[0] > 64 * 1024 * 1024:
            return None
        f.seek(moov[0])
        b = f.read(moov[1] - moov[0])
        movie_scale = movie_len = None
        fragments = None                            # a "fragmented" file may say its length in mvex/mehd
        trex = {}                                   # and each track's usual sample duration in mvex/trex
        track = None                                # (media timescale, media length, edit list, id) of the sound
        for k, s, e in _boxes(b, 0, len(b)):
            if k == b"mvhd":
                movie_scale, movie_len = _scale_and_length(b, s)
            elif k == b"mvex":
                for k2, s2, e2 in _boxes(b, s, e):
                    if k2 == b"mehd":
                        fragments = struct.unpack_from(">Q" if b[s2] == 1 else ">I", b, s2 + 4)[0]
                    elif k2 == b"trex":
                        tid, _, dur = struct.unpack_from(">III", b, s2 + 4)
                        trex[tid] = dur
            elif k == b"trak" and track is None:
                mdia = _child(b, s, e, b"mdia")
                hdlr = _child(b, mdia[0], mdia[1], b"hdlr") if mdia else None
                if not hdlr or b[hdlr[0] + 8:hdlr[0] + 12] != b"soun":
                    continue                        # a picture or text track
                mdhd = _child(b, mdia[0], mdia[1], b"mdhd")
                tkhd = _child(b, s, e, b"tkhd")
                tid = struct.unpack_from(">I", b, tkhd[0] + (20 if b[tkhd[0]] == 1 else 12))[0] if tkhd else None
                edts = _child(b, s, e, b"edts")
                elst = _child(b, edts[0], edts[1], b"elst") if edts else None
                scale, length = _scale_and_length(b, mdhd[0]) if mdhd else (None, None)
                track = (scale, length, _edits(b, elst[0], elst[1]) if elst else [], tid)
        if trex or fragments is not None:
            # a fragmented file: the samples in moov (often none) and then every fragment after it
            if fragments and movie_scale:
                return fragments / movie_scale
            if track and track[0] and track[3] is not None:
                summed = (track[1] or 0) + _fragments_length(f, size, track[3], trex.get(track[3]))
                if summed:
                    return summed / track[0]
    if track:
        scale, length, edits, _ = track
        if edits and movie_scale and any(m >= 0 for _, m in edits) and sum(seg for seg, _ in edits):
            # the edit list says how much of the sound is played (an AAC song's first moment is the encoder
            # warming up, and the list leaves it out); its lengths are in the movie's timescale
            return sum(seg for seg, _ in edits) / movie_scale
        played = _itunes_samples(b)
        if played and scale:
            return played / scale                  # the same, said the iTunes way (what afconvert writes)
        if scale and length:
            return length / scale
    if movie_scale and movie_len:
        return movie_len / movie_scale
    if movie_scale and fragments:
        return fragments / movie_scale
    return None


# MP3: frame headers, plus a Xing / Info or VBRI header in the first frame on most files.

_MPA_BITRATES = {  # kbit/s by (MPEG-1?, layer) and index 1-14
    (True, 1): (32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    (True, 2): (32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    (True, 3): (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    (False, 1): (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    (False, 2): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    (False, 3): (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
_MPA_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}  # by version bits


def _mpa_frame(b, p):
    """(frame bytes, samples, sample rate, bit rate, MPEG-1?, mono?) of an MP3 frame header at p, or None."""
    if p + 4 > len(b) or not _is_mpa(b, p):
        return None
    ver = (b[p + 1] >> 3) & 3                    # 3 MPEG-1, 2 MPEG-2, 0 MPEG-2.5, 1 reserved
    layer = 4 - ((b[p + 1] >> 1) & 3)            # 1, 2 or 3
    br_i, sr_i = b[p + 2] >> 4, (b[p + 2] >> 2) & 3
    if ver == 1 or br_i in (0, 15) or sr_i == 3:  # reserved, free-format or bad: not a frame we can measure
        return None
    mpeg1 = ver == 3
    rate = _MPA_RATES[ver][sr_i]
    bitrate = _MPA_BITRATES[(mpeg1, layer)][br_i - 1] * 1000
    pad = (b[p + 2] >> 1) & 1
    if layer == 1:
        size, samples = (12 * bitrate // rate + pad) * 4, 384
    elif layer == 2 or mpeg1:
        size, samples = 144 * bitrate // rate + pad, 1152
    else:
        size, samples = 72 * bitrate // rate + pad, 576
    mono = (b[p + 3] >> 6) == 3
    return size, samples, rate, bitrate, mpeg1, mono


def _first_frame(b, start):
    """The first real frame at or after start: one whose next frame is also a frame of the same kind."""
    p, end = start, min(len(b), start + 256 * 1024)
    while p < end:
        p = b.find(b"\xff", p, end)
        if p < 0:
            return None, None
        h = _mpa_frame(b, p)
        if h:
            nxt = _mpa_frame(b, p + h[0])
            if p + h[0] >= len(b) or (nxt and nxt[2] == h[2] and nxt[4] == h[4]):
                return p, h
        p += 1
    return None, None


def _mp3_duration(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        b = f.read(min(size, 1024 * 1024))         # the start is enough unless every frame has to be counted
    start = _id3_end(b[:10])
    if start > len(b) - 4096 and len(b) < size:     # a big tag (cover art) in front: read past it
        with open(path, "rb") as f:
            b = f.read(min(size, start + 1024 * 1024))
    p, h = _first_frame(b, start)
    if p is None:
        return None
    flen, spf, rate, bitrate, mpeg1, mono = h
    side = (17 if mono else 32) if mpeg1 else (9 if mono else 17)
    x = p + 4 + side
    if b[x:x + 4] in (b"Xing", b"Info"):
        flags = struct.unpack_from(">I", b, x + 4)[0]
        if flags & 1:
            # the number of sound frames after this header frame. Every frame counted, as the Mac's own afinfo
            # does (ffmpeg also leaves out the encoder's few milliseconds of padding: at most about 0.05 s less)
            frames = struct.unpack_from(">I", b, x + 8)[0]
            return frames * spf / rate
    v = p + 4 + 32
    if b[v:v + 4] == b"VBRI":
        frames = struct.unpack_from(">I", b, v + 14)[0]
        return frames * spf / rate
    # no header: walk the first frames; all the same bit rate means constant bit rate, which the size tells
    q, n, rates = p, 0, set()
    while n < 40:
        fh = _mpa_frame(b, q)
        if not fh:
            break
        rates.add(fh[3])
        q += fh[0]
        n += 1
    tail = 0
    if size >= 128:
        with open(path, "rb") as f:
            f.seek(size - 128)
            tail = 128 if f.read(3) == b"TAG" else 0
    if len(rates) == 1 and n >= 2:
        return (size - p - tail) * 8 / bitrate
    # bit rates vary and nothing says how many frames: count every one
    if len(b) < size:
        with open(path, "rb") as f:
            b = f.read(min(size, 64 * 1024 * 1024))
    q, samples = p, 0
    while True:
        fh = _mpa_frame(b, q)
        if not fh:
            break
        samples += fh[1]
        q += fh[0]
    if samples and len(b) < size:                # a very long file: scale up from what was read
        samples = samples * (size - p) / max(1, q - p)
    return samples / rate if samples else None


# WAV and AIFF: chunk lists that say exactly how many samples there are.

def _wav_layout(f, size):
    """(format code, channels, rate, bits, block align, bytes a second, data offset, data bytes) of a WAV
    file, or None."""
    f.seek(0)
    head = f.read(12)
    if head[:4] not in (b"RIFF", b"RF64", b"BW64") or head[8:12] != b"WAVE":
        return None                                # (in RF64 the data chunk's size says "see ds64": read to the end)
    fmt = None
    pos = 12
    while pos + 8 <= size:
        f.seek(pos)
        cid, n = struct.unpack("<4sI", f.read(8))
        if cid == b"fmt ":
            body = f.read(min(n, 40))
            code, ch, rate, per_second, align, bits = struct.unpack_from("<HHIIHH", body, 0)
            if code == 0xFFFE and len(body) >= 26:          # WAVE_FORMAT_EXTENSIBLE: the real code is in the GUID
                code = struct.unpack_from("<H", body, 24)[0]
            fmt = (code, ch, rate, bits, align, per_second)
        elif cid == b"data" and fmt:
            start = pos + 8
            data = size - start if n in (0, 0xFFFFFFFF) else min(n, size - start)
            return fmt + (start, data)
        pos += 8 + n + (n & 1)
    return None


def _wav_duration(path):
    try:
        with wave.open(path, "rb") as w:                    # plain PCM: what the wave module reads
            return w.getnframes() / w.getframerate()
    except (wave.Error, EOFError, RuntimeError, struct.error, ZeroDivisionError):
        pass                                                # float or 24-bit "extensible" files: read the chunks
    with open(path, "rb") as f:
        lay = _wav_layout(f, os.fstat(f.fileno()).st_size)
    if not lay:
        return None
    code, ch, rate, bits, align, per_second, start, data = lay
    if code in (1, 3) and rate and align:
        return (data // align) / rate                       # plain samples: count them
    return data / per_second if per_second else None        # a compressed WAV (ADPCM...): by its byte rate


def _ext80(b):
    """An 80-bit IEEE extended number (AIFF's sample rate). 0.0 for anything that is not a usable rate
    (cut short, infinite, or so large it is plainly damaged)."""
    if len(b) < 10:
        return 0.0
    exp = ((b[0] & 0x7F) << 8) | b[1]
    mant = int.from_bytes(b[2:10], "big")
    if (exp == 0 and mant == 0) or exp == 0x7FFF:            # zero, or infinity / not a number
        return 0.0
    try:
        v = (-1 if b[0] & 0x80 else 1) * math.ldexp(mant, exp - 16383 - 63)
    except OverflowError:
        return 0.0
    return v if math.isfinite(v) and 0 < v < 10_000_000 else 0.0


def _aiff_layout(f, size):
    """(channels, frames, bits, rate, compression, data offset, data bytes) of an AIFF or AIFC file, or None.
    Read by hand: Python's own aifc module is gone from Python 3.13."""
    f.seek(0)
    head = f.read(12)
    if head[:4] != b"FORM" or head[8:12] not in (b"AIFF", b"AIFC"):
        return None
    comm = ssnd = None
    pos = 12
    while pos + 8 <= size:
        f.seek(pos)
        cid, n = struct.unpack(">4sI", f.read(8))
        if cid == b"COMM":
            body = f.read(min(n, 64))
            ch, frames, bits = struct.unpack_from(">HIH", body, 0)
            rate = _ext80(body[8:18])
            comp = body[18:22] if head[8:12] == b"AIFC" and len(body) >= 22 else b"NONE"
            comm = (ch, frames, bits, rate, comp)
        elif cid == b"SSND":
            off = struct.unpack(">I", f.read(4))[0]
            ssnd = (pos + 16 + off, min(n - 8 - off, size - (pos + 16 + off)))
        pos += 8 + n + (n & 1)
    if not comm:
        return None
    return comm + (ssnd or (0, 0))


def _aiff_duration(path):
    with open(path, "rb") as f:
        lay = _aiff_layout(f, os.fstat(f.fileno()).st_size)
    if not lay or not lay[3]:
        return None
    return lay[1] / lay[3]


def _flac_duration(path):
    with open(path, "rb") as f:
        head = f.read(16)
        f.seek(_id3_end(head))
        if f.read(4) != b"fLaC":
            return None
        f.read(4)                                           # the STREAMINFO block's own header
        si = f.read(34)
    x = int.from_bytes(si[10:18], "big")
    rate, total = x >> 44, x & ((1 << 36) - 1)
    return total / rate if rate and total else None


_ADTS_RATES = (96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)


def _adts_duration(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        b = f.read(min(size, 64 * 1024 * 1024))
    p = _id3_end(b[:10])
    samples, rate = 0, None
    while p + 7 <= len(b) and _is_adts(b, p):
        sr_i = (b[p + 2] >> 2) & 0x0F
        if sr_i >= len(_ADTS_RATES):
            break
        rate = _ADTS_RATES[sr_i]
        flen = ((b[p + 3] & 0x03) << 11) | (b[p + 4] << 3) | (b[p + 5] >> 5)
        if flen < 7:
            break
        samples += ((b[p + 6] & 0x03) + 1) * 1024
        p += flen
    if samples and len(b) < size:
        samples = samples * size / max(1, p)
    return samples / rate if rate and samples else None


# ---------------------------------------------------------------- the sound as samples

def _read_wav(path):
    """Mono 16-bit samples from a 16-bit .wav file (what afconvert and ffmpeg are asked to write), plus its rate.
    afconvert writes some of them with the "extensible" header (for instance from an M4A made by Apple's own
    tools), which the wave module of Python 3.9 to 3.11 refuses ("unknown format: 65534"): those are read
    from their chunks instead."""
    try:
        w = wave.open(str(path), "rb")
    except (wave.Error, EOFError, RuntimeError):
        got = _plain_or_none(str(path), ".wav")
        if not got:
            raise
        raw, layout, ch, rate = got
        return _to_mono16(raw, layout, ch), rate
    with w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError("only 16-bit wav")
    a = array.array("h")
    a.frombytes(raw)
    if sys.byteorder == "big":
        a.byteswap()
    if ch > 1:  # average the channels
        a = array.array("h", (sum(a[i:i + ch]) // ch for i in range(0, len(a) - ch + 1, ch)))
    return a, rate


def _resample(a, rate, want):
    """Crude but fine for rhythm: average blocks down to about `want` samples a second."""
    if rate == want:
        return a
    step = rate / want
    out = array.array("h")
    i = 0.0
    n = len(a)
    while i + step <= n:
        lo, hi = int(i), int(i + step)
        seg = a[lo:hi] or a[lo:lo + 1]
        out.append(sum(seg) // len(seg))
        i += step
    return out


def _to_16(raw, kind, channels):
    """Interleaved samples of any common layout (s16le, s16be, s24le, s24be, s32le, s32be, f32le, f32be, f64le,
    f64be, u8) as interleaved 16-bit numbers, every channel kept."""
    big = kind.endswith("be")
    width = 1 if kind == "u8" else {"s16": 2, "s24": 3, "s32": 4, "f32": 4, "f64": 8}[kind[:3]]
    raw = raw[:len(raw) - len(raw) % (width * max(1, channels))]
    if kind.startswith("f"):
        a = array.array("f" if width == 4 else "d")
        a.frombytes(raw)
        if big != (sys.byteorder == "big"):
            a.byteswap()
        return array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in a))
    if kind == "u8":
        return array.array("h", ((v - 128) << 8 for v in raw))
    if width > 2:                                    # keep the top 16 bits of each sample
        keep = bytearray(len(raw) // width * 2)
        hi = 0 if big else width - 2
        keep[0::2] = raw[hi::width]
        keep[1::2] = raw[hi + 1::width]
        raw = bytes(keep)
    a = array.array("h")
    a.frombytes(raw)
    if big != (sys.byteorder == "big"):
        a.byteswap()
    return a


def _to_mono16(raw, kind, channels):
    """The same, as one channel: the channels averaged."""
    a = _to_16(raw, kind, channels)
    if channels > 1:
        a = array.array("h", (sum(a[i:i + channels]) // channels for i in range(0, len(a) - channels + 1, channels)))
    return a


def _plain(path, kind):
    """(raw bytes, layout, channels, rate) of a WAV or AIFF file, read in plain Python, or None."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if kind == ".wav":
            lay = _wav_layout(f, size)
            if not lay:
                return None
            code, ch, rate, bits, align, _, start, n = lay
            kinds = {(1, 8): "u8", (1, 16): "s16le", (1, 24): "s24le", (1, 32): "s32le", (3, 32): "f32le", (3, 64): "f64le"}
            layout = kinds.get((code, bits))
        else:
            lay = _aiff_layout(f, size)
            if not lay:
                return None
            ch, frames, bits, rate, comp, start, n = lay
            rate = int(round(rate))
            kinds = {(b"NONE", 16): "s16be", (b"twos", 16): "s16be", (b"sowt", 16): "s16le", (b"NONE", 24): "s24be",
                     (b"NONE", 32): "s32be", (b"fl32", 32): "f32be", (b"FL32", 32): "f32be", (b"fl64", 64): "f64be"}
            layout = kinds.get((comp, bits))         # (signed 8-bit AIFF, rare, is not in the list: not read here)
        if not layout or not ch or not rate or not n:
            return None
        f.seek(start)
        raw = f.read(min(n, int(LONGEST_SONG * rate * ch * max(1, bits // 8))))
    return raw, layout, ch, rate


# what a damaged, cut-short or half-downloaded WAV or AIFF header raises while it is read by hand
_DAMAGED = (struct.error, IndexError, OverflowError, ValueError, EOFError, RuntimeError, ZeroDivisionError)
_DAMAGED_WORDS = "could not read the song (the file looks damaged or only partly downloaded)"


def _plain_or_none(path, kind):
    """_plain, with a damaged header read as "can't read it" (None) instead of an error."""
    try:
        return _plain(path, kind)
    except _DAMAGED:
        return None


def _looks_damaged(path, kind):
    """True when a WAV or AIFF file's own header can't be made sense of (cut short, half downloaded, chunk
    names spoiled), as against a whole file of a kind plain Python just doesn't read (ADPCM, say)."""
    try:
        with open(path, "rb") as f:
            size = os.fstat(f.fileno()).st_size
            lay = _wav_layout(f, size) if kind == ".wav" else _aiff_layout(f, size)
    except _DAMAGED:
        return True
    except OSError:
        return False
    return lay is None or (kind == ".aiff" and not lay[3])


def _afconvert_ok():
    return bool(shutil.which("afconvert")) and not os.environ.get("ASSISTANT_NO_AFCONVERT")  # pc-ok: only a Mac has it


def _ffmpegs():
    """(program, how) for each ffmpeg this computer has: one on the PATH, then the imageio-ffmpeg add-on's own."""
    if os.environ.get("ASSISTANT_NO_FFMPEG"):
        return
    seen = None
    exe = shutil.which("ffmpeg")
    if exe:
        seen = os.path.normcase(os.path.abspath(exe))
        yield exe, "ffmpeg"
    try:
        import imageio_ffmpeg                       # pip install imageio-ffmpeg: carries its own ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001  (not installed, or its ffmpeg is missing)
        return
    if exe and os.path.isfile(exe) and os.path.normcase(os.path.abspath(exe)) != seen:
        yield exe, "imageio-ffmpeg"


def _run(cmd, timeout=600):
    kw = {"creationflags": 0x08000000} if WINDOWS else {}      # CREATE_NO_WINDOW: no black window flashing up
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout, **kw)


def _last_line(text):
    lines = [x.strip() for x in (text or "").strip().split("\n") if x.strip()]
    return lines[-1][:160] if lines else ""


def decode(path, rate=11025):
    """(samples, how) or (None, reason in plain words). Samples: an array of mono 16-bit numbers, `rate` a
    second. how: afconvert, ffmpeg, imageio-ffmpeg, wav, aiff or windows."""
    path = str(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    alias_dir = None
    try:
        if _afconvert_ok():
            src = path
            kind = real_kind(path)
            if _wants_alias(path, kind):
                # a link with the right name, in a temporary folder; the song itself is untouched
                alias_dir = tempfile.mkdtemp()
                src = os.path.join(alias_dir, "song" + kind)
                os.symlink(os.path.abspath(path), src)  # pc-ok: only where afconvert is, a Mac; a PC copies instead
            r = subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{rate}", "-c", "1", src, tmp.name],  # pc-ok: Mac only
                               capture_output=True, encoding="utf-8", errors="replace")
            if r.returncode == 0 and os.path.getsize(tmp.name) > 44:
                a, got = _read_wav(tmp.name)
                return _resample(a, got, rate), "afconvert"  # pc-ok: the name of the route, in the Mac branch
        for exe, how in _ffmpegs():
            r = _run([exe, "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", str(rate),
                      "-c:a", "pcm_s16le", tmp.name])
            if r.returncode == 0 and os.path.getsize(tmp.name) > 44:
                a, got = _read_wav(tmp.name)
                return _resample(a, got, rate), how
        kind = real_kind(path)
        damaged = False
        if kind in (".wav", ".aiff"):
            got = _plain_or_none(path, kind)
            if got:
                raw, layout, ch, src_rate = got
                return _resample(_to_mono16(raw, layout, ch), src_rate, rate), kind[1:]
            damaged = _looks_damaged(path, kind)
        if WINDOWS:
            a, why = _decode_windows(path, rate)    # unproven on a real PC
            if a is not None:
                return a, "windows"
            return None, (_DAMAGED_WORDS if damaged else why)
        if damaged:
            return None, _DAMAGED_WORDS
        return None, "this computer has no way to read that kind of song file (a .wav would work)"
    except (OSError, ValueError, wave.Error, EOFError, subprocess.SubprocessError, RuntimeError) as e:
        return None, f"could not read the song ({e})"
    except _DAMAGED:
        return None, _DAMAGED_WORDS
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        if alias_dir:
            shutil.rmtree(alias_dir, ignore_errors=True)


# ---------------------------------------------------------------- the sound of a video, as a song file

def _free(path):
    """path, or "<name> 2.<ext>", "<name> 3.<ext>"... whichever is not taken."""
    path, n = Path(path), 2
    cand = path
    while cand.exists():
        cand = path.with_name(f"{path.stem} {n}{path.suffix}")
        n += 1
    return cand


def _remove_ours(path):
    """Take away a half-made file this run created itself (never anything that was there before)."""
    try:
        Path(path).unlink()
    except OSError:
        pass


def extract_audio(video, out):
    """The sound of a video or screen recording as a song file. (path written, how) or (None, reason in plain
    words). The video is only ever read. `out` is the .m4a to make, and must not exist yet; nothing that is
    already there is written over. On a PC with no ffmpeg, Windows' own media parts write it as a .wav beside
    it instead (unproven on a real PC)."""
    video, out = str(video), Path(out)
    if out.exists():
        return None, f"there is already a file called {out.name} there"
    detail = ""
    if _afconvert_ok():
        r = subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", video, str(out)],  # pc-ok: Mac only
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and out.is_file() and out.stat().st_size >= 2000:
            return out, "afconvert"  # pc-ok: the name of the route, in the Mac branch
        _remove_ours(out)
        detail = _last_line(r.stderr)
    for exe, how in _ffmpegs():
        # the song exactly as it is in the video (no re-encoding); if that kind can't go in an .m4a, make AAC.
        # -n: ffmpeg never writes over a file that is there.
        for codec in (["-c:a", "copy"], ["-c:a", "aac", "-b:a", "192k"]):
            if out.exists():                         # only ever clear away a file this run made itself
                return None, f"there is already a file called {out.name} there"
            try:
                r = _run([exe, "-v", "error", "-n", "-i", video, "-vn", "-map", "0:a:0", *codec, str(out)])
            except (OSError, subprocess.SubprocessError) as e:
                detail = str(e)
                _remove_ours(out)
                break                                # this ffmpeg can't run: try the next one
            if r.returncode == 0 and out.is_file() and out.stat().st_size >= 2000:
                return out, how
            _remove_ours(out)
            detail = _last_line(r.stderr)
            if "matches no streams" in (r.stderr or ""):
                return None, "There's no sound in that video."
    if WINDOWS:
        wav, why, saving = _extract_windows(video, out.with_suffix(".wav"))     # unproven on a real PC
        if wav:
            return wav, "windows"
        if why == _NO_SOUND:                         # the add-on wouldn't help: there's nothing to pull out
            return None, "There's no sound in that video."
        if saving:                                   # nor here: Windows heard it, the file couldn't be saved
            return None, f"I heard the sound in that video but couldn't save it as a file ({why})."
        return None, ("I couldn't pull the sound out of that video on this PC (" + why + "). One free add-on "
                      "would do it: imageio-ffmpeg (the command is: python -m pip install imageio-ffmpeg). Or use "
                      "the song itself as a file (mp3, m4a or wav).")
    # (a Mac always has afconvert; this is a computer with neither it nor ffmpeg)
    if detail or _afconvert_ok():
        return None, "I couldn't read any sound in that video. " + detail
    return None, ("this computer has no way to pull the sound out of a video yet. Use the song itself as a file "
                  "(mp3, m4a or wav).")


# ---------------------------------------------------------------- Windows' own Media Foundation (unproven)
#
# Everything below runs only on a PC and has never run on one. Written from Microsoft's documentation:
# "Tutorial: Decoding Audio" for the steps, and the method order of each interface from the Windows SDK
# headers (mfreadwrite.h: IMFSourceReader; mfobjects.h: IMFAttributes, IMFMediaType, IMFSample,
# IMFMediaBuffer). A COM method is called through the object's table of functions, by its place in that table:
#   IUnknown:        0 QueryInterface, 1 AddRef, 2 Release
#   IMFSourceReader: 3 GetStreamSelection, 4 SetStreamSelection, 5 GetNativeMediaType, 6 GetCurrentMediaType,
#                    7 SetCurrentMediaType, 8 SetCurrentPosition, 9 ReadSample, 10 Flush, ...
#   IMFAttributes:   3 GetItem, 4 GetItemType, 5 CompareItem, 6 Compare, 7 GetUINT32, 8 GetUINT64, 9 GetDouble,
#                    10 GetGUID, 11 GetStringLength, 12 GetString, 13 GetAllocatedString, 14 GetBlobSize,
#                    15 GetBlob, 16 GetAllocatedBlob, 17 GetUnknown, 18 SetItem, 19 DeleteItem,
#                    20 DeleteAllItems, 21 SetUINT32, 22 SetUINT64, 23 SetDouble, 24 SetGUID, 25 SetString,
#                    26 SetBlob, 27 SetUnknown, 28 LockStore, 29 UnlockStore, 30 GetCount, 31 GetItemByIndex,
#                    32 CopyAllItems    (IMFMediaType and IMFSample start with these)
#   IMFSample:       33 GetSampleFlags ... 39 GetBufferCount, 40 GetBufferByIndex, 41 ConvertToContiguousBuffer
#   IMFMediaBuffer:  3 Lock, 4 Unlock, 5 GetCurrentLength, 6 SetCurrentLength, 7 GetMaxLength

class _WindowsSoundError(Exception):
    pass


_MF_GUIDS = {
    "MF_MT_MAJOR_TYPE": "48eba18e-f8c9-4687-bf11-0a74c9f96a8f",
    "MF_MT_SUBTYPE": "f7e34c9a-42e8-4714-b74b-cb29d72c35e5",
    "MF_MT_AUDIO_NUM_CHANNELS": "37e48bf5-645e-4c5b-89de-ada9e29b696a",
    "MF_MT_AUDIO_SAMPLES_PER_SECOND": "5faeeae7-0290-4c31-9e8a-c534f68d9dba",
    "MF_MT_AUDIO_BITS_PER_SAMPLE": "f2deb57f-40fa-4764-aa33-ed4f2d1ff669",
    "MFMediaType_Audio": "73647561-0000-0010-8000-00aa00389b71",
    "MFAudioFormat_PCM": "00000001-0000-0010-8000-00aa00389b71",
    "MFAudioFormat_Float": "00000003-0000-0010-8000-00aa00389b71",
}
_NO_SOUND = "there's no sound in it"
# HRESULTs worth saying in words
_MF_WORDS = {
    0xC00D36C4: "Windows doesn't know that kind of file",            # MF_E_UNSUPPORTED_BYTESTREAM_TYPE
    0xC00D36B4: "Windows can't turn that sound into plain samples",  # MF_E_INVALIDMEDIATYPE
    0xC00D5212: "Windows has no decoder for that kind of sound",     # MF_E_TOPO_CODEC_NOT_FOUND
    0xC00D36B9: _NO_SOUND,                                           # MF_E_NO_MORE_TYPES (no audio stream)
    0xC00D36B3: _NO_SOUND,                                           # MF_E_INVALIDSTREAMNUMBER
    0x80070002: "the file isn't there",
    0x80070005: "Windows wasn't allowed to open it",
}


# ---------------------------------------------------------------- the encoder's warm-up at the start
#
# An AAC song starts with about 2,112 samples (48 ms) of the encoder warming up, and an MP3 with the LAME
# encoder's delay plus the decoder's own 529 samples (about 25 ms). The file says how much, and afconvert and
# ffmpeg leave it out; a decoder that keeps it hears every beat that much late, and a cut placed on a late
# beat lands after it (the fault Dustin turned down on Oct 25). _drop_warmup checks what Windows' own Media
# Foundation gave against the lengths a decode could have: when it is a decode that kept the warm-up, the
# warm-up comes off the front; when Windows already took it off, nothing is dropped; when it is neither,
# nothing is dropped either (a song a few milliseconds late beats a song cut short).
#
# Seen on GitHub's Windows machines (Nov 6, 2026, Windows Server 2025, the test songs in tests/fixtures):
# for an MP3, Media Foundation takes the decoder's own 529 samples off the front, as the Mac's afconvert does,
# but keeps LAME's delay (576 samples, 13 ms), so what comes back is 529 samples shorter than a decode that
# kept everything; for a constant-rate MP3 it also plays the silent Info frame first (26 ms more). Before this
# was known, MP3 beats came back a step (variable rate) and three steps (constant rate) later than on the Mac,
# whose own clicks are 13.1 ms late (measured to 0.1 ms with tests/fixtures/decode_report.py). So for that
# shape only LAME's delay (and the Info frame) comes off. The Mac's afconvert is the Mac's route and is not
# changed here.

_MP3_DECODER_DELAY = 529     # samples every MP3 decoder adds at the front
_LAME_DELAY = 576            # LAME's own delay, the usual one; used only when the file doesn't say

def _itunes_note(b):
    """The iTunes gapless note (iTunSMPB) as (encoder delay, padding, samples played), or None."""
    for k, s, e in _boxes(b, 0, len(b)):
        if k != b"udta":
            continue
        meta = _child(b, s, e, b"meta")
        ilst = _child(b, meta[0] + 4, meta[1], b"ilst") if meta else None
        for k2, s2, e2 in _boxes(b, *ilst) if ilst else []:
            if k2 != b"----":
                continue
            name = _child(b, s2, e2, b"name")
            data = _child(b, s2, e2, b"data")
            if name and data and b[name[0] + 4:name[1]] == b"iTunSMPB":
                words = b[data[0] + 8:data[1]].decode("latin-1").split()
                try:
                    return int(words[1], 16), int(words[2], 16), int(words[3], 16)
                except (IndexError, ValueError):
                    return None
    return None


def _stts_totals(b, stbl):
    """(number of packets, their durations added up) from a track's time-to-sample table, or None."""
    stts = _child(b, stbl[0], stbl[1], b"stts")
    if not stts:
        return None
    n = struct.unpack_from(">I", b, stts[0] + 4)[0]
    packets = total = 0
    for i in range(min(n, (stts[1] - stts[0] - 8) // 8)):
        count, delta = struct.unpack_from(">II", b, stts[0] + 8 + 8 * i)
        packets += count
        total += count * delta
    return packets, total


def _mp4_warmup(path):
    """(warm-up seconds, [lengths in seconds a decode that kept the warm-up could have], one frame in seconds,
    False) for the AAC sound of an M4A / MP4 / MOV, or None when it has none or can't be told (a fragmented
    file, more than one piece in its edit list, a sound that isn't AAC).
    The lengths: every packet as a full frame of 1,024 samples (what ffmpeg gives with nothing trimmed); the
    last packet cut to its stated length; and the padding at the end taken off but not the warm-up. Not the
    mdhd length: CapCut's songs give the played length there."""
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        moov = next(((s, e) for k, s, e in _file_boxes(f, 0, size) if k == b"moov"), None)
        if not moov or moov[1] - moov[0] > 64 * 1024 * 1024:
            return None
        f.seek(moov[0])
        b = f.read(moov[1] - moov[0])
    if any(k == b"mvex" for k, _, _ in _boxes(b, 0, len(b))):
        return None                                  # fragmented: the length lives in each fragment
    for k, s, e in _boxes(b, 0, len(b)):
        if k != b"trak":
            continue
        mdia = _child(b, s, e, b"mdia")
        hdlr = _child(b, mdia[0], mdia[1], b"hdlr") if mdia else None
        if not hdlr or b[hdlr[0] + 8:hdlr[0] + 12] != b"soun":
            continue
        mdhd = _child(b, mdia[0], mdia[1], b"mdhd")
        minf = _child(b, mdia[0], mdia[1], b"minf")
        stbl = _child(b, minf[0], minf[1], b"stbl") if minf else None
        stsd = _child(b, stbl[0], stbl[1], b"stsd") if stbl else None
        if not mdhd or not stsd or b[stsd[0] + 12:stsd[0] + 16] != b"mp4a":
            return None                              # not AAC (PCM, ALAC...): no warm-up to speak of
        scale = _scale_and_length(b, mdhd[0])[0]
        counted = _stts_totals(b, stbl)
        if not scale or not counted or not counted[0]:
            return None
        frame = 1024 / scale                         # (the media timescale of an AAC track is its sample rate)
        packets, total = counted
        kept = [packets * 1024 / scale, total / scale]
        note = _itunes_note(b)
        if note and note[0]:
            delay, _, played = note
            return delay / scale, kept + [(delay + played) / scale], frame, False
        mvhd = _child(b, 0, len(b), b"mvhd")
        movie_scale = _scale_and_length(b, mvhd[0])[0] if mvhd else None
        edts = _child(b, s, e, b"edts")
        elst = _child(b, edts[0], edts[1], b"elst") if edts else None
        used = [(seg, m) for seg, m in (_edits(b, elst[0], elst[1]) if elst else []) if m >= 0]
        if len(used) == 1 and used[0][1] > 0:
            front = used[0][1] / scale
            if movie_scale:
                kept.append(front + used[0][0] / movie_scale)
            return front, kept, frame, False
        return None
    return None


def _mp3_frames(path, p, size):
    """Every sound frame of an MP3 counted, from the first one at byte p: (frames, samples a frame), or None
    when the count can't be trusted (a frame that changes kind part way, a file over 64 MB)."""
    if size > 64 * 1024 * 1024:
        return None
    with open(path, "rb") as f:
        b = f.read(size)
    first = _mpa_frame(b, p)
    if not first:
        return None
    q, n = p, 0
    while True:
        fh = _mpa_frame(b, q)
        if not fh:
            break
        if fh[1] != first[1] or fh[2] != first[2]:
            return None
        q += fh[0]
        n += 1
    return (n, first[1]) if n else None


def _mp3_warmup(path):
    """The same for an MP3: from the LAME (or ffmpeg) note in its first frame, which says the encoder's delay;
    True at the end when that first frame is a header frame, which some decoders play as a frame of silence.
    A file with no note at all has its frames counted and LAME's usual delay assumed (most MP3s are LAME's;
    another encoder's few milliseconds more or less are the most it can be off by). None when the file can't
    be measured (Fraunhofer's VBRI header, a header with no frame count, a frame count that can't be trusted)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        b = f.read(min(size, 1024 * 1024))
    start = _id3_end(b[:10])
    if start > len(b) - 4096 and len(b) < size:
        with open(path, "rb") as f:
            b = f.read(min(size, start + 1024 * 1024))
    p, h = _first_frame(b, start)
    if p is None:
        return None
    flen, spf, rate, bitrate, mpeg1, mono = h
    if not rate:
        return None
    x = p + 4 + ((17 if mono else 32) if mpeg1 else (9 if mono else 17))
    if b[x:x + 4] in (b"Xing", b"Info"):
        flags = struct.unpack_from(">I", b, x + 4)[0]
        if not flags & 1:
            return None
        frames = struct.unpack_from(">I", b, x + 8)[0]
        if not frames:
            return None
        q = x + 8 + 4 + (4 if flags & 2 else 0) + (100 if flags & 4 else 0) + (4 if flags & 8 else 0)
        if b[q:q + 4] in (b"LAME", b"Lavf", b"Lavc") and q + 24 <= len(b):
            delay = int.from_bytes(b[q + 21:q + 24], "big") >> 12
        else:
            delay = _LAME_DELAY
        return (delay + _MP3_DECODER_DELAY) / rate, [frames * spf / rate], spf / rate, True
    if b[p + 36:p + 40] == b"VBRI":
        return None
    counted = _mp3_frames(path, p, size)
    if not counted:
        return None
    frames, spf = counted
    return (_LAME_DELAY + _MP3_DECODER_DELAY) / rate, [frames * spf / rate], spf / rate, False


def _drop_warmup(raw, layout, channels, rate, path, first_time):
    """raw without the encoder's warm-up at the front, when Windows left it in. first_time: the first sound's
    time from Windows, in 100-nanosecond steps (below 0 means "this much is warm-up"). Unproven on a real PC."""
    width = (1 if layout == "u8" else {"s16": 2, "s24": 3, "s32": 4, "f32": 4, "f64": 8}[layout[:3]]) * channels
    frames = len(raw) // width
    drop = 0
    if first_time is not None and first_time < 0:
        drop = int(round(-first_time * rate / 10_000_000))
    else:
        kind = real_kind(path)
        try:
            w = _mp4_warmup(path) if kind == ".m4a" else _mp3_warmup(path) if kind == ".mp3" else None
        except Exception:  # noqa: BLE001  (a note that can't be read means nothing is dropped)
            w = None
        if w:
            front, lengths, frame, may_play_first = w
            near = 8                                 # samples: a decode's length is exact; this covers rounding
            base = [(round(x * rate), round(front * rate)) for x in lengths]
            kept = list(base)                        # (length of a decode that kept the warm-up, how much to drop)
            gone = [n - f for n, f in base]          # lengths of the same decodes with the warm-up already off
            if may_play_first:                       # an MP3 decoder that also played the silent first frame
                one = round(frame * rate)
                kept += [(n + one, f + one) for n, f in base]
                gone += [n + one - f for n, f in base]       # ... and took the warm-up off after it
            if kind == ".mp3":                       # Media Foundation: the decoder's 529 off, the encoder's kept
                kept += [(n - _MP3_DECODER_DELAY, f - _MP3_DECODER_DELAY) for n, f in list(kept)]
            for n, f in kept:
                if abs(frames - n) <= near and all(abs(frames - g) > near for g in gone):
                    drop = f
                    break
    if 0 < drop < frames:
        return raw[drop * width:]
    return raw


def _mf_read_pcm(path, longest):
    """(raw bytes, layout like "s16le", channels, rate) of the first sound track of a song or video, decoded by
    Windows' own Media Foundation. Raises _WindowsSoundError in plain words. Unproven on a real PC."""
    import ctypes
    import uuid
    from ctypes import POINTER, byref, c_int, c_long, c_longlong, c_uint32, c_ulong, c_void_p, c_wchar_p

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16),
                    ("Data4", ctypes.c_ubyte * 8)]

    G = {k: GUID.from_buffer_copy(uuid.UUID(v).bytes_le) for k, v in _MF_GUIDS.items()}

    def com(obj, index, *argtypes, restype=c_long):
        """Method number `index` of a COM object (a c_void_p holding the interface pointer)."""
        table = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
        return ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)(table[index])

    def release(obj):
        if obj and obj.value:
            com(obj, 2, restype=c_ulong)(obj)
            obj.value = None

    def check(hr, what):
        if hr < 0:
            code = hr & 0xFFFFFFFF
            raise _WindowsSoundError(_MF_WORDS.get(code, f"Windows said 0x{code:08X} at {what}"))

    try:
        ole32 = ctypes.WinDLL("ole32")
        mfplat = ctypes.WinDLL("mfplat")
        mfrw = ctypes.WinDLL("mfreadwrite")
    except OSError:
        raise _WindowsSoundError("this PC is missing Windows' own media parts (some editions of Windows leave "
                                 "them out; Microsoft's free Media Feature Pack adds them back)")
    ole32.CoInitializeEx.argtypes, ole32.CoInitializeEx.restype = [c_void_p, c_uint32], c_long
    ole32.CoUninitialize.argtypes, ole32.CoUninitialize.restype = [], None
    mfplat.MFStartup.argtypes, mfplat.MFStartup.restype = [c_ulong, c_uint32], c_long
    mfplat.MFShutdown.argtypes, mfplat.MFShutdown.restype = [], c_long
    mfplat.MFCreateMediaType.argtypes, mfplat.MFCreateMediaType.restype = [POINTER(c_void_p)], c_long
    mfrw.MFCreateSourceReaderFromURL.argtypes = [c_wchar_p, c_void_p, POINTER(c_void_p)]
    mfrw.MFCreateSourceReaderFromURL.restype = c_long

    FIRST_AUDIO, ALL_STREAMS = 0xFFFFFFFD, 0xFFFFFFFE
    END_OF_STREAM, READ_ERROR, TYPE_CHANGED = 0x2, 0x1, 0x20
    hr = ole32.CoInitializeEx(None, 0x0)            # COINIT_MULTITHREADED
    com_started = hr >= 0                           # S_OK or S_FALSE; RPC_E_CHANGED_MODE means set up already
    mf_started = False
    reader, partial, current = c_void_p(), c_void_p(), c_void_p()
    chunks, total = [], 0
    try:
        check(mfplat.MFStartup(0x00020070, 0x1), "start")      # MF_VERSION, MFSTARTUP_LITE (no network)
        mf_started = True
        check(mfrw.MFCreateSourceReaderFromURL(os.path.abspath(path), None, byref(reader)), "open")
        select = com(reader, 4, c_uint32, c_int)
        select(reader, ALL_STREAMS, 0)
        check(select(reader, FIRST_AUDIO, 1), "choosing the sound")
        check(mfplat.MFCreateMediaType(byref(partial)), "media type")
        set_guid = com(partial, 24, POINTER(GUID), POINTER(GUID))
        check(set_guid(partial, byref(G["MF_MT_MAJOR_TYPE"]), byref(G["MFMediaType_Audio"])), "sound type")
        check(set_guid(partial, byref(G["MF_MT_SUBTYPE"]), byref(G["MFAudioFormat_PCM"])), "plain samples")
        check(com(partial, 21, POINTER(GUID), c_uint32)(partial, byref(G["MF_MT_AUDIO_BITS_PER_SAMPLE"]), 16), "16-bit")
        set_type = com(reader, 7, c_uint32, c_void_p, c_void_p)
        if set_type(reader, FIRST_AUDIO, None, partial) < 0:
            # this decoder won't give 16-bit: ask for plain samples of whatever size it gives
            com(partial, 19, POINTER(GUID))(partial, byref(G["MF_MT_AUDIO_BITS_PER_SAMPLE"]))
            check(set_type(reader, FIRST_AUDIO, None, partial), "plain samples")
        check(com(reader, 6, c_uint32, POINTER(c_void_p))(reader, FIRST_AUDIO, byref(current)), "reading the type")
        get_u32 = com(current, 7, POINTER(GUID), POINTER(c_uint32))

        def u32(name):
            v = c_uint32(0)
            check(get_u32(current, byref(G[name]), byref(v)), name)
            return v.value
        channels, rate, bits = (u32("MF_MT_AUDIO_NUM_CHANNELS"), u32("MF_MT_AUDIO_SAMPLES_PER_SECOND"),
                                u32("MF_MT_AUDIO_BITS_PER_SAMPLE"))
        sub = GUID()
        check(com(current, 10, POINTER(GUID), POINTER(GUID))(current, byref(G["MF_MT_SUBTYPE"]), byref(sub)), "subtype")
        floats = bytes(sub) == bytes(G["MFAudioFormat_Float"])
        layout = {(False, 16): "s16le", (False, 24): "s24le", (False, 32): "s32le", (False, 8): "u8",
                  (True, 32): "f32le", (True, 64): "f64le"}.get((floats, bits))
        if not layout or not channels or not rate:
            raise _WindowsSoundError(f"Windows gave the sound in a form I can't read ({bits}-bit)")
        cap = int(longest * rate * channels * max(1, bits // 8))
        read = com(reader, 9, c_uint32, c_uint32, POINTER(c_uint32), POINTER(c_uint32), POINTER(c_longlong),
                   POINTER(c_void_p))
        empty = 0
        first_time = None                            # the first sound's time, in 100-nanosecond steps
        while total < cap:
            flags, sample, stamp = c_uint32(0), c_void_p(), c_longlong(0)
            check(read(reader, FIRST_AUDIO, 0, None, byref(flags), byref(stamp), byref(sample)), "reading")
            try:
                if flags.value & TYPE_CHANGED:
                    raise _WindowsSoundError("the sound changed form part way through")
                empty = 0 if sample.value else empty + 1
                if empty > 10000:                    # a gap that never ends: stop rather than wait forever
                    raise _WindowsSoundError("Windows kept giving no sound")
                if sample.value and first_time is None:
                    first_time = stamp.value
                if sample.value:
                    buf = c_void_p()
                    check(com(sample, 41, POINTER(c_void_p))(sample, byref(buf)), "the sound's buffer")
                    try:
                        ptr, most, now = c_void_p(), c_uint32(0), c_uint32(0)
                        check(com(buf, 3, POINTER(c_void_p), POINTER(c_uint32), POINTER(c_uint32))(
                            buf, byref(ptr), byref(most), byref(now)), "locking the buffer")
                        try:
                            if now.value and ptr.value:
                                chunks.append(ctypes.string_at(ptr.value, now.value))
                                total += now.value
                        finally:
                            com(buf, 4)(buf)                         # Unlock
                    finally:
                        release(buf)
            finally:
                release(sample)
            if flags.value & READ_ERROR:
                raise _WindowsSoundError("Windows stopped part way through the sound")
            if flags.value & END_OF_STREAM:
                break
    finally:
        release(current)
        release(partial)
        release(reader)
        if mf_started:
            mfplat.MFShutdown()
        if com_started:
            ole32.CoUninitialize()
    if not total:
        raise _WindowsSoundError(_NO_SOUND)
    raw = b"".join(chunks)
    if total < cap:                                  # (a decode cut off at `cap` can't be measured against the file)
        raw = _drop_warmup(raw, layout, channels, rate, path, first_time)
    return raw[:cap], layout, channels, rate


_PC_WAYS = ("The same song saved as a .wav file would work, or one free add-on reads every kind: imageio-ffmpeg "
            "(the command is: python -m pip install imageio-ffmpeg)")


def _named_right(path, kind, work):
    """Windows picks how to open a file by its ending, so a CapCut song (M4A named .mp3) is opened from a copy
    with the right ending, in a temporary folder. A copy, not a link: a PC needs special permission to make
    links. The song itself is only read."""
    if not _wants_alias(path, kind):
        return path
    dst = os.path.join(work, "song" + kind)
    shutil.copyfile(path, dst)
    return dst


def _decode_windows(path, rate):
    """(samples, "windows") or (None, reason). Unproven on a real PC."""
    work = tempfile.mkdtemp()
    try:
        src = _named_right(path, real_kind(path), work)
        raw, layout, ch, src_rate = _mf_read_pcm(src, LONGEST_SONG)
        return _resample(_to_mono16(raw, layout, ch), src_rate, rate), "windows"
    except _WindowsSoundError as e:
        return None, f"this PC couldn't read that song ({e}). {_PC_WAYS}"
    except Exception as e:  # noqa: BLE001  (anything unexpected from a route nobody has run: say so, never crash)
        return None, f"this PC couldn't read that song ({type(e).__name__}: {e}). {_PC_WAYS}"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _extract_windows(video, wav):
    """The sound of a video written as a 16-bit .wav named like wav, or "<name> 2.wav" and so on if that name
    is taken by the time the sound is ready (decoding can take minutes, and nothing already there is ever
    written over or removed). (path written, "", False) or (None, why, whether it was the saving that failed).
    Unproven on a real PC."""
    try:
        raw, layout, ch, rate = _mf_read_pcm(video, LONGEST_VIDEO)
        if layout != "s16le":                        # every channel kept, as plain 16-bit
            a = _to_16(raw, layout, ch)
            if sys.byteorder == "big":
                a.byteswap()
            raw = a.tobytes()
    except _WindowsSoundError as e:
        return None, str(e), False
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", False
    if len(raw) < 2000:
        return None, _NO_SOUND, False
    for _ in range(100):
        cand = _free(wav)                            # picked now, after the decode, not before it
        try:
            fh = open(cand, "xb")                    # "x": only ever a file this run makes itself
        except FileExistsError:
            continue                                 # it appeared in the meantime: it isn't ours, leave it
        except OSError as e:
            return None, str(e), True
        try:
            with fh, wave.open(fh, "wb") as w:
                w.setnchannels(ch)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(raw)
            return cand, "", False
        except (OSError, wave.Error) as e:
            _remove_ours(cand)                       # our own half-made file, opened above by this run
            return None, str(e), True
    return None, f"there are too many files called {Path(wav).stem} there already", True


# ---------------------------------------------------------------- a quick look

def main():
    args = sys.argv[1:]
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--extract" and len(args) == 3:
        got, how = extract_audio(args[1], args[2])
        print(f"Made {got} ({how})" if got else how)
        return 0 if got else 1
    for a in args:
        d = duration(a)
        print(f"{Path(a).name}: {real_kind(a) or 'unknown kind'}, " + (f"{d:.3f} s" if d else "length unknown"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
