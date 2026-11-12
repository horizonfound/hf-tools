#!/usr/bin/env python3
"""Checks for the carousel designer's last part: designs, templates, the shoot menu, the preview, Save slides.

Run through tests/design_check.py (python3 tests/design_check.py --only designs --port 8960 --work <new folder>).
Two parts:

    check_designs_page(case, work)      what the four scripts are made of, and the rules (DesignPlan) run by
                                        themselves under the Mac's own JavaScript engine
    check_designs_browser(...)          the real page in a hidden Chrome, on two pretend shoots, with Pillow
                                        reading every slide the page saved: a photo across two slides joins
                                        up at the seam; a ruler photo lands where the layout says, within a
                                        pixel; words sit where the screen showed them; nothing that was in the
                                        Carousel folder or the photos is changed; a save cut off part way
                                        adds nothing; the same set is never made twice

The first shoot's photos are drawn here with Pillow (a checkerboard with edges at known places, smooth
stripes, plain colours in wide, tall and square) and the pretend kit points at that folder, so the test knows
every pixel it should find. Nothing here ever opens Finder: every page gets a stand-in for the one request
that would (GET /open), and the check is that the request was right.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
W, H = 1080, 1350
MINE = ("design_js_plan.py", "design_js_paint.py", "design_js_designs.py", "design_js_save.py")


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


# ---------------------------------------------------------------------------------------------------------
# the rules, by themselves
# ---------------------------------------------------------------------------------------------------------

PLAN_TESTS_JS = r"""
(new Function(MODEL_SRC)).call(this);
(new Function(PLAN_SRC)).call(this);
var P = this.DesignPlan, M = this.DesignModel, out = [], W = 1080, H = 1350;
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
function F(id, n, x, y, w, h, more){ var b = {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; for (var k in (more || {})) b[k] = more[k]; return b; }
function TX(id, x, y, w){ return {id: id, type: 'text', text: 'Words', font: 'Inter', size: 96, weight: 400, italic: false, upper: false, al: 'center', ls: 0, lh: 1.15, color: '#2a2622', x: x, y: y, w: w, h: 110}; }
function ST(slides, blocks){ return {slides: slides, bg: '#ffffff', blocks: blocks}; }
function ns(st){ return st.blocks.map(function(b){ return b.type === 'text' ? 't' : b.n; }); }
var photos = [{n: 1, way: 'wide', w: 1800, h: 1200}, {n: 2, way: 'tall', w: 1200, h: 1800}, {n: 3, way: 'square', w: 1400, h: 1400},
              {n: 4, way: 'wide', w: 1800, h: 1200}, {n: 5, way: 'tall', w: 1200, h: 1800}, {n: 6, way: 'tall', w: 1200, h: 1800},
              {n: 7, way: 'wide', w: 1800, h: 1200, missing: true}, {n: 8, way: 'square', w: 1400, h: 1400}];
var wideF = function(id, x, more){ return F(id, null, x, 0, 2160, 1350, more); };
var tallF = function(id, x, more){ return F(id, null, x, 0, 1080, 1350, more); };
var sqF = function(id, x, more){ return F(id, null, x, 100, 600, 600, more); };

// ---- the order photos are taken in ----
t('fill order: the carousel\'s picks first, in its order, then every other photo by number',
  eq(P.fillOrder(photos, [5, 2]).map(function(p){ return p.n; }), [5, 2, 1, 3, 4, 6, 8]));
t('fill order: a photo that can\'t be read is left out, a number named twice is taken once, a number not on the list is passed over',
  eq(P.fillOrder(photos, [7, 2, 2, 99]).map(function(p){ return p.n; }), [2, 1, 3, 4, 5, 6, 8]));
t('fill order: no carousel order at all is the photos by number', eq(P.fillOrder(photos, null).map(function(p){ return p.n; }), [1, 2, 3, 4, 5, 6, 8]));

// ---- filling frames by shape ----
t('wants: a frame across two slides wants a wide photo, a whole slide a tall one, a square whatever comes next',
  P.wants(wideF(1, 0)) === 'wide' && P.wants(tallF(1, 0)) === 'tall' && P.wants(sqF(1, 0)) === null && P.wants({w: 1000, h: 800}) === 'wide' && P.wants({w: 900, h: 1000}) === null);
var st = ST(4, [tallF(1, 0, {slot: 1}), wideF(2, 1080, {slot: 2}), tallF(3, 3240, {slot: 3})]);
var f = P.fill(st, photos, []);
t('fill: wide to wide, tall to tall: the first tall photo, the first wide one, the next tall one', eq(ns(f), [2, 1, 5]), ns(f));
t('fill: the layout handed in is not changed (a new one comes back)', eq(ns(st), [null, null, null]) && f !== st);
f = P.fill(st, photos, [6, 4]);
t('fill: the carousel\'s picks are used first (tall 6 before tall 2, wide 4 before wide 1)', eq(ns(f), [6, 4, 2]), ns(f));
f = P.fill(ST(3, [sqF(1, 0), sqF(2, 1080), sqF(3, 2160)]), photos, []);
t('fill: a frame with no leaning takes the next unused photo, whatever its shape', eq(ns(f), [1, 2, 3]), ns(f));
f = P.fill(ST(8, [wideF(1, 0), wideF(2, 2160), wideF(3, 4320), wideF(4, 6480)]), photos, []);
t('fill: with no wide photo left, a wide frame takes a square one before a tall one', eq(ns(f), [1, 4, 3, 8]), ns(f));
f = P.fill(ST(12, [wideF(1, 0), wideF(2, 2160), wideF(3, 4320), wideF(4, 6480), wideF(5, 8640), wideF(6, 10800)]), photos, []);
t('fill: with no wide or square photo left, it takes what there is', eq(ns(f), [1, 4, 3, 8, 2, 5]), ns(f));
f = P.fill(ST(4, [F(1, 2, 0, 0, W, H), tallF(2, 1080), tallF(3, 2160), tallF(4, 3240)]), photos, []);
t('fill: a photo already on a slide is not used again', eq(ns(f), [2, 5, 6, 1]), ns(f));
f = P.fill(ST(4, [tallF(3, 2160), tallF(2, 1080), tallF(1, 0)]), photos, []);
t('fill: frames with no slot are filled left to right', eq(ns(f), [6, 5, 2]), ns(f));
f = P.fill(ST(4, [tallF(1, 0, {slot: 3}), tallF(2, 1080, {slot: 1}), tallF(3, 2160, {slot: 2})]), photos, []);
t('fill: frames are filled in the order of their slots', eq(ns(f), [6, 2, 5]), ns(f));
var many = []; for (var i = 0; i < 10; i++) many.push(tallF(i + 1, (i % 4) * 1080, {slot: i + 1}));
f = P.fill(ST(4, many), photos, []);
t('fill: no photo is used twice, and frames stay empty when the photos run out (7 can be read, 10 frames)',
  ns(f).filter(function(n){ return n !== null; }).length === 7 && ns(f).slice(7).every(function(n){ return n === null; })
  && ns(f).slice(0, 7).slice().sort().join() === '1,2,3,4,5,6,8', ns(f));
var full = ST(2, [F(1, 2, 0, 0, W, H), TX(2, 100, 100, 800)]);
t('fill: nothing to fill gives the very same layout back', P.fill(full, photos, []) === full);
t('fill: no photos gives the very same layout back', P.fill(st, [], []) === st && P.fill(st, [{n: 9, way: 'wide', missing: true}], []) === st);
f = P.fill(ST(2, [F(1, null, 0, 0, W, H, {ox: 0.1, oy: 0.9, zoom: 2, slot: 4, border: {w: 12, color: '#ffffff'}}), TX(2, 100, 100, 800)]), photos, []);
t('fill: a filled frame starts from the middle at zoom 1 and keeps its slot and border; text is left alone',
  f.blocks[0].n === 2 && f.blocks[0].ox === 0.5 && f.blocks[0].oy === 0.5 && f.blocks[0].zoom === 1 && f.blocks[0].slot === 4 && f.blocks[0].border.w === 12 && eq(f.blocks[1], TX(2, 100, 100, 800)), f.blocks[0]);
t('holes: the empty frames, by slot, then left to right, then top to bottom',
  eq(P.holes(ST(3, [F(1, null, 1080, 600, 500, 500), F(2, null, 1080, 0, 500, 500), F(3, 4, 0, 0, W, H), F(4, null, 0, 0, 500, 500, {slot: 9}), TX(5, 0, 0, 500)])).map(function(b){ return b.id; }), [2, 1, 4]));
t('frames: how many frames a layout has (text is not one)', P.frames(ST(2, [tallF(1, 0), F(2, 3, 0, 0, W, H), TX(3, 0, 0, 500)])) === 2);

// ---- a template into a layout ----
var tpl = {slides: 3, bg: '#f4efe6', blocks: [F(1, null, 0, 0, W, H, {slot: 1}), F(2, null, 1080, 0, 2160, H, {slot: 2}), TX(3, 100, 300, 800)]};
var keep = JSON.stringify(tpl);
var a = P.fromTemplate(tpl, false, photos, []);
t('template: without the tick every frame is empty, the text and the background are kept, the ids are the template\'s own',
  eq(ns(a), [null, null, 't']) && a.bg === '#f4efe6' && a.slides === 3 && eq(a.blocks.map(function(b){ return b.id; }), [1, 2, 3]) && a.blocks[2].text === 'Words');
var b2 = P.fromTemplate(tpl, true, photos, [5]);
t('template: with the tick the frames are filled by shape from this shoot\'s photos', eq(ns(b2), [5, 1, 't']), ns(b2));
t('template: using one does not change the template itself', JSON.stringify(tpl) === keep);
a = P.fromTemplate({slides: 3, bg: '#ffffff', blocks: [F(1, 44, 0, 0, W, H, {ox: 0.2, zoom: 2})]}, false, photos, []);
t('template: a photo number that somehow came with a template is never used (templates hold no photo)', a.blocks[0].n === null && a.blocks[0].ox === 0.5 && a.blocks[0].zoom === 1);
// one slide on its own is a single post (decision 12): the rules go down to one slide, as the Assistant's do (before v19 stage c2 they
// brought a template to 2, so a one-slide template came out as two slides)
t('template: a silly slide count is brought to 1..20', P.fromTemplate({slides: 99, bg: '#ffffff', blocks: []}, false).slides === 20 && P.fromTemplate({slides: 0, bg: '#ffffff', blocks: []}, false).slides === 1);
t('template: a one-slide template stays one slide', P.fromTemplate({slides: 1, bg: '#ffffff', blocks: []}, false).slides === 1);

// ---- one photo per slide ----
var one = P.onePerSlide(photos, [6, 3, 1], '#111111');
t('one per slide: the carousel\'s order, each photo filling its own slide, on the kit\'s background',
  one.slides === 3 && one.bg === '#111111' && eq(ns(one), [6, 3, 1]) && one.blocks.every(function(b, i){ return b.x === i * W && b.y === 0 && b.w === W && b.h === H && b.id === i + 1 && b.slot === i + 1; }), one);
one = P.onePerSlide(photos, [], '#ffffff');
t('one per slide: with no carousel order it is the first eight photos', one.slides === 8 && eq(ns(one), [1, 2, 3, 4, 5, 6, 7, 8]), ns(one));
t('one per slide: one photo makes one slide (a single post)', P.onePerSlide(photos, [4], '#ffffff').slides === 1 && P.onePerSlide(photos, [4], '#ffffff').blocks.length === 1);
var lots = []; for (i = 1; i <= 30; i++) lots.push({n: i, way: 'tall', w: 1200, h: 1800});
t('one per slide: never more than 20', P.onePerSlide(lots, lots.map(function(p){ return p.n; }), '#ffffff').slides === 20);

// ---- what is on each slide ----
var lay = ST(4, [F(1, 1, 0, 0, W, H), F(2, 4, 1080, 0, 2160, H), TX(3, 1500, 200, 800), F(4, null, 3340, 100, 500, 500)]);
t('slide blocks: a photo across two slides is on both, in list order with what else is there',
  eq(P.slideBlocks(lay, 0).map(function(b){ return b.id; }), [1]) && eq(P.slideBlocks(lay, 1).map(function(b){ return b.id; }), [2, 3])
  && eq(P.slideBlocks(lay, 2).map(function(b){ return b.id; }), [2, 3]) && eq(P.slideBlocks(lay, 3).map(function(b){ return b.id; }), [4]));
t('slide blocks: something that ends exactly at a seam is not on the next slide', P.slideBlocks(ST(2, [F(1, 1, 0, 0, W, H)]), 1).length === 0);
t('slide blocks: something that hangs one pixel over a seam is on both', P.slideBlocks(ST(2, [F(1, 1, 0, 0, W + 1, H)]), 1).length === 1);
t('bare slides: the slides nothing reaches into', eq(P.bareSlides(ST(5, [F(1, 1, 0, 0, W, H), F(2, 4, 2160, 0, W, H)])), [2, 4, 5]) && eq(P.bareSlides(lay), []));
t('bare slides: a slide with only words on it is not bare', eq(P.bareSlides(ST(2, [TX(1, 100, 100, 800), F(2, 1, 1080, 0, W, H)])), []));
var hs = P.holeSlides(ST(4, [F(1, null, 0, 0, W, H), F(2, null, 100, 100, 300, 300), F(3, null, 3000, 0, 400, H), F(4, 2, 1080, 0, W, H)]));
t('empty frames: how many, and the slides they are on (the slide under each one\'s middle)', hs.count === 3 && eq(hs.slides, [1, 3]), hs);
t('empty frames: none in a full layout', P.holeSlides(full).count === 0 && eq(P.holeSlides(full).slides, []));

// ---- which made copy ----
var sizes = {s: 520, l: 1600, x: 2400, xx: 4320};
var same = true, why = null;
[[W, H], [2160, H], [540, 675], [300, 300], [3240, H]].forEach(function(fr){
  [[1200, 1800], [1800, 1200], [6000, 4000], [8192, 5464], [300, 450], [1400, 1400]].forEach(function(ph){
    [1, 1.7, 3].forEach(function(zoom){
      var b = {w: fr[0], h: fr[1], zoom: zoom, ox: 0.5, oy: 0.5}, L = M.layoutImg(b, ph[0], ph[1]);
      var want = M.pickSize(Math.max(L.iw, L.ih), Math.max(ph[0], ph[1]), sizes), got = P.copyFor(b, {w: ph[0], h: ph[1]}, 1, sizes);
      if (want !== got) { same = false; why = [fr, ph, zoom, want, got]; }
    });
  });
});
t('which copy: for a saved slide it is the contract\'s rule exactly (the smallest copy at least as large as drawn, or as large as the photo)', same, why);
t('which copy: a wide 45-megapixel photo filling one slide or two is drawn from the 2400 copy (2024 and 2160 wide), across three from the 4320 one',
  P.copyFor({w: W, h: H, zoom: 1}, {w: 8192, h: 5464}, 1, sizes) === 'x' && P.copyFor({w: 2160, h: H, zoom: 1}, {w: 8192, h: 5464}, 1, sizes) === 'x'
  && P.copyFor({w: 3240, h: H, zoom: 1}, {w: 8192, h: 5464}, 1, sizes) === 'xx' && P.copyFor({w: 540, h: H, zoom: 1}, {w: 5464, h: 8192}, 1, sizes) === 'l');
t('which copy: a small photo is never asked for larger than itself', P.copyFor({w: 2160, h: H, zoom: 3}, {w: 300, h: 450}, 1, sizes) === 's');
t('which copy: drawn small (the gallery, the preview) a smaller copy does', P.copyFor({w: W, h: H, zoom: 1}, {w: 8192, h: 5464}, 0.07, sizes) === 's' && P.copyFor({w: W, h: H, zoom: 1}, {w: 8192, h: 5464}, 0.7, sizes) === 'l');
t('which copy: the preview never asks for a copy that has to be made first', P.copyFor({w: 3240, h: H, zoom: 3}, {w: 8192, h: 5464}, 0.7, sizes, 'l') === 'l' && P.copyFor({w: 300, h: 300, zoom: 1}, {w: 8192, h: 5464}, 0.2, sizes, 'l') === 's');

// ---- the profile grid, and the small things ----
t('profile grid: a 4:5 slide in a 3:4 tile keeps 1012.5 of its 1080: 33.75 left out each side', P.gridTrim() === 33.75 && W - 2 * P.gridTrim() === H * 3 / 4, P.gridTrim());
t('edited: just now, minutes, hours, and nothing for older than a day (the page shows the day)',
  P.ago(1000, 1030) === 'just now' && P.ago(1000, 1000 + 300) === '5 min ago' && P.ago(1000, 1000 + 7200) === '2 hr ago' && P.ago(1000, 1000 + 90000) === null && P.ago(0, 500) === null);
var toks = [P.token('s', 1793977989123, 0.5), P.token('n', 1793977989123, 0), P.token('t', 0, 0.999999), P.token('', 5, 0.3), P.token('S9!', 1e15, 0.1), P.token('s', 1793977989123, 7)];
t('a press\'s name is 8 to 24 small letters and digits, whatever it is made from', toks.every(function(x){ return /^[a-z0-9]{8,24}$/.test(x); }), toks);
t('a press\'s name differs from the next one', P.token('s', 1793977989123, 0.25) !== P.token('s', 1793977989123, 0.75) && P.token('s', 1, 0.5) !== P.token('s', 2, 0.5));
t('preview: a drag past 40 px turns the slide; less puts it back; never past either end',
  P.swipe(2, -41, 7) === 3 && P.swipe(2, 41, 7) === 1 && P.swipe(2, -40, 7) === 2 && P.swipe(2, 12, 7) === 2 && P.swipe(0, 300, 7) === 0 && P.swipe(6, -300, 7) === 6);
t('preview: the slide fits the window (at most 380 wide, a narrow or short window makes it smaller)',
  P.phoneWidth(1280, 900) === 380 && P.phoneWidth(390, 844) === 342 && P.phoneWidth(1280, 500) === 248 && P.phoneWidth(200, 300) === 160);
t('gallery: a strip is drawn as large as fits 256 by 96', Math.abs(P.cardScale(3, 256, 96) - 96 / H) < 1e-9 && Math.abs(P.cardScale(7, 256, 96) - 256 / (7 * W)) < 1e-9);
t('a list of numbers in words', P.list([2]) === '2' && P.list([2, 4]) === '2 and 4' && P.list([2, 4, 5]) === '2, 4 and 5' && P.list([]) === '');
JSON.stringify(out);
"""


def check_designs_page(case, work):
    """What the last part's scripts are made of, and its rules run by themselves."""
    sys.path.insert(0, str(SCRIPTS))
    import arrange_page
    import design_js_designs
    import design_js_save
    import design_page as dp
    page = dp.page_html("A kit")
    names = [n for n, _ in dp.SCRIPTS]
    src = {n: s for n, s in dp.SCRIPTS}
    ours = ("DESIGN_PLAN_JS", "DESIGN_PAINT_JS", "DESIGN_DESIGNS_JS", "DESIGN_SAVE_JS")

    case("designs part: its four scripts go on the page after the brand colors, the rules first, and before the page starts",
         all(n in names for n in ours)
         and page.index(src["DESIGN_BRAND_JS"]) < page.index(src["DESIGN_PLAN_JS"]) < page.index(src["DESIGN_PAINT_JS"])
         < page.index(src["DESIGN_DESIGNS_JS"]) < page.index(src["DESIGN_SAVE_JS"]) < page.index(dp.DESIGN_START_JS), names)
    bare = re.sub(r"//[^\n]*", "", src["DESIGN_PLAN_JS"])
    case("the rules for designs and saving have no page in them (no document, no window but the one they hang themselves on, no fetch)",
         "document" not in bare and bare.count("window") == 2 and "fetch(" not in bare and "Date.now" not in bare and "Math.random" not in bare, bare.count("window"))
    for n in ours:
        s = src[n]
        case(f"{n}: words only ever go on the page as text (no innerHTML, outerHTML, insertAdjacentHTML, document.write)",
             not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|DOMParser|createContextualFragment|srcdoc", s))
        case(f"{n}: nothing kept in the browser, no browser drag-and-drop, no clipboard, no navigator.onLine",
             not re.search(r"localStorage|sessionStorage|indexedDB|document\.cookie|draggable|dataTransfer|ondragstart|navigator\.clipboard|navigator\.onLine", s))
        case(f"{n}: no requestAnimationFrame and no setInterval", "requestAnimationFrame" not in s and "setInterval" not in s)
        case(f"{n}: no script, frame or link is ever added to the page", not re.search(r"createElement\(\s*['\"](script|iframe|object|embed|link)['\"]", s))
        case(f"{n}: no address on the internet is written in it", not re.search(r"https?://|googleapis|gstatic", s))
    case("the rules and the drawing wait on no timer at all", "setTimeout" not in src["DESIGN_PLAN_JS"] and "setTimeout" not in src["DESIGN_PAINT_JS"])
    # (v24: the saving script has a second timer, the wait before the small picture for the post kit is drawn:
    # 1.5 s after a good save or a design opening, hers; nothing on the page depends on it)
    case("the only timers are waits between tries, one giving-up limit and the wait before the post kit's small picture: three in the designs script (a POST with no answer; leaving for another shoot; giving up on a new design the Assistant never answered), two in the saving script",
         src["DESIGN_DESIGNS_JS"].count("setTimeout(") == 3 and "setTimeout(ok, MAKE_WAIT)" in src["DESIGN_DESIGNS_JS"] and src["DESIGN_SAVE_JS"].count("setTimeout(") == 2
         and "setTimeout(ok, ms)" in src["DESIGN_SAVE_JS"] and "pvT = setTimeout(pushPreview, ms > 0 ? ms : PV.wait)" in src["DESIGN_SAVE_JS"],
         (src["DESIGN_DESIGNS_JS"].count("setTimeout("), src["DESIGN_SAVE_JS"].count("setTimeout(")))
    d, sv, pt = src["DESIGN_DESIGNS_JS"], src["DESIGN_SAVE_JS"], src["DESIGN_PAINT_JS"]
    case("drawing: a photo is laid out by the strip's own rule from the loaded picture's own size, and words by the text part's own drawing",
         "M.layoutImg(b, img.naturalWidth, img.naturalHeight)" in pt and "D.type.drawText(ctx, b, x0, 0)" in pt and pt.count("drawImage(") == 1 and "fillText" not in pt)
    # (v24: the post kit's small picture is each slide drawn small by Designer.paint, then set side by side: the one
    # drawImage in the saving script copies a slide the painter has just drawn, canvas to canvas, and nothing else)
    case("drawing: the preview, the gallery, a saved slide and the post kit's small picture are all drawn by Designer.paint (no fillText, and no drawImage on the page's later parts but the one that sets the small slides side by side)",
         "drawImage" not in d and sv.count("drawImage(") == 1 and "cx.drawImage(one, i * (w + PV.gap), 0);" in sv and "fillText" not in d and "fillText" not in sv
         and "D.paint.slide(" in sv and sv.count("D.paint.slide(") == 3 and "await D.paint.slide(ox, st, i, {out: PV.k, shelf: sh, cap: 's'});" in sv and "D.paint.strip(" in d)
    case("the post kit's small picture: up to 6 slides (4 stories) at 20% (15%), 6 px apart on white, JPEG at 0.85, 1.5 s after a good save or a design opening, never beside Save slides",
         "PV = {wait: 1500, most: STORY ? 4 : 6, k: STORY ? 0.15 : 0.2, gap: 6, quality: 0.85" in sv and "'image/jpeg', PV.quality" in sv and "cx.fillStyle = '#ffffff'" in sv
         and "D.on('saved', previewSoon);" in sv and "D.on('design', previewSoon);" in sv and "if (pvBusy || busy) { schedulePreview(); return; }" in sv
         and "if (!D.st || !D.design || D.blocked || !D.st.blocks.length) return;" in sv)
    pv_part = sv[sv.index("a small picture of the design, for the post kit"):sv.index("the profile grid's crop, on slide 1")]
    case("the post kit's small picture never puts a word on the page: its part of the script touches no element, says nothing and opens no box",
         not re.search(r"\bsay\(|textContent|\.hidden\b|\$\(|\bel\(|alert\(|confirm\(|prompt\(|console\.", pv_part), re.findall(r"\bsay\(|textContent|\$\(|console\.\w+", pv_part)[:3])
    case("saving: one canvas of 1080 by 1350 for every slide, JPEG at 0.93, and the pictures the next slide does not need are let go",
         "cv.width = W; cv.height = H;" in sv and "QUALITY = 0.93" in sv and "'image/jpeg', QUALITY" in sv and "D.paint.letGo(sh, i < n ? D.paint.keys(st, i, 1) : null)" in sv)
    case("saving: the commit is asked again under the same name for the press (the token is made once, before the first slide)",
         sv.count("D.newToken('s')") == 1 and sv.index("D.newToken('s')") < sv.index("for (i = 1; i <= n; i++)") and "set: token" in sv)
    case("a shoot's link is its kit folder's name and nothing else (and, in the stories designer, the kind)", "a.href = '/design.html?kit=' + encodeURIComponent(s.kit) + D.KQ;" in d and d.count(".href") == 1 and ".href" not in sv)
    asked = sorted(set(re.findall(r"'(/[a-z][a-z.-]*)[?']", d + sv)))
    case("every address the later parts name is one of the Assistant's own routes (and the designer's own page, for another shoot)",
         asked == ["/design-commit", "/design-new", "/design-preview", "/design-slide", "/design-state", "/design-template", "/design.html", "/open"]
         and len(re.findall(r"\bfetch\(", d + sv)) == 6 and "XMLHttpRequest" not in d + sv and "sendBeacon" not in d + sv and "WebSocket" not in d + sv, asked)
    case("there is no way to delete a design or a template on the page", not re.search(r"[Dd]elete|[Tt]rash|/design-delete|/design-remove", d + sv))
    # the bar at the bottom: every line Save slides says is beside the button that was pressed
    case("designer page: the Save slides line, its two answers, and Open the Carousel folder with its own line are in one bar with the button, in that order",
         bool(re.search(r"<div class='sv-bar' id='savebar'><div class='sv-notes' id='notes'>(?:(?!</div>).)*</div><div class='sv-in'>(?:(?!</div>).)*id='preview-btn'(?:(?!</div>).)*id='gridcrop'(?:(?!</div>).)*id='save-slides'(?:(?!</div>).)*id='save-line'"
                        r"(?:(?!</div>).)*id='save-yes'(?:(?!</div>).)*id='save-no'(?:(?!</div>).)*id='open-carousel'(?:(?!</div>).)*id='open-line'(?:(?!</div>).)*</div></div>", page, re.S)))
    case("designer page: one main (terracotta) button shows at a time in that bar: Save slides, or Save anyway while a question is up",
         page.count("class='tb main") == 2 and "id='save-yes' type='button' hidden" in page)
    case("designer page: no Instagram name, logo or handle written into the preview (the stories preview's name is their own handle, sent with the state)",
         not re.search(r"@[a-z0-9_]{3,}|instagram\.com|ig-logo|nicolelhill", d + sv, re.I) and "Instagram" not in sv)
    for css_name, css in (("designs styles", design_js_designs.DESIGN_DESIGNS_CSS), ("saving styles", design_js_save.DESIGN_SAVE_CSS)):
        case(f"{css_name}: no backslash, fetch nothing (no url(...), no @font-face, no @import), name no font, light only",
             "\\" not in css and "url(" not in css and "@font-face" not in css and "@import" not in css and "prefers-color-scheme" not in css
             and not re.search(r"font-family|Georgia|Fraunces|googleapis|gstatic", css))
        used = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
        theirs = set(re.findall(r"\.([a-zA-Z][\w-]*)", arrange_page.CSS)) - {"on"}
        mine = {c for c in used if c.startswith(("dz-", "sv-", "pv-"))}
        case(f"{css_name}: every class of its own starts dz-, sv- or pv-, and none is one the pickers use", mine and not (mine & theirs)
             and used - mine <= {"tb", "hint", "gline", "on", "cur", "main"}, sorted(used - mine))
    case("designs part: its styles are on the page, after the text and brand-color styles", page.index(dp.DESIGN_CSS) < page.index(design_js_designs.DESIGN_DESIGNS_CSS) < page.index(design_js_save.DESIGN_SAVE_CSS))
    for f in MINE:
        text = (SCRIPTS / f).read_text(encoding="utf-8")
        code_only = "\n".join(ln.split("#")[0] for ln in re.sub(r'"""(?:.|\n)*?"""', '""', text).splitlines())
        case(f"{f}: runs no Mac-only program and uses no Mac-only call", not re.search(r"\b(sips|osascript|chflags|caffeinate|fcntl|subprocess)\b|/Volumes|%-d", code_only))
        case(f"{f}: Python never formats over the JavaScript (raw strings, joined as they are)",
             not re.search(r'JS\s*(%|\.format\()', text) and not re.search(r'\bf(r|R)?"""', text) and 'JS = r"""' in text)

    f = work / "design-plan-tests.js"
    f.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar PLAN_SRC = " + json.dumps(src["DESIGN_PLAN_JS"]) + ";\n" + PLAN_TESTS_JS, encoding="utf-8")
    r = osascript(f)
    try:
        got = json.loads(r.stdout) if r.returncode == 0 else None
    except ValueError:
        got = None
    if not case("the rules for designs and saving ran to the end under osascript", got is not None and len(got) >= 40, (r.stderr or r.stdout)[-400:]):
        return
    for name, ok, detail in got:
        case("plan: " + name, ok, detail)


# ---------------------------------------------------------------------------------------------------------
# the pretend photos, drawn here so every pixel is known
# ---------------------------------------------------------------------------------------------------------

CELL = 250          # the checkerboard's squares, in the photo's own pixels


def draw_photos(folder):
    """Twenty-four photos: a wide and a tall checkerboard (edges every 250 px), smooth stripes (wide), and
    plain colours in tall, wide and square. Returns {file name: (w, h)}."""
    import colorsys
    import math
    from PIL import Image, ImageChops, ImageDraw
    folder.mkdir(parents=True)
    out = {}

    def checker(w, h):
        im = Image.new("RGB", (w, h), (255, 255, 255))
        d = ImageDraw.Draw(im)
        for ky in range(0, h // CELL + 1):
            for kx in range(0, w // CELL + 1):
                if (kx + ky) % 2:
                    d.rectangle([kx * CELL, ky * CELL, (kx + 1) * CELL - 1, (ky + 1) * CELL - 1], fill=(0, 0, 0))
        return im

    def stripes(w, h):
        # red: smooth stripes down the picture (they show a sideways shift); green: across it (an up-down shift)
        col = Image.new("L", (w, 1))
        col.putdata([int(128 + 100 * math.sin(2 * math.pi * x / 180.0)) for x in range(w)])
        row = Image.new("L", (1, h))
        row.putdata([int(128 + 100 * math.sin(2 * math.pi * y / 140.0)) for y in range(h)])
        r, g = col.resize((w, h)), row.resize((w, h))
        return Image.merge("RGB", (r, g, ImageChops.add(r, g, scale=2)))

    def plain(w, h, i):
        hue = (i * 0.618034) % 1.0
        rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.5, 0.85))
        dark = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.6, 0.5))
        im = Image.new("RGB", (w, h), rgb)
        d = ImageDraw.Draw(im)
        d.rectangle([0, h * 2 // 3, w, h], fill=dark)
        d.ellipse([w // 8, h // 8, w // 8 + w // 6, h // 8 + w // 6], fill=(255, 244, 200))
        return im

    # each photo is drawn, saved and let go before the next (all of them held at once took about 300 MB, more than a
    # run under the memory guard can spare beside a hidden Chrome)
    made = [("a-checker-wide.jpg", lambda: checker(3000, 2000)), ("b-stripes-wide.jpg", lambda: stripes(3600, 2400)),
            ("c-checker-tall.jpg", lambda: checker(2000, 3000))]
    shapes = [("tall", 1200, 1800), ("wide", 1800, 1200), ("tall", 1200, 1800), ("wide", 1800, 1200), ("square", 1400, 1400), ("tall", 1200, 1800), ("wide", 1800, 1200)]
    for i in range(21):
        way, w, h = shapes[i % len(shapes)]
        made.append((f"p{i + 1:02d}-{way}.jpg", (lambda w=w, h=h, i=i: plain(w, h, i))))
    for name, draw in made:
        im = draw()
        im.save(folder / name, "JPEG", quality=93, subsampling=0)
        out[name] = im.size
        im.close()
        del im
    return out


def sha_tree(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).iterdir()) if p.is_file()}


def luma_row(im, y, x0, x1):
    px = im.load()
    return [0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2] for x in range(x0, x1)]


def luma_col(im, x, y0, y1):
    px = im.load()
    return [0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2] for y in range(y0, y1)]


