#!/usr/bin/env python3
"""The sorter: arrange the verified copy on their drive into one folder per
shoot, with every photo named for the shoot and its original filename kept
inside the new one, in shooting order. Rule 1 in code:

  - the card is never changed; this only ever works on the copy
  - it refuses to run unless backup.py verified every file and saw no problems
  - nothing is deleted or overwritten: a destination that already exists stops it
  - files are renamed on the same drive (no data is copied), then every moved
    file is read again and checked against the hash backup.py recorded
  - every move is written to _studio/sort-log.json first, so anything can be
    traced back and the run can pick up where it left off

    python3 sort.py "<session folder>" --dry-run      show the plan, touch nothing
    python3 sort.py "<session folder>"                do it, then re-verify

Names come from _studio/names.json (what they said) or the suggested name in
_studio/shoots.json (date-based) when they left one blank. A photo's sidecar
(.xmp) travels with it. Files with no capture time stay where they are.

A shoot with photos and video clips gets two folders inside its own, Photos and
Videos, each numbered from 0001 in shooting order (Dustin, Nov 11). A shoot of
only photos, or only clips, stays one flat folder, as before.
"""
import argparse
import errno
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import studio_file  # noqa: E402
import clips  # noqa: E402  (which files are video, and the Photos and Videos folders)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()


def say(msg):
    """Print, but never let a closed pipe (someone ran us through `head`) stop the work on their files."""
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe. A Mac raises anything else, as before. unproven on a real PC
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):
            raise
        sys.stdout = open(os.devnull, "w", encoding="utf-8")


def safe_folder(name):
    """A folder name macOS, Windows and cloud drives all accept. The same on both computers on purpose, so a
    drive can move between them (readiness row B5): the cut at 80 never leaves a space or a dot at the end
    (a PC drops it, and the folder could not be found again), and a name Windows keeps for itself gets an
    underscore ("Con" -> "Con_", "Nul. Family" -> "Nul_. Family"). Every other name is exactly as before."""
    name = re.sub(r'[\\/:*?"<>|]+', " ", name).strip(" .")
    name = re.sub(r"\s+", " ", name)
    return this_computer.unreserved(name[:80].strip(" .") or "Untitled shoot")


def slug(name):
    """The shoot's name as a filename prefix: Lani swim shoot -> Lani-swim-shoot."""
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return s[:40] or "Shoot"


