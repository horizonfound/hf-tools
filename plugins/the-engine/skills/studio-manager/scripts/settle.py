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
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import RECORDS, locate  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def leave(why):
    say(f"Left together, on purpose: {why}")
    sys.exit(6)


RECORDS_HELD = ("Another program had one of the backup's own files open for a moment (the virus checker, or something "
                "else reading it right then), so its records could not be put away yet. The photos are already in "
                "their folders and nothing is lost. Say go and I'll finish putting them away.")


def stopped(log, log_path, e, words):
    """A PC would not move a folder or a file because another program had something in it open
    (this_computer.HeldOpen). The log was written before every move and says how far it got, so running
    settle again finishes the job. Not a problem in the log: it is not one, and the next run starts clean."""
    log.setdefault("stops", []).append({"when": datetime.now().isoformat(timespec="seconds"), "status": log.get("status"),
                                        "file": e.src, "detail": str(e)})
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    what = "take down the empty folder" if e.src == e.dst else "move"
    say(f"Stopped part way: the {this_computer.COMPUTER} would not {what} {Path(e.src).name} ({e.cause}). "
        "Every move so far is in settle-log.json.")
    say(words)
    sys.exit(1)


def too_long(session, studio, parent, records, folders, ident):
    """Every place the settle would make that is too long on this PC (never on a Mac): their shoot folders and
    photos held to what File Explorer can open, the Assistant's own hidden records to what Python can."""
    theirs = [(parent / f, True) for f in folders] + [(parent / rel, False) for rel in ident]
    own = [(records, True)]
    for dirpath, _, names in os.walk(studio):
        here = records / Path(dirpath).relative_to(studio)
        own.append((here, True))
        own += [(here / n, False) for n in names]
    own += [(records / "from-the-card" / x.name, False) for x in session.iterdir()
            if x.is_file() and this_computer.housekeeping_file(x.name)]
    return ([str(p) for p, folder in theirs if this_computer.path_too_long(p, folder=folder)]
            + [str(p) for p, folder in own if this_computer.records_path_too_long(p, folder=folder)])


def shoot_folders(studio):
    """The top-level folders the sorter made: one per shoot, from where the index says the photos are."""
    index = json.loads((studio / "index.json").read_text(encoding="utf-8"))
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


