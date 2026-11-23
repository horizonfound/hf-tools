#!/usr/bin/env python3
"""Bring reels and talking reels made on the older pages into each shoot's post kit (Nov 18).

Before the Assistant's own reel page and talking reel page, a prototype page server kept each shoot's reel at
    <the Assistant folder>/.studio/reel-pages/<shoot folder name>.json
and its talking reel at
    <the Assistant folder>/.studio/talking/<shoot folder name>.json
(the photos' numbers in <...>/.studio/cache/photos/<mark of the shoot's name>/photos.json). Our pages read
<kit>/.kit/reel-page.json (reel_page.py) and <kit>/.kit/talking.json + talking-words.json (talking_rec.py), so
those reels show empty. This brings them over.

    bring_older.py look  [--from "<the old .studio folder>"] [--shoot "<words>"] [--photos-unchanged]
    bring_older.py bring [--from ...] [--shoot ...] [--photos-unchanged --names-confirmed]

`look` changes NOTHING: it says, shoot by shoot, which post kit it matched, each reel and talking reel it found,
every photo number with the photo it means in the older record and the number it carries here, and whatever it
cannot bring. `bring` does it. Default --from: the ".studio" folder beside Your Content.

The rules (each has a check in tests/bring_older_check.py):
  * The older records are only ever READ. Nothing there is moved, renamed or changed.
  * Nothing of ours is written over. A kit with no reel yet: the older reels become its reels. A kit that has
    reels already: the older ones are ADDED as further reels under their own names (a name that is taken gets
    " (older)" after it); the reel that was open stays open, and nothing in it changes. A reel here with
    nothing of theirs in it (the page was only opened) counts as no reel. The version before any record we
    change is kept the way that record's own writer keeps it (reel-page.prev.json, talking.prev.json,
    talking-words.prev.json), under the same locks the pages' writers hold. A reel record here that is there
    but can't be read (the drive, or a file cut short) is never taken for "no reel": that shoot's reels stop.
  * A reel keeps the id it had on the older pages (v1, v2...) whenever that id is free here or the reel here
    under it holds nothing, because a post in the posting queue says which reel it is by that id
    ("...-reel-v2"). When the id is taken by a reel of theirs, the older reel gets a new one, and look and
    bring say which queued post to check.
  * Photo numbers are never copied across. The older pages numbered photos their own way (JPEGs only; name
    order with capitals first on a first look; from Nov 14 a photo added later went at the END, and before
    that the photos were numbered again from 1 by name); ours are fixed once given and may have gaps. Each
    older number is turned into a FILE NAME by the older page's own numbered list (photos.json), then into our
    number by that name in the kit's sheet.json. When that older list is not there, name order is NOT proof
    (it is wrong as soon as a photo was ever added there): it is shown by `look --photos-unchanged` only so the
    photo names can be read back to the photographer, and `bring` uses it only with --names-confirmed, their
    own yes that those are each reel's photos. A reel with ANY photo that can't be proven is not brought, and
    the line says which photo and why; the other reels carry on. Nothing is guessed.
  * Every field goes through the same checks a save from our own page goes through (reel_page.SAVE_FIELDS,
    talking_rec.SAVE_FIELDS). One that doesn't pass is left out and named; nothing is invented.
  * A talking reel is brought only when its video is in the shoot's Talking folder now and nothing says it was
    saved again since its script was made: the script is then tied to that file by OUR key for it (video.key).
  * The first reel's pick of the Assistant's lives in kit.json (reel_page.assistant_pick). It is written there
    only through kit.py's own `picks --reel`, and only when the kit has no reel pick at all. A kit that already
    has a different pick keeps it: the older order then comes over as the photographer's own order, so the page
    shows what the older page showed.
  * Safe to run twice: each reel brought carries where it came from ("brought_from": the older file's NAME and
    the reel's id there, never a path), and one that is here already is skipped. What is about to be written is
    noted in <kit>/.kit/brought-older.json before any record changes (a kit whose photos have no numbers yet
    is numbered before that, by kit.py's own sheet); a run cut off part way is finished by the next.

Exit 0: done, or nothing to do. 1: something could not be brought. 2: stop (no older folder, no such shoot).

Python 3.9, standard library only. Nothing here is Mac-only (the small copy a talking reel's player shows is
made by video.py, which says so itself on a PC).
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
this_computer.utf8_output()
import arrange          # noqa: E402
import kit as kit_mod   # noqa: E402
import posts            # noqa: E402
import reel_page        # noqa: E402
import reels            # noqa: E402
import talking_rec as TR  # noqa: E402

OLD_NAME = ".studio"                    # the older pages' folder, beside Your Content
OLD_REELS, OLD_TALKING = "reel-pages", "talking"
OLD_LISTS = ("cache", "photos")         # <old>/cache/photos/<mark>/photos.json: the older pages' numbered list
JOURNAL = "brought-older.json"          # <kit>/.kit/brought-older.json: what a run is about to write, and what it did
MARK = "brought_from"                   # in our records: {"file": the older file's name, "id": the reel's id there}
OLDER_JPEG = (".jpg", ".jpeg")          # the older pages numbered only these
OUR_PHOTOS = (".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff")     # reel.py's PHOTOS (what `kit.py sheet` numbers)
TAKEN_WORD = "older"                    # a name that is taken: "<name> (older)", then "(older 2)"...
SAVED_AGAIN_SLACK = 2.0                 # seconds a file's time may sit past its script's before it counts as saved again
LENGTH_SLACK = 0.5                      # seconds a video's length may differ from the one its script was made from
TEST_STOP = "ASSISTANT_TEST_BRING_STOP"  # tests only: stop dead at a named point, as a run cut off would
TEST_RAISE = "ASSISTANT_TEST_BRING_RAISE"  # tests only: a shoot whose name holds these words fails in an unforeseen way
VIBE_WORDS = {"beat": "On every beat", "mixed": "A little of everything", "calm": "Calm", "build": "Build"}

ASK_UNCHANGED = ("The older page's own list of this shoot's photos isn't there, so the photo numbers can't be checked "
                 "against it. Ask: \"After you first opened this shoot on the older pages, did you ever add photos to it "
                 "or take any out?\" Only if they say no, never: run `look` again with --photos-unchanged, which lists "
                 "each reel's photos by file name for you to read back. If they did, or aren't sure, the reel stays where "
                 "it is.")
NAME_ORDER_NOT_PROOF = ("its photos are matched by name order only, which is not proof (it is wrong if a photo was ever "
                        "added on the older pages). Read the photo names `look --photos-unchanged` lists for it back to "
                        "them, and only on their yes that those are its photos run bring with --photos-unchanged "
                        "--names-confirmed")
RECORD_TROUBLE = ("this shoot's own reel record here is there but can't be read right now (the drive, or a file cut "
                  "short). It is never taken for an empty one and never written over, so no reel was brought for this shoot")


def say(msg=""):
    kit_mod.say(msg)


def nfc(s):
    return unicodedata.normalize("NFC", str(s))


def _stop_here(point):
    if os.environ.get(TEST_STOP) == point:
        os._exit(9)


def read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None


def reel_record(kit):
    """This kit's own reel record, read here and not through reel_page.load (which answers "no record" for a file
    it could not read): ("none", {}) when there is no file, ("ok", the record), or ("trouble", None) when the file
    is there and can't be read or is not a record. Trouble is never taken for empty."""
    try:
        raw = reel_page.record_path(kit).read_bytes()
    except FileNotFoundError:
        return "none", {"v": 1}
    except OSError:
        return "trouble", None
    try:
        d = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        return "trouble", None
    return ("ok", d) if isinstance(d, dict) else ("trouble", None)


def _num(x):
    return float(x) if type(x) in (int, float) and x == x and abs(x) < 10 ** 12 else None


class Unproven(Exception):
    """A photo number that can't be shown to mean one photo here; str(e) is the plain reason."""


# ---------- the older folder ----------

def old_folder(given):
    """(the older .studio folder, None) or (None, plain words)."""
    if given:
        p = Path(given).expanduser()
        if p.is_dir():
            return p, None
        return None, f"There is no folder at \"{given}\"."
    h = posts.home()
    if not h:
        return None, "The Assistant folder isn't set up on this computer yet, so there is nowhere to look for older reels."
    p = h / OLD_NAME
    if not p.is_dir():
        return None, (f"There is no \"{OLD_NAME}\" folder beside Your Content in \"{h.name}\", which is where the older "
                      "pages kept their reels. If they were kept somewhere else, name that folder with --from. "
                      "(Is the drive plugged in?)")
    return p, None


