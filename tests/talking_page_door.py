#!/usr/bin/env python3
"""The `door` part of tests/talking_page_check.py (Stage E of docs/handoff-v24-build-2026-11-12.md): the way in to
the talking reel page. Not run by itself:

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py --only door

talking_page_check.py hands this file itself (`t`: its Setup class, its helpers), its Setup (`s`) and, for the
page, its hidden Chrome (`c`).

The door is the Talking to camera card on the reel page's chooser (Nicole's v27 reel-maker.html: <a class="kind"
id="kTalk">; her v23 had it as step 1's third card, which v27 took out with the yes/no cards). What is checked:
  * her two lines, against her own v27 page when her handoff is on this computer (SKIP when it is not; it is never
    in the repository), and that they are in reel_page.KIND_WORDS, not written twice;
  * the card is a plain link written on the server (it works before any script runs), third of her four kinds, to
    the talking page of the SAME shoot, by folder name and never by a path, for a shoot whose name has an accent,
    an ampersand, quotes, an emoji and (off a PC) a tag;
  * following it by request gives that shoot's talking page, and the talking page's own way back goes to our post
    kit page;
  * on the real page: it sits third with the same look as the other three, is not underlined, and a press on it
    opens the talking page for the same shoot and leaves the reel page's record, and every other file the
    Assistant keeps for the shoot, exactly as they were.

Nothing here makes or plays a video: the kit has photos only. Python 3.9, standard library only.
"""
import hashlib
import html
import re
from pathlib import Path
from urllib.parse import quote, unquote

KIT_WIN = "2026-09-29 Zoë & the 'door' 🚪"
KIT_MAC = "2026-09-29 Zoë <b>& the 'door' 🚪"
HER_B = "Talking to camera"
HER_S = "You talk about the shoot, and your photos go with what you say."


def kit_name(t):
    return KIT_WIN if t.WINDOWS else KIT_MAC


def her_v27():
    """Her v27 reel page, or None when her handoff is not on this computer."""
    here = Path(__file__).resolve().parent.parent
    for base in (here, here.parent / "hf-tools", Path("/Users/dustindamron/Projects/hf-tools")):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v27-*")):
            f = h / "Carousel designer and reel picker" / "pages" / "reel-maker.html"
            if f.is_file():
                return f.read_text(encoding="utf-8")
    return None


