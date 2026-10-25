#!/usr/bin/env python3
"""Find the photographer's edited photos for a shoot, without asking where they
export to.

After their edit they export JPEGs the way they always do and say "I'm done
with the beach shoot." This looks for those JPEGs two ways:

  1. By name. The backup named every photo <Shoot>_<NNNN>_<camera name>, and
     Lightroom keeps the file name on export unless told otherwise, so
     "Black-sand-beach_0012_IMG_4471.jpg" is that shoot, edited. The camera's
     own name ("IMG_4471.jpg") counts too.
  2. By what the photo carries. If they rename on export, every JPEG still
     knows the moment it was taken and which camera took it; those are
     matched against the backup's index.

It looks first where their exports went last time (remembered in the Studio
File), then in and beside the shoot's folder, then Pictures, Desktop and
Downloads. It only reads; nothing is moved or changed.

    python3 find_exports.py --night "<the night's folder or records>" --shoot s1
    python3 find_exports.py ... --remember "<folder>"     after they confirm it, remember where exports go
    python3 find_exports.py ... --json

Exit codes: 0 found · 7 nothing found (ask where they exported).
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exif_read  # noqa: E402
import studio_file  # noqa: E402
from where import locate  # noqa: E402

EDITED = {".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff"}
SKIP = {".photoslibrary", ".lrdata", ".lrcat-data", ".app", ".Trash", "Library", "node_modules", "_studio", ".studio"}
NUM = re.compile(r"^(?P<prefix>.+?)_(?P<n>\d{4})_(?P<orig>.+)$")


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def shoot_photos(root, studio, shoot_id):
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        sys.exit(f"STOP: no shoot {shoot_id} in that backup.")
    folder = s.get("folder")
    index = json.loads((studio / "index.json").read_text())["photos"]
    mine = [p for p in index if folder and Path(p["file"]).parent.as_posix() == folder]
    if not mine:  # not sorted into a folder: take the shoot's groups instead
        groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]}
        files = {f for g in s.get("groups", []) for f in groups.get(g, {}).get("files", [])}
        mine = [p for p in index if p["file"] in files]
    return s, folder, mine


def name_keys(photos):
    """Every stem an exported copy of these photos could carry, lower-case."""
    keys = {}
    for p in photos:
        stem = Path(p["file"]).stem.lower()
        keys[stem] = p
        m = NUM.match(Path(p["file"]).stem)
        orig = Path(p.get("original") or p["file"]).stem.lower()
        keys.setdefault(orig, p)
        if m:
            keys.setdefault(Path(m["orig"]).stem.lower(), p)
    return keys


def candidate_folders(root, folder, remembered):
    """(path, depth) in the order to look: remembered spots, the shoot folder, beside it, then the usual places."""
    home = Path.home()
    out = [(Path(r), 3) for r in remembered]
    if folder:
        out.append((root / folder, 3))
    out.append((root, 2))
    out += [(home / "Pictures", 3), (home / "Desktop", 3), (home / "Downloads", 2)]
    seen, ordered = set(), []
    for p, d in out:
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            ordered.append((p, d))
    return ordered


def edited_files(top, depth, newer_than):
    """JPEGs and friends under top, at most `depth` folders down, modified after the shoot."""
    top_parts = len(top.parts)
    for dirpath, dirnames, filenames in os.walk(top):
        d = Path(dirpath)
        dirnames[:] = [x for x in dirnames if not x.startswith(".") and not any(x.endswith(s) or x == s for s in SKIP)]
        if len(d.parts) - top_parts >= depth:
            dirnames[:] = []
        for fn in filenames:
            if fn.startswith(".") or Path(fn).suffix.lower() not in EDITED:
                continue
            p = d / fn
            try:
                if p.stat().st_mtime >= newer_than:
                    yield p
            except OSError:
                pass


def find(root, studio, shoot_id, remembered, max_reads=400):
    s, folder, photos = shoot_photos(root, studio, shoot_id)
    if not photos:
        sys.exit("STOP: no photos recorded for that shoot.")
    keys = name_keys(photos)
    shot_day = min(p["taken"][:10] for p in photos if p.get("taken"))
    newer = datetime.fromisoformat(shot_day).timestamp()
    by_time = defaultdict(list)
    for p in photos:
        if p.get("taken"):
            by_time[p["taken"][:19]].append(p)
    per_folder = defaultdict(lambda: {"files": [], "by_name": set(), "by_time": set()})
    looked = set()
    for top, depth in candidate_folders(root, folder, remembered):
        for f in edited_files(top, depth, newer):
            if str(f) in looked:
                continue
            looked.add(str(f))
            per_folder[str(f.parent)]["files"].append(f)
    # 1. by name
    for fol, rec in per_folder.items():
        for f in rec["files"]:
            stem = f.stem.lower()
            stem = re.sub(r"(-edit|-\d+| copy)$", "", stem)  # Lightroom's "-Edit", "-2" and Finder's " copy"
            if stem in keys:
                rec["by_name"].add(keys[stem]["file"])
    # 2. by capture time + camera, only where names did not match, and only so many reads
    reads = 0
    for fol, rec in sorted(per_folder.items(), key=lambda kv: -len(kv[1]["files"])):
        if rec["by_name"] or reads >= max_reads:
            continue
        for f in rec["files"][:60]:
            if reads >= max_reads:
                break
            reads += 1
            facts = exif_read.read(f)
            t = (facts.get("taken") or "")[:19]
            for p in by_time.get(t, []):
                if not p.get("serial") or not facts.get("serial") or p["serial"] == facts.get("serial"):
                    rec["by_time"].add(p["file"])
                    break
        if rec["by_time"] and len(rec["by_time"]) * 3 >= min(len(rec["files"]), 60):  # most of the sample matches
            rec["by_time_all"] = True
    results = []
    for fol, rec in per_folder.items():
        hits = len(rec["by_name"]) or len(rec["by_time"])
        if not hits:
            continue
        results.append({"folder": fol, "how": "name" if rec["by_name"] else "capture time",
                        "matched": hits, "files_in_folder": len(rec["files"]),
                        "count": len(rec["files"]) if rec.get("by_time_all") else hits})
    results.sort(key=lambda r: (-r["matched"], r["folder"]))
    return s, photos, results


def check(folder):
    """A light look at the export: how many, any names twice, any suspiciously small files."""
    files = [p for p in Path(folder).iterdir() if p.suffix.lower() in EDITED and not p.name.startswith(".")]
    sizes = [p.stat().st_size for p in files]
    stems = [p.stem.lower() for p in files]
    twice = sorted({s for s in stems if stems.count(s) > 1})
    tiny = [p.name for p in files if p.stat().st_size < 150 * 1024]
    return {"count": len(files), "twice": twice[:10], "tiny": tiny[:10],
            "smallest_kb": round(min(sizes) / 1024) if sizes else 0, "largest_kb": round(max(sizes) / 1024) if sizes else 0}


def remember(folder):
    sf = studio_file.load()
    spots = [s for s in sf.get("exports", []) if s != str(Path(folder).parent)]
    sf["exports"] = [str(Path(folder).parent)] + spots[:4]  # where exports tend to land, newest first
    studio_file.save(sf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--night", required=True)
    ap.add_argument("--shoot", required=True)
    ap.add_argument("--remember", help="the folder they confirmed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root, studio = locate(a.night)
    if a.remember:
        remember(a.remember)
        say(f"Remembered: exports go near {Path(a.remember).parent}.")
        return
    remembered = studio_file.load().get("exports", [])
    s, photos, results = find(root, studio, a.shoot, remembered)
    name = s.get("name") or s.get("suggested") or a.shoot
    if not results:
        if a.json:
            print(json.dumps({"shoot": name, "found": None}))
        else:
            say(f"No edited photos from {name} found yet. Ask where they exported them.")
        sys.exit(7)
    best = results[0]
    best["check"] = check(best["folder"])
    if a.json:
        print(json.dumps({"shoot": name, "found": best, "others": results[1:4]}, indent=1))
        return
    say(f"Found {best['count']} edited photos from {name} in {best['folder']} (matched by {best['how']}).")
    c = best["check"]
    if c["twice"]:
        say(f"  Same name twice: {', '.join(c['twice'])}")
    if c["tiny"]:
        say(f"  Very small files, maybe exported at the wrong size: {', '.join(c['tiny'])}")
    for r in results[1:3]:
        say(f"  Also some in {r['folder']} ({r['matched']} matched)")


if __name__ == "__main__":
    main()
