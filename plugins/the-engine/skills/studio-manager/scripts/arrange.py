#!/usr/bin/env python3
"""Arranging a post kit's photos on a page: which photos are in the reel, and in what order.

The Assistant picks; the photographer can move things. The page (arrange_page.py) is served by the page
server (posting_queue.py), which hands every request for it to handle_get / handle_post here. This file
holds the records, the commands and the route handlers. It holds no page code.

    python3 arrange.py show "beach"                    the kit's name, how many photos, the list's stamp
    python3 arrange.py previews "beach"                small JPEG copies of every photo, for the page to show
    python3 arrange.py open "beach" --piece reel       get the page ready and print its address
    python3 arrange.py apply "beach" --piece reel      take the order from the page into the kit; prints the
                                                       picks the way reel.py wants them ("Reel picks: 19,4,10+,14-")
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
  <kit>/.kit/previews/NNNN-1600-<the same>.failed     an empty mark: sips could not read that photo as it is now
  <kit>/.kit/arrange.json     {"v": 1, "reel": {stamp, synced, names, first, now, happy, earlier, dropped}}
                              now = {nums, marks, rev, by, at, from}: rev is the counter, which only this file
                              moves on (by one, for every accepted change); from = {page, base} says which open
                              page saved it and which counter that page had last seen
  <kit>/.kit/arrange.lock     an empty file the writers hold while they work (never removed)
  ~/.studio/arrange-waiting.json   a pointer for Claude: which kit's order is waiting (the order is in the kit)
  ~/.studio/arrange.log       what the page's requests carried (their Origin), for reading after a problem

Python 3.9, standard library only. Image work is the Mac's own sips.
"""
import argparse
import contextlib
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

try:
    import fcntl
except ImportError:                      # not a Mac or Linux: one writer at a time inside this process only
    fcntl = None

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit as kit_mod  # noqa: E402
import posts  # noqa: E402

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
WAITING = HOME / "arrange-waiting.json"
LOG = HOME / "arrange.log"

SIZES = {"s": 520, "l": 1600}           # the long edge of each copy, never larger than the photo's own
QUALITY = {520: "82", 1600: "86"}
PIECES = ("reel",)                      # the pieces that have a page so far
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
# on this Mac) still passes; the Host check above is what stops those from outside.
ORIGIN_ENFORCED = True

CANT_FIND = "I can't find that shoot's posts. Is the drive plugged in?"
NOT_READY = "This shoot isn't ready for this yet. Say \"make posts from this shoot\" to Claude first."
CANT_REACH = "Could not reach the Assistant. Tell Claude instead."
PHOTOS_CHANGED = "The photos in this shoot changed since this page opened."
NEWER = "This order was changed somewhere else. Here's the newest."
NOT_UNDERSTOOD = "That didn't arrive the way it should have. Reload the page and try again."

_LOCK = threading.RLock()               # one writer at a time for arrange.json and the waiting list (this process)
_held = {}                              # lock file -> [its open handle, how deep]; only touched while _LOCK is held
_children = {}                          # kit path -> the previews child this server started
_logged = set()


class Busy(Exception):
    """Another process has held a record for longer than LOCK_WAIT."""


@contextlib.contextmanager
def locked(lock_file):
    """One writer at a time for a record, in this process (_LOCK) and across processes (a lock held on
    lock_file by the Mac itself, which lets go of it even if the holder dies). May be entered again by the
    thread that holds it. Where the lock can't be had at all (a drive that has no such thing, a folder that
    can't be written, no fcntl), the work goes on under _LOCK alone, as before. Raises Busy if another
    process keeps the record for more than LOCK_WAIT seconds."""
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
                lock_file.parent.mkdir(parents=True, exist_ok=True)
                f = open(lock_file, "a")
            except OSError:
                f = None
            end = time.time() + LOCK_WAIT
            while f is not None:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() > end:
                        f.close()
                        raise Busy(f"{lock_file.name} was held for more than {LOCK_WAIT:.0f} s")
                    time.sleep(0.02)
                except OSError:              # this drive has no locks: carry on without one
                    f.close()
                    f = None
        _held[key] = [f, 1]
        try:
            yield
        finally:
            _held.pop(key, None)
            if f is not None:
                try:
                    fcntl.flock(f, fcntl.LOCK_UN)
                except OSError:
                    pass
                f.close()


def kit_lock(kit):
    return kit / ".kit" / "arrange.lock"


WAITING_LOCK = HOME / "arrange-waiting.lock"


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


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
    """A file written whole or not at all: a temp name no one else is using, then a rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


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
    """An empty file that says "sips could not read this photo as it is now", so the page can say so and the
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


