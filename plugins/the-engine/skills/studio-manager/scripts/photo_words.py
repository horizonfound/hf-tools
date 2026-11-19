#!/usr/bin/env python3
"""What is in each photo, in words, so search can find it (Nicole's v29, 1.5: "you're not looking for a shoot
name, you're looking for a photo of someone laughing").

NO PHOTO IS EVER TOUCHED OR RENAMED ("I don't want the assistant to rename the photos"). The words are kept
beside the kit, in its hidden folder:

    <kit>/.kit/photo-words.json         {"v": 1, "photos": {"<photo number>": {
                                            "key":      the photo's name-size-time key (arrange._key), so a photo
                                                        exported again is looked at again,
                                            "tags":     ["outdoor", "sky", "people"],   from this computer
                                            "tags_by":  "mac", "tags_at": when,
                                            "unread":   true            only when no picture could be read
                                            "words":    "Mom laughing with the kids at the water",  from your assistant
                                            "words_by": "assistant", "words_at": when,
                                            "words_key": the key of the photo the words were written for}}}
    <kit>/.kit/photo-words.prev.json    the version before, kept on every change

written whole, under a lock of its own in the kit's hidden folder (photo-words.lock). One per post kit. The
vault's list is references (vault.py): a vault photo that is in a shoot's post kit has its words in THAT kit's
file, under its number there; only the photos added to the vault itself are in the vault's own file.

Two writers, two fields:

  * tags, by themselves. Apple's own image classifier (Vision's VNClassifyImageRequest) asked through the Mac's
    scripting (this_computer.mac_javascript), the way faces.py asks where the faces are: on the 520 px small
    copies only (never an original), a dozen a run, the labels Vision is more than TAG_MIN sure of, at most
    TAGS_MOST a photo, plus "one person" / "people" from the faces in it. Nothing leaves the computer. A job of
    its own per kit (`photo_words.py job`), started when a post kit's page is opened or its numbered list is
    made, one kit at a time on this computer; the page follows it at GET /photo-words-state?kit= and shows her
    line, "Getting your photos ready to search: 40 of 72.", while it runs.
    A PC has no Vision: no tags there (this_computer.NO_TAGS_PC), and search goes by the shoot's name and by
    whatever your assistant has described.
  * words, from your assistant, only when asked, from the numbered contact sheets (never photo by photo):
        python3 photo_words.py status "<kit words>"                 how many photos have no description (draws nothing)
        python3 photo_words.py sheets "<kit words>"                 the numbered sheets, and which numbers have none
        python3 photo_words.py describe "<kit words>" --file f.json {"photos": {"12": {"words": "..."}}}: the whole
                                                                    file is checked before anything is saved; twice
                                                                    writes nothing
    A description is for FINDING a photo only. It is never used as a fact in a caption, a note or a hook.

Tests: PHOTO_WORDS_PRETEND is a JSON file {"<photo's file name>": ["tag", ...] | {"tags": [...], "faces": 2} | null}
(a name not in it: looked at, nothing found; null: could not be read), or "none" for a computer with no classifier;
a file that can't be read is a classifier that does not answer. Nothing is run then. And nothing starts by itself
inside a test that did not ask for it (auto()).

Python 3.9, standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
STORE = "photo-words.json"
PREV = "photo-words.prev.json"
LOCK = "photo-words.lock"
JOB = "photo-words-job.json"            # what the page follows while the job runs (state, done, total)
JOB_LOCK = "photo-words-job.lock"       # held by the job for as long as it lives
TURN = "photo-words.lock"               # in the Assistant's own folder: one kit at a time on this computer
TAG_MIN = 0.3                           # a label Vision is less sure of than this is left out
TAGS_MOST = 12                          # at most this many labels a photo
BATCH = 12                              # photos to one run of the classifier (starting a run is the slow part)
WORDS_MAX = 140                         # one plain line, up to this many letters
FILE_MOST = 2000                        # the most photos one describe file may carry
STARTING_FOR = 20.0                     # seconds a job may take to get going before "starting" means it never did
TURN_WAIT = 1800.0                      # seconds a job waits for another kit's job before it gives up
ASK_ABOVE = 300                         # the instructions' line: ask before describing more photos than this
PRETEND = "PHOTO_WORDS_PRETEND"
PAUSE = "STUDIO_PHOTO_WORDS_PAUSE_FOR_TESTS"     # seconds between batches, so a test can watch the count go up
GET_ROUTES = ("/photo-words-state",)
ONE_PERSON, PEOPLE = "one person", "people"

# Hers, word for word (UPDATE-v29.md 1.5: "One plain line on the post kit while it runs").
WORDS = {
    "getting": "Getting your photos ready to search: {done} of {total}.",
}
# Ours, where she has none: drafts for Dustin and Nicole.
OUR_WORDS = {
    "more": "Want search to find more, like \"laughing\" or \"a kiss\"? Copy this into the chat:",
    "line": "Describe my photos for {shoot}",
    "line_vault": "Describe the photos in my vault",
    "copy": "Copy",
    "copied": "Copied. Paste it into the chat.",
    "not_copied": "Couldn't copy that. Select the line and copy it yourself.",
}

# One run for every picture given: what Apple's classifier sees in it, and how many faces. The turn mark is read
# from the file and handed to Vision, as FACES_JS does. Labels come back as Vision spells them ("blue_sky").
TAGS_JS = r"""
ObjC.import('Vision'); ObjC.import('Foundation'); ObjC.import('AppKit'); ObjC.import('CoreImage');
function run(argv) {
  var least = parseFloat(argv[0]), sure = parseFloat(argv[1]), all = [];
  for (var a = 2; a < argv.length; a++) {
    var out = {tags: [], faces: 0, ok: false};
    try {
      var url = $.NSURL.fileURLWithPath(argv[a]);
      var o = 1;
      var ci = $.CIImage.imageWithContentsOfURL(url);
      if (ci && !ci.isNil()) {
        var p = ci.properties;
        if (p && !p.isNil()) { var v = p.objectForKey('Orientation'); if (v && !v.isNil()) o = v.intValue; }
      }
      if (!(o >= 1 && o <= 8)) o = 1;
      var hd = $.VNImageRequestHandler.alloc.initWithURLOrientationOptions(url, o, $());
      var rc = $.VNClassifyImageRequest.alloc.init;
      var rf = $.VNDetectFaceRectanglesRequest.alloc.init;
      out.ok = !!hd.performRequestsError($([rc, rf]), Ref());
      var r = rc.results;
      if (r && !r.isNil()) for (var i = 0; i < r.count; i++) {
        var c = r.objectAtIndex(i);
        if (c.confidence > least) out.tags.push([ObjC.unwrap(c.identifier), c.confidence]);
      }
      var f = rf.results;
      if (f && !f.isNil()) for (var j = 0; j < f.count; j++) if (f.objectAtIndex(j).confidence > sure) out.faces++;
    } catch (err) { out.ok = false; }
    all.push(out);
  }
  return JSON.stringify(all);
}
"""


class Wrong(ValueError):
    """A describe file that can't be taken, in plain words. Nothing was saved."""


