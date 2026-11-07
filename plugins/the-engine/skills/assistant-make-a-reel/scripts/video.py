#!/usr/bin/env python3
"""The Assistant, by Horizon Found. What the reel page and the footage look need from a video, with nothing
installed: its facts, stills at given times, a small copy to play on the page, and how loud it is.

    python3 video.py facts <video> [<video> ...]           the facts, as JSON, one line each
    python3 video.py stills <video> <folder> <times> [--edge 360]
                                                            stills at those times (seconds, comma between), in a
                                                            new folder made inside <folder>
    python3 video.py copy <video> <out.mp4>                 the small copy for playing (made once)
    python3 video.py loudness <video>                       loudness every half second, and the loud moments

Nicole's footage.py and server.py did this with ffprobe, ffmpeg and Pillow (handoff v19). The Assistant installs
nothing, so:

  * The facts (facts): read from the video's own movie header (the 'moov' box) in plain Python, the same code on
    a Mac and a PC, never the picture data (a few KB to a few MB read, wherever in the file the header sits):
    length, the size it is shown at (after a phone's sideways turn), the turn, the kind of video (avc1 is
    H.264, hvc1 / hev1 HEVC...), H.264's profile and colour layout (chroma) and bit depth when the file says,
    frames a second, whether it has sound, and when the phone recorded it. A file that is not a video is
    refused in plain words (NotAVideo), never guessed at.
  * Stills (stills) and the small copy (preview_copy), on a Mac: the Mac's own AVFoundation, through one small
    JavaScript for Automation script (VIDEO_JS), run by this_computer.mac_javascript. Stills are taken at the
    exact time asked (no nearest-keyframe guess) and each is labelled with the time AVFoundation really
    returned; they come out upright (a phone's turn applied), no longer than the long edge asked for, as JPEG.
    The copy is hers in size: 540 on its short side (never enlarged), H.264 8-bit 4:2:0 with AAC sound, made by
    AVFoundation's own export session (its 960x540 preset's rate, not her 1.3 Mbit/s: an export session can't be
    given a rate, and the reader-to-writer loop that could held every frame in memory: v19 review, Nov 7).
  * Loudness (loudness): her measure (footage.py's loudness, an RMS level in dB every half second of the sound
    at 8,000 a second), on the sound sound.decode hears (afconvert on a Mac, Media Foundation on a PC), or, on
    a Mac when that can't, AVFoundation's reader. Her loud_moments picks the stretches that jump out of the
    room sound. One difference, on purpose (NEAR_FULL): her loop dropped the last half second whenever it was
    even one sample short, which a decode often is; ours keeps a last half second that is at least 90% there.

On a PC (decision 11 of the v19 plan, and a named gap): the facts, plays_as_is, loudness and everything built on
them work. Stills and the small copy are NOT built for a PC yet (Media Foundation's source reader and sink
writer through ctypes, written and proven on GitHub's Windows machines first): there stills() and
preview_copy() answer with state "pc" and this_computer.NO_PREVIEW, and an HEVC video (an iPhone's High
Efficiency) with "hevc_pc" and this_computer.HEVC_HELP. The reel page plays a video that plays as it is (H.264)
on a PC with no strip of stills; anything else can't give a clip there. Nothing is asked for up front and nothing
is installed (PC_ADDON stays None).
ASSISTANT_NO_AVFOUNDATION=1 makes a Mac answer the way a PC does, to try that route.

The rules it keeps (CLAUDE.md, and the plan's section 4):
  * A video is only ever read. Nothing is deleted or written over: every look's stills go in a new folder
    (fresh_folder), never one an earlier look made (her footage.py emptied its folder first; this never does);
    the copy is written under a hidden ".<name>.part-<number>.mp4" name in the same folder and only then given
    its real name, never over a file that is there; a copy already made is used as it is.
  * The copy is refused unless the drive keeps 5 GB free after it (SPACE_MARGIN, hers): state "lowspace".
  * Memory: JavaScript for Automation keeps every still it wrote until its program ends (measured Nov 7: about
    one still's pixels each, 160 MB for 400 stills at 360 px), so stills are taken in batches, each its own short
    program held under STILL_BATCH_BYTES. The copy is AVFoundation's export session, which does its own reading
    and writing, so its memory stays flat however long the video (measured Nov 7: 38.9 MB for 2 s and 39.4 MB for
    10 s at 60 a second, where the old loop grew from 44.5 to 51.0 MB; tests/video_check.py checks it).
  * One video program at a time on this computer (turn(), a lock file in STUDIO_HOME held by the running program
    itself), and every program stops by itself when the Python that started it is gone.
  * plays_as_is: H.264 with 8-bit 4:2:0 colour plays in the Claude app's browser pane as it is (her rule: h264
    with yuv420p); anything else is played from the small copy.
  * The copy keeps its header at the end (the plan's b1). The page server answers range requests, so the player
    still finds it. The phone's turn is drawn into the copy's pictures (it is stored upright, turn 0).

What is proven (Nov 7, 2026, on Dustin's Mac, macOS 27.2, Apple's own Python 3.9), only on clips tests/video_check.py
makes itself (6 s, 640 x 360 and 720 x 720, H.264, one stored sideways, one MP4 with an accent and a space in its
name): the facts equal AVFoundation's own; stills at exact times by their colour, upright, never enlarged; the loud
stretch found within one half second, through afconvert (which does hear a MOV's sound) and through AVFoundation's
reader alike; the copy made once, upright, read back by AVFoundation. tests/pc_video.py checks the header reader on
headers built byte by byte, on both computers. Not tried: a phone's own HEVC or HDR footage, 4K, long footage,
a fragmented file from a real camera, any of it on a real PC.

Python 3.9, standard library only.
"""
import array
import contextlib
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "studio-manager" / "scripts"))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import sound  # noqa: E402

VIDEO_EXTS = (".mov", ".mp4", ".m4v")      # hers
PREVIEW_SHORT = 540                        # hers: the copy is 540 on its short side (never enlarged)
COPY_PRESET = "AVAssetExportPreset960x540"  # AVFoundation's own 540p rate (hers asked ffmpeg for 1300k + AAC 96k;
                                           # an export session can't be given a rate: on the Tell Nicole list)
COPY_RATE = 5_000_000                      # bits a second the copy is allowed for, to check the room first (more
                                           # than the preset uses, so the check errs on the side of room)
