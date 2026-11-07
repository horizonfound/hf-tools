#!/usr/bin/env python3
"""The footage look: what Claude runs when the photographer copies "Look through my footage for <shoot>" (or
"... and follow my notes") from the reel page into the chat. Nicole's footage.py (handoff v19), the Assistant's
way. The heavy lifting is here, on the computer, and uses none of the photographer's plan: the stills, the
contact sheets, the sound. Claude then reads the sheets (that part uses the plan), takes a closer look at the
promising stretches, and saves the moments it found, which the reel page shows as cards by itself.

    python3 footage.py scan    "<kit>" [--every 2]
            every video in the shoot's Footage folder: its key, length and shape, when it was recorded,
            contact sheets (a still every 1 to 8 s by its length, each labelled with its time), the loudest
            moments, and the photos taken while it was recording (5 s either side). Their notes and the feel
            they picked on the page come first, then the rules.
    python3 footage.py close   "<kit>" <video key or file name> <from> <to> [--every 0.5] [--photo N]
            a closer look at one stretch: a still every half second (at most CLOSE_MOST); --photo N puts the
            finished photo N first, to compare (The reveal only)
    python3 footage.py moments "<kit>" --file <moments.json>
            save the moments Claude chose, as cards on the reel page

moments.json: {"moments": [{"video": "<the key scan printed, or the file name>", "start": 42.0, "end": 46.0,
                            "label": "Laughing at the wave", "photo": 12 or null}, ...],
               "order": "41,10,14-,..."   (optional: the photos for the reel with footage; leave it out and the
                                           page uses the reel's photo pick, which is right: SELECTS rule 6)}
Times are seconds (42.0) or minutes and seconds ("0:42"). Each moment is the clip as it goes in the reel: 3 to
4 seconds (MOMENT_SECONDS), the first never under 3; at most MAX_MOMENTS. A video shorter than 3 seconds may be
used whole, never as the first moment. Anything wrong is refused in plain words and NOTHING is written.

Where Nicole's differs, on purpose (the Assistant's rules):
  * Nothing installed: the stills come from the Mac's own AVFoundation (video.py, through this_computer), the
    sheets are drawn with sheet.py's pure-Python canvas and written as PNG (her Pillow and Arial are not needed),
    the sound is sound.py's. No ffmpeg, no ffprobe, no Pillow on a Mac.
  * Every look goes in a NEW folder: <kit>/.kit/footage/looks/look, "look 2", "look 3"... and "close", "close
    2"... for the close looks (video.fresh_folder). Nothing an earlier look made is cleared away or written
    over; hers emptied its folder first.
  * Each still is labelled with the time AVFoundation really returned (exact, not the nearest keyframe).
  * The sheets carry no title line (the canvas draws only times); each sheet's file name says which video it
    is, and the scan prints the stretch each one covers.
  * The page never sees a path: a video is named by its key (video.key), a moment by its id.
  * The record is the reel page's own (<kit>/.kit/reel-page.json), written whole under its lock with the
    version before kept (reel_page.save); the photographer's own moments stay first. Claude's moments from an
    earlier look are kept in the record ("earlier_looks"), never lost. A style's selection that named an earlier
    moment of the same video, start and end is carried over to its new id (her BUILD.md section 9, step 6).
  * Moments are checked before anything is written: at most 12, 3 to 4 seconds, inside the video, a video in
    the Footage folder, a photo on the numbered list. Hers checked only the count and the video.
  * "order" (her claude_bts) must be the same photos as the reel's photo pick (SELECTS rule 6). Without it the
    page uses that pick, which is the same thing.

On a PC (decision 11, video.py's named gap): stills can't be taken from a video yet, so scan prints each
video's facts, the loud moments and the photos taken while it recorded, makes no sheets, and ends with exit 3
and plain words. close does the same. moments works on a PC as on a Mac (the cards then have no still).

Exit codes: 0 done; 1 stopped (it says why, nothing written); 2 the record was busy, try again; 3 no sheets on
this computer (a PC).

Python 3.9, standard library only.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import reel_page  # noqa: E402
import sheet  # noqa: E402
import pictures  # noqa: E402
import exif_read  # noqa: E402

this_computer.utf8_output()

MAX_MOMENTS = 12                  # Nicole, Nov 6: "the most you should select is 12"
MOMENT_SECONDS = (3.0, 4.0)       # hers: "Save each moment 3 to 4 seconds long"; the opener never under 3
SLACK = 0.02                      # a moment's length may be off by this much (times written to a tenth)
DURING = 5.0                      # hers: a photo taken 5 s before a video started, to 5 s after it ended
CLOSE_EVERY = 0.5                 # hers: a close look has a still every half second
CLOSE_MOST = 48                   # ours: the most stills one close look takes (24 s at a half second)
LABEL_MAX = 80                    # hers: a moment's label is cut at 80 characters
GAP = 6                           # hers
BG = (28, 28, 30)                 # hers: the sheet's background
LABEL_BG, LABEL_INK = (20, 20, 20), (240, 127, 90)     # hers: the time in coral on a dark box
SCALE = 3                         # our letters: 5 x 7 dots, 3 px each (her font was 20 px)
EXIT_NO_SHEETS = 3

# The letters a sheet's labels need: sheet.py's digits, and ":", ".", "-", a space and PHOTO (for --photo).
GLYPHS = dict(sheet.DIGITS)
GLYPHS.update({
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    " ": ["00000"] * 7,
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
})

# The rules, printed where the choice is made (SELECTS.md: "the rule should show up exactly where the choice is
# made, not only in a file"). Her RULES text, with the rest of her footage rules beside it.
RULES = """How to choose (Nicole, Nov 6; the full rules are in the reel skill's footage section):
  PHOTOS FIRST. The photos are the point of the reel; the footage only adds behind-the-scenes moments between them.
  The photos are the same with footage or without: the reel's photo pick, chosen on its own merit (the most
  beautiful and engaging, the ones that tell the best story, with variety and emotion). Never choose, leave out or
  move a photo because of a clip, and never limit the photos to the setting the footage shows.
  MOMENTS: find the best moments, as many as are genuinely good, up to 12 at most (fewer is fine): engaging,
  interesting, real reactions, the photographer and clients looking good. Judge each clip on how it looks; there
  are no banned kinds of moment. Loudness is a hint for where to look, never a reason to pick.
  Save each one 3 to 4 seconds long, starting where the good part starts; the first one never under 3 seconds.
  Their notes come first: find the moments they describe, keep them in the order they describe, always include
  them; if one can't be found, say so plainly and never invent one. The feel steers which moments.
  Match a photo ("photo": N) only for The reveal, only when it's obvious (same pose, same setting, an angle that
  agrees with where the photographer stood: check with close --photo N). No match is fine; a wrong one is worse.
  A label says what happens, in plain words; never a name or a fact the photographer didn't give.
