#!/usr/bin/env python3
"""The Assistant's home page (Nicole's v28, Nov 17; posts first since her v29, Nov 19), in the Claude app's browser pane.

Top to bottom, in Nicole's v30 look (her pages/home-new-look.html and screenshot 01, Nov 21): the bar ("THE
ASSISTANT" in her one accent, by Horizon Found, the date, Open my Assistant folder); the hello, ONE wide photo framed
on its faces (from the 1600 px copies) with a greeting and one line from her approved lines over it (hello_lines.py:
it only lifts them up, no reminders, no button, no "Another hello"); Turn your shoots into posts with four photo
tiles, Reels, Carousels, Stories and Captions, and See all my post kits alone under them; My posting queue (with the
last three posts of their grid) beside Back up a card and My editing queue stacked, each on its own light card, each
saying what is going on right now; the monthly recap card on tan; and the Your year bar in its dates. No list of
post kits, so it stays clean after years of shoots: every backup and every post kit is on its own screen
(home_base.py). The v30 look is this page's alone (HOME_LOOK, one block); every other page keeps look.py's. Served
live by the posting server at /home (posting_queue.py serve), which also opens folders and pages for its buttons
and records which card was pressed.

A click in the pane cannot type into the chat for them, so the two steps that need a conversation show, on their
own screens, what to paste ("backup now", "make my posts") with a Copy button. Every press of a card is kept in
~/.studio/journey.json, so whatever they say next, the assistant already knows what they pressed, whether it is
their first time there, and what they did last time in that category: first time, a short explanation and "want
to dive in?"; later, pick up where they left off.

Kept by this page, beside what was already kept: ~/.studio/home-recap.json (whether they hid the monthly recap:
for one month, or for good; home-recap.prev.json is the choice before). Routes of its own on the posting server:
POST /home-recap (behind the pickers' same-page-only guard). The faces are faces.py's (GET /kit-faces).

    python3 home.py page            write ~/.studio/home.html (a saved copy; the live page is /home)
    python3 home.py url             the live page's address (starts the posting server if needed)
    python3 home.py pending         clicks Claude hasn't answered yet, with that category's history (JSON)
    python3 home.py seen            mark them answered
    python3 home.py did <category> [--note "..."]   remember something done in a category
    python3 home.py journey         the whole record
    python3 home.py hello [--mark]  which hello to give: a first-time introduction, or the day's rundown (JSON)

Categories: backup, posts, queue, posting, reel, folder.
"""
import argparse
import errno
import html
import json
import os
import sys
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import home_base  # noqa: E402  (the home base's words, look and two screens)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
from where import same_place  # noqa: E402  (two recorded paths, the same folder? case-blind on a PC)
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JOURNEY = HOME / "journey.json"
PAGE = HOME / "home.html"
CATEGORIES = ("backup", "posts", "queue", "posting", "reel", "folder")


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


def now():
    return datetime.now().isoformat(timespec="seconds")


# ---------- the journey: what they've pressed and done ----------

# One read, change and save of the record at a time in this program: the page server answers two clicks at once,
# and on a PC a save can't put the new record in place while another thread has the old one open to read it
# (seen on GitHub's Windows machines, Nov 6: six threads saving at once lost 16 to 31 of 240 saves). A Mac never
# refused, and gives the same bytes either way.
_JOURNEY_LOCK = threading.RLock()


def load_journey():
    for i in range(25):
        try:
            if not JOURNEY.exists():
                break
            return json.loads(JOURNEY.read_text(encoding="utf-8"))
        except ValueError:
            break
        except PermissionError:
            # on a PC, opening the record in the instant another program puts a new one in place is refused:
            # wait a moment (about three seconds in all). A Mac never refuses; a real refusal is passed on.
            if not this_computer.WINDOWS or i == 24:
                raise
            time.sleep(0.01 * (i + 1))
    return {"clicks": [], "done": {}, "hellos": {"first": None, "count": 0}}