def old_shoots(old):
    """{shoot folder name as the file is called: {"reel": path or None, "talking": path or None}}."""
    out = {}
    for kind, folder in (("reel", OLD_REELS), ("talking", OLD_TALKING)):
        d = old / folder
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for f in names:
            if f.startswith(".") or not f.lower().endswith(".json") or f.lower().endswith(".prev.json"):
                continue
            p = d / f
            if p.is_file() and not p.is_symlink():
                out.setdefault(f[:-5], {"reel": None, "talking": None})[kind] = p
    return out


def old_reels(rec, first):
    """[(id, name, that reel's own fields)] from an older record: the open reel's fields are at the top, the
    others wait in versions[].data. A record with no list is one reel."""
    vs = rec.get("versions") if isinstance(rec.get("versions"), list) else []
    vs = [v for v in vs if isinstance(v, dict) and isinstance(v.get("id"), str) and reels.ID.fullmatch(v["id"])]
    top = {k: v for k, v in rec.items() if k not in ("versions", "current")}
    if not vs:
        return [("v1", first, top)], "v1"
    cur = rec.get("current") if any(v["id"] == rec.get("current") for v in vs) else vs[0]["id"]
    out, seen = [], set()
    for k, v in enumerate(vs):
        if v["id"] in seen:
            continue
        seen.add(v["id"])
        name = reels.clean_name(v.get("name")) or f"{first.rsplit(' ', 1)[0]} {k + 1}"
        data = top if v["id"] == cur else (v.get("data") if isinstance(v.get("data"), dict) else {})
        out.append((v["id"], name, data))
    return out, cur


# ---------- the photo numbers ----------

class Numbers:
    """Turns a photo number of the older pages into a file name, and that name into our number."""

    def __init__(self, old, shoot, kit, rec_file, unchanged=False):
        self.kit = kit
        self.rec_kit = kit_mod.load_rec(kit)
        self.folder = kit_mod.photos_dir(kit, self.rec_kit)
        self.old_name, self.how, self.why_not, self.ask = {}, "", "", False
        self.predicted = self.some_new = self.by_name_order = False
        self._ours()
        self._theirs(old, shoot, rec_file, unchanged)

    def _ours(self):
        """{file name: our number}: the kit's numbered list; when there is none yet, the numbers `kit.py sheet`
        will give a first list (name order, capitals aside, from 1), which `bring` makes before anything else."""
        rows = arrange.sheet_rows(self.kit)
        self.ours = {}
        self.predicted = self.some_new = False
        try:
            names = [f for f in os.listdir(self.folder) if not f.startswith(".") and f.lower().endswith(OUR_PHOTOS)
                     and (self.folder / f).is_file()]
        except OSError:
            names = []
        if rows:
            for x in rows:
                self.ours.setdefault(nfc(arrange.photo_name(x)), x["n"])
            # A photo that is in the folder and not on the list yet (the list is a step behind): the number
            # `kit.py sheet` will give it, as reel.py numbers (one that left and came back takes its old number;
            # a new one the next after the highest ever given, in name order). `bring` makes the list first and
            # plans again from the real one.
            sheet = read_json(self.kit / ".kit" / "sheet.json")
            gone = {}
            for x in (sheet.get("retired") if isinstance(sheet, dict) and isinstance(sheet.get("retired"), list) else []):
                if isinstance(x, dict) and type(x.get("n")) is int and isinstance(x.get("file"), str):
                    gone[nfc(x["file"])] = x["n"]
            have = {k.casefold() for k in self.ours}
            nxt = max(list(self.ours.values()) + list(gone.values()), default=0) + 1
            for f in sorted(names, key=lambda f: f.lower()):
                if nfc(f).casefold() in have:
                    continue
                self.predicted = self.some_new = True
                if nfc(f) in gone and gone[nfc(f)] not in self.ours.values():
                    self.ours[nfc(f)] = gone[nfc(f)]
                else:
                    self.ours[nfc(f)] = nxt
                    nxt += 1
                have.add(nfc(f).casefold())
            return
        self.predicted = True
        for k, f in enumerate(sorted(names, key=lambda f: f.lower()), 1):
            self.ours.setdefault(nfc(f), k)

    def _theirs(self, old, shoot, rec_file, unchanged):
        got = None
        for form in dict.fromkeys((shoot, nfc(shoot), unicodedata.normalize("NFD", shoot))):
            mark = hashlib.sha1(form.encode("utf-8")).hexdigest()[:12]
            got = read_json(old.joinpath(*OLD_LISTS, mark, "photos.json"))
            if got is not None:
                break
        if got is not None:
            rows = got if isinstance(got, list) else (got.get("photos") if isinstance(got, dict) else None)
            names, ok = {}, isinstance(rows, list) and bool(rows)
            for x in rows if ok else []:
                if (not isinstance(x, dict) or type(x.get("n")) is not int or x["n"] < 1 or x["n"] in names
                        or not isinstance(x.get("file"), str) or not x["file"]):
                    ok = False
                    break
                names[x["n"]] = nfc(Path(x["file"].replace("\\", "/")).name)
            if ok and len(set(names.values())) == len(names):
                self.old_name = names
                self.how = (f"from the older page's own numbered list of this shoot's photos ({len(names)} photos); "
                            "each photo was then found by its file name in this shoot's numbered list")
                return
            self.why_not = "the older page's list of this shoot's photos is there but can't be read as a list of photos"
            return
        if not unchanged:
            self.why_not, self.ask = "the older page's own list of this shoot's photos isn't there", True
            return
        # Name order: how the older pages numbered a shoot on a FIRST look (JPEGs only, hidden files left out, as
        # Python sorts the names the drive lists, capitals before small letters, from 1). From Nov 14 a photo added
        # later went at the END there, so this is not proof of anything: it is only what is shown for the
        # photographer to confirm by the file names (bring needs --names-confirmed).
        try:
            listed = [f for f in os.listdir(self.folder) if not f.startswith(".") and f.lower().endswith(OLDER_JPEG)
                      and (self.folder / f).is_file()]
        except OSError:
            listed = []
        if not listed:
            self.why_not = "this shoot's Photos folder can't be read right now"
            return
        try:
            when = Path(rec_file).stat().st_mtime if rec_file else 0
            newer = [f for f in listed if (self.folder / f).stat().st_mtime > when + SAVED_AGAIN_SLACK]
        except OSError:
            newer = listed
        if newer:
            self.why_not = (f"{len(newer)} photo{'s were' if len(newer) != 1 else ' was'} added or saved again after the "
                            f"older reel was last saved (\"{sorted(newer)[0]}\"), so name order no longer shows which "
                            "photo each number meant")
            return
        if (read_json(self.kit / ".kit" / "sheet.json") or {}).get("retired"):
            self.why_not = "a photo has been taken out of this shoot since it was first numbered, so name order no longer shows which photo each number meant"
            return
        self.old_name = {k: nfc(f) for k, f in enumerate(sorted(listed), 1)}
        self.by_name_order = True
        self.how = (f"NOT checked. The older page's own list isn't there, so each number is matched by name order "
                    f"({len(listed)} JPEG photos), which is only right if no photo was ever added to this shoot on the "
                    "older pages. Read each reel's photo names below back to them; bring only on their yes that those "
                    "are its photos (bring --photos-unchanged --names-confirmed)")

    def turn(self, n):
        """(file name, our number) for an older number. Raises Unproven(why)."""
        if type(n) is not int:
            raise Unproven(f"\"{n}\" is not a photo number")
        if not self.old_name:
            raise Unproven(self.why_not or "the photo numbers can't be checked")
        name = self.old_name.get(n)
        if name is None:
            raise Unproven(f"photo {n}: the older list has no photo with that number (it has {len(self.old_name)})")
        ours = self.ours.get(name)
        if ours is None:
            raise Unproven(f"photo {n} (\"{name}\") is not among this shoot's photos now")
        return name, ours

