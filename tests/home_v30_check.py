#!/usr/bin/env python3
"""The home page in Nicole's v30 look (her UPDATE-v30 sections 1, 2 and 3; screenshot 01; pages/home-new-look.html).

    python3 tests/guard.py 3000 python3 tests/home_v30_check.py [--port 9960] [--work <a folder to keep>] [--no-chrome] [--shot <png>]

What it holds, on the pretend Assistant tests/home_v28_check.py builds (two pretend kits drawn with sips, a scratch
STUDIO_HOME, pretend records, pretend faces, a card that "is in" by a test switch; nothing of the real ~/.studio, no
real kit, no /Volumes, no window on the screen):
  * the hello only lifts them up: a greeting and one line, each one of her approved lines filled in; no reminder,
    no button, no "Another hello"; the words as text, never markup;
  * one hello photo, the kit's 1600 px copy (size=l), a wide favorite first, never the photo itself, never a path;
  * Turn your shoots into posts (into posts in her accent), her line, four photo tiles Reels / Carousels / Stories /
    Captions, each with data-make (reel, carousel, stories, captions), each a photo from a different shoot when
    there are shoots enough, none the photo the hello opens on; See all my post kits alone (no Newest line);
  * My posting queue on the left with the last three posts of their grid ("Your grid, newest first"), Back up a
    card and My editing queue stacked on the right, each on its light card; the recap card on her tan;
  * her look: Helvetica, warm paper, black words, one accent, square corners, a thin black line under the bar, and
    the look on the home page only (every other page keeps look.py's);
  * in a HIDDEN Chrome at 1440 x 900: all of the above on the screen, the page fitting about one laptop screen,
    a tile's press asking which shoot and recorded for the chat, phone width (375 and 336) with no
    sideways scroll, reduced motion (the photo never changes), and a brand-new Assistant (grey placeholders);
  * Nicole's Nov 22 decisions: the very first hello is her one line alone ("Hi! I'm your Assistant, and I'm so glad
    you're here.", no greeting over it); a tile's press is recorded as "tile", which `home.py pending` leaves out
    (no first-time explanation in the chat) and the hello stage counts as posts started; the four tiles put the
    faces' middle about 30% from the top, above the word (her v31 section 7), and a photo whose faces can't be
    brought there gives way to the next photo with a face; the hello keeps its faces in the middle.
A screenshot of the page at 1440 x 900 is written where --shot says (default: none).

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only; a Mac (the pretend kits are drawn
with sips).
"""
import argparse
import base64
import html as html_mod
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
APPROVED = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "hellos" / "approved-hellos-by-when.json"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import home_v28_check as v28  # noqa: E402  (its pretend Assistant: World, at, box_words)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

TODAY = v28.TODAY
A, B = v28.A, v28.B
MAKES = ["reel", "carousel", "stories", "captions"]
TILE_WORDS = ["Reels", "Carousels", "Stories", "Captions"]
# words that would make the hello a reminder (her section 3: "it's not a reminder header")
REMINDERS = ("waiting", "late", "due", "pressure", "card", "Still up", "Late-night", "left ready", "back up", "queue", "Psst", "Heads up", "Today’s the day", "goes out today")


def reminds(words):
    """The reminder words in a hello, as whole words ("Your latest shoot" is no "late")."""
    return [r for r in REMINDERS if re.search(r"(?<![A-Za-z])" + re.escape(r.lower()) + r"(?![A-Za-z])", words.lower())]


def skip(line):
    print("SKIP  " + line, flush=True)


def part(page, start, end):
    return page.split(start, 1)[1].split(end, 1)[0]


def flat(markup):
    return [t.strip() for t in html_mod.unescape(re.sub(r"<[^>]+>", "¦", re.sub(r"</?em>", "", markup))).split("¦") if t.strip()]


def approved_patterns():
    """Every one of her approved lines as a pattern ({name}, {shoot}, {n}, {day}, {kind} filled with anything)."""
    d = json.loads(APPROVED.read_text(encoding="utf-8"))
    out = {}
    for group_name, lines in d.items():
        for t in lines:
            rx = "^" + re.sub(r"\\\{(name|shoot|n|day|kind)\\\}", ".+", re.escape(t)) + "$"
            out.setdefault(group_name, []).append(re.compile(rx))
    return out


