#!/usr/bin/env python3
"""The home page's four tiles are shortcuts (Nicole's v30, section 4; screenshots 02 and 03).

    python3 tests/guard.py 3000 python3 tests/create_dialog_check.py [--port 9980] [--work <a folder to keep>] [--no-chrome] [--shot <png>]

What it holds, on the pretend Assistant tests/home_v28_check.py builds (two pretend kits drawn with sips, a scratch
STUDIO_HOME, a pretend folder of finished photos, the folder picker answered by STUDIO_PICK_FOLDER_FOR_TESTS; nothing
of the real ~/.studio, no real kit, no /Volumes, no window on the screen):
  * + A new shoot without the page (new_shoot.py): one picked folder is ONE post kit named for the folder in their
    folder pattern, only its finished photos COPIED (every copy checked; the originals hashed before and after and
    untouched), the log written, the kit numbered; picked again it goes back to the same kit (no second kit, nothing
    copied twice); a name clash, a folder inside the Assistant's own, a folder holding it, and a folder with no
    finished photos each stop in plain words with nothing copied; with no Assistant folder yet one is made in
    Pictures (a pretend one); the routes refuse another website and never send a path;
  * in a HIDDEN Chrome: each tile opens its own title (Create a reel / a carousel / your stories, Write your captions,
    the last word in her accent) with "Which shoot do you want to make it from?"; + A new shoot on top; Your shoots
    with My vault first, then every post kit newest first (small photo, name, date, number of photos); the search
    box only from 7 shoots, and what it finds; no post kits: only + A new shoot and "Start with a shoot..."; closed
    by x, a press outside and Escape; each shoot landing on its page (the reel page's chooser, the carousel designer,
    the stories designer, the words page), My vault on its own reel page or its post kit page; + A new shoot making
    the kit and landing on the page that was tapped, a second time landing on the same kit; a closed picker changing
    nothing;
  * Captions asks "Captions for a reel or a carousel?" [Reel] [Carousel] once the shoot is picked (Nicole, Nov 22),
    from a shoot, from My vault (its own words page, which really opens) and from + A new shoot, and lands on the
    words page's tab they chose.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only; a Mac.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, urlsplit, parse_qs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import home_v28_check as v28  # noqa: E402

TODAY = v28.TODAY
A, B = v28.A, v28.B
TITLES = {"reel": "Create a reel", "carousel": "Create a carousel", "stories": "Create your stories", "captions": "Write your captions"}
ACCENT = {"reel": "reel", "carousel": "carousel", "stories": "stories", "captions": "captions"}


def skip(line):
    print("SKIP  " + line, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hashes(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def finished_folder(w, name="Aston Martin Final Exports"):
    """A pretend folder of finished photos outside the Assistant folder: four JPEGs (one again in a subfolder, under
    the same name), a TIFF, a RAW and a video that must stay where they are."""
    src = w.work / "Exports" / name
    (src / "extra").mkdir(parents=True, exist_ok=True)
    jpgs = sorted(p for p in (w.content / A / "Photos").iterdir() if p.suffix.lower() == ".jpg")[:4]
    for p in jpgs:
        shutil.copy2(str(p), str(src / p.name))
    shutil.copy2(str(jpgs[0]), str(src / "extra" / jpgs[0].name))
    (src / "big.tif").write_bytes(b"II*\x00" + b"\x00" * 64)
    (src / "IMG_0001.CR3").write_bytes(b"\x00" * 64)
    (src / "clip.mov").write_bytes(b"\x00" * 64)
    return src


def run_new(env, folder, *more):
    return subprocess.run([sys.executable, str(SCRIPTS / "new_shoot.py"), "make", str(folder)] + list(more), env=env,
                          capture_output=True, text=True, timeout=300)


def content_names(w):
    return sorted(p.name for p in w.content.iterdir() if not p.name.startswith("."))


def check_making(w):
    env = dict(w.env, STUDIO_NO_WINDOWS_FOR_TESTS="1")
    src = finished_folder(w)
    before = hashes(src)
    kits_before = content_names(w)
    r = run_new(env, src, "--for", "stories")
    made = [n for n in content_names(w) if n not in kits_before]
    case("+ A new shoot: one picked folder makes ONE post kit, named for the folder (export words left off) in their folder pattern",
         r.returncode == 0 and len(made) == 1 and made[0].endswith(" Aston Martin") and made[0][:4].isdigit(), (r.stdout[-400:], made))
    kit = w.content / made[0] if made else None
    photos = sorted(p.name for p in (kit / "Photos").iterdir()) if kit else []
    case("... only the finished photos are copied, flat, the second one of a name with its subfolder in front", len(photos) == 5
         and any(p.startswith("extra_") for p in photos) and not any(p.endswith((".tif", ".CR3", ".mov")) for p in photos), photos)
    case("... every copy is byte for byte its original", kit and all(sha(kit / "Photos" / n) == before[n if not n.startswith("extra_") else "extra/" + n[6:]] for n in photos))
    case("... the folder they picked is exactly as it was (copied, never moved)", hashes(src) == before)
    rec = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8")) if kit else {}
    case("... a post kit record and its numbered list", rec.get("source") == "picked" and rec.get("name") == "Aston Martin" and rec.get("numbered") == 5
         and (kit / ".kit" / "sheet.json").is_file(), rec)
    log = json.loads((w.assistant / ".studio" / "new-shoots.json").read_text(encoding="utf-8"))
    case("... the log says where each photo went, with its hash, and that it is done", len(log["runs"]) == 1 and log["runs"][0]["status"] == "done"
         and all(m.get("done") and len(m.get("sha256", "")) == 64 for m in log["runs"][0]["moves"]), log["runs"][-1].get("status"))
    case("... the command names the page that was tapped", "Its stories page: /design.html?kit=" + quote(made[0]) + "&kind=stories" in r.stdout, r.stdout[-200:])
    # twice: the same kit, nothing copied again; a new photo in the folder joins it
    stamp = {n: (kit / "Photos" / n).stat().st_mtime_ns for n in photos}
    shutil.copy2(str(sorted((w.content / B / "Photos").glob("*.jpg"))[0]), str(src / "added later.jpg"))
    r2 = run_new(env, src, "--for", "reel")
    case("picked again: the same kit, no second one", r2.returncode == 0 and content_names(w) == sorted(kits_before + made), (r2.stdout[-300:], content_names(w)))
    case("... the photos already there are left exactly as they were, a new one in the folder joins it",
         all((kit / "Photos" / n).stat().st_mtime_ns == stamp[n] for n in photos) and (kit / "Photos" / "added later.jpg").is_file())
    log2 = json.loads((w.assistant / ".studio" / "new-shoots.json").read_text(encoding="utf-8"))
    case("... one run in the log, still", len(log2["runs"]) == 1 and log2["runs"][0]["status"] == "done")
    (src / "added later.jpg").unlink()           # the test's own file, put there a moment ago
    # a photo they put in the kit's Photos by hand keeps its name; one of the same name from the folder gets " (2)"
    jp = sorted((w.content / B / "Photos").glob("*.jpg"))
    shutil.copy2(str(jp[1]), str(kit / "Photos" / "hand.jpg"))
    shutil.copy2(str(jp[2]), str(src / "hand.jpg"))
    mine = sha(kit / "Photos" / "hand.jpg")
    r2b = run_new(env, src)
    case("a photo they put in the shoot by hand is never written over; the folder's photo of that name comes in as \"hand (2).jpg\"",
         r2b.returncode == 0 and sha(kit / "Photos" / "hand.jpg") == mine and (kit / "Photos" / "hand (2).jpg").is_file()
         and sha(kit / "Photos" / "hand (2).jpg") == sha(src / "hand.jpg"), r2b.stdout[-300:])
    (src / "hand.jpg").unlink()                  # the test's own file, put there a moment ago
    # stops, each with nothing copied
    other = finished_folder(w, "Aston Martin")   # the same name again, from another folder: a clash
    n0 = content_names(w)
    r3 = run_new(env, other)
    case("a shoot of the same name from another folder: stops in plain words, nothing copied", r3.returncode == 1 and "There's already a shoot called" in r3.stdout
         and content_names(w) == n0, r3.stdout[-300:])
    r4 = run_new(env, w.content / A / "Photos")
    case("a folder inside Your Content: stops, pick it from Your shoots", r4.returncode == 1 and "Pick its shoot from Your shoots instead." in r4.stdout and content_names(w) == n0, r4.stdout[-200:])
    r5 = run_new(env, w.work)
    case("a folder that holds the Assistant folder: stops", r5.returncode == 1 and "holds your Assistant folder" in r5.stdout and content_names(w) == n0, r5.stdout[-200:])
    empty = w.work / "Exports" / "Only raws"
    empty.mkdir(parents=True, exist_ok=True)
    (empty / "a.CR3").write_bytes(b"\x00" * 8)
    r6 = run_new(env, empty)
    case("a folder with no finished photos: stops, nothing copied", r6.returncode == 1 and "No finished photos (JPEGs)" in r6.stdout and content_names(w) == n0, r6.stdout[-200:])
    # no Assistant folder yet: made in Pictures (a pretend Pictures, by the tests' switch)
    fresh = w.work / "fresh"
    pics = fresh / "folders" / "Pictures"
    pics.mkdir(parents=True)
    (fresh / "studio").mkdir()
    env2 = dict(env, STUDIO_HOME=str(fresh / "studio"), STUDIO_FOLDERS_FOR_TESTS=str(fresh / "folders"))
    r7 = run_new(env2, src)
    made2 = sorted(p.name for p in (pics / "The Assistant" / "Your Content").iterdir()) if (pics / "The Assistant" / "Your Content").is_dir() else []
    case("a brand-new Assistant: its folder is made in Pictures, and the shoot in it", r7.returncode == 0 and len(made2) == 1 and made2[0].endswith("Aston Martin"), (r7.stdout[-300:], made2))
    return made[0] if made else None


def check_routes(w):
    code, d = w.get_json("/make-list")
    raw = json.dumps(d)
    case("/make-list: every post kit, newest first, with a small picture and the four pages each lands on, never a path",
         code == 200 and d["ok"] and [k["folder"] for k in d["kits"]][:2] == sorted([k["folder"] for k in d["kits"]], reverse=True)[:2]
         and all(set(k["go"]) == {"reel", "carousel", "stories", "captions", "captions_reel", "captions_carousel"} and k["thumb"].startswith("/kit-thumb?kit=") for k in d["kits"])
         and all(k["go"]["captions_carousel"].endswith("&piece=carousel") and k["go"]["captions_reel"].endswith("&piece=reel") for k in d["kits"])
         and str(w.work) not in raw and "/private/" not in raw, raw[:300])
    code, _ = w.get_json("/make-list", headers={"Sec-Fetch-Site": "cross-site"})
    case("... refused to another website", code == 403, code)
    code, raw = w.http("POST", "/make-new", raw=b"{}", headers={"Content-Type": "application/json", "Origin": "http://evil.example"})
    case("POST /make-new from another website: refused, no window, nothing made", code == 403, code)
    code, raw = w.http("POST", "/make-vault", raw=b'{"make":"nope"}', headers={"Content-Type": "application/json"})
    case("POST /make-vault with anything but one of the four: refused", code == 400, code)
    code, raw = w.http("POST", "/make-vault", raw=b'{"make":"captions"}', headers={"Content-Type": "application/json"})
    try:
        d = json.loads(raw.decode("utf-8"))
    except ValueError:
        d = {}
    case("POST /make-vault for Captions: both of the vault's words pages, for the page to choose from once they answer (Nov 22)",
         code == 200 and d.get("ok") and (d.get("go") or {}).get("captions_reel") == "/words.html?kit=My%20vault&piece=reel"
         and (d.get("go") or {}).get("captions_carousel") == "/words.html?kit=My%20vault&piece=carousel", d)


# ---------------------------------------------------------------- in a browser

def ready(c):
    c.wait_for("!!document.getElementById('tiles') && !!document.getElementById('mk')", 20)


def open_box(c, make):
    c.click("#tiles .tl[data-make=%s]" % make)
    c.wait_for("!document.getElementById('mk').hidden && document.querySelectorAll('#mkL .mkr').length + (document.getElementById('mkLab').hidden ? 1 : 0) > 0", 15)
    time.sleep(0.2)


def box_state(c):
    return c.js("(() => { const t = document.getElementById('mkT'); return {title: t.textContent, em: t.querySelector('em') && t.querySelector('em').textContent, "
                "emColor: t.querySelector('em') && getComputedStyle(t.querySelector('em')).color, sub: document.getElementById('mkS').textContent, "
                "top: [...document.querySelectorAll('#mkTop .mkr')].map(r => r.innerText.replace(/\\s+/g, ' ').trim()), lab: !document.getElementById('mkLab').hidden, "
                "labText: document.getElementById('mkLab').textContent, find: !document.getElementById('mkF').hidden, "
                "rows: [...document.querySelectorAll('#mkL .mkr')].map(r => ({b: r.querySelector('b').textContent, small: r.querySelector('small').textContent, "
                "href: r.getAttribute('href'), imgs: r.querySelectorAll('img').length, v: r.classList.contains('v')})), "
                "nothing: (document.querySelector('#mkL .mknothing') || {}).textContent || ''}; })()")


def ask_state(c):
    return c.js("(() => ({shown: !document.getElementById('mkAsk').hidden, sub: document.getElementById('mkS').textContent, for: document.getElementById('mkFor').textContent, "
                "buttons: [...document.querySelectorAll('#mkAsk button')].map(b => b.textContent), listShown: !document.getElementById('mkL').hidden, "
                "newShown: !document.getElementById('mkTop').hidden, path: location.pathname, focus: (document.activeElement || {}).id}))()")


def closed(c):
    return c.js("document.getElementById('mk').hidden")


def check_browser(c, w, shot=None):
    c.open(w.url("/home"))
    ready(c)
    for make in ("reel", "carousel", "stories", "captions"):
        open_box(c, make)
        s = box_state(c)
        case("the %s tile: \"%s\", the last word in her accent, and \"Which shoot do you want to make it from?\"" % (make, TITLES[make]),
             s["title"] == TITLES[make] and s["em"] == ACCENT[make] and s["emColor"] == "rgb(217, 96, 58)" and s["sub"] == "Which shoot do you want to make it from?", s)
        c.key("Escape")
        c.wait_for("document.getElementById('mk').hidden", 5)
    open_box(c, "reel")
    s = box_state(c)
    if shot:
        import base64
        c.wait_for("[...document.querySelectorAll('#mkL img')].every(i => i.complete)", 10)
        Path(shot).parent.mkdir(parents=True, exist_ok=True)
        Path(shot).write_bytes(base64.b64decode(c.cdp("Page.captureScreenshot", {"format": "png"})["data"]))
        print("screenshot: %s" % shot, flush=True)
    case("+ A new shoot on top, \"Pick the folder with your finished photos\"", s["top"] == ["+ A new shoot Pick the folder with your finished photos →"], s["top"])
    case("Your shoots: My vault first (\"Mix photos and clips from all your shoots\", a little mosaic), then the post kits newest first",
         s["lab"] and s["labText"] == "Your shoots" and s["rows"][0]["b"] == "My vault" and s["rows"][0]["v"] and s["rows"][0]["imgs"] >= 1
         and s["rows"][0]["small"] == "Mix photos and clips from all your shoots" and [r["b"] for r in s["rows"][1:3]] == ["Katie Austin Maternity", "Hannah"], s["rows"][:3])
    import home_base
    count = {k["folder"]: k["photos"] for k in home_base.kits()}
    case("... each a small photo, the name, the date and the number of photos", s["rows"][1]["small"] == "Nov 2, 2026 · %d photos" % count[B] and s["rows"][1]["imgs"] == 1
         and s["rows"][2]["small"] == "Nov 1, 2026 · %d photos" % count[A], [r["small"] for r in s["rows"]])
    case("... no search box with fewer than 7 shoots", not s["find"])
    # close three ways
    c.click("#mkX")
    case("closed with x", c.wait_for("document.getElementById('mk').hidden", 5) is not False and closed(c))
    open_box(c, "reel")
    r = c.rect(".mk")
    c.click(".mk", fx=0.01, fy=0.01)
    case("closed with a press outside", c.wait_for("document.getElementById('mk').hidden", 5) is not False and closed(c), r)
    open_box(c, "reel")
    c.click("#mkS")
    case("... a press inside it keeps it open", not closed(c))
    c.key("Escape")
    case("closed with Escape", c.wait_for("document.getElementById('mk').hidden", 5) is not False and closed(c))
    case("no page errors, and nothing asked of the internet", not c.page_errors() and not c.outside_requests(), (c.page_errors()[:2], c.outside_requests()[:2]))
    # each landing address
    want = {"reel": ("/reel.html", {"kit": [B]}), "carousel": ("/design.html", {"kit": [B]}),
            "stories": ("/design.html", {"kit": [B], "kind": ["stories"]}), "captions": ("/words.html", {"kit": [B], "piece": ["carousel"]})}
    for make, (path, q) in want.items():
        c.open(w.url("/home"))
        ready(c)
        open_box(c, make)
        c.click("#mkL .mkr[data-kit=%s]" % json.dumps(B))
        if make == "captions":
            c.wait_for("!document.getElementById('mkAsk').hidden", 10)
            a = ask_state(c)
            case("Captions from a shoot: it asks \"Captions for a reel or a carousel?\", Reel and Carousel, naming the shoot, the list put away, still on the home page (Nov 22)",
                 a == {"shown": True, "sub": "Captions for a reel or a carousel?", "for": "Katie Austin Maternity", "buttons": ["Reel", "Carousel"],
                       "listShown": False, "newShown": False, "path": "/home", "focus": "mkAR"}, a)
            c.click("#mkAC")
        c.wait_for("location.pathname === %s" % json.dumps(path), 20)
        u = urlsplit(c.js("location.href"))
        case("%s from a shoot lands on %s for that shoot" % (make, path), u.path == path and landed(u, q), c.js("location.href"))
        if make == "reel":
            case("... the reel page's chooser (no kind picked yet)", "kind" not in parse_qs(u.query))
    # Captions, Reel: the words page's Reel tab
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "captions")
    c.click("#mkL .mkr[data-kit=%s]" % json.dumps(B))
    c.wait_for("!document.getElementById('mkAsk').hidden", 10)
    c.click("#mkAR")
    c.wait_for("location.pathname === '/words.html'", 20)
    u = urlsplit(c.js("location.href"))
    case("... Reel lands on the words page's Reel tab", parse_qs(u.query) == {"kit": [B], "piece": ["reel"]}, c.js("location.href"))
    # the question opened afresh: Escape closes it, and the next tile shows its list again (nothing left over)
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "captions")
    c.click("#mkL .mkr[data-kit=%s]" % json.dumps(B))
    c.wait_for("!document.getElementById('mkAsk').hidden", 10)
    c.key("Escape")
    c.wait_for("document.getElementById('mk').hidden", 5)
    open_box(c, "reel")
    s = box_state(c)
    case("... closed with Escape; the next tile opens on its list again, not the question", c.js("document.getElementById('mkAsk').hidden") and s["sub"] == "Which shoot do you want to make it from?"
         and len(s["rows"]) >= 3 and s["top"], s)
    c.key("Escape")
    # My vault from Captions: the same question, then the vault's own words page (a page the vault has)
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "captions")
    c.click("#mkVault")
    c.wait_for("!document.getElementById('mkAsk').hidden", 10)
    a = ask_state(c)
    case("My vault from Captions: the same question, naming My vault", a["shown"] and a["for"] == "My vault" and a["path"] == "/home", a)
    c.click("#mkAC")
    c.wait_for("location.pathname === '/words.html'", 20)
    href = c.js("decodeURIComponent(location.href)")
    c.wait_for("document.readyState === 'complete'", 10)
    body = c.js("document.body.innerText")
    import arrange
    case("... Carousel lands on the vault's own words page, Carousel tab, and the page really opens",
         href.endswith("/words.html?kit=My vault&piece=carousel") and arrange.CANT_FIND not in body and len(body) > 40, (href, body[:200]))
    for make, path in (("reel", "/reel.html"), ("stories", "/content/")):
        c.open(w.url("/home"))
        ready(c)
        open_box(c, make)
        c.click("#mkVault")
        c.wait_for("location.pathname.startsWith(%s)" % json.dumps(path), 20)
        href = c.js("decodeURIComponent(location.href)")
        case("My vault from %s: %s" % (make, "its own reel page" if make == "reel" else "its post kit page"),
             ("/reel.html?kit=My vault" in href) if make == "reel" else href.endswith("/content/My vault/Post kit.html"), href)
    case("... and no page errors on the pages it landed on", not c.page_errors(), c.page_errors()[:2])


def check_search(c, w):
    extra = []
    for i in range(5):
        k = w.content / ("2026-10-0%d Extra %d" % (i + 1, i + 1))
        (k / "Photos").mkdir(parents=True)
        (k / ".kit").mkdir()
        w.put(k / ".kit" / "kit.json", {"name": "Extra %d" % (i + 1), "date": "2026-10-0%d" % (i + 1), "folder": k.name})
        extra.append(k)
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "carousel")
    c.wait_for("document.querySelectorAll('#mkL .mkr').length >= 8", 10)
    s = box_state(c)
    case("7 shoots or more: \"Search your shoots\" shows", s["find"] and c.js("document.getElementById('mkF').placeholder") == "Search your shoots", s["find"])
    c.click("#mkF")
    c.type_text("katie")
    time.sleep(0.3)
    s = box_state(c)
    case("... it finds by name, and leaves My vault out unless it matches", [r["b"] for r in s["rows"]] == ["Katie Austin Maternity"], [r["b"] for r in s["rows"]])
    c.key("Meta+a")
    c.type_text("zzz")
    time.sleep(0.3)
    s = box_state(c)
    case("... nothing found says so, in her words", not s["rows"] and s["nothing"] == "Nothing matches \"zzz\".", s["nothing"])
    c.key("Meta+a")
    c.type_text("vault")
    time.sleep(0.3)
    s = box_state(c)
    case("... \"vault\" finds My vault", [r["b"] for r in s["rows"]] == ["My vault"], [r["b"] for r in s["rows"]])
    c.key("Escape")
    for k in extra:                              # the test's own pretend kits, made a moment ago
        shutil.rmtree(str(k))


def landed(u, want):
    """The address the box sent them to. The stories designer itself adds `design=<id>` to its own address a moment
    after it opens (history.replaceState, once it has opened or made the set), so a slow run can read the address
    after that: the design the designer chose is not part of where the box landed them (final check, Nov 22: seen
    on Apple's 3.9 only)."""
    q = parse_qs(u.query)
    q.pop("design", None)
    return q == want


def check_new_shoot(c, w, src):
    """+ A new shoot in the page: the picker (answered by the tests' switch), the kit made, landing on the tapped page."""
    before = hashes(src)
    names0 = content_names(w)
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "stories")
    c.click("#mkNew")
    c.wait_for("location.pathname === '/design.html'", 120)
    u = urlsplit(c.js("location.href"))
    made = [n for n in content_names(w) if n not in names0]
    case("+ A new shoot from Stories: the post kit is made and the page lands on the stories designer, not the post kit",
         len(made) == 1 and landed(u, {"kit": [made[0]], "kind": ["stories"]}), (c.js("location.href"), made))
    case("... the folder they picked is exactly as it was", hashes(src) == before)
    got = sorted(p.name for p in (w.content / made[0] / "Photos").iterdir()) if made else []
    case("... its photos are in the kit", len(got) == 5, got)
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "captions")
    c.click("#mkNew")
    c.wait_for("!document.getElementById('mkAsk').hidden || location.pathname === '/words.html'", 120)
    a = ask_state(c)
    case("the same folder again from Captions: it asks reel or carousel before landing (Nov 22)", a["shown"] and a["sub"] == "Captions for a reel or a carousel?" and a["path"] == "/home", a)
    c.click("#mkAC")
    c.wait_for("location.pathname === '/words.html'", 30)
    u = urlsplit(c.js("location.href"))
    case("... then no second kit, the words page of the same one, on the Carousel tab",
         content_names(w) == sorted(names0 + made) and parse_qs(u.query) == {"kit": [made[0]], "piece": ["carousel"]}, (content_names(w), c.js("location.href")))
    return made[0] if made else None


