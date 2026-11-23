#!/usr/bin/env python3
"""The home base's two screens, after Nicole's v26 (stage B of the v26 build): Back up a card (/backups) and Make
posts from a shoot (/make-posts; its words are her v27's since Nov 17: the What's a post kit? box and the third
step), and that the home page leads to them. The home page itself was rebuilt after her v28 (Nov 17) and is checked
line by line in tests/home_v28_check.py.

    python3 tests/home_base_check.py [--port 9820] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant in a throwaway folder (a scratch STUDIO_HOME; pretend backups that are only
records and empty folders, pretend kits that are a record and three tiny pictures; no real drive, no card, no
real kit, nothing of the real ~/.studio; the card that "is in" is a test switch, so no drive is ever looked at):
  * the words: her lines on our three pages, compared with her own pages when her handoff is on this computer
    (reference-private/, never pushed; home-test.html and backups.html from her v26 pack, make-posts.html from the
    newest pack that has it, v27 today), both ways, with the lines of hers left out on purpose named in
    HERS_NOT_OURS; "your assistant", never "Claude"; none of her test-only bits (port 8799, ?home=test);
  * what the screens read (/home-data): every backup the editing queue knows, read from each backup's own
    records wherever they are now (settled or not); the cards of one shoot as ONE backup, by the link
    shoot_report.py wrote and never by their names; a sample backup never safe to format; a backup with a
    problem; a second copy; a shoot on a drive that is not plugged in; a folder that was moved; and never a path;
  * the routes: only for this server's own pages (another Host, another website's ask or press refused);
    Archive and Bring it back, the list kept in kit-archive.json with the list before beside it, a second press
    writing nothing, a name that is not a kit refused in her words, every field checked, no kit ever moved;
    See the report finding a settled backup's records; a kit whose page was never written still listed and opened;
  * the pages in a HIDDEN Chrome (when there is one): the home base's four cards in order and where each goes,
    no recent-shoots list; Your backups (the 10 newest, Show older with month headings, the search, "2 cards",
    each shoot's state and its two buttons, the unplugged drive, the moved folder, the line a press puts under
    its button); Your post kits (the 20 newest, Show older, the search that includes archived kits, Archive and
    Bring it back); Copy; and all three at phone width with no sideways scroll.
The buttons that would open a folder window, a folder picker or another page server are answered by the test
inside the page (no Finder window, no picker, no report server is ever started).

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import base64
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
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

WINDOWS = os.name == "nt"
TODAY = "2026-11-14"
NASTY = "Tom & <img src=x onerror=\"window.__got=1\"> 'Jo'"
ODD_FOLDER = "Smith #2 100% & (b)"       # a kit folder with the letters an address trips on (all fine on a PC too)
NO_DRIVE = "Zz Pretend Drive 4471"          # a drive that is not plugged in: a name that is on no computer
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wAARCAAgADADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwBaKKK8o+iCiiigAooooAKKKKACiiigAooooA//2Q==")

# Lines of hers that are NOT on our pages, on purpose, and why.
HERS_NOT_OURS = {
    # her test-only bits (UPDATE-v26 section 6: "drop these when it becomes the real home page")
    "Test copy: a screen of its own for backing up, with every backup underneath.": "test-only",
    "Test copy: a screen of its own for making posts, with your post kits underneath.": "test-only",
    # gone since her v29 (Nov 19): the home page no longer numbers steps, so the Back up a card screen has no
    # "Step 1" over its heading, and the post kits screen (her v29 make-posts-preview.html) none either
    "Step 1 of your workflow": "gone with the numbered steps (v29)",
    "Step 3 of your workflow": "gone with the numbered steps (v29; her make-posts-preview.html has no eyebrow)",
    # no longer true since Nov 19 (Dustin: nothing is asked before the copy); ours is OUR_WORDS["b_s2_small"]
    "The Assistant asks a quick question or two, then you can walk away. The report is ready when you're back, and it shows up below.": "no questions before the copy (v29)",
    # our Today is drawn by the server with the page, so there is no moment when the home page waits for records
    # (the two screens keep her line for it)
}
# Capitalised runs her scripts hold that are code or comments, not words a photographer reads.
HERS_JS_NOT_WORDS = ("Content-Type", "Nothing ready")     # a header's name; a test of the posting queue's line, not a line shown


def skip(line):
    print("SKIP  " + line, flush=True)


def her_roots():
    roots = [ROOT / "reference-private"]
    try:                                                   # a worktree: the main checkout's reference-private too
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            roots.append((ROOT / out).resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def her_folder():
    """Her v26 pack (the home page and Back up a card changed last in v26)."""
    for r in her_roots():
        for f in sorted(r.glob("nicole-handoff-v26-*/Carousel designer and reel picker/pages/home-test.html")):
            return f.parent.parent
    return None


def her_newest(name):
    """The newest pack of hers (v26 or later) that has pages/<name>: a later pack replaces only the files it has."""
    found = []
    for r in her_roots():
        for f in r.glob("nicole-handoff-v2*-*/Carousel designer and reel picker/pages/" + name):
            m = re.match(r"nicole-handoff-v(\d+)-", f.parents[2].name)
            if m and int(m.group(1)) >= 26:
                found.append((int(m.group(1)), f))
    return max(found)[1] if found else None


def stop_listener(port):
    try:
        if WINDOWS:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=30).stdout
            pids = set(l.split()[-1] for l in out.splitlines() if "LISTENING" in l and (":%d " % port) in l)
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=30)
        else:
            out = subprocess.run(["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-t"], capture_output=True, text=True, timeout=30).stdout
            pids = set(out.split())
            for pid in pids:
                os.kill(int(pid), 15)
        return bool(pids)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------- the pretend Assistant

def manifest(name, n=3, second=None, problems=None, finished=True, sample=None, second_ok=True):
    files = {}
    for i in range(n):
        e = {"size": 10, "sha256": "x" * 8, "dest": {"ok": True}}
        if second:
            e["second"] = {"ok": second_ok}
        files["DCIM/100/IMG_%04d.CR3" % i] = e
    m = {"session": name, "source": "/pretend/card", "dest": "/pretend/dest", "second": second, "files": files,
         "started": "2026-11-01T09:00:00", "problems": problems or []}
    if finished:
        m["finished"] = "2026-11-01T09:10:00"
    if sample:
        m["sample"] = sample
    return m


class World:
    """A pretend photographer: a place for shoots (a plain folder standing in for their drive), backups in every
    state the screen has words for, an Assistant folder with post kits, and the queue's record of it all."""

    def __init__(self, work, port):
        self.work, self.port0, self.port = work, port, None
        self.home = work / "studio-home"
        self.home.mkdir(parents=True, exist_ok=True)
        self.place = work / "their drive" / "Shoots"
        self.place.mkdir(parents=True)
        self.assistant = work / "kit drive" / "The Assistant"
        self.env = dict(os.environ, STUDIO_HOME=str(self.home), STUDIO_TODAY=TODAY, PYTHONIOENCODING="utf-8",
                        STUDIO_CARD_FOR_TESTS="none", REMINDERS_BACKEND="none",
                        # nothing this test's server is asked may open a window, a folder picker or another server
                        STUDIO_NO_WINDOWS_FOR_TESTS="1")
        self.proc = None
        self.shoots = []            # the queue's records
        self.records = {}           # a backup's name -> its records folder

    def run(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *[str(a) for a in args]], env=self.env, capture_output=True,
                           text=True, encoding="utf-8", timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()

    # ---- backups
    def backup(self, name, added, shoots, settled=True, spelled_old=False, **mf):
        """One pretend backup: its records (settled: <place>/.studio/<name>; not: <place>/<name>/_studio) and an
        empty folder per shoot. shoots: [(shoot name, status, extra queue fields)]."""
        if settled:
            rec, root = self.place / ".studio" / name, self.place
        else:
            rec, root = self.place / name / "_studio", self.place / name
        rec.mkdir(parents=True)
        (rec / "manifest.json").write_text(json.dumps(manifest(name, **mf)), encoding="utf-8")
        if settled:
            (rec / "settled.json").write_text(json.dumps({"session_was": str(self.place / name)}), encoding="utf-8")
        listed = []
        for i, (sname, status, more) in enumerate(shoots, 1):
            folder = "2026 " + re.sub(r"[^A-Za-z0-9 ]", "", sname).strip()
            if not more.get("_moved"):
                (root / folder).mkdir(parents=True, exist_ok=True)
            listed.append({"id": "s%d" % i, "name": sname, "folder": folder, "groups": []})
            q = {"id": "%s-%d" % (re.sub(r"[^a-z0-9]+", "-", name.lower()), i), "name": sname, "shot": added[:10], "due": None, "count": 100 + i,
                 "clips": 0, "folder": str(root / folder),
                 "studio": str(self.place / name / "_studio") if spelled_old else str(rec), "shoot": "s%d" % i, "thumbs": [],
                 "status": status, "added": added}
            q.update({k: v for k, v in more.items() if not k.startswith("_")})
            self.shoots.append(q)
        (rec / "shoots.json").write_text(json.dumps({"shoots": listed}), encoding="utf-8")
        self.records[name] = rec
        return rec

    def build(self):
        self.assistant.parent.mkdir(parents=True, exist_ok=True)
        code, out = self.run("posts.py", "setup", "--home", self.assistant)
        if code:
            raise RuntimeError("posts.py setup: " + out)
        # --- the backups, newest first as the page should show them
        self.backup("friday card", "2026-11-13T18:00:00", [("Garcia wedding", "waiting", {"due": "2026-11-20"}),
                                                           (NASTY, "archived", {}),
                                                           ("Patio session", "finished", {"finished_at": "2026-11-13T20:00:00"})],
                    second=str(self.work / "second drive" / "friday card"))
        # one shoot on two cards: linked by shoot_report.py, and named nothing alike
        self.backup("monday morning", "2026-11-12T10:00:00", [("Lee wedding", "waiting", {"due": "2026-11-10"})])
        self.backup("the other body", "2026-11-12T10:30:00", [("Lee wedding details", "archived", {"clips": 4, "count": 20})], settled=False)
        # two backups whose NAMES look like two cards of one shoot, and are not linked: two backups
        self.backup("Smith day", "2026-11-11T09:00:00", [("Smith family", "archived", {})])
        self.backup("Smith day, card 2", "2026-11-11T09:30:00", [("Smith cousins", "archived", {})])
        self.backup("a sample", "2026-11-10T09:00:00", [("Sample shoot", "archived", {})], sample={"kept": 3, "of": 9})
        self.backup("went wrong", "2026-11-09T09:00:00", [("Trouble shoot", "archived", {})], problems=["IMG_0001.CR3: the copy does not match the card"])
        self.backup("still going", "2026-11-08T09:00:00", [("Half done", "archived", {})], finished=False)
        self.backup("moved away", "2026-11-07T09:00:00", [("Moved shoot", "archived", {"_moved": True})])
        self.backup("old spelling", "2026-11-06T09:00:00", [("Old spelling shoot", "archived", {})], spelled_old=True)
        self.backup("half second", "2026-11-05T09:00:00", [("Half second shoot", "archived", {})],
                    second=str(self.work / "second drive" / "half"), second_ok=False)
        # a shoot on a drive that is not plugged in (only a name: nothing on this computer is called that)
        gone = "/Volumes/%s" % NO_DRIVE
        self.shoots.append({"id": "unplugged-1", "name": "Iceland", "shot": "2026-11-04", "due": None, "count": 880, "clips": 0,
                            "folder": gone + "/2026 Iceland", "studio": gone + "/.studio/iceland card", "shoot": "s1", "thumbs": [],
                            "status": "archived", "added": "2026-11-04T09:00:00"})
        # older ones, over three months, so Show older has months to head
        for i in range(8):
            month = ("10", "09", "08")[i // 3]
            self.backup("older %d" % i, "2026-%s-%02dT09:00:00" % (month, 20 - i), [("Older shoot %d" % i, "archived", {})])
        # a shoot that was only typed into the queue (no backup): never on the backups screen
        self.shoots.append({"id": "typed-1", "name": "Typed in only", "shot": None, "due": None, "count": None, "folder": None, "studio": None,
                            "shoot": None, "thumbs": [], "status": "waiting", "added": "2026-11-13T19:00:00"})
        (self.home / "queue.json").write_text(json.dumps({"shoots": self.shoots, "picks": {}, "manual_order": False}, indent=1), encoding="utf-8")
        code, out = self.run("shoot_report.py", "link", self.records["monday morning"], self.records["the other body"], "--shoot", "Lee wedding")
        if code:
            raise RuntimeError("shoot_report.py link: " + out)
        # --- the post kits
        content = self.assistant / "Your Content"
        self.kits = []
        for i in range(24):
            month = ("11", "10", "09", "08")[i // 7]
            day = "2026-%s-%02d" % (month, 28 - (i % 7))
            name = "Kit shoot %02d" % i
            self.kit("%s %s" % (day, name), name, day)
        self.kit("2026-11-30 With pictures", "With pictures", "2026-11-30", photos=3)
        self.kit(ODD_FOLDER, NASTY, "2026-11-29")
        self.kit("No date kit", "No date kit", None)
        (content / "Just a folder").mkdir()                              # no kit record: not a kit the page could open
        (content / "Just a folder" / "notes.txt").write_text("theirs", encoding="utf-8")

    def kit(self, folder, name, day, photos=0):
        d = self.assistant / "Your Content" / folder
        (d / ".kit").mkdir(parents=True)
        (d / "Photos").mkdir()
        for i in range(photos):
            (d / "Photos" / ("photo %d.jpg" % (i + 1))).write_bytes(TINY_JPEG)
        if photos:
            (d / "Photos" / "notes about this shoot.txt").write_text("theirs, and not a photo", encoding="utf-8")
        rec = {"name": name, "folder": folder, "source": "drop"}
        if day:
            rec["date"] = day
        (d / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        self.kits.append(folder)

    # ---- the page server
    def start(self):
        f = self.home / "posting-url.txt"
        kw = {"creationflags": 0x00000200} if WINDOWS else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.port0)], env=self.env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
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

    def http(self, method, path, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            h = dict(headers or {})
            data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
            if data is not None:
                h.setdefault("Content-Type", "application/json")
            c.request(method, path, body=data, headers=h)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def page(self, path):
        code, raw = self.http("GET", path)
        return code, raw.decode("utf-8", "replace")

    def data(self):
        code, raw = self.http("GET", "/home-data")
        return json.loads(raw.decode("utf-8"))

    def archive(self, shoot, on, **kw):
        code, raw = self.http("POST", "/kit-archive", {"shoot": shoot, "archived": on}, **kw)
        try:
            return code, json.loads(raw.decode("utf-8"))
        except ValueError:
            return code, raw.decode("utf-8", "replace")

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)


# ---------------------------------------------------------------- the words

class _Text(HTMLParser):
    """The text a page shows: every piece of text in its body, outside its scripts and styles."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self._off, self._body = [], 0, False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._body = True
        if tag in ("script", "style"):
            self._off += 1
        for k, v in attrs:
            if k in ("placeholder", "aria-label", "data-copy") and v and self._body:
                self.out.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._off -= 1

    def handle_data(self, data):
        if self._body and not self._off and data.strip():
            self.out.append(data)


def norm(t):
    return re.sub(r"\s+", " ", html_mod.unescape(str(t))).strip()


def shown_text(page):
    p = _Text()
    p.feed(page)
    return [norm(x) for x in p.out if norm(x)]


def untag(t):
    return norm(re.sub(r"</?(?:em|b|i|small|span|a|p|h1|h2|h3|div|button|li|img)\b[^>]*>", "", str(t)))


def pieces(template):
    """A line of ours cut at its {gaps}: the parts that must be hers."""
    return [norm(x) for x in re.split(r"\{\w+\}", untag(template)) if len(norm(x)) > 1]


def scripts_of(page):
    return "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))


def js_words(script):
    """The runs of words in a script that read like something shown to a person: a capital, then at least one
    more word. Comments are dropped first."""
    s = re.sub(r"(?m)(^|\s)//.*$", "", script).replace("\\'", "'")
    out = []
    word = r"[A-Za-z0-9]+(?:['\u2019][a-z]+)?[,:;]?"
    for m in re.finditer(r"(?<![A-Za-z0-9$_.])([A-Z][a-z]*(?:['\u2019][a-z]+)?[,:;]?(?: " + word + r")+[.\u2026?!]?)", s):
        t = norm(m.group(1))
        if len(t.split()) >= 2:
            out.append(t)
    return out


def check_words(w):
    sys.path.insert(0, str(SCRIPTS))
    os.environ.update(STUDIO_HOME=str(w.home), STUDIO_TODAY=TODAY, STUDIO_CARD_FOR_TESTS="none")
    import home
    import home_base
    case("the test's own Assistant, not the real one", Path(home.HOME) == w.home and Path(home_base.HOME) == w.home)
    pages = {"/home": home.page_html(), "/backups": home_base.backups_html(), "/make-posts": home_base.make_posts_html()}
    everything = "\n".join(pages.values())
    ours_words = dict(home_base.WORDS)
    case("the pages say \"the Assistant\", never \"Claude\"", "Claude" not in everything and "claude" not in everything.lower(), re.findall(r".{30}[Cc]laude.{20}", everything)[:3])
    case("none of her test-only bits: no port 8799, no ?home=test, no test-copy line",
         not re.search(r"(?<![\d.\w])8799(?![\d.\w])|home=test|assistantHomeTest|test copy|Test copy|/hp/", everything))   # 8799 as a port, not four digits inside a record's time stamp
    # (the home page, her v28: what the hello said lately is kept in the browser, as hers; tests/home_v28_check.py holds it to that)
    case("the two screens keep nothing in the browser", not re.search(r"localStorage|sessionStorage", pages["/backups"] + pages["/make-posts"]))
    case("no em dash in any line of words", "—" not in everything and not any("—" in v for v in list(ours_words.values()) + list(home_base.OUR_WORDS.values())))
    case("nothing from the internet, and the shared look first in each page's styles",
         "googleapis" not in everything and "<link" not in everything and all(("<style>" + home.look.head_css()) in p for p in pages.values()))
    all_js = home_base.JS_SHARED + home_base.JS_BACKUPS + home_base.JS_MAKE + home.SCRIPT + home.HELLO_JS
    known = set(ours_words) | set(home_base.OUR_WORDS) | set(home.OUR_WORDS) | {k for k in home.WORDS if k.startswith("mk_")}   # the Create box's (v30: page_html hands these over)
    case("every line our scripts show is in the words (W.<name> names a line that exists)",
         all(k in known for k in set(re.findall(r"\bW\.([a-z_0-9]+)", all_js))), sorted(k for k in set(re.findall(r"\bW\.([a-z_0-9]+)", all_js)) if k not in known))
    # the home page itself is her v28's since Nov 17 (tests/home_v28_check.py checks it line by line); here only
    # that it still leads to the two screens
    hp = pages["/home"]
    order = [hp.find(x) for x in ("Turn your shoots <em>into posts</em>", "My posting <em>queue</em>", "Back up <em>a card</em>", "My editing <em>queue</em>")]
    case("the home page: the four cards, posts first (her v29 order, her v28 names)", -1 not in order and order == sorted(order), order)
    case("... each where her page sends it: its own screen, the editing queue, its own screen, the posting queue",
         "href='/backups'" in hp and "href='/make-posts'" in hp and "href='/posting.html'" in hp and "id='s2' data-item='queue'" in hp)
    case("... and nothing else: no recent-shoots list, no My post kits card, no drop-down steps",
         not re.search(r"recent shoots|(?<!all )My post kits|class='howto'|class='recent'|class='shoot'", hp.split("<script", 1)[0], re.I))

    hers = her_folder()
    if not hers:
        skip("her words compared with her own pages: her handoff is not on this computer")
        return home_base
    raw = {n: nicole_nov22.read((hers / "pages" / n)) for n in ("home-test.html", "backups.html", "make-posts.html", "home-test.js")}   # Nicole, Nov 22: everything is the Assistant
    raw["server.py"] = nicole_nov22.read((hers / "server.py"))   # Nicole, Nov 22: everything is the Assistant
    newest = her_newest("make-posts.html")                 # v27 changed this one page (section 8); v26's is still beside it
    case("her Make posts page is read from her newest pack that has it (v27 or later)", newest is not None and int(re.search(r"-v(\d+)-", newest.parents[2].name).group(1)) >= 27, newest)
    if newest:
        raw["make-posts.html"] = nicole_nov22.read(newest)   # Nicole, Nov 22: everything is the Assistant
    # v29 (Nov 19): her preview of the same screen, with her new title and My vault first; its lines are hers too
    # (tests/vault_page_check.py compares that page line by line)
    for r in her_roots():
        for f in sorted(r.glob("nicole-handoff-v29-*/unpacked/Carousel designer and reel picker/pages/make-posts-preview.html")) + \
                sorted(r.glob("nicole-handoff-v29-*/Carousel designer and reel picker/pages/make-posts-preview.html")):
            raw["make-posts-preview.html"] = nicole_nov22.read(f)   # Nicole, Nov 22: everything is the Assistant
    if "make-posts-preview.html" not in raw:
        skip("her v29 preview of the post kits screen is not on this computer: its title and the My vault card's lines are not compared here")
        ours_words = {k: v for k, v in ours_words.items() if k not in ("m_h1", "v_name", "v_small")}
    hers_all = untag("\n".join(raw.values()).replace("\\'", "'"))
    # 1. ours -> hers: every line in WORDS, cut at its gaps, is in her files
    missing = []
    for k, v in ours_words.items():
        for part in pieces(v):
            if part not in hers_all:
                missing.append((k, part))
    case("every line of ours that is called hers is in her pages, word for word (%d lines)" % len(ours_words), not missing, missing[:6])
    # 2. hers -> ours: every piece of text her three pages show is on ours
    ours_shown = " ¦ ".join(shown_text(everything)) + " ¦ " + " ¦ ".join(untag(v) for v in ours_words.values())
    gone, left_out = [], set()
    for n in ("backups.html", "make-posts.html"):            # (her home page is her v28's now: tests/home_v28_check.py)
        for t in shown_text(raw[n]):
            if t in HERS_NOT_OURS:
                left_out.add(t)
            elif re.fullmatch(r"[\d\W]+", t) or t in ours_shown:
                continue
            else:
                gone.append((n, t))
    case("every line her two screens show is on ours, but for the ones left out on purpose", not gone, gone[:6])
    case("... and those are exactly the lines left out on purpose (HERS_NOT_OURS)", left_out == set(HERS_NOT_OURS), sorted(set(HERS_NOT_OURS) - left_out))
    # 3. hers -> ours, the lines her scripts write
    ours_flat = " ¦ ".join(p for v in ours_words.values() for p in pieces(v)) + " ¦ " + " ¦ ".join(untag(v) for v in ours_words.values())
    lost = []
    for n in ("backups.html", "make-posts.html", "home-test.js"):
        src = raw[n] if n.endswith(".js") else scripts_of(raw[n])
        for t in js_words(src):
            t2 = t.rstrip(".\u2026?!")
            if t in ours_flat or t2 in ours_flat or t.strip('"') in ours_flat or any(x in t for x in HERS_JS_NOT_WORDS):
                continue
            lost.append((n, t))
    case("every line her scripts write on the page is in ours", not lost, lost[:8])
    case("her words for a name that is not a kit, and her three states", home_base.WORDS["not_a_kit"] == "That shoot isn't in your content folder."
         and (home_base.WORDS["st_waiting"], home_base.WORDS["st_edited"], home_base.WORDS["st_just"]) == ("Waiting to be edited", "Edited", "Just for you"))
    # Make posts, her v27 (section 8): the lede names the post kit, the What's a post kit? box sits between the lede
    # and the steps title, the steps are three and the third has no button (it happens inside the post kit)
    mp = html_mod.unescape(pages["/make-posts"].split("<script>", 1)[0])
    case("make posts (v27): her lede, with post kit in bold", "we'll build you a <b>post kit</b>, and together we'll create your reels, carousels, single photos, stories and captions." in mp)
    case("make posts (v27): the What's a post kit? box sits between the lede and the steps title, in her words",
         re.search(r"</header><div class='whatkit'><p class='wk-h'>What's a post kit\?</p><p>It's one place for everything you'll post from a shoot\. .*?Nothing is ever posted for you\.</p></div><p class='steps-title'>How to make a post kit from a shoot</p>", mp))
    steps = re.findall(r"<div class='st'><span class='num'>(\d)</span>(.*?)</div></div>", mp.split("<div class='steps light'>", 1)[1].split("<section", 1)[0])
    case("make posts (v27): three steps, numbered 1, 2, 3", [n for n, _ in steps] == ["1", "2", "3"], [n for n, _ in steps])
    case("make posts (v27): step 1 has the folder button, step 2 the words to paste, step 3 no button at all",
         len(steps) == 3 and "id='pick'" in steps[0][1] and "class='paste'" in steps[1][1] and "<button" not in steps[2][1] and "<a " not in steps[2][1]
         and "Make your posts inside your post kit." in steps[2][1] and "I'll bring your photos in and open your new post kit. You'll find it below any time, too." in steps[1][1])
    case("make posts (v27): her v26 lines that v27 replaced are gone",
         not any(x in mp for x in ("start here and we'll create your social media content", "How to make posts from a shoot", "Your shoot's post kit opens, and it shows up below")))
    return home_base


# ---------------------------------------------------------------- what the screens read

def by_shoot(d):
    out = {}
    for gi, g in enumerate(d["groups"]):
        for b in g["backups"]:
            for s in b["shoots"]:
                out[s["name"]] = (gi, g, b, s)
    return out


def check_data(w, hb):
    d = w.data()
    code, raw = w.http("GET", "/home-data")
    text = raw.decode("utf-8")
    case("/home-data answers, and carries names and numbers, never a path",
         code == 200 and d.get("ok") is True and str(w.work) not in text and "/Volumes" not in text and "studio-home" not in text and "\\\\" not in text, text[:200])
    at = by_shoot(d)
    case("every backed-up shoot is there once; a shoot only typed into the queue is not", "Typed in only" not in at and len(at) == len([s for s in w.shoots if s["studio"]]), sorted(at))
    days = [g["added"] for g in d["groups"]]
    case("newest first", days == sorted(days, reverse=True) and at["Garcia wedding"][0] == 0, days[:4])
    # the cards of one shoot
    gi, g, b, s = at["Lee wedding"]
    gi2, g2, b2, s2 = at["Lee wedding details"]
    case("the two cards of one shoot are ONE backup, though their names are nothing alike", gi == gi2 and len(g["backups"]) == 2, (gi, gi2))
    case("... card 1 first, each shoot under its own card number", [x["card_no"] for x in g["backups"]] == [1, 2] and b["card_no"] == 1 and b2["card_no"] == 2)
    case("... the settled card and the one not settled yet both found, both safe", b["safe"] is True and b2["safe"] is True and b["known"] and b2["known"])
    case("... dated by the newer card", g["added"] == "2026-11-12T10:30:00", g["added"])
    case("two backups that only LOOK like two cards by name (\"Smith day\", \"Smith day, card 2\") stay two",
         at["Smith family"][0] != at["Smith cousins"][0] and len(at["Smith family"][1]["backups"]) == 1)
    # how each backup stands
    case("a clean backup: safe to format", at["Garcia wedding"][2]["safe"] is True and at["Garcia wedding"][2]["sample"] is False)
    case("a second copy that was made and checked says so; none says none", at["Garcia wedding"][2]["second"] is True and at["Smith family"][2]["second"] is False)
    sb = at["Sample shoot"][2]
    case("a SAMPLE backup is never safe to format", sb["safe"] is not True and sb["sample"] is True, sb)
    case("a backup with a problem: not safe (something needs a look)", at["Trouble shoot"][2]["safe"] is False)
    case("a backup that has not finished: not safe", at["Half done"][2]["safe"] is False)
    case("a second copy that did not check out: not safe, and not called a second copy", at["Half second shoot"][2]["safe"] is False and at["Half second shoot"][2]["second"] is False)
    # each shoot
    case("a queued shoot: to edit, with its due date in words", at["Garcia wedding"][3]["status"] == "waiting" and at["Garcia wedding"][3]["due"] == "due in 6 days" and not at["Garcia wedding"][3]["late"], at["Garcia wedding"][3])
    case("a late one is late", at["Lee wedding"][3]["late"] is True and "late" in at["Lee wedding"][3]["due"])
    case("a delivered shoot is \"finished\" (Edited on the page), an uploaded one \"archived\" (Just for you)",
         at["Patio session"][3]["status"] == "finished" and at[NASTY][3]["status"] == "archived")
    case("clips are counted apart from photos", at["Lee wedding details"][3]["clips"] == 4 and at["Lee wedding details"][3]["count"] == 20)
    ice = at["Iceland"]
    case("a shoot on a drive that is not plugged in: named, not found, not plugged", ice[3]["plugged"] is False and ice[3]["found"] is False and ice[3]["drive"] == NO_DRIVE
         and ice[2]["plugged"] is False and ice[2]["drive"] == NO_DRIVE and ice[2]["known"] is False, (ice[3], {k: v for k, v in ice[2].items() if k != "shoots"}))
    mv = at["Moved shoot"][3]
    case("a folder that was moved or renamed: plugged in, and not found", mv["plugged"] is True and mv["found"] is False, mv)
    case("a folder that is there: found", at["Garcia wedding"][3]["found"] is True and at["Garcia wedding"][3]["plugged"] is True)
    case("a backup whose queue record still names the day folder it settled out of is found all the same",
         at["Old spelling shoot"][2]["known"] is True and at["Old spelling shoot"][2]["safe"] is True)
    # the kits
    kits = {k["folder"]: k for k in d["kits"]}
    case("every shoot folder in Your Content that holds a kit record is a post kit, though none has a saved page", set(kits) == set(w.kits)
         and not any((w.assistant / "Your Content" / f / ".kit" / "Post kit.html").exists() for f in w.kits), sorted(set(w.kits) ^ set(kits)))
    case("a plain folder with no kit record is not listed", "Just a folder" not in kits)
    order = [k["folder"] for k in d["kits"]]
    case("newest first, the undated one last", order[0] == "2026-11-30 With pictures" and order[-1] == "No date kit", order[:2] + order[-1:])
    case("each with its name, its day and how many photos (a text file in its Photos folder is not a photo)", kits["2026-11-30 With pictures"] == {"folder": "2026-11-30 With pictures", "name": "With pictures", "date": "2026-11-30", "photos": 3, "archived": False},
         kits["2026-11-30 With pictures"])
    # in the program itself: the card that is in (what the home page draws from it is tests/home_v28_check.py's)
    os.environ["STUDIO_CARD_FOR_TESTS"] = "EOS_DIGITAL:3931"
    import home
    try:
        facts = home.facts()
        page = hb.data()
    finally:
        os.environ["STUDIO_CARD_FOR_TESTS"] = "none"
    case("with a card in, the home page is told so", facts["card"] == {"name": "EOS_DIGITAL", "files": 3931})
    case("... and the screens are told the card is in", page["card"] == {"name": "EOS_DIGITAL", "files": 3931})
    facts = home.facts()
    case("the home page reads the queue as the screens do: the shoots waiting, soonest due first, and the newest backup",
         len(facts["queue"]) == 3 and facts["queue"][0]["name"] == "Lee wedding" and facts["backup"]["when"] == "2026-11-13", (facts["queue"], facts["backup"]))
    rec = w.records["friday card"]
    a = hb.backup_status(rec)
    (rec / "manifest.json").write_text(json.dumps(manifest("friday card", problems=["x"])), encoding="utf-8")
    b = hb.backup_status(rec)
    (rec / "manifest.json").write_text(json.dumps(manifest("friday card", second=str(w.work / "second drive" / "friday card"))), encoding="utf-8")
    case("a backup's manifest is read again when it changes (a problem fixed, a problem found)", a["safe"] is True and b["safe"] is False and hb.backup_status(rec)["safe"] is True)

    check_data_review(w, hb)


def check_data_review(w, hb):
    """The review round (Nov 14): one backup spelled two ways, one odd record, a path as a picture, a broken queue."""
    import copy
    base = json.loads((w.home / "queue.json").read_text(encoding="utf-8"))
    old_way = str(w.place / "friday card" / "_studio")          # the day folder the friday card settled out of

    def friday(q):
        return [g for g in hb.backups(q) if any(s["id"].startswith("friday-card-") for b in g["backups"] for s in b["shoots"])]

    q = copy.deepcopy(base)
    next(s for s in q["shoots"] if s["id"] == "friday-card-2")["studio"] = old_way
    g = friday(q)
    case("ONE backup whose queue records spell its records folder two ways is one backup: never \"2 cards\", every shoot under it",
         len(g) == 1 and len(g[0]["backups"]) == 1 and sorted(s["id"] for s in g[0]["backups"][0]["shoots"]) == ["friday-card-1", "friday-card-2", "friday-card-3"]
         and g[0]["backups"][0]["card_no"] == 1, [(b["card_no"], [s["id"] for s in b["shoots"]]) for x in g for b in x["backups"]])
    q = copy.deepcopy(base)
    twin = dict(next(s for s in q["shoots"] if s["id"] == "friday-card-1"), id="friday-card-1-again", studio=old_way, status="archived", due=None)
    q["shoots"].insert(0, twin)
    g = friday(q)
    ids = [s["id"] for x in g for b in x["backups"] for s in b["shoots"]]
    case("the same shoot of one backup listed twice in the queue (once per spelling) shows once: the one still to edit",
         len(g) == 1 and len(g[0]["backups"]) == 1 and sorted(ids) == ["friday-card-1", "friday-card-2", "friday-card-3"], ids)
    # one odd record never takes the others with it
    for label, change in (("a due date that is not a day", lambda s: s.update(due="soon")), ("no id", lambda s: s.pop("id")),
                          ("a records folder that is not text", lambda s: s.update(studio=7)), ("a shoot that is not a record", None)):
        q = copy.deepcopy(base)
        if change:
            change(next(s for s in q["shoots"] if s.get("id") == "friday-card-1"))
        else:
            q["shoots"].insert(0, "not a shoot")
        try:
            got = hb.backups(q)
            names = [s["name"] for x in got for b in x["backups"] for s in b["shoots"]]
            why = ""
        except Exception as e:  # noqa: BLE001
            names, why = [], e.__class__.__name__
        case("one odd record in the queue (%s) never hides the other backups" % label, "Patio session" in names and "Lee wedding" in names and len(names) >= len([s for s in base["shoots"] if s.get("studio")]) - 1, why or len(names))
    q = copy.deepcopy(base)
    next(s for s in q["shoots"] if s["id"] == "friday-card-1")["due"] = "soon"
    s1 = next(s for x in hb.backups(q) for b in x["backups"] for s in b["shoots"] if s["id"] == "friday-card-1")
    case("... and a shoot whose due date is not a day is still shown, to edit, with no date", s1["status"] == "waiting" and s1["due"] is None and s1["late"] is False, s1)
    # a small picture is only ever one the queue itself made
    (w.home / "queue-thumbs" / "friday-card-1").mkdir(parents=True, exist_ok=True)
    (w.home / "queue-thumbs" / "friday-card-1" / "0.jpg").write_bytes(TINY_JPEG)
    outside = w.work / "outside.jpg"
    outside.write_bytes(TINY_JPEG)
    q = copy.deepcopy(base)
    next(s for s in q["shoots"] if s["id"] == "friday-card-1")["thumbs"] = [str(outside), "queue-thumbs/friday-card-1/0.jpg", "queue-thumbs/../../outside.jpg"]
    s1 = next(s for x in hb.backups(q) for b in x["backups"] for s in b["shoots"] if s["id"] == "friday-card-1")
    case("a shoot's small picture reaches the page only as the queue's own (queue-thumbs/...): never a path, never \"..\"", s1["thumbs"] == ["queue-thumbs/friday-card-1/0.jpg"], s1["thumbs"])
    # one odd kit record never hides the other kits
    rec = w.assistant / "Your Content" / "No date kit" / ".kit" / "kit.json"
    kept = rec.read_bytes()
    try:
        for label, odd in (("a date that is a number", json.dumps({"name": "No date kit", "date": 20261114})), ("a record that is a list", "[1, 2]")):
            rec.write_text(odd, encoding="utf-8")
            d = hb.data()
            case("one odd kit record (%s) never hides the other kits" % label, "problem_kits" not in d and {k["folder"] for k in d["kits"]} == set(w.kits), d.get("problem_kits"))
    finally:
        rec.write_bytes(kept)
    # a queue that can't be read: the screens are told so (never an empty list), and the kits still show
    qf = w.home / "queue.json"
    kept = qf.read_bytes()
    try:
        qf.write_text("{broken", encoding="utf-8")
        try:
            d, why = hb.data(), ""
        except BaseException as e:  # noqa: BLE001
            d, why = {}, e.__class__.__name__
        case("a queue.json that can't be read: the screens are told the backups couldn't be read, and the post kits still show",
             bool(d.get("problem_backups")) and d.get("groups") == [] and len(d.get("kits") or []) == len(w.kits), why or d.get("problem_backups"))
        import home
        try:
            page, why = home.page_html(), ""
        except BaseException as e:  # noqa: BLE001
            page, why = "", e.__class__.__name__
        case("... and the home page still comes", "id='s3'" in page and "id='s4'" in page, why)
        code, raw = w.http("GET", "/home")
        case("... from the page server too (it answers, it does not drop the line)", code == 200 and b"id='s4'" in raw, code)
    finally:
        qf.write_bytes(kept)


# ---------------------------------------------------------------- the routes

def listing(folder):
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))


def check_routes(w, hb):
    for path in ("/backups", "/make-posts", "/home"):
        code, page = w.page(path)
        case("%s is served, in the shared look, asking nothing of the internet" % path,
             code == 200 and "googleapis" not in page and "<link" not in page and "/look-font?f=" in page, code)
    code, page = w.page("/backups")
    case("/backups: Back to home goes to the real home page", "class='homelink' href='/home'" in page and "Back to home" in page)
    code, page = w.page("/make-posts")
    case("/make-posts: the same", "class='homelink' href='/home'" in page)
    for path in ("/backups", "/make-posts", "/home-data", "/kit-thumb?kit=x&i=1"):
        code, raw = w.http("GET", path, headers={"Host": "evil.example:%d" % w.port})
        case("a request for %s that names another host is refused" % path.split("?")[0], code == 403, code)
    code, raw = w.http("GET", "/home-data", headers={"Sec-Fetch-Site": "cross-site"})
    case("another website's page cannot read what the screens draw from", code == 403 and b"Garcia" not in raw, code)
    for path in ("/open-home", "/open-shoot?id=friday-card-1", "/report-url?id=latest", "/pick-folder", "/queue-url", "/open?kit=%s&sub=" % quote("2026-11-30 With pictures")):
        code, raw = w.http("GET", path, headers={"Sec-Fetch-Site": "cross-site"})
        case("another website's page cannot press %s (a folder window, a picker, a page server)" % path.split("?")[0], code == 403, code)
    check_no_windows(w)

    # See the report
    code, raw = w.http("GET", "/report-url?id=no-such-shoot")
    case("See the report for a shoot nobody knows: plain words, no report", code == 200 and json.loads(raw).get("ok") is False and "url" not in json.loads(raw))
    code, raw = w.http("GET", "/report-url?id=unplugged-1")
    case("See the report on an unplugged drive: \"Plug in <drive> to see this report.\"", json.loads(raw).get("words") == "Plug in %s to see this report." % NO_DRIVE, raw[:200])
    code, raw = w.http("GET", "/report-url?id=old-spelling-1")
    words = json.loads(raw).get("words") or ""
    case("See the report finds a settled backup's records from the day folder it settled out of (never \"plug in\"), and says \"the Assistant\"",
         "Plug in" not in words and "the Assistant" in words and "Claude" not in words, words)
    code, raw = w.http("GET", "/open-shoot?id=no-such-shoot")
    case("Open this folder for a shoot nobody knows opens nothing", json.loads(raw) == {"ok": False, "words": "I don't know that shoot."}, raw[:200])
    code, raw = w.http("GET", "/open-shoot?id=unplugged-1")
    case("Open this folder on an unplugged drive opens nothing and says which drive", json.loads(raw).get("ok") is False and NO_DRIVE in json.loads(raw).get("words", ""), raw[:200])

    # a kit's small pictures
    code, raw = w.http("GET", "/kit-thumb?kit=%s&i=1" % quote("2026-11-30 With pictures"))
    if code == 200:
        case("a kit's small picture is made the first time it is asked for, in the Assistant's own folder", raw[:2] == b"\xff\xd8" and (w.home / "home-thumbs" / "2026-11-30 With pictures-1.jpg").is_file())
    else:
        skip("a kit's small picture: this computer can't make one (no sips, no Pillow): %s" % code)
    for q in ("kit=%s&i=4" % quote("2026-11-30 With pictures"), "kit=%s&i=1" % quote("../studio-home"), "kit=Just%20a%20folder&i=1", "kit=nope&i=1", "i=1",
              "kit=%s&i=1" % quote("2026-11-28 Kit shoot 00")):
        code, raw = w.http("GET", "/kit-thumb?" + q)
        case("no picture for /kit-thumb?%s" % q[:40], code == 404, code)

    # a kit whose page was never written opens (v25, section 10)
    code, page = w.page("/content/%s/Post%%20kit.html" % quote("2026-11-28 Kit shoot 00"))
    case("a post kit with no saved page still opens: the page is built when it is asked for", code == 200 and "Kit shoot 00" in page, code)
    code, page = w.page("/content/%s/Post%%20kit.html" % quote(ODD_FOLDER, safe=""))
    case("... and so does one whose folder name has #, %, & and ? in it", code == 200, code)

    # Archive and Bring it back
    content = w.assistant / "Your Content"
    before = listing(content)
    f, prev = w.home / "kit-archive.json", w.home / "kit-archive.prev.json"
    case("no archive list before anything is archived", not f.exists())
    kit = "2026-11-28 Kit shoot 00"
    code, out = w.archive(kit, True)
    case("Archive: the kit is on the list, in ~/.studio/kit-archive.json", code == 200 and out == {"ok": True, "archived": [kit]} and json.loads(f.read_text(encoding="utf-8")) == {"archived": [kit]}, (code, out))
    stamp = f.stat().st_mtime_ns
    time.sleep(0.02)
    code, out = w.archive(kit, True)
    case("a second press changes nothing and writes nothing", code == 200 and out == {"ok": True, "archived": [kit]} and f.stat().st_mtime_ns == stamp and not prev.exists())
    code, out = w.archive("2026-11-30 With pictures", True)
    case("a second kit: both on the list, and the list before is kept beside it",
         code == 200 and out["archived"] == sorted([kit, "2026-11-30 With pictures"]) and json.loads(prev.read_text(encoding="utf-8")) == {"archived": [kit]}, out)
    case("/home-data says which kits are archived", {k["folder"] for k in w.data()["kits"] if k["archived"]} == {kit, "2026-11-30 With pictures"})
    code, out = w.archive("2026-11-30 With pictures", False)
    case("Bring it back: off the list", code == 200 and out == {"ok": True, "archived": [kit]}, out)
    case("no kit was moved, renamed or changed by any of it", listing(content) == before)
    kept = f.read_bytes()
    for label, name in (("a name that is not a kit", "No such shoot"), ("a plain folder with no kit record", "Just a folder"), ("a path out of Your Content", "../The Assistant"),
                        ("a hidden name", ".kit")):
        code, out = w.archive(name, True)
        case("%s is refused, in her words, nothing changed" % label, code == 400 and out == {"ok": False, "problem": "That shoot isn't in your content folder."} and f.read_bytes() == kept, (code, out))
    for label, body in (("a name that is not text", {"shoot": 7, "archived": True}), ("archived that is not yes or no", {"shoot": kit, "archived": "yes"}),
                        ("a field too many", {"shoot": kit, "archived": False, "path": "/"}), ("a field missing", {"shoot": kit}), ("a list", [kit, False]),
                        ("a name of 201 letters", {"shoot": "x" * 201, "archived": True})):
        code, raw = w.http("POST", "/kit-archive", body)
        case("a press with %s is refused, nothing changed" % label, code == 400 and f.read_bytes() == kept, code)
    code, raw = w.http("POST", "/kit-archive", raw=b"{not json", headers={"Content-Type": "application/json"})
    case("a press that is not JSON is refused", code == 400 and f.read_bytes() == kept, code)
    for label, kw in (("another website (its Origin)", {"headers": {"Origin": "https://evil.example"}}), ("another website (a cross-site press)", {"headers": {"Sec-Fetch-Site": "cross-site"}}),
                      ("another host's name", {"headers": {"Host": "evil.example:%d" % w.port}}), ("the wrong kind of body", {"headers": {"Content-Type": "text/plain"}})):
        code, out = w.archive(kit, False, **kw)
        case("a press from %s is refused, nothing changed" % label, code in (403, 415) and f.read_bytes() == kept, code)
    code, raw = w.http("POST", "/kit-archive", raw=b'{"shoot": "' + b"x" * 3000 + b'", "archived": true}')
    case("a press that is too big is refused before it is read", code == 413 and f.read_bytes() == kept, code)
    code, out = w.archive(kit, False)
    case("after all that, Bring it back still works, and the list is empty again", code == 200 and out == {"ok": True, "archived": []}, out)
    # a list that was damaged (by hand, by a disk): set aside whole, the last good list before never written over
    w.archive(kit, True)
    w.archive("2026-11-30 With pictures", True)
    good_prev = prev.read_bytes()
    f.write_text("{broken", encoding="utf-8")
    code, out = w.archive("No date kit", True)
    aside = sorted(p.name for p in w.home.glob("kit-archive.unreadable-*.json"))
    case("a damaged archive list is set aside under a name of its own; the list before is not written over",
         code == 200 and out == {"ok": True, "archived": ["No date kit"]} and prev.read_bytes() == good_prev and len(aside) == 1
         and (w.home / aside[0]).read_text(encoding="utf-8") == "{broken", (code, out, aside))
    for odd in ('{"archived": "nope"}', '{"archived": {"a": 1}}', '{"archived": ["x", 7]}', '"nope"'):
        f.write_text(odd, encoding="utf-8")
        got = {k["folder"] for k in w.data()["kits"] if k["archived"]}
        case("an archive list of the wrong shape (%s) is read as no list, never as names" % odd, got == set() and hb.archived() == set(), sorted(got))
    f.write_text(json.dumps({"archived": []}), encoding="utf-8")

    # the other pages point at the real routes
    import edit_queue
    link = edit_queue.make_posts_link()
    case("the editing queue's Make posts from this shoot goes to this server's /make-posts", link == w.url("/make-posts"), link)
    case("... and its Back to home to /home", "href='%s'" % w.url("/home") in edit_queue.home_link())
    hits = []
    for p in sorted((ROOT / "plugins").rglob("*")):
        if p.is_file() and p.suffix in (".py", ".md", ".json", ".js", ".html"):
            t = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\b8799\b|home=test|assistantHomeTest", t):
                hits.append(p.name)
    case("no port 8799 and no ?home=test anywhere in the plugin", not hits, hits)


def check_no_windows(w):
    """The tests' own switch (STUDIO_NO_WINDOWS_FOR_TESTS): with it set, nothing shows on the screen and no other
    program or server is started, so a guard that fails here can never put a window or a folder picker on
    someone's screen. Checked in the program itself, with the computer's own commands watched, never run."""
    import finder
    import serve_report
    import this_computer
    ran = []

    def watch(*a, **k):
        ran.append(a[0] if a else k.get("args"))
        raise OSError("a test never runs this")

    case("this test's page server runs with the no-windows switch set", w.env.get("STUDIO_NO_WINDOWS_FOR_TESTS") == "1")
    real = (this_computer.subprocess.run, finder.subprocess.run, getattr(os, "startfile", None), serve_report.fresh.start_server)
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    try:
        this_computer.subprocess.run = finder.subprocess.run = watch
        if real[2]:
            os.startfile = watch
        serve_report.fresh.start_server = watch
        picked = this_computer.pick_folder("a test")
        opened = finder.open_folder(w.place)
        played = finder.open_file(w.place / "nothing.mp4")
        page = w.records["friday card"] / "report.html"       # a report there is to show, so a server would be started for it
        page.write_text("<p>a pretend report</p>", encoding="utf-8")
        try:
            report = serve_report.report_url(w.records["friday card"])
        finally:
            page.unlink()
        queue = serve_report.queue_url()
    finally:
        this_computer.subprocess.run, finder.subprocess.run = real[0], real[1]
        if real[2]:
            os.startfile = real[2]
        serve_report.fresh.start_server = real[3]
        os.environ.pop("STUDIO_NO_WINDOWS_FOR_TESTS", None)
    case("with the switch, the folder picker never opens (it answers as if closed)", picked == (None, "cancelled") and not ran, (picked, ran[:1]))
    case("with the switch, no folder window and no player opens", opened == (True, "") and played == (True, "") and not ran, (opened, played, ran[:1]))
    case("with the switch, no report server and no queue server is started", report is None and queue is None and not ran, (report, queue, ran[:1]))
    # and through the page server itself: the same-page asks answer, and nothing is left running or waiting.
    # Asked only when the program itself has just proved it opens nothing (a real picker must never appear).
    if not (w.env.get("STUDIO_NO_WINDOWS_FOR_TESTS") == "1" and picked == (None, "cancelled") and opened == (True, "") and not ran):
        case("the server is not asked for a picker or a folder while the switch does not hold", False)
        return
    code, raw = w.http("GET", "/pick-folder")
    case("the server, asked for the folder picker by its own page, answers at once with no folder chosen", code == 200 and json.loads(raw).get("words") == "No folder chosen.", raw[:200])
    code, raw = w.http("GET", "/open-home")
    case("... and Open my Assistant folder answers its line", code == 200 and json.loads(raw).get("words") == "Opened The Assistant in %s." % this_computer.FILES_APP, raw[:200])


# ---------------------------------------------------------------- the pages, in a hidden Chrome

STUB_JS = r"""
(function(){
  var real = window.fetch;
  window.__asked = [];
  window.__answers = {
    '/open-shoot': {ok: true, words: 'Opened 2026 Garcia wedding in Finder.'},
    '/report-url': {ok: false, words: 'Pretend: the report would open here.'},
    '/pick-folder': {ok: true, words: "Copied 48 finished photos from Final Exports. Your originals weren't moved.", copied: 48},
    '/open-home': {ok: true, words: 'Opened The Assistant in Finder.'},
    '/queue-url': {url: null, words: 'Pretend: the editing queue would open here.'}
  };
  window.fetch = function(u, o){
    var path = String(u).split('?')[0];
    if (window.__answers[path]) {
      window.__asked.push(String(u));
      return Promise.resolve(new Response(JSON.stringify(window.__answers[path]), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    return real.apply(this, arguments);
  };
})();
"""


def asked(c, n):
    """Wait until the page has asked n things of the Assistant and has shown what came back."""
    c.wait_for("window.__asked.length == %d" % n, 5)
    time.sleep(0.25)


def texts(c, sel):
    return c.js("Array.from(document.querySelectorAll(%s)).map(e => e.textContent.replace(/\\s+/g, ' ').trim())" % json.dumps(sel))


def no_sideways(c, width):
    """Nothing on the page is wider than the phone. (A phone's browser zooms out to fit a page that is too wide,
    so the page is measured against the phone's own width, never against the window as it then stands.)"""
    return c.js("document.documentElement.scrollWidth <= %d + 1 && window.innerWidth <= %d + 1" % (width, width))


def search(c, text):
    c.js("(() => { const i = document.querySelector('#find'); i.value = %s; i.dispatchEvent(new Event('input')); })()" % json.dumps(text))


def backup_of(c, shoot):
    """The index of the backup card that holds this shoot."""
    return c.js("Array.from(document.querySelectorAll('#backups .backup')).findIndex(b => Array.from(b.querySelectorAll('.shoot b')).some(x => x.textContent === %s))" % json.dumps(shoot))


def in_backup(c, shoot, sel):
    return c.js("(() => { const b = Array.from(document.querySelectorAll('#backups .backup')).find(b => Array.from(b.querySelectorAll('.shoot b')).some(x => x.textContent === %s)); "
                "return b ? Array.from(b.querySelectorAll(%s)).map(e => e.textContent.replace(/\\s+/g, ' ').trim()) : null; })()" % (json.dumps(shoot), json.dumps(sel)))


def in_shoot(c, shoot, sel):
    return c.js("(() => { const s = Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === %s); "
                "return s ? Array.from(s.querySelectorAll(%s)).map(e => e.textContent.replace(/\\s+/g, ' ').trim()) : null; })()" % (json.dumps(shoot), json.dumps(sel)))


def check_home_page(c, w):
    # (the home page itself, her v28's, is tests/home_v28_check.py's; here: it leads to the two screens and back)
    c.open(w.url("/home"))
    c.wait_for("document.querySelectorAll('#s1, #s2, #s3, #s4').length == 4", 10)
    # (her v30 look since Nov 21: tests/home_v30_check.py holds the layout itself)
    case("home: Turn your shoots into posts, then the three cards by name (her v30)", c.text("#s3 h1") == "Turn your shoots into posts"
         and texts(c, "#s4 .n, .also .n") == ["My posting queue", "Back up a card", "My editing queue"], texts(c, "#s4 .n, .also .n"))
    case("home: the cards are not numbered", c.count(".k") == 0)
    case("home: See all my post kits under the tiles, and the posting queue's own label", c.text("#kitsBtn") in ("Create your post kits →", "See all my post kits →") and texts(c, "#s4 .lnk2") == ["Open my posting queue →"], texts(c, "#s4 .lnk2"))
    case("home: no shoots and no kits listed on it", c.count(".shoot") == 0 and c.count(".backup") == 0)
    case("home: no page errors", not c.page_errors(), c.page_errors()[:2])
    # the editing queue card and the folder button: what they ask, and where the answer shows
    c.click("#s2")
    asked(c, 1)
    case("home: My editing queue asks for the queue's address, and what comes back shows on the card itself",
         c.js("window.__asked[0]") == "/queue-url" and c.js("document.querySelector('#s2 .note').textContent") == "Pretend: the editing queue would open here.")
    c.click("#folder")
    asked(c, 2)
    case("home: Open my Assistant folder asks to open it, and the line shows right beside that button",
         c.js("window.__asked[1]") == "/open-home" and c.js("document.querySelector('.bar .fold .note').textContent") == "Opened The Assistant in Finder.")
    time.sleep(0.3)
    j = json.loads((w.home / "journey.json").read_text(encoding="utf-8"))
    case("home: both presses were recorded for the chat (journey.json)", [x["item"] for x in j["clicks"]][-2:] == ["queue", "folder"], j["clicks"][-3:])
    time.sleep(4.6)
    case("home: recording a press does not reload the page from under the line it just showed",
         c.js("document.querySelector('.bar .fold .note').textContent") == "Opened The Assistant in Finder.")
    c.click("#s1")
    c.wait_for("location.pathname === '/backups'", 10)
    case("home: Back up a card opens its own screen", c.js("location.pathname") == "/backups")
    time.sleep(0.3)
    j = json.loads((w.home / "journey.json").read_text(encoding="utf-8"))
    case("... and the press is recorded as a backup press", j["clicks"][-1]["item"] == "backup", j["clicks"][-1])
    c.click(".homelink")
    c.wait_for("location.pathname === '/home'", 10)
    c.click("#kitsBtn")
    c.wait_for("location.pathname === '/make-posts'", 10)
    case("home: Back to home comes back, and Turn your shoots into posts opens its own screen", c.js("location.pathname") == "/make-posts")
    c.click(".homelink")
    c.wait_for("location.pathname === '/home'", 10)
    c.click("#s4")
    c.wait_for("location.pathname === '/posting.html'", 10)
    case("home: My posting queue opens the posting queue", c.js("location.pathname") == "/posting.html")


def check_backups_page(c, w):
    c.open(w.url("/backups"))
    c.wait_for("document.querySelectorAll('#backups .backup').length > 0", 15)
    case("backups: her heading, her two paragraphs, her steps box", c.text("h1") == "Back up a card." and len(texts(c, ".head .lede")) == 2
         and c.text(".steps-title") == "How to back up a card" and texts(c, ".steps .num") == ["1", "2"])
    case("backups: step 1 says whether a card is in", c.text("#cardStatus") == "No card in yet.", c.text("#cardStatus"))
    case("backups: the words to paste, with Copy", c.text(".paste .words") == "backup now" and c.text(".paste .copy") == "Copy" and c.js("document.querySelector('.paste .copy').dataset.copy") == "backup now")
    c.js("document.execCommand = function(){ window.__copied = document.activeElement && document.activeElement.value; return true; }")
    c.click(".paste .copy")
    case("backups: Copy copies them and says Copied", c.js("window.__copied") == "backup now" and c.text(".paste .copy") == "Copied")
    case("backups: the steps box is light (white, not black)", c.js("getComputedStyle(document.querySelector('.steps')).backgroundColor") == "rgb(255, 255, 255)")
    case("backups: the 10 newest, and a button for the rest", c.count("#backups .backup") == 10 and c.text("#older") == "Show 9 older backups" and c.count("#backups h3.month") == 0,
         (c.count("#backups .backup"), c.text("#older") if c.count("#older") else None))
    case("backups: the newest is first, dated as she writes a day", texts(c, "#backups .backup h3")[0] == "Backed up Nov 13, 2026", texts(c, "#backups .backup h3")[:2])
    # one backup at a glance
    case("backups: a backup's line: how many shoots and photos", in_backup(c, "Garcia wedding", ".top .meta") == ["3 shoots · 306 photos"], in_backup(c, "Garcia wedding", ".top .meta"))
    case("backups: Card safe to format, Second copy made", in_backup(c, "Garcia wedding", ".flags .pill") == ["Card safe to format", "Second copy made"], in_backup(c, "Garcia wedding", ".flags .pill"))
    case("backups: a queued shoot says To edit with its due date; a delivered one Edited; an uploaded one Just for you",
         in_shoot(c, "Garcia wedding", ".pill") == ["To edit, due in 6 days"] and in_shoot(c, "Patio session", ".pill") == ["Edited"] and in_shoot(c, NASTY, ".pill") == ["Just for you"],
         (in_shoot(c, "Garcia wedding", ".pill"), in_shoot(c, "Patio session", ".pill"), in_shoot(c, NASTY, ".pill")))
    case("backups: each shoot has Open this folder with See the report under it",
         in_shoot(c, "Garcia wedding", ".acts .btn") == ["Open this folder", "See the report"]
         and c.js("(() => { const b = Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Garcia wedding').querySelectorAll('.acts .btn'); return b[1].getBoundingClientRect().top >= b[0].getBoundingClientRect().bottom - 1; })()"))
    case("backups: a name with <, & and a script is shown as text only", c.js("window.__got === undefined && !document.querySelector('#backups img[src=x]')") and backup_of(c, NASTY) == 0)
    # the cards of one shoot
    lee = backup_of(c, "Lee wedding")
    case("backups: the two cards of one shoot are one backup: \"2 cards\", both shoots in it", lee >= 0 and lee == backup_of(c, "Lee wedding details")
         and in_backup(c, "Lee wedding", ".top .meta") == ["2 cards · 2 shoots · 121 photos and 4 video clips"], in_backup(c, "Lee wedding", ".top .meta"))
    case("backups: ... each shoot labeled with its card, and \"Cards safe to format\"",
         in_shoot(c, "Lee wedding", "small")[0].endswith("· card 1") and in_shoot(c, "Lee wedding details", "small")[0].endswith("· card 2")
         and in_backup(c, "Lee wedding", ".flags .pill") == ["Cards safe to format", "No second copy"], (in_shoot(c, "Lee wedding", "small"), in_backup(c, "Lee wedding", ".flags .pill")))
    case("backups: a late shoot's pill is the late colour", c.js("Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Lee wedding').querySelector('.pill').classList.contains('late')"))
    case("backups: a shoot with clips never calls them photos", "20 photos and 4 video clips" in in_shoot(c, "Lee wedding details", "small")[0], in_shoot(c, "Lee wedding details", "small"))
    case("backups: two backups that only look alike by name are two backups, with no card labels",
         backup_of(c, "Smith family") != backup_of(c, "Smith cousins") and "card" not in in_shoot(c, "Smith family", "small")[0] and "cards" not in in_backup(c, "Smith family", ".top .meta")[0])
    case("backups: a SAMPLE never says safe to format; it says to keep the card", in_backup(c, "Sample shoot", ".flags .pill") == ["Keep the card: this was a sample", "No second copy"], in_backup(c, "Sample shoot", ".flags .pill"))
    case("backups: a backup with a problem: Something needs a look: see the report", in_backup(c, "Trouble shoot", ".flags .pill")[0] == "Something needs a look: see the report", in_backup(c, "Trouble shoot", ".flags .pill"))
    case("backups: a folder that was moved says so, with no dead button",
         in_shoot(c, "Moved shoot", ".warn") == ["I can't find this folder anymore. If you moved or renamed it in Finder, tell the Assistant where it went."] and in_shoot(c, "Moved shoot", ".btn") == [], in_shoot(c, "Moved shoot", ".warn"))
    # a press, and where its line shows
    c.js("Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Garcia wedding').querySelector('[data-open]').click()")
    asked(c, 1)
    case("backups: Open this folder asks for that shoot by its id (never a path), and the line shows right under the button",
         c.js("window.__asked[0]") == "/open-shoot?id=friday-card-1"
         and c.js("(() => { const b = Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Garcia wedding').querySelector('[data-open]'); return b.nextElementSibling.className + '|' + b.nextElementSibling.textContent; })()") == "note|Opened 2026 Garcia wedding in Finder.")
    c.js("Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Patio session').querySelector('[data-report]').click()")
    asked(c, 2)
    case("backups: See the report asks for that shoot's backup, the line under that button",
         c.js("window.__asked[1]") == "/report-url?id=friday-card-3"
         and c.js("Array.from(document.querySelectorAll('#backups .shoot')).find(s => s.querySelector('b').textContent === 'Patio session').querySelector('[data-report]').nextElementSibling.textContent") == "Pretend: the report would open here.")
    # Show older
    c.click("#older")
    case("backups: Show older shows every backup, the older ones under their months", c.count("#backups .backup") == 19 and texts(c, "#backups h3.month") == ["November 2026", "October 2026", "September 2026", "August 2026"]
         and c.text("#older") == "Show only the 10 most recent", (c.count("#backups .backup"), texts(c, "#backups h3.month")))
    case("backups: the first month heading comes after the 10 newest", c.js("(() => { const all = Array.from(document.querySelectorAll('#backups > *')); return all.findIndex(e => e.matches('h3.month')); })()") == 10)
    case("backups: a shoot on a drive that is not plugged in: her line, no dead button, and the backup says where it is",
         in_shoot(c, "Iceland", ".warn") == ["This one's on %s. Plug it in to open it." % NO_DRIVE] and in_shoot(c, "Iceland", ".btn") == []
         and in_backup(c, "Iceland", ".flags .pill") == ["On %s, not plugged in" % NO_DRIVE], (in_shoot(c, "Iceland", ".warn"), in_backup(c, "Iceland", ".flags .pill")))
    c.click("#older")
    case("backups: and back to the 10 most recent", c.count("#backups .backup") == 10 and c.text("#older") == "Show 9 older backups")
    # the search
    search(c, "OLDER SHOOT 7")
    case("backups: the search finds a shoot by name, whatever the capitals, among the older ones too", texts(c, "#backups .shoot b") == ["Older shoot 7"] and c.count("#older") == 0, texts(c, "#backups .shoot b"))
    search(c, "lee wedding det")
    case("backups: a search inside a two-card shoot shows only the shoot that matches", texts(c, "#backups .shoot b") == ["Lee wedding details"], texts(c, "#backups .shoot b"))
    search(c, "zzz Nobody")
    case("backups: nothing by that name: her line", texts(c, "#backups .empty") == ['No shoot called "zzz nobody" yet.'], texts(c, "#backups .empty"))
    search(c, "<img src=x onerror=window.__got2=1>")
    case("backups: what is typed in the search is only ever shown as text", c.js("window.__got2 === undefined && !document.querySelector('#backups img[src=x]')"))
    search(c, "")
    case("backups: an empty search shows the 10 newest again", c.count("#backups .backup") == 10)
    case("backups: no page errors", not c.page_errors(), c.page_errors()[:2])
    # it follows what changes: a shoot marked as delivered in the chat shows as Edited without a reload
    code, out = w.run("edit_queue.py", "done", "garcia")
    try:
        c.wait_for("Array.from(document.querySelectorAll('#backups .shoot')).some(s => s.querySelector('b').textContent === 'Garcia wedding' && s.querySelector('.pill').textContent === 'Edited')", 12)
        ok = True
    except chrome_drive.Timeout:
        ok = False
    case("backups: a change made in the chat shows on the open page by itself (a shoot marked as delivered reads Edited)", code == 0 and ok, out[-200:])
    w.run("edit_queue.py", "undo", "garcia")


def kit_names(c, sel="#recent .shoot b"):
    return texts(c, sel)


def check_make_page(c, w):
    c.open(w.url("/make-posts"))
    c.wait_for("document.querySelectorAll('#recent .shoot').length > 0", 15)
    case("make posts: her heading, her paragraph, her steps box (v27: a post kit from a shoot, three steps)", c.text("h1") == "Turn your shoots into posts." and len(texts(c, ".head .lede")) == 1
         and c.text(".steps-title") == "How to make a post kit from a shoot" and c.text("#pick") == "Select the folder with your finished photos" and texts(c, ".steps .num") == ["1", "2", "3"],
         (c.text(".steps-title"), texts(c, ".steps .num")))
    case("make posts: the What's a post kit? box is drawn between the lede and the steps title, as her screenshot 08",
         c.text(".whatkit .wk-h") == "What's a post kit?" and c.js("document.querySelector('.whatkit').previousElementSibling.className") == "head"
         and c.js("document.querySelector('.whatkit').nextElementSibling.className") == "steps-title"
         and c.js("document.querySelector('.whatkit').getBoundingClientRect().top") > c.js("document.querySelector('.head .lede').getBoundingClientRect().bottom"),
         (c.text(".whatkit .wk-h"), c.js("document.querySelector('.whatkit').previousElementSibling.className"), c.js("document.querySelector('.whatkit').nextElementSibling.className")))
    case("make posts: step 3 is words only, no button, and its small line is hers", c.count(".steps .st:nth-child(3) button, .steps .st:nth-child(3) a") == 0
         and c.text(".steps .st:nth-child(3) small") == "Pick what you want to make: a reel, a carousel, stories or a caption. Each one walks you through it.")
    case("make posts: the words to paste", c.text(".paste .words") == "make my posts" and c.js("document.querySelector('.paste .copy').dataset.copy") == "make my posts")
    case("make posts: the 20 newest in one grid, and a button for the rest", c.count("#recent .shoot") == 20 and c.count("#recent h3.month") == 0 and c.text("#older") == "Show 7 older post kits",
         (c.count("#recent .shoot"), c.text("#older") if c.count("#older") else None))
    case("make posts: newest first, by the name the kit has", kit_names(c)[:2] == ["With pictures", NASTY], kit_names(c)[:3])
    case("make posts: a kit's line: its day and how many photos", c.js("document.querySelector('#recent .shoot small').textContent") == "Nov 30, 2026 · 3 photos")
    case("make posts: each kit has Open the post kit and Archive", texts(c, "#recent .shoot:first-child .acts > *") == ["Open the post kit", "Archive"], texts(c, "#recent .shoot:first-child .acts > *"))
    case("make posts: Open the post kit leads to that kit's own page", c.js("document.querySelector('#recent .shoot:first-child a.btn').getAttribute('href')") == "/content/2026-11-30%20With%20pictures/Post%20kit.html")
    case("make posts: a name with <, & and a script is shown as text only", c.js("window.__got === undefined && !document.querySelector('#recent img[src=x]')"))
    case("make posts: the Archived list is not shown while nothing is archived", c.js("document.querySelector('#archBox').hidden"))
    c.click("#pick")
    asked(c, 1)
    case("make posts: Select the folder asks for the computer's own folder picker, and what was copied shows right under the button",
         c.js("window.__asked[0]") == "/pick-folder" and c.js("document.querySelector('#pick').nextElementSibling.textContent") == "Copied 48 finished photos from Final Exports. Your originals weren't moved.")
    # Show older, by month
    c.click("#older")
    case("make posts: Show older puts the older kits under their months, the undated one under No date",
         c.count("#recent .shoot") == 27 and texts(c, "#recent h3.month") == ["September 2026", "August 2026", "No date"] and c.text("#older") == "Show only the 20 most recent",
         (c.count("#recent .shoot"), texts(c, "#recent h3.month")))
    c.click("#older")
    # Archive
    c.js("Array.from(document.querySelectorAll('#recent .shoot')).find(s => s.querySelector('b').textContent === 'Kit shoot 00').querySelector('[data-arch]').click()")
    c.wait_for("!document.querySelector('#archBox').hidden", 10)
    case("make posts: Archive moves the kit into the Archived list, which opens and closes and starts closed",
         "Kit shoot 00" not in kit_names(c) and c.text("#archSum") == "Archived (1)" and not c.js("document.querySelector('#archBox').open") and kit_names(c, "#archived .shoot b") == ["Kit shoot 00"],
         (c.text("#archSum"), kit_names(c, "#archived .shoot b")))
    case("make posts: ... the list is in kit-archive.json, and the kit's folder is where it was", json.loads((w.home / "kit-archive.json").read_text(encoding="utf-8")) == {"archived": ["2026-11-28 Kit shoot 00"]}
         and (w.assistant / "Your Content" / "2026-11-28 Kit shoot 00" / ".kit" / "kit.json").is_file())
    case("make posts: the 20 newest fill up again from the older ones", c.count("#recent .shoot") == 20 and c.text("#older") == "Show 6 older post kits")
    search(c, "kit shoot 0")
    case("make posts: the search looks through the archived kits too", "Kit shoot 00" in kit_names(c, "#archived .shoot b") and c.text("#archSum") == "Archived (1)"
         and sorted(kit_names(c)) == ["Kit shoot %02d" % i for i in range(1, 10)], (kit_names(c), kit_names(c, "#archived .shoot b")))
    search(c, "zzz nobody")
    case("make posts: nothing by that name: her line, and no Archived list", texts(c, "#recent .empty") == ['No post kit called "zzz nobody" yet.'] and c.js("document.querySelector('#archBox').hidden"), texts(c, "#recent .empty"))
    search(c, "")
    c.js("document.querySelector('#archBox').open = true")
    case("make posts: an archived kit has Open the post kit and Bring it back", texts(c, "#archived .shoot .acts > *") == ["Open the post kit", "Bring it back"])
    c.click("#archived [data-arch]")
    c.wait_for("document.querySelector('#archBox').hidden", 10)
    case("make posts: Bring it back returns it to the list, in its place by date", "Kit shoot 00" in kit_names(c) and json.loads((w.home / "kit-archive.json").read_text(encoding="utf-8")) == {"archived": []})
    # a kit that has gone meanwhile: the refusal shows by the button
    c.click("#older")
    shutil.move(str(w.assistant / "Your Content" / "No date kit"), str(w.work / "No date kit (moved by the test)"))
    c.js("Array.from(document.querySelectorAll('#recent .shoot')).find(s => s.querySelector('b').textContent === 'No date kit').querySelector('[data-arch]').click()")
    try:
        c.wait_for("!!Array.from(document.querySelectorAll('#recent .shoot')).find(s => s.querySelector('b').textContent === 'No date kit').querySelector('.note')", 8)
        said = c.js("Array.from(document.querySelectorAll('#recent .shoot')).find(s => s.querySelector('b').textContent === 'No date kit').querySelector('.note').textContent")
    except chrome_drive.Timeout:
        said = None
    case("make posts: Archive on a kit that is no longer there says so, in her words, by that kit", said == "That shoot isn't in your content folder.", said)
    shutil.move(str(w.work / "No date kit (moved by the test)"), str(w.assistant / "Your Content" / "No date kit"))
    case("make posts: no page errors", not c.page_errors(), c.page_errors()[:2])
    # the pictures
    code, raw = w.http("GET", "/kit-thumb?kit=%s&i=1" % quote("2026-11-30 With pictures"))
    if code == 200:
        c.open(w.url("/make-posts"))
        try:
            c.wait_for("(() => { const i = document.querySelector('#recent .shoot .ph img'); return i && i.complete && i.naturalWidth > 0; })()", 10)
            ok = True
        except chrome_drive.Timeout:
            ok = False
        case("make posts: a kit with photos shows its small pictures; one without shows plain tiles",
             ok and c.js("document.querySelectorAll('#recent .shoot:first-child .ph img').length") == 3)
    else:
        skip("make posts: a kit's small pictures (this computer can't make one)")
    # opening a kit from the list
    c.open(w.url("/make-posts"))
    c.wait_for("document.querySelectorAll('#recent .shoot').length > 0", 15)
    c.js("Array.from(document.querySelectorAll('#recent .shoot')).find(s => s.querySelector('b').textContent === 'Kit shoot 01').querySelector('a.btn').click()")
    c.wait_for("location.pathname.indexOf('/content/') === 0 && document.readyState === 'complete'", 15)
    case("make posts: Open the post kit opens a kit whose page was never written", "Kit shoot 01" in c.js("document.body.textContent") and c.js("location.pathname").endswith("/Post%20kit.html"), c.js("location.pathname"))


def check_cant_read(c, w):
    """The review round: when the Assistant says it could not read the backups (or the kits) just now, the screen
    keeps the list it had, or says her "can't reach" line; it never says there is nothing."""
    for path, ready, box, row, problem, cant, none in (
            ("/backups", "document.querySelectorAll('#backups .backup').length > 0", "#backups", "#backups .backup", "problem_backups", "b_cant", "b_none"),
            ("/make-posts", "document.querySelectorAll('#recent .shoot').length > 0", "#recent", "#recent .shoot", "problem_kits", "m_cant", "m_none")):
        c.open(w.url(path))
        c.wait_for(ready, 15)
        had = c.count(row)
        c.js("homeData = async () => ({ok: true, card: null, groups: [], kits: [], %s: 'KeyError', stamp: ''})" % problem)
        c.js("load()")
        case("%s: the records could not be read just now: the list it had stays" % path, c.count(row) == had and had > 0, (had, c.count(row)))
        c.js("got = false")
        c.js("load()")
        said = c.js("document.querySelector(%s).textContent.trim()" % json.dumps(box))
        case("%s: ... and with no list yet it says her \"can't reach\" line, never that there is nothing" % path,
             said == c.js("W.%s" % cant) and said != c.js("W.%s" % none) and c.count(row) == 0, said)


def check_phone(c, w):
    # a name with no place to break (an underscore-joined shoot name; a long card name) never widens a page
    long_name = "Lee_wedding_" + "x" * 100
    qf = w.home / "queue.json"
    kept = qf.read_bytes()
    q = json.loads(kept.decode("utf-8"))
    next(s for s in q["shoots"] if s["name"] == "Lee wedding")["name"] = long_name       # late, so it is on Today too
    qf.write_text(json.dumps(q, indent=1), encoding="utf-8")
    try:
        check_phone_pages(c, w, long_name)
    finally:
        qf.write_bytes(kept)


def check_phone_pages(c, w, long_name):
    c.phone(width=375, height=800)
    try:
        for path, ready in (("/home", "document.querySelectorAll('#s1, #s2, #s3, #s4').length == 4"), ("/backups", "document.querySelectorAll('#backups .backup').length > 0"),
                            ("/make-posts", "document.querySelectorAll('#recent .shoot').length > 0")):
            c.open(w.url(path))
            c.wait_for(ready, 15)
            if path == "/backups":
                c.js("document.querySelector('#older').click()")
                c.js("document.querySelector('#cardStatus').textContent = fill(W.b_card_in, {name: %s, files: '3,931'})" % json.dumps("CARD_" + "W" * 100))
            if path == "/home":
                case("phone width: the long name is in the editing queue's box on the home page", long_name in c.js("document.querySelector('#n2').textContent"))
            if path == "/backups":
                case("phone width: the long name is on a backup, and the long card name in the steps box", backup_of(c, long_name) >= 0 and "WWWWWWWW" in c.text("#cardStatus"))
            case("phone width: %s has no sideways scroll, with a 100-letter name that has no place to break" % path, no_sideways(c, 375), c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
            if path == "/make-posts":
                case("phone width: the What's a post kit? box fits the screen", c.js("(r => r.left >= 0 && r.right <= window.innerWidth && r.height > 40)(document.querySelector('.whatkit').getBoundingClientRect())"),
                     c.js("[document.querySelector('.whatkit').getBoundingClientRect().right, window.innerWidth]"))
            if path != "/home":
                case("phone width: %s: the Back to home button reads Home" % path, c.js("getComputedStyle(document.querySelector('.homelink .long')).display") == "none"
                     and c.js("getComputedStyle(document.querySelector('.homelink .short')).display") != "none")
        c.phone(width=336, height=700)
        for path, ready in (("/home", "document.querySelectorAll('#s1, #s2, #s3, #s4').length == 4"), ("/backups", "document.querySelectorAll('#backups .backup').length > 0"),
                            ("/make-posts", "document.querySelectorAll('#recent .shoot').length > 0")):
            c.open(w.url(path))
            c.wait_for(ready, 15)
            if path == "/backups":
                c.js("document.querySelector('#cardStatus').textContent = fill(W.b_card_in, {name: %s, files: '3,931'})" % json.dumps("CARD_" + "W" * 100))
            case("a narrow phone (336): %s has no sideways scroll" % path, no_sideways(c, 336), c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    finally:
        c.desktop()


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=9820)
    ap.add_argument("--no-chrome", action="store_true", help="the words, what the screens read and the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS or p in (8791, 8792, 8799) for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="home-base-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    w = World(work, a.port)
    try:
        w.build()
        hb = group("the words", check_words, w)
        w.start()
        case("the page server is this test's own (port %d)" % w.port, a.port <= w.port < a.port + 20)
        if hb:
            group("what the screens read", check_data, w, hb)
            group("the routes", check_routes, w, hb)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the pages in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                c.init_script(STUB_JS)
                group("the home page", check_home_page, c, w)
                c.js("window.__asked = []")
                group("the Back up a card screen", check_backups_page, c, w)
                group("the Make posts screen", check_make_page, c, w)
                group("when the records can't be read", check_cant_read, c, w)
                group("phone width", check_phone, c, w)
    finally:
        w.stop()
        if w.port:
            stop_listener(w.port)
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
