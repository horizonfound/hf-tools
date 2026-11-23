#!/usr/bin/env python3
"""Your year and the monthly recap, as stories (Nicole's v28, Nov 17; her wrapped.html, built our way).

One page for both, on the posting server:

    /wrapped.html              Your year (the year the Your year bar is about: last year from Jan 1 to 15, else this one)
    /wrapped.html?y=2026       that year
    /wrapped.html?m=2026-11    that month: "Your November, so far." or "recapped."

Each story is drawn on a 1080x1920 canvas, so what is on screen is exactly the picture that gets saved. Her
stories in her order with her words; her controls (tap right / left, hold to pause, the arrow keys, Back / Pause /
Next / Start over); "Save this one to share" and "Save all of them".

Her rule for what goes in (Nicole, Nov 17): "things that someone would want to brag about, not things about the
assistant." So the numbers are the photographer's own work, counted from the records the Assistant already keeps.
NOTHING new is stored; everything here only reads, except a saved story picture.

WHAT EACH NUMBER IS COUNTED FROM (every one a count of records; the only estimate is the time saved):
  reels          the reels made in the period, each reel ONCE, on the day it was first made: each entry of a kit's .kit/reel-page.json "made" list that names a
                 CapCut project or a saved video, by its "when"; a reel made from the chat the older way (kit.json
                 "reel", when the page's list does not know that project), by its "made"; and every talking reel
                 made (.kit/talking.json "made", the open reel's and each other reel's), by its "when".
                 A reel made again (another mix, a fix, a test) is still one reel, and stays in the month of
                 its first make. (COUNT_EACH_MAKE, below, turns that round: every make counts.)
  carousels      the carousel designs slides were saved from (kit.json "laid_out" and "carousel_set": one per
                 design, however often it was saved again), by the day of the first save.
  stories        the same for sets of stories (kit.json "stories_laid_out" and "stories_set").
  posted         the pieces in ~/.studio/posting.json marked posted, by "posted_at"; ready: the ones ready to post.
  shared_shoots  the shoots with at least one piece actually posted in the period (Nicole, Nov 23: "lets only
                 count stuff they actually posted"): each posted piece is traced to its shoot by the post kit
                 folder it was made from (else by the shoot id it carries); the vault is never a shoot; a posted
                 piece that names no shoot at all counts as a post and as no shoot. This is the N of "You shared
                 N shoots with the world". made_shoots is what it counted before: the shoots something was made
                 from in the period, posted or not (the hello's "{n} shoots turned into posts" still reads that).
  shot           photos off their cards: the backups the editing queue knows (home_base.backups: each backup once,
                 wherever its records are now) whose "added" day is in the period, counting the shoots of 10 or
                 more photos; photo_shoots is how many such shoots. With none, the page says "finished photos":
                 the photos in the kits it shows.
  shoots         the kits in Your Content: for a month, the ones something was made from in that month; for a
                 year, those and the ones whose shoot day is in that year. top: the one most was made from.
  weeks_posted   weeks (Monday to Sunday) of the month so far with a post, out of the weeks of the month so far.
  since          the day of the first thing above that ever happened (any year).
  minutes_saved  AN ESTIMATE, hers (MINUTES_SAVED): 45 minutes a reel, 30 a carousel, 20 a set of stories. The
                 page says so beside the stories.

Routes (all on the posting server; the page never sees or sends a path):
    GET  /wrapped.html, /wrapped-data[?m=YYYY-MM | ?y=YYYY], /wrapped-font
    POST /share-image?i=<story 1..9>[&m=YYYY-MM | &y=YYYY]   the body is the PNG itself (image/png, 1080x1920),
                 behind the pickers' same-page-only guard; checked to really be a PNG of that size; the file's
                 name is made here, never taken from the page; saved in "Stories to share" beside Your Content,
                 never over a file that is there (a new name each time).
    POST /share-open {}                                      opens that folder (finder.py, as the neighbours)
The photos on the stories come only through /kit-photo, the route that already serves a kit's small copies.

For the home page (the next builder's): home_answers(today=None, force_year=False) gives, in one read of the
records, the two "should it show" answers: the monthly recap card (which month, "so far." or "recapped.", its
chips and three photos, or None) and the Your year bar (Dec 1 to Jan 15, and only when the first activity was on
or before Jan 31 of that year; force_year is ?wrapped=1, for testing).

    python3 wrapped.py data [--month 2026-11 | --year 2026]    print what /wrapped-data answers (changes nothing)
    python3 wrapped.py home                                     print home_answers()
    python3 wrapped.py url [--month 2026-11 | --year 2026]     the page's address (starts the page server if needed)

Her words are in WORDS and in the stories' own lines (STORIES_JS), whole. Ours, where hers has none, are in
OUR_WORDS, each a draft for Dustin and Nicole. Python 3.9, standard library only; a Mac and a PC alike.
"""
import argparse
import calendar
import html
import json
import os
import re
import unicodedata
import struct
import sys
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import this_computer  # noqa: E402
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
GET_PATHS = ("/wrapped.html", "/wrapped-data", "/wrapped-font")
POST_PATHS = ("/share-image", "/share-open")

MINUTES_SAVED = {"reel": 45, "carousel": 30, "stories": 20}     # hers: about how long each takes by hand. An estimate.
# False (Nicole, v29 2.2, Nov 19): each reel counts once, on the day it was first made. Her November recap said
# 79 reels because every make counted, test makes too; she wants what she actually made. The hours saved follow
# (45 minutes a reel, counted once). True is her v28 way: every make of a reel counts.
COUNT_EACH_MAKE = False
REAL_SHOOT = 10             # hers: a shoot off a card counts when it has this many photos
FAVS = 12                   # hers: up to this many of a shoot's photos are used for the pictures
SHARE_FOLDER = "Stories to share"                               # hers: beside the content folder
PNG_W, PNG_H = 1080, 1920
PNG_CAP = 12 * 1024 * 1024  # a 1080x1920 picture is 8.3 MB before PNG squeezes it; nothing honest is bigger than this
PNG_MIN = 2000
STORIES = 9
ACCENT_SERIF = False        # hers draws the accent words in Fraunces italic; Dustin, Nov 7: no serif. True brings it back
                            # (the plugin's own Fraunces Italic, served by /wrapped-font; nothing from the internet).
SERIF_FILE = "Fraunces-Italic"
YEAR_BAR_FROM, YEAR_BAR_TO = (12, 1), (1, 15)                   # hers: the Your year bar shows Dec 1 to Jan 15
RECAP_LAST_MONTH_DAYS = 7   # hers: in the first 7 days of a month the card shows last month, "recapped."

# ---------- the words ----------
# Nicole's (pages/wrapped.html, v28), whole. {label} is the month's name or the year. Her test-only lines (the
# "Sample · test pages only" eyebrow, the sentence about numbers from testing, the link to the samples page) are
# left out.
WORDS = {
    "wait_year": "Getting your year ready…",
    "wait_month": "Getting your {label} ready…",
    "h1_year": "Your year, <em>wrapped.</em>",
    "h1_month": "Your {label}, <em>{word}</em>",
    "so_far": "so far.",
    "recapped": "recapped.",
    "lede_year": "Your year with the Assistant, story by story, with your real numbers and your own photos. Tap the right side for the next one, the left side to go back, and hold to pause.",
    "lede_month": "Your {label} in photos, reels and posts. Tap the right side for the next one, the left side to go back, and hold to pause.",
    "back": "‹ Back", "pause": "Pause", "play": "Play", "next": "Next ›", "again": "Start over",
    "save_one": "Save this one to share", "save_all": "Save all of them",
    "saving": "Saving…",
    "saving_n": "Saving {i} of {n}…",
    "saved_one": "Saved \"{file}\" in your Assistant folder, under Stories to share.",
    "saved_all": "Saved all {n} in your Assistant folder, under Stories to share.",
    "didnt_save": "That didn't save.",
    "cant_reach": "I can't reach your records right now.",
    "nothing_month": "Nothing from {label} yet.",
    "no_shoots": "No shoots yet. Make posts from a shoot first.",
    "note": "Each one is a 1080×1920 picture, the size of an Instagram story, saved in your Assistant folder under Stories to share.",
    "note_time": "Time saved counts about 45 minutes a reel, 30 a carousel and 20 a set of stories, done by hand.",
    "tap_back": "Back", "tap_next": "Next",
    "not_a_picture": "That isn't a picture.",
}
# Ours, where hers has none. Drafts for Dustin and Nicole.
OUR_WORDS = {
    "eyebrow_year": "Your year",                 # hers: "Sample · test pages only"
    "eyebrow_month": "Monthly recap",            # hers: "Monthly recap · test pages only"
    "title_year": "Your year",
    "title_month": "Your {label}",
    "estimate": "It is an estimate.",            # after her "Time saved counts about..." line
    "open_folder": "Open the folder",            # beside the line that says where a story was saved
    "opened": "Opened Stories to share in {app}.",
    "cant_open": "Could not open the folder. Ask the Assistant to open it.",
    "no_folder": "I can't find your Assistant folder to save into. Is the drive plugged in?",
    "not_set_up": "There's no Assistant folder to save into yet. Say \"set up my Assistant folder\" to the Assistant first.",
    "photos_wait": "Getting your photos ready…",
    "nothing_year": "Nothing from {label} yet.",
    "back_home": "Back to home", "home_short": "Home",
}