SPACE_MARGIN = 5e9                         # hers: always leave at least 5 GB free on the drive
STILL_EDGE = 360                           # hers: stills 360 px (footage.py's scale=360)
STILL_QUALITY = 0.82                       # hers: her sheets were saved at quality 82
STILL_BATCH_BYTES = 96_000_000             # the most still pixels one AVFoundation program may hold (see Memory)
STILL_BATCH_MOST = 120
LOUD_STEP = 0.5                            # hers: a level every half second
LOUD_RATE = 8000                           # hers: the sound read at 8,000 a second, one channel
NEAR_FULL = 0.9                            # ours: a last half second this full still counts (hers needed it whole)
MOOV_MOST = 256 * 1024 * 1024              # a movie header bigger than this is not a video anyone shot
PC_ADDON = None                            # decision 11: no add-on is asked for on a PC (nothing is installed)
NO_AV = "ASSISTANT_NO_AVFOUNDATION"        # tests: a Mac answers the way a PC does
TURN_WAIT = 900                            # seconds a video program waits for its turn before saying it's busy
BUSY = "another video is being got ready on this computer right now"
_RUN = os.urandom(3).hex()                 # this process's own mark on its half-made copies (exec keeps the pid)

CHROMA = {0: "4:0:0", 1: "4:2:0", 2: "4:2:2", 3: "4:4:4"}
H264_PROFILES = {66: "Baseline", 77: "Main", 88: "Extended", 100: "High", 110: "High 10", 122: "High 4:2:2",
                 244: "High 4:4:4", 44: "CAVLC 4:4:4"}
# H.264 profiles whose sequence header carries the colour layout and bit depth (the others are always 8-bit 4:2:0)
_H264_HIGH = {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}
CODEC_NAMES = {"avc1": "h264", "avc3": "h264", "hvc1": "hevc", "hev1": "hevc", "dvh1": "hevc", "dvhe": "hevc",
               "mp4v": "mpeg4", "ap4h": "prores", "ap4x": "prores", "apch": "prores", "apcn": "prores",
               "apcs": "prores", "apco": "prores", "jpeg": "mjpeg", "av01": "av1", "vp09": "vp9"}
HEVC = {"hvc1", "hev1", "dvh1", "dvhe"}


class NotAVideo(ValueError):
    """The file is not a video this can read. str() is the reason in plain words, for the page and for Claude."""


# ---------------------------------------------------------------- the movie header, in plain Python

def _file_boxes(f, start, end):
    """(kind, where its contents start, where it ends) for each box between start and end, read by seeking."""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        hdr = f.read(8)
        if len(hdr) < 8:
            return
        size, kind = struct.unpack(">I4s", hdr)
        head = 8
        if size == 1:                            # a 64-bit box (a long video's picture data)
            big = f.read(8)
            if len(big) < 8:
                return
            size, head = struct.unpack(">Q", big)[0], 16
        elif size == 0:                          # the last box, to the end of the file
            size = end - pos
        if size < head or pos + size > end:
            yield kind, None, None               # cut off, or not boxes at all
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
    if s is None:
        return None, None
    return next(((cs, ce) for k, cs, ce in _boxes(b, s, e) if k == kind), (None, None))


_TOP_KINDS = {b"ftyp", b"moov", b"mdat", b"free", b"skip", b"wide", b"pnot", b"uuid", b"junk", b"meta", b"pdin",
              b"moof", b"mfra", b"styp", b"sidx", b"prfl", b"PICT"}


def still_coming(path):
    """True when the file looks like a video still being copied in: a box at its top level (the picture data, or
    a header written at the end) runs past the end of the file. A whole video, and a file that isn't boxes at
    all, say False (the facts then say what it is). Only a few bytes are read."""
    try:
        size = os.path.getsize(path)
        f = open(path, "rb")
    except OSError:
        return False
    with f:
        first = True
        for kind, s, e in _file_boxes(f, 0, size):
            if first and kind not in _TOP_KINDS:
                return False
            first = False
            if s is None:
                return kind in _TOP_KINDS
    return False


def read_moov(path):
    """The movie header's bytes, wherever it sits in the file (a phone writes it at the end, an export at the
    front). Only the header is read. NotAVideo when there is none."""
    path = str(path)
    try:
        size = os.path.getsize(path)
        f = open(path, "rb")
    except OSError as e:
        raise NotAVideo(f"I couldn't open that file ({e.strerror or e}).")
    with f:
        if size < 16:
            raise NotAVideo("That file is empty, or nearly: it isn't a video.")
        first = True
        for kind, s, e in _file_boxes(f, 0, size):
            if first and kind not in _TOP_KINDS:
                raise NotAVideo("That file isn't a video (it isn't a MOV or MP4 file inside).")
            first = False
            if s is None:
                break
            if kind == b"moov":
                if e - s > MOOV_MOST:
                    raise NotAVideo("That video's header is far too big to be a real video.")
                f.seek(s)
                body = f.read(e - s)
                if len(body) < e - s:
                    break
                # handed back as a box of its own with an ordinary 8-byte header (a 64-bit one is written as a
                # plain one here), so its contents always start at 8
                return struct.pack(">I4s", 8 + len(body), b"moov") + body
    raise NotAVideo("That video looks cut off: its header (the part that says how long it is) isn't in the file. "
                    "If it was still copying, wait for it to finish.")


def _fixed(x):
    return x / 65536.0


def _rotation(m):
    """The turn, in degrees clockwise (0, 90, 180 or 270), from a track's 3x3 matrix (a, b, u, c, d, v, x, y, w).
    The same angle AVFoundation's preferredTransform gives (atan2 of b over a)."""
    a, b = _fixed(m[0]), _fixed(m[1])
    if a == 0 and b == 0:
        return 0
    deg = math.degrees(math.atan2(b, a)) % 360
    return int(round(deg / 90.0) * 90) % 360


def _unescape(nal):
    """An H.264 NAL unit without its emulation-prevention bytes (00 00 03 -> 00 00)."""
    out, zeros = bytearray(), 0
    for x in nal:
        if zeros >= 2 and x == 3:
            zeros = 0
            continue
        out.append(x)
        zeros = zeros + 1 if x == 0 else 0
    return bytes(out)


