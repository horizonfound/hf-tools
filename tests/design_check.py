#!/usr/bin/env python3
"""Check the carousel designer's server side without a browser: the routes, the records, the commands.

    python3 tests/design_check.py                                  makes its own pretend kits under /private/tmp
    python3 tests/design_check.py --work /private/tmp/somewhere --port 8920

It makes a pretend Assistant with tests/fake_kit.py in a new folder under /private/tmp (it refuses anywhere
else): three shoots (an ordinary one, one with accents in its name, one with large photos). It points
STUDIO_HOME at it, starts the page server on a scratch port under the Mac's own /usr/bin/python3 (the Python a
new Mac comes with, which is what the plugin must run on), and prints one PASS or FAIL line per case. It never
touches the real ~/.studio and never uses the ports the real pages use. The server it starts is stopped at the
end, whatever happened. The work folder is left in place so a failure can be looked at; it is this script's
own scratch and can be thrown away.

Run it with a Python that has Pillow (python3, 3.12 on this Mac): the finished slides it sends are real
1080x1350 JPEGs drawn here, and fake_kit.py needs Pillow too. Pillow is used by this test only, never by the
plugin.

Three parts (--only server | page | browser runs one): the server side, by requests (below); the page's own
scripts by themselves, under the Mac's own JavaScript engine; and the real page in a hidden Chrome driven by
tests/chrome_drive.py (SKIP when there is no Chrome). The last two are in tests/design_page_check.py (the
strip, the frames, the tray) and tests/design_text_check.py (text boxes, fonts, brand colors; --only text
runs just its browser part), and tests/design_save_check.py (designs, templates, the shoot menu, the preview
and Save slides, with Pillow reading every slide the page saved; --only designs runs just that part and its
own page checks). The browser part uses --port + 5 and --port + 7 for a page server of its own, --port + 8
for the text part's and --port + 9 for the designs part's. The text and designs parts ask Google Fonts for
a few fonts when the internet is there, and skip those checks when it is not.

A fourth part, tests/design_wire_check.py (--only wire runs just it, on --port + 4): the designer as part of
the Assistant. The kit page and the posting queue showing the newest laid-out set, the plain slides again
after a new order from the picker, a Canva carousel fetched after a save, the line home.py pending prints and
design.py took clears, and the two "Lay out the slides" links pressed in the hidden Chrome.

A fifth part, tests/design_fix_check.py (--only fixes runs just it, on --port + 11 to + 14): what the
reviewers of the designer found, each with a case that failed before its fix. Slides that have been in the
Carousel folder are never moved out or cleared; "Already saved" only when the very same slides would be made
(a photo exported again, a font, a new name); unfinished saves never lock Save slides; a drive that will not
take a change is said as that; the line for Claude after a folder is renamed; names in any alphabet.

A sixth part, tests/design_layout_check.py (--only layout runs just it, on --port + 20): the page's arrangement
after the hand test of Nov 6, measured at four window sizes and two narrow ones: two rows of tools, one bar for
the selected thing that never moves the strip, the strip's starting size and the Size slider, the clip at the
strip's edges, the sheets that never scroll the page behind, and the names a screen reader hears.

Exit 0 when every case passes, 1 otherwise. When there is no Chrome the parts that drive the real page are
skipped, and the last line says so: a run like that has not looked at the page.
"""
import argparse
import copy
import hashlib
import http.client
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FONTS = ROOT / "plugins" / "the-engine" / "shared" / "fonts"
SAFE = Path("/private/tmp")
NEVER_PORTS = {8790, 8765, 8770, 8899} | set(range(8850, 8867))
PY = sys.executable
APPLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else PY     # what the plugin's own code runs under

results = []
SEEN = []           # every answer a designer route gave, for the "no path, no file name" check at the end


def case(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + ((" -> " + str(detail)[:400]) if detail and not ok else ""), flush=True)
    return bool(ok)


