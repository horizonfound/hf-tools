#!/usr/bin/env python3
"""The Studio by Horizon Found. From a folder of edited photos to a CapCut project cut
on the beat. Claude does the choosing; this does the counting.

    python3 reel.py sheet --folder "<edited photos>" [--shoot "Black-sand beach"]
        One numbered contact sheet (or a few, 48 photos each) for Claude to look at,
        plus photos.json: number, file, which way up. Nothing in the folder changes;
        the sheet goes in ~/.studio/reels/<shoot>/.

    python3 reel.py strip --folder "<edited photos>" --picks 7,2,11,4,9,1 [--shoot ...]
        The picks drawn in play order, numbered as on the sheet, so the flow from one
        photo to the next can be checked in one look before anything is made.

    python3 reel.py songs [<folder> ...]
        Songs from CapCut's own music used in their CapCut projects (C1, C2...), then
        song files on this computer, newest first (Downloads, Music, Desktop, and any
        folders named), with their length. Says whether the CapCut license note has
        been shown; `reel.py capcut-ok` records that they read it and chose to go ahead.

    python3 reel.py make --folder "<edited photos>" --picks 7,2,11,4,9,1 --song "<file>" | --song none
                                                   | --capcut-song "<song name from CapCut's music>"
        [--clips clips.json]   video clips from their footage, placed in --picks as c1, c2...: c1,7,2,c2,11-,4
        [--shoot "Black-sand beach"] [--night "<backup>" --shoot-id s1] [--name "..."] [--hook "Words on the first photo"]
        [--pace beat|mixed|calm|build] [--variation 2] [--song-start 41.3] [--fit] [--dry-run] [--store <CapCut projects>]
        [--kit "<post kit folder>"]   the reel's working files go in that kit's hidden .kit/reels (REEL_WORK_IN_KIT)
        [--status <file>]   a small JSON of what happened, for the reel page (ok, dry, short_song, project, plan)
        Finds the beat, starts the song where it picks up, lays the photos (and clips) in that
        order, every cut on a beat, and writes the CapCut project (capcut.py).
        --dry-run prints the plan, ending with "Beats per piece: clip 6, 1, 1, 2, ..." and writes nothing.
        clips.json: [{"path": "<video>", "src": 2.5, "seconds": 4.0, "w": 2160, "h": 3840, "length": 420.8}, ...]
        (src: where in the video the clip starts; seconds: its card's length; length: the whole video's).

The vibe (timing.py, Nicole's engine, Nov 6): every cut lands on a whole beat, every photo stays at least one
beat and about half a second, and nothing is left out to fit. "beat" (On every beat, the default) is a new
photo on the beat with a longer hold where the song hits; "mixed" (A little of everything) is some quick,
some long, changing where the music turns over; "calm" is longer looks; "build" starts calm, speeds up toward
the end, then lands. None is a fixed template: one search over the whole reel fits each to its own song,
photos and clips. Claude's marks count in every vibe ("7+" Longer, about twice as long; "11-" Quicker, one
beat). The old names still work: "fast" is beat, "steady" is calm. A clip runs whole beats, never longer
than its card; with a song the clips are muted, with no song they keep their own sound. No song: an even
100 beats a minute, so music can be added in CapCut or Instagram.

Exit codes: 0 done · 2 stop (folder, photo or song missing; the song too short even at one beat a photo).
"""
import argparse
import errno
import json
import subprocess
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "studio-manager" / "scripts"))
import beats_lite  # noqa: E402
import capcut  # noqa: E402
import timing  # noqa: E402  (Nicole's timing: every vibe, photos and clips, one search over the whole reel)
import pictures  # noqa: E402  (small pictures, on a Mac or a PC)
import sound  # noqa: E402  (a song's sound and length, on a Mac or a PC)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()
QUIT = capcut.QUIT

PHOTOS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}
SONGS = {".mp3", ".m4a", ".aac", ".wav", ".aif", ".aiff", ".flac"}
HOME = Path(os.environ.get("STUDIO_HOME") or Path.home() / ".studio")
PER_SHEET = 48
EVEN_BPM = 100.0

# ---------- two defaults Dustin and Nicole may change (v19 plan, section 2), each in this one place ----------
# Decision 1: what belongs to one shoot lives with the shoot. With a --kit, the reel's working files (photos.json,
# the plan in reel.json, the sheets) go in <kit>/.kit/reels instead of ~/.studio/reels/<shoot>. False: as before.
REEL_WORK_IN_KIT = True
# Decision 6: what a reel made for a post kit is called (kit_reel_name). "folder": Dustin's, from Oct 25, the kit's
# folder name and "reel" ("2022-06-24 Black-sand beach reel"; CapCut's list adds " 2" to a second one). "short":
# Nicole's, the shoot's short name ("Black-sand beach reel", then "Black-sand beach reel 2").
REEL_NAME = "folder"


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe, and the work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


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