class _Bits:
    def __init__(self, b):
        self.b, self.p = b, 0

    def bit(self):
        if self.p >= len(self.b) * 8:
            raise ValueError("ran out")
        v = (self.b[self.p >> 3] >> (7 - (self.p & 7))) & 1
        self.p += 1
        return v

    def ue(self):
        zeros = 0
        while self.bit() == 0:
            zeros += 1
            if zeros > 31:
                raise ValueError("bad number")
        v = 0
        for _ in range(zeros):
            v = (v << 1) | self.bit()
        return (1 << zeros) - 1 + v


def _avcc(b, s, e):
    """(profile, chroma, bits) from an avcC box: the profile always; the colour layout and bit depth from the
    first sequence header for the High profiles, else what the profile always means (8-bit 4:2:0)."""
    if e - s < 7:
        return None, None, None
    profile = b[s + 1]
    chroma, bits = (1, 8) if profile not in _H264_HIGH else (None, None)
    n_sps = b[s + 5] & 0x1F
    if profile in _H264_HIGH and n_sps and s + 8 <= e:
        ln = struct.unpack_from(">H", b, s + 6)[0]
        sps = b[s + 8:min(e, s + 8 + ln)]
        try:
            r = _Bits(_unescape(sps[4:]))       # after the NAL header, profile, constraint flags and level
            r.ue()                              # which sequence header
            c = r.ue()
            if c == 3:
                r.bit()                         # separate colour planes
            chroma, bits = c, r.ue() + 8
        except ValueError:
            chroma, bits = None, None
        if chroma is None and e - s >= 7:
            # the avcC's own extension, after the picture headers, says it too (High profiles only)
            try:
                p = s + 6
                for _ in range(n_sps):
                    p += 2 + struct.unpack_from(">H", b, p)[0]
                n_pps = b[p]
                p += 1
                for _ in range(n_pps):
                    p += 2 + struct.unpack_from(">H", b, p)[0]
                if p + 3 <= e:
                    chroma, bits = b[p] & 3, (b[p + 1] & 7) + 8
            except (struct.error, IndexError):
                pass
    return profile, chroma, bits


def _hvcc(b, s, e):
    """(profile, chroma, bits) from an hvcC box (HEVC): 1 Main, 2 Main 10 (an iPhone's HDR)."""
    if e - s < 19:
        return None, None, None
    return b[s + 1] & 0x1F, b[s + 16] & 3, (b[s + 17] & 7) + 8


def _apple_creationdate(b, moov_s, moov_e):
    """com.apple.quicktime.creationdate from moov/meta (its keys and ilst), the phone's own time with its time
    zone, or ""."""
    ms, me = _child(b, moov_s, moov_e, b"meta")
    if ms is None:
        return ""
    if ms + 4 <= me and b[ms:ms + 4] == b"\x00\x00\x00\x00":
        ms += 4                                  # an ISO-style meta: version and flags first (a QuickTime one starts
                                                 # with its first box's size, never 0)
    ks, ke = _child(b, ms, me, b"keys")
    ls, le = _child(b, ms, me, b"ilst")
    if ks is None or ls is None or ke - ks < 8:
        return ""
    count = struct.unpack_from(">I", b, ks + 4)[0]
    p, idx = ks + 8, None
    for i in range(1, count + 1):
        if p + 8 > ke:
            break
        size = struct.unpack_from(">I", b, p)[0]
        if size < 8 or p + size > ke:
            break
        if b[p + 8:p + size] == b"com.apple.quicktime.creationdate":
            idx = i
            break
        p += size
    if idx is None:
        return ""
    for kind, s, e in _boxes(b, ls, le):
        if struct.unpack(">I", kind)[0] != idx:
            continue
        ds, de = _child(b, s, e, b"data")
        if ds is not None and de - ds > 8:
            return b[ds + 8:de].decode("utf-8", "replace").strip("\x00").strip()
    return ""


def _udta_day(b, moov_s, moov_e):
    """The ©day text of moov/udta (some cameras and older phones), or ""."""
    us, ue = _child(b, moov_s, moov_e, b"udta")
    if us is None:
        return ""
    ds, de = _child(b, us, ue, b"\xa9day")
    if ds is None or de - ds < 5:
        return ""
    ln = struct.unpack_from(">H", b, ds)[0]
    return b[ds + 4:min(de, ds + 4 + ln)].decode("utf-8", "replace").strip("\x00").strip()


def _mvhd(b, s, e):
    """(created, timescale, duration) of the movie header; created is seconds since 1904 (0 = not set)."""
    if b[s] == 1:
        created, _, scale, dur = struct.unpack_from(">QQIQ", b, s + 4)
        unknown = dur == 0xFFFFFFFFFFFFFFFF
    else:
        created, _, scale, dur = struct.unpack_from(">IIII", b, s + 4)
        unknown = dur == 0xFFFFFFFF
    return created, scale, (None if unknown else dur)


def _mdhd(b, s):
    if b[s] == 1:
        scale, dur = struct.unpack_from(">IQ", b, s + 20)
    else:
        scale, dur = struct.unpack_from(">II", b, s + 12)
    return scale, dur


def _stts_frames(b, s, e):
    if s is None or e - s < 8:
        return 0
    n = struct.unpack_from(">I", b, s + 4)[0]
    total = 0
    for i in range(n):
        p = s + 8 + 8 * i
        if p + 8 > e:
            break
        total += struct.unpack_from(">I", b, p)[0]
    return total


