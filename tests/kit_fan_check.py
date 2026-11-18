#!/usr/bin/env python3
"""The post kit's photo fan (Nicole's v28, her section 6 "The post kit fan", screenshot 11): the first time a kit
opens, 9 of its photos pile up, fan out and fly in an arc into the Reels, Carousel and Stories cards, which pulse
coral. Once per kit; ?fan=1 plays it again.

    python3 tests/guard.py 3000 python3 tests/kit_fan_check.py --work /private/tmp/somewhere [--port 9570]

What it checks, on pretend kits it makes itself (tests/fake_kit.py; nothing of a client's, never the real ~/.studio):
  * the list the page is handed: 9 at most, the reel's photos first, each photo once, each an address of the
    pickers' own /kit-photo with a number (never a path or a file name); a kit of two photos gets two; a kit whose
    photos have no numbers yet, or can't be reached, gets none;
  * the script: her key (kitFan:<shoot>) read and written inside try/catch, the computer's reduce-motion setting
    asked, presses passing through, nothing from the internet, no long dash; her own page has the same key and
    the same numbers, when her handoff is on this computer;
  * in a HIDDEN Chrome:
      - the first open: 9 photos on a layer over the page that takes no presses (a folder button pressed in the
        middle of it answers at once), every flight ending in a card, all three cards pulsing coral, the layer
        gone when it ends, the key kept;
      - a second open: nothing plays; ?fan=1: it plays again;
      - the computer set to reduce motion: nothing plays and the key is not written;
      - storage blocked: it plays, and the page has no error;
      - a kit of two photos plays with two; a kit with none plays nothing;
      - a phone's width: it plays, with no sideways scroll;
      - nothing asked of the internet, no error on the page.

Nothing outside --work is touched. The page server and the hidden Chrome are this test's own and are stopped at the
end. Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402
import kit_cards_check as kcc  # noqa: E402  (its page fetch, its kit module and its in-page answers for folder buttons)

KIT = rpc.KIT
KQ = quote(KIT)
TWO, NONE = "Two photos", "Gone photos"

# every animation the page starts is written down, with what it was started on
WATCH = r"""
(() => {
  window.__anim = [];
  const real = Element.prototype.animate;
  Element.prototype.animate = function(frames, opts){
    window.__anim.push({tag: this.tagName, piece: this.dataset ? (this.dataset.piece || '') : '', inFan: !!(this.parentElement && this.parentElement.id === 'kitFan'),
                        frames: JSON.stringify(frames), at: performance.now()});
    return real.apply(this, arguments); };
})()
"""
BLOCKED = r"""
(() => { const no = function(){ throw new DOMException('blocked', 'SecurityError'); };
  Storage.prototype.getItem = no; Storage.prototype.setItem = no; })()
