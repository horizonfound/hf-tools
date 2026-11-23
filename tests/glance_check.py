#!/usr/bin/env python3
"""The glance before a backup (Dustin, Nov 11): from the second backup on, the usual is shown as a few short
lines, with Looks good or Change something. This checks the lines `studio_file.py glance` prints, on a pretend
setup in a scratch folder (never the real ~/.studio).

    python3 tests/glance_check.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402

FAILED = []


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {detail}"), flush=True)
    if not ok:
        FAILED.append(what)


def main():
    work = Path(tempfile.mkdtemp(prefix="glance-check-"))
    try:
        home, drive, second = work / "home", work / "Photo Shoots", work / "Second"
        for d in (home, drive, second):
            d.mkdir()
        env = {"STUDIO_HOME": str(home)}
        code, out = t.run("studio_file.py", "glance", env=env)
        check("with no setup yet there is nothing to glance at, and it says so", code == 0 and "No setup yet" in out, out)
        t.run("studio_file.py", "set", "--drive", drive, "--no-second", "--offered", "2", "--file-names", "shoot", env=env)
        code, out = t.run("studio_file.py", "glance", env=env)
        lines = out.split("THE USUAL")[-1].split("ONE LINE")[0].strip().splitlines()[1:]
        one = out.split("ONE LINE (put this in the question itself):")[-1].strip()
        check("the drive, the second copy asked for each time (Nicole, Nov 23), the folder naming and the photo naming, one short line each",
              len(lines) == 4 and lines[0].startswith("Photos go onto Photo Shoots")
              and lines[1] == "A second copy is yours to ask for after each backup, on its report"
              and "2026-10-18 Smith Family" in lines[2] and "named after the shoot" in lines[3], out)
        check("every line is short and plain: no path, no code marks, no setting names",
              all(len(x) <= 90 and "/" not in x.replace("Dustin / ", "") and "`" not in x and "{" not in x for x in lines), str(lines))
        check("the same thing as one line for the question, ending in a full stop",
              one.startswith("Photos onto Photo Shoots") and one.endswith(".") and one.count(";") == 3 and "\n" not in one, one)
        # a second copy, their own camera names, a tone, a posting rhythm
        t.run("studio_file.py", "set", "--second", second, "--file-names", "original", env=env)
        t.run("client_note.py", "setup", "--tone", "warm", "--sign-off", "xo, Nicole", env=env)
        t.run("posting_queue.py", "interval", "3 a week", env=env)
        before = (home / "studio.json").read_bytes()
        code, out = t.run("studio_file.py", "glance", env=env)
        check("the camera's own names and the posting rhythm show; a second drive saved by an earlier version is no longer "
              "said to get a copy by itself",
              "A second copy goes onto" not in out and "A second copy is yours to ask for after each backup, on its report" in out
              and "Photos keep the camera's own names" in out and "Posts lined up at 3 a week" in out, out)
        check("notes to clients are not in the glance any more (taken out Nov 23), though how they write is still on file",
              "lient note" not in out and "xo, Nicole" in (home / "studio.json").read_text(encoding="utf-8"), out)
        check("looking changes nothing that is remembered", (home / "studio.json").read_bytes() == before)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
