#!/usr/bin/env python3
"""The post kit as Nicole's three cards (v19 stage d): the kit page built on every request, checked on pretend kits.
(The three steps on the Reel and Carousel cards, v20, have their own check: tests/kit_steps_check.py.)

    /usr/bin/python3 tests/kit_cards_check.py --work /private/tmp/somewhere [--port 9550]

What it checks, on pretend kits it makes itself (tests/fake_kit.py; nothing of a client's):
  * her words, word for word: every word in kit.KIT_WORDS against her own pages/post-kit.html (handoff v20), when
    her handoff is on this computer (it is never in the repository; without it that one part says SKIP);
  * the page as the server builds it on each request (/content/<kit>/Post kit.html) and as kit.py page saves it:
    her bar, date, lede and three cards, each a link to its page (the reel page, the designer, the stories
    designer); her "+N" after 7 reel photos and after 6 slides or stories; "1 slide saved" (not "1 slides"); the
    design counts; the Reel and Carousel cards' steps there and the Stories card without them; her folder buttons
    at the top; the quiet line under the cards (Singles, Covers, Canva's links);
  * the kit at each stage: nothing made yet, a reel made (from the chat, then a newer one from the reel page), a
    laid-out carousel, a one-slide set (a single post, also on the posting page's grid), saved stories, a Canva
    carousel fetched after the laid-out set, and an unplugged drive (her "I can't reach this shoot right now..."
    line, answered as not found);
  * the design preview (her v24): her two lines and her style line, the same in her page and ours; the picture of
    the design they're working on shown on the Carousel card while no slides are saved (the assistant's own first
    design once the designer has opened it and sent its picture, never a blank design, the design changed last
    even when an older design has the newer picture, a design's name as text), the same on the Stories card,
    the piece still not "made" and its queue step locked, saved slides winning, and an unplugged drive;
  * in a HIDDEN Chrome: each card's words and where its link goes, a press on a card opening its page, Open in
    CapCut saying her words and not following the card's link, the folder buttons asking the Assistant (and never leaving the page), the reel photos loading,
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
LEDE = ("Everything you need to post this shoot, in one place. Make your reel or carousel, write its words, then add it "
        "to your posting queue. Nothing gets posted for you.")

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
    """Her post kit page, the newest on this computer (v20: the three steps; v24: the design preview), when her
    handoff is here."""
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v2[0-9]-*"), reverse=True):
            f = h / "Carousel designer and reel picker" / "pages" / "post-kit.html"
            if f.is_file() and "Add to my queue" in f.read_text(encoding="utf-8"):
                return html.unescape(f.read_text(encoding="utf-8")).replace("\\'", "'")
    return None


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
        print("SKIP  her words against her own page: her handoff v20 is not on this computer", flush=True)
        return
    # (the design preview's two lines are hers from v24 on: checked just below, against her v24 page, when it is here)
    missing = [key for key, v in k.KIT_WORDS.items() if not (key.startswith("preview_") and "design_preview" not in t)
               and any(frag.strip() and frag not in t for frag in re.split(r"\{\w+\}", v))]
    case("every word in kit.KIT_WORDS is in her pages/post-kit.html, word for word", not missing, missing)
    for frag in ("slides saved in the Carousel folder", "saved design", "no slides saved yet", "saved in the Stories folder", "'story' : 'stories'",
                 "no stories saved yet", "Make a new version", "Create my reel", "+${order.length - 7}", "slice(0, 7)", "slice(0, 6)"):
        case("her page has %r (our status lines and strips follow it)" % frag, frag in t)
    case("our status lines say her words", k.carousel_status(7, 2) == "7 slides saved in the Carousel folder · 2 saved designs"
         and k.stories_status(3, 1) == "3 stories saved in the Stories folder · 1 saved design"
         and k.carousel_status(0, 1) == "1 saved design, no slides saved yet" and k.stories_status(0, 0) == "Not made yet",
         (k.carousel_status(7, 2), k.stories_status(3, 1), k.carousel_status(0, 1)))
    # v24: the design preview. Her two lines and her style line, found in her page and equal to ours.
    if "design_preview" not in t:
        print("SKIP  her design preview's words against her own page: her handoff v24 is not on this computer", flush=True)
    else:
        raw = next(f.read_text(encoding="utf-8") for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools"))
                   for f in sorted((base / "reference-private").glob("nicole-handoff-v2[0-9]-*/Carousel designer and reel picker/pages/post-kit.html"), reverse=True)
                   if "design_preview" in f.read_text(encoding="utf-8"))
        hers_car = re.search(r"kit\.design_preview \? `<div class=\"status\"><span class=\"dot no\"></span>(.*?)</div>`", raw)
        hers_sto = re.search(r"kit\.story_preview \? `<div class=\"status\"><span class=\"dot no\"></span>(.*?)</div>`", raw)
        hers_css = re.search(r"^\.strip img\.dprev\{.*\}$", raw, re.M)
        case("her v24 page has the two preview lines and the one style line", bool(hers_car and hers_sto and hers_css), (bool(hers_car), bool(hers_sto), bool(hers_css)))
        if hers_car and hers_sto and hers_css:
            case("the Carousel card's preview line is hers, word for word (the design's name where hers has it)",
                 hers_car.group(1).replace("\\'", "'").replace("${esc(kit.design_preview.name)}", "{name}") == k.KIT_WORDS["preview_of"], (hers_car.group(1), k.KIT_WORDS["preview_of"]))
            case("the Stories card's preview line is hers, word for word", hers_sto.group(1).replace("\\'", "'") == k.KIT_WORDS["preview_stories"], (hers_sto.group(1), k.KIT_WORDS["preview_stories"]))
            case("the preview picture's style line is hers, letter for letter, and is in our page's styles", hers_css.group(0) == k.PREVIEW_STYLE and k.PREVIEW_STYLE in k._head("x"), hers_css.group(0))
            case("...and hers shows it with a grey dot, in a plain strip (not the tall one) for stories too",
                 raw.count('<div class="strip"><img class="dprev"') == 2 and "dot no\"></span>A preview of" in raw)
    case("our two preview lines never say Claude, and say 'your'", "Claude" not in k.KIT_WORDS["preview_of"] + k.KIT_WORDS["preview_stories"]
         and k.KIT_WORDS["preview_of"] == "A preview of {name}: your slides aren't saved yet" and k.KIT_WORDS["preview_stories"] == "A preview of your stories: they aren't saved yet")
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
    return [html.unescape(x) for x in re.findall(r"<img(?: class='dprev')? src='([^']*)'", fragment)]


def status_of(fragment):
    m = re.search(r"<div class='status'>(.*?)</div>", fragment, re.S)
    return re.sub(r"\s+", " ", plain(m.group(1))).strip() if m else ""


def steps(fragment):
    """The numbered steps in a card: ["1 Make it", "2 Your words: caption & hooks", "3 Add to my queue"]."""
    return [re.sub(r"\s+", " ", plain(m)).strip() for m in re.findall(r"<div class='stepk'>(.*?)</div>", fragment, re.S)]


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
    case("nothing made: the Reel and Carousel cards have her three steps (Make it, Your words, Add to my queue); the Stories card has none",
         steps(r) == ["1 Make it", "2 Your words: caption & hooks", "3 Add to my queue"] and steps(c) == ["1 Make it", "2 Your words: caption", "3 Add to my queue"]
         and steps(t) == [] and "class='w" not in t, (steps(r), steps(c), steps(t)))
    case("nothing made: 'Not written yet. Tell me about it ...' in both words boxes, and both queue steps locked",
         "Not written yet. Tell me about it and I'll help with your caption and hooks." in plain(r) and "Not written yet. Tell me about it and I'll help with your caption." in plain(c)
         and "Make your reel and write its caption first." in plain(r) and "Make your carousel and write its caption first." in plain(c))
    case("nothing made: no Open in CapCut on a kit with no reel", "id='capcut'" not in text)
    also = text[text.index("<div class='also'>"):]
    head = text[text.index("<header class='head'>"):text.index("</header>")]
    case("nothing made: her buttons at the top, Open the kit folder, Open the Photos folder and My posting queue →, and an empty quiet line (no Singles, no Covers folder yet)",
         re.findall(r"data-sub='([^']*)'", head) == ["", "Photos"] and "Open the kit folder" in head and "Open the Photos folder" in head
         and "<a class='go' id='queueLink' href='/posting.html'>My posting queue &rarr;</a>" in head
         and re.findall(r"data-sub='([^']*)'", also) == [], (re.findall(r"data-sub='([^']*)'", head), re.findall(r"data-sub='([^']*)'", also)))
    return k


def check_page_fresh(s):
    """The fake kit (12 reel picks), step by step through what a photographer makes."""
    k = s.kit
    code, text = page(s)
    case("the page is answered (200), as HTML, UTF-8", code == 200 and text.startswith("<!doctype html>"), code)
    # Nov 7 (Dustin: every page in the reel page's look, no serif): the page's font is the plugin's own DM Sans from
    # /look-font (look.py); it asked for /reel-font and Fraunces italic before.
    case("nothing from the internet in the page: no Google Fonts link, no http(s) address, the plugin's own DM Sans and no serif",
         "googleapis" not in text and not re.search(r"https?://", text)
         and "url('/look-font?f=DMSans-Regular')" in text and "url('/look-font?f=DMSans-SemiBold')" in text
         and "Fraunces" not in text and "--display" not in text and "/reel-font" not in text)
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

    # the saved copy (kit.py page) is the page the server builds
    code, out = s.cmd("kit.py", "page", KIT)
    code2, text = page(s)
    case("the saved copy kit.py page writes is the same page as the one served",
         code == 0 and (k / ".kit" / "Post kit.html").read_text(encoding="utf-8") == text, (code, out[-200:]))

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
    case("the quiet line under the cards: '2 single photos sized for Instagram' with Open the Singles folder, 'The reel cover' with Open the Covers folder",
         re.findall(r"data-sub='([^']*)'", also) == ["Singles", "Covers"] and "2 single photos sized for Instagram" in plain(also)
         and "The reel cover" in plain(also), re.findall(r"data-sub='([^']*)'", also))
    case("no Singles or Covers card of their own (decision 12)", "<h2>Single posts" not in text and text.count("class='piece'") == 3)


# ---------- the design preview (her v24) ----------

def shaped_jpeg(src, w, h, out):
    """A real JPEG of exactly w by h, made from one of the pretend kit's photos with the Mac's own sips (this test
    only; the designer's page draws the real ones)."""
    r = subprocess.run(["/usr/bin/sips", "-s", "format", "jpeg", "-z", str(h), str(w), str(src), "--out", str(out)], capture_output=True, text=True, timeout=60)
    data = Path(out).read_bytes() if r.returncode == 0 and Path(out).is_file() else b""
    return data


def empty_kit(s):
    hits = [p for p in (s.target / "The Assistant" / "Your Content").iterdir() if p.name.endswith(EMPTY_NAME)]
    return hits[0] if hits else None


def send_preview(s, kit_name, did, rev, data, kind=""):
    return s.http("POST", "/design-preview?kit=%s&design=%s&rev=%d%s" % (quote(kit_name), did, rev, kind), body=data, headers={"Content-Type": "image/jpeg"})


def check_preview(s):
    """The kit with nothing made, as the designer's page leaves it: this check sends the pictures the page would."""
    k = empty_kit(s)
    if not case("(the kit with nothing made is there)", k is not None):
        return
    q = quote(k.name)
    code, out = s.cmd("kit.py", "sheet", str(k))                # its photos numbered, as "make posts" leaves a kit
    case("(the kit's photos are numbered: kit.py sheet)", code == 0 and (k / ".kit" / "sheet.json").is_file(), out[-300:])
    ph = photos_of(s.kit)                                       # pictures to shape the test's previews from
    theirs = s.work / "a folder of finished photos"             # this kit was started from a folder: its photos stay there
    scratch = s.work / "preview pictures"
    scratch.mkdir(exist_ok=True)
    photos_before = sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in theirs.iterdir())
    rec_before = (k / ".kit" / "kit.json").read_bytes()

    def cards():
        code, text = page(s, k.name)
        return text, card(text, "carousel")[1], card(text, "stories")[1]

    def pic(n, w, h):
        return shaped_jpeg(ph[n], w, h, scratch / ("p%d-%dx%d.jpg" % (n, w, h)))

    def carousel_shape(slides):
        n = min(slides, 6)
        return n * 216 + (n - 1) * 6, 270

    # the first visit to the designer makes the assistant's own first design
    code, st, _ = s.http("GET", "/design-state?kit=%s" % q)
    if not case("(the designer's first visit made the assistant's own first design)", code == 200 and st and st["design"]["untouched"] and st["design"]["state"]["blocks"], code):
        return
    A, a_rev, a_name, a_slides, stamp = st["design"]["id"], st["design"]["rev"], st["design"]["name"], st["design"]["state"]["slides"], st["stamp"]
    text, c, t = cards()
    case("a design is there but the designer has sent no picture yet: 'No slides yet.' and 'Not made yet', as before", "No slides yet." in plain(c) and status_of(c) == "Not made yet" and "class='dprev'" not in text, status_of(c))
    w, h = carousel_shape(a_slides)
    a1 = pic(0, w, h)
    code, out, _ = send_preview(s, k.name, A, a_rev, a1)
    case("(the designer's page sends the picture of the design it opened)", code == 200 and out == {"ok": True, "same": False}, (code, out))
    text, c, t = cards()
    srcs = strip_srcs(c)
    case("the assistant's own first design, once opened: its picture is the Carousel card's strip, one picture",
         len(srcs) == 1 and srcs[0].startswith("/design-preview?kit=%s&design=%s&v=" % (q, A)) and "<div class='strip'><img class='dprev' src='" in c and "class='more'" not in c, srcs)
    case("...with her line 'A preview of <the design's name>: your slides aren't saved yet' and a grey dot",
         status_of(c) == "A preview of %s: your slides aren't saved yet" % a_name and "<span class='dot no'></span>" in c and "<span class='dot'></span>" not in c, status_of(c))
    case("...and the card no longer says 'No slides yet.'", "No slides yet." not in plain(c))
    code, _, raw = s.http("GET", srcs[0]) if srcs else (0, None, b"")
    case("...the picture loads from that address, and is the one that was sent", code == 200 and raw == a1, code)
    case("...the button beside a preview is her 'Open my carousel →' (hers never says 'Design my carousel' beside a picture of one), though the assistant's own design is still not counted",
         "Open my carousel →" in plain(c) and "Design my carousel" not in plain(c) and "saved design" not in plain(c), plain(c)[-200:])
    case("...the piece is still not made: its queue step is locked",
         "Make your carousel and write its caption first." in plain(c) and "data-add=" not in c, plain(c)[-200:])
    case("...the Stories card is as it was ('No stories yet.', 'Not made yet')", "No stories yet." in plain(t) and status_of(t) == "Not made yet" and "class='dprev'" not in t, status_of(t))
    case("...no path in the page, and nothing from the internet", not re.search(r"/private/|/Users/|\.kit/|kit\.json|https?://", text))

    # a blank design made after it: nothing is shown of a blank design
    blank = {"slides": 5, "bg": "#ffffff", "blocks": []}
    code, out, _ = s.http("POST", "/design-new", body={"kit": k.name, "stamp": stamp, "state": blank, "token": "kitcardtok01"})
    B = out["design"]["id"] if code == 200 and out else ""
    code2, out2, _ = send_preview(s, k.name, B, 0, pic(1, *carousel_shape(5)))
    text, c, t = cards()
    case("a blank design made afterwards (the newest design): its picture is refused, and the card still previews the first design",
         bool(B) and code2 == 409 and not (k / ".kit" / "designs" / (B + ".preview.jpg")).exists()
         and status_of(c) == "A preview of %s: your slides aren't saved yet" % a_name and ("design=%s&" % A) in strip_srcs(c)[0], (code2, out2, status_of(c)))

    # a second design with something on it, changed later: the newest design wins
    time.sleep(0.05)
    code, out, _ = s.http("POST", "/design-new", body={"kit": k.name, "stamp": stamp, "token": "kitcardtok02"})
    C = out["design"]["id"] if code == 200 and out else ""
    c_name, c_slides = (out["design"]["name"], out["design"]["state"]["slides"]) if C else ("", 1)
    code, out, _ = send_preview(s, k.name, C, 0, pic(2, *carousel_shape(c_slides)))
    text, c, t = cards()
    case("a second design with photos on it, made later, with a picture: the card previews it (the design changed last)",
         code == 200 and status_of(c) == "A preview of %s: your slides aren't saved yet" % c_name and ("design=%s&" % C) in strip_srcs(c)[0], (code, status_of(c)))
    v_before = re.search(r"&v=(\d+)", strip_srcs(c)[0]).group(1)
    time.sleep(1.1)
    a2 = pic(3, w, h)
    code, out, _ = send_preview(s, k.name, A, a_rev, a2)
    pa, pc = k / ".kit" / "designs" / (A + ".preview.jpg"), k / ".kit" / "designs" / (C + ".preview.jpg")
    text, c, t = cards()
    case("the older design gets a newer picture file: the card still previews the design that was changed last (hers: by the design, not the picture)",
         code == 200 and pa.read_bytes() == a2 and pa.stat().st_mtime > pc.stat().st_mtime
         and status_of(c) == "A preview of %s: your slides aren't saved yet" % c_name and ("design=%s&" % C) in strip_srcs(c)[0], status_of(c))
    case("...and that picture's address is unchanged (its 'v' is its own file's time)", re.search(r"&v=(\d+)", strip_srcs(c)[0]).group(1) == v_before)
    c2 = pic(4, *carousel_shape(c_slides))
    time.sleep(0.05)
    send_preview(s, k.name, C, 0, c2)
    text, c, t = cards()
    case("a new picture of the previewed design changes its address, so a browser never shows the old one", re.search(r"&v=(\d+)", strip_srcs(c)[0]).group(1) != v_before, strip_srcs(c))

    # a design's name is text
    code, cst, _ = s.http("GET", "/design-state?kit=%s&design=%s" % (q, C))
    tricky = "<b>Tom & \"Jo\"</b>"
    code, out, _ = s.http("POST", "/design", body={"kit": k.name, "design": C, "stamp": stamp, "base": cst["design"]["rev"], "page": "kitcardpage1", "name": tricky, "state": cst["design"]["state"]})
    text, c, t = cards()
    case("a design's name is shown as text, never as markup", code == 200 and status_of(c) == "A preview of %s: your slides aren't saved yet" % tricky
         and "A preview of &lt;b&gt;Tom &amp; &quot;Jo&quot;&lt;/b&gt;: your slides aren&#x27;t saved yet" in c and "<b>Tom" not in c, (code, c[-400:]))

    # a design emptied after its picture was kept: its old picture is never shown (a fault of hers, fixed)
    code, out, _ = s.http("POST", "/design", body={"kit": k.name, "design": C, "stamp": stamp, "base": out["rev"] if code == 200 and out else -1, "page": "kitcardpage1",
                                                   "name": tricky, "state": dict(cst["design"]["state"], blocks=[])})
    emptied_rev = out["rev"] if code == 200 and out else -1
    text, c, t = cards()
    code2, _, raw = s.http("GET", "/design-preview?kit=%s&design=%s" % (q, C))
    case("the previewed design is emptied (every photo taken off): the card stops showing its old picture and previews the next design that has something on it",
         code == 200 and pc.is_file() and status_of(c) == "A preview of %s: your slides aren't saved yet" % a_name and ("design=%s&" % A) in strip_srcs(c)[0] and tricky not in html.unescape(c), (code, status_of(c)))
    case("...the emptied design's picture is still on disk (nothing is removed) but its address answers not found", pc.is_file() and code2 == 404 and raw[:2] != b"\xff\xd8", code2)
    code3, out3, _ = s.http("POST", "/design", body={"kit": k.name, "design": C, "stamp": stamp, "base": emptied_rev, "page": "kitcardpage1", "name": tricky, "state": cst["design"]["state"]})
    text, c, t = cards()
    case("the photos put back: that design is previewed again", code3 == 200 and status_of(c) == "A preview of %s: your slides aren't saved yet" % tricky and ("design=%s&" % C) in strip_srcs(c)[0], (code3, status_of(c)))

    # stories: the same, in her words for stories
    code, sst, _ = s.http("GET", "/design-state?kit=%s&kind=stories" % q)
    S = sst["design"]["id"] if code == 200 and sst else ""
    code, out, _ = send_preview(s, k.name, S, sst["design"]["rev"], pic(5, 162, 288), kind="&kind=stories")
    text, c, t = cards()
    case("the shoot's stories while they are one empty story: no picture is kept and the Stories card is as it was", code == 409 and status_of(t) == "Not made yet" and "class='dprev'" not in t, (code, status_of(t)))
    s_state = {"slides": 6, "bg": "#ffffff", "blocks": [{"id": 1, "type": "text", "text": "A sneak peek", "font": "Inter", "size": 72, "weight": 700, "italic": False,
                                                          "upper": False, "al": "center", "color": "#111111", "ls": 0, "lh": 1.3, "x": 100, "y": 400, "w": 800, "h": 200}]}
    code, out, _ = s.http("POST", "/design", body={"kit": k.name, "kind": "stories", "design": S, "stamp": sst["stamp"], "base": sst["design"]["rev"], "page": "kitcardpage2", "state": s_state})
    s_rev = out["rev"] if code == 200 and out else -1
    s1 = pic(6, 4 * 162 + 18, 288)
    code, out, _ = send_preview(s, k.name, S, s_rev, s1, kind="&kind=stories")
    text, c, t = cards()
    srcs = strip_srcs(t)
    case("stories with something on them, and their picture sent (the first four of six): the Stories card's strip is that one picture, in a plain strip",
         code == 200 and len(srcs) == 1 and srcs[0].startswith("/design-preview?kit=%s&design=%s&kind=stories&v=" % (q, S)) and "<div class='strip'><img class='dprev' src='" in t, (code, srcs))
    case("...with her line 'A preview of your stories: they aren't saved yet', a grey dot, and no words box or queue step",
         status_of(t) == "A preview of your stories: they aren't saved yet" and "<span class='dot no'></span>" in t and steps(t) == [], status_of(t))
    code, _, raw = s.http("GET", srcs[0]) if srcs else (0, None, b"")
    case("...the stories picture loads from that address", code == 200 and raw == s1, code)
    case("...and the Stories card's button is her 'Open my stories →'", "Open my stories →" in plain(t) and "Make my stories" not in plain(t), plain(t)[-160:])
    case("...and the Carousel card still shows its own", "design=%s&" % C in strip_srcs(c)[0] and "kind=stories" not in strip_srcs(c)[0])

    # none of it touched anything of theirs, or the kit's record, or what counts as a design
    names = sorted(p.name for p in (k / ".kit" / "designs").iterdir() if not p.name.startswith("."))
    case("the pictures are hidden files beside their designs: '<id>.preview.jpg', one each, and no scratch file left",
         [n for n in names if n.endswith(".jpg")] == sorted([A + ".preview.jpg", C + ".preview.jpg"])
         and [p.name for p in (k / ".kit" / "story-designs").iterdir() if p.name.endswith(".jpg")] == [S + ".preview.jpg"]
         and not [p for p in (k / ".kit" / "designs").iterdir() if p.name.startswith(".")], names)
    case("the kit's record and its photos are as they were, and no Carousel or Stories folder was made",
         (k / ".kit" / "kit.json").read_bytes() == rec_before and sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in theirs.iterdir()) == photos_before
         and not (k / "Carousel").exists() and not (k / "Stories").exists())
    code, out = s.cmd("kit.py", "page", k.name)
    code2, text = page(s, k.name)
    case("the saved copy kit.py page writes is the same page as the one served, preview and all", code == 0 and "class='dprev'" in text and (k / ".kit" / "Post kit.html").read_text(encoding="utf-8") == text, (code, out[-200:]))

    # saved slides still win (this check's own pictures, as kit.py build or Save slides would leave them)
    (k / "Carousel").mkdir()
    shutil.copyfile(ph[0], k / "Carousel" / "Slide 01.jpg")
    (k / "Stories").mkdir()
    shutil.copyfile(ph[1], k / "Stories" / "Story 01.jpg")
    text, c, t = cards()
    case("saved slides win: the Carousel card shows the slide and '1 slide saved in the Carousel folder · 2 saved designs' (the blank one and the second; not the assistant's own), no preview",
         strip_srcs(c) == ["Carousel/Slide 01.jpg"] and status_of(c) == "1 slide saved in the Carousel folder · 2 saved designs" and "class='dprev'" not in c and "<span class='dot'></span>" in c, (strip_srcs(c), status_of(c)))
    case("saved stories win: the Stories card shows the story and '1 story saved in the Stories folder · 1 saved design', no preview",
         strip_srcs(t) == ["Stories/Story 01.jpg"] and status_of(t) == "1 story saved in the Stories folder · 1 saved design" and "class='dprev'" not in t, (strip_srcs(t), status_of(t)))
    (k / "Carousel" / "Slide 01.jpg").rename(scratch / "Slide 01.jpg")       # this check's own two pictures, taken out again
    (k / "Stories" / "Story 01.jpg").rename(scratch / "Story 01.jpg")
    text, c, t = cards()
    case("with the slides gone again the previews are back", "class='dprev'" in c and "class='dprev'" in t and status_of(t) == "A preview of your stories: they aren't saved yet")

    # an unplugged drive
    content = s.target / "The Assistant"
    away = s.target / "The Assistant (unplugged for the preview check)"
    src = strip_srcs(c)[0]
    content.rename(away)                       # this check's own pretend drive, put back below
    try:
        code, text = page(s, k.name)
        code2, _, raw = s.http("GET", src)
        case("the drive unplugged: her 'I can't reach this shoot right now...' line with no card, and the picture's address answers not found",
             code == 404 and REACH in html.unescape(text) and "class='piece'" not in text and code2 == 404 and raw[:2] != b"\xff\xd8", (code, code2))
        km = kit_module(s)
        import design as design_mod
        case("...and asking which design to preview on a kit that is not there gives nothing, never an error",
             design_mod.newest_preview(k) is None and design_mod.newest_preview(k, "stories") is None)
    finally:
        away.rename(content)
    text, c, t = cards()
    case("plugged in again: both previews are back", "class='dprev'" in c and "class='dprev'" in t and text.count("class='piece'") == 3)