def check_cancel(c, w):
    names0 = content_names(w)
    job0 = (w.home / "new-shoot-job.json").read_bytes() if (w.home / "new-shoot-job.json").exists() else None
    log = w.assistant / ".studio" / "new-shoots.json"
    log0 = log.read_bytes() if log.exists() else None
    c.open(w.url("/home"))
    ready(c)
    open_box(c, "reel")
    c.click("#mkNew")
    time.sleep(1.5)
    case("a closed folder window changes nothing: the box stays, no line, no kit, no job, no log",
         not closed(c) and c.js("document.getElementById('mkNote').hidden") and content_names(w) == names0
         and ((w.home / "new-shoot-job.json").read_bytes() if (w.home / "new-shoot-job.json").exists() else None) == job0
         and (log.read_bytes() if log.exists() else None) == log0 and c.js("location.pathname") == "/home")
    case("... and + A new shoot can be pressed again", c.js("!document.getElementById('mkNew').disabled"))


def check_empty(c, w):
    with v28_kits_away(w):
        c.open(w.url("/home"))
        ready(c)
        c.click("#tiles .tl[data-make=reel]")
        c.wait_for("!document.getElementById('mk').hidden && document.getElementById('mkS').textContent.startsWith('Start')", 15)
        s = box_state(c)
    case("no post kits yet: only + A new shoot, and \"Start with a shoot: pick the folder with your finished photos.\"",
         s["sub"] == "Start with a shoot: pick the folder with your finished photos." and not s["lab"] and not s["rows"] and not s["find"] and len(s["top"]) == 1, s)


