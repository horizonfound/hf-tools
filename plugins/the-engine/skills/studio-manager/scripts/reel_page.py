#!/usr/bin/env python3
"""The reel page: Nicole's reel maker (handoff v19, pages/reel-maker.html), as the Assistant's own page.

    python3 reel_page.py open "beach"      get the page ready (the numbered list, the small copies) and print its address
    python3 reel_page.py show "beach"      what the page has saved: whose order, the order, the song and vibe picked
    python3 reel_page.py make "beach" [--capcut-song "<name>"] [--hook "..."] [--name "..."] [--no-song] [--dry-run]
                                           Claude's own Make my reel, for what the page doesn't do (a song from
                                           CapCut's music, words on the first photo, a second take under another
                                           name) or when the page said "Ask your assistant to make the reel instead":
                                           the page's order, song and vibe, made exactly as the page makes it
    python3 reel_page.py job "<kit>" --id <id>   (the page server's own) make the reel a page asked for

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
  GET  /reel-songs?kit=<folder>  step 3: the songs in the shoot's Music and Photos folders, {id, name, where, kind}
  POST /reel-open                {kit, what: "music"}: makes <kit>/Music if it isn't there and opens it (finder.py)
  POST /reel-make                {kit, stamp, picks, song, vibe, test}: Make my reel; answers with a job to ask after
  GET  /reel-job?kit=&id=        how that job is going: queued, running, done (her lines) or problem (her words)
  POST /reel-capcut              {kit}: Open CapCut (capcut.py's own open), in her words (capcut.OPEN_WORDS)
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
  <kit>/.kit/reel-job.json        Make my reel's newest job: {id, state, ask: {picks, song id, vibe, dry, stamp}, pid,
                                  words, project, problem, short_song}; reel-job.lock is held by its process while it
                                  lives; reel-job-status.json is what reel.py make --status said; .kit/reels holds the
                                  reel's working files (reel.REEL_WORK_IN_KIT)
  "made" in the record            one entry per reel made: {project, picks, vibe, footage, song (its file name),
                                  song_id, when}; the next reel of the same choices is the next mix (her variation)

The defaults Dustin and Nicole may change sit in one place each (PLAN section 2): MAX_PICKS and its line (23),
DRAG_OUT (22), REV_CHECK (21), the WORDS table (9, and every word on the page), STYLE (16), SHORT_SONG_FROM_TOP (8),
SOUND_BESIDE_OUTSIDE (4), PLAN_WORDS (5). Elsewhere: reel.REEL_NAME (6), reel.REEL_WORK_IN_KIT (1),
timing.DEFAULT_PACE (7), capcut.OPEN_WORDS (24), finder.BEHIND_WORDS (25).

Songs and the sound of a screen recording (hers: server.py list_songs, sound_of): a song is named to the page by
an id made from where it is and its file name. A recording's sound is made once with sound.py (afconvert on a Mac,
Media Foundation on a PC) as "<name> sound.m4a" (".wav" on a PC) beside it, or in <kit>/Music when the recording
sits in an export folder outside Your Content; a sound already there is used as it is, never written over.

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
import subprocess
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
SHORT_SONG_FROM_TOP = 40  # decision 8: a song shorter than this (seconds) starts at the top (her code), not where it picks up
SOUND_BESIDE_OUTSIDE = False   # decision 4: a screen recording in a Photos folder outside Your Content (an export folder
                        # the kit only points to) has its sound made in <kit>/Music, never in their folder. True: beside it
PLAN_WORDS = "nicole"   # decision 5: the Plan line in the result box is hers ("Plan: 14 photos, 15.2 seconds, every cut on
                        # the beat at about 85 beats a minute, starting the song at the top."); "reel": reel.py's longer line
MAKE_LIMIT = 600        # hers: a reel may take ten minutes to make, then it is stopped and the page says so
SONG_EVERY_MS = 3000    # hers: the song list is looked at again every 3 seconds
JOB_EVERY_MS = 700      # how often the page asks how Make my reel is going (ours: hers waited on one long request)
JOB_BOOT = 20.0         # seconds a job may take to start before "queued" means it never did

RECORD = "reel-page.json"
PREV = "reel-page.prev.json"
LOCK = "reel-page.lock"
JOB = "reel-job.json"                 # Make my reel's job: its state, its words, what it was asked (ids and numbers only)
JOB_LOCK = "reel-job.lock"            # held by the job's own process for as long as it lives
JOB_STATUS = "reel-job-status.json"   # what reel.py make says happened (reel.py --status)
MAKE_LOCK = arrange.HOME / "reel-make.lock"   # one reel made at a time on this computer (her MAKE_LOCK)
SONG_EXTS = (".m4a", ".mp3", ".wav", ".aif", ".aiff", ".aac")   # hers
VIDEO_EXTS = (".mov", ".mp4", ".m4v")                           # hers: a screen recording, whose sound is used
SOUND = " sound"                      # hers: the sound of "<name>.mov" is kept as "<name> sound.m4a" (".wav" on a PC)
SONG_ID = re.compile(r"[0-9a-f]{12}")
JOB_ID = re.compile(r"[0-9a-f]{12}")
HER_KINDS = ("Plan:", "Made", "Wide", "Dry run", "Beats per piece", "Your song is only", "I left out")   # her server.py
SHOWN_MADE = ("Plan", "Wide", "Your song is only", "I left out")     # her page, after a reel is made
LEFT_OUT = ("Your song is only", "I left out")                       # her page shows these in their own box
TEST_OPEN = "ASSISTANT_TEST_OPEN"     # tests only: "front", "behind" or "fail"; no folder is opened, the answer is as if
TEST_CAPCUT = "ASSISTANT_TEST_CAPCUT"  # tests only: set, CapCut is never started and the answer is as if it opened
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

GET_PATHS = ("/reel.html", "/reel-state", "/reel-font", "/reel-job", "/reel-songs")
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

    # her server.py, when Make my reel can't go ahead
    "pick_photos": "Pick a few photos for the reel first.",
    "pick_vibe": "Pick a vibe first.",
    "song_gone": "That song isn't there anymore. Press Add my music and drag it in again.",
    "no_sound": "I couldn't take the sound out of that recording. Try saving the song as an audio file.",
    "went_wrong_make": "Something went wrong making the reel. Ask your assistant to make it instead.",
    "too_long": "That took too long. Ask your assistant to make the reel instead.",

    # her Plan line (bts_reel.py), decision 5: "Plan: 1 clip and 14 photos, 15.2 seconds, every cut on the beat at
    # about 85 beats a minute, starting the song at the top."
    "plan_start": "Plan: ",
    "plan_clip": "{n} clip",
    "plan_clips": "{n} clips",
    "plan_and": " and ",
    "plan_body": ", {secs} seconds, every cut on the beat",
    "plan_tempo": " at about {bpm} beats a minute",
    "plan_top": ", starting the song at the top",
    "plan_in": ", starting the song {s} seconds in",
    "plan_no_song": ", no song",
    "plan_own_sound": " (the footage keeps its own sound).",
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
    # decision 25: her "is open in Finder" line, when the folder opened behind the Claude app (finder.BEHIND_WORDS)
    "behind": "",                                  # filled in below, from finder.behind_words()
    # Make my reel runs on its own now, so the page can be told about a second press or a job that was stopped
    "already_making": "Your reel is already being made. One moment.",
    "interrupted": "Making your reel stopped before it finished. Nothing was made. Press Make my reel again.",
}

def _behind():
    try:
        import finder
        return finder.behind_words()
    except Exception:  # noqa: BLE001  (the words only)
        return f", behind this window. Click {this_computer.FILES_APP} in {this_computer.APP_BAR} to see it."


OUR_WORDS["behind"] = _behind()


def pc_words(s):
    """Her words name Finder; a PC says File Explorer (decision 26). A Mac: exactly hers."""
    return s.replace("Finder", this_computer.FILES_APP) if this_computer.WINDOWS else s


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
        "songs": songs_for_page(kit, rec_kit),
        "music": music_dir(kit).is_dir(),
        "job": job_for_page(kit),
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
    """None (not picked yet), "" (No song), or the id of a song in this shoot right now."""
    if v is None or v == "":
        return v
    if isinstance(v, str) and SONG_ID.fullmatch(v) and v in song_ids(kit):
        return v
    raise Refused("song")


# ---------- step 3: the songs (hers: server.py list_songs and sound_of) ----------

def _reel_module(name):
    """One of the reel scripts (beside these, in assistant-make-a-reel/scripts), loaded without letting them stay at
    the front of Python's search list (posting_queue._capcut's way)."""
    d = str(kit_mod.REEL_PY.parent)
    if d not in sys.path:
        sys.path.append(d)
    saved = list(sys.path)
    try:
        return __import__(name)
    finally:
        sys.path[:] = saved + [x for x in sys.path if x not in saved]


def default_vibe():
    try:
        v = _reel_module("timing").DEFAULT_PACE
        return v if v in VIBES else "beat"
    except Exception:  # noqa: BLE001
        return "beat"


def music_dir(kit):
    return kit / "Music"


def _inside_content(path):
    """Is this file or folder inside Your Content? (Then a sound may be kept beside it, decision 4.)"""
    try:
        import posts
        h = posts.home()
        if not h:
            return False
        content = Path(os.path.realpath(h / posts.CONTENT_NAME))
        return content in Path(os.path.realpath(path)).parents
    except Exception:  # noqa: BLE001
        return False


def song_id(where, name):
    """A song's id: from where it is (Music or Photos) and its file name, never a path, the same on every look."""
    return hashlib.sha1(("%s\0%s" % (where, arrange._nfc(name))).encode("utf-8")).hexdigest()[:12]


