#!/usr/bin/env python3
"""Check what Nicole's v22 (Nov 10) added to the carousel designer. A part of tests/design_check.py (--only v22).

    + Add slides        the window in adding mode: her heading and line, every button Add, what is picked goes after
                        the last slide and nothing is replaced, 20 slides at most, an empty design is + New design
    Single slides       her eight, between Start fresh and Your templates, as small cards
    Starter templates   her five first, then the six she kept; the five she removed are gone from the window, and a
                        design that was made from one of them opens and saves as before
    previews            a long template's picture fills its card
    Rename              on a card under Your templates: Return or a press elsewhere saves, Escape cancels; the
                        Assistant keeps the version before; refused by request when it is not a name or not a template
    centered            the middle of a slide, a seam the photo sits across, and half way up: the blue lines and
                        her five labels while dragging, not with Alt or with Snap off, and for a moment after an arrow key
    Save slides         an untouched design's slides are what the screen shows

Three parts, as the other parts have: the tables and the rules by themselves (check_v22_page), the routes by request
(check_v22_server, a pretend kit and a page server on the port it is given), and the real page in a hidden Chrome
(check_v22_browser, another pretend kit and server). Her numbers are in this file's own tables (HERS_STARTERS,
HERS_SINGLES); when her page is beside the project (reference-private/, never pushed) the tables are also checked
against it, and that one case is left out when it is not there.
"""
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
HER_PAGE = ROOT / "reference-private" / "nicole-handoff-v22-2026-11-10" / "Carousel designer and reel picker" / "pages" / "carousel-designer.html"
W, H = 1080, 1350
M_, G_ = 70, 24                 # her m and g


def _grid(cols, rows, g=G_):
    cw, ch = (W - (cols - 1) * g) / cols, (H - (rows - 1) * g) / rows
    return [(c * (cw + g), r * (ch + g), cw, ch) for r in range(rows) for c in range(cols)]


_HALF = H / 2 - 1.5 * M_
# (id, name, slides, background, frames as (x, y, w, h)) exactly as her page has them, in her order
HERS_STARTERS = [
    ("tp-postcard", "Postcard collage", 9, "#f6f1e7",
     [(0, 0, 1080, 1350), (1534, 176, 562, 594), (1151, 878, 361, 405), (2160, 0, 1080, 1350), (3413, 68, 907, 405), (3316, 878, 551, 472),
      (4320, 0, 1080, 1350), (5400, 351, 432, 418), (6026, 0, 454, 634), (5724, 837, 454, 459), (6480, 0, 1080, 1350), (7787, 432, 626, 675),
      (8640, 0, 1080, 1350)]),
    ("tp-layered", "Layered trio", 3, "#ffffff", [(0, 400, 1560, 950), (1685, 40, 1385, 970), (880, 70, 545, 605), (975, 740, 855, 610)]),
    ("tp-overlay-frames", "Overlay, column and frames", 5, "#f4f1ec",
     [(0, 0, 1080, 1350), (283, 353, 499, 644), (1080, 0, 1594, 1350), (2751, 141, 412, 403), (2751, 589, 412, 403), (3390, 190, 780, 865),
      (4470, 190, 780, 865)]),
    ("tp-seam-editorial", "Across the seam into a collage", 5, "#f2f0ec",
     [(324, 266, 1511, 772), (2510, 230, 560, 860), (3240, 0, 487, 721), (3780, 62, 425, 608), (3727, 721, 557, 629), (4454, 190, 786, 954)]),
    ("tp-gallery", "Gallery walk", 5, "#ffffff",
     [(295, 354, 507, 701), (1080, 0, 1080, 1350), (2160, 0, 1080, 1350), (3443, 228, 549, 953), (4059, 228, 549, 953), (4667, 228, 549, 953)]),
    ("st-story", "Story mix", 7, "#f4efe6",
     [(0, 0, W, H), (W, 0, 2 * W, H), (3 * W + M_, M_, W - 2 * M_, _HALF), (3 * W + M_, H / 2 + M_ / 2, W - 2 * M_, _HALF),
      (4 * W + 90, 120, 600, 900), (4 * W + 750, 560, 660, 660), (5 * W + 470, 170, 520, 780), (6 * W, 0, W, H)]),
    ("st-pano", "Panorama opener", 5, "#ffffff", [(0, 0, W, H), (W, 0, 2 * W, H), (3 * W, 0, W, H), (4 * W, 0, W, H)]),
    ("st-stack", "Stacked horizontals", 4, "#ffffff",
     [(0, 0, W, H), (W + M_, M_, W - 2 * M_, _HALF), (W + M_, H / 2 + M_ / 2, W - 2 * M_, _HALF), (2 * W + M_, M_, W - 2 * M_, _HALF),
      (2 * W + M_, H / 2 + M_ / 2, W - 2 * M_, _HALF), (3 * W, 0, W, H)]),
    ("st-peek", "Seam peek", 5, "#e9e1d6",
     [(0, 0, W, H), (W + 90, 200, 640, 960), (2 * W - 300, 520, 600, 600), (2 * W + 420, 150, 560, 840), (3 * W, 0, W, H), (4 * W, 0, W, H)]),
    ("st-border", "Editorial borders", 5, "#ffffff", [(k * W + 90, 110, 900, 1130) for k in range(5)]),
    ("st-wide3", "One wide across three", 3, "#ffffff", [(0, 0, 3 * W, H)]),
]
HERS_SINGLES = [
    ("cs-border", "One with a border", 1, "#ffffff", [(90, 110, 900, 1130)]),
    ("cs-2t", "Two stacked", 1, "#ffffff", [(M_, M_, W - 2 * M_, _HALF), (M_, H / 2 + M_ / 2, W - 2 * M_, _HALF)]),
    ("cs-three", "Three across", 1, "#ebe9e5", [(0, 460, 308, 336), (355, 460, 344, 336), (742, 460, 338, 336)]),
    ("cs-4", "Four", 1, "#ffffff", _grid(2, 2)),
    ("cs-9", "Nine", 1, "#ffffff", _grid(3, 3)),
    ("cs-mosaic", "Playful mosaic", 1, "#f2efe8",
     [(251, 175, 193, 268), (462, 51, 189, 392), (668, 88, 172, 172), (668, 277, 253, 391), (382, 460, 269, 412), (668, 685, 253, 194), (617, 897, 304, 287)]),
    ("cs-mood", "Mood board", 1, "#dcdad5",
     [(213, 315, 223, 319), (463, 225, 232, 234), (453, 472, 287, 310), (176, 634, 264, 376), (463, 787, 196, 293), (697, 672, 168, 302)]),
    ("cs-overlap", "Overlapping collage", 1, "#d6d4cc",
     [(92, 101, 312, 312), (433, 101, 309, 312), (301, 342, 356, 231), (694, 481, 271, 269), (226, 575, 674, 450), (756, 993, 258, 256)]),
]
REMOVED = [("st-grid", "Four-photo grid"), ("st-title", "Title slide"), ("st-film", "Film strip"), ("st-pairs", "Side by side"), ("st-bigsmall", "Big and small")]
# her words, exactly
ADD_TITLE = "Add slides"
ADD_SUB = "Pick what to add. It goes after your last slide, and nothing you made is replaced: one slide at a time, or a whole template."
SECTIONS = ["Start fresh", "Single slides", "Your templates", "Starter templates"]
LABELS = ["Centered", "Centered side to side", "Centered up and down", "Centered on the seam", "Centered on the seam, and up and down"]
MAX_WORDS = "Instagram allows up to 20 slides."
# Film strip as it was (one of the five she removed): a design made from it must open and save as before
FILM = {"slides": 3, "bg": "#111111", "blocks": [{"id": i + 1, "n": None, "x": i * W + 40, "y": 275, "w": 1000, "h": 800, "ox": 0.5, "oy": 0.5, "zoom": 1, "slot": i + 1}
                                                   for i in range(3)]}
APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable


def _r(v):
    return round(float(v), 2)


def frames_of(tpl):
    """A template's frames as rounded (x, y, w, h), in list order (which is the stacking and the filling order)."""
    return [(_r(b["x"]), _r(b["y"]), _r(b["w"]), _r(b["h"])) for b in tpl["blocks"] if b.get("type") != "text"]


def hers(frames, off=0):
    return [(_r(x + off), _r(y), _r(w), _r(h)) for x, y, w, h in frames]


def _src():
    sys.path.insert(0, str(SCRIPTS))
    import design_page
    return {n: s for n, s in design_page.SCRIPTS}


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