class v28_kits_away:
    """Every post kit (and the vault) put away for a moment, inside the test's own folder, then put back."""
    def __init__(self, w):
        self.w, self.away = w, w.work / "kits-away"

    def __enter__(self):
        self.away.mkdir(exist_ok=True)
        self.names = content_names(self.w)
        for n in self.names:
            (self.w.content / n).rename(self.away / n)

    def __exit__(self, *a):
        for n in self.names:
            (self.away / n).rename(self.w.content / n)


def check_page(w):
    import home
    page = home.page_html()
    case("the box is on the page, hidden, with her words drawn as text", "<div class='mk' id='mk' hidden>" in page and ">A new shoot<" in page
         and ">Pick the folder with your finished photos<" in page and ">Which shoot do you want to make it from?<" in page and "aria-modal='true'" in page)
    case("... her four titles reach the page's script as words, never drawn as markup from a name",
         all(('"mk_%s": "%s"' % (k, t.replace(ACCENT[k], "<em>%s</em>" % ACCENT[k]))) in page.replace("<\\/", "</") for k, t in TITLES.items()))
    case("... no em dash, no serif, never Claude", "—" not in page and "serif" not in page.replace("sans-serif", "") and "claude" not in page.lower())


# ---------------------------------------------------------------- the review (Nov 21)

