#!/usr/bin/env python3
"""The centered line on the talking reel page's preview (ours, not on Nicole's page; Dustin, Nov 13: "when I'm
dragging the text around... there should be like a snap to the center point that shows a vertical line straight
down so that you know that the text is centered right there").

    python3 tests/guard.py 3000 python3 tests/talking_snap_check.py [--no-chrome] [--port 9740] [--work <folder>]

Run it under the memory guard, ONE such test at a time (it drives a hidden Chrome).

In Python (no browser):
  - the line is in the page, inside the preview, hidden from screen readers, with no words in it and no new line of
    words anywhere; it can't be pressed; the distance is 6 screen px; her styles are untouched (the line's are ours).
On the real page, in a hidden Chrome, with a real mouse, real keys and a finger:
  - the caption, a photo (Center and Small corner) and themselves in the corner each: dragged to within the
    distance of the preview's middle, left to right, the thing sits exactly on it and a thin line runs down the
    whole preview there; further away it lets go and the line goes; let go while snapped, what is SAVED is exactly
    0.5 (not nearly), and up and down is exactly what the drag gave, as before;
  - outside the distance nothing snaps, no line ever shows, and what is saved is the very number the page saved
    before this was built (worked out by the old sum, in the page, from the page's own numbers);
  - Option (Alt) held during the drag turns it off: no line, the old number saved; pressed and let go with the
    mouse still, the snap goes and comes back at once;
  - the round handles are as they were: sizing a photo or themselves through the middle never snaps, never shows
    the line;
  - a click without a drag changes nothing and shows no line;
  - no line is left behind: after letting go, after the Mac's own menu, after a pointer cancel, after the window
    loses the keyboard, after Escape and letting go;
  - the line is never saved (the record has the same fields as before) and never the thing under the pointer;
  - phone width, with a finger: the same snap, the same exact 0.5, no sideways scroll with the line showing;
  - no page error, nothing asked of the internet.

What it never does: touch the real ~/.studio (STUDIO_HOME is a scratch folder; the real one is listed before and
after), start the real transcriber, write into CapCut. The page server (port 9740 up) and the hidden Chrome are this
test's own and are stopped at the end.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
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
import talking_page_preview as tpp  # noqa: E402

PORT = 9740
KIT = tpp.KIT
WORDS = tpp.WORDS
SNAP = 6

HELPERS = r"""
// the line as a person sees it (null on a page that has none)
window.__line = function(){
  var e = document.getElementById('cline'), s = document.getElementById('screen').getBoundingClientRect();
  if (!e) return null;
  var r = e.getBoundingClientRect(), cs = getComputedStyle(e);
  return {on: cs.display !== 'none' && r.width > 0 && r.height > 0, off: (r.left + r.width / 2) - (s.left + s.width / 2),
          top: r.top - s.top, h: r.height, sh: s.height, w: r.width, hidden: e.getAttribute('aria-hidden'), text: e.textContent,
          kids: e.children.length, events: cs.pointerEvents, bg: cs.backgroundColor};
};
window.__lineOn = function(){ var l = window.__line(); return !!l && l.on; };
// the sum the page did before the snap was built: the start plus the px dragged, as a part of the screen, to 4 places
window.__old = function(start, px, tall){
  var s = document.getElementById('screen').getBoundingClientRect();
  return Math.round((start + px / (tall ? s.height : s.width)) * 10000) / 10000;
};
window.__mid = function(sel){
  var e = document.querySelector(sel), s = document.getElementById('screen').getBoundingClientRect(), r = e.getBoundingClientRect();
  return (r.left + r.width / 2 - s.left) / s.width;
};
window.__under = function(){
  var s = document.getElementById('screen').getBoundingClientRect(), e = document.elementFromPoint(s.left + s.width / 2, s.top + s.height * 0.3);
  return e ? e.id : null;
};
"""


# ---------- in Python ----------

def run_python(s):
    tp = s.tp
    import talking_css
    import talking_js_preview as pv
    html = ""
    try:
        import urllib.request
        html = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(s.url("/talking.html" + s.q(KIT)), timeout=20).read().decode("utf-8")
    except Exception as e:  # noqa: BLE001
        html = html or str(e)
    i, j = html.find("id='screen'"), html.find("class='controls'")
    case("the line is in the page, inside the preview, hidden from screen readers, with no words in it",
         0 < i < html.find("<i class='cline' id='cline' aria-hidden='true'></i>") < j and html.count("id='cline'") == 1, (i, j))
    case("no line of words was added for it: none of her words or ours speaks of a snap or of Option",
         not [k for k, v in list(tp.WORDS.items()) + [(k, v[0]) for k, v in tp.OUR_WORDS.items()]
              if isinstance(v, str) and any(x in v.lower() for x in ("snap", "option key", "centered"))])
    case("the line's styles are ours, not in her stylesheet; it can't be pressed and is drawn only when a drag says so",
         ".cline" not in talking_css.STYLE and ".screen .cline{" in talking_css.OUR_CSS and "pointer-events:none" in talking_css.OUR_CSS.split(".screen .cline{")[1].split("}")[0]
         and "display:none" in talking_css.OUR_CSS.split(".screen .cline{")[1].split("}")[0] and ".screen .cline.on{display:block}" in talking_css.OUR_CSS)
    code = pv.JS
    case("the distance is %d screen px, only a move ever snaps (never a round handle), and the line goes whenever a drag ends" % SNAP,
         "var SNAP_PX = %d;" % SNAP in code and "(d.kind === 'move' || d.kind === 'memove' || d.kind === 'cap') && !d.alt" in code
         and code.index("centerLine(false)") < code.index("if (cancel === true)"))
    case("what is saved is still only the spot: the line is no part of any save", "cline" not in code[code.index("T.save(function(){"):code.index("sc.addEventListener('pointerup'")])


# ---------- on the page ----------

def run_page(c, s):
    tpp.make(t, s)
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script(tpp.HELPERS)
    c.init_script(HELPERS)
    c.clear_errors()

    def rev():
        return c.js("window.Talk.rev")

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")
        c.wait_for("window.Talk.previewHeld() === null", 5)

    def save_js(body):
        c.js("Promise.resolve(window.Talk.save(%s)).then(function(){ return 1; })" % json.dumps(body))      # a save that changes nothing is fine
        c.wait_for("window.Talk.previewHeld() === null", 5)

    def rec():
        return s.rec(KIT) or {}

    def shot():
        return next((x for x in rec().get("shots") or [] if x["a"] == 1), None)

    def at(tm):
        return c.js("window.__at(%r)" % float(tm))

    def line():
        return c.js("window.__line()")

    def on():
        return c.js("window.__lineOn()")

    def old(start, px, tall=False):
        return c.js("window.__old(%r, %r, %s)" % (float(start), float(px), "true" if tall else "false"))

    def held():
        return c.js("window.Talk.previewHeld()")

    def paused():
        return c.js("document.getElementById('vid').paused")

    def grab(sel):
        """Press on the middle of something (whole px), the button left held. Returns where."""
        r = c.rect(sel)
        x, y = float(round(r["cx"])), float(round(r["cy"]))
        c.mouse_move(x, y)
        c.mouse_press()
        return x, y

    def to(p, dx, dy, **mods):
        c.mouse_move(p[0] + dx, p[1] + dy, **mods)

    def px_to_middle(sel):
        """How many px right of the preview's middle this thing's middle is."""
        return c.js("(window.__mid(%s) - 0.5) * document.getElementById('screen').getBoundingClientRect().width" % json.dumps(sel))

    def stretch(**more):
        x = {"a": 1, "b": 3, "ns": [1], "v": None, "from": 0, "spot": "full", "pos": None, "me": None}
        x.update(more)
        return x

    def open_it():
        t.open_page(c, s, KIT)
        c.wait_for("document.querySelectorAll('#script .sent').length === 3", 10, tell="document.getElementById('status').textContent")
        c.wait_for("document.getElementById('vid').readyState >= 1", 15)
        c.js("document.getElementById('screen').scrollIntoView({block: 'center'})")

    open_it()
    save_js({"shots": [], "cut": [], "zooms": [], "speeds": [], "captions": True, "cap_pos": None, "cap_size": 1})
    keys0 = set(rec().keys())
    mid = WORDS[2]["start"] + 0.01

    # ================= the caption =================
    at(WORDS[3]["start"] + 0.02)
    ln = line()
    case("before any drag: no line on the preview; it is hidden from screen readers, holds nothing and can't be pressed",
         ln is not None and not ln["on"] and ln["hidden"] == "true" and ln["text"] == "" and ln["kids"] == 0 and ln["events"] == "none", ln)
    undo0 = c.js("window.Talk.UNDO.length")
    was = rev()
    p = grab("#cap")
    to(p, 20, -10); to(p, 40, -30)
    far = [on(), held()["cap_pos"]["x"], old(0.5, 40)]
    to(p, SNAP - 2, -30)
    ln, h, m = line(), held(), c.js("window.__mid('#cap')")
    case("drag the caption away from the middle: no line, and it is where the hand has it (the sum as it always was)", far[0] is False and far[1] == far[2] and far[1] != 0.5, far)
    case("...back to within %d px of the middle: it sits exactly on it (0.5, not nearly), and the word on the preview is in the middle" % SNAP,
         h["cap_pos"]["x"] == 0.5 and abs(m - 0.5) < 0.002, (h, m))
    case("...and a thin line runs down the whole preview, right at its middle (blue, as in the designer)",
         bool(ln) and ln["on"] and abs(ln["off"]) <= 0.6 and abs(ln["top"]) <= 0.6 and abs(ln["h"] - ln["sh"]) <= 1 and 1 <= ln["w"] <= 3 and ln["bg"] == "rgb(31, 143, 255)", ln)
    case("...the line is never the thing under the pointer (a press there is still a press on the preview)", c.js("window.__under()") != "cline", c.js("window.__under()"))
    to(p, SNAP + 3, -30)
    away = [on(), held()["cap_pos"]["x"], old(0.5, SNAP + 3)]
    case("...moved on past the distance: it lets go and the line goes", away[0] is False and away[1] == away[2] and away[1] != 0.5, away)
    to(p, -(SNAP - 1), -30)
    left = [on(), held()["cap_pos"]["x"]]
    case("...and it snaps coming from the other side too", left == [True, 0.5], left)
    c.mouse_release()
    gone = on()
    moved(was)
    got = rec().get("cap_pos") or {}
    case("let go while snapped: the line goes at once, and what is SAVED is exactly centered: x 0.5 (up and down exactly as dragged), one Undo step, nothing played",
         gone is False and got.get("x") == 0.5 and got.get("y") == old(0.71, -30, True) and c.js("window.Talk.UNDO.length") == undo0 + 1 and paused() and not on(), (gone, got))
    # outside the distance, from the middle
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    seen = []
    for dx in (SNAP + 4, SNAP + 9, SNAP + 3):
        to(p, dx, 25)
        seen.append(on())
    c.mouse_release()
    moved(was)
    got = rec().get("cap_pos") or {}
    case("outside the distance nothing snaps: no line at any moment, and what is saved is the very number it was before (x and y)",
         seen == [False, False, False] and got == {"x": old(0.5, SNAP + 3), "y": old(0.71, 25, True)} and got["x"] != 0.5, (seen, got))
    # Option held
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    to(p, 2, 10, alt=True); to(p, 3, 25, alt=True)
    alt_seen = [on(), held()["cap_pos"]["x"]]
    c.mouse_release(alt=True)
    moved(was)
    got = rec().get("cap_pos") or {}
    case("Option (Alt on a PC) held during the drag turns the snap off: no line 3 px from the middle, and the old number is saved",
         alt_seen == [False, old(0.5, 3)] and got == {"x": old(0.5, 3), "y": old(0.71, 25, True)} and got["x"] != 0.5 and not on(), (alt_seen, got))
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    to(p, 2, 10); to(p, 3, 25)
    a0 = [on(), held()["cap_pos"]["x"]]
    c.key_down("Alt")
    a1 = [on(), held()["cap_pos"]["x"]]
    c.key_up("Alt")
    a2 = [on(), held()["cap_pos"]["x"]]
    c.mouse_release()
    moved(was)
    case("...Option pressed and let go with the mouse still: the snap goes and comes back at once, and it is saved as it was let go (centered)",
         a0 == [True, 0.5] and a1 == [False, old(0.5, 3)] and a2 == [True, 0.5] and (rec().get("cap_pos") or {}).get("x") == 0.5, (a0, a1, a2))
    # a click
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    to(p, 2, 0)
    tiny = on()
    c.mouse_release()
    time.sleep(0.4)
    case("a press on the caption that moves under 3 px is a click: no line, nothing saved", tiny is False and rev() == was and rec().get("cap_pos") is None and not on(), (tiny, rev(), was))
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)
    # the caption's round handle is as it was
    was = rev()
    p = grab("#capKnob")
    to(p, 3, 2); to(p, 4, 3)
    kn = on()
    c.mouse_release()
    moved(was)
    case("the caption's round handle is as it was: sizing shows no line and leaves the spot alone", kn is False and rec().get("cap_pos") is None and rec().get("cap_size") not in (None, 1), (kn, rec().get("cap_size")))
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)

    # no line left behind
    def cancel_by(what, js):
        was_ = rev()
        p_ = grab("#cap")
        to(p_, 2, 10); to(p_, 3, 25)
        before = on()
        c.js(js)
        after = [on(), bool(c.js("!!window.Talk.previewDrag()")), held()]
        c.mouse_release()
        time.sleep(0.4)
        case("no line left behind when %s: the drag is over, nothing is saved, the caption is back in the middle" % what,
             before is True and after == [False, False, None] and rev() == was_ and rec().get("cap_pos") is None and not on() and paused(), (before, after))
        c.mouse_move(5, 5)
    cancel_by("the Mac's own menu comes up", "document.dispatchEvent(new Event('contextmenu'))")
    cancel_by("the pointer is cancelled", "document.getElementById('screen').dispatchEvent(new PointerEvent('pointercancel', {bubbles: true}))")
    cancel_by("the window loses the keyboard", "window.dispatchEvent(new Event('blur'))")
    was = rev()
    p = grab("#cap")
    to(p, 2, 10); to(p, 3, 25)
    c.key("Escape")
    esc = [on(), bool(c.js("!!window.Talk.previewDrag()"))]
    c.mouse_release()
    gone = on()
    try:
        moved(was, 3)
    except Exception:  # noqa: BLE001
        pass
    case("Escape during a drag is as it was (the drag goes on, still snapped), and letting go leaves no line", esc == [True, True] and gone is False and not on(), (esc, gone))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    save_js({"cap_pos": None, "cap_size": 1, "captions": False})

    # ================= a photo =================
    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    c.wait_for("window.__pic().loaded", 10)
    was = rev()
    p = grab("#phFront")
    to(p, 2, 15); to(p, SNAP - 2, 30)
    ph = [on(), held()["pos"]["x"], abs(c.js("window.__mid('#phFront')") - 0.5) < 0.002, line()["off"]]
    c.mouse_release()
    moved(was)
    got = shot()["pos"] or {}
    case("a photo in Center, dragged within the distance: exactly centered with the line down the preview; saved x is 0.5, up and down as dragged, the same size",
         ph[0] is True and ph[1] == 0.5 and ph[2] and abs(ph[3]) <= 0.6 and got == {"x": 0.5, "y": old(0.44, 30, True), "w": 0.704} and not on(), (ph, got))
    was = rev()
    p = grab("#phFront")
    seen = []
    for dx in (-10, -25, -40):
        to(p, dx, 0)
        seen.append(on())
    c.mouse_release()
    moved(was)
    got = shot()["pos"] or {}
    case("...dragged off to the side: no line, and the saved number is the one it always was", seen == [False, False, False] and got.get("x") == old(0.5, -40) and got["x"] != 0.5, (seen, got))
    off = px_to_middle("#phFront")
    was = rev()
    p = grab("#phFront")
    to(p, 10, 0); to(p, round(-off) + 2, 0)
    back = [on(), held()["pos"]["x"]]
    c.mouse_release()
    moved(was)
    case("...and brought back from there to within the distance: it snaps, and is saved exactly centered (0.5), however it got there",
         back == [True, 0.5] and shot()["pos"]["x"] == 0.5 and not on(), (off, back, shot()["pos"]))
    was = rev()
    p = grab("#phFront")
    to(p, 2, 0, alt=True); to(p, 4, 0, alt=True)
    al = [on(), held()["pos"]["x"]]
    c.mouse_release(alt=True)
    moved(was)
    case("...with Option held: no snap, no line, the old number", al == [False, old(0.5, 4)] and shot()["pos"]["x"] == old(0.5, 4) and not on(), (al, shot()["pos"]))
    # its round handle, through the middle
    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    was = rev()
    p = grab("#phKnob")
    to(p, 3, 0); to(p, 5, 0)
    kn = [on(), held()["pos"]]
    c.mouse_release()
    moved(was)
    got = shot()["pos"]
    wide = old(0.704, 5)
    case("a photo's round handle is as it was: its middle a few px from the preview's does not snap and shows no line (the top left corner stays put)",
         kn[0] is False and got["w"] == wide and got["x"] != 0.5 and abs(got["x"] - (0.5 - 0.352 + wide / 2)) < 0.0002 and not on(), (kn, got))
    # Small corner
    save_js({"shots": [stretch(spot="corner")]})
    at(mid)
    off = px_to_middle("#phFront")
    was = rev()
    p = grab("#phFront")
    to(p, -20, 5); to(p, round(-off) - 3, 10)
    co = [on(), held()["pos"]["x"]]
    c.mouse_release()
    moved(was)
    case("a photo in Small corner dragged to the middle snaps too: saved x exactly 0.5, the same size", co == [True, 0.5] and shot()["pos"]["x"] == 0.5 and shot()["pos"]["w"] == 0.352 and not on(), (off, co, shot()["pos"]))
    save_js({"shots": [stretch()]})
    at(mid)
    was = rev()
    p = grab("#phFront")
    to(p, 2, 10); to(p, 3, 20)
    full = on()
    c.mouse_release()
    time.sleep(0.4)
    case("a photo that is Full screen still can't be moved: no line, nothing saved", full is False and rev() == was and not on(), full)
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)

    # ================= themselves in the corner =================
    save_js({"shots": [stretch(spot="pip")]})
    at(mid)
    me = c.js("window.Talk.ME")
    off = px_to_middle("#vid")
    was = rev()
    p = grab("#vid")
    to(p, 30, -20)
    m0 = [on(), held()["me"]["x"], old(me["x"], 30)]
    to(p, round(-off) + 3, -40)
    m1 = [on(), held()["me"]["x"], abs(c.js("window.__mid('#vid')") - 0.5) < 0.002, line()["off"]]
    c.mouse_release()
    moved(was)
    got = shot()
    case("themselves in the corner: away from the middle no line and the old sum; dragged to it, exactly centered with the line; saved x is 0.5, the same size, the photo not moved",
         m0[0] is False and m0[1] == m0[2] and m1[0] is True and m1[1] == 0.5 and m1[2] and abs(m1[3]) <= 0.6
         and got["me"]["x"] == 0.5 and got["me"]["w"] == 0.36 and got["pos"] is None and not on(), (off, m0, m1, got))
    was = rev()
    p = grab("#vid")
    to(p, 2, 0, alt=True); to(p, 5, 0, alt=True)
    al = on()
    c.mouse_release(alt=True)
    moved(was)
    case("...with Option held: no snap, no line, the old number", al is False and shot()["me"]["x"] == old(0.5, 5) and not on(), shot()["me"])
    save_js({"shots": [stretch(spot="pip", me={"x": 0.5, "y": 0.7, "w": 0.36})]})
    at(mid)
    was = rev()
    p = grab("#meKnob")
    to(p, 3, 0); to(p, 4, 0)
    kn = on()
    c.mouse_release()
    moved(was)
    got = shot()["me"]
    case("their round handle is as it was: sizing through the middle does not snap and shows no line", kn is False and got["x"] != 0.5 and got["w"] == old(0.36, 4) and not on(), (kn, got))

    # ================= set a little off the middle on purpose, then moved straight up or down =================
    scr = c.js("(function(){ var r = document.getElementById('screen').getBoundingClientRect(); return [r.width, r.height]; })()")
    offx = round(0.5 + 4.0 / scr[0], 4)                      # 4 px right of the middle: inside the distance, not centered
    save_js({"shots": [], "captions": True, "cap_pos": {"x": offx, "y": 0.71}, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    seen = []
    for dx, dy in ((0, 8), (1, 14), (-2, 20), (0, 20)):
        to(p, dx, dy)
        seen.append([on(), held()["cap_pos"]["x"]])
    c.mouse_release()
    moved(was)
    got = rec().get("cap_pos") or {}
    case("a caption set 4 px off the middle and dragged straight down (the hand wobbling a px or two sideways) keeps its spot: no line at any moment, "
         "and the saved left-to-right number is the one it had, not 0.5",
         [x[0] for x in seen] == [False] * 4 and seen[2][1] == old(offx, -2) and got == {"x": offx, "y": old(0.71, 20, True)} and got["x"] != 0.5, (offx, seen, got))
    was = rev()
    p = grab("#cap")
    to(p, 5, 6)
    s0 = [on(), held()["cap_pos"]["x"]]
    to(p, -3, 10)
    s1 = [on(), held()["cap_pos"]["x"]]
    c.mouse_release()
    moved(was)
    case("...the same caption dragged sideways first (5 px), then to within the distance: now it snaps, and is saved exactly centered",
         s0 == [False, old(offx, 5)] and s1 == [True, 0.5] and (rec().get("cap_pos") or {}).get("x") == 0.5 and not on(), (s0, s1, rec().get("cap_pos")))
    save_js({"captions": False, "cap_pos": None, "shots": [stretch(spot="center", pos={"x": offx, "y": 0.44, "w": 0.704})]})
    at(mid)
    c.wait_for("window.__pic().loaded", 10)
    was = rev()
    p = grab("#phFront")
    to(p, 0, 10); to(p, 1, 22)
    pd = [on(), held()["pos"]["x"]]
    c.mouse_release()
    moved(was)
    case("...and a photo set 4 px off the middle, dragged straight down, keeps its spot too: no line, the old number",
         pd == [False, old(offx, 1)] and shot()["pos"]["x"] == old(offx, 1) and shot()["pos"]["x"] != 0.5 and not on(), (pd, shot()["pos"]))
    save_js({"shots": [stretch(spot="pip", me={"x": offx, "y": 0.7, "w": 0.36})]})
    at(mid)
    was = rev()
    p = grab("#vid")
    to(p, 0, -10); to(p, -1, -22)
    md = [on(), held()["me"]["x"]]
    c.mouse_release()
    moved(was)
    case("...and so does themselves in the corner", md == [False, old(offx, -1)] and shot()["me"]["x"] == old(offx, -1) and shot()["me"]["x"] != 0.5 and not on(), (md, shot()["me"]))

    # ================= left to right only: nothing snaps up and down =================
    def to_vertical_middle(start_y):
        """Whole px to drag down (or up) so the thing's middle ends 2 px below the preview's middle, top to bottom."""
        return int(round((0.5 - start_y) * scr[1])) + 2

    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    c.wait_for("window.__pic().loaded", 10)
    dy = to_vertical_middle(0.44)
    was = rev()
    p = grab("#phFront")
    to(p, -20, dy // 2); to(p, -40, dy)
    v0 = [on(), held()["pos"]["y"]]
    to(p, 2, dy)
    v1 = [on(), held()["pos"]["x"], held()["pos"]["y"]]
    c.mouse_release()
    moved(was)
    got = shot()["pos"]
    case("a photo dragged to 2 px from the preview's middle TOP TO BOTTOM, off to the side: nothing snaps up and down and no line shows; "
         "brought to the middle left to right there, only x is centered and y is still the old sum",
         v0 == [False, old(0.44, dy, True)] and v0[1] != 0.5 and abs(v0[1] - 0.5) * scr[1] < 3 and v1 == [True, 0.5, old(0.44, dy, True)]
         and got["x"] == 0.5 and got["y"] == old(0.44, dy, True) and got["y"] != 0.5, (dy, v0, v1, got))
    save_js({"shots": [stretch(spot="pip", me={"x": 0.3, "y": 0.44, "w": 0.36})]})
    at(mid)
    was = rev()
    p = grab("#vid")
    to(p, 0, dy // 2); to(p, 0, dy)
    v0 = [on(), held()["me"]["y"]]
    c.mouse_release()
    moved(was)
    got = shot()["me"]
    case("...themselves in the corner likewise: 2 px from the middle top to bottom, y is the old sum, never 0.5, and no line",
         v0 == [False, old(0.44, dy, True)] and got == {"x": 0.3, "y": old(0.44, dy, True), "w": 0.36} and got["y"] != 0.5 and abs(got["y"] - 0.5) * scr[1] < 3, (v0, got))
    save_js({"shots": [], "captions": True, "cap_pos": {"x": 0.3, "y": 0.44}, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    to(p, 0, dy // 2); to(p, 0, dy)
    v0 = [on(), held()["cap_pos"]["y"]]
    c.mouse_release()
    moved(was)
    got = rec().get("cap_pos") or {}
    case("...and the caption likewise", v0 == [False, old(0.44, dy, True)] and got == {"x": 0.3, "y": old(0.44, dy, True)} and got["y"] != 0.5, (v0, got))
    # exactly on the edge of the distance counts, from either side
    save_js({"cap_pos": None, "cap_size": 1})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    p = grab("#cap")
    to(p, 20, 12)
    edge = []
    for dx in (SNAP + 1, SNAP, -(SNAP + 1), -SNAP):
        to(p, dx, 12)
        edge.append(on())
    c.mouse_release()
    moved(was)
    case("exactly %d px from the middle counts as within the distance on BOTH sides (%d px does not)" % (SNAP, SNAP + 1), edge == [False, True, False, True], edge)

    # ================= never saved, nothing broken =================
    save_js({"shots": [], "captions": True, "cap_pos": None, "cap_size": 1})
    blob = json.dumps(rec())
    case("the line is never saved: nothing in the record speaks of a line or a snap, and no field is new to the record's own list",
         "cline" not in blob and "snap" not in blob and "alt" not in [k for k in rec()] and set(rec().keys()) - keys0 <= {"cap_pos", "cap_size", "shots", "from", "photos"}, sorted(set(rec().keys()) - keys0))
    case("no browser pop-up, no page error, no part of the page failed, nothing asked of the internet",
         c.js("window.__dialogs") == 0 and not c.page_errors() and c.js("window.Talk.faults.length") == 0 and not c.outside_requests(), (c.page_errors()[:3], c.outside_requests()[:3]))

    # ================= phone width, a finger =================
    def settle(cond):
        try:
            c.wait_for(cond, 3)
        except Exception:  # noqa: BLE001
            pass

    c.phone()
    try:
        open_it()
        at(WORDS[3]["start"] + 0.02)
        r = c.rect("#cap")
        x, y = float(round(r["cx"])), float(round(r["cy"]))
        was = rev()
        c._touch("touchStart", [(x, y)])
        c._touch("touchMove", [(x + 15, y - 10)])
        c._touch("touchMove", [(x + 30, y - 30)])
        settle("(window.Talk.previewHeld() || {cap_pos: {}}).cap_pos.x === window.__old(0.5, 30, false)")      # a finger's moves reach the page a frame later
        f0 = [on(), (held() or {}).get("cap_pos", {}).get("x"), old(0.5, 30)]
        c._touch("touchMove", [(x + 3, y - 30)])
        settle("window.__lineOn()")
        ln = line()
        f1 = [ln["on"], (held() or {}).get("cap_pos", {}).get("x"), abs(ln["off"]) <= 0.6, abs(ln["h"] - ln["sh"]) <= 1]
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
        c._touch("touchEnd", [])
        gone = on()
        moved(was)
        got = rec().get("cap_pos") or {}
        case("phone width, a finger on the caption: away from the middle no line; within the distance it snaps with the line down the whole preview, and no sideways scroll",
             f0[0] is False and f0[1] == f0[2] and f1 == [True, 0.5, True, True] and wide[0] <= 0 and wide[1] == 390, (f0, f1, wide))
        case("...the finger lifted: the line goes, and what is saved is exactly centered (0.5)", gone is False and got.get("x") == 0.5 and got.get("y") == old(0.71, -30, True) and not on(), (gone, got))
        save_js({"cap_pos": None, "captions": False, "shots": [stretch(spot="center")]})
        at(mid)
        c.wait_for("window.__pic().loaded", 10)
        r = c.rect("#phFront")
        x, y = float(round(r["cx"])), float(round(r["cy"]))
        was = rev()
        c._touch("touchStart", [(x, y)])
        c._touch("touchMove", [(x + 8, y + 10)])
        c._touch("touchMove", [(x - 4, y + 20)])
        settle("window.__lineOn()")
        f1 = [on(), (held() or {}).get("pos", {}).get("x")]
        c._touch("touchEnd", [])
        moved(was)
        case("...a finger on a photo: the same snap, saved exactly centered", f1 == [True, 0.5] and shot()["pos"]["x"] == 0.5 and not on(), (f1, shot()))
        case("...and no page error at phone width", not c.page_errors(), c.page_errors()[:3])
    finally:
        c.desktop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="talking-snap-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.make()
    try:
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        tpp.make(t, s)
        group("the centered line, in Python and by request", run_python, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the centered line on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1100)) as c:
                group("the centered line on the page", run_page, c, s)
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
