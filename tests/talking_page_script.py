#!/usr/bin/env python3
"""The `script` part of tests/talking_page_check.py (sub-stage C2 of the talking reel page): the script column,
the highlight bar, the bars above the words, a bar's menu, and the two pickers. Not run by itself:

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py --only script

talking_page_check.py hands this file itself (`t`: its Setup, its helpers), its Setup (`s`) and, for the page, its
hidden Chrome (`c`). What is checked, in the plan's own order (docs/handoff-v24-build-2026-11-12.md, Stage C, C2):
the sentences and their styles; a click on a word; the highlight bar in her order and each of its buttons; the Move
row; the photo picker; a stretch's bar (its sizes, its thumbnails, its handles, a stretch across two sentences);
the menu (where it opens, each button, how it closes); dragging a bar (a click, an end, the middle, onto another
stretch); the video picker (asked for only when it opens, a video going from "getting it ready" to playable, the
start point, Change video); her pitfalls and the layouts she turned down; text as text, no path, no pop-up,
nothing asked of the internet, phone width. Since her v27 (Nov 17): fixing a word the transcriber got wrong (the
bar's fourth group, the double-click, the small box and its keys, the same-number rule, the underline, the grey
word typed away, the hover line, the captions, Undo and Redo, and ours around it: fix_words below), and "+ Add
more photos" in the photo pop-up's footer (her button and her lines, the folder opened through the posting
server's own route, a photo dropped into the Photos folder while the pop-up is open numbered at the END with
every other number kept and the grid built again with nothing picked lost: add_more_photos below).

The record is seeded here (TR.put_words), so nothing is transcribed. The talking video and the two Footage videos
are tests/fixtures/loud-tone-3s.mp4 (3 seconds, self-made); the video picker has the Mac get those two ready (a
few stills each), which is why this runs under the memory guard, one test at a time.
"""
import html
import json
import re
import shutil
import time
from pathlib import Path

KIT = "2026-09-25 Zoë's script"
SHORT = KIT[11:]
TALK = "talk.mp4"
SAID = ["OK", "so", "<b>bold</b>", "we", "were", "at", "the", "beach.",
        "It", "was", "awesome", "and", "you", "'re", "going", "to", "love", "it.",
        "Every", "photo", "is", "yours."]
S1, S2, S3 = (0, 7), (8, 17), (18, 21)
WORDS = [{"w": w, "start": round(0.05 + i * 0.13, 3), "end": round(0.15 + i * 0.13, 3), "conf": 0.9} for i, w in enumerate(SAID)]
PHOTOS = 10

HELPERS = r"""
window.__seeks = [];
window.__pickWords = function(a, b){
  var T = window.Talk, s = window.getSelection(), r = document.createRange();
  var x = T.wordEl(a).lastChild, y = T.wordEl(b).lastChild;
  r.setStart(x, 0); r.setEnd(y, y.nodeValue.length);
  s.removeAllRanges(); s.addRange(r);
};
window.__segs = function(a){
  return Array.from(document.querySelectorAll('#script .seg[data-a="' + a + '"]')).map(function(g){
    var sp = g.parentNode, r = g.getBoundingClientRect(), q = sp.getBoundingClientRect(), cs = getComputedStyle(g);
    return {i: +sp.getAttribute('data-i'), cls: g.className.split(/\s+/).filter(Boolean).sort().join(' '),
            l: !!g.querySelector('.sh.l'), r: !!g.querySelector('.sh.r'), top: Math.round((r.top - q.top) * 10) / 10, h: Math.round(r.height * 10) / 10,
            over: Math.round((r.right - q.right) * 10) / 10, z: cs.zIndex,
            imgs: Array.from(g.querySelectorAll('.sthumbs img')).map(function(i){ return [i.getAttribute('src'), i.offsetWidth, i.offsetHeight, i.naturalWidth > 0]; }),
            em: g.querySelector('.sthumbs em') ? g.querySelector('.sthumbs em').textContent : null};
  });
};
window.__menu = function(){
  var m = document.getElementById('pmenu');
  if (!m.classList.contains('open')) return null;
  var r = m.getBoundingClientRect();
  return {words: m.querySelector('.pm-w').textContent, spots: Array.from(m.querySelectorAll('[data-mspot]')).map(function(b){ return [b.textContent, b.classList.contains('on')]; }),
          acts: Array.from(m.querySelectorAll('.pm-a button')).map(function(b){ return b.textContent; }),
          x: r.left, y: r.top, w: r.width, h: r.height};
};
"""


def run_requests(t, s):
    """By request, no browser: what a whole state now carries for the script and the pickers."""
    case = t.case
    kit = make(t, s)
    st = s.state(KIT)
    case("a whole state carries the shoot's photos as the pickers know them: numbered as the sheet, with each one's size, and nothing else",
         [p["n"] for p in st.get("photos") or []] == list(range(1, PHOTOS + 1)) and all(set(p) == {"n", "w", "h", "v", "have", "missing"} for p in st["photos"])
         and st.get("stills") == {}, (st.get("photos") or [])[:2])
    blob = json.dumps(st, ensure_ascii=False)
    case("...and no path or file name of a photo is in it", str(s.work) not in blob and "beach-0" not in blob and "/Photos" not in blob)
    short = s.state(KIT, "&rev=%d&mark=%s" % (st["rev"], st["mark"]))
    case("the short answer (nothing moved) carries neither", "photos" not in short and "stills" not in short and "rec" not in short, sorted(short))
    code, j = s.post("/talking-save", {"kit": KIT, "base": st["rev"], "page": "scripttest1", "saved": {"shots": [
        {"a": 9, "b": 12, "ns": [3, 2], "v": None, "from": 0, "spot": "full", "pos": None, "me": None}]}})
    case("a save of a photo stretch answers with the whole state, photos beside it", code == 200 and j.get("ok") and len(j.get("photos") or []) == PHOTOS
         and [(x["a"], x["b"], x["ns"]) for x in j["shots"]] == [(9, 12, [3, 2])], (code, (j or {}).get("words")))
    code, j = s.post("/talking-save", {"kit": KIT, "base": j["rev"], "page": "scripttest1", "saved": {"shots": []}})
    case("...and it is taken away again the same way", code == 200 and j.get("shots") == [])
    import talking_js_script
    import talking_js_pick
    for m in (talking_js_script, talking_js_pick):
        case("%s.py is one string of JavaScript and nothing else" % m.__name__, [n for n in dir(m) if not n.startswith("_")] == ["JS"])
    js = talking_js_script.JS + talking_js_pick.JS
    code_only = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)
    case("her pitfall: no plus and no \"add\" that shows on hover; adding is only from the highlight bar",
         "addph" not in js and "mouseenter" not in code_only and "onBar('selPhoto'" in js and "onBar('selVideo'" in js)
    case("the Footage list is asked for in one place only: when the video picker is opened, pressed again, or a video is still being got ready",
         js.count("/reel-footage") == 1 and "for=talking" in js and "T.on('apply'" not in talking_js_pick.JS)
    case("no pop-up, no HTML from a string, in the new parts", not re.search(r"\b(confirm|alert|prompt)\s*\(|innerHTML|outerHTML|insertAdjacentHTML|document\.write", js))
    # her v27 footer: + Add more photos and its line in her .addph span, before the count and Use this photo
    page = s.tp.page_html(KIT)
    foot = re.search(r"<div class='pickfoot'>(.*?)</div></div></div>", page, re.S)
    # her markup, word for word, as a Mac shows it. Her title names Finder; on a PC the page says that computer's
    # word for it (talking_page.page_words, decision 26), so there the title is the plugin's own PC line, quoted
    # the same way, and everything around it is still hers to the letter. On a Mac the two are one and the same.
    her_title = "Opens this shoot&#x27;s Photos folder in Finder"
    hers = ("<span class='addph'><button class='btn small' id='addPhotos' type='button' title='" + her_title + "'>"
            "+ Add more photos</button><span class='hintsm' id='addPhotosSay'></span></span><span class='hintsm' id='pickCount'></span>"
            "<button class='btn main' id='pickUse' type='button' disabled>Use this photo</button>")
    here_title = html.escape(s.tp.page_words()["add_photos_title"], quote=True)
    want = hers.replace(her_title, here_title)
    case("the photo pop-up's footer (v27): her button with her title, then a line of its own, then the count and Use this photo, in her markup",
         bool(foot) and foot.group(1) == want and hers.count(her_title) == 1
         and html.escape(s.tp.WORDS["add_photos_title"], quote=True) == her_title
         and ((want != hers and "File Explorer" in here_title and "Finder" not in want) if t.WINDOWS else want == hers), foot and foot.group(1))
    case("the pop-up's button asks the posting server's own /open route for the Photos folder (the kit by its name, never a path), and the look asks for new photos only while the pop-up is open",
         "T.ask('/open?' + Q + '&sub=Photos')" in talking_js_pick.JS and "T.photoPickOpen = function(){ return isOpen('pick'); }" in talking_js_pick.JS
         and "T.photoPickOpen && T.photoPickOpen() ? '&photos=1' : ''" in s.tp.talking_js_core.JS and "setInterval" not in talking_js_pick.JS.split("// ---------- the video picker")[0])
    # with photos=1 the state numbers a photo dropped into the Photos folder (the record test proves the numbers; here the route)
    st = s.state(KIT, "&photos=1")
    case("GET /talking-state?photos=1 answers the whole state as ever when nothing landed", st.get("ok") and [p["n"] for p in st["photos"]] == list(range(1, PHOTOS + 1)))
    return kit


def make(t, s):
    kit = s.kit(KIT)
    if (kit / ".kit" / "talking.json").exists():
        return kit
    kit = s.make_kit(KIT, photos=PHOTOS)
    key = s.add_talk(kit, TALK)
    s.TR.put_words(kit, TALK, key, WORDS, info={"dur": 3.0})
    return kit


