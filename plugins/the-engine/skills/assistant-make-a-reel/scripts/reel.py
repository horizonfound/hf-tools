#!/usr/bin/env python3
"""The Studio by Horizon Found. From a folder of edited photos to a CapCut project cut
on the beat. Claude does the choosing; this does the counting.

    python3 reel.py sheet --folder "<edited photos>" [--shoot "Black-sand beach"]
        One numbered contact sheet (or a few, 48 photos each) for Claude to look at,
        plus photos.json: number, file, which way up. Nothing in the folder changes;
        the sheet goes in ~/.studio/reels/<shoot>/.

    python3 reel.py songs [<folder> ...]
        Song files on this computer, newest first (Downloads, Music, Desktop, and any
        folders named), with their length.

    python3 reel.py make --folder "<edited photos>" --picks 7,2,11,4,9,1 --song "<file>" | --song none
        [--shoot "Black-sand beach"] [--name "Black-sand beach reel"] [--hook "Words on the first photo"]
        [--rhythm steady|build] [--song-start 41.3] [--fit] [--dry-run] [--store <CapCut projects>]
        Finds the beat, starts the song where it picks up, lays the photos in that
        order one cut per beat-step, and writes the CapCut project (capcut.py).
        --dry-run prints the plan and writes nothing.

Rhythm: every photo holds the same number of beats (about a second each), the
first and last hold twice as long. "build" quickens the last third, then
settles on the last photo. No song: an even 100 beats a minute, so music can be
added in CapCut or Instagram.

Exit codes: 0 done · 2 stop (folder, photo or song missing) · 8 CapCut is open (close it, run again).
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "studio-manager" / "scripts"))
import beats_lite  # noqa: E402
import capcut  # noqa: E402

PHOTOS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}
SONGS = {".mp3", ".m4a", ".aac", ".wav", ".aif", ".aiff", ".flac"}
HOME = Path(os.environ.get("STUDIO_HOME") or Path.home() / ".studio")
PER_SHEET = 48
TARGET_HOLD = 1.1      # seconds a photo stays up, before rounding to whole beats
EVEN_BPM = 100.0


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def slug(s):
    return re.sub(r"[^\w\-]+", "-", s.strip()).strip("-") or "reel"


def edited_photos(folder):
    folder = Path(folder)
    if not folder.is_dir():
        say(f"STOP: no folder at {folder}")
        sys.exit(2)
    out = [p for p in sorted(folder.iterdir(), key=lambda p: p.name.lower())
           if p.is_file() and p.suffix.lower() in PHOTOS and not p.name.startswith(".")]
    if not out:
        say(f"STOP: no photos in {folder}")
        sys.exit(2)
    return out


def workdir(shoot, folder):
    d = HOME / "reels" / slug(shoot or Path(folder).name)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- the contact sheet

def _thumb(src, size, tmp):
    """(w, h, rows) of a small copy: sips on a Mac, Pillow if it happens to be there."""
    if shutil.which("sips"):
        import sheet
        return sheet.thumb(src, size, tmp)
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((size, size))
        w, h = im.size
        raw = im.tobytes()
    return w, h, [raw[y * w * 3:(y + 1) * w * 3] for y in range(h)]


def make_sheets(photos, out_dir, cell=200, per_row=6):
    import sheet
    tmp = out_dir / ".thumb.bmp"
    paths = []
    gap, tag = 8, 34
    for s in range(0, len(photos), PER_SHEET):
        chunk = photos[s:s + PER_SHEET]
        rows_n = (len(chunk) + per_row - 1) // per_row
        W = per_row * (cell + gap) + gap
        H = rows_n * (cell + gap) + gap
        cv = sheet.Canvas(W, H, bg=(30, 30, 30))
        for i, p in enumerate(chunk):
            n = s + i + 1
            x = gap + (i % per_row) * (cell + gap)
            y = gap + (i // per_row) * (cell + gap)
            t = _thumb(p, cell, tmp)
            if t:
                w, h, rows = t
                cv.paste(x + (cell - w) // 2, y + (cell - h) // 2, w, h, rows)
            cv.rect(x, y, tag + 12 * len(str(n)), tag, (20, 20, 20))
            cv.text(x + 6, y + 6, str(n), scale=3, color=(240, 127, 90))
        out = out_dir / f"sheet-{s // PER_SHEET + 1}.png"
        sheet.write_png(out, W, H, cv.rows)
        paths.append(out)
    if tmp.exists():
        tmp.unlink()
    return paths


def cmd_sheet(a):
    photos = edited_photos(a.folder)
    wd = workdir(a.shoot, a.folder)
    listing = []
    for i, p in enumerate(photos, 1):
        w, h = capcut.photo_size(p)
        way = "tall" if h > w * 1.05 else "wide" if w > h * 1.05 else "square"
        listing.append({"n": i, "file": str(p), "w": w, "h": h, "way": way})
    (wd / "photos.json").write_text(json.dumps({"folder": str(Path(a.folder)), "photos": listing}, indent=1))
    try:
        sheets = make_sheets(photos, wd)
    except Exception as e:  # a sheet is a convenience; the numbered list still works
        sheets = []
        say(f"(could not draw the sheet: {e})")
    tall = sum(1 for x in listing if x["way"] == "tall")
    say(f"{len(photos)} edited photos ({tall} tall, {len(photos) - tall} wide or square).")
    for s in sheets:
        say(f"Sheet: {s}")
    say(f"List: {wd / 'photos.json'}")


# ---------------------------------------------------------------- songs

def cmd_songs(a):
    home = Path.home()
    places = [Path(x).expanduser() for x in a.folders] + [home / "Downloads", home / "Music", home / "Desktop"]
    found, seen = [], set()
    for top in places:
        if not top.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and not d.endswith((".app", ".photoslibrary"))
                           and d not in ("Music Library.musiclibrary", "node_modules")]
            if len(Path(dirpath).parts) - len(top.parts) > 3:
                dirnames[:] = []
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() in SONGS and not fn.startswith(".") and str(p) not in seen:
                    seen.add(str(p))
                    try:
                        found.append((p.stat().st_mtime, p))
                    except OSError:
                        pass
    if not found:
        say("No song files found. Download the song you want (mp3 or m4a) and tell me, or make the reel with no song.")
        sys.exit(7)
    found.sort(reverse=True)
    for i, (mt, p) in enumerate(found[:12], 1):
        secs = capcut.song_length(p)
        say(f"{i:2}. {p.name}  ({int(secs // 60)}:{int(secs % 60):02d}, {time.strftime('%b %d', time.localtime(mt))})  {p.parent}")


# ---------------------------------------------------------------- the plan

def beats_per_photo(period):
    """Whole beats closest to about a second a photo, never faster than 0.5 s."""
    best = min((1, 2, 4), key=lambda k: abs(k * period - TARGET_HOLD))
    while best * period < 0.5:
        best *= 2
    return best


def plan_reel(photos, song, rhythm="steady", song_start=None, fit=False):
    """photos: list of {path, w, h}. Returns (plan pieces, facts for Claude to tell them)."""
    if song:
        info = beats_lite.analyze(song)
        if not info["ok"]:
            return None, {"problem": f"I couldn't find the beat in {Path(song).name}: {info.get('reason')}."}
        period = info["period"]
    else:
        period = 60.0 / EVEN_BPM
        info = {"beats": [i * period for i in range(400)], "energy": [], "duration": 400 * period, "tempo": EVEN_BPM}
    k = beats_per_photo(period)
    n = len(photos)
    steps = [k] * n
    if n >= 2:
        steps[0] = 2 * k
        steps[-1] = 2 * k
    if rhythm == "build" and n >= 6 and k >= 2:
        for i in range(n - 1 - n // 3, n - 1):
            steps[i] = k // 2
    need_beats = sum(steps)
    need = need_beats * period
    beats = info["beats"]
    if song_start is None:
        start = beats_lite.best_start(info, need + period) if song else 0.0
    else:
        start = song_start
    # start on the beat at or after the chosen moment
    i0 = next((i for i, b in enumerate(beats) if b >= start - 0.02), None)
    if i0 is None or i0 + need_beats >= len(beats):
        i0 = 0
        if need_beats >= len(beats):
            return None, {"problem": "That song is too short for this many photos. Pick fewer photos or a longer song."}
    start = beats[i0]
    cuts = [beats[i0]]
    j = i0
    for s in steps:
        j += s
        cuts.append(beats[j])
    out = []
    for p, a, b in zip(photos, cuts, cuts[1:]):
        out.append({"path": p["path"], "w": p.get("w", 0), "h": p.get("h", 0),
                    "start": round(a - start, 4), "dur": round(b - a, 4), "fill": not fit})
    facts = {"tempo": info.get("tempo"), "beats_per_photo": k, "length": round(cuts[-1] - start, 2),
             "song_from": round(start, 2) if song else None,
             "wide": [i + 1 for i, p in enumerate(photos) if p.get("w", 0) > p.get("h", 0) * 1.05]}
    return out, facts


def cmd_make(a):
    listing_file = workdir(a.shoot, a.folder) / "photos.json"
    if listing_file.is_file() and json.loads(listing_file.read_text()).get("folder") == str(Path(a.folder)):
        listing = json.loads(listing_file.read_text())["photos"]
    else:
        listing = [{"n": i, "file": str(p), "w": 0, "h": 0} for i, p in enumerate(edited_photos(a.folder), 1)]
    by_n = {x["n"]: x for x in listing}
    try:
        picks = [int(x) for x in re.split(r"[,\s]+", a.picks.strip()) if x]
    except ValueError:
        say("STOP: --picks is the photo numbers in order, like 7,2,11,4")
        sys.exit(2)
    bad = [n for n in picks if n not in by_n]
    if bad or not picks:
        say(f"STOP: no photo numbered {', '.join(map(str, bad))} on the sheet." if bad else "STOP: no photos picked.")
        sys.exit(2)
    photos = []
    for n in picks:
        x = by_n[n]
        w, h = (x["w"], x["h"]) if x.get("w") else capcut.photo_size(x["file"])
        photos.append({"path": x["file"], "w": w, "h": h})
    song = None if a.song.lower() in ("none", "no", "") else str(Path(a.song).expanduser())
    if song and not Path(song).is_file():
        say(f"STOP: no song at {song}")
        sys.exit(2)
    pieces, facts = plan_reel(photos, song, a.rhythm, a.song_start, a.fit)
    if pieces is None:
        say(facts["problem"])
        sys.exit(2)
    name = a.name or f"{a.shoot or Path(a.folder).name} reel"
    plan = {"name": name, "photos": pieces,
            "song": ({"path": song, "from": facts["song_from"], "fade_out": 0.5,
                      "length": capcut.song_length(song)} if song else None),
            "hook": {"text": a.hook, "dur": pieces[0]["dur"]} if a.hook else None}
    wd = workdir(a.shoot, a.folder)
    (wd / "reel.json").write_text(json.dumps({"plan": plan, "facts": facts}, indent=1))
    when = ""
    if song:
        f = facts["song_from"]
        if f < 1:
            when = ", starting the song at the top"
        elif f < 60:
            when = f", starting the song {f:.0f} seconds in"
        else:
            when = f", starting the song at {int(f // 60)}:{int(f % 60):02d}"
    if song:
        say(f"Plan: {len(pieces)} photos, {facts['length']:.1f} seconds, a cut every {facts['beats_per_photo']} "
            f"beat{'s' if facts['beats_per_photo'] > 1 else ''} at about {facts['tempo']:.0f} beats a minute{when}.")
    else:
        say(f"Plan: {len(pieces)} photos, {facts['length']:.1f} seconds, a new photo every "
            f"{pieces[min(1, len(pieces) - 1)]['dur']:.1f} seconds, no song (add one in CapCut or Instagram).")
    if facts["wide"]:
        say(f"Wide photos zoomed to fill the screen: {', '.join(map(str, facts['wide']))} (slide them in CapCut if a face is cut off).")
    if a.dry_run:
        say(f"Dry run: nothing written. The plan is in {wd / 'reel.json'}")
        return
    store = Path(a.store).expanduser() if a.store else capcut.default_store()
    dest, draft = capcut.write(plan, store, a.ignore_open)
    say(f"Made \"{dest.name}\" in CapCut. Open CapCut and it's at the top of your projects.")
    rec = json.loads((wd / "reel.json").read_text())
    rec["capcut_project"] = str(dest)
    (wd / "reel.json").write_text(json.dumps(rec, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--folder", required=True)
    s.add_argument("--shoot")
    g = sub.add_parser("songs")
    g.add_argument("folders", nargs="*")
    m = sub.add_parser("make")
    m.add_argument("--folder", required=True)
    m.add_argument("--picks", required=True)
    m.add_argument("--song", required=True)
    m.add_argument("--shoot")
    m.add_argument("--name")
    m.add_argument("--hook")
    m.add_argument("--rhythm", choices=["steady", "build"], default="steady")
    m.add_argument("--song-start", type=float)
    m.add_argument("--fit", action="store_true", help="show whole wide photos with bars instead of filling the screen")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--store")
    m.add_argument("--ignore-open", action="store_true")
    a = ap.parse_args()
    {"sheet": cmd_sheet, "songs": cmd_songs, "make": cmd_make}[a.cmd](a)


if __name__ == "__main__":
    main()