class Server:
    def __init__(self, env, port):
        self.env, self.want, self.port, self.proc = env, port, None, None

    def start(self):
        if any(p in NEVER_PORTS for p in range(self.want, self.want + 20)):
            raise SystemExit("STOP: that port range reaches one the real pages use.")
        self.proc = subprocess.Popen([APPLE, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env)
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise SystemExit(f"STOP: the page server did not start ({line.strip()!r}).")
        self.port = int(m.group(1))
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                return self.port
            except OSError:
                time.sleep(0.1)
        raise SystemExit("STOP: the page server did not answer.")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


def ask(port, method, path, body=None, headers=None, timeout=90):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        if path.startswith("/design"):
            SEEN.append((method + " " + path.split("?")[0], data))
        return r.status, {k.lower(): v for k, v in r.getheaders()}, data
    finally:
        c.close()


def get_json(port, path):
    code, _, data = ask(port, "GET", path)
    try:
        return code, json.loads(data)
    except ValueError:
        return code, None


def post(port, path, obj=None, headers=None, raw=None):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    body = raw if raw is not None else json.dumps(obj).encode("utf-8")
    code, _, data = ask(port, "POST", path, body=body, headers=h)
    try:
        return code, json.loads(data)
    except ValueError:
        return code, None


def raw_request(port, text):
    """Send bytes exactly as written (a request whose body never comes). The status line back."""
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        s.sendall(text.encode())
        s.settimeout(8)
        got = b""
        while b"\r\n" not in got:
            more = s.recv(4096)
            if not more:
                break
            got += more
        return got.split(b"\r\n")[0].decode(errors="replace")
    except socket.timeout:
        return "(no answer: the server hung)"
    finally:
        s.close()


def run(env, script, *args, more=None, py=None):
    e = dict(env)
    e.update(more or {})
    r = subprocess.run([py or APPLE, str(SCRIPTS / script), *args], capture_output=True, text=True, env=e, timeout=300)
    return r.returncode, (r.stdout + r.stderr).strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree_print(folder, skip=()):
    """Every file under a folder with its hash: to prove nothing in it was changed."""
    out = {}
    folder = Path(folder)
    if not folder.is_dir():
        return out
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if p.is_file() and not any(rel == s or rel.startswith(s + "/") for s in skip):
            out[rel] = sha(p.read_bytes())
    return out


def jpeg(w=1080, h=1350, seed=0, quality=85):
    """A real JPEG drawn here (the test only): a colour, a box and a few lines, different for every seed."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), ((seed * 53) % 256, (seed * 97 + 40) % 256, (seed * 31 + 90) % 256))
    d = ImageDraw.Draw(im)
    d.rectangle([w // 6, h // 6, w // 2 + (seed * 7) % 200, h // 2], fill=(250, 240, 220))
    for k in range(6):
        d.line([0, (k + 1) * h // 8, w, (k + 1) * h // 8 + seed % 40], fill=(20, 20, 30), width=3)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def png(w=1080, h=1350):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (10, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def jpeg_size(data):
    from PIL import Image
    try:
        return Image.open(io.BytesIO(data)).size
    except Exception:  # noqa: BLE001
        return None


def fold(name):
    return unicodedata.normalize("NFC", name).casefold()


def make_kit(target, name, photos, megapixels=0):
    cmd = [PY, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", str(photos), "--name", name]
    if megapixels:
        cmd += ["--megapixels", str(megapixels)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def check_all(work, port):
    target = work / "fake"
    ok, out = make_kit(target, "Fake beach", 14)
    if not case("the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    ok, out = make_kit(target, "Zoë Été", 8)
    case("a second pretend kit, with accents in its name", ok, out)
    ok, out = make_kit(target, "Big photos", 8, megapixels=13)
    case("a third pretend kit, with photos larger than 4320 on the long edge", ok, out)
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    content = target / "The Assistant" / "Your Content"
    kit_name = "2026-11-01 Fake beach"
    kit = content / kit_name
    KQ = quote(kit_name)
    kit2_name = next(n for n in os.listdir(content) if fold(n) == fold("2026-11-01 Zoë Été"))
    kit2 = content / kit2_name
    K2 = quote(kit2_name)
    kit3_name = "2026-11-01 Big photos"
    kit3 = content / kit3_name
    K3 = quote(kit3_name)
    designs = kit / ".kit" / "designs"
    car = kit / "Carousel"
    rec_file = kit / ".kit" / "kit.json"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
    on_sheet = [x["n"] for x in sheet]

    # the plain slides first (kit.py's own), plus a Canva slide and a file of the photographer's own, so the
    # Carousel folder holds things a save must never touch
    code, out = run(env, "kit.py", "build", kit_name)
    case("kit.py build made the plain slides (so the Carousel folder is not empty)", code == 0 and car.is_dir() and len(list(car.glob("Slide *.jpg"))) >= 2, out[-300:])
    (car / "Slide 01 (Canva).jpg").write_bytes(jpeg(seed=901))
    (car / "my own picture.jpg").write_bytes(jpeg(seed=902))
    photos_before = tree_print(kit / "Photos")
    car_before = tree_print(car)
    rec_before = rec_file.read_bytes()

    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (page server on port {P} under {APPLE}, STUDIO_HOME={studio})", flush=True)

        # ---------- the page and the state ----------
        code, h, data = ask(P, "GET", f"/design.html?kit={KQ}")
        page = data.decode("utf-8", "replace")
        case("page: /design.html answers with a page that names the shoot only by its folder name",
             code == 200 and h.get("content-type", "").startswith("text/html") and "data-kit='2026-11-01 Fake beach'" in page, (code, page[:200]))
        csp = h.get("content-security-policy", "")
        case("page: the browser is told no script from anywhere, and fonts only from Google or the Assistant",
             "script-src 'unsafe-inline'" in csp and "https://fonts.googleapis.com" in csp and "https://fonts.gstatic.com" in csp
             and "default-src 'self'" in csp and "http:" not in csp.replace("https:", ""), csp)
        code, h, data = ask(P, "GET", "/design.html?kit=No%20such%20shoot")
        case("page: a shoot that isn't there gets the plain 'can't find' page, not an error", code == 200 and b"find that shoot" in data, (code, data[:200]))
        code, h, data = ask(P, "GET", f"/design.html?kit={KQ}", headers={"Host": "evil.example"})
        case("page: a request sent under another site's name is refused", code == 403, code)
        code, h, data = ask(P, "GET", f"/design-state?kit={KQ}", headers={"Host": "evil.example"})
        case("state: a request sent under another site's name is refused", code == 403, code)
        for bad in ("..", "%2e%2e", ".kit", "Your%20Content%20old", quote(str(kit), safe=""), quote(kit_name.upper()), ""):
            code, st = get_json(P, f"/design-state?kit={bad}")
            case(f"state: kit={bad[:40] or '(empty)'} is refused in plain words", code == 404 and st and st.get("ok") is False and st.get("words"), (code, st))

        code, h, data = ask(P, "GET", f"/design-state?kit={KQ}", headers={"Sec-Fetch-Site": "cross-site"})
        case("state: a question put by another website through the browser is refused, and makes no design", code == 403 and (not designs.exists() or not list(designs.glob("*.json"))), code)
        case("state: before the first visit the shoot has no design on the drive", not designs.exists() or not list(designs.glob("*.json")))
        code, st = get_json(P, f"/design-state?kit={KQ}")
        if not case("state: the first visit answers", code == 200 and st and st.get("ok") is True, (code, st)):
            return
        d = st["design"]
        DID, STAMP = d["id"], st["stamp"]
        carousel = json.loads(rec_file.read_text(encoding="utf-8"))["picks"]["carousel"]
        case("state: the first visit made one design, named '<Shoot name> carousel 1'", d["name"] == "Fake beach carousel 1" and len(st["designs"]) == 1 and st["designs"][0]["open"] is True, (d["name"], st["designs"]))
        case("state: it is one photo per slide, in the carousel's order, each filling its slide",
             d["state"]["slides"] == len(carousel) and [b["n"] for b in d["state"]["blocks"]] == carousel
             and all(b["x"] == i * 1080 and b["y"] == 0 and b["w"] == 1080 and b["h"] == 1350 for i, b in enumerate(d["state"]["blocks"])), d["state"])
        case("state: on the kit's slide background", d["state"]["bg"] == "#ffffff" and st["slide_bg"] == "#ffffff", d["state"]["bg"])
        case("state: the design's id was made by the server (lower-case letters and digits)", re.fullmatch(r"[a-z][a-z0-9]{5,23}", DID), DID)
        f = designs / f"{DID}.json"
        on_disk = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        case("state: the design is on the drive as {id, name, updated, rev, state}", all(k in on_disk for k in ("id", "name", "updated", "rev", "state")) and on_disk["rev"] == 0 and on_disk["state"] == d["state"], list(on_disk))
        code, st2 = get_json(P, f"/design-state?kit={KQ}")
        case("state: a second visit makes no second design", code == 200 and len(st2["designs"]) == 1 and st2["design"]["id"] == DID and len(list(designs.glob("*.json"))) == 1, st2.get("designs"))
        case("state: every photo of the shoot is listed by number, with its shape and whether its copy is made",
             [p["n"] for p in st["photos"]] == on_sheet and all(set(p) >= {"n", "way", "w", "h", "v", "missing", "have"} for p in st["photos"]), st["photos"][:2])
        case("state: the four sizes of copy are named", st["sizes"] == {"s": 520, "l": 1600, "x": 2400, "xx": 4320}, st["sizes"])
        case("state: the carousel's order is given for 'One photo per slide'", st["carousel"] == carousel, st["carousel"])
        case("state: the eleven starter templates, every frame empty", len(st["starters"]) == 11 and all(
            all(b.get("type") == "text" or b["n"] is None for b in s["template"]["blocks"]) and s["template"]["blocks"] for s in st["starters"]),
            [s["name"] for s in st["starters"]])
        title = next((s for s in st["starters"] if s["id"] == "st-title"), None)
        case("state: the Title slide starter carries two text boxes and four frames", title and sum(1 for b in title["template"]["blocks"] if b.get("type") == "text") == 2
             and sum(1 for b in title["template"]["blocks"] if b.get("type") != "text") == 4, title)
        groups = {g["name"]: g["fonts"] for g in st["fonts"]["groups"]}
        own = sorted(x["name"] for fs in groups.values() for x in fs if x["own"])
        case("state: the font list has Serif, Sans and Script groups", list(groups) == ["Serif", "Sans", "Script"] and len(groups["Serif"]) == 12 and len(groups["Sans"]) == 12 and len(groups["Script"]) == 7, {k: len(v) for k, v in groups.items()})
        case("state: the five families the plugin carries are marked as its own", own == ["Cormorant Garamond", "DM Sans", "Fraunces", "Inter", "Montserrat"], own)
        case("state: every own face names a font file the plugin has", st["fonts"]["faces"] and all((FONTS / (x["file"] + ".ttf")).is_file() for x in st["fonts"]["faces"]), st["fonts"]["faces"])
        case("state: the fallback font and the rule for a font's name are given", st["fonts"]["fallback"] == "Georgia" and re.fullmatch(st["fonts"]["pattern"], "Old Standard TT") and not re.fullmatch(st["fonts"]["pattern"], "x'; }"), st["fonts"])
        shoots = {s["kit"]: s for s in st["shoots"]}
        case("state: the shoot menu lists every shoot with its photo count and design count, this one marked open",
             set(shoots) == {kit_name, kit2_name, kit3_name} and shoots[kit_name]["photos"] == 14 and shoots[kit_name]["designs"] == 1
             and shoots[kit_name]["open"] is True and shoots[kit2_name]["designs"] == 0 and shoots[kit2_name]["open"] is False, st["shoots"])
        case("state: the look-alike folder beside Your Content is not a shoot", not any("Sneaky" in s["kit"] or "old" in s["kit"] for s in st["shoots"]), st["shoots"])
        case("state: no brand colors, no templates, no fonts of their own yet", st["brand"] == {"colors": [], "max": 16} and st["templates"] == [] and st["fonts"]["yours"] == [], (st["brand"], st["templates"]))
        case("state: the limits are given (1 to 20 slides: one slide on its own is a single post; 80 blocks, 2,000 letters)", st["limits"]["slides"] == [1, 20] and st["limits"]["blocks"] == 80 and st["limits"]["text"] == 2000, st["limits"])
        code, st3 = get_json(P, f"/design-state?kit={KQ}&design=dnosuchdesign1")
        case("state: asking for a design that isn't there gives the newest, and says so", code == 200 and st3["design"]["id"] == DID and st3["fell_back"] is True, (code, st3 and st3.get("fell_back")))
        code, st3 = get_json(P, f"/design-state?kit={KQ}&design=..%2Fx")
        case("state: a design id that is not an id gives the newest, and says so", code == 200 and st3["design"]["id"] == DID and st3["fell_back"] is True, code)
        case("state: none of this wrote the kit's own record", rec_file.read_bytes() == rec_before)

        # ---------- saving a design ----------
        STATE = copy.deepcopy(d["state"])
        REV = [0]

        def body(state=None, **over):
            b = {"kit": kit_name, "design": DID, "stamp": STAMP, "base": REV[0], "page": "checkpage1", "state": copy.deepcopy(state if state is not None else STATE)}
            b.update(over)
            return b

        s1 = copy.deepcopy(STATE)
        s1["blocks"][0].update(x=40.123456, y=12.5, w=900, h=1200, ox=0.25, zoom=1.5)
        code, out = post(P, "/design", body(s1))
        case("save: a changed layout is taken, and the counter goes up by one", code == 200 and out == dict(out, ok=True, words="Saved", rev=1), (code, out))
        on_disk = json.loads(f.read_text(encoding="utf-8"))
        b0 = on_disk["state"]["blocks"][0]
        case("save: the drive holds the new layout, numbers rounded", on_disk["rev"] == 1 and b0["x"] == 40.12 and b0["y"] == 12.5 and b0["w"] == 900 and b0["ox"] == 0.25 and b0["zoom"] == 1.5, b0)
        prev = designs / f"{DID}.prev.json"
        case("save: the version before is kept beside it", prev.is_file() and json.loads(prev.read_text(encoding="utf-8"))["state"] == STATE and json.loads(prev.read_text(encoding="utf-8"))["rev"] == 0)
        STATE, REV[0] = on_disk["state"], 1
        before = f.read_bytes()
        code, out = post(P, "/design", body())
        case("save: sending exactly what is stored is fine and writes nothing", code == 200 and out["rev"] == 1 and f.read_bytes() == before, (code, out))
        code, out = post(P, "/design", body(base=0))
        case("save: the same again from an older counter is still fine (nothing would change)", code == 200 and out["rev"] == 1 and f.read_bytes() == before, (code, out))
        code, out = post(P, "/design", body(name="  Beach   day one \n"))
        on_disk = json.loads(f.read_text(encoding="utf-8"))
        case("save: a new name is kept (tidied to one line), counter up", code == 200 and out["rev"] == 2 and on_disk["name"] == "Beach day one", (code, out, on_disk.get("name")))
        REV[0] = 2
        s2 = copy.deepcopy(STATE)
        s2["bg"] = "#F4EFE6"
        code, out = post(P, "/design", body(s2, base=1, page="otherpage22"))
        case("save: a change from a page that has not seen the newest is refused, and given the newest",
             code == 409 and out.get("why") == "newer" and out.get("words") and out["design"]["rev"] == 2 and out["design"]["name"] == "Beach day one", (code, out))
        code, out = post(P, "/design", body(s2))
        case("save: the same change from the page that has seen it is taken (color kept in small letters)", code == 200 and out["rev"] == 3 and json.loads(f.read_text(encoding="utf-8"))["state"]["bg"] == "#f4efe6", (code, out))
        s3 = copy.deepcopy(s2)
        s3["slides"] = 3
        s3["blocks"] = s3["blocks"][:3]
        code, out = post(P, "/design", body(s3, base=2))
        case("save: a page whose last answer was lost carries on from the counter it knew, and is taken", code == 200 and out["rev"] == 4, (code, out))
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], 4
        code, out = post(P, "/design", body(stamp="000000000000"))
        case("save: a page that opened before the photos changed is told so", code == 409 and out.get("why") == "photos" and out.get("design"), (code, out))
        s4 = copy.deepcopy(STATE)
        s4["extra"] = "x"
        s4["blocks"][0].update(z=-5, evil="<script>", ox=7, oy=-3, zoom=99)
        code, out = post(P, "/design", body(s4))
        b0 = json.loads(f.read_text(encoding="utf-8"))["state"]["blocks"][0]
        case("save: keys the Assistant does not know are dropped", code == 200 and "z" not in b0 and "evil" not in b0 and "extra" not in json.loads(f.read_text(encoding="utf-8"))["state"], b0)
        case("save: where the photo sits in its frame, and its zoom, are brought into range", b0["ox"] == 1 and b0["oy"] == 0 and b0["zoom"] == 3, b0)
        REV[0] = out["rev"] if code == 200 else REV[0]
        text = {"id": 50, "type": "text", "text": "Zoë & Émile\r\nby the sea", "font": "Playfair Display", "size": 110, "weight": 700, "italic": True, "upper": False,
                "al": "left", "ls": 4, "lh": 1.2, "color": "#FFFFFF", "x": 120, "y": 500, "w": 820, "h": 264}
        hole = {"id": 51, "n": None, "x": 2200, "y": 100, "w": 600, "h": 800, "border": {"w": 12, "color": "#C4683F"}, "slot": 3}
        s5 = copy.deepcopy(STATE)
        s5["blocks"] += [text, hole]
        code, out = post(P, "/design", body(s5))
        kept = json.loads(f.read_text(encoding="utf-8"))["state"]["blocks"]
        t_kept, h_kept = kept[-2], kept[-1]
        case("save: a text box is kept with every part of its style, line ends made plain", code == 200 and t_kept == dict(text, text="Zoë & Émile\nby the sea", color="#ffffff"), t_kept)
        case("save: an empty frame with a border is kept (crop back to the middle)", h_kept == {"id": 51, "n": None, "x": 2200, "y": 100, "w": 600, "h": 800, "ox": 0.5, "oy": 0.5, "zoom": 1, "border": {"w": 12, "color": "#c4683f"}, "slot": 3}, h_kept)
        case("save: the order of the blocks is the order sent (which is the stacking)", [b["id"] for b in kept] == [b["id"] for b in s5["blocks"]], [b["id"] for b in kept])
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]
        case("save: the answer says whether a set of slides has been saved from this design (none yet)", out.get("set") is None and out.get("unfinished") is False, out)

        # the first change of a new day keeps the design as it stood at the end of the day before
        dj = json.loads(f.read_text(encoding="utf-8"))
        dj["updated"] = "2026-10-01T21:00:00"           # the test's own hand on its own scratch: as if last saved on an earlier day
        f.write_text(json.dumps(dj, indent=1, ensure_ascii=False), encoding="utf-8")
        yesterday = json.loads(f.read_text(encoding="utf-8"))
        s_day = copy.deepcopy(STATE)
        s_day["blocks"][1]["y"] = 3
        code, out = post(P, "/design", body(s_day))
        kept_day = designs / "earlier" / f"{DID} 2026-10-01.json"
        case("save: the first change of a new day keeps the design as it stood the day before, under that day's date",
             code == 200 and kept_day.is_file() and json.loads(kept_day.read_text(encoding="utf-8")) == yesterday, (code, list((designs / "earlier").glob("*")) if (designs / "earlier").is_dir() else "no folder"))
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]
        code, out = post(P, "/design", body(dict(STATE, bg="#fefefe")))
        case("save: a second change the same day does not write over that kept version", code == 200 and json.loads(kept_day.read_text(encoding="utf-8")) == yesterday and len(list((designs / "earlier").glob("*"))) == 1)
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]
        # a design file that something else damaged is left alone and simply not shown
        (designs / "dbrokenfile01.json").write_text("{ this is not a design", encoding="utf-8")
        (designs / "dbrokenfile02.json").write_text(json.dumps({"id": "dbrokenfile02", "name": "Planted", "rev": 0, "state": {"slides": 3, "bg": "javascript:alert(1)", "blocks": []}}), encoding="utf-8")
        code, st = get_json(P, f"/design-state?kit={KQ}&design=dbrokenfile02")
        case("state: a design file that is damaged, or holds a layout that fails the checks, is not shown, and is left as it is",
             code == 200 and st["fell_back"] is True and [x["id"] for x in st["designs"]] == [DID] and (designs / "dbrokenfile01.json").read_text(encoding="utf-8") == "{ this is not a design", (code, st and st["designs"]))
        code, out = post(P, "/design", dict(body(dict(STATE, bg="#000000")), design="dbrokenfile02"))
        case("save refused: into a design file whose layout fails the checks", code == 404 and out.get("why") == "design", (code, out))
        for n in ("dbrokenfile01.json", "dbrokenfile02.json"):
            os.rename(designs / n, work / n)            # out of the way of the counts below (the test's own files)

        # ---------- every refusal, with the design file unchanged after each ----------
        def refused(name, b=None, code_want=400, why=None, headers=None, raw=None, words=None):
            was = tree_print(designs)
            code, out = post(P, "/design", b, headers=headers, raw=raw)
            good = (code == code_want and isinstance(out, dict) and out.get("ok") is False and bool(out.get("words"))
                    and (why is None or out.get("why") == why) and (words is None or words in out.get("words", "")))
            case(f"save refused, nothing written: {name}", good and tree_print(designs) == was, (code, out))

        def with_block(i, **ch):
            s = copy.deepcopy(STATE)
            s["blocks"][i].update(ch)
            return body(s)

        def with_state(**ch):
            s = copy.deepcopy(STATE)
            s.update(ch)
            return body(s)

        ti = len(STATE["blocks"]) - 2       # the text box
        refused("0 slides", with_state(slides=0), why="slides")
        refused("21 slides", with_state(slides=21), why="slides")
        refused("slides as a word", with_state(slides="3"), why="slides")
        refused("slides as true", with_state(slides=True), why="slides")
        refused("slides as 3.5", with_state(slides=3.5), why="slides")
        refused("a background that is a word (red)", with_state(bg="red"), why="bg")
        refused("a three-letter color (#fff)", with_state(bg="#fff"), why="bg")
        refused("a background with a script in it", with_state(bg="#fff;}</style>"), why="bg")
        many = copy.deepcopy(STATE)
        many["blocks"] = [{"id": i + 1, "n": None, "x": 10, "y": 10, "w": 100, "h": 100} for i in range(81)]
        refused("81 blocks", body(many), why="many", words="up to 80")
        many_t = copy.deepcopy(STATE)
        many_t["blocks"] = [dict(text, id=i + 1) for i in range(41)]
        refused("41 text boxes", body(many_t), why="many")
        refused("blocks that are not a list", with_state(blocks={"a": 1}), why="shape")
        refused("a block that is a word", with_state(blocks=["x"]), why="block")
        refused("a block of an unknown kind", with_block(0, type="video"), why="block")
        refused("a photo number that is not on the list", with_block(0, n=9999), why="photo")
        refused("a photo number of 0", with_block(0, n=0), why="photo")
        refused("a photo number of 1.5", with_block(0, n=1.5), why="photo")
        refused("a photo named by a file name", with_block(0, n="beach-001.jpg"), why="photo")
        refused("a frame 10 wide", with_block(0, w=10), why="frame")
        refused("a frame 10 tall", with_block(0, h=10), why="frame")
        refused("a frame taller than a slide", with_block(0, h=2000), why="frame")
        refused("a frame wider than the whole strip", with_block(0, w=1080 * 3 + 1), why="frame")
        refused("a frame a billion pixels to the right", with_block(0, x=1e9), why="frame")
        refused("a frame wholly off the strip to the left", with_block(0, x=-5000), why="frame")
        refused("a frame wholly below the strip", with_block(0, y=1340), why="frame")
        refused("a frame with no x at all", body({"slides": 3, "bg": "#ffffff", "blocks": [{"id": 1, "n": None, "y": 0, "w": 100, "h": 100}]}), why="frame")
        refused("x as a word", with_block(0, x="12"), why="frame")
        refused("x as true", with_block(0, x=True), why="frame")
        nan = json.dumps(with_block(0, x="@@")).replace('"@@"', "NaN").encode()
        refused("x that is NaN", raw=nan, why="frame")
        inf = json.dumps(with_block(0, w="@@")).replace('"@@"', "Infinity").encode()
        refused("a width that is Infinity", raw=inf, why="frame")
        zn = json.dumps(with_block(0, zoom="@@")).replace('"@@"', "NaN").encode()
        refused("a zoom that is NaN", raw=zn, why="crop")
        huge = json.dumps(with_block(0, x="@@")).replace('"@@"', "1" + "0" * 400).encode()
        refused("x with four hundred digits", raw=huge)
        refused("two blocks with the same id", with_block(1, id=STATE["blocks"][0]["id"]), why="id")
        refused("a block id of 0", with_block(0, id=0), why="id")
        refused("a block id that is a word", with_block(0, id="a"), why="id")
        refused("a border that is a word", with_block(0, border="thick"), why="border")
        refused("a border 500 wide", with_block(0, border={"w": 500, "color": "#000000"}), why="border")
        refused("a border in a color that is a word", with_block(0, border={"w": 5, "color": "blue"}), why="border")
        refused("a slot that is a word", with_block(0, slot="first"), why="slot")
        refused("a font name with a quote and a brace in it", with_block(ti, font="Evil'; } body{"), why="font", words="font")
        refused("a font name that is an address", with_block(ti, font="https://evil.example/x.css"), why="font")
        refused("a font name with two spaces together", with_block(ti, font="Old  Standard"), why="font")
        refused("a font name 60 letters long", with_block(ti, font="A" * 60), why="font")
        refused("a font name that is a number", with_block(ti, font=12), why="font")
        refused("text 2,001 letters long", with_block(ti, text="x" * 2001), why="long", words="text box")
        refused("text that is a list", with_block(ti, text=["a"]), why="text")
        refused("text with a control character in it", with_block(ti, text="a\x00b"), why="text")
        refused("a text size of 2", with_block(ti, size=2), why="style")
        refused("a text size of 5000", with_block(ti, size=5000), why="style")
        refused("a weight of 500", with_block(ti, weight=500), why="style")
        refused("a weight of '700'", with_block(ti, weight="700"), why="style")
        refused("italic as a word", with_block(ti, italic="yes"), why="style")
        refused("all capitals as 1", with_block(ti, upper=1), why="style")
        refused("an alignment of 'justify'", with_block(ti, al="justify"), why="style")
        refused("letter spacing of 9000", with_block(ti, ls=9000), why="style")
        refused("line spacing of 9", with_block(ti, lh=9), why="style")
        refused("a text color that is a word", with_block(ti, color="white"), why="style")
        refused("a text box 20 wide", with_block(ti, w=20), why="frame")
        refused("a text box with no height", with_block(ti, h=0), why="frame")
        lots = copy.deepcopy(STATE)
        lots["blocks"] = [dict(text, id=i + 1, text="y" * 1999) for i in range(12)]
        refused("more than 20,000 letters in all", body(lots), why="long")
        refused("a state that is a word", dict(body(), state="hello"), why="shape")
        refused("no state at all", {k: v for k, v in body().items() if k != "state"}, why="shape")
        refused("an older counter with a real change", dict(with_state(bg="#101010"), base=0, page="otherpage22"), code_want=409, why="newer")
        refused("a counter that is a word", dict(with_state(bg="#101010"), base="4"), why="page")
        refused("a counter below zero", dict(with_state(bg="#101010"), base=-1), why="page")
        refused("no page name", {k: v for k, v in with_state(bg="#101010").items() if k != "page"}, why="page")
        refused("a page name with a slash", dict(with_state(bg="#101010"), page="../../x"), why="page")
        refused("a design id that is not an id", dict(with_state(bg="#101010"), design="../x"), why="design")
        refused("a design that is not there", dict(with_state(bg="#101010"), design="dnosuchdesign1"), code_want=404, why="design")
        refused("a shoot that is not there", dict(with_state(bg="#101010"), kit="No such shoot"), code_want=404)
        refused("a shoot named by '..'", dict(with_state(bg="#101010"), kit=".."), code_want=404)
        refused("a shoot named by its full path", dict(with_state(bg="#101010"), kit=str(kit)), code_want=404)
        refused("an empty name", dict(with_state(bg="#101010"), name="   "), why="name", words="name")
        refused("a name 81 letters long", dict(with_state(bg="#101010"), name="n" * 81), why="name")
        refused("a name that is a number", dict(with_state(bg="#101010"), name=5), why="name")
        refused("another site's Origin", with_state(bg="#101010"), code_want=403, headers={"Origin": "http://evil.example"})
        refused("the right name on another port as Origin", with_state(bg="#101010"), code_want=403, headers={"Origin": f"http://127.0.0.1:{P + 1}"})
        refused("another site's name as Host", with_state(bg="#101010"), code_want=403, headers={"Host": "evil.example"})
        refused("sent as plain text", with_state(bg="#101010"), code_want=415, headers={"Content-Type": "text/plain"})
        refused("sent as a form", with_state(bg="#101010"), code_want=415, headers={"Content-Type": "application/x-www-form-urlencoded"})
        refused("a body that is not JSON", raw=b"{not json")
        refused("a body that is a list", raw=b"[1,2,3]")
        refused("a body nested a hundred thousand deep", raw=b"[" * 100000)
        big = dict(with_state(bg="#101010"), pad="p" * 300000)
        refused("a body of 300,000 bytes", big, code_want=413)
        line = raw_request(P, f"POST /design HTTP/1.1\r\nHost: 127.0.0.1:{P}\r\nContent-Type: application/json\r\n\r\n")
        case("save refused: no length given", " 400 " in line + " ", line)
        was = tree_print(designs)
        code, out = post(P, "/design", dict(with_state(bg="#101010"), page="checkpage1"), headers={"Origin": f"http://127.0.0.1:{P}"})
        case("save: the page's own Origin is taken", code == 200 and out["rev"] == REV[0] + 1 and tree_print(designs) != was, (code, out))
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]
        code, out = post(P, "/design", body(), headers={"Origin": f"http://localhost:{P}", "Host": f"localhost:{P}"})
        case("save: the same server under the name localhost is taken", code == 200, (code, out))
        case("save: after all of that the kit's own record is as it was", rec_file.read_bytes() == rec_before)

        # ---------- new designs never take the place of another ----------
        first_bytes = f.read_bytes()
        blank = {"slides": 5, "bg": "#ffffff", "blocks": []}
        code, out = post(P, "/design-new", {"kit": kit_name, "stamp": STAMP, "state": blank, "token": "newtoken01"})
        D2 = out["design"]["id"] if code == 200 else ""
        case("new design: a blank one is made, with the next free name", code == 200 and out["design"]["name"] == "Fake beach carousel 1" and out["design"]["rev"] == 0 and D2 != DID
             and out["design"]["state"] == blank, (code, out and out.get("design")))
        case("new design: the open one is untouched, byte for byte", f.read_bytes() == first_bytes and len(list(designs.glob("d*.json"))) - len(list(designs.glob("*.prev.json"))) == 2)
        case("new design: the answer lists both designs, the new one open", code == 200 and [x["id"] for x in out["designs"]] == [D2, DID] and out["designs"][0]["open"] is True, out and out.get("designs"))
        code, again = post(P, "/design-new", {"kit": kit_name, "stamp": STAMP, "state": blank, "token": "newtoken01"})
        case("new design: the same press sent twice gives the same design, not a third", code == 200 and again["design"]["id"] == D2 and len(again["designs"]) == 2, (code, again and again.get("designs")))
        code, out = post(P, "/design-new", {"kit": kit_name, "token": "newtoken02"})
        D3 = out["design"]["id"] if code == 200 else ""
        case("new design: with no layout sent it is one photo per slide, named with the next number", code == 200 and out["design"]["name"] == "Fake beach carousel 2"
             and [b["n"] for b in out["design"]["state"]["blocks"]] == carousel, (code, out and out["design"]["name"]))
        code, out = post(P, "/design-new", {"kit": kit_name, "copy": DID, "token": "newtoken03"})
        D4 = out["design"]["id"] if code == 200 else ""
        case("new design: Duplicate makes '<name> copy' with the same layout, and leaves the first alone", code == 200 and out["design"]["name"] == "Beach day one copy"
             and out["design"]["state"] == STATE and f.read_bytes() == first_bytes, (code, out and out["design"]["name"]))
        code, out = post(P, "/design-new", {"kit": kit_name, "copy": DID, "token": "newtoken04"})
        case("new design: a second Duplicate is '<name> copy 2'", code == 200 and out["design"]["name"] == "Beach day one copy 2", (code, out and out["design"]["name"]))
        code, out = post(P, "/design-new", {"kit": kit_name, "state": blank, "name": "Twin", "token": "newtoken05"})
        D5 = out["design"]["id"] if code == 200 else ""
        code2, out2 = post(P, "/design-new", {"kit": kit_name, "state": blank, "name": "Twin", "token": "newtoken06"})
        D6 = out2["design"]["id"] if code2 == 200 else ""
        case("new design: a name of their own is kept, and two designs may share one", code == 200 and code2 == 200 and out["design"]["name"] == "Twin" == out2["design"]["name"] and D5 != D6, (code, code2))
        n_designs = len(list(designs.glob("*.json"))) - len(list(designs.glob("*.prev.json")))

        def new_refused(name, b, code_want=400, headers=None):
            was = tree_print(designs)
            code, out = post(P, "/design-new", b, headers=headers)
            case(f"new design refused, nothing made: {name}", code == code_want and isinstance(out, dict) and out.get("ok") is False and out.get("words") and tree_print(designs) == was, (code, out))

        new_refused("a layout with 0 slides", {"kit": kit_name, "state": {"slides": 0, "bg": "#ffffff", "blocks": []}, "token": "newtoken10"})
        new_refused("a photo that is not on the list", {"kit": kit_name, "state": {"slides": 2, "bg": "#ffffff", "blocks": [{"id": 1, "n": 9999, "x": 0, "y": 0, "w": 100, "h": 100}]}, "token": "newtoken11"})
        new_refused("a token that is not a token", {"kit": kit_name, "state": blank, "token": "../x"})
        new_refused("a copy of a design that is not there", {"kit": kit_name, "copy": "dnosuchdesign1", "token": "newtoken12"}, 404)
        new_refused("a copy and a layout at once", {"kit": kit_name, "copy": DID, "state": blank, "token": "newtoken13"})
        new_refused("an empty name", {"kit": kit_name, "state": blank, "name": "", "token": "newtoken14"})
        new_refused("a stamp from before the photos changed", {"kit": kit_name, "stamp": "000000000000", "state": blank, "token": "newtoken15"}, 409)
        new_refused("a shoot that is not there", {"kit": "Nope", "state": blank, "token": "newtoken16"}, 404)
        new_refused("another site's Origin", {"kit": kit_name, "state": blank, "token": "newtoken17"}, 403, headers={"Origin": "http://evil.example"})
        case("new design: after the refusals the shoot has exactly the designs it had", len(list(designs.glob("*.json"))) - len(list(designs.glob("*.prev.json"))) == n_designs == 7, n_designs)
        code, st = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        case("state: asking for a design by its id opens that one; the list is this shoot's only", code == 200 and st["design"]["id"] == DID and st["fell_back"] is False and len(st["designs"]) == 7
             and sum(1 for x in st["designs"] if x["open"]) == 1, (code, st and len(st["designs"])))
        code, stz = get_json(P, f"/design-state?kit={K2}")
        Z_ID = stz["design"]["id"] if code == 200 else ""
        case("state: the accented shoot's first design is named after it, and its list holds only its own", code == 200 and fold(stz["design"]["name"]) == fold("Zoë Été carousel 1") and len(stz["designs"]) == 1
             and stz["shoots"] and next(s for s in stz["shoots"] if s["open"])["kit"] == kit2_name, (code, stz and stz["design"]["name"]))

        # ---------- templates: shared by every shoot, no photo in them ----------
        tpl_dir = studio / "design-templates"
        code, out = post(P, "/design-template", {"kit": kit_name, "name": "My wide opener", "state": STATE, "token": "tpltoken01"})
        T1 = out["template"]["id"] if code == 200 else ""
        tfile = tpl_dir / f"{T1}.json"
        case("template: saved, with words that say where to find it", code == 200 and "My wide opener" in out.get("words", "") and tfile.is_file(), (code, out))
        tpl = json.loads(tfile.read_text(encoding="utf-8")) if tfile.is_file() else {"template": {"blocks": []}}
        frames = [b for b in tpl["template"]["blocks"] if b.get("type") != "text"]
        case("template: it holds no photo number, and every crop is back to the middle", frames and all(b["n"] is None and b["ox"] == 0.5 and b["oy"] == 0.5 and b["zoom"] == 1 for b in frames), frames)
        case("template: frames are numbered in reading order; text and border are kept; it says which shoot it came from",
             sorted(b["slot"] for b in frames) == list(range(1, len(frames) + 1)) and [b["slot"] for b in sorted(frames, key=lambda b: (b["x"], b["y"]))] == list(range(1, len(frames) + 1))
             and any(b.get("type") == "text" and b["text"] == "Zoë & Émile\nby the sea" for b in tpl["template"]["blocks"]) and any("border" in b for b in frames)
             and tpl.get("from") == "Fake beach", tpl)
        case("template: no file name of a photo is in it", "beach-0" not in tfile.read_text(encoding="utf-8") if tfile.is_file() else False)
        code, again = post(P, "/design-template", {"kit": kit_name, "name": "My wide opener", "state": STATE, "token": "tpltoken01"})
        case("template: the same press sent twice saves one template", code == 200 and again["template"]["id"] == T1 and len(list(tpl_dir.glob("*.json"))) == 1, (code, len(list(tpl_dir.glob("*.json")))))
        for name, b, want in (("an empty design", {"kit": kit_name, "name": "Empty", "state": blank, "token": "tpltoken02"}, 400),
                              ("no name", {"kit": kit_name, "name": " ", "state": STATE, "token": "tpltoken03"}, 400),
                              ("a layout that is not one", {"kit": kit_name, "name": "Bad", "state": {"slides": 99}, "token": "tpltoken04"}, 400),
                              ("a shoot that is not there", {"kit": "Nope", "name": "Bad", "state": STATE, "token": "tpltoken05"}, 404)):
            was = tree_print(tpl_dir)
            code, out = post(P, "/design-template", b)
            case(f"template refused, nothing saved: {name}", code == want and out and out.get("ok") is False and out.get("words") and tree_print(tpl_dir) == was, (code, out))
        code, st = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        code2, stz = get_json(P, f"/design-state?kit={K2}")
        case("template: it comes back in this shoot's state and in another shoot's, the same", code == 200 and code2 == 200 and len(st["templates"]) == 1 and st["templates"] == stz["templates"]
             and st["templates"][0]["template"] == tpl["template"] and st["templates"][0]["name"] == "My wide opener", (st and st["templates"]))

        # ---------- brand colors and fonts: shared by every shoot ----------
        code, out = post(P, "/design-brand", {"add": "#C4683F"})
        case("brand: a color is saved (in small letters)", code == 200 and out == {"ok": True, "colors": ["#c4683f"]}, (code, out))
        code, out = post(P, "/design-brand", {"add": "#c4683f"})
        case("brand: the same color again is not saved twice", code == 200 and out["colors"] == ["#c4683f"], (code, out))
        for name, b in (("a word", {"add": "red"}), ("a number", {"add": 5}), ("add and remove at once", {"add": "#111111", "remove": "#c4683f"}), ("nothing", {})):
            was = (studio / "brand.json").read_bytes()
            code, out = post(P, "/design-brand", b)
            case(f"brand refused, nothing changed: {name}", code == 400 and out.get("ok") is False and (studio / "brand.json").read_bytes() == was, (code, out))
        for i in range(15):
            post(P, "/design-brand", {"add": "#0000%02x" % i})
        code, out = post(P, "/design-brand", {"add": "#abcdef"})
        case("brand: a 17th color is refused in plain words, and none is dropped to make room", code == 409 and "16" in out.get("words", "") and len(out["colors"]) == 16 and out["colors"][0] == "#c4683f", (code, out))
        code, out = post(P, "/design-brand", {"remove": "#000003"})
        bj = json.loads((studio / "brand.json").read_text(encoding="utf-8"))
        case("brand: a color can be taken off the list, and is kept in the file as removed", code == 200 and "#000003" not in out["colors"] and len(out["colors"]) == 15
             and any(x.get("color") == "#000003" for x in bj.get("removed", [])), (code, out, bj.get("removed")))
        code, st = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        code2, stz = get_json(P, f"/design-state?kit={K2}")
        case("brand: the colors come back for every shoot, in the order saved", st["brand"]["colors"] == stz["brand"]["colors"] == out["colors"] and st["brand"]["colors"][0] == "#c4683f", st["brand"])
        code, out = post(P, "/design-brand", {"add": "#111111"}, headers={"Origin": "http://evil.example"})
        case("brand refused: another site's Origin", code == 403, code)

        code, out = post(P, "/design-font", {"add": "Lobster"})
        case("fonts: a font loaded by name is kept under Yours", code == 200 and out == {"ok": True, "yours": ["Lobster"]}, (code, out))
        code, out = post(P, "/design-font", {"add": "Zen Kaku Gothic Antique"})
        code, out = post(P, "/design-font", {"add": "Lobster"})
        case("fonts: newest first, and never twice", code == 200 and out["yours"] == ["Zen Kaku Gothic Antique", "Lobster"], (code, out))
        code, out = post(P, "/design-font", {"add": "Inter"})
        case("fonts: one that is already on the list is not added to Yours", code == 200 and "Inter" not in out["yours"], (code, out))
        for bad in ("Evil'; }", "a/b", "x" * 51, "", " Lobster", "Lob  ster", "https://x", 7, None):
            was = (studio / "design-fonts.json").read_bytes()
            code, out = post(P, "/design-font", {"add": bad})
            case(f"fonts refused, nothing changed: {str(bad)[:20]!r}", code == 400 and out.get("ok") is False and out.get("words") and (studio / "design-fonts.json").read_bytes() == was, (code, out))
        code, st = get_json(P, f"/design-state?kit={K2}")
        case("fonts: Yours comes back for every shoot", st["fonts"]["yours"] == ["Zen Kaku Gothic Antique", "Lobster"], st["fonts"]["yours"])
        code, h, data = ask(P, "GET", "/design-font-file?f=Inter-Regular")
        case("font file: one of the plugin's own font files is served, byte for byte", code == 200 and h.get("content-type") == "font/ttf" and data == (FONTS / "Inter-Regular.ttf").read_bytes(), (code, h.get("content-type"), len(data)))
        for bad in ("..%2F..%2Fdesign.py", "Inter-Regular.ttf", "CormorantGaramond-Light", "", "%2Fetc%2Fpasswd", "Inter-Regular%00"):
            code, h, data = ask(P, "GET", f"/design-font-file?f={bad}")
            case(f"font file refused: f={bad or '(empty)'}", code == 404, code)

        # ---------- the two larger copies of a photo ----------
        prev1 = kit / ".kit" / "previews"
        run(env, "arrange.py", "previews", kit_name)
        row = next(x for x in sheet if x["n"] == 1)
        own = max(row["w"], row["h"])
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n=1&size=x")
        case(f"larger copy: a photo {own} px long asked for at 2400 comes at its own size, never blown up", code == 200 and 1600 < own < 2400 and max(jpeg_size(data) or (0, 0)) == own, (code, own, jpeg_size(data)))
        code, h, data2 = ask(P, "GET", f"/kit-photo?kit={KQ}&n=1&size=xx")
        case("larger copy: asked for at 4320 it is the same copy, and no second file is made", code == 200 and data2 == data and not [n for n in os.listdir(prev1) if n.startswith("0001-4320-")]
             and len([n for n in os.listdir(prev1) if n.startswith("0001-2400-")]) == 1, (code, [n for n in os.listdir(prev1) if n.startswith("0001-")]))
        small = next(x for x in sheet if "small" in x["file"])
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n={small['n']}&size=xx")
        case("larger copy: a small photo asked for at 4320 comes at its own size, from the copy already made", code == 200 and jpeg_size(data) == (small["w"], small["h"])
             and not [n for n in os.listdir(prev1) if n.startswith(f"{small['n']:04d}-") and ("-2400-" in n or "-4320-" in n)], (code, jpeg_size(data)))
        case("larger copy: nothing in the Photos folder was changed or added", tree_print(kit / "Photos") == photos_before)
        sheet3 = json.loads((kit3 / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
        big_row = next(x for x in sheet3 if max(x["w"], x["h"]) > 4320 and x["file"].lower().endswith(".jpg"))
        run(env, "arrange.py", "previews", kit3_name)
        prev3 = kit3 / ".kit" / "previews"
        got = {}

        def fetch(size, key):
            got[key] = ask(P, "GET", f"/kit-photo?kit={K3}&n={big_row['n']}&size={size}")

        ts = [threading.Thread(target=fetch, args=("x", "x1")), threading.Thread(target=fetch, args=("x", "x2")), threading.Thread(target=fetch, args=("xx", "xx"))]
        for t in ts:
            t.start()
        for t in ts:
            t.join(180)
        case("larger copy: a large photo at 2400 is 2400 on its long edge", got.get("x1", (0,))[0] == 200 and max(jpeg_size(got["x1"][2]) or (0, 0)) == 2400, jpeg_size(got["x1"][2]) if "x1" in got else got)
        case("larger copy: at 4320 it is 4320 on its long edge (the photo itself is larger)", got.get("xx", (0,))[0] == 200 and max(jpeg_size(got["xx"][2]) or (0, 0)) == 4320 and max(big_row["w"], big_row["h"]) > 4320, jpeg_size(got["xx"][2]) if "xx" in got else got)
        names3 = os.listdir(prev3)
        case("larger copy: two requests at once made one file, and no half-made file is left", got.get("x2", (0,))[0] == 200 and got["x1"][2] == got["x2"][2]
             and len([n for n in names3 if n.startswith(f"{big_row['n']:04d}-2400-")]) == 1 and not [n for n in names3 if n.startswith(".")], names3)
        code, h, data = ask(P, "GET", f"/kit-photo?kit={K3}&n={big_row['n']}&size=xxx")
        case("larger copy: a size that is not one of the four is refused", code == 404, code)

        # ---------- finished slides: staging ----------
        staging = kit / ".kit" / "design-staging"
        everything_else = lambda: tree_print(kit, skip=(".kit/design-staging", ".kit/previews"))   # noqa: E731
        was_all = everything_else()
        S = [jpeg(seed=i) for i in range(1, 30)]
        JH = {"Content-Type": "image/jpeg"}

        def slide(tok, i, of, data, did=None, headers=None, kitq=None):
            code, _, out = ask(P, "POST", f"/design-slide?kit={kitq or KQ}&design={did or DID}&set={tok}&i={i}&of={of}", body=data, headers=headers or JH)
            try:
                return code, json.loads(out)
            except ValueError:
                return code, None

        def slide_refused(name, tok, i, of, data, code_want=400, did=None, headers=None, kitq=None):
            code, out = slide(tok, i, of, data, did=did, headers=headers, kitq=kitq)
            case(f"slide refused: {name}", code == code_want and isinstance(out, dict) and out.get("ok") is False and out.get("words"), (code, out))

        slide_refused("a PNG", "settoken01", 1, 3, png())
        slide_refused("a JPEG that is 2000 by 2000", "settoken01", 1, 3, jpeg(2000, 2000, 5))
        slide_refused("a JPEG that is 1350 by 1080 (on its side)", "settoken01", 1, 3, jpeg(1350, 1080, 5))
        slide_refused("a JPEG cut off before its end", "settoken01", 1, 3, S[0][:-200])
        slide_refused("a JPEG with something after its end", "settoken01", 1, 3, S[0] + b"<script>")
        slide_refused("a body of 500 bytes", "settoken01", 1, 3, S[0][:498] + b"\xff\xd9")
        slide_refused("words, sent as a JPEG", "settoken01", 1, 3, b"hello " * 400)
        slide_refused("a set name that is too short (AB)", "AB", 1, 3, S[0])
        slide_refused("a set name with capitals", "SETTOKEN01", 1, 3, S[0])
        slide_refused("a set name that is a path", "..%2F..%2Fx", 1, 3, S[0])
        slide_refused("slide 0", "settoken01", 0, 3, S[0])
        slide_refused("slide 4 of 3", "settoken01", 4, 3, S[0])
        slide_refused("slide 1 of 0", "settoken01", 1, 0, S[0])
        slide_refused("slide 1 of 1 for a design of 3 slides", "settoken01", 1, 1, S[0], 409)
        slide_refused("slide 1 of 21", "settoken01", 1, 21, S[0])
        slide_refused("a slide number that is a word", "settoken01", "one", 3, S[0])
        slide_refused("a slide number below zero", "settoken01", -1, 3, S[0])
        slide_refused("a count that is not the design's (5 of a 3-slide design)", "settoken01", 1, 5, S[0], 409)
        slide_refused("a design that is not there", "settoken01", 1, 3, S[0], 404, did="dnosuchdesign1")
        slide_refused("a design id that is a path", "settoken01", 1, 3, S[0], 400, did="..%2Fx")
        slide_refused("a shoot that is not there", "settoken01", 1, 3, S[0], 404, kitq="Nope")
        slide_refused("sent as JSON", "settoken01", 1, 3, S[0], 415, headers={"Content-Type": "application/json"})
        slide_refused("another site's Origin", "settoken01", 1, 3, S[0], 403, headers={"Content-Type": "image/jpeg", "Origin": "http://evil.example"})
        slide_refused("another site's name as Host", "settoken01", 1, 3, S[0], 403, headers={"Content-Type": "image/jpeg", "Host": "evil.example"})
        line = raw_request(P, f"POST /design-slide?kit={KQ}&design={DID}&set=settoken01&i=1&of=3 HTTP/1.1\r\nHost: 127.0.0.1:{P}\r\nContent-Type: image/jpeg\r\nContent-Length: 13000000\r\n\r\n")
        case("slide refused: a body of 13 MB, before a byte of it is read", " 413 " in line + " ", line)
        case("slides: after every refusal nothing is staged, and nothing else in the kit was written", not staging.exists() or not any(p.is_file() for p in staging.rglob("*")), list(staging.rglob("*")) if staging.exists() else "")
        case("slides: ...and the Carousel folder and the rest of the kit are as they were", everything_else() == was_all and tree_print(car) == car_before)

        staging.mkdir(exist_ok=True)
        for k in range(60):
            (staging / f"dfillerdesign-fillertoken{k:02d}").mkdir()        # sixty saves that never finished arriving
        slide_refused("a sixty-first unfinished save, while sixty are waiting", "settoken01", 1, 3, S[0], 503)
        for k in range(60):
            os.rmdir(staging / f"dfillerdesign-fillertoken{k:02d}")         # the test's own empty folders
        code, out = slide("settoken01", 1, 3, S[0])
        case("slides: a real 1080x1350 JPEG is taken, into staging only", code == 200 and out == {"ok": True, "i": 1, "of": 3, "have": 1}
             and (staging / f"{DID}-settoken01" / "slide-01.jpg").read_bytes() == S[0] and tree_print(car) == car_before, (code, out))
        code, out = slide("settoken01", 1, 3, S[0])
        case("slides: the same slide sent again (its answer was lost) is fine", code == 200 and out["have"] == 1, (code, out))
        code, out = slide("settoken01", 1, 3, S[1])
        case("slides: a different picture for a slide that has arrived is refused, and the first is kept", code == 409 and out.get("why") == "again" and (staging / f"{DID}-settoken01" / "slide-01.jpg").read_bytes() == S[0], (code, out))
        code, out = slide("settoken01", 3, 3, S[2])
        case("slides: slides may arrive in any order", code == 200 and out["have"] == 2, (code, out))
        case("slides: no half-written file is left in staging", not [p for p in staging.rglob(".part-*")])

        # ---------- finished slides: the commit ----------
        def commit(tok, did=None, rev=None, count=None, kitname=None, headers=None, **more):
            b = {"kit": kitname or kit_name, "design": did or DID, "set": tok, "rev": REV[0] if rev is None else rev}
            if count is not None:
                b["count"] = count
            b.update(more)
            return post(P, "/design-commit", b, headers=headers)

        def new_in_car(folder=None, before=None):
            return sorted(set(tree_print(folder or car)) - set(before if before is not None else car_before))

        code, out = commit("settoken01", count=3)
        case("commit refused: a slide is missing from staging; nothing moved", code == 400 and out.get("why") == "missing" and out.get("words") and tree_print(car) == car_before, (code, out))
        slide("settoken01", 2, 3, S[1])
        for name, b, want in (("an older counter (the design changed since the slides were drawn)", {"rev": REV[0] - 1}, 409),
                              ("a count that is not the design's", {"count": 7}, 409),
                              ("a set name that is a path", {"tok": "../x"}, 400),
                              ("a design that is not there", {"did": "dnosuchdesign1"}, 404),
                              ("a counter that is a word", {"rev": "5"}, 400),
                              ("a shoot that is not there", {"kitname": "Nope"}, 404),
                              ("another site's Origin", {"headers": {"Origin": "http://evil.example"}}, 403)):
            kw = dict(b)
            tok = kw.pop("tok", "settoken01")
            code, out = commit(tok, **kw)
            case(f"commit refused, nothing moved: {name}", code == want and out and out.get("ok") is False and out.get("words") and tree_print(car) == car_before, (code, out))
        case("commit: up to here the kit's own record has never been written by the page server", rec_file.read_bytes() == rec_before)

        code, out = commit("settoken01", count=3)
        BASE1 = "Beach day one"
        names1 = [f"{BASE1} - slide {i:02d}.jpg" for i in (1, 2, 3)]
        case("commit: the set is saved, and the words say how many, under what name, and that nothing was replaced",
             code == 200 and out.get("ok") is True and out.get("already") is False and out.get("base") == BASE1 and out.get("count") == 3
             and out.get("words") == f"Saved 3 slides in your Carousel folder, named \"{BASE1}\". Nothing was replaced.", (code, out))
        now = tree_print(car)
        case("commit: exactly the set is new in the Carousel folder, named '<design name> - slide NN.jpg'", new_in_car() == names1, new_in_car())
        case("commit: each slide is byte for byte what the page sent", [now.get(n) for n in names1] == [sha(S[0]), sha(S[1]), sha(S[2])])
        case("commit: every file that was there before has the same hash (plain slides, the Canva slide, their own file)", all(now.get(k) == v for k, v in car_before.items()) and len(car_before) >= 4)
        case("commit: the Photos folder is unchanged", tree_print(kit / "Photos") == photos_before)
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("commit: the kit's record names the set as the newest laid-out one, and lists it", rec.get("carousel_set", {}).get("kind") == "laid-out" and rec["carousel_set"]["base"] == BASE1
             and rec["carousel_set"]["files"] == names1 and len(rec.get("laid_out", [])) == 1 and rec["laid_out"][0]["files"] == names1, rec.get("carousel_set"))
        case("commit: the plain slides are still the kit's own made pieces, and its picks are as they were", rec.get("made_pieces", {}).get("carousel") == json.loads(rec_before)["made_pieces"]["carousel"]
             and rec.get("picks") == json.loads(rec_before)["picks"], rec.get("made_pieces"))
        jfile = designs / "sets" / f"{DID}-settoken01.json"
        j = json.loads(jfile.read_text(encoding="utf-8")) if jfile.is_file() else {}
        case("commit: the layout that made the set is kept with it, with each file's hash", j.get("state") == "done" and j.get("layout") == STATE and [x["sha256"] for x in j.get("files", [])] == [sha(S[0]), sha(S[1]), sha(S[2])], j.get("state"))
        case("commit: staging holds no slide of that set any more", not (staging / f"{DID}-settoken01").exists() or not list((staging / f"{DID}-settoken01").iterdir()))
        code, out2 = run(env, "home.py", "pending")
        case("commit: Claude is told through the waiting list (one line, counting slides)", f"ARRANGED: {kit_name} | design | 3 slides" in out2, out2[-300:])
        case("commit: the kit page was written again", (kit / ".kit" / "Post kit.html").is_file())
        rec_after1, car_after1 = rec_file.read_bytes(), tree_print(car)
        code, again = commit("settoken01", count=3)
        case("commit twice: the same answer, and nothing changes (no file, not the kit's record)", code == 200 and again == out and tree_print(car) == car_after1 and rec_file.read_bytes() == rec_after1, (code, again))
        code, o = run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken01", "--rev", str(REV[0]))
        case("commit twice, as Claude's command: the same, and nothing changes", code == 0 and "RESULT: " in o and json.loads(o.split("RESULT: ")[1])["state"] == "done" and tree_print(car) == car_after1 and rec_file.read_bytes() == rec_after1, o[-300:])
        code, out = slide("settoken01", 1, 3, S[5])
        case("slides: a slide for a set that is already saved is refused", code == 409 and out.get("why") == "again", (code, out))

        code, out = post(P, "/design", body())
        case("save: the answer now says the last set's name and that nothing has changed since", code == 200 and out["set"] and out["set"]["base"] == BASE1 and out["set"]["count"] == 3 and out["set"]["same"] is True
             and out["set"]["words"] == f"Already saved as \"{BASE1}\". Change something to save a new set.", (code, out))
        for i in (1, 2, 3):
            slide("settoken02", i, 3, S[2 + i])
        code, out = commit("settoken02", count=3)
        case("saved with nothing changed: 'Already saved as ...', and no new file", code == 200 and out.get("already") is True and out.get("base") == BASE1
             and out.get("words") == f"Already saved as \"{BASE1}\". Change something to save a new set." and tree_print(car) == car_after1 and rec_file.read_bytes() == rec_after1, (code, out))
        code, out = commit("settoken09", count=3)
        case("saved with nothing changed, and nothing sent at all: the same answer", code == 200 and out.get("already") is True and tree_print(car) == car_after1, (code, out))

        # a change, then a second save: a new set beside the first
        s6 = copy.deepcopy(STATE)
        s6["blocks"][1].update(x=s6["blocks"][1]["x"] + 30)
        code, out = post(P, "/design", body(s6))
        STATE, REV[0] = json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]
        case("save: after a change the answer says the last set no longer matches", code == 200 and out["set"]["same"] is False and out["set"]["base"] == BASE1, (code, out))
        for i in (1, 2, 3):
            slide("settoken03", i, 3, S[5 + i])
        code, out = commit("settoken03", count=3)
        BASE2 = f"{BASE1} (2)"
        names2 = [f"{BASE2} - slide {i:02d}.jpg" for i in (1, 2, 3)]
        now = tree_print(car)
        case("a second, changed save makes '<design name> (2)' beside the first", code == 200 and out.get("base") == BASE2 and new_in_car(before=car_after1) == names2, (code, out, new_in_car(before=car_after1)))
        case("...and the first set and everything else is byte for byte as it was", all(now.get(k) == v for k, v in car_after1.items()))
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("...and the kit's record names the second as the newest and lists both", rec["carousel_set"]["base"] == BASE2 and [x["base"] for x in rec["laid_out"]] == [BASE1, BASE2], rec.get("laid_out"))

        # ---------- a save that is cut off, three ways ----------
        def change():
            s = copy.deepcopy(STATE)
            s["blocks"][0]["x"] = s["blocks"][0]["x"] + 7
            code, out = post(P, "/design", body(s))
            return json.loads(f.read_text(encoding="utf-8"))["state"], out["rev"]

        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken04", i, 3, S[8 + i])
        car_b = tree_print(car)
        code, o = run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken04", "--rev", str(REV[0]), more={"DESIGN_TEST_STOP": "after-2"})
        BASE3 = f"{BASE1} (3)"
        j4 = json.loads((designs / "sets" / f"{DID}-settoken04.json").read_text(encoding="utf-8"))
        case("cut off after two files: the run died, two of the three slides are in, and it is written down as not finished",
             code == 9 and new_in_car(before=car_b) == [f"{BASE3} - slide 01.jpg", f"{BASE3} - slide 02.jpg"] and j4["state"] == "moving" and j4["base"] == BASE3, (code, new_in_car(before=car_b), j4.get("state")))
        code, st = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        case("cut off: the state tells the page a save of this design is unfinished", st["design"]["unfinished"] is True, st["design"].get("unfinished"))
        code, o = run(env, "design.py", "show", kit_name)
        case("cut off: design.py show says so to Claude", "NOT FINISHED" in o and BASE3 in o, o[-400:])
        code, out = commit("settoken04", count=3)
        now = tree_print(car)
        names3 = [f"{BASE3} - slide {i:02d}.jpg" for i in (1, 2, 3)]
        case("cut off: pressing Save slides again finishes it under the SAME name, with no extra set", code == 200 and out.get("base") == BASE3 and out.get("already") is False
             and new_in_car(before=car_b) == names3, (code, out, new_in_car(before=car_b)))
        j4 = json.loads((designs / "sets" / f"{DID}-settoken04.json").read_text(encoding="utf-8"))
        case("cut off: every file's hash matches what was written down before the first file moved", j4["state"] == "done" and [now[x["final"]] for x in j4["files"]] == [x["sha256"] for x in j4["files"]] == [sha(S[9]), sha(S[10]), sha(S[11])])
        case("cut off: everything that was there before is unchanged", all(now.get(k) == v for k, v in car_b.items()))
        code, st = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        case("cut off: once finished, the state no longer says unfinished, and names the set", st["design"]["unfinished"] is False and st["design"]["set"]["base"] == BASE3 and st["design"]["set"]["same"] is True, st["design"])

        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken05", i, 3, S[11 + i])
        car_b = tree_print(car)
        code, o = run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken05", "--rev", str(REV[0]), more={"DESIGN_TEST_STOP": "after-1"})
        BASE4 = f"{BASE1} (4)"
        # the page was reloaded: it knows nothing of that set, and presses Save slides afresh
        code, out = commit("settoken06", count=3)
        case("cut off, then the page reloaded and Save slides pressed afresh: the cut-off set is finished under its own name, and the words say saved",
             code == 200 and out.get("base") == BASE4 and out.get("already") is False and out.get("words", "").startswith("Saved 3 slides")
             and new_in_car(before=car_b) == [f"{BASE4} - slide {i:02d}.jpg" for i in (1, 2, 3)], (code, out, new_in_car(before=car_b)))
        for i in (1, 2, 3):
            slide("settoken07", i, 3, S[14 + i])
        code, out = commit("settoken07", count=3)
        case("...and one more press with new slides and nothing changed makes no extra set", code == 200 and out.get("already") is True and out.get("base") == BASE4
             and new_in_car(before=car_b) == [f"{BASE4} - slide {i:02d}.jpg" for i in (1, 2, 3)], (code, out))

        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken08", i, 3, S[17 + i])
        car_b, rec_b = tree_print(car), rec_file.read_bytes()
        code, o = run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken08", "--rev", str(REV[0]), more={"DESIGN_TEST_STOP": "after-journal"})
        case("cut off before any file moved: nothing is in the Carousel folder yet, and the name is already written down", code == 9 and tree_print(car) == car_b
             and json.loads((designs / "sets" / f"{DID}-settoken08.json").read_text(encoding="utf-8"))["base"] == f"{BASE1} (5)")
        code, o = run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken08", "--rev", str(REV[0]), more={"DESIGN_TEST_STOP": "after-record"})
        case("cut off after the kit's record, before the set was marked done: the files are all in", code == 9 and len(new_in_car(before=car_b)) == 3
             and json.loads((designs / "sets" / f"{DID}-settoken08.json").read_text(encoding="utf-8"))["state"] == "moving")
        rec_c, car_c = rec_file.read_bytes(), tree_print(car)
        code, out = commit("settoken08", count=3)
        case("...and the next try only marks it done: the same name, no file and no record changed", code == 200 and out.get("base") == f"{BASE1} (5)" and tree_print(car) == car_c and rec_file.read_bytes() == rec_c, (code, out))

        # a file turns up in the way of a set that was cut off: it is put back, never written over
        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken10", i, 3, S[20 + i])
        car_b = tree_print(car)
        run(env, "design.py", "commit", str(kit), "--design", DID, "--set", "settoken10", "--rev", str(REV[0]), more={"DESIGN_TEST_STOP": "after-1"})
        BASE6 = f"{BASE1} (6)"
        theirs = jpeg(seed=777)
        (car / f"{BASE6} - slide 02.jpg").write_bytes(theirs)
        code, out = commit("settoken10", count=3)
        BASE7 = f"{BASE1} (7)"
        now = tree_print(car)
        case("a file of theirs has the name a cut-off set needs: their file is untouched, and ours that was already in under that name is taken back out",
             now.get(f"{BASE6} - slide 02.jpg") == sha(theirs) and f"{BASE6} - slide 01.jpg" not in now and all(now.get(k) == v for k, v in car_b.items()), sorted(set(now) - set(car_b)))
        case("...and the same press saves the whole set under the next free name instead", code == 200 and out.get("base") == BASE7 and [now.get(f"{BASE7} - slide {i:02d}.jpg") for i in (1, 2, 3)] == [sha(S[21]), sha(S[22]), sha(S[23])]
             and sorted(set(now) - set(car_b)) == [f"{BASE6} - slide 02.jpg"] + [f"{BASE7} - slide {i:02d}.jpg" for i in (1, 2, 3)], (code, out, sorted(set(now) - set(car_b))))
        j10 = json.loads((designs / "sets" / f"{DID}-settoken10.json").read_text(encoding="utf-8"))
        case("...and the record keeps that the first name was given up, and why", j10["state"] == "done" and j10["base"] == BASE7 and j10.get("undone") and j10["undone"][0]["base"] == BASE6 and j10["undone"][0]["why"] == "clash", j10.get("undone"))

        # ---------- names: capitals, accents, and characters no drive takes ----------
        odd = 'A/B: "c"? <d>|e* (Canva) Zoë.  '
        code, out = post(P, "/design", body(name=odd))
        REV[0] = out["rev"]
        code, out = commit("settoken0a", count=3)
        # (until the reviewers' pass this was answered "already saved" under the old name; a new name is a change now:
        # see tests/design_fix_check.py part 3 for the set it then makes)
        case("a new name alone is a change: nothing is 'already saved' under the old name (and with no new slides sent, nothing is made)",
             code == 400 and out.get("why") == "missing" and tree_print(car) == now, (code, out))
        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken11", i, 3, S[i])
        car_b = tree_print(car)
        code, out = commit("settoken11", count=3)
        new = new_in_car(before=car_b)
        case("a design named with slashes, colons, quotes, stars and '(Canva)': saved under a name any drive takes", code == 200 and len(new) == 3 and out.get("base") == "A B c d e Zoë"
             and all(not re.search(r'[/\\:*?"<>|]', n) and "(Canva)" not in n and n.startswith("A B c d e Zoë - slide ") for n in new), (code, out, new))
        code, out = post(P, "/design", body(name="con"))
        REV[0] = out["rev"]
        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken12", i, 3, S[i + 3])
        code, out = commit("settoken12", count=3)
        case("a design named with a word Windows keeps for itself (con): the files get 'con_'", code == 200 and out.get("base") == "con_" and (car / "con_ - slide 01.jpg").is_file(), (code, out))
        code, out = post(P, "/design", body(name="BEACH DAY ONE"))
        REV[0] = out["rev"]
        STATE, REV[0] = change()
        for i in (1, 2, 3):
            slide("settoken13", i, 3, S[i + 6])
        car_b = tree_print(car)
        code, out = commit("settoken13", count=3)
        case("a design whose name differs from saved sets only in capitals: the first free name is counted without regard to capitals",
             code == 200 and out.get("base") == "BEACH DAY ONE (8)" and len(new_in_car(before=car_b)) == 3 and all(tree_print(car).get(k) == v for k, v in car_b.items()), (code, out))

        zcar = kit2 / "Carousel"
        zstate, zstamp = stz["design"]["state"], stz["stamp"]
        zslides = zstate["slides"]
        for i in range(1, zslides + 1):
            slide("zsettoken1", i, zslides, S[i], did=Z_ID, kitq=K2)
        code, out = commit("zsettoken1", did=Z_ID, rev=0, count=zslides, kitname=kit2_name)
        zbase = out.get("base", "") if out else ""
        znew = sorted(os.listdir(zcar)) if zcar.is_dir() else []
        case("the accented shoot: its first save is named after its design, accents and all", code == 200 and fold(zbase) == fold("Zoë Été carousel 1") and len(znew) == zslides
             and all(fold(n) == fold(f"{zbase} - slide {i:02d}.jpg") for i, n in enumerate(znew, 1)), (code, out, znew))
        # a drive that keeps accents its own way, and ignores capitals, would list a set like this one: the
        # next name must be counted as taken
        nfd = unicodedata.normalize("NFD", f"{zbase} (2) - slide 01.jpg").upper()
        (zcar / nfd).write_bytes(jpeg(seed=555))
        zs = copy.deepcopy(zstate)
        zs["bg"] = "#111111"
        code, out = post(P, "/design", {"kit": kit2_name, "design": Z_ID, "stamp": zstamp, "base": 0, "page": "checkpage1", "state": zs})
        for i in range(1, zslides + 1):
            slide("zsettoken2", i, zslides, S[i + 1], did=Z_ID, kitq=K2)
        zbefore = tree_print(zcar)
        code, out = commit("zsettoken2", did=Z_ID, rev=1, count=zslides, kitname=kit2_name)
        znow = tree_print(zcar)
        case("the accented shoot: a name already there with its accents kept another way and in capitals is counted as taken (the save becomes '... (3)')",
             code == 200 and fold(out.get("base", "")) == fold(f"{zbase} (3)") and all(znow.get(k) == v for k, v in zbefore.items()) and len(znow) == len(zbefore) + zslides, (code, out))
        case("the accented shoot: its saves went to its own Carousel folder, not the other shoot's", not [n for n in os.listdir(car) if "Été" in unicodedata.normalize("NFC", n)])

        # ---------- two saves at once ----------
        s_twin = {"slides": 2, "bg": "#ffffff", "blocks": [{"id": 1, "n": on_sheet[0], "x": 0, "y": 0, "w": 1080, "h": 1350}]}
        for did in (D5, D6):
            code, out = post(P, "/design", {"kit": kit_name, "design": did, "stamp": STAMP, "base": 0, "page": "checkpage1", "state": s_twin})
        for i in (1, 2):
            slide("racetoken1", i, 2, S[i], did=D5)
            slide("racetoken2", i, 2, S[i + 2], did=D6)
        car_b = tree_print(car)
        got = {}

        def go(key, tok, did):
            got[key] = commit(tok, did=did, rev=1, count=2)

        ts = [threading.Thread(target=go, args=("a", "racetoken1", D5)), threading.Thread(target=go, args=("b", "racetoken2", D6))]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        bases = sorted(x[1].get("base", "") for x in got.values() if x[1])
        now = tree_print(car)
        case("two designs with the same name saved at the same moment: two whole sets under two names", len(got) == 2 and all(x[0] == 200 for x in got.values()) and bases == ["Twin", "Twin (2)"]
             and len(new_in_car(before=car_b)) == 4, (got, new_in_car(before=car_b)))
        by = {got["a"][1]["base"]: (S[1], S[2]), got["b"][1]["base"]: (S[3], S[4])} if len(got) == 2 and all(x[1] and x[1].get("base") for x in got.values()) else {}
        case("...each set holds its own design's slides, and nothing was written over", by and all([now.get(f"{b} - slide 01.jpg"), now.get(f"{b} - slide 02.jpg")] == [sha(p[0]), sha(p[1])] for b, p in by.items())
             and all(now.get(k) == v for k, v in car_b.items()))
        s_twin2 = copy.deepcopy(s_twin)
        s_twin2["bg"] = "#222222"
        post(P, "/design", {"kit": kit_name, "design": D5, "stamp": STAMP, "base": 1, "page": "checkpage1", "state": s_twin2})
        for i in (1, 2):
            slide("racetoken3", i, 2, S[i + 4], did=D5)
            slide("racetoken4", i, 2, S[i + 6], did=D5)
        car_b = tree_print(car)
        got = {}

        def go2(key, tok):
            got[key] = commit(tok, did=D5, rev=2, count=2)

        ts = [threading.Thread(target=go2, args=("a", "racetoken3")), threading.Thread(target=go2, args=("b", "racetoken4"))]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        case("the same design saved twice at the same moment: one set, and both presses are told its name", len(got) == 2 and all(x[0] == 200 for x in got.values())
             and len({x[1]["base"] for x in got.values()}) == 1 and len(new_in_car(before=car_b)) == 2 and sorted(x[1]["already"] for x in got.values()) == [False, True], (got, new_in_car(before=car_b)))
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        case("the kit's record lists every set once, each with files that are in the folder", len(rec["laid_out"]) == len({(x["design"], x["token"]) for x in rec["laid_out"]})
             and all((car / n).is_file() for x in rec["laid_out"] for n in x["files"]), len(rec["laid_out"]))
        case("after every save the Photos folder is unchanged, and so is every file that was in the Carousel folder at the start", tree_print(kit / "Photos") == photos_before
             and all(tree_print(car).get(k) == v for k, v in car_before.items()))
        case("after every save no design's earlier version was lost: each design that changed has its version before", all((designs / f"{x}.prev.json").is_file() for x in (DID, D5, D6)))

        # ---------- the commands ----------
        code, o = run(env, "design.py", "show", kit_name)
        case("design.py show lists the designs and the sets saved from them", code == 0 and "Twin" in o and "saved" in o and "put back" not in o.split("Slides:")[0] and "newest laid-out set" in o, o[-500:])
        code, o = run(env, "design.py", "took", kit_name)
        code2, o2 = run(env, "home.py", "pending")
        case("design.py took clears the line that was waiting for Claude", code == 0 and "Cleared." in o and f"ARRANGED: {kit_name} | design" not in o2, (o, o2[-200:]))
        code, o = run(env, "design.py", "took", kit_name)
        case("design.py took twice says nothing was waiting", code == 0 and "Nothing was waiting" in o, o)
        url_file = studio / "posting-url.txt"
        if case("the page server's address on record is this test's own (so 'open' starts no other server)", url_file.is_file() and f":{P}/" in url_file.read_text()):
            code, o = run(env, "design.py", "open", "Fake beach", "--design", DID)
            case("design.py open prints the designer's address for that design", code == 0 and o.strip().endswith(f"http://127.0.0.1:{P}/design.html?kit={KQ}&design={DID}"), o[-300:])
            code, o = run(env, "design.py", "open", "Fake beach", "--design", "dnosuchdesign1")
            case("design.py open with a design that is not there stops and says so", code == 1 and "STOP" in o, o[-200:])
            code, o = run(env, "design.py", "open", "Big photos")
            case("design.py open on a shoot with no design yet makes its first one", code == 0 and "1 design" in o and f":{P}/design.html?kit={K3}&design=d" in o and len(list((kit3 / '.kit' / 'designs').glob('d*.json'))) == 1, o[-300:])
            code, st = get_json(P, f"/design-state?kit={K3}")
            case("...and the state for it shows that design, with the large photo still readable", code == 200 and st["design"]["name"] == "Big photos carousel 1" and len(st["designs"]) == 1
                 and not next(p for p in st["photos"] if p["n"] == big_row["n"])["missing"], code)
        code, o = run(env, "design.py", "commit", str(kit), "--design", "../x", "--set", "settoken01")
        case("design.py commit with ids that are not ids stops", code == 2 and "STOP" in o, o[-200:])

        # a planted template with a photo number in it, or a layout that fails the checks, is never handed to a page
        tpl_dir.mkdir(exist_ok=True)
        (tpl_dir / "tplantedfile1.json").write_text(json.dumps({"id": "tplantedfile1", "name": "Planted", "template": {"slides": 3, "bg": "#ffffff", "blocks": [{"id": 1, "n": 5, "x": 0, "y": 0, "w": 500, "h": 500}]}}), encoding="utf-8")
        (tpl_dir / "tplantedfile2.json").write_text("not json", encoding="utf-8")
        code, st = get_json(P, f"/design-state?kit={K2}")
        case("templates: a template file that holds a photo number, or is not a template, is not shown", code == 200 and [t["id"] for t in st["templates"]] == [T1], st and [t["id"] for t in st["templates"]])
        for n in ("tplantedfile1.json", "tplantedfile2.json"):
            os.rename(tpl_dir / n, work / n)

        # a shoot holds 200 designs at most (there is no way to delete one, so there is an end to making them)
        made, last = 1, None
        for k in range(199):
            code, last = post(P, "/design-new", {"kit": kit3_name, "state": {"slides": 2, "bg": "#ffffff", "blocks": []}, "token": f"filltoken{k:04d}"})
            made += 1 if code == 200 else 0
        code, out = post(P, "/design-new", {"kit": kit3_name, "state": {"slides": 2, "bg": "#ffffff", "blocks": []}, "token": "filltoken9999"})
        case("new design refused: a 201st design in one shoot, in plain words", made == 200 and code == 409 and out.get("why") == "full" and "200" in out.get("words", "")
             and len(list((kit3 / ".kit" / "designs").glob("d*.json"))) == 200, (made, code, out))
        code, st = get_json(P, f"/design-state?kit={K3}")
        case("...and the shoot's state still answers with all 200", code == 200 and len(st["designs"]) == 200, code)

        # ---------- the photos are numbered again: every photo is found by its file name ----------
        code, st = get_json(P, f"/design-state?kit={KQ}&design={D3}")
        d3 = st["design"]
        name_of = {x["n"]: Path(x["file"]).name for x in sheet}
        used = [b["n"] for b in d3["state"]["blocks"]]
        gone_n = used[1]
        aside = work / "moved-out"
        aside.mkdir(exist_ok=True)
        os.rename(kit / "Photos" / name_of[gone_n], aside / name_of[gone_n])       # the pretend photographer takes a photo out of the shoot
        code, o = run(env, "kit.py", "sheet", kit_name, py=PY)
        sheet_b = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]
        n_now = {Path(x["file"]).name: x["n"] for x in sheet_b}
        code, st = get_json(P, f"/design-state?kit={KQ}&design={D3}")
        d3b = st["design"]
        want = [n_now.get(name_of[n]) for n in used]
        case("photos numbered again: each frame still holds the same photo (found by its file name), the one that left is an empty frame",
             code == 200 and len(sheet_b) == len(sheet) - 1 and [b["n"] for b in d3b["state"]["blocks"]] == want and want[1] is None and want[0] is not None and want != used, ([b["n"] for b in d3b["state"]["blocks"]], want))
        case("photos numbered again: the design says one photo left, its counter went up, and the version before is kept", d3b["dropped"] == 1 and d3b["rev"] == d3["rev"] + 1
             and json.loads((designs / f"{D3}.prev.json").read_text(encoding="utf-8"))["state"] == d3["state"], (d3b["dropped"], d3b["rev"]))
        code, out = post(P, "/design", {"kit": kit_name, "design": D3, "stamp": STAMP, "base": d3["rev"], "page": "checkpage1", "state": d3["state"]})
        case("photos numbered again: a page still open from before is told the photos changed, and nothing is written", code == 409 and out.get("why") == "photos", (code, out))
        code, out = post(P, "/design", {"kit": kit_name, "design": D3, "stamp": st["stamp"], "base": d3b["rev"], "page": "checkpage1", "state": d3b["state"]})
        case("photos numbered again: the page that has the new list saves as usual", code == 200, (code, out))

        # ---------- a single post: a design of one slide (decision 12: one slide on its own is a single post) ----------
        code, st1 = get_json(P, f"/design-state?kit={KQ}")
        one = {"slides": 1, "bg": "#ffffff", "blocks": [{"id": 1, "n": sheet_b[0]["n"], "x": 0, "y": 0, "w": 1080, "h": 1350}]}
        code, out = post(P, "/design-new", {"kit": kit_name, "stamp": st1["stamp"], "state": one, "name": "Single post", "token": "onetoken001"})
        D1 = out["design"]["id"] if code == 200 and out and out.get("ok") else "dnosuchdesign1"
        case("a single post: a new design of one slide is taken", code == 200 and out["design"]["state"]["slides"] == 1, (code, out))
        slide_refused("a single post: slide 1 of 2 for a design of one slide", "onetoken002", 1, 2, S[9], 409, did=D1)
        code, out = slide("onetoken002", 1, 1, S[9], did=D1)
        case("a single post: its one slide is taken (slide 1 of 1)", code == 200 and out == {"ok": True, "i": 1, "of": 1, "have": 1}, (code, out))
        car_b = tree_print(car)
        code, out = commit("onetoken002", did=D1, rev=0, count=1)
        case("a single post: saved as one slide, and the words say '1 slide'", code == 200 and out.get("count") == 1 and out.get("base") == "Single post"
             and out.get("words") == "Saved 1 slide in your Carousel folder, named \"Single post\". Nothing was replaced.", (code, out))
        case("a single post: exactly one file is new in the Carousel folder, byte for byte the slide sent, and nothing that was there changed",
             new_in_car(before=car_b) == ["Single post - slide 01.jpg"] and tree_print(car).get("Single post - slide 01.jpg") == sha(S[9])
             and all(tree_print(car).get(k) == v for k, v in car_b.items()), new_in_car(before=car_b))
        code, o = run(env, "home.py", "pending")
        case("a single post: Claude is told one slide (not '1 slides')", f"ARRANGED: {kit_name} | design | 1 slide | Single post" in o, o[-300:])
        run(env, "design.py", "took", kit_name)
        code, o = run(env, "posting_queue.py", "add", "--kit", kit_name)
        pieces = json.loads((studio / "posting.json").read_text(encoding="utf-8"))["pieces"] if (studio / "posting.json").is_file() else []
        mine = [x for x in pieces if x.get("kit") and Path(x["kit"]).name == kit_name and x["id"].endswith("-carousel")]
        case("a single post: in the posting queue the one-slide set counts as a single post", code == 0 and len(mine) == 1 and mine[0]["kind"] == "single", (code, o[-200:], mine))
        two = {"slides": 2, "bg": "#ffffff", "blocks": [{"id": 1, "n": sheet_b[0]["n"], "x": 0, "y": 0, "w": 2160, "h": 1350}]}
        code, out = post(P, "/design", {"kit": kit_name, "design": D1, "stamp": st1["stamp"], "base": 0, "page": "checkpage1", "state": two})
        for i in (1, 2):
            slide("onetoken003", i, 2, S[9 + i], did=D1)
        code, out = commit("onetoken003", did=D1, rev=1, count=2)
        pieces = json.loads((studio / "posting.json").read_text(encoding="utf-8"))["pieces"]
        mine = [x for x in pieces if x["id"] == (mine[0]["id"] if mine else "")]
        case("a single post grown to two slides and saved: the queue's piece is a carousel again (same piece, same place)",
             code == 200 and out.get("count") == 2 and len(mine) == 1 and mine[0]["kind"] == "carousel", (code, out, mine))
        run(env, "design.py", "took", kit_name)

        # ---------- nothing is in the server's memory: stop it, start it on another port ----------
        code, before_stop = get_json(P, f"/design-state?kit={KQ}&design={DID}")
        STATE, REV[0], STAMP = before_stop["design"]["state"], before_stop["design"]["rev"], before_stop["stamp"]
        srv.stop()
        srv = Server(env, P + 3)
        P2 = srv.start()
        code, after = get_json(P2, f"/design-state?kit={KQ}&design={DID}")
        keys = ("design", "designs", "templates", "brand", "carousel", "stamp", "starters", "shoots")
        case(f"a server started afresh on another port ({P2}) gives the same designs, templates, colors and fonts", P2 != P and code == 200 and all(after[k] == before_stop[k] for k in keys)
             and after["fonts"] == before_stop["fonts"], [k for k in keys if after.get(k) != before_stop.get(k)])
        code, out = post(P2, "/design", body())
        case("...and a save carries on from the same counter", code == 200 and out["rev"] == REV[0], (code, out))

        # ---------- no path, no file name, in anything a page was sent ----------
        leaks = []
        for where, data in SEEN:
            text = data.decode("utf-8", "replace")
            if where.endswith("/design-font-file"):
                continue                # a font file's own bytes
            for bad in (str(work), "/private/", "/Users/", "/Volumes/", "beach-0", "BEACH-0", ".heic", "Traceback"):
                if bad in text:
                    leaks.append((where, bad))
        case(f"none of the {len(SEEN)} answers the designer's routes gave holds a path, a photo's file name or an error's innards", not leaks, sorted(set(leaks))[:6])
        log = (studio / "arrange.log").read_text(encoding="utf-8", errors="replace") if (studio / "arrange.log").is_file() else ""
        case("the server never fell over: its log holds no Python error and no route that failed", "Traceback" not in log and " failed: " not in log, [ln for ln in log.splitlines() if " failed: " in ln or "Traceback" in ln][:3])
    finally:
        srv.stop()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a new folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=8920)
    ap.add_argument("--only", choices=["server", "page", "browser", "text", "designs", "wire", "fixes", "screen", "layout"],
                    help="server: the routes and records; page: the page's scripts by themselves; browser: the real page in a hidden Chrome "
                         "(the strip; text, fonts and brand colors; designs, templates and Save slides); text: only the text, fonts and "
                         "brand colors part of that; designs: only the designs, templates, preview and Save slides part (with its own page checks); "
                         "wire: only the kit page, the posting queue, the links and the line for Claude; fixes: what the first reviewers found (safety); "
                         "screen: what the second reviewers found (matching Nicole's, and what is on the screen); "
                         "layout: the arrangement (the rows, the selection bar, the strip's size, the sheets, the names), measured at six window sizes")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        print("STOP: this needs a Mac (sips).")
        return 2
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("STOP: this test draws real JPEGs with Pillow. Run it with a Python that has Pillow (python3, not /usr/bin/python3).")
        return 2
    if a.work:
        work = Path(a.work).resolve()
        if SAFE not in work.parents:
            print(f"STOP: {work} is not under {SAFE}.")
            return 2
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="hf-design-check-", dir=str(SAFE)))
    if any((work / n).exists() for n in ("fake", "browser", "text", "designs", "designs-photos", "wire", "wire-browser", "fix", "fix-browser", "screen", "layout")):
        print(f"STOP: {work} already holds a pretend kit from an earlier run. Give a new --work folder.")
        return 2
    # Nothing here may ever look at the real ~/.studio: this process and every command it runs get a
    # STUDIO_HOME inside the work folder (the pretend kit's own, once it is made).
    os.environ["STUDIO_HOME"] = str(work / "no-studio")
    r = subprocess.run([PY, str(ROOT / "tools" / "check_plugin.py")], capture_output=True, text=True)
    case("tools/check_plugin.py prints CLEAN", r.returncode == 0 and "CLEAN" in r.stdout, r.stdout[-300:])
    for f in ("design.py", "design_page.py", "design_js_model.py", "design_js_core.py", "design_js_edit.py", "design_js_type.py", "design_js_text.py",
              "design_js_brand.py", "design_js_plan.py", "design_js_paint.py", "design_js_designs.py", "design_js_save.py", "arrange.py", "arrange_page.py",
              "kit.py", "posting_queue.py", "home.py"):
        r = subprocess.run([APPLE, "-c", "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')", str(SCRIPTS / f)], capture_output=True, text=True)
        case(f"{f} compiles under the Mac's own /usr/bin/python3", r.returncode == 0, r.stderr[-200:])
    src = (SCRIPTS / "design.py").read_text(encoding="utf-8")
    code_only = "\n".join(ln.split("#")[0] for ln in re.sub(r'"""(?:.|\n)*?"""', '""', src).splitlines())
    case("design.py runs no Mac-only program and uses no Mac-only call of its own", not re.search(r"\b(sips|osascript|chflags|caffeinate|fcntl)\b|/Volumes|%-d", code_only), re.findall(r"\b(sips|osascript|chflags|caffeinate|fcntl)\b|/Volumes|%-d", code_only)[:5])
    case("design.py names the encoding of every text file it reads or writes", not re.search(r"\.(read_text|write_text)\((?![^)]*encoding=)", src) and not re.search(r"open\([^)]*\"[rwa]\"\s*\)", src))
    import chrome_drive
    import design_fix_check
    import design_layout_check
    import design_page_check
    import design_save_check
    import design_screen_check
    import design_text_check
    import design_wire_check
    have_chrome = bool(chrome_drive.find_chrome())
    skipped = []            # the parts that drive the real page, when there is no Chrome to drive

    def real_page(part):
        if not have_chrome:
            skipped.append(part)
    if a.only in (None, "page"):
        design_page_check.check_page(case, work)
        design_text_check.check_type_page(case, work)
    if a.only in (None, "page", "designs"):
        design_save_check.check_designs_page(case, work)
    if a.only in (None, "server"):
        check_all(work, a.port)
    if a.only in (None, "server", "wire"):
        # the designer as part of the Assistant: two more pretend shoots and a page server of their own
        try:
            design_wire_check.check_wire(case, work, a.port + 4, make_kit, Server, post, get_json, ask, run, tree_print, sha)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the checks of the kit page, the posting queue and the line for Claude ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
    if a.only in (None, "server", "fixes"):
        # what the reviewers found, each with a case that failed before its fix: its own pretend shoots and servers
        try:
            design_fix_check.check_fixes(case, work, a.port + 11, make_kit, Server, post, get_json, ask, run, jpeg)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the checks of the reviewers' findings ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
    if a.only in (None, "browser", "fixes"):
        real_page("the reviewers' findings on the page")
        try:
            design_fix_check.check_fixes_browser(case, work, a.port + 14, make_kit, Server, post, get_json, jpeg)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the real-browser checks of the reviewers' findings ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
    if a.only in (None, "browser", "wire"):
        real_page("the 'Lay out the slides' links")
        try:
            design_wire_check.check_wire_browser(case, work, a.port + 4, make_kit, Server, run, ask, post, get_json)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the real-browser checks of the 'Lay out the slides' links ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
    if a.only in (None, "browser"):
        # its own pretend kit and its own page server, a little above the server check's ports
        real_page("the strip, the frames and the tray")
        try:
            design_page_check.check_browser(case, work, a.port + 5, make_kit, Server, post, get_json)
        except Exception as e:  # noqa: BLE001
            case("the real-browser checks ran to the end", False, f"{type(e).__name__}: {e}")
    if a.only in (None, "browser", "text"):
        # text, fonts and brand colors: another pretend kit and page server, on the port after those
        real_page("text, fonts and brand colors")
        try:
            design_text_check.check_type_browser(case, work, a.port + 8, make_kit, Server, post, get_json)
        except Exception as e:  # noqa: BLE001
            case("the real-browser checks of text, fonts and brand colors ran to the end", False, f"{type(e).__name__}: {e}")
    if a.only in (None, "page", "screen"):
        design_screen_check.check_screen_page(case, work)
    if a.only in (None, "page", "layout"):
        design_layout_check.check_layout_page(case, work)
    if a.only in (None, "browser", "screen"):
        # what the second reviewers found (the screen, and matching Nicole's): its own pretend shoot and page server
        real_page("the page's own lines, the keyboard, words over a seam, the folder button's answer")
        try:
            design_screen_check.check_screen_browser(case, work, a.port + 16, make_kit, Server, post, get_json, run)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the real-browser checks of what is on the screen ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    if a.only in (None, "browser", "layout"):
        # the arrangement, measured in a hidden Chrome at six window sizes: its own pretend shoot and page server
        real_page("the arrangement at six window sizes")
        try:
            design_layout_check.check_layout_browser(case, work, a.port + 20, make_kit, Server, post, get_json)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the real-browser checks of the arrangement ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-900:]}")
    if a.only in (None, "browser", "designs"):
        # designs, templates, the preview and Save slides: two more pretend shoots (one from photos drawn
        # here, so every saved pixel is known) and a page server on the port after those
        real_page("designs, templates, the preview and Save slides")
        try:
            design_save_check.check_designs_browser(case, work, a.port + 9, make_kit, Server, post, get_json)
        except Exception as e:  # noqa: BLE001
            import traceback
            case("the real-browser checks of designs, templates and Save slides ran to the end", False, f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
    bad = [n for n, ok in results if not ok]
    print()
    missed = (f"  {len(skipped)} PART{'S' if len(skipped) != 1 else ''} SKIPPED (no Chrome on this computer): the real page was NOT checked ({'; '.join(skipped)})." if skipped else "")
    print(f"{len(results)} cases, {len(results) - len(bad)} passed, {len(bad)} failed." + missed + (f"  Work folder: {work}" if bad or a.work else f"  Work folder (safe to throw away): {work}"))
    for n in bad:
        print("  FAILED:", n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
