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
    the photo inside its frame Show the whole photo (B12): the frame shrinks to the photo's own shape inside its space, never under 60 px;
                               Crop (B11): the window with the whole photo and a box, the corners keeping the frame's shape, eight
                               handles when unticked and the frame taking the box's shape, Done mapped onto zoom and crop up to 25
    several photos at once     (B13) Shift-, Cmd- or Ctrl-click to select several, the bar inside the stage ("3 selected", Even them
                               out, Same size, Line up tops, Remove them, Done, her hint), a drag of any moving them all (kept on the
                               strip), Backspace and Escape; the rules by themselves (evenOut's columns, sameSize's reference, ...)
    see a photo big            (B14) a tray tile's ⤢ or a double-click opens the dark window, ‹ › and the arrow keys browse round,
                               Use this photo / Put it in the selected frame, Close, Escape; a single click puts the photo in only
                               after 230 ms; the picture by number, never a path
    save just this slide       (B17) "Save just this slide" in the slide's group and "Save just slide N" beside Save slides: one slide
                               drawn by the same painter and put beside the design's newest set as "<set> - slide 03 updated.jpg"
                               (then "updated 2"), through the same staging, record and commit; a file of theirs under that name
                               never taken for the slide; nothing in kit.json, no line for the chat; her saved and Stopped lines
    + Add photos               (B16) the Photos folder opened through the Assistant, her lines in this computer's words, and photos
                               dropped in joining the END of the tray with the next numbers (POST /design-photos, the one writer),
                               every design's frames and counter untouched; a photo gone still asks for a Reload
    the path at the top        (B21) Home › <shoot> post kit › Carousel | Stories by look.crumbs, her Back pills hidden

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
import html
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
    # Crop (B11): the button and its tooltip (her HTML line 306), the window's words (404-410) and its line (1212)
    "crop": "Crop",
    "crop_title": "See the whole photo and drag the edges to crop it",
    "crop_hint": "Drag a corner to cut off the edges you don't want, and drag inside the box to move it. Only what's inside the box shows on your slide.",
    "crop_lock": "Keep the frame's shape",
    "crop_cancel": "Cancel", "crop_done": "Done",
    "crop_lock_hint": "Untick Keep the frame's shape to crop each side on its own. The frame on your slide changes shape to match.",
    "cropped": "Cropped. Undo takes it back.",
    # several photos at once (B13): her bar (her HTML line 343) and its lines (her page line 1064)
    "even": "Even them out", "even_title": "Lay them out tidily on their slide, every photo whole",
    "same": "Same size", "same_title": "Make them the same width as the last one you clicked",
    "tops": "Line up tops", "remove_them": "Remove them", "done": "Done",
    "many_hint": "Shift-click a photo to add it or take it out. Drag any of them to move them all.",
    "evened": "Evened out, every photo whole. Undo puts them back.",
    "samed": "Same size. Undo puts them back.",
    "lined": "Lined up. Undo puts them back.",
    "removed_them": "Removed. Undo brings them back.",
    # + Add photos (B16): the button and its tooltip (her HTML line 352) and its three lines (her page 1094-1099)
    "add_photos": "+ Add photos", "add_title": "Opens this shoot's Photos folder in Finder",
    "add_opening": "Opening your Photos folder in Finder...",
    "add_open": "Your Photos folder is open in Finder. Drag your finished photos in, and they show up here at the end.",
    "add_cant": "Could not open the folder. Is the photo drive plugged in?",
    # the path at the top (B21): her crumbs.js words (Home, "<shoot> post kit", Carousel, Stories), through look.CRUMB_WORDS and this page's own two
    "crumb_home": "Home", "crumb_carousel": "Carousel", "crumb_stories": "Stories",
    # Save just this slide (B17): the two buttons and their tooltips (her HTML lines 292 and 337), her stories' name (435)
    "save_one": "Save just this slide", "save_one_story": "Save just this story",
    "save_one_title": "Save only the slide this is on, as its own picture",
    "save_one_top_title": "Save only the slide you clicked",
    # See a photo big (B14): the tile's button (her page line 1783) and her window (her HTML 395-401, her page 1757-1759)
    "bigger": "See it bigger", "view_prev": "Previous photo", "view_next": "Next photo", "view_label": "Photo, bigger",
    "view_used": "already in this design", "view_use": "Use this photo", "view_put": "Put it in the selected frame", "view_close": "Close",
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
    # Save just this slide (B17): the top button's two labels, the line with no slide to mean, the making line, her Stopped line
    "save_one_any": ("`Save just one ${u}`", "Save just one slide", "Save just one story"),
    "save_one_n": ("`Save just ${u} ${si + 1}`", "Save just slide 3", "Save just story 3"),
    "click_first": ("`Click the ${UNIT.toLowerCase()} you want to save first, then press this.`", "Click the slide you want to save first, then press this.", "Click the story you want to save first, then press this."),
    "making_one": ("`Making ${u} ${si + 1}\u2026`", "Making slide 3\u2026", "Making story 3\u2026"),
    "stopped_one": ("'Stopped: ' + err.message + '. Nothing was overwritten.'", "Stopped: a thing. Nothing was overwritten.", "Stopped: a thing. Nothing was overwritten."),
    # + Add photos (B16): her line when photos have joined (her page line 1086), for three and for one
    "joined_3": ("`${k} new photo${k === 1 ? '' : 's'} in, at the end of your photos (#${now.length - k + 1}${k > 1 ? '\u2013' + now.length : ''}).`",
                 "3 new photos in, at the end of your photos (#168\u2013170).", "3 new photos in, at the end of your photos (#168\u2013170)."),
    "joined_1": ("`${k} new photo${k === 1 ? '' : 's'} in, at the end of your photos (#${now.length - k + 1}${k > 1 ? '\u2013' + now.length : ''}).`",
                 "1 new photo in, at the end of your photos (#168).", "1 new photo in, at the end of your photos (#168)."),
}
# Her saved line for a single slide (her page line 1114), built on her page from the kind's word, the number, the file's name,
# the shoot's short name and the folder; the Assistant says it with those filled in (design.SAVED_SINGLE).
HERS_SAVED_ONE = "`Saved ${u} ${si + 1} as \"${j.file}\", in the ${shoot.short} folder under ${STORY ? 'Stories' : 'Carousel'}. Nothing else was changed. `"
# Her lines in these parts that ours does not carry word for word, and why.
HERS_NOT_OURS = {
    "Opened in Finder": "her saved line's own button changes its label; ours has one Open folder button right after the saved line, whose answer is her full sentence",
    "Could not open it": "the same button; ours says what the Assistant answered",
}
# ("in Finder", her Open folder answers and her Add photos lines, is said on a Mac and File Explorer on a PC: this_computer.FILES_APP;
# hers run `open` and are Mac only. Checked below as its own case rather than as a line left out.)
# Our own words where hers has none (drafts for Nicole), each with its reason.
OUR_WORDS = {
    "Your assistant’s pick is in your slides.": "the carousel's line for the moment the pick arrives on the open page (hers has none; the stories' line is from v26)",
    "It’s your only slide, so it stays.": "beside Remove this slide at one slide, where hers does nothing and says nothing (the stories' line is from v26)",
    "Put a new blank story in front of the one this is on": "her stories' tooltips still say slide (her page renames the three buttons only); ours say story, as every story word does (decision 20)",
    "It's behind this window: click <Finder> in <the Dock> to see it.": "added after her 'Your Carousel folder is open in Finder.' when macOS kept the browser in front (hers never knows); File Explorer and the taskbar on a PC",
    "Only what's inside the box shows on your story.": "the end of her Crop hint in the stories designer: her one page says slide for both kinds; ours says story there, as every story word does (decision 20)",
    "The frame on your story changes shape to match.": "the end of her Keep the frame's shape hint in the stories designer, the same way",
    "Crop the photo": "the Crop window's name for a screen reader (hers: its aria-label, the same words)",
    "Lay them out tidily on their story, every photo whole": "Even them out's tooltip in the stories designer: her one page says slide for both kinds; ours says story there (decision 20)",
    "Save only the story this is on, as its own picture": "Save just this story's tooltip in the stories designer: her page renames the button only; ours says story in its tooltip too (decision 20)",
    "the slide didn't arrive whole, so press it again": "why a single slide was not saved, inside her \"Stopped: <why>. Nothing was overwritten.\" (hers shows the server's own error text there); one clause for each refusal, in design.ONE_WHY",
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


def her_server():
    """Her server.py beside her page (read as text, never run)."""
    for p in HER_PAGES:
        if p.is_file() and (p.parent.parent / "server.py").is_file():
            return (p.parent.parent / "server.py").read_text(encoding="utf-8")
    return ""


HER_SERVER = her_server()


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
// Save just this slide (B17): the saving part's own words, run the same way
var s = SAVE.slice(SAVE.indexOf('var SW = D.WORDS.save = {'), SAVE.indexOf('D.storyWords(SW'));
var SWt = (new Function('D', 'P', s + '; return SW;'))({WORDS: {}}, {list: function(a){ return a.join(', '); }});
out.save_one_any = SWt.saveOneAny; out.save_one_n = SWt.saveOneN(3); out.click_first = SWt.clickFirst; out.making_one = SWt.makingOne(3); out.stopped_one = SWt.stoppedOne('a thing.');
// + Add photos (B16): the ask part's joined line, run by itself (the other three lines come from the page as data)
var a = ASK.slice(ASK.indexOf('joined: function(k, first, last)'), ASK.indexOf('};', ASK.indexOf('joined: function(k, first, last)')));
var J = (new Function('return {' + a + '};'))();
out.joined_3 = J.joined(3, 168, 170); out.joined_1 = J.joined(1, 168, 168);
// a story's own: the most line names 40 stories (the stories' override in the core), and tooMany is given 40
out.too_many_s = W.tooMany(4, 40, 18); out.too_many_1_s = W.tooMany(1, 40, 40);
var m = /most: '((?:[^'\\]|\\.)*)'/g, ms = [], mm; while ((mm = m.exec(CORE))) ms.push(mm[1]);
out.most_s = ms.length > 1 ? (new Function("return '" + ms[1] + "';"))() : '';
JSON.stringify(out);
"""
        f = Path(os.environ.get("TMPDIR", "/private/tmp")) / ("v27-said-%d.js" % os.getpid())
        f.write_text("var CORE = " + json.dumps(core) + ";\nvar DZ = " + json.dumps(dz) + ";\nvar SAVE = " + json.dumps(_src()["DESIGN_SAVE_JS"]) + ";\nvar ASK = " + json.dumps(_src()["DESIGN_ASK_JS"]) + ";\n" + js, encoding="utf-8")
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
// ---- Crop (B11): the box as fractions of the photo, and Done ----
t('crop: the zoom runs 1 to 25 (the Crop window\'s most: a box 4% of the photo), the wheel\'s own top is 3, the box never under 4%', eq(M.RULES.zoom, [1, 25]) && M.RULES.zoomHand === 3 && M.RULES.cropMin === 0.04);
var b1 = F(1, 1, 0, 0, W, H, {ox: 0.3, oy: 0.7, zoom: 2}), PW = 3000, PH = 2000;
var CR = M.cropFromBlock(b1, PW, PH);
t('crop: a frame filling the slide at zoom 2, held at .3 / .7, opens with the box it shows: .2667 by .5 of the photo at .22, .35', eq(CR, {x: 0.22, y: 0.35, w: 0.2667, h: 0.5}), CR);
var p = M.cropApply(b1, CR, PW, PH, 1, true);
t('crop: Done on that box, the shape kept: the very same frame, zoom and crop back (within 1e-3)', p.x === 0 && p.y === 0 && p.w === W && p.h === H && near(p.zoom, 2, 0.001) && near(p.ox, 0.3, 0.001) && near(p.oy, 0.7, 0.001), p);
p = M.cropApply(b1, CR, PW, PH, 1, false);
t('crop: ... and unlocked, a box of the frame\'s own shape leaves the frame as good as it was (a hair from the box\'s rounding), zoom and crop back', near(p.w, W, 0.5) && near(p.h, H, 0.5) && near(p.zoom, 2, 0.001) && near(p.ox, 0.3, 0.001) && near(p.oy, 0.7, 0.001), p);
var b0 = F(1, 1, 0, 0, W, H);
t('crop: a frame at zoom 1 centred opens with the largest box of its shape, centred: for a 3:2 photo in a 4:5 frame, .5333 wide, the whole height', eq(M.cropFromBlock(b0, PW, PH), {x: 0.2333, y: 0, w: 0.5333, h: 1}));
var k = M.cropK(W / H, PW, PH);
t('crop: the frame\'s shape in photo fractions (cropK) is .5333 for a 4:5 frame on a 3:2 photo, and fitLocked at the middle gives that same box', near(k, 0.5333, 0.0001) && eq(M.fitLocked(k, 0.5, 0.5, 1), {w: 0.5333, h: 1, x: 0.2333, y: 0}));
t('crop: fitLocked of a wide shape (k = 2) a quarter wide, centred at .9, .9: the box stays on the photo', eq(M.fitLocked(2, 0.9, 0.9, 0.25), {w: 0.25, h: 0.125, x: 0.75, y: 0.8375}));
var o = {x: 0.2, y: 0.2, w: 0.5, h: 0.5};
t('crop: the se corner pulled in by .1, .2 with the shape free: the box is .4 by .3, its nw corner where it was', eq(M.cropResize(o, 'se', -0.1, -0.2, null), {x: 0.2, y: 0.2, w: 0.4, h: 0.3}));
t('crop: ... with the shape kept (k = .5333): the box follows the smaller pull and keeps the shape, .16 by .3, the nw corner still put', eq(M.cropResize(o, 'se', -0.1, -0.2, k), {x: 0.2, y: 0.2, w: 0.16, h: 0.3}));
t('crop: the nw corner pulled in by .1, .1 with the shape kept: the se corner (.7, .7) stays put', (function(){ var r = M.cropResize(o, 'nw', 0.1, 0.1, k); return near(r.x + r.w, 0.7, 0.0001) && near(r.y + r.h, 0.7, 0.0001) && near(r.w / r.h, k, 0.001); })(), M.cropResize(o, 'nw', 0.1, 0.1, k));
t('crop: the n side pushed down past the bottom: the box is never under 4% tall', eq(M.cropResize(o, 'n', 0, 0.9, null), {x: 0.2, y: 0.66, w: 0.5, h: 0.04}));
t('crop: the e side pulled past the photo\'s edge: the box stops at the edge', eq(M.cropResize(o, 'e', 0.9, 0, null), {x: 0.2, y: 0.2, w: 0.8, h: 0.5}));
t('crop: the w side pushed past the e side, and the e side past the w side: 4% wide, never less, on the far side', eq(M.cropResize(o, 'w', 0.9, 0, null), {x: 0.66, y: 0.2, w: 0.04, h: 0.5}) && eq(M.cropResize(o, 'e', -0.9, 0, null), {x: 0.2, y: 0.2, w: 0.04, h: 0.5}));
t('crop: the s side pushed past the n side: 4% tall', eq(M.cropResize(o, 's', 0, -0.9, null), {x: 0.2, y: 0.2, w: 0.5, h: 0.04}));
t('crop: the se corner pulled past the edge with the shape kept: the box grows as far as the photo allows and keeps the shape', (function(){ var r = M.cropResize(o, 'se', 0.9, 0.9, k); return r.x === 0.2 && r.y === 0.2 && near(r.y + r.h, 1, 0.0001) && near(r.w / r.h, k, 0.001); })(), M.cropResize(o, 'se', 0.9, 0.9, k));
t('crop: moved by .5, .5: the box stays on the photo', eq(M.cropMove(o, 0.5, 0.5), {x: 0.5, y: 0.5, w: 0.5, h: 0.5}) && eq(M.cropMove(o, -0.5, 0.1), {x: 0, y: 0.3, w: 0.5, h: 0.5}));
t('crop: the box given to a resize or a move is untouched', eq(o, {x: 0.2, y: 0.2, w: 0.5, h: 0.5}));
var wide = F(1, 1, 0, 0, W, 400), kw = M.cropK(W / 400, PW, PH), tiny = {x: 0.1, y: 0.1, w: 0.04, h: 0.04 / kw};
p = M.cropApply(wide, tiny, PW, PH, 1, true);
t('crop: a box 4% of the photo on its covering side gives zoom 25, the frame unchanged, the crop where the box was', eq([p.x, p.y, p.w, p.h, p.zoom], [0, 0, W, 400, 25]) && near(p.ox, 0.1 / 0.96, 0.001), p);
p = M.cropApply(b1, {x: 0.4, y: 0, w: 0.04, h: 1}, PW, PH, 1, false);
t('crop: unlocked, a tall thin box (4% wide, the whole height) on a frame filling the slide: the frame takes that shape, 81 by 1350, around the same middle, zoom 1', eq([p.x, p.y, p.w, p.h, p.zoom, p.oy], [499.5, 0, 81, H, 1, 0.5]) && near(p.ox, 0.4167, 0.001), p);
p = M.cropApply(F(1, 1, 0, 0, 400, 400), {x: 0.5, y: 0.1, w: 0.04, h: 0.8}, PW, PH, 1, false);
t('crop: unlocked, a box that would make the frame under 60 px wide (30 by 400): the frame is 60 wide (hers could leave 30), centred where it was, and the box\'s width still fills it (zoom 2.5, so the photo covers the frame)', p.w === 60 && p.h === 400 && p.x === 170 && p.y === 0 && p.zoom === 2.5, p);
p = M.cropApply(F(1, 1, -300, 0, 600, H), {x: 0, y: 0, w: 1, h: 1}, PW, PH, 1, false);
t('crop: unlocked on a frame hanging off the strip\'s left edge: the frame keeps at least 40 px on the strip', M.onStrip(p, 1), p);
t('crop: Done with the whole photo in the box, shape free: zoom 1, the crop centred, the frame the photo\'s shape', (function(){ var q = M.cropApply(b1, {x: 0, y: 0, w: 1, h: 1}, PW, PH, 1, false); return q.zoom === 1 && q.ox === 0.5 && q.oy === 0.5 && near(q.w / q.h, PW / PH, 0.001); })());
t('crop: the layout given to cropApply is untouched', eq(b1, F(1, 1, 0, 0, W, H, {ox: 0.3, oy: 0.7, zoom: 2})));
JSON.stringify(out);
"""


