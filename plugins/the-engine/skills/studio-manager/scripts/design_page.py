#!/usr/bin/env python3
"""The carousel designer's page: a strip of slides the photographer lays photos out on.

    page_html(kit_name)     the page (served live by posting_queue.py through design.handle_get)
    plain_page(words)       a small page with the Back to home button, for "can't find that shoot"

The page is put together by plain joining. Only the kit's folder name goes into it (html-escaped, as a data-
attribute); the scripts ask /design-state for everything else. All JavaScript is in raw strings in sibling
files, so nothing Python does can change a character of it:

    design_js_model.py   DESIGN_MODEL_JS   the rules, with no page in them (window.DesignModel)
    design_js_core.py    DESIGN_CORE_JS    the state, one way to change it, one drawing pass, one save queue,
                                           Undo, and the places other parts add themselves (window.Designer)
    design_js_edit.py    DESIGN_EDIT_JS    the strip, the frames, the buttons, the keys, the tray of photos
    design_js_type.py    DESIGN_TYPE_JS    the rules for words, with no page in them (window.DesignType): where
                                           lines break, a font's name, a new text box
    design_js_text.py    DESIGN_TEXT_JS    text boxes, their style, the fonts and the font list (Designer.type)
    design_js_brand.py   DESIGN_BRAND_JS   the brand colors

SCRIPTS below is the order they go on the page. A later part (text and fonts; designs, templates and Save
slides) adds its own string to that list, after the ones here: it finds window.Designer ready, and the page
starts (Designer.start()) only after every part is in place.

The look is the pickers' (arrange_page.CSS: Nicole's colours, the system's own font, light only) with the
designer's own pieces in DESIGN_CSS (and the text and brand-color parts' own, beside their scripts). The
page's own chrome loads nothing from the internet. The ONE thing the page may load from the internet is a
Google Fonts stylesheet and its font files, for the words on the slides, and only through the address the
Assistant sends with the state (design.GOOGLE_CSS): no address on the internet is written in this page.
Nothing that matters is kept in the browser: every change is saved to the kit by POST /design.
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arrange_page  # noqa: E402
import brand  # noqa: E402
from design_js_brand import DESIGN_BRAND_CSS, DESIGN_BRAND_JS  # noqa: E402
from design_js_core import DESIGN_CORE_JS  # noqa: E402
from design_js_edit import DESIGN_EDIT_JS  # noqa: E402
from design_js_model import DESIGN_MODEL_JS  # noqa: E402
from design_js_text import DESIGN_TEXT_CSS, DESIGN_TEXT_JS  # noqa: E402
from design_js_type import DESIGN_TYPE_JS  # noqa: E402

DESIGN_CSS = """
:root{--sel:#2f7cf6;--wide:1320px}
body.designer .bar,body.designer .head{max-width:var(--wide)}
body.designer .head{padding:10px 0 10px}
body.designer h1{font-size:19px}
body.designer .lede{font-size:13.5px}
.d-tools,.stage,.tray,.d-note{flex:none;width:100%;max-width:var(--wide);margin-left:auto;margin-right:auto}
.d-tools{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px}
.group{display:flex;flex-wrap:wrap;gap:5px;align-items:center;min-height:38px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:4px 7px}
.group .lbl{color:var(--soft);font-size:12.5px;margin-right:2px}
.group b{font-weight:650}
.tb{font:600 13px/1.2 var(--sans);border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:8px;padding:6px 9px;cursor:pointer}
.tb:hover{border-color:var(--soft)}
.tb:disabled{opacity:.4;cursor:default}
.tb:disabled:hover{border-color:var(--line)}
.tb.main{background:var(--accent);border-color:var(--accent);color:#fff}
.tb.on{background:var(--sel);border-color:var(--sel);color:#fff}
@media(pointer:coarse){.tb{padding:10px 12px}}
.sw{width:24px;height:24px;border-radius:50%;padding:0;border:2px solid var(--line);cursor:pointer}
.sw.on{border-color:var(--sel)}
.group input[type=color]{width:28px;height:28px;border:0;padding:0;background:none;cursor:pointer}
.group input[type=range]{width:110px}
.hint{color:var(--soft);font-size:12.5px;margin:0}
label.hint{display:inline-flex;align-items:center;gap:5px;cursor:pointer}
.gline{font-size:13.5px;color:var(--accent-d)}
.gline:empty{display:none}
.dname{font:650 14.5px/1.3 var(--sans);overflow-wrap:anywhere}
.savestate{font-size:12.5px;color:var(--soft);min-width:52px}
.savestate.bad{color:var(--accent-d)}
.selbar{min-height:50px;margin-bottom:18px}
.selbar.off .needsel{opacity:.4;pointer-events:none}
.selbar #selhint{flex:1 0 100%;min-height:18px}

.stage{position:sticky;top:0;z-index:20;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:30px 18px 18px;overflow-x:auto;overflow-y:hidden;overscroll-behavior-x:contain;box-shadow:0 -14px 0 0 var(--bg),var(--shadow),0 12px 20px -16px rgba(42,38,34,.45)}
.stripwrap{position:relative;display:inline-block;vertical-align:top}
.labels{position:absolute;left:0;top:-22px;height:20px;width:100%;pointer-events:none}
.labels span{position:absolute;top:0;font-size:12px;color:var(--soft);transform:translateX(-50%);white-space:nowrap}
.strip{position:relative;overflow:hidden;touch-action:none;user-select:none;-webkit-user-select:none;box-shadow:0 0 0 1px var(--line)}
.over{position:absolute;top:0;right:0;bottom:0;left:0;pointer-events:none;z-index:5}
.seam{position:absolute;top:0;bottom:0;width:0;border-left:1.5px dashed rgba(47,124,246,.75);pointer-events:none;z-index:9000}
.blk{position:absolute;overflow:hidden;cursor:move;background:var(--line)}
.blk img{position:absolute;max-width:none;pointer-events:none;-webkit-user-drag:none;user-select:none}
.blk.hole{background:repeating-linear-gradient(45deg,rgba(120,110,100,.16) 0 10px,rgba(120,110,100,.26) 10px 20px);box-shadow:inset 0 0 0 1.5px rgba(120,110,100,.55);display:flex;align-items:center;justify-content:center;text-align:center;color:#5c534a;font-weight:600}
.blk .drop{background:rgba(255,253,249,.85);border-radius:6px;padding:2px 6px;pointer-events:none}
.blk .cant{position:absolute;top:0;right:0;bottom:0;left:0;display:grid;place-items:center;padding:6px;text-align:center;font-size:11.5px;line-height:1.3;color:var(--ink);pointer-events:none}
.blk .bd{position:absolute;top:0;right:0;bottom:0;left:0;pointer-events:none}
.blk.adj{cursor:grab}
.blk.droptarget{outline:3px solid var(--accent);outline-offset:-3px}
.blk.other{background:transparent;outline:1.5px dashed rgba(120,110,100,.7);outline-offset:-1px;color:var(--ink);white-space:pre-wrap;text-align:center;line-height:1.15}
.selbox{position:absolute;display:none;outline:2px solid var(--sel);pointer-events:none}
.selbox.on{display:block}
.selbox.adj{outline:2px dashed #f0a020}
.h{position:absolute;width:14px;height:14px;background:#fff;border:2px solid var(--sel);border-radius:3px;pointer-events:auto;touch-action:none}
.h::after{content:'';position:absolute;top:-6px;right:-6px;bottom:-6px;left:-6px}
.h.tl{left:-7px;top:-7px;cursor:nwse-resize}.h.br{right:-7px;bottom:-7px;cursor:nwse-resize}
.h.tr{right:-7px;top:-7px;cursor:nesw-resize}.h.bl{left:-7px;bottom:-7px;cursor:nesw-resize}
.selbox.adj .h,.selbox.fixed .h{display:none}
.guide{position:absolute;background:#f0508c;pointer-events:none}
.slidemark{position:absolute;top:0;bottom:0;display:none;outline:3px solid var(--accent);outline-offset:-3px;background:rgba(196,104,63,.14);pointer-events:none}
.d-note{margin-top:10px;font-size:13.5px;color:var(--accent-d);display:flex;flex-wrap:wrap;gap:8px;align-items:center}

.tray{flex:1 0 auto;margin-top:18px;padding-bottom:28px}
.trayhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;margin:0 0 2px}
.tray h2{margin:0;font:650 16px/1.3 var(--sans)}
.tray .prep{font-size:13.5px;color:var(--soft)}
.tray .hint{margin:0 0 10px}
.thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:8px;align-items:start}
@media(max-width:520px){.thumbs{grid-template-columns:repeat(auto-fill,minmax(68px,1fr));gap:6px}}
.th{position:relative;aspect-ratio:2/3;border-radius:8px;overflow:hidden;cursor:grab;background:var(--line);touch-action:pan-y;user-select:none;-webkit-user-select:none;outline:0}
.th.wide{aspect-ratio:3/2;grid-column:span 2}
.th img{position:absolute;top:0;left:0;display:block;width:100%;height:100%;object-fit:cover;pointer-events:none;-webkit-user-drag:none;user-select:none;transition:opacity .15s}
.th .num{position:absolute;top:4px;left:4px;padding:0 5px;border-radius:5px;background:rgba(0,0,0,.6);color:#fff;font:400 11.5px/1.5 var(--sans);pointer-events:none}
.th .tick{position:absolute;right:5px;bottom:5px;width:20px;height:20px;border-radius:50%;background:var(--accent);color:#fff;font:700 12px/20px var(--sans);text-align:center;pointer-events:none;display:none}
.th.used .tick{display:block}
.th.used img{opacity:.6}
.th .cant{position:absolute;top:0;right:0;bottom:0;left:0;display:none;place-items:center;padding:22px 5px 5px;text-align:center;font-size:11px;line-height:1.3;color:var(--ink);pointer-events:none}
.th.cantread .cant{display:grid}
.th.dragging{opacity:.35}
.th:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}

body.d-dragging,body.d-dragging *{user-select:none!important;-webkit-user-select:none!important}
.d-lift{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;will-change:transform;transform-origin:0 0}
.d-lift .pic{width:100%;height:100%;border-radius:8px;overflow:hidden;background:var(--line);box-shadow:0 0 0 3px #fff,0 18px 36px -12px rgba(0,0,0,.5)}
.d-lift .pic img{display:block;width:100%;height:100%;object-fit:cover}
.d-lift .say{position:absolute;left:50%;top:100%;transform:translateX(-50%);margin-top:8px;white-space:nowrap;background:var(--ink);color:#fff;font:600 12.5px/1 var(--sans);padding:6px 10px;border-radius:8px;display:none}
.d-lift .say.on{display:block}
"""

# The page starts only when every part is on it.
DESIGN_START_JS = r"""
window.Designer.start();
"""

# The scripts, in the order they go on the page. A later part of the build appends (name, string) here.
SCRIPTS = [
    ("DESIGN_MODEL_JS", DESIGN_MODEL_JS),
    ("DESIGN_CORE_JS", DESIGN_CORE_JS),
    ("DESIGN_EDIT_JS", DESIGN_EDIT_JS),
    ("DESIGN_TYPE_JS", DESIGN_TYPE_JS),
    ("DESIGN_TEXT_JS", DESIGN_TEXT_JS),
    ("DESIGN_BRAND_JS", DESIGN_BRAND_JS),
    # HOOK (stage D): ("DESIGN_DESIGNS_JS", ...)  designs bar, gallery, templates, shoot menu, preview, Save slides
]

# The styles of the parts added after the strip, in the order their scripts go on the page.
PART_CSS = DESIGN_TEXT_CSS + DESIGN_BRAND_CSS

# The four background swatches (the prototype's): name, colour.
SWATCHES = (("White", "#ffffff"), ("Cream", "#f4efe6"), ("Sand", "#e9e1d6"), ("Black", "#111111"))

LEDE = "Each box is one Instagram slide. A photo can stretch across slides, so they join up when people swipe."
TRAY_HINT = ("Drag a photo onto a slide to add it, or onto a frame to put it there. "
             "Click one to put it in the selected frame, or in the next empty spot.")
SNAP_TITLE = ("Photos line up with the slides and with each other as you drag. "
              "Hold Option (Alt on a PC) while you drag to turn it off for a moment.")


def plain_page(words):
    """A small page for when there is nothing to design: the words, and the way back home."""
    return arrange_page.plain_page(words)


def _shell(title, body_attrs, inner, scripts=""):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>" + html.escape(title) + "</title><style>" + arrange_page.CSS + DESIGN_CSS + PART_CSS + "</style></head>"
            "<body class='designer'" + body_attrs + ">"
            "<div class='wrap'><div class='bar'>" + arrange_page.BACK_HOME + brand.bar()
            + inner + scripts + "</body></html>")


def page_html(kit_name):
    """The designer for one shoot. Everything else arrives by /design-state."""
    attrs = " data-kit='" + html.escape(kit_name, quote=True) + "'"
    swatches = "".join(
        "<button class='sw' type='button' data-c='" + c + "' style='background:" + c + "' aria-label='" + name + "' title='" + name + "'></button>"
        for name, c in SWATCHES)
    inner = (
        "<a class='kitlink' id='kitlink' hidden>Back to the post kit</a></div>"
        "<header class='head'><span class='eyebrow'>Carousel designer</span><h1 id='title'></h1>"
        "<p class='lede'>" + html.escape(LEDE) + "</p>"
        "<p class='topline' id='l-reach' hidden></p><p class='topline' id='l-missing' hidden></p><p class='topline' id='l-dropped' hidden></p>"
        "</header>"
        # The top row: the open design. HOOK (stage D): the shoot menu goes before #g-design; the name becomes a
        # box, and My designs, Duplicate, + New design, Save as template and Fill empty frames are added to this
        # row with Designer.tools.group(id, label, 'tools-designs').
        "<div class='d-tools' id='tools-designs'>"
        "<div class='group' id='g-design'><span class='lbl'>Design</span><b class='dname' id='d-name'></b>"
        "<span class='savestate' id='d-status' role='status'></span></div>"
        "</div>"
        # The second row: the whole carousel. The scripts add to it with Designer.tools.group(id, label): the
        # brand colors (put beside Background) and + Add text are there; HOOK (stage D): Preview swipe and
        # Save slides.
        "<div class='d-tools' id='tools-main'>"
        "<div class='group' id='g-slides'><span class='lbl'>Slides</span>"
        "<button class='tb' id='slides-minus' type='button' aria-label='One fewer slide'>&minus;</button><b id='slides-count'></b>"
        "<button class='tb' id='slides-plus' type='button' aria-label='One more slide'>+</button>"
        "<span class='gline' id='slides-line' role='status'></span></div>"
        "<div class='group' id='g-bg'><span class='lbl'>Background</span>" + swatches +
        "<input type='color' id='bgc' value='#ffffff' aria-label='Pick any background color' title='Pick any color'></div>"
        "<div class='group' id='g-view'><span class='lbl'>Size</span>"
        "<button class='tb' id='view-smaller' type='button'>Smaller</button><button class='tb' id='view-bigger' type='button'>Bigger</button></div>"
        "<div class='group' id='g-snap'><label class='hint' title='" + html.escape(SNAP_TITLE, quote=True) + "'>"
        "<input type='checkbox' id='snap' checked> Snap into line</label></div>"
        "<div class='group' id='g-undo'><button class='tb' id='undo' type='button' disabled>Undo</button></div>"
        "</div>"
        "<p class='gline' id='toolline' role='status'></p>"
        # The bar for the selected thing: its groups are added by the scripts (Designer.selbar.group). The line a
        # press brings (#selline) and the help line (#selhint) sit in the bar itself, beside the buttons.
        "<div class='d-tools selbar off' id='selbar'><span class='gline' id='selline' role='status'></span>"
        "<span class='hint' id='selhint'></span></div>"
        "<section class='stage' id='stage'><div class='stripwrap' id='stripwrap'><div class='labels' id='labels'></div>"
        "<div class='strip' id='strip'></div><div class='over' id='over'></div></div></section>"
        "<p class='d-note' id='d-note' hidden></p>"
        "<section class='tray' id='tray'><div class='trayhead'><h2 id='trayname'>Photos</h2>"
        "<span class='prep' id='prep' hidden></span><span class='gline' id='trayline' role='status'></span></div>"
        "<p class='hint' id='trayhint'>" + html.escape(TRAY_HINT) + "</p>"
        "<div class='thumbs' id='thumbs'></div></section>"
        "</div>"
    )
    scripts = "".join("<script>" + src + "</script>" for _, src in SCRIPTS) + "<script>" + DESIGN_START_JS + "</script>"
    return _shell(brand.title("Carousel designer"), attrs, inner, scripts)


if __name__ == "__main__":
    print(len(page_html("A kit")), "characters")