def kit_reel_name(folder_name, short):
    """The name of a reel made for a post kit (decision 6, REEL_NAME): the kit's folder name and "reel", or the
    shoot's short name and "reel". CapCut's list makes a second one "... reel 2" (capcut.folder_name)."""
    return f"{short if REEL_NAME == 'short' else folder_name} reel"


def kit_workdir(kit):
    """<kit>/.kit/reels, when REEL_WORK_IN_KIT and kit is a post kit folder (it has its hidden .kit); else None."""
    if not REEL_WORK_IN_KIT or not kit:
        return None
    k = Path(kit).expanduser()
    if not (k / ".kit").is_dir():
        return None
    d = k / ".kit" / "reels"
    d.mkdir(exist_ok=True)              # only inside a .kit that is there: never a look-alike kit
    return d


def workdir(shoot, folder, kit=None):
    d = kit_workdir(kit)
    if d is not None:
        return d
    name = slug(shoot or Path(folder).name)
    if this_computer.WINDOWS:
        name = this_computer.unreserved(name)      # a shoot called "Con" or "Aux" is a name Windows keeps for itself
    d = HOME / "reels" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- the contact sheet

def _thumb(src, size, tmp):
    """(w, h, rows) of a small copy: the Mac's own sips, as always; on a PC, Pillow, the right way up and in
    sRGB (sheet.thumb -> pictures.thumb_rows does both). None if the photo can't be read here."""
    import sheet
    return sheet.thumb(src, size, tmp)


def _pictures_note():
    """Plain words for Claude to pass on when this computer can't draw the photos on a sheet, else None."""
    ok, why = pictures.ready()
    return None if ok else "NOTE: the sheet shows numbers but no photos. " + why


