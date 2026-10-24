#!/usr/bin/env python3
"""Build _studio/index.json for a session: one record per photo or clip, with
when it was taken, which camera and lens, its size, and the hash backup.py
already verified. Everything after the backup reads from this file, so no
later step has to open a RAW to learn when it was taken.

Reads the verified copy on her drive, never the card. Metadata only: a few MB
from the front of each file, so a 4,000-photo session takes about a minute.

    python3 index.py "<session folder>"
"""
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exif_read  # noqa: E402

MEDIA = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw", ".jpg", ".jpeg", ".heic", ".png",
         ".tif", ".tiff", ".mov", ".mp4", ".m4v"}


def build(session_dir):
    session_dir = Path(session_dir)
    studio = session_dir / "_studio"
    manifest = json.loads((studio / "manifest.json").read_text()) if (studio / "manifest.json").exists() else {"files": {}}
    hashes = {k: v.get("sha256") for k, v in manifest.get("files", {}).items()}
    t0 = time.time()
    records, unreadable = [], []
    for p in sorted(session_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in MEDIA or "_studio" in p.parts or p.name.startswith("."):
            continue
        rel = p.relative_to(session_dir).as_posix()
        rec = {"file": rel, "size": p.stat().st_size, "sha256": hashes.get(rel)}
        facts = exif_read.read(p)
        if not facts.get("taken"):
            unreadable.append(rel)
        rec.update(facts)
        records.append(rec)
    records.sort(key=lambda r: (r.get("taken") or "9999", r["file"]))

    taken = [r["taken"] for r in records if r.get("taken")]
    days = Counter(t[:10] for t in taken)
    cameras = Counter(r.get("camera", "unknown") for r in records)
    serials = Counter(r.get("serial") for r in records if r.get("serial"))
    index = {
        "session": manifest.get("session") or session_dir.name,
        "built": datetime.now().isoformat(timespec="seconds"),
        "seconds": round(time.time() - t0, 1),
        "count": len(records),
        "clips": sum(1 for r in records if r.get("clip")),
        "first": taken[0] if taken else None,
        "last": taken[-1] if taken else None,
        "days": dict(sorted(days.items())),
        "cameras": dict(cameras.most_common()),
        "bodies": len(serials),
        "no_date": unreadable,
        "photos": records,
    }
    (studio / "index.json").write_text(json.dumps(index, indent=1))
    return index


def nice(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%a %b %-d, %Y %-I:%M %p").replace("AM", "am").replace("PM", "pm")
    except (TypeError, ValueError):
        return "?"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: index.py <session folder>")
    ix = build(sys.argv[1])
    print(f"{ix['count']} photos or clips indexed in {ix['seconds']} s")
    print(f"Taken: {nice(ix['first'])} to {nice(ix['last'])}")
    for day, n in ix["days"].items():
        print(f"  {day}: {n}")
    print("Cameras: " + ", ".join(f"{c} ({n})" for c, n in ix["cameras"].items()) + f"; {ix['bodies']} camera bod{'y' if ix['bodies'] == 1 else 'ies'} by serial")
    if ix["no_date"]:
        print(f"No date found for {len(ix['no_date'])}: " + ", ".join(ix["no_date"][:5]) + (" ..." if len(ix["no_date"]) > 5 else ""))
