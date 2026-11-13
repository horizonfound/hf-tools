#!/usr/bin/env python3
"""Several clips picked at once on the talking reel page's timeline (ours, on top of Nicole's v24; Dustin, Nov 12:
"I held down Command and clicked another one... the effect just automatically apply across all 3... they are joined
and then it becomes one long zoom... that's how other video editors work").

    python3 tests/guard.py 3000 python3 tests/talking_multi_check.py [--no-chrome] [--port 9650] [--work <folder>]

Run it under the memory guard, ONE such test at a time (it drives a hidden Chrome).

By request and in Python (no browser):
  - our words for it are ours (in talking_page.OUR_WORDS, each with its reason, none of them hers), her help line
    is untouched, a PC's line names Ctrl, and the page carries the second line under hers;
  - what a press with several clips sends is taken by the Assistant's side as it stands: one slow zoom across a
    run of clips (the cut words between two of them included) gives every piece of the run the same zoom, and in
    the CapCut plan (built here, never written into CapCut) its keyframes run 1.0 to 1.12 across the whole run
    and meet where one piece hands over to the next;
  - two zooms that overlap are told apart from what the page sends: the page never sends such a list.
On the real page, in a hidden Chrome, with real Command, Ctrl and Shift clicks:
  - Command-click adds a clip and takes it out; Shift-click picks the run from the clip clicked last; both
    together add a run; a plain click picks just one; Escape lets go of several; on a Mac a Control-click is
    still the right click; as a PC, Ctrl-click adds;
  - every picked clip LOOKS picked (her own mark), the little x is not drawn, the button reads "Delete 3 clips",
    the line under her help line says how many, the script outlines every picked clip's words;
  - Slow zoom: one zoom across clips side by side (also across cut words), a zoom each for clips that do not
    touch, a zoom that reached past the picked clips trimmed and not lost; clips already inside one long slow
    zoom left as they are (nothing saved);
  - Punch in on each, None on all, Speed on each, Delete on all (button and key), Split as ever;
  - one press is ONE step of Undo and one of Redo, by button and by key;
  - with ONE clip picked, what the page sends is byte for byte what her code sends (the exact text of each save),
    and every line of the timeline's script as it was before this (commit eb2e9d9, kept in tests/fixtures) is
    still there, in order, but for the lines named below (sixteen changed for this, and the chips' own lines,
    which went when Speed and Zoom became two small menus on Nov 13: tests/talking_menus_check.py);
  - a reload keeps what was done; a picked clip the chat cuts drops out; phone width does not break; no page
    error, nothing asked of the internet, every word on the page as text.

What it never does: touch the real ~/.studio (STUDIO_HOME is a scratch folder; the real one is listed before and
after), start the real transcriber, write into CapCut, or play a video. The page server (port 9650 up) and the
hidden Chrome are this test's own and are stopped at the end.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import talking_page_check as t  # noqa: E402
import talking_page_timeline as tpt  # noqa: E402

PORT = 9650
KIT = "2026-09-29 Zoë's <b>several clips" if not t.WINDOWS else "2026-09-29 Zoë's several clips"
TALK = "talk.mp4"
BEFORE = "eb2e9d9"          # the commit before several clips could be picked
JS_FILE = "plugins/the-engine/skills/studio-manager/scripts/talking_js_timeline.py"
OLD_SCRIPT = "talking_js_timeline_before_several.txt"      # that file at commit BEFORE, kept so the check runs anywhere

# 21 words in seven sentences of three: seven clips, c0..c6, whose first words are 0, 3, 6, 9, 12, 15, 18.
SAID = ["One", "two", "three.", "Four", "<b>five</b>", "six.", "Seven", "eight", "nine.", "Ten", "eleven", "twelve.",
        "Thirteen", "fourteen", "fifteen.", "Sixteen", "seventeen", "eighteen.", "Nineteen", "twenty", "done."]
WORDS = [{"w": w, "start": round(0.05 + 0.13 * i, 3), "end": round(0.14 + 0.13 * i, 3), "conf": 0.9} for i, w in enumerate(SAID)]
FIRST = [0, 3, 6, 9, 12, 15, 18]
CLEAN = {"cut": [], "splits": [], "speeds": [], "zooms": [], "shots": []}

# The lines of the timeline's script that were CHANGED for this (everything else is only added): as they were.
CHANGED_LINES = [
    "What it gives the other parts: T.pickedWords() (the words of the clip picked, for the script's outline),",
    "T.renderTimeline(), T.tl() (what a test may read: {pps, selw, sel, drag, making}).",
    "  var sel = selPiece(), clips = document.createDocumentFragment();",
    "    var d = el('div', 'tl-clip' + (p === sel ? ' on' : '') + (p.speed !== 1 ? ' fast' : ''));",
    "    if (TLSEL === 'clip' && p === sel) d.appendChild(round_x(W.tl_clip_x));",
    "  var p = selPiece(), zk = zoomKind(p);",
    "  $('tlCut').textContent = ph ? W.delete_photo : W.delete_clip;",
    "    var on = !!p && p.speed === SPEEDS[k];",
    "    var on = !!p && zk === MOVES[k][0];",
    "  if (e.button !== 0 || e.ctrlKey || drag || !T.ready()) return;      // a Control-click is the Mac's right click",
    "    SELW = drag.w0;",
    "  SELW = best;",
    "    cutClip(); TLSEL = null;",
    "  if (!a.ready) { if (drag) endDrag(null, true); SELW = null; TLSEL = null; return; }",
    "T.pickedWords = function(){ var p = selPiece(); return p ? p.words : []; };",
    "T.tl = function(){ return {pps: PPS, selw: SELW, sel: TLSEL, drag: !!drag, making: making}; };",
]

# The lines that went when Speed and Zoom became two small menus (Dustin, Nov 13): the chips themselves, how each was
# lit, and two lines of notes. What a choice DOES is not among them: speedClip and zoomClip are as they were (the
# case under this one holds their words), and tests/talking_menus_check.py holds what each choice sends.
MENU_LINES = [
    '    its words. Speed and Zoom chips are grey with no clip picked; badges "1.5x", "Punch in", "Slow zoom";',
    "// the chips are made once; a press looks up the clip picked at that moment",
    "var speedChips = SPEEDS.map(function(v){",
    "  var b = el('button', 'chip', T.fill(W.speed_x, {v: v}));",
    "  b.type = 'button'; b.disabled = true; b.setAttribute('data-v', v);",
    "  b.addEventListener('click', function(){ speedClip(v); });",
    "  $('tlSpeed').appendChild(b);",
    "  return b;",
    "});",
    "var zoomChips = MOVES.map(function(m){",
    "  var b = el('button', 'chip', m[1]);",
    "  b.type = 'button'; b.disabled = true; b.setAttribute('data-z', m[0]);",
    "  b.addEventListener('click', function(){ zoomClip(m[0]); });",
    "  $('tlZoom').appendChild(b);",
    "  return b;",
    "});",
    "  speedChips.forEach(function(b, k){",
    "    b.disabled = !p; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');",
    "  zoomChips.forEach(function(b, k){",
    "    b.disabled = !p; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');",
    "T.on('resize', function(){ if (T.ready() && !drag) renderTimeline(); });",
]

HELPERS = r"""
(function(){
  // as a PC: the page's own facts say so (only when this test asks, with #pc on the address)
  var real = JSON.parse;
  JSON.parse = function(){
    var o = real.apply(this, arguments);
    if (location.hash === '#pc' && o && typeof o === 'object' && 'lookEvery' in o && o.words) o.pc = true;
    return o;
  };
  // every save the page sends, as the text it sent
  window.__saves = [];
  var f = window.fetch;
  window.fetch = function(u, o){
    if (String(u).indexOf('/talking-save') >= 0 && o && o.body) window.__saves.push(String(o.body));
    return f.apply(this, arguments);
  };
})();
window.__multi = function(){
  var T = window.Talk, s = T.tl(), cut = document.getElementById('tlCut');
  return {picked: s.picked, sel: s.sel, selw: s.selw, more: s.more,
          on: Array.from(document.querySelectorAll('#tlClips .tl-clip.on')).map(function(e){ return +e.getAttribute('data-w'); }),
          xs: document.querySelectorAll('#tlClips .tl-x').length,
          cut: [cut.textContent, cut.disabled, cut.title],
          line: document.getElementById('tlMulti').textContent, lineKids: document.getElementById('tlMulti').children.length,
          hint: document.getElementById('tlHint').textContent,
          time: document.getElementById('tlTime').textContent,
          outlined: Array.from(document.querySelectorAll('#script .words span.picked')).map(function(e){ return +e.getAttribute('data-i'); }),
          n: [T.UNDO.length, T.REDO.length], rev: T.rev, sum: document.getElementById('sum').textContent};
};
"""


def set_range(lst, a, b, extra):
    """Her setRange, in Python (what one clip's press has always sent)."""
    out = []
    for r in lst:
        if r["b"] < a or r["a"] > b:
            out.append(dict(r))
            continue
        if r["a"] < a:
            out.append(dict(r, b=a - 1))
        if r["b"] > b:
            out.append(dict(r, a=b + 1))
    if extra:
        out.append(dict(extra, a=a, b=b))
    return sorted(out, key=lambda x: x["a"])


def overlap(zs):
    zs = sorted(zs, key=lambda x: x["a"])
    return any(x["b"] >= y["a"] for x, y in zip(zs, zs[1:]))


def make(s):
    kit = s.kit(KIT)
    if (kit / ".kit" / "talking.json").exists():
        return kit
    kit = s.make_kit(KIT, photos=3)
    key = s.add_talk(kit, TALK)
    s.TR.put_words(kit, TALK, key, WORDS, info={"dur": 3.0})
    return kit


def seed(s, **edit):
    """The record's edit put to exactly this (as the chat would change it): everything not named is empty."""
    want = dict(json.loads(json.dumps(CLEAN)), **edit)
    s.TR.change(s.kit(KIT), lambda rec: rec.update(json.loads(json.dumps(want))))


def zoom_values(s):
    """The plan CapCut would be given, built and never written: for each piece, (its zoom, the scale at its start,
    the scale at its end), each divided by what fills the frame (so 1.0 is no zoom)."""
    import capcut
    import talking_make
    plan = talking_make.plan_for(s.kit(KIT))
    d, _m = capcut.build_talking(plan, capcut.load_parts(), None)
    fill = capcut.cover_scale(plan["video"]["w"], plan["video"]["h"])
    out = []
    for seg, p in zip(d["tracks"][0]["segments"], plan["pieces"]):
        kf = seg["common_keyframes"]
        if kf:
            ks = kf[0]["keyframe_list"]
            out.append((p["zoom"], round(ks[0]["values"][0] / fill, 4), round(ks[1]["values"][0] / fill, 4), round(seg["clip"]["scale"]["x"] / fill, 4)))
        else:
            out.append((p["zoom"], None, None, round(seg["clip"]["scale"]["x"] / fill, 4)))
    return out


# ---------- in Python and by request ----------

def run_requests(s):
    tp, TR = s.tp, s.TR
    make(s)
    ours = ("multi_hint", "multi_hint_pc", "multi_selected", "delete_clips", "delete_title_many", "cut_clips", "zoom_joined", "zoom_some_joined", "zoom_all_joined")
    case("every word for several clips is OURS (in OUR_WORDS with its reason), none of them a key of hers, none says \"Claude\"",
         all(k in tp.OUR_WORDS and k not in tp.WORDS and len(tp.OUR_WORDS[k][1]) > 10 and "claude" not in tp.OUR_WORDS[k][0].lower() for k in ours),
         [k for k in ours if k not in tp.OUR_WORDS or k in tp.WORDS])
    case("her help lines are word for word what they were",
         tp.WORDS["tl_hint"] == "Drag to scrub · drag a clip's end to cut or bring back talking · a photo's ends only move the photo · spacebar plays · zoom in to see your words"
         and tp.WORDS["tl_hint_words"].startswith("Drag a clip's end to cut or bring back talking (sound and picture together)")
         and tp.WORDS["delete_clip"] == "🗑 Delete clip" and tp.WORDS["delete_title"] == "Delete the clip you picked (or press Delete)"
         and tp.WORDS["cut_clip"] == "Cut. Undo brings it back, or find it crossed out in your script.")
    pw = tp.page_words()
    import this_computer
    was = this_computer.WINDOWS
    try:
        this_computer.WINDOWS = True
        pc = tp.page_words()
        this_computer.WINDOWS = False
        mac = tp.page_words()
    finally:
        this_computer.WINDOWS = was
    case("the line names Command on a Mac and Ctrl on a PC, and Shift on both",
         "Hold Command and click" in mac["multi_hint"] and "Ctrl" not in mac["multi_hint"] and "Hold Ctrl and click" in pc["multi_hint"]
         and "Command" not in pc["multi_hint"] and "Shift" in mac["multi_hint"] and "Shift" in pc["multi_hint"], (mac["multi_hint"], pc["multi_hint"]))
    code, _j, raw, _h = s.http("GET", "/talking.html" + s.q(KIT))
    page = raw.decode("utf-8")
    import html as _html
    case("the page carries our line under her help line, in an element of its own; hers is still first and whole",
         code == 200 and ("<div class='tl-hint' id='tlHint'>" + _html.escape(pw["tl_hint"]) + "</div><div class='tl-hint more' id='tlMulti' aria-live='polite'>"
                          + _html.escape(pw["multi_hint"]) + "</div>") in page, code)

    # the page is TOLD whether it is a PC (Ctrl-click adds there, Command-click on a Mac): the fact the server sends
    def facts(text):
        a = text.index("id='talkData'")
        a = text.index(">", a) + 1
        return json.loads(text[a:text.index("</script>", a)])
    try:
        served = facts(page).get("pc")
    except (ValueError, KeyError):
        served = "unreadable"
    case("the page the server sends says whether this is a PC, truly (so Ctrl-click, not the Windows key, adds a clip there)",
         served is bool(this_computer.WINDOWS), served)
    try:
        this_computer.WINDOWS = True
        as_pc = facts(tp.page_html(KIT)).get("pc")
        this_computer.WINDOWS = False
        as_mac = facts(tp.page_html(KIT)).get("pc")
    finally:
        this_computer.WINDOWS = was
    case("...built as a PC the page's facts say pc, built as a Mac they say not", as_pc is True and as_mac is False, (as_pc, as_mac))

    # ---- one slow zoom across a run, as the Assistant's side takes it ----
    seed(s)
    st = s.state(KIT)
    case("seven clips, whose first words are 0, 3, 6, 9, 12, 15, 18, one after another with no gap on the reel",
         [p["words"][0] for p in st["pieces"]] == FIRST
         and all(abs(a["at"] + a["dur"] - b["at"]) < 0.002 for a, b in zip(st["pieces"], st["pieces"][1:])), [p["words"] for p in st["pieces"]])
    code, j = s.post("/talking-save", {"kit": KIT, "base": st["rev"], "page": "multitest001", "saved": {"zooms": [{"a": 3, "b": 11, "kind": "zoom"}]}})
    case("one zoom from the first word of a run of three clips to its last is taken, and every piece of the run has that one zoom",
         code == 200 and j["zooms"] == [{"a": 3, "b": 11, "kind": "zoom"}] and [p["zoom"] for p in j["pieces"]] == [None, 0, 0, 0, None, None, None],
         (code, [p["zoom"] for p in (j or {}).get("pieces", [])]))
    v = zoom_values(s)
    case("in the CapCut plan it is ONE zoom: 1.0 at the run's start, 1.12 at its end, and each piece starts at the value the one before ended on",
         [x[0] for x in v] == [None, 0, 0, 0, None, None, None] and v[1][1] == 1.0 and v[3][2] == 1.12 and v[1][2] == v[2][1] and v[2][2] == v[3][1]
         and 1.0 < v[1][2] < v[2][2] < 1.12 and all(x[1] == x[3] for x in v[1:4]) and v[0][3] == v[4][3] == 1.0, v)
    # across cut words: clip c3 (words 9 to 11) is cut, so c2 and c4 sit side by side; one zoom from 6 to 14
    seed(s, cut=[[9, 11]])
    st = s.state(KIT)
    code, j = s.post("/talking-save", {"kit": KIT, "base": st["rev"], "page": "multitest001", "saved": {"zooms": [{"a": 6, "b": 14, "kind": "zoom"}]}})
    v = zoom_values(s)
    case("across cut words too: the two clips either side of a cut share the one zoom, and it carries on where the first hands over (never back to 1.0)",
         code == 200 and [p["words"][0] for p in j["pieces"]] == [0, 3, 6, 12, 15, 18] and [x[0] for x in v] == [None, None, 0, 0, None, None]
         and v[2][1] == 1.0 and v[3][2] == 1.12 and v[2][2] == v[3][1] and 1.0 < v[2][2] < 1.12, v)
    # two separate zooms side by side, for the difference: each starts again at 1.0 (hers; the owners' question 20)
    seed(s, zooms=[{"a": 3, "b": 5, "kind": "zoom"}, {"a": 6, "b": 8, "kind": "zoom"}])
    v = zoom_values(s)
    case("...where two SEPARATE slow zooms side by side each start again at 1.0 (as hers; this is what joining them avoids)",
         v[1][1] == 1.0 and v[1][2] == 1.12 and v[2][1] == 1.0 and v[2][2] == 1.12, v[1:3])
    seed(s)


# ---------- on the page ----------

def run_page(c, s):
    wait_for = t.wait_for
    W = s.tp.page_words()
    make(s)
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script(tpt.HELPERS)
    c.init_script(HELPERS)
    c.clear_errors()

    def fill(key, **kw):
        line = W[key]
        for k, v_ in kw.items():
            line = line.replace("{%s}" % k, str(v_))
        return line

    def m():
        return c.js("window.__multi()")

    def rec():
        return s.rec(KIT) or {}

    def toast():
        return t.toast(c)

    def clip(w0):
        return '#tlClips .tl-clip[data-w="%d"]' % w0

    def click(w0, **mods):
        c.click(clip(w0), check=False, **mods)

    def chip(group_id, attr, value):
        # what was a press on a chip: the menu's button, then the item (Dustin, Nov 13: two small menus)
        tpt.menu_pick(c, group_id, attr=attr, value=value)

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")

    def press(fn):
        """A press that saves: wait for its answer. Returns the texts of the saves it sent."""
        was, n = c.js("window.Talk.rev"), c.js("window.__saves.length")
        fn()
        moved(was)
        return c.js("window.__saves.slice(%d)" % n)

    def saved_text(body):
        return body[body.index('"saved":'):]

    def open_it(pc=False, **edit):
        seed(s, **edit)
        c.open("about:blank")
        c.open(s.url("/talking.html" + s.q(KIT)) + ("#pc" if pc else ""))
        c.wait_for("window.Talk && window.Talk.loaded", 15, tell="document.body.innerText.slice(0, 200)")
        c.wait_for("document.querySelectorAll('#script .sent').length === 7", 10, tell="document.getElementById('status').textContent")
        c.wait_for("document.getElementById('vid').readyState >= 1", 15)
        c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length > 0", 10)

    def undo_button():
        return press(lambda: c.click("#tlUndo"))

    # ================= as it opens =================
    open_it()
    g = m()
    case("as it opens: seven clips, none picked, her help line whole and ours on a line of its own under it, as text",
         c.js("window.__clips().map(function(x){ return x.w; })") == FIRST and g["picked"] == [] and g["on"] == [] and g["hint"] in (W["tl_hint"], W["tl_hint_words"])
         and g["line"] == W["multi_hint"] and g["lineKids"] == 0 and g["cut"] == [W["delete_clip"], True, W["delete_title"]], g)
    below = c.js("[document.getElementById('tlHint').getBoundingClientRect().bottom, document.getElementById('tlMulti').getBoundingClientRect().top,"
                 " document.getElementById('tlMulti').getBoundingClientRect().height]")
    case("...our line sits right under hers and can be seen", below[1] >= below[0] - 0.5 and below[2] > 8, below)

    # ================= a plain click, then Command-click to add and to take out =================
    click(3)
    g1 = m()
    case("a plain click picks one clip, as ever: her mark, her little x, her button, and our line is still the help line",
         g1["picked"] == [3] and g1["on"] == [3] and g1["xs"] == 1 and g1["cut"] == [W["delete_clip"], False, W["delete_title"]] and g1["line"] == W["multi_hint"]
         and g1["more"] == [] and g1["outlined"] == [3, 4, 5], g1)
    click(6, meta=True)
    g2 = m()
    case("Command-click adds a clip: both are picked and both wear her mark", g2["picked"] == [3, 6] and g2["on"] == [3, 6] and g2["sel"] == "clip", g2)
    case("...no little x is drawn, the button reads \"Delete 2 clips\" with its own tooltip, and the line says 2 clips are selected, as text",
         g2["xs"] == 0 and g2["cut"] == [fill("delete_clips", n=2), False, W["delete_title_many"]] and g2["line"] == fill("multi_selected", n=2) and g2["lineKids"] == 0, g2)
    case("...the script outlines the words of both clips", g2["outlined"] == [3, 4, 5, 6, 7, 8], g2["outlined"])
    case("...the line did not move and nothing was saved (picking is no edit)", g2["time"] == g1["time"] and g2["rev"] == g1["rev"] and g2["n"] == [0, 0], (g1["time"], g2["time"]))
    tools = c.js("window.__tools()")
    case("...Speed and Zoom are live, lit where every picked clip agrees (1× and None)",
         [x[1] for x in tools["speed"]] == [False] * 4 and [x[2] for x in tools["speed"]] == [True, False, False, False]
         and [x[1] for x in tools["zoom"]] == [False] * 3 and [x[2] for x in tools["zoom"]] == [True, False, False], tools)
    click(12, meta=True)
    g3 = m()
    case("a third, not next to the others: three picked, \"Delete 3 clips\", \"3 clips selected\"",
         g3["picked"] == [3, 6, 12] and g3["on"] == [3, 6, 12] and g3["cut"][0] == fill("delete_clips", n=3) and g3["line"] == fill("multi_selected", n=3), g3)
    runs = c.js("window.Talk.tlRuns()")
    case("...as runs: the two side by side are one run (words 3 to 8), the third is by itself (12 to 14)",
         [(r["a"], r["b"], len(r["clips"])) for r in runs] == [(3, 8, 2), (12, 14, 1)], runs)
    click(6, meta=True)
    g4 = m()
    case("Command-click on a picked clip takes it out: two left, the mark gone from it", g4["picked"] == [3, 12] and g4["on"] == [3, 12] and g4["cut"][0] == fill("delete_clips", n=2), g4)
    click(12, meta=True)
    g5 = m()
    case("...down to one: everything reads as one clip picked again (her x, her button, the help line)",
         g5["picked"] == [3] and g5["xs"] == 1 and g5["cut"] == [W["delete_clip"], False, W["delete_title"]] and g5["line"] == W["multi_hint"] and g5["more"] == [], g5)
    click(3, meta=True)
    g6 = m()
    case("...and out of the last one: nothing picked, the button and the two menus grey",
         g6["picked"] == [] and g6["on"] == [] and g6["sel"] is None and g6["cut"][1] is True and c.js("window.__tools().zoom.every(function(x){ return x[1]; })"), g6)
    click(9, meta=True)
    case("Command-click with nothing picked picks that clip", m()["picked"] == [9] and m()["xs"] == 1, m())
    click(9, ctrl=True)
    case("on a Mac a Control-click is still the right click: nothing changes", m()["picked"] == [9], m())

    # ================= Shift-click =================
    click(3)
    click(12, shift=True)
    g = m()
    case("Shift-click picks every clip from the one clicked last to this one", g["picked"] == [3, 6, 9, 12] and g["on"] == [3, 6, 9, 12] and g["line"] == fill("multi_selected", n=4), g)
    click(6, shift=True)
    case("...a second Shift-click reaches from the same first clip (the pick shrinks to it)", m()["picked"] == [3, 6], m())
    click(0, shift=True)
    case("...and backwards", m()["picked"] == [0, 3], m())
    click(0)
    click(6, meta=True)
    click(12, meta=True, shift=True)
    case("Command and Shift together add the run to what is picked", m()["picked"] == [0, 6, 9, 12], m())
    c.click("#tlRuler", check=False)
    case("a press on empty timeline lets go of everything, as ever", m()["picked"] == [] and m()["sel"] is None and m()["line"] == W["multi_hint"], m())
    click(15, shift=True)
    case("Shift-click with nothing picked picks that clip", m()["picked"] == [15], m())
    click(3)
    click(9, shift=True)
    click(6)
    g = m()
    case("a plain click on one of several picks just that one", g["picked"] == [6] and g["on"] == [6] and g["xs"] == 1 and g["more"] == [], g)
    case("no text on the page was highlighted by the Shift-clicks", c.js("String(window.getSelection())") == "")

    # ================= Escape =================
    click(3, meta=True)
    c.key("Escape")
    case("Escape lets go of several", m()["picked"] == [] and m()["sel"] is None, m())
    click(3)
    c.key("Escape")
    case("...and with one clip picked Escape is as it was (the clip stays picked)", m()["picked"] == [3], m())

    # ================= Slow zoom: one zoom across clips side by side =================
    open_it()
    click(3)
    click(9, shift=True)
    sent = press(lambda: chip("tlZoom", "z", "zoom"))
    g = m()
    case("Slow zoom with three clips side by side picked: ONE save, and it is ONE zoom from the run's first word to its last",
         len(sent) == 1 and saved_text(sent[0]) == '"saved":{"zooms":[{"a":3,"b":11,"kind":"zoom"}]}}' and rec().get("zooms") == [{"a": 3, "b": 11, "kind": "zoom"}], sent)
    case("...the toast says so, every clip of the run wears her Slow zoom badge, the summary counts one zoom, and they stay picked with Slow zoom checked in the menu",
         toast() == fill("zoom_joined", n=3) and [x["bd"] for x in c.js("window.__clips()")] == [[], [W["slow_zoom"]], [W["slow_zoom"]], [W["slow_zoom"]], [], [], []]
         and "1 zoom" in g["sum"] and g["picked"] == [3, 6, 9] and [x[2] for x in c.js("window.__tools().zoom")] == [False, False, True], (toast(), g))
    case("...it is ONE step of Undo", g["n"] == [1, 0], g["n"])
    zs = c.js("window.Talk.P().map(function(p){ return p.zoom; })")
    v = zoom_values(s)
    case("...on the page and in the CapCut plan the three pieces are one zoom whose keyframes are continuous: 1.0, on through each hand-over, to 1.12",
         zs == [None, 0, 0, 0, None, None, None] and v[1][1] == 1.0 and v[1][2] == v[2][1] and v[2][2] == v[3][1] and v[3][2] == 1.12 and v[1][2] < v[2][2], (zs, v))
    span = c.js("window.Talk.zoomSpan(0)")
    ps = c.js("window.Talk.P()")
    case("...and the preview's own zoom runs across the whole run", abs(span[0] - ps[1]["at"]) < 0.002 and abs(span[1] - (ps[3]["at"] + ps[3]["dur"])) < 0.002, span)
    undo_button()
    g = m()
    case("Undo, once, takes the whole zoom off all three", rec().get("zooms") == [] and g["n"] == [0, 1] and toast() == W["undone"], (rec().get("zooms"), g["n"]))
    press(lambda: c.click("#tlRedo"))
    case("Redo, once, puts it back on all three", rec().get("zooms") == [{"a": 3, "b": 11, "kind": "zoom"}] and m()["n"] == [1, 0], rec().get("zooms"))
    press(lambda: c.key("Mod+Z"))
    undone = rec().get("zooms")
    press(lambda: c.key("Mod+Shift+Z"))
    case("...and by the keys: one Undo, one Redo", undone == [] and rec().get("zooms") == [{"a": 3, "b": 11, "kind": "zoom"}] and m()["n"] == [1, 0], undone)

    # ---- a reload keeps it ----
    open_seed = rec()
    c.reload()
    c.wait_for("window.Talk && window.Talk.loaded && document.querySelectorAll('#tlClips .tl-clip').length === 7", 15)
    g = m()
    case("a reload keeps the result (the one zoom, its badges); what was picked is not kept, as a single pick never was",
         rec() == open_seed and [x["bd"] for x in c.js("window.__clips()")][1:4] == [[W["slow_zoom"]]] * 3 and c.js("window.Talk.ZL") == [{"a": 3, "b": 11, "kind": "zoom"}]
         and g["picked"] == [] and g["line"] == W["multi_hint"], g)

    # ---- Punch in on each, None on all ----
    click(3)
    click(9, shift=True)
    sent = press(lambda: chip("tlZoom", "z", "punch"))
    case("Punch in with the three picked: one save, each clip punched in by itself (the one slow zoom gone)",
         len(sent) == 1 and rec().get("zooms") == [{"a": 3, "b": 5, "kind": "punch"}, {"a": 6, "b": 8, "kind": "punch"}, {"a": 9, "b": 11, "kind": "punch"}]
         and [x["bd"] for x in c.js("window.__clips()")][1:4] == [[W["punch"]]] * 3 and m()["n"] == [1, 0], (sent, rec().get("zooms")))
    v = zoom_values(s)
    case("...in the CapCut plan each of the three sits at 1.15 with no keyframes", [x[1:] for x in v[1:4]] == [(None, None, 1.15)] * 3, v)
    click(6, meta=True)
    sent = press(lambda: chip("tlZoom", "z", ""))
    case("None with two of them picked: the zoom comes off those two and stays on the third, in one save and one step",
         len(sent) == 1 and rec().get("zooms") == [{"a": 6, "b": 8, "kind": "punch"}] and m()["n"] == [2, 0], rec().get("zooms"))

    # ================= clips that do not touch; a zoom that reaches past the picked clips =================
    open_it(zooms=[{"a": 0, "b": 8, "kind": "punch"}])
    click(6)
    click(9, meta=True)
    click(15, meta=True)
    sent = press(lambda: chip("tlZoom", "z", "zoom"))
    z = rec().get("zooms")
    case("Slow zoom with a run of two and a clip apart: the run is one zoom, the clip apart has its own; the punch in that reached past the picked clips is trimmed, not lost",
         len(sent) == 1 and z == [{"a": 0, "b": 5, "kind": "punch"}, {"a": 6, "b": 11, "kind": "zoom"}, {"a": 15, "b": 17, "kind": "zoom"}] and not overlap(z)
         and toast() == W["zoom_some_joined"] and m()["n"] == [1, 0], (z, toast()))
    v = zoom_values(s)
    case("...in the CapCut plan: the run 1.0 to 1.12 across both, the clip apart 1.0 to 1.12 by itself, the two before still punched in",
         v[2][1] == 1.0 and v[2][2] == v[3][1] and v[3][2] == 1.12 and v[5][1] == 1.0 and v[5][2] == 1.12 and v[0][3] == v[1][3] == 1.15 and v[4][3] == 1.0, v)
    open_it()
    click(0)
    click(6, meta=True)
    click(12, meta=True)
    sent = press(lambda: chip("tlZoom", "z", "zoom"))
    case("three clips, none of them side by side: three zooms of their own, no \"one zoom\" toast, one step",
         rec().get("zooms") == [{"a": 0, "b": 2, "kind": "zoom"}, {"a": 6, "b": 8, "kind": "zoom"}, {"a": 12, "b": 14, "kind": "zoom"}] and toast() == "" and m()["n"] == [1, 0],
         (rec().get("zooms"), toast()))

    # ================= Slow zoom on clips that are already inside one long slow zoom =================
    def quiet(fn, wait=0.8):
        """A press that should save nothing: how many saves it sent."""
        n = c.js("window.__saves.length")
        fn()
        time.sleep(wait)
        return c.js("window.__saves.length") - n
    long_zoom = [{"a": 0, "b": 14, "kind": "zoom"}]
    open_it(zooms=long_zoom)
    click(3)
    click(9, meta=True)
    lit = [x_[2] for x_ in c.js("window.__tools().zoom")]
    n = quiet(lambda: chip("tlZoom", "z", "zoom"))
    v = zoom_values(s)
    case("two clips of one long slow zoom picked (not side by side), Slow zoom chosen: it was checked already, nothing is saved, and the long zoom is still ONE zoom",
         lit == [False, False, True] and n == 0 and rec().get("zooms") == long_zoom and m()["n"] == [0, 0] and toast() == ""
         and v[0][1] == 1.0 and v[4][2] == 1.12 and all(v[k][2] == v[k + 1][1] for k in range(4)), (lit, n, rec().get("zooms"), toast()))
    click(6, meta=True)
    n = quiet(lambda: chip("tlZoom", "z", "zoom"))
    case("...the same with three of its clips side by side picked: left as it is", n == 0 and rec().get("zooms") == long_zoom and m()["n"] == [0, 0], (n, rec().get("zooms")))
    click(15, meta=True)
    sent = press(lambda: chip("tlZoom", "z", "zoom"))
    case("...with a clip outside it picked as well: only that clip gets a zoom; the long zoom is not broken up",
         len(sent) == 1 and rec().get("zooms") == long_zoom + [{"a": 15, "b": 17, "kind": "zoom"}] and m()["n"] == [1, 0], rec().get("zooms"))
    open_it(zooms=[{"a": 3, "b": 8, "kind": "zoom"}])
    click(3)
    click(9, shift=True)
    press(lambda: chip("tlZoom", "z", "zoom"))
    case("a run that reaches PAST the slow zoom it started in is still made one zoom", rec().get("zooms") == [{"a": 3, "b": 11, "kind": "zoom"}] and toast() == fill("zoom_joined", n=3),
         (rec().get("zooms"), toast()))
    open_it(zooms=long_zoom)
    click(3)
    click(9, meta=True)
    press(lambda: chip("tlZoom", "z", "punch"))
    case("Punch in on clips of a long slow zoom still changes them (only Slow zoom on a slow zoom is left alone)",
         rec().get("zooms") == [{"a": 0, "b": 2, "kind": "zoom"}, {"a": 3, "b": 5, "kind": "punch"}, {"a": 6, "b": 8, "kind": "zoom"}, {"a": 9, "b": 11, "kind": "punch"},
                                {"a": 12, "b": 14, "kind": "zoom"}], rec().get("zooms"))

    # ---- the toast: two groups side by side and no clip by itself; a second press saves nothing ----
    open_it()
    click(0)
    click(3, meta=True)
    click(9, meta=True)
    click(12, meta=True)
    press(lambda: chip("tlZoom", "z", "zoom"))
    case("two groups of clips side by side, no clip by itself: the toast does not speak of \"the others\"",
         rec().get("zooms") == [{"a": 0, "b": 5, "kind": "zoom"}, {"a": 9, "b": 14, "kind": "zoom"}] and toast() == W["zoom_all_joined"] and "others" not in W["zoom_all_joined"], toast())
    c.wait_for("!document.getElementById('toast').classList.contains('on')", 15)
    n = quiet(lambda: chip("tlZoom", "z", "zoom"))
    case("...pressed again on the same clips: nothing saved, no toast again, still one step of Undo", n == 0 and toast() == "" and m()["n"] == [1, 0], (n, toast(), m()["n"]))

    # ---- a Zoom item is checked only when every picked clip agrees ----
    open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom"}, {"a": 6, "b": 8, "kind": "punch"}])
    click(3)
    click(6, meta=True)
    case("two clips with different zooms picked: no Zoom item is checked", [x_[2] for x_ in c.js("window.__tools().zoom")] == [False, False, False], c.js("window.__tools().zoom"))

    # ---- a press on a clip's end handle lets go of the others ----
    open_it()
    click(3)
    click(9, shift=True)
    c.click(clip(6) + " .tl-clip-h.r", check=False)
    g = m()
    case("three picked, then a press on one clip's end: only that clip is picked", g["picked"] == [6] and g["more"] == [] and g["xs"] == 1, g)

    # ================= across cut words =================
    open_it(cut=[[9, 11]])
    case("with the middle clip cut, six clips are left", c.js("window.__clips().map(function(x){ return x.w; })") == [0, 3, 6, 12, 15, 18])
    click(6)
    click(12, meta=True)
    runs = c.js("window.Talk.tlRuns()")
    press(lambda: chip("tlZoom", "z", "zoom"))
    v = zoom_values(s)
    case("the two clips either side of a cut are side by side on the reel: one run, ONE zoom over them (the cut words inside it), continuous in the CapCut plan",
         [(r["a"], r["b"], len(r["clips"])) for r in runs] == [(6, 14, 2)] and rec().get("zooms") == [{"a": 6, "b": 14, "kind": "zoom"}]
         and v[2][1] == 1.0 and v[2][2] == v[3][1] and v[3][2] == 1.12 and toast() == fill("zoom_joined", n=2), (runs, rec().get("zooms"), v))
    press(lambda: chip("tlZoom", "z", ""))
    case("None on those two clears the whole zoom: no stray zoom is left on the cut words between them, and the summary counts none",
         rec().get("zooms") == [] and "0 zooms" in m()["sum"], (rec().get("zooms"), m()["sum"]))

    # ================= Speed =================
    open_it()
    click(0)
    click(6, meta=True)
    sent = press(lambda: chip("tlSpeed", "v", "1.5"))
    case("1.5× with two clips picked: both sped up, each as a press on it would, in one save and one step",
         len(sent) == 1 and saved_text(sent[0]) == '"saved":{"speeds":[{"a":0,"b":2,"v":1.5},{"a":6,"b":8,"v":1.5}]}}'
         and rec().get("speeds") == [{"a": 0, "b": 2, "v": 1.5}, {"a": 6, "b": 8, "v": 1.5}] and m()["n"] == [1, 0]
         and [x[2] for x in c.js("window.__tools().speed")] == [False, False, True, False] and m()["picked"] == [0, 6], (sent, rec().get("speeds")))
    click(0)
    press(lambda: chip("tlSpeed", "v", "2"))
    click(6, meta=True)
    case("two picked clips at different speeds: no speed item is checked", [x[2] for x in c.js("window.__tools().speed")] == [False] * 4 and m()["picked"] == [0, 6], c.js("window.__tools().speed"))
    press(lambda: chip("tlSpeed", "v", "1"))
    case("1× with both picked puts both back, in one step", rec().get("speeds") == [] and m()["n"] == [3, 0], rec().get("speeds"))
    undo_button()
    case("...and one Undo brings both speeds back", rec().get("speeds") == [{"a": 0, "b": 2, "v": 2.0}, {"a": 6, "b": 8, "v": 1.5}], rec().get("speeds"))

    # ================= Delete =================
    open_it()
    click(3)
    click(9, meta=True)
    sent = press(lambda: c.click("#tlCut"))
    g = m()
    case("Delete 2 clips: both clips' words are cut in one save; the toast says two, and nothing is picked",
         len(sent) == 1 and saved_text(sent[0]) == '"saved":{"cut":[[3,5],[9,11]]}}' and rec().get("cut") == [[3, 5], [9, 11]] and toast() == fill("cut_clips", n=2)
         and g["picked"] == [] and g["sel"] is None and g["line"] == W["multi_hint"] and c.js("window.__clips().map(function(x){ return x.w; })") == [0, 6, 12, 15, 18], (sent, g))
    case("...one step of Undo", g["n"] == [1, 0], g["n"])
    undo_button()
    case("...one Undo brings both back", rec().get("cut") == [] and c.js("window.__clips().length") == 7 and m()["n"] == [0, 1], rec().get("cut"))
    click(12)
    click(18, shift=True)
    press(lambda: c.key("Delete"))
    case("the Delete key takes every picked clip too", rec().get("cut") == [[12, 20]] and m()["picked"] == [] and toast() == fill("cut_clips", n=3), rec().get("cut"))

    # ================= Split is as ever =================
    open_it()
    click(0)
    click(3, meta=True)
    p2 = c.js("window.Talk.P()[2]")
    c.js("window.__at(%r)" % (p2["from"] + (p2["to"] - p2["from"]) * 0.5))
    press(lambda: c.click("#tlSplit"))
    sp = rec().get("splits")
    g = m()
    case("Split with several picked is as ever: it splits the clip under the line (not the picked ones), and then only the new clip is picked",
         len(sp) == 1 and sp[0] in (7, 8) and g["picked"] == [sp[0]] and g["more"] == [] and g["xs"] == 1, (sp, g))

    # ================= a picked clip the chat cuts =================
    open_it()
    click(3)
    click(6, meta=True)
    click(9, meta=True)
    s.cut(KIT, [[9, 11]])
    c.js("window.Talk.poll(true)")
    c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length === 6", 10)
    g = m()
    case("a picked clip the chat cuts drops out; the others stay picked, looked up afresh", g["picked"] == [3, 6] and g["on"] == [3, 6] and g["line"] == fill("multi_selected", n=2), g)
    s.cut(KIT, [[3, 5], [9, 11]])
    c.js("window.Talk.poll(true)")
    c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length === 5", 10)
    g = m()
    case("...down to one: it reads as one clip picked", g["picked"] == [6] and g["xs"] == 1 and g["line"] == W["multi_hint"] and g["cut"][0] == W["delete_clip"], g)

    # ================= one clip at a time is byte for byte what it was =================
    open_it(zooms=[{"a": 0, "b": 8, "kind": "punch"}])
    click(3)
    bodies = []
    bodies += press(lambda: chip("tlZoom", "z", "zoom"))
    z1 = rec().get("zooms")
    bodies += press(lambda: chip("tlZoom", "z", "punch"))
    bodies += press(lambda: chip("tlZoom", "z", ""))
    bodies += press(lambda: chip("tlSpeed", "v", "1.5"))
    bodies += press(lambda: chip("tlSpeed", "v", "1"))
    bodies += press(lambda: c.click("#tlCut"))
    want = ['"saved":{"zooms":[{"a":0,"b":2,"kind":"punch"},{"a":3,"b":5,"kind":"zoom"},{"a":6,"b":8,"kind":"punch"}]}}',
            '"saved":{"zooms":[{"a":0,"b":2,"kind":"punch"},{"a":3,"b":5,"kind":"punch"},{"a":6,"b":8,"kind":"punch"}]}}',
            '"saved":{"zooms":[{"a":0,"b":2,"kind":"punch"},{"a":6,"b":8,"kind":"punch"}]}}',
            '"saved":{"speeds":[{"a":3,"b":5,"v":1.5}]}}',
            '"saved":{"speeds":[]}}',
            '"saved":{"cut":[[3,5]]}}']
    case("with ONE clip picked each press sends, character for character, what her code sends: Slow zoom, Punch in, None, 1.5×, 1×, Delete clip",
         [saved_text(b) for b in bodies] == want, [saved_text(b) for b in bodies])
    case("...the very lists her setRange gives (worked again here in Python), and the record holds them",
         z1 == set_range([{"a": 0, "b": 8, "kind": "punch"}], 3, 5, {"kind": "zoom"}) and rec().get("zooms") == set_range(z1, 3, 5, None)
         and rec().get("cut") == [[3, 5]] and rec().get("speeds") == [] and toast() == W["cut_clip"], (z1, rec().get("zooms")))
    case("...and each was one step of Undo, as ever", m()["n"] == [6, 0], m()["n"])
    keys = [sorted(json.loads(b)) for b in bodies]
    case("...a save carries only what it always did (kit, base, page, saved): nothing new is asked of the Assistant's side", all(k == ["base", "kit", "page", "saved"] for k in keys), keys[:1])

    # ================= as a PC: Ctrl-click adds =================
    open_it(pc=True)
    click(3)
    click(6, ctrl=True)
    g = m()
    case("as a PC, Ctrl-click adds a clip", c.js("window.Talk.DATA.pc") is True and g["picked"] == [3, 6] and g["line"] == fill("multi_selected", n=2), g)
    click(6, ctrl=True)
    case("...and takes it out", m()["picked"] == [3], m())
    click(9, shift=True)
    case("...Shift-click picks the run there too", m()["picked"] == [3, 6, 9], m())
    click(3)
    click(9, ctrl=True)
    click(15, ctrl=True, shift=True)
    case("...Ctrl with Shift adds the run to what is picked", m()["picked"] == [3, 9, 12, 15], m())
    click(3)
    click(9, shift=True)
    c.click("#tlRuler", check=False, ctrl=True)
    case("...a Ctrl-click that is not on a clip does nothing, as before", m()["picked"] == [3, 6, 9], m())

    # ================= clean, and phone width =================
    case("no part of the page failed, no pop-up was asked for, nothing was asked of the internet",
         c.js("window.Talk.faults.length") == 0 and c.js("window.__dialogs") == 0 and not list(c.dialogs) and not c.outside_requests(), (c.js("window.Talk.faults"), c.outside_requests()[:3]))
    errs = [e for e in c.page_errors() if "Failed to load resource" not in e and "ERR_BLOCKED" not in e]
    case("no page errors", not errs, errs[:3])
    c.phone()
    try:
        open_it()
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth, document.getElementById('tlMulti').getBoundingClientRect().right,"
                    " document.getElementById('tlMulti').getBoundingClientRect().left, document.getElementById('tlMulti').getBoundingClientRect().bottom,"
                    " document.getElementById('dock').getBoundingClientRect().bottom, parseInt(document.body.style.paddingBottom), document.getElementById('dock').offsetHeight]")
        case("phone width: no sideways scroll; our line wraps inside the window and inside the dock, and the page still leaves the dock its room",
             wide[0] <= 0 and wide[1] == 390 and wide[2] <= 390.5 and wide[3] >= 0 and wide[4] <= wide[5] + 0.5 and wide[6] == wide[7] + 24, wide)
        click(0)
        click(3, meta=True)
        click(6, meta=True)
        tall = c.js("[parseInt(document.body.style.paddingBottom), document.getElementById('dock').offsetHeight, document.getElementById('tlMulti').textContent]")
        case("...with three picked our line is longer and the dock taller: the page measures the dock's room again",
             tall[1] > wide[7] and tall[0] == tall[1] + 24 and tall[2] == fill("multi_selected", n=3), (tall, wide[7]))
    finally:
        c.desktop()