def _listing(folder):
    try:
        return [e for e in os.listdir(folder)]
    except OSError:
        return []


def list_songs(kit, rec=None):
    """The songs they put in the shoot's Music folder or its Photos folder, Music first, each folder newest first
    (hers): audio files, and screen recordings whose sound is used. The sound made from a recording is not listed
    on its own (the recording is shown once): beside it, or, for a recording in a Photos folder outside Your
    Content, in the Music folder (decision 4). Links are left out. Each: {id, name, where, kind, path}; the path
    never leaves this computer's own side."""
    rec = rec if rec is not None else kit_mod.load_rec(kit)
    folders = [("Music", music_dir(kit)), ("Photos", kit_mod.photos_dir(kit, rec))]
    videos = {}
    for where, d in folders:
        videos[where] = {Path(f).stem.casefold() for f in _listing(d) if f.lower().endswith(VIDEO_EXTS) and not f.startswith(".")}
    outside = not _inside_content(folders[1][1])
    out = []
    for where, d in folders:
        made_here = set(videos[where])
        if where == "Music" and outside and not SOUND_BESIDE_OUTSIDE:
            made_here |= videos["Photos"]
        found = []
        for f in _listing(d):
            low = f.lower()
            if f.startswith(".") or not low.endswith(SONG_EXTS + VIDEO_EXTS):
                continue
            stem = Path(f).stem
            if low.endswith((SOUND + ".m4a", SOUND + ".wav")) and stem[:-len(SOUND)].casefold() in made_here:
                continue                       # the sound taken from a recording: the recording is shown once
            p = d / f
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                when = p.stat().st_mtime
            except OSError:
                continue
            found.append((-when, f, {"id": song_id(where, f), "name": stem, "where": where,
                                     "kind": "video" if low.endswith(VIDEO_EXTS) else "audio", "path": p}))
        out += [x[2] for x in sorted(found, key=lambda x: (x[0], x[1]))]
    return out


def songs_for_page(kit, rec=None):
    return [{k: s[k] for k in ("id", "name", "where", "kind")} for s in list_songs(kit, rec)]


def song_ids(kit):
    return {s["id"] for s in list_songs(kit)}


def song_by_id(kit, sid, rec=None):
    return next((s for s in list_songs(kit, rec) if s["id"] == sid), None)


def _named(folder, name):
    """The file in folder whose name is this one (capitals aside, as the drive sees it), or None."""
    want = arrange._nfc(name).casefold()
    hit = [e for e in _listing(folder) if arrange._nfc(e).casefold() == want]
    return folder / hit[0] if hit else None


