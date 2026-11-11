#!/usr/bin/env python3
"""The words page (words_page.py: Nicole's v20 page for captions and hooks, served by the posting server), checked
by request and on the real page in a HIDDEN Chrome.

    python3 tests/words_page_check.py [--port 9420] [--work <a folder to keep the run in>]

What it does, on a pretend Assistant with one pretend kit it makes itself in a throwaway folder (a few tiny
pictures; nothing of a client's, nothing of the real ~/.studio, no drive):
  * her words, word for word: every word in words_page.WORDS against her own pages/words.html (handoff v20),
    when her handoff is on this computer (it is never in the repository; without it that one part says SKIP);
  * every route and every refusal: another host, another Origin, another website's page, a type that isn't JSON,
    a body too big, a kit that isn't in Your Content (a path, "..", a look-alike beside it), words for stories,
    a field the page never sends, an answer in the wrong shape; nothing is written by a refused save;
  * the record: an autosave round trip, every text held to words.py's limits, "where" never kept for a carousel,
    answers given in the chat (words.py answer) and drafts (words.py draft) showing up, picks, carry-over;
  * the posting queue step: locked until the piece is made and has its caption, her five rhythm chips the first
    time, the piece ready to post with a date, the grid-photo lines when the piece carries a cover;
  * the page itself (when there is a Chrome): the tabs, the five questions, question 3 and the hooks hidden for a
    carousel, the placeholder that follows the chip, typing saved by itself, chat answers filling in but never
    over typing, Pick and Copy, her Post it steps, the other piece's box in each of its states, and that a
    shoot's name or an answer with <, &, quotes, an accent and an emoji only ever shows as text;
  * what their words are never lost to: a save carries only what they touched (an answer the chat just gave is
    never blanked), a new draft reaches a caption box the cursor was left in, a first look that fails never
    empties "write your own", typing then leaving within the 600 ms still saves, a trial reel said in the chat
    reaches the last step, Pick keeps the keyboard's place, and a shoot named in one long unbroken piece never
    makes a phone scroll sideways.

The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import base64
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402

WINDOWS = os.name == "nt"
# A shoot named to break a careless page: an accent, an emoji, an ampersand, a quote; and, where a folder may be
# named so (not on a PC), a tag.
KIT = "2026-09-23 Zoë & the 'boys' 🌊" if WINDOWS else "2026-09-23 Zoë <b>& the 'boys' 🌊"
SHORT = KIT[11:]
PROJECT = SHORT + " reel 3"
TODAY = "2026-11-10"                      # a Tuesday; the first post lands on Wed, Nov 11
NASTY = "<img src=x onerror=\"window.pwned=1\"> & \"quotes\" 'single' Zoë 🤍 </script><script>window.pwned=2</script>"
TINY = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAASABIAAD/4QCARXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAABIAAAAAQAAAEgAAAABAAOgAQADAAAAAf//AACgAgAEAAAAAQAAABigAwAEAAAAAQAAAB4AAAAA/+0AOFBob3Rvc2hvcCAzLjAAOEJJTQQEAAAAAAAAOEJJTQQlAAAAAAAQ1B2M2Y8AsgTpgAmY7PhCfv/AABEIAB4AGAMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQIDBAUGBwgJCgv/xAC1EQACAQIEBAMEBwUEBAABAncAAQIDEQQFITEGEkFRB2FxEyIygQgUQpGhscEJIzNS8BVictEKFiQ04SXxFxgZGiYnKCkqNTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqCg4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2wBDAAICAgICAgMCAgMFAwMDBQYFBQUFBggGBgYGBggKCAgICAgICgoKCgoKCgoMDAwMDAwODg4ODg8PDw8PDw8PDw//2wBDAQIDAwQEBAcEBAcQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/3QAEAAL/2gAMAwEAAhEDEQA/APtrXr/x5b6R4r8S2Hiu+trbRdW+wwWMFeaf8J78Uv7P/tr+3737N5/leb57f67GfXPSsjxrNMPFviGET5g+33P/AKOausv743/wY06y+zwW/wDZ2ufZ/O/5+P8AR/8AlvX7rRo+wPgPbnN/8LL+If8A0MV//wCBFH/Cy/iH/wBDFf8A/gRXF0V7n1Kgc/tq5//QPiX8X7mw+Ifiux+xFfs+q38OPN3YxcN3/CvYP+Egvv8AhmT/AITr/iVZ/tX7R9h/tA+f9n/5B/8AqOn/AB8V8b/Fz/krXjP/ALDWof8ApQ9ed1+6XrewonxZ7x/wvC4/6A3/AJMUf8LwuP8AoDf+TFeD0V6ntjk9if/Z")
HOOKS = ["Moms are always the ones taking the picture. On December 4th, you're in it.",
         "Mommy & me on the beach, with your photos in time for Christmas.",
         "I'm a mom of twins... I promise your kids don't need to sit still.",
         "Let them get sandy. Let them get wet. I'll catch every single moment.",
         "You don't have to get everyone looking at the camera. Just come play.",
         "The photos you'll want framed on your wall by Christmas.",
         "<i>Your kids</i> don't have to smile. They just have to be themselves.",
         "Hold onto this season with your babies, before everything changes.",
         "5 mini session spots in Laguna on December 4th... want one? 😉",
         "One afternoon at the beach with your kids, and photos by Christmas."]
# words of hers that this file's WORDS holds in one piece where her page builds them from parts
BUILT_FROM_PARTS = ("copy_say_reel", "hooks_empty")
# In her page and, on purpose, not in ours (each named, so that anything else of hers that goes missing shows):
HERS_NOT_OURS = {
    # the top bar's name: ours is brand.bar(), the one every page of the Assistant wears
    "The Assistant", "by Horizon Found",
    # the three lines in her markup that her own header() writes over as the page loads, never seen
    "Ask me about it", "Write my words", "\u201cPolish my caption\u201d",
    "When you've told me about it, copy this into the chat. I'll write a caption and hooks from what you said, and they'll show up right here.",
    # cover lines and story lines: no words for stories, no cover lines for a carousel (Nicole, Nov 10)
    "Cover lines", "5 cover lines", "the words on the first slide", "Story lines", "5 story lines",
    "short words for your stories", "Stories", "Pick the ones you love.",
    # her patch for a carousel with no count ("Your  slides" -> "Your slides"); ours has its own honest lines
    "Your slides",
    # names her code uses, not wording
    "Content-Type", "#who button", "#purpose button", "#where button",
}
# A shoot whose name is one long piece with no space or hyphen to break at, the kind an export folder gets
LONG = "2026-09-23 2026_Henderson_Montgomery_Family_Reunion_Finals_Supercalifragilistic"
LONG_SHORT = LONG[11:]


def skip(line):
    print("SKIP  " + line, flush=True)


def her_page():
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v20-*")):
            f = h / "Carousel designer and reel picker" / "pages" / "words.html"
            if f.is_file():
                return f
    return None


def units(text):
    """A line of words as it is compared: whole, and in the pieces between its {names}; spaces evened out."""
    return {" ".join(x.split()) for x in [text] + re.split(r"\{\w+\}", text)}


def js_strings(src):
    """Every piece of text in a script's string literals: '...' and "..." whole, `...` split at each ${...}
    (what is inside a ${...} is read the same way). Comments and /regular expressions/ are stepped over."""
    out, i, n = [], 0, len(src)

    def quoted(i, q):
        buf = []
        i += 1
        while i < n and src[i] != q:
            if src[i] == "\\" and i + 1 < n:
                buf.append({"n": "\n", "t": "\t"}.get(src[i + 1], src[i + 1])); i += 2
            else:
                buf.append(src[i]); i += 1
        out.append("".join(buf))
        return i + 1

    def template(i):
        buf = []
        i += 1
        while i < n and src[i] != "`":
            if src[i] == "\\" and i + 1 < n:
                buf.append(src[i + 1]); i += 2
            elif src.startswith("${", i):
                out.append("".join(buf)); buf = []
                i = code(i + 2, True)
            else:
                buf.append(src[i]); i += 1
        out.append("".join(buf))
        return i + 1

    def code(i, inner=False):
        depth, last = 0, ""
        while i < n:
            c = src[i]
            if c in "'\"":
                i = quoted(i, c); last = "x"; continue
            if c == "`":
                i = template(i); last = "x"; continue
            if src.startswith("//", i):
                i = src.find("\n", i); i = n if i < 0 else i; continue
            if src.startswith("/*", i):
                i = src.find("*/", i); i = n if i < 0 else i + 2; continue
            if c == "/" and (last == "" or last in "(,=:[!&|?{};"):
                i += 1; cls = False
                while i < n and (cls or src[i] != "/"):
                    if src[i] == "\\": i += 1
                    elif src[i] == "[": cls = True
                    elif src[i] == "]": cls = False
                    i += 1
                i += 1; last = "x"; continue
            if inner and c == "{": depth += 1
            if inner and c == "}":
                if depth == 0: return i + 1
                depth -= 1
            if not c.isspace(): last = c
            i += 1
        return i
    code(0)
    return out


def her_strings(page, everything=False):
    """What her page can show a photographer: the text between her tags, her placeholders, and the wording in
    her script's strings (tags inside them taken out). Each as (where, text). "everything" keeps the code's own
    names too (for asking whether a word of ours is one of hers, whole)."""
    m = re.search(r"<script>(.*?)</script>", page, re.S)
    script = m.group(1)
    body = page[page.index("<body"):m.start()]
    got = []
    for t in re.split(r"<[^>]+>", body):
        got.append(("page", t))
    for t in re.findall(r'placeholder="([^"]*)"', body):
        got.append(("placeholder", t))
    for lit in js_strings(script):
        for t in re.split(r"<[^>]*>|<[^>]*$|^[^<]*>", lit) if "<" in lit or ">" in lit else [lit]:
            got.append(("script", t))
    for t in re.findall(r'alt="([^"$]+)"', script):
        got.append(("alt", t))
    out = []
    for where, t in got:
        t = " ".join(html.unescape(t).split())
        if everything:
            out.append((where, t))
            continue
        if where == "script" and not (re.search(r"[A-Za-z]{2,} [A-Za-z]", t) or re.match(r"[A-Z][a-z]", t) or re.match(r"\d+ [a-z]", t)):
            continue                     # a name the code uses (a field, a class, an address), not wording
        if len(t) >= 2 and re.search(r"[A-Za-z]", t):
            out.append((where, t))
    return out


# ---------- the pretend Assistant, its one kit, and the page server ----------

class Setup:
    def __init__(self, work, port):
        self.work, self.want = Path(work), port
        self.home = self.work / "home"
        self.studio = self.work / "studio"
        self.assistant = self.work / "The Assistant"
        self.content = self.assistant / "Your Content"
        self.kit = self.content / KIT
        self.rec = self.kit / ".kit" / "post-words.json"
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), STUDIO_HOME=str(self.studio),
                        STUDIO_TODAY=TODAY, ASSISTANT_TEST_OPEN="front", ASSISTANT_TEST_CAPCUT="1", PYTHONIOENCODING="utf-8")
        self.proc = None
        self.port = None
        self.n = 0

    def make(self):
        for d in (self.home, self.studio, self.kit / ".kit", self.kit / "Photos",
                  self.assistant / "Your Content old" / "Sneaky" / ".kit"):
            d.mkdir(parents=True, exist_ok=True)
        (self.studio / "studio.json").write_text(json.dumps({"posts": {"home": str(self.assistant)}}), encoding="utf-8")
        photos = []
        for i in range(1, 7):
            f = self.kit / "Photos" / ("beach-%03d.jpg" % i)
            f.write_bytes(TINY)
            photos.append({"n": i, "file": str(f), "w": 24, "h": 30, "way": "tall"})
        self.write_kit({"name": SHORT, "date": "2026-09-23", "folder": KIT, "picks": {"reel": [1, 2, 3, 4], "carousel": [2, 3, 5]}})
        (self.kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(self.kit / "Photos"), "photos": photos}), encoding="utf-8")
        (self.assistant / "Your Content old" / "Sneaky" / ".kit" / "kit.json").write_text(json.dumps({"name": "Sneaky"}), encoding="utf-8")

    def make_long(self):
        """A second pretend kit, named in one long unbroken piece, with its reel made and three slides."""
        kit = self.content / LONG
        for d in (kit / ".kit", kit / "Photos", kit / "Carousel"):
            d.mkdir(parents=True, exist_ok=True)
        photos = []
        for i in range(1, 4):
            f = kit / "Photos" / ("p%d.jpg" % i)
            f.write_bytes(TINY)
            photos.append({"n": i, "file": str(f), "w": 24, "h": 30, "way": "tall"})
            (kit / "Carousel" / ("Slide %02d (p%d).jpg" % (i, i))).write_bytes(TINY)
        (kit / ".kit" / "kit.json").write_text(json.dumps({
            "name": LONG_SHORT, "date": "2026-09-23", "folder": LONG, "picks": {"reel": [1, 2, 3], "carousel": [1, 2, 3]},
            "reel": {"project": LONG_SHORT + "_reel_3", "picks": [1, 2, 3], "made": "2026-11-09T10:00:00"}}), encoding="utf-8")
        (kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(kit / "Photos"), "photos": photos}), encoding="utf-8")

    def kit_rec(self):
        return json.loads((self.kit / ".kit" / "kit.json").read_text(encoding="utf-8"))

    def write_kit(self, rec):
        (self.kit / ".kit" / "kit.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    def reel_made(self):
        rec = self.kit_rec()
        rec["reel"] = {"project": PROJECT, "picks": [1, 2, 3, 4], "made": "2026-11-09T10:00:00"}
        self.write_kit(rec)

    def slides_made(self, n=3):
        (self.kit / "Carousel").mkdir(exist_ok=True)
        for i in range(1, n + 1):
            (self.kit / "Carousel" / ("Slide %02d (beach-%03d).jpg" % (i, i))).write_bytes(TINY)

    def cmd(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", env=self.env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def words(self, what, piece, given):
        """words.py answer / draft, as the chat would: what they said, from a file."""
        self.n += 1
        f = self.work / ("in%d.json" % self.n)
        f.write_text(json.dumps(given, ensure_ascii=False), encoding="utf-8")
        code, out = self.cmd("words.py", what, KIT, piece, "--file", str(f))
        if code != 0:
            raise RuntimeError("words.py %s: %s" % (what, out[-300:]))

    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=self.env)
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise RuntimeError("the page server did not start (%r)" % line)
        self.port = int(m.group(1))
        chrome_drive.wait_until(lambda: socket.create_connection(("127.0.0.1", self.port), 0.5).close() or True, 10, what="the server")
        threading.Thread(target=lambda: [None for _ in self.proc.stdout], daemon=True).start()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def q(self, piece="reel", kit=KIT):
        return "?kit=" + quote(kit, safe="") + "&piece=" + piece

    def http(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            j = json.loads(raw.decode("utf-8"))
        except ValueError:
            j = None
        return r.status, j, raw

    def state(self, piece="reel"):
        return self.http("GET", "/words-state" + self.q(piece))[1]

    def save(self, piece="reel", **given):
        return self.http("POST", "/words-save", dict({"kit": KIT, "piece": piece}, **given))

    def record(self):
        try:
            return json.loads(self.rec.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def piece(self, piece="reel"):
        return ((self.record() or {}).get("pieces") or {}).get(piece) or {}

    def rec_bytes(self):
        try:
            return self.rec.read_bytes()
        except OSError:
            return b""

    def kit_hash(self):
        return hashlib.sha256((self.kit / ".kit" / "kit.json").read_bytes()).hexdigest()

    def posting(self):
        try:
            return json.loads((self.studio / "posting.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def queue_piece(self, piece):
        return next((x for x in self.posting().get("pieces", []) if x.get("id", "").endswith("-" + piece)), None)

    def write_posting(self, p):
        tmp = self.studio / "posting.json.test"
        tmp.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(self.studio / "posting.json"))


def page_module(s):
    os.environ["STUDIO_HOME"] = str(s.studio)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    return importlib.import_module("words_page")


# ---------- 1. her words ----------

def check_words(wp):
    f = her_page()
    if f is None:
        skip("her words against her own page: her handoff (reference-private) isn't on this computer")
    else:
        raw = f.read_text(encoding="utf-8")
        t = html.unescape(raw).replace("\\'", "'")
        # ours in hers: each line of ours (each piece between its {names}) is a WHOLE piece of her wording, not
        # merely found somewhere in her file (so "Copy" can't be matched by her CSS, nor a line by half of hers)
        hers_all = {x for _, x in her_strings(raw, everything=True)}
        bad = []
        for k, v in wp.WORDS.items():
            if k in BUILT_FROM_PARTS:
                continue
            for frag in units(v) - {" ".join(v.split())} or units(v):
                if len(frag) >= 2 and frag not in hers_all:
                    bad.append((k, frag))
        case("every word in words_page.WORDS (%d) is in her words.html, word for word" % len(wp.WORDS), not bad, bad[:5])
        # hers in ours: every line her page can show is, whole, a line of ours; so one of hers that is missing
        # here, or cut short, shows. The few left out on purpose are named in HERS_NOT_OURS.
        ours = set()
        for v in list(wp.WORDS.values()) + list(wp.RHYTHMS):
            ours |= units(v)
        built = [" ".join(wp.WORDS[k].split()) for k in BUILT_FROM_PARTS]
        shown = her_strings(raw)
        missing = [x for _, x in shown if x not in ours and x not in HERS_NOT_OURS and not any(x in b for b in built)]
        case("every line her page shows (%d) is in words_page.WORDS, whole; the ones left out on purpose are named" % len(shown),
             len(shown) > 150 and not missing, missing[:5])
        case("...and nothing is named as left out that is in fact ours", not [x for x in HERS_NOT_OURS if x in ours], [x for x in HERS_NOT_OURS if x in ours])
        parts = ("When you've told me about it, copy this into the chat. I'll edit what you said into a caption and ",
                 "10 hooks", "the line on the reel\\'s first photo".replace("\\'", "'"), "), and they'll show up right here.", " show up here.")
        case("the two lines her page builds from parts are made of her parts", all(p in t for p in parts) and
             wp.WORDS["copy_say_reel"] == parts[0] + parts[1] + " (" + parts[2] + parts[3], [p for p in parts if p not in t])
        case("her five rhythm chips, as she wrote them", all(("'" + r + "'") in t for r in wp.RHYTHMS) and len(wp.RHYTHMS) == 5)
    case("her limits and her times: saved 600 ms after typing stops, a look every 2.5 s, 5 s of quiet before a fill",
         (wp.SAVE_AFTER_MS, wp.LOOK_EVERY_MS, wp.TYPING_MS) == (600, 2500, 5000))
    page = wp.page_html(KIT, "reel")
    case("no address outside this computer in the page, and no serif", not re.search(r"https?://|//fonts|googleapis|Fraunces|--display", page),
         re.findall(r"https?://\S{0,40}", page)[:3])
    case("the shoot's name is never in the page as HTML", WINDOWS or ("<b>& the" not in page and "<b>&amp; the" not in page and "Zoë &lt;b&gt;&amp; the" in page))
    case("no path in the page", str(ROOT) not in page and "/private" not in page and "Users" not in page)
    car = wp.page_html(KIT, "carousel")
    case("a carousel's page: question 3 and the hooks are hidden, and the line says a caption only",
         "id='qWhere' hidden" in car and "id='hooksPart' hidden" in car and html.escape(wp.WORDS["copy_say_carousel"]) in car
         and "id='qWhere'>" in page and "id='hooksPart'>" in page)
    if not WINDOWS:
        w = wp.page_words()
        case("on a Mac every word of hers is as she wrote it", all(w[k] == v for k, v in wp.WORDS.items()))


# ---------- 2. the routes and the refusals, without a browser ----------

def check_server(s, wp):
    port = s.port
    code, _, raw = s.http("GET", "/words.html" + s.q("reel"))
    page = raw.decode("utf-8")
    case("the page answers, with her lede", code == 200 and html.escape(wp.WORDS["lede"]) in page and "wordsData" in page, code)
    st = s.state()
    case("the state answers: an empty record, nothing made, nothing in the queue",
         st and st.get("ok") and st["w"]["caption"] == "" and st["kit"] == {"reel": "", "slides": 0, "made": False, "on_drive": st["kit"]["on_drive"]}
         and st["queue"]["status"] == "" and st["other"]["has"] is False, st)
    raw_state = json.dumps(st)
    case("no path in the state", str(s.work) not in raw_state and "Photos" not in raw_state, raw_state[:300])
    case("the reel's strip is the pickers' small copies, by number", st["strip"] and all(re.match(r"^/kit-photo\?kit=[^&/]+&n=\d+&size=s&v=", u) for u in st["strip"])
         and [int(re.search(r"&n=(\d+)", u).group(1)) for u in st["strip"]] == [1, 2, 3, 4], st["strip"])

    # words are for a reel or a carousel
    code, _, raw = s.http("GET", "/words.html" + s.q("stories"))
    case("words for stories: the page is refused, plainly", code == 200 and b"wordsData" not in raw and html.escape(wp.CANT_FIND).encode() in raw, code)
    code, j, _ = s.http("GET", "/words-state" + s.q("stories"))
    case("words for stories: no state", code == 404 and j and j["ok"] is False, (code, j))
    code, j, _ = s.save("stories", own="x")
    case("words for stories: nothing saved", code == 400 and j and j["ok"] is False and s.record() is None, (code, j))

    # a kit is a folder's name in Your Content, and nothing else
    for name, what in ((".." , "two dots"), ("../Your Content old/Sneaky", "a look-alike beside Your Content"), ("Sneaky", "a folder that isn't in Your Content"),
                       (str(s.kit), "a whole path"), ("No such shoot", "a shoot that isn't there"), ("", "no name")):
        code, j, _ = s.http("GET", "/words-state" + s.q("reel", name))
        c2, _, raw = s.http("GET", "/words.html" + s.q("reel", name))
        c3, j3, _ = s.http("POST", "/words-save", {"kit": name, "piece": "reel", "own": "x"})
        c4, j4, _ = s.http("POST", "/words-queue", {"kit": name, "piece": "reel"})
        case("%s: no state, no page, no save, no queue" % what, code == 404 and j["ok"] is False and b"wordsData" not in raw
             and c3 == 404 and j3["ok"] is False and c4 == 404 and j4["ok"] is False, (code, c2, c3, c4))
    case("nothing was written beside Your Content", not (s.assistant / "Your Content old" / "Sneaky" / ".kit" / "post-words.json").exists()
         and s.record() is None)

    # who is asking
    other = {"Host": "evil.example:%d" % port}
    case("another host gets nothing", s.http("GET", "/words-state" + s.q(), headers=other)[0] == 403
         and s.http("GET", "/words.html" + s.q(), headers=other)[0] == 403
         and s.http("POST", "/words-save", {"kit": KIT, "piece": "reel", "own": "x"}, headers=other)[0] == 403)
    for path, body in (("/words-save", {"kit": KIT, "piece": "reel", "own": "x"}), ("/words-carry", {"kit": KIT, "piece": "reel"}),
                       ("/words-rhythm", {"text": "3 a week"}), ("/words-queue", {"kit": KIT, "piece": "reel"}), ("/words-open", {"kit": KIT})):
        code, j, _ = s.http("POST", path, body, headers={"Origin": "http://evil.example"})
        c2, _, _ = s.http("POST", path, body, headers={"Origin": "http://127.0.0.1:%d" % (port + 1)})
        case("POST %s from another page's Origin: 403" % path, code == 403 and j and j["ok"] is False and c2 == 403, (code, c2))
    case("...and nothing was saved or queued by them", s.record() is None and not s.posting())
    case("a look from another website's page (cross-site): no state", s.http("GET", "/words-state" + s.q(), headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
    code, _, raw = s.http("GET", "/words.html" + s.q(), headers={"Sec-Fetch-Site": "cross-site"})
    case("a link from another website: the plain page, not this shoot's", b"wordsData" not in raw)
    case("our own page's Origin is let in", s.http("POST", "/words-save", {"kit": KIT, "piece": "reel", "own": ""},
                                                    headers={"Origin": "http://127.0.0.1:%d" % port, "Sec-Fetch-Site": "same-origin"})[0] == 200)
    case("a body that isn't JSON by its type: 415", s.http("POST", "/words-save", json.dumps({"kit": KIT, "piece": "reel", "own": "x"}).encode(),
                                                             headers={"Content-Type": "text/plain"})[0] == 415)
    case("a body that isn't JSON: 400", s.http("POST", "/words-save", b"{not json")[0] == 400)
    case("a body that is a list: 400", s.http("POST", "/words-save", b"[1,2]")[0] == 400)
    case("a body too big: 413", s.http("POST", "/words-save", {"kit": KIT, "piece": "reel", "own": "x" * 70000})[0] == 413)
    case("a route that isn't one of ours: 404", s.http("POST", "/words-delete", {"kit": KIT})[0] == 404)
    before = s.rec_bytes()
    bad = [("a field the page never sends (hooks)", dict(hooks=["mine"])), ("an unknown field", dict(path="/etc")),
           ("answers that aren't a set", dict(answers="hi")), ("an answer it doesn't know", dict(answers={"about": "x", "extra": "y"})),
           ("an answer that isn't text", dict(answers={"about": {"a": 1}})), ("a purpose that isn't a chip", dict(answers={"purpose": "sell"})),
           ("a place that isn't a chip", dict(answers={"where": "tiktok"})), ("who that isn't a list", dict(answers={"who": "new"})),
           ("picks that aren't numbers", dict(picked=["1"])), ("picks that are true/false", dict(picked=[True])),
           ("a caption that isn't text", dict(caption=["x"])), ("nothing to save", dict())]
    for what, given in bad:
        code, j, _ = s.save("reel", **given)
        case("refused, nothing saved: %s" % what, code == 400 and j and j["ok"] is False and s.rec_bytes() == before, (code, j))

    # the round trip
    kit_before = s.kit_hash()
    ans = {"about": "A mommy and me shoot in Laguna. " + NASTY, "who": ["new", "followers"], "who_text": "Moms like Zoë",
           "where": "trial", "purpose": "offer", "purpose_text": "Mini sessions on December 4th, $400", "notes": "Names: say \"Hannah and her two boys\""}
    code, j, _ = s.save("reel", answers=ans, own="My own caption 🤍")
    case("a save comes back with the piece as saved", code == 200 and j["ok"] and j["piece"]["answers"] == ans and j["piece"]["own"] == "My own caption 🤍", j)
    case("...is in the kit's words record, as text", s.piece()["answers"] == ans and s.piece()["own"] == "My own caption 🤍", s.piece())
    case("...and is what the page reads back", s.state()["w"]["answers"] == ans)
    code, j, _ = s.save("reel", answers={"about": "x" * 5000, "who_text": "y" * 900, "purpose_text": "z" * 1500, "notes": "n" * 1500},
                        own="o" * 5000, caption="c" * 5000)
    a = s.piece()["answers"]
    case("every text is held to words.py's limits (3000, 600, 1000, 1000, 4000, 4000)",
         code == 200 and [len(a["about"]), len(a["who_text"]), len(a["purpose_text"]), len(a["notes"]), len(s.piece()["own"]), len(s.piece()["caption"])]
         == [3000, 600, 1000, 1000, 4000, 4000], [len(a["about"]), len(s.piece()["own"])])
    case("a save of some answers leaves the others", a["who"] == ["new", "followers"] and a["where"] == "trial" and a["purpose"] == "offer")
    case("the version before is kept beside the record", (s.kit / ".kit" / "post-words.prev.json").is_file())
    s.save("reel", answers=ans, own="", caption="")
    code, j, _ = s.save("carousel", answers=dict(ans, about="The carousel's own"))
    case("a carousel never keeps where it's going (a reel's question)", code == 200 and "where" not in s.piece("carousel")["answers"]
         and j["piece"]["answers"]["where"] == "", s.piece("carousel"))
    case("the page never writes kit.json", s.kit_hash() == kit_before)

    # answers and drafts from the chat
    s.words("answer", "reel", {"notes": "No names", "who": ["past"]})
    st = s.state()
    case("an answer given in the chat is what the page reads next", st["w"]["answers"]["notes"] == "No names" and st["w"]["answers"]["who"] == ["past"]
         and st["w"]["answers"]["about"] == ans["about"], st["w"]["answers"])
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming!!! " + NASTY, "hooks": HOOKS})
    st = s.state()
    case("a draft from the chat: the caption and ten hooks", st["w"]["caption"].startswith("MINI SESSIONS") and st["w"]["hooks"] == HOOKS, st["w"]["hooks"][:2])
    code, j, _ = s.save("reel", picked=[5, 2, 5, 44, -1])
    case("picks are saved, each once, only for hooks that are there", code == 200 and j["piece"]["picked"] == [2, 5] and sorted(s.piece()["picked"]) == [2, 5], j)
    code, j, _ = s.save("reel", caption="MINI SESSIONS, edited on the page")
    case("an edit to the caption is saved, and the hooks and picks stay", s.piece()["caption"] == "MINI SESSIONS, edited on the page"
         and s.piece()["hooks"] == HOOKS and sorted(s.piece()["picked"]) == [2, 5])
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    case("the same hooks drafted again keep the picks", sorted(s.piece()["picked"]) == [2, 5])

    # the other piece: carry over
    s.rec.unlink()
    code, j, _ = s.http("POST", "/words-carry", {"kit": KIT, "piece": "reel"})
    case("carry over with nothing answered: says so, saves nothing", code == 200 and j["ok"] is False and j["words"] == wp.OUR_WORDS["nothing_to_carry"]
         and not s.piece("carousel"), (code, j))
    s.save("reel", answers=ans)
    code, j, _ = s.http("POST", "/words-carry", {"kit": KIT, "piece": "reel"})
    want = {k: v for k, v in ans.items() if k != "where"}
    case("carry over: the carousel has every answer but where it's going", code == 200 and j["ok"] and s.piece("carousel")["answers"] == want, s.piece("carousel"))
    case("...and the reel's own are as they were", s.piece("reel")["answers"] == ans)
    case("carry over for stories: refused", s.http("POST", "/words-carry", {"kit": KIT, "piece": "stories"})[0] == 400)
    st = s.state()
    case("the other piece isn't offered while the shoot has no carousel", st["other"] == {"piece": "carousel", "has": False, "answered": True, "caption": False, "hooks": 0}, st["other"])


def check_queue(s, wp):
    """The posting queue step: locked, her rhythm chips, ready to post with a date, and the grid photo's lines."""
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    case("a reel that isn't made can't be added (her locked line)", code == 409 and j["ok"] is False
         and j["words"] == "Once your reel is made and has its caption, add it here to see it in your feed and give it a date." and not s.posting(), (code, j))
    s.reel_made()
    s.save("reel", caption="")
    st = s.state()
    case("the reel is made: the page knows its CapCut project by name", st["kit"]["reel"] == PROJECT and st["kit"]["made"] is True, st["kit"])
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    case("a reel with no caption can't be added", code == 409 and not s.posting(), (code, j))
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    for text in ("Hourly", "", "9 a week", ["3 a week"]):
        code, j, _ = s.http("POST", "/words-rhythm", {"text": text})
        case("a rhythm that isn't one of her five chips is refused: %r" % (text,), code == 400 and not s.posting().get("interval"), (code, j))
    case("a rhythm with a field too many is refused", s.http("POST", "/words-rhythm", {"text": "3 a week", "kit": KIT})[0] == 400)
    code, j, _ = s.http("POST", "/words-rhythm", {"text": "3 a week"})
    case("3 a week: the posting queue has its rhythm", code == 200 and j["ok"] and s.posting().get("interval") == 3.0, s.posting().get("interval"))
    s.http("POST", "/words-rhythm", {"text": "Every day"})
    case("a rhythm already set is never changed from this page", s.posting().get("interval") == 3.0)
    case("the page knows a rhythm is set", s.state()["queue"]["interval"] is True)
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    x = s.queue_piece("reel") or {}
    case("Add to my queue: the reel is ready to post, with a date", code == 200 and j["ok"] and j["queue"]["status"] == "green"
         and j["queue"]["date"] == "2026-11-11" and x.get("status") == "green" and x.get("date") == "2026-11-11" and x.get("changed_by") == "words page", (j, x))
    case("the page reads it back from the queue", s.state()["queue"]["status"] == "green" and s.state()["queue"]["date"] == "2026-11-11")
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    case("added twice: still one piece, the same date", code == 200 and len([y for y in s.posting()["pieces"] if y["id"].endswith("-reel")]) == 1
         and s.queue_piece("reel")["date"] == "2026-11-11")
    case("the carousel, not made, went in beside it as not started, and can't be added", (s.queue_piece("carousel") or {}).get("status") == "red"
         and s.http("POST", "/words-queue", {"kit": KIT, "piece": "carousel"})[0] == 409 and s.queue_piece("carousel")["status"] == "red")
    case("the queue's piece holds the kit's folder, the page's state doesn't", str(s.kit) not in json.dumps(s.state()))

    # the grid photo (stage 3 puts "cover" on the piece; the page already reads it)
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-reel"):
            y["cover"] = "Photos/beach-002.jpg"
            y["thumb"] = y.get("thumb") or "posting-thumbs/x.jpg"
    s.write_posting(p)
    q = s.state()["queue"]
    case("a reel in the queue with a grid photo: the page is told, with the queue's own tile", q["cover"] is True and q["thumb"].startswith("/posting-thumbs/")
         and ":" not in q["thumb"].split("/")[-1].replace("%3A", ""), q)
    s.slides_made(3)
    s.words("draft", "carousel", {"caption": "Hannah's baby boy was just turning one..."})
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "carousel"})
    case("the carousel, made and with its caption, is added after the reel", code == 200 and j["queue"]["status"] == "green" and j["queue"]["date"] == "2026-11-13", j)
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-carousel"):
            y["cover"] = "Carousel/Slide 03 (beach-003).jpg"
    s.write_posting(p)
    q = s.state("carousel")["queue"]
    case("a carousel whose grid photo is slide 3: the page is told which slide", q["cover"] is True and q["cover_slide"] == 3, q)
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-carousel"):
            y["cover"] = "Carousel/Slide 01 (beach-001).jpg"
    s.write_posting(p)
    case("...and slide 1 needs no warning", s.state("carousel")["queue"]["cover_slide"] == 1)
    st = s.state("carousel")
    case("the carousel's strip is its slides, as the kit page shows them", len(st["strip"]) == 3 and all(u.startswith("/content/") and "/Carousel/Slide%200" in u for u in st["strip"]), st["strip"])
    case("...and each one is served", all(s.http("GET", u)[0] == 200 for u in st["strip"]))
    case("each piece now sees the other", st["other"]["has"] is True and s.state("reel")["other"] == {"piece": "carousel", "has": True, "answered": True, "caption": True, "hooks": 0}
         and st["other"]["hooks"] == 10, (st["other"], s.state("reel")["other"]))

    # the Carousel folder's button (ours)
    code, j, _ = s.http("POST", "/words-open", {"kit": KIT})
    app = "File Explorer" if WINDOWS else ("Finder" if sys.platform == "darwin" else "the file manager")
    case("Open the Carousel folder says what it did", code == 200 and j["ok"] and j["words"] == "Opened Carousel in %s." % app, j)
    case("...and takes nothing but the kit's name", s.http("POST", "/words-open", {"kit": KIT, "sub": "Photos"})[0] == 400)

    # the drive words, in the page's own function
    st_mod = wp.page_words()
    case("her carousel line names the photo drive; the page leaves those words out on the computer's own disk",
         wp.ON_DRIVE in wp.WORDS["c1"] and st_mod["on_drive"] == wp.ON_DRIVE and wp.ON_DRIVE in st_mod["c1_one"])


