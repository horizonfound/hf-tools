#!/usr/bin/env python3
"""The `preview` part of tests/talking_page_check.py (sub-stage C3 of the talking reel page): the tall screen
beside the script. Not run by itself:

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py --only preview

talking_page_check.py hands this file itself (`t`: its Setup, its helpers), its Setup (`s`) and, for the page, its
hidden Chrome (`c`). What is checked, in the plan's own order (docs/handoff-v24-build-2026-11-12.md, Stage C, C3):
playing the cut and the whole (her numbers: 0.02 s before a piece, to - 0.02, the word being said, the sentence lit
outside a piece, the end of the reel, the speed put back on pause, a press that ended a drag, the spacebar, "Play
the cut version" ticked and never remembered); every spot with her default numbers, the same ones CapCut gets;
several photos flashing through a stretch; dragging and sizing a photo, themselves in the corner, the caption and
its size, each held to her limits, under 3 px a click; the zooms; the captions; a Footage video kept in step; the
phone guides at her percentages, remembered by the browser; step 3's chips; and ours: a stretch is never held
across a refresh (a drag let go over a change from the chat wipes nothing), a drag that is cancelled saves nothing,
text as text, no path, no pop-up, nothing asked of the internet, phone width, and what is cut still skipped on a
page that is not showing.

The record is seeded here (TR.put_words), so nothing is transcribed. The talking video and the one Footage video
are tests/fixtures/loud-tone-3s.mp4 (3 seconds, self-made). The Footage video is played as it is: nothing here asks
the Mac to make a small copy or a still, and the page never asks for the Footage list.
"""
import json
import os
import re
import shutil
import time

KIT = "2026-09-26 Zoë's preview"
SHORT = KIT[11:]
TALK = "talk.mp4"
FOOT = "bts.mp4"
SAID = ["OK", "so", "<b>bold</b>", "we", "were", "there.",
        "It", "was", "awesome", "and", "you", "'re", "in.",
        "Every", "photo", "is", "yours."]
SENTS = [[0, 5], [6, 12], [13, 16]]


def _times():
    out = []
    for i, w in enumerate(SAID):
        base = 0.05 + 0.1 * i if i < 6 else 1.2 + 0.1 * (i - 6) if i < 13 else 2.3 + 0.1 * (i - 13)
        out.append({"w": w, "start": round(base, 3), "end": round(base + 0.07, 3), "conf": 0.9})
    return out


WORDS = _times()
PHOTOS = 6

HELPERS = r"""
window.__seeks = []; window.__rates = [];
window.__watch = function(){
  var v = document.getElementById('vid');
  if (v.__watched) return; v.__watched = true;
  v.addEventListener('seeking', function(){ window.__seeks.push(v.currentTime); });
  v.addEventListener('ratechange', function(){ window.__rates.push(v.playbackRate); });
};
window.__at = function(t){ document.getElementById('vid').currentTime = t; window.Talk.frame(); return document.getElementById('vid').currentTime; };
window.__rel = function(sel){
  var e = document.querySelector(sel), s = document.getElementById('screen').getBoundingClientRect();
  if (!e) return null;
  var r = e.getBoundingClientRect(), cs = getComputedStyle(e);
  return {l: (r.left - s.left) / s.width, t: (r.top - s.top) / s.height, w: r.width / s.width, h: r.height / s.height,
          cx: (r.left + r.width / 2 - s.left) / s.width, cy: (r.top + r.height / 2 - s.top) / s.height, shown: cs.display !== 'none'};
};
window.__lit = function(){
  return {word: Array.from(document.querySelectorAll('#script .words span.speaking')).map(function(e){ return +e.getAttribute('data-i'); }),
          sent: Array.from(document.querySelectorAll('#script .sent.now')).map(function(e){ return +e.getAttribute('data-k'); })};
};
window.__pic = function(){
  var i = document.querySelector('#phFront img'), b = document.getElementById('bvid');
  return {img: getComputedStyle(i).display !== 'none', src: i.getAttribute('src') || '', loaded: i.naturalWidth > 0,
          vid: getComputedStyle(b).display !== 'none', vsrc: b.getAttribute('src') || '', wrap: getComputedStyle(document.getElementById('phFront')).display !== 'none',
          movable: document.getElementById('phFront').classList.contains('movable'), pip: document.getElementById('screen').classList.contains('pip')};
};
window.__scale = function(){ var m = /scale\(([0-9.]+)\)/.exec(document.getElementById('vid').style.transform || ''); return m ? +m[1] : null; };
"""


def make(t, s):
    kit = s.kit(KIT)
    if (kit / ".kit" / "talking.json").exists():
        return kit
    kit = s.make_kit(KIT, photos=PHOTOS)
    # photo 2 is a wide one, by the numbered list (the picture itself does not matter to where a photo sits)
    sheet = kit / ".kit" / "sheet.json"
    d = json.loads(sheet.read_text(encoding="utf-8"))
    d["photos"][1].update({"w": 60, "h": 40, "way": "wide"})
    sheet.write_text(json.dumps(d), encoding="utf-8")
    key = s.add_talk(kit, TALK)
    s.TR.put_words(kit, TALK, key, WORDS, info={"dur": 3.0})
    return kit


def near(a, b, tol=0.006):
    return a is not None and b is not None and abs(a - b) <= tol


def box_is(r, l, t_, w, h, tol=0.006):
    return bool(r) and r["shown"] and near(r["l"], l, tol) and near(r["t"], t_, tol) and near(r["w"], w, tol) and near(r["h"], h, tol)


def run_requests(t, s):
    """By request and by reading the files, no browser."""
    case = t.case
    make(t, s)
    import talking_js_preview
    import capcut
    js = talking_js_preview.JS
    code = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)
    case("talking_js_preview.py is one string of JavaScript and nothing else", [n for n in dir(talking_js_preview) if not n.startswith("_")] == ["JS"])
    case("the preview's part is on the page, after the parts it stands on", s.tp.JS_PARTS[-1] is js or js in s.tp.JS_PARTS[4:])
    case("no pop-up and no HTML from a string in the preview's part",
         not re.search(r"\b(confirm|alert|prompt)\s*\(|innerHTML|outerHTML|insertAdjacentHTML|document\.write", js))
    case("her pitfall: the preview's part finds the talking video by its own name, never as \"video\", and uses neither of the two kept class names",
         "querySelector('video')" not in code and "getElementsByTagName" not in code and not re.search(r"['\"](bar|sel)['\"]", code))
    case("the Footage list is never asked for from the preview (only the video picker asks)", "/reel-footage" not in code)
    case("the phone guides are remembered under her key, talkGuides", code.count("'talkGuides'") == 2 and "localStorage" in code)
    case("a slow zoom's span is never under 0.1 s, a punch in is CapCut's own number, and the second video is set again past 0.35 s",
         "Math.max(0.1, zs[1] - zs[0])" in code and "PUNCH = %s" % capcut.PUNCH in code and "RESEEK = 0.35" in code and "SLOW_OUTSIDE = 1.06" in code)
    case("a stretch is never held by the drag: it keeps the start word, and looks the stretch up when the save's turn comes",
         "T.findShot(d.a)" in code and "x: x," not in code[code.index("pdrag = {"):code.index("pdrag = {") + 400])
    page = s.tp.page_html(KIT)
    case("neither tick under the preview may be put back by the browser on a reload (autocomplete off), and the cut version starts ticked",
         "id='guidesOn' autocomplete='off'>" in page and "id='cutMode' checked autocomplete='off'>" in page)
    st = s.state(KIT)
    case("the test's own script: three sentences, three pieces, a caption a word (\"you're\" closed up)",
         st["rec"]["sentences"] == SENTS and len(st["pieces"]) == 3 and [x["text"] for x in st["captions"]][9:11] == ["and", "you're"],
         (st["rec"]["sentences"], len(st["pieces"]), [x["text"] for x in st["captions"]]))
    case("...and photo 2 is a wide one", [(p["w"], p["h"]) for p in st["photos"]][:2] == [(24, 30), (60, 40)], st["photos"][:2])


