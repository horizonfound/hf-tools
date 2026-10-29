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

    python3 posting_queue.py feed                        what the Studio knows of their real Instagram grid
    python3 posting_queue.py feed --handle horizonfound  remember their handle (asked once)
    python3 posting_queue.py grab-script                 the snippet that reads their profile page in the browser
                                                         and hands the last posts to the Studio (POST /feed, localhost only)
    python3 posting_queue.py feed --import tiles.json    the same, from a file
    python3 posting_queue.py feed --clear

The real grid: Instagram gives no simple way to read a profile's posts, so the Studio reads what is on
screen in the photographer's own browser (the Claude app's browser pane, open on their profile, signed in
or not): the grab script collects the last 15 tiles as small thumbnails and sends them to the Studio's
local server. Nothing leaves the Mac; nothing is posted. Kept in ~/.studio/feed.json + ~/.studio/feed/.

Kept in ~/.studio/posting.json with a thumbnail per piece in ~/.studio/posting-thumbs/.
A piece is named "<shoot> reel" or "<shoot> carousel"; a word or two from that is enough to find it.
"""
import argparse
import base64
import html
import json
import math
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
PFILE = HOME / "posting.json"
THUMBS = HOME / "posting-thumbs"
PAGE = HOME / "posting.html"
FEED = HOME / "feed.json"
FEED_THUMBS = HOME / "feed"
FEED_MAX = 15            # tiles read from their profile: five rows of three
FEED_ORIGINS = ("https://www.instagram.com", "https://instagram.com")
FONTS = "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=DM+Sans:wght@400;500;600&display=swap"
KINDS = ("reel", "carousel")
LOW_WEEKS = 1.0          # the running-low tap
STALE_DAYS = 7           # a yellow piece sitting this long gets a nudge


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


# ---------- the file ----------

def load():
    if PFILE.exists():
        try:
            p = json.loads(PFILE.read_text())
            p.setdefault("pieces", [])
            p.setdefault("interval", None)
            p.setdefault("reminded", {})
            return p
        except ValueError:
            sys.exit(f"STOP: {PFILE} could not be read. Nothing changed.")
    return {"pieces": [], "interval": None, "reminded": {}}


def save(p):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = PFILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(p, indent=1, ensure_ascii=False))
    os.replace(tmp, PFILE)


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
    return f"{p['shoot_name']} {p['kind']}"


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
    """Red pieces for an edited shoot, one per kind, with a thumbnail from the queue's copies."""
    made = []
    for kind in kinds:
        if any(x["shoot_id"] == shoot["id"] and x["kind"] == kind for x in p["pieces"]):
            continue
        pid = f"{shoot['id']}-{kind}"
        thumb = None
        for t in shoot.get("thumbs") or []:
            src = HOME / t
            if src.exists():
                THUMBS.mkdir(parents=True, exist_ok=True)
                dst = THUMBS / f"{pid}{src.suffix.lower()}"
                shutil.copyfile(src, dst)
                thumb = dst.relative_to(HOME).as_posix()
                break
        p["pieces"].append({"id": pid, "shoot_id": shoot["id"], "shoot_name": shoot["name"], "shot": shoot.get("shot"),
                            "kind": kind, "status": "red", "thumb": thumb, "added": now()})
        made.append(pid)
    return made


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
    if weeks is not None and weeks <= LOW_WEEKS and rem.get("low") != t:
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
            f = json.loads(FEED.read_text())
            f.setdefault("posts", [])
            return f
        except ValueError:
            pass
    return {"handle": None, "read_at": None, "posts": []}


def save_feed(f):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = FEED.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(f, indent=1, ensure_ascii=False))
    os.replace(tmp, FEED)


def post_id(href):
    """'/horizonfound/reel/DVv_ydTDP6x/' -> 'DVv_ydTDP6x'."""
    m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", str(href))
    return m.group(1) if m else re.sub(r"[^A-Za-z0-9_-]", "", str(href))[-24:]


