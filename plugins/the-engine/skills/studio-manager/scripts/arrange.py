#!/usr/bin/env python3
"""Arranging a post kit's photos on a page: which photos are in the reel or the carousel, and in what order.

The Assistant picks; the photographer can move things. The page (arrange_page.py) is served by the page
server (posting_queue.py), which hands every request for it to handle_get / handle_post here. This file
holds the records, the commands and the route handlers. It holds no page code.

    python3 arrange.py show "beach"                    the kit's name, how many photos, the list's stamp
    python3 arrange.py previews "beach"                small JPEG copies of every photo, for the page to show
    python3 arrange.py open "beach" --piece reel       get the page ready and print its address (or --piece carousel)
    python3 arrange.py apply "beach" --piece reel      take the order from the page into the kit; prints the
                                                       picks the way reel.py wants them ("Reel picks: 19,4,10+,14-")
    python3 arrange.py apply "beach" --piece carousel  the carousel: take the order into the kit and make the plain
                                                       slides match it (new ones made, earlier ones set aside,
                                                       nothing deleted). When the final button was pressed and is
                                                       waiting, it is the order the button was pressed on;
                                                       --as-it-is takes the order on the page right now instead.
                                                       --job is how the page's own button runs it, on its own,
                                                       with a status the page reads.
    python3 arrange.py waiting                         orders they pressed "I'm happy with this order" on
    python3 arrange.py took "beach" [--piece reel]     that one has been dealt with
    python3 arrange.py earlier "beach" --piece reel    orders that were replaced (nothing is ever thrown away)

Rules this file keeps:
  * A page names a kit only by its folder name, and a photo only by its number on the kit's numbered list
    (.kit/sheet.json). No route takes a path or a file name, and no answer contains one.
  * The browser only ever gets JPEG copies the Assistant made (.kit/previews), never the photo itself, so a
    HEIC, a TIFF or a 45-megapixel file is safe. The photos folder is never written to.
  * kit.json is written only by commands (this file's main, kit.py), never by the page server.
  * Nothing is deleted or written over. A replaced order goes into the record's "earlier" list.
  * One writer at a time for a kit's arrangement, across processes: the page server and the commands both
    hold <kit>/.kit/arrange.lock (locked()) for every read-change-write of arrange.json.
  * A numbered list that can't be read changes nothing: the record is left exactly as it is.
  * Nothing here exits the process outside main(): a server thread must never bring the server down.

Records:
  <kit>/.kit/previews/NNNN-<520|1600>-<6 hex of the file name>-<bytes>-<mtime ns>.jpg
  <kit>/.kit/previews/NNNN-1600-<the same>.failed     an empty mark: no copy could be made of that photo as it is now
  <kit>/.kit/arrange.json     {"v": 1, "reel": {stamp, synced, names, first, now, happy, earlier, dropped}}
                              now = {nums, marks, rev, by, at, from}: rev is the counter, which only this file
                              moves on (by one, for every accepted change); from = {page, base} says which open
                              page saved it and which counter that page had last seen
  <kit>/.kit/arrange.lock     an empty file the writers hold while they work (never removed)
  <kit>/.kit/arrange-job.json {"state": "queued"|"running"|"done"|"same"|"problem", "line": plain words for the page,
                              "rev": the counter of the order it is for, "count", "pid", "at", "t"}: the slide-making
                              job the carousel's final button starts. "queued" is written by the page server just
                              before it starts the job; everything after by the job itself. On disk, so a server
                              that starts over loses nothing.
  <kit>/.kit/arrange-job.lock an empty file the job holds for as long as it lives (the computer lets go of it when
                              the job ends, however it ends), which is how anyone knows whether a job is still at work
  <kit>/.kit/slides.lock, kit.lock   kit.py's own: held while slides are moved, and while the kit record is read,
                              changed and saved (kit.update_rec), so no writer puts an older copy back over another's
  ~/.studio/arrange-waiting.json   a pointer for Claude: which kit's order is waiting (the order is in the kit)
  ~/.studio/arrange.log       what the page's requests carried (their Origin), for reading after a problem

Python 3.9, standard library only on a Mac. A Mac and a PC (Nov 6):
  * the small copies: on a Mac the Mac's own sips, the same command as always (a sideways photo's copy keeps the
    camera's turn mark, which the browser follows); on a PC pictures.make_jpeg (the JPEG every camera stores
    inside its RAW, or the photo itself, resized with Pillow), turned upright in the pixels themselves. A PC
    without Pillow makes nothing and marks nothing, and says pictures.ready()'s plain words instead.
    On a PC an iPhone photo (HEIC) without its add-on (pillow-heif) is shown as "can't be shown" but gets no
    .failed mark, so it is tried again by the next open once the add-on is there. A PC with long paths off
    (Windows' own setting) whose kit sits too deep for the copies' names (cant_make) makes and marks nothing,
    and says so in plain words; a PC's scratch copy has a short name, so it is never the longest one.
    On a PC a new copy that something holds for longer than this_computer.replace waits (most often the virus
    checker reading a file just written), or that could not be written though the photo opens, is "later": no
    mark, tried again a few seconds on, and otherwise left for the next run. A Mac never gets "later".
  * the background runs' output: on a Mac they write to arrange.log through the server's own handle, as before;
    on a PC they open arrange.log for themselves (_own_output), because Windows' "add at the end" belongs to
    each program's own handle and a shared one would write over the server's lines.
  * the locks: this_computer.try_lock (a Mac's flock, exactly the call made before; a PC's msvcrt.locking).
  * "is that job still running?": a Mac's own waitpid and kill(pid, 0), as before; a PC asks
    this_computer.still_running (and, when it can't say, the job's age decides).
  * the background processes: this_computer.popen_detached (a Mac: start_new_session, as before).
Nothing for a PC here has run on a real PC.
"""
import argparse
import contextlib
import errno
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import kit as kit_mod  # noqa: E402
import pictures  # noqa: E402
import posts  # noqa: E402

this_computer.utf8_output()

# Locks between processes go through this_computer.try_lock (a Mac's flock, the very call made here before Nov 6;
# a PC's msvcrt.locking). This switch is set wherever a lock may be tried; set to None, every writer works under
# this process's own _LOCK alone, as on a drive that has no locks. It keeps the name the Mac-only lock module had
# here, because tests/arrange_check.py (NO_LOCKS) switches the locks off with "arrange.fcntl = None". It is only
# ever an on/off switch now ("fcntl is not None"): nothing here may call fcntl.anything.
fcntl = True

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
WAITING = HOME / "arrange-waiting.json"
LOG = HOME / "arrange.log"

SIZES = {"s": 520, "l": 1600, "x": 2400, "xx": 4320}    # the long edge of each copy, never larger than the photo's own
QUALITY = {520: "82", 1600: "86", 2400: "90", 4320: "92"}     # x and xx are for the designer's finished slides: made only when asked for (big_copy)
PIECES = ("reel", "carousel")           # the pieces that have a page so far
LIMITS = {"reel": {"min": 2, "max": 60, "best": [8, 14]},
          "carousel": {"min": 2, "max": 20, "best": [5, 8]}}
MARKS = ("", "+", "-")                  # Normal, Longer, Quicker: reel.py's own marks
POST_CAP = 65536
DRAIN_CAP = 1_048_576                   # a refused body up to this size is read and dropped, so the answer arrives
KEEP_EARLIER = 5
KEEP_WAITING = 30
LOCK_WAIT = 10.0                        # seconds to wait for another process to let go of a record
BODY_WAIT = 15                          # seconds a POST's body may take to arrive
PAGE_ID = re.compile(r"[A-Za-z0-9]{6,40}")     # the name an open page gives itself (made up afresh on every load)
# The Origin rule is ON. Read from arrange.log on Nov 5, 2026: the Claude app's pane sends
# Origin 'http://127.0.0.1:<port>' and Sec-Fetch-Site 'same-origin' with every save from the picker,
# so a save that names any other Origin is refused. A request with no Origin at all (curl, a script
# on this computer) still passes; the Host check above is what stops those from outside.
ORIGIN_ENFORCED = True

CANT_FIND = "I can't find that shoot's posts. Is the drive plugged in?"
NOT_READY = "This shoot isn't ready for this yet. Say \"make posts from this shoot\" to Claude first."
CANT_REACH = "Could not reach the Assistant. Tell Claude instead."
PHOTOS_CHANGED = "The photos in this shoot changed since this page opened."
NEWER = "This order was changed somewhere else. Here's the newest."
NOT_UNDERSTOOD = "That didn't arrive the way it should have. Reload the page and try again."
TOO_MANY = {"reel": "A reel holds up to 60 photos. Take one out first.",
            "carousel": "Instagram allows up to 20. Take one out first."}       # the page's own words for a full row
# the carousel's final button: what the page shows under it (the job's own words, read from its status)
MAKING = "Making your slides..."
ALREADY_MAKING = "Your slides are already being made. One moment."
IN_ORDER = "Your slides are already in this order."
LEFT_AS_WAS = "Your Carousel folder was left as it was."
NOT_FINISHED = "Couldn't finish changing your slides. Nothing was lost. Tell Claude and it'll sort it out."
IN_THE_WAY = "Couldn't make the slides: a file in your Carousel folder has a name one of the new slides needs. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out."
JOB_STOPPED = "Making your slides was interrupted. Press \"I'm happy with this order\" again and it will finish."
JOB_BOOT = 20.0                         # seconds a job may take to start before "queued" means it never did
JOB_OLD = 300.0                         # where locks can't be used: a job older than this is taken for dead
JOB_LOOPS = 6                           # how many newer orders one job will take on before it stops
LATER_WAITS = (2.0, 4.0)                # a PC only: copies something held ("later") are tried again after these pauses
FULL_BYTES = 50_000_000                 # a PC only: less room than this on the kit's drive, and "later" means a full drive
CHILD_LOG = "ASSISTANT_ARRANGE_OWN_LOG"  # a PC only: set by the server for its background runs (_own_output)

_LOCK = threading.RLock()               # one writer at a time for arrange.json and the waiting list (this process)
_held = {}                              # lock file -> [its open handle, how deep]; only touched while _LOCK is held
_children = {}                          # kit path -> the previews child this server started
_logged = set()