def make_sheets(photos, out_dir, cell=200, per_row=6, labels=None, name="sheet"):
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
            n = labels[s + i] if labels else s + i + 1
            x = gap + (i % per_row) * (cell + gap)
            y = gap + (i // per_row) * (cell + gap)
            t = _thumb(p, cell, tmp)
            if t:
                w, h, rows = t
                cv.paste(x + (cell - w) // 2, y + (cell - h) // 2, w, h, rows)
            cv.rect(x, y, tag + 12 * len(str(n)), tag, (20, 20, 20))
            cv.text(x + 6, y + 6, str(n), scale=3, color=(240, 127, 90))
        out = out_dir / (f"{name}-{s // PER_SHEET + 1}.png" if name == "sheet" else f"{name}.png")
        sheet.write_png(out, W, H, cv.rows)
        paths.append(out)
    if tmp.exists():
        tmp.unlink()
    return paths


def cmd_sheet(a):
    photos = edited_photos(a.folder)
    wd = workdir(a.shoot, a.folder, a.kit)
    listing = []
    for i, p in enumerate(photos, 1):
        w, h = capcut.photo_size(p)
        way = "tall" if h > w * 1.05 else "wide" if w > h * 1.05 else "square"
        listing.append({"n": i, "file": str(p), "w": w, "h": h, "way": way})
    (wd / "photos.json").write_text(json.dumps({"folder": str(Path(a.folder)), "photos": listing}, indent=1), encoding="utf-8")
    try:
        sheets = make_sheets(photos, wd)
    except Exception as e:  # a sheet is a convenience; the numbered list still works
        sheets = []
        say(f"(could not draw the sheet: {e})")
    tall = sum(1 for x in listing if x["way"] == "tall")
    say(f"{len(photos)} edited photos ({tall} tall, {len(photos) - tall} wide or square).")
    for s in sheets:
        say(f"Sheet: {s}")
    note = _pictures_note() if sheets else None
    if note:
        say(note)
    say(f"List: {wd / 'photos.json'}")


def kit_numbers(kit, folder):
    """The numbered list of a post kit (<kit>/.kit/sheet.json, written by `kit.py sheet`), each photo named in
    `folder`, or None when there is no kit, no list, or the list is of another folder. With --kit this is what
    the numbers mean, always (v19 review: a list the page had left in .kit/reels went stale after a new export and
    `kit.py sheet`, and a chat reel then put every photo one off)."""
    if not kit:
        return None
    f = Path(kit).expanduser() / ".kit" / "sheet.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        rows = [x for x in d.get("photos", []) if isinstance(x, dict) and type(x.get("n")) is int and isinstance(x.get("file"), str)]
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    same = os.path.normcase
    if not rows or same(str(d.get("folder") or "")) != same(str(Path(folder))):
        return None
    return [dict(x, file=str(Path(folder) / Path(x["file"]).name)) for x in rows]


def read_picks(a, n_clips=0):
    """The listing from the sheet, the picked photo numbers in order, Claude's marks ("7+" lingers on photo 7,
    "11-" passes it quickly), and the play order: ("photo", k) for the k-th pick, ("clip", k) for c1, c2...
    (the k-th clip in --clips; only when there are clips)."""
    same = os.path.normcase      # on a PC, E:\Photos and e:\photos are the same folder; on a Mac this changes nothing
    kit_list = kit_numbers(getattr(a, "kit", None), a.folder)
    listing_file = workdir(a.shoot, a.folder, getattr(a, "kit", None)) / "photos.json"
    if kit_list is not None:
        listing = kit_list       # a kit's one numbered list: the numbers Claude, the page and the kit page all mean
    elif listing_file.is_file() and same(json.loads(listing_file.read_text(encoding="utf-8")).get("folder") or "") == same(str(Path(a.folder))):
        listing = json.loads(listing_file.read_text(encoding="utf-8"))["photos"]
    else:
        listing = [{"n": i, "file": str(p), "w": 0, "h": 0} for i, p in enumerate(edited_photos(a.folder), 1)]
    by_n = {x["n"]: x for x in listing}
    picks, hints, order = [], [], []
    for tok in re.split(r"[,\s]+", a.picks.strip()):
        if not tok:
            continue
        mc = re.fullmatch(r"[cC](\d+)", tok)
        if mc and n_clips:
            k = int(mc.group(1))
            if not 1 <= k <= n_clips:
                say(f"STOP: there is no clip {tok} in --clips (it holds {n_clips}: c1 to c{n_clips}).")
                sys.exit(2)
            order.append(("clip", k - 1))
            continue
        m = re.fullmatch(r"(\d+)([+-]?)", tok)
        if not m:
            say("STOP: --picks is the photo numbers in order, like 7+,2,11-,4 (+ to linger, - to pass quickly)"
                + (", with the clips where they play: c1,7+,2,c2,11-,4" if n_clips else ""))
            sys.exit(2)
        order.append(("photo", len(picks)))
        picks.append(int(m.group(1)))
        hints.append(m.group(2) or None)
    bad = [n for n in picks if n not in by_n]
    if bad or not picks:
        say(f"STOP: no photo numbered {', '.join(map(str, bad))} on the sheet." if bad else "STOP: no photos picked.")
        sys.exit(2)
    if n_clips:
        used = [k for kind, k in order if kind == "clip"]
        twice = sorted({k + 1 for k in used if used.count(k) > 1})
        unused = [k + 1 for k in range(n_clips) if k not in used]
        if twice:
            say(f"STOP: clip c{twice[0]} is in --picks more than once. Each clip plays once.")
            sys.exit(2)
        if unused:                                    # nothing is ever left out quietly
            say(f"STOP: clip c{unused[0]} isn't in --picks. Put each clip where it plays, like c1,7+,2,c2,11-,4.")
            sys.exit(2)
    return by_n, picks, hints, order


def cmd_strip(a):
    """The picks in play order, one or two rows, numbered as on the sheet: read the flow in one look."""
    by_n, picks, _, _ = read_picks(a)
    wd = workdir(a.shoot, a.folder, a.kit)
    per_row = len(picks) if len(picks) <= 8 else (len(picks) + 1) // 2
    out = make_sheets([by_n[n]["file"] for n in picks], wd, cell=260, per_row=per_row, labels=picks, name="strip")
    say(f"Strip: {out[0]}  (left to right, top row then bottom, the order the reel plays)")
    note = _pictures_note()
    if note:
        say(note)


# ---------------------------------------------------------------- songs

CAPCUT_NOTE = ("CapCut's own songs come with CapCut's license: its regular songs are for personal, non-commercial "
               "posts, and its commercial songs are cleared for businesses only on CapCut and TikTok, not Instagram. "
               "Your call.")


def note_seen():
    try:
        import studio_file
        return bool(studio_file.load().get("capcut_music_noted"))
    except Exception:
        return False


def cmd_capcut_ok(a):
    """They have read the CapCut music note and chose to go ahead: don't repeat it every time."""
    import studio_file
    sf = studio_file.load()
    sf["capcut_music_noted"] = True
    studio_file.save(sf)
    say("Noted: they've seen the CapCut music license note.")


def cmd_songs(a):
    store = Path(a.store).expanduser() if a.store else capcut.default_store()
    cc = capcut.capcut_songs(store) if store.is_dir() else []
    if cc:
        say("Songs from CapCut's music, in your CapCut projects (newest first):")
        for i, x in enumerate(cc[:8], 1):
            secs = x["seconds"]
            say(f"  C{i}. {x['name']}  ({int(secs // 60)}:{int(secs % 60):02d})  in \"{x['project']}\""
                + ("" if x["present"] else "  (open that project in CapCut once so it downloads the song again)"))
        say("  License note: " + ("already shown and accepted." if note_seen() else "not shown yet. Say it before using one: " + CAPCUT_NOTE))
    home = Path.home()
    places = [Path(x).expanduser() for x in a.folders] + [this_computer.known_folder("Downloads"), this_computer.known_folder("Music"), this_computer.known_folder("Desktop")]
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
        if cc:
            return
        say("No song files found. Download the song you want (mp3 or m4a) and tell me, pick one in CapCut, "
            "or make the reel with no song.")
        sys.exit(7)
    found.sort(reverse=True)
    if cc:
        say("Song files on this computer:")
    for i, (mt, p) in enumerate(found[:12], 1):
        secs = capcut.song_length(p)
        say(f"{i:2}. {p.name}  ({int(secs // 60)}:{int(secs % 60):02d}, {time.strftime('%b %d', time.localtime(mt))})  {p.parent}")


# ---------------------------------------------------------------- the plan

FPS = 30   # CapCut's projects run at 30 frames a second; cuts are placed on whole frames


def plan_reel(photos, song, feel="beat", song_start=None, fit=False, hints=None, variation=0, beat_file=None,
              song_length=None):
    """photos: the pieces in play order. A photo is {path, w, h} (or {"kind": "photo", ...}, "mark" + or -); a
    video clip is {"kind": "clip", path, src (where in the video it starts), seconds (its card's length), w, h,
    length (the whole video's)}. hints: per piece "+", "-" or None (a photo's own "mark" counts too). feel: a
    vibe (beat, mixed, calm, build) or an old pace name (fast, steady). Returns (plan pieces, facts for Claude
    to tell them), or (None, {"problem": what to say}).

    The timing is Nicole's (timing.py): one search over the whole reel, every cut on a whole beat, every photo
    at least one beat and about half a second, nothing left out to fit. The reel starts on the first beat of a
    bar, and every time is a whole video frame (CapCut moves anything else onto its frame grid, which made cuts
    land late). Each cut is placed on the frame at or just before its beat, never after: a cut that arrives
    with the beat, or a hair early, feels on time; a frame late feels off."""
    vibe = timing.vibe_of(feel)
    if not vibe:
        return None, {"problem": f"STOP: no vibe called \"{feel}\". Pick one of: {', '.join(timing.VIBES)}."}
    hints = list(hints or [])
    items = []
    for k, p in enumerate(photos):
        kind = "clip" if p.get("kind") == "clip" else "photo"
        mark = (hints[k] if k < len(hints) else None) or p.get("mark") or ""
        items.append(dict(p, kind=kind, mark=mark if kind == "photo" else ""))
    if not items:
        return None, {"problem": "STOP: nothing to put in the reel yet."}
    if song:
        grid, why = timing.song_grid(song, beat_file)
        if grid is None:
            return None, {"problem": f"I couldn't find the beat in {Path(song).name}: {why}."}
        if song_length is None:
            song_length = capcut.song_length(song)
    else:
        grid = timing.even_grid(EVEN_BPM)
    got = timing.plan(items, grid, vibe, song_start, variation, song_length or 0.0)
    if not got["ok"]:
        return None, {"problem": got["stop"], "short_song": bool(got.get("short"))}
    holds, i0 = got["holds"], got["j0"]
    beats = grid.T
    idx = [i0]
    for h in holds:
        idx.append(idx[-1] + h)
    from_f = int(beats[i0] * FPS + 1e-6)                  # the song starts on the frame at or before the first beat
    song_from = from_f / FPS
    cut_f = [int((beats[i] - song_from) * FPS + 1e-6) for i in idx]
    cut_f[0] = 0
    out = []
    for x, a, b in zip(items, cut_f, cut_f[1:]):
        piece = {"path": x["path"], "w": x.get("w", 0), "h": x.get("h", 0), "start_f": a, "dur_f": b - a,
                 "start": round(a / FPS, 4), "dur": round((b - a) / FPS, 4), "fill": not fit}
        if x["kind"] == "clip":
            length = float(x["length"])
            src = float(x["src"])
            if piece["dur"] > length + 1e-6:               # the whole video is shorter than one beat of the reel
                which = x.get("label") or "a clip"
                return None, {"problem": f"STOP: {which} ({Path(x['path']).name}) is only {length:.2f} seconds of "
                                         f"video, and nothing in a reel stays on screen for less than one beat "
                                         f"({piece['dur']:.2f} s here). Pick a longer moment for it, or take it out."}
            if src + piece["dur"] > length:                # near the end of the video: start a little earlier
                src = max(0.0, length - piece["dur"] - 0.05)
            piece.update(clip=True, src=round(src, 3), length=length)
        out.append(piece)
    steps = [h // 2 for h in holds]                       # whole beats, every one
    words, shortest, longest = timing.describe(items, steps, grid.period, vibe)
    early = [round((beats[i] - song_from) - f / FPS, 3) for i, f in zip(idx, cut_f)]
    clips = [k + 1 for k, x in enumerate(items) if x["kind"] == "clip"]
    photo_no = 0
    wide, wide_at, wide_clips = [], [], []                # photo numbers; places in the reel; clips (places)
    for at, x in enumerate(items, 1):
        is_wide = x.get("w", 0) > x.get("h", 0) * 1.05
        if x["kind"] == "photo":
            photo_no += 1
            if is_wide:
                wide.append(photo_no)
                wide_at.append(at)
        elif is_wide:
            wide_clips.append(at)
    facts = {"tempo": grid.tempo, "meter": grid.meter, "feel": vibe, "vibe": vibe, "feel_words": words,
             "shortest": shortest, "longest": longest, "beats": steps, "length": round(cut_f[-1] / FPS, 2),
             "song_from": round(song_from, 3) if song else None, "song_from_f": from_f if song else None,
             "cut_early_by": early, "beats_from": grid.beats_from, "wide": wide, "wide_at": wide_at,
             "wide_clips": wide_clips, "clips": clips,
             "photo_count": photo_no,
             "beats_line": timing.beats_line(items, holds), "hits_line": timing.hits_line(grid, i0, holds),
             "kind_note": timing.kind_note(items, vibe, song, song_length) if got["squeezed"] else None}
    return out, facts


def shoot_folder_name(night, shoot_id):
    """The shoot's own folder name on their drive, read from its backup's records (renames and settling followed)."""
    try:
        from where import locate
        root, studio = locate(night)
        for x in json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]:
            if x["id"] == shoot_id and x.get("folder"):
                return Path(x["folder"]).name
    except (SystemExit, OSError, ValueError, KeyError):
        pass
    return None


def reel_name(a, photos):
    """The reel is named after its shoot, so the CapCut project and the video CapCut exports
    ("2022-06-24 Black-sand beach reel.mp4") sit beside the shoot folder of the same name.
    1. the shoot's own folder name, when we know the backup it came from;
    2. otherwise the shoot name in their own folder pattern, dated by the first photo taken;
    3. otherwise the shoot name, or the export folder's name."""
    if a.name:
        return a.name
    if a.night and a.shoot_id:
        folder = shoot_folder_name(a.night, a.shoot_id)
        if folder:
            return f"{folder} reel"
    if a.shoot:
        try:
            import exif_read
            import studio_file
            naming = studio_file.load().get("naming", {})
            taken = sorted(t for t in ((exif_read.read(p["path"]) or {}).get("taken") for p in photos[:12]) if t)
            if naming.get("folder_pattern") and taken:
                return f"{studio_file.render(naming, a.shoot, taken[0])} reel"
        except Exception:
            pass
        return f"{a.shoot} reel"
    return f"{Path(a.folder).name} reel"


def read_clips(path):
    """The clips for --clips: a JSON file holding a list (or {"clips": [...]}), each {"path": the video,
    "src": seconds into the video where the clip starts, "seconds": the clip's length on its card, "w", "h":
    the video's size, "length": the whole video's length in seconds}. Plain words for anything wrong."""
    f = Path(path).expanduser()
    try:
        data = json.loads(f.read_text(encoding="utf-8-sig"))     # (a file PowerShell wrote may start with a BOM)
    except (OSError, ValueError) as e:
        say(f"STOP: I couldn't read the clips in {f.name} ({e}).")
        sys.exit(2)
    if isinstance(data, dict):
        data = data.get("clips")
    if not isinstance(data, list) or not data:
        say(f"STOP: {f.name} has no clips in it (a list of clips, each with path, src, seconds, w, h and length).")
        sys.exit(2)
    out = []
    for k, c in enumerate(data, 1):
        def num(key, *alt):
            for name in (key,) + alt:
                v = c.get(name) if isinstance(c, dict) else None
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v:
                    return float(v)
            return None
        src, secs, length = num("src", "start"), num("seconds"), num("length")
        p = c.get("path") if isinstance(c, dict) else None
        if not isinstance(p, str) or not p.strip() or src is None or secs is None or length is None:
            say(f"STOP: clip c{k} needs its video (path), where it starts (src), how long it is (seconds) and "
                f"how long the whole video is (length).")
            sys.exit(2)
        if src < 0 or secs <= 0 or length <= 0 or src + secs > length + 0.05:
            say(f"STOP: clip c{k} starts at {src:g} s and runs {secs:g} s, but its video is {length:g} s long, "
                f"so it would run past the end of its video.")
            sys.exit(2)
        w, h = num("w", "width"), num("h", "height")
        if not w or not h or w <= 0 or h <= 0:
            say(f"STOP: clip c{k} needs its video's size (w and h, in pixels), so it can fill the tall screen.")
            sys.exit(2)
        out.append({"kind": "clip", "path": str(Path(p).expanduser()), "src": src, "seconds": secs,
                    "w": int(w), "h": int(h), "length": length, "label": f"c{k}"})
    return out


def write_status(a, **what):
    """--status: a small JSON of what happened, for the reel page, so it never reads the words to tell (her page
    told a short song by matching "only N seconds", which missed "15.4 seconds"). Written whole, or not at all."""
    if not getattr(a, "status", None):
        return
    f = Path(a.status).expanduser()
    tmp = f.with_name(f".{f.name}.{os.getpid()}.tmp")
    try:
        old = json.loads(f.read_text(encoding="utf-8"))
        mine = {"for": old["for"]} if isinstance(old, dict) and isinstance(old.get("for"), str) else {}
    except (OSError, ValueError):
        mine = {}                    # the reel page's job writes {"for": <its id>} first; that is kept, so the page
    try:                             # can tell which job this says made what
        tmp.write_text(json.dumps(dict({"ok": False, "dry": bool(a.dry_run), "short_song": False, "project": None,
                                        "plan": None}, **mine, **what), indent=1), encoding="utf-8")
        this_computer.replace(tmp, f)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def cmd_make(a):
    clips = read_clips(a.clips) if a.clips else []
    by_n, picks, hints, order = read_picks(a, len(clips))
    photos = []
    for n in picks:
        x = by_n[n]
        w, h = (x["w"], x["h"]) if x.get("w") else capcut.photo_size(x["file"])
        photos.append({"path": x["file"], "w": w, "h": h})
    if clips:                                          # the clips where they play, among the photos
        pieces_in = [dict(photos[k], kind="photo", mark=hints[k] or "") if kind == "photo" else dict(clips[k])
                     for kind, k in order]
        piece_hints = [hints[k] if kind == "photo" else None for kind, k in order]
    else:
        pieces_in, piece_hints = photos, hints
    picked = None
    if a.capcut_song:
        store = Path(a.store).expanduser() if a.store else capcut.default_store()
        want = a.capcut_song.strip().lower()
        cc = capcut.capcut_songs(store)
        picked = (next((x for x in cc if x["name"].lower() == want or x["material"].get("music_id") == want), None)
                  or next((x for x in cc if want in x["name"].lower()), None))
        if not picked:
            say(f"STOP: no song called \"{a.capcut_song}\" in your CapCut projects. "
                f"Add it to a project in CapCut, {QUIT} CapCut, and try again.")
            sys.exit(2)
        if not picked["present"]:
            say(f"STOP: CapCut doesn't have \"{picked['name']}\" downloaded right now. Open \"{picked['project']}\" "
                f"in CapCut once so it downloads the song again, {QUIT} CapCut, and try again.")
            sys.exit(2)
        song = picked["path"]
    else:
        song = None if (a.song or "none").lower() in ("none", "no", "") else str(Path(a.song).expanduser())
    if song and not Path(song).is_file():
        say(f"STOP: no song at {song}")
        sys.exit(2)
    beat_file = None
    if picked and picked.get("beats"):
        bp = (picked["beats"].get("ai_beats") or {}).get("beats_path")
        beat_file = bp if bp and Path(bp).is_file() else None
    pieces, facts = plan_reel(pieces_in, song, a.pace, a.song_start, a.fit, piece_hints, a.variation, beat_file,
                              song_length=(picked["seconds"] if picked else None))
    if pieces is None:
        write_status(a, short_song=bool(facts.get("short_song")))
        say(facts["problem"])
        sys.exit(2)
    name = reel_name(a, photos)
    plan = {"name": name, "photos": pieces,
            "song": ({"path": song, "from": facts["song_from"], "from_f": facts["song_from_f"], "fade_out": 0.5,
                      "length": (picked["seconds"] if picked else capcut.song_length(song)),
                      "name": picked["name"] if picked else Path(song).name,
                      "capcut_material": picked["material"] if picked else None,
                      "capcut_beats": picked["beats"] if picked else None} if song else None),
            "hook": {"text": a.hook, "dur": pieces[0]["dur"], "dur_f": pieces[0]["dur_f"]} if a.hook else None}
    wd = workdir(a.shoot, a.folder, a.kit)
    (wd / "reel.json").write_text(json.dumps({"plan": plan, "facts": facts}, indent=1), encoding="utf-8")
    plan_facts = {"clips": len(facts["clips"]), "photos": facts["photo_count"], "length": facts["length"],
                  "tempo": facts["tempo"], "song": bool(song), "song_from": facts["song_from"]}
    when = ""
    if song:
        f = facts["song_from"]
        if f < 1:
            when = ", starting the song at the top"
        elif f < 60:
            when = f", starting the song {f:.0f} seconds in"
        else:
            when = f", starting the song at {int(f // 60)}:{int(f % 60):02d}"
    span = (f"{facts['shortest']:.1f} to {facts['longest']:.1f} seconds a photo"
            if facts["shortest"] != facts["longest"] else f"{facts['shortest']:.1f} seconds a photo")
    n_cl, n_ph = len(facts["clips"]), facts["photo_count"]
    what = (f"{n_cl} clip{'s' if n_cl != 1 else ''} and " if n_cl else "") + f"{n_ph} photo{'s' if n_ph != 1 else ''}"
    if song:
        say(f"Plan: {what}, {facts['length']:.1f} seconds, {facts['feel_words']} ({span}), every cut "
            f"on the beat at about {facts['tempo']:.0f} beats a minute{when}.")
    elif n_cl:
        say(f"Plan: {what}, {facts['length']:.1f} seconds, {facts['feel_words']} ({span}), no song: the cuts "
            f"follow an even {EVEN_BPM:.0f} beats a minute and the footage keeps its own sound.")
    else:
        say(f"Plan: {what}, {facts['length']:.1f} seconds, {facts['feel_words']} ({span}), "
            f"no song (add one in CapCut or Instagram).")
    if facts["kind_note"]:
        say(facts["kind_note"])
    for k, p in enumerate(pieces, 1):
        if p.get("clip"):
            say(f"  {k}. clip from {Path(p['path']).name} at {p['src']:.1f} s, {p['dur']:.1f} s long")
    if facts["wide"] and not a.fit:
        if n_cl:                                     # count by place in the reel, as the clip lines above do
            say(f"Wide photos zoomed to fill the screen, by their place in the reel: "
                f"{', '.join(map(str, facts['wide_at']))} (slide them in CapCut if a face is cut off).")
        else:
            say(f"Wide photos zoomed to fill the screen: {', '.join(map(str, facts['wide']))} (slide them in CapCut if a face is cut off).")
    for k in ([] if a.fit else facts["wide_clips"]):
        say(f"The clip at {k} in the reel ({Path(pieces[k - 1]['path']).name}) is wide, so it's zoomed to fill the tall screen and loses its sides "
            f"(slide it in CapCut if anything important is cut off).")
    if a.dry_run:
        if facts["hits_line"]:
            say(facts["hits_line"])
        say(facts["beats_line"])
        say(f"Dry run: nothing written. The plan is in {wd / 'reel.json'}")
        write_status(a, ok=True, plan=plan_facts)
        return
    store = Path(a.store).expanduser() if a.store else capcut.default_store()
    dest, draft = capcut.write(plan, store, a.ignore_open)
    if capcut.write.left_to_capcut:                  # a Mac with CapCut open: CapCut adds it by itself (seen)
        say(f"Made \"{dest.name}\" in CapCut. CapCut is open, so it will show up in your projects by itself in a "
            f"moment; if it isn't there, {QUIT} and reopen CapCut.")
    elif capcut.write.listed:
        say(f"Made \"{dest.name}\" in CapCut. Open CapCut and it's at the top of your projects.")
    else:                                            # not in CapCut's list yet: the note says why and what to do
        say(f"Made \"{dest.name}\" in CapCut.")
    if capcut.write.note:
        say(capcut.write.note)
    if capcut.write.waiting:
        say(capcut.WAITING_HINT)
    write_status(a, ok=True, project=dest.name, plan=plan_facts, listed=bool(capcut.write.listed),
                 left_to_capcut=bool(capcut.write.left_to_capcut), waiting=bool(capcut.write.waiting))
    rec = json.loads((wd / "reel.json").read_text(encoding="utf-8"))
    rec["capcut_project"] = str(dest)
    (wd / "reel.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # the posting queue: this shoot's reel is now in progress (yellow). Best effort; the reel is made either way.
    try:
        pq = HERE.parent.parent / "studio-manager" / "scripts" / "posting_queue.py"
        if pq.exists() and a.shoot:
            r = subprocess.run([sys.executable, str(pq), "made", f"{a.shoot} reel", "--where", dest.name],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=20)
            if r.returncode == 0:
                say("It's in your posting queue as in progress; say \"the reel is ready\" when it's exported.")
    except Exception:
        pass


def cmd_sound(a):
    """The sound of a video or screen recording, as a song file in this reel's own working folder
    (~/.studio/reels/<shoot>/). The recording itself is never moved, renamed or changed. Never write the
    song into Music, Downloads, Desktop or Documents: the Mac guards those (Nicole's first reel, Nov 5).
    How (sound.extract_audio): the Mac's own afconvert as always; else ffmpeg (the sound copied as it is);
    on a PC with neither, Windows' own media parts write it as a .wav (unproven on a real PC)."""
    src = Path(a.video).expanduser()
    if not src.is_file():
        say(f"STOP: no file at {src}")
        sys.exit(2)
    d = workdir(a.shoot, a.shoot)
    out = d / f"{src.stem} sound.m4a"
    n = 2
    while out.exists():
        out = d / f"{src.stem} sound {n}.m4a"
        n += 1
    out, how = sound.extract_audio(src, out)       # nothing of theirs is written over; a failed try leaves nothing
    if not out:
        say("STOP: " + how)
        sys.exit(2)
    secs = capcut.song_length(str(out)) or 0
    say(f"Sound: {out}")
    say(f"{secs:.0f} seconds, pulled from \"{src.name}\". The recording is where it was, unchanged.")
    say("Use it with: reel.py make --song \"" + str(out) + "\" ...   (the script puts its own copy inside the CapCut project)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--folder", required=True)
    s.add_argument("--shoot")
    t = sub.add_parser("strip")
    t.add_argument("--folder", required=True)
    t.add_argument("--picks", required=True)
    t.add_argument("--shoot")
    g = sub.add_parser("songs")
    g.add_argument("folders", nargs="*")
    g.add_argument("--store")
    sub.add_parser("capcut-ok", help="they read the CapCut music note and chose to go ahead")
    sd = sub.add_parser("sound", help="pull the sound out of a video or screen recording, to use as the song")
    sd.add_argument("--from", dest="video", required=True)
    sd.add_argument("--shoot", required=True)
    m = sub.add_parser("make")
    m.add_argument("--folder", required=True)
    m.add_argument("--picks", required=True)
    m.add_argument("--song", help="a song file, or none")
    m.add_argument("--capcut-song", help="the name of a song from CapCut's music, used in one of their CapCut projects")
    m.add_argument("--shoot")
    m.add_argument("--night", help="the backup the shoot came from, so the reel is named exactly like its folder")
    m.add_argument("--shoot-id", help="the shoot's id in that backup (s1, s2...)")
    m.add_argument("--name")
    m.add_argument("--hook")
    m.add_argument("--clips", help="a JSON file of video clips (path, src, seconds, w, h, length), placed in --picks as c1, c2...")
    m.add_argument("--pace", "--vibe", dest="pace", choices=list(timing.VIBES) + list(timing.OLD_NAMES), default=timing.DEFAULT_PACE,
                   help="beat (On every beat), mixed (A little of everything), calm, build; "
                        "the old names still work: fast is beat, steady is calm")
    m.add_argument("--variation", type=int, default=0, help="another mix of the same picks and vibe (the page counts the reels already made)")
    m.add_argument("--song-start", type=float)
    m.add_argument("--fit", action="store_true", help="show whole wide photos with bars instead of filling the screen")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--store")
    m.add_argument("--ignore-open", action="store_true")
    m.add_argument("--kit", help="the post kit this reel is for: its working files go in the kit's hidden .kit/reels")
    m.add_argument("--status", help="write what happened here as a small JSON, for the reel page")
    s.add_argument("--kit", help="the post kit these photos are for: the sheet and photos.json go in its .kit/reels")
    t.add_argument("--kit")
    a = ap.parse_args()
    {"sheet": cmd_sheet, "strip": cmd_strip, "songs": cmd_songs, "make": cmd_make,
     "capcut-ok": cmd_capcut_ok, "sound": cmd_sound}[a.cmd](a)


if __name__ == "__main__":
    main()