def import_feed(tiles, handle=None):
    """The last posts as the browser saw them: [{href, data (a jpeg data URL), w, h, reel, carousel, pinned}].
    Writes one small jpeg per post and replaces feed.json whole. Returns the feed. Thumbnails that are not a
    jpeg data URL are refused (nothing else is ever written into the folder)."""
    if not isinstance(tiles, list) or not tiles:
        raise ValueError("no tiles")
    FEED_THUMBS.mkdir(parents=True, exist_ok=True)
    posts, seen = [], set()
    for t in tiles[:FEED_MAX]:
        pid = post_id(t.get("href", ""))
        if not pid or pid in seen:
            continue
        data = str(t.get("data", ""))
        if not data.startswith("data:image/jpeg;base64,"):
            continue
        raw = base64.b64decode(data.split(",", 1)[1], validate=True)
        if not raw.startswith(b"\xff\xd8") or len(raw) > 400_000:
            continue
        (FEED_THUMBS / f"{pid}.jpg").write_bytes(raw)
        seen.add(pid)
        kind = "reel" if t.get("reel") else "carousel" if t.get("carousel") else "photo"
        posts.append({"id": pid, "kind": kind, "pinned": bool(t.get("pinned")), "w": t.get("w"), "h": t.get("h"),
                      "thumb": f"feed/{pid}.jpg"})
    if not posts:
        raise ValueError("no usable tiles")
    old = load_feed()
    for p_ in FEED_THUMBS.glob("*.jpg"):      # the old grid's tiles, no longer shown: set aside, not deleted
        if p_.stem not in seen:
            keep = FEED_THUMBS / "older"
            keep.mkdir(exist_ok=True)
            os.replace(p_, keep / p_.name)
    f = {"handle": (handle or old.get("handle") or "").lstrip("@") or None, "read_at": now(), "posts": posts}
    save_feed(f)
    return f


def grab_script(port=None, handle=None):
    """The snippet to run on their profile page in the browser. It collects the first tiles of the grid as small
    jpegs (drawn in the page, so the picture never leaves the browser as a link) and posts them to the Studio
    on this Mac. Plain text body, so the browser sends it without a preflight; the Studio answers with CORS
    headers for instagram.com only."""
    if port is None:
        try:
            port = int(urlsplit((HOME / "posting-url.txt").read_text().strip()).port or 8790)
        except (OSError, ValueError):
            port = 8790
    return r"""(() => {
  const url = 'http://127.0.0.1:%d/feed';
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;top:12px;left:50%%;transform:translateX(-50%%);z-index:2147483647;background:#1F2430;color:#fff;font:600 14px/1.3 -apple-system,Helvetica,Arial,sans-serif;padding:10px 16px;border-radius:999px;box-shadow:0 10px 30px rgba(0,0,0,.3)';
  banner.textContent = 'The Studio is reading your grid...';
  document.body.appendChild(banner);
  const handle = (location.pathname.split('/').filter(Boolean)[0] || '').toLowerCase();
  const links = [...document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')].filter(a => a.querySelector('img')).slice(0, %d);
  (async () => {
    const tiles = [];
    for (const a of links) {
      const img = a.querySelector('img');
      const href = a.getAttribute('href').split('?')[0];
      try {
        const res = await fetch(img.currentSrc || img.src, {mode: 'cors'});
        const bmp = await createImageBitmap(await res.blob());
        const c = document.createElement('canvas');
        const s = 216 / Math.max(bmp.width, bmp.height);
        c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
        c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
        tiles.push({href, w: bmp.width, h: bmp.height, reel: href.includes('/reel/'),
          carousel: !!a.querySelector('svg[aria-label="Carousel"]'), pinned: !!a.querySelector('svg[aria-label="Pinned post icon"]'),
          data: c.toDataURL('image/jpeg', 0.72)});
      } catch (e) {}
    }
    if (!tiles.length) { banner.textContent = 'No posts found on this page. Scroll to the grid and try again.'; return; }
    try {
      const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({handle, tiles})});
      const j = await r.json();
      banner.textContent = j.ok ? ('Got ' + j.posts + ' posts. The Studio has your grid.') : ('The Studio said: ' + (j.error || 'no'));
    } catch (e) { banner.textContent = 'Could not reach the Studio on this Mac. Is the posting queue page open?'; }
    setTimeout(() => banner.remove(), 6000);
  })();
  return 'reading ' + links.length + ' tiles' + (handle ? ' from @' + handle : '');
})()""" % (port, FEED_MAX)


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