def crossings(vals, start, level=128.0):
    """Where a run of brightnesses crosses a level, to a fraction of a pixel. A pixel's value is taken to
    sit at its middle, so a sharp edge at 209.0 between pixel 208 and pixel 209 is reported as 209.0."""
    out = []
    for i in range(len(vals) - 1):
        a, b = vals[i], vals[i + 1]
        if (a < level) != (b < level) and a != b:
            out.append(start + i + 0.5 + (level - a) / (b - a))
    return out


def ink_box(im, limit=128):
    """The box around everything darker than the limit, as (x0, y0, x1, y1) with x1, y1 one past the last."""
    return im.convert("L").point(lambda v: 255 if v < limit else 0).getbbox()


# Run in every page before its own scripts: the ONE request that would open Finder (GET /open) never leaves
# the page. It is written down, and answered as the Assistant would answer it.
NO_FINDER_JS = r"""
(function(){
  var real = window.fetch;
  window.__opens = [];
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) {
      window.__opens.push(String(u));
      return Promise.resolve(new Response(JSON.stringify({ok: true, words: 'Opened Carousel in Finder.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    if (window.__hold && window.__hold(String(u))) {
      // the test holds this one request back until it says go (to stop the server in the middle of a save)
      var self = this, args = arguments;
      return new Promise(function(ok, bad){ window.__held = function(){ window.__held = null; real.apply(self, args).then(ok, bad); }; });
    }
    return real.apply(this, arguments);
  };
})();
"""


