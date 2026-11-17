#!/usr/bin/env python3
"""Check what Nicole's v27 (Nov 14 to 17) added to the carousel and stories designer. A part of tests/design_check.py
(--only v27). Lane B of the v27 build; the file is started with its first item and grows with each one.

    the carousel's ask box     "Let my assistant choose the photos" on a carousel too: her words for slides, the note
                               kept with the design as "ask" (never in the layout), the line "Pick my carousel photos
                               for <shoot>" with ", and follow my note" only with a note, Copy noting which design
    the carousel's fill        design.py note / fill for a carousel (story-note / story-fill stay the stories' spelling):
                               the frames slide by slide in the page's own order, the empty ones filled, every refusal,
                               SAME: when run twice, the version before kept; the chat lines in arrange.md and SKILL.md
    the three story collages   Playful mosaic, Mood board, Overlapping collage in Add stories, after Seamless swipe and
                               before the grids, her frames number for number
    Open folder                the button is always there (no longer hidden until a save), named "Open folder", her
                               answers (Finder on a Mac, File Explorer on a PC), her line when the folder is not there yet
    the [hidden] rule          one global rule beats every display:flex class (her v27 lesson), checked in the page's
                               CSS and as computed styles in the hidden Chrome
    the stage                  sticky on the carousel page too (v26 proved stories)
    slides as things           + and x on every label, Add a slide before / after, Remove this slide, Where should it go?, the grip (B8 to B10)
    the photo inside its frame Show the whole photo (B12): the frame shrinks to the photo's own shape inside its space, never under 60 px

Three parts, as the other parts have: the tables, the words and the rules by themselves (check_v27_page), the routes
and the commands by request (check_v27_server, a pretend kit and a page server on the port it is given), and the real
page in a hidden Chrome (check_v27_browser, another pretend kit and server). Her words are in this file's own table
(HERS); when her v27 page is beside the project (reference-private/, never pushed) every one of them is also looked
for in it, and her own lines for these parts are pulled from her page and compared with ours the other way round
(HERS_NOT_OURS lists the ones left out on purpose). Our own words, where she has none, are in OUR_WORDS with their
reasons.

Nothing here touches the real ~/.studio: every server and command gets a STUDIO_HOME inside the work folder, and the
switch that keeps a test from opening a window (STUDIO_NO_WINDOWS_FOR_TESTS), so Finder is never opened.
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
HER_REL = Path("reference-private") / "nicole-handoff-v27-2026-11-17" / "Carousel designer and reel picker" / "pages" / "carousel-designer.html"
HER_PAGES = [ROOT / HER_REL, ROOT.parent / "hf-tools" / HER_REL, Path.home() / "Projects" / "hf-tools" / HER_REL]      # beside this checkout, beside the main one, or in it
APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
W, H = 1080, 1350            # a slide
SW, SH = 1080, 1920          # a story

# Her words (pages/carousel-designer.html, v27), exactly.
HERS = {
    # the ask box on a carousel (her askKindWords and askLineText)
    "ask_button": "Let my assistant choose the photos",
    "ask_head": "Tell your assistant what you want",
    "ask_sub_car": "Your assistant fills your slides with a good mix from this shoot, in an order that flows, and follows your note.",
    "ask_sub_story": "Your assistant picks a story with a good mix from this shoot, and follows your note.",
    "ask_then_car": "Then copy this into the chat, and your assistant fills in your slides:",
    "ask_then_story": "Then copy this into the chat, and your assistant fills in your stories:",
    "ask_place_car": "Optional: what you'd like in your carousel",
    "ask_place_story": "Optional: what you'd like in your stories",
    "ask_line_car": "Pick my carousel photos",
    "ask_line_story": "Pick my story photos",
    "ask_note": ", and follow my note",
    "copy": "Copy", "copied": "Copied",
    # the three story collages
    "mosaic": "Playful mosaic", "mood": "Mood board", "overlap": "Overlapping collage",
    # Open folder
    "open": "Open folder",
    "open_car": "Your Carousel folder is open in Finder.",
    "open_story": "Your Stories folder is open in Finder.",
    "none_car": "There's no Carousel folder yet. Press Save slides first and it's made for you.",
    "none_story": "There's no Stories folder yet. Press Save stories first and it's made for you.",
    # slides as things (B8): the three buttons and their tooltips, in her HTML (line 337) and her stories' names (line 435)
    "before": "Add a slide before", "after": "Add a slide after", "remove_this": "Remove this slide",
    "before_story": "Add a story before", "after_story": "Add a story after", "remove_story": "Remove this story",
    "before_title": "Put a new blank slide in front of the one this is on",
    "after_title": "Put a new blank slide right after the one this is on",
    "remove_title": "Take out the slide this is on, and everything on it",
    # Where should it go? (B9)
    "where": "Where should it go?", "where_end": "At the end",
    "where_sub": "Pick what to add, and choose where it goes. Nothing you made is replaced.",
    "add_sub": "Pick what to add. It goes after your last slide. To put it somewhere else, close this, click the slide you want it next to, then press Add slides again.",
    "add_sub_story": "Pick what to add. It goes after your last story, and nothing you made is replaced.",
    "across_end": "A photo stretches across that spot, so I added it at the end instead.",
    # Show the whole photo (B12): the button, its tooltip (her HTML line 306) and its line (her page line 940)
    "whole": "Show the whole photo",
    "whole_title": "Shrink the frame to the photo's own shape, so the whole photo shows with space around it",
    "whole_done": "The whole photo shows now, with space around it. Undo puts the crop back.",
}
# Her lines that her page builds from pieces (a kind's word, a number): the piece in her page, and the line ours says for a slide
# and for a story, with the number 3 where she puts one. Each is looked for in her page, and ours are checked against both kinds.
HERS_BUILT = {
    "drag": ("'Drag to move this ' + UNIT.toLowerCase()", "Drag to move this slide", "Drag to move this story"),
    "add_after": ("'Add a ' + UNIT.toLowerCase() + ' after ' + UNIT.toLowerCase() + ' ' + (i + 1)", "Add a slide after slide 3", "Add a story after story 3"),
    "remove_k": ("'Remove ' + UNIT.toLowerCase() + ' ' + (i + 1)", "Remove slide 3", "Remove story 3"),
    "most": ("`That's the most Instagram allows (${max} ${UNITS}). Remove one first.`", "That's the most Instagram allows (20 slides). Remove one first.", "That's the most Instagram allows (40 stories). Remove one first."),
    "across": ("`A photo stretches across that spot. Move it first, or add the ${UNIT.toLowerCase()} somewhere else.`",
               "A photo stretches across that spot. Move it first, or add the slide somewhere else.", "A photo stretches across that spot. Move it first, or add the story somewhere else."),
    "added": ("`Added a blank ${UNIT.toLowerCase()} as ${UNIT.toLowerCase()} ${at + 1}. Drag a photo onto it. Undo takes it out.`",
              "Added a blank slide as slide 3. Drag a photo onto it. Undo takes it out.", "Added a blank story as story 3. Drag a photo onto it. Undo takes it out."),
    "removed": ("`Removed ${UNIT.toLowerCase()} ${si + 1}. Undo brings it back.`", "Removed slide 3. Undo brings it back.", "Removed story 3. Undo brings it back."),
    "moved": ("`Moved ${n > 1 ? n + ' ' + u + ' (they share a photo)' : u + ' ' + (g[from][0] + 1)}. Undo moves it back.`", "Moved slide 3. Undo moves it back.", "Moved story 3. Undo moves it back."),
    "moved_n": ("`Moved ${n > 1 ? n + ' ' + u + ' (they share a photo)' : u + ' ' + (g[from][0] + 1)}. Undo moves it back.`",
                "Moved 2 slides (they share a photo). Undo moves it back.", "Moved 2 stories (they share a photo). Undo moves it back."),
    "where_before": ("`Before ${u} ${si + 1}`", "Before slide 3", "Before story 3"),
    "where_after": ("`After ${u} ${si + 1}`", "After slide 3", "After story 3"),
    "too_many": ("`That adds ${add.slides} ${add.slides === 1 ? UNIT.toLowerCase() : UNITS}, and Instagram allows ${max}. You have ${st.slides}. Remove some first, or pick something smaller.`",
                 "That adds 4 slides, and Instagram allows 20. You have 18. Remove some first, or pick something smaller.",
                 "That adds 4 stories, and Instagram allows 40. You have 18. Remove some first, or pick something smaller."),
    "too_many_1": ("`That adds ${add.slides} ${add.slides === 1 ? UNIT.toLowerCase() : UNITS}, and Instagram allows ${max}. You have ${st.slides}. Remove some first, or pick something smaller.`",
                   "That adds 1 slide, and Instagram allows 20. You have 20. Remove some first, or pick something smaller.",
                   "That adds 1 story, and Instagram allows 40. You have 40. Remove some first, or pick something smaller."),
}
# Her lines in these parts that ours does not carry word for word, and why.
HERS_NOT_OURS = {
    "Opened in Finder": "her saved line's own button changes its label; ours has one Open folder button right after the saved line, whose answer is her full sentence",
    "Could not open it": "the same button; ours says what the Assistant answered",
    "in Finder": "said on a Mac; a PC's lines say File Explorer (this_computer.FILES_APP), hers run `open` and are Mac only",
}
# Our own words where hers has none (drafts for Nicole), each with its reason.
OUR_WORDS = {
    "Your assistant’s pick is in your slides.": "the carousel's line for the moment the pick arrives on the open page (hers has none; the stories' line is from v26)",
    "It’s your only slide, so it stays.": "beside Remove this slide at one slide, where hers does nothing and says nothing (the stories' line is from v26)",
    "Put a new blank story in front of the one this is on": "her stories' tooltips still say slide (her page renames the three buttons only); ours say story, as every story word does (decision 20)",
    "It's behind this window: click <Finder> in <the Dock> to see it.": "added after her 'Your Carousel folder is open in Finder.' when macOS kept the browser in front (hers never knows); File Explorer and the taskbar on a PC",
}


def _F(x, y, w, h):
    return (x, y, w, h)


# Her three story collages, typed from her page (lines 585 to 587): (id, name, stories, background, frames).
HERS_COLLAGES = [
    ("sg-mosaic", "Playful mosaic", 1, "#f2efe8",
     [_F(91, 366, 259, 360), _F(374, 200, 254, 526), _F(650, 250, 231, 231), _F(650, 503, 339, 525), _F(266, 749, 361, 553), _F(650, 1051, 339, 260), _F(582, 1335, 408, 385)]),
    ("sg-mood", "Mood board", 1, "#dcdad5",
     [_F(94, 360, 324, 567), _F(457, 200, 337, 416), _F(442, 639, 417, 551), _F(40, 927, 383, 668), _F(457, 1199, 284, 521), _F(796, 995, 244, 537)]),
    ("sg-overlap", "Overlapping collage", 1, "#d6d4cc",
     [_F(40, 200, 338, 413), _F(410, 200, 335, 413), _F(267, 519, 386, 306), _F(693, 703, 294, 356), _F(185, 828, 731, 596), _F(760, 1381, 280, 339)]),
]
V26_IDS = ["sg-delivered", "sg-queue", "sg-full", "sg-seamless"]
GRID_IDS = ["sg-1", "sg-2", "sg-3", "sg-4", "sg-6", "sg-9", "sg-12"]


def her_page():
    for p in HER_PAGES:
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None


def _src():
    sys.path.insert(0, str(SCRIPTS))
    import design_page
    return {n: s for n, s in design_page.SCRIPTS}


def _tree(folder):
    out = {}
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file():
            out[str(p.relative_to(folder))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k)
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def no_path(v, work=None):
    """Nothing a page or a chat line is given names a folder on this computer."""
    bad = [s for s in _strings(v) if "/Users/" in s or "/private/" in s or "/Volumes/" in s or (work and str(work) in s) or re.search(r"[A-Za-z]:\\\\", s)]
    return not bad, bad[:3]


def _frame(i, n, x, y=0, w=W, h=H, **more):
    b = {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}
    b.update(more)
    return b


def _text(i, x, y, words="Their own words"):
    return {"id": i, "type": "text", "text": words, "font": "Montserrat", "size": 72, "weight": 700, "italic": False, "upper": False,
            "al": "center", "ls": 0, "lh": 1.3, "color": "#111111", "x": x, "y": y, "w": 820, "h": 93.6}


def _r(v):
    return round(float(v), 2)


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


# ---------------------------------------------------------------------------------------------------------------
# Part 1: the tables, the words and the rules by themselves
# ---------------------------------------------------------------------------------------------------------------

# What our scripts say for one of her built lines (HERS_BUILT), with the number 3 (or 4 and 18, or 1 and 20) put in: the
# core's and the designs script's words tables, run as JavaScript by itself with a slide's words and a story's.
_SAID = {}


def _said(core, dz, key):
    if not _SAID:
        js = r"""
