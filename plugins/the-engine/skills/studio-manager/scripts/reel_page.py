#!/usr/bin/env python3
"""The reel page: Nicole's reel maker (handoff v19, pages/reel-maker.html), as the Assistant's own page.

    python3 reel_page.py open "beach"      get the page ready (the numbered list, the small copies) and print its address
    python3 reel_page.py show "beach"      what the page has saved: whose order, the order, the record's counter

The photographer sees her page: her words (WORDS below, word for word from her reel-maker.html and server.py),
her steps in her order, her buttons and what they do. Underneath it is built the Assistant's way:

  * The page names a kit only by its folder name and a photo only by its number on the kit's numbered list
    (.kit/sheet.json, reel.py's own numbering). No route takes a path or a file name, and no answer has one.
  * Nothing is loaded from the internet: the fonts are the plugin's own (shared/fonts, through /reel-font), the
    drag is our own pointer drag (arrange_page.DRAG_JS; no SortableJS, no browser drag-and-drop).
  * Nothing is kept in the browser: every choice is saved to the kit by POST /reel-save, retried until it lands.
  * kit.json is only ever read here (Claude's order is picks.reel there, with reel_marks); commands write it.
  * Nothing is deleted or written over: the record is written whole, with the version before kept beside it.

Routes, all on the posting server (posting_queue.py hands them here):
  GET  /reel.html?kit=<folder>   the page
  GET  /reel-state?kit=<folder>  everything the page draws from: the photos (numbers and sizes only), Claude's
                                 order, what was saved, the record's counter
  POST /reel-save                {kit, stamp, base, page, saved: {...}}: the page's choices, checked field by field
  GET  /reel-font?f=<name>       one of the plugin's own font files (FACES)
  POST /reel-open, /reel-make, /reel-capcut and GET /reel-job: kept for the later stages (the song's folder,
                                 Make my reel and its job, Open CapCut); for now they answer "not yet", in plain words
Small copies of the photos are arrange.py's (/kit-photo, .kit/previews), the same the pickers use.

Records:
  <kit>/.kit/reel-page.json       {"v": 1, "rev": the counter (only this file moves it on, by one for every accepted
                                  save), "from": {page, base} of the last save, "stamp": the numbered list it was saved
                                  against, "names": {number: file name} for every number it mentions (so a re-made
                                  list finds the same photos again), "saved": {picks, mine, mine_picks, song, vibe,
                                  footage, style, sel, ask, feel, updated}, and, from the later stages, "moments",
                                  "claude_bts" and "made"}. Her record (BUILD.md section 8), minus her "claude", which
                                  is read from kit.json picks.reel every time.
  <kit>/.kit/reel-page.prev.json  the version before, kept whole
  <kit>/.kit/reel-page.lock       held by every writer (this_computer.try_lock, through arrange.locked), never removed

The defaults Dustin and Nicole may change sit in one place each (PLAN section 2): MAX_PICKS and its line (23),
DRAG_OUT (22), REV_CHECK (21), the WORDS table (9, and every word on the page), STYLE (16).

The page is built so the steps still to come slot in where hers has them: SECTIONS keeps her order (1 footage,
2 the order, 3 the song, 4 the style, 5 the vibe), and an empty slot is simply left out; her renumbering counts
only the steps that show. The page's script is a small core (CORE_JS: the record, saving, following) with one
part per step (ORDER_JS is step 2); each later step adds its own part and its own fields to SAVE_FIELDS.

Python 3.9, standard library only. Nothing here is Mac-only: the small copies are arrange.py's (sips on a Mac,
pictures.py's Pillow on a PC), the lock is this_computer.try_lock, and the page's words name no Mac thing.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import brand  # noqa: E402

this_computer.utf8_output()

# ---------- the defaults, each in one place (PLAN section 2) ----------
MAX_PICKS = 40          # decision 23: her server keeps 40 (and quietly drops the rest); ours says so
DRAG_OUT = False        # decision 22: hers. Only the x or a tap below takes a photo out, never a drag down
REV_CHECK = True        # decision 21: two windows on one reel page: a save from a page that hadn't seen the newest is refused
UNDO_STEPS = 60         # hers
SAVE_AFTER_MS = 500     # hers: a change is saved half a second after the last one
FOLLOW_MS = 4000        # how often an open page asks for a fresh pick from Claude (hers looks every 4 s)

RECORD = "reel-page.json"
PREV = "reel-page.prev.json"
LOCK = "reel-page.lock"
POST_CAP = 65536
VIBES = ("beat", "mixed", "calm", "build")           # hers
STYLES = ("first", "reveal", "backforth", "bookends")  # hers
MOMENT_ID = re.compile(r"[mu][0-9]{1,4}-[0-9a-f]{6}")  # hers: m<k>-<6 hex> (Claude's), u<k>-<6 hex> (theirs)
PAGE_ID = arrange.PAGE_ID
FONT_DIR = HERE.parent.parent.parent / "shared" / "fonts"
# (family, weight, style, the file in shared/fonts without its .ttf): her page asks Google for DM Sans 400, 500
# and 600 and for Fraunces; these are the plugin's own, so the page works with no internet (decision 16).
FACES = [
    ("DM Sans", 400, "normal", "DMSans-Regular"),
    ("DM Sans", 500, "normal", "DMSans-Medium"),
    ("DM Sans", 600, "normal", "DMSans-SemiBold"),
    ("Fraunces", 400, "normal", "Fraunces-Regular"),
    ("Fraunces", 400, "italic", "Fraunces-Italic"),
]
FACE_FILES = tuple(f[3] for f in FACES)       # the only names /reel-font answers to

GET_PATHS = ("/reel.html", "/reel-state", "/reel-font", "/reel-job")
POST_PATHS = ("/reel-save", "/reel-open", "/reel-make", "/reel-capcut")

# ---------- the words: hers, word for word (reel-maker.html and server.py, handoff v19) ----------
# Each is shown exactly as written here. "_html" words carry her own <b>; {short}, {n}, {k}, {max} are filled in.
# The words for the steps still to come are here already, so every word on the page lives in this one table.
# The few lines that are ours, not hers, are in OUR_WORDS below, each with its reason.
WORDS = {
    # the top of the page
    "page_title": "Make my reel",
    "reel_of": "{short} reel",
    "back_kit": "Back to the post kit",
    "eyebrow": "Reel",
    "h1": "Your reel",
    "lede_html": "A few quick steps, then press <b>Make my reel</b> and it's cut on the beat in CapCut, ready for your look.",
    "reach": "I can't reach this shoot right now. Check that the photo drive is plugged in, then reload.",

    # step 1 (stage b): behind-the-scenes footage
    "foot_h2": "Behind-the-scenes footage?",
    "foot_say": "Do you want this reel to include behind-the-scenes video from the shoot, or just your photos?",
    "foot_bts_b": "Add behind-the-scenes footage",
    "foot_bts_s": "Clips from the shoot, mixed with your finished photos.",
    "foot_photos_b": "Just photos",
    "foot_photos_s": "Your finished photos, cut on the beat.",

    # step 2: put your photos in order
    "order_h2": "Put your photos in order",
    "order_say": "Your assistant can choose the order for you, or you can drag and drop them into the order you'd like. Whichever you pick, the other one is kept, so you can switch back and forth to compare.",
    "claude_b": "Let my assistant choose",
    "claude_rec": "Recommended for behind-the-scenes reels",
    "claude_words": "Your assistant picks the strongest photos and orders them so each one flows into the next.",
    "claude_words_bts": "Your assistant picks your strongest photos, the ones with the most feeling and the best story, and fits your behind-the-scenes moments in between.",
    "not_picked_html": "Your assistant hasn't picked for this shoot yet. In the chat, say <b>“pick my reel photos for {short}”</b> and they'll show up here.",
    "mine_b": "I'll drag them in myself",
    "mine_words": "Drag any photo to move it, or drag one up from all your photos below. Tap × to take one out.",
    "tip_html": "If there's a photo you really want on screen a little longer, tap <b>Longer</b> under it. If there are ones you'd like to flash by quicker, tap <b>Quicker</b>. Leave the rest alone.",
    "legend_long": "Longer stays on screen about twice as long",
    "legend_quick": "Quicker gets the shortest time, one beat",
    "undo": "↶ Undo",
    "undone": "Undone.",
    "empty": "Your reel is empty. Tap photos below to add them.",       # her CSS shows it in an empty row
    "take_out": "Take it out",
    "take_out_label": "Take photo {n} out",
    "photo_alt": "Photo {n}",
    "longer": "Longer",
    "quicker": "Quicker",
    "one_photo": "{n} photo",
    "photos": "{n} photos",
    "n_longer": " · {k} longer",
    "n_quicker": " · {k} quicker",
    "few": " · 6 or more works best",
    "lots": " · that's a lot for one reel",
    "all_summary": "All your photos (drag one up into your order, or tap to add it and tap again to take it out)",
    "zoom": "See it bigger",

    # step 3 (stage a3): the song
    "song_h2": "Add your song",
    "song_say1": "The music you choose shapes how your reel feels, so pick a song that helps tell your story.",
    "song_say2_html": "Press <b>Add my music</b> and a Music folder for this shoot opens. Drag your song into it. A screen recording of the song playing works fine: I'll take the sound from it and keep it right beside the recording.",
    "add_music": "♫ Add my music",
    "licence_html": "Posting from a business account? Music you didn't license can get your reel muted. The always-safe way: pick <b>No song</b>, make the reel, and add a song from Instagram's own music when you post.",
    "song_recording": "Screen recording · I'll use its sound",
    "song_song": "Song",
    "song_in_music": "in your Music folder",
    "song_in_photos": "in your Photos folder",
    "no_song_b": "No song",
    "no_song_s": "I'll add music in Instagram when I post",
    "got_it": "Got it: {name}.",
    "opening_music": "Opening your Music folder in Finder...",
    "music_open": "Your Music folder is open in Finder. Drag your song in, and it will show up here by itself.",
    "cant_open": "Could not open the folder. Ask your assistant to open it.",

    # step 4 (stage b2): the style
    "style_h2": "What style of behind the scenes is this?",
    "style_say": "Pick a style. It uses the clips you selected in step 1. Style and vibe come last so you can try a few versions: change them and press Make my reel again. Every cut still lands on the beat. With a song, the footage plays muted so your song carries the reel; with No song, it keeps its own sound.",
    "style_first_b": "Moment first",
    "style_first_s": "A few seconds of footage opens the reel, then your photos.",
    "style_reveal_b": "The reveal",
    "style_reveal_s": "The moment the photo was taken, then the finished photo. A few times through.",
    "style_backforth_b": "Back and forth",
    "style_backforth_s": "A clip, then a couple of photos, then the next clip, so it feels like being there.",
    "style_bookends_b": "Bookends",
    "style_bookends_s": "Footage opens and closes the reel, with your photos in the middle. Works with any footage.",

    # step 5 (stage a4): the vibe
    "vibe_h2": "Pick the vibe",
    "vibe_say": "How should it move? Every cut lands on the beat, whichever you pick. None of these is a fixed template: the timing is worked out for your song, your photos and your clips, so every reel comes out its own way.",
    "vibe_beat_b": "On every beat",
    "vibe_rec": "Recommended",
    "vibe_beat_s": "Quick and punchy, a new photo on the beat, with a longer hold where the song hits.",
    "vibe_mixed_b": "A little of everything",
    "vibe_mixed_s": "Some quick, some long, changing where the music turns over.",
    "vibe_calm_b": "Calm",
    "vibe_calm_s": "Longer looks, room to breathe. Best with fewer photos or a longer song.",
    "vibe_build_b": "Build",
    "vibe_build_s": "Starts calm, speeds up toward the end, then lands on the last photo.",

    # the bar at the bottom and the result (stage a4)
    "make": "Make my reel",
    "make_test": "Make my reel (test: nothing is made)",
    "making": "Making your reel...",
    "finding_beat": "Finding the beat and cutting your photos to it. This takes a few seconds.",
    "sum_no_song_yet": "no song picked yet",
    "sum_no_song": "no song",
    "vibe_word_beat": "on every beat",
    "vibe_word_mixed": "a little of everything",
    "vibe_word_calm": "calm",
    "vibe_word_build": "build",
    "need_song_h3": "One more thing: your song",
    "need_song_html": "Add your song under <b>Add your song</b>, or pick <b>No song</b> if you'll add music in Instagram.",
    "short_h3": "Your song is a little short for this",
    "short_more_html": "Add a longer version of the song under <b>Add your song</b>, or take a few photos out.",
    "didnt_work_h3": "That didn't work yet",
    "went_wrong": "Something went wrong.",
    "test_h3": "Test run: nothing was made",
    "in_capcut_h3": "It's in CapCut: {project}",
    "new_reel": "your new reel",
    "open_capcut_say": "Open CapCut, click it at the top of your projects, add your look, and export.",
    "open_capcut": "Open CapCut",
    "no_server": "I couldn't reach the page server. Ask your assistant to make the reel instead.",
    "capcut_opening": "CapCut is opening. Your newest reel is at the top of your projects.",
}

# Lines that are ours, not hers, each with why (they go on the "Tell Nicole" list):
OUR_WORDS = {
    # decision 23: her server keeps the first 40 without a word
    "too_many": f"A reel holds up to {MAX_PICKS} photos. Take one out first.",
    # decision 21: only when a second window saved first
    "newer": arrange.NEWER,
    # her page has no Back to home: a kit with no kit page yet gets ours, from every other page
    "back_home": "Back to home",
    # her saves are sent once and forgotten; ours are tried again until they land, and say so only when one didn't
    "retry": "Not saved yet. Trying again...",
    "cant_reach": arrange.CANT_REACH,
    # our numbered list can be re-made under an open page (hers has no such list)
    "photos_changed": arrange.PHOTOS_CHANGED,
    "reload": "Reload",
    # our small copies are made in the background the first time, where hers were made before the page showed
    "getting_ready": "Getting this photo ready...",
    "cant_read": "Can't read this photo right now",
}

CANT_FIND = WORDS["reach"]
NOT_READY = arrange.NOT_READY
NOT_YET = "This part isn't ready yet."            # the later stages' routes, until they are built
NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD

_LOCK = threading.RLock()


def say(msg):
    arrange.say(msg)


def short_name(name):
    """Hers (server.py short_name): the folder name without a leading date."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", name) or name


