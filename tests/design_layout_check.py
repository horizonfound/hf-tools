#!/usr/bin/env python3
"""Checks of the carousel designer's ARRANGEMENT: where things sit, how big the strip starts, and what the hand
test in the Claude app's pane found (Nov 6). Run as part of tests/design_check.py (--only layout runs just this
part: the page server on port + 20).

What must hold, like Nicole's page:

  * the top is compact: the title and one help line, then TWO rows of tools at 1024 px and up (the design's row,
    the slides' row), each one row; the save status sits in a slot of fixed width, so no word it holds moves a button
  * ONE bar for the selected thing under the rows, with room held for it, so the strip never moves when the
    selection changes: nothing selected shows the help line alone (no greyed buttons), a photo its buttons in at
    most two rows, a text box its controls in at most two rows
  * "Fill N empty frames" is in that bar's first line, only while there is an empty frame, and takes no room otherwise
  * no label in the slides' row changes length with the selection (Brand colors stays Brand colors)
  * a line a press on a tool brings (Slides, + Add text, Brand colors) sits under its own group and moves nothing
  * the strip starts with a slide about a third of the window tall (230 to 460 px), however many slides, and the
    Size slider runs from "every slide fits across the window" to large, with the arrow keys stepping by a quarter
  * the strip's top is at most about 300 px down at 1024 x 768, no lower at wider windows, and the photos' heading
    is in sight under it; at 720 and 375 px the rows wrap with no sideways scroll and every control in reach
  * what is outside the strip's top and bottom is not drawn over the slide labels: the selection's ring stops at
    the strip's edge, a handle whose corner is off the strip is not drawn, and one on the very edge shows whole
  * opening the preview, the gallery, My designs, the shoot menu, the font list or Save as template never scrolls
    the page behind; the wheel does not scroll the page behind a sheet; closing puts the keyboard back
  * every button's name for a screen reader is its visible words (the tooltip is its description); the two tick
    boxes are "Snap into line" and "Profile grid crop"; every slider is named

Needs Chrome (SKIP without it). Makes its own pretend kit in the work folder, points STUDIO_HOME at it, and stops
the server it starts.
"""
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
W, H = 1080, 1350

SIZES = ((1024, 768), (1280, 900), (900, 700), (1440, 900))

MEASURE = r"""
(function(){
  function r(id){ var e = document.getElementById(id); if (!e) return null; var b = e.getBoundingClientRect(); return {top: Math.round(b.top * 10) / 10, left: Math.round(b.left * 10) / 10, h: Math.round(b.height * 10) / 10, w: Math.round(b.width * 10) / 10, bottom: Math.round(b.bottom * 10) / 10, right: Math.round(b.right * 10) / 10}; }
  function rows(sel){ var tops = {}; Array.prototype.forEach.call(document.querySelectorAll(sel), function(g){ if (g.hidden || !g.offsetParent) return; tops[Math.round(g.getBoundingClientRect().top)] = 1; }); return Object.keys(tops).length; }
  var shown = Array.prototype.filter.call(document.querySelectorAll('#selbar .needsel'), function(g){ return !g.hidden && !!g.offsetParent; }).map(function(g){ return g.id; });
  return {win: [innerWidth, innerHeight], scrollW: document.documentElement.scrollWidth, scrollY: scrollY,
          stage: r('stage'), strip: r('strip'), tools1: r('tools-designs'), tools2: r('tools-main'), selbar: r('selbar'), selcap: r('selcap'),
          rows1: rows('#tools-designs > .group'), rows2: rows('#tools-main > .group'), selrows: rows('#selrows > .group'), shown: shown,
          undo: r('undo'), tray: r('trayname'), thumbs: r('thumbs'), savebar: r('savebar'), fill: r('fill-holes'),
          view: window.Designer && Designer.view ? Designer.view() : 0, slideH: Math.round(window.Designer ? Designer.scale * 1350 : 0),
          brand: document.getElementById('brand-label').textContent, brandName: document.getElementById('g-brand').getAttribute('aria-label'),
          hint: document.getElementById('selhint').textContent};
})()
"""


