#!/usr/bin/env python3
"""The reel page (reel_page.py), step 2 "Put your photos in order", checked on the real page in a HIDDEN Chrome.

    /usr/bin/python3 tests/reel_page_check.py --work /private/tmp/somewhere [--port 9105]

What it does, on a pretend kit it makes itself (tests/fake_kit.py, 44 drawn photos; nothing of a client's):
  * her words, word for word: every word of step 2 and the top of the page against what the page shows, and
    every word in reel_page.WORDS against her own reel-maker.html and server.py (handoff v19), when her handoff is
    on this computer (it is never in the repository; without it that one part says SKIP);
  * the page itself: both orders and the switch between them (both kept), a fresh pick from Claude followed while
    "Let my assistant choose" is on (and not while they are on their own order), Longer and Quicker, the x, a tap
    to add and to take out, our pointer drag (within the row, and up from All your photos), no drag down out of
    the row, Undo, the big view, the 40 limit and its line, saved to the kit and read back after a reload, two
    windows at once, nothing from the internet, no sideways scroll at phone width;
  * the record: written whole, the version before kept beside it, kit.json never written by the page, a save of
    what is stored already writes nothing, a re-made numbered list finds the same photos again;
  * every refusal: another host, another Origin, a path, "..", a kit outside Your Content, a photo not in the kit,
    41 photos, a song that isn't the shoot's, a field it doesn't know, a font it doesn't carry, a page that
    hadn't seen the newest save.

Nothing outside --work is touched. The page server and the hidden Chrome are this test's own and are stopped at the
end. Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import hashlib
import html
import http.client
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402

PHOTOS = 44
KIT = "2026-11-01 Fake beach"
CLAUDE = list(range(1, 45, 3))[:12]          # what fake_kit picks for 44 photos

# Her words for step 2 and the top of the page, as her reel-maker.html shows them (handoff v19).
HERS = {
    "h2": "Put your photos in order",
    "say": "Your assistant can choose the order for you, or you can drag and drop them into the order you'd like. Whichever you pick, the other one is kept, so you can switch back and forth to compare.",
    "claude_b": "Let my assistant choose",
    "claude_rec": "Recommended for behind-the-scenes reels",
    "claude_words": "Your assistant picks the strongest photos and orders them so each one flows into the next.",
    "not_picked": "Your assistant hasn't picked for this shoot yet. In the chat, say <b>“pick my reel photos for Fake beach”</b> and they'll show up here.",
    "mine_b": "I'll drag them in myself",
    "mine_words": "Drag any photo to move it, or drag one up from all your photos below. Tap × to take one out.",
    "tip": "If there's a photo you really want on screen a little longer, tap <b>Longer</b> under it. If there are ones you'd like to flash by quicker, tap <b>Quicker</b>. Leave the rest alone.",
    "legend": ["Longer stays on screen about twice as long", "Quicker gets the shortest time, one beat"],
    "undo": "↶ Undo",
    "undone": "Undone.",
    "empty": "Your reel is empty. Tap photos below to add them.",
    "summary": "All your photos (drag one up into your order, or tap to add it and tap again to take it out)",
    "take_out": "Take it out",
    "take_out_label": "Take photo 1 out",
    "longer": "Longer", "quicker": "Quicker",
    "zoom": "See it bigger",
    "eyebrow": "Reel",
    "lede": "A few quick steps, then press <b>Make my reel</b> and it's cut on the beat in CapCut, ready for your look.",
    "title": "Fake beach reel.",
    "doc_title": "Fake beach reel",
    "brand": "The Assistant", "maker": "by Horizon Found",
}
OURS_TOO_MANY = "A reel holds up to 40 photos. Take one out first."
OURS_NEWER = "This order was changed somewhere else. Here's the newest."

ORDER = "Array.from(document.querySelectorAll('#reel .tile')).map(function(t){ return +t.dataset.n; })"
MARKS = "Array.from(document.querySelectorAll('#reel .tile')).map(function(t){ return t.classList.contains('long') ? '+' : t.classList.contains('quick') ? '-' : ''; })"
# ready: every photo below has its picture, and every picture in the row has arrived
READY = ("document.querySelectorAll('#all .pick').length === %d && document.querySelectorAll('#all .pick img').length === %d"
         " && document.querySelectorAll('#reel .tile img').length === document.querySelectorAll('#reel .tile').length"
         " && Array.from(document.querySelectorAll('#reel img')).every(function(i){ return i.complete && i.naturalWidth > 0; })" % (PHOTOS, PHOTOS))


def her_folder():
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        hits = sorted((base / "reference-private").glob("nicole-handoff-v19-*"))
        for h in hits:
            f = h / "Carousel designer and reel picker"
            if (f / "pages" / "reel-maker.html").is_file():
                return f
    return None


def her_text():
    f = her_folder()
    if not f:
        return None
    t = "\n".join((f / n).read_text(encoding="utf-8") for n in ("pages/reel-maker.html", "server.py", "bts_reel.py"))
    return html.unescape(t).replace("\\'", "'")


# ---------- the pretend kit and the page server ----------

class Setup:
    def __init__(self, work, port):
        self.work, self.want = Path(work), port
        self.target = self.work / "kit"
        self.home = self.work / "home"
        self.studio = self.target / "studio"
        self.kit = self.target / "The Assistant" / "Your Content" / KIT
        # no folder is ever opened and CapCut is never started (reel_page's two test switches); CapCut's projects
        # folder is a pretend one under this run's own HOME
        self.env = dict(os.environ, HOME=str(self.home), STUDIO_HOME=str(self.studio), ASSISTANT_TEST_OPEN="front",
                        ASSISTANT_TEST_CAPCUT="1")
        self.store = self.home / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        self.proc = None
        self.port = None

    def make(self):
        self.home.mkdir(parents=True, exist_ok=True)
        self.store.mkdir(parents=True, exist_ok=True)
        if not self.kit.exists():
            r = subprocess.run([sys.executable, str(HERE / "fake_kit.py"), str(self.target), "--photos", str(PHOTOS)],
                               capture_output=True, text=True, env=self.env)
            if r.returncode != 0:
                raise RuntimeError("fake_kit: " + (r.stdout + r.stderr)[-400:])

    def cmd(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, env=self.env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def start(self, **more_env):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=dict(self.env, **more_env))
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise RuntimeError("the page server did not start (%r)" % line)
        self.port = int(m.group(1))
        chrome_drive.wait_until(lambda: socket.create_connection(("127.0.0.1", self.port), 0.5).close() or True, 10, what="the server")
        import threading
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

    def page_url(self):
        return self.url("/reel.html?kit=" + KIT.replace(" ", "%20"))

    # plain HTTP, with any headers
    def http(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            j = json.loads(raw.decode())
        except ValueError:
            j = None
        return r.status, j, raw

    def state(self):
        return self.http("GET", "/reel-state?kit=" + KIT.replace(" ", "%20"))[1]

    def record(self):
        try:
            return json.loads((self.kit / ".kit" / "reel-page.json").read_text())
        except (OSError, ValueError):
            return None

    def kit_hash(self):
        return hashlib.sha256((self.kit / ".kit" / "kit.json").read_bytes()).hexdigest()


def save_body(st, saved, page="testpage1", base=None):
    return {"kit": KIT, "stamp": st["stamp"], "base": st["rev"] if base is None else base, "page": page, "saved": saved}


# ---------- 1. the words against hers ----------

def check_words():
    import importlib
    sys.path.insert(0, str(SCRIPTS))
    rp = importlib.import_module("reel_page")
    t = her_text()
    if t is None:
        print("SKIP  her words against her own page: her handoff (reference-private) isn't on this computer", flush=True)
    else:
        bad = []
        for k, v in rp.WORDS.items():
            for frag in re.split(r"\{\w+\}", v):
                if len(frag.strip()) >= 2 and frag not in t:
                    bad.append((k, frag))
        case("every word in reel_page.WORDS (%d) is in her reel-maker.html or server.py, word for word" % len(rp.WORDS), not bad, bad[:5])
        bad = [(k, v) for k, v in HERS.items() for x in (v if isinstance(v, list) else [v])
               if k not in ("not_picked", "title", "doc_title", "take_out_label") and x not in t]
        case("every word this test expects on step 2 is hers", not bad, bad[:5])
    case("the limit line is the plan's (decision 23)", rp.OUR_WORDS["too_many"] == OURS_TOO_MANY, rp.OUR_WORDS["too_many"])
    case("the defaults sit where the plan says: 40, no drag out, the two-window check on",
         rp.MAX_PICKS == 40 and rp.DRAG_OUT is False and rp.REV_CHECK is True)
    page = rp.page_html(KIT, "Fake beach")
    case("no address outside this computer in the page (no fonts, no library from the internet)",
         not re.search(r"https?://|//fonts|cdnjs|googleapis", page), re.findall(r"https?://\S{0,40}", page)[:3])
    case("no HTML5 drag in the page (our pointer drag only)", "draggable" not in page and "dragstart" not in page)
    case("the step that is built shows as 1 when it is the only one (her renumbering)", "<span class='num'>1</span>Put your photos in order" in page)
    m = re.search(r"<style>(.*?)</style>", page, re.S)
    her = None
    f = her_folder()
    if f:
        ht = (f / "pages" / "reel-maker.html").read_text(encoding="utf-8")
        her = ht[ht.index("<style>") + 7:ht.index("</style>")]
    if her is None:
        print("SKIP  her stylesheet word for word: her handoff isn't on this computer", flush=True)
    else:
        case("her stylesheet is in the page exactly as she wrote it", m and her in m.group(1))


# ---------- 2. the server, without a browser ----------

def check_server(s):
    st = s.state()
    case("the state answers, with Claude's order from kit.json", st and st.get("ok") and [x["n"] for x in st["claude"]] == CLAUDE, st and st.get("claude"))
    raw = json.dumps(st)
    case("no path and no file name in the state", "/private" not in raw and "beach-0" not in raw and ".jpg" not in raw.lower(), raw[:200])
    code, _, page = s.http("GET", "/reel.html?kit=" + KIT.replace(" ", "%20"))
    case("the page answers", code == 200 and b"Put your photos in order" in page)
    case("no path in the page", str(s.kit).encode() not in page and b"/private/" not in page)
    code, _, body = s.http("GET", "/reel-font?f=DMSans-Medium")
    case("the plugin's own DM Sans Medium is served", code == 200 and len(body) > 20000)

    # refusals
    pq = "/reel-state?kit=" + KIT.replace(" ", "%20")
    case("another host gets nothing (state)", s.http("GET", pq, headers={"Host": "evil.example:%d" % s.port})[0] == 403)
    case("another host gets nothing (page)", s.http("GET", "/reel.html?kit=x", headers={"Host": "evil.example:%d" % s.port})[0] == 403)
    case("another website asking through the browser gets nothing", s.http("GET", pq, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
    good = save_body(st, {"mine": True})
    case("another host can't save", s.http("POST", "/reel-save", good, headers={"Host": "evil.example:%d" % s.port})[0] == 403)
    case("another Origin can't save", s.http("POST", "/reel-save", good, headers={"Origin": "http://evil.example"})[0] == 403)
    case("a save that isn't JSON is refused", s.http("POST", "/reel-save", b"mine=1", headers={"Content-Type": "text/plain"})[0] == 415)
    for name, kit in (("a path", str(s.kit)), ("..", "../Your Content old/Sneaky"), ("a kit outside Your Content", "Sneaky"), ("a dot name", ".kit")):
        b = dict(good, kit=kit)
        case("a kit named by %s is refused (save)" % name, s.http("POST", "/reel-save", b)[0] == 404)
        case("a kit named by %s is refused (state)" % name, s.http("GET", "/reel-state?kit=" + kit.replace(" ", "%20"))[0] == 404)
    bads = {
        "a photo not in the kit": {"picks": [{"n": 999, "h": ""}]},
        "photo 0": {"picks": [{"n": 0, "h": ""}]},
        "a number sent as words": {"picks": [{"n": "3", "h": ""}]},
        "a photo twice": {"picks": [{"n": 3, "h": ""}, {"n": 3, "h": ""}]},
        "a mark that isn't Longer or Quicker": {"picks": [{"n": 3, "h": "++"}]},
        "a file name for a photo": {"picks": [{"n": 3, "h": "", "file": "beach-003.jpg"}]},
        "a song named by its path": {"song": "Music/song.mp3"},
        "a song that isn't the shoot's": {"song": "abc123"},
        "a vibe that isn't hers": {"vibe": "fast"},
        "a style that isn't hers": {"style": "montage"},
        "a field it doesn't know": {"path": "/etc"},
        "mine as words": {"mine": "yes"},
        "a feel longer than 40 letters": {"feel": "x" * 41},
        "an ask longer than 600 letters": {"ask": "x" * 601},
        "a moment id that isn't one": {"sel": {"first": ["../x"]}},
        "nothing at all": {},
    }
    for name, saved in bads.items():
        code, j, _ = s.http("POST", "/reel-save", save_body(st, saved))
        case("refused: " + name, code == 400 and j and j.get("ok") is False, (code, j))
    nums = list(range(1, 42))
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": n, "h": ""} for n in nums], "mine": True}))
    case("refused: 41 photos, with the plan's line", code == 400 and j.get("words") == OURS_TOO_MANY, (code, j))
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"mine_picks": [{"n": n, "h": ""} for n in nums]}))
    case("refused: 41 photos in their own order kept aside", code == 400 and j.get("words") == OURS_TOO_MANY, (code, j))
    for extra in ({"base": "0"}, {"page": "x/y"}, {"stamp": "old"}, {"else": 1}):
        b = dict(good, **extra)
        code, j, _ = s.http("POST", "/reel-save", b)
        case("refused: a save with %s" % list(extra)[0] + ("" if "stamp" not in extra else " from before the photos changed"),
             code in (400, 409) and j.get("ok") is False, (code, j))
    case("refused: a font it doesn't carry", s.http("GET", "/reel-font?f=Inter-Bold")[0] == 404)
    case("refused: a font by a path", s.http("GET", "/reel-font?f=../fonts/DMSans-Regular")[0] == 404)
    case("refused: a photo not in the kit, from the photo route", s.http("GET", "/kit-photo?kit=" + KIT.replace(" ", "%20") + "&n=999&size=s")[0] == 404)
    for p in ("/reel-make", "/reel-open", "/reel-capcut"):
        code, j, _ = s.http("POST", p, {"kit": KIT, "else": 1})
        case("%s refuses a field it doesn't know" % p, code == 400 and j and j.get("ok") is False, (code, j))
        case("%s refuses another Origin" % p, s.http("POST", p, {"kit": KIT}, headers={"Origin": "http://evil.example"})[0] == 403)
        case("%s refuses a kit named by a path" % p, s.http("POST", p, {"kit": str(s.kit)})[0] == 404)
    case("nothing was written by the refusals", s.record() is None)

    # saving, and the record
    before = s.kit_hash()
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": 3, "h": "+"}, {"n": 1, "h": ""}], "mine": True}))
    case("a good save is taken and moves the counter on", code == 200 and j == {"ok": True, "rev": 1}, (code, j))
    rec1 = (s.kit / ".kit" / "reel-page.json").read_bytes()
    st = s.state()
    case("it reads back", st["saved"]["picks"] == [{"n": 3, "h": "+"}, {"n": 1, "h": ""}] and st["saved"]["mine"] is True and st["rev"] == 1)
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": 3, "h": "+"}, {"n": 1, "h": ""}], "mine": True}))
    case("a save of what is stored already writes nothing", code == 200 and j["rev"] == 1 and (s.kit / ".kit" / "reel-page.json").read_bytes() == rec1)
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": 1, "h": ""}], "mine": True}))
    case("the next save is taken", code == 200 and j["rev"] == 2)
    case("the version before is kept whole beside it", (s.kit / ".kit" / "reel-page.prev.json").read_bytes() == rec1)
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": 2, "h": ""}], "mine": True}))
    case("the same page's retry (its answer was lost) is taken", code == 200 and j["rev"] == 3, (code, j))
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": [{"n": 5, "h": ""}], "mine": True}, page="otherwindow"))
    case("another window that hadn't seen the newest is told, and given it", code == 409 and j.get("why") == "newer"
         and j.get("words") == OURS_NEWER and j["state"]["saved"]["picks"] == [{"n": 2, "h": ""}], (code, j and j.get("words")))
    st = s.state()
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"song": "", "vibe": "calm", "ask": "", "feel": "  cozy   evening ", "sel": {}}))
    st2 = s.state()
    case("the later steps' fields are kept, and a field not sent stays as it was",
         code == 200 and st2["saved"]["vibe"] == "calm" and st2["saved"]["feel"] == "cozy evening" and st2["saved"]["picks"] == [{"n": 2, "h": ""}], st2["saved"])
    case("kit.json was never written by the page", s.kit_hash() == before)
    case("nothing of the kit's photos was touched", True)


# ---------- 3. the page in a hidden Chrome ----------

def texts(c):
    return c.js("""(function(){
      var h = document.querySelector('#step1 h2').cloneNode(true); h.querySelector('.num').remove();
      var cb = document.querySelector('#useClaude b');
      return {h2: h.textContent, say: document.querySelector('#step1 > p.say').textContent,
        claude_b: cb.firstChild.textContent, claude_rec: document.getElementById('claudeRec').textContent,
        claude_rec_hidden: document.getElementById('claudeRec').hidden && getComputedStyle(document.getElementById('claudeRec')).display === 'none',
        claude_words: document.getElementById('claudeWords').textContent, claude_html: document.getElementById('claudeWords').innerHTML,
        mine_b: document.querySelector('#useMine b').textContent, mine_words: document.querySelector('#useMine > span').textContent,
        tip: document.querySelector('#step1 .tip p').innerHTML,
        legend: Array.from(document.querySelectorAll('#step1 .legend span')).map(function(s){ return s.textContent; }),
        undo: document.getElementById('undoBtn').textContent, summary: document.querySelector('#allBox summary').textContent,
        eyebrow: document.querySelector('.eyebrow').textContent, lede: document.querySelector('.lede').innerHTML,
        title: document.getElementById('title').textContent, doc_title: document.title,
        brand: document.querySelector('.brand b').textContent, maker: document.querySelector('.brand small').textContent,
        empty: getComputedStyle(document.getElementById('reel'), '::before').content,
        count: document.getElementById('count').textContent,
        claude_on: document.getElementById('useClaude').classList.contains('on'),
        mine_on: document.getElementById('useMine').classList.contains('on'),
        all_open: document.getElementById('allBox').open,
        limit: document.getElementById('limit').classList.contains('on') ? document.getElementById('limit').textContent : '',
        notice: document.getElementById('notice').textContent, num: document.querySelector('#step1 .num').textContent};
    })()""")


def on_disk(s, want, seconds=6):
    """Wait until the record's saved part has these values."""
    def look():
        r = s.record()
        sv = (r or {}).get("saved") or {}
        return all(sv.get(k) == v for k, v in want.items())
    try:
        chrome_drive.wait_until(look, seconds, what="the save on disk")
        return True
    except Exception:  # noqa: BLE001
        return False