class Busy(Exception):
    """Another process has held a record for longer than LOCK_WAIT."""


@contextlib.contextmanager
def locked(lock_file):
    """One writer at a time for a record, in this process (_LOCK) and across processes (a lock held on
    lock_file by the computer itself, which lets go of it even if the holder dies: this_computer.try_lock). May
    be entered again by the thread that holds it. Where the lock can't be had at all (a drive that has no such
    thing, a folder that can't be written, the switch above set to None), the work goes on under _LOCK alone,
    as before. Raises Busy if another process keeps the record for more than LOCK_WAIT seconds."""
    with _LOCK:
        key = str(lock_file)
        ent = _held.get(key)
        if ent is not None:
            ent[1] += 1
            try:
                yield
            finally:
                ent[1] -= 1
            return
        f = None
        if fcntl is not None:
            try:
                make_folder(lock_file.parent)
                f = open(lock_file, "a", encoding="utf-8")      # never written to: only held
            except OSError:
                f = None
            end = time.time() + LOCK_WAIT
            while f is not None:
                got = this_computer.try_lock(f)
                if got:
                    break
                if got is None:              # this drive has no locks: carry on without one
                    f.close()
                    f = None
                    break
                if time.time() > end:
                    f.close()
                    raise Busy(f"{lock_file.name} was held for more than {LOCK_WAIT:.0f} s")
                time.sleep(0.02)
        _held[key] = [f, 1]
        try:
            yield
        finally:
            _held.pop(key, None)
            if f is not None:
                this_computer.unlock(f)
                f.close()


def make_folder(folder):
    """Make one of the Assistant's own folders if it isn't there yet. A folder inside a kit's hidden folder
    is only ever made when the kit's own folder is there: if the kit has been renamed, or its drive is gone,
    this raises (FileNotFoundError) and makes nothing, so a look-alike of the kit is never left at its old
    address with nothing in it but our records."""
    folder = Path(folder)
    parts = folder.parts
    if ".kit" not in parts:
        folder.mkdir(parents=True, exist_ok=True)
        return
    i = parts.index(".kit")
    d = Path(*parts[:i])
    for part in parts[i:]:
        d = d / part
        d.mkdir(exist_ok=True)          # plain: it fails by itself when the kit's own folder is not there


def kit_lock(kit):
    return kit / ".kit" / "arrange.lock"


WAITING_LOCK = HOME / "arrange-waiting.lock"


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


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def log(line):
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{now_iso()} {line}\n")
    except OSError:
        pass


def write_whole(path, obj):
    """A file written whole or not at all: a temp name no one else is using, then a rename. When it can't be
    written or put in place (a full drive; on a PC, a reader that keeps the real file open for longer than the
    wait), the earlier file is exactly as it was and our own scratch copy is dropped, as kit._write_text_whole
    drops its own: a page that tries again by itself would otherwise leave one more at every try."""
    make_folder(path.parent)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, path)    # a Mac: os.replace; a PC waits a moment while a reader has it open
    except BaseException:
        try:
            tmp.unlink()                    # our own scratch copy, never the real file
        except OSError:
            pass
        raise


# ---------- the kit and its numbered list ----------

def _nfc(s):
    return unicodedata.normalize("NFC", s)


def kit_by_name(name):
    """The kit folder for a name a PAGE sent, or None. Only a folder whose name is exactly in the listing of
    Your Content (same capitals), a real folder and not a link, holding a kit record. Never a path."""
    try:
        if not isinstance(name, str) or not 1 <= len(name) <= 200:
            return None
        if "/" in name or "\\" in name or "\x00" in name or name.startswith("."):
            return None
        h = posts.home()
        if not h:
            return None
        content = h / posts.CONTENT_NAME
        hits = [e for e in os.listdir(content) if _nfc(e) == _nfc(name)]
        if len(hits) != 1:
            return None
        k = content / hits[0]
        if k.is_symlink() or not k.is_dir():
            return None
        if not (k / ".kit" / "kit.json").is_file():
            return None
        return k
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def sheet_rows(kit):
    """The kit's numbered photos, read straight from .kit/sheet.json. An empty list if there is none."""
    try:
        d = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))
        out = []
        for x in d.get("photos", []):
            if isinstance(x, dict) and type(x.get("n")) is int and x["n"] >= 1 and isinstance(x.get("file"), str) and x["file"]:
                out.append(x)
        return out
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def sheet_stamp(kit):
    """A short mark that changes whenever the numbered list does."""
    try:
        return hashlib.sha1((kit / ".kit" / "sheet.json").read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def photo_path(kit, rec, row):
    """Where a numbered photo is now: the kit's photos folder (from the kit record) plus the file's NAME from
    the list. None if it is not a plain file there right now."""
    try:
        name = Path(row["file"]).name
        if not name or name.startswith("."):
            return None
        p = kit_mod.photos_dir(kit, rec) / name
        return p if p.is_file() else None
    except (OSError, KeyError, TypeError, ValueError):
        return None


def photo_name(row):
    return Path(row["file"]).name


# ---------- the small copies the page shows ----------

def previews_dir(kit):
    return kit / ".kit" / "previews"


def _name6(name):
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]


def _key(src):
    st = src.stat()
    return f"{_name6(src.name)}-{st.st_size}-{st.st_mtime_ns}"


def preview_file(kit, row, size, src):
    """The copy of this photo as it is now. Its name carries the photo's size and time, so a re-exported
    photo gets a new copy and none is ever written over."""
    return previews_dir(kit) / f"{row['n']:04d}-{size}-{_key(src)}.jpg"


def failed_mark(kit, row, size, src):
    """An empty file that says "no copy could be made of this photo as it is now", so the page can say so and the
    copies are not tried again on every page load. A re-exported photo has a new name here, so it is tried again."""
    return previews_dir(kit) / f"{row['n']:04d}-{size}-{_key(src)}.failed"


def _older_copy(names, row, size):
    """When the photo itself can't be reached: the newest copy already made for it, by name."""
    prefix = f"{row['n']:04d}-{size}-{_name6(photo_name(row))}-"
    best, best_t = None, -1
    for x in names:
        if x.startswith(prefix) and x.endswith(".jpg"):
            try:
                t = int(x[:-4].rsplit("-", 1)[1])
            except (ValueError, IndexError):
                t = 0
            if t > best_t:
                best, best_t = x, t
    return best


def copy_to_serve(kit, rec, row, size):
    """The file /kit-photo sends, or None: the copy that matches the photo now; if the photo can't be
    reached, the newest copy already made for it."""
    src = photo_path(kit, rec, row)
    d = previews_dir(kit)
    if src is not None:
        try:
            p = preview_file(kit, row, size, src)
            return p if p.is_file() else None
        except OSError:
            pass
    try:
        older = _older_copy(os.listdir(d), row, size)
    except OSError:
        return None
    return d / older if older else None


def _is_jpeg(p):
    try:
        with open(p, "rb") as f:
            return f.read(2) == b"\xff\xd8"
    except OSError:
        return False


def _opens(src):
    """A PC only: can this computer open the photo at all? Asked only after pictures.make_jpeg said no, which it
    says both when the photo can't be opened and when its new copy couldn't be written or put in place (the virus
    checker holding it, a full drive). Only the first is about the photo. pictures.thumb_rows opens it the same
    way make_jpeg does (the same reader, every JPEG a RAW keeps tried in turn), only smaller, so it is quick."""
    try:
        return pictures.thumb_rows(src, 64) is not None
    except Exception:  # noqa: BLE001  (a photo Pillow chokes on is one that can't be opened, never a crash)
        return False


def _jpeg_copy(src, dst, edge, size):
    """One JPEG copy, written under a dot-name and renamed into place only when it is whole.
    A Mac: the Mac's own sips, the same command as always (its copy keeps the photo's turn mark).
    A PC: pictures.make_jpeg, the photo turned upright in the pixels and never made bigger than it is.
    Returns "made", "there" (someone else made it), None (no copy can be made of this photo as it is) or, on a
    PC only, "later": the photo opens, but its new copy couldn't be written or put in place this time."""
    if dst.is_file():
        return "there"
    try:
        make_folder(dst.parent)
    except OSError:
        return None
    later = False
    if pictures.use_sips():
        tmp = dst.with_name(f".part-{os.getpid()}-{threading.get_ident()}-{dst.name}")
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", QUALITY.get(size, "85"), "-Z", str(max(1, edge)), str(src), "--out", str(tmp)]  # pc-ok: a Mac only (pictures.use_sips); a PC goes through pictures.make_jpeg below
        try:
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
            good = r.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 100 and _is_jpeg(tmp)
        except (OSError, subprocess.SubprocessError):
            good = False
    else:
        # unproven on a real PC (run here with sips switched off: ASSISTANT_NO_SIPS=1). The same sizes and
        # quality as the Mac's; make_jpeg writes its own .part file and renames it into tmp when it is whole.
        # A short scratch name (22 characters with make_jpeg's ".part"), unique to this process, thread and copy,
        # so on a PC the longest name written here is the copy's own ".failed" mark, which cant_make has measured.
        tag = hashlib.sha1(f"{os.getpid()}-{threading.get_ident()}-{dst.name}".encode("utf-8")).hexdigest()[:10]
        tmp = dst.with_name(f".p-{tag}.jpg")
        made = None
        try:
            made = pictures.make_jpeg(src, tmp, max(1, edge), int(QUALITY.get(size, "85")))
            good = made and tmp.is_file() and tmp.stat().st_size > 100 and _is_jpeg(tmp)
        except Exception:  # noqa: BLE001  (a picture Pillow chokes on is a photo that can't be read, never a crash)
            good = False
        # make_jpeg said no, yet the photo opens: its copy couldn't be written or put in place this time (the
        # virus checker held it for longer than this_computer.replace waits, a full drive). Not the photo's fault,
        # so it gets no mark. unproven on a real PC.
        later = not good and not made and _opens(src)
    if not good:
        try:
            tmp.unlink()        # our own half-made scratch file
        except OSError:
            pass
        return "later" if later else None
    if dst.exists():
        try:
            tmp.unlink()        # someone made the same copy a moment ago; theirs stays
        except OSError:
            pass
        return "there"
    try:
        this_computer.replace(tmp, dst)
    except PermissionError:
        # A PC only: something (most often the virus checker reading the new copy) held it for longer than
        # this_computer.replace waits. The photo is fine, so no mark: "later". A Mac's os.replace never refuses
        # like this, and anything a Mac raises is raised as before. unproven on a real PC.
        if not this_computer.WINDOWS:
            raise
        try:
            tmp.unlink()        # our own scratch copy (if it is still held, it stays; it is never shown)
        except OSError:
            pass
        return "there" if dst.is_file() else "later"
    return "made"


