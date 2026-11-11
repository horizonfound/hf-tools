#!/usr/bin/env python3
"""The post kit's three steps per piece (Nicole's v20: Make it, Your words, Add to my queue), checked by request
and on the real page in a HIDDEN Chrome.

    python3 tests/kit_steps_check.py [--port 8880] [--work <a folder to keep the run in>] [--no-chrome]

What it does, on a pretend Assistant with one pretend kit it makes itself in a throwaway folder (the words page
check's own: a few tiny pictures; nothing of a client's, nothing of the real ~/.studio, no drive):
  * her words, word for word: every word in kit.KIT_WORDS against her own pages/post-kit.html (handoff v20), when
    her handoff is on this computer (it is never in the repository; without it that one part says SKIP);
  * the top of the page: her new lede, her three buttons (Open the kit folder, Open the Photos folder, My posting
    queue →) and the line under them;
  * step 2, Your words, in each of her three states, for a reel (caption & hooks) and a carousel (caption only),
    with "Write my words →" / "Open my words →", the whole box opening the words page for that piece;
  * step 3, Add to my queue, in every state: her three not-ready wordings with a grey disabled button, ready, in
    the queue with no date, "Down for <day>." with the pale green disabled "✓ Added to my queue" and "See it in my
    feed →", and "Posted ✓" / "✓ Posted"; a reel never made, a kit with no carousel, a one-slide carousel (a
    single post, whose words are the carousel's);
  * a piece whose only caption is the one they typed themselves: the button the page shows adds it;
  * a second shoot whose folder name shortens to the same queue name: never shown, or changed, as the first one's;
  * the Stories card: no words box, no queue step;
  * NO link inside a link (the bug Nicole caught): every page served, in every state, is read tag by tag;
  * who may press: the queue's two requests from another page's Origin or another host are refused and change
    nothing; a folder the kit doesn't name is never opened;
  * one way to write a caption: no hashtags and no short caption anywhere on the page or in `kit.py facts`,
    `kit.py words` and `kit.py voice --hashtags` refused with nothing written, and an older kit's words.json and
    captions file left on the disk byte for byte, never shown;
  * that a shoot's name with <, &, quotes, an accent and an emoji only ever shows as text;
  * the page itself (when there is a Chrome): the cards whole, a press on the words box opening the words page,
    a press on a disabled button or anywhere in the queue box never opening the card's page, the five rhythm
    chips the first time, the button changing in place with nothing else moving, "See it in my feed" on its own
    line under it and opening the posting queue, "Adding it…" in the button itself with the box not growing, the
    folder buttons, a phone's width with six slides (nothing wider than the page or hanging out of a card), no
    error, nothing asked of the internet.

No folder is ever opened (the page's folder requests are answered inside the page) and CapCut is never started.
The page server and the hidden Chrome are this test's own and are stopped at the end. Every line says PASS, FAIL
or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only, a Mac or a PC.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
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
import words_page_check as wpc  # noqa: E402  (its pretend Assistant: one kit, the page server, words.py from the chat)

KIT, SHORT, PROJECT, HOOKS, WINDOWS = wpc.KIT, wpc.SHORT, wpc.PROJECT, wpc.HOOKS, wpc.WINDOWS
KQ = quote(KIT, safe="")
JSQ = quote(KIT, safe="!~*'()")              # as the page's own encodeURIComponent writes it
PAGE = "/content/%s/Post%%20kit.html" % KQ
LEDE = ("Everything you need to post this shoot, in one place. Make your reel or carousel, write its words, then add it "
        "to your posting queue. Nothing gets posted for you.")
LOCK_TAIL = " first. Then add it to your posting queue to see it in your feed and give it a date."
READY = "It's ready! Add it to your posting queue so you can see it in your feed and give it a date."
RHYTHMS = ["Every day", "Every other day", "3 a week", "Twice a week", "Once a week"]
OLD_WORDS = {"hooks": ["An older hook"], "caption": "An older caption", "short": "Old short one", "stories": ["An old story line"],
             "hashtags": "#oldtag #beachfamily", "leaned_on": "what you said"}
OLD_TEXT = "HOOKS\n\n1. An older hook\n\nCAPTION\n\nAn older caption\n\nHASHTAGS\n\n#oldtag #beachfamily\n"

# every request the page makes to open a folder is answered inside the page: no folder is ever opened
PAGE_HOOKS = r"""
(function(){
  var real = window.fetch;
  window.fetch = function(u, o){
    if (String(u).indexOf('/open') === 0) {
      try { var a = JSON.parse(sessionStorage.getItem('__opens') || '[]'); a.push(String(u)); sessionStorage.setItem('__opens', JSON.stringify(a)); } catch (e) {}
      return Promise.resolve(new Response(JSON.stringify({ok: true, words: 'Opened the folder in Finder.'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
    }
    return real.apply(this, arguments);
  };
})();
"""


# a phone's width, measured against the page's own width (window.innerWidth grows with a page that overflows, so
# it can never show a sideways scroll): the page's width, how wide its contents are, and everything inside a card
# whose right edge passes the card's own
WIDE_JS = """(function(){
  var d = document.documentElement, out = [];
  document.querySelectorAll('a.piece').forEach(function(card){
    var edge = card.getBoundingClientRect().right + 0.5;
    card.querySelectorAll('.top, .cta, .sub, .strip, .w, .qbtn, .qchips, [data-box]').forEach(function(n){
      if (n.getBoundingClientRect().right > edge) out.push(card.dataset.piece + ' ' + (n.className || n.tagName));
    });
  });
  return {page: d.clientWidth, scroll: d.scrollWidth, out: out};
})()"""


def skip(line):
    print("SKIP  " + line, flush=True)


def her_page():
    for base in (ROOT, Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v2[0-9]-*")):
            f = h / "Carousel designer and reel picker" / "pages" / "post-kit.html"
            if f.is_file() and "Add to my queue" in f.read_text(encoding="utf-8"):
                return f
    return None


# ---------- reading a page tag by tag ----------

VOID = {"img", "meta", "br", "hr", "input", "link", "source", "wbr", "area", "base", "col", "embed", "track"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids, self.bits = tag, dict(attrs), parent, [], []

    def text(self):
        return re.sub(r"\s+", " ", "".join(b if isinstance(b, str) else b.text() for b in self.bits)).strip()

    def all(self):
        for k in self.kids:
            yield k
            for x in k.all():
                yield x

    def find(self, tag=None, **attrs):
        """Every node below this one with that tag and those attributes: class_ means "has that class"; any other
        name is the attribute itself, with _ for - (data_box is data-box)."""
        def fits(n):
            if tag is not None and n.tag != tag:
                return False
            for k, v in attrs.items():
                if k == "class_":
                    if v not in (n.attrs.get("class") or "").split():
                        return False
                elif n.attrs.get(k.replace("_", "-")) != v:
                    return False
            return True
        return [n for n in self.all() if fits(n)]

    def up(self, tag):
        n = self.parent
        while n is not None and n.tag != tag:
            n = n.parent
        return n


class Tree(HTMLParser):
    def __init__(self, text):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node("#root", [], None)
        self.at = self.root
        self.nested = []                       # every <a> opened while another <a> was still open
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == "a" and (self.at.tag == "a" or self.at.up("a") is not None):
            self.nested.append(dict(attrs))
        n = Node(tag, attrs, self.at)
        self.at.kids.append(n)
        self.at.bits.append(n)
        if tag not in VOID:
            self.at = n

    def handle_endtag(self, tag):
        n = self.at
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.at = n.parent

    def handle_data(self, data):
        if self.at.tag not in ("script", "style"):
            self.at.bits.append(data)


class Kit:
    """One served kit page, read."""

    def __init__(self, s, headers=None):
        self.code, _, raw = s.http("GET", PAGE, headers=headers)
        self.raw = raw.decode("utf-8", "replace")
        self.tree = Tree(self.raw)
        self.root = self.tree.root

    def card(self, piece):
        got = self.root.find("a", data_piece=piece)
        return got[0] if got else None

    def box(self, name):
        got = self.root.find(data_box=name)
        return got[0] if got else None

    def words(self, piece):
        """(the step's label, the state line, the link's words, where it goes)."""
        b = self.box("words-" + piece)
        if b is None:
            return None
        return (b.find(class_="stepk")[0].text(), (b.find("p") or [None])[0].text(), b.find(class_="wl")[0].text(), b.attrs.get("data-href"))

    def queue(self, piece):
        """(the line, the button's words, is it disabled, its classes, the feed link's words or None, locked)."""
        b = self.box("queue-" + piece)
        if b is None:
            return None
        btn = b.find("button")[0]
        link = b.find(class_="qlink")
        return (b.find("p", class_="ws")[0].text(), btn.text(), "disabled" in btn.attrs, btn.attrs.get("class"),
                link[0].text() if link else None, "locked" in (b.attrs.get("class") or "").split())


def anchors_ok(k):
    """No <a> inside an <a>, and inside a card nothing that is an <a> at all."""
    inside = [n for p in ("reel", "carousel", "stories") for n in ((k.card(p).find("a")) if k.card(p) else [])]
    return k.code == 200 and not k.tree.nested and not inside and len(k.root.find("a", class_="piece")) == 3


SEEN = []


def look(s, what):
    """The page now; every look is also a look for a link inside a link."""
    k = Kit(s)
    SEEN.append((what, anchors_ok(k)))
    return k


def kit_module(s):
    os.environ["STUDIO_HOME"] = str(s.studio)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    return importlib.import_module("kit")


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def set_status(s, piece, status):
    p = s.posting()
    for y in p["pieces"]:
        if y["id"].endswith("-" + piece):
            y["status"] = status
    s.write_posting(p)


# ---------- 1. her words ----------

def check_words(k):
    case("the lede is her v20 one, word for word", k.KIT_WORDS["lede"] == LEDE)
    f = her_page()
    if f is None:
        skip("her words against her own page: her handoff (reference-private) isn't on this computer")
    else:
        t = html.unescape(f.read_text(encoding="utf-8")).replace("\\'", "'")
        bad = []
        for key, v in k.KIT_WORDS.items():
            for frag in re.split(r"\{\w+\}", v):
                if frag.strip() and frag not in t:
                    bad.append((key, frag))
        case("every word in kit.KIT_WORDS (%d) is in her pages/post-kit.html, word for word" % len(k.KIT_WORDS), not bad, bad[:5])
        case("her five rhythm chips, as she wrote them, are the words page's own list", all(("'" + r + "'") in t for r in RHYTHMS))
        case("her page has no <a> in the queue box either (her fix: a span with role=link)", '<span class="qlink" role="link"' in t)
    case("ours and hers say the same day: 'Wed, Nov 11'", k.nice_day("2026-11-11") == "Wed, Nov 11" and k.nice_day("2026-11-03") == "Tue, Nov 3"
         and k.nice_day("") == "" and k.nice_day(None) == "", k.nice_day("2026-11-11"))
    import words_page
    case("the chips the kit page shows are the words page's five", list(words_page.RHYTHMS) == RHYTHMS)
    src = (SCRIPTS / "kit.py").read_text(encoding="utf-8")
    case("the kit page has no queue logic of its own: it asks the words page's two routes", "/words-queue" in src and "/words-rhythm" in src
         and "add_for_kit" not in src and "set_status" not in src and "parse_interval" not in src)


# ---------- 2. every state, by request ----------

def check_states(s, k):
    # an older kit: the flat words file and the captions file an earlier version wrote, with hashtags in them
    old_words, old_text = s.kit / ".kit" / "words.json", s.kit / ".kit" / "Captions and hooks.txt"
    old_words.write_text(json.dumps(OLD_WORDS), encoding="utf-8")
    old_text.write_text(OLD_TEXT, encoding="utf-8")
    was = (digest(old_words), digest(old_text))

    p = look(s, "nothing made")
    case("the page answers, as HTML, with today's mark", p.code == 200 and p.raw.startswith("<!doctype html>") and k.PAGE_MARK in p.raw, p.code)
    case("her new lede under the shoot's name", p.root.find("p", class_="lede")[0].text() == LEDE)
    top = p.root.find("p", class_="folders")[0]
    btns = [(b.text(), b.attrs.get("data-sub")) for b in top.find("button")]
    link = top.find("a")
    case("her three buttons: Open the kit folder, Open the Photos folder, My posting queue →",
         btns == [("Open the kit folder", ""), ("Open the Photos folder", "Photos")] and len(link) == 1
         and link[0].text() == "My posting queue →" and link[0].attrs.get("href") == "/posting.html", (btns, [a.attrs for a in link]))
    case("...and the line under them that says what happened", [n.attrs.get("id") for n in p.root.find("p", class_="went") if n.parent.tag == "header"] == ["folderWent"])
    for piece in ("reel", "carousel"):
        c = p.card(piece)
        steps = [(n.find(class_="stepno")[0].text(), n.text()) for n in c.find(class_="stepk")]
        label = "Your words: caption & hooks" if piece == "reel" else "Your words: caption"
        case("the %s card: three numbered steps, 1 Make it, 2 %s, 3 Add to my queue" % (piece, label),
             steps == [("1", "1Make it"), ("2", "2" + label), ("3", "3Add to my queue")], steps)
    st = p.card("stories")
    case("the Stories card is as it was: no steps, no words box, no queue step",
         st is not None and not st.find(class_="stepk") and not st.find(class_="w") and not st.find("button") and "Make my stories →" in st.text())

    what = {"reel": "caption and hooks", "carousel": "caption"}
    for piece in ("reel", "carousel"):
        w = p.words(piece)
        case("step 2, the %s, nothing said: 'Not written yet. Tell me about it and I'll help with your %s.' and 'Write my words →'" % (piece, what[piece]),
             w[1] == "Not written yet. Tell me about it and I'll help with your %s." % what[piece] and w[2] == "Write my words →", w)
        case("...and the whole box opens the words page for the %s (a link by role, not an <a>)" % piece,
             w[3] == "/words.html?kit=%s&piece=%s" % (KQ, piece) and p.box("words-" + piece).tag == "div"
             and p.box("words-" + piece).attrs.get("role") == "link" and p.box("words-" + piece).attrs.get("tabindex") == "0", w[3])
    q = p.queue("reel")
    case("step 3, a reel never made and not written: 'Make your reel and write its caption first. ...', locked, a grey disabled Add to my queue",
         q == ("Make your reel and write its caption" + LOCK_TAIL, "Add to my queue", True, "qbtn", None, True), q)
    q = p.queue("carousel")
    case("step 3, no carousel: 'Make your carousel and write its caption first. ...', locked",
         q == ("Make your carousel and write its caption" + LOCK_TAIL, "Add to my queue", True, "qbtn", None, True), q)
    case("no carousel: 'No slides yet.' and 'Not made yet'; no reel: 'Not made yet' and no Open in CapCut",
         "No slides yet." in p.card("carousel").text() and "Not made yet" in p.card("carousel").text()
         and "Not made yet" in p.card("reel").text() and not p.root.find(id="capcut"))

    # they answered in the chat, nothing written yet
    s.words("answer", "reel", {"about": "A mommy & me morning in Laguna."})
    s.words("answer", "carousel", {"about": "Hannah's baby boy was just turning one."})
    p = look(s, "answered")
    case("step 2, told but not written: 'You've told me about it. Copy the line on the page into the chat and I'll write your caption and hooks.'",
         p.words("reel")[1:3] == ("You've told me about it. Copy the line on the page into the chat and I'll write your caption and hooks.", "Write my words →"), p.words("reel"))
    case("...and for the carousel: '... I'll write your caption.'",
         p.words("carousel")[1:3] == ("You've told me about it. Copy the line on the page into the chat and I'll write your caption.", "Write my words →"), p.words("carousel"))

    # the caption and hooks are written; the reel is still not made
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    p = look(s, "written, not made")
    case("step 2, written: 'Caption ready · 10 hooks' and 'Open my words →'", p.words("reel")[1:3] == ("Caption ready · 10 hooks", "Open my words →"), p.words("reel"))
    case("step 3, written but not made: 'Make your reel first. ...', still locked",
         p.queue("reel") == ("Make your reel" + LOCK_TAIL, "Add to my queue", True, "qbtn", None, True), p.queue("reel"))
    s.save("reel", picked=[2])
    p = look(s, "a hook picked")
    case("a hook picked on the words page: 'Caption ready · 10 hooks, 1 picked'", p.words("reel")[1] == "Caption ready · 10 hooks, 1 picked", p.words("reel"))
    case("the words themselves are not on the kit page (they are one press away, on the words page)",
         "MINI SESSIONS" not in p.raw and HOOKS[0] not in html.unescape(p.raw))

    # made, but the caption taken away again
    s.reel_made()
    s.save("reel", caption="")
    p = look(s, "made, no caption")
    case("step 3, made but no caption: 'Write its caption first. ...', locked", p.queue("reel") == ("Write its caption" + LOCK_TAIL, "Add to my queue", True, "qbtn", None, True), p.queue("reel"))
    case("step 2, hooks but no caption: '10 hooks, 1 picked' (hers), 'Open my words →'", p.words("reel")[1:3] == ("10 hooks, 1 picked", "Open my words →"), p.words("reel"))
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"})
    case("...and the Assistant refuses the add too, whatever the page shows", code == 409 and not s.posting(), (code, j))
    case("made: 'In CapCut: <project>' with Open in CapCut, a button", PROJECT in p.card("reel").text() and p.root.find("button", id="capcut")[0].text() == "Open in CapCut")

    # ready
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    p = look(s, "ready")
    b = p.box("queue-reel")
    btn = b.find("button")[0]
    case("step 3, made and written: 'It's ready! Add it to your posting queue ...' with a live Add to my queue",
         b.find("p", class_="ws")[0].text() == READY and btn.text() == "Add to my queue" and "disabled" not in btn.attrs
         and btn.attrs.get("data-add") == "reel" and "locked" not in b.attrs["class"] and not b.find(class_="qlink"), b.text())
    case("no rhythm yet: the page knows to ask (and shows no chips until Add is pressed)",
         p.root.find("body")[0].attrs.get("data-rhythm") == "" and not p.root.find(class_="qchips") and '"rhythms": ["Every day", "Every other day", "3 a week", "Twice a week", "Once a week"]' in p.raw)
    case("showing the kit page put nothing in the posting queue", not s.posting())

    # who may press
    port = s.port
    for path, body in (("/words-queue", {"kit": KIT, "piece": "reel"}), ("/words-rhythm", {"text": "3 a week"})):
        c1 = s.http("POST", path, body, headers={"Origin": "http://evil.example"})[0]
        c2 = s.http("POST", path, body, headers={"Origin": "http://127.0.0.1:%d" % (port + 1)})[0]
        c3 = s.http("POST", path, body, headers={"Host": "evil.example:%d" % port})[0]
        c4 = s.http("POST", path, json.dumps(body).encode("utf-8"), headers={"Content-Type": "text/plain"})[0]
        case("POST %s from another page's Origin, another host, or not as JSON: refused" % path, (c1, c2, c3) == (403, 403, 403) and c4 == 415, (c1, c2, c3, c4))
    case("...and nothing was queued and no rhythm set by them", not s.posting())
    case("a GET can't add (the kit page's requests are POSTs)", s.http("GET", "/words-queue?kit=%s&piece=reel" % KQ)[0] in (404, 405, 501) and not s.posting())
    c1 = s.http("GET", PAGE, headers={"Host": "evil.example:%d" % port})[0]
    case("the kit page itself, asked for under another host's name: refused", c1 == 403, c1)
    for sub in ("..", "../..", ".kit", "Elsewhere", "Photos/.."):
        code, j, _ = s.http("GET", "/open?kit=%s&sub=%s" % (KQ, quote(sub, safe="")))
        case("a folder the kit doesn't name (%r) is never opened" % sub, j is not None and j.get("ok") is False, (code, j))

    # added before any rhythm is set (the page asks the rhythm first; the Assistant copes either way)
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "reel"}, headers={"Origin": "http://127.0.0.1:%d" % port, "Sec-Fetch-Site": "same-origin"})
    p = look(s, "added, no date")
    case("added with no rhythm set: 'In your posting queue.', the pale green disabled '✓ Added to my queue', 'See it in my feed →'",
         code == 200 and p.queue("reel") == ("In your posting queue.", "✓ Added to my queue", True, "qbtn done", "See it in my feed →", False), (code, p.queue("reel")))
    code, j, _ = s.http("POST", "/words-rhythm", {"text": "3 a week"})
    p = look(s, "added, dated")
    case("with a rhythm: 'Down for Wed, Nov 11.' then '✓ Added to my queue' and 'See it in my feed →'",
         code == 200 and p.queue("reel") == ("Down for Wed, Nov 11.", "✓ Added to my queue", True, "qbtn done", "See it in my feed →", False), p.queue("reel"))
    b = p.box("queue-reel")
    kinds = [n.tag for n in b.kids]
    feed = b.find(class_="qlink")[0]
    case("'See it in my feed' is a span with role=link, after the button's line, and goes to the posting queue on this server",
         kinds == ["div", "p", "div", "span"] and feed.tag == "span" and feed.attrs.get("role") == "link" and feed.attrs.get("data-href") == "/posting.html"
         and feed.attrs.get("tabindex") == "0", (kinds, feed.attrs))
    case("the page knows the rhythm is set now", p.root.find("body")[0].attrs.get("data-rhythm") == "1")
    x = s.queue_piece("reel") or {}
    case("decision 7: the piece is ready to post in the queue, with its date", x.get("status") == "green" and x.get("date") == "2026-11-11", x)

    # in progress in the queue (made, added by the kit) is not "added": the button still shows
    set_status(s, "reel", "yellow")
    p = look(s, "in progress")
    case("a piece the queue holds as in progress still shows 'It's ready!' and Add to my queue", p.queue("reel")[:3] == (READY, "Add to my queue", False), p.queue("reel"))
    set_status(s, "reel", "posted")
    p = look(s, "posted")
    case("posted: 'Posted ✓' and a disabled '✓ Posted', with 'See it in my feed →'",
         p.queue("reel") == ("Posted ✓", "✓ Posted", True, "qbtn done", "See it in my feed →", False), p.queue("reel"))
    set_status(s, "reel", "green")

    # their own caption, no draft: a caption all the same (hers)
    s.save("carousel", own="Hannah's boy turned one. We went to the beach.")
    p = look(s, "own caption")
    case("their own caption counts: 'Caption ready' (a carousel never says hooks) and 'Open my words →'",
         p.words("carousel")[1:3] == ("Caption ready", "Open my words →"), p.words("carousel"))
    case("...the carousel isn't made: 'Make your carousel first. ...'", p.queue("carousel")[0] == "Make your carousel" + LOCK_TAIL and p.queue("carousel")[5], p.queue("carousel"))

    # a one-slide carousel is a single post, and its words are the carousel's (decision 6)
    car = s.kit / "Carousel"
    car.mkdir(exist_ok=True)
    one = "Beach carousel 1 - slide 01.jpg"
    (car / one).write_bytes(wpc.TINY)
    rec = s.kit_rec()
    rec["carousel_set"] = {"kind": "laid-out", "base": "Beach carousel 1", "files": [one], "saved": "2026-11-09T10:00:00"}
    rec["laid_out"] = [dict(rec["carousel_set"])]
    s.write_kit(rec)
    # made, and the only caption is the one they typed themselves: the button the page shows must work
    p = look(s, "own caption, made")
    kept = s.posting()
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "carousel"})
    x = s.queue_piece("carousel") or {}
    p2 = look(s, "own caption, added")
    case("a piece whose only caption is their own typed one: the page says it's ready, and Add to my queue adds it (not 'write its caption')",
         p.queue("carousel")[:3] == (READY, "Add to my queue", False) and code == 200 and x.get("status") == "green"
         and p2.queue("carousel")[1] == "✓ Added to my queue", (p.queue("carousel"), code, j, p2.queue("carousel")))
    s.write_posting(kept)                     # as it was, for what follows
    s.words("draft", "carousel", {"caption": "Hannah's baby boy was just turning one..."})
    p = look(s, "one slide")
    case("a one-slide carousel: '1 slide saved in the Carousel folder', its words box is the carousel's, and it is ready",
         "1 slide saved in the Carousel folder" in p.card("carousel").text() and p.words("carousel")[0] == "2Your words: caption"
         and p.words("carousel")[3].endswith("&piece=carousel") and p.queue("carousel")[:3] == (READY, "Add to my queue", False), (p.words("carousel"), p.queue("carousel")))
    code, j, _ = s.http("POST", "/words-queue", {"kit": KIT, "piece": "carousel"})
    p = look(s, "one slide, added")
    x = s.queue_piece("carousel") or {}
    case("...added: the queue holds it as a single post, ready, dated after the reel; the page says 'Down for Fri, Nov 13.'",
         code == 200 and x.get("kind") == "single" and x.get("status") == "green" and p.queue("carousel")[:2] == ("Down for Fri, Nov 13.", "✓ Added to my queue"), (x, p.queue("carousel")))

    # another shoot whose folder name comes out the same once the queue shortens it: never this one's pieces
    twin = KIT[:10] + "-" + KIT[11:]         # "2026-09-23-Zoë ...": a dash where the space was
    shutil.copytree(str(s.kit), str(s.kit.parent / twin))
    try:
        before = json.dumps(s.posting(), sort_keys=True)
        tq = quote(twin, safe="")
        code_t, _, raw_t = s.http("GET", "/content/%s/Post%%20kit.html" % tq)
        tw = Tree(raw_t.decode("utf-8", "replace")).root
        tb = {pc: tw.find(data_box="queue-" + pc)[0] for pc in ("reel", "carousel")} if code_t == 200 and tw.find(data_box="queue-reel") else {}
        lines = {pc: (b.find("p", class_="ws")[0].text(), b.find("button")[0].text()) for pc, b in tb.items()}
        case("a second shoot whose folder name shortens to the same one ('%s'): its page never shows the first shoot's 'Added to my queue' or its date" % twin[:12],
             lines == {"reel": (READY, "Add to my queue"), "carousel": (READY, "Add to my queue")}, (code_t, lines))
        code_a, j_a, _ = s.http("POST", "/words-queue", {"kit": twin, "piece": "reel"})
        first = json.loads(before).get("pieces", [])
        now_p = s.posting().get("pieces", [])
        mine = [x for x in now_p if re.split(r"[\\/]", str(x.get("kit") or ""))[-1] == twin]
        case("...and adding it works (stage 3: a name of its own in the queue), with the first shoot's pieces left exactly as they were",
             code_a == 200 and (j_a or {}).get("ok") and json.dumps(now_p[:len(first)], sort_keys=True) == json.dumps(first, sort_keys=True)
             and len(mine) == 2 and not {x["id"] for x in mine} & {x["id"] for x in first}
             and any(x["id"].endswith("-reel") and x["status"] == "green" for x in mine), (code_a, j_a, [x["id"] for x in now_p]))
        s.write_posting(json.loads(before))       # as it was, for what follows
    finally:
        shutil.rmtree(str(s.kit.parent / twin), ignore_errors=True)

    # the Assistant's own files beside it never show, and nothing of the old way is on the page
    low = html.unescape(p.raw).lower()
    case("no hashtags and no short caption anywhere on the page", "hashtag" not in low and "short caption" not in low and "#oldtag" not in low
         and "old short one" not in low and "an older caption" not in low and "an older hook" not in low and "story line" not in low and "written from" not in low)
    case("no Copy buttons, no word boxes of the old page", "class='copy'" not in p.raw and "class='w hook'" not in p.raw)
    case("no path in the page, nothing from the internet, no serif",
         str(s.work) not in p.raw and ".kit/" not in p.raw and "kit.json" not in p.raw and not re.search(r"https?://|googleapis|Fraunces|--display", p.raw))
    if not WINDOWS:
        case("the shoot's name is never in the page as HTML", "<b>& the" not in p.raw and "<b>&amp; the" not in p.raw
             and all(b.up("h1") is None and not b.text().startswith("& the") for b in p.root.find("b")) and p.root.find("h1")[0].text() == SHORT + ".")
    code, _, raw = s.http("GET", "/content/%s/Captions%%20and%%20hooks.txt" % KQ)
    case("the older captions file is no longer handed out by the page server", code == 404 and b"#oldtag" not in raw, code)

    # the old way to write a caption is closed, and what it left is left
    f = s.work / "old-way.json"
    f.write_text(json.dumps({"hooks": ["A new hook"], "caption": "A new caption", "hashtags": "#new"}), encoding="utf-8")
    code, out = s.cmd("kit.py", "words", KIT, "--file", str(f))
    case("kit.py words: refused in plain words that point to the words page and words.py, nothing saved",
         code == 2 and out.startswith("STOP:") and "words.py" in out and "words page" in out and "Nothing was saved" in out and "Traceback" not in out, (code, out[-300:]))
    code, out = s.cmd("kit.py", "voice", "--hashtags", "#beach")
    case("kit.py voice --hashtags: no such thing any more, nothing kept", code == 2 and "hashtags" not in json.dumps(json.loads((s.studio / "studio.json").read_text(encoding="utf-8"))), (code, out[-200:]))
    sf = json.loads((s.studio / "studio.json").read_text(encoding="utf-8"))
    sf["voice"] = {"samples": ["A caption they posted."], "hashtags": "#fromlastyear"}
    (s.studio / "studio.json").write_text(json.dumps(sf), encoding="utf-8")
    code, out = s.cmd("kit.py", "facts", KIT)
    try:
        facts = json.loads(out)
    except ValueError:
        facts = {}
    case("kit.py facts: no hashtags (the ones an earlier version kept stay in the Studio File, unread), the words are the words page's",
         code == 0 and "hashtag" not in out.lower() and facts.get("voice") == {"samples": ["A caption they posted."]}
         and facts.get("words", {}).get("reel", {}).get("caption") is True and "existing_words" not in facts
         and json.loads((s.studio / "studio.json").read_text(encoding="utf-8"))["voice"]["hashtags"] == "#fromlastyear", (code, out[-300:]))
    code, out = s.cmd("kit.py", "show", KIT)
    case("kit.py show: the words by piece, from the words page's record", code == 0 and "Words: reel caption written, carousel caption written" in out, out[-300:])
    code, out = s.cmd("kit.py", "page", KIT)
    saved = s.kit / ".kit" / "Post kit.html"
    case("kit.py page: the saved copy is today's page too (the steps, no old words)", code == 0 and saved.is_file() and k.PAGE_MARK in saved.read_text(encoding="utf-8")
         and "#oldtag" not in saved.read_text(encoding="utf-8") and "data-box='queue-reel'" in saved.read_text(encoding="utf-8"), (code, out[-200:]))
    case("the older kit's words.json and captions file are still on the disk, byte for byte", (digest(old_words), digest(old_text)) == was)
    case("the kit's record of the words page was never touched by the kit page", s.piece("reel").get("caption", "").startswith("MINI SESSIONS"))

    bad = [w for w, ok in SEEN if not ok]
    case("NO link inside a link, and no <a> at all inside a card, in every one of the %d states above" % len(SEEN), len(SEEN) >= 12 and not bad, bad)
    broken = "<a class='piece' href='/x'><div><a href='/posting.html'>See it in my feed</a></div></a>"
    case("(the check itself sees her bug: a link inside a card is caught)", Tree(broken).nested == [{"href": "/posting.html"}])


# ---------- 3. the page in a hidden Chrome ----------

def check_browser(c, s):
    s.reel_made()
    s.slides_made(3)
    s.words("draft", "reel", {"caption": "MINI SESSIONS are coming to Laguna Beach on December 4th!!!", "hooks": HOOKS})
    c.init_script(PAGE_HOOKS)
    url = s.url(PAGE)
    here = "location.pathname.indexOf('/content/') === 0"
    c.open(url)
    c.wait_for("document.body.classList.contains('live') && document.querySelectorAll('a.piece').length === 3", 10)
    case("in a browser: three cards, each whole (its steps inside it), and no link inside a link",
         c.js("document.querySelectorAll('#pieces > a.piece').length === 3 && document.querySelectorAll('#pieces > *').length === 3"
              " && document.querySelectorAll('a a').length === 0"
              " && ['reel','carousel'].every(function(p){var a=document.querySelector('a.piece[data-piece='+p+']');"
              "return a.contains(document.querySelector('[data-box=words-'+p+']')) && a.contains(document.querySelector('[data-box=queue-'+p+']'))})") is True)
    case("in a browser: her lede, and the shoot's name only as text", c.text(".lede") == LEDE and c.text("h1") == SHORT + "."
         and c.js("document.querySelectorAll('h1 b').length === 0 && window.pwned === undefined") is True, c.text("h1"))
    nums = c.js("Array.from(document.querySelectorAll('a.piece')).map(function(a){return Array.from(a.querySelectorAll('.stepno')).map(function(n){return n.textContent}).join('')})")
    case("in a browser: 1 2 3 on the Reel and Carousel cards, none on Stories", nums == ["123", "123", ""], nums)
    case("in a browser: two columns, the words box above the queue box, beside the photos",
         c.rect("[data-box=words-reel]")["x"] > c.rect("[data-piece=reel] .strip")["x"] + 100
         and c.rect("[data-box=queue-reel]")["y"] > c.rect("[data-box=words-reel]")["bottom"] - 1)

    # the folder buttons at the top
    c.click("button.go[data-sub='Photos']")
    c.wait_for("JSON.parse(sessionStorage.getItem('__opens') || '[]').length === 1 && document.getElementById('folderWent').textContent.indexOf('Opened') === 0", 5)
    c.click(".folders button.go[data-sub='']")
    c.wait_for("JSON.parse(sessionStorage.getItem('__opens') || '[]').length === 2 && document.getElementById('folderWent').textContent.indexOf('Opened') === 0", 5)
    case("Open the Photos folder and Open the kit folder ask the Assistant for exactly those, and the line under them says the answer",
         json.loads(c.js("sessionStorage.getItem('__opens')")) == ["/open?kit=%s&sub=Photos" % JSQ, "/open?kit=%s&sub=" % JSQ]
         and c.text("#folderWent") == "Opened the folder in Finder." and c.js(here) is True, c.js("sessionStorage.getItem('__opens')"))

    # the carousel has no caption: its queue box is locked, and no press there opens the designer
    case("in a browser: the carousel's Add to my queue is grey and disabled", c.js("document.querySelector('[data-box=queue-carousel] .qbtn').disabled") is True
         and c.text("[data-box=queue-carousel] .ws") == "Write its caption" + LOCK_TAIL)
    c.click("[data-box=queue-carousel] .qbtn", check=False)
    c.click("[data-box=queue-carousel] .ws")
    c.click("[data-box=queue-carousel] .stepk")
    time.sleep(0.5)
    case("a press on the disabled button, or anywhere in a locked queue box, never opens the card's page", c.js(here) is True, c.js("location.href"))

    # the reel is ready: Add to my queue asks the rhythm the first time, in place
    c.js("window.__same = 1")
    spot = c.rect("[data-box=queue-reel] [data-add]")
    c.mouse_move(spot["cx"], spot["cy"])          # the card lifts a little under the pointer: measured with the pointer already on it
    time.sleep(0.5)
    before = {k: c.rect(k) for k in ("a.piece[data-piece=reel]", "[data-piece=reel] .strip", "[data-box=words-reel]", "a.piece[data-piece=carousel] h2")}
    c.click("[data-box=queue-reel] [data-add]")
    c.wait_for("document.querySelectorAll('[data-box=queue-reel] .qchips button').length === 5", 5)
    chips = c.js("Array.from(document.querySelectorAll('[data-box=queue-reel] .qchips button')).map(function(b){return b.textContent})")
    case("the first add: 'How often do you want to post? I'll give each post a date.' and her five chips, in place of the button",
         chips == RHYTHMS and c.text("[data-box=queue-reel] .qb .ws") == "How often do you want to post? I'll give each post a date."
         and c.count("[data-box=queue-reel] [data-add]") == 0, chips)
    case("...and nothing was added yet, and the card's page was not opened", not s.posting() and c.js(here) is True)
    c.click("[data-box=queue-reel] .qb .ws")
    time.sleep(0.3)
    case("a press on the question itself does nothing", c.js(here) is True and c.count("[data-box=queue-reel] .qchips button") == 5)
    c.click("[data-box=queue-reel] .qchips button:nth-child(3)")
    try:
        c.wait_for("!!document.querySelector('[data-box=queue-reel] .qbtn.done')", 10)
        done = True
    except chrome_drive.Timeout:
        done = False
    case("a press on '3 a week': the rhythm is saved, the reel is added, and the card's page is NOT opened",
         done and s.posting().get("interval") == 3.0 and (s.queue_piece("reel") or {}).get("status") == "green" and c.js(here) is True, (s.posting().get("interval"), c.js("location.href")))
    case("the button changed in place: 'Down for Wed, Nov 11.', a pale green disabled '✓ Added to my queue'",
         done and c.text("[data-box=queue-reel] .ws") == "Down for Wed, Nov 11." and c.text("[data-box=queue-reel] .qbtn") == "✓ Added to my queue"
         and c.js("(function(){var b=document.querySelector('[data-box=queue-reel] .qbtn');return b.disabled && getComputedStyle(b).backgroundColor})()") == "rgb(230, 242, 236)",
         c.text("[data-box=queue-reel]"))
    if done:
        btn, feed = c.rect("[data-box=queue-reel] .qbtn"), c.rect("[data-box=queue-reel] .qlink")
        case("'See it in my feed →' is on its own line under the button", c.text("[data-box=queue-reel] .qlink") == "See it in my feed →"
             and feed["y"] >= btn["bottom"] and abs(feed["x"] - btn["x"]) < 3, (btn, feed))
    after = {k: c.rect(k) for k in before}
    same = all(abs(before[k][d] - after[k][d]) < 0.5 for k in ("[data-piece=reel] .strip", "[data-box=words-reel]") for d in ("x", "y", "w", "h"))
    card_same = all(abs(before["a.piece[data-piece=reel]"][d] - after["a.piece[data-piece=reel]"][d]) < 0.5 for d in ("x", "y", "w"))
    case("the page was drawn again without a reload and nothing jumped: the card, its photos and its words box are where they were",
         c.js("window.__same") == 1 and same and card_same, [(k, d, before[k][d], after[k][d]) for k in before for d in ("x", "y", "w", "h") if abs(before[k][d] - after[k][d]) >= 0.5])
    case("the card is still whole after the change (her broken card: three pieces)", c.js("document.querySelectorAll('#pieces > *').length === 3 && document.querySelectorAll('a a').length === 0"
                                                                                      " && document.querySelector('a.piece[data-piece=reel]').contains(document.querySelector('[data-box=queue-reel]'))") is True)
    c.click("[data-box=queue-reel] .qbtn", check=False)
    c.click("[data-box=queue-reel] .ws")
    time.sleep(0.4)
    case("a press on '✓ Added to my queue' or beside it does nothing, and adds nothing twice", c.js(here) is True
         and len([y for y in s.posting()["pieces"] if y["id"].endswith("-reel")]) == 1)

    # the second piece: no rhythm question
    s.words("draft", "carousel", {"caption": "Hannah's baby boy was just turning one..."})
    c.open(url)
    c.wait_for("!!document.querySelector('[data-box=queue-carousel] [data-add]')", 10)
    h0 = c.rect("[data-box=queue-carousel]")["h"]
    stories_y = c.rect("a.piece[data-piece=stories]")["y"]
    # the answer held back a moment, so the page can be measured while it says "Adding it…"
    c.js("(function(){var real=window.fetch;window.fetch=function(u,o){var a=arguments,me=this;if(String(u).indexOf('/words-queue')!==0)return real.apply(me,a);"
         "return new Promise(function(ok){setTimeout(ok,1200)}).then(function(){return real.apply(me,a)})}})()")
    c.click("[data-box=queue-carousel] [data-add]")
    time.sleep(0.4)
    mid = (c.text("[data-box=queue-carousel] .qbtn"), c.js("document.querySelector('[data-box=queue-carousel] .qbtn').disabled"),
           c.text("[data-box=queue-carousel] .went"))
    h1 = c.rect("[data-box=queue-carousel]")["h"]
    try:
        c.wait_for("!!document.querySelector('[data-box=queue-carousel] .qbtn.done')", 10)
        done = True
    except chrome_drive.Timeout:
        done = False
    h2 = c.rect("[data-box=queue-carousel]")["h"]
    case("while it is adding, the button itself says 'Adding it…' (disabled) and the box does not grow; once added it is within a few pixels, and the Stories card has not moved",
         mid == ("Adding it…", True, "") and abs(h1 - h0) < 0.5 and abs(h2 - h0) < 6 and abs(c.rect("a.piece[data-piece=stories]")["y"] - stories_y) < 6, (mid, h0, h1, h2))
    case("the carousel, added next: no rhythm question this time, 'Down for Fri, Nov 13.', the designer not opened",
         done and c.text("[data-box=queue-carousel] .ws") == "Down for Fri, Nov 13." and c.js(here) is True and s.posting().get("interval") == 3.0, c.text("[data-box=queue-carousel]"))

    # the words box opens the words page; See it in my feed opens the posting queue
    c.click("[data-box=words-carousel] .ws")
    try:
        c.wait_for("location.pathname === '/words.html'", 10)
        went = c.js("location.search")
    except chrome_drive.Timeout:
        went = None
    case("a press anywhere in the Your words box opens the words page for that piece (not the designer)", went == "?kit=%s&piece=carousel" % KQ, c.js("location.href"))
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    c.js("document.querySelector('[data-box=words-reel]').focus()")
    c.key("Enter")
    try:
        c.wait_for("location.pathname === '/words.html'", 10)
        went = c.js("location.search")
    except chrome_drive.Timeout:
        went = None
    case("...and so does Enter with the box in focus (the reel's)", went == "?kit=%s&piece=reel" % KQ, c.js("location.href"))
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    c.click("[data-box=queue-reel] .qlink")
    try:
        c.wait_for("location.pathname === '/posting.html'", 10)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("'See it in my feed →' opens the posting queue (not the reel page)", went, c.js("location.href"))
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    c.click("#queueLink")
    try:
        c.wait_for("location.pathname === '/posting.html'", 10)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("'My posting queue →' at the top opens it too", went, c.js("location.href"))

    # the card itself still opens its page
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    c.click("[data-piece=carousel] h2")
    try:
        c.wait_for("location.pathname === '/design.html'", 15)
        went = True
    except chrome_drive.Timeout:
        went = False
    case("a press on the Make it half of the Carousel card still opens the designer", went, c.js("location.href"))

    # a phone's width
    s.slides_made(6)                          # six slides: a no-wrap row of pictures wider than a phone
    c.phone(390, 844)
    try:
        c.open(url)
        c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
        wide = c.js(WIDE_JS)
        case("at a phone's width: one column (the steps under the photos), no sideways scroll, nothing hanging out of a card (six slides)",
             wide == {"page": 390, "scroll": 390, "out": []} and c.count("[data-piece=carousel] .strip img") >= 6
             and c.rect("[data-box=words-reel]")["y"] > c.rect("[data-piece=reel] .status")["y"], wide)
    finally:
        c.desktop()
    c.open(url)
    c.wait_for("document.querySelectorAll('a.piece').length === 3", 10)
    outside = [u for u in c.outside_requests() if not u.startswith(("data:", "blob:", "about:", "chrome"))]
    case("nothing was asked of the internet by the kit page", not outside, outside[:3])
    case("no error on the page", c.page_errors() == [], c.page_errors()[:3])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a folder for this run, kept afterwards (default: a throwaway folder, removed at the end)")
    ap.add_argument("--port", type=int, default=8880)
    ap.add_argument("--no-chrome", action="store_true", help="the page by request only")
    a = ap.parse_args()
    if any(p in chrome_drive.NEVER_PORTS for p in range(a.port, a.port + 10)):
        print("STOP: that port is one a person's own page server uses")
        return 2
    keep = bool(a.work)
    work = Path(a.work).resolve() / time.strftime("run-%H%M%S") if a.work else Path(tempfile.mkdtemp(prefix="kit-steps-check-")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    s = wpc.Setup(work / "by request", a.port)
    s.make()
    k = kit_module(s)
    try:
        group("her words", check_words, k)
        s.start()
        case("the page server is this test's own (port %d)" % s.port, a.port <= s.port < a.port + 10)
        group("every state, by request", check_states, s, k)
        s.stop()
        if a.no_chrome or not chrome_drive.find_chrome():
            skip("the page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        else:
            s = wpc.Setup(work / "in a browser", a.port)       # a fresh pretend Assistant: nothing queued, no rhythm
            s.make()
            s.start()
            with chrome_drive.Chrome(work=str(work), size=(1280, 1500)) as c:
                group("the page in a browser", check_browser, c, s)
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not keep:
            shutil.rmtree(str(work), ignore_errors=True)
        else:
            print("kept: %s" % work, flush=True)
    return wpc.summary()


if __name__ == "__main__":
    sys.exit(main())