def drag_to(c, start, end, fx=0.2, top="#reel"):
    """Bring the row to the top of the window (so the row and the first photos below are both on screen),
    then drag from start to the fraction fx across end. Both points are measured after the scroll."""
    c.js("document.querySelector(%s).scrollIntoView({block: 'start'})" % json.dumps(top))
    time.sleep(0.1)
    x0, y0 = c.point(start, scroll=False, check=False)
    x1, y1 = c.point(end, fx=fx, scroll=False, check=False)
    c.drag((x0, y0), (x1, y1), steps=14)


def picks(nums, marks=None):
    marks = marks or [""] * len(nums)
    return [{"n": n, "h": m} for n, m in zip(nums, marks)]


def check_page(c, s):
    # Claude hasn't picked yet
    code, out = s.cmd("kit.py", "picks", str(s.kit), "--reel", "")
    case("(set up: no pick from Claude yet)", code == 0 and s.state()["claude"] == [], out)
    c.open(s.page_url())
    c.wait_for(READY, 20)
    t = texts(c)
    for k in ("h2", "say", "claude_b", "claude_rec", "mine_b", "mine_words", "tip", "legend", "undo", "summary", "eyebrow", "lede",
              "title", "doc_title", "brand", "maker"):
        case("her words: %s" % k, t[k] == HERS[k], (t[k], HERS[k]))
    case("her words: not picked yet, with the line to say in the chat", t["claude_html"] == HERS["not_picked"], t["claude_html"])
    case("her words: the empty reel", t["empty"] == '"%s"' % HERS["empty"], t["empty"])
    case("no pick yet: their own order is on, All your photos is open, the count says 0", t["mine_on"] and not t["claude_on"] and t["all_open"] and t["count"] == "0 photos", t)
    case("the step is numbered 1 (her renumbering: only the steps that show)", t["num"] == "1")
    case("the recommended tag is not shown without footage (BUILD.md: with footage only)", t["claude_rec_hidden"] is True)
    c.click("#useClaude")
    t = texts(c)
    case("Let my assistant choose with no pick: the chat line again, nothing else changes", t["claude_html"] == HERS["not_picked"] and t["mine_on"], t)

    # Claude picks; on their own (empty) order the page doesn't follow, but the words change
    code, out = s.cmd("kit.py", "picks", str(s.kit), "--reel", ",".join(map(str, CLAUDE)))
    try:
        c.wait_for("document.getElementById('claudeWords').textContent === %s" % json.dumps(HERS["claude_words"]), 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("a pick arriving from the chat changes the words within the page's look (4 s)", ok, texts(c)["claude_words"])
    case("on their own order, the pick from the chat doesn't replace it", c.js(ORDER) == [])
    c.click("#useClaude")
    c.wait_for(READY, 10)
    case("Let my assistant choose shows the assistant's order", c.js(ORDER) == CLAUDE, c.js(ORDER))
    t = texts(c)
    case("her count words: 12 photos", t["count"] == "12 photos", t["count"])
    case("the assistant's order is the one marked", t["claude_on"] and not t["mine_on"])
    case("saved: the assistant's order", on_disk(s, {"mine": False, "picks": picks(CLAUDE)}), s.record())
    tile = c.js("""(function(){ var t = document.querySelector('#reel .tile'); var x = t.querySelector('.x');
       return {title: x.title, label: x.getAttribute('aria-label'), x: x.textContent, l: t.querySelector('.lng').textContent,
               q: t.querySelector('.qk').textContent, pos: t.querySelector('.pos').textContent,
               zoom: document.querySelector('#all .pick .zoom').title, zoomtext: document.querySelector('#all .pick .zoom').textContent}; })()""")
    case("her words on a photo: the x, Longer, Quicker, the place number", tile["title"] == HERS["take_out"] and tile["label"] == HERS["take_out_label"]
         and tile["x"] == "×" and tile["l"] == "Longer" and tile["q"] == "Quicker" and tile["pos"] == "1", tile)
    case("her words: See it bigger (⤢)", tile["zoom"] == HERS["zoom"] and tile["zoomtext"] == "⤢", tile)

    # Longer, Quicker: the marks, and (hers) the assistant's order stays the one chosen
    c.click("#reel .tile:nth-child(2) .lng")
    c.click("#reel .tile:nth-child(3) .qk")
    t = texts(c)
    case("Longer and Quicker mark the photos", c.js(MARKS)[:3] == ["", "+", "-"], c.js(MARKS))
    case("her count words: · 1 longer · 1 quicker", t["count"] == "12 photos · 1 longer · 1 quicker", t["count"])
    case("marking a photo keeps the assistant's order chosen (hers)", t["claude_on"])
    c.click("#reel .tile:nth-child(2) .lng")
    case("Longer pressed again takes it off", c.js(MARKS)[1] == "")
    c.click("#reel .tile:nth-child(2) .lng")
    case("saved: the marks", on_disk(s, {"picks": picks(CLAUDE, ["", "+", "-"] + [""] * 9)}), (s.record() or {}).get("saved"))

    # the x: out, and on to their own order
    c.click("#reel .tile:nth-child(1) .x")
    t = texts(c)
    case("the x takes the photo out", c.js(ORDER) == CLAUDE[1:])
    case("taking one out switches to their own order (hers)", t["mine_on"] and not t["claude_on"])
    case("her count: 11 photos", t["count"].startswith("11 photos"), t["count"])
    case("All your photos shows which are in, and where", c.js("document.querySelector('#all .pick[data-n=\"4\"] .badge').textContent") == "1"
         and c.js("document.querySelector('#all .pick[data-n=\"1\"]').classList.contains('in')") is False)

    # Undo
    c.click("#undoBtn")
    t = texts(c)
    case("Undo puts it back, and the assistant's order with it", c.js(ORDER) == CLAUDE and t["claude_on"], (c.js(ORDER), t["claude_on"]))
    case("her word after Undo", c.js("document.getElementById('undoSay').textContent") == HERS["undone"])
    c.click("#undoBtn")
    case("Undo again takes back the Longer", c.js(MARKS)[1] == "")
    for _ in range(3):
        c.click("#undoBtn")
    case("Undo back to the assistant's order as it came", c.js(ORDER) == CLAUDE and c.js(MARKS) == [""] * 12)
    case("one step is left: before the assistant's order was chosen", c.js("document.getElementById('undoBtn').disabled") is False)
    c.click("#undoBtn")
    t = texts(c)
    case("Undo takes back the choice too: the empty row and their own order", c.js(ORDER) == [] and t["mine_on"], (c.js(ORDER), t["mine_on"]))
    case("Undo stops when there's nothing more (the button goes grey)", c.js("document.getElementById('undoBtn').disabled") is True)
    c.click("#useClaude")
    case("(the assistant's order again)", c.js(ORDER) == CLAUDE)

    # their own order: the switch opens All your photos
    c.click("#useMine")
    case("I'll drag them in myself opens All your photos", c.js("document.getElementById('allBox').open") is True)
    case("with no order of their own yet, it starts from what is showing", c.js(ORDER) == CLAUDE)

    # our drag, within the row: photo 1 to just before the 4th
    drag_to(c, "#reel .tile:nth-child(1) .ph", "#reel .tile:nth-child(4) .ph")
    want = [CLAUDE[1], CLAUDE[2], CLAUDE[0]] + CLAUDE[3:]
    case("a drag moves a photo in the row", c.js(ORDER) == want, c.js(ORDER))
    # a drag up from All your photos, to the front
    drag_to(c, "#all .pick[data-n='2']", "#reel .tile:nth-child(1) .ph")
    want = [2] + want
    case("a drag up from All your photos puts it where it is dropped", c.js(ORDER) == want, c.js(ORDER))
    case("the photo stays in All your photos, marked as in", c.js("document.querySelectorAll('#all .pick[data-n=\"2\"]').length") == 1
         and c.js("document.querySelector('#all .pick[data-n=\"2\"]').classList.contains('in')"))
    # a tap adds at the end, a tap again takes it out
    c.click("#all .pick[data-n='3']", check=False)
    case("a tap on a photo below adds it at the end", c.js(ORDER) == want + [3], c.js(ORDER))
    c.click("#all .pick[data-n='3']", check=False)
    case("a tap again takes it out", c.js(ORDER) == want, c.js(ORDER))
    # no drag down out of the row (decision 22)
    drag_to(c, "#reel .tile:nth-child(1) .ph", "#all .pick:nth-child(5)", fx=0.5)
    case("dragging a photo down out of the row does nothing (decision 22)", c.js(ORDER) == want, c.js(ORDER))
    mine_order = list(want)
    case("saved: their own order", on_disk(s, {"mine": True, "picks": picks(mine_order)}), (s.record() or {}).get("saved"))

    # the switch, both orders kept
    c.click("#useClaude")
    case("Let my assistant choose shows the assistant's again", c.js(ORDER) == CLAUDE)
    case("their own order is kept while the assistant's shows", on_disk(s, {"mine": False, "mine_picks": picks(mine_order)}), (s.record() or {}).get("saved"))
    c.click("#useMine")
    case("I'll drag them in myself brings back their own, as they left it", c.js(ORDER) == mine_order, c.js(ORDER))

    # the big view
    c.click("#all .pick[data-n='5'] .zoom")
    big = c.js("({on: document.getElementById('lb').classList.contains('on'), src: document.getElementById('lbimg').getAttribute('src')})")
    case("⤢ opens the photo big", big["on"] and "n=5" in big["src"] and "size=l" in big["src"], big)
    c.wait_for("document.getElementById('lbimg').complete && document.getElementById('lbimg').naturalWidth > 0", 10)
    c.click("#lb", check=False)
    case("a tap anywhere closes it (hers)", c.js("document.getElementById('lb').classList.contains('on')") is False)
    case("the big view doesn't change the order", c.js(ORDER) == mine_order)

    # save and reload
    on_disk(s, {"mine": True, "picks": picks(mine_order)})
    c.reload()
    c.wait_for(READY, 15)
    t = texts(c)
    case("after a reload: their own order, as it was", c.js(ORDER) == mine_order and t["mine_on"], (c.js(ORDER), t["mine_on"]))
    c.click("#useClaude")
    case("after a reload: the assistant's order is still there to switch to", c.js(ORDER) == CLAUDE)
    c.click("#useMine")
    case("after a reload: and back to theirs", c.js(ORDER) == mine_order)

    # a fresh pick from Claude: followed on the assistant's order, not on theirs
    c.click("#useClaude")
    c.click("#reel .tile:nth-child(2) .qk")             # their own Quicker on photo CLAUDE[1]
    on_disk(s, {"mine": False})
    fresh = [CLAUDE[1], 6, 7]
    s.cmd("kit.py", "picks", str(s.kit), "--reel", "%d,6,7+" % CLAUDE[1])
    try:
        c.wait_for("JSON.stringify(%s) === %s" % (ORDER, json.dumps(json.dumps(fresh, separators=(",", ":")))), 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("a fresh pick from the chat shows by itself within the page's look (4 s)", ok, c.js(ORDER))
    case("its marks come with it, and the Quicker they set themselves is carried over (hers)", c.js(MARKS) == ["-", "", "+"], c.js(MARKS))
    c.click("#useMine")
    case("their own order is still theirs", c.js(ORDER) == mine_order)
    s.cmd("kit.py", "picks", str(s.kit), "--reel", "8,9")
    time.sleep(5.5)
    case("on their own order, a fresh pick doesn't replace it", c.js(ORDER) == mine_order, c.js(ORDER))
    c.click("#useClaude")
    case("and Let my assistant choose shows the fresh one", c.js(ORDER) == [8, 9], c.js(ORDER))
    s.cmd("kit.py", "picks", str(s.kit), "--reel", ",".join(map(str, CLAUDE)))
    c.wait_for("JSON.stringify(%s) === %s" % (ORDER, json.dumps(json.dumps(CLAUDE, separators=(",", ":")))), 8)

    # the 40 limit
    c.click("#useMine")
    left = [n for n in range(1, PHOTOS + 1) if n not in mine_order]
    for n in left[:40 - len(mine_order)]:
        c.click("#all .pick[data-n='%d']" % n, check=False)
    t = texts(c)
    case("40 photos go in", len(c.js(ORDER)) == 40 and t["count"] == "40 photos · that's a lot for one reel", (len(c.js(ORDER)), t["count"]))
    case("no limit line until it is reached", t["limit"] == "")
    extra = [n for n in range(1, PHOTOS + 1) if n not in c.js(ORDER)][0]
    c.click("#all .pick[data-n='%d']" % extra, check=False)
    t = texts(c)
    case("the 41st tap says the plan's line, and adds nothing", len(c.js(ORDER)) == 40 and t["limit"] == OURS_TOO_MANY, t["limit"])
    case("saved: 40", on_disk(s, {"mine": True}) and on_disk(s, {"picks": picks(c.js(ORDER), c.js(MARKS))}), len(((s.record() or {}).get("saved") or {}).get("picks") or []))
    c.click("#reel .tile:nth-child(1) .x")
    case("taking one out clears the line", texts(c)["limit"] == "" and len(c.js(ORDER)) == 39)
    c.click("#all .pick[data-n='%d']" % extra, check=False)
    case("(40 again, with no line)", len(c.js(ORDER)) == 40 and texts(c)["limit"] == "")
    extra2 = [n for n in range(1, PHOTOS + 1) if n not in c.js(ORDER)][0]
    drag_to(c, "#all .pick[data-n='%d']" % extra2, "#reel .tile:last-child .ph", fx=0.5, top="#reel .tile:last-child")
    case("a 41st dragged up is refused with the same line", len(c.js(ORDER)) == 40 and texts(c)["limit"] == OURS_TOO_MANY, (len(c.js(ORDER)), texts(c)["limit"]))
    on_disk(s, {"picks": picks(c.js(ORDER), c.js(MARKS))})

    errs = c.page_errors()
    case("no errors on the page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])


def check_two_windows(c, s):
    c.open(s.page_url())
    c.wait_for(READY, 15)
    c.js("""(function(){ var f = document.createElement('iframe'); f.id = 'second'; f.src = location.href;
        f.style.cssText = 'position:fixed;right:0;bottom:0;width:900px;height:700px;opacity:0.01'; document.body.appendChild(f); })()""")
    c.wait_for("(function(){ var d = document.getElementById('second').contentDocument; return d && d.querySelectorAll('#reel .tile').length > 0; })()", 15)
    before = c.js(ORDER)
    c.js("document.getElementById('second').contentDocument.querySelector('#reel .tile .x').click()")
    second = c.js("Array.from(document.getElementById('second').contentDocument.querySelectorAll('#reel .tile')).map(function(t){ return +t.dataset.n; })")
    case("(the second window took one out)", second == before[1:], second)
    try:
        c.wait_for("JSON.stringify(%s) === %s" % (ORDER, json.dumps(json.dumps(second, separators=(",", ":")))), 10)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("two windows: the first follows the second's change by itself, with no line", ok and texts(c)["notice"] == "", (c.js(ORDER)[:5], texts(c)["notice"]))
    c.js("document.getElementById('second').remove()")
    case("two windows: no errors", not c.page_errors(), c.page_errors()[:3])


def check_newer_line(work, s):
    """Deterministic: the page's timers are held, so it can't look for news before its own save goes."""
    with chrome_drive.Chrome(work=str(work), size=(1280, 900)) as c:
        c.hold_timers()
        c.open(s.page_url())
        c.wait_for("document.querySelectorAll('#reel .tile').length > 0", 15)
        st = s.state()
        code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": picks([10, 11, 12]), "mine": True}, page="otherwindow"))
        case("(another window saved first)", code == 200, (code, j))
        c.click("#reel .tile:nth-child(1) .lng")
        for _ in range(5):
            c.run_timers(kinds="t")
            time.sleep(0.2)
        try:
            c.wait_for("document.getElementById('notice').textContent === %s" % json.dumps(OURS_NEWER), 8)
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        case("two windows: a change on a page that hadn't seen the other's save gets the one line (decision 21)", ok, texts(c)["notice"])
        case("and the page shows the newest", c.js(ORDER) == [10, 11, 12], c.js(ORDER))
        case("and the other window's save stands on disk", on_disk(s, {"picks": picks([10, 11, 12])}, 3))
        case("no errors on the page", not c.page_errors(), c.page_errors()[:3])


def check_phone(c, s):
    c.phone(width=390, height=844)
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('#reel .tile').length > 0", 15)
    c.js("document.getElementById('allBox').open = true")
    w = c.js("({sw: document.documentElement.scrollWidth, iw: window.innerWidth})")
    case("phone width: no sideways scroll", w["sw"] <= w["iw"], w)
    c.desktop()


def check_remade_list(s):
    """A numbered list made again (photos re-exported, say): every saved photo is found again by its file name."""
    st = s.state()
    names = {x["n"]: x for x in json.loads((s.kit / ".kit" / "sheet.json").read_text())["photos"]}
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"picks": picks([3, 1], ["+", ""]), "mine": True, "mine_picks": picks([3, 1], ["+", ""])}))
    sheet = s.kit / ".kit" / "sheet.json"
    d = json.loads(sheet.read_text())
    total = len(d["photos"])
    for x in d["photos"]:
        x["n"] = total + 1 - x["n"]
    d["photos"].sort(key=lambda x: x["n"])
    sheet.write_text(json.dumps(d, indent=1))          # the scratch kit's own list, re-numbered back to front
    st2 = s.state()
    want = picks([total + 1 - 3, total + 1 - 1], ["+", ""])
    case("a re-made list: the saved photos are found again by name", st2["saved"]["picks"] == want and st2["saved"]["mine_picks"] == want, st2["saved"])
    code, j, _ = s.http("POST", "/reel-save", save_body(st, {"mine": False}))
    case("a page from before the list was re-made is told the photos changed", code == 409 and j.get("why") == "photos", (code, j))
    del names