def needs_addon(src):
    """On a PC: a photo this computer can't open until an add-on is put in (an iPhone photo, HEIC, without
    pillow-heif). It is not tried and gets no .failed mark: that mark is for the photo as it is, and this is
    about the computer, so the next open (a fresh process) tries it again once the add-on is there. The page
    shows it as can't be shown meanwhile. A Mac: never (sips reads HEIC), and nothing is asked."""
    return (not pictures.use_sips() and Path(src).suffix.lower() in pictures.HEIC
            and not pictures.heic_ok())


def _too_deep(kit, rows, rec=None):
    """On a PC with long paths off (Windows' own setting): would the small copies' records sit past Windows'
    260-character limit? The longest of them is a photo's ".failed" mark (the scratch copy's name is shorter on
    a PC: _jpeg_copy), so each photo's mark is measured. A Mac: never, and nothing is measured."""
    if not this_computer.WINDOWS:
        return False
    rec = rec if rec is not None else kit_mod.load_rec(kit)          # unproven on a real PC
    for row in rows:
        src = photo_path(kit, rec, row)
        if src is None:
            continue
        try:
            if this_computer.records_path_too_long(failed_mark(kit, row, SIZES["l"], src)):
                return True
        except OSError:
            continue
    return False


def too_deep_words():
    """What a PC says when _too_deep: the same limit kit.py names when a kit is made, in the same words."""
    try:
        h = posts.home()
        where = f"your \"{h.name}\" folder" if h else "the folder your posts are kept in"
    except (Exception, SystemExit):  # noqa: BLE001
        where = "the folder your posts are kept in"
    pc = this_computer.COMPUTER
    return (f"This shoot's folder sits too deep in other folders for this {pc} to keep the small copies of its "
            f"photos that the page shows (on a {pc} a file's full address, counting the drive, every folder on the "
            f"way and its own name, can be at most 260 characters). Moving {where} nearer the top of the drive, or a "
            "shorter name for this shoot's folder, puts it right. Nothing was changed.")


def cant_make(kit, rows, rec=None):
    """(kind, plain words) when no small copy can be made on this computer at all, else None.
      "addon": a PC without Pillow (pictures.ready()'s words);
      "deep":  a PC with long paths off, and the kit too deep in folders for the copies' names (_too_deep).
    Nothing is made or marked then. A Mac: always None, with nothing measured."""
    can, words = pictures.ready()
    if not can:
        return "addon", words
    if _too_deep(kit, rows, rec):
        return "deep", too_deep_words()
    return None


def make_one(kit, row, size, src=None, rec=None, retry=False):
    """One copy of one photo. 1600 comes from the photo; 520 comes from the 1600 copy. The long edge is never
    larger than the photo's own (sips would blow a small photo up; on a PC pictures.make_jpeg never does, so
    nothing is measured there). Returns "made", "there" or None; on a PC also "later" (_jpeg_copy), which gets
    no mark."""
    if src is None:
        src = photo_path(kit, rec or kit_mod.load_rec(kit), row)
    if src is None:
        return None
    try:
        dst = preview_file(kit, row, size, src)
        mark = failed_mark(kit, row, SIZES["l"], src)
    except OSError:
        return None
    if dst.is_file():
        return "there"
    if needs_addon(src):
        return None             # a PC: not tried, and no mark, so it is tried once the add-on is there
    if mark.exists() and not retry:
        return None
    if pictures.use_sips():
        own = max(row.get("w") or 0, row.get("h") or 0)
        try:
            listed_before = (kit / ".kit" / "sheet.json").stat().st_mtime >= src.stat().st_mtime
        except OSError:
            listed_before = False
        if own <= 0 or not listed_before:
            # no size on the list, or the photo was exported again after it was listed: measure it
            got = kit_mod.size_of(src)
            own = max(got) if got else own
        edge = min(size, own) if own > 0 else size
    else:
        # a PC: Pillow keeps a photo smaller than this at its own size. Not measured, so a size on the list that
        # is wrong for a RAW (a thumbnail's, read as the photo's) can never make the copy smaller than it should be.
        edge = size
    if size >= SIZES["l"]:      # the 1600 copy, and the designer's two larger ones, are made from the photo itself
        got = _jpeg_copy(src, dst, edge, size)
        if got is None and size == SIZES["l"]:      # only the 1600 copy failing marks a photo unreadable
            try:
                make_folder(mark.parent)
                mark.touch()
            except OSError:
                pass
        return got
    big = preview_file(kit, row, SIZES["l"], src)
    if not big.is_file():
        first = make_one(kit, row, SIZES["l"], src, retry=retry)
        if first is None or first == "later":       # "later": a PC only; the big copy isn't there to make it from
            return first
    return _jpeg_copy(big, dst, edge, size)


def make_previews(kit, workers=4, retry=False):
    """Both copies of every photo on the list, four at a time. Copies already there are left alone. A photo
    no copy could be made of last time is skipped unless retry is set (the command sets it; the page's own
    background run does not, so an unreadable photo is not tried on every page load).
    A computer that can't make pictures at all (a PC without Pillow, or a kit too deep in folders for a PC's
    limit: cant_make) makes nothing and marks nothing: "cant" then holds the plain words and "cant_kind" says
    which ("addon" or "deep"), and the copies are made once that is put right. On a PC, "why" holds
    pictures.why_not's words for a photo that could not be read, an add-on's words first, and "later" counts the
    photos whose copies something kept busy even after LATER_WAITS (no mark: the next run makes them); "full" is
    True when the kit's drive has (all but) no room left, which is then why, and nothing waits. A Mac never sets
    any of these."""
    t0 = time.time()
    rec = kit_mod.load_rec(kit)
    rows = sheet_rows(kit)
    out = {"made": 0, "there": 0, "missing": 0, "failed": 0, "of": len(rows)}
    cant = cant_make(kit, rows, rec)
    if cant:
        kind, words = cant
        for row in rows:
            src = photo_path(kit, rec, row)
            try:
                # the two copies a page shows. The designer's two larger ones are made only when a finished slide
                # asks for one (big_copy), so a photo without them is still a photo that is there.
                have = src is not None and all(preview_file(kit, row, s, src).is_file() for s in (SIZES["s"], SIZES["l"]))
            except OSError:
                have = False
            if src is None:
                out["missing"] += 1
            elif have:
                out["there"] += 1
            else:
                out["cant"], out["cant_kind"] = words, kind
        out["seconds"] = round(time.time() - t0, 2)
        return out

    def one(row):
        src = photo_path(kit, rec, row)
        if src is None:
            return "missing"
        a = make_one(kit, row, SIZES["l"], src, retry=retry)
        b = make_one(kit, row, SIZES["s"], src, retry=retry) if a in ("made", "there") else None
        if "later" in (a, b):
            return "later"      # a PC only: no mark, and no "why" (the photo itself opens)
        if not a or not b:
            # unproven on a real PC. The words for a missing add-on win: they say what puts it right.
            if not a and not pictures.use_sips() and ("why" not in out or needs_addon(src)):
                out["why"] = pictures.why_not(src)
            return "failed"
        return "made" if "made" in (a, b) else "there"

    if rows:
        try:
            make_folder(previews_dir(kit))
        except OSError:
            rows = []                   # the kit's folder is not there right now: nothing to make, and nothing is made
            out["missing"] = out["of"]
    if rows:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            got = list(ex.map(one, rows))
            # A PC only (a Mac never gets "later", so this asks nothing there and never waits): a copy something
            # held is tried again after a short pause, twice at most, then left for the next run.
            for pause in LATER_WAITS:
                again = [i for i, res in enumerate(got) if res == "later"]
                if not again:
                    break
                if _drive_full(kit):
                    out["full"] = True  # waiting won't make room: say so, and leave them for the next run
                    break
                time.sleep(pause)
                for i, res in zip(again, ex.map(one, [rows[i] for i in again])):
                    got[i] = res
        for res in got:
            out[res] = out.get(res, 0) + 1
    out["seconds"] = round(time.time() - t0, 2)
    return out


def _drive_full(kit):
    """A PC only, asked once copies came back "later": is the kit's drive full (under FULL_BYTES free)? A copy that
    couldn't be written is then most likely that, not the virus checker, and a pause won't help."""
    try:
        free = this_computer.free_bytes(kit)
    except OSError:
        return False
    return free is not None and free < FULL_BYTES


def _child_env():
    """What the server adds when it starts a background run (the small copies, the slide job). A Mac: nothing,
    exactly as before. A PC: a note telling the run to write to arrange.log through a handle of its own
    (_own_output). The run is still given the server's handle too, so a run that fails before it gets that far
    still leaves its words in the log."""
    if not this_computer.WINDOWS:
        return {}
    return {"env": dict(os.environ, **{CHILD_LOG: "1"})}         # unproven on a real PC


def _own_output():
    """A PC only, in a background run the server started (_child_env): from here on, its output goes into
    arrange.log through a handle of its own, opened to add at the end.

    Why: the server hands the run its own handle to arrange.log as the run's output. On a Mac that handle adds at
    the end for everyone who shares it. On a PC "add at the end" is done by each program for its own handles, and
    a handle passed to another program keeps one place in the file for both (Microsoft's DuplicateHandle and
    _open pages), so the run would write over any line the server or another run added since it started."""
    if not (this_computer.WINDOWS and os.environ.get(CHILD_LOG) == "1"):
        return
    os.environ.pop(CHILD_LOG, None)          # not passed on to anything this run starts
    try:                                     # unproven on a real PC
        f = open(LOG, "a", encoding="utf-8", buffering=1)   # line by line, each one added at the end as it is written
    except OSError:
        return                               # the server's handle stays: the run's words still reach the log
    sys.stdout = sys.stderr = f