class Table:
    """The numbers one reel uses, for look's lines: older number, file name, our number."""

    def __init__(self, numbers):
        self.numbers, self.rows = numbers, {}

    def turn(self, n):
        name, ours = self.numbers.turn(n)
        self.rows[n] = (name, ours)
        return ours

    def order(self, lst, what):
        """A list of {n, h} of the older record's, as ours. Raises Unproven for a list that can't be read."""
        if not isinstance(lst, list):
            raise Unproven(f"{what} is not a list of photos")
        out, seen = [], set()
        for x in lst:
            if not isinstance(x, dict) or type(x.get("n")) is not int:
                raise Unproven(f"{what} holds something that is not a photo number")
            n = self.turn(x["n"])
            if n in seen:
                continue
            seen.add(n)
            out.append({"n": n, "h": x.get("h") if x.get("h") in ("+", "-") else ""})
        return out

    def lines(self):
        return [f"photo {n} there is \"{name}\", number {ours} here" for n, (name, ours) in sorted(self.rows.items())]


# ---------- one older reel, checked ----------

def _songs_by_place(kit, rec_kit):
    out = {}
    for s in reel_page.list_songs(kit, rec_kit):
        out[(s["where"], nfc(Path(s["path"]).name).casefold())] = s
    return out


def _footage(kit):
    """{name as compared: (name as it is, key)} for the videos in the shoot's Footage folder (nothing is written)."""
    out = {}
    for cf, (name, path) in TR._plain_videos(kit, reel_page.FOOTAGE).items():
        out[cf] = (name, TR._key_of(path))
    return out


def _capcut_store(given=None):
    if given:
        return Path(given).expanduser()
    if os.environ.get(TR.TEST_STORE):
        return Path(os.environ[TR.TEST_STORE])
    try:
        return reel_page._reel_module("capcut").default_store()
    except Exception:  # noqa: BLE001
        return None


def _project_here(store, name):
    try:
        return bool(store and isinstance(name, str) and name and "/" not in name and "\\" not in name
                    and not name.startswith(".") and name in os.listdir(store) and (store / name).is_dir())
    except OSError:
        return False


def _made_picks(text, t):
    """A made reel's order ("41,2-,c1,21") with every photo number turned into ours; a clip's token stays."""
    out = []
    for tok in str(text or "").split(","):
        tok = tok.strip()
        m = re.fullmatch(r"(\d+)([+-]?)", tok)
        out.append(f"{t.turn(int(m.group(1)))}{m.group(2)}" if m else tok)
    return ",".join(x for x in out if x)


def plan_reel(kit, numbers, her_id, name, data, made, store):
    """One older reel as our record would hold it. {"ok", "why", "name", "id", "saved", "moments", "claude_bts",
    "claude", "made", "left": [plain lines], "table": Table, "facts": [plain lines]}."""
    t = Table(numbers)
    p = {"ok": False, "why": "", "id": her_id, "name": name, "left": [], "table": t, "facts": [], "made": [], "claude": None}
    saved = data.get("saved") if isinstance(data.get("saved"), dict) else None
    claude = data.get("claude") if isinstance(data.get("claude"), list) and data.get("claude") else None
    their_moments = [m for m in (data.get("moments") if isinstance(data.get("moments"), list) else []) if isinstance(m, dict)]
    if saved is None and not claude and not their_moments and not data.get("claude_bts"):
        p["why"] = "there is nothing in it (no photos chosen, no clips)"
        return p
    saved = saved or {}
    on_sheet = set(numbers.ours.values())
    rec_kit = numbers.rec_kit
    left = p["left"]
    try:
        picks = t.order(saved.get("picks") or [], "the order")
        mine_picks = None if saved.get("mine_picks") is None else t.order(saved["mine_picks"], "their own order")
        p["claude"] = t.order(claude, "the assistant's pick") if claude else None
        bts = t.order(data.get("claude_bts") or [], "the assistant's order with footage")
        foot = _footage(kit)
        moments, gone = [], []
        for m in their_moments:
            one = {k: m[k] for k in ("id", "video", "start", "end", "photo") if k in m}
            if isinstance(m.get("label"), str):
                one["label"] = m["label"][:200]
            for k in ("keep", "named"):
                if isinstance(m.get(k), bool):
                    one[k] = m[k]
            if m.get("by") == "you":
                one["by"] = "you"
            if m.get("set"):
                one["set"] = True
            if not reel_page.moments_of({"moments": [one]}):
                left.append("a clip that can't be read (no video, or no start and end)")
                continue
            vname = re.sub(r"^Footage/", "", one["video"])
            hit = foot.get(nfc(vname).casefold())
            if hit is None:
                gone.append(vname)
                continue
            one["video"] = "Footage/" + hit[0]
            if one.get("photo") is not None:
                one["photo"] = t.turn(one["photo"])
            moments.append(one)
        for v in sorted(set(gone)):
            left.append(f"the clips from \"{v}\": that video is not in this shoot's Footage folder now")
    except Unproven as e:
        p["why"] = str(e)
        return p
    if len(picks) > reel_page.MAX_PICKS or (mine_picks and len(mine_picks) > reel_page.MAX_PICKS):
        p["why"] = f"it holds more than {reel_page.MAX_PICKS} photos, which a reel here can't"
        return p
    out = {"picks": [], "mine": True, "mine_picks": [], "song": None, "vibe": reel_page.default_vibe(), "footage": None,
           "style": "first", "ask": "", "feel": "", "sel": {}}
    sent = {"picks": picks}
    if "mine_picks" in saved:
        sent["mine_picks"] = mine_picks
    for k in ("mine", "vibe", "footage", "style", "ask", "feel", "photo_ask", "direct"):
        if k in saved:
            sent[k] = saved[k]
    if saved.get("style") == reel_page.BROLL_STYLE and saved.get("footage") is True:
        sent["kind"] = "broll"              # the older page kept the kind in its address; B-roll is the one a record can't be read as
    # the song: the older record names it by where it is ("Music/<file>"); ours by an id made from the same two
    song = saved.get("song")
    if song is None or song == "":
        sent["song"] = song
    elif isinstance(song, str) and "/" in song:
        where, fname = song.split("/", 1)
        s = _songs_by_place(kit, rec_kit).get((where, nfc(fname).casefold()))
        if s:
            sent["song"] = s["id"]
            p["facts"].append(f"song \"{Path(fname).stem}\"")
        else:
            left.append(f"the song \"{fname}\": it is not in this shoot's {where} folder now, so no song is picked")
    else:
        left.append("the song: the older record names it in a way that can't be read")
    if isinstance(saved.get("sel"), dict):
        ids = {m["id"] for m in moments}
        sent["sel"] = {k: [i for i in v if isinstance(i, str) and i in ids] for k, v in saved["sel"].items()
                       if isinstance(k, str) and isinstance(v, list)}
    if isinstance(saved.get("onscreen"), dict) and saved["onscreen"].get("text"):
        sent["onscreen"] = {k: saved["onscreen"][k] for k in ("text", "font", "style") if k in saved["onscreen"]}
        left.append("where the words on screen sat: the older page never saved it, so they start in the usual spot")
    names = {"mine": "whose order it is", "vibe": "the pace", "footage": "footage on or off", "style": "the footage style",
             "ask": "the note about footage", "feel": "how it should feel", "photo_ask": "the note about photos",
             "direct": "the direction for the edit", "sel": "which clips are chosen", "onscreen": "the words on screen",
             "kind": "the kind of reel", "song": "the song", "picks": "the order", "mine_picks": "their own order"}
    for k, v in sent.items():
        try:
            out[k] = reel_page.SAVE_FIELDS[k](v, kit, on_sheet)
        except (reel_page.Refused, TypeError, ValueError, KeyError, AttributeError):
            if k in ("picks", "mine_picks"):
                p["why"] = f"{names[k]} can't be read"
                return p
            left.append(f"{names[k]}: what the older record holds isn't something this page can keep")
    up = _num(saved.get("updated"))
    out["updated"] = up if up is not None else time.time()
    # "Let my assistant choose" there, with an order on the page that is not the assistant's pick as it stands
    # (the older page and its post kit showed the saved order; ours would show the pick): it comes over as their
    # own order, so this page shows what that one showed. Both orders are kept.
    shown = [x["n"] for x in out["picks"]]
    if (out.get("mine") is False and shown and p["claude"] and shown != [x["n"] for x in p["claude"]]
            and shown != [x["n"] for x in bts]):
        out["mine"], out["mine_picks"] = True, [dict(x) for x in out["picks"]]
        left.append("\"Let the Assistant choose\": the order the older page showed was not the assistant's pick as it "
                    "stands, so it comes over as their own order (the pick is kept beside it)")
    if any("about" in m for m in their_moments) or any(isinstance(m, dict) and "about" in m for m in
                                                        (data.get("moments_found") if isinstance(data.get("moments_found"), list) else [])):
        left.append("the clips' descriptions: this page keeps a clip's name only")
    p.update(ok=True, saved=out, moments=moments, claude_bts=bts)
    # which reels were made in CapCut: only a project that is on this computer under that name
    for m in made:
        proj = m.get("project")
        if not _project_here(store, proj):
            left.append(f"\"{proj}\" as made: no CapCut project by that name is on this computer" if isinstance(proj, str) and proj
                        else "a note of a reel made, with no project name")
            continue
        try:
            text = _made_picks(m.get("picks"), t)
        except Unproven:
            left.append(f"\"{proj}\" as made: a photo in it can't be matched")
            continue
        one = {"project": proj, "picks": text, "vibe": m.get("vibe") if m.get("vibe") in reel_page.VIBES else out["vibe"],
               "footage": m.get("footage") if m.get("footage") in reel_page.STYLES + (reel_page.BROLL_STYLE,) else None,
               "song": Path(m["song"].replace("\\", "/")).name[:200] if isinstance(m.get("song"), str) else "",
               "when": _num(m.get("when")) or 0.0}
        p["made"].append(one)
    n = len(out["picks"])
    kind = reel_page.reel_kind(out)
    p["facts"][:0] = [f"{n} photo{'s' if n != 1 else ''}" + (f", {len(moments)} clip{'s' if len(moments) != 1 else ''}" if moments else ""),
                      "pace " + VIBE_WORDS.get(out["vibe"], out["vibe"])]
    if kind:
        p["facts"].append({"bts": "behind the scenes", "photos": "just photos", "broll": "B-roll"}[kind])
    if p["made"]:
        p["facts"].append("made in CapCut as " + ", ".join(f"\"{m['project']}\"" for m in p["made"]))
    return p


