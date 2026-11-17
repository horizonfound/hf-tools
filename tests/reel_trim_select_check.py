#!/usr/bin/env python3
"""Trim a clip, and select several photos like Lightroom (Nicole's handoff v25, sections 4 and 8; stage I of the
v26 build), on the reel page.

    python3 tests/reel_trim_select_check.py                 everything (the page in a hidden Chrome)
    python3 tests/reel_trim_select_check.py --no-chrome     the checks that need no browser
    python3 tests/guard.py 3000 python3 tests/reel_trim_select_check.py     as it is run: under the memory guard

What it holds:
  her words     the Trim button, the trim panel and the two "N selected" bars against her v25 reel page, both
                ways; her style rules, each as she wrote it; the panel's markup above the page's scripts
  a trim        by request (POST /reel-moment, do: update, with a start AND an end), on the 3-second clip in
                tests/fixtures: saved whole with the version before kept, marked as set; refused outside 1 to 15
                seconds, with a start before 0, or with anything that is not a number, nothing written; never
                past the video's end; the card's - and + as before, and no longer past the end either; another
                website and another reel refused
  selecting     in a hidden Chrome, with the real Shift, Cmd and Ctrl keys: click, Shift-click, Cmd/Ctrl-click,
                Escape; the bar (Longer, Quicker, Neither, Take them out, Clear), each one save and one Undo;
                a drag of any selected photo moves them all, in order, with the "N photos" tag and the others
                faded; in All your photos a plain click still adds or takes out, Shift and Cmd select, then a
                drag up or Add them to the end; more than a reel holds is refused whole; a phone's width
  the panel     RETIRED with Nicole's v27 (Nov 17): the trim lives on the footage editor's timeline
                (tests/reel_footage_check.py --only editor drives it), and her v27 page leaves the v25 panel
                unreachable. Its code stays in reel_page.py behind TRIM_PANEL (False) until Nicole says; this
                test holds that the panel is NOT on the page, that its words and markup are still there to put
                back, and that a trim by request behaves exactly as the editor's drags send it. --only trim and
                --only pc run that part alone.

Nothing here touches the real ~/.studio, a real kit, CapCut or a visible window: a scratch home and pretend kits.
Python 3.9, standard library only.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import talking_page_check as t  # noqa: E402   (its Setup: a scratch home, pretend kits, the page server)

SCRIPTS = t.SCRIPTS
PORT = 9900
KIT = "2026-09-23 Zoë & the 'boys' 🌊" if t.WINDOWS else "2026-09-23 Zoë <b>& the 'boys' 🌊"
SEL_KIT = "2026-09-28 Select several"
BIG_KIT = "2026-09-29 A full reel"
TRIM_KIT = "2026-09-30 Trim a clip"
PAGE = "abcdefgh12"
FIXTURE = HERE / "fixtures" / "loud-tone-3s.mp4"
TAIL = "Press ▶ to preview one, use − and + to make it shorter or longer, Trim to pick exactly where it starts and ends, or Remove it."   # her v25 line; gone from the page since v27


def her_v25():
    for base in (ROOT, ROOT.parent / "hf-tools"):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v25-*")):
            f = h / "Carousel designer and reel picker"
            if (f / "pages" / "reel-maker.html").is_file():
                return f
    return None


def rec(s, kit, name="reel-page.json"):
    try:
        return json.loads((s.kit(kit) / ".kit" / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def rec_bytes(s, kit):
    try:
        return (s.kit(kit) / ".kit" / "reel-page.json").read_bytes()
    except OSError:
        return None


def reel_state(s, kit):
    return s.http("GET", "/reel-state" + s.q(kit))[1]


def save(s, kit, saved, page=PAGE):
    st = reel_state(s, kit)
    return s.post("/reel-save", {"kit": kit, "stamp": st["stamp"], "base": st["rev"], "page": page, "saved": saved})


def footage(s, kit):
    return s.http("GET", "/reel-footage" + s.q(kit))[1]


def wait_videos(s, kit, n=1, seconds=90):
    def ready():
        j = footage(s, kit)
        vs = (j or {}).get("videos") or []
        return j if len(vs) >= n and all(v["preview"] in ("ready", "failed", "lowspace", "pc", "hevc_pc") for v in vs) else None
    return t.wait_for(ready, seconds, 0.3)


def moment(s, body, **kw):
    return s.post("/reel-moment", body, **kw)


def the_moment(s, kit, mid):
    return next((m for m in (rec(s, kit) or {}).get("moments") or [] if m.get("id") == mid), None)


def picks(n):
    return [{"n": i, "h": ""} for i in range(1, n + 1)]


# ---------- her words ----------

def run_words(s):
    import reel_page as rp
    tw, sw = rp.TRIM_WORDS, rp.SELECT_WORDS
    page_ours = rp.page_html(KIT, "x")
    case("no page word of these says Claude, and none has a long dash",
         not [v for v in list(tw.values()) + list(sw.values()) + [rp.OUR_WORDS["trim_stuck"], rp.OUR_WORDS["trim_no_stills_pc"], rp.OUR_WORDS["trim_length"]]
              if "Claude" in v or "—" in v or "–" in v])
    body = page_ours.split("<div class='wrap'>", 1)[1].split("<script", 1)[0]          # the page's markup: no style, no script, no words table
    case("her v25 line over the clip cards is kept in the table, and is NOT on the page since v27 (the editor has no such row)", tw["moments_tail"] == TAIL and TAIL not in body)
    case("a clip is kept 1 to 15 seconds, an arrow moves an end a quarter second, the strip shows about 8 seconds either side (hers)",
         (rp.MOMENT_MIN, rp.MOMENT_MAX, rp.TRIM_NUDGE, rp.TRIM_WINDOW, rp.TRIM_SPAN_MIN, rp.TRIM_GRID) == (1.0, 15.0, 0.25, 16.0, 20.0, 0.05))
    case("the trim panel is not on the page (TRIM_PANEL is False since v27: the trim lives on the editor's timeline)",
         rp.TRIM_PANEL is False and "id='trim'" not in body and "id='trimDone'" not in body and "R.openTrim = open" not in page_ours and 'class="tr"' not in page_ours)
    was = rp.TRIM_PANEL
    try:
        rp.TRIM_PANEL = True
        back = rp.page_html(KIT, "x")
        case("...and can be put back with one switch: the panel's markup above every script, its script, and a Trim button in a picked clip's box",
             0 < back.index("id='trim'") < back.index("<script") and "R.openTrim = open" in back and "edTrimClip" in back)
    finally:
        rp.TRIM_PANEL = was
    case("the two bars sit where hers do: one over the order, one inside All your photos over the photos",
         page_ours.index("id='undoBtn'") < page_ours.index("id='reelSel'") < page_ours.index("id='reel'")
         and page_ours.index("<summary>") < page_ours.index("id='allSel'") < page_ours.index("id='all'"))
    case("on a Mac the editor has no PC line; where no stills can be taken it has ours, under the timeline",
         ("class='say sm edtip pcnote'" in body) == rp.pc_footage() and (html.escape(rp.OUR_WORDS["editor_no_stills_pc"]) in body) == rp.pc_footage())
    hers = her_v25()
    if hers is None:
        t.skip("the trim and select words against her v25 reel page: her handoff (reference-private) isn't on this computer")
        return
    page = (hers / "pages" / "reel-maker.html").read_text(encoding="utf-8")
    server = (hers / "server.py").read_text(encoding="utf-8")
    flat = html.unescape(page).replace("\\'", "'")
    for name, w in (("Trim", tw), ("selecting several", sw)):
        bad = [(k, frag) for k, v in w.items() for frag in re.split(r"\{\w+\}", v) if len(frag.strip()) >= 2 and frag not in flat]
        case("every word of ours for %s (%d lines) is in her v25 reel page, word for word" % (name, len(w)), not bad, bad)
    block = re.search(r'<div class="trim" id="trim".*?\n</div>\n', page, re.S).group(0)
    her_bits = [html.unescape(x).strip() for x in re.findall(r">([^<>]+)<", block) if x.strip()] + re.findall(r'(?:title|aria-label)="([^"]+)"', block)
    her_bits = [x for x in her_bits if x not in ("×", "◀", "▶")]          # her glyph-only buttons: ours carry the same glyphs
    ours = [v.strip() for v in tw.values()]
    case("every line her trim panel shows or names is one of ours, whole", len(her_bits) >= 14 and not [x for x in her_bits if x not in ours],
         [x for x in her_bits if x not in ours])
    her_ids = re.findall(r'id="(trim\w*)"', block)
    case("every part of her panel is in ours, by her name (%d of them)" % len(her_ids), len(her_ids) >= 14 and all(("id='%s'" % i) in page_ours for i in her_ids),
         [i for i in her_ids if ("id='%s'" % i) not in page_ours])
    case("her four arrows are ours: a quarter second earlier or later, for the start and for the end",
         sorted(re.findall(r'data-n="([^"]+)"', block)) == sorted(re.findall(r"data-n='([^']+)'", page_ours)) == ["a:-0.25", "a:0.25", "b:-0.25", "b:0.25"])
    case("her card's Trim button: the scissors, the word, the title",
         '<button class="tr" title="Trim the start and the end">&#9986; Trim</button>' in page and tw["trim_btn"] == "✂ Trim")
    case("her readout is ours: Starts, ends, the length",
         "`Starts <b>${fmt2(TR.a)}</b> · ends <b>${fmt2(TR.b)}</b> · <b>${(TR.b - TR.a).toFixed(1)} s</b>`" in page)
    case("her two bars are ours, piece by piece",
         "<b>${SEL.size} selected.</b> Drag any of them and they all move together. <button data-s=\"long\">Longer</button><button data-s=\"quick\">Quicker</button>"
         "<button data-s=\"plain\">Neither</button><button data-s=\"out\">Take them out</button><button data-s=\"clear\">Clear</button>" in page
         and "<b>${ALLSEL.size} selected.</b> Drag any of them up into your order, or <button data-a=\"add\">Add them to the end</button><button data-a=\"clear\">Clear</button>" in page)
    her_css = [ln for ln in page.splitlines() if ln.startswith((".trim", ".mom .len button.tr", ".tile.picked", ".pick.picked", ".tile.riding",
                                                                "[data-count]", ".tile[data-count]", ".selbar"))]
    case("her style rules for the panel, the Trim button, a selected photo, the tag and the bars are ours, each as she wrote it (%d)" % len(her_css),
         len(her_css) == 39 and all(ln in page_ours for ln in her_css), [ln[:60] for ln in her_css if ln not in page_ours])
    case("her tag on the photos being moved says \"N photos\" (in her style rule, and so in ours)", "content:attr(data-count) ' photos'" in page_ours)
    case("her server keeps a clip 1 to 15 seconds, as ours does", "end = max(start + 1.0, min(end, start + 15.0, length))" in server)
    case("her numbers in her page: 1 and 15 seconds, twentieths, 8 seconds either side",
         "const MIN = 1.0, MAX = 15;" in page and "Math.round(a * 20) / 20" in page and "Math.max(20, (m.end - m.start) + 16)" in page)


# ---------- a trim, by request ----------

def run_request(s):
    import reel_page as rp
    kit = TRIM_KIT
    k = s.make_kit(kit, photos=6)
    (k / "Footage").mkdir()
    shutil.copyfile(str(FIXTURE), str(k / "Footage" / "clip.mp4"))
    j = wait_videos(s, kit)
    v = ((j or {}).get("videos") or [{}])[0]
    case("(set up: the 3-second clip is listed)", v.get("name") == "clip.mp4" and v.get("length") == 3.0, v)
    code, r = moment(s, {"kit": kit, "do": "add", "video": v.get("key"), "start": 0.5, "seconds": 1.5})
    mid = ((r or {}).get("moments") or [{}])[0].get("id")
    case("(set up: a clip of theirs, 0.5 to 2.0)", code == 200 and mid and the_moment(s, kit, mid)["end"] == 2.0, r)
    before = rec(s, kit)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "start": 1.0, "end": 2.5})
    m = the_moment(s, kit, mid)
    case("a trim (a start and an end together) is saved as asked", code == 200 and (m["start"], m["end"]) == (1.0, 2.5) and r["moments"][0]["start"] == 1.0, (code, r))
    case("...marked as a length they set, and a clip of their own is named for where it now starts (hers)", m.get("set") is True and m["label"] == "Your pick at 0:01", m)
    case("...the version before is kept beside the record", rec(s, kit, "reel-page.prev.json") == before)
    held = rec_bytes(s, kit)
    for name, body, words in (
            ("shorter than a second", {"start": 1.0, "end": 1.5}, rp.OUR_WORDS["trim_length"]),
            ("longer than 15 seconds", {"start": 0.0, "end": 15.5}, rp.OUR_WORDS["trim_length"]),
            ("a start before the video's start", {"start": -0.5, "end": 1.0}, rp.OUR_WORDS["trim_length"]),
            ("an end before its start", {"start": 2.0, "end": 1.0}, rp.OUR_WORDS["trim_length"]),
            ("a start that is not a number", {"start": "1", "end": 2.5}, None),
            ("an end that is true", {"start": 1.0, "end": True}, None),
            ("a field it doesn't know", {"start": 1.0, "end": 2.5, "length": 99}, None),
            ("no start and no end", {}, None)):
        code, r = moment(s, dict({"kit": kit, "do": "update", "id": mid}, **body))
        case("refused, nothing written: " + name, code == 400 and r.get("ok") is False and (words is None or r.get("words") == words) and rec_bytes(s, kit) == held, (code, r))
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "start": 2.0, "end": 3.5})
    m = the_moment(s, kit, mid)
    case("a trim that runs past the video's end is slid back inside it, its length kept", code == 200 and (m["start"], m["end"]) == (1.5, 3.0), m)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "start": 0.0, "end": 3.0})
    case("the whole of a 3-second video is a trim", code == 200 and (the_moment(s, kit, mid)["start"], the_moment(s, kit, mid)["end"]) == (0.0, 3.0))
    # the card's - and + (an end alone), as before
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "end": 2.5})
    case("the card's minus (an end alone) still works", code == 200 and the_moment(s, kit, mid)["end"] == 2.5)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "end": 9.0})
    case("the card's plus stops at the video's end", code == 200 and the_moment(s, kit, mid)["end"] == 3.0)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "end": 0.2})
    case("...and never makes a clip shorter than a second", code == 200 and the_moment(s, kit, mid)["end"] == 1.0)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "start": 2.9})
    m = the_moment(s, kit, mid)
    case("a start alone, right at the video's end: the clip ends at the end, a second long (it used to end past it)",
         code == 200 and m["end"] == 3.0 and m["start"] == 2.0, m)
    held = rec_bytes(s, kit)
    code, _j, _raw, _h = s.http("POST", "/reel-moment", {"kit": kit, "do": "update", "id": mid, "start": 0.5, "end": 2.0}, headers={"Origin": "http://evil.example"})
    case("another website's trim is refused, nothing written", code == 403 and rec_bytes(s, kit) == held, code)
    code, r = moment(s, {"kit": kit, "do": "update", "id": mid, "start": 0.5, "end": 2.0, "reel": "v7"})
    case("a trim from a page showing another reel is refused, nothing written", code in (400, 409) and rec_bytes(s, kit) == held, (code, r))
    code, r = moment(s, {"kit": kit, "do": "update", "id": "u9-abcdef", "start": 0.5, "end": 2.0})
    case("a clip that isn't there: her line, nothing written", code == 400 and r.get("words") == rp.WORDS["moment_gone"] and rec_bytes(s, kit) == held, (code, r))
    out = json.dumps(r) + json.dumps(footage(s, kit))
    case("no answer has a path in it", str(s.work) not in out and "/Footage" not in out)


# ---------- selecting several, on the page ----------

ORDER = "Array.from(document.querySelectorAll('#reel .tile')).map(function(x){ return +x.dataset.n; })"
PICKED = "Array.from(document.querySelectorAll('#reel .tile.picked')).map(function(x){ return +x.dataset.n; })"
ALLPICKED = "Array.from(document.querySelectorAll('#all .pick.picked')).map(function(x){ return +x.dataset.n; })"
MARKS = "Array.from(document.querySelectorAll('#reel .tile')).map(function(x){ return x.classList.contains('long') ? '+' : x.classList.contains('quick') ? '-' : ''; }).join(',')"
BAR = ("(function(id){ var b = document.getElementById(id); return {hidden: b.hidden, text: b.textContent, bold: b.querySelector('b') ? b.querySelector('b').textContent : '',"
       " buttons: Array.from(b.querySelectorAll('button')).map(function(x){ return x.textContent; })}; })")


def tile(n):
    return "#reel .tile[data-n='%d'] .ph" % n


def pick(n):
    return "#all .pick[data-n='%d']" % n


def saved_order(s, kit):
    r = rec(s, kit) or {}
    return [(x["n"], x["h"]) for x in (r.get("saved") or {}).get("picks") or []]


def wait_saved(s, kit, want, what):
    chrome_drive.wait_until(lambda: saved_order(s, kit) == want, 8, what=what)


def run_select(c, s):
    kit = SEL_KIT
    s.make_kit(kit, photos=12)
    reel_state(s, kit)
    code, r = save(s, kit, {"picks": picks(8), "mine": True})
    case("(set up: their own order of 8 photos)", code == 200, r)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))     # v27: a kind's page (the chooser has no photos)
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#reel .tile').length === 8", 20)
    c.js("document.getElementById('reelwrap').scrollIntoView({block: 'center'})")
    case("nothing is selected to begin with, and neither bar shows", c.js(PICKED) == [] and c.js(BAR + "('reelSel')")["hidden"] and c.js(BAR + "('allSel')")["hidden"])
    # click, Shift-click, Cmd-click, Ctrl-click, Escape
    c.click(tile(2))
    case("a click on a photo selects it", c.js(PICKED) == [2], c.js(PICKED))
    look = c.js("(function(){ var t = document.querySelector(\"#reel .tile[data-n='2'] .ph\"); var a = getComputedStyle(t, '::after'), o = getComputedStyle(t);"
                " return [o.outlineStyle, o.outlineWidth, a.content, a.backgroundColor, getComputedStyle(document.documentElement).getPropertyValue('--coral-2').trim()]; })()")
    case("...with her outline and her check mark", look[0] == "solid" and look[1] == "3px" and "✓" in look[2], look)
    case("...one photo selected shows no bar (hers: 2 or more)", c.js(BAR + "('reelSel')")["hidden"])
    case("...and the order is as it was: a click moves nothing and saves nothing", c.js(ORDER) == list(range(1, 9)))
    c.click(tile(5), shift=True)
    case("Shift-click selects everything between it and the last one clicked", c.js(PICKED) == [2, 3, 4, 5], c.js(PICKED))
    bar = c.js(BAR + "('reelSel')")
    case("the bar: \"4 selected.\" in bold, her line, her five buttons in her order",
         not bar["hidden"] and bar["bold"] == "4 selected." and bar["text"].startswith("4 selected. Drag any of them and they all move together. ")
         and bar["buttons"] == ["Longer", "Quicker", "Neither", "Take them out", "Clear"], bar)
    c.click(tile(7), meta=True)
    c.click(tile(3), meta=True)
    case("Cmd-click adds one and drops one", c.js(PICKED) == [2, 4, 5, 7], c.js(PICKED))
    c.click(tile(3), ctrl=True)
    case("Ctrl-click does the same (a PC's key)", c.js(PICKED) == [2, 3, 4, 5, 7], c.js(PICKED))
    c.click(tile(8), shift=True, meta=True)
    case("Shift with Cmd adds the run to what is selected (hers)", c.js(PICKED) == [2, 3, 4, 5, 6, 7, 8], c.js(PICKED))
    c.key("Escape")
    case("Escape clears, and the bar goes", c.js(PICKED) == [] and c.js(BAR + "('reelSel')")["hidden"])
    c.click(tile(4))
    c.click(tile(4))
    case("a click on the one selected photo lets it go (hers)", c.js(PICKED) == [])
    c.click(tile(4))
    c.click(tile(6))
    case("a plain click on another photo selects that one only", c.js(PICKED) == [6])
    c.click("#photoAskIn")
    c.key("Escape")
    case("Escape while typing in a box leaves the selection alone (hers)", c.js(PICKED) == [6])
    c.js("document.activeElement.blur()")
    case("selecting saved nothing: the order on disk is as it was", saved_order(s, kit) == [(i, "") for i in range(1, 9)])

    # the bar's buttons: one save and one Undo each
    c.js("document.getElementById('reelwrap').scrollIntoView({block: 'center'})")
    c.click(tile(2))
    c.click(tile(4), shift=True)
    rev0 = rec(s, kit)["rev"]
    c.click("#reelSel button[data-s='long']")
    case("Longer marks every selected photo, and they stay selected", c.js(MARKS) == ",+,+,+,,,," and c.js(PICKED) == [2, 3, 4], c.js(MARKS))
    wait_saved(s, kit, [(1, ""), (2, "+"), (3, "+"), (4, "+"), (5, ""), (6, ""), (7, ""), (8, "")], "Longer on three saved")
    c.js("window.Reel.flush && window.Reel.flush()")
    case("...in one save", rec(s, kit)["rev"] == rev0 + 1, (rev0, rec(s, kit)["rev"]))
    c.click("#undoBtn")
    case("...and one press of Undo takes all three back", c.js(MARKS) == ",,,,,,,", c.js(MARKS))
    c.click("#reelSel button[data-s='quick']")
    case("Quicker marks them all", c.js(MARKS) == ",-,-,-,,,,", c.js(MARKS))
    c.click(tile(3), meta=True)
    c.click(tile(1), meta=True)
    c.click("#reelSel button[data-s='long']")
    case("Longer on some marked Quicker and one not: all of those selected are Longer, the one let go keeps Quicker", c.js(MARKS) == "+,+,-,+,,,,", c.js(MARKS))
    c.click("#reelSel button[data-s='plain']")
    case("Neither takes the mark off every selected photo", c.js(MARKS) == ",,-,,,,,", c.js(MARKS))
    c.click("#reelSel button[data-s='clear']")
    case("Clear lets them go and changes nothing else", c.js(PICKED) == [] and c.js(MARKS) == ",,-,,,,," and c.js(ORDER) == list(range(1, 9)))
    c.click(tile(3))
    c.click("#reel .tile[data-n='3'] .qk")
    case("(the photo's own Quicker button still works on a selected photo)", c.js(MARKS) == ",,,,,,,")
    c.key("Escape")

    # a drag of any selected photo moves them all
    c.click(tile(2))
    c.click(tile(3), shift=True)
    c.click(tile(6), meta=True)
    r1 = c.rect(tile(1))
    c.drag(tile(6), (r1["x"] + 4, r1["cy"]), steps=14, release=False)
    during = c.js("(function(){ var l = document.querySelector('.arr-lift'); return {count: l ? l.dataset.count : null, tag: l ? getComputedStyle(l, '::before').content : '',"
                  " tagShown: l ? getComputedStyle(l, '::before').display : '', riding: Array.from(document.querySelectorAll('#reel .tile.riding')).map(function(x){ return +x.dataset.n; }),"
                  " faded: Array.from(document.querySelectorAll('#reel .tile.riding')).map(function(x){ return getComputedStyle(x).opacity; }), ins: document.querySelector('.ins').classList.contains('on')}; })()")
    case("while it is dragged: her tag says 3 photos", during.get("count") == "3" and "photos" in during["tag"] and during["tagShown"] != "none", during)
    case("...the other selected photos fade (hers), and the bar shows where they will land", during["riding"] == [2, 3] and during["faded"] == ["0.3", "0.3"] and during["ins"], during)
    c.mouse_release()
    case("dropped: the whole selection lands there, in the order it had", c.js(ORDER) == [2, 3, 6, 1, 4, 5, 7, 8], c.js(ORDER))
    case("...still selected, nothing left faded, no tag left", c.js(PICKED) == [2, 3, 6] and c.count("#reel .riding") == 0 and c.count(".arr-lift") == 0)
    wait_saved(s, kit, [(n, "") for n in (2, 3, 6, 1, 4, 5, 7, 8)], "the moved order saved")
    c.click("#undoBtn")
    case("one press of Undo puts all three back where they were", c.js(ORDER) == list(range(1, 9)), c.js(ORDER))
    r8 = c.rect(tile(8))
    c.drag(tile(2), (r8["right"] - 3, r8["cy"]), steps=14)
    case("dragged by another of them, to the end: they land together at the end, in order", c.js(ORDER) == [1, 4, 5, 7, 8, 2, 3, 6], c.js(ORDER))
    c.drag(tile(3), (c.rect(tile(3))["cx"] + 30, c.rect(tile(3))["cy"]), steps=6)
    case("a drag that lands where they already are changes nothing", c.js(ORDER) == [1, 4, 5, 7, 8, 2, 3, 6])
    c.drag(tile(2), (c.rect(tile(1))["x"] + 4, c.rect(tile(1))["cy"]), steps=10, release=False)
    c.key("Escape")
    c.mouse_release()
    case("Escape in the middle of a drag puts everything back, the selection kept", c.js(ORDER) == [1, 4, 5, 7, 8, 2, 3, 6] and c.js(PICKED) == [2, 3, 6] and c.count("#reel .riding") == 0)
    c.drag(tile(5), (c.rect(tile(1))["x"] + 4, c.rect(tile(1))["cy"]), steps=10)
    case("a drag of a photo that is not selected moves that one only, as before", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 3, 6], c.js(ORDER))
    c.click("#reel .tile[data-n='3'] .x")
    case("the x on a selected photo takes it out and lets it go; the others stay selected", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6] and c.js(PICKED) == [2, 6], (c.js(ORDER), c.js(PICKED)))
    case("...and the bar counts the two that are left", c.js(BAR + "('reelSel')")["bold"] == "2 selected.", c.js(BAR + "('reelSel')"))
    c.click("#reelSel button[data-s='out']")
    case("Take them out takes every selected photo out, and nothing is selected", c.js(ORDER) == [5, 1, 4, 7, 8] and c.js(PICKED) == [] and c.js(BAR + "('reelSel')")["hidden"], c.js(ORDER))
    c.click("#undoBtn")
    case("...one press of Undo brings them all back", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6], c.js(ORDER))
    c.tap(tile(7))
    case("a finger's tap on a photo selects it too", c.js(PICKED) == [7], c.js(PICKED))
    c.key("Escape")

    # All your photos
    c.js("document.getElementById('allBox').open = true; document.getElementById('all').scrollIntoView({block: 'center'})")
    c.click(pick(9))
    case("in All your photos a plain click still adds a photo", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9] and c.js(ALLPICKED) == [], c.js(ORDER))
    c.click(pick(9))
    case("...and a second plain click still takes it out", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6])
    c.click(pick(9))
    c.click(pick(11), shift=True)
    case("Shift-click selects from the last one clicked to this one, and adds nothing", c.js(ALLPICKED) == [9, 10, 11] and c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9], (c.js(ALLPICKED), c.js(ORDER)))
    bar = c.js(BAR + "('allSel')")
    case("its bar: \"3 selected.\", her line, Add them to the end and Clear",
         not bar["hidden"] and bar["bold"] == "3 selected." and bar["text"].startswith("3 selected. Drag any of them up into your order, or ")
         and bar["buttons"] == ["Add them to the end", "Clear"], bar)
    look = c.js("(function(){ var t = document.querySelector(\"#all .pick[data-n='10']\"); return [getComputedStyle(t).outlineStyle, getComputedStyle(t, '::after').content]; })()")
    case("...each with her outline and check mark", look[0] == "solid" and "✓" in look[1], look)
    c.click("#allSel button[data-a='add']")
    case("Add them to the end: they go to the end in the shoot's order (one already in moves there), and nothing stays selected",
         c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9, 10, 11] and c.js(ALLPICKED) == [] and c.js(BAR + "('allSel')")["hidden"], c.js(ORDER))
    c.click("#undoBtn")
    case("...one press of Undo takes that back", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9], c.js(ORDER))
    c.click(pick(12), meta=True)
    c.click(pick(3), meta=True)
    c.click(pick(1), meta=True)
    case("Cmd-click selects one at a time, and adds nothing", c.js(ALLPICKED) == [1, 3, 12] and c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9])
    c.click(pick(3), meta=True)
    case("...and drops one", c.js(ALLPICKED) == [1, 12])
    c.click("#allSel button[data-a='clear']")
    case("Clear lets them go and adds nothing", c.js(ALLPICKED) == [] and c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9])
    c.click(pick(12), meta=True)
    c.click(pick(3), meta=True)
    c.click(pick(1), ctrl=True)
    c.js("window.scrollTo(0, document.getElementById('reelwrap').getBoundingClientRect().top + window.scrollY - 120)")
    r5 = c.rect(tile(4))
    c.drag(pick(12), (r5["x"] + 4, r5["cy"]), steps=16, release=False, check=False)
    during = c.js("(function(){ var l = document.querySelector('.arr-lift'); return {count: l ? l.dataset.count : null, tag: l ? getComputedStyle(l, '::before').content : ''}; })()")
    case("dragging one of them up: her tag says 3 photos", during.get("count") == "3" and "photos" in during["tag"], during)
    c.mouse_release()
    case("dropped in the order: all three land there in the shoot's order (the one already in moves), and nothing below stays selected",
         c.js(ORDER) == [5, 1, 3, 12, 4, 7, 8, 2, 6, 9] and c.js(ALLPICKED) == [], c.js(ORDER))
    wait_saved(s, kit, [(n, "") for n in (5, 1, 3, 12, 4, 7, 8, 2, 6, 9)], "the three added saved")
    c.click("#undoBtn")
    case("...one press of Undo takes all three back out", c.js(ORDER) == [5, 1, 4, 7, 8, 2, 6, 9], c.js(ORDER))
    r = rec(s, kit)
    case("what is selected is the page's own: nothing of it is in the record", "picked" not in json.dumps(r) and set(r["saved"]) <= {"picks", "mine", "mine_picks", "song", "vibe", "footage", "style", "sel", "ask", "feel", "photo_ask", "kind", "updated"}, sorted(r["saved"]))
    many = c.js("(function(){ var M = window.ReelModel, l = [{n:1,h:''},{n:2,h:'+'},{n:3,h:''},{n:4,h:'-'}];"
                " var f = function(x){ return x.map(function(r){ return r.n + r.h; }).join(' '); };"
                " return [f(M.many(l, [2,4], 0)), f(M.many(l, [2,4], 4)), f(M.many(l, [2,4], 3)), M.many(l, [1,2], 0) === l, M.many(l, [2,3], 3) === l,"
                " f(M.many(l, [7,2,9], 1, {9: '-'})), f(M.many(l, [4,1], 2)), f(M.many(l, [8], 99))]; })()")
    case("the rule itself: several to one place keep their marks and their order, new ones come in with the mark last given, the rest stay in order",
         many == ["2+ 4- 1 3", "1 3 2+ 4-", "1 3 2+ 4-", True, True, "1 7 2+ 9- 3 4-", "2+ 4- 1 3", "1 2+ 3 4- 8"], many)
    case("no fault on the page", not c.page_errors(), c.page_errors())
    # a phone's width
    c.click(tile(5))
    c.click(tile(4), shift=True)
    c.phone(375, 800)
    c.reload()
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#reel .tile').length === 8", 20)
    case("after a reload nothing is selected: a selection is the page's own and is never kept", c.js(PICKED) == [] and c.js(BAR + "('reelSel')")["hidden"])
    c.desktop()
    c.reload()
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#reel .tile').length === 8", 20)
    c.js("document.getElementById('reelwrap').scrollIntoView({block: 'center'})")
    c.click(tile(5))
    c.click(tile(6), shift=True)
    c.phone(375, 800)
    wide = c.js("[document.documentElement.scrollWidth, document.getElementById('reelSel').getBoundingClientRect().right, document.getElementById('reelSel').hidden]")
    case("at a phone's width the bar and its five buttons fit, and nothing makes the page scroll sideways", wide[0] <= 375 and wide[1] <= 375 and wide[2] is False, wide)
    c.desktop()


def run_full(c, s):
    """More than a reel holds: nothing is added, the line says so, the selection is kept."""
    kit = BIG_KIT
    s.make_kit(kit, photos=44)
    reel_state(s, kit)
    code, r = save(s, kit, {"picks": picks(38), "mine": True})
    case("(set up: an order of 38, the reel holds 40)", code == 200, r)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=photos"))
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('#reel .tile').length === 38", 30)
    c.js("document.getElementById('allBox').open = true; document.getElementById('all').scrollIntoView({block: 'end'})")
    c.click(pick(41), meta=True, check=False)
    c.click(pick(43), shift=True, check=False)
    case("(three photos not in the reel are selected below)", c.js(ALLPICKED) == [41, 42, 43], c.js(ALLPICKED))
    c.click("#allSel button[data-a='add']")
    case("Add them to the end past what a reel holds: none is added, the line under the reel says why, they stay selected",
         c.count("#reel .tile") == 38 and c.js("document.getElementById('limit').classList.contains('on')") and c.js(ALLPICKED) == [41, 42, 43],
         (c.count("#reel .tile"), c.js(ALLPICKED)))
    c.click(pick(43), meta=True, check=False)
    c.click("#allSel button[data-a='add']")
    case("two fit: both are added and the line goes", c.js(ORDER)[-3:] == [38, 41, 42] and not c.js("document.getElementById('limit').classList.contains('on')"), c.js(ORDER)[-3:])
    case("no fault on the page", not c.page_errors(), c.page_errors())


# ---------- the trim panel, on the page ----------

def make_long(folder, secs=40):
    """A 40-second clip, 320 x 180 at 10 pictures a second with a tone (the Mac's own AVFoundation, as
    tests/video_check.py makes its clips): long enough for the 20-second window and the 15-second limit."""
    import video_check as vc
    folder.mkdir(parents=True, exist_ok=True)
    cols = ";".join(",".join(map(str, c)) for c in vc.COLOURS)
    pic, wav, m4a, out = folder / "picture.mov", folder / "tone.wav", folder / "tone.m4a", folder / "long.mov"
    vc.js("picture", str(pic), "320", "180", str(secs), "10", cols, timeout=300)
    vc.tone_wav(wav, secs=float(secs), loud_at=secs / 2.0, rate=22050)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], capture_output=True, check=True)
    vc.js("compose", str(pic), str(m4a), str(out), "0", vc.RECORDED, timeout=300)
    for p in (pic, wav, m4a):
        p.unlink()
    return out


TRIM = "window.Reel.trim()"
SAY = "document.getElementById('trimSay').textContent"
OPEN = "!document.getElementById('trim').hidden"


def x_of(c, sec):
    r, tr = c.rect("#trimBar"), c.js(TRIM)
    return r["x"] + (sec - tr["w0"]) / (tr["w1"] - tr["w0"]) * r["w"], r["cy"]


def handle(c, which):
    r = c.rect("#trimSel .h." + which)
    return r["cx"], r["cy"]


def near(a, b, by=0.051):
    return abs(a - b) <= by


def open_trim(c):
    c.js("document.querySelector('.mom').scrollIntoView({block: 'center'})")
    c.click(".mom .tr")
    c.wait_for(OPEN, 5)


def run_trim(c, s, clip):
    import reel_page as rp
    kit = "2026-10-01 The long clip"
    k = s.make_kit(kit, photos=8)
    (k / "Footage").mkdir()
    shutil.copyfile(str(clip), str(k / "Footage" / "long.mov"))
    reel_state(s, kit)
    save(s, kit, {"picks": picks(6), "mine": True, "footage": True})
    j = wait_videos(s, kit)
    v = ((j or {}).get("videos") or [{}])[0]
    case("(set up: the 40-second clip, ready, a still every 2 seconds)", v.get("length") == 40.0 and v.get("preview") == "ready" and len(v.get("strip") or []) == 20, v)
    code, r = moment(s, {"kit": kit, "do": "add", "video": v.get("key"), "start": 20.0, "seconds": 4.0})
    mid = ((r or {}).get("moments") or [{}])[0].get("id")
    case("(set up: a clip of theirs, 0:20 to 0:24)", code == 200 and mid, r)
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=bts"))     # v27: the clips are on a behind-the-scenes page
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('.mom').length === 1", 20)
    case("the trim panel is there and hidden until asked for", c.js("document.getElementById('trim').hidden") is True)
    card = c.js("(function(){ var m = document.querySelector('.mom'), b = m.querySelector('.tr'); return {text: b.textContent, title: b.title,"
                " order: Array.from(m.querySelectorAll('.len button')).map(function(x){ return x.className; }), say: document.getElementById('momentsSay').textContent}; })()")
    case("each clip card has her Trim button, after - and + and before Remove", card["text"] == "✂ Trim" and card["title"] == "Trim the start and the end" and card["order"] == ["ls", "lg", "tr", "rm"], card)
    case("the line over the cards names Trim (her v25 line)", card["say"].endswith(TAIL), card["say"])
    c.js("document.querySelector('.mom').scrollIntoView({block: 'center'})")
    c.click(".mom .lg")
    chrome_drive.wait_until(lambda: (the_moment(s, kit, mid) or {}).get("end") == 24.5, 8, what="plus saved")
    c.click(".mom .ls")
    chrome_drive.wait_until(lambda: (the_moment(s, kit, mid) or {}).get("end") == 24.0, 8, what="minus saved")
    case("- and + still work as quick length buttons (half a second)", the_moment(s, kit, mid)["end"] == 24.0)
    c.wait_for("document.querySelectorAll('.mom').length === 1 && !!document.querySelector('.mom .tr')", 5)

    open_trim(c)
    tr = c.js(TRIM)
    case("Trim opens the panel on that clip, named for it", tr["id"] == mid and c.text("#trimName") == "Your pick at 0:20" and c.js("document.getElementById('trim').getAttribute('role')") == "dialog", tr)
    case("the timeline shows about 8 seconds either side of the clip (0:12 to 0:32)", (tr["w0"], tr["w1"], tr["a"], tr["b"]) == (12, 32, 20, 24), tr)
    words = c.js("(function(){ var t = document.getElementById('trim'); return {hint: t.querySelector('.hint').textContent, ticks: Array.from(document.querySelectorAll('#trimTicks span')).map(function(x){ return x.textContent; }),"
                 " nudges: Array.from(t.querySelectorAll('.nudges > span')).map(function(x){ return x.firstChild.textContent.trim(); }), titles: Array.from(t.querySelectorAll('[data-n]')).map(function(x){ return x.title; }),"
                 " handles: Array.from(t.querySelectorAll('[data-h]')).map(function(x){ return x.title; }), play: document.getElementById('trimPlay').textContent,"
                 " acts: Array.from(t.querySelectorAll('.acts button')).map(function(x){ return x.textContent; }), x: document.getElementById('trimX').getAttribute('aria-label')}; })()")
    case("her words on it: the hint, Start and End with their quarter-second arrows, Play it again, Cancel and Done, Close",
         words["hint"] == rp.TRIM_WORDS["trim_hint"] and words["nudges"] == ["Start", "End"]
         and words["titles"] == ["A quarter second earlier", "A quarter second later"] * 2 and words["handles"] == ["Where it starts", "Where it ends"]
         and words["play"] == "▶ Play it again" and words["acts"] == ["Cancel", "Done"] and words["x"] == "Close", words)
    case("her readout: where it starts, where it ends, how long", c.js(SAY) == "Starts 0:20.0 · ends 0:24.0 · 4.0 s" and c.count("#trimSay b") == 3, c.js(SAY))
    case("the times under the timeline run from its start to its end", words["ticks"] == ["0:12", "0:17", "0:22", "0:27", "0:32"], words["ticks"])
    c.wait_for("Array.from(document.querySelectorAll('#trimFilm img')).every(function(i){ return i.complete; })", 10)
    film = c.js("Array.from(document.querySelectorAll('#trimFilm img')).map(function(i){ return [i.naturalWidth > 0, Math.round(parseFloat(i.style.left)), Math.round(parseFloat(i.style.width))]; })")
    case("the filmstrip: the video's own stills, one every 2 seconds, each where its moment is",
         len(film) == 12 and all(x[0] for x in film) and [x[1] for x in film] == list(range(-10, 110, 10)) and all(x[2] == 10 for x in film), film)
    box = c.js("(function(){ var b = document.getElementById('trimBar').getBoundingClientRect(), s = document.getElementById('trimSel').getBoundingClientRect(),"
               " l = document.getElementById('trimDimL').getBoundingClientRect(), r = document.getElementById('trimDimR').getBoundingClientRect();"
               " return [(s.left - b.left) / b.width, s.width / b.width, l.width / b.width, (r.left - b.left) / b.width, getComputedStyle(document.getElementById('trimSel')).borderTopColor,"
               " getComputedStyle(document.documentElement).getPropertyValue('--coral').trim()]; })()")
    case("the kept part is outlined over its stretch of the timeline, the rest dimmed", near(box[0], 0.4, 0.01) and near(box[1], 0.2, 0.01) and near(box[2], 0.4, 0.01) and near(box[3], 0.6, 0.01), box)
    c.wait_for("(function(){ var v = document.getElementById('trimVid'); return v.readyState >= 2 && !v.paused && v.currentTime >= 19.9; })()", 10)
    vid = c.js("(function(){ var v = document.getElementById('trimVid'); return {t: v.currentTime, paused: v.paused, muted: v.muted, vol: v.volume, hidden: v.hidden, no: document.getElementById('trimNoVid').hidden, w: v.videoWidth}; })()")
    case("the clip plays in the panel from its start, with sound", 19.9 <= vid["t"] <= 24.1 and not vid["paused"] and vid["muted"] is False and vid["vol"] > 0 and not vid["hidden"] and vid["no"] and vid["w"] == 320, vid)
    c.js("document.getElementById('trimVid').currentTime = 23.8")
    case("...on a loop: at its end it goes back to its start", c.wait_for("(function(){ var t = document.getElementById('trimVid').currentTime; return t >= 19.9 && t < 22; })()", 6, tell=False) is not False,
         c.js("document.getElementById('trimVid').currentTime"))
    case("the player is not asked to loop the whole video", c.js("document.getElementById('trimVid').loop") is False)

    # the quarter-second buttons
    c.click("#trim [data-n='a:0.25']")
    case("Start, later: a quarter second", c.js(SAY) == "Starts 0:20.3 · ends 0:24.0 · 3.8 s" and c.js(TRIM)["a"] == 20.25, c.js(SAY))
    c.click("#trim [data-n='a:-0.25']")
    c.click("#trim [data-n='a:-0.25']")
    case("Start, earlier, twice", c.js(TRIM)["a"] == 19.75 and c.js(TRIM)["b"] == 24, c.js(TRIM))
    c.click("#trim [data-n='b:0.25']")
    c.click("#trim [data-n='b:-0.25']")
    c.click("#trim [data-n='b:-0.25']")
    case("End, later then earlier twice", c.js(TRIM)["b"] == 23.75 and c.js(SAY) == "Starts 0:19.8 · ends 0:23.8 · 4.0 s", c.js(SAY))
    # the handles
    c.drag(handle(c, "a"), x_of(c, 18), steps=8)
    tr = c.js(TRIM)
    case("dragging the start handle moves where it starts, and only that", near(tr["a"], 18) and tr["b"] == 23.75, tr)
    c.drag(handle(c, "b"), x_of(c, 26), steps=8)
    tr = c.js(TRIM)
    case("dragging the end handle moves where it ends, and only that", near(tr["b"], 26) and near(tr["a"], 18), tr)
    grid = round(tr["a"] * 20, 6) % 1 == 0 and round(tr["b"] * 20, 6) % 1 == 0
    case("...in twentieths of a second (hers)", grid, tr)
    c.drag(handle(c, "a"), x_of(c, 31), steps=8)
    tr = c.js(TRIM)
    case("the start can't come closer than a second to the end", near(tr["b"] - tr["a"], 1.0, 0.001) and near(tr["b"], 26), tr)
    c.drag(handle(c, "a"), x_of(c, 12.5), steps=8)
    c.drag(handle(c, "b"), x_of(c, 32), steps=8)
    tr = c.js(TRIM)
    case("...and a clip is never longer than 15 seconds", near(tr["a"], 12.5) and near(tr["b"] - tr["a"], 15.0, 0.001), tr)
    c.drag(handle(c, "a"), x_of(c, 20), steps=8)
    c.drag(handle(c, "b"), x_of(c, 24), steps=8)
    a0, b0 = c.js(TRIM)["a"], c.js(TRIM)["b"]
    c.drag(x_of(c, 22), x_of(c, 27), steps=8)
    tr = c.js(TRIM)
    case("dragging the middle slides the whole clip and keeps its length", near(tr["a"], a0 + 5, 0.11) and near((tr["b"] - tr["a"]), (b0 - a0), 0.001), (a0, b0, tr))
    c.wait_for("!document.getElementById('trimVid').paused", 5)
    case("after a drag it plays again from the new start", c.js("(function(){ var v = document.getElementById('trimVid'), t = window.Reel.trim(); return !v.paused && v.currentTime >= t.a - 0.31 && v.currentTime <= t.b + 0.1; })()"))
    held = rec_bytes(s, kit)
    case("nothing is saved while the panel is open", (the_moment(s, kit, mid)["start"], the_moment(s, kit, mid)["end"]) == (20.0, 24.0))
    # the four ways out that save nothing
    c.click("#trimCancel")
    case("Cancel closes it and saves nothing", not c.js(OPEN) and rec_bytes(s, kit) == held and c.js("document.getElementById('trimVid').paused"))
    open_trim(c)
    case("opened again it shows the clip as saved, not what was let go", (c.js(TRIM)["a"], c.js(TRIM)["b"]) == (20, 24))
    c.click("#trim [data-n='a:0.25']")
    c.click("#trimX")
    case("the x closes it and saves nothing", not c.js(OPEN) and rec_bytes(s, kit) == held)
    open_trim(c)
    c.click("#trim [data-n='b:0.25']")
    c.key("Escape")
    case("Escape closes it and saves nothing", not c.js(OPEN) and rec_bytes(s, kit) == held)
    open_trim(c)
    c.click("#trim [data-n='b:0.25']")
    c.click((6, 6))
    case("a click outside the panel closes it and saves nothing", not c.js(OPEN) and rec_bytes(s, kit) == held)
    # Done
    open_trim(c)
    c.drag(handle(c, "a"), x_of(c, 18.5), steps=8)
    c.drag(handle(c, "b"), x_of(c, 26), steps=8)
    tr = c.js(TRIM)
    said = c.js(SAY)
    c.click("#trimDone")
    chrome_drive.wait_until(lambda: (the_moment(s, kit, mid) or {}).get("start") != 20.0, 8, what="the trim saved")
    m = the_moment(s, kit, mid)
    case("Done saves where it starts and where it ends, and closes the panel", not c.js(OPEN) and near(m["start"], tr["a"], 0.006) and near(m["end"], tr["b"], 0.006) and m.get("set") is True, (m, tr))
    case("...what the readout said is what was saved", said == "Starts 0:%04.1f · ends 0:%04.1f · %.1f s" % (m["start"], m["end"], m["end"] - m["start"]), (said, m))
    c.wait_for("!!document.querySelector('.mom .len b') && document.querySelector('.mom .len b').textContent === '%.1f s'" % (m["end"] - m["start"]), 8)
    case("...and the card shows the new length", c.text(".mom .len b") == "%.1f s" % (m["end"] - m["start"]), c.text(".mom .len b"))
    case("...the version before is kept beside the record", (rec(s, kit, "reel-page.prev.json") or {}).get("moments", [{}])[0].get("start") == 20.0)
    # never past the video's ends
    for _ in range(3):
        c.wait_for("!!document.querySelector('.mom .tr')", 5)
        open_trim(c)
        tr = c.js(TRIM)
        c.drag(x_of(c, (tr["a"] + tr["b"]) / 2), (c.rect("#trimBar")["right"] + 300, c.rect("#trimBar")["cy"]), steps=10)
        want = c.js(TRIM)["b"]
        c.click("#trimDone")
        chrome_drive.wait_until(lambda: near((the_moment(s, kit, mid) or {}).get("end", 0), want, 0.006), 8, what="the slid trim saved")
        time.sleep(0.7)                       # the card plays its new length a moment after a change (hers)
    c.wait_for("!!document.querySelector('.mom .tr')", 5)
    open_trim(c)
    tr = c.js(TRIM)
    case("slid to the very end of the video: it ends at 0:40 and no later, its length kept", tr["b"] == 40 and tr["w1"] == 40 and tr["len"] == 40 and near(tr["b"] - tr["a"], 7.5, 0.001), tr)
    c.click("#trim [data-n='b:0.25']")
    case("the End arrow can't push it past the video's end", c.js(TRIM)["b"] == 40)
    c.drag(x_of(c, 36), (c.rect("#trimBar")["x"] - 300, c.rect("#trimBar")["cy"]), steps=10)
    tr = c.js(TRIM)
    case("...and slid back the other way it keeps its length and never starts before the video does", tr["a"] >= 0 and near(tr["b"] - tr["a"], 7.5, 0.001) and tr["b"] < 40, tr)
    c.key("Escape")
    case("no fault on the page", not c.page_errors(), c.page_errors())
    c.phone(375, 800)
    c.reload()
    c.wait_for("window.Reel && window.Reel.state() && !!document.querySelector('.mom .tr')", 20)
    c.js("document.querySelector('.mom .tr').click()")       # at once, before the page has its list of videos: it opens when the list is here
    c.wait_for(OPEN, 5)
    c.key("Escape")
    was = c.js("document.documentElement.scrollWidth")
    c.js("document.querySelector('.mom .tr').click()")
    c.wait_for(OPEN, 5)
    wide = c.js("(function(){ var b = document.querySelector('#trim .box').getBoundingClientRect(), t = document.getElementById('trim').getBoundingClientRect();"
                " return [document.documentElement.scrollWidth, b.left - t.left, t.right - b.right, t.right - document.getElementById('trimDone').getBoundingClientRect().right,"
                " t.right - document.querySelector('#trim .nudges').getBoundingClientRect().right]; })()")
    case("at a phone's width the panel, its arrows and its buttons sit inside the window, and opening it makes the page no wider",
         wide[0] == was and wide[1] >= 0 and wide[2] >= 0 and wide[3] >= 0 and wide[4] >= 0, (was, wide))
    c.desktop()


def run_trim_pc(c, s, clip):
    """The same panel where no stills can be taken from a video (a PC; here ASSISTANT_NO_AVFOUNDATION=1), on a
    shoot that only ever met that computer."""
    import reel_page as rp
    s.stop()
    s.env["ASSISTANT_NO_AVFOUNDATION"] = "1"
    s.start()
    kit = "2026-10-02 On a PC"
    k = s.make_kit(kit, photos=8)
    (k / "Footage").mkdir()
    shutil.copyfile(str(clip), str(k / "Footage" / "long.mov"))
    shutil.copyfile(str(FIXTURE), str(k / "Footage" / "phone.mp4"))
    reel_state(s, kit)
    save(s, kit, {"picks": picks(6), "mine": True, "footage": True})
    j = wait_videos(s, kit, 2)
    # the second video is one a PC can't play: its facts said to be an iPhone's High Efficiency video
    fj = k / ".kit" / "footage" / "facts.json"
    facts = json.loads(fj.read_text(encoding="utf-8"))
    pk = next(v["key"] for v in j["videos"] if v["name"] == "phone.mp4")
    lk = next(v["key"] for v in j["videos"] if v["name"] == "long.mov")
    facts[pk] = dict(facts[pk], codec="hvc1", codec_name="hevc", bits=10, plays_as_is=False)
    fj.write_text(json.dumps(facts), encoding="utf-8")
    s.stop()
    s.start()
    j = wait_videos(s, kit, 2)
    states = {v["name"]: (v["preview"], len(v["strip"])) for v in j["videos"]}
    case("(set up: as a PC has it, one video plays as it is with no stills, the other can't be played)",
         states.get("long.mov") == ("ready", 0) and states.get("phone.mp4", ("",))[0] in ("pc", "hevc_pc"), states)
    code, r = moment(s, {"kit": kit, "do": "add", "video": lk, "start": 20.0, "seconds": 4.0})
    mid = ((r or {}).get("moments") or [{}])[0].get("id")
    code2, r2 = moment(s, {"kit": kit, "do": "add", "video": pk, "start": 0.5, "seconds": 1.5})
    other = next((m["id"] for m in (r2 or {}).get("moments") or [] if m["id"] != mid), None)
    case("(set up: a clip from each)", code == 200 and code2 == 200 and mid and other, (r, r2))
    c.open(s.url("/reel.html" + s.q(kit) + "&kind=bts"))
    c.wait_for("window.Reel && window.Reel.state() && document.querySelectorAll('.mom').length === 2", 20)
    note = c.js("(function(){ var n = document.getElementById('trimPcNote'); return n ? n.textContent : null; })()")
    case("a PC's panel has our line under the timeline: no pictures along it yet", note == rp.OUR_WORDS["trim_no_stills_pc"], note)
    c.js("document.querySelector('.mom[data-id=\"%s\"]').scrollIntoView({block: 'center'})" % mid)
    c.click(".mom[data-id='%s'] .tr" % mid)
    c.wait_for(OPEN, 5)
    c.wait_for("document.getElementById('trimVid').readyState >= 1", 10)
    got = c.js("(function(){ var v = document.getElementById('trimVid'); return {film: document.querySelectorAll('#trimFilm img').length, vid: !v.hidden && v.videoWidth > 0, no: document.getElementById('trimNoVid').hidden,"
               " noteShown: document.getElementById('trimPcNote').getBoundingClientRect().height > 0, say: document.getElementById('trimSay').textContent}; })()")
    case("...the timeline has no pictures, the note shows, and a video that plays still plays in the panel",
         got["film"] == 0 and got["vid"] and got["no"] and got["noteShown"] and got["say"] == "Starts 0:20.0 · ends 0:24.0 · 4.0 s", got)
    c.click("#trim [data-n='a:0.25']")
    c.drag(handle(c, "b"), x_of(c, 27), steps=8)
    tr = c.js(TRIM)
    c.click("#trimDone")
    chrome_drive.wait_until(lambda: (the_moment(s, kit, mid) or {}).get("start") == 20.25, 8, what="the PC trim saved")
    case("...and the handles, the arrows and Done work the same", the_moment(s, kit, mid)["start"] == 20.25 and near(the_moment(s, kit, mid)["end"], tr["b"], 0.006) and near(tr["b"], 27), (tr, the_moment(s, kit, mid)))
    c.wait_for("!!document.querySelector('.mom[data-id=\"%s\"] .tr')" % other, 5)
    time.sleep(0.7)
    c.js("document.querySelector('.mom[data-id=\"%s\"]').scrollIntoView({block: 'center'})" % other)
    c.click(".mom[data-id='%s'] .tr" % other)
    c.wait_for(OPEN, 5)
    got = c.js("(function(){ var v = document.getElementById('trimVid'), n = document.getElementById('trimNoVid'); return {vid: v.hidden, no: n.hidden, words: n.textContent, say: document.getElementById('trimSay').textContent}; })()")
    case("a video that can't be played here: the panel says so in our words, never that a preview is still being made, and the timeline still works",
         got["vid"] is True and got["no"] is False and got["words"] == rp.OUR_WORDS["trim_stuck"] and got["say"] == "Starts 0:00.5 · ends 0:02.0 · 1.5 s", got)
    c.click("#trim [data-n='b:0.25']")
    c.click("#trimDone")
    chrome_drive.wait_until(lambda: (the_moment(s, kit, other) or {}).get("end") == 2.25, 8, what="the trim of the unplayable clip saved")
    case("...and Done saves it", the_moment(s, kit, other)["end"] == 2.25)
    case("no fault on the page", not c.page_errors(), c.page_errors())
    s.stop()
    s.env.pop("ASSISTANT_NO_AVFOUNDATION", None)
    s.start()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-chrome", action="store_true", help="the checks that need no browser only")
    ap.add_argument("--only", choices=("select", "trim", "pc"), help="one part only: selecting; or (trim, pc) the retired panel's checks, which need no browser")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = t.real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="trim-select-check-", dir=str(base) if base else ("/private/tmp" if t.MAC else None))).resolve()
    s = t.Setup(work, a.port)
    s.env["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"       # no folder window, no picker, no CapCut, whatever a test presses
    s.env["STUDIO_CARD_FOR_TESTS"] = "none"
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    s.make()
    try:
        s.make_kit(KIT, photos=6)
        group("her words: the Trim button, the panel, the two bars", run_words, s)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("a trim, by request", run_request, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            t.skip("selecting several and the trim panel on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            if a.only in (None, "select"):
                with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1000)) as c:
                    group("selecting several photos, on the page", run_select, c, s)
                with chrome_drive.Chrome(work=str(work / "chrome"), size=(1280, 1000)) as c:
                    group("more than a reel holds", run_full, c, s)
            if a.only != "select":
                t.skip("the trim panel on the page: retired with Nicole's v27 (the trim is on the editor's timeline: tests/reel_footage_check.py --only editor); "
                       "run_trim and run_trim_pc stay below for the day it is put back (TRIM_PANEL)")
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