# ---------------------------------------------------------------------------------------------------------
# the real page in a hidden Chrome
# ---------------------------------------------------------------------------------------------------------

def check_designs_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the real-browser checks of designs, templates and Save slides: no Chrome on this computer", flush=True)
        return
    from PIL import Image, ImageChops, ImageStat
    target = work / "designs"
    src = work / "designs-photos"
    sizes = draw_photos(src)
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos-from", str(src), "--name", "Fake beach"], capture_output=True, text=True, timeout=600)
    if not case("designs browser: the pretend kit was made from photos drawn here (tests/fake_kit.py --photos-from)", r.returncode == 0, (r.stdout + r.stderr)[-400:]):
        return
    ok, out = make_kit(target, "Second shoot", 10)
    if not case("designs browser: a second pretend shoot was made beside it", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name, kit2_name = "2026-11-01 Fake beach", "2026-11-01 Second shoot"
    content = target / "The Assistant" / "Your Content"
    kit, kit2 = content / kit_name, content / kit2_name
    KQ, KQ2 = quote(kit_name), quote(kit2_name)
    designs, designs2 = kit / ".kit" / "designs", kit2 / ".kit" / "designs"
    carousel = kit / "Carousel"
    staging = kit / ".kit" / "design-staging"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    num = {Path(x["file"]).name: x["n"] for x in sheet}
    way = {x["n"]: x["way"] for x in sheet}
    CHECK, STRIPES, CHECK_TALL = num["a-checker-wide.jpg"], num["b-stripes-wide.jpg"], num["c-checker-tall.jpg"]
    talls = [n for n in sorted(way) if way[n] == "tall" and n != CHECK_TALL]
    wides = [n for n in sorted(way) if way[n] == "wide" and n not in (CHECK, STRIPES)]
    case("designs browser: the pretend shoot has 24 photos on its numbered list, wide, tall and square", len(sheet) == 24 and len(talls) >= 8 and len(wides) >= 8, (len(sheet), len(talls), len(wides)))
    photos_before = sha_tree(src)
    photos2_before = sha_tree(kit2 / "Photos")
    kept = {}           # file name in the Carousel folder -> its hash when it was first seen

    def car():
        return sorted(n for n in os.listdir(carousel) if not n.startswith(".")) if carousel.is_dir() else []

    def note_files():
        """Every file now in the Carousel folder is written down; True when none seen before has changed or gone."""
        now = sha_tree(carousel) if carousel.is_dir() else {}
        same = all(now.get(n) == h for n, h in kept.items())
        for n, h in now.items():
            kept.setdefault(n, h)
        return same

    def frame(i, n, x, y=0, w=W, h=H, **more):
        b = {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}
        b.update(more)
        return b

    def text(i, words, x, y, w, font="Inter", size=110, **more):
        b = {"id": i, "type": "text", "text": words, "font": font, "size": size, "weight": 400, "italic": False, "upper": False,
             "al": "center", "ls": 0, "lh": 1.15, "color": "#000000", "x": x, "y": y, "w": w, "h": 110}
        b.update(more)
        return b

    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    tokens = [0]
    times = {}
    again = []          # a Chrome started part way (CHROME_DRIVE_LEAN=1), ended at the end like the first
    early_outside = []  # what the first Chrome asked for, when it was ended part way
    try:
        with cd.Chrome(work=work / "chrome-designs", size=(1280, 900)) as c:
            c.init_script(NO_FINDER_JS)

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return J("Designer.st")

            def did():
                return c.js("Designer.design.id")

            def ready(seconds=20):
                c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def disk(i=None, folder=None):
                return json.loads(((folder or designs) / f"{i or did()}.json").read_text(encoding="utf-8"))

            def settled(seconds=12):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                d = disk(folder=designs2 if c.js("Designer.KIT") == kit2_name else designs)
                return d["state"] == st() and d["name"] == c.js("Designer.design.name")

            def fonts_in(seconds=15):
                try:
                    c.wait_for("Designer.st.blocks.every(function(b){ return b.type !== 'text' || Designer.type.status(b) !== 'wait'; }) && Designer.type.fit(Designer.st) === Designer.st", seconds)
                    return True
                except cd.Timeout:
                    return False

            def new_design(label, state=None, name=None, kitname=kit_name):
                tokens[0] += 1
                body = {"kit": kitname, "token": f"designscheck{tokens[0]:04d}"}
                if state is not None:
                    body.update(stamp=get_json(P, f"/design-state?kit={quote(kitname)}")[1]["stamp"], state=state)
                if name:
                    body["name"] = name
                code, out = post(P, "/design-new", body)
                if code != 200 or not out or not out.get("ok"):
                    case(f"designs browser [{label}]: a new design was made for this part", False, (code, out))
                    raise RuntimeError("no design")
                return out["design"]["id"]

            def open_design(i, kq=KQ):
                c.open(f"{base}/design.html?kit={kq}&design={i}")
                ready()
                fonts_in()
                settled()

            def files(folder=None):
                d = folder or designs
                return sorted(p.name for p in d.glob("*.json") if not p.name.endswith(".prev.json")) if d.is_dir() else []

            def press_save(seconds=90):
                """Press Save slides and wait until it is over, or a question is up. -> the line beside the button"""
                c.click("#save-slides")
                c.wait_for("!Designer.saver.busy() || Designer.saver.asking()", seconds, tell="document.getElementById('save-line').textContent")
                return c.text("#save-line")

            def done(seconds=90):
                c.wait_for("!Designer.saver.busy()", seconds, tell="document.getElementById('save-line').textContent")
                return c.text("#save-line")

            def slide(name):
                return Image.open(carousel / name).convert("RGB")

            def hidden(sel):
                return c.js("(function(e){ return !e || e.hidden || getComputedStyle(e).display === 'none'; })(document.querySelector(%s))" % json.dumps(sel))

            def gallery_open():
                c.click("#new-design")
                c.wait_for("!document.getElementById('gallery').hidden && document.querySelectorAll('#gallery-starters .dz-card').length === Designer.S.starters.length", 8)

            def use(box, nth, seconds=20):
                """Press Use on the nth card of a gallery section and wait for the new design to be open."""
                before = did()
                c.click(f"#gallery-{box} .dz-card .dz-use", nth=nth)
                c.wait_for("document.getElementById('gallery').hidden && Designer.design.id !== %s && Designer.save.idle()" % json.dumps(before), seconds,
                           tell="document.getElementById('gallery-line').textContent")
                return did()

            # ================= the first visit: the bar of designs =================
            c.open(f"{base}/design.html?kit={KQ}")
            ready()
            c.wait_for("Array.prototype.filter.call(document.querySelectorAll('#strip .blk img'), function(i){ return i.naturalWidth > 0; }).length >= 3", 20)
            first = did()
            first_name = "Fake beach carousel 1"
            case("first visit: the design's name is in a box you can type in, with Saved beside it, and the plain name is no longer shown",
                 c.js("document.getElementById('d-name-box').value") == first_name and c.text("#d-status") == "Saved" and hidden("#d-name")
                 and c.js("(function(a, b){ return a.parentNode === b.parentNode && a.parentNode.id === 'g-design'; })(document.getElementById('d-name-box'), document.getElementById('d-status'))"))
            case("first visit: the shoot's own button names the shoot, before the design",
                 c.text("#shoot-btn").startswith("Fake beach") and c.js("document.getElementById('g-shoot').nextElementSibling.id") == "g-design")
            case("first visit: My designs, Duplicate design, + New design and Save as template are in the top row; Fill empty frames is in the selection bar's first line, out of sight while no frame is empty",
                 all(c.js("document.getElementById('tools-designs').contains(document.getElementById(%s))" % json.dumps(i)) for i in ("designs-btn", "dup-design", "new-design", "save-template"))
                 and c.js("document.getElementById('selcap').contains(document.getElementById('fill-holes'))")
                 and c.text("#fill-holes") == "Fill empty frames" and c.js("document.getElementById('fill-holes').disabled") is True and hidden("#fill-holes"))
            case("first visit: Preview swipe and Save slides are in the bar at the bottom of the window, which stays in sight",
                 c.rect("#save-slides")["bottom"] <= 900 and c.rect("#save-slides")["y"] > 780 and c.rect("#preview-btn")["y"] > 780 and c.js("document.getElementById('save-slides').disabled") is False)
            case("first visit: nothing is said beside Save slides, and its question buttons and the folder button are not showing",
                 c.text("#save-line") == "" and hidden("#save-yes") and hidden("#save-no") and hidden("#open-wrap"))
            case("first visit: the top row of buttons is one row at this width (1280)", c.rect("#tools-designs")["h"] < 60, c.rect("#tools-designs"))
            case("first visit: the page has no errors and asked nothing of any address but its own", c.page_errors() == [] and c.outside_requests() == [], (c.page_errors(), c.outside_requests()))

            # ---- rename in place ----
            c.js("(function(e){ e.focus(); e.select(); })(document.getElementById('d-name-box'))")
            c.type_text("Beach day one")
            case("rename: while typing, the line beside the name says Saving...", c.text("#d-status") in ("Saving...", "Saved"))
            case("rename: the new name is saved with the design (the file on the drive has it), and the layout is as it was",
                 settled() and disk()["name"] == "Beach day one" and disk()["rev"] >= 1, disk()["name"])
            c.key("Enter")
            case("rename: Return leaves the box", c.js("document.activeElement.id") != "d-name-box")
            c.js("(function(e){ e.focus(); e.select(); })(document.getElementById('d-name-box'))")
            c.key("Backspace")
            case("rename: an emptied box changes nothing", c.js("document.getElementById('d-name-box').value") == "" and c.js("Designer.design.name") == "Beach day one")
            c.js("document.getElementById('d-name-box').blur()")
            case("rename: leaving the box empty puts the name back in it", c.js("document.getElementById('d-name-box').value") == "Beach day one" and settled() and disk()["name"] == "Beach day one")
            c.js("(function(e){ e.focus(); e.select(); })(document.getElementById('d-name-box'))")
            c.type_text("Oops")
            c.key("Escape")
            case("rename: Escape puts back the name it had when the box was clicked", c.js("document.getElementById('d-name-box').value") == "Beach day one" and settled() and disk()["name"] == "Beach day one", disk()["name"])
            c.js("document.getElementById('d-name-box').focus()")
            c.set_value("#d-name-box", "  <b>Beach</b>   &   \"day\" one  ")
            c.js("document.getElementById('d-name-box').blur()")
            case("rename: a name with markup in it is kept as plain words, tidied (single spaces, none at the ends)",
                 settled() and disk()["name"] == "<b>Beach</b> & \"day\" one" and c.js("document.getElementById('d-name-box').value") == "<b>Beach</b> & \"day\" one"
                 and c.count("#g-design b b") == 0, disk()["name"])
            c.js("document.getElementById('d-name-box').focus()")
            c.set_value("#d-name-box", "Beach day one")
            c.js("document.getElementById('d-name-box').blur()")
            settled()
            c.reload()
            ready()
            case("rename: after a reload the same design is open under its new name", did() == first and c.js("document.getElementById('d-name-box').value") == "Beach day one")
            first_bytes = (designs / f"{first}.json").read_bytes()
            # an address that names a design that is not there opens the newest, and says so
            c.open(f"{base}/design.html?kit={KQ}&design=dnotthere0000")
            ready()
            case("an address naming a design that isn't there: the newest one opens, a line under the slides says so, and the address is put right",
                 did() == first and c.text("#d-note") == "That design isn’t here, so this is your newest one." and c.js("location.search") == f"?kit={KQ}&design={first}"
                 and (designs / f"{first}.json").read_bytes() == first_bytes and files() == [first + ".json"], c.text("#d-note"))

            # ---- + New design: the gallery ----
            gallery_open()
            case("gallery: it opens over the page with Start fresh (Blank, One photo per slide), Your templates and the starter templates",
                 c.count("#gallery-fresh .dz-card") == 2 and c.text("#gallery-fresh .dz-card b", 0) == "Blank" and c.text("#gallery-fresh .dz-card b", 1) == "One photo per slide"
                 and c.count("#gallery-starters .dz-card") == 11 and c.count("#gallery-mine .dz-card") == 0 and "None yet" in c.text("#gallery-mine"))
            case("gallery: it says what will happen, and the tick to fill the frames is on",
                 "Fake beach" in c.text("#gallery-sub") and "new design" in c.text("#gallery-sub") and "stays as it is" in c.text("#gallery-sub")
                 and c.js("document.getElementById('gallery-fill').checked") is True)
            starters = J("Designer.S.starters.map(function(t){ return {id: t.id, name: t.name, slides: t.template.slides, frames: t.template.blocks.filter(function(b){ return b.type !== 'text'; }).length}; })")
            case("gallery: every starter is there by name with its slides and how many photos it has room for",
                 [c.text("#gallery-starters .dz-card b", i) for i in range(11)] == [s["name"] for s in starters]
                 and c.text("#gallery-starters .dz-card small", 0) == f"{starters[0]['slides']} slides · room for {starters[0]['frames']} photos", c.text("#gallery-starters .dz-card small", 0))
            # a little picture is a real drawing of the layout with this shoot's photos
            PAINTED = """(function(sel, nth){
              var cv = document.querySelectorAll(sel)[nth], d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, seen = {}, n = 0;
              var vivid = 0, m = 0;
              for (var i = 0; i < d.length; i += 4 * 7) {
                var k = (d[i] >> 4) + ',' + (d[i + 1] >> 4) + ',' + (d[i + 2] >> 4); if (!seen[k]) { seen[k] = 1; n++; }
                vivid += Math.max(d[i], d[i + 1], d[i + 2]) - Math.min(d[i], d[i + 1], d[i + 2]); m++;
              }
              return {w: cv.width, h: cv.height, cssw: cv.getBoundingClientRect().width, cssh: cv.getBoundingClientRect().height, colors: n, vivid: Math.round(vivid / m)};
            })"""
            c.wait_for("[0,1,2,3,4,5,6,7,8,9,10].every(function(i){ return (%s)('#gallery-starters .dz-card canvas', i).colors > 12; })" % PAINTED, 15)
            pics = [c.call(PAINTED, "#gallery-starters .dz-card canvas", i) for i in range(11)]
            # (v22: a long template's picture fills its card's width, so it may be wider than 256; never wider than its card)
            rooms = J("Array.from(document.querySelectorAll('#gallery-starters .dz-pic')).map(function(p){ return p.clientWidth; })")
            case("gallery: every card's little picture is drawn with this shoot's photos (many colours in each), no taller than 96 and no wider than its card",
                 all(p["colors"] > 12 and p["cssh"] <= 96.5 and p["cssw"] <= max(256, room) + 0.5 for p, room in zip(pics, rooms)), (pics, rooms))
            # (v22: her eight single slides have a little picture each too)
            case("gallery: the little pictures are canvases the page drew; no picture element points anywhere", c.count("#gallery img") == 0 and c.count("#gallery canvas") == 13 + 8)
            c.click("#gallery-fill")
            c.wait_for("!document.getElementById('gallery-fill').checked && document.querySelectorAll('#gallery-starters .dz-card').length === 11", 5)
            c.wait_for("[0,1,2,3,4,5,6,7,8,9,10].every(function(i){ return (%s)('#gallery-starters .dz-card canvas', i).colors > 1; })" % PAINTED, 15)
            pics_off = [c.call(PAINTED, "#gallery-starters .dz-card canvas", i) for i in range(11)]
            case("gallery: with the tick off the frames are drawn empty: every little picture is far less colourful than it was with the photos in",
                 all(off["vivid"] < 30 and on["vivid"] > off["vivid"] + 15 for on, off in zip(pics, pics_off)), [(on["vivid"], off["vivid"]) for on, off in zip(pics, pics_off)])
            c.click("#gallery-fill")
            c.wait_for("document.getElementById('gallery-fill').checked", 5)
            c.key("Escape")
            case("gallery: Escape closes it, and nothing was made", hidden("#gallery") and files() == [first + ".json"])
            gallery_open()
            c.click("#gallery-close")
            case("gallery: Close closes it", hidden("#gallery"))
            gallery_open()
            c.mouse_move(20, 450)
            c.mouse_press()
            c.mouse_release()
            case("gallery: a press beside the sheet closes it", hidden("#gallery"))

            # ---- Blank, and "it never replaces" ----
            gallery_open()
            blank = use("fresh", 0)
            case("new design: Blank makes a NEW design with 5 empty slides on the kit's background and opens it",
                 blank != first and st() == {"slides": 5, "bg": "#ffffff", "blocks": []} and files() == sorted([first + ".json", blank + ".json"]), st())
            case("new design: the first design's file is byte for byte what it was", (designs / f"{first}.json").read_bytes() == first_bytes)
            case("new design: it is named for the shoot with the next free number, and the address names it",
                 c.js("document.getElementById('d-name-box').value") == "Fake beach carousel 1" or c.js("document.getElementById('d-name-box').value") == "Fake beach carousel 2", c.js("document.getElementById('d-name-box').value"))
            case("new design: the address now names the new design", c.js("location.search") == f"?kit={KQ}&design={blank}")
            gallery_open()
            seeded = use("fresh", 1)
            order = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))["picks"]["carousel"]
            case("new design: One photo per slide is the carousel's order, one photo filling each slide",
                 [b["n"] for b in st()["blocks"]] == order and st()["slides"] == len(order) and all(b["w"] == W and b["h"] == H and b["x"] == i * W for i, b in enumerate(st()["blocks"])), st())
            case("new design: three designs now, the first two untouched", len(files()) == 3 and (designs / f"{first}.json").read_bytes() == first_bytes and disk(blank)["state"]["blocks"] == [])

            # ---- every starter template ----
            made = {}
            for i, s in enumerate(starters):
                gallery_open()
                made[s["id"]] = use("starters", i)
                fonts_in()
                lay = st()
                frames = [b for b in lay["blocks"] if b.get("type") != "text"]
                ns = [b["n"] for b in frames]
                shapes_ok = all((way.get(b["n"]) == "wide") if b["w"] / b["h"] > 1.15 else (way.get(b["n"]) == "tall") if b["w"] / b["h"] < 0.9 else True for b in frames)
                tpl = J("Designer.S.starters[%d].template" % i)
                same_places = [(b["x"], b["y"], b["w"], b["h"]) for b in lay["blocks"]] [:len(frames)] == [(b["x"], b["y"], b["w"], b["h"]) for b in tpl["blocks"] if b.get("type") != "text"]
                case(f"starter '{s['name']}': it opens as a new design with its {s['frames']} frames where the template has them, every one filled, no photo twice, wide frames with wide photos and tall with tall",
                     lay["slides"] == s["slides"] and len(frames) == s["frames"] and all(n is not None for n in ns) and len(set(ns)) == len(ns) and shapes_ok and same_places
                     and c.page_errors() == [], (ns, [way.get(n) for n in ns], c.page_errors()[:2]))
            case("starters: each press made one more design, and none took another's place (3 + 11 files, the first still byte for byte the same)",
                 len(files()) == 14 and len(set(made.values())) == 11 and (designs / f"{first}.json").read_bytes() == first_bytes, len(files()))
            # Title slide is no longer a starter (Nicole's v22). A design laid out as it was (as one made from it before
            # would be) still opens, and its words still get their heights from their lines.
            title_state = {"slides": 4, "bg": "#f4efe6", "blocks": [
                frame(1, None, 140, 760, 800, 470), frame(2, None, W), frame(3, None, 2 * W), frame(4, None, 3 * W),
                {"id": 5, "type": "text", "text": "Your title", "font": "Playfair Display", "size": 150, "weight": 400, "italic": False, "upper": False, "al": "center", "ls": 0,
                 "lh": 1.15, "color": "#2a2622", "x": 90, "y": 260, "w": 900, "h": 110},
                {"id": 6, "type": "text", "text": "a line of your own", "font": "Montserrat", "size": 34, "weight": 400, "italic": False, "upper": True, "al": "center", "ls": 8,
                 "lh": 1.15, "color": "#2a2622", "x": 140, "y": 470, "w": 800, "h": 110}]}
            open_design(new_design("the Title slide layout", title_state, "Title slide as it was"))
            fonts_in()
            try:
                c.wait_for("Designer.st.blocks.filter(function(b){ return b.type === 'text'; }).every(function(b){ return b.h !== 110; })", 10)
            except cd.Timeout:
                pass
            tb = [b for b in st()["blocks"] if b.get("type") == "text"]
            case("a design laid out as the 'Title slide' starter was: after its fonts arrive the words' heights follow their lines (no longer the stand-in 110)",
                 len(tb) == 2 and tb[0]["text"] == "Your title" and all(abs(b["h"] - round(b["h"] / (b["size"] * b["lh"])) * b["size"] * b["lh"]) < 0.02 for b in tb) and settled(), tb)

            # ---- the tick off: empty frames, and Fill N empty frames ----
            gallery_open()
            c.click("#gallery-fill")
            holes_id = use("starters", [s["id"] for s in starters].index("st-stack"))
            case("tick off: the frames come empty", all(b["n"] is None for b in st()["blocks"]) and len(st()["blocks"]) == 6 and c.count("#strip .blk.hole") == 6)
            case("tick off: the button says how many frames are empty", c.text("#fill-holes") == "Fill 6 empty frames" and c.js("document.getElementById('fill-holes').disabled") is False)
            c.click("#fill-holes")
            lay = st()
            case("fill: one press fills every empty frame, by shape, with no photo twice, and it is one Undo step",
                 all(b["n"] is not None for b in lay["blocks"]) and len({b["n"] for b in lay["blocks"]}) == 6
                 and all((way[b["n"]] == "wide") if b["w"] / b["h"] > 1.15 else (way[b["n"]] == "tall") for b in lay["blocks"])
                 and c.text("#fill-holes") == "Fill empty frames" and c.js("document.getElementById('fill-holes').disabled") is True and settled(), [(b["n"], way.get(b["n"])) for b in lay["blocks"]])
            c.click("#undo")
            case("fill: Undo empties them again", all(b["n"] is None for b in st()["blocks"]) and c.text("#fill-holes") == "Fill 6 empty frames")
            # a photo taken out of one frame leaves the spot ("Take the photo out" is the empty-frame button)
            c.click("#fill-holes")
            b0 = st()["blocks"][0]
            c.click(f"#strip .blk[data-id='{b0['id']}']")
            c.click("#selbar button[data-a='empty']")
            after = st()["blocks"][0]
            case("empty frame: Take the photo out leaves the frame where it was, empty, and the fill button counts it",
                 after["n"] is None and (after["x"], after["y"], after["w"], after["h"]) == (b0["x"], b0["y"], b0["w"], b0["h"]) and c.text("#fill-holes") == "Fill 1 empty frame", after)
            settled()

            # ---- Save slides asks about an empty frame, in the page ----
            before = car()
            always = [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")]
            line = press_save()
            case("save with an empty frame: the line beside the button asks first, with Save anyway and Go back, and nothing is drawn or sent yet",
                 line == "The frame on slide 1 is still empty. It will be left as plain background." and not hidden("#save-yes") and not hidden("#save-no")
                 and c.js("document.getElementById('save-slides').disabled") is True and car() == before and not (staging.is_dir() and os.listdir(staging)), line)
            case("save with an empty frame: the question is right after the Save slides button and its two answers right after the question, on one line",
                 abs(c.rect("#save-yes")["cy"] - c.rect("#save-slides")["cy"]) < 4 and 0 <= c.rect("#save-line")["x"] - c.rect("#save-slides")["right"] < 24
                 and 0 <= c.rect("#save-yes")["x"] - c.rect("#save-line")["right"] < 24 and c.rect("#save-no")["x"] > c.rect("#save-yes")["right"]
                 and c.js("document.getElementById('savebar').contains(document.getElementById('save-yes'))"), (c.rect("#save-line"), c.rect("#save-yes")))
            case("save with an empty frame: Preview swipe, the grid tick and Save slides are exactly where they were before the question came",
                 [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")] == always)
            c.click("#save-no")
            case("Go back: nothing is saved, the line is cleared, and the button works again",
                 done() == "" and hidden("#save-yes") and c.js("document.getElementById('save-slides').disabled") is False and car() == before)
            press_save()
            c.click("#save-yes")
            line = done()
            got_name = c.js("Designer.design.name")
            case("Save anyway: the slides are saved, and the line says how many, under what name, and that nothing was replaced",
                 line == f"Saved 4 slides in your Carousel folder, named \"{got_name}\". Nothing was replaced." and car() == [f"{got_name} - slide {i:02d}.jpg" for i in range(1, 5)], (line, car()))
            im = slide(f"{got_name} - slide 01.jpg")
            case("the buttons that are always in the bar are where they were, now that the long line about the save is showing",
                 [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")] == always, ([c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")], always))
            case("Save anyway: the empty frame's slide is plain background (white)", im.size == (W, H) and min(e[0] for e in ImageStat.Stat(im).extrema) > 245, ImageStat.Stat(im).extrema)
            note_files()

            # ---- Open the Carousel folder ----
            case("after a save: Open the Carousel folder is on the same line as the words about the save, right after them",
                 not hidden("#open-wrap") and abs(c.rect("#open-carousel")["cy"] - c.rect("#save-line")["cy"]) < 16 and 0 <= c.rect("#open-carousel")["x"] - c.rect("#save-line")["right"] < 24,
                 (c.rect("#open-carousel"), c.rect("#save-line")))
            ob = c.rect("#open-carousel")
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            opens = J("window.__opens")
            case("Open the Carousel folder: it asks the Assistant for this kit's own Carousel folder (the request is checked; Finder is never opened by this test)",
                 opens == [f"/open?kit={KQ}&sub=Carousel"], opens)
            ol = c.rect("#open-line")
            case("Open the Carousel folder: the answer shows in a small note right over the button, inside the window, and the button has not moved",
                 c.text("#open-line") == "Opened Carousel in Finder." and 0 <= ob["y"] - ol["bottom"] < 14 and ol["x"] < ob["right"] and ol["right"] > ob["x"] and ol["x"] >= 0 and ol["right"] <= 1280 and ol["y"] >= 0
                 and c.rect("#open-carousel") == ob and c.js("document.getElementById('open-wrap').contains(document.getElementById('open-line'))"), (ol, ob))

            # ---- saved again with nothing changed ----
            before = car()
            sent_before = sum(1 for r_ in list(c.requests) if "/design-slide" in r_["url"])
            line = press_save()
            sent_after = sum(1 for r_ in list(c.requests) if "/design-slide" in r_["url"])
            case("save again, nothing changed: 'Already saved as ...', no new file, and not one slide was drawn or sent", line == f"Already saved as \"{got_name}\". Change something to save a new set." and car() == before
                 and not hidden("#open-wrap") and note_files() and sent_after == sent_before and sent_before == 4, (line, sent_before, sent_after))
            # ---- changed, then saved: a second set beside the first ----
            c.click("#fill-holes")
            settled()
            case("a change takes away the line about the last save, and the folder button with it", c.text("#save-line") == "" and hidden("#open-wrap") and c.text("#open-line") == "")
            line = press_save()
            case("changed and saved again: a new set named '... (2)' beside the first, which is untouched",
                 line == f"Saved 4 slides in your Carousel folder, named \"{got_name} (2)\". Nothing was replaced."
                 and car() == sorted(before + [f"{got_name} (2) - slide {i:02d}.jpg" for i in range(1, 5)]) and note_files(), (line, car()))
            im = slide(f"{got_name} (2) - slide 01.jpg")
            case("changed and saved again: slide 1 now has its photo on it", min(e[0] for e in ImageStat.Stat(im).extrema) < 200)

            # ---- a bare slide is asked about too ----
            bare = new_design("bare", {"slides": 3, "bg": "#f4efe6", "blocks": [frame(1, talls[0], 0), frame(2, None, 2260, 100, 500, 500)]}, name="Bare one")
            open_design(bare)
            line = press_save()
            case("a slide with nothing on it and an empty frame: both are named in one question",
                 line == "The frame on slide 3 is still empty. It will be left as plain background. Slide 2 has nothing on it. It will be saved as a plain slide.", line)
            # changing the design while the question is up answers it "go back"
            c.click("#slides-plus")
            case("a change to the design while the question is up takes the question away (nothing is saved)",
                 done() == "" and hidden("#save-yes") and not any(n.startswith("Bare one") for n in car()))

            # ---- a photo across two slides joins up at the seam ----
            seam = new_design("seam", {"slides": 4, "bg": "#ffffff", "blocks": [frame(1, talls[0], 0), frame(2, STRIPES, 1080), frame(3, talls[1], 3240)]}, name="Seam test")
            open_design(seam)
            c.click("#strip .blk[data-id='2']")
            c.click("#selbar button[data-a='span2']")
            b = next(x for x in st()["blocks"] if x["id"] == 2)
            case("seam: Across 2 slides puts the wide photo over slides 2 and 3", (b["x"], b["y"], b["w"], b["h"]) == (1080, 0, 2160, H) and settled(), b)
            line = press_save()
            names = [f"Seam test - slide {i:02d}.jpg" for i in range(1, 5)]
            if case("seam: saved as four slides", line.startswith("Saved 4 slides") and all(n in car() for n in names), line):
                s2, s3 = slide(names[1]), slide(names[2])
                both = Image.new("RGB", (2 * W, H))
                both.paste(s2, (0, 0))
                both.paste(s3, (W, 0))
                # what it should be: the photo itself, covering 2160 by 1350 from its middle (3600x2400 -> 2160x1440)
                want = Image.open(src / "b-stripes-wide.jpg").convert("RGB").resize((2160, 1440), Image.LANCZOS).crop((0, 45, 2160, 1395))

                def off(dx):
                    a = both.crop((max(0, dx) + 8, 8, 2 * W - 8 + min(0, dx), H - 8))
                    e = want.crop((max(0, -dx) + 8, 8, 2 * W - 8 - max(0, dx), H - 8))
                    return sum(ImageStat.Stat(ImageChops.difference(a, e)).mean) / 3

                d = {dx: off(dx) for dx in (-2, -1, 0, 1, 2)}
                case("seam: slides 2 and 3 side by side are the photo itself, in the right place (nearer to it than when moved one pixel either way)",
                     d[0] < 5 and d[0] < d[-1] and d[0] < d[1] and d[-1] < d[-2] and d[1] < d[2], d)
                # the two columns that meet at the join are neighbours in the photo, like any other two. Brightness is
                # compared, not one colour: a JPEG keeps colour at half the sharpness, and the two slides are two JPEGs.
                r2, r3 = s2.convert("L"), s3.convert("L")

                def col_diff(a, xa, b_, xb):
                    return ImageStat.Stat(ImageChops.difference(a.crop((xa, 0, xa + 1, H)), b_.crop((xb, 0, xb + 1, H)))).mean[0]

                seam_d = col_diff(r2, W - 1, r3, 0)
                inner = [col_diff(r2, x, r2, x + 1) for x in range(40, W - 1, 97)] + [col_diff(r3, x, r3, x + 1) for x in range(40, W - 1, 97)]
                far = col_diff(r2, W - 1, r3, 12)
                case("seam: the last column of slide 2 and the first of slide 3 differ no more than any two neighbouring columns do (and far less than columns 12 apart)",
                     seam_d <= max(inner) + 1.0 and seam_d < far / 3, (round(seam_d, 2), round(max(inner), 2), round(far, 2)))
                wl = want.convert("L")

                def col_err(a, xa, xw):
                    return ImageStat.Stat(ImageChops.difference(a.crop((xa, 0, xa + 1, H)), wl.crop((xw, 0, xw + 1, H)))).mean[0]

                e_left = {dx: col_err(r2, W - 1, W - 1 + dx) for dx in (-1, 0, 1)}
                e_right = {dx: col_err(r3, 0, W + dx) for dx in (-1, 0, 1)}
                case("seam: each of those two columns is the photo's own column at that place (nearer to it than to the column on either side)",
                     e_left[0] < 2.5 and e_left[0] < e_left[-1] and e_left[0] < e_left[1] and e_right[0] < 2.5 and e_right[0] < e_right[-1] and e_right[0] < e_right[1],
                     ({k: round(v, 2) for k, v in e_left.items()}, {k: round(v, 2) for k, v in e_right.items()}))
                print(f"NOTE  seam: columns at the join differ by {seam_d:.2f} levels of brightness; neighbouring columns inside a slide by up to {max(inner):.2f}; columns 12 apart by {far:.2f}", flush=True)
            case("seam: nothing that was in the Carousel folder changed", note_files())

            # ---- a ruler photo lands where the layout says ----
            fx, fy, fw, fh, zoom, ox, oy = 137, 211, 800, 600, 1.4, 0.3, 0.5
            ruler = new_design("ruler", {"slides": 2, "bg": "#2060c0", "blocks": [frame(1, CHECK, fx, fy, fw, fh, ox=ox, oy=oy, zoom=zoom), frame(2, talls[2], 1080)]}, name="Ruler test")
            open_design(ruler)
            line = press_save()
            if case("ruler: saved", line.startswith("Saved 2 slides") and "Ruler test - slide 01.jpg" in car(), line):
                im = slide("Ruler test - slide 01.jpg")
                pw, ph = sizes["a-checker-wide.jpg"]
                cc = max(fw / pw, fh / ph) * zoom
                left, top = fx + (fw - pw * cc) * ox, fy + (fh - ph * cc) * oy
                want_x = [left + k * CELL * cc for k in range(0, 14) if fx + 6 < left + k * CELL * cc < fx + fw - 6]
                want_y = [top + k * CELL * cc for k in range(0, 10) if fy + 6 < top + k * CELL * cc < fy + fh - 6]
                row_y = int(want_y[0] + CELL * cc / 2)
                col_x = int(want_x[0] + CELL * cc / 2)
                got_x = crossings(luma_row(im, row_y, fx + 4, fx + fw - 4), fx + 4)
                got_y = crossings(luma_col(im, col_x, fy + 4, fy + fh - 4), fy + 4)
                worst_x = max([abs(a - b_) for a, b_ in zip(got_x, want_x)] or [99])
                worst_y = max([abs(a - b_) for a, b_ in zip(got_y, want_y)] or [99])
                case(f"ruler: the checkerboard's {len(want_x)} upright edges on the slide are where the layout puts them, within one pixel",
                     len(got_x) == len(want_x) and worst_x <= 1.0, (len(got_x), len(want_x), round(worst_x, 3), [round(v, 2) for v in got_x[:3]], [round(v, 2) for v in want_x[:3]]))
                case(f"ruler: its {len(want_y)} level edges too", len(got_y) == len(want_y) and worst_y <= 1.0, (len(got_y), len(want_y), round(worst_y, 3)))
                print(f"NOTE  ruler: the worst edge is {worst_x:.2f} px off sideways and {worst_y:.2f} px off up and down", flush=True)
                # the frame's own four edges: the background stops and the photo starts
                px = im.load()

                def is_bg(x, y):
                    r_, g_, b_ = px[x, y]
                    return abs(r_ - 0x20) < 26 and abs(g_ - 0x60) < 26 and abs(b_ - 0xC0) < 26

                edge_ok = all(is_bg(fx - 3, y) and not is_bg(fx + 2, y) and not is_bg(fx + fw - 3, y) and is_bg(fx + fw + 2, y) for y in range(fy + 20, fy + fh - 20, 37)) \
                    and all(is_bg(x, fy - 3) and not is_bg(x, fy + 2) and not is_bg(x, fy + fh - 3) and is_bg(x, fy + fh + 2) for x in range(fx + 20, fx + fw - 20, 37))
                case("ruler: the photo is cut off at its frame's four edges, with the background right up to them", edge_ok)
                case("ruler: outside the frame the slide is the background color", is_bg(40, 40) and is_bg(1040, 1300) and is_bg(fx + fw + 60, fy + 100), px[40, 40])
            case("ruler: nothing that was in the Carousel folder changed", note_files())

            # ---- the preview is the same drawing ----
            open_design(seam)
            c.click("#preview-btn")
            c.wait_for("!document.getElementById('preview').hidden && document.querySelectorAll('#pv-track canvas').length === 4", 5)
            case("preview: a phone-shaped box opens over the page, on slide 1 of 4, with four dots and only the forward arrow",
                 c.text("#pv-count") == "1 of 4" and c.count("#pv-dots b") == 4 and c.count("#pv-dots b.on") == 1
                 and c.js("getComputedStyle(document.getElementById('pv-prev')).visibility") == "hidden" and c.js("getComputedStyle(document.getElementById('pv-next')).visibility") == "visible")
            vr = c.rect("#pv-view")
            case("preview: the slide is the shape of an Instagram slide (4 by 5) and fits the window", abs(vr["w"] / vr["h"] - 0.8) < 0.01 and vr["w"] <= 380 and vr["bottom"] < 900, vr)
            case("preview: no name, logo or account on it", c.count("#preview img") == 0 and not re.search(r"instagram|@", c.text("#preview"), re.I), c.text("#preview"))
            SAMPLE = """(function(k, pts){
              var cv = document.querySelectorAll('#pv-track canvas')[k], ctx = cv.getContext('2d');
              return pts.map(function(p){ var d = ctx.getImageData(Math.floor(p[0] * cv.width), Math.floor(p[1] * cv.height), 1, 1).data; return [d[0], d[1], d[2]]; });
            })"""
            pts = [[0.1, 0.1], [0.3, 0.5], [0.5, 0.25], [0.7, 0.8], [0.9, 0.4], [0.5, 0.9]]
            c.wait_for("(%s)(1, [[0.5, 0.5]])[0].join() !== '255,255,255'" % SAMPLE, 10)
            s2 = slide(names[1])
            got = c.call(SAMPLE, 1, pts)
            near = all(max(abs(a - b_) for a, b_ in zip(g, s2.getpixel((int(p[0] * W), int(p[1] * H))))) < 40 for g, p in zip(got, pts))
            case("preview: slide 2 in the preview is the same picture as the saved slide 2 (six places compared)", near, (got, [s2.getpixel((int(p[0] * W), int(p[1] * H))) for p in pts]))
            c.click("#pv-next")
            case("preview: the arrow goes to the next slide ('2 of 4', second dot, both arrows)", c.text("#pv-count") == "2 of 4"
                 and c.js("Array.prototype.map.call(document.querySelectorAll('#pv-dots b'), function(d){ return d.classList.contains('on') ? 1 : 0; }).join('')") == "0100"
                 and c.js("getComputedStyle(document.getElementById('pv-prev')).visibility") == "visible")
            c.key("ArrowRight")
            c.key("ArrowRight")
            case("preview: the arrow keys turn the slides, and stop at the last one", c.text("#pv-count") == "4 of 4" and c.js("getComputedStyle(document.getElementById('pv-next')).visibility") == "hidden")
            c.key("ArrowRight")
            c.key("ArrowLeft")
            case("preview: the left arrow key goes back", c.text("#pv-count") == "3 of 4")
            case("preview: the strip's own keys are left alone while it is open (nothing moved on the slides)", st() == disk(seam)["state"])
            mid = (vr["cx"], vr["cy"])
            c.drag(mid, (mid[0] + 30, mid[1]), steps=4)
            case("preview: a drag of 30 px puts the slide back", c.text("#pv-count") == "3 of 4")
            c.drag(mid, (mid[0] + 70, mid[1]), steps=6)
            case("preview: a drag of 70 px to the right shows the slide before", c.text("#pv-count") == "2 of 4")
            c.drag(mid, (mid[0] - 70, mid[1]), steps=6)
            case("preview: a drag of 70 px to the left shows the next one", c.text("#pv-count") == "3 of 4")
            c.mouse_move(*mid)
            c.mouse_press()
            c.mouse_move(mid[0] - 55, mid[1])
            tr = c.js("document.getElementById('pv-track').style.transform")
            case("preview: while it is dragged the slides follow the pointer", "translateX(" in tr and abs(float(re.search(r"translateX\((-?[0-9.]+)px", tr).group(1)) - (-2 * vr["w"] - 55)) < 1.5, tr)
            c.mouse_release()
            case("preview: let go past 40 px, it turns", c.text("#pv-count") == "4 of 4")
            c.key("Escape")
            case("preview: Escape closes it, and its pictures are let go", hidden("#preview") and c.count("#pv-track canvas") == 0 and c.js("Designer.saver.preview.shelf") is None)
            c.click("#preview-btn")
            c.wait_for("!document.getElementById('preview').hidden", 5)
            case("preview: opened again it starts at slide 1", c.text("#pv-count") == "1 of 4")
            c.click("#pv-close")
            case("preview: Close closes it", hidden("#preview"))

            # ---- the profile grid's crop lines ----
            case("grid crop: not showing until it is ticked", c.js("getComputedStyle(document.querySelector('#over .sv-crop.sv-l')).display") == "none")
            c.click("#gridcrop")
            s = c.js("Designer.scale")
            sr, lr, rr = c.rect("#strip"), c.rect("#over .sv-crop.sv-l"), c.rect("#over .sv-crop.sv-r")
            case("grid crop: ticked, the two edges of slide 1 that the profile grid leaves out are shaded: 33.75 slide pixels each side",
                 abs(lr["x"] - sr["x"]) < 0.6 and abs(lr["w"] / s - 33.75) < 1.5 and abs((rr["right"] - sr["x"]) / s - W) < 1.5 and abs(rr["w"] / s - 33.75) < 1.5
                 and abs(lr["h"] - sr["h"]) < 1.5, (lr["w"] / s, rr["w"] / s))
            case("grid crop: it changes nothing in the design (only a way of looking)", st() == disk(seam)["state"] and c.js("Designer.save.idle()"))
            c.js("document.getElementById('view-size').focus({preventScroll: true})")
            c.key("ArrowRight")
            s2_ = c.js("Designer.scale")
            case("grid crop: it follows the strip when the strip is drawn bigger", abs(c.rect("#over .sv-crop.sv-l")["w"] / s2_ - 33.75) < 1.5 and s2_ > s)
            c.key("ArrowLeft")
            c.click("#gridcrop")
            case("grid crop: unticked, it is gone", c.js("getComputedStyle(document.querySelector('#over .sv-crop.sv-l')).display") == "none")

            # ---- My designs, Duplicate ----
            n_files = len(files())
            c.click("#designs-btn")
            c.wait_for("!document.getElementById('designs-pop').hidden", 3)
            items = J("Array.prototype.map.call(document.querySelectorAll('#designs-pop .dz-item'), function(b){ return {id: b.dataset.design, name: b.querySelector('b').textContent, sub: b.querySelector('small').textContent, cur: b.classList.contains('cur')}; })")
            case("My designs: it lists every design of this shoot and no other shoot's", sorted(i["id"] + ".json" for i in items) == files() and len(items) == n_files and c.text("#designs-pop .dz-pophead") == "Fake beach designs", len(items))
            case("My designs: newest first, each with its slide count and when it was edited; the open one says so",
                 [i["id"] for i in items] == [x["id"] for x in sorted((disk(f[:-5]) for f in files()), key=lambda x: -x["t"])]
                 and all(re.fullmatch(r"\d+ slides · edited (just now|\d+ min ago)( · open now)?", i["sub"]) for i in items)
                 and [i["id"] for i in items if i["cur"]] == [seam] and next(i for i in items if i["cur"])["sub"].endswith("· open now"), items[:3])
            case("My designs: no button to delete anything", c.count("#designs-pop button:not(.dz-item)") == 0)
            c.key("Escape")
            case("My designs: Escape closes the list", hidden("#designs-pop"))
            c.click("#designs-btn")
            c.click("#title")
            case("My designs: a press elsewhere closes the list", hidden("#designs-pop"))
            c.click("#designs-btn")
            c.click(f"#designs-pop .dz-item[data-design='{first}']")
            c.wait_for("Designer.design.id === %s" % json.dumps(first), 10)
            case("My designs: a click opens that design (the address, the name box and the strip follow)",
                 c.js("location.search") == f"?kit={KQ}&design={first}" and c.js("document.getElementById('d-name-box').value") == "Beach day one" and st() == disk(first)["state"])
            bytes_before = {f: (designs / f).read_bytes() for f in files()}
            c.click("#dup-design")
            c.wait_for("Designer.design.id !== %s && Designer.save.idle()" % json.dumps(first), 10)
            dup = did()
            case("Duplicate design: a copy named '... copy' is made and opened; every other design's file is byte for byte what it was",
                 disk(dup)["name"] == "Beach day one copy" and disk(dup)["state"] == disk(first)["state"] and c.js("document.getElementById('d-name-box').value") == "Beach day one copy"
                 and len(files()) == n_files + 1 and all((designs / f).read_bytes() == b_ for f, b_ in bytes_before.items()), disk(dup)["name"])
            c.click("#dup-design")
            c.wait_for("Designer.design.id !== %s && Designer.save.idle()" % json.dumps(dup), 10)
            case("Duplicate design: a copy of a copy gets its own name", disk()["name"] == "Beach day one copy copy" and len(files()) == n_files + 2, disk()["name"])

            # ---- Save as template, and using it in another shoot ----
            tdir = studio / "design-templates"
            lay_id = new_design("template", {"slides": 3, "bg": "#e9e1d6", "blocks": [
                frame(1, wides[0], 1080, 0, 2160, H), frame(2, talls[3], 90, 110, 900, 1130, ox=0.2, zoom=1.5), text(3, "Our day", 140, 60, 800, size=60)]}, name="Wide closer")
            open_design(lay_id)
            c.click("#save-template")
            c.wait_for("!document.getElementById('tpl-dialog').hidden", 3)
            case("Save as template: a small sheet asks for a name (the design's own to start with) and says the photos aren't kept in it",
                 c.js("document.getElementById('tpl-name').value") == "Wide closer" and "photos aren’t kept" in c.text("#tpl-dialog") and "any shoot" in c.text("#tpl-dialog"))
            c.set_value("#tpl-name", "   ")
            c.click("#tpl-save")
            case("Save as template: no name is asked for again, and nothing is saved", c.text("#tpl-line") == "Give it a name, up to 80 letters." and not (tdir.is_dir() and list(tdir.glob("*.json"))))
            c.set_value("#tpl-name", "My wide closer")
            c.click("#tpl-save")
            c.wait_for("document.getElementById('tpl-line').textContent.indexOf('Saved') === 0", 8)
            tfiles = sorted(tdir.glob("*.json"))
            tpl = json.loads(tfiles[0].read_text(encoding="utf-8")) if tfiles else {}
            tb = tpl.get("template", {}).get("blocks", [])
            case("Save as template: the line says it is saved and where to find it; Save is off and the other button now says Close",
                 c.text("#tpl-line") == "Saved \"My wide closer\" to your templates. You'll find it under + New design, in any shoot."
                 and c.js("document.getElementById('tpl-save').disabled") is True and c.text("#tpl-cancel") == "Close", c.text("#tpl-line"))
            case("Save as template: the Assistant kept one template, shared by every shoot: frames empty and back to the middle, numbered in reading order, the words kept",
                 len(tfiles) == 1 and tpl.get("name") == "My wide closer" and tpl.get("from") == "Fake beach" and len(tb) == 3
                 and [b.get("n", "none") for b in tb if b.get("type") != "text"] == [None, None] and [b["slot"] for b in tb if b.get("type") != "text"] == [2, 1]
                 and all(b["ox"] == 0.5 and b["zoom"] == 1 for b in tb if b.get("type") != "text") and tb[2]["text"] == "Our day"
                 and "names" not in tpl and not re.search(r"\.jpg|/private|Photos", tfiles[0].read_text(encoding="utf-8")), tpl)
            case("Save as template: the open design itself is as it was", disk(lay_id)["state"] == st() and [b.get("n") for b in st()["blocks"]][:2] == [wides[0], talls[3]])
            c.click("#tpl-cancel")
            case("Save as template: Close closes the sheet", hidden("#tpl-dialog"))
            gallery_open()
            case("gallery: the template is now under Your templates, with where it came from",
                 c.count("#gallery-mine .dz-card") == 1 and c.text("#gallery-mine .dz-card b") == "My wide closer" and c.text("#gallery-mine .dz-card small") == "3 slides · room for 2 photos · from Fake beach", c.text("#gallery-mine"))
            c.key("Escape")
            # an empty design cannot be made a template: the sheet says why, and offers only Close
            open_design(blank)
            c.click("#save-template")
            c.wait_for("!document.getElementById('tpl-dialog').hidden", 3)
            case("Save as template, nothing on the slides: it says to add something first, and there is nothing to press but Close",
                 c.text("#tpl-line") == "Add some photos or text first, then save it as a template." and c.js("document.getElementById('tpl-save').disabled") is True and c.text("#tpl-cancel") == "Close")
            c.key("Escape")
            case("Save as template: still one template", len(list(tdir.glob("*.json"))) == 1)

            # ---- the shoot menu ----
            c.click("#shoot-btn")
            c.wait_for("!document.getElementById('shoot-pop').hidden", 3)
            shoots = J("Array.prototype.map.call(document.querySelectorAll('#shoot-pop a.dz-item'), function(a){ return {href: a.getAttribute('href'), name: a.querySelector('b').textContent, sub: a.querySelector('small').textContent, cur: a.classList.contains('cur')}; })")
            case("shoot menu: every shoot with its photo and design counts; the open one says so",
                 sorted((s_["name"], s_["sub"]) for s_ in shoots) == sorted([("Fake beach", f"24 photos · {len(files())} designs · open now"), ("Second shoot", "10 photos · 0 designs")]), shoots)
            case("shoot menu: each shoot is a plain link to its own designer, named by its kit folder and nothing else",
                 sorted(s_["href"] for s_ in shoots) == sorted([f"/design.html?kit={KQ}", f"/design.html?kit={KQ2}"]))
            a_files = files()
            a_bytes = {f: (designs / f).read_bytes() for f in a_files}
            c.click("#shoot-pop a.dz-item:not(.cur)")
            c.wait_for("window.Designer && Designer.KIT === %s && Designer.st" % json.dumps(kit2_name), 20)
            ready()
            case("shoot menu: choosing the other shoot goes to that shoot's own designer, which makes its first design",
                 c.text("#title") == "Second shoot" and c.js("location.search").startswith(f"?kit={KQ2}&design=") and len(files(designs2)) == 1
                 and c.js("document.getElementById('d-name-box').value") == "Second shoot carousel 1")
            c.click("#designs-btn")
            c.wait_for("!document.getElementById('designs-pop').hidden", 3)
            case("My designs in the second shoot: only that shoot's one design, under that shoot's name",
                 c.count("#designs-pop .dz-item") == 1 and c.text("#designs-pop .dz-pophead") == "Second shoot designs" and c.js("document.querySelector('#designs-pop .dz-item').dataset.design") == did())
            c.key("Escape")
            # the template from the first shoot, used here
            gallery_open()
            case("template in another shoot: it is offered there too", c.count("#gallery-mine .dz-card") == 1 and c.text("#gallery-mine .dz-card b") == "My wide closer")
            used = use("mine", 0)
            fonts_in()
            lay = st()
            sheet2 = json.loads((kit2 / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
            way2 = {x["n"]: x["way"] for x in sheet2}
            fr = [b for b in lay["blocks"] if b.get("type") != "text"]
            case("template in another shoot: it opens as a new design of THAT shoot, its frames filled with that shoot's photos by shape, its words kept",
                 lay["slides"] == 3 and lay["bg"] == "#e9e1d6" and len(fr) == 2 and all(b["n"] in way2 for b in fr) and way2[fr[0]["n"]] == "wide" and way2[fr[1]["n"]] == "tall"
                 and (fr[0]["x"], fr[0]["w"]) == (1080, 2160) and [b["text"] for b in lay["blocks"] if b.get("type") == "text"] == ["Our day"]
                 and (designs2 / f"{used}.json").is_file() and len(files(designs2)) == 2, lay)
            case("template in another shoot: the first shoot's designs are untouched, and the template file is as it was",
                 files() == a_files and all((designs / f).read_bytes() == b_ for f, b_ in a_bytes.items()) and json.loads(tfiles[0].read_text(encoding="utf-8")) == tpl)
            settled()

            # ---- words on a saved slide sit where the screen showed them ----
            reach = c.js("Designer.type.fonts.reach()")
            blocks = [text(1, "Hamburg gently\nquiet joy", 140, 300, 800, font="Inter", size=120),
                      text(2, "Left & low", 1080 + 90, 820, 700, font="Cormorant Garamond", size=150, al="left", italic=True, ls=6)]
            if reach:
                blocks.append(text(3, "A Google face,\nwrapped onto more than one line here", 2160 + 120, 200, 840, font="Lora", size=96, weight=700, al="right"))
            words_id = new_design("words", {"slides": 3, "bg": "#ffffff", "blocks": blocks}, name="Words test")
            # A second hidden Chrome at twice the size. Under CHROME_DRIVE_LEAN=1 (a computer short of memory, every
            # test under a memory guard: two Chromes at once take about 2 GB) the first one is ended before the second
            # starts, and a fresh one takes its place after: the second window is still a window of its own.
            lean = os.environ.get("CHROME_DRIVE_LEAN") == "1"
            if lean:
                early_outside.extend(c.outside_requests())      # kept for the whole-run check at the end
                c.stop()
            with cd.Chrome(work=work / "chrome-designs-2x", size=(1500, 900), scale=2) as c2:
                c2.init_script(NO_FINDER_JS)
                c2.open(f"{base}/design.html?kit={KQ}&design={words_id}")
                c2.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S", 20)
                c2.wait_for("Designer.st.blocks.every(function(b){ return Designer.type.status(b) === 'ready'; }) && Designer.type.fit(Designer.st) === Designer.st && Designer.save.idle()", 20,
                            tell="JSON.stringify(Designer.st.blocks.map(function(b){ return Designer.type.status(b); }))")
                c2.js("document.getElementById('view-size').focus({preventScroll: true})")
                for _ in range(8):
                    if c2.js("Designer.view() >= Designer.M.RULES.view.max"):
                        break
                    c2.key("ArrowRight")
                c2.js("window.scrollTo(0, document.getElementById('stage').offsetTop - 4)")
                c2.js("document.getElementById('stage').scrollLeft = 0")
                c2.mouse_move(5, 5)
                s = c2.js("Designer.scale")
                on_screen = {}
                for k in range(len(blocks)):
                    # bring slide k to the left of what shows, then photograph it
                    c2.js("document.getElementById('stage').scrollLeft = %f" % max(0, k * W * s - 20))
                    sr = c2.rect("#strip")
                    shot = Image.open(c2.screenshot(f"words-{k}.png")).convert("RGB")
                    x0, y0 = sr["x"] + k * W * s, sr["y"]
                    crop = shot.crop((int((x0 + 3) * 2), int((y0 + 3) * 2), int((x0 + W * s - 3) * 2), int((y0 + H * s - 3) * 2)))
                    bb = ink_box(crop)
                    on_screen[k] = None if not bb else tuple((v + (int((x0 + 3) * 2) if i % 2 == 0 else int((y0 + 3) * 2))) / 2.0 for i, v in enumerate(bb))
                    if on_screen[k]:
                        on_screen[k] = ((on_screen[k][0] - x0) / s, (on_screen[k][1] - y0) / s, (on_screen[k][2] - x0) / s, (on_screen[k][3] - y0) / s)
                c2.click("#save-slides")
                c2.wait_for("!Designer.saver.busy()", 60)
                line = c2.text("#save-line")
                errs2 = c2.page_errors()
            if lean:
                # the helpers above all use "c", so the fresh Chrome is given that name
                c = cd.Chrome(work=work / "chrome-designs-again", size=(1280, 900)).start()
                again.append(c)
                c.init_script(NO_FINDER_JS)
            if case("words: saved (from a second window, drawn at twice the size so the screen can be measured)", line.startswith("Saved 3 slides") and errs2 == [], (line, errs2)):
                label = {0: "a font the Assistant carries (Inter)", 1: "a carried font in italics, set left, with letter spacing (Cormorant Garamond)", 2: "a Google font in bold, set right (Lora)"}
                for k in range(len(blocks)):
                    saved_bb = ink_box(slide(f"Words test - slide {k + 1:02d}.jpg"))
                    scr = on_screen[k]
                    worst = max(abs(a - b_) for a, b_ in zip(saved_bb, scr)) if saved_bb and scr else 99
                    case(f"words: {label[k]}: the ink on the saved slide is where the screen showed it, within 3 slide pixels (the screen is measured at 0.89 of a slide pixel)",
                         worst <= 3.0, (saved_bb, tuple(round(v, 1) for v in scr) if scr else None))
                    print(f"NOTE  words, slide {k + 1}: saved ink box {saved_bb}, on screen {tuple(round(v, 1) for v in scr) if scr else None}, worst side {worst:.1f} px", flush=True)
            if not reach:
                print("SKIP  words in a Google font: Google Fonts cannot be reached from here right now", flush=True)
            case("words: nothing that was in the Carousel folder changed", note_files())

            # ---- a font that cannot be loaded is asked about before it is saved in Georgia ----
            if reach:
                c.set_offline(True)
                fb = new_design("fallback", {"slides": 2, "bg": "#ffffff", "blocks": [frame(1, talls[0], 0), text(2, "Not here", 1080 + 140, 300, 800, font="Oswald", size=110)]}, name="Fallback test")
                c.open(f"{base}/design.html?kit={KQ}&design={fb}")
                ready()
                fonts_in(25)
                before = car()
                line = press_save(60)
                case("no internet: Save slides asks before saving words in Georgia, naming the font",
                     line == "“Oswald” couldn’t be loaded, so that text will be saved in Georgia." and not hidden("#save-yes") and car() == before, line)
                c.click("#save-no")
                case("no internet: Go back saves nothing", done() == "" and car() == before)
                c.set_offline(False)

            # ---- a photo that cannot be read ----
            open_design(seeded)
            before = car()
            errs_before = c.page_errors()
            c.block_urls([f"*kit-photo*&n={order[2]}&size=*"])
            line = press_save(60)
            case(f"a photo that can't be read: the line says which one, and that nothing was added (photo {order[2]} was made unreadable)",
                 line == f"Photo {order[2]} can’t be read. Is the drive plugged in? Nothing was added to your Carousel folder." and car() == before
                 and c.js("document.getElementById('save-slides').disabled") is False and hidden("#open-wrap"), line)
            c.block_urls([])
            c.clear_errors()            # the blocked picture is the one "error" that part was meant to make
            case("a photo that can't be read: the page had no error before it", errs_before == [], errs_before[:3])
            t0 = time.time()
            line = press_save(60)
            times["7 slides"] = time.time() - t0
            seeded_name = c.js("Designer.design.name")
            case("readable again: the same press now saves all seven, as one set", line == f"Saved 7 slides in your Carousel folder, named \"{seeded_name}\". Nothing was replaced."
                 and [n for n in car() if n not in before] == [f"{seeded_name} - slide {i:02d}.jpg" for i in range(1, 8)] and note_files(), line)

            # ---- the server goes away after the third slide ----
            c.click("#slides-plus")
            settled()
            before = car()
            waiting_before = set(os.listdir(staging)) if staging.is_dir() else set()
            c.js("window.__hold = function(u){ return u.indexOf('/design-slide') === 0 && /[?&]i=4(&|$)/.test(u); }; true")
            line = press_save()
            case("cut off: the new, bare eighth slide is asked about first", line == "Slide 8 has nothing on it. It will be saved as a plain slide.", line)
            c.click("#save-yes")
            c.wait_for("typeof window.__held === 'function'", 30)
            fresh = [d_ for d_ in staging.iterdir() if d_.name not in waiting_before] if staging.is_dir() else []
            staged = sorted(p.name for d_ in fresh for p in d_.iterdir() if p.name.startswith("slide-"))
            case("cut off: three slides of this press had arrived in the hidden waiting place when the Assistant was stopped, none in the Carousel folder",
                 len(fresh) == 1 and staged == ["slide-01.jpg", "slide-02.jpg", "slide-03.jpg"] and car() == before and c.text("#save-line") == "Making slide 4 of 8...", (staged, c.text("#save-line")))
            case("cut off: while a save runs the Save slides button is off, and a second press does nothing",
                 c.js("document.getElementById('save-slides').disabled") is True and c.js("(function(){ document.getElementById('save-slides').click(); return Designer.saver.busy(); })()") is True
                 and c.text("#save-line") == "Making slide 4 of 8...")
            srv.stop()
            c.js("window.__hold = null; window.__held(); true")
            line = done(40)
            case("cut off: the line says where it stopped and that nothing was added, and the button works again",
                 line == "Stopped at slide 4. Nothing was added to your Carousel folder. Press Save slides to try again."
                 and car() == before and c.js("document.getElementById('save-slides').disabled") is False and hidden("#open-wrap"), line)
            srv = Server(env, port)
            P2 = srv.start()
            if case("cut off: the Assistant came back at the same address", P2 == P, (P, P2)):
                press_save(90)
                c.click("#save-yes")
                line = done(90)
                new = [n for n in car() if n not in before]
                case("cut off: a fresh press saves one whole set, and only one",
                     line == f"Saved 8 slides in your Carousel folder, named \"{seeded_name} (2)\". Nothing was replaced." and new == [f"{seeded_name} (2) - slide {i:02d}.jpg" for i in range(1, 9)] and note_files(), (line, new))

            # ---- the connection drops at the very last step: the same press finishes as one set ----
            c.click("#g-bg .sw[data-c='#111111']")
            settled()
            before = car()
            c.js("window.__hold = function(u){ return u.indexOf('/design-commit') === 0; }; true")
            press_save()
            c.click("#save-yes")
            c.wait_for("typeof window.__held === 'function'", 30)
            case("dropped at the last step: every slide is waiting and the line says they are being put in the folder; none is in it yet",
                 c.text("#save-line") == "Putting the slides in your Carousel folder..." and car() == before, c.text("#save-line"))
            srv.stop()
            c.js("window.__hold = null; window.__held(); true")
            time.sleep(0.6)
            still = c.js("Designer.saver.busy()")
            srv = Server(env, port)
            P5 = srv.start()
            if case("dropped at the last step: the Assistant came back at the same address while the page was still trying", P5 == P and still is True, (P, P5, still)):
                line = done(60)
                new = [n for n in car() if n not in before]
                case("dropped at the last step: the page asked again by itself under the same name for the press, and one set was saved, once",
                     line == f"Saved 8 slides in your Carousel folder, named \"{seeded_name} (3)\". Nothing was replaced." and new == [f"{seeded_name} (3) - slide {i:02d}.jpg" for i in range(1, 9)] and note_files(), (line, new))

            # ---- the commit itself is cut off part way: the next press finishes it under the same name ----
            srv.stop()
            once = work / "designs-stop-once"
            env_stop = dict(env, DESIGN_TEST_STOP="after-3", DESIGN_TEST_STOP_ONCE=str(once))
            srv = Server(env_stop, port)
            P3 = srv.start()
            if case("interrupted commit: the Assistant came back at the same address", P3 == P, (P, P3)):
                c.click("#slides-minus")
                settled()
                before = car()
                line = press_save(90)
                part = [n for n in car() if n not in before]
                case("interrupted commit: stopped dead after three of seven files, the line says nothing was lost and to press again",
                     once.exists() and line == "Couldn't finish saving your slides. Nothing was lost. Press Save slides again and it will finish."
                     and part == [f"{seeded_name} (4) - slide {i:02d}.jpg" for i in range(1, 4)], (line, part))
                sent_before = sum(1 for r_ in list(c.requests) if "/design-slide" in r_["url"])
                line = press_save(90)
                sent_after = sum(1 for r_ in list(c.requests) if "/design-slide" in r_["url"])
                new = [n for n in car() if n not in before]
                case("interrupted commit: the next press finishes the SAME set under the SAME name (no '... 5', nothing drawn again, nothing replaced)",
                     line == f"Saved 7 slides in your Carousel folder, named \"{seeded_name} (4)\". Nothing was replaced." and new == [f"{seeded_name} (4) - slide {i:02d}.jpg" for i in range(1, 8)]
                     and note_files() and not any(n.startswith(f"{seeded_name} (5)") for n in car()) and sent_after == sent_before and sent_before >= 7, (line, new, sent_before, sent_after))
                line = press_save(60)
                case("interrupted commit: pressed once more it is 'Already saved as ...'", line == f"Already saved as \"{seeded_name} (4)\". Change something to save a new set." and [n for n in car() if n not in before] == new, line)
            srv.stop()
            srv = Server(env, port)
            P4 = srv.start()
            case("the Assistant is back as it was for the rest", P4 == P, (P, P4))

            # ---- twenty slides ----
            twenty = [n for n in sorted(way) if n != CHECK_TALL][:20]
            big = new_design("twenty", {"slides": 20, "bg": "#111111", "blocks": [frame(i + 1, n, i * W) for i, n in enumerate(twenty)]
                                        + [text(30, "Twenty", 140, 500, 800, font="Inter", size=140, color="#ffffff")]}, name="Twenty slides")
            open_design(big)
            before = car()
            heap0 = {m["name"]: m["value"] for m in c.cdp("Performance.getMetrics")["metrics"]} if c.cdp("Performance.enable") is not None else {}
            t0 = time.time()
            line = press_save(180)
            times["20 slides"] = time.time() - t0
            stats = J("Designer.saver.stats")
            new = [n for n in car() if n not in before]
            case("twenty slides: all twenty are saved as one set", line == "Saved 20 slides in your Carousel folder, named \"Twenty slides\". Nothing was replaced."
                 and new == [f"Twenty slides - slide {i:02d}.jpg" for i in range(1, 21)], (line, len(new)))
            c.cdp("HeapProfiler.collectGarbage")
            heap1 = {m["name"]: m["value"] for m in c.cdp("Performance.getMetrics")["metrics"]}
            case("twenty slides: the page never held more than two full-size pictures at once, and holds none afterwards",
                 stats["peak"] <= 2 and stats["held"] <= 2 and stats["slides"] == 20, stats)
            case("twenty slides: the page's memory afterwards is sane (under 120 MB of script memory, no canvases left behind)",
                 heap1.get("JSHeapUsedSize", 0) < 120 * 1024 * 1024 and c.count("canvas") == 0, (round(heap1.get("JSHeapUsedSize", 0) / 1e6, 1), c.count("canvas")))
            print(f"NOTE  twenty slides: script memory {heap0.get('JSHeapUsedSize', 0) / 1e6:.1f} MB before, {heap1.get('JSHeapUsedSize', 0) / 1e6:.1f} MB after; most pictures held at once: {stats['peak']}", flush=True)
            case("twenty slides: nothing that was in the Carousel folder changed", note_files())

            # ---- every slide ever saved, the photos, and what Claude is told ----
            sets = [n for n in car() if " - slide " in n]
            wrong = [n for n in sets if slide(n).size != (W, H)]
            case(f"every one of the {len(sets)} slides saved in this run is 1080 by 1350", len(sets) >= 50 and not wrong, wrong[:3])
            case("no file in the Carousel folder was ever changed or taken away after it was first written (hashes)", note_files())
            case("the shoot's photos are byte for byte what they were (hashes)", sha_tree(src) == photos_before and sha_tree(kit2 / "Photos") == photos2_before)
            leftovers = sorted(p.name for p in carousel.iterdir() if p.name.startswith(".") and not p.name == ".DS_Store")
            case("nothing half-made is in the Carousel folder", leftovers == [], leftovers)
            rec = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))
            case("the kit's record names the newest laid-out set, written by the Assistant's own command",
                 rec.get("carousel_set", {}).get("base") == "Twenty slides" and len(rec.get("laid_out") or []) >= 8, rec.get("carousel_set", {}).get("base"))
            r = subprocess.run(["/usr/bin/python3", str(SCRIPTS / "home.py"), "pending"], capture_output=True, text=True, env=env)
            case("Claude is told through the waiting list: 'ARRANGED: <kit> | design | 20 slides'", f"ARRANGED: {kit_name} | design | 20 slides" in r.stdout, r.stdout[-300:])

            # ---- at a phone's width ----
            c.phone(390, 844)
            c.open(f"{base}/design.html?kit={KQ}&design={seam}")
            ready()
            fonts_in()

            def no_sideways():
                return c.js("document.documentElement.scrollWidth <= window.innerWidth + 1")

            case("phone width: the page does not scroll sideways, and the bar with Save slides is at the bottom of the screen",
                 no_sideways() and c.rect("#save-slides")["bottom"] <= 844 and c.rect("#save-slides")["right"] <= 390 and c.rect("#preview-btn")["x"] >= 0, c.rect("#save-slides"))
            gallery_open()
            sh = c.rect("#gallery .dz-sheet")
            case("phone width: the gallery fits the screen, one card to a row, each with its Use button in reach",
                 no_sideways() and sh["x"] >= 0 and sh["right"] <= 390 and sh["bottom"] <= 844 and c.rect("#gallery-starters .dz-card", 0)["w"] > 250
                 and c.rect("#gallery-starters .dz-card .dz-use", 0)["right"] <= sh["right"] and c.rect("#gallery-close")["right"] <= 390, sh)
            c.click("#gallery-close")
            c.click("#preview-btn")
            c.wait_for("!document.getElementById('preview').hidden", 5)
            pr = c.rect("#preview .pv-phone")
            case("phone width: the preview fits the screen, whole, with Close in reach",
                 no_sideways() and pr["x"] >= 0 and pr["right"] <= 390 and pr["bottom"] <= 844 and pr["y"] >= 0 and c.rect("#pv-close")["bottom"] <= 844 and abs(c.rect("#pv-view")["w"] - 342) < 1, pr)
            c.click("#pv-close")
            always = [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")]
            line = press_save(60)
            lr_ = c.rect("#save-line")
            case("phone width: the line Save slides brings is whole, inside the screen, in the bar, above the buttons, with the folder button on a row of its own over it (so its answer never covers the line)",
                 line.startswith("Already saved as \"Seam test\"") and lr_["x"] >= 0 and lr_["right"] <= 390 and lr_["bottom"] <= 844 and no_sideways()
                 and c.rect("#open-carousel")["right"] <= 390 and c.rect("#open-carousel")["bottom"] <= 844
                 and c.rect("#open-carousel")["y"] >= 0 and c.rect("#open-carousel")["bottom"] <= lr_["y"] + 1 and lr_["bottom"] <= c.rect("#save-slides")["y"] + 1, (line, lr_, c.rect("#open-carousel")))
            case("phone width: Preview swipe, the grid tick and Save slides did not move when the line came", [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")] == always,
                 ([c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")], always))
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            ol = c.rect("#open-line")
            case("phone width: the folder button's answer is over the button and inside the screen", ol["x"] >= 0 and ol["right"] <= 390 and ol["bottom"] <= c.rect("#open-carousel")["y"] and ol["y"] >= 0, ol)
            c.click("#slides-plus")
            line = press_save(60)
            case("phone width: a question is above its two answers, which are above the buttons that are always there, all inside the screen",
                 line.startswith("Slide 5 has nothing on it") and c.rect("#save-yes")["right"] <= 390 and c.rect("#save-no")["right"] <= 390 and c.rect("#save-no")["bottom"] <= 844 and no_sideways()
                 and c.rect("#save-line")["bottom"] <= c.rect("#save-yes")["y"] + 1 and c.rect("#save-yes")["bottom"] <= c.rect("#save-slides")["y"] + 1
                 and [c.rect(x) for x in ("#preview-btn", "#gridcrop", "#save-slides")] == always, (line, c.rect("#save-line"), c.rect("#save-yes")))
            c.click("#save-no")
            done()
            c.click("#designs-btn")
            c.wait_for("!document.getElementById('designs-pop').hidden", 3)
            pp = c.rect("#designs-pop")
            case("phone width: the list of designs stays inside the screen", pp["x"] >= 0 and pp["right"] <= 390 and no_sideways(), pp)
            c.key("Escape")
            c.desktop()

            # ================= the whole run =================
            case("the page threw no error and logged none, in the whole run (but for the photo made unreadable on purpose)", c.page_errors() == [], c.page_errors()[:4])
            outside = [u for u in early_outside + c.outside_requests() if "fonts.googleapis.com" not in u and "fonts.gstatic.com" not in u]
            case("the page asked nothing of any address but the Assistant's and Google Fonts, in the whole run", outside == [], outside[:4])
    finally:
        for x in again:
            x.stop()
        srv.stop()
    for k, v in times.items():
        print(f"TIME  Save slides, {k} (pretend photos of 2 to 9 megapixels): {v:.1f} s from the press to the line", flush=True)
