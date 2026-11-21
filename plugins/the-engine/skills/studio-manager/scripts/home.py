#!/usr/bin/env python3
"""The Assistant's home page (Nicole's v28, Nov 17; posts first since her v29, Nov 19), in the Claude app's browser pane.

Top to bottom: the bar (the name, the date, Open my Assistant folder); the hello (a collage of the newest shoot's
photos, each framed on its faces, a greeting made from what is really going on and a button that goes there);
one big card, Turn your shoots into posts, whose button goes to its own screen (/make-posts); My posting queue,
full width; then "Also in your Assistant" with two smaller cards, Back up a card (its own screen, /backups) and
My editing queue; each card saying what is going on right now; the monthly recap card; and the Your year bar in
its dates. No step numbers and no list of post kits, so it stays clean after years of shoots: every backup and
every post kit is on its own screen (home_base.py). Served
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
# The home page, top to bottom (Nicole's v28, Nov 17; her home-test.html and hello.js, built our way):
#   the bar          the name, the date (hidden under 520 px), Open my Assistant folder
#   the hello        a collage of the newest shoot's photos, each framed on its faces (faces.py), a greeting made
#                    from what is really going on, a button that goes there, and "Another hello" in the corner
#   posts first      (her v29) the big Turn your shoots into posts card with its one button, My posting queue
#                    full width, then "Also in your Assistant": Back up a card and My editing queue, smaller;
#                    her exact words, each card with a box saying what is going on right now
#   the recap card   the month's numbers (wrapped.py), Watch, and the x that hides it (kept in home-recap.json)
#   Your year        the bar, only in its dates (Dec 1 to Jan 15, after about a year: wrapped.home_answers)
# Everything on it is read fresh, and only read, from what the Assistant already keeps. The server draws the
# steps, the card and the bar; the page's script draws the hello (it needs the clock and what was said last time).
# No path is in the page: a photo is a kit's folder name and a number (/kit-photo), a face a kit and numbers.

# The words to paste in the chat for the two steps that start a conversation (shown on their own screens).
SAY = {"backup": home_base.WORDS["b_say"], "posts": home_base.WORDS["m_say"], "setup": "set up my Assistant folder"}

# Nicole's words (pages/home-test.html, v28; the layout's own from pages/home-preview.html, v29), whole. "You would say what it is": the labels are plain on purpose
# (her section 10); do not make them clever. <em> is hers (the accent word). {…} is filled in by the page.
WORDS = {
    "folder": "Open my {short} folder",
    "again": "↻ Another hello",
    "again_title": "Another hello",
    "hello_plain": "Hello.",
    # v29 (her pages/home-preview.html, Nov 19): posts first. The big card, the posting queue under it, then
    # "Also in your Assistant" with the two smaller cards. No step numbers, no "Your workflow" (both gone, hers).
    "s3_n": "Turn your shoots <em>into posts</em>",
    "s3_p": "Turn your shoot into reels, carousels, stories, and captions.",
    "s3_create": "Create your post kits →",         # the button with no post kits yet
    "s3_see": "See all my post kits →",             # the same button once there are some
    "also_h": "Also in your Assistant",
    "s1_n": "Back up <em>a card</em>",
    "s1_p": "Copies your card to your drive, checks every photo, and sorts it into shoots.",
    "s2_n": "My editing <em>queue</em>",
    "s2_p": "The shoots you need to edit and when they're due.",
    "s4_n": "My posting <em>queue</em>",
    "s4_p": "Your posts ready to go, and how your grid will look.",
    "s4_go": "Open my posting queue →",
    # what is going on right now, step by step
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
    "n3_newest": "Newest: {short}",
    "n3_kits": "{n} post kit{s}",
    "n3_none": "No post kits yet",
    "n3_none_small": "Start with any finished shoot",
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
    "watch": "▶ Watch",
    "rc_hide_title": "Hide",
    "rc_hide_aria": "Hide the monthly recap",
    "rc_month": "Hide it for this month",
    "rc_all": "Stop showing monthly recaps",
    "rc_show": "Show my monthly recap",
    "yr_b": "Your {year}, <em>wrapped.</em>",
    "yr_small": "Your year with your assistant, story by story. Ready to share.",
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
        return {"kit": name, "n": n, "v": p["v"]}

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
        if not isinstance(t, str) or not t.startswith("posting-thumbs/") or "\\" in t or ".." in t.split("/"):
            return None
        if not (HOME / t).is_file():
            return None
        return "/" + quote(t, safe="/")
    except (OSError, ValueError):
        return None


def facts(force_year=False, start=False):
    """Everything the home page shows, read from what the Assistant already keeps. Each part fails soft: one
    record that can't be read never takes the page with it. Names and numbers only, never a path."""
    day = _today()
    iso = day.isoformat()
    f = {"today": day.strftime("%A, %B ") + str(day.day), "me": "", "card": None, "backup": None, "queue": [], "kits": 0,
         "newest": None, "posting": {"today": [], "late": [], "posted_week": [], "ready": 0, "per_week": None},
         "year": None, "collage": None, "recap": None, "recap_hidden": False, "year_bar": None}
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
            # the hello's collage: up to 12 favorite photos of the NEWEST shoot (hers), small copies only
            newest = max((k for k in got["kits"] if k["favs"]), key=lambda k: (k["date"], k["folder"]), default=None)
            if newest:
                shown = [p for p in (pics.one(newest["folder"], n) for n in newest["favs"][:wrapped.FAVS]) if p]
                if shown:
                    f["collage"] = {"kit": newest["folder"], "photos": [{"n": p["n"], "v": p["v"]} for p in shown]}
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
    if start:
        pics.start()
    return f