# ---------- the page ----------

CSS = r"""
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--coral:#F07F5A;--coral-2:#D4643F;--coral-l:#FCE6DD;
--ocean:#5EB5A9;--ocean-l:#DCEFEA;--sun:#F2CF72;--sun-l:#FBF2D6;--sand-l:#ECEAF6;--lime:#CDE9D6;--line:rgba(31,36,48,.12);
--red:#E0635A;--yellow:#E8B84A;--green:#4FB286;
--shadow:0 30px 60px -30px rgba(31,36,48,.35);--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue',Arial,sans-serif;--r:26px;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2)}
.head{padding:clamp(2rem,5vw,3.4rem) 0 1rem;display:grid;gap:.6rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(32px,4.6vw,54px)/1.03 var(--sans);letter-spacing:-.035em;text-wrap:balance}
h1 em{font:italic 400 1.1em/1 var(--display);color:var(--coral-2);letter-spacing:0}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:38em}
.tankbar{height:14px;border-radius:999px;background:var(--sand-l);overflow:hidden;max-width:520px;margin-top:.4rem}
.tankbar i{display:block;height:100%;border-radius:999px;background:var(--green);transition:width .8s var(--ease)}
.tankbar.low i{background:var(--red)}.tankbar.mid i{background:var(--yellow)}
.rhythm{font-size:14px;color:var(--ink-2)}.rhythm b{color:var(--ink)}
.sec{padding:1.6rem 0 .4rem;display:grid;gap:.3rem}
.sec h2{margin:0;font:600 22px/1.15 var(--sans);letter-spacing:-.02em}
.sec p{margin:0;color:var(--ink-2);font-size:14.5px;max-width:40em}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;max-width:420px;margin:1rem 0 .4rem;background:var(--paper);padding:4px;border-radius:18px;box-shadow:0 1px 0 var(--line)}
.tile{position:relative;aspect-ratio:4/5;background:var(--sand-l);overflow:hidden;border-radius:6px;cursor:grab;user-select:none;transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.tile:active{cursor:grabbing}.tile.dragging{opacity:.4}.tile.over{box-shadow:inset 0 0 0 3px var(--coral)}
.tile img{width:100%;height:100%;object-fit:cover;display:block}
.tile .k{position:absolute;top:6px;left:6px;font:600 10px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.45);padding:4px 7px;border-radius:999px}
.tile .d{position:absolute;bottom:6px;left:6px;right:6px;font:600 12px/1.2 var(--sans);color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.6)}
.tile.ghost{cursor:default;background:repeating-linear-gradient(45deg,#ECEAF6,#ECEAF6 6px,#E3E0F0 6px,#E3E0F0 12px)}
.tile.ghost small{position:absolute;inset:0;display:grid;place-items:center;font:italic 400 12px/1.2 var(--display);color:var(--ink-2);text-align:center;padding:8px}
.tile.real{cursor:default}.tile.real img{filter:saturate(.85)}
.tile.real .k{background:rgba(255,255,255,.8);color:var(--ink)}
.tile.mine{box-shadow:inset 0 0 0 3px var(--coral)}.tile.mine .k{background:var(--coral)}
.gridnote{font-size:13px;color:var(--ink-2);max-width:420px;margin:0}
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
.empty{font:italic 400 15px/1.3 var(--display);color:var(--ink-2);padding:.4rem 0 1rem}
.toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#fff;padding:.7rem 1.1rem;border-radius:999px;font-size:14px;opacity:0;transition:all .4s var(--ease);pointer-events:none}
.toast.on{opacity:1;transform:translateX(-50%)}
.offline{font-size:13px;color:var(--coral-2)}
@media(max-width:600px){.row{grid-template-columns:auto 52px 1fr}.row .act{grid-column:2/4}}
"""

