#!/usr/bin/env python3
"""The stories designer (the designer's second shape, ?kind=stories; Nicole's v19), checked. Run through
tests/design_check.py, which calls the three functions here:

    python3 tests/design_check.py --only stories --port 9500 --work /private/tmp/<new folder>

check_stories_page: her words, word for word, against her v19 page (pages/carousel-designer.html in the handoff),
with the decision-20 changes ("story" for her "slide", "+ Add stories" for "+ New design") checked as changes; the
page's rule scripts run by themselves under the Mac's own JavaScript engine with a story's size (Remove this story,
+ Add stories never replacing anything, One photo per story, the looks, a story's new text) and with a carousel's
(nothing of a carousel changed).

check_stories_server: every route with kind=stories, every refusal, the one stories design a shoot, a story's
looks kept and a carousel's dropped (so a carousel's records are byte for byte as they were), a save from staging
into the Stories folder under "<short> stories - 01.jpg" then "(2)", the kit's record, kit.stories_shown and the
kit page, the line for Claude, the commands with --kind stories, and no path in any answer.

check_stories_browser: the real page in a hidden Chrome: it opens on Add stories, adds never replace, Remove this
story and Undo, the bands, text and its looks, the story fonts, the preview, and Save stories, with every saved story
compared with the screen pixel by pixel (the words in a font the plugin carries, so it works with no internet; the
neon glow given a wider tolerance, since a canvas and a page blur a glow a little differently).

Never the real ~/.studio, never a window, never Finder (the folder button is not pressed).
"""
import io
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
APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
SW, SH = 1080, 1920

# Her words for the stories designer, as her v19 page has them (pages/carousel-designer.html): kept here, so a
# change to the page that drifts from hers is a FAIL. Only the decision-20 changes are allowed (STORY_CHANGED).
HERS = {
    "title": "Stories designer",
    "tab": "Stories Designer",
    "lede": ("Each box is one Instagram story (9:16). Behind the scenes, a sneak peek, a few favorites: make them here instead "
             "of on your phone. The red bands show where Instagram's own buttons sit, so keep your words out of them."),
    "count": "Stories", "bands": "Show Instagram's buttons", "save": "Save stories", "preview": "Preview", "fill": "Fill story",
    "add": "+ Add stories", "remove": "Remove this story", "removeTitle": "Take out the story this is on, and everything on it",
    "look": "Look", "plain": "Plain", "box": "Box", "neon": "Neon", "boxColor": "Box color",
    "topBand": "Instagram\\'s name and buttons", "bottomBand": "Instagram\\'s reply bar",
    "gallery": "Add stories", "subEmpty": "Pick how your first story starts. You can add more any time.",
    "subMore": "Pick what to add. It goes after your last story, and nothing you made is replaced.",
    "secs": ["Start with", "Your templates", "Layouts"], "use": "Add",
    "blank": "Blank story", "blankSub": "An empty white story", "onePer": "One photo per story",
    "reply": "Send message", "ago": "2h", "back": "Back to the post kit", "nav": ["Carousel", "Stories"],
}
FONTS = [("Figtree", "Classic"), ("Archivo Narrow", "Modern"), ("Yellowtail", "Neon"), ("Courier Prime", "Typewriter"),
         ("Anton", "Strong"), ("DM Serif Display", "Editor"), ("Bebas Neue", "Poster"), ("Playfair Display", "Elegant"),
         ("Fredoka", "Bubble"), ("Caveat", "Handwritten"), ("Lora", "Literature")]
GRIDS = [("One photo", 1, 1), ("Two up", 1, 2), ("Three strips", 1, 3), ("Four", 2, 2), ("Six", 2, 3), ("Nine", 3, 3), ("Twelve", 3, 4)]
# decision 20: her "slide" words in stories mode, said as "story" (the screen must not name a slide that isn't there)
STORY_CHANGED = {"Center on slide": "Center on story", "One fewer slide": "One fewer story", "One more slide": "One more story",
                 "How big the slides look": "How big the stories look"}


def _src():
    sys.path.insert(0, str(SCRIPTS))
    import design_page
    return {n: s for n, s in design_page.SCRIPTS}


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


