#!/usr/bin/env python3
"""The reel's video helper (assistant-make-a-reel/scripts/video.py) the way a PC runs it: written to run on GitHub's
Windows machine, and on a Mac.

    python tests/pc_video.py

tests/video_check.py is the full test, on real clips the Mac's AVFoundation makes; a PC can't make those with
nothing installed. This one builds video headers byte by byte in plain Python (a movie header is only boxes of
numbers; the picture data is never read by video.facts, so it can be anything), in a scratch folder it makes
itself, and checks:
  1. the facts read from the header, the same code on both computers: the length, the size shown after a phone's
     turn (0, 90, 180, 270), the kind (H.264, HEVC), H.264's profile, colour layout and bit depth from its sequence
     header, frames a second, sound, the recording time (the phone's own, a camera's, the file's clock, none);
     the header at the end, at the front with a "to the end" box after it, a 64-bit box, version-1 boxes, a
     header in a 64-bit box of its own, a disabled picture track beside an enabled one, a size only in the sample
     description;
  2. plays_as_is: only H.264 8-bit 4:2:0 (Baseline, Main, High); High 10, High 4:2:2 and HEVC play from the copy;
  3. refusals in plain words: random bytes, a WAV, an empty file, a cut-off file, sound only, an old squeezed
     QuickTime header, a missing file;
  4. this computer's stills and copy where there is no AVFoundation (a PC, or a Mac told ASSISTANT_NO_AVFOUNDATION):
     the plain words of the named gap (this_computer.NO_PREVIEW; HEVC_HELP for an HEVC video on a PC), and nothing
     made: no folder, no file;
  5. the small things: a fresh folder for every look (never one already there), a video's key, a recording time
     as local time, her loudness measure and loud moments on made-up levels, mac_javascript answering None on a PC.
Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept.
"""
import os
import random
import shutil
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(REEL))
import video  # noqa: E402
import this_computer  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:400]}]" if detail and not ok else ""), flush=True)


# ---------------------------------------------------------------- building a header, box by box

def box(kind, payload=b""):
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


def big_box(kind, payload):
    return struct.pack(">I4sQ", 1, kind, 16 + len(payload)) + payload


def full(kind, version, flags, payload):
    return box(kind, struct.pack(">I", (version << 24) | flags) + payload)


ONE = 0x10000
MATRIX = {0: (ONE, 0, 0, 0, ONE, 0, 0, 0, 0x40000000), 90: (0, ONE, 0, -ONE, 0, 0, 0, 0, 0x40000000),
          180: (-ONE, 0, 0, 0, -ONE, 0, 0, 0, 0x40000000), 270: (0, -ONE, 0, ONE, 0, 0, 0, 0, 0x40000000)}
SECS_1904_TO_2026 = int((datetime(2026, 11, 6, 18, 12, 33) - datetime(1904, 1, 1)).total_seconds())


def mvhd(scale, dur, created=SECS_1904_TO_2026, v=0):
    if v == 1:
        head = struct.pack(">QQIQ", created, created, scale, dur)
    else:
        head = struct.pack(">IIII", created, created, scale, dur)
    return full(b"mvhd", v, 0, head + struct.pack(">IH10x", ONE, 0x100) + struct.pack(">9i", *MATRIX[0]) + b"\0" * 24
                + struct.pack(">I", 3))


def tkhd(track, dur, w, h, rot=0, v=0, enabled=True):
    if v == 1:
        head = struct.pack(">QQIIQ", 0, 0, track, 0, dur)
    else:
        head = struct.pack(">IIIII", 0, 0, track, 0, dur)
    return full(b"tkhd", v, 3 if enabled else 2, head + b"\0" * 8 + struct.pack(">hhhH", 0, 0, 0, 0)
                + struct.pack(">9i", *MATRIX[rot]) + struct.pack(">II", w * ONE, h * ONE))


def mdhd(scale, dur, v=0):
    head = struct.pack(">QQIQ", 0, 0, scale, dur) if v == 1 else struct.pack(">IIII", 0, 0, scale, dur)
    return full(b"mdhd", v, 0, head + struct.pack(">HH", 0x55C4, 0))


def hdlr(kind):
    return full(b"hdlr", 0, 0, b"\0" * 4 + kind + b"\0" * 12 + b"name\0")