def start_previews(kit):
    """From the server: make the copies in a process of their own, so no request waits on them."""
    with _LOCK:
        old = _children.get(str(kit))
        if old is not None and old.poll() is None:
            return False
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            with open(LOG, "a", encoding="utf-8") as out:        # the child keeps its own handle; ours is closed again
                # a Mac: start_new_session, exactly as before; a PC: no window, a process group of its own
                _children[str(kit)] = this_computer.popen_detached(
                    [sys.executable, str(HERE / "arrange.py"), "previews", str(kit), "--quiet-on-unreadable"],
                    stdout=out, stderr=subprocess.STDOUT, **_child_env())
            return True
        except OSError:
            return False


_BIG = threading.Lock()                 # one large copy at a time: sips on a 45-megapixel photo is heavy


def big_copy(kit, rec, row, size):
    """The designer's two larger copies (2400 and 4320 on the long edge), made the first time one is asked
    for, one at a time. A photo that is no larger than the next size down already has all of itself in that
    copy, so that copy is the answer and no second one is made. Returns the file to send, or None.
    A PC only: a copy something kept busy ("later": the photo is fine, the virus checker held its new copy) is
    tried again after LATER_WAITS, as the pickers' copies are, before the answer is None. A Mac never waits."""
    own = max(row.get("w") or 0, row.get("h") or 0)
    while size > SIZES["l"]:
        below = max(v for v in SIZES.values() if v < size)
        if not 0 < own <= below:
            break
        size = below
    f = copy_to_serve(kit, rec, row, size)
    if f is None:
        with _BIG:
            got = make_one(kit, row, size, rec=rec)
            for pause in LATER_WAITS:   # a PC only (a Mac never gets "later", so this never waits there)
                if got != "later":
                    break
                time.sleep(pause)
                got = make_one(kit, row, size, rec=rec)
            if got is None:
                return None
        f = copy_to_serve(kit, rec, row, size)
    return f


# ---------- the record of an arrangement ----------

def arrange_path(kit):
    return kit / ".kit" / "arrange.json"