# ---------- 3. the page, in a hidden Chrome ----------

VAL = "document.getElementById(%s).value"
TOAST = "document.getElementById('toast').textContent"
STEPS = "Array.from(document.querySelectorAll('#todo > li')).map(function(li){ return [li.querySelector('b').textContent, li.querySelector('p').textContent]; })"


def open_page(c, s, piece, kit=KIT):
    c.open(s.url("/words.html" + s.q(piece, kit)))
    c.wait_for("document.querySelectorAll('#todo > li').length > 0", 10)


def check_page(c, s, wp):
    W = wp.page_words()

    def f(key, **more):
        t = W[key].replace("{short}", SHORT)
        for k, v in more.items():
            t = t.replace("{" + k + "}", str(v))
        return t
    # a fresh start: the reel is made, there is no carousel yet, nothing is written, nothing is queued
    for name in ("post-words.json", "post-words.prev.json"):
        if (s.kit / ".kit" / name).exists():
            (s.kit / ".kit" / name).unlink()
    for name in ("posting.json",):
        if (s.studio / name).exists():
            (s.studio / name).unlink()
    shutil.rmtree(str(s.kit / "Carousel"), ignore_errors=True)
    c.clear_errors()
    open_page(c, s, "reel")
    case("the top of the page is hers: the eyebrow, the title, the lede, the way back",
         c.text("#eyebrow") == "Your words · Reel" and c.text("#title") == SHORT + " reel words." and c.text(".lede") == W["lede"]
         and c.text("#back").strip() == "← Back to the post kit" and c.js("document.title") == SHORT + " reel · your words",
         (c.text("#eyebrow"), c.text("#title"), c.text("#back")))
    case("the way back is this kit's own page", c.js("document.getElementById('back').getAttribute('href')") == "/content/" + quote(KIT, safe="") + "/Post%20kit.html")
    case("two tabs, Reel and Carousel, and Reel is on", c.js("Array.from(document.querySelectorAll('#pieces a')).map(function(a){ return a.textContent + (a.classList.contains('on') ? '*' : ''); })") == ["Reel*", "Carousel"])
    case("the shoot's name shows as text, never as a tag", c.count("h1 b") == 0 and c.count(".line b") == 0 and c.js("window.pwned") is None)
    case("the strip holds the reel's photos", c.count("#strip img") == 4)
    case("the lines to copy name this shoot", c.text("#talkLine") == "Ask me about the %s reel" % SHORT and c.text("#copyLine") == "Write my words for the %s reel" % SHORT
         and c.text("#polishWords") == "“Polish my caption for the %s reel”" % SHORT)
    heads = c.js("Array.from(document.querySelectorAll('.q')).filter(function(q){ return !q.hidden; }).map(function(q){ return q.querySelector('b').textContent; })")
    case("five questions, with her headings", heads == [W["q_about"], W["q_who"], W["q_where"], W["q_purpose"], W["q_notes"]], heads)
    smalls = c.js("Array.from(document.querySelectorAll('.q > small')).map(function(q){ return q.textContent; })")
    case("each with her line of teaching", smalls == [W["q_about_small"], W["q_who_small"], W["q_where_small"], W["q_purpose_small"], W["q_notes_small"]])
    chips = c.js("Array.from(document.querySelectorAll('.chips button')).map(function(b){ return b.textContent; })")
    case("her chips", chips == ["New clients", "Past clients", "Everyone who follows me", "Other photographers", "On my feed", "A trial reel",
                               "Share my work", "Book more sessions", "Something coming up", "Something else"], chips)
    case("her placeholders", [c.js("document.getElementById('%s').placeholder" % i) for i in ("about", "who_text", "purpose_text", "notes", "own")]
         == [W["about_ph"], W["who_ph"], W["purpose_ph"], W["notes_ph"], W["own_ph"]])
    case("nothing written yet: both say so, and their Copy buttons wait", c.text("#capBox .empty") == W["caption_empty"] and c.text("#hooks .empty") == W["hooks_empty"]
         and c.js("document.getElementById('copyCap').disabled && document.getElementById('copyPicks').disabled && document.getElementById('copyOwn').disabled"))
    steps = c.js(STEPS)
    want = [[W["r1_h"], f("r1", project=" (" + PROJECT + ")")], [W["r2_h"], W["r2"]], [W["cap_h"], W["cap"]],
            [W["q_h"], "Once your reel is made and has its caption, add it here to see it in your feed and give it a date."], [W["r5_h"], W["r5"]]]
    case("Post it: her five steps for a reel, with the CapCut project's name", steps == want, steps)
    case("the queue step is locked until there is a caption", c.js("document.getElementById('addQueue').disabled") is True)
    case("no carousel from this shoot: the other piece's box isn't shown", c.js("document.getElementById('other').hidden") is True)
    c.click("#copyHook")
    case("Copy my hook with nothing picked: 'Pick one above first'", c.wait_for(TOAST + " === 'Pick one above first'", 3))
    c.click("#copyCap2")
    case("Copy caption with nothing written: says so", c.wait_for(TOAST + " === \"Your caption isn't written yet\"", 3))

    # typing saves by itself
    c.click("#about")
    c.type_text("It was Hannah & her 2 boys <3 ")
    c.js("document.execCommand('insertText', false, %s)" % json.dumps("Zoë 🤍 \"quoted\""))
    t0 = time.time()
    c.wait_for("document.getElementById('saved').textContent === 'Saved ✓'", 5)
    typed = "It was Hannah & her 2 boys <3 Zoë 🤍 \"quoted\""
    case("typing is saved by itself (Saved ✓), as text", s.piece()["answers"]["about"] == typed, s.piece())
    case("...about 600 ms after the last key, not on every key", 0.3 <= time.time() - t0 <= 3.0, time.time() - t0)
    case("the save carried that answer and no other", sorted(s.piece()["answers"]) == ["about"], sorted(s.piece()["answers"]))
    c.click("#who button", nth=0)
    c.click("#who button", nth=2)
    c.click("#where button", nth=1)
    c.wait_for("document.getElementById('saved').textContent === 'Saved ✓'", 5)
    chrome_drive.wait_until(lambda: s.piece()["answers"].get("where") == "trial", 5, what="the chips saved")
    case("chips: more than one for who, one for where", s.piece()["answers"]["who"] == ["new", "followers"] and s.piece()["answers"]["where"] == "trial"
         and c.js("Array.from(document.querySelectorAll('.chips button.on')).map(function(b){ return b.textContent; })") == ["New clients", "Everyone who follows me", "A trial reel"])
    case("a trial reel: the last step says to turn on Trial reel", c.js(STEPS)[4][1] == W["r5_trial"], c.js(STEPS)[4])
    c.click("#purpose button", nth=2)
    case("Something coming up: the box under it asks what's coming up", c.js("document.getElementById('purpose_text').placeholder") == W["purpose_ph_offer"])
    c.click("#purpose button", nth=1)
    case("Book more sessions: it asks what kind", c.js("document.getElementById('purpose_text').placeholder") == W["purpose_ph_book"])
    c.click("#purpose button", nth=1)
    case("the chip pressed again is off, and the box says the plain line", c.js("document.getElementById('purpose_text').placeholder") == W["purpose_ph"]
         and c.count("#purpose button.on") == 0)
    c.click("#purpose button", nth=2)
    c.wait_for("document.getElementById('saved').textContent === 'Saved ✓'", 5)
    chrome_drive.wait_until(lambda: s.piece()["answers"].get("purpose") == "offer", 5, what="the purpose saved")

    # typing is never overwritten; an answer from the chat fills in once they've stopped
    c.click("#notes")
    c.type_text("my own note")
    t_key = time.time()
    c.wait_for("document.getElementById('saved').textContent === 'Saved ✓'", 5)
    chrome_drive.wait_until(lambda: s.piece()["answers"].get("notes") == "my own note", 5, what="the note saved")
    s.words("answer", "reel", {"notes": "Names: say Hannah and her two boys", "who_text": NASTY})
    time.sleep(max(0.0, 3.8 - (time.time() - t_key)))        # past one look (2.5 s), within 5 s of the last key
    case("an answer from the chat within 5 s of their last key: what they typed stays", c.js(VAL % "'notes'") == "my own note", c.js(VAL % "'notes'"))
    got = c.wait_for(VAL % "'notes'" + " === 'Names: say Hannah and her two boys'", 8)
    case("...and fills in by itself once they've stopped typing", bool(got) and 4.8 <= time.time() - t_key <= 11, time.time() - t_key)
    case("an answer with tags and quotes in it fills the box as text", c.js(VAL % "'who_text'") == NASTY and c.js("window.pwned") is None)
    case("the chat's answer was not saved over by the page", s.piece()["answers"]["notes"] == "Names: say Hannah and her two boys")

    # the drafts arrive
    t0 = time.time()
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming!!! " + NASTY, "hooks": HOOKS})
    c.wait_for("document.querySelectorAll('#hooks .hook').length === 10 && !!document.getElementById('caption')", 6)
    case("a draft from the chat shows up within a look (2.5 s)", time.time() - t0 <= 4.5, time.time() - t0)
    case("the caption is in its box, as text", c.js(VAL % "'caption'") == "MINI SESSIONS are coming!!! " + NASTY and c.js("window.pwned") is None)
    rows = c.js("Array.from(document.querySelectorAll('#hooks .hook')).map(function(r){ return [r.querySelector('.n').textContent, r.querySelector('.t').textContent, r.querySelector('.pk').textContent, r.querySelector('.cp').textContent]; })")
    case("ten hooks, each with its number, Pick and Copy", rows == [[str(i + 1), h, "Pick", "Copy"] for i, h in enumerate(HOOKS)], rows[:2])
    case("a hook with a tag in it shows as text", c.count("#hooks i") == 0)
    case("the steps follow: the queue step is ready, with Add to my queue", c.js(STEPS)[3][1] == W["q_ready"] and c.js("document.getElementById('addQueue').disabled") is False)
    c.click("#hooks .pk", nth=5)
    c.wait_for("document.querySelectorAll('#hooks .hook.on').length === 1", 3)
    chrome_drive.wait_until(lambda: s.piece().get("picked") == [5], 5, what="the pick saved")
    case("Pick becomes ✓ Picked, the row is outlined, and the pick is saved", c.text("#hooks .hook.on .pk") == "✓ Picked" and c.text("#hooks .hook.on .n") == "6" and s.piece()["picked"] == [5])
    c.click("#hooks .pk", nth=1)
    chrome_drive.wait_until(lambda: s.piece().get("picked") == [1, 5], 5, what="the second pick saved")
    c.click("#hooks .cp", nth=8)
    c.wait_for(TOAST + " !== 'Pick one above first' && " + TOAST + " !== \"Your caption isn't written yet\"", 3)
    copied_ok = c.js(TOAST) == "Copied that one"
    case("Copy on a hook copies that hook", c.js("window.wordsLastCopied") == HOOKS[8] and c.js(TOAST) in ("Copied that one", W["copy_failed"]), c.js(TOAST))
    if copied_ok:
        case("the page's own copy worked from a press (the way the Claude app's pane allows)", True)
    else:
        skip("the page's own copy from a press: this Chrome refused it (the page said to select and copy)")
    c.click("#copyPicks")
    case("Copy my picks copies the picked hooks, one to a line", c.wait_for("window.wordsLastCopied === %s" % json.dumps(HOOKS[1] + "\n" + HOOKS[5]), 3))
    c.click("#copyHook")
    case("Copy my hook copies the first one picked", c.wait_for("window.wordsLastCopied === %s" % json.dumps(HOOKS[1]), 3))
    c.click("#talkBtn")
    case("the three lines for the chat copy as written", c.wait_for("window.wordsLastCopied === %s" % json.dumps("Ask me about the %s reel" % SHORT), 3)
         and (c.click("#copyBtn") and c.wait_for("window.wordsLastCopied === %s" % json.dumps("Write my words for the %s reel" % SHORT), 3))
         and (c.click("#copyPolish") and c.wait_for("window.wordsLastCopied === %s" % json.dumps("Polish my caption for the %s reel" % SHORT), 3)))
    c.click("#hooks .pk", nth=1)
    chrome_drive.wait_until(lambda: s.piece().get("picked") == [5], 5, what="the pick taken back")
    case("✓ Picked pressed again takes the pick back", c.count("#hooks .hook.on") == 1)

    # an edit to the caption, and their own
    c.click("#caption")
    c.js("(function(t){ t.focus(); t.select(); })(document.getElementById('caption'))")
    c.type_text("MINI SESSIONS are coming to Laguna Beach!!!")
    chrome_drive.wait_until(lambda: s.piece().get("caption") == "MINI SESSIONS are coming to Laguna Beach!!!", 6, what="the caption saved")
    case("an edit to the caption saves by itself", s.piece()["caption"] == "MINI SESSIONS are coming to Laguna Beach!!!" and s.piece()["hooks"] == HOOKS)
    time.sleep(3.0)
    case("...and a look just after doesn't put the older caption back", c.js(VAL % "'caption'") == "MINI SESSIONS are coming to Laguna Beach!!!")
    c.click("#copyCap")
    case("Copy caption copies it as it reads now", c.wait_for("window.wordsLastCopied === 'MINI SESSIONS are coming to Laguna Beach!!!'", 3))
    c.click("#own")
    c.type_text("My own words")
    chrome_drive.wait_until(lambda: s.piece().get("own") == "My own words", 6, what="their own caption saved")
    case("write your own: saved by itself, and Copy my caption wakes up", s.piece()["own"] == "My own words" and c.js("document.getElementById('copyOwn').disabled") is False)

    # the posting queue step: her chips the first time
    c.click("#addQueue")
    c.wait_for("document.querySelectorAll('[data-iv]').length === 5", 3)
    case("Add to my queue, the first time: 'How often do you want to post?' and her five chips", c.text("#qArea b") == "How often do you want to post?"
         and c.js("Array.from(document.querySelectorAll('[data-iv]')).map(function(b){ return b.textContent; })") == list(wp.RHYTHMS))
    time.sleep(3.2)
    case("the chips stay while the page looks again", c.count("[data-iv]") == 5 and not s.posting())
    c.click("[data-iv]", nth=2)
    c.wait_for("!!document.getElementById('seeFeed')", 8)
    case("3 a week: it's added, and the step says the day", c.js(STEPS)[3][1] == "It's in your queue, down for Wed, Nov 11. See how it looks in your grid before you post.", c.js(STEPS)[3])
    case("...with 'See it in my feed →' to the posting queue", c.text("#seeFeed") == "See it in my feed →" and c.js("document.getElementById('seeFeed').getAttribute('href')") == "/posting.html")
    case("...and the queue holds it, ready to post", (s.queue_piece("reel") or {}).get("status") == "green" and s.posting().get("interval") == 3.0)
    case("the posting queue page opens from there", s.http("GET", "/posting.html")[0] == 200)

    # the other piece: appears when the shoot has a carousel
    s.slides_made(3)
    c.wait_for("!document.getElementById('other').hidden", 6)
    case("a carousel is made: the box offers a version for it, in her words",
         c.text("#otherHead") == "Make a version for your carousel?" and c.text("#otherSay") == f("o_make", other="carousel")
         and c.text("#otherYes") == "Yes, make the carousel version", (c.text("#otherHead"), c.text("#otherSay")))
    c.click("#otherYes")
    c.wait_for("!!document.getElementById('otherLine')", 6)
    case("Yes: the answers are carried over, without where it's going", {k: v for k, v in s.piece("reel")["answers"].items() if k != "where"} == s.piece("carousel")["answers"]
         and s.piece("carousel")["answers"]["about"] == typed, s.piece("carousel"))
    case("...and the box gives the line to copy and the way there", c.text("#otherHead") == "Your carousel is waiting for its words"
         and c.text("#otherSay") == f("o_waiting", other="carousel") and c.text("#otherLine") == "Write my words for the %s carousel" % SHORT
         and c.text("#otherGo") == "Go to the carousel words →")
    c.click("#otherCopy")
    case("its Copy copies the carousel's line", c.wait_for("window.wordsLastCopied === %s" % json.dumps("Write my words for the %s carousel" % SHORT), 3))
    s.words("draft", "carousel", {"caption": "Hannah's baby boy was just turning one..."})
    c.wait_for("document.getElementById('otherHead').textContent === 'Your carousel words are ready too'", 6)
    case("the carousel's words are written: the box says so", c.text("#otherSay") == "You already have a caption for the %s carousel." % SHORT
         and c.text("#otherGo") == "Go to the carousel words →" and c.count("#otherYes") == 0)

    # the grid photo, when the queue's piece carries one
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-reel"):
            y["cover"] = "Photos/beach-002.jpg"
    s.write_posting(p)
    c.wait_for(STEPS + "[4][1].indexOf('Edit cover') > 0", 6)
    case("a grid photo picked in the queue: the last step says to set it as the cover", c.js(STEPS)[4][1] == W["r5_trial"] + W["r5_cover"], c.js(STEPS)[4])
    if (s.queue_piece("reel") or {}).get("thumb"):
        case("...and shows the queue's own tile, small", c.count("#todo img.coverpic") == 1 and c.js("document.querySelector('#todo img.coverpic').alt") == "Your cover photo")
    else:
        skip("the cover's small picture: this computer made no tile for the queue (no sips, no Pillow)")
    errs = [e for e in c.page_errors() if "favicon" not in e]
    case("no errors on the reel's page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])
    try:
        c.screenshot("words-reel.png", full=True)
    except Exception:  # noqa: BLE001  (a picture for a person to look at; never a failure)
        pass

    # the carousel's page
    c.clear_errors()
    c.click("#otherGo")
    c.wait_for("document.body.dataset.piece === 'carousel' && document.querySelectorAll('#todo > li').length > 0", 10)
    case("Go to the carousel words: the carousel's page", c.text("#eyebrow") == "Your words · Carousel" and c.text("#title") == SHORT + " carousel words."
         and c.js("Array.from(document.querySelectorAll('#pieces a')).map(function(a){ return a.textContent + (a.classList.contains('on') ? '*' : ''); })") == ["Reel", "Carousel*"])
    case("question 3 (where is this reel going) is hidden", c.js("document.getElementById('qWhere').hidden") is True
         and c.js("getComputedStyle(document.getElementById('qWhere')).display") == "none")
    case("the hooks are hidden, and the line says a caption only", c.js("getComputedStyle(document.getElementById('hooksPart')).display") == "none"
         and c.text("#copySay") == W["copy_say_carousel"] and c.text("#copyLine") == "Write my words for the %s carousel" % SHORT)
    case("the carried answers are in the boxes", c.js(VAL % "'about'") == typed and c.js(VAL % "'who_text'") == NASTY)
    case("the strip holds the slides, a little wider", c.count("#strip.wide img") == 3)
    c.wait_for("Array.from(document.querySelectorAll('#strip img')).every(function(i){ return i.complete && i.naturalWidth > 0; })", 8)
    steps = c.js(STEPS)
    on_drive = s.state("carousel")["kit"]["on_drive"]
    c1 = f("c1", n=3) if on_drive else f("c1", n=3).replace(wp.ON_DRIVE, "")
    want = [[W["c1_h"], c1], [W["cap_h"], W["cap"]], [W["q_h"], W["q_ready"]], [W["r5_h"], W["c4"]]]
    case("Post it: her four steps for a carousel", steps == want, steps)
    case("where the slides are is never said of a drive they aren't on", on_drive or "photo drive" not in steps[0][1])
    c.click("#openCarousel")
    c.wait_for("document.getElementById('openWent').textContent !== ''", 5)
    case("the Carousel folder it names has its button beside it, and says what it did", c.text("#openCarousel") == "Open the Carousel folder"
         and c.text("#openWent").startswith("Opened Carousel in "), c.text("#openWent"))
    case("the other piece: the reel's words are ready too, with its ten hooks", c.text("#otherHead") == "Your reel words are ready too"
         and c.text("#otherSay") == "You already have a caption and 10 hooks for the %s reel." % SHORT and c.text("#otherGo") == "Go to the reel words →")
    c.click("#addQueue")
    c.wait_for("!!document.getElementById('seeFeed')", 8)
    case("Add to my queue a second time asks nothing: no chips, straight in", c.count("[data-iv]") == 0
         and c.js(STEPS)[2][1] == "It's in your queue, down for Fri, Nov 13. See how it looks in your grid before you post.", c.js(STEPS)[2])
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-carousel"):
            y["cover"] = "Carousel/Slide 03 (beach-003).jpg"
    s.write_posting(p)
    c.wait_for(STEPS + "[3][1].indexOf('slide 3') > 0", 6)
    case("a grid photo that isn't slide 1: her warning, naming the slide", c.js(STEPS)[3][1] == W["c4"] + f("c4_cover", n=3), c.js(STEPS)[3])
    errs = [e for e in c.page_errors() if "favicon" not in e]
    case("no errors on the carousel's page", not errs, errs[:3])
    case("nothing asked of the internet there either", not c.outside_requests(), c.outside_requests()[:3])
    case("nothing of theirs ever ran as a script", c.js("window.pwned") is None)
    try:
        c.screenshot("words-carousel.png", full=True)
    except Exception:  # noqa: BLE001
        pass

    # a save that can't land says so, in her words
    c.click("#notes")
    s.stop()
    c.type_text(" more")
    got = c.wait_for("document.getElementById('saved').textContent !== ''", 6)
    case("the Assistant can't be reached: 'Not saved. Is the photo drive plugged in?'", c.text("#saved") == W["not_saved"], got)
    s.start_again()


def check_sturdy(s):
    """A posting queue file that is JSON but not a queue must not take the words page down."""
    f = s.studio / "posting.json"
    was = f.read_bytes() if f.exists() else None
    try:
        f.write_text("[]", encoding="utf-8")
        code, j, _ = s.http("GET", "/words-state" + s.q("reel"))
        case("a posting queue file that isn't a queue (a list): the page still gets its answers, the queue reads as empty",
             code == 200 and bool(j) and j.get("ok") is True and j["queue"]["status"] == "" and j["queue"]["interval"] is False, (code, j and j.get("ok")))
    finally:
        if was is None:
            f.unlink()
        else:
            f.write_bytes(was)


SENT = "window.__sent.filter(function(x){ return x[0] === '/words-save'; }).map(function(x){ return x[1]; })"
WATCH = ("window.__sent = []; (function(){ var f = window.fetch; window.fetch = function(u, o){"
         " if (o && o.body) window.__sent.push([String(u), JSON.parse(o.body)]); return f.apply(this, arguments); }; })()")
FAIL_FIRST_LOOK = ("(function(){ var f = window.fetch, n = 0; window.fetch = function(u, o){"
                   " if (String(u).indexOf('/words-state') === 0 && n++ === 0) return Promise.resolve(new Response('{\"ok\":false}', {status: 500}));"
                   " return f.apply(this, arguments); }; })()")
ON = "Array.from(document.querySelectorAll('.chips button.on')).map(function(b){ return b.textContent; })"
PK = "(function(){ var b = document.querySelectorAll('#hooks .pk')[%d]; return [document.activeElement === b, b.textContent, b.getAttribute('aria-pressed'), b.parentNode.classList.contains('on')]; })()"


def check_kept(c, s, wp):
    """What their words are never lost to (the fix round, Nov 10). Each case here failed on the page as first built."""
    W = wp.page_words()

    def seen(condition, seconds):          # a wait that says no rather than stopping the rest of these cases
        try:
            return bool(c.wait_for(condition, seconds))
        except Exception:  # noqa: BLE001
            return False

    def landed(fn, seconds):
        try:
            return bool(chrome_drive.wait_until(fn, seconds, what="the save"))
        except Exception:  # noqa: BLE001
            return False
    for name in ("post-words.json", "post-words.prev.json"):
        if (s.kit / ".kit" / name).exists():
            (s.kit / ".kit" / name).unlink()
    c.clear_errors()
    open_page(c, s, "reel")
    c.js(WATCH)

    # 1. a save carries only what they touched
    c.click("#notes")
    c.type_text("n")
    landed(lambda: s.piece().get("answers", {}).get("notes") == "n", 5)
    s.words("answer", "reel", {"about": "From the chat", "who": ["past"], "purpose": "book", "purpose_text": "Minis in May"})
    c.type_text("o names please")                # at once: the page has not shown the chat's answers yet
    landed(lambda: s.piece()["answers"].get("notes") == "no names please", 5)
    a = s.piece()["answers"]
    case("typing in one box saves that box: answers the chat gave a moment before are still there",
         (a.get("about"), a.get("who"), a.get("purpose"), a.get("purpose_text")) == ("From the chat", ["past"], "book", "Minis in May"), a)
    sent = c.js(SENT)
    case("each save from the page carried only what they touched", len(sent) >= 2 and all(sorted(b) == ["answers", "kit", "piece"] and list(b["answers"]) == ["notes"] for b in sent), sent)
    got = seen(VAL % "'about'" + " === 'From the chat'", 9)
    case("...and the chat's answers fill in once they've stopped typing", bool(got) and c.js(ON) == ["Past clients", "Book more sessions"]
         and c.js(VAL % "'purpose_text'") == "Minis in May" and c.js(VAL % "'notes'") == "no names please", c.js(ON))
    c.click("#who button", nth=0)
    landed(lambda: s.piece()["answers"].get("who") == ["past", "new"], 5)
    sent = c.js(SENT)
    case("a chip sends its own answer and no other", sorted(sent[-1]) == ["answers", "kit", "piece"] and list(sent[-1]["answers"]) == ["who"]
         and s.piece()["answers"]["about"] == "From the chat", sent[-1])

    # 2. Pick: the keyboard stays on the button pressed, and the pick goes alone
    s.words("draft", "reel", {"caption": "First caption", "hooks": HOOKS})
    seen("document.querySelectorAll('#hooks .hook').length === 10 && !!document.getElementById('caption')", 6)
    c.js("window.__sent.length = 0")
    c.click("#hooks .pk", nth=5)
    landed(lambda: s.piece().get("picked") == [5], 5)
    case("Pick: the keyboard stays on the button pressed, and it now says \u2713 Picked (pressed)", c.js(PK % 5) == [True, "\u2713 Picked", "true", True], c.js(PK % 5))
    case("...Copy my picks wakes up, and the pick was sent alone", c.js("document.getElementById('copyPicks').disabled") is False
         and c.js(SENT) == [{"kit": KIT, "piece": "reel", "picked": [5]}], c.js(SENT))
    c.js("document.querySelectorAll('#hooks .pk')[7].focus()")
    s.words("draft", "reel", {"hooks": HOOKS[::-1]})
    seen("document.querySelector('#hooks .hook .t').textContent === %s" % json.dumps(HOOKS[-1]), 6)
    case("new hooks from the chat: the rows are made again and the keyboard keeps its place among them",
         c.js("document.activeElement === document.querySelectorAll('#hooks .pk')[7]") is True, c.js("document.activeElement.tagName"))

    # 3. a new draft reaches the caption box even with the cursor left in it; an edit of theirs is never written over
    c.click("#caption")
    s.words("draft", "reel", {"caption": "SECOND caption from the chat"})
    got = seen(VAL % "'caption'" + " === 'SECOND caption from the chat'", 7)
    case("the cursor left in the caption box: a new draft from the chat still shows, and the cursor stays in the box",
         bool(got) and c.js("document.activeElement.id") == "caption", c.js(VAL % "'caption'"))
    c.click("#copyCap")
    case("...and Copy caption copies the new one", seen("window.wordsLastCopied === 'SECOND caption from the chat'", 3))
    c.js("(function(t){ t.focus(); t.setSelectionRange(t.value.length, t.value.length); })(document.getElementById('caption'))")
    c.type_text("!")
    t_key = time.time()
    landed(lambda: s.piece().get("caption") == "SECOND caption from the chat!", 5)
    s.words("draft", "reel", {"caption": "THIRD caption"})
    time.sleep(max(0.0, 3.8 - (time.time() - t_key)))        # past one look, within 5 s of their last key
    case("a draft arriving within 5 s of their last key in the caption: what they typed stays", c.js(VAL % "'caption'") == "SECOND caption from the chat!", c.js(VAL % "'caption'"))
    case("...and it goes in once they've stopped", bool(seen(VAL % "'caption'" + " === 'THIRD caption'", 8)) and s.piece()["caption"] == "THIRD caption")

    # 4. where the reel is going, said in the chat, reaches the last step
    steps5 = STEPS + "[4][1]"
    case("before: the last step is the plain one", c.js(steps5).startswith(W["r5"]), c.js(steps5))
    s.words("answer", "reel", {"where": "trial"})
    got = seen(steps5 + ".indexOf(%s) === 0" % json.dumps(W["r5_trial"]), 10)
    case("a trial reel, said in the chat: the chip lights and the last step says to turn on Trial reel", bool(got) and "A trial reel" in c.js(ON), c.js(steps5))
    s.words("answer", "reel", {"where": "feed"})
    got = seen(steps5 + ".indexOf(%s) === 0" % json.dumps(W["r5"]), 10)
    case("...and back to the feed in the chat: the plain step again", bool(got) and "On my feed" in c.js(ON), c.js(steps5))

    # 5. typing, then leaving inside the 600 ms
    c.js("(function(t){ t.focus(); t.setSelectionRange(t.value.length, t.value.length); })(document.getElementById('notes'))")
    c.type_text(" typed just before leaving")
    c.click("#pieces a", nth=1)
    landed(lambda: s.piece()["answers"].get("notes") == "no names please typed just before leaving", 4)
    case("an answer typed just before clicking the Carousel tab is saved as they go", s.piece()["answers"].get("notes") == "no names please typed just before leaving", s.piece()["answers"].get("notes"))
    seen("document.body.dataset.piece === 'carousel' && document.querySelectorAll('#todo > li').length > 0", 10)
    open_page(c, s, "reel")
    seen("!!document.getElementById('caption')", 6)
    c.js("(function(t){ t.focus(); t.setSelectionRange(t.value.length, t.value.length); })(document.getElementById('caption'))")
    c.type_text(" EDITED")
    c.click("#pieces a", nth=1)
    landed(lambda: s.piece().get("caption") == "THIRD caption EDITED", 4)
    case("...and so is an edit to the caption", s.piece().get("caption") == "THIRD caption EDITED", s.piece().get("caption"))
    seen("document.body.dataset.piece === 'carousel' && document.querySelectorAll('#todo > li').length > 0", 10)

    # 6. the first look fails: "write your own" is still filled by the look that works, and never wiped
    code, _, _ = s.save("reel", own="MY OWN CAPTION, written last week")
    ident = c.init_script(FAIL_FIRST_LOOK)
    try:
        open_page(c, s, "reel")
    finally:
        c.drop_init_script(ident)
    case("the page's first look failed: the next one fills their own caption in all the same", code == 200
         and c.js(VAL % "'own'") == "MY OWN CAPTION, written last week" and c.js("document.getElementById('copyOwn').disabled") is False
         and c.js(VAL % "'about'") == "From the chat", c.js(VAL % "'own'"))
    c.js("(function(t){ t.focus(); t.setSelectionRange(t.value.length, t.value.length); })(document.getElementById('notes'))")
    c.type_text(".")
    landed(lambda: s.piece()["answers"].get("notes", "").endswith("leaving."), 5)
    case("...and typing in another box afterwards leaves their own caption as it was", s.piece().get("own") == "MY OWN CAPTION, written last week", s.piece().get("own"))
    errs = [e for e in c.page_errors() if "favicon" not in e and "500" not in e]
    case("no errors on the page through all of that", not errs, errs[:3])


def check_phone(c, s):
    s.make_long()
    c.phone()
    try:
        for kit, what in ((KIT, ""), (LONG, ", a shoot named in one long unbroken piece")):
            for piece in ("reel", "carousel"):
                open_page(c, s, piece, kit)
                wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
                case("phone width, the %s's page%s: no sideways scroll" % (piece, what), wide[0] <= 0 and wide[1] == 390, wide)
        if LONG_SHORT not in c.text("#todo"):
            case("the long name is on the page it was tried on", False, c.text("#todo")[:200])
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
    ap.add_argument("--port", type=int, default=9420)
    ap.add_argument("--no-chrome", action="store_true", help="the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 20)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="words-page-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = Setup(work, a.port)
    s.make()
    wp = page_module(s)
    try:
        group("her words", check_words, wp)
        s.start()
        s.start_again = s.start
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 20)
        group("the routes", check_server, s, wp)
        group("the posting queue step", check_queue, s, wp)
        group("a queue file that isn't one", check_sturdy, s)
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page", check_page, c, s, wp)
                group("their words are kept", check_kept, c, s, wp)
                group("phone width", check_phone, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