# ---------- the page's look: hers (home-test.html's own styles), in the Assistant's colours and font ----------
# Her serif accent is the coral accent word here (Dustin, Nov 7: no serif). Every animation is under
# prefers-reduced-motion: no-preference, so with reduced motion nothing moves.
CSS_EXTRA = home_base.CSS + r"""
.bar .fold{position:relative;display:inline-flex}
.bar .lnk{font:600 13px/1 var(--sans);color:var(--ink-2);background:none;border:0;cursor:pointer;padding:8px 10px;border-radius:999px;text-decoration:none;white-space:nowrap}
.bar .lnk:hover{color:var(--ink);background:var(--sand-l)}
.bar .fold .note{position:absolute;right:0;top:100%;margin:0;width:max-content;max-width:min(320px,80vw);text-align:right;z-index:4;background:var(--cream);border-radius:8px;padding:0 4px}
.bar .fold .note:empty{display:none}
@media(max-width:520px){.bar .when{display:none}.bar .fold{margin-left:auto}}
.hello{position:relative;margin-top:1.2rem;min-height:240px;border-radius:26px;overflow:hidden;color:#fff;display:flex;align-items:flex-end;padding:clamp(1.2rem,3.4vw,2rem);background:#2a2f3a}
.hello .bgs{position:absolute;inset:0;display:grid;gap:3px}
.hello .tile{position:relative;overflow:hidden;background:#2a2f3a}
.hello .tile img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0}
.hello .tile img.on{opacity:1}
.hello::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,rgba(20,22,30,.86),rgba(20,22,30,.32) 55%,rgba(20,22,30,.05));pointer-events:none}
.hello .tx{position:relative;z-index:1;max-width:38em;min-width:0}
.hello h3{margin:0;font:600 clamp(28px,3.8vw,44px)/1.05 var(--sans);letter-spacing:-.03em;overflow-wrap:anywhere}.hello h3 em{font:inherit;font-style:normal;color:#FFB39A}
.hello p{margin:.45rem 0 0;font-size:clamp(15.5px,1.4vw,18px);color:#eef0f4;overflow-wrap:anywhere}
.hello .hgo{margin-top:.9rem;display:inline-flex;gap:.4rem;align-items:center;font:600 13.5px/1 var(--sans);padding:10px 16px;border-radius:999px;border:0;background:#fff;color:var(--ink);cursor:pointer;transition:background .2s}
.hello .hgo:hover{background:var(--coral)}
.hello .note{color:#eef0f4}
.again{position:absolute;right:14px;top:14px;z-index:2;font:600 12px/1 var(--sans);color:#fff;background:rgba(20,22,30,.35);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);border:0;border-radius:999px;padding:8px 11px;cursor:pointer;opacity:.75}
.again:hover,.again:focus-visible{opacity:1}
.step{position:relative;display:flex;flex-direction:column;gap:.5rem;text-align:left;padding:18px 18px 16px;border:0;border-radius:20px;background:var(--paper);box-shadow:0 1px 0 var(--line);cursor:pointer;font:inherit;color:inherit;text-decoration:none;min-width:0;transition:transform .3s var(--ease),box-shadow .3s var(--ease)}
.step:hover{transform:translateY(-3px);box-shadow:0 0 0 2px var(--coral),var(--shadow)}
.step .n{font:600 19px/1.15 var(--sans);letter-spacing:-.02em}.step .n em{font:inherit;font-style:normal;color:var(--coral-2)}
.step p{margin:0;color:var(--ink-2);font-size:14px;line-height:1.45}
.step .now{margin-top:auto;display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:14px;background:var(--cream);min-height:58px;min-width:0}
.step .now img{width:40px;height:50px;object-fit:cover;border-radius:7px;flex:none;background:var(--sand-l)}
.step .now span{font:500 13px/1.35 var(--sans);color:var(--ink);min-width:0;overflow-wrap:anywhere}.step .now small{display:block;color:var(--ink-2);font-size:12px}
.step .now .dot{width:9px;height:9px;border-radius:50%;flex:none;background:var(--ocean)}
.step .now .dot.coral{background:var(--coral)}.step .now .dot.green{background:var(--long)}.step .now .dot.red{background:#C2412D}.step .now .dot.yellow{background:#D9A400}
.step .go{font:600 13px/1 var(--sans);color:var(--coral-2)}
.step .note{margin-top:0}
.step.live{box-shadow:0 0 0 2px var(--coral),0 0 26px rgba(240,127,90,.35)}
.step .now small.late{color:#C2412D}
.mk{margin-top:1.6rem;padding:22px 22px 18px;cursor:default}
.mk:hover{transform:none;box-shadow:0 1px 0 var(--line)}
.mk .n{font-size:26px}.mk>p{margin:.1rem 0 0}
.mk-go{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:1rem;min-width:0}
.mk-go .now{flex:1 1 240px;margin:0}
.btn.big{font-size:15px;padding:13px 20px;white-space:nowrap}
.step.full{margin-top:12px}
.also{margin-top:1.8rem}.also h2{margin:0 0 .6rem;font:600 13px/1.3 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.also-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media(max-width:620px){.also-row{grid-template-columns:minmax(0,1fr)}}
.step.sm{padding:14px 16px;gap:.35rem;background:transparent;box-shadow:0 0 0 1px var(--line)}
.step.sm .n{font-size:16px}.step.sm p{font-size:13px}.step.sm .now{min-height:0;background:var(--paper)}
.step.sm.live{box-shadow:0 0 0 2px var(--coral),0 0 26px rgba(240,127,90,.35)}
.yr,.rc{margin-top:1.8rem;position:relative;display:flex;align-items:center;gap:1.2rem;border-radius:22px;padding:16px 20px;min-width:0}
.yr{background:var(--ink);color:#fff}.rc{background:linear-gradient(120deg,#FFE7DD,#F6EEFF);color:var(--ink)}
.yr[hidden],.rc[hidden]{display:none}
.yr .fan,.rc .fan{position:relative;width:110px;height:64px;flex:none}
.yr .fan img,.rc .fan img{position:absolute;left:36px;top:0;width:44px;height:64px;object-fit:cover;border-radius:7px;transition:transform .5s var(--ease)}
.yr .fan img{box-shadow:0 8px 18px rgba(0,0,0,.4)}.rc .fan img{box-shadow:0 8px 18px rgba(31,36,48,.25)}
.fan img:nth-child(1){transform:translateX(-30px) rotate(-10deg)}.fan img:nth-child(3){transform:translateX(30px) rotate(10deg)}
.yr:hover .fan img:nth-child(1),.rc:hover .fan img:nth-child(1){transform:translateX(-38px) rotate(-14deg)}.yr:hover .fan img:nth-child(3),.rc:hover .fan img:nth-child(3){transform:translateX(38px) rotate(14deg)}
.yr>div,.rc>div{min-width:0}
.yr b,.rc b{font:600 20px/1.1 var(--sans);letter-spacing:-.02em;overflow-wrap:anywhere}.yr b em{font:inherit;font-style:normal;color:var(--coral)}.rc b em{font:inherit;font-style:normal;color:var(--coral-2)}
.yr small{display:block;color:#b9bcc6;font-size:13.5px;margin-top:3px}
.yr .playbtn,.rc .playbtn{margin-left:auto;font:600 13px/1 var(--sans);padding:10px 15px;border-radius:999px;white-space:nowrap}
.yr .playbtn{background:var(--coral);color:var(--ink)}.rc .playbtn{background:var(--ink);color:#fff}
.yr .all,.rc .all{position:absolute;inset:0;border-radius:22px;z-index:1}
.rc .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}
.rc .chips span{font:600 12.5px/1 var(--sans);background:rgba(255,255,255,.75);border-radius:999px;padding:6px 10px}
.rc .chips span i{font-style:normal;font-weight:600;color:var(--coral-2)}
.rc .x{position:absolute;right:8px;top:6px;z-index:2;border:0;background:none;color:var(--ink-2);font:600 18px/1 var(--sans);cursor:pointer;padding:4px 7px;border-radius:999px;opacity:.6}
.rc .x:hover,.rc .x:focus-visible{opacity:1;background:rgba(255,255,255,.7)}
.rcmenu{position:absolute;right:10px;top:34px;z-index:3;background:#fff;border-radius:14px;box-shadow:var(--shadow);padding:6px;display:grid;min-width:210px}
.rcmenu[hidden]{display:none}
.rcmenu button{border:0;background:none;text-align:left;font:500 13.5px/1.2 var(--sans);padding:10px 12px;border-radius:10px;cursor:pointer;color:var(--ink)}
.rcmenu button:hover,.rcmenu button:focus-visible{background:var(--sand-l)}
.rc .rcnote{position:absolute;left:20px;bottom:2px;margin:0;font-size:12px;color:var(--coral-2);z-index:2}
@media(max-width:560px){.yr .fan,.rc .fan{display:none}.rc{flex-wrap:wrap;padding-right:34px}.rc .playbtn{margin-left:0}}
.foot{margin-top:1.4rem;font-size:13px;color:var(--ink-2);min-height:1em}
.foot button{border:0;background:none;padding:0;font:inherit;color:var(--ink-2);text-decoration:underline;cursor:pointer}
@media (prefers-reduced-motion: no-preference){
.hello .tile img{transition:opacity 1.6s ease;animation:kb 14s ease-in-out infinite alternate}
@keyframes kb{from{transform:scale(1)}to{transform:scale(1.07)}}
.hello .tx > *{animation:rise .7s var(--ease) both}.hello .tx p{animation-delay:.12s}.hello .tx .hgo{animation-delay:.24s}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.step.live .now .dot{animation:pulse 1.6s ease-in-out infinite}
@keyframes pulse{50%{box-shadow:0 0 0 6px rgba(240,127,90,.25)}}
}
@media (prefers-reduced-motion: reduce){.step,.fan img,.hello .hgo{transition:none}.step:hover{transform:none}}
"""

