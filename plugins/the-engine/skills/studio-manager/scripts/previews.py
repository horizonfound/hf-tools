#!/usr/bin/env python3
"""Pull a few small JPEG previews out of a session's RAW files, spread evenly
across the shoot, into _studio/previews/. Uses the Mac's built-in `sips`, so
nothing has to be installed. Reads the verified copy, never the card.

    python3 previews.py "<session folder>" [--count 12] [--size 1000]

These are teasers for the morning report and the raw material for contact
sheets. Picking the *good* ones is a later step (Claude on the shortlist).
"""
import argparse
import subprocess
import sys
from pathlib import Path

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
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", "-Z", str(size), str(src), "--out", str(dst)],
                       capture_output=True, text=True)
    return r.returncode == 0 and dst.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--size", type=int, default=1000, help="longest edge in pixels")
    a = ap.parse_args()

    out = Path(a.session) / "_studio" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    picks = spread(media_files(a.session), a.count)
    made = []
    for p in picks:
        dst = out / (p.stem + ".jpg")
        if dst.exists() or make_preview(p, dst, a.size):
            made.append(dst)
        else:
            print(f"could not read {p.name}", file=sys.stderr)
    print(f"{len(made)} previews in {out}")


if __name__ == "__main__":
    main()
