#!/usr/bin/env python3
"""The editing queue's animations (Nicole's v28, her section 6 "Delivered"): the cards deal in the first time the
page opens, and Mark as delivered flips the card to a green "Delivered." side, after the save.

    python3 tests/guard.py 3000 python3 tests/edit_queue_v28_check.py [--port 9260] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant in a throwaway folder (a scratch STUDIO_HOME; shoots that are only names and
three tiny made-up pictures; nothing of the real ~/.studio, no drive, no photo):
  * the words: her lines on the page (compared with her own changed file when her handoff is on this computer),
    34 confetti pieces, "your assistant" and never "Claude", no long dash, and the delivered side built with the
    shoot's name as text;
  * the page in a HIDDEN Chrome (when there is one):
      - the deal: each card rises in, staggered, its pictures fan in, once; a later redraw deals nothing; every
        card ends up fully shown;
      - a save that fails: today's problem line, no flip, no confetti, the record unchanged;
      - a real press: the save is answered BEFORE the first frame of the flip; the green side says "Delivered."
        and "<name>: gallery sent. Make posts from it whenever you're ready." with the name as text only (a name
        with <, & and a script), 3 pictures, 34 confetti pieces; the card is still there 1.5 s later and gone
        after about 2 s; the search box does not trip while a card shows its delivered side;
      - the computer set to reduce motion: no deal, no flip, no confetti; the save still happens and the card
        still leaves;
      - ?try=delivered: the flip plays on the first shoot, the page says "That was a preview. Nothing changed.",
        the shoot is back in the queue, the page sent no POST at all, and queue.json is byte for byte what it was.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import base64
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import edit_queue_v26_check as base  # noqa: E402  (its pretend Assistant, page server and helpers)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

NASTY = base.NASTY
# the smallest picture a browser will draw (1 x 1, grey)
JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/"
    "yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=")

HERS = [
    "Delivered.",
    "gallery sent. Make posts from it whenever you're ready.",
    "That was a preview. Nothing changed.",
    "${s.name}: delivered, moved to Delivered below",
]

# what the page does is written down as it happens: every animation started, every request sent
WATCH = r"""
(() => {
  window.__log = []; window.__failPosts = false;
  const cls = e => (e.tagName || '').toLowerCase() + (e.className ? '.' + String(e.className).trim().split(/\s+/).join('.') : '');
  const real = Element.prototype.animate;
  Element.prototype.animate = function(frames, opts){
    window.__log.push({what:'animate', on:cls(this), parent:this.parentElement ? cls(this.parentElement) : '', frames:JSON.stringify(frames), delay:(opts && opts.delay) || 0, at:performance.now()});
    return real.apply(this, arguments) };
  const f = window.fetch;
  window.fetch = async function(url, o){
    const m = ((o && o.method) || 'GET').toUpperCase();
    window.__log.push({what:'sent', method:m, url:String(url), body:(o && o.body) || '', at:performance.now()});
    if(m == 'POST' && window.__failPosts){ window.__log.push({what:'answered', method:m, ok:false, at:performance.now()}); return new Response('no', {status:500}) }
    const r = await f.apply(this, arguments);
    window.__log.push({what:'answered', method:m, ok:r.ok, at:performance.now()});
    return r };
  const xo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, url){ window.__log.push({what:'sent', method:String(m).toUpperCase(), url:String(url), at:performance.now()}); return xo.apply(this, arguments) };
  const sb = navigator.sendBeacon && navigator.sendBeacon.bind(navigator);
  if(sb) navigator.sendBeacon = function(url){ window.__log.push({what:'sent', method:'POST', url:String(url), at:performance.now()}); return sb.apply(null, arguments) };
})()
"""


def log(c, what=None):
    rows = c.js("window.__log")
    return [r for r in rows if what is None or r["what"] == what]


def motion(c, reduce):
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce" if reduce else "no-preference"}]})


def card(s, name):
    return "#list .card[data-id=%s]" % json.dumps(s.shoot(name)["id"])


def names_in_queue(c):
    return c.js("Array.from(document.querySelectorAll('#list .card .name')).map(e => e.textContent)")


def her_file():
    f = base.her_file()
    if not f:
        return None
    for g in sorted(f.parents[4].glob("nicole-handoff-v28-*/Carousel designer and reel picker/plugin-changes/changed/edit_queue.py")):
        return g
    return None


def check_words(s):
    sys.path.insert(0, str(SCRIPTS))
    import os
    os.environ["STUDIO_HOME"] = str(s.home)
    import edit_queue as eq
    for line in HERS:
        case("her line is on the page: %s" % line, line in eq.SCRIPT)
    hers = her_file()
    if hers:
        theirs = nicole_nov22.read(hers)   # Nicole, Nov 22: everything is the Assistant
        case("each of those lines is in her own changed file too", all(line in theirs for line in HERS), [line for line in HERS if line not in theirs])
        case("her confetti count is ours (34)", "k < 34" in theirs and "const CONFETTI = 34;" in eq.SCRIPT)
        case("her flip waits 2 s before the card leaves, as ours", "}, 2000);" in theirs and "leave(2000);" in eq.SCRIPT)
    else:
        base.skip("her own file is not on this computer (reference-private/ is never pushed)")
        case("34 confetti pieces", "const CONFETTI = 34;" in eq.SCRIPT)
        case("the card leaves 2 s after the flip", "leave(2000);" in eq.SCRIPT)
    face = eq.SCRIPT[eq.SCRIPT.index("function deliveredFace"):eq.SCRIPT.index("const CONFETTI")]
    case("the delivered side is built from text, never from markup", "innerHTML" not in face and "textContent" in face and "insertAdjacentHTML" not in eq.SCRIPT)
    fin = eq.SCRIPT[eq.SCRIPT.index("async function finish"):eq.SCRIPT.index("function deliveredFace")]
    case("in the code, the save comes before anything flips", 0 < fin.index("await send(") < fin.index("li.animate("))
    case("the preview never reaches send()", "send(" not in eq.SCRIPT[eq.SCRIPT.index("function tryDelivered"):eq.SCRIPT.index("// drag to reorder")])
    page = eq.page_html(eq.load())
    case("the page says \"the Assistant\", never \"Claude\"", "Claude" not in page and "the Assistant" in page)
    new = eq.SCRIPT[eq.SCRIPT.index("async function finish"):eq.SCRIPT.index("// drag to reorder")]
    case("no long dash in the new words", "—" not in new and "&mdash;" not in new)
    case("the motion asks the computer's reduce-motion setting", "prefers-reduced-motion: reduce" in eq.SCRIPT and "calm()" in fin)
    case("nothing on the page comes from the internet", "https://" not in eq.SCRIPT and "https://" not in eq.CSS)


def check_page(c, s):
    """Before: the queue = NASTY (Nov 18, three pictures), Garcia wedding (Nov 20), Lee family (Nov 25); Delivered = Patio session."""
    c.init_script(WATCH)
    motion(c, False)

    # ---- the deal
    c.open(s.url())
    c.wait_for("document.querySelectorAll('#list .card').length == 3", 10)
    deals = [r for r in log(c, "animate") if r["on"].startswith("li.card")]
    case("each card deals in once", len(deals) == 3, len(deals))
    case("rising from below and faded, into place", all('"opacity":0' in r["frames"] and "translateY(26px)" in r["frames"] for r in deals), [r["frames"] for r in deals][:1])
    case("one after the other (120, 210, 300 ms)", [r["delay"] for r in deals] == [120, 210, 300], [r["delay"] for r in deals])
    fans = [r for r in log(c, "animate") if r["on"] == "span" and r["parent"] == "div.pics"]
    case("the pictures of a card fan in, one after the other", len(fans) == 3 and [r["delay"] for r in fans] == [260, 320, 380] and all("rotate(" in r["frames"] for r in fans), [(r["on"], r["delay"]) for r in fans])
    c.wait_for("Array.from(document.querySelectorAll('#list .card, #list .pics span')).every(e => getComputedStyle(e).opacity === '1' && e.getAnimations().every(a => a.playState === 'finished'))", 6)
    case("every card ends fully shown", c.js("Array.from(document.querySelectorAll('#list .card, #list .pics span')).every(e => getComputedStyle(e).opacity === '1')"))
    case("a picture ends at its own tilt (the deal does not flatten the fan)", c.js("getComputedStyle(document.querySelector('#list .pics span')).transform !== 'none'"))
    c.js("window.__log = []; render()")
    case("a later redraw deals nothing", log(c, "animate") == [])
    case("the deal sent nothing", log(c, "sent") == [])

    # ---- a save that fails: today's problem line, no flip
    before = (s.home / "queue.json").read_bytes()
    c.js("window.__failPosts = true; window.__log = []")
    c.click(card(s, NASTY) + " .check")
    case("a failed save shows today's problem line", base.toast(c, "That did not save. Try again."))
    time.sleep(1.2)
    case("and nothing flips: no delivered side, no confetti, no animation", c.count("#list .flipped") == 0 and c.count(".confetti") == 0 and log(c, "animate") == [], log(c, "animate")[:2])
    case("the card is as it was (not greyed, still first)", c.js("!document.querySelector(%s).classList.contains('done')" % json.dumps(card(s, NASTY))) and names_in_queue(c)[0] == NASTY)
    case("the record is unchanged", (s.home / "queue.json").read_bytes() == before)
    c.js("window.__failPosts = false")

    # ---- a real press: the save, then the flip
    c.js("window.__log = []")
    sel = card(s, NASTY)
    c.click(sel + " .check")
    c.wait_for("!!document.querySelector('#list .card.flipped .dface')", 8)
    rows = log(c)
    answered = next((i for i, r in enumerate(rows) if r["what"] == "answered" and r["method"] == "POST" and r["ok"]), None)
    first_flip = next((i for i, r in enumerate(rows) if r["what"] == "animate" and "rotateX" in r["frames"]), None)
    case("the save was answered before the first frame of the flip", answered is not None and first_flip is not None and answered < first_flip, (answered, first_flip))
    case("the record already says delivered while the card is still flipping", s.shoot(NASTY)["status"] == "finished" and s.shoot(NASTY).get("finished_by") == "page")
    case("one save, the same press as before (action done)", [json.loads(r["body"]).get("action") for r in rows if r["what"] == "sent" and r["method"] == "POST"] == ["done"])
    case("the green side says Delivered.", c.text("#list .card.flipped .dface b") == "Delivered.")
    case("and her line, with the shoot's name", c.text("#list .card.flipped .dface .w") == NASTY + ": gallery sent. Make posts from it whenever you're ready.", c.text("#list .card.flipped .dface .w"))
    case("the name reached the card as text only", c.js("window.__got === undefined && !document.querySelector('#list img[src=x]') && document.querySelector('#list .card.flipped .dface .w').children.length === 0"))
    case("3 small pictures, the shoot's own", c.js("Array.from(document.querySelectorAll('#list .card.flipped .dp img')).map(i => new URL(i.src).pathname)") == ["/" + t for t in s.shoot(NASTY)["thumbs"]])
    case("the card's own buttons are gone from it", c.count("#list .card.flipped button") == 0)
    c.wait_for("document.querySelectorAll('.confetti').length > 0", 5)
    t0 = time.time()
    case("34 confetti pieces", c.count(".confetti") == 34 and len([r for r in log(c, "animate") if r["on"] == "i.confetti"]) == 34, c.count(".confetti"))
    case("confetti never takes a press and is hidden from screen readers", c.js("Array.from(document.querySelectorAll('.confetti')).every(e => getComputedStyle(e).pointerEvents === 'none' && e.getAttribute('aria-hidden') === 'true')"))
    c.clear_errors()
    base.search(c, "gar")
    case("the search works while a card shows its delivered side", c.page_errors() == [] and c.js("Array.from(document.querySelectorAll('#list .card')).filter(e => e.style.display !== 'none').length") == 1, c.page_errors())
    base.search(c, "")
    wait = 1.5 - (time.time() - t0)
    if wait > 0:
        time.sleep(wait)
    case("1.5 s on, the delivered side is still there", c.count("#list .card.flipped") == 1 and c.js("!document.querySelector('#list .card.flipped').classList.contains('leaving')"), time.time() - t0)
    c.wait_for("document.querySelectorAll('#list .card.flipped').length == 0", 6)
    gone = time.time() - t0
    case("it leaves after about 2 s (2.6 s with the fade)", 2.2 <= gone <= 4.0, round(gone, 2))
    case("the shoot is in Delivered below, the queue shows the other two", c.text("#dtitle") == "Delivered (2)" and names_in_queue(c) == ["Garcia wedding", "Lee family"], (c.text("#dtitle"), names_in_queue(c)))
    c.wait_for("document.querySelectorAll('.confetti').length == 0", 6)
    case("every confetti piece is taken away again", c.count(".confetti") == 0)
    case("nothing went wrong on the page", c.page_errors() == [], c.page_errors())

    # ---- the computer set to reduce motion
    motion(c, True)
    c.open(s.url())
    c.wait_for("document.querySelectorAll('#list .card').length == 2", 10)
    time.sleep(0.3)
    case("reduce motion: no deal", log(c, "animate") == [], log(c, "animate")[:1])
    c.click(card(s, "Garcia wedding") + " .check")
    case("reduce motion: the save still happens, with its line", base.toast(c, "Garcia wedding: delivered, moved to Delivered below") and s.shoot("Garcia wedding")["status"] == "finished")
    c.wait_for("document.querySelectorAll('#list .card').length == 1", 6)
    case("reduce motion: the card leaves with no flip and no confetti", log(c, "animate") == [] and c.count(".confetti") == 0 and names_in_queue(c) == ["Lee family"], log(c, "animate")[:1])
    motion(c, False)

    # ---- ?try=delivered: the flip, and nothing saved
    before = (s.home / "queue.json").read_bytes()
    c.open(s.url() + "?try=delivered")
    c.wait_for("document.querySelectorAll('#list .card').length == 1", 10)
    c.wait_for("!!document.querySelector('#list .card.flipped .dface')", 8)
    case("the preview flips the first shoot to its delivered side", c.text("#list .card.flipped .dface .w") == "Lee family: gallery sent. Make posts from it whenever you're ready.")
    c.wait_for("document.querySelectorAll('.confetti').length > 0", 5)
    case("with its 34 confetti pieces", c.count(".confetti") == 34)
    c.wait_for("document.querySelector('#count').textContent === 'All caught up'", 8)
    case("the page shows how it would look afterwards", c.text("#dtitle") == "Delivered (4)", c.text("#dtitle"))
    case("then says it was a preview", base.toast(c, "That was a preview. Nothing changed."))
    case("and shows what is really there: the shoot is back in the queue", names_in_queue(c) == ["Lee family"] and c.text("#dtitle") == "Delivered (3)", (names_in_queue(c), c.text("#dtitle")))
    sent = log(c, "sent")
    case("the preview sent no POST (it sent nothing at all)", [r for r in sent if r["method"] != "GET"] == [] and sent == [], sent)
    case("queue.json is byte for byte what it was", (s.home / "queue.json").read_bytes() == before)
    case("the shoot is still waiting in the record", s.shoot("Lee family")["status"] == "waiting" and "finished_at" not in s.shoot("Lee family"))
    c.wait_for("document.querySelectorAll('.confetti').length == 0", 6)
    # the real queue is dealt in again after the preview, so the card is still rising for half a second: the test's
    # press is aimed at where the button was measured, and on a slow Mac (GitHub's) the card had moved on by the time
    # the press landed. Wait until the deal is over, then press.
    c.wait_for("Array.from(document.querySelectorAll('#list .card')).every(e => getComputedStyle(e).opacity === '1' && e.getAnimations().every(a => a.playState === 'finished'))", 8)
    c.click(card(s, "Lee family") + " .setdue")
    case("after the preview the card works as ever (Change the date opens)", c.wait_for("!!document.querySelector('#list .card input[type=date]')", 5))
    case("nothing went wrong on the page", c.page_errors() == [], c.page_errors())

    motion(c, True)
    c.open(s.url() + "?try=delivered")
    c.wait_for("document.querySelectorAll('#list .card').length == 1", 10)
    case("reduce motion: the preview still ends with its line", base.toast(c, "That was a preview. Nothing changed.", 12))
    case("reduce motion: no animation in it, nothing sent, the record as it was", log(c, "animate") == [] and log(c, "sent") == [] and (s.home / "queue.json").read_bytes() == before, (log(c, "animate")[:1], log(c, "sent")))
    motion(c, False)


def prepare(s):
    for name, due in ((NASTY, "2026-11-18"), ("Garcia wedding", "2026-11-20"), ("Lee family", "2026-11-25"), ("Patio session", "2026-11-12")):
        code, out = s.run("add-manual", "--name", name, "--due", due)
        assert code == 0, out
    code, out = s.run("done", "Patio")
    assert code == 0, out
    q = s.queue()                               # three small pictures behind the first shoot, as a backed-up shoot has
    x = next(z for z in q["shoots"] if z["name"] == NASTY)
    folder = s.home / "queue-thumbs" / "practice-shoot"
    folder.mkdir(parents=True, exist_ok=True)
    x["thumbs"] = []
    for n in (1, 2, 3):
        (folder / ("%d.jpg" % n)).write_bytes(JPEG)
        x["thumbs"].append("queue-thumbs/practice-shoot/%d.jpg" % n)
    (s.home / "queue.json").write_text(json.dumps(q, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9260)
    ap.add_argument("--no-chrome", action="store_true", help="the words only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="edit-queue-v28-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = base.Setup(work, a.port)
    try:
        prepare(s)
        group("the words", check_words, s)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 20)
        case("the page answers with ?try=delivered on its address", s.http("GET", "/queue.html?try=delivered")[0] == 200)
        if a.no_chrome or not chrome_drive.find_chrome():
            base.skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page", check_page, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return base.summary()


if __name__ == "__main__":
    sys.exit(main())