# ---------- one older talking reel, checked ----------

def plan_talking(kit, numbers, her_id, name, data, store):
    eng = TR._engine()
    t = Table(numbers)
    p = {"ok": False, "why": "", "id": her_id, "name": name, "left": [], "table": t, "facts": [], "fields": {}, "made": []}
    left = p["left"]
    video = eng._video_name(data.get("video"))
    raw = data.get("words") if isinstance(data.get("words"), list) else []
    if not video:
        p["why"] = "no video was chosen for it"
        return p
    if data.get("status") != "ready" or not raw:
        p["why"] = f"\"{video}\" was never turned into a script there (or that didn't finish)"
        return p
    hit = TR._plain_videos(kit, TR.TALKING).get(nfc(video).casefold())
    if hit is None:
        p["why"] = f"its video, \"{video}\", is not in this shoot's Talking folder now"
        return p
    name_now, path = hit
    key = TR._key_of(path)
    made_at = _num(data.get("transcribed"))
    try:
        st = path.stat()
    except OSError:
        key = None
    if not key:
        p["why"] = f"its video, \"{video}\", can't be read right now"
        return p
    if made_at is None:
        p["why"] = f"the older record doesn't say when \"{video}\" was turned into a script, so nothing shows the file is still the same one"
        return p
    if st.st_mtime > made_at + SAVED_AGAIN_SLACK:
        p["why"] = (f"\"{video}\" was saved again after its script was made, so the script's word times belong to the "
                    "earlier file. Press Edit my video on the talking reel page for a fresh script")
        return p
    info = data.get("info") if isinstance(data.get("info"), dict) else {}
    dur = _num(info.get("dur"))
    try:
        length = _num(reel_page._video().facts(path).get("length"))
    except Exception:  # noqa: BLE001  (a file the header reader can't read: the time check above stands alone)
        length = None
    if dur is not None and length is not None and abs(dur - length) > LENGTH_SLACK:
        p["why"] = (f"\"{video}\" is {length:.1f} seconds long now and was {dur:.1f} when its script was made, so it is "
                    "not the same file. Press Edit my video on the talking reel page for a fresh script")
        return p
    # the words as they were HEARD (a word fixed on the older page was written over, with the heard one beside it)
    words, fixes = [], {}
    for i, x in enumerate(raw):
        if isinstance(x, dict) and eng.heard(x) is not None:
            if isinstance(x.get("w"), str):
                fixes[str(i)] = x["w"]
            x = {k: v for k, v in x.items() if k != "w0"}
            x["w"] = raw[i]["w0"]
        words.append(x)
    clean = eng.clean(words)
    if len(clean) != len(raw):
        p["why"] = "some of its words can't be read (a word with no text or no times), so the word numbers wouldn't line up"
        return p
    if dur is not None and clean and clean[-1]["end"] > dur + 1.0:
        p["why"] = "its words run past the end of the video, so they belong to another file"
        return p
    n = len(clean)
    had = TR.words_for(kit, name_now)
    if had and (had.get("key") != key or eng.clean(had.get("words")) != clean):
        p["why"] = f"\"{video}\" already has a script here (Edit my video was pressed on it), and that one is never written over"
        return p
    slim = TR._slim(kit)
    for _vid, d in reels.each(slim, TR.TALK_LIVE, TR.TALK_FIRST):
        if isinstance(d.get("video"), str) and nfc(d["video"]).casefold() == nfc(name_now).casefold() and not _is_ours(d.get(MARK)):
            p["why"] = f"\"{video}\" is already the video of a talking reel here, and that one is never changed"
            return p
    # the edit, entry by entry through the page's own checks
    foot = _footage(kit)
    ctx = {"n": n, "heard": [w["w"] for w in clean], "on_sheet": set(numbers.ours.values()),
           "footage": lambda: {k: nm for nm, k in foot.values() if k}, "stored_ns": set(), "stored_v": {},
           "known": lambda: {}, "foot_names": lambda: TR._plain_videos(kit, reel_page.FOOTAGE), "seen": {},
           "stored_overlap": False}
    f = p["fields"]

    def each(key, items, what):
        good, bad = [], 0
        for x in items:
            try:
                good += TR.SAVE_FIELDS[key]([x], ctx)
            except (TR.Refused, TypeError, ValueError, KeyError, AttributeError):
                bad += 1
        if bad:
            left.append(f"{bad} {what}{'s' if bad != 1 else ''} that point{'s' if bad == 1 else ''} at words this script doesn't have")
        return good

    hers = dict(data, words=clean, sentences=data.get("sentences") if isinstance(data.get("sentences"), list) else eng.sentences(clean))
    f["cut"] = each("cut", [list(x) for x in (data.get("cut") if isinstance(data.get("cut"), list) else []) if isinstance(x, (list, tuple))], "cut")
    f["splits"] = each("splits", data.get("splits") if isinstance(data.get("splits"), list) else [], "split")
    f["speeds"] = each("speeds", [x for x in (data.get("speeds") if isinstance(data.get("speeds"), list) else []) if isinstance(x, dict)], "speed")
    f["zooms"] = each("zooms", eng.zooms(hers), "zoom")
    shots = []
    try:
        for s in eng.shots(hers):
            s = dict(s)
            if s["v"]:
                v = foot.get(nfc(s["v"]).casefold())
                if v is None or not v[1]:
                    left.append(f"a stretch showing \"{s['v']}\": that video is not in this shoot's Footage folder now")
                    continue
                s["v"] = {"key": v[1], "name": v[0]}
            else:
                s["ns"] = [t.turn(k) for k in s["ns"]]
            shots.append(s)
    except Unproven as e:
        p["why"] = str(e)
        return p
    got = each("shots", shots, "photo stretch")
    try:
        f["shots"] = TR.SAVE_FIELDS["shots"]([dict(s, v={"key": foot[nfc(s["v"]).casefold()][1], "name": s["v"]}) if s["v"] else s
                                              for s in got], ctx)
    except (TR.Refused, TypeError, ValueError, KeyError, AttributeError):
        f["shots"] = []
        if got:
            left.append("the photos placed over the words: two stretches share a word, which this page can't keep")
    for k in list(fixes):
        if int(k) >= n:
            fixes.pop(k)
    try:
        f["fixes"] = TR.SAVE_FIELDS["fixes"](fixes, ctx)
    except (TR.Refused, TypeError, ValueError, KeyError, AttributeError):
        f["fixes"] = {}
        left.append("the words fixed on the page: one of them is longer than this page keeps")
    for k, what in (("captions", "captions on or off"), ("cap_pos", "where the captions sit"), ("cap_size", "the captions' size"),
                    ("photo_mode", "who places the photos")):
        if k in data:
            try:
                f[k] = TR.SAVE_FIELDS[k](data[k], ctx)
            except (TR.Refused, TypeError, ValueError, KeyError, AttributeError):
                left.append(f"{what}: what the older record holds isn't something this page can keep")
    f.setdefault("captions", True)
    if isinstance(data.get("claude_cut"), list):
        try:
            f["claude_cut"] = TR.SAVE_FIELDS["cut"]([list(x) for x in data["claude_cut"]], ctx)
            why = data.get("claude_why") if isinstance(data.get("claude_why"), list) else []
            f["claude_why"] = [str(x)[:TR.WHY_LONG] for x in why if isinstance(x, str)][:TR.WHY_MOST]
        except (TR.Refused, TypeError, ValueError, KeyError, AttributeError):
            left.append("the assistant's own first cut (kept only for reference)")
    if data.get("claude_shots") is True and f["shots"]:
        f["claude_shots"] = True
    for m in data.get("made") if isinstance(data.get("made"), list) else []:
        if isinstance(m, dict) and _project_here(store, m.get("project")):
            p["made"].append({"project": m["project"], "when": _num(m.get("when")) or 0.0})
        elif isinstance(m, dict):
            left.append(f"\"{m.get('project')}\" as made: no CapCut project by that name is on this computer")
    left.append("when the script was made: it is dated today here")
    p.update(ok=True, video=name_now, key=key, words=clean,
             info={k: info[k] for k in ("w", "h", "dur") if _num(info.get(k)) is not None})
    p["facts"] = [f"\"{name_now}\"", f"{n} words", f"{len(f['cut'])} cut{'s' if len(f['cut']) != 1 else ''}",
                  f"{len(f['shots'])} photo stretch{'es' if len(f['shots']) != 1 else ''}"]
    if f["zooms"]:
        p["facts"].append(f"{len(f['zooms'])} zoom{'s' if len(f['zooms']) != 1 else ''}")
    if f["fixes"]:
        p["facts"].append(f"{len(f['fixes'])} word{'s' if len(f['fixes']) != 1 else ''} fixed")
    return p