def kept(kit):
    """Every file the Assistant keeps for the shoot (its hidden folder), by name and content; logs and locks,
    which a page being open may touch, left out."""
    out = {}
    for p in sorted((kit / ".kit").rglob("*")):
        if p.is_file() and p.suffix not in (".lock", ".log"):
            out[str(p.relative_to(kit))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def run_requests(t, s):
    case = t.case
    import reel_page as rp
    name = kit_name(t)
    kit = s.make_kit(name)
    short = name[11:]

    # ---- her words
    case("her two lines are in reel_page.KIND_WORDS, word for word", rp.KIND_WORDS.get("kind_talk_b") == HER_B and rp.KIND_WORDS.get("kind_talk_s") == HER_S,
         (rp.KIND_WORDS.get("kind_talk_b"), rp.KIND_WORDS.get("kind_talk_s")))
    src = Path(rp.__file__).read_text(encoding="utf-8")
    case("...each written once (the page reads them from KIND_WORDS)", src.count('"' + HER_S + '"') == 1)
    hers = her_v27()
    if hers is None:
        t.skip("the card against her own v27 page: her handoff (reference-private) isn't on this computer")
    else:
        m = re.search(r'<a class="kind" id="kTalk"><b>(.*?)</b><span>(.*?)</span></a>', hers)
        case("hers, from her v27 reel-maker.html: the same two lines", bool(m) and (html.unescape(m.group(1)), html.unescape(m.group(2))) == (HER_B, HER_S),
             m and m.groups())
        kinds = re.search(r'<div class="kinds">(.*?)</div>', hers, re.S).group(1)
        case("...hers has it third of her four kinds", re.findall(r'id="(k\w+)"', kinds) == ["kBts", "kPhotos", "kTalk", "kBroll"])
        case("...and hers gives it the shoot in its address, nothing else", "$('kTalk').href = 'talking-reel.html' + q;" in hers)

    # ---- the card as the server writes it
    page = rp.chooser_html(name, short, True)
    kinds = re.search(r"<div class='kinds'>(.*?)</div>", page, re.S).group(1)
    case("the card is third of the four kinds on the chooser", re.findall(r"id='(k\w+)'", kinds) == ["kBts", "kPhotos", "kTalk", "kBroll"], kinds[:300])
    m = re.search(r"<a class='kind' id='kTalk' href='([^']*)'><b>(.*?)</b><span>(.*?)</span></a>", kinds)
    case("it is a plain link with the look of the other kinds (class kind), written on the server", bool(m), kinds[-300:])
    href = html.unescape(m.group(1)) if m else ""
    case("her words on it", bool(m) and (html.unescape(m.group(2)), html.unescape(m.group(3))) == (HER_B, HER_S))
    case("it goes to the talking page of the same shoot, by its folder name", href == "/talking.html?kit=" + quote(name) and unquote(href.split("kit=")[1]) == name, href)
    case("no path in it", "/private" not in href and str(kit) not in page)
    case("the card is on the chooser once, and on no kind's page (v27: the old third card is gone)",
         page.count("id='kTalk'") == 1 and all("kTalk" not in rp.page_html(name, short, True, k) and "modeTalk" not in rp.page_html(name, short, True, k) for k in rp.KINDS))
    case("no script on the chooser: the card chooses nothing and saves nothing", "<script" not in page)
    case("a name that could break an address is held whole", "kit=" + quote("a&b=c #1?x") + "'" in rp.talk_card(rp.KIND_WORDS, "a&b=c #1?x")
         and "&" not in rp.talk_card(rp.KIND_WORDS, "a&b=c #1?x").split("href='")[1].split("'")[0])
    case("a PC gets the same card (the talking page itself says what a PC can't do yet)", "this_computer" not in rp.talk_card.__code__.co_names)

    # ---- by request
    code, _j, raw, _h = s.http("GET", "/reel.html" + s.q(name))
    served = raw.decode("utf-8", "replace")
    case("the reel page the server sends with no kind is the chooser, with the card, to this shoot", code == 200 and ("href='" + html.escape(href, quote=True) + "'") in served, code)
    before = kept(kit)
    code, _j, raw, _h = s.http("GET", href)
    talk = raw.decode("utf-8", "replace")
    case("following the card gives the talking page", code == 200 and "<title>" + html.escape(s.tp.page_words()["doc_title"].replace("{short}", short)) + "</title>" in talk,
         (code, talk[:120]))
    m = re.search(r"<body[^>]*data-kit='([^']*)'", talk)
    case("...for the same shoot", bool(m) and html.unescape(m.group(1)) == name, m and m.group(1))
    case("...whose way back goes to our post kit page", ("href='/content/" + quote(name) + "/Post%20kit.html'") in html.unescape(talk)
         and s.tp.WORDS["back_kit"] == "Back to the post kit")
    case("asking for either page changed nothing the Assistant keeps for the reel", {k: v for k, v in kept(kit).items() if "reel" in k} == {k: v for k, v in before.items() if "reel" in k})
    st = s.http("GET", "/reel-state" + s.q(name))[1]
    case("the reel page's state has no talking choice in it (the card is a link, not a choice)", bool(st and st.get("ok")) and "talk" not in " ".join(st.keys()).lower(), st and sorted(st))


def run_page(t, c, s):
    case = t.case
    name = kit_name(t)
    kit = s.kit(name)
    short = name[11:]
    c.open(s.url("/reel.html" + s.q(name)))
    c.wait_for("document.querySelectorAll('.kind').length === 4", 20, tell="document.body.innerText.slice(0, 200)")
    look = c.js("""(function(){
      function L(id){ var x = document.getElementById(id), cs = getComputedStyle(x), r = x.getBoundingClientRect();
        return {tag: x.tagName, b: x.querySelector('b').textContent, s: x.querySelector('span').textContent, border: cs.borderTopWidth + ' ' + cs.borderTopStyle + ' ' + cs.borderTopColor,
                radius: cs.borderTopLeftRadius, pad: cs.paddingTop + ' ' + cs.paddingLeft, bg: cs.backgroundColor, deco: cs.textDecorationLine, disp: cs.display,
                bfont: getComputedStyle(x.querySelector('b')).font, sfont: getComputedStyle(x.querySelector('span')).font, scol: getComputedStyle(x.querySelector('span')).color,
                bcol: getComputedStyle(x.querySelector('b')).color, w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), left: Math.round(r.left),
                cursor: cs.cursor}; }
      return {ids: Array.from(document.querySelectorAll('.kinds > *')).map(function(x){ return x.id; }), a: L('kBts'), b: L('kPhotos'), t: L('kTalk'),
              href: document.getElementById('kTalk').getAttribute('href')};
    })()""")
    a, b, k = look["a"], look["b"], look["t"]
    case("on the chooser: her four kinds, the card third", look["ids"] == ["kBts", "kPhotos", "kTalk", "kBroll"], look["ids"])
    case("her words on the card", (k["b"], k["s"]) == (HER_B, HER_S), (k["b"], k["s"]))
    same = ("border", "radius", "pad", "bg", "bfont", "sfont", "scol", "bcol", "cursor", "disp")
    case("the card has the look of the others (border, corners, room inside, colours, type)", not [x for x in same if k[x] != b[x]], [(x, k[x], b[x]) for x in same if k[x] != b[x]])
    case("...is a link and is not underlined (her rule)", k["tag"] == "A" and k["deco"] == "none", (k["tag"], k["deco"]))
    case("...sits in the same row, after them, the same width", k["top"] == b["top"] and k["left"] > b["left"] > a["left"] and abs(k["w"] - b["w"]) <= 1, (a, b, k))
    # the reel page's record, if any, is left exactly alone by a press on the card
    before = kept(kit)
    c.clear_errors()
    c.click("#kTalk")
    c.wait_for("location.pathname === '/talking.html' && window.Talk && window.Talk.loaded", 20, tell="location.href")
    case("a press on the card opens the talking page", c.js("location.pathname") == "/talking.html")
    case("...for the same shoot", c.js("document.body.dataset.kit") == name and unquote(c.js("location.search")) == "?kit=" + name, c.js("location.search"))
    case("...with her title for it", c.js("document.title") == s.tp.page_words()["doc_title"].replace("{short}", short), c.js("document.title"))
    import time
    time.sleep(1.5)
    after = kept(kit)
    reel = lambda d: {x: v for x, v in d.items() if "reel" in x or x.endswith("kit.json") or "arrange" in x}   # noqa: E731
    case("the press left the reel page's records exactly as they were", reel(after) == reel(before),
         [x for x in set(before) | set(after) if before.get(x) != after.get(x)])
    new = [x for x in after if x not in before]
    made = [x for x in new if Path(x).name in ("talking.json", "talking.prev.json", "talking-words.json") or Path(x).parts[0] == "Talking"]
    case("opening the talking page makes no talking record, no words file and no Talking folder", not made and not (kit / "Talking").exists()
         and not (kit / ".kit" / "talking.json").exists() and not (kit / ".kit" / "talking-words.json").exists(), made)
    case("...and nothing new at all outside the hidden folder's talking files", not [x for x in new if not (Path(x).parts[0] == ".kit" and "talking" in Path(x).name)], new)
    # the way back (her v27): the path at the top, "<shoot> post kit"; her Back pill is still in the markup, hidden as on her page
    pill = c.js("(function(){ var b = document.getElementById('back'); return [getComputedStyle(b).display, b.getAttribute('href'), b.textContent]; })()")
    case("her Back to the post kit pill is there, hidden, still pointing at our post kit page for the same shoot (v27)",
         pill == ["none", "/content/" + quote(name) + "/Post%20kit.html", "\u2190 " + s.tp.WORDS["back_kit"]], pill)
    c.click("nav.crumbs a[href^='/content/']")
    c.wait_for("location.pathname.indexOf('/content/') === 0", 15, tell="location.href")
    case("the talking page's way back is the path at the top: our post kit page for the same shoot", unquote(c.js("location.pathname")) == "/content/" + name + "/Post kit.html", c.js("location.pathname"))
    case("no page errors on the way through", not c.page_errors(), c.page_errors()[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])

    # phone width: the cards stack, nothing scrolls sideways
    c.phone()
    c.open(s.url("/reel.html" + s.q(name)))
    c.wait_for("!!document.getElementById('kTalk')", 20)
    case("at phone width the card is whole and the page has no sideways scroll",
         c.js("document.documentElement.scrollWidth <= window.innerWidth + 1 && document.getElementById('kTalk').getBoundingClientRect().right <= window.innerWidth"))
    c.desktop()
