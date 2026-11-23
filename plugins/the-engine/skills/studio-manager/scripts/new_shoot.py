#!/usr/bin/env python3
"""+ A new shoot (Nicole's v30, section 4): a folder of finished photos becomes a post kit, with no chat.

The home page's four tiles (Reels, Carousels, Stories, Captions) ask "Which shoot do you want to make it from?".
"+ A new shoot" opens the computer's own folder picker; this script then makes that folder's post kit and the page
lands on the page that was tapped (the reel page, the carousel designer, the stories designer, the words page),
not on the post kit. It is the chat's "make my posts" for one folder, done by the page:

    a picked folder is ONE shoot, named for the folder (posts.date_name, as `kit.py start --folder` names it) in their
    folder pattern (posts.folder_name), dated by its first photo;
    only finished photos are copied (JPEG, HEIC, PNG, WebP: posts.PHOTO), every one by posts.copy_checked, the
    backup's way (a hash while writing, a partial name, put in place, read back and compared); RAW files, TIFFs,
    Photoshop files, catalogs and videos are left where they are;
    COPIED, never moved: the folder they picked is only read;
    never over a file: a name already in the kit's Photos is compared, never replaced; two photos of the same name
    from two subfolders keep their subfolder's name in front (as posts.plan does), and a name still taken gets a
    number;
    the log first: <the Assistant folder>/.studio/new-shoots.json says what will be copied where before the first
    byte is written, and what was copied, with each copy's hash, as it goes;
    safe to run twice: the same folder picked again goes back to the shoot it made (photos already there are left
    as they are, new ones are added), never a second shoot; a run cut off part way is finished by the next;
    a name clash stops it in plain words: a folder of that name already in Your Content that this did not make;
    then the kit record (.kit/kit.json) and its numbered list (kit.sheet, the list only: the contact sheets are
    drawn when the chat asks for them, with the numbers kept).

Commands (the page server runs `make` detached; a person may run either by hand):
    new_shoot.py make "<folder>" [--for reel|carousel|stories|captions] [--job]
    new_shoot.py status                     what the page follows, as JSON

What the page follows is ~/.studio/new-shoot-job.json: {state: working | done | stopped, words, done, of, kit, go}.
Never a path: `kit` is the post kit's folder name, `go` the page addresses for it.
"""
import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import posts  # noqa: E402
import studio_file  # noqa: E402
import this_computer  # noqa: E402

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JOB = HOME / "new-shoot-job.json"
LOCK = HOME / "new-shoot.lock"
LOG_NAME = "new-shoots.json"            # in the Assistant folder's hidden .studio, beside the drop box's log
MAKES = ("reel", "carousel", "stories", "captions")
SAVE_EVERY = 10                         # the log is saved after this many copies (and at every stop)
NAMES_MOST = 500                        # "IMG_0001 (500).jpg": past that, a photo is a problem, not a copy
DATE_READS = 200                        # photos read for the shoot's date (the first one's date names the folder)
ROOM_SPARE = 1 << 30                    # 1 GB left free on the drive after the copy (review, Nov 21)

# Ours, every one a draft for Dustin and Nicole. The page shows `words`; never a path.
WORDS = {
    "starting": "Looking at the photos in that folder…",
    "working": "Copying {n} of {of}…",
    "numbering": "Getting your post kit ready…",
    "done": "Done. Opening it now…",
    "none": "No finished photos (JPEGs) in that folder. Nothing was copied.",
    "no_folder": "I can't see that folder right now. Nothing was copied.",
    "inside": "That folder is already in your Assistant folder. Pick its shoot from Your shoots instead.",
    "holds": "That folder holds your Assistant folder. Pick the folder your finished photos were exported to.",
    "would_hold": "Your Assistant folder will be made in that folder, so it can't be a shoot itself. Pick the folder your finished photos were exported to.",
    "clash": "There's already a shoot called \"{name}\" in Your Content. Nothing was copied. Rename that folder, or tell the Assistant what to call this one.",
    "unplugged": "Your Assistant folder isn't there right now. Check that its drive is plugged in, then try again.",
    "no_place": "There's no place for your Assistant folder yet. Ask the Assistant to set one up.",
    "held": "Something stopped the copy part way: {why}. {n} of {of} photos are in, each one checked. Nothing is lost and your originals weren't moved; pick the same folder again to finish.",
    "mismatch": "{n} photo{s} did not match the original after copying, so {they} not in your shoot. Your originals weren't moved. Pick the same folder again to try again, or tell the Assistant.",
    "too_many_names": "{name} couldn't be given a name of its own in the shoot. Nothing was written over. Tell the Assistant.",
    "unnumbered": "Your photos are in, but I couldn't get the post kit ready. Tell the Assistant.",
    "busy": "A shoot is being copied in right now. One moment.",
    "room": "There isn't room for these photos on the drive your Assistant folder is on: they need about {need}, and {free} is free. Nothing was copied.",
    "stopped": "The copy stopped before it finished. Nothing is lost; pick the same folder again to finish.",
}