def facts(path):
    """What the video is, from its movie header only, the same on a Mac and a PC:
    {"length": seconds, "w", "h": the size it is shown at, "stored_w", "stored_h", "rotation": 0/90/180/270,
     "codec": its four letters ("avc1", "hvc1"...), "codec_name": "h264", "hevc"..., "profile": a number or None,
     "profile_name", "chroma": "4:2:0"... or None, "bits": 8, 10 or None, "fps", "has_audio", "audio_codec",
     "recorded": when it was recorded as the file says it ("" when it doesn't), "recorded_from": "phone" (the
     phone's own time, with its time zone), "camera" (©day), "file" (the movie header's own clock, UTC) or "",
     "plays_as_is"}. NotAVideo for a file that isn't one."""
    b = read_moov(path)
    end = len(b)
    if _child(b, 8, end, b"cmov")[0] is not None:
        raise NotAVideo("That video is an old QuickTime kind with a squeezed header, which I can't read.")
    ms, me = _child(b, 8, end, b"mvhd")
    if ms is None:
        raise NotAVideo("That video's header is damaged (it has no movie header).")
    created, scale, dur = _mvhd(b, ms, me)
    out = {"length": round(dur / scale, 3) if scale and dur else 0.0, "w": 0, "h": 0, "stored_w": 0, "stored_h": 0,
           "rotation": 0, "codec": "", "codec_name": "", "profile": None, "profile_name": "", "chroma": None,
           "bits": None, "fps": 0.0, "has_audio": False, "audio_codec": "", "recorded": "", "recorded_from": ""}
    video = False
    for kind, s, e in _boxes(b, 8, end):
        if kind != b"trak":
            continue
        da, dz = _child(b, s, e, b"mdia")
        ha, hz = _child(b, da, dz, b"hdlr")
        if ha is None or hz - ha < 12:
            continue
        handler = b[ha + 8:ha + 12]
        ia, iz = _child(b, da, dz, b"minf")
        sa, sz = _child(b, ia, iz, b"stbl")
        ea, ez = _child(b, sa, sz, b"stsd")
        if ea is None or ez - ea < 16:
            continue
        entry = ea + 8                               # the first sample description
        esize = struct.unpack_from(">I", b, entry)[0]
        four = b[entry + 4:entry + 8].decode("latin-1")
        if handler == b"soun":
            if not out["has_audio"]:
                out["has_audio"], out["audio_codec"] = True, four.strip()
            continue
        if handler != b"vide" or video:
            continue
        ta, tz = _child(b, s, e, b"tkhd")
        if ta is None:
            continue
        mo = ta + (52 if b[ta] == 1 else 40)         # the matrix, then the width and height (16.16)
        if mo + 44 > tz:
            continue
        flags = struct.unpack_from(">I", b, ta)[0] & 0xFFFFFF
        if not flags & 1 and _any_enabled_video(b, end, s):
            continue                                 # a disabled picture track beside an enabled one
        video = True
        m = struct.unpack_from(">9i", b, mo)
        tw, th = (round(_fixed(x)) for x in struct.unpack_from(">II", b, mo + 36))
        ew, eh = struct.unpack_from(">HH", b, entry + 32) if entry + 36 <= ez else (0, 0)
        w, h = (tw, th) if tw and th else (ew, eh)
        rot = _rotation(m)
        out.update(stored_w=w, stored_h=h, rotation=rot, codec=four, codec_name=CODEC_NAMES.get(four, four.strip()),
                   w=h if rot in (90, 270) else w, h=w if rot in (90, 270) else h)
        cend = min(ez, entry + esize)
        for k2, s2, e2 in _boxes(b, entry + 86, cend):
            if k2 == b"avcC":
                p, c, bits = _avcc(b, s2, e2)
                out.update(profile=p, profile_name=H264_PROFILES.get(p, str(p) if p is not None else ""),
                           chroma=CHROMA.get(c) if c is not None else None, bits=bits)
            elif k2 == b"hvcC":
                p, c, bits = _hvcc(b, s2, e2)
                out.update(profile=p, profile_name={1: "Main", 2: "Main 10", 3: "Main Still"}.get(p, str(p)),
                           chroma=CHROMA.get(c) if c is not None else None, bits=bits)
        mh = _child(b, da, dz, b"mdhd")[0]
        if mh is not None:
            mscale, mdur = _mdhd(b, mh)
            frames = _stts_frames(b, *_child(b, sa, sz, b"stts"))
            if mscale and mdur and frames:
                out["fps"] = round(frames / (mdur / mscale), 3)
            if not out["length"] and mscale and mdur:
                out["length"] = round(mdur / mscale, 3)
    if not video:
        raise NotAVideo("That file has no picture in it (it is only sound, or something else).")
    if not out["length"]:
        try:                                         # a fragmented file: sound.py adds up its pieces
            d = sound.duration(path)
            out["length"] = round(d, 3) if d else 0.0
        except Exception:  # noqa: BLE001
            pass
    rec = _apple_creationdate(b, 8, end)
    if rec:
        out["recorded"], out["recorded_from"] = rec, "phone"
    else:
        day = _udta_day(b, 8, end)
        if day:
            out["recorded"], out["recorded_from"] = day, "camera"
        elif created > 86400 * 366 * 66:             # set, and after 1970 (a clock never set says 1904 or 1970)
            when = datetime(1904, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=created)
            out["recorded"], out["recorded_from"] = when.strftime("%Y-%m-%dT%H:%M:%SZ"), "file"
    out["plays_as_is"] = plays_as_is(out)
    return out


def _any_enabled_video(b, end, skip_at):
    for kind, s, e in _boxes(b, 8, end):
        if kind != b"trak" or s == skip_at:
            continue
        da, dz = _child(b, s, e, b"mdia")
        ha, hz = _child(b, da, dz, b"hdlr")
        ta, tz = _child(b, s, e, b"tkhd")
        if ha is not None and ta is not None and b[ha + 8:ha + 12] == b"vide" and struct.unpack_from(">I", b, ta)[0] & 1:
            return True
    return False


def plays_as_is(f):
    """True when the Claude app's browser pane plays this video as it is: H.264 with 8-bit 4:2:0 colour (her
    rule, ffprobe's h264 with yuv420p or yuvj420p). Anything else (HEVC, 10-bit, 4:2:2, ProRes, a kind the header
    doesn't say) is played from the small copy."""
    return f.get("codec") in ("avc1", "avc3") and f.get("chroma") == "4:2:0" and f.get("bits") == 8


def recorded_local(f):
    """When it was recorded, as a plain local date and time (camera clocks have no time zone; hers: when()), or
    None. A time with a zone ("2026-11-06T10:12:33-0800", "...Z") is turned into this computer's local time."""
    rec = (f.get("recorded") if isinstance(f, dict) else f) or ""
    m = re.match(r"(\d{4})[-:](\d\d)[-:](\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?", rec.strip())
    if not m:
        return None
    try:
        t = datetime(*(int(x) for x in m.groups()[:6]))
    except ValueError:
        return None
    zone = m.group(7)
    if zone:
        if zone == "Z":
            off = timedelta(0)
        else:
            hh, mm = int(zone[1:3]), int(zone[-2:])
            off = timedelta(hours=hh, minutes=mm) * (1 if zone[0] == "+" else -1)
        t = (t - off).replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    return t


