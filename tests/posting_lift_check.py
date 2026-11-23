#!/usr/bin/env python3
"""Posted lifts the post into the feed (Nicole's v28, section 6 "Posted", her screenshot 09): switching a post to
Posted, the tile lifts on an arc and lands in its spot in the grid with a shine, a green check and 22 pieces of
confetti, the other tiles slide over, and the row's Posted button slides its row out first. ?try=posted plays it
on the first ready post and puts everything back, changing nothing. The animation only draws: the save is the
same save as before and happens first.

    python3 tests/posting_lift_check.py [--port 8826] [--work <a folder to keep the run in>] [--no-chrome]

On a pretend Assistant with a pretend kit it makes itself in a throwaway folder (tiny pictures; nothing of the
real ~/.studio, no drive, no calendar: REMINDERS_BACKEND=file). The page runs in a HIDDEN Chrome with a small
note-taker in front of it (every fetch and every animation the page starts is written down), so "nothing was
sent" and "nothing moved" are read from a list, not guessed from the clock:
  * her line and the page's own promises, read from the script (no browser);
  * ?try=posted: the pretend "after" (the tile in the feed, the check, the shine, 22 confetti), a press while it
    plays sends nothing, then everything back with her line; the queue's file byte for byte the same; no POST;
  * a real press on a row's Posted button: saved first, then the row slides out, the tile rides its arc from
    where it was, the other tile slides over, the check, the shine, the confetti, and all of it cleared away;
  * the switch back: the tile rides back into line, with no check and no confetti;
  * prefers-reduced-motion: the same saves and the same end state with not one animation, and ?try=posted too.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: kits, the page server)
import posting_panel_check as ppc  # noqa: E402
import posting_posted_check as posted  # noqa: E402  (fresh_queue, the grid's signature, a posted tile)

SCRIPTS = wpc.SCRIPTS
SOURCE = (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")
PREVIEW = "That was a preview. Nothing changed."           # hers (UPDATE-v28.md section 6, her diff)
T_POSTED, T_BACK = posted.T_POSTED, posted.T_BACK
GRID, ptile = posted.GRID, posted.ptile

# the note-taker: every fetch (and its answer) and every animation the page starts, in order
LOG = ("window.__log = []; (function(){ var f = window.fetch; window.fetch = function(u, o){ var m = (o && o.method) || 'GET';"
       " window.__log.push({t: 'fetch', m: m, u: String(u)}); var p = f.apply(this, arguments);"
       " p.then(function(){ window.__log.push({t: 'answer', m: m, u: String(u)}); }, function(){}); return p; };"
       " var a = Element.prototype.animate; Element.prototype.animate = function(k, o){"
       " window.__log.push({t: 'anim', tag: this.tagName, cls: String(this.className), id: (this.dataset && this.dataset.id) || '',"
       " dur: Math.round(typeof o === 'number' ? o : o.duration), k0: (k && k[0] && k[0].transform) || '', mid: (k && k[1] && k[1].transform) || ''});"
       " return a.apply(this, arguments); }; })()")
LEFT = "document.querySelectorAll('.pqconf, .tile .yay, .tile.shine').length"


def skip(line):
    print("SKIP  " + line, flush=True)


def her_diff():
    for base in (HERE.parent, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v28-*"), reverse=True):
            f = h / "Carousel designer and reel picker" / "plugin-changes" / "posting_queue-since-v27.diff"
            if f.is_file():
                return f.read_text(encoding="utf-8")
    return None


def log(c):
    return c.js("window.__log") or []


def anims(c):
    return [e for e in log(c) if e["t"] == "anim"]


def posts(c):
    return [e for e in log(c) if e["t"] == "fetch" and e["m"].upper() != "GET"]


def reduce(c, on):
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce" if on else "no-preference"}]})


def queue_bytes(s):
    return (s.studio / "posting.json").read_bytes()


# ---------- 1. the script, read ----------

def check_source(s):
    start = SOURCE.index('SCRIPT = r"""')
    script = SOURCE[start:SOURCE.index('"""', start + 20)]
    case("her line is on the page, whole", "preview:'%s'" % PREVIEW in script)
    case("v31: the grid shows 12 posts at most (GRID_MOST, four rows), not 15", "const GRID_MOST=12;" in script
         and "g.children.length>=GRID_MOST" in script and ">=15" not in script)
    case("v31: the grid has no fixed width; it takes the width of her line through the box around them (fit-content)",
         "max-width:420px" not in SOURCE and ".gridbox{width:fit-content;max-width:100%;display:flex;flex-direction:column;gap:.3rem}" in SOURCE
         and "<div class='gridbox' id='gridbox'><p class='pickhint'" in SOURCE)
    d = her_diff()
    if d is None:
        skip("her line compared with her diff: her v28 pack is not beside the project")
    else:
        case("...and it is hers: her diff has it", PREVIEW in d)
    new = script[script.index("Posted lifts the post into the feed"):script.index("function render(S){LAST=S;")]
    case("the new part of the page never says Claude and has no long dash", "Claude" not in new and "—" not in new)
    case("22 pieces of confetti, as hers", "const CONFETTI=22;" in script)
    case("lift() draws the new state and stops under prefers-reduced-motion, before anything is measured or moved",
         "if(calm()||!g.animate){render(S2);return}" in new and "prefers-reduced-motion: reduce" in new)
    case("while the preview plays post() sends nothing: the check sits before the fetch",
         script.index("if(TRYING){say(PW.preview);return null}") < script.index("fetch('/posting',{method:'POST'"))
    case("the styles turn the shine, the check and the confetti off under prefers-reduced-motion too",
         "@media (prefers-reduced-motion:reduce){.tile.shine::before,.tile .yay,.pqconf{display:none;animation:none}}" in SOURCE)
    code, _, raw = s.http("GET", "/posting.html?try=posted")
    case("the page answers at /posting.html?try=posted (the same page; the server does nothing with the word)",
         code == 200 and b"tryPosted" in raw)


