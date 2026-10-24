#!/usr/bin/env python3
"""Find the shoots on a card from the gaps in the capture times. Reads
_studio/index.json, writes _studio/groups.json, and pulls a few previews per
group into _studio/groups/ so a contact sheet can be made for the first look.

A new group starts when the camera was quiet for longer than --gap minutes
(default 15) or the day changed. This is the first pass only: it over-splits
on purpose (a wedding's ceremony and reception come out as two groups), and
the groups carry the gap before them so the next step, Claude looking at one
preview per group, can say "same shoot" and merge. Nothing is moved or
renamed here; this only describes what is on the card.

    python3 groups.py "<session folder>" [--gap 15] [--previews 4]
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def spread(items, count):
    if len(items) <= count:
        return list(items)
    step = (len(items) - 1) / (count - 1)
    return [items[round(i * step)] for i in range(count)]


def find_groups(photos, gap_minutes):
    dated = sorted((p for p in photos if p.get("taken")), key=lambda p: p["taken"])
    groups, cur, prev_t = [], [], None
    for p in dated:
        t = datetime.fromisoformat(p["taken"])
        if cur and (t.date() != prev_t.date() or (t - prev_t).total_seconds() > gap_minutes * 60):
            groups.append(cur)
            cur = []
        cur.append(p)
        prev_t = t
    if cur:
        groups.append(cur)

    out, prev_end = [], None
    for i, g in enumerate(groups, 1):
        start, end = datetime.fromisoformat(g[0]["taken"]), datetime.fromisoformat(g[-1]["taken"])
        gap_before = round((start - prev_end).total_seconds() / 60) if prev_end and prev_end.date() == start.date() else None
        cams = Counter(p.get("serial") or p.get("camera") or "?" for p in g)
        out.append({
            "id": f"g{i:02d}",
            "start": g[0]["taken"], "end": g[-1]["taken"],
            "minutes": round((end - start).total_seconds() / 60),
            "count": len(g),
            "gap_before_min": gap_before,
            "bodies": len(cams),
            "lenses": [l for l, _ in Counter(p.get("lens") for p in g if p.get("lens")).most_common(2)],
            "files": [p["file"] for p in g],
        })
        prev_end = end
    return out, [p["file"] for p in photos if not p.get("taken")]


def make_preview(src, dst, size=700):
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", "-Z", str(size), str(src), "--out", str(dst)],
                       capture_output=True, text=True)
    return r.returncode == 0 and dst.exists()


def clock(iso):
    return datetime.fromisoformat(iso).strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--gap", type=float, default=15, help="minutes of quiet that start a new group")
    ap.add_argument("--previews", type=int, default=4, help="previews per group, 0 for none")
    a = ap.parse_args()
    session = Path(a.session)
    studio = session / "_studio"
    index = json.loads((studio / "index.json").read_text())
    groups, undated = find_groups(index["photos"], a.gap)

    if a.previews:
        folder = studio / "groups"
        folder.mkdir(exist_ok=True)
        for g in groups:
            g["previews"] = []
            for f in spread(g["files"], a.previews):
                dst = folder / f"{g['id']}_{Path(f).stem}.jpg"
                if dst.exists() or make_preview(session / f, dst):
                    g["previews"].append(dst.name)

    (studio / "groups.json").write_text(json.dumps({
        "session": index.get("session"), "gap_minutes": a.gap,
        "built": datetime.now().isoformat(timespec="seconds"),
        "groups": groups, "undated": undated}, indent=1))

    day = None
    for g in groups:
        d = g["start"][:10]
        if d != day:
            day = d
            print(f"\n{datetime.fromisoformat(g['start']).strftime('%A, %B %-d, %Y')}")
        gap = f"after a {g['gap_before_min']} min gap" if g["gap_before_min"] is not None else "first of the day"
        bodies = f", {g['bodies']} cameras" if g["bodies"] > 1 else ""
        print(f"  {g['id']}  {clock(g['start'])} to {clock(g['end'])}  {g['count']:>5} photos  {g['minutes']:>4} min   {gap}{bodies}")
    if undated:
        print(f"\n{len(undated)} files with no date, left out of the groups")
    print(f"\n{len(groups)} groups at a {a.gap:g} minute gap. Written to {studio / 'groups.json'}")


if __name__ == "__main__":
    main()