SCRIPT = r"""
const D=JSON.parse(document.getElementById('data').textContent);const live=location.protocol.startsWith('http');
const $=s=>document.querySelector(s);const toast=$('#toast');let tt;
function say(m){toast.textContent=m;toast.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>toast.classList.remove('on'),2400)}
function nice(iso){if(!iso)return'';const d=new Date(iso+'T12:00:00');return d.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}
async function post(body){if(!live){say('This is a saved copy. Ask Claude to “show my posting queue” to change things.');return null}
 try{const r=await fetch('/posting',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw 0;return await r.json()}catch(e){say('Could not reach the Studio. Tell Claude instead.');return null}}
function render(S){
 $('#tankh').innerHTML=S.tank_head;$('#tankp').textContent=S.tank_line;
 const bar=$('#tankbar');bar.className='tankbar'+(S.weeks===null?'':S.weeks<=1?' low':S.weeks<=2?' mid':'');bar.firstElementChild.style.width=(S.weeks===null?0:Math.min(100,S.weeks/4*100))+'%';
 $('#rhythm').innerHTML=S.interval?`Posting <b>${S.interval_words}</b>. Tell Claude to change it.`:`No posting rhythm yet. Tell Claude how often you like to post.`;
 const g=$('#grid');g.innerHTML='';
 const greens=S.greens.slice().reverse();  // Instagram shows the newest first: the last in line sits top-left
 const feed=S.feed&&S.feed.posts||[];const pinned=feed.filter(x=>x.pinned),rest=feed.filter(x=>!x.pinned);
 const real=x=>{const t=document.createElement('div');t.className='tile real';t.innerHTML=`<img src="${x.thumb}" alt="">`+(x.pinned?`<span class="k">pinned</span>`:'');return t};
 pinned.forEach(x=>g.appendChild(real(x)));   // Instagram keeps pinned posts at the top; new posts land after them
 greens.forEach(x=>{const t=document.createElement('div');t.className='tile mine';t.draggable=live;t.dataset.id=x.id;
  t.innerHTML=(x.thumb?`<img src="${x.thumb}" alt="">`:'')+`<span class="k">${x.kind}</span><span class="d">${nice(x.date)}</span>`;g.appendChild(t)});
 if(feed.length){const want=Math.min(15,Math.max(9,Math.ceil((pinned.length+greens.length+Math.min(rest.length,3))/3)*3));
  for(const x of rest){if(g.children.length>=want)break;g.appendChild(real(x))}
  while(g.children.length%3){const t=document.createElement('div');t.className='tile ghost';t.innerHTML='<small>older posts</small>';g.appendChild(t)}}
 else for(let i=0;i<Math.max(0,9-greens.length);i++){const t=document.createElement('div');t.className='tile ghost';t.innerHTML=`<small>${i===0&&greens.length===0?'nothing ready yet':'what’s on your feed now'}</small>`;g.appendChild(t)}
 $('#gridnote').innerHTML=S.feed&&S.feed.posts.length?`Your last ${S.feed.posts.length} posts${S.feed.handle?' on <b>@'+S.feed.handle+'</b>':''}, read ${nice(S.feed.read_at.slice(0,10))}, with the pieces you've green-lit in their place. Say “read my grid again” to Claude to bring it up to date.`:`To see your real feed behind these, say “read my Instagram grid” to Claude.`;
 const mk=(sel,items,empty,act)=>{const el=$(sel);el.innerHTML='';if(!items.length){el.innerHTML=`<li class="empty">${empty}</li>`;return}
  items.forEach(x=>{const li=document.createElement('li');li.className='row';li.innerHTML=`<span class="light ${x.status}"></span><span class="th">${x.thumb?`<img src="${x.thumb}" alt="">`:''}</span><div><div class="name">${x.shoot_name} ${x.kind}</div><div class="sub">${act.sub(x)}</div></div><div class="act">${act.btns(x)}</div>`;el.appendChild(li)})};
 mk('#greens',S.greens,'Nothing ready to post yet.',{sub:x=>x.date?`Down for ${nice(x.date)}`:'Ready, waiting for a rhythm',btns:x=>`<button class="btn" data-a="posted" data-id="${x.id}">Posted</button><button class="btn o" data-a="unready" data-id="${x.id}">Not ready yet</button>`});
 mk('#yellows',S.yellows,'Nothing in progress.',{sub:x=>`In progress${x.where?': '+x.where:''}${x.days!=null?` · ${x.days} day${x.days!==1?'s':''}`:''}`,btns:x=>`<button class="btn g" data-a="ready" data-id="${x.id}">Ready to post</button>`});
 mk('#reds',S.reds,'Nothing waiting to be made.',{sub:x=>`Not started. Say “make the ${x.shoot_name} ${x.kind}” to Claude.`,btns:x=>`<button class="btn o" data-a="skip" data-id="${x.id}">Skip this one</button>`});
 document.querySelectorAll('[data-a]').forEach(b=>b.onclick=async()=>{const S2=await post({action:b.dataset.a,id:b.dataset.id});if(S2){render(S2);say({posted:'Posted. Nice.',ready:'Green light. It has a date now.',unready:'Back to in progress.',skip:'Skipped.'}[b.dataset.a])}});
 drag(S);}
function drag(S){if(!live)return;const g=$('#grid');let src=null;
 g.querySelectorAll('.tile.mine').forEach(t=>{
  t.addEventListener('dragstart',e=>{src=t;t.classList.add('dragging');e.dataTransfer.effectAllowed='move'});
  t.addEventListener('dragend',()=>{t.classList.remove('dragging');g.querySelectorAll('.over').forEach(x=>x.classList.remove('over'))});
  t.addEventListener('dragover',e=>{e.preventDefault();if(t!==src)t.classList.add('over')});
  t.addEventListener('dragleave',()=>t.classList.remove('over'));
  t.addEventListener('drop',async e=>{e.preventDefault();if(!src||src===t)return;const tiles=[...g.querySelectorAll('.tile.mine')];const from=tiles.indexOf(src),to=tiles.indexOf(t);
   tiles.splice(from,1);tiles.splice(to,0,src);const order=tiles.map(x=>x.dataset.id).reverse();  // back to line order (first to post first)
   const S2=await post({action:'order',ids:order});if(S2){render(S2);say('Moved. The dates follow the order.')}});});}
if(!live)$('#offline').hidden=false;render(D);
"""