RULES_JS = r"""
var out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
function F(id, n, x, y, w, h){ return {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; }
// ---- a carousel first: no limits written into the page (the old way), and a carousel's own limits ----
(new Function(MODEL_SRC)).call(this); (new Function(PLAN_SRC)).call(this); (new Function(TYPE_SRC)).call(this);
var M = this.DesignModel, P = this.DesignPlan, T = this.DesignType;
t('carousel, no limits on the page: a slide is 1080 by 1350, 1 to 20 slides, the kind is carousel', M.W === 1080 && M.H === 1350 && eq(M.RULES.slides, [1, 20]) && M.KIND === 'carousel' && P.H === 1350 && T.H === 1350);
var nt = T.newText(7, 1, '#ffffff', {text: 'Your words here', font: 'Playfair Display'});
t('carousel: a new text box is exactly as before (Playfair 96, regular, line 1.15, dark ink, no look)',
  eq(nt, {id: 7, type: 'text', text: 'Your words here', font: 'Playfair Display', size: 96, weight: 400, italic: false, upper: false, al: 'center', ls: 0, lh: 1.15, color: '#2a2622', x: 1210, y: 567, w: 820, h: 110.4}), nt);
t('carousel: on a dark background a new text box is white, as before', T.newText(1, 0, '#111111', {}).color === '#ffffff');
this.DESIGN_LIMITS = CAROUSEL_LIMITS;
(new Function(MODEL_SRC)).call(this); (new Function(PLAN_SRC)).call(this); (new Function(TYPE_SRC)).call(this);
M = this.DesignModel; P = this.DesignPlan; T = this.DesignType;
t('carousel, its limits on the page: the same size and the same 1 to 20', M.W === 1080 && M.H === 1350 && eq(M.RULES.slides, [1, 20]) && M.KIND === 'carousel' && eq(P.RULES.slides, [1, 20]));
t('carousel: a one-slide template is one slide (it came out as two before)', P.fromTemplate({slides: 1, bg: '#ffffff', blocks: []}, false).slides === 1);
// ---- stories ----
this.DESIGN_LIMITS = STORY_LIMITS;
(new Function(MODEL_SRC)).call(this); (new Function(PLAN_SRC)).call(this); (new Function(TYPE_SRC)).call(this);
M = this.DesignModel; P = this.DesignPlan; T = this.DesignType;
var W = 1080, H = 1920;
t('stories: the three rule scripts read their size from the page\'s limits: 1080 by 1920', M.W === 1080 && M.H === 1920 && P.W === 1080 && P.H === 1920 && T.W === 1080 && T.H === 1920);
t('stories: the kind is stories and a set holds 1 to 40', M.KIND === 'stories' && eq(M.RULES.slides, [1, 40]) && eq(P.RULES.slides, [1, 40]));
t('stories: 40 stories is as many as a set holds; one is the fewest', M.moreSlides({slides: 40, bg: '#ffffff', blocks: []}).why === 'max' && M.moreSlides({slides: 39, bg: '#ffffff', blocks: []}).st.slides === 40 && M.fewerSlides({slides: 1, bg: '#ffffff', blocks: []}).why === 'min');
t('stories: a thing is kept on the strip by a story\'s height', eq(M.clampXY(0, 5000, 100, 100, 1), {x: 0, y: 1880}) && M.onStrip({x: 0, y: 1880, w: 60, h: 60}, 1) && !M.onStrip({x: 0, y: 1881, w: 60, h: 60}, 1));
t('stories: Fill story makes a frame the whole story', eq(M.act({slides: 2, bg: '#fff', blocks: [F(1, 3, 1200, 100, 300, 300)]}, 1, 'full').st.blocks[0], F(1, 3, 1080, 0, 1080, 1920)));
// Remove this story
var three = {slides: 3, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H), F(2, 2, W, 0, W, H), F(3, 3, W + 100, 300, 300, 300), F(4, 4, 2 * W, 0, W, H),
             {id: 5, type: 'text', text: 'hi', font: 'Figtree', size: 72, weight: 700, italic: false, upper: false, al: 'center', ls: 0, lh: 1.3, color: '#111111', x: 2 * W + 130, y: 806.4, w: 820, h: 93.6, look: 'box', boxColor: '#ffffff'}]};
var r = M.removeStory(three, 1);
t('Remove this story: the story and everything on it go; the stories after it move up', r.st.slides === 2 && eq(r.st.blocks.map(function(b){ return [b.id, b.x]; }), [[1, 0], [4, W], [5, W + 130]]) && r.sel === null, r.st.blocks);
t('Remove this story: what is left is unchanged in every other way (the text keeps its look)', eq(r.st.blocks[2].look, 'box') && r.st.blocks[1].n === 4 && three.blocks.length === 5, r.st.blocks[2]);
r = M.removeStory(three, 2);
t('Remove this story: the last story', r.st.slides === 2 && eq(r.st.blocks.map(function(b){ return b.id; }), [1, 2, 3]));
r = M.removeStory(three, 0);
t('Remove this story: the first story', r.st.slides === 2 && eq(r.st.blocks.map(function(b){ return [b.id, b.x]; }), [[2, 0], [3, 100], [4, W], [5, W + 130]]), r.st.blocks);
r = M.removeStory({slides: 1, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H)]}, 0);
t('Remove this story: at one story nothing changes, and the reason is "one"', r.why === 'one' && r.st.blocks.length === 1);
// + Add stories
var empty = {slides: 1, bg: '#ffffff', blocks: []};
var one = {slides: 1, bg: '#ffffff', blocks: [{id: 1, n: null, x: 0, y: 0, w: W, h: H, ox: 0.5, oy: 0.5, zoom: 1, slot: 1}]};
var photos = [];
for (var i = 1; i <= 12; i++) photos.push({n: i, w: i % 3 ? 1200 : 1800, h: i % 3 ? 1800 : 1200, way: i % 3 ? 'tall' : 'wide'});
var a = P.addStories(empty, one, {});
t('+ Add stories on a shoot\'s first, empty story: it becomes that story', a.st.slides === 1 && a.st.blocks.length === 1 && a.st.blocks[0].x === 0 && a.first === 0, a);
var b2 = P.addStories(a.st, one, {});
t('+ Add stories after that: it goes after the last story, and the first is untouched', b2.st.slides === 2 && b2.st.blocks[1].x === W && eq(b2.st.blocks[0], a.st.blocks[0]) && b2.st.blocks[1].id === 2 && b2.first === 1, b2.st);
var blank = P.addStories(empty, {slides: 1, bg: '#ffffff', blocks: []}, {});
var blank2 = P.addStories(blank.st, {slides: 1, bg: '#ffffff', blocks: []}, {});
t('Blank story on a shoot\'s first, empty story keeps it one empty story, however often it is pressed (hers; the Stories + adds more)', blank.st.slides === 1 && blank2.st.slides === 1 && blank2.st.blocks.length === 0);
t('Blank story after a story with something on it adds one empty story after it', P.addStories(a.st, {slides: 1, bg: '#ffffff', blocks: []}, {}).st.slides === 2);
var withThings = {slides: 2, bg: '#f4efe6', blocks: [F(1, 4, 0, 0, W, H), F(2, 5, W + 40, 40, 500, 500)]};
var nine = {slides: 1, bg: '#ffffff', blocks: []};
for (var r9 = 0; r9 < 3; r9++) for (var c9 = 0; c9 < 3; c9++) nine.blocks.push({id: nine.blocks.length + 1, n: null, x: c9 * 356, y: r9 * 632, w: 352, h: 632, ox: 0.5, oy: 0.5, zoom: 1, slot: nine.blocks.length + 1});
var n9 = P.addStories(withThings, nine, {fill: true, photos: photos, carousel: []});
t('a layout added with photos put in for them: what was there is exactly as it was, and the background stays', eq(n9.st.blocks.slice(0, 2), withThings.blocks) && n9.st.bg === '#f4efe6' && n9.st.slides === 3);
var newOnes = n9.st.blocks.slice(2);
t('...the nine new frames are on the new story, each filled with a photo the stories did not use yet, none twice',
  newOnes.length === 9 && newOnes.every(function(b){ return b.x >= 2 * W && b.n != null && b.n !== 4 && b.n !== 5; }) && newOnes.map(function(b){ return b.n; }).filter(function(n, k, all){ return all.indexOf(n) === k; }).length === 9, newOnes.map(function(b){ return [b.x, b.n]; }));
var holeFirst = {slides: 1, bg: '#ffffff', blocks: [{id: 1, n: null, x: 0, y: 0, w: W, h: H, ox: 0.5, oy: 0.5, zoom: 1, slot: 1}]};
var keep = P.addStories(holeFirst, one, {fill: true, photos: photos, carousel: []});
t('...an empty frame that was already there is left empty (only the new frames are filled)', keep.st.blocks[0].n === null && keep.st.blocks[1].n !== null, keep.st.blocks);
var ids = n9.st.blocks.map(function(b){ return b.id; });
t('...every block has its own id', ids.filter(function(x, k){ return ids.indexOf(x) === k; }).length === ids.length);
var full = {slides: 40, bg: '#ffffff', blocks: [F(1, 1, 0, 0, W, H)]};
t('+ Add stories at 40 stories: nothing is added, and the reason is "max"', P.addStories(full, one, {}).why === 'max' && P.addStories(full, one, {}).st === full);
var crowd = {slides: 2, bg: '#ffffff', blocks: []};
for (var k = 1; k <= 75; k++) crowd.blocks.push(F(k, null, 0, 0, 100, 100));
t('+ Add stories past 80 photos and words: nothing is added, and the reason is "many"', P.addStories(crowd, nine, {}).why === 'many');
var ops = P.onePerStory(withThings, photos);
t('One photo per story: one story each for the next five photos not in a story yet, in number order, each filling its story',
  ops.slides === 5 && ops.blocks.every(function(b, k){ return b.x === k * W && b.w === W && b.h === H; }) && eq(ops.blocks.map(function(b){ return b.n; }), [1, 2, 3, 6, 7]), ops.blocks.map(function(b){ return b.n; }));
t('One photo per story with fewer than five left: as many as are left', P.onePerStory(n9.st, photos).slides === 1 && P.onePerStory(n9.st, photos).blocks[0].n === 12);
var allUsed = {slides: 1, bg: '#ffffff', blocks: photos.map(function(p, k){ return F(k + 1, p.n, 0, 0, 100, 100); })};
var none = P.onePerStory(allUsed, photos);
t('One photo per story with every photo used: one story with an empty frame (hers)', none.slides === 1 && none.blocks.length === 1 && none.blocks[0].n === null);
// a story's new text and its looks
var st0 = T.newText(9, 2, '#ffffff', STORY_TEXT);
t('a story\'s new text: Classic (Figtree), bold, 72, line height 1.3, black on a white box, in the middle of story 3',
  st0.font === 'Figtree' && st0.size === 72 && st0.weight === 700 && st0.lh === 1.3 && st0.color === '#111111' && st0.look === 'box' && st0.boxColor === '#ffffff'
  && st0.x === 2 * W + 130 && st0.y === 806.4 && st0.h === 93.6, st0);
t('contrast: black words on a light box, white on a dark one', T.contrast('#ffffff') === '#111111' && T.contrast('#111111') === '#ffffff' && T.contrast('#c4683f') === '#ffffff' && T.contrast('#ffd84d') === '#111111' && T.contrast('nope') === '#111111');
t('lighten: 65% toward white', T.lighten('#ff0000', 0.65) === '#ffa6a6' && T.lighten('#000000', 0.65) === '#a6a6a6' && T.lighten('bad', 0.65) === '#ffffff', [T.lighten('#ff0000', 0.65), T.lighten('#000000', 0.65)]);
t('the box: padding 0.3 of the size, corners 0.22 of it; neon blurs 0.06, 0.18, 0.36; core 65% toward white',
  T.boxPad({size: 100}) === 30 && Math.abs(T.boxRad({size: 100}) - 22) < 1e-9 && eq(T.NEON.blurs, [0.06, 0.18, 0.36]) && T.NEON.core === 0.65);
var plainRed = {look: 'plain', color: '#e02020', boxColor: '#ffffff'};
t('Plain to Box: the text\'s color becomes the box\'s, and the words go white on it (like Instagram)', eq(T.lookChange(plainRed, 'box'), {look: 'box', boxColor: '#e02020', color: '#ffffff'}), T.lookChange(plainRed, 'box'));
t('Neon to Box: a white box with black words', eq(T.lookChange({look: 'neon', color: '#ff5aa8'}, 'box'), {look: 'box', boxColor: '#ffffff', color: '#111111'}));
t('Box to Plain or Neon: the words take the box\'s color', eq(T.lookChange({look: 'box', color: '#ffffff', boxColor: '#2f7cf6'}, 'plain'), {look: 'plain', color: '#2f7cf6'}) && eq(T.lookChange({look: 'box', color: '#111111', boxColor: '#ffd84d'}, 'neon'), {look: 'neon', color: '#ffd84d'}));
t('Plain to Neon keeps the color; a look that is not one is refused', eq(T.lookChange({color: '#123456'}, 'neon'), {look: 'neon'}) && T.lookChange({}, 'glitter') === null);
t('the box color as one change: the words go black or white on it', eq(T.style({}, 'boxColor', '#FFD84D'), {boxColor: '#ffd84d', color: '#111111'}) && T.style({}, 'boxColor', 'red') === null);
t('a box behind the lines does not change where they break (the line breaks do not read the look)', T.sig({font: 'Figtree', size: 72, text: 'a', w: 800, lh: 1.3, al: 'center'}) === T.sig({font: 'Figtree', size: 72, text: 'a', w: 800, lh: 1.3, al: 'center', look: 'neon'}));
JSON.stringify(out);
"""


