#!/usr/bin/env python3
"""The posting queue: every social piece the Studio helped make (a reel, a carousel),
with a light on it, a place in line, and a posting date.

  red     not started: the shoot is edited, the piece hasn't been made yet
  yellow  in progress: the Studio did its part (the CapCut project, the carousel exists);
          they are still styling, finishing, exporting
  green   ready to post: they said so. Only green pieces get a date and count in the tank
  posted  done

The interval is how often they want to post (asked once). The schedule gives each green
piece a date, in line order, at that interval. The fuel tank is how many weeks of posts
the green pieces cover. Nothing here posts anything, ever (rule 5): dates only.

    python3 posting_queue.py interval "3 a week"      (also: daily, every other day, twice a week, weekly, 2)
    python3 posting_queue.py add --shoot "beach" [--kinds reel,carousel]    red pieces for an edited shoot
    python3 posting_queue.py made "beach reel" [--where "<CapCut project name or file>"]   -> yellow
    python3 posting_queue.py ready "beach reel"          -> green, next in line, gets a date
    python3 posting_queue.py unready "beach reel"        back to yellow
    python3 posting_queue.py posted "beach reel"         it went out
    python3 posting_queue.py skip "beach carousel"       they don't want this one (red -> gone from the list)
    python3 posting_queue.py move "beach reel" --to 1    change its place in line (dates follow)
    python3 posting_queue.py list
    python3 posting_queue.py tank                        weeks of posts ready
    python3 posting_queue.py reminders [--mark]          today's post, running low, pieces sitting in yellow
    python3 posting_queue.py page | serve
    (posting-day reminders, Nicole's v21: reminders.py knows the calendar; this file only decides WHEN. In the
     page server the calendar is brought into step in the background after every save and when the page opens;
     a command that changed the queue asks the running server to do it, or starts "remind-sync", a helper that
     finishes by itself. python3 reminders.py status | sync | calendars | open for the chat.)

    python3 posting_queue.py feed                        what the Studio knows of their real Instagram grid
    python3 posting_queue.py feed --handle horizonfound  remember their handle (asked once)
    python3 posting_queue.py grab-script                 the snippet that reads their profile page in the browser:
                                                         it returns the last 15 posts as a small list (post, picture address)
    python3 posting_queue.py feed --import tiles.json    that list saved to a file: the Studio fetches each picture
                                                         full size from Instagram's picture server and keeps it
    python3 posting_queue.py feed --clear

The real grid: Instagram gives no simple way to read a profile's posts, so the Studio reads what is on
screen in the photographer's own browser (the Claude app's browser pane, open on their profile, signed in
or not). The grab script collects the last 15 tiles as a small list: which post, and the address of its
full-size picture. Claude saves what it returns to a file and `feed --import` fetches the pictures on this
computer. (The first version drew the tiles small in the page and posted them to the Studio's server; that can
never work: instagram.com's page rules refuse any connection to 127.0.0.1, and the app's browser pane
refuses local connections from an outside page too, websockets included. The POST /feed route stays
for a browser outside the app with those rules relaxed, nothing more.) Nothing is posted. Kept in
~/.studio/feed.json + ~/.studio/feed/ (the picture addresses are used once and not kept).

Kept in ~/.studio/posting.json with a thumbnail per piece in ~/.studio/posting-thumbs/.
A piece is named "<shoot> reel" or "<shoot> carousel"; a word or two from that is enough to find it.

A post's panel on the page (Nicole's v20 and v21): a click on an upcoming post in the grid opens it right under
that post's row: the photo the post shows in the grid (a strip to pick from), Copy caption, Copy my hook, Open my
words. All of it on this one server:
    GET  /posting/panel?id=<piece>                    the photos to pick from and the post's words (panel_for)
    POST /posting {action: "cover", id, rel}          the pick: rel is "Photos/<file>" or "Carousel/<file>" of that
                                                      piece's own kit (cover_file); the piece keeps "cover" and a
                                                      new thumbnail (the earlier one is left where it is)
A kit's pieces are told apart by the folder they were made from, never by its name made short (kit_sid, same_kit).
"""
import argparse
import base64
import errno
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import fresh  # noqa: E402  (read at startup: which code this process loaded; see fresh.py)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()
REEL_SCRIPTS = HERE.parent.parent / "assistant-make-a-reel" / "scripts"   # capcut.py, for "Open in CapCut"

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
PFILE = HOME / "posting.json"
THUMBS = HOME / "posting-thumbs"
PAGE = HOME / "posting.html"
FEED = HOME / "feed.json"
FEED_THUMBS = HOME / "feed"
FEED_MAX = 15            # tiles read from their profile: five rows of three
FEED_ORIGINS = ("https://www.instagram.com", "https://instagram.com")
FEED_PICTURE_HOSTS = (".cdninstagram.com", ".fbcdn.net")   # where Instagram keeps the pictures themselves
FEED_TILE_MAX = 2_500_000  # a full-size grid picture is 100 to 400 KB; anything bigger is not one
KINDS = ("reel", "carousel", "single")
KIT_OWN_FILES = ("Post kit.html", "Reel.txt")   # what /content serves from a kit (not an older kit's captions file:
                                            # no page shows it since Nov 10, and it may hold hashtags), and
KIT_PIECE_FOLDERS = ("Singles", "Carousel", "Stories", "Covers")          # the folders it serves pictures from
LOW_WEEKS = 1.0          # the running-low tap
STALE_DAYS = 7           # a yellow piece sitting this long gets a nudge
# The small pictures the pages show, and how deep each folder's go: a piece's ("posting-thumbs/<piece>.jpg"), a feed
# tile's ("feed/<post>.jpg"), a queued shoot's ("queue-thumbs/<shoot>/0.jpg") and a kit's on the home page
# ("home-thumbs/<kit>-1.jpg"). Nothing else in the Studio folder is served from these addresses.
THUMB_FOLDERS = {"posting-thumbs": 1, "feed": 1, "queue-thumbs": 2, "home-thumbs": 1}
PICTURE_SUFFIXES = (".jpg", ".jpeg", ".png")
_POSTING_LOCK = threading.Lock()   # the page server answers two presses at once: one reads, changes and saves the queue at a time
_CAPCUT_LOCK = threading.Lock()    # one "Open in CapCut" at a time, so what capcut.py notes about a press is that press's own
_CLICK_LOCK = threading.Lock()     # one home-page click recorded at a time (each reads, adds to and saves home.py's record)


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


# ---------- the file ----------

def load():
    if PFILE.exists():
        try:
            p = json.loads(PFILE.read_text(encoding="utf-8"))
            p.setdefault("pieces", [])
            p.setdefault("interval", None)
            p.setdefault("reminded", {})
            return p
        except ValueError:
            sys.exit(f"STOP: {PFILE} could not be read. Nothing changed.")
    return {"pieces": [], "interval": None, "reminded": {}}


def write_whole(path, text):
    """Write a file whole: under a scratch name of this program's and this thread's own beside it, then put in
    place in one step. Two writers (a command and the page server, or two presses the server answers at once)
    never share a half-written file; the name had only the program's number before, so two presses at once could
    take each other's file away mid-save and one went unanswered (seen on a Mac too, Nov 6). On a PC
    this_computer.replace waits a moment if the page server is reading the file right then. The bytes written
    are the same as ever. If the save fails, the scratch copy is taken away and the error is passed on."""
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()                     # only the scratch copy just written here, never the file itself
        except OSError:
            pass
        raise


def save(p):
    write_whole(PFILE, json.dumps(p, indent=1, ensure_ascii=False))
    # In the page server, any saved change may have moved a post's day or taken it out of line, so the
    # posting-day reminders are brought into step afterwards, in the background (remind_soon: never inside
    # this save, never while the queue's lock is wanted for the calendar). A command does it its own way
    # (calendar_in_step). The round's own save, of the few fields the calendar handed back, starts nothing.
    if _SERVING and not getattr(_IN_ROUND, "on", False):
        remind_soon()


def today():
    o = os.environ.get("STUDIO_TODAY")
    return date.fromisoformat(o) if o else date.today()


def now():
    return datetime.now().isoformat(timespec="seconds")


# ---------- the interval ----------

def parse_interval(text):
    """Posts per week from plain words. Returns a float, or None if it can't tell."""
    t = str(text).strip().lower()
    words = {"daily": 7, "every day": 7, "everyday": 7, "every other day": 3.5, "every second day": 3.5,
             "twice a week": 2, "two a week": 2, "2 a week": 2, "three a week": 3, "3 a week": 3,
             "once a week": 1, "weekly": 1, "one a week": 1, "four a week": 4, "4 a week": 4,
             "five a week": 5, "5 a week": 5, "every weekday": 5, "weekdays": 5,
             "every other week": 0.5, "twice a month": 0.5, "once a month": 0.25, "monthly": 0.25}
    for k, v in words.items():
        if k in t:
            return float(v)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|times|posts?)?\s*(?:a|per|/)\s*week", t)
    if m:
        return float(m.group(1))
    m = re.search(r"every\s+(\d+)\s*days?", t)
    if m and int(m.group(1)) > 0:
        return 7.0 / int(m.group(1))
    try:
        v = float(t)
        return v if 0 < v <= 7 else None
    except ValueError:
        return None


def interval_words(per_week):
    if not per_week:
        return "no posting rhythm set"
    if per_week >= 7:
        return "every day"
    if per_week == 5:
        return "every weekday"
    if per_week == 3.5:
        return "every other day"
    if per_week == 1:
        return "once a week"
    if per_week == 0.5:
        return "every other week"
    if per_week < 1:
        return f"about {per_week * 4:.0f} a month"
    return f"{per_week:g} a week"


# ---------- pieces ----------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def piece_name(p):
    return f"{p['shoot_name']} {p['kind']}" + (f" {p['n']}" if p.get("n") else "")


def thumb_file(pid, suffix=".jpg"):
    """Where a piece's thumbnail is kept. A post kit's pieces have ids like "kit:<kit>-reel". A Mac keeps the
    file name it always had. On a PC the colon becomes "_" in the file name only (the id in the records stays
    as it is): Windows does not allow a colon in a file name, and on NTFS "kit:<...>.jpg" would mean a hidden
    stream inside a file called "kit" (Microsoft, "Naming Files, Paths, and Namespaces" and "File Streams
    (Local File Systems)"). No id has "_" in it otherwise (ids are letters, digits and dashes), so two pieces
    never share a file. Unproven on a real PC."""
    name = pid.replace(":", "_") if this_computer.WINDOWS else pid
    return THUMBS / f"{name}{suffix}"


# ---------- a post kit's pieces: which are whose ----------
# A kit's pieces are named "kit:<the folder's name made short>-reel" (and -carousel, -single-N). Made short means
# lower case, punctuation as dashes, 40 characters, so two shoots can come out alike ("Fake beach" and
# "Fake-beach", or two long names alike at the start). Every piece keeps the folder it was made from ("kit"), and
# that folder's NAME is what says whose a piece is: every lookup by kit goes through same_kit / kit_piece, never
# through the short name. A second shoot whose short name is taken gets a few letters of its own after it
# (kit_sid); a piece already in someone's queue is never renamed, so every older posting.json reads as it did.

def _nfc(s):
    return unicodedata.normalize("NFC", s)


def kit_folder(x):
    """The NAME of the kit folder a piece was made from ("" for a piece that kept none). Never the path."""
    was = x.get("kit") if isinstance(x, dict) else None
    if not isinstance(was, str) or not was:
        return ""
    return re.split(r"[\\/]", was.rstrip("\\/"))[-1]


def same_kit(x, kit_dir):
    """Is this piece this kit's own? By the folder it was made from. A piece from before the folder was written
    down counts as the kit's whose short name it carries (there was no way to have two then)."""
    if not isinstance(x, dict):
        return False
    name = kit_folder(x)
    if name:
        return _nfc(name) == _nfc(Path(kit_dir).name)
    return x.get("shoot_id") == "kit:" + slug(Path(kit_dir).name)


def kit_role(x):
    """What a kit's piece is in its kit, from its name: "reel", "carousel" (also when it is shown as a single
    post: a carousel saved as one slide), "single" (a photo from the Singles folder), or "" for anything else."""
    pid = str(x.get("id") or "") if isinstance(x, dict) else ""
    if not (pid.startswith("kit:") or kit_folder(x)):
        return ""
    if pid.endswith("-reel"):
        return "reel"
    if pid.endswith("-carousel"):
        return "carousel"
    if re.search(r"-single-\d+$", pid):
        return "single"
    return ""


def kit_piece(p, kit_dir, role, n=None):
    """This kit's reel or carousel (or its single post number n) in the queue, or None. role is kit_role's."""
    for x in p.get("pieces", []):
        if isinstance(x, dict) and kit_role(x) == role and same_kit(x, kit_dir) and (n is None or x.get("n") == n):
            return x
    return None


def kit_sid(p, kit_dir):
    """The name this kit's pieces go under ("kit:<short name>"), one no other kit's pieces have. The one its
    pieces already carry, when it has any (never changed). Else the short name; and when another shoot's pieces
    already have that one, the short name with a few letters made from this folder's whole name after it."""
    name = Path(kit_dir).name
    pieces = [x for x in p.get("pieces", []) if isinstance(x, dict)]
    for x in pieces:
        if kit_folder(x) and same_kit(x, kit_dir) and str(x.get("shoot_id") or "").startswith("kit:"):
            return x["shoot_id"]
    others = [x for x in pieces if kit_folder(x) and not same_kit(x, kit_dir)]

    def taken(sid):
        own = re.compile(re.escape(sid) + r"-(reel|carousel|single-\d+)$")
        return any(x.get("shoot_id") == sid or own.match(str(x.get("id") or "")) for x in others)
    base = "kit:" + slug(name)
    if not taken(base):
        return base
    mark = hashlib.sha1(_nfc(name).encode("utf-8")).hexdigest()
    for k in (8, 12, 16, 40):
        sid = "kit:" + (slug(name)[:30].strip("-") + "-" + mark[:k]).strip("-")
        if not taken(sid):
            return sid
    return sid


def cover_file(kit_dir, role, rel, rec=None):
    """The photo a grid pick names, or None. rel is "Photos/<a file name>" for a reel (one of the kit's numbered
    photos, by its exact name on the list) or "Carousel/<a file name>" for a carousel (one of the slides the kit
    page shows as the carousel). One folder word and one plain file name, nothing else: never a path, never
    "..", never a name starting with a dot, never a link out of the folder."""
    import arrange
    import kit as kit_mod
    if not isinstance(rel, str) or not 3 <= len(rel) <= 400:
        return None
    head, sep, name = rel.partition("/")
    if not sep or not name or "/" in name or "\\" in name or "\x00" in name or name.startswith(".") or name in (".", ".."):
        return None
    try:
        if role == "reel" and head == "Photos":
            row = next((r for r in arrange.sheet_rows(kit_dir) if _nfc(arrange.photo_name(r)) == _nfc(name)), None)
            f = arrange.photo_path(kit_dir, rec if rec is not None else kit_mod.load_rec(kit_dir), row) if row else None
        elif role == "carousel" and head == "Carousel":
            f = next((x for x in kit_mod.carousel_shown(kit_dir, rec)["files"] if _nfc(x.name) == _nfc(name)), None)
        else:
            return None
        if f is None or f.is_symlink() or not f.is_file():
            return None
        return f
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def reel_first_photo(kit_dir, rec, photos):
    """The photo a reel's tile shows until they pick one: the reel's own first photo, in the order Make my reel
    would use (the reel page's record: reel_page.order_for_kit_page; Claude's pick when the page was never
    used). Nicole, Nov 10: "a reel's first tile should be the reel's first photo, not the kit's first photo".
    Failing that, the first pick the kit record holds, then the kit's first photo, as before."""
    import arrange
    try:
        import reel_page
        rows = arrange.sheet_rows(kit_dir)
        by_n = {r["n"]: r for r in rows}
        for x in reel_page.order_for_kit_page(kit_dir, rows, rec):
            f = arrange.photo_path(kit_dir, rec, by_n[x["n"]]) if x.get("n") in by_n else None
            if f is not None:
                return f
    except (Exception, SystemExit):  # noqa: BLE001  (a tile only: the old way below still gives one)
        pass
    try:
        pick = (rec.get("picks", {}).get("reel") or [None])[0]
        sheet_p = Path(kit_dir) / ".kit" / "sheet.json"
        if pick is not None and sheet_p.exists():
            by = {x["n"]: x["file"] for x in json.loads(sheet_p.read_text(encoding="utf-8"))["photos"]}
            if by.get(pick):
                return by[pick]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return photos[0] if photos else None


def find(p, text, statuses=None):
    """One piece from a few words ("beach reel", "beach", "garcia carousel"). A shoot word alone with two
    pieces returns the one that fits best in context, else asks for the kind."""
    t = str(text).strip().lower()
    cands = [x for x in p["pieces"] if (statuses is None or x["status"] in statuses) and x["status"] != "skipped"]
    exact = [x for x in cands if piece_name(x).lower() == t or x["id"] == t]
    if exact:
        return exact[0]
    words = [w for w in re.split(r"[^a-z0-9]+", t) if w]
    kind = next((k for k in KINDS if k in words), None)
    rest = [w for w in words if w not in KINDS]
    hits = []
    for x in cands:
        name = x["shoot_name"].lower()
        if (not rest or all(w in name for w in rest)) and (not kind or x["kind"] == kind):
            hits.append(x)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"STOP: nothing in the posting queue matches \"{text}\".")
    names = ", ".join(piece_name(x) for x in hits)
    sys.exit(f"STOP: \"{text}\" could mean more than one: {names}. Say which.")


def queue_shoot(text):
    """The editing queue's record for a shoot, by a few words of its name (or its id)."""
    import edit_queue
    q = edit_queue.load()
    t = str(text).strip().lower()
    byid = next((s for s in q["shoots"] if s["id"] == t), None)
    if byid:
        return byid
    return edit_queue.find(q, text, include_finished=True)