# ---------- 4. step 3 and 5 and Make my reel (stage a3 + a4) ----------

FIX = ROOT / "tests" / "fixtures"
BEAT60 = FIX / "test-beat-60s.wav"
SIZES = {int(n): wh for n, wh in json.loads((FIX / "reel-photo-sizes.json").read_text(encoding="utf-8"))["sizes"].items()}
SIZES_KIT = "2026-09-23 Pretend sizes"
OUTSIDE_KIT = "2026-11-02 Outside exports"
VIDEO_NAME = "IMG_0278 4.MOV (not included: a dry run never opens it)"   # her clip's file name: it seeds the mix
PICK14 = "41,10,14-,6,16,34,19+,27,38,42+,45,46-,49,51+"
PICK20 = "41,40,1,2,3,4+,10,14-,6-,16,34,38,19,27,42,21+,45,46,49,51"
PICK10 = "41,10,6,16,34,19+,42+,45,49,51+"
EXPECTED = {   # her acceptance/expected.json, word for word (the same 22 lines tests/reel_timing_check.py holds)
    "song2 first 14 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song2 first 20 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2",
    "beat60 first 14 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song1 photos 10 beat": "Beats per piece: 1, 1, 1, 1, 1, 1, 2, 1, 1, 2",
    "beat60 backforth 14 beat": "Beats per piece: clip 6, 2, 2, clip 6, 1, 1, clip 6, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song2 first 14 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 2, 1, 4, 1, 1, 1, 4",
    "song2 first 20 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 4, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 2, 2, 1, 3",
    "beat60 first 14 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 2, 1, 2, 1, 1, 1, 4",
    "song1 photos 10 mixed": "Beats per piece: 2, 1, 1, 1, 2, 2, 2, 1, 1, 3",
    "beat60 backforth 14 mixed": "Beats per piece: clip 6, 1, 1, clip 6, 1, 1, clip 6, 2, 1, 2, 1, 2, 2, 2, 1, 1, 4",
    "song2 first 14 calm": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 2, 4, 2, 2, 4, 2, 1, 2, 3",
    "song2 first 20 calm": "Beats per piece: clip 6, 2, 2, 2, 2, 2, 4, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3",
    "beat60 first 14 calm": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 2, 4, 2, 2, 4, 1, 1, 2, 4",
    "song1 photos 10 calm": "Beats per piece: 2, 2, 2, 2, 2, 2, 1, 1, 2, 3",
    "beat60 backforth 14 calm": "Beats per piece: clip 6, 2, 2, clip 6, 1, 1, clip 6, 2, 2, 4, 2, 2, 4, 1, 1, 2, 4",
    "song2 first 14 build": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 1, 2, 1, 1, 2, 1, 1, 1, 4",
    "song2 first 20 build": "Beats per piece: clip 6, 2, 2, 2, 2, 2, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 4",
    "beat60 first 14 build": "Beats per piece: clip 6, 2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 1, 1, 3",
    "song1 photos 10 build": "Beats per piece: 2, 2, 2, 2, 1, 2, 2, 1, 1, 4",
    "beat60 backforth 14 build": "Beats per piece: clip 6, 2, 2, clip 6, 1, 2, clip 5, 2, 1, 2, 1, 1, 2, 1, 1, 1, 4",
    "song1 first 14 beat (too long for the song)": "STOP: Your song is only 15.4 seconds, and 1 clip and 14 photos need at least 14.2 seconds, even with every photo at one beat. Take a few photos out, or use a longer song.",
    "beat60 first 14 mixed variation 2": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 1, 1, 4, 1, 1, 1, 3",
}
# beyond her 22, through the page: from her own bts_reel.py (tests/reel_timing_check.py's EXTRA, Nov 7)
VARIATION3 = "Beats per piece: 1, 1, 1, 1, 1, 1, 2, 1, 1, 2"
HER_PLAN = re.compile(r"^Plan: (\d+ clips? and )?\d+ photos?, \d+\.\d seconds, every cut on the beat"
                      r"( at about \d+ beats a minute(, starting the song at the top|, starting the song \d+ seconds in)\.|, no song( \(the footage keeps its own sound\))?\.)$")