# The hello (Nicole's hello.js, Nov 17): "personal, exciting, fun, and definitely different, like every time." Every
# line comes from what is really going on (F, the facts the server read); only the wording is playful. Her openers
# and her lines, whole. Ours underneath: the words reach the page as text (textContent), never as markup; the
# name is only ever the one in their Brand File (no name: her openers without one, never an invented one); what
# was said lately is kept in this browser (hers, a nicety for this viewer only), inside try/catch.
HELLO_JS = r"""
const F = JSON.parse($('facts').textContent);
const STILL = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
const pick1 = a => a[Math.floor(Math.random() * a.length)];
// each line knows where it leads: [weight, subject, words, button]
const GO = {backup: ['Back it up', 'backup'], posting: ['My posting queue', 'posting'], editing: ['My editing queue', 'queue'],
            posts: ['Make posts', 'posts'], year: ['See your year', '']};
function hellos(F, d){
  const me = F.me || '', P = F.posting || {};
  const hr = d.getHours(), day = d.toLocaleDateString('en-US', {weekday: 'long'}), mo = d.getMonth();
  // an opener is [the plain words, the accent word]: "Welcome back, " + "Nicole." with a name, "Welcome back" + "." without
  const N = t => me ? [t + ', ', me + '.'] : [t, '.'], Nx = t => me ? [t + ', ', me + '!'] : [t, '!'], Nq = t => me ? [t + ', ', me + '?'] : [t, '?'];
  const op = [N(`Welcome back`), Nx(`Hi`), N(`Hey hey`), N(`Oh hi`), N(`There you are`), Nx(`Look who’s here`), [`Hello, `, `you.`]];
  if (hr < 12) op.push(N(`Good morning`), N(`Morning`), N(`Rise and shine`), Nq(`Coffee first`));
  else if (hr < 17) op.push(N(`Good afternoon`), N(`Afternoon`), N(`Hey there`));
  else if (hr < 21) op.push(N(`Good evening`), N(`Evening`));
  else op.push(Nq(`Late-night edit`), Nq(`Still up`), N(`Night owl mode`));
  op.push(day === 'Monday' ? Nx(`New week`) : day === 'Friday' ? Nx(`Happy Friday`) : N(`Happy ${day}`));
  if (mo === 10 || mo === 11) op.push([`Hello, `, `holiday season.`]);
  const L = [], add = (w, key, opts, go) => L.push([w, key, pick1(opts), go]);
  (P.today || []).forEach(x => { const n = x.who, k = x.kind;
    add(5, 'today', [`${n} ${k} goes out today. Let’s make it a good one.`, `Today’s the day for ${n} ${k}.`, `${n} ${k} is up today, and it’s ready when you are.`], 'posting'); });
  (P.late || []).forEach(x => { const n = x.who, k = x.kind, g = x.days;
    add(4, 'late', [`${n} ${k} has been waiting ${g === 1 ? 'a day' : g + ' days'} to go out. Today?`, `Psst: ${n} ${k} is still waiting in the wings.`, `${n} ${k} is still ready and waiting. No pressure. (A little pressure.)`], 'posting'); });
  const pw = (P.posted_week || []).length;
  if (pw) add(3, 'posted', pw === 1 ? [`You posted ${P.posted_week[0].who} ${P.posted_week[0].kind} this week. Love that for you.`, `One post out this week. Look at you go.`]
                                    : [`${pw} posts out this week. Look at you go.`, `${pw} posts this week already. Your feed is glowing.`, `You’ve posted ${pw} times this week. That’s how it’s done.`], 'posting');
  if (P.ready) add(2, 'tank', P.ready <= 1 ? [`Only one post left ready to go. Want to make a few more?`] : [`${P.ready} posts are lined up and ready. Future you says thank you.`, `You’ve got ${P.ready} posts ready to go. Smooth sailing.`], P.ready <= 1 ? 'posts' : 'posting');
  if (F.card) { const f = many(F.card.files || 0);
    add(6, 'card', [`Your card is in. Let’s get those ${f} files safe.`, `I see a card! ${f} files, ready to back up whenever you are.`], 'backup'); }
  const q = F.queue || [];
  if (q.length === 1) add(3, 'queue', [`“${q[0].name}” is waiting for your magic.`, `“${q[0].name}” is in your editing queue, ready when you are.`], 'editing');
  else if (q.length > 1) add(3, 'queue', [`${q.length} shoots are waiting for your magic.`, `${q.length} shoots in your editing queue. One at a time.`], 'editing');
  q.filter(x => x.due_in !== null && x.due_in !== undefined).forEach(x => { const g = x.due_in;
    if (g >= 0 && g <= 3) add(5, 'due', [`Heads up: “${x.name}” is due ${g === 0 ? 'today' : g === 1 ? 'tomorrow' : 'in ' + g + ' days'}.`], 'editing'); });
  const Y = F.year;
  if (Y) {
    if (Y.newest) add(2, 'newest', [`${Y.newest} is your newest shoot. Want to turn it into posts?`, `Still thinking about ${Y.newest}? Let’s make something from it.`], 'posts');
    if (Y.reels) add(1, 'reels', [`${Y.reels} reels made so far this year. That’s a lot of beats.`, `${Y.reels} reels this year and counting.`], 'year');
    if (Y.photos) add(1, 'photos', [`${many(Y.photos)} finished photos this year. Every one of them yours.`], 'year');
    if (Y.top) add(1, 'top', [`${Y.top} is your most-made-from shoot this year. Iconic.`], 'year');
  }
  if (day === 'Friday') add(2, 'day', [`Friday’s a great day to line up the weekend’s posts.`], 'posting');
  if (day === 'Monday') add(2, 'day', [`Fresh week, fresh posts. Let’s see what’s waiting.`], 'posting');
  if (!L.length) add(1, 'none', [`Everything’s calm. A great day to make something.`], 'posts');
  return {op, L};
}
function recentSaid(){ try { const r = JSON.parse(localStorage.getItem('assistantHello') || '[]'); return Array.isArray(r) ? r.filter(x => typeof x === 'string') : []; } catch (e) { return []; } }
function goFrom(where, el){
  const g = GO[where]; if (!g) return;
  if (g[1]) clicked(g[1]);
  if (where === 'editing') assistant('/queue-url', el, W.opening_queue);
  else if (F.go[where]) location.href = F.go[where];
}
function sayHello(el, d){
  const {op, L} = hellos(F, d || new Date());
  let recent = recentSaid();
  const said = o => o[0] + o[1];
  const freshOp = op.filter(o => !recent.includes(said(o))), o = pick1(freshOp.length ? freshOp : op);
  const lastKeys = recent.filter(x => x.startsWith('k:')).slice(-2);          // a different subject than the last two times
  let pool = L.filter(l => !lastKeys.includes('k:' + l[1]) && !recent.includes(l[2])); if (!pool.length) pool = L;
  let r = Math.random() * pool.reduce((t, l) => t + l[0], 0), line = pool[0];
  for (const l of pool) { r -= l[0]; if (r <= 0) { line = l; break; } }
  recent = recent.concat([said(o), line[2], 'k:' + line[1]]).slice(-24); try { localStorage.setItem('assistantHello', JSON.stringify(recent)); } catch (e) {}
  const g = GO[line[3]];
  el.textContent = '';
  const h = document.createElement('h3'), em = document.createElement('em'), p = document.createElement('p');
  h.append(o[0]); em.textContent = o[1]; h.append(em); p.textContent = line[2]; el.append(h, p);
  el.dataset.subject = line[1];
  if (g && (line[3] === 'editing' || F.go[line[3]])) {
    const b = document.createElement('button'), ar = document.createElement('span');
    b.className = 'hgo'; b.type = 'button'; b.dataset.go = line[3]; b.append(g[0] + ' '); ar.setAttribute('aria-hidden', 'true'); ar.textContent = '→'; b.append(ar);
    b.onclick = () => goFrom(line[3], b); el.append(b);
  }
}

/* the collage: tall tiles, each photo centered on its faces (the Mac's own face finder, asked by the server) */
const clamp01 = v => Math.max(0, Math.min(1, v));
function window1(fs, vis){
  let best = null;
  fs.forEach(a => { const lo = clamp01(Math.min(1 - vis, a.c - vis / 2)), hi = lo + vis;
    const inn = fs.filter(f => f.a >= lo - .005 && f.b <= hi + .005), score = inn.reduce((t, f) => t + f.size, 0);
    if (!best || score > best.score) best = {score, inn}; });
  if (!best || !best.inn.length) return fs.reduce((t, f) => t + f.c, 0) / fs.length;      // no stretch holds a whole face: the middle of them
  return (Math.min(...best.inn.map(f => f.a)) + Math.max(...best.inn.map(f => f.b))) / 2;
}
function aim(img, x, bw, bh){
  const f = x.f || {}, w = f.w || x.nw || 1000, h = f.h || x.nh || 1500, sc = Math.max(bw / w, bh / h), dw = w * sc, dh = h * sc, fc = f.faces || [];
  let cx = .5, cy = fc.length ? .35 : .5, px = .5, py = .5;        // no faces known (a PC, or none in the photo): the photo is centered
  if (fc.length) {
    cx = window1(fc.map(a => ({a: a[0], b: a[0] + a[2], c: a[0] + a[2] / 2, size: a[2] * a[3]})), bw / dw);
    cy = window1(fc.map(a => ({a: a[1] - a[3] * .4, b: a[1] + a[3] * 1.1, c: a[1] + a[3] / 2, size: a[2] * a[3]})), bh / dh);
    px = dw > bw + 1 ? clamp01((cx * dw - bw / 2) / (dw - bw)) : .5; py = dh > bh + 1 ? clamp01((cy * dh - .38 * bh) / (dh - bh)) : .5;   // heads about 38% down the tile
  }
  img.style.objectPosition = `${(px * 100).toFixed(1)}% ${(py * 100).toFixed(1)}%`;
  img.style.transformOrigin = `${(cx * dw - px * (dw - bw)).toFixed(0)}px ${(cy * dh - py * (dh - bh)).toFixed(0)}px`;
}
// two photos with the same number of faces, every face within 0.09 of the other's: frames from one burst
function twin(p, q){ const A = (p.f && p.f.faces) || [], B = (q.f && q.f.faces) || []; if (A.length !== B.length || !A.length) return false;
  const c = x => [x[0] + x[2] / 2, x[1] + x[3] / 2], ca = A.map(c).sort((u, v) => u[0] - v[0]), cb = B.map(c).sort((u, v) => u[0] - v[0]);
  return ca.every((u, i) => Math.hypot(u[0] - cb[i][0], u[1] - cb[i][1]) < .09); }
let HP = [], HTIMER = 0;
function collage(box, bg){
  clearInterval(HTIMER); if (!HP.length) return;
  const bw = box.clientWidth, n = Math.max(3, Math.round(bw / 165)), gap = 3, tw = (bw - gap * (n - 1)) / n, th = Math.max(230, Math.round(tw * 1.5));
  box.style.minHeight = th + 'px';
  bg.style.gridTemplateColumns = `repeat(${n},1fr)`;
  bg.textContent = '';
  for (let k = 0; k < n; k++) { const t = document.createElement('div'), a = document.createElement('img'), b = document.createElement('img');
    t.className = 'tile'; a.alt = ''; b.alt = ''; a.className = 'on'; a.style.animationDelay = `-${k * 2.3}s`; t.append(a, b); bg.append(t); }
  const put = (im, x) => { im.dataset.n = x.n; im.src = x.u; aim(im, x, tw, th); };
  const step = Math.max(1, Math.floor(HP.length / n)); let HQ = n * step + 1, lastT = -1;
  [...bg.children].forEach((t, k) => put(t.firstChild, HP[(k * step) % HP.length]));
  if (HP.length <= n || STILL) return;                                   // reduced motion: the photos stay as they are
  HTIMER = setInterval(() => {
    let k; do { k = Math.floor(Math.random() * n); } while (n > 1 && k === lastT); lastT = k;
    const t = bg.children[k]; if (!t) return;
    const on = t.querySelector('img.on'), off = on === t.firstChild ? t.lastChild : t.firstChild;
    off.onload = () => { on.classList.remove('on'); off.classList.add('on'); off.onload = null; }; put(off, HP[HQ++ % HP.length]);
  }, 2800);
}
async function startHello(box){
  const bg = box.querySelector('.bgs'), tx = box.querySelector('.tx');
  sayHello(tx);
  const C = F.collage; if (!C || !C.photos.length || !live) return;
  // the small copies only (never the photos themselves), and every face in one ask; if the faces take more than a
  // moment (a brand new shoot), the collage starts anyway and re-aims when they arrive
  const kq = encodeURIComponent(C.kit);
  const all = C.photos.map(p => ({n: p.n, u: '/kit-photo?kit=' + kq + '&n=' + p.n + '&size=s&v=' + encodeURIComponent(p.v || ''), f: {}, ok: false, tries: 0}));
  const load = x => new Promise(r => { const im = new Image(); im.onload = () => { x.ok = true; x.nw = im.naturalWidth; x.nh = im.naturalHeight; r(); }; im.onerror = () => r();
    if (x.tries) x.u = x.u.replace(/&t=\d+$/, '') + '&t=' + x.tries; im.src = x.u; });
  const faces = xs => fetch('/kit-faces?kit=' + kq + '&n=' + xs.map(x => x.n).join(','), {cache: 'no-store'}).then(r => r.json()).then(d => (d && d.faces) || {}).catch(() => ({}));
  const build = () => { HP = []; all.filter(x => x.ok).forEach(x => { if (!HP.some(y => twin(x, y))) HP.push(x); }); collage(box, bg); box.dataset.photos = HP.length; };
  async function round(first){
    const todo = all.filter(x => !x.ok);
    await Promise.all(todo.map(load));
    const got = todo.filter(x => x.ok); if (!got.length) return;
    const fq = faces(got).then(G => { got.forEach(x => { if (G[x.n]) x.f = G[x.n]; }); box.dataset.faces = '1'; });
    const late = first ? await Promise.race([fq.then(() => false), new Promise(r => setTimeout(() => r(true), 900))]) : await fq.then(() => false);
    if (late) fq.then(build);
    build();
  }
  await round(true);
  // a small copy that was still being made: asked for again a few times, then the collage is drawn again with it
  let tries = 0;
  (function again(){ if (!all.some(x => !x.ok) || ++tries > 6) return;
    setTimeout(async () => { all.forEach(x => { if (!x.ok) x.tries = tries; }); await round(false); again(); }, 5000); })();
  let rsz = 0; addEventListener('resize', () => { clearTimeout(rsz); rsz = setTimeout(() => collage(box, bg), 300); });
}
"""