class BitWriter:
    def __init__(self):
        self.bits = []

    def put(self, v, n):
        self.bits += [(v >> (n - 1 - i)) & 1 for i in range(n)]

    def ue(self, v):
        v += 1
        n = v.bit_length()
        self.put(0, n - 1)
        self.put(v, n)

    def bytes(self):
        bits = self.bits + [1] + [0] * ((8 - (len(self.bits) + 1) % 8) % 8)    # the stop bit, then zeros
        return bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))


def sps(profile, chroma=1, bits=8, level=31):
    w = BitWriter()
    w.ue(0)                                       # seq_parameter_set_id
    if profile in (100, 110, 122, 244):
        w.ue(chroma)
        if chroma == 3:
            w.put(0, 1)
        w.ue(bits - 8)
        w.ue(bits - 8)
        w.put(0, 2)                               # qpprime_y_zero_transform_bypass, seq_scaling_matrix_present
    w.ue(0)
    w.ue(0)
    w.ue(1)
    w.ue(39)
    w.ue(22)
    return bytes([0x67, profile, 0, level]) + w.bytes()


def avcc(profile, chroma=1, bits=8):
    s = sps(profile, chroma, bits)
    pps = bytes([0x68, 0xEE, 0x3C, 0x80])
    return box(b"avcC", bytes([1, profile, 0, 31, 0xFF, 0xE1]) + struct.pack(">H", len(s)) + s
               + bytes([1]) + struct.pack(">H", len(pps)) + pps)


def hvcc(profile, chroma=1, bits=8):
    return box(b"hvcC", bytes([1, profile, 0x60, 0, 0, 0, 0x90, 0, 0, 0, 0, 0, 120, 0xF0, 0, 0xFC, 0xFC | chroma,
                               0xF8 | (bits - 8), 0xF8 | (bits - 8), 0, 0, 0x0F, 0]))


def video_entry(four, w, h, inner):
    body = (b"\0" * 6 + struct.pack(">H", 1) + b"\0" * 16 + struct.pack(">HH", w, h) + struct.pack(">II", 0x480000, 0x480000)
            + b"\0" * 4 + struct.pack(">H", 1) + b"\0" * 32 + struct.pack(">Hh", 24, -1) + inner)
    return box(four, body)


def audio_entry():
    return box(b"mp4a", b"\0" * 6 + struct.pack(">H", 1) + b"\0" * 8 + struct.pack(">HHHHI", 2, 16, 0, 0, 44100 << 16))


def stbl(entry, frames, delta):
    return box(b"stbl", full(b"stsd", 0, 0, struct.pack(">I", 1) + entry)
               + full(b"stts", 0, 0, struct.pack(">III", 1, frames, delta)) + full(b"stco", 0, 0, struct.pack(">I", 0)))


def vtrak(track=1, w=640, h=360, rot=0, secs=6, fps=30, codec=b"avc1", conf=None, v=0, enabled=True, entry_wh=None):
    scale = fps * 100
    conf = conf if conf is not None else avcc(100)
    ew, eh = entry_wh or (w, h)
    return box(b"trak", tkhd(track, secs * 600, w, h, rot, v, enabled)
               + box(b"mdia", mdhd(scale, secs * scale, v) + hdlr(b"vide")
                     + box(b"minf", stbl(video_entry(codec, ew, eh, conf), secs * fps, 100))))


def atrak(track=2, secs=6):
    return box(b"trak", tkhd(track, secs * 600, 0, 0) + box(b"mdia", mdhd(44100, secs * 44100) + hdlr(b"soun")
                                                            + box(b"minf", stbl(audio_entry(), secs * 43, 1024))))


def creationdate(text, iso=False):
    keys = full(b"keys", 0, 0, struct.pack(">I", 2) + box(b"mdta", b"com.apple.quicktime.make")
                + box(b"mdta", b"com.apple.quicktime.creationdate"))
    item1 = box(struct.pack(">I", 1), box(b"data", struct.pack(">II", 1, 0) + b"Apple"))
    item2 = box(struct.pack(">I", 2), box(b"data", struct.pack(">II", 1, 0) + text.encode("utf-8")))
    inner = hdlr(b"mdta") + keys + box(b"ilst", item1 + item2)
    return box(b"meta", (b"\0" * 4 + inner) if iso else inner)


