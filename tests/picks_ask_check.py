#!/usr/bin/env python3
"""The photographer picks (Nicole's handoff v25, section 3 and the last bullet of section 10; stage H of the v26
build): nothing is picked until they ask, the photo note under "Put your photos in order" with its line to copy,
the command the Assistant reads before it picks, and "make my posts" only bringing the photos in.

    python3 tests/picks_ask_check.py                 everything (the page in a hidden Chrome)
    python3 tests/picks_ask_check.py --no-chrome     the checks that need no browser
    python3 tests/guard.py 3000 python3 tests/picks_ask_check.py     as it is run: under the memory guard

What it holds:
  her words     the not-picked line, the note box and the line to copy, against her v25 reel page, both ways;
                the line it replaced is gone
  the note      by request: saved as photo_ask, checked (text, her 600), each reel its own, kept by a save
                that does not send it, never written into another reel
  the command   reel_page.py note: which reel the pick is for, whether it is the one open on the page, the
                note word for word, the command that saves for that reel only; it changes nothing; a name that
                fits no reel stops; reel_page.py show and kit.py picks print the note too
  a new kit     kit.py start and kit.py sheet (what "make my posts" runs after the photos are in) pick nothing
                and make nothing: no picks, no pieces, the reel page on "I'll drag them in myself"
  the page      in a hidden Chrome: her line under Let my assistant choose, the box where she has it, the line
                to copy with the reel's name only with several reels and "and follow my note" only with a
                note, saved as they type, Copy, each reel its own note, names as text, a phone's width

Nothing here touches the real ~/.studio, a real kit, CapCut or a visible window: a scratch home and pretend kits.
Python 3.9, standard library only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import talking_page_check as t  # noqa: E402   (its Setup: a scratch home, pretend kits, the page server)

SCRIPTS = t.SCRIPTS
PORT = 9880
KIT = "2026-09-23 Zoë & the 'boys' 🌊" if t.WINDOWS else "2026-09-23 Zoë <b>& the 'boys' 🌊"
NEW_KIT = "2026-09-26 Brought in"
PAGE = "abcdefgh12"
NOT_PICKED = "Your assistant hasn't picked for this reel yet. Tell it which photos you'd like below, then copy the line into the chat."
OLD_LINE = "hasn't picked for this shoot yet"
NOTE = "Only the ones in front of the white backdrop.\nNot the $5 \"cupcake\" ones, <b>please</b>."


def her_v25():
    for base in (ROOT, ROOT.parent / "hf-tools"):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v25-*")):
            f = h / "Carousel designer and reel picker"
            if (f / "pages" / "reel-maker.html").is_file():
                return f
    return None


def run(s, script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, encoding="utf-8",
                       errors="replace", env=s.env, timeout=240)
    return r.returncode, (r.stdout + r.stderr)


def reel_rec(s, kit):
    try:
        return json.loads((s.kit(kit) / ".kit" / "reel-page.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def reel_bytes(s, kit):
    out = []
    for name in ("reel-page.json", "reel-page.prev.json", "kit.json"):
        try:
            out.append((s.kit(kit) / ".kit" / name).read_bytes())
        except OSError:
            out.append(None)
    return out


def reel_state(s, kit):
    return s.http("GET", "/reel-state" + s.q(kit))[1]


def save(s, kit, saved, reel=None, page=PAGE):
    st = reel_state(s, kit)
    body = {"kit": kit, "stamp": st["stamp"], "base": st["rev"], "page": page, "saved": saved}
    if reel:
        body["reel"] = reel
    return s.post("/reel-save", body)


def ver(s, kit, **ask):
    return s.post("/reel-version", dict(ask, kit=kit))


# ---------- her words ----------

def run_words(s):
    import reel_page as rp
    w = rp.PICK_WORDS
    case("the page's lines for this are in their own table, and the not-picked line is hers of v25",
         w["not_picked"] == NOT_PICKED and "not_picked_html" not in rp.WORDS and "not_picked" not in rp.WORDS)
    case("the line it replaced (\"...for this shoot yet. In the chat, say...\") is nowhere in the page's words or script",
         OLD_LINE not in json.dumps(rp.WORDS, ensure_ascii=False) + json.dumps(w, ensure_ascii=False) and OLD_LINE not in rp.page_html(KIT, "x"))
    case("no page word says Claude, and none has a long dash", not [v for v in w.values() if "Claude" in v or "—" in v or "–" in v])
    case("the line to copy is built from three pieces: the shoot, the reel's name, the note's ending",
         w["photo_for"] == "Pick my reel photos for {short}" and w["photo_reel"] == ", {name}" and w["photo_note"] == ", and follow my note")
    case("her box holds 600 letters, and so does what is saved", rp.PHOTO_ASK_MAX == 600)
    hers = her_v25()
    if hers is None:
        t.skip("the photo note's words against her v25 reel page: her handoff (reference-private) isn't on this computer")
        return
    page = (hers / "pages" / "reel-maker.html").read_text(encoding="utf-8")
    server = (hers / "server.py").read_text(encoding="utf-8")
    flat = page.replace("\\'", "'")
    bad = [(k, frag) for k, v in w.items() for frag in re.split(r"\{\w+\}", v) if len(frag.strip()) >= 2 and frag not in flat]
    case("every word of ours for this (%d lines) is in her v25 reel page, word for word" % len(w), not bad, bad)
    block = re.search(r'<div class="paste ask photoask" id="photoAskBox">(.*?)\n    </div>', page, re.S).group(1)
    her_bits = [x.strip() for x in re.findall(r">([^<>]+)<", block) if x.strip()] + re.findall(r'placeholder="([^"]+)"', block)
    ours = [v.strip() for v in w.values()] + [rp.WORDS["copy"]]
    case("every line her note box shows is one of ours, whole", len(her_bits) >= 6 and not [x for x in her_bits if x not in ours], [x for x in her_bits if x not in ours])
    case("her line to copy is built the way ours is (the reel's name only with several reels, the ending only with a note)",
         "'Pick my reel photos for ' + short + (nm ? ', ' + nm : '') + (photoAsk ? ', and follow my note' : '')" in page
         and "VERS.length > 1 && v ? v.name : ''" in page)
    case("her not-picked line is the one line her page has for a reel with no pick", flat.count(NOT_PICKED) == 1 and OLD_LINE not in flat)
    case("her box: two rows, 600 letters, and her server keeps 600", 'rows="2" maxlength="600"' in block and '"photo_ask": str(d.get("photo_ask") or "")[:600]' in server)
    her_css = [ln.strip() for ln in page.splitlines() if ln.strip().startswith(".photoask")]
    case("her style rules for the box are ours, each as she wrote it", len(her_css) == 3 and all(ln in rp.page_html(KIT, "x") for ln in her_css),
         [ln for ln in her_css if ln not in rp.page_html(KIT, "x")])
    html_ = rp.page_html(KIT, "x")
    case("the box sits where hers does: after the two choices, before the Longer and Quicker tip",
         html_.index("id='useMine'") < html_.index("id='photoAskBox'") < html_.index("class='tip'")
         and page.index('id="useMine"') < page.index('id="photoAskBox"') < page.index('<div class="tip">'))


# ---------- the note, by request ----------

def run_note(s):
    st = reel_state(s, KIT)
    case("(set up: one reel, nothing saved, no pick)", st["ok"] and st["saved"] is None and st["claude"] == [] and len(st["versions"]) == 1, st.get("saved"))
    code, j = save(s, KIT, {"picks": [], "mine": True, "photo_ask": NOTE})
    case("the note is saved with the reel's other choices, as photo_ask, exactly as typed", code == 200 and j["ok"] and reel_rec(s, KIT)["saved"]["photo_ask"] == NOTE, j)
    case("...and the page is given it back", reel_state(s, KIT)["saved"]["photo_ask"] == NOTE)
    code, j = save(s, KIT, {"vibe": "calm"})
    case("a save that does not send the note keeps it", code == 200 and reel_rec(s, KIT)["saved"]["photo_ask"] == NOTE and reel_rec(s, KIT)["saved"]["vibe"] == "calm")
    before = reel_bytes(s, KIT)
    for bad, why in (("x" * 601, "longer than her 600"), (7, "a number"), (["a"], "a list"), ({"a": 1}, "an object"), ("a\x00b", "a nul in it"), (None, "nothing")):
        code, j = save(s, KIT, {"photo_ask": bad})
        case("a note that is %s is refused whole, nothing written" % why, code == 400 and not j.get("ok") and reel_bytes(s, KIT) == before, (code, j))
    code, j = save(s, KIT, {"photo_ask": "x" * 600})
    case("600 letters is taken (her box's length)", code == 200 and len(reel_rec(s, KIT)["saved"]["photo_ask"]) == 600, code)
    save(s, KIT, {"photo_ask": NOTE})
    # the command, one reel
    before = reel_bytes(s, KIT)
    code, out = run(s, "reel_page.py", "note", KIT)
    case("reel_page.py note: one reel, the note word for word, each of its lines whole", code == 0 and "This shoot has one reel. The pick is for it." in out
         and all(("    " + ln) in out for ln in NOTE.splitlines()) and "word for word" in out, out)
    case("...it says to pick only what the note allows, and to ask when nothing fits", "Pick only what the note allows." in out and "say so and ask" in out and "never widen it" in out, out)
    case("...and the command that saves the pick, with no --for-reel when the pick is for the open reel",
         ('kit.py picks "%s" --reel' % KIT) in out and "--for-reel" not in out, out)
    case("...it changes nothing (the records are byte for byte as they were)", reel_bytes(s, KIT) == before)
    code, out = run(s, "reel_page.py", "show", KIT)
    case("reel_page.py show prints the note too", code == 0 and "Their note for this reel's photos" in out and "white backdrop" in out, out)
    # a second reel: its own note
    code, j = ver(s, KIT, op="new")
    st = reel_state(s, KIT)
    case("a new reel has no note of its own (hers: per reel)", code == 200 and st["current"] == "v2" and not (st["saved"] or {}).get("photo_ask"), st.get("saved"))
    case("...and the first reel's note waits with it, untouched", reel_rec(s, KIT)["versions"][0]["data"]["saved"]["photo_ask"] == NOTE)
    code, out = run(s, "reel_page.py", "note", KIT)
    case("note with several reels and no note on the open one: says which reel, and to choose from the whole shoot",
         code == 0 and 'The pick is for "Reel 2", the reel open on the page' in out and "No note for this reel's photos" in out and "white backdrop" not in out
         and "--for-reel" not in out.split("Save the pick")[1], out)
    save(s, KIT, {"photo_ask": "Just the kitchen and the cupcakes."}, reel="v2")
    before = reel_bytes(s, KIT)
    code, out = run(s, "reel_page.py", "note", KIT, "--reel", "reel 1")
    case("the line names a reel that is not the one open on the page: said plainly, that reel's own note, and --for-reel in the command",
         code == 0 and 'NOTE: the line names "Reel 1", but the reel open on the page is "Reel 2".' in out and "white backdrop" in out and "cupcakes." not in out
         and '--for-reel "Reel 1"' in out and 'Nothing of "Reel 2" changes.' in out, out)
    code, out = run(s, "reel_page.py", "note", KIT, "--reel", "Reel 2")
    case("the line names the reel that is open: its note, no --for-reel", code == 0 and "Just the kitchen and the cupcakes." in out and "white backdrop" not in out
         and "NOTE:" not in out and "--for-reel" not in out, out)
    code, out = run(s, "reel_page.py", "note", KIT, "--reel", "Garden")
    case("a name that fits no reel stops, lists the reels, and changes nothing", code == 1 and out.startswith("STOP:") and '"Reel 1"' in out and '"Reel 2"' in out, out)
    case("none of those four looks changed anything", reel_bytes(s, KIT) == before)
    # the pick, for that reel only, and the note said again
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "2+,3,4-", "--for-reel", "Reel 1")
    st1 = s.http("GET", "/reel-state" + s.q(KIT))[1]
    case("kit.py picks --for-reel saves the pick for the reel named and says that reel's note again",
         code == 0 and "Their note for this reel's photos: Only the ones in front of the white backdrop." in out and "cupcakes." not in out, out)
    case("...the reel open on the page has no pick still, and says so to the page", st1["current"] == "v2" and st1["claude"] == [], st1["claude"])
    code, out = run(s, "kit.py", "picks", KIT, "--reel", "5,6+")
    case("a pick with no --for-reel goes to the open reel, with its note", code == 0 and "Just the kitchen and the cupcakes." in out and "white backdrop" not in out, out)
    kj = json.loads((s.kit(KIT) / ".kit" / "kit.json").read_text(encoding="utf-8"))
    case("each reel has its own pick: the first reel's 2, 3, 4, the second's 5, 6", kj["picks"]["reel"] == [2, 3, 4] and [x["n"] for x in reel_state(s, KIT)["claude"]] == [5, 6], kj.get("picks"))
    # a page showing reel 1 can't write its note into reel 2
    before = reel_bytes(s, KIT)
    code, j = save(s, KIT, {"photo_ask": "from a page still on reel 1"}, reel="v1")
    case("a page still showing another reel can't write its note into this one", not (code == 200 and j.get("ok") and not j.get("state")) and reel_rec(s, KIT)["saved"]["photo_ask"] == "Just the kitchen and the cupcakes.", (code, j.get("why")))
    code, _ = s.post("/reel-save", {"kit": KIT, "stamp": reel_state(s, KIT)["stamp"], "base": reel_state(s, KIT)["rev"], "page": PAGE, "saved": {"photo_ask": "x"}},
                     headers={"Origin": "http://evil.example"})
    case("another website's save of a note is refused (the page's own guard)", code == 403 and reel_rec(s, KIT)["saved"]["photo_ask"] == "Just the kitchen and the cupcakes.", code)


# ---------- a new kit: "make my posts" picks nothing ----------

def run_new_kit(s):
    k = s.make_kit(NEW_KIT, photos=7, sheet=not t.MAC)
    code, out = run(s, "kit.py", "start", NEW_KIT)
    case("kit.py start says what is next: number the photos and show the post kit, nothing picked, no question",
         code == 0 and "Nothing is picked or made until they ask." in out and "the question" not in out, out)
    if t.MAC:
        code, out = run(s, "kit.py", "sheet", NEW_KIT)
        case("kit.py sheet numbers the photos", code == 0 and (k / ".kit" / "sheet.json").is_file(), out)
    kj = json.loads((k / ".kit" / "kit.json").read_text(encoding="utf-8"))
    case("after start and sheet the kit has no pick of any kind", not any((kj.get("picks") or {}).values()) and not kj.get("reel_marks"), kj.get("picks"))
    case("...and no piece was made: no Singles, Carousel, Stories or Covers folder", not [d for d in ("Singles", "Carousel", "Stories", "Covers") if (k / d).exists()],
         sorted(p.name for p in k.iterdir()))
    st = reel_state(s, NEW_KIT)
    case("the reel page has nothing picked and nothing saved for it", st["ok"] and st["claude"] == [] and st["saved"] is None and st["total"] == 7, (st.get("claude"), st.get("saved")))
    code, out = run(s, "reel_page.py", "note", NEW_KIT)
    case("reel_page.py note on a shoot nobody has touched: one reel, no note, no pick so far", code == 0 and "No note for this reel's photos" in out and "(none yet)" in out, out)
    code, out = run(s, "posting_queue.py", "add", "--kit", NEW_KIT)
    case("in the posting queue the reel and the carousel are both not started", code == 0 and "reel: red" in out and "carousel: red" in out, out)
    code, _j, raw, _h = s.http("GET", "/content/" + NEW_KIT.replace(" ", "%20") + "/Post%20kit.html")
    page = raw.decode("utf-8", "replace")
    case("the post kit opens with nothing picked and nothing made (her Reel card line, No slides yet, No stories yet)",
         code == 200 and "Your assistant hasn&#x27;t picked the reel photos yet." in page.replace("'", "&#x27;") and "No slides yet." in page and "No stories yet." in page, code)


# ---------- the page ----------

BOX = ("(function(){ var b = document.getElementById('photoAskBox'), l = b.querySelector('label'), ta = document.getElementById('photoAskIn');"
       " return {prev: b.previousElementSibling.className, next: b.nextElementSibling.className, inStep: document.getElementById('step1').contains(b),"
       " title: l.querySelector('b').textContent, opt: l.childNodes[1].textContent, ex: l.querySelector('.ex').textContent, forIn: l.htmlFor,"
       " rows: ta.rows, max: ta.maxLength, ph: ta.placeholder, then: b.querySelector('p').textContent, copy: document.getElementById('copyPhoto').textContent,"
       " kids: document.getElementById('photoPaste').children.length}; })()")


def line(c):
    return c.text("#photoPaste")


def run_page(c, s):
    import reel_page as rp
    kit = "2026-09-27 Page <i>reel &amp; more" if not t.WINDOWS else "2026-09-27 Page reel"
    short = kit[11:]
    s.make_kit(kit, photos=8)
    c.open(s.url("/reel.html" + s.q(kit)))
    c.wait_for("window.Reel && window.Reel.state()", 20)
    case("a new shoot's reel: Let my assistant choose says her line, as plain words", c.text("#claudeWords") == NOT_PICKED and c.count("#claudeWords b") == 0, c.text("#claudeWords"))
    case("...and the page is on I'll drag them in myself, with nothing in the reel", c.js("document.getElementById('useMine').classList.contains('on')") and c.count("#reel .tile") == 0)
    box = c.js(BOX)
    case("her note box is under the two choices, before the tip, in step 2",
         box["prev"] == "choice" and box["next"] == "tip" and box["inStep"] is True, box)
    case("her words on it: the title, optional and only for this reel, her two examples, the placeholder, the line above the copy line",
         box["title"] == "Tell your assistant which photos you'd like in this reel" and box["opt"] == " Optional, and only for this reel."
         and box["ex"] == "For example: “Only the ones in front of the white backdrop.” or “Just the kitchen and the cupcakes.”"
         and box["ph"] == "Optional: which photos to use, or leave out" and box["forIn"] == "photoAskIn"
         and box["then"] == "Then copy this into the chat, and your assistant picks the photos for this reel:" and box["copy"] == "Copy", box)
    case("the box is two rows and takes 600 letters (hers)", box["rows"] == 2 and box["max"] == 600, box)
    case("with one reel and no note the line is the shoot only, and the shoot's name is letters, not a tag",
         line(c) == "Pick my reel photos for " + short and box["kids"] == 0, line(c))
    c.click("#useClaude")
    case("Let my assistant choose with no pick: her line stays, nothing else changes",
         c.text("#claudeWords") == NOT_PICKED and c.js("document.getElementById('useMine').classList.contains('on')"))
    # a note
    c.click("#photoAskIn")
    c.type_text("  Only the white backdrop ")
    case("with a note the line ends \", and follow my note\"", line(c) == "Pick my reel photos for " + short + ", and follow my note", line(c))
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("photo_ask") == "Only the white backdrop", 8, what="the note saved")
    case("the note is saved by itself as they type, as photo_ask, without the spaces round it", reel_rec(s, kit)["saved"]["photo_ask"] == "Only the white backdrop")
    case("...and what they typed stays in the box as typed (nothing rewrites it under their hand)", c.js("document.getElementById('photoAskIn').value") == "  Only the white backdrop ")
    # Copy
    c.js("window.__copied = null; document.execCommand = function(){ window.__copied = String(window.getSelection()); return true; }")
    c.click("#copyPhoto")
    case("Copy copies the line and says Copied", c.js("window.__copied") == line(c) and c.text("#copyPhoto") == "Copied", c.js("window.__copied"))
    c.wait_for("document.getElementById('copyPhoto').textContent === 'Copy'", 5)
    # the note cleared: the ending goes
    c.click("#photoAskIn")
    c.key("Mod+A")
    c.key("Backspace")
    case("the note cleared: the ending goes from the line", line(c) == "Pick my reel photos for " + short, line(c))
    c.type_text("Just the kitchen")
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("photo_ask") == "Just the kitchen", 8, what="the second note saved")
    # a second reel
    c.click("#verNew")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v2'", 20)
    case("a new reel: its box is empty, its line names the reel and has no ending (hers: the name only with several reels)",
         c.js("document.getElementById('photoAskIn').value") == "" and line(c) == "Pick my reel photos for " + short + ", Reel 2", line(c))
    case("...and it says her not-picked line", c.text("#claudeWords") == NOT_PICKED)
    case("...the first reel's note is kept with it", reel_rec(s, kit)["versions"][0]["data"]["saved"]["photo_ask"] == "Just the kitchen")
    c.click("#verRen")
    c.key("Mod+A")
    c.type_text("White <b>backdrop</b>")
    c.key("Enter")
    c.wait_for("document.getElementById('verRenBox').hidden", 5)
    case("Rename: the line has the new name at once, as letters", line(c) == "Pick my reel photos for " + short + ", White <b>backdrop</b>" and c.count("#photoPaste *") == 0, line(c))
    c.click("#photoAskIn")
    c.type_text("only the white backdrop")
    case("a note on the second reel: the shoot, the reel's name, then the ending", line(c) == "Pick my reel photos for " + short + ", White <b>backdrop</b>, and follow my note", line(c))
    chrome_drive.wait_until(lambda: ((reel_rec(s, kit) or {}).get("saved") or {}).get("photo_ask") == "only the white backdrop", 8, what="the second reel's note saved")
    case("the second reel's note is its own; the first reel's is as it was",
         reel_rec(s, kit)["saved"]["photo_ask"] == "only the white backdrop" and reel_rec(s, kit)["versions"][0]["data"]["saved"]["photo_ask"] == "Just the kitchen")
    # the Assistant picks for this reel while the page is open
    c.js("document.activeElement.blur()")
    code, out = run(s, "kit.py", "picks", kit, "--reel", "3+,1,2-")
    c.js("window.Reel.followNow()")
    c.wait_for("document.getElementById('claudeWords').textContent !== %s" % json.dumps(NOT_PICKED), 10)
    case("the Assistant's pick arrives: her line gives way to what Let my assistant choose does, and their own (empty) order stays on the screen",
         code == 0 and c.text("#claudeWords") == rp.WORDS["claude_words"] and c.count("#reel .tile") == 0
         and c.js("document.getElementById('useMine').classList.contains('on')"), (out, c.text("#claudeWords")))
    c.click("#useClaude")
    c.wait_for("document.querySelectorAll('#reel .tile').length === 3", 5)
    case("...and pressing Let my assistant choose shows the pick", c.js("Array.from(document.querySelectorAll('#reel .tile')).map(function(x){ return +x.dataset.n; })") == [3, 1, 2])
    # a note written in another window shows when the box is not under their hand
    chrome_drive.wait_until(lambda: (reel_rec(s, kit)["saved"].get("mine") is False), 8, what="the choice saved")
    save(s, kit, {"photo_ask": "from the other window"}, page="otherpage1")
    c.js("window.Reel.followNow()")
    c.wait_for("document.getElementById('photoAskIn').value === 'from the other window'", 10)
    case("a note saved in another window shows here, and the line keeps its ending", line(c).endswith(", and follow my note"))
    ver(s, kit, op="rename", id="v2", name="Garden")
    c.js("window.Reel.followNow()")
    c.wait_for("document.getElementById('verSel').selectedOptions[0].textContent === 'Garden'", 10)
    case("a reel renamed in another window: the line here names it anew", line(c) == "Pick my reel photos for " + short + ", Garden, and follow my note", line(c))
    # back to the first reel
    c.set_value("#verSel", "v1")
    c.wait_for("window.Reel && window.Reel.state() && window.Reel.state().current === 'v1'", 20)
    case("back on the first reel: its own note is in the box, and the line names it with the ending",
         c.js("document.getElementById('photoAskIn').value") == "Just the kitchen" and line(c) == "Pick my reel photos for " + short + ", Reel 1, and follow my note", line(c))
    case("no fault on the page", not c.page_errors(), c.page_errors())
    c.phone(375, 800)
    c.reload()
    c.wait_for("window.Reel && window.Reel.state()", 20)
    wide = c.js("[document.documentElement.scrollWidth, document.getElementById('photoAskBox').getBoundingClientRect().right, document.getElementById('copyPhoto').getBoundingClientRect().right]")
    case("at a phone's width the box and its line fit, and nothing makes the page scroll sideways", wide[0] <= 375 and wide[1] <= 375 and wide[2] <= 375, wide)
    c.desktop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="picks-ask-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"       # no folder window, no picker, no CapCut, whatever a test presses
    s.env["STUDIO_CARD_FOR_TESTS"] = "none"
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    s.make()
    try:
        s.make_kit(KIT, photos=9)
        group("her words: the not-picked line, the note box, the line to copy", run_words, s)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("the photo note by request, and the command the Assistant reads", run_note, s)
        group("a new kit picks nothing and makes nothing", run_new_kit, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("the note box on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1000)) as c:
                group("the note box and the line to copy, on the page", run_page, c, s)
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
