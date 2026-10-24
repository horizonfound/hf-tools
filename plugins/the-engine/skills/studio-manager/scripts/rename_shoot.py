#!/usr/bin/env python3
"""Rename a shoot that the sorter has already placed: the folder and every
photo in it take her name, keeping the running number and the original
filename. This is her one decision on the first look, made real.

    python3 rename_shoot.py "<session>" --shoot s2 --name "Brittan sunset palms"
    python3 rename_shoot.py "<session>" --from-names        apply _studio/names.json to every shoot whose name differs
    ...  --dry-run                                           show the plan, touch nothing

Same promises as the sorter: only the copy on her drive, never the card;
a destination that exists stops it; renames on the same drive only; every
move written to _studio/rename-log.json before it happens; every renamed
photo re-read against the backup's hash for its original frame. The
`original` path kept in index.json is what makes this safe to do any
number of times.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sort import safe_folder, slug, sha256_of, load, say  # noqa: E402

NUMBERED = re.compile(r"^(?P<prefix>.+?)_(?P<n>\d{4})_(?P<orig>.+)$")


def plan_rename(session, studio, shoot_id, new_name):
    manifest = load(studio, "manifest.json")
    index = load(studio, "index.json")
    sh = load(studio, "shoots.json")
    shoot = next((s for s in sh["shoots"] if s["id"] == shoot_id), None)
    if not shoot:
        sys.exit(f"STOP: no shoot {shoot_id} in shoots.json.")
    if not shoot.get("folder"):
        sys.exit(f"STOP: {shoot_id} has not been sorted yet; run sort.py first.")
    old_folder = Path(shoot["folder"])
    new_folder = Path(safe_folder(new_name))
    prefix = slug(new_name)
    if not (session / old_folder).is_dir():
        sys.exit(f"STOP: the folder {old_folder} is not there. Nothing renamed.")
    if new_folder != old_folder and (session / new_folder).exists():
        sys.exit(f"STOP: a folder named {new_folder} already exists. Nothing renamed.")

    files = manifest["files"]
    moves = []
    for p in index["photos"]:
        cur = Path(p["file"])
        if cur.parent != old_folder or not p.get("original"):
            continue
        m = NUMBERED.match(cur.name)
        if not m:
            sys.exit(f"STOP: {cur.name} is not in the sorter's naming; will not guess. Nothing renamed.")
        rec = files.get(p["original"])
        if not rec or not rec.get("sha256"):
            sys.exit(f"STOP: no verified record for {p['original']}. Nothing renamed.")
        new = new_folder / f"{prefix}_{m['n']}_{m['orig']}"
        moves.append({"from": p["file"], "to": new.as_posix(), "original": p["original"], "sha256": rec["sha256"]})
        # the sidecar, if the sorter brought one along
        for ext in (".xmp", ".XMP"):
            sc = cur.with_suffix(ext)
            if (session / sc).exists():
                so = Path(p["original"]).with_suffix(ext).as_posix()
                moves.append({"from": sc.as_posix(), "to": (new_folder / f"{prefix}_{m['n']}_{Path(m['orig']).stem}{ext}").as_posix(),
                              "original": so, "sha256": files.get(so, {}).get("sha256")})
    if not moves:
        sys.exit(f"STOP: no sorted photos found in {old_folder}. Nothing renamed.")
    dests = [x["to"] for x in moves]
    if len(set(dests)) != len(dests):
        sys.exit("STOP: two files would get the same new name. Nothing renamed.")
    return shoot, old_folder, new_folder, moves


def apply(session, studio, shoot, old_folder, new_folder, moves, new_name, dry):
    say(f"{shoot['id']}: \"{shoot.get('name') or shoot.get('suggested')}\"  ->  \"{new_name}\"")
    say(f"  {old_folder}/  ->  {new_folder}/   {len(moves)} files")
    say(f"  e.g. {Path(moves[0]['from']).name}  ->  {Path(moves[0]['to']).name}")
    if dry:
        say("  Dry run. Nothing renamed.")
        return
    log_path = studio / "rename-log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"renames": []}
    entry = {"shoot": shoot["id"], "from_name": shoot.get("name"), "to_name": new_name,
             "started": datetime.now().isoformat(timespec="seconds"), "moves": moves, "verified": 0, "problems": []}
    log["renames"].append(entry)
    log_path.write_text(json.dumps(log, indent=1))

    t0 = time.time()
    if new_folder != old_folder:
        os.rename(session / old_folder, session / new_folder)  # one atomic move of the whole folder
    for m in moves:
        src = session / new_folder / Path(m["from"]).name
        dst = session / m["to"]
        if dst.exists() and src != dst:
            entry["problems"].append(f"{m['to']} already exists; not overwritten")
            break
        if src != dst:
            os.rename(src, dst)
        m["moved"] = True
    log_path.write_text(json.dumps(log, indent=1))
    say(f"  renamed in {time.time() - t0:.0f} s; reading every file again against the backup's hashes...")
    t1 = time.time()
    for m in moves:
        dst = session / m["to"]
        if not dst.exists():
            entry["problems"].append(f"after the rename, {m['to']} is not there")
        elif not m["sha256"]:
            entry["problems"].append(f"no hash to check against: {m['to']}")
        elif sha256_of(dst) != m["sha256"]:
            entry["problems"].append(f"hash mismatch after the rename: {m['to']}")
        else:
            entry["verified"] += 1
    say(f"  {entry['verified']} of {len(moves)} verified in {time.time() - t1:.0f} s")

    new_path = {m["from"]: m["to"] for m in moves}
    index = load(studio, "index.json")
    for p in index["photos"]:
        p["file"] = new_path.get(p["file"], p["file"])
    (studio / "index.json").write_text(json.dumps(index, indent=1))
    g = load(studio, "groups.json")
    for grp in g["groups"]:
        grp["files"] = [new_path.get(f, f) for f in grp["files"]]
    (studio / "groups.json").write_text(json.dumps(g, indent=1))
    sh = load(studio, "shoots.json")
    for s in sh["shoots"]:
        if s["id"] == shoot["id"]:
            s["name"], s["folder"] = new_name, new_folder.as_posix()
    (studio / "shoots.json").write_text(json.dumps(sh, indent=1))
    names = load(studio, "names.json", required=False) or {}
    names[shoot["id"]] = new_name
    (studio / "names.json").write_text(json.dumps(names, indent=1, ensure_ascii=False))
    entry["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1))
    if entry["problems"]:
        say("  PROBLEMS (every move is in rename-log.json):")
        for p in entry["problems"][:10]:
            say(f"    - {p}")
        sys.exit(1)
    say("  All done.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--shoot", help="shoot id from shoots.json, e.g. s2")
    ap.add_argument("--name", help="the new name")
    ap.add_argument("--from-names", action="store_true", help="apply _studio/names.json to every shoot whose name differs")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    session = Path(a.session).expanduser().resolve()
    studio = session / "_studio"

    jobs = []
    if a.from_names:
        names = load(studio, "names.json", required=False) or {}
        sh = load(studio, "shoots.json")
        for s in sh["shoots"]:
            want = (names.get(s["id"]) or "").strip()
            if want and want != (s.get("name") or ""):
                jobs.append((s["id"], want))
        if not jobs:
            say("Every shoot already has the name she gave it. Nothing to do.")
            return
    elif a.shoot and a.name:
        jobs.append((a.shoot, " ".join(a.name.split())))
    else:
        sys.exit("usage: --shoot <id> --name <name>, or --from-names")

    for shoot_id, new_name in jobs:
        shoot, old_folder, new_folder, moves = plan_rename(session, studio, shoot_id, new_name)
        apply(session, studio, shoot, old_folder, new_folder, moves, new_name, a.dry_run)


if __name__ == "__main__":
    main()
