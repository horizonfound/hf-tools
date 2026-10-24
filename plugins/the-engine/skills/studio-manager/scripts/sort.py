#!/usr/bin/env python3
"""The sorter: arrange the verified copy on her drive into one folder per
shoot, with every photo named for the shoot and its original filename kept
inside the new one, in shooting order. Rule 1 in code:

  - the card is never touched; this only ever works on the copy
  - it refuses to run unless backup.py verified every file and saw no problems
  - nothing is deleted or overwritten: a destination that already exists stops it
  - files are renamed on the same drive (no data is copied), then every moved
    file is read again and checked against the hash backup.py recorded
  - every move is written to _studio/sort-log.json first, so anything can be
    traced back and the run can pick up where it left off

    python3 sort.py "<session folder>" --dry-run      show the plan, touch nothing
    python3 sort.py "<session folder>"                do it, then re-verify

Names come from _studio/names.json (what she said) or the suggested name in
_studio/shoots.json (date-based) when she left one blank. A photo's sidecar
(.xmp) travels with it. Files with no capture time stay where they are.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path


def say(msg):
    print(msg, flush=True)


def safe_folder(name):
    """A folder name macOS, Windows and cloud drives all accept."""
    name = re.sub(r'[\\/:*?"<>|]+', " ", name).strip(" .")
    name = re.sub(r"\s+", " ", name)
    return name[:80] or "Untitled shoot"


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
    return json.loads(p.read_text())


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
    # a photo the sorter already placed carries its original path; it is never planned again
    already = sum(1 for p in index["photos"] if p.get("original"))
    moves, used_dest = [], set()
    for s in shoots:
        name = (names.get(s["id"]) or s.get("suggested") or s["id"]).strip()
        folder = safe_folder(name)
        prefix = slug(name)
        photos = sorted((by_file[f] for g in s["groups"] for f in groups[g]["files"]
                         if f in by_file and not by_file[f].get("original")),
                        key=lambda p: (p.get("taken") or "", p["file"]))
        for n, p in enumerate(photos, 1):
            src = Path(p["file"])
            new_name = f"{prefix}_{n:04d}_{src.name}"
            dest = Path(folder) / new_name
            cands = [(src, dest)]
            # the sidecar travels with its photo, same new stem
            for sc in (src.with_suffix(".xmp"), src.with_suffix(".XMP")):
                if sc.as_posix() in files:
                    cands.append((sc, Path(folder) / f"{prefix}_{n:04d}_{sc.name}"))
            for a, b in cands:
                if b.as_posix() in used_dest:
                    sys.exit(f"STOP: two files would land on {b}. Nothing sorted.")
                rec = files.get(a.as_posix())
                if not rec or not rec.get("sha256"):
                    # no verified record means we could not prove the move safe afterwards: refuse
                    sys.exit(f"STOP: {a} has no verified record in the backup manifest. Nothing sorted.")
                used_dest.add(b.as_posix())
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
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="skip the re-read after moving (not recommended)")
    a = ap.parse_args()
    session = Path(a.session).expanduser().resolve()
    studio = session / "_studio"

    plan = make_plan(session, studio)
    problems = check_plan(session, plan)
    by_shoot = {}
    for m in plan["moves"]:
        by_shoot.setdefault(m["name"], 0)
        by_shoot[m["name"]] += 1
    say(f"Plan for {plan['session']}:")
    if plan["already_sorted"]:
        say(f"  already sorted on an earlier run, left alone: {plan['already_sorted']} photos")
    for name, n in by_shoot.items():
        say(f"  {safe_folder(name)}/   {n} files")
    say(f"  left where they are: {len(plan['untouched'])} (no capture time, or not a photo)")
    first = next((m for m in plan["moves"] if not m.get("already")), None)
    if first:
        say(f"  e.g. {first['from']}  ->  {first['to']}")
    if problems:
        say("\nSTOP, nothing moved:")
        for p in problems[:20]:
            say(f"  - {p}")
        sys.exit(2)
    if a.dry_run:
        (studio / "sort-plan.json").write_text(json.dumps(plan, indent=1))
        say(f"\nDry run. The plan is in {studio / 'sort-plan.json'}. Nothing moved.")
        return

    # write the log before touching anything, so every move is on record first
    log_path = studio / "sort-log.json"
    log = {"session": plan["session"], "started": datetime.now().isoformat(timespec="seconds"),
           "moves": plan["moves"], "done": 0, "verified": 0, "problems": []}
    log_path.write_text(json.dumps(log, indent=1))

    t0 = time.time()
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
        os.rename(src, dst)
        m["moved"] = True
        log["done"] += 1
        if log["done"] % 200 == 0:
            log_path.write_text(json.dumps(log, indent=1))
            say(f"  {log['done']} of {len(plan['moves'])} moved")
    log_path.write_text(json.dumps(log, indent=1))
    say(f"{log['done']} files moved in {time.time() - t0:.0f} s")

    # whatever was not sorted (camera housekeeping, anything with no capture time) is set aside
    # inside _studio, original path kept, so her folder shows only the shoots. Nothing is deleted.
    aside = []
    if not log["problems"]:
        for rel in plan["untouched"]:
            src, dst = session / rel, studio / "from-the-card" / rel
            if not src.exists() or dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            aside.append({"from": rel, "to": dst.relative_to(session).as_posix()})
        # folders the card layout left behind come down once only Finder's hidden notes (.DS_Store and the
        # like) remain; those are set aside too, never deleted. rmdir refuses a folder with anything in it.
        for d in sorted((p for p in session.rglob("*") if p.is_dir() and "_studio" not in p.parts), key=lambda p: -len(p.parts)):
            entries = list(d.iterdir())
            if entries and all(x.is_file() and x.name.startswith(".") for x in entries):
                for x in entries:
                    rel = x.relative_to(session)
                    dst = studio / "from-the-card" / rel
                    if not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        os.rename(x, dst)
                        aside.append({"from": rel.as_posix(), "to": dst.relative_to(session).as_posix()})
            try:
                d.rmdir()
            except OSError:
                pass
        log["set_aside"] = aside
        if aside:
            say(f"{len(aside)} file{'s that are not photos' if len(aside) != 1 else ' that is not a photo'} set aside in _studio/from-the-card")

    if not a.no_verify and not log["problems"]:
        say("Reading every moved file again against the backup's hashes...")
        t1 = time.time()
        for m in plan["moves"]:
            dst = session / m["to"]
            if not dst.exists():
                log["problems"].append(f"after the move, {m['to']} is not there")
                continue
            if not m["sha256"]:
                log["problems"].append(f"no hash to check against: {m['to']}")  # must never pass silently
                continue
            if sha256_of(dst) != m["sha256"]:
                log["problems"].append(f"hash mismatch after the move: {m['to']}")
                continue
            log["verified"] += 1
            if log["verified"] % 500 == 0:
                say(f"  {log['verified']} of {len(plan['moves'])} verified")
        say(f"{log['verified']} of {len(plan['moves'])} verified in {time.time() - t1:.0f} s")

    # the index and groups now point at the new names; the original path stays beside it
    new_path = {m["from"]: m["to"] for m in plan["moves"]}
    index = load(studio, "index.json")
    for p in index["photos"]:
        if p["file"] in new_path:
            p["original"] = p["file"]
            p["file"] = new_path[p["file"]]
    (studio / "index.json").write_text(json.dumps(index, indent=1))
    g = load(studio, "groups.json")
    for grp in g["groups"]:
        grp["files"] = [new_path.get(f, f) for f in grp["files"]]
    (studio / "groups.json").write_text(json.dumps(g, indent=1))
    sh = load(studio, "shoots.json")
    for s in sh["shoots"]:
        fs = [m for m in plan["moves"] if m["shoot"] == s["id"]]
        if fs:
            s["name"] = fs[0]["name"]
            s["folder"] = Path(fs[0]["to"]).parent.as_posix()
    (studio / "shoots.json").write_text(json.dumps(sh, indent=1))

    log["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1))
    if log["problems"]:
        say("\nPROBLEMS (nothing deleted, every move is in sort-log.json):")
        for p in log["problems"][:20]:
            say(f"  - {p}")
        sys.exit(1)
    say("Sorted. Every move is in _studio/sort-log.json.")


if __name__ == "__main__":
    main()