def say(msg):
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _arrange():
    import arrange
    return arrange


def _kit():
    import kit as kit_mod
    return kit_mod


# ---------- the classifier ----------

def here():
    """Can this computer look at a photo and say what is in it? A Mac: yes (Vision). A PC: no. In a test, whatever
    PHOTO_WORDS_PRETEND says ("none": a computer with no classifier)."""
    pretend = os.environ.get(PRETEND)
    if pretend:
        return pretend != "none"
    return bool(this_computer.MAC)


def auto():
    """May a job start by itself (a page opened, a list made)? Always, except inside a test that did not ask for
    it: a test runs in a scratch home of its own (STUDIO_HOME set, which a photographer's computer never has, the
    same belt transcribe.py wears) or with STUDIO_NO_WINDOWS_FOR_TESTS, and then only a test that set
    PHOTO_WORDS_PRETEND gets a job. So no test asks the real Vision by accident, and no test's pretend kit gets a
    file it did not expect."""
    if os.environ.get(PRETEND):
        return True
    return not (this_computer.no_windows() or os.environ.get("STUDIO_HOME"))


def clean_tags(labels, faces=0):
    """Labels as they are kept: lower case, underscores as spaces, plain letters and numbers only, each once, at
    most TAGS_MOST, the surest first; then "one person" or "people" from the faces seen."""
    out = []
    pairs = []
    for x in labels or []:
        if isinstance(x, (list, tuple)) and len(x) == 2 and isinstance(x[0], str):
            try:
                pairs.append((x[0], float(x[1])))
            except (TypeError, ValueError):
                continue
        elif isinstance(x, str):
            pairs.append((x, 1.0))
    pairs.sort(key=lambda p: -p[1])
    for label, _sure in pairs:
        t = " ".join(label.replace("_", " ").lower().split())
        if re.fullmatch(r"[a-z0-9][a-z0-9 ]{0,39}", t) and t not in out:
            out.append(t)
        if len(out) >= TAGS_MOST:
            break
    try:
        n = int(faces or 0)
    except (TypeError, ValueError):
        n = 0
    who = ONE_PERSON if n == 1 else PEOPLE if n >= 2 else None
    if who and who not in out:
        out.append(who)
    return out