def check_stories_page(case, work):
    sys.path.insert(0, str(SCRIPTS))
    import design
    import design_page
    src = _src()
    story = design_page.page_html("2026-11-01 Fake beach", "stories")
    car = design_page.page_html("2026-11-01 Fake beach")
    allsrc = "".join(src.values())
    # ---- her words, word for word ----
    for k in ("title", "lede", "count", "bands", "save", "preview"):
        case(f"stories page: her words: {HERS[k][:70]}", HERS[k].replace("'", "&#x27;") in story or HERS[k] in story, HERS[k])
    case("stories page: the tab says her \"Stories Designer\"", f"<title>{HERS['tab']}" in story)
    case("stories page: the Carousel / Stories switch beside the title, Stories marked as the one open",
         re.search(r"<span class='kindnav' id='kindnav'><a href='/design\.html\?kit=2026-11-01%20Fake%20beach'>Carousel</a><a href='/design\.html\?kit=2026-11-01%20Fake%20beach&amp;kind=stories' class='on' aria-current='page'>Stories</a></span>", story) is not None)
    case("carousel page: the same switch, Carousel marked", "<a href='/design.html?kit=2026-11-01%20Fake%20beach' class='on' aria-current='page'>Carousel</a>" in car)
    case("both pages: \"← Back to the post kit\" (her words, with her arrow)", all("<span class='arr' aria-hidden='true'>&larr;</span>Back to the post kit</a>" in p for p in (story, car)))
    case("stories page: the bands' tick is on to start with (hers)", "id='gridcrop' checked aria-label=\"Show Instagram's buttons\"" in story or "id='gridcrop' checked aria-label='Show Instagram&#x27;s buttons'" in story, re.findall(r"id='gridcrop'[^>]*>", story))
    case("stories page: the folder's button is Open the Stories folder", ">Open the Stories folder</button>" in story)
    for her, ours in STORY_CHANGED.items():
        case(f"decision 20: \"{her}\" is \"{ours}\" on the stories page", ours in story or ours in allsrc, ours)
    for k in ("add", "remove", "removeTitle", "look", "plain", "box", "neon", "boxColor", "topBand", "bottomBand", "gallery", "subEmpty", "subMore",
              "use", "blank", "blankSub", "onePer", "reply", "ago", "fill"):
        case(f"page scripts: her words: {HERS[k][:70]}", ("'" + HERS[k] + "'") in allsrc or HERS[k] in allsrc, HERS[k])
    case("page scripts: her three section names in Add stories: Start with, Your templates, Layouts",
         "secFresh: 'Start with'" in allsrc and "secMine: 'Your templates'" in allsrc and "secStarters: 'Layouts'" in allsrc)
    case("page scripts: the preview's top bar and reply bar (♡ and ➤, her marks)", "'♡'" in allsrc and "'➤'" in allsrc and "'×'" in allsrc)
    case("page scripts: never her own handle anywhere", "nicolelhill" not in allsrc + story)
    # ---- the carousel page is as it was ----
    for w in ("Stories designer", "Show Instagram", "Save stories", "data-kind='stories'", "Instagram's name"):
        case(f"carousel page: nothing of stories in it ({w})", w not in car)
    lim = json.loads(re.search(r"window\.DESIGN_LIMITS=(\{.*?\});</script>", car).group(1))
    case("carousel page: the limits written into it are exactly the carousel's (LIMITS, 1080 by 1350, 1 to 20)", lim == design.LIMITS and lim["h"] == 1350, lim)
    slim = json.loads(re.search(r"window\.DESIGN_LIMITS=(\{.*?\});</script>", story).group(1))
    case("stories page: its limits: 1080 by 1920, 1 to 40, the bands at 250 and 340, kind stories",
         slim["w"] == SW and slim["h"] == SH and slim["slides"] == [1, 40] and slim["safe"] == [250, 340] and slim["kind"] == "stories", slim)
    case("stories page: the limits come before every script, so each script reads its size from them",
         story.index("window.DESIGN_LIMITS=") < story.index("DesignModel"))
    # ---- design.py's own tables ----
    case("her story fonts, in her order, each with her nickname", [(n, k) for n, _, k in design.STORY_FONTS] == FONTS, design.STORY_FONTS)
    ff = design.fonts_for_page("stories")
    case("a story's font list starts with the story fonts (\"Story fonts\"), then the carousel's groups; the carousel's list is as it was",
         ff["groups"][0]["name"] == "Story fonts" and [f["nick"] for f in ff["groups"][0]["fonts"]] == [k for _, k in FONTS]
         and [g["name"] for g in ff["groups"][1:]] == ["Serif", "Sans", "Script"] and [g["name"] for g in design.fonts_for_page()["groups"]] == ["Serif", "Sans", "Script"]
         and ff["default"] == "Figtree" and design.fonts_for_page()["default"] == "Playfair Display")
    st = design.STORY_STARTERS
    ok = [x["name"] for x in st] == [g[0] for g in GRIDS] and len(st) == 7
    for x, (_, cols, rows) in zip(st, GRIDS):
        fr = x["template"]["blocks"]
        right = max(b["x"] + b["w"] for b in fr)
        bottom = max(b["y"] + b["h"] for b in fr)
        gaps = sorted({round(b2["x"] - (b1["x"] + b1["w"]), 6) for b1 in fr for b2 in fr if b2["y"] == b1["y"] and b2["x"] > b1["x"] and abs(b2["x"] - (b1["x"] + b1["w"]) - 12) < 1})
        ok = ok and len(fr) == cols * rows and x["template"]["slides"] == 1 and x["template"]["bg"] == "#ffffff" and right == SW and bottom == SH and all(b["n"] is None for b in fr) and (cols == 1 or gaps == [12])
    case("her seven layouts: One photo, Two up, Three strips, Four, Six, Nine, Twelve; edge to edge, 12 px apart, white, empty frames", ok, [(x["name"], len(x["template"]["blocks"])) for x in st])
    # ---- the rule scripts by themselves ----
    js = work / "stories-rules.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar PLAN_SRC = " + json.dumps(src["DESIGN_PLAN_JS"]) + ";\nvar TYPE_SRC = "
                  + json.dumps(src["DESIGN_TYPE_JS"]) + ";\nvar CAROUSEL_LIMITS = " + json.dumps(design.limits_for("carousel")) + ";\nvar STORY_LIMITS = "
                  + json.dumps(design.limits_for("stories")) + ";\nvar STORY_TEXT = " + json.dumps(dict(design.STORY_TEXT, text="Your words here")) + ";\n"
                  + RULES_JS, encoding="utf-8")
    r = osascript(js)
    try:
        got = json.loads(r.stdout.strip())
    except ValueError:
        got = None
    if case("the stories rules ran to the end under osascript", isinstance(got, list) and len(got) >= 30, (r.stderr or r.stdout)[-500:]):
        for name, ok, detail in got:
            case("rules: " + name, ok, detail)


def _tree(folder, skip=()):
    import hashlib
    out = {}
    folder = Path(folder)
    if not folder.is_dir():
        return out
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and not any(rel == x or rel.startswith(x + "/") for x in skip):
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


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


