#!/usr/bin/env python3
"""Check what Nicole's v26 (Nov 13) added to the stories designer. A part of tests/design_check.py (--only v26).

    Show Instagram's guides   the tick's new name, and the last sentence of her intro
    the stories stay in view  the stage stays at the top of the window while the photos scroll under it
    Let my assistant choose   the button beside the photos' heading, her box, the note saved with the set as "ask"
                              (never part of the layout), the line to copy (", and follow my note" only with a
                              note), and the chat's side: design.py story-note and story-fill; an open page takes
                              the assistant's pick by itself after Copy
    her templates             Gallery delivered (4), My editing queue (1, no photo, filled from the editing queue),
                              The full story (10), Seamless swipe (6), in her order, before her seven grids
    Redo                      beside Undo, Cmd+Shift+Z and Cmd+Y; in the carousel's designer too
    sets of stories           the name box, My story sets, + New set of stories; a shoot's one design from before is
                              its first set; the kit shows the set saved last
    x on a story's label      removes that story, even an empty one; the others move up; Undo brings it back

Three parts, as the other parts have: the tables, the words and the rules by themselves (check_v26_page), the routes
and the commands by request (check_v26_server, a pretend kit and a page server on the port it is given), and the
real page in a hidden Chrome (check_v26_browser, another pretend kit and server). Her words are in this file's own
table (HERS); when her page is beside the project (reference-private/, never pushed) every one of them is also
looked for in it, and that one case is left out when it is not there.

Nothing here touches the real ~/.studio: every server and command gets a STUDIO_HOME inside the work folder, and the
switch that keeps a test from opening a window (STUDIO_NO_WINDOWS_FOR_TESTS).
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
HER_REL = Path("reference-private") / "nicole-handoff-v26-2026-11-13" / "Carousel designer and reel picker" / "pages" / "carousel-designer.html"
HER_PAGES = [ROOT / HER_REL, ROOT.parent / "hf-tools" / HER_REL]      # beside this checkout, or beside the main one
APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
W, H = 1080, 1920

# Her words (pages/carousel-designer.html, v26), exactly. "'" is how her file writes an apostrophe inside a string.
HERS = {
    "bands": "Show Instagram's guides",
    "lede_end": "Untick Show Instagram's guides to hide them.",
    "ask_button": "Let my assistant choose the photos",
    "ask_head": "Tell your assistant what you want",
    "ask_sub": "Optional. Your assistant picks a story with a good mix from this shoot, and follows your note.",
    "ask_example": "For example: “Start with the big laugh, then the details, and end on the two of them walking away.”",
    "ask_place": "Optional: what you'd like in your stories",
    "ask_then": "Then copy this into the chat, and your assistant fills in your stories:",
    "ask_line": "Pick my story photos",
    "ask_for": " for ",
    "ask_note": ", and follow my note",
    "copy": "Copy", "copied": "Copied",
    "redo": "Redo",
    "sets": "My story sets", "new_set": "+ New set of stories", "sets_head": " story sets",
    "removed": "Undo brings it back.",
    "queue_title": "My editing queue", "queue_place": "Your editing queue",
    "queue_closing": "If your shoot is on here, your gallery is on its way.",
    "queue_empty": "Nothing in your editing queue right now",
    "queue_cant": "I can't reach your editing queue right now.",
}


def _grid(cols, rows, g=12):
    cw, ch = (W - (cols - 1) * g) / cols, (H - (rows - 1) * g) / rows
    return [(c * (cw + g), r * (ch + g), cw, ch) for r in range(rows) for c in range(cols)]


# Her four story templates, typed from her page: (id, name, stories, background, frames (x, y, w, h), texts).
# A text is (x, y, w, words, what differs from her ST: Figtree 72 bold, line height 1.3, black on a white box, centered).
HERS_TEMPLATES = [
    ("sg-delivered", "Gallery delivered", 4, "#f6f1e7",
     [(0, 0, W, H), (W, 0, W, 620), (W, 650, W, 620), (W, 1300, W, 620), (2 * W + 90, 260, 900, 1150), (3 * W + 60, 330, 465, 700), (3 * W + 555, 330, 465, 700)],
     [(60, 1180, 960, "Gallery delivery day", {"size": 80}),
      (190, 1320, 700, "for your client's name", {"size": 56, "weight": 400}),
      (W + 240, 300, 600, "A few favorites", {"size": 64}),
      (2 * W + 140, 1460, 800, "Your full gallery is in your inbox", {"size": 56}),
      (3 * W + 140, 1120, 800, "Thank you for letting me tell your story", {"size": 60})]),
    ("sg-queue", "My editing queue", 1, "#f6f1e7", [],
     [(90, 380, 900, "My editing queue", {"size": 60, "look": "plain"}),
      (90, 520, 900, "Your editing queue", {"size": 40, "weight": 400, "lh": 1.7, "look": "plain"}),
      (90, 1440, 900, "If your shoot is on here, your gallery is on its way.", {"size": 34, "weight": 400, "italic": True, "look": "plain"})]),
    ("sg-full", "The full story", 10, "#f6f1e7",
     [(0, 0, W, H), (W, 0, W, 950), (W, 970, W, 950), (2 * W + 90, 250, 900, 1300), (3 * W, 0, W, 630), (3 * W, 645, W, 630), (3 * W, 1290, W, 630),
      (4 * W, 0, W, H), (5 * W, 0, W, 1250), (5 * W + 560, 1060, 440, 560)]
     + [(x + 6 * W, y, w, h) for x, y, w, h in _grid(2, 2)]
     + [(7 * W, 0, W, H), (8 * W, 0, 535, H), (8 * W + 545, 0, 535, H), (9 * W + 140, 250, 800, 1000)],
     [(140, 1300, 800, "Your words here", {"size": 80}),
      (9 * W + 140, 1340, 800, "Your words here", {"size": 64, "look": "plain"})]),
    ("sg-seamless", "Seamless swipe", 6, "#ffffff",
     [(0, 0, 3 * W, H), (3 * W + 90, 300, 900, 1200), (4 * W, 0, W, H), (5 * W, 0, W, 950), (5 * W, 970, W, 950)], []),
]
GRID_NAMES = ["One photo", "Two up", "Three strips", "Four", "Six", "Nine", "Twelve"]
ST_DEFAULT = {"font": "Figtree", "size": 72, "weight": 700, "italic": False, "upper": False, "al": "center", "ls": 0, "lh": 1.3,
              "color": "#111111", "look": "box", "boxColor": "#ffffff"}


def _r(v):
    return round(float(v), 2)


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


def _frame(i, n, x, y=0, w=W, h=H):
    return {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}


def _text(i, x, y, words="Their own words"):
    return dict(ST_DEFAULT, id=i, type="text", text=words, x=x, y=y, w=820, h=93.6)


def queue_file(studio, names, more=()):
    """A pretend editing queue: these shoots waiting, due a day apart in this order, then anything in more."""
    shoots = [{"id": f"q{i}", "name": n, "status": "waiting", "due": f"2026-12-{i + 1:02d}", "added": f"2026-11-01T10:{i:02d}:00", "photos": 10}
              for i, n in enumerate(names)]
    (studio / "queue.json").write_text(json.dumps({"shoots": shoots + list(more), "picks": {}, "manual_order": False}), encoding="utf-8")


RULES_JS = r"""
var out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
var window = this;
window.DESIGN_LIMITS = STORY_LIMITS;
eval(MODEL_SRC); eval(PLAN_SRC);
var M = window.DesignModel, P = window.DesignPlan;
var tpl = QUEUE_TPL, LIST = QUEUE_LIST;
function listOf(st){ return st.blocks.filter(function(b){ return b.id === LIST; })[0]; }
var three = P.fillQueue(tpl, ['Garcia wedding', 'Lee family', 'Zoë & Été'], LIST, 3);
t('fillQueue: the shoots in order, each numbered with three spaces before her name', listOf(three).text === '1   Garcia wedding\n2   Lee family\n3   Zoë & Été', listOf(three).text);
t('fillQueue: only the list changes: the title and the closing line are as the template has them',
  eq(three.blocks.filter(function(b){ return b.id !== LIST; }), tpl.blocks.filter(function(b){ return b.id !== LIST; })) && three.slides === 1 && three.bg === tpl.bg);