def state(p):
    schedule(p)
    weeks, n = tank(p)
    def pub(x):
        d = {k: x.get(k) for k in ("id", "shoot_name", "kind", "status", "thumb", "date", "slot", "where")}
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
    return {"today": today().isoformat(), "interval": p.get("interval"), "interval_words": interval_words(p.get("interval")),
            "weeks": weeks, "tank_head": head, "tank_line": tank_words(p), "feed": feed,
            "greens": [pub(x) for x in greens(p)],
            "yellows": [pub(x) for x in p["pieces"] if x["status"] == "yellow"],
            "reds": [pub(x) for x in p["pieces"] if x["status"] == "red"]}


def page_html(p):
    data = json.dumps(state(p)).replace("</", "<\\/")
    when = today().strftime("%A, %B ") + str(today().day)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Posting queue · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body>"
            "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>"
            f"<span class='when'>{html.escape(when)}</span></div>"
            "<header class='head'><span class='eyebrow'>Posting queue</span><h1 id='tankh'></h1><p class='lede' id='tankp'></p>"
            "<div class='tankbar' id='tankbar'><i></i></div><span class='rhythm' id='rhythm'></span>"
            "<p class='offline' id='offline' hidden>This is a saved copy. Ask Claude to “show my posting queue” to change things.</p></header>"
            "<section class='sec'><h2>Your grid, as it will look</h2><p>Newest on top, the way Instagram shows it. The outlined tiles are yours to come: drag one to a different spot and its posting date follows.</p>"
            "<div class='grid' id='grid'></div><p class='gridnote' id='gridnote'></p></section>"
            "<section class='sec'><h2>Ready to post</h2></section><ul class='list' id='greens'></ul>"
            "<section class='sec'><h2>In progress</h2><p>The Studio did its part. Finish it in CapCut or Canva, then press Ready.</p></section><ul class='list' id='yellows'></ul>"
            "<section class='sec'><h2>Not started</h2></section><ul class='list' id='reds'></ul>"
            "</div><div class='toast' id='toast'></div>"
            f"<script type='application/json' id='data'>{data}</script><script>{SCRIPT}</script></body></html>")


