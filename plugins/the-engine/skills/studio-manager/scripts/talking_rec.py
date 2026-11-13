#!/usr/bin/env python3
"""A talking-to-camera reel's record, and the assistant's side of it in the chat (Nicole's handoffs v23 and v24,
Nov 11 and 12, built our way).

They record themselves talking about a shoot, as messy as they like, and drag the video into the shoot's Talking
folder. The page turns it into a script; the assistant cuts the script like an editor, and places the photos if
they ask. Nothing here writes a word of theirs: every command prints Nicole's rules again so they are never
skipped.

When they paste "Cut my talking reel for <shoot>":
    python3 talking_rec.py show  "<shoot>"                 the rules, then every word numbered, by sentence
    python3 talking_rec.py cut   "<shoot>" --file cuts.json [--replace]
        cuts.json: {"cut": [[first word, last word], ...], "why": ["the warm-up", "a restart", ...]}
        Their own cuts on the page are never replaced without asking them first (then --replace).

When they paste "Place the photos in my talking reel for <shoot>" (or "Cut my talking reel and place the photos
for <shoot>": cut first, then this):
    python3 talking_rec.py photos "<shoot>"                the photo rules, the kept words by sentence, and how to
                                                           see the photos (the numbered sheet: the page's numbers)
    python3 talking_rec.py place  "<shoot>" --file shots.json [--replace]
        shots.json: {"shots": [{"a": first word, "b": last word, "ns": [photo numbers, flashing in this order],
                                "spot": "pip" | "full" | "center" | "corner"}, ...]}

    python3 talking_rec.py status "<shoot>"                where this shoot's talking reel stands, in a few lines

When they say "set up talking reels" (the page tells them to when a Mac needs it):
    python3 talking_rec.py setup --check                   where turning talking into words stands on this computer:
                                                           Apple's tools, the small app that listens, and what the
                                                           Mac last said about Speech Recognition. Sets nothing up.
    python3 talking_rec.py setup                           the same, then the first-time setup. If Apple's tools are
                                                           missing it says so and stops: `xcode-select --install`
                                                           opens Apple's own install window, so only with their yes.

Make it in CapCut on the page (start_make(), then `talking_rec.py make-job`, the Assistant's own command) runs
assistant-make-a-reel/scripts/talking_make.py in a job of its own, as Make my reel does: see "Make it in CapCut"
below. make_for_page() is what the page asks after.

Edit my video on the page (start(), then `talking_rec.py job`, the Assistant's own command) turns the video into
words in a job of its own: see "turning a video into words" below. The Mac's own Speech Recognition route first
ran on Nov 12, 2026 (Dustin's Mac, macOS 27.2, two real videos, the first 25 seconds and 60 words, the Allow answer
only; the Mac did not ask again for the second); every test still uses the pretend transcriber.

<shoot> is the name as the page wrote it in the line they pasted, or a few words of it. Write the two files in
the scratchpad, never in their folders, and hand them over with --file (never on the command line).

Where things are kept, all in the kit's hidden folder (nothing of theirs is in the computer's own Assistant folder;
only the transcriber's own app, when it has one, and the scratch sound of a job at work, in <that folder>/talking/,
the sound removed when the job ends):
    .kit/talking.json            the record: which video, their cuts, splits, speeds, zooms, photo stretches,
                                 captions. Her field names. Saved whole or not at all, one writer at a time
                                 (.kit/talking.lock), with a counter ("rev") that moves on with every change.
    .kit/talking.prev.json       the record as it was before the last change
    .kit/talking-words.json      every word they said with its times, the sentences and the video's facts, for
                                 each video that was turned into a script. Written once per video, never by a
                                 save from the page, so every save stays small (a 30-minute talk is about 4,500
                                 words).
    .kit/talking-job.json        the newest job that turned a video into words (its state, which video);
                                 .kit/talking-job.lock is held by that job's process for as long as it lives
    .kit/talking/<key>/preview.mp4   the small copy of a talking video the page plays (540 on its short side),
                                 made once per video and kept; .kit/talking/facts.json the videos' facts
    .kit/talking-make-job.json   the newest Make it in CapCut from the page (its state, its one line);
                                 .kit/talking-make-job.lock is held by that job's process for as long as it
                                 lives; .kit/talking-make-status.json is what the maker said happened, and
                                 .kit/talking-make.json the plan it last handed to CapCut's writer (all four
                                 the Assistant's own working files, each replaced by the next make)
    a record that was read and is not a record (damaged) is set aside as talking.damaged-<date>-<time>.json,
    never written over. A record that is there and would not be READ just now (a drive that hiccuped, another
    program holding it) is left exactly where it is: every command and save says "try again", nothing is moved.

Two small things of ours in the record: "words_of", the mark of the script its edit was made on (so an edit is
never left on another script's word numbers when a job is cut off between its two saves), and "shot_keys",
which Footage video each key the page has sent belongs to (a file's key changes when it is exported again).

The edit of each video is its own: choosing another video in the Talking folder keeps this one's cuts and
photos in the record ("earlier") and brings them back when they come back to it. What a --replace replaces is
kept too ("replaced", the last 12).

Exit: 0 done, 1 a problem with the kit, 2 STOP (nothing was saved).

A Mac and a PC: every file is read and written as UTF-8. The record and the chat's commands need no Mac. Turning
a video into words does (a named gap): on a PC, Edit my video answers this_computer.NO_TALKING_PC at once and makes
nothing.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer   # noqa: E402
import arrange         # noqa: E402
import fresh           # noqa: E402
import kit as kitmod   # noqa: E402
import posts           # noqa: E402
import reel_page       # noqa: E402

TALKING = "Talking"                       # hers: <shoot>/Talking, beside Photos, Footage and Music
RECORD, PREV, LOCK = "talking.json", "talking.prev.json", "talking.lock"
WORDS_FILE, WORDS_PREV = "talking-words.json", "talking-words.prev.json"
JOB_LOCK = "talking-job.lock"             # held by the job that turns a video into words, for as long as it lives
LOCK_WAIT = 10.0
LOG = fresh.LOGS / "talking.log"          # the real words of anything that went wrong; never shown on a page

# What is kept beside the record, per video, and joined back on when the record is read (her shape for the page).
WORD_FIELDS = ("words", "sentences", "info", "transcribed", "video_key", "how", "ondevice")
# Everything that counts in word numbers: it belongs to one video's script and to no other.
EDIT_FIELDS = ("cut", "claude_cut", "claude_why", "splits", "speeds", "zooms", "shots", "moves", "photos", "claude_shots",
               "claude_placed")
KEPT_WHEN_REPLACED = ("cut", "shots", "zooms", "splits", "speeds")
MADE_AGAIN = "made-again"                 # in "earlier": this video's words were made again while the record was on another
REPLACED_KEPT = 12                        # as kit.py picks --reel keeps reel_earlier

# hers (server.py /talking/save), each in one place
MAX_CUTS, MAX_SPLITS, MAX_RANGES, MAX_SHOTS, MAX_NS = 2000, 500, 500, 500, 30
PAGE_SPEEDS = (1.25, 1.5, 2.0)            # a speed of 1 is "no speed-up": dropped, as hers
WHY_MOST, WHY_LONG = 20, 120              # hers: up to 20 reasons, 120 characters each
PLACE_SPOTS = ("pip", "full", "center", "corner")     # hers, in her order (talking.py place)
KEY = reel_page.KEY
PAGE_ID = arrange.PAGE_ID
REV_CHECK = True                          # a save from a page that hadn't seen the newest record is refused (reel_page's rule)

NOT_UNDERSTOOD = arrange.NOT_UNDERSTOOD
NEWER = "This was changed somewhere else. Here's the newest."       # ours (hers has no such state): for Nicole to reword
BUSY = "Something else is saving this shoot's talking reel right now. Try again in a moment."      # ours
# ours: the record (or the drive it is on) would not be read or written just now. Nothing was changed.
TROUBLE = "I couldn't get to this shoot's talking reel just now. Nothing was changed. Try again in a moment."
SHOT_KEYS_KEPT = 200                      # the keys last handed to the page for Footage videos, so a save can still name them
FAR = 10 ** 9                             # no number the page sends (a second, a part of the screen, a size) is ever larger

# Hers, word for word (talking.py): what the commands say.
NO_SCRIPT_SHOW = "there's no script for this shoot yet: on the page, add their video and press Edit my video"
NO_SCRIPT = "no script yet"
NO_SCRIPT_MAKE = "Turn your video into a script first."       # hers (server.py make_talking)
THEIR_CUTS = "they've already made their own cuts on the page. Ask before replacing them (then run again with --replace)"
THEIR_PHOTOS = "they already have photos placed. Ask before replacing them (then run again with --replace)"
PHOTOS_PLACED = "They already have photos placed: ask before replacing them (then place with --replace)."
EXPORTED_AGAIN = ("NOTE: their talking video was exported again since this script was made, so these word times belong to "
                  "the old file. Ask them to press Edit my video again on the page before you cut")     # show and photos end with it


def _engine():
    return reel_page._reel_module("talking")


def say(msg):
    kitmod.say(msg)


def log(msg):
    """One line in the Assistant's own log (never a page, never the chat)."""
    try:
        fresh.LOGS.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg).replace("\n", " / ") + "\n")
    except OSError:
        pass


class Stop(Exception):
    """Something in what was handed over can't be saved; nothing was written."""


class Busy(Exception):
    """Another program kept the record for longer than LOCK_WAIT."""


class Refused(Exception):
    """A field the page sent isn't one it could have sent."""


class Unreadable(Exception):
    """The record is there and the computer would not let it be read just now (a drive that hiccuped, a file
    another program holds, no permission). It is NOT a damaged record: nothing is moved, nothing is written."""


def _rev(d):
    """The record's counter: a whole number from 0 up (anything else in a record reads as 0)."""
    v = d.get("rev") if isinstance(d, dict) else None
    return v if type(v) is int and v >= 0 else 0


def _lst(rec, key):
    """A field that should be a list: the list, or an empty one when the record holds anything else there."""
    v = rec.get(key) if isinstance(rec, dict) else None
    return v if isinstance(v, list) else []


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def short_name(kit):
    """Hers: the shoot's folder name without a leading date (the name in the page's title and its chat lines)."""
    return reel_page.short_name(Path(kit).name)


def find(words):
    """The kit for the name in a pasted chat line. The page writes the shoot's short name ("Hannah" for
    "2026-09-23 Hannah"); when exactly one shoot has that short name it is that one, even if another shoot's
    name holds the same words. Otherwise a few words find it, as for every other command (kit.find_kit)."""
    p = Path(words)
    if not (p.is_dir() and (p / ".kit").is_dir()):
        try:
            h = posts.home()
            content = h / posts.CONTENT_NAME if h else None
            if content is not None and content.is_dir():
                want = _nfc(words).strip().casefold()
                hits = [d for d in content.iterdir() if d.is_dir() and not d.name.startswith(".") and (d / ".kit").is_dir()
                        and _nfc(reel_page.short_name(d.name)).strip().casefold() == want]
                if len(hits) == 1:
                    return hits[0]
        except OSError:
            pass
    return kitmod.find_kit(words)


# ---------- the record ----------

def record_path(kit):
    return Path(kit) / ".kit" / RECORD


def words_path(kit):
    return Path(kit) / ".kit" / WORDS_FILE


def _read_json(p):
    """(what the file holds, was it there). (None, True) for a file that WAS read and is not a record (not JSON,
    not UTF-8, not an object): that one is damaged, and the next change sets it aside. A file that is there and
    could not be read at all raises Unreadable: it may be perfectly good, so nothing may be done to it."""
    try:
        raw = Path(p).read_bytes()
    except FileNotFoundError:
        return None, False
    except OSError as e:
        log(f"{Path(p).parent.parent.name}: {Path(p).name} could not be read just now ({e.__class__.__name__}: {e})")
        raise Unreadable(TROUBLE)
    try:
        d = json.loads(raw.decode("utf-8"))
    except ValueError:                                     # not UTF-8 (UnicodeDecodeError is one) or not JSON
        return None, True
    return (d if isinstance(d, dict) else None), True


def _slim(kit):
    """The record as it is on the drive (no words), or a new one."""
    d, _ = _read_json(record_path(kit))
    return d if d is not None else {"v": 1}


def _words_file(kit):
    d, _ = _read_json(words_path(kit))
    if d is None or not isinstance(d.get("videos"), dict):
        return {"v": 1, "videos": {}}
    return d


def words_for(kit, video, wf=None):
    """What was kept when `video` (a file name) was turned into a script, or None."""
    if not isinstance(video, str) or not video:
        return None
    got = (wf or _words_file(kit))["videos"].get(video)
    return got if isinstance(got, dict) and isinstance(got.get("words"), list) else None


