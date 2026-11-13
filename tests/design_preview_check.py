#!/usr/bin/env python3
"""Check the small picture of a design that the designer's page sends for the post kit (Nicole's v24).

    python3 tests/guard.py 3000 python3 tests/design_preview_check.py --work /private/tmp/somewhere [--port 9640]

It is also a part of tests/design_check.py (--only preview). The routes by request, with every refusal, are in
tests/design_check.py's server part and tests/pc_design.py; the post kit's card is in tests/kit_cards_check.py.
This file is the real page in a HIDDEN Chrome (tests/chrome_drive.py), on a pretend kit of its own and a page
server of its own:

    the first visit        the assistant's own first design, once the designer has opened it: one picture is sent
                           about 1.5 s later, of the right shape, kept as one hidden file beside the design; the
                           design, its counter and the list of designs are as they were; the kit page shows it
    the shape              1 slide, 3 slides, 8 slides (the first 6), stories (162 by 288 each, the first 4)
    a blank design         nothing is drawn and nothing is sent, and the same for a shoot's one empty story
    several quick changes  one picture, drawn from the last of them
    Save slides            nothing is drawn or sent while it runs (held at its question for longer than the wait);
                           the picture comes after; the slides are byte for byte the ones a page with the preview
                           switched off saves from the same layout
    the picture            its first slide is slide 1 as it was saved, small, within a tolerance (and is not
                           slide 2); the gaps are white (needs Pillow; SKIP without it)
    refused                the Assistant refuses the picture: no words on the page, no error, no box
    a photo not ready      a photo whose small copy can't be had yet is waited for, then the picture is sent

Nothing outside --work is touched: the pretend kit, its page server (a port of this test's own, never the real
pages') and the hidden Chrome are all this test's, and are stopped at the end. No folder is opened. Every line
says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
W, H = 1080, 1350

# No folder is ever opened from this test's page.
NO_FINDER_JS = r"""
(function(){
  var real = window.fetch;
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) return Promise.resolve(new Response(JSON.stringify({ok: true, words: 'Opened.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    return real.apply(this, arguments);
  };
})();
"""
# The preview switched off for one page: the moment the page makes its previewer, its wait is made endless, so it
# never draws and never sends. (The test's own switch; the Assistant has none.)
PREVIEW_OFF_JS = r"""
(function(){
  var real;
  Object.defineProperty(window, 'Designer', {configurable: true, get: function(){ return real; }, set: function(v){
    real = v;
    var pv;
    try { Object.defineProperty(v, 'previewer', {configurable: true, get: function(){ return pv; }, set: function(p){ pv = p; p.rules.wait = 1e9; }}); } catch (e) {}
  }});
})();
"""
# The picture held at the door: while window.__pvGate is true, the page's POST of a preview waits (so the test can
# change what the Assistant will answer). Everything else goes straight through.
GATE_JS = r"""
(function(){
  var real = window.fetch;
  window.__pvGate = false; window.__pvHeld = 0;
  window.fetch = function(u, o){
    if (String(u).indexOf('/design-preview') === 0 && window.__pvGate) {
      var self = this, a = arguments;
      window.__pvHeld += 1;
      return new Promise(function(ok){ (function w(){ if (window.__pvGate) setTimeout(w, 30); else ok(real.apply(self, a)); })(); });
    }
    return real.apply(this, arguments);
  };
})();
"""


def _frame(i, n, x, y=0, w=W, h=H, **more):
    b = {"id": i, "n": n, "x": x, "y": y, "w": w, "h": h, "ox": 0.5, "oy": 0.5, "zoom": 1}
    b.update(more)
    return b


def shape(slides, stories=False):
    n = min(slides, 4 if stories else 6)
    w, h = (162, 288) if stories else (216, 270)
    return n * w + (n - 1) * 6, h


def check_preview_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(SCRIPTS))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the design preview on the real page: no Chrome on this computer", flush=True)
        return
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        Image = None
    target = work / "preview-browser"
    ok, out = make_kit(target, "Preview beach", 14)
    if not case("preview browser: the pretend kit was made", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    os.environ["STUDIO_HOME"] = str(studio)         # for design.jpeg_size below (it reads nothing, but imports arrange)
    import design as design_mod
    kit_name = "2026-11-01 Preview beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs, sdesigns, carousel = kit / ".kit" / "designs", kit / ".kit" / "story-designs", kit / "Carousel"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    nums = [x["n"] for x in sheet]
    srv = Server(env, port)
    P = srv.start()
    base = f"http://127.0.0.1:{P}"
    tokens = [0]

    def pv_file(i, stories=False):
        return (sdesigns if stories else designs) / f"{i}.preview.jpg"

    def size_of(path):
        return design_mod.jpeg_size(path.read_bytes())

    try:
        with cd.Chrome(work=work / "chrome-preview", size=(1280, 900)) as c:
            c.init_script(NO_FINDER_JS)
            gate = c.init_script(GATE_JS)

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def ready(seconds=25):
                c.wait_for("window.Designer && Designer.saver && Designer.previewer && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total",
                           seconds, tell="document.body.innerText.slice(0, 300)")

            def stats():
                return J("Designer.previewer.stats")

            def posts(path="/design-preview"):
                return [r for r in list(c.requests) if r.get("method") == "POST" and r["url"].split("?")[0] == base + path]

            def kept(n, seconds=15):
                """Wait until the page has had n pictures taken by the Assistant. -> True, or False when the time ran out"""
                try:
                    c.wait_for("Designer.previewer.stats.kept >= %d && !Designer.previewer.busy()" % n, seconds)
                    return True
                except cd.Timeout:
                    return False

            def quiet(seconds):
                """Let the page be for longer than the preview's wait."""
                time.sleep(seconds)

            def words():
                return c.js("document.body.innerText")

            def new_design(state=None, name=None, kind=None):
                tokens[0] += 1
                body = {"kit": kit_name, "token": f"previewcheck{tokens[0]:04d}"}
                if state is not None:
                    body.update(stamp=get_json(P, f"/design-state?kit={KQ}")[1]["stamp"], state=state)
                if name:
                    body["name"] = name
                code, out = post(P, "/design-new", body)
                if code != 200 or not out or not out.get("ok"):
                    case("preview browser: a design was made for this part", False, (code, out))
                    raise RuntimeError("no design")
                return out["design"]["id"]

            def open_design(i=None, stories=False):
                c.clear_errors()
                c.open(f"{base}/design.html?kit={KQ}" + ("&kind=stories" if stories else "") + (f"&design={i}" if i else ""))
                ready()

            # ---------- the first visit: the assistant's own first design, once the designer has opened it ----------
            case("first visit: before it, the shoot has no design and no picture", not designs.exists() or not any(designs.iterdir()))
            t0 = time.time()
            open_design()
            A = c.js("Designer.design.id")
            a_slides = c.js("Designer.st.slides")

            a_file = designs / f"{A}.json"
            a_bytes = a_file.read_bytes()
            got = kept(1)
            took = time.time() - t0
            case("first visit: the page sent one picture of the design by itself, about a second and a half after it opened", got and len(posts()) == 1
                 # a first try may find a photo's small copy not made yet (a slow machine: GitHub's Mac did);
                 # the page then waits and tries again by itself, which is the design. What must hold is
                 # one picture drawn, one sent, one kept, none refused, and no more tries than the page allows.
                 and stats() == dict(stats(), sent=1, kept=1, refused=0, drawn=1)
                 and 0 <= stats()["failed"] <= c.js("Designer.previewer.rules.tries"), (stats(), len(posts()), round(took, 1)))
            req = posts()[0] if posts() else {"url": "", "status": None}
            case("first visit: ...to /design-preview, naming the kit by its folder name, the design by its id and the layout by its counter; answered 200",
                 f"kit={KQ}" in req["url"] and f"design={A}" in req["url"] and "rev=0" in req["url"] and req["status"] == 200 and "kind=" not in req["url"], req)
            case("first visit: the picture is kept beside the design as '<id>.preview.jpg', the first %d slides at 216 by 270 with 6 px between" % min(a_slides, 6),
                 pv_file(A).is_file() and size_of(pv_file(A)) == shape(a_slides), (pv_file(A).is_file() and size_of(pv_file(A)), shape(a_slides)))
            case("first visit: it is a small file (under 1 MB; here %d KB)" % (pv_file(A).stat().st_size // 1024 if pv_file(A).is_file() else 0),
                 pv_file(A).is_file() and 500 < pv_file(A).stat().st_size < 1024 * 1024)
            case("first visit: the design is byte for byte as it was (its counter still 0), and it is still the only file of a design",
                 a_file.read_bytes() == a_bytes and sorted(p.name for p in designs.iterdir() if not p.is_dir()) == sorted([a_file.name, pv_file(A).name]),
                 sorted(p.name for p in designs.iterdir()))
            case("first visit: no scratch file is left, and no Carousel folder was made", not [p for p in designs.iterdir() if p.name.startswith(".")] and not carousel.exists())
            case("first visit: the page shows no error and no box, and the line beside Save slides is empty",
                 not c.page_errors() and not c.dialogs and c.text("#save-line") == "", (c.page_errors(), c.dialogs))
            code, st = get_json(P, f"/design-state?kit={KQ}&design={A}")
            case("first visit: to the Assistant it is still the design nobody has changed (it counts as no saved design)", st["design"]["untouched"] is True and st["design"]["rev"] == 0
                 and [s["designs"] for s in st["shoots"] if s["kit"] == kit_name] == [0], st["design"].get("untouched"))
            import http.client
            hc = http.client.HTTPConnection("127.0.0.1", P, timeout=15)
            hc.request("GET", f"/content/{KQ}/Post%20kit.html")
            kit_page = hc.getresponse().read().decode("utf-8", "replace")
            hc.close()
            a_name = st["design"]["name"]
            case("first visit: the post kit's Carousel card now shows that picture and her line 'A preview of %s: your slides aren't saved yet'" % a_name,
                 f"<img class='dprev' src='/design-preview?kit={KQ}&amp;design={A}&amp;v=" in kit_page and f"A preview of {a_name}: your slides aren&#x27;t saved yet" in kit_page, kit_page.count("dprev"))
            quiet(2.5)
            case("first visit: left alone, the page sends nothing more", len(posts()) == 1 and stats()["drawn"] == 1, (len(posts()), stats()))
            stamp1 = pv_file(A).stat().st_mtime_ns
            open_design(A)
            c.wait_for("document.getElementById('d-status').textContent === 'Saved'", 10)
            before_words, sent_then = words(), stats()["sent"]
            got = kept(1)
            case("opened again, unchanged: the same picture is drawn and sent, and the Assistant writes nothing (the file's time is as it was)",
                 got and len(posts()) == 1 and pv_file(A).stat().st_mtime_ns == stamp1, (len(posts()), stats()))
            now_words = words()
            case("opened again: the page says nothing about it: every word on the page is as it was before the picture was sent, no error, no box",
                 sent_then == 0 and now_words == before_words and not c.page_errors() and not c.dialogs,
                 (sent_then, [x for x in now_words.splitlines() if x not in before_words.splitlines()][:4], [x for x in before_words.splitlines() if x not in now_words.splitlines()][:4]))

            # ---------- the right shape for each count of slides ----------
            one = new_design({"slides": 1, "bg": "#ffffff", "blocks": [_frame(1, nums[0], 0)]}, "One slide")
            open_design(one)
            got = kept(1)
            case("shape: a design of 1 slide gives a picture of 216 by 270", got and size_of(pv_file(one)) == (216, 270), got and size_of(pv_file(one)))
            eight = new_design({"slides": 8, "bg": "#f4efe6", "blocks": [_frame(i + 1, nums[i], i * W) for i in range(8)]}, "Eight slides")
            open_design(eight)
            got = kept(1)
            case("shape: a design of 8 slides gives its first 6: 1326 by 270", got and size_of(pv_file(eight)) == (1326, 270) == shape(8), got and size_of(pv_file(eight)))
            holes = new_design({"slides": 3, "bg": "#ffffff", "blocks": [_frame(1, None, 0), _frame(2, None, W), _frame(3, None, 2 * W)]}, "Empty frames")
            open_design(holes)
            got = kept(1)
            case("shape: a design of empty frames has something on it (hers: any block counts), so it gets its picture: 660 by 270",
                 got and size_of(pv_file(holes)) == (660, 270), got and size_of(pv_file(holes)))

            # ---------- a blank design: nothing drawn, nothing sent ----------
            blank = new_design({"slides": 5, "bg": "#ffffff", "blocks": []}, "Blank")
            open_design(blank)
            quiet(3.2)
            case("blank: a design with nothing on it is never drawn and never sent, and has no picture",
                 stats() == dict(stats(), sent=0, kept=0, drawn=0, failed=0) and not posts() and not pv_file(blank).exists() and not c.page_errors(), (stats(), len(posts())))

            # ---------- several quick changes: one picture ----------
            c.clear_errors()
            before_n = 0
            for i in range(4):
                c.js("Designer.setState(function(st){ var s = JSON.parse(JSON.stringify(st)); s.bg = '%s'; return s; })" % ("#101010", "#202020", "#303030", "#e8d8c8")[i])
                time.sleep(0.25)
            c.js("Designer.setState(function(st){ var s = JSON.parse(JSON.stringify(st)); s.blocks.push({id: 1, n: %d, x: 0, y: 0, w: 1080, h: 1350, ox: 0.5, oy: 0.5, zoom: 1}); return s; })" % nums[2])
            got = kept(before_n + 1)
            quiet(2.2)
            saves = len(posts("/design"))
            rev = c.js("Designer.save.rev()")
            case("quick changes: five changes a quarter of a second apart (the last puts a photo on the blank design) made %d autosave(s) and ONE picture" % saves,
                 got and saves >= 1 and len(posts()) == 1 and stats()["sent"] == 1 and stats()["drawn"] == 1, (len(posts()), stats()))
            case("quick changes: ...drawn from the last of them (the newest counter), and kept", bool(posts()) and f"rev={rev}" in posts()[0]["url"] and posts()[0]["status"] == 200
                 and size_of(pv_file(blank)) == shape(5), posts()[:1])
            if Image is not None:
                im = Image.open(pv_file(blank)).convert("RGB")
                bg = im.getpixel((216 + 6 + 100, 135))          # slide 2 is bare: the last background
                case("quick changes: ...the picture shows the last background on its bare slides (#e8d8c8), not an earlier one",
                     all(abs(a - b) <= 6 for a, b in zip(bg, (0xe8, 0xd8, 0xc8))), bg)
            else:
                print("SKIP  quick changes: the picture's colours (no Pillow under this Python)", flush=True)

            # ---------- Save slides: nothing beside it, and the same slides with the preview on or off ----------
            layout = {"slides": 4, "bg": "#ffffff", "blocks": [_frame(1, nums[3], 0), _frame(2, nums[4], W, 100, 2 * W, 1100), _frame(3, None, 3 * W + 100, 100, 880, 1150)]}
            off_id = new_design(layout, "Quiet set")
            on_id = new_design(layout, "Loud set")

            def save_from(i, off):
                ident = c.init_script(PREVIEW_OFF_JS) if off else None
                try:
                    open_design(i)
                finally:
                    if ident is not None:
                        c.drop_init_script(ident)
                if not off:
                    kept(1)                         # the picture of the design as it opened
                    c.clear_errors()                # (the page's requests so far are forgotten; what follows is the save's)
                n0, d0 = stats()["sent"], stats()["drawn"]
                c.click("#save-slides")
                c.wait_for("Designer.saver.asking()", 30, tell="document.getElementById('save-line').textContent")
                quiet(3.4)                          # held at its question for more than twice the preview's wait
                during = (stats()["sent"] - n0, stats()["drawn"] - d0, len(posts()))
                c.click("#save-yes")
                c.wait_for("!Designer.saver.busy()", 90, tell="document.getElementById('save-line').textContent")
                return during, c.text("#save-line")

            during_off, line_off = save_from(off_id, True)
            quiet(2.2)
            case("Save slides, preview switched off (this test's own switch): the set is saved, and no picture was ever drawn or sent",
                 "Quiet set" in line_off and stats() == dict(stats(), sent=0, drawn=0) and not posts() and not pv_file(off_id).exists(), (line_off, stats()))
            during_on, line_on = save_from(on_id, False)
            case("Save slides, preview on: while it was held at its question for 3.4 s, nothing was drawn and nothing was sent", during_on == (0, 0, 0), during_on)
            got = kept(2)
            order = [r["url"].split("?")[0].replace(base, "") for r in list(c.requests) if r.get("method") == "POST"]
            case("Save slides, preview on: the set is saved, and the picture is sent only after the last slide and the commit",
                 "Loud set" in line_on and got and order.count("/design-preview") == 1 and order[-1] == "/design-preview"
                 and order.count("/design-slide") == 4 and "/design-commit" in order, order)
            quiet_set = [carousel / ("Quiet set - slide %02d.jpg" % i) for i in range(1, 5)]
            loud_set = [carousel / ("Loud set - slide %02d.jpg" % i) for i in range(1, 5)]
            case("Save slides: the slides saved with the preview on are byte for byte the ones saved with it off (4 slides each)",
                 all(p.is_file() for p in quiet_set + loud_set) and [p.read_bytes() for p in quiet_set] == [p.read_bytes() for p in loud_set],
                 [p.name for p in quiet_set + loud_set if not p.is_file()])
            case("Save slides: the Carousel folder holds those eight slides and nothing else (no picture of a design is ever put there)",
                 sorted(p.name for p in carousel.iterdir() if not p.name.startswith(".")) == sorted(p.name for p in quiet_set + loud_set), sorted(p.name for p in carousel.iterdir()))
            case("Save slides: no error on the page", not c.page_errors(), c.page_errors())

            # ---------- the picture is the slides, small ----------
            if Image is None:
                print("SKIP  the picture against the saved slides (no Pillow under this Python)", flush=True)
            else:
                pv = Image.open(pv_file(on_id)).convert("RGB")

                def far(cell, slide_no):
                    small = Image.open(loud_set[slide_no - 1]).convert("RGB").resize((216, 270), Image.LANCZOS)
                    part = pv.crop((cell * 222, 0, cell * 222 + 216, 270))
                    return sum(ImageStat.Stat(ImageChops.difference(small, part)).mean) / 3.0
                d11, d12, d22, d44 = far(0, 1), far(0, 2), far(1, 2), far(3, 4)
                case("the picture: its first slide is slide 1 as it was saved, made small (mean difference %.1f of 255), and is not slide 2 (%.1f)" % (d11, d12),
                     pv.size == (4 * 216 + 18, 270) and d11 < 8 and d12 > 3 * max(d11, 2), (pv.size, d11, d12))
                case("the picture: its second and fourth are slides 2 and 4 (%.1f, %.1f): a photo across two slides, and an empty frame left as background" % (d22, d44), d22 < 8 and d44 < 8, (d22, d44))
                gaps = [pv.getpixel((x, y)) for x in (216 + 2, 216 + 3, 438 + 2, 660 + 3) for y in (5, 135, 265)]
                case("the picture: the 6 px between one slide and the next are white", all(min(px) >= 244 for px in gaps), gaps[:4])

            # ---------- stories: 162 by 288 each, the first four ----------
            open_design(stories=True)
            S = c.js("Designer.design.id")
            quiet(3.2)
            case("stories: a shoot's one empty story is never drawn and never sent", stats() == dict(stats(), sent=0, drawn=0) and not posts() and not pv_file(S, True).exists(), stats())
            code, sst = get_json(P, f"/design-state?kit={KQ}&kind=stories")
            s_state = {"slides": 6, "bg": "#ffffff", "blocks": [_frame(i + 1, nums[i], i * 1080, 0, 1080, 1920) for i in range(6)]}
            code, out = post(P, "/design", {"kit": kit_name, "kind": "stories", "design": S, "stamp": sst["stamp"], "base": sst["design"]["rev"], "page": "previewpage1", "state": s_state})
            if case("stories: (the shoot's stories are given six stories, a photo on each)", code == 200 and out.get("ok"), (code, out)):
                open_design(stories=True)
                got = kept(1)
                req = posts()[0] if posts() else {"url": "", "status": None}
                case("stories: the first four at 162 by 288 (666 by 288), sent with kind=stories and kept beside the stories design, not the carousel's",
                     got and "kind=stories" in req["url"] and req["status"] == 200 and size_of(pv_file(S, True)) == (666, 288) == shape(6, True)
                     and not pv_file(S).exists(), (req, pv_file(S, True).is_file() and size_of(pv_file(S, True))))
                case("stories: no word about it on the page, no error", c.text("#save-line") == "" and not c.page_errors(), c.page_errors())

            # ---------- the Assistant refuses the picture: the page says nothing ----------
            open_design(one)
            kept(1)
            c.clear_errors()
            before_words = words()
            one_file = designs / f"{one}.json"
            was = one_file.read_bytes()
            pic_was = pv_file(one).read_bytes()
            c.js("window.__pvGate = true")
            c.js("Designer.setState(function(st){ var s = JSON.parse(JSON.stringify(st)); s.bg = '#c0ffee'; return s; })")
            try:
                c.wait_for("window.__pvHeld >= 1", 15)
                held = True
            except cd.Timeout:
                held = False
            now = json.loads(one_file.read_text(encoding="utf-8"))
            mine = dict(now, rev=now["rev"] + 1)            # this check's own pretend record: as if it had been changed elsewhere meanwhile
            one_file.write_text(json.dumps(mine, indent=1, ensure_ascii=False), encoding="utf-8")
            n_ref = stats()["refused"]
            c.js("window.__pvGate = false")
            try:
                c.wait_for("Designer.previewer.stats.refused >= %d && !Designer.previewer.busy()" % (n_ref + 1), 15)
                refused = True
            except cd.Timeout:
                refused = False
            req = posts()[-1] if posts() else {"status": None}
            case("refused: a picture drawn from a layout that is no longer the newest is refused by the Assistant (409), and the one it had is kept",
                 held and refused and req["status"] == 409 and pv_file(one).read_bytes() == pic_was, (held, refused, req))
            after_words = words()
            case("refused: the page says nothing: no word, no error, no box, the Save slides line empty, the status still 'Saved'",
                 not c.page_errors() and not c.dialogs and c.text("#save-line") == "" and c.text("#d-status") == "Saved"
                 and after_words.replace("Saved", "").split() == before_words.replace("Saved", "").split(), (c.page_errors(), c.dialogs, c.text("#d-status")))
            one_file.write_text(json.dumps(now, indent=1, ensure_ascii=False), encoding="utf-8")       # the pretend record put back
            c.drop_init_script(gate)
            # the Assistant not answering at all
            open_design(holes)
            kept(1)
            c.clear_errors()
            before_words = words()
            c.block_urls(["*/design-preview*"])
            try:
                n_fail = stats()["failed"]
                c.js("Designer.setState(function(st){ var s = JSON.parse(JSON.stringify(st)); s.bg = '#abcdef'; return s; })")
                try:
                    c.wait_for("Designer.previewer.stats.failed >= %d && !Designer.previewer.busy()" % (n_fail + 1), 15)
                    failed = True
                except cd.Timeout:
                    failed = False
                case("refused: the picture can't be sent at all (the request fails): the page says nothing, shows no error, and the design is saved as always",
                     failed and not c.page_errors() and not c.dialogs and c.text("#save-line") == "" and c.text("#d-status") == "Saved"
                     and json.loads((designs / f"{holes}.json").read_text(encoding="utf-8"))["state"]["bg"] == "#abcdef", (failed, c.page_errors(), c.text("#d-status")))
            finally:
                c.block_urls([])
            c.js("Designer.setState(function(st){ var s = JSON.parse(JSON.stringify(st)); s.bg = '#fedcba'; return s; })")
            got = kept(2)
            case("...and the next good save sends the picture again", got, stats())

            # ---------- a photo whose small copy can't be had yet: waited for, then drawn ----------
            c.block_urls(["*/kit-photo*"])
            try:
                open_design(eight)
                try:
                    c.wait_for("Designer.previewer.stats.failed >= 1 && !Designer.previewer.busy()", 15)
                    waited = True
                except cd.Timeout:
                    waited = False
                case("a photo not ready: while the photos' small copies can't be had, no picture is sent, and the page says nothing (no error from the preview, the Save slides line empty)",
                     waited and stats()["sent"] == 0 and not posts() and c.text("#save-line") == "" and not [e for e in c.page_errors() if "preview" in e.lower()], (stats(), c.page_errors()[:2]))
            finally:
                c.block_urls([])
            got = kept(1, seconds=12)
            case("a photo not ready: ...and once they can be had it is drawn and sent by itself, a few seconds later, with nothing pressed", got and len(posts()) == 1 and posts()[0]["status"] == 200, (stats(), len(posts())))

            # ---------- nothing of theirs was touched, and nothing went anywhere else ----------
            case("nothing was asked of anything but this computer by the preview (the only outside requests are Google's fonts, if any)",
                 all("fonts.g" in u for u in c.outside_requests()), c.outside_requests()[:3])
        log = (studio / "arrange.log").read_text(encoding="utf-8", errors="replace") if (studio / "arrange.log").is_file() else ""
        case("the page server never fell over: no Python error and no route that failed in its log", "Traceback" not in log and " failed: " not in log,
             [ln for ln in log.splitlines() if " failed: " in ln or "Traceback" in ln][:3])
        every = sorted(p.name for p in designs.iterdir() if p.name.endswith(".jpg")) + sorted(p.name for p in sdesigns.iterdir() if p.name.endswith(".jpg"))
        case("every picture kept is '<a design's id>.preview.jpg' beside that design (%d of them), each a whole JPEG under 1 MB" % len(every),
             bool(every) and all((designs / n.replace(".preview.jpg", ".json")).is_file() or (sdesigns / n.replace(".preview.jpg", ".json")).is_file() for n in every)
             and all(p.stat().st_size < 1024 * 1024 and p.read_bytes()[:2] == b"\xff\xd8" and p.read_bytes()[-2:] == b"\xff\xd9"
                     for d in (designs, sdesigns) for p in d.iterdir() if p.name.endswith(".jpg")), every)
    finally:
        srv.stop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9640)
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
    try:
        check_preview_browser(dc.case, work, a.port, dc.make_kit, dc.Server, dc.post, dc.get_json)
    except Exception as e:  # noqa: BLE001
        import traceback
        dc.case("the real-browser checks of the design preview ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    bad = [n for n, ok in dc.results if not ok]
    print()
    print(f"{len(dc.results)} cases, {len(dc.results) - len(bad)} passed, {len(bad)} failed.  Work folder: {work}")
    for n in bad:
        print("  FAILED: " + n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
