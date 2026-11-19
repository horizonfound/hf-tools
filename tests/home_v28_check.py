#!/usr/bin/env python3
"""The home page after Nicole's v28 (her home-test.html and hello.js): the hello, the face finder, her four steps
with what is going on now, the monthly recap card and hiding it, the Your year bar.

    python3 tests/guard.py 3000 python3 tests/home_v28_check.py [--port 9900] [--work <a folder to keep>] [--no-chrome]

What it does, on a pretend Assistant in a throwaway folder under /private/tmp (two pretend kits from fake_kit.py; a
scratch STUDIO_HOME; pretend records; the card that "is in" is a test switch, so no drive is looked at; nothing of
the real ~/.studio, no real kit, no /Volumes):
  * the face finder (faces.py): the numbers a page may ask for; an answer cleaned; every unknown small copy looked
    at in ONE run; what is found kept in faces.json under the kit's name and the small copy's own name (never a
    path), and never looked at twice; a photo exported again looked at again; a computer with no face finder
    (a PC) gives no faces and keeps nothing; and, on a Mac, the Mac's own Vision really asked about the pretend
    kit's small copies (drawn photos: a size, no faces; no permission is asked for a file on this computer);
  * what the page reads (home.facts) and draws: her four steps in her exact words and order; each step's box
    (a card in, the last backup and how it stands, the queue and its next due date, red when late, the newest
    kit, today's post or a late one, days of posts worked out from the rhythm); the name from the Brand File and
    no name without one; the recap card (this month "so far.", last month "recapped." in the first week), hidden
    for a month or for good in home-recap.json with the choice before kept, and back; the Your year bar only in
    its dates or with ?wrapped=1; no path, no "Claude", no em dash, nothing from the internet, every animation
    only where motion is welcome;
  * her words compared with her own files when her handoff is on this computer (reference-private/, never pushed);
  * the routes: /kit-faces and POST /home-recap only for this server's own page, every field checked;
  * the page in a HIDDEN Chrome: the hello (a name, a line, a button that goes there; never the same twice in a
    row; the words as text, never markup), the collage (small copies only, every face in one ask, framed on the
    faces, burst twins skipped), the steps, the recap card's x and its two choices saved before the card goes,
    Show my monthly recap, phone width with no sideways scroll, and nothing moving under reduced motion.
The buttons that would open a folder window or another page server are never pressed for real.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only; a Mac (the pretend kits are drawn
with sips).
"""
import argparse
import hashlib
import html as html_mod
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402

TODAY = "2026-11-17"            # a Tuesday
A, B = "2026-11-01 Hannah", "2026-11-02 Katie Austin Maternity"
NASTY = "Tom & <img src=x onerror=\"window.__got=1\"> 'Jo'"

# Lines of hers that are NOT on our page, on purpose, and why.
HERS_NOT_OURS = {
    "Home (test)": "her test page's title",
    "This is a test copy of your home page, for trying ideas. The Assistant's own home page isn't changed.": "test-only",
    "Trying ideas:": "test-only (the link to her samples page)",
    "animation samples": "test-only",
    "·": "the dot before her samples link",
    "Hello.": None,                     # on ours (kept in this table only so the None marks it as checked below)
}


# Lines of hers said a little differently on ours, and why: hers -> the part of it that is on ours.
HERS_REWORDED = {
    # "271 photos and 6 video clips, every one checked": the count is the Assistant's own (a clip is never called a photo)
    "photos, every one checked": "every one checked",
}


def skip(line):
    print("SKIP  " + line, flush=True)


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


def her_pack():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for f in sorted(r.glob("nicole-handoff-v28-*/Carousel designer and reel picker/pages/home-test.html")):
            return f.parent
    return None


class World:
    def __init__(self, work, port):
        self.work, self.port0, self.port, self.proc = work, port, None, None
        self.home = work / "studio"
        self.assistant = work / "The Assistant"
        self.content = self.assistant / "Your Content"
        self.pretend = work / "faces-pretend.json"
        self.env = dict(os.environ, STUDIO_HOME=str(self.home), STUDIO_TODAY=TODAY, PYTHONIOENCODING="utf-8",
                        ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="EOS_DIGITAL:233", FACES_PRETEND=str(self.pretend))

    def build(self):
        for name, n in (("Hannah", 8), ("Katie Austin Maternity", 14)):
            r = subprocess.run([sys.executable, str(HERE / "fake_kit.py"), str(self.work), "--photos", str(n), "--name", name],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError("fake_kit.py: " + (r.stdout + r.stderr)[-300:])
        # fake_kit.py dates every kit Nov 1: the second one is made a day newer, so "the newest shoot" is certain
        (self.content / "2026-11-01 Katie Austin Maternity").rename(self.content / B)
        rec = json.loads((self.content / B / ".kit" / "kit.json").read_text(encoding="utf-8"))
        rec["date"] = "2026-11-02"
        self.put(self.content / B / ".kit" / "kit.json", rec)
        a = self.content / A
        # kit A: a reel made in November (so November has something to recap) and one in October. They are two
        # different reels of the shoot (v2 and the first): since v29 a reel counts once, in the month of its first
        # make, so a second make of ONE reel in November would leave November with nothing to recap
        self.put(a / ".kit" / "reel-page.json", {"v": 1, "made": [{"project": "Hannah reel", "when": ts("2026-11-03T10:00:00"), "version": "v2"},
                                                                   {"project": "Hannah reel old", "when": ts("2026-10-20T10:00:00")}]})
        self.posting(interval=3.5)
        self.queue()
        (self.assistant / "brand-homebase.md").write_text("# Brand Homebase\n\n- Name / business: Nicole Hill Photography\n- Instagram: @nicolelhill_.\n", encoding="utf-8")

    def posting(self, interval=3.5, pieces=None):
        (self.home / "posting-thumbs").mkdir(parents=True, exist_ok=True)
        shutil.copy(str(next(p for p in sorted((self.content / A / "Photos").iterdir()) if p.suffix.lower() == ".jpg")), str(self.home / "posting-thumbs" / "p5.jpg"))
        self.put(self.home / "posting.json", {"interval": interval, "reminded": {}, "pieces": pieces if pieces is not None else [
            {"id": "p1", "shoot_name": "Hannah", "kind": "reel", "status": "posted", "posted_at": "2026-11-14T18:00:00"},
            {"id": "p2", "shoot_name": "Hannah", "kind": "carousel", "status": "posted", "posted_at": "2026-11-04T18:00:00"},
            {"id": "p5", "shoot_name": "Katie Austin Maternity", "kind": "reel", "status": "green", "slot": 1, "date": TODAY, "thumb": "posting-thumbs/p5.jpg"},
            {"id": "p6", "shoot_name": "The beach day", "kind": "single", "status": "green", "slot": 2, "date": "2026-11-15", "thumb": "../studio.json"},
            {"id": "p7", "shoot_name": "Hannah", "kind": "carousel", "status": "green", "slot": 3, "date": "2026-11-20"},
            {"id": "p8", "shoot_name": "Not started", "kind": "reel", "status": "red"}, "odd"]})

    def queue(self, shoots=None):
        gone = str(self.work / "gone" / "2026-11-13 card" / "_studio")
        self.put(self.home / "queue.json", {"asked": True, "on": True, "shoots": shoots if shoots is not None else [
            {"id": "q1", "shoot": "s1", "name": NASTY, "studio": gone, "count": 231, "clips": 6, "status": "waiting", "added": "2026-11-13T20:00:00", "due": "2026-11-19", "thumbs": []},
            {"id": "q2", "shoot": "s2", "name": "Lee wedding", "studio": gone, "count": 40, "status": "waiting", "added": "2026-11-13T20:00:00", "thumbs": []},
            {"id": "q3", "shoot": "s3", "name": "Old one", "count": 120, "status": "finished", "added": "2026-10-10T20:00:00", "thumbs": []}]})

    @staticmethod
    def put(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")

    def previews(self, kit):
        r = subprocess.run([sys.executable, str(SCRIPTS / "arrange.py"), "previews", str(self.content / kit)], env=self.env, capture_output=True, text=True, timeout=300)
        return r.returncode

    def copies(self, kit):
        """{photo number: its 520 px copy's file name}"""
        out = {}
        for f in sorted((self.content / kit / ".kit" / "previews").glob("*-520-*.jpg")):
            out[int(f.name[:4])] = f.name
        return out

    def start(self, **env):
        f = self.home / "posting-url.txt"
        if f.exists():
            f.unlink()
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.port0)], env=dict(self.env, **env),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        chrome_drive.wait_until(lambda: f.exists() and f.read_text(encoding="utf-8").strip(), 30, every=0.1, what="the page server's address")
        self.port = int(re.search(r":(\d+)/", f.read_text(encoding="utf-8")).group(1))
        chrome_drive.wait_until(lambda: self.http("GET", "/home")[0] == 200, 30, every=0.1, what="the home page")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, raw=None, headers=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            h = dict(headers or {})
            if host:
                h["Host"] = host
            c.request(method, path, body=raw, headers=h)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def get_json(self, path, headers=None, host=None):
        code, raw = self.http("GET", path, headers=headers, host=host)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, None

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)