# ---------- what is here already ----------

def _is_ours(m):
    return isinstance(m, dict) and isinstance(m.get("file"), str) and isinstance(m.get("id"), str)


def reel_marks(rec):
    """{(older file name, older id): our reel id} for the reels of this record that were brought."""
    got = rec.get(MARK) if isinstance(rec.get(MARK), dict) else {}
    return {(m["file"], m["id"]): vid for vid, m in got.items() if _is_ours(m)}


def talking_marks(slim):
    out = {}
    for vid, d in reels.each(slim, TR.TALK_LIVE, TR.TALK_FIRST):
        if _is_ours(d.get(MARK)):
            out[(d[MARK]["file"], d[MARK]["id"])] = vid
    return out


def reel_blank(d, found_ids=()):
    """One reel's own fields: is there nothing of the photographer's (or the Assistant's) in it? A reel page that
    was only opened, or a reel just started, holds its choices at their starting values and the shoot's found
    clips as found; anything more (a photo, a note, a song, a clip of theirs, a clip taken out, a pick, an
    earlier pick) and it is NOT blank, and is never filled or replaced."""
    if any(d.get(k) for k in ("claude_bts", "removed", "claude", "claude_earlier")):
        return False
    s = d.get("saved")
    if s is None:
        s = {}
    if not isinstance(s, dict):
        return False
    if s.get("picks") or s.get("mine_picks") or s.get("song"):
        return False
    if any(s.get(k) and not (isinstance(s[k], str) and not s[k].strip()) for k in ("ask", "feel", "photo_ask", "direct")):
        return False
    o = s.get("onscreen")
    if o and not (isinstance(o, dict) and not o.get("text")):
        return False
    if s.get("sel") and not (isinstance(s["sel"], dict) and not any(s["sel"].values())):
        return False
    ms = d.get("moments")
    if ms:
        if not isinstance(ms, list):
            return False
        for m in ms:
            if (not isinstance(m, dict) or m.get("by") == "you" or "set" in m or m.get("named") or m.get("keep") is False
                    or m.get("id") not in found_ids):
                return False
    return True


def blank_here(rec, vid, rec_kit=None):
    """Is the reel `vid` of this record blank (reel_blank), with no reel of it made?"""
    made = rec.get("made") if isinstance(rec.get("made"), list) else ([rec["made"]] if rec.get("made") else [])
    if any(not isinstance(m, dict) or reel_page.made_for(m) == vid for m in made):
        return False
    if vid == reels.FIRST_ID and isinstance(rec_kit, dict) and rec_kit.get("reel"):
        return False                                    # a reel made from the chat the older way is the first reel's
    found = {m.get("id") for m in (rec.get("moments_found") if isinstance(rec.get("moments_found"), list) else [])
             if isinstance(m, dict) and isinstance(m.get("id"), str)}
    return reel_blank(reels.data_of(rec, vid, reel_page.REEL_LIVE, reel_page.REEL_FIRST), found)


def real_reels(rec, rec_kit=None):
    """[{id, name}] of the reels here that hold something."""
    return [v for v in reels.listed(rec, reel_page.REEL_FIRST) if not blank_here(rec, v["id"], rec_kit)]


def place_reels(rec, todo, fname, kit, rec_kit, older_ids, cur, dry=False, say_wrong=None):
    """Put each checked older reel of `todo` into the record IN MEMORY (the caller saves, or throws the copy
    away: Shoot.plan runs this on a copy to say what will happen). Returns [(plan, our id, our name)].

    Where each lands: under the id it had on the older pages when that id is free here, or when the reel here
    under it is blank (that one is filled); otherwise under a new id, past every id here and every older one.
    The reel that was open is open again afterwards unless nothing here held anything, and then the older
    pages' open reel is."""
    first, live = reel_page.REEL_FIRST, reel_page.REEL_LIVE
    all_blank = not real_reels(rec, rec_kit)
    back = reels.current(rec, first)
    marks = reel_marks(rec)
    mark = dict(rec.get(MARK)) if isinstance(rec.get(MARK), dict) else {}
    placed = []
    for p in todo:
        if (fname, p["id"]) in marks:
            continue
        ids = {v["id"] for v in reels.listed(rec, first)}
        try:
            if p["id"] in ids and blank_here(rec, p["id"], rec_kit):
                vid = p["id"]
                if reels.current(rec, first) != vid:
                    reels.switch(rec, vid, live, first)
                name = free_name(p["name"], [v["name"] for v in reels.listed(rec, first) if v["id"] != vid])
                if name and name != reels.name_of(rec, vid, first):
                    reels.rename(rec, vid, name, first)
                name = reels.name_of(rec, vid, first)
            else:
                name = free_name(p["name"], [v["name"] for v in reels.listed(rec, first)])
                as_id = p["id"]
                if as_id in ids:
                    as_id = "v%d" % (1 + max(int(i[1:]) for i in ids | set(older_ids)))
                vid = reels.new(rec, live, reel_page.reel_fresh, first, reel_page.REEL_WORD, name, as_id=as_id)
                name = reels.name_of(rec, vid, first)
        except reels.Wrong as e:
            if say_wrong:
                say_wrong(p, e)
            continue
        for k in reel_page.REEL_KEYS:
            rec.pop(k, None)
        saved = dict(p["saved"])
        if vid == reels.FIRST_ID and saved.get("mine") is False and saved.get("picks") and not dry \
                and kit_pick(kit) != (p.get("claude") or []):
            saved["mine"] = True          # the kit's pick is another one: the older order stays the one shown
        rec["saved"], rec["moments"] = saved, p["moments"]
        if p["moments"]:
            rec["moments_at"] = time.time()
        if p["claude_bts"]:
            rec["claude_bts"] = p["claude_bts"]
        if vid != reels.FIRST_ID and p.get("claude"):
            rec["claude"], rec["claude_at"] = p["claude"], time.time()
        mark[vid] = {"file": fname, "id": p["id"], "when": time.strftime("%Y-%m-%d %H:%M:%S")}
        placed.append((p, vid, name))
    if not placed:
        return placed
    rec[MARK] = mark
    ours = {p["id"]: vid for p, vid, _n in placed}
    several = reels.several(rec)
    made = [m for m in (rec.get("made") if isinstance(rec.get("made"), list) else [])]
    for p, vid, _n in placed:
        for m in p["made"]:
            m = dict(m)
            if several:
                m["version"] = vid
            made.append(m)
    if made:
        rec["made"] = made
    want = ours.get(cur, placed[0][1]) if all_blank else back
    if want != reels.current(rec, first):
        reels.switch(rec, want, live, first)
    return placed