t('fillQueue: the template it was given is not changed', listOf(tpl).text === PLACE);
t('fillQueue: the list is as tall as its lines as written (3 lines of 40 at 1.7)', listOf(three).h === 204, listOf(three).h);
var none = P.fillQueue(tpl, [], LIST, 0);
t('fillQueue: an empty queue says her line', listOf(none).text === EMPTY, listOf(none).text);
var names = []; for (var i = 1; i <= 14; i++) names.push('Shoot ' + i);
var twelve = P.fillQueue(tpl, names.slice(0, 12), LIST, 12);
t('fillQueue: twelve shoots: twelve lines, no "more"', listOf(twelve).text.split('\n').length === 12 && listOf(twelve).text.indexOf('more') < 0);
var many = P.fillQueue(tpl, names, LIST, 14), rows = listOf(many).text.split('\n');
t('fillQueue: fourteen shoots: the first twelve, then "+ 2 more"', rows.length === 13 && rows[11] === '12   Shoot 12' && rows[12] === '+ 2 more', rows);
var counted = P.fillQueue(tpl, names.slice(0, 12), LIST, 430), r2 = listOf(counted).text.split('\n');
t('fillQueue: a long queue the Assistant sent only the start of: the count it gave decides "+ n more"', r2[12] === '+ 418 more', r2[12]);
var odd = P.fillQueue(tpl, ['A', 7, null, '', 'B'], LIST);
t('fillQueue: anything that is not a name is left out', listOf(odd).text === '1   A\n2   B', listOf(odd).text);
var code = P.fillQueue(tpl, ['<img src=x onerror=1>'], LIST, 1);
t('fillQueue: a name is kept as the text it is', listOf(code).text === '1   <img src=x onerror=1>');
var wrong = P.fillQueue(tpl, ['A'], 999, 1);
t('fillQueue: with no such text box nothing changes', eq(wrong, tpl));
// the x on a label: an empty story is removed, the ones after it move up
var S = {slides: 4, bg: '#ffffff', blocks: [{id: 1, n: 1, x: 0, y: 0, w: 1080, h: 1920, ox: .5, oy: .5, zoom: 1}, {id: 2, n: 2, x: 2160, y: 0, w: 1080, h: 1920, ox: .5, oy: .5, zoom: 1},
     {id: 3, n: 3, x: 3240, y: 100, w: 500, h: 500, ox: .5, oy: .5, zoom: 1}]};
var gone = M.removeStory(S, 1);
t('removeStory: an EMPTY story is removed; the stories after it move up by one; nothing else changes',
  gone.st.slides === 3 && eq(gone.st.blocks.map(function(b){ return [b.id, b.x]; }), [[1, 0], [2, 1080], [3, 2160]]) && !gone.why, gone.st);