def add_for_shoot(p, shoot, kinds):
    """Red pieces for an edited shoot, one per kind, each with a different one of the queue's three previews
    (the reel the first, the carousel the second), so a shoot's pieces never show the same photo twice in the grid."""
    made = []
    have = [HOME / t for t in (shoot.get("thumbs") or []) if (HOME / t).exists()]
    for n, kind in enumerate(kinds):
        if any(x["shoot_id"] == shoot["id"] and x["kind"] == kind for x in p["pieces"]):
            continue
        pid = f"{shoot['id']}-{kind}"
        thumb = None
        if have:
            src = have[n % len(have)]
            THUMBS.mkdir(parents=True, exist_ok=True)
            dst = thumb_file(pid, src.suffix.lower())
            shutil.copyfile(src, dst)
            thumb = dst.relative_to(HOME).as_posix()
        p["pieces"].append({"id": pid, "shoot_id": shoot["id"], "shoot_name": shoot["name"], "shot": shoot.get("shot"),
                            "kind": kind, "status": "red", "thumb": thumb, "added": now()})
        made.append(pid)
    return made


def carousel_kind(shown):
    """The kind of a kit's carousel piece (decision 12, Nicole, Nov 6: "One slide on its own is a single post"):
    "single" when the slides the kit shows as its carousel are a set laid out in the designer that is one slide,
    "carousel" otherwise. The piece keeps its place (its id) in the queue either way. shown is kit.carousel_shown's."""
    return "single" if shown.get("kind") == "laid-out" and len(shown.get("files") or []) == 1 else "carousel"


def add_for_kit(p, kit_dir):
    """The pieces of a post kit (kit.py): the reel and the carousel (in progress once made, waiting if not),
    and one piece per single post, each with its own thumbnail. Stories don't go on the grid, so they stay
    on the kit page only. Adding the same kit again updates what's there. The pieces are this kit's own by the
    folder they were made from (kit_sid, same_kit): another shoot whose name shortens alike is never touched.
    A tile the photographer picked in the posting queue (the piece's "cover") is left as they picked it."""
    import kit as kit_mod
    kit_dir = Path(kit_dir)
    rec = kit_mod.load_rec(kit_dir)
    name = rec.get("name") or kit_dir.name
    sid = kit_sid(p, kit_dir)
    THUMBS.mkdir(parents=True, exist_ok=True)
    photos = kit_mod.photo_files(kit_mod.photos_dir(kit_dir, rec))

    def thumb_of(src, pid):
        if not src or not Path(src).exists():
            return None
        dst = thumb_file(pid)
        if not kit_mod.fit(Path(src), dst, (360, 450)):
            return None
        return dst.relative_to(HOME).as_posix()

    def upsert(pid, kind, status, thumb_src, where=None, n=None):
        x = next((y for y in p["pieces"] if y["id"] == pid and same_kit(y, kit_dir)), None)
        if x is None:
            x = {"id": pid, "shoot_id": sid, "shoot_name": name, "shot": rec.get("date"), "kind": kind, "status": "red", "added": now(), "kit": str(kit_dir)}
            if n is not None:
                x["n"] = n
            p["pieces"].append(x)
        x["kit"] = str(kit_dir)     # where the kit is now (a piece from before this was kept gets it here)
        x["kind"] = kind            # a carousel saved as one slide is a single post, and back (carousel_kind)
        picked = x.get("cover") and x.get("thumb") and cover_file(kit_dir, kit_role(x), x["cover"], rec) is not None
        if not picked:
            x.pop("cover", None)    # the photo they picked is gone (the slides were made again): the usual tile
            x["thumb"] = thumb_of(thumb_src, pid) or x.get("thumb")
        if x["status"] in ("red", "yellow") and status != x["status"]:
            set_status(p, x, status, by="kit", where=where)
        return x

    out = []
    reel = rec.get("reel")
    out.append(upsert(f"{sid}-reel", "reel", "yellow" if reel else "red", reel_first_photo(kit_dir, rec, photos),
                      where=reel["project"] if reel else None))
    shown = kit_mod.carousel_shown(kit_dir, rec)     # the slides the kit page shows as the carousel (kit.py's one rule)
    slides = shown["files"]
    out.append(upsert(f"{sid}-carousel", carousel_kind(shown), "yellow" if slides else "red", slides[0] if slides else (photos[1] if len(photos) > 1 else None),
                      where="the Carousel folder" if slides else None))
    singles = sorted(f for f in (kit_dir / "Singles").glob("*.jpg") if not f.name.startswith(".")) if (kit_dir / "Singles").is_dir() else []
    for i, f in enumerate(singles, 1):
        out.append(upsert(f"{sid}-single-{i}", "single", "yellow", f, where="the Singles folder", n=i))
    return out


def refresh_kit_carousel(kit_dir):
    """A kit's carousel slides were re-made: its piece here gets the new first slide as its picture, and
    nothing else in the queue is looked at. The picture is made FIRST (that is the slow part); only then is
    the queue read, that one piece changed, and the queue saved, in one quick step, so a change made to the
    queue meanwhile (a piece marked ready to post, say) is never put back to how it was. A slide they picked
    for the grid in the posting queue stays their tile while that slide is still one of the carousel's; when it
    is gone, the tile is the first slide again.
    False when this kit's carousel is not in the queue."""
    import kit as kit_mod
    kit_dir = Path(kit_dir)
    was = kit_piece(load(), kit_dir, "carousel")
    if was is None:
        return False
    pid = was["id"]
    shown = kit_mod.carousel_shown(kit_dir)          # the slides the kit page shows as the carousel (kit.py's one rule)
    slides = shown["files"]
    cover = was.get("cover")
    keep = bool(cover) and cover_file(kit_dir, "carousel", cover) is not None
    thumb = None
    if slides and not keep:
        THUMBS.mkdir(parents=True, exist_ok=True)
        dst = thumb_file(pid)
        if kit_mod.fit(slides[0], dst, (360, 450)):
            thumb = dst.relative_to(HOME).as_posix()
    p = load()                                        # read afresh, change one piece, save: nothing in between
    x = next((y for y in p["pieces"] if y.get("id") == pid and same_kit(y, kit_dir)), None)
    if x is None:
        return False
    if not (keep and x.get("cover") == cover):
        if x.get("cover") == cover:
            x.pop("cover", None)                      # the slide they picked is gone
        if x.get("cover") is None:
            x["thumb"] = thumb or x.get("thumb")
    x["kind"] = carousel_kind(shown)                  # one laid-out slide is a single post (decision 12)
    status = "yellow" if slides else "red"
    if x["status"] in ("red", "yellow") and status != x["status"]:
        set_status(p, x, status, by="kit", where="the Carousel folder" if slides else None)
    save(p)
    write_page(p)
    return True


def greens(p):
    return sorted((x for x in p["pieces"] if x["status"] == "green"), key=lambda x: x.get("slot", 10 ** 6))


def renumber(p):
    for i, x in enumerate(greens(p), 1):
        x["slot"] = i


def schedule(p, reflow=False):
    """A date for every green piece, in line order, at the interval. Dates already given stay put day to day
    (a missed one is reported, not quietly moved); only pieces without a date get one, after the last dated
    piece. reflow=True (the order or the rhythm changed) gives everyone a fresh date from the front."""
    per_week = p.get("interval")
    g = greens(p)
    if not per_week or not g:
        for x in g:
            x.pop("date", None)
        return
    gap = 7.0 / per_week
    last_posted = max((x.get("posted_at", "")[:10] for x in p["pieces"] if x["status"] == "posted"), default=None)
    start = today() + timedelta(days=1)
    if last_posted:
        start = max(start, date.fromisoformat(last_posted) + timedelta(days=max(1, round(gap))))
    if reflow:
        for x in g:
            x.pop("date", None)
    anchor, k = start, 0
    dated = [x for x in g if x.get("date")]
    if dated:
        anchor = max(date.fromisoformat(x["date"]) for x in dated)
        k = 1
    for x in g:
        if x.get("date"):
            continue
        x["date"] = (anchor + timedelta(days=round(k * gap))).isoformat()
        k += 1


def tank(p):
    """(weeks of posts ready, number of green pieces). Weeks is None when no interval is set."""
    n = len(greens(p))
    per_week = p.get("interval")
    if not per_week:
        return None, n
    return n / per_week, n


def tank_words(p):
    weeks, n = tank(p)
    if n == 0:
        return "Nothing ready to post yet."
    if weeks is None:
        return f"{n} piece{'s' if n != 1 else ''} ready to post. Tell me how often you like to post and I'll turn that into weeks."
    if weeks < 1:
        days = round(weeks * 7)
        return f"{n} piece{'s' if n != 1 else ''} ready: about {days} day{'s' if days != 1 else ''} of posts at {interval_words(per_week := p['interval'])}."
    w = round(weeks, 1)
    w = int(w) if w == int(w) else w
    return f"{n} piece{'s' if n != 1 else ''} ready: about {w} week{'s' if w != 1 else ''} of posts at {interval_words(p['interval'])}."


def nice_day(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%a %b ") + str(d.day)


def reminders(p, mark=False):
    """Lines worth a tap today: a post due today (or missed), running low, pieces sitting in yellow."""
    lines = []
    t = today().isoformat()
    rem = p.setdefault("reminded", {})
    for x in greens(p):
        d = x.get("date")
        if not d:
            continue
        key = f"due:{x['id']}:{d}"
        if d == t and rem.get(key) != t:
            lines.append(f"Today's post: the {piece_name(x)}.")
            if mark:
                rem[key] = t
        elif d < t and rem.get(f"late:{x['id']}") != t:
            lines.append(f"The {piece_name(x)} was down for {nice_day(d)} and hasn't gone out. Post it, or drag it later on the page.")
            if mark:
                rem[f"late:{x['id']}"] = t
    weeks, n = tank(p)
    # Running low is a nudge for someone who has posts going. Someone who has never made a piece is not
    # "running low"; telling them so is a list of what's empty (seen on Dustin's Home after a first backup, Nov 5).
    if weeks is not None and weeks <= LOW_WEEKS and rem.get("low") != t and p.get("pieces"):
        if n == 0:
            lines.append("Nothing ready to post. Time to get something in the pipeline.")
        else:
            lines.append(f"You've got about a week of posts left ({n} ready). Time to get something in the pipeline.")
        if mark:
            rem["low"] = t
    for x in p["pieces"]:
        if x["status"] == "yellow" and x.get("made_at"):
            days = (today() - date.fromisoformat(x["made_at"][:10])).days
            if days >= STALE_DAYS and rem.get(f"stale:{x['id']}") != t:
                where = " in CapCut" if x["kind"] == "reel" else ""
                lines.append(f"The {piece_name(x)} has been sitting{where} for {days} days. Finish it up and tell me it's ready.")
                if mark:
                    rem[f"stale:{x['id']}"] = t
    return lines


# ---------- their real grid ----------

def load_feed():
    if FEED.exists():
        try:
            f = json.loads(FEED.read_text(encoding="utf-8"))
            f.setdefault("posts", [])
            return f
        except ValueError:
            pass
    return {"handle": None, "read_at": None, "posts": []}


def save_feed(f):
    write_whole(FEED, json.dumps(f, indent=1, ensure_ascii=False))


def post_id(href):
    """'/horizonfound/reel/DVv_ydTDP6x/' -> 'DVv_ydTDP6x'."""
    m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", str(href))
    return m.group(1) if m else re.sub(r"[^A-Za-z0-9_-]", "", str(href))[-24:]


def curl_program():
    """The computer's own curl. A Mac finds it on its PATH, as always. A PC (Windows 10 from 2018 on, and 11)
    keeps it in System32 (Microsoft, "Tar and Curl Come to Windows!"); it is named there in full, because
    Windows looks in the current folder before System32 for a bare name, and so that PowerShell's own "curl"
    (a different thing, and only inside PowerShell) never comes into it. Unproven on a real PC."""
    if this_computer.WINDOWS:
        system32 = Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "curl.exe"
        return str(system32) if system32.is_file() else "curl.exe"
    return "curl"


def fetch_tile(src):
    """One grid picture, full size, from Instagram's own picture server. Only that server, only https, only a
    jpeg. Fetched with the computer's own curl (every Mac and every Windows 10+ PC has it): Python's own fetch
    cannot check Instagram's certificate on a Mac whose Python came without root certificates. (curl on a PC
    checks it against Windows' own certificates.)"""
    u = urlsplit(str(src))
    if u.scheme != "https" or not u.hostname or not u.hostname.endswith(FEED_PICTURE_HOSTS):
        raise ValueError("not an Instagram picture address")
    # On a PC no window of its own (CREATE_NO_WINDOW, Microsoft's "Process Creation Flags"), even when the page
    # server that asks has none. Unproven on a real PC. A Mac: exactly as before.
    quiet = {"creationflags": 0x08000000} if this_computer.WINDOWS else {}
    # this_computer.run_curl: on a Mac exactly subprocess.run, the same command. On a PC, when Windows' curl.exe
    # stops only because the network won't let it ask whether Instagram's certificate was withdrawn (exit 35,
    # CRYPT_E_NO_REVOCATION_CHECK), it is asked once more with that one question skipped. Unproven on a real PC.
    r = this_computer.run_curl([curl_program(), "-sS", "--fail", "--max-time", "25", "--max-filesize", str(FEED_TILE_MAX),
                                "-A", "The Assistant by Horizon Found", "-o", "-", src], capture_output=True, **quiet)
    if r.returncode != 0:
        raise ValueError(f"curl {r.returncode}: {r.stderr.decode('utf-8', errors='replace')[:120]}")
    raw = r.stdout
    if not raw.startswith(b"\xff\xd8") or len(raw) > FEED_TILE_MAX:
        raise ValueError("not a jpeg")
    return raw


def tile_bytes(t, why=None):
    """The picture for one tile: fetched full size from its address when there is one, else the small jpeg the
    first version drew in the page. None when neither works (the tile is left out, never a broken picture).
    When the fetch fails, the reason is added to `why` (a list), so a run where nothing came in can say why."""
    if t.get("src"):
        try:
            return fetch_tile(t["src"])
        except OSError as e:                     # curl itself couldn't be started (not on this computer)
            if why is not None:
                why.append(f"curl couldn't be started ({e.strerror or e.__class__.__name__})")
        except ValueError as e:                  # curl's own error, or not an Instagram picture
            if why is not None:
                why.append(" ".join(str(e).split()))
    data = str(t.get("data", ""))
    if data.startswith("data:image/jpeg;base64,"):
        try:
            raw = base64.b64decode(data.split(",", 1)[1], validate=True)
        except ValueError:
            return None
        if raw.startswith(b"\xff\xd8") and len(raw) <= 400_000:
            return raw
    return None


def import_feed(tiles, handle=None):
    """The last posts as the browser saw them: [{href, src (the full-size picture's address) or data (a jpeg data
    URL), w, h, reel, carousel, pinned}]. Fetches or decodes one jpeg per post into the feed folder and replaces
    feed.json whole. Returns the feed. Nothing but a jpeg is ever written into the folder; the addresses are
    used once and not kept."""
    if not isinstance(tiles, list) or not tiles:
        raise ValueError("no tiles")
    FEED_THUMBS.mkdir(parents=True, exist_ok=True)
    posts, seen, why = [], set(), []
    for t in tiles[:FEED_MAX]:
        if not isinstance(t, dict):
            continue      # not a tile (a list saved wrongly): left out, as an unusable tile always was
        pid = post_id(t.get("href", ""))
        if not pid or pid in seen:
            continue
        if this_computer.WINDOWS and this_computer.unreserved(pid) != pid:
            continue      # a PC: "CON.jpg" or "NUL.jpg" would be a device, not a file. Real post codes never are one.
        raw = tile_bytes(t, why)
        if raw is None:
            continue
        (FEED_THUMBS / f"{pid}.jpg").write_bytes(raw)
        seen.add(pid)
        kind = "reel" if t.get("reel") else "carousel" if t.get("carousel") else "photo"
        posts.append({"id": pid, "kind": kind, "pinned": bool(t.get("pinned")), "w": t.get("w"), "h": t.get("h"),
                      "thumb": f"feed/{pid}.jpg"})
    if not posts:
        # say why when the pictures couldn't be fetched (curl's own words: no network, a certificate it can't check,
        # no curl on this computer), so Claude can tell them more than "nothing usable"
        raise ValueError("no usable tiles" + (f"; the first picture couldn't be fetched: {why[0]}" if why else ""))
    old = load_feed()
    for p_ in FEED_THUMBS.glob("*.jpg"):      # the old grid's tiles, no longer shown: set aside, not deleted
        if p_.stem not in seen:
            keep = FEED_THUMBS / "older"
            keep.mkdir(exist_ok=True)
            this_computer.replace(p_, keep / p_.name)   # on a PC, waits a moment if the page is showing it right then
    f = {"handle": (handle or old.get("handle") or "").lstrip("@") or None, "read_at": now(), "posts": posts}
    save_feed(f)
    return f


def grab_script(port=None, handle=None):
    """The snippet to run on their profile page in the browser (the pane's javascript tool, or the console of any
    browser). It scrolls once so the grid fills in, then returns the first tiles as a small list: which post, the
    address of its full-size picture (the largest the page offers), reel / carousel / pinned. Nothing is sent
    anywhere by the page: Claude saves what comes back to a file and `feed --import` fetches the pictures on
    this computer. (Pages on instagram.com are not allowed to talk to 127.0.0.1, and the app's browser pane allows
    no local connection from an outside page at all, so the page cannot hand anything over itself.)"""
    return r"""await (async () => {
  for (let i = 0; i < 4; i++) { window.scrollBy(0, 1600); await new Promise(r => setTimeout(r, 1200)); }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 600));
  const handle = (location.pathname.split('/').filter(Boolean)[0] || '').toLowerCase();
  const links = [...document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')].filter(a => a.querySelector('img')).slice(0, %d);
  const best = img => {
    const c = (img.getAttribute('srcset') || '').split(',').map(x => x.trim().split(/\s+/)).filter(x => x[0])
      .map(x => ({u: x[0], w: parseInt(x[1]) || 0})).sort((a, b) => b.w - a.w);
    return c.length ? c[0].u : (img.currentSrc || img.src);
  };
  const tiles = links.map(a => {
    const img = a.querySelector('img');
    const href = a.getAttribute('href').split('?')[0];
    return {href, src: best(img), reel: href.includes('/reel/'),
      carousel: !!a.querySelector('svg[aria-label="Carousel"]'), pinned: !!a.querySelector('svg[aria-label="Pinned post icon"]')};
  });
  return JSON.stringify({handle, tiles});
})()""" % FEED_MAX


def feed_words(f):
    if not f["posts"]:
        return "I haven't read your Instagram grid yet." + (f" Your handle is @{f['handle']}." if f.get("handle") else "")
    when = f.get("read_at", "")[:10]
    try:
        when = nice_day(when)
    except ValueError:
        pass
    pinned = sum(1 for x in f["posts"] if x.get("pinned"))
    return (f"Your grid, read {when}: the last {len(f['posts'])} posts" + (f" on @{f['handle']}" if f.get("handle") else "")
            + (f", {pinned} pinned" if pinned else "") + ".")


# ---------- a post's panel: its grid photo and its words (Nicole's v20 section 5 and v21 section 2) ----------
# Hers reads the photo list and the words from a second server, open to any page. Ours: this server answers
# GET /posting/panel?id=<piece> itself (its own name in Host, never for another website's page), the pictures are
# the small copies the pickers already make (/kit-photo) and the slides the kit page already serves (/content),
# the words are read from words.py here in the server, and a pick is saved by POST /posting {action: "cover"}.
# The page names a piece by its id and a photo by "Photos/<file name>" or "Carousel/<file name>"; no path goes
# to the page or comes from it.
PANEL_KINDS = ("reel", "carousel")
POST_CAP = 65536                 # a press on the posting page is a few hundred bytes
COVER_BOX = (360, 450)           # a grid tile, as every piece's thumbnail


def panel_role(x):
    """"reel" or "carousel" when a click on this piece's tile opens its panel, else "". A kit's reel or carousel
    (a carousel shown as a single post too: its slides and its words are the carousel's); a piece made without a
    kit ("add --shoot") by its kind, so the panel can say its photos can't be found. A photo from the Singles
    folder has no panel: it has one photo and no words (decision 6)."""
    role = kit_role(x)
    if role in PANEL_KINDS:
        return role
    if not role and not kit_folder(x) and x.get("kind") in PANEL_KINDS:
        return x["kind"]
    return ""


def piece_kit(x):
    """The kit folder of a queue piece as it is in Your Content right now (arrange.kit_by_name: its exact name in
    the folder's own listing, a real folder, never the path the piece kept), or None."""
    import arrange
    name = kit_folder(x)
    return arrange.kit_by_name(name) if name and kit_role(x) else None


def panel_choices(x, kit):
    """The photos a post's tile can show, as the page draws them: [{src, rel, in_reel | first}].
    A reel: its own photos first, in the order Make my reel would use, then every other photo of the shoot.
    A carousel: the slides the kit page shows as the carousel, in order. (choices, are small copies still to make)"""
    import arrange
    import kit as kit_mod
    kq = quote(kit.name, safe="")
    rec = kit_mod.load_rec(kit)
    if not isinstance(rec, dict):
        rec = {}
    if panel_role(x) == "carousel":
        files = kit_mod.carousel_shown(kit, rec)["files"]
        return [{"src": "/content/%s/Carousel/%s" % (kq, quote(f.name, safe="")), "rel": "Carousel/" + f.name, "first": i == 0}
                for i, f in enumerate(files)], False
    import reel_page
    rows = arrange.sheet_rows(kit)
    if not rows:
        return [], False
    try:
        order = [o["n"] for o in reel_page.order_for_kit_page(kit, rows, rec)]
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        order = []
    by_n = {r["n"]: r for r in rows}
    order = [n for i, n in enumerate(order) if n in by_n and n not in order[:i]]
    inside = set(order)
    shown = [by_n[n] for n in order] + [r for r in rows if r["n"] not in inside]
    photos, _ = arrange.page_photos(kit, rec, shown)
    out, need = [], False
    for row, ph in zip(shown, photos):
        if ph["missing"] and not ph["have"]:
            continue                                   # can't be reached, or can't be read: not one to pick
        need = need or not ph["have"]
        out.append({"src": "/kit-photo?kit=%s&n=%d&size=s&v=%s" % (kq, ph["n"], quote(ph["v"] or "", safe="")),
                    "rel": "Photos/" + arrange.photo_name(row), "in_reel": row["n"] in inside})
    return out, need


def panel_words(x, kit):
    """The post's words for its panel, straight from words.py: {piece, caption, hook}. The caption is the drafted
    one, or their own when that is all there is; the hook is the first one they picked (a reel's). None for a
    piece that has no words record (reminders.words_piece decides whose words a piece reads)."""
    import reminders as posting_reminders      # by this name: this file has a reminders() of its own
    import words as words_mod
    which = posting_reminders.words_piece(x)
    if not which:
        return None
    w = (words_mod.load(kit).get("pieces") or {}).get(which)
    w = w if isinstance(w, dict) else {}
    def text(v):
        return v.strip() if isinstance(v, str) else ""
    return {"piece": which, "caption": text(w.get("caption")) or text(w.get("own")),
            "hook": posting_reminders.picked_hook(w) if x.get("kind") == "reel" else ""}


def panel_for(pid):
    """Everything the panel of one upcoming post draws from, or None when there is no such upcoming post.
    {ok, id, choices, cover (the choice in use), words}. A kit that can't be reached right now gives no choices
    and no words (the page then says, in her words, that it can't find the photos)."""
    import arrange
    p = load()
    x = next((y for y in p.get("pieces", []) if isinstance(y, dict) and y.get("id") == pid), None)
    if x is None or x.get("status") != "green" or not panel_role(x):
        return None
    out = {"ok": True, "id": pid, "choices": [], "cover": None, "words": None}
    kit = piece_kit(x)
    if kit is None:
        return out
    try:
        out["choices"], need = panel_choices(x, kit)
        if need and not arrange.cant_make(kit, arrange.sheet_rows(kit)):
            arrange.start_previews(kit)                # a photo in the strip has no small copy yet: made in the background
    except (Exception, SystemExit) as e:  # noqa: BLE001  (the strip only: the words below are still theirs to copy)
        say(f"posting panel: the photos of {kit.name!r} couldn't be listed ({e.__class__.__name__}: {str(e)[:160]})")
        out["choices"] = []
    rels = [c["rel"] for c in out["choices"]]
    cover = x.get("cover") if isinstance(x.get("cover"), str) else None
    out["cover"] = next((r for r in rels if cover and _nfc(r) == _nfc(cover)), rels[0] if rels else None)
    try:
        out["words"] = panel_words(x, kit)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        say(f"posting panel: the words of {kit.name!r} couldn't be read ({e.__class__.__name__}: {str(e)[:160]})")
    return out


def cover_tile(pid, rel):
    """The tile for a grid pick, made before the queue is locked (making a picture is the slow part): checks that
    the piece is an upcoming post, that rel names a photo of that piece's own kit (cover_file), and makes the
    small picture with the kit's own fit under a NEW name in the thumbnails folder (the piece's name and a mark
    made from the photo's name, size and date), so the browser shows the new one. The thumbnail before is left
    where it is; nothing is deleted. Returns the new thumbnail's place under the Assistant's folder.
    ValueError, in a few plain words, for anything else."""
    import kit as kit_mod
    p = load()
    x = next((y for y in p.get("pieces", []) if isinstance(y, dict) and y.get("id") == pid), None)
    if x is None:
        raise ValueError("no such post")
    if x.get("status") != "green":
        raise ValueError("not an upcoming post")
    role = kit_role(x)
    kit = piece_kit(x) if role in PANEL_KINDS else None
    if kit is None:
        raise ValueError("this post's kit can't be found")
    f = cover_file(kit, role, rel)
    if f is None:
        raise ValueError("not a photo in this post's kit")
    st = f.stat()
    mark = hashlib.sha1(f"{_nfc(rel)}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8")).hexdigest()[:10]
    THUMBS.mkdir(parents=True, exist_ok=True)
    dst = thumb_file(f"{pid}-{mark}")
    if not dst.is_file() and not kit_mod.fit(f, dst, COVER_BOX):
        raise ValueError("the tile couldn't be made")
    return dst.relative_to(HOME).as_posix()