# ---------- 2. the page ----------

LINE_W = ("(function(){ var h = document.getElementById('pickhint'), sec = h.closest('.sec'), k = h.cloneNode(true);"
          " k.removeAttribute('id'); k.hidden = false; k.style.cssText += ';position:absolute;left:0;top:0;width:max-content;visibility:hidden';"
          " sec.appendChild(k); var w = k.getBoundingClientRect().width; k.remove(); return w; })()")
GRID_W = "document.getElementById('grid').getBoundingClientRect().width"


def check_size(c, s):
    """Nicole's v31, section 8 (was v30, section 5: about 420 px): the grid is as wide as her line above it, "Click on
    a post to change the photo it shows in your grid, or to copy its caption", about 550 px, and it follows the line,
    not a number: a bigger font makes the grid wider. 12 posts at most (four rows of three; v30 showed 15). The gap
    is still 3 px, and the panel still opens inside the grid at the grid's width."""
    reel, car = posted.fresh_queue(s)
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    c.js("document.fonts.ready.then(function(){ return 1; })")
    m = c.js("(function(){ var g = document.getElementById('grid'), cs = getComputedStyle(g), t = g.querySelector('.tile'), h = document.getElementById('pickhint');"
             " return {w: g.getBoundingClientRect().width, gap: cs.columnGap, rowgap: cs.rowGap, tw: t.getBoundingClientRect().width,"
             " th: t.getBoundingClientRect().height, vw: innerWidth, sw: document.documentElement.scrollWidth, shown: !h.hidden,"
             " lines: Math.round(h.getBoundingClientRect().height / parseFloat(getComputedStyle(h).lineHeight)), line: %s}; })()" % LINE_W)
    case("at desktop width (1280) her line shows on one line above the grid", m["shown"] and m["lines"] == 1 and m["vw"] >= 1200, m)
    case("...and the grid is exactly as wide as her line (within 1 px), about 550 px (520 to 600), not 420",
         abs(m["w"] - m["line"]) <= 1 and 520 <= m["w"] <= 600, m)
    case("...with a 3 px gap between posts, across and down", m["gap"] == "3px" and m["rowgap"] == "3px", m)
    room = c.js("(function(){ var h = document.getElementById('pickhint').getBoundingClientRect(), g = document.getElementById('grid').getBoundingClientRect(), r = parseFloat(getComputedStyle(document.documentElement).fontSize); return [g.top - h.bottom, 0.9 * r]; })()")
    case("...and between her line and the grid the same room as before (.9rem: the box's margins add up, never collapse)", abs(room[0] - room[1]) <= 0.5, room)
    case("...so a post is about 180 px wide and four rows (12 posts) are about 900 px tall",
         170 <= m["tw"] <= 200 and 4 * m["th"] + 12 < 1000, m)
    case("...and the page has no sideways scroll", m["sw"] <= m["vw"], m)
    # the line, not the number: a bigger font on her line makes the grid follow it
    big = c.js("(function(){ var h = document.getElementById('pickhint'); h.style.fontSize = '17px'; var r = {w: %s, line: %s}; h.style.fontSize = ''; return r; })()" % (GRID_W, LINE_W))
    case("her line in a bigger font: the grid grows with it, still exactly as wide as the line", big["w"] > m["w"] + 40 and abs(big["w"] - big["line"]) <= 1, (big, m["w"]))
    # with no post to click her line is hidden: it takes no room, and the grid keeps its width
    hid = c.js("(function(){ var h = document.getElementById('pickhint'); h.hidden = true; var p = h.closest('.sec').querySelector('p:not(.pickhint)').getBoundingClientRect(), g = document.getElementById('grid').getBoundingClientRect(), rem = parseFloat(getComputedStyle(document.documentElement).fontSize);"
                " var r = {w: %s, h: h.getBoundingClientRect().height, vis: getComputedStyle(h).visibility, room: g.top - p.bottom, want: 1.3 * rem}; h.hidden = false; return r; })()" % GRID_W)
    case("her line hidden: it is not seen and takes no height, the grid keeps the same width, and sits where it did before (1.3rem under the words above)",
         hid["h"] == 0 and hid["vis"] == "hidden" and abs(hid["w"] - m["w"]) <= 1 and abs(hid["room"] - hid["want"]) <= 0.5, hid)
    # 12 posts at most: twenty posts read from their feed, two upcoming ones, four rows of three
    feed = c.js("(function(){ var px = 'data:image/gif;base64,R0lGODlhAQABAAAAACw=', posts = [];"
                " for (var i = 0; i < 20; i++) posts.push({id: 'f' + i, thumb: px, pinned: false});"
                " render(Object.assign({}, LAST, {feed: {handle: 'h', read_at: '2026-11-20T10:00:00', posts: posts}}));"
                " var g = document.getElementById('grid'), t = Array.prototype.slice.call(g.children).filter(function(e){ return e.classList.contains('tile'); });"
                " return {n: t.length, mine: g.querySelectorAll('.tile.mine').length, real: g.querySelectorAll('.tile.real').length, ghost: g.querySelectorAll('.tile.ghost').length,"
                " rows: Math.round(g.getBoundingClientRect().height / (t[0].getBoundingClientRect().height + 3))}; })()")
    case("with 20 feed posts and 2 upcoming: 12 posts in the grid (2 upcoming, 10 of the feed), four rows, not 15",
         feed["n"] == 12 and feed["mine"] == 2 and feed["real"] == 10 and feed["ghost"] == 0 and feed["rows"] == 4, feed)
    c.reload()
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    ppc.open_panel(c, car["id"])
    p = c.js("(function(){ var k = document.getElementById('pick'), g = document.getElementById('grid'); return {inside: k.parentNode === g,"
             " w: k.getBoundingClientRect().width, sw: k.scrollWidth, cw: k.clientWidth, gw: g.getBoundingClientRect().width,"
             " pageW: document.documentElement.scrollWidth, vw: innerWidth}; })()")
    case("a post's panel still opens inside the grid, the grid's width, with nothing in it running past its edge",
         p["inside"] and abs(p["w"] - (p["gw"] - 8)) <= 2 and p["sw"] <= p["cw"] + 1 and p["pageW"] <= p["vw"], p)
    c.click("#pick .x")
    # a phone: her line wraps, and the grid takes the width there is, with no sideways scroll
    c.cdp("Emulation.setDeviceMetricsOverride", {"width": 375, "height": 812, "deviceScaleFactor": 1, "mobile": False})
    try:
        c.reload()
        c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
        ph = c.js("(function(){ var g = document.getElementById('grid'), h = document.getElementById('pickhint');"
                  " return {w: g.getBoundingClientRect().width, hw: h.getBoundingClientRect().width, vw: innerWidth, sw: document.documentElement.scrollWidth}; })()")
        case("at phone width (375) the grid is as wide as her wrapped line, inside the window, with no sideways scroll",
             abs(ph["w"] - ph["hw"]) <= 1 and ph["w"] <= ph["vw"] - 20 and ph["sw"] <= ph["vw"], ph)
    finally:
        c.cdp("Emulation.clearDeviceMetricsOverride", {})


