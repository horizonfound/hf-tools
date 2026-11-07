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
                                          button, the coral accent word)
  head_css()                              font_css() + ROOT + BASE: what goes first inside a page's <style>
  serve_font(handler, query)              answers GET /look-font?f=<file> for a page server

What is not here, on purpose: the fonts the photographer picks for the words on their own slides and stories
(the designer's font lists, shared/fonts used for slide text, hooktext.py). Those are their design, not the
pages' look.

Why the pages call the font "Assistant Sans" and not "DM Sans": the designer lets the photographer choose
"DM Sans" for the words on a slide, and registers its own faces under that name. Giving the pages' copy its own
name keeps the page and the photographer's slide fonts from ever meeting. Same files, same letters.
"""
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parent.parent.parent / "shared" / "fonts"

FAMILY = "Assistant Sans"
# (the file in shared/fonts without its .ttf, its weight). DM Sans comes in these three; no italic, no 300, no 700.
FACES = (("DMSans-Regular", 400), ("DMSans-Medium", 500), ("DMSans-SemiBold", 600))
FACE_FILES = tuple(f for f, _ in FACES)          # the only names /look-font answers to
FONT_ROUTE = "/look-font"

# Segoe UI stays in the list for a PC whose page server is restarting (the font route down for a moment).
SANS = "'Assistant Sans','DM Sans','Helvetica Neue','Segoe UI',Arial,sans-serif"

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