# ---------- the page ----------

# ---------- posting-day reminders (Nicole's v21, stage 4): the calendar work, always in the background ----------
# reminders.py (imported as posting_reminders: this file has its own reminders(), the taps in the chat) knows
# what the calendar should hold and how to talk to it. Here is only WHEN: after any save in the page server,
# when the posting page is opened (a caption edited on the words page catches up), and after a command that
# changed the queue. Hers ran inside save(), so a press on the page waited for Calendar; ours never does.
# One round at a time; a change that lands while a round runs asks for one more round afterwards.
_SERVING = False                       # True in the page server only (serve())
_IN_ROUND = threading.local()          # .on while this thread is a reminders round (its own save starts no round)
_REMIND = {"lock": threading.Lock(), "running": False, "again": False, "closed": False}   # closed: this server is starting over; no new round
_CALS = {"lock": threading.Lock(), "names": None, "at": 0.0}    # the calendar list last read, for checking a choice
REMIND_WAIT = 170                      # seconds a round waits for another program's round (one Calendar call: 120)
REMIND_ACTS = ("remind", "remind-calendar", "remind-sync", "remind-open")


def remind_backend():
    """Where reminders go on this computer (reminders.default_backend), or None when there is nowhere."""
    import reminders as posting_reminders
    try:
        return posting_reminders.default_backend()
    except Exception:  # noqa: BLE001  (the pretend calendar asked for outside a test: no reminders at all)
        return None


