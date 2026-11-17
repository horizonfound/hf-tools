#!/usr/bin/env python3
"""The look of every page the Assistant shows, in one place.

Dustin, Nov 7: every page takes the reel page's style (Nicole's v19): DM Sans for everything, the cream
background, the dark ink, the coral accent; no serif anywhere in the pages themselves. "We'll probably change it
again", so the colours, the font and the few rules every page shares live here, and the next restyle is an edit
to this file.

What is here:
  FAMILY, FACES, FONT_ROUTE, font_css()   the plugin's own DM Sans files, served by each page's own server
                                          (nothing from the internet), under a name of the pages' own
  SANS                                    the font list every page uses
  COLORS, ROOT                            the colour names (:root) every page uses
  BASE                                    the few rules every page shares (body, the eyebrow, the Back to home
                                          button, the coral accent word, the path at the top)
  head_css()                              font_css() + ROOT + BASE: what goes first inside a page's <style>
  serve_font(handler, query)              answers GET /look-font?f=<file> for a page server
  crumbs(trail), kit_trail(kit_name)      the path at the top of every post kit page (Nicole's v27):
                                          Home › Hannah post kit › Reels › B-roll

What is not here, on purpose: the fonts the photographer picks for the words on their own slides and stories
(the designer's font lists, shared/fonts used for slide text, hooktext.py). Those are their design, not the
pages' look.

Why the pages call the font "Assistant Sans" and not "DM Sans": the designer lets the photographer choose
"DM Sans" for the words on a slide, and registers its own faces under that name. Giving the pages' copy its own
name keeps the page and the photographer's slide fonts from ever meeting. Same files, same letters.
"""
import html
import re
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parent.parent.parent / "shared" / "fonts"

FAMILY = "Assistant Sans"
# (the file in shared/fonts without its .ttf, its weight). DM Sans comes in these three; no italic, no 300, no 700.
FACES = (("DMSans-Regular", 400), ("DMSans-Medium", 500), ("DMSans-SemiBold", 600))
FACE_FILES = tuple(f for f, _ in FACES)          # the only names /look-font answers to
FONT_ROUTE = "/look-font"

# Segoe UI stays in the list for a PC whose page server is restarting (the font route down for a moment).
# 'DM Sans' is left out on purpose (Nov 7, the designer): a letter DM Sans does not have (the arrows, the little
# triangles) falls through to the next name in the list, and in the designer 'DM Sans' is the photographer's slide
# font, so the page itself was loading the photographer's DM Sans Bold for an arrow. With the name left out the
# page never asks for a slide font. Same letters either way when the route is up.
# -apple-system and BlinkMacSystemFont come right after it (Nov 7, review): the few symbols DM Sans lacks (the
# little triangle on "My designs", the ticks, the pens, the arrow on Open photo folder, the drag grips) are drawn
# in the Mac's own font, as the pickers drew them before, instead of whatever Chrome finds (Lucida Grande,
# PingFang, Apple Symbols). Neither name means anything on a PC, which goes on to Segoe UI.
SANS = "'Assistant Sans',-apple-system,BlinkMacSystemFont,'Helvetica Neue','Segoe UI',Arial,sans-serif"

# Every colour name the pages use. The first block is the reel page's own; the second is the backup report's
# extra palette (the first look, the stats bar, the legend), kept at the values it has always had.
COLORS = (
    ("cream", "#FAFAF6"),        # the page background
    ("paper", "#FFFFFF"),        # cards, panels, buttons
    ("ink", "#1F2430"),          # text, the main button
    ("ink-2", "#646B78"),        # quieter text
    ("coral", "#F07F5A"),        # hover borders, dashed lines
    ("coral-2", "#D4643F"),      # eyebrows, the accent word, selected things
    ("coral-l", "#FCE6DD"),      # tags, a result that went wrong
    ("sand-l", "#ECEAF6"),       # behind a photo still loading, disabled things
    ("line", "rgba(31,36,48,.12)"),   # every hairline and border
    ("long", "#2f7d57"), ("long-l", "#dcefe5"),     # Longer, a step done, a result that went right
    ("quick", "#7a5bb0"), ("quick-l", "#ebe3f7"),   # Quicker
    ("ink-deep", "#2F6F6B"), ("ocean", "#5EB5A9"), ("ocean-l", "#DCEFEA"),
    ("sun", "#F2CF72"), ("sun-l", "#FBF2D6"), ("lime", "#CDE9D6"),
)
COLOR = dict(COLORS)

ROOT = (":root{" + "".join("--%s:%s;" % kv for kv in COLORS)
        + "--sans:" + SANS + ";--ease:cubic-bezier(.2,.7,.2,1);--r:22px;"
        + "--shadow:0 30px 60px -30px rgba(31,36,48,.35)}")

# The rules every page shares. They come right after ROOT and before a page's own rules, so a page's own rule
# still wins where it has one. The last rule is the coral accent word ("Welcome back.", "verified."): the same
# letters as the line it sits in, upright, in coral. It takes the place of the old italic serif accent.
BASE = r"""
*{box-sizing:border-box}
body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.homelink{display:inline-flex;align-items:center;gap:.45em;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px;white-space:nowrap;transition:background .2s}.homelink:hover{background:var(--coral-2)}
h1 em,.swap,.accent{font:inherit;font-style:normal;color:var(--coral-2);letter-spacing:inherit;text-decoration:none}
"""