# ---------- the script as it was is still all there ----------

def check_lines():
    # the script as it was is kept beside the tests (so this runs anywhere, GitHub's one-commit checkout included)
    kept = (HERE / "fixtures" / OLD_SCRIPT).read_text(encoding="utf-8")
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (BEFORE, JS_FILE)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.SubprocessError):
        r = None
    if r is None or r.returncode != 0 or "selPiece" not in r.stdout:
        t.skip("the kept copy of the script as it was is what git has at commit %s: git can't show that commit here" % BEFORE)
    else:
        case("the kept copy of the script as it was is exactly what git has at commit %s" % BEFORE, r.stdout.splitlines() == kept.splitlines())
    old, new = kept.splitlines(), (ROOT / JS_FILE).read_text(encoding="utf-8").splitlines()
    # the old lines that are no longer there, in order (the longest run of lines the two share is what "still there"
    # means: a plain search for each line in turn would let a common line like "});" match far ahead and lose the rest)
    same = difflib.SequenceMatcher(None, old, new, autojunk=False)
    missing = [old[i] for tag, i1, i2, _j1, _j2 in same.get_opcodes() if tag in ("replace", "delete") for i in range(i1, i2)]
    named = CHANGED_LINES + MENU_LINES
    case("every line of the timeline's script as it was before several clips (%d lines) is still there, in order, but for the %d lines named in this test "
         "(%d changed for several clips, %d for the two small menus that took the chips' place)" % (len(old), len(named), len(CHANGED_LINES), len(MENU_LINES)),
         sorted(missing) == sorted(named), [x for x in missing if x not in named][:4] or [x for x in named if x not in missing][:4])
    src = "\n".join(new)

    def body(name):
        a = src.index("\nfunction %s(" % name)
        return src[a:src.index("\n}", a)]
    case("her one-clip Speed, Zoom and cut are word for word what they were, each reached when fewer than two clips are picked",
         "var a = p.words[0], b = p.words[p.words.length - 1];\n  T.save(function(){\n    return {speeds: T.setRange(T.REC.speeds || [], a, b, v === 1 ? null : {v: v}).map(function(r){ return {a: r.a, b: r.b, v: r.v}; })};" in body("speedClip")
         and "return {zooms: T.setRange(T.ZL, a, b, kind ? {kind: kind} : null).map(function(r){ return {a: r.a, b: r.b, kind: r.kind}; })};" in body("zoomClip")
         and "var list = p.words.slice();\n  SELW = null;\n  saveCut(list, true);\n  T.toast(W.cut_clip);" in body("cutClip")
         and "if (!MORE.length || TLSEL !== 'clip') return null;" in body("many"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8792,) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="talking-multi-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.make()
    try:
        group("the script as it was", check_lines)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("several clips, in Python and by request", run_requests, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("several clips on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1100)) as c:
                group("several clips on the page", run_page, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        case("the real Assistant folder on this computer is exactly as it was", t.real_listing() == real_before)
        if not keep and not [1 for _n, ok in chrome_drive._results if not ok]:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return t.summary()


if __name__ == "__main__":
    sys.exit(main())