def sound_for(kit, s):
    """The sound of a screen recording (hers: sound_of), made ONCE and never written over: "<name> sound.m4a"
    beside the recording (a PC with no ffmpeg makes "<name> sound.wav"), or, when the recording sits in a Photos
    folder outside Your Content (an export folder the kit only points to), in the kit's own Music folder
    (decision 4), since their folder is never written to. A sound already there is used as it is.
    Returns (path, None) or (None, her plain words)."""
    video = s["path"]
    if s["where"] == "Photos" and not SOUND_BESIDE_OUTSIDE and not _inside_content(video):
        folder = music_dir(kit)
        try:
            folder.mkdir(exist_ok=True)
        except OSError:
            return None, WORDS["no_sound"]
    else:
        folder = video.parent
    for ext in (".m4a", ".wav"):
        have = _named(folder, video.stem + SOUND + ext)
        if have is not None and have.is_file() and not have.is_symlink():
            return have, None
    out = folder / (video.stem + SOUND + ".m4a")
    if this_computer.WINDOWS and this_computer.path_too_long(out):      # unproven on a real PC
        return None, WORDS["no_sound"]
    try:
        got, how = _reel_module("sound").extract_audio(video, out)
    except Exception as e:  # noqa: BLE001
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {e.__class__.__name__}: {str(e)[:200]}")
        return None, WORDS["no_sound"]
    if not got:
        arrange.log(f"reel page: the sound of a recording couldn't be taken: {str(how)[:200]}")
        return None, WORDS["no_sound"]
    return Path(got), None


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
            clean = {}
            for k, v in sent.items():
                if k == "song" and isinstance(v, str) and v and v == stored.get("song"):
                    clean[k] = v           # the song saved before stays as it is, even if its file went a moment ago
                else:
                    clean[k] = SAVE_FIELDS[k](v, kit, on_sheet)
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


# ---------- Make my reel: a job of its own (hers: one long request to bts_reel.py) ----------
# The page asks for a reel (POST /reel-make) and is given a job; a process of its own makes it (reel_page.py job),
# writing how it is going to <kit>/.kit/reel-job.json, which the page reads (GET /reel-job) until it is done. One
# job per shoot at a time; one reel made at a time on this computer (the job waits its turn for MAKE_LOCK, as hers
# waited for her MAKE_LOCK); at most MAKE_LIMIT seconds. Only her kinds of lines reach the page, never a path.

_JOB_ROUTE = threading.Lock()


def job_path(kit):
    return kit / ".kit" / JOB


def job_lock_path(kit):
    return kit / ".kit" / JOB_LOCK