def write_page(p):
    HOME.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page_html(p))
    return PAGE


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/posting.html"):
            body = page_html(load()).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if (path.startswith("/posting-thumbs/") or path.startswith("/feed/")) and ".." not in path:
            return super().do_GET()
        self.send_error(HTTPStatus.NOT_FOUND)

    def cors(self):
        """Only the grab script, running on instagram.com in their own browser, may talk to /feed from another origin."""
        origin = self.headers.get("Origin", "")
        if origin in FEED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
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
        if path == "/feed":
            return self.post_feed()
        if path != "/posting":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            p = load()
            act = body.get("action")
            if act in ("ready", "unready", "posted", "skip"):
                x = next(y for y in p["pieces"] if y["id"] == body.get("id"))
                set_status(p, x, {"ready": "green", "unready": "yellow", "posted": "posted", "skip": "skipped"}[act], by="page")
            elif act == "order":
                ids = [str(i) for i in body.get("ids", [])]
                g = {x["id"]: x for x in greens(p)}
                for i, pid in enumerate([i for i in ids if i in g], 1):
                    g[pid]["slot"] = i
                renumber(p)
                schedule(p, reflow=True)
            else:
                raise ValueError(act)
            schedule(p)
            save(p)
            write_page(p)
        except (StopIteration, ValueError, TypeError) as e:
            self.send_error(HTTPStatus.BAD_REQUEST, str(e)[:200])
            return
        out = json.dumps(state(p)).encode()
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
        except (ValueError, TypeError, KeyError) as e:
            out, code = {"ok": False, "error": "nothing usable in what the page sent"}, HTTPStatus.BAD_REQUEST
            say(f"(feed refused: {str(e)[:120]})")
        data = json.dumps(out).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


def serve(port):
    HOME.mkdir(parents=True, exist_ok=True)
    for pt in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", pt), partial(Handler, directory=str(HOME)))
            break
        except OSError:
            continue
    else:
        sys.exit(f"STOP: no free port between {port} and {port + 19}.")
    url = f"http://127.0.0.1:{pt}/posting.html"
    (HOME / "posting-url.txt").write_text(url)
    print(f"Posting queue: {url}", flush=True)
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
    a_ = sub.add_parser("add"); a_.add_argument("--shoot", required=True); a_.add_argument("--kinds", default="reel,carousel")
    m = sub.add_parser("made"); m.add_argument("piece"); m.add_argument("--where")
    for c in ("ready", "unready", "posted", "skip"):
        sub.add_parser(c).add_argument("piece")
    mv = sub.add_parser("move"); mv.add_argument("piece"); mv.add_argument("--to", type=int, required=True)
    sub.add_parser("list"); sub.add_parser("tank"); sub.add_parser("page")
    r = sub.add_parser("reminders"); r.add_argument("--mark", action="store_true")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8790)
    fd = sub.add_parser("feed"); fd.add_argument("--handle"); fd.add_argument("--import", dest="import_file"); fd.add_argument("--clear", action="store_true")
    gs = sub.add_parser("grab-script"); gs.add_argument("--port", type=int)
    a = ap.parse_args()
    p = load()

    if a.cmd == "feed":
        f = load_feed()
        if a.clear:
            for p_ in FEED_THUMBS.glob("*.jpg"):
                (FEED_THUMBS / "older").mkdir(parents=True, exist_ok=True)
                os.replace(p_, FEED_THUMBS / "older" / p_.name)
            save_feed({"handle": a.handle or f.get("handle"), "read_at": None, "posts": []})
            write_page(p)
            say("Forgot your grid. The page shows placeholders again until it's read once more.")
            return 0
        if a.import_file:
            body = json.loads(Path(a.import_file).read_text())
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
        return 0
    if a.cmd == "add":
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
        return 0
    if a.cmd == "move":
        x = find(p, a.piece, statuses=("green",))
        g = greens(p); g.remove(x); g.insert(max(0, min(a.to - 1, len(g))), x)
        for i, y in enumerate(g, 1):
            y["slot"] = i
        schedule(p, reflow=True); save(p); write_page(p)
        say(f"{piece_name(x)} is now {x['slot']} in line, down for {nice_day(x['date'])}." if x.get("date") else f"{piece_name(x)} is now {x['slot']} in line.")
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
    if a.cmd == "serve":
        serve(a.port); return 0


if __name__ == "__main__":
    sys.exit(main())