def queue_posts(kit):
    """{reel id: a few words naming the post} for this kit's reel posts in the posting queue that are still to
    post. Read only; any trouble reading it is an empty answer (this is for a heads-up line, nothing more)."""
    out = {}
    try:
        import posting_queue as PQ
        d = read_json(PQ.PFILE)
        for x in (d.get("pieces") if isinstance(d, dict) and isinstance(d.get("pieces"), list) else []):
            if isinstance(x, dict) and PQ.kit_role(x) == "reel" and PQ.same_kit(x, kit) and x.get("status") != "posted":
                words = f"{x.get('shoot_name') or 'this shoot'} reel" + (f" · {x['reel_name']}" if isinstance(x.get("reel_name"), str) and x["reel_name"] else "")
                out.setdefault(PQ.reel_version(x), words)
    except Exception:  # noqa: BLE001
        return {}
    return out




def talking_empty(slim):
    return not reels.several(slim) and not any(k for k in slim if k not in TR.TALK_KEEP and slim[k] not in (None, "", [], {}))


def free_name(name, taken):
    """`name`, or with " (older)" after it when a reel here already has it. Never longer than a reel's name may be."""
    name = reels.clean_name(name)
    taken = {x.casefold() for x in taken}
    if name and name.casefold() not in taken:
        return name
    for k in range(1, 100):
        tail = f" ({TAKEN_WORD})" if k == 1 else f" ({TAKEN_WORD} {k})"
        one = reels.clean_name(name[:reels.NAME_MAX - len(tail)].rstrip() + tail)
        if one.casefold() not in taken:
            return one
    return ""


def kit_pick(kit):
    nums, marks = arrange.kit_pick(kit_mod.load_rec(kit), "reel")
    return [{"n": n, "h": m} for n, m in zip(nums, marks)]


# ---------- the journal ----------

def journal_note(kit, items):
    """Write down what is about to be written (names and ids only), before the first change."""
    p = kit / ".kit" / JOURNAL
    j = read_json(p)
    j = j if isinstance(j, dict) and isinstance(j.get("runs"), list) else {"v": 1, "runs": []}
    j["runs"] = j["runs"][-19:] + [{"started": time.strftime("%Y-%m-%d %H:%M:%S"), "state": "started", "items": items}]
    arrange.write_whole(p, j)
    return j


def journal_done(kit, j, items):
    j["runs"][-1].update(state="finished", finished=time.strftime("%Y-%m-%d %H:%M:%S"), items=items)
    arrange.write_whole(kit / ".kit" / JOURNAL, j)


# ---------- one shoot ----------

