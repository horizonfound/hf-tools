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

<shoot> is the name as the page wrote it in the line they pasted, or a few words of it. Write the two files in
the scratchpad, never in their folders, and hand them over with --file (never on the command line).

Where things are kept, all in the kit's hidden folder (nothing of theirs is in the computer's own Assistant folder):
    .kit/talking.json            the record: which video, their cuts, splits, speeds, zooms, photo stretches,
                                 captions. Her field names. Saved whole or not at all, one writer at a time
                                 (.kit/talking.lock), with a counter ("rev") that moves on with every change.
    .kit/talking.prev.json       the record as it was before the last change
    .kit/talking-words.json      every word they said with its times, the sentences and the video's facts, for
                                 each video that was turned into a script. Written once per video, never by a
                                 save from the page, so every save stays small (a 30-minute talk is about 4,500
                                 words).
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

A Mac and a PC: every file is read and written as UTF-8; nothing here needs a Mac.
"""
import argparse
import hashlib
import json
import os
import sys
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
EDIT_FIELDS = ("cut", "claude_cut", "claude_why", "splits", "speeds", "zooms", "shots", "moves", "photos", "claude_shots")
KEPT_WHEN_REPLACED = ("cut", "shots", "zooms", "splits", "speeds")
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
THEIR_CUTS = "they've already made their own cuts on the page. Ask before replacing them (then run again with --replace)"
THEIR_PHOTOS = "they already have photos placed. Ask before replacing them (then run again with --replace)"
PHOTOS_PLACED = "They already have photos placed: ask before replacing them (then place with --replace)."


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


def change(kit, fn, src=None, stale_why="its script was made again"):
    """Read the record, change it (fn(record with its words); return False to leave it alone, raise to refuse),
    and save it as one step no other command or page can get in the middle of. The version before is kept
    beside it. Nothing is written when fn changed nothing. An accepted change moves the counter ("rev") on by
    one. The words themselves are never written from here (put_words does that, once per video).
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


def put_words(kit, name, key, words, info=None, more=None, again=False):
    """A video has just been turned into words: keep them (once, in the words file, the version before beside
    it), and make the record ready on that video. Words made again for a video that already had a script start
    its edit afresh (what was there is kept in "replaced"): the word numbers belong to the old words.
    `key` is the video's key as it was when the words were made (video.key); `more` may hold "how", "ondevice".
    `again=True` is Edit my video pressed again on a video that already had its script: the edit starts afresh
    even when the words come back the same (hers always does; the plan's "replaced"). Without it, the same words
    for the same file change nothing, so a job that runs twice is harmless.

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


def job_running(kit):
    """Is a job turning this shoot's video into words right now? The job holds .kit/talking-job.lock for as long
    as it lives (reel_page.job_running's way); nothing is made by asking."""
    p = Path(kit) / ".kit" / JOB_LOCK
    try:
        if not p.is_file():
            return False
        with open(p, "a", encoding="utf-8") as f:           # never written to: only looked at
            got = this_computer.try_lock(f, shared=True)
            if got is False:
                return True
            if got:
                this_computer.unlock(f)
    except OSError:
        pass
    return False


def folder_mark(kit):
    """A short mark that moves whenever something the page shows changes without the record changing: a video
    added to, taken from or exported again in the Talking or Footage folder (their names, sizes and times, from
    plain listings: nothing is opened, nothing queued), or the numbered photo list."""
    kit = Path(kit)
    parts = []
    for folder in (TALKING, reel_page.FOOTAGE):
        for _, (name, p) in sorted(_plain_videos(kit, folder).items()):
            try:
                st = p.stat()
                parts.append([folder, name, st.st_size, st.st_mtime_ns])
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
    working = job_running(kit)
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
            if set(vkey) - {"key", "name", "gone"}:
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
    return out


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
               "foot_names": foot_names, "seen": seen}
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
        theirs = bool(rec.get("cut")) and rec.get("claude_cut") != rec.get("cut")
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
        if had and not replace:
            raise Stop(THEIR_PHOTOS)
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
        if had and not _same(had, shots):
            keep_replaced(rec, "place --replace")
        rec["shots"], rec["photos"], rec["claude_shots"] = shots, {}, True
        out["n"], out["photos"] = len(shots), sum(len(x["ns"]) for x in shots)
    change(kit, fn)
    return out["n"], out["photos"]


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
        say("\nNOTE: their talking video was exported again since this script was made, so these word times belong to "
            "the old file. Ask them to press Edit my video again on the page before you cut.")
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
    say(f"  Photo stretches: {len(sh)}" + (" (placed by you)" if sh and rec.get("claude_shots") else "")
        + f"; who places them: {rec.get('photo_mode') or 'not chosen'}.")
    kept_for = sorted(k for k in (rec.get("earlier") if isinstance(rec.get("earlier"), dict) else {}) if isinstance(k, str))
    if kept_for:
        say("  Edits kept for other videos: " + ", ".join(kept_for))
    return 0


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
    a = ap.parse_args(argv)
    fresh.announce()
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