def check_layout_page(case, work):
    """What can be read from the files themselves, with no browser."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    import design_page
    page = design_page.page_html("A kit")
    css = design_page.DESIGN_CSS
    case("layout: the page has two rows of tools and one bar for the selected thing, with its first line and its rows",
         page.count("class='d-tools'") == 2 and "id='tools-designs'" in page and "id='tools-main'" in page
         and page.count("id='selbar'") == 1 and "id='selcap'" in page and "id='selrows'" in page and "class='d-tools selbar" not in page)
    case("layout: the Smaller and Bigger buttons are gone; a Size slider for the strip is in the slides' row, named for a screen reader",
         "view-smaller" not in page and "view-bigger" not in page
         and re.search(r"<div class='group' id='g-view'><span class='lbl'>Size</span><input type='range' id='view-size'[^>]*aria-label='How big the slides look'", page) is not None)
    case("layout: the two tick boxes carry their words as their names", "id='snap' checked aria-label='Snap into line'" in page and "id='gridcrop' aria-label='Profile grid crop'" in page)
    case("layout: the room held for the selection bar is two rows and its first line, at 1024 px and up",
         re.search(r"@media\(min-width:1024px\)\{[^@]*\.selbar\{min-height:calc\(var\(--row\) \* 2 \+ \d+px\)\}", css) is not None
         and ".selbar.off .selrows{display:none}" in css)
    case("layout: a line a press brings in the tool rows sits under its own group (absolute, at 1024 px and up), not in the row",
         re.search(r"@media\(min-width:1024px\)\{[^@]*\.d-tools \.group>\.gline\{position:absolute;left:0;top:calc\(100% \+ \d+px\)", css) is not None)
    case("layout: the selection's ring is its own element, cut at the strip's edges, and a handle off the strip is not drawn",
         ".selbox .ring{" in css and ".h.out{display:none}" in css and "outline:2px solid var(--sel);pointer-events:none}\n.selbox.on" not in css)
    case("layout: the page behind a sheet is held still by a class on the page's root", "html.d-locked{overflow:hidden}" in css and "scrollbar-gutter:stable" in css)
    case("layout: the slide labels' room above the strip stays (the stage's top padding is at least 24 px)",
         re.search(r"\.stage\{[^}]*padding:2[4-9]px 18px", css) is not None)
    import design_js_model
    case("layout: the model's view rules start the strip at a third of the window, 230 to 460 px tall, and the slider's small end is 'all slides fit'",
         "start: [230, 460]" in design_js_model.DESIGN_MODEL_JS and "function viewLow(avail, slides)" in design_js_model.DESIGN_MODEL_JS)


def check_layout_browser(case, work, port, make_kit, Server, post, get_json):
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  no Chrome on this computer: the designer's arrangement was not measured in a real page", flush=True)
        return
    target = work / "layout"
    ok, out = make_kit(target, "Layout lake", 24)
    if not case("layout browser: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Layout lake"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    nums = [x["n"] for x in sheet]
    scratch = work / "chrome-layout"
    scratch.mkdir(parents=True, exist_ok=True)
    toks = [0]

    def frame(i, n, k, **more):
        b = {"id": i, "n": n, "x": k * W, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}
        b.update(more)
        return b

    def text(i, words, x, y):
        return {"id": i, "type": "text", "text": words, "font": "Inter", "size": 96, "weight": 400, "italic": False, "upper": False,
                "al": "center", "ls": 0, "lh": 1.15, "color": "#2a2622", "x": x, "y": y, "w": 820, "h": 110.4}

    srv = Server(env, port)
    P = srv.start()
    try:
        def new_design(state, name):
            toks[0] += 1
            code, out = post(P, "/design-new", {"kit": kit_name, "token": f"layoutcheck{toks[0]:04d}", "state": state, "name": name})
            assert code == 200 and out.get("ok"), (code, out)
            return out["design"]["id"]

        # seven slides: six photos, one empty frame, a text box on slide 1, and a photo pulled half above the top of slide 3
        D = new_design({"slides": 7, "bg": "#ffffff", "blocks": [frame(i + 1, nums[i], i) for i in range(6)] + [frame(9, None, 6)] + [text(8, "A windy morning", 130, 600)]}, "Layout seven")
        D_FULL = new_design({"slides": 3, "bg": "#ffffff", "blocks": [frame(i + 1, nums[i], i) for i in range(3)]}, "Layout full")
        D20 = new_design({"slides": 20, "bg": "#ffffff", "blocks": [frame(i + 1, nums[i], i) for i in range(20)]}, "Layout twenty")

        def J(c, expr):
            return json.loads(c.js("JSON.stringify(" + expr + ")"))

        def open_page(c, did):
            c.open(f"http://127.0.0.1:{P}/design.html?kit={KQ}&design={did}")
            c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 25,
                       tell="document.body.innerText.slice(0, 300)")
            try:
                c.wait_for("Designer.st.blocks.every(function(b){ return b.type !== 'text' || Designer.type.status(b) !== 'wait'; }) && Designer.type.fit(Designer.st) === Designer.st", 12)
            except cd.Timeout:
                pass

        def measure(c):
            return J(c, MEASURE)

        def inset(clip):
            """The four sides of a clip-path inset() as Chrome writes it back (it folds equal sides together)."""
            m = re.match(r"inset\(([^)]*)\)", clip or "")
            if not m:
                return None
            v = [float(x[:-2]) for x in m.group(1).split()]
            if len(v) == 1:
                v = v * 4
            elif len(v) == 2:
                v = [v[0], v[1], v[0], v[1]]
            elif len(v) == 3:
                v = [v[0], v[1], v[2], v[1]]
            return v if len(v) == 4 else None

        # =====================================================================================================
        # A to D: the rows, the bar, the strip, at the four window sizes
        # =====================================================================================================
        tops = {}
        for size in SIZES:
            w, h = size
            wide = w >= 1024
            tag = f"{w}x{h}"
            with cd.Chrome(work=scratch, size=size) as c:
                open_page(c, D)
                m0 = measure(c)
                c.screenshot(f"layout-{tag}-none.png")
                want_h = min(460, max(230, h / 3))
                case(f"{tag}: the strip starts with a slide about a third of the window tall ({round(want_h)} px, between 230 and 460), seven slides or not",
                     abs(m0["slideH"] - want_h) <= 2 and 230 - 2 <= m0["slideH"] <= 460 + 2, m0["slideH"])
                case(f"{tag}: nothing selected: no group of the selection bar shows, the help line is in the bar's first line, and Fill 1 empty frame is beside it",
                     m0["shown"] == [] and m0["hint"].startswith("Click a photo on the slides") and m0["fill"] and m0["fill"]["w"] > 0
                     and m0["selcap"]["top"] <= m0["fill"]["top"] and m0["fill"]["bottom"] <= m0["selcap"]["bottom"] + 1 and c.text("#fill-holes") == "Fill 1 empty frame", (m0["shown"], m0["hint"], m0["fill"]))
                case(f"{tag}: no sideways scroll of the page", m0["scrollW"] <= w, m0["scrollW"])
                if wide:
                    case(f"{tag}: two rows of tools, one row each (the design's, the slides')", m0["rows1"] == 1 and m0["rows2"] == 1, (m0["rows1"], m0["rows2"]))
                    case(f"{tag}: the strip's top is at most about 300 px from the top of the page (stage under 300, strip under 320)",
                         m0["stage"]["top"] <= 300 and m0["strip"]["top"] <= 320, (m0["stage"]["top"], m0["strip"]["top"]))
                    case(f"{tag}: the photos' heading is in sight under the strip, above the bar at the bottom of the window",
                         m0["tray"]["top"] + m0["tray"]["h"] <= m0["savebar"]["top"] and m0["thumbs"]["top"] < m0["savebar"]["top"], (m0["tray"], m0["savebar"]))
                    tops[size] = m0["strip"]["top"]
                order = J(c, "Array.prototype.map.call(document.querySelectorAll('#tools-main > .group'), function(g){ return g.id; })")
                case(f"{tag}: the slides' row runs Slides, Background, Brand colors, + Add text, Size, Snap into line, Undo",
                     order == ["g-slides", "g-bg", "g-brand", "g-text", "g-view", "g-snap", "g-undo"], order)
                order1 = J(c, "Array.prototype.map.call(document.querySelectorAll('#tools-designs > .group'), function(g){ return g.id; })")
                case(f"{tag}: the design's row runs Shoot, Design (name, status, My designs, Duplicate design), + New design and Save as template; Fill empty frames is not in it",
                     order1 == ["g-shoot", "g-design", "g-new"] and J(c, "Array.prototype.map.call(document.querySelectorAll('#g-new > button'), function(b){ return b.id; })") == ["new-design", "save-template"]
                     and c.js("document.getElementById('selcap').contains(document.getElementById('fill-holes'))"), order1)
                # the selection: a photo, then text, then nothing
                c.js("Designer.select(1)")
                m1 = measure(c)
                c.screenshot(f"layout-{tag}-photo.png")
                case(f"{tag}: a photo selected: its three groups show{', in at most two rows' if wide else ''}, and the help line names it",
                     m1["shown"] == ["sel-photo", "sel-crop", "sel-all"] and (m1["selrows"] <= 2 or not wide) and m1["hint"].startswith("Photo 1."), (m1["shown"], m1["selrows"]))
                c.js("Designer.select(8)")
                m2 = measure(c)
                c.screenshot(f"layout-{tag}-text.png")
                case(f"{tag}: text selected: its four groups show{', in at most two rows' if wide else ''}", m2["shown"] == ["sel-text", "sel-color", "sel-style", "sel-all"] and (m2["selrows"] <= 2 or not wide), (m2["shown"], m2["selrows"]))
                case(f"{tag}: the Brand colors label keeps its words and its place with text selected (the longer words are its tooltip and its name for a screen reader)",
                     m2["brand"] == "Brand colors" and m0["brand"] == "Brand colors" and m2["brandName"] == "Brand colors (for the text)" and m0["brandName"] == "Brand colors"
                     and m2["undo"] == m0["undo"] and m2["rows2"] == m0["rows2"], (m2["brand"], m2["brandName"], m0["undo"], m2["undo"]))
                c.click("#font-btn")
                c.screenshot(f"layout-{tag}-fonts.png")
                c.key("Escape")
                c.js("Designer.select(null)")
                m3 = measure(c)
                if wide:
                    case(f"{tag}: selecting a photo, then text, then nothing moves the strip's top by 0 px",
                         m0["stage"]["top"] == m1["stage"]["top"] == m2["stage"]["top"] == m3["stage"]["top"] and m0["strip"]["top"] == m1["strip"]["top"] == m2["strip"]["top"] == m3["strip"]["top"],
                         (m0["stage"]["top"], m1["stage"]["top"], m2["stage"]["top"], m3["stage"]["top"]))
                    # the help lines all fit in the bar's first line at this width (the long one is for a photo)
                    fits = J(c, "(function(){ var h = document.getElementById('selhint'); return ['hintNone', 'hintHole', 'hintOther'].map(function(k){ return Designer.WORDS[k]; }).concat([Designer.WORDS.hintPhoto(24), Designer.WORDS.hintInside(24), Designer.WORDS.type.hint])"
                                  ".map(function(t){ var was = h.textContent; h.textContent = t; var ok = h.scrollWidth <= h.clientWidth + 1; h.textContent = was; return ok; }); })()")
                    case(f"{tag}: every help line fits in the bar's first line beside Fill empty frames", all(fits), fits)
                else:
                    case(f"{tag}: the strip still starts no lower than it did (its top under 460 px with nothing selected)", m0["strip"]["top"] <= 460, m0["strip"]["top"])
                # the save status: a slot of fixed width, so no word in it moves a button
                moved = J(c, "(function(){ var s = document.getElementById('d-status'), b = document.getElementById('designs-btn').getBoundingClientRect().left, n = document.getElementById('new-design').getBoundingClientRect(), out = [];"
                             " ['saved', 'saving', 'notSaved', 'needsReload', 'retry'].forEach(function(k){ s.textContent = Designer.WORDS[k]; var r = document.getElementById('new-design').getBoundingClientRect();"
                             " out.push([k, document.getElementById('designs-btn').getBoundingClientRect().left === b && r.left === n.left && r.top === n.top, s.scrollWidth <= s.clientWidth]); }); s.textContent = 'Saved'; return out; })()")
                case(f"{tag}: the save status slot holds Saved, Saving..., Not saved and Needs reload without moving My designs or + New design",
                     all(x[1] for x in moved) and all(x[2] for x in moved if x[0] != "retry"), moved)
                case(f"{tag}: no error on the page", not c.page_errors(), c.page_errors())
        case("the strip starts no lower at a wider window than at 1024 x 768", all(tops[s] <= tops[(1024, 768)] for s in tops), tops)

        # =====================================================================================================
        # the narrow windows: 720 and a phone's 375
        # =====================================================================================================
        for size in ((720, 900), (375, 740)):
            w, h = size
            tag = f"{w}x{h}"
            with cd.Chrome(work=scratch, size=size) as c:
                if w < 500:
                    c.phone(w, h)
                open_page(c, D)
                m0 = measure(c)
                c.screenshot(f"layout-{tag}-none.png")
                case(f"{tag}: no sideways scroll of the page", m0["scrollW"] <= w, m0["scrollW"])
                case(f"{tag}: the strip starts no lower than it did (under {620 if w < 500 else 420} px with nothing selected)", m0["strip"]["top"] <= (620 if w < 500 else 420), m0["strip"]["top"])
                c.js("Designer.select(1)")
                m1 = measure(c)
                c.screenshot(f"layout-{tag}-photo.png")
                reach = J(c, "(function(){ var bad = []; Array.prototype.forEach.call(document.querySelectorAll('#tools-designs button, #tools-designs input, #tools-main button, #tools-main input, #selbar button, #selbar input, #selbar textarea'), function(e){"
                             " if (e.hidden || !e.offsetParent || e.type === 'color' && e.classList.contains('bc-pick')) return; var r = e.getBoundingClientRect(); if (r.left < 0 || r.right > innerWidth + 0.5 || r.width <= 0) bad.push(e.id || e.className || e.textContent); }); return bad; })()")
                case(f"{tag}: every control in the rows and the bar is inside the window sideways (a photo selected)", not reach and m1["scrollW"] <= w, (reach, m1["scrollW"]))
                c.js("Designer.select(8)")
                m2 = measure(c)
                case(f"{tag}: text selected: its controls show and the page has no sideways scroll", m2["shown"] == ["sel-text", "sel-color", "sel-style", "sel-all"] and m2["scrollW"] <= w, (m2["shown"], m2["scrollW"]))
                case(f"{tag}: no error on the page", not c.page_errors(), c.page_errors())

        # =====================================================================================================
        # the Size slider, the clip at the strip's edges, the lines a press brings, the sheets, the names
        # =====================================================================================================
        with cd.Chrome(work=scratch, size=(1024, 768)) as c:
            open_page(c, D)
            m = measure(c)
            v0 = m["view"]
            lo = J(c, "Number(document.getElementById('view-size').min)")
            hi = J(c, "Number(document.getElementById('view-size').max)")
            room = J(c, "document.getElementById('stage').clientWidth - 2 * document.getElementById('stripwrap').offsetLeft")
            case("Size slider: it runs from 'every slide fits across the window' (never under 40, never over 140) up to 480, and sits at the strip's size",
                 lo == max(40, min(140, room // 7)) and hi == 480 and J(c, "Number(document.getElementById('view-size').value)") == v0, (lo, hi, room, v0))
            c.click("#view-size", fx=0.5)       # a click on its middle: the strip follows at once
            v_mid = J(c, "Designer.view()")
            case("Size slider: a click on its middle draws the strip at that size at once", abs(v_mid - (lo + hi) / 2) <= 6 and v_mid != v0 and abs(c.rect("#strip")["w"] - 7 * v_mid) < 2, (v_mid, lo, hi))
            c.key("ArrowRight")
            v_up = J(c, "Designer.view()")
            case("Size slider: the right arrow makes the slides a quarter bigger (the step Bigger had)", v_up == min(480, round(v_mid * 1.25)), (v_mid, v_up))
            c.key("ArrowLeft")
            c.key("ArrowLeft")
            v_dn = J(c, "Designer.view()")
            case("Size slider: the left arrow a quarter smaller", v_dn == max(lo, round(round(v_up / 1.25) / 1.25)), (v_up, v_dn))
            c.key("Home")
            fits_all = J(c, "(function(){ var s = document.getElementById('stage'); return {view: Designer.view(), fits: s.scrollWidth <= s.clientWidth + 1}; })()")
            case("Size slider: Home goes to its small end, where every slide fits across the window with no sideways scroll", fits_all["view"] == lo and fits_all["fits"], fits_all)
            c.key("End")
            case("Size slider: End goes to its large end (480 px a slide, 600 tall)", J(c, "Designer.view()") == 480 and abs(c.rect("#strip")["h"] - 600) < 1, J(c, "Designer.view()"))
            c.set_value("#view-size", str(v0))
            case("Size slider: set back to where it started, the strip is its starting size again", J(c, "Designer.view()") == v0, J(c, "Designer.view()"))
            # twenty slides: the small end is 'all twenty fit', still never under 40
            open_page(c, D20)
            lo20 = J(c, "Number(document.getElementById('view-size').min)")
            m20 = measure(c)
            case("twenty slides: the strip still starts at a third of the window tall (it scrolls sideways), and the slider's small end is 'all twenty fit'",
                 m20["slideH"] == m["slideH"] and lo20 == max(40, min(140, room // 20)), (m20["slideH"], m["slideH"], lo20))
            c.key("Tab")
            c.js("document.getElementById('view-size').focus({preventScroll: true})")
            c.key("Home")
            fits20 = J(c, "(function(){ var s = document.getElementById('stage'); return {view: Designer.view(), fits: s.scrollWidth <= s.clientWidth + 1, slides: Designer.st.slides}; })()")
            case("twenty slides: at the slider's small end all twenty are across the window", fits20["view"] == lo20 and fits20["fits"] and fits20["slides"] == 20, fits20)

            # ---- the clip: a frame pulled above the top of the strip ----
            open_page(c, D)
            c.js("Designer.select(3)")
            r3 = c.rect("#strip .blk[data-id='3']")
            c.drag((r3["cx"], r3["cy"]), (r3["cx"], r3["cy"] - r3["h"] * 0.6), steps=10)
            b3 = J(c, "Designer.M.find(Designer.st, 3)")
            sel = J(c, "(function(){ var s = document.querySelector('#over .selbox'), ring = s.querySelector('.ring'), st = document.getElementById('strip').getBoundingClientRect();"
                       " var hs = {}; Array.prototype.forEach.call(s.querySelectorAll('.h'), function(h){ hs[h.dataset.h] = {out: h.classList.contains('out'), shown: getComputedStyle(h).display !== 'none'}; });"
                       " var sr = s.getBoundingClientRect(); return {clip: ring.style.clipPath, top: sr.top, stripTop: st.top, hs: hs, labels: document.getElementById('labels').getBoundingClientRect().top}; })()")
            ins = inset(sel["clip"])
            case("clip: the photo is above the top of the strip (its y is negative)", b3["y"] < -100, b3)
            case("clip: the selection's ring is cut at the strip's top by as much as the frame is above it, and shows 3 px outside the box on the other sides",
                 ins is not None and abs(ins[0] - (-b3["y"]) * J(c, "Designer.scale")) < 1 and ins[1:] == [-3, -3, -3], sel["clip"])
            case("clip: the two top handles (off the strip) are not drawn; the two bottom ones (on it) are",
                 sel["hs"]["tl"]["out"] and sel["hs"]["tr"]["out"] and not sel["hs"]["tl"]["shown"] and not sel["hs"]["tr"]["shown"]
                 and not sel["hs"]["bl"]["out"] and not sel["hs"]["br"]["out"] and sel["hs"]["bl"]["shown"] and sel["hs"]["br"]["shown"], sel["hs"])
            over = J(c, "(function(){ var st = document.getElementById('strip').getBoundingClientRect(), b = document.querySelector(\"#strip .blk[data-id='3']\").getBoundingClientRect();"
                        " var x = b.left + b.width / 2, y = st.top - 8; var e = document.elementFromPoint(x, y); return {x: x, y: y, hit: e ? (e.id || e.className || e.tagName) : null, blk: !!(e && e.closest && e.closest('.blk')), ring: !!(e && e.classList && e.classList.contains('ring')), sel: !!(e && e.closest && e.closest('.selbox'))}; })()")
            case("clip: 8 px above the strip, over the frame's column, neither the photo nor its selection box is what is drawn there (the slide labels' room)",
                 not over["blk"] and not over["ring"] and not over["sel"], over)
            c.js("Designer.select(1)")
            edge = J(c, "(function(){ var s = document.querySelector('#over .selbox'), hs = {}; Array.prototype.forEach.call(s.querySelectorAll('.h'), function(h){ hs[h.dataset.h] = !h.classList.contains('out') && getComputedStyle(h).display !== 'none'; }); return {hs: hs, clip: s.querySelector('.ring').style.clipPath}; })()")
            case("clip: a frame that fills its slide, reaching every edge of the strip: all four handles are drawn whole and the ring is not cut",
                 all(edge["hs"].values()) and inset(edge["clip"]) == [-3, -3, -3, -3], edge)
            c.key("Meta+Z")
            case("clip: Undo puts the pulled frame back, and its handles all show again", J(c, "Designer.M.find(Designer.st, 3).y") == 0 and J(c, "document.querySelectorAll('#over .selbox .h.out').length") == 0)
            # a text box: its two side handles at mid-height; pulled so its middle is above the strip, both are out
            c.js("Designer.select(8)")
            tsel = J(c, "(function(){ var s = document.querySelector('#over .selbox'); return Array.prototype.map.call(s.querySelectorAll('.h'), function(h){ return [h.dataset.h, h.classList.contains('out'), getComputedStyle(h).display !== 'none']; }); })()")
            case("clip: a text box on the strip shows its two side handles", [x for x in tsel if x[2]] == [["tl", False, True], ["br", False, True]], tsel)

            # ---- a line a press brings sits under its own group and moves nothing ----
            open_page(c, D)
            before = measure(c)
            c.js("Designer.select(null)")
            c.click("#slides-minus")           # slide 7 has an empty frame on it
            after = measure(c)
            line = J(c, "(function(){ var l = document.getElementById('slides-line'), g = document.getElementById('g-slides'); var r = l.getBoundingClientRect(), gr = g.getBoundingClientRect();"
                        " return {text: l.textContent, top: r.top, left: r.left, right: r.right, gBottom: gr.bottom, gLeft: gr.left, abs: getComputedStyle(l).position}; })()")
            case("a press that brings a line (one fewer slide, with slide 7 in use): the line sits right under the Slides group, inside the window",
                 line["text"].startswith("Slide 7 still has something on it") and line["abs"] == "absolute" and line["gBottom"] <= line["top"] <= line["gBottom"] + 12
                 and abs(line["left"] - line["gLeft"]) < 2 and line["right"] <= 1024, line)
            case("...and nothing moved: not the strip, not Undo, not the rows", after["stage"] == before["stage"] and after["undo"] == before["undo"] and after["tools2"] == before["tools2"], (before["stage"], after["stage"]))
            c.js("Designer.select(1)")
            after2 = measure(c)
            case("...and selecting a photo under that line moves nothing either (the line lies over the bar's first line)", after2["stage"] == before["stage"] and after2["selrows"] == 2, after2["stage"])

            # ---- the sheets never scroll the page behind, and closing puts the keyboard back ----
            open_page(c, D)
            c.js("Designer.select(null)")
            # scrolled a little, with the rows still in sight (the driver brings a button it clicks into the window)
            y0 = J(c, "(function(){ window.scrollTo(0, 60); return scrollY; })()")
            case("the page can be scrolled to 60 px for this check", y0 == 60, y0)

            def sheet(name, open_btn, sheet_sel, close_key="Escape", back_to=None):
                c.click(open_btn)
                c.wait_for(f"!document.querySelector('{sheet_sel}').hidden", 5)
                y1 = J(c, "scrollY")
                case(f"{name}: opening it does not scroll the page behind (still at 60)", y1 == 60, y1)
                c.wheel(sheet_sel, 300)
                c.wheel(sheet_sel, -600)
                y2 = J(c, "scrollY")
                locked = J(c, "document.documentElement.classList.contains('d-locked') && getComputedStyle(document.documentElement).overflow === 'hidden'")
                case(f"{name}: the wheel over it does not scroll the page behind, which is held still", y2 == 60 and locked, (y2, locked))
                c.key(close_key)
                c.wait_for(f"document.querySelector('{sheet_sel}').hidden", 5)
                y3 = J(c, "scrollY")
                focus = J(c, "document.activeElement ? document.activeElement.id : ''")
                case(f"{name}: closing leaves the page where it was and puts the keyboard back on {back_to or open_btn}",
                     y3 == 60 and focus == (back_to or open_btn).lstrip("#") and not J(c, "document.documentElement.classList.contains('d-locked')"), (y3, focus))

            sheet("Preview swipe", "#preview-btn", "#preview")
            sheet("the gallery (+ New design)", "#new-design", "#gallery")
            sheet("Save as template", "#save-template", "#tpl-dialog")
            # the pop-ups: opening never scrolls; Escape puts the keyboard back on their button
            for name, btn, pop in (("My designs", "#designs-btn", "#designs-pop"), ("the shoot menu", "#shoot-btn", "#shoot-pop")):
                c.click(btn)
                c.wait_for(f"!document.getElementById('{pop[1:]}').hidden", 5)
                y1 = J(c, "scrollY")
                c.key("Escape")
                case(f"{name}: opening it does not scroll the page behind, and Escape puts the keyboard back on its button",
                     y1 == 60 and J(c, "document.getElementById('" + pop[1:] + "').hidden") and J(c, "document.activeElement.id") == btn[1:] and J(c, "scrollY") == 60, (y1, J(c, "document.activeElement.id")))
            c.js("Designer.select(8)")
            c.js("window.scrollTo(0, 60)")
            c.click("#font-btn")
            c.wait_for("!document.getElementById('font-panel').hidden", 5)
            y1 = J(c, "scrollY")
            c.key("Escape")
            case("the font list: opening it does not scroll the page behind (the search box takes the keyboard without moving the page), and Escape puts it back on the font button",
                 y1 == 60 and J(c, "document.activeElement.id") == "font-btn" and J(c, "scrollY") == 60, (y1, J(c, "document.activeElement.id")))
            # and from the top of the page, the hand test's own case: Preview swipe leaves scrollY at 0
            c.js("window.scrollTo(0, 0); Designer.select(null)")
            c.click("#preview-btn")
            c.wait_for("!document.getElementById('preview').hidden", 5)
            case("Preview swipe from the top of the page: the page behind stays at 0 (it went to 419 in the pane)", J(c, "scrollY") == 0, J(c, "scrollY"))
            c.key("Escape")

            # ---- names for a screen reader, from Chrome's own accessibility tree ----
            open_page(c, D)
            c.js("Designer.select(8)")
            tree = c.cdp("Accessibility.getFullAXTree")
            ax = {}
            for n in tree.get("nodes", []):
                role = (n.get("role") or {}).get("value")
                if role not in ("button", "checkbox", "slider", "textbox", "combobox"):
                    continue
                name = (n.get("name") or {}).get("value") or ""
                desc = (n.get("description") or {}).get("value") or ""
                ax.setdefault(role, []).append((name, desc))
            buttons = dict(ax.get("button", []))
            case("names: Duplicate design, + New design and Fill empty frames are named by their words, with the explanation as the description",
                 buttons.get("Duplicate design", None) == "Makes a copy of this design and opens it. This one stays as it is."
                 and buttons.get("+ New design", None) == "Start another design for this shoot. The one you have open stays as it is."
                 and buttons.get("Fill 1 empty frame", None) == "Puts photos you haven’t used yet into the empty frames", {k: v for k, v in buttons.items() if "design" in k.lower() or "Fill" in k})
            case("names: the two tick boxes are Snap into line and Profile grid crop (not 'on')",
                 sorted(n for n, d in ax.get("checkbox", [])) == ["Profile grid crop", "Snap into line"], ax.get("checkbox"))
            sliders = sorted(n for n, d in ax.get("slider", []))
            case("names: every slider is named (the strip's size, the text's size, letter and line spacing)",
                 sliders == ["How big the slides look", "Space between letters", "Space between lines", "Text size"], sliders)
            case("names: the font button says what it does and which font (Choose a font: Inter); the shoot and My designs buttons are their words",
                 any(n.startswith("Choose a font: Inter") for n, d in ax.get("button", [])) and "My designs" in buttons and "Shoot: Layout lake" in buttons, [n for n, d in ax.get("button", []) if "font" in n.lower() or "Shoot" in n][:4])
            # every button whose visible words are words is named by them
            vis = J(c, "Array.prototype.map.call(document.querySelectorAll('button'), function(b){ if (b.hidden || !b.offsetParent) return null; var t = b.textContent.replace(/\\s*▾\\s*$/, '').replace(/\\s+/g, ' ').trim(); return [t, b.getAttribute('aria-label') || '', b.id || '']; }).filter(Boolean)")
            mis = [v for v in vis if len(v[0]) > 2 and re.search(r"[a-z]{3,}", v[0]) and v[1] and not v[1].startswith(v[0]) and not v[1].endswith(v[0]) and v[0] not in v[1]]
            case("names: no visible button with words is given a name for a screen reader that leaves its words out", not mis, mis[:6])
            case("names: no error on the page", not c.page_errors(), c.page_errors())
    finally:
        srv.stop()
