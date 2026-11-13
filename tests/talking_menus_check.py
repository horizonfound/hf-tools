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
  - phone width: no sideways scroll, the lists inside the window, a finger's tap chooses, and when a button's
    words make the bar wrap, the dock's room is measured again at once;
  - everything is text (no element made from a string), no page error, nothing asked of the internet.

What it never does: touch the real ~/.studio (STUDIO_HOME is a scratch folder; the real one is listed before and
after), start the real transcriber, write into CapCut, or play a video. The page server (port 9670 up) and the
hidden Chrome are this test's own and are stopped at the end.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
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
    return Array.from(document.querySelector('#tl .tl-row').children).map(function(e){ return e.id || e.className; });
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
         a > 0 and b > a and between == "<span class='tl-sep'></span><span class='tl-group' id='tlSpeed'></span><span class='tl-group' id='tlZoom'></span>", between[:300])
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
    # the dock's room when a button's words make the bar wrap: a width is looked for at which the bar is one line
    # taller with clip 3 picked ("1.25×", "Slow zoom") than with clip 0 picked ("1×", "None")
    tm.seed(s, zooms=[{"a": 3, "b": 5, "kind": "zoom"}], speeds=[{"a": 3, "b": 5, "v": 1.25}])
    found = None
    try:
        for width in range(330, 1100, 8):
            c.phone(width=width, height=900, touch=False)
            c.open("about:blank")
            c.open(s.url("/talking.html" + s.q(KIT)))
            c.wait_for("window.Talk && window.Talk.loaded && document.querySelectorAll('#tlClips .tl-clip').length > 0", 15)
            # the 3-second look measures the dock too: held off, so what is seen is what the press itself did
            c.js("window.Talk.poll = function(){}")
            hs = c.js("(function(){ var T = window.Talk, d = document.getElementById('dock'), b = function(w){ var e = document.querySelector('#tlClips .tl-clip[data-w=\"' + w + '\"]'),"
                      " r = e.getBoundingClientRect(), o = {bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, button: 0, buttons: 1, pointerId: 1, pointerType: 'mouse'};"
                      " e.dispatchEvent(new PointerEvent('pointerdown', o)); o.buttons = 0; document.getElementById('tlTrack').dispatchEvent(new PointerEvent('pointerup', o)); return [d.offsetHeight, parseInt(document.body.style.paddingBottom),"
                      " document.documentElement.scrollWidth - document.documentElement.clientWidth]; }; var a = b(0), z = b(3), y = b(0); return [a, z, y]; })()")
            if hs[1][0] - hs[0][0] >= 20:          # a whole line taller
                found = (width, hs)
                break
        case("at a width where the longer words make the bar wrap (found: %s px), picking the clip with \"1.25×\" and \"Slow zoom\" makes the dock taller, and the page gives it that room "
             "AT ONCE (and takes it back when the other clip is picked); no sideways scroll" % (found[0] if found else "none"),
             bool(found) and found[1][1][0] > found[1][0][0] and all(h[1] == h[0] + 24 and h[2] <= 0 for h in found[1]) and found[1][2][0] == found[1][0][0], found)
    finally:
        c.desktop()


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