def at(day, card=None):
    """The computer's day (and the card that is in) for what is read next, in this program."""
    os.environ["STUDIO_TODAY"] = day
    os.environ["STUDIO_CARD_FOR_TESTS"] = card or "none"


def text_of(page):
    return html_mod.unescape(re.sub(r"<[^>]+>", "¦", page.split("<script", 1)[0]))


def box(page, n):
    m = re.search(r"<div class='now' id='n%d'>(.*?)</div>" % n, page)
    return m.group(1) if m else ""


def box_words(page, n):
    return [x for x in html_mod.unescape(re.sub(r"<[^>]+>", "¦", box(page, n))).split("¦") if x]


# ---------------------------------------------------------------- the face finder

def check_faces(w, faces):
    case("the numbers a page may ask for: 1 to 24 of them, each once", faces.numbers_of("1,2,3") == [1, 2, 3] and faces.numbers_of("7") == [7]
         and faces.numbers_of("3,3,1") == [3, 1] and faces.numbers_of(",".join(str(i) for i in range(1, 25))) == list(range(1, 25)))
    case("... never 25, never a word, never nothing, never a path", all(faces.numbers_of(x) is None for x in
         (",".join(str(i) for i in range(1, 26)), "one", "", "1,", "1;2", "../1", "0", None, "1234567")))
    case("an answer is cleaned: whole sizes, each face four numbers from 0 to 1",
         faces._clean({"w": 520.0, "h": 346, "faces": [[0.12345, -0.2, 0.5, 1.7]]}) == {"w": 520, "h": 346, "faces": [[0.123, 0.0, 0.5, 1.0]]}
         and faces._clean({"w": 0, "h": 5, "faces": []}) is None and faces._clean({"w": 5, "h": 5, "faces": [[1, 2, 3]]}) is None and faces._clean({"faces": []}) is None)
    import arrange
    kit = arrange.kit_by_name(B)
    case("the pretend kit is found by its folder name", kit is not None)
    os.environ["FACES_PRETEND"] = "none"
    case("no small copies made yet: nothing to look at, nothing answered, nothing kept", faces.for_kit(kit, [1, 2, 3]) == {} and not faces.CACHE.exists())
    case("the small copies are made (arrange.py previews)", w.previews(B) == 0 and w.previews(A) == 0 and len(w.copies(B)) >= 12, len(w.copies(B)))
    cp = w.copies(B)
    case("a computer with no face finder (a PC): no faces for any photo, and nothing kept",
         faces.find([str(w.content / B / ".kit" / "previews" / cp[1])]) == [None] and faces.for_kit(kit, [1, 2, 3]) == {} and not faces.CACHE.exists())
    # a pretend finder: photo 1 a face far left, 2 and 3 the same two faces (a burst), 4 none, 5 not read
    table = {cp[1]: {"w": 520, "h": 346, "faces": [[0.05, 0.3, 0.1, 0.15]]},
             cp[2]: {"w": 346, "h": 520, "faces": [[0.3, 0.2, 0.1, 0.07], [0.6, 0.25, 0.1, 0.07]]},
             cp[3]: {"w": 346, "h": 520, "faces": [[0.31, 0.21, 0.1, 0.07], [0.61, 0.24, 0.1, 0.07]]},
             cp[4]: {"w": 346, "h": 520, "faces": []}}
    w.put(w.pretend, table)
    os.environ["FACES_PRETEND"] = str(w.pretend)
    got = faces.for_kit(kit, [1, 2, 3, 4, 5, 999])
    case("every small copy not known yet is looked at, and answered by its number", set(got) == {1, 2, 3, 4} and got[1] == table[cp[1]] and got[4]["faces"] == [], got)
    kept = json.loads(faces.CACHE.read_text(encoding="utf-8"))
    case("what was found is kept in faces.json, under the kit's name and the small copy's own name",
         set(kept["faces"]) == {"%s/%s" % (B, cp[n]) for n in (1, 2, 3, 4)}, sorted(kept["faces"])[:2])
    case("... and never a path: no folder of this computer is in the file", str(w.work) not in faces.CACHE.read_text(encoding="utf-8") and "/private" not in faces.CACHE.read_text(encoding="utf-8"))
    case("a photo that was not read is not kept, so it is looked at again another day", "%s/%s" % (B, cp[5]) not in kept["faces"])
    os.environ["FACES_PRETEND"] = "none"
    case("each photo is looked at once, ever: with the finder gone the answers still come, from what was kept", faces.for_kit(kit, [1, 2, 3, 4]) == got)
    # one run for all: count the runs
    calls = []
    real = faces.find
    faces.find = lambda paths: (calls.append(len(paths)), real(paths))[1]
    try:
        os.environ["FACES_PRETEND"] = str(w.pretend)
        table.update({cp[n]: {"w": 346, "h": 520, "faces": []} for n in (6, 7, 8)})
        w.put(w.pretend, table)
        faces.for_kit(kit, [1, 2, 6, 7, 8])
        case("the photos not known yet go through ONE run together (the known ones are not sent again)", calls == [3], calls)
        faces.for_kit(kit, [6, 7, 8])
        case("... and a second ask starts no run at all", calls == [3], calls)
    finally:
        faces.find = real
    # a photo exported again: a new small copy, a new name, looked at again
    photo = next(p for p in (w.content / B / "Photos").iterdir() if p.is_file() and hashlib.sha1(p.name.encode("utf-8")).hexdigest()[:6] == cp[4].split("-")[2])
    os.utime(str(photo), (time.time() + 5, time.time() + 5))
    w.previews(B)
    names = sorted(f.name for f in (w.content / B / ".kit" / "previews").glob("0004-520-*.jpg"))
    new = [x for x in names if x != cp[4]]
    case("a photo exported again gets a new small copy under a new name", len(new) == 1, names)
    if new:
        table[new[0]] = {"w": 346, "h": 520, "faces": [[0.4, 0.4, 0.2, 0.14]]}
        w.put(w.pretend, table)
        os.environ["FACES_PRETEND"] = str(w.pretend)
        case("... and is looked at again: the answer is the new photo's, the old one's is not used", faces.for_kit(kit, [4])[4]["faces"] == [[0.4, 0.4, 0.2, 0.14]])
    cp = w.copies(B)
    # the Mac's own Vision, for real, on the pretend kit's small copies (drawn photos: no faces; nothing asked)
    os.environ.pop("FACES_PRETEND", None)
    try:
        import this_computer
        if not this_computer.MAC:
            skip("the Mac's own Vision asked for real: not a Mac")
            case("not a Mac: no faces, never a crash", faces.find([str(w.content / A / ".kit" / "previews" / w.copies(A)[1])]) == [None])
        else:
            ca = w.copies(A)
            files = [w.content / A / ".kit" / "previews" / ca[n] for n in sorted(ca)]
            t0 = time.time()
            got = faces.find([str(f) for f in files] + [str(w.work / "no such picture.jpg"), str(w.home / "studio.json")])
            took = time.time() - t0
            case("the Mac's own Vision answers for every small copy, in one run (%.1f s for %d)" % (took, len(files)),
                 len(got) == len(files) + 2 and all(isinstance(d, dict) and d["w"] > 0 and d["h"] > 0 and max(d["w"], d["h"]) <= 520 for d in got[:len(files)]), got[:2])
            case("... a drawn photo has no faces in it", all(d["faces"] == [] for d in got[:len(files)] if d))
            case("... a picture that is not there, or a file that is no picture: not read (None), never a crash", got[-2:] == [None, None], got[-2:])
            # the pretend kit has one photo stored sideways (its small copy keeps the camera's turn mark): the list
            # the kit keeps says which way each photo stands
            rows = {r["n"]: r for r in json.loads((w.content / A / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]}
            ways = [(n, d["w"], d["h"], rows[n]["w"], rows[n]["h"]) for n, d in zip(sorted(ca), got)]
            case("... the width and height are the picture's as it stands upright (a turn mark in the file is followed: the sideways one is tall)",
                 all((dw > dh) == (rw > rh) and (dw == dh) == (rw == rh) for _, dw, dh, rw, rh in ways) and any("sideways" in rows[n]["file"] and dw < dh for n, dw, dh, _, _ in ways), ways)
    finally:
        os.environ["FACES_PRETEND"] = str(w.pretend)
    src = (SCRIPTS / "faces.py").read_text(encoding="utf-8")
    case("the face finder is the Mac's own Vision asked through this_computer (no Swift tool is built or shipped)",
         "this_computer.mac_javascript(FACES_JS" in src and "VNDetectFaceRectanglesRequest" in src and "swiftc" not in src and not list((ROOT / "plugins").rglob("faces.swift")))
    case("... keeping faces Vision is more than 0.6 sure of (hers)", faces.CONFIDENCE == 0.6 and "f.confidence > least" in src)
    return table


# ---------------------------------------------------------------- what the page reads and draws

def check_page_words(w, home):
    at(TODAY, "EOS_DIGITAL:233")
    page = home.page_html()
    shown = text_of(page)
    case("the page says \"your assistant\", never \"Claude\"", "claude" not in page.lower())
    case("no em dash in any line of words", "—" not in page and not any("—" in v for v in list(home.WORDS.values()) + list(home.OUR_WORDS.values())))
    case("nothing from the internet, and the shared look first in the page's styles", "googleapis" not in page and "<link" not in page and "http://" not in page and "https://" not in page
         and ("<style>" + home.look.head_css()) in page)
    case("no path of this computer is anywhere in the page", str(w.work) not in page and "/private/" not in page and "Photos/" not in page)
    case("none of her test-only bits: no test-copy line, no samples link, no port of hers, nothing of the recap kept in the browser",
         not re.search(r"test copy|samples\.html|:8799|:8790|home=test|assistantRecapHide", page))
    stores = re.findall(r"(?:localStorage|sessionStorage)\.\w+\([^)]*\)", page)
    case("the only thing kept in the browser is what the hello said lately (hers), each use inside try/catch",
         stores and all("'assistantHello'" in s for s in stores) and all(re.search(r"try \{[^}]*" + re.escape(s), page) for s in stores), stores)
    # every animation only where motion is welcome
    css = page.split("<style>", 1)[1].split("</style>", 1)[0]
    mine = css.split(home.home_base.CSS, 1)[1] if home.home_base.CSS in css else css
    calm, moving = mine.split("@media (prefers-reduced-motion: no-preference){", 1)
    case("every animation and every @keyframes of the page is inside prefers-reduced-motion: no-preference",
         "animation" not in calm and "@keyframes" not in calm and moving.count("@keyframes") == 3 and "animation:kb" in moving and "animation:pulse" in moving and "animation:rise" in moving)
    case("... and with reduced motion the collage does not change photos", "if (HP.length <= n || STILL) return;" in page and "prefers-reduced-motion: reduce" in page)
    # her four steps, her exact words
    order = [page.find(x) for x in ("Back up <em>a card</em>", "My editing <em>queue</em>", "Turn your shoots <em>into posts</em>", "My posting <em>queue</em>")]
    case("Your workflow: her four steps in the order of the work", -1 not in order and order == sorted(order), order)
    for line in ("Your workflow", "Start wherever you are. Making posts from an old shoot? Jump straight to 3.",
                 "Copies your card to your drive, checks every photo, and sorts it into shoots.", "The shoots you need to edit and when they're due.",
                 "Turn your shoot into reels, carousels, stories, and captions.", "Your posts ready to go, and how your grid will look.",
                 "Back up →", "Open my editing queue →", "Make posts →", "Open my posting queue →", "Open my Assistant folder", "↻ Another hello"):
        case("her words: %s" % line, ("¦" + line + "¦") in shown, line)
    case("each step where hers sends it: its own screen, the editing queue (a button), its own screen, the posting queue",
         "id='s1' data-item='backup' href='/backups'" in page and "<button class='step' id='s2' data-item='queue'" in page
         and "id='s3' data-item='posts' href='/make-posts'" in page and "id='s4' data-item='posting' href='/posting.html'" in page)
    case("the bar: the name, the date, Open my Assistant folder; no Today list, no welcome paragraphs, no folder card",
         "<span class='when' id='when'>Tuesday, November 17</span>" in page and "id='folder' data-item='folder'" in page
         and not re.search(r"Welcome to your|class='todayl'|item minor|Your workflow, step by step", page))
    case("the date is hidden under 520 px, as hers", "@media(max-width:520px){.bar .when{display:none}" in page)
    hers = her_pack()
    if not hers:
        skip("her words compared with her own files: her handoff is not on this computer")
        return
    raw = (hers / "home-test.html").read_text(encoding="utf-8")
    body = raw.split("</style>", 1)[1].split("<script", 1)[0]
    theirs = [t.strip() for t in html_mod.unescape(re.sub(r"<[^>]+>", "¦", re.sub(r"</?em>", "", "<title>" + raw.split("<title>", 1)[1].split("</title>", 1)[0] + "</title>" + body))).split("¦") if t.strip()]
    ours_flat = html_mod.unescape(re.sub(r"</?em>", "", page.split("<script", 1)[0]))
    ours_flat = re.sub(r"<[^>]+>", "¦", ours_flat) + " ¦ " + " ¦ ".join(re.sub(r"</?em>", "", v) for v in home.WORDS.values())
    gone, left = [], set()
    for t in theirs:
        if t in HERS_NOT_OURS and HERS_NOT_OURS[t]:
            left.add(t)
        elif re.fullmatch(r"[\d\W]+", t) or t in ours_flat or t.replace("2026", "{year}") in ours_flat:
            continue
        else:
            gone.append(t)
    case("every line her home page shows is on ours, but for the ones left out on purpose (%d lines of hers)" % len(theirs), not gone, gone[:6])
    case("... and those are exactly her test-only lines", left == {k for k, v in HERS_NOT_OURS.items() if v}, sorted({k for k, v in HERS_NOT_OURS.items() if v} - left))
    # the lines her scripts write: every piece of words between the filled-in parts is in ours
    def flat(s):
        """A template's words with every filled-in part (${...}, braces inside it counted) taken out."""
        out, i, depth = [], 0, 0
        while i < len(s):
            if depth == 0 and s.startswith("${", i):
                depth, i = 1, i + 2
                out.append("¤")
            elif depth:
                depth += 1 if s[i] == "{" else -1 if s[i] == "}" else 0
                i += 1
            else:
                out.append(s[i])
                i += 1
        return "".join(out)

    def pieces(src):
        out = set()
        for s in re.findall(r"`((?:[^`\\]|\\.)*)`", src):
            for part in re.sub(r"<[^>]+>", "¤", flat(s)).split("¤"):
                part = html_mod.unescape(part).strip()
                if len(re.findall(r"[A-Za-z]", part)) >= 4 and " " in part:
                    out.add(HERS_REWORDED.get(part, part))
        return out
    ours_js = page.split("<script>", 1)[1]
    ours_pieces = " ¤ ".join(sorted(pieces(ours_js))) + " ¤ " + " ¤ ".join(home.WORDS.values()) + ours_flat
    hello = (hers / "hello.js").read_text(encoding="utf-8")
    code_bits = ("/s/", "repeat(", "px ", "animation-delay", "class=", "data-go")
    lost = sorted(p for p in pieces(hello) if p not in ours_pieces and not any(x in p for x in code_bits))
    case("every line her hello writes is in ours, word for word (%d pieces of hers)" % len(pieces(hello)), not lost, lost[:6])
    openers = re.findall(r"`([A-Z][^`$<]*?)\$\{N[xq]?\}`", hello)
    case("every opener of hers is one of ours (%d)" % len(openers), len(openers) >= 18 and all(("(`%s`)" % o) in ours_js for o in openers), [o for o in openers if ("(`%s`)" % o) not in ours_js])
    case("... and her two without a name: Hello, you. and Hello, holiday season.", "[`Hello, `, `you.`]" in ours_js and "[`Hello, `, `holiday season.`]" in ours_js)
    buttons = re.findall(r"(\w+): \['([^']+)', '[^']*'\]", hello.split("const GO = ", 1)[1].split("};", 1)[0])
    case("the hello's five buttons are hers: %s" % ", ".join(b for _, b in buttons), len(buttons) == 5 and all(("%s: ['%s'," % kb) in ours_js for kb in buttons))
    script = raw.split("<script>", 1)[1]
    lost = sorted(p for p in pieces(script) if p not in ours_pieces and not any(x in p for x in code_bits + ("img src", "<i>", "wrapped.html")))
    case("every line her page's script writes in the boxes and the recap card is in ours", not lost, lost[:8])


def check_boxes(w, home):
    at(TODAY, "EOS_DIGITAL:233")
    f = home.facts()
    page = home.page_html()
    case("the first name comes from the Brand File", f["me"] == "Nicole")
    case("step 1, a card in: the step glows (live), a coral dot, her line", "class='step live' id='s1'" in page and "<i class='dot coral'></i>" in box(page, 1)
         and box_words(page, 1) == ["A card is in", "EOS_DIGITAL · about 233 files"], box_words(page, 1))
    at(TODAY)
    f = home.facts()
    page = home.page_html()
    case("step 1, no card: no glow, the last backup by its day; its records can't be found, so no claim that every one was checked",
         "class='step' id='s1'" in page and f["backup"] == {"when": "2026-11-13", "photos": 271, "clips": 6, "state": "unknown"}
         and box_words(page, 1) == ["Last backup Nov 13", "271 photos and 6 video clips"], (f["backup"], box_words(page, 1)))
    # a backup whose records say how it stands
    rec = w.work / "gone" / "2026-11-13 card" / "_studio"
    rec.mkdir(parents=True)
    def manifest(**m):
        base = {"finished": True, "problems": [], "files": {"a.jpg": {"dest": {"ok": True}}}}
        base.update(m)
        (rec / "manifest.json").write_text(json.dumps(base), encoding="utf-8")
        os.utime(str(rec / "manifest.json"), (time.time() + manifest.n, time.time() + manifest.n))
        manifest.n += 3
        return box_words(home.page_html(), 1)
    manifest.n = 3
    case("... a backup that finished with every copy checked: \"every one checked\", a green dot", manifest() == ["Last backup Nov 13", "271 photos and 6 video clips, every one checked"]
         and "<i class='dot green'></i>" in box(home.page_html(), 1), manifest.__dict__)
    case("... a sample is never called checked: Keep the card", manifest(sample={"kept": 2, "of": 9}) == ["Last backup Nov 13", "Keep the card: this was a sample"])
    got = manifest(problems=["one"])
    case("... a backup with a problem: Something needs a look, in red", got == ["Last backup Nov 13", "Something needs a look: see the report"]
         and "<i class='dot red'></i>" in box(home.page_html(), 1) and "<small class='late'>" in box(home.page_html(), 1), got)
    shutil.rmtree(str(rec.parent.parent))
    case("step 2: how many are waiting and the next one due (its name as text, never markup)", box_words(page, 2) == ["2 shoots waiting", NASTY + " · due Nov 19"]
         and "<i class='dot yellow'></i>" in box(page, 2) and "<img src=x" not in page.split("<script", 1)[0] and "&lt;img src=x" in box(page, 2), box_words(page, 2))
    at("2026-11-21")
    late = home.page_html()
    case("... red when it is late", "<i class='dot red'></i>" in box(late, 2) and "<small class='late'>" in box(late, 2))
    at(TODAY)
    case("step 3: the newest kit with its photo (a small copy, by the kit's name and a number), and how many kits",
         box_words(page, 3) == ["Newest: Katie Austin Maternity", "2 post kits"]
         and re.search(r"<img src='/kit-photo\?kit=%s&amp;n=\d+&amp;size=s&amp;v=\w*' alt=''>" % re.escape(quote(B, safe="")), box(page, 3)), box(page, 3)[:160])
    case("step 4: today's post with its picture, and the one that missed its day (red)",
         box_words(page, 4) == ["Today: Katie’s reel", "The beach day single post is late too"] and "<img src='/posting-thumbs/p5.jpg' alt=''>" in box(page, 4)
         and "<small class='late'>" in box(page, 4), box_words(page, 4))
    case("... a piece's picture is only ever one of the posting queue's own small pictures (a record changed by hand shows none)", "studio.json" not in page)
    case("the hello is told what is true: today's post, the late one and how late, this week's post, the queue, the year",
         f["posting"]["today"][0]["who"] == "Katie’s" and f["posting"]["late"][0]["days"] == 2 and len(f["posting"]["posted_week"]) == 1
         and f["posting"]["ready"] == 3 and [x["due_in"] for x in f["queue"]] == [2, None] and f["year"]["reels"] == 2 and f["year"]["newest"] == "Katie Austin Maternity"
         and f["year"]["top"] == "Hannah", (f["posting"], f["queue"], f["year"]))
    case("who a post is: a first name becomes \"Katie’s\", anything else stays whole (hers)",
         [home.who(x) for x in ("Katie Austin Maternity", "Hannah", "The beach day", "Family at the lake", "black-sand beach", "Zoë B", "", "A")]
         == ["Katie’s", "Hannah’s", "The beach day", "Family at the lake", "black-sand beach", "Zoë B", "", "A"])
    # nothing today, one late
    w.posting(pieces=[{"id": "p6", "shoot_name": "Hannah", "kind": "carousel", "status": "green", "slot": 1, "date": "2026-11-15"}])
    case("step 4, only a late one: it is waiting, and the day it was down for", box_words(home.page_html(), 4) == ["Hannah’s carousel is waiting", "It was down for Nov 15"])
    w.posting(interval=3.5, pieces=[{"id": "p%d" % i, "shoot_name": "Hannah", "kind": "reel", "status": "green", "slot": i, "date": "2026-11-2%d" % i} for i in (1, 2, 3)])
    case("step 4, three ready at 3.5 posts a week: about 6 days of posts (worked out from the rhythm, 3 x 7 / 3.5)",
         box_words(home.page_html(), 4) == ["3 ready to go", "About 6 days of posts"], box_words(home.page_html(), 4))
    w.posting(interval=None, pieces=[{"id": "p1", "shoot_name": "Hannah", "kind": "reel", "status": "green", "slot": 1}])
    case("... with no rhythm set, no days are claimed", box_words(home.page_html(), 4) == ["1 ready to go", "No posting rhythm set yet"])
    w.posting(pieces=[])
    w.queue(shoots=[])
    page = home.page_html()
    case("nothing anywhere: her four quiet lines", [box_words(page, n) for n in (1, 2, 3, 4)][0] == ["No backups yet", "Put a card in to start"]
         and box_words(page, 2) == ["All caught up", "Nothing waiting to edit"] and box_words(page, 4) == ["Nothing lined up yet", "Make posts, then add them here"],
         [box_words(page, n) for n in (1, 2, 4)])
    # records that can't be read: the page still comes
    for name in ("queue.json", "posting.json"):
        (w.home / name).write_text("{broken", encoding="utf-8")
    try:
        page, why = home.page_html(), ""
    except BaseException as e:  # noqa: BLE001
        page, why = "", e.__class__.__name__
    case("a queue and a posting record that can't be read: the page still comes, with its four steps", "id='s4'" in page and "Your workflow" in page, why)
    # no Brand File: no name, never an invented one
    kept = (w.assistant / "brand-homebase.md").read_text(encoding="utf-8")
    (w.assistant / "brand-homebase.md").unlink()
    try:
        case("no Brand File: no name at all (the openers are said without one)", home.facts()["me"] == "" and '"me": ""' in home.page_html())
    finally:
        (w.assistant / "brand-homebase.md").write_text(kept, encoding="utf-8")
    w.posting()
    w.queue()


def check_recap(w, home):
    at(TODAY)
    f = home.facts()
    page = home.page_html()
    case("the recap card: this month, so far.", f["recap"]["month"] == "2026-11" and "<b id='rcT'>Your November, <em>so far.</em></b>" in page, f["recap"])
    chips = re.findall(r"<span><i>([^<]*)</i> ([^<]*)</span>", page.split("id='rcC'>", 1)[1].split("</div>", 1)[0])
    case("... its chips are the month's own numbers (wrapped.py's), the number in coral", chips and [" ".join(c) for c in chips] == f["recap"]["chips"] and ("1", "reel") in chips, chips)
    case("... a fan of the month's photos, Watch to the recap page, the x with her two choices",
         len(re.findall(r"<img src='/kit-photo\?", page.split("id='rcFan'>", 1)[1].split("</div>", 1)[0])) in (1, 2, 3)
         and "<a class='all' href='/wrapped.html?m=2026-11'" in page and ">▶ Watch<" in page and "aria-label='Hide the monthly recap'" in page
         and "<button type='button' data-h='month'>Hide it for this month</button><button type='button' data-h='all'>Stop showing monthly recaps</button>" in page)
    case("... shown, so the footer has no Show my monthly recap in sight", "<div class='rc' id='rc' data-m='2026-11'>" in page and "<span id='rcBack' hidden>" in page)
    case("no Your year bar in November", "class='yr'" not in page)
    case("?wrapped=1 shows the Your year bar any time (hers, for testing)", "<div class='yr' id='yr'><a class='all' href='/wrapped.html?y=2026'" in home.page_html("wrapped=1")
         and "Your 2026, <em>wrapped.</em>" in home.page_html("wrapped=1") and "Your year with your assistant, story by story. Ready to share." in home.page_html("wrapped=1"))
    at("2026-12-03")
    page = home.page_html()
    case("in the first week of December: last month, recapped.", "Your November, <em>recapped.</em>" in page and "data-m='2026-11'" in page)
    case("... and no Your year bar: they have not had the Assistant since January", "class='yr'" not in page)
    at("2026-12-10")
    case("after the first week, a month with nothing in it has no card (and no Show my monthly recap)", "id='rc'" not in home.page_html() and "id='rcShow'" not in home.page_html())
    at(TODAY)
    # hiding it: kept with their records
    case("nothing is hidden to begin with, and no file is there", home.recap_hide() == "" and not home.RECAP.exists())
    home.set_recap_hide("")
    case("showing what is already shown writes nothing", not home.RECAP.exists())
    home.set_recap_hide("2026-11")
    page = home.page_html()
    case("Hide it for this month: kept in home-recap.json", json.loads(home.RECAP.read_text(encoding="utf-8"))["hide"] == "2026-11" and home.recap_hidden("2026-11"))
    case("... the card is drawn hidden, and Show my monthly recap is in the footer", "<div class='rc' id='rc' data-m='2026-11' hidden>" in page
         and "<span id='rcBack'><button id='rcShow' type='button'>Show my monthly recap</button></span>" in page)
    stamp = home.RECAP.stat().st_mtime_ns
    home.set_recap_hide("2026-11")
    case("... a second press that changes nothing writes nothing", home.RECAP.stat().st_mtime_ns == stamp and not home.RECAP_PREV.exists())
    at("2026-12-03")
    case("... it was this month only: November recapped is hidden in December's first week (the same month's card)", " hidden>" in home.page_html().split("id='rc'", 1)[1][:40])
    at("2026-12-10")
    w.put(w.content / A / ".kit" / "reel-page.json", {"v": 1, "made": [{"project": "Hannah reel", "when": ts("2026-11-03T10:00:00"), "version": "v2"}, {"project": "Dec", "when": ts("2026-12-09T10:00:00"), "version": "v3"}]})
    case("... and the next month's card shows again", "<div class='rc' id='rc' data-m='2026-12'>" in home.page_html())
    home.set_recap_hide("all")
    case("Stop showing monthly recaps: every month is hidden, and the choice before is kept beside it",
         home.recap_hidden("2026-12") and home.recap_hidden("2027-03") and json.loads(home.RECAP_PREV.read_text(encoding="utf-8"))["hide"] == "2026-11"
         and "data-m='2026-12' hidden>" in home.page_html())
    home.set_recap_hide("")
    case("Show my monthly recap brings it back", home.recap_hide() == "" and "<div class='rc' id='rc' data-m='2026-12'>" in home.page_html())
    for bad in ("2026-13", "../x", "ALL", 7, None, "2026-1"):
        try:
            home.set_recap_hide(bad)
            ok = False
        except (ValueError, TypeError):
            ok = True
        case("a choice that is not a month is refused (%r)" % (bad,), ok and home.recap_hide() == "")
    home.RECAP.write_text("{broken", encoding="utf-8")
    case("a choice file that can't be read hides nothing", home.recap_hide() == "" and "id='rc' data-m" in home.page_html())
    home.RECAP.unlink()
    home.RECAP_PREV.unlink()
    w.put(w.content / A / ".kit" / "reel-page.json", {"v": 1, "made": [{"project": "Hannah reel", "when": ts("2026-11-03T10:00:00"), "version": "v2"}, {"project": "Hannah reel old", "when": ts("2026-10-20T10:00:00")}]})
    at(TODAY)


# ---------------------------------------------------------------- the routes

def check_routes(w):
    cp = w.copies(B)
    code, d = w.get_json("/kit-faces?kit=%s&n=1,2,3,4" % quote(B))
    case("/kit-faces answers several at once: {ok, faces: {number: {w, h, faces}}}", code == 200 and d["ok"] and set(d["faces"]) == {"1", "2", "3", "4"}
         and d["faces"]["1"] == {"w": 520, "h": 346, "faces": [[0.05, 0.3, 0.1, 0.15]]}, d)
    code, raw = w.http("GET", "/kit-faces?kit=%s&n=1,2" % quote(B))
    case("... names and numbers only, never a path or a file name", str(w.work).encode() not in raw and b".jpg" not in raw and cp[1].encode() not in raw)
    code, d = w.get_json("/kit-faces?kit=%s&n=1" % quote(B))
    case("... one photo: the same shape", code == 200 and list(d["faces"]) == ["1"])
    code, d = w.get_json("/kit-faces?kit=%s&n=998,999" % quote(B))
    case("... a number that is no photo of the kit: simply not in the answer", code == 200 and d == {"ok": True, "faces": {}}, d)
    for what, path in (("a kit that is not in Your Content", "/kit-faces?kit=Nope&n=1"), ("a path for a kit", "/kit-faces?kit=%s&n=1" % quote(str(w.content / B))),
                       ("25 numbers", "/kit-faces?kit=%s&n=%s" % (quote(B), ",".join(str(i) for i in range(1, 26)))), ("no numbers", "/kit-faces?kit=%s" % quote(B)),
                       ("a word for a number", "/kit-faces?kit=%s&n=one" % quote(B)), ("something extra", "/kit-faces?kit=%s&n=1&file=x" % quote(B))):
        code, d = w.get_json(path)
        case("/kit-faces, %s: nothing" % what, code == 404 and d == {"ok": False}, (code, d))
    code, d = w.get_json("/kit-faces?kit=%s&n=1" % quote(B), host="evil.example:%d" % w.port)
    case("/kit-faces asked under another name (not this server's): refused", code == 403, code)
    code, d = w.get_json("/kit-faces?kit=%s&n=1" % quote(B), headers={"Sec-Fetch-Site": "cross-site"})
    case("another website's page cannot ask where the faces are", code == 403 and d == {"ok": False}, code)
    code, raw = w.http("GET", "/home?wrapped=1")
    case("/home?wrapped=1 shows the Your year bar (hers, for testing); /home alone does not", code == 200 and b"class='yr'" in raw and b"class='yr'" not in w.http("GET", "/home")[1])
    # hiding the recap
    own = {"Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % w.port, "Sec-Fetch-Site": "same-origin"}
    f = w.home / "home-recap.json"

    def post(body, headers=own, host=None):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        code, out = w.http("POST", "/home-recap", raw=raw, headers=headers, host=host)
        try:
            return code, json.loads(out.decode("utf-8"))
        except ValueError:
            return code, None
    code, d = post({"hide": "month", "month": "2026-11"})
    case("POST /home-recap, Hide it for this month: saved with their records", code == 200 and d == {"ok": True, "hide": "2026-11"} and json.loads(f.read_text(encoding="utf-8"))["hide"] == "2026-11", (code, d))
    case("... and the page comes with the card hidden", b"data-m='2026-11' hidden>" in w.http("GET", "/home")[1])
    code, d = post({"hide": "all"})
    case("... Stop showing monthly recaps", code == 200 and d == {"ok": True, "hide": "all"})
    before = f.read_bytes()
    for what, body, headers, host, want in (
            ("from another website (its Origin)", {"hide": "show"}, dict(own, Origin="https://evil.example"), None, 403),
            ("a cross-site press", {"hide": "show"}, dict(own, **{"Sec-Fetch-Site": "cross-site"}), None, 403),
            ("sent to another name", {"hide": "show"}, own, "evil.example:%d" % w.port, 403),
            ("not JSON by its type (a plain form another site could send)", {"hide": "show"}, dict(own, **{"Content-Type": "text/plain"}), None, 415),
            ("too long", b'{"hide": "show", "month": "' + b"x" * 3000 + b'"}', own, None, 413),
            ("not JSON", b"{hide", own, None, 400),
            ("a choice that is none of the three", {"hide": "never"}, own, None, 400),
            ("this month with no month", {"hide": "month"}, own, None, 400),
            ("a month that is not one", {"hide": "month", "month": "2026-13"}, own, None, 400),
            ("a path for a month", {"hide": "month", "month": "../../x"}, own, None, 400),
            ("a field too many", {"hide": "show", "file": "x"}, own, None, 400),
            ("a list", ["show"], own, None, 400)):
        code, d = post(body, headers, host)
        case("POST /home-recap, %s: refused (%d), nothing changed" % (what, want), code == want and f.read_bytes() == before and (d or {}).get("ok") is not True, (code, d))
    code, d = post({"hide": "show"})
    case("... Show my monthly recap: back, and the choice before kept beside it", code == 200 and d == {"ok": True, "hide": ""} and json.loads(f.read_text(encoding="utf-8"))["hide"] == ""
         and json.loads((w.home / "home-recap.prev.json").read_text(encoding="utf-8"))["hide"] == "all")
    case("only those two files were made by it", sorted(p.name for p in w.home.glob("home-recap*")) == ["home-recap.json", "home-recap.prev.json"])


# ---------------------------------------------------------------- the page in a browser

HELLO = "(() => { const t = document.querySelector('.hello .tx'); const b = t.querySelector('.hgo'); return {h: t.querySelector('h3').textContent, em: t.querySelector('h3 em').textContent, p: t.querySelector('p').textContent, b: b ? b.textContent : '', go: b ? b.dataset.go : '', k: t.dataset.subject}; })()"


def check_browser(c, w, table):
    c.init_script("window.__asked = []; (function(){ const f = window.fetch; window.fetch = function(u, o){ window.__asked.push(String(u)); "
                  "if (String(u).startsWith('/queue-url')) return Promise.resolve(new Response(JSON.stringify({words: 'Pretend: the editing queue would open here.'}), {headers: {'Content-Type': 'application/json'}})); "
                  "if (String(u).startsWith('/open-home')) return Promise.resolve(new Response(JSON.stringify({words: 'Opened The Assistant in Finder.'}), {headers: {'Content-Type': 'application/json'}})); "
                  "return f.apply(this, arguments); }; })();")
    # The test says which it means, every time: a machine may itself ask for reduced motion (GitHub's Mac does),
    # and then the page, rightly, plays nothing. Never left to the computer's own setting.
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    c.open(w.url("/home"))
    c.wait_for("document.getElementById('hello').dataset.faces === '1' && document.querySelectorAll('.hello .tile img.on').length > 0", 20)
    h = c.js(HELLO)
    case("the hello: an opener with their name as the accent word (or one of her two that take no name), a line, and a button that goes there",
         ("Nicole" in h["em"] or h["h"] in ("Hello, you.", "Hello, holiday season.")) and h["h"].endswith(h["em"]) and len(h["p"]) > 10 and h["b"].strip().endswith("→") and h["go"] in ("backup", "posting", "editing", "posts", "year"), h)
    case("... Another hello sits in its corner", c.text("#again") == "↻ Another hello" and c.js("getComputedStyle(document.getElementById('again')).position") == "absolute")
    seen, same = [h], 0
    for _ in range(14):
        c.click("#again")
        seen.append(c.js(HELLO))
        same += 1 if (seen[-1]["h"] == seen[-2]["h"] or seen[-1]["p"] == seen[-2]["p"]) else 0
    case("never the same twice in a row: 14 presses, the opener and the line change every time", same == 0, [(x["h"], x["p"]) for x in seen][:4])
    case("... and never the same subject as the one before", all(seen[i]["k"] != seen[i - 1]["k"] for i in range(1, len(seen))), [x["k"] for x in seen])
    case("... what was said lately is kept in this browser, the last 24", c.js("JSON.parse(localStorage.getItem('assistantHello')).length") == 24)
    subjects = set(c.js("hellos(F, new Date(2026, 10, 20, 8)).L.map(l => l[1])"))
    case("every line comes from something true: today's post, the late one, this week's post, what is ready, the card, the queue, what is due, the newest shoot, the year, the day",
         subjects == {"today", "late", "posted", "tank", "card", "queue", "due", "newest", "reels", "photos", "top", "day"}, sorted(subjects))
    lines = c.js("(() => { const out = {}; for (let i = 0; i < 60; i++) hellos(F, new Date(2026, 10, 20, 8)).L.forEach(l => { (out[l[1]] = out[l[1]] || {})[l[2]] = l[3]; }); return out; })()")
    case("the lines say the real names and numbers", "Katie’s reel goes out today. Let’s make it a good one." in lines["today"] and "The beach day single post has been waiting 2 days to go out. Today?" in lines["late"]
         and "You posted Hannah’s reel this week. Love that for you." in lines["posted"] and "3 posts are lined up and ready. Future you says thank you." in lines["tank"]
         and "I see a card! 233 files, ready to back up whenever you are." in lines["card"] and "2 shoots are waiting for your magic." in lines["queue"]
         and ("Heads up: “%s” is due in 2 days." % NASTY) in lines["due"] and "2 reels made so far this year. That’s a lot of beats." in lines["reels"]
         and "Hannah is your most-made-from shoot this year. Iconic." in lines["top"] and "Friday’s a great day to line up the weekend’s posts." in lines["day"], {k: list(v)[:1] for k, v in lines.items()})
    case("... each with the button that goes there", set(lines["today"].values()) == {"posting"} and set(lines["card"].values()) == {"backup"} and set(lines["queue"].values()) == {"editing"}
         and set(lines["newest"].values()) == {"posts"} and set(lines["top"].values()) == {"year"})
    ops = c.js("(d => hellos(F, d).op.map(o => o[0] + o[1]))(new Date(2026, 10, 20, 8))")
    case("openers by the time of day, the weekday and the season (a Friday morning in November)",
         all(x in ops for x in ("Good morning, Nicole.", "Coffee first, Nicole?", "Happy Friday, Nicole!", "Hello, holiday season.", "Welcome back, Nicole.", "Hello, you.")) and "Good evening, Nicole." not in ops, ops)
    ops = c.js("(d => { const G = Object.assign({}, F, {me: ''}); return hellos(G, d).op.map(o => o[0] + o[1]); })(new Date(2026, 5, 15, 22))")
    case("with no name the openers are said without one, never an invented one (a Monday night in June)",
         all(x in ops for x in ("Welcome back.", "Still up?", "New week!", "Night owl mode.")) and not any("," in x and "Hello" not in x for x in ops) and "Hello, holiday season." not in ops, ops)
    # the words are text, never markup
    c.js("(() => { for (let i = 0; i < 40; i++) document.getElementById('again').click(); })()")
    case("a shoot's name reaches the hello as text, never as markup", c.js("!window.__got && document.querySelectorAll('.hello .tx img').length === 0") is True)
    # the collage
    ph = c.js("JSON.stringify({n: document.querySelectorAll('.hello .tile').length, w: document.getElementById('hello').clientWidth, photos: document.getElementById('hello').dataset.photos, "
              "srcs: [...document.querySelectorAll('.hello .tile img')].map(i => i.getAttribute('src') || ''), want: F.collage.photos.length, kit: F.collage.kit})")
    ph = json.loads(ph)
    case("the collage is the NEWEST shoot's photos, up to 12", ph["kit"] == B and ph["want"] == 12, (ph["kit"], ph["want"]))
    case("tall tiles, as many as fit: max(3, round(width / 165))", ph["n"] == max(3, round(ph["w"] / 165)), (ph["n"], ph["w"]))
    case("only the small copies are ever asked for (size=s), by the kit's name and a number", all("size=s" in s and s.startswith("/kit-photo?kit=") for s in ph["srcs"] if s)
         and not any("size=l" in u or "/Photos/" in u for u in c.js("performance.getEntriesByType('resource').map(r => r.name)")))
    asks = [u for u in c.js("window.__asked") if u.startswith("/kit-faces")]
    case("every face is asked for in ONE request", len(asks) == 1 and asks[0].count(",") == 11, asks)
    case("burst twins are skipped: two photos with the same faces in the same spots count once (12 photos, 11 used)", ph["photos"] == "11", ph["photos"])
    aims = c.js("(() => { const out = {}; HP.forEach(x => { const im = document.createElement('img'); aim(im, x, 200, 300); out[x.n] = im.style.objectPosition; }); return out; })()")
    case("a wide photo with its face far left is framed on the face, not on its middle", float(aims["1"].split("%")[0]) < 20, aims["1"])
    case("... a photo with no faces known is centered", [float(x.rstrip("%")) for x in aims["5"].split()] == [50.0, 50.0], aims)
    tall = c.js("(() => { const im = document.createElement('img'); aim(im, {f: {w: 400, h: 1200, faces: [[0.4, 0.5, 0.2, 0.07]]}}, 200, 300); return im.style.objectPosition; })()")
    # a 400x1200 photo fills a 200x300 tile at 200x600; a face in its middle (head and shoulders from 283 to 346, the
    # middle at 315) is put 38% down the tile (114 px): the photo is moved up 201 of the 300 it can move, 66.9%
    case("... heads sit about 38% down the tile (a tall photo, a face in its middle: the photo is moved up so the head is 114 px down a 300 px tile)", tall == "50% 66.9%", tall)
    rect = c.rect(".hello .tile")
    case("the tiles are tall (about 2:3)", rect["h"] >= 230 and rect["h"] > rect["w"], rect)
    # the steps
    case("the four steps, numbered, with her names", c.js("[...document.querySelectorAll('.flow4 .step .k')].map(x => x.textContent).join('')") == "1234"
         and c.js("[...document.querySelectorAll('.flow4 .step .n')].map(x => x.textContent)") == ["Back up a card", "My editing queue", "Turn your shoots into posts", "My posting queue"])
    case("a card is in: step 1 glows coral and its dot pulses", c.js("document.getElementById('s1').classList.contains('live') && getComputedStyle(document.querySelector('#s1 .now .dot')).animationName") == "pulse"
         and "240, 127, 90" in c.js("getComputedStyle(document.getElementById('s1')).boxShadow"))
    case("the pictures in the boxes are there (the newest kit's photo, today's post)", c.js("[...document.querySelectorAll('.now img')].map(i => i.naturalWidth > 0)") == [True, True])
    c.js("window.__asked.length = 0")
    c.click("#s2")
    c.wait_for("!!document.querySelector('#s2 .note') && document.querySelector('#s2 .note').textContent.startsWith('Pretend')", 10)
    case("My editing queue asks for the queue, and what comes back shows on the card itself", "/queue-url" in c.js("window.__asked") and c.js("document.querySelector('#s2 .note').textContent") == "Pretend: the editing queue would open here.")
    c.click("#folder")
    c.wait_for("document.querySelector('.bar .fold .note').textContent.length > 20", 10)
    case("Open my Assistant folder asks to open it, and the line shows right under the button", "/open-home" in c.js("window.__asked") and c.js("document.querySelector('.bar .fold .note').textContent") == "Opened The Assistant in Finder.")
    time.sleep(0.3)
    j = json.loads((w.home / "journey.json").read_text(encoding="utf-8"))
    case("both presses were recorded for the chat (journey.json)", [x["item"] for x in j["clicks"]][-2:] == ["queue", "folder"], j["clicks"][-3:])
    case("no page errors, and nothing asked of the internet", not c.page_errors() and not c.outside_requests(), (c.page_errors()[:2], c.outside_requests()[:2]))
    # the recap card
    (w.home / "home-recap.json").unlink()
    c.open(w.url("/home"))
    c.wait_for("!!document.getElementById('rc')", 10)
    case("the recap card: Your November, so far., its chips, three photos fanned, Watch", c.text("#rcT") == "Your November, so far." and c.count("#rcC span") >= 2
         and c.count("#rcFan img") == 3 and c.text("#rc .playbtn") == "▶ Watch" and c.js("getComputedStyle(document.getElementById('rc')).overflow") == "visible")
    case("... its menu is closed", c.js("document.getElementById('rcM').hidden") is True)
    c.click("#rcX")
    case("the x opens her two choices, whole inside the card's corner (not cut off)", c.js("[...document.querySelectorAll('#rcM button')].map(b => b.textContent)") == ["Hide it for this month", "Stop showing monthly recaps"]
         and c.js("(() => { const r = document.getElementById('rcM').getBoundingClientRect(); const e = document.elementFromPoint(r.left + 20, r.bottom - 12); return !!e && !!e.closest('#rcM') && r.right <= innerWidth; })()") is True)
    c.key("Escape")
    case("Escape closes it, and nothing was saved", c.js("document.getElementById('rcM').hidden") is True and not (w.home / "home-recap.json").exists() and c.js("location.pathname") == "/home")
    c.click("#rcX")
    c.click("#rcM button[data-h=month]")
    c.wait_for("document.getElementById('rc').hidden", 10)
    case("Hide it for this month: saved with their records first, then the card goes and the footer offers Show my monthly recap",
         json.loads((w.home / "home-recap.json").read_text(encoding="utf-8"))["hide"] == "2026-11" and c.js("!document.getElementById('rcBack').hidden") is True
         and c.text("#rcShow") == "Show my monthly recap" and c.js("location.pathname") == "/home")
    c.js("(() => { try { localStorage.clear(); } catch (e) {} })()")
    c.open(w.url("/home"))
    c.wait_for("!!document.getElementById('rcShow')", 10)
    case("... it is their records that remember, not this browser: after a fresh load with the browser's own memory emptied it is still hidden",
         c.js("document.getElementById('rc').hidden && !document.getElementById('rcBack').hidden") is True)
    c.click("#rcShow")
    c.wait_for("!document.getElementById('rc').hidden", 10)
    case("Show my monthly recap brings it back, and that is saved too", json.loads((w.home / "home-recap.json").read_text(encoding="utf-8"))["hide"] == "" and c.js("document.getElementById('rcBack').hidden") is True)
    c.click("#rcX")
    c.click("#rcM button[data-h=all]")
    c.wait_for("document.getElementById('rc').hidden", 10)
    case("Stop showing monthly recaps: saved as \"all\"", json.loads((w.home / "home-recap.json").read_text(encoding="utf-8"))["hide"] == "all")
    c.click("#rcShow")
    c.wait_for("!document.getElementById('rc').hidden", 10)
    c.click("#rc .all")
    c.wait_for("location.pathname === '/wrapped.html'", 10)
    case("Watch (the whole card) opens that month's recap", c.js("location.pathname + location.search") == "/wrapped.html?m=2026-11")
    # the hello's button goes there
    c.open(w.url("/home"))
    c.wait_for("!!document.querySelector('.hello .hgo')", 10)
    c.js("(() => { for (let i = 0; i < 80 && document.querySelector('.hello .hgo').dataset.go !== 'backup'; i++) document.getElementById('again').click(); })()")
    case("a hello about the card has Back it up", c.js("document.querySelector('.hello .hgo').dataset.go") == "backup" and c.text(".hello .hgo").startswith("Back it up"))
    c.click(".hello .hgo")
    c.wait_for("location.pathname === '/backups'", 10)
    time.sleep(0.3)
    j = json.loads((w.home / "journey.json").read_text(encoding="utf-8"))
    case("... which opens the Back up a card screen, and the press is recorded as a backup press", c.js("location.pathname") == "/backups" and j["clicks"][-1]["item"] == "backup", j["clicks"][-1])
    c.open(w.url("/home?wrapped=1"))
    c.wait_for("!!document.getElementById('yr')", 10)
    case("the Your year bar (?wrapped=1): Your 2026, wrapped., Watch, to the year's stories", c.js("document.querySelector('#yr b').textContent") == "Your 2026, wrapped."
         and c.js("document.querySelector('#yr .all').getAttribute('href')") == "/wrapped.html?y=2026" and c.count("#yrFan img") == 3)
    # a phone
    c.phone(390, 844)
    c.open(w.url("/home?wrapped=1"))
    c.wait_for("document.querySelectorAll('.hello .tile img.on').length > 0", 20)
    time.sleep(0.4)
    m = c.js("({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, when: getComputedStyle(document.getElementById('when')).display, tiles: document.querySelectorAll('.hello .tile').length, "
             "cols: getComputedStyle(document.querySelector('.flow4')).gridTemplateColumns.split(' ').length, fan: getComputedStyle(document.getElementById('rcFan')).display})")
    case("at phone width: no sideways scroll, the date hidden, three tall tiles, the steps one under another, the recap's fan put away",
         m["sw"] <= m["cw"] and m["when"] == "none" and m["tiles"] == 3 and m["cols"] == 1 and m["fan"] == "none", m)
    c.tap("#rcX")
    case("... and the x's menu opens whole on the screen", c.js("(() => { const r = document.getElementById('rcM').getBoundingClientRect(); return !document.getElementById('rcM').hidden && r.left >= 0 && r.right <= innerWidth && document.documentElement.scrollWidth <= document.documentElement.clientWidth; })()") is True)
    c.desktop()
    # reduced motion
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    c.open(w.url("/home"))
    c.wait_for("document.querySelectorAll('.hello .tile img.on').length > 0", 20)
    before = c.js("[...document.querySelectorAll('.hello .tile img.on')].map(i => i.dataset.n).join(',')")
    time.sleep(3.4)
    case("with reduced motion nothing moves: no zoom, no rise, no pulse, and the photos stay as they are",
         c.js("STILL && getComputedStyle(document.querySelector('.hello .tile img')).animationName === 'none' && getComputedStyle(document.querySelector('.hello .tx h3')).animationName === 'none' "
              "&& getComputedStyle(document.querySelector('#s1 .now .dot')).animationName === 'none'") is True
         and c.js("[...document.querySelectorAll('.hello .tile img.on')].map(i => i.dataset.n).join(',')") == before)
    c.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
    c.open(w.url("/home"))
    c.wait_for("document.querySelectorAll('.hello .tile img.on').length > 0", 20)
    before = c.js("[...document.querySelectorAll('.hello .tile img.on')].map(i => i.dataset.n).join(',')")
    c.wait_for("[...document.querySelectorAll('.hello .tile img.on')].map(i => i.dataset.n).join(',') !== %s" % json.dumps(before), 12)
    case("with motion welcome a tile changes to the next photo (every 2.8 s), with the slow zoom",
         c.js("getComputedStyle(document.querySelector('.hello .tile img')).animationName") == "kb")
    case("no page errors at the end, and nothing asked of the internet", not c.page_errors() and not c.outside_requests(), (c.page_errors()[:2], c.outside_requests()[:2]))


def check_pc_browser(c, w):
    """The same page on a computer with no face finder (a PC): the collage still comes, every photo centered."""
    c.open(w.url("/home"))
    c.wait_for("document.querySelectorAll('.hello .tile img.on').length > 0", 20)
    time.sleep(0.5)
    pos = c.js("[...document.querySelectorAll('.hello .tile img.on')].map(i => i.style.objectPosition)")
    case("no face finder (the named PC gap): the collage is drawn all the same, every photo centered", pos and all(p == "50% 50%" or p == "50.0% 50.0%" for p in pos), pos)
    case("... all twelve photos used (no faces, no twins to skip), and no page errors", c.js("document.getElementById('hello').dataset.photos") == "12" and not c.page_errors(), c.page_errors()[:2])


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder under /private/tmp for this run, kept afterwards (default: a throwaway one, removed at the end)")
    ap.add_argument("--port", type=int, default=9900)
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    if os.name == "nt" or not shutil.which("sips"):
        skip("the pretend kits are drawn with the Mac's own sips: nothing here runs on this computer")
        return 0
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="home-v28-check-", dir="/private/tmp")).resolve()
    work = base / time.strftime("run-%H%M%S")
    w = World(work, a.port)
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", STUDIO_CARD_FOR_TESTS="none")
    try:
        w.build()
        sys.path.insert(0, str(SCRIPTS))
        import faces
        import home
        case("the test's own scratch home, never the real one", Path(home.HOME) == w.home and Path(faces.HOME) == w.home and ".studio" not in str(home.HOME))
        table = group("the face finder", check_faces, w, faces)
        group("the page's words", check_page_words, w, home)
        group("what is going on right now", check_boxes, w, home)
        group("the monthly recap card and the Your year bar", check_recap, w, home)
        w.start()
        case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
        group("the routes", check_routes, w)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                group("the page in a browser", check_browser, c, w, table)
            w.stop()
            (w.home / "faces.json").unlink()
            w.start(FACES_PRETEND="none")
            with chrome_drive.Chrome(work=str(work / "pc"), size=(1280, 1000)) as c:
                group("the page with no face finder", check_pc_browser, c, w)
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