def words_id(key, words):
    """A short mark of one script: the video's key as it was when the words were made, and the words themselves.
    The record keeps it ("words_of") so an edit is never left sitting on another script's word numbers."""
    raw = json.dumps([key, words], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _entry_id(entry):
    if not isinstance(entry, dict):
        return None
    got = entry.get("id")
    return got if isinstance(got, str) and got else words_id(entry.get("key"), entry.get("words"))


def _stale_edit(rec, entry, why):
    """Does the record's edit belong to a script other than the one its video has now? (The words were made
    again and the record never heard: a job cut off between its two saves.) Then the edit starts afresh, what
    was there kept in "replaced". A record with no mark yet is left alone. True when the edit was started afresh."""
    eid = _entry_id(entry)
    was = rec.get("words_of")
    if eid is None or was is None or was == eid:
        return False
    fresh_edit(rec, why)
    rec["words_of"] = eid
    return True


def _join(rec, kept):
    """The record with its video's words joined on, in her shape."""
    for k in WORD_FIELDS:
        rec.pop(k, None)
    rec["words"], rec["sentences"] = [], []
    if kept:
        rec["words"] = kept.get("words") or []
        rec["sentences"] = kept.get("sentences") or []
        for k in ("info", "transcribed", "how", "ondevice"):
            if k in kept:
                rec[k] = kept[k]
        rec["video_key"] = kept.get("key")
    return rec


def load(kit):
    """The kit's talking record with the words of its video, as hers held it in one file. A new, empty one when
    there is none (or when what is in the file is not a record: the next change sets that damaged file aside,
    never over it). Raises Unreadable when the file is there and would not be read just now."""
    rec = _slim(kit)
    return _join(rec, words_for(kit, rec.get("video")))


def _set_aside(p):
    """A record that can't be read: moved to talking.damaged-<date>-<time>.json beside it, never written over."""
    stem = p.name[:-5] if p.name.endswith(".json") else p.name
    base = f"{stem}.damaged-{time.strftime('%Y%m%d-%H%M%S')}"
    for k in range(1, 100):
        dst = p.with_name(base + ("" if k == 1 else f"-{k}") + ".json")
        if not os.path.lexists(dst):
            os.rename(p, dst)
            log(f"{p.parent.parent.name}: {p.name} could not be read; set aside as {dst.name}")
            return dst
    raise OSError("no free name to set the damaged record aside under")


def _same(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


QUIET_FIELDS = ("made",)                  # the Assistant's own notes: nothing the page edits or reads (see change)


def change(kit, fn, src=None, stale_why="its script was made again", quiet=False):
    """Read the record, change it (fn(record with its words); return False to leave it alone, raise to refuse),
    and save it as one step no other command or page can get in the middle of. The version before is kept
    beside it. Nothing is written when fn changed nothing. An accepted change moves the counter ("rev") on by
    one. The words themselves are never written from here (put_words does that, once per video).
    `quiet`: a change that touches ONLY the Assistant's own notes (QUIET_FIELDS: which reels were made) is saved
    without moving the counter, the page's stamp or its mark, and without replacing the version before: the page
    never edits or reads those, so its next save is not refused as stale and its Undo list is not emptied by a
    press of Make it in CapCut (hers has no counter, so her note costs nothing either). A quiet change that
    turns out to touch anything else is an ordinary change.
    Returns the record as it now is, words joined on."""
    kit = Path(kit)
    kitmod.hidden(kit)
    with kitmod._held(kit / ".kit" / LOCK, LOCK_WAIT) as got:
        if got is False:
            raise Busy(BUSY)
        p = record_path(kit)
        d, there = _read_json(p)
        if there and d is None:
            _set_aside(p)
            there = False
        slim = d if d is not None else {"v": 1}
        before = json.loads(json.dumps(slim))
        wf = _words_file(kit)
        entry = words_for(kit, slim.get("video"), wf)
        full = _join(slim, entry)
        settled = _stale_edit(full, entry, stale_why)     # written even if fn then changes nothing
        if fn(full) is False and not settled:
            return _join(before, words_for(kit, before.get("video"), wf))
        new = {k: v for k, v in full.items() if k not in WORD_FIELDS}
        if _same(new, before):
            return full
        new["v"] = 1
        own = set(QUIET_FIELDS) | {"v"}
        if quiet and there and all(_same(new.get(k), before.get(k)) for k in (set(new) | set(before)) - own):
            arrange.write_whole(p, new)                    # rev, updated and from exactly as they were
            return _join(dict(new), words_for(kit, new.get("video"), wf))
        new["rev"] = _rev(before) + 1
        new["updated"] = time.time()                       # hers: the page tells a change by this
        if src is not None:
            new["from"] = src                              # which page saved it, and from which counter
        else:
            new.pop("from", None)
        if there:
            try:
                reel_page._write_bytes_whole(p.with_name(PREV), p.read_bytes())
            except OSError:
                pass                                       # the earlier copy could not be read: the save still goes ahead
        arrange.write_whole(p, new)
        return _join(dict(new), words_for(kit, new.get("video"), wf))


def keep_replaced(rec, why):
    """Before something of theirs is replaced (a cut --replace, a place --replace, Edit my video pressed again on
    the same video): the current cuts, photo stretches, zooms, splits and speeds go into the record's "replaced",
    dated, the last 12 kept. Nothing is added when there is nothing to keep."""
    eng = _engine()
    now = {"cut": rec.get("cut") or [], "shots": eng.shots(rec), "zooms": eng.zooms(rec),
           "splits": rec.get("splits") or [], "speeds": rec.get("speeds") or []}
    if not any(now.values()):
        return False
    lst = [x for x in _lst(rec, "replaced") if isinstance(x, dict)]
    lst.append(dict(now, when=time.strftime("%Y-%m-%d %H:%M:%S"), why=str(why)[:80], video=rec.get("video")))
    rec["replaced"] = lst[-REPLACED_KEPT:]
    return True


def fresh_edit(rec, why):
    """A new script for the same video: what was there is kept in "replaced", then every word-numbered field is
    emptied (the numbers belong to the old words)."""
    keep_replaced(rec, why)
    for k in EDIT_FIELDS:
        rec.pop(k, None)


def switch_video(rec, new):
    """They chose another video in the Talking folder. The edit of the video the record was on (every
    word-numbered field) moves into rec["earlier"][<its name>]; the new video's edit comes back out of "earlier"
    if it has one, else every such field starts empty. Captions, their spot and size, and who places the photos
    stay as they are. Returns True when an earlier edit came back. The words follow the video by themselves
    (they are kept per video)."""
    old = rec.get("video")
    if old == new:
        return False
    earlier = rec.get("earlier") if isinstance(rec.get("earlier"), dict) else {}
    if isinstance(old, str) and old:
        edit = {k: rec[k] for k in EDIT_FIELDS if k in rec}
        if edit:
            if rec.get("words_of") is not None:
                edit["words_of"] = rec["words_of"]         # which script these word numbers belong to
            earlier[old] = dict(edit, kept=time.strftime("%Y-%m-%d %H:%M:%S"))
    for k in EDIT_FIELDS + ("words_of",):
        rec.pop(k, None)
    back = earlier.pop(new, None) if isinstance(new, str) else None
    if isinstance(back, dict):
        for k in EDIT_FIELDS + ("words_of",):
            if k in back:
                rec[k] = back[k]
    rec["earlier"] = earlier
    rec["video"] = new
    return isinstance(back, dict)


def use_video(kit, name):
    """Make `name` (a file in the Talking folder) the video this record is about. Its script and its edit come
    back if it was done before ("ready", no new transcription); otherwise the record waits for its words."""
    wf = _words_file(kit)

    def fn(rec):
        if rec.get("video") == name:
            return False
        switch_video(rec, name)
        entry = words_for(kit, name, wf)
        if entry:
            _stale_edit(rec, entry, "its script was made again")     # the edit that came back is another script's
            rec["words_of"] = _entry_id(entry)
        rec["status"] = "ready" if entry else ""
        rec["step"], rec["problem"] = "", ""
    return change(kit, fn)


def put_words(kit, name, key, words, info=None, more=None, again=False, switch=True):
    """A video has just been turned into words: keep them (once, in the words file, the version before beside
    it), and make the record ready on that video. Words made again for a video that already had a script start
    its edit afresh (what was there is kept in "replaced"): the word numbers belong to the old words.
    `key` is the video's key as it was when the words were made (video.key); `more` may hold "how", "ondevice".
    `again=True` is Edit my video pressed again on a video that already had its script: the edit starts afresh
    even when the words come back the same (hers always does; the plan's "replaced"). Without it, the same words
    for the same file change nothing, so a job that runs twice is harmless.
    `switch=False` (the job's own save): when they chose ANOTHER video while this one's words were being made,
    the words are kept (they are per video) and the record is left on the video they chose; this video's script
    is there when they come back to it (use_video), its earlier edit started afresh then if it must be.

    Safe to cut off: the words file is written first and the record second, and the record carries the mark of
    the script its edit belongs to ("words_of"). If this stops between the two, the record's mark no longer
    matches, and the next run here (or the next change of any kind) starts the edit afresh then."""
    kit = Path(kit)
    eng = _engine()
    words = eng.clean(words)
    kitmod.hidden(kit)
    with kitmod._held(kit / ".kit" / "talking-words.lock", LOCK_WAIT) as got:
        if got is False:
            raise Busy(BUSY)
        wf = _words_file(kit)
        had = words_for(kit, name, wf)
        rewrote = bool(had) and (had.get("words") != words or had.get("key") != key)
        eid = words_id(key, words)
        entry = {"key": key, "id": eid, "words": words, "sentences": eng.sentences(words), "transcribed": time.time()}
        if isinstance(info, dict):
            entry["info"] = info
        for k in ("how", "ondevice"):
            if isinstance(more, dict) and k in more:
                entry[k] = more[k]
        if not had or rewrote:
            p = words_path(kit)
            d, there = _read_json(p)
            if there and d is None:
                _set_aside(p)
            elif there:
                try:
                    reel_page._write_bytes_whole(p.with_name(WORDS_PREV), p.read_bytes())
                except OSError:
                    pass
            wf["videos"][name] = entry
            arrange.write_whole(p, wf)

    def fn(rec):
        if rec.get("video") != name:
            if not switch:
                # they are on another video now: leave them there. This video's edit, set aside when they left,
                # is marked so it starts afresh when they come back, if it belongs to the old words.
                e = rec.get("earlier", {}).get(name) if isinstance(rec.get("earlier"), dict) else None
                if isinstance(e, dict) and (again or (e.get("words_of") is None and rewrote)) and e.get("words_of") != MADE_AGAIN:
                    e["words_of"] = MADE_AGAIN
                    return None
                return False
            switch_video(rec, name)
        was = rec.get("words_of")
        if again or (was is not None and was != eid) or (was is None and rewrote):
            fresh_edit(rec, "Edit my video again")
        rec["words_of"] = eid
        rec["status"], rec["step"], rec["problem"] = "ready", "", ""
        rec.setdefault("captions", True)
    return change(kit, fn, stale_why="Edit my video again")


# ---------- the Talking folder ----------

def talking_dir(kit):
    return Path(kit) / TALKING


def talking_ok(kit):
    """Is <kit>/Talking (if it is there at all) a real folder of the kit's own? (reel_page's rule for Footage.)"""
    return reel_page._own_folder(Path(kit), TALKING)


def list_talks(kit, coming=None):
    """The videos in <kit>/Talking, in name order: [{key, name, path, size, facts}], the reel page's Footage
    listing pointed at this folder (dot files and links left out; a file still being copied in waits, and goes
    in `coming`). Their facts are kept in .kit/talking/facts.json."""
    return reel_page.list_videos(Path(kit), coming, folder=TALKING)


def talk_by_key(kit, key, talks=None):
    if not isinstance(key, str) or not KEY.fullmatch(key):
        return None
    return next((v for v in (talks if talks is not None else list_talks(kit)) if v["key"] == key), None)


def talk_by_name(kit, name, talks=None):
    want = _nfc(str(name or "")).casefold()
    return next((v for v in (talks if talks is not None else list_talks(kit)) if _nfc(v["name"]).casefold() == want), None)


def _plain_videos(kit, folder):
    """{name as compared: (name as it is, path)} for the videos in one of the kit's own folders, from its exact
    listing; nothing is opened (for turning a name in the record into a key, and back)."""
    kit = Path(kit)
    d = kit / folder
    out = {}
    if not reel_page._own_folder(kit, folder) or not d.is_dir():
        return out
    for f in sorted(reel_page._listing(d)):
        if f.startswith(".") or not f.lower().endswith(reel_page.VIDEO_EXTS):
            continue
        p = d / f
        try:
            if p.is_symlink() or not p.is_file():
                continue
        except OSError:
            continue
        out.setdefault(_nfc(f).casefold(), (f, p))
    return out


def _key_of(p):
    try:
        return reel_page._video().key(p)
    except OSError:
        return None


def gone_key(name):
    """What stands in for the key of a video that is no longer in its folder: made from its name alone, so it can
    never be the key of a real file (a real key has the file's size and time in it)."""
    return hashlib.sha1(("gone|" + _nfc(str(name))).encode("utf-8")).hexdigest()[:12]


def video_state(kit, rec, talks=None):
    """Where the record's video stands: "" (none chosen), "here" (in the Talking folder, the one its script was
    made from), "changed" (a file by that name is there but it is not the one the script was made from: it was
    exported again), "gone" (no file by that name)."""
    name = rec.get("video")
    if not isinstance(name, str) or not name:
        return ""
    hit = _plain_videos(kit, TALKING).get(_nfc(name).casefold())
    if hit is None:
        return "gone"
    made_from = rec.get("video_key")
    if rec.get("words") and made_from and _key_of(hit[1]) != made_from:
        return "changed"
    return "here"


# ---------- turning a video into words: a job of its own (hers: a thread inside her server) ----------
# Edit my video (start) writes the job down and starts a process of its own (talking_rec.py job), which the page
# server starting over cannot stop. The job: the video's facts, whatever the transcriber needs set up (the first
# time only), the small copy to play on the page, the sound, the words, then ONE whole save (put_words). One job
# per shoot (.kit/talking-job.lock, held for as long as the job lives); one talking job at a time on this
# computer (<the Assistant's own folder>/talking/turn.lock); the small copy and the sound are made in the
# computer's one video turn (video.turn(), shared with a backup's clip work, so a talk may wait behind a backup).
# Every step has its own stated time limit, a watchdog stops a job that runs past them all, and a job that died
# reads as plain words on the page, never a page stuck on "Getting your video ready…".
# The two waits (for another shoot's talking job, for the video turn) share one allowance. The computer is kept
# awake for as long as the job lives (this_computer.awake_while; a closed lid still stops it, and every limit is
# a clock time, so a Mac that slept part way comes back as "took too long"). A job whose words reached their file
# but whose record was busy is finished by the next look (settle), never thrown away; a job that starts after
# the page was told it stopped makes nothing; and the job's save never moves the record off a video they have
# since chosen.
#
# Where things are: the small copy is the kit's (.kit/talking/<the video's key>/preview.mp4, made once and
# kept); the sound the transcriber listens to is on the computer's own disk (talking/work/<job>/, removed when
# the job ends, and by the next job if this one was killed); the transcriber's own app, when there is one, is
# in talking/ too. Nothing of theirs is kept there.

JOB = "talking-job.json"                  # the newest job: {id, state, video, key, again, t, t0, pid, until}
JOB_ID = re.compile(r"[0-9a-f]{12}")
JOB_BOOT = 20.0                           # seconds a job may take to start before "queued" means it never did
TALK_HOME = arrange.HOME / "talking"      # on the computer's own disk: the transcriber's app, and the scratch sound
WORK = TALK_HOME / "work"
TALK_TURN = "turn.lock"
MAX_TALK = 30 * 60                        # ours (hers has no limit): a talk over 30 minutes is refused
SETUP_LIMIT = 300.0                       # ours: the first-time setup (building the small app) may take this long
JOB_GRACE = 30.0                          # the plan's 30 s of grace
SETUP_TURN_WAIT = 20.0                    # `setup` from the chat waits this long for a talking job to finish, then says so
SAVE_TRIES = 6                            # the finished words' last save is tried this often when the record is busy
COPY_SMALLEST = 1000                      # a small copy under this many bytes is no video (video._copy_now's own floor)
WORK_YOUNG = 30.0                         # a work folder this new is never cleared (its job may be about to hold it)
LANG = "en-US"                            # hers: the only language asked for
TEST_LIMITS = "ASSISTANT_TEST_TALK_LIMITS"   # tests only: a JSON object of limits in seconds, in place of the real ones

# Hers, word for word (talking_core.py): what the page is told while a video becomes a script, and when it can't.
JOB_WORDS = {
    "ready_video": "Getting your video ready…",
    "to_script": "Turning your words into a script…",
    "not_in_folder": "That video isn't in this shoot's Talking folder.",
    "still_working": "I'm still working on the last one. Give it a minute.",
    "lowspace": "The photo drive is almost full, so I couldn't make the preview.",
    "unreadable": "I couldn't read that video. Try exporting it again as a regular .mov or .mp4.",
    "no_talking": "I couldn't hear any talking in that video.",
}
# Ours: states hers never reaches, or reaches with words that would be wrong. Every one a DRAFT for Nicole to
# reword. Each with its reason. (line, why it is ours)
# The Mac's real box was seen on Nov 12, 2026 (Dustin's Mac, macOS 27.2). Title: Allow "Assistant Transcriber" to
# access what is said using speech recognition?  Apple's own fixed sentence: "Speech data from this app will be
# sent to Apple to process your requests. This will also help Apple improve its speech recognition technology."
# Then the plist's line: "So your talking video turns into a script you can edit."  Buttons: [Don't Allow] [Allow].
# The app it names is the plist's CFBundleName, "Assistant Transcriber" (not its display name, "The Assistant"),
# and that is its name in System Settings too, so the permission lines name that app and that button.
OUR_JOB_WORDS = {
    "setup": ("Setting up, just this once…",
              "hers has the transcriber built by hand beforehand; ours builds it on their Mac the first time"),
    "asking": ("Your Mac is asking if Assistant Transcriber may use Speech Recognition. Press Allow in that box and "
               "I'll carry on. (It may be behind this window.)",
               "hers waits in silence while macOS asks"),
    "no_answer": ("Your Mac asked if Assistant Transcriber may use Speech Recognition, and nobody answered, so I "
                  "stopped. Press Edit my video to try again, and press Allow when the box comes up.",
                  "hers would wait an hour"),
    "refused": ("Speech Recognition is turned off for Assistant Transcriber, so I can't turn your talking into words "
                "yet. To turn it on: open System Settings, then Privacy & Security, then Speech Recognition, and switch "
                "on Assistant Transcriber. Then press Edit my video again.",
                "hers says \"click Allow, then try again\", which is wrong once refused: macOS never asks twice"),
    "restricted": ("This Mac doesn't allow Speech Recognition (Screen Time or a work profile is holding it off), so I "
                   "can't turn your talking into words on it.",
                   "hers shows the Mac's own error words"),
    "dictation_off": ("Your Mac's Dictation looks to be turned off, and I need it to turn your talking into words. To "
                      "turn it on: open System Settings, then Keyboard, and switch on Dictation. Then press Edit my "
                      "video again.",
                      "hers shows the Mac's own error words"),
    "servers": ("This Mac can only turn talking into words by sending the sound to Apple, and I won't send your video's "
                "sound anywhere. So I can't make a script on this Mac yet.",
                "hers sends the sound to Apple without a word (rules 7 and 8)"),
    "no_tools": ("Talking reels need one more thing from Apple on this Mac before the first one. Tell your assistant: "
                 "set up talking reels.",
                 "ours builds the transcriber on their Mac, which needs Apple's Command Line Tools"),
    "old_tools": ("Apple's tools on this Mac are older than its macOS, so I couldn't finish setting up. Tell your "
                  "assistant: set up talking reels.",
                  "after a macOS update the compiler and the SDK can disagree"),
    "licence": ("Apple's tools on this Mac are waiting for their licence to be accepted, so I couldn't finish setting "
                "up. Tell your assistant: set up talking reels.",
                "an Xcode whose licence was never accepted refuses to build"),
    "setup_failed": ("I couldn't finish setting up talking reels on this Mac. Tell your assistant: set up talking reels.",
                     "the build can fail in ways hers never meets"),
    "old_mac": ("Talking reels need macOS 13 or newer, and this Mac is on an older one.",
                "hers needs macOS 13 too and does not say so"),
    "changed": ("This video has changed since its script was made. Press Edit my video to make its script again.",
                "hers keeps the old script on a video exported again under the same name"),
    "too_long": ("That took too long, so I stopped. Nothing of yours was changed. Press Edit my video to try again.",
                 "hers has no limit: a hung step leaves the page on \"Getting your video ready…\" for good"),
    "over_30": ("That video is over 30 minutes, which is more than I can turn into a script. Try a shorter one.",
                "hers has no limit"),
    "waited": ("Another video was still being worked on, so I didn't get to yours. Press Edit my video to try again.",
               "hers does one video at a time inside her server; ours can wait behind a backup's clips or another "
               "shoot's talk, and her \"still working on the last one\" would not be true of this shoot"),
    "interrupted": ("I was stopped before the script was finished. Press Edit my video to try again.",
                    "hers stays on \"Getting your video ready…\" when her server stops part way"),
    "failed": ("I couldn't turn the talking into words just now. Press Edit my video to try again.",
               "hers shows the Mac's own error words in brackets; ours keeps those in the log"),
    "pc": (this_computer.NO_TALKING_PC, "hers has no PC"),
}
# Ours, shown under the "asking" line while the Mac's box is up. The box carries Apple's fixed sentence about speech
# data being sent to Apple; the app only ever asks the Mac to do it by itself (transcribe.swift: the "by itself?"
# question first, requiresOnDeviceRecognition = true, and "servers" otherwise). It says what the app ASKS FOR and
# no more: nobody has watched the network, so no line of ours says nothing is sent. A draft for Nicole.
APPLE_NOTE = ("The box says speech data will be sent to Apple. Apple puts that sentence on every box like this. I only "
              "ask your Mac to do it by itself, and I stop if it can't.")
# What video.preview_copy says, as this page's own lines (its `words` are the footage page's, never passed on).
COPY_STATES = {"lowspace": "lowspace", "failed": "unreadable", "busy": "waited", "pc": "pc", "hevc_pc": "pc"}


def line_for(code):
    """The page's line for a state: hers where she has one, else ours. An unknown state gets the plain "couldn't"."""
    if code in JOB_WORDS:
        return JOB_WORDS[code]
    return OUR_JOB_WORDS.get(code, OUR_JOB_WORDS["failed"])[0]


class JobProblem(Exception):
    """The job can't go on: `code` names the page's line (line_for); `detail` is for the log only."""

    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code, self.detail = code, str(detail or "")[:1500]


def _vm():
    return reel_page._video()


def _sound():
    return reel_page._reel_module("sound")


def _transcribe():
    return reel_page._reel_module("transcribe")


def transcriber():
    """The way this computer turns talking into words (transcribe.pick), its files in the Assistant's own folder."""
    return _transcribe().pick(TALK_HOME)


def limits(length):
    """The job's stated time limits for a video `length` seconds long, in seconds:
    turn   waiting for the computer's one video turn AND for another shoot's talking job, ONE allowance shared
           by the two waits (the plan's 900 s): does not count against the work
    setup  the first-time setup;  ask  the Mac's own question, waiting for an answer
    copy   the small copy: the larger of 120 s and 3 times the length
    sound  the larger of 120 s and the length;  words  the larger of 5 minutes and 4 times the length
    grace  30 s;  spare  a minute;  ceiling  the whole job: their sum and the spare minute."""
    n = max(0.0, float(length or 0))
    d = {"turn": float(_vm().TURN_WAIT), "setup": SETUP_LIMIT, "ask": float(_transcribe().ASK_WAIT),
         "copy": max(120.0, 3 * n), "sound": max(120.0, n), "words": max(300.0, 4 * n), "grace": JOB_GRACE, "spare": 60.0}
    t = os.environ.get(TEST_LIMITS)
    if t:
        try:
            d.update({k: float(v) for k, v in json.loads(t).items() if k in d})
        except (ValueError, TypeError, AttributeError):
            pass
    d["ceiling"] = d["setup"] + d["ask"] + d["copy"] + d["sound"] + d["words"] + d["grace"] + d["spare"]
    return d


def job_path(kit):
    return Path(kit) / ".kit" / JOB


def read_job(kit):
    try:
        j = json.loads(job_path(kit).read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def write_job(kit, j):
    arrange.write_whole(job_path(kit), j)


def _fnum(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def job_running(kit):
    """Is a job turning this shoot's video into words right now? The job holds .kit/talking-job.lock for as long
    as it lives (reel_page.job_running's way); nothing is made by asking. On a drive that has no locks, the
    job's own process number is asked after instead, for at most the job's ceiling and a minute."""
    p = Path(kit) / ".kit" / JOB_LOCK
    try:
        if p.is_file():
            with open(p, "a", encoding="utf-8") as f:       # never written to: only looked at
                got = this_computer.try_lock(f, shared=True)
                if got is False:
                    return True
                if got:
                    this_computer.unlock(f)
                    return False
    except OSError:
        pass
    j = read_job(kit) or {}
    if j.get("state") != "running":
        return False
    return time.time() < _fnum(j.get("until")) + 60 and arrange._pid_alive(j.get("pid"))


def _starting(j):
    """Written down a moment ago and not yet picked up by its own process."""
    return bool(j) and j.get("state") == "queued" and not j.get("pid") and time.time() - _fnum(j.get("t")) < JOB_BOOT


def settle(kit):
    """A record that says "working" when no job is: the job was killed, the computer was turned off, or it ran
    past every limit. The record is given its plain line (once), so the page never waits on a job that is gone.
    True when it changed the record. Cheap when there is nothing to do; never raises."""
    kit = Path(kit)
    try:
        if _slim(kit).get("status") != "working":
            return False
    except Unreadable:
        return False

    def gone():
        j = read_job(kit) or {}
        until = _fnum(j.get("until"))
        if j.get("state") == "running" and until and time.time() > until + JOB_GRACE:
            return "too_long"                     # past its time, whatever its lock says
        if job_running(kit) or _starting(j):
            return None
        return "interrupted"

    if gone() is None:
        return False
    done = []

    def fn(rec):
        code = gone()                             # asked again, now that nothing else can be changing the record
        if rec.get("status") != "working" or code is None:
            return False
        j = read_job(kit) or {}
        if _landed(rec, j):                       # its words were kept and only the record's save was missed
            _ready(rec, j)
            code = "landed"
        else:
            _stopped(rec, line_for(code))
        done.append((code, j.get("id")))
    try:
        change(kit, fn)
    except (Busy, Unreadable, OSError):
        return False
    if done:
        # the job is written down as over too, so a process that starts late (a busy Mac, one just woken) sees
        # it is no longer wanted and makes nothing, instead of turning the record ready minutes after this
        j = read_job(kit) or {}
        if j.get("id") == done[0][1] and j.get("state") in ("queued", "running"):
            _job_over(kit, j.get("id"), "done" if done[0][0] == "landed" else "problem")
        log(f"{kit.name}: the job turning its video into words was gone ({done[0][0]}); the record says so now")
        try:                                      # a job killed outright never tidied up: the sound of their talk
            cleared = clear_stale_work()          # is not left on the disk until some later talking job
            if cleared:
                log(f"cleared the scratch of {len(cleared)} talking job(s) that were stopped part way")
        except Exception:  # noqa: BLE001  (settle never raises)
            pass
    return bool(done)


def _landed(rec, j):
    """Did this job's words reach the words file, with only the record's own save missed? (The record's lock was
    busy at the very end, or the job was stopped between its two saves.) rec: the record with its words joined on."""
    if not isinstance(j, dict) or not isinstance(j.get("video"), str) or rec.get("video") != j["video"]:
        return False
    began = _fnum(j.get("t0")) or _fnum(j.get("t"))
    return bool(rec.get("words")) and bool(began) and isinstance(j.get("key"), str) and rec.get("video_key") == j["key"] \
        and _fnum(rec.get("transcribed")) >= began


def _ready(rec, j):
    """The record made ready on words that are already kept (what put_words' second half does)."""
    if j.get("again") and any(k in rec for k in EDIT_FIELDS):
        fresh_edit(rec, "Edit my video again")
    rec["words_of"] = words_id(rec.get("video_key"), rec.get("words"))
    rec["status"], rec["step"], rec["problem"] = "ready", "", ""
    rec.setdefault("captions", True)


def _stopped(rec, line):
    """The record after a job that didn't finish: its plain line; a script made earlier for this video is still
    there and still theirs to edit ("ready"), otherwise there is nothing to show but the line ("problem")."""
    rec["status"] = "ready" if rec.get("words") else "problem"
    rec["step"], rec["problem"] = "", str(line)[:300]


def preview_path(kit, key):
    """Where the small copy of a talking video is kept (made once per video key, in the kit's hidden folder)."""
    return Path(kit) / ".kit" / TALKING.lower() / str(key) / "preview.mp4"


def preview_for(kit, rec=None):
    """The small copy to play for the record's video, or None when there is none (for the page's player).
    The video as it is in the Talking folder now; when it has gone, the copy made from the one its script was
    made from."""
    kit = Path(kit)
    rec = rec if rec is not None else load(kit)
    name = rec.get("video")
    if not isinstance(name, str) or not name:
        return None
    hit = _plain_videos(kit, TALKING).get(_nfc(name).casefold())
    for key in ((_key_of(hit[1]) if hit else None), rec.get("video_key")):
        if isinstance(key, str) and KEY.fullmatch(key) and preview_path(kit, key).is_file():
            return preview_path(kit, key)
    return None


# ---------- Make it in CapCut: may it be made, and the words for when it may not ----------
# Hers, word for word (server.py make_talking): why a talking reel can't be made right now.
MAKE_WORDS = {
    "no_script": NO_SCRIPT_MAKE,
    "gone": "Your talking video isn't in the Talking folder anymore.",
    "all_cut": "Everything is cut. Bring some words back first.",
    "went_wrong": "Something went wrong making it.",
}
# Ours, each a DRAFT for Nicole to reword, each with its reason (decision 2b.13). (line, why it is ours)
OUR_MAKE_WORDS = {
    "photo_gone": ("A photo in your talking reel isn't in this shoot anymore. Take it off its words or put it back, "
                   "then make it again.",
                   "hers leaves that stretch out of the reel without a word; ours stops before anything is written"),
    "video_gone": ("A video in your talking reel isn't in the Footage folder anymore. Take it off its words or put it "
                   "back, then make it again.",
                   "hers leaves that stretch out of the reel without a word; ours stops before anything is written"),
    # capcut.py's own STOP lines as the page's result box may show them (any place taken out by reel_page._no_path).
    # Hers shows her maker's STOP line too; these are our maker's. Any OTHER line capcut.py stops with is told as
    # her "Something went wrong making it." and kept in the log.
    "no_capcut": ("I can't find CapCut's projects folder. Is CapCut installed, and has it been opened once?",
                  "capcut.py's own stop, as the photo reel's page shows it: tells them what to do, where hers says only that something went wrong"),
    "no_folder": ("I couldn't make the project's folder in CapCut's projects folder. Nothing was written.",
                  "capcut.py's own stop, as the photo reel's page shows it"),
    "no_name": ("I couldn't give the CapCut project its name. Nothing was added to CapCut. Try again.",
                "capcut.py's own stop, as the photo reel's page shows it"),
}
CAPCUT_STOPS = ("no_capcut", "no_folder", "no_name")


def make_line(code):
    """The page's line for why a talking reel can't be made: hers where she has one, else ours; a video still
    being turned into words gets her "still working" line, one exported again our "changed" line (stage B)."""
    if code in MAKE_WORDS:
        return MAKE_WORDS[code]
    if code in OUR_MAKE_WORDS:
        return OUR_MAKE_WORDS[code][0]
    if code in ("working", "making"):                  # "making": another make of this shoot's reel is at work
        return JOB_WORDS["still_working"]
    if code == "changed":
        return line_for("changed")
    if code == "trouble":
        return TROUBLE
    return MAKE_WORDS["went_wrong"]


def make_problem(kit, rec=None):
    """Why this shoot's talking reel can't be made in CapCut right now, as a code for make_line, or None when it
    can. "working" while its video is being turned into words; "no_script"; "changed" when the video was exported
    again since its script was made (every word's time belongs to the old file); "gone" when it is no longer in
    the Talking folder; "all_cut" when no word is left."""
    kit = Path(kit)
    rec = rec if rec is not None else load(kit)
    if job_running(kit) or rec.get("status") == "working":
        return "working"
    if not rec.get("words"):
        return "no_script"
    vs = video_state(kit, rec)
    if vs == "changed":
        return "changed"
    if vs != "here":
        return "gone"
    if not _engine().pieces(rec):
        return "all_cut"
    return None


def can_make(kit, rec=None):
    """May this shoot's talking reel be made in CapCut right now? (True, "") or (False, the page's line)."""
    code = make_problem(kit, rec)
    return (True, "") if code is None else (False, make_line(code))


def facts_problem(f):
    """Why this video can't be turned into a script, from its facts alone (before anything is made), or None."""
    if not isinstance(f, dict) or f.get("refused"):
        return "unreadable"
    if not f.get("has_audio"):
        return "no_talking"                       # hers: "I couldn't hear any talking in that video."
    if _fnum(f.get("length")) > MAX_TALK:
        return "over_30"
    if _fnum(f.get("length")) <= 0:
        return "unreadable"
    return None


_START = threading.Lock()


def start(kit, video):
    """Edit my video: turn `video` (its key as the page sends it, or its file name) into a script, in a job of
    its own. (status, answer): {"ok": True} when the job was started, else {"ok": False, "why", "words"} with the
    page's line and NOTHING made or changed.
    On a PC (and on a Mac older than macOS 13) it answers at once with that computer's line."""
    kit = Path(kit)
    tr = transcriber()
    if tr.name == "none":
        return 200, {"ok": False, "why": tr.why(), "words": line_for(tr.why())}
    with _START:
        talks = list_talks(kit)
        talk = talk_by_key(kit, video, talks) or talk_by_name(kit, video, talks)
        if talk is None:
            return 404, {"ok": False, "why": "gone", "words": JOB_WORDS["not_in_folder"]}
        if job_running(kit) or _starting(read_job(kit)):
            return 409, {"ok": False, "why": "working", "words": JOB_WORDS["still_working"]}
        bad = facts_problem(talk["facts"])
        if bad:
            return 200, {"ok": False, "why": bad, "words": line_for(bad)}
        name, jid = talk["name"], os.urandom(6).hex()
        try:
            again = bool(words_for(kit, name))
            kitmod.hidden(kit)
            write_job(kit, {"id": jid, "state": "queued", "t": time.time(), "video": name, "key": talk["key"],
                            "again": again, "length": _fnum(talk["facts"].get("length"))})

            def fn(rec):
                if rec.get("video") != name:
                    switch_video(rec, name)
                rec["status"], rec["step"], rec["problem"] = "working", JOB_WORDS["ready_video"], ""
                rec.setdefault("captions", True)
            change(kit, fn)
        except Busy:
            _job_over(kit, jid, "problem")
            return 503, {"ok": False, "why": "busy", "words": BUSY}
        except (Unreadable, OSError) as e:
            log(f"{kit.name}: Edit my video could not start ({e.__class__.__name__}: {e})")
            _job_over(kit, jid, "problem")
            return 503, {"ok": False, "why": "trouble", "words": TROUBLE}
        try:
            fresh.LOGS.mkdir(parents=True, exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as out:
                # a Mac: a session of its own; a PC: no window, a process group of its own (as the reel's job)
                this_computer.popen_detached([sys.executable, str(HERE / "talking_rec.py"), "job", str(kit), "--id", jid],
                                             stdout=out, stderr=subprocess.STDOUT, **arrange._child_env())
        except OSError as e:
            log(f"{kit.name}: the job could not be started: {e}")
            _job_over(kit, jid, "problem")
            _fail(kit, name, line_for("failed"))
            return 200, {"ok": False, "why": "failed", "words": line_for("failed")}
        return 200, {"ok": True}


def _job_over(kit, jid, state):
    try:
        j = read_job(kit) or {}
        if j.get("id") == jid:
            j.update(state=state, t=time.time())
            write_job(kit, j)
    except OSError:
        pass


def _fail(kit, name, line, j=None):
    """The job stopped: the record gets its line (only if it is still on that video and still says working).
    With the job `j`: when its words did reach the words file and only the record's save was missed, the record
    is made ready instead (the work is never thrown away over a busy moment)."""
    def fn(rec):
        if rec.get("video") != name or rec.get("status") != "working":
            return False
        if j is not None and _landed(rec, j):
            _ready(rec, j)
        else:
            _stopped(rec, line)
    try:
        change(kit, fn)
    except (Busy, Unreadable, OSError) as e:
        log(f"{Path(kit).name}: the record could not be told the job stopped ({e.__class__.__name__}); settle() will")


def _step(kit, name, line):
    """What the page shows under Edit my video while the job is at work."""
    def fn(rec):
        if rec.get("video") != name or rec.get("status") != "working" or rec.get("step") == line:
            return False
        rec["step"] = line
    try:
        change(kit, fn)
    except (Busy, Unreadable, OSError):
        pass                                      # a line on the page, nothing more: the work goes on


# ---- the job's scratch folders on the computer's own disk

def _work_alive(d):
    """Is the job this work folder belongs to still alive? It holds the folder's own lock for as long as it lives."""
    try:
        with open(d / ".lock", "a", encoding="utf-8") as f:
            got = this_computer.try_lock(f)
            if got is False:
                return True
            if got:
                this_computer.unlock(f)
                return False
    except OSError:
        return True                               # can't tell: leave it be
    try:                                          # no locks here: by the job's own number, for at most its ceiling
        o = json.loads((d / "owner.json").read_text(encoding="utf-8"))
        return time.time() < _fnum(o.get("until")) + 60 and arrange._pid_alive(o.get("pid"))
    except (OSError, ValueError, AttributeError):
        return False


def clear_stale_work():
    """Take away work folders whose job is no longer alive (a job stopped by the watchdog can't tidy up after
    itself). Ours by name only: a folder directly inside talking/work whose name is a job's id. Returns the
    names it removed."""
    out = []
    try:
        names = sorted(os.listdir(WORK))
    except OSError:
        return out
    for n in names:
        d = WORK / n
        try:
            if not JOB_ID.fullmatch(n) or d.is_symlink() or not d.is_dir():
                continue
            if time.time() - d.stat().st_mtime < WORK_YOUNG or _work_alive(d):
                continue
            shutil.rmtree(d)
            out.append(n)
        except OSError:
            continue
    return out


BUILD_DIR = re.compile(r"build-(\d+)-[0-9a-f]{6}")


def clear_stale_builds():
    """Take away a scratch build folder left by a build that was stopped part way (the watchdog, the power).
    Ours by name only: a folder directly inside the talking folder named build-<process number>-<six letters>,
    whose process is gone, and older than a build can take. Returns the names it removed."""
    out = []
    try:
        names = sorted(os.listdir(TALK_HOME))
        old = float(_transcribe().BUILD_LIMIT) + 120
    except OSError:
        return out
    for n in names:
        m = BUILD_DIR.fullmatch(n)
        d = TALK_HOME / n
        try:
            if not m or d.is_symlink() or not d.is_dir():
                continue
            if time.time() - d.stat().st_mtime < old or arrange._pid_alive(int(m.group(1))):
                continue
            shutil.rmtree(d)
            out.append(n)
        except (OSError, ValueError):
            continue
    return out


def _copy_usable(p):
    """Is the small copy at `p` a video that can be played? (One found already there is otherwise used as it is.)"""
    try:
        if Path(p).stat().st_size < COPY_SMALLEST:
            return False
        return _fnum(_vm().facts(p).get("length")) > 0
    except Exception:  # noqa: BLE001  (not a video, or it can't be read)
        return False


def _set_copy_aside(p):
    """A small copy that is there and is no video (a drive that hiccuped, a copy cut short by something other
    than us): moved to preview.unusable-<date>-<time>.mp4 beside it, never deleted, so a good one can be made."""
    p = Path(p)
    base = f"preview.unusable-{time.strftime('%Y%m%d-%H%M%S')}"
    for k in range(1, 100):
        dst = p.with_name(base + ("" if k == 1 else f"-{k}") + ".mp4")
        if not os.path.lexists(dst):
            os.rename(p, dst)
            log(f"{p.parent.parent.parent.parent.name}: the small copy {p.parent.name}/{p.name} was no video; set aside as {dst.name}")
            return dst
    raise OSError("no free name to set the unusable small copy aside under")


def _save_words(kit, name, key, words, info, more, again):
    """The job's one whole save. The words file is written first (put_words); when the record itself is busy
    just then it is tried again a few times (the words are already safe, and the same words written twice
    change nothing), so many minutes of work are never thrown away over a short clash."""
    for k in range(SAVE_TRIES):
        try:
            return put_words(kit, name, key, words, info=info, more=more, again=again, switch=False)
        except Busy:
            if k == SAVE_TRIES - 1 or time.time() > _UNTIL[0] - 2 * LOCK_WAIT:
                raise
            time.sleep(1.0)


class _Turn:
    """One talking job at a time on this computer: a lock file in the Assistant's own talking folder, held for as
    long as the with-block lasts. ok is False when the turn didn't come within `wait` seconds."""

    def __init__(self, wait):
        self.wait, self.cm, self.ok = wait, None, False

    def __enter__(self):
        try:
            TALK_HOME.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.cm = kitmod._held(TALK_HOME / TALK_TURN, self.wait)
        self.ok = self.cm.__enter__() is not False
        return self.ok

    def __exit__(self, *a):
        return self.cm.__exit__(*a)


_UNTIL = [0.0]            # when the watchdog stops this job's process, whatever it is doing
_JOB_WRITE = threading.Lock()


def _watchdog(kit, jid, name, finished):
    """The job's hard limit: past _UNTIL (the stated limits, added up) the job is written down as too long, and
    this process and everything it started are stopped. The transcriber's own app stops by itself a few seconds
    later (nothing touches its "alive" file any more)."""
    while not finished.wait(0.25):
        if time.time() <= _UNTIL[0]:
            continue
        with _JOB_WRITE:
            if finished.is_set():
                return
            log(f"{Path(kit).name}: the job turning its video into words ran past its limits and was stopped")
            _fail(kit, name, line_for("too_long"))
            _job_over(kit, jid, "problem")
            this_computer.stop_scripts()
            if JOB_ID.fullmatch(str(jid)):        # ours: this job's own scratch (the sound of their talk is never kept);
                shutil.rmtree(WORK / jid, ignore_errors=True)   # cmd_job's own tidy-up is never reached from here
            this_computer.stop_tree(os.getpid())  # a Mac: its whole group (popen_detached made it one); a PC: its tree
            os._exit(1)


def _work(kit, j, work, lim):
    """The work of one job. Returns nothing when the record is ready; raises JobProblem (or the transcriber's
    TalkProblem) with the state the page's line comes from."""
    vm, name = _vm(), j["video"]
    talk = talk_by_name(kit, name)
    if talk is None:
        raise JobProblem("not_in_folder")
    key, f = talk["key"], talk["facts"]
    bad = facts_problem(f)
    if bad:
        raise JobProblem(bad, f.get("refused", ""))
    tr = transcriber()
    if tr.name == "none":
        raise JobProblem(tr.why())

    def say(code):
        _step(kit, name, {"setup": OUR_JOB_WORDS["setup"][0], "asking": OUR_JOB_WORDS["asking"][0]}.get(code, JOB_WORDS["to_script"]))

    asked = time.time()
    with _Turn(lim["turn"]) as mine:
        if not mine:
            raise JobProblem("waited", "another shoot's talking job kept the turn")
        waited = time.time() - asked              # the two waits share ONE allowance (the plan's 900 s)
        tr.setup(time.time() + lim["setup"], say)
        _step(kit, name, JOB_WORDS["ready_video"])
        with vm.turn(max(0.0, lim["turn"] - waited)) as ok:
            if not ok:
                raise JobProblem("waited", "the computer's video turn didn't come")
            with _JOB_WRITE:                      # the waiting is over: from here the work's own limits count
                _UNTIL[0] = time.time() + lim["copy"] + lim["sound"] + lim["ask"] + lim["words"] + lim["grace"] + lim["spare"]
                j["until"] = _UNTIL[0]
                write_job(kit, j)
            pv = preview_path(kit, key)
            if os.path.lexists(pv) and not _copy_usable(pv):
                _set_copy_aside(pv)               # there, and no video: never played, never deleted; made again
            r = vm.preview_copy(talk["path"], pv, f=f, timeout=lim["copy"], wait=0)
            if not r.get("ok"):
                code = COPY_STATES.get(r.get("state"), "unreadable")
                if "too long" in str(r.get("detail") or ""):
                    code = "too_long"
                raise JobProblem(code, f"the small copy: {r.get('state')} {r.get('detail') or ''}")
            _step(kit, name, JOB_WORDS["to_script"])
            wav, how = _sound().speech_wav(talk["path"], work / "sound.wav", timeout=lim["sound"])
            if wav is None:
                code = "no_talking" if how == _sound()._NO_SOUND else ("too_long" if "too long" in str(how) else "unreadable")
                raise JobProblem(code, f"the sound: {how}")
        got = tr.run(wav, LANG, time.time() + lim["words"], say)
    words = got.get("words") if isinstance(got, dict) else None
    if not words:
        raise JobProblem("no_talking", "the transcriber gave no words")
    if _key_of(talk["path"]) != key:
        raise JobProblem("changed", "the video was exported again while its script was being made")
    j["key"] = key                                # the key the words were made from (for a save finished later)
    _save_words(kit, name, key, words, {"w": f.get("w"), "h": f.get("h"), "dur": f.get("length")},
                {"how": got.get("how"), "ondevice": got.get("ondevice")}, bool(j.get("again")))


def cmd_job(kit, jid):
    """The job's own process (started by start()). Holds the job's lock for as long as it lives."""
    kit = Path(kit)
    t0 = time.time()
    arrange._own_output()
    try:
        arrange.make_folder(kit / ".kit")
        f = open(kit / ".kit" / JOB_LOCK, "a", encoding="utf-8")
    except OSError:
        f = None
    got = None
    if f is not None:
        end = time.time() + 3.0                   # a page asking "is it running?" holds it for an instant: wait that out
        while True:
            got = this_computer.try_lock(f)
            if got is not False or time.time() > end:
                break
            time.sleep(0.05)
    if got is False:
        f.close()
        return 0                                  # another job's process has it
    work, wf = WORK / jid, None
    try:
        j = read_job(kit) or {}
        if j.get("id") != jid or j.get("state") != "queued" or not isinstance(j.get("video"), str):
            return 0
        name = j["video"]
        try:
            now = _slim(kit)
            wanted = now.get("status") == "working" and now.get("video") == name
        except Unreadable:
            wanted = True                         # can't tell just now: carry on, as asked
        if not wanted:
            # the page was already told this job stopped (it took too long to start), or they moved on: a job
            # that carried on now would turn the record ready by itself minutes later. It makes nothing.
            log(f"{kit.name}: a job started late for {name!r}; the record no longer waits for it, so it did nothing")
            _job_over(kit, jid, "problem")
            return 0
        lim = limits(j.get("length"))
        _UNTIL[0] = t0 + lim["turn"] + lim["ceiling"]
        j.update(state="running", pid=os.getpid(), t0=t0, t=time.time(), until=_UNTIL[0])
        write_job(kit, j)
        this_computer.awake_while()               # the computer stays awake while this job lives (a closed lid still stops it)
        finished = threading.Event()
        threading.Thread(target=_watchdog, args=(kit, jid, name, finished), daemon=True).start()
        line = None
        try:
            cleared = clear_stale_work()
            clear_stale_builds()
            if cleared:
                log(f"cleared the scratch of {len(cleared)} talking job(s) that were stopped part way")
            work.mkdir(parents=True, exist_ok=True)
            wf = open(work / ".lock", "a", encoding="utf-8")
            this_computer.try_lock(wf)
            (work / "owner.json").write_text(json.dumps({"pid": os.getpid(), "until": _UNTIL[0], "kit": kit.name}), encoding="utf-8")
            _work(kit, j, work, lim)
        except JobProblem as e:
            line = line_for(e.code)
            log(f"{kit.name}: the video could not be turned into words ({e.code}): {e.detail}")
        except (Busy, Unreadable) as e:
            line = str(e)
            log(f"{kit.name}: the video's words could not be saved ({e.__class__.__name__})")
        except Exception as e:  # noqa: BLE001  (a transcriber's TalkProblem, or anything else: plain words on the page, the real ones in the log)
            state = getattr(e, "state", None)
            line = line_for(state if isinstance(state, str) else "failed")
            log(f"{kit.name}: the video could not be turned into words ({e.__class__.__name__}: {state or ''}): "
                f"{getattr(e, 'detail', '') or str(e)[:600]}")
        with _JOB_WRITE:
            finished.set()
            if line:
                _fail(kit, name, line, j)
            _job_over(kit, jid, "problem" if line else "done")
        return 1 if line else 0
    finally:
        if wf is not None:
            try:
                this_computer.unlock(wf)
            except (OSError, ValueError):
                pass
            wf.close()
        if JOB_ID.fullmatch(jid):
            shutil.rmtree(work, ignore_errors=True)     # ours: this job's own scratch (the sound is never kept)
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


def cmd_setup(check=False):
    """`setup [--check]`: where "turning talking into words" stands on this computer, for the assistant (never
    read out as it is). Without --check it also does the setup (the first time: builds the small app)."""
    tr = transcriber()
    rep = tr.report()
    say(f"Turning talking into words on this {this_computer.COMPUTER}: {rep.get('how')}")
    if tr.name == "none":
        say(f"  Not possible here: {line_for(tr.why())}")
        return 1
    tools = rep.get("tools")
    if isinstance(tools, dict):
        say("  Apple's tools: " + ("found" if tools.get("found") else f"NOT found ({tools.get('why')})"
            if tools.get("found") is not None else "not looked for"))
    if "built" in rep:
        say("  The small app that listens: " + ("built" if rep["built"] else
            ("there, but from an older version: it will be built again" if rep.get("app_there") else "not built yet")))
    perm = rep.get("permission") or {}
    if "permission" in rep:
        say("  Speech Recognition, as last seen: " + (f"{perm.get('state')} ({perm.get('when')})" if perm.get("state") else
            "never asked yet (the Mac asks the first time a video is turned into a script; its box names Assistant "
            "Transcriber and the button is Allow)"))
    if check:
        return 0
    if not tr.needs_setup():
        say("Nothing to set up: it is ready.")
        return 0
    # the same turn a talking job holds while it sets up: two builds at once would each set the other's app
    # aside, and to macOS every rebuilt app is a new app (the permission would be asked again)
    with _Turn(SETUP_TURN_WAIT) as mine:
        if not mine:
            say("STOP: a talking video is being turned into a script right now, and that job does this setup "
                "itself when it is needed. Nothing was done. Run this again once it has finished.")
            return 3
        clear_stale_builds()
        return _setup_now(tr)


def _setup_now(tr):
    """The setup itself, inside the computer's talking turn."""
    if not tr.needs_setup():                      # asked again now the turn is held: a job may have just built it
        say("Nothing to set up: it is ready.")
        return 0
    try:
        tr.setup(time.time() + SETUP_LIMIT, None)
    except Exception as e:  # noqa: BLE001
        state = getattr(e, "state", None)
        log(f"setup: {e.__class__.__name__}: {state or ''}: {getattr(e, 'detail', '') or str(e)[:600]}")
        if state in ("no_tools", "licence", "old_tools", "pc", "old_mac"):
            say(f"STOP: {line_for(state)}")
        else:
            # never the page's own line here: it ends "Tell your assistant: set up talking reels.", which is
            # the very thing that was just run
            say("STOP: the small app that listens could not be built on this Mac"
                + (" in the time it is given." if state == "too_long" else "."))
            say(f"  The Mac's own words for why are at the end of the talking log: {LOG}")
            say("  Read them, and tell them plainly what is in the way. Running this again with nothing changed will "
                "stop the same way, so don't send them round again; talking reels wait until that is sorted out. "
                "Their photo reel, carousel and stories are not affected.")
        if state == "no_tools":
            say("  Apple's Command Line Tools are not on this Mac. Ask them first; only with their yes, run "
                "`xcode-select --install` (it opens Apple's own install window), wait for it to finish, then run this again.")
        elif state == "licence":
            say("  Apple's licence for its tools has not been accepted on this Mac. Ask them to open Xcode once and "
                "agree, then run this again.")
        elif state == "old_tools":
            say("  Apple's tools are older than this macOS. Ask them to run Software Update (it offers the newer "
                "Command Line Tools), then run this again.")
        return 2
    say("Set up. The first video turned into a script will make the Mac ask once about Speech Recognition (the box "
        "names Assistant Transcriber; the button is Allow).")
    return 0


def folder_mark(kit):
    """A short mark that moves whenever something the page shows changes without the record changing: a video
    added to, taken from or exported again in the Talking or Footage folder (their names, sizes and times, and
    whether each changed in the last couple of minutes, from plain listings: nothing is opened, nothing queued),
    or the numbered photo list."""
    kit = Path(kit)
    parts = []
    for folder in (TALKING, reel_page.FOOTAGE):
        for _, (name, p) in sorted(_plain_videos(kit, folder).items()):
            try:
                st = p.stat()
                # "changed just now" is part of the mark: a video that is still coming in is held back only
                # while it is recent, so the mark must move when that window ends, or a copy that was cut off
                # (or a file whose header can't be read) would be "still being copied" on the page for ever
                parts.append([folder, name, st.st_size, st.st_mtime_ns, reel_page._just_changed(p)])
            except OSError:
                parts.append([folder, name, None, None])
    parts.append(arrange.sheet_stamp(kit))
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


# ---------- what the page is given ----------

PAGE_REC = ("cut", "splits", "speeds", "video", "status", "step", "problem", "transcribed", "claude_cut", "photo_mode",
            "cap_pos", "cap_size", "captions", "updated")


def state_for_page(kit, rev=None, mark=None):
    """Hers (GET /talking): {ok, folder, videos, working, rec, pieces, zooms, shots, captions}, with ours beside
    it: the counter ("rev"), the numbered list's mark ("stamp"), the shoot's short name, the videos still coming
    in, and where the record's video stands ("video_state"). `rec` holds only what her page reads. A video is
    {key, name}: the name is shown as text, the key is what the page sends back. No path anywhere.
    With `rev` equal to the record's counter, only {ok, rev, mark, working, step} (a 30-minute talk's whole
    state is about half a megabyte, and the page asks every 3 seconds). "mark" moves when a video is added,
    taken away or exported again, or the photo list changes: the page sends back the mark it holds, and gets the
    whole state when either the counter or the mark has moved.
    When the record can't be read just now: {ok: False, why: "trouble", words} and nothing else; never an empty
    edit that looks as if theirs had gone."""
    kit = Path(kit)
    settle(kit)                                            # a job that is gone is told as plain words, once
    working = job_running(kit) or _starting(read_job(kit))
    try:
        slim = _slim(kit)
        now = _rev(slim)
        fmark = folder_mark(kit)
        if rev is not None and rev == now and (mark is None or mark == fmark):
            return {"ok": True, "rev": now, "mark": fmark, "working": working, "step": str(slim.get("step") or "")}
        entry = words_for(kit, slim.get("video"))
    except Unreadable:
        return {"ok": False, "why": "trouble", "words": TROUBLE, "working": working}
    eng = _engine()
    rec = _join(slim, entry)
    coming = []
    talks = list_talks(kit, coming)
    has = bool(rec.get("words"))
    pcs = eng.pieces(rec) if has else []
    foot = _plain_videos(kit, reel_page.FOOTAGE)
    shots = []
    for x in eng.shots(rec):
        x = dict(x)
        if x["v"]:
            hit = foot.get(_nfc(x["v"]).casefold())
            key = _key_of(hit[1]) if hit else None
            x["v"] = {"key": key, "name": hit[0]} if key else {"key": gone_key(x["v"]), "name": x["v"], "gone": True}
            if key:
                # its shape too, so the preview draws a wide video wide from the first frame (hers loads the
                # Footage list as the page starts; ours asks for that list only when the picker is opened)
                try:
                    fx = reel_page._facts(kit, hit[1], key)
                    w, h = int(fx.get("w") or 0), int(fx.get("h") or 0)
                except (OSError, TypeError, ValueError, AttributeError):
                    w = h = 0
                if w > 0 and h > 0:
                    x["v"]["w"], x["v"]["h"] = w, h
        shots.append(x)
    on_sheet = {x["n"] for x in arrange.sheet_rows(kit)}
    photos_gone = sorted({k for x in shots for k in x["ns"] if k not in on_sheet})
    out = {k: rec.get(k) for k in PAGE_REC if k in rec}
    for k in ("video", "status", "step", "problem"):       # text or nothing, whatever the record holds
        if k in out and not isinstance(out[k], str):
            out[k] = None if k == "video" else ""
    for k in ("transcribed", "updated"):
        if k in out and eng._num(out[k]) is None:
            out.pop(k)
    if "cap_pos" in out and not (isinstance(out["cap_pos"], dict) and all(eng._num(out["cap_pos"].get(k)) is not None for k in ("x", "y"))):
        out["cap_pos"] = None
    out["words"] = [{"w": w["w"], "start": w["start"], "end": w["end"]} for w in eng._words(rec)]
    out["sentences"] = eng._sents(rec, out["words"]) if has else []
    out["cut"] = [list(p) for p in (eng._pair(x) for x in _lst(rec, "cut")) if p]
    out["claude_cut"] = rec["claude_cut"] if isinstance(rec.get("claude_cut"), list) else None    # a list, even empty: cut
    out["captions"] = rec.get("captions") is not False
    out["cap_size"] = eng._num(rec.get("cap_size")) or 1
    out["photo_mode"] = rec.get("photo_mode") if rec.get("photo_mode") in ("me", "assistant") else ""
    info = rec.get("info") if isinstance(rec.get("info"), dict) else {}
    out["info"] = {"dur": info.get("dur") if info.get("dur") is not None else info.get("length")}
    earlier = rec.get("earlier") if isinstance(rec.get("earlier"), dict) else {}
    out["kept_for"] = sorted(k for k in earlier if isinstance(k, str))     # videos whose edit is kept
    return {"ok": True, "short": short_name(kit), "rev": now, "mark": fmark, "stamp": arrange.sheet_stamp(kit),
            "photos_gone": photos_gone,    # photo numbers on a stretch that are no longer in the numbered list
            "folder": talking_dir(kit).is_dir() and talking_ok(kit),
            "videos": [{"key": v["key"], "name": v["name"]} for v in talks],
            "coming": [{"name": c["name"]} for c in coming],
            "working": working, "video_state": video_state(kit, rec), "rec": out,
            "pieces": pcs, "zooms": eng.zooms(rec), "shots": shots,
            "captions": eng.captions(rec) if has else []}


# ---------- a save from the page, field by field (hers: server.py /talking/save) ----------

def _no(what):
    raise Refused(what)


def _int(v, what):
    if type(v) is not int:
        _no(what)
    return v


def _number(v, what):
    if type(v) is int:
        if abs(v) > FAR:                                    # float() of a very large whole number is a Python error
            _no(what)
    elif type(v) is not float or v != v or v in (float("inf"), float("-inf")):
        _no(what)
    return float(v)


def _range(r, n, what):
    """a and b of one entry: whole numbers, 0 <= a <= b < number of words."""
    a, b = _int(r.get("a"), what), _int(r.get("b"), what)
    if not (0 <= a <= b < n):
        _no(what)
    return a, b


def _f_cut(v, ctx):
    if not isinstance(v, list) or len(v) > MAX_CUTS:
        _no("cut")
    out = []
    for x in v:
        if not isinstance(x, list) or len(x) != 2:
            _no("cut")
        a, b = _int(x[0], "cut"), _int(x[1], "cut")
        if not (0 <= a <= b < ctx["n"]):
            _no("cut")
        out.append([a, b])
    return out


def _f_splits(v, ctx):
    if not isinstance(v, list):
        _no("splits")
    out = sorted({_int(x, "splits") for x in v})            # hers: no doubles, in order
    if len(out) > MAX_SPLITS or any(not (0 < x < ctx["n"]) for x in out):
        _no("splits")
    return out


def _f_speeds(v, ctx):
    if not isinstance(v, list) or len(v) > MAX_RANGES:
        _no("speeds")
    out = []
    for r in v:
        if not isinstance(r, dict) or set(r) - {"a", "b", "v"}:
            _no("speeds")
        a, b = _range(r, ctx["n"], "speeds")
        sp = _number(r.get("v"), "speeds")
        if sp == 1.0:
            continue                                        # hers: a speed of 1 is no speed-up, dropped
        if sp not in PAGE_SPEEDS:
            _no("speeds")
        out.append({"a": a, "b": b, "v": sp})
    return out


def _f_zooms(v, ctx):
    if not isinstance(v, list) or len(v) > MAX_RANGES:
        _no("zooms")
    out = []
    for r in v:
        if not isinstance(r, dict) or set(r) - {"a", "b", "kind"} or r.get("kind") not in ("punch", "zoom"):
            _no("zooms")
        a, b = _range(r, ctx["n"], "zooms")
        out.append({"a": a, "b": b, "kind": r["kind"]})
    return out


def _f_box(v, what):
    """Where they dragged a photo, or themselves: {x, y, w} as parts of the screen, held to hers; None for none."""
    if v is None:
        return None
    if not isinstance(v, dict) or set(v) != {"x", "y", "w"}:
        _no(what)
    x, y, w = (_number(v[k], what) for k in ("x", "y", "w"))
    return {"x": round(min(1.5, max(-0.5, x)), 4), "y": round(min(1.5, max(-0.5, y)), 4), "w": round(min(2.0, max(0.08, w)), 4)}


def _f_shots(v, ctx):
    if not isinstance(v, list) or len(v) > MAX_SHOTS:
        _no("shots")
    out = []
    for r in v:
        if not isinstance(r, dict) or set(r) - {"a", "b", "ns", "v", "from", "spot", "pos", "me"}:
            _no("shots")
        a, b = _range(r, ctx["n"], "shots")
        if r.get("spot") not in PLACE_SPOTS or not isinstance(r["spot"], str):   # behind and top are read, never saved
            _no("shots")
        ns = r.get("ns", [])
        if ns is None:
            ns = []
        if not isinstance(ns, list):
            _no("shots")
        ns = [_int(k, "shots") for k in ns][:MAX_NS]        # hers: more than 30 keeps the first 30, without a word
        # a number must be one of the kit's photos, or one a stored stretch already holds (the photo has since left
        # the list: the page was handed that stretch, so sending it back with the rest must not refuse the save)
        if any(k not in ctx["on_sheet"] and k not in ctx["stored_ns"] for k in ns):
            _no("shots")
        frm = r.get("from")
        frm = 0.0 if frm is None else _number(frm, "shots")
        if frm < 0:
            _no("shots")
        vkey, name, given = r.get("v"), None, None
        if isinstance(vkey, dict):                          # the state's own {key, name}, sent back as it came
            if set(vkey) - {"key", "name", "gone", "w", "h"}:      # w and h: the state's own, never kept
                _no("shots")
            given, vkey = vkey.get("name"), vkey.get("key")
            if given is not None and _engine()._video_name(given) is None:
                _no("shots")
        if vkey is not None:
            if not isinstance(vkey, str) or not KEY.fullmatch(vkey):
                _no("shots")
            name = ctx["footage"]().get(vkey)
            if name is None:
                # Not a key any Footage file has now. A file's key changes when it is exported again (or just
                # copied again) under the same name, and the page may still hold the old one: so first, whose
                # key was it? (the keys saves have seen, the stand-in keys of stored stretches, the name sent)
                was = ctx["known"]().get(vkey) or given
                cf = _nfc(was).casefold() if isinstance(was, str) else None
                hit = ctx["foot_names"]().get(cf) if cf else None
                if hit:
                    name = hit[0]                           # the same video, still in Footage under that name
                elif cf and cf in ctx["stored_v"]:
                    name = ctx["stored_v"][cf]              # gone, but a stored stretch already names it: it stays
                else:
                    continue      # hers: a Footage video since taken away (an Undo names it): that one stretch is left out
            ctx["seen"][vkey] = name
        elif not ns:
            _no("shots")
        out.append({"a": a, "b": b, "ns": [] if name else ns, "v": name, "from": round(frm, 3) if name else 0.0,
                    "spot": r["spot"], "pos": _f_box(r.get("pos"), "shots"), "me": _f_box(r.get("me"), "shots")})
    # hers: the page only ever sends stretches in order of their first word, none sharing a word with another
    # (everything it saves goes through setRange). So they are kept in that order, and a set that overlaps is
    # refused; unless the stored record already overlaps (one changed by hand): that one must stay saveable.
    out.sort(key=lambda x: x["a"])
    if not ctx.get("stored_overlap") and overlapping(out):
        _no("shots")
    return out


def overlapping(shots):
    """Do any two stretches share a word? (shots in order of their first word)"""
    return any(y["a"] <= x["b"] for x, y in zip(shots, shots[1:]))


def _f_cap_pos(v, ctx):
    if v is None:
        return None                                         # put back to where captions sit by themselves
    if not isinstance(v, dict) or set(v) != {"x", "y"}:
        _no("cap_pos")
    return {k: round(min(0.98, max(0.02, _number(v[k], "cap_pos"))), 4) for k in ("x", "y")}


def _f_cap_size(v, ctx):
    if v is None or (type(v) in (int, float) and v == 0):
        return 1.0                                          # hers: nothing, or 0, reads as 1 (as made)
    return round(min(3.0, max(0.4, _number(v, "cap_size"))), 2)


SAVE_FIELDS = {
    "cut": _f_cut, "splits": _f_splits, "speeds": _f_speeds, "zooms": _f_zooms, "shots": _f_shots,
    "cap_pos": _f_cap_pos, "cap_size": _f_cap_size,
    "captions": lambda v, ctx: v if type(v) is bool else _no("captions"),
    "photo_mode": lambda v, ctx: v if isinstance(v, str) and v in ("me", "assistant", "") else _no("photo_mode"),
}
CLEARS = {"zooms": ("moves", {}), "shots": ("photos", {})}     # hers: saving the newer field empties v23's


def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def _stored(rec, k):
    """What the record holds for a field, as a save would store it (to tell "nothing to write")."""
    eng = _engine()
    if k == "shots":
        return eng.shots(rec) if rec.get("shots") else []
    if k == "zooms":
        return eng.zooms(rec) if rec.get("zooms") else []
    if k == "captions":
        return rec.get("captions") if type(rec.get("captions")) is bool else None
    if k == "photo_mode":
        return rec.get("photo_mode")
    if k == "cap_pos":
        return rec.get(k)
    if k == "cap_size":
        v = rec.get(k)
        return float(v) if type(v) in (int, float) and v else 1.0
    return rec.get(k) or []


def save_from_page(kit, body):
    """One save from the talking reel page. Returns (status, answer). `body` is {"base": the counter the page
    last saw, "page": the page's own name, "saved": {any of her fields}} (a "kit" beside them is the route's).
    Every field is checked; one wrong field, or a field that isn't hers, refuses the whole save in plain words
    and nothing is written. Two things are done as hers because her own page can send them: more than 30 photos
    for one stretch keeps the first 30, and a stretch naming a Footage video that has since gone is left out.

    A save is taken only from a page that has seen the stored record (base == rev), or that is sending its own
    last save again (its answer never arrived). Anything else is told there is something newer, and given it:
    a page save can never wipe what the chat just wrote. Sending exactly what is stored writes nothing."""
    kit = Path(kit)
    if not isinstance(body, dict) or set(body) - {"kit", "base", "page", "saved"}:
        return _bad()
    base, page, sent = body.get("base"), body.get("page"), body.get("saved")
    if type(base) is not int or base < 0 or not isinstance(page, str) or not PAGE_ID.fullmatch(page):
        return _bad()
    if not isinstance(sent, dict) or not sent or set(sent) - set(SAVE_FIELDS):
        return _bad()
    foot = {}

    def footage():
        if "v" not in foot:
            foot["v"] = {v["key"]: v["name"] for v in reel_page.list_videos(kit)}
        return foot["v"]

    result = {}

    def fn(rec):
        eng = _engine()
        had = eng.shots(rec)
        stored_v = {_nfc(x["v"]).casefold(): x["v"] for x in had if x["v"]}
        keys = rec.get("shot_keys") if isinstance(rec.get("shot_keys"), dict) else {}
        memo = {}

        def known():
            if "k" not in memo:
                memo["k"] = {k: v for k, v in keys.items() if isinstance(k, str) and isinstance(v, str)}
                memo["k"].update({gone_key(n): n for n in stored_v.values()})
            return memo["k"]

        def foot_names():
            if "f" not in memo:
                memo["f"] = _plain_videos(kit, reel_page.FOOTAGE)
            return memo["f"]

        seen = {}
        ctx = {"n": len(eng._words(rec)), "on_sheet": {x["n"] for x in arrange.sheet_rows(kit)}, "footage": footage,
               "stored_ns": {k for x in had for k in x["ns"]}, "stored_v": stored_v, "known": known,
               "foot_names": foot_names, "seen": seen, "stored_overlap": overlapping(had)}
        clean = {k: SAVE_FIELDS[k](v, ctx) for k, v in sent.items()}
        rev = _rev(rec)
        if all(_same(_stored(rec, k), v) for k, v in clean.items()):
            result["same"] = True
            return False                                   # what is stored already: nothing to write
        src = rec.get("from") if isinstance(rec.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if REV_CHECK and base != rev and not own:
            result["newer"] = True
            return False
        for k, v in clean.items():
            rec[k] = v
            if k in CLEARS:
                rec[CLEARS[k][0]] = dict(CLEARS[k][1])
        if seen:                                           # which Footage video each key the page holds belongs to
            both = dict(keys)
            for k, v in seen.items():
                both.pop(k, None)
                both[k] = v
            rec["shot_keys"] = dict(list(both.items())[-SHOT_KEYS_KEPT:])
        return True

    try:
        change(kit, fn, src={"page": page, "base": base})
    except (Refused, TypeError, ValueError, KeyError, AttributeError, ArithmeticError):
        return _bad()                                      # nothing was written
    except Busy:
        return _bad(BUSY, 503, why="busy")
    except Unreadable:
        return _bad(TROUBLE, 503, why="trouble")           # the record is there and would not be read: left alone
    except OSError as e:                                   # a drive unplugged or full: plain words, never a Python error
        log(f"{kit.name}: a save from the page could not be written ({e.__class__.__name__}: {e})")
        return _bad(TROUBLE, 503, why="trouble")
    st = state_for_page(kit)
    if not st.get("ok"):
        return _bad(TROUBLE, 503, why="trouble")
    if result.get("newer"):
        return _bad(NEWER, 409, why="newer", state=st)
    return 200, st


# ---------- the chat's commands ----------

def merge_ranges(pairs):
    """Cuts in order, with any two that touch or overlap made one."""
    out = []
    for a, b in sorted(pairs):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _wnum(v):
    """A word or photo number from a file the assistant wrote: a whole number (3, or 3.0), never True or text."""
    if type(v) is int:
        return v
    if type(v) is float and v == v and abs(v) < FAR and v == int(v):
        return int(v)
    if isinstance(v, str) and 0 < len(v.strip()) <= 9 and all(c in "0123456789" for c in v.strip()):
        return int(v.strip())                              # "12" for 12, as hers takes it (she calls int())
    return None


def save_cut(kit, given, replace=False):
    """The assistant's cut. Returns (how many cuts, the reel's seconds). Stop when it can't be saved."""
    eng = _engine()
    out = {}

    def fn(rec):
        n = len(eng._words(rec))
        if not n:
            raise Stop(NO_SCRIPT)
        if not isinstance(given, dict) or not isinstance(given.get("cut"), list):     # no "cut" at all is a mistake, never an empty cut
            raise Stop('the file should be {"cut": [[first word, last word], ...], "why": [...]}')
        cuts = []
        for pair in given.get("cut") or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise Stop("each cut is two word numbers, [first, last]")
            x, y = _wnum(pair[0]), _wnum(pair[1])
            if x is None or y is None or not (0 <= x <= y < n):
                raise Stop(f"{pair[0]}-{pair[1]} isn't a range of word numbers (0 to {n - 1})")
            cuts.append([x, y])
        cuts = merge_ranges(cuts)
        # theirs: what is on the record is not the assistant's own last cut. That holds for an EMPTY list too:
        # after the assistant's cut, bringing every word back on the page is their own work (status says so)
        theirs = (bool(rec.get("cut")) or isinstance(rec.get("claude_cut"), list)) and rec.get("claude_cut") != _lst(rec, "cut")
        if theirs and not replace:
            raise Stop(THEIR_CUTS)
        why = given.get("why")
        why = [str(w)[:WHY_LONG] for w in (why if isinstance(why, list) else [])][:WHY_MOST]
        if theirs and rec.get("cut") != cuts:
            keep_replaced(rec, "cut --replace")
        rec["cut"], rec["claude_cut"], rec["claude_why"] = cuts, [list(c) for c in cuts], why
        out["n"], out["secs"] = len(cuts), eng.reel_seconds(eng.pieces(rec))
    change(kit, fn)
    return out["n"], out["secs"]


def save_place(kit, given, replace=False):
    """The assistant's photo stretches. Returns (stretches, photos). Stop when they can't be saved."""
    eng = _engine()
    out = {}

    def fn(rec):
        n = len(eng._words(rec))
        if not n:
            raise Stop(NO_SCRIPT)
        had = eng.shots(rec)
        try:
            shots = _stretches(kit, given, rec, n, eng)
        except Stop:
            if had and not replace:
                raise Stop(THEIR_PHOTOS)                   # as before: photos already there is said first
            raise
        if had and not replace:
            # the very set the assistant placed last, sent again (a run cut off or doubted): it landed, so there
            # is nothing to save and nothing to ask them. Anything else on the record stops, as ever.
            if not (rec.get("claude_shots") and _same(had, shots)):
                raise Stop(THEIR_PHOTOS)
        if had and not _same(had, shots):
            keep_replaced(rec, "place --replace")
        rec["shots"], rec["photos"], rec["claude_shots"] = shots, {}, True
        rec["claude_placed"] = shots_mark(shots)           # ours: which set it was, so status can tell if it still is
        out["n"], out["photos"] = len(shots), sum(len(x["ns"]) for x in shots)
    change(kit, fn)
    return out["n"], out["photos"]


def shots_mark(shots):
    """A short mark of one set of photo stretches (her claude_shots is a plain yes; this says which set)."""
    return hashlib.sha1(json.dumps(shots, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def placed_by(rec, shots):
    """Whose the photo stretches on the record are, for status: "assistant" (still the very set the assistant
    placed), "changed" (the assistant placed photos and the page has changed them since), or None (never placed
    by the assistant, or an older record that does not say which set it placed: no claim either way)."""
    if not shots or not rec.get("claude_shots") or not isinstance(rec.get("claude_placed"), str):
        return None
    return "assistant" if rec["claude_placed"] == shots_mark(shots) else "changed"


def _stretches(kit, given, rec, n, eng):
    """The photo stretches in a file the assistant wrote, checked one by one. Stop names the first that is wrong."""
    if not isinstance(given, dict) or not isinstance(given.get("shots", []), list):
        raise Stop('the file should be {"shots": [{"a": first word, "b": last word, "ns": [photo numbers], "spot": "pip"}, ...]}')
    on_sheet = {x["n"] for x in arrange.sheet_rows(Path(kit))}
    if not on_sheet:
        raise Stop("this shoot has no numbered photo list yet (kit.py sheet makes it)")
    keep = eng.kept(rec)
    rows = []
    for x in given.get("shots") or []:
        if not isinstance(x, dict) or _wnum(x.get("a")) is None or _wnum(x.get("b")) is None:
            raise Stop("each stretch needs a first word (a) and a last word (b), as word numbers")
        rows.append(x)
    shots, last = [], -1
    for x in sorted(rows, key=lambda x: _wnum(x["a"])):
        s0, e0 = _wnum(x["a"]), _wnum(x["b"])
        if not (0 <= s0 <= e0 < n) or s0 <= last:
            raise Stop(f"{s0}-{e0} isn't a range of word numbers that follows the one before it")
        if x.get("v"):
            raise Stop(f"{s0}-{e0}: place takes photos only, never a video (a video is theirs to add on the page)")
        raw = x.get("ns") if isinstance(x.get("ns"), list) else []
        ns = [_wnum(v) for v in raw]
        if not ns or None in ns or x.get("spot") not in PLACE_SPOTS:
            raise Stop(f"{s0}-{e0}: each stretch needs photo numbers and a spot (pip, full, center, corner)")
        missing = [k for k in ns if k not in on_sheet]
        if missing:
            raise Stop(f"{s0}-{e0}: photo {missing[0]} isn't one of this shoot's photos (the sheet's numbers are the page's)")
        if not any(keep[s0:e0 + 1]):
            raise Stop(f"{s0}-{e0}: every word there is cut, so the photo would never show. Cover kept words only")
        shots.append({"a": s0, "b": e0, "ns": ns[:MAX_NS], "v": None, "from": 0.0, "spot": x["spot"], "pos": None, "me": None})
        last = e0
    return shots


def cmd_show(kit):
    eng = _engine()
    rec = load(kit)
    words = eng._words(rec)
    if not words:
        raise Stop(NO_SCRIPT_SHOW)
    say(eng.RULES)
    say(f"\n{kit.name}: {rec.get('video')}, {len(words)} words. Each word is number:word (seconds).\n")
    for k, (s, e) in enumerate(eng._sents(rec, words)):
        line = " ".join(f"{i}:{words[i]['w']}" for i in range(s, e + 1))
        say(f"[{k}] {words[s]['start']:.1f}s  {line}")
    cut = [p for p in (eng._pair(x) for x in _lst(rec, "cut")) if p]
    if cut:
        say("\nAlready cut (theirs or yours): " + ", ".join(f"{x}-{y}" for x, y in cut))
    if video_state(kit, rec) == "changed":
        say("\n" + EXPORTED_AGAIN + ".")
    return 0


def sheet_line(kit):
    """The command that draws the numbered sheet (the page's numbers), ready to paste."""
    k = str(HERE / "kit.py")
    if this_computer.WINDOWS:
        return f"python {kitmod._pc_arg(Path(k).as_posix())} sheet {kitmod._pc_arg(kit.name)}"
    return f'python3 "{k}" sheet "{kit.name}"'


def cmd_photos(kit):
    eng = _engine()
    rec = load(kit)
    words = eng._words(rec)
    if not words:
        raise Stop(NO_SCRIPT_SHOW)
    say(eng.PHOTO_RULES)
    keep = eng.kept(rec)
    say(f"\n{kit.name}: the kept words, by sentence. Each word is number:word.\n")
    for k, (s0, e0) in enumerate(eng._sents(rec, words)):
        line = " ".join(f"{i}:{words[i]['w']}" for i in range(s0, e0 + 1) if keep[i])
        if line:
            say(f"[{k}] {line}")
    say(f"\nTheir photos: {kitmod.photos_dir(kit)}")
    say("See them on the reel maker's contact sheet (the numbers match the page):")
    say("  " + sheet_line(kit))
    if eng.shots(rec):
        say("\n" + PHOTOS_PLACED)
    if video_state(kit, rec) == "changed":
        say("\n" + EXPORTED_AGAIN + " or place.")
    return 0


def cmd_status(kit):
    """Where this shoot's talking reel stands, for the assistant (never read out as it is)."""
    eng = _engine()
    rec = load(kit)
    words = eng._words(rec)
    talks = list_talks(kit)
    say(f"{kit.name}: talking reel")
    say(f"  Talking folder: {len(talks)} video{'s' if len(talks) != 1 else ''}" + (": " + ", ".join(v["name"] for v in talks) if talks else
        " (none yet: on the page, Add my video opens the folder)"))
    if not rec.get("video"):
        say("  No video has been turned into a script yet (on the page: Edit my video).")
        return 0
    vs = video_state(kit, rec)
    say(f"  Video: {rec['video']}" + {"gone": " (no longer in the Talking folder)",
                                     "changed": " (exported again since its script was made: Edit my video again)"}.get(vs, ""))
    if job_running(kit):
        say("  Being turned into a script right now.")
    if rec.get("status") == "problem":
        say(f"  Stopped: {rec.get('problem')}")
    if not words:
        say("  No script yet.")
        return 0
    pcs = eng.pieces(rec)
    cut = _lst(rec, "cut")
    cut_by = "not cut yet" if not isinstance(rec.get("claude_cut"), list) and not cut else (
        "your cut" if rec.get("claude_cut") == cut else "their own cuts (ask before replacing them)")
    say(f"  Script: {len(words)} words, {sum(eng.kept(rec))} kept, {len(cut)} cuts ({cut_by}).")
    say(f"  The reel: {eng.reel_seconds(pcs):.1f} seconds in {len(pcs)} pieces.")
    sh = eng.shots(rec)
    say(f"  Photo stretches: {len(sh)}" + {"assistant": " (placed by you)",
                                          "changed": " (changed on the page since you placed them: ask before replacing them)"}.get(placed_by(rec, sh), "")
        + f"; who places them: {rec.get('photo_mode') or 'not chosen'}.")
    kept_for = sorted(k for k in (rec.get("earlier") if isinstance(rec.get("earlier"), dict) else {}) if isinstance(k, str))
    if kept_for:
        say("  Edits kept for other videos: " + ", ".join(kept_for))
    return 0


# ---------- Make it in CapCut: a job of its own (hers: a subprocess inside her server's request) ----------
# The page presses Make it in CapCut (start_make) and is given a job; a process of its own makes the reel
# (talking_rec.py make-job, which runs talking_make.py), writing how it is going to .kit/talking-make-job.json,
# which the page asks after (make_for_page) until it is done: Make my reel's way (reel_page.py). One make per
# shoot at a time (.kit/talking-make-job.lock, held for as long as the job lives); one reel of ANY kind made at a
# time on this computer (the job waits its turn for the same reel-make.lock the photo reel's job holds); at most
# reel_page.MAKE_LIMIT seconds, then a watchdog stops it and the page says so. Only the maker's one line, or a
# plain line of why not, ever reaches the page: never a path, never a Python error (those go to the log).
# A job that died after the project was written is told as made (its --status file says so): never "nothing
# was made" about a reel that is in CapCut.

MAKE_JOB = "talking-make-job.json"        # the newest make: {id, state, t, t0, pid, dry, words, project, problem}
MAKE_JOB_LOCK = "talking-make-job.lock"
MAKE_STATUS = "talking-make-status.json"  # what talking_make.py said happened, for the job that asked ("for")
TEST_STORE = "ASSISTANT_TEST_TALKING_STORE"   # tests only: a pretend CapCut projects folder; CapCut is never asked after
_MAKE_ROUTE = threading.Lock()
_MAKE_WRITE = threading.Lock()


def _maker():
    return kitmod.REEL_PY.parent / "talking_make.py"


def read_make(kit):
    try:
        j = json.loads((Path(kit) / ".kit" / MAKE_JOB).read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def write_make(kit, j):
    arrange.write_whole(Path(kit) / ".kit" / MAKE_JOB, j)


def make_running(kit):
    """Is a job making this shoot's talking reel right now? It holds .kit/talking-make-job.lock for as long as it
    lives (reel_page.job_running's way); nothing is made by asking. On a drive that has no locks, the job's own
    process number is asked after instead, for at most the limit and a minute."""
    p = Path(kit) / ".kit" / MAKE_JOB_LOCK
    try:
        if p.is_file():
            with open(p, "a", encoding="utf-8") as f:       # never written to: only looked at
                got = this_computer.try_lock(f, shared=True)
                if got is False:
                    return True
                if got:
                    this_computer.unlock(f)
                    return False
    except OSError:
        pass
    j = read_make(kit) or {}
    if j.get("state") not in ("queued", "running"):
        return False
    return time.time() - (_fnum(j.get("t0")) or _fnum(j.get("t"))) < reel_page.MAKE_LIMIT + 60 and arrange._pid_alive(j.get("pid"))


def _made_by(kit, jid):
    """What a job's maker said it made, when it had finished the project (its --status says so for this job)
    though the job was stopped before writing that down: {"project", "line"}; else None. Names only, no path."""
    try:
        st = json.loads((Path(kit) / ".kit" / MAKE_STATUS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(st, dict) and st.get("for") == jid and st.get("ok") and not st.get("dry") and isinstance(st.get("project"), str):
        line = st.get("line")
        return {"project": st["project"], "line": line if isinstance(line, str) and line else f"Made \"{st['project']}\" in CapCut."}
    return None


def make_for_page(kit):
    """The newest make as the page sees it: {id, state (queued, running, done, problem), dry, project, words,
    problem}, or None when this shoot's reel was never made from the page. `words` are the lines for her result
    box (the maker's one line). A job that says it is at work but is not (stopped, the computer turned off, past
    its time) is a problem in plain words; unless its project did reach CapCut, and then it is done. No path, no
    file name, no process number."""
    kit = Path(kit)
    j = read_make(kit)
    if not j or not isinstance(j.get("id"), str) or j.get("state") not in ("queued", "running", "done", "problem"):
        return None
    state, problem = j["state"], j.get("problem")
    words, project = [w for w in (j.get("words") or []) if isinstance(w, str)], j.get("project")
    if state in ("queued", "running"):
        began = _fnum(j.get("t0"))
        late = bool(began) and time.time() - began > reel_page.MAKE_LIMIT + reel_page.JOB_GRACE
        gone = not make_running(kit) and (state == "running" or j.get("pid") or time.time() - _fnum(j.get("t")) > JOB_BOOT)
        if late or gone:
            made = _made_by(kit, j["id"])
            if made:
                state, words, project = "done", [made["line"]], made["project"]
            else:
                state, problem = "problem", MAKE_WORDS["went_wrong"]
    return {"id": j["id"], "state": state, "dry": bool(j.get("dry")), "project": project if state == "done" else None,
            "words": words if state == "done" else [],
            "problem": (problem if isinstance(problem, str) and problem else MAKE_WORDS["went_wrong"]) if state == "problem" else None}


def note_made(kit, project):
    """Hers: the record keeps each reel that was made, and when ("made": [{"project", "when"}]). Saved quietly:
    the record's counter does not move (see change), so the page's next save and its Undo are as they were."""
    def fn(rec):
        made = [m for m in _lst(rec, "made") if isinstance(m, dict)]
        made.append({"project": str(project), "when": time.time()})
        rec["made"] = made
    change(kit, fn, quiet=True)


def start_make(kit, dry=False):
    """Make it in CapCut. (status, answer): {"ok": True, "job": make_for_page} when a job was started; else
    {"ok": False, "why", "words"} with the page's line and NOTHING made or changed. Refused at once, hers: no
    script yet, the talking video gone from its folder, everything cut; ours: its video still being turned into
    words, exported again since its script was made, or a make already at work for this shoot."""
    kit = Path(kit)
    try:
        code = make_problem(kit)
    except Unreadable:
        return 503, {"ok": False, "why": "trouble", "words": TROUBLE}
    if code:
        return (409 if code == "working" else 400), {"ok": False, "why": code, "words": make_line(code)}
    with _MAKE_ROUTE:
        j = read_make(kit) or {}
        if make_running(kit) or (j.get("state") == "queued" and not j.get("pid") and time.time() - _fnum(j.get("t")) < JOB_BOOT):
            return 409, {"ok": False, "why": "making", "words": JOB_WORDS["still_working"], "job": make_for_page(kit)}
        jid = os.urandom(6).hex()
        try:
            kitmod.hidden(kit)
            write_make(kit, {"id": jid, "state": "queued", "t": time.time(), "dry": bool(dry)})
        except OSError as e:
            log(f"{kit.name}: Make it in CapCut could not start ({e.__class__.__name__}: {e})")
            return 503, {"ok": False, "why": "trouble", "words": TROUBLE}
        try:
            fresh.LOGS.mkdir(parents=True, exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as out:
                # a Mac: a session of its own; a PC: no window, a process group of its own (as the photo reel's job)
                this_computer.popen_detached([sys.executable, str(HERE / "talking_rec.py"), "make-job", str(kit), "--id", jid],
                                             stdout=out, stderr=subprocess.STDOUT, **arrange._child_env())
        except OSError as e:
            log(f"{kit.name}: the talking reel's job could not be started: {e}")
            try:
                write_make(kit, {"id": jid, "state": "problem", "t": time.time(), "dry": bool(dry), "problem": MAKE_WORDS["went_wrong"]})
            except OSError:
                return 503, {"ok": False, "why": "trouble", "words": TROUBLE}
        return 200, {"ok": True, "job": make_for_page(kit)}


def _make_now(kit, jid, dry, deadline):
    """The work of one make: talking_make.py, held to the deadline with everything it starts. Returns what goes
    in the job: {state, words, project} or {state, problem}."""
    status = kit / ".kit" / MAKE_STATUS
    arrange.write_whole(status, {"for": jid, "pending": True})      # the maker keeps "for" when it writes what happened
    cmd = [sys.executable, str(_maker()), "make", "--kit", str(kit), "--status", str(status)]
    if dry:
        cmd.append("--dry-run")
    if os.environ.get(TEST_STORE):
        cmd += ["--store", os.environ[TEST_STORE], "--ignore-open"]
    left = deadline - time.time()
    if left <= 1:
        return {"state": "problem", "problem": MAKE_WORDS["went_wrong"]}
    try:
        rc, r_out, r_err = reel_page._run_bounded(cmd, left, cwd=str(_maker().parent))
    except subprocess.TimeoutExpired:
        log(f"{kit.name}: the talking reel's maker ran past its time and was stopped")
        made = _made_by(kit, jid)
        return {"state": "done", "words": [made["line"]], "project": made["project"]} if made else \
            {"state": "problem", "problem": MAKE_WORDS["went_wrong"]}
    try:
        st = json.loads(status.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    if not isinstance(st, dict) or st.get("pending") or st.get("for") != jid:
        st = {}
    lines = [w.strip() for w in (r_out or "").splitlines() if w.strip()]
    if rc != 0 or not st.get("ok"):
        log(f"{kit.name}: talking_make.py stopped ({rc}): {((r_out or '') + ' / ' + (r_err or '')).strip()[-600:]}")
        if isinstance(st.get("stop"), str):
            return {"state": "problem", "problem": make_line(st["stop"])}
        stop = next((w for w in lines if w.startswith("STOP")), "")
        # capcut.py's own STOP (no CapCut projects folder, say): its plain words with any place taken out, or hers
        said = reel_page._no_path(re.sub(r"^STOP:\s*", "", stop), [kit]) if stop else None
        known = {OUR_MAKE_WORDS[k][0] for k in CAPCUT_STOPS}      # only a line that is on our list reaches the page
        return {"state": "problem", "problem": said if said in known else MAKE_WORDS["went_wrong"]}
    shown = [x for x in (reel_page._no_path(w, [kit]) for w in lines) if x]       # the maker's one line; never a path
    return {"state": "done", "words": shown, "project": st.get("project") if not dry else None}


def _make_watchdog(kit, jid, deadline, finished):
    """The make's hard limit: at the deadline and reel_page.JOB_GRACE, a job still at work is written down (as
    made, when its project did reach CapCut; else as a problem), and this process, the maker it started and
    everything they started are stopped. The next Make it in CapCut can then go ahead."""
    if finished.wait(max(0.0, deadline + reel_page.JOB_GRACE - time.time())):
        return
    with _MAKE_WRITE:
        if finished.is_set():
            return
        j = read_make(kit) or {}
        if j.get("id") == jid and j.get("state") in ("queued", "running"):
            made = _made_by(kit, jid)
            if made:
                j.update(state="done", words=[made["line"]], project=made["project"], t=time.time())
            else:
                j.update(state="problem", problem=MAKE_WORDS["went_wrong"], t=time.time())
            try:
                write_make(kit, j)
            except OSError:
                pass
        log(f"{Path(kit).name}: the talking reel's job ran past its time and was stopped")
        for p in list(reel_page._CHILD):
            this_computer.stop_tree(p.pid)
        this_computer.stop_tree(os.getpid())      # a Mac: its whole group (popen_detached made it one); a PC: its tree
        os._exit(1)


def cmd_make_job(kit, jid):
    """The make's own process (started by start_make). Holds the make's lock for as long as it lives."""
    kit = Path(kit)
    t0 = time.time()
    arrange._own_output()
    try:
        arrange.make_folder(kit / ".kit")
        f = open(kit / ".kit" / MAKE_JOB_LOCK, "a", encoding="utf-8")
    except OSError:
        f = None
    got = None
    if f is not None:
        end = time.time() + 3.0                   # a page asking "is it running?" holds it for an instant: wait that out
        while True:
            got = this_computer.try_lock(f)
            if got is not False or time.time() > end:
                break
            time.sleep(0.05)
    if got is False:
        f.close()
        return 0                                  # another make's process has it
    try:
        j = read_make(kit) or {}
        if j.get("id") != jid or j.get("state") != "queued":
            return 0
        deadline = t0 + reel_page.MAKE_LIMIT
        j.update(pid=os.getpid(), t0=t0, t=time.time())
        write_make(kit, j)
        finished = threading.Event()
        threading.Thread(target=_make_watchdog, args=(kit, jid, deadline, finished), daemon=True).start()
        g = reel_page._hold_make_lock(deadline)   # one reel of any kind made at a time on this computer
        if g is None:
            with _MAKE_WRITE:
                finished.set()
                j.update(state="problem", problem=MAKE_WORDS["went_wrong"], t=time.time())
                write_make(kit, j)
            log(f"{kit.name}: another reel was being made for the whole of this make's time; nothing was made")
            return 1
        try:
            j.update(state="running", t=time.time())
            write_make(kit, j)
            try:
                res = _make_now(kit, jid, bool(j.get("dry")), deadline)
            except Exception as e:  # noqa: BLE001  (whatever happens, the page is told in plain words)
                log(f"{kit.name}: the talking reel's job failed: {e.__class__.__name__}: {str(e)[:300]}")
                res = {"state": "problem", "problem": MAKE_WORDS["went_wrong"]}
            with _MAKE_WRITE:
                finished.set()
                j.update(res, t=time.time())
                write_make(kit, j)
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


def read_json(path):
    try:
        return json.loads(kitmod.read_their_file(path))
    except (OSError, UnicodeDecodeError) as e:
        raise Stop(f"the file can't be read ({e.__class__.__name__})")
    except ValueError as e:
        raise Stop(f"the file isn't JSON that can be read ({e})")


def main(argv=None):
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, with_file in (("show", False), ("cut", True), ("photos", False), ("place", True), ("status", False)):
        s = sub.add_parser(name)
        s.add_argument("shoot", help="the shoot's name as the page wrote it, or a few words of it")
        if with_file:
            s.add_argument("--file", required=True, help="a UTF-8 JSON file (in the scratchpad)")
            s.add_argument("--replace", action="store_true", help="only after they said yes to replacing theirs")
    s = sub.add_parser("setup", help="where turning talking into words stands on this computer, and set it up")
    s.add_argument("--check", action="store_true", help="only say where it stands; set nothing up")
    s = sub.add_parser("job", help="(the Assistant's own) turn a video into words; started by Edit my video")
    s.add_argument("kit")
    s.add_argument("--id", required=True)
    s = sub.add_parser("make-job", help="(the Assistant's own) make the talking reel in CapCut; started by Make it in CapCut")
    s.add_argument("kit")
    s.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    if a.cmd in ("job", "make-job"):
        if not JOB_ID.fullmatch(a.id) or not (Path(a.kit) / ".kit").is_dir():
            return 1
        return cmd_job(Path(a.kit), a.id) if a.cmd == "job" else cmd_make_job(Path(a.kit), a.id)
    fresh.announce()
    if a.cmd == "setup":
        return cmd_setup(a.check)
    kit = find(a.shoot)
    try:
        if a.cmd == "show":
            return cmd_show(kit)
        if a.cmd == "photos":
            return cmd_photos(kit)
        if a.cmd == "status":
            return cmd_status(kit)
        if a.cmd == "cut":
            n, secs = save_cut(kit, read_json(a.file), a.replace)
            say(f"Saved: {n} cuts. The reel is now {secs:.1f} seconds of talking. The page shows it in a few seconds.")
            return 0
        if a.cmd == "place":
            n, m = save_place(kit, read_json(a.file), a.replace)
            say(f"Saved: {n} photo stretches, {m} photos. The page shows them in a few seconds.")
            return 0
    except Stop as e:
        say(f"STOP: {e}")
        return 2
    except (Busy, Unreadable) as e:
        say(f"STOP: {e}")
        return 2
    except OSError as e:                                   # the drive went, or is full: plain words, nothing half-written
        log(f"{kit.name}: {a.cmd} could not finish ({e.__class__.__name__}: {e})")
        say(f"STOP: {TROUBLE}")
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
