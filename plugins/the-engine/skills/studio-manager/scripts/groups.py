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
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()


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
    return pictures.make_jpeg(src, dst, size, 80)


def clock(iso):
    return this_computer.strftime(datetime.fromisoformat(iso), "%-I:%M %p").replace("AM", "am").replace("PM", "pm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--gap", type=float, default=15, help="minutes of quiet that start a new group")
    ap.add_argument("--previews", type=int, default=4, help="previews per group, 0 for none")
    a = ap.parse_args()
    session = Path(a.session)
    studio = session / "_studio"
    index = json.loads((studio / "index.json").read_text(encoding="utf-8"))
    groups, undated = find_groups(index["photos"], a.gap)

    if a.previews:
        ok, words = pictures.ready()
        if not ok:
            # stop before groups.json is written, so the next run (once the add-on is in) does this step again
            print(f"STOP: {words} The photos are already backed up and checked. Once it is in, run the backup again "
                  "and it picks up right here.", flush=True)
            return 1
        folder = studio / "groups"
        folder.mkdir(exist_ok=True)
        for g in groups:
            g["previews"] = []
            for f in spread(g["files"], a.previews):
                dst = folder / f"{g['id']}_{Path(f).stem}.jpg"
                if dst.exists() or make_preview(session / f, dst):
                    g["previews"].append(dst.name)
                else:
                    why = pictures.why_not(session / f)
                    if why:
                        print(f"could not show {Path(f).name}: {why}", flush=True)

    (studio / "groups.json").write_text(json.dumps({
        "session": index.get("session"), "gap_minutes": a.gap,
        "built": datetime.now().isoformat(timespec="seconds"),
        "groups": groups, "undated": undated}, indent=1), encoding="utf-8")

    day = None
    for g in groups:
        d = g["start"][:10]
        if d != day:
            day = d
            print(f"\n{this_computer.strftime(datetime.fromisoformat(g['start']), '%A, %B %-d, %Y')}")
        gap = f"after a {g['gap_before_min']} min gap" if g["gap_before_min"] is not None else "first of the day"
        bodies = f", {g['bodies']} cameras" if g["bodies"] > 1 else ""
        print(f"  {g['id']}  {clock(g['start'])} to {clock(g['end'])}  {g['count']:>5} photos  {g['minutes']:>4} min   {gap}{bodies}")
    if undated:
        print(f"\n{len(undated)} files with no date, left out of the groups")
    print(f"\n{len(groups)} groups at a {a.gap:g} minute gap. Written to {studio / 'groups.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
