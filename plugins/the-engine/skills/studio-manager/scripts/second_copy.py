#!/usr/bin/env python3
"""A second copy of a finished backup, made afterwards, on another drive (Dustin, Nov 19: nothing is asked
before the copy; "they can choose whether they want to do a second backup or not", from the report).

    python3 second_copy.py "<the backup: its folder, or its records>" --to "<a drive, or a folder on one>"
                           [--check] [--json] [--always]

One layout, always, the card's own (Dustin, Oct 28: the second copy stays as the card wrote it):

    <to>/<the backup's folder name, "2026-11-19 thursday card">/<each file at its path on the card>
    <to>/<the backup's folder name>/_studio/manifest.json     (hidden; what backup.py --second leaves)

It is never sorted, settled or renamed. Each file is read from the card when the card is still in and the card
ledger says it is the card of this very backup; otherwise from the checked copy on their drive, wherever the
sort, a rename or the settle has put it. One run may use both, and a later run finishes a run that stopped.

The same promises as backup.py, whose own functions do the work here (imported, never copied):
  - nothing is deleted and nothing is written over: a file already at the destination is compared, never
    replaced; only this copy's own failed attempt may be written again
  - "checked" means a hash matched: what was read, what was read back from the new copy, and what the backup
    recorded for that file must all three agree. A source that no longer matches the backup's record is a
    problem, is not counted, and is not left under the photo's name on the second drive
  - log first: second-copy.json in the backup's records, written whole before the first byte and after every file
  - the backup's own manifest.json is changed ONCE, at the very end, only when every file is copied and checked
    (the manifest before is kept once as manifest.before-second-copy.json). Until then it says there is no
    second copy, so a copy that is running or has stopped can never switch off "Card safe to format"
  - safe to run twice, safe to cut off: a file recorded as checked and still there at its size is skipped

--check   only the questions asked before a byte is written; nothing is made or changed
--json    the last line printed is one JSON object {"ok", "state", "words"} (for the report's server)
--always  when the copy finishes, save this place as the second copy for every backup (the report's tick box)

Exit codes: 0 done (or nothing to do) · 1 problems · 2 refused before anything was written · 3 stopped part
way (run it again).
"""
import argparse
import errno
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backup  # noqa: E402  (copy_with_hash, sha256_of, identity, ours_to_redo, onto_itself, DIFFERS: used, never copied)
import cards  # noqa: E402  (the ledger: is the card that is in the card of this very backup?)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
from where import locate, same_place  # noqa: E402
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
LOCK = HOME / "second-copy.lock"            # one second copy at a time on this computer
RUNNING = HOME / "second-copy.running.json"  # who holds the lock: {pid, studio, card, to_name}; read by the report and by eject
RECORD = "second-copy.json"                 # in the backup's records: how far this copy has got
BEFORE = "manifest.before-second-copy.json"  # the backup's manifest as it was, kept once
MISSED = "second-missed.json"               # written by night.py: the saved second drive was not plugged in
MARGIN = 2 * 1024 ** 3                      # room kept free beyond the files themselves (as the backup keeps)