def save_journey(j):
    HOME.mkdir(parents=True, exist_ok=True)
    # A scratch name of this program's and this thread's own: a command (`home.py did`, `hello --mark`) and a
    # click on the home page can save at the same moment, and with one shared name ("journey.json.tmp", before
    # Nov 6) one could take the other's file away mid-save. The bytes saved are the same as ever.
    tmp = JOURNEY.with_name(f"{JOURNEY.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(j, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, JOURNEY)   # on a PC, waits a moment if the page server is reading it right then
    except BaseException:
        try:
            tmp.unlink()                      # only the scratch copy just written here, never the record itself
        except OSError:
            pass
        raise


def record_click(item):
    if item not in CATEGORIES:
        return False
    with _JOURNEY_LOCK:
        j = load_journey()
        j["clicks"].append({"at": now(), "item": item, "seen": False})
        j["clicks"] = j["clicks"][-50:]
        save_journey(j)
    return True


def record_done(category, note=None):
    with _JOURNEY_LOCK:
        j = load_journey()
        d = j["done"].setdefault(category, {"first": None, "count": 0})
        d["first"] = d["first"] or now()
        d["last"] = now()
        d["count"] += 1
        if note:
            d["note"] = note
        save_journey(j)
    return d


def pending():
    """Unanswered clicks, newest last, each with what they've done in that category before."""
    j = load_journey()
    out = []
    for c in j["clicks"]:
        if c.get("seen"):
            continue
        d = j["done"].get(c["item"]) or {}
        out.append({"item": c["item"], "at": c["at"], "first_time": not d.get("count"),
                    "times_before": d.get("count", 0), "last_done": d.get("last"), "last_note": d.get("note")})
    return out


def mark_seen():
    with _JOURNEY_LOCK:
        j = load_journey()
        for c in j["clicks"]:
            c["seen"] = True
        save_journey(j)


# ---------- the hello: an introduction the first time, the day's rundown once they know their way around ----------

HELLO_WORDS = {
    "first": "They have never been here. Introduce yourself with the first-time script in the skill. No rundown of the day.",
    "new": "They've said hello before but haven't done anything yet. One warm line and the one first step. No introduction again, no rundown.",
    "getting-started": "They've done one side but not the other. The day in a line or two if there is anything in it, then one line inviting them to what they haven't tried.",
    "regular": "They know their way around. The day in two or three lines, then what they can say next.",
}


def hello(mark=False):
    """Which hello to give (Dustin, Nov 5: a brand-new photographer who said hi got "nothing due, nothing
    waiting, no card in", a status report on a day with nothing in it, where an introduction belonged).
    The stage comes from what they have actually done, never from how many times they've said hello:
    first (nothing done, never greeted), new (nothing done, greeted before), getting-started (a backup or
    posts, not both), regular (both)."""
    j = load_journey()
    h = j.get("hellos") or {"first": None, "count": 0}
    g = gather()
    done = {c: d for c, d in (j.get("done") or {}).items() if d.get("count")}
    did = {"backup": bool(g["setup"] or done.get("backup")),
           "posts": bool(done.get("posts") or done.get("reel") or g["kits"])}
    if not (did["backup"] or did["posts"] or done):
        stage = "first" if not h.get("count") else "new"
    elif did["backup"] and did["posts"]:
        stage = "regular"
    else:
        stage = "getting-started"
    out = {"stage": stage, "what_to_say": HELLO_WORDS[stage], "hellos_before": h.get("count", 0),
           "name": brand.own_name(), "card_in": bool(g["card"]),
           "not_tried": [k for k in ("backup", "posts") if not did[k]],
           "done": {c: {"times": d["count"], "last_note": d.get("note")} for c, d in done.items()}}
    if mark:
        with _JOURNEY_LOCK:
            j = load_journey()               # read again: a click may have been saved while the day was gathered
            h = j.get("hellos") or {"first": None, "count": 0}
            h["first"] = h.get("first") or now()
            h["last"] = now()
            h["count"] = h.get("count", 0) + 1
            j["hellos"] = h
            save_journey(j)
    return out


# ---------- what matters today ----------

def card_in():
    """A memory card mounted right now: a volume with a DCIM folder. Name and rough count, or None."""
    pretend = os.environ.get("STUDIO_CARD_FOR_TESTS")      # the tests' own: "none", or "EOS_DIGITAL:1234" (no drive is looked at)
    if pretend:
        name, _, n = pretend.partition(":")
        return {"name": name, "files": int(n)} if n.isdigit() else None
    for c in this_computer.cards():   # /Volumes on a Mac, drive letters on a PC
        n = 0
        for root, _, files in os.walk(Path(c["path"]) / "DCIM"):
            n += len([f for f in files if not f.startswith(".")])
            if n > 20000:
                break
        return {"name": c["shown"], "files": n}
    return None


def fingerprint():
    """Changes when anything the page shows might have changed: the Studio File, the queues, the journey,
    the Content folder, a card coming or going. The page polls this and reloads itself when it moves."""
    parts = []
    try:  # an update to the Assistant counts as a change too, so an open home page reloads into the new one
        import fresh
        parts.append(str(fresh.code_stamp()))
    except Exception:
        parts.append("?")
    # (not the record of what was pressed: the page shows nothing from it since Nov 14, and reloading after a
    # press wiped the line a press had just put under its button)
    for f in ("studio.json", "queue.json", "posting.json", "kit-archive.json", "posting-url.txt"):
        try:
            parts.append(str(int((HOME / f).stat().st_mtime)))
        except OSError:
            parts.append("-")
    try:
        import posts
        h = posts.home()
        parts.append(str(int((h / posts.CONTENT_NAME).stat().st_mtime)) if h and (h / posts.CONTENT_NAME).is_dir() else "nohome")
    except Exception:
        parts.append("?")
    try:
        c = card_in()
        parts.append(c["name"] if c else "nocard")
    except Exception:
        parts.append("?")
    return "|".join(parts)


def gather():
    """Everything the page shows, read from what the Studio already keeps. Each part fails soft."""
    g = {"today": date.today().strftime("%A, %B ") + str(date.today().day), "notes": [], "due": [], "tank": None,
         "card": None, "recent": [], "kits": [], "home_folder": None, "setup": False, "done": load_journey()["done"], "waiting": 0}
    try:
        import studio_file
        g["setup"] = bool(studio_file.load().get("drives", {}).get("session"))
    except Exception:
        pass
    try:
        import edit_queue
        q = edit_queue.load()
        for n, s in edit_queue.heads_up(q):
            g["notes"].append(("late" if n < 0 else "soon", f"{s['name']}: {edit_queue.due_words(s.get('due'))}"))
        g["waiting"] = len(edit_queue.waiting(q))
        for s in edit_queue.waiting(q)[:4]:
            g["due"].append({"name": s["name"], "due": edit_queue.due_words(s.get("due")), "late": bool(s.get("due")) and s["due"] < date.today().isoformat()})
        shoots = sorted(q["shoots"], key=lambda s: (s.get("shot") or "", s.get("added", "")), reverse=True)
        for s in shoots[:6]:
            g["recent"].append({"id": s["id"], "name": s["name"], "shot": s.get("shot"), "count": s.get("count"),
                                "thumbs": [t for t in (s.get("thumbs") or [])[:3] if (HOME / t).exists()], "status": s.get("status"),
                                "report": bool(s.get("studio"))})
        # the newest backup, so its report is one click away from Home (Dustin, Nov 5)
        backed = [s for s in q["shoots"] if s.get("studio")]
        if backed:
            last = max(backed, key=lambda s: s.get("added", ""))
            same = [s for s in backed if same_place(s.get("studio"), last["studio"])]
            g["last_backup"] = {"when": (last.get("added") or "")[:10], "shoots": len(same), "photos": sum(s.get("count") or 0 for s in same),
                                "clips": sum(s.get("clips") or 0 for s in same)}
    except (Exception, SystemExit):     # an unreadable queue.json ends edit_queue.load with SystemExit: the page still comes
        pass
    try:
        import posting_queue
        p = posting_queue.load()
        if p.get("pieces") or p.get("interval"):
            g["tank"] = posting_queue.tank_words(p)
        for r in posting_queue.reminders(p):
            g["notes"].append(("post", r if isinstance(r, str) else r.get("words", "")))
    except Exception:
        pass
    try:
        import posts
        h = posts.home()
        if h:
            g["home_folder"] = str(h)
            # every shoot folder in Your Content that holds a kit record, also one whose page was never written
            # (Nicole, v25: her newest shoot didn't show until its hidden page was made)
            g["kits"] = [k for k in posts.kits(h) if k.get("kit") or (Path(k["path"]) / ".kit" / "kit.json").is_file()][:6]
    except Exception:
        pass
    try:
        g["card"] = card_in()
    except Exception:
        pass
    return g


# ---------- the page ----------
#
# The home page, top to bottom (Nicole's v30, Nov 21; v28 and v29 before it, built our way):
#   the bar          the name in her accent, the date (hidden under 560 px), Open my Assistant folder (a link-style
#                    button, what it did shown beside it)
#   the hello        one wide photo framed on its faces (faces.py), 1.22x toward them, changing every few seconds;
#                    a greeting and one line from her approved lines (hello_lines.py), kept for a visit
#   posts first      Turn your shoots into posts, the four tiles (data-make: what each makes), See all my post kits;
#                    My posting queue beside Back up a card and My editing queue, each with what is going on now
#   the recap card   the month's numbers (wrapped.py), Watch, and the x that hides it (kept in home-recap.json)
#   Your year        the bar, only in its dates (Dec 1 to Jan 15, after about a year: wrapped.home_answers)
# Everything on it is read fresh, and only read, from what the Assistant already keeps (the hello's choice is the one
# thing written: hello_lines keeps it for a visit). The server draws the words; the page's script loads the photos.
# No path is in the page: a photo is a kit's folder name and a number (/kit-photo), a face a kit and numbers.

# The words to paste in the chat for the two steps that start a conversation (shown on their own screens).
SAY = {"backup": home_base.WORDS["b_say"], "posts": home_base.WORDS["m_say"], "setup": "set up my Assistant folder"}

# Nicole's words (her v30 pages/home-new-look.html, Nov 21; v28's home-test.html and v29's home-preview.html before
# it), whole. "You would say what it is": the labels are plain on purpose (her section 10); do not make them clever.
# <em> is hers (the accent word: "into posts"; on the cards it is drawn plain in the v30 look). {…} is filled in.
# Gone in v30, by her ask (UPDATE-v30 sections 2 and 3): "↻ Another hello", the hello's button and every reminder
# line in it, the "Newest: …" box beside See all my post kits, and the heading "Also in your Assistant" (hers hides it).
WORDS = {
    "folder": "Open my {short} folder",
    "hello_plain": "Hello.",
    "s3_n": "Turn your shoots <em>into posts</em>",
    "s3_p": "Turn your shoot into reels, carousels, stories, and captions.",
    "s3_create": "Create your post kits →",         # the button with no post kits yet
    "s3_see": "See all my post kits →",             # the same button once there are some
    # the four tiles (her section 4): a photo each, the word on it
    "t_reel": "Reels",
    "t_carousel": "Carousels",
    "t_stories": "Stories",
    "t_captions": "Captions",
    "s1_n": "Back up <em>a card</em>",
    "s1_p": "Copies your card to your drive, checks every photo, and sorts it into shoots.",
    "s2_n": "My editing <em>queue</em>",
    "s2_p": "The shoots you need to edit and when they're due.",
    "s4_n": "My posting <em>queue</em>",
    "s4_p": "Your posts ready to go, and how your grid will look.",
    "s4_go": "Open my posting queue →",
    "s4_grid": "Your grid, newest first",
    # what is going on right now, card by card
    "n1_card": "A card is in",
    "n1_card_small": "{name} · about {files} files",
    "n1_last": "Last backup {day}",
    "n1_last_small": "{count}, every one checked",
    "n1_none": "No backups yet",
    "n1_none_small": "Put a card in to start",
    "n2_one": "1 shoot waiting",
    "n2_many": "{n} shoots waiting",
    "n2_due": "{name} · due {day}",
    "n2_none": "All caught up",
    "n2_none_small": "Nothing waiting to edit",
    "n4_today": "Today: {who} {kind}",
    "n4_late_too": "{who} {kind} is late too",
    "n4_ready": "{n} ready to go",
    "n4_waiting": "{who} {kind} is waiting",
    "n4_was_down": "It was down for {day}",
    "n4_none": "Nothing lined up yet",
    "n4_none_small": "Make posts, then add them here",
    "n4_days": "About {n} days of posts",
    # the monthly recap card and the Your year bar
    "rc_t": "Your {label}, <em>{word}</em>",
    "watch": "Watch",
    "rc_hide_title": "Hide",
    "rc_hide_aria": "Hide the monthly recap",
    "rc_month": "Hide it for this month",
    "rc_all": "Stop showing monthly recaps",
    "rc_show": "Show my monthly recap",
    "yr_b": "Your {year}, <em>wrapped.</em>",
    "yr_small": "Your year with your assistant, story by story. Ready to share.",
    # the four tiles ask which shoot, then go straight there (her section 4; screenshots 02 and 03)
    "mk_reel": "Create a <em>reel</em>",
    "mk_carousel": "Create a <em>carousel</em>",
    "mk_stories": "Create your <em>stories</em>",
    "mk_captions": "Write your <em>captions</em>",
    "mk_sub": "Which shoot do you want to make it from?",
    "mk_sub_none": "Start with a shoot: pick the folder with your finished photos.",
    "mk_new": "A new shoot",
    "mk_new_small": "Pick the folder with your finished photos",
    "mk_shoots": "Your shoots",
    "mk_vault": "My vault",
    "mk_vault_small": "Mix photos and clips from all your shoots",
    "mk_find": "Search your shoots",
    "mk_nothing": "Nothing matches \"{q}\".",
    "mk_close": "Close",
    "mk_photos": "{n} photos",
}
# Ours, where hers has none. Each is a draft for Dustin and Nicole.
OUR_WORDS = {
    # the last backup, when "every one checked" would not be true of it: no claim is made that was not measured
    "n1_last_plain": "{count}",
    "n1_last_sample": "Keep the card: this was a sample",          # the report's own words for a sample backup
    "n1_last_look": "Something needs a look: see the report",      # hers, from the Back up a card screen
    # ready posts and no posting rhythm set: days of posts can't be worked out, so none are claimed
    "n4_no_rhythm": "No posting rhythm set yet",
    "n4_day": "About 1 day of posts",
    "n4_single": "single post",                                     # a piece of the kind "single", said in words
    # the recap card: one link for the whole card (hers is the card itself), and a save that did not work
    "rc_watch_aria": "Watch your {label} recap",
    "yr_watch_aria": "Watch your {year}, story by story",
    "rc_didnt": "That didn't work. Try again in a moment.",
    # the four tiles, for a screen reader (the word on the photo says what it is; this says where it goes)
    "t_aria": "{word}: make them from one of your shoots",
    # "Create a reel: which shoot?" (her section 4), where hers has none
    "mk_photo": "{n} photo",                                        # one photo (hers always says "photos")
    "mk_picking": "Pick the folder in the window that opened. Your photos are copied, never moved.",
    "mk_list_cant": "Couldn't load your shoots. Try again in a moment.",
    "mk_didnt": "That didn't work. Try again in a moment.",
}

def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key] if key in OUR_WORDS else home_base.W(key)


# ---------- hiding the monthly recap: kept with the photographer's own records, never in the browser ----------
#
# Hers keeps it in the browser (her test page) and says: "In the real Assistant, keep it with the photographer's
# settings." Ours:  ~/.studio/home-recap.json   {"hide": "2026-11" | "all" | ""}   (home-recap.prev.json: before)

RECAP = HOME / "home-recap.json"
RECAP_PREV = HOME / "home-recap.prev.json"
_RECAP_LOCK = threading.Lock()
POST_CAP = 2000                 # a press on the card's menu is a few dozen bytes


def recap_hide():
    """What they chose: "all" (stop showing monthly recaps), a month "2026-11" (hidden for that month), or ""."""
    try:
        d = json.loads(RECAP.read_text(encoding="utf-8"))
        h = d.get("hide") if isinstance(d, dict) else ""
    except (OSError, ValueError):
        return ""
    return h if h == "all" or _month_ok(h) else ""


def _month_ok(m):
    return isinstance(m, str) and len(m) == 7 and m[:2] == "20" and m[2:4].isdigit() and m[4] == "-" and m[5:] in tuple("%02d" % i for i in range(1, 13))


def recap_hidden(month):
    h = recap_hide()
    return h == "all" or (bool(month) and h == month)


def set_recap_hide(hide):
    """Save the choice ("all", a month, or "" to show it again), whole, with the choice before kept beside it.
    A press that changes nothing writes nothing."""
    if hide not in ("all", "") and not _month_ok(hide):
        raise ValueError("not a month")
    with _RECAP_LOCK:
        if recap_hide() == hide and (hide or not RECAP.exists()):
            return hide
        HOME.mkdir(parents=True, exist_ok=True)
        mark = f"{os.getpid()}-{threading.get_ident()}"
        if RECAP.is_file():
            tmp = RECAP_PREV.with_name(f"{RECAP_PREV.name}.{mark}.tmp")
            tmp.write_bytes(RECAP.read_bytes())
            this_computer.replace(tmp, RECAP_PREV)
        tmp = RECAP.with_name(f"{RECAP.name}.{mark}.tmp")
        try:
            tmp.write_text(json.dumps({"hide": hide, "changed": now()}, indent=1), encoding="utf-8")
            this_computer.replace(tmp, RECAP)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
        return hide


# ---------- what is going on right now ----------

