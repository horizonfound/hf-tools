#!/usr/bin/env python3
"""The talking reel page (talking_page.py: Nicole's handoff v24, pages/talking-reel.html, served by the posting
server), checked by request and on the real page in a HIDDEN Chrome.

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py [--only s1|script|preview|words] [--no-chrome] [--port 9620] [--work <folder>]

Run it under the memory guard, ONE such test at a time (it drives a hidden Chrome and plays a tiny video). The
limit is 3000 MB, as for the other tests that drive a Chrome: the guard counts a Chrome's shared memory once per
helper, so a hidden Chrome alone reads about 1 GB (--no-chrome stays under 800).

Parts (one per sub-stage of the page; the later ones are added as they are built):
  words   her words, both ways: every line her page, her engine and her server can show a photographer is in
          talking_page.WORDS (or named in HERS_NOT_OURS with why), and every line in WORDS is found in her files
          (SKIP when her handoff is not on this computer; it is never in the repository). No "Claude" in any word.
  s1      the page's structure, every route and every refusal by request, the state and its short answer, then
          step 1 on the real page: Add my video, the videos, Edit my video (the video already edited, another
          video with the question on the page, a video with no script yet), the status line in each state, who
          places the photos, the three lines to copy and when each shows, the refresh and its pauses, Undo's
          lists and the chat (two edits in the same moment, a save or an Undo that does not get through, a part
          of the page that fails, answers that cross, a copy into the folder that was cut off), names and words with <b>, quotes and an emoji showing as text, no path anywhere,
          nothing asked of the internet, phone width, no page errors.

  script  sub-stage C2 (tests/talking_page_script.py holds it): the sentences, a click on a word, the highlight
          bar and each of its buttons, the Move row, the bars above the words, dragging a bar, a bar's menu, the
          photo picker and the video picker; her pitfalls and the layouts she turned down, each with its check.
          The video picker has the Mac get two 3-second Footage videos ready (a few stills each).

  preview sub-stage C3 (tests/talking_page_preview.py holds it): playing the cut and the whole, every spot with her
          numbers (the same ones CapCut gets), dragging and sizing a photo, themselves in the corner and the
          caption, the zooms, the captions, a Footage video kept in step, the phone guides, step 3's chips.

What it never does: touch the real ~/.studio (STUDIO_HOME is the scratch folder; the real one is listed before
and after), build or start the real transcriber (TALKING_TRANSCRIBER=pretend, TALKING_NO_REAL=1), open a folder
(ASSISTANT_TEST_OPEN), or make a talking video's small copy: the one "talking video" is
tests/fixtures/loud-tone-3s.mp4 (3 seconds, self-made), and its small copy is put in place by the test, so no job
here ever asks the Mac to make one. (The `script` part does have the Mac read stills from two Footage videos, both
that same 3-second file.)
The page server (port 9620 up) and the hidden Chrome are this test's own and are stopped at the end.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only.
"""
import argparse
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
from urllib.parse import quote, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKILLS = ROOT / "plugins" / "the-engine" / "skills"
SCRIPTS = SKILLS / "studio-manager" / "scripts"
REEL = SKILLS / "assistant-make-a-reel" / "scripts"
FIXTURE = HERE / "fixtures" / "loud-tone-3s.mp4"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import words_page_check as wpc  # noqa: E402   (its tiny picture, and how her page's lines are pulled out)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

WINDOWS = os.name == "nt"
MAC = sys.platform == "darwin"
PORT = 9620
# Names made to break a careless page: an accent, an emoji, an ampersand, quotes; and, where a file may be named
# so (not on a PC), a tag.
KIT = "2026-09-23 Zoë & the 'boys' 🌊" if WINDOWS else "2026-09-23 Zoë <b>& the 'boys' 🌊"
SHORT = KIT[11:]
V1 = "my talk & 'é' 🎤.mp4" if WINDOWS else "my <b>talk<i> & 'é' \"q\" 🎤.mp4"
V2 = "second take.mp4"
ROUTES_KIT = "2026-09-22 Routes"
EMPTY_KIT = "2026-10-01 Nothing yet"
NO_SHEET = "2026-10-02 No sheet"
LONG_KIT = "2026-10-03 A long talk"
SAID = ["OK", "so", "<b>bold</b>", "\"quoted\"", "🌊", "we", "were", "at", "the", "beach.", "It", "was", "awesome."]
WORDS1 = [{"w": w, "start": round(0.1 + i * 0.2, 3), "end": round(0.25 + i * 0.2, 3), "conf": 0.9} for i, w in enumerate(SAID)]
SAID2 = "And this is the second take of it.".split()
WORDS2 = [{"w": w, "start": round(0.1 + i * 0.3, 3), "end": round(0.3 + i * 0.3, 3), "conf": 0.9} for i, w in enumerate(SAID2)]
HERS24 = None
for _base in (ROOT, ROOT.parent / "hf-tools"):
    _h = _base / "reference-private" / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker"
    if (_h / "pages" / "talking-reel.html").is_file():
        HERS24 = _h
        break

# In her page and, on purpose, not in ours; each with why, so that anything else of hers that goes missing shows.
HERS_NOT_OURS = {
    "The Assistant": "the top bar's name: ours is brand.bar(), the one every page of the Assistant wears",
    "by Horizon Found": "the same",
    "Your talking reel": "her markup's title, written over by her own script as the page loads; ours is right from the start",
    "Cut my talking reel": "her markup's line, written over at once with the shoot's name",
    "Place the photos in my talking reel": "the placeholder her script writes over at once (the plan, section 4)",
    "Drag to scrub · click a clip to pick it · spacebar plays and pauses · zoom in to see your words":
        "the first-paint hint, replaced at once by her script (the plan, section 4)",
    "Photo moved. Undo puts it back.": "dead code in her page (the photo strip she turned down)",
    "In CapCut: Remove background on your clip": "dead code (the tag on the screen)",
    "Across top": "dead code (the spot she removed, Nov 12)",
    "The Assistant's transcriber isn't on this Mac yet.": "a state ours cannot reach: ours builds it, and says so in its own lines",
    "I can't find the Assistant's reel maker on this Mac.": "a state ours cannot reach",
    # names her code uses, not wording
    "Content-Type": "a name in her code", "Escape": "a key's name", "Space": "a key's name", "Delete": "a key's name",
    "Backspace": "a key's name",
}
# ...and one of hers that is the END of a line her engine builds (the Mac's own error words come first)
HERS_NOT_OURS_ENDS = {
    "If it asked about Speech Recognition, click Allow, then try again.": "replaced by our permission lines (wrong once refused: macOS never asks twice)",
}
# Lines of ours held in one piece where her script builds them from parts: (key, her parts, each found in her page)
BUILT_FROM_PARTS = {
    "sum_photos": (" photo${ph === 1 ? '' : 's'}",),
    "sum_videos": (" video${nv === 1 ? '' : 's'}",),
    "sum_zooms": (" zoom${mv === 1 ? '' : 's'}",),
    "sum_caps_on": (" · captions ${REC.captions === false ? 'off' : 'on'}",),
    "sum_caps_off": (" · captions ${REC.captions === false ? 'off' : 'on'}",),
    "secs": ("+ ' s'",),
    "pick_alt": ('alt="Photo ${p.n}"',),
}
REAL = Path.home() / (".stu" + "dio")          # only ever listed, to prove this test leaves it alone


def real_listing():
    try:
        return sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in REAL.iterdir())
    except OSError:
        return None


def skip(line):
    print("SKIP  " + line, flush=True)


def wait_for(cond, seconds=30, every=0.1):
    end = time.time() + seconds
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(every)
    return cond()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- the pretend Assistant, its kits, and the page server ----------