# ---------- the record ----------

def record_path(kit):
    return kit / ".kit" / RECORD


def prev_path(kit):
    return kit / ".kit" / PREV


def lock_path(kit):
    return kit / ".kit" / LOCK


def load(kit):
    try:
        d = json.loads(record_path(kit).read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except (OSError, ValueError):
        pass
    return {"v": 1}


def _write_bytes_whole(path, data):
    """Bytes written whole or not at all (a scratch name, then a rename), as arrange.write_whole does."""
    arrange.make_folder(path.parent)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(data)
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def save(kit, rec):
    """Write the record whole, keeping the version before it whole beside it. The caller holds the lock."""
    rec["v"] = 1
    p = record_path(kit)
    try:
        before = p.read_bytes()
    except OSError:
        before = None
    if before is not None:
        _write_bytes_whole(prev_path(kit), before)
    arrange.write_whole(p, rec)


def claude_order(kit, rec_kit=None, on_sheet=None):
    """Claude's photo-only order: kit.json picks.reel with its marks, as her record's "claude": [{n, h}].
    Only numbers on the numbered list."""
    rec_kit = rec_kit if rec_kit is not None else kit_mod.load_rec(kit)
    nums, marks = arrange.kit_pick(rec_kit, "reel")
    out = []
    for n, m in zip(nums, marks):
        if on_sheet is None or n in on_sheet:
            out.append({"n": n, "h": m})
    return out


def _numbers_in(saved):
    out = set()
    for key in ("picks", "mine_picks"):
        for x in (saved or {}).get(key) or []:
            if isinstance(x, dict) and type(x.get("n")) is int:
                out.add(x["n"])
    return out


def _refind(lst, old_names, n_of):
    """A list of {n, h} on a re-made numbered list: every photo found again by its file name. Gone ones drop out."""
    if not isinstance(lst, list):
        return lst
    out, seen = [], set()
    for x in lst:
        if not isinstance(x, dict):
            continue
        nm = old_names.get(str(x.get("n")))
        n = n_of.get(nm) if nm else None
        if n is None or n in seen:
            continue
        seen.add(n)
        out.append({"n": n, "h": x.get("h") if x.get("h") in ("+", "-") else ""})
    return out


def sync(kit):
    """The record, brought in line with the numbered list. Returns (record, rows, stamp); rows is [] when the
    list can't be read right now, and then NOTHING is changed. The caller holds the lock."""
    rec = load(kit)
    rows = arrange.sheet_rows(kit)
    stamp = arrange.sheet_stamp(kit)
    if not rows or not stamp:
        return rec, [], ""
    if rec.get("stamp") and rec.get("stamp") != stamp and isinstance(rec.get("saved"), dict):
        # the list was re-made: find each photo again by its file name
        n_of = {}
        for x in rows:
            n_of.setdefault(arrange.photo_name(x), x["n"])
        old = rec.get("names") or {}
        s = rec["saved"]
        for key in ("picks", "mine_picks"):
            if isinstance(s.get(key), list):
                s[key] = _refind(s[key], old, n_of)
        rec["names"] = _names(s, {x["n"]: arrange.photo_name(x) for x in rows})
        rec["stamp"] = stamp
        rec["rev"] = int(rec.get("rev") or 0) + 1
        rec.pop("from", None)
        save(kit, rec)
    return rec, rows, stamp


def _names(saved, name_of):
    return {str(n): name_of[n] for n in sorted(_numbers_in(saved)) if n in name_of}


def state(kit):
    """Everything the page draws from. No path and no file name is in it. None when the numbered list can't be
    read right now."""
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
    if not rows:
        return None
    rec_kit = kit_mod.load_rec(kit)
    photos, made = arrange.page_photos(kit, rec_kit, rows)
    on_sheet = {x["n"] for x in rows}
    saved = rec.get("saved") if isinstance(rec.get("saved"), dict) else None
    return {
        "ok": True,
        "short": short_name(kit.name),
        "kit_page": kit_mod.rec_path(kit).with_name("Post kit.html").is_file(),
        "stamp": stamp, "rev": int(rec.get("rev") or 0), "total": len(rows),
        "photos": photos, "previews": {"made": made, "of": len(rows)},
        "claude": claude_order(kit, rec_kit, on_sheet),
        "saved": _for_page(saved, on_sheet),
        "max": MAX_PICKS,
    }


def _for_page(saved, on_sheet):
    """What was saved, as the page reads it back: her fields only, photos only if they are on the list."""
    if not saved:
        return None
    out = {k: saved.get(k) for k in SAVE_FIELDS if k in saved}
    for key in ("picks", "mine_picks"):
        if isinstance(out.get(key), list):
            out[key] = [x for x in out[key] if x.get("n") in on_sheet]
    return out


def current_picks(kit):
    """The order Make my reel uses when it is not handed one by the page, as reel.py reads it ("19,4,10+,14-"):
    their own when they chose "I'll drag them in myself", otherwise Claude's newest, with the Longer / Quicker
    they set on the same photos (her followClaude). "" when there is nothing yet."""
    st = state(kit)
    if st is None:
        return ""
    saved = st["saved"] or {}
    claude = st["claude"]
    if saved.get("mine") or (not claude and saved.get("picks")):
        lst = saved.get("picks") or []
    elif isinstance(saved.get("picks"), list) and [x["n"] for x in saved["picks"]] == [x["n"] for x in claude]:
        lst = saved["picks"]
    else:
        lst = claude
    return ",".join(f"{x['n']}{x.get('h') or ''}" for x in lst)


# ---------- checking what a page sends ----------

class Refused(Exception):
    pass


def _picks(v, on_sheet):
    """A list of {n, h}: each n a photo on the list, once; h '' (Normal), '+' (Longer) or '-' (Quicker)."""
    if not isinstance(v, list):
        raise Refused("picks")
    out, seen = [], set()
    for x in v:
        if not isinstance(x, dict) or set(x) - {"n", "h"}:
            raise Refused("picks")
        n, h = x.get("n"), x.get("h", "")
        if type(n) is not int or n not in on_sheet or n in seen or h not in ("", "+", "-") or not isinstance(h, str):
            raise Refused("picks")
        seen.add(n)
        out.append({"n": n, "h": h})
    return out


def _text(v, cap):
    if not isinstance(v, str) or len(v) > cap or "\x00" in v:
        raise Refused("text")
    return v


def _song(v, kit):
    """None (not picked yet), "" (No song), or the id of a song in this shoot (stage a3 fills the list)."""
    if v is None or v == "":
        return v
    if isinstance(v, str) and v in song_ids(kit):
        return v
    raise Refused("song")


def song_ids(kit):
    """The ids of the songs found for this kit. Stage a3 (the song) fills this in; until then there are none."""
    return set()


def _sel(v):
    if not isinstance(v, dict):
        raise Refused("sel")
    out = {}
    for k, ids in v.items():
        if k not in STYLES or not isinstance(ids, list) or len(ids) > 12:
            raise Refused("sel")
        if any(not isinstance(x, str) or not MOMENT_ID.fullmatch(x) for x in ids):
            raise Refused("sel")
        out[k] = list(ids)
    return out


def _feel(v):
    v = re.sub(r"\s+", " ", _text(v, 200)).strip()
    if len(v) > 40:
        raise Refused("feel")
    return v


# Every field the page may save, with its check (her record's "saved", BUILD.md section 8). A field the page
# does not send is kept as it is. A later step adds its own field here.
SAVE_FIELDS = {
    "picks": lambda v, kit, ons: _picks(v, ons),
    "mine": lambda v, kit, ons: v if type(v) is bool else _no("mine"),
    "mine_picks": lambda v, kit, ons: None if v is None else _picks(v, ons),
    "song": lambda v, kit, ons: _song(v, kit),
    "vibe": lambda v, kit, ons: v if v in VIBES else _no("vibe"),
    "footage": lambda v, kit, ons: v if v is None or type(v) is bool else _no("footage"),
    "style": lambda v, kit, ons: v if v in STYLES else _no("style"),
    "sel": lambda v, kit, ons: _sel(v),
    "ask": lambda v, kit, ons: _text(v, 600),
    "feel": lambda v, kit, ons: _feel(v),
}


def _no(what):
    raise Refused(what)


def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def save_from_page(body):
    """One save from the page. Returns (status, answer). Checks, in order: the kit, the numbered list's stamp,
    the counter the page had last seen, then every field it sent (the whole save is refused if any one is
    wrong, and nothing is written).

    The counter is this file's alone; an accepted save moves it on by one and the answer carries it. A save is
    taken only from a page that has seen the stored record: its "base" is the stored counter, or the stored
    record is that same page's own last save from that same base (its answer never arrived). Anything else is
    told there is something newer, and given it (REV_CHECK; with it off, the last save wins, as hers does).
    Sending exactly what is stored writes nothing."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "stamp", "base", "page", "saved"}:
        return _bad()
    base, page, sent = body.get("base"), body.get("page"), body.get("saved")
    if type(base) is not int or base < 0 or not isinstance(page, str) or not PAGE_ID.fullmatch(page):
        return _bad()
    if not isinstance(sent, dict) or not sent or set(sent) - set(SAVE_FIELDS):
        return _bad()
    with arrange.locked(lock_path(kit)):
        rec, rows, stamp = sync(kit)
        if not rows:
            return _bad(NOT_READY, 404)
        if body.get("stamp") != stamp:
            return _bad(OUR_WORDS["photos_changed"], 409, why="photos")
        on_sheet = {x["n"] for x in rows}
        stored = rec.get("saved") if isinstance(rec.get("saved"), dict) else {}
        try:
            clean = {k: SAVE_FIELDS[k](v, kit, on_sheet) for k, v in sent.items()}
        except Refused:
            return _bad()
        # More than a reel holds is refused, with one way through: an order that is ALREADY that long (an
        # older pick of Claude's) may be re-ordered and made shorter here, never longer.
        longest = len(claude_order(kit, None, on_sheet))
        for key in ("picks", "mine_picks"):
            if isinstance(clean.get(key), list) and len(clean[key]) > max(MAX_PICKS, longest, len(stored.get(key) or [])):
                return _bad(OUR_WORDS["too_many"], 400, why="many")
        rev = int(rec.get("rev") or 0)
        if all(stored.get(k) == v for k, v in clean.items()):
            return 200, {"ok": True, "rev": rev}      # what is stored already: nothing to write
        src = rec.get("from") if isinstance(rec.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not (REV_CHECK and base != rev and not own):
            new = dict(stored)
            new.update(clean)
            new["updated"] = time.time()
            rec["saved"] = new
            rec["rev"] = rev + 1
            rec["from"] = {"page": page, "base": base}
            rec["stamp"] = stamp
            rec["names"] = _names(new, {x["n"]: arrange.photo_name(x) for x in rows})
            save(kit, rec)
            return 200, {"ok": True, "rev": rev + 1}
    st = state(kit)
    return _bad(OUR_WORDS["newer"], 409, why="newer", state=st)


# ---------- the routes ----------

def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _get_page(handler, q):
    import arrange_page
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
    rows = arrange.sheet_rows(kit)
    if not rows:
        return arrange._send_page(handler, arrange_page.plain_page(NOT_READY))
    st = state(kit)
    if st is None:
        return arrange._send_page(handler, arrange_page.plain_page(NOT_READY))
    if any(not x["have"] and not x["missing"] for x in st["photos"]):
        # a PC without Pillow, or a kit too deep in folders for a PC: say so. A Mac: never.
        cant = arrange.cant_make(kit, rows)
        if cant:
            return arrange._send_page(handler, arrange_page.plain_page(cant[1] + " Tell Claude and it'll sort it out."))
        arrange.start_previews(kit)
    arrange._send_page(handler, page_html(kit.name, st["short"], st["kit_page"]))


def _get_state(handler, q):
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    st = state(kit) if arrange.sheet_rows(kit) else None
    if st is None:
        return arrange._send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    arrange._send_json(handler, st)


def _get_font(handler, q):
    key = _one(q, "f")
    if key not in FACE_FILES:
        return handler.send_error(404)
    try:
        data = (FONT_DIR / f"{key}.ttf").read_bytes()
    except OSError:
        return handler.send_error(404)
    handler.send_response(200)
    handler.send_header("Content-Type", "font/ttf")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=604800")
    handler.end_headers()
    handler.wfile.write(data)


def handle_get(handler, path, query):
    """Every GET for the reel page. Whatever goes wrong, the server answers and stays up."""
    try:
        if not arrange.our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/reel.html":
            return _get_page(handler, q)
        if path == "/reel-state":
            return _get_state(handler, q)
        if path == "/reel-font":
            return _get_font(handler, q)
        if path == "/reel-job":                     # stage a4: Make my reel's job
            return arrange._send_json(handler, {"ok": False, "words": NOT_YET}, 404)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path == "/reel-font":
                handler.send_error(404)
            elif path.endswith(".html"):
                import arrange_page
                arrange._send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _json_body(handler, path):
    """The body of a JSON POST as a dict, after arrange's guard (host, Origin, type, length). None when it was
    refused (and answered)."""
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "application/json", POST_CAP, path)
    if bad:
        arrange._drain(handler)
        arrange._send_json(handler, {"ok": False, "words": bad[1]}, bad[0])
        return None
    raw = handler.rfile.read(int(handler.headers.get("Content-Length").strip()))
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        body = None
    if not isinstance(body, dict):
        arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
        return None
    return body


def handle_post(handler, path, query):
    """Every POST for the reel page. Whatever goes wrong, the server answers and stays up."""
    try:
        body = _json_body(handler, path)
        if body is None:
            return
        if path == "/reel-save":
            code, out = save_from_page(body)
            return arrange._send_json(handler, out, code)
        # /reel-open (the song's and the footage's folders), /reel-make, /reel-capcut: the later stages
        return arrange._send_json(handler, {"ok": False, "words": NOT_YET}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        arrange.log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            arrange._send_json(handler, {"ok": False, "words": OUR_WORDS["cant_reach"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the page ----------
# Her stylesheet (reel-maker.html, v19), as she wrote it. Only the Google Fonts link is gone: the same two
# families are served by the Assistant itself (FONT_CSS). OUR_CSS adds what our own drag draws, and one rule
# hers lacks: anything marked hidden stays hidden. In hers ".opt .rec{display:inline-block}" wins over hidden, so
# "Recommended for behind-the-scenes reels" shows on a photos-only reel too; BUILD.md says it is for footage
# only (for the "Tell Nicole" list).
STYLE = r"""
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--coral:#F07F5A;--coral-2:#D4643F;--coral-l:#FCE6DD;--sand-l:#ECEAF6;--line:rgba(31,36,48,.12);
--long:#2f7d57;--long-l:#dcefe5;--quick:#7a5bb0;--quick-l:#ebe3f7;
--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue',Arial,sans-serif;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 9rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.homelink{display:inline-flex;align-items:center;gap:.45em;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px;white-space:nowrap;transition:background .2s}.homelink:hover{background:var(--coral-2)}
.head{padding:clamp(1.8rem,4vw,3rem) 0 .6rem;display:grid;gap:.5rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(30px,4.4vw,50px)/1.03 var(--sans);letter-spacing:-.035em}
h1 em{font:italic 400 1.1em/1 var(--display);color:var(--coral-2);letter-spacing:0}
.lede{margin:0;color:var(--ink-2);font-size:clamp(15.5px,1.3vw,17.5px);max-width:42em}

.step{background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.1rem;box-shadow:0 1px 0 var(--line)}
.step h2{display:flex;align-items:center;gap:.6rem;margin:0 0 .3rem;font:600 21px/1.2 var(--sans);letter-spacing:-.02em}
.num{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;font:600 13px/1 var(--sans);flex:none}
.step.done .num{background:var(--long)}
.say{margin:.2rem 0 .9rem;color:var(--ink-2);font-size:15px;max-width:44em}
.say b{color:var(--ink);font-weight:600}

.choice{display:flex;gap:.6rem;flex-wrap:wrap;margin:.2rem 0 1rem}
.opt{border:1.5px solid var(--line);background:var(--paper);border-radius:14px;padding:.75rem 1rem;text-align:left;cursor:pointer;font:inherit;color:inherit;min-width:220px;flex:1 1 220px;max-width:340px;transition:border-color .2s,box-shadow .2s}
.opt b{display:block;font-weight:600;font-size:15px}
.opt span{display:block;color:var(--ink-2);font-size:13.5px;line-height:1.35;margin-top:.15rem}
.opt:hover{border-color:var(--coral)}
.opt{position:relative}
.opt.on{border-color:var(--coral-2);background:#FFF6F2;box-shadow:0 0 0 1px var(--coral-2) inset}
.opt.on::after{content:"✓";position:absolute;top:.6rem;right:.75rem;width:22px;height:22px;border-radius:50%;background:var(--coral-2);color:#fff;font:700 12px/22px var(--sans);text-align:center}
.opt.on b{padding-right:1.6rem}
.tools{display:flex;gap:.7rem;align-items:center;margin:0 0 .6rem;min-height:34px}
.btn.small{padding:.35rem .9rem;font-size:14px}
.btn:disabled{opacity:.4;cursor:default}
.tools-say{font-size:13.5px;color:var(--ink-2,#6b625a)}
.ask{margin-top:.8rem}.ask label{display:block;font-size:14px;margin-bottom:.5rem}
.ask .ex{display:block;color:var(--ink-2);margin-top:.25rem;padding-left:.8rem;border-left:2px solid var(--coral-l)}
.ask textarea{width:100%;box-sizing:border-box;font:15px/1.45 var(--sans);padding:.6rem .8rem;border:1px solid var(--line);border-radius:10px;background:#fff;resize:vertical;min-height:4.6em}
.feel{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;margin-top:.75rem;font-size:14px}
.feel > b{font-weight:600;margin-right:.2rem}
.feel button{font:500 14px/1 var(--sans);padding:.55em .95em;border-radius:999px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.feel button:hover{border-color:var(--coral)}
.feel button.on{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.feel small{color:var(--ink-2);flex-basis:100%}
.feel input{font:15px/1.2 var(--sans);padding:.5em .8em;border:1.5px solid var(--coral-2);border-radius:999px;min-width:0;width:15em;max-width:100%;background:#fff;color:var(--ink)}
.feel input:focus{outline:2px solid var(--coral);outline-offset:0}
.ask textarea:focus{outline:2px solid var(--coral);outline-offset:0;border-color:transparent}
.result .leftout{background:#FFF8EC;border:1px solid #F3E3C3;border-radius:10px;padding:.6rem .8rem}
#reel .pick{aspect-ratio:auto;min-height:120px}
.tip{display:flex;gap:.8rem;align-items:flex-start;background:var(--cream);border-radius:14px;padding:.8rem 1rem;margin:0 0 1rem;font-size:14.5px}
.tip p{margin:0}
.tip .legend{margin:.35rem 0 0}
.opt .rec{display:inline-block;font:600 10px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--coral-2);background:var(--coral-l);border-radius:999px;padding:.3em .55em;margin-left:.35rem;vertical-align:2px}

#reel{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:10px;min-height:120px}
#reel:empty::before{content:"Your reel is empty. Tap photos below to add them.";color:var(--ink-2);grid-column:1/-1;align-self:center;text-align:center;font:italic 400 16px/1.3 var(--display)}
.tile{position:relative;border-radius:12px;overflow:hidden;background:var(--sand-l);cursor:grab;user-select:none;-webkit-user-select:none;box-shadow:0 0 0 1px var(--line)}
.tile .ph{aspect-ratio:9/16;position:relative}
.tile img{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none}
.pos{position:absolute;top:6px;left:6px;background:rgba(20,22,30,.72);color:#fff;font:600 12px/1 var(--sans);border-radius:999px;padding:.35em .6em}
.x{position:absolute;top:5px;right:5px;width:26px;height:26px;border-radius:50%;border:0;background:rgba(20,22,30,.65);color:#fff;font-size:16px;line-height:26px;cursor:pointer;padding:0}
.tile.long{box-shadow:0 0 0 3px var(--long)}
.tile.quick{box-shadow:0 0 0 3px var(--quick)}
.hold{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:5px;background:var(--paper)}
.hold button{border:1px solid var(--line);background:var(--paper);color:var(--ink-2);border-radius:8px;font:600 11.5px/1 var(--sans);padding:.45rem 0;cursor:pointer}
.hold button.lng.on{background:var(--long);border-color:var(--long);color:#fff}
.hold button.qk.on{background:var(--quick);border-color:var(--quick);color:#fff}
.ghost{opacity:.35}.chosen{outline:3px solid var(--coral);outline-offset:-3px}
.count{font-size:13.5px;color:var(--ink-2);margin-top:.7rem}
.count.warn{color:var(--coral-2)}
.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:.2rem 0 .9rem}
.legend i{display:inline-block;width:12px;height:12px;border-radius:4px;margin-right:.35rem;vertical-align:-1px}

details.all{margin-top:1rem;border-top:1px solid var(--line);padding-top:.8rem}
details.all summary{cursor:pointer;font-weight:600;font-size:15px}
#all{display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:8px;margin-top:.8rem}
.pick{position:relative;border-radius:10px;overflow:hidden;background:var(--sand-l);aspect-ratio:2/3;cursor:pointer;border:0;padding:0}
.pick img{width:100%;height:100%;object-fit:cover;display:block;transition:opacity .15s}
.pick .badge{position:absolute;right:5px;bottom:5px;background:var(--coral-2);color:#fff;font:700 12px/24px var(--sans);border-radius:999px;min-width:24px;height:24px;text-align:center;padding:0 6px;display:none}
.pick.in .badge{display:block}.pick.in img{opacity:.45}
.zoom{position:absolute;top:4px;right:4px;width:24px;height:24px;border-radius:50%;border:0;background:rgba(20,22,30,.55);color:#fff;font-size:12px;cursor:pointer;padding:0}

.btn{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:.62rem 1.1rem;font:600 14px/1 var(--sans);cursor:pointer;transition:all .2s var(--ease)}
.btn:hover{border-color:var(--coral);color:var(--coral-2)}
.btn.main{background:var(--ink);color:#fff;border-color:var(--ink)}.btn.main:hover{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.btn:disabled{opacity:.45;cursor:default}
.songs{display:grid;gap:.5rem;margin-top:.9rem}
.song{display:flex;align-items:center;gap:.75rem;border:1.5px solid var(--line);border-radius:14px;padding:.7rem .9rem;cursor:pointer;background:var(--paper);text-align:left;font:inherit;color:inherit;width:100%}
.song:hover{border-color:var(--coral)}
.song.on{border-color:var(--coral-2);background:#FFF6F2;box-shadow:0 0 0 1px var(--coral-2) inset}
.song .ic{width:34px;height:34px;border-radius:10px;background:var(--coral-l);color:var(--coral-2);display:grid;place-items:center;font-size:16px;flex:none}
.song b{display:block;font-weight:600;font-size:15px}
.song small{color:var(--ink-2);font-size:13px}
.song.none .ic{background:var(--sand-l);color:var(--ink-2)}
.waiting{font-size:14px;color:var(--ink-2);margin:.7rem 0 0}
.note{font-size:13px;color:var(--ink-2);margin:.9rem 0 0;max-width:46em}
.vibes{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.6rem}
.vibes .opt{max-width:none}

.make{position:fixed;left:0;right:0;bottom:0;background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:.8rem 16px;z-index:5}
.make .in{max-width:1040px;margin:0 auto;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.make .sum{flex:1 1 260px;font-size:14px;color:var(--ink-2)}
.make .sum b{color:var(--ink)}
#makeBtn{padding:.8rem 1.4rem;font-size:15px}
.result{display:none;margin-top:1.1rem;border-radius:22px;padding:1.2rem 1.3rem;background:var(--long-l)}
.result.on{display:block}
.result.bad{background:var(--coral-l)}
.result h3{margin:0 0 .3rem;font:600 19px/1.25 var(--sans)}
.result p{margin:.2rem 0;font-size:14.5px}
.result .acts{margin-top:.7rem;display:flex;gap:.5rem;flex-wrap:wrap}
.spin{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.vlist{display:grid;gap:.4rem;margin:.8rem 0 0}
.viewer .spin{border-color:rgba(0,0,0,.15);border-top-color:var(--coral-2);vertical-align:-2px}
.viewer{display:flex;gap:1.1rem;align-items:flex-start;border:1px solid var(--line);border-radius:16px;padding:1rem;margin:.8rem 0 0;background:var(--paper)}
.viewer video{width:250px;max-width:42vw;aspect-ratio:9/16;background:#111;border-radius:12px;display:block;flex:none;object-fit:contain}
.viewer video.wide{aspect-ratio:16/9;width:420px}
.vside{flex:1;min-width:0}
.vside h4{margin:0 0 .2rem;font:600 15px/1.3 var(--sans)}
.vside p{margin:0 0 .6rem;font-size:13.5px;color:var(--ink-2)}
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:5px;max-height:330px;overflow-y:auto;padding:2px;border-radius:10px}
.strip button{position:relative;border:0;padding:0;border-radius:6px;overflow:hidden;cursor:pointer;background:var(--sand-l);aspect-ratio:9/16;outline-offset:-2px}
.strip.wide button{aspect-ratio:16/9}
.strip img{width:100%;height:100%;object-fit:cover;display:block}
.strip span{position:absolute;left:0;right:0;bottom:0;font:600 9.5px/1.5 var(--sans);color:#fff;background:rgba(0,0,0,.45);text-align:center}
.strip button.now{outline:3px solid var(--coral)}
.strip button.inm::after{content:"";position:absolute;top:3px;right:3px;width:8px;height:8px;border-radius:50%;background:var(--coral-2);box-shadow:0 0 0 1.5px #fff}
.userow{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;margin-top:.8rem}
.userow .at{font-size:13.5px;color:var(--ink-2)}
.mom .play{position:absolute;left:8px;top:8px;width:34px;height:34px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;display:grid;place-items:center;font-size:13px;cursor:pointer}
.mom .play:hover{background:var(--coral-2)}
.mom .len{display:flex;align-items:center;gap:.35rem;margin-top:.45rem;font-size:13px}
.mom .len button{width:28px;height:26px;border-radius:8px;border:1px solid var(--line);background:#fff;font:600 15px/1 var(--sans);cursor:pointer;color:var(--ink)}
.mom .len button:hover{border-color:var(--coral)}
.mom .len b{min-width:3.6em;text-align:center;font-weight:600}
.mom.editing{border-color:var(--coral-2);box-shadow:0 0 0 1px var(--coral-2) inset}
.userow .btn.small[hidden]{display:none}
.mom .rm{position:absolute;right:8px;bottom:8px;font:600 12px/1 var(--sans);color:var(--ink-2);text-decoration:underline;cursor:pointer}
.mom .yours{display:inline-block;font:600 10px/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--coral-2);background:var(--coral-l);border-radius:999px;padding:.3em .55em;margin-bottom:.3rem}
@media(max-width:620px){.viewer{flex-direction:column}.viewer video{width:100%;max-width:none}}
.vid{display:flex;align-items:center;gap:.7rem;border:1px solid var(--line);border-radius:12px;padding:.55rem .8rem;font-size:14.5px}
.vid .ic{width:30px;height:30px;border-radius:9px;background:var(--coral-l);color:var(--coral-2);display:grid;place-items:center;font-size:13px;flex:none}
.vid small{color:var(--ink-2);margin-left:auto;white-space:nowrap}
.insight{background:#FFF8EC;border:1px solid #F3E3C3;border-radius:14px;padding:.85rem 1rem;margin:1rem 0 0;font-size:14px}
.insight b{font-weight:600}.insight p{margin:.35rem 0 0}
.paste{margin:1rem 0 0;font-size:14.5px}.paste p{margin:0 0 .45rem}
.paste .line{display:flex;align-items:center;gap:.7rem;justify-content:space-between;border:1.5px dashed var(--coral);border-radius:14px;padding:.6rem .7rem .6rem 1rem;max-width:520px;background:var(--paper)}
.paste .line span{font:italic 400 18px/1.3 var(--display)}
.mh{font:600 16px/1.2 var(--sans);margin:1.3rem 0 .2rem}
.moments{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,190px));gap:.8rem}
.mom{position:relative;border:1.5px solid var(--line);border-radius:14px;overflow:hidden;background:var(--paper);cursor:default;text-align:left;padding:0;font:inherit;color:inherit}
.mom .th{display:flex;aspect-ratio:9/16;background:#111;position:relative}
.mom .th video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#111}
.mom .play{border:0;padding:0;z-index:2}
.mom .play.on{background:var(--coral-2)}
.mom .th{cursor:pointer}
.mom .len{display:flex;align-items:center;justify-content:space-between;gap:.4rem;margin-top:.55rem}
.mom .len > span{display:flex;align-items:center;gap:.3rem}
.mom .tx .len b{display:inline-block;min-width:3.4em;text-align:center;font-size:13.5px}
.mom .len button.rm{width:auto;height:auto;border:0;background:none;padding:.2rem 0;font:600 12.5px/1 var(--sans);color:var(--ink-2);text-decoration:underline;cursor:pointer}
.mom .len button.rm:hover{color:var(--coral-2)}
.mom .usebtn{display:block;width:100%;margin-top:.55rem;padding:.55rem .6rem;border-radius:10px;border:1.5px solid var(--line);background:#fff;font:600 13.5px/1.1 var(--sans);color:var(--ink);cursor:pointer}
.mom .usebtn:hover{border-color:var(--coral)}
.mom .usebtn[disabled]{cursor:default;color:var(--ink-2);background:var(--sand-l);border-color:transparent;font-weight:500}
.mom.sel{border-color:var(--coral-2);box-shadow:0 0 0 1.5px var(--coral-2) inset}
.mom.sel .usebtn{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.mom .badge{position:absolute;right:8px;top:8px;z-index:2;font:700 12px/1 var(--sans);background:var(--coral-2);color:#fff;border-radius:999px;padding:.45em .7em}
.undo-note{display:flex;gap:.7rem;align-items:center;font-size:14px;background:var(--ink);color:#fff;border-radius:12px;padding:.55rem .9rem;margin:.6rem 0 0;width:max-content;max-width:100%}
.undo-note button{background:none;border:0;color:#FFB59B;font:600 14px var(--sans);text-decoration:underline;cursor:pointer;padding:0}
.mom .th img{height:100%;object-fit:cover;flex:1 1 0;min-width:0}
.mom .th img.ph{flex:0 0 38%;border-left:3px solid #fff}
.mom .tx{padding:.55rem .7rem .65rem;font-size:13.5px;line-height:1.35}
.mom .tx b{display:block;font-weight:600;font-size:14px}
.mom .tx small{color:var(--ink-2)}
.mom .kp{position:absolute;top:8px;right:8px;font:600 11px/1 var(--sans);border-radius:999px;padding:.4em .7em;background:var(--long);color:#fff}
.mom.off{opacity:.45}.mom.off .kp{background:var(--ink-2)}
.mom.off .kp::after{content:""}
.lb{position:fixed;inset:0;background:rgba(20,22,30,.92);display:none;place-items:center;z-index:50;cursor:zoom-out;padding:16px}
.lb.on{display:grid}.lb img{max-width:92vw;max-height:92vh;border-radius:12px}
@media(max-width:560px){#reel{grid-template-columns:repeat(auto-fill,minmax(88px,1fr))}.opt{min-width:0;max-width:none}}
"""

FONT_CSS = "".join(
    "@font-face{font-family:'%s';src:url('/reel-font?f=%s') format('truetype');font-weight:%d;font-style:%s;font-display:swap}"
    % (fam, key, wt, st) for fam, wt, st, key in FACES)

OUR_CSS = r"""
[hidden]{display:none!important}
.reelwrap{position:relative}
.ins{position:absolute;width:4px;border-radius:3px;background:var(--coral-2);pointer-events:none;display:none;box-shadow:0 0 0 2px rgba(212,100,63,.22);z-index:3}
.ins.on{display:block}
#reel .tile{touch-action:none}
#all .pick{touch-action:pan-y}
#reel img,#all img{pointer-events:none;-webkit-user-drag:none;user-select:none}
.tile.dragging,.pick.dragging{opacity:.35}
.tile .ph .wait,.pick .wait{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:8px;font-size:12px;line-height:1.3;color:var(--ink-2)}
.notice{font-size:13.5px;color:var(--coral-2)}
.notice button{margin-left:.5rem}
.limit{display:none}.limit.on{display:block}
body.arr-dragging,body.arr-dragging *{cursor:grabbing!important;user-select:none!important;-webkit-user-select:none!important}
.arr-lift{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;will-change:transform;transform-origin:0 0}
.arr-lift .pic{width:100%;height:100%;border-radius:12px;overflow:hidden;background:var(--sand-l);box-shadow:0 0 0 3px #fff,0 18px 36px -12px rgba(0,0,0,.5)}
.arr-lift .pic img{display:block;width:100%;height:100%;object-fit:cover}
.arr-lift .say{position:absolute;left:50%;top:100%;transform:translateX(-50%);margin-top:8px;white-space:nowrap;background:var(--ink);color:#fff;font:600 12.5px/1 var(--sans);padding:6px 10px;border-radius:8px;display:none}
.arr-lift .say.on{display:block}
"""

# Her steps, in her order (BUILD.md section 5: "This order is final"). Each is (her section's id, the
# function that writes it, or None while that step is not built yet). A step left out is simply not on the page.
def _order_section(w, num):
    e = html.escape
    return (
        "<section class='step' id='step1'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["order_h2"]) + "</h2>"
        "<p class='say'>" + e(w["order_say"]) + "</p>"
        "<div class='choice'>"
        "<button class='opt' id='useClaude' type='button'><b>" + e(w["claude_b"])
        + "<span class='rec' id='claudeRec' hidden>" + e(w["claude_rec"]) + "</span></b>"
        "<span id='claudeWords'>" + e(w["claude_words"]) + "</span></button>"
        "<button class='opt' id='useMine' type='button'><b>" + e(w["mine_b"]) + "</b><span>" + e(w["mine_words"]) + "</span></button>"
        "</div>"
        "<div class='tip'><div><p>" + w["tip_html"] + "</p>"
        "<div class='legend'><span><i style='background:var(--long)'></i>" + e(w["legend_long"]) + "</span>"
        "<span><i style='background:var(--quick)'></i>" + e(w["legend_quick"]) + "</span></div></div></div>"
        "<div class='tools'><button class='btn small' id='undoBtn' type='button' disabled>" + e(w["undo"]) + "</button>"
        "<span class='tools-say' id='undoSay'></span><span class='notice' id='notice'></span></div>"
        "<div class='reelwrap' id='reelwrap'><div id='reel'></div></div>"
        "<div class='count' id='count'></div>"
        "<div class='count warn limit' id='limit'>" + e(OUR_WORDS["too_many"]) + "</div>"
        "<details class='all' id='allBox'><summary>" + e(w["all_summary"]) + "</summary><div id='all'></div></details>"
        "</section>")


SECTIONS = [
    ("step0", None),            # 1. Behind-the-scenes footage? (stage b)
    ("step1", _order_section),  # 2. Put your photos in order
    ("step3", None),            # 3. Add your song (stage a3)
    ("stepStyle", None),        # 4. What style of behind the scenes is this? (stage b2)
    ("step4", None),            # 5. Pick the vibe (stage a4)
]


def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page_html(kit_name, short, kit_page=False):
    e = html.escape
    w = WORDS
    title = w["reel_of"].replace("{short}", short)
    data = {"words": dict(WORDS, **OUR_WORDS), "max": MAX_PICKS, "dragOut": DRAG_OUT, "undoSteps": UNDO_STEPS,
            "saveAfter": SAVE_AFTER_MS, "followEvery": FOLLOW_MS}
    steps = "".join(fn(w, i) for i, fn in enumerate((fn for _, fn in SECTIONS if fn), 1))
    back_href = ("/content/" + quote(kit_name) + "/Post%20kit.html") if kit_page else "/home"
    back_words = w["back_kit"] if kit_page else OUR_WORDS["back_home"]
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + e(title) + "</title><style>" + FONT_CSS + STYLE + OUR_CSS + "</style></head>"
        "<body data-kit='" + e(kit_name, quote=True) + "'>"
        "<div class='wrap'>"
        "<div class='bar'><a class='homelink' id='back' href='" + e(back_href, quote=True) + "'><span aria-hidden='true'>&larr;</span> "
        "<span id='backWords'>" + e(back_words) + "</span></a>" + brand.bar() + "</div>"
        "<header class='head'><span class='eyebrow'>" + e(w["eyebrow"]) + "</span>"
        "<h1 id='title'>" + e(title) + "<em>.</em></h1>"
        "<p class='lede'>" + w["lede_html"] + "</p></header>"
        + steps +
        "<div class='result' id='result'></div>"
        "</div>"
        "<div class='lb' id='lb'><img id='lbimg' alt=''></div>"
        "<script type='application/json' id='reelData'>" + _json_for_script(data) + "</script>"
        "<script>" + DRAG_JS + "</script><script>" + MODEL_JS + "</script><script>" + CORE_JS + "</script>"
        "<script>" + ORDER_JS + "</script><script>" + START_JS + "</script>"
        "</body></html>")


def _drag_js():
    import arrange_page
    return arrange_page.DRAG_JS


DRAG_JS = _drag_js()

# The order as a list of {n, h} (her shape: h '' Normal, '+' Longer, '-' Quicker). No page in it.
MODEL_JS = r"""
(function(root){
  'use strict';
  function at(list, n){ for (var i = 0; i < list.length; i++) { if (list[i].n === n) return i; } return -1; }
  function copy(list){ return (list || []).map(function(r){ return {n: r.n, h: r.h || ''}; }); }
  function clampPos(pos, len){ pos = Math.floor(Number(pos)); if (!(pos >= 0)) pos = 0; return pos > len ? len : pos; }
  // Put photo n into the gap before the photo now at pos (pos = length: the end). Already in: it moves there and
  // keeps its mark. Not in and the list full: null.
  function insertAt(list, n, pos, max){
    var from = at(list, n), out = list.slice();
    pos = clampPos(pos, list.length);
    if (from >= 0) {
      if (pos === from || pos === from + 1) return list;
      var it = out.splice(from, 1)[0];
      if (pos > from) pos -= 1;
      out.splice(pos, 0, it);
      return out;
    }
    if (list.length >= max) return null;
    out.splice(pos, 0, {n: n, h: ''});
    return out;
  }
  function takeOut(list, n){ var i = at(list, n); if (i < 0) return list; var out = list.slice(); out.splice(i, 1); return out; }
  function sameNums(a, b){ if (a.length !== b.length) return false; for (var i = 0; i < a.length; i++) { if (a[i].n !== b[i].n) return false; } return true; }
  // where a drop lands among the row's tiles: the first one the pointer is above the bottom of and left of the
  // middle of, or above altogether; none: the end (arrange_page's rule)
  function landing(rects, x, y){
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if ((y < r.bottom && x < (r.left + r.right) / 2) || y < r.top) return i;
    }
    return rects.length;
  }
  root.ReelModel = {at: at, copy: copy, insertAt: insertAt, takeOut: takeOut, sameNums: sameNums, landing: landing};
})(typeof window !== 'undefined' ? window : this);
"""

# The page's core: the record, saving (retried until it lands), following what changes elsewhere. Each step is
# a part: {fields(): what it saves, adopt(st, first): take a state, follow(st): a newer state arrived while idle}.
CORE_JS = r"""
(function(){
  'use strict';
  var DATA = JSON.parse(document.getElementById('reelData').textContent);
  var W = DATA.words, KIT = document.body.dataset.kit, Q = 'kit=' + encodeURIComponent(KIT);
  var $ = function(id){ return document.getElementById(id); };
  var esc = function(t){ return String(t).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var fill = function(t, o){ return String(t).replace(/\{(\w+)\}/g, function(m, k){ return o && o[k] != null ? o[k] : m; }); };
  // a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this page's
  // own save (whose answer never arrived) from a save made in another window
  var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');
  var parts = [], S = null, rev = 0, stamp = '', blocked = false;
  var saving = false, dirty = false, timer = null, retryT = null, followT = null;

  function notice(text, reload){
    var n = $('notice'); if (!n) return;
    n.textContent = text || '';
    if (reload) { var b = document.createElement('button'); b.className = 'btn small'; b.type = 'button'; b.textContent = W.reload; b.onclick = function(){ location.reload(); }; n.appendChild(b); }
  }
  function photosChanged(){
    blocked = true; dirty = false; clearTimeout(timer); clearTimeout(retryT);
    notice(W.photos_changed, true);
  }
  function fields(){ var out = {}; parts.forEach(function(p){ if (p.fields) { var f = p.fields(); for (var k in f) out[k] = f[k]; } }); return out; }
  function adopt(st, first){ S = st; rev = st.rev; stamp = st.stamp; parts.forEach(function(p){ if (p.adopt) p.adopt(st, first); }); }
  function save(){
    if (blocked || !S) return;
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(send, DATA.saveAfter);
  }
  function body(){ return JSON.stringify({kit: KIT, stamp: stamp, base: rev, page: PAGE, saved: fields()}); }
  function send(){
    clearTimeout(timer); clearTimeout(retryT);
    if (saving || blocked || !dirty || !S) return;
    saving = true; dirty = false;
    fetch('/reel-save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: body()})
      .then(function(r){
        if (r.status >= 500) throw new Error('no answer');
        return r.json().then(function(j){ return {code: r.status, j: j}; });
      })
      .then(function(res){
        saving = false;
        var j = res.j || {};
        if (res.code === 200 && j.ok) {
          if (typeof j.rev === 'number') rev = j.rev;
          if ($('notice') && $('notice').textContent === W.retry) notice('');
          if (dirty) send();
          return;
        }
        if (res.code === 409 && j.why === 'photos') { photosChanged(); return; }
        if (res.code === 409 && j.why === 'newer' && j.state && j.state.ok) {
          dirty = false;
          adopt(j.state, false);
          notice(W.newer);
          return;
        }
        if (res.code === 404) { dirty = true; notice(j.words || W.cant_reach); retryT = setTimeout(send, 2000); return; }
        notice(j.words || W.cant_reach, true);       // refused in a way trying again will not fix
      })
      .catch(function(){ saving = false; dirty = true; notice(W.retry); retryT = setTimeout(send, 2000); });
  }
  // a change still waiting when the page goes away is sent on its way
  window.addEventListener('pagehide', function(){
    if (!dirty || blocked || !S || saving) return;
    try { fetch('/reel-save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: body(), keepalive: true}); } catch (e) {}
  });
  function getState(){ return fetch('/reel-state?' + Q, {cache: 'no-store'}).then(function(r){ return r.json(); }); }
  function idle(){ return !!S && !blocked && !saving && !dirty && !(R.busy && R.busy()); }
  function follow(){
    if (document.hidden || !idle()) return;
    var asked = rev;
    getState().then(function(st){
      if (!st || !st.ok || !idle() || rev !== asked) return;
      if (st.stamp !== stamp) { photosChanged(); return; }
      if (st.rev !== rev) { adopt(st, false); return; }          // saved in another window: shown as it is now
      S = st;
      parts.forEach(function(p){ if (p.follow) p.follow(st); });
    }).catch(function(){});
  }
  function start(){
    getState().then(function(st){
      if (!st || !st.ok) throw new Error('not ready');
      notice('');
      adopt(st, true);
      if (!followT) followT = setInterval(follow, DATA.followEvery);
    }).catch(function(){
      parts.forEach(function(p){ if (p.unreachable) p.unreachable(); });
      setTimeout(start, 2000);
    });
  }
  var R = window.Reel = {data: DATA, words: W, kit: KIT, q: Q, $: $, esc: esc, fill: fill, part: function(p){ parts.push(p); },
    save: save, notice: notice, start: start, state: function(){ return S; }, busy: null, followNow: follow,
    photoUrl: function(p, size){ return '/kit-photo?' + Q + '&n=' + p.n + '&size=' + size + '&v=' + encodeURIComponent(p.v || ''); },
    // her renumbering: only the steps that show are counted
    renumber: function(){ var k = 0; document.querySelectorAll('section.step').forEach(function(s){ if (!s.hidden) s.querySelector('.num').textContent = ++k; }); }};
})();
"""

# Step 2, her "Put your photos in order", with our drag.
ORDER_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc, M = window.ReelModel, MAX = R.data.max;
  var photos = [], byN = {}, claude = [], claudeBts = [], reel = [], mine = false, mineOrder = null;
  var footage = null;            // step 1 sets this (R.setFootage); until then, no footage
  var marks = {};                // only the Longer / Quicker they set themselves, carried over to the assistant's next order
  var undoStack = [], lastSnap = null, undoT = null, pollT = null, stampSeen = null;
  var short = '';
  var reelEl = $('reel'), allEl = $('all'), wrapEl = $('reelwrap'), insEl = document.createElement('div');
  insEl.className = 'ins'; wrapEl.appendChild(insEl);

  var claudeOrder = function(){ return (footage && claudeBts.length) ? claudeBts : claude; };
  function notPicked(){ $('claudeWords').innerHTML = R.fill(W.not_picked_html, {short: esc(short)}); }
  function setMode(m){
    mine = m;
    $('useClaude').classList.toggle('on', !mine);
    $('useMine').classList.toggle('on', mine);
  }
  function limit(on){ $('limit').classList.toggle('on', !!on); }

  // ---- drawing ----
  function picture(holder, p, size){
    var wait = holder.querySelector('.wait');
    if (p && p.have) {
      var img = holder.querySelector('img');
      if (!img) {
        img = document.createElement('img'); img.alt = R.fill(W.photo_alt, {n: p.n}); img.decoding = 'async';
        if (holder.classList.contains('pick')) img.loading = 'lazy';
        holder.insertBefore(img, holder.firstChild);
      }
      var u = R.photoUrl(p, size);
      if (img.getAttribute('src') !== u) img.setAttribute('src', u);
      if (wait) wait.remove();
    } else if (!wait) {
      wait = document.createElement('span'); wait.className = 'wait';
      holder.insertBefore(wait, holder.firstChild);
    }
    if (wait) wait.textContent = p && p.missing ? W.cant_read : W.getting_ready;
  }
  function renderReel(){
    reelEl.innerHTML = '';
    reel.forEach(function(r, i){
      var p = byN[r.n]; if (!p) return;
      var t = document.createElement('div');
      t.className = 'tile' + (r.h === '+' ? ' long' : r.h === '-' ? ' quick' : '');
      t.dataset.n = r.n;
      t.innerHTML = '<div class="ph"><span class="pos">' + (i + 1) + '</span>' +
        '<button class="x" type="button" title="' + esc(W.take_out) + '" aria-label="' + esc(R.fill(W.take_out_label, {n: i + 1})) + '">&times;</button></div>' +
        '<div class="hold"><button class="lng ' + (r.h === '+' ? 'on' : '') + '" type="button">' + esc(W.longer) + '</button>' +
        '<button class="qk ' + (r.h === '-' ? 'on' : '') + '" type="button">' + esc(W.quicker) + '</button></div>';
      picture(t.querySelector('.ph'), p, 's');
      reelEl.appendChild(t);
    });
    var n = reel.length, c = $('count');
    var longs = reel.filter(function(r){ return r.h === '+'; }).length, quicks = reel.filter(function(r){ return r.h === '-'; }).length;
    c.textContent = R.fill(n === 1 ? W.one_photo : W.photos, {n: n}) + (longs ? R.fill(W.n_longer, {k: longs}) : '') +
      (quicks ? R.fill(W.n_quicker, {k: quicks}) : '') + (n && n < 6 ? W.few : n > 20 ? W.lots : '');
    c.className = 'count' + ((n && n < 6) || n > 20 ? ' warn' : '');
    $('step1').classList.toggle('done', n >= 1);
  }
  function buildAll(){
    allEl.innerHTML = '';
    photos.forEach(function(p){
      var b = document.createElement('div');
      b.className = 'pick'; b.dataset.n = p.n; b.setAttribute('role', 'button'); b.tabIndex = 0;
      b.innerHTML = '<button class="zoom" type="button" title="' + esc(W.zoom) + '" aria-label="' + esc(W.zoom) + '">&#10530;</button><span class="badge"></span>';
      picture(b, p, 's');
      b.onkeydown = function(e){ if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(p.n); } };
      b.querySelector('.zoom').onclick = function(e){ e.stopPropagation(); openBig(p.n); };
      allEl.appendChild(b);
    });
  }
  function renderAll(){
    var pos = {}; reel.forEach(function(r, i){ pos[r.n] = i + 1; });
    allEl.querySelectorAll('.pick').forEach(function(el){
      var p = pos[+el.dataset.n];
      el.classList.toggle('in', !!p);
      el.querySelector('.badge').textContent = p || '';
    });
  }
  function refreshPictures(){
    reelEl.querySelectorAll('.tile').forEach(function(t){ picture(t.querySelector('.ph'), byN[+t.dataset.n], 's'); });
    allEl.querySelectorAll('.pick').forEach(function(b){ picture(b, byN[+b.dataset.n], 's'); });
  }
  function track(){
    var s = JSON.stringify({reel: reel, mine: mine});
    if (lastSnap !== null && s !== lastSnap) { undoStack.push(lastSnap); if (undoStack.length > R.data.undoSteps) undoStack.shift(); }
    lastSnap = s;
    $('undoBtn').disabled = !undoStack.length;
  }
  function refresh(){ limit(false); renderReel(); renderAll(); R.save(); track(); }

  // ---- the two orders ----
  function followClaude(){        // on "Let my assistant choose", always show the assistant's latest order
    if (mine) return;
    var c = claudeOrder();
    if (!c.length) return;
    if (M.sameNums(c, reel)) return;          // same photos: keep their Longer / Quicker marks
    reel = c.map(function(r){ return {n: r.n, h: marks[r.n] !== undefined ? marks[r.n] : (r.h || '')}; });
    renderReel(); renderAll(); track();
  }
  function setFootage(v){
    footage = v;
    $('claudeRec').hidden = v !== true;
    $('claudeWords').textContent = v === true ? W.claude_words_bts : W.claude_words;
    if (!claudeOrder().length) notPicked();
    R.renumber(); followClaude();
  }
  R.setFootage = setFootage;
  $('useClaude').onclick = function(){
    var c = claudeOrder();
    if (!c.length) { notPicked(); return; }
    if (mine) mineOrder = M.copy(reel);         // keep theirs before showing the assistant's
    reel = M.copy(c);
    setMode(false); refresh();
  };
  $('useMine').onclick = function(){
    if (!mine && mineOrder && mineOrder.length) reel = M.copy(mineOrder);   // their own order, as they left it
    setMode(true); $('allBox').open = true; refresh();
  };
  function toggle(n){
    var i = M.at(reel, n);
    if (i >= 0) reel.splice(i, 1);
    else { if (reel.length >= MAX) { limit(true); return; } reel.push({n: n, h: ''}); }
    setMode(true); refresh();
  }
  reelEl.addEventListener('click', function(e){
    if (drag.justDragged) return;
    var b = e.target.closest('button'); if (!b) return;
    var t = b.closest('.tile'); if (!t) return;
    var n = +t.dataset.n, i = M.at(reel, n); if (i < 0) return;
    e.stopPropagation();
    if (b.classList.contains('x')) { reel.splice(i, 1); setMode(true); refresh(); }
    else if (b.classList.contains('lng')) { reel[i] = {n: n, h: reel[i].h === '+' ? '' : '+'}; marks[n] = reel[i].h; refresh(); }
    else if (b.classList.contains('qk')) { reel[i] = {n: n, h: reel[i].h === '-' ? '' : '-'}; marks[n] = reel[i].h; refresh(); }
  });
  $('undoBtn').onclick = function(){
    if (!undoStack.length) return;
    var s = JSON.parse(undoStack.pop());
    reel = s.reel; setMode(s.mine);
    lastSnap = JSON.stringify({reel: reel, mine: mine});
    limit(false); renderReel(); renderAll(); R.save();
    $('undoBtn').disabled = !undoStack.length;
    $('undoSay').textContent = W.undone; clearTimeout(undoT); undoT = setTimeout(function(){ $('undoSay').textContent = ''; }, 1500);
  };

  // ---- the big view (hers: tap anywhere to close; Escape too) ----
  var lb = $('lb'), lbimg = $('lbimg');
  function openBig(n){ var p = byN[n]; if (!p || !p.have) return; lbimg.src = R.photoUrl(p, 'l'); lbimg.alt = R.fill(W.photo_alt, {n: n}); lb.classList.add('on'); }
  lb.onclick = function(){ lb.classList.remove('on'); };
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && lb.classList.contains('on')) lb.classList.remove('on'); });

  // ---- dragging (ours: a photo is lifted and a bar shows where it will land) ----
  var target = null;
  function inside(r, x, y){ return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; }
  function clearIns(){ insEl.classList.remove('on'); }
  function showIns(pos, tiles, y){
    var wr = wrapEl.getBoundingClientRect(), left, top, h;
    if (!tiles.length) { left = 6; top = 8; h = Math.max(60, reelEl.clientHeight - 16); }
    else {
      var a = pos < tiles.length ? tiles[pos] : null, before = pos > 0 ? tiles[pos - 1] : null, useBefore = !a, r;
      if (a && before) { var ar = a.getBoundingClientRect(), br = before.getBoundingClientRect(); if (ar.top > br.top + 4 && y < ar.top) useBefore = true; }
      if (useBefore) { r = before.getBoundingClientRect(); left = r.right - wr.left + 3; }
      else { r = a.getBoundingClientRect(); left = r.left - wr.left - 7; }
      top = r.top - wr.top; h = r.height;
    }
    insEl.style.left = left + 'px'; insEl.style.top = top + 'px'; insEl.style.height = h + 'px';
    insEl.classList.add('on');
  }
  function over(x, y, t){
    clearIns(); target = null;
    var n = +t.dataset.n, at = M.at(reel, n), fromRow = t.classList.contains('tile');
    if (inside(wrapEl.getBoundingClientRect(), x, y)) {
      var tiles = Array.prototype.slice.call(reelEl.querySelectorAll('.tile'));
      var pos = M.landing(tiles.map(function(k){ return k.getBoundingClientRect(); }), x, y);
      if (at >= 0 && (pos === at || pos === at + 1)) return;          // where it already is
      if (at < 0 && reel.length >= MAX) { target = {kind: 'full'}; return; }
      target = {kind: 'in', pos: pos};
      showIns(pos, tiles, y);
      return;
    }
    if (R.data.dragOut && fromRow && inside(allEl.getBoundingClientRect(), x, y)) target = {kind: 'out'};
  }
  function drop(t){
    var n = +t.dataset.n, tg = target;
    target = null; clearIns();
    if (!tg) return;
    if (tg.kind === 'full') { limit(true); return; }
    if (tg.kind === 'out') { reel = M.takeOut(reel, n); setMode(true); refresh(); return; }
    var next = M.insertAt(reel, n, tg.pos, MAX);
    if (next == null) { limit(true); return; }
    if (next === reel) return;
    reel = next; setMode(true); refresh();
  }
  var drag = window.arrangeDrag({
    tileOf: function(el){
      var t = el && el.closest ? el.closest('.tile, .pick') : null;
      return t && (reelEl.contains(t) || allEl.contains(t)) ? t : null;
    },
    canDrag: function(t, e){ return !!R.state() && !(e.pointerType === 'touch' && t.classList.contains('pick')); },
    picture: function(t){ return t.classList.contains('tile') ? t.querySelector('.ph') : t; },
    over: over, drop: drop,
    cancel: function(){ target = null; clearIns(); },
    click: function(t){ if (t.classList.contains('pick')) toggle(+t.dataset.n); },
    scrollBox: null
  });
  R.busy = function(){ return drag.busy(); };

  // ---- the state from the Assistant ----
  function known(list){ return (list || []).filter(function(r){ return !!byN[r.n]; }).map(function(r){ return {n: r.n, h: r.h || ''}; }); }
  function stillMaking(){ return photos.some(function(p){ return !p.have && !p.missing; }); }
  function pollPictures(){
    if (pollT || !stillMaking()) return;
    pollT = setInterval(function(){
      fetch('/reel-state?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(st){
        if (!st || !st.ok || st.stamp !== stampSeen) return;
        photos = st.photos; photos.forEach(function(p){ byN[p.n] = p; });
        refreshPictures();
        if (!stillMaking()) { clearInterval(pollT); pollT = null; }
      }).catch(function(){});
    }, 1500);
  }
  R.part({
    fields: function(){
      if (mine) mineOrder = M.copy(reel);
      return {picks: M.copy(reel), mine: mine, mine_picks: mineOrder ? M.copy(mineOrder) : null};
    },
    adopt: function(st, first){
      short = st.short;
      document.title = R.fill(W.reel_of, {short: short});
      $('title').innerHTML = esc(R.fill(W.reel_of, {short: short})) + '<em>.</em>';
      var back = $('back');
      if (st.kit_page) { back.href = '/content/' + encodeURIComponent(R.kit) + '/Post%20kit.html'; $('backWords').textContent = W.back_kit; }
      var rebuild = stampSeen !== st.stamp;
      stampSeen = st.stamp;
      photos = st.photos; byN = {}; photos.forEach(function(p){ byN[p.n] = p; });
      claude = known(st.claude);
      var saved = st.saved;
      if (saved && Array.isArray(saved.picks)) {
        reel = known(saved.picks);
        mine = !!saved.mine;
        mineOrder = Array.isArray(saved.mine_picks) ? known(saved.mine_picks) : (mine ? M.copy(reel) : null);
        if (saved.footage === true || saved.footage === false) footage = saved.footage;
      } else {
        reel = M.copy(claude);
        mine = !claude.length;
      }
      if (rebuild) buildAll();
      setMode(mine); renderReel(); renderAll();
      if (first) {
        setFootage(footage);
        if (!reel.length) $('allBox').open = true;
      } else {
        $('claudeWords').textContent = footage === true ? W.claude_words_bts : W.claude_words;
        if (!claudeOrder().length) notPicked();
      }
      track();
      pollPictures();
    },
    follow: function(st){
      var c = known(st.claude);
      if (JSON.stringify(c) !== JSON.stringify(claude)) {          // a fresh pick from the assistant
        claude = c;
        $('claudeWords').textContent = footage === true ? W.claude_words_bts : W.claude_words;
        if (!claudeOrder().length) notPicked();
        followClaude();
      }
    },
    unreachable: function(){
      var r = $('reel');
      if (r && !$('reachLine')) { var p = document.createElement('p'); p.className = 'say'; p.id = 'reachLine'; p.textContent = W.reach; wrapEl.parentNode.insertBefore(p, wrapEl); }
    }
  });
  R.part({adopt: function(){ var l = $('reachLine'); if (l) l.remove(); }});
})();
"""

START_JS = r"""window.Reel.start();"""


# ---------- the commands (Claude's) ----------

def page_address(kit):
    base = arrange.server_base()
    return f"{base}/reel.html?kit={quote(kit.name)}" if base else None


def cmd_open(kit):
    listed = arrange.kit_by_name(kit.name)
    if listed is None or listed.resolve() != kit.resolve():
        say(f"STOP: \"{kit.name}\" isn't in Your Content, so the page can't show it.")
        return 1
    if not arrange.sheet_rows(kit):
        if kit_mod.sheet(kit) != 0 or not arrange.sheet_rows(kit):
            say("STOP: couldn't number this shoot's photos. Are they where the kit says they are?")
            return 1
    got = arrange.make_previews(kit)
    if got.get("cant"):
        say(f"STOP: {got['cant']}")
        return 1
    if got["missing"] or got["failed"]:
        say(f"({got['missing'] + got['failed']} of {got['of']} photos couldn't be read right now; the page will say so.)")
    addr = page_address(kit)
    if not addr:
        say("STOP: couldn't start the page server.")
        return 2
    say(f"{got['of']} photos in the shoot.")
    say(addr)
    return 0


def cmd_show(kit):
    st = state(kit)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    saved = st["saved"] or {}
    say(f"{st['short']}  ({kit.name})")
    say(f"  Claude's order: {','.join(str(x['n']) + x['h'] for x in st['claude']) or '(none yet)'}")
    if saved:
        whose = "their own order" if saved.get("mine") else "the assistant's order"
        say(f"  On the page: {whose}")
    else:
        say("  On the page: nothing saved yet")
    say(f"  The order Make my reel uses: {current_picks(kit) or '(none yet)'}")
    say(f"  Saved {st['rev']} time{'s' if st['rev'] != 1 else ''}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open").add_argument("words")
    sub.add_parser("show").add_argument("words")
    a = ap.parse_args()
    import fresh
    fresh.announce()
    kit = kit_mod.find_kit(a.words)
    try:
        if a.cmd == "open":
            return cmd_open(kit)
        return cmd_show(kit)
    except arrange.Busy:
        say("STOP: this shoot's reel page is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
