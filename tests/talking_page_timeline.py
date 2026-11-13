#!/usr/bin/env python3
"""The `timeline` part of tests/talking_page_check.py (sub-stage C4 of the talking reel page): the dock across the
bottom, Undo and Redo, the keys, and Make it in CapCut. Not run by itself:

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py --only timeline

talking_page_check.py hands this file itself (`t`: its Setup, its helpers), its Setup (`s`) and, for the page, its
hidden Chrome (`c`). What is checked, in the plan's own order (docs/handoff-v24-build-2026-11-12.md, Stage C, C4):
the dock sized into --dock; the scale and the ruler's steps, number for number; the words under the clips past 55
px a second; picking a clip and a photo block, the round x, Delete clip and Delete photo, the keys; a clip's end
dragged in (cuts) and out (brings back), with her three toasts; a photo block's end (a video keeps its video and
its start point); Split and its three toasts; the Speed and Zoom menus; the timeline's own zoom (slider, buttons,
Ctrl or Cmd with the wheel around the mouse, a plain wheel sideways); the line followed while playing; Undo and
Redo by button and by key, to 60 steps, emptied when the chat changes things, and an Undo that names a Footage
video since gone; and Make it in CapCut from the press to her result box, with Undo still live afterwards. And
ours: nothing is held across a refresh, a drag let go unseen saves nothing, the look waits during a drag, text as
text, no path, no pop-up, nothing asked of the internet, phone width. From C4's review: a sped-up clip (its words
under it, its end dragged out by distance x speed), a not-ready state with an end in the hand, a block's end
dropped where it was (no save), a save sent and answered before the make, a newer make than the one followed, a
make that can no longer be seen (the button back, plain words), and the make-only answer of /talking-state.

The records are seeded here (TR.put_words), so nothing is transcribed. The talking video and the one Footage video
are tests/fixtures/loud-tone-3s.mp4 (3 seconds, self-made). A second kit has a "long talk" of 60 seconds of words
over that same 3-second file: it is only ever measured (scale, ruler, zoom), never played. Nothing here asks the
Mac to make a small copy or a still, and the page never asks for the Footage list. Make it in CapCut writes into
the test's own pretend CapCut folder (ASSISTANT_TEST_TALKING_STORE); CapCut is never started or asked after.
"""
import json
import os
import re
import shutil
import time

import talking_page_preview as tpp

KIT = "2026-09-27 Zoë's timeline"
SHORT = KIT[11:]
LONG = "2026-09-28 Long timeline"
TALK = "talk.mp4"
FOOT = "bts.mp4"
SAID, WORDS, SENTS = tpp.SAID, tpp.WORDS, tpp.SENTS      # 17 words in three sentences: 0-5, 6-12, 13-16
PHOTOS = 6
PAD = 12


def _long_words():
    """Twenty sentences of five words over 60 seconds; the first word is a very short one at the very start."""
    out = []
    for k in range(20):
        for j in range(5):
            st = k * 3.0 + j * 0.4
            w = "w%d%s" % (k * 5 + j, "." if j == 4 else "")
            out.append({"w": w, "start": round(st, 3), "end": round(st + 0.3, 3), "conf": 0.9})
    out[0]["end"] = 0.02
    return out


LONG_WORDS = _long_words()

def menu_pick(c, menu_id, nth=None, attr=None, value=None):
    """Choose from the Speed or the Zoom menu as a hand does: a press on its button, then on the item (the nth, or
    the one whose data-<attr> is value). What was a press on that chip."""
    c.click("#%sBtn" % menu_id, check=False)
    c.wait_for("window.Talk.tl().menu === %r" % menu_id, 5)
    if nth is not None:
        c.click("#%s [role=menuitemradio]" % menu_id, nth=nth, check=False)
    else:
        c.click('#%s [role=menuitemradio][data-%s="%s"]' % (menu_id, attr, value), check=False)
    c.wait_for("window.Talk.tl().menu === null", 5)


HELPERS = r"""
window.__wheels = [];
window.addEventListener('wheel', function(e){ window.__wheels.push([e.deltaY, e.deltaX, e.defaultPrevented]); }, true);
window.__at = function(t){ document.getElementById('vid').currentTime = t; window.Talk.frame(); return document.getElementById('vid').currentTime; };
window.__tl = function(){
  var T = window.Talk, tr = document.getElementById('tlTrack'), r = tr.getBoundingClientRect(), s = T.tl();
  return {pps: s.pps, selw: s.selw, sel: s.sel, drag: s.drag, making: s.making, left: r.left, top: r.top, w: tr.clientWidth, scroll: tr.scrollLeft,
          inner: parseFloat(document.getElementById('tlInner').style.width), total: T.total(), value: +document.getElementById('tlScale').value,
          time: document.getElementById('tlTime').textContent, head: parseFloat(document.getElementById('tlHead').style.left),
          hint: document.getElementById('tlHint').textContent, wordsOff: document.getElementById('tlWords').classList.contains('off'),
          nwords: document.querySelectorAll('#tlWords .tl-w').length,
          ticks: Array.from(document.querySelectorAll('#tlRuler span')).map(function(e){ return [e.textContent, parseFloat(e.style.left)]; })};
};
window.__tlx = function(R){ var tr = document.getElementById('tlTrack'); return tr.getBoundingClientRect().left - tr.scrollLeft + 12 + R * window.Talk.tl().pps; };
window.__clips = function(){
  return Array.from(document.querySelectorAll('#tlClips .tl-clip')).map(function(e){
    return {w: +e.getAttribute('data-w'), left: parseFloat(e.style.left), width: parseFloat(e.style.width), on: e.classList.contains('on'),
            fast: e.classList.contains('fast'), x: e.querySelector('.tl-x') ? e.querySelector('.tl-x').title : null,
            bd: Array.from(e.querySelectorAll('.bd')).map(function(b){ return b.textContent; }), text: e.querySelector('span').textContent, title: e.title,
            kids: e.querySelector('span').children.length, bg: getComputedStyle(e).backgroundImage};
  });
};
window.__blocks = function(){
  return Array.from(document.querySelectorAll('#tlPhotos .tl-ph')).map(function(e){
    return {a: +e.getAttribute('data-a'), left: parseFloat(e.style.left), width: parseFloat(e.style.width), on: e.classList.contains('on'),
            x: e.querySelector('.tl-x') ? e.querySelector('.tl-x').title : null, imgs: e.querySelectorAll('img').length,
            label: e.querySelector('span').textContent, text: e.textContent, title: e.title, kids: e.querySelector('span').children.length};
  });
};
window.__tools = function(){
  // Speed and Zoom are a small menu each (Dustin, Nov 13). One row per item of the list, in the shape the chips had:
  // [its words, greyed (the menu's button is off), checked]; and the button itself: {label, value, off, on, open}.
  var g = function(id){
    var b = document.getElementById(id + 'Btn');
    return Array.from(document.querySelectorAll('#' + id + ' [role=menuitemradio]')).map(function(d){ return [d.querySelector('.t').textContent, b.disabled, d.getAttribute('aria-checked') === 'true']; });
  };
  var mb = function(id){
    var b = document.getElementById(id + 'Btn');
    return {label: b.querySelector('.nm').textContent, value: b.querySelector('.val').textContent, off: b.disabled, on: b.classList.contains('on'),
            open: b.getAttribute('aria-expanded') === 'true' && !document.getElementById(id + 'List').hidden};
  };
  var cut = document.getElementById('tlCut');
  return {speed: g('tlSpeed'), zoom: g('tlZoom'), speedBtn: mb('tlSpeed'), zoomBtn: mb('tlZoom'), cut: [cut.textContent, cut.disabled],
          undo: document.getElementById('tlUndo').disabled, redo: document.getElementById('tlRedo').disabled,
          n: [window.Talk.UNDO.length, window.Talk.REDO.length]};
};
window.__picked = function(){ return Array.from(document.querySelectorAll('#script .words span.picked')).map(function(e){ return +e.getAttribute('data-i'); }); };
window.__pickWords = function(a, b){
  var T = window.Talk, s = window.getSelection(), r = document.createRange();
  var x = T.wordEl(a).lastChild, y = T.wordEl(b).lastChild;
  r.setStart(x, 0); r.setEnd(y, y.nodeValue.length);
  s.removeAllRanges(); s.addRange(r);
};
window.__result = function(){
  var r = document.getElementById('result');
  return {h2: r.querySelector('h2') ? r.querySelector('h2').textContent : null, ps: Array.from(r.querySelectorAll('p')).map(function(p){ return [p.className, p.textContent]; }),
          kids: r.querySelectorAll('p *').length, btn: [document.getElementById('makeBtn').textContent, document.getElementById('makeBtn').disabled]};
};
"""