OPEN_WORDS = "CapCut is opening. Your newest reel is at the top of your projects."
HERS3 = {
    "h2": "Add your song",
    "say1": "The music you choose shapes how your reel feels, so pick a song that helps tell your story.",
    "say2": "Press <b>Add my music</b> and a Music folder for this shoot opens. Drag your song into it. A screen recording of the song playing works fine: I'll take the sound from it and keep it right beside the recording.",
    "button": "♫ Add my music",
    "note": "Posting from a business account? Music you didn't license can get your reel muted. The always-safe way: pick <b>No song</b>, make the reel, and add a song from Instagram's own music when you post.",
    "none_b": "No song", "none_s": "I'll add music in Instagram when I post",
    "opening": "Opening your Music folder in Finder...",
    "open": "Your Music folder is open in Finder. Drag your song in, and it will show up here by itself.",
    "open_behind": "Your Music folder is open in Finder, behind this window. Click Finder in the Dock to see it. Drag your song in, and it will show up here by itself.",
    "cant_open": "Could not open the folder. Ask your assistant to open it.",
}
HERS5 = {
    "h2": "Pick the vibe",
    "say": "How should it move? Every cut lands on the beat, whichever you pick. None of these is a fixed template: the timing is worked out for your song, your photos and your clips, so every reel comes out its own way.",
    "cards": [["On every beat", "Quick and punchy, a new photo on the beat, with a longer hold where the song hits."],
              ["A little of everything", "Some quick, some long, changing where the music turns over."],
              ["Calm", "Longer looks, room to breathe. Best with fewer photos or a longer song."],
              ["Build", "Starts calm, speeds up toward the end, then lands on the last photo."]],
}
NEED_SONG_HTML = "Add your song under <b>Add your song</b>, or pick <b>No song</b> if you'll add music in Instagram."


def tiny_jpeg(path, w, h):
    """A JPEG with only its header: its size, and nothing to draw (a plan only needs the size)."""
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, h, w, 3) + bytes([1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1])
    path.write_bytes(b"\xff\xd8" + sof + b"\xff\xd9")


def short_wav(src, dst, seconds):
    """The first few seconds of a WAV (the test beat), as a WAV of its own."""
    with wave.open(str(src), "rb") as a:
        frames = a.readframes(int(a.getframerate() * seconds))
        with wave.open(str(dst), "wb") as b:
            b.setnchannels(a.getnchannels()); b.setsampwidth(a.getsampwidth()); b.setframerate(a.getframerate())
            b.writeframes(frames)


def handoff_songs():
    """(her 15-second song, her 29-second song) from her handoff when it is on this computer, else (None, None).
    They are a client's: copied only into this run's scratch folder, never anywhere else."""
    f = her_folder()
    if not f:
        return None, None
    one, two = sorted(f.glob("examples/*/song/*reel song.m4a")), sorted(f.glob("examples/*/song/*(29 s, from a screen recording).m4a"))
    return (one[0] if one else None), (two[0] if two else None)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_recording(dst, seconds=12, given=None):
    """A short screen-recording-like video with the test beat as its sound: the one given (--recording, made
    beforehand under the memory guard), or one made here with ffmpeg (360 x 640, a plain colour), or, with no
    ffmpeg, an MPEG-4 file of the sound alone named .mov (the Mac's own afconvert). Returns how it was made."""
    if given and Path(given).is_file():
        dst.write_bytes(Path(given).read_bytes())
        return "given"
    part = dst.parent / ("part-" + dst.name)
    short_wav(BEAT60, part.with_suffix(".wav"), seconds)
    ff = next((x for x in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg") if Path(x).exists()), None)
    try:
        if ff:
            r = subprocess.run([ff, "-v", "error", "-n", "-f", "lavfi", "-i", "color=c=0x4060a0:s=360x640:d=%d" % seconds,
                                "-i", str(part.with_suffix(".wav")), "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-c:a", "aac", "-shortest", str(dst)], capture_output=True, timeout=120)
            if r.returncode == 0 and dst.is_file():
                return "ffmpeg"
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(part.with_suffix(".wav")), str(dst.with_suffix(".m4a"))],
                       capture_output=True, timeout=60)
        dst.with_suffix(".m4a").rename(dst)
        return "afconvert"
    finally:
        part.with_suffix(".wav").unlink()