def classify(items):
    """Ask this computer what is in these pictures, all in one run. items: [(the small copy, the photo's own file
    name)]. A list as long as items: for each, its tags (a list, maybe empty) or None (that picture could not be
    read). None for the whole run when the classifier did not answer at all (a PC, the Mac's scripting saying no,
    a run that took too long): nothing may then be recorded as looked at."""
    items = [(str(p), str(name)) for p, name in items]
    if not items:
        return []
    pretend = os.environ.get(PRETEND)
    if pretend:
        if pretend == "none":
            return None
        try:
            table = json.loads(Path(pretend).read_text(encoding="utf-8"))
            if not isinstance(table, dict):
                return None
        except (OSError, ValueError):
            return None
        out = []
        for _p, name in items:
            got = table.get(name, [])
            if got is None:
                out.append(None)
            elif isinstance(got, dict):
                out.append(clean_tags(got.get("tags"), got.get("faces")))
            else:
                out.append(clean_tags(got if isinstance(got, list) else []))
        return out
    try:
        import faces
        r = this_computer.mac_javascript(TAGS_JS, [TAG_MIN, faces.CONFIDENCE, *[p for p, _ in items]], timeout=30 + 4 * len(items))
        if not r or r[0] != 0:                      # None: a PC. Not 0: the Mac's scripting said no.
            return None
        got = json.loads(r[1])
        if not isinstance(got, list) or len(got) != len(items):
            return None
        return [clean_tags(d.get("tags"), d.get("faces")) if isinstance(d, dict) and d.get("ok") else None for d in got]
    except Exception:  # noqa: BLE001  (a run that took too long, an answer that is not JSON: no answer, never a crash)
        return None


# ---------- the store ----------

def store_path(kit):
    return Path(kit) / ".kit" / STORE


def _entry(e):
    """One photo's entry as it is kept, or None when it is not one."""
    if not isinstance(e, dict) or not isinstance(e.get("key"), str):
        return None
    out = {"key": e["key"]}
    if isinstance(e.get("tags"), list) and isinstance(e.get("tags_at"), str):
        out["tags"] = [t for t in e["tags"] if isinstance(t, str) and t][:TAGS_MOST + 1]
        out["tags_by"] = str(e.get("tags_by") or "mac")
        out["tags_at"] = e["tags_at"]
        if e.get("unread") is True:
            out["unread"] = True
    if isinstance(e.get("words"), str) and e["words"].strip():
        out["words"] = e["words"]
        out["words_by"] = str(e.get("words_by") or "assistant")
        out["words_at"] = str(e.get("words_at") or "")
        out["words_key"] = str(e.get("words_key") or "")
    return out


def _entries(raw):
    """The entries in a store's bytes: {"<number>": entry}, or None when the bytes are not a store."""
    try:
        d = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    photos = d.get("photos") if isinstance(d, dict) else None
    if not isinstance(photos, dict):
        return None
    out = {}
    for k, e in photos.items():
        e = _entry(e)
        if isinstance(k, str) and k.isdigit() and e is not None:
            out[k] = e
    return out


def read(kit):
    """A kit's own photo words: {"<number>": entry}. {} when there are none yet or the file can't be read.
    For READERS (search, a page). A save never starts from this: see update."""
    try:
        return _entries(store_path(kit).read_bytes()) or {}
    except OSError:
        return {}


def update(kit, change):
    """Read the kit's photo words, change them (change(photos) on a copy), and save them whole, as one step under
    the store's own lock. The version before is kept (photo-words.prev.json) first. When nothing is different,
    nothing is written. True when the file was written. Never makes a kit's hidden folder: a kit that is gone
    (renamed, its drive away) raises OSError and gets nothing.

    "Can't read it" is never "it is empty": a store that is there and can't be read this moment (a drive hiccup,
    a refusal, on a PC another program holding it) raises OSError and nothing is written, or every earlier
    description and tag of the shoot would be replaced by the new ones alone. A store that is damaged (it reads,
    and is not a store) is kept beside itself under a dated name, never as the version before, and the save
    starts from the version before (photo-words.prev.json) when that one reads."""
    arrange = _arrange()
    kit = Path(kit)
    with arrange.locked(kit / ".kit" / LOCK):
        p = store_path(kit)
        try:
            was = p.read_bytes()                # an OSError other than "not there" goes to the caller: nothing is written
        except FileNotFoundError:
            was = None
        before = _entries(was) if was is not None else {}
        damaged = before is None
        if damaged:
            try:
                before = _entries(p.with_name(PREV).read_bytes()) or {}
            except FileNotFoundError:
                before = {}
            stamp = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
            tmp = p.with_name(f".{p.stem}.damaged-{stamp}.tmp")
            try:
                tmp.write_bytes(was)
                for i in range(1, 100):         # never over one already kept
                    if this_computer.rename_new(tmp, p.with_name(f"{p.stem}.damaged-{stamp}{'' if i == 1 else f'-{i}'}{p.suffix}")):
                        break
                else:
                    tmp.unlink()                # our own scratch copy
            except BaseException:
                try:
                    tmp.unlink()                # our own scratch copy
                except OSError:
                    pass
                raise
        after = json.loads(json.dumps(before))
        change(after)
        after = {k: e for k, e in ((k, _entry(e)) for k, e in after.items()) if e is not None}
        if after == before and not damaged:
            return False
        if was is not None and not damaged:
            prev = p.with_name(PREV)
            tmp = prev.with_name(f".{prev.name}.{os.getpid()}.tmp")
            try:
                tmp.write_bytes(was)
                this_computer.replace(tmp, prev)
            except BaseException:
                try:
                    tmp.unlink()                # our own scratch copy
                except OSError:
                    pass
                raise
        arrange.write_whole(p, {"v": 1, "photos": {k: after[k] for k in sorted(after, key=int)}})
        return True