def make(t, s):
    kit = s.kit(KIT)
    if (kit / ".kit" / "talking.json").exists():
        return kit
    kit = s.make_kit(KIT, photos=PHOTOS)
    key = s.add_talk(kit, TALK)
    s.TR.put_words(kit, TALK, key, WORDS, info={"dur": 3.0})
    (kit / "Footage").mkdir(exist_ok=True)
    f = kit / "Footage" / FOOT
    shutil.copyfile(str(t.FIXTURE), str(f))
    old = time.time() - 7200
    os.utime(str(f), (old, old))                       # not "still being copied in"
    lk = s.make_kit(LONG, photos=2)
    key = s.add_talk(lk, TALK)
    s.TR.put_words(lk, TALK, key, LONG_WORDS, info={"dur": 60.0})
    return kit


def near(a, b, tol=0.6):
    return a is not None and b is not None and abs(a - b) <= tol


def wait_make(s, kit, seconds=60):
    def over():
        m = (s.state(kit) or {}).get("make")
        return m if m and m.get("state") in ("done", "problem") else None
    return t_wait(over, seconds)


def t_wait(cond, seconds):
    end = time.time() + seconds
    while True:
        v = cond()
        if v or time.time() > end:
            return v
        time.sleep(0.1)


def run_requests(t, s):
    """By request and by reading the files, no browser."""
    case = t.case
    make(t, s)
    import talking_js_timeline
    import talking_js_core
    import talking_make
    import talking
    TR, tp = s.TR, s.tp
    js = talking_js_timeline.JS
    code = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)
    case("talking_js_timeline.py is one string of JavaScript and nothing else", [n for n in dir(talking_js_timeline) if not n.startswith("_")] == ["JS"])
    case("the timeline's part is on the page, last, after the parts it stands on", tp.JS_PARTS[-1] is js and len(tp.JS_PARTS) == 6)
    case("no pop-up and no HTML from a string in the timeline's part",
         not re.search(r"\b(confirm|alert|prompt)\s*\(|innerHTML|outerHTML|insertAdjacentHTML|document\.write", js))
    case("her pitfall: the timeline's part uses neither of the two kept class names, and never finds a video as \"video\"",
         not re.search(r"['\"](bar|sel)['\"]|['\"][^'\"]*\.(bar|sel)\b", code) and "querySelector('video')" not in code and "getElementsByTagName" not in code)
    case("the Footage list is never asked for from the timeline (only the video picker asks)", "/reel-footage" not in code and "/reel-video" not in code)
    want = ("PAD = 12", "WORDS_AT = 55", "MOST = 240", "ROOM = 200", "TICK = 56", "STEPS = [0.25, 0.5, 1, 2, 5, 10, 15, 30, 60]", "SPEEDS = [1, 1.25, 1.5, 2]",
            "CLICK_PX = 3", "NUDGE = 15", "WHEEL = 0.4", "CLIP_MIN = 3", "PHOTO_MIN = 18", "FOLLOW_L = 30", "FOLLOW_R = 60", "THUMBS = 10",
            "track.clientWidth * 0.25", "Math.pow(max / fit, +$('tlScale').value / 100)")
    case("her numbers, each written once in the timeline's part (%d)" % len(want), not [w for w in want if w not in code], [w for w in want if w not in code])
    case("...and the speeds offered are the ones the engine takes", list(talking.SPEEDS) == [1.0, 1.25, 1.5, 2.0])
    case("her pitfall: a photo block is held by its start word and a clip by its first word, never the stretch or the piece itself; each is looked up again when the save's turn comes",
         "a: +ph.getAttribute('data-a')" in code and "w0: +clip.getAttribute('data-w')" in code and "var c = T.findShot(d.a)" in code and "pieceOf(d.w0)" in code)
    case("her fault, fixed: a block's end dragged on the timeline carries a video and its start point (hers kept only ns, spot, pos, me)",
         "keep = {ns: c.ns, v: c.v, from: c.from, spot: c.spot, pos: c.pos, me: c.me}" in code)
    case("her fault, fixed: Undo, Redo and Delete do nothing behind either picker (hers looked at the photo picker only)", "T.pickerOpen && T.pickerOpen()" in code)
    case("the keys are hers: Cmd or Ctrl with Z (Shift: Redo) and with Y; Delete and Backspace",
         "k === 'z'" in code and "k === 'y'" in code and "e.key === 'Delete' || e.key === 'Backspace'" in code and "e.metaKey || e.ctrlKey" in code)
    case("Undo keeps 60 steps (hers), written once and handed to the page", tp.UNDO_STEPS == 60 and "DATA.undoSteps" in talking_js_core.JS and "T.UNDO.shift()" in talking_js_core.JS)
    page = tp.page_html(KIT)
    w = tp.page_words()
    q = "Ctrl" if t.WINDOWS else "⌘"
    case("the Undo and Redo buttons start grey, with the tooltips for this computer's keys",
         re.search(r"id='tlUndo' type='button' disabled title='Undo \((⌘|Ctrl\+)Z\)'>↶ Undo<", page) and re.search(r"id='tlRedo' type='button' disabled title='Redo \((⇧⌘|Ctrl\+Shift\+)Z\)'>↷ Redo<", page)
         and q in w["undo_title"], w["undo_title"])
    case("the lines the maker prints into her result box are the very ones talking_page holds as hers (\"quit\" is a PC's \"close\")",
         w["made_listed"] == talking_make.MADE_LISTED and w["made_open"] == talking_make.MADE_OPEN and tp.OUR_WORDS["made_only"][0] == talking_make.MADE_ONLY,
         (w["made_listed"], w["made_open"]))

    # ---- /talking-make, by request
    st = s.state(KIT)
    code_, j = s.post("/talking-make", {"kit": KIT, "dry": "yes"})
    code2, j2 = s.post("/talking-make", {"kit": KIT, "dry": 1})
    case("POST /talking-make takes `dry` only as true or false", code_ == 400 and code2 == 400 and j.get("words") == tp.NOT_UNDERSTOOD and s.state(KIT)["make"] is None, (code_, code2))
    code_, j = s.post("/talking-make", {"kit": KIT, "dry": True})
    again, j_again = s.post("/talking-make", {"kit": KIT, "dry": True})
    m = wait_make(s, KIT)
    case("a dry make by request: a job is handed back, and pressed again at once it is her \"still working\" line, never two at once",
         code_ == 200 and j.get("ok") and j["job"]["state"] in ("queued", "running", "done") and set(j["job"]) == {"id", "state", "dry", "project", "words", "problem"}
         and (again == 409 and j_again.get("words") == TR.JOB_WORDS["still_working"] or again == 200), (code_, j, again, j_again))
    if again == 200:
        time.sleep(0.5)
        m = wait_make(s, KIT)
    store = s.work / "capcut"
    case("...it ends done with the two dry lines for the result box, no project, and nothing written to CapCut or the record",
         bool(m) and m["state"] == "done" and m["dry"] is True and m["project"] is None and len(m["words"]) == 2 and m["words"][1] == talking_make.DRY_DONE
         and m["words"][0].startswith("Plan: 3 pieces of talking") and not os.listdir(str(store)) and "made" not in (s.rec(KIT) or {}), m)
    now = s.state(KIT)
    case("...and the record's counter did not move for it (the page's next save and its Undo are as they were)", now["rev"] == st["rev"], (st["rev"], now["rev"]))
    blob = json.dumps(now.get("make"), ensure_ascii=False)
    case("...nothing the page is handed about a make holds a path or a process number", str(s.work) not in blob and "pid" not in blob and "/private" not in blob)
    short = s.state(KIT, "&rev=%d&mark=%s" % (now["rev"], now["mark"]))
    case("the short answer (nothing moved) still says how the make stands, so the 3-second look sees a make begun elsewhere",
         "rec" not in short and (short.get("make") or {}).get("state") == "done", sorted(short))
    only = s.state(KIT, "&only=make")
    stale = s.state(KIT, "&only=make&rev=0&mark=000000000000")
    code_, _j, _raw, _h = s.http("GET", "/talking-state" + s.q(KIT) + "&only=other")
    case("asked for the make only (what the page asks once a second while one is at work), the answer is {ok, make} and nothing else: never the whole state, whatever counter the page holds",
         set(only) == {"ok", "make"} and only["make"] == now["make"] and set(stale) == {"ok", "make"} and "/talking-state?' + Q + '&only=make'" in code
         and "&rev='" not in code, (sorted(only), sorted(stale)))
    case("...and any other `only` is refused in plain words", code_ == 400 and _j.get("words") == tp.NOT_UNDERSTOOD, code_)
    lst = s.state(LONG)
    case("the test's long talk: 20 sentences, 20 clips, 100 words over a minute",
         len(lst["pieces"]) == 20 and len(lst["rec"]["sentences"]) == 20 and len(lst["rec"]["words"]) == 100, (len(lst["pieces"]), len(lst["rec"]["sentences"])))