# Every line here may be shown on the report's page, so none of them ever holds a path: a drive is its name.
# All ours, all drafts for Dustin and Nicole.
OUR_WORDS = {
    "no_records": "I can't find that backup's records. Is the drive your photos are on plugged in?",
    "unfinished": "That backup isn't finished yet, so there's nothing to make a second copy of. Finish the backup first.",
    "problems": "That backup stopped with a problem, so I won't copy it yet. Sort out what its report says first.",
    "sample": "That backup was a sample of the card, for a test, so it gets no second copy.",
    "no_place": "I can't see that drive right now. Is it plugged in?",
    "onto_card": "That is the memory card itself. A second copy belongs on a drive that never gets formatted.",
    "a_card": "That is a memory card. A second copy belongs on a drive that never gets formatted.",
    "inside": "That is inside the backup's own folder. Pick a different drive for the second copy.",
    "same_drive": ("That is the drive your photos are already on ({drive}). A copy there is not a second place: "
                   "if that drive fails, both are gone. Pick a different drive."),
    "no_room": ("Not enough room on {drive}: this backup is {need} and there is {free} free. "
                "Free up about {short}, or pick another drive."),
    "another_there": ("{drive} already has a folder with this backup's name, holding a different backup. "
                      "So nothing gets mixed up, I won't copy into it."),
    "has_one": "This backup already has a second copy, on {drive}. Nothing to do.",
    "has_one_elsewhere": "This backup already has a second copy, on {drive}. I keep one second copy of a backup.",
    "busy": "A second copy is already being made. One at a time: try again when it's done.",
    "ready": "Ready: {n} files, {size}, to {drive}.",
    "copying": "Copying to {drive}: {done} of {total}.",
    "keep_card": "Keep your card in until this is done.",
    "done": "Second copy made on {drive}: {total} files, every one checked.",
    "from_drive": " It was made from the copy on {photos}, since the card wasn't in.",
    "some_from_drive": " {n} of them came from the copy on {photos}, since the card wasn't in for those.",
    "upright": " {n} video clip{s} the upright one{s2} from your drive.",
    "nothing_removed": "Nothing was removed. Press Make a second copy to carry on.",
    "stopped_dest": "{drive} stopped answering part way, at {done} of {total}. Is it still plugged in?",
    "stopped_full": "{drive} filled up part way, at {done} of {total}.",
    "stopped_photos": "The drive your photos are on stopped answering part way, at {done} of {total}. Is it still plugged in?",
    "stopped_readback": "A file did not read back from {drive} the way it was written, so I stopped at {done} of {total}. That drive may have a fault.",
    "stopped_killed": "The copy stopped before it finished, at {done} of {total}.",
    "differs": "{n} file{s} already on {drive} {are} different from your backup, so I left {them} alone.",
    "changed": "{n} photo{s} on your drive no longer match{es} what the backup recorded, so {they} {were} not copied.",
    "edited": ("{n} photo{s} on your drive {have} been changed since the backup (saved over, by an editing program for "
               "instance), so I can't make a checked copy of {them} from your drive. {They} {are} still on your drive. "
               "If the card still has {them}, put it in and press Make a second copy."),
    "edited_no_card": ("{n} photo{s} on {photos} {have} been changed since the backup (saved over, by an editing program "
                       "for instance), and the card isn't in, so I can't make a checked second copy from the drive alone. "
                       "Your photos on {photos} are still there. If the card still has them, put it in and press Make a "
                       "second copy. If the card has been formatted, this backup can't get a checked second copy any more."),
    "missing": "{n} photo{s} could not be found on your drive, so {they} {were} not copied.",
    "not_all": "{done} of {total} files are copied and checked so far.",
    "eject_wait": "A second copy is still being made from this card. It won't be long.",
    "missed": "Your second drive wasn't plugged in, so there's one copy for now. Plug it in and press Make a second copy.",
}


def say(msg):
    """Print, and never let a closed pipe stop a copy part way (as backup.py's)."""
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except OSError as e:
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise
        sys.stdout = open(os.devnull, "w", encoding="utf-8")


def plural(n, **forms):
    """The small words a count changes: s, are, them, they, were, es."""
    one = n == 1
    return {"n": f"{n:,}", "s": "" if one else "s", "s2": "" if one else "s", "are": "is" if one else "are",
            "have": "has" if one else "have", "They": "It" if one else "They",
            "them": "it" if one else "them", "they": "it" if one else "they", "were": "was" if one else "were",
            "es": "es" if one else "", **forms}