def read_job(kit):
    try:
        j = json.loads(job_path(kit).read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def write_job(kit, j):
    arrange.write_whole(job_path(kit), j)


def job_running(kit):
    """Is a job's process at work on this shoot right now? It holds .kit/reel-job.lock for as long as it lives;
    asking tries to share that lock for an instant (arrange.job_running's way). Where a drive has no locks, the
    job's own process number is asked after instead, for at most MAKE_LIMIT and a minute."""
    try:
        arrange.make_folder(job_lock_path(kit).parent)
        with open(job_lock_path(kit), "a", encoding="utf-8") as f:       # never written to: only looked at
            got = this_computer.try_lock(f, shared=True)
            if got is False:
                return True
            if got:
                this_computer.unlock(f)
                return False
    except OSError:
        pass
    j = read_job(kit) or {}
    if j.get("state") not in ("queued", "running"):
        return False
    return time.time() - float(j.get("t0") or j.get("t") or 0) < MAKE_LIMIT + 60 and arrange._pid_alive(j.get("pid"))


def job_for_page(kit):
    """The newest job as the page sees it: {id, state (queued, running, done, problem), dry, project, words,
    problem, short_song}. A job that says it is at work but is not (stopped, or the computer was turned off) is a
    problem, in plain words. No path, no file name, no process number."""
    j = read_job(kit)
    if not j or not isinstance(j.get("id"), str) or j.get("state") not in ("queued", "running", "done", "problem"):
        return None
    state, problem = j["state"], j.get("problem")
    if state in ("queued", "running") and not job_running(kit):
        if state == "running" or j.get("pid") or time.time() - float(j.get("t") or 0) > JOB_BOOT:
            state, problem = "problem", OUR_WORDS["interrupted"]
    words = [w for w in (j.get("words") or []) if isinstance(w, str)]
    return {"id": j["id"], "state": state, "dry": bool(j.get("dry")), "project": j.get("project") if state == "done" else None,
            "words": words if state == "done" else [], "problem": problem if state == "problem" else None,
            "short_song": bool(j.get("short_song")) and state == "problem"}


def _picks_text(lst):
    return ",".join(f"{x['n']}{x['h']}" for x in lst)


def start_make(body):
    """POST /reel-make: {kit, stamp, picks: [{n, h}], song: an id, "" for No song, vibe, test}. Checked the way a
    save is; then the job is written down and its process started. (status, answer)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "stamp", "picks", "song", "vibe", "test"}:
        return _bad()
    rows = arrange.sheet_rows(kit)
    if not rows:
        return _bad(NOT_READY, 404)
    if body.get("stamp") != arrange.sheet_stamp(kit):
        return _bad(OUR_WORDS["photos_changed"], 409, why="photos")
    on_sheet = {x["n"] for x in rows}
    try:
        picks = _picks(body.get("picks"), on_sheet)
    except Refused:
        return _bad()
    if not picks:
        return _bad(WORDS["pick_photos"])
    if len(picks) > MAX_PICKS:
        return _bad(OUR_WORDS["too_many"], 400, why="many")
    vibe = body.get("vibe")
    if vibe not in VIBES:
        return _bad(WORDS["pick_vibe"])
    song = body.get("song")
    if song is None:
        return _bad(re.sub(r"<[^>]+>", "", WORDS["need_song_html"]), 400, why="song")
    if not isinstance(song, str) or (song and not SONG_ID.fullmatch(song)):
        return _bad()
    if song and song not in song_ids(kit):
        return _bad(WORDS["song_gone"], 400, why="song")
    test = body.get("test", False)
    if type(test) is not bool:
        return _bad()
    with _JOB_ROUTE:
        j = read_job(kit) or {}
        if job_running(kit) or (j.get("state") == "queued" and not j.get("pid") and time.time() - float(j.get("t") or 0) < JOB_BOOT):
            return 409, {"ok": False, "words": OUR_WORDS["already_making"], "why": "making", "job": job_for_page(kit)}
        jid = os.urandom(6).hex()
        write_job(kit, {"id": jid, "state": "queued", "t": time.time(), "dry": test,
                        "ask": {"picks": _picks_text(picks), "song": song, "vibe": vibe, "dry": test,
                                "stamp": body.get("stamp")}})
        try:
            arrange.HOME.mkdir(parents=True, exist_ok=True)
            with open(arrange.LOG, "a", encoding="utf-8") as out:
                # a Mac: start_new_session; a PC: no window, a process group of its own (as the slide job)
                this_computer.popen_detached([sys.executable, str(HERE / "reel_page.py"), "job", str(kit), "--id", jid],
                                             stdout=out, stderr=subprocess.STDOUT, **arrange._child_env())
        except OSError as e:
            arrange.log(f"reel page: the reel's job could not be started: {e}")
            write_job(kit, {"id": jid, "state": "problem", "t": time.time(), "dry": test, "problem": WORDS["went_wrong_make"]})
        return 200, {"ok": True, "job": job_for_page(kit)}


def her_plan_line(p):
    """Her Plan line (bts_reel.py), from the plan's own numbers (decision 5)."""
    w = WORDS
    fill = lambda text, **kw: re.sub(r"\{(\w+)\}", lambda m: str(kw.get(m.group(1), m.group(0))), text)   # noqa: E731
    clips, photos = int(p.get("clips") or 0), int(p.get("photos") or 0)
    what = (fill(w["plan_clip" if clips == 1 else "plan_clips"], n=clips) + w["plan_and"] if clips else "")
    what += fill(w["one_photo" if photos == 1 else "photos"], n=photos)
    line = w["plan_start"] + what + fill(w["plan_body"], secs=f"{float(p.get('length') or 0):.1f}")
    if p.get("song"):
        f = float(p.get("song_from") or 0)
        line += fill(w["plan_tempo"], bpm=round(float(p.get("tempo") or 0)))
        line += (w["plan_top"] if f < 1 else fill(w["plan_in"], s=f"{f:.0f}")) + "."
    else:
        line += w["plan_no_song"] + (w["plan_own_sound"] if clips else ".")
    return line


_PATHISH = re.compile(r"(/[^\s/]+){2,}|~/|[A-Za-z]:[\\/]|\\\\")    # two parts of a path, a home, a drive, a network share


def _no_path(line, known):
    """A line as the page may see it: any path we know of taken back to its last name; a path left after that, and
    the line is not for the page (None)."""
    for k in sorted({str(x) for x in known if x}, key=len, reverse=True):
        if k and k in line:
            line = line.replace(k, Path(k).name)
    line = re.sub(r"\s*\([^()]*[/\\][^()]*\)", "", line)        # "(<a folder>)" said in passing
    return None if _PATHISH.search(line) else line


def _her_lines(out, dry, plan, known):
    """The lines her page shows, from reel.py's words: her server's kinds, then her page's filter."""
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    keep = [w for w in lines if w.startswith(HER_KINDS) or " clip from " in w]
    if dry:
        keep = [w for w in keep if not w.startswith(("Dry run", "Made"))]
    else:
        keep = [w for w in keep if w.startswith(SHOWN_MADE)]
    if PLAN_WORDS == "nicole" and plan:
        keep = [her_plan_line(plan) if w.startswith("Plan:") else w for w in keep]
    return [x for x in (_no_path(w, known) for w in keep) if x]


def _problem(out, known):
    """What stopped reel.py, in its own plain words (hers: the STOP line, or the last plain line)."""
    lines = [w.strip() for w in (out or "").splitlines() if w.strip()]
    stop = next((w for w in lines if w.startswith("STOP")), None) or (lines[-1] if lines else "")
    stop = re.sub(r"^STOP:\s*", "", stop)
    return (_no_path(stop, known) if stop else None) or WORDS["went_wrong_make"]


def _hold_make_lock(deadline):
    """MAKE_LOCK, waited for until deadline: the open file holding it, "none" where locks can't be had (the work
    goes on), or None when the wait ran out."""
    try:
        arrange.HOME.mkdir(parents=True, exist_ok=True)
        f = open(MAKE_LOCK, "a", encoding="utf-8")
    except OSError:
        return "none"
    while True:
        got = this_computer.try_lock(f)
        if got:
            return f
        if got is None:
            f.close()
            return "none"
        if time.time() > deadline:
            f.close()
            return None
        time.sleep(0.25)


def _make(kit, ask, jid, t0):
    """The work of one job. Returns what goes in the job record: {state, words, project, problem, short_song}."""
    rec_kit = kit_mod.load_rec(kit)
    photos = kit_mod.photos_dir(kit, rec_kit)
    short = short_name(kit.name)
    known = [kit, photos]          # paths whose last name means something to them; anything else is never shown
    song, song_name = None, ""
    if ask.get("capcut_song"):
        song_name = ask["capcut_song"]          # Claude's make only (decision 2): CapCut's own music is never on the page
    elif ask.get("song"):
        s = song_by_id(kit, ask["song"], rec_kit)
        if s is None:
            return {"state": "problem", "problem": WORDS["song_gone"]}
        song_name = s["path"].name
        if s["kind"] == "video":
            got, why = sound_for(kit, s)
            if not got:
                return {"state": "problem", "problem": why}
            song = got
        else:
            song = s["path"]
        known += [song]
    reel = _reel_module("reel")
    capcut = _reel_module("capcut")
    picks = ask["picks"]
    with arrange.locked(lock_path(kit)):
        made = load(kit).get("made") or []
    variation = sum(1 for m in made if isinstance(m, dict) and m.get("picks") == picks and m.get("vibe") == ask["vibe"]
                    and m.get("footage") is None)
    # The numbers on the page are the kit's numbered list (.kit/sheet.json); reel.py is handed that same list in
    # its working folder, so a photo exported since can never shift a number to another photo.
    rows = arrange.sheet_rows(kit)
    if not rows or arrange.sheet_stamp(kit) != ask.get("stamp"):
        return {"state": "problem", "problem": OUR_WORDS["photos_changed"]}
    listing = [{"n": x["n"], "file": str(photos / arrange.photo_name(x)), "w": x.get("w") or 0, "h": x.get("h") or 0,
                "way": x.get("way") or ""} for x in rows]
    work = reel.kit_workdir(kit) or reel.workdir(rec_kit.get("name") or short, str(photos))
    arrange.write_whole(work / "photos.json", {"folder": str(photos), "photos": listing})
    status = kit / ".kit" / JOB_STATUS
    arrange.write_whole(status, {"for": jid, "pending": True})
    cmd = [sys.executable, str(kit_mod.REEL_PY), "make", "--folder", str(photos), "--shoot", rec_kit.get("name") or short,
           "--kit", str(kit), "--picks", picks, "--vibe", ask["vibe"],
           *(["--capcut-song", ask["capcut_song"]] if ask.get("capcut_song") else ["--song", str(song) if song else "none"]),
           "--variation", str(variation), "--name", ask.get("name") or reel.kit_reel_name(kit.name, short), "--status", str(status)]
    if ask.get("hook"):
        cmd += ["--hook", ask["hook"]]          # Claude's make only (decision 15): words on the first photo, when they ask
    if song:
        secs = capcut.song_length(str(song)) or 99
        if secs < SHORT_SONG_FROM_TOP:
            cmd += ["--song-start", "0"]            # decision 8: her code starts a short song at the top
    if ask.get("dry"):
        cmd.append("--dry-run")
    left = max(30.0, MAKE_LIMIT - (time.time() - t0))
    try:
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=left,
                           cwd=str(kit_mod.REEL_PY.parent))
    except subprocess.TimeoutExpired:
        return {"state": "problem", "problem": WORDS["too_long"]}
    try:
        st = json.loads(status.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    if st.get("pending") or not isinstance(st, dict):
        st = {}
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    if r.returncode != 0 or not st.get("ok"):
        arrange.log(f"reel page: reel.py stopped ({r.returncode}): {out.strip()[-400:]}")
        return {"state": "problem", "problem": _problem(r.stdout or out, known), "short_song": bool(st.get("short_song"))}
    dry = bool(ask.get("dry"))
    words = _her_lines(r.stdout, dry, st.get("plan"), known)
    project = st.get("project")
    if not dry and project:
        with arrange.locked(lock_path(kit)):
            rec = load(kit)
            rec.setdefault("made", []).append({"project": project, "picks": picks, "vibe": ask["vibe"], "footage": None,
                                               "song": song_name, "song_id": ask.get("song") or "", "when": time.time()})
            save(kit, rec)
        try:                     # the kit's own record of its reel, through its command (kit.json is only theirs to write)
            k = subprocess.run([sys.executable, str(HERE / "kit.py"), "reel-made", str(kit), "--project", project, "--picks", picks],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            if k.returncode != 0:
                arrange.log(f"reel page: kit.py reel-made said: {(k.stdout + k.stderr).strip()[-300:]}")
        except (OSError, subprocess.SubprocessError) as e:
            arrange.log(f"reel page: kit.py reel-made could not run: {e}")
    return {"state": "done", "words": words, "project": project}


def cmd_job(kit, jid):
    """The job's own process (started by the page server). Holds the job's lock for as long as it lives."""
    t0 = time.time()
    arrange._own_output()
    try:
        arrange.make_folder(job_lock_path(kit).parent)
        f = open(job_lock_path(kit), "a", encoding="utf-8")
    except OSError:
        f = None
    got = None
    if f is not None:
        end = time.time() + 3.0                     # a page asking "is it running?" holds it for an instant: wait that out
        while True:
            got = this_computer.try_lock(f)
            if got is not False or time.time() > end:
                break
            time.sleep(0.05)
    if got is False:
        f.close()
        return 0                                    # another job's process has it
    try:
        j = read_job(kit) or {}
        if j.get("id") != jid or j.get("state") != "queued":
            return 0
        ask = j.get("ask") or {}
        j.update(pid=os.getpid(), t0=t0, t=time.time())
        write_job(kit, j)
        g = _hold_make_lock(t0 + MAKE_LIMIT)
        if g is None:
            j.update(state="problem", problem=WORDS["too_long"], t=time.time())
            write_job(kit, j)
            return 1
        try:
            j.update(state="running", t=time.time())
            write_job(kit, j)
            try:
                res = _make(kit, ask, jid, t0)
            except Exception as e:  # noqa: BLE001  (whatever happens, the page is told in plain words)
                arrange.log(f"reel page: the reel's job failed: {e.__class__.__name__}: {str(e)[:300]}")
                res = {"state": "problem", "problem": WORDS["went_wrong_make"]}
            j.update(res, t=time.time())
            write_job(kit, j)
        finally:
            if g != "none":
                this_computer.unlock(g)
                g.close()
        return 0 if j.get("state") == "done" else 1
    finally:
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


# ---------- the folder buttons and Open CapCut ----------

def _open_folder(path):
    """finder.open_folder, or, in a test (TEST_OPEN), nothing opened and the answer as if it had been."""
    t = os.environ.get(TEST_OPEN)
    if t:
        arrange.log(f"reel page (test): would open {Path(path).name}")
        return (t != "fail"), ("behind" if t == "behind" else "" if t != "fail" else "test")
    import finder
    return finder.open_folder(path)


def open_music(body):
    """POST /reel-open {kit, what: "music"}: makes <kit>/Music if it isn't there, and opens it (hers)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit", "what"} or body.get("what") != "music":
        return _bad()
    d = music_dir(kit)
    try:
        d.mkdir(exist_ok=True)               # the kit's own folder is there (kit_by_name): only Music is ever made
    except OSError:
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    ok, note = _open_folder(d)
    if not ok:
        arrange.log(f"reel page: the Music folder couldn't be opened: {str(note)[:200]}")
        return 200, {"ok": False, "words": WORDS["cant_open"]}
    w = pc_words(WORDS["music_open"])
    if note == "behind":
        first, rest = w.split(". ", 1)
        w = first + OUR_WORDS["behind"] + " " + rest
    return 200, {"ok": True, "words": w}


def open_capcut_for_page(body):
    """POST /reel-capcut {kit}: starts CapCut (posting_queue.open_capcut, through capcut.py's own open) and says
    her words (decision 24, capcut.OPEN_WORDS)."""
    kit = arrange.kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    if set(body) - {"kit"}:
        return _bad()
    with arrange.locked(lock_path(kit)):
        made = [m for m in (load(kit).get("made") or []) if isinstance(m, dict) and m.get("project")]
    project = made[-1]["project"] if made else (kit_mod.load_rec(kit).get("reel") or {}).get("project")
    words = _reel_module("capcut").OPEN_WORDS
    if os.environ.get(TEST_CAPCUT):
        arrange.log("reel page (test): would open CapCut")
        return 200, {"ok": True, "words": words}
    import posting_queue
    ok, said = posting_queue.open_capcut({"reel": {"project": project}} if project else {}, ok_words=words)
    return 200, {"ok": bool(ok), "words": said}


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


def _get_job_or_songs(handler, path, q):
    """GET /reel-songs?kit=: the shoot's songs (ids and names only); GET /reel-job?kit=&id=: how Make my reel is going."""
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 403)
    kit = arrange.kit_by_name(_one(q, "kit"))
    if kit is None:
        return arrange._send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    if path == "/reel-songs":
        return arrange._send_json(handler, {"ok": True, "music": music_dir(kit).is_dir(), "songs": songs_for_page(kit)})
    jid = _one(q, "id")
    if jid and not JOB_ID.fullmatch(jid):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
    job = job_for_page(kit)
    if job is None or (jid and job["id"] != jid):
        return arrange._send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD, "job": job}, 404)
    arrange._send_json(handler, {"ok": True, "job": job})


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
        if path in ("/reel-job", "/reel-songs"):
            return _get_job_or_songs(handler, path, q)
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
        route = {"/reel-save": save_from_page, "/reel-make": start_make, "/reel-open": open_music,
                 "/reel-capcut": open_capcut_for_page}.get(path)
        if route is None:
            return arrange._send_json(handler, {"ok": False, "words": NOT_YET}, 404)
        code, out = route(body)
        return arrange._send_json(handler, out, code)
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


