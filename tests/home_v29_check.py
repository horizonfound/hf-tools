#!/usr/bin/env python3
"""The home page after Nicole's v29 (her pages/home-preview.html, section 1.2): posts first.

    python3 tests/guard.py 3000 python3 tests/home_v29_check.py [--port 9930] [--work <a folder to keep>] [--no-chrome]

What it holds, on the pretend Assistant tests/home_v28_check.py builds (two pretend kits from fake_kit.py, a scratch
STUDIO_HOME, pretend records, a card that "is in" by a test switch; nothing of the real ~/.studio, no real kit, no
/Volumes, no window on the screen):
  * the order, top to bottom: the hello, the big Turn your shoots into posts card, My posting queue full width,
    the heading Also in your Assistant, Back up a card and My editing queue side by side, the monthly recap card;
  * the big card's one button: "See all my post kits →" with post kits, "Create your post kits →" with none, a
    plain link to the post kits screen either way; the box beside it ("Newest: ..." / "No post kits yet");
  * no list of post kits on the home page: the big card holds its title, its line, its button and the one Newest
    box and nothing else, and no other kit's name or link is anywhere on the cards;
  * what went: the step numbers, "Your workflow", "Start wherever you are...", the three old button labels, and
    the "Step 1 of your workflow" eyebrow on the Back up a card screen;
  * her words compared with her own page, both ways, when her handoff is on this computer (reference-private/,
    never pushed); a SKIP line where it is not;
  * in a HIDDEN Chrome: the sections where they should be (the big card and the posting queue full width, the two
    small cards side by side and smaller), each card going where it went before with its press recorded for the
    chat (home.py pending), the big card itself not a press, the page with no post kits, and phone width with no
    sideways scroll.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only; a Mac (the pretend kits are drawn
with sips).
"""
import argparse
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import home_v28_check as v28  # noqa: E402  (its pretend Assistant: World, at, text_of, box_words)

TODAY = v28.TODAY
A, B = v28.A, v28.B
LAYOUT_KEYS = ("s3_n", "s3_p", "s3_create", "s3_see", "s4_n", "s4_p", "s4_go", "also_h", "s1_n", "s1_p", "s2_n", "s2_p")
GONE_KEYS = ("wf_h", "wf_say", "s1_go", "s2_go", "s3_go")
GONE_LINES = ("Your workflow", "Start wherever you are", "Back up →", "Open my editing queue →", "Make posts →")

# Lines of her preview page that are NOT on ours, on purpose, and why.
HERS_NOT_OURS = {
    "Home preview": "her preview page's title",
    "Preview of a new layout: making posts first, everything else supporting it. Nothing else is changed.": "her preview banner (test-only)",
    "Trying ideas:": "test-only (the link to her samples page)",
    "animation samples": "test-only",
    "·": "the dot before her samples link",
}


def skip(line):
    print("SKIP  " + line, flush=True)


def her_page():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for f in sorted(r.glob("nicole-handoff-v29-*/unpacked/Carousel designer and reel picker/pages/home-preview.html")):
            return f
        for f in sorted(r.glob("nicole-handoff-v29-*/Carousel designer and reel picker/pages/home-preview.html")):
            return f
    return None


def flat(markup):
    return [t.strip() for t in html_mod.unescape(re.sub(r"<[^>]+>", "¦", re.sub(r"</?em>", "", markup))).split("¦") if t.strip()]


def part(page, start, end):
    return page.split(start, 1)[1].split(end, 1)[0]


class Kits:
    """The pretend kits put away for a moment (moved inside the test's own folder, then moved back)."""
    def __init__(self, w):
        self.w, self.away = w, w.work / "kits-away"

    def __enter__(self):
        self.away.mkdir(exist_ok=True)
        for k in (A, B):
            (self.w.content / k).rename(self.away / k)

    def __exit__(self, *a):
        for k in (A, B):
            (self.away / k).rename(self.w.content / k)


