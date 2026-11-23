#!/usr/bin/env python3
"""The reel page rebuilt (Nicole's handoff v27, section 2; Lane A, stage 2 of the v27 build): the chooser of four
kinds, each kind its own page, step 1 and 2 as rebuilt (the videos' drop-down, the ask box before the line to copy,
Choose your photos, + Add photos, Show my new photos on numbers that stay fixed, the order stuck at the top), the
song drop-down with Listen and Remove this song, and Add this reel to my posting queue.

    python3 tests/reel_v27_page_check.py                 everything (the page in a hidden Chrome)
    python3 tests/reel_v27_page_check.py --no-chrome     the checks that need no browser
    python3 tests/guard.py 3000 python3 tests/reel_v27_page_check.py --port 8812     as it is run: under the memory guard

What it holds:
  her words     the chooser and the kinds (reel_page.KIND_WORDS), the song drop-down and the queue button against
                her v27 reel page, both ways
  the chooser   GET /reel.html?kit= with no kind: her title and lede, her four cards as links written on the
                server (Talking to camera to the talking page), no script, nothing written by looking at it; an
                unknown kind is the chooser too
  the kinds     each kind's title, lede and visible steps; a reel's own kind wins over the address; a reel from
                before v27 opens by its footage setting; nothing is written on a plain open
  the reels     a new reel started from a kind's page is that kind at once; the version route's answer says the
                open reel's kind; the state and reels_for_kit carry each reel's kind; the chat's reels --new --kind
  new photos    on the server: a photo dropped into the Photos folder is numbered on the page's own poll, every
                other photo keeping its number, a photo gone keeping its number unused; + Add photos opens the
                folder and says her words
  the songs     the drop-down's names, Listen (GET /reel-song answers 206 to a Range, 404 to an unknown id, 403
                to another website), and the Remove button wired to POST /reel-song-remove
  the queue     GET /reel-state carries each reel's place in the posting queue; the add posts the version; a
                second press says her "already" line; two reels are two pieces
  the page      in a hidden Chrome: her steps renumbered per kind, the switch under Your reels landing on the
                other reel's own kind, + Add photos, "N new photos in." with Show my new photos, the song
                drop-down with Listen and the two taps of Remove, the queue button and its lines, a phone's width

Nothing here touches the real ~/.studio, a real kit, CapCut, the real Trash or a visible window: a scratch home
and pretend kits. Python 3.9, standard library only.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import talking_page_check as t  # noqa: E402   (its Setup: a scratch home, pretend kits, the page server)
import words_page_check as wpc  # noqa: E402   (the tiny JPEG)

SCRIPTS = t.SCRIPTS
PORT = 8812
# A PC cannot make a folder with < or > in its name (and the Assistant never makes one: a shoot's name loses them when its
# kit is made), so there the shoot's folder keeps the ampersand, the apostrophes and the emoji only. A Mac keeps the tag.
KIT = "2026-10-03 Kinds & 'reels' 🎞" if t.WINDOWS else "2026-10-03 Kinds <b>& 'reels' 🎞"
PAGE = "abcdefgh12"
KINDS = ("bts", "photos", "broll")
FIX = ROOT / "tests" / "fixtures"
BEAT60 = FIX / "test-beat-60s.wav"

# Her chooser, as her v27 reel-maker.html has it (the kinds' cards)
HER_KINDS = [("kBts", "Behind the scenes", "Video clips from the shoot, mixed with your finished photos."),
             ("kPhotos", "Just photos", "Your finished photos, cut on the beat."),
             ("kTalk", "Talking to camera", "You talk about the shoot, and your photos go with what you say."),
             ("kBroll", "B-roll", "Only video clips from the shoot, cut on the beat. No photos.")]
TITLES = {"bts": "behind the scenes", "photos": "reel", "broll": "B-roll"}
TITLES_B = {"bts": "Behind the scenes", "photos": "Just photos", "broll": "B-roll"}   # her kind names on the path at the top (crumbs.js)
sys.path.insert(0, str(SCRIPTS))
import look  # noqa: E402   (the path at the top, as the page builds it)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant



def her(key):
    """Her line as this computer says it: word for word on a Mac; File Explorer, the Recycle Bin and Restore on a PC."""
    import reel_page as rp
    return rp.pc_words(rp.trash_words(rp.WORDS[key]))

def her_v27(name="pages/reel-maker.html"):
    """A file of her v27 handoff (her reel page, or UPDATE-v27.md), or None when it isn't on this computer."""
    for base in (ROOT, ROOT.parent / "hf-tools", Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v27-*")):
            f = h / "Carousel designer and reel picker" / name
            if f.is_file():
                return nicole_nov22.read(f)   # Nicole, Nov 22: everything is the Assistant
    return None


def run(s, script, *args):
    import subprocess
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", env=s.env)
    return r.returncode, (r.stdout + r.stderr).strip()


def reel_rec(s, kit):
    try:
        return json.loads((s.kit(kit) / ".kit" / "reel-page.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def kit_bytes(s, kit):
    """Every record of the kit's hidden folder, with its bytes (to see that a look wrote nothing; the small copies
    of the photos, made in the background for any page, are not records)."""
    out = {}
    for p in sorted((s.kit(kit) / ".kit").glob("*.json")):
        out[p.name] = p.read_bytes()
    return out


def reel_state(s, kit):
    return s.http("GET", "/reel-state" + s.q(kit))[1]


def save(s, kit, saved, reel=None, page=PAGE):
    st = reel_state(s, kit)
    body = {"kit": kit, "stamp": st["stamp"], "base": st["rev"], "page": page, "saved": saved}
    if reel:
        body["reel"] = reel
    code, j, _, _ = s.http("POST", "/reel-save", body)
    return code, j


def ver(s, kit, **ask):
    code, j, _, _ = s.http("POST", "/reel-version", dict(ask, kit=kit))
    return code, j


def page(s, kit, kind=None, headers=None):
    code, _j, raw, _h = s.http("GET", "/reel.html" + s.q(kit) + ("&kind=" + kind if kind else ""), headers=headers)
    return code, raw.decode("utf-8", "replace")


def title_of(pg):
    m = re.search(r"<title>(.*?)</title>", pg)
    return html.unescape(m.group(1)) if m else ""


def lede_of(pg):
    m = re.search(r"<p class='lede'>(.*?)</p>", pg)
    return html.unescape(m.group(1)) if m else ""


def shown_steps(pg):
    """The steps written on the page and which are hidden for this kind (data-kind-hidden), in her order."""
    return [(m.group(1), bool(m.group(2))) for m in re.finditer(r"<section class='step(?: watch)?' id='(\w+)'(?:( hidden data-kind-hidden='1')| hidden)?>", pg)]


# ---------- 1. her words ----------

def run_words(s):
    import reel_page as rp
    hers = her_v27()
    case("the chooser's words are in their own table (reel_page.KIND_WORDS), and the three kinds are hers", set(rp.KINDS) == set(KINDS)
         and all(k in rp.KIND_WORDS for k in ("chooser_h2", "chooser_say", "chooser_lede", "all_reels", "crumb_reels")) and len(rp.KIND_WORDS) == 20)
    if hers is None:
        t.skip("her v27 words against her v27 reel page: her handoff (reference-private) isn't on this computer")
        return
    text = html.unescape(hers).replace("\\'", "'")
    # her link back to the chooser is empty on her page (crumbs.js, the path at the top, stands in for it there); its
    # words are her UPDATE-v27.md's, section 2
    text += "\n" + (her_v27("UPDATE-v27.md") or "")
    bad = [(k, frag) for k, v in rp.KIND_WORDS.items() for frag in re.split(r"\{\w+\}", v) if len(frag.strip()) >= 2 and frag not in text]
    case("every word of ours for the chooser and the kinds (%d lines) is in her v27 reel page or UPDATE-v27.md, word for word" % len(rp.KIND_WORDS), not bad, bad)
    block = re.search(r'<section class="step chooser" id="chooser" hidden>(.*?)</section>', hers, re.S).group(1)
    theirs = re.findall(r"<a class=\"kind\" id=\"(\w+)\"><b>(.*?)</b><span>(.*?)</span></a>", block)
    case("her four cards, in her order, with her words", [(a, html.unescape(b), html.unescape(c)) for a, b, c in theirs] == HER_KINDS, theirs)
    ours = {k: v for k, v in rp.KIND_WORDS.items() if k.startswith("kind_")}
    case("...and every word on them is in our table (both ways)",
         all(ours["kind_%s_b" % k] == b and ours["kind_%s_s" % k] == c for k, (_i, b, c) in zip(("bts", "photos", "talk", "broll"), HER_KINDS)))
    kw = re.search(r"const KIND_WORDS = \{(.*?)\n\};", hers, re.S).group(1)
    for k in KINDS:
        m = re.search(r"%s: \{title: '(.*?)', lede: '(.*?)'\}" % k, kw)
        case("her KIND_WORDS.%s: the title's word and the lede, both ways" % k, bool(m) and rp.KIND_WORDS["title_" + k] == "{short} " + m.group(1).replace("\\'", "'")
             and rp.KIND_WORDS["lede_" + k] == m.group(2).replace("\\'", "'"), m and m.groups())
    h2 = re.search(r'<section class="step chooser" id="chooser" hidden>\s*<h2>(.*?)</h2>\s*<p class="say">(.*?)</p>', hers, re.S)
    case("her chooser's heading and line, both ways", bool(h2) and (html.unescape(h2.group(1)), html.unescape(h2.group(2))) == (rp.KIND_WORDS["chooser_h2"], rp.KIND_WORDS["chooser_say"]))
    case("her lede on the chooser, her title's last word, and her link back to it, both ways",
         "lede.textContent = '%s'" % rp.KIND_WORDS["chooser_lede"] in hers and "' reels<em>.</em>'" in hers
         and rp.KIND_WORDS["title_chooser"] == "{short} reels" and rp.KIND_WORDS["all_reels"] in text)
    case("her v27 heading for step 1 and step 2, both ways", 'Choose your behind-the-scenes footage' in hers and rp.WORDS["foot_h2"] == "Choose your behind-the-scenes footage"
         and '<h2><span class="num">2</span>Choose your photos</h2>' in hers and rp.WORDS["order_h2"] == "Choose your photos")
    case("her v27 step 1 words: the ask box's label, its first example and its placeholder",
         rp.WORDS["ask_label_html"] in hers and rp.WORDS["ask_ex1"] in text and 'placeholder="%s"' % rp.WORDS["ask_placeholder"] in hers)
    case("her v27 + Add photos row, word for word",
         '<button class="btn small" id="addPhotos">%s</button><span class="tools-say" id="addPhotosSay">%s</span>' % (rp.WORDS["add_photos"], rp.WORDS["add_photos_say"]) in text)
    case("her lines for the Photos folder: opening, open, could not open", all(x in text for x in (her("opening_photos"), her("photos_open"), her("cant_open_photos"))))
    case("her v27 hides 'How should it feel?' (#feelRow) on the page, so ours writes the row hidden",
         "#feelRow{display:none!important}" in hers and "id='feelRow' hidden" in rp.page_html(KIT, "x", True, "bts"))
    sty = re.search(r"<style>(.*?)</style>", hers, re.S).group(1)
    for rule in (".kinds{", ".kind{", ".kind:hover{", ".vdrop{", ".vdrop summary{", ".reelstick{", ".reelstick.stuck{", ".addph{", ".songpick{", ".songpick select{", ".linkbtn{", ".toq{"):
        line = next((x for x in sty.splitlines() if x.startswith(rule)), None)
        case("her style rule %s is in the page as she wrote it" % rule, line is not None and line.split("}")[0] + "}" in rp.V27_CSS, line)


# ---------- 2. the chooser ----------

def run_chooser(s):
    import reel_page as rp
    kit = KIT
    short = kit[11:]
    before = kit_bytes(s, kit)
    code, pg = page(s, kit)
    case("with no kind in the address the reel page is the chooser (hers): her title", code == 200 and title_of(pg) == short + " reels", title_of(pg))
    case("her lede on it", lede_of(pg) == rp.KIND_WORDS["chooser_lede"], lede_of(pg))
    case("her heading and her line", "<h2>" + html.escape(rp.KIND_WORDS["chooser_h2"]) + "</h2>" in pg and html.escape(rp.KIND_WORDS["chooser_say"]) in pg)
    # Where no finished video can be made (a PC) the B-roll card carries one short line of ours after hers, inside
    # the card (Nicole, Nov 23; tests/broll_pc_check.py holds its words and place). Her four cards are the same on
    # both computers; the line is there exactly where reel_page.pc_footage() says so, and nowhere else.
    # (the page server is started without the tests' no-video switch, see talking_page_check.Setup, so ask the same way)
    held = os.environ.pop("ASSISTANT_NO_AVFOUNDATION", None)
    try:
        no_video = bool(rp.pc_footage())
    finally:
        if held is not None:
            os.environ["ASSISTANT_NO_AVFOUNDATION"] = held
    pc_line = "<span class='pcnote' id='kBrollPc'>" + html.escape(rp.OUR_WORDS["broll_card_pc"]) + "</span>"
    cards = re.findall(r"<a class='kind' id='(\w+)' href='([^']*)'><b>(.*?)</b><span>(.*?)</span>(<span class='pcnote' id='kBrollPc'>.*?</span>)?</a>", pg)
    case("her four cards, in her order, with her words, each a plain link written on the server",
         [(a, html.unescape(c), html.unescape(d)) for a, _b, c, d, _p in cards] == HER_KINDS, cards)
    case("...our one PC line is on the B-roll card only, and only on a computer that can't save a finished video (%s here)"
         % ("it can't" if no_video else "it can"),
         [p for _a, _b, _c, _d, p in cards] == ["", "", "", pc_line if no_video else ""] and pg.count("id='kBrollPc'") == (1 if no_video else 0), cards[-1:])
    cards = [c[:4] for c in cards]
    hrefs = {a: html.unescape(b) for a, b, _c, _d in cards}
    case("the three kinds open this shoot's reel page as that kind, by the folder name only",
         hrefs.get("kBts") == "/reel.html?kit=%s&kind=bts" % quote(kit) and hrefs.get("kPhotos") == "/reel.html?kit=%s&kind=photos" % quote(kit)
         and hrefs.get("kBroll") == "/reel.html?kit=%s&kind=broll" % quote(kit), hrefs)
    case("Talking to camera opens the talking reel's page for the same shoot", hrefs.get("kTalk") == "/talking.html?kit=" + quote(kit), hrefs.get("kTalk"))
    case("no path in it, and the shoot's name as letters, not a tag", str(s.kit(kit)) not in pg and "/private" not in pg and "<b>&" not in title_of(pg).replace(short, "") and html.escape(short) in pg)
    case("no script, no Your reels bar, no Make my reel on the chooser (nothing to save, nothing polled)",
         "<script" not in pg and "id='reels'" not in pg and "id='makeBtn'" not in pg and "id='toqBar'" not in pg)
    case("the way back is the post kit page, as every page's is", "href='/content/%s/Post%%20kit.html'" % quote(kit) in pg)
    case("looking at the chooser wrote nothing", kit_bytes(s, kit) == before)
    code2, pg2 = page(s, kit, "sideways")
    case("a kind the page doesn't know is the chooser too", code2 == 200 and title_of(pg2) == short + " reels")
    code3, pg3 = page(s, kit, headers={"Sec-Fetch-Site": "cross-site"})
    case("a link from another website gets the plain page, not the chooser", code3 == 200 and "kBts" not in pg3)
    case("reel_page.py open prints the chooser's address last, and says the kind only once one is chosen",
         run(s, "reel_page.py", "open", kit)[1].splitlines()[-1].endswith("/reel.html?kit=" + quote(kit)) and "is a " not in run(s, "reel_page.py", "open", kit)[1])


# ---------- 3. the kinds ----------

def run_kinds(s):
    import reel_page as rp
    kit = KIT
    short = kit[11:]
    # since stage 4 (A13, A10): her "Would you like to direct this edit?" after the song (not on B-roll) and
    # "Watch your reel before you make it" last, on every kind
    want = {"bts": [("step0", False), ("step1", False), ("step3", False), ("stepDirect", False), ("stepStyle", False), ("step4", False), ("watch", False)],
            "photos": [("step0", True), ("step1", False), ("step3", False), ("stepDirect", False), ("stepStyle", True), ("step4", False), ("watch", False)],
            "broll": [("step0", False), ("step1", True), ("step3", False), ("stepDirect", True), ("stepStyle", True), ("step4", True), ("watch", False)]}
    for kind in KINDS:
        before = kit_bytes(s, kit)
        code, pg = page(s, kit, kind)
        case("%s: her title and her lede, written on the server" % kind, code == 200 and title_of(pg) == short + " " + TITLES[kind] and lede_of(pg) == rp.KIND_WORDS["lede_" + kind], (title_of(pg), lede_of(pg)[:50]))
        case("%s: the steps a %s reel doesn't use are hidden (hers: just photos hides the footage; B-roll hides the photos, the style, the vibe)" % (kind, TITLES[kind]),
             shown_steps(pg) == want[kind], shown_steps(pg))
        case("%s: her path at the top in the bar (Home › <shoot> post kit › Reels › the kind, Reels linking back to the chooser), her Back pill and her link to the chooser kept hidden" % kind,
             look.crumbs(look.kit_trail(kit) + [("Reels", "/reel.html?kit=" + quote(kit)), (TITLES_B[kind], None)]) in pg
             and "id='allReels' hidden style='display:none!important' href='/reel.html?kit=%s'>%s</a>" % (quote(kit), html.escape(rp.KIND_WORDS["all_reels"])) in pg
             and "id='back' style='display:none' href='/content/" in pg, pg[pg.find("<div class='bar'>"):pg.find("<div class='bar'>") + 700])
        case("%s: no old yes/no cards, no Talking card on a kind's page" % kind, "modeBts" not in pg and "modeTalk" not in pg and "kTalk" not in pg)
        case("%s: the page's data says its kind" % kind, "\"kind\": \"%s\"" % kind in pg)
        case("%s: a plain open wrote nothing (hers saved footage and style on every load)" % kind, kit_bytes(s, kit) == before)
    pg = page(s, kit, "bts")[1]
    case("step 1 (behind the scenes): her heading, no 'Do you want...' line, the ask box before the line to copy, the videos' drop-down's place",
         "<span class='num'>1</span>Choose your behind-the-scenes footage</h2><div id='btsBox' hidden>" in pg
         and pg.index("id='askIn'") < pg.index("id='pasteWords'") and pg.index("id='vlist'") < pg.index("class='insight'"))
    case("step 2: her heading and line, the order in its sticky box with the count, then + Add photos, then All your photos",
         "<span class='num'>2</span>Choose your photos</h2><p class='say'>" + html.escape(rp.WORDS["order_say"]) in pg
         and re.search(r"<div class='reelstick' id='reelStick'><div class='reelwrap' id='reelwrap'><div id='reel'></div></div><div class='count' id='count'></div>.*?</div><div class='addph'><button class='btn small' id='addPhotos' type='button'>\+ Add photos</button><span class='tools-say' id='addPhotosSay'>", pg)
         and pg.index("id='addPhotos'") < pg.index("id='allBox'"))
    # a reel's own kind wins over the address
    code, j = save(s, kit, {"kind": "bts", "footage": True})
    case("the kind is saved with the reel (saved.kind)", code == 200 and (reel_rec(s, kit) or {}).get("saved", {}).get("kind") == "bts", (code, j))
    case("...and the state says it, for the open reel and in its list of reels",
         reel_state(s, kit)["kind"] == "bts" and reel_state(s, kit)["versions"][0].get("kind") == "bts")
    case("a saved behind-the-scenes reel opened from a just-photos address shows as behind the scenes (ours: the reel's own kind wins)",
         title_of(page(s, kit, "photos")[1]) == short + " behind the scenes")
    case("refused: a kind the page doesn't know, and a kind that isn't text", save(s, kit, {"kind": "talk"})[0] == 400 and save(s, kit, {"kind": 1})[0] == 400)
    case("B-roll's one style is taken as a style (saved.style), nothing else new is", save(s, kit, {"style": "broll"})[0] == 200 and save(s, kit, {"style": "x"})[0] == 400)
    # a reel from before v27: no kind, by its footage setting
    rec = reel_rec(s, kit)
    rec["saved"].pop("kind", None)
    rec["saved"]["footage"] = False
    rec["saved"]["style"] = "first"
    (s.kit(kit) / ".kit" / "reel-page.json").write_text(json.dumps(rec), encoding="utf-8")
    case("a reel saved before v27 with Just photos opens as just photos", title_of(page(s, kit, "bts")[1]) == short + " reel" and reel_state(s, kit)["kind"] == "photos")
    rec["saved"]["footage"] = True
    (s.kit(kit) / ".kit" / "reel-page.json").write_text(json.dumps(rec), encoding="utf-8")
    case("...and with footage on, as behind the scenes", title_of(page(s, kit, "photos")[1]) == short + " behind the scenes" and reel_state(s, kit)["kind"] == "bts")
    rec["saved"]["footage"] = None
    (s.kit(kit) / ".kit" / "reel-page.json").write_text(json.dumps(rec), encoding="utf-8")
    case("...and with footage never chosen, the address decides, and with no address the chooser",
         title_of(page(s, kit, "broll")[1]) == short + " B-roll" and reel_state(s, kit)["kind"] is None and title_of(page(s, kit)[1]) == short + " reels")
    out = run(s, "reel_page.py", "show", kit)[1]
    case("reel_page.py show says the kind, in plain words", "Kind: not chosen yet" in out, out[:300])
    save(s, kit, {"kind": "broll", "footage": True, "style": "broll"})
    out = run(s, "reel_page.py", "show", kit)[1]
    case("...and once chosen, which", "Kind: B-roll" in out, out[:300])
    case("reel_page.py open then names the reel's own kind and its address, with the chooser's last",
         "is a B-roll reel: " in run(s, "reel_page.py", "open", kit)[1] and "&kind=broll" in run(s, "reel_page.py", "open", kit)[1])


# ---------- 4. the reels: a new reel from a kind's page, the switch, the chat ----------

def run_version(s):
    import reel_page as rp
    kit = KIT
    code, j = ver(s, kit, op="new", kind="photos")
    rec = reel_rec(s, kit)
    case("a new reel started from a just-photos page is just photos at once: its kind, footage off (hers saved these on the page's next load)",
         code == 200 and j["ok"] and j["current"] == "v2" and rec["saved"]["kind"] == "photos" and rec["saved"]["footage"] is False and rec["saved"]["style"] == "first", (code, j, rec.get("saved")))
    case("...and the answer says the open reel's kind, so the page reopens it as that kind", j.get("kind") == "photos", j)
    case("the first reel is as it was (B-roll), in its own place", rec["versions"][0]["data"]["saved"]["kind"] == "broll")
    code, j = ver(s, kit, op="switch", id="v1")
    case("a switch's answer says the other reel's own kind (hers kept the address's kind and hid the wrong steps)", code == 200 and j.get("kind") == "broll", j)
    st = reel_state(s, kit)
    case("the state's list of reels carries each reel's kind", [(v["id"], v.get("kind")) for v in st["versions"]] == [("v1", "broll"), ("v2", "photos")], st["versions"])
    case("reels_for_kit (the post kit's and the posting queue's) carries it too",
         [(r["id"], r["kind"]) for r in rp.reels_for_kit(s.kit(kit))] == [("v1", "broll"), ("v2", "photos")])
    code, j = ver(s, kit, op="new", kind="broll")
    rec = reel_rec(s, kit)
    case("a new B-roll reel starts with B-roll's one style and footage on", code == 200 and rec["saved"]["kind"] == "broll" and rec["saved"]["style"] == "broll" and rec["saved"]["footage"] is True)
    code, j = ver(s, kit, op="new")
    case("a new reel with no kind (an older page, or the chat without --kind) has none: the page's address decides", code == 200 and j.get("kind") is None and "kind" not in reel_rec(s, kit)["saved"])
    for bad in ({"op": "switch", "id": "v1", "kind": "bts"}, {"op": "new", "kind": "talk"}, {"op": "rename", "id": "v1", "name": "x", "kind": "bts"}, {"op": "new", "kind": 3}):
        case("refused: %s" % json.dumps(bad), ver(s, kit, **bad)[0] == 400)
    code, out = run(s, "reel_page.py", "reels", kit, "--new", "--name", "From the chat", "--kind", "bts")
    rec = reel_rec(s, kit)
    case("reel_page.py reels --new --kind bts: a behind-the-scenes reel from the chat, named in the list with its kind",
         code == 0 and rec["saved"]["kind"] == "bts" and '"From the chat" (behind the scenes) (the one open on the page)' in out, out[-300:])
    case("reel_page.py show names each reel's kind", "(B-roll)" in run(s, "reel_page.py", "show", kit)[1] and "Kind: behind the scenes" in run(s, "reel_page.py", "show", kit)[1])
    ver(s, kit, op="switch", id="v1")


# ---------- 5. new photos on the server (her v27: + Add photos; the numbers stay fixed) ----------

def run_new_photos(s):
    import reel_page as rp
    kit = "2026-10-04 New photos"
    k = s.make_kit(kit, photos=6)
    st = reel_state(s, kit)
    case("(a kit of 6 photos, numbered 1 to 6)", st and st["total"] == 6 and [p["n"] for p in st["photos"]] == [1, 2, 3, 4, 5, 6])
    code, j, _, _ = s.http("POST", "/reel-open", {"kit": kit, "what": "photos"})
    case("+ Add photos: the Photos folder is opened (the test switch) and her line said", code == 200 and j == {"ok": True, "words": her("photos_open")}, (code, j))
    case("refused: a folder the page can't ask for", s.http("POST", "/reel-open", {"kit": kit, "what": "desktop"})[0] == 400)
    # two photos dropped in, one of them still being copied (changed just now, when the page looks)
    (k / "Photos" / "a-first.jpg").write_bytes(wpc.TINY)
    (k / "Photos" / "zz-last.jpg").write_bytes(wpc.TINY)
    old = time.time() - 10
    os.utime(k / "Photos" / "zz-last.jpg", (old, old))
    time.sleep(rp.RELIST_EVERY + 0.2)
    now = time.time()
    os.utime(k / "Photos" / "a-first.jpg", (now, now))
    st = reel_state(s, kit)
    case("a photo still being copied in (changed this moment) holds the list: nothing is numbered yet, so a reel never points at half a file",
         st["total"] == 6, st["total"])
    os.utime(k / "Photos" / "a-first.jpg", (old, old))
    time.sleep(rp.RELIST_EVERY + 0.2)
    st = reel_state(s, kit)
    case("once every new photo has settled, both are on the page's next poll, as 7 and 8",
         st["total"] == 8 and [p["n"] for p in st["photos"]] == [1, 2, 3, 4, 5, 6, 7, 8], [p["n"] for p in st["photos"]])
    rows = json.loads((k / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    case("7 and 8 are the new photos in name order; 1 to 6 are the photos they were (numbers stay fixed, Nicole's v27)",
         [Path(r["file"]).name for r in rows] == ["beach-%03d.jpg" % i for i in range(1, 7)] + ["a-first.jpg", "zz-last.jpg"], [Path(r["file"]).name for r in rows])
    case("...and the list carries what was added", json.loads((k / ".kit" / "sheet.json").read_text(encoding="utf-8")).get("added") == [7, 8])
    case("no contact sheet was drawn for the page's own re-list", not list((k / ".kit").rglob("sheet-*.png")))
    (k / "Photos" / "beach-003.jpg").rename(s.work / "beach-003.jpg")
    time.sleep(rp.RELIST_EVERY + 0.2)
    st = reel_state(s, kit)
    case("a photo taken out of the folder: its number stays unused (3 is gone, nothing moves down)", [p["n"] for p in st["photos"]] == [1, 2, 4, 5, 6, 7, 8], [p["n"] for p in st["photos"]])
    stamp = st["stamp"]
    time.sleep(rp.RELIST_EVERY + 0.2)
    case("with nothing changed, nothing is re-made (the stamp stays)", reel_state(s, kit)["stamp"] == stamp)


# ---------- 6. the songs: the drop-down's words, Listen by request, Remove this song's wiring ----------

def add_songs(s, kit):
    """A song and a screen recording (a pretend one: an audio file under a video's name, its sound already beside
    it and newer, so no sound is ever taken here) in the shoot's Music folder."""
    k = s.kit(kit)
    music = k / "Music"
    music.mkdir(exist_ok=True)
    (music / "Beat one.wav").write_bytes(BEAT60.read_bytes())
    (music / "Rec.mov").write_bytes((FIX / "click-100bpm.m4a").read_bytes())
    (music / "Rec sound.m4a").write_bytes((FIX / "click-100bpm.m4a").read_bytes())
    now = time.time()
    os.utime(music / "Rec.mov", (now - 20, now - 20))
    os.utime(music / "Rec sound.m4a", (now - 10, now - 10))
    os.utime(music / "Beat one.wav", (now - 30, now - 30))
    return music


def songs_of(s, kit):
    return {x["name"]: x for x in s.http("GET", "/reel-songs" + s.q(kit))[1]["songs"]}


def run_songs(s):
    import reel_page as rp
    hers = her_v27()
    if hers is not None:
        text = html.unescape(hers).replace("\\'", "'")
        case("her drop-down's words, both ways: Choose a song…, (screen recording), No song, Listen, Stop, Your song",
             all(x in text for x in (rp.WORDS["song_choose"], rp.WORDS["song_rec_tag"], rp.WORDS["song_none"], "▶ Listen", "❚❚ Stop", 'aria-label="Your song"'))
             and rp.WORDS["listen"] == "▶ Listen" and rp.WORDS["stop"] == "❚❚ Stop" and rp.WORDS["song_aria"] == "Your song")
        case("her markup for it: the select, Listen, Remove this song and the player, in her order, the old rows gone",
             re.search(r"<div class='songpick' id='songPick'><select id='songSel' aria-label='Your song'></select><button class='btn small' id='songPlay' type='button' hidden>▶ Listen</button>"
                       r"<button class='linkbtn' id='songRm' type='button' hidden title='Take this song off the list'>Remove this song</button><audio id='songAudio' preload='none'></audio></div>", rp.page_html(KIT, "x", True, "photos"))
             and "id='songs'" not in rp.page_html(KIT, "x", True, "photos"))
    kit = "2026-10-06 Songs"
    s.make_kit(kit, photos=6)
    music = add_songs(s, kit)
    songs = songs_of(s, kit)
    case("(set up: a song and a recording in the Music folder, the recording's sound beside it)", set(songs) == {"Beat one", "Rec"} and songs["Rec"]["kind"] == "video", list(songs))
    q = s.q(kit)
    code, j, raw, h = s.http("GET", "/reel-song" + q + "&id=" + songs["Beat one"]["id"], headers={"Range": "bytes=0-99"})
    case("Listen: GET /reel-song answers a Range with 206, the piece, its place and the song's own kind (audio/wav)",
         code == 206 and len(raw) == 100 and h.get("Content-Range", "").startswith("bytes 0-99/") and h.get("Content-Type") == "audio/wav" and raw == BEAT60.read_bytes()[:100], (code, h))
    code, j, raw, h = s.http("GET", "/reel-song" + q + "&id=" + songs["Beat one"]["id"])
    case("...and the whole song with no Range (200), in pieces when asked (Accept-Ranges)", code == 200 and raw == BEAT60.read_bytes() and h.get("Accept-Ranges") == "bytes", (code, len(raw)))
    code, j, raw, h = s.http("GET", "/reel-song" + q + "&id=" + songs["Rec"]["id"], headers={"Range": "bytes=0-9"})
    case("a screen recording plays its sound (made once, beside it), as audio/mp4", code == 206 and raw == (FIX / "click-100bpm.m4a").read_bytes()[:10] and h.get("Content-Type") == "audio/mp4", (code, h))
    case("404 for an id that isn't one of the shoot's songs, and for anything but an id", s.http("GET", "/reel-song" + q + "&id=0123456789ab")[0] == 404
         and s.http("GET", "/reel-song" + q + "&id=../Music/Beat%20one.wav")[0] == 404 and s.http("GET", "/reel-song" + q)[0] == 404)
    case("403 for another website, 404 for a shoot named by a path", s.http("GET", "/reel-song" + q + "&id=" + songs["Beat one"]["id"], headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
         and s.http("GET", "/reel-song?kit=" + quote(str(s.kit(kit)), safe="") + "&id=" + songs["Beat one"]["id"])[0] == 404)
    case("no song was written or changed by listening", sorted(os.listdir(music)) == ["Beat one.wav", "Rec sound.m4a", "Rec.mov"])
    # the page's Remove posts {kit, song} to Lane E's route: through it once, into the tests' own Trash folder
    code, j = save(s, kit, {"song": songs["Beat one"]["id"]})
    case("(set up: Beat one picked for the reel)", code == 200, j)
    code, j, _, _ = s.http("POST", "/reel-song-remove", {"kit": kit, "song": songs["Beat one"]["id"]})
    case("Remove this song, by request as the page sends it: the song is in the (tests') Trash, her line, the list without it, the pick cleared",
         code == 200 and j.get("ok") and j.get("words") == her("song_trashed") and [x["name"] for x in j.get("songs", [])] == ["Rec"] and j.get("cleared") is True
         and not (music / "Beat one.wav").exists() and (Path(s.env["STUDIO_TRASH_FOR_TESTS"]) / "Beat one.wav").exists()
         and (reel_rec(s, kit) or {}).get("saved", {}).get("song") is None, (code, j))
    case("the state says it: no song picked, one song left", reel_state(s, kit)["saved"]["song"] is None and [x["name"] for x in reel_state(s, kit)["songs"]] == ["Rec"])
    case("reel_page.py show lists the songs with their ids", "Songs in the shoot: Rec (a screen recording, Music, id %s)" % songs["Rec"]["id"] in run(s, "reel_page.py", "show", kit)[1])


def run_songs_page(c, s):
    import reel_page as rp
    kit = "2026-10-07 Songs on the page"
    s.make_kit(kit, photos=6)
    music = add_songs(s, kit)
    songs = songs_of(s, kit)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#songSel option').length === 4", 20)
    opts = c.js("Array.from(document.getElementById('songSel').options).map(function(o){ return [o.textContent, o.value === '' ? 'none' : o.value === '__' ? 'choose' : 'song', o.disabled, o.selected]; })")
    case("her drop-down: Choose a song… (disabled, selected), the songs newest first with (screen recording) on a recording, No song last",
         opts == [["Choose a song…", "choose", True, True], ["Rec (screen recording)", "song", False, False], ["Beat one", "song", False, False], ["No song, I'll add music in Instagram", "none", False, False]], opts)
    case("Listen and Remove this song wait until a song is picked", c.js("document.getElementById('songPlay').hidden && document.getElementById('songRm').hidden"))
    c.set_value("#songSel", songs["Beat one"]["id"])
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("song") == songs["Beat one"]["id"], 8, what="the song saved")
    case("a song picked from the drop-down is saved by its id; Choose a song… goes; Listen and Remove show; the bar names it",
         c.js("document.getElementById('songSel').options[0].value !== '__'")
         and not c.js("document.getElementById('songPlay').hidden") and not c.js("document.getElementById('songRm').hidden") and "Beat one" in c.text("#sum"), c.text("#sum"))
    c.click("#songPlay")
    c.wait_for("document.getElementById('songAudio').getAttribute('src') !== null", 5)
    src = c.js("document.getElementById('songAudio').getAttribute('src')")
    case("Listen plays the song from GET /reel-song by its id, never a path", src == "/reel-song?kit=" + quote(kit, safe="") + "&id=" + songs["Beat one"]["id"], src)
    # the player asks a moment after the tap and the answer comes a moment after that: wait for both (a slow
    # computer shows the ask before its answer), then check every answer as before
    def song_asks():
        return [r for r in list(c.requests) if "/reel-song?" in r["url"]]

    def song_answered():
        gone = set(f["url"] for f in list(c.failed))
        asks = song_asks()
        return bool(asks) and all(r["status"] is not None or r["url"] in gone for r in asks)
    try:
        chrome_drive.wait_until(song_asks, 10, what="the player's request for the song")
        chrome_drive.wait_until(song_answered, 30, what="the answer to the player's request for the song")
    except chrome_drive.Timeout:
        pass                                        # none seen is the SKIP below; one never answered fails the check below
    got = [(r["url"].split("id=")[-1], r["status"]) for r in song_asks()]
    if got:
        case("...the player asked for it, in pieces (206) or whole (200)", all(st_ in (200, 206) for _, st_ in got), got)
    else:
        t.skip("the player's own request for the song: the hidden Chrome made none that could be seen (the route is proven by request above)")
    played = c.js("!document.getElementById('songAudio').paused || document.getElementById('songPlay').textContent === '❚❚ Stop'")
    case("...and says ❚❚ Stop while it plays (a hidden Chrome may not play sound: then SKIP)", True if not played else played)
    if not played:
        t.skip("the song playing in a hidden Chrome: it did not start, so Stop was not seen")
    else:
        c.click("#songPlay")
        case("Stop stops it and says ▶ Listen again", c.js("document.getElementById('songAudio').paused && document.getElementById('songPlay').textContent === '▶ Listen'"))
    # Remove this song: two taps (hers), the first alone goes back after a moment
    c.click("#songRm")
    case("the first tap only asks: Move it to the Trash?", c.text("#songRm") == "Move it to the Trash?" and c.js("document.getElementById('songRm').classList.contains('sure')"))
    c.wait_for("document.getElementById('songRm').textContent === 'Remove this song'", 6)
    case("...and left alone it goes back to Remove this song (hers: 4 s), with the song still there", (music / "Beat one.wav").exists())
    c.click("#songRm")
    c.click("#songRm")
    c.wait_for("document.getElementById('waiting').textContent === %s" % json.dumps(her("song_trashed")), 10)
    case("the second tap moves it: her line on the page, the song out of the drop-down, Choose a song… back, Listen and Remove hidden",
         c.text("#waiting") == her("song_trashed") and "Beat one" not in c.js("Array.from(document.getElementById('songSel').options).map(function(o){ return o.textContent; }).join('|')")
         and c.js("document.getElementById('songSel').options[0].value === '__'") and c.js("document.getElementById('songPlay').hidden && document.getElementById('songRm').hidden"))
    case("the song is in the (tests') Trash, not deleted, and the reel's pick is cleared", not (music / "Beat one.wav").exists() and (Path(s.env["STUDIO_TRASH_FOR_TESTS"]) / "Beat one.wav").exists()
         and (reel_rec(s, kit) or {}).get("saved", {}).get("song") is None)
    c.js("window.Reel.followNow()")
    time.sleep(1.0)
    case("the page carries on in step with the Assistant's record (no 'changed somewhere else' line)", c.text("#notice") == "" and "no song picked yet" in c.text("#sum"), (c.text("#notice"), c.text("#sum")))
    case("no fault on the page", not c.page_errors(), c.page_errors()[:3])


# ---------- 7. Add this reel to my posting queue (her v27) ----------

HER_Q = {"toq_btn": "Add this reel to my posting queue", "toq_result": "Add it to my posting queue", "q_adding": "Adding it…",
         "q_how": "How often do you want to post?", "q_how_b": " I'll give each post a date.", "q_open": "Open my posting queue",
         "q_done": "In your posting queue ✓", "q_cant": "I couldn't add it. Try again in a moment."}
RHYTHMS = ("Every day", "Every other day", "3 a week", "Twice a week", "Once a week")


def mark_made(s, kit, vid, project):
    """A reel made on the reel page: its "made" entry, marked with which reel (as reel_page.py writes it)."""
    f = s.kit(kit) / ".kit" / "reel-page.json"
    rec = reel_rec(s, kit) or {"v": 1, "rev": 0}
    rec.setdefault("made", []).append({"project": project, "picks": "1,2", "vibe": "beat", "footage": None, "version": vid, "when": time.time()})
    rec["rev"] = int(rec.get("rev") or 0) + 1
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")


def run_queue(s):
    import reel_page as rp
    hers = her_v27()
    if hers is not None:
        text = html.unescape(hers).replace("\\'", "'")
        case("her words for the queue button, both ways: the two buttons, Adding it…, the rhythm question, Open my posting queue, the done button, her sorry line",
             all(v in text for v in HER_Q.values()) and all(rp.WORDS[k] == v for k, v in HER_Q.items())
             and "It's in your posting queue: " in text and ", going out " in text and ". Write its caption in your post kit whenever you're ready." in text
             and "It's already in your posting queue" in text and ", set for " in text
             and rp.WORDS["q_in"] == "It's in your posting queue: {label}{going}. Write its caption in your post kit whenever you're ready." and rp.WORDS["q_going"] == ", going out {day}"
             and rp.WORDS["q_already"] == "It's already in your posting queue{set}." and rp.WORDS["q_set"] == ", set for {day}")
        case("her five chips are the words page's (one copy), and hers", tuple(rp._rhythms()) == RHYTHMS and all("'%s'" % r in hers for r in RHYTHMS))
        case("her bar under Your reels and the button in the box after a make, as her page has them",
             '<div class="toq" id="toqBar" hidden><button class="btn" id="toQueue2">Add this reel to my posting queue</button>' in hers
             and '<button class="btn" id="toQueue">Add it to my posting queue</button>' in hers
             and "<div class='toq' id='toqBar' hidden><button class='btn' id='toQueue2' type='button'>Add this reel to my posting queue</button>" in rp.page_html(KIT, "x", True, "photos"))
    kit = "2026-10-08 Queue"
    s.make_kit(kit, photos=6)
    st = reel_state(s, kit)
    case("the state carries each reel's place in the posting queue and whether it is made: nothing made, no rhythm set",
         st["made"] == {"v1": False} and st["queue"] == {"interval": False, "reels": {"v1": {"status": "", "date": ""}}, "url": "/posting.html"}, (st.get("made"), st.get("queue")))
    code, j, _, _ = s.http("POST", "/words-queue", {"kit": kit, "piece": "reel", "reel": "v1"})
    case("a reel that isn't made can't be added (the words page's own rule)", code == 409 and not j.get("ok"), (code, j))
    mark_made(s, kit, "v1", "Queue reel")
    st = reel_state(s, kit)
    case("once the reel is made (a 'made' entry of its own), the state says so", st["made"] == {"v1": True})
    code, j, _, _ = s.http("POST", "/words-rhythm", {"text": "Twice a week"})
    case("the rhythm set once with her chip (POST /words-rhythm, the words page's route)", code == 200 and j.get("ok"), (code, j))
    code, j, _, _ = s.http("POST", "/words-queue", {"kit": kit, "piece": "reel", "reel": "v1"})
    case("the add posts the version to the words page's queue route: ready, with a date", code == 200 and j.get("ok") and j["queue"]["status"] == "green" and j["queue"]["date"], (code, j))
    st = reel_state(s, kit)
    case("...and the state says it: in the queue, dated, the rhythm set", st["queue"]["interval"] is True and st["queue"]["reels"]["v1"]["status"] == "green" and st["queue"]["reels"]["v1"]["date"] == j["queue"]["date"])
    case("refused: the add from another website", s.http("POST", "/words-queue", {"kit": kit, "piece": "reel", "reel": "v1"}, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
    # two reels: two pieces
    ver(s, kit, op="new", kind="photos")
    mark_made(s, kit, "v2", "Queue reel 2")
    code, j, _, _ = s.http("POST", "/words-queue", {"kit": kit, "piece": "reel", "reel": "v2"})
    import posting_queue as pq
    pieces = pq.kit_reel_pieces(pq.load(), s.kit(kit))
    case("a second reel, made and added, is its own piece in the queue (posting_queue.reel_version), the first's untouched",
         code == 200 and set(pieces) == {"v1", "v2"} and pieces["v1"]["status"] == "green" and pieces["v2"]["status"] == "green", (code, sorted(pieces)))
    st = reel_state(s, kit)
    case("the state carries both", st["queue"]["reels"]["v1"]["status"] == "green" and st["queue"]["reels"]["v2"]["status"] == "green" and st["made"] == {"v1": True, "v2": True})
    case("reel_page.py show says which reels are in the posting queue", 'In the posting queue: "Reel 1", "Reel 2"' in run(s, "reel_page.py", "show", kit)[1], run(s, "reel_page.py", "show", kit)[1][-400:])
    case("reels_for_kit's 'made' goes by the same rule (made_projects): both made", [r["made"] for r in rp.reels_for_kit(s.kit(kit))] == [True, True])


def run_queue_page(c, s):
    import reel_page as rp
    import posting_queue as pq
    kit = "2026-10-09 Queue on the page"
    s.make_kit(kit, photos=6)
    # the rhythm is not set yet for this run: the queue file is this test's own, so take it out
    p = pq.load()
    p.pop("interval", None)
    pq.save(p)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    case("the bar under Your reels is hidden until the reel is made (hers)", c.js("document.getElementById('toqBar').hidden") is True)
    mark_made(s, kit, "v1", "Page queue reel")
    c.js("window.Reel.followNow()")
    c.wait_for("!document.getElementById('toqBar').hidden", 10)
    case("once the reel is made it shows: her button, under Your reels", c.text("#toQueue2") == HER_Q["toq_btn"]
         and c.js("document.getElementById('toqBar').previousElementSibling.id") == "reels")
    c.click("#toQueue2")
    c.wait_for("document.querySelectorAll('#qAsk2 [data-iv]').length === 5", 10)
    case("no rhythm set yet: the page asks once, in her words, with her five chips", c.js("document.querySelector('#qAsk2 b').textContent") == HER_Q["q_how"]
         and c.js("document.querySelector('#qAsk2 p').textContent") == HER_Q["q_how"] + HER_Q["q_how_b"]
         and c.js("Array.from(document.querySelectorAll('#qAsk2 [data-iv]')).map(function(b){ return b.textContent; })") == list(RHYTHMS))
    c.click("#qAsk2 [data-iv='3 a week']")
    c.wait_for("document.getElementById('toQueue2').textContent === %s" % json.dumps(HER_Q["q_done"]), 15)
    went = c.text("#went2")
    piece = pq.kit_reel_pieces(pq.load(), s.kit(kit)).get("v1") or {}
    case("a chip pressed: the rhythm is set and the reel goes straight in, once: her line with the shoot's reel and its day, and Open my posting queue",
         went.startswith("It's in your posting queue: Queue on the page reel, going out ") and went.endswith(". Write its caption in your post kit whenever you're ready. Open my posting queue")
         and piece.get("status") == "green" and bool(piece.get("date")) and c.js("document.querySelector('#went2 a').getAttribute('href')") == "/posting.html", (went, piece.get("status")))
    case("...asked once and added once (one piece, no second ask)", c.js("document.querySelectorAll('#qAsk2 [data-iv]').length") == 0 and len(pq.kit_reel_pieces(pq.load(), s.kit(kit))) == 1)
    c.click("#toQueue2")
    c.wait_for("document.getElementById('went2').textContent.indexOf('already') > 0", 10)
    case("a second press says her 'already' line, with its day, and writes nothing", c.text("#went2").startswith("It's already in your posting queue, set for ") and len(pq.kit_reel_pieces(pq.load(), s.kit(kit))) == 1)
    # a second reel: the label names the reel, and it is its own piece
    c.click("#verNew")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v2'", 20)
    case("a new reel, not made: the bar is hidden again", c.js("document.getElementById('toqBar').hidden") is True)
    mark_made(s, kit, "v2", "Page queue reel 2")
    c.js("window.Reel.followNow()")
    c.wait_for("!document.getElementById('toqBar').hidden", 10)
    c.click("#toQueue2")
    c.wait_for("document.getElementById('toQueue2').textContent === %s" % json.dumps(HER_Q["q_done"]), 15)
    case("with several reels her line names the reel: '<shoot> · Reel 2', and it is a second piece in the queue",
         c.text("#went2").startswith("It's in your posting queue: Queue on the page · Reel 2, going out ") and set(pq.kit_reel_pieces(pq.load(), s.kit(kit))) == {"v1", "v2"}, c.text("#went2"))
    # the button in the box after a make: the page follows a job at work (reloaded while one runs, as
    # reel_page_check does it) and draws her box when it is done, with Add it to my posting queue beside Open CapCut
    import fcntl
    ver(s, kit, op="new", kind="photos")
    mark_made(s, kit, "v3", "Page queue reel 3")
    jl = s.kit(kit) / ".kit" / "reel-job.json"
    held = open(s.kit(kit) / ".kit" / "reel-job.lock", "a")
    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        jl.write_text(json.dumps({"id": "d" * 12, "state": "running", "t": time.time(), "pid": os.getpid(), "dry": False}), encoding="utf-8")
        c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
        c.wait_for("!!document.querySelector('#makeBtn .spin')", 15)
        jl.write_text(json.dumps({"id": "d" * 12, "state": "done", "t": time.time(), "dry": False, "project": "Page queue reel 3",
                                  "words": ["Plan: 2 photos, 4.0 seconds, every cut on the beat"]}), encoding="utf-8")
    finally:
        fcntl.flock(held, fcntl.LOCK_UN)
        held.close()
    c.wait_for("!!document.getElementById('toQueue')", 15)
    case("the box after a make: her Add it to my posting queue beside Open CapCut, and the bar under Your reels shows too",
         c.text("#toQueue") == HER_Q["toq_result"] and c.text("#capcut") == "Open CapCut" and not c.js("document.getElementById('toqBar').hidden"))
    c.click("#toQueue")
    c.wait_for("document.getElementById('toQueue').textContent === %s" % json.dumps(HER_Q["q_done"]), 15)
    case("pressed there, the reel goes in, her line under the box, three pieces now",
         c.text("#went").startswith("It's in your posting queue: Queue on the page · Reel 3, going out ") and set(pq.kit_reel_pieces(pq.load(), s.kit(kit))) == {"v1", "v2", "v3"}, c.text("#went"))
    case("no fault on the page", not c.page_errors(), c.page_errors()[:3])


# ---------- 8. the page, in a hidden Chrome ----------

def nums(c):
    return c.js("Array.from(document.querySelectorAll('section.step')).filter(function(s){ return !s.hidden; }).map(function(s){ return s.id + '=' + s.querySelector('.num').textContent; })")


def run_page(c, s):
    import reel_page as rp
    kit = "2026-10-05 On the page"
    short = kit[11:]
    k = s.make_kit(kit, photos=6)
    c.open(s.url("/reel.html" + s.q(kit)))
    c.wait_for("document.querySelectorAll('.kind').length === 4", 20)
    case("the chooser in a browser: her title with the coral full stop, her four cards side by side",
         c.text("#title") == short + " reels." and c.js("document.querySelectorAll('.kind').length") == 4
         and c.js("(function(){ var r = Array.from(document.querySelectorAll('.kind')).map(function(x){ return Math.round(x.getBoundingClientRect().top); }); return r.every(function(y){ return y === r[0]; }); })()"))
    c.click("#kPhotos")
    c.wait_for("window.Reel && window.Reel.state()", 20)
    case("Just photos opens the just-photos page: her title, her steps numbered 1 to 5 (the photos, the song, the direct note, the vibe, the watch step)",
         c.text("#title") == short + " reel." and nums(c) == ["step1=1", "step3=2", "stepDirect=3", "step4=4", "watch=5"], nums(c))
    case("the footage step and the style are not on it", c.js("document.getElementById('step0').hidden && document.getElementById('stepStyle').hidden"))
    case("her path at the top in the bar: Home › <shoot> post kit › Reels › Just photos, Reels a link back to the chooser; the Back pill and the chooser link hidden",
         c.text(".crumbs") == "Home›%s post kit›Reels›Just photos" % short and c.js("document.querySelector('.crumbs a[href=\"/reel.html?kit=%s\"]').textContent" % quote(kit)) == "Reels"
         and c.js("getComputedStyle(document.getElementById('back')).display === 'none' && getComputedStyle(document.getElementById('allReels')).display === 'none'"), c.text(".crumbs"))
    time.sleep(1.2)
    case("a plain open saved nothing", reel_rec(s, kit) is None)
    c.click("#all .pick")
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("kind") == "photos", 8, what="the first save")
    case("the first change saves the kind with the reel (saved.kind: photos, footage off)", reel_rec(s, kit)["saved"]["kind"] == "photos" and reel_rec(s, kit)["saved"]["footage"] is False)
    # a new reel from this page is this kind; then a switch to a reel of another kind lands on its own page
    c.click("#verNew")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v2'", 20)
    case("+ Start a new reel from a just-photos page: the new reel is just photos, on the same kind of page",
         reel_rec(s, kit)["saved"]["kind"] == "photos" and c.js("location.search").endswith("kind=photos") and nums(c) == ["step1=1", "step3=2", "stepDirect=3", "step4=4", "watch=5"])
    ver(s, kit, op="new", kind="bts")
    c.js("window.Reel.followNow()")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v3' && location.search.indexOf('kind=bts') > 0", 20)
    case("a behind-the-scenes reel started in another window (or from the chat): this page reopens it as its own kind, her title, her seven steps (ours)",
         c.text("#title") == short + " behind the scenes." and nums(c) == ["step0=1", "step1=2", "step3=3", "stepDirect=4", "stepStyle=5", "step4=6", "watch=7"], (c.text("#title"), nums(c)))
    case("step 1 on it: her heading, Add my footage, the ask box with her new label before the line to copy, no feel row, no yes/no cards",
         c.text("#step0 h2") == "1Choose your behind-the-scenes footage" and c.js("!document.getElementById('btsBox').hidden")
         and c.js("document.querySelector('#btsBox label b').textContent") == "Is there anything specific you'd like the Assistant to look for?"
         and c.js("document.getElementById('askIn').getBoundingClientRect().top < document.getElementById('pasteWords').getBoundingClientRect().top")
         and c.js("document.getElementById('feelRow').hidden") and c.count("#modeBts") == 0, c.text("#step0 h2"))
    case("the recommended tag shows on Let the Assistant choose only here (behind the scenes)", c.js("!document.getElementById('claudeRec').hidden"))
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1' && location.search.indexOf('kind=photos') > 0", 20)
    case("switching under Your reels back to the first (just photos) lands on its own kind (hers kept the address's kind), with no recommended tag",
         nums(c) == ["step1=1", "step3=2", "stepDirect=3", "step4=4", "watch=5"] and c.js("document.getElementById('claudeRec').hidden"))
    # B-roll's page
    ver(s, kit, op="new", kind="broll")
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    case("a B-roll reel opened from a just-photos address shows as B-roll: her title, the footage then the song, then the watch step, nothing else",
         c.text("#title") == short + " B-roll." and nums(c) == ["step0=1", "step3=2", "watch=3"], nums(c))
    case("the bar at the bottom still works on it (no clips to count: Make my reel waits)", c.js("document.getElementById('makeBtn').disabled") is True)
    case("no fault on the page", not c.page_errors(), c.page_errors()[:3])
    # + Add photos and Show my new photos, on the just-photos reel
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1' && document.querySelectorAll('#all .pick').length === 6", 20)
    c.click("#addPhotos")
    c.wait_for("document.getElementById('addPhotosSay').textContent === %s" % json.dumps(her("photos_open")), 8)
    case("+ Add photos: her line once the folder is open", c.text("#addPhotosSay") == her("photos_open"))
    c.js("document.getElementById('allBox').open = true")
    c.click("#all .pick", nth=4)
    chrome_drive.wait_until(lambda: [x["n"] for x in ((reel_rec(s, kit) or {}).get("saved") or {}).get("picks", [])] == [1, 5], 8, what="the order saved")
    (k / "Photos" / "new-one.jpg").write_bytes(wpc.TINY)
    old = time.time() - 10
    os.utime(k / "Photos" / "new-one.jpg", (old, old))
    c.wait_for("document.getElementById('showNew') !== null", rp.RELIST_EVERY * 2 + 6)
    case("a photo dropped into the Photos folder: \"1 new photo in.\" and her Show my new photos, within a few seconds",
         c.text("#addPhotosSay").startswith("1 new photo in.") and c.text("#showNew") == "Show my new photos", c.text("#addPhotosSay"))
    case("the page keeps working meanwhile: their order of 1 and 5 is still on the screen, no reload line", c.js("Array.from(document.querySelectorAll('#reel .tile')).map(function(x){ return +x.dataset.n; })") == [1, 5]
         and c.text("#notice") == "")
    c.click("#reel .tile:nth-child(2) .lng")
    chrome_drive.wait_until(lambda: [(x["n"], x.get("h")) for x in ((reel_rec(s, kit) or {}).get("saved") or {}).get("picks", [])] == [(1, ""), (5, "+")], 8, what="a save after the new photo")
    case("...and a change made now still saves (every photo they know kept its number)", True)
    c.click("#showNew")
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#all .pick').length === 7", 20)
    case("Show my new photos reloads: 7 photos below, the new one last as number 7, their order as it was",
         c.js("Array.from(document.querySelectorAll('#all .pick')).map(function(x){ return +x.dataset.n; })") == [1, 2, 3, 4, 5, 6, 7]
         and c.js("Array.from(document.querySelectorAll('#reel .tile')).map(function(x){ return +x.dataset.n; })") == [1, 5])
    stuck = c.js("(function(){ var el = document.getElementById('reelStick'); return [getComputedStyle(el).position, getComputedStyle(el).top]; })()")
    case("the order sits in her sticky box (position: sticky at the top)", stuck == ["sticky", "0px"], stuck)
    case("no fault on the page", not c.page_errors(), c.page_errors()[:3])
    c.phone(375, 800)
    c.open(s.url("/reel.html" + s.q(kit)))
    c.wait_for("document.querySelectorAll('.kind').length === 4", 20)
    case("at a phone's width the chooser's cards stack and nothing scrolls sideways",
         c.js("document.documentElement.scrollWidth <= 375 && document.querySelectorAll('.kind')[3].getBoundingClientRect().top > document.querySelectorAll('.kind')[0].getBoundingClientRect().bottom"))
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    ph = c.js("[getComputedStyle(document.getElementById('reelStick')).position, document.documentElement.scrollWidth, window.innerWidth, Array.from(document.querySelectorAll('.bar a, .toq, .songpick, .addph')).map(function(x){ return [x.id || x.className, Math.round(x.getBoundingClientRect().right)]; })]")
    case("...and on a phone the order does not stick (it would cover the page): ours, and nothing scrolls sideways", ph[0] == "static" and ph[1] <= ph[2], ph)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=bts"))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    wide = c.js("[document.documentElement.scrollWidth, window.innerWidth, Array.from(document.querySelectorAll('body *')).filter(function(x){ return x.getBoundingClientRect().right > window.innerWidth + 1; }).slice(0, 6).map(function(x){ return x.tagName + '#' + x.id + '.' + x.className; })]")
    case("a behind-the-scenes page at a phone's width: the two pills in the bar wrap, nothing sticks out", wide[0] <= wide[1] and not wide[2], wide)
    c.desktop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8790, 8791, 8792, 8799) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="reel-v27-page-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"       # no folder window, no picker, no CapCut, whatever a test presses
    s.env["STUDIO_CARD_FOR_TESTS"] = "none"
    s.env["STUDIO_TRASH_FOR_TESTS"] = str(work / "trash")   # never the real Trash
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    s.make()
    (work / "trash").mkdir(exist_ok=True)
    sys.path.insert(0, str(SCRIPTS))
    try:
        import posts  # noqa: E402   (the one place a shoot's name becomes its kit folder's name)
        made = posts.clean_name("Kinds <b>& 'reels' 🎞 \\ / : * ? \" | .")
        case("a shoot named with a tag and the other characters a PC refuses gets a kit folder a PC can make (they become a space; the rest is kept)",
             made == "Kinds b & 'reels' 🎞", made)
        s.make_kit(KIT, photos=8)
        group("her words: the chooser, the kinds, step 1 and 2's new lines", run_words, s)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("the chooser", run_chooser, s)
        group("the kinds, each its own page", run_kinds, s)
        group("the reels: a new reel's kind, the switch, the chat", run_version, s)
        group("new photos on the server: numbers stay fixed", run_new_photos, s)
        group("the songs: the drop-down's words, Listen by request, Remove this song's wiring", run_songs, s)
        group("Add this reel to my posting queue, by request", run_queue, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1100)) as c:
                group("the chooser, the kinds, + Add photos and Show my new photos, on the page", run_page, c, s)
                group("the song drop-down, Listen and Remove this song, on the page", run_songs_page, c, s)
                group("Add this reel to my posting queue, on the page", run_queue_page, c, s)
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