def sha256_of(path, chunk=4 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def backup_hashes(records):
    """Where each photo is now -> the hash the backup recorded for it when it came off the card."""
    try:
        files = json.loads((records / "manifest.json").read_text(encoding="utf-8")).get("files", {})
        photos = json.loads((records / "index.json").read_text(encoding="utf-8")).get("photos", [])
    except (OSError, ValueError):
        return {}
    out = {}
    for p in photos:
        orig = p.get("original") or p.get("file")
        rec = files.get(orig) or {}
        if not rec and this_computer.WINDOWS:  # an older record spelled with backslashes; unproven on a real PC
            rec = files.get(str(orig).replace("/", "\\")) or {}
        if rec.get("sha256"):
            out[Path(p["file"]).as_posix()] = rec["sha256"]
    return out


def gates(studio):
    """The night must be finished and clean before anything moves."""
    sl = studio / "sort-log.json"
    if not sl.exists():
        return "the photos have not been sorted yet"
    log = json.loads(sl.read_text(encoding="utf-8"))
    if log.get("problems"):
        return "the sort reported problems"
    if log.get("verified", 0) < len(log.get("moves", [])):
        return "not every sorted photo has been checked"
    rl = studio / "rename-log.json"
    if rl.exists():
        for e in json.loads(rl.read_text(encoding="utf-8")).get("renames", []):
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
    shoots_here = set(folders) if this_computer.WINDOWS else {unicodedata.normalize("NFC", f) for f in folders}
    for x in session.iterdir():
        # A Mac's older drives (Mac OS Extended, like Big Kahuna) list an accented letter in pieces (the ñ of
        # "Muñoz" as n plus a separate mark) while the index holds it whole, so on a Mac the two spellings of
        # the same letter count as the same name (as rename_shoot.on_disk does). A PC keeps a name as written.
        if x.name == "_studio" or (x.name if this_computer.WINDOWS else unicodedata.normalize("NFC", x.name)) in shoots_here:
            continue
        (hidden if this_computer.housekeeping_file(x.name) and x.is_file() else extras).append(x.name)
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
    ident = identity(session, folders)
    long = too_long(session, studio, parent, records, folders, ident)
    if long:
        say(f"  too long for this {this_computer.COMPUTER}: {long[0]}" + (f" (and {len(long) - 1} more)" if len(long) > 1 else ""))
        leave(f"a photo's new place would be longer than this {this_computer.COMPUTER} allows (260 characters, counting "
              "the drive and every folder on the way), so the shoots stay together in the day folder")
    known = backup_hashes(studio)
    extra = {}
    for rel in ident:
        if rel not in known:
            try:
                extra[rel] = sha256_of(session / rel)
            except OSError:
                pass
    return {"session_was": str(session), "parent": str(parent), "records": str(records), "folders": folders,
            "hidden_files": hidden, "ident": ident, "extra_hash": extra, "status": "planned",
            "started": datetime.now().isoformat(timespec="seconds"), "problems": []}


def take_down_day_folder(session, records):
    """Set the computer's own notes aside with the records, then remove the emptied day folder. rmdir refuses a
    folder with anything else in it (OSError, and it stays); on a PC a folder window holding it is HeldOpen."""
    for x in list(session.iterdir()):
        if x.is_file() and this_computer.housekeeping_file(x.name):
            dst = records / "from-the-card" / x.name
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                this_computer.rename(x, dst)
    this_computer.rmdir(session)


DAY_FOLDER_LEFT = ("Everything is in its place and checked. One empty folder, {name}, is still there because a folder "
                   "window has it open. It holds nothing now, so you can delete it whenever you like.")


def finish(log, log_path):
    """Everything after the shoot folders are up: records, the empty day folder, the check, the ledger."""
    session, parent, records = Path(log["session_was"]), Path(log["parent"]), Path(log["records"])
    studio_now = session / "_studio"
    log["problems"] = []  # this part is checked afresh on every run
    log.pop("day_folder_left", None)
    # the records move (one rename); the manifest learns where the photos are now
    if studio_now.exists() and not records.exists():
        m = json.loads((studio_now / "manifest.json").read_text(encoding="utf-8"))
        m.setdefault("dest_was", m.get("dest"))
        m["dest"] = str(parent)
        (studio_now / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        records.parent.mkdir(parents=True, exist_ok=True)
        if this_computer.WINDOWS:  # a PC shows a folder whose name starts with a dot unless it is marked; a Mac hides it already
            this_computer.hide(records.parent)  # unproven on a real PC
        log["status"] = "records moving"
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
        try:
            this_computer.rename(studio_now, records)
        except this_computer.HeldOpen as e:
            stopped(log, log_path, e, RECORDS_HELD)
    log_path = records / "settle-log.json"
    # the day folder: the computer's hidden notes (Finder's .DS_Store; on a PC also Thumbs.db) are set aside
    # with the records, then the empty folder comes down
    if session.exists():
        try:
            take_down_day_folder(session, records)
        except this_computer.HeldOpen as e:
            # Only on a PC: a folder window (or File Explorer's own Thumbs.db) holds the emptied day folder. No photo
            # and none of the records are in it any more, so this is no reason to stop: the settle finishes, the
            # empty folder stays, and they are told so plainly (main). Stopping here would leave the records moved
            # and the backup not marked settled, which a later "backup now" does not pick up cleanly.
            log["day_folder_left"] = {"when": datetime.now().isoformat(timespec="seconds"), "detail": str(e)}
        except OSError:
            left = [x.name for x in session.iterdir()]
            log["problems"].append(f"the day folder still has something in it, so it stays: {', '.join(left[:5])}")
    # every photo: the same file, at its new place
    checked = hashed = 0
    hashes = None
    for rel, want in log["ident"].items():
        p = parent / rel
        try:
            st = os.stat(p)
        except OSError:
            log["problems"].append(f"not where it should be after the move: {rel}")
            continue
        if [st.st_ino, st.st_size, st.st_mtime_ns] != want or not want[0]:  # a drive that numbers no file (0) proves nothing
            # Some drives give a file a new number when its folder moves (Microsoft says so of FAT drives;
            # exFAT under Windows is unproven). Then the file is proved the long way: read in full and
            # compared with the hash the backup took. Never a pass without one proof or the other.
            if hashes is None:
                hashes = dict(backup_hashes(records), **log.get("extra_hash", {}))
            want_hash = hashes.get(rel)
            try:
                same = bool(want_hash) and st.st_size == want[1] and sha256_of(p) == want_hash
            except OSError:
                same = False
            if not same:
                log["problems"].append(f"not the same file after the move: {rel}" if want_hash
                                       else f"could not prove it is the same file after the move (no hash on record): {rel}")
                continue
            hashed += 1
        checked += 1
    log["checked"] = checked
    log["checked_by_reading"] = hashed
    log["status"] = "done" if not log["problems"] else "done with problems"
    log["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    if not log["problems"]:
        (records / "settled.json").write_text(json.dumps(
            {"session_was": log["session_was"], "folders": log["folders"], "when": log["finished"], "checked": checked}, indent=1), encoding="utf-8")
        # the card ledger now points at the records where they are now
        try:
            import cards
            ledger = cards.load()
            for entry in ledger.get("cards", {}).values():
                for s in entry.get("sessions", []):
                    if this_computer.same_place(s.get("folder") or "", log["session_was"]):
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
        try:  # an emptied day folder a PC's folder window held last time comes down now, if it is still there
            was = Path(json.loads((studio / "settled.json").read_text(encoding="utf-8"))["session_was"])
            if was.is_dir() and was.parent == root and all(x.is_file() and this_computer.housekeeping_file(x.name)
                                                           for x in was.iterdir()):
                take_down_day_folder(was, studio)
                say(f"The empty folder {was.name} is gone now.")
        except (OSError, ValueError, KeyError):
            pass
        return
    log_path = studio / "settle-log.json"
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))  # a settle that was cut off: finish it
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
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")  # on record before anything moves

    session, parent = Path(log["session_was"]), Path(log["parent"])
    if log["status"] == "planned":
        try:
            for f in log["folders"]:
                src, dst = session / f, parent / f
                if src.exists() and not dst.exists():
                    this_computer.rename(src, dst)  # the whole shoot folder, in one step
                elif dst.exists() and not src.exists():
                    continue  # moved before the cut-off
                else:
                    log["problems"].append(f"{f}: both or neither of {src} and {dst} exist; left as they are")
        except this_computer.HeldOpen as e:
            stopped(log, log_path, e, this_computer.HeldOpen.words)
        if log["problems"]:
            log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
            say("STOP:")
            for p in log["problems"]:
                say(f"  - {p}")
            sys.exit(1)
        log["status"] = "folders moved"
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")

    records, checked = finish(log, log_path)
    if log["problems"]:
        say("PROBLEMS (every move is in settle-log.json):")
        for p in log["problems"][:10]:
            say(f"  - {p}")
        sys.exit(1)
    say(f"Settled. {len(log['folders'])} shoot folders in {parent}, {checked:,} files checked, nothing overwritten.")
    if log.get("day_folder_left"):
        say(DAY_FOLDER_LEFT.format(name=session.name))


if __name__ == "__main__":
    main()
