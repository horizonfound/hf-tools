#!/usr/bin/env python3
"""The `door` part of tests/talking_page_check.py (Stage E of docs/handoff-v24-build-2026-11-12.md): the way in to
the talking reel page. Not run by itself:

    python3 tests/guard.py 3000 python3 tests/talking_page_check.py --only door

talking_page_check.py hands this file itself (`t`: its Setup class, its helpers), its Setup (`s`) and, for the
page, its hidden Chrome (`c`).

The door is step 1's third card on the reel page (Nicole's v23 reel-maker.html: <a class="opt" id="modeTalk">,
"Talking to camera"). What is checked:
  * her two lines and her one style rule, against her own v23 page when her handoff is on this computer (SKIP
    when it is not; it is never in the repository), and that they are in reel_page.WORDS, not written twice;
  * the card is a plain link written on the server (it works before any script runs), third after the two
    choices, to the talking page of the SAME shoot, by folder name and never by a path, for a shoot whose name has
    an accent, an ampersand, quotes, an emoji and (off a PC) a tag;
  * following it by request gives that shoot's talking page, and the talking page's own way back goes to our post
    kit page;
  * on the real page: it sits third with the same look as the other two, is not underlined, never gets the tick,
    and a press on it opens the talking page for the same shoot and leaves the reel page's record, and every other
    file the Assistant keeps for the shoot, exactly as they were.

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
HER_S = "You talk about the shoot; your photos go with what you say. Opens its own page."
HER_RULE = "a.opt{text-decoration:none;display:block}"


def kit_name(t):
    return KIT_WIN if t.WINDOWS else KIT_MAC


def her_v23():
    """Her v23 reel page, or None when her handoff is not on this computer."""
    here = Path(__file__).resolve().parent.parent
    for base in (here, here.parent / "hf-tools"):
        for h in sorted((base / "reference-private").glob("nicole-handoff-v23-*")):
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

    # ---- her words and her style rule
    case("her two lines are in reel_page.WORDS, word for word", rp.WORDS.get("foot_talk_b") == HER_B and rp.WORDS.get("foot_talk_s") == HER_S,
         (rp.WORDS.get("foot_talk_b"), rp.WORDS.get("foot_talk_s")))
    src = Path(rp.__file__).read_text(encoding="utf-8")
    case("...each written once (the page reads them from WORDS)", src.count('"' + HER_B + '"') == 1 and src.count(HER_S) == 1)
    case("her one style rule is in the page's styles, right after the rule hers follows",
         ".opt{position:relative}\n" + HER_RULE + "\n" in rp.STYLE and rp.STYLE.count("a.opt{") == 1)
    hers = her_v23()
    if hers is None:
        t.skip("the card against her own v23 page: her handoff (reference-private) isn't on this computer")
    else:
        m = re.search(r'<a class="opt" id="modeTalk" href="talking-reel\.html"><b>(.*?)</b><span>(.*?)</span></a>', hers)
        case("hers, from her v23 reel-maker.html: the same two lines", bool(m) and (html.unescape(m.group(1)), html.unescape(m.group(2))) == (HER_B, HER_S),
             m and m.groups())
        case("...and the same style rule, after the same rule", ".opt{position:relative}\n" + HER_RULE + "\n" in hers)
        choice = re.search(r'<div class="choice">(.*?)</div>', hers, re.S).group(1)
        case("...hers has it third, after her two choices", re.findall(r'id="(mode\w+)"', choice) == ["modeBts", "modePhotos", "modeTalk"])
        case("...and hers gives it the shoot in its address, nothing else", "$('modeTalk').href = 'talking-reel.html?shoot=' + encodeURIComponent(SHOOT)" in hers
             and hers.count("modeTalk") == 2)

    # ---- the card as the server writes it
    page = rp.page_html(name, short, True)
    choice = re.search(r"<div class='choice'>(.*?)</div>", page, re.S).group(1)
    case("the card is third in step 1, after the two choices", re.findall(r"id='(mode\w+)'", choice) == ["modeBts", "modePhotos", "modeTalk"], choice[:300])
    m = re.search(r"<a class='opt' id='modeTalk' href='([^']*)'><b>(.*?)</b><span>(.*?)</span></a>", choice)
    case("it is a plain link with the look of the two choices (class opt), written on the server", bool(m), choice[-300:])
    href = html.unescape(m.group(1)) if m else ""
    case("her words on it", bool(m) and (html.unescape(m.group(2)), html.unescape(m.group(3))) == (HER_B, HER_S))
    case("it goes to the talking page of the same shoot, by its folder name", href == "/talking.html?kit=" + quote(name) and unquote(href.split("kit=")[1]) == name, href)
    case("no path in it, and nothing left of the place it is written into", "/private" not in href and str(kit) not in page and rp.TALK_SPOT not in page)
    case("the card is on the page once", page.count("id='modeTalk'") == 1)
    js = "".join(re.findall(r"<script>(.*?)</script>", page, re.S))
    case("no script touches the card: it chooses nothing, saves nothing and never gets the tick", "modeTalk" not in js)
    case("a name that could break an address is held whole", "kit=" + quote("a&b=c #1?x") + "'" in rp.talk_card(rp.WORDS, "a&b=c #1?x")
         and "&" not in rp.talk_card(rp.WORDS, "a&b=c #1?x").split("href='")[1].split("'")[0])
    case("a PC gets the same card (the talking page itself says what a PC can't do yet)", "this_computer" not in rp.talk_card.__code__.co_names)

    # ---- by request
    code, _j, raw, _h = s.http("GET", "/reel.html" + s.q(name))
    served = raw.decode("utf-8", "replace")
    case("the reel page the server sends has the card, to this shoot", code == 200 and ("href='" + html.escape(href, quote=True) + "'") in served, code)
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
    import reel_page as rp
    name = kit_name(t)
    kit = s.kit(name)
    short = name[11:]
    c.open(s.url("/reel.html" + s.q(name)))
    c.wait_for("!!(document.getElementById('modeTalk') && document.getElementById('modePhotos').onclick)", 20, tell="document.body.innerText.slice(0, 200)")
    look = c.js("""(function(){
      function L(id){ var x = document.getElementById(id), cs = getComputedStyle(x), r = x.getBoundingClientRect();
        return {tag: x.tagName, b: x.querySelector('b').textContent, s: x.querySelector('span').textContent, border: cs.borderTopWidth + ' ' + cs.borderTopStyle + ' ' + cs.borderTopColor,
                radius: cs.borderTopLeftRadius, pad: cs.paddingTop + ' ' + cs.paddingLeft, bg: cs.backgroundColor, deco: cs.textDecorationLine, disp: cs.display,
                bfont: getComputedStyle(x.querySelector('b')).font, sfont: getComputedStyle(x.querySelector('span')).font, scol: getComputedStyle(x.querySelector('span')).color,
                bcol: getComputedStyle(x.querySelector('b')).color, w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), left: Math.round(r.left), on: x.classList.contains('on'),
                cursor: cs.cursor}; }
      return {ids: Array.from(document.querySelectorAll('#step0 .choice > *')).map(function(x){ return x.id; }), a: L('modeBts'), b: L('modePhotos'), t: L('modeTalk'),
              href: document.getElementById('modeTalk').getAttribute('href')};
    })()""")
    a, b, k = look["a"], look["b"], look["t"]
    case("on the page: three choices in step 1, the card third", look["ids"] == ["modeBts", "modePhotos", "modeTalk"], look["ids"])
    case("her words on the card", (k["b"], k["s"]) == (HER_B, HER_S), (k["b"], k["s"]))
    same = ("border", "radius", "pad", "bg", "bfont", "sfont", "scol", "bcol", "cursor")
    case("the card has the look of the other two (border, corners, room inside, colours, type)", not [x for x in same if k[x] != b[x]], [(x, k[x], b[x]) for x in same if k[x] != b[x]])
    case("...is a link, a block, and is not underlined (her one style rule)", k["tag"] == "A" and k["disp"] == "block" and k["deco"] == "none", (k["tag"], k["disp"], k["deco"]))
    case("...sits in the same row, after them, the same width", k["top"] == b["top"] and k["left"] > b["left"] > a["left"] and abs(k["w"] - b["w"]) <= 1, (a, b, k))

    # choose one of the real two, then the other: the card never gets the tick
    c.click("#modePhotos")
    c.wait_for("document.getElementById('modePhotos').classList.contains('on')", 5)
    on1 = c.js("document.getElementById('modeTalk').classList.contains('on')")
    c.click("#modeBts")
    c.wait_for("document.getElementById('modeBts').classList.contains('on')", 5)
    on2 = c.js("document.getElementById('modeTalk').classList.contains('on')")
    c.click("#modePhotos")
    c.wait_for("document.getElementById('modePhotos').classList.contains('on')", 5)
    case("the card never gets the tick, whichever of the two is chosen", on1 is False and on2 is False)
    rec = kit / ".kit" / "reel-page.json"
    t.wait_for(lambda: rec.is_file() and '"footage": false' in rec.read_text(encoding="utf-8").replace("False", "false"), 10)
    # let the page's saves and follow-ups finish, so what is compared is a page at rest
    last = [None, 0]

    def still():
        now = kept(kit)
        last[1] = last[1] + 1 if now == last[0] else 0
        last[0] = now
        return last[1] >= 6
    t.wait_for(still, 20, every=0.25)
    before = kept(kit)
    case("(the reel page has a record to leave alone)", ".kit/reel-page.json".replace("/", __import__("os").sep) in before, sorted(before))
    c.clear_errors()
    c.click("#modeTalk")
    c.wait_for("location.pathname === '/talking.html' && window.Talk && window.Talk.loaded", 20, tell="location.href")
    case("a press on the card opens the talking page", c.js("location.pathname") == "/talking.html")
    case("...for the same shoot", c.js("document.body.dataset.kit") == name and unquote(c.js("location.search")) == "?kit=" + name, c.js("location.search"))
    case("...with her title for it", c.js("document.title") == s.tp.page_words()["doc_title"].replace("{short}", short), c.js("document.title"))
    import time
    time.sleep(1.5)
    after = kept(kit)
    reel = lambda d: {x: v for x, v in d.items() if "reel" in x or x.endswith("kit.json") or "arrange" in x}   # noqa: E731
    case("the press left the reel page's record exactly as it was", reel(after) == reel(before) and (".kit" + __import__("os").sep + "reel-page.json") in after,
         [x for x in set(before) | set(after) if before.get(x) != after.get(x)])
    new = [x for x in after if x not in before]
    made = [x for x in new if Path(x).name in ("talking.json", "talking.prev.json", "talking-words.json") or Path(x).parts[0] == "Talking"]
    case("opening the talking page makes no talking record, no words file and no Talking folder", not made and not (kit / "Talking").exists()
         and not (kit / ".kit" / "talking.json").exists() and not (kit / ".kit" / "talking-words.json").exists(), made)
    case("...and nothing new at all outside the hidden folder's talking files", not [x for x in new if not (Path(x).parts[0] == ".kit" and "talking" in Path(x).name)], new)
    c.click("#back")
    c.wait_for("location.pathname.indexOf('/content/') === 0", 15, tell="location.href")
    case("the talking page's way back is our post kit page for the same shoot", unquote(c.js("location.pathname")) == "/content/" + name + "/Post kit.html", c.js("location.pathname"))
    case("no page errors on the way through", not c.page_errors(), c.page_errors()[:3])
    case("nothing asked of the internet", not c.outside_requests(), c.outside_requests()[:3])

    # phone width: three cards stack, nothing scrolls sideways
    c.phone()
    c.open(s.url("/reel.html" + s.q(name)))
    c.wait_for("!!document.getElementById('modeTalk')", 20)
    case("at phone width the card is whole and the page has no sideways scroll",
         c.js("document.documentElement.scrollWidth <= window.innerWidth + 1 && document.getElementById('modeTalk').getBoundingClientRect().right <= window.innerWidth"))
    c.desktop()