class Setup:
    def __init__(self, work, port):
        self.work, self.want = Path(work), port
        self.home = self.work / "home"
        self.studio = self.work / "studio"
        self.assistant = self.work / "The Assistant"
        self.content = self.assistant / "Your Content"
        self.pretend = self.work / "pretend.json"
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), STUDIO_HOME=str(self.studio),
                        ASSISTANT_TEST_OPEN="front", ASSISTANT_TEST_CAPCUT="1", PYTHONIOENCODING="utf-8",
                        ASSISTANT_TEST_TALKING_STORE=str(self.work / "capcut"), REMINDERS_BACKEND="none",
                        TALKING_TRANSCRIBER="pretend", TALKING_PRETEND=str(self.pretend), TALKING_NO_REAL="1")
        for k in ("ASSISTANT_NO_AVFOUNDATION", "ASSISTANT_NO_AFCONVERT", "ASSISTANT_TEST_TALK_LIMITS"):
            self.env.pop(k, None)
        self.proc, self.port, self.n = None, None, 0
        self.TR = self.tp = self.video = None

    def modules(self):
        """talking_rec and talking_page in this process, on the scratch home (to seed records as the job would,
        and to cut as the chat would)."""
        for k in ("STUDIO_HOME", "TALKING_TRANSCRIBER", "TALKING_PRETEND", "TALKING_NO_REAL", "ASSISTANT_TEST_OPEN", "REMINDERS_BACKEND",
                  "ASSISTANT_TEST_TALKING_STORE"):
            os.environ[k] = self.env[k]
        sys.path.insert(0, str(SCRIPTS))
        sys.path.insert(0, str(REEL))
        import talking_rec, talking_page, video    # noqa: E401
        self.TR, self.tp, self.video = talking_rec, talking_page, video

    def kit(self, name):
        return self.content / name

    def make_kit(self, name, photos=6, sheet=True):
        k = self.kit(name)
        for d in (k / ".kit", k / "Photos"):
            d.mkdir(parents=True, exist_ok=True)
        rows = []
        for i in range(1, photos + 1):
            f = k / "Photos" / ("beach-%03d.jpg" % i)
            f.write_bytes(wpc.TINY)
            rows.append({"n": i, "file": str(f), "w": 24, "h": 30, "way": "tall"})
        (k / ".kit" / "kit.json").write_text(json.dumps({"name": name[11:], "date": name[:10], "folder": name}, ensure_ascii=False), encoding="utf-8")
        if sheet:
            (k / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(k / "Photos"), "photos": rows}), encoding="utf-8")
        return k

    def add_talk(self, kit, name, copy=True):
        """One "talking video" in the kit's Talking folder (the 3-second fixture), its small copy already in
        place (so no job here ever makes one). Returns its key."""
        d = kit / "Talking"
        d.mkdir(exist_ok=True)
        shutil.copyfile(str(FIXTURE), str(d / name))
        return self.place_copy(kit, name) if copy else self.video.key(d / name)

    def place_copy(self, kit, name):
        key = self.video.key(kit / "Talking" / name)
        p = self.TR.preview_path(kit, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(FIXTURE), str(p))
        return key

    def says(self, **spec):
        self.pretend.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    def make(self):
        for d in (self.home, self.studio, self.content, self.work / "capcut"):
            d.mkdir(parents=True, exist_ok=True)
        (self.studio / "studio.json").write_text(json.dumps({"posts": {"home": str(self.assistant)}}), encoding="utf-8")
        self.modules()
        self.says(words=WORDS2)

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

    def q(self, kit):
        return "?kit=" + quote(kit, safe="")

    def http(self, method, path, body=None, headers=None, raw_body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = raw_body
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        if data is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        hdrs = dict(r.getheaders())
        c.close()
        try:
            j = json.loads(raw.decode("utf-8"))
        except ValueError:
            j = None
        return r.status, j, raw, hdrs

    def state(self, kit, more=""):
        return self.http("GET", "/talking-state" + self.q(kit) + more)[1]

    def post(self, path, body, **kw):
        code, j, _raw, _h = self.http("POST", path, body, **kw)
        return code, j

    def rec(self, kit):
        try:
            return json.loads((self.kit(kit) / ".kit" / "talking.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def rec_bytes(self, kit):
        try:
            return (self.kit(kit) / ".kit" / "talking.json").read_bytes()
        except OSError:
            return b""

    def job(self, kit):
        return self.TR.read_job(self.kit(kit)) or {}

    def settled(self, kit, seconds=60):
        """Until no job is at work on this kit and its record no longer says working; the state then."""
        def over():
            st = self.state(kit)
            return st if (st and st.get("ok") and not st["working"] and st["rec"].get("status") != "working") else None
        return wait_for(over, seconds)

    def cut(self, kit, pairs, why=("the warm-up",), replace=False):
        """As the chat's `talking_rec.py cut` would."""
        return self.TR.save_cut(self.kit(kit), {"cut": pairs, "why": list(why)}, replace)


# ---------- words: hers, both ways ----------

def fragments(line):
    """A line of ours as it is compared: the pieces between its {names} (her bold, her line break, a blank)."""
    return [" ".join(x.split()) for x in re.split(r"\{\w+\}", line)]


def worth(frag):
    return len(frag) >= 2 and re.search(r"[A-Za-z0-9]", frag)


def her_lines():
    """(everything she wrote as whole pieces, the lines a photographer can see, all her text as one string)."""
    raw = (HERS24 / "pages" / "talking-reel.html").read_text(encoding="utf-8")
    attrs = [" ".join(html.unescape(t).split()) for t in re.findall(r'(?:title|aria-label)="([^"]*)"', raw)]
    whole = {x for _, x in wpc.her_strings(raw, everything=True)} | set(attrs)
    shown = [x for _, x in wpc.her_strings(raw)] + [a for a in attrs if "${" not in a]
    py = ""
    for name in ("talking_core.py", "server.py"):
        src = (HERS24 / name).read_text(encoding="utf-8")
        py += "\n" + src
        if name == "server.py":                      # only her talking reel's own part of the server
            a = src.find("def make_talking")
            src = src[a:src.find("\ndef ", a + 10)] if a >= 0 else ""
        for m in re.finditer(r'(?:ValueError\(f?|"step": |\["step"\] = |"problem": )"((?:[^"\\]|\\.)+)"', src):
            t = " ".join(m.group(1).replace("\\'", "'").replace('\\"', '"').split())
            if re.search(r"[A-Za-z]{2,} [A-Za-z]", t):
                shown.append(t)
    text = " ".join((html.unescape(raw) + py).replace("\\'", "'").split())
    return whole, shown, text


def check_words(s):
    tp = s.tp
    w = tp.WORDS
    ours_lines = [line for line, _why in tp.OUR_WORDS.values()]
    case("no word on the page says \"Claude\" (hers: \"my assistant\", \"your assistant\")",
         not [v for v in list(w.values()) + ours_lines if "claude" in v.lower()], [v for v in list(w.values()) + ours_lines if "claude" in v.lower()][:3])
    case("every line of ours has its reason beside it", all(isinstance(v, tuple) and len(v) == 2 and v[0] and len(v[1]) > 10 for v in tp.OUR_WORDS.values()))
    case("no key is both hers and ours", not set(w) & set(tp.OUR_WORDS), sorted(set(w) & set(tp.OUR_WORDS)))
    case("her engine's and her server's lines are the very ones talking_rec sends",
         all(w["job_" + k] == v for k, v in s.TR.JOB_WORDS.items()) and all(w["make_" + k] == v for k, v in s.TR.MAKE_WORDS.items()))
    case("her times: a look every 3 seconds, a toast for 2.6, 60 steps of Undo, a save of up to 200,000 bytes",
         (tp.LOOK_EVERY_MS, tp.TOAST_MS, tp.UNDO_STEPS, tp.SAVE_CAP) == (3000, 2600, 60, 200000))
    pw = tp.page_words()
    if WINDOWS:
        case("on a PC her \"Finder\" is File Explorer and the Undo tooltips name Ctrl",
             "File Explorer" in pw["talking_open"] and "Finder" not in pw["talking_open"] and pw["undo_title"] == "Undo (Ctrl+Z)" and pw["redo_title"] == "Redo (Ctrl+Shift+Z)", pw["talking_open"])
    else:
        case("on a Mac her words are exactly hers (Finder, ⌘Z, ⇧⌘Z)", all(pw[k] == v for k, v in w.items()))
    if HERS24 is None:
        skip("her words against her own files: her handoff (reference-private) isn't on this computer")
        return
    whole, shown, text = her_lines()
    # ours in hers: each piece of each line of ours is a WHOLE piece of her wording (or, for a piece of 12
    # characters or more, is found word for word in her files; her script's pieces inside an attribute are not
    # pulled out whole)
    bad = []
    for k, v in w.items():
        if k in BUILT_FROM_PARTS:
            continue
        for frag in fragments(v):
            if worth(frag) and frag not in whole and not (len(frag) >= 12 and frag in text):
                bad.append((k, frag))
    case("every line in talking_page.WORDS (%d) is in her files, word for word" % len(w), not bad, bad[:6])
    raw = (HERS24 / "pages" / "talking-reel.html").read_text(encoding="utf-8")
    case("the lines ours holds in one piece are made of her parts", all(p in raw for parts in BUILT_FROM_PARTS.values() for p in parts),
         [p for parts in BUILT_FROM_PARTS.values() for p in parts if p not in raw])
    # hers in ours: every line her page, engine and server can show is, whole, a line (or a piece) of ours
    ours = set()
    for v in w.values():
        ours |= {" ".join(v.split())} | set(fragments(v))
    built = [" ".join(w[k].split()) for k in BUILT_FROM_PARTS]

    def named(x):
        return x in HERS_NOT_OURS or any(x.endswith(n) for n in HERS_NOT_OURS_ENDS)
    missing = [x for x in shown if x not in ours and not named(x) and not any(x in b for b in built)
               and not re.fullmatch(r"[.#][\w .#\[\]=\"-]+", x)]          # a selector in her code, not wording
    case("every line her page, her engine and her server can show (%d) is in talking_page.WORDS, whole; the ones left out on purpose are named" % len(shown),
         len(shown) > 150 and not missing, missing[:6])
    case("...and nothing is named as left out that is in fact ours", not [x for x in HERS_NOT_OURS if x in ours and x not in ("Delete",)],
         [x for x in HERS_NOT_OURS if x in ours])
    gone = [n for n in list(HERS_NOT_OURS) + list(HERS_NOT_OURS_ENDS) if n not in text]
    case("...and everything named as left out is truly in her files (the list can't hide a line she never wrote)", not gone, gone)
    case("every line of ours is truly ours (none of them is one of hers under another name)",
         not [v for v in ours_lines if " ".join(v.split()) in whole and len(v) > 12], [v for v in ours_lines if " ".join(v.split()) in whole][:3])


# ---------- s1, by request: the page as built ----------

def check_built(s):
    tp = s.tp
    page = tp.page_html(KIT)
    js = "\n".join(tp.JS_PARTS)
    import talking_css
    css = talking_css.css()
    body = page[page.index("<body"):page.index("<script")]
    case("no address outside this computer in the page, and no serif", not re.search(r"https?://|//fonts|googleapis|Fraunces|--display", page),
         re.findall(r"https?://\S{0,40}", page)[:3])
    case("no path in the page", str(s.work) not in page and "/private" not in page and "Users" not in page and "Your Content" not in page)
    data = page[page.index("id='talkData'>"):page.index("</script>", page.index("id='talkData'>"))]
    case("\"Claude\" is nowhere on the page, nor in any word its script may show", "claude" not in (body + data).lower())
    if not WINDOWS:
        case("the shoot's name is in the page as text, never as HTML",
             "<b>& the" not in page and "<b>&amp; the" not in page and html.escape(SHORT) + " talking reel<em>.</em>" in page)
    code = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)                # the script without its notes
    case("no browser pop-up anywhere in the page's script (confirm, alert, prompt)", not re.search(r"\b(confirm|alert|prompt)\s*\(", js))
    case("the script never writes HTML from a string (innerHTML, insertAdjacentHTML, document.write)",
         not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", js))
    case("the older copy call is tried first, the newer one only after it", 0 < js.find("execCommand('copy')") < js.find("navigator.clipboard.writeText"))
    classes = [c for m in re.finditer(r"class='([^']*)'", body) for c in m.group(1).split()]
    case("her pitfall: the class names \"bar\" and \"sel\" are the top bar's and the highlight bar's, and nothing else's",
         classes.count("bar") == 1 and classes.count("sel") == 1 and "id='selBar'" in body and not re.search(r"['\"](?:[\w -]* )?(bar|sel)(?: [\w -]*)?['\"]|['\"][^'\"]*\.(bar|sel)\b", code),
         (classes.count("bar"), classes.count("sel")))
    case("her pitfall: the talking video's styles name #vid, never a bare \"video\"",
         ".screen #vid{" in css and ".screen.pip #vid{" in css and not re.search(r"\.screen(\.pip)? video\{", css)
         and {x.strip() for x in re.findall(r"([^{}]*)\bvideo\{", css)} <= {".screen .phw", ".vplayer"}, re.findall(r"([^{}]*)\bvideo\{", css))
    case("turned down (a): the preview's box is sticky and the script has no scroll frame of its own",
         ".phone{position:sticky;top:12px}" in css and not re.search(r"\.script\{[^}]*overflow", css) and not re.search(r"\.edit\{[^}]*overflow", css))
    m = re.search(r"<div class='controls'>(.*?)</div></div><div class='script'", body, re.S)
    case("turned down (b): nothing but the two checkboxes sits under the preview",
         bool(m) and re.findall(r"id='(\w+)'", m.group(1)) == ["guidesOn", "cutMode"] and m.group(1).count("<input") == 2 and "<button" not in m.group(1))
    case("turned down (c): the room above the words is only in a sentence that has a photo",
         ".sent.hasph .words span[data-i]{display:inline-block;position:relative;padding-top:44px" in css and css.count("padding-top:44px") == 1)
    dead = (".shot", ".pthumb", ".dragghost", ".words span.hl", ".words span.drop", ".screen.behind", ".screen .tag", ".strip", ".grp", ".addph", ".phw.back")
    case("the styles of what she turned down or left behind are not carried", not [d for d in dead if re.search(re.escape(d) + r"[{ .:,]", css)],
         [d for d in dead if re.search(re.escape(d) + r"[{ .:,]", css)])
    case("...nor their pieces in the page (no photo frame behind the video, no tag, no Photo row)",
         "phBack" not in page and "id='tag'" not in page and ">Photo<" not in page)
    ids = ("back", "title", "addVideo", "vids", "startBtn", "status", "askCut", "cutLine", "copyCut", "whoMe", "whoAsst", "placeAsk", "placeSay",
           "placeLine", "copyPlace", "editStep", "screen", "vid", "phFront", "bvid", "phKnob", "meKnob", "capKnob", "cap", "guides", "guidesOn",
           "cutMode", "script", "capStep", "capOn", "capOff", "capReset", "result", "selBar", "selPhoto", "selVideo", "selCut", "selBack", "selPunch",
           "selZoom", "selNoZoom", "pick", "pickHead", "pickClose", "pickGrid", "pickCount", "pickUse", "dock", "tl", "tlPlay", "tlTime", "tlSplit",
           "tlCut", "tlSpeed", "tlZoom", "tlUndo", "tlRedo", "tlOut", "tlScale", "tlIn", "tlTrack", "tlInner", "tlRuler", "tlPhotos", "tlClips",
           "tlWords", "tlHead", "tlHint", "sum", "makeBtn", "vpick", "vpHead", "vpClose", "vpList", "vpPlayer", "vpVid", "vpAt", "vpUse", "vpOpen",
           "vpRefresh", "pmenu", "toast")
    case("the whole page is there, every piece under her own name (%d)" % len(ids), not [i for i in ids if ("id='%s'" % i) not in body],
         [i for i in ids if ("id='%s'" % i) not in body])
    case("as it opens: steps 2 and 3 and the timeline are hidden, Make it in CapCut is off, and the bar says \"Add your video to start\"",
         "id='editStep' hidden" in body and "id='capStep' hidden" in body and "id='tl' hidden" in body
         and re.search(r"id='makeBtn' type='button' disabled>Make it in CapCut<", body) and ">Add your video to start</span>" in body)
    case("every button says it is a button (none can send a form)", not re.findall(r"<button(?![^>]*type='button')[^>]*>", body))
    case("the Back to the post kit link goes to this shoot's kit page", "href='/content/" + quote(KIT, safe="") + "/Post%20kit.html'" in body)
    case("the page's files stay readable: each script file is one string and nothing else",
         all(len([n for n in dir(m) if not n.startswith("_")]) == 1 for m in (sys.modules["talking_js_core"], sys.modules["talking_js_step1"])))
    new = ("talking_page.py", "talking_css.py", "talking_js_core.py", "talking_js_step1.py", "talking_js_script.py", "talking_js_pick.py",
           "talking_js_preview.py")
    lit = [f for f in new if re.search(r"expanduser|['\"]\.studio['\"]", (SCRIPTS / f).read_text(encoding="utf-8"))]
    case("no literal home in the new files (the computer's own folder only through arrange.HOME)", not lit, lit)


# ---------- s1, by request: the routes ----------

def check_routes(s):
    TR = s.TR
    kit = s.make_kit(ROUTES_KIT)
    empty = s.make_kit(EMPTY_KIT)
    bare = s.make_kit(NO_SHEET, sheet=False)
    q, host = s.q(ROUTES_KIT), {"Host": "127.0.0.1:%d" % s.port}
    k1 = s.add_talk(kit, V1)
    k2 = s.add_talk(kit, V2)
    (bare / "Footage").mkdir()
    shutil.copyfile(str(FIXTURE), str(bare / "Footage" / "bts.mp4"))

    # ---- the page and the state: who may ask
    code, _j, raw, _h = s.http("GET", "/talking.html" + q)
    page = raw.decode("utf-8")
    case("GET /talking.html: the page, for a kit by its folder name", code == 200 and "id='startBtn'" in page and "Routes talking reel<em>.</em>" in page)
    case("...and its photos' small copies are started, as the pickers do",
         wait_for(lambda: len([f for f in os.listdir(str(kit / ".kit" / "previews")) if f.endswith(".jpg")]) >= 6 if (kit / ".kit" / "previews").is_dir() else False, 30)
         or not MAC)
    for what, path, hdr in (("another host", "/talking.html" + q, {"Host": "evil.example"}),
                            ("another host", "/talking-state" + q, {"Host": "evil.example:%d" % s.port}),
                            ("another host", "/talking-video" + q, {"Host": "localhost.evil.example"})):
        code, _j, raw, _h = s.http("GET", path, headers=hdr)
        case("GET %s from %s: 403" % (path.split("?")[0], what), code == 403)
    code, _j, raw, _h = s.http("GET", "/talking.html" + q, headers={"Sec-Fetch-Site": "cross-site"})
    case("the page asked for from another website: the plain \"can't find\" page", code == 200 and s.tp.CANT_FIND in html.unescape(raw.decode("utf-8")) and b"startBtn" not in raw)
    code, j, _raw, _h = s.http("GET", "/talking-state" + q, headers={"Sec-Fetch-Site": "cross-site"})
    case("the state asked for from another website: 403, nothing told", code == 403 and j == {"ok": False, "words": s.tp.NOT_UNDERSTOOD})
    code, _j, raw, _h = s.http("GET", "/talking-video" + q, headers={"Sec-Fetch-Site": "cross-site"})
    case("the video asked for from another website: 404", code == 404)
    for bad in ("Nope", "../" + ROUTES_KIT, "..", str(kit), ROUTES_KIT + "/.kit", ""):
        code, j, raw, _h = s.http("GET", "/talking-state?kit=" + quote(bad, safe=""))
        code2, _j2, raw2, _h2 = s.http("GET", "/talking.html?kit=" + quote(bad, safe=""))
        code3 = s.http("GET", "/talking-video?kit=" + quote(bad, safe=""))[0]
        case("a kit that isn't in Your Content (%r): can't find, on all three" % bad[-24:],
             code == 404 and j.get("words") == s.tp.CANT_FIND and b"startBtn" not in raw2 and s.tp.CANT_FIND in html.unescape(raw2.decode("utf-8")) and code3 == 404, (code, j, code3))
    code, _j, raw, _h = s.http("GET", "/talking.html" + s.q(NO_SHEET))
    code2, j2, _raw, _h = s.http("GET", "/talking-state" + s.q(NO_SHEET))
    case("a kit whose photos aren't numbered yet: the pickers' own \"not ready\" page, and the state says the same",
         code == 200 and b"startBtn" not in raw and s.tp.NOT_READY in html.unescape(raw.decode("utf-8")) and code2 == 404 and j2 == {"ok": False, "words": s.tp.NOT_READY}, (code, code2, j2))
    case("...in this page's own words: \"your assistant\", never \"Claude\" (the pickers' line says \"to Claude\")",
         "claude" not in raw.decode("utf-8").lower() and "claude" not in json.dumps(j2).lower() and "your assistant" in s.tp.NOT_READY
         and s.tp.NOT_READY == s.tp.OUR_WORDS["not_ready"][0], j2)

    # ---- the state, whole and short
    st = s.state(ROUTES_KIT)
    case("the state before anything: her shape, the two videos as {key, name}, no script, nothing working",
         st["ok"] and st["videos"] == sorted([{"key": k1, "name": V1}, {"key": k2, "name": V2}], key=lambda v: v["name"]) and st["working"] is False
         and st["rec"]["words"] == [] and st["pieces"] == [] and st["folder"] is True and st["short"] == "Routes" and "make" in st and st["make"] is None,
         {k: st.get(k) for k in ("ok", "videos", "working", "folder", "short")})
    blob = json.dumps(st, ensure_ascii=False)
    case("no path in the state", str(s.work) not in blob and "/private" not in blob and "Talking/" not in blob and ".kit" not in blob)
    more = "&rev=%d&mark=%s" % (st["rev"], st["mark"])
    short = s.state(ROUTES_KIT, more)
    case("asked with the counter and the mark it holds, the page gets only {ok, rev, mark, working, step, make}",
         set(short) == {"ok", "rev", "mark", "working", "step", "make"} and short["rev"] == st["rev"] and short["mark"] == st["mark"], short)
    for what, m in (("the counter alone", "&rev=%d" % st["rev"]), ("a counter that isn't a number", "&rev=abc&mark=" + st["mark"]),
                    ("a mark that isn't one", "&rev=%d&mark=../x" % st["rev"]), ("an older counter", "&rev=%d&mark=%s" % (st["rev"] + 7, st["mark"])),
                    ("another mark", "&rev=%d&mark=%s" % (st["rev"], "0" * 12))):
        got = s.state(ROUTES_KIT, m)
        case("...and with %s, the whole state" % what, got.get("ok") and "rec" in got and "videos" in got, sorted(got))
    TR.put_words(kit, V1, k1, WORDS1, info={"dur": 3.0, "w": 320, "h": 240})
    got = s.state(ROUTES_KIT, more)
    case("once the record moves (a script arrives), the same question gets the whole state",
         "rec" in got and got["rev"] != st["rev"] and len(got["rec"]["words"]) == len(SAID) and got["rec"]["status"] == "ready" and got["video_state"] == "here"
         and got["rec"]["info"] == {"dur": 3.0}, sorted(got))
    case("the words with <b>, quotes and an emoji travel as they are (the page shows them as text)",
         [x["w"] for x in got["rec"]["words"]][2:5] == ["<b>bold</b>", "\"quoted\"", "🌊"])
    st = got
    shutil.copyfile(str(FIXTURE), str(kit / "Talking" / "third.mp4"))
    got = s.state(ROUTES_KIT, "&rev=%d&mark=%s" % (st["rev"], st["mark"]))
    case("a video dragged into the Talking folder moves the mark: the whole state, with the new video",
         "rec" in got and got["rev"] == st["rev"] and got["mark"] != st["mark"] and "third.mp4" in [v["name"] for v in got["videos"]], got.get("mark"))
    (kit / "Talking" / "third.mp4").unlink()                # the test's own copy

    # a long talk: the whole state is big, the short answer tiny
    long_kit = s.make_kit(LONG_KIT, photos=2)
    lk = s.add_talk(long_kit, "long.mp4")
    many = [{"w": "word%d%s" % (i, "." if i % 12 == 11 else ""), "start": round(i * 0.4, 3), "end": round(i * 0.4 + 0.3, 3), "conf": 0.9} for i in range(4500)]
    TR.put_words(long_kit, "long.mp4", lk, many, info={"dur": 1800.0})
    t0 = time.time()
    code, lj, lraw, _h = s.http("GET", "/talking-state" + s.q(LONG_KIT))
    t_full = time.time() - t0
    code2, sj, sraw, _h = s.http("GET", "/talking-state" + s.q(LONG_KIT) + "&rev=%d&mark=%s" % (lj["rev"], lj["mark"]))
    case("a 30-minute talk (4,500 words): the whole state is hundreds of kilobytes, the 3-second answer under 300 bytes",
         code == 200 and len(lraw) > 200000 and len(lj["rec"]["words"]) == 4500 and code2 == 200 and len(sraw) < 300 and "rec" not in sj, (len(lraw), len(sraw), round(t_full, 2)))

    # ---- the talking video's small copy
    code, _j, raw, hdr = s.http("GET", "/talking-video" + q)
    case("GET /talking-video: the small copy of the record's video, whole", code == 200 and raw == FIXTURE.read_bytes() and hdr.get("Content-Type") == "video/mp4")
    code, _j, raw, hdr = s.http("GET", "/talking-video" + q + "&v=anything", headers={"Range": "bytes=100-199"})
    case("...and in pieces when the player asks (Range: 206)", code == 206 and raw == FIXTURE.read_bytes()[100:200] and hdr.get("Content-Range") == "bytes 100-199/%d" % FIXTURE.stat().st_size, (code, hdr.get("Content-Range")))
    code = s.http("GET", "/talking-video" + q + "&file=" + quote(str(FIXTURE)))[0]
    code2 = s.http("GET", "/talking-video" + q + "&key=" + k2)[0]
    case("...nothing but the kit may be named (a file, a key: 404)", code == 404 and code2 == 404, (code, code2))
    case("a kit with no script has no video to play: 404", s.http("GET", "/talking-video" + s.q(EMPTY_KIT))[0] == 404)

    # ---- every POST: who may send, what, and how much
    ok_body = {"kit": ROUTES_KIT}
    before = s.rec_bytes(ROUTES_KIT)
    for path in s.tp.POST_PATHS:
        got = [s.http("POST", path, ok_body, headers=h)[0] for h in ({"Host": "evil.example"}, {"Origin": "http://evil.example"}, {"Origin": "null"},
                                                                     {"Content-Type": "text/plain"}, {"Content-Type": "application/x-www-form-urlencoded"})]
        code_big = s.http("POST", path, raw_body=b'{"kit": "' + b"x" * 200001 + b'"}')[0]
        code_arr = s.http("POST", path, raw_body=b"[1, 2]")[0]
        code_junk = s.http("POST", path, raw_body=b"{not json")[0]
        code_kit, j_kit = s.post(path, dict(ok_body, kit="Nope"))
        code_dots, _j = s.post(path, dict(ok_body, kit="../" + ROUTES_KIT))
        code_more, _j = s.post(path, dict(ok_body, also="x", page="abcdef123", base=0, saved={"captions": True}))
        case("POST %s refuses: another host, another Origin, a type that isn't JSON, over the cap, not an object, an unknown kit, \"..\", a field it doesn't take" % path,
             got == [403, 403, 403, 415, 415] and code_big == 413 and code_arr == 400 and code_junk == 400 and code_kit == 404 and j_kit.get("words") == s.tp.CANT_FIND
             and code_dots == 404 and code_more == 400, (got, code_big, code_arr, code_junk, code_kit, code_dots, code_more))
    filler = "x" * 100000
    code_save = s.http("POST", "/talking-save", raw_body=json.dumps({"kit": ROUTES_KIT, "base": 0, "page": "abcdef123", "saved": {"nope": filler}}).encode())[0]
    code_open = s.http("POST", "/talking-open", raw_body=json.dumps({"kit": ROUTES_KIT, "pad": filler}).encode())[0]
    case("a save may be up to 200,000 bytes (100,000 is read, and refused for what is in it); the other routes keep the usual small cap",
         code_save == 400 and code_open == 413, (code_save, code_open))
    case("...and none of those refusals wrote anything", s.rec_bytes(ROUTES_KIT) == before and not (kit / ".kit" / "talking-job.json").exists())

    # ---- Add my video
    code, j = s.post("/talking-open", {"kit": EMPTY_KIT})
    case("POST /talking-open: makes the shoot's Talking folder and answers her toast",
         code == 200 and j == {"ok": True, "words": s.tp.page_words()["talking_open"]} and (empty / "Talking").is_dir(), j)
    os.environ["ASSISTANT_TEST_OPEN"] = "behind"
    code, j = s.tp.open_talking({"kit": EMPTY_KIT})
    case("...opened behind the window: her toast and where to look", j["ok"] and j["words"].startswith(s.tp.page_words()["talking_open"] + ",") and "behind" in j["words"], j)
    os.environ["ASSISTANT_TEST_OPEN"] = "fail"
    code, j = s.tp.open_talking({"kit": EMPTY_KIT})
    case("...could not be opened: says so, never \"is open\"", j == {"ok": False, "words": s.tp.OUR_WORDS["cant_open"][0]}, j)
    os.environ["ASSISTANT_TEST_OPEN"] = "front"
    if not WINDOWS:
        linked = s.make_kit("2026-10-04 Linked")
        outside = s.work / "outside"
        outside.mkdir()
        os.symlink(str(outside), str(linked / "Talking"))
        code, j = s.post("/talking-open", {"kit": "2026-10-04 Linked"})
        case("a Talking \"folder\" that is a link out of the kit is never opened, and nothing is listed from it",
             j == {"ok": False, "words": s.tp.OUR_WORDS["cant_open"][0]} and s.state("2026-10-04 Linked")["videos"] == [] and s.state("2026-10-04 Linked")["folder"] is False, j)

    # ---- Edit my video
    for bad in (V1, "../x", "", 7, None, k1 + "0", str(kit / "Talking" / V1)):
        code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": bad})
        if not case("Edit my video takes a video's key and nothing else (%r): refused" % (str(bad)[-20:],), code == 400 and j["ok"] is False, (code, j)):
            break
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": "0123456789ab"})
    case("a key no video in the Talking folder has: her line", code == 404 and j.get("words") == "That video isn't in this shoot's Talking folder.", (code, j))
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": k1})
    case("the video already edited (its script ready, the file as it was): nothing to do, no job, nothing written",
         (code, j) == (200, {"ok": True, "already": True}) and not (kit / ".kit" / "talking-job.json").exists(), (code, j))
    os.environ["TALKING_TRANSCRIBER"] = "none"
    code, j = s.tp.start_from_page({"kit": ROUTES_KIT, "video": k2})
    os.environ["TALKING_TRANSCRIBER"] = "pretend"
    pc_line = TR.line_for("pc") if (WINDOWS or not MAC) else None
    case("a computer that can't turn talking into words answers at once, in plain words, and makes nothing",
         j.get("ok") is False and j.get("words") and (pc_line is None or j["words"] == pc_line) and "Traceback" not in j["words"]
         and not (kit / ".kit" / "talking-job.json").exists() and s.rec(ROUTES_KIT)["video"] == V1, j)
    code, j = s.post("/talking-make", {"kit": EMPTY_KIT})
    case("Make it in CapCut with no script: her line", code == 400 and j.get("words") == "Turn your video into a script first.", (code, j))

    # ---- the save
    st = s.state(ROUTES_KIT)
    code, j = s.post("/talking-save", {"kit": ROUTES_KIT, "base": st["rev"], "page": "pageone123", "saved": {"photo_mode": "assistant"}})
    case("POST /talking-save: saved, and the answer is the new state", code == 200 and j["ok"] and j["rec"]["photo_mode"] == "assistant" and j["rev"] == st["rev"] + 1 and "make" in j, (code, j.get("rev")))
    s.cut(ROUTES_KIT, [[0, 1]])
    cut_rev = s.rec(ROUTES_KIT)["rev"]
    code, j2 = s.post("/talking-save", {"kit": ROUTES_KIT, "base": j["rev"], "page": "pagetwo456", "saved": {"cut": []}})
    case("a save from a page that hasn't seen the assistant's cut does NOT undo it: told there is something newer, and given it",
         code == 409 and j2.get("why") == "newer" and j2["state"]["rec"]["cut"] == [[0, 1]] and s.rec(ROUTES_KIT)["cut"] == [[0, 1]] and s.rec(ROUTES_KIT)["rev"] == cut_rev
         and "make" in j2["state"], (code, j2.get("why")))
    before = s.rec_bytes(ROUTES_KIT)
    for what, saved in (("a field that isn't hers", {"video": V2}), ("a speed she doesn't offer", {"speeds": [{"a": 0, "b": 1, "v": 3}]}),
                        ("a photo that isn't in the shoot", {"shots": [{"a": 0, "b": 1, "ns": [99], "spot": "full"}]}), ("nothing", {})):
        code, j = s.post("/talking-save", {"kit": ROUTES_KIT, "base": cut_rev, "page": "pageone123", "saved": saved})
        case("a save with %s: refused in plain words, nothing written" % what, code == 400 and j["ok"] is False and j["words"] == s.tp.NOT_UNDERSTOOD and s.rec_bytes(ROUTES_KIT) == before, (code, j))

    # ---- a copy into the Talking folder that was cut off: "still being copied" must not last for ever
    import reel_page as rp
    cutoff = s.make_kit("2026-10-04 Cut off", photos=1)
    (cutoff / "Talking").mkdir()
    (cutoff / "Talking" / "half.mp4").write_bytes(FIXTURE.read_bytes()[:9000])
    first = s.tp.state(cutoff)
    if [x["name"] for x in first.get("coming") or []] != ["half.mp4"]:
        skip("a copy cut off part way: this computer's listing didn't hold it back")
    else:
        short = s.tp.state(cutoff, first["rev"], first["mark"])
        was = rp.COMING_RECENT
        rp.COMING_RECENT = 0                     # as if the two minutes had gone by with the file untouched
        try:
            later = s.tp.state(cutoff, first["rev"], first["mark"])
        finally:
            rp.COMING_RECENT = was
        case("a video whose copy was cut off is \"still being copied\" only while it is recent: once that time has passed the look "
             "brings the whole state by itself (the folders' mark moves) and the line is gone",
             "rec" not in short and "rec" in later and later["coming"] == [] and later["mark"] != first["mark"],
             (sorted(short), sorted(later), later.get("coming")))

    # ---- the video picker's list (for the sub-stage that builds it): read only
    reel_rec = bare / ".kit" / "reel-page.json"
    code, j = s.http("GET", "/reel-footage" + s.q(NO_SHEET) + "&for=talking")[:2]
    case("GET /reel-footage?for=talking: the Footage list with no \"not ready\", and the reel page's record is neither made nor written",
         code == 200 and j["ok"] and [v["name"] for v in j["videos"]] == ["bts.mp4"] and j["moments"] == [] and not reel_rec.exists(), (code, j))
    code, j = s.http("GET", "/reel-footage" + s.q(NO_SHEET))[:2]
    case("...the reel page's own question is as it was (not ready, for a kit with no numbered photos)", code == 404 and j == {"ok": False, "words": __import__("arrange").NOT_READY}, (code, j))

    if not MAC:
        skip("the job behind Edit my video, by request: turning talking into words is a Mac's (the PC line is checked above)")
        return
    # ---- Edit my video on another video: a job; then back: no job
    s.says(words=WORDS2, sleep=1.5)
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": k2})
    r = s.rec(ROUTES_KIT)
    case("Edit my video on a video with no script: a job is started, and at once the record is on it, working, with her line",
         (code, j) == (200, {"ok": True}) and r["video"] == V2 and r["status"] == "working" and r["step"] == "Getting your video ready…", (code, j, r.get("status")))
    st = s.state(ROUTES_KIT)
    case("...the page is told it is working", st["working"] is True and st["rec"]["status"] == "working")
    short = s.state(ROUTES_KIT, "&rev=%d&mark=%s" % (st["rev"], st["mark"]))
    case("...and the short answer carries it too", short.get("working") is True, short)
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": k1})
    case("a press while it works: her line \"I'm still working on the last one. Give it a minute.\"",
         code == 409 and j.get("words") == "I'm still working on the last one. Give it a minute.", (code, j))
    st = s.settled(ROUTES_KIT)
    case("the job ends: ready, on the second video, with its words; the first video's edit is kept",
         bool(st) and st["rec"]["video"] == V2 and st["rec"]["status"] == "ready" and [x["w"] for x in st["rec"]["words"]] == SAID2
         and st["rec"]["kept_for"] == [V1] and st["rec"]["cut"] == [], st and (st["rec"].get("status"), st["rec"].get("problem"), st["rec"].get("kept_for")))
    case("...and no small copy was made for it (the one already there was used; nothing asked the Mac for a video)",
         sha(TR.preview_path(kit, k2)) == sha(FIXTURE) and sorted(set(os.listdir(str(kit / ".kit" / "talking"))) - {"facts.lock"}) == sorted([k1, k2, "facts.json"]), os.listdir(str(kit / ".kit" / "talking")))
    jid = s.job(ROUTES_KIT).get("id")
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": k1})
    st = s.state(ROUTES_KIT)
    case("back to the first video: its script and its edit come back with NO new transcription (no new job)",
         (code, j) == (200, {"ok": True, "back": True}) and s.job(ROUTES_KIT).get("id") == jid and st["rec"]["video"] == V1 and st["rec"]["status"] == "ready"
         and st["rec"]["cut"] == [[0, 1]] and len(st["rec"]["words"]) == len(SAID) and st["working"] is False,
         (code, j, st["rec"].get("cut"), s.job(ROUTES_KIT).get("id") == jid, st["rec"].get("status"), st["working"]))
    # ---- the video exported again under the same name: the stale-script state
    f = kit / "Talking" / V1
    os.utime(str(f), (f.stat().st_atime, f.stat().st_mtime + 100))
    k1b = s.place_copy(kit, V1)
    st = s.state(ROUTES_KIT)
    case("the video exported again under the same name: the state says its script is another file's",
         k1b != k1 and st["video_state"] == "changed" and {"key": k1b, "name": V1} in st["videos"], (k1b != k1, st.get("video_state")))
    code, j = s.post("/talking-make", {"kit": ROUTES_KIT})
    case("...Make it in CapCut is refused until its script is made again", code == 400 and j.get("words") == TR.line_for("changed"), (code, j))
    s.says(words=WORDS1)
    code, j = s.post("/talking-start", {"kit": ROUTES_KIT, "video": k1b})
    st = s.settled(ROUTES_KIT)
    r = s.rec(ROUTES_KIT)
    case("...and Edit my video on it makes the script again (a new job), the old edit kept, not thrown away",
         (code, j) == (200, {"ok": True}) and s.job(ROUTES_KIT).get("id") != jid and bool(st) and st["video_state"] == "here" and st["rec"]["status"] == "ready"
         and st["rec"]["cut"] == [] and any(x.get("cut") == [[0, 1]] for x in r.get("replaced", [])), (code, j, st and st.get("video_state")))
    s.cut(ROUTES_KIT, [[0, len(SAID) - 1]], replace=True)
    code, j = s.post("/talking-make", {"kit": ROUTES_KIT})
    case("Make it in CapCut with every word cut: her line, nothing made",
         code == 400 and j.get("words") == "Everything is cut. Bring some words back first." and not os.listdir(str(s.work / "capcut")), (code, j))


# ---------- s1, on the real page ----------

READ_TEXT = r"""(function(){
  var out = [], skip = {SCRIPT: 1, STYLE: 1};
  (function walk(n){
    if (n.nodeType === 3) { var t = n.nodeValue.replace(/\s+/g, ' ').trim(); if (t) out.push(t); return; }
    if (n.nodeType !== 1 || skip[n.tagName]) return;
    ['title', 'aria-label', 'placeholder', 'alt'].forEach(function(a){ var v = n.getAttribute(a); if (v) out.push(v.replace(/\s+/g, ' ').trim()); });
    for (var c = n.firstChild; c; c = c.nextSibling) walk(c);
  })(document.body);
  return out;
})()"""


def allowed_text(s, extra=()):
    """Is a piece of text on the page one of WORDS / OUR_WORDS (a blank standing for anything), or theirs?"""
    tp = s.tp
    pats = []
    for line in list(tp.page_words().values()):
        for seg in re.split(r"\{b\}|\{eb\}|\{br\}", line):
            seg = " ".join(seg.split())
            if seg:
                pats.append(re.compile("".join(".+?" if re.fullmatch(r"\{\w+\}", p) else re.escape(p) for p in re.split(r"(\{\w+\})", seg)), re.S))
    import brand
    own = set(extra) | {"1", "2", "3", ".", "+", "−", "0:00.0 / 0:00.0", "▶", "←", brand.PRODUCT, brand.MAKER, SHORT, V1, V2}
    own |= {" ".join(x.split()) for x in re.split(r"<[^>]+>", brand.bar()) if x.strip()}

    def ok(t):
        return t in own or any(p.fullmatch(t) for p in pats)
    return ok


def open_page(c, s, kit=KIT):
    c.open(s.url("/talking.html" + s.q(kit)))
    c.wait_for("window.Talk && window.Talk.loaded", 15, tell="document.body.innerText.slice(0, 200)")


def poll(c, force=False):
    c.js("window.Talk.poll(%s)" % ("true" if force else "false"))


def status(c):
    return " ".join(c.text("#status").split())


def chips(c):
    return c.js("Array.from(document.querySelectorAll('#vids .vid')).map(function(b){ return [b.textContent, b.classList.contains('on'), b.children.length]; })")


def click_chip(c, name):
    c.js("Array.from(document.querySelectorAll('#vids .vid')).filter(function(b){ return b.textContent === %s; })[0].click()" % json.dumps(name))


def toast(c):
    return c.js("document.getElementById('toast').classList.contains('on') ? document.getElementById('toast').textContent : ''")


def check_page(c, s):
    TR, W = s.TR, s.tp.page_words()
    kit = s.make_kit(KIT)
    (kit / "Footage").mkdir()
    shutil.copyfile(str(FIXTURE), str(kit / "Footage" / "bts.mp4"))
    c.init_script("window.__dialogs = 0; ['alert','confirm','prompt'].forEach(function(k){ window[k] = function(){ window.__dialogs++; return true; }; });")
    # a hidden Chrome draws frames only now and then, so the page's one smooth scroll (to the edit) can still be
    # under way many steps later and carry a button out from under a press; here it jumps instead
    c.init_script("(function(){ var real = Element.prototype.scrollIntoView; Element.prototype.scrollIntoView = function(o){"
                  " return real.call(this, (o && typeof o === 'object') ? Object.assign({}, o, {behavior: 'auto'}) : o); }; })();")

    # ---- a shoot with nothing yet
    open_page(c, s)
    case("the page opens: the shoot's name in the title and the tab, as text",
         c.text("#title") == SHORT + " talking reel." and c.js("document.title") == SHORT + " · talking reel" and c.js("document.querySelectorAll('#title b').length") == 0, c.text("#title"))
    case("nothing yet: her \"No videos in the Talking folder yet.\", Edit my video off, no status, the bar says \"Add your video to start\", Make it in CapCut off",
         c.text("#vids") == "No videos in the Talking folder yet." and c.js("document.getElementById('startBtn').disabled") and status(c) == ""
         and c.text("#sum") == "Add your video to start" and c.js("document.getElementById('makeBtn').disabled"), (c.text("#vids"), status(c), c.text("#sum")))
    case("...steps 2 and 3 and the timeline are not shown, nor either line to copy",
         c.js("['editStep','capStep','tl','askCut','placeAsk'].every(function(i){ return document.getElementById(i).hidden; })"))
    case("the dock's room is measured into the page (the make bar never covers the last of it)",
         c.js("parseInt(getComputedStyle(document.documentElement).getPropertyValue('--dock')) === document.getElementById('dock').offsetHeight && parseInt(document.body.style.paddingBottom) === document.getElementById('dock').offsetHeight + 24"))
    c.click("#addVideo")
    c.wait_for("document.getElementById('toast').classList.contains('on')", 5)
    case("Add my video: the Talking folder is made and her toast says it is open", toast(c) == W["talking_open"] and (kit / "Talking").is_dir(), toast(c))

    # ---- who places the photos, before there is a script
    c.click("#whoAsst")
    c.wait_for("!document.getElementById('placeAsk').hidden", 5)
    case("My assistant places them, before the script: the line to copy with her \"Once your script is ready...\"",
         c.text("#placeLine") == "Place the photos in my talking reel for " + SHORT and c.text("#placeSay") == W["place_say_wait"]
         and c.js("document.getElementById('whoAsst').classList.contains('on') && document.getElementById('askCut').hidden") and s.rec(KIT)["photo_mode"] == "assistant",
         (c.text("#placeLine"), c.text("#placeSay")))
    c.click("#copyPlace")
    c.wait_for("document.getElementById('toast').textContent === %s" % json.dumps(W["copied"]), 5)
    case("Copy: the line is copied and her toast says to paste it into the chat", c.js("window.Talk.lastCopied") == "Place the photos in my talking reel for " + SHORT)
    c.click("#whoAsst")
    c.wait_for("document.getElementById('placeAsk').hidden", 5)
    case("pressed again it closes (hers)", s.rec(KIT)["photo_mode"] == "" and not c.js("document.getElementById('whoAsst').classList.contains('on')"))
    c.click("#whoMe")
    c.wait_for("document.getElementById('whoMe').classList.contains('on')", 5)
    case("I'll add them: chosen, with her toast, and no line to copy", toast(c) == W["who_me_toast"] and c.js("document.getElementById('placeAsk').hidden") and s.rec(KIT)["photo_mode"] == "me", toast(c))
    case("choosing who places the photos is no Undo step (2c)", c.js("window.Talk.UNDO.length === 0 && document.getElementById('tlUndo').disabled"))

    # ---- videos arrive in the folder
    k1 = s.add_talk(kit, V1)
    k2 = s.add_talk(kit, V2)
    held = c.js("window.Talk.ST === (window.__st = window.Talk.ST)")
    poll(c)
    c.wait_for("document.querySelectorAll('#vids .vid').length === 2", 10)
    got = chips(c)
    case("videos dragged into the folder show up by themselves, each name as text; the first is picked",
         held and sorted(x[0] for x in got) == sorted([V1, V2]) and [x[1] for x in got].count(True) == 1 and all(x[2] == 0 for x in got)
         and not c.js("document.getElementById('startBtn').disabled"), got)
    c.js("window.__st = window.Talk.ST")
    poll(c)
    time.sleep(0.4)
    case("a look that finds nothing moved brings no new state (the short answer): what is on the page is left alone", c.js("window.Talk.ST === window.__st"))

    if not MAC:
        skip("Edit my video on the real page: turning talking into words is a Mac's")
    else:
        check_edit(c, s, kit, k1, k2)

    # ---- every word on the page is hers, ours, or theirs
    ok = allowed_text(s)
    texts = c.js(READ_TEXT)
    stray = [t for t in texts if not ok(t) and t not in SAID and t not in SAID2]
    case("every piece of text on the page (%d) is one of her lines, one of ours, or the photographer's own" % len(texts), len(texts) > 60 and not stray, stray[:6])
    case("nothing of theirs became HTML (a name, a file name, a word with a tag in it)",
         c.js("!window.pwned && !document.querySelector('#step1 b b, #vids b, #status b b, #title b')") and c.js("document.querySelectorAll('img[src=x]').length") == 0)
    blob = c.js("document.documentElement.outerHTML")
    case("no path anywhere in the page as it stands", str(s.work) not in blob and "/private/" not in blob and "Your Content" not in blob and "/Talking/" not in blob)
    case("no browser pop-up was ever asked for", c.js("window.__dialogs") == 0 and not list(c.dialogs))
    case("nothing was asked of the internet", not c.outside_requests(), c.outside_requests()[:3])
    asked = [r["url"] for r in list(c.requests)]
    case("the page never asked for the Footage list (only the video picker will), and nothing was made for a Footage video while it sat open",
         not [u for u in asked if "/reel-" in u] and not (kit / ".kit" / "footage").exists(), [u for u in asked if "/reel-" in u][:3])
    case("no page errors", not c.page_errors(), c.page_errors()[:3])

    # ---- phone width
    c.phone()
    try:
        open_page(c, s)
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
        case("phone width: no sideways scroll", wide[0] <= 0 and wide[1] == 390, wide)
        c.click("#whoAsst")
        c.wait_for("!document.getElementById('placeAsk').hidden", 5)
        wide = c.js("[document.documentElement.scrollWidth - document.documentElement.clientWidth, window.innerWidth]")
        case("...nor with the line to copy showing", wide[0] <= 0, wide)
        c.click("#whoAsst")
        c.wait_for("document.getElementById('placeAsk').hidden", 5)
    finally:
        c.desktop()


def check_edit(c, s, kit, k1, k2):
    TR, W = s.TR, s.tp.page_words()
    dur = W["secs"].replace("{t}", "3")

    # ---- a video with no script yet: the job's steps, then ready
    click_chip(c, V1)
    s.says(words=WORDS1, needs_setup=True, setup_sleep=1.5, sleep=1.5)
    c.js("window.__hist = []; new MutationObserver(function(){ window.__hist.push(document.getElementById('status').innerHTML); })"
         ".observe(document.getElementById('status'), {childList: true, subtree: true, characterData: true})")
    c.click("#startBtn")
    c.wait_for("document.querySelector('#status b') && window.Talk.ST.working", 10, tell="document.getElementById('status').textContent")
    seen = set()

    def watch():
        poll(c)
        seen.add(status(c))
        return c.js("!window.Talk.ST.working && window.Talk.REC.status === 'ready'")
    case("Edit my video on a video with no script: it starts; while it works the button is off",
         c.js("document.getElementById('startBtn').disabled") and s.rec(KIT)["video"] == V1)
    wait_for(watch, 40, 0.25)
    minute = " A minute of video takes about a minute."
    case("just after the press the status line is her plain \"Getting your video ready…\" (not bold, nothing joined to it), until the first look draws the step",
         W["job_ready_video"] in c.js("window.__hist"), c.js("window.__hist")[:4])
    want = [W["job_ready_video"], W["job_setup"], W["job_to_script"]]
    case("the status line shows each step of the job in bold, with her \"A minute of video takes about a minute.\" (hers: getting ready, turning into a script; ours: setting up)",
         all((x + minute) in seen for x in want), sorted(seen))
    after = W["secs"].replace("{t}", str(round(c.js("window.Talk.total()") * 10) / 10).rstrip("0").rstrip("."))
    case("ready: \"<video>: N words, X s of video, Y s after the cuts.\", the video's name in bold and as text",
         status(c) == "%s: %d words, %s of video, %s after the cuts." % (V1, len(SAID), dur, after) and c.text("#status b") == V1
         and c.js("document.querySelectorAll('#status b').length") == 2 and not c.js("document.getElementById('status').classList.contains('bad')"), status(c))
    case("...steps 2 and 3 and the timeline show, and the talking video's small copy is the one asked for",
         c.js("['editStep','capStep','tl'].every(function(i){ return !document.getElementById(i).hidden; })")
         and unquote(c.js("document.getElementById('vid').getAttribute('src')")).startswith("/talking-video?kit=" + KIT + "&v=" + V1),
         c.js("document.getElementById('vid').getAttribute('src')"))
    c.wait_for("document.getElementById('vid').readyState >= 1", 15, tell="document.getElementById('vid').error && document.getElementById('vid').error.message")
    case("...and it loads and plays from this computer (3 seconds long)", abs(c.js("document.getElementById('vid').duration") - 3.0) < 0.3, c.js("document.getElementById('vid').duration"))
    case("the make bar's line, hers: seconds of talking, photos, zooms, captions",
         c.text("#sum") == "%s of talking · 0 photos · 0 zooms · captions on" % after and c.text("#sum b") == after and c.js("document.getElementById('makeBtn').disabled"), c.text("#sum"))
    case("the dock grew with the timeline, and the page's room with it",
         c.js("parseInt(document.body.style.paddingBottom) === document.getElementById('dock').offsetHeight + 24 && document.getElementById('dock').offsetHeight > 100"))

    # ---- the lines to copy, and the empty-list rule
    case("a script the assistant has not cut: her cut line shows (I'll add them is chosen: no place line)",
         not c.js("document.getElementById('askCut').hidden") and c.text("#cutLine") == "Cut my talking reel for " + SHORT and c.js("document.getElementById('placeAsk').hidden"), c.text("#cutLine"))
    c.click("#copyCut")
    c.wait_for("window.Talk.lastCopied === %s" % json.dumps("Cut my talking reel for " + SHORT), 5)
    case("...and Copy copies it", toast(c) == W["copied"], toast(c))
    c.click("#whoAsst")
    c.wait_for("!document.getElementById('placeAsk').hidden", 5)
    case("My assistant places them and nothing cut yet: ONE line does both, and the cut line hides",
         c.text("#placeLine") == "Cut my talking reel and place the photos for " + SHORT and c.text("#placeSay") == W["place_say"] and c.js("document.getElementById('askCut').hidden"),
         c.text("#placeLine"))
    s.cut(KIT, [])
    poll(c)
    c.wait_for("document.getElementById('placeLine').textContent.indexOf('Place the photos') === 0", 10)
    case("the assistant cut, and cut nothing (an empty list still means cut): the line is \"Place the photos in my talking reel for <short>\", no cut line",
         c.text("#placeLine") == "Place the photos in my talking reel for " + SHORT and c.js("document.getElementById('askCut').hidden") and s.rec(KIT)["claude_cut"] == [], c.text("#placeLine"))
    c.click("#whoMe")
    c.wait_for("document.getElementById('placeAsk').hidden", 5)
    case("...and with I'll add them, no line at all once it is cut", c.js("document.getElementById('askCut').hidden && document.getElementById('placeAsk').hidden"))

    # ---- the chat cuts while the page is open; Undo's lists
    c.js("window.Talk.save({captions: false})")
    c.wait_for("window.Talk.UNDO.length === 1 && !document.getElementById('tlUndo').disabled", 5)
    case("an edit on the page is an Undo step, and the bar's line follows it", c.text("#sum").endswith("captions off") and s.rec(KIT)["captions"] is False, c.text("#sum"))
    c.click("#tlUndo")
    c.wait_for("window.Talk.REC.captions === true && window.Talk.REDO.length === 1", 5)
    case("Undo puts it back, with her toast, and Redo is ready", toast(c) == W["undone"] and s.rec(KIT)["captions"] is True and c.js("document.getElementById('tlUndo').disabled && !document.getElementById('tlRedo').disabled"), toast(c))
    took = c.js("window.Talk.save(window.Talk.snap())")
    case("a whole snapshot of the edit goes back to the Assistant as the page holds it (what Undo sends is accepted)", took is True and toast(c) != s.tp.NOT_UNDERSTOOD, took)
    held = c.js("[window.Talk.UNDO.length, window.Talk.rev]")
    again = c.js("window.Talk.save(window.Talk.snap()).then(function(ok){ return [ok, window.Talk.UNDO.length, window.Talk.rev]; })")
    case("a save that changes nothing is no Undo step (the next Undo would say \"Undone\" and undo nothing)", again == [True] + held, (held, again))
    c.js("window.Talk.save({captions: false})")
    c.wait_for("window.Talk.REC.captions === false && window.Talk.UNDO.length >= 1", 5)
    s.cut(KIT, [[0, 1]])
    poll(c)
    c.wait_for("window.Talk.REC.cut.length === 1", 10)
    after2 = W["secs"].replace("{t}", str(round(c.js("window.Talk.total()") * 10) / 10).rstrip("0").rstrip("."))
    case("the assistant's cut arrives by itself: the status line and the bar show the shorter reel",
         status(c).endswith(", %s after the cuts." % after2) and c.text("#sum").startswith(after2 + " of talking") and after2 != after, (status(c), after))
    case("...and Undo and Redo are emptied and grey: one press could have wiped the assistant's cut (2c)",
         c.js("window.Talk.UNDO.length === 0 && window.Talk.REDO.length === 0 && document.getElementById('tlUndo').disabled && document.getElementById('tlRedo').disabled"))
    # a save from a page that has not seen the newest: the cut stays
    c.js("window.__rev = window.Talk.rev")
    s.cut(KIT, [[0, 2]])
    c.js("window.Talk.save({cut: []})")
    c.wait_for("window.Talk.rev !== window.__rev", 10)
    case("a save made before the page saw the assistant's newer cut does not undo it: the page says so and shows the newest",
         s.rec(KIT)["cut"] == [[0, 2]] and c.js("JSON.stringify(window.Talk.REC.cut)") == "[[0,2]]" and toast(c) == TR.NEWER and c.js("window.Talk.UNDO.length") == 0, (s.rec(KIT)["cut"], toast(c)))

    # ---- two quick edits, a save that doesn't get through, a part that fails, answers that cross
    c.wait_for("JSON.stringify(window.Talk.REC.cut) === '[[0,2]]'", 5)
    c.js("(function(){ var T = window.Talk; function add(a, b){ return function(){ return {cut: (T.REC.cut || []).concat([[a, b]])}; }; }"
         " T.save(add(5, 5)); return T.save(add(8, 8)); })()")
    case("two edits pressed in the same moment are BOTH kept, each built on the one before, and each is its own Undo step",
         s.rec(KIT)["cut"] == [[0, 2], [5, 5], [8, 8]] and c.js("window.Talk.UNDO.length") == 2, (s.rec(KIT)["cut"], c.js("window.Talk.UNDO.length")))
    c.js("window.Talk.undo()")
    case("...and Undo takes them off one at a time", s.rec(KIT)["cut"] == [[0, 2], [5, 5]] and c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]") == [1, 1], s.rec(KIT)["cut"])
    c.block_urls(["*talking-save*"])
    try:
        got = c.js("window.Talk.undo()")
        case("Undo whose save does not get through: \"Try again in a moment\", and the step is still there to try again",
             got is False and toast(c) == s.tp.OUR_WORDS["cant_reach"][0] and c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]") == [1, 1]
             and s.rec(KIT)["cut"] == [[0, 2], [5, 5]], (got, toast(c), c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]")))
    finally:
        c.block_urls([])
    c.js("window.Talk.undo()")
    case("...trying again undoes that SAME step: exactly one edit back, not two",
         s.rec(KIT)["cut"] == [[0, 2]] and c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]") == [0, 2] and toast(c) == W["undone"], s.rec(KIT)["cut"])
    c.block_urls(["*talking-save*"])
    try:
        got = c.js("window.Talk.redo()")
        case("Redo the same way: a save that does not get through leaves the step", got is False and c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]") == [0, 2])
    finally:
        c.block_urls([])
    c.js("window.Talk.redo()")
    case("...and trying again redoes that one step", s.rec(KIT)["cut"] == [[0, 2], [5, 5]] and c.js("[window.Talk.UNDO.length, window.Talk.REDO.length]") == [1, 1], s.rec(KIT)["cut"])
    # answers that cross: an older look's answer landing after a newer one's
    crossed = c.js("(function(){ var T = window.Talk, real = window.fetch, n = 0;"
                   " var old = JSON.stringify(Object.assign({}, T.ST, {rev: T.rev - 1, rec: Object.assign({}, T.REC, {cut: []})}));"
                   " window.fetch = function(u, o){ if (String(u).indexOf('/talking-state') < 0) return real(u, o); n++;"
                   "   if (n === 1) return new Promise(function(res){ window.__late = function(){ res(new Response(old, {status: 200, headers: {'Content-Type': 'application/json'}})); }; });"
                   "   return real(u, o); };"
                   " var was = [T.rev, JSON.stringify(T.REC.cut), T.UNDO.length];"
                   " T.poll(false); return T.poll(true).then(function(){ window.__late(); return new Promise(function(r){ setTimeout(r, 150); }); })"
                   "   .then(function(){ window.fetch = real; return [n >= 2, was, [T.rev, JSON.stringify(T.REC.cut), T.UNDO.length]]; }); })()")
    case("an older look's answer that lands after a newer one's is dropped: the page does not go back, and Undo's steps are not thrown away",
         crossed[0] is True and crossed[1] == crossed[2] and crossed[2][2] == 1, crossed)
    # the short answer's step
    c.js("(function(){ var T = window.Talk, real = window.fetch; window.__realFetch = real;"
         " window.fetch = function(u, o){ if (String(u).indexOf('/talking-state') < 0) return real(u, o);"
         "   return Promise.resolve(new Response(JSON.stringify({ok: true, rev: T.rev, mark: T.mark, working: true, step: %s, make: null}), {status: 200})); }; })()" % json.dumps(W["job_to_script"]))
    try:
        poll(c)
        c.wait_for("document.getElementById('status').textContent.indexOf(%s) === 0" % json.dumps(W["job_to_script"]), 8, tell="document.getElementById('status').textContent")
        case("the short answer's step is followed: the status line shows the job's newest step without the whole state", status(c) == W["job_to_script"] + " A minute of video takes about a minute.", status(c))
    except chrome_drive.Timeout:
        case("the short answer's step is followed: the status line shows the job's newest step without the whole state", False, status(c))
    finally:
        c.js("window.fetch = window.__realFetch")
    poll(c, True)
    c.wait_for("!window.Talk.ST.working && document.getElementById('status').textContent.indexOf(%s) === 0" % json.dumps(V1 + ": "), 10)
    # a part of the page that fails
    c.js("window.__boom = true; window.Talk.on('apply', function(a){ if (window.__boom && a.how === 'save') throw new Error('on purpose'); })")
    c.js("window.Talk.save({captions: true})")
    c.js("window.__boom = false")
    s.cut(KIT, [[0, 1]], replace=True)
    poll(c)
    try:
        c.wait_for("JSON.stringify(window.Talk.REC.cut) === '[[0,1]]'", 8)
        arrived = True
    except chrome_drive.Timeout:
        arrived = False
    case("one part of the page failing on a save's answer does not stop the refresh: the assistant's next cut still arrives, and the fault is told",
         arrived and "on purpose" in " ".join(c.js("window.Talk.faults")) and s.rec(KIT)["captions"] is True and c.js("!document.getElementById('tlUndo').disabled || window.Talk.UNDO.length === 0"),
         (arrived, c.js("window.Talk.faults")))
    c.errors[:] = [e for e in c.errors if "on purpose" not in e["text"]]
    c.js("window.Talk.faults.length = 0")
    s.cut(KIT, [[0, 2]], replace=True)
    poll(c, True)
    c.wait_for("JSON.stringify(window.Talk.REC.cut) === '[[0,2]]'", 10)

    # ---- the refresh and its pauses
    case("the 3-second look may run: the page is showing and the video is paused", c.js("window.Talk.quiet()") is True)
    for what, on, off in (("the photo menu open", "document.getElementById('pmenu').classList.add('open')", "document.getElementById('pmenu').classList.remove('open')"),
                          ("the photo picker open", "document.getElementById('pick').classList.add('open')", "document.getElementById('pick').classList.remove('open')"),
                          ("the video picker open", "document.getElementById('vpick').classList.add('open')", "document.getElementById('vpick').classList.remove('open')"),
                          ("a drag", "window.__drag = true; window.__busy || (window.__busy = window.Talk.busy(function(){ return window.__drag; }))", "window.__drag = false")):
        c.js(on)
        held = c.js("window.Talk.quiet()")
        c.js(off)
        case("...it waits during %s" % what, held is False and c.js("window.Talk.quiet()") is True)
    played = c.js("(function(){ var v = document.getElementById('vid'); v.muted = true; return v.play().then(function(){ return true; }, function(){ return false; }); })()")
    if played:
        held = c.js("window.Talk.quiet()")
        c.js("document.getElementById('vid').pause()")
        case("...and while the talking video plays; it runs again once paused", held is False and c.js("window.Talk.quiet()") is True)
        c.js("(function(){ var v = document.getElementById('vid'); v.loop = true; return v.play().then(function(){ return true; }, function(){ return false; }); })()")
        gone = c.js("(function(){ var T = window.Talk; T.apply(Object.assign({}, T.ST, {rec: Object.assign({}, T.REC, {status: 'working'})}), 'poll');"
                    " return [document.getElementById('editStep').hidden, document.getElementById('vid').paused, T.quiet()]; })()")
        c.js("document.getElementById('vid').loop = false")
        case("when the script goes away (another video is being made ready) a playing talking video is stopped: nothing plays unseen, and the look can run to bring the new script",
             gone == [True, True, True], gone)
        poll(c, True)
        c.wait_for("!document.getElementById('editStep').hidden", 10)
    else:
        skip("the look waiting while the video plays: this Chrome would not play it")
    c.js("document.getElementById('vid').muted = false")
    got = c.js("fetch('/talking-state?kit=' + encodeURIComponent(document.body.dataset.kit) + '&rev=' + window.Talk.rev + '&mark=' + window.Talk.mark).then(function(r){ return r.text(); })")
    case("what the page asks every 3 seconds comes back short (under 300 bytes, no script in it)", len(got) < 300 and "words" not in json.loads(got), len(got))
    c.wait_for("window.Talk.timer > 0", 2)

    # ---- the same video again: to the edit, nothing started
    jid = s.job(KIT).get("id")
    c.js("window.scrollTo(0, 0)")
    c.click("#startBtn")
    time.sleep(0.8)
    case("Edit my video on the video already edited takes them to the edit and starts nothing",
         s.job(KIT).get("id") == jid and c.js("document.getElementById('editStep').getBoundingClientRect().top") < 200 and s.rec(KIT)["cut"] == [[0, 2]]
         and not c.js("window.Talk.ST.working"), c.js("document.getElementById('editStep').getBoundingClientRect().top"))
    c.js("window.scrollTo(0, 0)")

    # ---- another video: asked once, on the page
    click_chip(c, V2)
    c.click("#startBtn")
    ask = "Edit %s instead? Your edit of %s is kept, but this page will show the new one. Press Edit my video again to go ahead." % (V2, V1)
    case("Edit my video on a different video asks first, ON THE PAGE, with both names as text",
         status(c) == ask and c.js("Array.from(document.querySelectorAll('#status b')).map(function(b){ return b.textContent; })") == ["Edit %s instead?" % V2, "Edit my video"]
         and s.job(KIT).get("id") == jid and s.rec(KIT)["video"] == V1, status(c))
    poll(c)
    poll(c, True)
    time.sleep(0.5)
    s.cut(KIT, [[0, 3]], replace=True)
    poll(c)
    c.wait_for("JSON.stringify(window.Talk.REC.cut) === '[[0,3]]'", 10)
    case("the 3-second refresh never writes over that question, even when it brings a change", status(c) == ask, status(c))
    click_chip(c, V1)
    case("picking the first video again takes the question away", status(c).startswith(V1 + ": "), status(c))
    click_chip(c, V2)
    c.click("#startBtn")
    case("...and coming back to the other one asks again (in hers the next press went ahead unasked)", status(c) == ask and s.job(KIT).get("id") == jid, status(c))
    s.says(words=WORDS2, asking=2.0, sleep=0.3)
    c.click("#startBtn")
    c.wait_for("window.Talk.ST.working", 10)
    case("the second press goes ahead: the new video is being worked on", s.rec(KIT)["video"] == V2 and status(c).endswith(minute) and s.job(KIT).get("id") != jid, status(c))
    seen = set()

    def watch2():
        poll(c)
        seen.add((status(c), c.text("#status b") if c.count("#status b") else ""))
        return c.js("!window.Talk.ST.working && window.Talk.REC.status === 'ready'")
    wait_for(watch2, 40, 0.25)
    case("while the Mac is asking about Speech Recognition the status line says so, whole and in bold (ours; no \"a minute\" after it)",
         (W["job_asking"], W["job_asking"]) in seen, sorted(seen))
    case("...then ready, on the new video, the first one's edit kept",
         status(c).startswith("%s: %d words, " % (V2, len(SAID2))) and s.state(KIT)["rec"]["kept_for"] == [V1] and c.js("window.Talk.REC.cut.length") == 0, status(c))
    case("a new script on the page empties Undo (its steps were another video's word numbers)", c.js("window.Talk.UNDO.length === 0"))

    # ---- back to the first: its edit, no new transcription
    jid = s.job(KIT).get("id")
    click_chip(c, V1)
    c.click("#startBtn")
    case("going back asks the same way", status(c).startswith("Edit %s instead? Your edit of %s is kept" % (V1, V2)), status(c))
    c.click("#startBtn")
    c.wait_for("window.Talk.REC.video === %s && window.Talk.REC.status === 'ready'" % json.dumps(V1), 10)
    case("...and its script and edit are back at once, nothing transcribed again (\"Your edit is kept\" is true)",
         s.job(KIT).get("id") == jid and c.js("JSON.stringify(window.Talk.REC.cut)") == "[[0,3]]" and status(c).startswith("%s: %d words, " % (V1, len(SAID))), status(c))

    # ---- a refusal that stays, and a problem from the job
    s.says(words=WORDS2, error="refused")
    click_chip(c, V2)
    c.click("#startBtn")
    c.click("#startBtn")
    c.wait_for("window.Talk.REC.video === %s" % json.dumps(V2), 10)
    f2 = kit / "Talking" / V2
    os.utime(str(f2), (f2.stat().st_atime, f2.stat().st_mtime + 50))
    s.place_copy(kit, V2)
    poll(c)
    c.wait_for("window.Talk.ST.video_state === 'changed'", 10)
    case("the video exported again under the same name: the status line says its script is the old file's, in red (ours)",
         status(c) == TR.line_for("changed") and c.js("document.getElementById('status').classList.contains('bad')"), status(c))
    c.click("#startBtn")
    c.wait_for("window.Talk.REC.problem && !window.Talk.ST.working", 30, tell="JSON.stringify([window.Talk.REC.status, window.Talk.ST.working])")
    case("...Edit my video on it starts its script again instead of scrolling; and when the Mac refuses, the status line says what to do, in red, and the button is back",
         status(c) == TR.line_for("refused") and c.js("document.getElementById('status').classList.contains('bad') && !document.getElementById('startBtn').disabled"), status(c))
    case("...and the script made before is still there to edit (only a video with no script at all puts steps 2 and 3 away)",
         c.js("!document.getElementById('editStep').hidden && !document.getElementById('tl').hidden && window.Talk.REC.words.length") == len(SAID2))
    # a refusal from Edit my video itself: her two short ones are toasts, a long one of ours stays in the status line
    c.js("window.scrollTo(0, 0)")          # the page is still down at the edit from "going back": a press right after a jump can land where the button was
    c.wait_for("window.scrollY === 0", 3)
    click_chip(c, V1)
    c.click("#startBtn")
    c.js("window.__post = window.Talk.post; window.Talk.post = function(){ return Promise.resolve({code: 200, j: {ok: false, why: 'pc', words: %s}}); }" % json.dumps(TR.line_for("pc")))
    c.click("#startBtn")
    c.wait_for("document.getElementById('status').classList.contains('bad') && document.getElementById('status').textContent.indexOf('PC') > 0", 10, tell="document.getElementById('status').textContent")
    poll(c)
    poll(c, True)
    time.sleep(0.4)
    case("a computer that can't turn talking into words: Edit my video's answer stays in the status line, in red, through a refresh (not a toast gone in 2.6 s)",
         status(c) == TR.line_for("pc") and c.js("!document.getElementById('startBtn').disabled") and s.rec(KIT)["video"] == V2, status(c))
    c.js("window.Talk.post = function(){ return Promise.resolve({code: 409, j: {ok: false, why: 'working', words: %s}}); }" % json.dumps(W["job_still_working"]))
    c.click("#startBtn")
    c.click("#startBtn")
    c.wait_for("document.getElementById('toast').textContent === %s" % json.dumps(W["job_still_working"]), 5, tell="document.getElementById('toast').textContent")
    case("her short \"I'm still working on the last one...\" is a toast, as hers", toast(c) == W["job_still_working"] and status(c) != W["job_still_working"], (toast(c), status(c)))
    c.js("window.Talk.post = window.__post")
    click_chip(c, V2)
    case("...and picking a video clears the line that stayed", status(c) == TR.line_for("refused"), status(c))
    # a video still copying in
    part = kit / "Talking" / "coming in.mp4"
    part.write_bytes(FIXTURE.read_bytes()[:9000])
    poll(c)
    try:
        c.wait_for("!document.getElementById('coming').hidden", 8)
        case("a video still being copied in is named under the row (ours) and can't be picked yet",
             c.text("#coming") == W["coming"].replace("{name}", "coming in.mp4") and "coming in.mp4" not in [x[0] for x in chips(c)], c.text("#coming"))
    except chrome_drive.Timeout:
        skip("a video still copying in: this computer's listing didn't hold it back")
    part.unlink()
    s.says(words=WORDS2)


def check_unreached(c, s):
    """The Assistant can't be reached as the page opens: plain words, nothing broken."""
    c.clear_errors()
    c.block_urls(["*talking-state*"])
    try:
        c.open(s.url("/talking.html" + s.q(EMPTY_KIT)))
        c.wait_for("document.getElementById('status').textContent.length > 0", 10)
        case("the state can't be fetched as the page opens: the status line says so in plain words, in red; nothing is shown as if empty",
             status(c) == s.tp.OUR_WORDS["cant_reach"][0] and c.js("document.getElementById('status').classList.contains('bad') && !window.Talk.loaded"), status(c))
        c.click("#whoAsst")
        c.click("#whoMe")
        time.sleep(0.4)
        case("...and nothing can be saved over a record the page never saw", s.rec(EMPTY_KIT) is None)
        case("...nor does I'll add them say a choice was made that was not (no toast, nothing lit)",
             toast(c) == "" and c.js("!document.getElementById('whoMe').classList.contains('on') && document.getElementById('placeAsk').hidden"), toast(c))
    finally:
        c.block_urls([])


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--only", choices=("s1", "script", "preview", "words"), help="one part")
    ap.add_argument("--no-chrome", action="store_true", help="the routes only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    real_before = real_listing()
    keep = bool(a.work)
    base = Path(a.work).resolve() if a.work else None
    if base:
        base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="talking-page-check-", dir=str(base) if base else ("/private/tmp" if MAC else None))).resolve()
    s = Setup(work, a.port)
    s.make()
    try:
        if a.only in (None, "words"):
            group("her words", check_words, s)
        if a.only in (None, "s1"):
            group("the page as built", check_built, s)
            s.start()
            case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
            group("the routes", check_routes, s)
            if a.no_chrome or not chrome_drive.find_chrome():
                skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
            else:
                with chrome_drive.Chrome(work=str(work), size=(1280, 1100)) as c:
                    group("step 1 on the page", check_page, c, s)
                    group("the Assistant out of reach", check_unreached, c, s)
        if a.only in (None, "script"):
            import talking_page_script as tps
            me = sys.modules[__name__]
            if s.proc is None:
                s.start()
                case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
            group("the script and the pickers, by request", tps.run_requests, me, s)
            if a.no_chrome or not chrome_drive.find_chrome():
                skip("the script on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
            else:
                with chrome_drive.Chrome(work=str(work / "chrome2"), size=(1280, 1100)) as c:
                    group("the script and the pickers on the page", tps.run_page, me, c, s)
        if a.only in (None, "preview"):
            import talking_page_preview as tpp
            me = sys.modules[__name__]
            if s.proc is None:
                s.start()
                case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
            group("the preview, by request", tpp.run_requests, me, s)
            if a.no_chrome or not chrome_drive.find_chrome():
                skip("the preview on the page: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
            else:
                with chrome_drive.Chrome(work=str(work / "chrome3"), size=(1280, 1100)) as c:
                    group("the preview on the page", tpp.run_page, me, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        case("the real Assistant folder on this computer is exactly as it was", real_listing() == real_before)
        if not keep and not [1 for _n, ok in chrome_drive._results if not ok]:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
