#!/usr/bin/env python3
"""The two small menus for Speed and Zoom on the talking reel page's timeline (ours, in place of Nicole's chips;
Dustin, Nov 13: "C is the best. By far... any user interface that can be cleaner and still have everything necessary
is fantastic").

    python3 tests/guard.py 3000 python3 tests/talking_menus_check.py [--no-chrome] [--port 9670] [--work <folder>]

Run it under the memory guard, ONE such test at a time (it drives a hidden Chrome).

In Python (no browser):
  - the two new lines are OURS (talking_page.OUR_WORDS, each with its reason), her words Speed, Zoom, None, Punch in,
    Slow zoom and "{v}×" are untouched and are what the menus show, and the bar the page carries reads Split,
    Delete clip, a thin separator, Speed, Zoom, Undo, Redo with no bare word in it;
  - the line under the timeline still says "Speed, Zoom and Delete change all of them".
On the real page, in a hidden Chrome, with a real mouse and real keys:
  - nothing picked: both buttons grey ("Speed: 1×", "Zoom: None"), a press opens nothing;
  - a press opens a short list right at the button: above it (the bar sits on the timeline), whole inside the
    window, nothing lying over any item, her words in her order, the picked clip's choice checked; proper names for
    a screen reader (aria-haspopup, aria-expanded, role menu and menuitemradio, aria-checked);
  - only one open at a time; a press on the button again, a press anywhere else (which still does what it was a
    press on), choosing, Escape, a resize all close it; Escape closes the menu FIRST and leaves what is picked
    alone, the next Escape lets go of several clips as ever;
  - with ONE clip picked every item sends, character for character, what her chip's press sent (the exact text of
    each save), one save and one step of Undo each; the button then says the choice, looks on (filled) for a zoom
    or a speed that is not 1×, and has the keyboard again;
  - several clips that disagree: "Mixed", no item checked; that agree: their choice, checked;
  - the keys: Enter, Space, Down and Up open from the button, the arrows, Home and End move, Enter and Space
    choose, Tab closes; the spacebar never plays the video behind an open menu;
  - a photo picked, or the picked clip cut from the chat with the menu open: grey, and the menu closes itself;
  - a window with no room above the button: the list goes under it, still whole inside the window;
  - phone width: no sideways scroll, the lists inside the window, a finger's tap chooses;
  - the review round: the bar keeps its shape (each button's words have the room of their longest, so no button
    moves when another clip is picked) and Undo and Redo are never parted, at eight widths; Backspace and Delete
    do nothing inside an open list; the window losing the keyboard closes it; no item is shaded unless the pointer
    or the keyboard is on it;
  - everything is text (no element made from a string), no page error, nothing asked of the internet.

Since Nov 13 also the two rows under the Zoom menu's items, How much and How fast (shown only with a zoom, the lit
choice, one save and one Undo, the menu staying open, several clips, the keys, phone widths), and the preview's
zoom checked value for value against the engine's function of time.

What it never does: touch the real ~/.studio (STUDIO_HOME is a scratch folder; the real one is listed before and
after), start the real transcriber, write into CapCut, or play a video. The page server (port 9670 up) and the
hidden Chrome are this test's own and are stopped at the end.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
import re
import html as _html
import json
import shutil
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
import talking_multi_check as tm  # noqa: E402

PORT = 9670
KIT = tm.KIT

HELPERS = r"""
(function(){
  var $ = function(id){ return document.getElementById(id); };
  // one menu, as a person and a screen reader find it
  window.__menu = function(id){
    var b = $(id + 'Btn'), l = $(id + 'List'), r = b.getBoundingClientRect(), q = l.getBoundingClientRect(), cs = getComputedStyle(b);
    var items = Array.from(l.querySelectorAll('[role=menuitemradio]'));
    var open = !l.hidden && getComputedStyle(l).display !== 'none';
    return {
      label: b.querySelector('.nm').textContent, value: b.querySelector('.val').textContent, off: b.disabled, on: b.classList.contains('on'),
      // what a screen reader says for the button: its words without the little arrow, which is hidden from it
      name: Array.from(b.childNodes).filter(function(n){ return !(n.getAttribute && n.getAttribute('aria-hidden') === 'true'); }).map(function(n){ return n.textContent; }).join(' '),
      arrow: b.querySelector('.car').textContent, arrowHidden: b.querySelector('.car').getAttribute('aria-hidden'),
      has: b.getAttribute('aria-haspopup'), expanded: b.getAttribute('aria-expanded'), controls: b.getAttribute('aria-controls'), listId: l.id,
      role: l.getAttribute('role'), listName: l.getAttribute('aria-label'), open: open,
      bg: cs.backgroundColor, color: cs.color, opacity: cs.opacity,
      btn: [r.left, r.top, r.right, r.bottom], box: [q.left, q.top, q.right, q.bottom], win: [document.documentElement.clientWidth, document.documentElement.clientHeight],
      texts: items.map(function(d){ return d.querySelector('.t').textContent; }),
      roles: items.map(function(d){ return d.getAttribute('role'); }),
      checked: items.map(function(d){ return d.getAttribute('aria-checked') === 'true'; }),
      ticks: items.map(function(d){ return getComputedStyle(d.querySelector('.tick')).visibility === 'visible'; }),
      // is anything lying over an item? (the dock, the make bar, the window's edge)
      seen: !open ? null : items.map(function(d){ var x = d.getBoundingClientRect(), e = document.elementFromPoint((x.left + x.right) / 2, (x.top + x.bottom) / 2); return !!e && (e === d || d.contains(e)); }),
      focus: document.activeElement === b ? 'button' : items.indexOf(document.activeElement),
      tags: Array.from(document.querySelectorAll('#' + id + ' *')).map(function(e){ return e.tagName; }).filter(function(v, i, a){ return a.indexOf(v) === i; }).sort()
    };
  };
  window.__bar = function(){
    var out = []; Array.from(document.querySelector('#tl .tl-row').children).forEach(function(e){ if (e.className === 'tl-ur') Array.from(e.children).forEach(function(k){ out.push(k.id); }); else out.push(e.id || e.className); }); return out;
  };
  window.__room = function(){ return [parseInt(document.body.style.paddingBottom), $('dock').offsetHeight, document.documentElement.scrollWidth - document.documentElement.clientWidth]; };
})();
"""

INK = "rgb(31, 36, 48)"          # look.py's ink: what a filled button is filled with


# ---------- in Python ----------

def run_python(s):
    tp = s.tp
    W = tp.page_words()
    ours = ("menu_label", "mixed")
    case("the two new lines are OURS (in OUR_WORDS with a reason each), neither a key of hers, neither says \"Claude\": \"{name}:\" and \"Mixed\"",
         all(k in tp.OUR_WORDS and k not in tp.WORDS and len(tp.OUR_WORDS[k][1]) > 10 and "claude" not in tp.OUR_WORDS[k][0].lower() for k in ours)
         and tp.OUR_WORDS["menu_label"][0] == "{name}:" and tp.OUR_WORDS["mixed"][0] == "Mixed", [tp.OUR_WORDS.get(k) for k in ours])
    case("her words the menus show are as she wrote them: Speed, Zoom, \"{v}×\", None, Punch in, Slow zoom",
         (tp.WORDS["speed"], tp.WORDS["zoom"], tp.WORDS["speed_x"], tp.WORDS["move_none"], tp.WORDS["punch"], tp.WORDS["slow_zoom"])
         == ("Speed", "Zoom", "{v}×", "None", "Punch in", "Slow zoom"))
    case("the line under the timeline still says Speed, Zoom and Delete change every picked clip", "Speed, Zoom and Delete change all of them" in W["multi_selected"])
    page = tp.page_html(KIT)
    a = page.find("id='tlCut'")
    b = page.find("id='tlUndo'")
    between = page[page.find("</button>", a) + 9:page.rfind("<button", 0, b)]
    case("the bar the page carries: after Delete clip a thin separator, then a place each for the Speed and the Zoom menu, then Undo; no bare word Speed or Zoom between them",
         a > 0 and b > a and between == "<span class='tl-sep'></span><span class='tl-group' id='tlSpeed'></span><span class='tl-group' id='tlZoom'></span><span class='tl-ur'>"
         and "id='tlRedo'" in page[b:page.find("</span>", b)], between[:300])
    rows = {"how_much": "How much", "amt_subtle": "Subtle", "amt_medium": "Medium", "amt_strong": "Strong", "how_fast": "How fast",
            "pace_quick": "Quick", "pace_whole": "Whole clip", "pace_instant": "Instant", "pace_push": "Quick push"}
    case("the nine words of How much and How fast (Nov 13) are OURS, each with its reason, none a key of hers, none says \"Claude\"",
         all(k in tp.OUR_WORDS and k not in tp.WORDS and tp.OUR_WORDS[k][0] == v and len(tp.OUR_WORDS[k][1]) > 10 and "claude" not in v.lower() for k, v in rows.items())
         and all(W[k] == v for k, v in rows.items()), [tp.OUR_WORDS.get(k) for k in rows])
    eng = s.TR._engine()
    m = re.search(r'"zoom": (\{.*?\}\}), "undoSteps"', page)
    sent = json.loads(m.group(1)) if m else None
    case("the page is handed the engine's own numbers for how much and how fast (no number of them is written in the page's script)",
         sent == {"amount": eng.ZOOM_AMOUNT, "amounts": list(eng.ZOOM_AMOUNTS), "amountDefault": "medium",
                  "pace": {"zoom": ["quick", "whole"], "punch": ["instant", "push"]}, "paceDefault": {"zoom": "whole", "punch": "instant"}, "secs": eng.MOVE_SECS}
         and not any(n in "\n".join(ln.split("//")[0] for ln in (tp.talking_js_preview.JS + tp.talking_js_core.JS + tp.talking_js_timeline.JS).splitlines())
                     for n in ("1.15", "1.12", "1.06", "1.075", "1.24")), sent)
    js = tp.talking_js_timeline.JS
    code = "\n".join(x for x in js.splitlines() if not x.lstrip().startswith("//"))      # the script without its notes
    case("...the page carries no chip for a speed or a zoom on the timeline any more, and the menus are made of elements and text (the timeline's script never writes HTML from a string)",
         "speedChips" not in page and "zoomChips" not in page and "class='lbl'>" + _html.escape(W["speed"]) not in page and "innerHTML" not in js and "insertAdjacentHTML" not in js)
    case("...choosing still goes through the functions her chips called, and nothing else in the menus saves",
         "function(v){ speedClip(v); }" in js and "function(kind){ zoomClip(kind); }" in js and code.count("speedClip(") == 2 and code.count("zoomClip(") == 2,
         (code.count("speedClip("), code.count("zoomClip(")))


# ---------- on the page ----------

def run_page(c, s):
    W = s.tp.page_words()
    tm.make(s)
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script(tpt.HELPERS)
    c.init_script(tm.HELPERS)
    c.init_script(HELPERS)
    c.clear_errors()

    def menu(mid):
        return c.js("window.__menu(%r)" % mid)

    def multi():
        return c.js("window.__multi()")

    def is_open():
        return c.js("window.Talk.tl().menu")

    def rec():
        return s.rec(KIT) or {}

    def clip(w0):
        return '#tlClips .tl-clip[data-w="%d"]' % w0

    def click(w0, **mods):
        c.click(clip(w0), check=False, **mods)

    def item(mid, k):
        return "#%s [role=menuitemradio]:nth-child(%d)" % (mid, k + 1)

    def open_menu(mid):
        c.click("#%sBtn" % mid, check=False)
        c.wait_for("window.Talk.tl().menu === %r" % mid, 5)

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")

    def press(fn):
        """A press that saves: wait for its answer. Returns the texts of the saves it sent."""
        was, n = c.js("window.Talk.rev"), c.js("window.__saves.length")
        fn()
        moved(was)
        return c.js("window.__saves.slice(%d)" % n)

    def quiet(fn, wait=0.6):
        """A press that must save nothing: how many saves it sent."""
        n = c.js("window.__saves.length")
        fn()
        time.sleep(wait)
        return c.js("window.__saves.length") - n

    def saved_text(body):
        return body[body.index('"saved":'):]

    def open_it(**edit):
        tm.seed(s, **edit)
        c.open("about:blank")
        c.open(s.url("/talking.html" + s.q(KIT)))
        c.wait_for("window.Talk && window.Talk.loaded", 15, tell="document.body.innerText.slice(0, 200)")
        c.wait_for("document.querySelectorAll('#script .sent').length === 7", 10, tell="document.getElementById('status').textContent")
        c.wait_for("document.getElementById('vid').readyState >= 1", 15)
        c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length > 0", 10)

    def inside(g):
        x0, y0, x1, y1 = g["box"]
        return x0 >= 0 and y0 >= 0 and x1 <= g["win"][0] + 0.5 and y1 <= g["win"][1] + 0.5 and x1 - x0 > 40 and y1 - y0 > 40

    # ================= as it opens: the bar, and nothing picked =================
    open_it()
    bar = c.js("window.__bar()")
    case("the bar reads: play, the time, a separator, Split, Delete clip, a thin separator, Speed, Zoom, Undo, Redo, the timeline's own zoom",
         bar == ["tlPlay", "tlTime", "tl-sep", "tlSplit", "tlCut", "tl-sep", "tlSpeed", "tlZoom", "tlUndo", "tlRedo", "tl-scale"], bar)
    sp, zm = menu("tlSpeed"), menu("tlZoom")
    case("nothing picked: both buttons are grey and say what an untouched clip has, \"Speed: 1×\" and \"Zoom: None\", her words with our colon; no bare word beside them",
         (sp["label"], sp["value"], sp["off"], sp["on"], sp["opacity"]) == ("Speed:", "1×", True, False, "0.4")
         and (zm["label"], zm["value"], zm["off"], zm["on"], zm["opacity"]) == ("Zoom:", "None", True, False, "0.4")
         and c.count("#tl .tl-row .lbl") == 0 and c.count("#tl .tl-row .chip") == 0, (sp["label"], sp["value"], sp["off"], zm["label"], zm["value"], zm["off"]))
    c.click("#tlSpeedBtn", check=False)
    c.click("#tlZoomBtn", check=False)
    case("...a press on a grey button opens nothing, and no item is checked", is_open() is None and not menu("tlSpeed")["open"] and not menu("tlZoom")["open"]
         and not any(sp["checked"] + zm["checked"]) and not any(sp["ticks"] + zm["ticks"]), (is_open(), sp["checked"]))
    case("a screen reader hears each as a button that opens a menu: its name is \"Speed: 1×\" (the little arrow is hidden from it), aria-haspopup menu, not expanded, tied to its list; "
         "the list is a menu named Speed, its items radio items",
         sp["name"] == "Speed: 1×" and zm["name"] == "Zoom: None" and sp["arrow"] == "▾" and sp["arrowHidden"] == "true" and sp["has"] == zm["has"] == "menu"
         and sp["expanded"] == zm["expanded"] == "false" and sp["controls"] == sp["listId"] and zm["controls"] == zm["listId"] and sp["listId"] != zm["listId"]
         and (sp["role"], sp["listName"], zm["role"], zm["listName"]) == ("menu", "Speed", "menu", "Zoom")
         and sp["roles"] == ["menuitemradio"] * 4 and zm["roles"] == ["menuitemradio"] * 3, sp)
    case("the lists hold her words in her order: 1×, 1.25×, 1.5×, 2× and None, Punch in, Slow zoom; everything in them is text (buttons, spans and the list, nothing else)",
         sp["texts"] == ["1×", "1.25×", "1.5×", "2×"] and zm["texts"] == [W["move_none"], W["punch"], W["slow_zoom"]]
         and sp["tags"] == ["BUTTON", "DIV", "SPAN"] and zm["tags"] == ["BUTTON", "DIV", "SPAN"], (sp["texts"], zm["texts"], sp["tags"]))

    # ================= a press opens the list at the button =================
    click(3)
    sp = menu("tlSpeed")
    case("a clip picked: the buttons come alive, plain (not filled) for 1× and None", not sp["off"] and not sp["on"] and sp["opacity"] == "1" and sp["bg"] != INK
         and not menu("tlZoom")["off"] and not menu("tlZoom")["on"], sp["bg"])
    open_menu("tlSpeed")
    sp = menu("tlSpeed")
    case("a press on Speed opens its list: expanded, the picked clip's choice (1×) checked with a check mark and nothing else checked, the keyboard on that item",
         sp["open"] and sp["expanded"] == "true" and sp["checked"] == [True, False, False, False] and sp["ticks"] == [True, False, False, False] and sp["focus"] == 0, sp)
    case("...right at the button and ABOVE it (the bar sits on the timeline, which the list never covers): its left edge at the button's, its bottom just over the button's top",
         abs(sp["box"][0] - sp["btn"][0]) < 1 and 0 < sp["btn"][1] - sp["box"][3] <= 10 and c.js("window.Talk.tl().menuUp") is True, (sp["box"], sp["btn"]))
    case("...whole inside the window, and nothing lies over any item (not the dock, not the make bar)", inside(sp) and sp["seen"] == [True] * 4, (sp["box"], sp["win"], sp["seen"]))
    picked0 = multi()["picked"]
    c.click("#tlZoomBtn", check=False)
    c.wait_for("window.Talk.tl().menu === 'tlZoom'", 5)
    sp, zm = menu("tlSpeed"), menu("tlZoom")
    case("a press on Zoom while Speed is open: Speed closes, Zoom opens (never two), None checked, above its own button, whole inside the window, nothing over it",
         not sp["open"] and sp["expanded"] == "false" and zm["open"] and zm["expanded"] == "true" and zm["checked"] == [True, False, False] and zm["ticks"] == [True, False, False]
         and abs(zm["box"][0] - zm["btn"][0]) < 1 and zm["box"][3] < zm["btn"][1] and inside(zm) and zm["seen"] == [True] * 3, (sp["open"], zm))
    c.click("#tlZoomBtn", check=False)
    case("a press on the button again closes it; the clip is still picked", is_open() is None and not menu("tlZoom")["open"] and multi()["picked"] == picked0 == [3], (is_open(), multi()["picked"]))
    open_menu("tlZoom")
    n = quiet(lambda: c.click("#title", check=False), 0.3)
    case("a press anywhere else closes it: nothing saved, the clip still picked", is_open() is None and n == 0 and multi()["picked"] == [3], (is_open(), n))
    open_menu("tlSpeed")
    click(9)
    case("...and that press still does what it was a press on: a press on another clip closes the menu AND picks that clip", is_open() is None and multi()["picked"] == [9], (is_open(), multi()["picked"]))
    open_menu("tlZoom")
    c.desktop((1180, 1000))
    c.wait_for("window.Talk.tl().menu === null", 5)
    case("the window resized: the menu closes (it is never left where its button no longer is)", is_open() is None)
    c.desktop()

    # ================= Escape: the menu first, then what is picked =================
    click(3)
    click(6, meta=True)
    click(9, meta=True)
    open_menu("tlZoom")
    c.key("Escape")
    g = multi()
    case("three clips picked, the menu open, Escape: the menu closes FIRST, the three clips stay picked, and the button has the keyboard again",
         is_open() is None and g["picked"] == [3, 6, 9] and menu("tlZoom")["focus"] == "button", (is_open(), g["picked"], menu("tlZoom")["focus"]))
    c.key("Escape")
    case("...Escape again lets go of the clips, as ever", multi()["picked"] == [] and multi()["sel"] is None, multi()["picked"])

    # ================= one clip: every item sends what her chip's press sent =================
    open_it()
    click(3)
    bodies, looks = [], []
    plan = [("tlSpeed", 1, "1.25×", True), ("tlSpeed", 2, "1.5×", True), ("tlSpeed", 3, "2×", True), ("tlSpeed", 0, "1×", False),
            ("tlZoom", 1, W["punch"], True), ("tlZoom", 2, W["slow_zoom"], True), ("tlZoom", 0, W["move_none"], False)]
    for mid, k, _says, _lit in plan:
        open_menu(mid)
        sent = press(lambda: c.click(item(mid, k), check=False))
        bodies += sent
        g = menu(mid)
        looks.append([len(sent), g["value"], g["on"], g["checked"].index(True) if True in g["checked"] else -1, g["ticks"] == g["checked"], g["open"], is_open(), g["focus"],
                      g["bg"] == INK, multi()["picked"], multi()["n"]])
    want = ['"saved":{"speeds":[{"a":3,"b":5,"v":1.25}]}}',
            '"saved":{"speeds":[{"a":3,"b":5,"v":1.5}]}}',
            '"saved":{"speeds":[{"a":3,"b":5,"v":2}]}}',
            '"saved":{"speeds":[]}}',
            '"saved":{"zooms":[{"a":3,"b":5,"kind":"punch"}]}}',
            '"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom"}]}}',
            '"saved":{"zooms":[]}}']
    case("with ONE clip picked every item of both menus sends, character for character, what her chip's press sent: 1.25×, 1.5×, 2×, 1×, Punch in, Slow zoom, None",
         [saved_text(b) for b in bodies] == want, [saved_text(b) for b in bodies])
    case("...each choice is ONE save and one step of Undo, the menu closes, the clip stays picked, and the button has the keyboard again",
         [x[0] for x in looks] == [1] * 7 and [x[10] for x in looks] == [[i + 1, 0] for i in range(7)] and all(x[5] is False and x[6] is None and x[7] == "button" and x[9] == [3] for x in looks), looks)
    case("...and the button then says the choice, with that item (and only it) checked the next time it opens",
         [x[1] for x in looks] == [p[2] for p in plan] and [x[3] for x in looks] == [p[1] for p in plan] and all(x[4] for x in looks), [(x[1], x[3]) for x in looks])
    case("...it looks ON (filled, ink) for a speed that is not 1× and for a zoom, and plain again for 1× and for None",
         [x[2] for x in looks] == [p[3] for p in plan] and [x[8] for x in looks] == [p[3] for p in plan], [(x[2], x[8]) for x in looks])
    keys = [sorted(json.loads(b)) for b in bodies]
    case("...a save carries only what it always did (kit, base, page, saved)", all(k == ["base", "kit", "page", "saved"] for k in keys), keys[:1])
    press(lambda: c.click("#tlUndo"))
    press(lambda: c.click("#tlUndo"))
    g = menu("tlZoom")
    case("Undo twice (None, then Slow zoom) is two steps back: the clip has its Punch in again, and the button says so and is filled",
         rec().get("zooms") == [{"a": 3, "b": 5, "kind": "punch"}] and g["value"] == W["punch"] and g["on"] and g["checked"] == [False, True, False] and multi()["n"] == [5, 2], (rec().get("zooms"), g["value"], multi()["n"]))

    # ================= several clips: Mixed, or what they agree on =================
    open_it(zooms=[{"a": 3, "b": 5, "kind": "punch"}], speeds=[{"a": 3, "b": 5, "v": 1.5}])
    click(3)
    click(9, meta=True)
    sp, zm = menu("tlSpeed"), menu("tlZoom")
    case("two clips picked that do not agree (1.5× with a Punch in, and an untouched one): the buttons read \"Speed: Mixed\" and \"Zoom: Mixed\", filled, and no item is checked",
         (sp["value"], sp["name"], sp["on"]) == ("Mixed", "Speed: Mixed", True) and (zm["value"], zm["name"], zm["on"]) == ("Mixed", "Zoom: Mixed", True)
         and not any(sp["checked"] + zm["checked"] + sp["ticks"] + zm["ticks"]) and W["mixed"] == "Mixed", (sp["value"], zm["value"], sp["checked"], zm["checked"]))
    open_menu("tlZoom")
    zm = menu("tlZoom")
    case("...open, the Mixed menu has nothing checked and the keyboard on its first item", zm["open"] and not any(zm["checked"]) and zm["focus"] == 0, zm["focus"])
    sent = press(lambda: c.click(item("tlZoom", 1), check=False))
    zm = menu("tlZoom")
    case("...choosing Punch in changes both clips in one save, as the chip did; now they agree, and the button says Punch in with it checked; both clips stay picked",
         len(sent) == 1 and rec().get("zooms") == [{"a": 3, "b": 5, "kind": "punch"}, {"a": 9, "b": 11, "kind": "punch"}] and zm["value"] == W["punch"]
         and zm["checked"] == [False, True, False] and zm["on"] and multi()["picked"] == [3, 9] and multi()["n"] == [1, 0], (rec().get("zooms"), zm["value"]))
    open_menu("tlSpeed")
    press(lambda: c.click(item("tlSpeed", 0), check=False))
    sp = menu("tlSpeed")
    case("...1× on both: \"Speed: 1×\", checked, plain", sp["value"] == "1×" and sp["checked"] == [True, False, False, False] and not sp["on"] and rec().get("speeds") == [], sp["value"])
    click(0)
    click(6, meta=True)
    zm = menu("tlZoom")
    case("two untouched clips picked: \"Zoom: None\", None checked, plain", zm["value"] == W["move_none"] and zm["checked"] == [True, False, False] and not zm["on"], zm["value"])

    # ================= the keys =================
    open_it()
    click(3)
    c.js("document.getElementById('tlSpeedBtn').focus()")
    c.key("Enter")
    sp = menu("tlSpeed")
    case("the keys: Enter on the Speed button opens its list with the keyboard on the checked item", is_open() == "tlSpeed" and sp["open"] and sp["focus"] == 0, (is_open(), sp["focus"]))
    c.key("ArrowDown")
    a1 = menu("tlSpeed")["focus"]
    c.key("ArrowDown", times=3)
    a2 = menu("tlSpeed")["focus"]
    c.key("ArrowUp")
    a3 = menu("tlSpeed")["focus"]
    c.key("Home")
    a4 = menu("tlSpeed")["focus"]
    c.key("End")
    a5 = menu("tlSpeed")["focus"]
    c.key("ArrowUp")
    a6 = menu("tlSpeed")["focus"]
    case("...Down and Up move through the items and go round at the ends, Home and End jump; nothing is chosen by moving",
         [a1, a2, a3, a4, a5, a6] == [1, 0, 3, 0, 3, 2] and is_open() == "tlSpeed" and multi()["n"] == [0, 0], [a1, a2, a3, a4, a5, a6])
    sent = press(lambda: c.key("Enter"))
    sp = menu("tlSpeed")
    case("...Enter chooses the item the keyboard is on (1.5×): the same save as a press, the menu closed, the keyboard back on the button",
         [saved_text(b) for b in sent] == ['"saved":{"speeds":[{"a":3,"b":5,"v":1.5}]}}'] and is_open() is None and sp["focus"] == "button" and sp["value"] == "1.5×", (sent, sp["focus"]))
    c.key("Space")
    c.wait_for("window.Talk.tl().menu === 'tlSpeed'", 5)
    sp = menu("tlSpeed")
    paused = c.js("document.getElementById('vid').paused")
    case("the spacebar on the button opens the list (on the checked item, 1.5×) and does not play the video", sp["open"] and sp["focus"] == 2 and paused is True, (sp["focus"], paused))
    c.key("ArrowDown")
    sent = press(lambda: c.key("Space"))
    case("...and the spacebar on an item chooses it (2×), never playing the video behind the open menu",
         [saved_text(b) for b in sent] == ['"saved":{"speeds":[{"a":3,"b":5,"v":2}]}}'] and is_open() is None and c.js("document.getElementById('vid').paused") is True and menu("tlSpeed")["focus"] == "button", sent)
    c.js("document.getElementById('tlZoomBtn').focus()")
    c.key("ArrowDown")
    z1 = [is_open(), menu("tlZoom")["focus"]]
    c.key("Escape")
    z2 = [is_open(), menu("tlZoom")["focus"]]
    c.key("ArrowUp")
    z3 = [is_open(), menu("tlZoom")["focus"]]
    c.key("Tab")
    z4 = is_open()
    case("Down on the Zoom button opens it on the checked item, Escape closes it with the button focused, Up opens it on the last item, Tab closes it and moves on; nothing saved by any of it",
         z1 == ["tlZoom", 0] and z2 == [None, "button"] and z3 == ["tlZoom", 2] and z4 is None and multi()["n"] == [2, 0] and multi()["picked"] == [3], (z1, z2, z3, z4))
    c.js("document.getElementById('tlZoomBtn').focus()")
    c.key("Mod+Z")
    c.wait_for("window.Talk.UNDO.length === 1", 10)
    case("with the keyboard on a menu's button the timeline's own keys still work (Undo by key took one step back)", multi()["n"] == [1, 1] and menu("tlSpeed")["value"] == "1.5×", multi()["n"])

    # ================= greyed while open: it closes itself =================
    open_it()
    click(3)
    open_menu("tlZoom")
    s.cut(KIT, [[3, 5]])
    c.js("window.Talk.poll(true)")
    c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length === 6", 10)
    zm = menu("tlZoom")
    case("the picked clip cut from the chat while its menu is open: the buttons go grey and the menu closes itself (never a list for a clip that is gone)",
         is_open() is None and not zm["open"] and zm["off"] and zm["expanded"] == "false" and multi()["picked"] == [], (is_open(), zm["off"]))

    # ================= no room above: under the button, still inside the window =================
    open_it()
    c.desktop((1280, 330))
    try:
        c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length > 0", 10)
        click(3)
        open_menu("tlSpeed")
        sp = menu("tlSpeed")
        case("a window with no room above the button: the list goes under it instead, whole inside the window, every item still pressable",
             c.js("window.Talk.tl().menuUp") is False and sp["box"][1] >= sp["btn"][3] and inside(sp) and sp["seen"] == [True] * 4, (sp["box"], sp["btn"], sp["win"], sp["seen"]))
        sent = press(lambda: c.click(item("tlSpeed", 1), check=False))
        case("...and a press on an item there chooses it", [saved_text(b) for b in sent] == ['"saved":{"speeds":[{"a":3,"b":5,"v":1.25}]}}'], sent)
    finally:
        c.desktop()

    # ================= clean =================
    case("no part of the page failed, no pop-up was asked for, nothing was asked of the internet",
         c.js("window.Talk.faults.length") == 0 and c.js("window.__dialogs") == 0 and not list(c.dialogs) and not c.outside_requests(), (c.js("window.Talk.faults"), c.outside_requests()[:3]))
    errs = [e for e in c.page_errors() if "Failed to load resource" not in e and "ERR_BLOCKED" not in e]
    case("no page errors", not errs, errs[:3])

    # ================= phone width =================
    c.phone()
    try:
        open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom"}], speeds=[{"a": 3, "b": 5, "v": 1.25}])
        room = c.js("window.__room()")
        case("phone width: no sideways scroll, and the page leaves the dock its room", room[2] <= 0 and room[0] == room[1] + 24 and c.js("window.innerWidth") == 390, room)
        click(3)
        room = c.js("window.__room()")
        c.tap("#tlZoomBtn", check=False)
        c.wait_for("window.Talk.tl().menu === 'tlZoom'", 5)
        zm = menu("tlZoom")
        case("...a tap opens the Zoom list: Slow zoom checked, whole inside the window, nothing over it, no sideways scroll",
             zm["open"] and zm["checked"] == [False, False, True] and inside(zm) and zm["seen"] == [True] * 3 and c.js("window.__room()")[2] <= 0, (zm["box"], zm["win"], zm["seen"]))
        sent = press(lambda: c.tap(item("tlZoom", 0), check=False))
        case("...a tap on None takes the zoom off: the save her chip sent, the menu closed, the button plain",
             [saved_text(b) for b in sent] == ['"saved":{"zooms":[]}}'] and is_open() is None and not menu("tlZoom")["on"] and menu("tlZoom")["value"] == W["move_none"], sent)
        c.tap("#tlSpeedBtn", check=False)
        c.wait_for("window.Talk.tl().menu === 'tlSpeed'", 5)
        sp = menu("tlSpeed")
        case("...the Speed list too: 1.25× checked, whole inside the window, nothing over it", sp["checked"] == [False, True, False, False] and inside(sp) and sp["seen"] == [True] * 4, (sp["box"], sp["win"]))
        c.tap("#title", check=False)
        c.wait_for("window.Talk.tl().menu === null", 5)
        case("...and a tap anywhere else closes it", is_open() is None)
    finally:
        c.desktop()
    # ---- the review round (Nov 13) ----
    # the bar keeps its shape: each button's value has the room of its longest word, so picking another clip, or
    # choosing from a menu, never moves a button; and Undo and Redo are never parted
    tm.seed(s, zooms=[{"a": 3, "b": 5, "kind": "zoom"}], speeds=[{"a": 3, "b": 5, "v": 1.5}])
    SHAPE = ("(function(){ var row = document.querySelector('#tl .tl-row').getBoundingClientRect().top, b = function(id){ var r = document.getElementById(id).getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top - row), Math.round(r.width)]; };"
             " return {speed: b('tlSpeedBtn'), zoom: b('tlZoomBtn'), undo: b('tlUndo'), redo: b('tlRedo'), scale: b('tlScale'), dock: document.getElementById('dock').offsetHeight,"
             " words: [document.querySelector('#tlSpeedBtn .val').textContent, document.querySelector('#tlZoomBtn .val').textContent],"
             " side: document.documentElement.scrollWidth - document.documentElement.clientWidth}; })()")
    moves, parted, sideways, words = [], [], [], None
    try:
        # 840, 430 and 336 are widths at which Undo and Redo would part without their pairing (found by trying every 6 px)
        for width, height in ((1280, 800), (1100, 800), (840, 800), (800, 793), (640, 800), (430, 800), (375, 812), (336, 800)):
            c.phone(width=width, height=height, scale=1, touch=False)
            c.open("about:blank")
            c.open(s.url("/talking.html" + s.q(KIT)))
            c.wait_for("window.Talk && window.Talk.loaded && document.querySelectorAll('#tlClips .tl-clip').length > 0", 15)
            c.wait_for("document.fonts.status === 'loaded'", 10)
            seen = [c.js(SHAPE)]                       # nothing picked
            click(0)
            seen.append(c.js(SHAPE))                   # 1×, None
            click(3)
            seen.append(c.js(SHAPE))                   # 1.5×, Slow zoom
            click(9, meta=True)
            seen.append(c.js(SHAPE))                   # Mixed, Mixed
            if width == 1280:
                words = [g["words"] for g in seen]
            for n, g in enumerate(seen[1:]):
                # several picked: our line under the timeline is longer, but it holds the room of its longest words
                # at every width (multiRoom), so the dock's height is compared in every state
                keys = ("speed", "zoom", "undo", "redo", "scale", "dock")
                if any(g[k] != seen[0][k] for k in keys):
                    moves.append((width, g["words"], {k: (seen[0][k], g[k]) for k in keys if g[k] != seen[0][k]}))
            for g in seen:
                if g["undo"][1] != g["redo"][1]:
                    parted.append((width, g["words"], g["undo"], g["redo"]))
                if g["side"] > 0:
                    sideways.append((width, g["words"], g["side"]))
        case("the four states really differ in their words (nothing picked, 1× and None, 1.5× and Slow zoom, Mixed and Mixed)",
             words == [["1×", "None"], ["1×", "None"], ["1.5×", "Slow zoom"], ["Mixed", "Mixed"]], words)
        case("the bar keeps its shape at eight window widths from 1280 down to 336: with another clip picked, or several that disagree, the two menu buttons, Undo, Redo and the "
             "timeline's own zoom stay exactly where they were in the bar, and the dock is the same height (the line under the timeline keeps room for its longest words)", not moves, moves[:3])
        case("...Undo and Redo sit side by side on one row at every one of those widths, in every state", not parted, parted[:3])
        case("...and nothing scrolls sideways at any of them", not sideways, sideways[:3])
    finally:
        c.desktop()

    # Delete or Backspace inside an open list does nothing: the picked clip is not deleted
    open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom"}])
    click(3)
    open_menu("tlZoom")
    clips = c.count("#tlClips .tl-clip")
    n = quiet(lambda: (c.key("Backspace"), c.key("Delete")))
    case("with a menu open, Backspace and Delete delete nothing: no save, the same clips, the clip still picked, the menu still open",
         n == 0 and c.count("#tlClips .tl-clip") == clips and not rec().get("cut") and multi()["sel"] == "clip" and is_open() == "tlZoom", (n, c.count("#tlClips .tl-clip"), rec().get("cut"), is_open()))
    c.key("Escape")
    sent = press(lambda: c.key("Backspace"))
    case("...and with the menu closed, Backspace deletes the picked clip as ever", [saved_text(b) for b in sent] == ['"saved":{"cut":[[3,5]]}}'], sent)

    # the window losing the keyboard closes the menu
    open_it()
    click(3)
    open_menu("tlSpeed")
    c.js("window.dispatchEvent(new Event('blur'))")
    case("the window losing the keyboard closes the open menu, saving nothing", is_open() is None and not menu("tlSpeed")["open"], is_open())

    # the shading: only under the pointer or the keyboard's own ring, so with Mixed no item looks like the choice
    open_it(zooms=[{"a": 3, "b": 5, "kind": "punch"}], speeds=[{"a": 3, "b": 5, "v": 1.5}])
    click(3)
    click(9, meta=True)
    open_menu("tlZoom")
    c.mouse_move(5, 5)
    BGS = "Array.from(document.querySelectorAll('#tlZoomList [role=menuitemradio]')).map(function(d){ return getComputedStyle(d).backgroundColor; })"
    bgs = c.js(BGS)
    case("Mixed, opened with the mouse: no item is shaded as if it were the choice (and none is checked)",
         all(b in ("rgba(0, 0, 0, 0)", "transparent") for b in bgs) and not any(menu("tlZoom")["checked"]), bgs)
    c.key("ArrowDown")
    bgs = c.js(BGS)
    case("...moved to with the arrow keys, the item the keyboard is on is shaded (and only that one)",
         [b in ("rgba(0, 0, 0, 0)", "transparent") for b in bgs] == [True, False, True] and menu("tlZoom")["focus"] == 1, (bgs, menu("tlZoom")["focus"]))
    c.key("Escape")
    arrow = c.js("parseFloat(getComputedStyle(document.querySelector('#tlZoomBtn .car')).fontSize)")
    case("the little arrow that says a list opens is drawn at 14 px or more (it was 10, and read as a dot)", arrow >= 14, arrow)


    # ================= How much and How fast: two rows under the Zoom menu's items (Dustin, Nov 13) =================
    ROWS = r"""(function(){
      var l = document.getElementById('tlZoomList'), more = l.querySelector('.tl-mx'), de = document.documentElement;
      var vis = function(e){ return !!e && getComputedStyle(e).display !== 'none' && e.getClientRects().length > 0; };
      var last = Array.from(l.querySelectorAll('.tl-mi')).pop().getBoundingClientRect(), q = l.getBoundingClientRect();
      return {shown: vis(more), line: getComputedStyle(more).borderTopWidth, under: vis(more) && more.getBoundingClientRect().top >= last.bottom - 0.5,
              box: [q.left, q.top, q.right, q.bottom], win: [de.clientWidth, de.clientHeight], side: de.scrollWidth - de.clientWidth,
              up: window.Talk.tl().menuUp, btnTop: document.getElementById('tlZoomBtn').getBoundingClientRect().top,
              focus: document.activeElement ? (document.activeElement.getAttribute('data-amount') || document.activeElement.getAttribute('data-pace') || document.activeElement.getAttribute('data-z') || document.activeElement.id) : null,
              groups: Array.from(l.querySelectorAll('[role=radiogroup]')).filter(vis).map(function(g){
                return {name: g.getAttribute('aria-label'), label: g.querySelector('.lb').textContent, labelHidden: g.querySelector('.lb').getAttribute('aria-hidden'),
                        opts: Array.from(g.querySelectorAll('[role=radio]')).map(function(d){
                          var r = d.getBoundingClientRect(), e = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
                          return {t: d.textContent, v: d.getAttribute('data-amount') || d.getAttribute('data-pace'), on: d.getAttribute('aria-checked') === 'true',
                                  bg: getComputedStyle(d).backgroundColor, seen: e === d, tab: d.tabIndex, top: r.top, left: r.left, right: r.right}; })}; })};
    })()"""

    def rows():
        return c.js(ROWS)

    def lit(g):
        return [o["v"] for o in g["opts"] if o["on"]]

    def radio(v):
        return '#tlZoomList [role=radio][data-amount="%s"], #tlZoomList [role=radio][data-pace="%s"]' % (v, v)

    def in_window(r):
        x0, y0, x1, y1 = r["box"]
        return x0 >= 0 and y0 >= 0 and x1 <= r["win"][0] + 0.5 and y1 <= r["win"][1] + 0.5

    case("the page holds the engine's own numbers for a zoom (the same table the CapCut builder reads)",
         c.js("window.Talk.ZS.amount") == s.TR._engine().ZOOM_AMOUNT and c.js("window.Talk.ZS.secs") == s.TR._engine().MOVE_SECS)

    # with None: no rows
    open_it()
    click(3)
    open_menu("tlZoom")
    r = rows()
    case("a clip with no zoom: the Zoom menu is its three items and nothing more (no How much, no How fast, no hairline)",
         not r["shown"] and r["groups"] == [] and menu("tlZoom")["texts"] == [W["move_none"], W["punch"], W["slow_zoom"]], r)
    c.key("ArrowDown"); c.key("ArrowDown"); c.key("ArrowDown")
    case("...and the arrows walk only those three (three presses down from None are back on None)", rows()["focus"] == "" and menu("tlZoom")["focus"] == 0, rows()["focus"])
    c.key("Escape")

    # a slow zoom nobody set
    open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom"}])
    click(3)
    shape0 = c.js(SHAPE)
    open_menu("tlZoom")
    r = rows()
    g = r["groups"]
    case("a clip with a Slow zoom: under the three items and a hairline, two rows, How much (Subtle | Medium | Strong) and How fast (Quick | Whole clip)",
         r["shown"] and r["under"] and r["line"] == "1px" and [x["name"] for x in g] == ["How much", "How fast"]
         and [[o["t"] for o in x["opts"]] for x in g] == [["Subtle", "Medium", "Strong"], ["Quick", "Whole clip"]]
         and [[o["v"] for o in x["opts"]] for x in g] == [["subtle", "medium", "strong"], ["quick", "whole"]], g)
    case("...what a zoom has by itself is lit, and only that: Medium and Whole clip (filled, like a button that is on)",
         lit(g[0]) == ["medium"] and lit(g[1]) == ["whole"] and all((o["bg"] == INK) == o["on"] for x in g for o in x["opts"]), [(o["v"], o["bg"]) for x in g for o in x["opts"]])
    case("...a screen reader hears each row as a named radio group (the row's name once: the words drawn are hidden from it), its choices radios with checked or not",
         c.js("Array.from(document.querySelectorAll('#tlZoomList [role=radiogroup]')).filter(function(g){ return !g.hidden; }).map(function(g){ return [g.getAttribute('aria-label'), g.querySelector('.lb').getAttribute('aria-hidden'), "
              "Array.from(g.querySelectorAll('[role=radio]')).map(function(d){ return d.getAttribute('aria-checked'); }).join()]; })")
         == [["How much", "true", "false,true,false"], ["How fast", "true", "true,false".replace("true,false", "false,true")]])
    case("...each choice of a row sits beside the next on one line (joined), nothing lies over any of them, and the list is whole inside the window, above its button",
         all(len({round(o["top"]) for o in x["opts"]}) == 1 and all(abs(a["right"] - b["left"]) < 1.5 for a, b in zip(x["opts"], x["opts"][1:])) and all(o["seen"] for o in x["opts"]) for x in g)
         and in_window(r) and r["up"] is True and r["box"][3] <= r["btnTop"], (r["box"], r["btnTop"]))
    n0 = multi()["n"]
    sent = press(lambda: c.click(radio("strong"), check=False))
    r = rows()
    case("choosing Strong saves at once, in ONE save that says only that (the zoom with its amount; nothing else is added)",
         [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom","amount":"strong"}]}}']
         and rec().get("zooms") == [{"a": 3, "b": 5, "kind": "zoom", "amount": "strong"}], sent)
    case("...the menu STAYS OPEN with Strong lit now (and Medium not), the keyboard still on Strong, and it is one step of Undo",
         is_open() == "tlZoom" and lit(r["groups"][0]) == ["strong"] and lit(r["groups"][1]) == ["whole"] and r["focus"] == "strong" and multi()["n"] == [n0[0] + 1, 0], (is_open(), r["focus"], multi()["n"]))
    sent = press(lambda: c.click(radio("quick"), check=False))
    r = rows()
    case("...so both can be set: Quick is one more save, the menu still open, Strong and Quick both lit",
         [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom","amount":"strong","pace":"quick"}]}}']
         and is_open() == "tlZoom" and lit(r["groups"][0]) == ["strong"] and lit(r["groups"][1]) == ["quick"] and multi()["n"] == [n0[0] + 2, 0], (sent, is_open()))
    case("...the Zoom button still reads \"Zoom: Slow zoom\" (the choice is not put in the button), and the bar is exactly where and what it was",
         menu("tlZoom")["name"] == "Zoom: Slow zoom" and c.js(SHAPE) == shape0, (menu("tlZoom")["name"], c.js(SHAPE), shape0))
    n = quiet(lambda: c.click(radio("quick"), check=False))
    case("...a press on the choice it already has saves nothing and is no step of Undo; the menu stays open", n == 0 and is_open() == "tlZoom" and multi()["n"] == [n0[0] + 2, 0], n)
    case("...the CapCut plan (built here, never written into CapCut) has that clip's zoom ending on 1.2, the Strong amount",
         [x[2] for x in tm.zoom_values(s) if x[0] == 0] == [1.2] or max(x[3] for x in tm.zoom_values(s)) == 1.2, tm.zoom_values(s))
    sent = press(lambda: c.click(radio("medium"), check=False))
    case("choosing Medium again takes the amount out of the record (what a zoom has by itself is never written); Quick stays",
         [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom","pace":"quick"}]}}'] and lit(rows()["groups"][0]) == ["medium"], sent)
    press(lambda: c.click(radio("whole"), check=False))
    case("...and Whole clip again leaves the zoom exactly as a zoom nobody set: a, b and kind", json.dumps(rec().get("zooms")) == json.dumps([{"a": 3, "b": 5, "kind": "zoom"}]), rec().get("zooms"))
    c.key("Escape")
    press(lambda: c.click("#tlUndo"))
    press(lambda: c.click("#tlUndo"))
    case("Undo twice brings back Quick, then Strong with it: each choice was its own step", rec().get("zooms") == [{"a": 3, "b": 5, "kind": "zoom", "amount": "strong", "pace": "quick"}], rec().get("zooms"))

    # the kinds: a punch in has its own How fast; a new kind starts as made; the same kind again keeps what it had
    open_menu("tlZoom")
    sent = press(lambda: c.click(item("tlZoom", 1), check=False))
    case("choosing Punch in on a clip with a Strong, Quick slow zoom closes the menu, as ever, and the new punch in starts as made (no amount, no pace)",
         is_open() is None and [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"punch"}]}}'], sent)
    open_menu("tlZoom")
    g = rows()["groups"]
    case("a clip with a Punch in: How much is the same row, and How fast is Instant | Quick push, with Medium and Instant lit",
         [x["name"] for x in g] == ["How much", "How fast"] and [o["t"] for o in g[1]["opts"]] == ["Instant", "Quick push"] and [o["v"] for o in g[1]["opts"]] == ["instant", "push"]
         and lit(g[0]) == ["medium"] and lit(g[1]) == ["instant"], g)
    press(lambda: c.click(radio("push"), check=False))
    press(lambda: c.click(radio("subtle"), check=False))
    case("...Quick push and Subtle are saved on the punch in", rec().get("zooms") == [{"a": 3, "b": 5, "kind": "punch", "amount": "subtle", "pace": "push"}], rec().get("zooms"))
    n = quiet(lambda: c.click(item("tlZoom", 1), check=False))
    case("...choosing Punch in again on that clip keeps what it has (Subtle, Quick push), and the menu closes",
         rec().get("zooms") == [{"a": 3, "b": 5, "kind": "punch", "amount": "subtle", "pace": "push"}] and is_open() is None, (n, rec().get("zooms")))
    open_menu("tlZoom")
    press(lambda: c.click(item("tlZoom", 0), check=False))
    open_menu("tlZoom")
    case("...and None takes the zoom away, and the rows with it", rec().get("zooms") == [] and not rows()["shown"], rec().get("zooms"))
    c.key("Escape")

    # another clip's change leaves a zoom's settings alone
    open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom", "amount": "strong", "pace": "quick"}])
    click(9)
    open_menu("tlZoom")
    press(lambda: c.click(item("tlZoom", 1), check=False))
    case("a zoom on ANOTHER clip changes nothing of this one: the Strong, Quick slow zoom is saved back with both",
         rec().get("zooms") == [{"a": 3, "b": 5, "kind": "zoom", "amount": "strong", "pace": "quick"}, {"a": 9, "b": 11, "kind": "punch"}], rec().get("zooms"))
    press(lambda: c.js("document.querySelector('#script [data-move=\"zoom\"][data-k=\"5\"]').click()"))
    case("...nor does a Move pressed under a sentence in the script, which makes a zoom as made (no amount, no pace)",
         rec().get("zooms") == [{"a": 3, "b": 5, "kind": "zoom", "amount": "strong", "pace": "quick"}, {"a": 9, "b": 11, "kind": "punch"}, {"a": 15, "b": 17, "kind": "zoom"}], rec().get("zooms"))

    # several clips
    click(3)
    click(9, meta=True)
    open_menu("tlZoom")
    g = rows()["groups"]
    case("a Slow zoom and a Punch in picked together: How much shows with nothing lit (Strong and Medium disagree); How fast is not shown (its choices are not the same for the two)",
         [x["name"] for x in g] == ["How much"] and lit(g[0]) == [], g)
    sent = press(lambda: c.click(radio("subtle"), check=False))
    g = rows()["groups"]
    case("...choosing Subtle gives it to both picked zooms in ONE save, leaves the third zoom alone, and now Subtle is lit; the menu stays open, both clips stay picked",
         len(sent) == 1 and rec().get("zooms") == [{"a": 3, "b": 5, "kind": "zoom", "amount": "subtle", "pace": "quick"}, {"a": 9, "b": 11, "kind": "punch", "amount": "subtle"},
                                                    {"a": 15, "b": 17, "kind": "zoom"}]
         and lit(g[0]) == ["subtle"] and is_open() == "tlZoom" and multi()["picked"] == [3, 9], (sent, rec().get("zooms")))
    c.key("Escape")
    click(3)
    click(15, meta=True)
    open_menu("tlZoom")
    g = rows()["groups"]
    case("two Slow zooms picked that differ in both: both rows show (they are one kind) and nothing is lit in either",
         [x["name"] for x in g] == ["How much", "How fast"] and lit(g[0]) == [] and lit(g[1]) == [] and menu("tlZoom")["value"] == W["slow_zoom"], g)
    press(lambda: c.click(radio("whole"), check=False))
    g = rows()["groups"]
    case("...Whole clip on both: lit, and the Quick is gone from the record",
         lit(g[1]) == ["whole"] and rec().get("zooms")[0] == {"a": 3, "b": 5, "kind": "zoom", "amount": "subtle"} and rec().get("zooms")[2] == {"a": 15, "b": 17, "kind": "zoom"}, rec().get("zooms"))
    c.key("Escape")
    click(3)
    click(12, meta=True)
    open_menu("tlZoom")
    g = rows()["groups"]
    case("a clip with a zoom and a clip with none picked together: the rows show (a picked clip has a zoom) and speak for the zoom there is",
         lit(g[0]) == ["subtle"] and lit(g[1]) == ["whole"], g)
    press(lambda: c.click(radio("strong"), check=False))
    case("...and a choice changes that zoom only; the clip with none still has none", rec().get("zooms")[0] == {"a": 3, "b": 5, "kind": "zoom", "amount": "strong"} and len(rec().get("zooms")) == 3, rec().get("zooms"))
    c.key("Escape")

    # one slow zoom joined across clips is ONE zoom
    open_it(zooms=[{"a": 3, "b": 8, "kind": "zoom"}])
    click(6)
    open_menu("tlZoom")
    sent = press(lambda: c.click(radio("quick"), check=False))
    v = tm.zoom_values(s)
    case("a slow zoom joined across two clips is one zoom with one setting: Quick chosen with only its second clip picked is saved on the whole zoom, never a piece of it",
         [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":8,"kind":"zoom","pace":"quick"}]}}'], sent)
    case("...in the CapCut plan it is still ONE move: 1.0 at the run's start, and the second clip starts on the value the first ended on",
         v[1][1] == 1.0 and (v[2][1] == v[1][2] if v[2][1] is not None else v[2][3] == v[1][2]), v)
    c.key("Escape")

    # the keys
    open_it(zooms=[{"a": 3, "b": 5, "kind": "zoom"}])
    click(3)
    c.js("document.getElementById('tlZoomBtn').focus()")
    c.key("Enter")
    walk = [rows()["focus"]]
    for k in ("ArrowDown", "ArrowRight", "ArrowDown", "ArrowDown", "ArrowDown", "ArrowDown", "ArrowUp", "ArrowLeft", "End", "Home"):
        c.key(k)
        walk.append(rows()["focus"])
    case("the keyboard reaches every choice: from Slow zoom the arrows go down into How much (Subtle, Medium, Strong), on into How fast (Quick, Whole clip), round to None and back; "
         "Left and Right move along a row; End is the last choice, Home the first item",
         walk == ["zoom", "subtle", "medium", "strong", "quick", "whole", "", "whole", "quick", "whole", ""], walk)
    case("...every choice can hold the keyboard without being a stop of its own on the page (tabindex -1, like the items above)",
         all(o["tab"] == -1 for x in rows()["groups"] for o in x["opts"]))
    c.key("End")
    c.key("ArrowLeft")
    sent = press(lambda: c.key("Enter"))
    case("...Enter on a choice chooses it and the menu stays open with the keyboard where it was; the space bar the same, and neither plays the video",
         [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom","pace":"quick"}]}}'] and is_open() == "tlZoom" and rows()["focus"] == "quick"
         and c.js("document.getElementById('vid').paused") is True, (sent, is_open(), rows()["focus"]))
    c.key("ArrowUp")
    sent = press(lambda: c.key(" "))
    case("...(the space bar on Strong)", [saved_text(b) for b in sent] == ['"saved":{"zooms":[{"a":3,"b":5,"kind":"zoom","amount":"strong","pace":"quick"}]}}']
         and is_open() == "tlZoom" and c.js("document.getElementById('vid').paused") is True, sent)
    c.key("Escape")
    case("...Escape closes it with the keyboard back on the Zoom button, and the clip still picked",
         is_open() is None and c.js("document.activeElement.id") == "tlZoomBtn" and multi()["sel"] == "clip", c.js("document.activeElement.id"))

    # the preview draws the same function of time as the CapCut plan is cut from
    eng = s.TR._engine()
    grid = [(z, tt, span) for z in ({"kind": "zoom"}, {"kind": "zoom", "amount": "subtle"}, {"kind": "zoom", "amount": "strong", "pace": "quick"}, {"kind": "punch"},
                                    {"kind": "punch", "amount": "strong", "pace": "push"}, {"kind": "punch", "amount": "subtle"}, {"kind": "zoom", "pace": "quick"})
            for span in (0.2, 0.9, 4.0) for tt in (0.0, 0.07, 0.2, 0.35, 0.5, 0.9, 1.0, 2.0, 4.0) if tt <= span]
    theirs = c.js("(%s).map(function(x){ return window.Talk.zoomValue(x[0], x[1], x[2]); })" % json.dumps(grid))
    case("the page's function of time for a zoom is the engine's, value for value (every amount and pace, short stretches and long): the preview and the CapCut plan follow one curve",
         len(grid) > 100 and all(abs(a - eng.zoom_value(z, tt, span)) < 1e-12 for a, (z, tt, span) in zip(theirs, grid))
         and c.js("[0, 0.25, 0.5, 0.75, 1, -2, 9].map(window.Talk.ease)") == [0, 0.15625, 0.5, 0.84375, 1, 0, 1], theirs[:6])
    SCALE = ("(function(tt){ var v = document.getElementById('vid'); v.currentTime = tt; window.Talk.frame(); var m = /scale\\(([0-9.]+)\\)/.exec(v.style.transform || ''), T = window.Talk, "
             "R = T.reelAt(tt), zs = T.zoomSpan(0); return [m ? +m[1] : null, R - zs[0], zs[1] - zs[0]]; })")
    seen = [c.js(SCALE + "(%r)" % tt) for tt in (0.45, 0.5, 0.6, 0.7, 0.8)]
    zq = {"kind": "zoom", "amount": "strong", "pace": "quick"}
    case("...and the preview really draws it: on the Strong, Quick slow zoom the picture's scale at five moments is the engine's value for that moment, growing, never a straight line",
         all(abs(sc - eng.zoom_value(zq, tt, max(0.1, span))) < 1e-5 for sc, tt, span in seen) and all(a[0] < b[0] for a, b in zip(seen, seen[1:]))
         and 1.0 <= seen[0][0] < seen[-1][0] <= 1.2, seen)
    tm.seed(s, zooms=[{"a": 3, "b": 5, "kind": "punch", "pace": "push", "amount": "strong"}])
    c.open("about:blank")
    c.open(s.url("/talking.html" + s.q(KIT)))
    c.wait_for("window.Talk && window.Talk.loaded && document.querySelectorAll('#tlClips .tl-clip').length > 0", 15)
    c.wait_for("document.getElementById('vid').readyState >= 1", 15)
    seen = [c.js(SCALE + "(%r)" % tt) for tt in (0.44, 0.5, 0.6, 0.78)]
    zp = {"kind": "punch", "amount": "strong", "pace": "push"}
    case("...a Strong punch in with Quick push starts near 1 and pushes in to 1.24 on the same curve, then holds",
         all(abs(sc - eng.zoom_value(zp, tt, max(0.1, span))) < 1e-5 for sc, tt, span in seen) and seen[0][0] < 1.1 and seen[-1][0] == 1.24, seen)

    # a phone's width: the rows fit, inside the window, and the bar keeps still
    try:
        fits = []
        for width, height in ((375, 812), (336, 800)):
            c.phone(width=width, height=height, scale=1, touch=False)
            open_it(zooms=[{"a": 3, "b": 5, "kind": "punch"}])
            c.wait_for("document.fonts.status === 'loaded'", 10)
            click(3)
            before = c.js(SHAPE)
            open_menu("tlZoom")
            r = rows()
            press(lambda: c.click(radio("push"), check=False))
            r2 = rows()
            fits.append((width, in_window(r) and in_window(r2), r["up"], r["side"] == 0 == r2["side"],
                         all(o["seen"] for x in r["groups"] for o in x["opts"]), all(len({round(o["top"]) for o in x["opts"]}) == 1 for x in r["groups"]),
                         [len(x["opts"]) for x in r["groups"]] == [3, 2], c.js(SHAPE) == before, is_open() == "tlZoom", lit(r2["groups"][1]) == ["push"]))
            c.key("Escape")
        case("at a phone's width (375 and 336): the menu with its two rows is whole inside the window, opening upward; every choice is on its row and can be pressed; nothing scrolls "
             "sideways; and after a choice the menu is still open and the bar has not moved", all(all(x[1:]) for x in fits), fits)
    finally:
        c.desktop()
    case("nothing on the page threw while the rows were used", not c.js("window.Talk.faults") and c.js("window.__dialogs") == 0, c.js("window.Talk.faults"))


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
    work = Path(tempfile.mkdtemp(prefix="talking-menus-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.make()
    try:
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        tm.make(s)
        group("the two menus, in Python and by request", run_python, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the two menus on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1100)) as c:
                group("the two menus on the page", run_page, c, s)
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