def her_numbers():
    """{id: (name, slides, bg, frames)} for the layouts her page writes in plain numbers, or None when her page is
    not beside the project."""
    if not HER_PAGE.is_file():
        return None
    out = {}
    for line in HER_PAGE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\{ id: '((?:tp|cs)-[a-z0-9-]+)', name: '([^']+)', slides: (\d+), bg: '(#[0-9a-f]{6})', frames: \[(.*)\], texts: \[\] \},?\s*$", line)
        if not m:
            continue
        fr = re.findall(r"F\(([^()]*)\)", m.group(5))
        if not fr or not all(re.fullmatch(r"\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*", f) for f in fr):
            continue                            # written with her W, H, m and g: this file's own table has those
        out[m.group(1)] = (m.group(2), int(m.group(3)), m.group(4), [tuple(int(v) for v in f.split(",")) for f in fr])
    return out


RULES_JS = r"""
var out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
function F(id, n, x, y, w, h){ return {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; }
this.DESIGN_LIMITS = CAROUSEL_LIMITS;
(new Function(MODEL_SRC)).call(this); (new Function(PLAN_SRC)).call(this);
var M = this.DesignModel, P = this.DesignPlan, W = 1080, H = 1350;
t('the reach of the centers is 14 screen pixels and the flash lasts 1.4 s (hers); the edges keep their 10', M.RULES.centerPx === 14 && M.RULES.centerFlash === 1400 && M.RULES.snapPx === 10);
// a 400 by 500 frame on a 3-slide strip, with nothing else on it
var st = {slides: 3, bg: '#ffffff', blocks: [F(1, 1, 100, 100, 400, 500)]}, b = st.blocks[0], o = {snap: true, thr: 20, cthr: 28}, r;
r = M.move(st, b, 245, 30, o);         // its middle would be at 545: within reach of 540, the middle of slide 1
t('the middle of a slide: the frame is pulled so its middle is at 540', r.x === 340 && r.mid && r.mid.x === 540 && r.mid.y === null && !r.mid.seam, r);
t('... and the label is "Centered side to side"', M.midWords(r.mid) === 'Centered side to side', M.midWords(r.mid));
t('... no pink line on the axis that centered', r.gx.length === 0, r.gx);
r = M.move(st, b, 0, 330, o);          // its middle would be at 680: within reach of 675
t('half way up: the frame is pulled so its middle is at 675, and the label is "Centered up and down"', r.y === 425 && r.mid && r.mid.y === 675 && r.mid.x === null && M.midWords(r.mid) === 'Centered up and down', r);
t('... the level line runs over the one slide the frame is on', r.mid.slide === 0 && r.mid.span === 1, r.mid);
r = M.move(st, b, 75, 330, o);         // its left edge would be at 175: within reach of 180, a sixth of the slide; its middle is far from 540
t('... the edges still snap on the other axis (its left edge goes to a sixth of the slide, with a pink line there), and not on the centered one', r.x === 180 && eq(r.gx, [180]) && r.gy.length === 0 && r.y === 425 && r.mid && r.mid.x === null, r);
r = M.move(st, b, 250, 320, o);
t('both: "Centered", at 340, 425', r.x === 340 && r.y === 425 && M.midWords(r.mid) === 'Centered' && r.gx.length === 0 && r.gy.length === 0, r);
r = M.move(st, b, 1330, 0, o);         // the middle of slide 2 (1620)
t('the middle of the second slide: 1620', r.x === 1420 && r.mid && r.mid.x === 1620 && r.mid.slide === 1 && r.mid.span === 1, r);
// a seam: only one the frame actually sits across
var wide = {slides: 3, bg: '#ffffff', blocks: [F(1, 1, 700, 100, 600, 500)]}, wb = wide.blocks[0];
r = M.move(wide, wb, 70, 0, o);        // 770..1370, its middle at 1070: across the seam at 1080
t('a seam the frame sits across: its middle is pulled to 1080, "Centered on the seam"', r.x === 780 && r.mid && r.mid.x === 1080 && r.mid.seam === true && M.midWords(r.mid) === 'Centered on the seam', r);
t('... the level line would run over both slides it is on', r.mid.slide === 0 && r.mid.span === 2, r.mid);
r = M.move(wide, wb, 70, 320, o);
t('a seam and half way up: "Centered on the seam, and up and down"', r.x === 780 && r.y === 425 && M.midWords(r.mid) === 'Centered on the seam, and up and down', r);
var small = {slides: 3, bg: '#ffffff', blocks: [F(1, 1, 100, 100, 60, 60)]};
r = M.move(small, small.blocks[0], 965, 0, {snap: true, thr: 2, cthr: 28});     // 1065..1125: its middle at 1095, but the reach is 28 and... it does sit across
t('a small frame that does sit across the seam centers on it', r.mid && r.mid.seam === true && r.x === 1050, r);
r = M.move(small, small.blocks[0], 915, 0, {snap: true, thr: 2, cthr: 60});     // 1015..1075: its middle at 1045, within 60 of the seam, but not across it
t('a frame that is near a seam but not across it does not center on the seam', !r.mid || !r.mid.seam, r);
// no centering: Alt or Snap off (snap false), or no reach given
r = M.move(st, b, 245, 330, {snap: false, thr: 20, cthr: 28});
t('with Snap off (or Alt held) nothing centers and nothing snaps: the frame is where the hand put it', r.x === 345 && r.y === 430 && r.mid === null && !r.gx.length && !r.gy.length, r);
r = M.move(st, b, 245, 330, {snap: true, thr: 2});
t('without a reach for the centers, moving is as it was before (edges only)', r.mid === null && r.x === 345 && r.y === 430, r);
r = M.move(st, b, 300, 30, o);
t('out of reach of every middle: no blue line', r.mid === null, r);
// held on the strip: no line where the thing does not really sit
var tall = {slides: 1, bg: '#ffffff', blocks: [F(1, 1, 0, 0, 3000, 500)]};
r = M.move(tall, tall.blocks[0], -935, 0, {snap: true, thr: 2, cthr: 28});
t('a thing held at the strip\'s edge shows no centered line it is not on', !r.mid || r.mid.x === null || Math.abs(r.x + 1500 - r.mid.x) < 0.01, r);
// the flash after an arrow key
t('centered (within a pixel) side to side', M.midWords(M.centered(st, F(1, 1, 340.4, 100, 400, 500))) === 'Centered side to side');
t('centered up and down', M.midWords(M.centered(st, F(1, 1, 100, 425, 400, 500))) === 'Centered up and down');
t('centered both ways', M.midWords(M.centered(st, F(1, 1, 1420, 425, 400, 500))) === 'Centered');
t('centered on a seam it sits across', M.midWords(M.centered(st, F(1, 1, 780, 100, 600, 500))) === 'Centered on the seam');
t('centered on a seam, and up and down', M.midWords(M.centered(st, F(1, 1, 780, 425, 600, 500))) === 'Centered on the seam, and up and down');
t('two pixels off: not centered', M.centered(st, F(1, 1, 342, 100, 400, 500)) === null && M.centered(st, F(1, 1, 100, 427, 400, 500)) === null);
t('a thing whose middle is on a seam it does not sit across... cannot be: but one off the strip\'s end is not centered', M.centered({slides: 1, bg: '#fff', blocks: []}, F(1, 1, 1420, 100, 400, 500)) === null);
t('her five labels, and none for nothing', eq([M.midWords({x: 1, y: 1}), M.midWords({x: 1, y: null}), M.midWords({x: null, y: 1}), M.midWords({x: 1, y: null, seam: true}), M.midWords({x: 1, y: 1, seam: true}), M.midWords(null)], LABELS.concat([''])));
// ---- adding to a carousel ----
var base = {slides: 4, bg: '#f4efe6', blocks: [F(1, 1, 0, 0, W, H), F(2, 2, W, 0, 2 * W, H), {id: 3, type: 'text', text: 'hello', x: 3 * W + 90, y: 200, w: 800, h: 110}]};
var before = JSON.stringify(base), add = {slides: 1, bg: '#ebe9e5', blocks: [F(1, null, 0, 460, 308, 336), F(2, null, 355, 460, 344, 336)]};
r = P.addStories(base, add, {});
t('adding a single slide: one more slide, after the last', r.st.slides === 5 && r.first === 4, r);
t('... what was there is exactly as it was (the same blocks, in the same order), and the layout given was not changed', JSON.stringify(r.st.blocks.slice(0, 3)) === JSON.stringify(JSON.parse(before).blocks) && JSON.stringify(base) === before);
t('... the new frames sit on the new slide, with ids after the highest', eq(r.st.blocks.slice(3).map(function(x){ return [x.id, x.x, x.y, x.w, x.h, x.n]; }), [[4, 4320, 460, 308, 336, null], [5, 4675, 460, 344, 336, null]]), r.st.blocks.slice(3));
t('... the design keeps its own background', r.st.bg === '#f4efe6');
r = P.addStories(base, {slides: 1, bg: '#f4efe6', blocks: []}, {});
t('a blank slide: one more slide and nothing else', r.st.slides === 5 && r.st.blocks.length === 3);
var photos = [1, 2, 3, 4, 5, 6, 7, 8].map(function(n){ return {n: n, w: 2, h: 3, way: 'tall'}; });
r = P.addStories(base, add, {fill: true, photos: photos, carousel: []});
t('with the tick on, only the new frames are filled, from the photos not used yet', eq(r.st.blocks.slice(3).map(function(x){ return x.n; }), [3, 4]) && JSON.stringify(r.st.blocks.slice(0, 3)) === JSON.stringify(JSON.parse(before).blocks), r.st.blocks);
var per = P.onePerStory(base, photos);
t('one photo per slide when adding: the next five photos not used yet, each filling a slide', per.slides === 5 && eq(per.blocks.map(function(x){ return [x.n, x.x, x.y, x.w, x.h]; }), [3, 4, 5, 6, 7].map(function(n, i){ return [n, i * W, 0, W, H]; })), per);
var nineteen = {slides: 19, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H)]};
r = P.addStories(nineteen, add, {});
t('19 slides and one more: 20', r.st.slides === 20 && !r.why);
r = P.addStories(nineteen, {slides: 3, bg: '#fff', blocks: [F(1, null, 0, 0, W, H)]}, {});
t('19 slides and a three-slide template: refused (max), and nothing changes', r.why === 'max' && r.st === nineteen, r.why);
r = P.addStories({slides: 20, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H)]}, {slides: 1, bg: '#fff', blocks: []}, {});
t('20 slides and a blank one: refused (max)', r.why === 'max');
JSON.stringify(out);
"""


def check_v22_page(case, work):
    sys.path.insert(0, str(SCRIPTS))
    import design
    import design_page
    src = _src()
    allsrc = "".join(src.values())
    page = design_page.page_html("2026-11-01 Fake beach")
    story = design_page.page_html("2026-11-01 Fake beach", "stories")
    # ---- the tables ----
    st = design.STARTERS
    case("v22: the starter templates are her eleven, in her order (her five first)", [(t["id"], t["name"]) for t in st] == [(h[0], h[1]) for h in HERS_STARTERS],
         [(t["id"], t["name"]) for t in st])
    by = {t["id"]: t for t in st}
    for sid, name, slides, bg, fr in HERS_STARTERS:
        t = by.get(sid)
        ok = bool(t) and t["template"]["slides"] == slides and t["template"]["bg"] == bg and frames_of(t["template"]) == hers(fr) \
            and not any(b.get("type") == "text" for b in t["template"]["blocks"]) and all(b["n"] is None for b in t["template"]["blocks"]) \
            and [b["slot"] for b in t["template"]["blocks"]] == list(range(1, len(fr) + 1))
        case(f"v22: starter \"{name}\": {slides} slides on {bg}, her {len(fr)} frames exactly, in her order, empty, no words", ok, t and (t["template"]["slides"], t["template"]["bg"], frames_of(t["template"])))
    sg = design.SINGLES
    case("v22: the single slides are her eight, in her order", [(t["id"], t["name"]) for t in sg] == [(h[0], h[1]) for h in HERS_SINGLES], [(t["id"], t["name"]) for t in sg])
    by1 = {t["id"]: t for t in sg}
    for sid, name, slides, bg, fr in HERS_SINGLES:
        t = by1.get(sid)
        ok = bool(t) and t["template"]["slides"] == 1 and t["template"]["bg"] == bg and frames_of(t["template"]) == hers(fr) \
            and not any(b.get("type") == "text" for b in t["template"]["blocks"]) and all(b["n"] is None for b in t["template"]["blocks"])
        case(f"v22: single slide \"{name}\": one slide on {bg}, her {len(fr)} frames exactly, empty, no words", ok, t and (t["template"]["bg"], frames_of(t["template"])))
    for sid, name in REMOVED:
        case(f"v22: \"{name}\" is no longer a starter template (hers)", sid not in by and name not in [t["name"] for t in st])
    case("v22: stories have no single slides of their own (their layouts are that), and their seven layouts are as they were",
         design.KINDS["stories"]["singles"] == [] and len(design.STORY_STARTERS) == 7 and design.KINDS["carousel"]["singles"] is sg)
    got = her_numbers()
    if got is None:
        print("SKIP  v22: her page is not beside the project, so this file's tables were not checked against it", flush=True)
    else:
        mine = {h[0]: (h[1], h[2], h[3], [tuple(int(v) for v in f) for f in h[4]] if all(float(v).is_integer() for f in h[4] for v in f) else None)
                for h in HERS_STARTERS + HERS_SINGLES}
        bad = [k for k, v in got.items() if mine.get(k) != v]
        case(f"v22: this file's tables are her page's own numbers ({len(got)} layouts she wrote in plain numbers)", len(got) >= 9 and not bad, bad)
        her = HER_PAGE.read_text(encoding="utf-8")
        ids = re.findall(r"\{ id: '((?:tp|st)-[a-z0-9-]+)'", her[her.index("const STARTERS"):her.index("// Story starters")])
        case("v22: the order of the starters is her page's own", ids == [h[0] for h in HERS_STARTERS], ids)
        ids1 = re.findall(r"\{ id: '(cs-[a-z0-9-]+)'", her)
        case("v22: the order of the single slides is her page's own", ids1 == [h[0] for h in HERS_SINGLES], ids1)
        for w in [ADD_TITLE, ADD_SUB, "Blank slide", "One empty slide", "Single slides", "+ Add slides", "Rename"] + LABELS:
            case(f"v22: her page says \"{w[:60]}\" and so do the page's scripts", w in her and w in allsrc, w)
    # ---- her words ----
    for w in [ADD_SUB, "addGalleryTitle: 'Add slides'", "addSlides: '+ Add slides'", "secSingles: 'Single slides'", "blankSlide: 'Blank slide'", "blankSlideSub: 'One empty slide'",
              "rename: 'Rename'", "add: 'Add'"] + ["'" + x + "'" for x in LABELS]:
        case(f"v22: page scripts: her words: {w[:70]}", w in allsrc, w)
    case("v22: the page's styles have the blue lines and the blue pill (2 px, #1f8fff)", ".guide.mid{background:#1f8fff" in page and ".guide.mid-v{width:2px" in page and ".guide.mid-h{height:2px" in page and ".midtag{" in page)
    case("v22: the stories page has the same styles (hers: the centers show there too)", ".midtag{" in story)
    case("v22: nothing new on the page comes from the internet", not re.search(r"https?://(?!fonts\.googleapis\.com|fonts\.gstatic\.com|127\.0\.0\.1|localhost|www\.w3\.org)", page), re.findall(r"https?://[^\s'\"<)]+", page)[:6])
    # ---- the rules by themselves ----
    js = work / "v22-rules.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar PLAN_SRC = " + json.dumps(src["DESIGN_PLAN_JS"]) + ";\nvar CAROUSEL_LIMITS = "
                  + json.dumps(design.limits_for("carousel")) + ";\nvar LABELS = " + json.dumps(LABELS) + ";\n" + RULES_JS, encoding="utf-8")
    r = osascript(js)
    try:
        got = json.loads(r.stdout.strip())
    except ValueError:
        got = None
    if case("v22: the rules ran to the end under osascript", isinstance(got, list) and len(got) >= 30, (r.stderr or r.stdout)[-600:]):
        for name, ok, detail in got:
            case("v22 rules: " + name, ok, detail)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _frame(i, n, x, y=0, w=W, h=H):
    return {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}