def key(path):
    """A video's key for the page: made from its name, size and time, never its place (12 letters and numbers)."""
    p = Path(path)
    st = p.stat()
    return hashlib.sha1(f"{p.name}|{st.st_size}|{int(st.st_mtime)}".encode("utf-8")).hexdigest()[:12]


def fresh_folder(parent, name):
    """A new folder for one look: <parent>/<name>, or "<name> 2", "<name> 3"... whichever is not there yet. Never a
    folder that is already there, so nothing an earlier look made is ever written over or cleared away."""
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    name = this_computer.safe_name(name, fallback="look")
    for n in range(1, 10000):
        cand = parent / (name if n == 1 else f"{name} {n}")
        try:
            cand.mkdir()
            return cand
        except FileExistsError:
            continue
    raise OSError("too many looks in " + str(parent))


# ---------------------------------------------------------------- the Mac's own AVFoundation

VIDEO_JS = r"""
ObjC.import('AVFoundation'); ObjC.import('CoreMedia'); ObjC.import('CoreGraphics'); ObjC.import('ImageIO');
ObjC.import('Foundation'); ObjC.import('unistd');
// The Assistant's video helper (video.py). Every command only READS the video, and never writes over a file.
function C(n) { return $.NSClassFromString(n); }
function spin(flag, ms) { var t0 = Date.now(); while (!flag() && Date.now() - t0 < ms) $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(0.02)); }
function asset(p) { return C('AVURLAsset').URLAssetWithURLOptions($.NSURL.fileURLWithPath(p), $.NSDictionary.dictionaryWithDictionary({AVURLAssetPreferPreciseDurationAndTimingKey: true})); }
function track(a, kind) { var ts = a.tracksWithMediaType(kind); return Number(ts.count) ? ts.objectAtIndex(0) : null; }
function there(p) { return $.NSFileManager.defaultManager.fileExistsAtPath($(p)); }
function secs(t) { return $.CMTimeGetSeconds(t); }
function why(e) { return e && e[0] && !e[0].isNil() ? e[0].localizedDescription.js : ''; }
// The program that started this one (video.py's Python). When it is gone (a page server stopped or crashed), this
// one stops too: nobody is left to take its answer, and it would hold the video lock (v19 review, Nov 7).
var PARENT = 0;
function orphaned() { return PARENT > 1 && Number($.getppid()) !== PARENT; }

// stills <video> <folder> <long edge> <quality> <first number> <t1,t2,...>: JPEGs NNNNNN.jpg, exact times
function stills(p, dir, edge, q, first, spec) {
  var a = asset(p);
  if (!track(a, 'vide')) return {error: 'no picture in it'};
  var g = C('AVAssetImageGenerator').assetImageGeneratorWithAsset(a);
  g.appliesPreferredTrackTransform = true;              // a phone video stored sideways comes out upright
  g.maximumSize = $.CGSizeMake(edge, edge);             // fits inside edge x edge; never made bigger
  g.requestedTimeToleranceBefore = $.kCMTimeZero; g.requestedTimeToleranceAfter = $.kCMTimeZero;
  var times = spec.split(',').map(parseFloat), got = [];
  for (var i = 0; i < times.length; i++) {
    if (orphaned()) return {error: 'stopped: the program that asked for it is gone', stills: got};
    var f = dir + '/' + ('00000' + (first + i)).slice(-6) + '.jpg';
    if (there(f)) { got.push({asked: times[i], error: 'already there'}); continue; }
    var act = Ref(), err = Ref();
    var cg = g.copyCGImageAtTimeActualTimeError($.CMTimeMakeWithSeconds(times[i], 600), act, err);
    if (!cg || (cg.isNil && cg.isNil())) { got.push({asked: times[i], error: why(err) || 'no picture there'}); continue; }
    var d = $.CGImageDestinationCreateWithURL($.NSURL.fileURLWithPath(f), $('public.jpeg'), 1, null);
    $.CGImageDestinationAddImage(d, cg, $.NSDictionary.dictionaryWithDictionary({kCGImageDestinationLossyCompressionQuality: q}));
    if (!$.CGImageDestinationFinalize(d)) { got.push({asked: times[i], error: 'could not write the still'}); continue; }
    got.push({asked: times[i], at: Math.round(secs(act[0]) * 10000) / 10000, w: Number($.CGImageGetWidth(cg)),
              h: Number($.CGImageGetHeight(cg)), file: ('00000' + (first + i)).slice(-6) + '.jpg'});
  }
  return {stills: got};
}

// copy <video> <out> <short side> <preset>: H.264 + AAC, upright, never enlarged. AVFoundation's own export
// session decodes and encodes by itself (the reader-to-writer loop it replaced held every frame and every second of
// sound in this program's memory until it ended: v19 review, Nov 7). The picture is drawn through a video
// composition at exactly the size wanted, the phone's turn applied, so every copy is made fresh as H.264 8-bit
// 4:2:0 (a composition never passes the original's pictures through as they were).
function copy(p, out, shortSide, preset) {
  if (there(out)) return {error: 'already there'};
  var a = asset(p), v = track(a, 'vide'), t0 = Date.now();
  if (!v) return {error: 'no picture in it'};
  var n = v.naturalSize, T = v.preferredTransform;
  var box = $.CGRectApplyAffineTransform($.CGRectMake(0, 0, n.width, n.height), T);
  var sw = Math.abs(box.size.width), sh = Math.abs(box.size.height);
  if (!(sw > 0 && sh > 0)) return {error: 'no picture size'};
  var k = Math.min(1, shortSide / Math.min(sw, sh));
  var W = Math.max(2, Math.round(sw * k / 2) * 2), H = Math.max(2, Math.round(sh * k / 2) * 2);
  var M = $.CGAffineTransformConcat($.CGAffineTransformConcat(T, $.CGAffineTransformMakeTranslation(-box.origin.x, -box.origin.y)),
                                    $.CGAffineTransformMakeScale(W / sw, H / sh));
  var li = C('AVMutableVideoCompositionLayerInstruction').videoCompositionLayerInstructionWithAssetTrack(v);
  li.setTransformAtTime(M, $.kCMTimeZero);
  var ins = C('AVMutableVideoCompositionInstruction').videoCompositionInstruction;
  ins.timeRange = $.CMTimeRangeMake($.kCMTimeZero, a.duration);
  ins.layerInstructions = $.NSArray.arrayWithObject(li);
  var comp = C('AVMutableVideoComposition').videoComposition;
  comp.renderSize = $.CGSizeMake(W, H);
  var fps = Number(v.nominalFrameRate) || 30;
  comp.frameDuration = $.CMTimeMake(100, Math.max(100, Math.round(fps * 100)));
  comp.instructions = $.NSArray.arrayWithObject(ins);
  var ex = C('AVAssetExportSession').alloc.initWithAssetPresetName(a, preset);
  if (!ex || ex.isNil()) return {error: 'this Mac has no ' + preset};
  ex.outputURL = $.NSURL.fileURLWithPath(out); ex.outputFileType = 'public.mpeg-4';
  ex.videoComposition = comp;
  ex.shouldOptimizeForNetworkUse = false;               // the header at the end; the page server answers ranges
  var done = false; ex.exportAsynchronouslyWithCompletionHandler(function () { done = true; });
  while (!done) {
    if (orphaned()) { ex.cancelExport; spin(function () { return done; }, 10000); return {error: 'stopped: the program that asked for it is gone'}; }
    $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(0.05));
  }
  if (Number(ex.status) !== 3) return {error: 'the copy could not be made' + (ex.error.isNil() ? '' : ': ' + ex.error.localizedDescription.js)};
  return {w: W, h: H, took: (Date.now() - t0) / 1000};
}

// pcm <video> <out> <rate>: the sound as plain 16-bit samples, one channel, little-endian (for loudness)
function pcm(p, out, rate) {
  if (there(out)) return {error: 'already there'};
  var a = asset(p), s = track(a, 'soun'), err = Ref();
  if (!s) return {has_audio: false};
  var r = C('AVAssetReader').assetReaderWithAssetError(a, err);
  var o = C('AVAssetReaderTrackOutput').assetReaderTrackOutputWithTrackOutputSettings(s, $.NSDictionary.dictionaryWithDictionary({
    AVFormatIDKey: 0x6C70636D, AVSampleRateKey: rate, AVNumberOfChannelsKey: 1, AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false, AVLinearPCMIsNonInterleaved: false}));
  r.addOutput(o); r.startReading;
  var all = $.NSMutableData.data;
  while (true) {
    if (orphaned()) { r.cancelReading; return {error: 'stopped: the program that asked for it is gone'}; }
    var sb = o.copyNextSampleBuffer;
    if (Number(r.status) !== 1 || !$.CMSampleBufferIsValid(sb)) break;
    var bb = $.CMSampleBufferGetDataBuffer(sb), len = $.CMBlockBufferGetDataLength(bb);
    var d = $.NSMutableData.dataWithLength(len);
    $.CMBlockBufferCopyDataBytes(bb, 0, len, d.mutableBytes);
    all.appendData(d);
  }
  if (Number(r.status) !== 2) return {error: 'the sound could not be read to the end'};
  if (!all.writeToFileAtomically($(out), false)) return {error: 'could not write the sound'};
  return {has_audio: true, rate: rate, bytes: Number(all.length)};
}

function run(argv) {
  try {
    var c = argv[0], r;
    PARENT = Number($.getppid());
    if (c === 'stills') r = stills(argv[1], argv[2], parseInt(argv[3]), parseFloat(argv[4]), parseInt(argv[5]), argv[6]);
    else if (c === 'copy') r = copy(argv[1], argv[2], parseInt(argv[3]), argv[4]);
    else if (c === 'pcm') r = pcm(argv[1], argv[2], parseInt(argv[3]));
    else r = {error: 'no such command'};
    return JSON.stringify(r);
  } catch (e) { return JSON.stringify({error: String((e && e.message) || e)}); }
}
"""


