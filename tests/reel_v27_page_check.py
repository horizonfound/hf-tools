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
KIT = "2026-10-03 Kinds <b>& 'reels' 🎞"
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


def her_v27(name="pages/reel-maker.html"):
    """A file of her v27 handoff (her reel page, or UPDATE-v27.md), or None when it isn't on this computer."""
    for base in (ROOT, ROOT.parent / "hf-tools", Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v27-*")):
            f = h / "Carousel designer and reel picker" / name
            if f.is_file():
                return f.read_text(encoding="utf-8")
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
    return [(m.group(1), bool(m.group(2))) for m in re.finditer(r"<section class='step' id='(\w+)'(?:( hidden data-kind-hidden='1')| hidden)?>", pg)]


# ---------- 1. her words ----------

def run_words(s):
    import reel_page as rp
    hers = her_v27()
    case("the chooser's words are in their own table (reel_page.KIND_WORDS), and the three kinds are hers", set(rp.KINDS) == set(KINDS)
         and all(k in rp.KIND_WORDS for k in ("chooser_h2", "chooser_say", "chooser_lede", "all_reels")) and len(rp.KIND_WORDS) == 19)
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
    case("her lines for the Photos folder: opening, open, could not open", all(x in text for x in (rp.WORDS["opening_photos"], rp.WORDS["photos_open"], rp.WORDS["cant_open_photos"])))
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
    cards = re.findall(r"<a class='kind' id='(\w+)' href='([^']*)'><b>(.*?)</b><span>(.*?)</span></a>", pg)
    case("her four cards, in her order, with her words, each a plain link written on the server",
         [(a, html.unescape(c), html.unescape(d)) for a, _b, c, d in cards] == HER_KINDS, cards)
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
    want = {"bts": [("step0", False), ("step1", False), ("step3", False), ("stepStyle", False), ("step4", False)],
            "photos": [("step0", True), ("step1", False), ("step3", False), ("stepStyle", True), ("step4", False)],
            "broll": [("step0", False), ("step1", True), ("step3", False), ("stepStyle", True), ("step4", True)]}
    for kind in KINDS:
        before = kit_bytes(s, kit)
        code, pg = page(s, kit, kind)
        case("%s: her title and her lede, written on the server" % kind, code == 200 and title_of(pg) == short + " " + TITLES[kind] and lede_of(pg) == rp.KIND_WORDS["lede_" + kind], (title_of(pg), lede_of(pg)[:50]))
        case("%s: the steps a %s reel doesn't use are hidden (hers: just photos hides the footage; B-roll hides the photos, the style, the vibe)" % (kind, TITLES[kind]),
             shown_steps(pg) == want[kind], shown_steps(pg))
        case("%s: her link back to the chooser in the bar, and the kit's link beside it" % kind,
             "id='allReels' href='/reel.html?kit=%s'>%s</a>" % (quote(kit), html.escape(rp.KIND_WORDS["all_reels"])) in pg and "id='back' href='/content/" in pg)
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
    case("+ Add photos: the Photos folder is opened (the test switch) and her line said", code == 200 and j == {"ok": True, "words": rp.WORDS["photos_open"]}, (code, j))
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


# ---------- 6. the page, in a hidden Chrome ----------

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
    case("Just photos opens the just-photos page: her title, her steps numbered 1 to 3 (the photos, the song, the vibe)",
         c.text("#title") == short + " reel." and nums(c) == ["step1=1", "step3=2", "step4=3"], nums(c))
    case("the footage step and the style are not on it", c.js("document.getElementById('step0').hidden && document.getElementById('stepStyle').hidden"))
    case("her link back to the chooser in the bar", c.text("#allReels") == rp.KIND_WORDS["all_reels"] and c.js("document.getElementById('allReels').getAttribute('href')") == "/reel.html?kit=" + quote(kit))
    time.sleep(1.2)
    case("a plain open saved nothing", reel_rec(s, kit) is None)
    c.click("#all .pick")
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("kind") == "photos", 8, what="the first save")
    case("the first change saves the kind with the reel (saved.kind: photos, footage off)", reel_rec(s, kit)["saved"]["kind"] == "photos" and reel_rec(s, kit)["saved"]["footage"] is False)
    # a new reel from this page is this kind; then a switch to a reel of another kind lands on its own page
    c.click("#verNew")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v2'", 20)
    case("+ Start a new reel from a just-photos page: the new reel is just photos, on the same kind of page",
         reel_rec(s, kit)["saved"]["kind"] == "photos" and c.js("location.search").endswith("kind=photos") and nums(c) == ["step1=1", "step3=2", "step4=3"])
    ver(s, kit, op="new", kind="bts")
    c.js("window.Reel.followNow()")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v3' && location.search.indexOf('kind=bts') > 0", 20)
    case("a behind-the-scenes reel started in another window (or from the chat): this page reopens it as its own kind, her title, her five steps (ours)",
         c.text("#title") == short + " behind the scenes." and nums(c) == ["step0=1", "step1=2", "step3=3", "stepStyle=4", "step4=5"], (c.text("#title"), nums(c)))
    case("step 1 on it: her heading, Add my footage, the ask box with her new label before the line to copy, no feel row, no yes/no cards",
         c.text("#step0 h2") == "1Choose your behind-the-scenes footage" and c.js("!document.getElementById('btsBox').hidden")
         and c.js("document.querySelector('#btsBox label b').textContent") == "Is there anything specific you'd like your assistant to look for?"
         and c.js("document.getElementById('askIn').getBoundingClientRect().top < document.getElementById('pasteWords').getBoundingClientRect().top")
         and c.js("document.getElementById('feelRow').hidden") and c.count("#modeBts") == 0, c.text("#step0 h2"))
    case("the recommended tag shows on Let my assistant choose only here (behind the scenes)", c.js("!document.getElementById('claudeRec').hidden"))
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1' && location.search.indexOf('kind=photos') > 0", 20)
    case("switching under Your reels back to the first (just photos) lands on its own kind (hers kept the address's kind), with no recommended tag",
         nums(c) == ["step1=1", "step3=2", "step4=3"] and c.js("document.getElementById('claudeRec').hidden"))
    # B-roll's page
    ver(s, kit, op="new", kind="broll")
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    case("a B-roll reel opened from a just-photos address shows as B-roll: her title, the footage then the song, nothing else",
         c.text("#title") == short + " B-roll." and nums(c) == ["step0=1", "step3=2"], nums(c))
    case("the bar at the bottom still works on it (no photos to count: Make my reel waits)", c.js("document.getElementById('makeBtn').disabled") is True)
    case("no fault on the page", not c.page_errors(), c.page_errors()[:3])
    # + Add photos and Show my new photos, on the just-photos reel
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1' && document.querySelectorAll('#all .pick').length === 6", 20)
    c.click("#addPhotos")
    c.wait_for("document.getElementById('addPhotosSay').textContent === %s" % json.dumps(rp.WORDS["photos_open"]), 8)
    case("+ Add photos: her line once the folder is open", c.text("#addPhotosSay") == rp.WORDS["photos_open"])
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
        s.make_kit(KIT, photos=8)
        group("her words: the chooser, the kinds, step 1 and 2's new lines", run_words, s)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("the chooser", run_chooser, s)
        group("the kinds, each its own page", run_kinds, s)
        group("the reels: a new reel's kind, the switch, the chat", run_version, s)
        group("new photos on the server: numbers stay fixed", run_new_photos, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1100)) as c:
                group("the chooser, the kinds, + Add photos and Show my new photos, on the page", run_page, c, s)
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