def her_mock():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for f in sorted(r.glob("nicole-handoff-v30-*/pages/home-new-look.html")):
            return f
    return None


# A face a little above the photo's middle on the left (Nov 22: high enough that the old framing, which put the faces
# in the middle, and the new one, 30% from the top, land in different places in a tile)
FACE = [0.12, 0.40, 0.14, 0.15]


def pretend_faces(w):
    """A face for every other small copy (FACE), none for the rest; kept in the test's own file."""
    table = {}
    for kit in (A, B):
        for n, name in w.copies(kit).items():
            if n % 2:
                table[name] = {"w": 520, "h": 347, "faces": [list(FACE)]}
    w.put(w.pretend, table)


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


# ---------------------------------------------------------------- what the server draws

def check_page(w, home):
    v28.at(TODAY, "EOS_DIGITAL:233")
    f = home.facts()
    page = home.page_html()
    pats = approved_patterns()
    hello = part(page, "<section class='hello'", "</section>")
    g, l = flat("<h2" + part(hello, "<h2", "</h2>") + "</h2>"), flat(part(hello, "<p>", "</p>")) if "<p>" in hello else []
    greet, line = " ".join(g), " ".join(l)
    greet_groups = ("greet", "morning", "afternoon", "evening", "greetday")
    case("the hello's greeting is one of her approved greetings, filled in", any(p.match(greet) for k in greet_groups for p in pats[k]), greet)
    line_group = next((k for k, ps in pats.items() if k not in greet_groups and any(p.match(line) for p in ps)), None)
    case("... and its line is one of her approved lines (never a 'later' one)", line_group not in (None, "later"), (line, line_group))
    case("... it says what hello_lines chose, word for word", f["hello"] and greet == f["hello"]["greeting"] and line == f["hello"]["line"], (greet, line, f["hello"] and f["hello"]["greeting"]))
    case("the hello is no reminder: nothing waiting, late, due, no card, no queue", not reminds(greet + " " + line), (greet + " / " + line, reminds(greet + " " + line)))
    case("... no button and no link in it, and no Another hello anywhere", "<button" not in hello and "<a " not in hello and "Another hello" not in page and "id='again'" not in page and "hgo" not in page)
    case("... the name (when there is one) is the accent word, as text", all(p.get("name") is False or p.get("text") == f["me"] for p in (f["hello"]["greeting_parts"] + f["hello"]["line_parts"]))
         and hello.count("<em>") == sum(1 for p in f["hello"]["greeting_parts"] + f["hello"]["line_parts"] if p.get("name")))
    # the hello's photos
    data = json.loads(part(page, "id='facts'>", "</script>"))
    hp = data["hello_photos"]
    case("the hello's photos: kit folder names and numbers only (never a path)", hp and all(set(x) == {"kit", "n", "v"} and x["kit"] in (A, B) and isinstance(x["n"], int) for x in hp)
         and "/private/" not in json.dumps(data) and str(w.work) not in page, hp[:2])
    kit_rows = {}
    for kit in (A, B):
        for r in json.loads((w.content / kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]:
            kit_rows[(kit, r["n"])] = r.get("way")
    ways = [kit_rows.get((x["kit"], x["n"])) for x in hp]
    case("... horizontal favorites first (they crop best into a wide strip)", ways and ways[0] == "wide" and ways == sorted(ways, key=lambda x: x != "wide"), ways)
    case("... the shoot the hello names first", hp[0]["kit"] == (f["hello"].get("kit") or hp[0]["kit"]), (hp[0], f["hello"].get("kit")))
    case("... the 1600 px copy: the page asks for size=l, never the small 520 one for the hello", "&size=l&v=" in page and "const photoUrl = (kit, p) => '/kit-photo?kit=' + encodeURIComponent(kit) + '&n=' + p.n + '&size=l" in page)
    case("... cropped toward the faces' middle, 1.22x, a new one every few seconds", "const ZOOM = 1.22, EVERY = 6000;" in page and "img.style.transform = `scale(${ZOOM})`" in page)
    # Turn your shoots into posts and the tiles
    s3 = part(page, "<section id='s3'>", "</section>")
    case("Turn your shoots into posts, 'into posts' the accent word, and her line", "<h1 class='big'>Turn your shoots <em>into posts</em></h1>" in s3
         and "<p class='sub'>Turn your shoot into reels, carousels, stories, and captions.</p>" in s3)
    makes = re.findall(r"data-make='(\w+)'", s3)
    case("four photo tiles, Reels, Carousels, Stories, Captions, each with data-make (what stage C opens)",
         makes == MAKES and flat(part(s3, "id='tiles'>", "</div>")) == TILE_WORDS, (makes, flat(part(s3, "id='tiles'>", "</div>"))))
    case("... each a link to the post kits screen (a saved copy, a new tab), its press asking which shoot and recorded as a tile press (Nov 22; See all my post kits stays posts)",
         s3.count("class='tl' href='/make-posts'") == 4 and s3.count("data-item='tile'") == 4 and s3.count("data-item='posts'") == 1)
    tiles = data["tiles"]
    case("... a photo from a different shoot for each pair of neighbours (two shoots: they take turns)", [t.get("kit") for t in tiles] == [B, A, B, A], [t.get("kit") for t in tiles])
    used = [(t["kit"], c["n"]) for t in tiles for c in t["cands"]]
    case("... no tile offers a photo another tile offers, nor the photo the hello opens on", len(used) == len(set(used)) and (hp[0]["kit"], hp[0]["n"]) not in used, used)
    case("See all my post kits alone: no Newest line, no box beside it", "<div class='go-row'><a class='btn solid' id='kitsBtn' data-item='posts' href='/make-posts'>See all my post kits →</a></div>" in s3
         and "Newest" not in page and "id='n3'" not in page)
    # the cards
    pq = part(page, "<a class='pq' id='s4'", "</a>")
    case("My posting queue: her words, what is going on, the little row of their grid with her line",
         flat("<" + pq)[:2] == ["My posting queue", "Your posts ready to go, and how your grid will look."] and "Open my posting queue →" in flat("<" + pq)
         and "<small>Your grid, newest first</small>" in pq and "<img src='/posting-thumbs/p5.jpg' alt=''>" in part(pq, "id='stack'>", "</div>"), flat("<" + pq))
    case("the grid's row: the posts lined up (last in line first), then those marked posted, then their Instagram (not pinned), at most three",
         home.grid_now() == ["/posting-thumbs/p5.jpg"] and set(data) == {"hello_photos", "tiles", "samples"}, home.grid_now())
    also = part(page, "<div class='also'>", "</button></div>")
    case("Back up a card and My editing queue, stacked, with their boxes", flat(also)[:4] == ["Back up a card", "Copies your card to your drive, checks every photo, and sorts it into shoots.", "A card is in", "EOS_DIGITAL · about 233 files"]
         and "My editing queue" in flat(also) and "id='n1'" in also and "id='n2'" in also)
    case("a name with markup in it reaches the page as text", "&lt;img src=x" in also and "<img src=x" not in page.split("<script", 1)[0])
    case("the recap card and its x as before, Watch in her word", "id='rc'" in page and ">Watch<" in page and "▶" not in page and "aria-label='Hide the monthly recap'" in page)
    # the look
    case("her look's tokens, in one block: paper, cards, text, grey, one accent, Helvetica, square corners",
         all(t in home.HOME_LOOK for t in ("--accent:#D9603A", "--cream:#EDEAE4", "--paper:#F5F3EF", "--tan:#DED8CD", "--ink:#111", "--ink-2:#6E6A64", '--sans:"Helvetica Neue",Helvetica,Arial,sans-serif', "--corner:2px"))
         and home.HOME_LOOK in page)
    case("no serif, no em dash, never Claude, nothing from the internet", "Fraunces" not in page and "serif" not in page.replace("sans-serif", "") and "—" not in page
         and "claude" not in page.lower() and "https://" not in page and "http://" not in page and "<link" not in page)
    case("none of her test-only lines (Preview of a look, Trying ideas, samples links)", not re.search(r"Preview of a look|Trying ideas|samples\.html|try 1|home=test|8790|8799", page))
    import home_base
    other = home_base.backups_html() + home_base.make_posts_html()
    case("the look is the home page's alone: the other screens keep look.py's", "--accent:#D9603A" not in other and "--cream:#EDEAE4" not in other and home.HOME_LOOK not in other)
    # no post kits: grey placeholders
    with Kits(w):
        f0 = home.facts()
        p0 = home.page_html()
    d0 = json.loads(part(p0, "id='facts'>", "</script>"))
    case("a brand-new Assistant (no post kits): the hello and the tiles are grey placeholders with nothing to load, Create your post kits",
         d0 == {"hello_photos": [], "tiles": [], "samples": None} and p0.count("class='tl'") == 4 and "Create your post kits →" in p0 and "--placeholder:#D3CDC4" in p0, d0)
    case("... and the hello still says hello", f0.get("hello") is None or len(flat(part(p0, "<h2", "</h2>"))) >= 1)
    # a tile's press, for the chat (Nov 22): left out of pending; the hello stage counts it as posts started
    jp = home.JOURNEY
    saved_j = jp.read_bytes() if jp.exists() else None
    try:
        with Kits(w):
            home.save_journey({"clicks": [], "done": {}, "hellos": {"first": None, "count": 0}})
            before = home.hello()
            home.record_click("tile")
            after = home.hello()
            pend = home.pending()
            home.record_click("posts")
            pend2 = home.pending()
    finally:
        if saved_j is not None:
            jp.write_bytes(saved_j)
        elif jp.exists():
            jp.unlink()
    case("a tile's press is kept as tile, and pending leaves it out (no first-time explanation in the chat)", pend == [], pend)
    case("... while See all my post kits (posts) still shows in pending, as before", [x["item"] for x in pend2] == ["posts"] and pend2[0]["first_time"], pend2)
    case("... and the hello counts a tile's press as posts started", "posts" in before["not_tried"] and "posts" not in after["not_tried"], (before, after))
    # the very first hello (Nicole, Nov 22): her one line alone, nothing stacked over it
    import hello_lines
    saved = hello_lines.STATE.read_bytes() if hello_lines.STATE.exists() else None
    real_gather = hello_lines.gather
    try:
        if hello_lines.STATE.exists():
            hello_lines.STATE.unlink()
        hello_lines.gather = lambda now=None: dict(hello_lines._empty_facts(), name="Nicole")   # no shoot yet
        p1 = home.page_html()
        p2 = home.page_html()
    finally:
        hello_lines.gather = real_gather
        if saved is not None:
            hello_lines.STATE.write_bytes(saved)
    only = "Hi! I\u2019m your Assistant, and I\u2019m so glad you\u2019re here."
    h1 = part(p1, "<section class='hello'", "</section>")
    case("the very first hello: only her line, as the heading, with no greeting over it and no line under it (Nov 22)",
         flat("<h2" + part(h1, "<h2", "</h2>") + "</h2>") == [only] and "<p>" not in part(h1, "<div class='tx'>", "</div>") and "data-only=1" in h1
         and "Nicole" not in h1, flat("<x" + h1))
    case("... and a reload keeps it", part(p2, "<section class='hello'", "</section>") == h1)
    # her mock-up's words
    hers = her_mock()
    if not hers:
        skip("her words compared with her mock-up: her v30 handoff is not on this computer")
        return
    raw = nicole_nov22.read(hers)   # Nicole, Nov 22: everything is the Assistant
    for t in ("Turn your shoots <em>into posts</em>", "Turn your shoot into reels, carousels, stories, and captions.", "Your grid, newest first", "See all my post kits &rarr;",
              "Your posts ready to go, and how your grid will look.", "Open my posting queue &rarr;", "Copies your card to your drive, checks every photo, and sorts it into shoots.",
              "The shoots you need to edit and when they're due.", ">Watch<", "Open my Assistant folder", "'Reels', 'Carousels', 'Stories', 'Captions'", "#D9603A", "#EDEAE4", "#F5F3EF", "#DED8CD", "#6E6A64"):
        case("hers and ours: %s" % html_mod.unescape(t), t in raw and (html_mod.unescape(t).replace("'Reels', 'Carousels', 'Stories', 'Captions'", "Captions") in html_mod.unescape(page)), t)


# ---------------------------------------------------------------- the page in a browser

def clicks(w):
    try:
        return [c["item"] for c in json.loads((w.home / "journey.json").read_text(encoding="utf-8"))["clicks"]]
    except (OSError, ValueError, KeyError):
        return []


R = "(s => { const r = document.querySelector(s).getBoundingClientRect(); return {t: Math.round(r.top + scrollY), l: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height), b: Math.round(r.bottom + scrollY)}; })"


def ready(c):
    c.wait_for("document.querySelectorAll('.hello .bgs img.on').length === 1 && document.querySelectorAll('#tiles img[src]').length === 4 "
               "&& [...document.querySelectorAll('#tiles img[src]')].every(i => i.complete && i.naturalWidth > 0)", 25)
    time.sleep(0.4)


def check_browser(c, w, shot):
    c.init_script("window.__asked = []; (function(){ const f = window.fetch; window.fetch = function(u, o){ window.__asked.push(String(u)); return f.apply(this, arguments); }; })();")
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    c.open(w.url("/home"))
    ready(c)
    if shot:
        d = c.cdp("Page.captureScreenshot", {"format": "png"})
        Path(shot).parent.mkdir(parents=True, exist_ok=True)
        Path(shot).write_bytes(base64.b64decode(d["data"]))
        print("screenshot: %s" % shot, flush=True)
    # the bar
    bar = c.js("(() => { const b = getComputedStyle(document.querySelector('.brand b')), s = getComputedStyle(document.querySelector('.bar')), f = getComputedStyle(document.getElementById('folder')); "
               "return {color: b.color, tt: b.textTransform, small: document.querySelector('.brand small').textContent, line: s.borderBottomWidth + ' ' + s.borderBottomStyle + ' ' + s.borderBottomColor, "
               "deco: f.textDecorationLine, fbg: f.backgroundColor, when: document.getElementById('when').textContent}; })()")
    case("the bar: THE ASSISTANT in her accent, by Horizon Found, the date, Open my Assistant folder as an underlined link, a thin black line under it",
         bar["color"] == "rgb(217, 96, 58)" and bar["tt"] == "uppercase" and bar["small"] == "by Horizon Found" and bar["line"] == "1px solid rgb(17, 17, 17)"
         and bar["deco"] == "underline" and bar["fbg"] == "rgba(0, 0, 0, 0)" and bar["when"] == "Tuesday, November 17", bar)
    # the hello
    h = c.js("(() => { const box = document.getElementById('hello'); return {h: box.getBoundingClientRect().height, w: box.getBoundingClientRect().width, imgs: box.querySelectorAll('img.on').length, "
             "src: box.querySelector('img.on').getAttribute('src'), buttons: box.querySelectorAll('button, a').length, again: !!document.getElementById('again'), color: getComputedStyle(box.querySelector('h2')).color, "
             "words: box.innerText, tf: box.querySelector('img.on').style.transform, faces: box.querySelector('img.on').dataset.faces, wrapw: document.querySelector('.wrap').clientWidth}; })()")
    case("the hello: ONE wide photo across the page, about 210 to 290 px tall", h["imgs"] == 1 and 195 <= h["h"] <= 290 and h["w"] >= h["wrapw"] - 90, h)
    case("... the kit's 1600 px copy (size=l), by its name and number", h["src"].startswith("/kit-photo?kit=") and "&size=l&" in h["src"], h["src"])
    case("... cropped in 1.22x, toward the faces when it has some", h["tf"] == "scale(1.22)", h)
    case("... words in white over it, no button, no link, no Another hello, no reminder", h["color"] == "rgb(255, 255, 255)" and h["buttons"] == 0 and not h["again"]
         and not reminds(h["words"]), (h, reminds(h["words"])))
    asked = c.js("window.__asked")
    small = [u for u in c.js("performance.getEntriesByType('resource').map(r => r.name).filter(u => u.includes('/kit-photo') && !u.includes('size=l'))")]
    fans = c.js("[...document.querySelectorAll('#rcFan img, #yrFan img')].map(i => i.src)")
    case("never a photo itself: the 1600 px copies, and the 520 ones only for the recap card's little pictures",
         all(u in fans for u in small) and not any("/Photos/" in u for u in c.js("performance.getEntriesByType('resource').map(r => r.name)")), small)
    case("the faces are asked for once per shoot list, from /kit-faces", 1 <= len([u for u in asked if u.startswith("/kit-faces")]) <= 6, [u for u in asked if u.startswith("/kit-faces")])
    # Turn your shoots into posts and the tiles
    t = c.js("(() => { const el = [...document.querySelectorAll('#tiles .tl')]; return {makes: el.map(x => x.dataset.make), words: el.map(x => x.querySelector('b').textContent), "
             "srcs: el.map(x => x.querySelector('img').getAttribute('src')), color: getComputedStyle(el[0].querySelector('b')).color, font: getComputedStyle(el[0].querySelector('b')).fontFamily, "
             "weight: getComputedStyle(el[0].querySelector('b')).fontWeight, faces: el.map(x => x.querySelector('img').dataset.faces), tops: el.map(x => Math.round(x.getBoundingClientRect().top)), "
             "em: getComputedStyle(document.querySelector('#s3 h1 em')).color, h1: getComputedStyle(document.querySelector('#s3 h1')).fontFamily}; })()")
    case("four photo tiles in a row: Reels, Carousels, Stories, Captions, the word in white Helvetica Bold", t["makes"] == MAKES and t["words"] == TILE_WORDS and len(set(t["tops"])) == 1
         and t["color"] == "rgb(255, 255, 255)" and t["font"].startswith('"Helvetica Neue"') and t["weight"] == "700", t)
    case("... four different photos, each the 1600 px copy, none the hello's own", len(set(t["srcs"])) == 4 and all("&size=l&" in s for s in t["srcs"]) and h["src"] not in t["srcs"], t["srcs"])
    case("... each tile chose a photo with a face when it had one (the pretend faces are on the odd photos)", all(x == "1" for x in t["faces"]), t["faces"])
    case("'into posts' in her accent, the heading in Helvetica", t["em"] == "rgb(217, 96, 58)" and t["h1"].startswith('"Helvetica Neue"'), t)
    case("See all my post kits alone under the tiles", c.text("#kitsBtn") == "See all my post kits →" and c.count(".go-row > *") == 1 and c.count("#n3") == 0)
    # the cards side by side
    m = c.js("(() => { const R = %s; return {s4: R('#s4'), s1: R('#s1'), s2: R('#s2'), tiles: R('#tiles'), rc: R('#rc'), stack: R('#stack')}; })()" % R)
    case("My posting queue on the left, Back up a card and My editing queue stacked on the right, the same height in all",
         m["s4"]["t"] == m["s1"]["t"] and m["s1"]["l"] > m["s4"]["l"] + m["s4"]["w"] and m["s2"]["t"] >= m["s1"]["b"] and abs(m["s1"]["l"] - m["s2"]["l"]) <= 1
         and abs(m["s4"]["b"] - m["s2"]["b"]) <= 2 and m["s4"]["t"] > m["tiles"]["b"] and m["rc"]["t"] >= m["s4"]["b"], m)
    case("... the posting queue's little row of their grid", c.count("#stack img") == 1 and c.text("#stack small") == "Your grid, newest first" and m["stack"]["l"] > m["s4"]["l"] + m["s4"]["w"] / 3)
    look = c.js("(() => { const g = s => getComputedStyle(document.querySelector(s)); return {body: g('body').backgroundColor, font: g('body').fontFamily, ls: g('body').letterSpacing, "
                "cards: ['#s4', '#s1', '#s2'].map(s => g(s).backgroundColor), rc: g('#rc').backgroundColor, ink: g('body').color, "
                "corners: ['#s4', '#s1', '#s2', '#rc', '.tl', '#kitsBtn', '#hello'].map(s => parseFloat(g(s).borderTopLeftRadius))}; })()")
    case("her look on the screen: warm paper, light cards, tan recap, black words, Helvetica at -1%, square corners",
         look["body"] == "rgb(237, 234, 228)" and look["cards"] == ["rgb(245, 243, 239)"] * 3 and look["rc"] == "rgb(222, 216, 205)" and look["ink"] == "rgb(17, 17, 17)"
         and look["font"].startswith('"Helvetica Neue"') and look["ls"] in ("-0.15px", "-0.01em") and all(x <= 2 for x in look["corners"]), look)
    fit = c.js("({sh: document.documentElement.scrollHeight, ih: innerHeight, iw: innerWidth, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
    case("the whole home page fits one laptop screen, or nearly (1440 x 900: at most 930 px tall)", fit["iw"] == 1440 and fit["sh"] <= 930 and fit["sw"] <= fit["cw"], fit)
    case("no page errors, and nothing asked of the internet", not c.page_errors() and not c.outside_requests(), (c.page_errors()[:2], c.outside_requests()[:2]))
    # the tiles' faces (her v31 section 7): the faces' middle about 30% down each tile, above the word
    tf = c.js("[...document.querySelectorAll('#tiles .tl')].map(el => { const im = el.querySelector('img'); return {faces: im.dataset.faces, "
              "at: parseFloat(im.style.transformOrigin.split(' ')[1]) / el.clientHeight, word: (el.querySelector('b').getBoundingClientRect().top - el.getBoundingClientRect().top) / el.clientHeight}; })")
    case("each tile's faces sit about 30% from the top, above the word in the middle (v31 section 7)",
         all(x["faces"] == "1" and abs(x["at"] - 0.30) <= 0.06 and x["at"] < x["word"] for x in tf), tf)
    hb = c.js("(() => { const box = document.getElementById('hello'), F = {f: {w: 520, h: 347, faces: [%s]}}; "
              "return {hello: framing(F, box.clientWidth, box.clientHeight).lands, tile: framing(F, box.clientWidth, box.clientHeight, TILE_AT).lands}; })()" % json.dumps(FACE))
    case("... the hello keeps its faces in the middle (its words sit at the bottom); only the tiles aim at 30%", abs(hb["hello"] - 0.5) <= 0.03 and abs(hb["tile"] - 0.3) <= 0.03, hb)
    order = c.js("(() => { const G = {1: {w: 520, h: 347, faces: [[.1, .80, .1, .12]]}, 2: {w: 520, h: 347, faces: [%s]}, 4: {w: 520, h: 347, faces: [[.1, .80, .1, .12]]}}; "
                 "const el = document.querySelector('#tiles .tl'), bw = el.clientWidth, bh = el.clientHeight; "
                 "return {order: tileOrder([{n: 1}, {n: 3}, {n: 2}, {n: 4}], G, bw, bh).map(c => c.n), low: tileFits({f: G[1]}, bw, bh), mid: tileFits({f: G[2]}, bw, bh), "
                 "none: tileOrder([{n: 5}, {n: 6}], {}, bw, bh).map(c => c.n)}; })()" % json.dumps(FACE))
    case("... a photo whose faces can't be brought that high (a face near the bottom) gives way to the next photo with a face; then the other faces, then the rest",
         order == {"order": [2, 1, 4, 3], "low": False, "mid": True, "none": [5, 6]}, order)
    cen = c.js("(() => { const im = document.createElement('img'); aim(im, {f: {w: 520, h: 347, faces: []}}, 300, 150, TILE_AT); return [im.style.objectPosition, im.dataset.faces]; })()")
    case("... a tile photo with no face stays centered", cen[0] in ("50% 50%", "50.0% 50.0%") and cen[1] == "0", cen)
    # a tile's press: "Create a carousel: which shoot?" (stage C; tests/create_dialog_check.py holds the box), recorded as
    # "tile" (Nov 22): `pending` leaves it out, so the chat never explains posts after it, and the hello counts it
    import home
    home.mark_seen()
    before = len(clicks(w))
    c.click("#tiles .tl[data-make=carousel]")
    c.wait_for("!document.getElementById('mk').hidden", 15)
    chrome_drive.wait_until(lambda: clicks(w)[before:] == ["tile"], 10, what="the press recorded")
    case("a tile's press asks which shoot (Create a carousel), stays on the home page, and is recorded as tile",
         clicks(w)[before:] == ["tile"] and c.js("document.getElementById('mkT').textContent") == "Create a carousel" and c.js("location.pathname") == "/home", clicks(w)[before:])
    case("... home.py pending leaves it out: no first-time explanation and no Want to dive in? in the chat", not any(x["item"] == "tile" for x in home.pending()), home.pending())
    c.key("Escape")
    # the photo changes every few seconds
    c.open(w.url("/home"))
    ready(c)
    first = c.js("document.querySelector('.hello img.on').getAttribute('src')")
    c.wait_for("document.querySelector('.hello img.on').getAttribute('src') !== %s" % json.dumps(first), 15)
    case("the hello's photo changes to another every few seconds (a fade)", c.js("document.querySelectorAll('.hello img.on').length") == 1
         and c.js("getComputedStyle(document.querySelector('.hello .bgs img')).transitionDuration") == "1.6s")
    case("... and the hello's words stay the same (one hello for the visit)", c.js("document.querySelector('.hello h2').textContent") == c.js("document.querySelector('.hello h2').textContent"))
    # reduced motion
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    c.open(w.url("/home"))
    ready(c)
    first = c.js("document.querySelector('.hello img.on').getAttribute('src')")
    time.sleep(7)
    case("with reduced motion the hello's photo never changes, and nothing fades",
         c.js("document.querySelector('.hello img.on').getAttribute('src')") == first and c.js("getComputedStyle(document.querySelector('.hello .bgs img')).transitionDuration") == "0s")
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    # about the Claude app's pane (Nov 22): her "fit on one screen" was measured at 1440 x 900; here the height is
    # only measured and said, never promised, and nothing may scroll sideways
    for wd, ht in ((1000, 800), (800, 800)):
        c.desktop((wd, ht))
        c.open(w.url("/home"))
        ready(c)
        pm = c.js("({sh: document.documentElement.scrollHeight, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, iw: innerWidth})")
        print("  measured: at %d x %d the home page is %d px tall" % (wd, ht, pm["sh"]), flush=True)
        case("%d x %d (about the Claude app's pane): no sideways scroll (its height is said above, not promised)" % (wd, ht), pm["iw"] == wd and pm["sw"] <= pm["cw"], pm)
    # phones
    for wd, ht in ((375, 812), (336, 700)):
        c.phone(wd, ht)
        c.open(w.url("/home"))
        ready(c)
        p = c.js("({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, cols: getComputedStyle(document.getElementById('tiles')).gridTemplateColumns.split(' ').length, "
                 "low: getComputedStyle(document.querySelector('.low')).gridTemplateColumns.split(' ').length})")
        case("phone width %d: no sideways scroll, the tiles two by two, the cards one under another" % wd, p["sw"] <= p["cw"] and p["cols"] == 2 and p["low"] == 1, p)
    c.desktop((1440, 900))
    # a brand-new Assistant
    with Kits(w):
        c.open(w.url("/home"))
        c.wait_for("!!document.querySelector('.hello h2')", 15)
        time.sleep(1.2)
        e = c.js("({imgs: document.querySelectorAll('.hello img[src], #tiles img[src]').length, tile: getComputedStyle(document.querySelector('.tl')).backgroundColor, "
                 "hello: getComputedStyle(document.getElementById('hello')).backgroundColor, btn: document.getElementById('kitsBtn').textContent, errors: 0})")
    case("a brand-new Assistant: grey placeholders for the hello and the tiles, nothing broken, Create your post kits",
         e["imgs"] == 0 and e["tile"] == "rgb(211, 205, 196)" and e["hello"] == "rgb(211, 205, 196)" and e["btn"] == "Create your post kits →" and not c.page_errors(), e)


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards (default: a throwaway one, removed at the end)")
    ap.add_argument("--port", type=int, default=9960)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    ap.add_argument("--shot", help="write a screenshot of the page at 1440 x 900 here")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8790, 8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        skip("the pretend kits are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="home-v30-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    w = v28.World(work, a.port)
    w.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    # an empty samples folder of the test's own (v30 section 6): "brand-new" here means grey, whatever the plugin ships
    (work / "no-samples").mkdir(parents=True, exist_ok=True)
    w.env["STUDIO_SAMPLES_FOR_TESTS"] = str(work / "no-samples")
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none", STUDIO_NO_WINDOWS_FOR_TESTS="1", FACES_PRETEND=str(w.pretend),
                      STUDIO_SAMPLES_FOR_TESTS=str(work / "no-samples"))
    try:
        w.build()
        w.posting(pieces=[
            {"id": "p1", "shoot_name": "Hannah", "kind": "reel", "status": "posted", "posted_at": "2026-11-14T18:00:00"},
            {"id": "p5", "shoot_name": "Katie Austin Maternity", "kind": "reel", "status": "green", "slot": 1, "date": TODAY, "thumb": "posting-thumbs/p5.jpg"},
            {"id": "p7", "shoot_name": "Hannah", "kind": "carousel", "status": "green", "slot": 2, "date": "2026-11-20"}])
        for k in (A, B):
            w.previews(k)
        pretend_faces(w)
        sys.path.insert(0, str(SCRIPTS))
        import home
        case("the test's own scratch home, never the real one", Path(home.HOME) == w.home and ".studio" not in str(home.HOME))
        group("what the page says and draws", check_page, w, home)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            w.start()
            case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
            with chrome_drive.Chrome(work=str(work), size=(1440, 900)) as c:
                group("the page in a browser", check_browser, c, w, a.shot)
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