def check_stories_server(case, work, port, make_kit, Server, post, get_json, ask, run, jpeg):
    target = work / "stories"
    ok, out = make_kit(target, "Fake beach", 12)
    if not case("stories: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    ok, out = make_kit(target, "Other day", 8)
    case("stories: a second pretend kit", ok, out)
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    content = target / "The Assistant" / "Your Content"
    kit_name = "2026-11-01 Fake beach"
    kit = content / kit_name
    KQ = quote(kit_name)
    rec_file = kit / ".kit" / "kit.json"
    sdesigns = kit / ".kit" / "story-designs"
    cdesigns = kit / ".kit" / "designs"
    stories_dir = kit / "Stories"
    code, out = run(env, "kit.py", "picks", kit_name, "--stories", "1,2,3")
    code, out = run(env, "kit.py", "build", kit_name)
    case("stories: kit.py build made the plain stories first (MAKE_PLAIN_STORIES), so the Stories folder is not empty",
         code == 0 and len(list(stories_dir.glob("Story *.jpg"))) >= 2, out[-300:])
    (stories_dir / "Story 01 (Canva).jpg").write_bytes(jpeg(SW, SH, seed=801))
    (stories_dir / "my own story.jpg").write_bytes(jpeg(SW, SH, seed=802))
    stories_before = _tree(stories_dir)
    photos_before = _tree(kit / "Photos")
    seen = []

    def J(code_and):
        seen.append(code_and[1])
        return code_and

    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (stories: page server on port {P}, STUDIO_HOME={studio})", flush=True)
        # ---------- the page and the state ----------
        code, h, data = ask(P, "GET", f"/design.html?kit={KQ}&kind=stories")
        page = data.decode("utf-8", "replace")
        case("stories page: /design.html?kind=stories is the stories designer, its size written in", code == 200 and "data-kind='stories'" in page and '"h":1920' in page and "<title>Stories Designer" in page, page[:300])
        code, h, data = ask(P, "GET", f"/design.html?kit={KQ}&kind=reels")
        sys.path.insert(0, str(SCRIPTS))
        import arrange as arrange_mod
        case("stories page: a kind that is not one gets a plain page in plain words, not an error and not the designer",
             code == 200 and b"DesignModel" not in data and arrange_mod.NOT_UNDERSTOOD.encode("utf-8") in data.replace(b"&#x27;", b"'"), data[-400:])
        code, st = J(get_json(P, f"/design-state?kit={KQ}&kind=reels"))
        case("state: kind=reels is refused (400, plain words)", code == 400 and st and st.get("ok") is False and st.get("words"), (code, st))
        case("state: before the first visit there are no stories designs", not sdesigns.exists() or not list(sdesigns.glob("*.json")))
        code, st = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        if not case("state: the first visit to the stories answers", code == 200 and st and st.get("ok") is True and st.get("kind") == "stories", (code, st and st.get("words"))):
            return
        d = st["design"]
        DID, STAMP = d["id"], st["stamp"]
        case("state: the shoot's one stories design is made empty: one white story, nothing on it, called \"<shoot> stories\"",
             d["state"] == {"slides": 1, "bg": "#ffffff", "blocks": []} and d["name"] == "Fake beach stories" and (sdesigns / f"{DID}.json").is_file(), d)
        case("state: the stories design is kept apart from the carousel's (no carousel design was made by it)", not cdesigns.exists() or not list(cdesigns.glob("*.json")))
        case("state: a story's limits (1080 by 1920, 1 to 40, the bands at 250 and 340)", st["limits"]["h"] == SH and st["limits"]["slides"] == [1, 40] and st["limits"]["safe"] == [250, 340], st["limits"])
        case("state: her seven layouts are the starters", [x["name"] for x in st["starters"]] == [g[0] for g in GRIDS])
        case("state: a new text box starts the way hers does (Figtree, bold, 72, 1.3, black on a white box)",
             st["text"] == {"font": "Figtree", "size": 72, "weight": 700, "color": "#111111", "look": "box", "boxColor": "#ffffff", "lh": 1.3, "text": "Your words here"}, st["text"])
        case("state: the preview's name is \"yourname\" while their handle isn't known (decision 18), never hers", st["handle"] == "yourname" and "nicolelhill" not in json.dumps(st))
        case("state: the blank story and the photos to fill from: white, in number order (no carousel order)", st["blank"] == {"slides": 1, "bg": "#ffffff", "blocks": []} and st["carousel"] == [] and st["slide_bg"] == "#ffffff")
        # the empty white story the visit made is not a design of theirs until it is changed (hers saves nothing until then)
        case("state: the shoot menu counts story designs apart from carousel designs, and not the empty one a visit made",
             next(x for x in st["shoots"] if x["kit"] == kit_name)["story_designs"] == 0 and next(x for x in st["shoots"] if x["kit"] == kit_name)["designs"] == 0,
             next(x for x in st["shoots"] if x["kit"] == kit_name))
        code, st2 = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        case("state: asked again, the same one design (never a second)", code == 200 and st2["design"]["id"] == DID and len(list(sdesigns.glob("*.json"))) == 1)
        code, st3 = J(get_json(P, f"/design-state?kit={KQ}&kind=stories&design=dnosuchdesign1"))
        case("state: one stories design a shoot: any design asked for gives that one, with nothing said", code == 200 and st3["design"]["id"] == DID and st3["fell_back"] is False)
        (studio / "feed.json").write_text(json.dumps({"handle": "my.studio_photos", "read_at": None, "posts": []}), encoding="utf-8")
        code, st4 = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        case("state: their handle from the grid they had read is the preview's name", st4["handle"] == "my.studio_photos", st4.get("handle"))
        (studio / "feed.json").write_text(json.dumps({"handle": "<b>me</b>"}), encoding="utf-8")
        code, st4 = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        case("state: a handle that is not one is never shown (\"yourname\" instead)", st4["handle"] == "yourname", st4.get("handle"))
        code, cst = J(get_json(P, f"/design-state?kit={KQ}"))
        case("state: the carousel's state has no kind, no handle, and its own design", code == 200 and "kind" not in cst and "handle" not in cst and cst["design"]["id"] != DID and cst["limits"]["h"] == 1350)

        # ---------- saving: a story's looks are kept; a carousel's are dropped ----------
        rev = [0]

        def body(state, **over):
            b = {"kit": kit_name, "kind": "stories", "design": DID, "stamp": STAMP, "base": rev[0], "page": "storypage01", "state": state}
            b.update(over)
            return b

        def frame(i, n, x, y=0, w=SW, h=SH):
            return {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}

        def text(i, words, x, y, look=None, box=None, color="#111111"):
            t = {"id": i, "type": "text", "text": words, "font": "Inter", "size": 72, "weight": 700, "italic": False, "upper": False, "al": "center",
                 "ls": 0, "lh": 1.3, "color": color, "x": x, "y": y, "w": 820, "h": 93.6}
            if look:
                t["look"] = look
            if box:
                t["boxColor"] = box
            return t

        S1 = {"slides": 3, "bg": "#ffffff", "blocks": [frame(1, 1, 0), frame(2, 2, SW), frame(3, 3, 2 * SW),
                                                        text(4, "behind the scenes", 130, 400, "box", "#FFD84D"), text(5, "more soon", SW + 130, 900, "neon", None, "#ff5aa8"),
                                                        text(6, "plain", 2 * SW + 130, 1200, "plain")]}
        code, out = J(post(P, "/design", body(S1)))
        if case("save: a story's layout of three stories is taken", code == 200 and out.get("ok") and out.get("rev") == 1, (code, out)):
            rev[0] = 1
        on = json.loads((sdesigns / f"{DID}.json").read_text(encoding="utf-8"))["state"]
        tb = [b for b in on["blocks"] if b.get("type") == "text"]
        case("save: each text keeps its look, the box's color is written in small letters", [b.get("look") for b in tb] == ["box", "neon", "plain"] and tb[0]["boxColor"] == "#ffd84d" and "boxColor" not in tb[1], tb)
        for name, change in (("a look that is not one", lambda st: st["blocks"][3].update(look="glitter")),
                             ("a box color that is not a color", lambda st: st["blocks"][3].update(boxColor="yellow")),
                             ("41 stories", lambda st: st.update(slides=41)),
                             ("a frame below the bottom of a story", lambda st: st["blocks"][0].update(y=1900))):
            bad = json.loads(json.dumps(S1))
            change(bad)
            code, out = J(post(P, "/design", body(bad)))
            case(f"save refused: {name}", code == 400 and out.get("ok") is False and out.get("words"), (code, out))
        code, out = J(post(P, "/design", body(S1, kind="reels")))
        case("save refused: a kind that is not one", code == 400 and out.get("why") == "kind", (code, out))
        code, out = J(post(P, "/design", body(S1, kind="carousel")))
        case("save refused: a story's design sent as a carousel's is not found there (the two are kept apart)", code == 404 and out.get("why") == "design", (code, out))
        tall = json.loads(json.dumps(S1))
        tall["blocks"][0].update(h=1920, y=0)
        cs = cst["design"]["state"]
        cbody = {"kit": kit_name, "design": cst["design"]["id"], "stamp": STAMP, "base": cst["design"]["rev"], "page": "carpage0001",
                 "state": {"slides": cs["slides"], "bg": cs["bg"], "blocks": cs["blocks"] + [dict(text(90, "words", 100, 300, "neon", "#ffffff"))]}}
        code, out = J(post(P, "/design", cbody))
        cdisk = json.loads((cdesigns / f"{cst['design']['id']}.json").read_text(encoding="utf-8"))["state"]
        ct = [b for b in cdisk["blocks"] if b.get("type") == "text"]
        case("carousel: a look sent with a carousel's text is dropped like any unknown key: its record is as it always was",
             code == 200 and len(ct) == 1 and "look" not in ct[0] and "boxColor" not in ct[0] and sorted(ct[0]) == sorted(["id", "type", "text", "font", "size", "weight", "italic", "upper", "al", "ls", "lh", "color", "x", "y", "w", "h"]), (code, ct))
        car_tall = {"kit": kit_name, "design": cst["design"]["id"], "stamp": STAMP, "base": cst["design"]["rev"] + 1, "page": "carpage0001",
                    "state": {"slides": 1, "bg": "#ffffff", "blocks": [frame(1, 1, 0, 0, 1080, 1920)]}}
        code, out = J(post(P, "/design", car_tall))
        case("carousel: a frame as tall as a story is refused on a carousel (its size is 1350)", code == 400, (code, out))
        code, out = J(post(P, "/design-new", {"kit": kit_name, "kind": "stories", "token": "newstory0001"}))
        case("new design: a second stories design is refused (one a shoot), in plain words", code == 409 and out.get("why") == "one" and "+ Add stories" in out.get("words", ""), (code, out))
        code, out = J(post(P, "/design-new", {"kit": kit_name, "kind": "stories", "copy": DID, "token": "newstory0002"}))
        case("new design: a copy of the stories is refused too", code == 409 and out.get("why") == "one", (code, out))
        case("new design: still one stories design on the drive", len([f for f in sdesigns.glob("*.json") if not f.name.endswith(".prev.json")]) == 1)

        # ---------- templates: a story's kept apart ----------
        code, out = J(post(P, "/design-template", {"kit": kit_name, "kind": "stories", "token": "tplstory0001", "name": "My grid", "state": S1}))
        tfiles = list((studio / "story-templates").glob("*.json"))
        case("template: a story's template is saved in story-templates, its photos taken out, its looks kept, and the line names + Add stories",
             code == 200 and len(tfiles) == 1 and all(b.get("n") is None for b in out["template"]["template"]["blocks"] if b.get("type") != "text")
             and [b.get("look") for b in out["template"]["template"]["blocks"] if b.get("type") == "text"] == ["box", "neon", "plain"]
             and out["words"] == "Saved \"My grid\" to your templates. You'll find it under + Add stories, in any shoot." and not (studio / "design-templates").exists(), (code, out))
        code, sst = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        code2, cst2 = J(get_json(P, f"/design-state?kit={KQ}"))
        case("template: listed for stories, not for the carousel", [t["name"] for t in sst["templates"]] == ["My grid"] and cst2["templates"] == [])

        # ---------- slides: a story's size ----------
        staging = kit / ".kit" / "story-staging"
        JH = {"Content-Type": "image/jpeg"}
        STORIES = [jpeg(SW, SH, seed=i) for i in range(1, 8)]

        def slide(tok, i, of, data, kind="stories"):
            code, _, out = ask(P, "POST", f"/design-slide?kit={KQ}&design={DID}&set={tok}&i={i}&of={of}" + (f"&kind={kind}" if kind else ""), body=data, headers=JH)
            try:
                o = json.loads(out)
            except ValueError:
                o = None
            seen.append(o)
            return code, o

        code, out = slide("storyset0001", 1, 3, jpeg(1080, 1350, seed=3))
        case("slide refused: a carousel's 1080 by 1350 sent as a story", code == 400 and out and out.get("ok") is False, (code, out))
        code, out = slide("storyset0001", 1, 41, STORIES[0])
        case("slide refused: story 1 of 41", code == 400, (code, out))
        code, out = slide("storyset0001", 1, 3, STORIES[0], kind="reels")
        case("slide refused: a kind that is not one", code == 400 and out.get("why") == "kind", (code, out))
        code, out = slide("storyset0001", 1, 3, STORIES[0], kind=None)
        case("slide refused: a story sent as a carousel's slide (no such carousel design)", code in (400, 404), (code, out))
        oks = [slide("storyset0001", i, 3, STORIES[i - 1])[0] for i in (1, 2, 3)]
        case("slides: three finished 1080 by 1920 stories are taken, into the stories' own staging only",
             oks == [200, 200, 200] and len(list((staging / f"{DID}-storyset0001").glob("slide-*.jpg"))) == 3 and _tree(stories_dir) == stories_before
             and not (kit / ".kit" / "design-staging").exists(), oks)

        def commit(tok, **more):
            b = {"kit": kit_name, "kind": "stories", "design": DID, "set": tok, "rev": rev[0]}
            b.update(more)
            return J(post(P, "/design-commit", b))

        code, out = commit("storyset0001", kind="carousel")
        case("commit refused: the stories' set sent as a carousel's", code == 404, (code, out))
        code, out = commit("storyset0001", count=41)
        case("commit refused: 41 stories", code == 400, (code, out))
        code, out = commit("storyset0001", count=3)
        names = [f"Fake beach stories - {i:02d}.jpg" for i in (1, 2, 3)]
        case("Save stories: the set goes into the Stories folder as \"Fake beach stories - 01.jpg\" (decision 17), and the line says so",
             code == 200 and out.get("ok") and out.get("base") == "Fake beach stories" and out.get("words") == 'Saved 3 stories in your Stories folder, named "Fake beach stories". Nothing was replaced.', (code, out))
        case("Save stories: each file is byte for byte the story that was sent", all((stories_dir / n).is_file() and (stories_dir / n).read_bytes() == STORIES[i] for i, n in enumerate(names)))
        now = _tree(stories_dir)
        case("Save stories: nothing that was in the Stories folder changed (plain stories, Canva's, their own)", all(now.get(k) == v for k, v in stories_before.items()))
        case("Save stories: the Carousel folder and the photos are as they were", _tree(kit / "Photos") == photos_before and not list((kit / "Carousel").glob("Fake beach stories*")))
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("the kit's record: stories_set names this set, stories_laid_out has it, and the carousel's keys are not touched",
             rec["stories_set"]["kind"] == "laid-out" and rec["stories_set"]["files"] == names and rec["stories_laid_out"][0]["base"] == "Fake beach stories"
             and "carousel_set" not in rec and "laid_out" not in rec, {k: rec.get(k) for k in ("stories_set", "carousel_set", "laid_out")})
        code, out = commit("storyset0001", count=3)
        case("Save stories again with the same press: the same answer, nothing new", code == 200 and out.get("ok") and len(list(stories_dir.glob("Fake beach stories*"))) == 3, (code, out))
        sys.path.insert(0, str(SCRIPTS))
        os.environ["STUDIO_HOME"] = str(studio)
        import importlib
        import kit as kit_mod
        importlib.reload(kit_mod)
        sh = kit_mod.stories_shown(kit)
        case("kit.stories_shown: the newest saved set, in order", sh["kind"] == "laid-out" and [p.name for p in sh["files"]] == names and sh["others"] >= 3, sh)
        code, outp = run(env, "kit.py", "page", kit_name) if False else (0, "")
        kit_mod.write_page(kit)
        kpage = (kit / ".kit" / "Post kit.html").read_text(encoding="utf-8")
        m = re.search(r"<a class='piece' data-piece='stories' href='([^']*)'>(.*?)</a>", kpage, re.S)
        href, sect = (m.group(1), m.group(2)) if m else ("", "")
        case("the kit page's Stories card (her post kit) shows the saved set, counts it, and is her \"Open my stories →\" link to the stories designer",
             all(f"Stories/{n}" in sect for n in names) and "Story 01 (" not in sect and "3 stories saved in the Stories folder \u00b7 1 saved design" in sect
             and href == f"/design.html?kit={quote(kit_name)}&amp;kind=stories" and "<span class='cta'>Open my stories &rarr;</span>" in sect, sect[:700])
        code, outw = run(env, "home.py", "pending")
        case("the line for Claude: ARRANGED: <kit> | stories | 3 stories | Fake beach stories", "ARRANGED: 2026-11-01 Fake beach | stories | 3 stories | Fake beach stories" in outw, outw[-300:])
        code, outt = run(env, "design.py", "took", kit_name)
        code2, outw2 = run(env, "home.py", "pending")
        case("design.py took without --kind clears only a carousel's line (the stories' line stays)", "| stories |" in outw2, outw2[-200:])
        code, outt = run(env, "design.py", "took", kit_name, "--kind", "stories")
        code2, outw2 = run(env, "home.py", "pending")
        case("design.py took --kind stories clears it", code == 0 and "Cleared" in outt and "| stories |" not in outw2, (outt, outw2[-200:]))
        # a change, then Save stories again: "(2)"
        S2 = json.loads(json.dumps(S1))
        S2["bg"] = "#111111"
        code, out = J(post(P, "/design", body(S2)))
        rev[0] = out.get("rev", rev[0])
        for i in (1, 2, 3):
            slide("storyset0002", i, 3, STORIES[i + 2])
        code, out = commit("storyset0002", count=3)
        names2 = [f"Fake beach stories (2) - {i:02d}.jpg" for i in (1, 2, 3)]
        case("Save stories after a change: a new set beside the first, \"Fake beach stories (2) - 01.jpg\", nothing replaced",
             code == 200 and out.get("base") == "Fake beach stories (2)" and all((stories_dir / n).read_bytes() == STORIES[i + 3] for i, n in enumerate(names2))
             and all((stories_dir / n).read_bytes() == STORIES[i] for i, n in enumerate(names)), (code, out))
        code, out = commit("storyset0003", count=3)
        case("Save stories with nothing changed: \"Already saved as ...\", no file made", code == 200 and out.get("already") is True and out.get("words") == 'Already saved as "Fake beach stories (2)". Change something to save a new set.'
             and len(list(stories_dir.glob("Fake beach stories*"))) == 6, (code, out))
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("the kit shows the newest set", rec["stories_set"]["base"] == "Fake beach stories (2)" and kit_mod.stories_shown(kit)["base"] == "Fake beach stories (2)")
        # ---------- the commands ----------
        code, outs = run(env, "design.py", "show", kit_name, "--kind", "stories")
        case("design.py show --kind stories lists the stories and both saved sets, in a story's words",
             code == 0 and "\"Fake beach stories\"  3 stories" in outs and "Stories: \"Fake beach stories (2)\", 3 stories" in outs and "slide" not in outs.lower(), outs[-600:])
        code, outo = run(env, "design.py", "open", "Other day", "--kind", "stories")
        case("design.py open --kind stories on a shoot with none: NEW, the stories made empty, and the address with kind=stories",
             code == 0 and "NEW:" in outo and outo.strip().splitlines()[-1].endswith("/design.html?kit=2026-11-01%20Other%20day&kind=stories"), outo[-500:])
        code, outo = run(env, "design.py", "open", kit_name, "--kind", "stories")
        case("design.py open --kind stories on a shoot that has them: THEIRS", code == 0 and "THEIRS:" in outo and "3 stories" in outo, outo[-400:])
        code, outo = run(env, "design.py", "open", kit_name, "--kind", "reels")
        case("design.py open --kind reels: refused, nothing made", code != 0, outo[-200:])
        # ---------- no path in any answer ----------
        bad = [x for o in seen if o is not None for x in _strings(o) if str(target) in x or "/private/" in x or "\\" in x]
        case("no answer to any stories route held a path", not bad, bad[:3])
    finally:
        srv.stop()


NO_FINDER_JS = r"""
(function(){
  var real = window.fetch;
  window.__opens = [];
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) { window.__opens.push(String(u)); return Promise.resolve(new Response('{"ok":true,"words":"Opened."}', {status: 200, headers: {'Content-Type': 'application/json'}})); }
    return real.apply(this, arguments);
  };
})();
"""


def check_stories_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the stories designer's real page: no Chrome on this computer", flush=True)
        return
    from PIL import Image, ImageChops, ImageStat
    target = work / "stories-browser"
    ok, out = make_kit(target, "Story beach", 12)
    if not case("stories browser: the pretend kit was made", ok, out):
        return
    ok, out = make_kit(target, "Lone story", 8)
    case("stories browser: a second pretend kit", ok, out)
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Story beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    sdesigns = kit / ".kit" / "story-designs"
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    try:
        with cd.Chrome(work=work / "chrome-stories", size=(1400, 1000)) as c:
            c.init_script(NO_FINDER_JS)

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return J("Designer.st")

            def ready(seconds=20):
                c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def settled(seconds=10):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                did = c.js("Designer.design.id")
                return json.loads((sdesigns / f"{did}.json").read_text(encoding="utf-8"))["state"] == st()

            def gallery_open():
                return c.js("!document.getElementById('gallery').hidden")

            def add(section, nth):
                c.click(f"#gallery-{section} .dz-card:nth-child({nth}) .dz-use")
                c.wait_for("document.getElementById('gallery').hidden", 5)

            c.open(f"{base}/design.html?kit={KQ}&kind=stories")
            ready()
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            case("opened on a shoot with no stories: the page opens on its Add stories window", gallery_open())
            g = J("{h: document.querySelector('#gallery h2').textContent, sub: document.getElementById('gallery-sub').textContent, "
                  "secs: Array.from(document.querySelectorAll('#gallery .dz-sec')).map(function(x){ return x.textContent; }), "
                  "use: Array.from(document.querySelectorAll('#gallery .dz-use')).map(function(x){ return x.textContent; }), "
                  "names: Array.from(document.querySelectorAll('#gallery .dz-cap b')).map(function(x){ return x.textContent; }), "
                  "subs: Array.from(document.querySelectorAll('#gallery .dz-cap small')).map(function(x){ return x.textContent; })}")
            case("the window: her title, her line for a first story, her three sections, every card's button says Add",
                 g["h"] == HERS["gallery"] and g["sub"] == HERS["subEmpty"] and [x.title() for x in g["secs"]] == [x.title() for x in HERS["secs"]] and set(g["use"]) == {"Add"}, g)
            case("the window: Blank story, One photo per story, then her seven layouts, with her words under them",
                 g["names"] == ["Blank story", "One photo per story"] + [x[0] for x in GRIDS] and g["subs"][0] == HERS["blankSub"] and g["subs"][1] == "5 stories"
                 and g["subs"][2:] == ["1 story · 1 photo", "1 story · 2 photos", "1 story · 3 photos", "1 story · 4 photos", "1 story · 6 photos", "1 story · 9 photos", "1 story · 12 photos"], g)
            words = J("{title: document.title, eyebrow: document.querySelector('.eyebrow').firstChild.textContent, save: document.getElementById('save-slides').textContent, "
                      "prev: document.getElementById('preview-btn').textContent, count: document.querySelector('#g-slides .lbl').textContent, "
                      "add: document.getElementById('new-design').textContent, nameShown: !document.getElementById('d-name-box').hidden, "
                      "mine: !document.getElementById('designs-btn').hidden, dup: !document.getElementById('dup-design').hidden, bands: document.getElementById('gridcrop').checked}")
            case("the page: Stories designer, Save stories, Preview, Stories, + Add stories; no design name, no My designs, no Duplicate; the bands on",
                 words == {"title": "Stories Designer · " + words["title"].split(" · ")[-1], "eyebrow": "Stories designer", "save": "Save stories", "prev": "Preview",
                           "count": "Stories", "add": "+ Add stories", "nameShown": False, "mine": False, "dup": False, "bands": True}, words)
            add("fresh", 2)
            s1 = st()
            case("One photo per story: five stories, one photo each, the shoot's first five photos, each filling its story",
                 s1["slides"] == 5 and [b["n"] for b in s1["blocks"]] == [1, 2, 3, 4, 5] and all(b["x"] == k * SW and b["w"] == SW and b["h"] == SH for k, b in enumerate(s1["blocks"])), s1)
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            case("+ Add stories again: her line says it goes after the last story and nothing is replaced", c.text("#gallery-sub") == HERS["subMore"], c.text("#gallery-sub"))
            add("starters", 3)
            s2 = st()
            new = s2["blocks"][5:]
            case("Three strips added: a sixth story, the first five exactly as they were", s2["slides"] == 6 and s2["blocks"][:5] == s1["blocks"], s2["slides"])
            case("...its three strips edge to edge on story 6, each with a photo the stories did not use yet",
                 len(new) == 3 and all(5 * SW <= b["x"] < 6 * SW for b in new) and sorted(b["y"] for b in new) == [0, 644, 1288] and all(b["n"] not in (1, 2, 3, 4, 5) and b["n"] for b in new), new)
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            add("starters", 6)
            s3 = st()
            case("Nine added: a seventh story, nothing before it changed", s3["slides"] == 7 and s3["blocks"][:8] == s2["blocks"] and len(s3["blocks"]) == 17, s3["slides"])
            case("the saved design follows the page", settled())
            c.click("#undo")
            case("Undo takes the last add back in one step", st() == s2)
            c.click("#undo")
            case("...and the one before", st() == s1)
            c.click("#new-design")
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            add("starters", 3)
            s2b = st()
            case("settled after the undo and a new add", settled() and s2b["slides"] == 6)
            # ---- Remove this story ----
            target_id = next(b["id"] for b in s2b["blocks"] if b["x"] == SW)
            c.click(f"#strip .blk[data-id='{target_id}']")
            sel = J("{shown: !document.getElementById('sel-story').hidden, words: document.querySelector('#sel-story [data-a=delstory]').textContent, "
                    "title: document.querySelector('#sel-story [data-a=delstory]').title, off: document.querySelector('#sel-story [data-a=delstory]').disabled, "
                    "fill: document.querySelector('#sel-photo [data-a=full]').textContent, span: !!document.querySelector('#sel-photo [data-a=span2]'), "
                    "center: document.querySelector('#sel-all [data-a=center]').textContent}")
            case("a photo selected: Remove this story (her words and tooltip), Fill story, Center on story, and no Across 2 slides",
                 sel == {"shown": True, "words": HERS["remove"], "title": HERS["removeTitle"], "off": False, "fill": "Fill story", "span": False, "center": "Center on story"}, sel)
            c.click("#sel-story [data-a=delstory]")
            s4 = st()
            want = [dict(b, x=b["x"] - SW) if b["x"] >= 2 * SW else b for b in s2b["blocks"] if b["id"] != target_id]
            case("Remove this story: story 2 and its photo are gone, the stories after it move up, nothing else changes", s4["slides"] == 5 and s4["blocks"] == want, s4)
            c.click("#undo")
            case("Undo brings the story back exactly", st() == s2b)
            case("settled", settled())
            # ---- the bands ----
            bands = J("Array.from(document.querySelectorAll('#strip .safe')).map(function(z){ return z.textContent; })")
            case("Show Instagram's buttons: a band at the top and the bottom of every story, with her words",
                 len(bands) == 12 and bands[:2] == ["Instagram's name and buttons", "Instagram's reply bar"], bands[:4])
            sc = c.js("Designer.scale")
            top, bot = c.rect("#strip .safe:nth-of-type(1)") if False else None, None
            hb = J("Array.from(document.querySelectorAll('#strip .safe')).slice(0, 2).map(function(z){ return [parseFloat(z.style.top), parseFloat(z.style.height)]; })")
            case("the bands are 250 and 340 story pixels tall, at the very top and bottom", abs(hb[0][0]) < 0.01 and abs(hb[0][1] - 250 * sc) < 0.01 and abs(hb[1][0] - (SH - 340) * sc) < 0.01 and abs(hb[1][1] - 340 * sc) < 0.01, (hb, sc))
            c.click("#gridcrop")
            case("unticked, the bands go", c.count("#strip .safe") == 0)
            c.click("#gridcrop")
            case("ticked again, they come back", c.count("#strip .safe") == 12)
            # ---- text and its looks ----
            c.click("#strip .blk[data-id='1']")
            c.click("#add-text")
            t0 = J("Designer.selected()")
            case("+ Add text on a story: Figtree, bold, 72, line height 1.3, black on a white box, a little above the middle",
                 {k: t0.get(k) for k in ("font", "size", "weight", "lh", "color", "look", "boxColor", "y")} == {"font": "Figtree", "size": 72, "weight": 700, "lh": 1.3, "color": "#111111", "look": "box", "boxColor": "#ffffff", "y": 806.4}, t0)
            case("the font button says the story font's Instagram style first: \"Classic · Figtree ▾\"", c.text("#font-btn") == "Classic · Figtree ▾", c.text("#font-btn"))
            lk = J("{label: document.querySelector('#sel-look .lbl').textContent, btns: Array.from(document.querySelectorAll('#sel-look [data-look]')).map(function(b){ return [b.textContent, b.classList.contains('on')]; }), "
                   "box: !document.getElementById('t-box').hidden, boxLbl: document.getElementById('box-lbl').textContent, shown: !document.getElementById('sel-look').hidden}")
            case("the Look group: Look, Plain / Box / Neon with Box on, and Box color showing", lk == {"label": "Look", "btns": [["Plain", False], ["Box", True], ["Neon", False]], "box": True, "boxLbl": "Box color", "shown": True}, lk)
            order = J("Array.from(document.getElementById('selrows').children).filter(function(g){ return !g.hidden; }).map(function(g){ return g.id; })")
            case("the bar for a story's text, in her order: the text's groups, Look, Remove this story, then the rest",
                 order[-3:] == ["sel-look", "sel-story", "sel-all"] and order.index("sel-text") < order.index("sel-look"), order)
            c.wait_for("Designer.type.status(Designer.selected()) !== 'wait'", 15)
            c.click("#sel-look [data-look='neon']")
            t1 = J("Designer.selected()")
            case("Neon: the look is neon, the words take the box's color, and Box color hides", t1["look"] == "neon" and t1["color"] == "#ffffff" and c.js("document.getElementById('t-box').hidden") is True, t1)
            c.click("#sel-look [data-look='box']")
            t1b = J("Designer.selected()")
            case("Neon to Box: a white box with black words (hers)", t1b["look"] == "box" and t1b["boxColor"] == "#ffffff" and t1b["color"] == "#111111", t1b)
            c.click("#sel-look [data-look='plain']")
            c.set_value("#t-color", "#ff3399")
            c.click("#sel-look [data-look='box']")
            t2 = J("Designer.selected()")
            case("Plain to Box: the box takes the words' color, and the words go white on it", t2["look"] == "box" and t2["boxColor"] == "#ff3399" and t2["color"] == "#ffffff", t2)
            c.set_value("#t-box", "#ffe066")
            t3 = J("Designer.selected()")
            case("Box color: the box changes, and the words go black on a light box", t3["boxColor"] == "#ffe066" and t3["color"] == "#111111", t3)
            nb = c.count("#strip .blk.words .bx2")
            case("on the strip the box is drawn behind each line of words", nb >= 1, nb)
            c.click("#sel-look [data-look='plain']")
            t4 = J("Designer.selected()")
            case("Plain: the words take the box's color", t4["look"] == "plain" and t4["color"] == "#ffe066" and c.count("#strip .blk.words .bx2") == 0, t4)
            case("each press of a look is one Undo step", (c.click("#undo") or True) and J("Designer.selected().look") == "box")
            c.click("#font-btn")
            fl = J("{grp: document.querySelector('#font-list .fp-grp').textContent, first: document.querySelector('#font-list .fp-it .fp-name').textContent, "
                   "n: Array.from(document.querySelectorAll('#font-list .fp-grp')).map(function(g){ return g.textContent; })}")
            case("the font list starts with her story fonts, each as \"<Instagram style> · <font>\"", fl["grp"] == "Yours" and False or (fl["n"][0] in ("Story fonts", "Yours") and fl["first"] == "Classic · Figtree" and "Story fonts" in fl["n"]), fl)
            c.key("Escape")
            case("settled with the text", settled())
            # ---- the preview ----
            c.click("#strip .blk[data-id='1']")
            c.key("Escape")
            c.click("#preview-btn")
            c.wait_for("!document.getElementById('preview').hidden", 5)
            pv = J("{bars: document.querySelectorAll('#pv-bars b').length, who: document.querySelector('#pv-igtop .pv-who').textContent, ago: document.querySelector('#pv-igtop small').textContent, "
                   "reply: document.querySelector('#pv-igbot span').textContent, dots: document.getElementById('pv-dots').hidden, count: document.getElementById('pv-count').hidden, "
                   "black: getComputedStyle(document.querySelector('.pv-phone')).backgroundColor}")
            case("Preview: a bar for each story, their name (\"yourname\" until their handle is known) with 2h, the reply bar, no dots or count, a black phone",
                 pv == {"bars": 6, "who": "yourname", "ago": "2h", "reply": "Send message", "dots": True, "count": True, "black": "rgb(0, 0, 0)"}, pv)
            r = c.rect("#pv-view")
            c.click((r["x"] + r["w"] * 0.8, r["y"] + r["h"] * 0.5))
            i1 = c.js("Designer.saver.preview.i")
            c.click((r["x"] + r["w"] * 0.15, r["y"] + r["h"] * 0.5))
            i2 = c.js("Designer.saver.preview.i")
            case("Preview: a tap on the right goes on, a tap on the left third goes back (like stories)", (i1, i2) == (1, 0), (i1, i2))
            onb = J("Array.from(document.querySelectorAll('#pv-bars b')).map(function(b){ return b.className; })")
            case("Preview: the first bar is lit", onb[0] == "on", onb)
            c.key("Escape")
            case("no error of the page's own so far", not c.page_errors(), c.page_errors()[:3])

        # ---- one story: Remove this story is off, with a line ----
        with cd.Chrome(work=work / "chrome-stories-one", size=(1400, 1000)) as c:
            c.init_script(NO_FINDER_JS)
            c.open(f"{base}/design.html?kit={quote('2026-11-01 Lone story')}&kind=stories")
            c.wait_for("window.Designer && Designer.st && !document.getElementById('gallery').hidden", 20)
            c.click("#gallery-fresh .dz-card:nth-child(1) .dz-use")
            c.wait_for("document.getElementById('gallery').hidden", 5)
            c.click("#add-text")
            one = json.loads(c.js("JSON.stringify({slides: Designer.st.slides, off: document.querySelector('#sel-story [data-a=delstory]').disabled, "
                                  "line: document.getElementById('only-story').hidden ? '' : document.getElementById('only-story').textContent})"))
            case("one story: Remove this story is off, and a line beside it says why", one == {"slides": 1, "off": True, "line": "It\u2019s your only story, so it stays."}, one)
            case("no error of the page's own on the one-story shoot", not c.page_errors(), c.page_errors()[:3])

        # ---- Save stories, every story compared with the screen ----
        code, sst = get_json(P, f"/design-state?kit={KQ}&kind=stories")
        d = sst["design"]

        def T(i, words, x, y, look, color, box=None, size=110):
            t = {"id": i, "type": "text", "text": words, "font": "Inter", "size": size, "weight": 700, "italic": False, "upper": False, "al": "center",
                 "ls": 0, "lh": 1.3, "color": color, "x": x, "y": y, "w": 860, "h": round(size * 1.3, 2), "look": look}
            if box:
                t["boxColor"] = box
            return t

        layout = {"slides": 3, "bg": "#2a4d6e", "blocks": [
            {"id": 1, "n": 1, "x": 0, "y": 0, "w": SW, "h": SH, "ox": 0.5, "oy": 0.5, "zoom": 1},
            T(2, "Box words here", 110, 700, "box", "#111111", "#ffe066"),
            T(3, "Neon glow", SW + 110, 800, "neon", "#ff3399"),
            {"id": 4, "n": 2, "x": 2 * SW, "y": 0, "w": SW, "h": 632, "ox": 0.5, "oy": 0.5, "zoom": 1},
            {"id": 5, "n": 3, "x": 2 * SW, "y": 644, "w": SW, "h": 632, "ox": 0.5, "oy": 0.5, "zoom": 1},
            {"id": 6, "n": 4, "x": 2 * SW, "y": 1288, "w": SW, "h": 632, "ox": 0.5, "oy": 0.5, "zoom": 1},
            T(7, "Plain words", 2 * SW + 110, 1400, "plain", "#ffffff")]}
        code, out = post(P, "/design", {"kit": kit_name, "kind": "stories", "design": d["id"], "stamp": sst["stamp"], "base": d["rev"], "page": "pixelcheck01", "state": layout})
        case("a known layout for the pixel check (a photo, a box, neon words, three strips, plain words) is saved", code == 200 and out.get("ok"), (code, out))
        with cd.Chrome(work=work / "chrome-stories-2x", size=(1500, 1250), scale=2) as c2:
            c2.init_script(NO_FINDER_JS)
            c2.open(f"{base}/design.html?kit={KQ}&kind=stories")
            c2.wait_for("window.Designer && Designer.saver && Designer.st && Designer.st.slides === 3", 20)
            c2.wait_for("Designer.st.blocks.filter(Designer.M.isText).every(function(b){ return Designer.type.status(b) === 'ready'; }) && Designer.type.fit(Designer.st) === Designer.st && Designer.save.idle()", 20,
                        tell="JSON.stringify(Designer.st.blocks.filter(Designer.M.isText).map(function(b){ return Designer.type.status(b); }))")
            c2.wait_for("Array.prototype.every.call(document.querySelectorAll('#strip .blk img'), function(i){ return i.complete && i.naturalWidth > 0; })", 20)
            c2.js("Designer.setView(330)")
            c2.click("#gridcrop")              # the bands off, so the screen is what a saved story should be
            c2.js("window.scrollTo(0, document.getElementById('stage').offsetTop - 4)")
            c2.js("document.getElementById('stage').scrollLeft = 0")
            c2.mouse_move(3, 3)
            time.sleep(0.4)
            s = c2.js("Designer.scale")
            sr = c2.rect("#strip")
            shot = Image.open(c2.screenshot("stories-screen.png")).convert("RGB")
            crops = []
            for k in range(3):
                x0, y0 = sr["x"] + k * SW * s, sr["y"]
                crops.append(shot.crop((int(round(x0 * 2)) + 2, int(round(y0 * 2)) + 2, int(round((x0 + SW * s) * 2)) - 2, int(round((y0 + SH * s) * 2)) - 2)))
            c2.click("#gridcrop")              # the bands back on for the save: they must not be in the saved stories
            c2.click("#save-slides")
            c2.wait_for("!Designer.saver.busy() || Designer.saver.asking()", 90, tell="document.getElementById('save-line').textContent")
            line = c2.text("#save-line")
            errs = c2.page_errors()
        stories = kit / "Stories"
        files = sorted(p.name for p in stories.glob("Story beach stories*.jpg")) if stories.is_dir() else []
        case("Save stories (from a second window): the line says three stories are in the Stories folder", line.startswith("Saved 3 stories in your Stories folder, named \"Story beach stories") and not errs, (line, errs))
        newest = sorted(f for f in files if f.endswith(" - 01.jpg"))[-1].rsplit(" - ", 1)[0] if files else ""
        saved = [Image.open(stories / f"{newest} - {i:02d}.jpg").convert("RGB") for i in (1, 2, 3)] if newest else []
        case("Save stories: three 1080 by 1920 JPEGs", len(saved) == 3 and all(im.size == (SW, SH) for im in saved), [im.size for im in saved])
        if len(saved) == 3:
            def diff(a, b):
                return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3

            def region(im, box, crop_size):
                fx, fy = crop_size[0] / SW, crop_size[1] / SH
                return im.crop((int(box[0] * fx), int(box[1] * fy), int(box[2] * fx), int(box[3] * fy)))
            names = ["story 1: a photo and words on a box", "story 2: neon words on the background", "story 3: three strips and plain words"]
            limits = [6.0, 6.0, 6.0]
            for k in range(3):
                cr = crops[k]
                sv = saved[k].resize(cr.size, Image.LANCZOS)
                whole = diff(sv, cr)
                print(f"NOTE  stories pixel check, {names[k]}: mean difference {whole:.2f} of 255 over the whole story", flush=True)
                case(f"pixel by pixel: {names[k]}: the saved story is the screen (mean difference {whole:.1f} of 255, at most {limits[k]})", whole <= limits[k], round(whole, 2))
            for k, box, lim, what in ((0, (60, 640, 1020, 900), 14.0, "the box behind the words"), (1, (330, 780, 750, 970), 22.0, "the neon words and their glow (a wider tolerance: a canvas and a page blur a glow a little differently)"),
                                      (2, (60, 1360, 1020, 1600), 14.0, "the plain words")):
                cr = crops[k]
                sv = saved[k].resize(cr.size, Image.LANCZOS)
                dd = diff(region(sv, box, cr.size), region(cr, box, cr.size))
                print(f"NOTE  stories pixel check, {what}: mean difference {dd:.2f} of 255 in its own area", flush=True)
                case(f"pixel by pixel: {what}: the same on the saved story as on the screen (mean difference {dd:.1f}, at most {lim})", dd <= lim, round(dd, 2))
            top = saved[0].crop((0, 0, SW, 250))
            r_, g_, b_ = ImageStat.Stat(top).mean
            scr_top = ImageStat.Stat(crops[0].crop((0, 0, crops[0].size[0], int(250 * crops[0].size[1] / SH)))).mean
            case("no band of Instagram's buttons is in a saved story (they were showing when it was saved)", abs(r_ - scr_top[0]) < 8 and abs(g_ - scr_top[1]) < 8, ((r_, g_, b_), scr_top))
            bx = saved[0].crop((195, 712, 205, 722))          # the box's left padding, beside the first letter
            yellow = ImageStat.Stat(bx).mean
            case("the box on the saved story is her box color (#ffe066)", abs(yellow[0] - 255) < 12 and abs(yellow[1] - 224) < 14 and yellow[2] < 140, yellow)
    finally:
        srv.stop()