class Trouble(Exception):
    """A stop in plain words (the page shows them as they are)."""


def say(msg):
    try:
        print(msg, flush=True)
    except (BrokenPipeError, OSError, ValueError):
        pass


def _s(n):
    return "" if n == 1 else "s"


def _json(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_whole(path, obj):
    """Whole or not at all: a scratch name of this process's own, then put in place."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()            # our own scratch copy, never the real file
        except OSError:
            pass
        raise


# ---------- where each tile lands ----------

def _words_pages(q):
    """The words page's two tabs for a kit (q: its folder name, already in an address). Captions asks "a reel or a
    carousel?" first (Nicole, Nov 22) and lands on the one they chose; "captions" alone stays the Reel tab (the
    chat's `make --for captions`, a page that does not ask)."""
    return {"captions": f"/words.html?kit={q}&piece=reel", "captions_reel": f"/words.html?kit={q}&piece=reel",
            "captions_carousel": f"/words.html?kit={q}&piece=carousel"}


def go(kit_folder):
    """The pages a kit's tiles land on, the addresses the post kit page itself uses: the reel page's chooser
    (kit.reel_door), the carousel designer and the stories designer (kit.design_door), the words page (its Reel or
    its Carousel tab, as they answer)."""
    import kit as kit_mod
    q = quote(kit_folder, safe="")
    return dict({"reel": kit_mod.reel_door(kit_folder), "carousel": kit_mod.design_door(kit_folder),
                 "stories": kit_mod.design_door(kit_folder, stories=True)}, **_words_pages(q))


def vault_go(vault_folder):
    """My vault (her section 4): its own reel page for Reels, its post kit page for Carousels and Stories, and for
    Captions its own words page (the vault's post kit page links the same one, so it is a page the vault has), on
    the tab they chose."""
    q = quote(vault_folder, safe="")
    kit_page = "/content/" + q + "/Post%20kit.html"
    return dict({"reel": "/reel.html?kit=" + q, "carousel": kit_page, "stories": kit_page}, **_words_pages(q))


# ---------- the Assistant folder ----------

def home_place():
    """Where an Assistant folder goes when there is none yet and a photographer picks + A new shoot (the first time
    the Assistant is opened, say): on the drive their photos go to (the Studio File's), else in Pictures on this
    computer. Never a drive nobody named. None when there is neither."""
    sess = (studio_file.load().get("drives") or {}).get("session")
    try:
        if sess and Path(sess).is_dir():
            return Path(sess)
    except OSError:
        pass
    pics = this_computer.known_folder("Pictures")
    try:
        return pics if pics.is_dir() else None
    except OSError:
        return None


def where_home():
    """The Assistant folder, or where it WILL be made when there is none yet (home_place), WITHOUT making anything:
    (folder, there_already). The folder they picked is checked against it, and its photos found, before a folder
    is made or the Studio File changed (review, Nov 21: a brand-new Assistant used to be made first, so a folder
    with no photos left an Assistant folder behind, and picking Pictures was then refused for holding it)."""
    h = posts.home()
    if h is not None:
        try:
            ok = h.is_dir()
        except OSError:
            ok = False
        if not ok:
            raise Trouble(WORDS["unplugged"])
        return h, True
    place = home_place()
    if place is None:
        raise Trouble(WORDS["no_place"])
    return place / posts.HOME_NAME, False


def ensure_home():
    """The Assistant folder, made where home_place says when there is none yet. (folder, made_now)."""
    h, there = where_home()
    if there:
        return posts.need_home(), False
    return posts.setup(home_path=str(h)), True


def _inside(child, parent):
    """Is `child` the folder `parent` or inside it? Asked of the drive itself (the same file on disk, os.path.samefile,
    up `child`'s folders), never of the spelling: most drives ignore capitals and how an accent is written, so
    ".../YOUR CONTENT/Beach" typed in the chat is inside Your Content (review, Nov 21: the spelling was compared, and a
    post kit's own Photos folder in capitals became a new shoot). A `child` not made yet is inside when the nearest
    folder of it that is there is; a `parent` that is not there holds nothing."""
    try:
        c = Path(child).resolve()
        par = Path(parent).resolve()
        if not par.exists():
            return False
        while not c.exists():
            if c.parent == c:
                return False
            c = c.parent
        for a in [c] + list(c.parents):
            try:
                if os.path.samefile(a, par):
                    return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def refusal(h, src, there=True):
    """Why this folder can't be a new shoot, as a key of WORDS, or None when it can. Checked before anything is
    read: a folder that is not there; the Assistant's own Your Content or records (a shoot already there is picked
    from the list); a folder that holds the Assistant folder (a whole drive: it would copy the Assistant's own
    shoots back into it). The drop box is fine: it is theirs."""
    src = Path(src)
    try:
        if not src.is_dir():
            return "no_folder"
    except OSError:
        return "no_folder"
    if _inside(src, h / posts.CONTENT_NAME) or _inside(src, h / ".studio"):
        return "inside"
    if _inside(h, src):
        return "holds" if there else "would_hold"
    return None


# ---------- the plan ----------

def finished_photos(src):
    """The finished photos under the folder they picked (posts.walk: hidden files, Lightroom catalogs and Photos
    libraries skipped), as paths relative to it, in name order."""
    return [rel for rel in posts.walk(src) if posts.kind(rel) == "photo"]


def _fold(name):
    """A name as a drive that ignores capitals (and how an accent is spelled) sees it."""
    return unicodedata.normalize("NFC", name).casefold()


def _listing(folder):
    try:
        return set(os.listdir(folder))
    except OSError:
        return set()


def _listed(listing, name):
    """The name as the folder's listing spells it, or None: the same name however its accents are written and
    whatever its capitals, as most drives see it (a Mac's HFS+ drive, like Big Kahuna, stores "Café" decomposed
    whatever spelling it was given; review, Nov 21: the exact spelling was compared, so the same accented folder
    picked again stopped as a name clash with its own shoot)."""
    want = _fold(name)
    for n in sorted(listing):
        if _fold(n) == want:
            return n
    return None


def _free_name(name, listing):
    """A name not yet in the folder (any capitals, any accent spelling): the name itself, else " (2)" and on."""
    taken = {_fold(n) for n in listing}
    stem, ext = os.path.splitext(name)
    cand, i = name, 2
    while _fold(cand) in taken:
        if i > NAMES_MOST:
            raise Trouble(WORDS["too_many_names"].format(name=name))
        cand, i = f"{stem} ({i}){ext}", i + 1
    return cand


def _size(n):
    return f"{n / (1 << 30):.1f} GB" if n >= 1 << 30 else f"{max(1, round(n / (1 << 20)))} MB"


def _room(where, need):
    """Stop before the first copy when the drive can't hold it with ROOM_SPARE left over (a whole drive or a
    year of exports picked by mistake would otherwise fill it photo by photo). A drive that can't say is let be."""
    free = this_computer.free_bytes(where)
    if free is not None and need + ROOM_SPARE > free:
        raise Trouble(WORDS["room"].format(need=_size(need), free=_size(free)))


def names_for(rels, before, on_disk=()):
    """The name each photo takes in the kit's flat Photos folder: {rel: name}. `before` (from an earlier run) is kept
    as it was, and a name already in the folder (`on_disk`: one they put there themselves) is never taken. A new photo
    takes its own name; two of one name from two subfolders keep their subfolder's name in
    front (posts.plan's way); a name still taken (any capitals: most drives ignore them) gets " (2)" and on."""
    out = {r: n for r, n in before.items() if r in set(rels)}
    taken = {_fold(n) for n in out.values()} | {_fold(n) for n in on_disk}     # a file put there by hand keeps its name
    count = {}
    for r in rels:
        if r not in out:
            count[_fold(Path(r).name)] = count.get(_fold(Path(r).name), 0) + 1
    for r in rels:
        if r in out:
            continue
        name = Path(r).name
        if (count.get(_fold(name), 0) > 1 or _fold(name) in taken) and "/" in r:
            name = r.rsplit("/", 1)[0].replace("/", "_") + "_" + name
        stem, ext = os.path.splitext(name)
        cand, i = name, 2
        while _fold(cand) in taken:
            if i > NAMES_MOST:
                raise Trouble(WORDS["too_many_names"].format(name=Path(r).name))
            cand, i = f"{stem} ({i}){ext}", i + 1
        out[r] = cand
        taken.add(_fold(cand))
    return out


def shoot_date(src, rels):
    """The first photo's date (what the camera wrote), else the oldest file time: ISO text."""
    import exif_read
    taken = []
    for r in rels[:DATE_READS]:
        try:
            t = (exif_read.read(src / r) or {}).get("taken")
        except Exception:  # noqa: BLE001  (one odd photo never stops the shoot)
            t = None
        if t:
            taken.append(t)
    if taken:
        return min(taken)
    times = []
    for r in rels[:DATE_READS]:
        try:
            times.append((src / r).stat().st_mtime)
        except OSError:
            pass
    return datetime.fromtimestamp(min(times) if times else datetime.now().timestamp()).isoformat(timespec="seconds")


# ---------- the log ----------

def log_path(h):
    return h / ".studio" / LOG_NAME


def read_log(h):
    d = _json(log_path(h))
    runs = d.get("runs") if isinstance(d.get("runs"), list) else []
    return {"runs": [r for r in runs if isinstance(r, dict) and isinstance(r.get("kit"), str) and isinstance(r.get("moves"), list)]}


def write_log(h, log):
    _write_whole(log_path(h), log)
    try:
        posts.hide(h / ".studio")
    except Exception:  # noqa: BLE001
        pass


def earlier_run(h, src, log):
    """The run that made a shoot from this very folder before, when its shoot is still in Your Content (the exact
    name in the listing). Newest first."""
    content = h / posts.CONTENT_NAME
    names = _listing(content)
    where = str(Path(src).resolve())
    for run in reversed(log["runs"]):
        if not this_computer.same_place(run.get("from", ""), where):
            continue
        spelled = _listed(names, run["kit"])
        if spelled is not None and (content / spelled).is_dir():
            run["kit"] = spelled                    # as the drive spells it (accents), so every path below is exact
            return run
    return None


# ---------- the job record the page follows ----------

def job_write(**facts):
    try:
        _write_whole(JOB, dict(facts, pid=os.getpid(), when=datetime.now().isoformat(timespec="seconds")))
    except OSError:
        pass                        # the page's progress line is a courtesy; the copy itself never waits on it


def job_write_pid(pid):
    """The page server's own, right after it starts the job: the job's number, so a job that died before its first
    line is seen as stopped and never as working for ever."""
    d = _json(JOB)
    if d.get("state") == "working" and not d.get("of"):
        try:
            _write_whole(JOB, dict(d, pid=pid))
        except OSError:
            pass


def _alive(pid):
    """Is the job's program still running? On a Mac the page server started it, so once it has ended it stays a
    "zombie" until it is waited for, and asking with signal 0 says yes for ever (review, Nov 21: a job that was
    killed showed "Copying..." for ever and + A new shoot answered "One moment" until the server restarted). So a
    program of ours that has ended is waited for here; anyone else's is asked as before."""
    if not this_computer.WINDOWS and type(pid) is int and pid > 0:
        try:
            got, _ = os.waitpid(pid, os.WNOHANG)    # pc-ok: a Mac (and Linux) only, a PC is asked below
            if got == pid:
                return False
        except ChildProcessError:
            pass                                    # not ours to wait for
        except OSError:
            pass
    return this_computer.still_running(pid)


def job():
    """What the page follows: {state: none | working | done | stopped, words, done, of, kit, go}. A job whose process
    is gone while its record still says working is "stopped" (picking the same folder again finishes it)."""
    d = _json(JOB)
    state = d.get("state") if d.get("state") in ("working", "done", "stopped") else "none"
    out = {"state": state, "words": str(d.get("words") or ""), "done": d.get("done") or 0, "of": d.get("of") or 0}
    if state == "working" and _alive(d.get("pid")) is False:
        out.update(state="stopped", words=WORDS["stopped"])
    if state == "done" and isinstance(d.get("kit"), str):
        out["kit"] = d["kit"]
        out["go"] = go(d["kit"])
    return out


# ---------- making it ----------

def make(folder, progress=None):
    """Make a post kit from one folder of finished photos (see the top of this file). Returns the kit folder.
    Raises Trouble with plain words for every stop."""
    import kit as kit_mod
    progress = progress or (lambda **k: None)
    h, there = where_home()                         # nothing is made until the folder is known to be a shoot
    src = Path(folder).expanduser()
    no = refusal(h, src, there)
    if no:
        raise Trouble(WORDS[no])
    src = src.resolve()
    rels = finished_photos(src)
    if not rels:
        raise Trouble(WORDS["none"])
    done_before = set()
    if there:
        old = earlier_run(h, src, read_log(h))
        kit_now = _listing(h / posts.CONTENT_NAME / old["kit"] / "Photos") if old else set()
        done_before = {m["src"] for m in (old or {}).get("moves", []) if isinstance(m, dict) and m.get("done")
                       and isinstance(m.get("dst"), str) and _listed(kit_now, m["dst"]) is not None}
    need = 0
    for r in rels:
        if r not in done_before:
            try:
                need += (src / r).stat().st_size
            except OSError:
                pass
    _room(h if there else h.parent, need)
    h, made_home = ensure_home()
    if made_home:
        say(f"Made \"{posts.HOME_NAME}\" at {h} for their posts.")
    content = h / posts.CONTENT_NAME
    content.mkdir(parents=True, exist_ok=True)
    log = read_log(h)
    run = earlier_run(h, src, log)
    if run is None:
        when = shoot_date(src, rels)
        name = posts.clean_name(posts.date_name([{"folders": [src.name]}]))
        folder_name = posts.folder_name(name, when)
        if not folder_name or folder_name.startswith("."):
            folder_name = posts.folder_name("Shoot", when)
        if _fold(folder_name) in {_fold(n) for n in _listing(content)}:
            raise Trouble(WORDS["clash"].format(name=folder_name))
        kit = content / folder_name
        if this_computer.WINDOWS and kit_mod._kit_too_long(kit):
            raise Trouble("That shoot's folder would sit too deep in folders for this PC. Tell the Assistant.")
        run = {"from": str(src), "picked": src.name, "kit": folder_name, "name": name, "date": when[:10],
               "started": datetime.now().isoformat(timespec="seconds"), "status": "copying", "moves": []}
        log["runs"].append(run)
        say(f"A new shoot: \"{folder_name}\" from {src.name} ({len(rels)} finished photo{_s(len(rels))}).")
    else:
        run["status"] = "copying"
        run["again"] = datetime.now().isoformat(timespec="seconds")
        say(f"This folder made \"{run['kit']}\" before: going back to it (photos already there are left as they are).")
    kit = content / run["kit"]
    before = {m["src"]: m["dst"] for m in run["moves"] if isinstance(m, dict) and isinstance(m.get("src"), str) and isinstance(m.get("dst"), str)}
    names = names_for(rels, before, _listing(kit / "Photos"))
    by_src = {m["src"]: m for m in run["moves"] if isinstance(m, dict) and isinstance(m.get("src"), str)}
    for r in rels:
        if r not in by_src:
            m = {"src": r, "dst": names[r]}
            run["moves"].append(m)
            by_src[r] = m
    moves = [by_src[r] for r in rels]
    write_log(h, log)                               # the plan first, before a byte is copied
    photos = kit / "Photos"
    photos.mkdir(parents=True, exist_ok=True)
    aside = kit / ".kit" / "copies-set-aside"
    bad = []
    progress(state="working", words=WORDS["working"].format(n=0, of=len(moves)), done=0, of=len(moves))
    for i, m in enumerate(moves, 1):
        listing = _listing(photos)
        spelled = _listed(listing, m["dst"])
        if m.get("done") and spelled is not None:
            pass                                    # copied and checked by an earlier run: left as it is
        else:
            try:
                got = posts.copy_checked(src / m["src"], photos / (spelled or m["dst"]), aside=aside)
                if got is None and spelled is not None and not m.get("done"):
                    # The name this photo was given in a run that was cut off is now taken by a different file (one
                    # they put there by hand): compared, never replaced, and the photo comes in under a free name
                    # instead of failing the same way on every try (review, Nov 21).
                    m["dst"] = _free_name(m["dst"], _listing(photos))
                    write_log(h, log)
                    got = posts.copy_checked(src / m["src"], photos / m["dst"], aside=aside)
            except OSError as ex:
                write_log(h, log)                   # still "copying", with what is done marked: the next run finishes it
                n = sum(1 for x in moves if x.get("done"))
                raise Trouble(WORDS["held"].format(why=posts.could_not(ex), n=n, of=len(moves)))
            m["done"] = got is not None
            if got:
                m["sha256"] = got
            else:
                bad.append(m["src"])
        if i % SAVE_EVERY == 0:
            write_log(h, log)
        progress(state="working", words=WORDS["working"].format(n=i, of=len(moves)), done=i, of=len(moves))
    if bad:
        run["status"] = "problems"
        run["problems"] = bad[:50]
        write_log(h, log)
        n = len(bad)
        raise Trouble(WORDS["mismatch"].format(n=n, s=_s(n), they="it's" if n == 1 else "they're"))
    progress(state="working", words=WORDS["numbering"], done=len(moves), of=len(moves))
    in_kit = sorted(p.name for p in photos.iterdir() if p.is_file() and not p.name.startswith(".")
                    and not p.name.endswith(".studio-partial") and p.suffix.lower() in posts.PHOTO)
    if (kit / ".kit" / "kit.json").is_file():
        def note(rec):
            rec["photos"] = in_kit
        kit_mod.update_rec(kit, note)
    else:
        kit_mod.save_rec(kit, {"name": run["name"], "date": run["date"], "folder": run["kit"], "source": "picked",
                               "picked_from": run["picked"], "photos": in_kit, "made": datetime.now().isoformat(timespec="seconds")})
    try:
        ok = kit_mod.sheet(kit, quick=True) == 0
    except (Exception, SystemExit):  # noqa: BLE001
        ok = False
    run["status"] = "done" if ok else "unnumbered"
    run["finished"] = datetime.now().isoformat(timespec="seconds")
    write_log(h, log)
    if not ok:
        raise Trouble(WORDS["unnumbered"])
    return kit


def run_job(folder):
    """`make --job`: the page server's detached run. One at a time (a lock); every line the page sees in the job."""
    import kit as kit_mod
    HOME.mkdir(parents=True, exist_ok=True)
    with kit_mod._held(LOCK, 2.0) as got:
        if got is False:
            say("Another new shoot is being copied in right now.")
            return 3
        job_write(state="working", words=WORDS["starting"], done=0, of=0)
        try:
            kit = make(folder, progress=lambda **k: job_write(**k))
        except Trouble as t:
            job_write(state="stopped", words=str(t), done=0, of=0)
            say("STOP: " + str(t))
            return 1
        except (Exception, SystemExit) as e:  # noqa: BLE001
            job_write(state="stopped", words=WORDS["stopped"], done=0, of=0)
            say(f"STOP: {e.__class__.__name__}: {str(e)[:200]}")
            return 1
        job_write(state="done", words=WORDS["done"], kit=kit.name)
        say(f"Done: {kit.name}")
        return 0


def main():
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make", help="make a post kit from one folder of finished photos (copied, never moved)")
    mk.add_argument("folder")
    mk.add_argument("--for", dest="make", choices=MAKES, default="reel", help="the page to name at the end")
    mk.add_argument("--job", action="store_true", help="the page server's run: follow it in new-shoot-job.json")
    sub.add_parser("status", help="what the page follows, as JSON")
    a = ap.parse_args()
    if a.cmd == "status":
        say(json.dumps(job(), ensure_ascii=False))
        return 0
    if a.job:
        return run_job(a.folder)
    import kit as kit_mod
    HOME.mkdir(parents=True, exist_ok=True)
    with kit_mod._held(LOCK, 2.0) as got:   # one at a time, the page's job and the chat's alike (review, Nov 21)
        if got is False:
            say("STOP: " + WORDS["busy"])
            return 3
        try:
            kit = make(a.folder, progress=lambda **k: None)
        except Trouble as t:
            say("STOP: " + str(t))
            return 1
    say(f"Post kit: {kit.name}. Its {a.make} page: {go(kit.name)[a.make]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