class Shoot:
    def __init__(self, old, name, files, a, doing=False):
        self.old, self.name, self.files, self.a, self.doing = old, name, files, a, doing
        self.kit = arrange.kit_by_name(name)
        self.store = _capcut_store(a.capcut_store)
        self.short = reel_page.short_name(name)
        self.problems = 0
        self.todo = 0
        self.brought = 0
        self.found = []

    def plan(self):
        """Read everything; write nothing. Sets self.reels, self.talks (plans) and what is here already."""
        kit = self.kit
        if os.environ.get(TEST_RAISE) and os.environ[TEST_RAISE] in self.name:
            raise RuntimeError("the test's own")
        rec_file = self.files["reel"] or self.files["talking"]
        self.numbers = Numbers(self.old, self.name, kit, rec_file, self.a.photos_unchanged)
        self.reels, self.talks = [], []
        self.reel_cur = self.talk_cur = None
        self.older_ids = []
        if self.files["reel"]:
            hers = read_json(self.files["reel"])
            if not isinstance(hers, dict):
                self.reels.append({"ok": False, "why": "the older record can't be read", "name": "the reel", "id": "", "left": [], "facts": []})
            else:
                made = [m for m in (hers.get("made") if isinstance(hers.get("made"), list) else []) if isinstance(m, dict)]
                got, self.reel_cur = old_reels(hers, reel_page.REEL_FIRST)
                self.older_ids = [vid for vid, _nm, _data in got]
                for vid, nm, data in got:
                    self.reels.append(plan_reel(kit, self.numbers, vid, nm, data, [m for m in made if reel_page.made_for(m) == vid], self.store))
                self.found = [m for m in (hers.get("moments_found") if isinstance(hers.get("moments_found"), list) else []) if isinstance(m, dict)]
        if self.files["talking"]:
            hers = read_json(self.files["talking"])
            if not isinstance(hers, dict):
                self.talks.append({"ok": False, "why": "the older record can't be read", "name": "the talking reel", "id": "", "left": [], "facts": []})
            else:
                got, self.talk_cur = old_reels(hers, TR.TALK_FIRST)
                for vid, nm, data in got:
                    self.talks.append(plan_talking(kit, self.numbers, vid, nm, data, self.store))
                # Two older talking reels on ONE video, each with a script of its own: here a video keeps one
                # script, so only one of them can come (the one that was open there, else the first).
                kept = {}
                for p in sorted((p for p in self.talks if p["ok"]), key=lambda p: p["id"] != self.talk_cur):
                    k = nfc(p["video"]).casefold()
                    if k in kept and kept[k]["words"] != p["words"]:
                        p.update(ok=False, why=f"its video, \"{p['video']}\", is also the video of the older talking reel "
                                 f"\"{kept[k]['name']}\", with a different script. A video keeps one script here, so only that "
                                 "one comes over. For this one, start a new talking reel and press Edit my video")
                    else:
                        kept.setdefault(k, p)
        # Name order is not proof: without their own yes to the photo names, nothing that leans on a number comes.
        if self.numbers.by_name_order and self.doing and not getattr(self.a, "names_confirmed", False):
            for p in self.reels + self.talks:
                if p["ok"] and p["table"].rows:
                    p.update(ok=False, why=NAME_ORDER_NOT_PROOF)
        how, rec = reel_record(kit)
        self.reel_trouble = how == "trouble"
        if self.reel_trouble:
            rec = {"v": 1}
            for p in self.reels:
                if p["ok"]:
                    p.update(ok=False, why=RECORD_TROUBLE)
        rec_kit = self.numbers.rec_kit
        self.here_reels = real_reels(rec, rec_kit)
        marks = reel_marks(rec)
        for p in self.reels:
            p["here"] = marks.get((self.files["reel"].name, p["id"]))
            p["notes"] = []
        for p in self.talks:
            p["notes"] = []
        try:
            slim = TR._slim(kit)
        except TR.Unreadable:
            slim = None
        self.talk_trouble = slim is None
        slim = slim or {"v": 1}
        self.slim_empty = talking_empty(slim)
        self.here_talks = reels.listed(slim, TR.TALK_FIRST) if not self.slim_empty else []
        marks = talking_marks(slim)
        for p in self.talks:
            p["here"] = marks.get((self.files["talking"].name, p["id"]))
        # where each lands, and under which name: the real placing, done on a copy that is thrown away
        self.pick_plan = None
        todo = [p for p in self.reels if p["ok"] and not p["here"]]
        trial = copy.deepcopy(rec)
        before = {v["id"]: v["name"] for v in reels.listed(rec, reel_page.REEL_FIRST)}
        real = {v["id"] for v in self.here_reels}
        posts = queue_posts(kit) if todo else {}
        first = not self.here_reels
        for p in todo:
            p["as"], p["lands"] = "", ""
        fname = self.files["reel"].name if self.files["reel"] else ""
        for p, vid, name in place_reels(trial, todo, fname, kit, rec_kit, self.older_ids, self.reel_cur, dry=True):
            p["as"], p["vid"] = name, vid
            p["lands"], first = ("first" if first else "added"), False
            if vid == reels.FIRST_ID:
                self._first_pick(p)
            if vid != p["id"] and p["id"] in posts and p["id"] in real:
                p["notes"].append(f"a post in the posting queue (\"{posts[p['id']]}\") belongs to the reel \"{before[p['id']]}\" "
                                  f"that is already here. If it was added to the queue on the older page, it was meant for "
                                  f"\"{p['name']}\": take it out of the queue and add \"{name}\" again from the post kit")
        for p in todo:
            if not p["lands"]:
                p.update(ok=False, why="this shoot can't keep another reel under that name here")
        got = {p.get("vid") for p in todo if p["lands"]}
        self.place_kept = [v["name"] for v in reels.listed(trial, reel_page.REEL_FIRST)
                           if got and v["id"] not in got and v["id"] not in real and v["id"] in self.older_ids]
        taken = [v["name"] for v in self.here_talks]
        first = self.slim_empty
        for p in self.talks:
            if p["here"] or not p["ok"]:
                continue
            if first:
                p["as"], p["lands"], first = p["name"], "first", False
            else:
                p["as"], p["lands"] = free_name(p["name"], taken), "added"
            taken.append(p["as"])

    def _first_pick(self, p):
        """The reel that becomes the kit's first reel: its pick of the Assistant's lives in kit.json."""
        has = kit_pick(self.kit)
        want = p.get("claude")
        if want and not has:
            self.pick_plan = reel_page._order_text(want)
            p["facts"].append("the assistant's pick comes along (as this shoot's reel pick)")
            return
        if has and want != has:
            if want:
                p["left"].append("the assistant's pick from the older page: this shoot already has a reel pick here, and that one is never replaced")
            if p["saved"].get("mine") is False and p["saved"].get("picks"):
                p["saved"]["mine"] = True
                p["left"].append("\"Let the Assistant choose\": so the page shows the same order the older page showed, it comes over as their own order")

    def tell(self, doing):
        say(f"\n{self.short}  (the older records are named \"{self.name}\")")
        if self.kit is None:
            say("  No post kit by that name is in Your Content, so there is nowhere to bring this one. Nothing was changed.")
            self.problems += 1
            return
        say(f"  Post kit: \"{self.kit.name}\".")
        n = self.numbers
        if n.how:
            say(f"  How the photo numbers were checked: {n.how}."
                + (" Some photos in this shoot's Photos folder have no number here yet; bringing numbers them first "
                   "(shown below as they will be)." if n.some_new else
                   " This shoot's photos have no numbers here yet; bringing gives them their numbers first (shown "
                   "below as they will be)." if n.predicted else ""))
        else:
            say(f"  The photo numbers can't be checked: {n.why_not}.")
            if n.ask:
                say("  " + ASK_UNCHANGED)
        for kind, plans, here, word in (("Reel", self.reels, self.here_reels, "reel"), ("Talking reel", self.talks, self.here_talks, "talking reel")):
            for p in plans:
                head = f"  {kind} \"{p['name']}\": "
                if p.get("here"):
                    say(head + "already brought. Nothing to do.")
                    continue
                if not p["ok"]:
                    say(head + f"can't be brought: {p['why']}.")
                    self.problems += 1
                    continue
                self.todo += 1
                if p["lands"] == "first":
                    where = f"becomes this shoot's {word}"
                else:
                    where = f"added as another {word}"
                if p["as"] != p["name"]:
                    where += f", called \"{p['as']}\" because \"{p['name']}\" is taken"
                if here:
                    where += (f", beside the {len(here)} already here, which stay{'s' if len(here) == 1 else ''} as "
                              f"{'it is' if len(here) == 1 else 'they are'} and open; find this one under "
                              f"Your {'talking ' if kind != 'Reel' else ''}reels, called \"{p['as']}\"")
                say(head + ("can be brought: " if not doing else "") + where + ". " + ", ".join(p["facts"]) + ".")
                for line in p["table"].lines():
                    say("      " + line)
                for line in p["left"]:
                    say("      Not brought: " + line + ".")
                for line in p.get("notes") or []:
                    say("      Check: " + line + ".")
        for nm in getattr(self, "place_kept", []):
            say(f"  An empty reel called \"{nm}\" stays in this shoot's list of reels: it holds the place of an older reel "
                "that was not brought, so the ones that were keep the ids their queued posts know them by.")
        if self.talk_trouble and self.talks:
            say("  This shoot's talking reel record can't be read right now, so no talking reel was looked at closely.")

    # ----- bring -----

    def bring(self):
        kit = self.kit
        if self.numbers.predicted:
            with contextlib.redirect_stdout(io.StringIO()):      # kit.py's own lines name a file; not for this reader
                made = kit_mod.sheet(kit, quick=True)
            if made != 0 or not arrange.sheet_rows(kit):
                say("  I couldn't number this shoot's photos, so nothing was brought for it.")
                self.problems += 1
                return
            self.plan()
            if self.numbers.predicted:
                say("  Some of this shoot's photos still have no number here, so nothing was brought for it. Run it again.")
                self.problems += 1
                return
        self.tell(True)
        if not self.todo:
            return
        items = ([{"kind": "reel", "file": self.files["reel"].name, "id": p["id"], "name": p["name"], "as": p["as"]}
                  for p in self.reels if p["ok"] and not p.get("here")]
                 + [{"kind": "talking", "file": self.files["talking"].name, "id": p["id"], "name": p["name"], "as": p["as"],
                     "video": p["video"]} for p in self.talks if p["ok"] and not p.get("here")])
        kit_mod.hidden(kit)
        j = journal_note(kit, items)
        _stop_here("after-journal")
        done = []
        try:
            done += self._bring_reels()
        except arrange.Busy:
            say("  Something else is saving this shoot's reel right now, so its reels were not brought. Try again in a moment.")
            self.problems += 1
        done += self._bring_talks()
        for it in items:
            it["state"] = "brought" if (it["kind"], it["id"]) in done else "not brought"
        self.brought = len(done)
        journal_done(kit, j, items)

    def _bring_reels(self):
        kit, todo = self.kit, [p for p in self.reels if p["ok"] and not p.get("here")]
        if not todo:
            return []
        if self.pick_plan and not kit_pick(kit):
            # the first reel's pick of the Assistant's: kit.json, through kit.py's own writer, only when there is none
            r = subprocess.run([sys.executable, str(HERE / "kit.py"), "picks", str(kit), "--reel", self.pick_plan],
                               capture_output=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                say("  The assistant's pick from the older page could not be kept as this shoot's reel pick; the order itself still comes over.")
        _stop_here("after-pick")
        fname = self.files["reel"].name
        out = []
        with arrange.locked(reel_page.lock_path(kit)):
            if reel_record(kit)[0] == "trouble":           # never through load(), which reads trouble as "no record"
                say("  " + RECORD_TROUBLE[0].upper() + RECORD_TROUBLE[1:] + ".")
                self.problems += len(todo)
                return []
            rec, rows, stamp = reel_page.sync(kit)
            if not rows:
                say("  This shoot's numbered list of photos can't be read right now, so its reels were not brought.")
                self.problems += len(todo)
                return []
            if self.numbers.ours != {nfc(arrange.photo_name(x)): x["n"] for x in rows}:
                say("  This shoot's photos changed while I was looking. Nothing was brought; run it again.")
                self.problems += len(todo)
                return []
            rec_kit = kit_mod.load_rec(kit)
            had_found = bool(rec.get("moments_found"))
            all_blank = not real_reels(rec, rec_kit)

            def wrong(p, e):
                say(f"  Reel \"{p['name']}\" was not brought: {e}")
                self.problems += 1
            placed = place_reels(rec, todo, fname, kit, rec_kit, self.older_ids, self.reel_cur, say_wrong=wrong)
            if not placed:
                return []
            out = [("reel", p["id"]) for p, _vid, _name in placed]
            if not had_found and all_blank:
                foot, good = _footage(kit), []
                for m in self.found:
                    one = {k: m[k] for k in ("id", "video", "start", "end") if k in m}
                    if isinstance(m.get("label"), str):
                        one["label"] = m["label"][:200]
                    if isinstance(m.get("keep"), bool):
                        one["keep"] = m["keep"]
                    hit = foot.get(nfc(re.sub(r"^Footage/", "", str(one.get("video") or ""))).casefold())
                    if hit and reel_page.moments_of({"moments": [one]}):
                        one["video"] = "Footage/" + hit[0]
                        good.append(one)
                if good:
                    rec["moments_found"] = good
            rec["rev"] = int(rec.get("rev") or 0) + 1
            rec.pop("from", None)
            reel_page._stamp_names(rec, rows, stamp)
            reel_page.save(kit, rec)
        return out

    def _bring_talks(self):
        kit, out = self.kit, []
        todo = [p for p in self.talks if p["ok"] and not p.get("here")]
        if not todo:
            return out
        fname = self.files["talking"].name
        try:
            if TR.job_running(kit) or TR._starting(TR.read_job(kit)) or TR.make_running(kit):
                say("  This shoot's talking reel is busy right now (a script or a reel is being made), so its talking reels were "
                    "not brought. Try again when it's done.")
                self.problems += len(todo)
                return out
            slim = TR._slim(kit)
            # nothing of theirs here: empty, or (a run cut off part way) only talking reels this brought
            was_empty = talking_empty(slim) or all(_is_ours(d.get(MARK)) for _vid, d in reels.each(slim, TR.TALK_LIVE, TR.TALK_FIRST))
            ours = dict((older, vid) for (_file, older), vid in talking_marks(slim).items() if _file == fname)
            for p in todo:
                # the words first (once per video, their own file, the version before kept), never touching the
                # record: no reel here names this video (plan_talking), so put_words leaves the record as it is
                had = TR.words_for(kit, p["video"])
                if had and (had.get("key") != p["key"] or TR._engine().clean(had.get("words")) != p["words"]):
                    say(f"  Talking reel \"{p['name']}\" was not brought: \"{p['video']}\" has another script here now, "
                        "and that one is never written over.")
                    self.problems += 1
                    continue
                TR.put_words(kit, p["video"], p["key"], p["words"], info=p["info"] or None, switch=False)
                entry = TR.words_for(kit, p["video"])
                if not entry or entry.get("key") != p["key"]:
                    say(f"  Talking reel \"{p['name']}\" was not brought: its script could not be kept.")
                    self.problems += 1
                    continue
                _stop_here("after-words")
                got = {}

                def fn(rec, p=p, entry=entry, got=got):
                    if (fname, p["id"]) in talking_marks(rec):
                        return False
                    for k in TR.WORD_FIELDS:
                        rec.pop(k, None)
                    back = None
                    if talking_empty(rec):
                        vid = reels.FIRST_ID
                        if p["as"] != TR.TALK_FIRST:
                            reels.rename(rec, vid, p["as"], TR.TALK_FIRST)
                    else:
                        back = reels.current(rec, TR.TALK_FIRST)
                        name = free_name(p["name"], [v["name"] for v in reels.listed(rec, TR.TALK_FIRST)])
                        vid = reels.new(rec, TR.TALK_LIVE, TR.talk_fresh, TR.TALK_FIRST, TR.TALK_WORD, name)
                    rec["video"], rec["words_of"] = p["video"], TR._entry_id(entry)
                    rec["status"], rec["step"], rec["problem"] = "ready", "", ""
                    for k, v in p["fields"].items():
                        rec[k] = v
                    if p["made"]:
                        rec["made"] = p["made"]
                    rec[MARK] = {"file": fname, "id": p["id"], "when": time.strftime("%Y-%m-%d %H:%M:%S")}
                    got["vid"] = vid
                    if back is not None:
                        reels.switch(rec, back, TR.TALK_LIVE, TR.TALK_FIRST)
                    TR._join(rec, TR.words_for(kit, rec.get("video")))
                    return None
                try:
                    TR.change(kit, fn)
                except reels.Wrong as e:
                    say(f"  Talking reel \"{p['name']}\" was not brought: {e}")
                    self.problems += 1
                    continue
                if got.get("vid"):
                    ours[p["id"]] = got["vid"]
                out.append(("talking", p["id"]))
                self._small_copy(p)
            want = ours.get(self.talk_cur)
            if was_empty and want and want != reels.current(TR._slim(kit), TR.TALK_FIRST):
                def to(rec):
                    for k in TR.WORD_FIELDS:
                        rec.pop(k, None)
                    reels.switch(rec, want, TR.TALK_LIVE, TR.TALK_FIRST)
                    TR._join(rec, TR.words_for(kit, rec.get("video")))
                TR.change(kit, to)
        except (TR.Busy, TR.Unreadable):
            say("  This shoot's talking reel record couldn't be reached just now. What wasn't brought will be on the next run.")
            self.problems += 1
        return out

    def _small_copy(self, p):
        """The small copy the page's player shows: ours, made fresh by video.py (never the older page's). Without
        it the script, the cuts and the timeline are all there and the player is empty."""
        kit = self.kit
        try:
            dst = TR.preview_path(kit, p["key"])
            if dst.is_file():
                return
            hit = TR._plain_videos(kit, TR.TALKING).get(nfc(p["video"]).casefold())
            r = reel_page._video().preview_copy(hit[1], dst) if hit else {"ok": False}
        except Exception:  # noqa: BLE001
            r = {"ok": False}
        if not r.get("ok"):
            say(f"      The small copy that plays on the page could not be made for \"{p['video']}\""
                + (" (not on a PC yet)" if this_computer.WINDOWS else "") + ": the script, the cuts and the photos are "
                "there, and the player stays empty.")


# ---------- the commands ----------

def run(a, doing):
    old, why = old_folder(a.old)
    if old is None:
        say("STOP: " + why + " Nothing was changed.")
        return 2
    found = old_shoots(old)
    if a.shoot:
        want = [w for w in nfc(a.shoot).casefold().split() if w]
        found = {k: v for k, v in found.items() if all(w in nfc(k).casefold() for w in want)}
        if not found:
            say(f"STOP: no older reel or talking reel is kept there for a shoot called \"{a.shoot}\". Nothing was changed.")
            return 2
    if not found:
        say("There are no older reels or talking reels in that folder. Nothing to bring.")
        return 0
    say(("Bringing the older reels into their post kits." if doing else
         "Looking only: nothing is changed. This is what bringing the older reels over would do.")
        + f" The older records, in \"{old.name}\" in \"{old.parent.name}\", are only read.")
    problems = todo = brought = 0
    for name in sorted(found, key=lambda s: nfc(s).casefold()):
        s = Shoot(old, name, found[name], a, doing)
        try:
            if s.kit is None:
                s.tell(doing)
            else:
                s.plan()
                if doing:
                    s.bring()
                else:
                    s.tell(False)
        except (OSError, arrange.Busy, TR.Busy, TR.Unreadable, TR.Stop) as e:
            say(f"  I couldn't finish this shoot just now ({e.__class__.__name__}). Nothing else of it was changed; run it again.")
            s.problems += 1
        except Exception as e:  # noqa: BLE001  (one odd older record must not stop the shoots after it)
            say(f"\n{reel_page.short_name(name)}: I couldn't make sense of this shoot's older records ({e.__class__.__name__}), "
                "so it was left as it is. The other shoots carry on.")
            if doing:                       # `look` writes nothing at all, not even a log line
                TR.log(f"bring_older: {name}: {e.__class__.__name__}: {e}")
            s.problems += 1
        problems += s.problems
        todo += s.todo
        brought += s.brought
    say("")
    if doing:
        say(f"Done: {brought} brought." if not problems else f"Done: {brought} brought; {problems} could not be (see above).")
    elif todo:
        say(f"{todo} can be brought" + (f"; {problems} can't (see above)" if problems else "")
            + ". Nothing was changed. Read this back in plain words, and run `bring` only when they say yes.")
    else:
        say("Nothing to bring" + (f"; {problems} can't be brought (see above)." if problems else ": everything there is here already."))
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description="Bring reels and talking reels made on the older pages into their post kits.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("look", "bring"):
        p = sub.add_parser(name)
        p.add_argument("--from", dest="old", help="the older pages' folder (default: the .studio folder beside Your Content)")
        p.add_argument("--shoot", help="only the shoot whose name holds these words")
        p.add_argument("--photos-unchanged", action="store_true",
                       help="they said no photo was EVER added to or taken out of the shoot on the older pages: when the "
                            "older list of photos isn't there, show each number's photo by name order (not proof)")
        p.add_argument("--names-confirmed", action="store_true",
                       help="bring only: they heard each reel's photo names from `look --photos-unchanged` and said yes, "
                            "those are its photos")
        p.add_argument("--capcut-store", help=argparse.SUPPRESS)
    a = ap.parse_args()
    try:
        return run(a, a.cmd == "bring")
    except KeyboardInterrupt:
        say("Stopped. Run it again to finish; what was already brought stays.")
        return 1
    except Exception as e:  # noqa: BLE001  (plain words, never a Python error, for whoever reads this)
        say(f"STOP: something went wrong that I didn't expect ({e.__class__.__name__}). Run it again; what was already "
            "brought stays, and the older records are untouched.")
        TR.log(f"bring_older: {e.__class__.__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