# B13 under the Mac's own JavaScript engine: several things at once, with no page.
MANY_JS = r"""
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
function by(st, id){ return M.find(st, id); }
function whole(b, a){ return near(b.w / b.h, a, 0.002) && b.ox === 0.5 && b.oy === 0.5 && b.zoom === 1; }
function inside(b, slide){ var m = M.EVEN.margin; return b.x >= slide * W + m - 0.01 && b.x + b.w <= (slide + 1) * W - m + 0.01 && b.y >= m - 0.01 && b.y + b.h <= H - m + 0.01; }
// two slides: three photos of mixed shapes and a text box on slide 1 (one photo held at a zoom), one photo on slide 2
var st = {slides: 2, bg: '#ffffff', blocks: [F(1, 1, 100, 100, 500, 400, {ox: 0.2, oy: 0.8, zoom: 2}), F(2, 2, 700, 50, 300, 600), F(3, 3, 150, 700, 600, 300), TX(4, 0, 1200), F(5, 5, W + 50, 50, 600, 600)]};
var A = {1: 1.5, 2: 2 / 3, 3: 1.5, 5: 1}, was = JSON.stringify(st);
t('many: the margin is 40 and the gap 24 (hers), and members() gives the things that are there, once each, in the order asked', M.EVEN.margin === 40 && M.EVEN.gap === 24 && eq(M.members(st, [3, 1, 3, 9, 1]).map(function(b){ return b.id; }), [3, 1]));
// ---- Even them out ----
var r = M.evenOut(st, [1, 2, 3], A);
t('evenOut: three photos (wide, tall, wide): one column comes out biggest (her search), the tall one first (it is highest), each photo whole at its own shape, the crop back to the middle',
  by(r, 2).y < by(r, 1).y && by(r, 1).y < by(r, 3).y && whole(by(r, 1), 1.5) && whole(by(r, 2), 2 / 3) && whole(by(r, 3), 1.5) && near(by(r, 1).x, by(r, 2).x + (by(r, 2).w - by(r, 1).w) / 2, 0.02), r.blocks.slice(0, 3));
t('evenOut: ... the three sit inside the slide\'s margins, the rows 24 apart and the stack centred up and down, the same height each (one column: the row is as tall as its photo)',
  [1, 2, 3].every(function(i){ return inside(by(r, i), 0); }) && near(by(r, 1).y - (by(r, 2).y + by(r, 2).h), 24, 0.02) && near(by(r, 3).y - (by(r, 1).y + by(r, 1).h), 24, 0.02)
  && near(by(r, 2).y, H - (by(r, 3).y + by(r, 3).h), 0.02), r.blocks.slice(0, 3));
t('evenOut: ... it is the largest total area of the column counts: one column beats two and three here', (function(){
  var best = 0, which = 0;
  for (var c = 1; c <= 3; c++) { var rr = Math.ceil(3 / c), cw = (W - 80 - (c - 1) * 24) / c, ch = (H - 80 - (rr - 1) * 24) / rr, area = 0;
    [1.5, 2 / 3, 1.5].forEach(function(a){ var w = Math.min(cw, ch * a); area += w * w / a; }); if (area > best) { best = area; which = c; } }
  return which === 1 && near(by(r, 1).w * by(r, 1).h + by(r, 2).w * by(r, 2).h + by(r, 3).w * by(r, 3).h, best, 5); })());
t('evenOut: the text box in the set is left exactly where it is, and the photo on slide 2 is untouched', eq(by(r, 4), by(st, 4)) && eq(by(r, 5), by(st, 5)));
t('evenOut: the layout it was given is untouched', JSON.stringify(st) === was);
r = M.evenOut(st, [1], A);
t('evenOut: one photo: as large as the margins allow, centred, whole', whole(by(r, 1), 1.5) && by(r, 1).w === 1000 && near(by(r, 1).x, 40) && near(by(r, 1).y, (H - 1000 / 1.5) / 2), by(r, 1));
r = M.evenOut(st, [4, 1], A);
t('evenOut: with a text box among them, only the photos are laid out (one here), the text box stays', eq(by(r, 4), by(st, 4)) && by(r, 1).w === 1000);
t('evenOut: only text boxes, or nothing that is there: the very same layout', M.evenOut(st, [4], A) === st && M.evenOut(st, [99], A) === st && M.evenOut(st, [], A) === st);
r = M.evenOut(st, [5, 1], A);
t('evenOut: photos from two slides land on the first one\'s slide (by slide, then top to bottom): both on slide 1 here, slide 1\'s photo first (one column comes out biggest: the wide one over the square one)',
  inside(by(r, 1), 0) && inside(by(r, 5), 0) && by(r, 1).y < by(r, 5).y && near(by(r, 1).x + by(r, 1).w / 2, W / 2, 0.02) && near(by(r, 5).x + by(r, 5).w / 2, W / 2, 0.02) && whole(by(r, 5), 1), [by(r, 1), by(r, 5)]);
r = M.evenOut(st, [2, 3], null);
t('evenOut: with no shapes given, a photo\'s frame\'s own shape stands in', whole(by(r, 2), 0.5) && whole(by(r, 3), 2));
var many = {slides: 1, bg: '#fff', blocks: []};
for (var i = 1; i <= 60; i++) many.blocks.push(F(i, i, 10 * i, 10 * i, 100, 100));
var ids60 = many.blocks.map(function(b){ return b.id; });
r = M.evenOut(many, ids60, null);
var cols60 = (function(){ var best = 0, which = 0; for (var c = 1; c <= 60; c++) { var rr = Math.ceil(60 / c), cw = (W - 80 - (c - 1) * 24) / c, ch = (H - 80 - (rr - 1) * 24) / rr; if (cw < 60 || ch < 60) continue; var w = Math.min(cw, ch), area = 60 * w * w; if (area > best) { best = area; which = c; } } return which; })();
t('evenOut: sixty squares: laid out in the count of columns where they come out biggest with every cell at least 60 px (' + cols60 + ' columns by her search), all inside the margins, none under 60',
  r !== many && cols60 === 7 && many.blocks.every(function(b){ var q = by(r, b.id); return inside(q, 0) && q.w >= 60 && q.h >= 60; })
  && (function(){ var top = Math.min.apply(null, r.blocks.map(function(b){ return b.y; })), xs = {}; r.blocks.forEach(function(b){ if (b.y === top) xs[Math.round(b.x)] = 1; }); return Object.keys(xs).length === cols60; })()
  && (function(){ var last = Math.max.apply(null, r.blocks.map(function(b){ return b.y; })), row = r.blocks.filter(function(b){ return b.y === last; }); return row.length === 4 && near(Math.min.apply(null, row.map(function(b){ return b.x; })) + Math.max.apply(null, row.map(function(b){ return b.x + b.w; })), W, 0.05); })(), [cols60, r.blocks.length]);
t('evenOut: a layout where no column count fits (frames under 60 either way: 400 squares) is left as it is', (function(){ var s = {slides: 1, bg: '#fff', blocks: []}; for (var i = 1; i <= 400; i++) s.blocks.push(F(i, 1, 0, 0, 100, 100)); return M.evenOut(s, s.blocks.map(function(b){ return b.id; }), null) === s; })());
t('evenOut: the same again changes nothing (the very same layout back)', (function(){ var a = M.evenOut(st, [1, 2, 3], A); return M.evenOut(a, [1, 2, 3], A) === a; })());
// ---- Same size ----
r = M.sameSize(st, [1, 2, 3, 4], 2, {textMin: 80});
t('sameSize: the last clicked (photo 2, 300 wide) is the reference: the others become 300 wide, each photo keeping its own shape with its crop back to the middle, the text box only its width', by(r, 2) === by(st, 2) && by(r, 1).w === 300 && by(r, 1).h === 240 && by(r, 1).ox === 0.5 && by(r, 1).zoom === 1 && by(r, 3).w === 300 && by(r, 3).h === 150 && by(r, 4).w === 300 && by(r, 4).h === 94 && eq([by(r, 1).x, by(r, 1).y, by(r, 3).x, by(r, 3).y], [100, 100, 150, 700]), r.blocks);
r = M.sameSize(st, [1, 4], 4, {textMin: 80});
t('sameSize: a text box as the last clicked is skipped as the reference (ours: hers gave the photos its width): the first photo among them is the reference, so the text box takes the photo\'s width and the photo is untouched', by(r, 1) === by(st, 1) && by(r, 4).w === 500, r.blocks);
t('sameSize: only text boxes, or nothing that is there: the very same layout', M.sameSize(st, [4], 4, null) === st && M.sameSize(st, [99], 99, null) === st);
t('sameSize: a text box is never narrower than the narrowest it may be', by(M.sameSize({slides: 1, bg: '#fff', blocks: [F(1, 1, 0, 0, 60, 60), TX(2, 0, 500)]}, [1, 2], 1, {textMin: 80}), 2).w === 80);
t('sameSize: a photo is never under 60 tall (a very wide one made 60 wide)', by(M.sameSize({slides: 1, bg: '#fff', blocks: [F(1, 1, 0, 0, 60, 60), F(2, 2, 0, 500, 600, 100)]}, [1, 2], 1, null), 2).h === 60);
r = M.sameSize({slides: 1, bg: '#fff', blocks: [F(1, 1, 0, 0, 1000, 1000), F(2, 2, 1000, 1200, 200, 100)]}, [1, 2], 1, null);
t('sameSize: a photo near the strip\'s edge made 1000 wide is kept on the strip (at least 40 px on it)', M.onStrip(by(r, 2), 1) && by(r, 2).w === 1000 && by(r, 2).h === 500, by(r, 2));
t('sameSize: the same again changes nothing', (function(){ var a = M.sameSize(st, [1, 2, 3], 2, null); return M.sameSize(a, [1, 2, 3], 2, null) === a; })());
t('sameSize: the layout it was given is untouched', JSON.stringify(st) === was);
// ---- Line up tops ----
r = M.lineTops(st, [1, 2, 3, 4]);
t('lineTops: every one moves to the highest top among them (50), the text box too; nothing else changes', [1, 2, 3, 4].every(function(i){ return by(r, i).y === 50 && by(r, i).x === by(st, i).x && by(r, i).w === by(st, i).w; }) && eq(by(r, 5), by(st, 5)), r.blocks.map(function(b){ return b.y; }));
t('lineTops: one thing, or things already level, or nothing there: the very same layout', M.lineTops(st, [1]) === st && M.lineTops(r, [1, 2, 3]) === r && M.lineTops(st, [99, 98]) === st);
// ---- Remove them ----
r = M.removeMany(st, [1, 3, 4]);
t('removeMany: the three go, the two left are as they were, in their order', eq(r.blocks, [by(st, 2), by(st, 5)]));
t('removeMany: nothing that is there: the very same layout', M.removeMany(st, [99]) === st && M.removeMany(st, []) === st);
// ---- Drag any of them and they all move ----
r = M.moveMany(st, [1, 2], 10, 20);
t('moveMany: the two move by the same 10, 20; the rest stay', eq([by(r, 1).x, by(r, 1).y, by(r, 2).x, by(r, 2).y], [110, 120, 710, 70]) && eq(by(r, 3), by(st, 3)) && eq(by(r, 4), by(st, 4)));
r = M.moveMany(st, [1, 2], -5000, -5000);
t('moveMany: pushed far off to the top left: the group stops where the first of them would leave the strip (40 px kept), and stays rigid (the two as far apart as they were); hers let them go off altogether',
  M.onStrip(by(r, 1), 2) && M.onStrip(by(r, 2), 2) && by(r, 1).x === 40 - 500 && by(r, 2).x - by(r, 1).x === 600 && by(r, 2).y - by(r, 1).y === -50 && by(r, 1).y === 40 - 400, [by(r, 1), by(r, 2)]);
r = M.moveMany(st, [1, 2, 5], 5000, 5000);
t('moveMany: ... and to the bottom right: the one nearest the strip\'s end stops it (photo 5 keeps 40 px on the strip)', M.onStrip(by(r, 5), 2) && by(r, 5).x === 2 * W - 40 && by(r, 1).x - by(st, 1).x === by(r, 5).x - by(st, 5).x && by(r, 1).y === H - 40, [by(r, 1), by(r, 5)]);
t('moveMany: no move, or nothing there: the very same layout', M.moveMany(st, [1, 2], 0, 0) === st && M.moveMany(st, [99], 10, 10) === st);
t('moveMany: the layout it was given is untouched', JSON.stringify(st) === was);
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
    case("v27 page: the room held for the selected thing's buttons is the same for both kinds now: four rows from 768 px (the slide's group has four buttons), three from 1024 px",
         ".selbar{min-height:calc(var(--row) * 4 + 40px)}" in design_page.DESIGN_CSS and "@media(min-width:900px){.selbar{" not in design_page.DESIGN_CSS
         and "@media(min-width:1024px){\n.selbar{min-height:calc(var(--row) * 3 + 36px)}" in design_page.DESIGN_CSS and "body[data-kind=stories] .selbar" not in design_page.DESIGN_CSS)
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
    # ---- B11: Crop: her words in the crop part, the part on the page, the limits ----
    crop = src["DESIGN_CROP_JS"]
    for k in ("crop_title", "crop_hint", "crop_lock", "crop_cancel", "crop_done", "crop_lock_hint", "cropped"):
        case(f"v27 page: her words in the crop part: {HERS[k][:60]}", "'" + HERS[k].replace("'", "\\'") + "'" in crop, HERS[k])
    names_ = [n for n, _ in design_page.SCRIPTS]
    case("v27 page: the crop part comes after the designs part (whose windows it uses) and before the view part, and its styles are in the parts' CSS",
         names_.index("DESIGN_CROP_JS") > names_.index("DESIGN_DESIGNS_JS") and names_[-2:] == ["DESIGN_CROP_JS", "DESIGN_VIEW_JS"] and ".cr-box{" in design_page.PART_CSS and ".dz-sheet.cr-sheet{" in design_page.PART_CSS)
    case("v27 page: the Crop button is put between Show the whole photo and Move photo inside (her order), and the strip's press is handed to the crop part",
         "group.insertBefore(cropBtn, adj)" in crop and "if (a === 'crop') { if (D.crop) D.crop.open(); return; }" in edit)
    case("v27 page: the window's picture is the Assistant's made copy by number (never a path), and the box's maths are the model's",
         "D.photoUrl(b.n, 'l')" in crop and "M.cropApply(b, cr, cr.pw, cr.ph, D.st.slides, locked)" in crop and "M.cropResize(drag.o, drag.h, dx, dy, lock.checked ? k() : null)" in crop and "/full/" not in crop)
    case("v27 page: the Assistant's own limits give the page zoom 1 to 25 for both kinds, and the smallest frame is still 60",
         design.limits_for("carousel")["zoom"] == [1, 25] and design.limits_for("stories")["zoom"] == [1, 25] and design.ZOOM == (1, 25) and design.FRAME_MIN == 60)
    case("v27 page: the three story-worded lines of the crop window are listed under our words, with their reasons",
         all(w in OUR_WORDS for w in ("Only what's inside the box shows on your story.", "The frame on your story changes shape to match.", "Crop the photo")))
    case("v27 page: the window's two hints read in story words in the stories designer (the page's story words), and in her words on a carousel",
         design.story_words(HERS["crop_hint"]).endswith("Only what's inside the box shows on your story.") and design.story_words(HERS["crop_lock_hint"]).endswith("The frame on your story changes shape to match."))
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

    # ---- B13: several photos at once: her words in the core's table, the bar built inside the stage, the keys, the rules by themselves ----
    for k in ("even", "even_title", "same", "same_title", "tops", "remove_them", "done", "many_hint", "evened", "samed", "lined", "removed_them"):
        case(f"v27 page: her words in the core's table: {HERS[k][:60]}", "'" + HERS[k].replace("'", "\\'") + "'" in core, HERS[k])
    case("v27 page: \"3 selected\" is built from the count as hers is, and the bar is built from the words table inside the stage, as its first child, with her five buttons and her hint",
         "selN: function(n){ return n + ' selected'; }" in core and "stage.insertBefore(mbar, stage.firstChild)" in edit
         and all(x in edit for x in ("mbtn(WORDS.even, 'even', WORDS.evenTitle)", "mbtn(WORDS.sameSize, 'size', WORDS.sameTitle)", "mbtn(WORDS.tops, 'tops')", "mbtn(WORDS.removeThem, 'del')", "mbtn(WORDS.done, 'done')", "el('span', 'hint', WORDS.manyHint)")))
    case("v27 page: a Shift-, Cmd- or Ctrl-click joins or leaves the several before any drag starts, and a press on one of several drags them all through the model's moveMany, with no snapping",
         "if (bd && !hd && (e.shiftKey || e.metaKey || e.ctrlKey)) { D.selectMore(id); return; }" in edit and "next = M.moveMany(D.st, ids, p.x - q0.x, p.y - q0.y)" in edit
         and edit.index("D.selectMore(id); return;") < edit.index("if (D.sel !== id || D.multi.length) D.select(id);"))
    case("v27 page: the five presses go through the model's own operations, Same size with the last clicked as its reference and the text box's narrowest width, each one change (one Undo step, one save)",
         all(x in edit for x in ("M.evenOut(D.st, ids, aspects(ids))", "M.sameSize(D.st, ids, D.sel, {textMin: D.blockTypes.text ? D.blockTypes.text.minW : 0})", "M.lineTops(D.st, ids)", "M.removeMany(D.st, ids)"))
         and "D.setState(next, a === 'del' ? {sel: null, multi: []} : {multi: ids, adjust: false})" in edit)
    case("v27 page: Backspace or Delete with several selected removes them all; Escape lets the several go (the last clicked stays selected)",
         "if (D.multi.length > 1) doMany('del'); else doAct('del');" in edit and "if (D.multi.length > 1) D.select(D.sel); else D.select(null);" in edit)
    case("v27 page: the several are the page's own: never in what a save sends, let go when another design opens, and one that leaves the layout drops out by itself",
         "multi" not in core[core.index("function body(){"):core.index("function queue(){")] and "D.sel = null; D.multi = []; D.adjust = false; dirty = false;" in core and "function pruneMulti(){" in core)
    case("v27 page: the bar's styles are in the page's CSS, in her coral, sticky at the stage's left edge, and the global [hidden] rule covers it (no rule of its own needed)",
         ".multibar{position:sticky;left:0;display:flex;" in design_page.DESIGN_CSS and "background:#fbeee8;border:1px solid #f0cdbf" in design_page.DESIGN_CSS and ".blk.many{outline:2px solid var(--sel)" in design_page.DESIGN_CSS
         and "[hidden]{display:none!important}" in arrange_page.CSS)
    case("v27 page: Even them out's tooltip in a story's words is listed under our words", "Lay them out tidily on their story, every photo whole" in OUR_WORDS
         and design.story_words(HERS["even_title"]) == "Lay them out tidily on their story, every photo whole")
    js = work / "v27-many.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar CAROUSEL_LIMITS = " + json.dumps(design.limits_for("carousel")) + ";\n" + MANY_JS, encoding="utf-8")
    r = osascript(js)
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        rows = None
    if case("v27 page: the several-at-once rules ran by themselves (no page)", isinstance(rows, list) and len(rows) >= 20, (r.stdout[-300:], r.stderr[-300:])):
        for name, ok, detail in rows:
            case("v27 rules: " + name, ok, detail)

    # ---- B14: See a photo big: her words, the tile's button, the wait, the view part on the page last ----
    view = src["DESIGN_VIEW_JS"]
    for k in ("bigger", "view_prev", "view_next", "view_label", "view_used", "view_use", "view_put", "view_close"):
        case(f"v27 page: her words in the core's table: {HERS[k][:60]}", "'" + HERS[k].replace("'", "\\'") + "'" in core, HERS[k])
    case("v27 page: \"See photo 12 bigger\" and \"#12\" are built from the number as hers are", "biggerN: function(n){ return 'See photo ' + n + ' bigger'; }" in core and "viewNum: function(n){ return '#' + n; }" in core)
    case("v27 page: every tray tile is built by one function, with her small button (her tooltip, its name for a screen reader with the number)",
         "function tile(p){" in edit and "D.S.photos.forEach(function(p){ frag.appendChild(tile(p)); });" in edit and "D.tile = tile;" in edit
         and "big.title = WORDS.bigger; big.setAttribute('aria-label', WORDS.biggerN(p.n));" in edit)
    case("v27 page: a single click on a tile puts the photo in after 230 ms (hers), a double-click or the button shows it big and cancels that wait; Return on a tile puts it in at once",
         "var CLICK_WAIT = 230, clickT = null;" in edit and "click: function(){ clickLater(n); }" in edit and "function seeBig(n){ clearTimeout(clickT); clickT = null; if (D.big) D.big.open(n); }" in edit
         and "thumbs.addEventListener('dblclick'" in edit and "if (e.target.closest && e.target.closest('.see')) return;" in edit
         and "if ((e.key === 'Enter' || e.key === ' ') && t && t.classList && t.classList.contains('th')) { e.preventDefault(); clickPhoto(Number(t.dataset.n)); return; }" in edit)
    case("v27 page: the view part is the last script on the page, its styles in the parts' CSS, its window one of the page's sheets",
         names_[-1] == "DESIGN_VIEW_JS" and "#view-img{" in design_page.PART_CSS and ".th .see{" in design_page.PART_CSS and "D.modals.make('view')" in view)
    case("v27 page: the picture is the Assistant's made copy by number (never a path, nothing new fetched), Use is the tray's own click, and the arrow keys step round the tray's order",
         "D.photoUrl(n, 'l')" in view and "/full/" not in view and "D.clickPhoto(n)" in view and "step(e.key === 'ArrowLeft' ? -1 : 1)" in view and "((i + d * k) % list.length + list.length) % list.length" in view)
    case("v27 page: Use says Put it in the selected frame with a frame selected, else Use this photo; and the window closes when the design changes under it",
         "D.label(useBtn, b && M.isFrame(b) ? WORDS.viewPut : WORDS.viewUse);" in view and "D.on('design', function(){ if (D.modals.isOpen(modal)) close(); });" in view)

    # ---- B21: the path at the top: Home › <shoot> post kit › Carousel | Stories, built by look.crumbs (Lane D); her Back pills hidden ----
    import look
    story_html = design_page.page_html("2026-11-01 Fake beach", "stories")
    for name, page_, last in (("carousel", car, HERS["crumb_carousel"]), ("stories", story_html, HERS["crumb_stories"])):
        nav = re.search(r"<nav class='crumbs' aria-label='Where you are'>(.*?)</nav>", page_)
        bar = re.search(r"<div class='bar'>(.*?)</div>", page_)
        case(f"v27 page: the {name} page's bar carries her path, Home › Fake beach post kit › {last}: Home and the post kit are links to paths of this server, the last step is where they are",
             nav and bar and nav.group(0) in bar.group(1) and nav.group(1) == ("<a href='/home'>Home</a><span class='sep' aria-hidden='true'>›</span>"
                                                                                "<a href='/content/2026-11-01%20Fake%20beach/Post%20kit.html'>Fake beach post kit</a><span class='sep' aria-hidden='true'>›</span>"
                                                                                f"<span class='here' aria-current='page'>{last}</span>"), nav and nav.group(1))
        case(f"v27 page: ... her two Back pills stay in the {name} page's markup, hidden (Back to home before the path, ← Back to the post kit after the brand mark)",
             bar and bar.group(1).startswith("<a class='homelink' hidden href='/home'>") and "<a class='kitlink' id='kitlink' hidden>" in bar.group(1) and bar.group(1).count("<a ") == 4, bar and bar.group(1)[:120])
        case(f"v27 page: ... the {name} page counts one bar, and no link in it names a folder on this computer", page_.count("<div class='bar'>") == 1 and no_path(re.findall(r"href='([^']*)'", bar.group(1)))[0] if bar else False)
    case("v27 page: the path is built by look.crumbs from look.kit_trail (Lane D's one builder) with this page's own last step, and the page carries the path's rules with the one colour they need",
         "look.crumbs(look.kit_trail(kit_name) + [(CRUMB_STORIES if story else CRUMB_CAROUSEL, None)])" in (SCRIPTS / "design_page.py").read_text(encoding="utf-8")
         and look.CRUMBS in car and ":root{--coral-2:" + look.COLOR["coral-2"] + "}" in car and design_page.CRUMB_CAROUSEL == HERS["crumb_carousel"] and design_page.CRUMB_STORIES == HERS["crumb_stories"])
    case("v27 page: the script no longer shows the Back to the post kit pill when the kit page is there (the path is the way back); the pill keeps its address",
         "kl.hidden = true;" in core and "kl.hidden = false" not in core and "if (j.kit_page) kl.href = '/content/' + encodeURIComponent(KIT) + '/Post%20kit.html';" in core)

    # ---- B16: + Add photos: her button before "Let my assistant choose", her lines as data in this computer's words, the poll ----
    askjs = src["DESIGN_ASK_JS"]
    app = this_computer.FILES_APP
    tb = re.search(r"<span class='tray-btns'><button class='tb add-photos' id='add-photos' type='button' title='([^']*)'>([^<]*)</button><button class='tb ask-btn' id='ask-pick'", car)
    case("v27 page: \"+ Add photos\" sits right before \"Let my assistant choose the photos\" beside the photos' heading, with her tooltip in this computer's words, on both pages",
         tb and tb.group(2) == HERS["add_photos"] and html.unescape(tb.group(1)) == HERS["add_title"].replace("Finder", app) and "id='add-photos' type='button'" in design_page.page_html("2026-11-01 Fake beach", "stories"), tb and tb.groups())
    ln = re.search(r"<p class='hint' id='add-photos-line' role='status' hidden data-opening='([^']*)' data-open='([^']*)' data-cant='([^']*)'></p>", car)
    case("v27 page: her three lines are on the page as data on the line under the heading, Finder on a Mac and File Explorer on a PC",
         ln and [html.unescape(x) for x in ln.groups()] == [HERS["add_opening"].replace("Finder", app), HERS["add_open"].replace("Finder", app), HERS["add_cant"]]
         and "Finder" not in design_page.ADD_PHOTOS_OPEN.format(app="File Explorer") and "Finder" not in design_page.ADD_PHOTOS_TITLE.format(app="File Explorer"), ln and ln.groups())
    case("v27 page: \"in Finder\" is on our page only in those lines, written from this computer's own file manager (hers names Finder outright)",
         car.count("in " + app) == 3 and car.count("in Finder") == (3 if app == "Finder" else 0) and "in Finder" not in allsrc)
    case("v27 page: the button opens the Photos folder through the Assistant (GET /open, sub Photos, the same route as Open folder), says her line or her could-not line, and starts looking every 4 seconds",
         "fetch('/open?' + D.Q + '&sub=Photos', {cache: 'no-store'})" in askjs and "addSay(APW.opening);" in askjs and "if (!(j && j.ok)) { addSay(APW.cant); return; }" in askjs
         and "var ADD_EVERY = 4000" in askjs and "function watchPhotos(){ if (!addT) addT = setInterval(lookPhotos, ADD_EVERY); }" in askjs)
    case("v27 page: the look asks POST /design-photos only while the line is showing and the page is in sight; a moved stamp with every number kept takes the new list (Designer.takePhotos); a photo gone or renamed asks for a Reload as always",
         "if (addLine.hidden || document.hidden || addBusy || !D.S || !D.design || D.blocked) return;" in askjs and "fetch('/design-photos', {method: 'POST'" in askjs
         and "if (j.kept === false) { addBusy = false; D.photosChanged(); return; }" in askjs and "var fresh = D.takePhotos(s);" in askjs
         and "if (fresh && fresh.length) addSay(APW.joined(fresh.length, fresh[0].n, fresh[fresh.length - 1].n));" in askjs)
    case("v27 page: takePhotos (the core) takes nothing while something is unsaved, when the design on the Assistant's side is not this layout, or when a photo this page knows is gone; it keeps the layout and gives the new photos to the tray, which puts each at the END",
         "if (!D.st || !D.design || D.blocked || !D.save.idle() || !j || !j.ok || !j.design || j.design.id !== D.design.id) return null;" in core
         and "if (JSON.stringify(M.tidy(j.design.state)) !== JSON.stringify(D.st)) return null;" in core and "for (var k = 0; k < D.S.photos.length; k++) { if (!now[D.S.photos[k].n]) return null; }" in core
         and "D.emit('photos-added', fresh);" in core and "hist.clear()" not in core.split("D.takePhotos = function(j){")[1].split("function wanted()")[0]
         and "D.on('photos-added', function(fresh){" in edit and "fresh.forEach(function(p){ if (!tiles[p.n]) frag.appendChild(tile(p)); });" in edit and "thumbs.appendChild(frag);" in edit.split("D.on('photos-added'")[1][:400])
    case("v27 page: the Assistant re-lists through one writer (kit.py sheet, by the reel page's relist_if_changed: Lane A's rule), never from the request thread's own hands, and a design whose photos all kept their numbers keeps its counter",
         "relisted = bool(reel_page.relist_if_changed(kit))" in (SCRIPTS / "design.py").read_text(encoding="utf-8") and '"/design-photos"' in (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")
         and 'if d["state"] != old["state"]:' in (SCRIPTS / "design.py").read_text(encoding="utf-8").split("def _sync(")[1].split("def seed_state")[0])

    # ---- B17: Save just this slide: her two buttons on both pages, the words, the road through the saving part ----
    save_js = src["DESIGN_SAVE_JS"]
    btn = re.search(r"<button class='tb' id='save-one' type='button' disabled title='([^']*)'>([^<]*)</button>", car)
    sbtn = re.search(r"<button class='tb' id='save-one' type='button' disabled title='([^']*)'>([^<]*)</button>", design_page.page_html("2026-11-01 Fake beach", "stories"))
    case("v27 page: \"Save just one slide\" sits right after Save slides in the bar, with her tooltip; the stories page says story",
         btn and sbtn and btn.group(2) == "Save just one slide" and btn.group(1) == HERS["save_one_top_title"] and sbtn.group(2) == "Save just one story"
         and sbtn.group(1) == "Save only the story you clicked" and car.index("id='save-slides'") < car.index("id='save-one'") < car.index("id='save-line'"), (btn and btn.groups(), sbtn and sbtn.groups()))
    case("v27 page: \"Save just this slide\" and its tooltip are in the core's table, and the slide group's last button (after the one-slide line) presses it",
         "saveOne: 'Save just this slide', saveOneTitle: 'Save only the slide this is on, as its own picture'" in core
         and "D.selbar.button(g4, WORDS.saveOne, 'saveone', WORDS.saveOneTitle).id = 'save-one-sel';" in edit and edit.index("g4.appendChild(oneLine);") < edit.index("'saveone'")
         and "if (a === 'saveone') { if (D.saveOne) D.saveOne(slideOf(b) - 1); return; }" in edit)
    case("v27 page: ... and in a story's words the button is her \"Save just this story\"", SW_(HERS["save_one"]) == HERS["save_one_story"])
    case("v27 page: the top button means the slide the selected thing is on, else the one clicked last (D.oneSlideAt), and is relabelled after every press and draw",
         "var si = D.st && D.oneSlideAt ? D.oneSlideAt() : null;" in save_js and "D.label(oneBtn, si == null ? SW.saveOneAny : SW.saveOneN(si + 1));" in save_js
         and "document.addEventListener('pointerup', showSaveOne);" in save_js and "D.on('render', showSaveOne);" in save_js)
    case("v27 page: one slide goes the same road as a set: the fonts waited for, the design saved first, the photo's edit checked, the same painter, the same staging route, one commit that names the slide",
         "await D.type.fonts.ready(D.st, {retry: true})" in save_js.split("async function runOne")[1] and "await D.paint.slide(ctx, st, si, {out: 1, shelf: sh, fonts: false});" in save_js
         and "sent = await sendSlide(id, token, k, n, blob);" in save_js and "var res = await commit(id, token, rev, n, drawn, k);" in save_js and "if (one) o.one = one;" in save_js
         and "if (stale(drawn)) { say(SW.stoppedOne(SW.photoNewer)); D.photosChanged(); return; }" in save_js)
    case("v27 page: a single save never touches what the page knows of the design's set (D.design.set), and the saved line is the Assistant's (her words) with Open folder right after it",
         "if (res.ok) { say(res.words); showOpen(true); }" in save_js and "D.design.set = " not in save_js.split("async function runOne")[1].split("function showSaveOne")[0])
    case("v27 page: Save just this slide asks only about fonts that fell back (hers asks nothing), and the Assistant's reasons are said inside her Stopped line",
         "if (fonts.fellBack && fonts.fellBack.length && !(await ask(SW.fellBack(fonts.fellBack)))) { say(''); return; }" in save_js.split("async function runOne")[1]
         and "P.holeSlides" not in save_js.split("async function runOne")[1].split("function showSaveOne")[0] and "else { say(SW.stoppedOne(res.words)); if (res.why === 'photos') D.photosChanged(); }" in save_js)
    case("v27 page: the Assistant's single-slide names are hers (\"<set> - slide 03 updated.jpg\", \"updated 2\"; a story's \"<set> - 03 updated.jpg\"), and her saved line is its words",
         design.ONE_NAME == "{base} - slide {i:02d} updated.jpg" and design.ONE_AGAIN == "{base} - slide {i:02d} updated {k}.jpg" and design.STORY_ONE_NAME == "{base} - {i:02d} updated.jpg"
         and design.one_name("Beach carousel 1", 3, 1) == "Beach carousel 1 - slide 03 updated.jpg" and design.one_name("Beach carousel 1", 3, 2) == "Beach carousel 1 - slide 03 updated 2.jpg"
         and design.one_name("Beach stories", 3, 1, "stories") == "Beach stories - 03 updated.jpg"
         and design.KW("carousel", design.SAVED_SINGLE, i=3, file="F.jpg", shoot="Beach", folder="Carousel") == 'Saved slide 3 as "F.jpg", in the Beach folder under Carousel. Nothing else was changed.'
         and design.KW("stories", design.SAVED_SINGLE, i=3, file="F.jpg", shoot="Beach", folder="Stories") == 'Saved story 3 as "F.jpg", in the Beach folder under Stories. Nothing else was changed.')
    case("v27 page: every reason a single slide is refused is one clause with no full stop, so her Stopped line reads as one sentence",
         all(isinstance(v, str) and v and not v.rstrip().endswith(".") for v in design.ONE_WHY.values()) and set(design.ONE_WHY) >= {"changed", "missing", "photos", "clash", "redo", "busy", "still", "design", "slide", "drive"})

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
    case("v27 page: her saved line for a single slide is built on her page from the pieces this file names, and her names are \"<set> - slide 0N updated\", then \"updated 2\"",
         HERS_SAVED_ONE in her and 'stem = f"{base}{sep}{i:02d} updated"' in HER_SERVER and 'name, n = f"{stem} {n}.jpg", n + 1' in HER_SERVER, HERS_SAVED_ONE in her)
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
    case("v27 page: her Add photos lines and her tooltip are built on her page as this file has them", all(v in her for k, v in HERS.items() if k.startswith("add_")))


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
        # ---- B11: the zoom past the slider, through the real save route ----
        for z, want, what in ((25, 25, "zoom 25 (the Crop window's most) is kept"), (26, 25, "zoom 26 is brought to 25"), (3, 3, "an older design's zoom 3 is as it was"), (1.5, 1.5, "zoom 1.5 is kept")):
            s_z = json.loads(json.dumps(S1))
            s_z["blocks"][0].update(zoom=z, ox=0.25, oy=0.75)
            code, out = save(s_z)
            got = disk(A)["state"]["blocks"][0]
            case(f"v27 server: {what}, the crop with it", code == 200 and out.get("ok") and got["zoom"] == want and got["ox"] == 0.25 and got["oy"] == 0.75, (code, out, got))
        code, st3 = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
        case("v27 server: the page is told the zoom runs 1 to 25 with every state, for the carousel and for stories",
             st3["limits"]["zoom"] == [1, 25] and get_json(P, f"/design-state?kit={KQ}&kind=stories")[1]["limits"]["zoom"] == [1, 25], st3.get("limits", {}).get("zoom"))
        case("v27 server: nothing a page was given in this part names a folder on this computer", all(no_path(x, work)[0] for x in seen))
        case("v27 server: the photos were only ever read", _tree(kit / "Photos") == _tree(kit / "Photos"))

        # ---- B4c: the chat's side for a carousel: design.py note and fill ----
        check_fill_commands(case, work, env, kit, kit_name, run, A, get_json, P, KQ, post, J)
        # ---- B17: Save just this slide, through the real routes and the commit as a process of its own ----
        check_save_one(case, work, env, kit, kit_name, studio, run, A, get_json, P, KQ, post, ask, jpeg, J, disk, save, S1, STAMP)
        # ---- B16: + Add photos: two photos dropped into the Photos folder, numbered after the last ----
        check_add_photos(case, work, kit, kit_name, A, get_json, P, KQ, post, ask, J, disk, save, S1)
    finally:
        srv.stop()


def check_add_photos(case, work, kit, kit_name, A, get_json, P, KQ, post, ask, J, disk, save, S1):
    """B16: POST /design-photos: nothing new answers so; two photos dropped in are numbered after the last by the one writer,
    every other photo keeping its number and name, the designs' frames and counters untouched; a photo taken out is told as
    not kept (the page's Reload path); another website refused; no path in any answer; the photos only ever read."""
    import shutil
    photos_dir = kit / "Photos"
    sheet = kit / ".kit" / "sheet.json"

    def rows():
        return {x["n"]: Path(x["file"]).name for x in json.loads(sheet.read_text(encoding="utf-8"))["photos"]}

    def stamp():
        return hashlib.sha1(sheet.read_bytes()).hexdigest()[:12]

    before, s0 = rows(), stamp()
    originals = _tree(photos_dir)
    code, out = J(post(P, "/design-photos", {"kit": kit_name}))
    case("v27 server: POST /design-photos with nothing new: ok, nothing added, every number kept, the list's stamp as it is",
         code == 200 and out == {"ok": True, "stamp": s0, "added": 0, "kept": True, "relisted": False}, (code, out))
    code, _, data = ask(P, "POST", "/design-photos", body=json.dumps({"kit": kit_name}).encode(), headers={"Content-Type": "application/json", "Origin": "http://evil.example"})
    case("v27 server: another website cannot ask it (403)", code == 403, (code, data[:80]))
    code, out = J(post(P, "/design-photos", {"kit": kit_name, "kind": "reels"}))
    case("v27 server: a kind that is not one is refused", code == 400 and out.get("why") == "kind", (code, out))
    first_two = sorted(os.listdir(photos_dir))[:2]
    new = ["zz new one.jpg", "zz new two.jpg"]
    for src, dst in zip(first_two, new):
        shutil.copyfile(photos_dir / src, photos_dir / dst)
        t = time.time() - 30
        os.utime(photos_dir / dst, (t, t))           # settled: not still being copied in
    d0 = disk(A)
    time.sleep(4.2)                                  # the folder is compared at most every 4 seconds a kit (Lane A's rule)
    code, out = J(post(P, "/design-photos", {"kit": kit_name}))
    after = rows()
    case("v27 server: two photos dropped in: the list is made again, 2 added as the next two numbers, every photo before kept its number and name",
         code == 200 and out.get("ok") and out.get("relisted") is True and out.get("added") == 2 and out.get("kept") is True and out.get("first") == len(before) + 1 and out.get("last") == len(before) + 2
         and out.get("stamp") == stamp() != s0 and {n: f for n, f in after.items() if n <= len(before)} == before and [after[len(before) + 1], after[len(before) + 2]] == new, (code, out))
    d1 = disk(A)
    code, st = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
    d2 = disk(A)
    case("v27 server: the design's frames are untouched and its counter has not moved (the photos it uses kept their numbers), its stamp now the new list's; the page is given 16 photos and no path",
         d1["state"] == d0["state"] and d2["state"] == d0["state"] and d2["rev"] == d0["rev"] and d2["stamp"] == stamp() and d2.get("names") == d0.get("names")
         and code == 200 and len(st["photos"]) == len(before) + 2 and st["stamp"] == stamp() and st["design"]["rev"] == d0["rev"] and no_path(st, work)[0], (d0["rev"], d1["rev"], d2["rev"]))
    code, out = J(post(P, "/design", {"kit": kit_name, "design": A, "stamp": stamp(), "base": d0["rev"], "page": "v27serverpage04", "state": dict(S1, bg="#eeeeee")}))
    case("v27 server: a page that took the new list goes on saving from the counter it had", code == 200 and out.get("ok") and out.get("rev") == d0["rev"] + 1, (code, out))
    code, out = J(post(P, "/design-photos", {"kit": kit_name}))
    case("v27 server: asked again at once: nothing new, and the folder is not compared again within 4 seconds", code == 200 and out.get("added") == 0 and out.get("relisted") is False and out.get("kept") is True, out)
    aside = kit / "Photos-aside"
    aside.mkdir(exist_ok=True)
    shutil.move(str(photos_dir / new[1]), str(aside / new[1]))
    time.sleep(4.2)
    code, out = J(post(P, "/design-photos", {"kit": kit_name}))
    after2 = rows()
    case("v27 server: a photo taken out: the list is made again, its number stays unused, and the answer says the numbers were NOT all kept (the page's Reload path)",
         code == 200 and out.get("relisted") is True and out.get("kept") is False and out.get("added") == 0 and len(before) + 2 not in after2 and after2[len(before) + 1] == new[0]
         and {n: f for n, f in after2.items() if n <= len(before)} == before, (code, out))
    code, st = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
    case("v27 server: the design is still whole after that (no frame used the photo that went)", code == 200 and disk(A)["state"] == dict(S1, bg="#eeeeee") and disk(A)["rev"] == d0["rev"] + 1, disk(A)["rev"])
    case("v27 server: the photos that were there were only ever read", all(_tree(photos_dir).get(k) == v for k, v in originals.items()))
    case("v27 server: no answer here names a folder on this computer", all(no_path(x, work)[0] for x in (out, st)))


def check_save_one(case, work, env, kit, kit_name, studio, run, A, get_json, P, KQ, post, ask, jpeg, J, disk, save, S1, STAMP):
    """B17: one slide saved beside the design's newest set as "<set> - slide 0N updated.jpg", then "updated 2"; a story's
    "<set> - 0N updated.jpg"; with no set yet, from the design's own name; i out of range, a stale counter and nothing
    staged refused in her Stopped clause; the file byte for byte the one sent; kit.json and the line for Claude untouched;
    a save cut off after its record is finished by the next press; design.py show lists it."""
    sys.path.insert(0, str(SCRIPTS))
    import design
    JH = {"Content-Type": "image/jpeg"}
    car_dir, sto_dir, rec_file, waiting = kit / "Carousel", kit / "Stories", kit / ".kit" / "kit.json", studio / "arrange-waiting.json"
    cdesigns, sdesigns = kit / ".kit" / "designs", kit / ".kit" / "story-designs"

    def jrn(did, tok, folder=cdesigns):
        p = folder / "sets" / f"{did}-{tok}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def held():
        return (rec_file.read_bytes(), waiting.read_bytes() if waiting.is_file() else b"")

    code, out = save(S1, base=disk(A)["rev"])      # the layout the design's whole set was saved from, back as it was
    case("v27 server: (the design's layout is back as its set was saved from)", code == 200 and out.get("ok"), (code, out))
    tree0, held0 = _tree(car_dir), held()
    r = disk(A)["rev"]
    one = jpeg(W, H, seed=21)
    code0, _, _ = ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27one0000001&i=2&of=3", body=one, headers=JH)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000001", "rev": r, "count": 3, "one": 2}))
    want = "Dune day carousel 1 - slide 02 updated.jpg"
    case("v27 server: Save just slide 2: the slide goes to staging as any slide does, and the commit with one: 2 puts it beside the design's newest set as her \"<set> - slide 02 updated.jpg\", byte for byte the one sent",
         code0 == 200 and code == 200 and out.get("ok") is True and out.get("file") == want and out.get("slide") == 2 and (car_dir / want).is_file() and (car_dir / want).read_bytes() == one, (code0, code, out))
    case("v27 server: ... her saved line, whole, with the shoot's short name and the folder", out.get("words") == f'Saved slide 2 as "{want}", in the Dune day folder under Carousel. Nothing else was changed.', out.get("words"))
    case("v27 server: ... nothing else in the Carousel folder changed, kit.json is byte for byte as it was (the set the kit shows is unchanged), and no line for Claude was written",
         {k: v for k, v in _tree(car_dir).items() if k != want} == tree0 and held() == held0)
    j1 = jrn(A, "v27one0000001")
    case("v27 server: ... the save's record says one: 2, the first time round, done, with the one file under that name and its hash",
         j1 and j1.get("one") == 2 and j1.get("again") == 1 and j1["state"] == "done" and [f["final"] for f in j1["files"]] == [want] and j1["files"][0]["sha256"] == hashlib.sha256(one).hexdigest(), j1 and {k: j1.get(k) for k in ("one", "again", "state")})
    code, out2 = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000001", "rev": r, "count": 3, "one": 2}))
    case("v27 server: the same press again (its answer lost): the same answer, and nothing new in the folder", code == 200 and out2 == out and {k: v for k, v in _tree(car_dir).items() if k != want} == tree0, out2)
    code, st = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
    case("v27 server: the page is still told the design's newest SET is the whole one (a single slide is not a set), and nothing unfinished",
         code == 200 and st["design"]["set"] and st["design"]["set"]["base"] == "Dune day carousel 1" and st["design"]["set"]["count"] == 3 and st["design"]["unfinished"] is False, st["design"].get("set"))
    two = jpeg(W, H, seed=22)
    ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27one0000002&i=2&of=3", body=two, headers=JH)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000002", "rev": r, "count": 3, "one": 2}))
    want2 = "Dune day carousel 1 - slide 02 updated 2.jpg"
    case("v27 server: slide 2 saved on its own again: \"updated 2\", the first left as it was", code == 200 and out.get("file") == want2 and (car_dir / want2).read_bytes() == two and (car_dir / want).read_bytes() == one, out)
    (car_dir / "DUNE DAY CAROUSEL 1 - SLIDE 02 UPDATED 3.JPG").write_bytes(b"theirs")
    ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27one0000003&i=2&of=3", body=two, headers=JH)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000003", "rev": r, "count": 3, "one": 2}))
    case("v27 server: a file of theirs under that name in capitals (a drive that ignores capitals): the next name is \"updated 4\", theirs untouched",
         code == 200 and out.get("file") == "Dune day carousel 1 - slide 02 updated 4.jpg" and (car_dir / "DUNE DAY CAROUSEL 1 - SLIDE 02 UPDATED 3.JPG").read_bytes() == b"theirs", out)
    # refusals, in her Stopped clause (no full stop), nothing added
    tree1 = _tree(car_dir)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000004", "rev": r, "count": 3, "one": 0}))
    case("v27 server: one: 0 is refused as not understood", code == 400 and out.get("ok") is False and out.get("why") == "commit", (code, out))
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000004", "rev": r, "count": 3, "one": 4}))
    case("v27 server: one: 4 on a three-slide design: refused (why slide), the clause for her Stopped line, nothing added",
         code == 400 and out.get("why") == "slide" and out.get("words") == design.ONE_WHY["slide"] and _tree(car_dir) == tree1, (code, out))
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000004", "rev": r + 1, "count": 3, "one": 2}))
    case("v27 server: a counter that is not the design's: refused (why changed) with the clause", code == 409 and out.get("why") == "changed" and out.get("words") == design.ONE_WHY["changed"], (code, out))
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000004", "rev": r, "count": 3, "one": 2}))
    case("v27 server: nothing staged under that press: refused (why missing) with the clause", code == 400 and out.get("why") == "missing" and out.get("words") == design.ONE_WHY["missing"], (code, out))
    ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27one0000005&i=1&of=3", body=one, headers=JH)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000005", "rev": r, "count": 3, "one": 2}))
    case("v27 server: slide 1 staged but slide 2 asked for: refused (why missing), nothing added", code == 400 and out.get("why") == "missing" and _tree(car_dir) == tree1, (code, out))
    code, _, data = ask(P, "POST", "/design-commit", body=json.dumps({"kit": kit_name, "design": A, "set": "v27one0000005", "rev": r, "count": 3, "one": 1}).encode(),
                        headers={"Content-Type": "application/json", "Origin": "http://evil.example"})
    case("v27 server: another website cannot save a slide (403)", code == 403 and _tree(car_dir) == tree1, (code, data[:80]))
    # a save cut off right after its record is written: finished under its name by the next commit (the route's)
    env_stop = dict(env, DESIGN_TEST_STOP="after-journal")
    code, o = run(env_stop, "design.py", "commit", kit_name, "--design", A, "--set", "v27one0000005", "--rev", str(r), "--one", "1")
    j5 = jrn(A, "v27one0000005")
    case("v27 server: the commit command stopped dead after writing the record: it says moving, names the file, and the Carousel folder has nothing new",
         code == 9 and j5 and j5["state"] == "moving" and j5.get("one") == 1 and j5["files"][0]["final"] == "Dune day carousel 1 - slide 01 updated.jpg" and _tree(car_dir) == tree1, (code, o[-200:], j5 and j5.get("state")))
    code, st = J(get_json(P, f"/design-state?kit={KQ}&design={A}"))
    case("v27 server: ... the page is told the design has an unfinished save", code == 200 and st["design"]["unfinished"] is True)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000005", "rev": r, "count": 3, "one": 1}))
    case("v27 server: ... the next press finishes it under the name written down, and says so",
         code == 200 and out.get("file") == "Dune day carousel 1 - slide 01 updated.jpg" and (car_dir / out.get("file", "x")).read_bytes() == one and jrn(A, "v27one0000005")["state"] == "done", out)
    # a save cut off after its record, whose staged slide is then gone and a file of THEIRS sits under the name written down:
    # the next commit finds a file there that is not the slide (by its hash) and refuses; theirs is never taken for the slide
    ask(P, "POST", f"/design-slide?kit={KQ}&design={A}&set=v27one0000010&i=3&of=3", body=two, headers=JH)
    code, o = run(env_stop, "design.py", "commit", kit_name, "--design", A, "--set", "v27one0000010", "--rev", str(r), "--one", "3")
    j10 = jrn(A, "v27one0000010")
    theirs = car_dir / "Dune day carousel 1 - slide 03 updated.jpg"
    if case("v27 server: (another save stopped dead after its record, for slide 3)", code == 9 and j10 and j10["state"] == "moving" and j10["files"][0]["final"] == theirs.name, (code, j10 and j10.get("state"))):
        (kit / ".kit" / "design-staging" / f"{A}-v27one0000010" / "slide-03.jpg").unlink()      # the Assistant's own staged copy, gone (a pretend mishap)
        theirs.write_bytes(b"a picture of theirs under that very name")
        code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27one0000010", "rev": r, "count": 3, "one": 3}))
        case("v27 server: ... the next press finds their file under the name and refuses (the record is put back as undone, then the press finds nothing staged: why missing, her clause): their file is never taken for the slide, and is untouched",
             code == 400 and out.get("ok") is False and out.get("why") in ("clash", "missing") and out.get("words") == design.ONE_WHY[out.get("why")] and theirs.read_bytes() == b"a picture of theirs under that very name"
             and jrn(A, "v27one0000010")["state"] == "undone" and not (car_dir / "Dune day carousel 1 - slide 03 updated 2.jpg").exists(), (code, out))
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": A, "set": "v27set0000009", "rev": r, "count": 3}))
    case("v27 server: Save slides after single saves, with the layout as the set was saved from: \"Already saved as ...\" still (a single slide is not a set and changes none)",
         code == 200 and out.get("already") is True and out.get("base") == "Dune day carousel 1", out)
    # with no whole set yet: the design's own name
    code, nd = J(post(P, "/design-new", {"kit": kit_name, "token": "v27new0000001", "state": {"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 3, 0), _frame(2, 4, W)]}}))
    B = nd.get("design", {}).get("id") if code == 200 else None
    if case("v27 server: (a second design, never saved as a set)", code == 200 and B, (code, nd)):
        rb = disk(B)["rev"]
        ask(P, "POST", f"/design-slide?kit={KQ}&design={B}&set=v27one0000006&i=1&of=2", body=two, headers=JH)
        code, out = J(post(P, "/design-commit", {"kit": kit_name, "design": B, "set": "v27one0000006", "rev": rb, "count": 2, "one": 1}))
        case("v27 server: a single slide from a design with no set yet is named from the design's own name", code == 200 and out.get("file") == f"{nd['design']['name']} - slide 01 updated.jpg" and (car_dir / out["file"]).read_bytes() == two, out)
    # a story on its own
    code, ss = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
    SID = ss["design"]["id"]
    sst = {"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, h=SH), _frame(2, 2, SW, h=SH)]}
    code, out = J(post(P, "/design", {"kit": kit_name, "kind": "stories", "design": SID, "stamp": STAMP, "base": disk(SID, sdesigns)["rev"], "page": "v27serverpage03", "state": sst}))
    story = jpeg(SW, SH, seed=23)
    code0, _, _ = ask(P, "POST", f"/design-slide?kit={KQ}&kind=stories&design={SID}&set=v27one0000007&i=2&of=2", body=story, headers=JH)
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "kind": "stories", "design": SID, "set": "v27one0000007", "rev": disk(SID, sdesigns)["rev"], "count": 2, "one": 2}))
    sname = disk(SID, sdesigns)["name"]
    case("v27 server: Save just this story: \"<set> - 02 updated.jpg\" in the Stories folder, her line in story words",
         code0 == 200 and code == 200 and out.get("file") == f"{sname} - 02 updated.jpg" and (sto_dir / out.get("file", "x")).read_bytes() == story
         and out.get("words") == f'Saved story 2 as "{out.get("file")}", in the Dune day folder under Stories. Nothing else was changed.', (code0, code, out))
    code, out = J(post(P, "/design-commit", {"kit": kit_name, "kind": "stories", "design": SID, "set": "v27one0000008", "rev": disk(SID, sdesigns)["rev"], "count": 2, "one": 2}))
    case("v27 server: ... a story's refusal is in story words", code == 400 and out.get("words") == "the story didn't arrive whole, so press it again", out)
    code, o = run(env, "design.py", "show", kit_name)
    case("v27 server: design.py show lists each slide saved on its own, by its file", code == 0 and f'Slide 2 on its own: "{want}"' in o and f'Slide 2 on its own: "{want2}"' in o and "Slide 1 on its own:" in o, o[-600:])
    code, o = run(env, "design.py", "show", kit_name, "--kind", "stories")
    case("v27 server: ... and a story saved on its own", code == 0 and f'Story 2 on its own: "{sname} - 02 updated.jpg"' in o, o[-400:])
    case("v27 server: nothing a page was given about single saves names a folder on this computer", all(no_path(x, work)[0] for x in (out, st, ss)))


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
    sys.path.insert(0, str(SCRIPTS))
    import design
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
            # ---- the path at the top (B21): in sight, the pills gone, the kit step a link, the page one bar ----
            crumbs = Jx("(function(){ var n = document.querySelector('.bar .crumbs'); if (!n) return null; var r = n.getBoundingClientRect(); "
                        "return {steps: Array.from(n.children).filter(function(e){ return !e.classList.contains('sep'); }).map(function(e){ return [e.tagName, e.textContent, e.getAttribute('href'), e.getAttribute('aria-current')]; }), "
                        "shown: getComputedStyle(n).display !== 'none' && r.height > 0, top: r.top, bars: document.querySelectorAll('.bar').length, "
                        "home: getComputedStyle(document.querySelector('.bar .homelink')).display, kit: getComputedStyle(document.getElementById('kitlink')).display, hover: getComputedStyle(n.querySelector('a')).borderRadius}; })()")
            case("v27 browser: her path at the top of the carousel page: Home › Beach post kit › Carousel, in sight at the top, Home and the post kit links, both Back pills really gone, one bar",
                 crumbs and crumbs["steps"] == [["A", "Home", "/home", None], ["A", "Beach post kit", "/content/2026-11-01%20Beach/Post%20kit.html", None], ["SPAN", "Carousel", None, "page"]]
                 and crumbs["shown"] and 0 <= crumbs["top"] < 60 and crumbs["bars"] == 1 and crumbs["home"] == "none" and crumbs["kit"] == "none" and crumbs["hover"] == "999px", crumbs)
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
            case("v27 browser: a photo selected: Add a slide before, Add a slide after, Remove this slide, Save just this slide (B17), with her tooltips, right before the group for anything (hers), after the text's groups",
                 grp == {"shown": True, "btns": [[HERS["before"], HERS["before_title"], False], [HERS["after"], HERS["after_title"], False], [HERS["remove_this"], HERS["remove_title"], False],
                                                 [HERS["save_one"], HERS["save_one_title"], False]], "line": True, "after": "sel-all"}, grp)
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
            case("v27 browser: a photo selected: the Crop group runs Show the whole photo (her tooltip), Crop, Move photo inside, the empty-frame button, none off",
                 grp["shown"] and grp["btns"][0] == [HERS["whole"], HERS["whole_title"], False] and grp["btns"][1][0] == "Crop" and grp["btns"][2][0] == "Move photo inside" and not any(b[2] for b in grp["btns"]), grp)
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
            case("v27 browser: an empty frame selected: Show the whole photo is off, like Move photo inside, and Crop too",
                 c.js("document.getElementById('whole-photo').disabled && document.getElementById('adjust').disabled && document.getElementById('crop-btn').disabled") is True)
            case("v27 browser: nothing went wrong on the page through the photo's buttons", not c.page_errors(), c.page_errors()[:3])

            # ---- Crop (B11) ----
            def crop_open():
                return c.js("!!(Designer.crop && Designer.crop.isOpen())")

            def box():
                return Jx("Designer.crop.box()")

            def img_layout(bid):
                return Jx("(function(){ var n = document.querySelector('#strip .blk[data-id=\"" + str(bid) + "\"]'), i = n.querySelector('img'), b = DesignModel.find(Designer.st, " + str(bid) + "); "
                          "var L = DesignModel.layoutImg(b, i.naturalWidth, i.naturalHeight), s = Designer.scale; return {dl: i.offsetLeft - L.left * s, dt: i.offsetTop - L.top * s, dw: i.offsetWidth - L.iw * s, dh: i.offsetHeight - L.ih * s}; })()")

            put({"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 100, 100, 800, 800)]})
            rev3 = disk()["rev"]
            c.click("#strip .blk[data-id='1']")
            order = Jx("Array.from(document.querySelectorAll('#sel-crop button')).map(function(b){ return [b.id, b.textContent, b.title]; })")
            case("v27 browser: the Crop group runs Show the whole photo, Crop (her tooltip), Move photo inside, then the empty-frame button (her order)",
                 [o[1] for o in order][:3] == [HERS["whole"], HERS["crop"], "Move photo inside"] and order[1][0] == "crop-btn" and order[1][2] == HERS["crop_title"], order)
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            words = Jx("(function(){ var m = document.getElementById('crop'); return {open: !m.hidden, h2: m.querySelector('h2').textContent, hint: m.querySelector('p.hint').textContent, "
                       "lock: document.querySelector('label.cr-chk').textContent.trim(), locked: document.getElementById('crop-lock').checked, all: document.getElementById('crop-all').textContent, "
                       "cancel: document.getElementById('crop-cancel').textContent, done: document.getElementById('crop-done').textContent, lockHint: document.getElementById('crop-hint').textContent, "
                       "label: m.querySelector('[role=dialog]').getAttribute('aria-label'), focus: document.activeElement.id, src: document.getElementById('crop-img').getAttribute('src'), "
                       "handles: Array.from(document.querySelectorAll('#crop-box i')).filter(function(i){ return getComputedStyle(i).display !== 'none'; }).map(function(i){ return i.dataset.h; }), "
                       "z: Number(getComputedStyle(m).zIndex), sz: Number(getComputedStyle(document.getElementById('stage')).zIndex), "
                       "over: (function(){ var r = document.getElementById('stage').getBoundingClientRect(); return m.contains(document.elementFromPoint(r.left + 20, r.top + 20)); })()}; })()")
            case("v27 browser: Crop opens her window: her title, hint, Keep the frame's shape ticked, Show the whole photo, Cancel, Done, her untick hint; four corner handles only; Done has the keyboard",
                 words["open"] and words["h2"] == "Crop" and words["hint"] == HERS["crop_hint"] and words["lock"] == HERS["crop_lock"] and words["locked"] and words["all"] == HERS["whole"]
                 and words["cancel"] == HERS["crop_cancel"] and words["done"] == HERS["crop_done"] and words["lockHint"] == HERS["crop_lock_hint"] and words["label"] == "Crop the photo"
                 and words["focus"] == "crop-done" and sorted(words["handles"]) == ["ne", "nw", "se", "sw"], words)
            case("v27 browser: the window sits above the sticky stage (a press on the stage's corner lands in the window), and its picture is the made copy by number, no path",
                 words["z"] > words["sz"] and words["over"] and words["src"].startswith("/kit-photo?") and "&n=1&size=l" in words["src"] and no_path(words["src"])[0], (words["z"], words["sz"], words["src"]))
            nat1 = Jx("(function(){ var i = document.getElementById('crop-img'); return {w: i.naturalWidth, h: i.naturalHeight}; })()")
            b_open = box()
            want_box = Jx("DesignModel.cropFromBlock(DesignModel.find(Designer.st, 1), " + str(b_open["pw"]) + ", " + str(b_open["ph"]) + ")")
            case("v27 browser: the box opens as what the frame shows now (a centred photo filling the slide: the largest box of the frame's shape, centred), of the photo's own shape",
                 {k_: b_open[k_] for k_ in ("x", "y", "w", "h")} == want_box and abs(b_open["pw"] * nat1["h"] - b_open["ph"] * nat1["w"]) <= max(nat1["w"], nat1["h"]) and (b_open["h"] == 1 or b_open["w"] == 1), (b_open, want_box, nat1))
            drawn = Jx("(function(){ var i = document.getElementById('crop-img'), b = document.getElementById('crop-box'); return {l: b.offsetLeft / i.clientWidth, t: b.offsetTop / i.clientHeight, w: b.offsetWidth / i.clientWidth, h: b.offsetHeight / i.clientHeight}; })()")
            case("v27 browser: ... and the box is drawn over the picture at those fractions", all(abs(drawn[a] - b_open[b_]) < 0.01 for a, b_ in (("l", "x"), ("t", "y"), ("w", "w"), ("h", "h"))), (drawn, b_open))
            hr = c.rect("#crop-box i[data-h=se]")
            c.drag("#crop-box i[data-h=se]", (hr["cx"] - 90, hr["cy"] - 60), steps=10)
            b1 = box()
            kk = Jx("DesignModel.cropK(Designer.crop.box().ar, Designer.crop.box().pw, Designer.crop.box().ph)")
            case("v27 browser: the se corner dragged in with the shape kept: the box is smaller, still the frame's shape, its nw corner where it was",
                 b1["w"] < b_open["w"] and b1["h"] < b_open["h"] and abs(b1["w"] / b1["h"] - kk) < 0.01 and b1["x"] == b_open["x"] and b1["y"] == b_open["y"], (b1, kk))
            c.drag("#crop-box", (c.rect("#crop-box")["cx"] + 40, c.rect("#crop-box")["cy"] + 30), steps=8)
            b2 = box()
            case("v27 browser: dragged inside the box: it moves, its size the same", b2["x"] > b1["x"] and b2["y"] > b1["y"] and b2["w"] == b1["w"] and b2["h"] == b1["h"], (b1, b2))
            want = Jx("DesignModel.cropApply(DesignModel.find(Designer.st, 1), Designer.crop.box(), Designer.crop.box().pw, Designer.crop.box().ph, Designer.st.slides, true)")
            c.click("#crop-done")
            c.wait_for("!Designer.crop.isOpen()", 5)
            got = st()["blocks"][0]
            case("v27 browser: Done: the frame shows exactly what was in the box (the model's cropApply: the same frame, a zoom past 1 and the crop), the window closed, her line beside the buttons, the photo still selected",
                 {k_: got[k_] for k_ in want} == want and got["zoom"] > 1.2 and got["x"] == 0 and got["w"] == W and sel_line() == HERS["cropped"] and c.js("Designer.sel") == 1, (got, want, sel_line()))
            lay = img_layout(1)
            case("v27 browser: ... and the strip draws the photo inside its frame from that zoom and crop (the picture's place and size follow layoutImg)", all(abs(v) <= 1.5 for v in lay.values()), lay)
            case("v27 browser: ... saved as one change (rev + 1)", settled() and disk()["rev"] == rev3 + 1 and disk()["state"]["blocks"][0]["zoom"] == got["zoom"], disk()["rev"])
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            b3 = box()
            case("v27 browser: Crop opened again: the box is the one Done made (the round trip)", all(abs(b3[k_] - b2[k_]) < 0.002 for k_ in ("x", "y", "w", "h")), (b2, b3))
            c.key("Escape")
            c.wait_for("!Designer.crop.isOpen()", 5)
            case("v27 browser: Escape closes the window and changes nothing", st()["blocks"][0] == got and c.js("Designer.crop.box()") is None)
            c.click("#undo")
            case("v27 browser: Undo takes the crop back", st()["blocks"][0] == _frame(1, 1, 0), st()["blocks"][0])
            # unlocked: eight handles, and the frame takes the box's shape
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            c.click("#crop-lock")
            handles = Jx("Array.from(document.querySelectorAll('#crop-box i')).filter(function(i){ return getComputedStyle(i).display !== 'none'; }).map(function(i){ return i.dataset.h; })")
            case("v27 browser: Keep the frame's shape unticked: eight handles", sorted(handles) == ["e", "n", "ne", "nw", "s", "se", "sw", "w"], handles)
            b4 = box()
            hr = c.rect("#crop-box i[data-h=e]")
            c.drag("#crop-box i[data-h=e]", (hr["cx"] - 120, hr["cy"]), steps=10)
            b5 = box()
            case("v27 browser: the e side dragged in: the box is narrower, as tall as it was", b5["w"] < b4["w"] - 0.05 and b5["h"] == b4["h"] and b5["x"] == b4["x"], (b4, b5))
            want = Jx("DesignModel.cropApply(DesignModel.find(Designer.st, 1), Designer.crop.box(), Designer.crop.box().pw, Designer.crop.box().ph, Designer.st.slides, false)")
            c.click("#crop-done")
            c.wait_for("!Designer.crop.isOpen()", 5)
            got2 = st()["blocks"][0]
            case("v27 browser: Done unticked: the frame takes the box's shape inside the space it had, around the same middle (narrower than the slide, centred on it), her line",
                 {k_: got2[k_] for k_ in want} == want and got2["w"] < W and abs(got2["x"] + got2["w"] / 2 - W / 2) < 1 and got2["h"] == H and abs(got2["w"] / got2["h"] - (b5["w"] * b5["pw"]) / (b5["h"] * b5["ph"])) < 0.01
                 and sel_line() == HERS["cropped"], (got2, want))
            case("v27 browser: ... the strip draws it so", all(abs(v) <= 1.5 for v in img_layout(1).values()), img_layout(1))
            case("v27 browser: ... saved", settled())
            c.click("#undo")
            # Show the whole photo inside the window, Cancel, a press beside the window
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            hr = c.rect("#crop-box i[data-h=se]")
            c.drag("#crop-box i[data-h=se]", (hr["cx"] - 90, hr["cy"] - 60), steps=8)
            c.click("#crop-all")
            b6 = box()
            # (the strip now draws from the sharper copy, whose shape is the photo's to within a pixel, so the box is the same to a few thousandths)
            case("v27 browser: Show the whole photo in the window, the shape kept: the largest box of the frame's shape, centred", all(abs(b6[k_] - want_box[k_]) < 0.003 for k_ in ("x", "y", "w", "h")), (b6, want_box))
            c.click("#crop-lock")
            c.click("#crop-all")
            b7 = box()
            case("v27 browser: ... and unticked: the whole photo, edge to edge", {k_: b7[k_] for k_ in ("x", "y", "w", "h")} == {"x": 0, "y": 0, "w": 1, "h": 1}, b7)
            c.click("#crop-lock")
            b8 = box()
            case("v27 browser: ticked again: the box takes the frame's shape around its middle", all(abs(b8[k_] - want_box[k_]) < 0.003 for k_ in ("x", "y", "w", "h")), b8)
            c.click("#crop-cancel")
            c.wait_for("!Designer.crop.isOpen()", 5)
            case("v27 browser: Cancel closes the window and changes nothing", st()["blocks"][0] == _frame(1, 1, 0) and c.js("Designer.crop.box()") is None)
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            hr = c.rect("#crop-box i[data-h=se]")
            c.drag("#crop-box i[data-h=se]", (hr["cx"] - 90, hr["cy"] - 60), steps=8)
            c.click((6, 6))
            c.wait_for("!Designer.crop.isOpen()", 5)
            case("v27 browser: a press beside the window closes it and changes nothing", st()["blocks"][0] == _frame(1, 1, 0) and settled())
            # a zoom past the slider, kept and drawn
            put({"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, zoom=25, ox=0.1, oy=0.1), _frame(2, 2, W + 100, 100, 800, 800)]})
            c.click("#strip .blk[data-id='1']")
            z = Jx("{slider: document.getElementById('zoom-img').value, zoom: Designer.st.blocks[0].zoom}")
            case("v27 browser: a frame at zoom 25 (a 4% crop) is kept by the Assistant and drawn 25 times the frame; the Zoom slider sits at its end, 300",
                 disk()["state"]["blocks"][0]["zoom"] == 25 and z == {"slider": "300", "zoom": 25} and all(abs(v) <= 1.5 for v in img_layout(1).values()), (z, img_layout(1)))
            case("v27 browser: nothing went wrong on the page through the Crop window", not c.page_errors(), c.page_errors()[:3])

            # ================= several photos at once (B13) =================
            def many_state():
                return {"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 100, 100, 400, 500), _frame(2, 2, 600, 80, 380, 500), _frame(3, 3, 150, 700, 500, 380), _text(4, W + 100, 1100), _frame(5, 4, W + 50, 50, 600, 600)]}

            def multi():
                return Jx("Designer.multi")

            def bar():
                return Jx("(function(){ var m = document.getElementById('multibar'); return {shown: !m.hidden && getComputedStyle(m).display !== 'none', n: document.getElementById('multi-n').textContent, "
                          "btns: Array.from(m.querySelectorAll('button')).map(function(b){ return [b.textContent, b.title, b.disabled]; }), hint: m.querySelector('.hint').textContent, line: document.getElementById('multi-line').textContent, "
                          "parent: m.parentNode.id, first: m.parentNode.firstElementChild === m, many: Array.from(document.querySelectorAll('#strip .blk.many')).map(function(e){ return Number(e.dataset.id); })}; })()")

            def pos(bid):
                b = [x for x in st()["blocks"] if x["id"] == bid][0]
                return [b["x"], b["y"]]

            put(many_state())
            rev4 = disk()["rev"]
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='2']", shift=True)
            b1 = bar()
            case("v27 browser: a photo clicked, another Shift-clicked: both are selected, the bar appears inside the stage (its first child, above the labels) saying \"2 selected\", her five buttons with her two tooltips, her hint; the one clicked last has the handles",
                 multi() == [1, 2] and b1["shown"] and b1["n"] == "2 selected" and b1["parent"] == "stage" and b1["first"] and b1["many"] == [1, 2] and b1["hint"] == HERS["many_hint"]
                 and b1["btns"] == [[HERS["even"], HERS["even_title"], False], [HERS["same"], HERS["same_title"], False], [HERS["tops"], "", False], [HERS["remove_them"], "", False], [HERS["done"], "", False]]
                 and c.js("Designer.sel") == 2 and c.js("document.querySelector('.selbox').classList.contains('on')"), (multi(), b1))
            geo = Jx("(function(){ var m = document.getElementById('multibar').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(), l = document.getElementById('labels').getBoundingClientRect(); return {bar: [m.top, m.bottom], stage: s.top, labels: l.top}; })()")
            case("v27 browser: ... the bar sits inside the stage's top and wholly above the slide labels", geo["bar"][0] > geo["stage"] and geo["bar"][1] <= geo["labels"], geo)
            c.click("#strip .blk[data-id='3']", meta=True)
            case("v27 browser: a Cmd-click adds a third: \"3 selected\" (her screenshot 11), the last clicked selected, the selected-photo buttons are its own",
                 multi() == [1, 2, 3] and bar()["n"] == "3 selected" and c.js("Designer.sel") == 3 and not c.js("document.getElementById('sel-photo').hidden"), (multi(), bar()["n"]))
            c.click("#strip .blk[data-id='3']", shift=True)
            case("v27 browser: Shift-click on one of them takes it out: \"2 selected\", the one clicked last of the rest selected", multi() == [1, 2] and bar()["n"] == "2 selected" and c.js("Designer.sel") == 2, (multi(), c.js("Designer.sel")))
            # the bar stays in sight while the tray scrolls under the sticky stage, and while the strip scrolls sideways
            view0 = c.js("Designer.view()")
            c.desktop((1400, 600))
            time.sleep(0.3)
            c.js("window.scrollTo(0, 900)")
            time.sleep(0.3)
            geo = Jx("(function(){ var m = document.getElementById('multibar').getBoundingClientRect(); return {top: m.top, bottom: m.bottom, y: scrollY, h: innerHeight}; })()")
            case("v27 browser: with the photos scrolled far under the sticky stage, the bar is still on screen (inside the stage)", geo["y"] > 500 and geo["top"] >= 0 and geo["bottom"] <= geo["h"], geo)
            c.js("window.scrollTo(0, 0)")
            c.desktop()
            time.sleep(0.3)
            c.js("Designer.setView(480); document.getElementById('stage').style.width = '600px'; document.getElementById('stage').scrollLeft = 400")
            time.sleep(0.2)
            geo = Jx("(function(){ var m = document.getElementById('multibar').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return {left: m.left - s.left, scrolled: document.getElementById('stage').scrollLeft, shown: !document.getElementById('multibar').hidden}; })()")
            case("v27 browser: with the slides drawn large in a narrow stage and the strip scrolled sideways, the bar stays at the stage's left edge (sticky)", geo["scrolled"] > 300 and 0 <= geo["left"] < 40 and geo["shown"] and multi() == [1, 2], geo)
            c.js("document.getElementById('stage').scrollLeft = 0; document.getElementById('stage').style.width = ''; Designer.setView(" + str(view0) + ")")
            time.sleep(0.2)
            # drag one of them: they all move, nothing else does, one step, one save
            r1 = c.rect("#strip .blk[data-id='1']")
            sc = c.js("Designer.scale")
            c.drag("#strip .blk[data-id='1']", (r1["cx"] + 60, r1["cy"] + 40), steps=10)
            m1 = many_state()
            case("v27 browser: a drag on one of the two moves both by the same amount (no snapping), the third photo and the text box stay, both still selected and the dragged one is the one with the handles",
                 abs(pos(1)[0] - (100 + 60 / sc)) < 1.5 and abs(pos(1)[1] - (100 + 40 / sc)) < 1.5 and abs(pos(2)[0] - (600 + 60 / sc)) < 1.5 and abs(pos(2)[1] - (80 + 40 / sc)) < 1.5
                 and pos(3) == [150, 700] and pos(4) == [W + 100, 1100] and multi() == [1, 2] and c.js("Designer.sel") == 1, (pos(1), pos(2), sc))
            case("v27 browser: ... saved as one change (rev + 1)", settled() and disk()["rev"] == rev4 + 1, disk()["rev"])
            c.click("#undo")
            case("v27 browser: Undo puts both back in one step, and the two stay selected", st() == m1 and multi() == [1, 2], (xs(), multi()))
            c.drag("#strip .blk[data-id='1']", (max(5, r1["cx"] - 400), max(5, r1["cy"] - 300)), steps=12)
            got = st()
            case("v27 browser: dragged far off the top left: the pair stops where the first would leave the strip (40 px kept), as far apart as they were (hers let them go off)",
                 all(Jx("DesignModel.onStrip(" + json.dumps(b) + ", 2)") for b in got["blocks"][:2]) and abs((pos(2)[0] - pos(1)[0]) - 500) < 0.02 and abs((pos(2)[1] - pos(1)[1]) - (-20)) < 0.02 and pos(1)[0] <= -300, (pos(1), pos(2)))
            c.click("#undo")
            c.drag("#strip .blk[data-id='2']", (r1["cx"] + 200, r1["cy"] + 100), steps=10, release=False)
            c.key("Escape")
            c.mouse_release()
            case("v27 browser: Escape in the middle of a group drag: the layout as it was", st() == m1 and multi() == [1, 2], xs())
            # the five buttons
            asp = Jx("(function(){ var o = {}; [1, 2].forEach(function(i){ var n = Designer.blockTypes.photo.natural(document.querySelector('#strip .blk[data-id=\"' + i + '\"]'), DesignModel.find(Designer.st, i)); o[i] = n.w / n.h; }); return o; })()")
            want = Jx("DesignModel.evenOut(Designer.st, [1, 2], " + json.dumps(asp) + ")")
            settled()
            rev_e = disk()["rev"]
            c.click("#multibar [data-m=even]")
            case("v27 browser: Even them out: the two laid out by the model's evenOut from the loaded pictures' own shapes (whole, inside the margins), her line in the bar, both still selected",
                 st() == want and st() != m1 and all(abs(b["w"] / b["h"] - asp[str(b["id"])]) < 0.01 and b["zoom"] == 1 and b["y"] >= 40 for b in st()["blocks"][:2]) and bar()["line"] == HERS["evened"] and multi() == [1, 2], (st()["blocks"][:2], bar()["line"]))
            case("v27 browser: ... saved as one change", settled() and disk()["rev"] == rev_e + 1, disk()["rev"])
            c.click("#undo")
            case("v27 browser: Undo puts them back, and the line is gone", st() == m1 and bar()["line"] == "", bar()["line"])
            c.click("#multibar [data-m=size]")
            s2 = st()
            case("v27 browser: Same size: as wide as the one clicked last (photo 2, 380 wide), photo 1 keeping its shape, her line",
                 s2["blocks"][0]["w"] == 380 and abs(s2["blocks"][0]["h"] - 380 * 500 / 400) < 0.02 and s2["blocks"][1] == m1["blocks"][1] and bar()["line"] == HERS["samed"], (s2["blocks"][:2], bar()["line"]))
            c.click("#undo")
            c.click("#multibar [data-m=tops]")
            case("v27 browser: Line up tops: both tops at 80 (the higher), her line", pos(1)[1] == 80 and pos(2)[1] == 80 and pos(1)[0] == 100 and bar()["line"] == HERS["lined"], (pos(1), pos(2), bar()["line"]))
            c.click("#undo")
            # Shift on a corner handle still keeps the shape (a handle press works on the one with the handles and lets the several go, hers)
            hr = c.rect(".selbox .h.br")
            c.drag(".selbox .h.br", (hr["cx"] + 60, hr["cy"] + 10), steps=8, shift=True)
            b2 = st()["blocks"][1]
            case("v27 browser: Shift on a corner handle still resizes the one with the handles alone, keeping its shape; the several are let go", abs(b2["w"] / b2["h"] - 380 / 500) < 0.01 and b2["w"] > 380 and st()["blocks"][0] == m1["blocks"][0] and multi() == [] and bar()["shown"] is False, (b2, multi()))
            c.click("#undo")
            # Backspace, Escape, Done, Remove them
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='2']", shift=True)
            c.click("#strip .blk[data-id='3']", ctrl=True)
            case("v27 browser: (three selected again, Ctrl-click for the third)", multi() == [1, 2, 3] and bar()["n"] == "3 selected", multi())
            c.key("Backspace")
            case("v27 browser: Backspace removes all three in one step: the text box and slide 2's photo stay, nothing selected, the bar gone, her line beside the selected-thing bar",
                 [b["id"] for b in st()["blocks"]] == [4, 5] and c.js("Designer.sel") is None and multi() == [] and bar()["shown"] is False and sel_line() == HERS["removed_them"], ([b["id"] for b in st()["blocks"]], sel_line()))
            c.click("#undo")
            case("v27 browser: Undo brings the three back", st() == m1)
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='2']", shift=True)
            c.key("Escape")
            case("v27 browser: Escape lets the several go: the one clicked last stays selected, the bar is gone", multi() == [] and c.js("Designer.sel") == 2 and bar()["shown"] is False, (multi(), c.js("Designer.sel")))
            c.key("Escape")
            case("v27 browser: ... and a second Escape lets that go too", c.js("Designer.sel") is None)
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='3']", shift=True)
            settled()
            rev_d = disk()["rev"]
            c.click("#multibar [data-m=done]")
            time.sleep(1.0)
            case("v27 browser: Done: the same, by the button; nothing changed, nothing saved", multi() == [] and c.js("Designer.sel") == 3 and st() == m1 and bar()["shown"] is False and disk()["rev"] == rev_d, (multi(), disk()["rev"]))
            weak = Jx("Array.from(document.querySelectorAll('[hidden]')).filter(function(e){ return getComputedStyle(e).display !== 'none'; }).map(function(e){ return e.id || e.className; })")
            case("v27 browser: the hidden bar really disappears (the global [hidden] rule beats its display:flex)", not weak and c.js("getComputedStyle(document.getElementById('multibar')).display") == "none", weak)
            c.click("#strip .blk[data-id='1']", shift=True)
            c.click("#multibar [data-m=del]")
            case("v27 browser: Remove them takes both out, her line, the two others stay", [b["id"] for b in st()["blocks"]] == [2, 4, 5] and sel_line() == HERS["removed_them"] and multi() == [], ([b["id"] for b in st()["blocks"]], sel_line()))
            c.click("#undo")
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='2']", shift=True)
            c.click("#strip .blk[data-id='4']", shift=True)
            case("v27 browser: a text box can be among them (hers)", multi() == [1, 2, 4] and bar()["n"] == "3 selected", multi())
            c.click("#multibar [data-m=even]")
            e3 = st()
            case("v27 browser: Even them out with a text box among them lays out the two photos and leaves the text box where it was", e3["blocks"][3] == m1["blocks"][3] and e3["blocks"][0] != m1["blocks"][0] and e3["blocks"][1] != m1["blocks"][1] and multi() == [1, 2, 4], e3["blocks"][3])
            c.click("#undo")
            c.click("#strip .blk[data-id='5']")
            case("v27 browser: a plain click on another photo lets the several go", multi() == [] and c.js("Designer.sel") == 5 and bar()["shown"] is False, multi())
            c.click("#strip .blk[data-id='1']")
            c.click("#strip .blk[data-id='2']", shift=True)
            c.click("#strip .blk[data-id='3']", shift=True)
            c.js("Designer.setState(function(st){ return DesignModel.act(st, 2, 'del').st; })")
            case("v27 browser: one of three leaving the layout (removed another way) drops out by itself: \"2 selected\"", multi() == [1, 3] and bar()["n"] == "2 selected", multi())
            c.js("Designer.setState(function(st){ return DesignModel.act(st, 3, 'del').st; })")
            case("v27 browser: ... and down to one there are no several: the bar is gone (the one clicked last went with the change, so nothing is selected; hers the same)", multi() == [] and bar()["shown"] is False and c.js("Designer.sel") is None, multi())
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            case("v27 browser: nothing of the several is in the saved record", "multi" not in json.dumps(disk()))
            case("v27 browser: nothing went wrong on the page through several photos at once", not c.page_errors(), c.page_errors()[:3])

            # ================= See a photo big (B14) =================
            def view():
                return Jx("(function(){ var m = document.getElementById('view'); if (!m || m.hidden) return {open: false}; var i = document.getElementById('view-img'); return {open: true, n: Designer.big.n(), src: i.getAttribute('src'), num: document.getElementById('view-num').textContent, "
                          "used: document.getElementById('view-used').textContent, use: document.getElementById('view-use').textContent, close: document.getElementById('view-close').textContent, label: m.querySelector('[role=dialog]').getAttribute('aria-label'), "
                          "prev: document.getElementById('view-prev').getAttribute('aria-label'), next: document.getElementById('view-next').getAttribute('aria-label'), focus: document.activeElement.id, dark: getComputedStyle(m).backgroundColor, loaded: i.naturalWidth > 0}; })()")

            put({"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 100, 100, 800, 800)]})
            rev5 = disk()["rev"]
            tl = Jx("(function(){ var t = document.querySelector('#thumbs .th[data-n=\"5\"]'), b = t.querySelector('button.see'); return {text: b.textContent, title: b.title, label: b.getAttribute('aria-label'), opacity: getComputedStyle(b).opacity, inTile: b.parentNode === t}; })()")
            case("v27 browser: every tray tile has her small ⤢ button (her tooltip, named with the number), out of sight until the pointer is over the tile",
                 tl == {"text": "⤢", "title": HERS["bigger"], "label": "See photo 5 bigger", "opacity": "0", "inTile": True} and c.count("#thumbs .th button.see") == 30, tl)
            c.click("#thumbs .th[data-n='5'] button.see", check=False)
            c.wait_for("Designer.big.isOpen() && document.getElementById('view-img').naturalWidth > 0", 8)
            v = view()
            case("v27 browser: the button opens her dark window: photo 5 big, its number, no \"already\" line (it is not in the design), Use this photo (nothing selected), Close, the arrows named, the window named, Use has the keyboard",
                 v["open"] and v["n"] == 5 and v["num"] == "#5" and v["used"] == "" and v["use"] == HERS["view_use"] and v["close"] == HERS["view_close"] and v["label"] == HERS["view_label"] and v["prev"] == HERS["view_prev"] and v["next"] == HERS["view_next"]
                 and v["focus"] == "view-use" and v["loaded"] and v["dark"].startswith("rgba(12, 12, 14"), v)
            case("v27 browser: the picture is the Assistant's 1600 copy by number, with no path in its address", v["src"].startswith("/kit-photo?") and "n=5&size=l" in v["src"] and no_path(v["src"], target)[0], v["src"])
            time.sleep(0.4)
            case("v27 browser: the tray's single-click wait did not also put photo 5 in (the window's button cancels it)", st()["blocks"][0]["n"] == 1 and len(st()["blocks"]) == 2)
            c.key("ArrowRight")
            c.wait_for("Designer.big.n() === 6", 5)
            c.key("ArrowLeft")
            c.key("ArrowLeft")
            c.wait_for("Designer.big.n() === 4", 5)
            case("v27 browser: the arrow keys browse: right to 6, left twice to 4", view()["num"] == "#4", view())
            c.click("#view-next", check=False)
            c.wait_for("Designer.big.n() === 5", 5)
            c.click("#view-prev", check=False)
            c.wait_for("Designer.big.n() === 4", 5)
            case("v27 browser: ‹ and › do the same", view()["n"] == 4)
            c.key("Escape")
            c.wait_for("!Designer.big.isOpen()", 5)
            case("v27 browser: Escape closes the window; nothing changed, nothing saved", not view()["open"] and st()["blocks"][0]["n"] == 1 and disk()["rev"] == rev5)
            c.double_click("#thumbs .th[data-n='1']")
            c.wait_for("Designer.big.isOpen()", 5)
            v = view()
            case("v27 browser: a double-click on a tile opens it too: photo 1, which says it is already in this design", v["open"] and v["n"] == 1 and v["used"] == HERS["view_used"], v)
            time.sleep(0.5)
            case("v27 browser: ... and the single-click wait did not put photo 1 in as well (nothing added, nothing swapped)", st()["blocks"][0]["n"] == 1 and len(st()["blocks"]) == 2 and c.js("Designer.sel") is None)
            c.key("ArrowLeft")
            c.wait_for("Designer.big.n() === 30", 5)
            c.key("ArrowRight")
            c.wait_for("Designer.big.n() === 1", 5)
            case("v27 browser: the browsing wraps round: left from the first is the last (30), right from there the first", view()["n"] == 1)
            c.click("#view-close", check=False)
            c.wait_for("!Designer.big.isOpen()", 5)
            case("v27 browser: Close closes it", not view()["open"])
            # the strip's selection does not move while the window is open
            c.click("#strip .blk[data-id='2']")
            c.click("#thumbs .th[data-n='7'] button.see", check=False)
            c.wait_for("Designer.big.isOpen()", 5)
            v = view()
            case("v27 browser: with a frame selected the button says Put it in the selected frame", v["use"] == HERS["view_put"] and v["n"] == 7, v)
            c.key("ArrowRight")
            c.wait_for("Designer.big.n() === 8", 5)
            c.key("ArrowLeft")
            c.wait_for("Designer.big.n() === 7", 5)
            case("v27 browser: the arrow keys in the window never move the selected frame", st()["blocks"][1]["x"] == W + 100 and c.js("Designer.sel") == 2, st()["blocks"][1])
            c.click("#view-use", check=False)
            c.wait_for("!Designer.big.isOpen()", 5)
            case("v27 browser: Put it in the selected frame: photo 7 is now in frame 2 (its crop back to the middle), the window closed, the frame still selected",
                 st()["blocks"][1]["n"] == 7 and st()["blocks"][1]["zoom"] == 1 and len(st()["blocks"]) == 2 and c.js("Designer.sel") == 2, st()["blocks"][1])
            case("v27 browser: ... saved as one change", settled() and disk()["rev"] == rev5 + 1, disk()["rev"])
            c.js("Designer.select(null)")
            c.click("#thumbs .th[data-n='9'] button.see", check=False)
            c.wait_for("Designer.big.isOpen()", 5)
            c.click("#view-use", check=False)
            c.wait_for("!Designer.big.isOpen()", 5)
            case("v27 browser: Use this photo with nothing selected adds it as a new slide (as a click in the tray does), and it is the selected one",
                 len(st()["blocks"]) == 3 and st()["blocks"][2]["n"] == 9 and st()["slides"] == 3 and c.js("Designer.sel") == 3, (st()["slides"], [b["n"] for b in st()["blocks"]]))
            c.click("#undo")
            c.js("Designer.select(null)")
            c.click("#thumbs .th[data-n='11'] button.see", check=False)
            c.wait_for("Designer.big.isOpen()", 5)
            c.click((6, 6))
            c.wait_for("!Designer.big.isOpen()", 5)
            case("v27 browser: a press beside the window closes it and changes nothing", len(st()["blocks"]) == 2 and st()["blocks"][1]["n"] == 7)
            # a single click still puts the photo in, a moment later
            before = len(st()["blocks"])
            c.click("#thumbs .th[data-n='12']")
            case("v27 browser: a single click on a tile has not put the photo in at once", len(st()["blocks"]) == before)
            c.wait_for("Designer.st.blocks.length === " + str(before + 1), 5)
            case("v27 browser: ... but after the 230 ms wait it is in (a new slide, as before), and the window is not open", st()["blocks"][before]["n"] == 12 and not view()["open"], [b["n"] for b in st()["blocks"]])
            c.click("#undo")
            c.js("document.querySelector('#thumbs .th[data-n=\"13\"]').focus()")
            c.key("Enter")
            case("v27 browser: Return on a tile reached with the Tab key puts the photo in at once", len(st()["blocks"]) == before + 1 and st()["blocks"][before]["n"] == 13, [b["n"] for b in st()["blocks"]])
            c.click("#undo")
            case("v27 browser: nothing went wrong on the page through See a photo big", not c.page_errors(), c.page_errors()[:3])

            # ================= Save just this slide (B17) =================
            c.open(f"{base}/design.html?kit={KQ}&design={A}")
            ready()
            c.wait_for("Designer.save.idle()", 10)
            put({"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, W + 100, 100, 800, 800)]})
            c.js("Designer.load('" + A + "')")          # opened afresh: no slide clicked yet in this design
            c.wait_for("Designer.save.idle()", 10)
            top = Jx("{text: document.getElementById('save-one').textContent, title: document.getElementById('save-one').title, after: document.getElementById('save-slides').nextElementSibling.id, off: document.getElementById('save-one').disabled}")
            case("v27 browser: the bar's button says \"Save just one slide\" with her tooltip, right after Save slides, on", top == {"text": "Save just one slide", "title": HERS["save_one_top_title"], "after": "save-one", "off": False}, top)
            c.click("#save-one")
            case("v27 browser: pressed with no slide to mean: her line, beside the button, nothing saved", c.text("#save-line") == "Click the slide you want to save first, then press this." and not (kit / "Carousel").is_dir() or not any("updated" in n for n in os.listdir(kit / "Carousel")), c.text("#save-line"))
            c.click("#strip .blk[data-id='2']")
            grp = Jx("(function(){ var b = document.getElementById('save-one-sel'); return {text: b.textContent, title: b.title, last: b.parentNode.lastElementChild === b, group: b.parentNode.id, top: document.getElementById('save-one').textContent}; })()")
            case("v27 browser: a photo on slide 2 selected: the slide group ends with her \"Save just this slide\" (her tooltip), and the bar's button says \"Save just slide 2\"",
                 grp == {"text": HERS["save_one"], "title": HERS["save_one_title"], "last": True, "group": "sel-slides", "top": "Save just slide 2"}, grp)
            car_before = _tree(kit / "Carousel")
            rec_before = (kit / ".kit" / "kit.json").read_bytes()
            c.click("#save-one")
            c.wait_for("/^Saved slide 2 as /.test(document.getElementById('save-line').textContent)", 40, tell="document.getElementById('save-line').textContent")
            line1 = c.text("#save-line")
            m1 = re.search(r'^Saved slide 2 as "(.+?)", in the Beach folder under Carousel\. Nothing else was changed\.$', line1)
            f1 = m1.group(1) if m1 else ""
            data1 = (kit / "Carousel" / f1).read_bytes() if f1 and (kit / "Carousel" / f1).is_file() else b""
            case("v27 browser: Save just slide 2: her saved line, the file \"<the design's name> - slide 02 updated.jpg\" in the Carousel folder, a whole 1080 by 1350 slide, Open folder right after the line",
                 bool(m1) and f1 == disk()["name"] + " - slide 02 updated.jpg" and design.slide_ok(data1) and Jx("document.getElementById('save-line').nextElementSibling.nextElementSibling.nextElementSibling.id") == "open-wrap", (line1, f1, len(data1)))
            case("v27 browser: ... nothing else in the Carousel folder, kit.json byte for byte as it was, the page's design still has no set",
                 {k: v for k, v in _tree(kit / "Carousel").items() if k != f1} == car_before and (kit / ".kit" / "kit.json").read_bytes() == rec_before and Jx("Designer.design.set") is None)
            c.click("#save-one-sel")
            c.wait_for("/updated 2/.test(document.getElementById('save-line').textContent)", 40, tell="document.getElementById('save-line').textContent")
            f2 = disk()["name"] + " - slide 02 updated 2.jpg"
            case("v27 browser: \"Save just this slide\" in the group saves the same slide again as \"updated 2\", the first left as it was",
                 c.text("#save-line") == f'Saved slide 2 as "{f2}", in the Beach folder under Carousel. Nothing else was changed.' and (kit / "Carousel" / f2).is_file() and (kit / "Carousel" / f1).read_bytes() == data1, c.text("#save-line"))
            c.js("document.getElementById('g-bg').querySelector('.sw[data-c=\"#111111\"]').click()")
            case("v27 browser: a change takes the saved line away (it is no longer what is on the slide)", c.text("#save-line") == "", c.text("#save-line"))
            c.click("#undo")
            case("v27 browser: nothing went wrong on the page through Save just this slide", not c.page_errors(), c.page_errors()[:3])

            # ================= + Add photos (B16) =================
            import shutil
            ab = Jx("(function(){ var b = document.getElementById('add-photos'); return {text: b.textContent, title: b.title, next: b.nextElementSibling.id, wrap: b.parentNode.className, line: document.getElementById('add-photos-line').hidden, watching: Designer.addPhotos.watching()}; })()")
            case("v27 browser: \"+ Add photos\" sits right before \"Let my assistant choose the photos\" beside the photos' heading, her tooltip in this computer's words, its line not showing, nothing being asked yet",
                 ab == {"text": HERS["add_photos"], "title": HERS["add_title"].replace("Finder", app), "next": "ask-pick", "wrap": "tray-btns", "line": True, "watching": False}, ab)
            c.js("document.getElementById('g-bg').querySelector('.sw[data-c=\"#f4efe6\"]').click()")       # a change first, so there is an Undo step to keep
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            total0, blocks0 = Jx("Designer.S.total"), len(st()["blocks"])
            c.click("#add-photos")
            c.wait_for("document.getElementById('add-photos-line').textContent.indexOf('is open in') >= 0", 8, tell="document.getElementById('add-photos-line').textContent")
            case("v27 browser: pressed: her line under the heading (the folder opened through the Assistant; nothing opened: the no-windows switch), and the page now looks every 4 seconds",
                 c.text("#add-photos-line") == HERS["add_open"].replace("Finder", app) and Jx("Designer.addPhotos.watching()") and Jx("Designer.addPhotos.EVERY") == 4000, c.text("#add-photos-line"))
            two = sorted(os.listdir(kit / "Photos"))[:2]
            for src, dst in zip(two, ("zz new a.jpg", "zz new b.jpg")):
                shutil.copyfile(kit / "Photos" / src, kit / "Photos" / dst)
                t = time.time() - 30
                os.utime(kit / "Photos" / dst, (t, t))
            c.wait_for("Designer.S.total === " + str(total0 + 2), 25, tell="document.getElementById('add-photos-line').textContent + ' | ' + Designer.S.total")
            tray = Jx("(function(){ var t = Array.from(document.querySelectorAll('#thumbs .th')); return {n: t.length, last: t.slice(-2).map(function(x){ return Number(x.dataset.n); }), name: document.getElementById('trayname').textContent, "
                      "line: document.getElementById('add-photos-line').textContent, undo: !document.getElementById('undo').disabled, blocks: Designer.st.blocks.length, blocked: Designer.blocked, status: document.getElementById('d-status').textContent, note: document.getElementById('d-note').hidden}; })()")
            case("v27 browser: two photos dropped into the Photos folder join the END of the tray with the next two numbers, her line says so, the slides are untouched, Undo is still there, the page is not blocked and asks for no Reload",
                 tray == {"n": total0 + 2, "last": [total0 + 1, total0 + 2], "name": f"All {total0 + 2} photos", "line": f"2 new photos in, at the end of your photos (#{total0 + 1}\u2013{total0 + 2}).",
                          "undo": True, "blocks": blocks0, "blocked": False, "status": "Saved", "note": True}, tray)
            c.wait_for("Designer.by[" + str(total0 + 2) + "] && Designer.by[" + str(total0 + 2) + "].have", 30)
            c.js("Designer.select(null); window.scrollTo(0, document.documentElement.scrollHeight)")      # nothing selected (a click would swap it); the last tile in sight below the sticky stage
            time.sleep(0.3)
            c.click(f"#thumbs .th[data-n='{total0 + 2}']")
            c.wait_for("Designer.st.blocks.length === " + str(blocks0 + 1), 5)
            case("v27 browser: a new photo goes onto the slides like any other, and the design saves with the new list's stamp",
                 settled() and st()["blocks"][-1]["n"] == total0 + 2 and disk()["stamp"] == hashlib.sha1((kit / ".kit" / "sheet.json").read_bytes()).hexdigest()[:12], st()["blocks"][-1])
            c.click("#undo")
            case("v27 browser: Undo still steps back through the changes made before the photos came", len(st()["blocks"]) == blocks0 and Jx("!document.getElementById('undo').disabled"))
            c.wait_for("Designer.save.idle()", 10)
            aside = kit / "Photos-aside"
            aside.mkdir(exist_ok=True)
            shutil.move(str(kit / "Photos" / "zz new b.jpg"), str(aside / "zz new b.jpg"))
            c.wait_for("Designer.blocked === true", 25, tell="document.getElementById('d-note').textContent")
            case("v27 browser: a photo taken out of the folder still stops the page until Reload, as it always has (only additions join without one)",
                 Jx("Designer.blocked") and c.text("#d-note").startswith("The photos in this shoot changed since this page opened.") and Jx("!!document.getElementById('d-reload')"), c.text("#d-note"))
            case("v27 browser: nothing went wrong on the page through + Add photos", not c.page_errors(), c.page_errors()[:3])
            shutil.move(str(aside / "zz new b.jpg"), str(kit / "Photos" / "zz new b.jpg"))

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
            scr = Jx("Array.from(document.querySelectorAll('.bar .crumbs > *')).filter(function(e){ return !e.classList.contains('sep'); }).map(function(e){ return e.textContent; })")
            case("v27 browser: the stories page's path ends in Stories", scr == ["Home", "Beach post kit", "Stories"], scr)
            sab = Jx("(function(){ var b = document.getElementById('add-photos'); return {text: b.textContent, title: b.title, next: b.nextElementSibling.id}; })()")
            case("v27 browser: the stories page has her + Add photos too, before Let my assistant choose", sab == {"text": HERS["add_photos"], "title": HERS["add_title"].replace("Finder", app), "next": "ask-pick"}, sab)
            c.click("#strip .blk")
            sgrp = Jx("{top: document.getElementById('save-one').textContent, title: document.getElementById('save-one').title, sel: document.getElementById('save-one-sel').textContent, selTitle: document.getElementById('save-one-sel').title}")
            case("v27 browser: on the stories page the two buttons say story: \"Save just story 1\" and her \"Save just this story\" (the tooltips in story words, ours)",
                 sgrp == {"top": "Save just story 1", "title": "Save only the story you clicked", "sel": HERS["save_one_story"], "selTitle": "Save only the story this is on, as its own picture"}, sgrp)
            c.click("#save-one")
            c.wait_for("/^Saved story 1 as /.test(document.getElementById('save-line').textContent)", 40, tell="document.getElementById('save-line').textContent")
            ms = re.search(r'^Saved story 1 as "(.+?)", in the Beach folder under Stories\. Nothing else was changed\.$', c.text("#save-line"))
            case("v27 browser: Save just story 1: \"<the set's name> - 01 updated.jpg\" in the Stories folder, a whole 1080 by 1920 story",
                 bool(ms) and ms.group(1) == disk(folder=sdesigns)["name"] + " - 01 updated.jpg" and design.slide_ok((kit / "Stories" / ms.group(1)).read_bytes(), "stories"), c.text("#save-line"))
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
            c.click("#strip .blk[data-id='3']", shift=True)
            mb = Jx("(function(){ var m = document.getElementById('multibar'); return {shown: !m.hidden, n: document.getElementById('multi-n').textContent, titles: Array.from(m.querySelectorAll('button')).map(function(b){ return b.title; }), hint: m.querySelector('.hint').textContent}; })()")
            case("v27 browser: several photos at once on the stories page: the same bar, Even them out's tooltip in story words (ours), the rest hers",
                 mb == {"shown": True, "n": "2 selected", "titles": ["Lay them out tidily on their story, every photo whole", HERS["same_title"], "", "", ""], "hint": HERS["many_hint"]}, mb)
            c.click("#multibar [data-m=even]")
            ev = [b for b in st()["blocks"] if b["id"] in (1, 3)]
            case("v27 browser: Even them out on a story lays the two out on story 1, inside the story's own height and width", all(b["y"] >= 40 and b["y"] + b["h"] <= SH - 40 + 0.01 and b["x"] >= 40 and b["x"] + b["w"] <= SW - 40 + 0.01 for b in ev) and ev[0] != sfour()["blocks"][0], ev)
            c.click("#undo")
            c.click("#strip .blk[data-id='1']")
            grp = Jx("Array.from(document.querySelectorAll('#sel-slides button')).map(function(b){ return [b.textContent, b.title]; })")
            case("v27 browser: the four buttons in her story names, with the tooltips in story words (ours: hers still say slide)",
                 grp == [[HERS["before_story"], "Put a new blank story in front of the one this is on"], [HERS["after_story"], "Put a new blank story right after the one this is on"], [HERS["remove_story"], "Take out the story this is on, and everything on it"],
                         [HERS["save_one_story"], "Save only the story this is on, as its own picture"]], grp)
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
            # Crop on a story: her words in story words, and Done on a story
            c.js("Designer.select(null); Designer.setState(" + json.dumps({"slides": 1, "bg": "#ffffff", "blocks": [_frame(1, 1, 0, h=SH)]}) + ")")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 12)
            c.click("#strip .blk[data-id='1']")
            c.click("#crop-btn")
            c.wait_for("Designer.crop.isOpen() && document.getElementById('crop-img').clientWidth > 0", 8)
            words = Jx("{hint: document.querySelector('#crop p.hint').textContent, lockHint: document.getElementById('crop-hint').textContent, btn: document.getElementById('crop-btn').title}")
            case("v27 browser: Crop on a story: her two hints end in story words (ours), the tooltip hers",
                 words == {"hint": design.story_words(HERS["crop_hint"]), "lockHint": design.story_words(HERS["crop_lock_hint"]), "btn": HERS["crop_title"]} and words["hint"].endswith("on your story."), words)
            hr = c.rect("#crop-box i[data-h=nw]")
            c.drag("#crop-box i[data-h=nw]", (hr["cx"] + 60, hr["cy"] + 90), steps=8)
            c.click("#crop-done")
            c.wait_for("!Designer.crop.isOpen()", 5)
            case("v27 browser: Done on a story: the story's frame as it was, a zoom past 1, her line", st()["blocks"][0]["zoom"] > 1.1 and st()["blocks"][0]["h"] == SH and c.text("#selline") == HERS["cropped"], (st()["blocks"][0], c.text("#selline")))
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
