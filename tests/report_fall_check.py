#!/usr/bin/env python3
"""The backup report's animation (Nicole's v28, section 6 "The backup report"): on a report where everything is
safe and there are pictures, the numbers count up from zero while photos fall into the files box, with
"Play it again" under the numbers.

    python3 tests/report_fall_check.py [--port 9000] [--work <a folder to keep the run in>] [--no-chrome]

What it checks:
  * the pages as written, on pretend backups made here with no add-on: which reports get the animation (a whole
    backup, all safe, with pictures) and which never do (a sample, a problem, not finished, no pictures, one card
    of a shoot, the shoot's own page); the real numbers are in the page as written either way; the pictures are
    only the report's own, by addresses beside the report, never a place on the drive
  * the real page in a hidden Chrome: the numbers start at zero and end exactly as written, a screen reader has
    the real ones throughout, photos 92 px tall fall and are gone at the end, the files box glows, Play it again,
    no replay on a reload, nothing at all with reduced motion, a page put behind something shows the real
    numbers at once, a phone's width

Nothing under ~/.studio is touched (STUDIO_HOME is a scratch folder), no window is ever opened, the servers are
the test's own on 127.0.0.1 and are stopped before it ends.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/the-engine/skills/studio-manager/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import report_v26_check as R  # noqa: E402  (its pretend backups and its report server)

RAW6 = ["cr3"] * 6


def data_of(html_text):
    """What the animation's script was handed, or None when the page has no animation."""
    m = re.search(r"var D=(\{.*?\}), box=document\.querySelector\('\.stats'\)", html_text)
    return json.loads(m.group(1)) if m else None


def stats_of(html_text):
    return re.findall(r"<div class='stat'><b>(.*?)</b>", html_text)


def rewrite(night, change):
    """Change a pretend backup's manifest and build its report again."""
    f = Path(night) / "_studio" / "manifest.json"
    m = json.loads(f.read_text(encoding="utf-8"))
    change(m)
    f.write_text(json.dumps(m), encoding="utf-8")
    code, said = R.run("report_page.py", str(night))
    assert code == 0, said
    return R.page(night)


def her_diff():
    roots = [ROOT / "reference-private"]
    try:
        import subprocess
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except Exception:  # noqa: BLE001
        pass
    for r in roots:
        for f in sorted(r.glob("nicole-handoff-v28-*/Carousel designer and reel picker/plugin-changes/report_page-since-v26.diff")):
            return f
    return None


# ---------------------------------------------------------------- the pages, as written