def avfoundation_here():
    """True when this computer can do stills and the copy (a Mac's own AVFoundation)."""
    return this_computer.MAC and not os.environ.get(NO_AV)


# ---- one video program at a time on this computer (v19 review, Nov 7)
# Two page servers, a server and itself after a restart, the footage look, and every Use this moment each started
# their own AVFoundation program, and two copies of one video were made at once. Now every AVFoundation run takes
# its turn under one lock file for the whole computer (<STUDIO_HOME>/video.lock), and the running program is handed
# the lock itself (this_computer.mac_javascript's pass_fds): the lock is held for as long as that program lives,
# even when the Python that started it is gone, so nothing can start a second one beside it. The program also
# stops by itself when its Python is gone (VIDEO_JS's orphaned()).

_HELD = threading.local()


def lock_path():
    return Path(os.environ.get("STUDIO_HOME") or (Path.home() / ".studio")) / "video.lock"


@contextlib.contextmanager
def turn(wait=TURN_WAIT, waiting=None):
    """Wait (up to `wait` seconds) for this computer's one video turn and hold it inside the with-block: yields
    True when held (or when this computer has no such locks: carry on, as before), False when the turn didn't come
    in time. Inside a turn this thread may run any number of video programs; another thread or program waits.
    waiting(): called once if it has to wait (to say so)."""
    if getattr(_HELD, "depth", 0):
        _HELD.depth += 1
        try:
            yield True
        finally:
            _HELD.depth -= 1
        return
    f = None
    try:
        p = lock_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        f = open(p, "a", encoding="utf-8")
    except OSError:
        f = None
    got = this_computer.try_lock(f) if f is not None else None
    if got is False:
        if waiting:
            waiting()
        end = time.time() + max(0.0, float(wait))
        while got is False and time.time() < end:
            time.sleep(0.2)
            got = this_computer.try_lock(f)
    if got is False:
        f.close()
        yield False
        return
    _HELD.depth, _HELD.f, _HELD.real = 1, (f if got else None), bool(got)
    try:
        yield True
    finally:
        _HELD.depth, _HELD.f, _HELD.real = 0, None, False
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


def holding_turn():
    """True inside a turn that holds the real lock (not one carried on without)."""
    return bool(getattr(_HELD, "depth", 0) and getattr(_HELD, "real", False))