def check_page(c, s):
    reel, car = posted.fresh_queue(s)
    rid, cid = reel["id"], car["id"]
    c.init_script(LOG)
    # The test says which it means, every time: a machine may itself ask for reduced motion (GitHub's Mac does),
    # and then the page, rightly, plays nothing. Never left to the computer's own setting.
    reduce(c, False)

    # ?try=posted
    c.open(s.url("/posting.html?try=posted"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    grid0, bytes0 = c.js(GRID), queue_bytes(s)
    c.wait_for("document.querySelectorAll(%s).length === 1" % json.dumps(ptile(rid)), 10)
    case("?try=posted: the first ready post (the next one up) is drawn in the feed, her Posted toast showing",
         c.js(GRID)[1].startswith("posted:" + rid) and ppc.wait_toast(c, T_POSTED) is True, c.js(GRID))
    yay = c.js("(function(){ var y = document.querySelector(%s + ' .yay'); return y ? [y.textContent, y.getAttribute('aria-hidden'), getComputedStyle(y).backgroundColor] : null; })()" % json.dumps(ptile(rid)))
    case("...with a green check on it (hidden from screen readers) and the shine", yay == ["✓", "true", "rgb(79, 178, 134)"]
         and c.js("document.querySelector(%s).classList.contains('shine')" % json.dumps(ptile(rid))), yay)
    a = [e for e in anims(c) if e["id"] == rid and e["dur"] == 950]
    case("...the tile rides her arc: 950 ms, a little bigger (1.14) and 34 px up on the way", len(a) == 1 and "scale(1.14)" in a[0]["mid"] and "-34px" in a[0]["mid"], a)
    got = c.js("post({action:'skip',id:%s})" % json.dumps(cid))
    case("...a press while it plays sends nothing and says her line", got is None and not posts(c) and ppc.wait_toast(c, PREVIEW) is True, (got, posts(c)))
    c.wait_for("document.querySelectorAll('.pqconf').length === 0 && window.__log.some(function(e){ return e.cls === 'pqconf'; })", 10)
    conf = [e for e in anims(c) if e["cls"] == "pqconf"]
    case("...22 pieces of confetti flew, and every one was taken away", len(conf) == 22, len(conf))
    c.wait_for("document.querySelectorAll('#grid .tile.justposted').length === 0 && document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    case("then everything is back as it was, and her line says so", c.js(GRID) == grid0 and ppc.wait_toast(c, PREVIEW) is True, (c.js(GRID), grid0))
    c.wait_for(LEFT + " === 0", 6)
    case("...nothing changed: no POST left the page, the queue's file is byte for byte the same, both posts still ready",
         not posts(c) and queue_bytes(s) == bytes0 and ppc.piece(s, rid)["status"] == "green" and ppc.piece(s, cid)["status"] == "green", posts(c))
    case("...and the page takes real presses again", c.js("TRYING") is False)

    # a real press: the row's Posted button, on the post that is NOT next up (so the tile has somewhere to go)
    c.open(s.url("/posting.html"))
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    time.sleep(2.5)
    case("without ?try=posted nothing plays by itself", not anims(c) and c.count("#grid .tile.justposted") == 0, anims(c))
    c.click("#greens [data-a='posted'][data-id=%s]" % json.dumps(cid))
    toast = ppc.wait_toast(c, T_POSTED)
    c.wait_for("document.querySelectorAll(%s).length === 1" % json.dumps(ptile(cid)), 10)
    lg = log(c)
    sent = next((i for i, e in enumerate(lg) if e["t"] == "fetch" and e["m"] == "POST"), -1)
    back = next((i for i, e in enumerate(lg) if e["t"] == "answer" and e["m"] == "POST"), -1)
    first = next((i for i, e in enumerate(lg) if e["t"] == "anim"), -1)
    case("the row's Posted button: the save went out and was answered BEFORE the first animation started, and the queue says posted",
         0 <= sent < back < first and ppc.piece(s, cid)["status"] == "posted" and toast is True, (sent, back, first, toast))
    an = anims(c)
    case("...the row slides out first (260 ms), then the tile lifts", an and an[0]["tag"] == "LI" and an[0]["dur"] == 260 and [e["tag"] for e in an].count("LI") == 1
         and any(e["id"] == cid and e["dur"] == 950 for e in an[1:]), an[:3])
    lift = next((e for e in an if e["id"] == cid and e["dur"] == 950), {})
    case("...the tile starts from where it was in line (not from its new spot) and lands in the feed after the upcoming one",
         lift.get("k0", "").startswith("translate(") and lift.get("k0") not in ("translate(0px,0px)", "translate(0px, 0px)")
         and c.js(GRID)[0].startswith("mine:" + rid) and c.js(GRID)[1].startswith("posted:" + cid), (lift, c.js(GRID)))
    case("...the other tile slides over (650 ms)", any(e["id"] == rid and e["dur"] == 650 for e in an), an)
    case("...the check and the shine are on it", c.count(ptile(cid) + " .yay") == 1 and c.js("document.querySelector(%s).classList.contains('shine')" % json.dumps(ptile(cid))))
    c.wait_for("window.__log.filter(function(e){ return e.cls === 'pqconf'; }).length === 22", 5)
    c.wait_for(LEFT + " === 0", 8)
    case("...22 pieces of confetti, then the check, the shine and the confetti are all gone and the tile sits still in its place",
         len([e for e in anims(c) if e["cls"] == "pqconf"]) == 22
         and c.js("(function(){ var t = document.querySelector(%s); return getComputedStyle(t).transform + '|' + t.style.zIndex; })()" % json.dumps(ptile(cid))) == "none|")
    case("...one save only", len(posts(c)) == 1, posts(c))

    # the switch back: the tile rides back into line, no check, no confetti
    c.js("window.__log = []")
    c.click(ptile(cid))
    c.wait_for("%s === %s" % (ppc.OPEN_ID, json.dumps(cid)), 5)
    c.click("#pick .pswitch")
    toast = ppc.wait_toast(c, T_BACK)
    c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
    time.sleep(1.2)
    an = anims(c)
    case("the switch back to Not posted: saved, the tile rides back into line, the other slides, and there is no check, shine or confetti",
         toast is True and ppc.piece(s, cid)["status"] == "green" and any(e["id"] == cid and e["dur"] == 950 and "mine" in e["cls"] for e in an)
         and any(e["id"] == rid and e["dur"] == 650 for e in an) and not any(e["cls"] == "pqconf" for e in an) and c.js(LEFT) == 0, an)
    c.click("#pick .x")

    # the switch to Posted, from the panel
    c.js("window.__log = []")
    ppc.open_panel(c, cid)
    c.click("#pick .pswitch")
    c.wait_for("document.querySelectorAll(%s).length === 1" % json.dumps(ptile(cid)), 10)
    an = anims(c)
    case("the switch to Posted: the same lift with the check (no row to slide out), and its panel stays open as the posted post's",
         any(e["id"] == cid and e["dur"] == 950 for e in an) and not any(e["tag"] == "LI" for e in an) and c.count(ptile(cid) + " .yay") == 1
         and c.js(ppc.OPEN_ID) == cid, an)
    c.wait_for(LEFT + " === 0", 8)
    c.click("#pick .x")
    s.http("POST", "/posting", {"action": "unposted", "id": cid})

    # prefers-reduced-motion: the same saves, not one animation
    reduce(c, True)
    try:
        c.open(s.url("/posting.html"))
        c.wait_for("document.querySelectorAll('#grid .tile.mine').length === 2", 10)
        c.click("#greens [data-a='posted'][data-id=%s]" % json.dumps(cid))
        toast = ppc.wait_toast(c, T_POSTED)
        c.wait_for("document.querySelectorAll(%s).length === 1" % json.dumps(ptile(cid)), 10)
        time.sleep(0.8)
        case("reduced motion: Posted is saved and drawn in the feed with her toast, and not one animation, check, shine or piece of confetti",
             toast is True and ppc.piece(s, cid)["status"] == "posted" and not anims(c) and c.js(LEFT) == 0, anims(c))
        bytes1 = queue_bytes(s)
        c.open(s.url("/posting.html?try=posted"))
        c.wait_for("document.querySelectorAll(%s).length === 1" % json.dumps(ptile(rid)), 10)
        c.wait_for("document.querySelectorAll(%s).length === 0" % json.dumps(ptile(rid)), 10)
        case("reduced motion, ?try=posted: the pretend after is shown and put back with her line, nothing animated, nothing sent, nothing changed",
             ppc.wait_toast(c, PREVIEW) is True and not anims(c) and not posts(c) and queue_bytes(s) == bytes1 and c.js(LEFT) == 0, (anims(c), posts(c)))
    finally:
        reduce(c, False)

    # nothing ready: ?try=posted does nothing at all
    s.http("POST", "/posting", {"action": "posted", "id": rid})
    c.open(s.url("/posting.html?try=posted"))
    c.wait_for("document.querySelectorAll('#grid .tile.justposted').length === 2", 10)
    time.sleep(3)
    case("with nothing ready to post, ?try=posted plays nothing and says nothing", not anims(c) and not posts(c) and c.js("document.getElementById('toast').classList.contains('on')") is False)
    errs = [e for e in c.page_errors() if "favicon" not in e]
    case("the page ran clean (no error) and asked nothing of the internet", not errs and not c.outside_requests(), (errs, c.outside_requests()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8826)
    ap.add_argument("--no-chrome", action="store_true", help="the script's own promises only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="posting-lift-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = wpc.Setup(work, a.port)
    s.env["REMINDERS_BACKEND"] = "file"       # never the real Calendar
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ["REMINDERS_BACKEND"] = "file"
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ["STUDIO_TODAY"] = wpc.TODAY
    s.make()
    s.reel_made()
    s.slides_made(4)
    s.words("draft", "reel", {"caption": "A reel caption.", "hooks": wpc.HOOKS})
    s.words("draft", "carousel", {"caption": "A carousel caption."})
    wpc.page_module(s)
    try:
        posted.fresh_queue(s)
        group("the script, read", check_source, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the grid's size (v31)", check_size, c, s)
                group("the page", check_page, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