def text_of(entry):
    """What search reads of one photo: its tags and its words."""
    if not entry:
        return ""
    return " ".join(list(entry.get("tags") or []) + ([entry["words"]] if entry.get("words") else []))


# ---------- which photos, and whose file each one's words are in ----------

def _home(kit, row):
    """(the kit whose file holds this row's words, the photo's number there), or None. A plain kit: itself and the
    row's number. The vault: a photo from a shoot's post kit is in that kit's file under its number there (one
    level only, a real kit folder beside the vault, never a link); a photo added to the vault itself is in the
    vault's own."""
    kit = Path(kit)
    member = row.get("kit")
    if not isinstance(member, str) or member == "":
        return kit, str(row["n"])
    if "/" in member or "\\" in member or "\x00" in member or member.startswith("."):
        return None
    d = kit.parent / member
    src = row.get("src")
    try:
        if type(src) is not int or src < 1 or d.is_symlink() or not (d / ".kit" / "kit.json").is_file():
            return None
    except OSError:
        return None
    return d, str(src)


def survey(kit):
    """Every photo on the kit's list, against what is kept. {"total", "done", "described", "need", "nowords",
    "stale"}: need is the photos with no tags for the photo as it is now, each (row, where the photo is, its key,
    the kit whose file it goes in, its number there); nowords and stale are the list's own numbers with no words,
    and with words written before the photo was exported again. A photo that can't be reached right now counts
    only if it was looked at before. Reads only."""
    arrange = _arrange()
    kit = Path(kit)
    rec = _kit().load_rec(kit)
    stores = {}
    out = {"total": 0, "done": 0, "described": 0, "need": [], "nowords": [], "stale": []}
    for row in arrange.sheet_rows(kit):
        home = _home(kit, row)
        if home is None:
            continue
        hk, num = home
        if str(hk) not in stores:
            stores[str(hk)] = read(hk)
        e = stores[str(hk)].get(num)
        src = arrange.photo_path(kit, rec, row)
        key = None
        if src is not None:
            try:
                key = arrange._key(src)
            except OSError:
                key = None
        if key is None:
            if e and e.get("tags_at"):
                out["total"] += 1
                out["done"] += 1
                if e.get("words"):
                    out["described"] += 1
            continue
        out["total"] += 1
        if e and e.get("key") == key and e.get("tags_at"):
            out["done"] += 1
        else:
            out["need"].append((row, src, key, hk, num))
        if e and e.get("words"):
            out["described"] += 1
            if e.get("words_key") and e["words_key"] != key:
                out["stale"].append(row["n"])
        else:
            out["nowords"].append(row["n"])
    return out


# ---------- the job ----------

def _job_file(kit):
    return Path(kit) / ".kit" / JOB


