#!/usr/bin/env python3
"""The post kit as Nicole's three cards (v19 stage d): the kit page built on every request, checked on pretend kits.

    /usr/bin/python3 tests/kit_cards_check.py --work /private/tmp/somewhere [--port 9550]

What it checks, on pretend kits it makes itself (tests/fake_kit.py; nothing of a client's):
  * her words, word for word: every word in kit.KIT_WORDS against her own pages/post-kit.html (handoff v19), when
    her handoff is on this computer (it is never in the repository; without it that one part says SKIP);
  * the page as the server builds it on each request (/content/<kit>/Post kit.html) and as kit.py page saves it:
    her bar, date, lede and three cards, each a link to its page (the reel page, the designer, the stories
    designer); her "+N" after 7 reel photos and after 6 slides or stories; "1 slide saved" (not "1 slides"); the
    design counts; her dashed word boxes, filled from the kit's words with a Copy button each, and "Not written
    yet." only where a piece has no words; the quiet line under the cards (Singles, Covers, the kit folder);
  * the kit at each stage: nothing made yet, a reel made (from the chat, then a newer one from the reel page), a
    laid-out carousel, a one-slide set (a single post, also on the posting page's grid), saved stories, a Canva
    carousel fetched after the laid-out set, and an unplugged drive (her "I can't reach this shoot right now..."
    line, answered as not found);
  * in a HIDDEN Chrome: each card's words and where its link goes, a press on a card opening its page, Copy inside
    a card copying its words and NOT following the card's link, Open in CapCut saying her words and not following
    the link either, the folder buttons asking the Assistant (and never leaving the page), the reel photos loading,
    nothing asked of the internet, no sideways scroll at a phone's width, no error on the page.

Nothing outside --work is touched. No folder is ever opened (the page's folder requests are answered inside the
page) and CapCut is never started (reel_page's test switch). The page server and the hidden Chrome are this test's
own and are stopped at the end. Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402

KIT = rpc.KIT
KQ = quote(KIT)
EMPTY_NAME = "Quiet morning"
OPEN_WORDS = rpc.OPEN_WORDS
REACH = "I can't reach this shoot right now. Check that the photo drive is plugged in, then reload."
LEDE = ("Everything you need to post this shoot, in one place. Click the reel, the carousel or your stories to make them "
        "your way. Nothing gets posted for you.")

# every request a page makes to open a folder is answered inside the page (no folder is ever opened), and every copy
# the page makes is noted, so a test can say what was copied
PAGE_HOOKS = r"""
(function(){
  var real = window.fetch;
  function note(k, v){ try { var a = JSON.parse(sessionStorage.getItem(k) || '[]'); a.push(v); sessionStorage.setItem(k, JSON.stringify(a)); } catch (e) {} }
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) {
      note('__opens', String(u));
      return Promise.resolve(new Response(JSON.stringify({ok: true, words: 'Opened the folder in Finder.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    return real.apply(this, arguments);
  };
  var ex = document.execCommand.bind(document);
  document.execCommand = function(c){
    if (c === 'copy') { var el = document.activeElement; note('__copied', el && el.value !== undefined ? el.value : String(getSelection())); return true; }
    return ex.apply(document, arguments);
  };
})();
"""


def her_text():
    f = rpc.her_folder()
    if not f or not (f / "pages" / "post-kit.html").is_file():
        return None
    return html.unescape((f / "pages" / "post-kit.html").read_text(encoding="utf-8")).replace("\\'", "'")


def kit_module(s):
    os.environ["STUDIO_HOME"] = str(s.studio)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    import kit as kit_mod
    return importlib.reload(kit_mod)


# ---------- 1. her words ----------

def check_words(s):
    k = kit_module(s)
    t = her_text()
    case("kit page words: the line under the heading is hers", k.KIT_WORDS["lede"] == LEDE)
    case("kit page words: her unreachable line is the same as the reel page's", k.KIT_WORDS["reach"] == REACH)
    if t is None:
        print("SKIP  her words against her own page: her handoff v19 is not on this computer", flush=True)
        return
    missing = [key for key, v in k.KIT_WORDS.items() if v not in t]
    case("every word in kit.KIT_WORDS is in her pages/post-kit.html, word for word", not missing, missing)
    for frag in ("slides saved in the Carousel folder", "saved design", "no slides saved yet", "saved in the Stories folder", "'story' : 'stories'",
                 "no stories saved yet", "Make a new version", "Create my reel", "+${order.length - 7}", "slice(0, 7)", "slice(0, 6)"):
        case("her page has %r (our status lines and strips follow it)" % frag, frag in t)
    case("our status lines say her words", k.carousel_status(7, 2) == "7 slides saved in the Carousel folder · 2 saved designs"
         and k.stories_status(3, 1) == "3 stories saved in the Stories folder · 1 saved design"
         and k.carousel_status(0, 1) == "1 saved design, no slides saved yet" and k.stories_status(0, 0) == "Not made yet",
         (k.carousel_status(7, 2), k.stories_status(3, 1), k.carousel_status(0, 1)))
    case("...and '1 slide saved', not her '1 slides'", k.carousel_status(1, 1) == "1 slide saved in the Carousel folder · 1 saved design"
         and k.stories_status(1, 0) == "1 story saved in the Stories folder", k.carousel_status(1, 1))


# ---------- the pretend kits ----------

def page(s, name=KIT):
    code, _, raw = s.http("GET", "/content/%s/Post%%20kit.html" % quote(name))
    return code, raw.decode("utf-8", "replace")


def card(text, piece):
    m = re.search(r"<a class='piece' data-piece='%s' href='([^']*)'>(.*?)</a><(?:a class='piece'|/div><div class='also')" % piece, text, re.S)
    return (html.unescape(m.group(1)), m.group(2)) if m else ("", "")


def plain(fragment):
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def strip_srcs(fragment):
    return [html.unescape(x) for x in re.findall(r"<img src='([^']*)'", fragment)]


def status_of(fragment):
    m = re.search(r"<div class='status'>(.*?)</div>", fragment, re.S)
    return re.sub(r"\s+", " ", plain(m.group(1))).strip() if m else ""


def boxes(fragment):
    """(label, text, has Copy) for every word box in a card."""
    out = []
    for m in re.finditer(r"<div class='w(?: hook)?'><div class='k'>(.*?)</div><p class='(t|empty)'>(.*?)</p>(<button class='copy'[^>]*>Copy</button>)?</div>", fragment, re.S):
        out.append((html.unescape(m.group(1)), html.unescape(m.group(3)), bool(m.group(4))))
    return out


def write_rec(kit, change):
    """This check's own pretend kit record (as a design save or a Canva fetch would leave it)."""
    f = kit / ".kit" / "kit.json"
    rec = json.loads(f.read_text(encoding="utf-8"))
    change(rec)
    f.write_text(json.dumps(rec, indent=1), encoding="utf-8")


class _Cycle(list):
    def __getitem__(self, i):
        return list.__getitem__(self, i if isinstance(i, slice) else i % len(self))


def photos_of(kit):
    return _Cycle(sorted(p for p in (kit / "Photos").iterdir() if p.suffix.lower() == ".jpg" and not p.name.startswith(".")))


def check_empty_kit(s):
    """A kit with nothing made: started from a folder of photos, no picks, no words, no folders."""
    src = s.work / "a folder of finished photos"
    src.mkdir(exist_ok=True)
    for p in photos_of(s.kit)[:5]:
        shutil.copyfile(p, src / p.name)
    code, out = s.cmd("kit.py", "start", "--folder", str(src), "--name", EMPTY_NAME)
    m = re.search(r"^Kit: (.+)$", out, re.M)
    case("(a second pretend kit, started from a folder: nothing picked, nothing made)", code == 0 and m, out[-300:])
    if not m:
        return None
    k = Path(m.group(1))
    code, text = page(s, k.name)
    case("nothing made: the page is served (200), built now (no saved copy was written)", code == 200 and not (k / ".kit" / "Post kit.html").exists(), code)
    r_href, r = card(text, "reel")
    c_href, c = card(text, "carousel")
    t_href, t = card(text, "stories")
    case("nothing made: three cards, Reel, Carousel and Stories, in her order", all((r, c, t)) and text.index("data-piece='reel'") < text.index("data-piece='carousel'") < text.index("data-piece='stories'"))
    case("nothing made: the Reel card says her 'Your assistant hasn't picked the reel photos yet. Click to pick them yourself.' and 'Not made yet'",
         "Your assistant hasn't picked the reel photos yet. Click to pick them yourself." in plain(r) and status_of(r) == "Not made yet", status_of(r))
    case("nothing made: the CTAs are hers: Create my reel →, Design my carousel →, Make my stories →",
         "Create my reel →" in plain(r) and "Design my carousel →" in plain(c) and "Make my stories →" in plain(t))
    case("nothing made: 'No slides yet.' and 'No stories yet.', each 'Not made yet'",
         "No slides yet." in plain(c) and "No stories yet." in plain(t) and status_of(c) == "Not made yet" and status_of(t) == "Not made yet")
    case("nothing made: every word box says 'Not written yet.' (Hooks; Caption and Hashtags; Story lines) and has no Copy",
         boxes(r) == [("Hooks", "Not written yet.", False)] and boxes(c) == [("Caption", "Not written yet.", False), ("Hashtags", "Not written yet.", False)]
         and boxes(t) == [("Story lines", "Not written yet.", False)], (boxes(r), boxes(c), boxes(t)))
    case("nothing made: no Open in CapCut on a kit with no reel", "id='capcut'" not in text)
    also = text[text.index("<div class='also'>"):]
    case("nothing made: the quiet line has only 'Open the kit folder' (no Singles, no Covers folder yet)",
         re.findall(r"data-sub='([^']*)'", also) == [""] and "Open the kit folder" in also, re.findall(r"data-sub='([^']*)'", also))
    return k


def check_page_fresh(s):
    """The fake kit (12 reel picks), step by step through what a photographer makes."""
    k = s.kit
    code, text = page(s)
    case("the page is answered (200), as HTML, UTF-8", code == 200 and text.startswith("<!doctype html>"), code)
    case("nothing from the internet in the page: no Google Fonts link, no http(s) address, the plugin's own fonts", "googleapis" not in text and not re.search(r"https?://", text)
         and "url('/reel-font?f=DMSans-Regular')" in text and "url('/reel-font?f=Fraunces-Italic')" in text)
    case("no path in the page", not re.search(r"/private/|/Users/|\.kit/|kit\.json", text), re.findall(r".{20}(?:/private/|/Users/|\.kit/).{20}", text)[:2])
    case("her bar: Back to home, the product's name, the date in words", "Back to home" in text and "<span class='when'>November 1, 2026</span>" in text)
    case("her heading: the eyebrow 'Post kit', the shoot's name with her coral full stop, her lede",
         "<span class='eyebrow'>Post kit</span><h1>Fake beach<em>.</em></h1>" in text and html.escape(LEDE) in text)
    r_href, r = card(text, "reel")
    case("the Reel card is a link to the reel page (kit.REEL_DOOR)", r_href == "/reel.html?kit=" + KQ, r_href)
    srcs = strip_srcs(r)
    case("the Reel card: the first 7 of the 12 photos, in the assistant's order, then her '+5'",
         [int(re.search(r"&n=(\d+)", x).group(1)) for x in srcs] == rpc.CLAUDE[:7] and "<span class='more'>+5</span>" in r, srcs[:3])
    case("...each named only by the kit and its number (/kit-photo)", all(x.startswith("/kit-photo?kit=%s&n=" % KQ) and "&size=s" in x for x in srcs))
    case("the Reel card: 'Not made yet', her CTA 'Create my reel →', her line under the heading",
         status_of(r) == "Not made yet" and "Create my reel →" in plain(r)
         and "Put your photos in order, pick your song and the vibe, and it's cut on the beat in CapCut." in plain(r))
    c_href, c = card(text, "carousel")
    t_href, t = card(text, "stories")
    case("the Carousel card goes to the designer, the Stories card to the stories designer",
         c_href == "/design.html?kit=" + KQ and t_href == "/design.html?kit=%s&kind=stories" % KQ, (c_href, t_href))
    case("her Carousel line ends 'One slide on its own makes a single post.'", "One slide on its own makes a single post." in plain(c))

    # the chat's reel
    code, out = s.cmd("kit.py", "reel-made", KIT, "--project", "Fake beach reel")
    code, text = page(s)
    _, r = card(text, "reel")
    case("a reel made: 'In CapCut: Fake beach reel' with her Open in CapCut, and her 'Make a new version →'",
         status_of(r) == "In CapCut: Fake beach reel Open in CapCut" and "<button class='go' id='capcut' type='button'>Open in CapCut</button>" in r
         and "Make a new version →" in plain(r), status_of(r))
    # a newer one from the reel page (this check's own record, as the page's Make my reel leaves it)
    rec_file = k / ".kit" / "reel-page.json"
    rp = json.loads(rec_file.read_text(encoding="utf-8")) if rec_file.exists() else {"v": 1}
    rp.setdefault("made", []).append({"project": "Fake beach reel 2", "picks": "1,4", "vibe": "beat", "when": time.time() + 60})
    rec_file.write_text(json.dumps(rp), encoding="utf-8")
    code, text = page(s)
    _, r = card(text, "reel")
    case("the newest reel is the one shown: one from the reel page made after the chat's", "In CapCut: Fake beach reel 2" in status_of(r), status_of(r))
    # their own order on the reel page shows on the card (her saved.picks before Claude's)
    rp["saved"] = {"picks": [{"n": 5, "h": ""}, {"n": 2, "h": "+"}], "mine": True}
    rp.pop("stamp", None)
    rec_file.write_text(json.dumps(rp), encoding="utf-8")
    code, text = page(s)
    _, r = card(text, "reel")
    case("their own order from the reel page is the one the card shows", [int(re.search(r"&n=(\d+)", x).group(1)) for x in strip_srcs(r)] == [5, 2] and "class='more'" not in r, strip_srcs(r))
    rp.pop("saved")
    rec_file.write_text(json.dumps(rp), encoding="utf-8")
    case("showing the kit page wrote nothing to the reel page's record", json.loads(rec_file.read_text(encoding="utf-8")) == rp)

    # the words
    words = s.work / "words.json"
    words.write_text(json.dumps({"hooks": ["Wind in every frame", "Three of us & a kite"], "caption": "A windy morning at the beach.\n\nMore soon.",
                                 "short": "Windy.", "stories": ["Sneak peek →"], "leaned_on": "what you said when the kit was made"}), encoding="utf-8")
    code, out = s.cmd("kit.py", "words", KIT, "--file", str(words))
    code2, text = page(s)
    _, r = card(text, "reel")
    _, c = card(text, "carousel")
    _, t = card(text, "stories")
    case("words written: the Reel card's hooks, one dashed box each, with Copy", boxes(r) == [("Hook 1", "Wind in every frame", True), ("Hook 2", "Three of us & a kite", True)], boxes(r))
    case("words written: the Carousel card's caption and short caption with Copy, and 'Not written yet.' only for the missing hashtags",
         boxes(c) == [("Caption", "A windy morning at the beach.\n\nMore soon.", True), ("Short caption", "Windy.", True), ("Hashtags", "Not written yet.", False)], boxes(c))
    case("words written: the Stories card's story line with Copy", boxes(t) == [("Story line 1", "Sneak peek →", True)], boxes(t))
    case("words written: 'Written from' under the cards", "Written from: what you said when the kit was made" in plain(text[text.index("<div class='also'>"):]))
    case("the saved copy kit.py wrote (kit.py words writes it) is the same page as the one served",
         (k / ".kit" / "Post kit.html").read_text(encoding="utf-8") == text, code)

    # a laid-out carousel (this check's own record, as a Save slides in the designer leaves it)
    car = k / "Carousel"
    car.mkdir(exist_ok=True)
    ph = photos_of(k)
    names = ["Fake beach carousel 1 - slide %02d.jpg" % i for i in range(1, 9)]
    for i, n in enumerate(names):
        shutil.copyfile(ph[i], car / n)
    for i in range(1, 4):
        shutil.copyfile(ph[10 + i], car / ("Slide %02d.jpg" % i))           # three plain slides beside the set
    dd = k / ".kit" / "designs"
    dd.mkdir(exist_ok=True)
    for did in ("dtestdesign1", "dtestdesign2"):
        (dd / (did + ".json")).write_text(json.dumps({"id": did, "name": "x", "t": 1}), encoding="utf-8")
    write_rec(k, lambda rec: rec.update(carousel_set={"kind": "laid-out", "base": "Fake beach carousel 1", "files": names, "saved": "2026-11-07T10:00:00"},
                                        laid_out=[{"base": "Fake beach carousel 1", "files": names, "saved": "2026-11-07T10:00:00"}]))
    code, text = page(s)
    _, c = card(text, "carousel")
    srcs = strip_srcs(c)
    case("a laid-out carousel: the first 6 of its 8 slides, in order, then her '+2'",
         srcs == ["Carousel/" + n for n in names[:6]] and "<span class='more'>+2</span>" in c, srcs[:2])
    case("...'8 slides saved in the Carousel folder · 2 saved designs', and 'Open my carousel →'",
         status_of(c) == "8 slides saved in the Carousel folder · 2 saved designs" and "Open my carousel →" in plain(c), status_of(c))
    code, h, data = s.http("GET", "/content/%s/%s" % (KQ, quote(srcs[0])))
    case("...and its pictures load from the kit page's own address", code == 200 and data[:2] == b"\xff\xd8", code)

    # one slide: a single post
    one = ["Fake beach carousel 1 (2) - slide 01.jpg"]
    shutil.copyfile(ph[9], car / one[0])
    write_rec(k, lambda rec: rec.update(carousel_set={"kind": "laid-out", "base": "Fake beach carousel 1 (2)", "files": one, "saved": "2026-11-07T11:00:00"},
                                        laid_out=rec["laid_out"] + [{"base": "Fake beach carousel 1 (2)", "files": one, "saved": "2026-11-07T11:00:00"}]))
    code, text = page(s)
    _, c = card(text, "carousel")
    case("a one-slide set: '1 slide saved in the Carousel folder' (not her '1 slides')", status_of(c) == "1 slide saved in the Carousel folder · 2 saved designs"
         and strip_srcs(c) == ["Carousel/" + one[0]] and "class='more'" not in c, status_of(c))
    code, out = s.cmd("posting_queue.py", "add", "--kit", str(k))
    pq = json.loads((s.studio / "posting.json").read_text(encoding="utf-8"))
    single = [x for x in pq["pieces"] if x.get("id", "").endswith("-carousel")]
    case("...the posting queue counts it as a single post", code == 0 and single and single[0]["kind"] == "single", (out[-200:], single[:1]))
    if single:
        code, out = s.cmd("posting_queue.py", "ready", single[0]["id"])
        case("(the single post is marked ready to post, so it has a tile on the grid)", code == 0, out[-200:])

    # saved stories (this check's own record, as Save stories leaves it), beside two plain stories
    sto = k / "Stories"
    sto.mkdir(exist_ok=True)
    snames = ["Fake beach stories - %02d.jpg" % i for i in range(1, 4)]
    for i in (1, 2):
        shutil.copyfile(ph[30 + i], sto / ("Story %02d.jpg" % i))
    sdd = k / ".kit" / "story-designs"
    sdd.mkdir(exist_ok=True)
    (sdd / "dtestst0ry1.json").write_text(json.dumps({"id": "dtestst0ry1", "name": "x", "t": 1}), encoding="utf-8")
    code, text = page(s)
    _, t = card(text, "stories")
    case("plain stories only: '2 stories saved in the Stories folder · 1 saved design' and 'Open my stories →'",
         status_of(t) == "2 stories saved in the Stories folder · 1 saved design" and "Open my stories →" in plain(t), status_of(t))
    for i, n in enumerate(snames):
        shutil.copyfile(ph[20 + i], sto / n)
    write_rec(k, lambda rec: rec.update(stories_set={"kind": "laid-out", "base": "Fake beach stories", "files": snames, "saved": "2026-11-07T12:00:00"},
                                        stories_laid_out=[{"base": "Fake beach stories", "files": snames, "saved": "2026-11-07T12:00:00"}]))
    code, text = page(s)
    _, t = card(text, "stories")
    case("saved stories: the set from the stories designer, in order, and '3 stories saved in the Stories folder · 1 saved design'",
         strip_srcs(t) == ["Stories/" + n for n in snames] and status_of(t) == "3 stories saved in the Stories folder · 1 saved design", (strip_srcs(t), status_of(t)))

    # a Canva carousel fetched after the laid-out set
    canva = ["Slide %02d (Canva).jpg" % i for i in (1, 2)]
    for i, n in enumerate(canva):
        shutil.copyfile(ph[35 + i], car / n)
    write_rec(k, lambda rec: rec.update(canva={"fetched": {"Carousel": "2026-11-07T13:00:00"},
                                               "carousel": {"edit_url": "https://www.canva.com/design/TEST/edit", "made": "2026-11-07T13:00:00"}}))
    code, text = page(s)
    _, c = card(text, "carousel")
    srcs = strip_srcs(c)
    case("a Canva carousel fetched after the laid-out set: the Canva slides first, then the plain ones; no laid-out slide",
         srcs[:2] == ["Carousel/" + n for n in canva] and all(x.split("/", 1)[1] not in names + one for x in srcs) and len(srcs) == 5, srcs)
    case("...'5 slides saved in the Carousel folder · 2 saved designs'", status_of(c) == "5 slides saved in the Carousel folder · 2 saved designs", status_of(c))
    also = text[text.index("<div class='also'>"):]
    case("...and its Canva link on the quiet line, opening in a new tab", "In Canva:" in plain(also) and "href='https://www.canva.com/design/TEST/edit' target='_blank' rel='noopener'>the carousel</a>" in also)

    # Singles and Covers on the quiet line, each with its folder's button
    for sub in ("Singles", "Covers"):
        (k / sub).mkdir(exist_ok=True)
    shutil.copyfile(ph[40], k / "Singles" / "Single 01.jpg")
    shutil.copyfile(ph[41], k / "Singles" / "Single 02.jpg")
    shutil.copyfile(ph[42], k / "Covers" / "Reel cover.jpg")
    code, text = page(s)
    also = text[text.index("<div class='also'>"):]
    case("the quiet line under the cards: '2 single photos sized for Instagram' with Open the Singles folder, 'The reel cover' with Open the Covers folder, and Open the kit folder",
         re.findall(r"data-sub='([^']*)'", also) == ["Singles", "Covers", ""] and "2 single photos sized for Instagram" in plain(also)
         and "The reel cover" in plain(also) and "Open the kit folder" in plain(also), re.findall(r"data-sub='([^']*)'", also))
    case("no Singles or Covers card of their own (decision 12)", "<h2>Single posts" not in text and text.count("class='piece'") == 3)


def check_unplugged(s):
    content = s.target / "The Assistant"
    away = s.target / "The Assistant (unplugged for this check)"
    content.rename(away)                       # this check's own pretend drive, put back below
    try:
        code, text = page(s)
        case("the drive unplugged: her line 'I can't reach this shoot right now. Check that the photo drive is plugged in, then reload.'",
             "<div class='problem'>%s</div>" % html.escape(REACH) in text and code == 404, code)
        case("...under her heading 'Post kit.' and her lede, with no card", "<h1>Post kit<em>.</em></h1>" in text and "class='piece'" not in text)
        code, text = page(s, "No such kit")
        case("a kit that isn't there: the same line, not found", code == 404 and REACH in html.unescape(text), code)
    finally:
        away.rename(content)
    code, text = page(s)
    case("plugged in again: the cards are back", code == 200 and text.count("class='piece'") == 3, code)
    for label, path in (("a look-alike beside Your Content", "/content/%2e%2e/Your%20Content%20old/Sneaky/Post%20kit.html"),
                        ("the hidden folder", "/content/%s/.kit/Post%%20kit.html" % KQ)):
        code, _, raw = s.http("GET", path)
        case("still refused: %s" % label, code == 404 and b"class='piece'" not in raw, code)


# ---------- the page in a hidden Chrome ----------

def check_browser(c, s):
    c.init_script(PAGE_HOOKS)
    url = s.url("/content/%s/Post%%20kit.html" % KQ)
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && document.querySelectorAll('a.piece').length === 3", 10)
    cards = c.js("Array.from(document.querySelectorAll('a.piece')).map(function(a){return [a.dataset.piece, a.querySelector('h2').firstChild.textContent, a.querySelector('.cta').textContent, a.getAttribute('href')]})")
    case("in a browser: the three cards, her headings and CTAs, each a link to its page", cards == [
        ["reel", "Reel", "Make a new version →", "/reel.html?kit=" + KQ],
        ["carousel", "Carousel", "Open my carousel →", "/design.html?kit=" + KQ],
        ["stories", "Stories", "Open my stories →", "/design.html?kit=%s&kind=stories" % KQ]], cards)
    case("in a browser: her lede, word for word", c.text(".lede") == LEDE)
    try:
        c.wait_for("Array.from(document.querySelectorAll('[data-piece=reel] .strip img')).every(function(i){return i.complete && i.naturalWidth > 0})", 60)
        loaded = True
    except chrome_drive.Timeout:
        loaded = False
    case("in a browser: the reel photos load (their small copies made in the background when missing)", loaded and c.count("[data-piece=reel] .strip img") == 7,
         c.js("Array.from(document.querySelectorAll('[data-piece=reel] .strip img')).map(function(i){return i.naturalWidth})"))
    case("in a browser: the carousel and stories pictures load", c.js("Array.from(document.querySelectorAll('[data-piece=carousel] .strip img, [data-piece=stories] .strip img')).every(function(i){return i.complete && i.naturalWidth > 0})") is True)
    case("in a browser: the page's fonts are the plugin's own and they loaded", c.js("document.fonts.check(\"600 16px 'DM Sans'\") && document.fonts.check(\"italic 400 16px 'Fraunces'\")") is True)

    # Copy inside a card: copies, and does not follow the card's link
    c.click("[data-piece=reel] .w .copy")
    time.sleep(0.4)
    case("Copy inside the Reel card copies the hook", json.loads(c.js("sessionStorage.getItem('__copied') || '[]'")) == ["Wind in every frame"], c.js("sessionStorage.getItem('__copied')"))
    case("...says 'Copied' on the button", c.text("[data-piece=reel] .w .copy") == "Copied")
    case("...and the card's link was NOT followed (still on the kit page)", c.js("location.pathname") == "/content/%s/Post%%20kit.html" % KQ, c.js("location.href"))
    c.click("[data-piece=carousel] .w .copy")
    time.sleep(0.4)
    case("Copy inside the Carousel card copies the caption, and stays on the page",
         json.loads(c.js("sessionStorage.getItem('__copied') || '[]'"))[-1:] == ["A windy morning at the beach.\n\nMore soon."] and c.js("location.pathname").startswith("/content/"))
    c.click("[data-piece=stories] .w .t")
    time.sleep(0.3)
    case("a click on the words themselves (to select them) doesn't open the card's page either", c.js("location.pathname").startswith("/content/"))

    # Open in CapCut: her words on the line under it, and the link not followed
    c.click("#capcut")
    try:
        c.wait_for("document.querySelector('[data-piece=reel] .went').textContent === %s" % json.dumps(OPEN_WORDS), 10)
        said = True
    except chrome_drive.Timeout:
        said = False
    case("Open in CapCut says her 'CapCut is opening. Your newest reel is at the top of your projects.' under it", said, c.text("[data-piece=reel] .went"))
    case("...and the card's link was NOT followed", c.js("location.pathname").startswith("/content/"))

    # the quiet line's folder buttons: asked of the Assistant, the result under them, never the card's link
    c.click("button.go[data-sub='Singles']")
    c.wait_for("JSON.parse(sessionStorage.getItem('__opens') || '[]').length === 1 && document.querySelector('.also .went').textContent !== 'Opening...'", 5)
    case("Open the Singles folder asks the Assistant for exactly that folder, and says the answer under the line",
         json.loads(c.js("sessionStorage.getItem('__opens')")) == ["/open?kit=%s&sub=Singles" % KQ] and c.text(".also .went") == "Opened the folder in Finder.")

    # a press on a card opens its page
    c.click("[data-piece=stories] .sub")
    try:
        c.wait_for("location.pathname === '/design.html'", 15)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("a press on the Stories card opens the stories designer for this shoot", went and c.js("location.search") == "?kit=%s&kind=stories" % KQ, c.js("location.href"))
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    c.click("[data-piece=reel] h2")
    try:
        c.wait_for("location.pathname === '/reel.html' && !!document.querySelector('h1')", 15)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("a press on the Reel card opens the reel page", went, c.js("location.href"))
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    outside = [u for u in c.outside_requests() if not u.startswith(("data:", "blob:", "about:", "chrome"))]
    case("nothing was asked of the internet by the kit page", not outside, outside[:3])
    case("no error on the page", c.page_errors() == [], c.page_errors()[:3])

    # the posting page's grid names the single post
    c.open(s.url("/posting.html"))
    try:
        c.wait_for("!!document.querySelector('#grid .tile.mine .k')", 10)
        label = c.js("Array.from(document.querySelectorAll('#grid .tile.mine .k')).map(function(k){return k.textContent})")
    except chrome_drive.Timeout:
        label = None
    case("the posting page's grid labels the one-slide set 'Single post' (it said Carousel)", label and any("Single post" in x for x in label) and not any("Carousel" in x for x in label), label)

    # at a phone's width
    c.phone(390, 844)
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    case("at a phone's width: one column, no sideways scroll", c.js("document.documentElement.scrollWidth <= window.innerWidth") is True
         and c.rect("[data-piece=reel] .words")["y"] > c.rect("[data-piece=reel] .status")["y"])
    c.desktop()


def check_unplugged_browser(c, s):
    content = s.target / "The Assistant"
    away = s.target / "The Assistant (unplugged for this check)"
    content.rename(away)
    try:
        c.open(s.url("/content/%s/Post%%20kit.html" % KQ))
        c.wait_for("!!document.querySelector('.problem')", 10)
        case("in a browser, the drive unplugged: her line shows, and nothing else", c.text(".problem") == REACH and c.count("a.piece") == 0)
    finally:
        away.rename(content)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9550)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("run-%H%M%S")
    run.mkdir(parents=True)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the kit page: the pretend kit is drawn with the Mac's sips", flush=True)
        return rpc.summary()
    s = rpc.Setup(run, a.port)
    s.make()
    group("her words", check_words, s)
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 10)
        group("a kit with nothing made", check_empty_kit, s)
        group("the kit, step by step", check_page_fresh, s)
        group("an unplugged drive", check_unplugged, s)
        if not chrome_drive.find_chrome():
            print("SKIP  the kit page in a browser: no Chrome on this computer", flush=True)
        else:
            with chrome_drive.Chrome(work=str(run), size=(1280, 1400)) as c:
                group("the kit page in a browser", check_browser, c, s)
                group("an unplugged drive, in a browser", check_unplugged_browser, c, s)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