def in_world(env, code):
    """A few lines of Python run against the scripts in a world of their own (its own STUDIO_HOME); the last line it
    prints is JSON."""
    pre = "import sys, json, os\nsys.path.insert(0, %r)\n" % str(SCRIPTS)
    r = subprocess.run([sys.executable, "-c", pre + code], env=env, capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (r.stdout[-400:], r.stderr[-800:])}


def review_world(w, name):
    """A brand-new photographer: a scratch STUDIO_HOME and a pretend Pictures, no Assistant folder yet."""
    base = w.work / "review" / name
    (base / "studio").mkdir(parents=True)
    pics = base / "folders" / "Pictures"
    pics.mkdir(parents=True)
    env = dict(w.env, STUDIO_HOME=str(base / "studio"), STUDIO_FOLDERS_FOR_TESTS=str(base / "folders"), STUDIO_NO_WINDOWS_FOR_TESTS="1")
    return base, pics, env


def jpgs(w, n):
    return sorted(p for p in (w.content / A / "Photos").iterdir() if p.suffix.lower() == ".jpg")[:n]


def check_review(w):
    import unicodedata
    # 1. nothing is made before the folder is known to be a shoot
    base, pics, env = review_world(w, "nothing-first")
    empty = base / "Only raws"
    empty.mkdir()
    (empty / "a.CR3").write_bytes(b"\x00" * 8)
    r = run_new(env, empty)
    sf = (base / "studio" / "studio.json")
    case("review: a brand-new Assistant and a folder with no finished photos: stops, and NO Assistant folder is made, the Studio File untouched",
         r.returncode == 1 and "No finished photos" in r.stdout and not (pics / "The Assistant").exists()
         and "posts" not in (json.loads(sf.read_text(encoding="utf-8")) if sf.is_file() else {}), (r.stdout[-300:], sorted(p.name for p in pics.iterdir())))
    for i, j in enumerate(jpgs(w, 3)):
        shutil.copy2(str(j), str(pics / ("x%d.jpg" % i)))
    r = run_new(env, pics)
    case("review: picking Pictures itself, where a brand-new Assistant folder would go: stops in true words, nothing made",
         r.returncode == 1 and "will be made in that folder" in r.stdout and not (pics / "The Assistant").exists(), (r.stdout[-300:], sorted(p.name for p in pics.iterdir())))
    # 2. a folder inside Your Content, spelled in other capitals, is still inside it
    base, pics, env = review_world(w, "capitals")
    src = finished_folder(w, "Capitals Final")
    r = run_new(env, src)
    content = pics / "The Assistant" / "Your Content"
    kits0 = sorted(content.iterdir()) if content.is_dir() else []
    upper = Path(str(kits0[0] / "Photos").upper()) if kits0 else Path("/nowhere")
    r2 = run_new(env, upper)
    case("review: a post kit's own Photos folder typed in capitals is still inside Your Content: stops, no second kit",
         r.returncode == 0 and upper.is_dir() and r2.returncode == 1 and "Pick its shoot from Your shoots instead." in r2.stdout
         and sorted(content.iterdir()) == kits0, (r2.stdout[-300:], [p.name for p in content.iterdir()] if content.is_dir() else None))
    # 3. the same accented folder again, its shoot's name stored decomposed (as an HFS+ drive stores it): back to it
    base, pics, env = review_world(w, "accents")
    src = finished_folder(w, "Caf\u00e9 Final")
    r = run_new(env, src)
    content = pics / "The Assistant" / "Your Content"
    kit = next((p for p in content.iterdir() if "Caf" in p.name), None) if content.is_dir() else None
    if kit is not None:
        spare = content / "spare-name"
        kit.rename(spare)
        spare.rename(content / unicodedata.normalize("NFD", kit.name))
    r2 = run_new(env, src)
    case("review: the same accented folder again, its shoot spelled decomposed on the drive: back to that shoot, no name clash",
         r.returncode == 0 and r2.returncode == 0 and "going back to it" in r2.stdout and len(list(content.iterdir())) == 1, r2.stdout[-300:])
    # 4. a cut-off run, then a photo of theirs put by hand at a name the cut-off run had planned: theirs kept, the photo comes in
    base, pics, env = review_world(w, "cut-off")
    src = finished_folder(w, "Cut Off Final")
    run_new(env, src)
    content = pics / "The Assistant" / "Your Content"
    kit = next(iter(content.iterdir()))
    logp = pics / "The Assistant" / ".studio" / "new-shoots.json"
    log = json.loads(logp.read_text(encoding="utf-8"))
    m = [x for x in log["runs"][0]["moves"] if "/" not in x["src"]][-1]
    m.pop("done", None)
    m.pop("sha256", None)
    log["runs"][0]["status"] = "copying"
    logp.write_text(json.dumps(log), encoding="utf-8")
    (kit / "Photos" / m["dst"]).unlink()           # the test's own copy, made a moment ago: as if the run stopped before it
    hand = sorted((w.content / B / "Photos").glob("*.jpg"))[0]   # a different photo from any in the folder
    shutil.copy2(str(hand), str(kit / "Photos" / m["dst"]))
    mine = sha(kit / "Photos" / m["dst"])
    stem, ext = os.path.splitext(m["dst"])
    r = run_new(env, src)
    r2 = run_new(env, src)
    case("review: a name a cut-off run had planned, taken meanwhile by a photo of theirs: theirs is never written over and the photo comes in under \" (2)\", not a stop on every try",
         r.returncode == 0 and r2.returncode == 0 and sha(kit / "Photos" / m["dst"]) == mine
         and sha(kit / "Photos" / (stem + " (2)" + ext)) == sha(src / m["src"]), (r.stdout[-300:], sorted(p.name for p in (kit / "Photos").iterdir())))
    # 5. no room: stops before the first copy
    base, pics, env = review_world(w, "room")
    src = finished_folder(w, "Room Final")
    got = in_world(env, "import this_computer, new_shoot\nthis_computer.free_bytes = lambda p: 10\n"
                        "try:\n    new_shoot.make(%r); print(json.dumps({'made': True}))\n"
                        "except new_shoot.Trouble as t:\n    print(json.dumps({'words': str(t)}))\n" % str(src))
    case("review: not enough room on the drive: stops in plain words before a byte is copied, no Assistant folder made",
         "There isn't room for these photos" in got.get("words", "") and not (pics / "The Assistant").exists(), got)
    # 6. a job that was killed is "stopped", not "working" for ever (the page server is its parent: waited for)
    base, pics, env = review_world(w, "killed")
    src = finished_folder(w, "Killed Final")
    got = in_world(env, "import signal, time, create_dialog, new_shoot\np = create_dialog._start(%r)\n"
                        "os.kill(p.pid, signal.SIGKILL)\ntime.sleep(1.0)\nprint(json.dumps(new_shoot.job()))\n" % str(src))
    case("review: a job whose program was killed reads as stopped, so + A new shoot works again (not \"One moment\" for ever)",
         got.get("state") == "stopped", got)
    # 7. two presses at once: one folder window, one copy
    base, pics, env = review_world(w, "two-presses")
    src = finished_folder(w, "Two Final")
    got = in_world(env, """import io, threading, time, create_dialog, this_computer
calls, starts = [], []
def slow(prompt):
    calls.append(1); time.sleep(1.0); return %r, ""
this_computer.pick_folder = slow
create_dialog._start = lambda f: starts.append(f)
class H:
    def __init__(self):
        self.headers = {"Host": "127.0.0.1:9", "Content-Type": "application/json", "Content-Length": "2"}
        self.rfile = io.BytesIO(b"{}"); self.wfile = io.BytesIO()
        self.server = type("S", (), {"server_address": ("127.0.0.1", 9)})()
    def send_response(self, c): self.code = c
    def send_header(self, *a): pass
    def end_headers(self): pass
hs = [H(), H()]
ts = [threading.Thread(target=create_dialog.handle_post, args=(h, "/make-new", "")) for h in hs]
[t.start() for t in ts]; [t.join() for t in ts]
print(json.dumps({"windows": len(calls), "starts": len(starts), "said": [h.wfile.getvalue().decode() for h in hs]}))
""" % str(src))
    case("review: two presses of + A new shoot at once: one folder window and one copy; the other press is told it's busy",
         got.get("windows") == 1 and got.get("starts") == 1 and any("being copied in right now" in s for s in got.get("said", [])), got)
    # 8. the chat's make and the page's job never run at once
    base, pics, env = review_world(w, "lock")
    src = finished_folder(w, "Lock Final")
    run_new(env, finished_folder(w, "Lock First"))          # the Assistant folder, made the usual way
    content = pics / "The Assistant" / "Your Content"
    names0 = sorted(p.name for p in content.iterdir())
    got = in_world(env, """import subprocess, kit, new_shoot
with kit._held(new_shoot.LOCK, 2.0) as g:
    r = subprocess.run([sys.executable, os.path.join(%r, "new_shoot.py"), "make", %r], capture_output=True, text=True, timeout=120)
print(json.dumps({"held": g, "code": r.returncode, "out": r.stdout[-300:]}))
""" % (str(SCRIPTS), str(src)))
    case("review: the chat's new_shoot.py make waits its turn: while a copy holds the lock it stops, nothing made",
         got.get("held") == "held" and got.get("code") == 3 and "being copied in right now" in got.get("out", "")
         and sorted(p.name for p in content.iterdir()) == names0, got)


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards")
    ap.add_argument("--port", type=int, default=9980)
    ap.add_argument("--no-chrome", action="store_true")
    ap.add_argument("--shot", help="write a screenshot of Create a reel at 1440 x 900 here")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8790, 8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        skip("the pretend kits are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="create-dialog-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    w = v28.World(work, a.port)
    w.env.update(STUDIO_NO_WINDOWS_FOR_TESTS="1", STUDIO_CARD_FOR_TESTS="none", PHOTO_WORDS_PRETEND="none")
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none",
                      STUDIO_NO_WINDOWS_FOR_TESTS="1", FACES_PRETEND=str(w.pretend), PHOTO_WORDS_PRETEND="none")
    try:
        w.build()
        for k in (A, B):
            w.previews(k)
        sys.path.insert(0, str(SCRIPTS))
        import new_shoot
        case("the test's own scratch home, never the real one", Path(new_shoot.HOME) == w.home and ".studio" not in str(new_shoot.HOME))
        group("what the page carries", check_page, w)
        group("+ A new shoot, without the page", check_making, w)
        # the shoot made above is put away, so the browser's + A new shoot makes one fresh (the log keeps the
        # earlier run's folder name, which is then gone from Your Content: a new kit, as a deleted one would be)
        made = [n for n in content_names(w) if n.endswith(" Aston Martin")]
        for n in made:
            (w.content / n).rename(w.work / ("put-away " + n))
        src = w.work / "Exports" / "Aston Martin Final Exports"
        if a.no_chrome or not chrome_drive.find_chrome():
            w.start()
            group("the routes", check_routes, w)
            skip("the box in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            w.start()
            group("the routes", check_routes, w)
            with chrome_drive.Chrome(work=str(work), size=(1440, 900)) as c:
                group("the box in a browser", check_browser, c, w, a.shot)
                group("the search box", check_search, c, w)
                group("a closed folder window", check_cancel, c, w)
                w.stop()
                w.start(STUDIO_PICK_FOLDER_FOR_TESTS=str(src))
                group("+ A new shoot in the page", check_new_shoot, c, w, src)
                group("no post kits yet", check_empty, c, w)
        group("the review of + A new shoot", check_review, w)
    finally:
        w.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(base), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
