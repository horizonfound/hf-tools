#!/usr/bin/env python3
"""posts.py bring says plainly when a folder has no finished photos (Dustin's first try, Nov 7: an empty folder
picked in the folder window got "Copied 0 finished photos ... every one checked").

    python3 tests/posts_bring_check.py

Works in a scratch folder only (STUDIO_HOME and the photos both there). Python 3.9, standard library."""
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts" / "posts.py"
fails = 0


def check(what, ok, detail=""):
    global fails
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else f"   [{detail}]"))
    fails += 0 if ok else 1


def tiny_jpeg(p):
    # the smallest JPEG header the copy accepts as a photo by its name; the bytes are never decoded here
    p.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9")


def run(env, *args):
    r = subprocess.run([sys.executable, str(POSTS), *args], capture_output=True, encoding="utf-8", env=env)
    return r.returncode, r.stdout + r.stderr


def main():
    work = Path(tempfile.mkdtemp(prefix="posts bring "))
    env = dict(os.environ, STUDIO_HOME=str(work / "studio"), HOME=str(work))
    code, out = run(env, "setup", "--home", str(work / "The Assistant"))
    check("a scratch Assistant folder is made", code == 0, out)

    empty = work / "Empty folder"
    empty.mkdir()
    code, out = run(env, "bring", str(empty))
    check("an empty folder: says it is empty and that nothing was copied",
          "No finished photos (JPEGs) in \"Empty folder\", so nothing was copied. The folder is empty." in out, out)
    check("...never 'Copied 0'", "Copied 0" not in out, out)
    check("...exit 3, as before", code == 3, code)

    raws = work / "Only TIFFs"
    raws.mkdir()
    (raws / "a.tif").write_bytes(b"II*\x00" + b"\x00" * 32)
    code, out = run(env, "bring", str(raws))
    check("a folder with only TIFFs: says what it has instead", "nothing was copied. It only has 1 TIFF." in out, out)
    check("...exit 3", code == 3, code)

    good = work / "Final Exports"
    good.mkdir()
    tiny_jpeg(good / "one.jpg")
    code, out = run(env, "bring", str(good))
    check("a folder with a JPEG: copied as before", "Copied 1 finished photo from \"Final Exports\" into the drop box" in out, out)
    check("...exit 0", code == 0, code)
    check("...the original is still there", (good / "one.jpg").is_file())

    print(f"\n{'All' if not fails else 'Not all'} passed ({fails} failed). Scratch: {work}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
