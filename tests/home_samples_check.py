#!/usr/bin/env python3
"""Sample photos for a brand-new Assistant (Nicole's v30, section 6), checked on a pretend Assistant.

    python3 tests/guard.py 3000 python3 tests/home_samples_check.py [--port 9990] [--work <folder>] [--no-chrome]

A scratch STUDIO_HOME, the v28 test's pretend kits (put away for "brand-new"), and a scratch samples folder
(STUDIO_SAMPLES_FOR_TESTS) holding pictures the Mac's own sips made, beside things that must never be served (a
hidden file, a text file, a folder, a link to a photo outside, a file too big, a photo outside the folder). Never the
plugin's own samples folder, never the real ~/.studio. It holds: the samples are used only while there is no post
kit (archived ones count), by file name only, with her line; they count in nothing; the route serves only a photo
in the folder by its exact name, only to this server's own page; an empty folder keeps the grey placeholders; and in
a browser, the hello and the four tiles show them with her line, and they go by themselves when a first kit comes in.
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import home_v28_check as v28  # noqa: E402
import home_v30_check as v30  # noqa: E402

TODAY = v28.TODAY
NOTE = "Sample photos. Yours show up here after your first shoot."
# name -> (width, height, colour): three wide, five tall, in name order
PHOTOS = {"01 beach.jpg": (1600, 1000, (200, 120, 60)), "02 field.jpg": (1600, 1060, (60, 140, 70)), "03 couple.jpg": (1600, 900, (40, 80, 160)),
          "04 baby.jpg": (1200, 1600, (220, 200, 40)), "05 kids.jpg": (1200, 1600, (160, 40, 160)), "06 mum.jpg": (1280, 1600, (40, 170, 170)),
          "07 dog.jpg": (1200, 1500, (120, 60, 30)), "08 dune.png": (1200, 1600, (90, 90, 90))}


def png(path, w, h, rgb):
    row = b"\x00" + bytes(rgb) * w
    raw = zlib.compress(row * h, 9)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def make_samples(d, outside):
    d.mkdir(parents=True, exist_ok=True)
    for name, (w, h, rgb) in PHOTOS.items():
        p = d / name
        if name.endswith(".png"):
            png(p, w, h, rgb)
            continue
        tmp = d.parent / ("tmp-" + name + ".png")
        png(tmp, w, h, rgb)
        subprocess.run(["sips", "-s", "format", "jpeg", str(tmp), "--out", str(p)], capture_output=True, timeout=60, check=True)
        tmp.unlink()
    # things that are never a sample
    shutil.copy(str(d / "01 beach.jpg"), str(d / ".hidden.jpg"))
    (d / "README.txt").write_text("not a photo", encoding="utf-8")
    (d / "notes.jpg.txt").write_text("not a photo", encoding="utf-8")
    (d / "sub").mkdir(exist_ok=True)
    shutil.copy(str(d / "01 beach.jpg"), str(d / "sub" / "inside.jpg"))
    outside.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(d / "02 field.jpg"), str(outside))
    os.symlink(str(outside), str(d / "link.jpg"))
    (d / "huge.jpg").write_bytes(b"\xff\xd8" + os.urandom(6_100_000))


def faces_table(w):
    t = {}
    try:
        t = json.loads(w.pretend.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    t["01 beach.jpg"] = {"w": 1600, "h": 1000, "faces": [[0.70, 0.20, 0.10, 0.16]]}
    t["04 baby.jpg"] = {"w": 1200, "h": 1600, "faces": [[0.10, 0.10, 0.20, 0.15]]}
    w.put(w.pretend, t)


def check_python(w, d, outside):
    import samples
    import home
    import home_base
    case("the samples are read from the test's own folder, never the plugin's", samples.folder() == d and samples.FOLDER != d)
    names = [n for n, _ in samples.listed()]
    case("only the photos in the folder itself, in name order: no hidden file, text file, folder, link or file too big", names == list(PHOTOS), names)
    case("the plugin's own samples folder ships with no photos, only its README", sorted(p.name for p in samples.FOLDER.iterdir()) == ["README.txt"],
         sorted(p.name for p in samples.FOLDER.iterdir()))
    case("the README says Nicole chooses 8 to 10, 1600 px, a few MB, licensed to ship inside a product",
         all(t in (samples.FOLDER / "README.txt").read_text(encoding="utf-8") for t in ("Nicole chooses", "8 to 10", "1600 px", "a few MB", "inside a product")))
    case("a picture's size is read from its own header (JPEG and PNG)", samples._dims(d / "01 beach.jpg") == (1600, 1000) and samples._dims(d / "08 dune.png") == (1200, 1600))
    case("with post kits, no samples: the home page is theirs", samples.for_home() is None and home.facts()["samples"] is None)
    with v30.Kits(w):
        s = samples.for_home()
        case("no post kit yet: the hello takes the wide samples, in order", s and s["hello"] == ["01 beach.jpg", "02 field.jpg", "03 couple.jpg"], s)
        flat_t = [n for t in s["tiles"] for n in t]
        case("...four tiles, each its own photos, none the hello opens on", len(s["tiles"]) == 4 and all(s["tiles"]) and len(set(flat_t)) == len(flat_t)
             and "01 beach.jpg" not in flat_t and [t[0] for t in s["tiles"]] == ["04 baby.jpg", "05 kids.jpg", "06 mum.jpg", "07 dog.jpg"], s["tiles"])
        f = home.facts()
        page = home.page_html()
        case("the home page carries them, with her line, whole", f["samples"] and f["samples"]["note"] == NOTE and NOTE in page and "id='sampleNote' hidden" in page)
        data = json.loads(v30.part(page, "id='facts'>", "</script>"))
        case("...names only on the page: no folder, no path", data["samples"]["hello"] == s["hello"] and str(d) not in page and "/samples/" not in page
             and all("/" not in n and "\\" not in n for n in data["samples"]["hello"] + flat_t), data["samples"])
        case("they count in nothing: no kits, no photos, no grid on the home page, the hello's facts know no shoot",
             f["kits"] == 0 and f["hello_photos"] == [] and f["tiles"] == [] and f["grid"] == [] and f["posting"]["ready"] == 0 and (f.get("hello") or {}).get("kit") in (None, ""), f)
        other = home_base.backups_html() + home_base.make_posts_html()
        case("...and show nowhere else (the Back up a card and post kits screens)", "home-sample" not in other and NOTE not in other)
        # an archived kit is still a post kit: no samples
        away = w.work / "kits-away"
        (away / v30.A).rename(w.content / v30.A)
        try:
            home_base.set_archived(v30.A, True)
            case("an archived post kit counts as their first: no samples", samples.for_home() is None and home.facts()["samples"] is None)
        finally:
            home_base.set_archived(v30.A, False)
            (w.content / v30.A).rename(away / v30.A)
        # an empty folder: the grey placeholders stay
        hold = w.work / "samples-away"
        d.rename(hold)
        d.mkdir()
        try:
            f2, p2 = home.facts(), home.page_html()
            case("an empty samples folder: no samples, no line, the grey placeholders stay", f2["samples"] is None and "id='sampleNote'" not in p2
                 and json.loads(v30.part(p2, "id='facts'>", "</script>"))["samples"] is None)
        finally:
            d.rmdir()
            hold.rename(d)


def check_routes(w, d, outside):
    with v30.Kits(w):
        st, body = w.http("GET", "/home-sample?name=" + quote("01 beach.jpg"))
        case("GET /home-sample serves a sample by its exact name, byte for byte", st == 200 and body == (d / "01 beach.jpg").read_bytes(), st)
        st, body = w.http("GET", "/home-sample?name=" + quote("08 dune.png"))
        case("...a PNG too", st == 200 and body[:8] == b"\x89PNG\r\n\x1a\n", st)
        bad = [".hidden.jpg", "README.txt", "notes.jpg.txt", "sub/inside.jpg", "sub", "link.jpg", "huge.jpg", "../outside.jpg", "..%2Foutside.jpg",
               str(outside), str(d / "01 beach.jpg"), "01 BEACH.jpg", "01 beach.jpg ", ""]
        got = {n: w.http("GET", "/home-sample?name=" + quote(n))[0] for n in bad}
        case("...and nothing else: a hidden file, a text file, a folder, a link, a file too big, a path, other capitals: all 404", all(v == 404 for v in got.values()), got)
        st2 = w.http("GET", "/home-sample?name=" + quote("01 beach.jpg") + "&name=" + quote("02 field.jpg"))[0]
        st3 = w.http("GET", "/home-sample")[0]
        case("...two names, or none: 404", st2 == 404 and st3 == 404, (st2, st3))
        st4 = w.http("GET", "/home-sample?name=" + quote("01 beach.jpg"), host="evil.example:%d" % w.port)[0]
        st5 = w.http("GET", "/home-sample?name=" + quote("01 beach.jpg"), headers={"Sec-Fetch-Site": "cross-site"})[0]
        case("...never to another website (another Host, a cross-site ask): 403", st4 == 403 and st5 == 403, (st4, st5))
        st, body = w.http("GET", "/home-sample-faces")
        fc = json.loads(body.decode("utf-8")).get("faces") if st == 200 else None
        case("GET /home-sample-faces: where the faces are, by name (the samples only)", fc and set(fc) == {"01 beach.jpg", "04 baby.jpg"}, fc)
    st, _ = w.http("GET", "/home-sample?name=" + quote("01 beach.jpg"))
    st6, _ = w.http("GET", "/home-sample-faces")
    case("once a post kit exists, the routes serve nothing", st == 404 and st6 == 404, (st, st6))


def check_browser(c, w, d):
    c.init_script("window.__asked = []; (function(){ const f = window.fetch; window.fetch = function(u, o){ window.__asked.push(String(u)); return f.apply(this, arguments); }; })();")
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    with v30.Kits(w):
        time.sleep(1.1)
        c.open(w.url("/home"))
        c.wait_for("document.querySelectorAll('.hello .bgs img.on').length === 1 && document.querySelectorAll('#tiles img[src]').length === 4 "
                   "&& [...document.querySelectorAll('#tiles img[src]')].every(i => i.complete && i.naturalWidth > 0)", 25)
        time.sleep(0.5)
        g = c.js("(function(){ const on = document.querySelector('.hello .bgs img.on'), n = document.getElementById('sampleNote'), r = n.getBoundingClientRect();"
                 " return {hello: on.getAttribute('src'), faces: on.dataset.faces, tiles: [...document.querySelectorAll('#tiles img')].map(i => i.getAttribute('src')),"
                 " note: n.textContent, shown: !n.hidden && r.width > 0 && r.height > 0, inHello: n.closest('#hello') !== null,"
                 " btn: document.getElementById('kitsBtn').textContent}; })()")
        case("a brand-new Assistant: the hello opens on the first wide sample, its face aimed at", g["hello"] == "/home-sample?name=01%20beach.jpg" and g["faces"] == "1", g)
        case("...the four tiles show samples, four different ones, none the hello's",
             all(t and t.startswith("/home-sample?name=") for t in g["tiles"]) and len(set(g["tiles"])) == 4 and g["hello"] not in g["tiles"], g["tiles"])
        case("...her line shows on the hello, whole", g["note"] == NOTE and g["shown"] and g["inHello"], g)
        case("...still 'Create your post kits', nothing broken, nothing from the internet",
             g["btn"] == "Create your post kits →" and not c.page_errors() and not c.outside_requests(), (g["btn"], c.page_errors()))
        asked = c.js("window.__asked")
        case("...no kit photo or kit face is asked for", not any("/kit-photo" in u or "/kit-faces" in u for u in asked), asked)
        # the first post kit comes in: the page reloads itself (the 4-second look), and the samples are gone
        time.sleep(1.2)
        away = w.work / "kits-away"
        (away / v30.A).rename(w.content / v30.A)
        try:
            c.wait_for("!document.getElementById('sampleNote') && document.querySelectorAll('.hello .bgs img.on').length === 1", 20)
            time.sleep(0.5)
            h = c.js("({hello: document.querySelector('.hello .bgs img.on').getAttribute('src'), tiles: [...document.querySelectorAll('#tiles img[src]')].map(i => i.getAttribute('src'))})")
            case("a first post kit comes in while the page is open: it reloads by itself, the line is gone, the photos are theirs",
                 h["hello"].startswith("/kit-photo?") and not any("home-sample" in t for t in h["tiles"]), h)
        finally:
            (w.content / v30.A).rename(away / v30.A)
        # an empty folder: grey, no line
        hold = w.work / "samples-away"
        d.rename(hold)
        d.mkdir()
        try:
            time.sleep(1.2)
            c.open(w.url("/home"))
            c.wait_for("!!document.querySelector('.hello h2')", 15)
            time.sleep(1.2)
            e = c.js("({imgs: document.querySelectorAll('.hello img[src], #tiles img[src]').length, note: !!document.getElementById('sampleNote'), "
                     "hello: getComputedStyle(document.getElementById('hello')).backgroundColor})")
            case("an empty samples folder: the grey placeholders stay, no line", e["imgs"] == 0 and not e["note"] and e["hello"] == "rgb(211, 205, 196)", e)
        finally:
            d.rmdir()
            hold.rename(d)
    # their own kits: no samples at all
    time.sleep(1.2)
    c.js("window.__asked = []")
    c.open(w.url("/home"))
    c.wait_for("document.querySelectorAll('.hello .bgs img.on').length === 1 && document.querySelectorAll('#tiles img[src]').length === 4", 25)
    time.sleep(0.8)
    k = c.js("({note: !!document.getElementById('sampleNote'), srcs: [...document.querySelectorAll('img[src]')].map(i => i.getAttribute('src')), asked: window.__asked})")
    case("with their own post kits: no sample anywhere on the page, none asked for", not k["note"] and not any("home-sample" in u for u in k["srcs"] + k["asked"]), k)
    for path in ("/posting.html", "/make-posts", "/backups"):
        c.open(w.url(path))
        time.sleep(1.5)
        srcs = c.js("[...document.querySelectorAll('img')].map(i => i.getAttribute('src') || '').concat(window.__asked || [])")
        case("%s never shows a sample" % path, not any("home-sample" in u for u in srcs), srcs)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards")
    ap.add_argument("--port", type=int, default=9990)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8790, 8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        print("SKIP  the pretend kits and samples are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="home-samples-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    d = work / "samples"
    outside = work / "elsewhere" / "outside.jpg"
    w = v28.World(work, a.port)
    env = dict(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none", STUDIO_NO_WINDOWS_FOR_TESTS="1",
               FACES_PRETEND=str(w.pretend), STUDIO_SAMPLES_FOR_TESTS=str(d))
    w.env.update(env)
    os.environ.update(env)
    try:
        w.build()
        w.posting(pieces=[])
        for k in (v30.A, v30.B):
            w.previews(k)
        v30.pretend_faces(w)
        make_samples(d, outside)
        faces_table(w)
        sys.path.insert(0, str(SCRIPTS))
        import home
        case("the test's own scratch home, never the real one", Path(home.HOME) == w.home and ".studio" not in str(home.HOME))
        group("what the Assistant says and draws", check_python, w, d, outside)
        w.start()
        case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
        group("the routes", check_routes, w, d, outside)
        if a.no_chrome or not chrome_drive.find_chrome():
            print("SKIP  the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1440, 900)) as c:
                group("the page in a browser", check_browser, c, w, d)
    finally:
        w.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(base), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return v30.summary()


if __name__ == "__main__":
    sys.exit(main())
