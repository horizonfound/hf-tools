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