def moov(*traks, secs=6, created=SECS_1904_TO_2026, extra=b"", v=0):
    return box(b"moov", mvhd(600, secs * 600, created, v) + b"".join(traks) + extra)


FTYP = box(b"ftyp", b"qt  " + struct.pack(">I", 0) + b"qt  ")
DATA = bytes(random.Random(7).getrandbits(8) for _ in range(5000))     # the "picture data": never read


def write(folder, name, *parts):
    p = Path(folder) / name
    p.write_bytes(b"".join(parts))
    return p


def main():
    work = Path(tempfile.mkdtemp(prefix="assistant pc video "))
    os.environ.pop(video.NO_AV, None)
    phone = "2026-11-06T10:12:33-0800"
    std = moov(vtrak(rot=90), atrak(), extra=creationdate(phone))

    # ---- 1. the facts
    end = write(work, "phone sideways.MOV", FTYP, box(b"wide"), box(b"mdat", DATA), std)
    f = video.facts(end)
    check("a phone video, header at the end: 6 s, stored 640x360, shown 360x640, turned 90",
          (f["length"], f["stored_w"], f["stored_h"], f["w"], f["h"], f["rotation"]) == (6.0, 640, 360, 360, 640, 90), f)
    check("its kind, profile, colour layout and bit depth: avc1 (h264), High, 4:2:0, 8-bit; 30 a second; sound",
          (f["codec"], f["codec_name"], f["profile"], f["profile_name"], f["chroma"], f["bits"], f["fps"], f["has_audio"],
           f["audio_codec"]) == ("avc1", "h264", 100, "High", "4:2:0", 8, 30.0, True, "mp4a"), f)
    check("its recording time is the phone's own, word for word", (f["recorded"], f["recorded_from"]) == (phone, "phone"), f)
    check("it plays as it is", f["plays_as_is"] is True, f)
    first = write(work, "header first.mp4", FTYP, std, struct.pack(">I4s", 0, b"mdat"), DATA)
    big = write(work, "big box.mp4", FTYP, big_box(b"mdat", DATA), std)
    bigmoov = write(work, "big header.mp4", FTYP, box(b"mdat", DATA), big_box(b"moov", std[8:]))
    v1 = write(work, "version one.mov", FTYP, box(b"mdat", DATA),
               moov(vtrak(rot=90, v=1), atrak(), extra=creationdate(phone), v=1))
    iso = write(work, "iso meta.mp4", FTYP, box(b"mdat", DATA), moov(vtrak(rot=90), atrak(), extra=creationdate(phone, iso=True)))
    for p in (first, big, bigmoov, v1, iso):
        g = video.facts(p)
        check(f"{p.name}: the same facts", {k: g[k] for k in f} == f, (g, f))
    for rot in (0, 180, 270):
        g = video.facts(write(work, f"turned {rot}.mov", FTYP, box(b"mdat", DATA), moov(vtrak(rot=rot))))
        want = (640, 360) if rot in (0, 180) else (360, 640)
        check(f"turned {rot}: shown {want[0]}x{want[1]}", (g["rotation"], g["w"], g["h"]) == (rot, *want), g)
    g = video.facts(write(work, "no tkhd size.mov", FTYP, box(b"mdat", DATA), moov(vtrak(w=0, h=0, entry_wh=(1280, 720)))))
    check("a size only in the sample description is used", (g["w"], g["h"]) == (1280, 720), g)
    g = video.facts(write(work, "two pictures.mov", FTYP, box(b"mdat", DATA),
                          moov(vtrak(track=1, w=320, h=240, enabled=False), vtrak(track=3, w=640, h=360))))
    check("a disabled picture track beside an enabled one: the enabled one counts", (g["w"], g["h"]) == (640, 360), g)
    g = video.facts(write(work, "camera.mov", FTYP, box(b"mdat", DATA),
                          moov(vtrak(), extra=box(b"udta", box(b"\xa9day", struct.pack(">HH", 19, 0x55C4)
                                                                + b"2026-11-06 10:12:33")))))
    check("a camera's own time (udta ©day)", (g["recorded"], g["recorded_from"]) == ("2026-11-06 10:12:33", "camera"), g)
    g = video.facts(write(work, "file clock.mov", FTYP, box(b"mdat", DATA), moov(vtrak())))
    check("no phone time: the movie header's own clock, as UTC", (g["recorded"], g["recorded_from"])
          == ("2026-11-06T18:12:33Z", "file"), g)
    g = video.facts(write(work, "no clock.mov", FTYP, box(b"mdat", DATA), moov(vtrak(), created=0)))
    check("a clock never set: no recording time, not a made-up one", (g["recorded"], g["recorded_from"]) == ("", ""), g)
    g = video.facts(write(work, "silent.mp4", FTYP, box(b"mdat", DATA), moov(vtrak(fps=25))))
    check("no sound, 25 a second", (g["has_audio"], g["fps"]) == (False, 25.0), g)

    # ---- 2. what plays as it is
    kinds = [("Baseline", avcc(66), b"avc1", (66, "4:2:0", 8, True)), ("Main", avcc(77), b"avc1", (77, "4:2:0", 8, True)),
             ("High 10", avcc(110, 1, 10), b"avc1", (110, "4:2:0", 10, False)),
             ("High 4:2:2", avcc(122, 2, 8), b"avc1", (122, "4:2:2", 8, False)),
             ("High 4:4:4", avcc(244, 3, 8), b"avc1", (244, "4:4:4", 8, False)),
             ("HEVC Main 10 (an iPhone's HDR)", hvcc(2, 1, 10), b"hvc1", (2, "4:2:0", 10, False)),
             ("HEVC Main", hvcc(1, 1, 8), b"hvc1", (1, "4:2:0", 8, False))]
    for name, conf, four, want in kinds:
        g = video.facts(write(work, name.replace(":", "-") + ".mov", FTYP, box(b"mdat", DATA), moov(vtrak(codec=four, conf=conf))))
        got = (g["profile"], g["chroma"], g["bits"], g["plays_as_is"])
        check(f"{name}: profile {want[0]}, {want[1]}, {want[2]}-bit, " + ("plays as it is" if want[3] else "played from the copy"),
              got == want, g)
    g = video.facts(write(work, "no avcC.mov", FTYP, box(b"mdat", DATA), moov(vtrak(conf=b""))))
    check("H.264 that doesn't say its colour layout: played from the copy (never guessed)", g["plays_as_is"] is False, g)
    check("emulation-prevention bytes are taken out before reading a sequence header",
          video._unescape(b"\x00\x00\x03\x01\x00\x00\x03\x00") == b"\x00\x00\x01\x00\x00\x00")

    # ---- 3. refusals
    bad = {"random bytes.mov": bytes(random.Random(3).getrandbits(8) for _ in range(4000)),
           "a wav.mp4": b"RIFF" + struct.pack("<I", 100) + b"WAVEfmt " + b"\0" * 100,
           "empty.mov": b"",
           "cut off.mov": FTYP + box(b"mdat", DATA) + std[:len(std) // 2],
           "sound only.m4a": FTYP + box(b"mdat", DATA) + moov(atrak()),
           "squeezed.mov": FTYP + box(b"moov", box(b"cmov", b"\0" * 40)),
           "no header.mov": FTYP + box(b"mdat", DATA)}
    for name, data in bad.items():
        p = work / name
        p.write_bytes(data)
        try:
            video.facts(p)
            check(f"{name}: refused", False, "read as a video")
        except video.NotAVideo as e:
            check(f"{name}: refused in plain words ({e})", str(e) and "/" not in str(e) and "\\" not in str(e), str(e))
        except Exception as e:  # noqa: BLE001
            check(f"{name}: refused in plain words", False, f"{type(e).__name__}: {e}")
    try:
        video.facts(work / "not there.mov")
        check("a missing file: refused", False)
    except video.NotAVideo as e:
        check(f"a missing file: refused in plain words ({e})", "\\" not in str(e) and "/" not in str(e), str(e))

    # ---- 4. stills and the copy where there is no AVFoundation
    pc_like = not video.avfoundation_here()
    if not pc_like:
        os.environ[video.NO_AV] = "1"             # a Mac answers the way a PC does
    try:
        r = video.stills(end, [1, 2], work / "looks")
        check("stills on this computer without AVFoundation: the named gap's words, and no folder made",
              r == {"ok": False, "state": "pc", "words": this_computer.NO_PREVIEW} and not (work / "looks").exists(), r)
        r = video.preview_copy(end, work / "previews" / "preview.mp4")
        check("the copy too: the same words, nothing made", r.get("state") == "pc" and not (work / "previews").exists(), r)
        hevc = write(work, "iphone hevc.mov", FTYP, box(b"mdat", DATA), moov(vtrak(codec=b"hvc1", conf=hvcc(2, 1, 10))))
        was = this_computer.WINDOWS
        this_computer.WINDOWS = True              # how a PC answers an HEVC video (decision 11)
        try:
            r = video.stills(hevc, [1], work / "looks")
            r2 = video.preview_copy(hevc, work / "previews" / "preview.mp4")
        finally:
            this_computer.WINDOWS = was
        check("an HEVC video on a PC: this_computer.HEVC_HELP, nothing made",
              r == {"ok": False, "state": "hevc_pc", "words": this_computer.HEVC_HELP} and r2.get("state") == "hevc_pc"
              and not (work / "looks").exists() and not (work / "previews").exists(), (r, r2))
        r = video.stills(work / "random bytes.mov", [1], work / "looks")
        check("stills of a non-video: plain words", r.get("state") == "failed" and "/" not in r.get("words", ""), r)
    finally:
        os.environ.pop(video.NO_AV, None)
    for name in ("NO_PREVIEW", "HEVC_HELP", "NO_LOOK_PC", "WATCH_PC_HTML", "NOT_LOOKED_PC_HTML", "MOMENTS_PC", "NO_LOOK_CHAT"):
        words = getattr(this_computer, name, "")
        check(f"this_computer.{name} names nothing Mac-only (no Mac, Finder, QuickTime)",
              words and not any(w in words for w in ("Mac", "Finder", "QuickTime")), words)
        # v19 review: the first drafts said "The moments and your reel still work" where a PC can make no moment,
        # promised the HEVC extensions would help (no PC route plays anything yet but H.264), and kept "tap a still"
        check(f"this_computer.{name} promises nothing a PC can't do yet", not any(w in words for w in (
              "still work", "Video Extensions", "tap a still", "I find", "look through it")), words)
    check("mac_javascript answers None on a PC, and runs on a Mac",
          (this_computer.mac_javascript("function run(a){return 'hi'}") is None) == (not this_computer.MAC))
    check("PC_ADDON stays None (decision 11: nothing asked for up front)", video.PC_ADDON is None)

    # ---- 5. the small things
    f1 = video.fresh_folder(work / "footage", "look")
    (f1 / "000001.jpg").write_bytes(b"x")
    f2 = video.fresh_folder(work / "footage", "look")
    f3 = video.fresh_folder(work / "footage", "CON")
    check("a fresh folder for every look: 'look', then 'look 2'; the first left as it was",
          (f1.name, f2.name) == ("look", "look 2") and (f1 / "000001.jpg").read_bytes() == b"x" and not any(f2.iterdir()))
    check("a look named with a word Windows keeps for itself is made safe on both computers", f3.name == "CON_", f3.name)
    k1 = video.key(end)
    copy = work / "same.MOV"
    shutil.copy2(end, copy)
    check("a video's key: 12 letters and numbers, the same each time, another for another name",
          len(k1) == 12 and all(c in "0123456789abcdef" for c in k1) and video.key(end) == k1 and video.key(copy) != k1)
    want = datetime(2026, 11, 6, 18, 12, 33, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    check("recording times as local time: a zone with or without a colon, Z, a camera's, junk",
          video.recorded_local(phone) == want and video.recorded_local("2026-11-06T10:12:33-08:00") == want
          and video.recorded_local("2026-11-06T18:12:33Z") == want
          and video.recorded_local("2026:11:06 10:12:33") == datetime(2026, 11, 6, 10, 12, 33)
          and video.recorded_local("yesterday") is None and video.recorded_local({"recorded": ""}) is None)
    hop = int(video.LOUD_RATE * video.LOUD_STEP)
    quiet, loud = [300, -300] * (hop // 2), [16000, -16000] * (hop // 2)
    lv = video.levels(quiet * 6 + loud * 6)
    check("her measure: -40.8 dB quiet, -6.2 dB loud, a level every half second",
          len(lv) == 12 and lv[0] == -40.8 and lv[-1] == -6.2, lv)
    check("a last half second 90% there counts; less does not (NEAR_FULL)",
          len(video.levels(quiet * 2 + quiet[:int(hop * 0.9)])) == 3 and len(video.levels(quiet * 2 + quiet[:int(hop * 0.8)])) == 2)
    lm = video.loud_moments(video.levels(quiet * 8 + loud * 4))
    check("her loud moments: the room is the middle level; one moment, at 4 s, 34.6 dB above the room",
          [(x["at"], x["above_room"]) for x in lm] == [(4.0, 34.6)], lm)
    check("no levels: no loud moments", video.loud_moments([]) == [])

    # ---- the sound of a long video on a PC (v19 review, Nov 7): read where it is (never copied into the temp folder,
    # where a phone's video would be gigabytes), and brought down to 8,000 a second, one channel, as it is read
    import array
    import sound
    rng = random.Random(3)
    raw = array.array("h", (rng.randint(-20000, 20000) for _ in range(2 * 48000 * 3)))       # 3 s, two channels, 48 kHz
    whole = sound._resample(sound._to_mono16(raw.tobytes(), "s16le", 2), 48000, 8000)
    sq = sound._Squash(8000)
    b = raw.tobytes()
    at = 0
    for n in (4096, 1000, 77777, 4, 32768, len(b)):                                         # pieces of every size
        n -= n % 4
        sq.add(b[at:at + n], "s16le", 2, 48000)
        at += n
    check("the sound brought down piece by piece is the same as brought down whole (%d samples)" % len(whole),
          abs(len(sq.out) - len(whole)) <= 1 and list(sq.out[:len(whole) - 1]) == list(whole[:len(sq.out) - 1]),
          (len(sq.out), len(whole)))
    vid = write(work, "phone video.MOV", FTYP, box(b"mdat", DATA), std)
    seen = {}
    real = (sound.WINDOWS, sound._afconvert_ok, sound._ffmpegs, sound._mf_read_pcm, shutil.copyfile)

    def fake_mf(path, longest, on_chunk=None):
        seen.update(path=path, longest=longest, streamed=on_chunk is not None)
        piece = array.array("h", [12000, -12000] * 4800).tobytes()                            # 0.1 s, two channels
        if on_chunk is None:
            return piece * 30, "s16le", 2, 48000
        for _ in range(30):
            on_chunk(piece, "s16le", 2, 48000)
        return None, "s16le", 2, 48000

    def spy_copy(a, b_, **k):
        seen.setdefault("copied", []).append(str(a))
        return real[4](a, b_, **k)
    sound.WINDOWS, sound._afconvert_ok, sound._ffmpegs, sound._mf_read_pcm = True, (lambda: False), (lambda: []), fake_mf
    shutil.copyfile = spy_copy
    try:
        a, how = sound.decode(vid, rate=8000, video=True)
    finally:
        sound.WINDOWS, sound._afconvert_ok, sound._ffmpegs, sound._mf_read_pcm, shutil.copyfile = real
    check("a phone's .MOV on a PC: opened where it is, never copied, read up to an hour, brought down as it is read",
          seen.get("path") == str(vid) and not seen.get("copied") and seen.get("longest") == sound.LONGEST_VIDEO
          and seen.get("streamed") and how == "windows" and a is not None and abs(len(a) - 24000) <= 1, (seen, how, a and len(a)))
    fx = ROOT / "tests" / "fixtures" / "loud-tone-3s.mp4"
    seen.clear()
    shutil.copyfile = spy_copy
    try:
        db, how = video.loudness(fx)
    finally:
        shutil.copyfile = real[4]
    check(f"a real 3-second clip ({fx.name}, ours): its sound read ({how}), quiet for 1.5 s and then loud, and never copied",
          db is not None and len(db) == 6 and db[3] - db[2] > 20 and not seen.get("copied"), (db, how, seen))

    ok = all(results)
    print(f"\n{sum(results)} of {len(results)} passed.")
    if ok:
        shutil.rmtree(work, ignore_errors=True)
    else:
        print("Kept for a look:", work)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
