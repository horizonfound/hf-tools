#!/usr/bin/env python3
"""The last step of the night: the shoots go where the photographer said, and the
day folder goes away.

During the night everything lands in one day folder ("2026-10-24 saturday card")
so a copy can be paused, resumed and checked as one job. Once every file is
copied, verified, sorted and named, that folder has done its job. Settling:

  - moves each shoot folder up into the place they chose (the drive, or the
    folder on it), next to their other shoots
  - moves the night's records (_studio: the checklist of every file, the
    report, the logs) to a hidden folder there, <their place>/.studio/<night>,
    so the report, renaming and the archive keep working
  - removes the day folder once it is empty (an empty folder only; anything
    else in it and it stays)

Same promises as everything else: only the copy on their drive, never the card;
moves on the same drive only (a rename, never copy-and-delete); nothing
overwritten (if a folder by the same name is already there, nothing moves and
it says why); every move written to settle-log.json first; every photo proved
to be the same file at its new place (its identity on the drive: inode, size,
modified time). Safe to run again at any point: a cut-off settle is finished.

    python3 settle.py "<the day folder>"            settle it
    python3 settle.py "<the day folder>" --dry-run  show what would move

Exit codes: 0 settled (or already) · 1 problems · 6 left together on purpose
(a name clash, something unexpected in the folder, or the night not finished).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import RECORDS, locate  # noqa: E402


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def leave(why):
    say(f"Left together, on purpose: {why}")
    sys.exit(6)


def shoot_folders(studio):
    """The top-level folders the sorter made: one per shoot, from where the index says the photos are."""
    index = json.loads((studio / "index.json").read_text())
    tops = {Path(p["file"]).parts[0] for p in index["photos"] if p.get("original") and len(Path(p["file"]).parts) > 1}
    return sorted(tops)


def identity(root, folders):
    out = {}
    for name in folders:
        for dirpath, _, files in os.walk(root / name):
            for fn in files:
                p = Path(dirpath) / fn
                st = os.stat(p)
                out[p.relative_to(root).as_posix()] = [st.st_ino, st.st_size, st.st_mtime_ns]
    return out


def gates(studio):
    """The night must be finished and clean before anything moves."""
    sl = studio / "sort-log.json"
    if not sl.exists():
        return "the photos have not been sorted yet"
    log = json.loads(sl.read_text())
    if log.get("problems"):
        return "the sort reported problems"
    if log.get("verified", 0) < len(log.get("moves", [])):
        return "not every sorted photo has been checked"
    rl = studio / "rename-log.json"
    if rl.exists():
        for e in json.loads(rl.read_text()).get("renames", []):
            if not e.get("finished") or e.get("problems"):
                return "a rename is unfinished or had problems"
    return None


def plan(session, studio):
    parent = session.parent
    why = gates(studio)
    if why:
        leave(why)
    folders = shoot_folders(studio)
    if not folders:
        leave("no shoot folders found")
    extras, hidden = [], []
    for x in session.iterdir():
        if x.name == "_studio" or x.name in folders:
            continue
        (hidden if x.name.startswith(".") and x.is_file() else extras).append(x.name)
    if extras:
        leave(f"there is something else in {session.name}: {', '.join(extras[:5])}")
    clash = [f for f in folders if (parent / f).exists()]
    if clash:
        leave(f"a folder called {clash[0]} is already in {parent.name or parent}")
    if os.stat(session).st_dev != os.stat(parent).st_dev:
        leave("the day folder is on a different drive from its parent")
    records = parent / RECORDS / session.name
    n = 2
    while records.exists():
        records = parent / RECORDS / f"{session.name} {n}"
        n += 1
    return {"session_was": str(session), "parent": str(parent), "records": str(records), "folders": folders,
            "hidden_files": hidden, "ident": identity(session, folders), "status": "planned",
            "started": datetime.now().isoformat(timespec="seconds"), "problems": []}


def finish(log, log_path):
    """Everything after the shoot folders are up: records, the empty day folder, the check, the ledger."""
    session, parent, records = Path(log["session_was"]), Path(log["parent"]), Path(log["records"])
    studio_now = session / "_studio"
    log["problems"] = []  # this part is checked afresh on every run
    # the records move (one rename); the manifest learns where the photos are now
    if studio_now.exists() and not records.exists():
        m = json.loads((studio_now / "manifest.json").read_text())
        m.setdefault("dest_was", m.get("dest"))
        m["dest"] = str(parent)
        (studio_now / "manifest.json").write_text(json.dumps(m, indent=1))
        records.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.system(f'attrib +h "{records.parent}"')
        log["status"] = "records moving"
        log_path.write_text(json.dumps(log, indent=1))
        os.rename(studio_now, records)
    log_path = records / "settle-log.json"
    # the day folder: Finder's hidden notes are set aside with the records, then the empty folder comes down
    if session.exists():
        for x in list(session.iterdir()):
            if x.is_file() and x.name.startswith("."):
                dst = records / "from-the-card" / x.name
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(x, dst)
        try:
            session.rmdir()  # refuses if anything is still in it; then it stays
        except OSError:
            left = [x.name for x in session.iterdir()]
            log["problems"].append(f"the day folder still has something in it, so it stays: {', '.join(left[:5])}")
    # every photo: the same file, at its new place
    checked = 0
    for rel, want in log["ident"].items():
        p = parent / rel
        try:
            st = os.stat(p)
        except OSError:
            log["problems"].append(f"not where it should be after the move: {rel}")
            continue
        if [st.st_ino, st.st_size, st.st_mtime_ns] != want:
            log["problems"].append(f"not the same file after the move: {rel}")
            continue
        checked += 1
    log["checked"] = checked
    log["status"] = "done" if not log["problems"] else "done with problems"
    log["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1))
    if not log["problems"]:
        (records / "settled.json").write_text(json.dumps(
            {"session_was": log["session_was"], "folders": log["folders"], "when": log["finished"], "checked": checked}, indent=1))
        # the card ledger now points at the records where they are now
        try:
            import cards
            ledger = cards.load()
            for entry in ledger.get("cards", {}).values():
                for s in entry.get("sessions", []):
                    if s.get("folder") == log["session_was"]:
                        s["folder"] = str(records)
            cards.save(ledger)
        except Exception as e:  # noqa: BLE001  the ledger is a convenience; the photos are already settled
            say(f"(the card ledger could not be updated: {e.__class__.__name__})")
    return records, checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session", help="the day folder (or where it was)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root, studio = locate(a.session)
    if (studio / "settled.json").exists():
        say(f"Already settled: the shoots are in {root}.")
        return
    log_path = studio / "settle-log.json"
    if log_path.exists():
        log = json.loads(log_path.read_text())  # a settle that was cut off: finish it
        say("Finishing a settle that was cut off.")
    else:
        if studio.name != "_studio":
            sys.exit("STOP: these records were moved without a settle log; will not guess.")
        log = plan(root, studio)
        session, parent = root, root.parent
        say(f"Moving {len(log['folders'])} shoot folder{'s' if len(log['folders']) != 1 else ''} into {parent}:")
        for f in log["folders"]:
            say(f"  {f}")
        say(f"  ({len(log['ident']):,} files; the day folder {session.name} goes once it is empty)")
        if a.dry_run:
            say("Dry run. Nothing moved.")
            return
        log_path.write_text(json.dumps(log, indent=1))  # on record before anything moves

    session, parent = Path(log["session_was"]), Path(log["parent"])
    if log["status"] == "planned":
        for f in log["folders"]:
            src, dst = session / f, parent / f
            if src.exists() and not dst.exists():
                os.rename(src, dst)  # the whole shoot folder, in one step
            elif dst.exists() and not src.exists():
                continue  # moved before the cut-off
            else:
                log["problems"].append(f"{f}: both or neither of {src} and {dst} exist; left as they are")
        if log["problems"]:
            log_path.write_text(json.dumps(log, indent=1))
            say("STOP:")
            for p in log["problems"]:
                say(f"  - {p}")
            sys.exit(1)
        log["status"] = "folders moved"
        log_path.write_text(json.dumps(log, indent=1))

    records, checked = finish(log, log_path)
    if log["problems"]:
        say("PROBLEMS (every move is in settle-log.json):")
        for p in log["problems"][:10]:
            say(f"  - {p}")
        sys.exit(1)
    say(f"Settled. {len(log['folders'])} shoot folders in {parent}, {checked:,} files checked, nothing overwritten.")


if __name__ == "__main__":
    main()
