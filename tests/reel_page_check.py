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
import subprocess
import sys
import time
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
    t = (f / "pages" / "reel-maker.html").read_text(encoding="utf-8") + "\n" + (f / "server.py").read_text(encoding="utf-8")
    return html.unescape(t).replace("\\'", "'")


# ---------- the pretend kit and the page server ----------

class Setup:
    def __init__(self, work, port):
        self.work, self.want = Path(work), port
        self.target = self.work / "kit"
        self.home = self.work / "home"
        self.studio = self.target / "studio"
        self.kit = self.target / "The Assistant" / "Your Content" / KIT
        self.env = dict(os.environ, HOME=str(self.home), STUDIO_HOME=str(self.studio))
        self.proc = None
        self.port = None

    def make(self):
        self.home.mkdir(parents=True, exist_ok=True)
        if not self.kit.exists():
            r = subprocess.run([sys.executable, str(HERE / "fake_kit.py"), str(self.target), "--photos", str(PHOTOS)],
                               capture_output=True, text=True, env=self.env)
            if r.returncode != 0:
                raise RuntimeError("fake_kit: " + (r.stdout + r.stderr)[-400:])

    def cmd(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, env=self.env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env)
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
        code, j, _ = s.http("POST", p, {"kit": KIT})
        case("%s is kept for a later stage and says so" % p, code == 404 and j and j.get("ok") is False)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9105)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    run = work / time.strftime("run-%H%M%S")
    run.mkdir(parents=True)
    group("her words", check_words)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the page: the pretend kit is drawn with the Mac's sips", flush=True)
        return summary()
    s = Setup(run, a.port)
    s.make()
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, 9100 <= s.port <= 9119 or s.port == a.port)
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
        group("a re-made list", check_remade_list, s)
    finally:
        s.stop()
    return summary()


def summary():
    res = chrome_drive._results
    bad = [n for n, ok in res if not ok]
    print("\n%d of %d passed." % (len(res) - len(bad), len(res)) + (" FAILED: %d" % len(bad) if bad else ""), flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