def check_v22_server(case, work, port, make_kit, Server, post, get_json, ask):
    target = work / "v22"
    ok, out = make_kit(target, "Add beach", 12)
    if not case("v22 server: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Add beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    tdir, sdir = studio / "design-templates", studio / "story-templates"
    srv = Server(env, port)
    P = srv.start()
    answers = []

    def rename(body, headers=None, raw=None):
        code, out = post(P, "/design-template", body, headers=headers, raw=raw)
        answers.append(out)
        return code, out
    try:
        code, S = get_json(P, f"/design-state?kit={KQ}")
        case("v22 server: the page is given her eleven starters in her order", code == 200 and [t["id"] for t in S["starters"]] == [h[0] for h in HERS_STARTERS], code)
        case("v22 server: ... and her eight single slides", [t["id"] for t in S.get("singles", [])] == [h[0] for h in HERS_SINGLES], S.get("singles") and [t["id"] for t in S["singles"]])
        case("v22 server: none of the five she removed is among them", not ({t["name"] for t in S["starters"] + S["singles"]} & {n for _, n in REMOVED if n not in ("Side by side",)} - set())
             and not ({t["id"] for t in S["starters"]} & {i for i, _ in REMOVED}))
        code, SS = get_json(P, f"/design-state?kit={KQ}&kind=stories")
        case("v22 server: stories are given no single slides, and their seven layouts as before", code == 200 and SS.get("singles") == [] and len(SS["starters"]) == 7, SS.get("singles"))
        # ---- a design made from a starter she removed ----
        code, out = post(P, "/design-new", {"kit": kit_name, "token": "v22filmstrip001", "stamp": S["stamp"], "state": FILM, "name": "From Film strip"})
        did = out and out.get("design", {}).get("id")
        case("v22 server: a design laid out as Film strip (no longer a starter) is made as any design is", code == 200 and bool(did), (code, out))
        dfile = kit / ".kit" / "designs" / f"{did}.json"
        on_disk = json.loads(dfile.read_text(encoding="utf-8")) if did else {}
        want = [(b["x"], b["y"], b["w"], b["h"]) for b in FILM["blocks"]]
        case("v22 server: ... it is on disk with Film strip's three frames on black", on_disk.get("state", {}).get("bg") == "#111111" and [(b["x"], b["y"], b["w"], b["h"]) for b in on_disk["state"]["blocks"]] == want, on_disk.get("state"))
        code, S2 = get_json(P, f"/design-state?kit={KQ}&design={did}")
        case("v22 server: ... it opens (the page is given that design, with its layout)", code == 200 and S2["design"]["id"] == did and S2["design"]["state"] == on_disk["state"] and not S2["fell_back"], code)
        moved = json.loads(json.dumps(on_disk["state"]))
        moved["blocks"][0]["n"] = 3
        code, out = post(P, "/design", {"kit": kit_name, "design": did, "page": "v22serverpage01", "base": on_disk["rev"], "stamp": S["stamp"], "state": moved, "name": "From Film strip"})
        again = json.loads(dfile.read_text(encoding="utf-8"))
        case("v22 server: ... and saves as before (a photo put in its first frame is kept, the version before is beside it)",
             code == 200 and out.get("ok") and again["state"]["blocks"][0]["n"] == 3 and again["rev"] == on_disk["rev"] + 1 and (kit / ".kit" / "designs" / f"{did}.prev.json").is_file(), (code, out))
        # ---- Rename ----
        state = {"slides": 2, "bg": "#f4efe6", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 90, 110, 900, 1130)]}
        code, out = post(P, "/design-template", {"kit": kit_name, "token": "v22template0001", "name": "My Test Template", "state": state})
        tid = out and out.get("template", {}).get("id")
        if not case("v22 server: a template of their own was saved for the rename checks", code == 200 and bool(tid), (code, out)):
            return
        code, out = post(P, "/design-template", {"kit": kit_name, "token": "v22template0002", "name": "Second one", "state": state})
        tid2 = out["template"]["id"]
        tfile = tdir / f"{tid}.json"
        first = tfile.read_bytes()
        was = json.loads(first)
        code, out = rename({"kit": kit_name, "rename": tid, "name": "  Beach   days\n"})
        now = json.loads(tfile.read_text(encoding="utf-8"))
        case("v22 server: Rename: the answer is ok and the list has the new name (tidied to one line)", code == 200 and out["ok"] and out["template"]["name"] == "Beach days"
             and {t["id"]: t["name"] for t in out["templates"]} == {tid: "Beach days", tid2: "Second one"}, (code, out))
        case("v22 server: Rename: the file has the new name, and the same id, layout, shoot and day as before",
             now["name"] == "Beach days" and all(now[k] == was[k] for k in ("id", "template", "from", "made", "made_by", "v")), now)
        prev = tdir / f"{tid}.prev.json"
        case("v22 server: Rename: the template as it was is kept beside it, byte for byte", prev.is_file() and prev.read_bytes() == first)
        code, S3 = get_json(P, f"/design-state?kit={KQ}")
        case("v22 server: Rename: the kept version is not shown as a template of its own", [t["id"] for t in S3["templates"]].count(tid) == 1 and len(S3["templates"]) == 2, [t["id"] for t in S3["templates"]])
        second = tfile.read_bytes()
        code, out = rename({"kit": kit_name, "rename": tid, "name": "Beach days"})
        case("v22 server: Rename to the name it has: ok, and nothing is written (the file and the kept version are as they were)",
             code == 200 and out["ok"] and tfile.read_bytes() == second and prev.read_bytes() == first, (code, out))
        code, out = rename({"kit": kit_name, "rename": tid, "name": "Sand"})
        case("v22 server: Rename again: the kept version is now the one before this rename", code == 200 and json.loads(prev.read_text(encoding="utf-8"))["name"] == "Beach days"
             and json.loads(tfile.read_text(encoding="utf-8"))["name"] == "Sand", (code, out))
        html = "<img src=x onerror=window.__pwn=1>\"'&"
        code, out = rename({"kit": kit_name, "rename": tid, "name": html})
        case("v22 server: a name that looks like page code is kept as the text it is", code == 200 and out["template"]["name"] == html and json.loads(tfile.read_text(encoding="utf-8"))["name"] == html, (code, out))
        code, out = rename({"kit": kit_name, "rename": tid, "name": "Zoë’s 海 🌊 walk"})
        case("v22 server: a name in any alphabet", code == 200 and out["template"]["name"] == "Zoë’s 海 🌊 walk", (code, out))
        good = tfile.read_bytes()
        files_before = sorted(p.name for p in tdir.iterdir())
        refusals = [
            ("no name", {"kit": kit_name, "rename": tid}, 400),
            ("an empty name", {"kit": kit_name, "rename": tid, "name": "   "}, 400),
            ("a name of 81 letters", {"kit": kit_name, "rename": tid, "name": "x" * 81}, 400),
            ("a name that is not text (a number)", {"kit": kit_name, "rename": tid, "name": 7}, 400),
            ("a name that is not text (a list)", {"kit": kit_name, "rename": tid, "name": ["a"]}, 400),
            ("a name of nothing but unseen marks", {"kit": kit_name, "rename": tid, "name": "‎‮\u0007"}, 400),
            ("an id that is not one of ours", {"kit": kit_name, "rename": "../" + tid, "name": "A"}, 400),
            ("an id with a file's ending", {"kit": kit_name, "rename": tid + ".json", "name": "A"}, 400),
            ("the kept version named as a template", {"kit": kit_name, "rename": tid + ".prev", "name": "A"}, 400),
            ("an id that is not text", {"kit": kit_name, "rename": {"id": tid}, "name": "A"}, 400),
            ("a template that is not there", {"kit": kit_name, "rename": "t" + "z" * 12, "name": "A"}, 404),
            ("a starter's id (not theirs to rename)", {"kit": kit_name, "rename": "tp-postcard", "name": "A"}, 400),
            ("a starter's id that looks like ours", {"kit": kit_name, "rename": "stborder", "name": "A"}, 404),
            ("a layout sent along (a rename never changes the layout)", {"kit": kit_name, "rename": tid, "name": "A", "state": state}, 400),
            ("a press's token sent along", {"kit": kit_name, "rename": tid, "name": "A", "token": "v22template0009"}, 400),
            ("a shoot that is not there", {"kit": "No such shoot", "rename": tid, "name": "A"}, 404),
            ("a kind that is not one", {"kit": kit_name, "kind": "reels", "rename": tid, "name": "A"}, 400),
            ("a carousel's template named as a story's", {"kit": kit_name, "kind": "stories", "rename": tid, "name": "A"}, 404),
        ]
        for what, body, want_code in refusals:
            code, out = rename(body)
            case(f"v22 server: Rename refused: {what} ({want_code}), with plain words, and the template is as it was",
                 code == want_code and out and out.get("ok") is False and isinstance(out.get("words"), str) and out["words"] and tfile.read_bytes() == good, (code, out))
        body = json.dumps({"kit": kit_name, "rename": tid, "name": "From elsewhere"}).encode()
        for what, headers, want_code in (("from another site", {"Origin": "http://evil.example"}, 403), ("sent as a form", {"Content-Type": "text/plain"}, 415),
                                         ("to another host's name", {"Host": "evil.example"}, 403)):
            code, out = post(P, "/design-template", None, headers=headers, raw=body)
            case(f"v22 server: Rename refused {what}, and the template is as it was", code in (want_code, 400, 403, 415) and code != 200 and tfile.read_bytes() == good, (code, out))
        big = json.dumps({"kit": kit_name, "rename": tid, "name": "A", "pad": "x" * 300000}).encode()
        code, out = post(P, "/design-template", None, raw=big)
        case("v22 server: Rename refused when the request is far too large", code != 200 and tfile.read_bytes() == good, code)
        case("v22 server: after every refusal the templates folder holds exactly what it held (nothing made, nothing removed)", sorted(p.name for p in tdir.iterdir()) == files_before, sorted(p.name for p in tdir.iterdir()))
        # a story's template
        code, out = post(P, "/design-template", {"kit": kit_name, "kind": "stories", "token": "v22storytpl0001", "name": "Story tpl",
                                                 "state": {"slides": 1, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, 0, W, 1920)]}})
        stid = out and out.get("template", {}).get("id")
        code2, out2 = rename({"kit": kit_name, "kind": "stories", "rename": stid, "name": "Story days"})
        case("v22 server: a story's template is renamed among the stories' own templates, with its version before kept there",
             code == 200 and code2 == 200 and out2["template"]["name"] == "Story days" and (sdir / f"{stid}.prev.json").is_file() and sorted(p.name for p in tdir.iterdir()) == files_before, (code2, out2))
        case("v22 server: no template was ever removed: both of theirs are still listed", {t["id"] for t in get_json(P, f"/design-state?kit={KQ}")[1]["templates"]} == {tid, tid2})
        seen = [s for a in answers for s in _strings(a)]
        case("v22 server: no answer to a rename held a path or a file's name", not any(str(target) in s or str(studio) in s or ".json" in s or "/private/" in s for s in seen))
    finally:
        srv.stop()