# hers (hello.js who()): "Katie Austin Maternity" -> "Katie’s"; anything else stays whole
_NOT_A_NAME = ("The", "At", "A", "An", "My", "Our", "Test", "Home", "Family", "Fall", "Spring", "Summer", "Winter", "Holiday", "Christmas")


def who(name):
    name = str(name or "").strip()
    try:                                # the vault (v29) reads whole, "My vault reel is waiting": one helper says so
        import vault
        if vault.who(name) is not None:
            return name
    except Exception:  # noqa: BLE001
        pass
    first = (name.split() or [""])[0]
    if len(first) > 1 and first[0].isupper() and first[1:].islower() and first.isalpha() and first.isascii() and first not in _NOT_A_NAME:
        return first + "’s"
    return name


def short_day(iso):
    """ "Nov 13", as her boxes write a day (the year left off)."""
    try:
        d = date.fromisoformat(str(iso)[:10])
        return d.strftime("%b ") + str(d.day)
    except ValueError:
        return ""


def _today():
    try:
        import edit_queue
        return edit_queue.today()               # STUDIO_TODAY, for tests, as the queues read it
    except Exception:  # noqa: BLE001
        return date.today()


class _Photos:
    """A kit's small copies, by number, for one drawing of the page: which there are (and their version mark for
    the address), and which kits still need theirs made."""

    def __init__(self):
        self.by_kit, self.need = {}, {}

    def _kit(self, name):
        if name not in self.by_kit:
            got = {}
            try:
                import arrange
                import kit as kit_mod
                kit = arrange.kit_by_name(name)
                if kit is not None:
                    rows = arrange.sheet_rows(kit)
                    photos, _ = arrange.page_photos(kit, kit_mod.load_rec(kit), rows)
                    got = {"kit": kit, "rows": rows, "photos": {p["n"]: p for p in photos}}
            except (Exception, SystemExit):  # noqa: BLE001
                got = {}
            self.by_kit[name] = got
        return self.by_kit[name]

    def one(self, name, n):
        """{"kit", "n", "v"} for a photo that can be shown now or soon (its small copy is made, or can be), else None."""
        k = self._kit(name)
        p = (k.get("photos") or {}).get(n)
        if not p or (p["missing"] and not p["have"]):
            return None
        if not p["have"]:
            self.need[name] = k
        return {"kit": name, "n": n, "v": p["v"], "way": p.get("way") or ""}

    def start(self):
        """Have the copies that are missing made, in a process of their own (as the kit page does)."""
        for k in self.need.values():
            try:
                import arrange
                if not arrange.cant_make(k["kit"], k["rows"]):
                    arrange.start_previews(k["kit"])
            except (Exception, SystemExit):  # noqa: BLE001
                pass


def photo_src(p):
    """A small copy's address: the kit's folder NAME and the photo's number, never a path."""
    return "/kit-photo?kit=%s&n=%d&size=s&v=%s" % (quote(p["kit"], safe=""), p["n"], quote(p.get("v") or "", safe=""))


def _thumb_src(t):
    """A posting piece's small picture ("posting-thumbs/<file>") as an address of this server, or None."""
    try:
        if not isinstance(t, str) or not t.startswith(("posting-thumbs/", "feed/")) or "\\" in t or ".." in t.split("/"):
            return None
        if not (HOME / t).is_file():
            return None
        return "/" + quote(t, safe="/")
    except (OSError, ValueError):
        return None


# ---------- the photos on the page (Nicole's v30 sections 2 and 4) ----------
#
# The hello: ONE wide photo at a time, horizontal favorites first ("they crop best into a wide strip"), the shoot the
# hello's line names first, then the other shoots taking turns; a few more photos of any shape only when there are
# fewer than HELLO_FEW wide ones. The tiles: four photos, each from a different shoot when there are four shoots
# (fewer: the shoots take turns, a different photo each time), and the page takes the first of a tile's few
# candidates that has a face. Every photo is a kit's folder name and a number (/kit-photo, arrange.py's route), never a path,
# and only the kit's own copies are ever sent (the 1600 px one, size=l; never the photo itself).
HELLO_MOST = 8          # photos the hello goes through
HELLO_FEW = 3           # fewer wide favorites than this: favorites of any shape join after them
TILE_CANDS = 6          # photos a tile may choose from (the first with a face wins)


def _shoots(got):
    """The shoots the photos come from, newest first: [(kit folder, favorite numbers)]. Only the post kits the post
    kits screen lists and has not archived (so never My vault, whose photos are the shoots' own)."""
    try:
        listed = {k["folder"] for k in home_base.kits() if not k["archived"]}
    except (Exception, SystemExit):  # noqa: BLE001
        listed = set()
    kits = [k for k in (got or {}).get("kits", []) if k.get("favs") and k.get("folder") in listed]
    kits.sort(key=lambda k: (k.get("date") or "", k.get("folder") or ""), reverse=True)
    return [(k["folder"], list(k["favs"])) for k in kits]


def _turns(lists, most):
    """One from each list in turn, then the second of each, and so on, up to most."""
    out, r = [], 0
    while len(out) < most and any(r < len(x) for x in lists):
        for x in lists:
            if r < len(x) and len(out) < most:
                out.append(x[r])
        r += 1
    return out


def hello_photos(pics, shoots, first=None):
    """[{kit, n, v}] for the hello, wide favorites first (the hello's own shoot first)."""
    order = sorted(shoots, key=lambda s: s[0] != first)
    wide, other = [], []
    for folder, favs in order:
        w, o = [], []
        for n in favs:
            p = pics.one(folder, n)
            if p:
                (w if p.get("way") == "wide" else o).append({"kit": folder, "n": p["n"], "v": p["v"]})
        wide.append(w)
        other.append(o)
    out = _turns(wide, HELLO_MOST)
    if len(out) < HELLO_FEW:
        out += _turns(other, HELLO_MOST - len(out))
    return out


