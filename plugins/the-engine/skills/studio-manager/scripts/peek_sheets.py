#!/usr/bin/env python3
"""Thin a shoot down to its moments and lay them out on numbered pages, so Claude can pick the
sneak peeks with a few looks instead of thousands (rule 6: scripts shortlist, Claude looks).

    python3 peek_sheets.py make "<backup folder or records>" [--gap 3] [--max 100] [--per-page 20]
    python3 peek_sheets.py closer "<backup>" s1=14,3,27,9,41,18,22,5,61,70 [s2=...]
    python3 peek_sheets.py pick "<backup>" s1=14,3,27,9,41,18 [s2=...] [--by "Claude, from the pages"]

make: for every shoot, one frame per burst (a new burst starts after --gap seconds of quiet;
the middle frame of each burst is kept), at most --max moments spread across the shoot, a small
preview of each (the Mac's own sips; nothing installed) into records/peeks/<shoot>/, and pages of
--per-page numbered thumbnails into records/peek-sheets/<shoot>-p1.png, -p2.png ...
A list of what is on each page goes in records/peek-sheets.json.

closer: a shortlist (ten or so per shoot) laid out big, four to a page at full preview size, into
records/peek-sheets/<shoot>-close1.png ..., so soft focus, a blink or a half-closed eye and an
awkward expression can be seen before anything is chosen (the small pages hide all three).

pick: turn the numbers Claude chose (the first is the hero) into records/sneak-peeks.json, in the
shape sneak_peeks.py and the report read. Shoots not mentioned keep what they had.
Reads the verified copy only. Nothing on the card is ever opened, nothing is changed anywhere.
Exit codes: 0 done, 1 a problem, 2 nothing to do.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from where import locate  # noqa: E402
import sheet  # noqa: E402

PHOTO = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def preview(src, dst, size):
    """A small JPEG of the photo. sips on a Mac; Pillow only as a stand-in where sips does not exist (tests)."""
    if shutil.which("sips"):
        r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", "-Z", str(size), str(src), "--out", str(dst)],
                           capture_output=True)
        return r.returncode == 0 and dst.exists()
    try:
        from PIL import Image
        im = Image.open(src)
        im.thumbnail((size, size))
        im.convert("RGB").save(dst, quality=80)
        return True
    except Exception:
        return False


def thumb_rows(src, size, tmp):
    """(w, h, rows) for the page: sips to BMP on a Mac, Pillow as the stand-in elsewhere."""
    if shutil.which("sips"):
        return sheet.thumb(src, size, tmp)
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((size, size))
        w, h = im.size
        raw = im.tobytes()
        return w, h, [raw[y * w * 3:(y + 1) * w * 3] for y in range(h)]
    except Exception:
        return None


def seconds(iso):
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return None


def moments(photos, gap):
    """One photo per burst: a burst is frames less than `gap` seconds apart; keep the middle frame."""
    out, burst = [], []
    last = None
    for p in photos:
        t = p["_t"]
        if last is not None and t - last > gap and burst:
            out.append(burst[len(burst) // 2])
            burst = []
        burst.append(p)
        last = t
    if burst:
        out.append(burst[len(burst) // 2])
    return out


def spread(items, n):
    if len(items) <= n:
        return items
    step = (len(items) - 1) / (n - 1)
    return [items[round(i * step)] for i in range(n)]


def make(night, gap, cap, per_page, size):
    root, studio = locate(night)
    index = json.loads((studio / "index.json").read_text())
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]}
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    by_file = {p["file"]: p for p in index["photos"]}
    out_dir = studio / "peek-sheets"
    out_dir.mkdir(exist_ok=True)
    tmp = out_dir / ".tmp.bmp"
    result = {"gap_seconds": gap, "per_page": per_page, "shoots": {}}
    cols, rows_per = 5, max(1, per_page // 5)
    cell_w, cell_h, pad, label_h = size, int(size * 1.0), 8, 26
    for s in shoots:
        files = [f for g in s.get("groups", []) if g in groups for f in groups[g].get("files", [])]
        photos = []
        for f in files:
            p = by_file.get(f)
            if not p or Path(f).suffix.lower() not in PHOTO:
                continue
            t = seconds(p.get("taken"))
            if t is None:
                continue
            photos.append({"file": f, "taken": p["taken"], "_t": t})
        photos.sort(key=lambda p: (p["_t"], p["file"]))
        chosen = spread(moments(photos, gap), cap)
        pdir = studio / "peeks" / s["id"]
        pdir.mkdir(parents=True, exist_ok=True)
        listed = []
        for i, p in enumerate(chosen, 1):
            dst = pdir / f"{i:03d}.jpg"
            if dst.exists() or preview(root / p["file"], dst, 700):
                listed.append({"n": i, "file": p["file"], "taken": p["taken"], "preview": f"peeks/{s['id']}/{dst.name}"})
        pages = []
        for pi in range(0, len(listed), per_page):
            chunk = listed[pi:pi + per_page]
            W = cols * (cell_w + pad) + pad
            H = rows_per * (cell_h + label_h + pad) + pad
            cv = sheet.Canvas(W, H)
            for j, m in enumerate(chunk):
                cx, cy = j % cols, j // cols
                x = pad + cx * (cell_w + pad)
                y = pad + cy * (cell_h + label_h + pad)
                cv.rect(x, y, cell_w, label_h, (40, 40, 40))
                cv.text(x + 6, y + 4, f"{m['n']}", scale=2, color=(240, 127, 90))
                t = thumb_rows(studio / m["preview"], size, tmp)
                if not t:
                    continue
                w, h, rws = t
                if h > cell_h:
                    rws = rws[(h - cell_h) // 2:(h - cell_h) // 2 + cell_h]
                    h = cell_h
                cv.paste(x + max(0, (cell_w - w) // 2), y + label_h + max(0, (cell_h - h) // 2), w, h, rws)
            page = out_dir / f"{s['id']}-p{pi // per_page + 1}.png"
            sheet.write_png(page, W, H, cv.rows)
            pages.append(str(page))
        result["shoots"][s["id"]] = {"name": s.get("name") or s.get("suggested", ""), "photos": len(photos),
                                     "moments": len(listed), "pages": pages, "list": listed}
        say(f"{s['id']} {s.get('name') or s.get('suggested', '')}: {len(photos):,} photos, {len(listed)} moments on {len(pages)} page(s)")
    if tmp.exists():
        tmp.unlink()
    p = studio / "peek-sheets.json"
    p.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


def closer(night, picks):
    """The shortlist, big: two columns, each photo at its full 700 px preview size, four to a page."""
    root, studio = locate(night)
    sheets = json.loads((studio / "peek-sheets.json").read_text())["shoots"]
    out_dir = studio / "peek-sheets"
    tmp = out_dir / ".tmp.bmp"
    cols, per_page, cell, pad, label_h = 2, 4, 700, 10, 28
    for spec in picks:
        sid, _, nums = spec.partition("=")
        if sid not in sheets:
            say(f"STOP: no shoot {sid} on the pages.")
            return 1
        by_n = {m["n"]: m for m in sheets[sid]["list"]}
        want = []
        for n in [x.strip() for x in nums.split(",") if x.strip()]:
            m = by_n.get(int(n)) if n.isdigit() else None
            if not m:
                say(f"STOP: {sid} has no photo numbered {n}.")
                return 1
            want.append(m)
        pages = []
        for pi in range(0, len(want), per_page):
            chunk = want[pi:pi + per_page]
            rows_per = (len(chunk) + cols - 1) // cols
            W = cols * (cell + pad) + pad
            H = rows_per * (cell + label_h + pad) + pad
            cv = sheet.Canvas(W, H)
            for j, m in enumerate(chunk):
                cx, cy = j % cols, j // cols
                x = pad + cx * (cell + pad)
                y = pad + cy * (cell + label_h + pad)
                cv.rect(x, y, cell, label_h, (40, 40, 40))
                cv.text(x + 6, y + 4, f"{m['n']}", scale=3, color=(240, 127, 90))
                t = thumb_rows(studio / m["preview"], cell, tmp)
                if not t:
                    continue
                w, h, rws = t
                cv.paste(x + max(0, (cell - w) // 2), y + label_h + max(0, (cell - h) // 2), w, h, rws)
            page = out_dir / f"{sid}-close{pi // per_page + 1}.png"
            sheet.write_png(page, W, H, cv.rows)
            pages.append(str(page))
        say(f"{sid}: {len(want)} up close on {len(pages)} page(s)")
        for pg in pages:
            say(f"   {pg}")
    if tmp.exists():
        tmp.unlink()
    return 0


def current_path(studio, f):
    """The photo's path now, if a rename moved it since the pages were made: same shoot number and
    camera frame name, read from the index (which every rename keeps up to date)."""
    try:
        index = json.loads((studio / "index.json").read_text())["photos"]
    except (OSError, ValueError):
        return f
    stem = Path(f).stem
    tail = "_".join(stem.split("_")[-3:]) if stem.count("_") >= 2 else stem  # NNNN_<camera frame>
    for p in index:
        if p["file"] == f:
            return f
    for p in index:
        if Path(p["file"]).stem.endswith(tail):
            return p["file"]
    return f


def pick(night, picks, by):
    root, studio = locate(night)
    sheets = json.loads((studio / "peek-sheets.json").read_text())["shoots"]
    pj = studio / "sneak-peeks.json"
    existing = json.loads(pj.read_text()).get("picks", []) if pj.exists() else []
    chosen_shoots = set()
    new = []
    for spec in picks:
        sid, _, nums = spec.partition("=")
        if sid not in sheets:
            say(f"STOP: no shoot {sid} on the pages.")
            return 1
        by_n = {m["n"]: m for m in sheets[sid]["list"]}
        for n in [x.strip() for x in nums.split(",") if x.strip()]:
            m = by_n.get(int(n)) if n.isdigit() else None
            if not m:
                say(f"STOP: {sid} has no photo numbered {n}.")
                return 1
            new.append({"file": current_path(studio, m["file"]), "shoot": sid, "n": m["n"]})
        chosen_shoots.add(sid)
    kept = [p for p in existing if p.get("shoot") not in chosen_shoots]
    pj.write_text(json.dumps({"picks": kept + new, "picked_by": by}, indent=1, ensure_ascii=False))
    for sid in chosen_shoots:
        say(f"{sid}: {sum(1 for p in new if p['shoot'] == sid)} sneak peeks")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("night")
    m.add_argument("--gap", type=float, default=3.0, help="seconds of quiet that end a burst")
    m.add_argument("--max", type=int, default=100, help="most moments per shoot")
    m.add_argument("--per-page", type=int, default=20)
    m.add_argument("--thumb", type=int, default=240)
    c = sub.add_parser("closer"); c.add_argument("night"); c.add_argument("picks", nargs="+", help="s1=14,3,27,9,41,18,22,5 (the shortlist)")
    k = sub.add_parser("pick"); k.add_argument("night"); k.add_argument("picks", nargs="+", help="s1=14,3,27,9,41,18 (hero first)")
    k.add_argument("--by", default="Claude, from the pages")
    a = ap.parse_args()
    if a.cmd == "make":
        return make(a.night, a.gap, a.max, a.per_page, a.thumb)
    if a.cmd == "closer":
        return closer(a.night, a.picks)
    return pick(a.night, a.picks, a.by)


if __name__ == "__main__":
    sys.exit(main())