def _song_section(w, num):
    e = html.escape
    return (
        "<section class='step' id='step3'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["song_h2"]) + "</h2>"
        "<p class='say'>" + e(w["song_say1"]) + "</p>"
        "<p class='say'>" + w["song_say2_html"] + "</p>"
        "<button class='btn main' id='addMusic' type='button'>" + e(w["add_music"]) + "</button>"
        "<p class='waiting' id='waiting'></p>"
        "<div class='songs' id='songs'></div>"
        "<p class='note'>" + w["licence_html"] + "</p>"
        "</section>")


def _vibe_section(w, num):
    e = html.escape
    rec = default_vibe()
    cards = "".join(
        "<button class='opt' type='button' data-vibe='" + v + "'><b>" + e(w["vibe_%s_b" % v])
        + ("<span class='rec'>" + e(w["vibe_rec"]) + "</span>" if v == rec else "") + "</b>"
        "<span>" + e(w["vibe_%s_s" % v]) + "</span></button>" for v in VIBES)
    return (
        "<section class='step' id='step4'>"
        "<h2><span class='num'>" + str(num) + "</span>" + e(w["vibe_h2"]) + "</h2>"
        "<p class='say'>" + e(w["vibe_say"]) + "</p>"
        "<div class='vibes' id='vibes'>" + cards + "</div>"
        "</section>")


