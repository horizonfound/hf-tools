#!/usr/bin/env python3
"""Checks for what the second pair of reviewers of the carousel designer found: does the page match what
Nicole's did, and can a person who knows nothing work out what to do from what is on the screen.

Run as part of tests/design_check.py (--only screen runs just this part: the page server on port + 16).
DESIGN_SCREEN_PARTS=lines,keys,overhang,bubble,font limits the real-browser half to those parts.

Every case here failed before its fix (or fails with the fix taken out). What must hold:

  * every line the page says by itself (a design changed somewhere else, the photos changed, a save refused,
    "That design isn't here") is INSIDE the window at the pane's usual size, with Reload beside it, and the
    place beside the design's name never goes blank
  * no line that arrives by itself moves a button: the save status is one fixed size, and the long sentences
    are in the bar at the bottom of the window
  * words that run past their own box and over a seam are on the next slide when saved, as on screen
  * Save slides asks before it saves words the Assistant put there ("Your words here", a starter's "Your title")
  * a second "+ Add text" goes under the first, never on top of it
  * the folder button's answer stays inside the window, never covers the save line, and goes at the next press
  * "+ New design" gives up with a plain line when the Assistant does not answer, and a press that was given
    up on never makes a design later by itself
  * everything on the strip can be reached and selected with the Tab key and says what it is; the greyed
    buttons for a selected thing are not Tab stops
  * a design saved again is "<name> (2)", never "<name> 1 2"
  * design.py open says whether the design is new, and the instructions give Claude a line for each
  * "Profile grid crop" says what it shows, in words on the page, while it is on
  * a set saved while a font was missing is saved again once the font loads (needs the internet)
  * a canvas measures a script font's line as wide as the page draws it (Caveat; needs the internet)

It needs Pillow (it reads saved slides) and Chrome. It makes its own pretend kit in the work folder, points
STUDIO_HOME at it, never opens Finder (the folder button's request is answered inside the page), and stops
every server it starts.
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
PARTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "parts"
APPLE = "/usr/bin/python3"
W, H = 1080, 1350

# The folder button's request never reaches Finder: it is answered here, in the page, with whatever the test
# put in window.__openAnswer. One request can also be held back until the test says go.
NO_FINDER_JS = r"""
(function(){
  var real = window.fetch;
  window.__opens = [];
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) {
      window.__opens.push(String(u));
      return Promise.resolve(new Response(JSON.stringify(window.__openAnswer || {ok: true, words: 'Opened Carousel in Finder.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    return real.apply(this, arguments);
  };
})();
"""

BEHIND = "Opened Carousel in Finder, behind this window. Click Finder in the Dock to see it."


def check_screen_page(case, work):
    """What can be read from the files themselves, with no browser."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    import design
    import design_page
    page = design_page.page_html("A kit")
    bar = page[page.index("id='savebar'"):]
    case("screen: the page's own lines (#d-note, #d-trouble, #grid-line) are written inside the bar at the bottom of the window, above its buttons",
         all(bar.find(f"id='{i}'") > 0 for i in ("d-note", "d-trouble", "grid-line")) and bar.index("id='d-note'") < bar.index("id='preview-btn'")
         and page.count("id='d-note'") == 1)
    case("screen: the save status beside the name is one fixed width that cannot wrap",
         re.search(r"\.savestate\{[^}]*width:\d+px[^}]*white-space:nowrap", design_page.DESIGN_CSS) is not None)
    case("screen: the strip's Size slider (Smaller / Bigger before Nov 6) is told apart from a text box's Size by its name for a screen reader",
         "<span class='lbl'>View</span>" not in page and "id='view-size'" in page and "aria-label='How big the slides look'" in page)
    case("screen: a design saved again is '<name> (2)'", design.SET_AGAIN.format(base="Beach carousel 1", k=2) == "Beach carousel 1 (2)"
         and design.safe_base("Beach carousel 1 (2)") == "Beach carousel 1 (2)")
    long_name = "A very long shoot name about the Garcia family sunset session by the water in June"
    first = design.next_name(long_name, [])
    stem = first[:-len(" carousel 1")]
    case("screen: a long shoot name is cut at the end of a word in the first design's name",
         first.endswith(" carousel 1") and len(first) <= design.NAME_MAX and long_name.startswith(stem + " "), first)
    case("screen: a short shoot name is kept whole", design.next_name("Garcia family", []) == "Garcia family carousel 1")
    one_word = design.next_name("Supercalifragilistic" * 6, [])
    case("screen: a name with no space in it is still cut to fit", one_word.endswith(" carousel 1") and len(one_word) <= design.NAME_MAX, one_word)
    case("screen: the words about a photo exported again no longer point to a Reload 'at the top of this page'",
         "at the top" not in design.PHOTO_NEWER and "Press Reload, then Save slides again." in design.PHOTO_NEWER)
    arr = (PARTS / "arrange.md").read_text(encoding="utf-8")
    case("screen: the instructions give Claude two opening lines, keyed to what design.py open prints (NEW: / THEIRS:)",
         "`NEW:`" in arr and "`THEIRS:`" in arr and "just as you left it" in arr
         and 'Never Chrome. Then say: "The designer is on the page beside us' not in arr)
    case("screen: the instructions name a second save the way the files are named", '("Beach carousel 1 (2)")' in arr and '"Beach carousel 1 2"' not in arr)
    import design_js_save
    import design_js_text
    case("screen: the folder button's answer is no wider than its button at a usual width, and wraps",
         re.search(r"\.sv-bub\{[^}]*left:0;right:0[^}]*white-space:normal", design_js_save.DESIGN_SAVE_CSS) is not None
         and "width:max-content;max-width:320px" not in design_js_save.DESIGN_SAVE_CSS)
    case("screen: a canvas is told to shape words as the page does (a script font's joins across a space)",
         "ctx.textRendering = 'optimizeLegibility'" in design_js_text.DESIGN_TEXT_JS)


def check_screen_browser(case, work, port, make_kit, Server, post, get_json, run):
    import chrome_drive as cd
    try:
        from PIL import Image
    except ImportError:
        Image = None
    if not cd.find_chrome():
        print("SKIP  no Chrome on this computer: the reviewers' screen findings were not checked in a real page", flush=True)
        return
    target = work / "screen"
    ok, out = make_kit(target, "Screen lake", 14)
    if not case("screen browser: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Screen lake"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs = kit / ".kit" / "designs"
    car = kit / "Carousel"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    nums = [x["n"] for x in sheet]
    scratch = work / "chrome-screen"
    scratch.mkdir(parents=True, exist_ok=True)
    toks = [0]

    def frame(i, n, k):
        return {"id": i, "n": n, "x": k * W, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}

    def text(i, words, x, y, **more):
        b = {"id": i, "type": "text", "text": words, "font": "Inter", "size": 96, "weight": 400, "italic": False, "upper": False,
             "al": "center", "ls": 0, "lh": 1.15, "color": "#2a2622", "x": x, "y": y, "w": 820, "h": 110.4}
        b.update(more)
        return b

    # --- the command for Claude: is the design new, or theirs? (before any page has made one) ---
    srv = Server(env, port)
    P = srv.start()
    try:
        code, out1 = run(env, "design.py", "open", kit_name)
        lines1 = [ln for ln in out1.splitlines() if ln.strip()]
        case("design.py open on a shoot with no design: the line above the address starts NEW:",
             code == 0 and len(lines1) >= 3 and lines1[-2].startswith("NEW:") and lines1[-1].startswith("http://127.0.0.1:") and "1 design for this shoot" in out1, out1[-400:])
        code, out2 = run(env, "design.py", "open", kit_name)
        lines2 = [ln for ln in out2.splitlines() if ln.strip()]
        case("design.py open again: the same design, and the line starts THEIRS: (so Claude never says 'one photo on each slide' of a design they worked on)",
             code == 0 and len(lines2) >= 3 and lines2[-2].startswith("THEIRS:") and lines2[-1] == lines1[-1], out2[-400:])
        first_id = sorted(p.stem for p in designs.glob("*.json") if ".prev" not in p.name)[0]

        def new_design(state, name):
            toks[0] += 1
            code, out = post(P, "/design-new", {"kit": kit_name, "token": f"screencheck{toks[0]:04d}", "state": state, "name": name})
            assert code == 200 and out.get("ok"), (code, out)
            return out["design"]["id"]

        def disk(i):
            return json.loads((designs / f"{i}.json").read_text(encoding="utf-8"))

        def in_car(prefix=""):
            return sorted(n for n in os.listdir(car) if n.startswith(prefix)) if car.is_dir() else []

        def session(size, body):
            with cd.Chrome(work=scratch, size=size) as c:
                c.init_script(NO_FINDER_JS)
                body(c)

        base = [f"http://127.0.0.1:{P}"]

        class Page:
            """The small things every part below asks of the page."""
            def __init__(self, c):
                self.c = c

            def J(self, expr):
                return json.loads(self.c.js("JSON.stringify(" + expr + ")"))

            def open(self, did=None):
                self.c.open(f"{base[0]}/design.html?kit={KQ}" + (f"&design={did}" if did else ""))
                self.c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 25,
                                tell="document.body.innerText.slice(0, 300)")
                try:
                    self.c.wait_for("Designer.st.blocks.every(function(b){ return b.type !== 'text' || Designer.type.status(b) !== 'wait'; }) && Designer.type.fit(Designer.st) === Designer.st", 12)
                except cd.Timeout:
                    pass

            def saved(self, seconds=12):
                try:
                    self.c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                    return True
                except cd.Timeout:
                    return False

            def press_save(self, seconds=90):
                self.c.click("#save-slides")
                self.c.wait_for("!Designer.saver.busy() || Designer.saver.asking()", seconds, tell="document.getElementById('save-line').textContent")
                return self.c.text("#save-line")

            def in_window(self, selector):
                """Is this element showing, wholly inside the window, and the thing on top at its own middle?"""
                return self.c.js("(function(e){ if (!e || e.hidden || !e.offsetParent) return false; var r = e.getBoundingClientRect();"
                                 " if (!(r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth)) return false;"
                                 " var t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!t && (t === e || e.contains(t)); })(document.querySelector(%s))" % json.dumps(selector))

            def places(self, *ids):
                """Where these are in the window (to ask: did a line's coming move anything?)."""
                return self.J("[%s].map(function(i){ var r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10]; })"
                              % ", ".join(json.dumps(i) for i in ids))

        FIXED = ("new-design", "stage", "slides-plus", "preview-btn", "gridcrop", "save-slides")

        # =====================================================================================================
        # 1. the pane's usual size (900 x 800): every line the page says by itself is in sight
        # =====================================================================================================
        def part_lines(c):
            p = Page(c)
            p.open("zzzz9")                 # an address naming a design that is not there
            p.saved()
            case("900 x 800: 'That design isn't here, so this is your newest one.' is inside the window",
                 c.text("#d-note span") == "That design isn’t here, so this is your newest one." and p.in_window("#d-note"), (c.text("#d-note"), c.rect("#d-note")))
            c.js("window.scrollTo(0, document.documentElement.scrollHeight)")
            case("900 x 800: ...and still is with the page scrolled to its end", p.in_window("#d-note"), c.rect("#d-note"))
            c.js("window.scrollTo(0, 0)")

            # ---- the four words the place beside the name ever holds all fit in it ----
            fits = p.J("['saved', 'saving', 'notSaved', 'needsReload'].map(function(k){ var s = document.getElementById('d-status'), was = s.textContent; s.textContent = Designer.WORDS[k];"
                       " var ok = s.scrollWidth <= s.clientWidth; s.textContent = was; return ok; })")
            case("the place beside the name is wide enough for each short word it holds (Saved, Saving..., Not saved, Needs reload)", fits == [True] * 4, fits)

            # ---- a second + Add text goes under the first; with nothing selected the first is on the first slide in sight ----
            D = new_design({"slides": 4, "bg": "#ffffff", "blocks": [frame(i + 1, nums[i], i) for i in range(4)]}, "Two texts")
            p.open(D)
            p.saved()
            c.click("#add-text")
            a = p.J("Designer.selected()")
            case("+ Add text with nothing selected and the strip at its start: the box is on slide 1 (the first slide in sight)",
                 a and a["type"] == "text" and 0 <= a["x"] and a["x"] + a["w"] <= W, a)
            c.click("#add-text")
            b = p.J("Designer.selected()")
            case("a second + Add text: the new box is under the first, not on top of it",
                 b and b["id"] != a["id"] and b["x"] == a["x"] and abs(b["y"] - (a["y"] + a["h"])) < 0.02, (a, b))
            c.click("#add-text")
            d3 = p.J("Designer.selected()")
            case("a third goes under the second", d3 and abs(d3["y"] - (b["y"] + b["h"])) < 0.02 and d3["x"] == a["x"], d3)
            tops = sorted(x["y"] for x in p.J("Designer.st.blocks") if x.get("type") == "text")
            case("no two text boxes share a spot", len(tops) == 3 and len(set(tops)) == 3, tops)
            p.saved()

            # ---- Save slides asks before saving words the Assistant put there ----
            before = in_car()
            line = p.press_save()
            asked = c.js("Designer.saver.asking()")
            case("Save slides with untouched 'Your words here' boxes: it asks, in the page, before anything is saved",
                 asked and line == "3 text boxes still say the words they started with (slide 1). They will be saved like that."
                 and c.js("!document.getElementById('save-yes').hidden") and in_car() == before, (asked, line))
            case("...and the question is inside the window, with its two answers", p.in_window("#save-line") and p.in_window("#save-yes") and p.in_window("#save-no"))
            c.click("#save-no")
            case("Go back: nothing was saved", not c.js("Designer.saver.asking()") and in_car() == before and c.text("#save-line") == "")
            # they write their own words in two of the three, and take the third off
            for bid, words in ((a["id"], "The Garcias"), (b["id"], "a windy morning")):
                c.js(f"Designer.select({bid})")
                c.click("#t-words")
                c.key("Mod+A")
                c.type_text(words)
            p.saved()
            line = p.press_save()
            case("with one stand-in left the question names the words and the slide",
                 c.js("Designer.saver.asking()") and line == "The text on slide 1 still says “Your words here”, the words it started with. It will be saved like that.", line)
            c.click("#save-no")
            c.js(f"Designer.select({d3['id']})")
            c.key("Delete")
            p.saved()
            line = p.press_save()
            name1 = "Two texts"
            case("with their own words on every box there is no question, and the slides are saved",
                 not c.js("Designer.saver.asking()") and line == f"Saved 4 slides in your Carousel folder, named \"{name1}\". Nothing was replaced."
                 and in_car(name1 + " - ") == [f"{name1} - slide {i:02d}.jpg" for i in range(1, 5)], (line, in_car(name1)))

            # ---- the folder button's answer ----
            c.js("window.__openAnswer = {ok: true, words: %s}" % json.dumps(BEHIND))
            line_before = c.text("#save-line")
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            geo = p.J("(function(){ var b = document.getElementById('open-line').getBoundingClientRect(), s = document.getElementById('save-line').getBoundingClientRect();"
                      " return {bub: [b.left, b.top, b.right, b.bottom], line: [s.left, s.top, s.right, s.bottom], doc: document.documentElement.scrollWidth, win: document.documentElement.clientWidth}; })()")
            bub, ln = geo["bub"], geo["line"]
            apart = bub[2] <= ln[0] or bub[0] >= ln[2] or bub[3] <= ln[1] or bub[1] >= ln[3]
            case("900 wide: the folder button's answer is whole inside the window and the page does not scroll sideways",
                 c.text("#open-line") == BEHIND and bub[0] >= 0 and bub[2] <= geo["win"] and bub[1] >= 0 and geo["doc"] <= geo["win"], geo)
            case("900 wide: the answer does not cover the line that names the saved set", apart and c.text("#save-line") == line_before and p.in_window("#save-line"), geo)
            case("the request was for this kit's Carousel folder, and Finder was never asked for real",
                 p.J("window.__opens") == [f"/open?kit={quote(kit_name, safe='')}&sub=Carousel"], p.J("window.__opens"))
            c.click("#gridcrop")
            case("the answer goes at the next press anywhere else", c.text("#open-line") == "")
            c.click("#gridcrop")
            c.js("window.__openAnswer = {ok: false, words: \"Couldn't open Finder. The folder is /Volumes/Somewhere/The Assistant/Your Content/Shoot/Carousel. (no Finder)\"}")
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            said = c.text("#open-line")
            case("a failure that spells out where the folder is on the computer is said in the page's own words, with no path",
                 said == "Couldn’t open the folder from here. Ask Claude to open your Carousel folder." and "/" not in said, said)
            c.key("Escape")
            case("...and a key takes the answer away too", c.text("#open-line") == "")

            # ---- a design saved again ----
            c.click("#g-bg .sw[data-c='#f4efe6']")
            p.saved()
            line = p.press_save()
            case("the same design saved again after a change is '<name> (2)'",
                 line == f"Saved 4 slides in your Carousel folder, named \"{name1} (2)\". Nothing was replaced."
                 and in_car(name1 + " (2) - ") == [f"{name1} (2) - slide {i:02d}.jpg" for i in range(1, 5)] and len(in_car(name1 + " - ")) == 4, (line, in_car()))
            # ---- a new name is a change, in the real page ----
            c.click("#d-name-box")
            c.key("Mod+A")
            c.type_text("Garcia family")
            c.key("Enter")
            p.saved()
            line = p.press_save()
            case("renamed, then Save slides: the slides are saved under the new name (not 'Already saved' under the old one)",
                 line == "Saved 4 slides in your Carousel folder, named \"Garcia family\". Nothing was replaced." and len(in_car("Garcia family - ")) == 4, line)

            # ---- Profile grid crop says what it shows ----
            c.js("window.scrollTo(0, 0)")
            p0 = p.places(*FIXED)
            c.click("#gridcrop")
            crop = p.J("(function(){ var e = document.querySelector('.sv-crop.sv-l'), s = getComputedStyle(e); return {on: e.classList.contains('on'), img: s.backgroundImage, w: e.getBoundingClientRect().width}; })()")
            case("Profile grid crop, ticked: one line in the window says what the striped edges are",
                 c.text("#grid-line") == "Your profile grid shows the first slide a little narrower. The striped edges on slide 1 are what it leaves out." and p.in_window("#grid-line"), c.text("#grid-line"))
            case("...the edges are striped, not a faint tint", crop["on"] and "repeating-linear-gradient" in crop["img"] and crop["w"] > 3, crop)
            case("...and the line's coming moved no button", p.places(*FIXED) == p0, (p0, p.places(*FIXED)))
            c.click("#gridcrop")
            case("unticked: the line goes", c.js("document.getElementById('grid-line').hidden") and not c.js("document.querySelector('.sv-crop.sv-l').classList.contains('on')"))

            # ---- changed somewhere else: the line is in the window ----
            d0 = disk(D)
            theirs = json.loads(json.dumps(d0["state"]))
            theirs["bg"] = "#111111"
            code, out = post(P, "/design", {"kit": kit_name, "design": D, "stamp": c.js("Designer.S.stamp"), "base": d0["rev"], "page": "anotherwindow7", "state": theirs})
            case("changed elsewhere: (another window saved a change to this design)", code == 200 and out.get("ok"), (code, out))
            p0 = p.places(*FIXED)
            c.click("#slides-plus")
            try:
                c.wait_for("!document.getElementById('d-note').hidden", 8)
            except cd.Timeout:
                pass
            case("900 x 800: 'This design was changed somewhere else. Here's the newest.' is inside the window",
                 c.text("#d-note span") == "This design was changed somewhere else. Here's the newest." and p.in_window("#d-note") and p.J("Designer.st.bg") == "#111111", c.text("#d-note"))
            case("...and its coming moved no button", p.places(*FIXED) == p0, (p0, p.places(*FIXED)))

            # ---- the Assistant not answering: the status keeps its size, the sentence is in the bar ----
            p0 = p.places(*FIXED)
            srv.stop()
            c.click("#g-bg .sw[data-c='#ffffff']")
            try:
                c.wait_for("document.getElementById('d-trouble').textContent === 'Not saved yet. Trying again...'", 10)
                said = True
            except cd.Timeout:
                said = False
            case("no answer from the Assistant: beside the name it says 'Not saved', and the whole sentence is in the bar at the bottom, inside the window",
                 said and c.text("#d-status") == "Not saved" and p.in_window("#d-trouble"), (c.text("#d-status"), c.text("#d-trouble")))
            case("...and nothing moved: not '+ New design', not the strip, not a button (the line used to wrap the top row)", p.places(*FIXED) == p0, (p0, p.places(*FIXED)))

            # ---- + New design while the Assistant is away ----
            n_before = len([q for q in designs.glob("*.json") if ".prev" not in q.name])
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden && document.querySelectorAll('#gallery button.dz-use').length > 0", 8)
            c.js("document.querySelector('#gallery button.dz-use').click()")
            making = c.text("#gallery-line") if c.js("!!document.getElementById('gallery-line')") else c.js("document.querySelector('#gallery .dz-say').textContent")
            case("+ New design with the Assistant away: (it says it is making one)", making == "Making your new design...", making)
            c.key("Escape")
            case("the gallery closed while it waits: the press is given up on, and Duplicate design and + New design work again",
                 c.js("document.getElementById('gallery').hidden") and not c.js("document.getElementById('dup-design').disabled") and not c.js("document.getElementById('new-design').disabled"))
            # a second try is left to run out by itself
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden && document.querySelectorAll('#gallery button.dz-use').length > 0", 8)
            c.js("document.querySelector('#gallery button.dz-use').click()")
            t0 = time.time()
            try:
                c.wait_for("document.querySelector('#gallery .dz-say').textContent.indexOf('no new design was made') > 0", 30)
                gave = True
            except cd.Timeout:
                gave = False
            took = time.time() - t0
            case("left alone, it gives up with a plain line (it used to say 'Making your new design...' for as long as the Assistant was away)",
                 gave and 15 <= took <= 28 and c.js("document.querySelector('#gallery .dz-say').textContent")
                 == "Can’t reach the Assistant right now, so no new design was made. Your open design is still here. Try again in a moment.", (gave, round(took, 1)))
            c.key("Escape")
            srv2 = Server(env, P)
            got = srv2.start()
            holder[0] = srv2
            if got == P:
                case("when the Assistant is back the open design's change saves by itself", p.saved(20) and disk(D)["state"]["bg"] == "#ffffff")
                time.sleep(3.0)
                n_after = len([q for q in designs.glob("*.json") if ".prev" not in q.name])
                case("...and NO design appears by itself from the presses that were given up on; the same design is still open",
                     n_after == n_before and c.js("Designer.design.id") == D and c.js("document.getElementById('gallery').hidden"), (n_before, n_after))
                case("...and the sentence in the bar has gone, moving nothing", c.js("document.getElementById('d-trouble').hidden") and p.places(*FIXED) == p0)
            else:
                base[0] = f"http://127.0.0.1:{got}"
                print(f"SKIP  the page server could not take port {P} again (it took {got}); what happens when the Assistant is back could not be watched", flush=True)
                return

            # ---- the photos change under the open page ----
            c.js("window.scrollTo(0, 0)")
            src = sorted((kit / "Photos").glob("*.jpg"))[0]
            shutil.copy(src, kit / "Photos" / "zz-one-more.jpg")
            r = subprocess.run([APPLE, str(SCRIPTS / "kit.py"), "sheet", kit_name], env=env, capture_output=True, text=True, timeout=120)
            case("photos changed: (a photo was added to the shoot and its photos numbered again)", r.returncode == 0, r.stderr[-200:])
            p0 = p.places(*FIXED)
            c.click("#slides-plus")
            try:
                c.wait_for("Designer.blocked === true", 8)
            except cd.Timeout:
                pass
            case("photos changed, 900 x 800: the words AND the Reload button are inside the window",
                 c.js("Designer.blocked") is True and c.text("#d-note span") == "The photos in this shoot changed since this page opened."
                 and p.in_window("#d-note") and p.in_window("#d-reload"), (c.text("#d-note"), c.rect("#d-reload")))
            case("...the place beside the design's name says 'Needs reload' (it used to go blank)", c.text("#d-status") == "Needs reload" and c.js("document.getElementById('d-status').classList.contains('bad')"), c.text("#d-status"))
            case("...and nothing moved when the line came", p.places(*FIXED) == p0, (p0, p.places(*FIXED)))
            off = p.J("['add-text', 'save-slides', 'slides-plus', 'slides-minus', 'undo', 'new-design', 'dup-design', 'save-template'].map(function(i){ return document.getElementById(i).disabled; })")
            case("...every button that can no longer do anything is greyed (+ Add text and + New design used to look live and do nothing)", off == [True] * 8, off)
            c.js("window.scrollTo(0, document.documentElement.scrollHeight)")
            case("...scrolled to the end of the page, Reload is still inside the window", p.in_window("#d-reload"))
            c.click("#d-reload")
            c.wait_for("window.Designer && Designer.S && Designer.st && Designer.blocked === false && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 25)
            case("Reload: the page works again, with the shoot's photos as they are now",
                 c.js("Designer.S.total") == len(sheet) + 1 and c.js("document.getElementById('d-note').hidden") and p.saved(), c.js("Designer.S.total"))

        holder = [srv]
        # DESIGN_SCREEN_PARTS=lines,keys,overhang,bubble,font runs only those (for trying one fix at a time)
        only = [x.strip() for x in os.environ.get("DESIGN_SCREEN_PARTS", "").split(",") if x.strip()]

        def wanted(name):
            return not only or name in only
        if wanted("lines"):
            session((900, 800), part_lines)
        srv = holder[0]

        # =====================================================================================================
        # 2. the keyboard
        # =====================================================================================================
        def part_keys(c):
            p = Page(c)
            D = new_design({"slides": 3, "bg": "#ffffff", "blocks": [frame(1, nums[0], 0), frame(2, nums[1], 1), dict(frame(3, None, 2)), text(4, "The Garcias", 130, 500)]}, "Keys")
            p.open(D)
            p.saved()
            names = p.J("Array.from(document.querySelectorAll('#strip .blk')).map(function(e){ return [e.tabIndex, e.getAttribute('role'), e.getAttribute('aria-label')]; })")
            case("everything on the strip is a Tab stop and says what it is",
                 names == [[0, "button", f"Photo {nums[0]} on slide 1"], [0, "button", f"Photo {nums[1]} on slide 2"], [0, "button", "Empty frame on slide 3"], [0, "button", "Text on slide 1: The Garcias"]], names)
            inert = p.J("Array.from(document.querySelectorAll('#selbar .needsel')).map(function(g){ return g.inert === true; })")
            case("with nothing selected, the groups of buttons for a selected thing are out of the Tab key's way (they used to be 14 live stops that did nothing)",
                 len(inert) >= 3 and all(inert), inert)
            c.js("document.body.focus(); window.scrollTo(0, 0)")
            seen, hit = [], None
            for _ in range(80):
                c.key("Tab")
                where = p.J("(function(a){ return {id: a.id || '', cls: a.className || '', blk: a.classList.contains('blk') ? Number(a.dataset.id) : null, greyed: !!(a.closest && a.closest('#selbar .needsel'))}; })(document.activeElement)")
                seen.append(where)
                if where["blk"] is not None:
                    hit = where
                    break
            case("the Tab key reaches a photo on the strip without stopping on a greyed button on the way",
                 hit is not None and not any(s["greyed"] for s in seen), [s["id"] or s["cls"] for s in seen][-6:])
            case("...and reaching it selects it (its buttons now work)", hit is not None and c.js("Designer.sel") == hit["blk"]
                 and not any(p.J("Array.from(document.querySelectorAll('#selbar .needsel')).filter(function(g){ return !g.hidden; }).map(function(g){ return g.inert === true; })")))
            x0 = p.J("Designer.selected().x")
            c.key("ArrowRight")
            case("the arrow keys then move it", p.J("Designer.selected().x") > x0)
            c.key("Mod+Z")
            # on to the text box, and Return puts the cursor in its words
            for _ in range(6):
                if p.J("document.activeElement.dataset && document.activeElement.dataset.kind") == "text":
                    break
                c.key("Tab")
            case("Tab reaches the text box and selects it", p.J("Designer.selected().type") == "text" and c.js("Designer.sel") == 4)
            c.key("Enter")
            case("Return on a text box puts the cursor in its words", c.js("document.activeElement.id") == "t-words")
            case("the help line for a text box in its own font is the plain one", c.text("#selhint").startswith("Text. Type in the box"))
            p.saved()

        if wanted("keys"):
            session((900, 800), part_keys)

        # =====================================================================================================
        # 3. words that run past their own box and over a seam
        # =====================================================================================================
        def part_overhang(c):
            p = Page(c)
            blocks = [frame(i + 1, nums[i], i) for i in range(4)]
            # white slides to read the ink on: frames only on slides 1 and 2
            blocks = blocks[:2] + [text(9, "W", 3150, 300, font="Inter", size=400, weight=700, w=80, h=460, color="#000000")]
            D = new_design({"slides": 4, "bg": "#ffffff", "blocks": blocks}, "Overhang")
            p.open(D)
            p.saved()
            ink = p.J("(function(){ var L = Designer.type.layout(Designer.st.blocks[2]), b = Designer.st.blocks[2]; return {lo: b.x + L.lines[0].x, hi: b.x + L.lines[0].x + L.lines[0].w, status: Designer.type.status(b)}; })()")
            case("overhang: (the big W is in its own font and runs from slide 3 over the seam onto slide 4 on screen)", ink["status"] == "ready" and ink["lo"] < 3 * W - 20 and ink["hi"] > 3 * W + 60, ink)
            line = p.press_save()
            if c.js("Designer.saver.asking()"):         # slides 3 and 4 hold only words: the bare-slide question does not come, but be ready for one
                c.click("#save-yes")
                c.wait_for("!Designer.saver.busy()", 60)
                line = c.text("#save-line")
            files = in_car("Overhang - ")
            case("overhang: the slides were saved", len(files) == 4 and line.startswith("Saved 4 slides"), (line, files))
            if Image is None or len(files) != 4:
                return

            def dark(name, x0, x1):
                im = Image.open(car / name).convert("L")
                box = im.crop((x0, 250, x1, 800))
                return sum(1 for v in box.getdata() if v < 90)
            left3, right3, left4 = dark(files[2], 0, 100), dark(files[2], W - 90, W), dark(files[3], 0, int(ink["hi"] - 3 * W))
            case("overhang: slide 3 has the part of the letter that is on it", right3 > 500 and left3 == 0, (left3, right3))
            case("overhang: slide 4 has the part of the letter that runs onto it (it used to be left off the saved slide)", left4 > 500, left4)
            beyond = dark(files[3], int(ink["hi"] - 3 * W) + 30, W)
            case("overhang: and nothing else is on slide 4", beyond == 0, beyond)

        if wanted("overhang") or wanted("bubble"):
            session((1280, 900), part_overhang)

        # =====================================================================================================
        # 4. the folder button's answer at a narrow and a wide window
        # =====================================================================================================
        def part_bubble(width):
            def go(c):
                p = Page(c)
                D = sorted((q.stem for q in designs.glob("*.json") if ".prev" not in q.name), key=lambda i: disk(i)["name"] != "Overhang")[0]
                p.open(D)
                p.saved()
                p.press_save()                      # "Already saved as ...", with the folder button
                c.js("window.__openAnswer = {ok: true, words: %s}" % json.dumps(BEHIND))
                ob = c.rect("#open-carousel")
                c.click("#open-carousel")
                c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
                geo = p.J("(function(){ var b = document.getElementById('open-line').getBoundingClientRect(), s = document.getElementById('save-line').getBoundingClientRect();"
                          " return {bub: [b.left, b.top, b.right, b.bottom], line: [s.left, s.top, s.right, s.bottom], doc: document.documentElement.scrollWidth, win: document.documentElement.clientWidth}; })()")
                bub, ln = geo["bub"], geo["line"]
                apart = bub[2] <= ln[0] or bub[0] >= ln[2] or bub[3] <= ln[1] or bub[1] >= ln[3]
                case(f"{width} wide: the folder button's answer is inside the window, the page does not scroll sideways, and the save line can still be read",
                     c.text("#save-line").startswith("Already saved as") and bub[0] >= 0 and bub[2] <= geo["win"] and bub[1] >= 0 and geo["doc"] <= geo["win"] and apart, geo)
                case(f"{width} wide: the button did not move when its answer came", c.rect("#open-carousel") == ob)
            return go

        if wanted("bubble"):
            session((760, 800), part_bubble(760))
            session((1280, 900), part_bubble(1280))

        # =====================================================================================================
        # 5. a set saved while its font was missing is saved again once the font is there (needs the internet)
        # =====================================================================================================
        def part_font(c):
            p = Page(c)
            D = new_design({"slides": 2, "bg": "#ffffff", "blocks": [frame(1, nums[0], 0), frame(2, nums[1], 1),
                            text(3, "WINDY", 130, 300, font="Bebas Neue", size=170, h=195.5, color="#000000")]}, "Georgia stays")
            c.block_urls(["*fonts.googleapis.com*", "*fonts.gstatic.com*"])
            p.open(D)
            p.saved()
            line = p.press_save()
            asked = c.js("Designer.saver.asking()")
            case("no internet: Save slides asks before saving the words in Georgia",
                 asked and line == "“Bebas Neue” couldn’t be loaded, so that text will be saved in Georgia.", line)
            if not asked:
                return
            c.click("#save-yes")
            c.wait_for("!Designer.saver.busy()", 60)
            first = in_car("Georgia stays")
            case("no internet: saved, in Georgia", c.text("#save-line").startswith("Saved 2 slides") and len(first) == 2, c.text("#save-line"))
            case("no internet: the line about the font is in the bar at the bottom, inside the window",
                 "Bebas Neue" in (c.text("#l-fonts") or "") and p.in_window("#l-fonts"), c.text("#l-fonts"))
            c.block_urls([])
            p.open(D)
            try:
                c.wait_for("Designer.type.status(Designer.st.blocks[2]) === 'ready'", 15)
                back = True
            except cd.Timeout:
                back = False
            if not back:
                print("SKIP  Google Fonts could not be reached from this computer: saving again once the font is back was not watched", flush=True)
                return
            p.saved()
            line = p.press_save()
            if c.js("Designer.saver.asking()"):
                c.click("#save-yes")
                c.wait_for("!Designer.saver.busy()", 60)
                line = c.text("#save-line")
            case("internet back, the screen now shows Bebas Neue: Save slides makes a NEW set in that font (it used to say 'Already saved' while the saved slides were in Georgia)",
                 line == "Saved 2 slides in your Carousel folder, named \"Georgia stays (2)\". Nothing was replaced." and len(in_car("Georgia stays (2) - ")) == 2
                 and in_car("Georgia stays - ") == [n for n in first if "(2)" not in n], line)

            # ---- a script font's joins across a space: the canvas ruler agrees with the page ----
            LONG = "Office waffle, file & flight: AVATAR Yo. Tofu 'fjord' 1974"
            D2 = new_design({"slides": 5, "bg": "#ffffff", "blocks": [frame(1, nums[0], 0), text(2, LONG, 100, 300, font="Caveat", size=230, w=4600, h=264.5, al="left")]}, "Caveat ruler")
            p.open(D2)
            try:
                c.wait_for("Designer.type.status(Designer.st.blocks[1]) === 'ready' && !!document.querySelector(\"#strip .blk[data-id='2'] .tx-ln\")", 15)
            except cd.Timeout:
                print("SKIP  Caveat could not be loaded from Google Fonts: the canvas ruler was not compared with the page for it", flush=True)
                return
            got = p.J("(function(){ var b = Designer.st.blocks[1], L = Designer.type.layout(b), e = document.querySelector(\"#strip .blk[data-id='2'] .tx-ln\"), r = document.createRange();"
                      " r.selectNodeContents(e); return {page: r.getBoundingClientRect().width / Designer.scale, ruler: L.lines[0].w, lines: L.lines.length}; })()")
            case("Caveat, one long line at 230 px: the canvas measures it as wide as the page draws it, to within a pixel (it was 8 px wider, so the saved line ended 9 px off)",
                 got["lines"] == 1 and got["page"] > 3000 and abs(got["page"] - got["ruler"]) < 1.0, got)

        if wanted("font"):
            session((1280, 900), part_font)
    finally:
        try:
            holder[0].stop()
        except Exception:  # noqa: BLE001
            pass
        srv.stop()