def check_pages(work):
    import report_page
    good = R.make_backup(work / "2026-06-25 all good", [
        {"name": "Beach", "day": "2026-06-24", "n": 12, "ext": "cr3", "peeks": RAW6},
        {"name": "Palm grove", "day": "2026-06-25", "n": 10, "ext": "cr3", "peeks": RAW6}])
    p = R.page(good)
    d = data_of(p)
    studio = good / "_studio"
    case("a whole backup, all safe, with pictures: the report has the animation", d is not None and len(d["pics"]) == 18, d)
    case("the numbers in the page as written are the real ones (22 files, checked 22, 7 min)",
         stats_of(p)[0] == "22" and stats_of(p)[2] == "22" and stats_of(p)[3] == "7 min" and len(stats_of(p)) == 4, stats_of(p))
    case("the pictures are the groups' previews first, then the sneak peeks",
         bool(d) and [u.split("/")[0] for u in d["pics"]] == ["groups"] * 6 + ["sneak-peeks"] * 12)
    import urllib.parse
    case("every picture is a file beside the report, in a folder the report already shows pictures from",
         bool(d) and all((studio / urllib.parse.unquote(u)).is_file() and not u.startswith(("/", "http", "file")) and ".." not in u for u in d["pics"]))
    script = p[p.index("var D="):p.index("</script>", p.index("var D="))]
    case("no place on the drive is in what the script is handed", str(work) not in script and "/Volumes" not in script and "file:" not in script)
    case("the button's words are hers: Play it again", bool(d) and d["again"] == "Play it again" == report_page.FALL_WORDS["again"])
    diff = her_diff()
    if diff:
        case("her own file has that line too", "Play it again" in diff.read_text(encoding="utf-8"))
    else:
        R.skip("her v28 pack is not on this computer (reference-private is never pushed)")
    js, css = report_page.FALL_JS, report_page.FALL_CSS
    case("it stands down for reduced motion before it changes anything", js.index("prefers-reduced-motion: reduce") < js.index("box.classList.add('falls')"))
    case("nothing in it says Claude, has an em dash, or names an address on the internet", not any(x in js + css for x in ("Claude", "—", "http://", "https://", "//fonts")))
    case("the photos are 92 px tall, normal-shaped, and never take a press", ".fallp{" in css and "height:92px" in css and "pointer-events:none" in css and "width:auto" in css)
    case("the page still loads nothing from the internet", not re.search(r"(src|href)=['\"]https?://", p))

    # the ones that never play
    p = rewrite(R.make_backup(work / "2026-06-25 sample", [{"name": "Beach", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6}]),
                lambda m: m.update(sample={"kept": 8, "of": 3931}))
    case("a sample backup: no animation, and the numbers simply show", data_of(p) is None and "fall-again" not in p.split("</style>")[1] and stats_of(p)[0] == "8"
         and "A sample: 8 of the 3,931" in p)
    p = rewrite(R.make_backup(work / "2026-06-25 problem", [{"name": "Beach", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6}]),
                lambda m: m.update(problems=["One file did not match the card."]))
    case("a backup with a problem: no animation", data_of(p) is None and stats_of(p)[0] == "8" and "Something needs you" in p)

    def half(m):
        for k in list(m["files"])[:3]:
            m["files"][k]["dest"] = {"ok": False}
    p = rewrite(R.make_backup(work / "2026-06-25 half", [{"name": "Beach", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6}]), half)
    case("a backup not finished yet: no animation, and checked says 5 of 8 as it is", data_of(p) is None and stats_of(p)[0] == "8" and stats_of(p)[2] == "5")

    def second(m):
        m["second"] = "/pretend/second"
        for k in list(m["files"])[1:]:
            m["files"][k]["second"] = {"ok": True}
    p = rewrite(R.make_backup(work / "2026-06-25 second", [{"name": "Beach", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6}]), second)
    case("a second copy that is not all checked: no animation", data_of(p) is None)

    clips = R.make_backup(work / "2026-06-24 clips", [{"name": "Garden demo", "day": "2026-06-24", "n": 5, "ext": "mp4", "clips": True}])
    d = data_of(R.page(clips))
    case("a card of only video clips WITH stills: the stills fall", d is not None and len(d["pics"]) == 3 and all(u.startswith("groups/") for u in d["pics"]), d)
    for f in (clips / "_studio" / "groups").glob("*.jpg"):
        f.rename(f.with_suffix(".set-aside"))          # the stills gone (as on a PC, which takes none)
    code, said = R.run("report_page.py", str(clips))
    p = R.page(clips)
    case("a card of only video clips with NO stills: no animation, and the numbers simply show", code == 0 and data_of(p) is None and stats_of(p)[0] == "5", said[-200:])

    # no shoots and no groups yet: the card's own previews
    early = R.make_backup(work / "2026-06-25 early", [{"name": "Beach", "day": "2026-06-24", "n": 6, "ext": "cr3"}], build=False)
    es = early / "_studio"
    for f in list((es / "groups").glob("*.jpg")):
        f.unlink()                                      # (a pretend file this test made a moment ago)
    for n in ("groups.json", "shoots.json"):
        (es / n).unlink()
    (es / "previews").mkdir()
    for i in range(4):
        (es / "previews" / ("IMG_%04d.jpg" % i)).write_bytes(R.TINY_JPEG)
    code, said = R.run("report_page.py", str(early))
    d = data_of(R.page(early))
    case("no shoots sorted yet: the card's own previews fall", code == 0 and d is not None and d["pics"] == ["previews/IMG_%04d.jpg" % i for i in range(4)], d)

    # many pictures, and names that could cause trouble
    many = R.make_backup(work / "2026-06-25 many", [{"name": "Beach", "day": "2026-06-24", "n": 12, "ext": "cr3", "peeks": RAW6}], build=False)
    ms = many / "_studio"
    g = json.loads((ms / "groups.json").read_text(encoding="utf-8"))
    odd = ["g01_it's 100% #1 & more.jpg", "g01_Zoë.jpg", "g01_a<b>.jpg" if os.name != "nt" else "g01_ab.jpg"]
    extra = odd + ["g01_extra_%03d.jpg" % i for i in range(60)]
    for n in extra:
        (ms / "groups" / n).write_bytes(R.TINY_JPEG)
    g["groups"][0]["previews"] += extra + ["../manifest.json", "missing.jpg", "sub/dir.jpg", "notes.txt"]
    (ms / "groups.json").write_text(json.dumps(g), encoding="utf-8")
    code, said = R.run("report_page.py", str(many))
    p = R.page(many)
    d = data_of(p)
    case("more pictures than it flies: 40 are handed over, spread across them", code == 0 and d is not None and len(d["pics"]) == report_page.FALL_MOST == 40
         and d["pics"][0].startswith("groups/") and d["pics"][-1].startswith("sneak-peeks/"), d and len(d["pics"]))
    allp = report_page.fall_pictures(ms, most=1000)
    case("a name outside the folder, a missing file, a folder inside and a file that is not a picture are left out",
         len(allp) == 3 + 63 + 6 and not any("manifest" in u or "missing" in u or "sub" in u or "notes" in u for u in allp), len(allp))
    case("names with a quote, a percent, a hash, an accent and angle brackets are written as addresses",
         "groups/g01_it%27s%20100%25%20%231%20%26%20more.jpg" in allp and all(re.fullmatch(r"[A-Za-z0-9_.~%/-]+", u) for u in allp), [u for u in allp if "more" in u])
    body = p.split("</style>", 1)[1]
    start = body.index("var D=")
    case("nothing handed to the script can end the script early", "<" not in body[start:body.index(", box=document", start)])
    return {"good": good, "sample": work / "2026-06-25 sample", "clips": clips}