SCRIPT = r"""
// every card records what was pressed, so the chat knows (journey.json); then it goes where it goes
document.querySelectorAll('[data-item]').forEach(b => b.addEventListener('click', () => clicked(b.dataset.item)));
$('s2').onclick = () => assistant('/queue-url', $('editingWords'), W.opening_queue);
$('folder').onclick = () => assistant('/open-home', $('folder'), W.opening);
if (!live) $('offline').hidden = false;
startHello($('hello'));
$('again').onclick = () => sayHello($('hello').querySelector('.tx'));
// a picture that can't be shown (its small copy is still being made) leaves no broken frame
document.querySelectorAll('.now img, .fan img').forEach(im => { const gone = () => { im.remove(); }; if (im.complete && !im.naturalWidth) gone(); else im.addEventListener('error', gone); });
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
// Reload when anything changes (a card goes in, a backup lands, a queue moves).
const STAMP = document.body.dataset.stamp;
if (live) setInterval(async () => { try { const r = await fetch('/home-state', {cache: 'no-store'}); const t = (await r.text()).trim(); if (t && STAMP && t !== STAMP) location.reload(); } catch (e) {} }, 4000);
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
    # 3. the newest post kit, with its photo, and how many kits there are
    k = f.get("newest")
    if k:
        n = f.get("kits") or 0
        boxes.append(_now("", W("n3_newest").format(short=k["short"]), W("n3_kits").format(n=n, s="" if n == 1 else "s"),
                          img=photo_src(k["photo"]) if k.get("photo") else None))
    else:
        boxes.append(_now("", W("n3_none"), W("n3_none_small")))
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
    # Posts first (Nicole, v29 1.2). The ids and the data-item names are the ones the four steps had (s1 backup,
    # s2 queue, s3 posts, s4 posting), so home.py pending, the hello's buttons and the now-boxes read as before.
    # The big card is not itself a press: its button is (a plain link). No list of post kits here, by her ask:
    # "Think about when someone is going to end up having like 20 post kits, 30 post kits."
    kits_btn = W("s3_see") if (f.get("kits") or f.get("newest")) else W("s3_create")
    big = (f"<section class='mk step' id='s3'><span class='n'>{W('s3_n')}</span><p>{e(W('s3_p'))}</p>"
           f"<div class='mk-go'><a class='btn solid big' id='kitsBtn' data-item='posts' href='/make-posts'>{e(kits_btn)}</a>"
           f"<div class='now' id='n3'>{boxes[2]}</div></div></section>")
    posting = (f"<a class='step full' id='s4' data-item='posting' href='/posting.html'><span class='n'>{W('s4_n')}</span><p>{e(W('s4_p'))}</p>"
               f"<div class='now' id='n4'>{boxes[3]}</div><span class='go'>{e(W('s4_go'))}</span></a>")
    also = (f"<div class='also'><h2>{e(W('also_h'))}</h2><div class='also-row'>"
            f"<a class='step sm{live_card}' id='s1' data-item='backup' href='/backups'><span class='n'>{W('s1_n')}</span><p>{e(W('s1_p'))}</p>"
            f"<div class='now' id='n1'>{boxes[0]}</div></a>"
            f"<button class='step sm' id='s2' data-item='queue' type='button'><span class='n'>{W('s2_n')}</span><p>{e(W('s2_p'))}</p>"
            f"<div class='now' id='n2'>{boxes[1]}</div><span id='editingWords' hidden></span></button>"
            f"</div></div>")
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
    # what the hello is made from: names and numbers, as data (never markup, never a path)
    go = {"backup": "/backups", "posting": "/posting.html", "posts": "/make-posts"}
    if f.get("year"):
        go["year"] = "/wrapped.html?y=" + f["year"]["y"]
    hello = {"me": f["me"], "card": f["card"], "queue": [{"name": x["name"], "due_in": x["due_in"]} for x in f["queue"]],
             "posting": {"today": [{"who": x["who"], "kind": x["kind"]} for x in f["posting"]["today"]],
                         "late": [{"who": x["who"], "kind": x["kind"], "days": x["days"]} for x in f["posting"]["late"]],
                         "posted_week": [{"who": x["who"], "kind": x["kind"]} for x in f["posting"]["posted_week"]],
                         "ready": f["posting"]["ready"]},
             "year": f["year"], "collage": f["collage"], "go": go}
    words = dict(home_base.WORDS)
    words.update(home_base.OUR_WORDS)
    words.update({"rc_didnt": W("rc_didnt")})
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(brand.title())}</title><style>{look.head_css()}{CSS_EXTRA}</style></head><body data-stamp='{e(fingerprint())}'>"
            f"<div class='wrap'><div class='bar'>{brand.bar()}"
            f"<span class='when' id='when'>{e(f['today'])}</span>"
            f"<span class='fold'><button class='lnk' id='folder' data-item='folder' type='button'>{e(W('folder').format(short=brand.short()))}</button><span class='note' role='status'></span></span></div>"
            f"<p class='offline' id='offline' hidden>{e(W('offline'))}</p>"
            f"<section class='hello' id='hello'><div class='bgs'></div>"
            f"<button class='again' id='again' type='button' title='{e(W('again_title'), quote=True)}'>{e(W('again'))}</button>"
            f"<div class='tx' aria-live='polite'><h3>{e(W('hello_plain'))}</h3></div></section>"
            f"{big}{posting}{also}"
            f"{recap}{year}<p class='foot'>{foot}</p>"
            f"</div><script type='application/json' id='facts'>{_json_for_script(hello)}</script>"
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