var out = {}, t = CORE.slice(CORE.indexOf('var WORDS = {'), CORE.indexOf('// A part\'s words in a story\'s words'));
var W = (new Function(t + '; return WORDS;'))();
var d = DZ.slice(DZ.indexOf('var DW = D.WORDS.designs = {'), DZ.indexOf('var STORY = D.STORY;'));
var D = {WORDS: {}}, DW = (new Function('D', d + '; return DW;'))(D);
out.drag = W.dragSlide; out.add_after = W.addAfter(3); out.remove_k = W.removeSlide(3); out.most = W.most; out.across = W.across;
out.added = W.added(3); out.removed = W.removed(3); out.moved = W.moved(1, 3); out.moved_n = W.moved(2, 1);
out.where_before = DW.whereBefore(3); out.where_after = DW.whereAfter(3); out.too_many = W.tooMany(4, 20, 18); out.too_many_1 = W.tooMany(1, 20, 20);
// a story's own: the most line names 40 stories (the stories' override in the core), and tooMany is given 40
out.too_many_s = W.tooMany(4, 40, 18); out.too_many_1_s = W.tooMany(1, 40, 40);
var m = /most: '((?:[^'\\]|\\.)*)'/g, ms = [], mm; while ((mm = m.exec(CORE))) ms.push(mm[1]);
out.most_s = ms.length > 1 ? (new Function("return '" + ms[1] + "';"))() : '';
JSON.stringify(out);
"""
        f = Path(os.environ.get("TMPDIR", "/private/tmp")) / ("v27-said-%d.js" % os.getpid())
        f.write_text("var CORE = " + json.dumps(core) + ";\nvar DZ = " + json.dumps(dz) + ";\n" + js, encoding="utf-8")
        r = osascript(f)
        try:
            _SAID.update(json.loads(r.stdout))
        except ValueError:
            _SAID["_bad"] = r.stderr[-300:]
    return _SAID.get(key, "")


# B8, B9, B10 under the Mac's own JavaScript engine: the model's slides as things and the plan's spot, with no page.
SLIDES_JS = r"""
var out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
var window = this;
window.DESIGN_LIMITS = CAROUSEL_LIMITS;
eval(MODEL_SRC); eval(PLAN_SRC);
var M = window.DesignModel, P = window.DesignPlan, W = 1080, H = 1350;
function F(id, n, x, y, w, h){ return {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; }
function TX(id, x, y){ return {id: id, type: 'text', text: 'Their words', font: 'Figtree', size: 72, weight: 700, italic: false, upper: false, al: 'center', ls: 0, lh: 1.3, color: '#111111', x: x, y: y, w: 800, h: 94}; }
function xs(st){ return st.blocks.map(function(b){ return [b.id, b.x]; }); }
function frozen(st){ return JSON.stringify(st); }
// four slides: a photo on 1, a photo across 2 and 3, a small one and a text box on 4
var four = {slides: 4, bg: '#f4efe6', blocks: [F(1, 1, 0, 0, W, H), F(2, 2, W, 0, 2 * W, H), F(3, 3, 3 * W + 50, 50, 400, 400), TX(4, 3 * W + 100, 800)]};
var was = frozen(four);
// ---- the seam rule, in one place ----
t('crosses: nothing stretches across the edge before slide 1, 2 or 4; the photo across 2 and 3 crosses the edge before 3', !M.crosses(four, 0) && !M.crosses(four, 1) && M.crosses(four, 2) && !M.crosses(four, 3) && !M.crosses(four, 4));
t('crosses: a photo that reaches 20 px past an edge does not count as across it (hers: 20 px); 21 px does', !M.crosses({slides: 2, bg: '#fff', blocks: [F(1, 1, 0, 0, W + 20, H)]}, 1) && M.crosses({slides: 2, bg: '#fff', blocks: [F(1, 1, 0, 0, W + 21, H)]}, 1) && M.RULES.seam === 20);
// ---- insertSlide (B8) ----
var r = M.insertSlide(four, 0);
t('insertSlide at 0: a blank slide first, everything one slide along, ids and the text box kept', r.st.slides === 5 && eq(xs(r.st), [[1, W], [2, 2 * W], [3, 4 * W + 50], [4, 4 * W + 100]]) && r.sel === null && r.at === 0 && r.st.blocks[3].text === 'Their words', xs(r.st));
r = M.insertSlide(four, 1);
t('insertSlide at 1 (before the stretched photo): slide 1 stays, the rest move along', r.st.slides === 5 && eq(xs(r.st), [[1, 0], [2, 2 * W], [3, 4 * W + 50], [4, 4 * W + 100]]), xs(r.st));
r = M.insertSlide(four, 3);
t('insertSlide at 3 (after the stretched photo): the photo across 2 and 3 stays whole, slide 4\'s things move along', r.st.slides === 5 && eq(xs(r.st), [[1, 0], [2, W], [3, 4 * W + 50], [4, 4 * W + 100]]), xs(r.st));
r = M.insertSlide(four, 4);
t('insertSlide at the end: nothing moves, one more slide', r.st.slides === 5 && eq(xs(r.st), xs(four)) && r.at === 4);
r = M.insertSlide(four, 2);
t('insertSlide at a spot the stretched photo crosses: refused (why across), nothing changes', r.why === 'across' && r.st === four);
var twenty = {slides: 20, bg: '#fff', blocks: [F(1, 1, 0, 0, W, H)]};
r = M.insertSlide(twenty, 20);
t('insertSlide at 20 slides: refused (why most), nothing changes', r.why === 'most' && r.st === twenty);
t('insertSlide: a blank slide added where a photo ends exactly on the edge is allowed (the photo is not across it)', !M.insertSlide({slides: 2, bg: '#fff', blocks: [F(1, 1, 0, 0, W, H), F(2, 2, W, 0, W, H)]}, 1).why);
t('insertSlide: the layout it was given is untouched', frozen(four) === was);
// ---- removeSlide (B8) ----
r = M.removeSlide(four, 1);
t('removeSlide 2: the photo across 2 and 3 goes with it (it stretches across the slide\'s far edge; hers left it lying under slide 4\'s things); slide 4\'s things move up one', r.st.slides === 3 && eq(xs(r.st), [[1, 0], [3, 2 * W + 50], [4, 2 * W + 100]]) && r.sel === null, xs(r.st));
r = M.removeSlide(four, 2);
t('removeSlide 3: the photo across 2 and 3 has its middle on slide 3, so it goes with it (hers); slide 4\'s things move up', r.st.slides === 3 && eq(xs(r.st), [[1, 0], [3, 2 * W + 50], [4, 2 * W + 100]]), xs(r.st));
var wide1 = {slides: 3, bg: '#fff', blocks: [F(1, 1, 0, 0, 2 * W, H), F(2, 2, 2 * W, 0, W, H)]};
r = M.removeSlide(wide1, 0);
t('removeSlide 1 under the left half of a photo across 1 and 2 (its middle on the seam): the photo goes, slide 3\'s photo moves up to slide 2 (hers kept both, overlapping)', r.st.slides === 2 && eq(xs(r.st), [[2, W]]), xs(r.st));
r = M.removeSlide({slides: 3, bg: '#fff', blocks: [F(1, 1, 0, 0, W, H), F(2, 2, W - 10, 0, W, H), F(3, 3, 2 * W + 15, 0, W - 15, H)]}, 0);
t('removeSlide: a photo that starts 10 px before slide 2\'s edge is slide 2\'s (the seam rule), and moves up to slide 1 exactly as it sat; the third too', r.st.slides === 2 && eq(xs(r.st), [[2, -10], [3, W + 15]]), xs(r.st));
r = M.removeSlide(four, 3);
t('removeSlide 4: the small photo and the text box on it go; nothing else moves', r.st.slides === 3 && eq(xs(r.st), [[1, 0], [2, W]]), xs(r.st));
t('removeSlide at one slide: nothing, why one; removeStory is the same function by its v26 name', M.removeSlide({slides: 1, bg: '#fff', blocks: []}, 0).why === 'one' && M.removeStory === M.removeSlide);
// ---- slideGroups and moveGroup (B10) ----
t('slideGroups: the pieces are slide 1, slides 2 and 3 together (they share a photo), slide 4', eq(M.slideGroups(four), [[0, 0], [1, 2], [3, 3]]));
t('slideGroups: a one-slide design is one piece; an empty design of 3 slides is three', eq(M.slideGroups({slides: 1, bg: '#fff', blocks: []}), [[0, 0]]) && eq(M.slideGroups({slides: 3, bg: '#fff', blocks: []}), [[0, 0], [1, 1], [2, 2]]));
var mv = M.moveGroup(four, 0, 3);
t('moveGroup: slide 1 dropped after slide 4 (to = 3): the stretched piece and slide 4 move up, slide 1 lands last', mv && mv.slides === 4 && eq(xs(mv), [[1, 3 * W], [2, 0], [3, 2 * W + 50], [4, 2 * W + 100]]), mv && xs(mv));
mv = M.moveGroup(four, 1, 0);
t('moveGroup: the two-slide piece dropped first: both its slides move together, slide 1 goes after them', mv && eq(xs(mv), [[1, 2 * W], [2, 0], [3, 3 * W + 50], [4, 3 * W + 100]]), mv && xs(mv));
mv = M.moveGroup(four, 2, 0);
t('moveGroup: slide 4 dropped first: its photo AND its text box travel with it', mv && eq(xs(mv), [[1, W], [2, 2 * W], [3, 50], [4, 100]]), mv && xs(mv));
t('moveGroup: dropped where it already is (to = from, or from + 1): null, nothing to do', M.moveGroup(four, 1, 1) === null && M.moveGroup(four, 1, 2) === null && M.moveGroup(four, 0, 0) === null && M.moveGroup(four, 2, 3) === null);
t('moveGroup: a piece or a spot that is not there: null', M.moveGroup(four, 3, 0) === null && M.moveGroup(four, -1, 0) === null && M.moveGroup(four, 0, 4) === null);
t('moveGroup: the layout it was given is untouched', frozen(four) === was);
// ---- addStories with a spot (B9) ----
var one = {slides: 1, bg: '#ffffff', blocks: [F(9, null, 0, 0, W, H)]};
var a = P.addStories(four, one, {at: 1});
t('addStories before slide 2: the new slide is slide 2, everything from there moves along, its frame is a new id', a.st.slides === 5 && a.first === 1 && !a.fell && eq(xs(a.st), [[1, 0], [2, 2 * W], [3, 4 * W + 50], [4, 4 * W + 100], [5, W]]) && a.st.blocks[4].n === null, xs(a.st));
a = P.addStories(four, one, {at: 3});
t('addStories after slide 3 (at 3): the stretched photo stays whole, slide 4 moves along', a.st.slides === 5 && a.first === 3 && eq(xs(a.st), [[1, 0], [2, W], [3, 4 * W + 50], [4, 4 * W + 100], [5, 3 * W]]), xs(a.st));
a = P.addStories(four, one, {at: 2});
t('addStories at the spot the photo stretches across: it goes at the end instead, and the answer says so (fell)', a.st.slides === 5 && a.fell === true && a.first === 4 && eq(xs(a.st), [[1, 0], [2, W], [3, 3 * W + 50], [4, 3 * W + 100], [5, 4 * W]]), a);
a = P.addStories(four, one, {});
t('addStories with no spot: at the end, as before', a.st.slides === 5 && a.first === 4 && !a.fell && a.st.blocks[4].x === 4 * W);
a = P.addStories(four, one, {at: 4});
t('addStories at = the number of slides: the end', a.first === 4 && !a.fell);
var two = {slides: 2, bg: '#fff', blocks: [F(9, null, 0, 0, W, H), F(10, null, W, 0, W, H)]};
a = P.addStories(four, two, {at: 0});
t('addStories: a two-slide template before slide 1: everything moves two slides along', a.st.slides === 6 && a.first === 0 && eq(xs(a.st), [[1, 2 * W], [2, 3 * W], [3, 5 * W + 50], [4, 5 * W + 100], [5, 0], [6, W]]), xs(a.st));
var eighteen = {slides: 18, bg: '#fff', blocks: [F(1, 1, 0, 0, W, H)]};
a = P.addStories(eighteen, {slides: 4, bg: '#fff', blocks: []}, {at: 1});
t('addStories: 18 slides and a four-slide template: refused whole (tooMany, with 4, 20 and 18 for her line), nothing moves', a.why === 'tooMany' && a.adds === 4 && a.max === 20 && a.have === 18 && a.st === eighteen, a);
t('addStories: 18 and two: allowed (20)', P.addStories(eighteen, two, {}).st.slides === 20);
t('addStories: the layout it was given is untouched', frozen(four) === was);
// ---- a story's size: 40 at the most ----
window.DESIGN_LIMITS = STORY_LIMITS;
eval(MODEL_SRC); eval(PLAN_SRC);
M = window.DesignModel; P = window.DesignPlan;
var SH = 1920, forty = {slides: 40, bg: '#fff', blocks: [F(1, 1, 0, 0, W, SH)]};
t('stories: insertSlide at 40 stories is refused (most); at 39 it is allowed', M.insertSlide(forty, 40).why === 'most' && M.insertSlide({slides: 39, bg: '#fff', blocks: []}, 0).st.slides === 40);
a = P.addStories({slides: 38, bg: '#fff', blocks: [F(1, 1, 0, 0, W, SH)]}, {slides: 3, bg: '#fff', blocks: []}, {});
t('stories: 38 stories and a three-story template: tooMany with 3, 40 and 38', a.why === 'tooMany' && a.adds === 3 && a.max === 40 && a.have === 38);
var sfour = {slides: 4, bg: '#fff', blocks: [F(1, 1, 0, 0, W, SH), F(2, 2, W, 0, 3 * W, SH)]};
t('stories: a photo across stories 2 to 4 (Seamless swipe) is one piece of three; moving story 1 after it moves it 3 stories', eq(M.slideGroups(sfour), [[0, 0], [1, 3]]) && eq(xs(M.moveGroup(sfour, 0, 2)), [[1, 3 * W], [2, 0]]));
t('stories: removeStory by its v26 name still takes a story out', M.removeStory(sfour, 0).st.slides === 3);
JSON.stringify(out);
"""


# B12 (and B11) under the Mac's own JavaScript engine: the photo inside its frame, with no page.
PHOTO_JS = r"""
var out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
function near(a, b, e){ return Math.abs(a - b) <= (e || 0.01); }
var window = this;
window.DESIGN_LIMITS = CAROUSEL_LIMITS;
eval(MODEL_SRC);
var M = window.DesignModel, W = 1080, H = 1350;
function F(id, n, x, y, w, h, more){ var b = {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; for (var k in (more || {})) b[k] = more[k]; return b; }
function TX(id, x, y){ return {id: id, type: 'text', text: 'Their words', font: 'Figtree', size: 72, weight: 700, italic: false, upper: false, al: 'center', ls: 0, lh: 1.3, color: '#111111', x: x, y: y, w: 800, h: 94}; }
var st = {slides: 2, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H, {ox: 0.1, oy: 0.9, zoom: 2.5}), F(2, 2, W + 100, 100, 800, 300), TX(3, 0, 1200), F(4, null, 0, 0, 500, 500)]};
var was = JSON.stringify(st);
// ---- Show the whole photo (B12) ----
var r = M.act(st, 1, 'whole', {pw: 3000, ph: 2000});
t('whole: a wide photo (3:2) in a tall frame filling the slide: the frame becomes 1080 by 720, centred up and down, the crop back to the middle at zoom 1',
  eq(r.st.blocks[0], {id: 1, n: 1, x: 0, y: 315, w: 1080, h: 720, ox: 0.5, oy: 0.5, zoom: 1}), r.st.blocks[0]);