def run_page(t, c, s):
    case, skip, wait_for = t.case, t.skip, t.wait_for
    W = s.tp.page_words()
    TR = s.TR
    kit = make(t, s)
    import talking_make
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script("(function(){ var real = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function(o){"
                  " return real.call(this, (o && typeof o === 'object') ? Object.assign({}, o, {behavior: 'auto'}) : o); }; })();")
    c.init_script(HELPERS)
    c.clear_errors()

    def rev():
        return c.js("window.Talk.rev")

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")

    def save_js(body):
        was = rev()
        c.js("window.Talk.save(%s)" % json.dumps(body))
        moved(was)

    def rec(name=KIT):
        return s.rec(name) or {}

    def shot(a):
        return next((x for x in rec().get("shots") or [] if x["a"] == a), None)

    def toast():
        return t.toast(c)

    def P():
        return c.js("window.Talk.P()")

    def tl():
        return c.js("window.__tl()")

    def clips():
        return c.js("window.__clips()")

    def blocks():
        return c.js("window.__blocks()")

    def tools():
        return c.js("window.__tools()")

    def tlx(R):
        return c.js("window.__tlx(%r)" % float(R))

    def at(tm):
        return c.js("window.__at(%r)" % float(tm))

    def now_R():
        return c.js("window.Talk.reelAt(document.getElementById('vid').currentTime)")

    def clip_sel(w0):
        return '#tlClips .tl-clip[data-w="%d"]' % w0

    def block_sel(a):
        return '#tlPhotos .tl-ph[data-a="%d"]' % a

    def press(sel, fx=0.5):
        """A press and release on the track, at a share of something's width."""
        r = c.rect(sel)
        x, y = r["x"] + r["w"] * fx, r["cy"]
        c.mouse_move(x, y)
        c.mouse_press()
        c.mouse_release()
        return x

    def drag_end(sel, to_x, release=True, steps=6):
        """Take hold of an end (its handle's middle) and drag it sideways to the window's x `to_x`."""
        r = c.rect(sel)
        c.drag((r["cx"], r["cy"]), (to_x, r["cy"]), steps=steps, release=release, check=False)
        return r

    def rs(p, i):
        """Where word i starts on the reel, inside piece p (hers)."""
        return p["at"] + (max(WORDS[i]["start"], p["from"]) - p["from"]) / p["speed"]

    def re_(p, i):
        return p["at"] + (min(WORDS[i]["end"], p["to"]) - p["from"]) / p["speed"]

    def piece_of(w0):
        return next(p for p in P() if p["words"][0] == w0)

    def open_it(name=KIT, sents=3):
        t.open_page(c, s, name)
        c.wait_for("document.querySelectorAll('#script .sent').length === %d" % sents, 10, tell="document.getElementById('status').textContent")
        c.wait_for("document.getElementById('vid').readyState >= 1", 15)
        c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length > 0", 10)

    open_it()
    wait_for(lambda: all(p["have"] for p in s.state(KIT)["photos"]), 60)
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.PHOTOS.length === %d && window.Talk.PHOTOS.every(function(p){ return p.have; })" % PHOTOS, 10)

    # ================= as it opens: the dock, the scale, the clips =================
    dock = c.js("[document.getElementById('dock').offsetHeight, getComputedStyle(document.documentElement).getPropertyValue('--dock').trim(), parseInt(document.body.style.paddingBottom),"
                " document.getElementById('tl').hidden, getComputedStyle(document.getElementById('dock')).position]")
    case("the dock is fixed across the bottom, its height is in --dock and the page leaves that room (and 24 px) under itself",
         dock[1] == "%dpx" % dock[0] and dock[2] == dock[0] + 24 and dock[3] is False and dock[4] == "fixed" and dock[0] > 150, dock)
    g, ps = tl(), P()
    fit = max(200, g["w"] - 2 * PAD) / max(g["total"], 1)
    case("the scale, hers: with the slider at 0 the whole reel fits (width - 24) / length, 12 px of padding each side",
         g["value"] == 0 and near(g["pps"], max(fit, 0), 0.01) and near(g["inner"], g["total"] * g["pps"] + 24, 0.5) and len(ps) == 3, (g["pps"], fit, g["inner"]))
    cl_ = clips()
    case("a clip for each piece of talking, where it plays on the reel: left = 12 + at x scale, width = length x scale - 2",
         [x["w"] for x in cl_] == [p["words"][0] for p in ps] and all(near(x["left"], PAD + p["at"] * g["pps"], 0.5) and near(x["width"], max(3, p["dur"] * g["pps"] - 2), 0.5) for x, p in zip(cl_, ps)),
         [(x["left"], x["width"]) for x in cl_])
    said0 = " ".join(SAID[0:6])
    case("...its words on it as text (a word with a tag in it stays a word), and her tooltip",
         cl_[0]["text"] == said0 and cl_[0]["kids"] == 0 and "<b>bold</b>" in cl_[0]["text"] and cl_[0]["title"] == W["tl_clip_title"].replace("{words}", said0), cl_[0])
    fm = c.js("[window.Talk.tlFmt(0), window.Talk.tlFmt(9.96), window.Talk.tlFmt(75.04), window.Talk.tlFmt(59.94), window.Talk.tlTick(0), window.Talk.tlTick(90), window.Talk.tlTick(0.5), window.Talk.tlTick(61.25)]")
    case("the time reads \"m:ss.t / m:ss.t\", and the ruler's marks m:ss with a tenth only when there is one",
         fm == ["0:00.0", "0:10.0", "1:15.0", "0:59.9", "0:00", "1:30", "0:00.5", "1:01.3"] and g["time"] == "%s / %s" % (c.js("window.Talk.tlFmt(window.Talk.reelAt(document.getElementById('vid').currentTime))"),
                                                                                                   c.js("window.Talk.tlFmt(window.Talk.total())")) and re.fullmatch(r"\d:\d\d\.\d / \d:\d\d\.\d", g["time"]), (fm, g["time"]))
    step = next((x for x in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60) if x * g["pps"] >= 56), 60)
    case("the ruler's step is the first of her steps that is 56 px wide or more, a mark at each from 0",
         len(g["ticks"]) == int(g["total"] / step + 0.001) + 1 and near(g["ticks"][0][1], PAD, 0.01) and near(g["ticks"][1][1] - g["ticks"][0][1], step * g["pps"], 0.5) and g["ticks"][0][0] == "0:00",
         (step, g["ticks"][:3]))
    kept = sum(len(p["words"]) for p in ps)
    case("past 55 px a second the words show under the clips, each where it is said, and the hint is her second one",
         g["pps"] >= 55 and not g["wordsOff"] and g["nwords"] == kept == len(SAID) and g["hint"] == W["tl_hint_words"]
         and near(c.js("parseFloat(document.querySelectorAll('#tlWords .tl-w')[7].style.left)"), PAD + rs(ps[1], 7) * g["pps"], 0.5)
         and c.js("document.querySelectorAll('#tlWords .tl-w')[2].textContent") == "<b>bold</b>" and c.js("document.querySelectorAll('#tlWords .tl-w *').length") == 0, (g["pps"], g["nwords"], g["hint"]))
    tools0 = tools()
    grey = c.js("[getComputedStyle(document.getElementById('tlSpeedBtn')).opacity, getComputedStyle(document.getElementById('tlZoomBtn')).opacity, getComputedStyle(document.getElementById('tlUndo')).opacity]")
    case("with nothing picked: the Speed menu (1×, 1.25×, 1.5×, 2×) and the Zoom menu (None, Punch in, Slow zoom) are grey, Delete clip is off, no round x anywhere, Undo and Redo grey",
         [x[0] for x in tools0["speed"]] == ["1×", "1.25×", "1.5×", "2×"] and [x[0] for x in tools0["zoom"]] == ["None", "Punch in", "Slow zoom"]
         and all(x[1] and not x[2] for x in tools0["speed"] + tools0["zoom"]) and tools0["cut"] == ["🗑 Delete clip", True] and tools0["undo"] and tools0["redo"]
         and c.count("#tl .tl-x") == 0 and grey == ["0.4", "0.4", "0.4"] and tools0["speedBtn"] == {"label": "Speed:", "value": "1×", "off": True, "on": False, "open": False}
         and tools0["zoomBtn"] == {"label": "Zoom:", "value": "None", "off": True, "on": False, "open": False} and g["sel"] is None and g["selw"] is None, (tools0, grey))
    case("Make it in CapCut is live as soon as there is something to make", c.js("window.__result().btn") == [W["make"], False])

    # ================= picking, scrubbing =================
    x = press(clip_sel(6), 0.3)
    g = tl()
    R = (x - g["left"] + g["scroll"] - PAD) / g["pps"]
    cl_ = clips()
    case("a press on a clip picks it and moves the line there: outlined, its round x on it (\"Delete this clip\"), the line and the time at that spot",
         [x_["on"] for x_ in cl_] == [False, True, False] and cl_[1]["x"] == W["tl_clip_x"] and [x_["x"] for x_ in cl_].count(None) == 2 and g["sel"] == "clip" and g["selw"] == 6
         and near(now_R(), R, 0.02) and near(g["head"], PAD + R * g["pps"], 3) and g["time"].startswith(c.js("window.Talk.tlFmt(%r)" % now_R())), (cl_[1], g["head"], R, now_R()))
    tools1 = tools()
    case("...the picked clip's words are outlined in the script, the Speed and Zoom menus come alive with what it has checked (1×, None), and the button reads Delete clip",
         c.js("window.__picked()") == ps[1]["words"] and [x_[1] for x_ in tools1["speed"] + tools1["zoom"]] == [False] * 7 and [x_[2] for x_ in tools1["speed"]] == [True, False, False, False]
         and [x_[2] for x_ in tools1["zoom"]] == [True, False, False] and tools1["cut"] == ["🗑 Delete clip", False], (c.js("window.__picked()"), tools1))
    ru = c.rect("#tlRuler")
    was = rev()
    c.mouse_move(g["left"] + 100, ru["cy"])
    c.mouse_press()
    c.mouse_release()
    g = tl()
    case("a press on empty track clears what was picked (no outline, no x, grey menus) and still moves the line",
         g["sel"] is None and g["selw"] is None and not any(x_["on"] or x_["x"] for x_ in clips()) and c.js("window.__picked()") == [] and all(x_[1] for x_ in tools()["speed"])
         and tools()["cut"][1] is True and near(now_R(), (100 + g["scroll"] - PAD) / g["pps"], 0.02), (g["sel"], now_R()))
    c.mouse_move(g["left"] + 60, ru["cy"])
    c.mouse_press()
    c.mouse_move(g["left"] + 140, ru["cy"])
    c.mouse_move(g["left"] + 220, ru["cy"])
    during = c.js("[window.Talk.quiet(), window.__tl().drag]")
    mid_R = now_R()
    c.mouse_move(g["left"] + 300, ru["cy"])
    c.mouse_release()
    g2 = tl()
    case("dragging along the track scrubs: the line and the preview's time follow the hand, the 3-second look waits meanwhile, and nothing is saved",
         during == [False, True] and near(mid_R, (220 + g["scroll"] - PAD) / g["pps"], 0.02) and near(now_R(), (300 + g["scroll"] - PAD) / g["pps"], 0.02)
         and near(g2["head"], PAD + now_R() * g2["pps"], 3) and rev() == was and not g2["drag"] and c.js("window.Talk.quiet()"), (during, mid_R, now_R()))

    # ================= Speed and Zoom on a clip =================
    press(clip_sel(6), 0.5)
    was, n0 = rev(), tools()["n"][0]
    tot0 = tl()["total"]
    menu_pick(c, "tlSpeed", 2)
    moved(was)
    p1 = piece_of(6)
    cl_ = clips()
    case("Speed 1.5× on the picked clip: saved over its words, the clip striped blue with a \"1.5×\" badge, the reel shorter, the words blue in the script, the bar's line says \"1 sped up\"; one Undo step",
         rec().get("speeds") == [{"a": 6, "b": 12, "v": 1.5}] and p1["speed"] == 1.5 and cl_[1]["fast"] and cl_[1]["bd"] == ["1.5×"] and "repeating-linear-gradient" in cl_[1]["bg"]
         and tl()["total"] < tot0 - 0.1 and "fast" in c.js("window.Talk.wordEl(8).className") and "· 1 sped up" in c.text("#sum") and tools()["n"][0] == n0 + 1
         and [x_[2] for x_ in tools()["speed"]] == [False, False, True, False] and cl_[1]["on"], (rec().get("speeds"), cl_[1], c.text("#sum")))
    was = rev()
    menu_pick(c, "tlZoom", 1)
    moved(was)
    case("Zoom Punch in on the picked clip: saved over its words, its badge beside the speed's, its item checked",
         rec().get("zooms") == [{"a": 6, "b": 12, "kind": "punch"}] and clips()[1]["bd"] == ["1.5×", "Punch in"] and [x_[2] for x_ in tools()["zoom"]] == [False, True, False], (rec().get("zooms"), clips()[1]["bd"]))
    was = rev()
    menu_pick(c, "tlZoom", 2)
    moved(was)
    case("...Slow zoom takes its place", rec().get("zooms") == [{"a": 6, "b": 12, "kind": "zoom"}] and clips()[1]["bd"] == ["1.5×", "Slow zoom"])
    was = rev()
    menu_pick(c, "tlZoom", 0)
    moved(was)
    was = rev()
    menu_pick(c, "tlSpeed", 0)
    moved(was)
    case("...None and 1× take them off again (a speed of 1 is no speed-up: nothing is kept for it)",
         rec().get("zooms") == [] and rec().get("speeds") == [] and clips()[1]["bd"] == [] and not clips()[1]["fast"] and near(tl()["total"], tot0, 0.002), (rec().get("zooms"), rec().get("speeds")))

    # ================= Split =================
    ps = P()
    at(ps[0]["to"] + 0.15)
    was = rev()
    c.click("#tlSplit", check=False)
    case("Split with the line on nothing: \"Move the line onto a clip to split it\", nothing saved", toast() == W["split_no_clip"] and rev() == was, toast())
    at((WORDS[2]["end"] + WORDS[3]["start"]) / 2 + 0.01)
    c.click("#tlSplit", check=False)
    moved(was)
    case("Split: the clip under the line is split at the gap between two words nearest the line, with her toast naming the word after it",
         rec().get("splits") == [3] and toast() == W["split_before"].replace("{word}", "we") and [p["words"] for p in P()][:2] == [[0, 1, 2], [3, 4, 5]] and tl()["selw"] == 3
         and [x_["on"] for x_ in clips()] == [False, True, False, False], (rec().get("splits"), toast(), [x_["on"] for x_ in clips()]))
    at(WORDS[0]["start"] + 0.01)
    was = rev()
    c.click("#tlSplit", check=False)
    moved(was)
    at(WORDS[0]["start"] + 0.01)
    was = rev()
    c.click("#tlSplit", check=False)
    time.sleep(0.3)
    case("...a clip of one word can't be split smaller: her toast, nothing saved",
         [p["words"] for p in P()][:2] == [[0], [1, 2]] and toast() == W["split_one_word"] and rev() == was and sorted(rec().get("splits")) == [1, 3], (toast(), rec().get("splits")))
    save_js({"splits": []})

    # ================= a clip's ends: in cuts, out brings back =================
    ps = P()
    p0 = ps[0]
    pps0 = tl()["pps"]
    r = drag_end(clip_sel(0) + " .tl-clip-h.r", tlx(rs(p0, 3)), release=False)
    during = c.js("[window.Talk.quiet(), window.__tl().drag, parseFloat(document.querySelector('#tlClips .tl-clip[data-w=\"0\"]').style.width)]")
    was = rev()
    c.mouse_release()
    moved(was)
    case("a clip's end dragged in cuts to the nearest word edge, sound and picture: those words are cut, her toast says which; the look waited and the clip followed the hand meanwhile",
         rec().get("cut") == [[3, 5]] and toast() == W["cut_said"].replace("{words}", "we were there.") and during[0] is False and during[1] is True
         and near(during[2], max(4, (rs(p0, 3) - p0["at"]) * pps0), 2) and "cut" in c.js("window.Talk.wordEl(4).className"), (rec().get("cut"), toast(), during))
    case("...and it is one Undo step", tools()["undo"] is False)
    p0 = piece_of(0)
    endx = tlx(p0["at"] + p0["dur"])
    was = rev()
    drag_end(clip_sel(0) + " .tl-clip-h.r", endx + 8)
    moved(was)
    case("the end dragged a little way out brings back only the cut words whose time falls within that distance (\"we were\")",
         rec().get("cut") == [[5, 5]] and toast() == W["brought_back"].replace("{words}", "we were"), (rec().get("cut"), toast()))
    p0 = piece_of(0)
    was = rev()
    drag_end(clip_sel(0) + " .tl-clip-h.r", tlx(p0["at"] + p0["dur"]) + 200)
    moved(was)
    case("...and further out, the rest (\"there.\")", rec().get("cut") == [] and toast() == W["brought_back"].replace("{words}", "there."), (rec().get("cut"), toast()))
    ps = P()
    last = ps[-1]
    was = rev()
    drag_end(clip_sel(last["words"][0]) + " .tl-clip-h.r", tlx(last["at"] + last["dur"]) + 40)
    time.sleep(0.3)
    case("dragged out where nothing is cut: \"Nothing cut there to bring back\", nothing saved, the clip back at its size",
         toast() == W["nothing_back"] and rev() == was and near(clips()[-1]["width"], max(3, last["dur"] * tl()["pps"] - 2), 0.5), (toast(), clips()[-1]["width"]))
    p1 = piece_of(6)
    was = rev()
    drag_end(clip_sel(6) + " .tl-clip-h", tlx(rs(p1, 8)))
    moved(was)
    case("a clip's START dragged in cuts the words before the nearest word edge (\"It was\")",
         rec().get("cut") == [[6, 7]] and toast() == W["cut_said"].replace("{words}", "It was") and [p["words"][0] for p in P()] == [0, 8, 13], (rec().get("cut"), toast()))
    p1 = piece_of(8)
    was = rev()
    drag_end(clip_sel(8) + " .tl-clip-h", tlx(p1["at"]) - 300)
    moved(was)
    case("...and dragged back out brings them back, in the order they are said", rec().get("cut") == [] and toast() == W["brought_back"].replace("{words}", "It was"), (rec().get("cut"), toast()))
    r = c.rect(clip_sel(0) + " .tl-clip-h.r")
    was = rev()
    c.mouse_move(r["cx"], r["cy"])
    c.mouse_press()
    c.mouse_move(r["cx"] - 2, r["cy"])
    c.mouse_release()
    time.sleep(0.2)
    case("a press on an end that moves 3 px or less is no trim: nothing saved", rev() == was and rec().get("cut") == [] and not tl()["drag"])
    p0 = piece_of(0)
    r = drag_end(clip_sel(0) + " .tl-clip-h.r", tlx(rs(p0, 2)), release=False)
    c.js("document.getElementById('tlTrack').dispatchEvent(new PointerEvent('pointermove', {bubbles: true, pointerType: 'mouse', buttons: 0, clientX: 300, clientY: %r}))" % r["cy"])
    gone = c.js("window.__tl().drag")
    c.mouse_release()
    time.sleep(0.3)
    case("a trim whose button was let go where the page never saw it ends at once and saves nothing; the clip is back at its size",
         gone is False and rev() == was and rec().get("cut") == [] and near(clips()[0]["width"], max(3, p0["dur"] * tl()["pps"] - 2), 0.5), (gone, clips()[0]["width"]))
    r = c.rect(clip_sel(0) + " .tl-clip-h.r")
    c.mouse_move(r["cx"], r["cy"])
    c.cdp("Input.dispatchMouseEvent", {"type": "mousePressed", "x": r["cx"], "y": r["cy"], "button": "left", "buttons": 1, "clickCount": 1, "modifiers": 2, "pointerType": "mouse"})
    held = c.js("window.__tl().drag")
    c.cdp("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": r["cx"], "y": r["cy"], "button": "left", "buttons": 0, "clickCount": 1, "modifiers": 2, "pointerType": "mouse"})
    case("a Control-click (the Mac's right click) starts no drag", held is False and rev() == was)

    # ================= a sped-up clip: its words under it, and its end dragged out =================
    save_js({"speeds": [{"a": 6, "b": 8, "v": 2}], "cut": [[9, 12]]})
    pf, g = piece_of(6), tl()
    idx = [i for p in P() for i in p["words"]].index(8)
    left8 = c.js("parseFloat(document.querySelectorAll('#tlWords .tl-w')[%d].style.left)" % idx)
    wide8 = c.js("parseFloat(document.querySelectorAll('#tlWords .tl-w')[%d].style.width)" % idx)
    case("the words under a sped-up clip sit where they are said on the REEL: a word's place and width are divided by the clip's speed",
         pf["speed"] == 2 and pf["words"] == [6, 7, 8] and near(left8, PAD + (pf["at"] + (WORDS[8]["start"] - pf["from"]) / 2) * g["pps"], 0.5)
         and near(wide8, max(6, (WORDS[8]["end"] - WORDS[8]["start"]) / 2 * g["pps"]), 0.5) and (WORDS[8]["start"] - pf["from"]) / 2 * g["pps"] > 20, (left8, wide8, pf))
    # dragged out by a little over HALF the time to the last cut word: at 2x that reaches every cut word; counted
    # at 1x it would stop one word short
    reach = (WORDS[12]["start"] - pf["to"] + 0.02) / 2
    was = rev()
    drag_end(clip_sel(6) + " .tl-clip-h.r", tlx(pf["at"] + pf["dur"]) + reach * g["pps"])
    moved(was)
    case("a sped-up clip's end dragged out brings back the cut words within the dragged distance x its speed (2x: twice as far along the talking)",
         WORDS[11]["start"] <= pf["to"] + reach < WORDS[12]["start"] and reach * g["pps"] > 6 and rec().get("cut") == []
         and toast() == W["brought_back"].replace("{words}", "and you 're in."), (rec().get("cut"), toast(), reach, g["pps"]))
    save_js({"speeds": [], "cut": []})

    # ================= a new state that is not ready, with an end in the hand =================
    press(clip_sel(6), 0.5)
    drag_end(clip_sel(6) + " .tl-clip-h.r", tlx(rs(piece_of(6), 9)), release=False)
    held = c.js("[window.__tl().drag, window.__tl().sel, window.__tl().selw]")
    c.js("window.Talk.emit('apply', {changed: true, ready: false, how: 'poll', outside: true})")
    let_go = c.js("[window.__tl().drag, window.__tl().sel, window.__tl().selw]")
    was = rev()
    c.mouse_release()
    time.sleep(0.3)
    case("a state that is no longer ready (the video swapped, its script being made again) ends a drag in the hand and clears what was picked; letting go afterwards saves nothing",
         held == [True, "clip", 6] and let_go == [False, None, None] and rev() == was and rec().get("cut") == [], (held, let_go))
    c.js("window.Talk.poll(true)")
    time.sleep(0.4)
    c.wait_for("document.querySelectorAll('#tlClips .tl-clip').length === 3 && !document.getElementById('editStep').hidden", 10)

    # ================= photo blocks =================
    vkey = s.video.key(kit / "Footage" / FOOT)
    me = {"x": 0.3, "y": 0.7, "w": 0.3}
    A = {"a": 1, "b": 3, "ns": [3, 2, 1], "v": None, "from": 0, "spot": "center", "pos": None, "me": None}
    V = {"a": 6, "b": 9, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 0.5, "spot": "pip", "pos": None, "me": me}
    S = {"a": 13, "b": 14, "ns": [4], "v": None, "from": 0, "spot": "corner", "pos": None, "me": None}
    at(0.0)
    save_js({"shots": [A, V, S]})
    ps, g, bl = P(), tl(), blocks()

    def span(a, b):
        on = [p for p in P() if a <= p["words"][0] <= b]
        return on[0]["at"], on[-1]["at"] + on[-1]["dur"]
    sp = [span(1, 3), span(6, 9), span(13, 14)]
    case("a block for each photo stretch and each video, over the words it goes with on the reel: left = 12 + start x scale, width = length x scale - 2",
         [b_["a"] for b_ in bl] == [1, 6, 13] and all(near(b_["left"], PAD + a_ * g["pps"], 0.5) and near(b_["width"], max(18, (e_ - a_) * g["pps"] - 2), 0.5) for b_, (a_, e_) in zip(bl, sp)),
         [(b_["left"], b_["width"]) for b_ in bl])
    case("...their labels are hers: \"3 photos · Center\" with its photos small, a video's name and its spot after a ▶, one photo just its spot; her tooltip",
         bl[0]["label"] == "3 photos · Center" and bl[0]["imgs"] == 3 and bl[1]["label"] == FOOT + " · Full screen, you in the corner" and "▶" in bl[1]["text"]
         and bl[2]["label"] == "Small corner" and bl[2]["imgs"] == 1 and all(b_["title"] == W["tl_photo_title"] and b_["kids"] == 0 for b_ in bl), bl)
    c.js("window.scrollTo(0, 0)")
    press(block_sel(1), 0.5)
    g, bl, tools2 = tl(), blocks(), tools()
    seg = c.rect('#script .seg[data-a="1"]')
    room = c.js("window.innerHeight - document.getElementById('dock').offsetHeight")
    case("a press on a photo block picks it: outlined, its round x (\"Delete this photo\"), the button reads Delete photo, and the clip's two menus go grey",
         [b_["on"] for b_ in bl] == [True, False, False] and bl[0]["x"] == W["tl_photo_x"] and g["sel"] == "photo" and g["selw"] is None and tools2["cut"] == ["🗑 Delete photo", False]
         and all(x_[1] for x_ in tools2["speed"] + tools2["zoom"]) and c.js("window.Talk.SELSHOT") == 1, (bl[0], tools2["cut"]))
    case("...and its bar in the script is lit and in view", "on" in c.js("document.querySelector('#script .seg[data-a=\"1\"]').className") and 0 <= seg["y"] and seg["bottom"] <= room + 1, (seg, room))
    c.desktop((1280, 600))
    try:
        c.js("window.scrollTo(0, 0)")
        time.sleep(0.3)
        below = c.rect('#script .seg[data-a="13"]')["y"] > c.js("window.innerHeight - document.getElementById('dock').offsetHeight")
        press(block_sel(13), 0.5)
        time.sleep(0.2)
        seg = c.rect('#script .seg[data-a="13"]')
        room = c.js("window.innerHeight - document.getElementById('dock').offsetHeight")
        case("a press on a block whose bar is out of sight brings the bar into view ABOVE the dock, never under it (ours: the page keeps the dock's room when it scrolls something into view)",
             below and 0 <= seg["y"] and seg["bottom"] <= room + 1 and c.js("window.Talk.SELSHOT") == 13, (below, seg, room))
    finally:
        c.desktop()
        c.js("window.scrollTo(0, 0)")
        time.sleep(0.2)
    pv = [p for p in P() if 6 <= p["words"][0] <= 12]
    p_end = next(p for p in pv if 11 in p["words"])
    was = rev()
    drag_end(block_sel(6) + " .tl-ph-h.r", tlx(re_(p_end, 11)))
    moved(was)
    got = shot(6) or {}
    case("her fault, fixed: a VIDEO block's end dragged to another word keeps its video, its start point, its spot and where they sit (hers lost the video)",
         (got.get("a"), got.get("b")) == (6, 11) and got.get("v") == FOOT and got.get("from") == 0.5 and got.get("spot") == "pip" and got.get("me") == me
         and toast() == W["photo_now_on"].replace("{words}", c.js("window.Talk.wordsOf(6, 11, 40)")), (got, toast()))
    case("...a photo's ends only change which words it covers: nothing was cut, and the talking is as long as it was", rec().get("cut") == [] and near(tl()["total"], g["total"], 0.002))
    p_a = piece_of(0)
    was = rev()
    drag_end(block_sel(1) + " .tl-ph-h.r", tlx(re_(p_a, 0)) - 4)
    time.sleep(0.3)
    case("an end dragged past the other end: \"That would leave the photo no words\", nothing saved, the block back where it was",
         toast() == W["no_words_left"] and rev() == was and (shot(1) or {}).get("b") == 3 and near(blocks()[0]["width"], bl[0]["width"], 0.5), (toast(), shot(1)))
    was = rev()
    drag_end(block_sel(1) + " .tl-ph-h", tlx(rs(p_a, 0)) + 1)
    moved(was)
    case("a photo block's START dragged to an earlier word takes it from there, with its photos in their order and its spot; the block is the one picked",
         (shot(0) or {}).get("b") == 3 and shot(0)["ns"] == [3, 2, 1] and shot(0)["spot"] == "center" and shot(1) is None and toast() == W["photo_now_on"].replace("{words}", c.js("window.Talk.wordsOf(0, 3, 40)"))
         and c.js("window.Talk.SELSHOT") == 0, (shot(0), toast()))

    p_a = piece_of(0)
    was, n_was = rev(), tools()["n"]
    sent = len([r_ for r_ in list(c.requests) if "/talking-save" in r_["url"]])
    drag_end(block_sel(0) + " .tl-ph-h.r", tlx(re_(p_a, 3)) + 7)
    time.sleep(0.5)
    case("a photo block's end dragged a little and dropped on the word it was already on saves nothing: no save is sent, no empty Undo step (hers sent the same thing again)",
         len([r_ for r_ in list(c.requests) if "/talking-save" in r_["url"]]) == sent and rev() == was and tools()["n"] == n_was and (shot(0) or {}).get("b") == 3
         and not tl()["drag"], (len([r_ for r_ in list(c.requests) if "/talking-save" in r_["url"]]), sent, tools()["n"], n_was))

    # ================= deleting: the x, the button, the keys =================
    press(block_sel(0), 0.5)
    c.js("window.Talk.poll(true)")                      # a refresh: every stretch on the page is a new object now
    time.sleep(0.4)
    was = rev()
    c.click(block_sel(0) + " .tl-x", check=False)
    moved(was)
    case("the round x on a picked photo block deletes it, also after a refresh (the stretch is looked up by its start word): her toast, the other stretches untouched",
         shot(0) is None and [x_["a"] for x_ in rec()["shots"]] == [6, 13] and toast() == W["photo_deleted"] and tl()["sel"] is None and c.count("#tl .tl-x") == 0, (rec()["shots"], toast()))
    was = rev()
    c.key("Mod+Z")
    moved(was)
    case("Cmd or Ctrl with Z is Undo: the photo is back, with her toast, and Redo is live", (shot(0) or {}).get("ns") == [3, 2, 1] and toast() == W["undone"] and tools()["redo"] is False, (shot(0), toast()))
    was = rev()
    c.key("Mod+Shift+Z")
    moved(was)
    case("...with Shift it is Redo", shot(0) is None and toast() == W["redone"])
    was = rev()
    c.key("Mod+Z")
    moved(was)
    was = rev()
    c.key("Mod+Y")
    moved(was)
    case("...and so is Cmd or Ctrl with Y", shot(0) is None and toast() == W["redone"] and tools()["n"][1] == 0)
    was = rev()
    c.click("#tlUndo", check=False)
    moved(was)
    case("the Undo button does the same", (shot(0) or {}).get("b") == 3 and toast() == W["undone"])
    press(block_sel(13), 0.5)
    was = rev()
    c.key("Delete")
    moved(was)
    case("the Delete key removes the photo block picked", shot(13) is None and toast() == W["photo_deleted"] and [x_["a"] for x_ in rec()["shots"]] == [0, 6])
    press(block_sel(6), 0.5)
    was = rev()
    c.click("#tlCut", check=False)
    moved(was)
    case("...and so does the Delete photo button (a video's block too)", shot(6) is None and [x_["a"] for x_ in rec()["shots"]] == [0])
    press(block_sel(0), 0.5)
    was = rev()
    c.key("Backspace")
    moved(was)
    case("...and Backspace", rec()["shots"] == [] and toast() == W["photo_deleted"])
    was = rev()
    c.key("Delete")
    c.key("Backspace")
    time.sleep(0.3)
    case("Delete and Backspace do nothing with nothing picked", rev() == was and rec().get("cut") == [])
    press(clip_sel(13), 0.5)
    c.js("window.__pickWords(1, 2)")
    c.wait_for("document.getElementById('selBar').style.display === 'flex'", 5)
    c.key("Delete")
    time.sleep(0.3)
    case("...nor while words are highlighted in the script, even with a clip picked", rev() == was and rec().get("cut") == [] and tl()["sel"] == "clip")
    c.js("window.getSelection().removeAllRanges()")
    for name in ("pick", "vpick"):
        c.js("document.getElementById('%s').classList.add('open')" % name)
        n_before = tools()["n"]
        c.key("Delete")
        c.key("Mod+Z")
        c.key("Mod+Shift+Z")
        c.key("Mod+Y")
        time.sleep(0.3)
        ok_ = rev() == was and tools()["n"] == n_before and rec().get("cut") == []
        c.js("document.getElementById('%s').classList.remove('open')" % name)
        case("her fault, fixed: Delete, Undo and Redo do nothing behind the open %s picker" % ("photo" if name == "pick" else "video"), ok_, (rev(), was, tools()["n"], n_before))
    c.key("Delete")
    moved(was)
    case("Delete on a picked clip cuts its words, sound and picture: her toast, the words crossed out in the script, nothing picked any more",
         rec().get("cut") == [[13, 16]] and toast() == W["cut_clip"] and "cut" in c.js("window.Talk.wordEl(15).className") and tl()["sel"] is None and tl()["selw"] is None
         and len(clips()) == 2 and tools()["cut"][1] is True, (rec().get("cut"), toast()))
    was = rev()
    c.key("Mod+Z")
    moved(was)
    press(clip_sel(13), 0.5)
    was = rev()
    c.click(clip_sel(13) + " .tl-x", check=False)
    moved(was)
    case("the round x on a picked clip does the same", rec().get("cut") == [[13, 16]] and toast() == W["cut_clip"])
    was = rev()
    c.click("#tlUndo", check=False)
    moved(was)
    press(clip_sel(13), 0.5)
    was = rev()
    c.click("#tlCut", check=False)
    moved(was)
    case("...and the Delete clip button", rec().get("cut") == [[13, 16]])
    save_js({"cut": [], "shots": []})

    # ================= Undo and Redo: 60 steps, the chat, a video since gone =================
    c.js("window.Talk.forget()")
    n = c.js("(async function(){ for (var i = 0; i < 62; i++) await window.Talk.save({captions: i % 2 === 1}); return window.Talk.UNDO.length; })()", timeout=90)
    case("Undo keeps the last 60 steps", n == 60 and tools()["undo"] is False, n)
    s.cut(KIT, [[0, 1]])
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.REC.cut && window.Talk.REC.cut.length === 1", 10)
    was = rev()
    c.key("Mod+Z")
    time.sleep(0.3)
    case("after the assistant cut in the chat, Undo and Redo are empty and grey, and the key says \"Nothing to undo\": one press could have wiped the cut (2c)",
         tools()["n"] == [0, 0] and tools()["undo"] and tools()["redo"] and toast() == W["nothing_undo"] and rev() == was and rec().get("cut") == [[0, 1]], (tools()["n"], toast()))
    c.key("Mod+Y")
    time.sleep(0.2)
    case("...and Redo says \"Nothing to redo\"", toast() == W["nothing_redo"] and rev() == was)
    s.cut(KIT, [], replace=True)
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.REC.cut && window.Talk.REC.cut.length === 0", 10)
    A2 = dict(A)
    V2 = dict(V, b=9)
    save_js({"shots": [A2, V2]})
    save_js({"shots": []})                               # the step Undo will take back holds a photo stretch AND the video
    away = kit / ".kit" / "bts-away.tmp"
    (kit / "Footage" / FOOT).rename(away)
    try:
        was = rev()
        c.click("#tlUndo", check=False)
        moved(was)
        case("an Undo whose step names a Footage video since taken away restores the rest and leaves that one stretch out (hers), with her toast",
             [(x_["a"], x_["b"], x_["ns"]) for x_ in rec()["shots"]] == [(1, 3, [3, 2, 1])] and toast() == W["undone"], (rec()["shots"], toast()))
    finally:
        away.rename(kit / "Footage" / FOOT)
        old = time.time() - 7200
        os.utime(str(kit / "Footage" / FOOT), (old, old))
    save_js({"shots": [], "captions": True})

    # ================= every word on the page; text as text; no path =================
    save_js({"shots": [A, V], "speeds": [{"a": 13, "b": 16, "v": 2}], "zooms": [{"a": 13, "b": 16, "kind": "zoom"}]})
    press(block_sel(1), 0.5)
    ok = t.allowed_text(s, extra=set(SAID) | {SHORT, TALK, FOOT, "❚❚", "you're", "×", "▶", "▶ bts"})
    texts = c.js(t.READ_TEXT)
    tick = re.compile(r"\d+:\d\d(\.\d)?")

    def theirs(x_):                                     # a clip shows the words said in it, a space between
        return all(w_ in SAID for w_ in x_.split(" "))
    stray = [x_ for x_ in texts if not ok(x_) and not theirs(x_) and not tick.fullmatch(x_) and not re.fullmatch(r"\d:\d\d\.\d / \d:\d\d\.\d", x_)]
    case("every piece of text on the page with the timeline full (%d) is one of her lines, one of ours, or the photographer's own" % len(texts), len(texts) > 120 and not stray, stray[:6])
    case("\"Claude\" is nowhere on the page", "claude" not in " ".join(texts).lower())
    blob = c.js("document.documentElement.outerHTML")
    case("no path anywhere in the page as it stands", str(s.work) not in blob and "/private/" not in blob and "Your Content" not in blob and "/Footage/" not in blob and "/Photos/" not in blob)
    save_js({"shots": [], "speeds": [], "zooms": []})

    # ================= Make it in CapCut =================
    store = s.work / "capcut"
    before = set(os.listdir(str(store)))
    save_js({"captions": False})
    n_undo, rev0 = tools()["n"], rev()
    c.click("#makeBtn", check=False)
    first = c.js("window.__result().btn")
    c.wait_for("window.__result().h2 !== null || window.__result().ps.length > 0", 60, tell="JSON.stringify(window.__tl())")
    res = c.js("window.__result()")
    made = sorted(set(os.listdir(str(store))) - before)
    name = SHORT + " talking reel"
    case("Make it in CapCut: the button reads \"Making it…\" and is off while the job works",
         first == [W["making"], True], first)
    case("...then her result box: \"It's in CapCut\", the maker's one line naming the project, and \"Open CapCut, give your captions your look, and export.\"",
         res["h2"] == W["made_h2"] and [p_[1] for p_ in res["ps"]] == [talking_make.MADE_LISTED.replace("{project}", name), W["made_say"]] and res["ps"][-1][0] == "say" and res["kids"] == 0, res)
    case("...the project is in the (pretend) CapCut folder under the shoot's short name, and the button is back", name in made and res["btn"] == [W["make"], False] and tl()["making"] is None, (made, res["btn"]))
    case("...the record notes what was made, and its counter did NOT move: Undo is as live as it was", [m_["project"] for m_ in rec().get("made") or []] == [name] and rev() == rev0
         and tools()["n"] == n_undo and tools()["undo"] is False, (rec().get("made"), rev(), rev0, tools()["n"]))
    save_js({"captions": True})
    case("...and the next save from this page is accepted (nothing \"newer\" in the way)", rec().get("captions") is True and toast() != TR.NEWER)
    was = rev()
    c.click("#tlUndo", check=False)
    moved(was)
    case("...and Undo still undoes", rec().get("captions") is False and toast() == W["undone"])
    texts = c.js(t.READ_TEXT)
    ok = t.allowed_text(s, extra=set(SAID) | {SHORT, TALK, FOOT, "❚❚", "you're", "×", "▶"})
    stray = [x_ for x_ in texts if not ok(x_) and not theirs(x_) and not tick.fullmatch(x_) and not re.fullmatch(r"\d:\d\d\.\d / \d:\d\d\.\d", x_)]
    case("...every word of the result box is hers", not stray, stray[:4])
    # a save and the press in the same tick: the save is sent AND answered before the make is asked for
    c.js("(function(){ var real = window.fetch, log = window.__order = []; window.fetch = function(u){"
         " var n = String(u).indexOf('/talking-save') >= 0 ? 'save' : String(u).indexOf('/talking-make') >= 0 ? 'make' : null;"
         " if (n) log.push(n + '>'); var p = real.apply(this, arguments); if (n) p.then(function(){ log.push(n + '<'); }, function(){ log.push(n + '!'); }); return p; }; })()")
    c.js("document.getElementById('result').textContent = ''; window.Talk.save({captions: true}); document.getElementById('makeBtn').click(); 1")
    c.wait_for("window.__result().h2 !== null || window.__result().ps.length > 0", 60, tell="JSON.stringify(window.__tl())")
    order, res = c.js("window.__order"), c.js("window.__result()")
    name2 = name + " 2"
    case("a save still on its way when Make it in CapCut is pressed goes first, and is answered, before the make is asked for: what is made is what the page shows",
         order[:3] == ["save>", "save<", "make>"] and rec().get("captions") is True and res["h2"] == W["made_h2"], order)
    case("...and a second reel of the same shoot is \"talking reel 2\", never over the first", name2 in os.listdir(str(store)) and name in os.listdir(str(store))
         and res["ps"][0][1] == talking_make.MADE_LISTED.replace("{project}", name2), (sorted(os.listdir(str(store))), res["ps"]))
    (kit / "Talking" / TALK).rename(kit / ".kit" / "talk-away.tmp")
    try:
        c.click("#makeBtn", check=False)
        c.wait_for("window.__result().ps.length === 1", 15, tell="JSON.stringify(window.__result())")
        res = c.js("window.__result()")
        case("a make that is refused shows her line in the result box, in red, and the button is back: \"Your talking video isn't in the Talking folder anymore.\"",
             res["ps"] == [["status bad", TR.MAKE_WORDS["gone"]]] and res["h2"] is None and res["btn"] == [W["make"], False], res)
    finally:
        (kit / ".kit" / "talk-away.tmp").rename(kit / "Talking" / TALK)
    c.block_urls(["*talking-make*"])
    try:
        c.click("#makeBtn", check=False)
        c.wait_for("window.__result().ps.length === 1 && window.__result().ps[0][1] !== %s" % json.dumps(TR.MAKE_WORDS["gone"]), 15, tell="JSON.stringify(window.__result())")
        res = c.js("window.__result()")
        case("the Assistant out of reach at the press: plain words in the box, the button back, nothing left \"Making it…\"",
             res["ps"] == [["status bad", s.tp.OUR_WORDS["cant_reach"][0]]] and res["btn"] == [W["make"], False] and tl()["making"] is None, res)
    finally:
        c.block_urls([])
    follow = c.js("(function(){ var T = window.Talk, out = [];"
                  " T.emit('make', {id: 'aaaaaaaaaaaa', state: 'done', words: ['old'], problem: null}); out.push(window.__result().btn[0], T.tl().making);"
                  " T.emit('make', {id: 'bbbbbbbbbbbb', state: 'running', words: [], problem: null}); out.push(window.__result().btn, T.tl().making);"
                  " T.emit('make', {id: 'bbbbbbbbbbbb', state: 'problem', words: [], problem: '<i>plain</i> words'}); out.push(window.__result().btn, window.__result().ps, window.__result().kids, T.tl().making);"
                  " return out; })()")
    case("a make finished before the page opened shows nothing; one at work when the page opens is followed (\"Making it…\") to its end; its problem shows as text",
         follow[0:2] == [W["make"], None] and follow[2:4] == [[W["making"], True], "bbbbbbbbbbbb"] and follow[4] == [W["make"], False]
         and follow[5] == [["status bad", "<i>plain</i> words"]] and follow[6] == 0 and follow[7] is None, follow)
    newer = c.js("(function(){ var T = window.Talk, out = [];"
                 " T.emit('make', {id: 'cccccccccccc', state: 'running', words: [], problem: null}); out.push(T.tl().making);"
                 " T.emit('make', {id: 'dddddddddddd', state: 'queued', words: [], problem: null}); out.push(T.tl().making, window.__result().btn);"
                 " document.getElementById('result').textContent = '';"
                 " T.emit('make', {id: 'eeeeeeeeeeee', state: 'done', words: ['not this page\\'s'], problem: null}); out.push(T.tl().making, window.__result().btn, window.__result().ps.length);"
                 " return out; })()")
    case("while one make is followed, a NEWER one at work is the one followed from then on; a newer one already over ends the wait, the button back, and its words are not shown as this page's",
         newer == ["cccccccccccc", "dddddddddddd", [W["making"], True], None, [W["make"], False], 0], newer)
    # the make the page follows can no longer be seen: never a page left on "Making it…"
    job = kit / ".kit" / "talking-make-job.json"
    job.rename(kit / ".kit" / "job-away.tmp")
    try:
        gone_make = s.state(KIT, "&only=make")
        c.js("document.getElementById('result').textContent = ''; window.Talk.emit('make', {id: 'ffffffffffff', state: 'running', words: [], problem: null})")
        time.sleep(2.5)
        still = c.js("[window.__result().btn, window.__tl().making]")
        c.wait_for("window.__tl().making === null", 12, tell="JSON.stringify(window.__result())")
        res = c.js("window.__result()")
        case("a make the page is following whose record has gone: after five answers with no make in them the button is back and her line says so in red (\"Something went wrong making it.\"); not at the first such answer",
             gone_make == {"ok": True, "make": None} and still == [[W["making"], True], "ffffffffffff"] and res["ps"] == [["status bad", TR.MAKE_WORDS["went_wrong"]]]
             and res["btn"] == [W["make"], False], (gone_make, still, res))
    finally:
        (kit / ".kit" / "job-away.tmp").rename(job)
    c.block_urls(["*talking-state*"])
    try:
        c.js("window.Talk.emit('make', {id: 'ffffffffffff', state: 'running', words: [], problem: null})")
        cleared = c.js("window.__result().ps.length")
        c.wait_for("window.__tl().making === null", 12, tell="JSON.stringify(window.__result())")
        res = c.js("window.__result()")
        case("...and with the Assistant out of reach while a make is followed, the same: the button back and plain words; an earlier red line is cleared when a make is followed again",
             cleared == 0 and res["ps"] == [["status bad", s.tp.OUR_WORDS["cant_reach"][0]]] and res["btn"] == [W["make"], False], (cleared, res))
    finally:
        c.block_urls([])
    time.sleep(1.3)
    case("no part of the page failed, no browser pop-up was asked for, nothing was asked of the internet, and the Footage list was never asked for",
         c.js("window.Talk.faults.length") == 0 and c.js("window.__dialogs") == 0 and not list(c.dialogs) and not c.outside_requests()
         and not [r_["url"] for r_ in list(c.requests) if "/reel-footage" in r_["url"]], (c.js("window.Talk.faults"), c.outside_requests()[:3]))
    errs = [e for e in c.page_errors() if "talking-make" not in e and "talking-state" not in e and "ERR_BLOCKED" not in e and "Failed to load resource" not in e]
    case("no page errors", not errs, errs[:3])
    case("nothing was made for the Footage video (no small copy, no still)", not list((kit / ".kit").glob("footage/*/preview.mp4")) and not list((kit / ".kit").glob("footage/*/strip*")))

    # ================= phone width =================
    c.phone()
    try:
        open_it()
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth, document.getElementById('tlTrack').getBoundingClientRect().right]")
        case("phone width: no sideways scroll of the page with the timeline showing; the track is inside the window and scrolls by itself",
             wide[0] <= 0 and wide[1] == 390 and wide[2] <= 390.5 and c.js("getComputedStyle(document.getElementById('tlTrack')).overflowX") == "auto", wide)
    finally:
        c.desktop()

    # ================= the long talk: the scale, the ruler, the timeline's own zoom =================
    open_it(LONG, sents=20)
    st = s.state(LONG)
    code_, j = s.post("/talking-save", {"kit": LONG, "base": st["rev"], "page": "tltest00001", "saved": {
        "cut": [[1, 4]], "shots": [{"a": 0, "b": 0, "ns": [1], "v": None, "from": 0, "spot": "full", "pos": None, "me": None}]}})
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.SH.length === 1 && document.querySelectorAll('#tlPhotos .tl-ph').length === 1", 10)
    g, ps = tl(), P()
    fit = max(200, g["w"] - 2 * PAD) / max(g["total"], 1)
    step = next((x for x in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60) if x * fit >= 56), 60)
    case("the long talk fits the track with the slider at 0; under 55 px a second no words show and the hint is her first",
         code_ == 200 and near(g["pps"], fit, 0.01) and fit < 55 and g["wordsOff"] and g["nwords"] == 0 and g["hint"] == W["tl_hint"] and near(g["inner"], g["total"] * fit + 24, 0.5), (g["pps"], fit, g["hint"]))
    case("...the ruler's step is %s s there (the first that is 56 px or more)" % step, step > 1 and near(g["ticks"][1][1] - g["ticks"][0][1], step * fit, 0.5) and len(g["ticks"]) == int(g["total"] / step + 0.001) + 1, g["ticks"][:3])
    cl0, bl0 = clips()[0], blocks()[0]
    case("a clip is never under 3 px wide and a photo block never under 18, however short (a first clip of %.2f s)" % ps[0]["dur"],
         ps[0]["dur"] * fit - 2 < 3 and cl0["width"] == 3 and bl0["width"] == 18, (ps[0], cl0["width"], bl0["width"]))
    c.set_value("#tlScale", 100)
    g = tl()
    case("most zoomed in is 240 px a second; the words show and the ruler's step is a quarter second", near(g["pps"], 240, 0.01) and not g["wordsOff"] and g["nwords"] == sum(len(p["words"]) for p in ps)
         and near(g["ticks"][1][1] - g["ticks"][0][1], 60, 0.01) and g["ticks"][1][0] == "0:00.3" and g["hint"] == W["tl_hint_words"], (g["pps"], g["ticks"][:2]))
    c.set_value("#tlScale", 50)
    g = tl()
    case("the slider's curve is fit x (max / fit) ^ (v / 100)", near(g["pps"], fit * (240 / fit) ** 0.5, 0.01), (g["pps"], fit * (240 / fit) ** 0.5))
    c.click("#tlIn", check=False)
    up = tl()["value"]
    c.click("#tlOut", check=False)
    c.click("#tlOut", check=False)
    down = tl()["value"]
    c.set_value("#tlScale", 95)
    c.click("#tlIn", check=False)
    top = tl()["value"]
    case("+ and − move the slider by 15, held to 0 and 100; their names for a screen reader are hers",
         (up, down, top) == (65, 35, 100) and c.js("[document.getElementById('tlOut').getAttribute('aria-label'), document.getElementById('tlScale').getAttribute('aria-label'), document.getElementById('tlIn').getAttribute('aria-label')]")
         == [W["zoom_out"], W["zoom_tl"], W["zoom_in"]], (up, down, top))
    c.set_value("#tlScale", 60)
    tr = c.rect("#tlTrack")
    c.js("document.getElementById('tlTrack').scrollLeft = 900; window.__wheels.length = 0; window.scrollTo(0, 0)")
    g = tl()
    mx = tr["x"] + 400
    R_under = (mx - g["left"] + g["scroll"] - PAD) / g["pps"]
    c.wheel((mx, tr["cy"]), -50, meta=not t.WINDOWS, ctrl=t.WINDOWS)
    time.sleep(0.1)
    g2 = tl()
    seen = c.js("window.__wheels")
    R_after = (mx - g2["left"] + g2["scroll"] - PAD) / g2["pps"]
    case("Cmd or Ctrl with the wheel zooms the timeline by value − deltaY x 0.4, around the mouse: the moment under the mouse stays under it",
         len(seen) == 1 and seen[0][0] != 0 and near(g2["value"], max(0, min(100, 60 - seen[0][0] * 0.4)), 0.5) and g2["pps"] > g["pps"] and near(R_after, R_under, 2.5 / g2["pps"]),
         (seen, g["value"], g2["value"], R_under, R_after))
    c.js("window.__wheels.length = 0")
    y0 = c.js("window.scrollY")
    c.wheel((mx, tr["cy"]), 120)
    time.sleep(0.1)
    g3 = tl()
    seen = c.js("window.__wheels")
    case("a plain wheel over the timeline moves it sideways by that much, and the page behind does not scroll",
         len(seen) == 1 and near(g3["scroll"] - g2["scroll"], seen[0][0], 1.5) and g3["value"] == g2["value"] and c.js("window.scrollY") == y0, (seen, g2["scroll"], g3["scroll"]))
    c.set_value("#tlScale", 100)
    w_ = tl()["w"]
    f = c.js("(function(){ var T = window.Talk, tr = document.getElementById('tlTrack'), out = [], X = function(R){ return 12 + R * 240; };"
             " tr.scrollLeft = 2000;"
             " T.emit('frame', {t: 0, R: (2000 + 400 - 12) / 240, playing: true}); out.push(tr.scrollLeft);"
             " T.emit('frame', {t: 0, R: (2000 + tr.clientWidth - 59 - 12) / 240, playing: false}); out.push(tr.scrollLeft);"
             " T.emit('frame', {t: 0, R: (2000 + tr.clientWidth - 59 - 12) / 240, playing: true}); out.push(tr.scrollLeft);"
             " tr.scrollLeft = 2000; T.emit('frame', {t: 0, R: (2000 + 29 - 12) / 240, playing: true}); out.push(tr.scrollLeft);"
             " tr.scrollLeft = 2000; T.emit('frame', {t: 0, R: (2000 + 31 - 12) / 240, playing: true}); out.push(tr.scrollLeft);"
             " return out; })()")
    case("while playing the line is followed: within 30 px of the left edge or 60 px of the right the timeline jumps so the line is a quarter in; never while paused",
         f[0] == 2000 and f[1] == 2000 and near(f[2], 2000 + w_ - 59 - w_ * 0.25, 1.5) and near(f[3], 2000 + 29 - w_ * 0.25, 1.5) and f[4] == 2000, (f, w_))
    case("no page errors on the long talk either", not [e for e in c.page_errors() if "talking-make" not in e and "ERR_BLOCKED" not in e and "Failed to load resource" not in e],
         c.page_errors()[:3])