def check_preview_browser(c, s):
    k = empty_kit(s)
    if k is None:
        return
    c.clear_errors()
    c.open(s.url("/content/%s/Post%%20kit.html" % quote(k.name)))
    ok = c.wait_for("Array.prototype.every.call(document.querySelectorAll('img.dprev'), function(i){ return i.complete && i.naturalWidth > 0; }) && document.querySelectorAll('img.dprev').length === 2", seconds=10)
    got = c.js("JSON.stringify(Array.prototype.map.call(document.querySelectorAll('img.dprev'), function(i){ var r = i.getBoundingClientRect(), p = i.closest('.piece').getBoundingClientRect(), cs = getComputedStyle(i);"
               " return {piece: i.closest('.piece').dataset.piece, nw: i.naturalWidth, nh: i.naturalHeight, w: r.width, h: r.height, inside: r.left >= p.left && r.right <= p.right + 0.5,"
               " fit: cs.objectFit, shadow: cs.boxShadow, bg: cs.backgroundImage + cs.backgroundColor}; }))")
    got = json.loads(got) if isinstance(got, str) else []
    case("in a browser: both preview pictures load, on the Carousel and the Stories cards", ok and [g["piece"] for g in got] == ["carousel", "stories"], got)
    case("...each is 120 px tall, shown whole at its own shape (her style line), and stays inside its card",
         bool(got) and all(abs(g["h"] - 120) < 0.6 and g["fit"] == "contain" and g["inside"] and g["w"] <= g["nw"] / g["nh"] * 120 + 1 for g in got), got)
    case("...with no tile behind it and no outline (hers: background none, box-shadow none)", bool(got) and all(g["shadow"] == "none" and "rgba(0, 0, 0, 0)" in g["bg"] for g in got), got)
    case("...nothing asked of the internet and no error on the page", not c.outside_requests() and not c.page_errors(), (c.outside_requests(), c.page_errors()))
    href = c.js("document.querySelector(\"a.piece[data-piece='carousel']\").getAttribute('href')")
    case("...and the card is still one link to the designer (the picture is not a link of its own)", href == "/design.html?kit=" + quote(k.name) and c.js("document.querySelectorAll('a.piece a').length") == 0, href)
    c.phone(390, 844)
    try:
        c.open(s.url("/content/%s/Post%%20kit.html" % quote(k.name)))
        c.wait_for("document.querySelectorAll('img.dprev').length === 2 && document.querySelector('img.dprev').complete", seconds=10)
        wide = c.js("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        fits = c.js("Array.prototype.every.call(document.querySelectorAll('img.dprev'), function(i){ var r = i.getBoundingClientRect(), p = i.parentNode.getBoundingClientRect(); return r.right <= p.right + 0.5; })")
        case("...at a phone's width the picture is no wider than its card, and the page does not scroll sideways", wide <= 0 and fits, (wide, fits))
    finally:
        c.desktop()


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
    case("in a browser: the page's font is the plugin's own DM Sans and it loaded (no Fraunces declared)",
         c.js("(function(){var f=Array.from(document.fonts);return f.some(function(x){return x.family.replace(/[\"']/g,'')=='Assistant Sans'&&x.weight=='400'&&x.status=='loaded'})"
              "&&f.some(function(x){return x.family.replace(/[\"']/g,'')=='Assistant Sans'&&x.weight=='600'&&x.status=='loaded'})"
              "&&!f.some(function(x){return /Fraunces/.test(x.family)})})()") is True,
         c.js("Array.from(document.fonts).map(function(x){return x.family+' '+x.weight+' '+x.status}).join(', ')"))

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
    wide = c.js("(function(){var d=document.documentElement,out=[];document.querySelectorAll('.piece').forEach(function(card){"
                "var e=card.getBoundingClientRect().right+0.5;card.querySelectorAll('.strip,.cta,.w').forEach(function(n){"
                "if(n.getBoundingClientRect().right>e)out.push(n.className)})});return {page:d.clientWidth,scroll:d.scrollWidth,out:out,"
                "imgs:Math.max.apply(null,Array.from(document.querySelectorAll('.strip')).map(function(s){return s.querySelectorAll('img').length}))}})()")
    # (against the page's own width: window.innerWidth grows with a page that overflows, so it could never fail)
    case("at a phone's width: one column, no sideways scroll, nothing hanging out of a card (a row of 6 or more pictures)",
         wide["scroll"] <= wide["page"] == 390 and not wide["out"] and wide["imgs"] >= 6, wide)
    case("at a phone's width: the steps sit under the photos", True
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
        group("the design preview", check_preview, s)
        group("an unplugged drive", check_unplugged, s)
        if not chrome_drive.find_chrome():
            print("SKIP  the kit page in a browser: no Chrome on this computer", flush=True)
        else:
            with chrome_drive.Chrome(work=str(run), size=(1280, 1400)) as c:
                group("the kit page in a browser", check_browser, c, s)
                group("the design preview in a browser", check_preview_browser, c, s)
                group("an unplugged drive, in a browser", check_unplugged_browser, c, s)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