def remind_last():
    """What the last round said: {"at", "problem": plain words or None, "did": [lines]}. Kept in a file, so a
    round a command started is seen by the page too."""
    try:
        d = json.loads((HOME / "reminders" / "last.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _remind_log(detail):
    """The real words of what stopped a round (Python's own, perhaps a file's path) go in logs/reminders.log
    only: never into last.json, which the page reads. Never raises."""
    try:
        (HOME / "logs").mkdir(parents=True, exist_ok=True)
        with open(HOME / "logs" / "reminders.log", "a", encoding="utf-8") as f:
            f.write(f"{now()} stopped: {str(detail)[:400]}\n")
    except Exception:  # noqa: BLE001  (a note only)
        pass


def _remind_keep(res):
    """Note a round's outcome (only when it says something new: most rounds find nothing to do). The problem
    kept for the page is plain words only (reminders._stopped); the real ones go to the log."""
    if res.get("detail") and res.get("detail") != res.get("problem"):
        _remind_log(res["detail"])
    try:
        was = remind_last()
        new = {"at": now(), "problem": res.get("problem") or None, "did": [str(x) for x in (res.get("did") or [])][:20]}
        if new["problem"] != (was.get("problem") or None) or new["did"]:
            (HOME / "reminders").mkdir(parents=True, exist_ok=True)
            write_whole(HOME / "reminders" / "last.json", json.dumps(new, indent=1, ensure_ascii=False))
    except Exception:  # noqa: BLE001  (a note only)
        pass


def remind_once(wait=0):
    """One reminders round, to its end: read the queue, talk to the calendar with the lock let go, merge the few
    fields back (reminders.run). When another program's round is at work, try again for up to `wait` seconds.
    Never raises. reminders.run's result."""
    import reminders as posting_reminders
    end = time.time() + wait
    while True:
        _IN_ROUND.on = True
        try:
            res = posting_reminders.run(load, save, _POSTING_LOCK)
        except BaseException as e:  # noqa: BLE001  (run never raises; if it ever did, the queue is still as it was)
            res = {"changed": False, "changes": {}, "did": [], "problem": posting_reminders.STOPPED_HERE,
                   "detail": f"{e.__class__.__name__}: {str(e)[:160]}", "note": None, "to_open": []}
        finally:
            _IN_ROUND.on = False
        if not res.get("busy") or time.time() >= end:
            break
        time.sleep(0.5)
    if not res.get("busy"):
        _remind_keep(res)
    return res


def _remind_rounds():
    while True:
        try:
            remind_once(wait=REMIND_WAIT)
        except BaseException as e:  # noqa: BLE001
            say(f"reminders: a round stopped ({e.__class__.__name__}: {str(e)[:160]})")
        with _REMIND["lock"]:
            if _REMIND["again"]:
                _REMIND["again"] = False
                continue
            _REMIND["running"] = False
            return


def remind_soon():
    """Bring the reminders into step in the background. Returns at once. A round already running is asked for
    one more afterwards, so the last change in this server is never the one that is missed (a change another
    program makes mid-round is caught by the round itself: reminders.run looks again).
    Once this server has begun starting over after an update (_start_over, fresh.restart) no new round is
    started: it would be cut off mid-call a moment later, leaving an event nobody recorded. The server that
    takes over starts a round of its own as it comes up (serve)."""
    with _REMIND["lock"]:
        if _REMIND["closed"] or fresh._restarting.is_set():
            return
        if _REMIND["running"]:
            _REMIND["again"] = True
            return
        _REMIND["running"] = True
    try:
        threading.Thread(target=_remind_rounds, name="reminders", daemon=True).start()
    except RuntimeError:
        with _REMIND["lock"]:
            _REMIND["running"] = False


def _start_over(handler):
    """Start this server over with the newer code on disk (fresh.restart), unless a reminders round is at work:
    starting over mid-call would leave an event nobody remembers making, so the next page request does it.
    The check and the "no new round from here on" mark are one step, so a press that lands in the moment
    between the "one moment" page and the new server starts no round. True when the request was answered."""
    with _REMIND["lock"]:
        if _REMIND["running"]:
            return False
        _REMIND["closed"] = True
    try:
        if fresh.restart(handler):
            return True
    except BaseException:
        with _REMIND["lock"]:
            _REMIND["closed"] = False
        raise
    with _REMIND["lock"]:
        _REMIND["closed"] = False          # the server stays as it is (the newer code does not compile)
    return False


def remind_state():
    """What the page needs to know about reminders besides each post's own time:
    way: "calendar" (a calendar is chosen once and the Assistant puts the events on it: a Mac), "file" (a
    calendar file per post, for them to open: a PC), or None (no reminders on this computer);
    busy: a round is at work; problem: the last round's trouble in plain words, or None;
    and for "file": waiting {post id: "new" | "again" | "off"} (a file that has not been opened since it last
    changed) and handed [post ids whose latest file was opened in their calendar app]."""
    out = {"way": None, "busy": bool(_REMIND["running"]), "problem": None}
    try:
        backend = remind_backend()
        if backend is None:
            return out
        out["problem"] = remind_last().get("problem") or None
        if getattr(backend, "needs_calendar", True):
            out["way"] = "calendar"
            return out
        out["way"] = "file"
        out["waiting"] = {str(w.get("id")): ("off" if w.get("cancel") else "again" if w.get("again") else "new") for w in backend.waiting()}
        out["handed"] = sorted(str(i) for i in backend.handed())
    except Exception as e:  # noqa: BLE001  (the page is drawn all the same)
        say(f"reminders: couldn't read where things stand ({e.__class__.__name__}: {str(e)[:120]})")
    return out


class _Known:
    """The calendar list already read for the page, standing in for the calendar when a choice is checked
    (reminders.set_calendar asks its backend for the list; asking Calendar again takes a second or more)."""
    def __init__(self, names):
        self.names = list(names)

    def calendars(self):
        return self.names


def calendar_names(fresh_within=0.0):
    """The calendars a reminder could go on, asked of the calendar (a second on a Mac, up to two minutes when
    macOS is waiting for an answer to its permission question). One asker at a time: a second request waits and
    takes the first one's answer. fresh_within: seconds an earlier answer still counts. CalendarProblem in plain
    words when it can't be read. [] where there is no list to choose from (a PC)."""
    import reminders as posting_reminders
    backend = remind_backend()
    if backend is None or not getattr(backend, "needs_calendar", True):
        return []
    with _CALS["lock"]:
        if _CALS["names"] is not None and time.time() - _CALS["at"] <= fresh_within:
            return list(_CALS["names"])
        names = posting_reminders.calendars(backend)
        _CALS["names"], _CALS["at"] = list(names), time.time()
        return list(names)


def _ask_server_to_sync():
    """From a command: ask the running page server to bring the reminders into step (it is the program macOS
    has already asked about Calendar, and it runs one round at a time). True when it took the request."""
    try:
        import urllib.request
        base = (HOME / "posting-url.txt").read_text(encoding="utf-8").strip().rsplit("/", 1)[0]
        if not re.fullmatch(r"http://127\.0\.0\.1:\d{2,5}", base):
            return False
        req = urllib.request.Request(base + "/posting", data=json.dumps({"action": "remind-sync"}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with this_computer.open_local(req, timeout=2) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001  (no server, or not ours: the command does it another way)
        return False


def calendar_in_step():
    """After a command changed the queue (ready, not ready, posted, a move, a new rhythm...): bring the
    posting-day reminders into step WITHOUT making the chat wait for Calendar, and say plainly what was done.
      - nothing on the calendar needs to change (the usual case): nothing is done, nothing is said;
      - a PC (calendar files): writing a file takes no time, so it is done here and said;
      - a Mac: a Calendar call can take two minutes (and the very first can sit behind macOS's permission
        question), and a command cut off mid-call could leave an event nobody remembers making. So the call is
        never made by the command itself: the running page server is asked to do it, and with no server running
        a small helper of its own is started that finishes by itself (posting_queue.py remind-sync, its log in
        logs/reminders.log). Either way the command returns at once and says the calendar is being updated.
    Never raises: a calendar problem never stops a command."""
    try:
        import reminders as posting_reminders
        backend = remind_backend()
        if backend is None:
            return
        acts = [a for a in posting_reminders.plan(posting_reminders.snapshot(load()), need_calendar=getattr(backend, "needs_calendar", True),
                                                  made=posting_reminders._made()) if a.get("do") != "leave"]
        if not acts:
            return
        if getattr(backend, "opens_files", False):
            res = remind_once(wait=10)
            if res.get("busy"):
                say("(Another reminders check is running; the calendar files will follow in a moment.)")
                return
            for line in res.get("did") or []:
                say(line)
            if res.get("note"):
                say(res["note"])
            k = len(res.get("to_open") or [])
            if k:
                say(f"{k} calendar file{' is' if k == 1 else 's are'} waiting to be opened in your calendar app. Nothing changes on your calendar until then.")
            return
        k = len(acts)
        if _ask_server_to_sync():
            say(f"(The reminder{'' if k == 1 else 's'} on your calendar {'is' if k == 1 else 'are'} being brought into step in the background.)")
            return
        fresh.start_server([sys.executable, str(Path(__file__).resolve()), "remind-sync"], "reminders")
        say(f"(The reminder{'' if k == 1 else 's'} on your calendar {'is' if k == 1 else 'are'} being brought into step in the background. "
            "\"python3 reminders.py status\" says where each one stands.)")
    except Exception as e:  # noqa: BLE001
        say(f"(reminders not updated: {e.__class__.__name__}: {str(e)[:120]}. They are tried again when the posting queue page is opened.)")


CSS = r"""
:root{--red:#E0635A;--yellow:#E8B84A;--green:#4FB286}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2)}
.bar .homelink{margin-right:.25rem}.bar .homelink .short{display:none}@media(max-width:560px){.bar .homelink .long{display:none}.bar .homelink .short{display:inline}}
.head{padding:clamp(2rem,5vw,3.4rem) 0 1rem;display:grid;gap:.6rem}
h1{margin:0;font:600 clamp(32px,4.6vw,54px)/1.03 var(--sans);letter-spacing:-.035em;text-wrap:balance}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:38em}
.tankbar{height:14px;border-radius:999px;background:var(--sand-l);overflow:hidden;max-width:520px;margin-top:.4rem}
.tankbar i{display:block;height:100%;border-radius:999px;background:var(--green);transition:width .8s var(--ease)}
.tankbar.low i{background:var(--red)}.tankbar.mid i{background:var(--yellow)}
.rhythm{font-size:14px;color:var(--ink-2)}.rhythm b{color:var(--ink)}
.sec{padding:1.6rem 0 .4rem;display:grid;gap:.3rem}
.sec h2{margin:0;font:600 22px/1.15 var(--sans);letter-spacing:-.02em}
.sec p{margin:0;color:var(--ink-2);font-size:14.5px;max-width:40em}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;max-width:820px;margin:1rem 0 .4rem;background:var(--paper);padding:4px;border-radius:18px;box-shadow:0 1px 0 var(--line)}
.tile{position:relative;aspect-ratio:4/5;background:var(--sand-l);overflow:hidden;border-radius:6px;cursor:grab;user-select:none;transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.tile.mine{touch-action:none}body.lifting,body.lifting *{cursor:grabbing!important}.tile.dragging{opacity:.3;box-shadow:inset 0 0 0 3px var(--coral)}.tile.over{box-shadow:inset 0 0 0 5px var(--sun);transform:scale(.94);transition:transform .18s var(--ease),box-shadow .18s var(--ease)}.tile.lift{position:fixed;left:0;top:0;z-index:9999;margin:0;pointer-events:none;opacity:1;border-radius:8px;transform:scale(1.06);transition:none;box-shadow:inset 0 0 0 3px var(--coral),0 0 0 3px #fff,0 30px 60px -14px rgba(31,36,48,.6),0 8px 18px rgba(31,36,48,.25)}
.tile img{width:100%;height:100%;object-fit:cover;display:block;-webkit-user-drag:none;pointer-events:none}
.tile .k{position:absolute;top:8px;left:8px;font:600 10px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.45);padding:5px 8px;border-radius:999px}
.tile .d{position:absolute;bottom:8px;left:8px;max-width:calc(100% - 16px);font:600 11px/1 var(--sans);letter-spacing:.02em;color:#fff;background:rgba(0,0,0,.78);padding:6px 9px;border-radius:999px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tile.next .d{background:var(--coral);color:#fff}.tile.mine::after{content:'';position:absolute;left:0;right:0;bottom:0;height:42%;background:linear-gradient(to top,rgba(0,0,0,.38),rgba(0,0,0,0));pointer-events:none}.tile.mine .k,.tile.mine .d{z-index:1}.tile.mine:hover{transform:translateY(-3px);box-shadow:inset 0 0 0 3px var(--coral),0 16px 28px -12px rgba(31,36,48,.5)}
.tile.ghost{cursor:default;background:repeating-linear-gradient(45deg,#ECEAF6,#ECEAF6 6px,#E3E0F0 6px,#E3E0F0 12px)}
.tile.ghost small{position:absolute;inset:0;display:grid;place-items:center;font:400 12px/1.2 var(--sans);color:var(--ink-2);text-align:center;padding:8px}
.tile.real{cursor:default}.tile.real img{filter:saturate(.85)}
.tile.real .k{background:rgba(255,255,255,.8);color:var(--ink)}
.tile.mine{box-shadow:inset 0 0 0 3px var(--coral)}.tile.mine .k{background:rgba(0,0,0,.78);color:#fff;text-transform:none;letter-spacing:.02em;font-size:11px}
.gridnote{font-size:13px;color:var(--ink-2);max-width:820px;margin:0}
.list{display:grid;gap:.7rem;padding:.8rem 0 1rem;margin:0;list-style:none}
.row{display:grid;grid-template-columns:auto 64px 1fr auto;gap:.9rem;align-items:center;background:var(--paper);border-radius:18px;padding:.7rem .9rem;box-shadow:0 1px 0 var(--line)}
.light{width:14px;height:14px;border-radius:50%;background:var(--sand-l)}
.light.red{background:var(--red)}.light.yellow{background:var(--yellow)}.light.green{background:var(--green)}
.row .th{width:64px;height:76px;border-radius:10px;overflow:hidden;background:var(--sand-l)}.row .th img{width:100%;height:100%;object-fit:cover;display:block}
.row .name{font:600 17px/1.2 var(--sans);letter-spacing:-.01em}.row .sub{font-size:13.5px;color:var(--ink-2);margin-top:.15rem}
.row .act{display:flex;gap:.5rem;align-items:center}
.btn{border:0;border-radius:999px;padding:.5rem .95rem;font:600 13.5px/1 var(--sans);cursor:pointer;background:var(--ink);color:#fff}
.btn.o{background:transparent;color:var(--ink);border:1px solid var(--line)}
.btn.g{background:var(--green);color:#fff}
.empty{font:400 15px/1.3 var(--sans);color:var(--ink-2);padding:.4rem 0 1rem}
.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#fff;padding:.7rem 1.1rem;border-radius:999px;font-size:14px;opacity:0;transition:all .4s var(--ease);pointer-events:none}
.toast.on{opacity:1;transform:translateX(-50%)}
.offline{font-size:13px;color:var(--coral-2)}
@media(max-width:600px){.row{grid-template-columns:auto 52px 1fr}.row .act{grid-column:2/4}}
/* a post's panel (Nicole's v20 and v21): the note above the grid, the outlined tile, the panel under its row */
.sec p.pickhint{margin:.9rem 0 -.4rem;font:600 14px/1.35 var(--sans);color:var(--coral-2);max-width:none}
.pickhint:before{content:'\270E';margin-right:.45rem}
.tile.mine:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.tile.picking{box-shadow:inset 0 0 0 4px var(--coral-2)!important}
.pick{max-width:820px;margin:.6rem 0 .4rem;background:var(--paper);border-radius:18px;padding:1rem 1.1rem;box-shadow:0 1px 0 var(--line),0 0 0 2px var(--coral-l);min-width:0}
.grid .pick{grid-column:1/-1;margin:4px 0;max-width:none}
.pick .ph{display:flex;align-items:flex-start;gap:1rem;justify-content:space-between}
.pick .ph>div{min-width:0}
.pick .ph b{font:600 17px/1.25 var(--sans);overflow-wrap:anywhere}.pick .ph p{margin:.2rem 0 0;color:var(--ink-2);font-size:14px;max-width:40em}
.pick .x{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:.4rem .8rem;font:600 13px/1 var(--sans);cursor:pointer;white-space:nowrap}
.pick .pw{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin:.7rem 0 0}.pick .pw:empty{display:none}
.pick .pwl{font:600 13.5px/1 var(--sans);color:var(--coral-2);text-decoration:none;margin-left:.3rem}.pick .pwl:hover{text-decoration:underline}
.pick .pwn{font-size:14px;color:var(--ink-2)}
.pick .rslot:empty{display:none}
.pick .pr{margin:.55rem 0 0}.pick .pr:empty{display:none}
.pick .prl{display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;padding:.55rem .7rem;border-radius:12px;background:var(--sun-l)}
.pick .prh{font-size:14px;color:var(--ink);margin-right:.2rem}
.pick .prt{font-size:13.5px;color:var(--ink-2);display:inline-flex;gap:.35rem;align-items:center}.pick .prt input{font:inherit;padding:.3rem .4rem;border:1px solid var(--line);border-radius:8px;background:var(--paper);color:var(--ink)}
.pick .prx{margin-left:auto;border:0;background:transparent;font:400 20px/1 var(--sans);color:var(--ink-2);cursor:pointer;padding:0 .2rem}
.pick .prb.on{border-color:var(--sun);background:var(--sun-l)}
.pick .pn{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin:.5rem 0 0;font-size:14px;color:#8a4a12;background:#FFF4EC;border-radius:10px;padding:.55rem .8rem}.pick .pn:empty{display:none}
.pick .strip{display:flex;gap:6px;overflow-x:auto;padding:.8rem 0 .3rem;scroll-snap-type:x proximity}
.pick .strip .empty{padding:0;margin:0}
.pick .c{flex:none;width:96px;aspect-ratio:4/5;border-radius:8px;overflow:hidden;cursor:pointer;position:relative;scroll-snap-align:start;box-shadow:0 0 0 1px var(--line);background:var(--sand-l);border:0;padding:0}
.pick .c img{width:100%;height:100%;object-fit:cover;display:block}
.pick .c:hover{box-shadow:0 0 0 2px var(--coral)}
.pick .c.on{box-shadow:0 0 0 3px var(--coral-2)}
.pick .c.on::after{content:'\2713';position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:50%;background:var(--coral-2);color:#fff;display:grid;place-items:center;font:700 12px/1 var(--sans)}
.pick .c .n{position:absolute;left:6px;bottom:6px;font:600 10px/1 var(--sans);color:#fff;background:rgba(0,0,0,.6);padding:4px 6px;border-radius:999px}
.pick .warn{margin:.5rem 0 0;font-size:14px;color:#8a4a12;background:#FFF4EC;border-radius:10px;padding:.6rem .8rem;max-width:40em}
.pick .warn:empty{display:none}
.pick .sep{flex:none;align-self:center;font:600 10px/1.2 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);padding:0 .4rem;width:70px;text-align:center}
"""

SCRIPT = r"""
const D=JSON.parse(document.getElementById('data').textContent);const live=location.protocol.startsWith('http');
const $=s=>document.querySelector(s);const toast=$('#toast');let tt;
function say(m){toast.textContent=m;toast.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>toast.classList.remove('on'),2400)}
function esc(t){return String(t==null?'':t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}   // a shoot's name is theirs: only ever text
function nice(iso){if(!iso)return'';const d=new Date(iso+'T12:00:00');return d.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}
async function post(body){if(!live){say('This is a saved copy. Ask Claude to “show my posting queue” to change things.');return null}
 try{const r=await fetch('/posting',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw 0;return await r.json()}catch(e){say('Could not reach the Assistant. Tell Claude instead.');return null}}
function render(S){LAST=S;
 $('#tankh').innerHTML=S.tank_head;$('#tankp').textContent=S.tank_line;
 const bar=$('#tankbar');bar.className='tankbar'+(S.weeks===null?'':S.weeks<=1?' low':S.weeks<=2?' mid':'');bar.firstElementChild.style.width=(S.weeks===null?0:Math.min(100,S.weeks/4*100))+'%';
 $('#rhythm').innerHTML=S.interval?`Posting <b>${S.interval_words}</b>. Tell Claude to change it.`:`No posting rhythm yet. Tell Claude how often you like to post.`;
 const g=$('#grid');if(PEL.parentNode===g)g.after(PEL);g.innerHTML='';   // the panel is kept (it lives under a row of the grid while open)
 const greens=S.greens.slice().reverse();  // Instagram shows the newest first: the last in line sits top-left
 const feed=S.feed&&S.feed.posts||[];const pinned=feed.filter(x=>x.pinned),rest=feed.filter(x=>!x.pinned);
 const real=x=>{const t=document.createElement('div');t.className='tile real';t.innerHTML=`<img src="${x.thumb}" alt="">`+(x.pinned?`<span class="k">pinned</span>`:'');return t};
 pinned.forEach(x=>g.appendChild(real(x)));   // Instagram keeps pinned posts at the top; new posts land after them
 {const h=$('#pickhint');if(h)h.hidden=!(live&&S.greens.some(x=>x.role))}   // her note, only when there is a post to click
 const nextId=S.greens[0]&&S.greens[0].id;   // first in line: the next post
 greens.forEach(x=>{const t=document.createElement('div');t.className='tile mine'+(x.id===nextId?' next':'');t.dataset.id=x.id;
  if(live&&x.role){t.title='Click to change its photo or copy its caption · drag to move it';t.tabIndex=0}
  t.innerHTML=(x.thumb?`<img src="${esc(x.thumb)}" alt="">`:'')+`<span class="k">${x.kind==='reel'?'&#9654;&#xFE0E; Reel':x.kind==='single'?'&#9634;&#xFE0E; Single post':'&#10697; Carousel'}</span><span class="d">${x.id===nextId?'Next up · ':''}${nice(x.date)}</span>`;g.appendChild(t)});
 if(feed.length){for(const x of rest){if(g.children.length>=15)break;g.appendChild(real(x))}   // every post read, five rows at most
  while(g.children.length%3){const t=document.createElement('div');t.className='tile ghost';t.innerHTML='<small>older posts</small>';g.appendChild(t)}}
 else for(let i=0;i<Math.max(0,9-greens.length);i++){const t=document.createElement('div');t.className='tile ghost';t.innerHTML=`<small>${i===0&&greens.length===0?'nothing ready yet':'what’s on your feed now'}</small>`;g.appendChild(t)}
 $('#gridnote').innerHTML=S.feed&&S.feed.posts.length?`Your last ${S.feed.posts.length} posts${S.feed.handle?' on <b>@'+esc(S.feed.handle)+'</b>':''}, read ${nice(S.feed.read_at.slice(0,10))}, with the pieces you've green-lit in their place. Say “read my grid again” to Claude to bring it up to date.`:`To see your real feed behind these, say “read my Instagram grid” to Claude.`;
 const mk=(sel,items,empty,act)=>{const el=$(sel);el.innerHTML='';if(!items.length){el.innerHTML=`<li class="empty">${empty}</li>`;return}
  items.forEach(x=>{const li=document.createElement('li');li.className='row';li.innerHTML=`<span class="light ${esc(x.status)}"></span><span class="th">${x.thumb?`<img src="${esc(x.thumb)}" alt="">`:''}</span><div><div class="name">${esc(x.shoot_name)} ${esc(x.kind)}${x.n?' '+esc(x.n):''}</div><div class="sub">${act.sub(x)}</div></div><div class="act">${act.btns(x)}</div>`;el.appendChild(li)})};
 mk('#greens',S.greens,'Nothing ready to post yet.',{sub:x=>x.date?`Down for ${nice(x.date)}`:'Ready, waiting for a rhythm',btns:x=>`<button class="btn" data-a="posted" data-id="${esc(x.id)}">Posted</button><button class="btn o" data-a="unready" data-id="${esc(x.id)}">Not ready yet</button>`});
 mk('#yellows',S.yellows,'Nothing in progress.',{sub:x=>`In progress${x.where?': '+esc(x.where):''}${x.days!=null?` · ${x.days} day${x.days!==1?'s':''}`:''}`,btns:x=>`<button class="btn g" data-a="ready" data-id="${esc(x.id)}">Ready to post</button>`});
 mk('#reds',S.reds,'Nothing waiting to be made.',{sub:x=>`Not started. Say “make the ${esc(x.shoot_name)} ${esc(x.kind)}” to Claude.`,btns:x=>`<button class="btn o" data-a="skip" data-id="${esc(x.id)}">Skip this one</button>`});
 document.querySelectorAll('[data-a]').forEach(b=>b.onclick=async()=>{const S2=await post({action:b.dataset.a,id:b.dataset.id});if(S2){render(S2);say({posted:'Posted. Nice.',ready:'Green light. It has a date now.',unready:'Back to in progress.',skip:'Skipped.'}[b.dataset.a])}});
 drag(S);
 if(PICK)openPick(PICK,true);watchRemind();}   // an open panel survives every redraw: put back under its post's row, its photos and words read again
function drag(S){if(!live)return;const g=$('#grid');drag.st={g,src:null,lift:null,over:null,sx:0,sy:0,ox:0,oy:0,on:false};
 // The Studio draws its own drag: a crisp copy of the tile with a border and a shadow follows the pointer, the tile the copy
 // mostly covers gets a yellow stroke (the target is where the picture sits, not where the pointer is), and the spot it left
 // stays dimmed. Pointer events, so it works with a mouse, a trackpad and a finger; the browser's own drag (which took over
 // mid-move when a drag started on the photo and froze the copy; Dustin, Oct 28) is switched off on every tile and photo.
 g.querySelectorAll('.tile.mine').forEach(t=>{t.draggable=false;t.querySelectorAll('img').forEach(i=>i.draggable=false);
  t.addEventListener('dragstart',e=>e.preventDefault());
  t.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target===t){e.preventDefault();openPick(t.dataset.id)}});
  t.addEventListener('pointerdown',e=>{if(e.button!==0)return;const s=drag.st;s.src=t;s.sx=e.clientX;s.sy=e.clientY;const r=t.getBoundingClientRect();s.ox=e.clientX-r.left;s.oy=e.clientY-r.top;try{t.setPointerCapture(e.pointerId)}catch(_){}e.preventDefault()});});
 if(drag.wired)return;drag.wired=true;   // the listeners below live on the document once; they read drag.st, which every render replaces
 const mark=t=>{const s=drag.st;if(s.over===t)return;if(s.over)s.over.classList.remove('over');s.over=(t&&t!==s.src)?t:null;if(s.over)s.over.classList.add('over')};
 const target=()=>{const s=drag.st;if(!s.lift)return null;const L=s.lift.getBoundingClientRect();let best=null,bestA=0;
  for(const t of s.g.querySelectorAll('.tile.mine')){if(t===s.src)continue;const r=t.getBoundingClientRect();
   const w=Math.min(L.right,r.right)-Math.max(L.left,r.left),h=Math.min(L.bottom,r.bottom)-Math.max(L.top,r.top);const a=(w>0&&h>0)?w*h:0;if(a>bestA){bestA=a;best=t}}
  return (best&&bestA>0.3*L.width*L.height)?best:null};   // the tile the copy mostly covers; nothing when it is mostly over nothing
 const stop=()=>{const s=drag.st;if(s.lift)s.lift.remove();s.lift=null;if(s.src)s.src.classList.remove('dragging');mark(null);s.src=null;s.on=false;document.body.classList.remove('lifting')};
 document.addEventListener('pointermove',e=>{const s=drag.st;if(!s.src)return;
  if(!s.on){if(Math.hypot(e.clientX-s.sx,e.clientY-s.sy)<6)return;s.on=true;const r=s.src.getBoundingClientRect();s.lift=s.src.cloneNode(true);s.lift.classList.add('lift');s.lift.style.width=r.width+'px';s.lift.style.height=r.height+'px';document.body.appendChild(s.lift);s.src.classList.add('dragging');document.body.classList.add('lifting')}
  s.lift.style.left=(e.clientX-s.ox)+'px';s.lift.style.top=(e.clientY-s.oy)+'px';mark(target())});
 const finish=async()=>{const s=drag.st;if(!s.src)return;const from=s.src,to=s.over,was=s.on;stop();if(!was){openPick(from.dataset.id);return}   // a press that didn't move 6 px is a click: the post's panel
  if(!to||to===from)return;
  const list=[...s.g.querySelectorAll('.tile.mine')];const a=list.indexOf(from),b=list.indexOf(to);list.splice(a,1);list.splice(b,0,from);const order=list.map(x=>x.dataset.id).reverse();  // back to line order (first to post first)
  const S2=await post({action:'order',ids:order});if(S2){render(S2);say('Moved. The dates follow the order.')}};
 document.addEventListener('pointerup',finish);document.addEventListener('pointercancel',stop);window.addEventListener('blur',stop);
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&drag.st.src)stop()});}
// ---------- a post's panel (Nicole's v20 and v21): the photo it shows in the grid, and its words to copy ----------
// It opens right under the row of the post that was clicked, across all three columns; the clicked tile is outlined.
// The photos and the words come from this same server (GET /posting/panel?id=), never from another one; a photo is
// named by "Photos/<file>" or "Carousel/<file>", a post by its id. Every word of theirs is set as text, never as HTML.
var LAST=D,PICK=null,PSEQ=0;
const PEL=$('#pick');
const PW={reel_line:'Pick the photo your reel shows in your grid. When you post it, tap Edit cover and choose the same photo so your feed matches.',
 carousel_line:'Instagram shows a carousel’s first slide in your grid, so pick the slide you want people to see first.',
 done:'Done',finding:'Finding the photos…',cant:'I can’t find this post’s photos right now. Open its post kit once, then try again.',
 more:'More from the shoot',slide:'Slide ',
 warn:'This isn’t your first slide, so your real grid will show slide 1 instead. To match, move this one to the front in the carousel designer.',
 changed_reel:'Changed. Pick this one as the cover when you post.',changed_carousel:'Changed. That’s its photo in your grid now.',
 copy_caption:'Copy caption',copy_hook:'Copy my hook',open_words:'Open my words',write_words:'Write my words',no_caption:'No caption yet.',
 no_hook:'Pick a hook on your words page first.',no_hook_tip:'Pick a hook on your words page first',
 copied:'Copied {what}. Paste it into Instagram.',your_caption:'your caption',your_hook:'your hook'};
const KINDW={reel:'reel',carousel:'carousel',single:'single post'};
function mkel(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e}
function copyText(t,what){   // the old way first: the Claude app's pane refuses navigator.clipboard, and honors this from a click
 let ok=false;const a=document.createElement('textarea');a.value=t;a.setAttribute('readonly','');a.style.cssText='position:fixed;left:-9999px;top:0;opacity:0';document.body.appendChild(a);
 try{a.select();a.setSelectionRange(0,t.length);ok=document.execCommand('copy')}catch(e){ok=false}a.remove();
 const said=()=>say(PW.copied.replace('{what}',what));
 if(ok){said();return}
 try{navigator.clipboard.writeText(t).then(said,()=>say('Could not copy that. Tell Claude instead.'))}catch(e){say('Could not copy that. Tell Claude instead.')}}
function closePick(){PICK=null;PSEQ++;PEL.hidden=true;PEL.textContent='';delete PEL.dataset.id;document.querySelectorAll('.tile.picking').forEach(z=>z.classList.remove('picking'))}
function placePick(id){   // right under the row of the post that was clicked
 const g=$('#grid'),tiles=[...g.children].filter(c=>c!==PEL),t=tiles.find(c=>c.dataset&&c.dataset.id===id),i=tiles.indexOf(t);
 const end=tiles[Math.min(tiles.length-1,Math.floor(Math.max(0,i)/3)*3+2)];if(end)end.after(PEL);else g.appendChild(PEL);
 document.querySelectorAll('.tile.picking').forEach(z=>z.classList.remove('picking'));if(t)t.classList.add('picking')}
function openPick(id,again){
 const x=(LAST.greens||[]).find(y=>y.id===id);
 if(!live||!x||!x.role){if(PICK===id||again)closePick();return}
 if(PICK===id&&!again){closePick();return}    // the same post clicked again closes it
 const fresh=PEL.dataset.id!==id;PICK=id;PEL.hidden=false;placePick(id);
 if(fresh){PEL.dataset.id=id;PEL.textContent='';
  const ph=mkel('div','ph'),hd=mkel('div');hd.appendChild(mkel('b',null,'Your '+(x.shoot_name||'')+' '+(KINDW[x.kind]||x.kind)));
  hd.appendChild(mkel('p',null,x.role==='reel'?PW.reel_line:PW.carousel_line));ph.appendChild(hd);
  const done=mkel('button','x',PW.done);done.type='button';done.onclick=closePick;ph.appendChild(done);PEL.appendChild(ph);
  PEL.appendChild(mkel('div','pw'));      // the button row: Copy caption, Copy my hook, [stage 4's reminder button], Open my words
  PEL.appendChild(mkel('div','pr'));      // the reminder drop-down opens here (closed, it is empty and takes no room)
  PEL.appendChild(mkel('div','pn'));      // ours: one plain line when the calendar could not be updated (empty otherwise)
  const strip=mkel('div','strip');strip.appendChild(mkel('p','empty',PW.finding));PEL.appendChild(strip);
  PEL.appendChild(mkel('p','warn'));
  if(!again)PEL.scrollIntoView({block:'nearest',behavior:'smooth'})}
 else remindNow(x);      // a redraw: the reminder's button and drop-down follow at once (the photos and words follow the fetch below)
 const seq=++PSEQ;
 fetch('/posting/panel?id='+encodeURIComponent(id),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null).then(P=>{
  if(seq!==PSEQ||PICK!==id)return;      // closed, or another post's panel opened, while this was on its way
  drawPick(x,P&&P.ok?P:{choices:[],cover:null,words:null},fresh)})}
function drawPick(x,P,fresh){const el=PEL,reel=x.role==='reel',C=P.choices||[];
 drawWords(el,x,P.words);
 const strip=el.querySelector('.strip'),warn=el.querySelector('.warn'),at=strip.scrollLeft;strip.textContent='';warn.textContent='';
 if(!C.length){strip.appendChild(mkel('p','empty',PW.cant));return}
 const cur=P.cover||C[0].rel;let sep=false,on=null;
 C.forEach((c,i)=>{if(reel&&!c.in_reel&&!sep&&i>0){sep=true;strip.appendChild(mkel('span','sep',PW.more))}
  const b=mkel('button','c'+(c.rel===cur?' on':''));b.type='button';b.dataset.rel=c.rel;if(!reel)b.title=PW.slide+(i+1);
  b.setAttribute('aria-pressed',c.rel===cur?'true':'false');
  const im=document.createElement('img');im.alt='';im.loading='lazy';let tries=0;
  im.onerror=()=>{if(tries++<8)setTimeout(()=>{im.src=c.src+(c.src.indexOf('?')<0?'?':'&')+'again='+tries},1500)};   // a small copy still being made
  im.src=c.src;b.appendChild(im);if(!reel)b.appendChild(mkel('span','n',String(i+1)));
  if(c.rel===cur)on=b;
  b.onclick=async()=>{if(c.rel===cur)return;const S2=await post({action:'cover',id:x.id,rel:c.rel});if(S2){render(S2);say(reel?PW.changed_reel:PW.changed_carousel)}};
  strip.appendChild(b)});
 const first=C.find(c=>c.first);
 warn.textContent=(!reel&&first&&cur!==first.rel)?PW.warn:'';
 if(fresh&&on)strip.scrollLeft=Math.max(0,on.offsetLeft-strip.offsetLeft-(strip.clientWidth-on.offsetWidth)/2);else strip.scrollLeft=at}
function drawWords(el,x,W){const w=el.querySelector('.pw');w.textContent='';if(!W||!x.folder)return;   // no words record for this post: no row
 const page='/words.html?kit='+encodeURIComponent(x.folder)+'&piece='+encodeURIComponent(W.piece);
 const link=t=>{const a=mkel('a','pwl',t+' →');a.href=page;return a};
 // the "Set a reminder to post" button sits in this place in the row (remindButton(x) returns it, or null)
 const slot=mkel('span','rslot');slot.dataset.remindSlot=x.id;const rb=remindButton(x);if(rb)slot.appendChild(rb);
 if(!W.caption){w.appendChild(mkel('span','pwn',PW.no_caption));w.appendChild(slot);w.appendChild(link(PW.write_words));wireRemind(el,x);return}
 const cap=mkel('button','btn',PW.copy_caption);cap.type='button';cap.dataset.c='cap';cap.onclick=()=>copyText(W.caption,PW.your_caption);w.appendChild(cap);
 if(x.kind==='reel'){const hb=mkel('button','btn o',PW.copy_hook);hb.type='button';hb.dataset.c='hook';if(!W.hook)hb.title=PW.no_hook_tip;
  hb.onclick=()=>W.hook?copyText(W.hook,PW.your_hook):say(PW.no_hook);w.appendChild(hb)}
 w.appendChild(slot);w.appendChild(link(PW.open_words));wireRemind(el,x)}
// ---------- posting-day reminders (Nicole's v21) ----------
// A drop-down, closed until they press "Set a reminder to post" (she found it too big open all the time). One pale
// yellow line: text, then buttons, a small × on the right. Every word a Mac shows is hers. The calendar itself is
// never waited for by a press: the server saves, answers, and brings the calendar into step in the background
// (LAST.reminding says how that went). A PC has no calendar to choose and gets a calendar file to open instead
// (LAST.reminding.way==='file'): those lines are ours, and say only what is true there.
const TIMES=[['09:00','9 am'],['12:00','Noon'],['18:00','6 pm'],['20:00','8 pm']];
let RMODE={};   // which post's reminder drop-down is open, and how: 'ask' | 'time' | 'cal' (kept outside the panel: it is redrawn often)
let CALS=null;  // the calendar list being asked for: {st:'wait'|'ok'|'fail', names, problem, slow}
const RW={set:'Set a reminder to post',on:'🔔 Reminder: ',close:'Close',
 ask:'Want a reminder on its posting day? Your phone will tell you when to post, with your caption ready to copy.',
 yes:'Remind me',no:"I'll post it myself",what:'What time?',or:'or ',own:'Set',
 finding:'Finding your calendars…',cant:'I can’t reach your Calendar right now.',
 which:'Which calendar does your phone show?',which2:' Your reminders go there.',
 on1:"🔔 I'll remind you on ",on2:' on your ',on3:' calendar, with your caption in it.',change:'Change time',off:'Turn off',
 set_toast:'Reminder set: {when}.',off_toast:'No reminder for this one.',
 // ours (hers has none of these): a slow or failing calendar, and trying again
 slow:' If your Mac asks whether this can use your Calendar, say yes.',again:'Try again',
 trouble:'I couldn’t update your calendar just now.',
 // ours: a post with no posting day yet (no rhythm set). Its reminder is not on any calendar, so nothing may say it is
 wait1:'🔔 Your reminder at ',wait2:' is waiting until this post has a posting day.',
 // ours, a PC only: a reminder there is a calendar file they open in their calendar app
 pc_ask:'Want a reminder on its posting day? I’ll make a calendar file to add to your calendar, with your caption in it.',
 pc_new1:'🔔 Your reminder for ',pc_new2:' is ready. It isn’t on your calendar until you add it.',
 pc_again2:' has changed. Add it to your calendar again.',
 pc_handed1:'🔔 Reminder for ',pc_handed2:': opened in your calendar app. I can’t see your calendar, so check that it’s there and that it has an alert.',
 pc_notyet2:' isn’t ready to add yet. Give it a moment.',
 pc_add:'Add to my calendar',pc_add_again:'Add it again',
 pc_off:'This reminder is off. If it’s already on your calendar, take it off there too.',pc_take:'Take it off my calendar',pc_off2:' If your calendar app keeps it, delete that one event by hand.',
 pc_new_one:'Set a new reminder',
 pc_set_toast:'Reminder ready: {when}. Add it to your calendar.',pc_off_toast:'Reminder off. Take it off your calendar too.',
 pc_opened:'Opened in your calendar app. Say yes to it there.',pc_opened_n:'Opened {n} reminders in your calendar app. Say yes to each one there.',
 pc_open_cant:'I couldn’t open that calendar file. Tell Claude instead.',pc_trouble:'I couldn’t make your calendar file just now.'};
function hm(t){if(!t)return'';let[h,m]=t.split(':').map(Number);const ap=h>=12?'pm':'am';h=h%12||12;return h===12&&m===0&&ap==='pm'?'noon':`${h}${m?':'+String(m).padStart(2,'0'):''} ${ap}`}
function RM(){return LAST.reminding||{}}
function remindButton(x){if(!live||!RM().way)return null;
 if(!x.date&&!x.remind_on)return null;   // no posting day yet: there is no day to be reminded on, so no button (ours; hers showed "Reminder: , 9 am")
 const b=mkel('button','btn o prb'+(x.remind_on?' on':''),x.remind_on?RW.on+(x.date?nice(x.date)+', ':'')+hm(x.remind_time||(LAST.remind||{}).time):RW.set);
 b.type='button';b.dataset.r='';b.setAttribute('aria-expanded',RMODE[x.id]?'true':'false');return b}
function wireRemind(el,x){const b=el.querySelector('[data-r]');
 if(b)b.onclick=()=>{RMODE[x.id]=RMODE[x.id]?null:'ask';if(!RMODE[x.id])CALS=null;b.setAttribute('aria-expanded',RMODE[x.id]?'true':'false');pickRemind(el,x)};
 pickRemind(el,x);remindNote(el,x)}
function remindNow(x){const slot=PEL.querySelector('[data-remind-slot]');if(!slot)return;   // the row is drawn: put the button and the drop-down in step with the newest state
 slot.textContent='';const rb=remindButton(x);if(rb)slot.appendChild(rb);wireRemind(PEL,x)}
function redrawRemind(){if(!PICK||PEL.hidden)return;const x=(LAST.greens||[]).find(y=>y.id===PICK);if(x)remindNow(x)}
function askCalendars(){const mine=CALS={st:'wait'};
 const slow=setTimeout(()=>{if(CALS===mine&&mine.st==='wait'){mine.slow=true;redrawRemind()}},8000);   // Calendar opening by itself takes about five
 fetch('/posting/calendars',{cache:'no-store'}).then(z=>z.json()).then(j=>{clearTimeout(slow);if(CALS!==mine)return;
   if(j.ok&&(j.calendars||[]).length){mine.st='ok';mine.names=j.calendars}else{mine.st='fail';mine.problem=j.problem||''}redrawRemind()})
  .catch(()=>{clearTimeout(slow);if(CALS!==mine)return;mine.st='fail';mine.problem='';redrawRemind()})}
function pickRemind(el,x,mode){const r=el.querySelector('.pr');if(!r||!live)return;const R=LAST.remind||{},M=RM(),pc=M.way==='file';
 if(mode)RMODE[x.id]=mode;mode=RMODE[x.id];
 const box=r.querySelector('input[type=time]'),typed=box&&r.dataset.mode==='time'&&r.dataset.id===x.id?box.value:'';   // a time being typed survives a redraw
 r.textContent='';r.dataset.mode=mode||'';r.dataset.id=x.id;
 if(!mode||!M.way)return;
 const l=mkel('div','prl');r.appendChild(l);
 const words=(...parts)=>{const s=mkel('span','prh');parts.forEach(p=>s.appendChild(typeof p==='string'?document.createTextNode(p):p));l.appendChild(s);return s};
 const btn=(label,m,dark)=>{const b=mkel('button',dark?'btn':'btn o',label);b.type='button';if(m)b.dataset.m=m;l.appendChild(b);return b};
 const close=()=>{const c=mkel('button','prx','×');c.type='button';c.title=RW.close;c.setAttribute('aria-label',RW.close);c.dataset.close='';
  c.onclick=()=>{RMODE[x.id]=null;CALS=null;pickRemind(el,x);const b=el.querySelector('[data-r]');if(b)b.setAttribute('aria-expanded','false')};l.appendChild(c)};
 const when=t=>`${nice(x.date)} at ${hm(t)}`;
 const setT=async t=>{const was=M.handed&&M.handed.indexOf(x.id)>=0||(M.waiting||{})[x.id]==='again';
  RMODE[x.id]=pc&&(t||was)?'ask':null;r.textContent='';     // a Mac: saved, closed. A PC: the line with the file to open stays
  const S2=await post({action:'remind',id:x.id,time:t});
  if(S2){render(S2);say(t?(pc?RW.pc_set_toast:RW.set_toast).replace('{when}',when(t)):(pc&&was?RW.pc_off_toast:RW.off_toast))}else pickRemind(el,x)};
 const openFiles=async()=>{const S2=await post({action:'remind-open'});if(!S2)return;
  render(S2);say(S2.open_problem?RW.pc_open_cant:S2.opened>1?RW.pc_opened_n.replace('{n}',S2.opened):RW.pc_opened)};
 if(!x.date){     // no posting day yet: a reminder that is on is waiting, and can only be turned off; none can be set
  if(!x.remind_on){RMODE[x.id]=null;r.textContent='';r.dataset.mode='';return}
  words(RW.wait1,mkel('b',null,hm(x.remind_time||R.time)),RW.wait2);btn(RW.off,'off').onclick=()=>setT(null);close();return}
 if(mode==='cal'||(mode==='time'&&!pc&&!R.calendar)){     // the very first time (a Mac): which calendar, then the times
  if(!CALS)askCalendars();
  if(CALS.st==='wait'){words(RW.finding+(CALS.slow?RW.slow:''));close();return}
  if(CALS.st==='fail'){words(RW.cant+(CALS.problem?' '+CALS.problem:''));btn(RW.again,'again').onclick=()=>{CALS=null;pickRemind(el,x)};close();return}
  words(mkel('b',null,RW.which),RW.which2);
  CALS.names.forEach(n=>{const b=btn(n);b.dataset.cal=n;b.onclick=async()=>{const S2=await post({action:'remind-calendar',calendar:n});if(S2){LAST=S2;pickRemind(el,x,'time')}}});
  close();return}
 if(mode==='time'){words(mkel('b',null,RW.what));
  TIMES.forEach(([v,t])=>{const b=btn(t);b.dataset.t=v;b.onclick=()=>setT(v)});
  const lab=mkel('label','prt',RW.or),inp=document.createElement('input');inp.type='time';inp.value=typed||x.remind_time||R.time||'18:00';lab.appendChild(inp);
  const own=mkel('button','btn o',RW.own);own.type='button';own.dataset.own='';own.onclick=()=>{const v=inp.value;if(v)setT(v.slice(0,5))};lab.appendChild(own);l.appendChild(lab);
  close();return}
 if(x.remind_on&&pc){const t=x.remind_time||R.time,w=(M.waiting||{})[x.id],handed=(M.handed||[]).indexOf(x.id)>=0;
  if(w==='new'||w==='again'){words(RW.pc_new1,mkel('b',null,when(t)),w==='new'?RW.pc_new2:RW.pc_again2);btn(w==='new'?RW.pc_add:RW.pc_add_again,'add',true).onclick=openFiles}
  else if(handed)words(RW.pc_handed1,mkel('b',null,when(t)),RW.pc_handed2);
  else words(RW.pc_new1,mkel('b',null,when(t)),RW.pc_notyet2);
  btn(RW.change,'time');btn(RW.off,'off');
  r.querySelector('[data-m="time"]').onclick=()=>pickRemind(el,x,'time');r.querySelector('[data-m="off"]').onclick=()=>setT(null);close();return}
 if(x.remind_on){words(RW.on1,mkel('b',null,when(x.remind_time||R.time)),RW.on2+(R.calendar||'')+RW.on3);btn(RW.change,'time');btn(RW.off,'off');
  r.querySelector('[data-m="time"]').onclick=()=>pickRemind(el,x,'time');r.querySelector('[data-m="off"]').onclick=()=>setT(null);close();return}
 if(pc&&(M.waiting||{})[x.id]==='off'){words(RW.pc_off+RW.pc_off2);btn(RW.pc_take,'take',true).onclick=openFiles;btn(RW.pc_new_one,'yes');
  r.querySelector('[data-m="yes"]').onclick=()=>pickRemind(el,x,'time');close();return}
 words(pc?RW.pc_ask:RW.ask);btn(RW.yes,'yes',true);btn(RW.no,'no');
 r.querySelector('[data-m="yes"]').onclick=()=>pickRemind(el,x,'time');   // always the times: each post gets its own (Nicole, Nov 10)
 r.querySelector('[data-m="no"]').onclick=()=>{RMODE[x.id]=null;pickRemind(el,x);const b=el.querySelector('[data-r]');if(b)b.setAttribute('aria-expanded','false')};
 close()}
function remindNote(el,x){const n=el.querySelector('.pn');if(!n)return;const M=RM();n.textContent='';   // ours: the calendar could not be updated, said plainly, with a way to try again
 if(!live||!M.way||!M.problem||M.busy)return;
 n.appendChild(mkel('span',null,(M.way==='file'?RW.pc_trouble:RW.trouble)+' '+M.problem));
 const b=mkel('button','btn o',RW.again);b.type='button';b.dataset.retry='';b.onclick=async()=>{n.textContent='';const S2=await post({action:'remind-sync'});if(S2)render(S2)};n.appendChild(b)}
// The calendar work runs in the background on the server: while a round is at work, ask how it went (a small
// answer, a few times a second at most), and put what it says into the open panel.
let RPOLL=null,RFAIL=0;
function watchRemind(){if(!live||RPOLL||!RM().busy)return;
 RPOLL=setTimeout(async()=>{RPOLL=null;
  try{const j=await fetch('/posting/reminding',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject());RFAIL=0;
   const was=JSON.stringify(LAST.reminding);LAST.reminding=j;if(JSON.stringify(j)!==was)redrawRemind()}
  catch(e){if(++RFAIL>20){LAST.reminding=Object.assign({},RM(),{busy:false});return}}
  watchRemind()},600)}
if(!live)$('#offline').hidden=false;render(D);
"""


def state(p):
    schedule(p)
    weeks, n = tank(p)
    def pub(x):
        d = {k: x.get(k) for k in ("id", "shoot_name", "kind", "status", "thumb", "date", "slot", "where", "n")}
        # for the post's panel (Nicole's v20 and v21): the photo they picked for the grid ("Photos/<file>" or
        # "Carousel/<file>", never a path), the kit's folder NAME (for the link to its words page), and whether
        # a click on its tile opens a panel (panel_role). And its reminder (Nicole's v21): on or off, and its
        # own time.
        d["remind_on"] = bool(x.get("remind_on"))
        d["remind_time"] = x.get("remind_time") if isinstance(x.get("remind_time"), str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", x["remind_time"]) else None
        d["cover"] = x.get("cover") if isinstance(x.get("cover"), str) else None
        d["folder"] = kit_folder(x) or None
        d["role"] = panel_role(x)
        if x["status"] == "yellow" and x.get("made_at"):
            d["days"] = (today() - date.fromisoformat(x["made_at"][:10])).days
        return d
    if n == 0:
        head = "Nothing ready to post <em>yet.</em>"
    elif weeks is None:
        head = f"{n} piece{'s' if n != 1 else ''} ready to <em>post.</em>"
    elif weeks < 1:
        d = max(1, round(weeks * 7))
        head = f"About {d} day{'s' if d != 1 else ''} of posts <em>ready.</em>"
    else:
        w = round(weeks, 1); w = int(w) if w == int(w) else w
        head = f"About {w} week{'s' if w != 1 else ''} of posts <em>ready.</em>"
    f = load_feed()
    feed = {"handle": f.get("handle"), "read_at": f.get("read_at"),
            "posts": [{k: x.get(k) for k in ("id", "kind", "pinned", "thumb")} for x in f["posts"] if (FEED_THUMBS / f"{x['id']}.jpg").exists()]}
    r = p.get("remind") if isinstance(p.get("remind"), dict) else {}
    remind = {k: r[k] for k in ("calendar", "time") if isinstance(r.get(k), str)}   # the calendar chosen, and the last time used (pre-fills the time box only)
    return {"today": today().isoformat(), "interval": p.get("interval"), "interval_words": interval_words(p.get("interval")),
            "remind": remind, "reminding": remind_state(),
            "weeks": weeks, "tank_head": head, "tank_line": tank_words(p), "feed": feed,
            "greens": [pub(x) for x in greens(p)],
            "yellows": [pub(x) for x in p["pieces"] if x["status"] == "yellow"],
            "reds": [pub(x) for x in p["pieces"] if x["status"] == "red"]}


def page_html(p):
    data = json.dumps(state(p)).replace("</", "<\\/")
    when = today().strftime("%A, %B ") + str(today().day)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(brand.title('Posting queue'))}</title><style>{look.head_css()}{CSS}</style></head><body>"
            f"<div class='wrap'><div class='bar'><a class='homelink' href='/home'><span aria-hidden='true'>&larr;</span><span class='long'>Back to home</span><span class='short'>Home</span></a>{brand.bar()}"
            f"<span class='when'>{html.escape(when)}</span></div>"
            "<header class='head'><span class='eyebrow'>Posting queue</span><h1 id='tankh'></h1><p class='lede' id='tankp'></p>"
            "<div class='tankbar' id='tankbar'><i></i></div><span class='rhythm' id='rhythm'></span>"
            "<p class='offline' id='offline' hidden>This is a saved copy. Ask Claude to “show my posting queue” to change things.</p></header>"
            "<section class='sec'><h2>Your Instagram grid, with your new posts in it</h2><p>Newest at the top, like Instagram. The outlined ones are your upcoming posts. Click one to pick the photo it shows. Drag one to a different spot to change the order; the dates update to match.</p>"
            "<p class='pickhint' id='pickhint' hidden>Click on a post to change the photo it shows in your grid, or to copy its caption.</p>"
            "<div class='grid' id='grid'></div><div class='pick' id='pick' hidden></div><p class='gridnote' id='gridnote'></p></section>"
            "<section class='sec'><h2>Ready to post</h2></section><ul class='list' id='greens'></ul>"
            "<section class='sec'><h2>Still finishing</h2><p>These are made but you're still working on them in CapCut or Canva. Press Ready when one is done.</p></section><ul class='list' id='yellows'></ul>"
            "<section class='sec'><h2>Not started</h2></section><ul class='list' id='reds'></ul>"
            "</div><div class='toast' id='toast'></div>"
            f"<script type='application/json' id='data'>{data}</script><script>{SCRIPT}</script></body></html>")


def write_page(p):
    write_whole(PAGE, page_html(p))
    return PAGE


def open_capcut(rec, ok_words=None, button="Open in CapCut"):
    """The kit page's "Open in CapCut" button. Starts CapCut through capcut.py (on a Mac its own `open -a`, as
    before; on a PC the CapCut program found where it installs itself), and says which project to click:
    CapCut can't be told to open a project from outside, so the words do that part. capcut.py also adds a reel
    that is still waiting for CapCut's list (one made while CapCut was open on a PC, or while the list couldn't
    be saved) when CapCut is surely closed, and its note about that is passed on. ok_words: the line to say when
    it opened, in place of the kit page's own (the reel page passes Nicole's, capcut.OPEN_WORDS). button: what the
    button pressed is called on that page, so a line that says to press it again names the button that is there
    (the reel page's is "Open CapCut")."""
    project = (rec.get("reel") or {}).get("project")
    if not project:
        return False, "The reel hasn't been made yet. Say “make the reel” to Claude."
    if not (this_computer.MAC or this_computer.WINDOWS):
        return False, "Opening CapCut only works on a Mac or a PC."
    capcut = _capcut()
    damaged = unsure = False
    with _CAPCUT_LOCK:                 # one press at a time: what capcut.py notes about a press is read before the next
        try:
            ok, why = capcut.open_capcut()
            # True when a reel was waiting but whether CapCut was open couldn't be told (on a PC, Windows' list of
            # running programs didn't answer): nothing was added, and pressing again would do the same
            unsure = bool(getattr(capcut.open_capcut, "unsure", False))
        except Exception as e:  # noqa: BLE001  (a damaged list of waiting reels must never leave the button without an answer)
            say(f"open CapCut: the list of reels waiting for CapCut couldn't be used ({e.__class__.__name__}); starting CapCut without it")
            damaged = True
            ok, why = capcut.launch()
            why = capcut.OPENED if ok else f"STOP: {why}."
        # True when the Mac's `open` was still waiting after capcut.py's 20 seconds: CapCut was asked to start and
        # may yet appear, so "couldn't open" would be wrong
        slow = bool(getattr(capcut.launch, "slow", False))
        missing = bool(getattr(capcut.launch, "missing", False))      # no CapCut found to start
    say(f"open CapCut: {'ok' if ok else 'no'}: {why}")
    if not ok:
        if slow:
            return False, (f"CapCut is taking a while to start on this {this_computer.COMPUTER}. Give it a moment, then "
                           f"click “{project}” in its project list (near the top, newest first).")
        if this_computer.MAC and missing:   # the words a Mac always gave when `open -a` found no CapCut
            return False, f"CapCut doesn't seem to be installed on this {this_computer.COMPUTER}. It's free from capcut.com."
        # it is there but didn't start, or a PC
        where = "the Start menu" if this_computer.WINDOWS else "your Applications folder"
        return False, (f"I couldn't open CapCut on this {this_computer.COMPUTER}. Open it from {where}, then click "
                       f"“{project}” in its project list (near the top, newest first). CapCut is free from capcut.com.")
    words = ok_words or f"CapCut is open. Click “{project}” in its project list (near the top, newest first), style it, and export it from there."
    base = capcut.OPENED                         # capcut.py's own words when it opened; anything after them is its note
    extra = why[len(base):].strip() if why.startswith(base) else ""
    if extra:                                    # the reel that was waiting is in its list now (or why it isn't)
        words += " " + extra
    if damaged:                                  # pressing again would meet the same damaged list: Claude sorts it out
        return True, words + " If it isn't in the list, tell Claude and it'll sort it out."
    try:
        waiting = capcut.waiting()               # still not in CapCut's list: CapCut was open (or it couldn't be told)
    except Exception:  # noqa: BLE001  (a hint, never a reason for the button to fail)
        waiting = []
    if waiting and not extra:
        if unsure:
            # pressing again would not help (this computer can't tell whether CapCut is open): Claude adds it with
            # `capcut.py open --closed` once they say CapCut is closed (parts/on-a-pc.md)
            words += f" If it isn't in the list, {capcut.QUIT} CapCut and tell Claude “add my waiting reel”."
        else:
            words += f" If it isn't in the list, {capcut.QUIT} CapCut and press {button} again, and I'll add it."
    return True, words


def _capcut():
    """capcut.py, from the reel scripts beside these. When it loads, capcut.py puts its own folder and this one at
    the front of Python's search list; the list is put back as it was straight after (anything new kept, at the
    end), so in a running page server a reel script can never stand in for a module imported later. No name is
    shared between the two folders today (checked Nov 6)."""
    if str(REEL_SCRIPTS) not in sys.path:
        sys.path.append(str(REEL_SCRIPTS))
    saved = list(sys.path)
    try:
        import capcut
    finally:
        sys.path[:] = saved + [x for x in sys.path if x not in saved]
    return capcut


def thumb_wanted(path):
    """Is this address (the path part, as sent) one small picture a page here shows, and nothing else? Checked
    after the address is decoded, part by part, the way Python's own server reads it: a folder named in
    THUMB_FOLDERS, then a picture's file name (or, for a queued shoot, its folder and a picture), each part a
    plain name: not empty, not starting with a dot (so never "." or ".."), no backslash, and on a PC no colon
    (another drive, or a hidden stream inside a file) and no word Windows keeps for a device (CON, NUL...). Never
    a folder, and never a link that leads out of its own folder.
    Before Nov 6 the check was for ".." in the address as sent, so "%2e%2e" (the same two dots, written the way
    addresses may write them) reached the Studio File and the queues, and "/feed/" listed the folder; and a kit
    named "Beach... sunset" had no pictures on the home page, since its name has two dots in a row."""
    try:
        decoded = unquote(path, errors="surrogatepass")    # exactly as SimpleHTTPRequestHandler.translate_path
    except UnicodeDecodeError:
        decoded = unquote(path)
    parts = decoded.split("/")
    if len(parts) < 3 or parts[0] != "" or parts[1] not in THUMB_FOLDERS:
        return False
    folder, rest = parts[1], parts[2:]
    if len(rest) > THUMB_FOLDERS[folder]:
        return False
    for x in rest:
        if not x or x.startswith(".") or "\\" in x or "\x00" in x:
            return False
        if this_computer.WINDOWS and (":" in x or this_computer.unreserved(x) != x):
            return False
    if Path(rest[-1]).suffix.lower() not in PICTURE_SUFFIXES:
        return False
    base = HOME / folder
    f = base.joinpath(*rest)
    try:
        if f.is_symlink() or f.exists():
            if not f.is_file():
                return False                                # a folder (or anything that isn't a file) is never served
            f.resolve().relative_to(base.resolve())         # and never anything outside its own folder
    except (OSError, ValueError):
        return False
    return True                                             # a picture that isn't there: Python's own "not found"


class Handler(SimpleHTTPRequestHandler):
    def ours(self):
        """Was this request sent to this server by its own name (127.0.0.1 or localhost, and this port)?
        Every page here is opened that way. A web page on another site that has been pointed at this computer by
        a trick of names still carries its own name in Host, and is refused before any route is looked at."""
        port = self.server.server_address[1]
        host = (self.headers.get("Host") or "").strip().lower()
        if host in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return True
        say(f"refused: a request for {urlsplit(self.path).path[:60]!r} named another host ({host[:80]!r})")
        self.send_error(HTTPStatus.FORBIDDEN)
        return False

    def do_HEAD(self):
        # only for the pictures a GET would serve (no page here asks for HEAD; before Nov 6 it told any file's size
        # and date in the Studio folder, and answered for a folder)
        if not self.ours():
            return
        if thumb_wanted(urlsplit(self.path).path):
            return super().do_HEAD()
        self.send_error(HTTPStatus.NOT_FOUND)

    def list_directory(self, path):
        """Never a folder's list of files (Python's own server makes one for a folder's address)."""
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def do_GET(self):
        if not self.ours():
            return
        path = urlsplit(self.path).path
        # (not while a reminders round is talking to Calendar: starting over mid-call would leave an event nobody
        # remembers making; the next page request starts over instead)
        if fresh.page_path(path) and fresh.stale() and _start_over(self):
            return
        if path == look.FONT_ROUTE:                     # the pages' font: the plugin's own DM Sans (look.py)
            return look.serve_font(self, urlsplit(self.path).query)
        if path in ("", "/"):
            # the bare address is the front door, the home page (it used to be the posting page)
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/home")
            self.end_headers()
            return
        if path == "/posting/panel":
            return self.posting_panel(urlsplit(self.path).query)
        if path == "/posting/calendars":
            return self.posting_calendars()
        if path == "/posting/reminding":
            if (self.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
                return self.answer({"ok": False}, HTTPStatus.FORBIDDEN)
            return self.answer(remind_state())
        if path == "/posting.html":
            remind_soon()          # a caption edited on the words page since: the reminder's notes follow (in the background)
            body = page_html(load()).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/home-state":
            import home
            body = home.fingerprint().encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/phone-setup":
            # the picture of where the Remote Control switch is, for a backup of more than one card (phone_setup.py)
            import phone_setup
            body = phone_setup.page_html().encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/home", "/home.html"):
            import home
            body = home.page_html().encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/design.html", "/design-state", "/design-font-file", "/design-preview"):
            # the carousel designer: every one of its requests is design.py's to answer
            import design
            return design.handle_get(self, path, urlsplit(self.path).query)
        if path in ("/arrange.html", "/arrange-state", "/kit-photo"):
            # the pages for arranging a kit's photos: every one of their requests is arrange.py's to answer
            import arrange
            return arrange.handle_get(self, path, urlsplit(self.path).query)
        if path in ("/reel.html", "/reel-state", "/reel-font", "/reel-job", "/reel-songs", "/reel-footage", "/reel-video",
                    "/reel-strip", "/reel-moment-still"):
            # the reel page (Nicole's reel maker): every one of its requests is reel_page.py's to answer
            import reel_page
            return reel_page.handle_get(self, path, urlsplit(self.path).query)
        if path in ("/words.html", "/words-state"):
            # the words page (Nicole's v20: captions and hooks): every one of its requests is words_page.py's to answer
            import words_page
            return words_page.handle_get(self, path, urlsplit(self.path).query)
        if path.startswith(("/posting-thumbs/", "/feed/", "/queue-thumbs/", "/home-thumbs/")):
            if thumb_wanted(path):                     # one small picture a page shows, nothing else (see thumb_wanted)
                return super().do_GET()
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if path.startswith("/content/"):
            # serve_content decodes the address and checks it part by part (never "." or ".."). The old check here,
            # for ".." anywhere in the address as sent, only kept out a kit named like "Beach... sunset" (Nov 6).
            return self.serve_content(path[len("/content/"):])
        if path == "/open":
            return self.open_kit_folder(urlsplit(self.path).query)
        if path == "/open-home":
            return self.open_home_folder()
        if path == "/open-drop":
            return self.open_home_folder(drop=True)
        if path == "/open-shoot":
            return self.open_shoot(urlsplit(self.path).query)
        if path == "/queue-url":
            return self.queue_url()
        if path == "/report-url":
            return self.report_url(urlsplit(self.path).query)
        if path == "/pick-folder":
            return self.pick_folder()
        self.send_error(HTTPStatus.NOT_FOUND)

    def answer(self, obj, code=HTTPStatus.OK):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(out)

    def posting_panel(self, query):
        """GET /posting/panel?id=<piece>: what an upcoming post's panel draws from (panel_for). Asked by the
        posting page only: this server's own name in Host (checked for every GET), and never for a page of
        another website. Whatever goes wrong, an answer, and the server stays up."""
        if (self.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return self.answer({"ok": False}, HTTPStatus.FORBIDDEN)
        try:
            ids = parse_qs(query or "", keep_blank_values=True).get("id") or [""]
            pid = ids[0]
            out = panel_for(pid) if 0 < len(pid) <= 200 else None
        except (Exception, SystemExit) as e:  # noqa: BLE001
            say(f"posting panel: couldn't answer ({e.__class__.__name__}: {str(e)[:160]})")
            return self.answer({"ok": False}, HTTPStatus.INTERNAL_SERVER_ERROR)
        if out is None:
            return self.answer({"ok": False}, HTTPStatus.NOT_FOUND)
        return self.answer(out)

    def posting_calendars(self):
        """GET /posting/calendars: {ok, calendars: [names]} for "Which calendar does your phone show?", or
        {ok: False, problem: plain words}. Asked of the calendar right now: about a second on a Mac, and as long
        as macOS waits for an answer to its permission question (two minutes at most). This server answers
        every request on a thread of its own, so nothing else on the page waits for it."""
        if (self.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return self.answer({"ok": False}, HTTPStatus.FORBIDDEN)
        import reminders as posting_reminders
        try:
            names = calendar_names(fresh_within=3.0)
        except posting_reminders.CalendarProblem as e:
            return self.answer({"ok": False, "problem": str(e)[:200]})
        except Exception as e:  # noqa: BLE001
            say(f"posting calendars: couldn't answer ({e.__class__.__name__}: {str(e)[:160]})")
            return self.answer({"ok": False, "problem": ""})
        if not names:
            return self.answer({"ok": False, "problem": "No calendar a reminder could go on was found."})
        return self.answer({"ok": True, "calendars": names})

    def open_home_folder(self, drop=False):
        """The home page's "Open my Studio folder": The Studio folder itself (Drop a shoot here and Content),
        or, with drop, the Drop a shoot here folder inside it (the button in the Make posts steps)."""
        import finder
        import posts
        h = posts.home()
        if not h or not h.is_dir():
            return self.answer({"ok": False, "words": f"There's no {posts.HOME_NAME} folder yet. Ask Claude to set one up, or plug in the drive it lives on."})
        if drop:
            h = h / posts.DROP_NAME
            h.mkdir(exist_ok=True)
        ok, why = finder.open_folder(h)
        app = this_computer.FILES_APP   # "Finder" on a Mac, "File Explorer" on a PC
        words = (f"Opened {h.name} in {app}, behind this window. Click {app} in {this_computer.APP_BAR} to see it." if why == "behind"
                 else f"Opened {h.name} in {app}.") if ok else f"Couldn't open {app}. The folder is {h}."
        self.answer({"ok": ok, "words": words})

    def open_shoot(self, query):
        """The home page's "Open photo folder" on a recent shoot: the same lookup the queue page uses."""
        from urllib.parse import parse_qs
        import edit_queue
        sid = parse_qs(query).get("id", [""])[0]
        try:
            s = next((x for x in edit_queue.load()["shoots"] if x["id"] == sid), None)  # only a shoot's own folder, never a path from the page
            ok, words = edit_queue.open_folder(s) if s else (False, "I don't know that shoot.")
        except Exception as e:  # noqa: BLE001
            ok, words = False, f"Couldn't open it ({e.__class__.__name__}). Ask Claude."
        self.answer({"ok": ok, "words": words})

    def report_url(self, query):
        """The home page's "See the report": the report of the backup a shoot came from, its server started if
        it isn't up. Only by a shoot's id, never a path from the page."""
        from urllib.parse import parse_qs
        import edit_queue
        q = parse_qs(query)
        sid = q.get("id", [""])[0]
        try:
            shoots = edit_queue.load()["shoots"]
            if sid == "latest":
                with_report = [x for x in shoots if x.get("studio")]
                s = max(with_report, key=lambda x: x.get("added", "")) if with_report else None
            else:
                s = next((x for x in shoots if x["id"] == sid), None)
            if not s or not s.get("studio"):
                return self.answer({"ok": False, "words": "There's no report for this one. It didn't come from a backup."})
            studio = Path(s["studio"])
            if not studio.is_dir():
                drive = this_computer.drive_words(studio) or "the drive"   # "Big Kahuna"; on a PC "the drive that was E:"
                return self.answer({"ok": False, "words": f"Plug in {drive} to see this report."})
            import serve_report
            url = serve_report.report_url(studio)
            if not url:
                return self.answer({"ok": False, "words": "Couldn't open the report. Say \"show me the report\" and Claude will."})
            # always the top of the report (Dustin, Nov 5: jumping to the shoot's name box opened it "scrolled
            # half way down the page", which read as a glitch)
            return self.answer({"ok": True, "url": url})
        except Exception as e:  # noqa: BLE001
            return self.answer({"ok": False, "words": f"Couldn't open the report ({e.__class__.__name__}). Say \"show me the report\" and Claude will."})

    def pick_folder(self):
        """The home page's "Choose the folder your finished photos are in": the computer's own folder picker
        (this_computer.pick_folder: the Mac's choose folder, as before; on a PC Windows' own folder window), then
        posts.py bring copies only the finished photos into the drop box. The originals are never moved.
        A PC is never told to drag the folder in: there, as on a Mac, a folder dragged within one drive is moved."""
        import posts
        h = posts.home()
        if not h or not h.is_dir():
            return self.answer({"ok": False, "words": f"There's no {posts.HOME_NAME} folder yet. Ask Claude to set one up."})
        if not (this_computer.MAC or this_computer.WINDOWS):
            return self.answer({"ok": False, "words": "Drag the folder of finished photos into Drop a shoot here instead."})
        if this_computer.WINDOWS:
            no_window = ("The folder window didn't open. Tell Claude which folder your finished photos are in (you can copy its "
                         f"address from the top of its {this_computer.FILES_APP} window), and it'll copy the photos for you.")
        else:
            no_window = f"The folder window didn't open. Drag the folder into Drop a shoot here instead (hold the {this_computer.COPY_KEY} key so it copies)."
        folder, why = this_computer.pick_folder("Pick the folder your finished photos are in. The Assistant copies the photos; nothing is moved.")
        if not folder:
            return self.answer({"ok": False, "words": "No folder chosen." if why == "cancelled" else no_window})
        got = posts.bring(h, folder)
        if not got:
            return self.answer({"ok": False, "words": "Something stopped the copy. Tell Claude and it'll sort it out."})
        copied, skipped, dest = got
        left = ", ".join(posts.plural(n, k) for k, n in sorted(skipped.items()))
        label = Path(folder).name
        if not label and this_computer.WINDOWS:     # the top of a drive ("E:\") has no name of its own: say "E:"
            label = folder.rstrip("\\/")
        words = (f"Copied {copied} finished photo{'s' if copied != 1 else ''} from {label}. Your originals weren't moved." if copied
                 else f"No finished photos (JPEGs) in {label}.") + (f" Left behind: {left}." if left else "")
        say(f"pick-folder: {folder} -> {copied} copied, skipped {skipped}")
        self.answer({"ok": bool(copied), "words": words, "copied": copied})

    def queue_url(self):
        """The live editing-queue page's address, starting its server if needed (serve_report has the logic)."""
        import serve_report
        u = serve_report.queue_url()
        self.answer({"url": u, "words": None if u else "Ask Claude: show my editing queue"})

    def open_kit_folder(self, query):
        """A kit page's "Open the ... folder" button: only a kit in Content, or one of its own folders
        (Photos may live elsewhere when the kit points at a Lightroom export folder)."""
        from urllib.parse import parse_qs
        import finder
        import posts
        import kit as kit_mod
        q = parse_qs(query)
        kit_name, sub = q.get("kit", [""])[0], q.get("sub", [""])[0]
        h = posts.home()
        ok, words = False, "That isn't a folder this kit names."
        content = (h / posts.CONTENT_NAME).resolve() if h else None
        # A kit is one folder's name inside Your Content, so it is checked as text before any path is made from it:
        # no slash (on a PC "//computer/share" would be another computer's shared folder, and asking Windows about
        # it, which resolve() does, reaches out to that computer before anything here could refuse it), no name
        # starting with a dot (never a kit; "." and ".." are folders around it). On a PC also no backslash, no
        # colon (another drive, or a hidden stream inside a file) and no word Windows keeps for a device (CON...).
        # ".." inside a name is fine: a kit named like "Beach... sunset" has two dots in a row (its buttons did
        # nothing before Nov 6), and the folder-by-folder check below keeps everything inside Your Content.
        named = (kit_name and "\x00" not in kit_name and "/" not in kit_name and not kit_name.startswith(".")
                 and not (this_computer.WINDOWS and ("\\" in kit_name or ":" in kit_name
                                                     or this_computer.unreserved(kit_name) != kit_name)))
        try:
            kd = (content / kit_name).resolve() if content and named else None
        except (OSError, ValueError):      # a name a PC can't even look up (a stray ? or *): not a kit
            kd = None
        # inside Your Content, folder by folder: a text match let "Your Content old/..." beside it through (both
        # computers); a path compare also ignores upper and lower case and the kind of slash on a PC
        if kd and content in kd.parents and kd.is_dir():
            if sub == "CapCut":
                # her words on both pages (decision 24); the kit page's own button now goes through /reel-capcut
                ok, words = open_capcut(kit_mod.load_rec(kd), ok_words=_capcut().OPEN_WORDS)
                target = None
            elif sub == "":
                target = kd
            elif sub == "Photos":
                target = kit_mod.photos_dir(kd)
            elif sub in ("Singles", "Carousel", "Stories", "Covers"):
                target = kd / sub
            else:
                target = None
            if target is None:
                pass
            elif not target.is_dir():
                ok, words = False, f"There's no {sub or 'kit'} folder yet." if sub != "Photos" else "The photos folder isn't there right now. Is the drive plugged in?"
            else:
                ok, why = finder.open_folder(target)
                name = target.name
                app = this_computer.FILES_APP   # "Finder" on a Mac, "File Explorer" on a PC
                words = (f"Opened {name} in {app}, behind this window. Click {app} in {this_computer.APP_BAR} to see it." if why == "behind"
                         else f"Opened {name} in {app}.") if ok else f"Couldn't open {app}. The folder is {target}. ({why})"
        elif h is None or not content.is_dir():
            words = f"The {posts.HOME_NAME} folder isn't there right now. Is the drive plugged in?"
        say(f"open asked: {kit_name} / {sub or '(kit)'} -> {'ok' if ok else 'no'}: {words}")
        out = json.dumps({"ok": ok, "words": words}).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(out)

    def serve_content(self, rel):
        """A post kit's page and its pieces, read-only, from Your Content (kit.py), so the kit page opens in
        the app's browser pane like the report does. Only what the kit page shows is served:
            <kit>/Post kit.html, Reel.txt                            (kept in the kit's hidden folder)
            <kit>/Singles|Carousel|Stories|Covers/<a picture>          (the pieces the Assistant made)
        Never the kit's records (they hold folder paths), never the photos themselves, never anything whose
        name starts with a dot, and never anything outside Your Content (the address is decoded first, then
        checked part by part; the file's real place is checked against Your Content's real place)."""
        import mimetypes
        from urllib.parse import unquote
        try:
            import posts
            h = posts.home()
        except Exception:
            h = None
        parts = unquote(rel).split("/")
        ok = bool(h) and len(parts) in (2, 3) and all(x and not x.startswith(".") and "\\" not in x and "\x00" not in x for x in parts)
        if ok and this_computer.WINDOWS:
            # no real name on a PC has a colon in it; one would mean another drive, or a hidden stream inside a
            # file (Microsoft, "Naming Files, Paths, and Namespaces"). Unproven on a real PC.
            ok = not any(":" in x for x in parts)
        if ok and len(parts) == 2:
            ok = parts[1] in KIT_OWN_FILES
        elif ok:
            ok = parts[1] in KIT_PIECE_FOLDERS and Path(parts[2]).suffix.lower() in (".jpg", ".jpeg", ".png")
        if not ok:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if parts[1] == "Post kit.html":
            return self.serve_kit_page(parts[0])
        content = h / posts.CONTENT_NAME
        kit = content / parts[0]
        f = kit.joinpath(*parts[1:])
        if len(parts) == 2 and not f.is_file():
            # The Assistant's own files live in the kit's hidden folder (Oct 30); the page's address stays
            # /content/<kit>/Post kit.html so its pictures (Carousel/..., Singles/...) still resolve beside it.
            f = kit / ".kit" / parts[1]
        try:
            inside = not kit.is_symlink() and f.is_file()
            if inside:
                f.resolve().relative_to(content.resolve())
        except (OSError, ValueError):
            inside = False
        if not inside:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        data = f.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_kit_page(self, name):
        """The kit page, built from the kit's records and folders on every request (kit.build_page: Nicole's three
        cards), so it always shows what is made now. The kit is found only by its exact name in Your Content's own
        listing (arrange.kit_by_name: a real folder, not a link, holding a kit record). When it can't be reached
        (the drive unplugged, or no such kit) her page says so, with her one line, and the answer is "not found".
        Should the page fail to build, the copy kit.py last saved is sent instead, but only one of today's page
        (kit.PAGE_MARK); a copy from before her three cards is never passed off as current, and the page says in one
        line that something couldn't be read and to tell Claude."""
        import arrange
        import kit as kit_mod
        kit = arrange.kit_by_name(name)
        body, code = None, HTTPStatus.OK
        if kit is None:
            body, code = kit_mod.unreachable_html(), HTTPStatus.NOT_FOUND
        else:
            try:
                body, need = kit_mod.build_page(kit)
                if need:
                    arrange.start_previews(kit)        # a reel photo on the card has no small copy yet: made in the background
            except Exception as e:  # noqa: BLE001
                try:
                    body = kit_mod.page_path(kit).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    body = None
                if body is None or kit_mod.PAGE_MARK not in body:
                    # no saved copy, or one from before her three cards: an old page would look current and isn't
                    say(f"kit page: couldn't build {name!r} ({e.__class__.__name__}: {str(e)[:160]}); no saved copy of today's page, so saying so")
                    body, code = kit_mod.unreachable_html(kit_mod.OUR_KIT_WORDS["cant_build"]), HTTPStatus.INTERNAL_SERVER_ERROR
                else:
                    say(f"kit page: couldn't build {name!r} ({e.__class__.__name__}: {str(e)[:160]}); sending the saved copy")
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def cors(self):
        """Only the grab script, running on instagram.com in their own browser, may talk to /feed from another origin."""
        origin = self.headers.get("Origin", "")
        if origin in FEED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        if not self.ours():
            return
        if urlsplit(self.path).path == "/feed":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.cors()
            self.send_header("Access-Control-Allow-Methods", "POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path in ("/design", "/design-new", "/design-template", "/design-brand", "/design-font", "/design-slide", "/design-commit",
                    "/design-preview"):
            # the carousel designer: design.py checks each of these the way arrange.py does (below)
            import design
            return design.handle_post(self, path, urlsplit(self.path).query)
        if path == "/arrange":
            # the pages for arranging a kit's photos. arrange.py checks the Host itself (and the type and the
            # size), reads a refused body away, and answers in the page's own words.
            import arrange
            return arrange.handle_post(self, path, urlsplit(self.path).query)
        if path in ("/reel-save", "/reel-open", "/reel-make", "/reel-capcut", "/reel-moment"):
            # the reel page: reel_page.py checks each of these the way arrange.py does (above)
            import reel_page
            return reel_page.handle_post(self, path, urlsplit(self.path).query)
        if path in ("/words-save", "/words-carry", "/words-rhythm", "/words-queue", "/words-open"):
            # the words page: words_page.py checks each of these the way arrange.py does (above)
            import words_page
            return words_page.handle_post(self, path, urlsplit(self.path).query)
        if not self.ours():
            return
        if path == "/feed":
            return self.post_feed()
        if path == "/clicked":
            import home
            try:
                n = int(self.headers.get("Content-Length", "0"))
                item = json.loads(self.rfile.read(n) or b"{}").get("item")
                with _CLICK_LOCK:          # two clicks at once: the second reads the record the first saved
                    ok = home.record_click(item)
            except (ValueError, TypeError, AttributeError):
                ok = False
            except OSError as e:           # the record couldn't be saved: an answer all the same
                say(f"clicked: couldn't save the record ({e.__class__.__name__})")
                ok = False
            return self.answer({"ok": ok})
        if path != "/posting":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        # A press on the posting page comes from the posting page: an Origin, when the browser sends one, is this
        # server's own, and the press is never another website's (the pickers' rule, arrange.guard). Before
        # Nov 11 only the Host was looked at here.
        port = self.server.server_address[1]
        origin = self.headers.get("Origin")
        if ((origin is not None and origin.strip().lower() not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"))
                or (self.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"):
            say(f"refused: a press on the posting page from another page ({str(origin)[:80]!r})")
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 <= n <= POST_CAP:
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("not a press")
            cover = None
            if body.get("action") == "cover":
                # the grid photo picker: the tile is made here, before the lock (cover_tile checks everything)
                pid, rel = body.get("id"), body.get("rel")
                if not isinstance(pid, str) or not isinstance(rel, str):
                    raise ValueError("not a press")
                cover = (pid, rel, cover_tile(pid, rel))
            act = body.get("action")
            more, names = {}, None
            if act in REMIND_ACTS:
                import reminders as posting_reminders
                if act == "remind-calendar":
                    # the list is read (or the one just shown is taken) BEFORE the lock: Calendar can take seconds
                    if not isinstance(body.get("calendar"), str):
                        raise ValueError("no such calendar")
                    try:
                        names = calendar_names(fresh_within=600.0)
                    except posting_reminders.CalendarProblem:
                        raise ValueError("no such calendar")
                elif act == "remind":
                    if not isinstance(body.get("id"), str) or not (body.get("time") is None or isinstance(body.get("time"), str)):
                        raise ValueError("not a press")
                elif act == "remind-open":
                    # a PC: open the calendar files that are waiting, in their calendar app. Not under the lock.
                    got = posting_reminders.open_waiting(remind_backend())
                    more = {"opened": len(got.get("opened") or []), "open_problem": got.get("problem") or None}
                    if got.get("detail"):
                        _remind_log(got["detail"])       # the real words (they may name a file) stay in the log
                elif act == "remind-sync":
                    remind_soon()      # "Try again", and a command asking this server to do the calendar work
            with _POSTING_LOCK:            # two presses at once: the second reads the queue the first saved
                p = load()
                if act in ("remind-open", "remind-sync"):
                    out = json.dumps(dict(state(p), **more)).encode()
                    p = None
                elif act in ("ready", "unready", "posted", "skip"):
                    x = next(y for y in p["pieces"] if y["id"] == body.get("id"))
                    set_status(p, x, {"ready": "green", "unready": "yellow", "posted": "posted", "skip": "skipped"}[act], by="page")
                elif act == "cover":
                    # the photo this post shows in the grid (Nicole's v20). A reel's pick is the cover to choose when
                    # posting; a carousel's only matches the real grid when it is the first slide (the page says so).
                    x = next(y for y in p["pieces"] if y["id"] == cover[0])
                    if x.get("status") != "green":
                        raise ValueError("not an upcoming post")     # it stopped being one while the tile was made
                    x["thumb"], x["cover"] = cover[2], cover[1]
                elif act == "remind":
                    # a post's reminder on (at its own time) or off (time: null). Nothing here talks to the
                    # calendar: the save below starts a round in the background.
                    posting_reminders.set_reminder(p, body["id"], body.get("time"))
                elif act == "remind-calendar":
                    posting_reminders.set_calendar(p, body["calendar"], backend=_Known(names))
                elif act == "order":
                    ids = [str(i) for i in body.get("ids", [])]
                    g = {x["id"]: x for x in greens(p)}
                    for i, pid in enumerate([i for i in ids if i in g], 1):
                        g[pid]["slot"] = i
                    renumber(p)
                    schedule(p, reflow=True)
                else:
                    raise ValueError(act)
                if p is not None:
                    schedule(p)
                    save(p)            # (in the page server every save is followed by a reminders round, in the background)
                    write_page(p)
                    out = json.dumps(state(p)).encode()
        except (StopIteration, ValueError, TypeError) as e:
            self.send_error(HTTPStatus.BAD_REQUEST, str(e)[:200])
            return
        except OSError as e:
            # the queue couldn't be saved (on a PC, another program held it longer than a few seconds; a full disk):
            # an answer all the same, never a dropped connection. The page says to tell Claude.
            say(f"posting: couldn't save the posting queue ({e.__class__.__name__}: {str(e)[:160]})")
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "The posting queue couldn't be saved just now")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def post_feed(self):
        """The grab script's delivery: {handle, tiles:[...]}. Up to about 4 MB of small jpegs."""
        out, code = {}, HTTPStatus.OK
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 6_000_000:
                raise ValueError("too big")
            body = json.loads(self.rfile.read(n) or b"{}")
            f = import_feed(body.get("tiles"), handle=body.get("handle"))
            write_page(load())
            out = {"ok": True, "posts": len(f["posts"]), "handle": f.get("handle")}
        except (ValueError, TypeError, KeyError, AttributeError) as e:   # AttributeError: a body that isn't {handle, tiles}
            out, code = {"ok": False, "error": "nothing usable in what the page sent"}, HTTPStatus.BAD_REQUEST
            say(f"(feed refused: {str(e)[:300]})")         # long enough for curl's reason when no picture came in
        data = json.dumps(out).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


def serve(port):
    global _SERVING
    if os.environ.get("REMINDERS_BACKEND", "").strip().lower() == "pretend":
        import reminders as posting_reminders
        if posting_reminders.pretend_config() is None:     # a test's switch, refused anywhere but a test's own folder
            sys.exit("STOP: " + posting_reminders.PRETEND_ONLY)
    HOME.mkdir(parents=True, exist_ok=True)
    _SERVING = True
    for pt in range(port, port + 20):
        try:
            # fresh.Server: Python's own server on a Mac, exactly as before; on a PC one that never shares its
            # port with another server (Windows would let two listen on 8790 and answer from either).
            srv = fresh.Server(("127.0.0.1", pt), partial(Handler, directory=str(HOME)))
            break
        except OSError:
            continue
    else:
        sys.exit(f"STOP: no free port between {port} and {port + 19}.")
    url = f"http://127.0.0.1:{pt}/posting.html"
    (HOME / "posting-url.txt").write_text(url, encoding="utf-8")
    print(f"Posting queue: {url}", flush=True)
    # A reminder changed just before this server came up (a press in the moment the last one was starting over,
    # a command with no server to ask) is brought into step now. Nothing to change: Calendar is never asked.
    remind_soon()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------- status changes ----------

def set_status(p, x, status, by="claude", where=None):
    old = x["status"]
    x["status"] = status
    if status == "yellow":
        x.setdefault("made_at", now())
        if where:
            x["where"] = where
        x.pop("slot", None); x.pop("date", None)
    elif status == "green":
        x["green_at"] = now()
        if "slot" not in x or old != "green":
            x["slot"] = max((y.get("slot", 0) for y in p["pieces"] if y["status"] == "green" and y is not x), default=0) + 1
    elif status == "posted":
        x["posted_at"] = now()
        x.pop("slot", None)
    elif status in ("red", "skipped"):
        x.pop("slot", None); x.pop("date", None)
    x["changed_by"] = by
    renumber(p)
    schedule(p)


def show(p):
    schedule(p)
    say(tank_words(p))
    g = greens(p)
    if g:
        say("Ready to post, in order:")
        for x in g:
            say(f"  {x['slot']}. {piece_name(x)}" + (f", {nice_day(x['date'])}" if x.get("date") else ""))
    y = [x for x in p["pieces"] if x["status"] == "yellow"]
    if y:
        say("In progress:")
        for x in y:
            days = (today() - date.fromisoformat(x["made_at"][:10])).days if x.get("made_at") else None
            say(f"  {piece_name(x)}" + (f" ({x['where']})" if x.get("where") else "") + (f", {days} days" if days is not None else ""))
    r = [x for x in p["pieces"] if x["status"] == "red"]
    if r:
        say("Not started: " + ", ".join(piece_name(x) for x in r))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("interval"); i.add_argument("text", nargs="?")
    a_ = sub.add_parser("add"); a_.add_argument("--shoot"); a_.add_argument("--kit"); a_.add_argument("--kinds", default="reel,carousel")
    m = sub.add_parser("made"); m.add_argument("piece"); m.add_argument("--where")
    for c in ("ready", "unready", "posted", "skip"):
        sub.add_parser(c).add_argument("piece")
    mv = sub.add_parser("move"); mv.add_argument("piece"); mv.add_argument("--to", type=int, required=True)
    sub.add_parser("list"); sub.add_parser("tank"); sub.add_parser("page")
    r = sub.add_parser("reminders"); r.add_argument("--mark", action="store_true")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8790)
    sub.add_parser("remind-sync")      # the helper calendar_in_step starts: one reminders round, to its end
    fd = sub.add_parser("feed"); fd.add_argument("--handle"); fd.add_argument("--import", dest="import_file"); fd.add_argument("--clear", action="store_true")
    gs = sub.add_parser("grab-script"); gs.add_argument("--port", type=int)
    a = ap.parse_args()
    if a.cmd == "remind-sync":
        res = remind_once(wait=REMIND_WAIT)
        for line in res.get("did") or []:
            say(line)
        if res.get("note"):
            say(res["note"])
        return 1 if res.get("problem") else 0
    p = load()

    if a.cmd == "feed":
        f = load_feed()
        if a.clear:
            for p_ in FEED_THUMBS.glob("*.jpg"):
                (FEED_THUMBS / "older").mkdir(parents=True, exist_ok=True)
                this_computer.replace(p_, FEED_THUMBS / "older" / p_.name)
            save_feed({"handle": a.handle or f.get("handle"), "read_at": None, "posts": []})
            write_page(p)
            say("Forgot your grid. The page shows placeholders again until it's read once more.")
            return 0
        if a.import_file:
            try:
                # read as bytes: json finds UTF-8, UTF-8 with a byte-order mark, and UTF-16 or -32 by itself (a list
                # saved on a PC through Windows PowerShell's ">" is UTF-16 with a mark)
                body = json.loads(Path(a.import_file).read_bytes())
                if isinstance(body, str):
                    # the browser pane's javascript tool hands the snippet's text back as one quoted string; saved
                    # exactly as it came, that string is the list, so it is read once more
                    body = json.loads(body)
            except FileNotFoundError:
                say(f"STOP: there's no file at {a.import_file}. Nothing changed.")
                return 1
            except (OSError, ValueError) as e:
                say(f"STOP: that file isn't the list the snippet returned ({e.__class__.__name__}). Nothing changed.")
                return 1
            tiles = body.get("tiles") if isinstance(body, dict) else body
            try:
                f = import_feed(tiles, handle=a.handle or (body.get("handle") if isinstance(body, dict) else None))
            except ValueError as e:
                say(f"STOP: nothing usable in that file ({e}).")
                return 1
            write_page(p)
            say(feed_words(f))
            return 0
        if a.handle:
            f["handle"] = a.handle.lstrip("@")
            save_feed(f)
            say(f"Your Instagram is @{f['handle']}. " + feed_words(f))
            return 0
        say(feed_words(f))
        return 0
    if a.cmd == "grab-script":
        say(grab_script(a.port))
        return 0

    if a.cmd == "interval":
        if not a.text:
            say(interval_words(p.get("interval")))
            return 0
        v = parse_interval(a.text)
        if v is None:
            say(f"STOP: I couldn't turn \"{a.text}\" into a rhythm. Try \"3 a week\", \"every other day\", or \"daily\".")
            return 1
        p["interval"] = v
        schedule(p, reflow=True); save(p); write_page(p)
        say(f"Posting {interval_words(v)}. " + tank_words(p))
        calendar_in_step()
        return 0
    if a.cmd == "add" and a.kit:
        import kit as kit_mod
        kd = kit_mod.find_kit(a.kit)
        pieces = add_for_kit(p, kd)
        schedule(p); save(p); write_page(p)
        say(f"{pieces[0]['shoot_name']}: {len(pieces)} pieces in the posting queue (" + ", ".join(f"{x['kind']}{' ' + str(x['n']) if x.get('n') else ''}: {x['status']}" for x in pieces) + ").")
        calendar_in_step()
        return 0
    if a.cmd == "add":
        if not a.shoot:
            say("STOP: say which (--shoot <words> or --kit <words>).")
            return 1
        shoot = queue_shoot(a.shoot)
        kinds = [k.strip() for k in a.kinds.split(",") if k.strip() in KINDS]
        made = add_for_shoot(p, shoot, kinds)
        save(p); write_page(p)
        say(f"{shoot['name']}: {len(made)} piece{'s' if len(made) != 1 else ''} waiting to be made ({', '.join(kinds)})." if made else f"{shoot['name']} is already in the posting queue.")
        return 0
    if a.cmd == "made":
        x = find(p, a.piece)
        set_status(p, x, "yellow", where=a.where)
        save(p); write_page(p)
        say(f"{piece_name(x)}: in progress. Say \"the {piece_name(x)} is ready\" when it's finished.")
        calendar_in_step()
        return 0
    if a.cmd in ("ready", "unready", "posted", "skip"):
        x = find(p, a.piece)
        set_status(p, x, {"ready": "green", "unready": "yellow", "posted": "posted", "skip": "skipped"}[a.cmd])
        save(p); write_page(p)
        if a.cmd == "ready":
            say(f"{piece_name(x)}: ready to post" + (f", down for {nice_day(x['date'])}" if x.get("date") else "") + ". " + tank_words(p))
        elif a.cmd == "posted":
            say(f"{piece_name(x)}: posted. " + tank_words(p))
        else:
            say(f"{piece_name(x)}: {'back to in progress' if a.cmd == 'unready' else 'skipped'}.")
        calendar_in_step()
        return 0
    if a.cmd == "move":
        x = find(p, a.piece, statuses=("green",))
        g = greens(p); g.remove(x); g.insert(max(0, min(a.to - 1, len(g))), x)
        for i, y in enumerate(g, 1):
            y["slot"] = i
        schedule(p, reflow=True); save(p); write_page(p)
        say(f"{piece_name(x)} is now {x['slot']} in line, down for {nice_day(x['date'])}." if x.get("date") else f"{piece_name(x)} is now {x['slot']} in line.")
        calendar_in_step()
        return 0
    if a.cmd == "list":
        show(p); return 0
    if a.cmd == "tank":
        schedule(p); say(tank_words(p)); return 0
    if a.cmd == "reminders":
        schedule(p)
        for line in reminders(p, a.mark):
            say(line)
        if a.mark:
            save(p)
        return 0
    if a.cmd == "page":
        say(str(write_page(p))); return 0
    if a.cmd != "serve":
        fresh.announce()
    if a.cmd == "serve":
        serve(a.port); return 0


if __name__ == "__main__":
    sys.exit(main())