t('removeStory: the layout it was given is not changed', S.slides === 4 && S.blocks[1].x === 2160);
t('removeStory: the last one of all stays (why: one)', M.removeStory({slides: 1, bg: '#ffffff', blocks: []}, 0).why === 'one');
JSON.stringify(out);
"""


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


def check_v26_page(case, work):
    sys.path.insert(0, str(SCRIPTS))
    import design
    import design_page
    src = _src()
    allsrc = "".join(src.values())
    story = design_page.page_html("2026-11-01 Fake beach", "stories")
    car = design_page.page_html("2026-11-01 Fake beach")

    def on(page, words):
        return words in page or words.replace("'", "&#x27;") in page

    # ---- her words, whole ----
    for k in ("bands", "lede_end", "ask_button", "ask_head", "ask_sub", "ask_example", "ask_place", "ask_then", "ask_line", "copy", "redo"):
        case(f"v26 page: her words on the stories page: {HERS[k][:60]}", on(story, HERS[k]), HERS[k])
    for k in ("ask_note", "copied", "sets", "new_set", "sets_head", "removed", "queue_empty"):
        case(f"v26 page: her words in the page's scripts: {HERS[k][:60]}", HERS[k] in allsrc or HERS[k].replace("'", "\\'") in allsrc, HERS[k])
    case("v26 page: her line when the queue can't be read, in the scripts and in the Assistant's own answer",
         HERS["queue_cant"].replace("'", "\\'") in allsrc and design.QUEUE_CANT == HERS["queue_cant"])
    case("v26 page: the old name of the tick is gone from the stories page", "Show Instagram's buttons" not in story and "Show Instagram&#x27;s buttons" not in story)
    case("v26 page: the tick is on to start with, and its name for a screen reader is her new name",
         re.search(r"<input type='checkbox' id='gridcrop' checked aria-label='Show Instagram&#x27;s guides'>", story) is not None)
    case("v26 page: the note's box holds 600 letters at the most, as hers", "id='ask-note' rows='2' maxlength='600'" in story and design.ASK_MAX == 600)
    case("v26 page: the box starts closed, and the button says whether it is open", "<div class='ask-box' id='ask-box' hidden>" in story and "id='ask-pick' type='button' aria-expanded='false'" in story)
    case("v26 page: no page word says Claude, and none has a long dash", "Claude" not in "".join(HERS.values()) and "—" not in story)
    her = her_page()
    if her is None:
        print("NOTE  v26: her page is not beside the project, so her words were checked against this file's own table only", flush=True)
    else:
        missing = [k for k, v in HERS.items() if v not in her and v.replace("'", "\\'") not in her and v.replace("“", "“").replace("”", "”") not in her]
        case("v26 page: every word in this file's table is in her page, as she wrote it", not missing, missing)
        names = re.findall(r"\{ id: '(sg-[a-z0-9]+)', name: '([^']+)', slides: (\d+), bg: '(#[0-9a-f]{6})'", her)
        case("v26 page: her page's story layouts, in her order, are this file's table and then her seven grids",
             [(i, n, int(s), b) for i, n, s, b in names][:4] == [(t[0], t[1], t[2], t[3]) for t in HERS_TEMPLATES] and [n for _, n, _, _ in names][4:] == GRID_NAMES, names)
    # ---- the carousel's page is as it was, but for Redo ----
    for w in ("id='ask-pick'", "id='ask-box'", "id='ask-note'", "Let my assistant choose", "Show Instagram's", "Show Instagram&#x27;s"):
        case(f"v26 page: the carousel's page has nothing of it ({w})", w not in car)
    case("v26 page: Redo is beside Undo on both pages, off to start with",
         all("<button class='tb' id='undo' type='button' disabled>Undo</button><button class='tb' id='redo' type='button' disabled>Redo</button>" in p for p in (story, car)))
    # ---- her templates, in design.py's own table ----
    st = design.STORY_STARTERS
    case("v26 page: eleven story layouts: her four templates, then her seven grids", [x["id"] for x in st] == [t[0] for t in HERS_TEMPLATES] + ["sg-1", "sg-2", "sg-3", "sg-4", "sg-6", "sg-9", "sg-12"]
         and [x["name"] for x in st] == [t[1] for t in HERS_TEMPLATES] + GRID_NAMES, [x["id"] for x in st])
    for mine, (tid, name, slides, bg, frames, texts) in zip(st, HERS_TEMPLATES):
        tp = mine["template"]
        fr = [b for b in tp["blocks"] if b.get("type") != "text"]
        tx = [b for b in tp["blocks"] if b.get("type") == "text"]
        case(f"v26 page: {name}: {slides} stor{'ies' if slides != 1 else 'y'} on her background, her {len(frames)} frames in her order, all empty",
             tp["slides"] == slides and tp["bg"] == bg and [(_r(b["x"]), _r(b["y"]), _r(b["w"]), _r(b["h"])) for b in fr] == [tuple(_r(v) for v in f) for f in frames]
             and all(b["n"] is None for b in fr) and [b["slot"] for b in fr] == list(range(1, len(fr) + 1)), [(b["x"], b["y"], b["w"], b["h"]) for b in fr][:3])
        want = [dict(ST_DEFAULT, **dict(more, text=words, x=x, y=y, w=w)) for x, y, w, words, more in texts]
        got = [{k: b[k] for k in list(ST_DEFAULT) + ["text", "x", "y", "w"]} for b in tx]
        case(f"v26 page: {name}: her {len(texts)} text boxes, with her placeholder words, sizes and looks", got == want, got[:2])
        case(f"v26 page: {name}: every text box is ordinary text of a story (a font name, a size, a look), after the frames",
             all(b["type"] == "text" and design.font_ok(b["font"]) and b["h"] >= 1 for b in tx) and tp["blocks"] == fr + tx)
    q = next((x for x in st if x["id"] == "sg-queue"), None)
    if not case("v26 page: My editing queue is the second layout, and says it is filled from the queue", q is not None and q is st[1] and q.get("fill") == "queue" and isinstance(q.get("list"), int), q and q.get("fill")):
        return
    case("v26 page: My editing queue holds no photo, is one story, and names the text box its list goes in",
         not [b for b in q["template"]["blocks"] if b.get("type") != "text"] and q["template"]["slides"] == 1
         and [b["text"] for b in q["template"]["blocks"] if b["id"] == q["list"]] == [HERS["queue_place"]], q.get("list"))
    case("v26 page: no other layout asks to be filled from anywhere", all("fill" not in x and "list" not in x for x in st if x is not q))
    seam = next(x for x in st if x["id"] == "sg-seamless")["template"]["blocks"][0]
    case("v26 page: Seamless swipe: one photo across the first three stories", seam["x"] == 0 and seam["w"] == 3 * W and seam["h"] == H)
    case("v26 page: every one of them is a layout a story may hold (checked like any design)", all(design.validate_state(x["template"], template=True, kind="stories")[0] == x["template"] for x in st))
    case("v26 page: the carousel's starters and single slides are as they were (eleven and eight, none of a story's)",
         len(design.STARTERS) == 11 and len(design.SINGLES) == 8 and not any(x["id"].startswith("sg-") for x in design.STARTERS + design.SINGLES))
    # ---- sets of stories: the rule is gone, the names are as before ----
    case("v26 page: stories are no longer one design a shoot", design.KINDS["stories"]["one_design"] is False and not hasattr(design, "ONE_STORIES"))
    case("v26 page: the first set is \"<Shoot> stories\", the next \"<Shoot> stories 2\", then 3",
         design.next_name("Beach", [], kind="stories") == "Beach stories" and design.next_name("Beach", [{"name": "Beach stories"}], kind="stories") == "Beach stories 2"
         and design.next_name("Beach", [{"name": "Beach stories"}, {"name": "beach STORIES 2"}], kind="stories") == "Beach stories 3")
    # ---- the note ----
    A = design.clean_ask
    case("v26 page: the note: text as typed, with its line breaks; nothing unseen at either end; \"\" is no note",
         A("  Start with the laugh,\r\nthen the details  ") == "Start with the laugh,\nthen the details" and A("") == "" and A("   ") == "")
    case("v26 page: the note: 600 letters fit, 601 do not; a number, a list and nothing are not a note",
         A("x" * 600) == "x" * 600 and A("x" * 601) is None and A(7) is None and A(["a"]) is None and A(None) is None)
    case("v26 page: the note: a control character becomes a space, and a mark that turns the reading direction is dropped",
         A("a\u0007b") == "a b" and A("a‮b") == "ab")
    case("v26 page: the note is never part of a layout (a layout with an ask comes back without it)",
         "ask" not in design.validate_state({"slides": 1, "bg": "#ffffff", "blocks": [], "ask": "hello"}, kind="stories")[0])
    # ---- the rule scripts by themselves ----
    js = work / "v26-rules.js"
    js.write_text("var MODEL_SRC = " + json.dumps(src["DESIGN_MODEL_JS"]) + ";\nvar PLAN_SRC = " + json.dumps(src["DESIGN_PLAN_JS"]) + ";\nvar STORY_LIMITS = "
                  + json.dumps(design.limits_for("stories")) + ";\nvar QUEUE_TPL = " + json.dumps(q["template"]) + ";\nvar QUEUE_LIST = " + json.dumps(q["list"])
                  + ";\nvar PLACE = " + json.dumps(HERS["queue_place"]) + ";\nvar EMPTY = " + json.dumps(HERS["queue_empty"]) + ";\n" + RULES_JS, encoding="utf-8")
    r = osascript(js)
    try:
        rows = json.loads(r.stdout)
    except ValueError:
        rows = None
    if not case("v26 page: the rules ran by themselves (no page)", isinstance(rows, list) and len(rows) >= 14, (r.stdout[-300:], r.stderr[-300:])):
        return
    for name, ok, detail in rows:
        case("v26 rules: " + name, ok, detail)


def check_v26_server(case, work, port, make_kit, Server, post, get_json, ask, run, jpeg):
    target = work / "v26"
    ok, out = make_kit(target, "Set beach", 14)
    if not case("v26 server: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio), STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none")
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Set beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    sdesigns, cdesigns, stories_dir, rec_file = kit / ".kit" / "story-designs", kit / ".kit" / "designs", kit / "Stories", kit / ".kit" / "kit.json"
    photos_before = _tree(kit / "Photos")
    srv = Server(env, port)
    P = srv.start()
    seen = []

    def J(res):
        seen.append(res[1])
        return res

    def files():
        return sorted(f.name for f in sdesigns.glob("*.json") if not f.name.endswith(".prev.json"))

    def disk(did):
        return json.loads((sdesigns / f"{did}.json").read_text(encoding="utf-8"))

    try:
        code, st = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        if not case("v26 server: the first visit to the stories answers", code == 200 and st and st.get("ok") is True, (code, st and st.get("words"))):
            return
        A, STAMP = st["design"]["id"], st["stamp"]
        case("v26 server: the page is given her four templates, then her seven grids", [x["id"] for x in st["starters"]][:4] == [t[0] for t in HERS_TEMPLATES] and len(st["starters"]) == 11)
        case("v26 server: My editing queue says it is filled from the queue, and which text box", st["starters"][1].get("fill") == "queue" and isinstance(st["starters"][1].get("list"), int))
        case("v26 server: the set comes with its note for the assistant, empty to start with", st["design"].get("ask") == "")
        code, cst = J(get_json(P, f"/design-state?kit={KQ}"))
        case("v26 server: a carousel's design has no note, and its starters are the carousel's", "ask" not in cst["design"] and not any(x["id"].startswith("sg-") for x in cst["starters"]))
        CID = cst["design"]["id"]

        # ---------- the note, saved with the set ----------
        S1 = {"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, None, W), _frame(3, None, 2 * W), _text(4, 130, 806.4)]}
        rev = [st["design"]["rev"]]

        def save(state, did=A, page="v26serverpage01", **more):
            b = {"kit": kit_name, "kind": "stories", "design": did, "stamp": STAMP, "base": rev[0], "page": page, "state": state}
            b.update(more)
            code, out = J(post(P, "/design", b))
            if code == 200 and out and isinstance(out.get("rev"), int) and did == A:
                rev[0] = out["rev"]
            return code, out

        code, out = save(S1)
        case("v26 server: (a layout is saved into the first set)", code == 200 and out.get("ok"), (code, out))
        before = (sdesigns / f"{A}.json").read_bytes()
        note = "Start with the big laugh,\nthen the details."
        code, out = save(S1, ask=note)
        d = disk(A)
        case("v26 server: the note is kept with the set as \"ask\", the layout untouched, the counter one higher", code == 200 and out.get("ok") and d.get("ask") == note
             and d["state"] == json.loads(before)["state"] and d["rev"] == json.loads(before)["rev"] + 1 and "ask" not in d["state"], (code, out))
        case("v26 server: the set as it was before the note is kept beside it, byte for byte", (sdesigns / f"{A}.prev.json").read_bytes() == before)
        code, st2 = J(get_json(P, f"/design-state?kit={KQ}&kind=stories&design={A}"))
        case("v26 server: the page is given the note back with the set", st2["design"]["ask"] == note)
        kept = (sdesigns / f"{A}.json").read_bytes()
        code, out = save(S1, ask=note)
        case("v26 server: the same note again: ok, and nothing is written", code == 200 and out.get("ok") and (sdesigns / f"{A}.json").read_bytes() == kept, (code, out))
        code, out = save(S1)
        case("v26 server: a save that says nothing about the note keeps it", code == 200 and disk(A).get("ask") == note and (sdesigns / f"{A}.json").read_bytes() == kept)
        for what, bad in (("a number", 7), ("a list", ["a"]), ("601 letters", "x" * 601), ("nothing at all (null)", None)):
            code, out = save(S1, ask=bad)
            case(f"v26 server: a note that is {what} is refused in plain words, and the set is as it was",
                 code == 400 and out.get("ok") is False and out.get("why") == "ask" and isinstance(out.get("words"), str) and out["words"] and (sdesigns / f"{A}.json").read_bytes() == kept, (code, out))
        html = "<img src=x onerror=window.__pwn=1>\"'&"
        code, out = save(S1, ask=html)
        case("v26 server: a note that looks like page code is kept as the text it is", code == 200 and disk(A).get("ask") == html, (code, out))
        code, out = save(S1, ask="   ")
        case("v26 server: an emptied note is no note (the key is gone from the record)", code == 200 and "ask" not in disk(A), (code, out))
        code, out = save(S1, ask=note)
        cbefore = (cdesigns / f"{CID}.json").read_bytes()
        crow = json.loads(cbefore)
        code, out = J(post(P, "/design", {"kit": kit_name, "design": CID, "stamp": STAMP, "base": crow["rev"], "page": "v26serverpage02", "state": crow["state"], "ask": "sneaky"}))
        case("v26 server: a carousel takes no note: the key is dropped and nothing is written", code == 200 and (cdesigns / f"{CID}.json").read_bytes() == cbefore, (code, out))

        # ---------- a saved set, and the note never changing what is saved ----------
        JH = {"Content-Type": "image/jpeg"}
        STORIES = [jpeg(W, H, seed=i) for i in range(1, 8)]

        def slide(did, tok, i, of, data):
            code, _, out = ask(P, "POST", f"/design-slide?kit={KQ}&design={did}&set={tok}&i={i}&of={of}&kind=stories", body=data, headers=JH)
            return code

        def commit(did, tok, r, count):
            return J(post(P, "/design-commit", {"kit": kit_name, "kind": "stories", "design": did, "set": tok, "rev": r, "count": count}))

        oks = [slide(A, "v26set000001", i, 3, STORIES[i - 1]) for i in (1, 2, 3)]
        code, out = commit(A, "v26set000001", rev[0], 3)
        names_a = [f"Set beach stories - {i:02d}.jpg" for i in (1, 2, 3)]
        case("v26 server: Save stories from the first set: named after the set", oks == [200, 200, 200] and code == 200 and out.get("base") == "Set beach stories"
             and all((stories_dir / n).read_bytes() == STORIES[i] for i, n in enumerate(names_a)), (oks, code, out))
        saved_tree = _tree(stories_dir)
        code, out = save(S1, ask="Now end on the walk away instead.")
        code, out = commit(A, "v26set000002", rev[0], 3)
        case("v26 server: a changed NOTE alone makes nothing new to save: \"Already saved as ...\", and the Stories folder is byte for byte as it was",
             code == 200 and out.get("already") is True and _tree(stories_dir) == saved_tree, (code, out))

        # ---------- sets of stories ----------
        first_bytes = (sdesigns / f"{A}.json").read_bytes()
        code, out = J(post(P, "/design-new", {"kit": kit_name, "kind": "stories", "token": "v26newset00001", "stamp": STAMP, "state": {"slides": 1, "bg": "#ffffff", "blocks": []}}))
        B = out and out.get("design", {}).get("id")
        case("v26 server: + New set of stories: a second set is made, empty and white, named \"<Shoot> stories 2\"", code == 200 and B and B != A
             and out["design"]["name"] == "Set beach stories 2" and out["design"]["state"] == {"slides": 1, "bg": "#ffffff", "blocks": []} and out["design"]["ask"] == "", (code, out))
        case("v26 server: ... the first set's file is byte for byte as it was, and two sets are on the drive", (sdesigns / f"{A}.json").read_bytes() == first_bytes and files() == sorted([f"{A}.json", f"{B}.json"]))
        code, out2 = J(post(P, "/design-new", {"kit": kit_name, "kind": "stories", "token": "v26newset00001", "stamp": STAMP, "state": {"slides": 1, "bg": "#ffffff", "blocks": []}}))
        case("v26 server: the same press again (its answer was lost) gives the same set, never a third", code == 200 and out2["design"]["id"] == B and len(files()) == 2, (code, out2))
        case("v26 server: the list the page is given has both, the new one first", [x["id"] for x in out["designs"]] == [B, A] and [x["slides"] for x in out["designs"]] == [1, 3], out["designs"])
        code, sb = J(get_json(P, f"/design-state?kit={KQ}&kind=stories"))
        case("v26 server: with no set named, the page opens the one changed last", code == 200 and sb["design"]["id"] == B and sb["fell_back"] is False)
        code, sa = J(get_json(P, f"/design-state?kit={KQ}&kind=stories&design={A}"))
        case("v26 server: a set named by its id is the one opened, with its own layout and its own note",
             code == 200 and sa["design"]["id"] == A and sa["design"]["state"]["slides"] == 3 and sa["design"]["ask"] == "Now end on the walk away instead." and sa["fell_back"] is False)
        code, sx = J(get_json(P, f"/design-state?kit={KQ}&kind=stories&design={CID}"))
        case("v26 server: a carousel's design named as a set of stories is not one: the newest set, and the page is told", code == 200 and sx["design"]["id"] in (A, B) and sx["fell_back"] is True)
        case("v26 server: the shoot menu counts both sets, apart from the carousel's designs", next(x for x in sa["shoots"] if x["kit"] == kit_name)["story_designs"] == 2)
        code, out = J(post(P, "/design-new", {"kit": kit_name, "kind": "stories", "token": "v26newset00002", "stamp": STAMP, "state": {"slides": 1, "bg": "#ffffff", "blocks": []}}))
        C = out["design"]["id"]
        case("v26 server: a third set is \"<Shoot> stories 3\"", code == 200 and out["design"]["name"] == "Set beach stories 3", out["design"]["name"])
        # the kit shows the set SAVED last
        SB = {"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 5, 0), _frame(2, 6, W)]}
        code, out = J(post(P, "/design", {"kit": kit_name, "kind": "stories", "design": B, "stamp": STAMP, "base": 0, "page": "v26serverpage03", "state": SB}))
        rb = out.get("rev")
        oks = [slide(B, "v26set000003", i, 2, STORIES[i + 3]) for i in (1, 2)]
        code, out = commit(B, "v26set000003", rb, 2)
        names_b = [f"Set beach stories 2 - {i:02d}.jpg" for i in (1, 2)]
        case("v26 server: Save stories from the second set: its own files, named after it, beside the first set's (nothing replaced)",
             code == 200 and out.get("base") == "Set beach stories 2" and all((stories_dir / n).is_file() for n in names_b) and all(_tree(stories_dir).get(k) == v for k, v in saved_tree.items()), (code, out))
        sys.path.insert(0, str(SCRIPTS))
        os.environ["STUDIO_HOME"] = str(studio)
        import importlib
        import kit as kit_mod
        importlib.reload(kit_mod)
        sh = kit_mod.stories_shown(kit)
        case("v26 server: the kit shows the set saved LAST (the second), whole and in order", sh["kind"] == "laid-out" and [p.name for p in sh["files"]] == names_b, sh.get("base"))
        kit_mod.write_page(kit)
        m = re.search(r"<a class='piece' data-piece='stories' href='([^']*)'>(.*?)</a>", (kit / ".kit" / "Post kit.html").read_text(encoding="utf-8"), re.S)
        sect = m.group(2) if m else ""
        case("v26 server: the kit page's Stories card shows that set's stories and not the first set's", all(f"Stories/{n}" in sect for n in names_b) and not any(f"Stories/{n}" in sect for n in names_a), sect[:400])
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("v26 server: the kit's record keeps both saved sets, the newest named", rec["stories_set"]["base"] == "Set beach stories 2" and [x["base"] for x in rec["stories_laid_out"]] == ["Set beach stories", "Set beach stories 2"],
             [x["base"] for x in rec["stories_laid_out"]])
        code, outs = run(env, "design.py", "show", kit_name, "--kind", "stories")
        case("v26 server: design.py show --kind stories lists every set", code == 0 and all(f"\"{n}\"" in outs for n in ("Set beach stories", "Set beach stories 2", "Set beach stories 3")), outs[-500:])
        code, outo = run(env, "design.py", "open", kit_name, "--kind", "stories", "--design", A)
        case("v26 server: design.py open --kind stories --design opens that set (its id is in the address)", code == 0 and outo.strip().splitlines()[-1].endswith(f"&kind=stories&design={A}") and "3 sets of stories" in outo, outo[-400:])

        # ---------- the editing queue's names ----------
        code, _, raw = ask(P, "GET", "/design-queue")
        case("v26 server: with no editing queue yet, the names are an empty list", code == 200 and json.loads(raw) == {"ok": True, "names": [], "count": 0}, (code, raw[:200]))
        queue_file(studio, ["Garcia wedding", "<img src=x onerror=window.__pwn=1>", "Zoë & Été  family"],
                   more=[{"id": "z1", "name": "No date yet", "status": "waiting", "added": "2026-11-02T10:00:00"},
                         {"id": "z2", "name": "Delivered one", "status": "finished", "due": "2026-11-05"},
                         {"id": "z3", "name": "Archived one", "status": "archived"},
                         {"id": "z4", "name": "", "status": "waiting", "due": "2026-12-30"}])
        code, _, raw = ask(P, "GET", "/design-queue")
        q = json.loads(raw)
        seen.append(q)
        case("v26 server: the shoots still to edit, in the queue's order (soonest due first, undated last), as they named them; delivered and archived ones are not in it",
             code == 200 and q["ok"] and q["names"] == ["Garcia wedding", "<img src=x onerror=window.__pwn=1>", "Zoë & Été family", "No date yet"] and q["count"] == 4, q)
        case("v26 server: the answer is names and a count, nothing else (no id, no date, no folder)", sorted(q) == ["count", "names", "ok"])
        for what, headers, want in (("another website's ask", {"Sec-Fetch-Site": "cross-site"}, 403), ("another host's name", {"Host": "evil.example"}, 403)):
            code, _, raw = ask(P, "GET", "/design-queue", headers=headers)
            case(f"v26 server: the queue's names are refused to {what}", code == want and b"Garcia" not in raw, (code, raw[:120]))
        good_queue = (studio / "queue.json").read_bytes()
        (studio / "queue.json").write_text("{not a queue", encoding="utf-8")
        code, _, raw = ask(P, "GET", "/design-queue")
        case("v26 server: a queue that can't be read: her line, and the server stays up", code == 503 and json.loads(raw) == {"ok": False, "words": HERS["queue_cant"]}, (code, raw[:200]))
        (studio / "queue.json").write_bytes(good_queue)
        code, _, raw = ask(P, "GET", "/design-queue")
        case("v26 server: ... and answers again once it can", code == 200 and json.loads(raw)["count"] == 4)
        queue_file(studio, [f"Shoot {i}" for i in range(1, 15)])
        qstate = json.loads(json.dumps(st["starters"][1]["template"]))
        next(b for b in qstate["blocks"] if b["id"] == st["starters"][1]["list"])["text"] = "\n".join(f"{i}   Shoot {i}" for i in range(1, 13)) + "\n+ 2 more"
        code, out = J(post(P, "/design-template", {"kit": kit_name, "kind": "stories", "token": "v26queuetpl001", "name": "My queue look", "state": qstate}))
        case("v26 server: a filled-in My editing queue is ordinary text: Save as template takes it, words and all",
             code == 200 and out.get("ok") and [b["text"] for b in out["template"]["template"]["blocks"]][1].endswith("+ 2 more"), (code, out and out.get("words")))

        # ---------- the chat's side: story-note and story-fill ----------
        code, outn = run(env, "design.py", "story-note", kit_name, "--design", A)
        case("v26 server: story-note prints their note, word for word, and says to follow it", code == 0 and "THEIR NOTE (their words; follow it): Now end on the walk away instead." in outn, outn[-700:])
        case("v26 server: story-note lists the set's frames in the order they are filled, with which are empty, and that the words are theirs",
             "FRAMES: 3 (2 empty)" in outn and re.search(r"1\s+story 1\s+wants a tall photo\s+has photo 1", outn) and re.search(r"3\s+story 3\s+wants a tall photo\n", outn)
             and "never change, add or suggest them" in outn and f"--design {A}" in outn, outn[-700:])
        code, outn2 = run(env, "design.py", "story-note", kit_name)
        case("v26 server: story-note with no set named takes the one changed last, and lists the others", code == 0 and "This shoot has 3 sets of stories" in outn2 and "<- this one" in outn2, outn2[:500])
        pre = (sdesigns / f"{A}.json").read_bytes()
        prow = json.loads(pre)
        code, outf = run(env, "design.py", "story-fill", kit_name, "--photos", "8,12", "--design", A)
        d = disk(A)
        fr = [b for b in d["state"]["blocks"] if b.get("type") != "text"]
        case("v26 server: story-fill puts the pick into the EMPTY frames, in order; the photo that was there stays", code == 0 and "FILLED:" in outf and [b["n"] for b in fr] == [1, 8, 12], outf[-400:])
        case("v26 server: ... the text box is exactly as it was, the note is kept, the counter is one higher, and nothing else in the layout moved",
             [b for b in d["state"]["blocks"] if b.get("type") == "text"] == [b for b in prow["state"]["blocks"] if b.get("type") == "text"] and d["ask"] == prow["ask"]
             and d["rev"] == prow["rev"] + 1 and [(b["x"], b["y"], b["w"], b["h"]) for b in fr] == [(b["x"], b["y"], b["w"], b["h"]) for b in prow["state"]["blocks"] if b.get("type") != "text"], d["rev"])
        case("v26 server: ... the set as it was before the pick is kept beside it, byte for byte", (sdesigns / f"{A}.prev.json").read_bytes() == pre)
        code, out = save(S1)
        case("v26 server: a page that has not seen the pick is told there is something newer, and given it (its older layout is not saved over the pick)",
             code == 409 and out.get("why") == "newer" and [b.get("n") for b in out["design"]["state"]["blocks"] if b.get("type") != "text"] == [1, 8, 12], (code, out and out.get("why")))
        filled = (sdesigns / f"{A}.json").read_bytes()
        refusals = [
            ("every frame full already", ["--photos", "3", "--design", A], "already has a photo"),
            ("a photo that is not in the shoot", ["--photos", "99", "--design", A, "--replace"], "no photo numbered 99"),
            ("a photo given twice", ["--photos", "3,3", "--design", A, "--replace"], "more than once"),
            ("more photos than frames", ["--photos", "2,3,4,5", "--design", A, "--replace"], "Give 3 at the most"),
            ("a set that is not there", ["--photos", "3", "--design", "dnosuchset0001"], "no set of stories with the id"),
            ("an id that is not one", ["--photos", "3", "--design", "../etc"], "--design is the id"),
            ("numbers that are not numbers", ["--photos", "three", "--design", A], "numbers"),
        ]
        for what, args, words in refusals:
            code, o = run(env, "design.py", "story-fill", kit_name, *args)
            case(f"v26 server: story-fill refused: {what}; it says why, and the set is byte for byte as it was", code != 0 and words in o and (sdesigns / f"{A}.json").read_bytes() == filled, o[-300:])
        code, o = run(env, "design.py", "story-fill", kit_name, "--photos", "8,12", "--design", A)
        code, o = run(env, "design.py", "story-fill", kit_name, "--photos", "1,8,12", "--design", A, "--replace")
        case("v26 server: story-fill with the very pick the set holds: SAME, and nothing is written", code == 0 and "SAME:" in o and (sdesigns / f"{A}.json").read_bytes() == filled, o[-300:])
        code, o = run(env, "design.py", "story-fill", kit_name, "--photos", "9,10", "--design", A, "--replace")
        case("v26 server: story-fill --replace puts the pick into every frame in order; a frame it has no photo for is left as it was",
             code == 0 and [b["n"] for b in disk(A)["state"]["blocks"] if b.get("type") != "text"] == [9, 10, 12] and "1 frame left as it was" in o, o[-300:])
        code, o = run(env, "design.py", "story-fill", kit_name, "--photos", "2,4,6", "--design", C)
        dc = disk(C)
        case("v26 server: story-fill on a set with nothing on it: one story for each photo, each filling its story",
             code == 0 and dc["state"]["slides"] == 3 and [(b["n"], b["x"], b["w"], b["h"]) for b in dc["state"]["blocks"]] == [(2, 0, W, H), (4, W, W, H), (6, 2 * W, W, H)], o[-300:])
        code, o = run(env, "design.py", "story-fill", kit_name, "--photos", ",".join(str(i) for i in range(1, 15)) , "--design", C, "--replace")
        case("v26 server: (a set holds what it is given room for: 14 photos into 3 frames is refused)", code != 0 and "Give 3 at the most" in o, o[-200:])
        case("v26 server: no command touched a photo, and the Stories folder still holds both saved sets exactly", _tree(kit / "Photos") == photos_before
             and all(_tree(stories_dir).get(k) == v for k, v in saved_tree.items()))
        text = [s for a in seen for s in _strings(a)]
        case("v26 server: no answer held a path or a file's name of a record", not any(str(target) in s or str(studio) in s or "/private/" in s or ".json" in s for s in text))
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
  // what Copy copies (a hidden Chrome has no clipboard to read back): the box the page selects for the copy call
  var copy = document.execCommand;
  document.execCommand = function(cmd){
    if (cmd === 'copy') { var a = document.activeElement; window.__copied = a && typeof a.value === 'string' ? a.value : null; return true; }
    return copy.apply(document, arguments);
  };
})();
"""