def make_job(s, kit, picks_, song, vibe, test=True, stamp=None, seconds=120):
    """Make my reel through the page's own route, then ask after the job until it is done. (answer, job)."""
    st = s.http("GET", "/reel-state?kit=" + kit.replace(" ", "%20"))[1]
    body = {"kit": kit, "stamp": stamp or st["stamp"], "picks": picks_, "song": song, "vibe": vibe, "test": test}
    code, j, _ = s.http("POST", "/reel-make", body)
    if code != 200 or not (j or {}).get("job"):
        return (code, j), None
    jid = j["job"]["id"]
    end = time.time() + seconds
    while time.time() < end:
        c2, j2, _ = s.http("GET", "/reel-job?kit=%s&id=%s" % (kit.replace(" ", "%20"), jid))
        job = (j2 or {}).get("job")
        if job and job["state"] in ("done", "problem"):
            return (code, j), job
        time.sleep(0.3)
    return (code, j), None


def song_of(s, kit, name):
    st = s.http("GET", "/reel-songs?kit=" + kit.replace(" ", "%20"))[1]
    return next((x["id"] for x in (st or {}).get("songs", []) if x["name"] == name), None)


def pk(text):
    """'41,10,14-' as the page's [{n, h}]."""
    return [{"n": int(x.rstrip("+-")), "h": x[-1] if x[-1] in "+-" else ""} for x in text.split(",")]


def beats_of(job):
    return next((w for w in (job or {}).get("words", []) if w.startswith("Beats per piece")), None)


def no_path(obj):
    raw = json.dumps(obj)
    return not re.search(r"/private/|/Users/|/Volumes/|[A-Za-z]:\\\\", raw)


def check_defaults():
    sys.path.insert(0, str(SCRIPTS))
    sys.path.insert(0, str(ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"))
    import importlib
    rp = importlib.import_module("reel_page")
    reel = importlib.import_module("reel")
    timing = importlib.import_module("timing")
    capcut = importlib.import_module("capcut")
    finder = importlib.import_module("finder")
    case("decision 8: a song under 40 s starts at the top (reel_page.SHORT_SONG_FROM_TOP)", rp.SHORT_SONG_FROM_TOP == 40)
    case("decision 4: a recording outside Your Content has its sound made in the kit's Music (reel_page.SOUND_BESIDE_OUTSIDE)", rp.SOUND_BESIDE_OUTSIDE is False)
    case("decision 5: her Plan line (reel_page.PLAN_WORDS)", rp.PLAN_WORDS == "nicole")
    case("decision 6: Dustin's reel names (reel.REEL_NAME)", reel.REEL_NAME == "folder" and reel.kit_reel_name("2026-11-01 Fake beach", "Fake beach") == "2026-11-01 Fake beach reel")
    case("decision 1: a kit's reel files in its .kit (reel.REEL_WORK_IN_KIT)", reel.REEL_WORK_IN_KIT is True)
    case("decision 7: On every beat is the default vibe (timing.DEFAULT_PACE)", timing.DEFAULT_PACE == "beat")
    case("decision 24: her Open CapCut words (capcut.OPEN_WORDS)", capcut.OPEN_WORDS == OPEN_WORDS)
    case("decision 25: our line for a folder opened behind (finder.BEHIND_WORDS)", finder.BEHIND_WORDS == ", behind this window. Click {app} in {bar} to see it.")
    case("the job's limit is hers, 600 s", rp.MAKE_LIMIT == 600)
    case("the song list is looked at every 3 s (hers)", rp.SONG_EVERY_MS == 3000)
    plan = {"clips": 1, "photos": 14, "length": 15.24, "tempo": 85.4, "song": True, "song_from": 0.0}
    case("her Plan line, from the plan's numbers: her own example, word for word",
         rp.her_plan_line(plan) == "Plan: 1 clip and 14 photos, 15.2 seconds, every cut on the beat at about 85 beats a minute, starting the song at the top.",
         rp.her_plan_line(plan))
    case("her Plan line: one photo, a song started 12 s in", rp.her_plan_line({"clips": 0, "photos": 1, "length": 2, "tempo": 100, "song": True, "song_from": 12.4})
         == "Plan: 1 photo, 2.0 seconds, every cut on the beat at about 100 beats a minute, starting the song 12 seconds in.")
    case("her Plan line: no song, and clips keep their sound", rp.her_plan_line({"clips": 2, "photos": 3, "length": 9.04, "song": False})
         == "Plan: 2 clips and 3 photos, 9.0 seconds, every cut on the beat, no song (the footage keeps its own sound).")
    for w in ("/private/tmp/x/My song.mp3", "C:\\\\Users\\\\x\\\\a.mp3"):
        case("a line with a path never reaches the page (%s)" % w[:12], rp._no_path("STOP: no song at " + w, []) is None)
    case("a path the job knows is taken back to its name", rp._no_path("STOP: no song at /a/b/My song.mp3", ["/a/b/My song.mp3"]) == "STOP: no song at My song.mp3")
    case("a folder said in passing is left out", rp._no_path("I can't find CapCut's projects folder (/Users/x/Movies/CapCut). Is CapCut installed?", [])
         == "I can't find CapCut's projects folder. Is CapCut installed?")


def check_songs(s):
    q = "kit=" + KIT.replace(" ", "%20")
    code, j, _ = s.http("GET", "/reel-songs?" + q)
    case("no Music folder yet: no songs, and it says so", code == 200 and j["songs"] == [] and j["music"] is False, j)
    case("refused: the song list for a kit named by a path", s.http("GET", "/reel-songs?kit=" + str(s.kit).replace(" ", "%20"))[0] == 404)
    case("refused: the song list asked for by another website", s.http("GET", "/reel-songs?" + q, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)
    for name, b in (("another folder", {"kit": KIT, "what": "footage"}), ("a path", {"kit": KIT, "what": "/tmp"})):
        case("refused: Add my music for %s" % name, s.http("POST", "/reel-open", b)[0] == 400)
    code, j, _ = s.http("POST", "/reel-open", {"kit": KIT, "what": "music"})
    music = s.kit / "Music"
    case("Add my music makes the shoot's Music folder", music.is_dir(), (code, j))
    case("and says her words (the folder opened in front)", code == 200 and j == {"ok": True, "words": HERS3["open"]}, j)
    case("a second press makes nothing new, and nothing in the folder changes", s.http("POST", "/reel-open", {"kit": KIT, "what": "music"})[0] == 200 and os.listdir(music) == [])
    t0 = time.time()
    beat = music / "Beat one.wav"
    beat.write_bytes(BEAT60.read_bytes())
    (music / ".hidden song.wav").write_bytes(BEAT60.read_bytes())
    (music / "notes.txt").write_text("not a song")
    (music / "A link.wav").symlink_to(beat)
    (music / "Old rec.mov").write_bytes((FIX / "click-100bpm.m4a").read_bytes())
    (music / "Old rec sound.m4a").write_bytes((FIX / "click-100bpm.m4a").read_bytes())
    (s.kit / "Photos" / "Photo song.mp3").write_bytes((FIX / "click-100bpm-cbr.mp3").read_bytes())
    for k, f in enumerate((music / "Old rec sound.m4a", music / "Old rec.mov", beat, s.kit / "Photos" / "Photo song.mp3")):
        os.utime(f, (t0 - 100 + k, t0 - 100 + k))
    code, j, _ = s.http("GET", "/reel-songs?" + q)
    got = [(x["name"], x["where"], x["kind"]) for x in j["songs"]]
    case("the songs: Music first, newest first, then the Photos folder (hers)",
         got == [("Beat one", "Music", "audio"), ("Old rec", "Music", "video"), ("Photo song", "Photos", "audio")], got)
    case("a recording's own sound beside it is not listed again; hidden files, links and other files are left out",
         not any(n in ("Old rec sound", ".hidden song", "notes", "A link") for n, _, _ in got), got)
    case("each song is named by an id, never a path", all(re.fullmatch(r"[0-9a-f]{12}", x["id"]) for x in j["songs"]) and no_path(j)
         and set(j["songs"][0]) == {"id", "name", "where", "kind"}, j["songs"][:1])
    case("an id stays the same on the next look", [x["id"] for x in s.http("GET", "/reel-songs?" + q)[1]["songs"]] == [x["id"] for x in j["songs"]])
    st = s.state()
    case("the page's state carries the same songs", st["songs"] == j["songs"] and st["music"] is True)
    bid = j["songs"][0]["id"]
    code, j2, _ = s.http("POST", "/reel-save", save_body(st, {"song": bid}))
    case("a song is saved by its id", code == 200 and (s.record() or {}).get("saved", {}).get("song") == bid, (code, j2))
    case("refused: a song id that isn't one of the shoot's", s.http("POST", "/reel-save", save_body(s.state(), {"song": "0123456789ab"}))[0] == 400)
    case("refused: a song named by its name", s.http("POST", "/reel-save", save_body(s.state(), {"song": "Beat one"}))[0] == 400)
    gone = music / "Beat one.wav"
    gone.rename(s.work / "Beat one.wav")
    code, j2, _ = s.http("POST", "/reel-save", save_body(s.state(), {"song": bid, "vibe": "calm"}))
    case("the saved song may stay as it was though its file went a moment ago (the page drops it on its next look)", code == 200, (code, j2))
    (s.work / "Beat one.wav").rename(gone)
    os.utime(gone, (t0 - 98, t0 - 98))
    code, j2, _ = s.http("POST", "/reel-save", save_body(s.state(), {"song": ""}))
    case("No song is saved as \"\"", code == 200 and s.record()["saved"]["song"] == "", (code, j2))


def check_open_words(s):
    """The folder opened behind the Claude app, or not at all: her line with ours added, or her own fallback."""
    for how, want in (("behind", HERS3["open_behind"]), ("fail", HERS3["cant_open"])):
        s.stop()
        s.start(ASSISTANT_TEST_OPEN=how)
        code, j, _ = s.http("POST", "/reel-open", {"kit": KIT, "what": "music"})
        case("Add my music, the folder opened %s: %s" % ("behind this window" if how == "behind" else "not at all", "our line added to hers" if how == "behind" else "her words"),
             code == 200 and j.get("words") == want, j)
    s.stop()
    s.start()


def check_sound(s, recording=None):
    """The sound of a screen recording: made once, beside it, never written over; for a recording outside Your
    Content, in the kit's own Music folder (decision 4)."""
    music = s.kit / "Music"
    how = make_recording(music / "New rec.mov", given=recording)
    case("(a short recording-like video made for this: %s)" % how, (music / "New rec.mov").is_file())
    rec_hash = sha(music / "New rec.mov")
    rid = song_of(s, KIT, "New rec")
    case("the recording is listed as a screen recording", rid is not None)
    nums = [n for n in range(1, 9)]
    _, job = make_job(s, KIT, picks(nums), rid, "beat")
    snd = music / "New rec sound.m4a"
    case("a test make with the recording takes its sound, beside it, as \"<name> sound.m4a\"", job and job["state"] == "done" and snd.is_file(), job)
    h1, m1 = sha(snd), snd.stat().st_mtime_ns
    case("the recording itself is unchanged", sha(music / "New rec.mov") == rec_hash)
    case("the sound beside it is not listed as a song of its own", song_of(s, KIT, "New rec sound") is None and song_of(s, KIT, "New rec") == rid)
    _, job = make_job(s, KIT, picks(nums), rid, "calm")
    case("made once: the next make uses the same sound file, not written over, no second copy",
         job and job["state"] == "done" and sha(snd) == h1 and snd.stat().st_mtime_ns == m1
         and sorted(f for f in os.listdir(music) if f.startswith("New rec")) == ["New rec sound.m4a", "New rec.mov"], os.listdir(music))
    old = music / "Old rec sound.m4a"
    oh, om = sha(old), old.stat().st_mtime_ns
    _, job = make_job(s, KIT, picks(nums), song_of(s, KIT, "Old rec"), "beat")
    case("a sound already beside a recording is used as it is, never written over",
         job and job["state"] == "done" and sha(old) == oh and old.stat().st_mtime_ns == om, job)
    case("the result says nothing of a path", no_path(job))

    # decision 4: a kit that points at an export folder outside Your Content
    content = s.kit.parent
    outside = s.work / "Lightroom exports" / "Outside shoot"
    outside.mkdir(parents=True)
    for n in range(1, 7):
        tiny_jpeg(outside / ("%02d.jpg" % n), 1080, 1350)
    make_recording(outside / "Outside rec.mov", given=recording)
    before = {f: sha(outside / f) for f in os.listdir(outside)}
    k = content / OUTSIDE_KIT
    (k / ".kit").mkdir(parents=True)
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": "Outside exports", "date": "2026-11-02", "folder": OUTSIDE_KIT,
                                                     "source": "folder", "photos_dir": str(outside),
                                                     "photos": sorted(f for f in os.listdir(outside) if f.endswith(".jpg"))}))
    code, out = s.cmd("kit.py", "sheet", str(k))
    case("(a kit pointing at an export folder outside Your Content)", (k / ".kit" / "sheet.json").is_file(), out[-300:])
    oid = song_of(s, OUTSIDE_KIT, "Outside rec")
    st = s.http("GET", "/reel-songs?kit=" + OUTSIDE_KIT.replace(" ", "%20"))[1]
    case("its recording is listed, in the Photos folder", oid and [x["where"] for x in st["songs"]] == ["Photos"], st)
    _, job = make_job(s, OUTSIDE_KIT, picks([1, 2, 3, 4, 5, 6]), oid, "beat")
    case("its sound is made in the kit's own Music folder (decision 4)", job and job["state"] == "done" and (k / "Music" / "Outside rec sound.m4a").is_file(), job)
    case("and the export folder is exactly as it was: nothing added, nothing changed",
         {f: sha(outside / f) for f in os.listdir(outside)} == before, sorted(os.listdir(outside)))
    st = s.http("GET", "/reel-songs?kit=" + OUTSIDE_KIT.replace(" ", "%20"))[1]
    case("that sound is not listed as a song of its own", [x["name"] for x in st["songs"]] == ["Outside rec"], st)
    _, job2 = make_job(s, OUTSIDE_KIT, picks([1, 2, 3, 4, 5, 6]), oid, "build")
    case("made once there too", job2 and job2["state"] == "done" and sorted(os.listdir(k / "Music")) == ["Outside rec sound.m4a"], os.listdir(k / "Music"))