def _sips_copy(src, dst, edge, size):
    """One JPEG copy by sips, written under a dot-name and renamed into place only when it is whole."""
    if dst.is_file():
        return "there"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".part-{os.getpid()}-{threading.get_ident()}-{dst.name}")
    cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", QUALITY.get(size, "85"), "-Z", str(max(1, edge)), str(src), "--out", str(tmp)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        good = r.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 100 and _is_jpeg(tmp)
    except (OSError, subprocess.SubprocessError):
        good = False
    if not good:
        try:
            tmp.unlink()        # our own half-made scratch file
        except OSError:
            pass
        return None
    if dst.exists():
        try:
            tmp.unlink()        # someone made the same copy a moment ago; theirs stays
        except OSError:
            pass
        return "there"
    os.replace(tmp, dst)
    return "made"


def make_one(kit, row, size, src=None, rec=None, retry=False):
    """One copy of one photo. 1600 comes from the photo; 520 comes from the 1600 copy. The long edge is never
    larger than the photo's own (sips would blow a small photo up). Returns "made", "there" or None."""
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
    if mark.exists() and not retry:
        return None
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
    if size == SIZES["l"]:
        got = _sips_copy(src, dst, edge, size)
        if got is None:
            try:
                mark.parent.mkdir(parents=True, exist_ok=True)
                mark.touch()
            except OSError:
                pass
        return got
    big = preview_file(kit, row, SIZES["l"], src)
    if not big.is_file() and make_one(kit, row, SIZES["l"], src, retry=retry) is None:
        return None
    return _sips_copy(big, dst, edge, size)


def make_previews(kit, workers=4, retry=False):
    """Both copies of every photo on the list, four at a time. Copies already there are left alone. A photo
    sips could not read last time is skipped unless retry is set (the command sets it; the page's own
    background run does not, so an unreadable photo is not tried on every page load)."""
    t0 = time.time()
    rec = kit_mod.load_rec(kit)
    rows = sheet_rows(kit)
    out = {"made": 0, "there": 0, "missing": 0, "failed": 0, "of": len(rows)}

    def one(row):
        src = photo_path(kit, rec, row)
        if src is None:
            return "missing"
        a = make_one(kit, row, SIZES["l"], src, retry=retry)
        b = make_one(kit, row, SIZES["s"], src, retry=retry) if a else None
        if not a or not b:
            return "failed"
        return "made" if "made" in (a, b) else "there"

    if rows:
        previews_dir(kit).mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(one, rows):
                out[res] += 1
    out["seconds"] = round(time.time() - t0, 2)
    return out