def load(kit):
    try:
        d = json.loads(arrange_path(kit).read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except (OSError, ValueError):
        pass
    return {"v": 1}


def save(kit, data):
    with _LOCK:
        data["v"] = 1
        write_whole(arrange_path(kit), data)


def pick_text(nums, marks=None):
    """An order the way reel.py reads it: 19,4,10+,14-"""
    marks = list(marks or []) + [""] * len(nums)
    return ",".join(f"{n}{marks[i] if marks[i] in ('+', '-') else ''}" for i, n in enumerate(nums))


def kit_pick(rec, piece):
    """The kit's own pick for a piece: the numbers, and for a reel the mark beside each."""
    nums = [n for n in ((rec.get("picks") or {}).get(piece) or []) if type(n) is int]
    seen, clean = set(), []
    for n in nums:
        if n not in seen:
            seen.add(n)
            clean.append(n)
    rm = rec.get("reel_marks") or {}
    marks = [(rm.get(str(n)) if rm.get(str(n)) in ("+", "-") else "") if piece == "reel" else "" for n in clean]
    return clean, marks


def _order(nums, marks, **more):
    d = {"nums": list(nums), "marks": list(marks), "at": now_iso()}
    d.update(more)
    return d


def _same(a, b):
    return list(a.get("nums") or []) == list(b.get("nums") or []) and list(a.get("marks") or []) == list(b.get("marks") or [])


def _keep_earlier(p, order, why, **more):
    e = {"nums": list(order["nums"]), "marks": list(order["marks"]), "at": order.get("at"), "by": order.get("by", "you"),
         "why": why, "replaced": now_iso()}
    e.update(more)
    p["earlier"] = (list(p.get("earlier") or []) + [e])[-KEEP_EARLIER:]


def _names_for(p, name_of):
    """File names for every number the record mentions, so a re-made list can find the same photos again."""
    used = set(p["first"]["nums"]) | set(p["now"]["nums"])
    for e in p.get("earlier") or []:
        used |= set(e["nums"])
    old = p.get("names") or {}
    return {str(n): name_of.get(n) or old.get(str(n)) for n in sorted(used) if name_of.get(n) or old.get(str(n))}


def sync(kit, piece):
    """Bring the record in line with the kit. Returns (the whole record, this piece's part).
      * no record yet: the first pick and the current one are the kit's pick
      * the kit's pick is not what this record last saw (Claude picked afresh): the current order is kept in
        "earlier" if it was theirs, then first and current become the kit's pick
      * the numbered list was re-made: every number is found again by file name; a photo that is no longer
        in the shoot is taken out and named in "dropped", and the order as it was is kept in "earlier"
      * the numbered list can't be read right now: NOTHING is changed, and this piece's part comes back as
        None (the caller says "not ready"). An unreadable list must never be taken for an empty shoot.
    """
    with locked(kit_lock(kit)):
        data = load(kit)
        rows = sheet_rows(kit)
        stamp = sheet_stamp(kit)
        if not rows or not stamp:
            return data, None
        name_of = {x["n"]: photo_name(x) for x in rows}
        rec = kit_mod.load_rec(kit)
        nums, marks = kit_pick(rec, piece)
        text = pick_text(nums, marks)
        p = data.get(piece)
        changed = False
        ok_shape = (isinstance(p, dict) and isinstance(p.get("now"), dict) and isinstance(p.get("first"), dict)
                    and isinstance(p["now"].get("nums"), list) and isinstance(p["first"].get("nums"), list))
        if not ok_shape:
            keep = [(n, m) for n, m in zip(nums, marks) if n in name_of]
            ns, ms = [k[0] for k in keep], [k[1] for k in keep]
            p = {"stamp": stamp, "synced": text, "names": {},
                 "first": _order(ns, ms), "now": _order(ns, ms, rev=0, by="assistant"),
                 "happy": None, "earlier": [], "dropped": [], "dropped_nums": []}
            p["names"] = _names_for(p, name_of)
            data[piece] = p
            changed = True
        else:
            p.setdefault("earlier", [])
            p.setdefault("dropped", [])
            p.setdefault("dropped_nums", [])
            p.setdefault("names", {})
            p["now"].setdefault("marks", [""] * len(p["now"]["nums"]))
            p["first"].setdefault("marks", [""] * len(p["first"]["nums"]))
            p["now"].setdefault("rev", 0)
            if p.get("stamp") != stamp:
                # the list was re-made: find each photo again by its file name
                n_of = {}
                for x in rows:
                    n_of.setdefault(photo_name(x), x["n"])
                old_names = p.get("names") or {}
                gone, gone_nums = [], []

                def refind(order, note=False):
                    ns, ms = [], []
                    for i, n in enumerate(order["nums"]):
                        nm = old_names.get(str(n))
                        new_n = n_of.get(nm) if nm else None
                        if new_n is None or new_n in ns:
                            if note and nm and nm not in gone:
                                gone.append(nm)
                                gone_nums.append(n)
                            elif note and not nm:
                                gone_nums.append(n)
                            continue
                        ns.append(new_n)
                        ms.append(order["marks"][i] if i < len(order["marks"]) else "")
                    order["nums"], order["marks"] = ns, ms

                was = {"nums": list(p["now"]["nums"]), "marks": list(p["now"]["marks"]), "at": p["now"].get("at"), "by": p["now"].get("by", "you")}
                was_files = [(old_names.get(str(n)) or "?") + (was["marks"][i] if i < len(was["marks"]) and was["marks"][i] in ("+", "-") else "")
                             for i, n in enumerate(was["nums"])]
                refind(p["first"])
                refind(p["now"], note=True)
                for e in p["earlier"]:
                    refind(e)
                if len(p["now"]["nums"]) != len(was["nums"]):
                    # photos left the shoot: keep the order as it was. Its numbers are the ones that are still
                    # here (in the new numbering); "was" is the whole order by file name, marks in place.
                    _keep_earlier(p, dict(was, nums=list(p["now"]["nums"]), marks=list(p["now"]["marks"])),
                                  "photos left the shoot", was=was_files)
                p["now"].pop("from", None)      # no open page has seen this order
                p["names"] = {}
                p["names"] = _names_for(p, name_of)
                p["stamp"] = stamp
                p["dropped"] = gone
                p["dropped_nums"] = gone_nums
                p["now"]["rev"] = int(p["now"].get("rev") or 0) + 1
                p["now"]["at"] = now_iso()
                changed = True
            if text != p.get("synced"):
                # Claude picked afresh: that pick wins, and theirs is kept
                keep = [(n, m) for n, m in zip(nums, marks) if n in name_of]
                ns, ms = [k[0] for k in keep], [k[1] for k in keep]
                fresh_order = {"nums": ns, "marks": ms}
                if p["now"].get("by") == "you" and not _same(p["now"], fresh_order):
                    _keep_earlier(p, p["now"], "a fresh pick replaced it")
                rev = int(p["now"].get("rev") or 0) + 1
                p["first"] = _order(ns, ms)
                p["now"] = _order(ns, ms, rev=rev, by="assistant")
                p["happy"] = None
                p["synced"] = text
                p["dropped"], p["dropped_nums"] = [], []
                p["names"] = _names_for(p, name_of)
                changed = True
        if changed:
            save(kit, data)
        return data, p


def state_for_page(kit, piece):
    """Everything the page draws from. No path and no file name is in it. None when the numbered list can't
    be read right now."""
    data, p = sync(kit, piece)
    if p is None:
        return None
    rec = kit_mod.load_rec(kit)
    rows = sheet_rows(kit)
    try:
        names = set(os.listdir(previews_dir(kit)))
    except OSError:
        names = set()
    photos, made = [], 0
    small = SIZES["s"]
    for row in rows:
        src = photo_path(kit, rec, row)
        have, v, unreadable = False, "", False
        if src is not None:
            try:
                fname = preview_file(kit, row, small, src).name
                have = fname in names
                v = hashlib.sha1(fname.encode("utf-8")).hexdigest()[:8]
                # can't be shown: a .failed mark, or (a PC only) an add-on this computer is still missing
                unreadable = not have and (failed_mark(kit, row, SIZES["l"], src).name in names or needs_addon(src))
            except OSError:
                src = None
        if src is None:
            older = _older_copy(names, row, small)
            have = bool(older)
            v = hashlib.sha1(older.encode("utf-8")).hexdigest()[:8] if older else ""
        made += 1 if have else 0
        # "missing" is what the page calls a photo it can't show the real thing of: it can't be reached right
        # now, or it is there and can't be read
        photos.append({"n": row["n"], "way": row.get("way") or "", "w": row.get("w") or 0, "h": row.get("h") or 0,
                       "v": v, "missing": src is None or unreadable, "have": have})
    # "happy" is for the line under the final button, and goes to the page only while that order is still
    # waiting for Claude. Once it has been taken (apply) or put aside (took), nothing is waiting any more.
    happy = p.get("happy") if any(w["kit"] == kit.name and w["piece"] == piece for w in waiting()) else None
    return {
        "ok": True, "name": rec.get("name") or kit.name, "piece": piece, "stamp": p["stamp"],
        "rev": int(p["now"].get("rev") or 0), "total": len(rows), "photos": photos,
        "first": {"nums": p["first"]["nums"], "marks": p["first"]["marks"]},
        "now": {"nums": p["now"]["nums"], "marks": p["now"]["marks"]},
        "happy": {"rev": happy["rev"]} if isinstance(happy, dict) and type(happy.get("rev")) is int else None,
        "dropped": list(p.get("dropped_nums") or []) or [0] * len(p.get("dropped") or []),
        "limits": LIMITS[piece], "previews": {"made": made, "of": len(rows)}, "job": job_for_page(kit, piece),
        "reel_made": bool(rec.get("reel")), "canva": kit_mod.canva_behind(rec),
        "kit_page": kit_mod.rec_path(kit).with_name("Post kit.html").is_file(),
    }


# ---------- what is waiting for Claude ----------

def waiting():
    """Orders they pressed the final button on, oldest first. A pointer only; the order is in the kit."""
    try:
        d = json.loads(WAITING.read_text(encoding="utf-8"))
        return [x for x in d if isinstance(x, dict) and x.get("kit") and x.get("piece")] if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def waiting_line(w):
    n = w.get("count") or 0
    return (f"ARRANGED: {w['kit']} | {w['piece']} | {n} {'slide' if w['piece'] == 'design' else 'photo'}{'s' if n != 1 else ''}"
            + (f" | {w['base']}" if w.get("base") else ""))      # a set of laid-out slides is named, last


def add_waiting(kit_name, name, piece, count, base=None):
    with locked(WAITING_LOCK):
        rest = [x for x in waiting() if not (x["kit"] == kit_name and x["piece"] == piece)]
        rest.append({"kit": kit_name, "name": name, "piece": piece, "count": count, "at": now_iso()})
        if base:
            rest[-1]["base"] = str(base)                         # the name the slides were saved under (design.py)
        write_whole(WAITING, rest[-KEEP_WAITING:])


def took(kit_name, piece=None):
    """Claude has dealt with this one. Returns how many entries were cleared."""
    with locked(WAITING_LOCK):
        was = waiting()
        rest = [x for x in was if not (x["kit"] == kit_name and (piece is None or x["piece"] == piece))]
        if len(rest) != len(was):
            write_whole(WAITING, rest)
        return len(was) - len(rest)


# ---------- the carousel's slide-making job ----------

def job_path(kit):
    return kit / ".kit" / "arrange-job.json"


def job_lock(kit):
    return kit / ".kit" / "arrange-job.lock"


def read_job(kit):
    try:
        j = json.loads(job_path(kit).read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def write_job(kit, state, line, rev, count=0):
    write_whole(job_path(kit), {"state": state, "line": line, "rev": rev, "count": count, "pid": os.getpid(),
                                "at": now_iso(), "t": time.time()})


def _pid_alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if this_computer.WINDOWS:
        # unproven on a real PC. Never os.kill there (signal 0 is Ctrl+C on Windows): the process is opened only
        # to read whether it has ended. When the PC can't say, True, and the job's age decides (JOB_OLD).
        alive = this_computer.still_running(pid)
        return True if alive is None else alive
    try:
        got, _ = os.waitpid(pid, os.WNOHANG)      # pc-ok: a Mac (and Linux) only, a PC returned above. A job this server started and that has ended is cleared away here
        return got != pid
    except ChildProcessError:
        pass                                       # not ours to wait for: ask the Mac whether it exists
    except OSError:
        return False
    try:
        os.kill(pid, 0)                            # pc-ok: a Mac (and Linux) only, a PC returned above
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def job_running(kit):
    """Is a slide-making job at work on this kit right now? The job holds a lock on .kit/arrange-job.lock for
    as long as it lives; anyone asking tries to share that lock for an instant (on a PC, which has no shared
    lock, it takes it for an instant and lets go at once). Where locks can't be used (a drive without them),
    the job's own number is asked after instead, for at most five minutes."""
    with _LOCK:
        if fcntl is not None:
            try:
                with open(job_lock(kit), "a", encoding="utf-8") as f:     # never written to: only looked at
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
        return time.time() - float(j.get("t") or 0) < JOB_OLD and (j.get("state") == "queued" or _pid_alive(j.get("pid")))


def job_for_page(kit, piece):
    """The job as the page should see it: its state, its plain line, and the counter of the order it is for.
    A job that says it is at work but is not (it was killed, or the computer was shut down) is told as a problem,
    with what to do about it. No path, no file name, no process number."""
    if piece != "carousel":
        return None
    j = read_job(kit)
    if not j or j.get("state") not in ("queued", "running", "done", "same", "problem"):
        return None
    state, line = j["state"], j.get("line") or ""
    if state in ("queued", "running") and not job_running(kit):
        if state == "running" or time.time() - float(j.get("t") or 0) > JOB_BOOT:
            state, line = "problem", JOB_STOPPED
    return {"state": state, "line": line, "rev": j.get("rev") if type(j.get("rev")) is int else -1, "count": j.get("count") or 0}


def start_job(kit):
    """From the server: the slides are made in a process of their own, so no request waits on them and a
    server that starts over does not take the work down with it."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as out:
            # a Mac: start_new_session, exactly as before; a PC: no window, a process group of its own
            this_computer.popen_detached([sys.executable, str(HERE / "arrange.py"), "apply", str(kit), "--piece", "carousel", "--job"],
                                         stdout=out, stderr=subprocess.STDOUT, **_child_env())
        return True
    except OSError as e:
        log(f"the slide job could not be started: {e}")
        return False


def carousel_done(kit, rev, nums):
    """The carousel's final button, on the server, with the kit's arrangement held. Returns what the page is
    told: {"job": is a job at work for this, "same": the slides were already in this order, "line": words}.
      * a job is already at work: it is left to it (before it stops, the job looks for a newer order)
      * the slides are already in this order: nothing is started
      * otherwise the job is written down as queued and started."""
    if job_running(kit):
        return {"job": True, "same": False, "line": ALREADY_MAKING}
    j = read_job(kit) or {}
    if j.get("state") == "queued" and j.get("rev") == rev and time.time() - float(j.get("t") or 0) < JOB_BOOT:
        return {"job": True, "same": False, "line": MAKING}        # started a moment ago and still getting going
    if kit_mod.carousel_in_order(kit, nums):
        write_job(kit, "same", IN_ORDER, rev, len(nums))
        return {"job": False, "same": True, "line": IN_ORDER}
    write_job(kit, "queued", MAKING, rev, len(nums))
    if not start_job(kit):
        write_job(kit, "problem", "Couldn't make the slides. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out.", rev, len(nums))
        return {"job": False, "same": False, "line": "Couldn't make the slides. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out."}
    return {"job": True, "same": False, "line": MAKING}


# ---------- the routes ----------

def _send_json(handler, obj, code=200):
    out = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(out)))
    handler.end_headers()
    handler.wfile.write(out)


def _send_page(handler, text):
    out = text.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(out)))
    handler.end_headers()
    handler.wfile.write(out)


def _one(q, key):
    v = q.get(key, [""])
    return v[0] if v else ""


def _get_photo(handler, q):
    if (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
        return handler.send_error(403)      # a picture asked for by another website through the browser: not theirs to show
    kit = kit_by_name(_one(q, "kit"))
    n_txt, size = _one(q, "n"), SIZES.get(_one(q, "size"))
    if kit is None or size is None or not re.fullmatch(r"[0-9]{1,6}", n_txt):
        return handler.send_error(404)
    n = int(n_txt)
    row = next((x for x in sheet_rows(kit) if x["n"] == n), None)
    if row is None:
        return handler.send_error(404)
    f = copy_to_serve(kit, kit_mod.load_rec(kit), row, size)
    if f is None and size > SIZES["l"]:
        f = big_copy(kit, kit_mod.load_rec(kit), row, size)
    if f is None:
        return handler.send_error(404)
    try:
        data = f.read_bytes()
    except OSError:
        return handler.send_error(404)
    if data[:2] != b"\xff\xd8":
        return handler.send_error(404)
    handler.send_response(200)
    handler.send_header("Content-Type", "image/jpeg")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=604800")
    handler.send_header("Cross-Origin-Resource-Policy", "same-origin")
    handler.end_headers()
    handler.wfile.write(data)


def _get_state(handler, q):
    kit = kit_by_name(_one(q, "kit"))
    if kit is None:
        return _send_json(handler, {"ok": False, "words": CANT_FIND}, 404)
    piece = _one(q, "page")
    if piece not in PIECES:
        return _send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    st = state_for_page(kit, piece) if sheet_rows(kit) else None
    if st is None:
        return _send_json(handler, {"ok": False, "words": NOT_READY}, 404)
    _send_json(handler, st)


def _get_page(handler, q):
    import arrange_page
    kit = kit_by_name(_one(q, "kit"))
    if kit is None:
        return _send_page(handler, arrange_page.plain_page(CANT_FIND))
    piece = _one(q, "piece")
    rows = sheet_rows(kit)
    if piece not in PIECES or not rows:
        return _send_page(handler, arrange_page.plain_page(NOT_READY))
    st = state_for_page(kit, piece)
    if st is None:
        return _send_page(handler, arrange_page.plain_page(NOT_READY))
    to_make = any(not x["have"] and not x["missing"] for x in st["photos"])
    if to_make:
        # a PC without Pillow, or a kit too deep in folders for a PC: say so, rather than "getting your photos
        # ready" for ever. A Mac: never.
        cant = cant_make(kit, rows)
        if cant:
            return _send_page(handler, arrange_page.plain_page(cant[1] + " Tell Claude and it'll sort it out."))
    if st["previews"]["made"] < st["previews"]["of"] and to_make:
        start_previews(kit)
    _send_page(handler, arrange_page.page_html(kit.name, piece))


def our_host(handler):
    """Was this request sent to this server by its own name (127.0.0.1 or localhost, and this port)? A web
    page on another site that has been pointed at this computer by a trick of names still carries its own name
    here, and gets nothing: no state, no photo, no save."""
    port = handler.server.server_address[1]
    host = (handler.headers.get("Host") or "").strip().lower()
    return host in (f"127.0.0.1:{port}", f"localhost:{port}")


def handle_get(handler, path, query):
    """Every GET for the arranging pages. Whatever goes wrong, the server answers and stays up."""
    try:
        if not our_host(handler):
            return handler.send_error(403)
        q = parse_qs(query or "", keep_blank_values=True)
        if path == "/kit-photo":
            return _get_photo(handler, q)
        if path == "/arrange-state":
            return _get_state(handler, q)
        if path == "/arrange.html":
            return _get_page(handler, q)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path == "/kit-photo":
                handler.send_error(404)
            elif path.endswith(".html"):
                import arrange_page
                _send_page(handler, arrange_page.plain_page(CANT_FIND))
            else:
                _send_json(handler, {"ok": False, "words": CANT_REACH}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _log_origin(handler, path, would_pass):
    key = (path, handler.headers.get("Origin"), handler.headers.get("Sec-Fetch-Site"), would_pass)
    if key in _logged:
        return
    _logged.add(key)
    log(f"origin: POST {path} Origin={handler.headers.get('Origin')!r} Sec-Fetch-Site={handler.headers.get('Sec-Fetch-Site')!r} "
        f"Host={handler.headers.get('Host')!r} User-Agent={(handler.headers.get('User-Agent') or '')[:60]!r} "
        f"would-pass={'yes' if would_pass else 'NO'} enforced={'yes' if ORIGIN_ENFORCED else 'no'}")


def guard(handler, kind, cap, path=""):
    """Is this POST one of ours? None if it may go on, otherwise (status, plain words).
    Host must be this server; an Origin, when sent, must be this server too (logged only until the pane's
    own has been read); the type must be the one the route takes; the length must be given, above zero and
    under the cap, and is checked before a byte is read."""
    port = handler.server.server_address[1]
    hosts = (f"127.0.0.1:{port}", f"localhost:{port}")
    if not our_host(handler):
        return 403, NOT_UNDERSTOOD
    origin = handler.headers.get("Origin")
    origin_ok = origin is None or origin.strip().lower() in tuple("http://" + h for h in hosts)
    _log_origin(handler, path, origin_ok)
    if ORIGIN_ENFORCED and not origin_ok:
        return 403, NOT_UNDERSTOOD
    ctype = (handler.headers.get("Content-Type") or "").strip().lower()
    if not ctype.startswith(kind):
        return 415, NOT_UNDERSTOOD
    raw = (handler.headers.get("Content-Length") or "").strip()
    if not re.fullmatch(r"[0-9]{1,12}", raw) or int(raw) <= 0:
        return 400, NOT_UNDERSTOOD
    if int(raw) > cap:
        return 413, NOT_UNDERSTOOD
    return None


def _drain(handler):
    """Read and drop a refused body (when it is small and its length is known), so the answer reaches the page."""
    raw = (handler.headers.get("Content-Length") or "").strip()
    if re.fullmatch(r"[0-9]{1,12}", raw) and 0 < int(raw) <= DRAIN_CAP:
        left = int(raw)
        try:
            while left > 0:
                got = handler.rfile.read(min(65536, left))
                if not got:
                    break
                left -= len(got)
        except OSError:
            pass


def _bad(words=NOT_UNDERSTOOD, code=400, **more):
    d = {"ok": False, "words": words}
    d.update(more)
    return code, d


def save_from_page(body):
    """One save from the picker page. Returns (status, answer). Checks in order: the kit, the piece, the
    photo list's stamp, the numbers, the marks, what the page had last seen, and the final button's own rule.

    The counter is this file's alone: an accepted change makes it one higher, and the answer carries it. A
    page sends "base", the counter it was last told, and "page", the name it gave itself when it loaded.
    A change is taken only from a page that has seen the stored order:
      * base is the stored counter, or
      * the stored order is that same page's own last save from that same base (its answer never arrived,
        and the page has carried on from there).
    Anything else is told there is something newer, and given it. Sending exactly what is stored is always
    fine and writes nothing."""
    kit = kit_by_name(body.get("kit"))
    if kit is None:
        return _bad(CANT_FIND, 404)
    piece = body.get("piece")
    if piece not in PIECES:
        return _bad()
    rows = sheet_rows(kit)
    if not rows:
        return _bad(NOT_READY, 404)
    on_sheet = {x["n"]: x for x in rows}
    with locked(kit_lock(kit)):
        data, p = sync(kit, piece)
        if p is None:
            return _bad(NOT_READY, 404)
        if body.get("stamp") != p["stamp"]:
            return _bad(PHOTOS_CHANGED, 409, why="photos")
        nums = body.get("nums")
        lim = LIMITS[piece]
        if not isinstance(nums, list):
            return _bad()
        # More than this piece holds is refused, with one way through: an order that is ALREADY over-long
        # (an older pick of Claude's) may be re-ordered and made shorter here, never longer, so the page can
        # be used to bring it down. The final button stays refused until it fits, with the reason said.
        if len(nums) > lim["max"] and len(nums) > len(p["now"]["nums"]):
            return _bad()
        if any(type(n) is not int or n not in on_sheet for n in nums) or len(set(nums)) != len(nums):
            return _bad()
        marks = body.get("marks")
        if piece == "reel":
            if not isinstance(marks, list) or len(marks) != len(nums) or any(m not in MARKS or not isinstance(m, str) for m in marks):
                return _bad()
        else:
            marks = [""] * len(nums)
        base = body.get("base")
        if type(base) is not int or base < 0:
            return _bad()
        page = body.get("page")
        if not isinstance(page, str) or not PAGE_ID.fullmatch(page):
            return _bad()
        done = body.get("done", False)
        if type(done) is not bool:
            return _bad()
        if done and len(nums) < lim["min"]:
            return _bad()
        if done and len(nums) > lim["max"]:
            return _bad(TOO_MANY[piece], 400, why="many")
        stored = p["now"]
        stored_rev = int(stored.get("rev") or 0)
        same = stored["nums"] == nums and stored["marks"] == marks
        src = stored.get("from") if isinstance(stored.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not same and base != stored_rev and not own:
            return _bad(NEWER, 409, why="newer", state=state_for_page(kit, piece))
        rec_name = kit_mod.load_rec(kit).get("name") or kit.name
        answer = {"ok": True, "words": "Saved", "job": False}
        if same:
            # what is stored already (the same save arriving twice because its answer was lost): nothing to write
            if done:
                if (p.get("happy") or {}).get("rev") != stored_rev:
                    p["happy"] = {"rev": stored_rev, "at": now_iso(), "nums": list(nums), "stamp": p["stamp"]}
                    save(kit, data)
                add_waiting(kit.name, rec_name, piece, len(nums))
                if piece == "carousel":
                    answer.update(carousel_done(kit, stored_rev, nums))
            return 200, dict(answer, rev=stored_rev)
        rev = stored_rev + 1
        new = {"nums": nums, "marks": marks}
        is_first = _same(new, p["first"])
        if stored.get("by") == "you" and is_first:
            _keep_earlier(p, stored, "back to the first pick")
        p["now"] = _order(nums, marks, rev=rev, by="assistant" if is_first else "you", **{"from": {"page": page, "base": base}})
        if done:
            # the order the button was pressed on is kept with it (and which numbered list its numbers are
            # from): the carousel's job makes exactly that one
            p["happy"] = {"rev": rev, "at": now_iso(), "nums": list(nums), "stamp": p["stamp"]}
        p["dropped"], p["dropped_nums"] = [], []
        p["names"] = _names_for(p, {n: photo_name(x) for n, x in on_sheet.items()})
        save(kit, data)
        if done:
            add_waiting(kit.name, rec_name, piece, len(nums))
            if piece == "carousel":
                answer.update(carousel_done(kit, rev, nums))
        return 200, dict(answer, rev=rev)


def _post_arrange(handler):
    try:
        handler.connection.settimeout(BODY_WAIT)    # a body that never arrives must not hold a thread for ever,
    except (OSError, AttributeError):               # whether the request is one of ours or one being refused
        pass
    bad = guard(handler, "application/json", POST_CAP, "/arrange")
    if bad:
        _drain(handler)
        return _send_json(handler, {"ok": False, "words": bad[1]}, bad[0])
    raw = handler.rfile.read(int(handler.headers.get("Content-Length").strip()))
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        body = None
    if not isinstance(body, dict):
        return _send_json(handler, {"ok": False, "words": NOT_UNDERSTOOD}, 400)
    code, out = save_from_page(body)
    _send_json(handler, out, code)


def handle_post(handler, path, query):
    """Every POST for the arranging pages. Whatever goes wrong, the server answers and stays up."""
    try:
        if path == "/arrange":
            return _post_arrange(handler)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _send_json(handler, {"ok": False, "words": CANT_REACH}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the commands (Claude's; these may stop with a message) ----------

def page_address(kit, piece):
    """The picker's address on the page server, which is started if it isn't running (as home.py does)."""
    import home
    u = home.url()
    if not u:
        return None
    base = u.rsplit("/", 1)[0]
    # A server that was running older code starts over when a page is asked for (fresh.py), and is gone for
    # a moment while it does. Wait until the home page itself answers, so the address printed here works.
    # Never through a proxy (this_computer.open_local, as home.url): a proxy can't see this computer's own
    # pages, so every try would fail. With no proxy set (every Mac and PC at home) this is exactly what it was.
    for _ in range(40):
        try:
            if b"<title>One moment</title>" not in this_computer.open_local(base + "/home", timeout=3).read(700):
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.25)
    return f"{base}/arrange.html?kit={quote(kit.name)}&piece={piece}"


def cmd_open(kit, piece):
    listed = kit_by_name(kit.name)
    if listed is None or listed.resolve() != kit.resolve():
        say(f"STOP: \"{kit.name}\" isn't in {posts.CONTENT_NAME}, so the page can't show it.")
        return 1
    if not sheet_rows(kit):
        if kit_mod.sheet(kit) != 0 or not sheet_rows(kit):
            say("STOP: couldn't number this shoot's photos. Are they where the kit says they are?")
            return 1
    got = make_previews(kit)
    if got.get("cant"):
        say(f"STOP: {got['cant']} " + ("Run this again once it is added." if got.get("cant_kind") == "addon"
                                       else "Run this again once that is done."))
        return 1
    if got["missing"] or got["failed"]:
        say(f"({got['missing'] + got['failed']} of {got['of']} photos couldn't be read right now; the page will say so.)")
        if got.get("why"):
            say(f"({got['why']})")
    if got.get("later") and got.get("full"):     # a PC only
        say(f"({got['later']} of {got['of']} photos weren't ready yet: the drive this post kit is on is full. Once "
            "there's some room on it, opening the page again makes them.)")
    elif got.get("later"):      # a PC only
        say(f"({got['later']} of {got['of']} photos weren't ready yet: something on this {this_computer.COMPUTER} kept "
            "their copies busy, most often the virus checker. The page makes them when it opens.)")
    _, p = sync(kit, piece)
    if p is None:
        say("STOP: couldn't read this shoot's numbered list. Nothing was changed.")
        return 1
    addr = page_address(kit, piece)
    if not addr:
        say("STOP: couldn't start the page server.")
        return 2
    n = len(p["now"]["nums"])
    say(f"{n} photo{'s' if n != 1 else ''} in the {piece}, {got['of']} in the shoot.")
    say(addr)
    return 0


def apply_reel(kit, dry=False):
    """Take the page's order into the kit record (a command writes kit.json; the server never does).
    Prints the picks the way reel.py wants them. Running it twice changes nothing.
    The kit's arrangement is held (locked) from the first read to the last write, so a save from the page
    lands either wholly before this (and is the order taken) or wholly after it (and is waiting again)."""
    with locked(kit_lock(kit)):
        data, p = sync(kit, "reel")
        if p is None:
            say("STOP: couldn't read this shoot's numbered list (kit.py sheet makes it). Nothing was changed.")
            return 2
        nums, marks = list(p["now"]["nums"]), list(p["now"]["marks"])
        if not nums:
            say("STOP: no photos are picked for this reel yet.")
            return 2
        text = pick_text(nums, marks)
        rec = kit_mod.load_rec(kit)
        picks = dict(rec.get("picks") or {})
        old = list(picks.get("reel") or [])
        new_marks = {str(n): m for n, m in zip(nums, marks) if m in ("+", "-")}
        if dry:
            say("Reel picks: " + text)
            return 0
        if old != nums or (rec.get("reel_marks") or {}) != new_marks:
            # The reel cover is made once and not re-made (kit.py build makes it from the cover pick, or from
            # the reel's first photo when there is none). So when the first photo changes and no cover pick is
            # written down, write down the OLD first photo: the record then stays true of the cover file.
            keep_cover = (not picks.get("cover") and (kit / "Covers" / "Reel cover.jpg").exists()
                          and old and type(old[0]) is int and old[0] != nums[0])

            def note(r):
                pk = dict(r.get("picks") or {})
                if keep_cover and not pk.get("cover"):
                    pk["cover"] = [old[0]]
                pk["reel"] = nums
                r["picks"] = pk
                r["reel_marks"] = new_marks

            kit_mod.update_rec(kit, note)
        if p.get("synced") != text:
            p["synced"] = text
            save(kit, data)
        took(kit.name, "reel")
    say("Reel picks: " + text)
    return 0


def _job_line(res, n):
    """What the page shows under the final button for a result from kit.rebuild_carousel."""
    if res["state"] == "done":
        return "done", f"Done. {n} slide{'s' if n != 1 else ''} {'are' if n != 1 else 'is'} in your Carousel folder."
    if res["state"] in ("same", "none"):
        return "same", IN_ORDER
    photos = res.get("photos") or []
    if res.get("why") in ("photo", "make") and photos:
        if res.get("detail"):   # a PC only: kit.rebuild_carousel names the real reason (pictures.why_not); never set on a Mac
            return "problem", (f"Couldn't make the slides: photo {photos[0]} can't be opened on this {this_computer.COMPUTER} yet. "
                               + LEFT_AS_WAS + " Tell Claude and it'll sort it out.")
        return "problem", f"Couldn't make the slides: photo {photos[0]} can't be read. Is the drive plugged in? " + LEFT_AS_WAS
    # The three below only ever come from a PC (kit.rebuild_carousel): no way to make pictures yet, or a slide's full
    # address longer than a PC allows. A Mac never gets them, so its words are as they were.
    if res.get("why") == "tools":
        return "problem", (f"Couldn't make the slides: this {this_computer.COMPUTER} needs one free add-on first. "
                           + LEFT_AS_WAS + " Tell Claude and it'll sort it out.")
    if res.get("why") == "long" and res.get("deep"):
        return "problem", (f"Couldn't make the slides: this post kit's folder sits too deep in other folders on this "
                           f"{this_computer.COMPUTER}. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out.")
    if res.get("why") == "long":
        return "problem", (f"Couldn't make the slides: a slide's name would be too long for this {this_computer.COMPUTER} "
                           "to open. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out.")
    if res.get("why") == "move" or res.get("left"):
        return "problem", NOT_FINISHED
    if res.get("why") == "clash":
        return "problem", IN_THE_WAY
    return "problem", "Couldn't make the slides. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out."


def _pressed(p):
    """The order the final button was last pressed on, when its numbers can still be trusted: {"rev", "nums"}
    from the record's "happy", or None. Its numbers are from the numbered list that was current at the press;
    if the photos have been numbered again since, they mean other photos now, and it is not used."""
    h = p.get("happy") if isinstance(p, dict) else None
    if not isinstance(h, dict) or type(h.get("rev")) is not int or not isinstance(h.get("nums"), list):
        return None
    if h.get("stamp") != p.get("stamp") or any(type(n) is not int for n in h["nums"]):
        return None
    return h


def _take_carousel(kit, nums):
    """With the kit's arrangement held: the order the slides were made in becomes the kit's own carousel pick,
    and the record notes that it has seen it (so it is not taken for a fresh pick of Claude's)."""
    data, p = sync(kit, "carousel")
    if list((kit_mod.load_rec(kit).get("picks") or {}).get("carousel") or []) != list(nums):
        def note(rec):
            picks = dict(rec.get("picks") or {})
            picks["carousel"] = list(nums)
            rec["picks"] = picks
        kit_mod.update_rec(kit, note)
    if p is not None and p.get("synced") != pick_text(nums):
        p["synced"] = pick_text(nums)
        save(kit, data)
    return p


@contextlib.contextmanager
def _job_hold(kit, wait):
    """Hold the job's lock for as long as the work takes. Yields True when it is held (or when this drive has
    no such locks), False when another job kept it for longer than `wait` seconds. The computer lets go of it
    by itself if the job ends any other way (a Mac at once; Windows soon after, as Microsoft's LockFileEx
    documentation says)."""
    f = None
    if fcntl is not None:
        try:
            make_folder(job_lock(kit).parent)
            f = open(job_lock(kit), "a", encoding="utf-8")     # never written to: only held
        except OSError:
            f = None
    got = True
    end = time.time() + wait
    while f is not None:
        held = this_computer.try_lock(f)
        if held:
            break
        if held is None:                    # no locks on this drive
            f.close()
            f = None
            break
        if time.time() > end:
            got = False
            break
        time.sleep(0.05)
    try:
        yield got
    finally:
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


def run_carousel_job(kit):
    """The carousel's final button, carried out: started by the page server as a process of its own. It makes
    the slides for the order the button was pressed on, and before it stops it looks, with the kit's
    arrangement held, for a button pressed on a newer order while it worked; if there is one it makes that
    too. Its state is always written down for the page, whatever goes wrong short of being killed (and a
    killed job is told from its lock having been let go)."""
    with _job_hold(kit, 3.0) as mine:
        if not mine:
            log(f"slide job for {kit.name}: another job is at work; left to it")
            return 0
        # A problem met before the order has been read must still reach the page that is waiting, and that
        # page takes only a result that carries the counter it pressed on. The server wrote that counter down
        # ("queued") just before it started this job, so that is where the counter starts from.
        was = read_job(kit) or {}
        queued = was.get("state") == "queued" and type(was.get("rev")) is int
        rev = was["rev"] if queued else -1
        n = was.get("count") if queued and type(was.get("count")) is int else 0
        loops = 0
        try:
            while True:
                loops += 1
                with locked(kit_lock(kit)):
                    data, p = sync(kit, "carousel")
                    if p is None:
                        write_job(kit, "problem", "Couldn't make the slides. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out.", rev, n)
                        return 1
                    happy = _pressed(p)
                    if happy:
                        nums, rev = list(happy["nums"]), happy["rev"]
                    else:               # no button on record (or the photos were numbered again since): the order as it is now
                        nums, rev = list(p["now"]["nums"]), int(p["now"].get("rev") or 0)
                    n = len(nums)
                    was = read_job(kit) or {}
                    if loops == 1 and was.get("state") in ("done", "same") and was.get("rev") == rev and kit_mod.carousel_in_order(kit, nums):
                        return 0                                # a job that started beside this one has already done it
                    write_job(kit, "running", MAKING, rev, n)

                def take(nums=nums):
                    with locked(kit_lock(kit)):
                        _take_carousel(kit, nums)

                # not with the arrangement held: the page goes on saving meanwhile. The order becomes the kit's
                # own pick (take) while the slides are still held, so the slides and the pick change together.
                res = kit_mod.rebuild_carousel(kit, nums, take=take)
                state, line = _job_line(res, n)
                with locked(kit_lock(kit)):
                    p = sync(kit, "carousel")[1]
                    newer = _pressed(p)
                    if newer and newer["rev"] != rev and loops < JOB_LOOPS:
                        continue                                # the button was pressed again on a newer order
                    write_job(kit, state, line, rev, n)         # written with the arrangement held: a press after this starts a new job
                    log(f"slide job for {kit.name}: {state} (counter {rev}, {n} slides; {res.get('made', 0)} made, {res.get('aside', 0)} set aside"
                        + (f"; {res.get('why')}: {res.get('detail') or res.get('files') or res.get('photos')}" if state == "problem" else "") + ")")
                    return 0 if state != "problem" else 1
        except (Exception, SystemExit) as e:  # noqa: BLE001
            log(f"slide job for {kit.name} failed: {e.__class__.__name__}: {str(e)[:200]}")
            try:
                moving = bool(kit_mod._moving(kit)) or not (kit / ".kit").is_dir()
            except (Exception, SystemExit):  # noqa: BLE001
                moving = True
            try:
                write_job(kit, "problem", NOT_FINISHED if moving else "Couldn't make the slides. " + LEFT_AS_WAS + " Tell Claude and it'll sort it out.", rev, n)
            except OSError as e2:       # the kit's own folder is not there to write in: nothing is made in its place
                log(f"slide job for {kit.name}: its state could not be written down ({e2.__class__.__name__})")
            return 1


def apply_carousel(kit, dry=False, as_it_is=False):
    """Claude's own command: the page's carousel order into the kit, and the plain slides made to match.
    Prints the order and what was done. Running it twice changes nothing. Clears the line that was waiting.

    Which order: when the final button was pressed and that press is still waiting for Claude, the order the
    button was pressed ON, even if they have moved photos on the page since (the page has told them "Press
    the button again when it's right", so what they moved afterwards is not finished and stays on the page).
    With no press waiting, or with as_it_is, the order as it is on the page now."""
    with locked(kit_lock(kit)):
        data, p = sync(kit, "carousel")
        if p is None:
            say("STOP: couldn't read this shoot's numbered list (kit.py sheet makes it). Nothing was changed.")
            return 2
        pressed = None if as_it_is else _pressed(p)
        if pressed and any(w["kit"] == kit.name and w["piece"] == "carousel" for w in waiting()):
            nums, rev = list(pressed["nums"]), pressed["rev"]
        else:
            nums, rev = list(p["now"]["nums"]), int(p["now"].get("rev") or 0)
        moved_since = nums != list(p["now"]["nums"])
    lim = LIMITS["carousel"]
    if len(nums) < lim["min"]:
        say("STOP: a carousel needs at least 2 photos, and this one has " + str(len(nums)) + ". Nothing was changed.")
        return 2
    if len(nums) > lim["max"]:
        say(f"STOP: Instagram allows up to {lim['max']} photos in a carousel, and this one has {len(nums)}. Nothing was changed.")
        return 2
    if dry:
        plan = kit_mod.carousel_plan(kit, kit_mod.load_rec(kit), nums)
        say("Carousel picks: " + pick_text(nums))
        if plan.get("ok"):
            say(f"Would make {len(plan['make'])} new slide{'s' if len(plan['make']) != 1 else ''} and set {len(plan['aside'])} earlier one{'s' if len(plan['aside']) != 1 else ''} aside. Nothing was changed.")
        return 0
    with _job_hold(kit, 120.0) as mine:
        if not mine:
            say("STOP: this shoot's slides are being made by the page right now. Nothing was changed. Try again in a moment.")
            return 2

        def take():
            with locked(kit_lock(kit)):
                _take_carousel(kit, nums)

        res = kit_mod.rebuild_carousel(kit, nums, take=take)
        state, line = _job_line(res, len(nums))
        if state == "problem":
            say("Carousel picks: " + pick_text(nums))
            say("STOP: " + kit_mod.carousel_trouble(res).strip("()"))
            return 1
        with locked(kit_lock(kit)):
            p = sync(kit, "carousel")[1]
            write_job(kit, state, line, rev, len(nums))        # an open page shows the same true line
            newer = _pressed(p)
            again = bool(newer) and newer["rev"] > rev and list(newer["nums"]) != nums
            if again:
                # the page's button was pressed on a newer order while this worked: that one is made next, by
                # the page's own job, and stays waiting for Claude
                write_job(kit, "queued", MAKING, newer["rev"], len(newer["nums"]))
            else:
                took(kit.name, "carousel")
    if again:
        start_job(kit)
    say("Carousel picks: " + pick_text(nums))
    if state == "same":
        say(f"Carousel: the {len(nums)} slides were already in this order. Nothing was changed.")
    else:
        say(f"Carousel: {len(nums)} slides are in the Carousel folder, in this order ({res.get('made', 0)} new; "
            f"{res.get('aside', 0)} earlier one{'s' if res.get('aside', 0) != 1 else ''} set aside in the kit's hidden folder, not deleted).")
    if moved_since and not again:
        say("Page: they have moved photos on the page since they pressed the button, and have not pressed it again. "
            "These slides are the order the button was pressed on; what they moved since is still on the page, not made.")
    if kit_mod.canva_behind(kit_mod.load_rec(kit)):
        # said whenever it is true, whether this run changed the slides or the page's own job already had
        say("Canva: this kit's Canva slides were made from the earlier photos and still show them.")
    return 0


def cmd_earlier(kit, piece):
    p = load(kit).get(piece) or {}
    es = p.get("earlier") or []
    if not es:
        say("Nothing has been replaced.")
        return 0
    for e in es:
        was = ("; it was: " + ", ".join(str(x) for x in e["was"])) if isinstance(e.get("was"), list) else ""
        say(f"{e.get('replaced') or e.get('at')}: {pick_text(e['nums'], e.get('marks'))}   (by {e.get('by', 'you')}; {e.get('why', '')}{was})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show").add_argument("words")
    pv = sub.add_parser("previews"); pv.add_argument("words"); pv.add_argument("--quiet-on-unreadable", action="store_true", help="the page's own background run: do not try again a photo that could not be read last time")
    o = sub.add_parser("open"); o.add_argument("words"); o.add_argument("--piece", default="reel")
    a_ = sub.add_parser("apply"); a_.add_argument("words"); a_.add_argument("--piece", default="reel"); a_.add_argument("--dry", action="store_true")
    a_.add_argument("--job", action="store_true", help="how the carousel page's own button runs it: on its own, writing its state for the page")
    a_.add_argument("--as-it-is", action="store_true", help="the carousel: make the order as it is on the page right now, even if the button was pressed on an earlier one")
    sub.add_parser("waiting")
    t = sub.add_parser("took"); t.add_argument("words"); t.add_argument("--piece")
    e = sub.add_parser("earlier"); e.add_argument("words"); e.add_argument("--piece", default="reel")
    a = ap.parse_args()
    _own_output()                          # a PC's background run only; nothing anywhere else
    import fresh
    fresh.announce()                       # this folder is where the Assistant's code is now (see fresh.py)

    if a.cmd == "waiting":
        ws = waiting()
        for w in ws:
            say(waiting_line(w))
        if not ws:
            say("Nothing is waiting.")
        return 0
    if getattr(a, "piece", None) and a.piece not in PIECES and a.cmd in ("open", "apply", "earlier"):
        say(f"STOP: only the reel and the carousel have a page so far (asked for: {a.piece}).")
        return 1
    kit = kit_mod.find_kit(a.words)
    if a.cmd == "show":
        rec = kit_mod.load_rec(kit)
        rows = sheet_rows(kit)
        say(f"{rec.get('name') or kit.name}  ({kit.name})")
        say(f"  Photos on the numbered list: {len(rows)}" + ("" if rows else "  (none yet: kit.py sheet)"))
        say(f"  Stamp: {sheet_stamp(kit) or '(no list)'}")
        return 0
    if a.cmd == "previews":
        got = make_previews(kit, retry=not a.quiet_on_unreadable)
        if got.get("cant"):
            say(got["cant"])
            return 1
        if got["made"]:
            say(f"made {got['made']}" + (f", already there {got['there']}" if got["there"] else "") + f" in {got['seconds']} s")
        else:
            say(f"already there {got['there']} in {got['seconds']} s")
        if got["missing"]:
            say(f"can't be reached right now: {got['missing']}")
        if got["failed"]:
            say(f"couldn't be read: {got['failed']}")
            if got.get("why"):
                say(f"  {got['why']}")
        if got.get("later"):    # a PC only
            say(f"not made yet: {got['later']}")
            if got.get("full"):
                say("  The drive this post kit is on is full. None of them was marked as unreadable; once there's "
                    "some room on it, running this again makes them.")
            else:
                say(f"  Something on this {this_computer.COMPUTER} kept their copies busy, most often the virus checker. "
                    "None of them was marked as unreadable; running this again makes them.")
        return 0 if not got["failed"] and not got.get("later") else 1
    try:
        if a.cmd == "open":
            return cmd_open(kit, a.piece)
        if a.cmd == "apply":
            if a.piece == "carousel":
                return run_carousel_job(kit) if a.job else apply_carousel(kit, a.dry, a.as_it_is)
            return apply_reel(kit, a.dry)
        if a.cmd == "took":
            n = took(kit.name, a.piece)
            say("Cleared." if n else "Nothing was waiting for that one.")
            return 0
    except Busy:
        say("STOP: this shoot's order is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2
    except OSError as e:
        say(f"STOP: {kit_mod._plain_os(e)}. Nothing was lost. Run this again once that is put right.")
        return 1
    if a.cmd == "earlier":
        return cmd_earlier(kit, a.piece)
    return 0


if __name__ == "__main__":
    sys.exit(main())