"""


def say(msg):
    arrange.say(msg)


def stop(msg, code=1):
    say("STOP: " + msg)
    return code


def layout(w, h):
    """Hers: sheets stay about 1,560 px wide, the most Claude sees in one look, and each still keeps the video's
    shape: a tall phone video gets tall cells big enough to read faces and which way the camera points.
    (columns, cell width, cell height, stills a sheet)."""
    if h > w * 1.2:
        return 7, 216, 384, 14          # tall: 7 across, 2 rows
    if w > h * 1.2:
        return 4, 384, 216, 20          # wide: 4 across, 5 rows
    return 6, 252, 252, 24


def every_for(length):
    """Hers: how often a still is taken, by the video's length (1 s up to 2 minutes ... 8 s past 40)."""
    return 1 if length <= 120 else 2 if length <= 600 else 3 if length <= 900 else 4 if length <= 1200 else 5 if length <= 2400 else 8


def mmss(t):
    """A time as the page shows it (0:04, 1:02.5), to a tenth."""
    return reel_page.mmss(round(float(t), 1))


def secs(s):
    """Seconds from 42, 42.5, "42.5" or "0:42.5". None for anything else."""
    if isinstance(s, bool):
        return None
    if isinstance(s, (int, float)):
        return float(s) if math.isfinite(float(s)) else None
    if not isinstance(s, str):
        return None
    s = s.strip()
    m = re.fullmatch(r"(?:(\d{1,3}):)?(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def fit_edge(w, h, cw, ch):
    """The long edge a still is taken at so it fits its cell (never larger than the video)."""
    if not w or not h:
        return max(cw, ch)
    k = min(cw / w, ch / h, 1.0)
    return max(16, int(math.floor(max(w, h) * k)))


# ---------- drawing a sheet ----------

def draw_text(cv, x0, y0, s, scale=SCALE, color=LABEL_INK):
    for ch in s:
        glyph = GLYPHS.get(ch)
        if glyph:
            for gy, line in enumerate(glyph):
                for gx, bit in enumerate(line):
                    if bit == "1":
                        cv.rect(x0 + gx * scale, y0 + gy * scale, scale, scale, color)
        x0 += 6 * scale


def label_box(label, scale=SCALE):
    """(width, height) of a label's dark box: her 12 px of room around the text, 28 px tall."""
    return 6 * scale * len(label) + 12 - scale, 7 * scale + 7


def sheet_size(n, shape):
    cols, cw, ch = shape
    rows = max(1, (n + cols - 1) // cols)
    return cols * (cw + GAP) + GAP, rows * (ch + GAP) + GAP


def draw_sheet(cells, out, shape, tmp):
    """cells: [(picture file or None, label)]. A grid in her layout, each picture centred in its cell with its
    label in a dark box at the top left. Written as a new PNG (out must not be there). Returns the cells' places."""
    cols, cw, ch = shape
    W, H = sheet_size(len(cells), shape)
    cv = sheet.Canvas(W, H, bg=BG)
    places = []
    for i, (pic, label) in enumerate(cells):
        x, y = GAP + (i % cols) * (cw + GAP), GAP + (i // cols) * (ch + GAP)
        shown = None
        if pic is not None:
            t = pictures.thumb_rows(pic, max(cw, ch), tmp)
            if t:
                w, h, rows = t
                if w > cw or h > ch:              # never wider or taller than its cell: the middle of it
                    k = min(cw / w, ch / h)
                    t2 = pictures.thumb_rows(pic, max(1, int(max(w, h) * k)), tmp)
                    if t2:
                        w, h, rows = t2
                if h > ch:
                    rows, h = rows[(h - ch) // 2:(h - ch) // 2 + ch], ch
                if w > cw:
                    cut = (w - cw) // 2
                    rows, w = [r[cut * 3:(cut + cw) * 3] for r in rows], cw
                cv.paste(x + (cw - w) // 2, y + (ch - h) // 2, w, h, rows)
                shown = [w, h]
        bw, bh = label_box(label)
        cv.rect(x, y, min(bw, cw), bh, LABEL_BG)
        draw_text(cv, x + 6, y + 4, label)
        places.append({"x": x, "y": y, "w": cw, "h": ch, "label": label, "shown": shown})
    out = Path(out)
    if os.path.lexists(out):
        raise FileExistsError(str(out))
    sheet.write_png(out, W, H, cv.rows)
    return places


# ---------- the shoot ----------

def find(words):
    """The kit, only when it is a kit in Your Content (the page can only show those)."""
    kit = kit_mod.find_kit(words)
    listed = arrange.kit_by_name(kit.name)
    if listed is None or Path(os.path.realpath(listed)) != Path(os.path.realpath(kit)):
        return None, kit
    return kit, kit


def looks_dir(kit):
    return reel_page.foot_work(kit) / "looks"


def video_of(vids, given):
    """A video by its key (what scan printed) or by its file name. None if it isn't in the Footage folder."""
    if not isinstance(given, str) or not given.strip():
        return None
    g = given.strip()
    if reel_page.KEY.fullmatch(g):
        hit = next((v for v in vids if v["key"] == g), None)
        if hit:
            return hit
    return reel_page.video_by_name(None, g, vids) if vids else None


def photo_times(kit):
    """{photo number: when it was taken, as the camera's own clock says} for the numbered photos that say."""
    rec = kit_mod.load_rec(kit)
    out = {}
    for row in arrange.sheet_rows(kit):
        p = arrange.photo_path(kit, rec, row)
        if p is None:
            continue
        taken = exif_read.read(p).get("taken")
        if not taken:
            continue
        try:
            out[row["n"]] = datetime.fromisoformat(taken)
        except ValueError:
            continue
    return out


def taken_during(times, start, length):
    """Hers: the photos whose clock falls between 5 s before the video started and 5 s after it ended."""
    if start is None:
        return []
    out = []
    for n, t in sorted(times.items()):
        off = (t - start).total_seconds()
        if -DURING <= off <= length + DURING:
            out.append({"photo": n, "at": round(off, 1)})
    return out


def during_words(x, length):
    if x["at"] < 0:
        return "photo %d just before it started (%s s)" % (x["photo"], ("%g" % -x["at"]))
    if x["at"] > length:
        return "photo %d just after it ended" % x["photo"]
    return "photo %d at %s" % (x["photo"], mmss(x["at"]))


def their_notes(kit):
    """(their notes, their feel) as saved on the reel page."""
    saved = reel_page.load(kit).get("saved")
    saved = saved if isinstance(saved, dict) else {}
    ask = saved.get("ask") if isinstance(saved.get("ask"), str) else ""
    feel = saved.get("feel") if isinstance(saved.get("feel"), str) else ""
    return ask.strip(), feel.strip()


def reel_pick(kit):
    nums, marks = arrange.kit_pick(kit_mod.load_rec(kit), "reel")
    return nums, marks


def _sheet_name(i, v, k, what="sheet"):
    stem = this_computer.safe_name(Path(v["name"]).stem, limit=40, fallback="video")
    return "%02d %s - %s %02d.png" % (i, stem, what, k)


def take_stills(vm, v, times, into, name, shape):
    """Stills of one video at these times, fitted to the sheet's cells, in a new folder. (cells, answer)."""
    f = v["facts"]
    edge = fit_edge(f.get("w"), f.get("h"), shape[1], shape[2])
    r = vm.stills(v["path"], times, into, name=name, edge=edge, f=f, deadline=time.time() + 60 + 1.0 * len(times))
    if not r.get("ok"):
        return None, r
    folder = Path(r["folder"])
    cells = []
    for s in r["stills"]:
        if s.get("file"):
            at = float(s.get("at", s.get("asked", 0)))
            cells.append({"asked": float(s["asked"]), "at": round(at, 3), "label": mmss(at), "file": str(folder / s["file"]),
                          "w": s.get("w"), "h": s.get("h")})
    return cells, r


def write_sheets(cells, look, i, v, shape, per, what="sheet", first=None):
    """The cells on sheets of `per`, written in the look folder. first: a cell put before them (--photo)."""
    tmp = look / ".sheet.bmp"
    sheets = []
    allc = ([first] if first else []) + cells
    try:
        for k, s in enumerate(range(0, len(allc), per), 1):
            chunk = allc[s:s + per]
            out = look / _sheet_name(i, v, k, what)
            places = draw_sheet([(c.get("file"), c["label"]) for c in chunk], out, shape[:3], tmp)
            sheets.append({"file": out.name, "path": str(out), "cells": [dict(c, place=p) for c, p in zip(chunk, places)]})
    finally:
        try:
            tmp.unlink()            # our own scratch picture, made a moment ago
        except OSError:
            pass
    return sheets


# ---------- scan ----------

def cmd_scan(kit, every=None):
    vm = reel_page._video()
    if not reel_page.footage_ok(kit):
        return stop("this shoot's Footage folder is a link or not a folder, so I don't look in it.")
    vids = reel_page.list_videos(kit)
    if not vids:
        return stop(f"there's no footage yet. Videos go in the Footage folder inside {reel_page.short_name(kit.name)}: "
                    "on the reel page, Add my footage opens it.")
    ask, feel = their_notes(kit)
    # their notes and their feel first, then the rules (SELECTS.md: "the photographer's notes and feel, then the rules")
    if ask:
        say("Their notes for this reel (follow them: find these moments first, keep them in the order they describe): " + ask)
    else:
        say("Their notes for this reel: none (they wrote nothing in \"Want to direct the reel?\").")
    if feel:
        say(f"They want it to feel {feel}. Choose the photos and the moments that bring that out, and order them to build it; "
            "the photos are still the best ones, with variety and a story.")
    else:
        say("How it should feel: not picked.")
    say("")
    say(RULES)
    nums, marks = reel_pick(kit)
    if nums:
        say("The reel's photo pick (the same with footage or without): "
            + ",".join(f"{n}{m}" for n, m in zip(nums, marks)) + ". Leave \"order\" out of the moments file and the page uses it.")
    else:
        say("NOTE: there is no photo pick for this reel yet. Pick the photos first, exactly as for a reel with no footage "
            "(the reel skill's Step 2, saved with kit.py picks --reel), never to match the footage.")
    with arrange.locked(reel_page.lock_path(kit)):
        rec = reel_page.load(kit)
    own = [m for m in reel_page.moments_of(rec) if m.get("by") == "you"]
    if own:
        say("Their own moments, already on the page (they stay first; don't save the same ones again): "
            + "; ".join(f"{m['video']} {mmss(m['start'])} to {mmss(m['end'])}" for m in own))
    can = vm.avfoundation_here()
    ok_pics, why_pics = pictures.ready()
    look = vm.fresh_folder(looks_dir(kit), "look")
    times_of = photo_times(kit)
    report = {"kit": kit.name, "when": arrange.now_iso(), "notes": ask, "feel": feel, "videos": []}
    say(f"\nThis look: {look}  (a new folder; earlier looks are kept as they were)")
    t_all = time.time()
    n_sheets = 0
    for i, v in enumerate(vids, 1):
        t0 = time.time()
        f = v["facts"]
        if f.get("refused"):
            say(f"\n{i}. {v['name']}: {f['refused']} (left out)")
            report["videos"].append({"key": v["key"], "name": v["name"], "refused": f["refused"]})
            continue
        length = float(f.get("length") or 0)
        ev = float(every) if every else every_for(length)
        cols, cw, ch, per = layout(f.get("w") or 0, f.get("h") or 0)
        n = max(1, int(math.ceil(length / ev - 1e-6)))
        times = [round(k * ev, 3) for k in range(n)]
        cells, sheets, gap = [], [], None
        if can and ok_pics:
            cells, r = take_stills(vm, v, times, look, v["key"], (cols, cw, ch))
            if cells is None:
                gap = r.get("words") or "I couldn't take stills from it."
            elif cells:
                sheets = write_sheets(cells, look, i, v, (cols, cw, ch), per)
        elif not can:
            gap = this_computer.NO_PREVIEW if f.get("codec") not in vm.HEVC else this_computer.HEVC_HELP
        else:
            gap = why_pics
        try:
            db, how = vm.loudness(v["path"], f=f)
        except Exception as e:  # noqa: BLE001  (the sound is a hint for where to look; the look goes on without it)
            db, how = None, f"{e.__class__.__name__}"
        loud = vm.loud_moments(db or [])
        start = vm.recorded_local(f)
        during = taken_during(times_of, start, length)
        shape = "tall" if ch > cw else "wide" if cw > ch else "square"
        item = {"key": v["key"], "name": v["name"], "length": round(length, 2), "w": f.get("w"), "h": f.get("h"),
                "shape": shape, "recorded": f.get("recorded") or "", "recorded_from": f.get("recorded_from") or "",
                "has_audio": bool(f.get("has_audio")), "every": ev, "layout": [cols, cw, ch, per],
                "stills": [{k: c[k] for k in ("asked", "at", "label", "w", "h")} for c in cells],
                "sheets": [{"file": s["file"], "from": s["cells"][0]["label"], "to": s["cells"][-1]["label"],
                            "cells": [{"label": c["label"], "at": c["at"], "place": c["place"]} for c in s["cells"]]} for s in sheets],
                "no_sheets": gap, "loud": loud, "sound": how if db is None else ("no sound" if not f.get("has_audio") else "read"),
                "photos_during": during, "took": round(time.time() - t0, 1)}
        report["videos"].append(item)
        n_sheets += len(sheets)
        rec_words = f", recorded {start:%b %d %H:%M:%S}" if start else ""
        say(f"\n{i}. {v['name']}  (key {v['key']}): {mmss(length)} long, {f.get('w')}x{f.get('h')} {shape}{rec_words}. "
            + (f"{len(cells)} stills (one every {ev:g} s) on {len(sheets)} sheet{'s' if len(sheets) != 1 else ''}, in {item['took']} s."
               if sheets else "No sheets: " + str(gap)))
        for s in sheets:
            say(f"  sheet, {s['cells'][0]['label']} to {s['cells'][-1]['label']}: {s['path']}")
        if loud:
            say("  Loudest moments (laughs, squeals, talking up): " + ", ".join(f"{mmss(x['at'])} (+{x['above_room']} dB)" for x in loud))
        elif not f.get("has_audio"):
            say("  No sound in this video.")
        elif db is None:
            say(f"  I couldn't read its sound ({how}).")
        else:
            say("  Nothing jumps out of the sound.")
        if during:
            say("  Photos taken while this was recording (if the camera's and phone's clocks agree): "
                + ", ".join(during_words(x, length) for x in during))
        elif times_of and start:
            say("  No photos were taken while this was recording, going by the clocks (they may not agree).")
        elif not start:
            say("  The video doesn't say when it was recorded, so I can't match photos to it by the clock.")
    (look / "scan.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    say(f"\nDone in {round(time.time() - t_all, 1)} s.")
    if not n_sheets:
        say("NOTE: no sheets were made, so there is nothing to look through on this computer. "
            + ("Stills can't be taken from a video on a PC yet." if not can else ""))
        return EXIT_NO_SHEETS
    say(f"Next: read each sheet once ({n_sheets} in all). Then a close look only at the promising stretches, a handful at most: "
        f"footage.py close \"{kit.name}\" <key> <from> <to> (add --photo N for The reveal). Then save: "
        f"footage.py moments \"{kit.name}\" --file <moments.json>.")
    return 0


# ---------- close ----------

def cmd_close(kit, given, a, b, every=CLOSE_EVERY, photo=None):
    vm = reel_page._video()
    vids = reel_page.list_videos(kit)
    v = video_of(vids, given)
    if v is None:
        return stop(f"there's no video \"{given}\" in this shoot's Footage folder. Use the key the scan printed.")
    f = v["facts"]
    if f.get("refused"):
        return stop(f"{v['name']}: {f['refused']}")
    length = float(f.get("length") or 0)
    s, e = secs(a), secs(b)
    if s is None or e is None or e <= s or s < 0:
        return stop("give the stretch as two times, the first before the second (like 0:42 0:50, or 42 50).")
    if s >= length:
        return stop(f"{v['name']} is only {mmss(length)} long.")
    e = min(e, length)
    try:
        every = float(every)
    except (TypeError, ValueError):
        every = CLOSE_EVERY
    if not math.isfinite(every) or every < 0.1:
        return stop("--every is how many seconds between stills: 0.1 or more.")
    times = []
    k = 0
    while True:
        t = round(s + k * every, 3)
        if t > e + 1e-6:
            break
        times.append(t)
        k += 1
    cut = len(times) > CLOSE_MOST
    times = times[:CLOSE_MOST]
    first = None
    rows = {x["n"]: x for x in arrange.sheet_rows(kit)}
    if photo is not None:
        if photo not in rows:
            return stop(f"photo {photo} isn't on this shoot's numbered list.")
        p = arrange.photo_path(kit, kit_mod.load_rec(kit), rows[photo])
        if p is None:
            return stop(f"photo {photo} can't be read right now. Is the drive plugged in?")
        first = {"label": f"PHOTO {photo}", "file": str(p), "photo": photo}
    if not vm.avfoundation_here():
        say("NOTE: " + (this_computer.HEVC_HELP if f.get("codec") in vm.HEVC else this_computer.NO_PREVIEW)
            + " Stills can't be taken from a video on a PC yet, so there is no close look here.")
        return EXIT_NO_SHEETS
    cols, cw, ch, per = layout(f.get("w") or 0, f.get("h") or 0)
    look = vm.fresh_folder(looks_dir(kit), "close")
    cells, r = take_stills(vm, v, times, look, v["key"], (cols, cw, ch))
    if cells is None:
        return stop(r.get("words") or "I couldn't take stills from that video.")
    i = next((k for k, x in enumerate(vids, 1) if x["key"] == v["key"]), 1)
    sheets = write_sheets(cells, look, i, v, (cols, cw, ch), per, what="close", first=first)
    (look / "close.json").write_text(json.dumps({"kit": kit.name, "key": v["key"], "name": v["name"], "from": s, "to": e,
                                                 "every": every, "photo": photo,
                                                 "sheets": [{"file": x["file"], "cells": [{"label": c["label"], "at": c.get("at"),
                                                             "photo": c.get("photo"), "place": c["place"]} for c in x["cells"]]}
                                                            for x in sheets]}, indent=1, ensure_ascii=False), encoding="utf-8")
    say(f"{v['name']}, close look {mmss(s)} to {mmss(times[-1])}, a still every {every:g} s"
        + (f", after finished photo {photo} (the first picture)" if photo else "") + ":")
    for x in sheets:
        say(f"  {x['path']}")
    if cut:
        say(f"(That stretch is longer than {CLOSE_MOST} stills; this look stops at {mmss(times[-1])}. Run close again from there for the rest.)")
    return 0


# ---------- moments ----------

class Wrong(Exception):
    pass


def _moment_id(k, name, s, e):
    """Hers: m<k>-<6 hex>, from the video, the start and the end."""
    return "m%d-%s" % (k, hashlib.sha1(("%s|%s|%s" % (arrange._nfc(name), round(s, 2), round(e, 2))).encode("utf-8")).hexdigest()[:6])


def check_moments(d, vids, on_sheet, pick):
    """The moments file, checked whole before anything is written: ([moment], claude_bts or None). Wrong(words)."""
    if not isinstance(d, dict) or set(d) - {"moments", "order"}:
        raise Wrong("the file must be {\"moments\": [...]} (and, if you need it, \"order\"), nothing else.")
    ms = d.get("moments")
    if not isinstance(ms, list) or not ms:
        raise Wrong("there are no moments in the file.")
    if len(ms) > MAX_MOMENTS:
        raise Wrong(f"{len(ms)} moments: the most I pick is {MAX_MOMENTS}. Keep the best {MAX_MOMENTS} and save again.")
    lo, hi = MOMENT_SECONDS
    out, seen = [], set()
    for i, m in enumerate(ms, 1):
        if not isinstance(m, dict) or set(m) - {"video", "start", "end", "label", "photo"}:
            raise Wrong(f"moment {i}: each moment has a video, a start, an end, a label and (only for The reveal) a photo, nothing else.")
        v = video_of(vids, m.get("video"))
        if v is None:
            raise Wrong(f"moment {i}: there's no video \"{m.get('video')}\" in the Footage folder. Use a key the scan printed.")
        f = v["facts"]
        if f.get("refused"):
            raise Wrong(f"moment {i}: {v['name']} can't be used ({f['refused']})")
        length = float(f.get("length") or 0)
        s, e = secs(m.get("start")), secs(m.get("end"))
        if s is None or e is None:
            raise Wrong(f"moment {i}: give its start and end as seconds (42.0) or minutes and seconds (\"0:42\").")
        if s < 0 or e <= s:
            raise Wrong(f"moment {i}: it ends before it starts.")
        if e > length + SLACK:
            raise Wrong(f"moment {i}: it runs past the end of {v['name']}, which is {mmss(length)} long.")
        e = min(e, length)
        span = e - s
        whole = length < lo and s <= SLACK and e >= length - SLACK
        if span < lo - SLACK and not (whole and i > 1):
            if i == 1:
                raise Wrong(f"moment 1 is {span:.1f} seconds: the first moment opens the reel and is never under {lo:g} seconds.")
            raise Wrong(f"moment {i} is {span:.1f} seconds: save each moment {lo:g} to {hi:g} seconds long"
                        + (f" ({v['name']} is only {mmss(length)} long: use all of it)" if length < lo else "") + ".")
        if span > hi + SLACK:
            raise Wrong(f"moment {i} is {span:.1f} seconds: save each moment {lo:g} to {hi:g} seconds long. "
                        "The photographer can make it longer on the page.")
        label = m.get("label", "")
        if label is None:
            label = ""
        if not isinstance(label, str) or "\x00" in label:
            raise Wrong(f"moment {i}: its label must be plain words.")
        label = re.sub(r"\s+", " ", label).strip()[:LABEL_MAX]
        photo = m.get("photo")
        if photo is not None and (type(photo) is not int or photo not in on_sheet):
            raise Wrong(f"moment {i}: photo {photo} isn't on this shoot's numbered list (or leave it null: a match is only for The reveal).")
        tag = (arrange._nfc(v["name"]).casefold(), round(s, 2), round(e, 2))
        if tag in seen:
            raise Wrong(f"moment {i} is the same as an earlier one.")
        seen.add(tag)
        out.append({"id": _moment_id(i, v["name"], s, e), "video": v["name"], "start": round(s, 2), "end": round(e, 2),
                    "label": label, "photo": photo, "keep": True})
    bts = None
    order = d.get("order")
    if order not in (None, ""):
        if not isinstance(order, str):
            raise Wrong("order is the photos as reel.py reads them, like \"41,10,14-,6\".")
        toks = [x.strip() for x in order.split(",") if x.strip()]
        bts, nums = [], []
        for x in toks:
            mm = re.fullmatch(r"(\d+)([+-]?)", x)
            if not mm or int(mm.group(1)) not in on_sheet or int(mm.group(1)) in nums:
                raise Wrong(f"order: \"{x}\" isn't a photo on this shoot's numbered list (or it is there twice).")
            nums.append(int(mm.group(1)))
            bts.append({"n": int(mm.group(1)), "h": mm.group(2)})
        if len(bts) > reel_page.MAX_PICKS:
            raise Wrong(reel_page.OUR_WORDS["too_many"])
        if pick and set(nums) != set(pick):
            raise Wrong("order: those aren't the photos picked for the reel. The photos are the same with footage or "
                        "without (never chosen to match a clip): leave order out, or change the reel's pick first with "
                        "kit.py picks --reel.")
    return out, bts


def carry_sel(saved, old_ms, new_ms, keep_ids):
    """Her step 6: a style's selection that named one of Claude's earlier moments now names the new one of the same
    video, start and end; ids that are gone drop out, and a style left with none goes back to its default (its key
    is taken out). Returns the new sel, or None when nothing changed."""
    sel = saved.get("sel") if isinstance(saved.get("sel"), dict) else None
    if not sel:
        return None

    def tag(m):
        try:
            return (arrange._nfc(str(m.get("video") or "")).casefold(), round(float(m["start"]), 2), round(float(m["end"]), 2))
        except (TypeError, ValueError):
            return None
    new_by = {tag(m): m["id"] for m in new_ms}
    remap = {m["id"]: new_by.get(tag(m)) for m in old_ms if isinstance(m.get("id"), str)}
    out = {}
    for st, ids in sel.items():
        if not isinstance(ids, list):
            continue
        got = []
        for x in ids:
            y = remap.get(x, x) if x in remap else x
            if y and y in keep_ids and y not in got:
                got.append(y)
        if got or not ids:
            out[st] = got
    return None if out == sel else out


def cmd_moments(kit, file):
    try:
        d = json.loads(Path(file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return stop(f"couldn't read the moments file ({e.__class__.__name__}). Nothing was saved.")
    vids = reel_page.list_videos(kit)
    if not vids:
        return stop("there's no footage in this shoot's Footage folder. Nothing was saved.")
    rows = arrange.sheet_rows(kit)
    on_sheet = {x["n"] for x in rows}
    pick, _marks = reel_pick(kit)
    try:
        new, bts = check_moments(d, vids, on_sheet, pick)
    except Wrong as e:
        return stop(str(e) + " Nothing was saved.")
    stills = []
    with arrange.locked(reel_page.lock_path(kit)):
        rec, rows, stamp = reel_page.sync(kit)
        if not rows:
            return stop("couldn't read this shoot's numbered list. Nothing was saved.")
        if {x["n"] for x in rows} != on_sheet:
            return stop("the shoot's numbered list changed while I checked. Run this again. Nothing was saved.")
        theirs = [m for m in reel_page.moments_of(rec) if m.get("by") == "you"]
        raw = rec.get("moments") if isinstance(rec.get("moments"), list) else []
        earlier = [m for m in raw if not any(m is t for t in theirs)]   # every other entry is kept, never lost
        if earlier:
            rec.setdefault("earlier_looks", []).append({"when": time.time(), "moments": earlier})
        rec["moments"] = theirs + new                     # the ones they picked themselves stay, first (hers)
        rec["moments_at"] = time.time()
        if bts is not None:
            rec["claude_bts"] = bts
        saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
        moved = False
        if saved is not None:
            sel = carry_sel(saved, [m for m in earlier if isinstance(m, dict) and "start" in m and "end" in m and "id" in m],
                            new, {m["id"] for m in rec["moments"]})
            if sel is not None:
                saved["sel"] = sel
                saved["updated"] = time.time()
                rec["rev"] = int(rec.get("rev") or 0) + 1  # an open page takes the new selection as it is
                rec.pop("from", None)
                moved = True
        reel_page._stamp_names(rec, rows, stamp)
        reel_page.save(kit, rec)
        for m in new:
            v = reel_page.video_by_name(kit, m["video"], vids)
            if v is not None:
                stills.append((m["id"], v, (m["start"] + m["end"]) / 2))
    made = 0
    if reel_page._video().avfoundation_here():
        for mid, v, at in stills:
            d_ = reel_page.foot_work(kit) / "moments" / mid
            if d_.is_dir() and any(x.lower().endswith(".jpg") for x in os.listdir(d_)):
                continue                                 # the same moment from an earlier look: its still is there
            reel_page._moment_still(kit, mid, v, at)
            made += 1
    say(f"Saved {len(new)} moment{'s' if len(new) != 1 else ''} for the reel page"
        + (f", after their own {len(theirs)}" if theirs else "") + (" and the photos for the reel with footage" if bts is not None else "") + ".")
    for k, m in enumerate(new, 1):
        say(f"  {k}. {m['video']}, {mmss(m['start'])} to {mmss(m['end'])} ({m['end'] - m['start']:.1f} s): {m['label'] or '(no label)'}"
            + (f", matched to photo {m['photo']}" if m["photo"] else ""))
    if bts is not None and not pick:
        say("NOTE: there is no photo pick for the reel without footage yet. Save the same photos with kit.py picks --reel, "
            "so the reel has the same photos with footage or without.")
    if moved:
        say("(A clip they had selected for a style is carried over to its new card; any that is gone was taken out of the selection.)")
    if earlier:
        say(f"(The {len(earlier)} moment{'s' if len(earlier) != 1 else ''} from my earlier look {'are' if len(earlier) != 1 else 'is'} kept in the record, not on the page.)")
    say("The page shows them by itself in a few seconds, under Select your clips.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("words")
    s.add_argument("--every", type=float, help="seconds between stills (her default goes by the video's length)")
    c = sub.add_parser("close")
    c.add_argument("words")
    c.add_argument("video", help="the video's key (from the scan) or its file name")
    c.add_argument("start")
    c.add_argument("end")
    c.add_argument("--every", type=float, default=CLOSE_EVERY)
    c.add_argument("--photo", type=int, help="put this finished photo first, to compare (The reveal only)")
    m = sub.add_parser("moments")
    m.add_argument("words")
    m.add_argument("--file", required=True)
    a = ap.parse_args()
    import fresh
    fresh.announce()
    kit, found = find(a.words)
    if kit is None:
        return stop(f"\"{found.name}\" isn't in Your Content, so the reel page can't show it.")
    if a.cmd == "scan" and a.every is not None and (not math.isfinite(a.every) or a.every < 0.5):
        return stop("--every is how many seconds between stills: 0.5 or more.")
    try:
        if a.cmd == "scan":
            return cmd_scan(kit, a.every)
        if a.cmd == "close":
            return cmd_close(kit, a.video, a.start, a.end, a.every, a.photo)
        return cmd_moments(kit, a.file)
    except arrange.Busy:
        return stop("this shoot's reel page is being written by something else right now. Nothing was changed. Try again in a moment.", 2)


if __name__ == "__main__":
    sys.exit(main())