def check_cards(work):
    c1 = R.make_backup(work / "2026-06-24 Fake wedding", [
        {"name": "Getting ready", "day": "2026-06-24", "n": 8, "ext": "cr3", "peeks": RAW6}])
    c2 = R.make_backup(work / "2026-06-24 Fake wedding, card 2", [
        {"name": "Reception", "day": "2026-06-25", "hour": 19, "n": 8, "ext": "cr3", "peeks": RAW6}])
    code, said = R.run("shoot_report.py", "link", str(c1), str(c2))
    case("(two backups are linked as one shoot on two cards)", code == 0, said[-300:])
    card, shoot, own = R.page(c1, "report-card.html"), R.page(c1, "shoot-report.html"), R.page(c1)
    case("one card inside the shoot's page: no animation (its numbers simply show)", data_of(card) is None and ".fallp" not in card and stats_of(card)[0] == "8")
    case("the shoot's own page: no animation either", data_of(shoot) is None and "fall-again" not in shoot)
    case("that card's own full report, opened by itself, still has it", data_of(own) is not None)
    return c1, c2


# ---------------------------------------------------------------- the real page

STATE = """(() => { const bs = [...document.querySelectorAll('.stats .stat b')];
  return { shown: bs.map(b => { const t = b.querySelector('span[aria-hidden]'); return t ? t.textContent : b.textContent; }),
           real: bs.map(b => { const r = b.querySelector('.fall-real'); return r ? r.textContent : b.textContent; }),
           plain: bs.map(b => b.children.length === 0), fly: document.querySelectorAll('.fallp').length, stars: document.querySelectorAll('.twk').length,
           btn: (() => { const b = document.querySelector('.fall-again'); return b ? [b.textContent, b.classList.contains('on'), getComputedStyle(b).visibility] : null; })() }; })()"""
REAL = ["22", "220 bytes", "22", "7 min"]


def num(s):
    return float(re.sub(r"[^\d.]", "", s) or 0)