def check_layout(w, home):
    v28.at(TODAY, "EOS_DIGITAL:233")
    f = home.facts()
    page = home.page_html()
    marks = ["<section class='hello'", "id='s3'", "id='s4'", "class='also'", "id='s1'", "id='s2'", "class='rc'"]
    order = [page.find(m) for m in marks]
    case("top to bottom: the hello, Turn your shoots into posts, My posting queue, Also in your Assistant, Back up a card, My editing queue, the recap card",
         -1 not in order and order == sorted(order), dict(zip(marks, order)))
    case("each of those is on the page once", all(page.count(m) == 1 for m in marks), [m for m in marks if page.count(m) != 1])
    case("two pretend post kits are there, the newer one is Katie's", f["kits"] == 2 and f["newest"]["short"] == "Katie Austin Maternity", (f["kits"], f["newest"]))
    big = part(page, "<section class='mk step' id='s3'>", "</section>")
    case("the big card with post kits: its title, her line, See all my post kits, and the one Newest box; nothing else",
         flat(big) == ["Turn your shoots into posts", "Turn your shoot into reels, carousels, stories, and captions.", "See all my post kits →", "Newest: Katie Austin Maternity", "2 post kits"], flat(big))
    case("... the button is a dark, plain link to the post kits screen, and a press on it is recorded as posts",
         "<a class='btn solid big' id='kitsBtn' data-item='posts' href='/make-posts'>See all my post kits →</a>" in big and big.count("<a ") == 1 and "<button" not in big)
    case("... the big card itself is not a link or a button (only its button is the press)", "<section class='mk step' id='s3'>" in page and "data-item" not in page.split("id='s3'", 1)[0].rsplit("<", 1)[1])
    cards = page.split("id='s3'", 1)[1].split("class='rc'", 1)[0]
    case("no list of post kits on the home page: the other kit's name is on no card, and nothing links to a post kit",
         "Hannah" not in part(page, "id='s3'", "id='s4'") and "/content/" not in cards and "Post kit.html" not in cards and cards.count("Newest:") == 1
         and sorted(re.findall(r"href='([^']*)'", cards)) == ["/backups", "/make-posts", "/posting.html"], re.findall(r"href='([^']*)'", cards))
    post = part(page, "<a class='step full' id='s4'", "</a>")
    case("My posting queue, full width, with her words, its box and its label", flat("<" + post) [:2] == ["My posting queue", "Your posts ready to go, and how your grid will look."]
         and flat("<" + post)[-1] == "Open my posting queue →" and "data-item='posting' href='/posting.html'" in post and "id='n4'" in post, flat("<" + post))
    also = part(page, "<div class='also'>", "</div></div>")
    words = flat(also)
    case("Also in your Assistant: the heading, then Back up a card and My editing queue with their same words and boxes, and no button label",
         words[0] == "Also in your Assistant" and "<h2>Also in your Assistant</h2>" in also
         and words[1:3] == ["Back up a card", "Copies your card to your drive, checks every photo, and sorts it into shoots."]
         and words[3:5] == ["A card is in", "EOS_DIGITAL · about 233 files"]
         and words[5:7] == ["My editing queue", "The shoots you need to edit and when they're due."]
         and "class='go'" not in also and "→" not in also and "id='n1'" in also and "id='n2'" in also, words)
    case("the two small cards open what they opened before: the Back up a card screen (a link) and the editing queue (a button), recorded as backup and queue",
         "<a class='step sm live' id='s1' data-item='backup' href='/backups'>" in also and "<button class='step sm' id='s2' data-item='queue' type='button'>" in also
         and "<span id='editingWords' hidden></span>" in also and "$('s2').onclick = () => assistant('/queue-url', $('editingWords'), W.opening_queue);" in page)
    case("what went: the step numbers, Your workflow, Start wherever you are, and the three old button labels",
         not any(g in page for g in GONE_LINES) and "class='k'" not in page and "flow4" not in page and not any(k in home.WORDS for k in GONE_KEYS), [g for g in GONE_LINES if g in page])
    case("the new words are hers and kept with her words", home.WORDS.get("s3_create") == "Create your post kits →" and home.WORDS.get("s3_see") == "See all my post kits →"
         and home.WORDS.get("also_h") == "Also in your Assistant" and not any(k in home.OUR_WORDS for k in ("s3_create", "s3_see", "also_h")))
    case("no serif, no em dash, never Claude, nothing from the internet", "serif" not in page.replace("sans-serif", "") and "Fraunces" not in page and "—" not in page and "claude" not in page.lower()
         and "https://" not in page and "http://" not in page)
    case("her accent words are in the page's own font, coral, not italic", ".step .n em{font:inherit;font-style:normal;color:var(--coral-2)}" in page)
    case("now_boxes still gives the four boxes in the order backup, editing queue, posts, posting queue",
         [v28.box_words(page, n)[0] for n in (1, 2, 3, 4)] == ["A card is in", "2 shoots waiting", "Newest: Katie Austin Maternity", "Today: Katie’s reel"] or
         [v28.box_words(page, n)[0][:6] for n in (1, 2, 3, 4)] == ["A card", "2 shoo", "Newest", "Today:"], [v28.box_words(page, n) for n in (1, 2, 3, 4)])
    # no post kits
    with Kits(w):
        f0 = home.facts()
        page0 = home.page_html()
    big0 = part(page0, "<section class='mk step' id='s3'>", "</section>")
    case("with no post kits the button reads Create your post kits, the same plain link, and the box says so",
         f0["kits"] == 0 and f0["newest"] is None
         and flat(big0) == ["Turn your shoots into posts", "Turn your shoot into reels, carousels, stories, and captions.", "Create your post kits →", "No post kits yet", "Start with any finished shoot"]
         and "<a class='btn solid big' id='kitsBtn' data-item='posts' href='/make-posts'>Create your post kits →</a>" in big0 and "See all my post kits" not in page0, flat(big0))
    case("... and the kits are back afterwards", home.facts()["kits"] == 2)
    # a card that is not in: the small card does not glow
    v28.at(TODAY)
    case("no card in: Back up a card does not glow", "<a class='step sm' id='s1' data-item='backup' href='/backups'>" in home.page_html())
    # the stale eyebrow
    import home_base
    bk = home_base.backups_html()
    case("the Back up a card screen no longer says Step 1 of your workflow, and has no empty eyebrow",
         "Step 1 of your workflow" not in bk and "of your workflow" not in part(bk, "<body", "<script") and "b_eyebrow" not in home_base.WORDS and "eyebrow" not in part(bk, "<header class='head'>", "</header>") and "<h1>Back up <em>a card.</em></h1>" in bk)
    stale = []
    for p in sorted(SCRIPTS.glob("*.py")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "of your workflow" in line and "m_eyebrow" not in line and not line.lstrip().startswith("#"):
                stale.append("%s:%d" % (p.name, n))
    case("no other screen says Step N of your workflow (the Make posts screen's is left for the stage that reworks it)", not stale, stale)


def check_her_words(w, home):
    hers = her_page()
    if not hers:
        skip("her words compared with her own page, both ways: her v29 handoff is not on this computer")
        return
    v28.at(TODAY, "EOS_DIGITAL:233")
    page = home.page_html()
    raw = hers.read_text(encoding="utf-8")
    body = raw.split("</style>", 1)[1].split("<script", 1)[0]
    theirs = flat("<title>" + raw.split("<title>", 1)[1].split("</title>", 1)[0] + "</title>" + body)
    ours = "¦" + "¦".join(flat(page.split("<script", 1)[0]) + flat("¦".join(home.WORDS.values()))) + "¦"
    gone, left = [], set()
    for t in theirs:
        if t in HERS_NOT_OURS:
            left.add(t)
        elif re.fullmatch(r"[\d\W]+", t) or ("¦" + t + "¦") in ours or ("¦" + t.replace("Your ,", "Your {year},") + "¦") in ours or t in ("Your", ", wrapped.", "wrapped."):
            continue
        else:
            gone.append(t)
    case("every line her preview page shows is on ours, whole, but for the ones left out on purpose (%d lines of hers)" % len(theirs), not gone, gone[:6])
    case("... and those are exactly her test-only lines", left == set(HERS_NOT_OURS), sorted(set(HERS_NOT_OURS) - left))
    hers_all = "¦" + "¦".join(theirs) + "¦" + raw
    lost = [k for k in LAYOUT_KEYS if ("¦" + re.sub(r"</?em>", "", home.WORDS[k]) + "¦") not in hers_all and html_mod.escape(re.sub(r"</?em>", "", home.WORDS[k])).replace("→", "&rarr;") not in raw]
    case("every line of the new layout on ours is on her page, word for word (%d lines of ours)" % len(LAYOUT_KEYS), not lost, lost)
    case("... her button changes the way ours does: Create with none, See all my post kits once there are some",
         ">Create your post kits &rarr;</a>" in raw and "if (kits.length) $('kitsBtn').innerHTML = 'See all my post kits &rarr;';" in raw)
    hers_order = [raw.find(x) for x in ('id="hello"', 'id="s3"', 'id="s4"', "Also in your Assistant", 'id="s1"', 'id="s2"', 'id="rc"')]
    case("... and her page's order is the order ours is held to", -1 not in hers_order and hers_order == sorted(hers_order), hers_order)
    case("her small cards have no button label, as ours", 'class="go"' not in part(raw, '<div class="also">', "</div>\n  </div>"))


def pending(w):
    r = subprocess.run([sys.executable, str(SCRIPTS / "home.py"), "pending"], env=w.env, capture_output=True, text=True, timeout=60)
    try:
        return [x["item"] for x in json.loads(r.stdout)]
    except ValueError:
        return ["?" + (r.stdout + r.stderr)[-200:]]


def clicks(w):
    try:
        return [c["item"] for c in json.loads((w.home / "journey.json").read_text(encoding="utf-8"))["clicks"]]
    except (OSError, ValueError, KeyError):
        return []


def check_browser(c, w):
    c.init_script("window.__asked = []; (function(){ const f = window.fetch; window.fetch = function(u, o){ window.__asked.push(String(u)); "
                  "if (String(u).startsWith('/queue-url')) return Promise.resolve(new Response(JSON.stringify({words: 'Pretend: the editing queue would open here.'}), {headers: {'Content-Type': 'application/json'}})); "
                  "return f.apply(this, arguments); }; })();")
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})

    def home_page(path="/home", collage=True):
        c.open(w.url(path))
        c.wait_for("!!document.getElementById('s3') && " + ("document.querySelectorAll('.hello .tile img.on').length > 0" if collage else "!!document.querySelector('.hello .tx h3')"), 20)
        time.sleep(0.5)

    home_page()
    R = "(id => { const r = (typeof id === 'string' ? document.querySelector(id) : id).getBoundingClientRect(); return {t: Math.round(r.top + scrollY), l: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height)}; })"
    m = c.js("(() => { const R = %s; return {hello: R('#hello'), s3: R('#s3'), s4: R('#s4'), also: R('.also h2'), s1: R('#s1'), s2: R('#s2'), rc: R('#rc'), wrap: R('.wrap'), btn: R('#kitsBtn'), n3: R('#n3')}; })()" % R)
    tops = [m[k]["t"] for k in ("hello", "s3", "s4", "also", "s1", "rc")]
    case("on the screen, top to bottom: the hello, the big card, the posting queue, the heading, the two small cards, the recap card", tops == sorted(tops) and len(set(tops)) == len(tops), tops)
    case("the big card and the posting queue run the full width", abs(m["s3"]["w"] - m["hello"]["w"]) <= 2 and abs(m["s4"]["w"] - m["hello"]["w"]) <= 2, (m["s3"], m["s4"], m["hello"]))
    case("the two small cards sit side by side, each under half the width, and smaller than the big card",
         m["s1"]["t"] == m["s2"]["t"] and m["s2"]["l"] >= m["s1"]["l"] + m["s1"]["w"] and m["s1"]["w"] < m["s3"]["w"] / 2 + 2 and abs(m["s1"]["w"] - m["s2"]["w"]) <= 2, (m["s1"], m["s2"]))
    sizes = c.js("['#s3 .n', '#s4 .n', '#s1 .n', '#s2 .n'].map(s => parseFloat(getComputedStyle(document.querySelector(s)).fontSize))")
    case("the titles step down in size: the big card, the posting queue, the two small cards", sizes[0] > sizes[1] > sizes[2] == sizes[3], sizes)
    case("the button and the Newest box sit beside each other", abs((m["btn"]["t"] + m["btn"]["h"] / 2) - (m["n3"]["t"] + m["n3"]["h"] / 2)) <= 4 and m["n3"]["l"] > m["btn"]["l"] + m["btn"]["w"], (m["btn"], m["n3"]))
    st = c.js("(() => { const b = getComputedStyle(document.getElementById('kitsBtn')); const e = getComputedStyle(document.querySelector('#s3 .n em')); return {bg: b.backgroundColor, fg: b.color, text: document.getElementById('kitsBtn').textContent, font: e.fontFamily, style: e.fontStyle, n: document.querySelectorAll('.step .n').length, k: document.querySelectorAll('.step .k').length, go: document.querySelectorAll('.step.sm .go').length}; })()")
    case("the button is dark with white words and reads See all my post kits", st["text"] == "See all my post kits →" and st["fg"] == "rgb(255, 255, 255)" and st["bg"] not in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"), st)
    case("the accent words are in the page's own font (DM Sans, carried by the Assistant), not italic; four cards, no numbers, no label on the small cards", st["font"].startswith('"Assistant Sans"') and "Fraunces" not in st["font"] and "serif" not in st["font"].replace("sans-serif", "") and st["style"] == "normal" and st["n"] == 4 and st["k"] == 0 and st["go"] == 0, st)
    case("a card is in: the small Back up a card glows", c.js("document.getElementById('s1').classList.contains('live')") is True and "240, 127, 90" in c.js("getComputedStyle(document.getElementById('s1')).boxShadow"))
    names = c.js("[...document.querySelectorAll('#s3, #s4, .also')].map(x => x.innerText).join(' | ')")
    case("no kit is listed: Katie's name is only in the Newest box and the posting queue's own box, Hannah's kit nowhere on the big card",
         c.js("document.getElementById('s3').innerText").count("Katie Austin Maternity") == 1 and "Hannah" not in c.js("document.getElementById('s3').innerText")
         and c.js("document.querySelectorAll('#s3 a').length") == 1 and c.js("document.querySelectorAll(\"a[href*='content/'], a[href*='kit=']\").length") == 0, names)
    # presses: where each goes, and that the chat hears of it
    before = len(clicks(w))
    c.click("#s3 .n")
    time.sleep(0.4)
    case("a press on the big card itself goes nowhere and records nothing", c.js("location.pathname") == "/home" and len(clicks(w)) == before)
    c.click("#kitsBtn")
    c.wait_for("location.pathname === '/make-posts'", 15)
    chrome_drive.wait_until(lambda: clicks(w)[before:] == ["posts"], 10, what="the press recorded")
    case("the button opens the post kits screen, and the press is recorded as posts", c.js("location.pathname") == "/make-posts" and clicks(w)[before:] == ["posts"], clicks(w)[before:])
    home_page()
    c.click("#s4")
    c.wait_for("location.pathname === '/posting.html'", 15)
    chrome_drive.wait_until(lambda: clicks(w)[before:] == ["posts", "posting"], 10, what="the press recorded")
    case("My posting queue opens the posting queue, recorded as posting", clicks(w)[before:] == ["posts", "posting"], clicks(w)[before:])
    home_page()
    c.click("#s1")
    c.wait_for("location.pathname === '/backups'", 15)
    chrome_drive.wait_until(lambda: clicks(w)[before:] == ["posts", "posting", "backup"], 10, what="the press recorded")
    case("Back up a card opens its screen as before, recorded as backup", c.js("location.pathname") == "/backups" and clicks(w)[before:] == ["posts", "posting", "backup"], clicks(w)[before:])
    case("... and that screen has no Step 1 of your workflow over its heading", "of your workflow" not in c.js("document.body.innerText") and c.js("document.querySelectorAll('.head .eyebrow').length") == 0
         and c.js("document.querySelector('.head h1').textContent") == "Back up a card.")
    home_page()
    c.js("window.__asked.length = 0")
    c.click("#s2")
    c.wait_for("!!document.querySelector('#s2 .note') && document.querySelector('#s2 .note').textContent.startsWith('Pretend')", 10)
    chrome_drive.wait_until(lambda: clicks(w)[before:] == ["posts", "posting", "backup", "queue"], 10, what="the press recorded")
    case("My editing queue asks for the queue as before, what comes back shows on the card, recorded as queue",
         "/queue-url" in c.js("window.__asked") and c.js("document.querySelector('#s2 .note').textContent") == "Pretend: the editing queue would open here."
         and c.js("getComputedStyle(document.querySelector('#s2 .note')).display") != "none" and clicks(w)[before:] == ["posts", "posting", "backup", "queue"], clicks(w)[before:])
    case("home.py pending tells the chat all four, in the order pressed", pending(w)[-4:] == ["posts", "posting", "backup", "queue"], pending(w))
    # the hello's buttons still go where they went
    go = c.js("JSON.parse(document.getElementById('facts').textContent).go")
    case("the hello's buttons still know where to go", go.get("backup") == "/backups" and go.get("posting") == "/posting.html" and go.get("posts") == "/make-posts", go)
    # a phone
    c.phone(390, 844)
    home_page()
    time.sleep(0.4)
    p = c.js("(() => { const R = %s; const fits = s => { const r = document.querySelector(s).getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 0.5; }; "
             "return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, cols: getComputedStyle(document.querySelector('.also-row')).gridTemplateColumns.split(' ').length, "
             "s1: R('#s1'), s2: R('#s2'), fits: ['#s3', '#kitsBtn', '#n3', '#s4', '#s1', '#s2', '.also h2'].map(fits)}; })()" % R)
    case("at phone width: no sideways scroll, every card and the button whole on the screen, the two small cards one under the other",
         p["sw"] <= p["cw"] and all(p["fits"]) and p["cols"] == 1 and p["s2"]["t"] >= p["s1"]["t"] + p["s1"]["h"], p)
    # no post kits, in the browser (the page reads everything fresh on each load)
    with Kits(w):
        home_page(collage=False)
        q = c.js("({b: document.getElementById('kitsBtn').textContent, href: document.getElementById('kitsBtn').getAttribute('href'), n3: document.getElementById('n3').innerText.replace(/\\s+/g, ' ').trim(), "
                 "sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
    case("with no post kits (phone width): Create your post kits, the same link, No post kits yet, still no sideways scroll",
         q["b"] == "Create your post kits →" and q["href"] == "/make-posts" and q["n3"] == "No post kits yet Start with any finished shoot" and q["sw"] <= q["cw"], q)


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards (default: a throwaway one, removed at the end)")
    ap.add_argument("--port", type=int, default=9930)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        skip("the pretend kits are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="home-v29-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    w = v28.World(work, a.port)
    w.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none", STUDIO_NO_WINDOWS_FOR_TESTS="1", FACES_PRETEND=str(w.pretend))
    try:
        w.build()
        # home_v28_check's pretend posting record carries a broken piece on purpose (the home page must still come);
        # the posting queue's own page is opened here, so this test's record is a clean one
        w.posting(pieces=[
            {"id": "p1", "shoot_name": "Hannah", "kind": "reel", "status": "posted", "posted_at": "2026-11-14T18:00:00"},
            {"id": "p5", "shoot_name": "Katie Austin Maternity", "kind": "reel", "status": "green", "slot": 1, "date": TODAY, "thumb": "posting-thumbs/p5.jpg"},
            {"id": "p7", "shoot_name": "Hannah", "kind": "carousel", "status": "green", "slot": 2, "date": "2026-11-20"}])
        sys.path.insert(0, str(SCRIPTS))
        import home
        case("the test's own scratch home, never the real one", Path(home.HOME) == w.home and ".studio" not in str(home.HOME))
        group("the layout, posts first", check_layout, w, home)
        group("her words, both ways", check_her_words, w, home)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            w.start()
            case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                group("the page in a browser", check_browser, c, w)
    finally:
        w.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(base), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
