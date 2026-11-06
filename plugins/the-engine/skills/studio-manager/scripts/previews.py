#!/usr/bin/env python3
"""Pull a few small JPEG previews out of a session's RAW files, spread evenly
across the shoot, into _studio/previews/. On a Mac the Mac's built-in `sips`
makes them, so nothing has to be installed; on a PC, pictures.py takes the JPEG
the camera stored inside each RAW and sizes it with Pillow. Reads the verified
copy, never the card.

    python3 previews.py "<session folder>" [--count 12] [--size 1000]

These are teasers for the morning report and the raw material for contact
sheets. Picking the *good* ones is a later step (Claude on the shortlist).
Exit codes: 0 done, 1 this computer cannot make previews yet (it says why; nothing written).
"""
import argparse
import sys
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()

RAW = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}


def media_files(session_dir):
    files = [p for p in Path(session_dir).rglob("*")
             if p.is_file() and p.suffix.lower() in RAW and "_studio" not in p.parts and not p.name.startswith(".")]
    return sorted(files, key=lambda p: (p.parent.as_posix().lower(), p.name.lower()))


def spread(items, count):
    """count items spread evenly across the list, first and last included."""
    if len(items) <= count:
        return list(items)
    step = (len(items) - 1) / (count - 1)
    return [items[round(i * step)] for i in range(count)]


def make_preview(src, dst, size):
    return pictures.make_jpeg(src, dst, size, 82)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--size", type=int, default=1000, help="longest edge in pixels")
    a = ap.parse_args()

    ok, words = pictures.ready()
    if not ok:
        # Nothing is made (not even the folder), so the next run, once the add-on is in, makes them all.
        print(f"STOP: {words}", flush=True)
        return 1
    out = Path(a.session) / "_studio" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    picks = spread(media_files(a.session), a.count)
    made = []
    for p in picks:
        dst = out / (p.stem + ".jpg")
        if dst.exists() or make_preview(p, dst, a.size):
            made.append(dst)
        else:
            why = pictures.why_not(p)
            print(f"could not read {p.name}" + (f": {why}" if why else ""), file=sys.stderr)
    print(f"{len(made)} previews in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