def write_whole(path, obj):
    """A record written whole or not at all: a scratch name of our own, then put in place."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()        # our own scratch copy, never the real file
        except OSError:
            pass
        raise


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- drives, by name

def volume_of(path):
    """The plugged-in drive a folder is on (this_computer.volumes(): path, name, shown, free), or None when it
    is on none of them (the computer's own disk on a Mac, say)."""
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        p = Path(path).expanduser()
    best = None
    for v in this_computer.volumes():
        try:
            top = Path(v["path"]).resolve()
        except OSError:
            continue
        if p == top or top in p.parents:
            if best is None or len(str(top)) > len(str(Path(best["path"]).resolve())):
                best = v
    return best


def drive_name(path):
    """How to say which drive a folder is on, never a path: "LaCie Rugged", or "this Mac" for its own disk."""
    v = volume_of(path)
    if v and not v.get("system"):
        return v.get("shown") or v.get("name") or "that drive"
    return this_computer.drive_words(path) or f"this {this_computer.COMPUTER}"


def same_drive(a, b):
    """Are two folders on one drive? By the list of plugged-in drives when both are on it; else by the
    computer's own number for the disk each is on."""
    va, vb = volume_of(a), volume_of(b)
    if va and vb:
        return same_place(va["path"], vb["path"])
    try:
        return os.stat(backup._nearest(a)).st_dev == os.stat(backup._nearest(b)).st_dev
    except (OSError, TypeError):
        return False


def room_on(path):
    """Free bytes where the copy would go: the plugged-in drive's own figure when it is one of them, else
    asked of the folder itself. None when it cannot be told."""
    v = volume_of(path)
    if v and v.get("free"):
        return int(v["free"])
    return this_computer.free_bytes(backup._nearest(path) or path)


def within(inner, outer):
    try:
        i, o = Path(inner).expanduser().resolve(), Path(outer).expanduser().resolve()
    except OSError:
        return False
    key = lambda p: os.path.normcase(str(p))
    return any(key(q) == key(o) for q in (i, *i.parents))


# ---------------------------------------------------------------- who is copying right now

def running():
    """The second copy being made on this computer right now ({pid, studio, card, to_name}), or None.
    The lock says whether one is alive (the computer lets go of it when its holder dies); the note beside it
    says which. Where this computer has no such lock, the holder's own number is asked instead."""
    info = read_json(RUNNING)
    if not isinstance(info, dict):
        return None
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with open(LOCK, "a+", encoding="utf-8") as f:
            got = this_computer.try_lock(f, shared=True)
            if got:
                this_computer.unlock(f)
                return None                     # nobody holds it: that note is from a copy that has ended
            if got is None and not this_computer.still_running(info.get("pid")):
                return None
    except OSError:
        return None
    return info


def reading_card(card):
    """True while a second copy is being made that reads this very card (eject_card.py asks before it lets go).
    When one is running from this card and its record cannot be read just now, the answer is True: wait."""
    info = running()
    if not info or not info.get("card"):
        return False
    try:
        same = Path(info["card"]).resolve() == Path(card).resolve()
    except OSError:
        same = same_place(str(info["card"]), str(card))
    if not same:
        return False
    rec = read_json(Path(info.get("studio") or "") / RECORD)
    if not isinstance(rec, dict):
        return True
    return rec.get("state") == "copying" and rec.get("reading", "card") == "card"


def free_words(gb):
    """ "1.2 TB free", "350 GB free": how the report's panel says a drive's room."""
    return f"{gb / 1000:.1f} TB free" if gb >= 1000 else f"{gb:,} GB free"


def offered_drives(studio):
    """The drives a second copy of this backup could go on, for the report's panel: every drive plugged in
    (studio_file.drives(): never the computer's own disk, a memory card or Time Machine), leaving out the drive
    the photos are on and the card. Each {"path", "name", "free"}; the page is only ever given name and free."""
    import studio_file
    studio = Path(studio)
    manifest = read_json(studio / "manifest.json", {}) or {}
    try:
        root, _ = locate(studio)
    except SystemExit:
        root = None
    out = []
    for d in studio_file.drives():
        if root is not None and (same_drive(root, d["path"]) or within(root, d["path"])):
            continue
        if manifest.get("source") and within(manifest["source"], d["path"]):
            continue
        out.append({"path": d["path"], "name": str(d["name"]), "free": free_words(int(d.get("free_gb") or 0))})
    return out


def missed(studio):
    """The line for the top of the report when the saved second drive was not plugged in for this backup
    (night.py wrote second-missed.json) and the backup still has no second copy; else None."""
    studio = Path(studio)
    if not (studio / MISSED).exists():
        return None
    manifest = read_json(studio / "manifest.json", {}) or {}
    if manifest.get("second"):
        return None
    note = read_json(studio / MISSED, {}) or {}
    if note.get("there"):
        # the drive was plugged in and the copy was refused before a byte was written (night.py kept the words:
        # ours, from this file, never a path). A copy that started and stopped is said by status(), not here.
        return str(note.get("words") or "") or None if not isinstance(read_json(studio / RECORD), dict) else None
    return OUR_WORDS["missed"]


# ---------------------------------------------------------------- where each file is on their drive now

def drive_places(root, studio):
    """card path -> the places, relative to root, that file may be at now, likeliest first: where the index
    says the photo is (the sort, a rename and the settle are all followed there), where the sort and rename
    logs say a sidecar went, and its card path itself. The set-aside leftovers are looked for by the caller,
    in the records. A wrong guess can never make a wrong copy: every file is checked against the backup's hash."""
    places = {}

    def add(key, rel):
        if key and rel:
            got = places.setdefault(key, [])
            rel = Path(rel).as_posix()
            if rel not in got:
                got.append(rel)

    for p in (read_json(studio / "index.json", {}) or {}).get("photos", []):
        add(p.get("original") or p.get("file"), p.get("file"))
    now = {}
    for m in (read_json(studio / "sort-log.json", {}) or {}).get("moves", []):
        if m.get("from") and m.get("to"):
            now[m["from"]] = m["to"]
    for entry in (read_json(studio / "rename-log.json", {}) or {}).get("renames", []):
        step = {m.get("from"): m.get("to") for m in entry.get("moves", []) if m.get("from") and m.get("to")}
        for key, at in list(now.items()):
            if at in step:
                now[key] = step[at]
    for key, at in now.items():
        add(key, at)
    return places


def find_on_drive(key, size, root, studio, places):
    """The file on their drive that was `key` on the card, at its recorded size, or None."""
    cands = [root / rel for rel in places.get(key, [])]
    cands += [studio / "from-the-card" / key, root / key]
    for c in cands:
        try:
            if c.is_file() and c.stat().st_size == size:
                return c
        except OSError:
            continue
    return None


def there_but_changed(key, root, studio, places):
    """True when the photo IS on their drive where the records say, at another size: it has been saved over
    since the backup (Lightroom writing a rating into a JPEG, say). Said as changed, never as "could not be
    found" (Nov 19 review: that read as lost photos, and they were there)."""
    cands = [root / rel for rel in places.get(key, [])]
    cands += [studio / "from-the-card" / key, root / key]
    for c in cands:
        try:
            if c.is_file():
                return True
        except OSError:
            continue
    return False


# ---------------------------------------------------------------- the questions asked before a byte is written

def rec_ok(studio, second, key, entry):
    """Is this file already on the second drive at its size, from an earlier run of this copy?"""
    try:
        return (second / Path(*key.split("/"))).stat().st_size == entry.get("size")
    except OSError:
        return False


class Refused(Exception):
    def __init__(self, state, words):
        super().__init__(words)
        self.state, self.words = state, words


def whole(manifest):
    """Is the backup finished, clean and not a sample? None when it is, else which refusal."""
    files = manifest.get("files") or {}
    if manifest.get("sample"):
        return "sample"
    if manifest.get("problems"):
        return "problems"
    if not files or not manifest.get("finished") or not all((v.get("dest") or {}).get("ok") for v in files.values()):
        return "unfinished"
    return None


def has_second(manifest):
    """The folder of a second copy this backup already has, every file checked; else None."""
    files = manifest.get("files") or {}
    if manifest.get("second") and files and all((v.get("second") or {}).get("ok") for v in files.values()):
        return manifest["second"]
    return None


def hashes_of(entry):
    """The hashes a right copy of this file may have: the card's own, and (for a video clip the backup turned
    upright) the turned one on their drive."""
    return {h for h in (entry.get("sha256"), entry.get("card_sha256")) if h}


def preflight(arg, to):
    """Everything asked before a byte is written. Returns the plan, or raises Refused(state, plain words).
    Makes and changes nothing."""
    try:
        root, studio = locate(arg)
    except SystemExit:
        raise Refused("no_records", OUR_WORDS["no_records"])
    manifest = read_json(studio / "manifest.json")
    if not isinstance(manifest, dict):
        raise Refused("no_records", OUR_WORDS["no_records"])
    why = whole(manifest)
    if why:
        raise Refused(why, OUR_WORDS[why])
    files = manifest["files"]
    session = manifest.get("session") or (studio.parent.name if studio.name == "_studio" else studio.name)
    place = this_computer.drive_root(to).expanduser()
    try:
        there = place.is_dir()
    except OSError:
        there = False
    if not there:
        raise Refused("no_place", OUR_WORDS["no_place"])
    place = place.resolve()
    second = place / this_computer.safe_name(session, limit=120)
    name = drive_name(place)
    had = has_second(manifest)
    if had:
        if same_place(str(Path(had)), str(second)):
            raise Refused("has_one", OUR_WORDS["has_one"].format(drive=drive_name(had)))
        raise Refused("has_one_elsewhere", OUR_WORDS["has_one_elsewhere"].format(drive=drive_name(had)))
    # never onto the card, never inside the backup, never onto the drive the photos are on
    card = Path(manifest["source"]) if manifest.get("source") else None
    card_in = False
    try:
        card_in = bool(card) and card.is_dir()
    except OSError:
        pass
    if card_in and (within(second, card) or (backup.onto_itself(card, second, "the second copy")
                                              and (backup._top_of_drive(card.resolve()) / "DCIM").is_dir())):
        raise Refused("onto_card", OUR_WORDS["onto_card"])
    # never onto a memory card: this backup's own or any other (one a camera has written to, wherever on it the
    # folder is). A card gets formatted, and may hold photos not backed up yet.
    import studio_file
    if studio_file.card_above(place) is not None:
        raise Refused("onto_card", OUR_WORDS["a_card"])
    shoots = [x.get("folder") for x in (read_json(studio / "shoots.json", {}) or {}).get("shoots", []) if x.get("folder")]
    if (within(second, studio) or (studio.name == "_studio" and within(second, root))
            or any(within(second, root / f) for f in shoots if isinstance(f, str))):
        raise Refused("inside", OUR_WORDS["inside"])
    if backup.onto_itself(root, second, "the second copy") or same_drive(root, place):
        raise Refused("same_drive", OUR_WORDS["same_drive"].format(drive=drive_name(root)))
    # a folder of that name already holding another backup's second copy
    theirs = read_json(second / "_studio" / "manifest.json")
    if isinstance(theirs, dict):
        other = theirs.get("files") or {}
        if set(other) != set(files) or any(not (hashes_of(other[k]) & hashes_of(files[k])) for k in files):
            raise Refused("another_there", OUR_WORDS["another_there"].format(drive=name))
    # room: what is still to copy, plus the margin the backup keeps
    need = 0
    for key, e in files.items():
        try:
            if (second / Path(*key.split("/"))).stat().st_size == e.get("size"):
                continue
        except OSError:
            pass
        need += max(0, e.get("size") or 0)
    free = room_on(place)
    if need and free is not None and free < need * 1.05 + MARGIN:
        raise Refused("no_room", OUR_WORDS["no_room"].format(
            drive=name, need=backup.human(need), free=backup.human(free), short=backup.human(need * 1.05 + MARGIN - free)))
    if running():
        raise Refused("busy", OUR_WORDS["busy"])
    if not card_in:
        # The card is not in, so every file must come from their drive. A photo that has been saved over since
        # the backup can never be copied and checked from there: said now, in words that say what happened,
        # rather than after copying the rest and calling those photos "not found". (Sizes only, a moment.)
        places = drive_places(root, studio)
        edited = [k for k, e in files.items()
                  if not (rec_ok(studio, second, k, e))
                  and find_on_drive(k, e.get("size"), root, studio, places) is None
                  and there_but_changed(k, root, studio, places)]
        if edited:
            raise Refused("edited", OUR_WORDS["edited_no_card"].format(photos=drive_name(root), **plural(len(edited))))
    return {"arg": str(arg), "root": root, "studio": studio, "manifest": manifest, "session": session, "place": place,
            "second": second, "name": name, "card": card if card_in else None,
            "bytes": sum(max(0, e.get("size") or 0) for e in files.values())}


# ---------------------------------------------------------------- the copy

class Stop(Exception):
    """The copy cannot go on right now (a drive went away, or filled up). Run again to finish."""
    def __init__(self, words_key):
        super().__init__(words_key)
        self.key = words_key


def readable(path):
    try:
        with open(path, "rb") as f:
            f.read(1)
        return True
    except OSError:
        return False


def set_aside_unchecked(dst):
    """A copy that did not pass its check never stays under the photo's name on the second drive: it goes
    back to the unfinished name it was written under (which every later attempt writes afresh, and which no
    backup ever counts as a file). Our own just-written copy only; nothing of theirs is ever moved."""
    try:
        this_computer.replace(dst, dst.with_name(dst.name + ".studio-partial"))
    except OSError:
        pass


def copy_all(plan, always=False):
    """Make the copy. Returns (exit code, the line for the page)."""
    arg, manifest, second, name = plan["arg"], plan["manifest"], plan["second"], plan["name"]
    files = manifest["files"]
    total = len(files)
    where = {"root": plan["root"], "studio": plan["studio"]}
    where["places"] = drive_places(where["root"], where["studio"])

    def relocate():
        """The backup may settle while this runs (its shoots move up, its records move): find it again."""
        try:
            where["root"], where["studio"] = locate(arg)
        except SystemExit:
            try:
                where["root"], where["studio"] = locate(where["studio"])
            except SystemExit:
                return False
        where["places"] = drive_places(where["root"], where["studio"])
        info = read_json(RUNNING)
        if isinstance(info, dict) and info.get("pid") == os.getpid() and info.get("studio") != str(where["studio"]):
            try:
                write_whole(RUNNING, dict(info, studio=str(where["studio"])))
            except OSError:
                pass
        return True

    # the card: only when it is in, answers, and the ledger says it is the card of this very backup
    card = plan["card"]
    if card is not None:
        try:
            ok = cards.answers(card)
            _, held = cards.check(card) if ok else (None, None)
            if not held or Path(held["studio"]).resolve() != where["studio"].resolve():
                card = None
        except (Exception, SystemExit):  # noqa: BLE001  (anything unreadable: the card is not used)
            card = None

    # the record, log first. A copy to this same place that stopped is carried on; one to another place is kept aside.
    rec_path = where["studio"] / RECORD
    rec = read_json(rec_path)
    if isinstance(rec, dict) and not same_place(str(Path(rec.get("to") or "")), str(second)):
        try:
            this_computer.rename_new(rec_path, rec_path.with_name(f"second-copy.older-{datetime.now():%Y%m%d-%H%M%S}.json"))
        except OSError:
            pass
        rec = None
    if not isinstance(rec, dict):
        rec = {"to": str(second), "to_name": name, "started": datetime.now().isoformat(timespec="seconds"), "files": {}}
    rec.update({"to_name": name, "state": "copying", "total": total, "bytes": plan["bytes"], "problems": [],
                "reading": "card" if card is not None else "drive", "pid": os.getpid(),
                "photos_name": drive_name(where["root"])})
    rec.setdefault("files", {})
    rec.pop("finished", None)

    def counts():
        ok = [r for r in rec["files"].values() if r.get("ok")]
        rec["done"] = len(ok)
        rec["from_card"] = sum(1 for r in ok if r.get("from") == "card")
        rec["from_drive"] = sum(1 for r in ok if r.get("from") == "drive")

    def save(line=None):
        counts()
        if line is not None:
            rec["line"] = line
        if not where["studio"].is_dir():
            relocate()
        write_whole(where["studio"] / RECORD, rec)

    save(OUR_WORDS["copying"].format(drive=name, done=f"{sum(1 for r in rec['files'].values() if r.get('ok')):,}", total=f"{total:,}"))
    try:
        (second / "_studio").mkdir(parents=True, exist_ok=True)
    except OSError:
        return finish_stopped(rec, save, "stopped_dest", name, total)
    backup.hide(second / "_studio")

    pause = 0.0
    try:   # for the tests only: a wait after each file, so a copy of small pretend photos can be cut off part way
        pause = float(os.environ.get("STUDIO_SECOND_COPY_PAUSE_FOR_TESTS") or 0)
    except ValueError:
        pass
    differs, changed, missing, edited = [], [], [], []
    t0 = time.time()
    stop = None
    for key in sorted(files):
        entry = files[key]
        size = entry.get("size")
        dst = second / Path(*key.split("/"))
        r = rec["files"].get(key)
        try:
            # checked on an earlier run and still there at its size: skip
            if r and r.get("ok") and dst.is_file() and dst.stat().st_size == size:
                continue
            if os.path.lexists(dst) and not backup.ours_to_redo(r, dst):
                # something is already there that is not our own failed copy: compared, never written over
                same = False
                try:
                    same = dst.is_file() and dst.stat().st_size == size and backup.sha256_of(dst) in hashes_of(entry)
                except OSError:
                    pass
                if same:
                    rec["files"][key] = {"ok": True, "from": "there", "note": "already there, identical"}
                else:
                    rec["files"][key] = {"ok": False, "note": backup.DIFFERS}
                    differs.append(key)
                save()
                continue
            only_drive = False
            while True:   # at most twice for one file: the card, then their drive
                from_card = card is not None and not only_drive
                if from_card:
                    src, want = card / Path(*key.split("/")), entry.get("card_sha256") or entry.get("sha256")
                else:
                    src, want = find_on_drive(key, size, where["root"], where["studio"], where["places"]), entry.get("sha256")
                    if src is None and relocate():
                        src = find_on_drive(key, size, where["root"], where["studio"], where["places"])
                    if src is None:
                        if not where["root"].is_dir():
                            raise Stop("stopped_photos")
                        if only_drive:
                            changed.append(key)      # the card's differs and the drive has none: said as changed
                        elif there_but_changed(key, where["root"], where["studio"], where["places"]):
                            rec["files"][key] = {"ok": False, "note": "changed on the drive since the backup", "left": backup.identity(dst)}
                            edited.append(key)
                        else:
                            rec["files"][key] = {"ok": False, "note": "not found on the drive", "left": backup.identity(dst)}
                            missing.append(key)
                        break
                if rec.get("reading") != ("card" if from_card else "drive"):
                    rec["reading"] = "card" if from_card else "drive"
                    save()
                try:
                    read_hash, back_hash = backup.copy_with_hash(src, dst)
                except OSError as e:
                    rec["files"][key] = {"ok": False, "note": f"{e.__class__.__name__}: {e.strerror or e}", "left": backup.identity(dst)}
                    if not readable(src):
                        if from_card:
                            card = None        # the card came out (or went quiet): the rest comes from their drive
                            say("  the card is not answering any more; carrying on from the copy on the drive")
                            continue
                        if not where["root"].is_dir():
                            raise Stop("stopped_photos")
                        missing.append(key)
                        break
                    raise Stop("stopped_full" if e.errno == errno.ENOSPC else "stopped_dest")
                if read_hash != back_hash:
                    # the new copy does not read back as it was written: that drive is not to be trusted today
                    rec["files"][key] = {"ok": False, "note": "the copy did not read back the same", "left": backup.identity(dst)}
                    raise Stop("stopped_readback")
                if not want or read_hash != want:
                    # The source is no longer what the backup recorded: not counted, and not left under the
                    # photo's name on the second drive. The card's file gets one more try, from their drive.
                    set_aside_unchecked(dst)
                    rec["files"][key] = {"ok": False, "note": f"the {'card' if from_card else 'drive'}'s file no longer matches the backup's record",
                                         "left": backup.identity(dst)}
                    if from_card:
                        rec.setdefault("notes", []).append(f"{key}: the card's file no longer matches the backup's record")
                        only_drive = True
                        continue
                    changed.append(key)
                    break
                rec["files"][key] = {"ok": True, "from": "card" if from_card else "drive"}
                if not from_card and entry.get("card_sha256") and entry["card_sha256"] != entry.get("sha256"):
                    rec["files"][key]["turned"] = True     # the upright clip from their drive, 36 bytes off the card's
                break
        except Stop as halt:
            stop = halt.key
            try:
                save()
            except OSError:
                pass
            break
        done = sum(1 for x in rec["files"].values() if x.get("ok"))
        save(OUR_WORDS["copying"].format(drive=name, done=f"{done:,}", total=f"{total:,}"))
        if done % 25 == 0 or done == total:
            say(f"  second copy: {done}/{total} files, {time.time() - t0:.0f} s")
        if pause:
            time.sleep(pause)

    if stop:
        return finish_stopped(rec, save, stop, name, total)
    counts()
    if differs or changed or missing or edited or rec["done"] != total:
        parts = []
        if differs:
            parts.append(OUR_WORDS["differs"].format(drive=name, **plural(len(differs))))
        if changed:
            parts.append(OUR_WORDS["changed"].format(**plural(len(changed))))
        if edited:
            parts.append(OUR_WORDS["edited"].format(**plural(len(edited))))
        if missing:
            parts.append(OUR_WORDS["missing"].format(**plural(len(missing))))
        parts.append(OUR_WORDS["not_all"].format(done=f"{rec['done']:,}", total=f"{total:,}"))
        rec["problems"] = ([f"{k} already exists on the second drive and is different. Not overwritten; check it by hand." for k in differs]
                           + [f"{k} no longer matches what the backup recorded. Not copied." for k in changed]
                           + [f"{k} has been changed on the drive since the backup. Not copied." for k in edited]
                           + [f"{k} could not be found on the drive. Not copied." for k in missing])
        rec["state"] = "stopped"
        rec["finished"] = datetime.now().isoformat(timespec="seconds")
        save(" ".join(parts))
        for p in rec["problems"][:20]:
            say("PROBLEM: " + p)
        say(rec["line"])
        return 1, rec["line"]

    # Every file is copied and checked. Only now does the backup's own manifest learn of the second copy,
    # in one whole write, with the manifest before kept beside it once.
    if not where["studio"].is_dir():
        relocate()
    studio = where["studio"]
    mpath = studio / "manifest.json"
    fresh = read_json(mpath)
    if not isinstance(fresh, dict) or set(fresh.get("files") or {}) != set(files) or any(
            not rec["files"].get(k, {}).get("ok") for k in fresh["files"]):
        rec["state"] = "stopped"
        save(OUR_WORDS["stopped_killed"].format(done=f"{rec['done']:,}", total=f"{total:,}") + " " + OUR_WORDS["nothing_removed"])
        say("STOPPED: the backup's records changed while the copy ran. Run it again.")
        return 3, rec["line"]
    before = studio / BEFORE
    if not before.exists():
        try:
            tmp = before.with_name(f".{before.name}.{os.getpid()}.tmp")
            tmp.write_bytes(mpath.read_bytes())
            if not this_computer.rename_new(tmp, before):
                tmp.unlink()
        except OSError:
            pass
    fresh["second"] = str(second)
    for k, e in fresh["files"].items():
        e["second"] = {"ok": True}
        if rec["files"][k].get("turned"):
            e["second"]["turned"] = True
    fresh["second_made"] = datetime.now().isoformat(timespec="seconds")
    write_whole(mpath, fresh)
    try:
        write_whole(second / "_studio" / "manifest.json", fresh)
        backup.hide(second / "_studio")
    except OSError:
        pass
    upright = sum(1 for x in rec["files"].values() if x.get("turned"))
    line = OUR_WORDS["done"].format(drive=name, total=f"{total:,}")
    photos = drive_name(where["root"])
    if rec["from_drive"] and not rec["from_card"]:
        line += OUR_WORDS["from_drive"].format(photos=photos)
    elif rec["from_drive"]:
        line += OUR_WORDS["some_from_drive"].format(n=f"{rec['from_drive']:,}", photos=photos)
    if upright:
        line += OUR_WORDS["upright"].format(n=f"{upright:,}", s=" is" if upright == 1 else "s are", s2="" if upright == 1 else "s")
    if always:
        try:
            import studio_file
            sf = studio_file.load()
            if studio_file.set_drive(sf.setdefault("drives", {}), "second", str(plan["place"])):
                studio_file.save(sf)
                say("Saved: every backup from now on gets a second copy there.")
        except Exception as e:  # noqa: BLE001  (the copy is made and checked; the setting can be said again)
            say(f"(could not save it as the usual second copy: {e.__class__.__name__})")
    for script in ("first_look.py", "report_page.py"):     # the report now says there is a second copy
        try:
            subprocess.run([sys.executable, str(HERE / script), str(studio)], capture_output=True, timeout=600,
                           **({"creationflags": 0x08000000} if this_computer.WINDOWS else {}))
        except (OSError, subprocess.SubprocessError):
            pass
    rec["state"] = "done"
    rec["finished"] = fresh["second_made"]
    rec["upright"] = upright
    rec["reading"] = None
    try:
        save(line)
    except OSError:
        pass                 # the copy is made, checked and in the manifest; only this note of it could not be written
    say(line)
    return 0, line


def finish_stopped(rec, save, key, name, total):
    rec["state"] = "stopped"
    rec["finished"] = datetime.now().isoformat(timespec="seconds")
    done = sum(1 for x in rec["files"].values() if x.get("ok"))
    line = OUR_WORDS[key].format(drive=name, done=f"{done:,}", total=f"{total:,}") + " " + OUR_WORDS["nothing_removed"]
    try:
        save(line)
    except OSError:
        rec["line"] = line
    say("STOPPED: " + line.replace(OUR_WORDS["nothing_removed"], "Nothing was removed. Run it again to carry on."))
    return 3, line


def status(studio):
    """How this backup's second copy stands, for the report's page: {"state": "none"|"copying"|"done"|"stopped",
    "done", "total", "name", "card" (is it reading the card right now), "line"}. Never a path."""
    studio = Path(studio)
    manifest = read_json(studio / "manifest.json", {}) or {}
    n = len(manifest.get("files") or {})
    had = has_second(manifest)
    rec = read_json(studio / RECORD)
    if not isinstance(rec, dict):
        rec = None
    alive = False
    if rec and rec.get("state") == "copying":
        info = running()
        try:
            alive = bool(info) and Path(info.get("studio") or "").resolve() == studio.resolve()
        except OSError:
            alive = False
    if had:
        # the backup's own manifest is what says a second copy is made; the record only adds the honest line
        mine = bool(rec) and same_place(str(Path(rec.get("to") or "")), str(Path(had)))
        if not (mine and alive):     # (alive: every file is checked and it is writing the report; a moment more)
            return {"state": "done", "done": n, "total": n, "name": drive_name(had), "card": False,
                    "line": str(rec.get("line") or "") if mine and rec.get("state") == "done" else ""}
    if not rec:
        return {"state": "none", "done": 0, "total": n, "name": "", "card": False, "line": ""}
    state = rec.get("state")
    done, total, name = int(rec.get("done") or 0), int(rec.get("total") or 0), str(rec.get("to_name") or "")
    line = str(rec.get("line") or "")
    stopped = OUR_WORDS["stopped_killed"].format(done=f"{done:,}", total=f"{total:,}") + " " + OUR_WORDS["nothing_removed"]
    if state == "copying" and not alive:
        state, line = "stopped", stopped
    elif state == "done":
        state, line = "stopped", stopped   # the record says done but the backup's own manifest does not: never called made
    return {"state": state if state in ("copying", "stopped") else "none", "done": done, "total": total, "name": name,
            "card": state == "copying" and rec.get("reading") == "card", "line": line}


def main():
    ap = argparse.ArgumentParser(
        description="A second copy of a finished backup, on another drive, in the card's own layout. Nothing is deleted or written over.",
        epilog="Exit codes: 0 done (or nothing to do), 1 problems, 2 refused before anything was written, 3 stopped part way (run it again).")
    ap.add_argument("backup", help="the backup: its folder, where it was, or its records")
    ap.add_argument("--to", required=True, help="the drive (or a folder on it) the second copy goes on")
    ap.add_argument("--check", action="store_true", help="only ask the questions; write nothing")
    ap.add_argument("--json", action="store_true", help="end with one JSON line {ok, state, words}")
    ap.add_argument("--always", action="store_true", help="when done, make this the second copy of every backup")
    a = ap.parse_args()

    def out(code, state, words):
        if a.json:
            say(json.dumps({"ok": code == 0, "state": state, "words": words}))
        sys.exit(code)

    try:
        plan = preflight(a.backup, a.to)
    except Refused as r:
        nothing = r.state == "has_one"
        say(("" if nothing else "REFUSED, before anything was written: ") + r.words)
        out(0 if nothing else 2, r.state, r.words)
    ready = OUR_WORDS["ready"].format(n=f"{len(plan['manifest']['files']):,}", size=backup.human(plan["bytes"]), drive=plan["name"])
    if a.check:
        say("OK. " + ready + " Nothing written (a check).")
        out(0, "ready", ready)

    HOME.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, "a+", encoding="utf-8")
    got = this_computer.try_lock(lock)
    for _ in range(10):
        # The report's page asks "is one running?" by trying this same lock for an instant (running()). A try
        # that lands in that instant is not another copy: ask again for a second before believing it.
        if got is not False:
            break
        time.sleep(0.1)
        got = this_computer.try_lock(lock)
    if got is False:
        lock.close()
        say("REFUSED, before anything was written: " + OUR_WORDS["busy"])
        out(2, "busy", OUR_WORDS["busy"])
    try:
        write_whole(RUNNING, {"pid": os.getpid(), "studio": str(plan["studio"]), "card": str(plan["card"]) if plan["card"] else None,
                              "to_name": plan["name"], "started": datetime.now().isoformat(timespec="seconds")})
        this_computer.awake_while()      # the computer stays awake for as long as this copy runs
        say(f"Second copy of {plan['session']} onto {plan['name']}: {len(plan['manifest']['files']):,} files, {backup.human(plan['bytes'])}.")
        code, line = copy_all(plan, always=a.always)
    finally:
        if got:
            this_computer.unlock(lock)
        lock.close()
    out(code, {0: "done", 1: "problems", 3: "stopped"}.get(code, "stopped"), line)


if __name__ == "__main__":
    main()