def tile_photos(pics, shoots, skip=()):
    """Four tiles, each {kit, cands: [{n, v}]}: a different shoot each while there are shoots enough; with fewer,
    the shoots take turns and each turn uses photos of that shoot no tile has used yet. No photo the hello opens on
    (skip: [(kit, n)]). No shoots: no tiles (grey placeholders)."""
    if not shoots:
        return []
    used = set(skip)
    out = []
    for i, _make in enumerate(TILES):
        folder, favs = shoots[i % len(shoots)]
        ps = [p for p in (pics.one(folder, n) for n in favs) if p]
        fresh = [p for p in ps if (folder, p["n"]) not in used]
        cands = [{"n": p["n"], "v": p["v"]} for p in (fresh or ps)][:TILE_CANDS]
        if len(shoots) < len(TILES):          # a shoot with more tiles to fill: this tile keeps only its share
            share = max(1, len(cands) // -(-(len(TILES) - i) // len(shoots)))
            cands = cands[:share]
        used.update((folder, c["n"]) for c in cands)
        out.append({"kit": folder, "cands": cands} if cands else {})
    return out


def grid_now():
    """The last three posts of their grid, newest first, as the posting page draws its grid: the posts lined up
    (the last in line sits first), the ones marked posted, then the posts read from their Instagram (pinned ones
    left out: they are old ones kept at the top). Addresses of this server's own pictures only."""
    import posting_queue
    p = posting_queue.load()
    pieces = [x for x in p.get("pieces") or [] if isinstance(x, dict)]
    greens = sorted((x for x in pieces if x.get("status") == "green"), key=lambda x: (x.get("date") or "9999", x.get("slot") or 0))
    posted = sorted((x for x in pieces if x.get("status") == "posted" and isinstance(x.get("posted_at"), str)), key=lambda x: x["posted_at"], reverse=True)
    out = []
    for x in list(reversed(greens)) + posted:
        u = _thumb_src(x.get("thumb"))
        if u and u not in out:
            out.append(u)
    try:
        for x in posting_queue.load_feed().get("posts") or []:
            if isinstance(x, dict) and not x.get("pinned"):
                u = _thumb_src(x.get("thumb"))
                if u and u not in out:
                    out.append(u)
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    return out[:3]


def facts(force_year=False, start=False):
    """Everything the home page shows, read from what the Assistant already keeps. Each part fails soft: one
    record that can't be read never takes the page with it. Names and numbers only, never a path."""
    day = _today()
    iso = day.isoformat()
    f = {"today": day.strftime("%A, %B ") + str(day.day), "me": "", "card": None, "backup": None, "queue": [], "kits": 0,
         "newest": None, "posting": {"today": [], "late": [], "posted_week": [], "ready": 0, "per_week": None},
         "year": None, "recap": None, "recap_hidden": False, "year_bar": None,
         "hello": None, "hello_photos": [], "tiles": [], "grid": []}
    pics = _Photos()
    try:
        f["card"] = card_in()
    except Exception:  # noqa: BLE001
        pass
    # 1. the last backup, and how it stands (from its own records, when they can be found)
    try:
        import edit_queue
        q = edit_queue.load()
        backed = [s for s in q["shoots"] if isinstance(s, dict) and s.get("studio")]
        if backed:
            last = max(backed, key=lambda s: s.get("added") or "")
            same = [s for s in backed if same_place(s.get("studio"), last["studio"])]
            b = {"when": (last.get("added") or "")[:10], "photos": sum(s.get("count") or 0 for s in same if isinstance(s.get("count"), int)),
                 "clips": sum(s.get("clips") or 0 for s in same if isinstance(s.get("clips"), int)), "state": "unknown"}
            try:
                rec = home_base.records_of(last["studio"])
                st = home_base.backup_status(rec) if rec else {"known": False}
                if st.get("known"):
                    b["state"] = "sample" if st.get("sample") else "safe" if st.get("safe") is True else "look"
            except Exception:  # noqa: BLE001
                pass
            f["backup"] = b
        # 2. the editing queue, in its own order (soonest due first)
        for s in edit_queue.waiting(q):
            due = s.get("due") if isinstance(s.get("due"), str) else None
            try:
                due_in = (date.fromisoformat(due) - day).days if due else None
            except ValueError:
                due, due_in = None, None
            f["queue"].append({"name": str(s.get("name") or ""), "due": due, "due_in": due_in})
    except (Exception, SystemExit):     # an unreadable queue.json ends edit_queue.load with SystemExit: the page still comes
        pass
    # 3 and the hello: the kits, the year's numbers, the recap (one read of the records for all of them)
    got = None
    try:
        import wrapped
        got = wrapped.gather()
        f["me"] = got.get("me") or ""
    except (Exception, SystemExit):  # noqa: BLE001
        got = None
    try:
        kits = [k for k in home_base.kits() if not k["archived"]]
        f["kits"] = len(kits)
        if kits:
            k = kits[0]
            favs = next((x["favs"] for x in (got or {}).get("kits", []) if x["folder"] == k["folder"]), [])
            f["newest"] = {"short": look.short_name(k["folder"]) or k["folder"], "photo": pics.one(k["folder"], favs[0]) if favs else None}
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    if got:
        try:
            import wrapped
            # the hello's lines about this year
            y = wrapped.data(year=str(day.year), got=got, day=day)
            last = max(y["shoots"], key=lambda s: s.get("date") or "", default=None)
            top = next((s for s in y["shoots"] if s["name"] == y["top"]), None) if y["top"] else None
            f["year"] = {"y": str(day.year), "reels": y["totals"]["reels"], "photos": y["totals"]["photos"],
                         "newest": last["short"] if last else "", "top": top["short"] if top else ""}
            # the monthly recap card and the Your year bar: whether each shows is wrapped.py's to say
            ans = wrapped.home_answers(day=day, force_year=force_year, got=got)
            if ans.get("recap"):
                r = ans["recap"]
                f["recap"] = {"month": r["month"], "label": r["label"], "word": r["word"], "chips": list(r["chips"]), "url": r["url"],
                              "photos": [p for p in (pics.one(x["kit"], x["n"]) for x in r["photos"]) if p][:3]}
                f["recap_hidden"] = recap_hidden(r["month"])
            if ans.get("year"):
                yd = wrapped.data(year=ans["year"]["year"], got=got, day=day)
                fan = []
                for s in yd["shoots"]:
                    fan += [p for p in (pics.one(s["name"], n) for n in s["favs"][:2]) if p]
                    if len(fan) >= 3:
                        break
                if yd["shoots"]:                 # hers: the bar needs shoots to show
                    f["year_bar"] = {"year": ans["year"]["year"], "url": ans["year"]["url"], "photos": fan[:3]}
        except (Exception, SystemExit):  # noqa: BLE001
            pass
    # 4. the posting queue: today's post, one that missed its day, what went out this week, how many are ready
    try:
        import posting_queue
        p = posting_queue.load()
        pieces = [x for x in p.get("pieces") or [] if isinstance(x, dict)]
        greens = sorted((x for x in pieces if x.get("status") == "green"), key=lambda x: (x.get("date") or "9999", x.get("slot") or 0))

        def pub(x):
            kind = x.get("kind") if x.get("kind") in posting_queue.KINDS else "post"
            return {"who": who(x.get("shoot_name")), "kind": W("n4_single") if kind == "single" else kind, "thumb": _thumb_src(x.get("thumb")),
                    "date": x.get("date") if isinstance(x.get("date"), str) else ""}
        week = (day - timedelta(days=7)).isoformat()
        f["posting"]["today"] = [pub(x) for x in greens if x.get("date") == iso]
        late = []
        for x in greens:
            d = x.get("date")
            if isinstance(d, str) and d < iso:
                try:
                    late.append(dict(pub(x), days=(day - date.fromisoformat(d[:10])).days))
                except ValueError:
                    pass
        f["posting"]["late"] = late
        posted = [x for x in pieces if x.get("status") == "posted" and isinstance(x.get("posted_at"), str) and x["posted_at"][:10] >= week]
        f["posting"]["posted_week"] = [pub(x) for x in sorted(posted, key=lambda x: x["posted_at"], reverse=True)]
        f["posting"]["ready"] = len(greens)
        per = p.get("interval")
        f["posting"]["per_week"] = per if isinstance(per, (int, float)) and not isinstance(per, bool) and per > 0 else None
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    # 5. the hello (her section 3: it only lifts them up): her approved lines, kept for a visit (hello_lines.py)
    try:
        import hello_lines
        f["hello"] = hello_lines.pick()
    except (Exception, SystemExit):  # noqa: BLE001  (no hello is still a page: it says "Hello.")
        f["hello"] = None
    # 6. the photos: the hello's one wide photo (and the next ones), and the four tiles
    try:
        shoots = _shoots(got)
        first = (f.get("hello") or {}).get("kit")
        f["hello_photos"] = hello_photos(pics, shoots, first)
        f["tiles"] = tile_photos(pics, shoots, skip=[(p["kit"], p["n"]) for p in f["hello_photos"][:1]])
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    # 6b. a brand-new Assistant (Nicole's v30, section 6): no post kit yet, so the hello and the tiles show the
    # sample photos the plugin carries (samples.py), until the first post kit exists. Names only; they count in nothing.
    f["samples"] = None
    if not f["hello_photos"] and not any(f["tiles"]):
        try:
            import samples
            f["samples"] = samples.for_home()
        except (Exception, SystemExit):  # noqa: BLE001
            f["samples"] = None
    # 7. the last three posts of their grid, newest first, as the posting page's grid shows them
    try:
        f["grid"] = grid_now()
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    if start:
        pics.start()
    return f


# ---------- the page's look: Nicole's v30 (her pages/home-new-look.html, screenshot 01), the HOME PAGE only ----------
#
# Her approved look (UPDATE-v30 section 1): one typeface, Helvetica (Neue Bold for headings, regular for the rest,
# letter spacing -1%), warm paper, black words, ONE accent (#D9603A, for "THE ASSISTANT" and the accent words), square
# corners, a thin black line under the top bar, few boxes, calm sizes; the photos bring the colour. Helvetica is the
# computer's own (a Mac has it; a PC gets Arial): nothing is downloaded. Every other page keeps look.py's look until
# Dustin and Nicole say; the colours and the type live in this one block so they can move into look.py in one step.
HOME_LOOK = r"""
:root{--accent:#D9603A;--cream:#EDEAE4;--paper:#F5F3EF;--tan:#DED8CD;--ink:#111;--ink-2:#6E6A64;--line:rgba(17,17,17,.14);
--placeholder:#D3CDC4;--late:#B3402A;--name-on-photo:#FFB08F;
--coral:#D9603A;--coral-2:#D9603A;--coral-l:#E2DED6;--sand-l:#E2DED6;
--sans:"Helvetica Neue",Helvetica,Arial,sans-serif;--ease:cubic-bezier(.2,.7,.2,1);--corner:2px}
"""
# (--name-on-photo is hers too: the accent lightened, so the name still reads on a dark photo.)

# Her layout, rule for rule where hers has one (home-new-look.html's own styles), on our markup. Every animation is
# under prefers-reduced-motion: no-preference, so with reduced motion nothing moves and the photo never changes.
CSS_EXTRA = home_base.CSS + HOME_LOOK + r"""
html,body{background:var(--cream)}
body{color:var(--ink);font:400 15px/1.5 var(--sans);letter-spacing:-.01em}
.wrap{max-width:1180px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 1rem}
.bar{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto auto;align-items:center;gap:1.4rem;min-height:52px;border-bottom:1px solid var(--ink)}
.brand{white-space:nowrap;min-width:0}
.brand b{font:700 13px/1 var(--sans);letter-spacing:-.01em;text-transform:uppercase;color:var(--accent)}
.brand small{display:inline;margin:0 0 0 .8em;font:400 12px/1 var(--sans);letter-spacing:-.01em;text-transform:none;color:var(--ink-2)}
.bar .when{margin:0;font:400 12px/1 var(--sans);color:var(--ink-2);text-align:right}
.bar .fold{display:inline-flex;align-items:baseline;gap:.8em;flex-direction:row-reverse}
.bar .lnk{font:400 12px/1 var(--sans);letter-spacing:-.01em;color:var(--ink);background:none;border:0;padding:4px 0;cursor:pointer;text-decoration:underline;text-underline-offset:3px;white-space:nowrap}
.bar .fold .note{display:inline;margin:0;font-size:12px;line-height:1.3;color:var(--ink-2);max-width:min(320px,36vw);text-align:right;min-height:0}
.bar .fold .note:empty{display:none}
@media(max-width:560px){.bar{grid-template-columns:minmax(0,1fr) auto}.bar .when{display:none}
 .bar .fold .note{position:absolute;right:0;top:100%;max-width:80vw;background:var(--cream);padding:2px 0;z-index:4}}
.offline{margin:.6rem 0 0;color:var(--late);font-size:13px}
.hello{position:relative;margin-top:10px;height:clamp(200px,24vh,290px);overflow:hidden;color:#fff;display:flex;align-items:flex-end;padding:clamp(1rem,3vw,2rem) clamp(1.1rem,3.4vw,2.4rem);background:var(--placeholder)}
.hello.photo{background:#222}
.hello .bgs{position:absolute;inset:0;overflow:hidden}
.hello .bgs img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0}
.hello .bgs img.on{opacity:1}
.hello .bgs img:not([src]){display:none}
.hello::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.6),rgba(0,0,0,.1) 70%);pointer-events:none}
.hello .tx{position:relative;z-index:1;max-width:46em;min-width:0}
.hello .samplenote{position:absolute;top:10px;right:12px;z-index:1;margin:0;font-size:11px;line-height:1.3;color:#fff;background:rgba(0,0,0,.45);padding:4px 8px;max-width:calc(100% - 24px)}
.hello .samplenote[hidden]{display:none}
.hello h2{margin:0;font:700 clamp(26px,3vw,40px)/1.04 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.hello em{font:inherit;font-style:normal;color:var(--name-on-photo)}
.hello p{margin:.4rem 0 0;font-size:15px;color:#fff;overflow-wrap:anywhere}
.hello p em{font-weight:400}
h1.big{margin:18px 0 0;font:700 clamp(26px,2.6vw,38px)/1.05 var(--sans);letter-spacing:-.01em}
h1.big em{font:inherit;font-style:normal;color:var(--accent)}
.sub{margin:.3rem 0 0;font-size:15px;color:var(--ink-2);max-width:40em}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px}
@media(max-width:760px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tl{position:relative;display:block;height:clamp(130px,16vh,210px);overflow:hidden;background:var(--placeholder);color:#fff;text-decoration:none}
.tl img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.tl img:not([src]){display:none}
.tl::after{content:'';position:absolute;inset:0;background:rgba(0,0,0,.14)}
.tl b{position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);z-index:1;text-align:center;font:700 clamp(18px,1.8vw,24px)/1 "Helvetica Neue",Helvetica,Arial,sans-serif;letter-spacing:-.01em}
.tl:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.go-row{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-top:12px}
.btn{display:inline-flex;align-items:center;gap:.4rem;font:700 13px/1 var(--sans);letter-spacing:-.01em;padding:13px 18px;border:1px solid var(--ink);border-radius:0;background:var(--ink);color:#fff;text-decoration:none;cursor:pointer}
.btn:hover,.btn.solid:hover{background:transparent;color:var(--ink);border-color:var(--ink)}
.low{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin-top:14px}
@media(max-width:820px){.low{grid-template-columns:minmax(0,1fr)}}
.pq{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,.9fr);gap:18px;align-items:center;padding:16px 18px;background:var(--paper);text-decoration:none;color:inherit;border-radius:var(--corner);min-width:0}
.pq.nogrid{grid-template-columns:minmax(0,1fr)}
@media(max-width:760px){.pq{grid-template-columns:minmax(0,1fr)}}
.pq>div{min-width:0}
.pq .n{display:block;margin:0;font:700 22px/1 var(--sans);letter-spacing:-.01em;text-transform:uppercase}
.row .n{display:block;font:700 18px/1 var(--sans);letter-spacing:-.01em;text-transform:uppercase}
.pq .n em,.row .n em{font:inherit;font-style:normal;color:inherit}
.pq p{margin:.35rem 0 .7rem;font-size:13px;color:var(--ink-2)}
.pq .lnk2{display:inline-block;margin-top:.7rem;font:700 13px/1 var(--sans);border-bottom:1px solid var(--ink);padding-bottom:3px}
.stack{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3px;min-width:0}
.stack img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;background:var(--placeholder)}
.stack small{grid-column:1/-1;margin-top:6px;font-size:11px;color:var(--ink-2)}
.also{display:grid;gap:12px;align-content:stretch;min-width:0}
.row{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr) auto;gap:1rem;align-items:center;padding:14px 18px;border:0;border-radius:var(--corner);text-decoration:none;color:inherit;background:var(--paper);font:inherit;text-align:left;width:100%;cursor:pointer;min-width:0}
.row>div{min-width:0}
.row p{margin:.35rem 0 0;font-size:13px;color:var(--ink-2)}
.row .ar{font-size:18px}
.row .note{grid-column:1/-1;margin:0;font-size:12px}
.row .note:empty{display:none}
@media(max-width:1000px){.row{grid-template-columns:minmax(0,1fr) auto}.row .now{grid-column:1/-1;grid-row:2}}
.now{display:flex;align-items:center;gap:10px;font-size:13px;min-width:0}
.now img{width:34px;height:44px;object-fit:cover;flex:none}
.now span{color:var(--ink);min-width:0;overflow-wrap:anywhere;line-height:1.35}
.now small{display:block;color:var(--ink-2);font-size:12px}
.now small.late{color:var(--late)}
.now .dot{width:7px;height:7px;border-radius:50%;flex:none;background:var(--ink-2)}
.now .dot.red,.now .dot.coral{background:var(--late)}
.rc,.yr{margin-top:12px;position:relative;display:flex;align-items:center;gap:1rem;padding:12px 18px;background:var(--tan);color:var(--ink);border-radius:var(--corner);min-width:0}
.rc[hidden],.yr[hidden]{display:none}
.rc .fan,.yr .fan{display:flex;gap:4px;flex:none}
.rc .fan img,.yr .fan img{width:40px;height:52px;object-fit:cover;display:block}
.rc>div,.yr>div{min-width:0}
.rc b,.yr b{font:700 17px/1.1 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.rc b em,.yr b em{font:inherit;font-style:normal;color:inherit}
.rc .chips{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px;font-size:12px;color:var(--ink-2)}
.rc .chips span i{font-style:normal;font-weight:700;color:var(--ink)}
.yr small{display:block;font-size:12px;color:var(--ink-2);margin-top:2px}
.rc .playbtn,.yr .playbtn{margin-left:auto;font:700 13px/1 var(--sans);border-bottom:1px solid var(--ink);padding-bottom:3px;white-space:nowrap}
.yr .all,.rc .all{position:absolute;inset:0;z-index:1}
.rc .x{position:relative;z-index:2;border:0;background:none;font:400 18px/1 var(--sans);cursor:pointer;color:var(--ink-2);padding:4px 6px}
.rc .x:hover,.rc .x:focus-visible{color:var(--ink)}
.rcmenu{position:absolute;right:8px;top:calc(100% - 6px);z-index:3;background:#fff;padding:6px;display:grid;min-width:210px;box-shadow:0 10px 30px rgba(0,0,0,.12)}
.rcmenu[hidden]{display:none}
.rcmenu button{border:0;background:none;text-align:left;font:400 13px/1.2 var(--sans);padding:10px 12px;cursor:pointer;color:var(--ink)}
.rcmenu button:hover,.rcmenu button:focus-visible{background:var(--cream)}
.rc .rcnote{position:absolute;left:18px;bottom:1px;margin:0;font-size:12px;color:var(--late);z-index:2}
@media(max-width:560px){.rc,.yr{flex-wrap:wrap}.rc .fan,.yr .fan{display:none}.rc{padding-right:44px}.rc .x{position:absolute;right:8px;top:8px}}
.foot{margin:.6rem 0 0;font-size:12px;color:var(--ink-2)}
.foot button{border:0;background:none;padding:0;font:inherit;color:var(--ink-2);text-decoration:underline;cursor:pointer}
/* "Create a reel: which shoot?" (her section 4): her dialog's styles, on our markup */
.mk{position:fixed;inset:0;z-index:20;background:rgba(17,17,17,.45);display:grid;place-items:center;padding:16px}
.mk[hidden]{display:none}
.mkbox{width:min(760px,100%);max-height:86vh;overflow:auto;background:var(--paper);padding:clamp(18px,3vw,28px);outline:0}
.mkh{display:flex;align-items:baseline;justify-content:space-between;gap:1rem}
.mkh h3{margin:0;font:700 26px/1.05 var(--sans);letter-spacing:-.01em}
.mkh h3 em{font-style:normal;color:var(--accent)}
.mkh button{border:0;background:none;font-size:22px;line-height:1;cursor:pointer;color:var(--ink-2);padding:4px 6px}
.mkh button:hover,.mkh button:focus-visible{color:var(--ink)}
.mkbox>p{margin:.3rem 0 1rem;color:var(--ink-2);font-size:14px}
.mkfind{box-sizing:border-box;width:100%;font:400 15px/1 var(--sans);letter-spacing:-.01em;padding:12px 14px;border:1px solid var(--line);border-radius:0;background:#fff;color:var(--ink);margin-bottom:10px}
.mkfind[hidden]{display:none}
.mklist{display:grid;gap:6px}
#mkL{max-height:52vh;overflow:auto}
.mkr{box-sizing:border-box;display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:14px;align-items:center;padding:8px;background:#fff;text-decoration:none;color:var(--ink);border:1px solid transparent;border-radius:0;cursor:pointer;font:inherit;text-align:left;width:100%}
.mkr:hover,.mkr:focus-visible{border-color:var(--ink);outline:0}
.mkr:disabled{cursor:default;opacity:.6}.mkr:disabled:hover{border-color:transparent}
.mkr .im{width:52px;height:52px;overflow:hidden;background:#d9d4cc;display:grid;place-items:center}
.mkr .im img{width:100%;height:100%;object-fit:cover;display:block}
.mkr>span{min-width:0}
.mkr b{display:block;font:700 15px/1.2 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}
.mkr small{display:block;font-size:12.5px;color:var(--ink-2);margin-top:2px}
.mkr .ar{font-size:16px;color:var(--ink-2)}
.mkr.new .im{background:var(--ink);color:#fff;font:400 26px/1 var(--sans)}
.mkr.v .im{grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:1px;background:var(--ink)}
.mklab{margin:10px 0 6px;font:700 11px/1 var(--sans);text-transform:uppercase;letter-spacing:.02em;color:var(--ink-2)}
.mklab[hidden]{display:none}
.mknote{margin:6px 0 0;background:#fff;padding:12px 14px;font-size:13.5px;color:var(--ink);border-left:3px solid var(--accent)}
.mknote[hidden]{display:none}
.mknothing{margin:0;background:#fff;padding:12px 14px;font-size:13.5px;color:var(--ink-2)}
@media (prefers-reduced-motion: no-preference){
.hello .bgs img{transition:opacity 1.6s ease}
.row .ar{transition:transform .3s var(--ease)}.row:hover .ar{transform:translateX(4px)}
}
"""

# The photos (Nicole's v30 sections 2 and 4): the hello is ONE wide photo, cropped in toward the faces' middle (1.22x)
# from the 1600 px copies (never the photos themselves), horizontal favorites first, a new one every few seconds; the
# four tiles each a photo from a different shoot with a face, faces centered. The hello's words are drawn by the
# server, as text (they are not this script's). A computer with no face finder (a PC): every photo centered.
HELLO_JS = r"""
const F = JSON.parse($('facts').textContent);
const STILL = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
const ZOOM = 1.22, EVERY = 6000;
const clamp01 = v => Math.max(0, Math.min(1, v));
function window1(fs, vis){
  let best = null;
  fs.forEach(a => { const lo = clamp01(Math.min(1 - vis, a.c - vis / 2)), hi = lo + vis;
    const inn = fs.filter(f => f.a >= lo - .005 && f.b <= hi + .005), score = inn.reduce((t, f) => t + f.size, 0);
    if (!best || score > best.score) best = {score, inn}; });
  if (!best || !best.inn.length) return fs.reduce((t, f) => t + f.c, 0) / fs.length;      // no stretch holds a whole face: the middle of them
  return (Math.min(...best.inn.map(f => f.a)) + Math.max(...best.inn.map(f => f.b))) / 2;
}
// the faces' middle, cropped in: object-position puts them in the frame, the 1.22x zoom grows from their middle
function aim(img, x, bw, bh){
  const f = x.f || {}, w = f.w || x.nw || 1000, h = f.h || x.nh || 1500, sc = Math.max(bw / w, bh / h), dw = w * sc, dh = h * sc, fc = f.faces || [];
  let cx = .5, cy = .5, px = .5, py = .5;        // no faces known (a PC, or none in the photo): the photo is centered
  if (fc.length) {
    cx = window1(fc.map(a => ({a: a[0], b: a[0] + a[2], c: a[0] + a[2] / 2, size: a[2] * a[3]})), bw / dw);
    cy = window1(fc.map(a => ({a: a[1] - a[3] * .4, b: a[1] + a[3] * 1.1, c: a[1] + a[3] / 2, size: a[2] * a[3]})), bh / dh);
    px = dw > bw + 1 ? clamp01((cx * dw - bw / 2) / (dw - bw)) : .5; py = dh > bh + 1 ? clamp01((cy * dh - .5 * bh) / (dh - bh)) : .5;
  }
  img.style.objectPosition = `${(px * 100).toFixed(1)}% ${(py * 100).toFixed(1)}%`;
  img.style.transformOrigin = `${(cx * dw - px * (dw - bw)).toFixed(0)}px ${(cy * dh - py * (dh - bh)).toFixed(0)}px`;
  img.style.transform = `scale(${ZOOM})`;
  img.dataset.faces = String(fc.length);
}
const photoUrl = (kit, p) => '/kit-photo?kit=' + encodeURIComponent(kit) + '&n=' + p.n + '&size=l&v=' + encodeURIComponent(p.v || '');
// a brand-new Assistant's sample photos (samples.py): by file name only, from the plugin's own samples folder
const SAMPLES = F.samples || null;
const sampleUrl = name => '/home-sample?name=' + encodeURIComponent(name);
let SFACES = null;
const sampleFaces = () => SFACES || (SFACES = live
  ? fetch('/home-sample-faces', {cache: 'no-store'}).then(r => r.json()).then(d => (d && d.faces) || {}).catch(() => ({}))
  : Promise.resolve({}));
const sampleShown = () => { const s = document.getElementById('sampleNote'); if (s) s.hidden = false; };
// the faces of a kit's photos, one ask per kit (faces.py looks at the 520 px copies; the boxes are fractions, so they
// hold for the 1600 px copy too); remembered for this page
const FACES = {};
function facesOf(kit, ns){
  const k = kit + '|' + ns.join(',');
  if (!FACES[k]) FACES[k] = live && ns.length
    ? fetch('/kit-faces?kit=' + encodeURIComponent(kit) + '&n=' + ns.slice(0, 24).join(','), {cache: 'no-store'}).then(r => r.json()).then(d => (d && d.faces) || {}).catch(() => ({}))
    : Promise.resolve({});
  return FACES[k];
}
const soon = (p, ms) => Promise.race([p, new Promise(r => setTimeout(() => r(null), ms))]);
function put(im, x, box){
  return new Promise(res => {
    const done = ok => { im.onload = im.onerror = null; res(ok); };
    im.onload = () => { x.nw = im.naturalWidth; x.nh = im.naturalHeight; aim(im, x, box.clientWidth, box.clientHeight); done(true); };
    im.onerror = () => done(false);
    im.dataset.n = x.n; im.dataset.kit = x.kit; im.src = x.u;
  });
}

/* the hello: one photo, a new one every few seconds (reduced motion: the first one stays) */
async function startHello(box){
  const P = SAMPLES ? (SAMPLES.hello || []).map(nm => ({kit: '', n: nm, u: sampleUrl(nm), f: {}}))
    : (F.hello_photos || []).map(p => ({kit: p.kit, n: p.n, u: photoUrl(p.kit, p), f: {}}));
  box.dataset.photos = String(P.length);
  if (!P.length || !live) return;
  const bg = box.querySelector('.bgs'), A = bg.children[0], B = bg.children[1];
  const kits = [...new Set(P.map(x => x.kit))];
  const asks = SAMPLES ? [sampleFaces().then(G => { P.forEach(x => { if (G[x.n]) x.f = G[x.n]; }); })]
    : kits.map(k => facesOf(k, P.filter(x => x.kit === k).map(x => x.n)).then(G => { P.filter(x => x.kit === k).forEach(x => { if (G[x.n]) x.f = G[x.n]; }); }));
  await soon(Promise.all(asks), 900);                       // a brand-new shoot's faces may take a moment: start anyway
  let i = 0, ok = false;
  for (; i < P.length && !ok; i++) ok = await put(A, P[i], box);
  if (!ok) { A.removeAttribute('src'); return; }
  A.classList.add('on'); box.classList.add('photo'); box.dataset.shown = String(i - 1);
  if (SAMPLES) sampleShown();
  Promise.all(asks).then(() => { const on = bg.querySelector('img.on'); const x = P.find(y => String(y.n) === on.dataset.n && y.kit === on.dataset.kit); if (x) aim(on, x, box.clientWidth, box.clientHeight); });
  let rsz = 0; addEventListener('resize', () => { clearTimeout(rsz); rsz = setTimeout(() => bg.querySelectorAll('img[src]').forEach(im => { const x = P.find(y => String(y.n) === im.dataset.n && y.kit === im.dataset.kit); if (x) aim(im, x, box.clientWidth, box.clientHeight); }), 250); });
  if (P.length < 2 || STILL) return;                        // reduced motion: the photo never changes
  let next = i % P.length, busy = false;
  setInterval(async () => {
    if (busy || document.hidden) return; busy = true;
    const on = bg.querySelector('img.on'), off = on === A ? B : A;
    for (let tries = 0; tries < P.length; tries++) {
      const k = next; next = (next + 1) % P.length;
      if (await put(off, P[k], box)) { off.classList.add('on'); on.classList.remove('on'); box.dataset.shown = String(k); break; }
    }
    busy = false;
  }, EVERY);
}

/* the four tiles: a photo from a different shoot each, the first one with a face, faces centered */
async function startTiles(){
  const T = SAMPLES ? (SAMPLES.tiles || []).map(ns => ({kit: '', sample: true, cands: (ns || []).map(nm => ({n: nm}))})) : (F.tiles || []);
  const facesFor = t => t.sample ? sampleFaces() : facesOf(t.kit, t.cands.map(c => c.n));
  const urlFor = (t, c) => t.sample ? sampleUrl(c.n) : photoUrl(t.kit, c);
  document.querySelectorAll('#tiles .tl').forEach(async (el, i) => {
    const t = T[i]; if (!t || !t.cands || !t.cands.length || !live) return;
    const im = el.querySelector('img');
    const G = await soon(facesFor(t), 2500) || {};
    const withFace = t.cands.filter(c => G[c.n] && G[c.n].faces && G[c.n].faces.length);
    const order = withFace.concat(t.cands.filter(c => !withFace.includes(c)));
    for (const c of order) { if (await put(im, {kit: t.kit, n: c.n, u: urlFor(t, c), f: G[c.n] || {}}, el)) { if (t.sample) sampleShown(); return; } }
    im.removeAttribute('src');
  });
  let rsz = 0; addEventListener('resize', () => { clearTimeout(rsz); rsz = setTimeout(() => document.querySelectorAll('#tiles .tl img[src]').forEach(im => {
    const el = im.closest('.tl'), t = T[[...el.parentNode.children].indexOf(el)]; if (!t) return;
    facesFor(t).then(G => aim(im, {f: G[im.dataset.n] || {}, nw: im.naturalWidth, nh: im.naturalHeight}, el.clientWidth, el.clientHeight)); }), 250); });
}
"""

SCRIPT = r"""
// every card records what was pressed, so the chat knows (journey.json); then it goes where it goes
document.querySelectorAll('[data-item]').forEach(b => b.addEventListener('click', () => clicked(b.dataset.item)));
$('s2').onclick = () => assistant('/queue-url', $('editingWords'), W.opening_queue);
$('folder').onclick = () => assistant('/open-home', $('folder'), W.opening);
if (!live) $('offline').hidden = false;
startHello($('hello'));
startTiles();
// a picture that can't be shown (its small copy is still being made) leaves no broken frame
document.querySelectorAll('.now img, .fan img, .stack img').forEach(im => { const gone = () => { im.remove(); }; if (im.complete && !im.naturalWidth) gone(); else im.addEventListener('error', gone); });
// the monthly recap: the x opens two choices; the choice is saved with their records first, then the card goes.
// "Show my monthly recap" in the footer brings it back.
(function(){
  const rc = $('rc'); if (!rc) return;
  const menu = $('rcM'), x = $('rcX'), back = $('rcBack'), noteEl = $('rcNote');
  const open = on => { menu.hidden = !on; x.setAttribute('aria-expanded', on ? 'true' : 'false'); };
  async function save(hide){
    noteEl.textContent = '';
    if (!live) { noteEl.textContent = W.not_running; return false; }
    try { const r = await fetch('/home-recap', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hide: hide, month: rc.dataset.m})});
      const d = await r.json(); if (d && d.ok) return true; } catch (e) {}
    return false;
  }
  x.onclick = e => { e.preventDefault(); e.stopPropagation(); open(menu.hidden); if (!menu.hidden) menu.querySelector('button').focus(); };
  menu.onclick = async e => { e.preventDefault(); e.stopPropagation(); const b = e.target.closest('button'); if (!b) return;
    open(false);
    if (await save(b.dataset.h)) { rc.hidden = true; back.hidden = false; } else if (!noteEl.textContent) noteEl.textContent = W.rc_didnt; };
  $('rcShow').onclick = async () => { if (await save('show')) { rc.hidden = false; back.hidden = true; } else note($('rcShow'), W.rc_didnt); };
  document.addEventListener('click', e => { if (!e.target.closest('#rcM') && !e.target.closest('#rcX')) open(false); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !menu.hidden) { open(false); x.focus(); } });
})();
// The four tiles are shortcuts (Nicole's v30, section 4): a press asks which shoot, then goes straight to that shoot's
// page (the reel page, the carousel designer, the stories designer, the words page). "+ A new shoot" picks a folder,
// the Assistant makes its post kit, and the page lands where the tile was going. Every word is drawn as text.
const MK = (function(){
  const box = $('mk'); if (!box) return null;
  const TITLE = {reel: 'mk_reel', carousel: 'mk_carousel', stories: 'mk_stories', captions: 'mk_captions'};
  let make = 'reel', from = null, list = null, following = false, asked = 0;
  window.MK_HOLD = false;
  const accent = (el, s) => { el.textContent = ''; const m = /^(.*)<em>(.*)<\/em>(.*)$/.exec(s);
    if (!m) { el.textContent = s; return; } const e = document.createElement('em'); e.textContent = m[2]; el.append(m[1], e, m[3]); };
  const el = (tag, cls, text) => { const x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; };
  function row(tag, cls, imgs, title, small){
    const r = el(tag, 'mkr' + (cls ? ' ' + cls : '')); if (tag === 'button') r.type = 'button';
    const im = el('span', 'im'); im.setAttribute('aria-hidden', 'true');
    if (typeof imgs === 'string') im.textContent = imgs;
    else imgs.forEach(src => { const i = el('img'); i.alt = ''; i.loading = 'lazy'; i.addEventListener('error', () => { i.remove(); }); i.setAttribute('src', src); im.append(i); });
    const t = el('span'); t.append(el('b', '', title), el('small', '', small));
    const ar = el('span', 'ar', '→'); ar.setAttribute('aria-hidden', 'true');
    r.append(im, t, ar); return r;
  }
  const say = t => { const n = $('mkNote'); n.textContent = t || ''; n.hidden = !t; };
  const photos = n => fill(n === 1 ? W.mk_photo : W.mk_photos, {n: many(n || 0)});
  function draw(){
    const L = $('mkL'), kits = (list && list.kits) || [], q = ($('mkF').value || '').trim().toLowerCase();
    $('mkS').textContent = (list && !kits.length) ? W.mk_sub_none : W.mk_sub;
    $('mkLab').hidden = !kits.length; $('mkF').hidden = kits.length < 7;
    L.textContent = '';
    if (list && list.vault && kits.length && (!q || W.mk_vault.toLowerCase().includes(q))) {
      const v = row('button', 'v', list.vault.thumbs || [], W.mk_vault, W.mk_vault_small); v.id = 'mkVault';
      v.onclick = () => toVault(v); L.append(v);
    }
    const hit = kits.filter(k => !q || String(k.name).toLowerCase().includes(q));
    hit.forEach(k => { const a = row('a', '', [k.thumb], k.name, [niceDay(k.date), photos(k.photos)].filter(Boolean).join(' · '));
      a.setAttribute('href', k.go[make]); a.dataset.kit = k.folder; L.append(a); });
    if (q && !L.children.length && kits.length) L.append(el('p', 'mknothing', fill(W.mk_nothing, {q: $('mkF').value.trim()})));
  }
  async function load(){
    const mine = ++asked;
    try { const r = await fetch('/make-list', {cache: 'no-store'}); const d = await r.json(); if (mine !== asked) return; if (!d || !d.ok) throw 0; list = d; }
    catch (e) { if (mine !== asked) return; list = {kits: [], vault: null}; say(W.mk_list_cant); }
    draw();
  }
  function open(kind, tile){
    make = TITLE[kind] ? kind : 'reel'; from = tile || null;
    accent($('mkT'), W[TITLE[make]]);
    $('mkF').value = ''; if (!following) say('');
    $('mkNew').disabled = following;
    draw(); box.hidden = false; window.MK_HOLD = true; box.querySelector('.mkbox').focus();
    load();
  }
  function close(){
    if (box.hidden) return;
    box.hidden = true; if (!following) window.MK_HOLD = false;
    if (from) try { from.focus(); } catch (e) {}
  }
  async function toVault(b){
    b.disabled = true;
    try { const r = await fetch('/make-vault', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({make})});
      const d = await r.json(); if (d && d.ok && d.url) { location.href = d.url; return; } say((d && d.words) || W.mk_didnt); }
    catch (e) { say(W.mk_didnt); }
    b.disabled = false;
  }
  function follow(){
    following = true; window.MK_HOLD = true; $('mkNew').disabled = true;
    const tick = async () => {
      let j = null; try { j = await (await fetch('/make-new-status', {cache: 'no-store'})).json(); } catch (e) {}
      if (j && j.state === 'done' && j.go) { following = false; say(j.words);
        if (!box.hidden) { location.href = j.go[make]; return; } window.MK_HOLD = false; $('mkNew').disabled = false; return; }
      if (j && (j.state === 'stopped' || j.state === 'none')) { following = false; $('mkNew').disabled = false; say(j.words || W.mk_didnt);
        if (box.hidden) window.MK_HOLD = false; return; }
      if (j && j.words) say(j.words);
      setTimeout(tick, 700);
    };
    setTimeout(tick, 300);
  }
  async function newShoot(){
    if (following) return;
    const b = $('mkNew'); b.disabled = true; say(W.mk_picking);
    let d = null;
    try { const r = await fetch('/make-new', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}); d = await r.json(); }
    catch (e) { d = {ok: false, words: W.not_running}; }
    if (d && d.state === 'working') { say(d.words); follow(); return; }
    b.disabled = false; say(d && d.cancelled ? '' : ((d && d.words) || W.mk_didnt));     // a closed window changes nothing
  }
  $('mkNew').onclick = newShoot;
  $('mkX').onclick = close;
  box.addEventListener('click', e => { if (e.target === box) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) { e.preventDefault(); close(); } });
  $('mkF').addEventListener('input', draw);
  document.querySelectorAll('#tiles .tl').forEach(t => t.addEventListener('click', e => {
    if (!live || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;     // a saved copy, or a new tab: the plain link
    e.preventDefault(); open(t.dataset.make, t); }));
  return {open, close};
})();
// Reload when anything changes (a card goes in, a backup lands, a queue moves).
const STAMP = document.body.dataset.stamp;
if (live) setInterval(async () => { if (window.MK_HOLD) return; try { const r = await fetch('/home-state', {cache: 'no-store'}); const t = (await r.text()).trim(); if (t && STAMP && t !== STAMP) location.reload(); } catch (e) {} }, 4000);
"""


def _in_address(t):
    """A kit folder's name (or a picture named after it) as part of a page address: the three characters that
    would cut the address short or change it ("#", "?" and "%") written the way addresses write them, and
    nothing else, so every other name is exactly as before. A kit named "Smith #2" lost its pictures and its
    Open the post kit button before Nov 6 (both computers): the address stopped at the "#"."""
    return str(t).replace("%", "%25").replace("#", "%23").replace("?", "%3F")


def nice_day(iso):
    """ "Nov 13, 2026", as the screens write a day."""
    try:
        d = date.fromisoformat(str(iso)[:10])
        return d.strftime("%b ") + str(d.day) + d.strftime(", %Y")
    except ValueError:
        return ""


def _now(dot, big, small=None, late=False, img=None):
    """One step's box: a dot or a small picture, a line, and a quieter line under it. Words are escaped here."""
    e = html.escape
    lead = f"<img src='{e(img, quote=True)}' alt=''>" if img else f"<i class='dot{(' ' + dot) if dot else ''}'></i>"
    cls = " class='late'" if late else ""
    sm = f"<small{cls}>{e(small)}</small>" if small else ""
    return f"{lead}<span>{e(big)}{sm}</span>"


def now_boxes(f):
    """What is going on right now, for each of the four cards (hers), in the order backup, editing queue, posts,
    posting queue (the ids n1 to n4, kept from v28 whatever order the page draws them in)."""
    boxes = []
    # 1. a card that is in; otherwise the last backup; otherwise nothing yet
    b = f.get("backup")
    if f.get("card"):
        boxes.append(_now("coral", W("n1_card"), W("n1_card_small").format(name=f["card"]["name"], files=f"{f['card']['files']:,}")))
    elif b:
        try:
            import clips
            count = clips.words(b["photos"], b.get("clips") or 0)
        except Exception:  # noqa: BLE001
            count = f"{b['photos']:,} photos"
        small, dot = {"safe": (W("n1_last_small").format(count=count), "green"), "sample": (W("n1_last_sample"), "yellow"),
                      "look": (W("n1_last_look"), "red")}.get(b["state"], (W("n1_last_plain").format(count=count), ""))
        boxes.append(_now(dot, W("n1_last").format(day=short_day(b["when"])).strip(), small, late=b["state"] == "look"))
    else:
        boxes.append(_now("", W("n1_none"), W("n1_none_small")))
    # 2. how many are waiting, and the next one due (red when late)
    q = f.get("queue") or []
    if q:
        d = next((x for x in q if x.get("due")), None)
        late = bool(d) and d["due_in"] is not None and d["due_in"] < 0
        small = W("n2_due").format(name=d["name"], day=short_day(d["due"])) if d else q[0]["name"]
        boxes.append(_now("red" if late else "yellow", W("n2_one") if len(q) == 1 else W("n2_many").format(n=len(q)), small, late=late))
    else:
        boxes.append(_now("green", W("n2_none"), W("n2_none_small")))
    # 3. (gone in v30: the "Newest: ..." box beside See all my post kits. Nicole: "no one cares about the newest.")
    boxes.append("")
    # 4. today's post with its picture, or one that missed its day; otherwise how many are ready
    P = f.get("posting") or {}
    t = (P.get("today") or [None])[0]
    la = (P.get("late") or [None])[0]
    ready = P.get("ready") or 0
    if t:
        small = W("n4_late_too").format(who=la["who"], kind=la["kind"]) if la else W("n4_ready").format(n=ready)
        boxes.append(_now("coral", W("n4_today").format(who=t["who"], kind=t["kind"]), small, late=bool(la), img=t.get("thumb")))
    elif la:
        boxes.append(_now("red", W("n4_waiting").format(who=la["who"], kind=la["kind"]), W("n4_was_down").format(day=short_day(la["date"])),
                          late=True, img=la.get("thumb")))
    elif ready:
        per = P.get("per_week")
        if per:
            days = max(1, round(ready * 7 / per))        # how long the ready posts last at their own rhythm (posts a week)
            small = W("n4_day") if days == 1 else W("n4_days").format(n=days)
        else:
            small = W("n4_no_rhythm")
        boxes.append(_now("green", W("n4_ready").format(n=ready), small))
    else:
        boxes.append(_now("", W("n4_none"), W("n4_none_small")))
    return boxes


def _json_for_script(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _fan(photos):
    return "".join(f"<img src='{html.escape(photo_src(p), quote=True)}' alt=''>" for p in photos[:3])


def _parts(parts):
    """The hello's words (hello_lines' [{"text", "name"}]) as markup: every word escaped, the name in <em>."""
    out = []
    for p in parts or []:
        if not isinstance(p, dict):
            continue
        t = html.escape(str(p.get("text") or ""))
        out.append(f"<em>{t}</em>" if p.get("name") else t)
    return "".join(out)


# The four tiles (her section 4): which kind each one makes. A press opens "Create a reel: which shoot?" (make_box and
# the page's script); the post kits screen stays the plain link (a saved copy of the page, a new tab).
TILES = (("reel", "t_reel"), ("carousel", "t_carousel"), ("stories", "t_stories"), ("captions", "t_captions"))


def make_box():
    """"Create a reel: which shoot?" (her section 4), drawn hidden: the page's script fills its title, its list (from
    /make-list) and its lines, all as text. + A new shoot is always there; Your shoots and the search box only when
    there are shoots (the search from 7)."""
    e = html.escape
    return (f"<div class='mk' id='mk' hidden><div class='mkbox' role='dialog' aria-modal='true' aria-labelledby='mkT' tabindex='-1'>"
            f"<div class='mkh'><h3 id='mkT'></h3><button type='button' id='mkX' aria-label='{e(W('mk_close'), quote=True)}'>&times;</button></div>"
            f"<p id='mkS'>{e(W('mk_sub'))}</p>"
            f"<div class='mklist' id='mkTop'><button type='button' class='mkr new' id='mkNew'><span class='im' aria-hidden='true'>+</span>"
            f"<span><b>{e(W('mk_new'))}</b><small>{e(W('mk_new_small'))}</small></span><span class='ar' aria-hidden='true'>&rarr;</span></button></div>"
            f"<p class='mknote' id='mkNote' role='status' hidden></p>"
            f"<p class='mklab' id='mkLab' hidden>{e(W('mk_shoots'))}</p>"
            f"<input class='mkfind' id='mkF' type='search' placeholder='{e(W('mk_find'), quote=True)}' aria-label='{e(W('mk_find'), quote=True)}' hidden>"
            f"<div class='mklist' id='mkL'></div></div></div>")


def page_html(query="", start=False):
    """The home page. query: the address's own (?wrapped=1 shows the Your year bar any time, for testing: hers).
    start: have the small copies the page wants made when some are missing (the page server passes True)."""
    try:
        force_year = "1" in (parse_qs(query or "").get("wrapped") or [])
    except ValueError:
        force_year = False
    f = facts(force_year=force_year, start=start)
    e = html.escape
    boxes = now_boxes(f)
    live_card = " live" if f.get("card") else ""
    # the hello (her section 3): a greeting and one line, made only from her approved lines, drawn here as text
    h = f.get("hello") or {}
    greet = _parts(h.get("greeting_parts")) if h.get("greeting_parts") else e(h.get("greeting") or W("hello_plain"))
    line = _parts(h.get("line_parts")) if h.get("line_parts") else e(h.get("line") or "")
    hello = (f"<section class='hello' id='hello' data-group='{e(str(h.get('group') or ''), quote=True)}'>"
             f"<div class='bgs' aria-hidden='true'><img alt=''><img alt=''></div>"
             f"<div class='tx'><h2 id='hi'>{greet}</h2>{f'<p>{line}</p>' if line else ''}</div>"
             + (f"<p class='samplenote' id='sampleNote' hidden>{e(f['samples']['note'])}</p>" if f.get("samples") else "")
             + "</section>")
    # Turn your shoots into posts, the four tiles, and the one button (no "Newest" box: her section 2)
    kits_btn = W("s3_see") if (f.get("kits") or f.get("newest")) else W("s3_create")
    tiles = "".join(
        f"<a class='tl' href='/make-posts' data-make='{make}' data-item='posts' aria-label='{e(W('t_aria').format(word=W(key)), quote=True)}'>"
        f"<img alt=''><b>{e(W(key))}</b></a>" for make, key in TILES)
    big = (f"<section id='s3'><h1 class='big'>{W('s3_n')}</h1><p class='sub'>{e(W('s3_p'))}</p>"
           f"<div class='tiles' id='tiles'>{tiles}</div>"
           f"<div class='go-row'><a class='btn solid' id='kitsBtn' data-item='posts' href='/make-posts'>{e(kits_btn)}</a></div></section>")
    # My posting queue on the left, with the last three posts of their grid; Back up a card and My editing queue
    # stacked on the right (hers: "That looks so good. I love that.")
    grid = f.get("grid") or []
    stack = ("<div class='stack' id='stack'>" + "".join(f"<img src='{e(u, quote=True)}' alt=''>" for u in grid[:3])
             + f"<small>{e(W('s4_grid'))}</small></div>") if grid else ""
    posting = (f"<a class='pq{'' if grid else ' nogrid'}' id='s4' data-item='posting' href='/posting.html'>"
               f"<div><h2 class='n'>{W('s4_n')}</h2><p>{e(W('s4_p'))}</p><div class='now' id='n4'>{boxes[3]}</div>"
               f"<span class='lnk2'>{e(W('s4_go'))}</span></div>{stack}</a>")
    also = (f"<div class='also'>"
            f"<a class='row{live_card}' id='s1' data-item='backup' href='/backups'><div><span class='n'>{W('s1_n')}</span><p>{e(W('s1_p'))}</p></div>"
            f"<div class='now' id='n1'>{boxes[0]}</div><span class='ar' aria-hidden='true'>&rarr;</span></a>"
            f"<button class='row' id='s2' data-item='queue' type='button'><div><span class='n'>{W('s2_n')}</span><p>{e(W('s2_p'))}</p></div>"
            f"<div class='now' id='n2'>{boxes[1]}</div><span class='ar' aria-hidden='true'>&rarr;</span><span id='editingWords' hidden></span></button>"
            f"</div>")
    low = f"<div class='low'>{posting}{also}</div>"
    # the monthly recap card (drawn hidden when they hid it, so Show my monthly recap brings it back at once)
    recap = ""
    foot = ""
    r = f.get("recap")
    if r:
        chips = "".join("<span><i>%s</i> %s</span>" % (e(c.split(" ", 1)[0]), e(c.split(" ", 1)[1] if " " in c else "")) for c in r["chips"])
        title = W("rc_t").format(label=e(r["label"]), word=e(r["word"]))
        recap = (f"<div class='rc' id='rc' data-m='{e(r['month'], quote=True)}'{' hidden' if f['recap_hidden'] else ''}>"
                 f"<a class='all' href='{e(r['url'], quote=True)}' aria-label='{e(W('rc_watch_aria').format(label=r['label']), quote=True)}'></a>"
                 f"<div class='fan' id='rcFan'>{_fan(r['photos'])}</div><div><b id='rcT'>{title}</b><div class='chips' id='rcC'>{chips}</div></div>"
                 f"<span class='playbtn' aria-hidden='true'>{e(W('watch'))}</span>"
                 f"<button class='x' id='rcX' type='button' title='{e(W('rc_hide_title'), quote=True)}' aria-label='{e(W('rc_hide_aria'), quote=True)}' aria-haspopup='true' aria-expanded='false'>&times;</button>"
                 f"<div class='rcmenu' id='rcM' hidden><button type='button' data-h='month'>{e(W('rc_month'))}</button>"
                 f"<button type='button' data-h='all'>{e(W('rc_all'))}</button></div><p class='rcnote' id='rcNote' role='status'></p></div>")
        foot = f"<span id='rcBack'{'' if f['recap_hidden'] else ' hidden'}><button id='rcShow' type='button'>{e(W('rc_show'))}</button></span>"
    year = ""
    y = f.get("year_bar")
    if y:
        year = (f"<div class='yr' id='yr'><a class='all' href='{e(y['url'], quote=True)}' aria-label='{e(W('yr_watch_aria').format(year=y['year']), quote=True)}'></a>"
                f"<div class='fan' id='yrFan'>{_fan(y['photos'])}</div><div><b>{W('yr_b').format(year=e(y['year']))}</b><small>{e(W('yr_small'))}</small></div>"
                f"<span class='playbtn' aria-hidden='true'>{e(W('watch'))}</span></div>")
    # what the page's script draws from: kit folder NAMES and photo numbers only (never a path, never markup)
    sm = f.get("samples") or None
    data = {"hello_photos": f.get("hello_photos") or [], "tiles": f.get("tiles") or [],
            "samples": {"hello": sm["hello"], "tiles": sm["tiles"]} if sm else None}
    words = dict(home_base.WORDS)
    words.update(home_base.OUR_WORDS)
    words.update({"rc_didnt": W("rc_didnt")})
    words.update({k: W(k) for k in list(WORDS) + list(OUR_WORDS) if k.startswith("mk_")})
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(brand.title())}</title><style>{look.head_css()}{CSS_EXTRA}</style></head><body class='home30' data-stamp='{e(fingerprint())}'>"
            f"<div class='wrap'><div class='bar'>{brand.bar()}"
            f"<span class='when' id='when'>{e(f['today'])}</span>"
            f"<span class='fold'><button class='lnk' id='folder' data-item='folder' type='button'>{e(W('folder').format(short=brand.short()))}</button><span class='note' role='status'></span></span></div>"
            f"<p class='offline' id='offline' hidden>{e(W('offline'))}</p>"
            f"{hello}{big}{low}"
            f"{recap}{year}<p class='foot'>{foot}</p>{make_box()}"
            f"</div><script type='application/json' id='facts'>{_json_for_script(data)}</script>"
            f"<script>const W = {_json_for_script(words)};{home_base.JS_SHARED}{HELLO_JS}{SCRIPT}</script></body></html>")