def run_page(t, c, s):
    case, skip, wait_for = t.case, t.skip, t.wait_for
    W = s.tp.page_words()
    kit = make(t, s)
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    c.init_script("(function(){ var real = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function(o){"
                  " return real.call(this, (o && typeof o === 'object') ? Object.assign({}, o, {behavior: 'auto'}) : o); }; })();")
    c.init_script(HELPERS)

    def rev():
        return c.js("window.Talk.rev")

    def moved(was, seconds=10):
        c.wait_for("window.Talk.rev !== %d" % was, seconds, tell="document.getElementById('toast').textContent")

    def toast():
        return t.toast(c)

    def shots():
        return [(x["a"], x["b"], x.get("ns") or [], x.get("v"), x.get("spot")) for x in (s.rec(KIT) or {}).get("shots") or []]

    def full(a):
        return next((x for x in (s.rec(KIT) or {}).get("shots") or [] if x["a"] == a), None)

    def pick_words(a, b):
        c.js("window.__pickWords(%d, %d)" % (a, b))
        c.wait_for("document.getElementById('selBar').style.display === 'flex'", 5)

    def bar_press(ident):
        """A press on one of the highlight bar's buttons, as a hand does it (the highlight must still be there)."""
        c.click("#" + ident, check=False)

    def save_js(body):
        was = rev()
        c.js("window.Talk.save(%s)" % json.dumps(body))
        moved(was)

    def word(i):
        return '#script .words span[data-i="%d"]' % i

    def cls(i):
        return sorted(c.js("document.querySelector(%s).className" % json.dumps(word(i))).split())

    t.open_page(c, s, KIT)
    c.wait_for("document.querySelectorAll('#script .sent').length === 3", 10, tell="document.getElementById('status').textContent")
    wait_for(lambda: all(p["have"] for p in s.state(KIT)["photos"]), 60)
    c.js("window.Talk.poll(true)")
    c.wait_for("window.Talk.PHOTOS.length === %d && window.Talk.PHOTOS.every(function(p){ return p.have; })" % PHOTOS, 10)
    c.wait_for("document.getElementById('vid').readyState >= 1", 15)
    c.js("document.getElementById('vid').addEventListener('seeking', function(){ window.__seeks.push(document.getElementById('vid').currentTime); })")

    # ---- the sentences
    got = c.js("Array.from(document.querySelectorAll('#script .sent')).map(function(e){ return [e.className, Array.from(e.querySelectorAll('.words span[data-i]')).map(function(x){ return x.textContent; })]; })")
    case("the script: one box a sentence, every word in it as text, in order",
         [g[1] for g in got] == [SAID[a:b + 1] for a, b in (S1, S2, S3)] and all(g[0].replace(" now", "") == "sent" for g in got), got)   # (the sentence being said is lit: the preview)
    case("a word with a tag in it is text, never HTML", c.js("document.querySelectorAll('#script .words b:not(.sh)').length") == 0 and c.text(word(2)) == "<b>bold</b>")
    tools = c.js("Array.from(document.querySelectorAll('#script .sent')).map(function(e){ var r = e.querySelector('.tools'); return [e.children.length, Array.from(r.children).map(function(x){ return [x.tagName, x.textContent, x.classList.contains('on')]; })]; })")
    want = [["SPAN", "Move", False], ["BUTTON", "None", True], ["BUTTON", "Punch in", False], ["BUTTON", "Slow zoom", False]]
    case("turned down (d): under a sentence the only row is Move: None / Punch in / Slow zoom (None lit), and no Photo row",
         all(x == [2, want] for x in tools), tools[:1])
    plain = c.js("(function(){ var e = document.querySelector(%s), cs = getComputedStyle(e); return [cs.paddingTop, cs.display, e.getBoundingClientRect().height]; })()" % json.dumps(word(3)))
    case("turned down (c): a sentence with no photo has the normal line height: no room above its words", plain[0] == "0px" and plain[1] == "inline" and plain[2] < 32, plain)
    lay = c.js("(function(){ var ph = getComputedStyle(document.querySelector('.phone')), sc = getComputedStyle(document.getElementById('script')), ed = getComputedStyle(document.querySelector('.edit'));"
               " return [ph.position, sc.overflowY, sc.maxHeight, ed.overflowY, Array.from(document.querySelector('.controls').querySelectorAll('input,button')).map(function(e){ return e.id; })]; })()")
    case("turned down (a) and (b), as the page stands: the preview is sticky, the script has no scroll frame of its own, and only the two checkboxes sit under the preview",
         lay == ["sticky", "visible", "none", "visible", ["guidesOn", "cutMode"]], lay)

    # ---- a click on a word
    c.js("document.getElementById('vid').pause()")
    c.click(word(3))
    c.wait_for("!document.getElementById('vid').paused && window.__seeks.length >= 1", 5)
    seeks = c.js("window.__seeks")
    case("a click on a word jumps to 0.05 s before it and plays", seeks and abs(seeks[-1] - (WORDS[3]["start"] - 0.05)) < 0.002, seeks[-3:])
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)

    # ---- highlight words: the bar
    a_, b_ = c.rect(word(4)), c.rect(word(6))
    c.drag((a_["x"] + 2, a_["cy"]), (b_["right"] - 2, b_["cy"]), steps=8)
    c.wait_for("document.getElementById('selBar').style.display === 'flex'", 5)
    # The bar shows from the drag's FIRST step, and the page moves it on every `selectionchange`, which a browser
    # hands over a moment AFTER the highlight itself has grown. So give the last one up to 5 s to arrive before
    # measuring (on GitHub's Mac, Nov 13, the bar was read where the step before the last had put it, 4.7 px
    # left). The measure and the check below are what they were: a bar that never gets there still FAILS.
    try:
        c.wait_for("(function(){ var b = document.getElementById('selBar').getBoundingClientRect(), s = window.getSelection().getRangeAt(0).getBoundingClientRect();"
                   " return Math.abs(b.left + b.width / 2 - (s.left + s.width / 2)) < 2; })()", 5)
    except Exception as e:
        print("      (the bar did not come to the middle of the highlight in 5 s; measured as it stands: %s)" % str(e)[:200])
    bar = c.js("(function(){ var b = document.getElementById('selBar'), r = b.getBoundingClientRect(), s = window.getSelection().getRangeAt(0).getBoundingClientRect();"
               " return {kids: Array.from(b.children).map(function(e){ return e.tagName === 'I' ? '|' : e.textContent; }), top: r.top, want: Math.max(8, s.top - 48), l: r.left, r: r.right,"
               " mid: r.left + r.width / 2, smid: s.left + s.width / 2, got: window.Talk.selectedWords(), paused: document.getElementById('vid').paused}; })()")
    case("highlight words with the mouse and the bar comes up, in her order: + Add photos, + Add video | Cut, Bring back | Punch in, Slow zoom, No zoom | Fix the words (v27)",
         bar["kids"] == ["+ Add photos", "+ Add video", "|", "Cut", "Bring back", "|", "Punch in", "Slow zoom", "No zoom", "|", "Fix the words"] and bar["got"] == [4, 6], (bar["kids"], bar["got"]))
    case("...48 px above the highlight, centered on it, kept on the screen", abs(bar["top"] - bar["want"]) < 1 and abs(bar["mid"] - bar["smid"]) < 2 and bar["l"] >= 8, bar)
    time.sleep(0.3)
    case("...and highlighting plays nothing (a click is ignored while words are highlighted)", bar["paused"] and len(c.js("window.__seeks")) == len(seeks), c.js("window.__seeks"))
    undo0 = c.js("window.Talk.UNDO.length")
    was = rev()
    bar_press("selCut")
    moved(was)
    case("Cut: those words are cut in the record and crossed out; the highlight and the bar are gone; one Undo step",
         s.rec(KIT)["cut"] == [[4, 6]] and all("cut" in cls(i) for i in (4, 5, 6)) and "cut" not in cls(7)
         and c.js("document.getElementById('selBar').style.display === 'none' && window.getSelection().isCollapsed && window.Talk.UNDO.length") == undo0 + 1, s.rec(KIT)["cut"])
    # a cut word, in the cut version: play starts at the next piece kept (the last of the three cut words: 0.05 s
    # before the first of them is still inside the tail of the piece before, in hers as in ours)
    c.js("window.__seeks.length = 0")
    c.click(word(6))
    c.wait_for("!document.getElementById('vid').paused && window.__seeks.length >= 2", 5, tell="window.__seeks")
    seeks = c.js("window.__seeks")
    nxt = c.js("(function(){ var T = window.Talk, t = %f; return T.P().filter(function(p){ return p.from > t; })[0].from; })()" % (WORDS[6]["start"] - 0.05))
    case("in the cut version a click on a cut word starts at the next piece kept", len(seeks) >= 2 and abs(seeks[-1] - nxt) < 0.002 and nxt > WORDS[6]["end"] - 0.2, (seeks, nxt))
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)
    c.click("#cutMode")
    c.js("window.__seeks.length = 0")
    c.click(word(6))
    c.wait_for("!document.getElementById('vid').paused && window.__seeks.length >= 1", 5)
    time.sleep(0.3)
    seeks = c.js("window.__seeks")
    case("...and with Play the cut version unticked it plays from the cut word itself", len(seeks) == 1 and abs(seeks[0] - (WORDS[6]["start"] - 0.05)) < 0.002, seeks)
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)
    c.click("#cutMode")
    pick_words(5, 6)
    was = rev()
    bar_press("selBack")
    moved(was)
    case("Bring back: only the highlighted words come back", s.rec(KIT)["cut"] == [[4, 4]] and "cut" in cls(4) and "cut" not in cls(5), s.rec(KIT)["cut"])
    pick_words(9, 11)
    was = rev()
    bar_press("selPunch")
    moved(was)
    case("Punch in: on those words, underlined, with her toast", s.rec(KIT)["zooms"] == [{"a": 9, "b": 11, "kind": "punch"}] and toast() == W["zoom_punch_toast"]
         and all("z-punch" in cls(i) for i in (9, 10, 11)) and "z-punch" not in cls(12), (s.rec(KIT).get("zooms"), toast()))
    part = c.js("Array.from(document.querySelectorAll('#script .sent')[1].querySelector('.tools').children).map(function(x){ return [x.textContent, x.classList.contains('on')]; })")
    case("...and the sentence's Move row says \"on part of it\", with no chip lit", part == [["Move", False], ["None", False], ["Punch in", False], ["Slow zoom", False], ["on part of it", False]], part)
    pick_words(10, 13)
    was = rev()
    bar_press("selZoom")
    moved(was)
    case("Slow zoom over part of a punch in trims it (setRange), dashed, with her toast",
         s.rec(KIT)["zooms"] == [{"a": 9, "b": 9, "kind": "punch"}, {"a": 10, "b": 13, "kind": "zoom"}] and toast() == W["zoom_slow_toast"] and "z-zoom" in cls(12), s.rec(KIT)["zooms"])
    pick_words(8, 14)
    was = rev()
    bar_press("selNoZoom")
    moved(was)
    case("No zoom: none left on those words, with her toast", s.rec(KIT)["zooms"] == [] and toast() == W["zoom_none_toast"] and "z-zoom" not in cls(12), s.rec(KIT)["zooms"])

    # ---- the Move row
    was = rev()
    c.click("#script .sent[data-k='2'] [data-move='punch']")
    moved(was)
    row = c.js("Array.from(document.querySelectorAll('#script .sent')[2].querySelectorAll('[data-move]')).map(function(x){ return x.classList.contains('on'); })")
    case("Move, Punch in: the whole sentence, the chip lit", s.rec(KIT)["zooms"] == [{"a": 18, "b": 21, "kind": "punch"}] and row == [False, True, False] and "z-punch" in cls(20), (s.rec(KIT)["zooms"], row))
    was = rev()
    c.click("#script .sent[data-k='2'] [data-move='zoom']")
    moved(was)
    was2 = rev()
    c.click("#script .sent[data-k='2'] [data-move='']")
    moved(was2)
    case("...Slow zoom takes its place, and None takes it off", s.rec(KIT)["zooms"] == [])
    pick_words(18, 21)
    was = rev()
    bar_press("selCut")
    moved(was)
    allcut = c.js("(function(){ var e = document.querySelectorAll('#script .sent')[2]; return [e.className, !!e.querySelector('.tools')]; })()")
    case("a sentence that is all cut is faint and has no Move row", allcut == ["sent allcut", False], allcut)
    pick_words(18, 21)
    was = rev()
    bar_press("selBack")
    moved(was)

    # ---- fix a word the transcriber got wrong (her v27)
    fix_words(t, c, s, kit, W, rev, moved, toast, pick_words, bar_press, word, cls)

    # ---- a refresh never redraws the script under a highlight
    pick_words(13, 14)
    c.js("window.__keep = window.Talk.wordEl(13)")
    s.cut(KIT, [[0, 1]], replace=True)
    c.js("window.Talk.poll(false)")
    c.wait_for("(window.Talk.REC.cut || []).length === 1 && window.Talk.REC.cut[0][0] === 0", 10)
    held = c.js("[window.__keep.isConnected, document.getElementById('selBar').style.display, window.Talk.scriptStale(), window.Talk.wordEl(0).className, window.Talk.UNDO.length]")
    case("her pitfall: a refresh that brings the assistant's cut does not redraw the script while words are highlighted (the bar stays under the cursor)",
         held[:4] == [True, "flex", True, ""], held)
    case("...and Undo's list is emptied, since the change was not this page's (2c)", held[4] == 0 and c.js("document.getElementById('tlUndo').disabled"))
    c.js("window.getSelection().removeAllRanges()")
    c.wait_for("!window.__keep.isConnected", 5)
    case("...it is drawn as soon as the highlight is let go", "cut" in cls(0) and "cut" in cls(1) and "cut" not in cls(4) and not c.js("window.Talk.scriptStale()"), cls(0))
    c.js("window.Talk.poll(true)")
    time.sleep(0.3)

    # ---- the photo picker
    pick_words(9, 12)
    bar_press("selPhoto")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    grid = c.js("Array.from(document.querySelectorAll('#pickGrid .pk')).map(function(d){ var i = d.querySelector('img'); return [+d.dataset.n, i.getAttribute('src').split('&v=')[0], i.alt, d.tagName]; })")
    q = c.js("window.Talk.Q")            # the kit as the page itself spells it in an address
    case("+ Add photos: the picker opens with every photo of the shoot, numbered as the sheet, each a small copy asked for by its number",
         grid == [[n, "/kit-photo?%s&n=%d&size=s" % (q, n), "Photo %d" % n, "BUTTON"] for n in range(1, PHOTOS + 1)], grid[:2])
    case("...its head quotes the words (her \"Photos for …\")",
         c.text("#pickHead") == "Photos for “was awesome and you”", c.text("#pickHead"))
    case("...nothing picked: \"Use this photo\" is off and there is no count", c.js("document.getElementById('pickUse').disabled") and c.text("#pickUse") == "Use this photo" and c.text("#pickCount") == "")
    case("the 3-second look RUNS while the photo pop-up is open (her v27: it asks for new photos), T.photoPickOpen() says so, and T.pickerOpen() too (for the keys)",
         c.js("window.Talk.quiet() && window.Talk.pickerOpen() && window.Talk.photoPickOpen()"))
    for n in (3, 5, 2):
        c.click("#pickGrid .pk[data-n='%d']" % n)
    marks = c.js("Array.from(document.querySelectorAll('#pickGrid .pk.on')).map(function(d){ return [+d.dataset.n, d.querySelector('b').textContent]; })")
    case("pick several: each shows its turn, in the order clicked, with her count and \"Use these 3\"",
         sorted(marks) == [[2, "3"], [3, "1"], [5, "2"]] and c.text("#pickCount") == "3 photos, flashing through in this order" and c.text("#pickUse") == "Use these 3"
         and not c.js("document.getElementById('pickUse').disabled"), (marks, c.text("#pickCount")))
    c.click("#pickGrid .pk[data-n='5']")
    marks = c.js("Array.from(document.querySelectorAll('#pickGrid .pk.on')).map(function(d){ return [+d.dataset.n, d.querySelector('b').textContent]; })")
    case("...clicked again a photo comes out and the rest close up", sorted(marks) == [[2, "2"], [3, "1"]] and c.text("#pickUse") == "Use these 2", marks)
    c.click("#pickClose")
    case("Close: the picker goes and nothing is changed", not c.js("document.getElementById('pick').classList.contains('open')") and shots() == [])
    pick_words(9, 12)
    bar_press("selPhoto")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    case("...opened again it starts with nothing picked", c.count("#pickGrid .pk.on") == 0)
    c.click((8, 8))
    case("a press outside the sheet closes it too", not c.js("document.getElementById('pick').classList.contains('open')") and shots() == [])
    pick_words(9, 12)
    bar_press("selPhoto")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    for n in (3, 2):
        c.click("#pickGrid .pk[data-n='%d']" % n)
    was = rev()
    c.click("#pickUse")
    moved(was)
    case("Use these 2: a new stretch on those words, Full screen, nothing moved; the picker closes",
         full(9) == {"a": 9, "b": 12, "ns": [3, 2], "v": None, "from": 0.0, "spot": "full", "pos": None, "me": None}
         and not c.js("document.getElementById('pick').classList.contains('open')") and c.js("window.Talk.SELSHOT") == 9, full(9))

    # ---- the stretch's bar
    c.wait_for("document.querySelectorAll('#script .seg[data-a=\"9\"] .sthumbs img').length === 2 && Array.from(document.querySelectorAll('#script .sthumbs img')).every(function(i){ return i.complete; })", 10)
    segs = c.js("window.__segs(9)")
    case("the stretch is a bar over its words: a piece above each word, the first one rounded with the thumbnails, a handle only at each true end",
         [g["i"] for g in segs] == [9, 10, 11, 12] and [g["cls"] for g in segs] == ["on seg st", "on seg", "on seg", "en on seg"]
         and [g["l"] for g in segs] == [True, False, False, False] and [g["r"] for g in segs] == [False, False, False, True], segs)
    case("...her sizes: 44 px of room above the words, the bar 3 px down and 37 px tall, thumbnails 25 by 31",
         c.js("getComputedStyle(document.querySelector(%s)).paddingTop" % json.dumps(word(10))) == "44px" and all(g["top"] == 3 and g["h"] == 37 for g in segs)
         and [i[1:3] for i in segs[0]["imgs"]] == [[25, 31], [25, 31]], segs[0])
    case("...its pieces bridge the spaces between the words (not after the last), and the first piece lies above the rest",
         all(4 < g["over"] < 7 for g in segs[:3]) and abs(segs[3]["over"]) < 0.5 and segs[0]["z"] == "2" and segs[1]["z"] == "1", [(g["over"], g["z"]) for g in segs])
    case("...the photos in their order, each loaded from this computer, then the spot's short name",
         [i[0].split("&v=")[0] for i in segs[0]["imgs"]] == ["/kit-photo?%s&n=3&size=s" % q, "/kit-photo?%s&n=2&size=s" % q] and all(i[3] for i in segs[0]["imgs"]) and segs[0]["em"] == "Full screen", segs[0]["imgs"])
    # a page opened before the small copies were made: they show by themselves, with no press and no forced look
    c.js("window.Talk.PHOTOS.forEach(function(p){ p.have = false; }); window.Talk.renderScript()")
    none = c.js("document.querySelectorAll('#script .seg[data-a=\"9\"] .sthumbs img').length")
    n_state = len([1 for r_ in list(c.requests) if "/talking-state" in r_["url"] and "&rev=" not in r_["url"]])
    try:
        c.wait_for("document.querySelectorAll('#script .seg[data-a=\"9\"] .sthumbs img').length === 2 && window.Talk.PHOTOS.every(function(p){ return p.have; })", 12)
        came = True
    except Exception:  # noqa: BLE001
        came = False
    case("a photo whose small copy is not made yet shows nothing on its bar (never a broken picture), and shows BY ITSELF once the copy is made: the page looks again every few seconds while one is missing",
         none == 0 and came, (none, came))
    if not came:
        c.js("window.Talk.poll(true)")
        c.wait_for("document.querySelectorAll('#script .seg[data-a=\"9\"] .sthumbs img').length === 2", 10)
    time.sleep(5)
    n_after = len([1 for r_ in list(c.requests) if "/talking-state" in r_["url"] and "&rev=" not in r_["url"]])
    time.sleep(5)
    case("...and once every copy on the page is there it stops asking for the whole state",
         len([1 for r_ in list(c.requests) if "/talking-state" in r_["url"] and "&rev=" not in r_["url"]]) == n_after and n_after >= n_state, (n_state, n_after))
    # the same in the open photo picker: each copy shows in its place, the grid is not drawn again
    c.js("window.Talk.openPick(9, 12, window.Talk.findShot(9))")
    c.wait_for("document.getElementById('pick').classList.contains('open') && document.querySelectorAll('#pickGrid .pk img[src]').length === %d" % PHOTOS, 10)
    c.js("window.__pk = document.querySelector('#pickGrid .pk'); window.Talk.PHOTOS.forEach(function(p){ p.have = false; });"
         " Array.from(document.querySelectorAll('#pickGrid .pk img')).forEach(function(i){ i.removeAttribute('src'); })")
    try:
        c.wait_for("document.querySelectorAll('#pickGrid .pk img[src]').length === %d" % PHOTOS, 12)
        came = True
    except Exception:  # noqa: BLE001
        came = False
    case("...in the open photo picker too: a copy made while it is open shows in its place, and the grid is not drawn again under their hand",
         came and c.js("window.__pk.isConnected && document.querySelectorAll('#pickGrid .pk.on').length === 2"), came)
    c.js("window.Talk.poll(true)")
    c.click("#pickClose")
    c.wait_for("window.Talk.PHOTOS.every(function(p){ return p.have; }) && document.querySelectorAll('#script .seg[data-a=\"9\"] .sthumbs img').length === 2", 10)
    hasph = c.js("Array.from(document.querySelectorAll('#script .sent')).map(function(e){ return e.classList.contains('hasph'); })")
    case("turned down (c), again: only the sentence that has the photo has the room above its words",
         hasph == [False, True, False] and c.js("getComputedStyle(document.querySelector(%s)).paddingTop" % json.dumps(word(3))) == "0px", hasph)
    x, y = c.point('#script .seg[data-a="9"]', nth=1, check=False)
    c.mouse_move(x, y)
    hov = c.js("Array.from(document.querySelectorAll('#script .seg')).map(function(g){ return g.classList.contains('hov'); })")
    btns = c.js("document.querySelectorAll('#script button').length")
    case("hover: the whole stretch lights up", hov == [True] * 4, hov)
    case("her pitfall: hovering adds nothing to press (the only buttons in the script are the Move chips)", btns == 9, btns)
    c.mouse_move(5, 5)
    case("...and it goes out when the pointer leaves", c.count("#script .seg.hov") == 0)

    # ---- the menu
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    m = c.js("window.__menu()")
    r = c.rect('#script .seg[data-a="9"]', nth=1)
    case("a click on the bar opens its menu and plays nothing: her quoted words, the four spots with its own lit, Change photos, Remove this one, Remove all 2",
         m["words"] == "“was awesome and you”" and m["spots"] == [["Full screen", True], ["Full screen, you in the corner", False], ["Center", False], ["Small corner", False]]
         and m["acts"] == ["Change photos", "Remove this one", "Remove all 2"] and c.js("document.getElementById('vid').paused"), m)
    case("...300 px wide, 8 px under the bar, at its left edge", abs(m["w"] - 300) < 1 and abs(m["y"] - (r["bottom"] + 8)) < 1.5 and abs(m["x"] - r["x"]) < 1.5, (m, r))
    case("the 3-second look waits while the menu is open", c.js("!window.Talk.quiet()"))
    c.key("Escape")
    case("Escape closes it", c.js("window.__menu()") is None)
    c.click('#script .seg[data-a="9"]', nth=2, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    c.click((3, 3))                                      # the window's corner: outside the menu wherever it opened
    case("a press anywhere outside it closes it", c.js("window.__menu()") is None)
    c.click('#script .seg[data-a="9"]', nth=2, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    was = rev()
    c.click("#pmenu [data-mspot='center']")
    moved(was)
    case("pick a spot: saved, the menu closes, and the bar says the spot's short name", full(9)["spot"] == "center" and c.js("window.__menu()") is None
         and c.js("window.__segs(9)[0].em") == "Center", full(9))
    # moved by hand (the preview's part will do this by dragging): Put it back shows, and a new spot keeps where they put themselves
    save_js({"shots": [{"a": 9, "b": 12, "ns": [3, 2], "v": None, "from": 0, "spot": "center", "pos": {"x": 0.4, "y": 0.3, "w": 0.5}, "me": {"x": 0.3, "y": 0.7, "w": 0.3}}]})
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    case("\"Put it back\" shows only once the photo, or they themselves, were moved", c.js("window.__menu().acts") == ["Change photos", "Remove this one", "Remove all 2", "Put it back"])
    was = rev()
    c.click("#pmenu [data-mspot='pip']")
    moved(was)
    case("a new spot clears where the photo was put and keeps where they put themselves", full(9)["spot"] == "pip" and full(9)["pos"] is None and full(9)["me"] == {"x": 0.3, "y": 0.7, "w": 0.3}
         and c.js("window.__segs(9)[0].em") == "You in corner", full(9))
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    was = rev()
    c.click("#pmenu [data-m='reset']")
    moved(was)
    case("Put it back clears both", full(9)["pos"] is None and full(9)["me"] is None and full(9)["spot"] == "pip", full(9))
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    case("...and is gone from the menu again", "Put it back" not in c.js("window.__menu().acts"))
    # Change photos keeps the spot, where it sits and where they sit
    save_js({"shots": [{"a": 9, "b": 12, "ns": [3, 2], "v": None, "from": 0, "spot": "center", "pos": {"x": 0.4, "y": 0.3, "w": 0.5}, "me": {"x": 0.3, "y": 0.7, "w": 0.3}}]})
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    c.click("#pmenu [data-m='change']")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    marks = c.js("Array.from(document.querySelectorAll('#pickGrid .pk.on')).map(function(d){ return [+d.dataset.n, d.querySelector('b').textContent]; })")
    case("Change photos: the picker opens on the photos it has, in their order", sorted(marks) == [[2, "2"], [3, "1"]] and c.js("window.__menu()") is None, marks)
    c.click("#pickGrid .pk[data-n='7']")
    was = rev()
    c.click("#pickUse")
    moved(was)
    case("...and Use keeps its spot, where it sits and where they sit", full(9) == {"a": 9, "b": 12, "ns": [3, 2, 7], "v": None, "from": 0.0, "spot": "center",
                                                                                 "pos": {"x": 0.4, "y": 0.3, "w": 0.5}, "me": {"x": 0.3, "y": 0.7, "w": 0.3}}, full(9))
    # a new stretch over part of it takes its spot and where they sit, never where the photo sat
    pick_words(12, 14)
    bar_press("selPhoto")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    c.click("#pickGrid .pk[data-n='8']")
    was = rev()
    c.click("#pickUse")
    moved(was)
    case("a new stretch laid over part of another takes that one's spot and where they sit (not where the photo sat), and trims it",
         full(12) == {"a": 12, "b": 14, "ns": [8], "v": None, "from": 0.0, "spot": "center", "pos": None, "me": {"x": 0.3, "y": 0.7, "w": 0.3}} and (full(9)["a"], full(9)["b"]) == (9, 11), (full(12), full(9)))
    # remove, after a refresh that replaced every object the menu was built from (her stale-object fault)
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    c.js("window.__old = window.Talk.SH; window.Talk.poll(true)")
    c.wait_for("window.Talk.SH !== window.__old", 5)
    was = rev()
    c.click("#pmenu [data-m='remove']")
    moved(was)
    case("her stale-object fault: after a refresh, \"Remove this one\" still removes (the first photo, as hers), with her toast",
         full(9)["ns"] == [2, 7] and toast() == W["removed"], (full(9), toast()))
    c.click('#script .seg[data-a="9"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    was = rev()
    c.click("#pmenu [data-m='removeall']")
    moved(was)
    case("Remove all 2: the stretch goes, with her \"Removed. Undo brings them back.\"", full(9) is None and toast() == W["removed_many"] and c.count('#script .seg[data-a="9"]') == 0, shots())
    c.click('#script .seg[data-a="12"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    case("one photo: the menu says Change photo and Remove", c.js("window.__menu().acts")[:2] == ["Change photo", "Remove"], c.js("window.__menu().acts"))
    was = rev()
    c.click("#pmenu [data-m='remove']")
    moved(was)
    case("...and Remove takes the stretch away, with her \"Removed. Undo brings it back.\"", shots() == [] and toast() == W["removed"] and c.count("#script .sent.hasph") == 0, shots())
    was = rev()
    c.click("#tlUndo")
    moved(was)
    case("...and Undo does bring it back", [x[:3] for x in shots()] == [(12, 14, [8])], shots())

    # ---- the menu's words at 70 characters, and where it opens near the dock
    save_js({"shots": [{"a": 0, "b": 17, "ns": [1, 2, 3, 4, 5, 6, 7, 8, 9], "v": None, "from": 0, "spot": "corner", "pos": None, "me": None}]})
    c.wait_for("document.querySelectorAll('#script .seg[data-a=\"0\"]').length === 18", 5)
    c.wait_for("Array.from(document.querySelectorAll('#script .sthumbs img')).every(function(i){ return i.complete; })", 10)
    segs = c.js("window.__segs(0)")
    case("a stretch that runs into the next sentence starts its thumbnails again there; handles only at its true ends; at most 8 thumbnails",
         [g["i"] for g in segs if "st" in g["cls"].split()] == [0, 8] and [g["i"] for g in segs if "en" in g["cls"].split()] == [7, 17]
         and [g["i"] for g in segs if g["l"]] == [0] and [g["i"] for g in segs if g["r"]] == [17]
         and [len(g["imgs"]) for g in segs if g["imgs"]] == [8, 8] and [g["em"] for g in segs if g["em"] is not None] == ["Corner", "Corner"], [(g["i"], g["cls"], len(g["imgs"])) for g in segs])
    c.desktop(size=(1280, 700))
    try:
        c.js("window.scrollTo(0, 0); window.Talk.sizeDock()")
        low = c.js("(function(){ var T = window.Talk, g = document.querySelectorAll('#script .seg[data-a=\"0\"]')[9], dock = document.getElementById('dock').offsetHeight;"
                   " var y = g.getBoundingClientRect().bottom + window.scrollY; window.scrollTo(0, Math.max(0, y - (innerHeight - dock - 30)));"
                   " var r = g.getBoundingClientRect(); T.openMenu(0, 0, g); var m = document.getElementById('pmenu').getBoundingClientRect();"
                   " return {top: m.top, h: m.height, segTop: r.top, segBottom: r.bottom, room: innerHeight - dock, words: document.querySelector('#pmenu .pm-w').textContent, left: m.left, right: m.right, vw: innerWidth}; })()")
        case("the menu opens ABOVE the bar when it would go under the dock", low["segBottom"] + 8 + low["h"] > low["room"] and abs(low["top"] - (low["segTop"] - low["h"] - 8)) < 1.5, low)
        said = " ".join(SAID[:18]).replace(" '", "'")
        case("...and its quoted words stop at 70 characters with \"…\"", low["words"] == "“" + said[:70] + "…”" and len(said) > 70, low["words"])
        c.key("Escape")
    finally:
        c.desktop()
    c.js("window.scrollTo(0, 0)")

    # ---- dragging a bar
    save_js({"shots": [{"a": 2, "b": 3, "ns": [1], "v": None, "from": 0, "spot": "full", "pos": None, "me": None},
                       {"a": 9, "b": 12, "ns": [3, 2], "v": None, "from": 0, "spot": "pip", "pos": None, "me": {"x": 0.3, "y": 0.7, "w": 0.3}}]})
    c.wait_for("document.querySelectorAll('#script .seg').length === 6", 5)
    c.js("document.getElementById('script').scrollIntoView({block: 'center'})")
    before = s.rec_bytes(KIT)
    x, y = c.point('#script .seg[data-a="9"]', nth=1, check=False)
    c.drag((x, y), (x + 3, y + 1), steps=2)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    case("a press that moves under 5 px is a click: the menu opens and nothing is saved", s.rec_bytes(KIT) == before)
    c.key("Escape")
    # the end handle, out to a later word
    hx, hy = c.point('#script .seg[data-a="9"] .sh.r', check=False)
    w14 = c.rect(word(14))
    c.click('#script .seg[data-a="9"]', nth=1, check=False)          # the menu is open as the drag starts
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    hx, hy = c.point('#script .seg[data-a="9"] .sh.r', check=False, scroll=False)
    w14 = c.rect(word(14))
    c.drag((hx, hy), (w14["right"] - 1, w14["cy"] + 8), steps=6, release=False)
    mid = c.js("[Array.from(document.querySelectorAll('#script .words span.ghost')).map(function(e){ return +e.dataset.i; }), document.getElementById('pmenu').classList.contains('open'), window.Talk.quiet()]")
    case("dragging an end: the words it would cover are tinted, the menu closes as the drag starts, and the 3-second look waits",
         mid == [[9, 10, 11, 12, 13, 14], False, False], mid)
    was = rev()
    c.mouse_release()
    moved(was)
    case("...let go: the end is on the nearest word, everything else of the stretch kept, with her toast Now on “…”",
         full(9) == {"a": 9, "b": 14, "ns": [3, 2], "v": None, "from": 0.0, "spot": "pip", "pos": None, "me": {"x": 0.3, "y": 0.7, "w": 0.3}}
         and toast() == "Now on “was awesome and you're going”" and c.count("#script .words span.ghost") == 0, (full(9), toast()))
    # the start handle can't pass the end
    hx, hy = c.point('#script .seg[data-a="9"] .sh.l', check=False)
    w17 = c.rect(word(17))
    was = rev()
    c.drag((hx, hy), (w17["right"] - 1, w17["cy"] + 8), steps=6)
    moved(was)
    case("the start can't pass the end: dragged past it, the stretch is its last word", [x[:2] for x in shots()] == [(2, 3), (14, 14)], shots())
    # the end handle can't pass the start
    hx, hy = c.point('#script .seg[data-a="14"] .sh.r', check=False)
    w9 = c.rect(word(9))
    before = s.rec_bytes(KIT)
    c.drag((hx, hy), (w9["x"] + 1, w9["cy"] + 8), steps=6)
    time.sleep(0.4)
    case("nor the end the start: dragged before it, nothing changes and nothing is saved", s.rec_bytes(KIT) == before and c.count("#script .words span.ghost") == 0)
    # stretch it back, then move it by its middle
    hx, hy = c.point('#script .seg[data-a="14"] .sh.l', check=False)
    w9 = c.rect(word(9))
    was = rev()
    c.drag((hx, hy), (w9["x"] + 1, w9["cy"] + 8), steps=6)
    moved(was)
    case("an end snaps to the word's own edge (the start to a word's left edge)", [x[:2] for x in shots()] == [(2, 3), (9, 14)], shots())
    x, y = c.point('#script .seg[data-a="2"]', nth=0, fx=0.6, check=False)
    w0 = c.rect(word(0))
    was = rev()
    c.drag((x, y), (w0["x"] - 40, w0["cy"] - 30), steps=6)
    moved(was)
    case("the middle moves it, the same length, and it stops at the first word", [x[:2] for x in shots()] == [(0, 1), (9, 14)] and toast() == "Now on “OK so”", (shots(), toast()))
    x, y = c.point('#script .seg[data-a="0"]', nth=0, fx=0.5, check=False)
    w11 = c.rect(word(11))
    was = rev()
    c.drag((x, y), (w11["cx"], w11["cy"] + 8), steps=8)
    moved(was)
    got = [(x_["a"], x_["b"], x_["ns"], x_["spot"]) for x_ in s.rec(KIT)["shots"]]
    case("dropped onto another stretch it splits that one around itself, and each keeps what it was",
         got == [(9, 10, [3, 2], "pip"), (11, 12, [1], "full"), (13, 14, [3, 2], "pip")], got)
    x, y = c.point('#script .seg[data-a="11"]', nth=0, fx=0.5, check=False)
    w21 = c.rect(word(21))
    was = rev()
    c.drag((x, y), (w21["right"] + 60, w21["cy"] + 40), steps=8)
    moved(was)
    case("...and a move stops at the last word", (20, 21, [1], "full") in [(x_["a"], x_["b"], x_["ns"], x_["spot"]) for x_ in s.rec(KIT)["shots"]], shots())

    # ---- a drag whose release the page never saw; a Control-click; a redraw between the press and the release
    c.key("Escape")
    a0 = c.js("window.Talk.SH[0].a")
    before = s.rec_bytes(KIT)
    x, y = c.point('#script .seg[data-a="%d"]' % a0, nth=0, fx=0.5, check=False)
    far = c.rect(word(16))
    c.mouse_move(x, y)
    c.mouse_press()
    c.mouse_move(x + 12, y + 2)                       # the drag has begun
    armed = c.js("[document.querySelectorAll('#script .words span.ghost').length > 0, window.Talk.quiet()]")
    c.buttons = 0                                     # the button was let go where the page did not see it
    for k in range(1, 6):
        c.mouse_move(x + (far["cx"] - x) * k / 5, y + (far["cy"] - y) * k / 5)
    loose = c.js("[document.querySelectorAll('#script .words span.ghost').length, window.Talk.quiet()]")
    c.buttons = 1
    c.mouse_release()
    time.sleep(0.5)
    case("a bar drag ends when the mouse moves with no button held (the release never reached the page): no words tinted, the 3-second look runs again, and the next release saves nothing",
         armed == [True, False] and loose == [0, True] and s.rec_bytes(KIT) == before and not c.js("document.getElementById('pmenu').classList.contains('open')"), (armed, loose))
    c.drag((x, y), (far["cx"], far["cy"]), steps=5, ctrl=True)
    time.sleep(0.4)
    case("a Control-click on a bar (the Mac's right click) starts no drag and saves nothing",
         s.rec_bytes(KIT) == before and c.count("#script .words span.ghost") == 0 and c.js("window.Talk.quiet()"))
    c.js("window.getSelection().removeAllRanges()")
    c.key("Escape")
    c.mouse_move(x, y)
    c.mouse_press()
    c.js("window.__old = document.querySelector('#script .seg[data-a=\"%d\"]'); window.Talk.renderScript()" % a0)
    c.mouse_release()
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    at = c.js("(function(){ var g = document.querySelector('#script .seg[data-a=\"%d\"]').getBoundingClientRect(), m = document.getElementById('pmenu').getBoundingClientRect();"
              " return {old: window.__old.isConnected, mx: m.left, my: m.top, mh: m.height, want: Math.max(8, Math.min(innerWidth - m.width - 8, g.left)), below: g.bottom + 8, above: g.top - m.height - 8}; })()" % a0)
    case("the script drawn again between the press and the release of a click on a bar (a save's answer, a look): the menu still opens beside the bar, not in the corner of the window",
         at["old"] is False and abs(at["mx"] - at["want"]) < 1.5 and (abs(at["my"] - at["below"]) < 1.5 or abs(at["my"] - at["above"]) < 1.5), at)
    c.key("Escape")
    case("...and none of that saved anything", s.rec_bytes(KIT) == before)

    # ---- the hook the timeline will use: the picked clip's words are outlined
    c.js("window.Talk.pickedWords = function(){ return [3, 4]; }; window.Talk.markPicked()")
    case("the words of a clip picked on the timeline are outlined in the script (the hook the timeline's part uses)",
         c.js("Array.from(document.querySelectorAll('#script .words span.picked')).map(function(e){ return +e.dataset.i; })") == [3, 4])
    c.js("window.Talk.pickedWords = null; window.Talk.markPicked()")

    # ---- the video picker
    asked = [r_["url"] for r_ in list(c.requests)]
    case("until the video picker is opened, the page has never asked for the Footage list, and nothing was made for a Footage video",
         not [u for u in asked if "/reel-footage" in u or "/reel-video" in u] and not (kit / ".kit" / "footage").exists(), [u for u in asked if "/reel-" in u][:3])
    pick_words(0, 2)
    bar_press("selVideo")
    c.wait_for("document.getElementById('vpick').classList.contains('open') && document.getElementById('vpList').children.length > 0", 10)
    none = c.js("(function(){ var p = document.querySelector('#vpList p'); return p ? [p.textContent, Array.from(p.querySelectorAll('b')).map(function(b){ return b.textContent; })] : null; })()")
    case("+ Add video with nothing in Footage: her head \"A video for …\", and her line with its two bold names",
         c.text("#vpHead") == "A video for “OK so <b>bold</b>”" and none == ["No videos in this shoot's Footage folder yet. Press Open my Footage folder, drag your videos in, then press I added videos.",
                                                                                 ["Open my Footage folder", "I added videos"]]
         and c.js("document.getElementById('vpPlayer').hidden && document.querySelectorAll('#vpHead b').length === 0"), (c.text("#vpHead"), none))
    case("the 3-second look waits while the video picker is open", c.js("!window.Talk.quiet() && window.Talk.pickerOpen()"))
    c.click("#vpOpen")
    c.wait_for("document.getElementById('toast').classList.contains('on') && document.getElementById('toast').textContent.indexOf('Footage') >= 0", 5)
    case("Open my Footage folder: the folder is made and her toast says it is open", toast() == W["footage_open"] and (kit / "Footage").is_dir(), toast())
    if not t.MAC:
        skip("the video picker with videos in it: getting a Footage video ready is a Mac's")
        c.click("#vpClose")
    else:
        video_picker(t, c, s, kit, W, rev, moved, toast, full, shots, pick_words, bar_press, word)

    # ---- + Add more photos (her v27): the pop-up's footer, the folder, and photos dropped in while it is open
    add_more_photos(t, c, s, kit, W, pick_words, bar_press)

    # ---- every word on the page is hers, ours, or theirs
    ok = t.allowed_text(s, extra=set(SAID) | {SHORT, TALK, "bts.mp4", "second.mp4", "zz-broken.mov", "▶ bts", "▶ second", "0:03"})
    texts = c.js(t.READ_TEXT)
    stray = [x for x in texts if not ok(x)]
    case("every piece of text on the page (%d) is one of her lines, one of ours, or the photographer's own" % len(texts), len(texts) > 80 and not stray, stray[:6])
    case("nothing of theirs became HTML", c.js("!window.pwned && document.querySelectorAll('#script .words b:not(.sh), #pmenu b, #vpList .vcard b b, #pickHead b, #vpHead b').length === 0"))
    blob = c.js("document.documentElement.outerHTML")
    case("no path anywhere in the page as it stands", str(s.work) not in blob and "/private/" not in blob and "Your Content" not in blob and "/Footage/" not in blob and "/Photos/" not in blob)
    case("no browser pop-up was ever asked for", c.js("window.__dialogs") == 0 and not list(c.dialogs))
    case("nothing was asked of the internet", not c.outside_requests(), c.outside_requests()[:3])
    case("no part of the page failed on a new state, and no page errors", c.js("window.Talk.faults.length") == 0 and not c.page_errors(), (c.js("window.Talk.faults"), c.page_errors()[:3]))
    case("her pitfall, on the page as it stands: the class names of the top bar and the highlight bar are on those two and nothing else",
         c.js("document.querySelectorAll('.bar').length === 1 && document.querySelectorAll('.sel').length === 1 && document.querySelector('.sel').id === 'selBar'"))

    # ---- phone width
    c.phone()
    try:
        t.open_page(c, s, KIT)
        c.wait_for("document.querySelectorAll('#script .sent').length === 3", 10)
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
        case("phone width: no sideways scroll with the script and its bars showing", wide[0] <= 0 and wide[1] == 390 and c.count("#script .seg") > 0, wide)
        c.js("(function(){ var g = document.querySelector('#script .seg'); g.scrollIntoView({block: 'center'}); window.Talk.openMenu(+g.dataset.a, 0, g); })()")
        m = c.js("window.__menu()")
        case("...and a bar's menu stays on the screen", m and m["x"] >= 0 and m["x"] + m["w"] <= 390 + 0.5, m)
        c.js("window.Talk.closeMenu(); window.__pickWords(3, 4)")
        c.wait_for("document.getElementById('selBar').style.display === 'flex'", 5)
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, document.getElementById('selBar').getBoundingClientRect().left]")
        case("...nor does the highlight bar push the page sideways", wide[0] <= 0, wide)
        c.js("window.getSelection().removeAllRanges()")
    finally:
        c.desktop()
    # the fix box on a small phone (375 px): above its word and inside the window; the legend's hint wraps under
    c.phone(width=375, height=812)
    try:
        t.open_page(c, s, KIT)
        c.wait_for("document.querySelectorAll('#script .sent').length === 3", 10)
        c.js("window.Talk.wordEl(3).scrollIntoView({block: 'center'}); window.Talk.openFix(3, 3, null)")
        c.wait_for("!document.getElementById('fixBox').hidden", 5)
        fb = c.js("(function(){ var b = document.getElementById('fixBox').getBoundingClientRect(), w = window.Talk.wordEl(3).getBoundingClientRect();"
                  " var f = document.querySelector('#editStep .legend .fixed').getBoundingClientRect(), h = document.querySelector('#editStep .legend .lfix').getBoundingClientRect();"
                  " return {x: b.left, r: b.right, y: b.top, bottom: b.bottom, wtop: w.top, vw: innerWidth, hint: h.top > f.bottom - 1 && h.left < f.left + 1,"
                  " wide: document.documentElement.scrollWidth - document.documentElement.clientWidth}; })()")
        case("at 375 px the box sits above its word and inside the window (her 180 px input gives way)",
             fb["x"] >= 8 and fb["r"] <= 375 - 8 + 0.5 and abs(fb["bottom"] + 8 - fb["wtop"]) < 1.5, fb)
        case("...and the legend's hint wraps under the legend at the left", fb["hint"], fb)
        c.js("window.Talk.closeFix(); window.Talk.openPick(3, 4)")
        c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
        c.js("document.getElementById('addPhotosSay').textContent = %s" % json.dumps(W["add_photos_open"]))      # her longest line beside the button
        ft = c.js("(function(){ var a = document.getElementById('addPhotos').getBoundingClientRect(), u = document.getElementById('pickUse').getBoundingClientRect(), s = document.querySelector('.sheet').getBoundingClientRect(), y = document.getElementById('addPhotosSay').getBoundingClientRect();"
                  " return {al: a.left, ar: a.right, ul: u.left, ur: u.right, abot: a.bottom, ytop: y.top, yl: y.left, yr: y.right, sl: s.left, sr: s.right, vw: innerWidth}; })()")
        case("at 375 px the pop-up's footer: her line wraps under + Add more photos (her .addph wraps), and the button, the line and Use this photo all stay inside the sheet and the window",
             ft["al"] >= ft["sl"] - 0.5 and ft["ytop"] >= ft["abot"] - 0.5 and ft["yl"] >= ft["sl"] - 0.5 and ft["yr"] <= ft["sr"] + 0.5
             and ft["ul"] >= ft["sl"] - 0.5 and ft["ur"] <= ft["sr"] + 0.5 and ft["ur"] <= ft["vw"] + 0.5, ft)
        c.js("window.Talk.closePick()")
        if fb["wide"] > 0 or fb["vw"] != 375:
            # not this item's: with this test's record (two-photo stretches over short words), the page is a few px wider
            # than 375 here (her .sthumbs are nowrap and sit absolutely over the word); the 390 check above is clean
            print("      (note: at 375 px the page is %d px wider than the window, innerWidth %d: a stretch's thumbnails over a short word at a line's end)" % (fb["wide"], fb["vw"]))
        c.js("window.Talk.closeFix()")
    finally:
        c.desktop()


def add_more_photos(t, c, s, kit, W, pick_words, bar_press):
    """Her v27 "+ Add more photos" in the photo pop-up's footer: her button with her title, before the count and
    Use; a press opens the shoot's Photos folder through the posting server's own /open route (no window from a
    test: STUDIO_NO_WINDOWS_FOR_TESTS) and says her line; a photo dropped into the Photos folder while the pop-up
    is open is numbered at the END by the Assistant (the look asks with photos=1; Lane A's numbers that stay
    fixed), the grid is built again with it last, what was picked stays picked, every earlier number is unchanged,
    and her "{k} new photo(s) in, at the end." line says what each look brought; the pop-up closed, the look no
    longer asks for new photos."""
    case, wait_for = t.case, t.wait_for
    import os
    import time as _time
    photos = kit / "Photos"

    def grid():
        return c.js("Array.from(document.querySelectorAll('#pickGrid .pk')).map(function(d){ return [+d.dataset.n, d.querySelector('b').textContent, d.querySelector('img').getAttribute('src') ? 1 : 0]; })")

    def numbers():
        return [(x["n"], Path(x["file"]).name) for x in json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]]

    def drop(name, old=True):
        f = photos / name
        f.write_bytes(t.wpc.TINY)
        if old:                                           # settled: not still being copied in (reel_page.RELIST_SETTLE)
            os.utime(f, (_time.time() - 30, _time.time() - 30))
        return f

    before = numbers()
    pick_words(0, 2)
    bar_press("selPhoto")
    c.wait_for("document.getElementById('pick').classList.contains('open')", 5)
    foot = c.js("(function(){ var f = document.querySelector('#pick .pickfoot'); return {kids: Array.from(f.children).map(function(e){ return e.id || e.className; }),"
                " span: Array.from(f.firstElementChild.children).map(function(e){ return [e.id, e.textContent, e.getAttribute('title')]; }), say: document.getElementById('addPhotosSay').textContent,"
                " left: f.firstElementChild.getBoundingClientRect().left - f.getBoundingClientRect().left, use: document.getElementById('pickUse').getBoundingClientRect().left}; })()")
    case("the pop-up's footer: her + Add more photos with her title and an empty line beside it, at the left (her margin: 0 auto 0 0), then the count and Use this photo",
         foot["kids"] == ["addph", "pickCount", "pickUse"] and foot["span"] == [["addPhotos", W["add_photos"], W["add_photos_title"]], ["addPhotosSay", "", None]]
         and foot["left"] < 2 and foot["use"] > foot["left"] + 200, foot)
    n_req = len(list(c.requests))
    c.click("#addPhotos")
    c.wait_for("document.getElementById('addPhotosSay').textContent === %s" % json.dumps(W["add_photos_open"]), 10, tell="document.getElementById('addPhotosSay').textContent")
    asked = [r_["url"] for r_ in list(c.requests)[n_req:] if "/open" in r_["url"]]
    q = c.js("window.Talk.Q")
    case("a press: her \"The Photos folder is open in Finder…\" line, after one ask of the posting server's own /open for this kit's Photos folder (the kit by its name)",
         c.text("#addPhotosSay") == W["add_photos_open"] and asked == [s.url("/open" + s.q(KIT) + "&sub=Photos")], (c.text("#addPhotosSay"), asked))
    for n in (3, 2):
        c.click("#pickGrid .pk[data-n='%d']" % n)
    case("two photos picked, to be kept across what comes", [g[:2] for g in grid() if g[1]] == [[2, "2"], [3, "1"]], grid())
    was = c.js("window.Talk.mark")
    drop("beach-011.jpg")
    c.wait_for("document.querySelectorAll('#pickGrid .pk').length === %d" % (PHOTOS + 1), 25, tell="document.getElementById('addPhotosSay').textContent")
    g = grid()
    case("a photo dropped into the Photos folder while the pop-up is open: the grid is built again with it at the END, numbered %d, every earlier number as it was, and the two picked still picked in their order" % (PHOTOS + 1),
         [x[0] for x in g] == list(range(1, PHOTOS + 2)) and [x[:2] for x in g if x[1]] == [[2, "2"], [3, "1"]], g)
    case("...her line says what the look brought: \"1 new photo in, at the end.\"", c.text("#addPhotosSay") == W["photo_in"] == "1 new photo in, at the end.")
    case("...the numbered list keeps every earlier photo at its number and the new one takes the next (never numbered again from the folder)",
         numbers() == before + [(PHOTOS + 1, "beach-011.jpg")], numbers()[-3:])
    # the 3-second look carries the counter and the mark; the copies look (talking_js_script.py lookForCopies) asks bare, and may run too
    looks = [r_["url"] for r_ in list(c.requests)[n_req:] if "/talking-state" in r_["url"] and "&rev=" in r_["url"]]
    case("...the page's own 3-second look asked for it, with photos=1 while the pop-up is open (no second timer), and the mark moved with the list",
         looks and all("photos=1" in u for u in looks) and c.js("window.Talk.mark") != was, looks[-2:])
    wait_for(lambda: all(p["have"] for p in s.state(KIT)["photos"]), 60)
    c.wait_for("(function(){ var d = document.querySelector('#pickGrid .pk[data-n=\"%d\"] img'); return d && d.getAttribute('src'); })()" % (PHOTOS + 1), 15)
    case("...and its small copy shows in its place once made, asked for by its number", c.js("document.querySelector('#pickGrid .pk[data-n=\"%d\"] img').getAttribute('src')" % (PHOTOS + 1)).startswith("/kit-photo?%s&n=%d&size=s" % (q, PHOTOS + 1)))
    drop("beach-012.jpg")
    drop("beach-013.jpg")
    c.wait_for("document.querySelectorAll('#pickGrid .pk').length === %d" % (PHOTOS + 3), 25, tell="document.getElementById('addPhotosSay').textContent")
    case("two more: \"2 new photos in, at the end.\", numbered on, the picks still there",
         c.text("#addPhotosSay") == "2 new photos in, at the end." and [x[0] for x in grid()] == list(range(1, PHOTOS + 4)) and [x[:2] for x in grid() if x[1]] == [[2, "2"], [3, "1"]]
         and numbers() == before + [(PHOTOS + 1, "beach-011.jpg"), (PHOTOS + 2, "beach-012.jpg"), (PHOTOS + 3, "beach-013.jpg")], (c.text("#addPhotosSay"), numbers()[-3:]))
    c.click("#pickClose")
    n_req = len(list(c.requests))
    c.wait_for("true", 1)
    wait_for(lambda: [r_ for r_ in list(c.requests)[n_req:] if "/talking-state" in r_["url"] and "&rev=" in r_["url"]], 12)
    later = [r_["url"] for r_ in list(c.requests)[n_req:] if "/talking-state" in r_["url"] and "&rev=" in r_["url"]]
    case("the pop-up closed: the look goes on without photos=1 (a 30-minute talk's page never lists the folder for nothing)", later and not any("photos=1" in u for u in later), later[-2:])
    st = s.state(KIT)
    case("the state's photo list carries the three new ones after the ten, by number, no path",
         [p["n"] for p in st["photos"]] == list(range(1, PHOTOS + 4)) and "beach-01" not in json.dumps(st), [p["n"] for p in st["photos"]])


def fix_words(t, c, s, kit, W, rev, moved, toast, pick_words, bar_press, word, cls):
    """Fix a word the transcriber got wrong (her v27, Nov 17, screenshots 20 and 21): double-click a word or
    highlight a few and press Fix the words; the small box; Enter, Esc, Fix, Undo fix and ×; the same-number
    rule; the underline, the grey word typed away and the hover line; the captions; Undo and Redo; and ours
    (the keys in the box, the box on scroll, a press outside). The record is left as it was: no fix."""
    case = t.case

    def fixes():
        return (s.rec(KIT) or {}).get("fixes") or {}

    def box():
        return c.js("(function(){ var b = document.getElementById('fixBox'); if (b.hidden) return null; var r = b.getBoundingClientRect();"
                    " return {val: document.getElementById('fixIn').value, back: !document.getElementById('fixBack').hidden, focus: document.activeElement === document.getElementById('fixIn'),"
                    " x: r.left, y: r.top, w: r.width, h: r.height, bar: document.getElementById('selBar').style.display, sel: window.getSelection().isCollapsed,"
                    " paused: document.getElementById('vid').paused, kids: Array.from(b.children).map(function(e){ return [e.tagName, e.id, e.textContent, e.hidden]; })}; })()")

    def title(i):
        return c.js("document.querySelector(%s).getAttribute('title')" % json.dumps(word(i)))

    def caps():
        return [x["text"] for x in s.state(KIT)["captions"]]

    def state_word(i):
        return s.state(KIT)["rec"]["words"][i]

    def open_on(i):
        c.double_click(word(i))
        c.wait_for("!document.getElementById('fixBox').hidden", 5)

    def undo_len():
        return c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]")

    # the page as built: her markup from parts
    mk = c.js("(function(){ var b = document.getElementById('fixBox'), i = document.getElementById('fixIn'), lg = Array.from(document.querySelectorAll('#editStep .legend span'));"
              " return {hidden: b.hidden, cls: b.className, input: [i.type, i.maxLength, i.getAttribute('aria-label')], ok: document.getElementById('fixOk').textContent,"
              " back: [document.getElementById('fixBack').textContent, document.getElementById('fixBack').title, document.getElementById('fixBack').className, document.getElementById('fixBack').hidden],"
              " no: [document.getElementById('fixNo').textContent, document.getElementById('fixNo').getAttribute('aria-label'), document.getElementById('fixNo').className],"
              " legend: lg.map(function(e){ return [e.className, e.textContent]; }).slice(-2), btns: Array.from(b.querySelectorAll('button')).every(function(x){ return x.type === 'button'; })}; })()")
    case("her fix box is in the page, hidden, as she wrote it: the input (text, 80 at most, \"The right words\"), Fix, Undo fix (hidden, \"Go back to what was heard\"), × (\"Cancel\")",
         mk["hidden"] and mk["cls"] == "fixbox" and mk["input"] == ["text", 80, "The right words"] and mk["ok"] == "Fix"
         and mk["back"] == ["Undo fix", "Go back to what was heard", "fx", True] and mk["no"] == ["×", "Cancel", "fx"] and mk["btns"], mk)
    case("...and the legend ends with her \"Fixed word\" (dotted) and her hint, \"Wrong word? Double-click it and type the right one.\"",
         mk["legend"] == [["fixed", "Fixed word"], ["lfix", "Wrong word? Double-click it and type the right one."]], mk["legend"])
    lg = c.js("(function(){ var f = document.querySelector('#editStep .legend .fixed'), h = document.querySelector('#editStep .legend .lfix'), cs = getComputedStyle(f);"
              " return [cs.textDecorationLine, cs.textDecorationStyle, h.getBoundingClientRect().left > f.getBoundingClientRect().right, getComputedStyle(h).fontStyle]; })()")
    case("...the legend's Fixed word is underlined dotted, and the hint sits at the legend's right, slanted", lg == ["underline", "dotted", True, "italic"], lg)

    # double-click a word: the box, above the word, with the word in it; the video paused; the highlight bar gone
    c.js("document.getElementById('vid').pause(); document.getElementById('vid').currentTime = 0")
    c.wait_for("document.getElementById('vid').paused && document.getElementById('vid').currentTime === 0", 5)
    c.js("window.__seeks.length = 0")
    undo0 = undo_len()
    open_on(3)
    try:
        c.wait_for("window.__seeks.length >= 1", 5)       # the first click's jump (the browser hands the event over a moment later)
    except Exception:  # noqa: BLE001
        pass
    b, r = box(), c.rect(word(3))
    case("double-click a word and the box opens with that word in it, above the word and centered on it, the input focused and its text selected; Undo fix is not shown",
         b and b["val"] == "we" and not b["back"] and b["focus"] and abs(b["y"] + b["h"] + 8 - r["y"]) < 1.5 and abs(b["x"] + b["w"] / 2 - r["cx"]) < 2 and b["x"] >= 8
         and c.js("document.getElementById('fixIn').selectionStart === 0 && document.getElementById('fixIn').selectionEnd === 2"), (b, r))
    case("...the video is paused (her first click of the two played from the word), the highlight bar is gone, no words are highlighted",
         b["paused"] and b["bar"] == "none" and b["sel"] and len(c.js("window.__seeks")) >= 1, b)
    case("...the 3-second look waits while the box is open, and T.pickerOpen() counts it (so the keys leave the video and the timeline alone)",
         c.js("!window.Talk.quiet() && window.Talk.pickerOpen() && window.Talk.fixOpen()"))
    was = rev()
    c.type_text("wee")
    c.key("Enter")
    moved(was)
    st3 = state_word(3)
    case("type the right word and press Enter: the whole map of fixes is saved ({\"3\": \"wee\"}), the box closes, her toast \"Fixed. Your captions use it now.\"",
         fixes() == {"3": "wee"} and box() is None and toast() == W["fixed_toast"], (fixes(), toast()))
    case("...the state carries the fixed word as the word and what was heard as w0, on that word only",
         st3["w"] == "wee" and st3["w0"] == "we" and "w0" not in state_word(2), (st3, state_word(2)))
    case("...on the page the word reads \"wee\", dotted underline (class fixed), with her hover line naming what was heard",
         c.text(word(3)) == "wee" and "fixed" in cls(3) and title(3) == 'You fixed this. It was heard as "we".' and title(2) is None
         and c.js("getComputedStyle(document.querySelector(%s)).textDecorationStyle" % json.dumps(word(3))) == "dotted", (c.text(word(3)), cls(3), title(3)))
    case("...the captions use the fixed word (and never the heard one); one Undo step", "wee" in caps() and "we" not in caps() and undo_len() == [undo0[0] + 1, 0], (caps()[:5], undo_len()))
    case("...cuts and timing did not change", s.rec(KIT)["cut"] == [[4, 4]] and st3["start"] == WORDS[3]["start"] and st3["end"] == WORDS[3]["end"], st3)
    # a single click still plays from the word
    c.js("window.__seeks.length = 0")
    c.click(word(3))
    c.wait_for("!document.getElementById('vid').paused && window.__seeks.length >= 1", 5)
    seeks = c.js("window.__seeks")
    case("a single click on a fixed word still plays from there", abs(seeks[-1] - (WORDS[3]["start"] - 0.05)) < 0.002 and box() is None, seeks)
    c.js("document.getElementById('vid').pause()")
    c.wait_for("document.getElementById('vid').paused", 5)
    # Esc: nothing saved
    before = s.rec_bytes(KIT)
    open_on(5)
    c.type_text("x")
    c.key("Escape")
    case("Esc closes the box and saves nothing", box() is None and s.rec_bytes(KIT) == before and not c.js("window.Talk.fixOpen()"))
    # highlight three words, press Fix the words, type three: one each; a word typed as heard is no fix
    pick_words(5, 7)
    bar_press("selFix")
    c.wait_for("!document.getElementById('fixBox').hidden", 5)
    b = box()
    case("highlight words and press Fix the words: the box opens with those words in it (\"at the beach.\"), the highlight let go",
         b and b["val"] == "at the beach." and not b["back"] and b["sel"] and b["bar"] == "none", b)
    was = rev()
    c.type_text("at a bench.")
    c.key("Enter")
    moved(was)
    case("the same number of words typed as highlighted: one each; a word typed as it was heard (\"at\") is no fix",
         fixes() == {"3": "wee", "6": "a", "7": "bench."} and c.text(word(6)) == "a" and c.text(word(5)) == "at" and "fixed" not in cls(5), fixes())
    # fewer words typed: all on the first, the rest show nothing (grey, slanted, the heard word)
    pick_words(5, 7)
    bar_press("selFix")
    c.wait_for("!document.getElementById('fixBox').hidden", 5)
    b = box()
    case("opened again on fixed words, the box shows the fixed words, and Undo fix is there now", b and b["val"] == "at a bench." and b["back"], b)
    was = rev()
    c.type_text("at home")
    c.key("Enter")
    moved(was)
    gone = c.js("(function(){ var e = document.querySelector(%s), cs = getComputedStyle(e); return [e.textContent, cs.color, cs.fontStyle]; })()" % json.dumps(word(6)))
    case("two words typed for three: all of it goes on the first word, and the other two show nothing (saved as \"\"): grey, slanted, showing the heard word",
         fixes() == {"3": "wee", "5": "at home", "6": "", "7": ""} and "gone" in cls(6) and "gone" in cls(7) and gone == ["the", "rgb(185, 180, 178)", "italic"]
         and c.text(word(5)) == "at home" and title(6) == 'You fixed this. It was heard as "the".', (fixes(), cls(6), gone))
    w6 = state_word(6)
    case("...the state carries the word typed away as \"\" with its w0, so every word keeps its number (the stretch below still lands on its words)",
         w6["w"] == "" and w6["w0"] == "the" and len(s.state(KIT)["rec"]["words"]) == len(SAID), w6)
    cp = caps()
    case("...no caption for a word typed away, and the fixed words are the captions", "" not in cp and "the" not in cp and "beach." not in cp and "at home" in cp, cp)
    # Undo fix: back to what was heard
    pick_words(5, 7)
    bar_press("selFix")
    c.wait_for("!document.getElementById('fixBox').hidden", 5)
    b = box()
    was = rev()
    c.click("#fixBack")
    moved(was)
    case("Undo fix (shown since one of them was fixed; the box showed \"at home\"): those words go back to what was heard, her toast \"Back to what was heard\"",
         b["val"] == "at home" and b["back"] and fixes() == {"3": "wee"} and toast() == W["fix_back_toast"] and "gone" not in cls(6) and c.text(word(6)) == "the"
         and title(6) is None, (fixes(), toast()))
    # an empty box
    before = s.rec_bytes(KIT)
    open_on(3)
    c.key("Backspace")
    c.key("Enter")
    case("an empty box: her toast \"Type the right word first. To take a word out, use Cut.\", the box stays, nothing saved",
         toast() == W["fix_empty"] and box() is not None and s.rec_bytes(KIT) == before, toast())
    c.key("Escape")
    # typed as it was heard: the fix is taken off
    open_on(3)
    was = rev()
    c.type_text("we")
    c.key("Enter")
    moved(was)
    case("the heard word typed back over a fixed one takes the fix off: no fixes, no underline, no hover line", fixes() == {} and "fixed" not in cls(3) and title(3) is None, fixes())
    # Undo and Redo carry the fixes (her snap() includes them)
    u = undo_len()
    was = rev()
    c.click("#tlUndo")
    moved(was)
    case("Undo brings the fix back (a step carries the fixes, hers)", fixes() == {"3": "wee"} and "fixed" in cls(3) and undo_len() == [u[0] - 1, u[1] + 1], (fixes(), undo_len()))
    was = rev()
    c.click("#tlRedo")
    moved(was)
    case("...and Redo takes it off again", fixes() == {} and "fixed" not in cls(3) and undo_len() == u, (fixes(), undo_len()))
    # a fix on a cut word is allowed (hers)
    open_on(4)
    was = rev()
    c.type_text("wore")
    c.key("Enter")
    moved(was)
    case("a cut word can be fixed too: crossed out and fixed", fixes() == {"4": "wore"} and sorted(cls(4)) == ["cut", "fixed"] and c.text(word(4)) == "wore", (fixes(), cls(4)))
    was = rev()
    c.click("#tlUndo")
    moved(was)
    case("...Undo takes that off", fixes() == {} and cls(4) == ["cut"], (fixes(), cls(4)))
    # ours: the keys typed in the box reach neither the video nor the timeline
    c.click(".tl-clip", nth=0)
    before, u2 = s.rec_bytes(KIT), undo_len()
    open_on(3)
    c.type_text(" ")
    c.key("Delete")
    c.key("Backspace")
    c.key("Mod+z")
    case("ours: the spacebar typed in the box plays nothing, Delete deletes no clip (one is picked on the timeline), and Undo's key undoes nothing",
         c.js("document.getElementById('vid').paused") and box() is not None and s.rec_bytes(KIT) == before and undo_len() == u2, (box(), undo_len()))
    c.key("Escape")
    # ours: Escape in the box lets go of nothing on the timeline
    c.click(".tl-clip", nth=0)
    c.click(".tl-clip", nth=1, meta=True)
    picked = c.js("window.Talk.tl().picked")
    c.js("window.Talk.openFix(3, 3, null)")
    c.wait_for("!document.getElementById('fixBox').hidden", 5)
    c.key("Escape")
    still = c.js("window.Talk.tl().picked")
    c.key("Escape")
    case("ours: with two clips picked on the timeline, Escape in the box closes the box and leaves them picked (hers would let go of them too); the next Escape lets go",
         len(picked) == 2 and box() is None and still == picked and len(c.js("window.Talk.tl().picked")) <= 1, (picked, still))
    # ours: a press outside closes it; a press on the highlight bar's button does not
    before = s.rec_bytes(KIT)
    open_on(3)
    c.click("h1")
    case("a press anywhere outside the box closes it, saving nothing", box() is None and s.rec_bytes(KIT) == before)
    # ours: the box is placed again when the page scrolls (hers stays where it was), and closes once its word is out of the window
    c.desktop(size=(1280, 520))
    try:
        c.js("window.Talk.sizeDock()")
        open_on(3)
        y0 = box()["y"]
        c.js("window.scrollBy(0, -20)")
        c.wait_for("Math.abs(document.getElementById('fixBox').getBoundingClientRect().top - %f) < 1" % (y0 + 20), 5, tell="document.getElementById('fixBox').getBoundingClientRect().top")
        case("ours: the box follows its word when the page scrolls", abs(box()["y"] - (y0 + 20)) < 1, (y0, box()["y"]))
        c.js("window.scrollTo(0, 0)")
        c.wait_for("document.getElementById('fixBox').hidden", 5)
        out = c.js("(function(){ var r = window.Talk.wordEl(3).getBoundingClientRect(); return r.top > innerHeight || r.bottom < 0; })()")
        case("...and closes once its word has scrolled out of the window (nothing saved)", out and box() is None and s.rec_bytes(KIT) == before, out)
    finally:
        c.desktop()
    c.js("window.scrollTo(0, 0)")
    # ours: a change from the chat that arrives while the box is open is not drawn under it; it is drawn when the box closes
    open_on(3)
    c.js("window.__keep = window.Talk.wordEl(3)")
    s.cut(KIT, [[0, 0]], replace=True)
    c.js("window.Talk.poll(false)")
    c.wait_for("(window.Talk.REC.cut || []).length === 1 && window.Talk.REC.cut[0][1] === 0", 10)
    held = c.js("[window.__keep.isConnected, window.Talk.scriptStale(), !document.getElementById('fixBox').hidden]")
    c.key("Escape")
    c.wait_for("!window.__keep.isConnected", 5)
    case("a change from the chat that arrives while the box is open is not drawn under it, and is drawn as soon as the box closes",
         held == [True, True, True] and "cut" in cls(0) and "cut" not in cls(4) and not c.js("window.Talk.scriptStale()"), (held, cls(0)))
    s.cut(KIT, [[4, 4]], replace=True)
    c.js("window.Talk.poll(true)")
    c.wait_for("(window.Talk.REC.cut || []).length === 1 && window.Talk.REC.cut[0][0] === 4", 10)
    case("(the record is as it was before this: word 4 cut, no fix)", s.rec(KIT)["cut"] == [[4, 4]] and fixes() == {} and box() is None)


def video_picker(t, c, s, kit, W, rev, moved, toast, full, shots, pick_words, bar_press, word):
    case, wait_for = t.case, t.wait_for
    q = c.js("window.Talk.Q")            # the kit as the page itself spells it in an address
    shutil.copyfile(str(t.FIXTURE), str(kit / "Footage" / "bts.mp4"))
    n0 = len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]])
    c.click("#vpRefresh")
    c.wait_for("document.querySelectorAll('#vpList .vcard').length === 1", 15)
    n1 = len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]])
    card = c.js("(function(){ var b = document.querySelector('#vpList .vcard'); return [b.querySelector('b').textContent, b.querySelector('span').textContent, b.disabled, b.tagName]; })()")
    first_time = card[1] != "0:03"
    case("I added videos reads the folder again: the new video is there by name" + (", \"getting it ready\", and can't be opened yet" if first_time else ""),
         n1 == n0 + 1 and card[0] == "bts.mp4" and card[3] == "BUTTON" and ((card[1].endswith(" · getting it ready") and card[2] is True) if first_time else True), card)
    asked = [r_["url"] for r_ in list(c.requests) if "/reel-footage" in r_["url"]]
    case("the list is the reel page's own, asked for=talking: the reel page's record is neither made nor written",
         all(u.endswith("&for=talking") for u in asked) and not (kit / ".kit" / "reel-page.json").exists(), asked[:2])
    c.wait_for("(function(){ var b = document.querySelector('#vpList .vcard'); return b && !b.disabled; })()", 90, every=0.5,
               tell="document.querySelector('#vpList .vcard span').textContent")
    card = c.js("(function(){ var b = document.querySelector('#vpList .vcard'); return [b.querySelector('span').textContent, b.querySelector('.vs').style.backgroundImage]; })()")
    case("by itself (the picker reads again every 4 seconds while a video is being got ready) it goes from \"getting it ready\" to playable, with its length and its first still",
         card[0] == "0:03" and "/reel-strip?kit=" in card[1] and "&n=" in card[1], card)
    shown = c.js("getComputedStyle(document.querySelector('#vpList .vcard .vs')).backgroundImage")
    case("...the still shows even though the shoot's name has an apostrophe in it (the address is made safe for a style)",
         "'" in KIT and shown.startswith("url(") and "%27" in shown, shown)
    n2 = len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]])
    time.sleep(5)
    case("...and once every video is ready it stops reading the list", len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]]) == n2)
    c.click("#vpList .vcard")
    c.wait_for("!document.getElementById('vpPlayer').hidden && document.getElementById('vpVid').readyState >= 1", 15,
               tell="document.getElementById('vpVid').error && document.getElementById('vpVid').error.message")
    pv = c.js("(function(){ var v = document.getElementById('vpVid'); return [v.getAttribute('src').split('&key=')[0], v.muted, document.querySelector('#vpList .vcard').classList.contains('on'), document.getElementById('vpAt').textContent, Math.round(v.duration)]; })()")
    case("click a video: it lights up and its player opens, muted, played from this computer by its key; \"Starts at 0:00.0\"",
         pv == ["/reel-video?" + q, True, True, "Starts at 0:00.0", 3], pv)
    c.js("document.getElementById('vpVid').currentTime = 1.27")
    try:
        c.wait_for("document.getElementById('vpAt').textContent === 'Starts at 0:01.2'", 5)
    except Exception:  # noqa: BLE001
        pass
    case("\"Starts at m:ss.t\" follows the player", c.text("#vpAt") == "Starts at 0:01.2", c.text("#vpAt"))
    # a second video arrives while the player is open: the list is not redrawn under their hand
    shutil.copyfile(str(t.FIXTURE), str(kit / "Footage" / "second.mp4"))
    c.js("window.__card = document.querySelector('#vpList .vcard')")
    c.click("#vpRefresh")
    c.wait_for("document.querySelectorAll('#vpList .vcard').length === 2", 15)
    c.js("window.__card = document.querySelector('#vpList .vcard'); window.__n = 0")
    wait_for(lambda: any(v["preview"] == "ready" for v in c.js("window.Talk.vids()") if v["name"] == "second.mp4"), 90, 0.5)
    case("while the player is open the list is never redrawn by the 4-second read (it would jump under their hand)",
         c.js("window.__card.isConnected") and c.js("Math.abs(document.getElementById('vpVid').currentTime - 1.27) < 0.05"), c.js("document.getElementById('vpVid').currentTime"))
    try:
        c.wait_for("!document.querySelectorAll('#vpList .vcard')[1].disabled", 10)
    except Exception:  # noqa: BLE001
        pass
    two = c.js("(function(){ var b = document.querySelectorAll('#vpList .vcard')[1]; return [b.querySelector('span').textContent, b.querySelector('.vs').style.backgroundImage.indexOf('/reel-strip?') >= 0, b.querySelector('.vs').textContent,"
               " window.__card.isConnected, !document.getElementById('vpPlayer').hidden]; })()")
    case("...yet a video that gets ready while the player is open can be pressed at once: its card changes where it is (its length, its still), nothing is drawn again",
         two == ["0:03", True, "", True, True], two)
    c.click("#vpList .vcard", nth=1, check=False)
    try:
        c.wait_for("document.querySelectorAll('#vpList .vcard')[1].classList.contains('on') && document.getElementById('vpVid').readyState >= 1 && document.getElementById('vpAt').textContent === 'Starts at 0:00.0'", 15)
    except Exception:  # noqa: BLE001
        pass
    case("...and a click on it opens it at its beginning, the list still the same cards",
         c.js("window.__card.isConnected && !window.__card.classList.contains('on') && document.querySelectorAll('#vpList .vcard')[1].classList.contains('on')"
              " && document.getElementById('vpAt').textContent === 'Starts at 0:00.0' && document.getElementById('vpVid').getAttribute('src').indexOf('/reel-video?') === 0"), c.text("#vpAt"))
    c.click("#vpList .vcard", nth=0)
    c.wait_for("window.__card.classList.contains('on') && document.getElementById('vpVid').readyState >= 1 && document.getElementById('vpAt').textContent === 'Starts at 0:00.0'", 15)
    c.js("document.getElementById('vpVid').currentTime = 1.27")
    c.wait_for("document.getElementById('vpAt').textContent === 'Starts at 0:01.2'", 5, tell="document.getElementById('vpAt').textContent")
    was = rev()
    c.click("#vpUse")
    moved(was)
    x = full(0)
    case("Use from here: a video stretch on those words, by the video's name in the record, its start to a tenth of a second, Full screen, nothing moved",
         x == {"a": 0, "b": 2, "ns": [], "v": "bts.mp4", "from": 1.3, "spot": "full", "pos": None, "me": None}
         and not c.js("document.getElementById('vpick').classList.contains('open')") and c.js("document.getElementById('vpVid').paused"), x)
    c.wait_for("document.querySelectorAll('#script .seg.vid[data-a=\"0\"]').length === 3", 5)
    c.wait_for("Array.from(document.querySelectorAll('#script .sthumbs img')).every(function(i){ return i.complete; })", 10)
    segs = c.js("window.__segs(0)")
    case("a video's bar is blue-green, with its first still and \"▶ name\" without its ending, and no spot word",
         all("vid" in g["cls"].split() for g in segs) and segs[0]["em"] == "▶ bts" and len(segs[0]["imgs"]) == 1 and segs[0]["imgs"][0][0].startswith("/reel-strip?" + q)
         and segs[0]["imgs"][0][3] and c.js("getComputedStyle(document.querySelector('#script .seg.vid')).backgroundColor") in ("rgb(217, 238, 240)", "rgb(185, 221, 225)", "rgb(201, 230, 233)"), segs[0])
    case("...and the page jumps to the first of those words", abs(c.js("document.getElementById('vid').currentTime") - max(0, WORDS[0]["start"] - 0.05)) < 0.01)
    st = s.state(KIT)
    case("the state now names that video's first still, so the bar shows it on the next visit without asking for the Footage list",
         len(st["stills"]) == 1 and all(type(v) is int for v in st["stills"].values()), st["stills"])
    # Change video: opens on the video it has, at its start
    c.click('#script .seg[data-a="0"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    case("a video's menu: Change video and Remove", c.js("window.__menu().acts") == ["Change video", "Remove"], c.js("window.__menu().acts"))
    c.click("#pmenu [data-m='change']")
    c.wait_for("document.getElementById('vpick').classList.contains('open') && !document.getElementById('vpPlayer').hidden", 15)
    c.wait_for("document.getElementById('vpAt').textContent === 'Starts at 0:0%.1f'" % x["from"], 10, tell="document.getElementById('vpAt').textContent")
    on = c.js("Array.from(document.querySelectorAll('#vpList .vcard')).map(function(b){ return [b.querySelector('b').textContent, b.classList.contains('on'), b.disabled]; })")
    case("Change video opens on the video it has, at its start point; the second video is there and ready too",
         on == [["bts.mp4", True, False], ["second.mp4", False, False]], on)
    c.click("#vpList .vcard", nth=1)
    c.wait_for("document.getElementById('vpAt').textContent === 'Starts at 0:00.0' && document.getElementById('vpVid').readyState >= 1", 15, tell="document.getElementById('vpAt').textContent")
    case("clicking another video puts the start back to 0", c.js("document.querySelectorAll('#vpList .vcard')[1].classList.contains('on')"))
    before = s.rec_bytes(KIT)
    c.click("#vpClose")
    case("Close: the picker goes, the player stops, and nothing is changed",
         not c.js("document.getElementById('vpick').classList.contains('open')") and c.js("document.getElementById('vpVid').paused") and s.rec_bytes(KIT) == before)
    c.click('#script .seg[data-a="0"]', nth=1, check=False)
    c.wait_for("document.getElementById('pmenu').classList.contains('open')", 5)
    c.click("#pmenu [data-m='change']")
    c.wait_for("document.getElementById('vpick').classList.contains('open') && !document.getElementById('vpPlayer').hidden", 15)
    c.click((6, 6))
    case("a press outside the sheet closes it, the player stops, and nothing is changed",
         not c.js("document.getElementById('vpick').classList.contains('open')") and c.js("document.getElementById('vpVid').paused") and s.rec_bytes(KIT) == before)
    # a new video over a photo that was moved: its spot and where they sit, never where the photo sat
    was = rev()
    c.js("window.Talk.save({shots: window.Talk.shotsOut(window.Talk.SH).concat([{a: 4, b: 6, ns: [4], v: null, from: 0, spot: 'center', pos: {x: 0.4, y: 0.3, w: 0.5}, me: {x: 0.3, y: 0.7, w: 0.3}}])})")
    moved(was)
    pick_words(5, 7)
    bar_press("selVideo")
    c.wait_for("document.querySelectorAll('#vpList .vcard').length === 2", 10)
    c.click("#vpList .vcard", nth=1)
    c.wait_for("!document.getElementById('vpPlayer').hidden && document.getElementById('vpVid').readyState >= 1", 15)
    was = rev()
    c.click("#vpUse")
    moved(was)
    case("a new video always starts where videos sit by themselves: it takes the spot and where they sit of the stretch under it, never where that photo sat",
         full(5) == {"a": 5, "b": 7, "ns": [], "v": "second.mp4", "from": 0.0, "spot": "center", "pos": None, "me": {"x": 0.3, "y": 0.7, "w": 0.3}} and (full(4)["a"], full(4)["b"]) == (4, 4), (full(5), full(4)))
    case("...and the reel page's record was never made by any of it", not (kit / ".kit" / "reel-page.json").exists())
    # a video that can't be got ready: this page's own line, never the reel page's
    import os
    bad = kit / "Footage" / "zz-broken.mov"
    bad.write_bytes(b"not a video at all " * 400)
    old = time.time() - 7200
    os.utime(str(bad), (old, old))                    # not "still being copied in"
    pick_words(18, 19)
    bar_press("selVideo")
    c.wait_for("document.querySelectorAll('#vpList .vcard').length === 3", 15)
    want = W["vp_cant"].replace("{length}", "0:00")
    try:
        c.wait_for("document.querySelectorAll('#vpList .vcard')[2].querySelector('span').textContent === %s" % json.dumps(want), 30)
    except Exception:  # noqa: BLE001
        pass
    card = c.js("(function(){ var b = document.querySelectorAll('#vpList .vcard')[2]; return [b.querySelector('b').textContent, b.querySelector('span').textContent, b.disabled]; })()")
    import reel_page
    theirs = [reel_page.WORDS["vid_failed"], reel_page.WORDS["vid_lowspace"]]
    case("a Footage video that can't be got ready says so in this page's own line (ours, with its reason), can't be opened, and never shows the reel page's \"The moments and your reel still work\"",
         card == ["zz-broken.mov", want, True] and "vp_cant" in s.tp.OUR_WORDS and "vp_lowspace" in s.tp.OUR_WORDS
         and not any(x in c.text("#vpList") for x in theirs) and "still work" not in c.text("#vpList"), card)
    recs = [p_ for p_ in (kit / ".kit" / "footage").glob("*/preview.json") if json.loads(p_.read_text(encoding="utf-8")).get("state") == "failed"]
    if len(recs) == 1:
        recs[0].write_text(json.dumps({"state": "lowspace", "words": reel_page.WORDS["vid_lowspace"]}), encoding="utf-8")
        c.click("#vpRefresh")
        want = W["vp_lowspace"].replace("{length}", "0:00")
        try:
            c.wait_for("document.querySelectorAll('#vpList .vcard')[2].querySelector('span').textContent === %s" % json.dumps(want), 10)
        except Exception:  # noqa: BLE001
            pass
    case("...and when the reason is a nearly full drive, this page's own line for that",
         len(recs) == 1 and c.js("document.querySelectorAll('#vpList .vcard')[2].querySelector('span').textContent") == want and "still work" not in c.text("#vpList"), (len(recs), c.text("#vpList")))
    n = len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]])
    time.sleep(5)
    case("...and a video that can't be got ready does not keep the 4-second read going", len([1 for r_ in list(c.requests) if "/reel-footage" in r_["url"]]) == n)
    c.click("#vpClose")
