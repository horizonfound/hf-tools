#!/usr/bin/env python3
"""A second copy of a finished backup, made afterwards, on another drive (Dustin, Nov 19: nothing is asked
before the copy; "they can choose whether they want to do a second backup or not", from the report).

    python3 second_copy.py "<the backup: its folder, or its records>" --to "<a drive, or a folder on one>"
                           [--check] [--json]
    python3 second_copy.py follow "<the backup>" [--json]     bring its second copy in line after a rename or a join
    python3 second_copy.py follow --all                       every second copy that was waiting for its drive

One layout for every new second copy: the photo drive's own (Nicole, Nov 23: "it should look just like the main
drive"). The same shoot folders, the same Photos and Videos folders inside them, the same photo names:

    <to>/<each shoot's folder>/<each photo, named as on the photo drive>
    <to>/.studio-second/<the backup's name>/manifest.json        (hidden: this copy's own records)
    <to>/.studio-second/<the backup's name>/from-the-card/...     (hidden: what the sort set aside, as on the photo drive)

  - Made only once the backup is sorted (night.py makes it after the settle). A backup still in its day folder
    is mirrored with that day folder; when it settles, follow() moves the mirror's shoots up the same way.
  - Each file is read from the card when the card is still in and the card ledger says it is the card of this
    very backup; otherwise from the checked copy on their drive. A video clip the backup turned upright is always
    read from their drive, since the card still has it sideways: the mirror holds what the photo drive holds.
  - The hash that proves every file of a mirror is the backup's `sha256` for it: the hash of the file as it is on
    the photo drive (for a turned clip that is the turned file's; `card_sha256` is never used for a mirror).
  - Only the files the backup itself copied are mirrored. Anything they add to a shoot's folder afterwards (edits,
    exports) is not copied.

A second copy made before Nov 23 is in the card's own layout (<to>/<the backup's name>/DCIM/..., records in a
hidden _studio inside it). It is left exactly as it is, never converted, and a copy of that kind that stopped
part way is finished in that same layout. second-copy.json says which: "layout": "main", or nothing (the card's).

The same promises as backup.py, whose own functions do the work here (imported, never copied):
  - nothing is deleted and nothing is written over: a file already at the destination is compared, never
    replaced; only this copy's own failed attempt may be written again. A folder on the second drive with a
    shoot's name that this copy did not make is refused in plain words before a byte is written
  - "checked" means a hash matched: what was read, what was read back from the new copy, and what the backup
    recorded for that file must all three agree. A source that no longer matches the backup's record is a
    problem, is not counted, and is not left under the photo's name on the second drive
  - log first: second-copy.json in the backup's records, written whole before the first byte and after every file
    (each file with where it is on the second drive, each folder this copy made); and before each file's first
    byte, a small note of which file and the name it is going under (second-copy.going.json), so a copy killed
    before the record heard of a file that had landed finds it again
  - the backup's own manifest.json is changed ONCE, at the very end, only when every file is copied and checked
    (the manifest before is kept once as manifest.before-second-copy.json). Until then it says there is no
    second copy, so a copy that is running or has stopped can never switch off "Card safe to format"
  - safe to run twice, safe to cut off: a file recorded as checked and still there at its size is skipped

follow(): after a shoot is renamed or two are joined on the photo drive, the mirror takes the same folders and
names. Renames on the second drive only (never a copy, never a delete), each written to second-follow-log.json
before it happens, each file proved the same file afterwards by its identity on the drive (its hash when identity
cannot prove it), names checked against the folder's own listing, nothing ever taken over. Run twice it does
nothing; a run cut off is finished by the next. With the second drive not plugged in it notes "waiting" in
second-copy.json; the report says so, and the next command that sees the drive (the report's own status check, a
backup, or follow --all) does it. The same goes for a rename that came while this computer's one second-copy lock
was held by something else (noted in second-follow-later.json, a file of its own: the record is only ever written
by whoever holds the lock), for a follow that was cut off (found by its own identity, never by "something has
that name"; no two files are ever on record at one place), and for one stopped by something in the way.

--check   only the questions asked before a byte is written; nothing is made or changed
--json    the last line printed is one JSON object {"ok", "state", "words"} (for the report's server)
--always  only with REMEMBER_SECOND on: save this place as the second copy for every backup. Off since Nov 23
          (Nicole: the second drive is asked each time), so the option is taken and nothing is saved

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
import unicodedata
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

LAYOUT_MAIN = "main"        # the second copy looks like the photo drive: shoot folders and photo names (Nicole, Nov 23)
LAYOUT_CARD = "card"        # a second copy made before Nov 23: the card's own folders and names, left as it is
MIRROR_RECORDS = ".studio-second"   # the hidden folder on the second drive that keeps a mirror's own records. Not
#                                     ".studio": nothing that looks for a backup's records may ever take a copy for one
FOLLOW_LOG = "second-follow-log.json"   # in the backup's records: every rename made on the second drive, written first
FOLLOW_KEPT = 6             # how many finished runs the follow log keeps in full (older ones keep their counts)
GOING = "second-copy.going.json"   # in the backup's records: the one file being copied right now and the name it is going
#                                   under, written before its first byte, so a copy killed before the record heard of
#                                   the file can find it again (and give it its new name after a rename)
LATER = "second-follow-later.json"  # in the backup's records: a rename came while this computer's one second-copy lock
#                                   was held by something else, so this copy still has to follow. A note of its own:
#                                   the record itself is never written by anyone who does not hold the lock
MOVING = ".studio-moving"   # the ending of a name a file steps aside under for a moment, when names go round in a ring
REMEMBER_SECOND = False     # Nicole, Nov 23: the second drive is asked each time. True brings back "Do this after
#                             every backup" (the report's tick box, --always, and a saved second drive used by itself)

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
    "folder_there": ("{drive} already has a folder called {folder} that isn't part of this second copy. So nothing "
                     "gets mixed up, I won't copy into it. Rename that folder, or pick another drive."),
    "unsorted": ("This backup's photos aren't sorted into shoots yet, and the second copy is laid out like your "
                 "shoots. Finish the backup first."),
    "mid_rename": ("One of this backup's shoots is part way through being renamed. Tell the Assistant, and once "
                   "that's finished the second copy can be made."),
    "mid_join": ("Shoots in this backup are part way through being put in one folder. Tell the Assistant, and once "
                 "that's finished the second copy can be made."),
    "has_one": "This backup already has a second copy, on {drive}. Nothing to do.",
    "has_one_elsewhere": "This backup already has a second copy, on {drive}. I keep one second copy of a backup.",
    "busy": "A second copy is already being made. One at a time: try again when it's done.",
    "ready": "Ready: {n} files, {size}, to {drive}.",
    "copying": "Copying to {drive}: {done} of {total}.",
    "keep_card": "Keep your card in until this is done.",
    "done": "Second copy made on {drive}: {total} files, every one checked.",
    "like_main": " It has the same folders and photo names as {photos}.",
    "card_layout": ("This second copy was made the earlier way: its folders and names are the memory card's, "
                    "not your shoots'. Every file in it is checked all the same."),
    "from_drive": " It was made from the copy on {photos}, since the card wasn't in.",
    "some_from_drive": " {n} of them came from the copy on {photos}, since the card wasn't in for those.",
    "upright": " {n} video clip{s} the upright one{s2} from your drive.",
    "nothing_removed": "Nothing was removed. Press Make a second copy to carry on.",
    "stopped_dest": "{drive} stopped answering part way, at {done} of {total}. Is it still plugged in?",
    "stopped_full": "{drive} filled up part way, at {done} of {total}.",
    "stopped_photos": "The drive your photos are on stopped answering part way, at {done} of {total}. Is it still plugged in?",
    "stopped_readback": "A file did not read back from {drive} the way it was written, so I stopped at {done} of {total}. That drive may have a fault.",
    "stopped_killed": "The copy stopped before it finished, at {done} of {total}.",
    "stopped_folder": ("{drive} has a folder called {folder} that isn't part of this second copy, so I stopped at "
                       "{done} of {total}."),
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
    "saved_unused": ("You had {drive} saved for a second copy after every backup. I ask each time now instead: "
                     "press Make a second copy whenever you want one."),
    "not_remembered": "(Not saved for every backup: the second drive is asked each time now.)",
    "follow_done": "Your second copy on {drive} has the same folders and names as {photos} again.",
    "follow_waiting": ("Your second copy on {drive} still has the folders and names from before. "
                       "Plug {drive} in and it will catch up."),
    "follow_busy": "A second copy is being made right now; it takes the new names itself before it finishes.",
    "follow_later": ("Your second copy on {drive} still has the folders and names from before. Another second copy "
                     "is being made right now; this one catches up as soon as that is done."),
    "follow_part_way": ("Your second copy on {drive} was part way through taking its new folders and names. "
                        "It finishes by itself in a moment."),
    "follow_problem": ("I couldn't give your second copy on {drive} the same folders and names as {photos}: {why} "
                       "Nothing was removed or written over. Tell the Assistant and it'll sort it out."),
    "follow_folder": "a folder called {folder} is already there that isn't part of the copy.",
    "follow_in_way": "something else already has a name one of its files should take.",
    "follow_gone": "{n} file{s} of the copy {are} not where {they} {were} left.",
    "follow_unproved": "{n} file{s} could not be proved the same after the move.",
    "follow_cant": "something unexpected stopped it.",
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
    if note.get("asked_each_time"):
        # a second drive was saved for every backup, and since Nov 23 it is asked each time: said once, on the
        # report of the first backup after that (night.py wrote the note), for as long as it has no second copy
        return str(note.get("words") or "") or None
    if note.get("there"):
        # the drive was plugged in and the copy was refused before a byte was written (night.py kept the words:
        # ours, from this file, never a path). A copy that started and stopped is said by status(), not here.
        return str(note.get("words") or "") or None if not isinstance(read_json(studio / RECORD), dict) else None
    return OUR_WORDS["missed"]


# ---------------------------------------------------------------- where each file is on their drive now

def drive_places(root, studio, keys=()):
    """card path -> the places, relative to root, that file may be at now, likeliest first: where the index
    says the photo is (the sort, a rename and the settle are all followed there), where the sort and rename
    logs say a sidecar went, and its card path itself. With `keys` (the manifest's), a sidecar is also looked
    for beside its photo under the photo's name now, which is where the sort, a rename and a join all put it,
    whatever log they kept: that place comes FIRST for a sidecar, since a join keeps a log this does not read and
    an older log entry may by now name a place another shoot's sidecar has taken. The set-aside leftovers are
    looked for by the caller, in the records. A wrong guess can never copy wrong bytes (every file is checked
    against the backup's hash), but in a copy that looks like the photo drive the place also decides the NAME the
    copy gets, so when more than one place fits, on_main() takes the one whose hash is this file's."""
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
    if keys:
        beside = {Path(p["original"]).with_suffix("").as_posix(): p["file"]
                  for p in (read_json(studio / "index.json", {}) or {}).get("photos", []) if p.get("original") and p.get("file")}
        for key in keys:
            photo = beside.get(Path(key).with_suffix("").as_posix())
            if photo and Path(key).suffix.lower() == ".xmp":
                rel = Path(photo).with_suffix(Path(key).suffix).as_posix()
                got = places.setdefault(key, [])
                if rel in got:
                    got.remove(rel)
                got.insert(0, rel)
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


# ---------------------------------------------------------------- a copy that looks like the photo drive

def main_view(root, studio, keys=()):
    """How this backup lies on the photo drive right now: the folder its paths are relative to, its records,
    the day folder's name when it has not settled ("" once it has), and where each file may be."""
    root, studio = Path(root), Path(studio)
    return {"root": root, "studio": studio, "prefix": root.name if studio.name == "_studio" else "",
            "places": drive_places(root, studio, keys)}


def on_main(key, entry, view):
    """Where this file of the backup is on the photo drive now, or None when it is nowhere the records know:
    {"kind": "shoot" (in a shoot's folder) or "aside" (set aside in the records by the sort),
     "rel": its place there, "src": the file itself when it is there at its recorded size (else None),
     "changed": it is there at another size (saved over since the backup)}."""
    size = entry.get("size")
    root, studio = view["root"], view["studio"]
    cands = [("shoot", rel, root / rel) for rel in view["places"].get(key, [])]
    cands.append(("aside", key, studio / "from-the-card" / Path(*key.split("/"))))
    other, fits, seen = None, [], set()
    for kind, rel, at in cands:
        if str(at) in seen:
            continue
        seen.add(str(at))
        try:
            if at.is_file():
                if at.stat().st_size == size:
                    fits.append((kind, rel, at))
                else:
                    other = other or (kind, rel)
        except OSError:
            continue
    if len(fits) > 1:
        # More than one place holds a file of this size (after a join, an older log may name a place that another
        # photo or sidecar has since taken). Size alone would put this file's copy under the other one's name:
        # the place whose hash is this file's is the one, and no two files are ever given the same place.
        hashes, claimed = view.setdefault("hashes", {}), view.setdefault("claimed", {})
        right = []
        for f in fits:
            try:
                if str(f[2]) not in hashes:
                    hashes[str(f[2])] = backup.sha256_of(f[2])
            except OSError:
                continue
            if hashes[str(f[2])] == entry.get("sha256"):
                right.append(f)
        if right:
            pick = next((f for f in right if claimed.get(str(f[2]), key) == key), right[0])
            claimed[str(pick[2])] = key
            fits = [pick]
    if fits:
        kind, rel, at = fits[0]
        return {"kind": kind, "rel": Path(rel).as_posix(), "src": at, "changed": False}
    if other:
        return {"kind": other[0], "rel": Path(other[1]).as_posix(), "src": None, "changed": True}
    return None


def mirror_rel(loc, view, mirror_name):
    """A file's place on the second drive, from its place on the photo drive: the same shoot folder and name
    (inside the day folder too, while the backup has not settled); what the sort set aside goes in the mirror's
    own hidden records, as it sits in the backup's hidden records on the photo drive."""
    if loc["kind"] == "aside":
        return f"{MIRROR_RECORDS}/{mirror_name}/from-the-card/{loc['rel']}"
    return (view["prefix"] + "/" if view["prefix"] else "") + loc["rel"]


def fold(name):
    """A name as a drive that ignores capital letters, and spells an accent either way, would compare it."""
    return unicodedata.normalize("NFC", str(name)).casefold()


class Names:
    """What is in each folder, by name, read from the folder's own listing (never exists(), which says yes to
    another spelling on a drive that ignores capital letters) and kept in step as files are moved."""

    def __init__(self):
        self.dirs = {}

    def of(self, folder):
        k = str(folder)
        if k not in self.dirs:
            try:
                self.dirs[k] = {fold(n): n for n in os.listdir(folder)}
            except OSError:
                self.dirs[k] = None          # no such folder (yet)
        return self.dirs[k]

    def has(self, path):
        """The name, as it is spelled there, of whatever holds this name in its folder (in any spelling), or None."""
        path = Path(path)
        return (self.of(path.parent) or {}).get(fold(path.name))

    def exact(self, path):
        """True only when this very name, letter for letter, is in its folder (an accent may be spelled either
        way on a Mac, as rename_shoot.on_disk allows)."""
        got = self.has(path)
        if got is None:
            return False
        name = Path(path).name
        return got == name or (not this_computer.WINDOWS and unicodedata.normalize("NFC", got) == unicodedata.normalize("NFC", name))

    def moved(self, src, dst):
        src, dst = Path(src), Path(dst)
        a = self.of(src.parent)
        if a is not None:
            a.pop(fold(src.name), None)
        b = self.of(dst.parent)
        if b is None:
            self.dirs[str(dst.parent)] = b = {}
        b[fold(dst.name)] = dst.name

    def forget(self):
        self.dirs = {}


def proved(path, ident, entry):
    """Is the file at path the very file that was moved there? By its identity on the drive (the same file
    number, size and modified time as just before the move: a rename never rewrites a byte), and when that
    cannot prove it (a drive that numbers no file, or a move made by a run that was cut off), by reading it in
    full against the hash the backup recorded. Never a pass without one or the other."""
    try:
        st = os.stat(path)
    except OSError:
        return False
    if ident and ident[0] and [st.st_ino, st.st_size, st.st_mtime_ns] == list(ident):
        return True
    want = entry.get("sha256")
    try:
        return bool(want) and st.st_size == entry.get("size") and backup.sha256_of(path) == want
    except OSError:
        return False


def same_ident(path, ident):
    """Is the file at path the one that had this identity (file number, size, modified time)? Never a guess:
    False when there is no identity to go by."""
    try:
        st = os.stat(path)
    except OSError:
        return False
    return bool(ident and ident[0]) and [st.st_ino, st.st_size, st.st_mtime_ns] == list(ident)


def same_hash(path, entry):
    """Is the file at path, read in full, the one the backup recorded?"""
    want = entry.get("sha256")
    try:
        return bool(want) and os.stat(path).st_size == entry.get("size") and backup.sha256_of(path) == want
    except OSError:
        return False


def place_key(rel):
    return "/".join(fold(x) for x in Path(rel).parts)


def unit_of(rel, prefix):
    """The shoot's own folder in a place on the drive: the first folder, or the first inside the day folder
    while the backup has not settled. None for a file that sits in no folder, or in the hidden records."""
    parts = Path(rel).parts
    depth = len(Path(prefix).parts) if prefix else 0
    if not parts or parts[0] == MIRROR_RECORDS or len(parts) <= depth + 1:
        return None
    return "/".join(parts[:depth + 1])


def ours(rec, top):
    return fold(top) in {fold(x) for x in rec.get("folders") or []}


def align(place, mirror_name, view, studio, rec, files, save):
    """Give the files of this copy that are already on the second drive the folders and names the photo drive
    has now. Returns {"moved", "problems" (plain words, never a path), "gone", "unproved"}.

    Renames on the second drive only. A whole shoot folder that only changed its name goes in one step, as on
    the photo drive; then each file whose name differs. Everything is written to the follow log before it is
    done, checked against the folders' own listings, and nothing is ever taken over: a name that is in use by
    something that is not this copy's stops the run before a file moves. Names that go round in a ring (photo 3
    takes photo 5's name and photo 5 takes photo 3's, after a join) step aside under a name of their own first.
    Safe to run twice; a run that was cut off is finished here, from the log and from what is really there."""
    place = Path(place)
    names = Names()
    out = {"moved": 0, "problems": [], "gone": 0, "unproved": 0}
    recs = rec.setdefault("files", {})
    rec.setdefault("folders", [])
    keys = [k for k, r in recs.items() if r.get("ok") and r.get("at") and k in files]
    was_prefix = rec.get("prefix") or ""
    log_path = Path(studio) / FOLLOW_LOG
    log = read_json(log_path)
    if not isinstance(log, dict) or not isinstance(log.get("runs"), list):
        log = {"runs": []}
    idents = {}
    dirty = False               # the record changed here and is not saved yet
    log_dirty = False           # the log changed here and is not written yet
    changed = set()             # the files whose place on the second drive this run changed

    def at(k):
        return recs[k]["at"]

    # A copy killed in the moment between a file landing under its name and the record hearing of it: the note
    # written before that file's first byte says which file and where. When it is there, in one of this copy's
    # own folders, and its hash is the backup's, it is this copy's file: on record now, so it takes a new name
    # with the others instead of staying behind under the old one.
    going = read_json(Path(studio) / GOING)
    if isinstance(going, dict) and same_place(str(going.get("place") or ""), str(place)):
        k, rel = going.get("key"), going.get("at")
        if (k in files and isinstance(rel, str) and rel and not (recs.get(k) or {}).get("ok")
                and (Path(rel).parts[0] == MIRROR_RECORDS or ours(rec, Path(rel).parts[0]))
                and not any(r.get("ok") and r.get("at") and place_key(r["at"]) == place_key(rel) for r in recs.values())
                and names.exact(place / rel) and same_hash(place / rel, files[k])):
            recs[k] = {"ok": True, "from": "there", "note": "found where a copy that was cut off had left it", "at": rel}
            dirty = True
    keys = [k for k, r in recs.items() if r.get("ok") and r.get("at") and k in files]

    # a run that was cut off: where its log says a file may have got to is looked at first
    for run in log["runs"]:
        if run.get("finished") or not same_place(str(run.get("place") or ""), str(place)):
            continue
        for f in run.get("folders", []):
            if names.exact(place / f["to"]) and not names.exact(place / f["from"]):
                if not ours(rec, Path(f["to"]).parts[0]):
                    rec["folders"].append(Path(f["to"]).parts[0])     # this copy's own folder, under the name the log gave it
                for k in keys:
                    if at(k) == f["from"] or at(k).startswith(f["from"] + "/"):
                        recs[k]["at"] = f["to"] + at(k)[len(f["from"]):]
                        dirty = True
        # Where did each file of that run get to? Never answered by "something has that name": when names were
        # changing hands (a ring after a join, or one photo taking the name another had), the name a file left
        # may hold ANOTHER file by now. Each file is found by its own identity on the drive as the log kept it
        # (a rename never changes it), and, where that cannot say, by its hash; and no two files are ever put on
        # record at one place.
        moves = [m for m in (run.get("moves") if isinstance(run.get("moves"), list) else [])
                 if isinstance(m, dict) and m.get("key") in keys]
        claimed, found = {}, {}
        for by_hash in (False, True):
            for m in moves:
                k = m["key"]
                if k in found:
                    continue
                if m.get("ident"):
                    idents[k] = m["ident"]
                for step in (m.get("to"), m.get("via"), at(k), m.get("from")):
                    if not step or place_key(step) in claimed or not names.exact(place / step):
                        continue
                    if same_hash(place / step, files[k]) if by_hash else same_ident(place / step, m.get("ident")):
                        found[k] = step
                        claimed[place_key(step)] = k
                        break
        for k, step in found.items():
            if at(k) != step:
                recs[k]["at"] = step
                dirty = True
        run["finished"] = datetime.now().isoformat(timespec="seconds") + " (cut off; picked up by a later run)"
        log_dirty = True

    # Never two files on record at one place (a record left that way by a run cut off before Nov 23's fix, or a
    # file that could not be found above). The file that IS there, by its hash, keeps the place; another that
    # claims it is looked for where it should be by now, and failing that is said as not where it was left: the
    # file that is there is never moved in its name.
    lost = set()
    by_place = {}
    for k in keys:
        by_place.setdefault(place_key(at(k)), []).append(k)
    for ks in by_place.values():
        if len(ks) < 2:
            continue
        holder = next((k for k in ks if same_hash(place / at(k), files[k])), None)
        for k in ks:
            if k != holder:
                lost.add(k)
    if lost:
        taken = {place_key(at(k)) for k in keys if k not in lost}
        for k in sorted(lost):
            loc = on_main(k, files[k], view)
            to = mirror_rel(loc, view, mirror_name) if loc is not None else None
            if to and place_key(to) not in taken and names.exact(place / to) and same_hash(place / to, files[k]):
                recs[k]["at"] = to
                taken.add(place_key(to))
                lost.discard(k)
                dirty = True
    if dirty:
        save()                  # the record first: the log is only marked picked-up once the record knows
        dirty = False

    want = {}
    for k in keys:
        if k in lost:
            continue
        loc = on_main(k, files[k], view)
        if loc is not None:           # (not on the photo drive just now: its copy stays where it is)
            want[k] = mirror_rel(loc, view, mirror_name)
    diffs = [k for k in want if at(k) != want[k]]
    if lost:
        out["gone"] += len(lost)
    if not diffs:
        if rec.get("prefix") != view["prefix"] and not lost:
            rec["prefix"] = view["prefix"]
            save()
        if log_dirty:
            write_whole(log_path, log)
        if lost:
            out["problems"].append(OUR_WORDS["follow_gone"].format(**plural(len(lost))))
        return out

    run = {"place": str(place), "started": datetime.now().isoformat(timespec="seconds"), "folders": [], "moves": []}
    log["runs"].append(run)
    for old in log["runs"][:-FOLLOW_KEPT]:       # older runs keep their counts, not every line
        if isinstance(old.get("moves"), list):
            old["moves"] = len(old["moves"])
    place_dev = os.stat(place).st_dev

    def stop(words, **count):
        if words not in out["problems"]:
            out["problems"].append(words)
        for name, n in count.items():
            out[name] += n

    # 1. a whole shoot folder that only changed its name (or went up out of the day folder): one step, as on the photo drive
    under = {}
    for k in keys:
        if k in lost:
            continue
        u = unit_of(at(k), was_prefix)
        if u:
            under.setdefault(u, []).append(k)
    steps = []
    for u, ks in sorted(under.items()):
        to = {unit_of(want[k], view["prefix"]) if k in want else None for k in ks}
        if len(to) != 1:
            continue
        v = to.pop()
        if not v or v == u or not names.exact(place / u):
            continue
        holder = names.has(place / v)
        twin = holder is not None and Path(u).parent == Path(v).parent and fold(Path(u).name) == fold(Path(v).name)
        if holder is not None and not twin:
            continue                    # something has that name already: each file is looked at on its own, below
        top = Path(v).parts[0]
        if len(Path(v).parts) > 1 and names.has(place / top) is not None and not ours(rec, top):
            continue
        steps.append({"from": u, "to": v})
    if steps:
        run["folders"] = steps
        write_whole(log_path, log)                                  # on record before anything moves
        for f in steps:
            src, dst = place / f["from"], place / f["to"]
            top = Path(f["to"]).parts[0]
            if not ours(rec, top):
                rec["folders"].append(top)
                save()
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if os.stat(src).st_dev != place_dev or os.stat(dst.parent).st_dev != place_dev:
                    stop(OUR_WORDS["follow_cant"])
                    continue
                names.forget()
                holder = names.has(dst)
                if holder is not None and not (src.parent == dst.parent and fold(src.name) == fold(dst.name)):
                    continue            # it appeared since the look a moment ago: never taken over
                this_computer.rename(src, dst)
            except OSError:
                stop(OUR_WORDS["follow_cant"])
                continue
            f["moved"] = True
            for k in under[f["from"]]:
                recs[k]["at"] = f["to"] + at(k)[len(f["from"]):]
                changed.add(k)
            names.forget()
            write_whole(log_path, log)
            save()
        if out["problems"]:
            run["problems"] = list(out["problems"])
            out["moved"] = len(changed)
            write_whole(log_path, log)
            return out

    # 2. each file whose place still differs
    names.forget()
    moves, taken_to = [], {}
    sources = {}
    for k in sorted(k for k in want if at(k) != want[k]):
        src, dst = place / at(k), place / want[k]
        if not names.exact(src):
            if names.exact(dst) and proved(dst, idents.get(k), files[k]):
                recs[k]["at"] = want[k]             # an earlier run got this far and could not write it down
                continue
            out["gone"] += 1
            continue
        key_to = "/".join(fold(x) for x in Path(want[k]).parts)
        if key_to in taken_to:
            stop(OUR_WORDS["follow_in_way"])
            continue
        taken_to[key_to] = k
        top = Path(want[k]).parts[0]
        if top != MIRROR_RECORDS and len(Path(want[k]).parts) > 1 and names.has(place / top) is not None and not ours(rec, top):
            stop(OUR_WORDS["follow_folder"].format(folder=top))
            continue
        sources["/".join(fold(x) for x in Path(at(k)).parts)] = k
        moves.append({"key": k, "from": at(k), "to": want[k]})
    for m in moves:                     # is anything in the way that is not one of this copy's own files about to move?
        dst = place / m["to"]
        if names.has(dst) is not None and "/".join(fold(x) for x in Path(m["to"]).parts) not in sources:
            stop(OUR_WORDS["follow_in_way"])
    if out["problems"]:
        run["problems"] = list(out["problems"])
        out["moved"] = len(changed)
        if not changed and not run["folders"]:
            log["runs"].remove(run)     # nothing moved at all: nothing to pick up, and a try every few seconds
            #                             while something is in the way must not grow the log
            if log_dirty:
                write_whole(log_path, log)
        else:
            write_whole(log_path, log)
            save()
        return out                      # nothing in the way is ever moved or taken over: no file moved
    for m in moves:
        try:
            st = os.stat(place / m["from"])
            m["ident"] = [st.st_ino, st.st_size, st.st_mtime_ns]
        except OSError:
            m["ident"] = None
    run["moves"] = moves
    write_whole(log_path, log)                                      # on record before the first file moves

    def one(m, dst_rel):
        """Move one file to dst_rel. True when it is there and proved; None when the name is in use for now."""
        k = m["key"]
        src, dst = place / at(k), place / dst_rel
        twin = src.parent == dst.parent and fold(src.name) == fold(dst.name)
        if names.has(dst) is not None and not twin:
            return None
        top = Path(dst_rel).parts[0]
        if top != MIRROR_RECORDS and len(Path(dst_rel).parts) > 1 and not ours(rec, top):
            rec["folders"].append(top)
            save()                      # the folder is on record as this copy's before it is made
        dst.parent.mkdir(parents=True, exist_ok=True)
        if os.stat(src).st_dev != os.stat(dst.parent).st_dev:
            raise OSError("the place it should go is on another drive")     # never a copy-and-delete
        if twin:
            this_computer.rename(src, dst)          # only the capital letters change
        elif not this_computer.rename_new(src, dst):
            return None                 # a name that appeared since the look: never taken over
        names.moved(src, dst)
        recs[k]["at"] = dst_rel
        if not proved(dst, m.get("ident"), files[k]):
            recs[k]["unproved"] = True
            stop(OUR_WORDS["follow_unproved"], unproved=1)
            return False
        return True

    waiting, turns = list(moves), 0
    try:
        while waiting:
            m = waiting.pop(0)
            got = one(m, m["to"])
            if got is None:
                waiting.append(m)
                turns += 1
                if turns > len(waiting):        # a ring of names: one steps aside under a name of its own
                    m = next((x for x in waiting if not x.get("via")), None)
                    if m is None:               # every one has stepped aside and a name is still in use: not ours to take
                        stop(OUR_WORDS["follow_in_way"])
                        break
                    waiting.remove(m)
                    src = place / at(m["key"])
                    n, via = 0, None
                    while via is None or names.has(place / via) is not None:
                        n += 1
                        via = (Path(at(m["key"])).parent / f".{src.name}.{n}{MOVING}").as_posix()
                    m["via"] = via
                    write_whole(log_path, log)
                    if one(m, via) is None:
                        stop(OUR_WORDS["follow_in_way"])
                        break
                    waiting.append(m)
                    turns = 0
                continue
            turns = 0
            if got and m["to"] == at(m["key"]):
                m["moved"] = True
                changed.add(m["key"])
                if len(changed) % 200 == 0:
                    write_whole(log_path, log)
                    save()
    except OSError:
        stop(OUR_WORDS["follow_cant"])
    out["moved"] = len(changed)
    if out["gone"]:
        out["problems"].append(OUR_WORDS["follow_gone"].format(**plural(out["gone"])))
    if out["unproved"]:
        out["problems"] = [w for w in out["problems"] if w != OUR_WORDS["follow_unproved"]]
        out["problems"].append(OUR_WORDS["follow_unproved"].format(**plural(out["unproved"])))

    # 3. the folders the files left: a folder of this copy's that is empty now comes down (an empty folder only;
    # the computer's own hidden notes in it are set aside in the mirror's records, never deleted)
    left = set()
    for was_at in [m["from"] for m in moves] + [f["from"] + "/x" for f in steps if f.get("moved")]:
        for parent in Path(was_at).parents:
            if parent.as_posix() not in (".", "") and parent.parts[0] != MIRROR_RECORDS and ours(rec, parent.parts[0]):
                left.add(parent.as_posix())
    aside = place / MIRROR_RECORDS / mirror_name / "set-aside"
    for rel in sorted(left, key=lambda r: -len(Path(r).parts)):
        d = place / rel
        try:
            entries = list(d.iterdir())
            if any(not (x.is_file() and this_computer.housekeeping_file(x.name)) for x in entries):
                continue
            for x in entries:
                (aside / rel).mkdir(parents=True, exist_ok=True)
                this_computer.rename_new(x, aside / rel / x.name)
            this_computer.rmdir(d)
        except OSError:
            continue
    names.forget()
    rec["folders"] = [t for t in rec["folders"] if names.has(place / t) is not None]
    if not out["problems"]:
        rec["prefix"] = view["prefix"]
        run["finished"] = datetime.now().isoformat(timespec="seconds")
    else:
        run["problems"] = list(out["problems"])
    run["done"] = out["moved"]
    save()                      # the record first: the log says "finished" only once the record knows where every
    write_whole(log_path, log)  # file is (cut between the two, the next run finds the run unfinished and checks)
    return out


def rebuild_report(studio):
    """The report's page is written again, so the page as a file says what the live page says. Never fatal."""
    for script in ("first_look.py", "report_page.py"):
        try:
            subprocess.run([sys.executable, str(HERE / script), str(studio)], capture_output=True, timeout=600,
                           **({"creationflags": 0x08000000} if this_computer.WINDOWS else {}))
        except (OSError, subprocess.SubprocessError):
            pass


def keep_mirror_record(place, mirror_name, rec):
    """The mirror's own hidden records keep a copy of where each of its files is (best effort: the record that
    counts is the one in the backup's records on the photo drive)."""
    try:
        d = Path(place) / MIRROR_RECORDS / mirror_name
        if d.is_dir():
            write_whole(d / RECORD, rec)
    except OSError:
        pass


def _held_lock():
    """This computer's one second-copy lock, taken (as main() takes it), or None when a copy holds it."""
    HOME.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, "a+", encoding="utf-8")
    got = this_computer.try_lock(lock)
    for _ in range(10):
        if got is not False:
            break
        time.sleep(0.1)
        got = this_computer.try_lock(lock)
    if got is False:
        lock.close()
        return None
    return lock, got


def follow(arg):
    """After a shoot is renamed or two are joined on the photo drive: this backup's second copy takes the same
    folders and names (align). Never raises. Returns {"state", "words", "moved"}; state is
      "none"     there is no second copy of this backup (or none of the new kind with files on it)
      "card"     its second copy is the earlier kind, laid out as the card was: left exactly as it is
      "same"     already in line: nothing was moved and nothing written
      "followed" the mirror now matches (words say so)
      "waiting"  the second drive is not plugged in: noted in second-copy.json, done when a command next sees it
      "busy"     a second copy is being made right now (it brings itself in line before it finishes)
      "problem"  something is in the way or could not be proved: nothing removed or written over (words say what)"""
    try:
        return _follow(arg)
    except (Exception, SystemExit) as e:  # noqa: BLE001  (the caller has just renamed photos; this never stops it)
        return {"state": "problem", "moved": 0, "words": "", "error": e.__class__.__name__}


def _follow(arg):
    root, studio = locate(arg)
    rec = read_json(studio / RECORD)
    if not isinstance(rec, dict) or not any(r.get("ok") for r in (rec.get("files") or {}).values()):
        return {"state": "none", "moved": 0, "words": ""}
    if rec.get("layout") != LAYOUT_MAIN:
        return {"state": "card", "moved": 0, "words": ""}
    manifest = read_json(studio / "manifest.json", {}) or {}
    files = manifest.get("files") or {}
    place = Path(rec.get("place") or rec.get("to") or "")
    name = str(rec.get("to_name") or "your second drive")
    photos = drive_name(root)
    was = dict(rec.get("follow") or {})

    def note(state, line="", **more):
        rec["follow"] = dict({"state": state, "when": datetime.now().isoformat(timespec="seconds"), "line": line}, **more)
        write_whole(studio / RECORD, rec)
        behind = lambda f: (f.get("state"), f.get("line")) if f.get("state") in ("waiting", "problem") else None  # noqa: E731
        if behind(was) != behind(rec["follow"]) and (studio / "report.html").is_file():
            rebuild_report(studio)      # the line under "Second copy made" comes or goes on the page as a file too

    held = _held_lock()
    if held is None:
        # Something holds this computer's one second-copy lock. Only a copy of THIS backup takes the new names
        # itself before it finishes. Anything else (another backup's copy, another backup's follow) will not: so
        # this copy is noted as waiting, the report says so, and the next look (the report's own status check,
        # a backup, follow --all) brings it in line. The record is this backup's own; the lock's holder never
        # writes it.
        info = running() or {}
        try:
            # (the note of who is copying outlives its copy, and a follow holds the lock without writing one: so
            # the note counts only while the process it names is alive)
            own = (bool(info.get("studio")) and Path(info["studio"]).resolve() == Path(studio).resolve()
                   and bool(this_computer.still_running(info.get("pid"))))
        except OSError:
            own = False
        if own or rec.get("state") == "copying":
            return {"state": "busy", "moved": 0, "words": OUR_WORDS["follow_busy"]}
        line = OUR_WORDS["follow_later"].format(drive=name)
        try:
            had = read_json(studio / LATER, {}) or {}
            if (had.get("state"), had.get("line")) != ("waiting", line):
                write_whole(studio / LATER, {"state": "waiting", "line": line, "when": datetime.now().isoformat(timespec="seconds")})
                if was.get("state") not in ("waiting", "problem") and (studio / "report.html").is_file():
                    rebuild_report(studio)
        except OSError:
            pass
        return {"state": "waiting", "moved": 0, "words": line}
    lock, got = held
    try:
        fresh = read_json(studio / RECORD)      # as it is now that the lock is ours (a follow just before may have moved files)
        if isinstance(fresh, dict) and fresh.get("layout") == LAYOUT_MAIN:
            rec.clear()
            rec.update(fresh)
            was = dict(rec.get("follow") or {})
        later = read_json(studio / LATER, {}) or {}
        if later.get("state") == "waiting":
            # the lock is ours now: that note has done its work (kept, emptied; never removed)
            write_whole(studio / LATER, {"state": "", "when": datetime.now().isoformat(timespec="seconds")})
            if was.get("state") not in ("waiting", "problem"):
                was = {"state": "waiting", "line": str(later.get("line") or "")}
        mirror_name = rec.get("mirror") or this_computer.safe_name(manifest.get("session") or studio.name, limit=120)

        try:
            there = place.is_dir()
        except OSError:
            there = False
        if not there:
            line = OUR_WORDS["follow_waiting"].format(drive=name)
            if (was.get("state"), was.get("line")) != ("waiting", line):
                note("waiting", line)
            return {"state": "waiting", "moved": 0, "words": line}
        view = main_view(root, studio, files)
        saved = []
        try:
            got_ = align(place, mirror_name, view, studio, rec, files, lambda: (saved.append(1), write_whole(studio / RECORD, rec)))
        except OSError:
            got_ = {"moved": 0, "problems": [OUR_WORDS["follow_cant"]]}
        if got_["problems"]:
            line = OUR_WORDS["follow_problem"].format(drive=name, photos=photos, why=" ".join(got_["problems"]))
            if got_["moved"] or saved or (was.get("state"), was.get("line")) != ("problem", line):
                note("problem", line, moved=got_["moved"])      # (the same problem met again, nothing moved: nothing rewritten)
                keep_mirror_record(place, mirror_name, rec)
            return {"state": "problem", "moved": got_["moved"], "words": line}
        if not got_["moved"] and not saved and was.get("state") not in ("waiting", "problem"):
            return {"state": "same", "moved": 0, "words": ""}
        line = OUR_WORDS["follow_done"].format(drive=name, photos=photos)
        note("done", line, moved=got_["moved"])
        keep_mirror_record(place, mirror_name, rec)
        return {"state": "followed" if got_["moved"] or saved else "same", "moved": got_["moved"], "words": line}
    finally:
        if got:
            this_computer.unlock(lock)
        lock.close()


def behind_how(studio, rec):
    """Why this mirror may not be in line with the photo drive, or "": "waiting" (its drive was out, or another
    copy held the lock, when a shoot was renamed), "problem" (something was in the way: worth another try, since
    they may have moved it since), "cut" (a follow was cut off part way: its log has a run that never finished)."""
    f = rec.get("follow") or {}
    if f.get("state") in ("waiting", "problem"):
        return f["state"]
    if (read_json(Path(studio) / LATER, {}) or {}).get("state") == "waiting":
        return "waiting"
    log = read_json(Path(studio) / FOLLOW_LOG)
    place = str(rec.get("place") or "")
    for run in (log.get("runs") if isinstance(log, dict) and isinstance(log.get("runs"), list) else []):
        if isinstance(run, dict) and not run.get("finished") and "done" not in run and not run.get("problems") \
                and same_place(str(run.get("place") or ""), place):
            return "cut"
    return ""


def follow_all():
    """Every backup the card ledger knows whose second copy is behind (it was waiting for its drive or for another
    copy to end, something was in the way, or a follow was cut off): followed now, when that drive is in. Quiet,
    never raises. Returns how many were brought in line."""
    n = 0
    try:
        sessions = [s.get("folder") for entry in (cards.load().get("cards") or {}).values()
                    for s in (entry.get("sessions") or []) if isinstance(s, dict) and s.get("folder")]
    except (Exception, SystemExit):  # noqa: BLE001
        return 0
    for folder in sessions:
        try:
            _, studio = locate(folder)
            rec = read_json(Path(studio) / RECORD)
            if not isinstance(rec, dict) or rec.get("layout") != LAYOUT_MAIN or not behind_how(studio, rec):
                continue
            if not Path(rec.get("place") or "").is_dir():
                continue
            if follow(studio).get("state") in ("followed", "same"):
                n += 1
        except (Exception, SystemExit):  # noqa: BLE001
            continue
    return n


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
    mirror_name = this_computer.safe_name(session, limit=120)
    name = drive_name(place)
    # Which layout. Every new second copy looks like the photo drive. Only a copy of the earlier kind (the card's
    # own layout, in a folder named for the backup) that stopped part way is finished the way it was begun.
    old = read_json(studio / RECORD)
    layout = LAYOUT_MAIN
    if (isinstance(old, dict) and old.get("layout", LAYOUT_CARD) == LAYOUT_CARD and old.get("files")
            and same_place(str(Path(old.get("to") or "")), str(place / mirror_name))):
        layout = LAYOUT_CARD
    main = layout == LAYOUT_MAIN
    second = place if main else place / mirror_name
    mirror = place / MIRROR_RECORDS / mirror_name if main else second / "_studio"
    had = has_second(manifest)
    if had:
        if same_place(str(Path(had)), str(place)) or same_place(str(Path(had)), str(place / mirror_name)):
            raise Refused("has_one", OUR_WORDS["has_one"].format(drive=drive_name(had)))
        raise Refused("has_one_elsewhere", OUR_WORDS["has_one_elsewhere"].format(drive=drive_name(had)))
    if main:
        # a copy that looks like the shoots needs the shoots: sorted, checked, and no rename half done
        import settle
        try:
            why = settle.gates(studio)
        except (OSError, ValueError):
            why = "unreadable"
        if why:
            key = "mid_rename" if "rename" in why else "mid_join" if "join" in why else "unsorted"
            raise Refused(key, OUR_WORDS[key])
    # never onto the card, never inside the backup, never onto the drive the photos are on
    card = Path(manifest["source"]) if manifest.get("source") else None
    card_in = False
    try:
        card_in = bool(card) and card.is_dir()
    except OSError:
        pass
    if card_in and (within(place, card) or (backup.onto_itself(card, place, "the second copy")
                                              and (backup._top_of_drive(card.resolve()) / "DCIM").is_dir())):
        raise Refused("onto_card", OUR_WORDS["onto_card"])
    # never onto a memory card: this backup's own or any other (one a camera has written to, wherever on it the
    # folder is). A card gets formatted, and may hold photos not backed up yet.
    import studio_file
    if studio_file.card_above(place) is not None:
        raise Refused("onto_card", OUR_WORDS["a_card"])
    shoots = [x.get("folder") for x in (read_json(studio / "shoots.json", {}) or {}).get("shoots", []) if x.get("folder")]
    if (within(place, studio) or (studio.name == "_studio" and within(place, root))
            or any(within(place, root / f) for f in shoots if isinstance(f, str))):
        raise Refused("inside", OUR_WORDS["inside"])
    if backup.onto_itself(root, place, "the second copy") or same_drive(root, place):
        raise Refused("same_drive", OUR_WORDS["same_drive"].format(drive=drive_name(root)))
    # records of that name already there, holding another backup's second copy
    theirs = read_json(mirror / "manifest.json")
    if isinstance(theirs, dict):
        other = theirs.get("files") or {}
        if set(other) != set(files) or any(not (hashes_of(other[k]) & hashes_of(files[k])) for k in files):
            raise Refused("another_there", OUR_WORDS["another_there"].format(drive=name))
    view, where_to = None, {}
    if main:
        # Where each file will go, and whose the folders are. A folder on the second drive with the name of one
        # of this backup's shoots that this copy did not make itself is never copied into: refused here, by name.
        view = main_view(root, studio, files)
        mine = old.get("folders") or [] if isinstance(old, dict) and same_place(str(Path(old.get("to") or "")), str(place)) else []
        names = Names()
        for key, e in files.items():
            loc = on_main(key, e, view)
            if loc is None:
                continue
            where_to[key] = (mirror_rel(loc, view, mirror_name), loc)
        for top in sorted({rel.split("/")[0] for rel, _ in where_to.values()} - {MIRROR_RECORDS}):
            holder = names.has(place / top)
            if holder is not None and fold(top) not in {fold(x) for x in mine}:
                raise Refused("folder_there", OUR_WORDS["folder_there"].format(drive=name, folder=holder))

    def dest_of(key):
        if not main:
            return second / Path(*key.split("/"))
        return place / Path(*where_to[key][0].split("/")) if key in where_to else None

    # room: what is still to copy, plus the margin the backup keeps
    need = 0
    for key, e in files.items():
        try:
            if dest_of(key) is not None and dest_of(key).stat().st_size == e.get("size"):
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
        def there(k, e):
            try:
                return dest_of(k) is not None and dest_of(k).stat().st_size == e.get("size")
            except OSError:
                return False

        if main:
            edited = [k for k, e in files.items() if not there(k, e) and k in where_to and where_to[k][1]["changed"]]
        else:
            places = drive_places(root, studio)
            edited = [k for k, e in files.items()
                      if not (rec_ok(studio, second, k, e))
                      and find_on_drive(k, e.get("size"), root, studio, places) is None
                      and there_but_changed(k, root, studio, places)]
        if edited:
            raise Refused("edited", OUR_WORDS["edited_no_card"].format(photos=drive_name(root), **plural(len(edited))))
    return {"arg": str(arg), "root": root, "studio": studio, "manifest": manifest, "session": session, "place": place,
            "second": second, "name": name, "card": card if card_in else None, "layout": layout, "mirror": mirror,
            "mirror_name": mirror_name,
            "bytes": sum(max(0, e.get("size") or 0) for e in files.values())}


# ---------------------------------------------------------------- the copy

class Stop(Exception):
    """The copy cannot go on right now (a drive went away, or filled up). Run again to finish."""
    def __init__(self, words_key, **more):
        super().__init__(words_key)
        self.key, self.more = words_key, more


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
    main = plan.get("layout", LAYOUT_MAIN) == LAYOUT_MAIN     # looks like the photo drive; else an older copy, the card's layout
    place, mirror, mirror_name = plan["place"], plan["mirror"], plan["mirror_name"]
    files = manifest["files"]
    total = len(files)
    where = {"root": plan["root"], "studio": plan["studio"]}
    where["places"] = drive_places(where["root"], where["studio"], files)
    where["view"] = main_view(where["root"], where["studio"], files)

    def relocate():
        """The backup may settle while this runs (its shoots move up, its records move): find it again."""
        try:
            where["root"], where["studio"] = locate(arg)
        except SystemExit:
            try:
                where["root"], where["studio"] = locate(where["studio"])
            except SystemExit:
                return False
        where["places"] = drive_places(where["root"], where["studio"], files)
        where["view"] = main_view(where["root"], where["studio"], files)
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
    if isinstance(rec, dict) and not (same_place(str(Path(rec.get("to") or "")), str(second))
                                      and rec.get("layout", LAYOUT_CARD) == plan.get("layout", LAYOUT_MAIN)):
        try:
            this_computer.rename_new(rec_path, rec_path.with_name(f"second-copy.older-{datetime.now():%Y%m%d-%H%M%S}.json"))
        except OSError:
            pass
        rec = None
    if not isinstance(rec, dict):
        rec = {"to": str(second), "to_name": name, "started": datetime.now().isoformat(timespec="seconds"), "files": {}}
        if main:    # where each file is on the second drive ("at"), and the folders this copy made, are kept as it goes
            rec.update({"layout": LAYOUT_MAIN, "place": str(place), "mirror": mirror_name, "folders": [],
                        "prefix": where["view"]["prefix"]})
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
        mirror.mkdir(parents=True, exist_ok=True)
    except OSError:
        return finish_stopped(rec, save, "stopped_dest", name, total)
    backup.hide(mirror if not main else mirror.parent)

    def in_line():
        """The files copied so far take the folders and names the photo drive has now (a shoot renamed since an
        earlier run stopped, or while this one ran). None when all is in line, else the line of a copy that stops."""
        if not where["studio"].is_dir():
            relocate()
        where["view"] = main_view(where["root"], where["studio"], files)
        try:
            got = align(place, mirror_name, where["view"], where["studio"], rec, files, save)
        except OSError:
            got = {"problems": [OUR_WORDS["follow_cant"]]}
        if not got["problems"]:
            rec.pop("follow", None)         # (a note that it was waiting for this drive, or for something in the way)
            try:
                if (read_json(where["studio"] / LATER, {}) or {}).get("state") == "waiting":
                    write_whole(where["studio"] / LATER, {"state": "", "when": datetime.now().isoformat(timespec="seconds")})
            except OSError:
                pass
            return None
        return OUR_WORDS["follow_problem"].format(drive=name, photos=drive_name(where["root"]), why=" ".join(got["problems"]))

    if main:
        line = in_line()
        if line:
            rec["state"] = "stopped"
            rec["finished"] = datetime.now().isoformat(timespec="seconds")
            save(line)
            say("PROBLEM: " + line)
            return 1, line
    made = Names()

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
        r = rec["files"].get(key)
        turned = bool(entry.get("card_sha256")) and entry["card_sha256"] != entry.get("sha256")
        at, loc = {}, None
        try:
            if main:
                # where this file is on the photo drive now says where its copy goes: the same folder, the same name
                if r and r.get("ok") and r.get("at"):
                    kept = place / Path(*r["at"].split("/"))
                    if kept.is_file() and kept.stat().st_size == size:
                        continue        # checked on an earlier run and still there at its size: skip
                loc = on_main(key, entry, where["view"])
                if loc is None and relocate():
                    loc = on_main(key, entry, where["view"])
                if loc is None:
                    if not where["root"].is_dir():
                        raise Stop("stopped_photos")
                    rec["files"][key] = {"ok": False, "note": "not found on the drive"}
                    missing.append(key)
                    save()
                    continue
                rel = mirror_rel(loc, where["view"], mirror_name)
                at = {"at": rel}
                dst = place / Path(*rel.split("/"))
                top = rel.split("/")[0]
                if top != MIRROR_RECORDS and "/" in rel and not ours(rec, top):
                    made.forget()
                    holder = made.has(place / top)
                    if holder is not None:      # a folder of that name appeared since the questions were asked: not ours
                        raise Stop("stopped_folder", folder=holder)
                    rec["folders"].append(top)
                    save()                      # on record as this copy's own before it is made
            else:
                dst = second / Path(*key.split("/"))
                # checked on an earlier run and still there at its size: skip
                if r and r.get("ok") and dst.is_file() and dst.stat().st_size == size:
                    continue
            if os.path.lexists(dst) and not backup.ours_to_redo(r, dst):
                # something is already there that is not our own failed copy: compared, never written over
                same = False
                try:
                    right = {entry.get("sha256")} if main else hashes_of(entry)     # a mirror holds what the photo drive holds
                    same = dst.is_file() and dst.stat().st_size == size and backup.sha256_of(dst) in right
                except OSError:
                    pass
                if same:
                    rec["files"][key] = dict({"ok": True, "from": "there", "note": "already there, identical"}, **at)
                else:
                    rec["files"][key] = {"ok": False, "note": backup.DIFFERS}
                    differs.append(key)
                save()
                continue
            only_drive = False
            while True:   # at most twice for one file: the card, then their drive
                # (a clip the backup turned upright is on the card sideways: a mirror takes the upright one, from their drive)
                from_card = card is not None and not only_drive and not (main and turned)
                if from_card:
                    src = card / Path(*key.split("/"))
                    want = entry.get("sha256") if main else (entry.get("card_sha256") or entry.get("sha256"))
                else:
                    want = entry.get("sha256")
                    if main:
                        src, was_changed = loc["src"], loc["changed"]
                    else:
                        src = find_on_drive(key, size, where["root"], where["studio"], where["places"])
                        if src is None and relocate():
                            src = find_on_drive(key, size, where["root"], where["studio"], where["places"])
                        was_changed = src is None and there_but_changed(key, where["root"], where["studio"], where["places"])
                    if src is None:
                        if not where["root"].is_dir():
                            raise Stop("stopped_photos")
                        if only_drive:
                            changed.append(key)      # the card's differs and the drive has none: said as changed
                        elif was_changed:
                            rec["files"][key] = {"ok": False, "note": "changed on the drive since the backup", "left": backup.identity(dst)}
                            edited.append(key)
                        else:
                            rec["files"][key] = {"ok": False, "note": "not found on the drive", "left": backup.identity(dst)}
                            missing.append(key)
                        break
                if rec.get("reading") != ("card" if from_card else "drive"):
                    rec["reading"] = "card" if from_card else "drive"
                    save()
                if main:
                    # log first: which file, and the name it is going under, before its first byte (a small note
                    # of its own; align() reads it when a copy was killed before the record heard of the file)
                    try:
                        if not where["studio"].is_dir():
                            relocate()
                        write_whole(where["studio"] / GOING, {"key": key, "at": at["at"], "place": str(place)})
                    except OSError:
                        pass
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
                        if main and relocate() and (on_main(key, entry, where["view"]) or {}).get("src") not in (None, src):
                            raise Stop("stopped_killed")    # the backup's folders moved while this ran (it settled): run again
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
                rec["files"][key] = dict({"ok": True, "from": "card" if from_card else "drive"}, **at)
                if not from_card and turned:
                    rec["files"][key]["turned"] = True     # the upright clip from their drive, 36 bytes off the card's
                break
        except Stop as halt:
            stop = halt
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
        return finish_stopped(rec, save, stop.key, name, total, **stop.more)
    counts()
    behind = in_line() if main else None      # a shoot renamed while this ran: the copy takes the new names before it is called made
    if differs or changed or missing or edited or behind or rec["done"] != total:
        parts = []
        if behind:
            parts.append(behind)
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
    if main:
        fresh["second_layout"] = LAYOUT_MAIN      # (a copy in the card's own layout has no such line, as before)
    for k, e in fresh["files"].items():
        e["second"] = {"ok": True}
        if rec["files"][k].get("turned"):
            e["second"]["turned"] = True
    fresh["second_made"] = datetime.now().isoformat(timespec="seconds")
    write_whole(mpath, fresh)
    try:
        write_whole(mirror / "manifest.json", fresh)
        backup.hide(mirror if not main else mirror.parent)
    except OSError:
        pass
    upright = sum(1 for x in rec["files"].values() if x.get("turned"))
    line = OUR_WORDS["done"].format(drive=name, total=f"{total:,}")
    photos = drive_name(where["root"])
    # (in a mirror, an upright clip always comes from their drive, card in or not: it is not "the card wasn't in")
    no_card = rec["from_drive"] - (upright if main else 0)
    if no_card and not rec["from_card"]:
        line += OUR_WORDS["from_drive"].format(photos=photos)
    elif no_card:
        line += OUR_WORDS["some_from_drive"].format(n=f"{no_card:,}", photos=photos)
    if upright:
        line += OUR_WORDS["upright"].format(n=f"{upright:,}", s=" is" if upright == 1 else "s are", s2="" if upright == 1 else "s")
    if main:
        line += OUR_WORDS["like_main"].format(photos=photos)
    if always and not REMEMBER_SECOND:
        say(OUR_WORDS["not_remembered"])
    if always and REMEMBER_SECOND:
        try:
            import studio_file
            sf = studio_file.load()
            if studio_file.set_drive(sf.setdefault("drives", {}), "second", str(plan["place"])):
                studio_file.save(sf)
                say("Saved: every backup from now on gets a second copy there.")
        except Exception as e:  # noqa: BLE001  (the copy is made and checked; the setting can be said again)
            say(f"(could not save it as the usual second copy: {e.__class__.__name__})")
    rebuild_report(studio)                                 # the report now says there is a second copy
    rec["state"] = "done"
    rec["finished"] = fresh["second_made"]
    rec["upright"] = upright
    rec["reading"] = None
    try:
        save(line)
    except OSError:
        pass                 # the copy is made, checked and in the manifest; only this note of it could not be written
    if main:
        keep_mirror_record(place, mirror_name, rec)
    say(line)
    return 0, line


def finish_stopped(rec, save, key, name, total, **more):
    rec["state"] = "stopped"
    rec["finished"] = datetime.now().isoformat(timespec="seconds")
    done = sum(1 for x in rec["files"].values() if x.get("ok"))
    line = OUR_WORDS[key].format(drive=name, done=f"{done:,}", total=f"{total:,}", **more) + " " + OUR_WORDS["nothing_removed"]
    try:
        save(line)
    except OSError:
        rec["line"] = line
    say("STOPPED: " + line.replace(OUR_WORDS["nothing_removed"], "Nothing was removed. Run it again to carry on."))
    return 3, line


def status(studio):
    """How this backup's second copy stands, for the report's page: {"state": "none"|"copying"|"done"|"stopped",
    "done", "total", "name", "card" (is it reading the card right now), "line", "behind", "catch", "old"}.
    behind: the line to show when the copy still has the folders and names from before a rename or a join (its
    drive was not plugged in, another copy was being made, a follow was cut off, or something was in the way); ""
    when it is in line, and while it is set `line` never says the copy has the photo drive's folders and names.
    catch: it is behind and its drive is in now (the report's server then runs follow). old: it is a copy
    of the earlier kind, laid out as the card was. Never a path."""
    studio = Path(studio)
    out = _status(studio)
    out.update({"behind": "", "catch": False, "old": False})
    rec = read_json(studio / RECORD)
    if out["state"] == "done":
        manifest = read_json(studio / "manifest.json", {}) or {}
        out["old"] = manifest.get("second_layout") != LAYOUT_MAIN
    if isinstance(rec, dict) and rec.get("layout") == LAYOUT_MAIN and out["state"] != "copying":
        how = behind_how(studio, rec)
        if how:
            f = rec.get("follow") or {}
            if f.get("state") not in ("waiting", "problem"):
                f = read_json(studio / LATER, {}) or {}
            out["behind"] = (str(f.get("line") or "") if how != "cut" else "") or OUR_WORDS["follow_part_way"].format(
                drive=str(rec.get("to_name") or "your second drive"))
            # worth a try whenever the drive is in: waiting catches up, a cut-off run is finished, and a problem
            # is looked at again (they may have moved what was in the way). The server asks no oftener than every
            # 20 seconds, and a try that meets the same problem moves and writes nothing.
            try:
                out["catch"] = Path(rec.get("place") or "").is_dir() and not running()
            except OSError:
                pass
            # While it is behind, the made line must not say it has the photo drive's folders and names: cut there.
            cut = out["line"].find(OUR_WORDS["like_main"].split("{photos}")[0])
            if cut >= 0:
                out["line"] = out["line"][:cut]
    return out


def _status(studio):
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


def follow_main(args):
    """second_copy.py follow "<backup>" [--json]   ·   second_copy.py follow --all"""
    as_json = "--json" in args
    args = [x for x in args if x != "--json"]
    if args == ["--all"]:
        n = follow_all()
        say(json.dumps({"ok": True, "followed": n}) if as_json else f"{n} second cop{'y' if n == 1 else 'ies'} brought in line.")
        return 0
    if len(args) != 1:
        sys.exit('usage: second_copy.py follow "<the backup>" [--json]   or   second_copy.py follow --all')
    got = follow(args[0])
    plain = {"none": "This backup has no second copy to bring in line.",
             "card": "This backup's second copy is the earlier kind, laid out as the card was. It is left as it is.",
             "same": "The second copy already has the same folders and names. Nothing to do."}
    line = got.get("words") or plain.get(got["state"]) or OUR_WORDS["follow_cant"]
    if as_json:
        say(json.dumps({"ok": got["state"] in ("followed", "same", "none", "card"), "state": got["state"], "words": line,
                        "moved": got.get("moved", 0)}))
    else:
        say(line)
    return 0 if got["state"] in ("followed", "same", "none", "card") else 3 if got["state"] in ("waiting", "busy") else 1


def main():
    if sys.argv[1:2] == ["follow"]:
        sys.exit(follow_main(sys.argv[2:]))
    ap = argparse.ArgumentParser(
        description=("A second copy of a finished backup, on another drive, with the same shoot folders and photo names as "
                     "the photo drive. Nothing is deleted or written over. "
                     "(second_copy.py follow \"<backup>\" brings a copy in line after a rename or a join.)"),
        epilog="Exit codes: 0 done (or nothing to do), 1 problems, 2 refused before anything was written, 3 stopped part way (run it again).")
    ap.add_argument("backup", help="the backup: its folder, where it was, or its records")
    ap.add_argument("--to", required=True, help="the drive (or a folder on it) the second copy goes on")
    ap.add_argument("--check", action="store_true", help="only ask the questions; write nothing")
    ap.add_argument("--json", action="store_true", help="end with one JSON line {ok, state, words}")
    ap.add_argument("--always", action="store_true",
                    help="no longer saves anything (the second drive is asked each time); kept so an older command still runs")
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