SECTIONS = [
    ("step0", None),            # 1. Behind-the-scenes footage? (stage b)
    ("step1", _order_section),  # 2. Put your photos in order
    ("step3", _song_section),   # 3. Add your song
    ("stepStyle", None),        # 4. What style of behind the scenes is this? (stage b2)
    ("step4", _vibe_section),   # 5. Pick the vibe
]


def _json_for_script(obj):
    """JSON that is safe inside a <script> element (no "</script>", no "<!--")."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page_html(kit_name, short, kit_page=False):
    e = html.escape
    w = {k: pc_words(v) for k, v in WORDS.items()}
    title = w["reel_of"].replace("{short}", short)
    data = {"words": dict(w, **OUR_WORDS), "max": MAX_PICKS, "dragOut": DRAG_OUT, "undoSteps": UNDO_STEPS,
            "saveAfter": SAVE_AFTER_MS, "followEvery": FOLLOW_MS, "defaultVibe": default_vibe(),
            "songEvery": SONG_EVERY_MS, "jobEvery": JOB_EVERY_MS}
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
        "<div class='make'><div class='in'><div class='sum' id='sum'></div>"
        "<button class='btn main' id='makeBtn' type='button'>" + e(w["make"]) + "</button></div></div>"
        "<div class='lb' id='lb'><img id='lbimg' alt=''></div>"
        "<script type='application/json' id='reelData'>" + _json_for_script(data) + "</script>"
        "<script>" + DRAG_JS + "</script><script>" + MODEL_JS + "</script><script>" + CORE_JS + "</script>"
        "<script>" + ORDER_JS + "</script><script>" + SONG_JS + "</script><script>" + VIBE_JS + "</script>"
        "<script>" + MAKE_JS + "</script><script>" + START_JS + "</script>"
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
    var out = $('result'); if (out && out.classList.contains('bad')) out.className = 'result';   // hers: they changed something, the old problem no longer applies
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
    // a POST of the page's own (arrange.guard checks it): {code, j}; a server that gave no answer throws
    post: function(url, obj){
      return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(obj)})
        .then(function(r){ if (r.status >= 500) throw new Error('no answer'); return r.json().then(function(j){ return {code: r.status, j: j}; }); });
    },
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
    if (R.changed) R.changed();                 // the bar at the bottom (hers: summary())
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
  R.order = function(){ return M.copy(reel); };
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

# Step 3, her "Add your song": the songs in the shoot's Music and Photos folders, by id; No song; a new file is
# picked by itself.
SONG_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var songs = [], seen = null, song = null;          // song: null (not picked yet), '' (No song), or a song's id
  R.song = function(){ return song; };
  R.songName = function(){ var s = songs.filter(function(x){ return x.id === song; })[0]; return s ? s.name : ''; };
  function renderSongs(){
    var box = $('songs');
    var list = songs.map(function(s){
      var on = song === s.id;
      var what = s.kind === 'video' ? W.song_recording : W.song_song;
      var where = s.where === 'Music' ? W.song_in_music : W.song_in_photos;
      return '<button class="song ' + (on ? 'on' : '') + '" type="button" data-id="' + esc(s.id) + '"><span class="ic">' +
        (s.kind === 'video' ? '&#9654;' : '&#9835;') + '</span><span><b>' + esc(s.name) + '</b><small>' + esc(what) + ', ' + esc(where) + '</small></span></button>';
    }).join('');
    box.innerHTML = list + '<button class="song none ' + (song === '' ? 'on' : '') + '" type="button" data-id=""><span class="ic">&ndash;</span><span><b>' +
      esc(W.no_song_b) + '</b><small>' + esc(W.no_song_s) + '</small></span></button>';
    box.querySelectorAll('.song').forEach(function(b){ b.onclick = function(){ song = b.dataset.id; renderSongs(); R.save(); if (R.changed) R.changed(); }; });
    $('step3').classList.toggle('done', song !== null);
  }
  // hers (loadSongs): a file that wasn't there on the last look is picked by itself
  function take(list){
    var fresh = seen ? list.filter(function(s){ return !seen[s.id]; }) : [];
    songs = list; seen = {}; list.forEach(function(s){ seen[s.id] = true; });
    if (fresh.length) { song = fresh[0].id; R.save(); $('waiting').textContent = R.fill(W.got_it, {name: fresh[0].name}); }
    if (song && !songs.some(function(s){ return s.id === song; })) song = null;
    renderSongs(); if (R.changed) R.changed();
  }
  function loadSongs(){
    return fetch('/reel-songs?' + R.q, {cache: 'no-store'}).then(function(r){ return r.json(); })
      .then(function(j){ if (j && j.ok && Array.isArray(j.songs)) take(j.songs); }).catch(function(){});
  }
  $('addMusic').onclick = function(){
    $('waiting').textContent = W.opening_music;
    R.post('/reel-open', {kit: R.kit, what: 'music'}).then(function(res){
      $('waiting').textContent = (res.j && res.j.words) || W.cant_open;
      loadSongs();
    }).catch(function(){ $('waiting').textContent = W.cant_open; });
  };
  setInterval(function(){ if (!document.hidden && R.state()) loadSongs(); }, R.data.songEvery);
  R.part({
    fields: function(){ return {song: song}; },
    adopt: function(st, first){
      var sv = st.saved || {};
      song = (sv.song === undefined || sv.song === null) ? null : sv.song;
      if (first) seen = null;
      take(st.songs || []);
    }
  });
})();
"""

