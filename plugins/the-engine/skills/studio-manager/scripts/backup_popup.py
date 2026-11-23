#!/usr/bin/env python3
"""Back up a card, from the home page (Nicole's v31, sections 1 to 4 and 6; her answers of Nov 23).

Tapping Back up a card on the home page opens a box: her safety words, the card and the drive as two pictures, and
one orange button. The first time it asks where backups go (a drive, then a folder on it, opened like Finder);
after that it opens filled in. Start the backup starts the backup itself, as a job of its own (backup_job.py), and
the home card shows how it is going. Nothing here copies a photo: the backup's own scripts do that, as ever.

    GET  /backup-popup        what the box shows: the card that is in, the drives, where backups go now, the
                              two ways of naming, the last few backups, the job
    GET  /backup-job          the job, for the home card and the box (polled): words, counts, never a path
    GET  /backup-report       the report of the backup the job made: {ok, url}
    POST /backup-folders      {d, name, path: [folder names]}            the folders in there: {ok, folders, more}
    POST /backup-folder-new   {d, name, path: [...], new: "<name>"}      + New folder: {ok, path, existed, cleaned}
    POST /backup-pick         {}                                         the computer's own folder window, as a
                                                                         fallback: {ok, d, name, path}
    POST /backup-naming       {offered: 1 | 2}                           the way shoot folders are named, remembered
    POST /backup-start        {source: "card" | "folder", card, dest, second, shoot_name}
                              dest: {"saved": true} | {"d", "name", "path": [...]} | {"computer": true}
                              second: null | {"d", "name"}   (asked each time, never remembered: Nicole, Nov 23)

The folder browser's rules (a drive's folder names are often client names, and a wrong folder is where every later
backup would go):
  * the page never sends or sees a path. A drive is its number in the list AND its name, both checked again here;
    a folder is a list of folder NAMES from the top of that drive;
  * each name must be one exact entry of its folder's own listing (never a case-blind "is it there"), never "." or
    "..", never a name with a slash, never one starting with a dot; never a link, a package (a Photos library) or
    a hidden or system folder (.studio, _studio, Backups.backupdb, $RECYCLE.BIN, System Volume Information);
  * the rebuilt folder must still be inside the drive once every link is followed;
  * a listing stops at LIST_MAX folders and LIST_SECONDS, and says there are more;
  * + New folder: a plain mkdir, never exist_ok; a name that is taken (whatever its capitals) opens the folder
    that is there; nothing is ever written over;
  * every POST goes through the pickers' guard (this server's Host, its own Origin, JSON, a short body); every
    GET refuses another website and any other Host.
Where backups go is saved (studio_file.set_backup_place: exactly the folder picked) only when Start is pressed.
"""
import html
import importlib.util
import json
import os
import stat
import sys
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JOB_FILE = HOME / "backup-job.json"

GET_ROUTES = ("/backup-popup", "/backup-job", "/backup-report")
POST_ROUTES = ("/backup-folders", "/backup-folder-new", "/backup-pick", "/backup-naming", "/backup-start", "/backup-again")
POST_CAP = 6000                 # a folder's path as names, a few hundred bytes; never more
LIST_MAX = 400                  # folders shown in one listing
SCAN_MAX = 6000                 # entries looked at in one folder before it says "there are more"
LIST_SECONDS = 4.0              # a drive that takes longer than this to list is told so, not waited for
DEPTH_MAX = 12                  # folders deep the browser goes
NAME_MAX = 255
SHOOT_NAME_MAX = 80
RECENT = 3                      # the last few backups at the bottom of the box (hers)
DONE_SHOWS_HOURS = 12           # how long the home card keeps saying Done after a backup
PROBLEM_SHOWS_HOURS = 48        # ... and how long a backup that stopped stays on it
FIND_FROM = 9                   # "Find a folder" shows from this many folders (hers: more than 8)
NAME_SHOOTS = "/name-shoots.html"   # lane C's page; the home card falls back to the report when it is not there
EXAMPLE_SHOOT = "Aurora"        # the name the two ways of naming are shown with (hers)

# Folders never shown and never opened, whatever is in them (lower case). The Assistant's own records, the two
# computers' own housekeeping, and Time Machine.
HIDDEN_NAMES = {".studio", "_studio", "backups.backupdb", "$recycle.bin", "system volume information", "lost+found",
                "recycler", "recycled", ".trashes", ".spotlight-v100", ".fseventsd", ".temporaryitems",
                ".documentrevisions-v100", "found.000"}

# ---------- the words ----------
# Nicole's, from pages/home-backup-popup.html and pages/idea-naming-after-the-backup.html (v31, Nov 22), whole;
# "Your assistant" is "The Assistant" (Nicole, Nov 22: "everything is the assistant"). <em> and <b> are hers.
WORDS = {
    "title": "Back up <em>a card</em>",
    "close": "Close",
    "safety": ("The Assistant copies every photo on your card to your drive, and it can save a second copy on another drive too. "
               "Then it double-checks every single photo against your card, so you know nothing is missing, and sorts them into "
               "shoots you can rename."),
    "safe": "✓ Nothing on your card is ever changed or deleted. It stays exactly as it is until you decide to format it.",
    "card_small": "Your card · about {files} files",
    "nocard": "Put your card in",
    "nocard_small": "It shows up here by itself",
    "pick_drive": "Pick a drive",
    "pick_drive_small": "Where your backups go",
    "half_small": "Now pick a folder",
    "change": "Change",
    "where_first": "Where should your backups go?",
    "where_again": "Where should it go?",
    "only_once": "This is the only thing it asks, and only this once. After that it remembers, and you can change it here anytime.",
    "remembers": "It remembers what you pick for next time.",
    "which_folder": "Which folder on {drive}?",
    "find_on": "Find a folder on {drive}",
    "find_in": "Find a folder in {folder}",
    "no_match": "No folder called “{q}” here.",
    "none_here": "No folders in here yet.",
    "name_new": "Name the new folder",
    "name_new_aria": "New folder name",
    "make_it": "Make it",
    "cancel": "Cancel",
    "put_in": "Put my backups in {folder}",
    "open_hint": "Open the folder you keep your shoots in, or make a new one.",
    "new_folder": "+ New folder",
    "new_folder_in": "+ New folder in {folder}",
    "each_here": "Each shoot gets its own folder in here, named your way, right next to your other shoots.",
    "dest_way": "Each shoot gets its own folder inside {folder}, named your way.",
    "dest_named": "Each shoot gets its own folder inside {folder}, named <b>{way}</b>",
    "like": "Like {example}",
    "nm_note": "It remembers this. You can always rename a shoot after.",
    "who_label": "What would you like to name this shoot?",
    "who_note": "Optional. Leave it blank if there's more than one shoot on this card: you'll name them after.",
    "who_ph": "Shoot name",
    "second_add": "+ Also save a second copy on another drive",
    "second_on": "A second copy goes to <b>{drive}</b>, in the same folders",
    "remove": "Remove",
    "second_run": "And a second copy on <b>{drive}</b>",
    "start": "Start the backup",
    "need_card": "Put your card in first.",
    "need_drive": "Pick where it goes first.",
    "need_folder": "Pick a folder first.",
    "no_wait_start": "No need to wait. Keep working while it backs up.",
    "folder_q": "Photos that aren’t on a card, like from a phone or a download?",
    "folder_btn": "Back up a folder instead",
    "your_backups": "Your backups",
    "see_all": "See all my backups",
    "recent_checked": "{shoots} · {count}, every one checked",
    "no_wait": "No need to wait. Keep working.",
    "sorting": "Sorting into shoots",
    "almost": "Almost done",
    "done_head": "Done. Every photo checked.",
    "done_step": "Done",
    "safe_format": "It’s safe to format your card.",
    "toast_done_b": "Your card is backed up.",
    "backing_up": "Backing up {card} to {where}",
}
# Ours. Each is a draft for Dustin and Nicole. Where one stands in for a line of hers, the reason is beside it.
OUR_WORDS = {
    # her steps were Copying / Checking every photo / Sorting / Done. Each photo is checked the moment it lands, so
    # there is no checking step of its own to show (her answers, Nov 23, as the lead worded them)
    "copying": "Copying and checking ({done} of {total})",
    "copying_plain": "Copying and checking",
    "copying_step": "Copying and checking",
    "second_step": "Making your second copy",
    "second_sub": "On {drive}, checked the same way",
    # hers ended "...and lets you know when it's done". Nicole said no to a notification (Nov 23): the home card
    # turning to Done is how they know, so nothing promises more
    "run_top": "No need to wait here. Close this and keep working: it shows how it’s going on your home page.",
    "run_nw": "No need to wait here. Keep working: your home page shows when it’s done.",
    "toast_start_rest": "No need to wait: keep working. Your home page shows when it’s done.",
    # hers said "3 shoots are in your editing queue". They are not: new shoots go to Your backups (Nicole, Nov 23)
    "toast_done_checked": "Every photo checked.",
    "backed_many": "Your {n} shoots are backed up.",
    "backed_one": "Your shoot is backed up.",
    "found_many": "We found {n} shoots on your card",
    "found_one": "We found 1 shoot on your card",
    "found_many_folder": "We found {n} shoots in your folder",
    "found_one_folder": "We found 1 shoot in your folder",
    "name_them": "Name them",
    "name_it": "Name it",
    "see_report": "See the report",
    "toast_done_folder_b": "Your folder is backed up.",
    # a backup that finished but whose records do not say every photo's copy was checked: no claim is made
    "done_plain": "Done.",
    "done_look": "Something needs a look: see the report",          # hers, from the backups list
    "done_sample": "Keep the card: this was a sample",              # the report's own words for a sample backup
    # the backup finished, and its records can't be read right now (the drive unplugged): not a problem, said as it is
    "done_away": "{drive} isn't plugged in right now. Plug it in to see this backup.",
    "done_away_plain": "I can't see this backup right now. If it is on a drive, plug the drive in.",
    # a backup that stopped
    "problem_head": "The backup stopped before it finished.",
    "problem_do": "Tap here and press Start the backup again. Photos already copied are checked, not copied again.",
    "problem_do_open": "Press Start the backup again. Photos already copied are checked, not copied again.",
    # a backup the page's own job stopped on: the job's lines say "press Try again", so the card has that button.
    # It starts the same backup again (same card or folder, same place, same second drive), under the same name.
    "try_again": "Try again",
    "problem_again": "Photos already copied are checked, not copied again.",
    "again_gone": "I can't start that one again from here. Tap Back up a card and press Start the backup.",
    # the second copy while it is being made, with how far it is
    "second_count": "Making your second copy ({done} of {total})",
    # the second copy asked for with this backup did not finish: the backup itself is whole, and the card says so
    "second_not": "Second copy not made",
    # the tiles
    "card_plain": "Your card",
    "folder_small": "Your folder",
    "top_of_drive": "Right on the drive",
    "not_plugged": "Not plugged in right now",
    "this_computer": "This {computer}",
    "free": "{free} free",
    # no external drive: the two choices the chat already offers (studio_file.ask_words), in plain words
    "no_drive": "I don't see an external drive. Where should your backups go?",
    "plug_one": "I'll plug one in",
    "on_computer": "On this {computer} for now",
    "plug_wait": "Plug it in and it shows up here by itself.",
    "computer_small": "In Shoots, inside Pictures",
    # the folder browser, where hers has none
    "loading": "Loading…",
    "more_folders": "There are more folders in here than fit. Use Find a folder, or open a folder inside.",
    "slow": "That drive is taking a long time to answer. Try again in a moment.",
    "gone": "That folder isn't there anymore. Pick again.",
    "drives_changed": "Your drives changed just now. Pick the drive again.",
    "not_listable": "I can't open that folder.",
    "bad_name": "A folder's name can't start with a dot or be empty. Try another name.",
    "taken_opened": "There was already a folder called {name} here, so I opened it. Nothing in it was changed.",
    "taken_not_folder": "That name is already used here by something I can't put backups in. Try another name.",
    "cleaned": "Folder names can't use some characters, so I called it {name}.",
    "cant_make": "I couldn't make a folder there. The drive may only allow reading.",
    "too_long": "That folder would sit too deep for Windows to open. Pick a folder nearer the top of the drive.",
    "pick_window": "Or pick it in a {files} window",
    "pick_waiting": "Pick the folder in the window that opened.",
    "pick_not_drive": "That folder isn't on one of the drives listed here. Pick a folder on your photo drive.",
    "pick_not_ok": "I can't put backups in that folder. Pick another one.",
    "no_window": "The folder window didn't open. Pick the folder here instead.",
    # the second copy, where hers has none
    "second_none": "Plug in another drive to save a second copy on it.",
    "second_which": "Which drive gets the second copy?",
    # the naming line: a third state hers has not (a way of their own, learned from a folder they pasted)
    "ways_aria": "How your shoot folders are named",
    # Start, where hers has none
    "starting": "Starting…",
    "already": "A backup is already running. This shows how it's going.",
    "card_gone": "Your card isn't in anymore. Put it back in and press Start the backup again.",
    "dest_gone": "The drive your backups go on isn't plugged in. Plug it in, or press Change to pick another.",
    "not_ready": "Backing up from this page isn't ready yet. Type backup now in the chat and the Assistant will do it.",
    "cant_start": "The backup couldn't start. Try again in a moment.",
    "didnt_work": "That didn't work. Try again in a moment.",
    "folder_pick": "Pick the folder to back up in the window that opened. It's copied and checked the same way as a card; nothing in it is changed.",
    "folder_prompt": "Pick the folder to back up. The Assistant copies and checks it; nothing in it is changed.",
    "dest_prompt": "Pick the folder your backups should go in.",
    "no_folder": "No folder chosen.",
    "second_same": "The second copy has to go on a different drive from the first.",
    "second_source": "The second copy can't go on the drive the photos are coming from.",
    "no_report": "The report isn't ready to open from here. Say \"show me the report\" and the Assistant will.",
    # the last few backups, when "every one checked" would not be true of one
    "recent_plain": "{shoots} · {count}",
    "shoots_one": "1 shoot",
    "shoots_many": "{n} shoots",
    "card_aria": "Back up a card: open it",
}