def _av(args, timeout, wait=TURN_WAIT):
    """Run one VIDEO_JS command, in its turn. Its answer as a dict (always one; {"error": ...} when it failed,
    {"error": BUSY, "busy": True} when its turn didn't come within `wait` seconds)."""
    with turn(wait) as ok:
        if not ok:
            return {"error": BUSY, "busy": True}
        fds = (_HELD.f.fileno(),) if getattr(_HELD, "f", None) is not None else ()
        return _av_now(args, timeout, fds)


def _av_now(args, timeout, fds):
    try:
        got = this_computer.mac_javascript(VIDEO_JS, args, timeout=timeout, pass_fds=fds)
    except subprocess.TimeoutExpired:
        return {"error": "it took too long"}
    except (OSError, subprocess.SubprocessError) as e:
        return {"error": str(e)}
    if got is None:
        return {"error": "this computer has no AVFoundation"}
    code, out, err = got
    line = (out or "").strip().splitlines()[-1:] or [""]
    try:
        r = json.loads(line[0])
        return r if isinstance(r, dict) else {"error": "an odd answer"}
    except ValueError:
        return {"error": ((err or "").strip().splitlines() or ["it stopped (exit %s)" % code])[-1][:300]}


def _pc_gap(f):
    """What a PC says in place of a still or a player (decision 11: HEVC gets its own words)."""
    if f and f.get("codec") in HEVC and this_computer.WINDOWS:
        return {"ok": False, "state": "hevc_pc", "words": this_computer.HEVC_HELP}
    return {"ok": False, "state": "pc", "words": this_computer.NO_PREVIEW}


def _batch_size(f, edge):
    """How many stills one AVFoundation program takes (see Memory in the notes at the top)."""
    w, h = (f.get("w") or edge), (f.get("h") or edge)
    k = min(1.0, edge / max(1, w, h))
    one = max(1, int(w * k)) * max(1, int(h * k)) * 4 + 40_000
    return max(1, min(STILL_BATCH_MOST, int(STILL_BATCH_BYTES // one)))


def stills(path, times, into, name="look", edge=STILL_EDGE, quality=STILL_QUALITY, f=None, deadline=None,
           wait=TURN_WAIT):
    """Stills of the video at the given times (seconds), in a NEW folder made inside `into` (fresh_folder(into,
    name)). Exact times; each still is labelled with the time it really is ("at") beside the time asked; upright;
    no longer than `edge` on its long side; JPEG. Answer:
      {"ok": True, "folder": <the new folder>, "stills": [{"asked", "at", "w", "h", "file"}, or {"asked", "error"}],
       "took"} or {"ok": False, "state": "pc" | "hevc_pc" | "failed" | "busy", "words": plain words}.
    The video is only read. A time past the end is taken at the last picture. Every batch waits its turn (turn())
    for up to `wait` seconds; "busy" when not one did, and then no folder is made."""
    t0 = time.time()
    try:
        f = f or facts(path)
    except NotAVideo as e:
        return {"ok": False, "state": "failed", "words": str(e)}
    if not avfoundation_here():
        return _pc_gap(f)
    last = max(0.0, f["length"] - (0.5 / f["fps"] if f.get("fps") else 0.02))
    want = []
    for t in times:
        try:
            t = float(t)
        except (TypeError, ValueError):
            continue
        if math.isfinite(t):
            want.append(round(min(max(0.0, t), last), 4))
    with turn(wait) as ok:
        if not ok:
            return {"ok": False, "state": "busy", "words": BUSY}
        return _stills_now(path, want, into, name, edge, quality, f, deadline, t0)


def _stills_now(path, want, into, name, edge, quality, f, deadline, t0):
    folder = fresh_folder(into, name)
    got = []
    per = _batch_size(f, int(edge))
    for i in range(0, len(want), per):
        part = want[i:i + per]
        left = None if deadline is None else deadline - time.time()
        if left is not None and left <= 1:
            got += [{"asked": t, "error": "out of time"} for t in want[i:]]
            break
        timeout = 30 + 0.5 * len(part) if left is None else min(30 + 0.5 * len(part), left)
        r = _av(["stills", str(path), str(folder), str(int(edge)), str(quality), str(i + 1),
                 ",".join(f"{t:.4f}" for t in part)], timeout)
        if "error" in r:
            got += [{"asked": t, "error": r["error"]} for t in part]
            continue
        got += r.get("stills") or []
    ok = any("file" in g for g in got)
    out = {"ok": ok, "folder": str(folder), "stills": got, "took": round(time.time() - t0, 2)}
    if not ok:
        out.update(state="failed", words="I couldn't take any stills from that video.")
    return out


def copy_name(out):
    """The hidden name a copy is made under: this process's number and its own mark (a server that starts over
    keeps its number, never its mark), so no run ever takes another's half-copy for its own."""
    out = Path(out)
    return out.with_name(f".{out.stem}.part-{os.getpid()}-{_RUN}{out.suffix}")


def _left_parts(out):
    """Half-copies beside `out` left by runs that were stopped (ours by their hidden name only)."""
    out = Path(out)
    pre, suf = f".{out.stem}.part-", out.suffix
    try:
        names = os.listdir(out.parent)
    except OSError:
        return []
    return [out.parent / n for n in names if n.startswith(pre) and n.endswith(suf)]


def space_ok(folder, need):
    """Hers: true only when the drive keeps SPACE_MARGIN (5 GB) free after `need` more bytes."""
    free = this_computer.free_bytes(folder)
    return free is not None and free > need + SPACE_MARGIN


def preview_copy(path, out, short=PREVIEW_SHORT, f=None, timeout=None, wait=TURN_WAIT):
    """The small copy to play on the page (hers: _make_preview), made once at `out` (an .mp4): 540 on its short
    side or smaller (never enlarged), H.264 about 1.3 Mbit/s, AAC 96 kbit/s, upright when played.
    Answer: {"ok": True, "made": True|False (False: it was already there, used as it is), "w", "h"} or
    {"ok": False, "state": "lowspace" | "failed" | "pc" | "hevc_pc", "words": plain words}.
    Refused unless the drive keeps 5 GB free after it. Written under a hidden ".<name>.part-<number>.mp4" first
    and only then given its real name, never over a file that is there; the video is only read. Made in its turn
    (turn()): a half-copy found beside it then can only be from a run that was stopped (every run that makes one
    holds the turn while it does), so it is taken away first; it is ours by its hidden name."""
    out = Path(out)
    if out.exists():
        return {"ok": True, "made": False}
    try:
        f = f or facts(path)
    except NotAVideo as e:
        return {"ok": False, "state": "failed", "words": str(e)}
    if not avfoundation_here():
        return _pc_gap(f)
    with turn(wait) as ok:
        if not ok:
            return {"ok": False, "state": "busy", "words": BUSY}
        return _copy_now(path, out, short, f, timeout)


def _copy_now(path, out, short, f, timeout):
    if out.exists():
        return {"ok": True, "made": False}
    out.parent.mkdir(parents=True, exist_ok=True)
    if holding_turn():
        for p in _left_parts(out):
            _remove_ours(p)                # a stopped run's half-copy: nobody else can be writing it now
    if not space_ok(out.parent, f["length"] * COPY_RATE / 8 * 1.2):
        return {"ok": False, "state": "lowspace",
                "words": "Your photo drive is nearly full, so I didn't make a preview of this one. The moments and "
                         "your reel still work; you just can't watch it here."}
    part = copy_name(out)
    if timeout is None:
        timeout = max(120.0, f["length"] * 3)
    r = _av(["copy", str(path), str(part), str(int(short)), COPY_PRESET], timeout)
    if "error" in r or not part.is_file() or part.stat().st_size < 1000:
        _remove_ours(part)
        return {"ok": False, "state": "failed", "detail": r.get("error", ""),
                "words": "I couldn't make a preview of this one. The moments and your reel still work; you just "
                         "can't watch it here."}
    try:
        placed = this_computer.rename_new(str(part), str(out))
    except OSError as e:
        _remove_ours(part)
        return {"ok": False, "state": "failed", "detail": str(e),
                "words": "I couldn't make a preview of this one. The moments and your reel still work; you just "
                         "can't watch it here."}
    if not placed:                         # another copy got there first: that one is used, ours goes
        _remove_ours(part)
        return {"ok": True, "made": False}
    return {"ok": True, "made": True, "w": r.get("w"), "h": r.get("h"), "took": r.get("took")}


def _remove_ours(path):
    """Take away a half-made file this run made itself under its hidden name (never anything else)."""
    try:
        Path(path).unlink()
    except OSError:
        pass


# ---------------------------------------------------------------- how loud, every half second (hers)

def levels(samples, rate=LOUD_RATE, step=LOUD_STEP):
    """Her measure: the RMS level in dB (of full scale, 16-bit) of each half second, rounded to a tenth. Ours: a
    last half second at least NEAR_FULL there counts too (hers dropped any that was a sample short)."""
    hop = int(rate * step)
    n = len(samples)
    out = []
    i = 0
    while i < n:
        chunk = samples[i:i + hop]
        if len(chunk) < hop and len(chunk) < NEAR_FULL * hop:
            break
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk)) or 1.0
        out.append(round(20 * math.log10(rms / 32768), 1))
        i += hop
    return out


def loudness(path, step=LOUD_STEP, f=None):
    """(levels every half second, how) or (None, why in plain words). [] with "no sound" when it has none."""
    try:
        f = f or facts(path)
    except NotAVideo as e:
        return None, str(e)
    if not f.get("has_audio"):
        return [], "no sound"
    a, how = sound.decode(path, rate=LOUD_RATE, video=True)
    if a is None and avfoundation_here():
        a, how2 = _pcm_mac(path)
        how = how2 if a is not None else how
    if a is None:
        return None, how
    return levels(a, LOUD_RATE, step), how


def _pcm_mac(path):
    """The sound through AVFoundation's reader, into a scratch file of this run that is taken away after."""
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="assistant-sound-"))
    raw = d / "sound.raw"
    try:
        f = facts(path)
        r = _av(["pcm", str(path), str(raw), str(LOUD_RATE)], max(60.0, f["length"]))
        if "error" in r or not raw.is_file():
            return None, "I couldn't read the sound in that video (" + r.get("error", "") + ")"
        a = array.array("h")
        a.frombytes(raw.read_bytes())
        if sys.byteorder == "big":
            a.byteswap()
        return a, "avfoundation"
    finally:
        _remove_ours(raw)
        try:
            d.rmdir()
        except OSError:
            pass