def start_previews(kit):
    """From the server: make the copies in a process of their own, so no request waits on sips."""
    with _LOCK:
        old = _children.get(str(kit))
        if old is not None and old.poll() is None:
            return False
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            with open(LOG, "a") as out:        # the child keeps its own handle; ours is closed again
                _children[str(kit)] = subprocess.Popen([sys.executable, str(HERE / "arrange.py"), "previews", str(kit), "--quiet-on-unreadable"],
                                                       stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            return True
        except OSError:
            return False


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
                unreadable = not have and failed_mark(kit, row, SIZES["l"], src).name in names
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
        "limits": LIMITS[piece], "previews": {"made": made, "of": len(rows)}, "job": None,
        "reel_made": bool(rec.get("reel")), "canva": bool((rec.get("canva") or {}).get("carousel")),
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
    return f"ARRANGED: {w['kit']} | {w['piece']} | {n} photo{'s' if n != 1 else ''}"


def add_waiting(kit_name, name, piece, count):
    with locked(WAITING_LOCK):
        rest = [x for x in waiting() if not (x["kit"] == kit_name and x["piece"] == piece)]
        rest.append({"kit": kit_name, "name": name, "piece": piece, "count": count, "at": now_iso()})
        write_whole(WAITING, rest[-KEEP_WAITING:])


def took(kit_name, piece=None):
    """Claude has dealt with this one. Returns how many entries were cleared."""
    with locked(WAITING_LOCK):
        was = waiting()
        rest = [x for x in was if not (x["kit"] == kit_name and (piece is None or x["piece"] == piece))]
        if len(rest) != len(was):
            write_whole(WAITING, rest)
        return len(was) - len(rest)


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
    kit = kit_by_name(_one(q, "kit"))
    n_txt, size = _one(q, "n"), SIZES.get(_one(q, "size"))
    if kit is None or size is None or not re.fullmatch(r"[0-9]{1,6}", n_txt):
        return handler.send_error(404)
    n = int(n_txt)
    row = next((x for x in sheet_rows(kit) if x["n"] == n), None)
    if row is None:
        return handler.send_error(404)
    f = copy_to_serve(kit, kit_mod.load_rec(kit), row, size)
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
    if st["previews"]["made"] < st["previews"]["of"] and any(not x["have"] and not x["missing"] for x in st["photos"]):
        start_previews(kit)
    _send_page(handler, arrange_page.page_html(kit.name, piece))


def our_host(handler):
    """Was this request sent to this server by its own name (127.0.0.1 or localhost, and this port)? A web
    page on another site that has been pointed at this Mac by a trick of names still carries its own name
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
        if not isinstance(nums, list) or len(nums) > lim["max"]:
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
        stored = p["now"]
        stored_rev = int(stored.get("rev") or 0)
        same = stored["nums"] == nums and stored["marks"] == marks
        src = stored.get("from") if isinstance(stored.get("from"), dict) else {}
        own = src.get("page") == page and src.get("base") == base
        if not same and base != stored_rev and not own:
            return _bad(NEWER, 409, why="newer", state=state_for_page(kit, piece))
        rec_name = kit_mod.load_rec(kit).get("name") or kit.name
        if same:
            # what is stored already (the same save arriving twice because its answer was lost): nothing to write
            if done:
                if (p.get("happy") or {}).get("rev") != stored_rev:
                    p["happy"] = {"rev": stored_rev, "at": now_iso()}
                    save(kit, data)
                add_waiting(kit.name, rec_name, piece, len(nums))
            return 200, {"ok": True, "words": "Saved", "rev": stored_rev, "job": False}
        rev = stored_rev + 1
        new = {"nums": nums, "marks": marks}
        is_first = _same(new, p["first"])
        if stored.get("by") == "you" and is_first:
            _keep_earlier(p, stored, "back to the first pick")
        p["now"] = _order(nums, marks, rev=rev, by="assistant" if is_first else "you", **{"from": {"page": page, "base": base}})
        if done:
            p["happy"] = {"rev": rev, "at": now_iso()}
        p["dropped"], p["dropped_nums"] = [], []
        p["names"] = _names_for(p, {n: photo_name(x) for n, x in on_sheet.items()})
        save(kit, data)
        if done:
            add_waiting(kit.name, rec_name, piece, len(nums))
        return 200, {"ok": True, "words": "Saved", "rev": rev, "job": False}


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
    import urllib.request
    u = home.url()
    if not u:
        return None
    base = u.rsplit("/", 1)[0]
    # A server that was running older code starts over when a page is asked for (fresh.py), and is gone for
    # a moment while it does. Wait until the home page itself answers, so the address printed here works.
    for _ in range(40):
        try:
            if b"<title>One moment</title>" not in urllib.request.urlopen(base + "/home", timeout=3).read(700):
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
    if got["missing"] or got["failed"]:
        say(f"({got['missing'] + got['failed']} of {got['of']} photos couldn't be read right now; the page will say so.)")
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
            if (not picks.get("cover") and (kit / "Covers" / "Reel cover.jpg").exists()
                    and old and type(old[0]) is int and old[0] != nums[0]):
                picks["cover"] = [old[0]]
            picks["reel"] = nums
            rec["picks"] = picks
            rec["reel_marks"] = new_marks
            kit_mod.save_rec(kit, rec)
        if p.get("synced") != text:
            p["synced"] = text
            save(kit, data)
        took(kit.name, "reel")
    say("Reel picks: " + text)
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
    sub.add_parser("waiting")
    t = sub.add_parser("took"); t.add_argument("words"); t.add_argument("--piece")
    e = sub.add_parser("earlier"); e.add_argument("words"); e.add_argument("--piece", default="reel")
    a = ap.parse_args()
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
        say(f"STOP: only the reel has a page so far (asked for: {a.piece}).")
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
        if got["made"]:
            say(f"made {got['made']}" + (f", already there {got['there']}" if got["there"] else "") + f" in {got['seconds']} s")
        else:
            say(f"already there {got['there']} in {got['seconds']} s")
        if got["missing"]:
            say(f"can't be reached right now: {got['missing']}")
        if got["failed"]:
            say(f"couldn't be read: {got['failed']}")
        return 0 if not got["failed"] else 1
    try:
        if a.cmd == "open":
            return cmd_open(kit, a.piece)
        if a.cmd == "apply":
            return apply_reel(kit, a.dry)
        if a.cmd == "took":
            n = took(kit.name, a.piece)
            say("Cleared." if n else "Nothing was waiting for that one.")
            return 0
    except Busy:
        say("STOP: this shoot's order is being written by something else right now. Nothing was changed. Try again in a moment.")
        return 2
    if a.cmd == "earlier":
        return cmd_earlier(kit, a.piece)
    return 0


if __name__ == "__main__":
    sys.exit(main())
