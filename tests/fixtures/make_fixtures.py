#!/usr/bin/env python3
"""Makes the test songs in this folder. Every sound is made here from sine waves and a fixed pseudo-random
hiss: a click track at 100 beats a minute, 4 to a bar, 10 seconds. No recorded or copyrighted audio.

    python3 tests/fixtures/make_fixtures.py [<folder>]      (default: this folder)

Needs the Mac's own afconvert (for the M4A) and ffmpeg with libmp3lame (for the MP3s). Only run when the
fixtures have to be remade; the made files are kept in the repository.
"""
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

BPM, BEATS_IN_BAR, SECONDS, FIRST_BEAT = 100.0, 4, 10.0, 0.25


def signal(rate):
    """The click track as 16-bit numbers at `rate` samples a second."""
    n = int(SECONDS * rate)
    out = [0.0] * n
    period = 60.0 / BPM
    seed = 12345

    def add(at, length, fn):
        s = int(at * rate)
        for i in range(int(length * rate)):
            if s + i < n:
                out[s + i] += fn(i / rate)

    k = 0
    while FIRST_BEAT + k * period < SECONDS:
        t0 = FIRST_BEAT + k * period
        pos = k % BEATS_IN_BAR
        if pos in (0, 2):                                   # a kick on 1 and 3, louder on 1
            amp = 0.85 if pos == 0 else 0.5
            add(t0, 0.12, lambda t, a=amp: a * math.exp(-t * 30) * math.sin(2 * math.pi * (55 + 90 * math.exp(-t * 40)) * t))
        hz, amp = (1600.0, 0.55) if pos == 0 else (1000.0, 0.35)
        add(t0, 0.025, lambda t, h=hz, a=amp: a * math.exp(-t * 160) * math.sin(2 * math.pi * h * t))
        for i in range(int(0.015 * rate)):                  # a soft hiss on the "and" of each beat
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            j = int((t0 + period / 2) * rate) + i
            if j < n:
                out[j] += 0.10 * math.exp(-i / rate * 200) * ((seed / 0x7FFFFFFF) * 2 - 1)
        k += 1
    return [max(-32768, min(32767, int(v * 32767))) for v in out]


def write_wav(path, rate, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<%dh" % len(samples), *samples))


def ext80(x):
    """An 80-bit IEEE extended number, as AIFF writes its sample rate."""
    e = int(math.floor(math.log2(x)))
    mant = int(x / 2.0 ** e * (1 << 63))
    return struct.pack(">HQ", e + 16383, mant)


def write_aiff(path, rate, samples):
    data = struct.pack(">%dh" % len(samples), *samples)
    comm = struct.pack(">hIh", 1, len(samples), 16) + ext80(rate)
    ssnd = struct.pack(">II", 0, 0) + data
    body = b"AIFF" + b"COMM" + struct.pack(">I", len(comm)) + comm + b"SSND" + struct.pack(">I", len(ssnd)) + ssnd
    Path(path).write_bytes(b"FORM" + struct.pack(">I", len(body)) + body)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stderr}")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    work = Path(tempfile.mkdtemp())
    try:
        master = work / "master.wav"                         # 44.1 kHz, the rate real songs have
        write_wav(master, 44100, signal(44100))
        small = signal(11025)                                # 11,025 a second keeps the plain files small
        write_wav(out / "click-100bpm.wav", 11025, small)
        write_aiff(out / "click-100bpm.aiff", 11025, small)
        run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "48000", str(master), str(out / "click-100bpm.m4a")])
        lame = [ffmpeg, "-v", "error", "-y", "-i", str(master), "-c:a", "libmp3lame"]
        run(lame + ["-b:a", "48k", str(out / "click-100bpm-cbr.mp3")])
        run(lame + ["-q:a", "6", str(out / "click-100bpm-vbr.mp3")])
        run(lame + ["-b:a", "48k", "-write_xing", "0", str(out / "click-100bpm-cbr-noheader.mp3")])
        run(lame + ["-q:a", "6", "-write_xing", "0", str(out / "click-100bpm-vbr-noheader.mp3")])
        # MPEG-2 (22,050 a second, frames of 576 samples, the same length as LAME's delay): variable rate with a
        # Xing header, added Nov 6 when a review found Windows' trimming rule missed this shape
        run(lame + ["-ar", "22050", "-q:a", "6", str(out / "click-100bpm-22k-vbr.mp3")])
        # what CapCut's library songs look like: an M4A file with a .mp3 name
        shutil.copyfile(out / "click-100bpm.m4a", out / "click-100bpm-m4a-named.mp3")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for f in sorted(out.iterdir()):
        if f.suffix in (".wav", ".aiff", ".m4a", ".mp3"):
            print(f"{f.name}: {os.path.getsize(f) // 1024} KB")


if __name__ == "__main__":
    main()