# The path at the top of every post kit page (Nicole's v27, crumbs.js: "so you don't have to just keep clicking
# back"): Home › Hannah post kit › Reels › B-roll. Her five rules, with her hover colour and her font named by the
# look's own names instead of #D4643F and 'DM Sans'. The last rule is ours: a saved copy of a page (body without
# .live, the kit page kept in the kit's hidden folder) has no server behind its links, so its path is drawn as
# plain words, the way the saved copy hides its Back to home.
CRUMBS = r"""
.crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;font:600 13.5px/1.3 var(--sans);min-width:0}
.crumbs a{color:inherit;text-decoration:none;padding:.42rem .75rem;border-radius:999px;background:rgba(128,128,128,.12)}
.crumbs a:hover{background:var(--coral-2);color:#fff}
.crumbs .sep{opacity:.45}
.crumbs .here{padding:.42rem .2rem;opacity:.75}
body:not(.live) .crumbs a{pointer-events:none;background:none;padding:.42rem .2rem;opacity:.75}
"""
BASE = BASE + CRUMBS

# Her words on the path (crumbs.js), whole. The steps after the post kit (Reels, Behind the scenes, Just photos,
# B-roll, Talking to camera, Carousel, Stories, Captions) are each page's own and are passed in by that page.
CRUMB_WORDS = {
    "home": "Home",
    "where": "Where you are",            # the nav's aria-label
    "post_kit": "{shoot} post kit",      # the kit's crumb: the folder name without its date
    "post_kit_none": "Post kit",         # the same crumb when there is no shoot (the unreachable page)
    "sep": "›",
}
HOME_PATH = "/home"                      # hers was a whole address with a port in it; every page here sits on the one server
DATE_FIRST = re.compile(r"^\d{4}-\d{2}-\d{2}\s+")


def short_name(name):
    """Hers (server.py short_name): the folder name without a leading date. The same rule as kit.short_name,
    copied here so the look never imports the post kit (tests/look_check.py holds the two equal)."""
    return DATE_FIRST.sub("", name) or name


def _path_only(href):
    """A crumb's link is a path of this server, never an address: it starts with one '/', and no '://' is in it.
    Anything else is refused here, so no page can ever carry her hard-coded address with its port."""
    if not isinstance(href, str) or not href.startswith("/") or href.startswith("//") or "://" in href or any(c in href for c in "\r\n\t"):
        raise ValueError("a crumb's link must be a path of this server, like /home, not %r" % (href,))
    return href


def crumbs(trail):
    """The path at the top of a post kit page, as HTML: Home, then every step in trail, each (label, href).
    Every step but the last is a link; the last is where you are (her .here, aria-current). A step given as
    (label, None) before the last is drawn as plain words too, never a dead link. Labels are escaped; a link
    must be a path of this server (see _path_only)."""
    steps = [(CRUMB_WORDS["home"], HOME_PATH)]
    for step in trail:
        if not isinstance(step, (tuple, list)) or len(step) != 2 or not isinstance(step[0], str) or not step[0].strip():
            raise ValueError("each step of the path is (label, href), the label a few words: %r" % (step,))
        steps.append((step[0], step[1]))
    out = []
    for i, (label, href) in enumerate(steps):
        last = i == len(steps) - 1
        if i:
            out.append("<span class='sep' aria-hidden='true'>%s</span>" % CRUMB_WORDS["sep"])
        if href is not None and not last:
            out.append("<a href='%s'>%s</a>" % (html.escape(_path_only(href), quote=True), html.escape(label)))
        elif last:
            out.append("<span class='here' aria-current='page'>%s</span>" % html.escape(label))
        else:
            out.append("<span class='here'>%s</span>" % html.escape(label))
    return "<nav class='crumbs' aria-label='%s'>%s</nav>" % (CRUMB_WORDS["where"], "".join(out))


def kit_page_path(kit_name):
    """The post kit page's path on the posting server, from the kit's folder name (never a path on the disk)."""
    return "/content/" + quote(kit_name, safe="") + "/Post%20kit.html"


def kit_trail(kit_name):
    """The first step after Home on every page of a kit: 'Hannah post kit', linked to the kit page. A page adds its
    own steps after it: kit_trail(kit) + [('Reels', '/reel.html?kit=...'), ('B-roll', None)]."""
    return [(CRUMB_WORDS["post_kit"].format(shoot=short_name(kit_name)), kit_page_path(kit_name))]


def font_css(route=FONT_ROUTE):
    """The @font-face rules for the plugin's own DM Sans, from a page server's own font route."""
    return "".join(
        "@font-face{font-family:'%s';src:url('%s?f=%s') format('truetype');font-weight:%d;font-style:normal;"
        "font-display:swap}" % (FAMILY, route, key, wt) for key, wt in FACES)


def head_css(route=FONT_ROUTE):
    """What goes first inside a page's <style>: the fonts, the colour names, the shared rules."""
    return font_css(route) + ROOT + BASE


def serve_font(handler, query):
    """Answer GET /look-font?f=<one of FACE_FILES> on a page server's handler. Exactly one f, and only a name on
    the list: never a path from the request. The caller has already checked who is asking (its host check)."""
    try:
        q = parse_qs(query or "", keep_blank_values=True)
    except ValueError:
        return handler.send_error(404)
    vals = q.get("f") or []
    if len(vals) != 1 or len(q) != 1 or vals[0] not in FACE_FILES:
        return handler.send_error(404)
    try:
        data = (FONT_DIR / (vals[0] + ".ttf")).read_bytes()
    except OSError:
        return handler.send_error(404)
    handler.send_response(200)
    handler.send_header("Content-Type", "font/ttf")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "private, max-age=604800")
    handler.end_headers()
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass                                      # the page moved on; that's normal