def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key]


def page_words():
    """Every word the page's script draws, with the computer's own words filled in."""
    out = dict(WORDS)
    out.update(OUR_WORDS)
    for k in ("this_computer", "on_computer"):
        out[k] = out[k].format(computer=this_computer.COMPUTER)
    out["pick_window"] = out["pick_window"].format(files=this_computer.FILES_APP)
    return out


class Refused(Exception):
    def __init__(self, words, code=400):
        super().__init__(words)
        self.words, self.code = words, code


def _log(msg):
    try:
        print("backup-popup: " + msg, flush=True)
    except (BrokenPipeError, OSError, ValueError):
        pass


# ---------------------------------------------------------------- the card, the drives, where backups go

def the_card():
    """The memory card that is in: {"name", "files", "path"} (the path is for this server only), or None."""
    for c in this_computer.cards():
        n = 0
        try:
            for _, _, files in os.walk(Path(c["path"]) / "DCIM"):
                n += len([f for f in files if not f.startswith(".")])
                if n > 20000:
                    break
        except OSError:
            pass
        return {"name": str(c["shown"]), "files": n, "path": str(c["path"])}
    return None


def free_words(gb):
    return f"{gb / 1000:.1f} TB" if gb >= 1000 else f"{gb:,} GB"


def drive_rows():
    """The drives a backup could go on (studio_file.drives(): never the computer's own disk, a memory card or
    Time Machine), in the order the page numbers them."""
    import studio_file
    return studio_file.drives()


def drive_row(d, name):
    """The drive the page means: its number in the list AND its name, both checked again here. Anything else (a
    drive unplugged since, another one plugged in) is refused, and the page is told to pick again."""
    rows = drive_rows()
    if type(d) is not int or not isinstance(name, str) or not 0 <= d < len(rows) or str(rows[d]["name"]) != name:
        raise Refused(W("drives_changed"), 409)
    return rows[d]


def _inside(inner, outer):
    try:
        i, o = Path(inner).resolve(), Path(outer).resolve()
    except OSError:
        return False
    return i == o or o in i.parents


def saved_place():
    """Where backups go now, as the box shows it: {"drive", "folders": [names], "here", "computer"} or None when
    nothing is on file. Names only. A drive that is not plugged in is named, with here False."""
    import studio_file
    session = (studio_file.load().get("drives") or {}).get("session")
    if not session or not isinstance(session, str):
        return None
    p = Path(session)
    try:
        here = p.is_dir()
    except OSError:
        here = False
    for r in drive_rows():
        if _inside(p, r["path"]):
            try:
                rel = p.resolve().relative_to(Path(r["path"]).resolve()).parts
            except (OSError, ValueError):
                rel = (p.name,)
            return {"drive": str(r["name"]), "folders": [str(x) for x in rel], "here": here, "computer": False}
    if here and studio_file.on_internal_disk(p):
        try:
            rel = p.resolve().relative_to(Path.home().resolve()).parts
        except (OSError, ValueError):
            rel = (p.name,)
        return {"drive": W("this_computer").format(computer=this_computer.COMPUTER), "folders": [str(x) for x in rel][-3:],
                "here": True, "computer": True}
    return {"drive": str(this_computer.drive_words(p) or p.name or ""), "folders": [p.name] if p.name else [], "here": False,
            "computer": False}


def naming_now():
    """The two offered ways, each named from its own pattern ("Shoot name_Date") and shown with an example in its
    real spelling ("Aurora_11-22-26"), and which one is theirs (0: a way of their own)."""
    import studio_file
    now = studio_file.load().get("naming") or {}
    ways, current = [], 0
    for n, way in enumerate(studio_file.OFFERED, 1):
        label = way["folder_pattern"].replace("{shoot}", "Shoot name").replace("{date}", "Date")
        try:
            example = studio_file.render(way, EXAMPLE_SHOOT, datetime.now())
        except Exception:  # noqa: BLE001
            example = way["label"]
        ways.append({"n": n, "label": label, "example": example})
        if now.get("folder_pattern") == way["folder_pattern"] and now.get("date_format") == way["date_format"]:
            current = n
    if not now.get("folder_pattern"):
        current = 1                 # nothing on file yet: the first backup gets the first way
    return {"current": current, "ways": ways}


def recent_backups():
    """The last few backups, for the bottom of the box: when, how many shoots and photos, and "every one checked"
    only when that backup's own records say so."""
    import home_base
    out = []
    try:
        groups = home_base.backups()
    except (Exception, SystemExit):  # noqa: BLE001
        return out
    for g in groups[:RECENT]:
        shoots = [s for b in g["backups"] for s in b["shoots"]]
        out.append({"added": str(g.get("added") or "")[:10], "shoots": len(shoots),
                    "photos": sum(s.get("count") or 0 for s in shoots), "clips": sum(s.get("clips") or 0 for s in shoots),
                    "checked": all(b.get("safe") is True for b in g["backups"])})
    return out


# ---------------------------------------------------------------- the folder browser

def name_ok(n):
    return (isinstance(n, str) and 0 < len(n) <= NAME_MAX and n not in (".", "..") and not n.startswith(".")
            and not any(c in n for c in "/\\\x00") and not any(ord(c) < 32 for c in n))


def allowed(name, full):
    """May this entry be shown and opened: a plain folder, not a link, not hidden, not a package, not the
    Assistant's or the computer's own housekeeping."""
    import studio_file
    low = name.lower()
    if not name_ok(name) or name.startswith("$") or low in HIDDEN_NAMES or low.endswith(studio_file.PACKAGES):
        return False
    try:
        st = os.lstat(full)                         # lstat: a link is a link, never the folder it points at
    except OSError:
        return False
    if not stat.S_ISDIR(st.st_mode):
        return False
    if getattr(st, "st_flags", 0) & 0x8000:         # a Mac's hidden mark (what chflags hidden sets)
        return False
    if getattr(st, "st_file_attributes", 0) & (0x2 | 0x4 | 0x400):   # a PC: hidden, system, or a junction
        return False
    return True


