#!/usr/bin/env python3
"""The Assistant's home page: the home base (Nicole's v26), in the Claude app's browser pane.

What it is, what matters today, then the four steps in the order of the work: Back up a card (its own screen,
/backups), My editing queue, Make posts from a shoot (its own screen, /make-posts), My posting queue; and Open my
Assistant folder as a small card. Nothing else is on it, so it stays clean after years of shoots: every backup
and every post kit is on its step's own screen (home_base.py). Served live by the posting server at /home
(posting_queue.py serve), which also opens folders and pages for its buttons and records which card was pressed.

A click in the pane cannot type into the chat for them, so the two steps that need a conversation show, on their
own screens, what to paste ("backup now", "make my posts") with a Copy button. Every press of a card is kept in
~/.studio/journey.json, so whatever they say next, the assistant already knows what they pressed, whether it is
their first time there, and what they did last time in that category: first time, a short explanation and "want
to dive in?"; later, pick up where they left off.

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
from datetime import datetime, date
from pathlib import Path

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
# The home base (Nicole's v26, Nov 13): what it is, Today, then the four steps in the order of the work, and the
# folder as a small card. Nothing else, so it stays clean after years of shoots: every backup is on the Back up
# a card screen and every post kit on the Make posts screen (home_base.py). Her words are home_base.WORDS.

# The words to paste in the chat for the two steps that start a conversation (shown on their own screens).
SAY = {"backup": home_base.WORDS["b_say"], "posts": home_base.WORDS["m_say"], "setup": "set up my Assistant folder"}

# The four steps: (what a click is recorded as, where it goes, the three lines of words)
STEPS = [
    ("backup", "/backups", "c1_name", "c1_p", "c1_go"),
    ("queue", None, "c2_name", "c2_p", "c2_go"),
    ("posts", "/make-posts", "c3_name", "c3_p", "c3_go"),
    ("posting", "/posting.html", "c4_name", "c4_p", "c4_go"),
]

CSS_EXTRA = home_base.CSS

SCRIPT = r"""
// every card records what was pressed, so the chat knows (journey.json); then it goes where it goes
document.querySelectorAll('.item[data-item]').forEach(b => b.addEventListener('click', () => clicked(b.dataset.item)));
$('editing').onclick = () => assistant('/queue-url', $('editingWords'), W.opening_queue);
$('folder').onclick = () => assistant('/open-home', $('folder').querySelector('p'), W.opening);
document.querySelectorAll('[data-report]').forEach(x => x.onclick = () => assistant('/report-url?id=' + encodeURIComponent(x.dataset.report), x, W.opening_report));
if (!live) $('offline').hidden = false;
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


def today_items(g):
    """Today, in her order: a card that is in, what is late or due soon (and posts to make today), the last
    backup with its report one click away, how many shoots are waiting, the posting queue's line."""
    e = html.escape
    Wd = home_base.W
    items = []
    if g["card"]:
        items.append(("card", e(Wd("t_card").format(name=g["card"]["name"], files=f"{g['card']['files']:,}"))
                      + f" <a class='btn' href='/backups'>{e(Wd('t_card_go'))}</a>"))
    for kind, words in g["notes"][:5]:
        items.append((kind, e(words)))
    lb = g.get("last_backup")
    if lb:
        n = lb["shoots"]
        try:
            import clips
            count = clips.words(lb["photos"], lb.get("clips") or 0)
        except Exception:  # noqa: BLE001
            count = f"{lb['photos']:,} photos"
        items.append(("", e(Wd("t_last").format(day=nice_day(lb["when"]), n=n, s="" if n == 1 else "s", count=count))
                      + f" <button class='btn' data-report='latest'>{e(Wd('see_report'))}</button>"))
    if g.get("waiting"):
        n = g["waiting"]
        items.append(("soon", e(Wd("t_waiting").format(n=n, s="" if n == 1 else "s"))))
    if g["tank"] and not g["tank"].startswith("Nothing ready"):
        items.append(("", e(g["tank"])))
    if not items:
        items.append(("", e(Wd("t_nothing"))))
    return items


def page_html():
    g = gather()
    e = html.escape
    Wd = home_base.W
    today_html = "".join(f"<li class='{k}'><span>{w}</span></li>" for k, w in today_items(g))
    cards = []
    for n, (item, href, name, blurb, go) in enumerate(STEPS, 1):
        go_id = "" if href else " id='editingWords'"
        inner = (f"<span class='k'>{n}</span><span class='n'>{Wd(name)}</span><p>{e(Wd(blurb))}</p>"
                 f"<span class='go'{go_id}>{e(Wd(go))}</span>")
        cards.append(f"<a class='item' data-item='{item}' href='{href}'>{inner}</a>" if href
                     else f"<button class='item' data-item='{item}' id='editing'>{inner}</button>")
    cards.append(f"<button class='item minor' data-item='folder' id='folder'><span class='n'>{Wd('c5_name').format(short=e(brand.short()))}</span>"
                 f"<p>{e(Wd('c5_p'))}</p></button>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(brand.title())}</title><style>{look.head_css()}{CSS_EXTRA}</style></head><body data-stamp='{e(fingerprint())}'>"
            f"<div class='wrap'><div class='bar'>{brand.bar()}"
            f"<span class='when'>{e(g['today'])}</span></div>"
            f"<header class='head'><span class='eyebrow'>{e(Wd('home_eyebrow'))}</span><h1>{Wd('home_h1')}</h1>"
            f"<p class='lede wide'>{e(Wd('home_lede_1'))}</p><p class='lede wide'>{e(Wd('home_lede_2'))}</p>"
            f"<p class='offline' id='offline' hidden>{e(Wd('offline'))}</p></header>"
            f"<section class='sec'><h2>{e(Wd('today'))}</h2><ul class='todayl' id='today'>{today_html}</ul></section>"
            f"<section class='sec'><h2>{e(Wd('flow'))}</h2><div class='flow'>{''.join(cards)}</div></section>"
            f"</div><script>{home_base.words_js()}{home_base.JS_SHARED}{SCRIPT}</script></body></html>")


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