def loud_moments(db, step=LOUD_STEP, k=10):
    """Hers, word for word in what it does: the stretches that jump out of the room sound (laughs, squeals,
    cheers, someone talking up): [{"at": seconds, "db", "above_room"}], at most k, 4 s apart or more."""
    if not db:
        return []
    srt = sorted(db)
    floor = srt[len(srt) // 2]
    score = []
    for i, x in enumerate(db):
        before = sum(db[max(0, i - 6):i]) / max(1, len(db[max(0, i - 6):i])) if i else x
        score.append((x - floor) + max(0, x - before) * 0.8)
    picks = []
    for i in sorted(range(len(db)), key=lambda i: -score[i]):
        if score[i] < 6:
            break
        if all(abs(i - j) * step > 4 for j in picks):
            picks.append(i)
        if len(picks) >= k:
            break
    return [{"at": round(i * step, 1), "db": db[i], "above_room": round(db[i] - floor, 1)} for i in sorted(picks)]


# ---------------------------------------------------------------- a quick look

def main():
    this_computer.utf8_output()
    a = sys.argv[1:]
    if not a or a[0] not in ("facts", "stills", "copy", "loudness"):
        print(__doc__)
        return 2
    if a[0] == "facts":
        code = 0
        for p in a[1:]:
            try:
                print(json.dumps({"video": Path(p).name, **facts(p)}, ensure_ascii=False))
            except NotAVideo as e:
                print(json.dumps({"video": Path(p).name, "refused": str(e)}, ensure_ascii=False))
                code = 1
        return code
    if a[0] == "stills" and len(a) >= 4:
        edge = int(a[a.index("--edge") + 1]) if "--edge" in a else STILL_EDGE
        r = stills(a[1], [x for x in a[3].split(",") if x.strip()], a[2], edge=edge)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("ok") else 1
    if a[0] == "copy" and len(a) == 3:
        r = preview_copy(a[1], a[2])
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("ok") else 1
    if a[0] == "loudness" and len(a) == 2:
        db, how = loudness(a[1])
        print(json.dumps({"levels": db, "how": how, "loud": loud_moments(db or [])}, ensure_ascii=False))
        return 0 if db is not None else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