def check_v26_browser(case, work, port, make_kit, Server, post, get_json, run):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  v26 on the real page: no Chrome on this computer", flush=True)
        return
    target = work / "v26-browser"
    ok, out = make_kit(target, "Lake day", 40)
    if not case("v26 browser: the pretend kit was made", ok, out):
        return
    ok, out = make_kit(target, "Old way", 8)
    if not case("v26 browser: a second pretend kit was made (a shoot whose stories are from before v26)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio), STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none")
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Lake day"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    sdesigns, cdesigns = kit / ".kit" / "story-designs", kit / ".kit" / "designs"
    queue_file(studio, ["<img src=x onerror=window.__pwn=1>"] + [f"Shoot {i}" for i in range(2, 15)])
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    try:
        with cd.Chrome(work=work / "chrome-v26", size=(1400, 1000)) as c:
            c.init_script(NO_FINDER_JS)

            def Jx(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return Jx("Designer.st")

            def did():
                return c.js("Designer.design.id")

            def disk(i=None, folder=sdesigns):
                return json.loads((folder / f"{i or did()}.json").read_text(encoding="utf-8"))

            def ready(seconds=40):
                c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def settled(seconds=12, folder=sdesigns):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                return disk(folder=folder)["state"] == st()

            def gallery_open():
                return c.js("!document.getElementById('gallery').hidden")

            def add(section, nth, wait=True):
                if not gallery_open():
                    c.click("#new-design")
                    c.wait_for("!document.getElementById('gallery').hidden", 5)
                c.click(f"#gallery-{section} .dz-card:nth-child({nth}) .dz-use")
                if wait:
                    c.wait_for("document.getElementById('gallery').hidden", 8)

            def fonts_in(seconds=25):
                """The words' fonts have arrived (or given up) and every text box is as tall as its lines: only then is
                a layout with words in it what it will stay."""
                c.wait_for("Designer.st.blocks.every(function(b){ return b.type !== 'text' || Designer.type.status(b) !== 'wait'; }) && Designer.type.fit(Designer.st) === Designer.st", seconds)

            def frames(s):
                return [b for b in s["blocks"] if b.get("type") != "text"]

            def texts(s):
                return [b for b in s["blocks"] if b.get("type") == "text"]

            def buttons():
                return Jx("{undo: !document.getElementById('undo').disabled, redo: !document.getElementById('redo').disabled}")

            c.open(f"{base}/design.html?kit={KQ}&kind=stories")
            ready()
            c.wait_for("!document.getElementById('gallery').hidden", 5)
            A = did()
            # ---- what the page shows ----
            words = Jx("{bands: document.getElementById('gridcrop').parentNode.textContent.trim(), ask: document.getElementById('ask-pick').textContent, "
                       "redo: document.getElementById('redo').textContent, name: document.getElementById('d-name-box').value, nameShown: !document.getElementById('d-name-box').hidden, "
                       "sets: document.getElementById('designs-btn').textContent, setsShown: !document.getElementById('designs-btn').hidden, "
                       "newSet: document.getElementById('new-set').textContent, dup: !document.getElementById('dup-design').hidden, box: document.getElementById('ask-box').hidden, "
                       "lede: document.querySelector('.lede').textContent}")
            case("v26 browser: the stories page: her tick, her button, Redo, the set's name in its box, My story sets, + New set of stories; no Duplicate; the box closed",
                 words["bands"] == HERS["bands"] and words["ask"] == HERS["ask_button"] and words["redo"] == "Redo" and words["name"] == "Lake day stories" and words["nameShown"]
                 and words["sets"] == "My story sets ▾" and words["setsShown"] and words["newSet"] == HERS["new_set"] and words["dup"] is False and words["box"] is True, words)
            case("v26 browser: her intro ends by saying how to hide the bands", words["lede"].endswith(HERS["lede_end"]), words["lede"][-80:])
            names = Jx("Array.from(document.querySelectorAll('#gallery-starters .dz-cap b')).map(function(x){ return x.textContent; })")
            subs = Jx("Array.from(document.querySelectorAll('#gallery-starters .dz-cap small')).map(function(x){ return x.textContent; })")
            case("v26 browser: the Add stories window: her four templates first, in her order, then her seven grids",
                 names == ["Gallery delivered", "My editing queue", "The full story", "Seamless swipe"] + GRID_NAMES, names)
            case("v26 browser: ... each says how many stories and photos it has", subs[:4] == ["4 stories · 7 photos", "1 story · 0 photos", "10 stories · 18 photos", "6 stories · 5 photos"], subs[:4])
            # ---- Gallery delivered ----
            add("starters", 1)
            fonts_in()
            s1 = st()
            f1, t1 = frames(s1), texts(s1)
            case("v26 browser: Gallery delivered added to an empty set: four stories, her seven frames, each with a photo of this shoot (none twice)",
                 s1["slides"] == 4 and [(b["x"], b["y"], b["w"], b["h"]) for b in f1] == [tuple(f) for f in HERS_TEMPLATES[0][4]] and all(b["n"] for b in f1) and len({b["n"] for b in f1}) == 7, s1["slides"])
            case("v26 browser: ... her five lines of placeholder words, each on its own story",
                 [b["text"] for b in t1] == [t[3] for t in HERS_TEMPLATES[0][5]] and [int((b["x"] + b["w"] / 2) // W) for b in t1] == [0, 0, 1, 2, 3], [b["text"] for b in t1])
            case("v26 browser: ... the words are ordinary story text: they can be picked and changed like any text box",
                 all(b["font"] == "Figtree" and b["look"] == "box" for b in t1) and c.count("#strip .blk.words") + c.count("#strip .blk") >= 12)
            case("v26 browser: the set saves itself as always", settled())
            # ---- the x on each story's label ----
            lab = Jx("Array.from(document.querySelectorAll('#labels > span')).map(function(s){ var x = s.querySelector('.labx'); return [s.firstChild.textContent, !!x && !x.hidden, x && x.title, x && x.getAttribute('aria-label')]; })")
            case("v26 browser: every story's label has a small x, named for the story it removes", lab == [[f"Story {k}", True, f"Remove story {k}", f"Remove story {k}"] for k in (1, 2, 3, 4)], lab)
            add("fresh", 1)
            s2 = st()
            case("v26 browser: (a blank story added at the end: five stories, the fifth empty)", s2["slides"] == 5 and s2["blocks"] == s1["blocks"])
            c.click("#labels .labx", nth=4)
            s3 = st()
            line = c.text("#slides-line")
            case("v26 browser: the x on an EMPTY story removes it (\"Remove this story\" could not): four stories, everything else as it was", s3["slides"] == 4 and s3["blocks"] == s1["blocks"], s3["slides"])
            case("v26 browser: ... and the line says so, in her words", line == "Removed story 5. Undo brings it back.", line)
            c.click("#undo")
            case("v26 browser: Undo brings the story back", st() == s2)
            c.click("#labels .labx", nth=1)
            s4 = st()
            gone = [b["id"] for b in s2["blocks"] if W <= b["x"] + b["w"] / 2 < 2 * W]
            moved = {b["id"]: b["x"] for b in s2["blocks"] if b["x"] >= 2 * W}
            case("v26 browser: the x on story 2 takes out that story and what is on it; the stories after it move up; nothing else changes",
                 s4["slides"] == 4 and len(gone) == 4 and not any(b["id"] in gone for b in s4["blocks"]) and all(b["x"] == moved[b["id"]] - W for b in s4["blocks"] if b["id"] in moved)
                 and [b for b in s4["blocks"] if b["id"] not in moved] == [b for b in s2["blocks"] if b["id"] not in moved and b["id"] not in gone], (s4["slides"], gone))
            case("v26 browser: ... its line names the story", c.text("#slides-line") == "Removed story 2. Undo brings it back.", c.text("#slides-line"))
            # ---- Redo ----
            case("v26 browser: after a change Undo is on and Redo is off", buttons() == {"undo": True, "redo": False}, buttons())
            c.click("#undo")
            case("v26 browser: Undo brings story 2 back exactly, and Redo comes on", st() == s2 and buttons()["redo"] is True, buttons())
            c.click("#redo")
            case("v26 browser: Redo takes it out again, exactly as before; Redo goes off, Undo stays on", st() == s4 and buttons() == {"undo": True, "redo": False}, buttons())
            case("v26 browser: what Redo did is saved like any change", settled())
            c.key("Mod+z")
            a = st()
            c.key("Mod+Shift+z")
            b = st()
            c.key("Mod+z")
            c.key("Mod+y")
            b2 = st()
            case("v26 browser: the keys: Cmd+Z undoes, Cmd+Shift+Z redoes, Cmd+Y redoes too", a == s2 and b == s4 and b2 == s4, (a["slides"], b["slides"], b2["slides"]))
            c.key("Mod+z")
            c.key("Mod+z")
            case("v26 browser: Undo goes back step by step (to the four stories as they were added)", st() == s1, st()["slides"])
            c.click("#redo")
            c.click("#redo")
            case("v26 browser: ... and Redo forward again, step by step", st() == s4 and buttons()["redo"] is False)
            c.click("#undo")
            c.click("#g-bg .sw[data-c='#f4efe6']")
            s5 = st()
            case("v26 browser: a new change after an Undo empties Redo (there is nothing to redo any more)", s5["bg"] == "#f4efe6" and s5["blocks"] == s2["blocks"] and buttons() == {"undo": True, "redo": False}, buttons())
            c.click("#undo")
            c.click("#labels .labx", nth=4)
            sA = st()
            case("v26 browser: (back to four stories on white for what follows)", sA["slides"] == 4 and sA["bg"] == "#ffffff" and sA["blocks"] == s1["blocks"] and settled())
            # ---- Let my assistant choose the photos ----
            c.click("#ask-pick")
            box = Jx("{open: !document.getElementById('ask-box').hidden, exp: document.getElementById('ask-pick').getAttribute('aria-expanded'), "
                     "head: document.querySelector('#ask-box label b').textContent, label: document.querySelector('#ask-box label').textContent, "
                     "ex: document.querySelector('#ask-box .ask-ex').textContent, place: document.getElementById('ask-note').placeholder, "
                     "then: document.querySelector('#ask-box p').textContent, line: document.getElementById('ask-words').textContent, "
                     "copy: document.getElementById('ask-copy').textContent, focus: document.activeElement.id}")
            case("v26 browser: the button opens her box, with her words, and the note's box has the keyboard",
                 box["open"] and box["exp"] == "true" and box["head"] == HERS["ask_head"] and box["label"] == HERS["ask_head"] + " " + HERS["ask_sub"] + HERS["ask_example"]
                 and box["ex"] == HERS["ask_example"] and box["place"] == HERS["ask_place"] and box["then"] == HERS["ask_then"] and box["copy"] == "Copy" and box["focus"] == "ask-note", box)
            case("v26 browser: with no note the line to copy is \"Pick my story photos for <shoot>\"", box["line"] == "Pick my story photos for Lake day", box["line"])
            note = "Start with the big laugh, then the details."
            c.type_text(note)
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            d = disk(A)
            case("v26 browser: a note typed in the box is saved with the set as \"ask\"", d.get("ask") == note, d.get("ask"))
            case("v26 browser: ... the stories are exactly as they were", d["state"] == sA and st() == sA)
            c.click("#undo")
            und = st()
            c.click("#redo")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            case("v26 browser: ... and the note is no Undo step: Undo takes back the last change to the stories (the fifth story is back), Redo returns, and the note is still there",
                 und["slides"] == 5 and st() == sA and c.js("document.getElementById('ask-note').value") == note and disk(A).get("ask") == note, (und["slides"], disk(A).get("ask")))
            case("v26 browser: with a note the line ends \", and follow my note\"", c.text("#ask-words") == "Pick my story photos for Lake day, and follow my note", c.text("#ask-words"))
            c.click("#ask-copy")
            copied = c.js("window.__copied")
            case("v26 browser: Copy copies exactly the line on the screen, and the button says Copied", copied == "Pick my story photos for Lake day, and follow my note" and c.text("#ask-copy") == "Copied", copied)
            c.wait_for("document.getElementById('ask-copy').textContent === 'Copy'", 4)
            case("v26 browser: ... then Copy again", c.text("#ask-copy") == "Copy" and c.js("Designer.ask.watching()") is True)
            # ---- the chat's side, and the open page taking the pick ----
            code, outn = run(env, "design.py", "story-note", kit_name, "--design", A)
            case("v26 browser: the assistant's story-note reads the very note they typed", code == 0 and f"THEIR NOTE (their words; follow it): {note}" in outn and "FRAMES: 7 (0 empty)" in outn, outn[-500:])
            code, outf = run(env, "design.py", "story-fill", kit_name, "--photos", "31,32,33,34,35,36,37", "--design", A, "--replace")
            case("v26 browser: (the assistant's pick is put in from the chat)", code == 0 and "FILLED:" in outf, outf[-300:])
            try:
                c.wait_for("Designer.st.blocks.filter(function(b){ return b.type !== 'text'; }).map(function(b){ return b.n; }).join(',') === '31,32,33,34,35,36,37'", 14)
                took = True
            except cd.Timeout:
                took = False
            sF = st()
            case("v26 browser: the open page shows the assistant's pick by itself, within a few seconds of it landing", took, [b.get("n") for b in frames(sF)])
            case("v26 browser: ... the words on the stories are untouched, the note is still in its box, and a quiet line says the pick is in",
                 texts(sF) == texts(sA) and c.js("document.getElementById('ask-note').value") == note and c.text("#ask-said") == "Your assistant’s pick is in your stories.", c.text("#ask-said"))
            case("v26 browser: ... nothing of it was sent back as a change of theirs (the set on the drive is the assistant's, once)", disk(A)["state"] == sF and disk(A).get("filled_by") == "assistant")
            note_box = Jx("{v: document.getElementById('ask-note').value}")
            c.click("#ask-note")
            c.key("Mod+a")
            c.key("Backspace")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            case("v26 browser: the note emptied: the line loses \", and follow my note\", and the record has no note", c.text("#ask-words") == "Pick my story photos for Lake day" and "ask" not in disk(A), (note_box, c.text("#ask-words")))
            c.type_text("Keep it wide")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            # ---- sets of stories ----
            c.click("#new-set")
            c.wait_for(f"Designer.design && Designer.design.id !== '{A}' && Designer.save.idle()", 15)
            B = did()
            sB = st()
            newset = Jx("{name: document.getElementById('d-name-box').value, gallery: !document.getElementById('gallery').hidden, search: location.search, "
                        "note: document.getElementById('ask-note').value, line: document.getElementById('ask-words').textContent, "
                        "x: Array.from(document.querySelectorAll('#labels .labx')).filter(function(x){ return !x.hidden; }).length}")
            case("v26 browser: + New set of stories: a new set, \"<Shoot> stories 2\", one empty white story, opened at once", sB == {"slides": 1, "bg": "#ffffff", "blocks": []} and newset["name"] == "Lake day stories 2", newset)
            case("v26 browser: ... the Add stories window is not thrown open over it (hers), and the address names the set", newset["gallery"] is False and f"design={B}" in newset["search"] and "kind=stories" in newset["search"], newset)
            case("v26 browser: ... the new set has no note of its own, and a lone story has no x", newset["note"] == "" and newset["line"] == "Pick my story photos for Lake day" and newset["x"] == 0, newset)
            case("v26 browser: ... the first set is on the drive exactly as it was left, with its note", disk(A)["state"] == sF and disk(A).get("ask") == "Keep it wide" and disk(A)["name"] == "Lake day stories")
            c.click("#designs-btn")
            c.wait_for("!document.getElementById('designs-pop').hidden", 5)
            time.sleep(0.6)             # the list is asked for again as the menu opens
            pop = Jx("{head: document.querySelector('#designs-pop .dz-pophead').textContent, items: Array.from(document.querySelectorAll('#designs-pop .dz-item')).map(function(b){ "
                     "return [b.querySelector('b').textContent, b.querySelector('small').textContent, b.classList.contains('cur')]; })}")
            case("v26 browser: My story sets: her heading, both sets, the newest first, the open one marked", pop["head"] == "Lake day story sets" and [x[0] for x in pop["items"]] == ["Lake day stories 2", "Lake day stories"]
                 and [x[2] for x in pop["items"]] == [True, False], pop)
            case("v26 browser: ... each line says how many stories and when it was edited (her words)", pop["items"][0][1].startswith("1 story · edited ") and pop["items"][0][1].endswith(" · open now")
                 and pop["items"][1][1].startswith("4 stories · edited "), [x[1] for x in pop["items"]])
            c.click("#designs-pop .dz-item", nth=1)
            c.wait_for(f"Designer.design && Designer.design.id === '{A}'", 15)
            case("v26 browser: a set picked from the menu opens as it was left: its stories, its name, its note", st() == sF and c.js("document.getElementById('d-name-box').value") == "Lake day stories"
                 and c.js("document.getElementById('ask-note').value") == "Keep it wide" and not gallery_open(), st()["slides"])
            # (the second set was made after the first was last changed, so the first is NOT the one changed last here)
            newest = get_json(P, f"/design-state?kit={KQ}&kind=stories")[1]["design"]["id"]
            c.reload()
            ready()
            case("v26 browser: a reload opens the same set (its id is in the address), though another set was changed since", newest == B and did() == A and st() == sF and not gallery_open(), (newest, did()))
            c.click("#d-name-box")
            c.key("Mod+a")
            c.type_text("Sneak peek set")
            c.key("Enter")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            case("v26 browser: a set is renamed in its box, like a carousel's design", disk(A)["name"] == "Sneak peek set" and disk(A)["state"] == sF, disk(A)["name"])
            # ---- My editing queue ----
            add("starters", 2)
            fonts_in()
            sQ = st()
            new = [b for b in sQ["blocks"] if b["x"] >= 4 * W]
            rows = new[1]["text"].split("\n") if len(new) == 3 else []
            case("v26 browser: My editing queue added: one more story, no photo on it, three text boxes; the stories before it untouched",
                 sQ["slides"] == 5 and len(new) == 3 and all(b.get("type") == "text" for b in new) and [b for b in sQ["blocks"] if b["x"] < 4 * W] == sF["blocks"], sQ["slides"])
            case("v26 browser: ... her title and her closing line, as written", len(new) == 3 and new[0]["text"] == HERS["queue_title"] and new[2]["text"] == HERS["queue_closing"])
            case("v26 browser: ... the list is the editing queue in its order, as the shoots are named: twelve, then \"+ 2 more\"",
                 rows == ["1   <img src=x onerror=window.__pwn=1>"] + [f"{i}   Shoot {i}" for i in range(2, 13)] + ["+ 2 more"], rows)
            case("v26 browser: ... a shoot's name is on the page as text only (nothing in it ran)", c.js("window.__pwn === undefined") and "<img src=x" in c.js("document.getElementById('strip').textContent"))
            case("v26 browser: ... centered, plain, in her sizes, and the list's box is as tall as its lines", len(new) == 3 and [(b["size"], b["look"], b["al"]) for b in new] == [(60, "plain", "center"), (40, "plain", "center"), (34, "plain", "center")]
                 and new[2]["italic"] is True and new[1]["h"] >= 13 * 40 * 1.7 - 1, [(b["size"], b["h"]) for b in new])
            case("v26 browser: ... saved like any change", settled())
            good = (studio / "queue.json").read_bytes()
            (studio / "queue.json").write_text("{broken", encoding="utf-8")
            add("starters", 2, wait=False)
            c.wait_for("document.getElementById('gallery-line').textContent !== ''", 8)
            case("v26 browser: when the editing queue can't be read: her line, in the window, which stays open; nothing is added",
                 c.text("#gallery-line") == HERS["queue_cant"] and gallery_open() and st() == sQ, c.text("#gallery-line"))
            queue_file(studio, [])
            add("starters", 2)
            fonts_in()
            sE = st()
            case("v26 browser: with nothing in the editing queue the list says her line", sE["slides"] == 6 and [b["text"] for b in sE["blocks"] if b["x"] >= 5 * W][1] == HERS["queue_empty"])
            (studio / "queue.json").write_bytes(good)
            # ---- Seamless swipe, The full story ----
            add("starters", 4)
            sS = st()
            wide = [b for b in sS["blocks"] if b["x"] >= 6 * W and b.get("type") != "text"]
            case("v26 browser: Seamless swipe added: six more stories, and one photo lies across the first three of them",
                 sS["slides"] == 12 and len(wide) == 5 and wide[0]["x"] == 6 * W and wide[0]["w"] == 3 * W and wide[0]["h"] == H and wide[0]["n"], (sS["slides"], wide[:1]))
            add("starters", 3)
            fonts_in()
            sL = st()
            case("v26 browser: The full story added: ten more stories, eighteen frames and her two lines of placeholder words",
                 sL["slides"] == 22 and len([b for b in sL["blocks"] if b["x"] >= 12 * W and b.get("type") != "text"]) == 18
                 and [b["text"] for b in sL["blocks"] if b["x"] >= 12 * W and b.get("type") == "text"] == ["Your words here", "Your words here"], sL["slides"])
            case("v26 browser: one Undo takes a whole template back; Redo puts it back", (c.click("#undo"), st() == sS)[1] and (c.click("#redo"), st() == sL)[1])
            case("v26 browser: settled", settled())
            # ---- the stories stay in view while the photos scroll ----
            c.js("window.scrollTo(0, document.documentElement.scrollHeight)")
            time.sleep(0.3)
            view = Jx("(function(){ var s = document.getElementById('stage').getBoundingClientRect(), t = document.querySelectorAll('#thumbs .th'), last = t[t.length - 1].getBoundingClientRect(); "
                      "return {y: window.scrollY, top: s.top, bottom: s.bottom, last: last.top, h: window.innerHeight, pos: getComputedStyle(document.getElementById('stage')).position}; })()")
            case("v26 browser: scrolled down to the last photo, the stories are still at the top of the window (the stage sticks; the photos scroll under it)",
                 view["y"] > 150 and view["pos"] == "sticky" and abs(view["top"]) <= 1 and view["bottom"] > 100 and view["last"] < view["h"], view)
            c.js("window.scrollTo(0, 0)")

        # ---- a shoot's one stories design from before v26 is its first set ----
        other = "2026-11-01 Old way"
        okit = target / "The Assistant" / "Your Content" / other
        code, ost = get_json(P, f"/design-state?kit={quote(other)}&kind=stories")
        OLD = ost["design"]["id"]
        code, o = post(P, "/design", {"kit": other, "kind": "stories", "design": OLD, "stamp": ost["stamp"], "base": 0, "page": "v26oldpage0001",
                                      "state": {"slides": 2, "bg": "#ffffff", "blocks": [_frame(1, 1, 0), _frame(2, 2, W)]}})
        ofile = okit / ".kit" / "story-designs" / f"{OLD}.json"
        rec = json.loads(ofile.read_text(encoding="utf-8"))
        rec.pop("ask", None)            # as the Assistant wrote a shoot's one stories design before v26: no note
        ofile.write_text(json.dumps(rec), encoding="utf-8")
        old_bytes = ofile.read_bytes()
        with cd.Chrome(work=work / "chrome-v26-old", size=(1400, 1000)) as c:
            c.init_script(NO_FINDER_JS)
            c.open(f"{base}/design.html?kit={quote(other)}&kind=stories")
            c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 40)
            got = json.loads(c.js("JSON.stringify({id: Designer.design.id, st: Designer.st, name: document.getElementById('d-name-box').value, gallery: !document.getElementById('gallery').hidden, "
                                  "sets: (Designer.S.designs || []).length})"))
            case("v26 browser: a shoot's stories from before v26 open as its first set: the same design, its stories, its name, nothing asked",
                 got["id"] == OLD and got["st"] == rec["state"] and got["name"] == "Old way stories" and got["gallery"] is False and got["sets"] == 1, got)
            time.sleep(1.2)
            case("v26 browser: ... and opening it wrote nothing: its file is byte for byte as it was", ofile.read_bytes() == old_bytes)
            c.click("#new-set")
            c.wait_for(f"Designer.design && Designer.design.id !== '{OLD}' && Designer.save.idle()", 15)
            case("v26 browser: ... a second set beside it leaves it exactly as it was", ofile.read_bytes() == old_bytes and c.js("document.getElementById('d-name-box').value") == "Old way stories 2")

        # ---- the carousel's designer: Redo, and nothing else of v26 ----
        with cd.Chrome(work=work / "chrome-v26-car", size=(1400, 1000)) as c:
            c.init_script(NO_FINDER_JS)
            c.open(f"{base}/design.html?kit={KQ}")
            c.wait_for("window.Designer && Designer.saver && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", 40)
            c.wait_for("Designer.save.idle()", 10)
            car = json.loads(c.js("JSON.stringify({ask: !!document.getElementById('ask-pick'), box: !!document.getElementById('ask-box'), x: document.querySelectorAll('#labels .labx').length, "
                                  "newSet: !!document.getElementById('new-set'), labels: Array.from(document.querySelectorAll('#labels span')).map(function(s){ return s.textContent; }).slice(0, 2), "
                                  "redo: document.getElementById('redo').disabled, dup: !document.getElementById('dup-design').hidden, mine: document.getElementById('designs-btn').textContent, "
                                  "asked: !!Designer.ask})"))
            case("v26 browser: the carousel's designer has no assistant button, no note, no x on a label and no sets; its labels and buttons read as before",
                 car == {"ask": False, "box": False, "x": 0, "newSet": False, "labels": ["Slide 1", "Slide 2"], "redo": True, "dup": True, "mine": "My designs ▾", "asked": False}, car)
            c0 = json.loads(c.js("JSON.stringify(Designer.st)"))
            c.click("#g-bg .sw[data-c='#111111']")
            c1 = json.loads(c.js("JSON.stringify(Designer.st)"))
            c.click("#undo")
            back = json.loads(c.js("JSON.stringify(Designer.st)"))
            c.click("#redo")
            again = json.loads(c.js("JSON.stringify(Designer.st)"))
            case("v26 browser: the carousel's designer: Redo puts back what Undo took back", c1["bg"] == "#111111" and back == c0 and again == c1 and c.js("document.getElementById('redo').disabled") is True)
            c.key("Mod+z")
            c.key("Mod+y")
            c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 10)
            cid = c.js("Designer.design.id")
            on_disk = json.loads((cdesigns / f"{cid}.json").read_text(encoding="utf-8"))
            case("v26 browser: ... with the keys too, and it is saved; the carousel's record has no note in it", on_disk["state"] == c1 and "ask" not in on_disk, on_disk["state"]["bg"])
    finally:
        srv.stop()


def main():
    """By itself (GitHub's Mac page job, or by hand): the three parts, on a work folder under /private/tmp."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9660)
    ap.add_argument("--no-chrome", action="store_true", help="the tables, words, rules, routes and commands only; the real page is not opened")
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
    check_v26_page(dc.case, work)
    try:
        check_v26_server(dc.case, work, a.port, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.ask, dc.run, dc.jpeg)
    except Exception as e:  # noqa: BLE001
        import traceback
        dc.case("the checks of v26's routes and commands ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    if not a.no_chrome:
        try:
            check_v26_browser(dc.case, work, a.port + 2, dc.make_kit, dc.Server, dc.post, dc.get_json, dc.run)
        except Exception as e:  # noqa: BLE001
            import traceback
            dc.case("the real-browser checks of v26 ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    bad = [n for n, ok in dc.results if not ok]
    print()
    print(f"{len(dc.results)} cases, {len(dc.results) - len(bad)} passed, {len(bad)} failed.  Work folder: {work}")
    for n in bad:
        print("  FAILED: " + n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