# Step 5, her "Pick the vibe".
VIBE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, $ = R.$, vibe = R.data.defaultVibe;
  var cards = document.querySelectorAll('#vibes .opt');
  R.vibe = function(){ return vibe; };
  function renderVibes(){
    cards.forEach(function(b){ b.classList.toggle('on', b.dataset.vibe === vibe); });
    $('step4').classList.add('done');
  }
  cards.forEach(function(b){ b.onclick = function(){ vibe = b.dataset.vibe; renderVibes(); R.save(); if (R.changed) R.changed(); }; });
  R.part({
    fields: function(){ return {vibe: vibe}; },
    adopt: function(st){ var sv = st.saved || {}; vibe = sv.vibe || R.data.defaultVibe; renderVibes(); }
  });
  renderVibes();
})();
"""

# The bar at the bottom and Make my reel: hers, with the reel made by a job of its own that the page asks after.
# A later step adds to it through R.sumExtra() (words after the photo count, hers: " + 1 clip · Moment first"),
# R.beforeMake() (a reason not to make yet: {h3, html}) and R.makeExtra() (more for the request).
MAKE_JS = r"""
(function(){
  'use strict';
  var R = window.Reel, W = R.words, $ = R.$, esc = R.esc;
  var TEST = new URLSearchParams(location.search).get('test') === '1';      // hers: plans the reel, makes nothing in CapCut
  var VIBE_WORDS = {beat: W.vibe_word_beat, mixed: W.vibe_word_mixed, calm: W.vibe_word_calm, build: W.vibe_word_build};
  var making = false, jobId = null, pollT = null, fails = 0;
  var btn = $('makeBtn'), out = $('result');
  if (TEST) btn.textContent = W.make_test;
  function summary(){
    if (!R.order || !R.song || !R.vibe) return;
    var n = R.order().length, s = R.song(), name = R.songName();
    var songW = s === null ? W.sum_no_song_yet : s === '' ? W.sum_no_song : (name ? esc(name) : W.sum_no_song_yet);
    var ft = R.sumExtra ? R.sumExtra() : '';
    $('sum').innerHTML = '<b>' + esc(R.fill(n === 1 ? W.one_photo : W.photos, {n: n})) + ft + '</b> · ' + songW + ' · ' + esc(VIBE_WORDS[R.vibe()] || '');
    if (!making) btn.disabled = !n;
  }
  R.changed = summary;
  function busy(on){
    making = on;
    if (on) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> ' + esc(W.making); }
    else { btn.textContent = TEST ? W.make_test : W.make; btn.disabled = !(R.order && R.order().length); }
  }
  function into_view(){ out.scrollIntoView({behavior: 'smooth', block: 'center'}); }
  function bad(h3, html){ out.className = 'result on bad'; out.innerHTML = '<h3>' + esc(h3) + '</h3><p>' + html + '</p>'; into_view(); }
  function lines(words){
    return (words || []).map(function(w){ return '<p' + (/^(Your song is only|I left out)/.test(w) ? ' class="leftout"' : '') + '>' + esc(w) + '</p>'; }).join('');
  }
  function show(job){
    clearTimeout(pollT); pollT = null; jobId = null; busy(false);
    if (job.state === 'problem') {
      var p = job.problem || W.went_wrong;
      out.className = 'result on bad';
      out.innerHTML = job.short_song
        ? '<h3>' + esc(W.short_h3) + '</h3><p>' + esc(p) + '</p>' + (/longer song/.test(p) ? '' : '<p>' + W.short_more_html + '</p>')
        : '<h3>' + esc(W.didnt_work_h3) + '</h3><p>' + esc(p) + '</p>';
    } else if (job.dry) {
      out.className = 'result on';
      out.innerHTML = '<h3>' + esc(W.test_h3) + '</h3>' + lines(job.words);
    } else {
      var back = $('back');
      out.className = 'result on';
      out.innerHTML = '<h3>' + esc(R.fill(W.in_capcut_h3, {project: job.project || W.new_reel})) + '</h3>' + lines(job.words) +
        '<p>' + esc(W.open_capcut_say) + '</p><div class="acts"><button class="btn main" id="capcut" type="button">' + esc(W.open_capcut) +
        '</button><a class="btn" id="resultBack" href="' + esc(back.getAttribute('href')) + '">' + esc($('backWords').textContent) + '</a></div><p class="went" id="went"></p>';
      $('capcut').onclick = function(){
        R.post('/reel-capcut', {kit: R.kit}).then(function(res){ $('went').textContent = (res.j && res.j.words) || ''; }).catch(function(){});
      };
    }
    into_view();
  }
  function poll(){
    pollT = null;
    if (!jobId) return;
    fetch('/reel-job?' + R.q + '&id=' + encodeURIComponent(jobId), {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        fails = 0;
        var job = j && j.job;
        if (!job || job.id !== jobId) { show({state: 'problem', problem: W.interrupted}); return; }
        if (job.state === 'done' || job.state === 'problem') { show(job); return; }
        pollT = setTimeout(poll, R.data.jobEvery);
      })
      .catch(function(){
        if (++fails > 40) { show({state: 'problem', problem: W.no_server}); return; }
        pollT = setTimeout(poll, R.data.jobEvery * 2);
      });
  }
  function follow(job){
    if (job.state === 'done' || job.state === 'problem') { show(job); return; }
    jobId = job.id; busy(true);
    out.className = 'result on'; out.innerHTML = '<p>' + esc(W.finding_beat) + '</p>';
    clearTimeout(pollT); pollT = setTimeout(poll, R.data.jobEvery);
  }
  btn.onclick = function(){
    if (making) return;
    if (R.song() === null) { bad(W.need_song_h3, W.need_song_html); return; }
    var stop = R.beforeMake ? R.beforeMake() : null;
    if (stop) { bad(stop.h3, stop.html); return; }
    busy(true);
    out.className = 'result on'; out.innerHTML = '<p>' + esc(W.finding_beat) + '</p>';
    var st = R.state() || {}, extra = R.makeExtra ? R.makeExtra() : {};
    var body = {kit: R.kit, stamp: st.stamp, picks: R.order(), song: R.song(), vibe: R.vibe(), test: TEST};
    for (var k in extra) body[k] = extra[k];
    R.post('/reel-make', body).then(function(res){
      var j = res.j || {};
      if (j.job) { follow(j.job); return; }             // started, or already being made: that one is followed
      busy(false); bad(W.didnt_work_h3, esc(j.words || W.went_wrong));
    }).catch(function(){ busy(false); bad(W.didnt_work_h3, esc(W.no_server)); });
  };
  R.part({
    adopt: function(st, first){
      var job = st.job;
      if (first && job && (job.state === 'queued' || job.state === 'running') && !making) follow(job);   // reloaded while one is at work
      summary();
    }
  });
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
    sid = saved.get("song")
    if sid is None:
        say("  Song: not picked on the page yet")
    elif sid == "":
        say("  Song: No song (they'll add music in Instagram)")
    else:
        s = song_by_id(kit, sid)
        say(f"  Song: {s['path'].name} ({'a screen recording, its sound' if s['kind'] == 'video' else 'a song'}, in the {s['where']} folder)"
            if s else "  Song: the one they picked is not there anymore")
    vibe = saved.get("vibe")
    say(f"  Vibe: {WORDS['vibe_' + vibe + '_b'] if vibe in VIBES else 'not picked on the page yet'}"
        + ("" if vibe in VIBES else f" (Make my reel would use {WORDS['vibe_' + default_vibe() + '_b']})"))
    made = [m for m in (load(kit).get("made") or []) if isinstance(m, dict)]
    if made:
        say(f"  Reels made from the page: {len(made)}, the newest \"{made[-1].get('project')}\"")
    say(f"  Saved {st['rev']} time{'s' if st['rev'] != 1 else ''}")
    return 0


def cmd_make(kit, a):
    """Claude's own Make my reel (see the top of this file): what the page would hand reel.py, made the same way,
    one reel at a time on this computer. A song comes from the page, unless they asked for CapCut's own music."""
    st = state(kit)
    if st is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was made.")
        return 1
    saved = st["saved"] or {}
    picks = current_picks(kit)
    if not picks:
        say("STOP: there's no order for this reel yet: pick the photos first (kit.py picks --reel), or they put them in order on the page.")
        return 1
    if len([x for x in picks.split(",") if x]) > MAX_PICKS:
        say("STOP: " + OUR_WORDS["too_many"])
        return 1
    vibe = saved.get("vibe") if saved.get("vibe") in VIBES else default_vibe()
    ask = {"picks": picks, "vibe": vibe, "dry": bool(a.dry_run), "stamp": st["stamp"]}
    if a.capcut_song:
        ask["capcut_song"] = a.capcut_song
    elif a.no_song or saved.get("song") == "":
        ask["song"] = ""
    elif saved.get("song"):
        if song_by_id(kit, saved["song"]) is None:
            say("STOP: " + WORDS["song_gone"])
            return 1
        ask["song"] = saved["song"]
    else:
        say("STOP: no song is picked on the page yet. The song is theirs to pick there (Add my music, or No song); pass --no-song only when they have said no song.")
        return 1
    if a.hook:
        ask["hook"] = a.hook
    if a.name:
        ask["name"] = a.name
    t0 = time.time()
    g = _hold_make_lock(t0 + MAKE_LIMIT)
    if g is None:
        say("STOP: another reel is still being made on this computer. Try again in a moment.")
        return 2
    try:
        res = _make(kit, ask, "chat" + os.urandom(4).hex(), t0)
    finally:
        if g != "none":
            this_computer.unlock(g)
            g.close()
    if res.get("state") != "done":
        say("STOP: " + str(res.get("problem") or WORDS["went_wrong_make"]))
        return 1
    for w in res.get("words") or []:
        say(w)
    if not a.dry_run and res.get("project"):
        say(f"Made: {res['project']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open").add_argument("words")
    sub.add_parser("show").add_argument("words")
    m = sub.add_parser("make", help="Claude's own Make my reel: the page's order, song and vibe")
    m.add_argument("words")
    m.add_argument("--capcut-song", help="a song from CapCut's music (only when they asked for it, after the licence note)")
    m.add_argument("--hook", help="words on the first photo, when they asked for them")
    m.add_argument("--name", help="another name for the CapCut project (a second take)")
    m.add_argument("--no-song", action="store_true", help="no song, whatever the page has")
    m.add_argument("--dry-run", action="store_true")
    j = sub.add_parser("job", help="(the page server's own) make the reel a page asked for")
    j.add_argument("kit")
    j.add_argument("--id", required=True)
    a = ap.parse_args()
    if a.cmd == "job":
        kit = Path(a.kit)
        if not (kit / ".kit" / "kit.json").is_file() or not JOB_ID.fullmatch(a.id):
            return 2
        return cmd_job(kit, a.id)
    import fresh
    fresh.announce()
    kit = kit_mod.find_kit(a.words)
    try:
        if a.cmd == "open":
            return cmd_open(kit)
        if a.cmd == "make":
            return cmd_make(kit, a)
        return cmd_show(kit)
    except arrange.Busy:
        say("STOP: this shoot's reel page is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