def _job_read(kit):
    try:
        d = json.loads(_job_file(kit).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _job_write(kit, **facts):
    try:
        _arrange().write_whole(_job_file(kit), dict(facts, at=time.time()))
    except OSError:
        pass


def _held_by_another(lock_file):
    """Is this lock held by some other program right now? False when it is free or can't be told."""
    try:
        f = open(lock_file, "ab")
    except OSError:
        return False
    try:
        got = this_computer.try_lock(f)
        if got:
            this_computer.unlock(f)
        return got is False
    finally:
        f.close()


def running(kit):
    """Is this kit's job at work (or about to be: just started, not yet holding its lock)?"""
    kit = Path(kit)
    if not (kit / ".kit").is_dir():
        return False
    if _held_by_another(kit / ".kit" / JOB_LOCK):
        return True
    j = _job_read(kit)
    try:
        return j.get("state") == "starting" and time.time() - float(j.get("at") or 0) < STARTING_FOR
    except (TypeError, ValueError):
        return False


def state(kit):
    """What the page follows: {"done", "total", "running", "can", "described"}. While the job runs, its own count
    (cheap); otherwise every photo is looked up afresh."""
    can = here()
    if running(kit):
        j = _job_read(kit)
        done, total = j.get("done"), j.get("total")
        if type(done) is int and type(total) is int and 0 <= done <= total:
            return {"done": done, "total": total, "running": True, "can": can, "described": 0}
        s = survey(kit)
        return {"done": s["done"], "total": s["total"], "running": True, "can": can, "described": s["described"]}
    s = survey(kit)
    return {"done": s["done"], "total": s["total"], "running": False, "can": can, "described": s["described"]}


def start(kit, done=0, total=0):
    """Start the kit's job in a process of its own, so nothing waits on it. False when it is running already or
    could not be started. Whether there is anything to do is the caller's to know (opened)."""
    kit = Path(kit)
    if running(kit):
        return False
    try:
        logs = HOME / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        _job_write(kit, state="starting", done=done, total=total)
        with open(logs / "photo-words.log", "ab") as out:
            this_computer.popen_detached([sys.executable, str(HERE / "photo_words.py"), "job", str(kit)],
                                         stdin=subprocess.DEVNULL, stdout=out, stderr=out)
        return True
    except OSError:
        return False


def opened(kit):
    """A post kit's page was opened, or its numbered list was made: if photos have no tags yet and this computer
    can make them, start the job. Never raises; True when a job was started."""
    try:
        if not auto() or not here() or running(kit):
            return False
        s = survey(kit)
        if not s["need"]:
            return False
        return start(kit, s["done"], s["total"])
    except (Exception, SystemExit):  # noqa: BLE001
        return False


def run_job(kit):
    """The job itself. Exit 0: every photo that can be looked at has been (or another job of this kit is already at
    it). 1: the classifier stopped answering part way; what was looked at is kept, the rest is tried next time."""
    arrange = _arrange()
    kit = Path(kit)
    if not (kit / ".kit" / "kit.json").is_file():
        return 2
    try:
        mine = open(kit / ".kit" / JOB_LOCK, "ab")
    except OSError:
        return 2
    turn = None
    try:
        if this_computer.try_lock(mine) is False:
            return 0                                # this kit's job is already running
        s = survey(kit)
        done, total = s["done"], s["total"]
        _job_write(kit, state="working", done=done, total=total, pid=os.getpid())
        if not s["need"] or not here():
            _job_write(kit, state="done", done=done, total=total)
            return 0
        # one kit at a time on this computer
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            turn = open(HOME / TURN, "ab")
        except OSError:
            turn = None
        end = time.time() + TURN_WAIT
        while turn is not None:
            got = this_computer.try_lock(turn)
            if got or got is None:
                break
            if time.time() > end:
                _job_write(kit, state="stopped", done=done, total=total)
                return 1
            time.sleep(0.5)
        rec = _kit().load_rec(kit)
        try:
            pause = float(os.environ.get(PAUSE) or 0)
        except ValueError:
            pause = 0.0
        need = s["need"]
        for i in range(0, len(need), BATCH):
            batch = need[i:i + BATCH]
            look, results = [], {}
            for j, (row, src, key, _hk, _num) in enumerate(batch):
                copy = None
                try:
                    got = arrange.make_one(kit, row, arrange.SIZES["s"], src, rec)
                    if got == "later":              # a PC only: something holds the copy; not looked at this time
                        results[j] = "later"
                        continue
                    p = arrange.preview_file(kit, row, arrange.SIZES["s"], src)
                    copy = p if p.is_file() else None
                except OSError:
                    copy = None
                if copy is None:
                    results[j] = None               # no picture of this photo can be made: looked at, nothing read
                else:
                    look.append((j, copy, src.name))
            if look:
                got = classify([(p, name) for _j, p, name in look])
                if got is None:                     # the classifier did not answer: record nothing for these
                    _job_write(kit, state="stopped", done=done, total=total)
                    return 1
                for (j, _p, _name), tags in zip(look, got):
                    results[j] = tags
            by_home = {}
            for j, (row, _src, key, hk, num) in enumerate(batch):
                if results.get(j, "later") == "later":
                    continue
                by_home.setdefault(str(hk), (hk, []))[1].append((num, key, results[j]))
            at = now_iso()
            for hk, found in by_home.values():
                def change(photos, found=found):
                    for num, key, tags in found:
                        e = dict(photos.get(num) or {})
                        e.update(key=key, tags=tags or [], tags_by="mac", tags_at=at)
                        e.pop("unread", None)
                        if tags is None:
                            e["unread"] = True
                        photos[num] = e
                try:
                    update(hk, change)
                except (OSError, arrange.Busy):
                    pass                            # that kit is away or busy: its photos are tried next time
            done = min(total, done + sum(1 for j in range(len(batch)) if results.get(j, "later") != "later"))
            _job_write(kit, state="working", done=done, total=total, pid=os.getpid())
            if pause:
                time.sleep(pause)
        s = survey(kit)
        _job_write(kit, state="done", done=s["done"], total=s["total"])
        return 0
    finally:
        for f in (turn, mine):
            if f is not None:
                try:
                    this_computer.unlock(f)
                except (OSError, ValueError):
                    pass
                f.close()


# ---------- the post kit page's part ----------

CSS = """
.pw{max-width:760px;margin:0 0 1.1rem}
.pw [hidden]{display:none!important}
.pw .getting{font-size:13.5px;color:var(--ink-2);margin:0;display:flex;align-items:center;gap:.5rem}
.pw .getting::before{content:'';width:8px;height:8px;border-radius:50%;background:var(--coral,#D4643F);flex:none;animation:pwb 1.2s ease-in-out infinite}
@keyframes pwb{0%,100%{opacity:.25}50%{opacity:1}}
@media (prefers-reduced-motion:reduce){.pw .getting::before{animation:none}}
.pw .more p{font-size:13px;color:var(--ink-2);margin:0 0 .35rem}
.pw .copyrow{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem}
.pw .copyrow code{font:500 13px/1.3 var(--sans);background:#fff;border:1px solid var(--line);border-radius:8px;padding:.4rem .65rem;user-select:all}
.pw .copyrow .went{margin:0;min-height:0}
"""

SCRIPT = r"""
(function(){
  var box = document.getElementById('pw'); if (!box) return;
  var W = JSON.parse(document.getElementById('pw-words').textContent);
  var kit = document.body.getAttribute('data-kit');
  var getting = document.getElementById('pwGetting'), more = document.getElementById('pwMore'), went = document.getElementById('pwWent');
  var timer = null;
  function show(s){
    if (s && s.running && s.total > 0){
      getting.textContent = W.getting.replace('{done}', s.done).replace('{total}', s.total);
      getting.hidden = false; more.hidden = true; return;
    }
    getting.hidden = true; getting.textContent = '';
    var ready = s && s.total > 0 && s.described < s.total && (!s.can || s.done >= s.total);
    more.hidden = !ready;
  }
  function ask(){
    fetch('/photo-words-state?kit=' + encodeURIComponent(kit), {cache: 'no-store'}).then(function(r){ return r.ok ? r.json() : null; }).then(function(s){
      if (!s || !s.ok){ show(null); return; }
      show(s);
      if (s.running) timer = setTimeout(ask, 1500);
    }).catch(function(){ show(null); });
  }
  document.getElementById('pwCopy').addEventListener('click', function(){
    var text = document.getElementById('pwLine').textContent, ok = false;
    try {
      var t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', ''); t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select(); ok = document.execCommand('copy'); document.body.removeChild(t);
    } catch (e) { ok = false; }
    if (ok) { went.textContent = W.copied; return; }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function(){ went.textContent = W.copied; }, function(){ went.textContent = W.not_copied; });
    else went.textContent = W.not_copied;
  });
  ask();
})();
"""


def page_parts(kit, rec):
    """What the post kit page adds for this: (the markup, the styles, what goes before </body>). Her line while the
    job runs; once the tags are done, our quiet line with the words to copy into the chat; on a PC, the PC line in
    its place. Every word reaches the page as text."""
    import html as html_mod
    vault = isinstance(rec, dict) and rec.get("vault") is True
    name = str(rec.get("name") or Path(kit).name) if isinstance(rec, dict) else Path(kit).name
    line = OUR_WORDS["line_vault"] if vault else OUR_WORDS["line"].format(shoot=name)
    more = OUR_WORDS["more"] if here() else this_computer.NO_TAGS_PC
    words = {"getting": WORDS["getting"], "copied": OUR_WORDS["copied"], "not_copied": OUR_WORDS["not_copied"]}
    markup = ("<div class='pw' id='pw'><p class='getting' id='pwGetting' role='status' hidden></p>"
              f"<div class='more' id='pwMore' hidden><p>{html_mod.escape(more)}</p>"
              f"<div class='copyrow'><code id='pwLine'>{html_mod.escape(line)}</code>"
              f"<button class='go small' type='button' id='pwCopy'>{html_mod.escape(OUR_WORDS['copy'])}</button>"
              "<span class='went' id='pwWent' role='status'></span></div></div></div>")
    tail = ("<script type='application/json' id='pw-words'>"
            + json.dumps(words, ensure_ascii=True).replace("<", "\\u003c") + f"</script><script>{SCRIPT}</script>")
    return markup, CSS, tail


# ---------- the route ----------

def _answer(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def handle_get(handler, path, query):
    """GET /photo-words-state?kit=<kit folder>: only for this server's own pages, a kit found by its exact folder
    name in Your Content. Numbers and yes or no only. Whatever goes wrong, the server answers."""
    try:
        arrange = _arrange()
        if not arrange.our_host(handler) or (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            return _answer(handler, {"ok": False}, 403)
        try:
            q = parse_qs(query or "", keep_blank_values=True)
        except ValueError:
            return _answer(handler, {"ok": False}, 404)
        names = q.get("kit") or []
        kit = arrange.kit_by_name(names[0]) if len(names) == 1 else None
        if path != "/photo-words-state" or kit is None or set(q) - {"kit"}:
            return _answer(handler, {"ok": False}, 404)
        return _answer(handler, dict(state(kit), ok=True))
    except (Exception, SystemExit) as e:  # noqa: BLE001
        try:
            print(f"photo_words: GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}", flush=True)
        except (BrokenPipeError, OSError):
            pass
        try:
            _answer(handler, {"ok": False}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- your assistant's descriptions ----------

def spans(nums):
    """1, 2, 3, 7 as "1 to 3, 7"."""
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if j == i else f"{nums[i]} to {nums[j]}" if j > i + 1 else f"{nums[i]}, {nums[j]}")
        i = j + 1
    return ", ".join(out)


def _s(n, one="photo", many="photos"):
    return f"{n:,} {one if n == 1 else many}"


def _own_rows(kit):
    """The rows whose words are in this kit's own file: every row of a plain kit; in the vault, the photos added
    to the vault itself. And the vault's other rows, by the post kit each is in."""
    own, others = [], {}
    for row in _arrange().sheet_rows(kit):
        member = row.get("kit")
        if isinstance(member, str) and member != "":
            others.setdefault(member, []).append(row)
        else:
            own.append(row)
    return own, others


def check_words(d, own, others=None):
    """The describe file, checked whole before a byte is written: {"photos": {"<number>": {"words": "..."}}}, every
    number a photo on this kit's list, every description one plain line of at most WORDS_MAX letters, and nothing
    else. {"<number>": words}."""
    others = others or {}
    if not isinstance(d, dict) or not isinstance(d.get("photos"), dict) or not d["photos"] or set(d) - {"photos"}:
        raise Wrong('the file needs {"photos": {"<photo number>": {"words": "..."}}}, one short description for each photo.')
    if len(d["photos"]) > FILE_MOST:
        raise Wrong(f"that's more than {FILE_MOST:,} photos in one file.")
    known = {row["n"] for row in own}
    elsewhere = {row["n"]: (member, row.get("src")) for member, rows in others.items() for row in rows}
    out = {}
    for k, w in d["photos"].items():
        if not isinstance(k, str) or not re.fullmatch(r"[1-9][0-9]{0,6}", k):
            raise Wrong(f"\"{str(k)[:40]}\" isn't a photo number (they are the numbers on the sheet, like 12).")
        n = int(k)
        if n in elsewhere:
            member, src = elsewhere[n]
            raise Wrong(f"photo {n} is in the post kit \"{member}\" (its number there is {src}): describe it there, "
                        f"with photo_words.py sheets \"{member}\".")
        if n not in known:
            raise Wrong(f"there is no photo numbered {n} on this kit's list. Run sheets again and use the numbers it shows.")
        if not isinstance(w, dict):
            raise Wrong(f"photo {n} needs {{\"words\": \"...\"}}.")
        if set(w) - {"words"}:
            raise Wrong(f"photo {n} has a field I don't know ({', '.join(sorted(set(w) - {'words'}))[:60]}). Each photo takes \"words\" only.")
        words = w.get("words")
        if not isinstance(words, str) or not words.strip():
            raise Wrong(f"photo {n} needs its words: one short plain line of what is in it.")
        if "\n" in words.strip() or "\r" in words.strip():
            raise Wrong(f"the words for photo {n} run over more than one line: one short line.")
        words = " ".join(words.split())
        if "/" in words or "\\" in words or any(ord(c) < 32 or ord(c) == 127 for c in words):
            raise Wrong(f"the words for photo {n} have a slash or a mark that isn't plain words. Plain words only, never a file's name or place.")
        if len(words) > WORDS_MAX:
            raise Wrong(f"the words for photo {n} are longer than {WORDS_MAX} letters ({len(words)}): keep it to one short line.")
        out[k] = words
    return out


def describe(kit, file):
    """Save your assistant's descriptions from a file. (exit code, lines to say)."""
    arrange = _arrange()
    try:
        d = json.loads(Path(file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return 2, [f"STOP: couldn't read the file ({e.__class__.__name__}). Nothing was saved."]
    own, others = _own_rows(kit)
    try:
        words = check_words(d, own, others)
    except Wrong as e:
        return 2, [f"STOP: {e} Nothing was saved."]
    rec = _kit().load_rec(kit)
    keys = {}
    for row in own:
        if str(row["n"]) in words:
            src = arrange.photo_path(kit, rec, row)
            try:
                keys[str(row["n"])] = arrange._key(src) if src is not None else ""
            except OSError:
                keys[str(row["n"])] = ""
    at = now_iso()
    changed = []

    def change(photos):
        for k, text in words.items():
            e = dict(photos.get(k) or {})
            key = keys.get(k) or e.get("key") or ""
            if e.get("words") == text and (not keys.get(k) or e.get("words_key") == keys[k]):
                continue
            if not e.get("key"):
                e["key"] = key
            e.update(words=text, words_by="assistant", words_at=at, words_key=key)
            photos[k] = e
            changed.append(int(k))
    try:
        wrote = update(kit, change)
    except arrange.Busy:
        return 2, ["STOP: this kit's photo words are being written right now. Try again in a moment. Nothing was saved."]
    except OSError as e:
        return 2, [f"STOP: couldn't save ({e.__class__.__name__}). Is the drive plugged in? Nothing was saved."]
    if not wrote:
        return 0, [f"Every one of these {_s(len(words), 'description', 'descriptions')} was already saved. Nothing was written."]
    same = len(words) - len(changed)
    return 0, [f"Saved {_s(len(changed), 'description', 'descriptions')}" + (f" ({same} already the same)" if same else "")
               + ". No photo was touched or renamed. Search finds them now."]


def status_lines(kit):
    """What `status` says: how many photos have no description, here and (for the vault) in each post kit."""
    kit = Path(kit)
    rec = _kit().load_rec(kit)
    s = survey(kit)
    lines = []
    if isinstance(rec, dict) and rec.get("vault") is True:
        own, others = _own_rows(kit)
        own_n = {r["n"] for r in own}
        missing_own = [n for n in s["nowords"] if n in own_n]
        todo = []
        for member in sorted(others):
            ns = {r["n"] for r in others[member]}
            miss = [n for n in s["nowords"] if n in ns]
            if miss:
                todo.append((member, len(miss), len(ns)))
        total = len(missing_own) + sum(m for _, m, _ in todo)
        lines.append(f"In the vault: {_s(s['total'])}, {total:,} with no description yet"
                     + (f", in {_s(len(todo), 'post kit', 'post kits')}" + (" and the vault's own photos" if missing_own else "") if todo else "") + ".")
        for member, miss, n in todo:
            lines.append(f"  {member}: {miss:,} of {_s(n)} with no description  ->  photo_words.py sheets \"{member}\"")
        if missing_own:
            lines.append(f"  Added to the vault itself: {_s(len(missing_own))} with no description (numbers {spans(missing_own)})"
                         f"  ->  photo_words.py sheets \"{kit.name}\"")
        if total > ASK_ABOVE:
            lines.append(f"That is more than {ASK_ABOVE}: say how many, and ask before describing them all.")
    else:
        lines.append(f"{_s(s['total'])} on the list, {len(s['nowords']):,} with no description yet"
                     + (f" (numbers {spans(s['nowords'])})" if s["nowords"] else "") + ".")
    if s["stale"]:
        lines.append(f"Described before the photo was exported again (worth another look): {spans(s['stale'])}.")
    if not here():
        lines.append("NOTE: " + this_computer.NO_TAGS_PC.split(" To have them described")[0])
    elif s["need"]:
        lines.append(f"This computer's own tags: {s['done']:,} of {s['total']:,} photos done so far.")
    return lines


# ---------- the commands ----------

def main():
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "sheets", "state", "tag"):
        sub.add_parser(name).add_argument("words")
    de = sub.add_parser("describe")
    de.add_argument("words")
    de.add_argument("--file", required=True)
    sub.add_parser("job").add_argument("kit")           # the Assistant's own: started by a page or a list being made
    a = ap.parse_args()
    if a.cmd == "job":
        try:
            return run_job(Path(a.kit))
        except (Exception, SystemExit) as e:  # noqa: BLE001
            say(f"{now_iso()} photo words job stopped: {e.__class__.__name__}: {str(e)[:200]}")
            _job_write(Path(a.kit), state="stopped", done=0, total=0)
            return 1
    try:
        import fresh
        fresh.announce()
    except Exception:  # noqa: BLE001
        pass
    kit_mod = _kit()
    kit = kit_mod.find_kit(a.words)
    if a.cmd == "state":
        say(json.dumps(state(kit)))
        return 0
    if a.cmd == "tag":
        # this computer's own tags, now, in this command (what the job does in the background)
        if not here():
            say("NOTE: " + this_computer.NO_TAGS_PC.split(" To have them described")[0])
            return 3
        code = run_job(kit)
        s = survey(kit)
        say(f"This computer's own tags: {s['done']:,} of {_s(s['total'])} done." + ("" if code == 0 else " It stopped part way; run it again."))
        return code
    if a.cmd == "status":
        for line in status_lines(kit):
            say(line)
        return 0
    if a.cmd == "sheets":
        code = kit_mod.sheet(kit)                       # the numbered contact sheets, 48 photos to a sheet
        if code != 0:
            return code
        for line in status_lines(kit):
            say(line)
        say("Describe from the sheets, never photo by photo. Then save them with:  photo_words.py describe \""
            + kit.name + "\" --file words.json   ({\"photos\": {\"12\": {\"words\": \"...\"}}}, one plain line each, up to "
            + str(WORDS_MAX) + " letters)")
        return 0
    if a.cmd == "describe":
        code, lines = describe(kit, a.file)
        for line in lines:
            say(line)
        return code
    return 2


if __name__ == "__main__":
    sys.exit(main())