def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key]


def say(msg):
    print(msg, flush=True)


def today():
    o = os.environ.get("STUDIO_TODAY")           # for tests, as the queues read it
    return date.fromisoformat(o) if o else date.today()


# ---------- reading the records (read only; one odd record never takes the others with it) ----------

def _json(path):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _day(v):
    """A record's time as a day, "YYYY-MM-DD", or None: seconds since 1970 (the reel page's "when") or an ISO
    text (the queues', the designer's, kit.py's)."""
    try:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)) and 946684800 < v < 4102444800:      # 2000 to 2100
            return datetime.fromtimestamp(v).date().isoformat()
        if isinstance(v, str) and re.match(r"\d{4}-\d\d-\d\d", v):
            return date.fromisoformat(v[:10]).isoformat()
    except (ValueError, OverflowError, OSError):
        pass
    return None


def _made_named(m):
    return isinstance(m, dict) and any(isinstance(m.get(k), str) and m.get(k) for k in ("project", "video"))


def _reel_days(kit, rec_kit):
    """The day of every reel made from this kit (see the top of this file), as [(day, which reel)]."""
    out = []
    page = _json(kit / ".kit" / "reel-page.json")
    known = set()
    for m in page.get("made") if isinstance(page.get("made"), list) else []:
        if not _made_named(m):
            continue
        if isinstance(m.get("project"), str):
            known.add(m["project"])
        d = _day(m.get("when"))
        if d:
            out.append((d, "reel:" + str(m.get("version") or "v1")))
    chat = rec_kit.get("reel") if isinstance(rec_kit.get("reel"), dict) else {}
    if isinstance(chat.get("project"), str) and chat["project"] and chat["project"] not in known:
        d = _day(chat.get("made"))
        if d:
            out.append((d, "reel:v1"))
    talk = _json(kit / ".kit" / "talking.json")
    lists = [(str(talk.get("current") or "v1"), talk.get("made"))]
    for v in talk.get("versions") if isinstance(talk.get("versions"), list) else []:
        if isinstance(v, dict) and isinstance(v.get("data"), dict) and v.get("id") != talk.get("current"):
            lists.append((str(v.get("id")), v["data"].get("made")))
    for vid, made in lists:
        for m in made if isinstance(made, list) else []:
            if isinstance(m, dict) and isinstance(m.get("project"), str) and m["project"]:
                d = _day(m.get("when"))
                if d:
                    out.append((d, "talk:" + vid))
    if not COUNT_EACH_MAKE:
        first = {}
        for d, which in out:
            first[which] = min(d, first.get(which, d))
        out = [(d, which) for which, d in first.items()]
    return sorted(d for d, _ in out)


def _set_days(rec_kit, all_key, set_key):
    """The day slides were first saved from each design: one per design."""
    sets = [x for x in (rec_kit.get(all_key) if isinstance(rec_kit.get(all_key), list) else []) if isinstance(x, dict)]
    cs = rec_kit.get(set_key)
    if isinstance(cs, dict) and cs.get("kind") == "laid-out":
        sets.append(cs)
    first = {}
    for x in sets:
        d, did = _day(x.get("saved")), str(x.get("design") or x.get("base") or "")
        if d and did:
            first[did] = min(d, first.get(did, d))
    return sorted(first.values())


def _favs(kit, rec_kit):
    """Up to FAVS of the kit's photos, by their numbers on the kit's list: the reel's order on its page, else the
    assistant's pick for the reel, else the first ones. Only numbers that are on the list."""
    import arrange
    on_list = [r["n"] for r in arrange.sheet_rows(kit)]
    have = set(on_list)
    page = _json(kit / ".kit" / "reel-page.json")
    saved = page.get("saved") if isinstance(page.get("saved"), dict) else {}
    picks = [p.get("n") for p in (saved.get("picks") if isinstance(saved.get("picks"), list) else []) if isinstance(p, dict)]
    picks = [n for n in picks if type(n) is int and n in have]
    if not picks:
        try:
            picks = [n for n in arrange.kit_pick(rec_kit, "reel")[0] if n in have]
        except (TypeError, AttributeError, ValueError):
            picks = []
    out = []
    for n in picks or on_list:
        if n not in out:
            out.append(n)
    return out[:FAVS]


def _kits():
    """Every kit in Your Content, with the days things were made from it."""
    import posts
    import kit as kit_mod
    out = []
    try:
        h = posts.home()
        listed = posts.kits(h, vault=True) if h else []      # the vault too: what was made in it counts; it is never a shoot
    except (Exception, SystemExit):  # noqa: BLE001
        listed = []
    for k in listed:
        try:
            d = Path(k["path"])
            if d.is_symlink() or not (d / ".kit" / "kit.json").is_file():
                continue
            rec = _json(d / ".kit" / "kit.json")
            is_vault = rec.get("vault") is True
            try:                        # the vault's photos are the shoots' own: counted there, never twice
                photos = 0 if is_vault else len(kit_mod.photo_files(kit_mod.photos_dir(d)))
            except (Exception, SystemExit):  # noqa: BLE001
                photos = 0
            day = "" if is_vault else (_day(k.get("date")) or _day(k["folder"]) or "")
            out.append({"folder": k["folder"], "short": look.short_name(k["folder"]) or k["folder"], "date": day, "photos": photos,
                        "vault": is_vault,
                        "reel_days": _reel_days(d, rec), "carousel_days": _set_days(rec, "laid_out", "carousel_set"),
                        "story_days": _set_days(rec, "stories_laid_out", "stories_set"), "favs": _favs(d, rec), "path": d})
        except (Exception, SystemExit):  # noqa: BLE001
            continue
    return out