def check_browser(c, base, written):
    case("(the page as written has the numbers this test expects)", written[0] == "22" and written[2] == "22" and written[3] == "7 min", written)
    REAL[:] = written
    # The test says which it means, every time: a machine may itself ask for reduced motion (GitHub's Mac does),
    # and then the page, rightly, plays nothing. Never left to the computer's own setting.
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    c.clear_errors()
    c.open(base + "/report.html")
    s = c.js(STATE)
    case("it opens with every number at zero, in its own words (0, 0 bytes, 0, 0 min)",
         [num(x) for x in s["shown"]] == [0, 0, 0, 0] and s["shown"][3] == "0 min" and s["shown"][0] == "0", s["shown"])
    case("a screen reader has the real numbers from the start, and never the counting ones",
         s["real"] == REAL and c.js("[...document.querySelectorAll('.stats .stat b')].every(b => b.querySelector('span[aria-hidden=\"true\"]') && b.querySelector('.fall-real'))"), s["real"])
    h0 = c.js("document.querySelector('.stats').getBoundingClientRect().height")
    case("Play it again is not offered while it has not played", s["btn"] is not None and s["btn"][1] is False and s["btn"][2] == "hidden", s["btn"])
    c.wait_for("document.querySelectorAll('.fallp').length > 0", 12)
    t0 = time.time()
    f = c.js("(() => { const e = document.querySelector('.fallp'), i = e.querySelector('img'), cs = getComputedStyle(e);"
             " return { h: e.offsetHeight, pe: cs.pointerEvents, pos: cs.position, src: i.getAttribute('src'), alt: i.alt, hid: e.getAttribute('aria-hidden'), glow: cs.boxShadow }; })()")
    case("photos fall: each 92 px tall with a white glow, one of the report's own pictures, never taking a press, hidden from a screen reader",
         f["h"] == 92 and f["pe"] == "none" and f["pos"] == "fixed" and re.match(r"(groups|sneak-peeks)/", f["src"]) and f["hid"] == "true" and "255, 255, 255" in f["glow"], f)
    c.wait_for("document.querySelectorAll('.twk').length > 0", 8)
    case("twinkling stars trail them", True)
    seen_mid, seen_glow, most = False, False, 0
    for _ in range(400):
        s = c.js(STATE)
        most = max(most, s["fly"])
        v = num(s["shown"][0])
        if 0 < v < 22:
            seen_mid = True
        if c.js("document.querySelector('.stats .stat').classList.contains('glow')"):
            seen_glow = True
        if all(s["plain"]) and s["btn"][1]:
            break
        time.sleep(0.05)
    took = time.time() - t0
    s = c.js(STATE)
    case("the numbers pass through the middle on the way (counting, not jumping)", seen_mid)
    case("the files box glows as photos arrive", seen_glow)
    case("many photos are in the air at once", most >= 8, most)
    case("at the end the numbers are exactly the real ones, as the page was written, with nothing left inside them",
         s["shown"] == REAL and all(s["plain"]) and c.js("[...document.querySelectorAll('.stats .stat b')].map(b => b.innerHTML)") == REAL, s["shown"])
    case("every photo and star is gone at the end", s["fly"] == 0 and c.js("document.querySelectorAll('.fallp,.twk').length") in (0, 1, 2), s)
    case("it takes a few seconds, not an age (photos on screen for 4 to 10 s)", 3.5 < took < 11, round(took, 1))
    case("then: Play it again, under the numbers", s["btn"] == ["↻ Play it again", True, "visible"]
         and c.js("(() => { const b = document.querySelector('.fall-again').getBoundingClientRect(), s = document.querySelector('.stats').getBoundingClientRect(); return b.top >= s.bottom - 1 && b.right <= s.right + 1 && b.height >= 24; })()"), s["btn"])
    case("the button sits on nothing else (the words under it start lower)",
         c.js("(() => { const b = document.querySelector('.fall-again').getBoundingClientRect(); const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2); return e && e.classList.contains('fall-again'); })()"))
    c.wait_for("document.querySelectorAll('.fallp,.twk').length === 0", 5)
    c.screenshot("after.png")
    h1 = c.js("document.querySelector('.stats').getBoundingClientRect().height")
    case("the row of numbers is the same height while it counts as after (nothing under it jumps)", abs(h0 - h1) < 1, (h0, h1))

    c.click(".fall-again")
    c.wait_for("document.querySelectorAll('.fallp').length > 0", 8)
    s = c.js(STATE)
    case("Play it again: the numbers go back to zero and count again, the real ones still there for a screen reader",
         num(s["shown"][0]) < 22 and s["real"] == REAL and s["btn"][1] is False, s)
    c.wait_for("document.querySelectorAll('.fallp').length >= 6", 8)
    c.screenshot("mid.png")
    # put behind something part way: the real numbers at once, nothing left in the air
    c.js("Object.defineProperty(document, 'hidden', { get: () => true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); true")
    s = c.js(STATE)
    case("a page put behind something part way shows the real numbers at once and clears the photos", s["shown"] == REAL and all(s["plain"]) and s["fly"] == 0 and s["btn"][1], s)
    c.js("delete document.hidden; true")
    time.sleep(1.2)
    s = c.js(STATE)
    case("... and nothing starts up again afterwards by itself", s["shown"] == REAL and s["fly"] == 0, s)

    c.reload()
    time.sleep(1.5)
    s = c.js(STATE)
    case("the page reloading itself (a rename, a note written) does not play it again: the numbers stay, the button is there",
         s["shown"] == REAL and all(s["plain"]) and s["fly"] == 0 and s["btn"] and s["btn"][1], s)
    errs = c.page_errors()
    case("the page had no errors, and asked for nothing outside this computer", not errs and not c.outside_requests(), (errs, c.outside_requests())[:2])
    case("no picture it asked for was missing", not [r for r in c.requests if r.get("status") and int(r["status"]) >= 400 and re.search(r"/(groups|sneak-peeks|previews)/", r["url"])])

    # reduced motion
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    try:
        c.open(base + "/report.html")
        s0 = c.js(STATE)
        time.sleep(1.5)
        s = c.js(STATE)
        case("with reduced motion: the real numbers at once, no photos, no stars, no button", s0["shown"] == REAL and s["shown"] == REAL and all(s0["plain"]) and s["fly"] == 0
             and s["stars"] == 0 and s["btn"] is None, (s0, s))
    finally:
        c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})

    # a picture that cannot be read never flies as an empty box; with none readable the numbers simply show
    c.block_urls(["*/groups/*", "*/sneak-peeks/*"])
    try:
        c.open(base + "/report.html")
        c.wait_for("[...document.querySelectorAll('.stats .stat b')].every(b => b.children.length === 0)", 10)
        s = c.js(STATE)
        case("when no picture can be read: no animation, the real numbers show, and no button", s["shown"] == REAL and s["fly"] == 0 and s["btn"][1] is False, s)
    finally:
        c.block_urls([])

    # a phone
    c.phone(390, 844)
    try:
        c.open(base + "/report.html")
        s = c.js(STATE)
        c.js("document.querySelector('.stats').scrollIntoView({block:'center'}); true")
        c.wait_for("document.querySelectorAll('.fallp').length > 0", 12)
        case("a phone: it starts when the numbers come into view", True)
        case("... and the falling photos never make the page scroll sideways", c.js("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        c.wait_for("(() => { const b = document.querySelector('.fall-again'); return b.classList.contains('on'); })()", 20)
        s = c.js(STATE)
        case("... the numbers end as written and the button is inside the window",
             s["shown"] == REAL and c.js("(() => { const b = document.querySelector('.fall-again').getBoundingClientRect(); return b.left >= 0 && b.right <= window.innerWidth + 1; })()"), s)
        c.screenshot("phone.png")
    finally:
        c.desktop()


def check_quiet(c, sample_base, cards_base):
    c.open(sample_base + "/report.html")
    time.sleep(1.2)
    s = c.js(STATE)
    case("a sample in a browser: the numbers simply show, nothing falls, no button", s["shown"][0] == "8" and all(s["plain"]) and s["fly"] == 0 and s["btn"] is None, s)
    c.open(cards_base + "/report.html")
    c.wait_for("document.querySelectorAll('iframe.card-frame').length === 2", 15)
    c.wait_for("Array.from(document.querySelectorAll('iframe.card-frame')).every(f => f.contentDocument && f.contentDocument.querySelector('.stats'))", 20)
    time.sleep(1.5)
    q = c.js("(() => { const docs = [document, ...Array.from(document.querySelectorAll('iframe.card-frame')).map(f => f.contentDocument)];"
             " return docs.map(d => [d.querySelectorAll('.fallp,.twk,.fall-again').length, [...d.querySelectorAll('.stats .stat b')].every(b => b.children.length === 0 && /\\d/.test(b.textContent))]); })()")
    case("a shoot on two cards: nothing falls on the shoot's page or inside either card, and every number simply shows",
         len(q) == 3 and all(n == 0 and ok for n, ok in q) and c.js("document.querySelectorAll('iframe.card-frame')[0].contentDocument.querySelector('.stat b').textContent") == "8", q)


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--no-chrome", action="store_true", help="the pages as written only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 70)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="report-fall-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    R.ENV.update({"STUDIO_HOME": str(work / "studio-home"), "STUDIO_NO_WINDOWS_FOR_TESTS": "1", "STUDIO_CARD_FOR_TESTS": "none"})
    os.environ.update(R.ENV)   # nothing here may touch the real ~/.studio
    servers = []
    try:
        made = group("the pages, as written", check_pages, work)
        cards = group("a shoot on two cards", check_cards, work)
        if a.no_chrome or not chrome_drive.find_chrome():
            R.skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        elif made and cards:
            for night, port in ((made["good"], a.port), (made["sample"], a.port + 22), (cards[1], a.port + 44)):
                servers.append(R.Server(night, port))
            case("the report servers are this test's own", all(s.base and a.port <= s.port < a.port + 66 for s in servers))
            if all(s.base for s in servers):
                with chrome_drive.Chrome(work=str(work), size=(1280, 900)) as c:
                    group("the report in a browser", check_browser, c, servers[0].base, stats_of(R.page(made["good"])))
                    group("the reports that stay still, in a browser", check_quiet, c, servers[1].base, servers[2].base)
    finally:
        for s in servers:
            s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