def run_page(t, c, s):
    case, skip, wait_for = t.case, t.skip, t.wait_for
    W = s.tp.page_words()
    kit = make(t, s)
    import capcut
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script(HELPERS)

    def rev():
        return c.js("window.Talk.rev")

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")

    def save_js(body):
        was = rev()
        c.js("window.Talk.save(%s)" % json.dumps(body))
        moved(was)

    def rec():
        return s.rec(KIT) or {}

    def shot(a):
        return next((x for x in rec().get("shots") or [] if x["a"] == a), None)

    def at(tm):
        return c.js("window.__at(%r)" % float(tm))

    def rel(sel):
        return c.js("window.__rel(%s)" % json.dumps(sel))

    def pieces():
        return c.js("window.Talk.P()")

    def paused():
        return c.js("document.getElementById('vid').paused")

    def pause():
        c.js("document.getElementById('vid').pause()")
        c.wait_for("document.getElementById('vid').paused", 5)

    def scr():
        return c.rect("#screen")

    def drag_by(start, dx, dy, release=True, steps=6):
        """Press at `start` (a selector's middle, or parts of the screen) and drag by (dx, dy) px. Returns the
        screen's box, so what is expected can be worked out from the very numbers the page used."""
        b = scr()
        if isinstance(start, str):
            r = c.rect(start)
            x0, y0 = r["cx"], r["cy"]
        else:
            x0, y0 = b["x"] + start[0] * b["w"], b["y"] + start[1] * b["h"]
        c.drag((x0, y0), (x0 + dx, y0 + dy), steps=steps, release=release, check=False)
        return b

    def tiny_press(start):
        r = c.rect(start)
        c.mouse_move(r["cx"], r["cy"])
        c.mouse_press()
        c.mouse_move(r["cx"] + 2, r["cy"])
        c.mouse_release()

    def open_it():
        t.open_page(c, s, KIT)
        c.wait_for("document.querySelectorAll('#script .sent').length === 3", 10, tell="document.getElementById('status').textContent")
        c.wait_for("document.getElementById('vid').readyState >= 1", 15)
        c.js("window.__watch(); document.getElementById('screen').scrollIntoView({block: 'center'})")

    open_it()
    wait_for(lambda: all(p["have"] for p in s.state(KIT)["photos"]), 60)
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.PHOTOS.length === %d && window.Talk.PHOTOS.every(function(p){ return p.have; })" % PHOTOS, 10)
    b = scr()
    room = c.js("[window.innerHeight - document.getElementById('dock').offsetHeight, window.innerWidth]")
    case("the test's own footing: the whole preview is in the window, above the dock, a tall 9:16 screen",
         b["y"] >= 0 and b["bottom"] <= room[0] and b["x"] > 30 and near(b["w"] / b["h"], 9 / 16, 0.01), (b, room))

    # ---- as it opens
    first = c.js("[document.getElementById('cutMode').checked, document.getElementById('guidesOn').checked, document.getElementById('guides').hidden,"
                 " document.getElementById('capOn').classList.contains('on'), document.getElementById('capOn').getAttribute('aria-pressed'),"
                 " document.getElementById('capOff').classList.contains('on'), document.getElementById('capReset').hidden, document.getElementById('tlPlay').textContent,"
                 " document.getElementById('tlPlay').getAttribute('aria-label'), document.getElementById('screen').title]")
    case("as it opens: Play the cut version is ticked, the phone guides are off, Captions on is lit, \"Put the captions back\" is not there, and the round button says Play",
         first == [True, False, True, True, "true", False, True, "▶", "Play", "Click to play or pause"], first)
    nums = c.js("[window.Talk.ME, window.Talk.CAP, window.Talk.defPos('center', 24, 30), window.Talk.defPos('corner', 24, 30), window.Talk.defPos('corner', 60, 40), window.Talk.defPos('corner', 0, 0)]")
    want = [capcut.ME_DEFAULT, capcut.CAP_DEFAULT, capcut.default_place("center", 24, 30), capcut.default_place("corner", 24, 30),
            capcut.default_place("corner", 60, 40), capcut.default_place("corner", 0, 0)]
    same = all(set(a) == set(b_) and all(abs(a[k] - b_[k]) < 1e-9 for k in a) for a, b_ in zip(nums, want))
    case("where things sit before they are moved: the page's numbers are the very ones CapCut gets (themselves in the corner, the captions, Center, Small corner tall and wide)",
         same and near(nums[0]["w"], 0.36, 1e-9) and nums[1] == {"x": 0.5, "y": 0.71} and nums[2] == {"x": 0.5, "y": 0.44, "w": 0.704}, (nums, want))

    # ---- playing: her numbers
    P = pieces()
    tot = c.js("window.Talk.total()")
    got = c.js("(function(){ var T = window.Talk, p = T.P()[1]; return [T.pieceAt(p.from - 0.019), T.pieceAt(p.from - 0.021), T.pieceAt(p.to - 0.001), T.pieceAt(p.to), T.srcAt(T.total() + 5), T.P()[2].to - 0.02]; })()")
    case("a piece begins 0.02 s before its start and ends at its end; past the end of the reel the video's time is the last piece's end less 0.02 s",
         got[:4] == [1, -1, 1, -1] and abs(got[4] - got[5]) < 1e-9, got)
    last = WORDS[16]
    at(last["end"] + 0.04)
    a_ = c.js("window.__lit()")
    at(last["end"] + 0.06)
    b_ = c.js("window.__lit()")
    at(WORDS[3]["start"] + 0.03)
    c_ = c.js("window.__lit()")
    case("the word being said is lit from its start to 0.05 s past its end, and its sentence with it",
         a_["word"] == [16] and b_["word"] == [] and c_ == {"word": [3], "sent": [0]}, (a_, b_, c_))
    edges = c.js("(function(){ var T = window.Talk; return [T.sentenceAt(0.62 + 0.29), T.sentenceAt(0.62 + 0.31), T.sentenceAt(1.2 - 0.14), T.sentenceAt(1.2 - 0.16)]; })()")
    lit = []
    for tm in (0.85, 1.0, 1.07):
        at(tm)
        lit.append((c.js("window.Talk.pieceAt(%r)" % tm), c.js("window.__lit().sent")))
    case("outside a piece the sentence lit is the one from 0.15 s before its first word to 0.3 s past its last",
         edges == [0, -1, 1, -1] and lit == [(-1, [0]), (-1, []), (-1, [1])] and P[0]["to"] < 0.85 and P[1]["from"] > 1.09, (edges, lit))

    # ---- play and pause
    at(P[0]["from"] + 0.05)
    c.click("#screen", check=False)
    c.wait_for("!document.getElementById('vid').paused && document.getElementById('tlPlay').textContent !== '▶'", 5)
    btn = c.js("[document.getElementById('tlPlay').textContent, document.getElementById('tlPlay').getAttribute('aria-label')]")
    c.click("#screen", check=False)
    c.wait_for("document.getElementById('vid').paused && document.getElementById('tlPlay').textContent === '▶'", 5)
    btn2 = c.js("[document.getElementById('tlPlay').textContent, document.getElementById('tlPlay').getAttribute('aria-label')]")
    case("a press on the preview plays, and the round button says Pause; another press pauses, and it says Play", btn == ["❚❚", "Pause"] and btn2 == ["▶", "Play"], (btn, btn2))
    at(P[0]["from"] + 0.05)
    c.click("#tlPlay", check=False)
    c.wait_for("!document.getElementById('vid').paused", 5)
    case("the round button on the timeline plays too", not paused())
    c.key("Space")
    c.wait_for("document.getElementById('vid').paused", 5)
    time.sleep(0.3)
    case("the spacebar pauses (and the button it was pressed on is not pressed again by it)", paused() and c.js("document.activeElement === document.body"))
    at(P[0]["from"] + 0.05)
    c.key("Space")
    c.wait_for("!document.getElementById('vid').paused", 5)
    playing = not paused()
    pause()
    case("...and plays", playing)
    c.js("window.Talk.openPick(0, 1)")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    c.key("Space")
    time.sleep(0.3)
    case("her fault, fixed: the spacebar does nothing while a picker is open (hers played the talking video behind it)", paused())
    c.js("window.Talk.closePick()")

    # a sped-up piece plays at its speed; the speed is put back to 1 on pause
    save_js({"speeds": [{"a": 6, "b": 12, "v": 2}]})
    P2 = pieces()
    at(P2[1]["from"] + 0.02)
    c.js("window.__rates.length = 0; window.Talk.togglePlay()")
    c.wait_for("window.__rates.indexOf(2) >= 0", 8, tell="JSON.stringify(window.__rates)")
    pause()
    c.wait_for("document.getElementById('vid').playbackRate === 1", 5)
    time.sleep(0.15)
    rates = c.js("[window.__rates, document.getElementById('vid').playbackRate]")
    case("in the cut version a sped-up piece plays at its speed, and the speed is put back to 1 on pause", 2 in rates[0] and rates[0][-1] == 1 and rates[1] == 1, rates)
    save_js({"speeds": []})

    # the cut version skips what is cut, and stops at the end of the reel, back at the first piece
    save_js({"cut": [[6, 12]]})
    P3 = pieces()
    at(P3[0]["to"] - 0.25)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    time.sleep(0.15)
    c.js("window.__seeks.length = 0; window.Talk.togglePlay()")
    c.wait_for("!document.getElementById('vid').paused", 5)
    c.wait_for("document.getElementById('vid').paused", 15, tell="document.getElementById('vid').currentTime")
    c.wait_for("!document.getElementById('vid').seeking", 5)
    end = c.js("[window.__seeks, document.getElementById('vid').currentTime, document.getElementById('vid').ended]")
    case("Play the cut version: what is cut is skipped (it jumps to the next piece kept)", len(P3) == 2 and any(abs(x - P3[1]["from"]) < 0.002 for x in end[0]), (end, P3))
    case("...and at the end of the reel it pauses and goes back to the first piece", abs(end[1] - P3[0]["from"]) < 0.002 and not end[2], end)
    at(1.5)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    time.sleep(0.15)
    c.js("window.__seeks.length = 0; window.Talk.togglePlay()")
    c.wait_for("window.__seeks.length >= 1", 5)
    sk = c.js("window.__seeks")
    pause()
    case("on a cut word, play starts at the next piece kept", abs(sk[0] - P3[1]["from"]) < 0.002, sk)
    c.click("#cutMode")
    at(P3[0]["to"] - 0.1)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    time.sleep(0.15)
    c.js("window.__seeks.length = 0; window.__rates.length = 0; window.Talk.togglePlay()")
    c.wait_for("document.getElementById('vid').currentTime > %r" % (P3[0]["to"] + 0.25), 8, tell="document.getElementById('vid').currentTime")
    pause()
    whole = c.js("[window.__seeks, window.__rates.filter(function(r){ return r !== 1; }), document.getElementById('cutMode').checked]")
    case("with Play the cut version unticked the whole video plays, through what is cut, at its own speed", whole == [[], [], False], whole)
    c.click("#cutMode")
    save_js({"cut": []})

    # ---- every spot, with her default numbers
    def stretch(**more):
        x = {"a": 1, "b": 3, "ns": [1], "v": None, "from": 0, "spot": "full", "pos": None, "me": None}
        x.update(more)
        return x
    mid = WORDS[2]["start"] + 0.01
    save_js({"shots": [stretch()]})
    at(mid)
    c.wait_for("window.__pic().loaded", 10, tell="JSON.stringify(window.__pic())")
    pic = c.js("window.__pic()")
    case("Full screen: the photo fills the screen (its larger small copy, by its number), with no handle and nothing to move",
         box_is(rel("#phFront"), 0, 0, 1, 1) and pic["img"] and not pic["vid"] and "/kit-photo?" in pic["src"] and "&n=1&size=l" in pic["src"]
         and not pic["movable"] and not pic["pip"] and not rel("#phKnob")["shown"] and not rel("#meKnob")["shown"], (rel("#phFront"), pic))
    at(WORDS[5]["start"] + 0.01)
    case("...and off its words it is gone", not c.js("window.__pic().wrap"))
    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    tall = 0.704 * 9 / 16 * 30 / 24
    k = rel("#phKnob")
    case("Center: 70.4% wide, its middle at 50% across and 44% down, its height from the photo's own shape; its round handle on its bottom right corner",
         box_is(rel("#phFront"), 0.5 - 0.352, 0.44 - tall / 2, 0.704, tall) and c.js("window.__pic().movable") and k["shown"] and near(k["cx"], 0.852) and near(k["cy"], 0.44 + tall / 2), (rel("#phFront"), k))
    save_js({"shots": [stretch(spot="corner")]})
    at(mid)
    tall = 0.352 * 9 / 16 * 30 / 24
    case("Small corner: 35.2% wide, 4.6% from the right and 7.3% from the top", box_is(rel("#phFront"), 1 - 0.046 - 0.352, 0.073, 0.352, tall) and c.js("window.__pic().movable"), rel("#phFront"))
    save_js({"shots": [stretch(spot="corner", ns=[2])]})
    at(mid)
    wide = 0.352 * 9 / 16 * 40 / 60
    k = rel("#phKnob")
    case("...a wide photo there is as wide and less tall, its handle still on its bottom right corner",
         box_is(rel("#phFront"), 1 - 0.046 - 0.352, 0.073, 0.352, wide) and near(k["cx"], 1 - 0.046) and near(k["cy"], 0.073 + wide), (rel("#phFront"), k))
    save_js({"shots": [stretch(spot="pip")], "zooms": [{"a": 1, "b": 3, "kind": "punch"}]})
    at(mid)
    me = capcut.ME_DEFAULT
    v, k, pic = rel("#vid"), rel("#meKnob"), c.js("window.__pic()")
    case("Full screen, you in the corner: the photo fills the screen and they are a box 36% of the screen wide and 36% tall, 50 px from the left and 60 px from the bottom of a 1080x1920 frame, with its own handle",
         pic["pip"] and box_is(rel("#phFront"), 0, 0, 1, 1) and box_is(v, 50 / 1080, 1 - 60 / 1920 - 0.36, 0.36, 0.36) and near(k["cx"], me["x"] + 0.18) and near(k["cy"], me["y"] + 0.18)
         and c.js("document.getElementById('vid').classList.contains('movable')") and not rel("#phKnob")["shown"], (v, k, pic))
    case("...and a zoom is not shown while they are in the corner", c.js("document.getElementById('vid').style.transform") == "")
    save_js({"shots": [stretch()]})
    at(mid)
    case("the same punch in with the photo full screen: 1.15", c.js("window.__scale()") == 1.15 and box_is({**rel("#phFront")}, 0, 0, 1, 1), c.js("document.getElementById('vid').style.transform"))
    at(WORDS[5]["start"] + 0.01)
    back = c.js("(function(){ var v = document.getElementById('vid'), cs = getComputedStyle(v); return [v.style.left, v.style.width, document.getElementById('screen').classList.contains('pip'), cs.transitionDuration, cs.transformOrigin, v.offsetWidth, v.offsetHeight, window.__scale()]; })()")
    ox, oy = [float(x.replace("px", "")) for x in back[4].split()[:2]]
    case("off those words they fill the screen again, with no zoom; the zoom turns around 50% 45% and eases over a quarter of a second",
         back[:4] == ["", "", False, "0.25s"] and abs(ox - back[5] * 0.5) < 0.6 and abs(oy - back[6] * 0.45) < 0.6 and back[7] == 1, back)

    # several photos flash through the stretch, each for an equal share of its time on the reel
    save_js({"shots": [stretch(ns=[3, 1, 2])], "zooms": []})
    srcs = c.js("(function(){ var T = window.Talk, x = T.findShot(1), sp = T.shotSpan(x), out = [];"
                " [0.02, 0.5, 0.98, 1.02, 1.5, 1.98, 2.02, 2.5, 2.98].forEach(function(f){ window.__at(T.srcAt(sp[0] + (sp[1] - sp[0]) * f / 3)); out.push(+/[?&]n=(\\d+)/.exec(window.__pic().src)[1]); });"
                " return [out, T.pieceAt(T.srcAt(sp[0])), sp]; })()")
    case("several photos on one stretch flash through it in their order, each for an equal share of the stretch's time on the reel",
         srcs[0] == [3, 3, 3, 1, 1, 1, 2, 2, 2], srcs)
    save_js({"cut": [[1, 5]]})
    at(0.45)          # past the first word's own 0.3 s, so the first word found there is one of the stretch's
    out = c.js("[window.Talk.pieceAt(0.45), window.__pic().wrap, /[?&]n=(\\d+)/.exec(window.__pic().src)[1]]")
    case("on words that are cut (seen with the whole video), the stretch's first photo shows", out == [-1, True, "3"], out)
    save_js({"cut": []})

    # ---- the zooms
    save_js({"shots": [], "zooms": [{"a": 13, "b": 16, "kind": "zoom"}]})
    z = c.js("(function(){ var T = window.Talk, p = T.P().filter(function(q){ return q.zoom === 0; }), a = p[0].at, b = p[p.length - 1].at + p[p.length - 1].dur, out = [];"
             " [0, 0.5, 0.999].forEach(function(f){ window.__at(T.srcAt(a + (b - a) * f)); out.push(window.__scale()); }); return [out, T.zoomSpan(0), [a, b]]; })()")
    case("a slow zoom grows from 1 to 1.12 across its whole span", near(z[0][0], 1.0, 0.002) and near(z[0][1], 1.06, 0.002) and near(z[0][2], 1.12, 0.002) and z[1] == z[2], z)
    save_js({"cut": [[13, 16]]})
    at(WORDS[14]["start"] + 0.01)
    outside = c.js("window.__scale()")
    save_js({"zooms": [{"a": 13, "b": 16, "kind": "punch"}]})
    at(WORDS[14]["start"] + 0.01)
    case("outside a piece (those words cut, the whole video showing) a slow zoom shows 1.06 and a punch in 1.15", outside == 1.06 and c.js("window.__scale()") == 1.15, outside)
    save_js({"cut": [], "zooms": []})

    # ---- captions
    def cap():
        return c.js("(function(){ var e = document.getElementById('cap'), k = document.getElementById('capKnob'), r = e.getBoundingClientRect(), q = k.getBoundingClientRect(), cs = getComputedStyle(e);"
                    " return {text: e.textContent, kids: e.children.length, size: parseFloat(cs.fontSize), shown: cs.display !== 'none', knob: getComputedStyle(k).display !== 'none',"
                    " kx: q.left + q.width / 2 - r.right, ky: q.top + q.height / 2 - r.bottom, h: document.getElementById('screen').clientHeight}; })()")
    at(WORDS[3]["start"] + 0.02)
    cp, r = cap(), rel("#cap")
    case("captions: the word being said, one word, in the middle 71% down, its size the screen's height x 0.035",
         cp["text"] == "we" and cp["shown"] and near(cp["size"], cp["h"] * 0.035, 0.05) and near(r["cx"], 0.5) and near(r["cy"], 0.71), (cp, r))
    case("...its round handle sits on the word's bottom right corner", cp["knob"] and abs(cp["kx"]) < 1 and abs(cp["ky"]) < 1, cp)
    at(WORDS[2]["start"] + 0.02)
    cp = cap()
    case("a word with a tag in it is text on the preview, never HTML", cp["text"] == "<b>bold</b>" and cp["kids"] == 0, cp)
    at(WORDS[10]["start"] + 0.02)
    one = cap()["text"]
    at(WORDS[11]["start"] + 0.02)
    case("\"you\" and \"'re\" are one caption, \"you're\" (hers showed \"you 're\")", one == "you're" and cap()["text"] == "you're", one)
    at(0.0)
    cp = cap()
    case("with no word showing (before the first is said) there is no caption and no handle", cp["text"] == "" and not cp["shown"] and not cp["knob"], cp)
    # No captions / Captions on
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    c.click("#capOff")
    moved(was)
    chips = c.js("[document.getElementById('capOn').classList.contains('on'), document.getElementById('capOff').classList.contains('on'), document.getElementById('capOff').getAttribute('aria-pressed'), document.getElementById('sum').textContent]")
    case("No captions: off in the record, the chip lit, nothing on the preview, and the make bar says \"captions off\"",
         rec().get("captions") is False and chips[:3] == [False, True, "true"] and chips[3].endswith("captions off") and cap()["text"] == "" and not cap()["knob"], chips)
    was = rev()
    c.click("#capOn")
    moved(was)
    case("Captions on: back", rec().get("captions") is True and cap()["text"] == "we" and c.js("document.getElementById('capOn').classList.contains('on')"))
    # drag the caption
    undo0 = c.js("window.Talk.UNDO.length")
    was = rev()
    bx = drag_by("#cap", 30, -40)
    now = rel("#cap")
    moved(was)
    want = {"x": 0.5 + 30 / bx["w"], "y": 0.71 - 40 / bx["h"]}
    got = rec().get("cap_pos") or {}
    case("drag the word on the preview: the captions go where it was dropped (as parts of the screen), one Undo step, and it never jumps back while the save is on its way",
         near(got.get("x"), want["x"], 0.0003) and near(got.get("y"), want["y"], 0.0003) and near(now["cx"], want["x"]) and near(now["cy"], want["y"])
         and near(rel("#cap")["cx"], want["x"]) and c.js("window.Talk.UNDO.length") == undo0 + 1, (got, want, now))
    case("...the press that ended the drag did not play the video, and \"Put the captions back to how they were\" is there now", paused() and not c.js("document.getElementById('capReset').hidden"))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    r = c.rect("#cap")
    b = scr()
    c.drag((r["cx"], r["cy"]), (b["right"] + 25, b["bottom"] + 25), steps=6, check=False)
    moved(was)
    far = rec().get("cap_pos")
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    r = c.rect("#cap")
    c.drag((r["cx"], r["cy"]), (b["x"] - 25, r["cy"]), steps=6, check=False)
    moved(was)
    case("the caption's spot is held to 2% to 98% of the screen", far == {"x": 0.98, "y": 0.98} and rec().get("cap_pos") == {"x": 0.02, "y": 0.98}, (far, rec().get("cap_pos")))
    save_js({"cap_pos": {"x": 0.5, "y": 0.5}})
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    bx = drag_by("#capKnob", 20, 10)
    moved(was)
    want = round(min(3, max(0.4, 1 * (1 + (20 / bx["w"] + 10 / bx["h"]) * 3))), 2)
    cp = cap()
    case("drag the caption's round handle right or down: bigger, by start x (1 + (dx + dy) x 3), rounded to 0.01; the word on the preview follows",
         near(rec().get("cap_size"), want, 0.0101) and want > 1.1 and near(cp["size"], cp["h"] * 0.035 * rec()["cap_size"], 0.06), (rec().get("cap_size"), want, cp))
    was = rev()
    drag_by("#capKnob", 0.4 * b["w"], 0.33 * b["h"])
    moved(was)
    big = rec().get("cap_size")
    c.wait_for("window.Talk.previewHeld() === null", 5)
    at(WORDS[3]["start"] + 0.02)
    was = rev()
    drag_by("#capKnob", -0.2 * b["w"], -0.2 * b["h"])
    moved(was)
    case("...held to 0.4 to 3", big == 3 and rec().get("cap_size") == 0.4, (big, rec().get("cap_size")))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    tiny_press("#cap")
    time.sleep(0.4)
    case("a press on the caption that moves under 3 px is a click: nothing is saved, and it neither plays nor pauses", rev() == was and paused())
    was = rev()
    c.click("#capReset")
    moved(was)
    cp, r = cap(), rel("#cap")
    case("Put the captions back to how they were: the spot and the size as they started, and the button goes",
         rec().get("cap_pos") is None and rec().get("cap_size") == 1 and c.js("document.getElementById('capReset').hidden") and near(r["cx"], 0.5) and near(r["cy"], 0.71)
         and near(cp["size"], cp["h"] * 0.035, 0.05), (rec().get("cap_pos"), rec().get("cap_size"), r))
    save_js({"captions": False})          # out of the way of the photo drags below

    # ---- dragging a photo
    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    c.wait_for("window.__pic().loaded", 10)
    c.js("window.Talk.SELSHOT = null; window.Talk.markShot()")
    undo0 = c.js("window.Talk.UNDO.length")
    was = rev()
    bx = drag_by("#phFront", -40, 30)
    now = rel("#phFront")
    moved(was)
    want = {"x": 0.5 - 40 / bx["w"], "y": 0.44 + 30 / bx["h"], "w": 0.704}
    got = shot(1)["pos"] or {}
    tall = 0.704 * 9 / 16 * 30 / 24
    case("drag a photo in Center: it goes where it was dropped, the same size (its middle and width as parts of the screen), one Undo step",
         all(near(got.get(k_), want[k_], 0.0003) for k_ in want) and near(now["cx"], want["x"]) and near(now["cy"], want["y"]) and near(now["w"], 0.704)
         and c.js("window.Talk.UNDO.length") == undo0 + 1, (got, want, now))
    k = rel("#phKnob")
    case("...its handle goes with it, the press that ended the drag did not play, and the stretch is the one picked (its bar lit in the script)",
         near(k["cx"], want["x"] + 0.352) and near(k["cy"], want["y"] + tall / 2) and paused() and c.js("window.Talk.SELSHOT") == 1
         and c.js("document.querySelectorAll('#script .seg.on[data-a=\"1\"]').length") == 3, k)
    c.wait_for("window.Talk.previewHeld() === null", 5)
    before = rel("#phFront")
    was = rev()
    bx = drag_by("#phKnob", 50, 0)
    moved(was)
    after, got = rel("#phFront"), shot(1)["pos"]
    case("drag its round handle: bigger by the distance dragged, its top left corner staying put",
         near(got["w"], 0.704 + 50 / bx["w"], 0.0003) and near(after["l"], before["l"], 0.004) and near(after["t"], before["t"], 0.004) and near(after["w"], got["w"])
         and near(after["h"], got["w"] * 9 / 16 * 30 / 24), (got, before, after))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    drag_by("#phKnob", -0.9 * b["w"], 0)
    moved(was)
    small, after2 = shot(1)["pos"]["w"], rel("#phFront")
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    drag_by("#phKnob", 1.7 * b["w"], 0)
    moved(was)
    case("...a photo's width is held to 10% to 160% of the screen, the corner still where it was",
         small == 0.1 and shot(1)["pos"]["w"] == 1.6 and near(after2["l"], before["l"], 0.004) and near(after2["t"], before["t"], 0.004)
         and near(rel("#phFront")["l"], before["l"], 0.004), (small, shot(1)["pos"], after2))
    save_js({"shots": [stretch(spot="corner", ns=[2])]})
    at(mid)
    c.js("window.Talk.SELSHOT = null; window.Talk.markShot()")
    was = rev()
    tiny_press("#phFront")
    time.sleep(0.4)
    case("a press on a photo that moves under 3 px is a click: nothing saved, nothing played; it picks the stretch",
         rev() == was and paused() and shot(1)["pos"] is None and c.js("window.Talk.SELSHOT") == 1 and c.js("document.querySelectorAll('#script .seg.on').length") == 3)
    was = rev()
    bx = drag_by("#phFront", -30, 25)
    moved(was)
    want = capcut.default_place("corner", 60, 40)
    got = shot(1)["pos"]
    case("a photo in Small corner moves too, from where it sat by itself",
         near(got["x"], want["x"] - 30 / bx["w"], 0.0003) and near(got["y"], want["y"] + 25 / bx["h"], 0.0003) and near(got["w"], 0.352, 1e-6), (got, want))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    save_js({"shots": [stretch()]})
    at(mid)
    was = rev()
    drag_by("#phFront", 40, 30)
    time.sleep(0.5)
    case("a photo that is Full screen can't be moved: a drag on it saves nothing", rev() == was and shot(1)["pos"] is None)
    pause()

    # ---- themselves in the corner
    save_js({"shots": [stretch(spot="pip")]})
    at(mid)
    was = rev()
    bx = drag_by("#vid", 30, -90)
    now = rel("#vid")
    moved(was)
    got = shot(1)
    want = {"x": me["x"] + 30 / bx["w"], "y": me["y"] - 90 / bx["h"], "w": 0.36}
    case("drag themselves in the corner: they go where they were dropped; the photo is not moved",
         all(near(got["me"][k_], want[k_], 0.0003) for k_ in want) and got["pos"] is None and near(now["cx"], want["x"]) and near(now["cy"], want["y"]) and paused(), (got, want, now))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    before = rel("#vid")
    was = rev()
    bx = drag_by("#meKnob", 40, 0)
    moved(was)
    after, got = rel("#vid"), shot(1)["me"]
    case("their round handle: bigger by the distance dragged, as wide a share of the screen as it is tall a share, the top left corner staying put",
         near(got["w"], 0.36 + 40 / bx["w"], 0.0003) and near(after["l"], before["l"], 0.004) and near(after["t"], before["t"], 0.004) and near(after["w"], got["w"]) and near(after["h"], got["w"]), (got, before, after))
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    drag_by("#meKnob", -0.9 * b["w"], 0)
    moved(was)
    small = shot(1)["me"]["w"]
    c.wait_for("window.Talk.previewHeld() === null", 5)
    was = rev()
    drag_by("#meKnob", 1.2 * b["w"], 0)
    moved(was)
    case("...held to 12% to 100% of the screen", small == 0.12 and shot(1)["me"]["w"] == 1, (small, shot(1)["me"]))
    c.wait_for("window.Talk.previewHeld() === null", 5)

    # ---- ours: the look waits during a drag; a drag let go over a change from the chat wipes nothing; a cancelled drag saves nothing
    save_js({"shots": [stretch(spot="center")]})
    at(mid)
    r = c.rect("#phFront")
    c.drag((r["cx"], r["cy"]), (r["cx"] + 30, r["cy"] + 20), steps=4, release=False, check=False)
    during = c.js("[window.Talk.quiet(), !!window.Talk.previewDrag(), window.Talk.previewDrag().a, window.Talk.previewDrag().x === undefined]")
    s.cut(KIT, [[13, 16]])
    was = rev()
    c.mouse_release()
    moved(was)
    case("the 3-second look waits while a hand drags on the preview, and the drag holds the stretch's start word, never the stretch itself", during == [False, True, 1, True], during)
    case("a drag let go after the assistant cut in the chat does not wipe the cut: the save is refused in plain words, the cut is on the page, and the photo is where it was",
         rec().get("cut") == [[13, 16]] and shot(1)["pos"] is None and t.toast(c) == s.TR.NEWER and "cut" in c.js("window.Talk.wordEl(14).className")
         and c.js("window.Talk.previewHeld()") is None and box_is(rel("#phFront"), 0.148, 0.44 - 0.704 * 9 / 16 * 30 / 24 / 2, 0.704, 0.704 * 9 / 16 * 30 / 24), (rec().get("cut"), shot(1), t.toast(c)))
    save_js({"cut": []})
    at(mid)
    was = rev()
    r = c.rect("#phFront")
    c.drag((r["cx"], r["cy"]), (r["cx"] + 30, r["cy"] + 20), steps=4, release=False, check=False)
    moved_to = rel("#phFront")
    c.js("document.dispatchEvent(new Event('contextmenu'))")
    gone = c.js("[!!window.Talk.previewDrag(), window.Talk.previewHeld()]")
    c.mouse_release()
    time.sleep(0.5)
    case("a drag that is cancelled (the Mac's own menu came up) saves nothing: the photo is back where it was, and letting go neither saves nor plays",
         near(moved_to["cx"], 0.5 + 30 / b["w"]) and gone == [False, None] and rev() == was and shot(1)["pos"] is None and near(rel("#phFront")["cx"], 0.5) and paused(), (moved_to, gone))
    c.click("#screen", fx=0.5, fy=0.92, check=False)
    c.wait_for("!document.getElementById('vid').paused", 5)
    playing = not paused()
    pause()
    case("...and the next press on the preview plays as always (no press is ever swallowed for good)", playing)

    # ---- the spacebar and the keyboard (a Center photo is on words 1 to 3)
    if rec().get("captions") is False:
        save_js({"captions": True})
    at(P[0]["from"] + 0.05)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    c.js("document.getElementById('capOn').focus()")
    c.key("Tab")
    foot = c.js("[document.activeElement.id, true]")
    was = rev()
    c.key("Space")
    try:
        moved(was, 5)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.2)
    a1 = [foot, rec().get("captions"), paused(), c.js("document.getElementById('vid').currentTime") < P[0]["from"] + 0.1]
    case("ours: a button reached with the keyboard is pressed by the spacebar (Tab to Captions off, Space: the captions are off), and nothing plays",
         a1 == [["capOff", True], False, True, True], a1)
    pause()
    save_js({"captions": True})
    at(P[0]["from"] + 0.05)
    c.js("document.getElementById('guidesOn').focus()")
    c.key("Tab")
    foot = c.js("[document.activeElement.id, true]")
    c.key("Space")
    time.sleep(0.3)
    a2 = [foot, c.js("document.getElementById('cutMode').checked"), paused()]
    pause()
    c.js("var m = document.getElementById('cutMode'); if (!m.checked) m.click(); if (document.activeElement) document.activeElement.blur();")
    case("...and a tick reached with the keyboard is unticked by it (Play the cut version), and nothing plays", a2 == [["cutMode", True], False, True], a2)
    at(mid)
    c.js("window.Talk.openMenu(1, 0, document.querySelector('#script .seg'))")
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    c.key("Space")
    time.sleep(0.3)
    a3 = [paused(), c.js("document.getElementById('pmenu').classList.contains('open')")]
    pause()
    c.js("window.Talk.closeMenu()")
    c.key("Space")
    try:
        c.wait_for("!document.getElementById('vid').paused", 5)
    except Exception:  # noqa: BLE001
        pass
    a3.append(not paused())
    pause()
    case("...the spacebar never plays the video behind the open photo menu (the menu stays); with the menu closed it plays again", a3 == [True, True, True], a3)

    # ---- the talking video itself runs out (the last piece kept goes to its very end)
    at(P[1]["from"] + 0.1)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    c.js("document.getElementById('vid').dispatchEvent(new Event('ended'))")
    c.wait_for("!document.getElementById('vid').seeking", 5)
    e1 = c.js("document.getElementById('vid').currentTime")
    c.js("document.getElementById('cutMode').checked = false")
    at(P[1]["from"] + 0.1)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    c.js("document.getElementById('vid').dispatchEvent(new Event('ended'))")
    time.sleep(0.2)
    e2 = c.js("document.getElementById('vid').currentTime")
    c.js("document.getElementById('cutMode').checked = true")
    case("when the talking video itself ends in the cut version, the time goes back to the first piece; with the whole video playing it stays where it ended",
         abs(e1 - P[0]["from"]) < 0.002 and abs(e2 - (P[1]["from"] + 0.1)) < 0.002, (e1, e2, P[0]["from"]))

    # ---- a photo that could not be loaded: nothing shows, and it is asked for again by itself
    at(mid)
    c.wait_for("window.__pic().loaded && window.__pic().movable", 10, tell="JSON.stringify(window.__pic())")
    n0 = len([r_ for r_ in list(c.requests) if "/kit-photo" in r_["url"] and "size=l" in r_["url"]])
    c.js("document.querySelector('#phFront img').dispatchEvent(new Event('error'))")
    time.sleep(0.4)
    lost = c.js("[window.__pic().wrap, window.__pic().movable, window.__rel('#phKnob').shown]")
    n1 = len([r_ for r_ in list(c.requests) if "/kit-photo" in r_["url"] and "size=l" in r_["url"]])
    try:
        c.wait_for("window.__pic().wrap && window.__pic().img && window.__pic().loaded && window.__pic().movable && window.__rel('#phKnob').shown", 9)
    except Exception:  # noqa: BLE001
        pass
    back = c.js("[window.__pic().wrap, window.__pic().img, window.__pic().movable, window.__rel('#phKnob').shown]")
    case("ours: a photo that could not be loaded shows nothing, with no box to move and no handle; it is not asked for on every frame, and it is back by itself a few seconds later, with no reload",
         lost == [False, False, False] and n1 == n0 and back == [True, True, True, True], (lost, n0, n1, back))

    # ---- a Footage video on a stretch: without its sound, in step with the reel
    (kit / "Footage").mkdir(exist_ok=True)
    f = kit / "Footage" / FOOT
    shutil.copyfile(str(t.FIXTURE), str(f))
    old = time.time() - 7200
    os.utime(str(f), (old, old))                       # not "still being copied in"
    vkey = s.video.key(f)
    code, _j, _raw, _h = s.http("GET", "/reel-video" + s.q(KIT) + "&key=" + vkey, headers={"Range": "bytes=0-99"})
    if code not in (200, 206):
        skip("a Footage video on the preview: this computer would have to make a small copy first (%s)" % code)
    else:
        # the first ask fails (the file is away for a moment; the 3-second look is held so the state never says "gone")
        def asks():
            return len([r_ for r_ in list(c.requests) if "/reel-video" in r_["url"] and vkey in r_["url"]])
        at(WORDS[0]["start"])
        save_js({"shots": [{"a": 6, "b": 9, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 0.5, "spot": "center", "pos": None, "me": None}]})
        c.js("window.__hold = true; if (!window.__held) { window.__held = true; window.Talk.busy(function(){ return !!window.__hold; }); }")
        away = kit / ".kit" / "bts-away.tmp"
        os.rename(str(f), str(away))
        at(WORDS[6]["start"] + 0.01)
        time.sleep(1.5)
        lost = c.js("[window.__pic().wrap, window.__pic().movable, window.__rel('#phKnob').shown, window.__pic().vid]")
        k1 = asks()
        time.sleep(1.0)
        k2 = asks()
        os.rename(str(away), str(f))
        try:
            c.wait_for("document.getElementById('bvid').readyState >= 2 && window.__pic().vid && window.__pic().movable && window.__rel('#phKnob').shown", 14)
        except Exception:  # noqa: BLE001
            pass
        back = c.js("[window.__pic().vid, window.__pic().movable, window.__rel('#phKnob').shown]")
        c.js("window.__hold = false")
        case("ours: a Footage video that could not be loaded the first time shows nothing (no empty box to move, no handle) and is not asked for on every frame; once it can be played it shows by itself, with no reload",
             s.video.key(f) == vkey and lost == [False, False, False, False] and k1 >= 1 and k2 == k1 and back == [True, True, True], (lost, k1, k2, back))
        save_js({"shots": [{"a": 6, "b": 9, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 0.5, "spot": "full", "pos": None, "me": None}]})
        at(WORDS[6]["start"] + 0.01)
        c.wait_for("document.getElementById('bvid').readyState >= 2 && !document.getElementById('bvid').seeking && window.__pic().vid", 15,
                   tell="JSON.stringify([document.getElementById('bvid').readyState, window.__pic()])")
        at(WORDS[6]["start"] + 0.01)
        c.wait_for("!document.getElementById('bvid').seeking", 5)
        got = c.js("(function(){ var T = window.Talk, b = document.getElementById('bvid'), x = T.findShot(6), sp = T.shotSpan(x), R = T.reelAt(document.getElementById('vid').currentTime);"
                   " return [window.__pic(), b.muted, b.currentTime, 0.5 + Math.max(0, R - sp[0]), b.paused, b.videoWidth, b.videoHeight]; })()")
        case("a video on a stretch: the Footage video itself shows (played from this computer by its key, never the Footage list), without its sound, from where they said it starts",
             got[0]["vid"] and not got[0]["img"] and got[0]["vsrc"] == "/reel-video?" + c.js("window.Talk.Q") + "&key=" + vkey and got[1] is True
             and abs(got[2] - got[3]) <= 0.35 and got[4] and box_is(rel("#phFront"), 0, 0, 1, 1), got)
        c.js("document.getElementById('bvid').currentTime = 2.4")
        c.wait_for("!document.getElementById('bvid').seeking", 5)
        c.js("window.Talk.frame()")
        c.wait_for("!document.getElementById('bvid').seeking", 5)
        t2 = c.js("document.getElementById('bvid').currentTime")
        c.js("document.getElementById('bvid').currentTime = %r; " % (got[3] + 0.2))
        c.wait_for("!document.getElementById('bvid').seeking", 5)
        c.js("window.Talk.frame()")
        time.sleep(0.2)
        t3 = c.js("document.getElementById('bvid').currentTime")
        case("...kept in step with the reel: more than 0.35 s out and it is set again; less, and it is left alone", abs(t2 - got[3]) < 0.02 and abs(t3 - (got[3] + 0.2)) < 0.02, (t2, t3, got[3]))
        c.js("window.Talk.togglePlay()")
        c.wait_for("!document.getElementById('vid').paused && !document.getElementById('bvid').paused", 8)
        both = c.js("[!document.getElementById('vid').paused, !document.getElementById('bvid').paused]")
        pause()
        c.wait_for("document.getElementById('bvid').paused", 5)
        case("...it plays while the talking video plays and stops when it stops", both == [True, True] and c.js("document.getElementById('bvid').paused"), both)

        # a Footage video shorter than the words it sits on: it stays on its last frame
        save_js({"shots": [{"a": 0, "b": 16, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 2.6, "spot": "full", "pos": None, "me": None}]})
        c.js("document.getElementById('cutMode').checked = false")
        at(WORDS[0]["start"])
        c.wait_for("document.getElementById('bvid').readyState >= 2 && !document.getElementById('bvid').seeking && !document.getElementById('vid').seeking", 10)
        c.js("window.Talk.frame()")
        c.wait_for("!document.getElementById('bvid').seeking", 5)
        c.js("(function(){ var b = document.getElementById('bvid'); window.__bv = {seeks: 0, plays: 0};"
             " if (b.__w) return; b.__w = true;"
             " b.addEventListener('seeking', function(){ window.__bv.seeks++; });"
             " b.addEventListener('play', function(){ window.__bv.plays++; }); })()")
        c.js("window.Talk.togglePlay()")
        try:
            c.wait_for("document.getElementById('vid').currentTime > 1.7", 10)
        except Exception:  # noqa: BLE001
            pass
        ran = c.js("[document.getElementById('vid').currentTime, !document.getElementById('vid').paused, document.getElementById('bvid').paused, window.__pic().vid]")
        pause()
        end = c.js("[window.__bv, document.getElementById('bvid').currentTime, document.getElementById('bvid').duration]")
        c.js("document.getElementById('cutMode').checked = true")
        case("her fault, fixed: a Footage video shorter than the words it sits on stays on its last frame while the talking goes on (never started again and thrown back to its end, over and over)",
             ran[0] > 1.7 and ran[1] and ran[2] and ran[3] and end[0]["seeks"] == 0 and end[0]["plays"] <= 1 and end[1] >= end[2] - 0.1, (ran, end))
        save_js({"shots": [{"a": 6, "b": 9, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 0.5, "spot": "full", "pos": None, "me": None}]})
        save_js({"shots": [{"a": 6, "b": 9, "ns": [], "v": {"key": vkey, "name": FOOT}, "from": 0.5, "spot": "corner", "pos": None, "me": None}]})
        at(WORDS[6]["start"] + 0.01)
        hv = 0.352 * 9 / 16 * got[6] / got[5]
        case("a video in Small corner takes its height from the video's own shape", got[5] > 0 and box_is(rel("#phFront"), 1 - 0.046 - 0.352, 0.073, 0.352, hv), (rel("#phFront"), got[5], got[6]))
        f.unlink()
        c.js("window.Talk.poll(true)")
        c.wait_for("window.Talk.SH.length === 1 && window.Talk.SH[0].v && window.Talk.SH[0].v.gone === true", 10, tell="JSON.stringify(window.Talk.SH)")
        at(WORDS[6]["start"] + 0.01)
        case("a video that has gone from the Footage folder shows nothing on the preview (never an empty box), and its stretch is still in the record",
             not c.js("window.__pic().wrap") and c.js("document.getElementById('bvid').paused") and (shot(6) or {}).get("v") == FOOT, c.js("window.__pic()"))
    save_js({"shots": []})

    # ---- phone guides
    c.click("#guidesOn")
    g = {k_: rel(k_) for k_ in (".g-top", ".g-side", ".g-bottom", ".g-nav")}
    case("Phone guides, at her percentages: the top 10%; the side column 14% wide from half way down to 9% from the bottom; the name and caption area 15% tall above the bottom 7%, stopping 14% from the right; the bottom bar 7%",
         not c.js("document.getElementById('guides').hidden") and box_is(g[".g-top"], 0, 0, 1, 0.10) and box_is(g[".g-side"], 0.86, 0.5, 0.14, 0.41)
         and box_is(g[".g-bottom"], 0, 0.78, 0.86, 0.15) and box_is(g[".g-nav"], 0, 0.93, 1, 0.07), g)
    labels = c.js("[document.querySelector('.g-top b').textContent, Array.from(document.querySelectorAll('.g-side i')).map(function(e){ return e.textContent; }), document.querySelector('.g-user b').textContent,"
                  " document.querySelector('.g-user em').textContent, document.querySelector('.g-audio').textContent, document.getElementById('guidesOn').parentNode.title, localStorage.getItem('talkGuides'),"
                  " getComputedStyle(document.getElementById('guides')).pointerEvents]")
    case("...with her mock labels, her tooltip, remembered under talkGuides, and never in the way of a press",
         labels == ["Reels", ["1,204", "36", "18"], "yourname", "Follow", "♫ Original audio", "Shows what Instagram covers on a reel", "1", "none"], labels)
    at(P[0]["from"] + 0.05)
    c.click("#screen", fx=0.5, fy=0.05, check=False)
    c.wait_for("!document.getElementById('vid').paused", 5)
    playing = not paused()
    pause()
    case("a press on the preview still plays with the guides showing", playing)
    c.click("#cutMode")
    unticked = c.js("document.getElementById('cutMode').checked")
    c.reload()
    c.wait_for("window.Talk && window.Talk.loaded && document.querySelectorAll('#script .sent').length === 3", 15)
    again = c.js("[document.getElementById('cutMode').checked, document.getElementById('guidesOn').checked, document.getElementById('guides').hidden]")
    case("after a reload the phone guides are still on (this browser remembers) and Play the cut version is ticked again (it is remembered nowhere)",
         unticked is False and again == [True, True, False], (unticked, again))
    c.js("window.__watch(); document.getElementById('screen').scrollIntoView({block: 'center'})")
    c.click("#guidesOn")
    case("untick it: the guides go, and that is remembered too", c.js("[document.getElementById('guides').hidden, localStorage.getItem('talkGuides')]") == [True, "0"])
    under = c.js("Array.from(document.querySelector('.controls').querySelectorAll('input,button,a,select')).map(function(e){ return e.id; })")
    case("turned down (b), as the page stands: nothing but the two ticks sits under the preview", under == ["guidesOn", "cutMode"], under)

    # ---- every word on the page is hers, ours, or theirs
    c.wait_for("document.getElementById('vid').readyState >= 1", 15)
    save_js({"captions": True, "shots": [stretch(spot="center")]})
    at(WORDS[2]["start"] + 0.02)
    ok = t.allowed_text(s, extra=set(SAID) | {SHORT, TALK, FOOT, "❚❚", "you're"})
    texts = c.js(t.READ_TEXT)
    stray = [x for x in texts if not ok(x)]
    case("every piece of text on the page (%d) is one of her lines, one of ours, or the photographer's own" % len(texts), len(texts) > 80 and not stray, stray[:6])
    case("nothing of theirs became HTML on the preview", c.js("document.querySelectorAll('#cap *').length") == 0 and c.text("#cap") == "<b>bold</b>")
    blob = c.js("document.documentElement.outerHTML")
    case("no path anywhere in the page as it stands", str(s.work) not in blob and "/private/" not in blob and "Your Content" not in blob and "/Footage/" not in blob and "/Photos/" not in blob)
    case("no browser pop-up was ever asked for", c.js("window.__dialogs") == 0 and not list(c.dialogs))
    case("nothing was asked of the internet", not c.outside_requests(), c.outside_requests()[:3])
    asked = [r_["url"] for r_ in list(c.requests) if "/reel-footage" in r_["url"]]
    case("the preview never asked for the Footage list, and nothing was made for a Footage video (no small copy, no still)",
         not asked and not list((kit / ".kit").glob("footage/*/preview.mp4")) and not list((kit / ".kit").glob("footage/*/preview.json")), asked[:2])
    case("no part of the page failed on a new state, and no page errors", c.js("window.Talk.faults.length") == 0 and not c.page_errors(), (c.js("window.Talk.faults"), c.page_errors()[:3]))

    # ---- phone width
    c.phone()
    try:
        open_it()
        at(WORDS[2]["start"] + 0.02)
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
        b2, k = scr(), c.rect("#phKnob")
        case("phone width: no sideways scroll with the preview, a photo, its handle and a caption showing; the screen fits the window",
             wide[0] <= 0 and wide[1] == 390 and b2["x"] >= 0 and b2["right"] <= 390.5 and c.js("window.__pic().wrap") and c.text("#cap") == "<b>bold</b>" and k["w"] > 0, (wide, b2))
        touchy = c.js("[getComputedStyle(document.getElementById('phFront')).touchAction, getComputedStyle(document.getElementById('cap')).touchAction, getComputedStyle(document.getElementById('phKnob')).touchAction,"
                      " getComputedStyle(document.getElementById('screen')).touchAction]")
        case("...a finger on something that drags is a drag; anywhere else on the preview it still scrolls the page", touchy == ["none", "none", "none", "auto"], touchy)
    finally:
        c.desktop()

    # ---- a page that is not showing: what is cut is still skipped (no animation frames there)
    open_it()
    save_js({"cut": [[6, 12]], "shots": []})
    P4 = pieces()
    c.js("window.requestAnimationFrame = function(){ return 0; }; Object.defineProperty(document, 'hidden', {get: function(){ return true; }, configurable: true});")
    at(P4[0]["to"] - 0.2)
    c.wait_for("!document.getElementById('vid').seeking", 5)
    time.sleep(0.15)
    c.js("window.__seeks.length = 0; window.Talk.togglePlay()")
    try:
        c.wait_for("window.__seeks.length >= 1", 8, tell="document.getElementById('vid').currentTime")
    except Exception:  # noqa: BLE001
        pass
    sk = c.js("window.__seeks")
    c.js("document.getElementById('vid').pause()")
    case("on a page that is not showing (it gets no animation frames) the cut version still skips what is cut, on the video's own clock",
         bool(sk) and abs(sk[0] - P4[1]["from"]) < 0.002, (sk, P4))
