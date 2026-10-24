#!/usr/bin/env python3
"""The whole night, one command. Runs every step in order and stops only
when something is wrong or when Claude's one look is needed:

  copy + verify (backup.py)  ->  index  ->  groups  ->  contact sheet
  ->  [Claude reads the sheet, writes shoots.json]  ->  sort with the
  suggested names  ->  the morning report (verdict, numbers, the shoots
  with their previews and name boxes, where the photos are)

Safe to run again at any point; each step is skipped once its result exists.

    python3 night.py --source /Volumes/EOS_DIGITAL --dest "/Volumes/Drive" --name "Saturday card"
    python3 night.py --session "<session folder>"          continue a session already started

Exit codes: 0 done · 1 problems (read the report) · 2 stop (missing source
or drive) · 3 paused (run again) · 4 needs Claude's look (read
_studio/groups-sheet.png, write _studio/shoots.json, run again).
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def say(msg):
    print(msg, flush=True)


def run(script, *args):
    """Run one of the scripts beside this one, streaming its output; return its exit code."""
    return subprocess.run([sys.executable, str(HERE / script), *map(str, args)]).returncode


def fresh(a, b):
    """True when file a exists and is newer than file b (or b is missing)."""
    return a.exists() and (not b.exists() or a.stat().st_mtime >= b.stat().st_mtime)


def check_shoots(studio):
    """shoots.json must give every group to exactly one shoot, with a suggested name each."""
    groups = [g["id"] for g in json.loads((studio / "groups.json").read_text())["groups"]]
    try:
        shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    except (ValueError, KeyError, OSError) as e:
        return f"shoots.json could not be read ({e.__class__.__name__})"
    seen = []
    for s in shoots:
        if not s.get("id") or not s.get("suggested") or not s.get("groups"):
            return f"a shoot is missing id, suggested name or groups: {s}"
        seen += s["groups"]
    missing = [g for g in groups if g not in seen]
    doubled = [g for g in seen if seen.count(g) > 1]
    if missing or doubled:
        return f"groups not assigned: {missing}; assigned twice: {doubled}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--dest", help="the session drive or folder")
    ap.add_argument("--name")
    ap.add_argument("--second", default=None)
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--session", help="an existing session folder, to continue")
    ap.add_argument("--gap", default="15", help="quiet minutes that start a new group")
    ap.add_argument("--budget", default=None, help="seconds the copy may run before pausing cleanly")
    ap.add_argument("--no-open", action="store_true", help="don't open the first look when done (the Claude app shows it in its own pane)")
    a = ap.parse_args()

    if a.session:
        session = Path(a.session).expanduser().resolve()
    elif a.source and a.dest and a.name:
        session = Path(a.dest).expanduser() / f"{a.date} {a.name}"
    else:
        sys.exit("usage: --source --dest --name, or --session <folder>")
    studio = session / "_studio"

    # 1. copy and verify (backup.py also builds the index and the report page)
    manifest = studio / "manifest.json"
    done = False
    if manifest.exists():
        m = json.loads(manifest.read_text())
        done = not m.get("problems") and all(v.get("dest", {}).get("ok") for v in m.get("files", {}).values()) and bool(m.get("files"))
    if not done:
        if not (a.source and a.dest and a.name):
            sys.exit(f"STOP: {session} is not fully backed up, and I need --source, --dest and --name to continue it.")
        say("1. Copying and verifying")
        args = ["--source", a.source, "--dest", a.dest, "--name", a.name, "--date", a.date]
        if a.second:
            args += ["--second", a.second]
        if a.budget:
            args += ["--budget", a.budget]
        code = run("backup.py", *args)
        if code != 0:
            sys.exit(code)  # 1 problems, 2 stop, 3 paused: backup.py already said why
    else:
        say("1. Already copied and verified")

    # 2. the index (backup.py makes it; make sure)
    if not (studio / "index.json").exists():
        say("2. Indexing")
        if run("index.py", session) != 0:
            sys.exit(1)
    else:
        say("2. Index is there")

    # a dozen previews spread across the card, for the report's teasers (seconds)
    if not (studio / "previews").is_dir():
        run("previews.py", session, "--count", "12")

    # 3. groups and the sheet
    if not fresh(studio / "groups.json", studio / "index.json"):
        say("3. Finding the shoots")
        if run("groups.py", session, "--gap", a.gap) != 0:
            sys.exit(1)
    else:
        say("3. Groups are there")
    if not fresh(studio / "groups-sheet.png", studio / "groups.json"):
        if run("sheet.py", session) != 0:
            sys.exit(1)

    # 4. Claude's one look
    if not (studio / "shoots.json").exists():
        groups = json.loads((studio / "groups.json").read_text())["groups"]
        say("\n4. NEEDS A LOOK. Read this image: " + str(studio / "groups-sheet.png"))
        say("   One row per group, in this order:")
        for i, g in enumerate(groups, 1):
            gap = f"after a {g['gap_before_min']} min gap" if g.get("gap_before_min") is not None else "first of the day"
            say(f"   {i:02d} {g['id']}  {g['start'][:16].replace('T', ' ')} to {g['end'][11:16]}  {g['count']:>5} photos  {gap}")
        say("   Decide which rows are one shoot (same people, same place, same day) and write " + str(studio / "shoots.json") + ":")
        say('   {"decided_by": "Claude, from the contact sheet", "shoots": [{"id": "s1", "suggested": "<place or subject>, <Mon D, YYYY>",'
            ' "groups": ["g01", "g02"], "photos": 1234, "recap": "<two or three warm sentences about what is in it>", "why": "<one line>"}, ...]}')
        say("   Then run this command again.")
        sys.exit(4)
    err = check_shoots(studio)
    if err:
        say(f"\n4. shoots.json needs fixing: {err}")
        sys.exit(4)
    say("4. Shoots decided")

    # 5. sort with the names there are (hers, or the suggested ones)
    index = json.loads((studio / "index.json").read_text())
    if any(not p.get("original") for p in index["photos"] if p.get("taken")):
        say("5. Sorting into folders")
        if run("sort.py", session) != 0:
            sys.exit(1)
    else:
        say("5. Already sorted")

    # 6. the pages
    say("6. Writing the report")
    if run("first_look.py", session) != 0 or run("report_page.py", session) != 0:
        sys.exit(1)
    say(f"\nDone. Report: {studio / 'report.html'}")
    # so there is something nice on the screen when she comes back
    if not a.no_open:
        opener = {"darwin": ["open"], "win32": ["cmd", "/c", "start", ""], "linux": ["xdg-open"]}.get(sys.platform)
        if opener:
            subprocess.run([*opener, str(studio / "report.html")], check=False)


if __name__ == "__main__":
    main()