def _slug(text):
    """A kit's short id, as the posting queue makes it (posting_queue.slug: kept the same here, by a test)."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40]


def _piece_shoot(p):
    """Which shoot a posted piece is from: (the post kit folder's NAME or "", its shoot id or ""), or None when
    the piece names no shoot. Never a path: only the last part of the folder it was made from."""
    was, sid = p.get("kit"), p.get("shoot_id")
    name = ""
    if isinstance(was, str) and was.strip("\\/ "):
        name = unicodedata.normalize("NFC", re.split(r"[\\/]", was.rstrip("\\/ "))[-1])
    sid = sid.strip() if isinstance(sid, str) else ""
    return (name, sid) if (name or sid) else None


def _posting():
    """(the days of the posts marked posted, how many are ready, and for each posted piece (day, its shoot))."""
    pieces = _json(HOME / "posting.json").get("pieces")
    pieces = [p for p in (pieces if isinstance(pieces, list) else []) if isinstance(p, dict)]
    done = sorted(((d, _piece_shoot(p)) for d, p in ((_day(p.get("posted_at")), p) for p in pieces if p.get("status") == "posted") if d),
                  key=lambda x: x[0])
    return [d for d, _ in done], sum(1 for p in pieces if p.get("status") == "green"), done


def _backups():
    """[(the day a backup was added, [how many photos in each of its shoots])] for every backup the editing queue
    knows, each backup once."""
    out = []
    try:
        import home_base
        for g in home_base.backups():
            for b in g.get("backups") or []:
                d = _day(b.get("added"))
                if d:
                    out.append((d, [s["count"] for s in b.get("shoots") or [] if isinstance(s.get("count"), int)]))
    except (Exception, SystemExit):  # noqa: BLE001  (an unreadable queue: no backups counted, the rest still shows)
        pass
    return out


def _who():
    """(their first name, their Instagram handle) from their Brand Homebase, hers; the handle else from the grid
    they had read. Either may be ""."""
    me = handle = ""
    try:
        import words
        hb = words.homebase()
        text = Path(hb).read_text(encoding="utf-8") if hb else ""
    except (Exception, SystemExit):  # noqa: BLE001
        text = ""
    for ln in text.splitlines():
        m = re.match(r"\s*-\s*Name\s*/\s*business:\s*([A-Za-zÀ-ɏ'-]+)", ln)
        if m:
            me = m.group(1)
            break
    m = re.search(r"Instagram:\s*(@[\w.]+?)\.?(\s|$)", text)
    if m:
        handle = m.group(1)
    if not handle:
        h = _json(HOME / "feed.json").get("handle")
        if isinstance(h, str) and re.fullmatch(r"[\w.]{1,40}", h.lstrip("@")):
            handle = "@" + h.lstrip("@")
    return me, handle


def gather():
    """Everything the counts are made from, read once."""
    kits = _kits()
    posted, ready, posted_from = _posting()
    backups = _backups()
    days = list(posted) + [d for d, _ in backups]
    for k in kits:
        days += k["reel_days"] + k["carousel_days"] + k["story_days"]
    me, handle = _who()
    return {"kits": kits, "posted": posted, "posted_from": posted_from, "ready": ready, "backups": backups, "since": min(days) if days else "",
            "me": me, "handle": handle}


# ---------- the counts ----------

def month_ok(m):
    return isinstance(m, str) and bool(re.fullmatch(r"(20\d\d)-(0[1-9]|1[0-2])", m))


def year_ok(y):
    return isinstance(y, str) and bool(re.fullmatch(r"20\d\d", y))


def default_year(day=None):
    """The year Your year is about: the one that just ended, from Jan 1 to 15 (while its bar still shows)."""
    day = day or today()
    return day.year - 1 if (day.month, day.day) <= YEAR_BAR_TO else day.year


def data(month=None, year=None, got=None, day=None):
    """What /wrapped-data answers: hers, field for field (ok, me, handle, year, month, label, next, shoots,
    totals, minutes_each, since, top), for one month ("2026-11") or one year. Names and numbers, never a path.
    Ours beside hers: so_far (is it the month we are in: decided here, by this computer's day), and making
    (small copies of the photos are still being made)."""
    day = day or today()
    got = got or gather()
    month = month if month_ok(month) else None
    year = (month[:4] if month else year if year_ok(str(year or "")) else str(default_year(day)))
    year = str(year)
    inside = (lambda d: d[:7] == month) if month else (lambda d: d[:4] == year)
    shoots, in_vault = [], []           # the vault (v29) is not a shoot: what was made in it counts, and that is all
    for k in got["kits"]:
        s = {"name": k["folder"], "short": k["short"], "photos": k["photos"], "date": k["date"], "favs": k["favs"],
             "reels": sum(1 for d in k["reel_days"] if inside(d)), "carousels": sum(1 for d in k["carousel_days"] if inside(d)),
             "stories": sum(1 for d in k["story_days"] if inside(d)), "shot_here": bool(k["date"]) and inside(k["date"])}
        (in_vault if k.get("vault") else shoots).append(s)
    made = lambda s: s["reels"] + s["carousels"] + s["stories"]  # noqa: E731
    worked = [s for s in shoots if made(s)]
    # a month shows the shoots something was made from that month; a year, those and the ones shot that year
    shown = worked if month else [s for s in shoots if made(s) or s["shot_here"]]
    posted = [d for d in got["posted"] if inside(d)]
    shared = _shared(got, inside, shoots)       # the shoots with a piece actually posted in the period
    for s in shoots:
        s["shared"] = s["name"] in shared["kits"]
    shot = photo_shoots = 0
    for d, counts in got["backups"]:
        if inside(d):
            for n in counts:
                if n >= REAL_SHOOT:
                    shot += n
                    photo_shoots += 1
    if not month:                       # hers: the year also counts the finished shoots in Your Content
        photo_shoots = max(photo_shoots, len(shown))
    weeks = weeks_posted = 0
    if month:
        y, m = int(month[:4]), int(month[5:])
        d0 = date(y, m, 1)
        end = min(day, date(y, m, calendar.monthrange(y, m)[1]))
        wk = {(d0 + timedelta(days=i)).isocalendar()[:2] for i in range((end - d0).days + 1)}
        weeks = len(wk)
        weeks_posted = len(wk & {date.fromisoformat(p).isocalendar()[:2] for p in posted})
    tot = {"photos": sum(s["photos"] for s in shown), "shot": shot, "photo_shoots": photo_shoots,
           "shared_shoots": shared["n"], "made_shoots": len(worked), "reels": sum(s["reels"] for s in shoots + in_vault),
           "carousels": sum(s["carousels"] for s in shoots + in_vault),
           "stories": sum(s["stories"] for s in shoots + in_vault), "posted": len(posted), "posted_days": len(set(posted)),
           "weeks_posted": weeks_posted, "weeks": weeks, "ready": got["ready"]}
    tot["minutes_saved"] = (tot["reels"] * MINUTES_SAVED["reel"] + tot["carousels"] * MINUTES_SAVED["carousel"]
                            + tot["stories"] * MINUTES_SAVED["stories"])
    top = max(worked, key=made, default=None)
    if month:
        label = calendar.month_name[int(month[5:])]
        nxt = calendar.month_name[int(month[5:]) % 12 + 1]
    else:
        label, nxt = year, "next year"
    anything = bool(tot["reels"] or tot["carousels"] or tot["stories"] or tot["posted"] or tot["shot"])
    # a shoot posted this period that nothing was made from this period (made last month, posted this one) is
    # shown too, after the others, so the "You shared" story has its photo; the photo count stays as it was
    listed = shown + [s for s in shoots if s["shared"] and s not in shown]
    return {"ok": True, "me": got["me"], "handle": got["handle"], "year": year, "month": month or "", "label": label,
            "next": nxt, "shoots": listed or (shoots if anything else []), "totals": tot, "minutes_each": dict(MINUTES_SAVED),
            "since": got["since"], "top": top["name"] if top else "", "anything": anything,
            "so_far": bool(month) and month == day.isoformat()[:7]}


def _shared(got, inside, shoots):
    """The shoots with at least one piece posted in the period (Nicole, Nov 23): {"n": how many, "kits": the names
    of the post kits among them}. A piece is its kit's by the folder it was made from, or (a piece from before the
    folder was written down) by the short id the posting queue gave that kit; a posted piece from a shoot with no
    post kit here (an older route, a kit on a drive that is unplugged) is still one shoot, by what it carries; a
    piece made in the vault, or one that names no shoot, is no shoot."""
    by_name = {unicodedata.normalize("NFC", k["folder"]): k for k in got["kits"]}
    by_id = {}
    for k in got["kits"]:
        by_id.setdefault("kit:" + _slug(k["folder"]), k)
    names = {s["name"] for s in shoots}
    kits, others = set(), set()
    for d, who in got.get("posted_from") or []:
        if not who or not inside(d):
            continue
        name, sid = who
        k = by_name.get(name) if name else by_id.get(sid)
        if k is None:
            others.add(sid or name)
        elif not k.get("vault") and k["folder"] in names:
            kits.add(k["folder"])
    return {"n": len(kits) + len(others), "kits": kits}


def chips(tot):
    """The monthly recap card's chips, hers ("231 photos · 79 reels · 8 carousels · 3 posts · 69 hours saved"), as a
    list; a number that is zero has no chip."""
    def n(v, one, many=None):
        return f"{v:,} {one if v == 1 else (many or one + 's')}"
    out = []
    photos = tot["shot"] or tot["photos"]
    if photos:
        out.append(n(photos, "photo"))
    if tot["reels"]:
        out.append(n(tot["reels"], "reel"))
    if tot["carousels"]:
        out.append(n(tot["carousels"], "carousel"))
    if tot["posted"]:
        out.append(n(tot["posted"], "post"))
    mins = tot["minutes_saved"]
    if mins >= 120:
        out.append(n(round(mins / 60), "hour") + " saved")
    elif mins:
        out.append(n(mins, "minute") + " saved")
    return out


def page_path(month=None, year=None):
    return "/wrapped.html" + (f"?m={month}" if month else f"?y={year}" if year else "")


def home_answers(day=None, force_year=False, got=None):
    """For the home page, in one read of the records: {"recap": the monthly recap card or None, "year": the Your
    year bar or None}.
      recap  hers: in the first 7 days of a month, last month, "recapped.", if last month had anything in it;
             otherwise this month, "so far."; nothing to show, no card. {month, label, word, chips, totals,
             photos: up to three [{kit, n}] for /kit-photo, url}
      year   hers: only from Dec 1 to Jan 15, and only when their first activity was on or before Jan 31 of that
             year; force_year (?wrapped=1) shows it any time. {year, url}
    Whether they hid the card is the home page's to remember (with their settings), not asked here."""
    day = day or today()
    got = got or gather()
    recap = None
    months = []
    if day.day <= RECAP_LAST_MONTH_DAYS:
        last = (day.replace(day=1) - timedelta(days=1)).isoformat()[:7]
        months.append((last, W("recapped")))
    months.append((day.isoformat()[:7], W("so_far")))
    for m, word in months:
        d = data(month=m, got=got, day=day)
        if d["anything"]:
            photos = []                              # three of the month's photos, a different shoot each where there are several
            for k in range(3):
                photos += [{"kit": s["name"], "n": s["favs"][k]} for s in d["shoots"] if len(s["favs"]) > k]
            recap = {"month": m, "label": d["label"], "word": word, "chips": chips(d["totals"]), "totals": d["totals"],
                     "photos": photos[:3], "url": page_path(month=m)}
            break
    y = default_year(day)
    in_window = (day.month, day.day) >= YEAR_BAR_FROM or (day.month, day.day) <= YEAR_BAR_TO
    since = got["since"]
    year = None
    if force_year or (in_window and since and since <= f"{y}-01-31"):
        year = {"year": str(y), "url": page_path(year=str(y))}
    return {"recap": recap, "year": year, "since": since}


# ---------- saving a story as a picture ----------

def png_ok(b):
    """Is this really a PNG picture, 1080x1920, whole and nothing else? Every chunk walked and its checksum
    checked: the signature, IHDR first (the size, 8 bits, colour or colour with see-through), picture data, IEND
    last with nothing after it."""
    if not isinstance(b, (bytes, bytearray)) or not PNG_MIN <= len(b) <= PNG_CAP or b[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    at, first, seen_data = 8, True, False
    while at + 12 <= len(b):
        n, kind = struct.unpack(">I4s", b[at:at + 8])
        end = at + 12 + n
        if end > len(b) or zlib.crc32(b[at + 4:at + 8 + n]) & 0xFFFFFFFF != struct.unpack(">I", b[end - 4:end])[0]:
            return False
        if first:
            if kind != b"IHDR" or n != 13:
                return False
            w, h, depth, colour = struct.unpack(">IIBB", b[at + 8:at + 18])
            if (w, h) != (PNG_W, PNG_H) or depth != 8 or colour not in (2, 6):
                return False
            first = False
        elif kind == b"IDAT":
            seen_data = True
        elif kind == b"IEND":
            return seen_data and n == 0 and end == len(b)
        at = end
    return False


def share_folder():
    """(the folder story pictures go in, None) or (None, why in plain words). "Stories to share" beside Your
    Content, in the Assistant's folder. Made here when it is not there yet."""
    try:
        import posts
        h = posts.home()
    except (Exception, SystemExit):  # noqa: BLE001
        h = None
    if not h:
        return None, W("not_set_up")
    try:
        if not Path(h).is_dir():
            return None, W("no_folder")
        f = Path(h) / SHARE_FOLDER
        if f.is_symlink() or (f.exists() and not f.is_dir()):
            return None, W("no_folder")
        f.mkdir(exist_ok=True)
        return f, None
    except OSError:
        return None, W("no_folder")


def share_name(i, month=None, year=None, day=None):
    """The picture's name, made here (hers, built by her page): "My November 2026 recap - 3 2026-11-17" or
    "My 2026 with The Assistant - 3 2026-11-17". Letters, digits, spaces and hyphens only."""
    day = day or today()
    if month:
        base = f"My {calendar.month_name[int(month[5:])]} {month[:4]} recap - {i}"
    else:
        base = f"My {year} with {brand.PRODUCT} - {i}"
    base = re.sub(r"[^\w ,.'-]+", "", base)[:60].strip() or "Story"
    return f"{base} {day.isoformat()}"


def save_picture(png, i, month=None, year=None):
    """Save one story's picture. (True, its file name) or (False, plain words). Never over a file: the name is
    taken only when no file has it (made with "x", so two saves at once can't share one), else "... 2", "... 3"."""
    if not png_ok(png):
        return False, W("not_a_picture")
    folder, why = share_folder()
    if not folder:
        return False, why
    base = share_name(i, month, year)
    for k in range(1, 1000):
        f = folder / (base + ("" if k == 1 else f" {k}") + ".png")
        try:
            fh = open(f, "xb")
        except FileExistsError:
            continue
        except OSError:
            return False, W("didnt_save")
        try:
            with fh:
                fh.write(png)
        except OSError:
            try:
                f.unlink()                  # only the file just made here, half written; never one that was there
            except OSError:
                pass
            return False, W("didnt_save")
        return True, f.name
    return False, W("didnt_save")


def open_share_folder():
    import reel_page
    folder, why = share_folder()
    if not folder:
        return {"ok": False, "words": why}
    ok, note = reel_page._open_folder(folder)
    if not ok:
        _log(f"the Stories to share folder couldn't be opened: {str(note)[:200]}")
        return {"ok": False, "words": W("cant_open")}
    said = W("opened").replace("{app}", this_computer.FILES_APP)
    if note == "behind":
        said = said[:-1] + reel_page.OUR_WORDS["behind"]
    return {"ok": True, "words": said}


# ---------- the routes ----------

def _log(msg):
    try:
        import arrange
        arrange.log("wrapped: " + msg)
    except (Exception, SystemExit):  # noqa: BLE001
        pass


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _send(handler, body, ctype, code=200, cache="no-store"):
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache)
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def _answer(handler, obj, code=200):
    _send(handler, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", code)


def _period(q):
    """(month, year) from an address's ?m= / ?y=; (None, None) for neither; False for one that is not a month or a year."""
    m, y = q.get("m") or [], q.get("y") or []
    if len(m) > 1 or len(y) > 1 or (m and y):
        return False
    if m:
        return (m[0], None) if month_ok(m[0]) else False
    if y:
        return (None, y[0]) if year_ok(y[0]) else False
    return (None, None)


def _photos_ready(d):
    """Are the small copies the stories draw from made? Starts making them (in the background, as the words page
    does) for a shoot that lacks one. True when nothing is missing."""
    import arrange
    import kit as kit_mod
    ready = True
    for s in d["shoots"]:
        kit = arrange.kit_by_name(s["name"])
        if kit is None or not s["favs"]:
            continue
        try:
            rows = {r["n"]: r for r in arrange.sheet_rows(kit)}
            rec = kit_mod.load_rec(kit)
            missing = any(n in rows and arrange.copy_to_serve(kit, rec, rows[n], arrange.SIZES["s"]) is None for n in s["favs"])
            if s["name"] == d["top"] and s["favs"][0] in rows:
                missing = missing or arrange.copy_to_serve(kit, rec, rows[s["favs"][0]], arrange.SIZES["l"]) is None
            if missing:
                if arrange.cant_make(kit, list(rows.values())):
                    continue                         # these can't be made (the photos are away): the stories draw without
                ready = False
                arrange.start_previews(kit)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            _log(f"the small copies couldn't be started ({e.__class__.__name__})")
    return ready


def handle_get(handler, path, query):
    """Every GET for Your year and the monthly recap. Whatever goes wrong, the server answers and stays up."""
    try:
        import arrange
        if not arrange.our_host(handler):
            return handler.send_error(403)
        try:
            q = parse_qs(query or "", keep_blank_values=True)
        except ValueError:
            return handler.send_error(404)
        if path == "/wrapped-font":
            if not ACCENT_SERIF or q:
                return handler.send_error(404)
            try:
                return _send(handler, (look.FONT_DIR / (SERIF_FILE + ".ttf")).read_bytes(), "font/ttf", cache="private, max-age=604800")
            except OSError:
                return handler.send_error(404)
        per = _period(q)
        if path == "/wrapped.html":
            month, year = per if per else (None, None)
            return _send(handler, page_html(month, year).encode("utf-8"), "text/html; charset=utf-8")
        if path == "/wrapped-data":
            if _cross_site(handler):                 # the numbers are for the page only
                return _answer(handler, {"ok": False}, 403)
            if per is False:
                return _answer(handler, {"ok": False}, 404)
            d = data(month=per[0], year=per[1])
            d["making"] = not _photos_ready(d)
            return _answer(handler, d)
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            if path.endswith(".html"):
                handler.send_error(500)
            else:
                _answer(handler, {"ok": False}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _post_image(handler, query):
    import arrange
    try:
        handler.connection.settimeout(arrange.BODY_WAIT)
    except (OSError, AttributeError):
        pass
    bad = arrange.guard(handler, "image/png", PNG_CAP, "/share-image")
    if bad is None and _cross_site(handler):
        bad = (403, arrange.NOT_UNDERSTOOD)
    if bad:
        arrange._drain(handler)
        return _answer(handler, {"ok": False, "words": bad[1]}, bad[0])
    png = handler.rfile.read(int(handler.headers.get("Content-Length").strip()))
    try:
        q = parse_qs(query or "", keep_blank_values=True)
    except ValueError:
        q = {}
    per = _period(q)
    i = q.get("i") or []
    if per is False or len(i) != 1 or not re.fullmatch(r"[1-9]", i[0]) or int(i[0]) > STORIES or set(q) - {"m", "y", "i"}:
        return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
    month, year = per
    ok, said = save_picture(png, int(i[0]), month, year or str(default_year()))
    if not ok:
        return _answer(handler, {"ok": False, "words": said}, 400 if said == W("not_a_picture") else 200)
    return _answer(handler, {"ok": True, "file": said})


def handle_post(handler, path, query):
    """POST /share-image and /share-open, behind the pickers' guard. Whatever goes wrong, the server answers and
    stays up."""
    try:
        import arrange
        if path == "/share-image":
            return _post_image(handler, query)
        if path == "/share-open":
            import reel_page
            if _cross_site(handler):
                arrange._drain(handler)
                return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 403)
            body = reel_page._json_body(handler, path)
            if body is None:
                return
            if body:
                return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
            return _answer(handler, open_share_folder())
        return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _answer(handler, {"ok": False, "words": W("didnt_save")}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


# ---------- the page ----------
# Her stylesheet (pages/wrapped.html, v28) as she wrote it, with these changes: the Google Fonts link is gone (the
# plugin's own DM Sans, look.py); her colour names come from look.py; the accent word in the heading is the look's
# (upright, coral: no serif, Dustin, Nov 7); the bar on top (Back to home) and the Open the folder button are ours.
CSS = r"""
html,body{height:100%}
body{background:#121318;color:#fff;font:400 15px/1.5 var(--sans)}
.top{position:absolute;left:20px;top:16px;z-index:5}
.top .homelink{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18)}
.top .homelink .short{display:none}
@media (max-width:640px){.top{position:static;padding:14px 20px 0}.top .homelink .long{display:none}.top .homelink .short{display:inline}}
.page{min-height:100%;display:flex;align-items:center;justify-content:center;gap:clamp(18px,4vw,48px);padding:20px;flex-wrap:wrap}
.phone{position:relative;height:min(92vh,880px);aspect-ratio:9/16;border-radius:28px;overflow:hidden;background:#000;box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.08);touch-action:none;user-select:none;-webkit-user-select:none}
@media (max-width:640px){.phone{height:auto;width:min(100%,420px)}}
canvas{width:100%;height:100%;display:block}
.bars{position:absolute;left:12px;right:12px;top:12px;display:flex;gap:5px;z-index:3;pointer-events:none}
.bars i{flex:1;height:3px;border-radius:2px;background:rgba(255,255,255,.35);overflow:hidden}
.bars i b{display:block;height:100%;width:0;background:#fff}
.tap{position:absolute;top:0;bottom:0;z-index:2;cursor:pointer}.tap.l{left:0;width:33%}.tap.r{right:0;width:67%}
.wait{position:absolute;inset:0;display:grid;place-items:center;z-index:4;color:#ddd;font-size:15px;background:#1F2430;padding:20px;text-align:center}
.wait[hidden]{display:none}
.side{width:min(330px,100%);display:grid;gap:14px;align-content:start}
.side .eyebrow{color:var(--coral)}
h1{margin:0;font:600 34px/1.05 var(--sans);letter-spacing:-.03em}h1 em{color:var(--coral)}
.side p{margin:0;color:#b9bcc6;font-size:14.5px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.btn{border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:#fff;border-radius:999px;padding:.6rem 1rem;font:600 13.5px/1 var(--sans);cursor:pointer}
.btn:hover{background:rgba(255,255,255,.14)}.btn.main{background:var(--coral);border-color:var(--coral);color:#1F2430}.btn.main:hover{background:#ff9472}
.btn[disabled]{opacity:.45;cursor:default}
.btn[hidden]{display:none}
.said{font-size:13.5px;color:#d6d8de;min-height:1.2em;overflow-wrap:anywhere}
.side .note{font-size:12.5px;color:#8b8f9b;border-top:1px solid rgba(255,255,255,.1);padding-top:12px}
"""

# The stories and the player: hers (pages/wrapped.html), with these changes, each named where it is.
#   * photos come through /kit-photo (the kit's small copies, by number), never an address with a folder in it
#   * the picture is sent as itself (image/png), not as text inside JSON, and its name is made by the server
#   * "You shared N shoots with the world" counts only shoots with a piece actually posted in the month (Nicole,
#     Nov 23), and its photos are those shoots'
#   * a story with nothing to brag about is left out (hers showed "You shared 0 shoots", a top shoot nothing was
#     made from, "0 reels made"); one of a thing is "1 reel", never "1 reels"
#   * "so far." or "recapped." is the server's answer (hers asked the browser's clock in London time)
#   * under prefers-reduced-motion every story is shown finished, with nothing moving
#   * no serif unless ACCENT_SERIF
STORIES_JS = r"""
const $ = id => document.getElementById(id);
const W = 1080, H = 1920, cv = $('cv');
let ctx = cv.getContext('2d');     // swapped for a spare canvas while a story is saved
const C = {coral: '#F07F5A', coral2: '#D4643F', ink: '#1F2430', cream: '#FAF6EF', lilac: '#E9E4FB', green: '#2F7D56', white: '#FFFFFF', grey: '#A7ABB6'};
const SANS = "'Assistant Sans','Helvetica Neue',Arial,sans-serif", SERIF = "'Assistant Serif',Georgia,serif";
const STILL = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = t => 1 - Math.pow(1 - cl(t), 3);
const back = t => { t = cl(t); const c = 1.6; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const win = (t, a, b) => cl((t - a) / (b - a));
const enc = encodeURIComponent;
const src = (kit, n, size) => '/kit-photo?kit=' + enc(kit) + '&n=' + n + '&size=' + (size || 's');
const pl = (n, one, many) => n === 1 ? one : (many || one + 's');
let D = null, POOL = [], HERO = null, S = [];
const IMG = new Map();
function load(u){ if (IMG.has(u)) return IMG.get(u); const p = new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = u; }); IMG.set(u, p); return p; }
const got = new Map();      // address -> Image, once loaded
function rr(x, y, w, h, r){ ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
function photo(u, x, y, w, h, o = {}){
  const im = got.get(u); ctx.save();
  if (o.rot || o.scale) { ctx.translate(x + w / 2, y + h / 2); ctx.rotate(o.rot || 0); const s = o.scale == null ? 1 : o.scale; ctx.scale(s, s); x = -w / 2; y = -h / 2; }
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  if (o.shadow) { ctx.shadowColor = 'rgba(0,0,0,.35)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 18; }
  if (o.frame) { ctx.fillStyle = '#fff'; rr(x - o.frame, y - o.frame, w + 2 * o.frame, h + 2 * o.frame + (o.foot || 0), 10); ctx.fill(); ctx.shadowColor = 'transparent'; }
  rr(x, y, w, h, o.r == null ? 18 : o.r); ctx.save(); ctx.clip();
  if (im) { const z = o.zoom || 1, s = Math.max(w / im.width, h / im.height) * z, iw = im.width * s, ih = im.height * s;
    ctx.drawImage(im, x + (w - iw) / 2 + (o.dx || 0), y + (h - ih) / 2 + (o.dy || 0), iw, ih); }
  else { ctx.fillStyle = 'rgba(128,128,128,.3)'; ctx.fillRect(x, y, w, h); }
  ctx.restore(); ctx.restore();
}
function text(s, x, y, o = {}){
  ctx.save(); ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
  let size = o.size || 60, italic = o.italic, weight = o.weight || 700, fam = o.serif ? SERIF : SANS;
  if (o.serif && !CFG.serif) { italic = false; weight = 600; fam = SANS; size = Math.round(size * .9); }   // no serif: the accent word upright, in its colour
  ctx.font = `${italic ? 'italic ' : ''}${weight} ${size}px ${fam}`;
  ctx.fillStyle = o.color || '#fff'; ctx.textAlign = o.align || 'center'; ctx.textBaseline = 'alphabetic';
  if (o.ls && 'letterSpacing' in ctx) ctx.letterSpacing = o.ls + 'px';
  const lines = []; let line = '';
  for (const w of String(s).split(' ')) { const t = line ? line + ' ' + w : w; if (o.max && ctx.measureText(t).width > o.max && line) { lines.push(line); line = w; } else line = t; }
  lines.push(line);
  const lh = size * (o.lh || 1.12);
  lines.forEach((l, k) => ctx.fillText(l, x, y + k * lh + (o.dy || 0)));
  ctx.restore(); return lines.length * lh;
}
const num = n => Math.round(n).toLocaleString('en-US');
function foot(t, dark){ text(`${D.handle || 'Your ' + D.label} · ${CFG.product}`, W / 2, H - 70, {size: 34, weight: 600, color: dark ? 'rgba(31,36,48,.55)' : 'rgba(255,255,255,.6)', alpha: win(t, .2, .8)}); }
function bg(c){ ctx.fillStyle = c; ctx.fillRect(0, 0, W, H); }
function rng(seed){ let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const pick = (k) => POOL[((k % POOL.length) + POOL.length) % POOL.length];
const topShoot = () => D.shoots.find(x => x.name === D.top) || null;

/* ---------- the stories ---------- */
const ALL = [
  {dur: 5.5, draw(t){   // 1: your year in photos
    bg(C.ink);
    const cols = 4, tw = 300, th = 375, gap = 18, x0 = (W - (cols * tw + (cols - 1) * gap)) / 2;
    for (let c = 0; c < cols; c++) {
      const dir = c % 2 ? 1 : -1, off = ((t * 38 * dir) % (th + gap) + (th + gap)) % (th + gap);
      for (let r = -2; r < 7; r++) photo(pick(c * 9 + r + 20), x0 + c * (tw + gap), r * (th + gap) + off - 60, tw, th, {r: 16, alpha: .55 * ease(win(t, 0, 1.2))});
    }
    const g = ctx.createLinearGradient(0, 500, 0, 1450); g.addColorStop(0, 'rgba(31,36,48,0)'); g.addColorStop(.35, 'rgba(31,36,48,.88)'); g.addColorStop(.65, 'rgba(31,36,48,.88)'); g.addColorStop(1, 'rgba(31,36,48,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 500, W, 950);
    const a = ease(win(t, .4, 1.4)), b = ease(win(t, .9, 1.9)), c2 = ease(win(t, 1.4, 2.4));
    text(`${D.me || 'Hi'},`, W / 2, 840 - 40 * (1 - a), {size: 150, serif: true, italic: true, weight: 400, color: C.coral, alpha: a});
    text(`your ${D.label}`, W / 2, 1000 - 40 * (1 - b), {size: D.label.length > 7 ? 124 : 140, weight: 800, alpha: b, ls: -3});
    text('in photos.', W / 2, 1140 - 40 * (1 - c2), {size: 140, weight: 800, alpha: c2, ls: -3});
  }},
  {dur: 5.5, when: () => (D.totals.shot || D.totals.photos) > 0, draw(t){   // 2: the photos
    bg(C.coral);
    const R = rng(7);
    for (let k = 0; k < 16; k++) {
      const x = 60 + R() * (W - 380), yEnd = 1100 + R() * 300, rot = (R() - .5) * .5, at = .3 + k * .14;
      const p = ease(win(t, at, at + .9)); if (p <= 0) continue;
      photo(pick(k), x, -500 + (yEnd + 500) * p, 300, 375, {rot: rot * p, frame: 14, foot: 26, shadow: true, r: 4});
    }
    const T = D.totals, took = T.shot > 0, full = took ? T.shot : T.photos, n = full * ease(win(t, .2, 2.2)), ps = T.photo_shoots;
    text(num(n), W / 2, 760, {size: 300, weight: 900, color: C.white, ls: -12});
    text(took ? pl(full, 'photo taken', 'photos taken') : pl(full, 'finished photo', 'finished photos'), W / 2, 880, {size: 76, weight: 700, color: C.ink, alpha: ease(win(t, .6, 1.4))});
    if (ps) text(`at ${ps} photo ${pl(ps, 'shoot')}`, W / 2, 970, {size: 50, weight: 500, color: C.ink, alpha: ease(win(t, 1.2, 2)), max: 980});
    foot(t, true);
  }},
  {dur: 6, when: () => (D.month ? D.totals.shared_shoots : D.totals.photo_shoots) > 0, draw(t){     // 3: the shoots
    bg(C.cream);
    const yr = !D.month, ns = yr ? D.totals.photo_shoots : D.totals.shared_shoots;
    text(yr ? 'You had' : 'You shared', W / 2, 200, {size: 64, weight: 700, color: C.ink, alpha: ease(win(t, 0, .6))});
    text(`${ns} ${pl(ns, yr ? 'photo shoot' : 'shoot')}`, W / 2, 360, {size: ns > 9 ? 150 : 170, weight: 900, color: C.ink, ls: -7, alpha: ease(win(t, .2, 1))});
    text(yr ? (ns === 1 ? 'and it counted' : 'and every one of them counted') : 'with the world', W / 2, 470, {size: 80, serif: true, italic: true, weight: 400, color: C.coral2, alpha: ease(win(t, .5, 1.3)), max: 980});
    // a month: the photos are of the shoots that were posted (Nicole, Nov 23), never of one that was only made from
    const sh = (yr ? D.shoots : D.shoots.filter(s => s.shared)).slice(0, 3), spots = [[90, 600, -.05], [570, 780, .05], [130, 1250, -.03]];
    sh.forEach((s, k) => {
      const [x, y, rot] = spots[k], at = .9 + k * .55, p = back(win(t, at, at + .8)); if (p <= 0) return;
      ctx.save(); ctx.globalAlpha = cl(p * 2);
      photo(s.favs.length ? src(s.name, s.favs[0]) : '', x, y - 120 * (1 - p), 400, 400, {rot, frame: 20, foot: 100, shadow: true, r: 2, scale: .8 + .2 * p});
      ctx.restore();
      ctx.save(); ctx.translate(x + 200, y + 400 - 120 * (1 - p)); ctx.rotate(rot);
      text(s.short, 0, 62, {size: s.short.length > 22 ? 30 : 36, weight: 700, color: C.ink, alpha: cl(p), max: 380, lh: 1.05}); ctx.restore();
    });
    foot(t, true);
  }},
  {dur: 6, when: () => D.totals.reels > 0, draw(t){     // 4: the reels
    bg(C.ink);
    const beat = .5, ph = (t % beat) / beat;
    for (let k = 0; k < 3; k++) { const q = ((t / beat + k / 3) % 1); ctx.beginPath(); ctx.arc(W / 2, 640, 180 + q * 420, 0, Math.PI * 2); ctx.strokeStyle = `rgba(240,127,90,${.35 * (1 - q)})`; ctx.lineWidth = 6; ctx.stroke(); }
    const n = D.totals.reels * ease(win(t, .2, 2));
    text(num(n), W / 2, 740, {size: 330, weight: 900, color: C.coral, ls: -12, dy: -8 * (1 - ph) * (t > 2 ? 1 : 0)});
    text(pl(D.totals.reels, 'reel made', 'reels made'), W / 2, 870, {size: 90, weight: 800, alpha: ease(win(t, .6, 1.3))});
    text(D.month ? `in ${D.label}` : `in ${D.year}`, W / 2, 960, {size: 50, weight: 500, color: C.grey, alpha: ease(win(t, 1.2, 2))});
    // a strip of film running past
    const y = 1180, fh = 430, fw = 300, gap = 22, speed = 160;
    ctx.fillStyle = '#0d0e12'; ctx.fillRect(0, y - 46, W, fh + 92);
    for (let x = -((t * speed) % 60); x < W; x += 60) { ctx.fillStyle = 'rgba(255,255,255,.18)'; rr(x + 14, y - 32, 30, 18, 4); ctx.fill(); rr(x + 14, y + fh + 14, 30, 18, 4); ctx.fill(); }
    const off = (t * speed) % (fw + gap);
    for (let k = -1; k < 5; k++) photo(pick(k + Math.floor(t * speed / (fw + gap)) + 40), k * (fw + gap) - off + 20, y, fw, fh, {r: 10});
    foot(t);
  }},
  {dur: 6, when: () => D.totals.minutes_saved > 0, draw(t){     // 5: the time you saved (Nicole: "you saved this much time"). An estimate; the side note says so.
    bg(C.lilac);
    const mins = D.totals.minutes_saved, hrs = mins / 60, p = ease(win(t, .4, 2.6));
    text('You saved about', W / 2, 330, {size: 70, weight: 700, color: C.ink, alpha: ease(win(t, 0, .7))});
    const big = hrs >= 2 ? `${num(hrs * p)} hours` : `${num(mins * p)} minutes`;
    text(big, W / 2, 520, {size: hrs >= 2 ? 190 : 150, weight: 900, color: C.coral2, ls: -7});
    text('making reels, carousels and stories', W / 2, 620, {size: 52, weight: 500, color: 'rgba(31,36,48,.75)', alpha: ease(win(t, 1, 1.7)), max: 960});
    // a clock, spinning fast and slowing down as the hours pile up
    const cx = W / 2, cy = 1130, r = 300, spin = (1 - Math.pow(1 - cl(t / 3.2), 3)) * Math.PI * 2 * 9;
    ctx.save(); ctx.globalAlpha = ease(win(t, .2, .9));
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.shadowColor = 'rgba(31,36,48,.18)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 20; ctx.fill(); ctx.shadowColor = 'transparent';
    for (let k = 0; k < 12; k++) { const a = k / 12 * Math.PI * 2; ctx.beginPath(); ctx.arc(cx + Math.sin(a) * (r - 46), cy - Math.cos(a) * (r - 46), k % 3 ? 7 : 12, 0, Math.PI * 2); ctx.fillStyle = k % 3 ? 'rgba(31,36,48,.25)' : C.ink; ctx.fill(); }
    const hand = (ang, len, w, col) => { ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(ang) * len, cy - Math.cos(ang) * len); ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.strokeStyle = col; ctx.stroke(); };
    hand(spin / 12, r * .5, 22, C.ink); hand(spin, r * .78, 12, C.coral);
    ctx.beginPath(); ctx.arc(cx, cy, 20, 0, Math.PI * 2); ctx.fillStyle = C.coral; ctx.fill();
    ctx.restore();
    const days = hrs / 8;
    if (days >= 1) text(`That's ${days >= 1.5 ? 'almost ' + Math.round(days) : 'a whole'} workday${days >= 1.5 ? 's' : ''} back.`, W / 2, 1600, {size: 60, weight: 800, color: C.ink, alpha: ease(win(t, 3, 3.7)), max: 960});
    else if (hrs >= 1) text("That's a whole evening back.", W / 2, 1600, {size: 60, weight: 800, color: C.ink, alpha: ease(win(t, 3, 3.7)), max: 960});
    foot(t, true);
  }},
  {dur: 6, when: () => D.totals.carousels + D.totals.stories > 0, draw(t){     // 6: designed
    bg(C.cream);
    const nc = D.totals.carousels, ns = D.totals.stories;
    if (nc) {
      text(`${nc} ${pl(nc, 'carousel')}`, W / 2, 330, {size: 150, weight: 900, color: C.ink, ls: -6, alpha: ease(win(t, 0, .8))});
      if (ns) text(`& ${ns} ${pl(ns, 'set')} of stories`, W / 2, 450, {size: 90, serif: true, italic: true, weight: 400, color: C.coral2, alpha: ease(win(t, .4, 1.2))});
    } else {
      text(`${ns} ${pl(ns, 'set')}`, W / 2, 330, {size: 150, weight: 900, color: C.ink, ls: -6, alpha: ease(win(t, 0, .8))});
      text('of stories', W / 2, 450, {size: 90, serif: true, italic: true, weight: 400, color: C.coral2, alpha: ease(win(t, .4, 1.2))});
    }
    text('created', W / 2, nc && !ns ? 450 : 540, {size: 58, weight: 700, color: C.ink, alpha: ease(win(t, .8, 1.4))});
    const sp = ease(win(t, 1, 2.2));       // a carousel fanning out
    for (let k = 0; k < 5; k++) { const d = k - 2; photo(pick(60 + k), W / 2 - 165 + d * 210 * sp, 660 + Math.abs(d) * 40 * sp, 330, 412, {rot: d * .09 * sp, frame: 10, shadow: true, r: 2}); }
    for (let k = 0; k < 3; k++) {          // stories rising
      const p = ease(win(t, 2 + k * .3, 3 + k * .3));
      photo(pick(80 + k), 150 + k * 290, 1240 + 300 * (1 - p), 240, 427, {alpha: p, r: 22, shadow: true});
    }
    foot(t, true);
  }},
  {dur: 6, when: () => !!topShoot(), draw(t){     // 7: your top shoot
    bg(C.ink);
    const s = topShoot();
    text('Your top shoot', W / 2, 230, {size: 58, weight: 600, color: C.grey, alpha: ease(win(t, 0, .7))});
    text(s.short, W / 2, 360, {size: 120, serif: true, italic: true, weight: 400, color: C.coral, alpha: ease(win(t, .3, 1.1)), max: 960, lh: 1.02});
    const p = ease(win(t, .6, 1.6));
    photo(HERO, 90, 560 + 60 * (1 - p), 900, 1040, {r: 30, zoom: 1 + .1 * (t / 6), alpha: p, shadow: true});
    const bits = [[s.reels, 'reel'], [s.carousels, 'carousel'], [s.stories, 'story set']].filter(b => b[0]).map(b => `${b[0]} ${pl(b[0], b[1])}`);
    text(bits.join(' · '), W / 2, 1720, {size: 44, weight: 600, alpha: ease(win(t, 1.6, 2.4)), max: 960});
    foot(t);
  }},
  {dur: 6, when: () => D.totals.posted > 0 || D.totals.ready > 0, draw(t){     // 8: out in the world
    bg(C.coral);
    const n = D.totals.posted;
    const T = D.totals, every = D.month && T.weeks && T.weeks_posted === T.weeks;
    text(n ? 'You posted' : 'Your posts', W / 2, 250, {size: 70, weight: 700, color: C.ink, alpha: ease(win(t, 0, .6))});
    text(n ? `${num(n * ease(win(t, .2, 1.4)))} ${pl(n, 'time')}` : 'are on their way', W / 2, 450, {size: n ? 200 : 110, weight: 900, color: C.white, ls: n ? -8 : -3, max: 980});
    if (n) text(every ? `Every single week. So consistent!` : D.month ? 'on Instagram. Keep it going!' : 'on Instagram. Way to show up!', W / 2, 570, {size: 56, weight: 700, color: C.ink, alpha: ease(win(t, .5, 1.2)), max: 980});
    if (T.ready) text(n ? `and ${T.ready} more ready to go` : `${T.ready} ready to go`, W / 2, 660, {size: 46, weight: 500, color: C.ink, alpha: ease(win(t, 1, 1.6))});
    const gx = 160, gy = 770, gw = 760, cw = (gw - 2 * 10) / 3, ch = cw * 5 / 4;
    ctx.fillStyle = '#fff'; rr(gx - 16, gy - 16, gw + 32, 3 * ch + 2 * 10 + 32, 26); ctx.fill();
    const fly = ease(win(t, 2, 3));
    for (let k = 0; k < 9; k++) {
      const slot = k === 0 ? 0 : k, r = Math.floor(slot / 3), c = slot % 3, a = ease(win(t, .6 + k * .1, 1.2 + k * .1));
      if (k === 0) continue;
      photo(pick(100 + k), gx + c * (cw + 10), gy + r * (ch + 10), cw, ch, {r: 6, alpha: a});
    }
    // the newest post flies into the top left, with a shine
    const fx = gx + (W - gx) * (1 - fly), fy = gy - 300 * (1 - fly);
    photo(pick(99), fx, fy, cw, ch, {r: 6, rot: (1 - fly) * .4, shadow: fly < 1, alpha: cl(win(t, 1.9, 2.1))});
    if (fly >= 1) { const sh = win(t, 3, 3.8); if (sh > 0 && sh < 1) { ctx.save(); rr(gx, gy, cw, ch, 6); ctx.clip(); const g = ctx.createLinearGradient(gx - cw + sh * 3 * cw, 0, gx + sh * 3 * cw, 0); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,.65)'); g.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = g; ctx.fillRect(gx, gy, cw, ch); ctx.restore(); } }
    foot(t, true);
  }},
  {dur: 6.5, draw(t){   // 9: here's to next year
    bg(C.ink);
    const R = rng(3);
    for (let k = 0; k < 10; k++) {
      const x = R() * (W - 300), y = 60 + R() * 760, rot = (R() - .5) * .45, at = k * .12;
      photo(pick(120 + k), x, y, 300, 375, {rot: rot + Math.sin(t * .8 + k) * .03, frame: 12, foot: 20, shadow: true, r: 3, alpha: ease(win(t, at, at + .6))});
    }
    text("Here's to", W / 2, 1180, {size: 110, weight: 800, alpha: ease(win(t, 1.2, 2))});
    text(D.month ? `${D.next}.` : 'next year.', W / 2, 1340, {size: 170, serif: true, italic: true, weight: 400, color: C.coral, alpha: ease(win(t, 1.7, 2.5))});
    if (D.handle) text(D.handle, W / 2, 1520, {size: 58, weight: 700, alpha: ease(win(t, 2.4, 3))});
    text(`Made with ${CFG.product} ${CFG.maker}`, W / 2, H - 90, {size: 34, weight: 600, color: 'rgba(255,255,255,.55)', alpha: ease(win(t, 2.8, 3.4))});
  }},
];

/* ---------- the player ---------- */
const P = {i: 0, t: 0, last: 0, paused: false, hold: false};
function frame(now){
  if (!P.last) P.last = now;
  const dt = Math.min(.1, (now - P.last) / 1000); P.last = now;
  if (!P.paused && !P.hold) P.t += dt;
  const s = S[P.i];
  if (P.t >= s.dur) { if (P.i < S.length - 1) { P.i++; P.t = 0; } else { P.t = s.dur; P.paused = true; ppLabel(); } }
  ctx.save(); S[P.i].draw(STILL ? S[P.i].dur : P.t); ctx.restore();     // nothing moves when they asked for less motion: each story finished
  [...$('bars').children].forEach((b, k) => b.firstChild.style.width = (k < P.i ? 100 : k > P.i ? 0 : cl(P.t / S[P.i].dur) * 100) + '%');
  requestAnimationFrame(frame);
}
const go = d => { if (!S.length) return; P.i = cl(P.i + d, 0, S.length - 1); P.t = 0; P.paused = false; ppLabel(); };
function ppLabel(){ $('pp').textContent = P.paused ? WORDS.play : WORDS.pause; }
$('next').onclick = () => go(1); $('prev').onclick = () => go(-1);
$('again').onclick = () => { P.i = 0; P.t = 0; P.paused = false; ppLabel(); };
$('pp').onclick = () => { P.paused = !P.paused; ppLabel(); };
let downAt = 0;
['tapL', 'tapR'].forEach(id => {
  $(id).addEventListener('pointerdown', () => { downAt = Date.now(); setTimeout(() => { if (downAt) P.hold = true; }, 220); });
  $(id).addEventListener('pointerup', () => { const quick = Date.now() - downAt < 220; downAt = 0; P.hold = false; if (quick) go(id === 'tapR' ? 1 : -1); });
  $(id).addEventListener('pointerleave', () => { downAt = 0; P.hold = false; });
});
document.addEventListener('keydown', e => { if (e.target && e.target.tagName === 'BUTTON' && e.key === ' ') return; if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1); else if (e.key === ' ') { e.preventDefault(); $('pp').click(); } });

/* ---------- saving one to share: the finished picture of that story ---------- */
const fill = (s, o) => s.replace(/\{(\w+)\}/g, (m, k) => k in o ? o[k] : m);
async function saveIdx(i){
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const real = ctx; ctx = c.getContext('2d');          // the story's last moment, drawn on a spare canvas
  try { S[i].draw(S[i].dur); } finally { ctx = real; }
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  if (!blob) throw new Error(WORDS.didnt_save);
  let r;
  try { r = await fetch('/share-image?i=' + (i + 1) + (D.month ? '&m=' + D.month : '&y=' + D.year), {method: 'POST', headers: {'Content-Type': 'image/png'}, body: blob}).then(r => r.json()); }
  catch (e) { throw new Error(WORDS.didnt_save); }
  if (!r.ok) throw new Error(r.words || WORDS.didnt_save);
  return r.file;
}
function saidSaved(words){ $('said').textContent = words; $('openF').hidden = false; }
$('saveOne').onclick = async () => {
  if (!S.length) return;
  $('saveOne').disabled = true; $('said').textContent = WORDS.saving;
  try { const f = await saveIdx(P.i); saidSaved(fill(WORDS.saved_one, {file: f})); }
  catch (e) { $('said').textContent = e.message || WORDS.didnt_save; }
  $('saveOne').disabled = false;
};
$('saveAll').onclick = async () => {
  if (!S.length) return;
  $('saveAll').disabled = true;
  try { for (let i = 0; i < S.length; i++) { $('said').textContent = fill(WORDS.saving_n, {i: i + 1, n: S.length}); await saveIdx(i); } saidSaved(fill(WORDS.saved_all, {n: S.length})); }
  catch (e) { $('said').textContent = e.message || WORDS.didnt_save; }
  $('saveAll').disabled = false;
};
$('openF').onclick = async () => {
  $('openF').disabled = true;
  try { const r = await fetch('/share-open', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(r => r.json()); $('said').textContent = r.words || WORDS.cant_open; }
  catch (e) { $('said').textContent = WORDS.cant_open; }
  $('openF').disabled = false;
};

/* ---------- start: the numbers, the photos, the fonts ---------- */
(async () => {
  const ask = '/wrapped-data' + (CFG.month ? '?m=' + CFG.month : CFG.year ? '?y=' + CFG.year : '');
  const fetchD = () => fetch(ask, {cache: 'no-store'}).then(r => r.json());
  try { D = await fetchD(); } catch (e) { D = null; }
  if (!D || !D.ok) { $('wait').textContent = WORDS.cant_reach; return; }
  if (!D.anything) { $('wait').textContent = fill(D.month ? WORDS.nothing_month : WORDS.nothing_year, {label: D.label}); return; }
  if (!D.shoots.length) { $('wait').textContent = WORDS.no_shoots; return; }
  for (let k = 0; D.making && k < 40; k++) {          // small copies of the photos still being made: wait for them, a while
    $('wait').textContent = WORDS.photos_wait;
    await new Promise(r => setTimeout(r, 1500));
    try { const d = await fetchD(); if (d && d.ok) D = d; } catch (e) { break; }
  }
  const per = Math.max(1, Math.ceil(24 / D.shoots.length));
  D.shoots.forEach(s => s.favs.slice(0, per).forEach(n => POOL.push(src(s.name, n))));
  if (!POOL.length) POOL.push('');
  for (let k = POOL.length - 1; k > 0; k--) { const j = Math.floor(rng(k + 11)() * (k + 1)); [POOL[k], POOL[j]] = [POOL[j], POOL[k]]; }
  const top = topShoot();
  HERO = top && top.favs.length ? src(top.name, top.favs[0], 'l') : '';
  const all = [...new Set([...POOL, HERO, ...D.shoots.filter(s => s.favs.length).map(s => src(s.name, s.favs[0]))])].filter(Boolean);
  await Promise.all([document.fonts.ready, ...all.map(u => load(u).then(im => { if (im) got.set(u, im); }))]);
  try { await Promise.all(['400', '500', '600'].map(w => document.fonts.load(`${w} 60px 'Assistant Sans'`)).concat(CFG.serif ? [document.fonts.load("italic 400 60px 'Assistant Serif'")] : [])); } catch (e) {}
  S = ALL.filter(s => !s.when || s.when());
  $('bars').innerHTML = S.map(() => '<i><b></b></i>').join('');
  window.__wrapped = {stories: () => S.length, at: () => P.i, data: () => D, still: STILL};     // for a look from outside (the test); nothing reads it here
  $('wait').hidden = true;
  requestAnimationFrame(frame);
})();
"""


def _json_for_script(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def page_html(month=None, year=None):
    """The page. Its words are fixed here; the numbers arrive from /wrapped-data once it is open."""
    e = html.escape
    day = today()
    month = month if month_ok(month) else None
    year = None if month else (str(year) if year_ok(str(year or "")) else str(default_year(day)))
    if month:
        label = calendar.month_name[int(month[5:])]
        word = W("so_far") if month == day.isoformat()[:7] else W("recapped")
        title, eyebrow = W("title_month").replace("{label}", label), W("eyebrow_month")
        h1 = W("h1_month").replace("{label}", e(label)).replace("{word}", e(word))
        lede, wait = W("lede_month").replace("{label}", label), W("wait_month").replace("{label}", label)
    else:
        title, eyebrow, h1, lede, wait = W("title_year"), W("eyebrow_year"), W("h1_year"), W("lede_year"), W("wait_year")
    words = {k: W(k) for k in ("play", "pause", "saving", "saving_n", "saved_one", "saved_all", "didnt_save", "cant_reach",
                               "nothing_month", "nothing_year", "no_shoots", "photos_wait", "cant_open")}
    cfg = {"month": month or "", "year": year or "", "serif": ACCENT_SERIF, "product": brand.PRODUCT, "maker": brand.MAKER}
    serif = ("@font-face{font-family:'Assistant Serif';src:url('/wrapped-font') format('truetype');font-weight:400;"
             "font-style:italic;font-display:swap}") if ACCENT_SERIF else ""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{e(brand.title(title))}</title><style>{look.head_css()}{serif}{CSS}</style></head><body>"
        "<div class='top'><a class='homelink' href='/home'><span aria-hidden='true'>&larr;</span>"
        f"<span class='long'>{e(W('back_home'))}</span><span class='short'>{e(W('home_short'))}</span></a></div>"
        "<div class='page'><div class='phone' id='phone'>"
        f"<canvas id='cv' width='{PNG_W}' height='{PNG_H}'></canvas><div class='bars' id='bars'></div>"
        f"<div class='tap l' id='tapL' title='{e(W('tap_back'))}'></div><div class='tap r' id='tapR' title='{e(W('tap_next'))}'></div>"
        f"<div class='wait' id='wait'>{e(wait)}</div></div>"
        f"<div class='side'><span class='eyebrow'>{e(eyebrow)}</span><h1>{h1}</h1><p>{e(lede)}</p>"
        f"<div class='row'><button class='btn' id='prev'>{e(W('back'))}</button><button class='btn' id='pp'>{e(W('pause'))}</button>"
        f"<button class='btn' id='next'>{e(W('next'))}</button><button class='btn' id='again'>{e(W('again'))}</button></div>"
        f"<div class='row'><button class='btn main' id='saveOne'>{e(W('save_one'))}</button><button class='btn' id='saveAll'>{e(W('save_all'))}</button></div>"
        f"<div class='row'><span class='said' id='said' role='status'></span><button class='btn' id='openF' hidden>{e(W('open_folder'))}</button></div>"
        f"<p class='note'>{e(W('note'))} {e(W('note_time'))} {e(W('estimate'))}</p></div></div>"
        f"<script>const WORDS = {_json_for_script(words)};const CFG = {_json_for_script(cfg)};{STORIES_JS}</script></body></html>")


# ---------- the commands ----------

def main():
    ap = argparse.ArgumentParser(description="Your year and the monthly recap: the counts, and the page's address.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("data", "url"):
        p = sub.add_parser(name)
        p.add_argument("--month", help="one month, as 2026-11")
        p.add_argument("--year", help="one year, as 2026")
    sub.add_parser("home")
    a = ap.parse_args()
    if a.cmd == "home":
        say(json.dumps(home_answers(), indent=1, ensure_ascii=False))
        return 0
    if a.month and (a.year or not month_ok(a.month)):
        say("STOP: --month is one month written like 2026-11 (and not together with --year).")
        return 2
    if a.year and not year_ok(a.year):
        say("STOP: --year is a year written like 2026.")
        return 2
    if a.cmd == "data":
        say(json.dumps(data(month=a.month, year=a.year), indent=1, ensure_ascii=False))
        return 0
    import arrange
    try:
        import fresh
        fresh.announce()
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    base = arrange.server_base()
    if not base:
        say("STOP: the page server couldn't be started. Nothing changed.")
        return 1
    say(base + page_path(a.month, a.year))
    return 0


if __name__ == "__main__":
    sys.exit(main())
