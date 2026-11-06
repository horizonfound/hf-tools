#!/usr/bin/env python3
"""What this computer's own decoder makes of the MP3 and M4A test songs, with nothing extra installed.

Information only. GitHub runs it on a real Windows machine as a step that may fail without failing the
check (.github/workflows/check-pc.yml), because Windows' own Media Foundation route in sound.py has never run
on a real PC and this is the first look at it. Both ffmpegs are switched off (ASSISTANT_NO_FFMPEG=1), so on
Windows it is Media Foundation that answers; on a Mac it is the Mac's own afconvert.

    python3 tests/fixtures/decode_report.py

For each song: what kind it really is, its length read from the file, then sound.decode: which way heard
it, how many seconds came back against the true length, how loud, how long it took, or the plain words for
why not. Standard library only. Exit 0 when every MP3 and M4A was heard at about the right length.
"""
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"))
os.environ["ASSISTANT_NO_FFMPEG"] = "1"     # nothing extra: neither an ffmpeg on the PATH nor imageio-ffmpeg's own
import sound  # noqa: E402

TRUE = {"click-100bpm.m4a": 10.0, "click-100bpm-m4a-named.mp3": 10.0, "click-100bpm-cbr.mp3": 10.031,
        "click-100bpm-vbr.mp3": 10.031, "click-100bpm-cbr-noheader.mp3": 10.031, "click-100bpm-vbr-noheader.mp3": 10.031}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print(f"{platform.platform()}, Python {sys.version.split()[0]}")
    print("ffmpeg switched off; the Mac's afconvert " + ("is here" if sound._afconvert_ok() else "is not here")
          + ("; Windows' own Media Foundation is tried" if sound.WINDOWS else "") + "\n")
    good = 0
    for name, want in TRUE.items():
        path = HERE / name
        t0 = time.monotonic()
        a, how = sound.decode(path)
        took = time.monotonic() - t0
        length = sound.duration(path)
        head = f"{name}: really {sound.real_kind(path)}, length from the file " + (f"{length:.4f} s" if length else "unknown")
        if a is None:
            print(f"NOT HEARD  {head}\n           {how}  ({took:.2f} s)")
            continue
        secs = len(a) / 11025
        peak = max(max(a), -min(a)) if len(a) else 0
        ok = abs(secs - want) <= 0.15 and peak > 1000
        good += ok
        print(f"{'HEARD' if ok else 'ODD  '}      {head}\n           by {how}: {secs:.4f} s back (true {want} s, "
              f"{(secs - want) * 1000:+.0f} ms), loudest {peak}, took {took:.2f} s")
    print(f"\n{good} of {len(TRUE)} heard at about the right length.")
    return 0 if good == len(TRUE) else 1


if __name__ == "__main__":
    sys.exit(main())