def _limited(fn, seconds):
    """Run fn in a thread of its own and wait at most `seconds`: a drive that has stopped answering must never
    hold a page request for ever. Raises Refused(slow) when it takes longer (the thread is left to end by itself)."""
    box = {}

    def run():
        try:
            box["got"] = fn()
        except BaseException as e:  # noqa: BLE001
            box["err"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise Refused(W("slow"), 504)
    if "err" in box:
        raise box["err"]
    return box.get("got")


def walk(root, names):
    """The folder a list of names leads to from the top of a drive, each name checked against its folder's exact
    listing. Raises Refused. Never follows a link, never leaves the drive."""
    if not isinstance(names, list) or len(names) > DEPTH_MAX or not all(name_ok(n) for n in names):
        raise Refused(W("not_listable"), 400)
    cur = str(root)
    for n in names:
        try:
            entries = os.listdir(cur)
        except OSError:
            raise Refused(W("gone"), 409)
        if n not in entries:                        # the exact name, as the folder itself lists it
            raise Refused(W("gone"), 409)
        nxt = os.path.join(cur, n)
        if not allowed(n, nxt):
            raise Refused(W("not_listable"), 400)
        cur = nxt
    try:
        real, top = Path(cur).resolve(), Path(str(root)).resolve()
    except OSError:
        raise Refused(W("gone"), 409)
    if not (real == top or top in real.parents) or not real.is_dir():
        raise Refused(W("not_listable"), 400)
    return Path(cur)


def listing(folder):
    """(the folders in there, by name, in order; are there more than fit)."""
    names, more, scanned, t0 = [], False, 0, time.monotonic()
    try:
        with os.scandir(str(folder)) as it:
            for e in it:
                scanned += 1
                if scanned > SCAN_MAX or time.monotonic() - t0 > LIST_SECONDS:
                    more = True
                    break
                if allowed(e.name, e.path):
                    names.append(e.name)
    except OSError:
        raise Refused(W("gone"), 409)
    names.sort(key=lambda s: (s.casefold(), s))
    if len(names) > LIST_MAX:
        names, more = names[:LIST_MAX], True
    return names, more


def folders_of(d, name, names):
    row = drive_row(d, name)

    def work():
        return listing(walk(row["path"], names))

    got, more = _limited(work, LIST_SECONDS + 2)
    return {"ok": True, "folders": got, "more": more, "path": list(names)}


def _fold(s):
    return unicodedata.normalize("NFC", s).casefold()


def new_folder(d, name, names, new):
    """+ New folder: made inside the folder the names lead to, by a plain mkdir. A name that is taken there,
    whatever its capitals, opens the folder that is there (never a second one, never anything written over)."""
    row = drive_row(d, name)
    if not isinstance(new, str) or len(new) > 200:
        raise Refused(W("bad_name"), 400)
    typed = " ".join(new.split())
    if not typed or typed.startswith("."):
        raise Refused(W("bad_name"), 400)
    clean = this_computer.safe_name(typed, fallback="")
    if not clean or clean.startswith(".") or not name_ok(clean) or clean.startswith("$") or clean.lower() in HIDDEN_NAMES:
        raise Refused(W("bad_name"), 400)
    if len(names) + 1 > DEPTH_MAX:
        raise Refused(W("not_listable"), 400)

    def work():
        parent = walk(row["path"], names)
        try:
            entries = os.listdir(str(parent))
        except OSError:
            raise Refused(W("gone"), 409)
        same = [e for e in entries if _fold(e) == _fold(clean)]
        if same:
            there = same[0]
            if not allowed(there, os.path.join(str(parent), there)):
                raise Refused(W("taken_not_folder"), 409)
            return there, True
        target = parent / clean
        if this_computer.WINDOWS and this_computer.path_too_long(target, folder=True):
            raise Refused(W("too_long"), 400)
        try:
            os.mkdir(str(target))                   # never exist_ok: a folder that appeared meanwhile is not ours
        except FileExistsError:
            again = [e for e in os.listdir(str(parent)) if _fold(e) == _fold(clean)]
            if again and allowed(again[0], os.path.join(str(parent), again[0])):
                return again[0], True
            raise Refused(W("taken_not_folder"), 409)
        except OSError:
            raise Refused(W("cant_make"), 409)
        return clean, False

    made, existed = _limited(work, LIST_SECONDS + 2)
    words = W("taken_opened").format(name=made) if existed else (W("cleaned").format(name=made) if made != typed else "")
    if not existed:
        _log("made a folder for backups")
    return {"ok": True, "path": list(names) + [made], "existed": existed, "cleaned": (not existed) and made != typed, "words": words}


def picked_in_window(folder):
    """A folder chosen in the computer's own folder window, turned into what the page keeps: a drive's number and
    name, and folder names. Only a folder on one of the listed drives, and only one the browser itself could open."""
    try:
        p = Path(folder).resolve()
    except OSError:
        raise Refused(W("pick_not_ok"), 400)
    for i, r in enumerate(drive_rows()):
        try:
            rel = list(p.relative_to(Path(r["path"]).resolve()).parts)
        except (OSError, ValueError):
            continue
        if not rel:
            raise Refused(W("pick_not_ok"), 400)   # the top of the drive: a folder on it is what is asked for
        try:
            walk(r["path"], rel)
        except Refused:
            raise Refused(W("pick_not_ok"), 400)
        return {"ok": True, "d": i, "name": str(r["name"]), "path": rel}
    raise Refused(W("pick_not_drive"), 400)


# ---------------------------------------------------------------- the job

_PRETEND_JOB = {}
# What the job's own record does not say and the words need: was it a folder ("Back up a folder instead") and not
# a card. Written here when Start is pressed; matched to the job by when it started. Names nothing, holds no path.
START_NOTE = HOME / "backup-popup-start.json"
NOTE_SLACK = 180                # seconds between Start being pressed and the job's own "started"


def note_start(from_folder):
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        tmp = START_NOTE.with_name(START_NOTE.name + ".part")
        tmp.write_text(json.dumps({"from_folder": bool(from_folder), "at": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
        this_computer.replace(tmp, START_NOTE)
    except OSError:
        pass


def started_from_folder(rec):
    if rec.get("source") == "folder":
        return True
    private = rec.get("private")
    if isinstance(private, dict) and private.get("as_folder") is True:
        return True                         # picked with Back up a folder instead: a folder, whatever is inside it
    if isinstance(private, dict) and isinstance(private.get("is_card"), bool) and "as_folder" in private:
        return not private["is_card"]       # the job's own record says what it was started on (backup_job.py)
    try:    # a record with no word of its own on it: the note this page wrote when Start was pressed
        note = json.loads(START_NOTE.read_text(encoding="utf-8"))
        a = datetime.fromisoformat(str(note["at"])[:19])
        b = datetime.fromisoformat(str(rec.get("started"))[:19])
        if bool(note.get("from_folder")) and abs((b - a).total_seconds()) <= NOTE_SLACK:
            return True
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if isinstance(private, dict) and isinstance(private.get("is_card"), bool):
        return not private["is_card"]
    try:
        note = json.loads(START_NOTE.read_text(encoding="utf-8"))
        a = datetime.fromisoformat(str(note["at"])[:19])
        b = datetime.fromisoformat(str(rec.get("started"))[:19])
        return bool(note.get("from_folder")) and abs((b - a).total_seconds()) <= NOTE_SLACK
    except (OSError, ValueError, KeyError, TypeError):
        return False


def job_module():
    """backup_job.py (lane A's: the detached job that runs the backup), or None while it is not there. A test names
    a stand-in file in STUDIO_BACKUP_JOB_FOR_TESTS (only a test sets it), so no test ever starts a real backup."""
    pretend = os.environ.get("STUDIO_BACKUP_JOB_FOR_TESTS")
    try:
        if pretend:
            if _PRETEND_JOB.get("path") != pretend:
                spec = importlib.util.spec_from_file_location("backup_job_for_tests", pretend)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _PRETEND_JOB.update(path=pretend, mod=mod)
            return _PRETEND_JOB["mod"]
        import backup_job
        return backup_job
    except Exception as e:  # noqa: BLE001
        if not isinstance(e, ImportError):
            _log(f"the backup job could not be loaded ({e.__class__.__name__})")
        return None


def job_record():
    """The job's own record (the contract's shape), from backup_job.status() when it is there, else from the file
    itself. Anything unreadable or odd is "idle": the card never shows a backup that nobody can vouch for."""
    rec = None
    mod = job_module()
    if mod is not None:
        try:
            rec = mod.status()
        except (Exception, SystemExit) as e:  # noqa: BLE001
            _log(f"the backup job's status could not be read ({e.__class__.__name__})")
    if rec is None:
        try:
            rec = json.loads(JOB_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rec = None
    if not isinstance(rec, dict) or rec.get("state") not in ("running", "done", "problem"):
        return {"state": "idle"}
    return rec


def _hours_since(iso):
    try:
        return (datetime.now() - datetime.fromisoformat(str(iso)[:19])).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def _int(v):
    return v if type(v) is int and v >= 0 else 0


def _records(rec):
    """The job's backup's records folder as it is found now (before or after it settled), or None."""
    r = rec.get("records")
    if not r or not isinstance(r, str):
        return None
    try:
        import home_base
        found = home_base.records_of(r)
    except (Exception, SystemExit):  # noqa: BLE001
        found = None
    if found is None:
        p = Path(r)
        try:
            found = p if (p / "manifest.json").is_file() else None
        except OSError:
            found = None
    return found


_CARD_KEYS = {}                 # (the card's path, how many files, its DCIM folder's own time) -> its fingerprint


def other_card_in(rec):
    """True when a memory card is in right now and it is NOT the card this job backed up. False when it is that
    card, when no card is in, or when it cannot be told (a record from before the job kept the card's
    fingerprint). The fingerprint is the card ledger's own (cards.py) and is read once per card put in, not on
    every look."""
    want = (rec.get("private") or {}).get("card_key") if isinstance(rec.get("private"), dict) else None
    if not want or not isinstance(want, str):
        return False
    card = the_card()
    if card is None:
        return False
    try:
        stamp = os.stat(Path(card["path"]) / "DCIM").st_mtime_ns
    except OSError:
        stamp = 0
    k = (card["path"], card["files"], stamp)
    if k not in _CARD_KEYS:
        try:
            import cards
            fp = cards.fingerprint(card["path"])
            got = cards.key(fp) if fp else ""
        except (Exception, SystemExit):  # noqa: BLE001
            return False
        _CARD_KEYS.clear()
        _CARD_KEYS[k] = got
    return _CARD_KEYS[k] != want


def job_view(rec=None):
    """The job as the page draws it: words and numbers only, never a path. `show` says whether the home card
    shows it at all (a backup running, one that stopped, or one that finished a little while ago)."""
    rec = job_record() if rec is None else rec
    state = rec.get("state")
    if state == "idle":
        return {"ok": True, "state": "idle", "show": False}
    card = str(rec.get("card") or "")
    drive = str(rec.get("drive") or "")
    folders = [str(x) for x in rec.get("folders") or [] if isinstance(x, str)][:DEPTH_MAX]
    second = str(rec["second"]) if isinstance(rec.get("second"), str) and rec.get("second") else None
    where = " › ".join([x for x in [drive] + folders if x])
    shoots = _int(rec.get("shoots"))
    from_folder = started_from_folder(rec)
    v = {"ok": True, "state": state, "step": rec.get("step") if rec.get("step") in ("copying", "sorting", "second", "done") else "copying",
         "card": card, "drive": drive, "folders": folders, "second": second, "where": where, "shoots": shoots,
         "backup": str(rec.get("backup") or ""), "from_folder": from_folder, "show": True, "frac": None, "link": None,
         "steps": [], "safe_format": False}
    names = [("copying", W("copying_step")), ("sorting", W("sorting"))] + ([("second", W("second_step"))] if second else []) + [("done", W("done_step"))]
    if state == "running":
        done, total = _int(rec.get("done")), _int(rec.get("total"))
        if v["step"] == "sorting":
            v.update(head=W("sorting"), sub=W("almost"), frac=1.0)
        elif v["step"] == "second":
            v.update(head=W("second_count").format(done=f"{min(done, total):,}", total=f"{total:,}") if total else W("second_step"),
                     sub=W("second_sub").format(drive=second) if second else "", frac=(min(done, total) / total) if total else 0.0)
        else:
            v["step"] = "copying"
            v.update(head=W("copying").format(done=f"{min(done, total):,}", total=f"{total:,}") if total else W("copying_plain"),
                     sub=W("backing_up").format(card=card or "your card", where=where) if where else "",
                     frac=(min(done, total) / total) if total else 0.0)
        at = [k for k, _ in names].index(v["step"])
        v["steps"] = [{"t": t, "dn": i < at, "on": i == at} for i, (_, t) in enumerate(names)]
        return v
    if state == "done":
        since = _hours_since(rec.get("finished"))
        v["show"] = since is not None and since <= DONE_SHOWS_HOURS
        v["step"] = "done"
        checked = sample = False
        records = _records(rec)
        if records is not None:
            try:
                import home_base
                st = home_base.backup_status(records)
                checked, sample = st.get("safe") is True, bool(st.get("sample"))
            except (Exception, SystemExit):  # noqa: BLE001
                pass
        v["checked"], v["sample"] = checked, sample
        # The card that is in now is not the card this backup was made from (card 1 out, card 2 in: cameras give
        # every card the same name). Nothing here may read as "the card in the slot is safe to format": the box
        # leaves the finished backup's lines out, and the format line is never said (Nov 23 review).
        other = other_card_in(rec) if not from_folder else False
        if other:
            v["other_card"] = True
        v["steps"] = [{"t": t, "dn": True, "on": False} for _, t in names]
        # what the job itself has to say about a finished backup, in its own plain words (never a path): the card
        # was already backed up, files set aside, nothing could be sorted, a second copy that did not finish
        v["note"] = " ".join(str(rec.get("line") or "").split())[:700]
        if second and rec.get("second_ok") is False:
            v["second_bad"] = True
            v["steps"] = [{"t": W("second_not") if k == "second" else t, "dn": k != "second", "on": False, "bad": k == "second"} for k, t in names]
            if not v["note"]:
                v["note"] = " ".join(str(rec.get("second_line") or "").split())[:700]
        if checked:
            found = (W("found_one_folder") if shoots == 1 else W("found_many_folder").format(n=shoots)) if from_folder else \
                    (W("found_one") if shoots == 1 else W("found_many").format(n=shoots))
            v.update(head=W("done_head"), sub=found if shoots else "", safe_format=not from_folder and not other,
                     link={"kind": "name", "words": W("name_it") if shoots == 1 else W("name_them")} if shoots else {"kind": "report", "words": W("see_report")},
                     backed=(W("backed_one") if shoots == 1 else W("backed_many").format(n=shoots)) if shoots else "")
        elif records is None:
            # the backup's records can't be read just now (the drive is unplugged, most likely): that is not
            # "something needs a look". Said as what it is, with nothing claimed and nothing to open.
            v.update(head=W("done_plain"), sub=W("done_away").format(drive=drive) if drive else W("done_away_plain"), link=None, backed="")
        elif sample:
            v.update(head=W("done_plain"), sub=W("done_sample"), link={"kind": "report", "words": W("see_report")}, backed="")
        else:
            v.update(head=W("done_plain"), sub=W("done_look"), link={"kind": "report", "words": W("see_report")}, backed="")
        return v
    # a backup that stopped: the job's own plain words, and what to do
    since = _hours_since(rec.get("finished") or rec.get("started"))
    v["show"] = since is None or since <= PROBLEM_SHOWS_HOURS
    line = " ".join(str(rec.get("line") or "").split())[:300]
    v.update(head=line or W("problem_head"), sub=W("problem_do"), sub_open=W("problem_do_open"), bad=True,
             link={"kind": "report", "words": W("see_report")} if _records(rec) is not None else None)
    if rec.get("nothing") is True:          # an empty card or folder: nothing was copied, nothing to try again
        v.update(sub="", sub_open="", link=None)
    elif _again_ask(rec) is not None:       # the page's own job: Try again starts the same backup again
        v.update(again=W("try_again"), sub=W("problem_again"), sub_open=W("problem_again"))
    return v


def _again_ask(rec):
    """What Try again would start, from the job's own record (never from a page): (source, dest, second, shoot
    name), or None when the record does not say (then the card keeps its "press Start the backup again" line)."""
    p = rec.get("private") if rec.get("state") == "problem" and not rec.get("nothing") else None
    if not isinstance(p, dict) or not isinstance(p.get("source"), str) or not isinstance(p.get("dest"), str) or not p["source"] or not p["dest"]:
        return None
    second = p.get("second") if isinstance(p.get("second"), str) and p.get("second") else None
    name = p.get("shoot_name") if isinstance(p.get("shoot_name"), str) and p.get("shoot_name") else None
    return p["source"], p["dest"], second, name


def again():
    """POST /backup-again. The backup that stopped is started again exactly as it was asked for (the job's own
    record holds what that was; the page sends nothing), so it carries on under the same name: what is already
    copied is checked, not copied again. Answers {"ok", "words", "job"}."""
    rec = job_record()
    if rec.get("state") == "running":
        return {"ok": False, "running": True, "words": W("already"), "job": job_view()}
    ask = _again_ask(rec)
    mod = job_module()
    if ask is None or mod is None or not hasattr(mod, "start"):
        return {"ok": False, "words": W("again_gone"), "job": job_view()}
    source, dest, second, name = ask
    try:
        ans = _start_job(mod, source, dest, second, name, (rec.get("private") or {}).get("as_folder") is True)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"the backup could not be started again ({e.__class__.__name__}: {str(e)[:120]})")
        return {"ok": False, "words": W("cant_start"), "job": job_view()}
    if not isinstance(ans, dict) or not ans.get("ok"):
        why = " ".join(str((ans or {}).get("why") or "").split())[:300] if isinstance(ans, dict) else ""
        return {"ok": False, "words": why or W("cant_start"), "job": job_view()}
    _log("a backup that stopped was started again from the home page")
    return {"ok": True, "job": job_view()}


def card_box(view=None):
    """The home card's box (#n1) while a backup is running, has just finished or has stopped, as markup the server
    draws on a reload; None when the card shows what it always did. Every word is escaped here."""
    v = job_view() if view is None else view
    if not v.get("show"):
        return None
    e = html.escape
    if v["state"] == "running":
        pct = int(round(100 * (v.get("frac") or 0)))
        return (f"<div class='bk'><b>{e(v['head'])}</b><div class='bar2'><i style='width:{pct}%'></i></div>"
                f"<small>{e(v.get('sub') or '')}</small><small class='nw'>{e(W('no_wait'))}</small></div>")
    link = v.get("link")
    lk = f" · <button type='button' class='lk' data-bk='{e(link['kind'], quote=True)}'>{e(link['words'])}</button>" if link else ""
    if v.get("again"):
        lk = f" · <button type='button' class='lk' data-bk='again'>{e(v['again'])}</button>" + lk
    if not (v.get("sub") or ""):
        lk = lk[3:]
    cls = "bad" if v.get("bad") else "dn"
    note = f"<small class='nt'>{e(v['note'])}</small>" if v.get("note") else ""
    return f"<div class='bk'><b class='{cls}'>{e(v['head'])}</b><small>{e(v.get('sub') or '')}{lk}</small>{note}</div>"


def state():
    card = the_card()
    saved = saved_place()
    rows = drive_rows()
    return {"ok": True, "card": {"name": card["name"], "files": card["files"]} if card else None,
            "drives": [{"d": i, "name": str(r["name"]), "free": free_words(int(r.get("free_gb") or 0))} for i, r in enumerate(rows)],
            "saved": saved, "first": saved is None, "naming": naming_now(), "recent": recent_backups(), "job": job_view()}


# ---------------------------------------------------------------- Start the backup

_PICKING = threading.Lock()     # one folder window at a time from this server
_STARTING = threading.Lock()    # one Start at a time: two presses never save two places or start two jobs


def _dest(body, card_path):
    """The exact folder the backup goes in, from what the page sent: (path, computer). Raises Refused."""
    import studio_file
    dest = body.get("dest")
    if dest == {"saved": True}:
        session = (studio_file.load().get("drives") or {}).get("session")
        if not session or not Path(session).is_dir():
            raise Refused(W("dest_gone"), 409)
        return Path(session), False
    if dest == {"computer": True}:
        if drive_rows():
            raise Refused(W("drives_changed"), 409)       # offered only when no external drive is plugged in
        return None, True
    if (not isinstance(dest, dict) or set(dest) != {"d", "name", "path"} or not isinstance(dest["path"], list) or not dest["path"]):
        raise Refused(W("didnt_work"), 400)
    row = drive_row(dest["d"], dest["name"])
    return _limited(lambda: walk(row["path"], dest["path"]), LIST_SECONDS + 2), False


def start(body):
    """POST /backup-start. Every part is checked again here; where backups go is saved only now, and only the
    exact folder picked; then the job is asked to start. Answers {"ok", "words", "job"}."""
    import studio_file
    if (not isinstance(body, dict) or set(body) - {"source", "card", "dest", "second", "shoot_name"}
            or body.get("source") not in ("card", "folder")):
        raise Refused(W("didnt_work"), 400)
    shoot_name = body.get("shoot_name") or ""
    if not isinstance(shoot_name, str) or len(shoot_name) > 400:
        raise Refused(W("didnt_work"), 400)
    shoot_name = " ".join(shoot_name.split())[:SHOOT_NAME_MAX].strip()
    second = body.get("second")
    if second is not None and (not isinstance(second, dict) or set(second) != {"d", "name"}):
        raise Refused(W("didnt_work"), 400)
    if job_record().get("state") == "running":
        return {"ok": False, "running": True, "words": W("already"), "job": job_view()}
    mod = job_module()
    if mod is None or not hasattr(mod, "start"):
        return {"ok": False, "words": W("not_ready")}
    # where it comes from
    if body["source"] == "card":
        card = the_card()
        if card is None or not isinstance(body.get("card"), str) or card["name"] != body["card"]:
            raise Refused(W("card_gone"), 409)
        source, from_name = card["path"], card["name"]
    else:
        if not _PICKING.acquire(blocking=False):
            return {"ok": False, "words": W("folder_pick")}
        try:
            folder, why = this_computer.pick_folder(W("folder_prompt"))
        finally:
            _PICKING.release()
        if not folder:
            if why == "cancelled":
                return {"ok": False, "cancelled": True, "words": W("no_folder")}
            return {"ok": False, "words": W("no_window")}
        if not Path(folder).is_dir():
            raise Refused(W("gone"), 409)
        source, from_name = str(Path(folder)), Path(folder).name
        if job_record().get("state") == "running":      # one started from the chat while the window was open
            return {"ok": False, "running": True, "words": W("already"), "job": job_view()}
    place, computer = _dest(body, source)
    # the second copy: asked each time, never saved (Nicole, Nov 23)
    second_path = None
    if second is not None:
        srow = drive_row(second["d"], second["name"])
        if place is None or _inside(place, srow["path"]):
            raise Refused(W("second_same"), 400)
        if _inside(source, srow["path"]):
            raise Refused(W("second_source"), 400)
        why = studio_file.cannot_use(srow["path"])
        if why:
            raise Refused(why, 409)
        second_path = str(srow["path"])
    need = studio_file.room_needed(source)
    got = studio_file.set_backup_place(place, source=source, need=need, computer=computer)
    if got["state"] == "stop":
        raise Refused(got["why"], 409)
    note_start(body["source"] == "folder")
    try:
        ans = _start_job(mod, source, got["place"], second_path, shoot_name or None, body["source"] == "folder")
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"the backup could not be started ({e.__class__.__name__}: {str(e)[:120]})")
        return {"ok": False, "words": W("cant_start")}
    if not isinstance(ans, dict) or not ans.get("ok"):
        why = " ".join(str((ans or {}).get("why") or "").split())[:300] if isinstance(ans, dict) else ""
        return {"ok": False, "words": why or W("cant_start"), "job": job_view()}
    _log("a backup was started from the home page" + (" (with a second copy)" if second_path else ""))
    saved = saved_place() or {}
    where = " › ".join([saved.get("drive") or ""] + list(saved.get("folders") or [])).strip(" ›")
    return {"ok": True, "from": from_name, "where": where, "second": second["name"] if second else None, "job": job_view()}


def _start_job(mod, source, dest, second, shoot_name, as_folder):
    """Ask the job to start. Picked as a folder ("Back up a folder instead"), the job is told so: a folder with
    a card's DCIM folder inside it (a card dragged to the Desktop) is still a folder, and nothing may say a card
    is safe to format (Nov 23 review). A job module that does not know the word is started as before."""
    if as_folder:
        try:
            return mod.start(source, dest, second=second, shoot_name=shoot_name, as_folder=True)
        except TypeError:
            pass
    return mod.start(source, dest, second=second, shoot_name=shoot_name)


def report_of_job():
    rec = job_record()
    records = _records(rec) if rec.get("state") != "idle" else None
    if records is None:
        return {"ok": False, "words": W("no_report")}
    try:
        import serve_report
        url = serve_report.report_url(records)
    except (Exception, SystemExit):  # noqa: BLE001
        url = None
    if not url:
        return {"ok": False, "words": W("no_report")}
    return {"ok": True, "url": url}


# ---------------------------------------------------------------- the routes

def _send(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def handle_get(handler, path, query):
    import arrange
    try:
        if not arrange.our_host(handler) or _cross_site(handler):
            return _send(handler, {"ok": False}, 403)
        if path == "/backup-popup":
            return _send(handler, state())
        if path == "/backup-job":
            return _send(handler, job_view())
        if path == "/backup-report":
            return _send(handler, report_of_job())
        return _send(handler, {"ok": False}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "words": W("didnt_work")}, 500)


def handle_post(handler, path, query):
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
        if refused is None and _cross_site(handler):
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _send(handler, {"ok": False, "words": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
        if not isinstance(body, dict):
            return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
        try:
            if path == "/backup-folders":
                if set(body) != {"d", "name", "path"}:
                    raise Refused(arrange.NOT_UNDERSTOOD, 400)
                return _send(handler, folders_of(body["d"], body["name"], body["path"]))
            if path == "/backup-folder-new":
                if set(body) != {"d", "name", "path", "new"}:
                    raise Refused(arrange.NOT_UNDERSTOOD, 400)
                return _send(handler, new_folder(body["d"], body["name"], body["path"], body["new"]))
            if path == "/backup-naming":
                import studio_file
                if set(body) != {"offered"} or type(body["offered"]) is not int or not 1 <= body["offered"] <= len(studio_file.OFFERED):
                    raise Refused(arrange.NOT_UNDERSTOOD, 400)
                studio_file.set_offered(body["offered"])
                return _send(handler, {"ok": True, "naming": naming_now()})
            if path == "/backup-pick":
                if body != {}:
                    raise Refused(arrange.NOT_UNDERSTOOD, 400)
                if not _PICKING.acquire(blocking=False):
                    return _send(handler, {"ok": False, "words": W("pick_waiting")})
                try:
                    folder, why = this_computer.pick_folder(W("dest_prompt"))
                finally:
                    _PICKING.release()
                if not folder:
                    return _send(handler, {"ok": False, "cancelled": why == "cancelled", "words": "" if why == "cancelled" else W("no_window")})
                return _send(handler, picked_in_window(folder))
            if path == "/backup-again":
                if body != {}:
                    raise Refused(arrange.NOT_UNDERSTOOD, 400)
                if not _STARTING.acquire(blocking=False):
                    return _send(handler, {"ok": False, "words": W("starting")})
                try:
                    return _send(handler, again())
                finally:
                    _STARTING.release()
            if path == "/backup-start":
                if not _STARTING.acquire(blocking=False):
                    return _send(handler, {"ok": False, "words": W("starting")})
                try:
                    return _send(handler, start(body))
                finally:
                    _STARTING.release()
        except Refused as r:
            return _send(handler, {"ok": False, "words": r.words}, r.code)
        return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "words": W("didnt_work")}, 500)


# ---------------------------------------------------------------- the page's part (drawn on the home page, in its look)

# Her popup's styles (pages/home-backup-popup.html), rule for rule where hers has one, on our markup; every class
# starts "bk" so nothing on the home page is touched. The colours and the font are the home page's own (HOME_LOOK).
CSS = r"""
.row .seeall{display:inline-block;margin-top:8px;font:700 12px/1 var(--sans);color:var(--ink);text-decoration:underline;text-underline-offset:3px}
#s1:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.bk{display:grid;gap:6px;min-width:0;width:100%}
.bk b{font:700 14px/1.2 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.bk small{display:block;font-size:12px;color:var(--ink-2);overflow-wrap:anywhere}
.bk .dn{color:#2f7d56}.bk .bad{color:var(--late)}
.bk .nw{color:var(--ink);font-weight:700}
.bk .lk,.bkbox .lk{border:0;background:none;padding:0;font:inherit;color:var(--ink);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.bk .note{display:block;font-size:12px;color:var(--ink-2);margin-top:2px}
.bar2{height:4px;background:#E2DED6;overflow:hidden}.bar2 i{display:block;height:100%;width:0;background:var(--accent)}
.bkp{position:fixed;inset:0;z-index:20;background:rgba(17,17,17,.45);display:grid;place-items:center;padding:16px}
.bkp[hidden]{display:none}
.bkbox{box-sizing:border-box;width:min(760px,100%);max-height:90vh;overflow:auto;background:var(--paper);padding:clamp(18px,3vw,28px);outline:0}
.bkh{display:flex;align-items:baseline;justify-content:space-between;gap:1rem}
.bkh h3{margin:0;font:700 26px/1.05 var(--sans);letter-spacing:-.01em}
.bkh h3 em{font-style:normal;color:var(--accent)}
.bkh button{border:0;background:none;font-size:22px;line-height:1;cursor:pointer;color:var(--ink-2);padding:4px 6px}
.bkh button:hover,.bkh button:focus-visible{color:var(--ink)}
#bkS p{margin:.3rem 0 0;color:var(--ink-2);font-size:14px}
#bkS p.bksafe{margin:10px 0 0;color:var(--ink);font-weight:700}
#bkTop{margin-top:1rem}
.bkflow{display:grid;grid-template-columns:minmax(0,1fr) 34px minmax(0,1fr);align-items:stretch;gap:6px;margin:4px 0 6px}
.bkflow .arr{display:grid;place-items:center;font-size:22px;color:var(--ink-2)}
.bktile{box-sizing:border-box;background:#fff;padding:14px;display:grid;grid-template-columns:62px minmax(0,1fr);gap:12px;align-items:center;border:1.5px solid transparent;min-height:92px;min-width:0}
.bktile.e{background:transparent;border:1.5px dashed #bdb6ab}
.bktile.half{border-style:dashed;background:#fff}
.bktile b{display:block;font:700 16px/1.2 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.bktile small{display:block;font-size:12.5px;color:var(--ink-2);margin-top:3px;overflow-wrap:anywhere}
.bktile.e b{color:var(--ink-2)}.bktile.half b{color:var(--ink)}
.bktile .fpath{display:flex;align-items:center;color:var(--ink);font-weight:700}
.bksd{position:relative;display:block;width:44px;height:58px;margin:auto;background:var(--accent);clip-path:polygon(32% 0,100% 0,100% 100%,0 100%,0 24%)}
.bksd i{position:absolute;left:38%;right:10%;top:7px;height:12px;background:repeating-linear-gradient(90deg,#F2C9B6 0 3px,transparent 3px 6px)}
.bksd.e{background:#d6d0c6}.bksd.e i{background:repeating-linear-gradient(90deg,#ece8e1 0 3px,transparent 3px 6px)}
.bkhd{position:relative;display:block;width:58px;height:42px;margin:auto;background:#2b2a28;border-radius:5px}
.bkhd i{position:absolute;right:8px;bottom:8px;width:6px;height:6px;border-radius:50%;background:#7fd19b}
.bkhd.e{background:#d6d0c6}.bkhd.e i{background:#ece8e1}
.bkfo{display:inline-block;width:16px;height:12px;margin-right:6px;vertical-align:-1px;background:#C9B79C;border-radius:2px;position:relative;flex:none}
.bkfo::before{content:"";position:absolute;left:0;top:-3px;width:7px;height:4px;background:#C9B79C;border-radius:2px 2px 0 0}
.bkdest{margin:6px 0 4px;font-size:13px;color:var(--ink-2)}.bkdest b{color:var(--ink)}
.bkdest .lk{margin-left:6px}.bkdest .lk.first{margin-left:0}
.bklab{margin:12px 0 6px;font:700 11px/1 var(--sans);text-transform:uppercase;letter-spacing:.02em;color:var(--ink-2)}
.bklab[hidden]{display:none}
.bklab a{float:right;font-weight:400;text-transform:none;letter-spacing:-.01em;color:var(--ink);text-decoration:underline;text-underline-offset:3px}
.bklist,.bkdrives{display:grid;gap:6px}
.bkr{box-sizing:border-box;display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:14px;align-items:center;padding:8px;background:#fff;text-decoration:none;color:var(--ink);border:1px solid transparent;border-radius:0;cursor:pointer;font:inherit;text-align:left;width:100%}
.bkr:hover,.bkr:focus-visible{border-color:var(--ink);outline:0}
.bkr .im{width:52px;height:52px;overflow:hidden;background:#d9d4cc;display:grid;place-items:center;font:700 12px/1.1 var(--sans);text-align:center}
.bkr .im .bkhd{width:38px;height:28px;border-radius:4px}.bkr .im .bkhd i{right:5px;bottom:5px;width:4px;height:4px}
.bkr>span{min-width:0}
.bkr b{display:block;font:700 15px/1.2 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.bkr small{display:block;font-size:12.5px;color:var(--ink-2);margin-top:2px}
.bkr .ar{font-size:16px;color:var(--ink-2)}
.bknote{margin:6px 0 0;background:#fff;padding:12px 14px;font-size:13.5px;color:var(--ink);border-left:3px solid var(--accent)}
.bknote[hidden]{display:none}
.bktwo{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.bktwo button{box-sizing:border-box;padding:16px 14px;background:#fff;color:var(--ink);border:1px solid transparent;border-radius:0;cursor:pointer;font:700 15px/1.2 var(--sans);letter-spacing:-.01em}
.bktwo button:hover,.bktwo button:focus-visible{border-color:var(--ink);outline:0}
.bkpick{margin-top:6px}
.bkcrumbs{display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin:4px 0 8px;font-size:13px;color:var(--ink-2)}
.bkcrumbs button{display:inline-flex;align-items:center;gap:6px;border:0;background:none;padding:2px 0;font:700 13px/1.2 var(--sans);color:var(--ink);cursor:pointer;text-decoration:underline;text-underline-offset:3px;overflow-wrap:anywhere;text-align:left}
.bkcrumbs button:last-child{text-decoration:none;cursor:default}
.bkcrumbs .bkhd{width:20px;height:14px;border-radius:2px;margin:0;flex:none}.bkcrumbs .bkhd i{right:2px;bottom:2px;width:3px;height:3px}
.bkfind{box-sizing:border-box;width:100%;font:400 15px/1 var(--sans);letter-spacing:-.01em;padding:12px 14px;border:1px solid var(--line);border-radius:0;background:#fff;color:var(--ink);margin-bottom:10px}
.bkflist{display:grid;gap:2px;max-height:240px;overflow:auto;background:#fff;padding:4px}
.bkfrow{display:flex;align-items:center;gap:4px;width:100%;text-align:left;border:0;background:none;padding:9px 10px;font:500 14px/1.2 var(--sans);letter-spacing:-.01em;color:var(--ink);cursor:pointer}
.bkfrow:hover,.bkfrow:focus-visible{background:var(--cream);outline:0}
.bkfrow span:nth-child(2){flex:1;min-width:0;overflow-wrap:anywhere}.bkfrow .ar{color:var(--ink-2);font-size:18px}
.bkfnone{margin:0;padding:12px 10px;font-size:13px;color:var(--ink-2)}
.bkfnew{display:flex;align-items:center;gap:8px;margin-top:8px;background:#fff;padding:8px 10px}
.bkfnew input{flex:1;min-width:0;font:500 14px/1.2 var(--sans);padding:9px 10px;border:1.5px solid var(--ink);border-radius:0;background:#fff;color:var(--ink)}
.bkfhere{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:10px 0}.bkfhere small{font-size:12.5px;color:var(--ink-2)}
.bkstart{font:700 15px/1 var(--sans);letter-spacing:-.01em;padding:15px 22px;background:var(--accent);color:#fff;border:0;border-radius:0;cursor:pointer}
.bkstart:disabled{background:#cfc9bf;cursor:default}
.bkstart.sm{font-size:13px;padding:11px 14px;background:var(--ink)}
.bkstartrow{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:16px 0 6px}
.bkstartrow small{font-size:12.5px;color:var(--ink-2);max-width:320px}
.bkfoldline{margin:12px 0 0;font-size:13px;color:var(--ink-2)}
#bkProg{background:#fff;padding:14px;margin:4px 0 8px}
.bksteps{display:flex;gap:6px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-2)}.bksteps .on{color:var(--ink);font-weight:700}.bksteps .dn{color:#2f7d56}
.bknsl{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0}
.bknsl button{display:flex;flex-wrap:wrap;align-items:center;text-align:left;box-sizing:border-box;padding:12px 14px;background:#fff;color:var(--ink);border:1.5px solid transparent;border-radius:0;cursor:pointer;font:700 14px/1.2 var(--sans);letter-spacing:-.01em}
.bknsl button.on{border-color:var(--ink)}
.bknsl button small{width:100%;margin:4px 0 0 22px;font-weight:400;font-size:12px;color:var(--ink-2);overflow-wrap:anywhere}
.bknsl .bknote{grid-column:1/-1;margin:0}
.bkwho{display:grid;gap:6px;margin:10px 0 4px}.bkwho label{font:700 13px/1.3 var(--sans)}
.bkwho label small{display:block;font-weight:400;color:var(--ink-2);font-size:12px}
.bkwho input{box-sizing:border-box;font:500 15px/1.2 var(--sans);letter-spacing:-.01em;padding:11px 12px;border:1px solid var(--line);border-radius:0;background:#fff;color:var(--ink);width:100%}
.bktoast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(20px);z-index:40;background:var(--ink);color:#fff;padding:13px 18px;font:400 14px/1.35 var(--sans);opacity:0;max-width:min(520px,92vw);pointer-events:none}
.bktoast.on{opacity:1;transform:translateX(-50%) translateY(0)}.bktoast b{font-weight:700}
@media(max-width:560px){.bkflow{grid-template-columns:minmax(0,1fr)}.bkflow .arr{transform:rotate(90deg);height:24px}.bknsl,.bktwo{grid-template-columns:minmax(0,1fr)}}
@media (prefers-reduced-motion: no-preference){.bar2 i{transition:width .6s linear}.bktoast{transition:all .4s}}
"""


def box_html():
    """The box, drawn hidden on the home page; the page's script fills it, every word as text."""
    e = html.escape
    title = W("title").replace("<em>", "\x00").replace("</em>", "\x01")
    title = e(title).replace("\x00", "<em>").replace("\x01", "</em>")
    return (f"<div class='bkp' id='bk' hidden><div class='bkbox' role='dialog' aria-modal='true' aria-labelledby='bkT' tabindex='-1'>"
            f"<div class='bkh'><h3 id='bkT'>{title}</h3><button type='button' id='bkX' aria-label='{e(W('close'), quote=True)}'>&times;</button></div>"
            f"<div id='bkS'></div><div id='bkTop'></div>"
            f"<p class='bklab' id='bkLab' hidden>{e(W('your_backups'))} <a href='/backups'>{e(W('see_all'))}</a></p>"
            f"<div class='bklist' id='bkL'></div></div></div>"
            f"<div class='bktoast' id='bkToast' role='status'></div>")


# The page's script. It is given the words (BW), the job as the server saw it (BJOB) and the home page's own helpers
# ($, live, fill, many, assistant, note). It never builds markup from a name: every word goes in as text.
JS = r"""
const BK = (function(){
  const box = $('bk'), s1 = $('s1'), n1 = $('n1'); if (!box || !s1 || !n1) return null;
  let S = null, job = BJOB, DEST = null, PICK = null, LIST = null, FQ = '', NEWF = false, SECOND = null, SECPICK = false,
      SHOWNS = false, WHO = '', MSG = '', PMSG = '', busy = false, cleared = false, plugWait = false, asked = 0, opened = 0, timer = null, toastT = 0;
  window.BK_HOLD = false;
  const el = (tag, cls, text) => { const x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; };
  const btn = (cls, text, id) => { const b = el('button', cls, text); b.type = 'button'; if (id) b.id = id; return b; };
  function rich(node, s, o){ const re = /<(b|em)>(.*?)<\/\1>/g; let at = 0, m;
    while ((m = re.exec(s))) { node.append(fill(s.slice(at, m.index), o)); node.append(el(m[1], '', fill(m[2], o))); at = re.lastIndex; }
    node.append(fill(s.slice(at), o)); return node; }
  const pic = (kind, empty) => { const s = el('span', kind + (empty ? ' e' : '')); s.append(el('i')); s.setAttribute('aria-hidden', 'true'); return s; };
  const fo = () => { const s = el('span', 'bkfo'); s.setAttribute('aria-hidden', 'true'); return s; };
  const post = async (path, body) => { try { const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}); return await r.json(); }
    catch (e) { return {ok: false, words: BW.didnt_work}; } };
  const running = () => !!job && job.state === 'running';
  const ready = () => !!DEST;
  function tile(cls, picture, big, smalls){ const t = el('div', 'bktile' + (cls ? ' ' + cls : '')); const s = el('span'); s.append(el('b', '', big));
    (smalls || []).forEach(x => { if (x == null) return; if (typeof x === 'string') s.append(el('small', '', x)); else s.append(x); }); t.append(picture, s); return t; }
  function pathLine(names){ const s = el('small', 'fpath'); s.append(fo(), names.join(' \u203a ')); return s; }
  function destNames(){ if (!DEST) return null;
    if (DEST.kind === 'saved') return {drive: S.saved.drive, folders: S.saved.folders || [], computer: !!S.saved.computer};
    if (DEST.kind === 'computer') return {drive: BW.this_computer, folders: [], computer: true};
    return {drive: DEST.name, folders: DEST.path, computer: false}; }
  function destBody(){ return DEST.kind === 'saved' ? {saved: true} : DEST.kind === 'computer' ? {computer: true} : {d: DEST.d, name: DEST.name, path: DEST.path}; }

  // how it is going: the same few lines on the home card and in the box
  function linkBtn(v){ if (!v.link) return null; const b = btn('lk', v.link.words); b.dataset.bk = v.link.kind; b.onclick = e => { e.stopPropagation(); go(v.link.kind, b); }; return b; }
  // a backup the job stopped on: Try again starts the same one again (the Assistant knows what it was; the page sends nothing)
  function againBtn(v){ if (!v.again) return null; const b = btn('lk', v.again); b.dataset.bk = 'again'; b.onclick = e => { e.stopPropagation(); tryAgain(b); }; return b; }
  async function tryAgain(b){
    if (busy) return; busy = true; b.disabled = true;
    const d = await post('/backup-again', {}); busy = false; b.disabled = false;
    if (d && d.job) job = d.job;
    if (d && (d.ok || d.running)) { MSG = ''; paintCard(); if (!box.hidden) draw(); soon(300); return; }
    const say = (d && d.words) || BW.cant_start;
    if (!box.hidden) { MSG = say; draw(); } else { paintCard(); note(n1, say); }
  }
  function tail(v, sm, sub){ const ab = againBtn(v), lb = linkBtn(v); let any = !!sub;
    [ab, lb].forEach(x => { if (!x) return; if (any) sm.append(' \u00b7 '); sm.append(x); any = true; }); }
  function barOf(v){ const bar = el('div', 'bar2'), i = el('i'); i.style.width = Math.round(100 * (v.frac || 0)) + '%'; bar.append(i); return bar; }
  function paintCard(){
    if (!job || !job.show) return;
    const k = el('div', 'bk'), v = job;
    if (v.state === 'running') { k.append(el('b', '', v.head), barOf(v), el('small', '', v.sub || ''), el('small', 'nw', BW.no_wait)); }
    else { k.append(el('b', v.bad ? 'bad' : 'dn', v.head)); const sm = el('small', '', v.sub || ''); tail(v, sm, v.sub); k.append(sm);
      if (v.note) k.append(el('small', 'nt', v.note)); }
    n1.textContent = ''; n1.append(k); n1.dataset.bk = '1'; s1.classList.remove('live');
  }
  function prog(){
    const v = job, p = el('div', 'bk'); p.id = 'bkProg';
    p.append(el('b', v.state === 'running' ? '' : (v.bad ? 'bad' : 'dn'), v.head));
    if (v.state === 'running') p.append(barOf(v));
    if ((v.steps || []).length) { const st = el('div', 'bksteps'); v.steps.forEach((x, i) => { if (i) st.append(el('span', '', '\u00b7'));
      st.append(el('span', x.bad ? 'bad' : x.dn ? 'dn' : x.on ? 'on' : '', (x.dn ? '\u2713 ' : '') + x.t)); }); p.append(st); }
    const sub = v.state === 'problem' ? (v.sub_open || v.sub) : v.state === 'done' ? [v.safe_format ? BW.safe_format : '', v.backed || '', v.sub || ''].filter(Boolean).join(' ') : (v.sub || '');
    const sm = el('small', '', sub); tail(v, sm, sub); p.append(sm);
    if (v.state === 'done' && v.note) p.append(el('small', 'nt', v.note));
    if (v.state === 'running') p.append(el('small', 'nw', BW.run_nw));
    return p;
  }
  async function go(kind, b){
    if (kind === 'name' && job && job.backup) { const u = BNAME + '?backup=' + encodeURIComponent(job.backup);
      try { const r = await fetch(u, {cache: 'no-store'}); if (r.ok) { location.href = u; return; } } catch (e) {} }
    assistant('/backup-report', b, BW_OPENING);
  }
  function toast(bold, rest){ const t = $('bkToast'); t.textContent = ''; t.append(el('b', '', bold), ' ' + rest); t.classList.add('on'); hold();
    clearTimeout(toastT); toastT = setTimeout(() => { t.classList.remove('on'); hold(); }, 5200); }
  function hold(){ window.BK_HOLD = !box.hidden || $('bkToast').classList.contains('on'); }

  // ---- the box
  function draw(){
    const top = $('bkTop'), sub = $('bkS'); top.textContent = ''; sub.textContent = ''; $('bkL').textContent = ''; $('bkLab').hidden = true;
    if (!S) { sub.append(el('p', '', BW.loading)); return; }
    const run = running();
    if (run) sub.append(el('p', '', BW.run_top)); else sub.append(el('p', '', BW.safety), el('p', 'bksafe', BW.safe));
    if (!run && job && job.show && job.state !== 'idle' && !job.other_card) top.append(prog());
    // the two pictures
    const flow = el('div', 'bkflow'), arr = el('span', 'arr', '\u2192'); arr.setAttribute('aria-hidden', 'true');
    let cardT, driveT; const dn = destNames();
    if (run) { cardT = tile('', pic('bksd'), job.card || '', [job.from_folder ? BW.folder_small : BW.card_plain]);
      driveT = tile('', pic('bkhd'), job.drive || '', [(job.folders || []).length ? pathLine(job.folders) : null]); }
    else {
      cardT = S.card ? tile('', pic('bksd'), S.card.name, [fill(BW.card_small, {files: many(S.card.files)})]) : tile('e', pic('bksd', true), BW.nocard, [BW.nocard_small]);
      const ch = () => { const s = el('small'); const b = btn('lk', BW.change, 'bkChange'); b.onclick = change; s.append(b); return s; };
      if (dn) driveT = tile('', pic('bkhd'), dn.drive, [dn.computer && DEST.kind === 'computer' ? BW.computer_small : (dn.folders.length ? pathLine(dn.folders) : BW.top_of_drive), ch()]);
      else if (PICK) driveT = tile('e half', pic('bkhd'), PICK.name, [BW.half_small]);
      else if (S.saved && !S.saved.here && !cleared) driveT = tile('e', pic('bkhd', true), S.saved.drive, [BW.not_plugged, ch()]);
      else driveT = tile('e', pic('bkhd', true), BW.pick_drive, [BW.pick_drive_small]);
    }
    cardT.id = 'bkCard'; driveT.id = 'bkDrive';
    flow.append(cardT, arr, driveT); top.append(flow);
    if (run) { if (job.second) top.append(rich(el('p', 'bkdest'), BW.second_run, {drive: job.second})); top.append(prog()); return; }
    if (dn) {
      // how the shoot folders are named, with Change; the optional name; the second copy (asked each time)
      const inside = dn.folders.length ? dn.folders[dn.folders.length - 1] : (dn.computer ? 'Shoots' : dn.drive), nm = S.naming || {ways: []};
      const cur = (nm.ways || []).find(w => w.n === nm.current);
      const p = el('p', 'bkdest'); p.id = 'bkNaming';
      if (cur) rich(p, BW.dest_named, {folder: inside, way: cur.label}); else p.append(fill(BW.dest_way, {folder: inside}));
      const nb = btn('lk', BW.change, 'bkNs'); nb.setAttribute('aria-expanded', SHOWNS ? 'true' : 'false'); nb.onclick = () => { SHOWNS = !SHOWNS; draw(); }; p.append(' ', nb); top.append(p);
      if (SHOWNS) { const l = el('div', 'bknsl'); l.id = 'bkWays'; l.setAttribute('role', 'group'); l.setAttribute('aria-label', BW.ways_aria);
        (nm.ways || []).forEach(w => { const b = btn(w.n === nm.current ? 'on' : ''); b.dataset.ns = w.n; b.setAttribute('aria-pressed', w.n === nm.current ? 'true' : 'false');
          b.append(fo(), w.label, el('small', '', fill(BW.like, {example: w.example})));
          b.onclick = async () => { const d = await post('/backup-naming', {offered: w.n}); if (d && d.ok) { S.naming = d.naming; } else MSG = (d && d.words) || BW.didnt_work; draw(); }; l.append(b); });
        l.append(el('p', 'bknote', BW.nm_note)); top.append(l); }
      const who = el('div', 'bkwho'), lab = el('label', '', BW.who_label), inp = el('input'); lab.htmlFor = 'bkWho'; lab.append(el('small', '', BW.who_note));
      inp.id = 'bkWho'; inp.type = 'text'; inp.placeholder = BW.who_ph; inp.maxLength = 80; inp.value = WHO; inp.autocomplete = 'off'; inp.oninput = () => { WHO = inp.value; };
      who.append(lab, inp); top.append(who);
      const sp = el('p', 'bkdest'); sp.id = 'bkSecond';
      if (SECOND) { rich(sp, BW.second_on, {drive: SECOND.name}); const r = btn('lk', BW.remove, 'bkNo2'); r.onclick = () => { SECOND = null; SECPICK = false; draw(); }; sp.append(' ', r); }
      else { const a = btn('lk first', BW.second_add, 'bkAdd2'); a.onclick = addSecond; sp.append(a); }
      top.append(sp);
      if (SECPICK && !SECOND) { const dl = el('div', 'bkdrives'); dl.id = 'bkSecDrives'; dl.append(el('p', 'bklab', BW.second_which));
        others().forEach(x => dl.append(driveRow(x, () => { SECOND = {d: x.d, name: x.name}; SECPICK = false; draw(); }))); top.append(dl); }
    }
    if (!dn && !PICK) {
      const dl = el('div', 'bkdrives'); dl.id = 'bkDrives'; dl.append(el('p', 'bklab', S.first ? BW.where_first : BW.where_again));
      if ((S.drives || []).length) S.drives.forEach(x => dl.append(driveRow(x, () => { PICK = {d: x.d, name: x.name, path: []}; LIST = null; FQ = ''; NEWF = false; PMSG = ''; MSG = ''; if (SECOND && SECOND.d === x.d) SECOND = null; draw(); loadFolders(); })));
      else { dl.append(el('p', 'bkfnone', BW.no_drive)); const two = el('div', 'bktwo'), a = btn('', BW.plug_one, 'bkPlug'), c = btn('', BW.on_computer, 'bkComputer');
        a.onclick = () => { plugWait = true; draw(); }; c.onclick = () => { DEST = {kind: 'computer'}; plugWait = false; draw(); }; two.append(a, c); dl.append(two);
        if (plugWait) dl.append(el('p', 'bknote', BW.plug_wait)); }
      dl.append(el('p', 'bknote', S.first ? BW.only_once : BW.remembers)); top.append(dl);
    }
    if (PICK && !dn) top.append(picker());
    // the one button
    const sr = el('div', 'bkstartrow'), goB = btn('bkstart', BW.start, 'bkGo'); goB.disabled = !(S.card && dn) || busy; goB.onclick = () => start('card');
    sr.append(goB, el('small', '', !S.card ? BW.need_card : (!dn && !PICK) ? BW.need_drive : !dn ? BW.need_folder : BW.no_wait_start)); top.append(sr);
    const fl = el('p', 'bkfoldline'), fb = btn('lk', BW.folder_btn, 'bkFolder'); fb.disabled = busy; fb.onclick = () => { if (!ready()) { MSG = PICK ? BW.need_folder : BW.need_drive; draw(); return; } start('folder'); };
    fl.append(BW.folder_q + ' ', fb); top.append(fl);
    const m = el('p', 'bknote', MSG); m.id = 'bkMsg'; m.setAttribute('role', 'status'); m.hidden = !MSG; top.append(m);
    // the last few backups
    if (!S.first && (S.recent || []).length) { $('bkLab').hidden = false;
      S.recent.forEach(b => { const a = el('a', 'bkr'); a.href = '/backups'; const im = el('span', 'im'), d = new Date(String(b.added).slice(0, 10) + 'T12:00:00'); im.setAttribute('aria-hidden', 'true');
        if (!isNaN(d)) im.append(d.toLocaleDateString('en-US', {month: 'short'}), el('br'), String(d.getDate()));
        const t = el('span'), sh = b.shoots === 1 ? BW.shoots_one : fill(BW.shoots_many, {n: b.shoots});
        t.append(el('b', '', niceDay(b.added)), el('small', '', fill(b.checked ? BW.recent_checked : BW.recent_plain, {shoots: sh, count: countWords(b.photos, b.clips)})));
        const ar = el('span', 'ar', '\u2192'); ar.setAttribute('aria-hidden', 'true'); a.append(im, t, ar); $('bkL').append(a); }); }
  }
  function driveRow(x, on){ const b = btn('bkr dv'); b.dataset.d = x.d; const im = el('span', 'im'); im.append(pic('bkhd')); im.setAttribute('aria-hidden', 'true');
    const t = el('span'); t.append(el('b', '', x.name), el('small', '', fill(BW.free, {free: x.free}))); const ar = el('span', 'ar', '\u2192'); ar.setAttribute('aria-hidden', 'true');
    b.append(im, t, ar); b.onclick = on; return b; }
  function others(){ return (S.drives || []).filter(x => !(DEST && DEST.kind === 'drive' && x.d === DEST.d) && !(DEST && DEST.kind === 'saved' && S.saved && x.name === S.saved.drive)); }
  function addSecond(){ const o = others(); MSG = '';
    if (!o.length) { MSG = BW.second_none; refresh(); } else if (o.length === 1) SECOND = {d: o[0].d, name: o[0].name}; else SECPICK = true; draw(); }
  function change(){ DEST = null; PICK = null; LIST = null; SECOND = null; SECPICK = false; FQ = ''; NEWF = false; MSG = ''; PMSG = ''; SHOWNS = false; cleared = true; plugWait = false; draw(); refresh(); }

  // ---- which folder: opened like Finder
  function picker(){
    const w = el('div', 'bkpick'); w.id = 'bkPick'; const here = PICK.path.length ? PICK.path[PICK.path.length - 1] : '';
    w.append(el('p', 'bklab', fill(BW.which_folder, {drive: PICK.name})));
    const cr = el('div', 'bkcrumbs'), up = i => () => { if (i === PICK.path.length) return; PICK.path = PICK.path.slice(0, i); LIST = null; FQ = ''; NEWF = false; PMSG = ''; draw(); loadFolders(); };
    const c0 = btn('', null); c0.append(pic('bkhd'), PICK.name); c0.dataset.up = 0; c0.onclick = up(0); cr.append(c0);
    PICK.path.forEach((p, i) => { cr.append(el('span', '', '\u203a')); const c = btn('', p); c.dataset.up = i + 1; c.onclick = up(i + 1); cr.append(c); }); w.append(cr);
    if (LIST && LIST.folders.length >= BFIND) { const f = el('input', 'bkfind'); f.id = 'bkFind'; f.type = 'search'; f.value = FQ;
      f.placeholder = here ? fill(BW.find_in, {folder: here}) : fill(BW.find_on, {drive: PICK.name}); f.setAttribute('aria-label', f.placeholder);
      f.oninput = () => { FQ = f.value; rows(); }; w.append(f); }
    const fl = el('div', 'bkflist'); fl.id = 'bkFl'; w.append(fl);
    if (NEWF) { const nf = el('div', 'bkfnew'), inp = el('input'), mk = btn('bkstart sm', BW.make_it, 'bkMake'), cn = btn('lk', BW.cancel, 'bkCancel');
      inp.id = 'bkName'; inp.type = 'text'; inp.placeholder = BW.name_new; inp.setAttribute('aria-label', BW.name_new_aria); inp.maxLength = 80; inp.autocomplete = 'off';
      const make = async () => { const v = (inp.value || '').trim(); if (!v || busy) return; busy = true; mk.disabled = true;
        const d = await post('/backup-folder-new', {d: PICK.d, name: PICK.name, path: PICK.path, new: v}); busy = false;
        if (d && d.ok) { PICK.path = d.path; NEWF = false; FQ = ''; LIST = null; PMSG = d.words || ''; draw(); loadFolders(); } else { PMSG = (d && d.words) || BW.didnt_work; draw(); const n = $('bkName'); if (n) { n.value = v; n.focus(); } } };
      mk.onclick = make; cn.onclick = () => { NEWF = false; draw(); };
      inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); make(); } if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); NEWF = false; draw(); } };
      nf.append(fo(), inp, mk, cn); w.append(nf); }
    const fh = el('div', 'bkfhere');
    if (here) { const put = btn('bkstart sm', fill(BW.put_in, {folder: here}), 'bkHere'); put.onclick = () => { DEST = {kind: 'drive', d: PICK.d, name: PICK.name, path: PICK.path.slice()}; PICK = null; MSG = ''; draw(); const g = $('bkGo'); if (g && !g.disabled) g.focus(); }; fh.append(put); }
    else fh.append(el('small', '', BW.open_hint));
    if (!NEWF) { const nb = btn('lk', here ? fill(BW.new_folder_in, {folder: here}) : BW.new_folder, 'bkNew'); nb.onclick = () => { NEWF = true; PMSG = ''; draw(); const n = $('bkName'); if (n) n.focus(); }; fh.append(nb); }
    const pw = btn('lk', BW.pick_window, 'bkWindow'); pw.onclick = async () => { PMSG = BW.pick_waiting; draw(); const d = await post('/backup-pick', {});
      if (d && d.ok) { DEST = {kind: 'drive', d: d.d, name: d.name, path: d.path}; PICK = null; PMSG = ''; } else PMSG = (d && d.words) || ''; draw(); }; fh.append(pw);
    w.append(fh);
    const pm = el('p', 'bknote', PMSG); pm.id = 'bkPmsg'; pm.setAttribute('role', 'status'); pm.hidden = !PMSG; w.append(pm);
    w.append(el('p', 'bknote', BW.each_here));
    setTimeout(rows, 0);
    return w;
  }
  function rows(){ const fl = $('bkFl'); if (!fl || !PICK) return; fl.textContent = '';
    if (!LIST) { fl.append(el('p', 'bkfnone', BW.loading)); return; }
    const q = FQ.trim().toLowerCase(), names = LIST.folders.filter(n => !q || n.toLowerCase().includes(q));
    names.forEach(n => { const r = btn('bkfrow'); r.dataset.in = n; const ar = el('span', 'ar', '\u203a'); ar.setAttribute('aria-hidden', 'true'); r.append(fo(), el('span', '', n), ar);
      r.onclick = () => { PICK.path.push(n); LIST = null; FQ = ''; NEWF = false; PMSG = ''; draw(); loadFolders(); }; fl.append(r); });
    if (!names.length) fl.append(el('p', 'bkfnone', q ? fill(BW.no_match, {q: FQ.trim()}) : BW.none_here));
    if (LIST.more) fl.append(el('p', 'bkfnone', BW.more_folders)); }
  async function loadFolders(){ if (!PICK) return; const mine = ++asked, at = PICK;
    const d = await post('/backup-folders', {d: at.d, name: at.name, path: at.path});
    if (mine !== asked || PICK !== at) return;
    if (d && d.ok) { LIST = {folders: d.folders || [], more: !!d.more}; draw(); if (NEWF && $('bkName')) $('bkName').focus(); return; }
    PMSG = (d && d.words) || BW.didnt_work;
    if (at.path.length) { at.path = at.path.slice(0, -1); LIST = null; draw(); const keep = PMSG; loadFolders().then(() => { if (PICK === at && !PMSG) { PMSG = keep; draw(); } }); }
    else { PICK = null; LIST = null; MSG = PMSG; draw(); refresh(); } }

  // ---- Start the backup (the only way to start): a card, or a folder picked in the computer's own window
  async function start(source){
    if (busy || !ready() || (source === 'card' && !S.card)) return; busy = true; MSG = source === 'folder' ? BW.folder_pick : BW.starting; draw();
    const d = await post('/backup-start', {source, card: S.card ? S.card.name : null, dest: destBody(), second: SECOND ? {d: SECOND.d, name: SECOND.name} : null, shoot_name: WHO});
    busy = false;
    if (d && d.ok) { job = d.job || job; MSG = ''; close(); paintCard();
      toast(fill(BW.backing_up, {card: d.from || '', where: d.where || ''}) + (d.second ? ' + ' + d.second : '') + '.', BW.toast_start_rest); soon(300); return; }
    if (d && d.job) job = d.job;
    MSG = d && d.cancelled ? '' : ((d && d.words) || BW.cant_start); draw(); if (d && d.running) { paintCard(); soon(300); }
  }

  // ---- open, close, and keeping up with the card, the drives and the job
  async function refresh(){ const mine = ++opened; let d = null; try { d = await (await fetch('/backup-popup', {cache: 'no-store'})).json(); } catch (e) {}
    if (mine !== opened || box.hidden) return false; if (!d || !d.ok) { if (!S) { $('bkS').textContent = ''; $('bkS').append(el('p', '', BW.didnt_work)); } return false; }
    const first = !S, was = S ? JSON.stringify([S.card, S.drives, S.saved]) : ''; const keepNaming = S && S.naming; S = d; if (keepNaming && SHOWNS) S.naming = keepNaming;
    if (d.job && d.job.ok) job = d.job;
    if (first) { DEST = (S.saved && S.saved.here) ? {kind: 'saved'} : null; draw(); return true; }
    if (was !== JSON.stringify([S.card, S.drives, S.saved])) {
      if (PICK && !(S.drives || []).some(x => x.d === PICK.d && x.name === PICK.name)) { PICK = null; LIST = null; }
      if (DEST && DEST.kind === 'drive' && !(S.drives || []).some(x => x.d === DEST.d && x.name === DEST.name)) DEST = null;
      if (DEST && DEST.kind === 'saved' && !(S.saved && S.saved.here)) DEST = null;
      if (DEST && DEST.kind === 'computer' && (S.drives || []).length) DEST = null;
      if (SECOND && !(S.drives || []).some(x => x.d === SECOND.d && x.name === SECOND.name)) SECOND = null;
      if (!DEST && !PICK && !cleared && S.saved && S.saved.here) DEST = {kind: 'saved'};      // their drive, plugged in while the box was open
      const a = document.activeElement; if (a && a.tagName === 'INPUT' && box.contains(a)) return true;       // never under their typing: the next look redraws
      draw(); }
    return true; }
  function open(){
    if (!live) { note(s1.querySelector('.seeall') || n1, BW_NOT_RUNNING); return; }
    S = null; DEST = null; PICK = null; LIST = null; FQ = ''; NEWF = false; SECOND = null; SECPICK = false; SHOWNS = false; WHO = ''; MSG = ''; PMSG = ''; busy = false; cleared = false; plugWait = false;
    box.hidden = false; hold(); draw(); box.querySelector('.bkbox').focus(); refresh(); soon(1500);
  }
  function close(){ if (box.hidden) return; box.hidden = true; hold(); try { s1.focus(); } catch (e) {} }
  function soon(ms){ clearTimeout(timer); timer = setTimeout(tick, ms); }
  async function tick(){
    let v = null; try { v = await (await fetch('/backup-job', {cache: 'no-store'})).json(); } catch (e) {}
    if (v && v.ok) { const was = job; job = v;
      if (was && was.state === 'running' && v.state === 'done' && v.show) toast(v.from_folder ? BW.toast_done_folder_b : BW.toast_done_b, [v.checked ? BW.toast_done_checked : '', v.backed || ''].filter(Boolean).join(' '));
      if (v.show) paintCard(); else if (n1.dataset.bk && box.hidden && !window.MK_HOLD) { location.reload(); return; }
      if (!box.hidden && S) { const moved = !was || was.state !== v.state || was.step !== v.step || was.show !== v.show;
        if (moved) { const a = document.activeElement; if (!(a && a.tagName === 'INPUT' && box.contains(a)) || v.state === 'running') draw(); }
        else if (v.state === 'running' && $('bkProg')) $('bkProg').replaceWith(prog()); } }
    // a card going in, a drive being plugged in: looked for only while the box is waiting on one
    if (!box.hidden && S && !running() && (!S.card || (!DEST && !PICK))) refresh();
    soon(running() ? 1500 : (box.hidden ? 5000 : 3000));
  }
  $('bkX').onclick = close;
  box.addEventListener('click', e => { if (e.target === box) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) { e.preventDefault(); close(); } });
  s1.addEventListener('click', e => { if (e.target.closest('a, button')) return; e.preventDefault(); open(); });
  s1.addEventListener('keydown', e => { if (e.target !== s1) return; if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); clicked('backup'); open(); } });
  // the box the server drew on the card (a reload while a backup runs or has just finished): its link works too
  n1.querySelectorAll('button[data-bk]').forEach(b => { b.onclick = e => { e.stopPropagation(); if (b.dataset.bk === 'again') tryAgain(b); else go(b.dataset.bk, b); }; });
  if (live) soon(job && job.state === 'running' ? 800 : 2500);
  // "Back up another card" on the Name your shoots page lands here as /home#backup: the box opens by itself
  // (the mark is taken off the address, so a reload does not open it again)
  if (live && location.hash === '#backup') { try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {} open(); }
  return {open, close, state: () => ({S, job, DEST, PICK, LIST, SECOND})};
})();
"""


def script():
    """The script as the home page carries it: the words, the job as it stands, then JS."""
    import home_base
    words = page_words()
    head = ("const BW = " + _json_for_script(words) + ";const BJOB = " + _json_for_script(job_view()) + ";const BFIND = %d;" % FIND_FROM
            + "const BNAME = " + _json_for_script(NAME_SHOOTS) + ";const BW_OPENING = " + _json_for_script(home_base.W("opening_report"))
            + ";const BW_NOT_RUNNING = " + _json_for_script(home_base.W("not_running")) + ";")
    return head + JS


def _json_for_script(obj):
    """JSON that can sit inside a <script>: "<" written as its escape, so no name can ever close the script."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