"""


def fan_of(text):
    m = re.search(r"<script type='application/json' id='kit-fan'>(.*?)</script>", text, re.S)
    return json.loads(m.group(1)) if m else None


def kit_url(s, name=KIT, more=""):
    return s.url("/content/%s/Post%%20kit.html%s" % (quote(name), more))


def start_kit(s, name, n):
    """A second pretend kit started from a folder of n of the first kit's photos. Returns (its folder, the folder
    its photos are in)."""
    src = s.work / ("photos for " + name)
    src.mkdir(exist_ok=True)
    for p in kcc.photos_of(s.kit)[:n]:
        shutil.copyfile(p, src / p.name)
    code, out = s.cmd("kit.py", "start", "--folder", str(src), "--name", name)
    m = re.search(r"^Kit: (.+)$", out, re.M)
    case("(a pretend kit of %d photos, started from a folder: %s)" % (n, name), code == 0 and m, out[-300:])
    return (Path(m.group(1)) if m else None), src


def her_page():
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v28-*"), reverse=True):
            f = h / "Carousel designer and reel picker" / "pages" / "post-kit.html"
            if f.is_file():
                return f.read_text(encoding="utf-8")
    return None


# ---------- 1. the list and the script ----------

def check_list(s):
    k = kcc.kit_module(s)
    code, text = kcc.page(s)
    fan = fan_of(text)
    case("the kit page carries the fan's list, 9 photos for a kit of %d" % rpc.PHOTOS, code == 200 and isinstance(fan, list) and len(fan) == 9, fan)
    fan = fan or []
    nums = [int(re.search(r"&n=(\d+)&", a).group(1)) for a in fan if re.search(r"&n=(\d+)&", a)]
    case("each is the pickers' own /kit-photo address with a photo's number, small size: never a path or a file name",
         len(nums) == len(fan) and all(a.startswith("/kit-photo?kit=%s&n=" % KQ) and "&size=s&v=" in a and ".jpg" not in a.lower() and "/Users" not in a and "/private" not in a for a in fan), fan)
    case("each photo once", len(set(nums)) == len(nums), nums)
    f = k.card_facts(s.kit)
    order = f["reel_order"][:9]
    case("the reel's photos come first, in the reel's order (then photos spread through the shoot)", nums[:len(order)] == order if order else nums == sorted(nums), [nums, order])
    case("the list is a list of addresses only, written so no photo name can end the script", "</script" not in json.dumps(fan) and all(isinstance(a, str) for a in fan))
    two, _ = start_kit(s, TWO, 2)
    if two:
        code, text = kcc.page(s, two.name)
        case("a kit whose photos have no numbers yet is handed none (its page is only ever read, so it numbers nothing itself)",
             code == 200 and fan_of(text) == [] and not (two / ".kit" / "sheet.json").exists(), fan_of(text))
        code, out = s.cmd("kit.py", "sheet", two.name)
        code, text = kcc.page(s, two.name)
        case("once its photos are numbered, a kit of two photos is handed two", code == 200 and len(fan_of(text) or []) == 2, [out[-200:], fan_of(text)])
    gone, src = start_kit(s, NONE, 1)
    if gone:
        s.cmd("kit.py", "sheet", gone.name)
        for p in src.iterdir():
            p.unlink()                                   # this test's own copies, in this run's folder
        code, text = kcc.page(s, gone.name)
        case("a kit whose photos can't be reached is handed none (and its page still builds)", code == 200 and fan_of(text) == [] and "class='piece'" in text, fan_of(text))
    saved = k.page_html(s.kit)
    case("kit.FAN_MOST is her 9", k.FAN_MOST == 9)
    sc = k.SCRIPT[k.SCRIPT.index("function kitFan"):]
    case("her key, kitFan:<shoot>", "'kitFan:' + KIT" in sc)
    case("the key is read and written inside try/catch (storage blocked never breaks the page)",
         re.search(r"try \{ seen = !!localStorage\.getItem\(key\); \} catch", sc) and re.search(r"try \{ localStorage\.setItem\(key, '1'\); \} catch", sc)
         and sc.count("localStorage") == 2)
    case("?fan=1 plays it again", "get('fan') === '1'" in sc)
    case("the computer's reduce-motion setting is asked before anything is drawn", 0 < sc.index("prefers-reduced-motion: reduce") < sc.index("createElement('div')"))
    case("the layer takes no presses and always takes itself away", "pointer-events:none" in sc and "setTimeout(away" in sc and "catch (e) { away(); }" in sc)
    case("a saved copy of the page (not served) plays nothing", "if (!live) return;" in sc)
    case("nothing from the internet, no long dash, never \"Claude\"", "https://" not in sc and "—" not in sc and "Claude" not in sc)
    case("the fan adds no words to the page", saved.count("kitFan") == k.SCRIPT.count("kitFan"))
    hers = her_page()
    if hers is None:
        print("SKIP  the fan against her own page: her handoff v28 is not on this computer", flush=True)
        return
    for frag in ("'kitFan:' + SHOOT", "pics.slice(0, 9)", "width:110px;height:138px", "duration: 420, delay: k * 35", "duration: 650, delay: k * 25",
                 "k * 80", "duration: 800", "duration: 900", "rgba(240,127,90,.9)", "pointer-events:none;z-index:50"):
        ours = frag.replace("'kitFan:' + SHOOT", "'kitFan:' + KIT").replace("pics.slice(0, 9)", "slice(0, 9)")
        case("hers has %r and so does ours" % frag, frag in hers and ours in sc)


# ---------- 2. the page in a hidden Chrome ----------

READY = "document.body.classList.contains('live') && document.querySelectorAll('a.piece').length === 3"


def motion(c, reduce):
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce" if reduce else "no-preference"}]})


def played(c, seconds=30):
    """Wait for the fan to start (its photos' small copies may still be being made). True when it did."""
    try:
        c.wait_for("!!document.getElementById('kitFan')", seconds)
        return True
    except chrome_drive.Timeout:
        return False


def quiet(c, seconds=3.0):
    """Nothing plays: no layer shows up in this long, and no animation was started."""
    end = time.time() + seconds
    while time.time() < end:
        if c.js("!!document.getElementById('kitFan')"):
            return False
        time.sleep(0.1)
    return c.js("window.__anim.length") == 0


def check_browser(c, s):
    c.init_script(kcc.PAGE_HOOKS)
    c.init_script(WATCH)
    motion(c, False)
    url = kit_url(s)
    c.open(url)
    c.wait_for(READY, 10)
    ok = played(c, 60)
    case("the first time the kit opens, the fan plays", ok)
    if not ok:
        return
    t0 = time.time()
    layer = c.js("(function(){ var l = document.getElementById('kitFan'), s = getComputedStyle(l); var im = l.querySelectorAll('img');"
                 " return {n: im.length, pe: s.pointerEvents, pos: s.position, hid: l.getAttribute('aria-hidden'), body: l.parentElement === document.body,"
                 "  imgpe: Array.from(im).every(function(i){ return getComputedStyle(i).pointerEvents === 'none' }),"
                 "  loaded: Array.from(im).every(function(i){ return i.naturalWidth > 0 }), w: im[0].offsetWidth, h: im[0].offsetHeight,"
                 "  srcs: Array.from(im).map(function(i){ return i.getAttribute('src') }) }; })()")
    case("9 of the kit's photos, each loaded, her size (110 by 138), on a layer over the page", layer["n"] == 9 and layer["loaded"] and [layer["w"], layer["h"]] == [110, 138]
         and layer["pos"] == "fixed" and layer["body"], layer)
    case("the layer and its photos take no presses, and a screen reader is not told about them", layer["pe"] == "none" and layer["imgpe"] and layer["hid"] == "true", layer)
    case("the photos are the pickers' small copies, by number", all(a.startswith("/kit-photo?kit=") for a in layer["srcs"]), layer["srcs"])
    # in the middle of it: whatever is under the pile is still the page, and a button answers at once
    time.sleep(0.9)
    under = c.js("(function(){ var l = document.getElementById('kitFan'); if (!l) return 'gone'; var out = []; l.querySelectorAll('img').forEach(function(i){"
                 " var r = i.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); out.push(e ? !!e.closest('#kitFan') : false) }); return out; })()")
    case("while it plays, what is under each photo is the page itself, never the fan", under != "gone" and not any(under), under)
    c.click("button.go[data-sub='Photos']", check=False)
    try:
        c.wait_for("document.getElementById('folderWent').textContent.indexOf('Opened') === 0", 2)
        pressed = True
    except chrome_drive.Timeout:
        pressed = False
    still = c.js("!!document.getElementById('kitFan')")
    case("a folder button pressed in the middle of the fan answers at once, while the fan is still playing", pressed and still, [pressed, still, time.time() - t0])
    try:
        c.wait_for("!document.getElementById('kitFan')", 8)
        gone = True
    except chrome_drive.Timeout:
        gone = False
    took = time.time() - t0
    case("the layer takes itself away when the fan ends (within about 4 s of starting)", gone and took < 6.5, took)
    time.sleep(1.0)
    anim = c.js("window.__anim")
    fl = [a for a in anim if a["inFan"]]
    case("each photo appears, fans out and flies: three moves each (27)", len(fl) == 27 and all(a["tag"] == "IMG" for a in fl), len(fl))
    last = [json.loads(a["frames"]) for a in fl[-9:]]
    case("every flight goes through the middle of an arc and ends small and faded out, in a card", all(len(f) == 3 and f[1].get("offset") == 0.5 and f[2]["opacity"] == 0
         and "scale(.28)" in f[2]["transform"] for f in last), last[:1])
    pulses = [a for a in anim if a["tag"] == "A" and "boxShadow" in a["frames"]]
    case("the Reels, Carousel and Stories cards each pulse coral as their photos land (3 photos each)",
         sorted(a["piece"] for a in pulses) == ["carousel"] * 3 + ["reel"] * 3 + ["stories"] * 3 and all("rgba(240,127,90" in a["frames"] for a in pulses),
         [a["piece"] for a in pulses])
    case("nothing else on the page was moved", len(anim) == 36, len(anim))
    case("her key is kept in this browser: kitFan:<the kit>", c.js("localStorage.getItem('kitFan:' + document.body.dataset.kit)") == "1")
    case("the cards are as they were: three links, each with its heading", c.js("Array.from(document.querySelectorAll('a.piece h2')).map(function(h){return h.firstChild.textContent})") == ["Reels", "Carousel", "Stories"])

    c.open(url)
    c.wait_for(READY, 10)
    case("a second open of the same kit: nothing plays", quiet(c))
    c.open(kit_url(s, more="?fan=1"))
    c.wait_for(READY, 10)
    case("?fan=1 plays it again", played(c, 15))
    c.wait_for("!document.getElementById('kitFan')", 8)

    # the computer set to reduce motion, on a browser that has never seen this kit
    c.js("localStorage.clear()")
    motion(c, True)
    try:
        c.open(url)
        c.wait_for(READY, 10)
        case("the computer set to reduce motion: nothing plays", quiet(c))
        case("... and the key is not written, so the fan is still theirs to see once", c.js("localStorage.getItem('kitFan:' + document.body.dataset.kit)") is None)
        c.open(kit_url(s, more="?fan=1"))
        c.wait_for(READY, 10)
        case("... not even with ?fan=1", quiet(c, 2.0))
    finally:
        motion(c, False)

    # storage blocked
    c.clear_errors()
    blocked = c.init_script(BLOCKED)
    try:
        c.open(url)
        c.wait_for(READY, 10)
        case("storage blocked: the fan simply plays", played(c, 15))
        c.wait_for("!document.getElementById('kitFan')", 8)
        case("... and the page has no error", not c.page_errors(), c.page_errors())
    finally:
        c.drop_init_script(blocked)

    # fewer than 9, and none
    names = {p.name[11:]: p.name for p in (s.target / "The Assistant" / "Your Content").iterdir()}
    if TWO in names:
        c.open(kit_url(s, names[TWO]))
        c.wait_for(READY, 10)
        ok = played(c, 60)
        n = c.js("(document.getElementById('kitFan') || {querySelectorAll: function(){ return [] }}).querySelectorAll('img').length") if ok else 0
        case("a kit of two photos plays with the two it has", ok and n == 2, n)
        if ok:
            c.wait_for("!document.getElementById('kitFan')", 8)
    if NONE in names:
        c.open(kit_url(s, names[NONE]))
        c.wait_for(READY, 10)
        case("a kit with no photo to show plays nothing, and its cards are there", quiet(c) and c.count("a.piece") == 3)
        case("... and its key is not written", c.js("localStorage.getItem('kitFan:' + document.body.dataset.kit)") is None)

    # a phone's width
    c.js("localStorage.clear()")
    c.phone(390, 844)
    try:
        c.open(url)
        c.wait_for(READY, 10)
        ok = played(c, 15)
        time.sleep(1.2)
        wide = c.js("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        case("at a phone's width it plays, with no sideways scroll", ok and wide[0] <= wide[1] == 390, wide)
        c.wait_for("!document.getElementById('kitFan')", 8)
    finally:
        c.desktop()
    outside = [r["url"] for r in list(c.requests) if not chrome_drive.is_this_computer(r["url"])]
    case("nothing was asked of the internet", not outside, outside[:3])
    case("no error on the page", not c.page_errors(), c.page_errors())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9570)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("run-%H%M%S")
    run.mkdir(parents=True)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the post kit's fan: the pretend kit is drawn with the Mac's sips", flush=True)
        return rpc.summary()
    s = rpc.Setup(run, a.port)
    s.make()
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 10)
        group("the fan's list and script", check_list, s)
        if not chrome_drive.find_chrome():
            print("SKIP  the fan in a browser: no Chrome on this computer", flush=True)
        else:
            with chrome_drive.Chrome(work=str(run), size=(1280, 1400)) as c:
                group("the fan in a browser", check_browser, c, s)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