# ---------- the routes of the home page's own (the posting server hands them over) ----------

POST_ROUTES = ("/home-recap",)


def _answer(handler, obj, code=200):
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


def handle_post(handler, path, query):
    """POST /home-recap {"hide": "month" | "all" | "show", "month": "YYYY-MM"}: the recap card's two choices and
    the footer's Show my monthly recap. Only from this server's own page (the pickers' guard: Host, Origin, type,
    length), every field checked. Answers {"ok": true, "hide": what is kept now} or {"ok": false, "problem": words}."""
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
        if refused is None and (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site":
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _answer(handler, {"ok": False, "problem": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _answer(handler, {"ok": False, "problem": arrange.NOT_UNDERSTOOD}, 400)
        if (path != "/home-recap" or not isinstance(body, dict) or set(body) - {"hide", "month"} or body.get("hide") not in ("month", "all", "show")
                or ("month" in body and body["month"] is not None and not isinstance(body["month"], str))
                or (body["hide"] == "month" and not _month_ok(body.get("month")))):
            return _answer(handler, {"ok": False, "problem": arrange.NOT_UNDERSTOOD}, 400)
        try:
            kept = set_recap_hide({"month": body.get("month"), "all": "all", "show": ""}[body["hide"]])
        except OSError as e:
            say(f"home: couldn't save the recap choice ({e.__class__.__name__})")
            return _answer(handler, {"ok": False, "problem": W("rc_didnt")}, 500)
        return _answer(handler, {"ok": True, "hide": kept})
    except (Exception, SystemExit) as e:  # noqa: BLE001
        say(f"home: POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _answer(handler, {"ok": False, "problem": W("rc_didnt")}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def write_page():
    HOME.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page_html(), encoding="utf-8")
    return PAGE


def url():
    """The live home page: on the posting server, started if it isn't running."""
    f = HOME / "posting-url.txt"
    def alive(u):
        try:
            # Never through a proxy (this_computer.open_local): a proxy can't see this computer's own pages, so the
            # check would fail and a second page server be started on the next address. With no proxy set (every
            # Mac and PC at home) this is exactly what it was.
            this_computer.open_local(u, timeout=1).read(1)
            return True
        except Exception:  # noqa: BLE001
            return False
    if f.exists():
        base = f.read_text(encoding="utf-8").strip().rsplit("/", 1)[0]
        if alive(base + "/home"):
            return base + "/home"
    HOME.mkdir(parents=True, exist_ok=True)
    import fresh
    try:  # its log is ~/.studio/logs/posting.log (fresh.server_log); the address comes from posting-url.txt
        fresh.start_server([sys.executable, str(HERE / "posting_queue.py"), "serve"], "posting")
    except OSError:
        return None
    for _ in range(50):
        time.sleep(0.1)
        if f.exists():
            base = f.read_text(encoding="utf-8").strip().rsplit("/", 1)[0]
            if alive(base + "/home"):
                return base + "/home"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("page"); sub.add_parser("url"); sub.add_parser("pending"); sub.add_parser("seen"); sub.add_parser("journey")
    d = sub.add_parser("did"); d.add_argument("category", choices=CATEGORIES); d.add_argument("--note")
    c = sub.add_parser("click"); c.add_argument("item", choices=CATEGORIES)
    hl = sub.add_parser("hello"); hl.add_argument("--mark", action="store_true")
    a = ap.parse_args()
    import fresh
    fresh.announce()                       # this folder is where the Assistant's code is now (see fresh.py)
    if a.cmd == "page":
        say(str(write_page()))
    elif a.cmd == "url":
        u = url()
        if not u:
            say(f"STOP: couldn't start {brand.the_name()}'s page server.")
            return 2
        say(u)
    elif a.cmd == "pending":
        say(json.dumps(pending(), indent=1))
        # an order they arranged on a picker page and pressed the final button on: one line each, after the
        # list ("ARRANGED: <kit folder> | reel | 12 photos"). parts/arrange.md says what to do with one.
        try:
            import arrange
            for w in arrange.waiting():
                say(arrange.waiting_line(w))
        except Exception:  # noqa: BLE001  (no such file, or anything else: pending must still answer)
            pass
    elif a.cmd == "seen":
        mark_seen(); say("ok")
    elif a.cmd == "did":
        say(json.dumps(record_done(a.category, a.note)))
    elif a.cmd == "click":
        record_click(a.item); say("ok")
    elif a.cmd == "journey":
        say(json.dumps(load_journey(), indent=1))
    elif a.cmd == "hello":
        say(json.dumps(hello(a.mark), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