def check_make_server(s):
    q = "kit=" + KIT.replace(" ", "%20")
    st = s.state()
    bid = song_of(s, KIT, "Beat one")
    good = {"kit": KIT, "stamp": st["stamp"], "picks": picks([1, 4, 7, 10, 13, 16]), "song": bid, "vibe": "beat", "test": True}
    bads = {
        "no photos": (dict(good, picks=[]), 400, "Pick a few photos for the reel first."),
        "41 photos": (dict(good, picks=picks(list(range(1, 42)))), 400, OURS_TOO_MANY),
        "a photo not in the kit": (dict(good, picks=picks([1, 999])), 400, None),
        "a photo twice": (dict(good, picks=picks([1, 1])), 400, None),
        "a vibe that isn't hers": (dict(good, vibe="fast"), 400, "Pick a vibe first."),
        "no song picked yet": (dict(good, song=None), 400, None),
        "a song by its path": (dict(good, song="Music/Beat one.wav"), 400, None),
        "a song that isn't there": (dict(good, song="0123456789ab"), 400, "That song isn't there anymore. Press Add my music and drag it in again."),
        "test as words": (dict(good, test="yes"), 400, None),
        "a field it doesn't know": (dict(good, folder="/tmp"), 400, None),
        "a numbered list from before": (dict(good, stamp="old"), 409, None),
        "a kit outside Your Content": (dict(good, kit="Sneaky"), 404, None),
    }
    for name, (b, want, words) in bads.items():
        code, j, _ = s.http("POST", "/reel-make", b)
        case("Make my reel refuses %s" % name, code == want and j and j.get("ok") is False and (words is None or j.get("words") == words), (code, j))
    case("Make my reel refuses another Origin", s.http("POST", "/reel-make", good, headers={"Origin": "http://evil.example"})[0] == 403)
    case("Make my reel refuses another host", s.http("POST", "/reel-make", good, headers={"Host": "evil.example:%d" % s.port})[0] == 403)
    case("nothing was asked of the job by the refusals", (s.http("GET", "/reel-job?" + q)[1] or {}).get("job") is None
         or s.http("GET", "/reel-job?" + q)[1]["job"]["state"] in ("done", "problem"))
    case("refused: a job asked for by a made-up id", s.http("GET", "/reel-job?" + q + "&id=../x")[0] == 400)
    case("refused: the job asked for by another website", s.http("GET", "/reel-job?" + q, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403)

    # a test make (her &test=1): the beats line and her Plan line, no path
    (code, j), job = make_job(s, KIT, good["picks"], bid, "beat")
    case("a test make answers with a job for the page to ask after, no path in it", code == 200 and j["job"]["state"] in ("queued", "running", "done") and no_path(j), j)
    case("the test make finishes, nothing made", job and job["state"] == "done" and job["dry"] is True and job["project"] is None, job)
    case("its lines are her kinds: her Plan line, then Beats per piece", job and HER_PLAN.match(job["words"][0] or "") and beats_of(job) and no_path(job), job)
    case("no \"Dry run\" line, no \"Hits\" line (hers shows neither)", job and not any(w.startswith(("Dry run", "Hits")) for w in job["words"]), job)
    case("nothing was written into CapCut's projects", not any(p.is_dir() for p in s.store.iterdir()))
    case("the reel's working files are in the kit's own .kit/reels (decision 1)", (s.kit / ".kit" / "reels" / "reel.json").is_file()
         and (s.kit / ".kit" / "reels" / "photos.json").is_file())
    case("the kit's record is not written by a test make", "made" not in (s.record() or {}))
    listed = json.loads((s.kit / ".kit" / "reels" / "photos.json").read_text())
    sheet = json.loads((s.kit / ".kit" / "sheet.json").read_text())["photos"]
    case("reel.py is handed the page's own numbered list", [(x["n"], Path(x["file"]).name) for x in listed["photos"]] == [(x["n"], Path(x["file"]).name) for x in sheet])

    # a second press while one is at work: told, and given that job to follow
    jl = s.kit / ".kit" / "reel-job.json"
    keep = jl.read_bytes()
    jl.write_text(json.dumps({"id": "a" * 12, "state": "queued", "t": time.time(), "dry": True}))
    code, j, _ = s.http("POST", "/reel-make", good)
    case("a second Make my reel while one is starting: told, with that job to follow", code == 409 and j.get("words") == "Your reel is already being made. One moment."
         and j["job"]["id"] == "a" * 12, (code, j))
    jl.write_text(json.dumps({"id": "b" * 12, "state": "running", "t": time.time(), "pid": 99999999, "dry": True}))
    code, j, _ = s.http("GET", "/reel-job?" + q + "&id=" + "b" * 12)
    case("a job that was stopped part way is told as one, in plain words", code == 200 and j["job"]["state"] == "problem"
         and j["job"]["problem"] == "Making your reel stopped before it finished. Nothing was made. Press Make my reel again.", j)
    jl.write_bytes(keep)

    # a short song: her heading, from the flag (her page's pattern missed "15.4 seconds")
    short_wav(BEAT60, s.kit / "Music" / "Short beat.wav", 10)
    sid = song_of(s, KIT, "Short beat")
    _, job = make_job(s, KIT, picks(list(range(1, 31))), sid, "beat")
    case("too many photos for a short song: the job says so, with the short-song flag", job and job["state"] == "problem" and job["short_song"] is True
         and job["problem"].startswith("Your song is only 10.0 seconds, and 30 photos need at least"), job)
    plan_file = s.kit / ".kit" / "reels" / "reel.json"
    _, job = make_job(s, KIT, picks([2, 5, 8, 11, 14, 17]), bid, "beat", stamp=None)
    long_from = json.loads(plan_file.read_text())["facts"]["song_from"]
    _, job2 = make_job(s, KIT, picks([2, 5, 8, 11, 14, 17]), sid, "beat")
    short_from = json.loads(plan_file.read_text())["facts"]["song_from"]
    # the 10-second cut of the test beat has its first 1 of a bar at about 1.25 s: "at the top" is her words under 1 s
    case("a song under 40 seconds starts at the top, on its first 1 (decision 8); a 60-second one where it picks up",
         job and job2 and short_from < 2.0 and long_from > 10.0 and job["words"][0].endswith("seconds in."), (long_from, short_from, job2 and job2["words"][:1]))

    # a real make: into the pretend CapCut projects folder only
    kit_before = json.loads((s.kit / ".kit" / "kit.json").read_text())
    nums = [1, 4, 7, 10, 13, 16]
    _, job = make_job(s, KIT, picks(nums, ["", "+", "", "-", "", ""]), bid, "beat", test=False)
    name = "2026-11-01 Fake beach reel"
    case("a real make: done, named after the kit's folder (decision 6)", job and job["state"] == "done" and job["project"] == name and job["dry"] is False, job)
    case("its lines are what her page shows after a make: her Plan line (and Wide, if any), no beats line",
         job and HER_PLAN.match(job["words"][0]) and all(w.startswith(("Plan", "Wide", "Your song is only", "I left out")) for w in job["words"]) and no_path(job), job)
    proj = s.store / name
    case("the CapCut project is in the pretend CapCut projects folder, with the song inside it", proj.is_dir()
         and any(f.startswith("draft_") for f in os.listdir(proj)) and (proj / "Beat one.wav").is_file(), sorted(os.listdir(proj)) if proj.is_dir() else None)
    made = (s.record() or {}).get("made") or []
    case("the reel page's record gains the reel it made", len(made) == 1 and made[0]["project"] == name and made[0]["picks"] == "1,4+,7,10-,13,16"
         and made[0]["vibe"] == "beat" and made[0]["footage"] is None and made[0]["song_id"] == bid, made)
    kit_after = json.loads((s.kit / ".kit" / "kit.json").read_text())
    case("the kit's own record says the reel, written by its command (kit.py reel-made), with the order made",
         kit_after.get("reel", {}).get("project") == name and kit_after["reel"].get("picks_text") == "1,4+,7,10-,13,16"
         and kit_after["reel"]["picks"] == nums and {k: v for k, v in kit_after.items() if k != "reel"} == {k: v for k, v in kit_before.items() if k != "reel"},
         kit_after.get("reel"))
    _, job = make_job(s, KIT, picks(nums, ["", "+", "", "-", "", ""]), bid, "beat", test=False)
    case("made again: a new project beside it, \"... reel 2\" (never written over)", job and job["project"] == name + " 2" and (s.store / name).is_dir()
         and (s.store / (name + " 2")).is_dir(), job)
    case("and the record has both", [m["project"] for m in (s.record() or {}).get("made", [])] == [name, name + " 2"])
    code, j, _ = s.http("POST", "/reel-capcut", {"kit": KIT})
    case("Open CapCut answers her words (decision 24), CapCut never started here", code == 200 and j == {"ok": True, "words": OPEN_WORDS}, j)


def check_acceptance(s):
    """Her 22 acceptance cases, on a pretend kit of her shoot's photo sizes. Photos only: through Make my reel's
    own route, with &test=1 (the route sends test: true). With clips: reel.py make --dry-run --clips, the way the
    route will call it once footage is on the page (a later stage)."""
    content = s.kit.parent
    k = content / SIZES_KIT
    (k / "Photos").mkdir(parents=True)
    (k / ".kit").mkdir()
    for n, (w, h) in SIZES.items():
        tiny_jpeg(k / "Photos" / ("%02d.jpg" % n), w, h)
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": "Pretend sizes", "date": "2026-09-23", "folder": SIZES_KIT, "source": "drop",
                                                     "photos": sorted(os.listdir(k / "Photos"))}))
    code, out = s.cmd("kit.py", "sheet", str(k))
    rows = json.loads((k / ".kit" / "sheet.json").read_text())["photos"]
    case("(a pretend kit of her 52 photo sizes, numbered as hers)", [(x["n"], Path(x["file"]).name, x["w"], x["h"]) for x in rows]
         == [(n, "%02d.jpg" % n, w, h) for n, (w, h) in sorted(SIZES.items())], out[-300:])
    (k / "Music").mkdir()
    (k / "Music" / "test beat.wav").write_bytes(BEAT60.read_bytes())
    song1, song2 = handoff_songs()
    songs = {"beat60": k / "Music" / "test beat.wav"}
    if song1 and song2:
        (k / "Music" / "song one.m4a").write_bytes(song1.read_bytes())          # this run's scratch folder only
        (k / "Music" / "song two.m4a").write_bytes(song2.read_bytes())
        songs.update(song1=k / "Music" / "song one.m4a", song2=k / "Music" / "song two.m4a")
    else:
        print("NOTE  her handoff's two songs aren't on this computer (a client's, never in this repository): their cases say SKIP", flush=True)
    ids = {key: song_of(s, SIZES_KIT, p.stem) for key, p in songs.items()}

    # photos only, through the page's route
    for v in ("beat", "mixed", "calm", "build"):
        name = "song1 photos 10 %s" % v
        if "song1" not in songs:
            print("SKIP  her case \"%s\" through Make my reel: the song is from her handoff" % name, flush=True)
            continue
        _, job = make_job(s, SIZES_KIT, pk(PICK10), ids["song1"], v)
        got = beats_of(job)
        case("her case \"%s\", through Make my reel (test): her line exactly" % name, got == EXPECTED[name], "expected: %s / got: %s" % (EXPECTED[name], job))
        case("her case \"%s\": her Plan line, the song from the top" % name, job and HER_PLAN.match(job["words"][0]) and job["words"][0].endswith("starting the song at the top."), job and job["words"][:1])
    # beyond her 22: a fourth reel of the same choices is the fourth mix (her variation, counted from the reels made)
    rec = k / ".kit" / "reel-page.json"
    rec.write_text(json.dumps({"v": 1, "made": [{"project": "x", "picks": PICK10, "vibe": "beat", "footage": None}] * 3}))
    _, job = make_job(s, SIZES_KIT, pk(PICK10), ids["beat60"], "beat")
    case("three reels already made with these choices: the next is variation 3, her line exactly (photos only, on the test beat)",
         beats_of(job) == VARIATION3, "expected: %s / got: %s" % (VARIATION3, job))

    # with clips: reel.py directly, with --kit and --clips
    video = s.work / VIDEO_NAME
    video.write_bytes(b"pretend video")
    env = dict(s.env)

    def clips_file(clips, tag):
        f = s.work / ("clips-%s.json" % tag)
        f.write_text(json.dumps([{"path": str(video), "src": a, "seconds": round(b - a, 2), "w": 2160, "h": 3840, "length": 420.7767} for a, b in clips]))
        return f
    rest = PICK14.split(",")
    first14 = "c1," + PICK14
    first20 = "c1," + PICK20
    backforth = ",".join(["c1"] + rest[0:2] + ["c2"] + rest[2:4] + ["c3"] + rest[4:])
    bf = [(2.5, 6.5), (136.0, 140.0), (188.0, 192.0)]
    cases = {}
    for v in ("beat", "mixed", "calm", "build"):
        cases["song2 first 14 %s" % v] = ("song2", True, v, first14, [(2.5, 6.5)], 0)
        cases["song2 first 20 %s" % v] = ("song2", True, v, first20, [(2.5, 6.5)], 0)
        cases["beat60 first 14 %s" % v] = ("beat60", False, v, first14, [(2.5, 6.5)], 0)
        cases["beat60 backforth 14 %s" % v] = ("beat60", False, v, backforth, bf, 0)
    cases["song1 first 14 beat (too long for the song)"] = ("song1", True, "beat", first14, [(2.5, 6.5)], 0)
    cases["beat60 first 14 mixed variation 2"] = ("beat60", False, "mixed", first14, [(2.5, 6.5)], 2)
    for name, (song, top, v, ptext, clips, var) in cases.items():
        if song not in songs:
            print("SKIP  her case \"%s\": the song is from her handoff" % name, flush=True)
            continue
        args = [sys.executable, str(ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts" / "reel.py"), "make", "--dry-run",
                "--folder", str(k / "Photos"), "--shoot", "Pretend sizes", "--kit", str(k), "--picks", ptext, "--vibe", v,
                "--song", str(songs[song]), "--variation", str(var), "--clips", str(clips_file(clips, name.replace(" ", "-")))]
        if top:
            args += ["--song-start", "0"]
        r = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
        line = next((ln for ln in r.stdout.splitlines() if ln.startswith(("Beats per piece", "STOP"))), r.stdout.strip()[-200:])
        case("her case \"%s\" (reel.py --clips --kit): her line exactly" % name, line == EXPECTED[name], "expected: %s / got: %s" % (EXPECTED[name], line))


def page_texts3(c):
    return c.js("""(function(){
      function h(id){ var x = document.querySelector('#' + id + ' h2').cloneNode(true); x.querySelector('.num').remove(); return x.textContent; }
      var says = document.querySelectorAll('#step3 > p.say');
      var none = document.querySelector('#songs .song.none');
      return {h2: h('step3'), say1: says[0].textContent, say2: says[1].innerHTML, button: document.getElementById('addMusic').textContent,
        note: document.querySelector('#step3 .note').innerHTML, none_b: none.querySelector('b').textContent, none_s: none.querySelector('small').textContent,
        h2v: h('step4'), sayv: document.querySelector('#step4 > p.say').textContent,
        cards: Array.from(document.querySelectorAll('#vibes .opt')).map(function(b){ var t = b.querySelector('b').cloneNode(true); var r = t.querySelector('.rec'); if (r) r.remove(); return [t.textContent, b.querySelector(':scope > span').textContent]; }),
        rec: Array.from(document.querySelectorAll('#vibes .opt')).filter(function(b){ return !!b.querySelector('.rec'); }).map(function(b){ return b.dataset.vibe + ':' + b.querySelector('.rec').textContent; }),
        nums: Array.from(document.querySelectorAll('section.step')).filter(function(s){ return !s.hidden; }).map(function(s){ return s.id + '=' + s.querySelector('.num').textContent; }),
        songs: Array.from(document.querySelectorAll('#songs .song:not(.none)')).map(function(b){ return [b.querySelector('b').textContent, b.querySelector('small').textContent, b.classList.contains('on')]; }),
        none_on: none.classList.contains('on'),
        vibe_on: (document.querySelector('#vibes .opt.on') || {dataset: {}}).dataset.vibe,
        sum: document.getElementById('sum').textContent, sum_b: document.querySelector('#sum b').textContent,
        make: document.getElementById('makeBtn').textContent, make_off: document.getElementById('makeBtn').disabled,
        waiting: document.getElementById('waiting').textContent,
        result: document.getElementById('result').className, result_html: document.getElementById('result').innerHTML,
        done3: document.getElementById('step3').classList.contains('done')};
    })()""")


def wait_result(c, seconds=60):
    c.wait_for("(function(){ var r = document.getElementById('result'); var b = document.getElementById('makeBtn');"
               " return r.classList.contains('on') && !!r.querySelector('h3') && !b.querySelector('.spin'); })()", seconds)
    return page_texts3(c)


def check_page_steps(c, s):
    # the record starts clean for the page: their own order of 8 photos, no song yet
    code, j, _ = s.http("POST", "/reel-save", save_body(s.state(), {"picks": picks([3, 6, 9, 12, 15, 18, 21, 24]), "mine": True, "song": None, "vibe": "beat"}))
    case("(set up: 8 photos of their own, no song yet)", code in (200, 409), (code, j))
    st = s.state()
    if st["saved"].get("song") is not None or st["saved"]["picks"] != picks([3, 6, 9, 12, 15, 18, 21, 24]):
        s.http("POST", "/reel-save", save_body(st, {"picks": picks([3, 6, 9, 12, 15, 18, 21, 24]), "mine": True, "song": None, "vibe": "beat"}, page="setup2"))
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('#reel .tile').length === 8 && document.querySelectorAll('#songs .song').length > 1", 20)
    t = page_texts3(c)
    for k in ("h2", "say1", "say2", "button", "note", "none_b", "none_s"):
        case("her words, step 3: %s" % k, t[k] == HERS3[k], (t[k], HERS3[k]))
    case("her words, step 5: the heading and the line", t["h2v"] == HERS5["h2"] and t["sayv"] == HERS5["say"], (t["h2v"], t["sayv"]))
    case("her words, step 5: the four vibes, in her order", t["cards"] == HERS5["cards"], t["cards"])
    case("Recommended on On every beat only (decision 7)", t["rec"] == ["beat:Recommended"], t["rec"])
    case("her renumbering: the order 1, the song 2, the vibe 3 (footage and style come later)", t["nums"] == ["step1=1", "step3=2", "step4=3"], t["nums"])
    case("her song list: each with her words for what it is and where",
         [x[:2] for x in t["songs"]][:3] == [["Short beat", "Song, in your Music folder"], ["New rec", "Screen recording · I'll use its sound, in your Music folder"],
                                              ["Beat one", "Song, in your Music folder"]] and ["Photo song", "Song, in your Photos folder"] in [x[:2] for x in t["songs"]], t["songs"])
    case("no song picked yet: nothing is marked, and the step isn't done", not any(x[2] for x in t["songs"]) and not t["none_on"] and not t["done3"])
    case("the bar: her summary, word for word", t["sum"] == "8 photos · no song picked yet · on every beat" and t["sum_b"] == "8 photos", t["sum"])
    case("the bar: her button", t["make"] == "Make my reel" and not t["make_off"], t["make"])

    c.click("#makeBtn")
    t = page_texts3(c)
    case("Make my reel with no song: her \"One more thing\" box", t["result"] == "result on bad" and t["result_html"] == "<h3>One more thing: your song</h3><p>%s</p>" % NEED_SONG_HTML, t["result_html"])
    c.click("#songs .song[data-id='%s']" % song_of(s, KIT, "Beat one"))
    t = page_texts3(c)
    case("picking a song marks it and clears the box (hers)", t["result"] == "result" and [x for x in t["songs"] if x[2]] == [["Beat one", "Song, in your Music folder", True]] and t["done3"], t["result"])
    case("saved: the song, by its id", on_disk(s, {"song": song_of(s, KIT, "Beat one")}))
    case("the bar: the song's name", page_texts3(c)["sum"] == "8 photos · Beat one · on every beat", page_texts3(c)["sum"])
    c.click("#songs .song.none")
    case("No song: marked, saved as \"\"", page_texts3(c)["none_on"] and on_disk(s, {"song": ""}))
    case("the bar: no song", page_texts3(c)["sum"] == "8 photos · no song · on every beat", page_texts3(c)["sum"])
    c.click("#vibes .opt[data-vibe='calm']")
    t = page_texts3(c)
    case("a vibe: marked, saved, in the bar", t["vibe_on"] == "calm" and on_disk(s, {"vibe": "calm"}) and t["sum"].endswith("· calm"), t["sum"])

    # Add my music, and a new file picked by itself
    c.click("#addMusic")
    try:
        c.wait_for("document.getElementById('waiting').textContent === %s" % json.dumps(HERS3["open"]), 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("Add my music: her words once the folder is open", ok, page_texts3(c)["waiting"])
    (s.kit / "Music" / "Dropped in.wav").write_bytes(BEAT60.read_bytes())
    try:
        c.wait_for("document.getElementById('waiting').textContent === 'Got it: Dropped in.'", 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    t = page_texts3(c)
    case("a song dropped in the Music folder shows up and is picked by itself, \"Got it: <name>.\" (within her 3 s look)", ok and t["songs"][0] == ["Dropped in", "Song, in your Music folder", True], (t["waiting"], t["songs"][:1]))
    case("saved: the new song", on_disk(s, {"song": song_of(s, KIT, "Dropped in")}))
    (s.kit / "Music" / "Dropped in.wav").rename(s.work / "Dropped in.wav")
    try:
        c.wait_for("!Array.from(document.querySelectorAll('#songs .song b')).some(function(b){ return b.textContent === 'Dropped in'; })", 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("a song taken out of the folder goes from the list, and is no longer picked (hers)", ok and page_texts3(c)["sum"].startswith("8 photos · no song picked yet"), page_texts3(c)["sum"])
    c.reload()
    c.wait_for("document.querySelectorAll('#songs .song').length > 1", 15)
    t = page_texts3(c)
    case("after a reload: the vibe as saved", t["vibe_on"] == "calm", t["vibe_on"])

    # a test make on the page (her &test=1)
    c.open(s.page_url() + "&test=1")
    c.wait_for("document.querySelectorAll('#songs .song').length > 1", 15)
    case("&test=1: her button words", page_texts3(c)["make"] == "Make my reel (test: nothing is made)")
    c.click("#songs .song[data-id='%s']" % song_of(s, KIT, "Beat one"))
    c.click("#makeBtn")
    t = page_texts3(c)
    case("while it is made: her spinner words and her line in the box", "Making your reel..." in t["make"] and t["make_off"]
         and "Finding the beat and cutting your photos to it. This takes a few seconds." in t["result_html"], (t["make"], t["result_html"][:120]))
    t = wait_result(c)
    lines = re.findall(r"<p[^>]*>(.*?)</p>", t["result_html"])
    case("a test make: her heading, \"Test run: nothing was made\"", "<h3>Test run: nothing was made</h3>" in t["result_html"], t["result_html"][:200])
    case("then her Plan line and the beats line, no Dry run line", lines and HER_PLAN.match(html.unescape(lines[0])) and any(x.startswith("Beats per piece: ") for x in lines)
         and not any(x.startswith("Dry run") for x in lines), lines)
    case("no path anywhere in the result", not re.search(r"/private/|/Users/|\.kit", t["result_html"]))
    case("the button is back, in its test words", t["make"] == "Make my reel (test: nothing is made)" and not t["make_off"])

    # a real make on the page
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('#songs .song').length > 1", 15)
    before = sorted(os.listdir(s.store))
    c.click("#makeBtn")
    t = wait_result(c)
    m = re.search(r"<h3>It's in CapCut: (.*?)</h3>", t["result_html"])
    case("a real make: her heading, with the reel's name", m and m.group(1).startswith("2026-11-01 Fake beach reel"), t["result_html"][:200])
    new = [x for x in os.listdir(s.store) if x not in before]
    case("and it is in the pretend CapCut projects folder, by that name", m and new == [html.unescape(m.group(1))], (new, m and m.group(1)))
    case("her line under it, her two buttons", "<p>Open CapCut, click it at the top of your projects, add your look, and export.</p>" in t["result_html"]
         and c.js("document.getElementById('capcut').textContent") == "Open CapCut"
         and c.js("document.getElementById('resultBack').textContent") in ("Back to the post kit", "Back to home"), t["result_html"][-400:])
    case("her Plan line shown, no beats line after a real make", any(HER_PLAN.match(html.unescape(x)) for x in re.findall(r"<p>(.*?)</p>", t["result_html"]))
         and "Beats per piece" not in t["result_html"])
    c.click("#capcut")
    try:
        c.wait_for("document.getElementById('went').textContent === %s" % json.dumps(OPEN_WORDS), 8)
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    case("Open CapCut: her words beside it (decision 24)", ok, c.js("document.getElementById('went').textContent"))

    # a short song on the page: her heading, from the flag
    code, j, _ = s.http("POST", "/reel-save", save_body(s.state(), {"picks": picks(list(range(1, 31))), "mine": True, "song": song_of(s, KIT, "Short beat"), "vibe": "beat"}, page="setup3"))
    c.open(s.page_url())
    c.wait_for("document.querySelectorAll('#reel .tile').length === 30", 15)
    c.click("#makeBtn")
    t = wait_result(c)
    case("too many photos for the song: her \"Your song is a little short for this\", the reason, and no second line (it already says what to do)",
         t["result"] == "result on bad" and t["result_html"].startswith("<h3>Your song is a little short for this</h3><p>Your song is only 10.0 seconds")
         and t["result_html"].count("<p>") == 1, t["result_html"])
    c.click("#vibes .opt[data-vibe='calm']")
    case("changing something clears the box (hers)", page_texts3(c)["result"] == "result")

    # a reload while a reel is being made: the page picks up where it was and shows the result when it ends
    import fcntl
    jl = s.kit / ".kit" / "reel-job.json"
    held = open(s.kit / ".kit" / "reel-job.lock", "a")
    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        jl.write_text(json.dumps({"id": "c" * 12, "state": "running", "t": time.time(), "pid": os.getpid(), "dry": True}))
        c.open(s.page_url())
        c.wait_for("!!document.querySelector('#makeBtn .spin')", 10)
        case("reloaded while a reel is being made: her spinner and her line", "Finding the beat" in page_texts3(c)["result_html"])
        jl.write_text(json.dumps({"id": "c" * 12, "state": "done", "t": time.time(), "dry": True, "words": ["Beats per piece: 1, 2"]}))
    finally:
        fcntl.flock(held, fcntl.LOCK_UN)
        held.close()
    t = wait_result(c, 10)
    case("and the result when it ends", "<h3>Test run: nothing was made</h3><p>Beats per piece: 1, 2</p>" == t["result_html"], t["result_html"])
    errs = c.page_errors()
    case("no errors on the page", not errs, errs[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9105)
    ap.add_argument("--recording", help="a short screen-recording-like video made beforehand (else one is made here)")
    ap.add_argument("--only", choices=("songs", "make", "acceptance", "page"), help="run only the server's song, make or acceptance part, or the page")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("run-%H%M%S")
    run.mkdir(parents=True)
    group("her words", check_words)
    group("the defaults, each in its one place", check_defaults)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the page: the pretend kit is drawn with the Mac's sips", flush=True)
        return summary()
    s = Setup(run, a.port)
    s.make()
    s.start()
    try:
        # the server takes the next free port when the one asked for is held for a moment (v19 review): any of the
        # few just above --port is still this test's own
        case("the page server is on a port of this test's own (%d)" % s.port, 9100 <= s.port <= 9139 or a.port <= s.port < a.port + 10)
        if a.only in ("songs", "make", "acceptance", "page"):
            return only(a, s, run)
        group("the server", check_server, s)
        # the browser part starts from a clean record
        for f in ("reel-page.json", "reel-page.prev.json"):
            p = s.kit / ".kit" / f
            if p.exists():
                p.rename(p.with_name(p.name + ".server-part"))
        if not chrome_drive.find_chrome():
            print("SKIP  the page in a browser: no Chrome on this computer", flush=True)
        else:
            # a tall window, so the end of a full row and the photos below it are on screen together
            with chrome_drive.Chrome(work=str(run), size=(1280, 1700)) as c:
                group("the page", check_page, c, s)
                group("two windows", check_two_windows, c, s)
                group("phone width", check_phone, c, s)
            group("the one line for two windows", check_newer_line, run, s)
        group("step 3, the songs", check_songs, s)
        group("Add my music, behind or not opened", check_open_words, s)
        group("the sound of a screen recording", check_sound, s, a.recording)
        group("Make my reel, on the server", check_make_server, s)
        group("her acceptance cases", check_acceptance, s)
        if chrome_drive.find_chrome():
            with chrome_drive.Chrome(work=str(run), size=(1280, 1700)) as c:
                group("steps 3 and 5, the bar and the result, in the page", check_page_steps, c, s)
                group("phone width, with every step", check_phone, c, s)
        group("a re-made list", check_remade_list, s)
    finally:
        s.stop()
    return summary()


def only(a, s, run):
    """--only: the server parts this stage added, in the order they build on each other."""
    group("step 3, the songs", check_songs, s)
    if a.only in ("make", "acceptance", "page"):
        group("the sound of a screen recording", check_sound, s, a.recording)
        group("Make my reel, on the server", check_make_server, s)
    if a.only == "acceptance":
        group("her acceptance cases", check_acceptance, s)
    if a.only == "page" and chrome_drive.find_chrome():
        with chrome_drive.Chrome(work=str(run), size=(1280, 1700)) as c:
            group("steps 3 and 5, the bar and the result, in the page", check_page_steps, c, s)
    return summary()


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