def sha256_of(path, chunk=4 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load(studio, name, required=True):
    p = studio / name
    if not p.exists():
        if required:
            sys.exit(f"STOP: {p} is missing. Run the earlier steps first.")
        return None
    return forward_slashes(name, json.loads(p.read_text(encoding="utf-8")))


def forward_slashes(name, d):
    """Every record spells a photo's place with forward slashes, on a Mac and on a PC, so a drive can move
    between them. On a PC an older record might say DCIM\\100CANON\\IMG_1.CR3; it is read the same way and
    written back the new way. Never on a Mac, where a backslash is an ordinary letter in a file name."""
    if not this_computer.WINDOWS or not isinstance(d, dict):
        return d
    # unproven on a real PC (no record with backslashes has ever been written: nothing ran on a PC before)
    fix = lambda s: s.replace("\\", "/") if isinstance(s, str) else s  # noqa: E731
    if name == "manifest.json" and isinstance(d.get("files"), dict):
        d["files"] = {fix(k): v for k, v in d["files"].items()}
    elif name == "index.json":
        for p in d.get("photos", []):
            for k in ("file", "original"):
                if k in p:
                    p[k] = fix(p[k])
    elif name == "groups.json":
        for g in d.get("groups", []):
            g["files"] = [fix(f) for f in g.get("files", [])]
    elif name == "shoots.json":
        for s in d.get("shoots", []):
            if s.get("folder"):
                s["folder"] = fix(s["folder"])
    return d


def text_key(p):
    """A path as text for "would two files land in the same place": on a PC, where the drive ignores upper and
    lower case, IMG_1.JPG and img_1.jpg are one place; on a Mac the text itself, as before."""
    if this_computer.WINDOWS:  # unproven on a real PC
        return os.path.normcase(Path(p).as_posix())
    return Path(p).as_posix()


TOO_LONG = (f"a photo's new place would be longer than {this_computer.FILES_APP} can open (260 characters, counting the "
            "drive and every folder on the way). A shorter name for the shoot fixes it.")


def new_places(session, plan):
    """Every file and folder the sort would make, as (path, is a folder, is the Assistant's own): each photo's
    new place and its folder (theirs), and where whatever is left (camera housekeeping, undated files, the
    computer's own notes) is set aside in the hidden records (the Assistant's own)."""
    aside = session / "_studio" / "from-the-card"
    photos = [session / m["to"] for m in plan["moves"] if not m.get("already")]
    kept = [aside / rel for rel in plan["untouched"]]
    # the card's own folders (DCIM...), where the computer's notes are set aside once the photos have gone
    tops = {Path(r).parts[0] for r in [m["from"] for m in plan["moves"]] + plan["untouched"] if len(Path(r).parts) > 1}
    for top in sorted(tops):
        for dirpath, _, names in os.walk(session / top):
            here = Path(dirpath)
            kept += [aside / here.relative_to(session) / n for n in names if this_computer.housekeeping_file(n)]
    return ([(f, False, False) for f in photos] + [(d, True, False) for d in sorted({f.parent for f in photos})]
            + [(f, False, True) for f in kept] + [(d, True, True) for d in sorted({f.parent for f in kept})])


def make_plan(session, studio):
    manifest = load(studio, "manifest.json")
    index = load(studio, "index.json")
    groups = {g["id"]: g for g in load(studio, "groups.json")["groups"]}
    shoots = load(studio, "shoots.json")["shoots"]
    names = load(studio, "names.json", required=False) or {}

    # the gate: every file verified, no problems
    files = manifest.get("files", {})
    not_ok = [k for k, v in files.items() if not v.get("dest", {}).get("ok")]
    if manifest.get("problems") or not_ok:
        sys.exit(f"STOP: the backup is not fully verified ({len(not_ok)} files unchecked, "
                 f"{len(manifest.get('problems') or [])} problems). Nothing sorted.")

    by_file = {p["file"]: p for p in index["photos"]}
    # their naming, from the Studio File: how folders are named, and whether photos keep their frame names
    naming = studio_file.load().get("naming", {})
    keep_names = naming.get("file_names", "shoot") == "original"
    # a photo the sorter already placed carries its original path; it is never planned again
    already = sum(1 for p in index["photos"] if p.get("original"))
    moves, used_dest = [], set()
    for s in shoots:
        name = (names.get(s["id"]) or s.get("suggested") or s["id"]).strip()
        photos = sorted((by_file[f] for g in s["groups"] for f in groups[g]["files"]
                         if f in by_file and not by_file[f].get("original")),
                        key=lambda p: (p.get("taken") or "", p["file"]))
        if not photos:
            continue
        shoot_date = photos[0].get("taken") or groups[s["groups"][0]]["start"]
        folder = safe_folder(studio_file.render(naming, name, shoot_date)) if naming.get("folder_pattern") else safe_folder(name)
        prefix = slug(name)
        # photos and clips together: two folders inside the shoot's, each numbered on its own, so a clip never
        # sits in among the photos or takes one of their numbers (Dustin, Nov 11). One kind only: one flat folder.
        stills, videos = [p for p in photos if not clips.is_clip(p)], [p for p in photos if clips.is_clip(p)]
        if stills and videos:
            placed = ([(Path(folder) / clips.PHOTOS_FOLDER, n, p) for n, p in enumerate(stills, 1)]
                      + [(Path(folder) / clips.VIDEOS_FOLDER, n, p) for n, p in enumerate(videos, 1)])
        else:
            placed = [(Path(folder), n, p) for n, p in enumerate(photos, 1)]
        for into, n, p in placed:
            src = Path(p["file"])
            new_name = src.name if keep_names else f"{prefix}_{n:04d}_{src.name}"
            dest = into / new_name
            cands = [(src, dest)]
            # the sidecar travels with its photo, same new stem
            for sc in (src.with_suffix(".xmp"), src.with_suffix(".XMP")):
                if sc.as_posix() in files:
                    cands.append((sc, into / (sc.name if keep_names else f"{prefix}_{n:04d}_{sc.name}")))
            for a, b in cands:
                if text_key(b) in used_dest:
                    sys.exit(f"STOP: two files would land on {b}. Nothing sorted."
                             + (" (Two frames share a name; naming photos for the shoot would keep them apart.)" if keep_names else ""))
                rec = files.get(a.as_posix())
                if not rec or not rec.get("sha256"):
                    # no verified record means we could not prove the move safe afterwards: refuse
                    sys.exit(f"STOP: {a} has no verified record in the backup manifest. Nothing sorted.")
                used_dest.add(text_key(b))
                moves.append({"from": a.as_posix(), "to": b.as_posix(), "shoot": s["id"], "name": name,
                              "sha256": rec["sha256"], "size": rec.get("size")})
    planned = {m["from"] for m in moves}
    # untouched: files still sitting at their card path (housekeeping, undated), not the ones already sorted
    untouched = [k for k in files if k not in planned and (session / k).exists()]
    return {"session": manifest.get("session"), "planned": datetime.now().isoformat(timespec="seconds"),
            "moves": moves, "already_sorted": already, "untouched": untouched}


def check_plan(session, plan):
    """Nothing moves until every source is there at the recorded size and no destination exists."""
    problems = []
    for m in plan["moves"]:
        src, dst = session / m["from"], session / m["to"]
        if not src.exists():
            if dst.exists() and m["size"] is not None and dst.stat().st_size == m["size"]:
                m["already"] = True  # a previous run moved it; verify will confirm the hash
                continue
            problems.append(f"missing: {m['from']}")
            continue
        if m["size"] is not None and src.stat().st_size != m["size"]:
            problems.append(f"size changed since the backup: {m['from']}")
        if dst.exists():
            problems.append(f"already exists, would not overwrite: {m['to']}")
    # on a PC, a place longer than Windows allows would stop the sort part way: found now, before anything moves
    long = [str(p) for p, folder, own in new_places(session, plan)
            if (this_computer.records_path_too_long if own else this_computer.path_too_long)(p, folder=folder)]
    if long:
        problems.insert(0, TOO_LONG)
        problems += [f"too long: {p}" for p in long[:5]]
    return problems


def stopped(log, log_path, e, phase):
    """A PC would not move a file because another program had it, or its folder, open (this_computer.HeldOpen).
    Every move so far is in the log, and the photos not yet moved are still where the backup put them, so
    running the sort again finishes it. The log keeps a problem until then, so nothing settles in between."""
    log["problems"].append(f"stopped part way while {phase}: another program had {Path(e.src).name} open")
    log["stopped"] = {"when": datetime.now().isoformat(timespec="seconds"), "while": phase, "file": e.src, "detail": str(e)}
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    what = "take down the empty folder" if e.src == e.dst else "move"
    say(f"\nStopped part way ({log['done']} of {len(log['moves'])} files moved): the {this_computer.COMPUTER} "
        f"would not {what} {Path(e.src).name} ({e.cause}). Every move so far is in _studio/sort-log.json.")
    say(e.words)
    sys.exit(1)


def earlier_stop(log_path):
    """The log of a sort that stopped part way (a file held open, the power), or {}."""
    if not log_path.exists():
        return {}
    try:
        old = json.loads(log_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {} if old.get("finished") else old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="skip the check after moving (not recommended)")
    ap.add_argument("--deep", action="store_true", help="re-read and hash every moved file instead of the identity check")
    a = ap.parse_args()
    session = Path(a.session).expanduser().resolve()
    studio = session / "_studio"

    plan = make_plan(session, studio)
    problems = check_plan(session, plan)
    by_shoot = {}
    for m in plan["moves"]:
        where = Path(m["to"]).parent.as_posix()
        by_shoot.setdefault(where, 0)
        by_shoot[where] += 1
    say(f"Plan for {plan['session']}:")
    if plan["already_sorted"]:
        say(f"  already sorted on an earlier run, left alone: {plan['already_sorted']} files")
    for where, n in by_shoot.items():
        say(f"  {where}/   {n} files")
    say(f"  left where they are: {len(plan['untouched'])} (no capture time, or not a photo or a clip)")
    first = next((m for m in plan["moves"] if not m.get("already")), None)
    if first:
        say(f"  e.g. {first['from']}  ->  {first['to']}")
    if problems:
        say("\nSTOP, nothing moved:")
        for p in problems[:20]:
            say(f"  - {p}")
        sys.exit(2)
    if a.dry_run:
        (studio / "sort-plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
        say(f"\nDry run. The plan is in {studio / 'sort-plan.json'}. Nothing moved.")
        return

    # write the log before touching anything, so every move is on record first
    log_path = studio / "sort-log.json"
    before = earlier_stop(log_path)
    # a sort that stopped part way proved each file it moved by its identity on the drive just before the
    # move; those proofs still hold (a rename never rewrites a byte), so the second run need not read them all
    proved = {(m["from"], m["to"], m.get("sha256")): m["ident"] for m in before.get("moves", [])
              if m.get("moved") and m.get("ident") and m.get("sha256")}
    for m in plan["moves"]:
        if m.get("already") and (m["from"], m["to"], m["sha256"]) in proved:
            m["ident"] = proved[(m["from"], m["to"], m["sha256"])]
    log = {"session": plan["session"], "started": datetime.now().isoformat(timespec="seconds"),
           "moves": plan["moves"], "done": 0, "verified": 0, "problems": []}
    if before.get("stopped"):
        log["stopped_before"] = before["stopped"]
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")

    t0 = time.time()
    try:
        for m in plan["moves"]:
            if m.get("already"):
                log["done"] += 1
                continue
            src, dst = session / m["from"], session / m["to"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if os.stat(src).st_dev != os.stat(dst.parent).st_dev:
                log["problems"].append(f"{m['from']}: destination is on a different drive; refusing to copy-and-delete")
                break
            if dst.exists():
                log["problems"].append(f"{m['to']} appeared since the plan was checked; not overwritten")
                break
            st = os.stat(src)
            m["ident"] = [st.st_ino, st.st_size, st.st_mtime_ns]  # the file's identity on this drive, before the move
            try:
                this_computer.rename(src, dst)
            except FileExistsError:  # a PC refuses to move onto a name that is there (a Mac checks above); unproven on a real PC
                log["problems"].append(f"{m['to']} appeared since the plan was checked; not overwritten")
                break
            m["moved"] = True
            log["done"] += 1
            if log["done"] % 200 == 0:
                log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
                say(f"  {log['done']} of {len(plan['moves'])} moved")
    except this_computer.HeldOpen as e:
        stopped(log, log_path, e, "moving the photos")
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    say(f"{log['done']} files moved in {time.time() - t0:.0f} s")

    # whatever was not sorted (camera housekeeping, anything with no capture time) is set aside
    # inside _studio, original path kept, so their folder shows only the shoots. Nothing is deleted.
    aside = []
    if not log["problems"]:
        if before:
            # anything a run that stopped part way had already set aside stays on the list, so the report names it all
            planned = {m["from"] for m in plan["moves"]}
            aside = [e for e in before.get("set_aside", []) if (session / e["to"]).exists()]
            done = {e["from"] for e in aside}
            for rel in sorted(load(studio, "manifest.json").get("files", {})):
                if rel in planned or rel in done or rel in plan["untouched"]:
                    continue
                if not (session / rel).exists() and (studio / "from-the-card" / rel).exists():
                    aside.append({"from": rel, "to": (studio / "from-the-card" / rel).relative_to(session).as_posix()})
        try:
            for rel in plan["untouched"]:
                src, dst = session / rel, studio / "from-the-card" / rel
                if not src.exists() or dst.exists():
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                this_computer.rename(src, dst)
                aside.append({"from": rel, "to": dst.relative_to(session).as_posix()})
            # folders the card layout left behind come down once only the computer's hidden notes (Finder's
            # .DS_Store and the like; on a PC also Thumbs.db) remain; those are set aside too, never deleted.
            # rmdir refuses a folder with anything in it.
            for d in sorted((p for p in session.rglob("*") if p.is_dir() and "_studio" not in p.parts), key=lambda p: -len(p.parts)):
                entries = list(d.iterdir())
                if entries and all(x.is_file() and this_computer.housekeeping_file(x.name) for x in entries):
                    for x in entries:
                        rel = x.relative_to(session)
                        dst = studio / "from-the-card" / rel
                        if not dst.exists():
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            this_computer.rename(x, dst)
                            aside.append({"from": rel.as_posix(), "to": dst.relative_to(session).as_posix()})
                try:
                    this_computer.rmdir(d)
                except this_computer.HeldOpen:
                    raise  # on a PC a folder window can hold an empty folder: stop and say so, never leave it quietly
                except OSError:
                    pass
        except this_computer.HeldOpen as e:
            log["set_aside"] = aside
            stopped(log, log_path, e, "setting aside what is not a photo")
        log["set_aside"] = aside
        if aside:
            say(f"{len(aside)} file{'s that are not photos' if len(aside) != 1 else ' that is not a photo'} set aside in _studio/from-the-card")

    if not a.no_verify and not log["problems"]:
        # A rename on the same drive never rewrites a byte: the file keeps its identity (inode), size and
        # modified time. Checking those proves the file at the new name is the very same file, instantly.
        # Any file that cannot be proved that way (moved by an earlier run, or an odd drive) is read and
        # hashed in full instead. Nothing passes without one of the two. --deep hashes everything.
        say("Checking every moved file is the same file it was..." if not a.deep else "Reading every moved file again against the backup's hashes...")
        t1 = time.time()
        hashed = 0
        for m in plan["moves"]:
            dst = session / m["to"]
            if not dst.exists():
                log["problems"].append(f"after the move, {m['to']} is not there")
                continue
            same = False
            if not a.deep and m.get("ident") and m["ident"][0]:  # a drive that numbers no file (0) proves nothing
                st = os.stat(dst)
                same = [st.st_ino, st.st_size, st.st_mtime_ns] == m["ident"] and (m["size"] is None or st.st_size == m["size"])
            if not same:
                if not m["sha256"]:
                    log["problems"].append(f"no hash to check against: {m['to']}")  # must never pass silently
                    continue
                if sha256_of(dst) != m["sha256"]:
                    log["problems"].append(f"hash mismatch after the move: {m['to']}")
                    continue
                hashed += 1
            log["verified"] += 1
            if log["verified"] % 500 == 0:
                say(f"  {log['verified']} of {len(plan['moves'])} checked")
        log["hashed_in_full"] = hashed
        say(f"{log['verified']} of {len(plan['moves'])} checked in {time.time() - t1:.0f} s"
            + (f" ({hashed} read in full)" if hashed else ""))

    # the index and groups now point at the new names; the original path stays beside it. Records say where
    # the files are, never where they were meant to go: if a move did not happen (a stop above), the records
    # stay as they were, so the next run plans the same names again and finishes from the log's evidence.
    if any(not (m.get("moved") or m.get("already")) for m in plan["moves"]):
        log["finished"] = datetime.now().isoformat(timespec="seconds")
        log["records_left_as_they_were"] = True
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
        say("\nPROBLEMS (nothing deleted, nothing overwritten, every move is in sort-log.json):")
        for p in log["problems"][:20]:
            say(f"  - {p}")
        sys.exit(1)
    new_path = {m["from"]: m["to"] for m in plan["moves"]}
    index = load(studio, "index.json")
    for p in index["photos"]:
        if p["file"] in new_path:
            p["original"] = p["file"]
            p["file"] = new_path[p["file"]]
    (studio / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    g = load(studio, "groups.json")
    for grp in g["groups"]:
        grp["files"] = [new_path.get(f, f) for f in grp["files"]]
    (studio / "groups.json").write_text(json.dumps(g, indent=1), encoding="utf-8")
    sh = load(studio, "shoots.json")
    for s in sh["shoots"]:
        fs = [m for m in plan["moves"] if m["shoot"] == s["id"]]
        if fs:
            s["name"] = fs[0]["name"]
            s["folder"] = Path(fs[0]["to"]).parts[0]   # the shoot's own folder (Photos and Videos sit inside it)
    (studio / "shoots.json").write_text(json.dumps(sh, indent=1), encoding="utf-8")

    log["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    if log["problems"]:
        say("\nPROBLEMS (nothing deleted, every move is in sort-log.json):")
        for p in log["problems"][:20]:
            say(f"  - {p}")
        sys.exit(1)
    say("Sorted. Every move is in _studio/sort-log.json.")


if __name__ == "__main__":
    main()
