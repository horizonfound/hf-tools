#!/usr/bin/env python3
"""The Assistant by Horizon Found. Finds songs on this computer the reel can cut to.

  python3 find_music.py <folder> [<folder> ...] [--newest 15]

Looks through the folders you give it (connected folders only), newest first, and lists audio files with their
length. Point it at the session folder, a Music folder, or CapCut's folder after you picked a song in CapCut
(CapCut keeps a copy of any song you add to a project). Prints a numbered list; nothing is copied or changed.
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AUDIO = {".mp3", ".m4a", ".wav", ".aac", ".aiff", ".aif", ".flac", ".ogg", ".opus"}


def dur(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                           capture_output=True, text=True, timeout=20)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--newest", type=int, default=15)
    a = ap.parse_args()
    found = []
    for f in a.folders:
        root = Path(f).expanduser()
        if not root.exists():
            print(f"(no folder at {root})")
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "_assistant")]
            for n in filenames:
                p = Path(dirpath) / n
                if p.suffix.lower() in AUDIO and not n.startswith("."):
                    try:
                        found.append((p.stat().st_mtime, p))
                    except OSError:
                        pass
    if not found:
        print("No songs found in those folders. Drop a song into the session folder, pick one in CapCut and point me at CapCut's folder, or say 'no song' and I'll cut at an even pace.")
        sys.exit(1)
    found.sort(reverse=True)
    print(f"{len(found)} song file(s), newest first:")
    for i, (m, p) in enumerate(found[: a.newest], 1):
        d = dur(p)
        age = time.strftime("%b %d", time.localtime(m))
        print(f"  {i:2}  {p.name:45} {d:5.0f}s   {age}   {p.parent}")
    print("Tell me the number, or the name.")


if __name__ == "__main__":
    main()