NO_FINDER_JS = r"""
(function(){
  var real = window.fetch;
  window.__opens = []; window.__posts = [];
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) { window.__opens.push(String(u)); return Promise.resolve(new Response('{"ok":true,"words":"Opened."}', {status: 200, headers: {'Content-Type': 'application/json'}})); }
    if (o && o.method === 'POST') window.__posts.push([String(u), typeof o.body === 'string' ? o.body.slice(0, 400) : '']);
    return real.apply(this, arguments);
  };
})();
"""


def check_v22_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  v22 on the real page: no Chrome on this computer", flush=True)
        return
    from PIL import Image, ImageChops, ImageStat
    target = work / "v22-browser"
    ok, out = make_kit(target, "Slide beach", 14)
    if not case("v22 browser: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Slide beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs, tdir, carousel = kit / ".kit" / "designs", studio / "design-templates", kit / "Carousel"
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    tokens = [0]
    try:
        stamp = get_json(P, f"/design-state?kit={KQ}")[1]["stamp"]

        def new_design(state, name):
            tokens[0] += 1
            code, out = post(P, "/design-new", {"kit": kit_name, "token": f"v22browser{tokens[0]:04d}", "stamp": stamp, "state": state, "name": name})
            if code != 200 or not out or not out.get("ok"):
                case(f"v22 browser: a design was made for this part ({name})", False, (code, out))
                raise RuntimeError("no design")
            return out["design"]["id"]

        tpl_state = {"slides": 7, "bg": "#f4efe6", "blocks": [_frame(1, 1, 0), _frame(2, 2, W, 0, 2 * W, H), _frame(3, 3, 3 * W + 90, 110, 900, 1130), _frame(4, 4, 4 * W),
                                                              _frame(5, 5, 5 * W), _frame(6, 6, 6 * W)]}
        code, out = post(P, "/design-template", {"kit": kit_name, "token": "v22browsertpl01", "name": "My Test Template", "state": tpl_state})
        tid = out["template"]["id"]
        tfile = tdir / f"{tid}.json"
        with cd.Chrome(work=work / "chrome-v22", size=(1400, 1000)) as c:
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

            def disk():
                return json.loads((designs / f"{did()}.json").read_text(encoding="utf-8"))

            def settled(seconds=12):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                return disk()["state"] == st()

            def open_design(i):
                c.open(f"{base}/design.html?kit={KQ}&design={i}")
                ready()
                settled()

            def is_open():
                return c.js("!document.getElementById('gallery').hidden")

            def open_window(btn="#add-slides"):
                c.click(btn)
                c.wait_for("!document.getElementById('gallery').hidden && document.querySelectorAll('#gallery-starters .dz-card').length === Designer.S.starters.length", 8)

            def close_window():
                if is_open():
                    c.click("#gallery-close")
                    c.wait_for("document.getElementById('gallery').hidden", 5)

            def window_words():
                return J("{h: document.querySelector('#gallery h2').textContent, label: document.querySelector('#gallery .dz-sheet').getAttribute('aria-label'), "
                         "sub: document.getElementById('gallery-sub').textContent, "
                         "secs: Array.from(document.querySelectorAll('#gallery .dz-sec')).map(function(x){ return x.textContent; }), "
                         "use: Array.from(new Set(Array.from(document.querySelectorAll('#gallery .dz-use')).map(function(x){ return x.textContent; }))), "
                         "fresh: Array.from(document.querySelectorAll('#gallery-fresh .dz-cap')).map(function(x){ return [x.querySelector('b').textContent, x.querySelector('small').textContent]; }), "
                         "singles: Array.from(document.querySelectorAll('#gallery-singles .dz-cap b')).map(function(x){ return x.textContent; }), "
                         "mine: Array.from(document.querySelectorAll('#gallery-mine .dz-cap b')).map(function(x){ return x.textContent; }), "
                         "starters: Array.from(document.querySelectorAll('#gallery-starters .dz-cap b')).map(function(x){ return x.textContent; })}")

            def tick(on):
                if c.js("document.getElementById('gallery-fill').checked") != on:
                    c.click("#gallery-fill")
                    c.wait_for("document.getElementById('gallery-fill').checked === %s" % ("true" if on else "false"), 3)

            def add(section, nth, wait_closed=True):
                c.click(f"#gallery-{section} .dz-card .dz-use", nth=nth)
                if wait_closed:
                    c.wait_for("document.getElementById('gallery').hidden", 5, tell="document.getElementById('gallery-line').textContent")

            def new_frames(before, after):
                """The frames after has that before had not, as (x - where the new slides start, y, w, h)."""
                off = before["slides"] * W
                return [(_r(b["x"] - off), _r(b["y"]), _r(b["w"]), _r(b["h"])) for b in after["blocks"][len(before["blocks"]):] if b.get("type") != "text"]

            def undo():
                c.click("#undo")

            # ================= the top bar =================
            start = {"slides": 3, "bg": "#f4efe6", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 100, 100, 400, 500), _frame(3, 3, 2 * W)]}
            d1 = new_design(start, "Adding")
            open_design(d1)
            bar = J("Array.from(document.getElementById('add-slides').parentNode.querySelectorAll('button')).map(function(b){ return [b.id, b.textContent]; })")
            case("v22 browser: \"+ Add slides\" is in the top bar, just before \"+ New design\" (hers)", bar[:2] == [["add-slides", "+ Add slides"], ["new-design", "+ New design"]], bar)
            # ================= the window in adding mode =================
            open_window()
            c.wait_for("Array.from(document.querySelectorAll('#gallery canvas')).length > 20", 5)
            ww = window_words()
            case("v22 browser: Add slides: the window is called \"Add slides\" (its heading and its name for a screen reader)", ww["h"] == ADD_TITLE and ww["label"] == ADD_TITLE, ww)
            case("v22 browser: Add slides: her line under it, word for word", ww["sub"] == ADD_SUB, ww["sub"])
            case("v22 browser: Add slides: her four sections in her order: Start fresh, Single slides, Your templates, Starter templates", ww["secs"] == SECTIONS, ww["secs"])
            case("v22 browser: Add slides: every card's button reads Add", ww["use"] == ["Add"], ww["use"])
            case("v22 browser: Add slides: Start fresh offers Blank slide (One empty slide) and One photo per slide (5 slides)",
                 ww["fresh"] == [["Blank slide", "One empty slide"], ["One photo per slide", "5 slides"]], ww["fresh"])
            case("v22 browser: Add slides: her eight single slides in her order", ww["singles"] == [h[1] for h in HERS_SINGLES], ww["singles"])
            case("v22 browser: Add slides: her five templates first, then the six she kept", ww["starters"] == [h[1] for h in HERS_STARTERS], ww["starters"])
            case("v22 browser: Add slides: none of the five she removed is in the window", not (set(ww["starters"] + ww["singles"]) & {"Film strip", "Big and small", "Title slide", "Four-photo grid"})
                 and "Side by side" not in ww["starters"], ww["starters"])
            case("v22 browser: Add slides: their own template is under Your templates", ww["mine"] == ["My Test Template"], ww["mine"])
            ones = J("Array.from(document.querySelectorAll('#gallery-singles .dz-card')).map(function(x){ var r = x.getBoundingClientRect(), p = x.querySelector('canvas').getBoundingClientRect(), "
                     "n = x.querySelector('b').getBoundingClientRect(), u = x.querySelector('.dz-use').getBoundingClientRect(); return {w: r.width, cw: p.width, ch: p.height, order: p.bottom <= n.top + 1 && n.bottom <= u.top + 1, "
                     "uw: u.width, small: getComputedStyle(x.querySelector('small')).display}; })")
            case("v22 browser: single slides are small cards: the slide (96 by 120), its name under it, Add underneath, no second line",
                 len(ones) == 8 and all(o["w"] < 200 and abs(o["cw"] - 96) <= 1 and abs(o["ch"] - 120) <= 1 and o["order"] and o["small"] == "none" and o["uw"] > o["w"] * 0.7 for o in ones), ones)
            big = J("(function(){ var x = document.querySelectorAll('#gallery-starters .dz-card')[0], r = x.getBoundingClientRect(); return {w: r.width}; })()")
            case("v22 browser: a template's card is much wider than a single slide's (hers: small cards beside the wide ones)", big["w"] > 2 * max(o["w"] for o in ones), (big, ones[0]))
            fits = J("Array.from(document.querySelectorAll('#gallery-starters .dz-card')).map(function(x){ var p = x.querySelector('.dz-pic'), cv = x.querySelector('canvas'); "
                     "return {pic: p.clientWidth, cw: cv.getBoundingClientRect().width, ch: cv.getBoundingClientRect().height, slides: 0}; })")
            long_ones = [0, 2, 3, 4, 5]             # 9, 5, 5, 5 and 7 slides: wider than their card at full height
            case("v22 browser: a long template's picture fills its card to the edge (no gap at its side)", all(abs(fits[i]["cw"] - fits[i]["pic"]) <= 1 and fits[i]["pic"] > 256 for i in long_ones), [fits[i] for i in long_ones])
            case("v22 browser: a short template's picture keeps its full height (96 px) and is not stretched", abs(fits[1]["ch"] - 96) <= 1 and abs(fits[10]["ch"] - 96) <= 1 and fits[1]["cw"] < fits[1]["pic"], (fits[1], fits[10]))
            paint_js = ("(function(){ var cv = document.querySelectorAll('#gallery-starters canvas')[0], d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, seen = {}; "
                           "for (var i = 0; i < d.length; i += 4 * 97) seen[d[i] + ',' + d[i + 1] + ',' + d[i + 2]] = 1; return Object.keys(seen).length; })()")
            try:
                c.wait_for(paint_js + " > 6", 8)
            except cd.Timeout:
                pass
            painted = c.js(paint_js)
            case("v22 browser: ... and it is drawn across that whole width (this shoot's photos are in it)", painted > 6, painted)
            # ================= adding never replaces =================
            before = st()
            before_disk = disk()
            tick(False)
            add("singles", 3)                       # Four
            after = st()
            case("v22 browser: Add (Four, the tick off): one more slide, after the last", after["slides"] == before["slides"] + 1 and after["bg"] == before["bg"], (before["slides"], after["slides"]))
            case("v22 browser: ... the slides that were there are exactly as they were", after["blocks"][:len(before["blocks"])] == before["blocks"])
            case("v22 browser: ... the four new frames are hers, on the new slide, and empty", new_frames(before, after) == hers(HERS_SINGLES[3][4]) and all(b["n"] is None for b in after["blocks"][3:]), new_frames(before, after))
            case("v22 browser: ... the page shows the new slide (the strip was brought to it)", c.js("(function(){ var s = document.getElementById('stage'); return s.scrollLeft > 0 || s.scrollWidth <= s.clientWidth; })()"))
            case("v22 browser: ... and it saved itself", settled(), c.text("#d-status"))
            d = disk()
            case("v22 browser: in the saved design the earlier slides' frames are byte for byte what they were",
                 json.dumps(d["state"]["blocks"][:3], sort_keys=True) == json.dumps(before_disk["state"]["blocks"], sort_keys=True) and d["state"]["slides"] == 4 and len(d["state"]["blocks"]) == 7, d["state"])
            case("v22 browser: ... and the version before is kept beside it, as with every save", (designs / f"{did()}.prev.json").is_file())
            case("v22 browser: Add never asked the Assistant for a new design (the same design is open, and it is the only one beside the shoot's first)", did() == d1 and len([p for p in designs.glob("*.json") if not p.name.endswith(".prev.json")]) == 2,
                 sorted(p.name for p in designs.glob("*.json")))
            undo()
            case("v22 browser: one Undo takes the whole addition back", st() == before, st()["slides"])
            # each single slide, each of her five templates, and the six she kept: Add puts her frames after the last slide
            for sec, table in (("singles", HERS_SINGLES), ("starters", HERS_STARTERS)):
                for i, (sid, name, slides, bg, fr) in enumerate(table):
                    b0 = st()
                    open_window()
                    tick(False)
                    add(sec, i)
                    a = st()
                    case(f"v22 browser: Add \"{name}\": {slides} more slide{'s' if slides != 1 else ''} after the last, her {len(fr)} frames exactly, what was there untouched",
                         a["slides"] == b0["slides"] + slides and a["blocks"][:len(b0["blocks"])] == b0["blocks"] and new_frames(b0, a) == hers(fr) and a["bg"] == b0["bg"], (a["slides"], new_frames(b0, a)))
                    undo()
                    if st() != b0:
                        case(f"v22 browser: Undo after \"{name}\"", False, st()["slides"])
            # the tick on: the new frames take photos not used yet; nothing there is refilled
            b0 = st()
            open_window()
            tick(True)
            add("singles", 1)                       # Two stacked
            a = st()
            used_before = {b["n"] for b in b0["blocks"] if b.get("n") is not None}
            got = [b["n"] for b in a["blocks"][len(b0["blocks"]):]]
            case("v22 browser: Add with the tick on: the new frames take photos that were not on a slide yet, and the earlier slides keep theirs",
                 len(got) == 2 and all(n is not None and n not in used_before for n in got) and len(set(got)) == 2 and a["blocks"][:3] == b0["blocks"], got)
            undo()
            # Start fresh, adding
            open_window()
            add("fresh", 0)
            a = st()
            case("v22 browser: Add \"Blank slide\": one empty slide after the last, in the design's own background, nothing else", a["slides"] == 4 and a["blocks"] == b0["blocks"] and a["bg"] == "#f4efe6", a["slides"])
            undo()
            open_window()
            add("fresh", 1)
            a = st()
            news = a["blocks"][3:]
            case("v22 browser: Add \"One photo per slide\": five slides after the last, each filled by one photo not used yet",
                 a["slides"] == 8 and len(news) == 5 and [(_r(b["x"]), b["y"], b["w"], b["h"]) for b in news] == [(_r((3 + i) * W), 0, W, H) for i in range(5)]
                 and [b["n"] for b in news] == [n for n in range(1, 15) if n not in used_before][:5] and a["blocks"][:3] == b0["blocks"], [(b["n"], b["x"]) for b in news])
            undo()
            # one of their own templates, added
            open_window()
            tick(False)
            add("mine", 0)
            a = st()
            case("v22 browser: Add one of their own templates: its 7 slides after the last, what was there untouched", a["slides"] == 10 and a["blocks"][:3] == b0["blocks"] and len(a["blocks"]) == 9, a["slides"])
            undo()
            case("v22 browser: after all of that and its Undos the design is exactly what it was", st() == before and settled(), st()["slides"])
            # ================= 20 slides =================
            d19 = new_design({"slides": 19, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, 18 * W)]}, "Nineteen")
            open_design(d19)
            b0 = st()
            open_window()
            add("starters", 1, wait_closed=False)   # Layered trio: 3 slides
            time.sleep(0.3)
            case("v22 browser: 19 slides and a 3-slide template: refused with \"Instagram allows up to 20 slides.\", the window stays, nothing changed",
                 is_open() and c.text("#gallery-line") == MAX_WORDS and st() == b0, (is_open(), c.text("#gallery-line")))
            add("singles", 0)
            case("v22 browser: 19 slides and one single slide: 20", st()["slides"] == 20 and st()["blocks"][:2] == b0["blocks"], st()["slides"])
            open_window()
            add("fresh", 0, wait_closed=False)
            time.sleep(0.3)
            case("v22 browser: 20 slides and a blank one: refused, 20 slides still", is_open() and c.text("#gallery-line") == MAX_WORDS and st()["slides"] == 20, c.text("#gallery-line"))
            close_window()
            settled()
            case("v22 browser: the 20-slide design is saved as 20 slides", disk()["state"]["slides"] == 20)
            # ================= + New design is as before; an empty design =================
            open_design(d1)
            open_window("#new-design")
            ww = window_words()
            case("v22 browser: + New design: the window is \"New design\", every button reads Use, and Start fresh is Blank and One photo per slide",
                 ww["h"] == "New design" and ww["use"] == ["Use"] and [f[0] for f in ww["fresh"]] == ["Blank", "One photo per slide"] and ww["sub"].startswith("Pick a starting point for Slide beach."), ww)
            case("v22 browser: + New design: the same four sections, single slides among them", ww["secs"] == SECTIONS and len(ww["singles"]) == 8, ww["secs"])
            n_before = len([p for p in designs.glob("*.json") if not p.name.endswith(".prev.json")])
            c.click("#gallery-singles .dz-card .dz-use", nth=2)        # Three across, as a new design
            c.wait_for("document.getElementById('gallery').hidden && Designer.design.id !== %s && Designer.save.idle()" % json.dumps(d1), 20, tell="document.getElementById('gallery-line').textContent")
            a = st()
            case("v22 browser: + New design with a single slide: a NEW one-slide design on her background, and the design that was open is as it was",
                 a["slides"] == 1 and a["bg"] == "#ebe9e5" and len(a["blocks"]) == 3 and len([p for p in designs.glob("*.json") if not p.name.endswith(".prev.json")]) == n_before + 1
                 and json.loads((designs / f"{d1}.json").read_text(encoding="utf-8"))["state"] == before, (a["slides"], a["bg"]))
            dempty = new_design({"slides": 5, "bg": "#ffffff", "blocks": []}, "Empty one")
            open_design(dempty)
            open_window("#add-slides")
            ww = window_words()
            case("v22 browser: + Add slides on a design with nothing on it behaves like + New design (hers)", ww["h"] == "New design" and ww["use"] == ["Use"] and ww["fresh"][0][0] == "Blank", ww)
            close_window()
            # ================= Rename =================
            open_design(d1)
            open_window()
            rn = J("(function(){ var c = document.querySelector('#gallery-mine .dz-card'), l = c.querySelector('.dz-rn'), b = c.querySelector('b'); "
                   "return {text: l && l.textContent, after: l && l.previousElementSibling === b, others: document.querySelectorAll('#gallery-starters .dz-rn, #gallery-singles .dz-rn, #gallery-fresh .dz-rn').length}; })()")
            case("v22 browser: Rename: a \"Rename\" link sits right after the name of their own template, and on no other card", rn == {"text": "Rename", "after": True, "others": 0}, rn)
            first = tfile.read_bytes()
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            box = J("(function(){ var i = document.querySelector('#gallery-mine .dz-rnin'); return {v: i.value, sel: i.selectionEnd - i.selectionStart, b: !!document.querySelector('#gallery-mine .dz-card b'), link: !!document.querySelector('#gallery-mine .dz-rn')}; })()")
            case("v22 browser: Rename: the name becomes a text box holding the name, selected", box == {"v": "My Test Template", "sel": len("My Test Template"), "b": False, "link": False}, box)
            c.js("window.__posts = []")
            c.type_text("Thrown away")
            c.key("Escape")
            time.sleep(0.4)
            case("v22 browser: Rename: Escape cancels: the window is still open, the name is as it was, and nothing was sent or written",
                 is_open() and c.text("#gallery-mine .dz-card b") == "My Test Template" and c.count("#gallery-mine .dz-rnin") == 0 and c.count("#gallery-mine .dz-rn") == 1
                 and not [p for p in J("window.__posts") if "rename" in p[1]] and tfile.read_bytes() == first, (is_open(), J("window.__posts")))
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            c.type_text("Beach days")
            c.key("Enter")
            c.wait_for("document.querySelector('#gallery-mine .dz-card b') && document.querySelector('#gallery-mine .dz-card b').textContent === 'Beach days'", 8, tell="document.getElementById('gallery-line').textContent")
            now = json.loads(tfile.read_text(encoding="utf-8"))
            case("v22 browser: Rename: Return saves: the card and the file have the new name, the layout is the same, the window is still open",
                 is_open() and now["name"] == "Beach days" and now["template"] == json.loads(first)["template"] and c.count("#gallery-mine .dz-rn") == 1, now["name"])
            case("v22 browser: Rename: the Assistant kept the version before", (tdir / f"{tid}.prev.json").read_bytes() == first)
            sent = [p for p in J("window.__posts") if "rename" in p[1]]
            case("v22 browser: Rename: what was sent is the template's id and the new name, never its layout", len(sent) == 1 and sent[0][0] == "/design-template"
                 and set(json.loads(sent[0][1])) == {"kit", "rename", "name"}, sent)
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            c.type_text("Clicked away")
            c.click("#gallery h2")
            c.wait_for("document.querySelector('#gallery-mine .dz-card b') && document.querySelector('#gallery-mine .dz-card b').textContent === 'Clicked away'", 8)
            case("v22 browser: Rename: a press anywhere else saves too", json.loads(tfile.read_text(encoding="utf-8"))["name"] == "Clicked away")
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            c.js("window.__posts = []")
            c.key("Enter")
            time.sleep(0.4)
            case("v22 browser: Rename: Return with the name unchanged sends nothing and puts the name back", not J("window.__posts") and c.text("#gallery-mine .dz-card b") == "Clicked away" and c.count("#gallery-mine .dz-rn") == 1)
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            c.key("Mod+a")
            c.key("Backspace")
            c.type_text("   ")
            c.key("Enter")
            time.sleep(0.4)
            case("v22 browser: Rename: an empty name changes nothing", c.text("#gallery-mine .dz-card b") == "Clicked away" and json.loads(tfile.read_text(encoding="utf-8"))["name"] == "Clicked away")
            html = "<img src=x onerror=window.__pwn=1><b>bold</b>"
            c.click("#gallery-mine .dz-rn")
            c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
            c.set_value("#gallery-mine .dz-rnin", html)
            c.key("Enter")
            c.wait_for("document.querySelector('#gallery-mine .dz-card b') && document.querySelector('#gallery-mine .dz-card b').textContent.indexOf('<img') === 0", 8)
            time.sleep(0.3)
            inj = J("{text: document.querySelector('#gallery-mine .dz-card b').textContent, imgs: document.querySelectorAll('#gallery img').length, kids: document.querySelector('#gallery-mine .dz-card b').children.length, "
                    "pwn: typeof window.__pwn, label: document.querySelector('#gallery-mine .dz-use').getAttribute('aria-label')}")
            case("v22 browser: a name that looks like page code is shown as the text it is: nothing in it runs, no picture or bold is made from it",
                 inj["text"] == html and inj["imgs"] == 0 and inj["kids"] == 0 and inj["pwn"] == "undefined" and inj["label"] == "Add: " + html, inj)
            close_window()
            c.reload()
            ready()
            open_window("#new-design")
            inj = J("{text: document.querySelector('#gallery-mine .dz-card b').textContent, imgs: document.querySelectorAll('#gallery img').length, pwn: typeof window.__pwn}")
            case("v22 browser: ... and after a reload too", inj == {"text": html, "imgs": 0, "pwn": "undefined"}, inj)
            close_window()
            # the server says no: the name stays, with the words
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            tfile_gone = tfile.with_name(tfile.name + ".away")
            tfile.rename(tfile_gone)                # the template is not there any more (a pretend: the test's own doing)
            try:
                c.click("#gallery-mine .dz-rn")
                c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
                c.type_text("Never lands")
                c.key("Enter")
                c.wait_for("document.getElementById('gallery-line').textContent !== ''", 8)
                case("v22 browser: Rename that the Assistant refuses: its words are shown in the window, and no name on the page changed to the refused one",
                     "can't find that template" in c.text("#gallery-line") and "Never lands" not in c.js("document.getElementById('gallery').innerText"), c.text("#gallery-line"))
            finally:
                tfile_gone.rename(tfile)
            close_window()
            # ================= the window holds still: a held press, where it is scrolled to, the line in sight =================
            # (a smaller window, so the Add slides window scrolls; a hand's press holds the button about 150 ms)
            c.desktop((1280, 700))
            code, out = post(P, "/design-template", {"kit": kit_name, "token": "v22browsertpl02", "name": "Second one", "state": tpl_state})
            tid2 = out["template"]["id"] if code == 200 and out and out.get("ok") else ""
            case("v22 browser: a second template of their own was saved for the held-press checks", bool(tid2), (code, out))
            for t_, n_ in ((tid, "First one"), (tid2, "Second one")):
                post(P, "/design-template", {"kit": kit_name, "rename": t_, "name": n_})

            def card_of(name):
                """Which card under Your templates has this name (the list's order is the Assistant's own)."""
                return J("Array.from(document.querySelectorAll('#gallery-mine .dz-card')).map(function(x){ var b = x.querySelector('b'); return b ? b.textContent : null; })").index(name)

            def file_name(t_):
                return json.loads((tdir / f"{t_}.json").read_text(encoding="utf-8"))["name"]

            def held_press(sel, nth, until, hold=0.15):
                """A press the way a hand makes it: down, the button held, then up at the same spot."""
                x, y = c.point(sel, nth=nth)
                c.mouse_move(x, y)
                c.mouse_press()
                time.sleep(hold)
                end = time.time() + 8
                while time.time() < end and not until():
                    time.sleep(0.03)
                time.sleep(0.1)
                c.mouse_release()

            def start_rename(i, typed):
                c.click("#gallery-mine .dz-card .dz-rn", nth=i)
                c.wait_for("document.activeElement && document.activeElement.classList.contains('dz-rnin')", 3)
                c.type_text(typed)

            def sheet_at():
                return J("(function(){ var s = document.querySelector('#gallery .dz-sheet'), r = s.getBoundingClientRect(); return {top: s.scrollTop, room: s.scrollHeight - s.clientHeight, y0: r.top, y1: r.bottom}; })()")

            open_design(d1)
            b0 = st()
            open_window()
            tick(False)
            i1 = card_of("First one")
            start_rename(i1, "Held one")
            held_press("#gallery-singles .dz-card .dz-use", 0, lambda: file_name(tid) == "Held one")
            try:
                c.wait_for("document.getElementById('gallery').hidden", 5)
            except cd.Timeout:
                pass
            case("v22 browser: a name being typed, then an ordinary press (held 150 ms) on another card's Add: the name is saved AND the slide is added, the window closes",
                 file_name(tid) == "Held one" and not is_open() and st()["slides"] == b0["slides"] + 1 and st()["blocks"][:len(b0["blocks"])] == b0["blocks"], (file_name(tid), is_open(), st()["slides"]))
            close_window()
            undo()
            open_window()
            case("v22 browser: ... and the window, opened again, has the new name", "Held one" in window_words()["mine"], window_words()["mine"])
            i1, i2 = card_of("Held one"), card_of("Second one")
            start_rename(i1, "First again")
            held_press("#gallery-mine .dz-card .dz-rn", 0, lambda: file_name(tid) == "First again")        # the one Rename link left: the second card's
            time.sleep(0.3)
            two = J("(function(){ var cs = Array.from(document.querySelectorAll('#gallery-mine .dz-card')); return cs.map(function(x){ var b = x.querySelector('b'), i = x.querySelector('.dz-rnin'); "
                    "return {b: b ? b.textContent : null, box: i ? i.value : null, rn: x.querySelectorAll('.dz-rn').length, label: x.querySelector('.dz-use').getAttribute('aria-label')}; }); })()")
            case("v22 browser: a name being typed, then a held press on another template's Rename: the first is renamed in its card, and the second's box opens",
                 file_name(tid) == "First again" and two[i1] == {"b": "First again", "box": None, "rn": 1, "label": "Add: First again"} and two[i2]["box"] == "Second one" and two[i2]["b"] is None
                 and c.js("document.activeElement && document.activeElement.classList.contains('dz-rnin')"), two)
            if c.count("#gallery-mine .dz-rnin"):
                c.key("Escape")
                time.sleep(0.2)
            if not is_open():
                open_window()
            # where the window is scrolled to, and the keyboard, after a rename
            i2 = card_of("Second one")
            c.js("(function(){ var s = document.querySelector('#gallery .dz-sheet'), x = document.querySelectorAll('#gallery-mine .dz-card')[%d]; s.scrollTop = 0; "
                 "s.scrollTop = Math.min(s.scrollHeight - s.clientHeight, x.getBoundingClientRect().top - s.getBoundingClientRect().top - 60); })()" % i2)
            at0 = sheet_at()
            case("v22 browser: (the window scrolls at this size, and Your templates is brought into view by scrolling)", at0["room"] > 200 and at0["top"] > 100, at0)
            start_rename(i2, "Kept in sight")
            at_typing = sheet_at()
            c.key("Enter")
            try:
                c.wait_for("Array.from(document.querySelectorAll('#gallery-mine .dz-card b')).some(function(b){ return b.textContent === 'Kept in sight'; })", 8)
            except cd.Timeout:
                pass
            time.sleep(0.3)
            at1 = sheet_at()
            seen = J("(function(){ var x = Array.from(document.querySelectorAll('#gallery-mine .dz-card')).filter(function(x){ var b = x.querySelector('b'); return b && b.textContent === 'Kept in sight'; })[0]; "
                     "if (!x) return null; var r = x.querySelector('b').getBoundingClientRect(), a = document.activeElement; return {y0: r.top, y1: r.bottom, on: !!a && a === x.querySelector('.dz-rn'), tag: a ? a.tagName : ''}; })()")
            case("v22 browser: Rename saved with Return: the window stays where it was scrolled to", file_name(tid2) == "Kept in sight" and abs(at1["top"] - at_typing["top"]) <= 2 and at1["top"] > 100, (at_typing, at1))
            case("v22 browser: ... the name just changed is in sight, in its own card", bool(seen) and seen["y0"] >= at1["y0"] and seen["y1"] <= at1["y1"], (seen, at1))
            case("v22 browser: ... and the keyboard is back on that card's Rename link (not lost to the page)", bool(seen) and seen["on"], seen)
            close_window()
            # the 20-slide line, with the window scrolled far down
            d19b = new_design({"slides": 19, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, 18 * W)]}, "Nineteen again")
            open_design(d19b)
            b0 = st()
            open_window()
            c.js("(function(){ var s = document.querySelector('#gallery .dz-sheet'); s.scrollTop = s.scrollHeight; })()")
            last = c.count("#gallery-starters .dz-card") - 1       # One wide across three: 3 slides, the last card in the window
            add("starters", last, wait_closed=False)
            time.sleep(0.3)
            line = J("(function(){ var l = document.getElementById('gallery-line'), r = l.getBoundingClientRect(), s = document.querySelector('#gallery .dz-sheet'), q = s.getBoundingClientRect(), "
                     "t = document.elementFromPoint(r.left + Math.min(40, r.width / 2), r.top + r.height / 2); return {text: l.textContent, y0: r.top, y1: r.bottom, s0: q.top, s1: q.bottom, top: s.scrollTop, hit: t === l}; })()")
            case("v22 browser: 19 slides, the window scrolled to its last card, Add on a 3-slide template: nothing is added and the window stays",
                 is_open() and st() == b0 and line["top"] > 200, (is_open(), line))
            case("v22 browser: ... and \"Instagram allows up to 20 slides.\" is IN SIGHT in the window, on top of what scrolls under it",
                 line["text"] == MAX_WORDS and line["y0"] >= line["s0"] and line["y1"] <= line["s1"] and line["hit"], line)
            close_window()
            c.desktop()
            case("v22 browser: nothing went wrong on the page so far", not c.page_errors(), c.page_errors())
            # ================= centered =================
            dc = new_design({"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, 1, 100, 100, 400, 500), _frame(2, 2, 2 * W + 200, 60, 600, 500)]}, "Centering")
            open_design(dc)
            s = c.js("Designer.scale")

            def blk(i):
                return next(b for b in st()["blocks"] if b["id"] == i)

            def drag_to(i, x, y, off=(4, 3), release=True, **mods):
                """Drag block i so that, with no snapping, its corner would land `off` screen pixels from strip (x, y)."""
                b = blk(i)
                r = c.rect(f".blk[data-id='{i}']")
                p0 = (r["x"] + min(40, r["w"] / 2), r["y"] + min(40, r["h"] / 2))
                p1 = (p0[0] + (x - b["x"]) * s + off[0], p0[1] + (y - b["y"]) * s + off[1])
                c.drag(p0, p1, steps=10, release=release, check=False, **mods)

            def guides():
                return J("(function(){ var sr = document.getElementById('strip').getBoundingClientRect(), q = function(sel){ return Array.from(document.querySelectorAll(sel)).map(function(e){ var r = e.getBoundingClientRect(), cs = getComputedStyle(e); "
                         "return {x: r.left - sr.left, y: r.top - sr.top, w: r.width, h: r.height, bg: cs.backgroundColor, text: e.textContent}; }); }; "
                         "return {v: q('.guide.mid-v'), h: q('.guide.mid-h'), tag: q('.midtag'), pink: q('.guide:not(.mid)')}; })()")

            def near(a, b, tol=1.2):
                return abs(a - b) <= tol

            BLUE = "rgb(31, 143, 255)"
            case("v22 browser: Snap is on to start with", c.js("document.getElementById('snap').checked") is True)
            # the middle of a slide, both ways: a hand a few pixels off still lands on it
            drag_to(1, 340, 425, off=(6, -5), release=False)
            g = guides()
            case("v22 browser: dragging near the middle of a slide: a blue upright line 2 px wide through the slide's middle", len(g["v"]) == 1 and near(g["v"][0]["x"] + 1, 540 * s) and near(g["v"][0]["w"], 2, 0.1) and g["v"][0]["bg"] == BLUE, g["v"])
            case("v22 browser: ... and a blue level line 2 px high, half way up, over that one slide only", len(g["h"]) == 1 and near(g["h"][0]["y"] + 1, 675 * s) and near(g["h"][0]["h"], 2, 0.1)
                 and near(g["h"][0]["x"], 0) and near(g["h"][0]["w"], W * s) and g["h"][0]["bg"] == BLUE, g["h"])
            case("v22 browser: ... and the blue pill at the photo's middle says \"Centered\"", len(g["tag"]) == 1 and g["tag"][0]["text"] == "Centered" and g["tag"][0]["bg"] == BLUE
                 and near(g["tag"][0]["x"] + g["tag"][0]["w"] / 2, 540 * s, 1.5) and near(g["tag"][0]["y"] + g["tag"][0]["h"] / 2, 675 * s, 1.5), g["tag"])
            case("v22 browser: ... and no pink edge line on either axis (the edges only snap where the middle did not)", g["pink"] == [], g["pink"])
            c.mouse_release()
            b = blk(1)
            case("v22 browser: let go: the photo sits exactly in the middle of the slide (340, 425), and the lines are gone", (b["x"], b["y"]) == (340, 425) and c.count(".guide") == 0 and c.count(".midtag") == 0, (b["x"], b["y"]))
            # side to side only
            drag_to(1, 340, 150, off=(-7, 2), release=False)
            g = guides()
            case("v22 browser: only side to side: \"Centered side to side\", an upright line and no level one", len(g["v"]) == 1 and g["h"] == [] and [t["text"] for t in g["tag"]] == ["Centered side to side"], g)
            c.mouse_release()
            case("v22 browser: ... the photo's middle is on the slide's middle", blk(1)["x"] == 340, blk(1))
            # up and down only, on the second slide's left part
            drag_to(1, 1200, 425, off=(2, 8), release=False)
            g = guides()
            case("v22 browser: only up and down: \"Centered up and down\", a level line over the second slide only", g["v"] == [] and len(g["h"]) == 1 and near(g["h"][0]["x"], W * s) and near(g["h"][0]["w"], W * s)
                 and [t["text"] for t in g["tag"]] == ["Centered up and down"], g)
            c.mouse_release()
            case("v22 browser: ... the photo's middle is half way up", blk(1)["y"] == 425, blk(1))
            # a seam it sits across
            drag_to(1, 880, 150, off=(-6, 2), release=False)
            g = guides()
            case("v22 browser: across a seam: \"Centered on the seam\", the upright line on the seam", len(g["v"]) == 1 and near(g["v"][0]["x"] + 1, 1080 * s) and [t["text"] for t in g["tag"]] == ["Centered on the seam"], g)
            c.mouse_release()
            case("v22 browser: ... the photo's middle is on the seam (880)", blk(1)["x"] == 880, blk(1))
            drag_to(1, 880, 425, off=(5, 6), release=False)
            g = guides()
            case("v22 browser: across a seam and half way up: \"Centered on the seam, and up and down\", the level line over both slides it is on",
                 [t["text"] for t in g["tag"]] == ["Centered on the seam, and up and down"] and len(g["h"]) == 1 and near(g["h"][0]["x"], 0) and near(g["h"][0]["w"], 2 * W * s), g)
            c.mouse_release()
            case("v22 browser: ... at 880, 425", (blk(1)["x"], blk(1)["y"]) == (880, 425), blk(1))
            # Alt held: nothing centers
            drag_to(1, 340, 425, off=(6, -5), release=False, alt=True)
            g = guides()
            c.mouse_release(alt=True)
            b = blk(1)
            case("v22 browser: with Alt (Option) held nothing centers: no blue line, no pill, and the photo is where the hand left it (off the middle)",
                 g["v"] == [] and g["h"] == [] and g["tag"] == [] and g["pink"] == [] and (b["x"], b["y"]) != (340, 425) and abs(b["x"] - 340) < 14 / s + 1 and abs(b["y"] - 425) < 14 / s + 1, (g, b["x"], b["y"]))
            # Snap off
            c.click("#snap")
            drag_to(1, 340, 425, off=(6, -5), release=False)
            g = guides()
            c.mouse_release()
            b = blk(1)
            case("v22 browser: with Snap off nothing centers either", c.js("document.getElementById('snap').checked") is False and g["v"] == [] and g["h"] == [] and g["tag"] == [] and (b["x"], b["y"]) != (340, 425), (g, b["x"], b["y"]))
            c.click("#snap")
            # out of reach
            drag_to(1, 340 + 40 / s, 150, off=(0, 0), release=False)
            g = guides()
            c.mouse_release()
            case("v22 browser: 40 screen pixels from the middle is out of reach: no blue line", g["v"] == [] and g["tag"] == [], g)
            settled()
            # the flash after an arrow key (a nudge is 5 px)
            open_design(new_design({"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, 1, 335, 100, 400, 500), _frame(2, 2, 2 * W + 200, 60, 600, 500)]}, "Nudging"))
            c.click(".blk[data-id='1']")
            c.wait_for("Designer.sel === 1", 3)
            case("v22 browser: selecting a photo shows no centered line by itself", c.count(".midtag") == 0 and c.count(".guide") == 0)
            t0 = time.time()
            c.key("ArrowRight")
            g = guides()
            case("v22 browser: an arrow key that lands the photo on the middle: the blue line and \"Centered side to side\" show", blk(1)["x"] == 340 and len(g["v"]) == 1 and near(g["v"][0]["x"] + 1, 540 * s)
                 and [t["text"] for t in g["tag"]] == ["Centered side to side"], (blk(1)["x"], g))
            time.sleep(max(0, 0.7 - (time.time() - t0)))
            case("v22 browser: ... still showing 0.7 s later", c.count(".midtag") == 1)
            try:
                c.wait_for("document.querySelectorAll('.midtag, .guide').length === 0", 3)
                gone = time.time() - t0
            except cd.Timeout:
                gone = None
            case("v22 browser: ... and gone after about 1.4 s", gone is not None and 1.0 <= gone <= 2.6, gone)
            c.key("ArrowRight")
            case("v22 browser: an arrow key that leaves it off the middle shows nothing", blk(1)["x"] == 345 and c.count(".midtag") == 0 and c.count(".guide") == 0, blk(1)["x"])
            c.key("ArrowLeft")
            case("v22 browser: back onto the middle: the flash again", c.count(".midtag") == 1 and c.text(".midtag") == "Centered side to side")
            c.key("ArrowDown", times=65)            # 100 -> 425: half way up
            g = guides()
            case("v22 browser: arrow keys down to half way up: \"Centered\" (both ways now)", blk(1)["y"] == 425 and [t["text"] for t in g["tag"]] == ["Centered"] and len(g["h"]) == 1 and len(g["v"]) == 1, (blk(1)["y"], g["tag"]))
            c.key("Escape")
            case("v22 browser: nothing selected any more: the lines go with it", c.count(".midtag") == 0 and c.count(".guide") == 0)
            settled()
            case("v22 browser: nothing went wrong on the page during the centering", not c.page_errors(), c.page_errors())
            # ================= Save slides, on a design nothing here touched =================
            dsave = new_design({"slides": 3, "bg": "#f4efe6", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 90, 110, 900, 1130), _frame(3, 3, 2 * W)]}, "Untouched")
            open_design(dsave)
            c.js("window.scrollTo(0, 0)")
            sr = c.rect("#strip")
            s = c.js("Designer.scale")
            shot = Image.open(c.screenshot("v22-screen.png")).convert("RGB")
            k = shot.size[0] / c.js("window.innerWidth")
            crops = []
            for i in range(3):
                x0, y0 = sr["x"] + i * W * s, sr["y"]
                crops.append(shot.crop((int(round(x0 * k)) + 2, int(round(y0 * k)) + 2, int(round((x0 + W * s) * k)) - 2, int(round((y0 + H * s) * k)) - 2)))
            vis = sr["x"] + 3 * W * s <= c.js("document.getElementById('stage').getBoundingClientRect().right")
            c.click("#save-slides")
            c.wait_for("!Designer.saver.busy() || Designer.saver.asking()", 90, tell="document.getElementById('save-line').textContent")
            line = c.text("#save-line")
            case("v22 browser: Save slides on a design nothing here changed: three slides in the Carousel folder", line.startswith("Saved 3 slides in your Carousel folder, named \"Untouched\"") and not c.page_errors(), (line, c.page_errors()))
            saved = [carousel / f"Untouched - slide {i:02d}.jpg" for i in (1, 2, 3)]
            ims = [Image.open(p).convert("RGB") for p in saved if p.is_file()]
            case("v22 browser: ... three 1080 by 1350 JPEGs", len(ims) == 3 and all(im.size == (W, H) for im in ims), [im.size for im in ims])
            if len(ims) == 3 and vis:
                for i in range(3):
                    cr = crops[i]
                    sv = ims[i].resize(cr.size, Image.LANCZOS)
                    whole = sum(ImageStat.Stat(ImageChops.difference(sv, cr)).mean) / 3
                    print(f"NOTE  v22 pixel check, slide {i + 1}: mean difference {whole:.2f} of 255", flush=True)
                    case(f"v22 browser: pixel by pixel: saved slide {i + 1} is what the screen shows (mean difference {whole:.1f} of 255, at most 8)", whole <= 8.0, round(whole, 2))
            else:
                case("v22 browser: the three slides were all on screen for the pixel check", False, (len(ims), vis))
            case("v22 browser: nothing on the page asked the internet for anything but fonts", all(("fonts.googleapis.com" in u or "fonts.gstatic.com" in u) for u in c.outside_requests()), c.outside_requests()[:5])
        # ================= stories are as they were, with the centers (hers) =================
        with cd.Chrome(work=work / "chrome-v22-stories", size=(1400, 1000)) as c2:
            c2.init_script(NO_FINDER_JS)
            c2.open(f"{base}/design.html?kit={KQ}&kind=stories")
            c2.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 20)
            c2.wait_for("!document.getElementById('gallery').hidden", 5)
            g = json.loads(c2.js("JSON.stringify({add: !!document.getElementById('add-slides'), h: document.querySelector('#gallery h2').textContent, "
                                 "secs: Array.from(document.querySelectorAll('#gallery .dz-sec')).map(function(x){ return x.textContent; }), singles: !!document.getElementById('gallery-singles'), "
                                 "use: Array.from(new Set(Array.from(document.querySelectorAll('#gallery .dz-use')).map(function(x){ return x.textContent; }))), "
                                 "n: document.querySelectorAll('#gallery-starters .dz-card').length})"))
            case("v22 browser: the stories designer has no \"+ Add slides\" and no single slides: its window is \"Add stories\" with its three sections and seven layouts, as before",
                 g == {"add": False, "h": "Add stories", "secs": ["Start with", "Your templates", "Layouts"], "singles": False, "use": ["Add"], "n": 7}, g)
            case("v22 browser: nothing went wrong on the stories page", not c2.page_errors(), c2.page_errors())
    finally:
        srv.stop()