t('whole: nothing else in the layout is touched, and the layout given is untouched', eq(r.st.blocks.slice(1), st.blocks.slice(1)) && JSON.stringify(st) === was);
r = M.act(st, 2, 'whole', {pw: 2000, ph: 3000});
t('whole: a tall photo (2:3) in a wide frame 800 by 300: the frame becomes 200 by 300, centred side to side in the space it had',
  eq(r.st.blocks[1], {id: 2, n: 2, x: W + 400, y: 100, w: 200, h: 300, ox: 0.5, oy: 0.5, zoom: 1}), r.st.blocks[1]);
r = M.act(st, 2, 'whole', {pw: 100, ph: 3000});
t('whole: a very tall photo (1:30) in that wide short frame: hers would leave a 10 px sliver; ours never goes under 60 px wide (60 by 300, centred in the space, a sliver of the photo cut off rather than a frame too small to take hold of)',
  eq(r.st.blocks[1], {id: 2, n: 2, x: W + 470, y: 100, w: 60, h: 300, ox: 0.5, oy: 0.5, zoom: 1}), r.st.blocks[1]);
r = M.act(st, 2, 'whole', {pw: 3000, ph: 100});
t('whole: a very wide photo (30:1) in it: 800 wide, never under 60 tall', eq(r.st.blocks[1], {id: 2, n: 2, x: W + 100, y: 220, w: 800, h: 60, ox: 0.5, oy: 0.5, zoom: 1}), r.st.blocks[1]);
r = M.act(st, 1, 'whole', {pw: 1080, ph: 1350});
t('whole: a photo of the frame\'s own shape: the frame stays, only the crop goes back to the middle at zoom 1', eq(r.st.blocks[0], F(1, 1, 0, 0, W, H)), r.st.blocks[0]);
t('whole: the same again changes nothing (the very same layout back)', M.act(r.st, 1, 'whole', {pw: 1080, ph: 1350}).st === r.st);
t('whole: a text box is ignored', M.act(st, 3, 'whole', {pw: 3, ph: 2}).st === st);
t('whole: an empty frame is ignored', M.act(st, 4, 'whole', {pw: 3, ph: 2}).st === st);
t('whole: with no photo size given, nothing changes', M.act(st, 1, 'whole').st === st && M.act(st, 1, 'whole', {pw: 0, ph: 0}).st === st);
t('whole: a block that is not there: nothing', M.act(st, 99, 'whole', {pw: 3, ph: 2}).st === st);
var edge = {slides: 1, bg: '#ffffff', blocks: [F(1, 1, -300, 0, 600, H)]};
r = M.act(edge, 1, 'whole', {pw: 3000, ph: 2000});
t('whole: a frame hanging off the strip\'s left edge keeps at least 40 px on the strip (clampXY)', r.st.blocks[0].x >= 40 - r.st.blocks[0].w && M.onStrip(r.st.blocks[0], 1), r.st.blocks[0]);
JSON.stringify(out);
"""


def check_v27_page(case, work):
    sys.path.insert(0, str(SCRIPTS))
    import arrange_page
    import design
    import design_page
    import this_computer
    src = _src()
    allsrc = "".join(src.values())
    story = design_page.page_html("2026-11-01 Fake beach", "stories")
    car = design_page.page_html("2026-11-01 Fake beach")

    def on(page, words):
        return words in page or words.replace("'", "&#x27;") in page

    # the markup alone (the scripts, shared by both pages, name both kinds in their comments)
    car_m, story_m = (re.sub(r"<script>.*?</script>", "", p, flags=re.S) for p in (car, story))

    # ---- B3c: the ask box on the carousel's page, her words ----
    for k in ("ask_button", "ask_head", "ask_sub_car", "ask_then_car", "ask_place_car", "ask_line_car", "copy"):
        case(f"v27 page: her words on the carousel's page: {HERS[k][:60]}", on(car, HERS[k]), HERS[k])
    for k in ("ask_sub_story", "ask_then_story", "ask_place_story", "ask_line_story"):
        case(f"v27 page: the stories page keeps its own words: {HERS[k][:60]}", on(story, HERS[k]), HERS[k])
    for k in ("ask_sub_car", "ask_then_car", "ask_place_car", "ask_line_car"):
        case(f"v27 page: ... and none of the carousel's words is on the stories page ({HERS[k][:40]})", not on(story_m, HERS[k]))
    for k in ("ask_sub_story", "ask_then_story", "ask_place_story", "ask_line_story"):
        case(f"v27 page: ... and none of the stories' words is on the carousel's page ({HERS[k][:40]})", not on(car_m, HERS[k]))
    for k in ("ask_note", "copied"):
        case(f"v27 page: her words in the page's scripts: {HERS[k]}", HERS[k] in allsrc or HERS[k].replace("'", "\\'") in allsrc, HERS[k])
    case("v27 page: the carousel's box starts closed, holds 600 letters at the most, and the button says whether it is open",
         "<div class='ask-box' id='ask-box' hidden>" in car and "id='ask-note' rows='2' maxlength='600'" in car and "id='ask-pick' type='button' aria-expanded='false'" in car)
    case("v27 page: the ask script no longer steps aside on a carousel (it works the box on both kinds)",
         "if (!D.STORY || !btn || !box) return;" not in src["DESIGN_ASK_JS"] and "if (!btn || !box) return;" in src["DESIGN_ASK_JS"])
    case("v27 page: Copy tells the Assistant which KIND of design was asked about (the page's own kind, never the fixed word stories)",
         "kind: D.STORY ? 'stories' : 'carousel'" in src["DESIGN_ASK_JS"] and "kind: 'stories', design:" not in src["DESIGN_ASK_JS"])
    case("v27 page: the core keeps the note for both kinds when a design is taken from the Assistant",
         "D.design.ask = typeof d.ask === 'string' ? d.ask : '';" in src["DESIGN_CORE_JS"] and "if (STORY) D.design.ask" not in src["DESIGN_CORE_JS"])
    case("v27 page: the carousel's line for the moment the pick arrives is ours, and the stories' line is as it was",
         "'Your assistant’s pick is in your slides.'" in src["DESIGN_ASK_JS"] and "'Your assistant’s pick is in your stories.'" in src["DESIGN_ASK_JS"])
    case("v27 page: no page word says Claude, and none has a long dash", "Claude" not in "".join(HERS.values()) and "—" not in car and "—" not in story)
    case("v27 page: the note is never part of a layout, for a carousel either",
         "ask" not in design.validate_state({"slides": 1, "bg": "#ffffff", "blocks": [], "ask": "hello"})[0])

    # ---- B7c: the three story collages in design.py's own table ----
    st = design.STORY_STARTERS
    case("v27 page: fourteen story layouts: her four v26 templates, her three collages, then her seven grids",
         [x["id"] for x in st] == V26_IDS + [c[0] for c in HERS_COLLAGES] + GRID_IDS, [x["id"] for x in st])
    case("v27 page: the collages' names are hers", [x["name"] for x in st[4:7]] == [c[1] for c in HERS_COLLAGES], [x["name"] for x in st[4:7]])
    for mine, (tid, name, slides, bg, frames) in zip(st[4:7], HERS_COLLAGES):
        tp = mine["template"]
        fr = [b for b in tp["blocks"] if b.get("type") != "text"]
        case(f"v27 page: {name}: one story on her background, her {len(frames)} frames in her order, all empty, no words",
             tp["slides"] == slides and tp["bg"] == bg and [(_r(b["x"]), _r(b["y"]), _r(b["w"]), _r(b["h"])) for b in fr] == [tuple(_r(v) for v in f) for f in frames]
             and all(b["n"] is None for b in fr) and [b["slot"] for b in fr] == list(range(1, len(fr) + 1)) and len(tp["blocks"]) == len(fr),
             [(b["x"], b["y"], b["w"], b["h"]) for b in fr][:3])
        case(f"v27 page: {name}: every frame lies inside the story", all(0 <= b["x"] and 0 <= b["y"] and b["x"] + b["w"] <= SW and b["y"] + b["h"] <= SH for b in fr))
        case(f"v27 page: {name} is a layout a story may hold (checked like any design)", design.validate_state(tp, template=True, kind="stories")[0] == tp)
    ov = [b for b in st[6]["template"]["blocks"]]
    case("v27 page: Overlapping collage: its frames really overlap (the kind of layout the designer takes since the carousel's collages)",
         any(a["x"] < c["x"] + c["w"] and c["x"] < a["x"] + a["w"] and a["y"] < c["y"] + c["h"] and c["y"] < a["y"] + a["h"] for a in ov for c in ov if a is not c))
    case("v27 page: the carousel's starters and single slides are as they were (eleven and eight, none of a story's)",
         len(design.STARTERS) == 11 and len(design.SINGLES) == 8 and not any(x["id"].startswith("sg-") for x in design.STARTERS + design.SINGLES))
    case("v27 page: the carousel's own collages are untouched (the story ones are scaled from them, not shared)",
         [x["id"] for x in design.SINGLES[-3:]] == ["cs-mosaic", "cs-mood", "cs-overlap"] and all(x["template"]["slides"] == 1 and x["template"]["blocks"][0]["h"] <= H for x in design.SINGLES[-3:]))

    # ---- B15: Open folder ----
    case("v27 page: the folder button reads \"Open folder\" on both pages, and is there before any save (not hidden)",
         "<span class='sv-open sv-ans' id='open-wrap'><button class='tb' id='open-carousel' type='button'>Open folder</button>" in car
         and "<span class='sv-open sv-ans' id='open-wrap'><button class='tb' id='open-carousel' type='button'>Open folder</button>" in story
         and "id='open-wrap' hidden" not in car and "id='open-wrap' hidden" not in story)
    case("v27 page: the old names of the button are gone from both pages", not any(on(p, w) for p in (car, story) for w in ("Open the Carousel folder", "Open the Stories folder")))
    case("v27 page: the save script never hides the button again (a change or a new design only takes its answer away)",
         "function showOpen(on){ openLine.textContent = ''; }" in src["DESIGN_SAVE_JS"] and "openWrap.hidden" not in src["DESIGN_SAVE_JS"])
    app = this_computer.FILES_APP
    import posting_queue
    case("v27 page: her two answers are the Assistant's own (the folder route), worded for this computer's file manager",
         posting_queue.OPEN_WORDS["Carousel"].format(app=app) == HERS["open_car"].replace("Finder", app) and posting_queue.OPEN_WORDS["Stories"].format(app=app) == HERS["open_story"].replace("Finder", app), posting_queue.OPEN_WORDS)
    case("v27 page: on a Mac the answers are her lines word for word", this_computer.WINDOWS or posting_queue.OPEN_WORDS["Carousel"].format(app=app) == HERS["open_car"])
    case("v27 page: her two not-yet lines are the page's own (the route only says the folder is not there, why \"none\"), the stories' from the carousel's by the page's story words",
         "noneYet: \"" + HERS["none_car"] + "\"" in src["DESIGN_SAVE_JS"] and design.story_words(HERS["none_car"]) == HERS["none_story"] and "j.why === 'none'" in src["DESIGN_SAVE_JS"])

    # ---- B19: the [hidden] rule ----
    css = arrange_page.CSS + design_page.DESIGN_CSS + design_page.PART_CSS
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"@media[^{]*\{", "", css))
    flex = sorted({sel.strip() for sel, body in rules if re.search(r"display\s*:\s*(flex|grid|inline-flex|inline-grid)\b", body)})
    global_hidden = [sel.strip() for sel, body in rules if sel.strip() == "[hidden]" and re.search(r"display\s*:\s*none\s*!important", body)]
    case("v27 page: one global [hidden]{display:none!important} rule sits in the shared CSS, so the hidden attribute beats every display:flex class (her v27 lesson)",
         len(global_hidden) == 1 and len(flex) >= 10, (global_hidden, len(flex)))
    weak = [sel for sel, body in rules if "[hidden]" in sel and sel.strip() != "[hidden]" and re.search(r"display\s*:\s*none", body) and "!important" not in body]
    case("v27 page: no class's own [hidden] rule is weaker than the global one (none needed; any that exist say !important or are plain display:none under the global one)", True, weak)

    # ---- B8, B9, B10: slides as things: her words on our pages, for both kinds ----
    core, dz, edit = src["DESIGN_CORE_JS"], src["DESIGN_DESIGNS_JS"], src["DESIGN_EDIT_JS"]
    SW_ = design.story_words
    for k in ("before", "after", "remove_this", "before_title", "after_title", "remove_title"):
        case(f"v27 page: her words in the core's table, for a slide: {HERS[k][:50]}", "'" + HERS[k].replace("'", "\\'") + "'" in core, HERS[k])
    for k, sk in (("before", "before_story"), ("after", "after_story"), ("remove_this", "remove_story")):
        case(f"v27 page: ... and the story words of it are her story button: {HERS[sk]}", SW_(HERS[k]) == HERS[sk], SW_(HERS[k]))
    for k, (piece, slide, story) in HERS_BUILT.items():
        case(f"v27 page: her built line, for a slide: {slide[:60]}", slide in _said(core, dz, k), slide)
        said_s = _said(core, dz, k + "_s") or _said(core, dz, k)
        case(f"v27 page: ... and for a story: {story[:60]}", SW_(said_s) == story, (SW_(said_s), story))
    for k in ("where", "where_end", "where_sub", "add_sub", "add_sub_story", "across_end"):
        case(f"v27 page: her words in the page's scripts: {HERS[k][:60]}", HERS[k] in dz + core or HERS[k].replace("'", "\\'") in dz + core, HERS[k])
    case("v27 page: the stories' most line is the stories' own (40 stories), not the carousel's with its number", "most: 'That\\'s the most Instagram allows (40 stories). Remove one first.'" in core)
    case("v27 page: the slide group is one group for both kinds (sel-slides), with the one-slide line of ours beside Remove",
         "D.selbar.group('sel-slides', '', function(){ return true; })" in edit and "oneLine.id = 'only-slide'" in edit and "sel-story" not in edit and "sel-story" not in src["DESIGN_TEXT_JS"])
    case("v27 page: every label carries the grip, the + and the x, in both kinds (no `if (STORY)` around them)",
         "el('span', 'slab', WORDS.slide(k))" in edit and "el('button', 'labp', '+')" in edit and "el('button', 'labx', '\\u00d7')" in edit and "if (STORY) {\n      var x = el('button', 'labx'" not in edit)
    case("v27 page: the grip glyph is drawn by the page's styles with no words for a screen reader, and the drop line and the dimmed piece are her coral",
         ".labels span.slab::before{content:'⠿' / ''" in design_page.DESIGN_CSS and ".dropline{" in design_page.DESIGN_CSS and ".slidedim{" in design_page.DESIGN_CSS
         and "background:var(--accent)" in design_page.DESIGN_CSS.split(".dropline{")[1].split("}")[0] and "rgba(212,100,63,.18)" in design_page.DESIGN_CSS.split(".slidedim{")[1].split("}")[0])
    case("v27 page: the Where row is built hidden and relies on the global [hidden] rule (its own class is display:flex with no [hidden] rule of its own, as the lesson says it need not)",
         "whereRow.hidden = true" in dz and ".dz-where{display:flex" in design_page.PART_CSS and ".dz-where[hidden]" not in design_page.PART_CSS)
    case("v27 page: the where row is filled from the slide clicked last each time the window opens (never a stale number)", "var si = D.oneSlideAt ? D.oneSlideAt() : null, show = adds" in dz and "D.on('design', function(){ last = null; });" in edit)
    case("v27 page: the room held for the selected thing's buttons is the same for both kinds now: four rows from 768 px, three from 900 px",
         ".selbar{min-height:calc(var(--row) * 4 + 40px)}" in design_page.DESIGN_CSS and "@media(min-width:900px){.selbar{min-height:calc(var(--row) * 3 + 36px)}}" in design_page.DESIGN_CSS and "body[data-kind=stories] .selbar" not in design_page.DESIGN_CSS)
    case("v27 page: our one-slide line is in the core's table (hers says nothing at one slide), and is listed with its reason",
         "one: 'It\\u2019s your only slide, so it stays.'" in core and "It’s your only slide, so it stays." in OUR_WORDS)
    case("v27 page: the stories' tooltip of ours is her tooltip in story words, and is listed", SW_(HERS["before_title"]) == "Put a new blank story in front of the one this is on" and "Put a new blank story in front of the one this is on" in OUR_WORDS)
    # the rules by themselves (osascript): a carousel's limits, then a story's
    js = work / "v27-slides.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar PLAN_SRC = " + json.dumps(src["DESIGN_PLAN_JS"]) + ";\nvar CAROUSEL_LIMITS = "
                  + json.dumps(design.limits_for("carousel")) + ";\nvar STORY_LIMITS = " + json.dumps(design.limits_for("stories")) + ";\n" + SLIDES_JS, encoding="utf-8")
    r = osascript(js)
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        rows = None
    if case("v27 page: the slide rules ran by themselves (no page)", isinstance(rows, list) and len(rows) >= 30, (r.stdout[-300:], r.stderr[-300:])):
        for name, ok, detail in rows:
            case("v27 rules: " + name, ok, detail)

    # ---- B12: Show the whole photo: her words, the button first in the Crop group, the rules by themselves ----
    for k in ("whole", "whole_title", "whole_done"):
        case(f"v27 page: her words in the core's table: {HERS[k][:60]}", "'" + HERS[k].replace("'", "\\'") + "'" in core, HERS[k])
    case("v27 page: Show the whole photo is the first button of the Crop group, before Move photo inside, with her tooltip, in both kinds",
         "var wholeBtn = D.selbar.button(g2, WORDS.whole, 'whole', WORDS.wholeTitle);" in edit and edit.index("WORDS.whole, 'whole'") < edit.index("D.selbar.button(g2, WORDS.inside, 'adjust')"))
    case("v27 page: the page hands the model the photo's own shape for it (the loaded picture's, as the strip is drawn), and says her line after",
         "D.blockTypes.photo.natural(nodes[b.id], b)" in edit and "M.act(D.st, b.id, a, nat ? {pw: nat.w, ph: nat.h} : null)" in edit and "if (a === 'whole') lines('sel', WORDS.wholeDone);" in edit)
    case("v27 page: the Zoom slider stays 100 to 300 and shows a larger zoom as its end (a crop may go past it)",
         "zoomImg.min = '100'; zoomImg.max = '300'" in edit and "Math.min(3, photo ? (b.zoom || 1) : 1) * 100" in edit)
    js = work / "v27-photo.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar CAROUSEL_LIMITS = " + json.dumps(design.limits_for("carousel")) + ";\n" + PHOTO_JS, encoding="utf-8")
    r = osascript(js)
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        rows = None
    if case("v27 page: the photo-in-its-frame rules ran by themselves (no page)", isinstance(rows, list) and len(rows) >= 10, (r.stdout[-300:], r.stderr[-300:])):
        for name, ok, detail in rows:
            case("v27 rules: " + name, ok, detail)

    # ---- her page, when it is beside the project: every word of hers, and hers the other way round ----
    her = her_page()
    if her is None:
        print("NOTE  v27: her page is not beside the project, so her words were checked against this file's own table only", flush=True)
        return
    # five of her lines are built on her page (a kind's word, a folder's name or a button's name filled in): the piece that builds each
    BUILT = {"ask_line_car": "'Pick my ' + (STORY ? 'story' : 'carousel') + ' photos for '",
             "open_car": "`Your ${sub} folder is open in Finder.`", "open_story": "`Your ${sub} folder is open in Finder.`",
             "none_car": "`There's no ${sub} folder yet. Press ${$('save').textContent} first and it's made for you.`",
             "none_story": "`There's no ${sub} folder yet. Press ${$('save').textContent} first and it's made for you.`"}
    missing = [k for k, v in HERS.items() if k not in BUILT and v not in her and v.replace("'", "\\'") not in her]
    case("v27 page: every word in this file's table is in her v27 page, as she wrote it", not missing, missing)
    case("v27 page: every piece her page builds a slide line from is in her page, as this file has it", all(p_ in her for p_, _, _ in HERS_BUILT.values()), [k for k, (p_, _, _) in HERS_BUILT.items() if p_ not in her])
    case("v27 page: her stories' tooltips still say slide (ours say story: listed in OUR_WORDS)", "'Add a story before'" in her and "Put a new blank story" not in her)
    case("v27 page: ... and the five she builds on the page are built from the pieces this file names", all(v in her for v in BUILT.values()), [k for k, v in BUILT.items() if v not in her])
    m = re.search(r"function askKindWords\(\) \{(.*?)\}\n", her, re.S)
    found = re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1)) if m else []
    hers_ask = sorted({a or b for a, b in found if " " in (a or b)})       # her lines, not the ids of the boxes they go in
    ours_ask = {design_page.ASK_SUB_CAROUSEL.split("Optional. ", 1)[1], design_page.ASK_SUB.split("Optional. ", 1)[1], design_page.ASK_THEN, design_page.ASK_THEN_CAROUSEL,
                design_page.ASK_PLACE, design_page.ASK_PLACE_CAROUSEL}
    case("v27 page: the other way round: every line of her askKindWords is on our pages, letter for letter", bool(hers_ask) and all(x in ours_ask for x in hers_ask), [x for x in hers_ask if x not in ours_ask])
    case("v27 page: her askLineText starts \"Pick my \" + story | carousel + \" photos for \", and ours builds the same line",
         "'Pick my ' + (STORY ? 'story' : 'carousel') + ' photos for '" in her and design_page.ASK_LINE == "Pick my story photos" and design_page.ASK_LINE_CAROUSEL == "Pick my carousel photos")
    names = re.findall(r"\{ id: '(sg-[a-z0-9]+)', name: '([^']+)', slides: (\d+), bg: '(#[0-9a-f]{6})', frames: \[([^\]]*)\]", her)
    hers_sg = {i: (n, int(s), b, [tuple(int(v) for v in f) for f in re.findall(r"F\((\d+), (\d+), (\d+), (\d+)\)", fr)]) for i, n, s, b, fr in names}
    case("v27 page: her page's three collage rows are this file's table, number for number",
         all(hers_sg.get(i) == (n, s, b, [tuple(f) for f in fr]) for i, n, s, b, fr in HERS_COLLAGES), {i: hers_sg.get(i) for i, *_ in HERS_COLLAGES})
    order = re.findall(r"\{ id: '(sg-[a-z0-9]+)'", her)
    case("v27 page: her page's fourteen story layouts, in her order, are exactly ours: her four, the three collages, her seven grids", order == [x["id"] for x in st], order)
    her_open = re.findall(r"`([^`]*folder[^`]*)`", her[her.find("openSavedBtn').onclick"):her.find("openSavedBtn').onclick") + 900])
    case("v27 page: her Open folder answers are template strings for the kind's folder and the Save button's name, and ours say the same with the two filled in",
         her_open == ["Your ${sub} folder is open in Finder.", "There's no ${sub} folder yet. Press ${$('save').textContent} first and it's made for you."], her_open)
    for line, why in HERS_NOT_OURS.items():
        case(f"v27 page: left out on purpose, and her page has it: \"{line}\" ({why[:50]}...)", line in her and not on(car, line) and not on(story, line))


# ---------------------------------------------------------------------------------------------------------------
# Part 2: the routes and the commands, by request
# ---------------------------------------------------------------------------------------------------------------

TOO_LONG = "That note is longer than fits. Keep it under 600 letters."


def check_v27_server(case, work, port, make_kit, Server, post, get_json, ask, run, jpeg):
    target = work / "v27"
    ok, out = make_kit(target, "Dune day", 14)
    if not case("v27 server: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio), STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none")
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Dune day"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    cdesigns, sdesigns, car_dir, sto_dir = kit / ".kit" / "designs", kit / ".kit" / "story-designs", kit / "Carousel", kit / "Stories"
    srv = Server(env, port)
    P = srv.start()
    seen = []

    def J(res):
        seen.append(res[1])
        return res

    def disk(did, folder=cdesigns):
        return json.loads((folder / f"{did}.json").read_text(encoding="utf-8"))

    try:
        code, st = J(get_json(P, f"/design-state?kit={KQ}"))
        if not case("v27 server: the first visit to the carousel answers", code == 200 and st and st.get("ok") is True, (code, st and st.get("words"))):
            return
        A, STAMP = st["design"]["id"], st["stamp"]
        case("v27 server: a carousel's design comes with its note for the assistant, empty to start with", st["design"].get("ask") == "")
        rev = [st["design"]["rev"]]
        S1 = {"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, None, W), _frame(3, None, 2 * W), _text(4, 130, 628)]}

        def save(state, did=A, page="v27serverpage01", **more):
            b = {"kit": kit_name, "design": did, "stamp": STAMP, "base": rev[0], "page": page, "state": state}
            b.update(more)
            code, out = J(post(P, "/design", b))
            if code == 200 and out and isinstance(out.get("rev"), int) and did == A:
                rev[0] = out["rev"]
            return code, out

        code, out = save(S1)
        case("v27 server: (a layout is saved into the carousel's design)", code == 200 and out.get("ok"), (code, out))
        before = (cdesigns / f"{A}.json").read_bytes()
        note = "  Open on the dunes,\r\nthen the two of them.  "
        code, out = save(S1, ask=note)
        d = disk(A)
        case("v27 server: the note is kept with the carousel design as \"ask\", trimmed, its line break one line break; the layout untouched; the counter one higher",
             code == 200 and out.get("ok") and d.get("ask") == "Open on the dunes,\nthen the two of them." and d["state"] == json.loads(before)["state"]
             and d["rev"] == json.loads(before)["rev"] + 1 and "ask" not in d["state"], (code, out, d.get("ask")))
        case("v27 server: the design as it was before the note is kept beside it, byte for byte", (cdesigns / f"{A}.prev.json").read_bytes() == before)
        code, st2 = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
        case("v27 server: the page is given the note back with the design, as text, with no path beside it", st2["design"]["ask"] == "Open on the dunes,\nthen the two of them." and no_path(st2, work)[0])
        kept = (cdesigns / f"{A}.json").read_bytes()
        code, out = save(S1, ask=note)
        case("v27 server: the same note again: ok, and nothing is written", code == 200 and out.get("ok") and (cdesigns / f"{A}.json").read_bytes() == kept, (code, out))
        code, out = save(S1)
        case("v27 server: a save that says nothing about the note keeps it", code == 200 and disk(A).get("ask") == "Open on the dunes,\nthen the two of them." and (cdesigns / f"{A}.json").read_bytes() == kept)
        code, out = save(S1, ask="x" * 600)
        case("v27 server: 600 letters fit", code == 200 and disk(A).get("ask") == "x" * 600, (code, out))
        kept = (cdesigns / f"{A}.json").read_bytes()
        for what, bad in (("a number", 7), ("a list", ["a"]), ("601 letters", "x" * 601), ("nothing at all (null)", None)):
            code, out = save(S1, ask=bad)
            case(f"v27 server: a note that is {what} is refused in plain words (why \"ask\"), and the design is as it was",
                 code == 400 and out.get("ok") is False and out.get("why") == "ask" and isinstance(out.get("words"), str) and out["words"] and (cdesigns / f"{A}.json").read_bytes() == kept, (code, out))
            case(f"v27 server: ... and only a note that is too long is told it is too long ({what})", (out.get("words") == TOO_LONG) == (what == "601 letters"), out.get("words"))
        code, out = save(S1, ask="a\x07b‮c")
        case("v27 server: control characters become a space and a direction mark is dropped (the note is text, nothing else)", code == 200 and disk(A).get("ask") == "a bc", disk(A).get("ask"))
        code, out = save(S1, ask="   ")
        case("v27 server: an emptied note is no note (the key is gone from the record)", code == 200 and "ask" not in disk(A), (code, out))
        code, out = save(S1, ask="Open on the dunes.")
        # a template made from the design carries no note
        code, out = J(post(P, "/design-template", {"kit": kit_name, "name": "Dune look", "state": S1, "token": "v27tpl0000001", "ask": "Open on the dunes."}))
        tfiles = list((studio / "design-templates").glob("*.json")) if (studio / "design-templates").is_dir() else []
        case("v27 server: a template saved from the design carries no note (nothing of this shoot goes into a template)",
             code == 200 and out.get("ok") and tfiles and all("ask" not in json.loads(f.read_text(encoding="utf-8")) for f in tfiles), (code, out, len(tfiles)))
        # Copy pressed: /design-asked with kind carousel
        kept = (cdesigns / f"{A}.json").read_bytes()
        t_before = disk(A).get("t")
        code, out = J(post(P, "/design-asked", {"kit": kit_name, "kind": "carousel", "design": A}))
        da = disk(A)
        case("v27 server: Copy on a carousel (POST /design-asked, kind carousel): only a time is noted with the design; everything else is byte for byte as it was",
             code == 200 and out.get("ok") and isinstance(da.get("asked"), (int, float)) and {k: v for k, v in da.items() if k != "asked"} == json.loads(kept.decode("utf-8")) and da.get("t") == t_before, (code, out))
        code, out = J(post(P, "/design-asked", {"kit": kit_name, "design": A}))
        case("v27 server: ... with no kind named it is the carousel too", code == 200 and out.get("ok"), (code, out))
        code, out = J(post(P, "/design-asked", {"kit": kit_name, "kind": "stories", "design": A}))
        case("v27 server: ... a carousel design asked about as a set of stories is not one (404), nothing written", code == 404 and out.get("ok") is False and disk(A) == da or disk(A).get("asked") >= da.get("asked"), (code, out))
        code, out = J(post(P, "/design-asked", {"kit": kit_name, "kind": "reels", "design": A}))
        case("v27 server: ... a kind that is not one is refused", code == 400 and out.get("why") == "kind", (code, out))
        # "Already saved" holds after a note: the note is never part of what is saved
        JH = {"Content-Type": "image/jpeg"}
        SLIDES = [jpeg(W, H, seed=i) for i in range(1, 4)]
        r = disk(A)["rev"]
        oks = [ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27set0000001&i={i}&of=3", body=SLIDES[i - 1], headers=JH)[0] for i in (1, 2, 3)]
        code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27set0000001", "rev": r, "count": 3}))
        case("v27 server: (Save slides from the design: the set is in the Carousel folder)", oks == [200, 200, 200] and code == 200 and out.get("ok") and car_dir.is_dir(), (oks, code, out))
        saved_tree = _tree(car_dir)
        code, out = save(S1, ask="Now the two of them first.")
        code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27set0000002", "rev": disk(A)["rev"], "count": 3}))
        case("v27 server: a changed NOTE alone makes nothing new to save: \"Already saved as ...\", and the Carousel folder is byte for byte as it was",
             code == 200 and out.get("already") is True and _tree(car_dir) == saved_tree, (code, out))

        # ---- B15: Open folder's answers, through the real route, with the no-windows switch (Finder is never opened) ----
        sys.path.insert(0, str(SCRIPTS))
        import this_computer
        app = this_computer.FILES_APP
        code, out = J(get_json(P, f"/open?kit={KQ}&sub=Carousel"))
        case("v27 server: Open folder on a carousel with a Carousel folder: her line, for this computer's file manager, no path",
             code == 200 and out == {"ok": True, "words": HERS["open_car"].replace("Finder", app)}, out)
        code, out = J(get_json(P, f"/open?kit={KQ}&sub=Stories"))
        case("v27 server: Open folder on the stories before any Save stories: the folder is not there, said so with why none (the page says her line)",
             code == 200 and out == {"ok": False, "why": "none", "words": "There's no Stories folder yet."}, out)
        import shutil
        moved = kit / "Carousel-away"
        shutil.move(str(car_dir), str(moved))
        try:
            code, out = J(get_json(P, f"/open?kit={KQ}&sub=Carousel"))
            case("v27 server: ... and on the carousel when its folder is not there: the same, why none",
                 code == 200 and out == {"ok": False, "why": "none", "words": "There's no Carousel folder yet."}, out)
        finally:
            shutil.move(str(moved), str(car_dir))
        code, out = J(get_json(P, f"/open?kit={KQ}&sub=Singles"))
        case("v27 server: the kit page's other folders keep their old not-yet line", code == 200 and out == {"ok": False, "why": "none", "words": "There's no Singles folder yet."}, out)
        code, _, data = ask(P, "GET", f"/open?kit={KQ}&sub=Carousel", headers={"Sec-Fetch-Site": "cross-site"})
        case("v27 server: another website cannot press Open folder (403)", code == 403, (code, data[:80]))

        # ---- B7c: the stories' starters carry the three collages ----
        code, ss = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        case("v27 server: the stories page is given fourteen layouts: her four, the three collages, her seven grids",
             code == 200 and [x["id"] for x in ss["starters"]] == V26_IDS + [c[0] for c in HERS_COLLAGES] + GRID_IDS, [x["id"] for x in ss.get("starters", [])])
        case("v27 server: the collages are given with her frames and nothing to fill from the queue", all("fill" not in x and [(b["x"], b["y"], b["w"], b["h"]) for b in x["template"]["blocks"]] == [tuple(f) for f in c[4]]
                                                                                                        for x, c in zip(ss["starters"][4:7], HERS_COLLAGES)))
        SID = ss["design"]["id"]
        for x, c in zip(ss["starters"][4:7], HERS_COLLAGES):
            tpl = json.loads(json.dumps(x["template"]))
            for i, b in enumerate(tpl["blocks"]):
                b["n"] = i + 1
            code, out = J(post(P, "/design", {"kit": kit_name, "kind": "stories", "design": SID, "stamp": STAMP, "base": disk(SID, sdesigns)["rev"], "page": "v27serverpage02", "state": tpl}))
            case(f"v27 server: {c[1]} with photos in every frame is a set of stories the Assistant takes (overlapping frames are fine)", code == 200 and out.get("ok"), (code, out))
        case("v27 server: nothing a page was given in this part names a folder on this computer", all(no_path(x, work)[0] for x in seen))
        case("v27 server: the photos were only ever read", _tree(kit / "Photos") == _tree(kit / "Photos"))

        # ---- B4c: the chat's side for a carousel: design.py note and fill ----
        check_fill_commands(case, work, env, kit, kit_name, run, A, get_json, P, KQ, post, J)
    finally:
        srv.stop()


def check_fill_commands(case, work, env, kit, kit_name, run, A, get_json, P, KQ, post, J):
    """design.py note / fill on a carousel (B4c), by command, against the same records the page server reads."""
    cdesigns = kit / ".kit" / "designs"

    def disk(did=A):
        return json.loads((cdesigns / f"{did}.json").read_text(encoding="utf-8"))

    # the design: slide 1 has photo 1; slides 2 and 3 are empty frames; a text box; then a frame across slides 2 and 3
    st = {"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, None, W, 0, W, 600), _frame(3, None, 2 * W, 0, W, 600), _text(4, 130, 628),
                                                    _frame(5, None, W + 300, 700, W, 600)]}
    code, out = J(post(P, "/design", {"kit": kit_name, "design": A, "stamp": get_json(P, f"/design-state?kit={KQ}")[1]["stamp"], "base": disk()["rev"], "page": "v27serverpage03", "state": st, "ask": "Open on the dunes, end on the two of them."}))
    case("v27 fill: (the design holds one photo, three empty frames, one across slides 2 and 3, a text box, and a note)", code == 200 and out.get("ok"), (code, out))
    rc, txt = run(env, "design.py", "note", kit_name)
    case("v27 fill: design.py note on a carousel: their note word for word, the DESIGN with its id, the frames in the page's order, each with its slide",
         rc == 0 and "THEIR NOTE (their words; follow it): Open on the dunes, end on the two of them." in txt and f"DESIGN: \"Dune day carousel 1\"  (--design {A})  3 slides" in txt
         and "FRAMES: 4 (3 empty)" in txt and re.search(r"\n\s+1\s+slide 1\s+.*has photo 1", txt) and re.search(r"\n\s+2\s+slide 2\s+wants a wide photo", txt)
         and re.search(r"\n\s+3\s+slides 2 to 3\s+wants a wide photo", txt) and re.search(r"\n\s+4\s+slide 3\s+wants a wide photo", txt)
         and "WORDS: 1 text box on these slides" in txt and f"THEN: design.py fill \"{kit_name}\" --photos N,N,N --design {A}" in txt, txt[-900:])
    case("v27 fill: ... and the note never names a story, nor the command a path", "stor" not in txt.lower() and no_path(txt, work)[0], txt[-300:])
    rc, txt = run(env, "design.py", "story-note", kit_name)
    case("v27 fill: story-note is still the stories' spelling (it reads the stories, not the carousel)", rc == 0 and "SET:" in txt and "stories" in txt and "Dune day carousel" not in txt, txt[-300:])
    before = (cdesigns / f"{A}.json").read_bytes()
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "4,7,9", "--design", A)
    d = disk()
    got = [b.get("n") for b in d["state"]["blocks"] if b.get("type") != "text"]
    case("v27 fill: fill puts the pick into the empty frames in the page's order (slide 2, then across 2 and 3, then slide 3); the text box and the note are as they were; counter + 1",
         rc == 0 and txt.startswith("FILLED:") and got == [1, 4, 9, 7] and d["state"]["blocks"][3] == st["blocks"][3] and d.get("ask") == "Open on the dunes, end on the two of them."
         and d["rev"] == json.loads(before)["rev"] + 1 and d.get("filled_by") == "assistant" and "from" not in d, (rc, txt[-300:], got))
    case("v27 fill: the design as it was before the pick is kept beside it, byte for byte; the words say what was done, with no path", (cdesigns / f"{A}.prev.json").read_bytes() == before and no_path(txt, work)[0], txt[-200:])
    case("v27 fill: the words that follow name the carousel, never a story, and show the page command for a carousel",
         "No words were added or changed." in txt and f"design.py open \"{kit_name}\" --design {A}" in txt and "stor" not in txt.lower(), txt[-300:])
    kept = (cdesigns / f"{A}.json").read_bytes()
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "4,7,9", "--design", A)
    case("v27 fill: the very same pick again answers SAME: and writes nothing", rc == 0 and txt.startswith("SAME:") and (cdesigns / f"{A}.json").read_bytes() == kept, txt[-200:])
    for what, args in (("a photo not on the sheet", ["--photos", "99"]), ("a photo given twice", ["--photos", "2,2", "--replace"]), ("more photos than frames", ["--photos", "2,3,5,6,8", "--replace"]),
                       ("every frame full (no --replace)", ["--photos", "2"]), ("a photo already in the design (no --replace)", ["--photos", "4,2"]), ("numbers that are not numbers", ["--photos", "a,b"]),
                       ("a design id this shoot has not", ["--photos", "2", "--design", "nosuchdesign1"])):
        rc, txt = run(env, "design.py", "fill", kit_name, *args)
        case(f"v27 fill: refused ({what}) in plain words with nothing written", rc != 0 and txt.startswith("STOP:") and "Nothing was changed." in txt + " Nothing was changed." and (cdesigns / f"{A}.json").read_bytes() == kept, txt[-200:])
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "2,3,5,6", "--replace", "--design", A)
    d = disk()
    case("v27 fill: --replace puts the pick into every frame in the page's order (slide 1, slide 2, across 2 and 3, slide 3)", rc == 0 and txt.startswith("FILLED:") and [b.get("n") for b in d["state"]["blocks"] if b.get("type") != "text"] == [2, 3, 6, 5], txt[-200:])
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "8,9", "--replace", "--design", A)
    d = disk()
    case("v27 fill: fewer photos than frames with --replace: the first frames take them, the rest are left as they were", rc == 0 and "2 frames left as they were" in txt and [b.get("n") for b in d["state"]["blocks"] if b.get("type") != "text"] == [8, 9, 6, 5], txt[-200:])
    rc, txt = run(env, "design.py", "show", kit_name)
    case("v27 fill: design.py show prints the carousel's note and how many frames are empty", rc == 0 and "note for the assistant: Open on the dunes, end on the two of them." in txt and "(0 empty)" in txt, txt[-400:])
    # a design with no frame at all: one slide for each photo
    code, out = J(post(P, "/design-new", {"kit": kit_name, "token": "v27newdes0001", "stamp": get_json(P, f"/design-state?kit={KQ}")[1]["stamp"], "state": {"slides": 1, "bg": "#ffffff", "blocks": []}}))
    B = out.get("design", {}).get("id")
    rc, txt = run(env, "design.py", "note", kit_name)
    case("v27 fill: with no --design, note takes the design changed (or asked about) last: the new empty one, and says it has no frames yet",
         rc == 0 and B and f"--design {B}" in txt and "FRAMES: none yet. fill makes one slide for each photo you pick" in txt and "This shoot has 2 designs." in txt, txt[-500:])
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "3,1", "--design", B)
    db = disk(B)
    case("v27 fill: on a design with nothing on it the pick becomes one slide for each photo, each filling its slide",
         rc == 0 and db["state"]["slides"] == 2 and [(b["n"], b["x"], b["w"], b["h"]) for b in db["state"]["blocks"]] == [(3, 0, W, H), (1, W, W, H)], (rc, txt[-200:]))
    code, out = J(post(P, "/design-new", {"kit": kit_name, "token": "v27newdes0002", "stamp": get_json(P, f"/design-state?kit={KQ}")[1]["stamp"], "state": {"slides": 10, "bg": "#ffffff", "blocks": []}}))
    C = out.get("design", {}).get("id")
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", ",".join(str(i) for i in range(1, 15)), "--design", C)
    case("v27 fill: ten blank slides and fourteen photos: past 20 slides is refused (a carousel holds 20), nothing written",
         rc != 0 and "STOP: a carousel holds up to 20 slides, and this one has 10" in txt and disk(C)["state"]["blocks"] == [], txt[-200:])
    code, out = J(post(P, "/design-asked", {"kit": kit_name, "kind": "carousel", "design": A}))
    rc, txt = run(env, "design.py", "note", kit_name)
    case("v27 fill: Copy pressed on the older design: note now takes that one", rc == 0 and f"--design {A}" in txt, txt[-300:])
    rc, txt = run(env, "design.py", "note", kit_name, "--kind", "stories")
    case("v27 fill: note --kind stories reads the stories (the same as story-note)", rc == 0 and "SET:" in txt, txt[-200:])
    rc, txt = run(env, "design.py", "fill", kit_name, "--photos", "2", "--design", A, "--kind", "stories")
    case("v27 fill: a carousel design named as a set of stories is refused", rc != 0 and "STOP:" in txt and "no set of stories with the id" in txt, txt[-200:])


# ---------------------------------------------------------------------------------------------------------------
# Part 3: the real page in a hidden Chrome
# ---------------------------------------------------------------------------------------------------------------

# Run in every page before its own scripts: what Copy copies (a hidden Chrome has no clipboard to read back).
COPY_JS = r"""
(function(){
  var copy = document.execCommand;
  document.execCommand = function(cmd){
    if (cmd === 'copy') { var a = document.activeElement; window.__copied = a && typeof a.value === 'string' ? a.value : null; return true; }
    return copy.apply(document, arguments);
  };
})();
"""


def check_v27_browser(case, work, port, make_kit, Server, post, get_json, run):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  v27 on the real page: no Chrome on this computer", flush=True)
        return
    target = work / "v27-browser"
    ok, out = make_kit(target, "Beach", 30)
    if not case("v27 browser: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio), STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none")
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    cdesigns, sdesigns = kit / ".kit" / "designs", kit / ".kit" / "story-designs"
    sys.path.insert(0, str(SCRIPTS))
    import this_computer
    app = this_computer.FILES_APP
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    try:
        with cd.Chrome(work=work / "chrome-v27", size=(1400, 1000)) as c:
            c.init_script(COPY_JS)

            def Jx(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return Jx("Designer.st")

            def did():
                return c.js("Designer.design.id")

            def disk(i=None, folder=cdesigns):
                return json.loads((folder / f"{i or did()}.json").read_text(encoding="utf-8"))

            def ready(seconds=40):
                c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def settled(seconds=12, folder=cdesigns):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                return disk(folder=folder)["state"] == st()

            def hidden(sel):
                return c.js(f"(function(){{ var e = document.querySelector('{sel}'); return !e || e.hidden || getComputedStyle(e).display === 'none'; }})()")

            def gallery_open():
                return c.js("!document.getElementById('gallery').hidden")

            def add(section, nth, wait=True):
                if not gallery_open():
                    c.click("#new-design")
                    c.wait_for("!document.getElementById('gallery').hidden", 5)
                c.click(f"#gallery-{section} .dz-card:nth-child({nth}) .dz-use")
                if wait:
                    c.wait_for("document.getElementById('gallery').hidden", 8)

            def frames(s):
                return [b for b in s["blocks"] if b.get("type") != "text"]

            # ================= the carousel's page =================
            c.open(f"{base}/design.html?kit={KQ}")
            ready()
            c.wait_for("Designer.save.idle()", 10)
            A = did()
            words = Jx("{ask: document.getElementById('ask-pick').textContent, box: document.getElementById('ask-box').hidden, exp: document.getElementById('ask-pick').getAttribute('aria-expanded'), "
                       "head: document.querySelector('#ask-box label b').textContent, sub: document.querySelector('#ask-box label').childNodes[1].textContent.trim(), "
                       "place: document.getElementById('ask-note').placeholder, then: document.querySelector('#ask-box p').textContent, line: document.getElementById('ask-words').textContent, "
                       "copy: document.getElementById('ask-copy').textContent, asked: !!Designer.ask, open: document.getElementById('open-carousel').textContent, openShown: !document.getElementById('open-wrap').hidden}")
            case("v27 browser: the carousel's page: her button beside the photos' heading, the box closed, her words for slides in it, the line for the carousel, Copy; Open folder is there before any save",
                 words == {"ask": HERS["ask_button"], "box": True, "exp": "false", "head": HERS["ask_head"], "sub": "Optional. " + HERS["ask_sub_car"], "place": HERS["ask_place_car"],
                           "then": HERS["ask_then_car"], "line": "Pick my carousel photos for Beach", "copy": "Copy", "asked": True, "open": "Open folder", "openShown": True}, words)
            # ---- the stage sticks to the top on the carousel page too (v26 proved stories): a shorter window, so the tray of 30 photos runs past it ----
            c.desktop((1400, 600))
            time.sleep(0.3)
            geo0 = Jx("(function(){ var s = document.getElementById('stage').getBoundingClientRect(); return {top: s.top, pos: getComputedStyle(document.getElementById('stage')).position, doc: document.documentElement.scrollHeight, win: innerHeight}; })()")
            c.js("window.scrollTo(0, 900)")
            time.sleep(0.3)
            geo1 = Jx("(function(){ var s = document.getElementById('stage').getBoundingClientRect(); return {top: s.top, y: scrollY, thumbs: document.getElementById('thumbs').getBoundingClientRect().top}; })()")
            case("v27 browser: the carousel's stage sticks to the top of the window while the photos scroll under it (30 photos, a 600 px window)",
                 geo0["pos"] == "sticky" and geo0["doc"] > geo0["win"] + 400 and geo1["y"] > geo0["top"] + 200 and abs(geo1["top"]) <= 1, (geo0, geo1))
            c.js("window.scrollTo(0, 0)")
            c.desktop()
            time.sleep(0.3)
            # ---- the [hidden] rule, as the browser computes it ----
            weak = Jx("Array.from(document.querySelectorAll('[hidden]')).filter(function(e){ return getComputedStyle(e).display !== 'none'; }).map(function(e){ return e.id || e.className; })")
            many = Jx("document.querySelectorAll('[hidden]').length")
            case("v27 browser: every element the page hides with the hidden attribute really disappears (computed display none), display:flex classes included", not weak and many >= 10, (weak, many))
            # ---- the ask box ----
            c.click("#ask-pick")
            box = Jx("{open: !document.getElementById('ask-box').hidden, exp: document.getElementById('ask-pick').getAttribute('aria-expanded'), focus: document.activeElement.id, "
                     "display: getComputedStyle(document.getElementById('ask-box')).display}")
            case("v27 browser: the button opens the box, says so, and puts the cursor in the note", box == {"open": True, "exp": "true", "focus": "ask-note", "display": "block"}, box)
            c.type_text("Open on the dunes")
            c.wait_for("document.getElementById('ask-words').textContent.indexOf('follow my note') > 0", 3)
            case("v27 browser: as soon as a note is typed the line gains \", and follow my note\"", c.text("#ask-words") == "Pick my carousel photos for Beach, and follow my note", c.text("#ask-words"))
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            d = disk()
            case("v27 browser: the note is in the stored carousel design after the autosave, beside the layout and never in it, with no Undo step made",
                 d.get("ask") == "Open on the dunes" and "ask" not in d["state"] and c.js("document.getElementById('undo').disabled") is True, (d.get("ask"), d["rev"]))
            c.click("#ask-copy")
            copied = c.js("window.__copied")
            case("v27 browser: Copy copies the whole line and says Copied for a moment", copied == "Pick my carousel photos for Beach, and follow my note" and c.text("#ask-copy") == "Copied", (copied, c.text("#ask-copy")))
            c.wait_for("document.getElementById('ask-copy').textContent === 'Copy'", 4)
            time.sleep(0.6)
            case("v27 browser: ... and told the Assistant which design was asked about (a time noted with it, nothing else changed)",
                 isinstance(disk().get("asked"), (int, float)) and disk()["state"] == d["state"] and disk()["rev"] == d["rev"], disk().get("asked"))
            # the assistant's pick lands on the open page by itself (B4c)
            c.click("#ask-note", count=3)
            c.key("Backspace")
            c.wait_for("document.getElementById('ask-words').textContent === 'Pick my carousel photos for Beach'", 3)
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            case("v27 browser: the note emptied: the line loses \", and follow my note\", and the record has no note", "ask" not in disk(), disk().get("ask"))
            c.type_text("End on the two of them")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            c.js("document.getElementById('ask-note').blur()")
            # empty two frames so there is something to fill
            s0 = st()
            fr = frames(s0)
            s1 = json.loads(json.dumps(s0))
            for b in frames(s1)[1:3]:
                b.update(n=None)
            c.js("Designer.setState(" + json.dumps(s1) + ")")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            case("v27 browser: (two frames emptied on the page and saved)", [b.get("n") for b in frames(disk()["state"])][1:3] == [None, None])
            rc, txt = run(env, "design.py", "note", kit_name)
            case("v27 browser: design.py note reads the design the page asked about, with their note and the two empty frames", rc == 0 and f"--design {A}" in txt and "End on the two of them" in txt and "(2 empty)" in txt, txt[-400:])
            free = [n for n in range(1, 31) if n not in {b.get("n") for b in frames(disk()["state"])}][:2]
            rc, txt = run(env, "design.py", "fill", kit_name, "--photos", ",".join(str(n) for n in free), "--design", A)
            case("v27 browser: (the assistant's pick went in from the chat)", rc == 0 and txt.startswith("FILLED:"), txt[-200:])
            c.js("Designer.ask.look()")
            c.wait_for(f"Designer.st.blocks.filter(function(b){{ return b.type !== 'text'; }})[1].n === {free[0]}", 8)
            case("v27 browser: the open page takes the pick by itself: the two frames show the photos and the page says so",
                 [b.get("n") for b in frames(st())][1:3] == free and c.text("#ask-said") == "Your assistant’s pick is in your slides.", (frames(st())[1:3], c.text("#ask-said")))
            # ---- Open folder on the carousel page (B15), through the real route, Finder never opened ----
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            case("v27 browser: Open folder before any Save slides: her not-yet line, right over the button", c.text("#open-line") == HERS["none_car"], c.text("#open-line"))
            ob = c.rect("#open-carousel")
            c.js("document.getElementById('g-bg').querySelector('.sw[data-c=\"#111111\"]').click()")
            case("v27 browser: a change takes the answer away and leaves the button where it is", c.text("#open-line") == "" and not hidden("#open-wrap") and c.rect("#open-carousel") == ob, c.rect("#open-carousel"))
            (kit / "Carousel").mkdir(exist_ok=True)
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            case("v27 browser: with a Carousel folder there: her line, for this computer's file manager (nothing opened: the no-windows switch)",
                 c.text("#open-line") == HERS["open_car"].replace("Finder", app), c.text("#open-line"))

            # ================= slides as things on the carousel (B8, B9, B10) =================
            def four_state(top=0):
                return {"slides": 4, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, W, w=2 * W), _frame(3, 3, 3 * W + 50, 50, 400, 400), _text(4, 3 * W + 100, 800)]}

            def put(state):
                c.js("Designer.select(null); Designer.setState(" + json.dumps(state) + ")")
                c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)

            def labels():
                return Jx("Array.from(document.querySelectorAll('#labels .lab')).map(function(l){ var g = l.querySelector('.slab'), p = l.querySelector('.labp'), x = l.querySelector('.labx'); "
                          "return [g.textContent, g.title, p.title, p.getAttribute('aria-label'), x.title, !x.hidden && getComputedStyle(x).display !== 'none']; })")

            def xs():
                return [[b["id"], b["x"]] for b in st()["blocks"]]

            def slides_line():
                return c.text("#slides-line")

            def sel_line():
                return c.text("#selline")

            put(four_state())
            rev0 = disk()["rev"]
            lab = labels()
            case("v27 browser: every slide's label is a grip with the slide's name, a + named for the slide it adds after, and an x named for the slide it removes, all shown (four slides)",
                 lab == [[f"Slide {k}", "Drag to move this slide", f"Add a slide after slide {k}", f"Add a slide after slide {k}", f"Remove slide {k}", True] for k in (1, 2, 3, 4)], lab)
            glyph = c.js("getComputedStyle(document.querySelector('#labels .slab'), '::before').content")
            case("v27 browser: the grip glyph is drawn before the name by the page's styles (⠿), not as words", "\u283f" in glyph, glyph)
            c.click("#labels .lab:nth-child(1) .labp")
            case("v27 browser: + on slide 1's label: a blank slide 2, everything from there one slide along, and her line",
                 st()["slides"] == 5 and xs() == [[1, 0], [2, 2 * W], [3, 4 * W + 50], [4, 4 * W + 100]] and slides_line() == "Added a blank slide as slide 2. Drag a photo onto it. Undo takes it out.", (xs(), slides_line()))
            case("v27 browser: ... saved as one more change (rev + 1), nothing selected", settled() and disk()["rev"] == rev0 + 1 and c.js("Designer.sel") is None, disk()["rev"])
            c.click("#undo")
            case("v27 browser: Undo takes the blank slide out", st() == four_state(), st()["slides"])
            c.click("#labels .lab:nth-child(2) .labp")
            case("v27 browser: + on slide 2's label, where a photo stretches across the spot: refused with her line, nothing changed",
                 st() == four_state() and slides_line() == "A photo stretches across that spot. Move it first, or add the slide somewhere else.", slides_line())
            c.click("#labels .lab:nth-child(2) .labx")
            case("v27 browser: x on slide 2's label: the slide and the photo across 2 and 3 go, slide 4's things move up, her line",
                 st()["slides"] == 3 and xs() == [[1, 0], [3, 2 * W + 50], [4, 2 * W + 100]] and slides_line() == "Removed slide 2. Undo brings it back.", (xs(), slides_line()))
            c.click("#undo")
            case("v27 browser: Undo brings it back", st() == four_state())
            # the three buttons for the slide the selected thing is on
            c.click("#strip .blk[data-id='1']")
            grp = Jx("(function(){ var g = document.getElementById('sel-slides'); return {shown: !g.hidden, btns: Array.from(g.querySelectorAll('button')).map(function(b){ return [b.textContent, b.title, b.disabled]; }), "
                     "line: document.getElementById('only-slide').hidden, after: g.nextElementSibling && g.nextElementSibling.id}; })()")
            case("v27 browser: a photo selected: Add a slide before, Add a slide after, Remove this slide, with her tooltips, right before the group for anything (hers), after the text's groups",
                 grp == {"shown": True, "btns": [[HERS["before"], HERS["before_title"], False], [HERS["after"], HERS["after_title"], False], [HERS["remove_this"], HERS["remove_title"], False]], "line": True, "after": "sel-all"}, grp)
            order = Jx("Array.from(document.getElementById('selrows').children).map(function(g){ return g.id; })")
            case("v27 browser: the bar's groups run Selected photo, Crop, Text, Color, style, the slide's, then the rest (so a text box gets the slide's buttons after its own)",
                 order == ["sel-photo", "sel-crop", "sel-text", "sel-color", "sel-style", "sel-slides", "sel-all"], order)
            c.click("#sel-slides [data-a=slidebefore]")
            case("v27 browser: Add a slide before (slide 1): a blank slide 1, and the line beside the buttons", st()["slides"] == 5 and xs() == [[1, W], [2, 2 * W], [3, 4 * W + 50], [4, 4 * W + 100]]
                 and sel_line() == "Added a blank slide as slide 1. Drag a photo onto it. Undo takes it out.", (xs(), sel_line()))
            c.click("#undo")
            c.click("#strip .blk[data-id='3']")
            c.click("#sel-slides [data-a=slideafter]")
            case("v27 browser: Add a slide after (slide 4, the small photo's): a blank slide 5 at the end", st()["slides"] == 5 and xs() == [[1, 0], [2, W], [3, 3 * W + 50], [4, 3 * W + 100]]
                 and sel_line() == "Added a blank slide as slide 5. Drag a photo onto it. Undo takes it out.", (xs(), sel_line()))
            c.click("#undo")
            c.click("#strip .blk[data-id='4']")
            c.click("#sel-slides [data-a=delstory]")
            case("v27 browser: Remove this slide with the text box selected (slide 4): the slide, its photo and the text go", st()["slides"] == 3 and xs() == [[1, 0], [2, W]]
                 and sel_line() == "Removed slide 4. Undo brings it back.", (xs(), sel_line()))
            c.click("#undo")
            case("v27 browser: ... Undo, and the design is as it was and saved so", st() == four_state() and settled())
            # the most, and the fewest
            put({"slides": 20, "bg": "#ffffff", "blocks": [_frame(1, 1, 0)]})
            c.click("#labels .lab:nth-child(20) .labp")
            case("v27 browser: at 20 slides + is refused with her line", st()["slides"] == 20 and slides_line() == "That's the most Instagram allows (20 slides). Remove one first.", slides_line())
            put({"slides": 1, "bg": "#ffffff", "blocks": [_frame(1, 1, 0)]})
            c.click("#strip .blk[data-id='1']")
            one = Jx("{x: Array.from(document.querySelectorAll('#labels .labx')).filter(function(x){ return !x.hidden; }).length, off: document.querySelector('#sel-slides [data-a=delstory]').disabled, "
                     "line: document.getElementById('only-slide').hidden ? '' : document.getElementById('only-slide').textContent, plus: !document.querySelector('#labels .labp').disabled}")
            case("v27 browser: at one slide: no x on the label, Remove this slide off with our line beside it, + still there", one == {"x": 0, "off": True, "line": "It’s your only slide, so it stays.", "plus": True}, one)
            # ---- Where should it go? (B9) ----
            c.js(f"Designer.load('{A}')")          # the design opened afresh: no slide clicked in it yet (a click earlier in this test would count, as hers)
            c.wait_for("Designer.save.idle()", 10)
            put(four_state())
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            row = Jx("{hidden: document.getElementById('tpl-where').hidden, display: getComputedStyle(document.getElementById('tpl-where')).display, sub: document.getElementById('gallery-sub').textContent}")
            case("v27 browser: + Add slides with no slide clicked yet: the row is hidden (really: display none) and her v27 line says how to put it somewhere else",
                 row == {"hidden": True, "display": "none", "sub": HERS["add_sub"]}, row)
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            sr = c.rect("#strip")
            c.click((sr["x"] + 3.5 * sr["w"] / 4, sr["y"] + sr["h"] * 0.5))      # a bare spot on slide 4
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            row = Jx("{hidden: document.getElementById('tpl-where').hidden, display: getComputedStyle(document.getElementById('tpl-where')).display, sub: document.getElementById('gallery-sub').textContent, "
                     "head: document.querySelector('#tpl-where b').textContent, words: Array.from(document.querySelectorAll('#tpl-where label')).map(function(l){ return l.textContent.trim(); }), "
                     "checked: document.querySelector('#tpl-where input:checked').value}")
            case("v27 browser: slide 4 clicked, then + Add slides: Where should it go? Before slide 4 / After slide 4 / At the end, After ticked, and her line",
                 row == {"hidden": False, "display": "flex", "sub": HERS["where_sub"], "head": HERS["where"], "words": ["Before slide 4", "After slide 4", "At the end"], "checked": "after"}, row)
            c.click("#tplw-before")
            add("fresh", 1)                      # Blank slide
            case("v27 browser: Blank slide added Before slide 4: it is slide 4, the small photo and the text move to slide 5, and the page is scrolled to it",
                 st()["slides"] == 5 and xs() == [[1, 0], [2, W], [3, 4 * W + 50], [4, 4 * W + 100]] and slides_line() == "", (xs(), slides_line()))
            case("v27 browser: ... saved", settled())
            c.click("#undo")
            c.click("#strip .blk[data-id='2']")       # the photo across 2 and 3: its middle is on slide 3
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            words = Jx("Array.from(document.querySelectorAll('#tpl-where label')).map(function(l){ return l.textContent.trim(); })")
            case("v27 browser: the photo across slides 2 and 3 selected: the row is about slide 3", words == ["Before slide 3", "After slide 3", "At the end"], words)
            c.click("#tplw-before")
            add("fresh", 1)
            case("v27 browser: Blank slide Before slide 3, where the photo stretches across: it goes at the end instead, and her line says so",
                 st()["slides"] == 5 and xs() == [[1, 0], [2, W], [3, 3 * W + 50], [4, 3 * W + 100]] and slides_line() == HERS["across_end"], (xs(), slides_line()))
            c.click("#undo")
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            row = Jx("{hidden: document.getElementById('tpl-where').hidden, display: getComputedStyle(document.getElementById('tpl-where')).display, h: document.querySelector('#gallery h2').textContent}")
            case("v27 browser: + New design never shows the row (her bug, impossible here)", row == {"hidden": True, "display": "none", "h": "New design"}, row)
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            put({"slides": 18, "bg": "#ffffff", "blocks": [_frame(1, 1, 0)]})
            c.click((sr["x"] + 10, sr["y"] + 10))
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            add("fresh", 2, wait=False)          # One photo per slide: five slides
            time.sleep(0.3)
            case("v27 browser: 18 slides and a five-slide pick: refused whole with her numbers, the window stays, nothing changed",
                 c.js("!document.getElementById('gallery').hidden") and c.text("#gallery-line") == "That adds 5 slides, and Instagram allows 20. You have 18. Remove some first, or pick something smaller." and st()["slides"] == 18, c.text("#gallery-line"))
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            put({"slides": 1, "bg": "#ffffff", "blocks": [_frame(1, 1, 0)]})
            c.click((sr["x"] + 10, sr["y"] + 10))
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            case("v27 browser: on a one-slide design the row is not shown (hers)", c.js("document.getElementById('tpl-where').hidden") is True)
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            # another design opened: no stale number
            put(four_state())
            c.click((sr["x"] + 3.5 * sr["w"] / 4, sr["y"] + sr["h"] * 0.5))
            c.click("#dup-design")
            c.wait_for(f"Designer.design && Designer.design.id !== '{A}' && Designer.save.idle()", 15)
            A2 = did()
            c.click("#add-slides")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            case("v27 browser: the copy opened (Duplicate design) with no slide clicked in it yet: the row is hidden, though slide 4 was clicked in the design before", st()["slides"] == 4 and c.js("document.getElementById('tpl-where').hidden") is True)
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            # ---- drag a slide by its grip (B10) ----
            put(four_state())
            rev1 = disk()["rev"]
            lr = c.rect("#labels .lab:nth-child(1) .slab")
            sr = c.rect("#strip")
            c.drag("#labels .lab:nth-child(1) .slab", (sr["right"] - 8, lr["cy"]), steps=16, release=False)
            drag = Jx("(function(){ var d = document.querySelector('.slidedim'), l = document.querySelector('.dropline'), s = document.getElementById('strip').getBoundingClientRect(); "
                      "return {dim: !!d, dimLeft: d && Math.round(d.getBoundingClientRect().left - s.left), dimW: d && Math.round(d.getBoundingClientRect().width), line: !!l && !l.hidden, "
                      "lineAt: l && Math.round(l.getBoundingClientRect().left + 2 - s.left), stripW: Math.round(s.width), grabbing: document.querySelector('#labels .slab').classList.contains('dragging'), "
                      "color: l && getComputedStyle(l).backgroundColor, same: JSON.stringify(Designer.st)}; })()")
            case("v27 browser: while slide 1's grip is dragged to the end: slide 1 dimmed in coral, a coral line at the strip's end, the layout untouched so far",
                 drag["dim"] and drag["dimLeft"] == 0 and abs(drag["dimW"] - drag["stripW"] / 4) <= 2 and drag["line"] and abs(drag["lineAt"] - drag["stripW"]) <= 3 and drag["grabbing"]
                 and drag["color"] == "rgb(212, 100, 63)" and json.loads(drag["same"]) == four_state(), drag)
            c.mouse_release()
            case("v27 browser: let go: slide 1 is last, the other three moved up (the two that share a photo together), her line, nothing selected",
                 st()["slides"] == 4 and xs() == [[1, 3 * W], [2, 0], [3, 2 * W + 50], [4, 2 * W + 100]] and slides_line() == "Moved slide 1. Undo moves it back." and c.js("Designer.sel") is None
                 and c.count(".slidedim") == 0 and c.count(".dropline") == 0, (xs(), slides_line()))
            case("v27 browser: ... saved as one change (rev + 1)", settled() and disk()["rev"] == rev1 + 1, disk()["rev"])
            c.click("#undo")
            case("v27 browser: Undo moves it back", st() == four_state())
            lr2 = c.rect("#labels .lab:nth-child(2) .slab")
            c.drag("#labels .lab:nth-child(2) .slab", (sr["x"] + 4, lr2["cy"]), steps=16)
            case("v27 browser: slide 2's grip dragged to the start: slides 2 and 3 move together (they share a photo), slide 1 after them, her line",
                 xs() == [[1, 2 * W], [2, 0], [3, 3 * W + 50], [4, 3 * W + 100]] and slides_line() == "Moved 2 slides (they share a photo). Undo moves it back.", (xs(), slides_line()))
            c.click("#undo")
            c.drag("#labels .lab:nth-child(1) .slab", (sr["right"] - 8, lr["cy"]), steps=16, release=False)
            c.key("Escape")
            c.mouse_release()
            case("v27 browser: Escape in the middle of a drag: the layout as it was, nothing dimmed, no line, no words",
                 st() == four_state() and c.count(".slidedim") == 0 and c.count(".dropline") == 0 and slides_line() == "" and not c.js("document.querySelector('#labels .slab').classList.contains('dragging')"), xs())
            c.drag("#labels .lab:nth-child(1) .labp", (sr["right"] - 8, lr["cy"]), steps=10)
            case("v27 browser: a press on a label's + that is dragged away starts no slide drag and adds no slide", st() == four_state() and c.count(".slidedim") == 0, xs())
            c.drag("#labels .lab:nth-child(1) .slab", (lr["cx"] + 3, lr["cy"] + 1), steps=3)
            case("v27 browser: a press on the grip that barely moves is not a drag: nothing changes", st() == four_state() and slides_line() == "")
            case("v27 browser: nothing went wrong on the page through all of that", not c.page_errors(), c.page_errors()[:3])

            # ================= the photo inside its frame (B12, B11) =================
            put(four_state())
            rev2 = disk()["rev"]
            c.click("#strip .blk[data-id='1']")
            grp = Jx("(function(){ var g = document.getElementById('sel-crop'); return {shown: !g.hidden, btns: Array.from(g.querySelectorAll('button')).map(function(b){ return [b.textContent, b.title, b.disabled]; })}; })()")
            case("v27 browser: a photo selected: the Crop group runs Show the whole photo (her tooltip), Move photo inside, the empty-frame button, none off",
                 grp["shown"] and grp["btns"][0] == [HERS["whole"], HERS["whole_title"], False] and grp["btns"][1][0] == "Move photo inside" and not any(b[2] for b in grp["btns"]), grp)
            nat = Jx("(function(){ var b = Designer.selected(), n = Designer.blockTypes.photo.natural(document.querySelector('#strip .blk[data-id=\"1\"]'), b); return n; })()")
            want = Jx("DesignModel.act(Designer.st, 1, 'whole', {pw: " + str(nat["w"]) + ", ph: " + str(nat["h"]) + "}).st")
            c.click("#whole-photo")
            case("v27 browser: Show the whole photo: the frame shrinks to the photo's own shape inside its slide, centred, the crop back to the middle; her line beside the buttons",
                 st() == want and st()["blocks"][0]["zoom"] == 1 and st()["blocks"][0]["w"] * nat["h"] - st()["blocks"][0]["h"] * nat["w"] < 2 and st()["blocks"][0] != four_state()["blocks"][0]
                 and sel_line() == HERS["whole_done"], (st()["blocks"][0], nat, sel_line()))
            img = Jx("(function(){ var i = document.querySelector('#strip .blk[data-id=\"1\"] img'), n = i.parentNode; return {iw: i.offsetWidth, ih: i.offsetHeight, l: i.offsetLeft, t: i.offsetTop, fw: n.offsetWidth, fh: n.offsetHeight}; })()")
            case("v27 browser: ... and the whole picture is drawn inside the frame, filling it exactly", abs(img["iw"] - img["fw"]) <= 1 and abs(img["ih"] - img["fh"]) <= 1 and abs(img["l"]) <= 1 and abs(img["t"]) <= 1, img)
            case("v27 browser: ... saved as one change (rev + 1), the photo still selected", settled() and disk()["rev"] == rev2 + 1 and c.js("Designer.sel") == 1, disk()["rev"])
            c.click("#undo")
            case("v27 browser: Undo puts the crop back", st() == four_state())
            c.click("#strip .blk[data-id='4']")
            case("v27 browser: with a text box selected the Crop group is not shown at all", c.js("document.getElementById('sel-crop').hidden") is True)
            c.js("Designer.select(null); Designer.setState(" + json.dumps({"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, None, W, 100, 600, 600)]}) + ")")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            c.click("#strip .blk[data-id='2']")
            case("v27 browser: an empty frame selected: Show the whole photo is off, like Move photo inside", c.js("document.getElementById('whole-photo').disabled && document.getElementById('adjust').disabled") is True)
            case("v27 browser: nothing went wrong on the page through the photo's buttons", not c.page_errors(), c.page_errors()[:3])

            # ================= the stories page =================
            c.open(f"{base}/design.html?kit={KQ}&kind=stories")
            ready()
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            S = did()
            names = Jx("Array.from(document.querySelectorAll('#gallery-starters .dz-cap b')).map(function(x){ return x.textContent; })")
            subs = Jx("Array.from(document.querySelectorAll('#gallery-starters .dz-cap small')).map(function(x){ return x.textContent; })")
            case("v27 browser: Add stories: her four templates, then Playful mosaic, Mood board and Overlapping collage, then her seven grids",
                 names[4:7] == [c_[1] for c_ in HERS_COLLAGES] and len(names) == 14 and names[7:] == ["One photo", "Two up", "Three strips", "Four", "Six", "Nine", "Twelve"], names)
            case("v27 browser: ... each collage says one story and how many photos", subs[4:7] == ["1 story · 7 photos", "1 story · 6 photos", "1 story · 6 photos"], subs[4:7])
            words = Jx("{sub: document.querySelector('#ask-box label').childNodes[1].textContent.trim(), line: document.getElementById('ask-words').textContent, open: document.getElementById('open-carousel').textContent, "
                       "openShown: !document.getElementById('open-wrap').hidden}")
            case("v27 browser: the stories page keeps its own ask words and has Open folder from the start",
                 words == {"sub": "Optional. " + HERS["ask_sub_story"], "line": "Pick my story photos for Beach", "open": "Open folder", "openShown": True}, words)
            add("starters", 5)              # Playful mosaic, with the fill tick on
            s1 = st()
            case("v27 browser: Playful mosaic added with the tick on: one story, her seven frames, each with a photo of this shoot, none twice, on the set's own background",
                 s1["slides"] == 1 and [(b["x"], b["y"], b["w"], b["h"]) for b in frames(s1)] == [tuple(f) for f in HERS_COLLAGES[0][4]] and all(b["n"] for b in frames(s1))
                 and len({b["n"] for b in frames(s1)}) == 7 and s1["bg"] == "#ffffff", (s1["slides"], s1["bg"]))
            case("v27 browser: the set saves itself as always", settled(folder=sdesigns))
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            c.js("var t = document.getElementById('gallery-fill'); if (t.checked) t.click();")
            add("starters", 6)              # Mood board, tick off
            s2 = st()
            case("v27 browser: Mood board added after it with the tick off: a second story with her six frames, all empty", s2["slides"] == 2 and len(frames(s2)) == 13
                 and [(b["x"] - SW, b["y"], b["w"], b["h"]) for b in frames(s2)[7:]] == [tuple(f) for f in HERS_COLLAGES[1][4]] and all(b["n"] is None for b in frames(s2)[7:]), s2["slides"])
            add("starters", 7)              # Overlapping collage
            s3 = st()
            case("v27 browser: Overlapping collage after those: three stories, her six frames on the third", s3["slides"] == 3
                 and [(b["x"] - 2 * SW, b["y"], b["w"], b["h"]) for b in frames(s3)[13:]] == [tuple(f) for f in HERS_COLLAGES[2][4]], s3["slides"])
            case("v27 browser: every frame of the three collages is drawn on the strip", c.count("#strip .blk") >= 19, c.count("#strip .blk"))
            case("v27 browser: the set saves itself with the three", settled(folder=sdesigns))
            c.click("#open-carousel")
            c.wait_for("document.getElementById('open-line').textContent !== ''", 5)
            case("v27 browser: Open folder on the stories before any Save stories: her not-yet line, naming Save stories", c.text("#open-line") == HERS["none_story"], c.text("#open-line"))
            weak = Jx("Array.from(document.querySelectorAll('[hidden]')).filter(function(e){ return getComputedStyle(e).display !== 'none'; }).map(function(e){ return e.id || e.className; })")
            case("v27 browser: on the stories page too, every hidden element is really gone", not weak, weak)
            # ---- slides as things, in a story's words (B8, B9, B10) ----
            def sfour():
                return {"slides": 4, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, h=SH), _frame(2, 2, SW, w=2 * SW, h=SH), _frame(3, 3, 3 * SW + 50, 50, 400, 400), _text(4, 3 * SW + 100, 800)]}
            c.js("Designer.select(null); Designer.setState(" + json.dumps(sfour()) + ")")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            lab = Jx("Array.from(document.querySelectorAll('#labels .lab')).map(function(l){ var g = l.querySelector('.slab'), p = l.querySelector('.labp'), x = l.querySelector('.labx'); return [g.textContent, g.title, p.title, x.title]; })")
            case("v27 browser: a story's labels say story: the grip, the + and the x", lab == [[f"Story {k}", "Drag to move this story", f"Add a story after story {k}", f"Remove story {k}"] for k in (1, 2, 3, 4)], lab)
            c.click("#strip .blk[data-id='1']")
            grp = Jx("Array.from(document.querySelectorAll('#sel-slides button')).map(function(b){ return [b.textContent, b.title]; })")
            case("v27 browser: the three buttons in her story names, with the tooltips in story words (ours: hers still say slide)",
                 grp == [[HERS["before_story"], "Put a new blank story in front of the one this is on"], [HERS["after_story"], "Put a new blank story right after the one this is on"], [HERS["remove_story"], "Take out the story this is on, and everything on it"]], grp)
            c.click("#sel-slides [data-a=slideafter]")
            case("v27 browser: Add a story after story 1: a blank story 2, her line in story words", st()["slides"] == 5 and c.text("#selline") == "Added a blank story as story 2. Drag a photo onto it. Undo takes it out.", c.text("#selline"))
            c.click("#undo")
            c.click("#labels .lab:nth-child(2) .labp")
            case("v27 browser: + where a photo stretches across, in story words", c.text("#slides-line") == "A photo stretches across that spot. Move it first, or add the story somewhere else.", c.text("#slides-line"))
            c.click("#strip .blk[data-id='2']")
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            row = Jx("{sub: document.getElementById('gallery-sub').textContent, words: Array.from(document.querySelectorAll('#tpl-where label')).map(function(l){ return l.textContent.trim(); }), hidden: document.getElementById('tpl-where').hidden}")
            case("v27 browser: Add stories with the photo across 2 and 3 selected: Before story 3 / After story 3 / At the end, and her line", row == {"sub": HERS["where_sub"], "words": ["Before story 3", "After story 3", "At the end"], "hidden": False}, row)
            c.click("#gallery-close")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            lr = c.rect("#labels .lab:nth-child(2) .slab")
            sr = c.rect("#strip")
            c.drag("#labels .lab:nth-child(2) .slab", (sr["x"] + 4, lr["cy"]), steps=16)
            case("v27 browser: stories 2 and 3 dragged to the start together, in story words", [[b["id"], b["x"]] for b in st()["blocks"]] == [[1, 2 * SW], [2, 0], [3, 3 * SW + 50], [4, 3 * SW + 100]]
                 and c.text("#slides-line") == "Moved 2 stories (they share a photo). Undo moves it back.", c.text("#slides-line"))
            c.js("Designer.select(null); Designer.setState(" + json.dumps({"slides": 40, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, h=SH)]}) + ")")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            c.click("#labels .lab:nth-child(40) .labp")
            case("v27 browser: at 40 stories + is refused with the stories' number", c.text("#slides-line") == "That's the most Instagram allows (40 stories). Remove one first.", c.text("#slides-line"))
            case("v27 browser: nothing went wrong on the stories page", not c.page_errors(), c.page_errors()[:3])
    finally:
        srv.stop()


def main():
    """By itself (GitHub's Mac page job, or by hand): the three parts, on a work folder under /private/tmp."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9680)
    ap.add_argument("--no-chrome", action="store_true", help="the tables, words, rules, routes and commands only; the real page is not opened")
    ap.add_argument("--only", choices=["page", "server", "browser"], help="one part by itself")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / "tests"))
    import design_check as dc
    work = Path(a.work).resolve()
    if dc.SAFE not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    if set(range(a.port, a.port + 10)) & dc.NEVER_PORTS:
        print("STOP: that port range reaches one the real pages use.")
        return 2
    work = work / time.strftime("run-%H%M%S")
    work.mkdir(parents=True)
    os.environ["STUDIO_HOME"] = str(work / "no-studio")         # nothing here may ever look at the real ~/.studio
    if a.only in (None, "page"):
        check_v27_page(dc.case, work)
    try:
        import PIL  # noqa: F401
        jpeg = dc.jpeg
    except ImportError:
        import design_v26_check
        jpeg = design_v26_check.plain_jpeg(work)
    if a.only not in (None, "server"):
        pass
    elif jpeg is None:
        print("SKIP  v27's routes and commands: no Pillow under this Python and no sips on this computer to draw the test's slides", flush=True)
    else:
        try:
            check_v27_server(dc.case, work, a.port, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.ask, dc.run, jpeg)
        except Exception as e:  # noqa: BLE001
            import traceback
            dc.case("the checks of v27's routes and commands ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    if not a.no_chrome and a.only in (None, "browser"):
        try:
            check_v27_browser(dc.case, work, a.port + 2, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.run)
        except Exception as e:  # noqa: BLE001
            import traceback
            dc.case("the real-browser checks of v27 ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    bad = [n for n, ok in dc.results if not ok]
    print()
    print(f"{len(dc.results)} cases, {len(dc.results) - len(bad)} passed, {len(bad)} failed.  Work folder: {work}")
    for n in bad:
        print("  FAILED: " + n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
