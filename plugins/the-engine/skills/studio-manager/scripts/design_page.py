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
    design_js_edit.py    DESIGN_EDIT_JS    the strip, the frames, the buttons, the Size slider, the keys, the tray of photos
    design_js_type.py    DESIGN_TYPE_JS    the rules for words, with no page in them (window.DesignType): where
                                           lines break, a font's name, a new text box
    design_js_text.py    DESIGN_TEXT_JS    text boxes, their style, the fonts and the font list (Designer.type)
    design_js_brand.py   DESIGN_BRAND_JS   the brand colors
    design_js_plan.py    DESIGN_PLAN_JS    the rules for templates, filling frames and saving, with no page in
                                           them (window.DesignPlan)
    design_js_paint.py   DESIGN_PAINT_JS   ONE way to draw a layout on a canvas: a saved slide, the preview and
                                           the gallery's little pictures (Designer.paint)
    design_js_designs.py DESIGN_DESIGNS_JS the shoot menu, the design's name, My designs, Duplicate, + New
                                           design (the gallery), Save as template, Fill empty frames
    design_js_save.py    DESIGN_SAVE_JS    Preview swipe, the profile grid's crop, and Save slides

SCRIPTS below is the order they go on the page. Each part finds window.Designer ready, and the page starts
(Designer.start()) only after every part is in place.

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
import this_computer  # noqa: E402
import arrange_page  # noqa: E402
import brand  # noqa: E402
from design_js_brand import DESIGN_BRAND_CSS, DESIGN_BRAND_JS  # noqa: E402
from design_js_core import DESIGN_CORE_JS  # noqa: E402
from design_js_designs import DESIGN_DESIGNS_CSS, DESIGN_DESIGNS_JS  # noqa: E402
from design_js_edit import DESIGN_EDIT_JS  # noqa: E402
from design_js_model import DESIGN_MODEL_JS  # noqa: E402
from design_js_paint import DESIGN_PAINT_JS  # noqa: E402
from design_js_plan import DESIGN_PLAN_JS  # noqa: E402
from design_js_save import DESIGN_SAVE_CSS, DESIGN_SAVE_JS  # noqa: E402
from design_js_text import DESIGN_TEXT_CSS, DESIGN_TEXT_JS  # noqa: E402
from design_js_type import DESIGN_TYPE_JS  # noqa: E402

DESIGN_CSS = """
:root{--sel:#2f7cf6;--wide:1320px;--row:34px}
html{scrollbar-gutter:stable}
html.d-locked{overflow:hidden}
body.designer .bar,body.designer .head{max-width:var(--wide)}
body.designer .bar{min-height:40px;padding:4px 0}
body.designer .bar .homelink{padding:5px 12px 5px 10px}
body.designer .head{padding:6px 0 4px;grid-template-columns:auto 1fr;column-gap:10px;row-gap:1px;align-items:baseline}
body.designer .head .eyebrow{grid-column:1}
body.designer h1{grid-column:2;font-size:19px}
body.designer .lede,body.designer .topline{grid-column:1/-1}
body.designer .lede{font-size:13.5px;line-height:1.4}
body.designer .topline{margin-top:6px}
.d-tools,.selbar,.stage,.tray{flex:none;width:100%;max-width:var(--wide);margin-left:auto;margin-right:auto}
.d-tools{display:flex;flex-wrap:wrap;gap:4px;align-items:stretch;margin-bottom:4px}
.group{position:relative;display:flex;flex-wrap:wrap;gap:4px;align-items:center;min-height:var(--row);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:3px 7px}
.group .lbl{color:var(--soft);font-size:12.5px;margin-right:1px;white-space:nowrap}
.group b{font-weight:650}
#slides-count{display:inline-block;min-width:2ch;text-align:center;font-variant-numeric:tabular-nums}
.tb{font:600 13px/1.2 var(--sans);border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:8px;padding:4px 8px;cursor:pointer;white-space:nowrap}
.tb:hover{border-color:var(--soft)}
.tb:disabled{opacity:.4;cursor:default}
.tb:disabled:hover{border-color:var(--line)}
.tb.main{background:var(--accent);border-color:var(--accent);color:#fff}
.tb.on{background:var(--sel);border-color:var(--sel);color:#fff}
@media(pointer:coarse){.tb{padding:9px 12px}}
.sw{width:22px;height:22px;border-radius:50%;padding:0;border:2px solid var(--line);cursor:pointer}
.sw.on{border-color:var(--sel)}
.group input[type=color]{width:26px;height:26px;border:0;padding:0;background:none;cursor:pointer}
.group input[type=range]{width:96px;margin:0}
#view-size{width:90px}
.hint{color:var(--soft);font-size:12.5px;margin:0}
label.hint{display:inline-flex;align-items:center;gap:5px;cursor:pointer;white-space:nowrap}
.gline{font-size:13px;color:var(--accent-d)}
.gline:empty{display:none}
.gline .tb{padding:2px 8px;font-size:12.5px}
.dname{font:650 14.5px/1.3 var(--sans);overflow-wrap:anywhere}
.savestate{display:inline-block;width:86px;font-size:12.5px;color:var(--soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:middle}
.savestate.bad{color:var(--accent-d)}
#toolline{margin:0 0 5px}
/* the bar for the selected thing: one line of words (the line a press brings, the help line, and Fill empty frames
   while there are any), then its buttons; with nothing selected, the help line alone in a quiet box. The lines a
   press on a tool brings (Slides, + Add text, Brand colors) are in this first line too, so a line never lies over
   other words and never covers a button. The help line has no claim of its own on the line (flex-basis 0): it
   fills what the lines a press brings and Fill leave, and gives way first when the line is full (its whole words
   are in its tooltip); a line a press brings is cut only when the lines alone are too long, and carries its words
   in its tooltip too. (A help line that shrank instead would leave the other line a fraction of a pixel short,
   and Chrome draws an ellipsis for that.) */
.selbar{display:flex;flex-direction:column;gap:4px;margin-bottom:6px}
.selcap{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;min-height:24px;font-size:12.5px;color:var(--soft)}
.selcap #selhint{flex:1 1 0%;min-width:0}
.selcap .gline{flex:0 1 auto;min-width:0;max-width:100%}
.selcap #fill-holes{flex:none;margin-left:auto}
.selrows{display:flex;flex-wrap:wrap;gap:4px;align-items:stretch}
.selbar.off .selrows{display:none}
.selbar.off .selcap{flex:1 1 auto;justify-content:center;border:1px solid var(--line);border-radius:10px;padding:6px 12px}
.selbar.off .selcap #selhint{text-align:center}
@media(max-width:767px){.selcap #fill-holes{margin-left:0}.selcap #selhint{flex-basis:auto}}
/* from 768 px up the bar's first line is one line (the help line gives way, cut at its end) and room is held under
   it for the selected thing's buttons: three rows between 768 and 1023 px, two from 1024 px up, where the rows
   are wide enough. So clicking a photo never moves the strip from under the pointer. */
@media(min-width:768px){
.selbar{min-height:calc(var(--row) * 3 + 36px)}
/* the Brand colors group takes whatever room is left in the slides' row and no more, so saving a fourth color
   never pushes Undo onto a row of its own: with more colors than fit, its swatches wrap inside the group (its
   row's own rule is in the brand colors' styles). The text's Color group does the same in its row. On a narrower
   window the rows are not rows, and the groups take their own width as before. */
#g-brand{flex:1 1 0;max-width:max-content}
.selrows #sel-color{flex:1 1 0;max-width:max-content}
.selbar:not(.off) .selcap{flex-wrap:nowrap;height:24px}
.selbar:not(.off) .selcap #selhint,.selbar:not(.off) .selcap .gline{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
}
@media(min-width:1024px){
.selbar{min-height:calc(var(--row) * 2 + 32px)}
}
/* between 1024 and 1180 the rows are tight: narrower boxes and sliders, a little less padding on a button and a
   group, the brand swatches the size of the background's, so six saved brand colors still sit on one line */
@media(max-width:1179px){.d-tools{gap:3px}.group{padding:3px 5px}.group .dz-name{width:180px}.group .tb.dz-strong{max-width:180px}.group .tx-words{width:180px}.group .fp-btn{min-width:140px;max-width:170px}.group input[type=range]{width:68px}#view-size{width:64px}.tb{padding:4px 6px}.sw{width:20px;height:20px}#g-brand .bc-row{gap:4px}#g-brand .bc-sw{width:20px;height:20px}}

.stage{position:sticky;top:0;z-index:20;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px 18px 16px;overflow-x:auto;overflow-y:hidden;overscroll-behavior-x:contain;box-shadow:0 -6px 0 0 var(--bg),var(--shadow),0 12px 20px -16px rgba(42,38,34,.45)}
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
.selbox{position:absolute;display:none;pointer-events:none}
.selbox.on{display:block}
.selbox .ring{position:absolute;top:0;right:0;bottom:0;left:0;outline:2px solid var(--sel);pointer-events:none}
.selbox.adj .ring{outline:2px dashed #f0a020}
.h.out{display:none}
.h{position:absolute;width:14px;height:14px;background:#fff;border:2px solid var(--sel);border-radius:3px;pointer-events:auto;touch-action:none}
.h::after{content:'';position:absolute;top:-6px;right:-6px;bottom:-6px;left:-6px}
.h.tl{left:-7px;top:-7px;cursor:nwse-resize}.h.br{right:-7px;bottom:-7px;cursor:nwse-resize}
.h.tr{right:-7px;top:-7px;cursor:nesw-resize}.h.bl{left:-7px;bottom:-7px;cursor:nesw-resize}
.selbox.adj .h,.selbox.fixed .h{display:none}
.guide{position:absolute;background:#f0508c;pointer-events:none}
.slidemark{position:absolute;top:0;bottom:0;display:none;outline:3px solid var(--accent);outline-offset:-3px;background:rgba(196,104,63,.14);pointer-events:none}
.d-note{margin:0 0 8px;font-size:13.5px;color:var(--accent-d);display:flex;flex-wrap:wrap;gap:8px;align-items:center;overflow-wrap:anywhere}
.d-note.quiet{color:var(--soft)}
.blk:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}

.tray{flex:1 0 auto;margin-top:14px;padding-bottom:28px}
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
    ("DESIGN_PLAN_JS", DESIGN_PLAN_JS),
    ("DESIGN_PAINT_JS", DESIGN_PAINT_JS),
    ("DESIGN_DESIGNS_JS", DESIGN_DESIGNS_JS),
    ("DESIGN_SAVE_JS", DESIGN_SAVE_JS),
]

# The styles of the parts added after the strip, in the order their scripts go on the page.
PART_CSS = DESIGN_TEXT_CSS + DESIGN_BRAND_CSS + DESIGN_DESIGNS_CSS + DESIGN_SAVE_CSS

# The four background swatches (the prototype's): name, colour.
SWATCHES = (("White", "#ffffff"), ("Cream", "#f4efe6"), ("Sand", "#e9e1d6"), ("Black", "#111111"))

LEDE = "Each box is one Instagram slide. A photo can stretch across slides, so they join up when people swipe."
TRAY_HINT = ("Drag a photo onto a slide to add it, or onto a frame to put it there. "
             "Click one to put it in the selected frame, or in the next empty spot.")
# The key that turns snapping off for a moment is Option on a Mac and Alt on a PC. A Mac's line is word for word
# what it was; a PC's names only its own key (unproven on a real PC: read from the browser's altKey, which is Alt there).
SNAP_TITLE = ("Photos line up with the slides and with each other as you drag. "
              + ("Hold Alt while you drag to turn it off for a moment." if this_computer.WINDOWS
                 else "Hold Option (Alt on a PC) while you drag to turn it off for a moment."))
# The bar at the bottom of the window: looking at the carousel as Instagram will show it, and saving it.
PREVIEW = "Preview swipe"
GRID_CROP = "Profile grid crop"
# The label of the slider that sets how large the slides are drawn on this page ("Size", as on Nicole's page; a
# text box has a Size of its own, so the slider's name for a screen reader says which this one is).
VIEW = "Size"
VIEW_LABEL = "How big the slides look"
SAVE_SLIDES = "Save slides"
SAVE_ANYWAY = "Save anyway"
GO_BACK = "Go back"
OPEN_CAROUSEL = "Open the Carousel folder"


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
        # The top row: the shoot and the open design. The scripts put the shoot menu before #g-design, a box to
        # type the name in beside #d-name (which is then hidden), and My designs, Duplicate design after it, then
        # + New design and Save as template in a group of their own.
        "<div class='d-tools' id='tools-designs'>"
        "<div class='group' id='g-design'><span class='lbl'>Design</span><b class='dname' id='d-name'></b>"
        "<span class='savestate' id='d-status' role='status'></span></div>"
        "</div>"
        # The second row: the whole carousel. The scripts add to it with Designer.tools.group(id, label): the
        # brand colors (put beside Background) and + Add text (before Size) are there. Preview swipe and Save
        # slides are in the bar at the bottom of the window.
        "<div class='d-tools' id='tools-main'>"
        "<div class='group' id='g-slides'><span class='lbl'>Slides</span>"
        "<button class='tb' id='slides-minus' type='button' aria-label='One fewer slide'>&minus;</button><b id='slides-count'></b>"
        "<button class='tb' id='slides-plus' type='button' aria-label='One more slide'>+</button></div>"
        "<div class='group' id='g-bg'><span class='lbl'>Background</span>" + swatches +
        "<input type='color' id='bgc' value='#ffffff' aria-label='Pick any background color' title='Pick any color'></div>"
        "<div class='group' id='g-view'><span class='lbl'>" + html.escape(VIEW) + "</span>"
        "<input type='range' id='view-size' min='40' max='480' value='230' aria-label='" + html.escape(VIEW_LABEL, quote=True) + "' title='" + html.escape(VIEW_LABEL, quote=True) + "'></div>"
        "<div class='group' id='g-snap'><label class='hint' title='" + html.escape(SNAP_TITLE, quote=True) + "'>"
        "<input type='checkbox' id='snap' checked aria-label='Snap into line'> Snap into line</label></div>"
        "<div class='group' id='g-undo'><button class='tb' id='undo' type='button' disabled>Undo</button></div>"
        "</div>"
        "<p class='gline' id='toolline' role='status'></p>"
        # The bar for the selected thing. One line first: the lines a press brings (#slides-line here; the + Add
        # text and Brand colors scripts put theirs beside it, and #selline is a selection button's), the help line
        # (#selhint), and, while the design has an empty frame, "Fill N empty frames" with its own line (both
        # put here by the designs script). Under it, the groups of buttons for the selected thing, added by the
        # scripts (Designer.selbar.group) into #selrows. With nothing selected the groups are hidden and the
        # help line sits alone in the room held for them, so the strip never moves when the selection changes.
        "<div class='selbar off' id='selbar'><div class='selcap' id='selcap'><span class='gline' id='slides-line' role='status'></span>"
        "<span class='gline' id='selline' role='status'></span>"
        "<span class='hint' id='selhint'></span></div><div class='selrows' id='selrows'></div></div>"
        "<section class='stage' id='stage'><div class='stripwrap' id='stripwrap'><div class='labels' id='labels'></div>"
        "<div class='strip' id='strip'></div><div class='over' id='over'></div></div></section>"
        "<section class='tray' id='tray'><div class='trayhead'><h2 id='trayname'>Photos</h2>"
        "<span class='prep' id='prep' hidden></span><span class='gline' id='trayline' role='status'></span></div>"
        "<p class='hint' id='trayhint'>" + html.escape(TRAY_HINT) + "</p>"
        "<div class='thumbs' id='thumbs'></div></section>"
        # The bar at the bottom of the window. Every line Save slides says, its two questions' buttons, and
        # "Open the Carousel folder" with the answer it brings, are here, beside the button that was pressed.
        # The bar is pinned to the bottom and grows upward, so the three buttons that are always there never
        # move when a line arrives.
        # Above its buttons the bar also holds every line the page says by itself (#d-note: a save that was
        # refused, a design changed somewhere else, the photos changed, with Reload beside it; #d-trouble: why
        # the last change is not saved yet; the fonts' line is put after these by its own script; #grid-line:
        # what the profile grid's tick shows). The bar is always in sight, and a line coming here moves nothing.
        "<div class='sv-bar' id='savebar'><div class='sv-notes' id='notes'>"
        "<p class='d-note' id='d-note' role='alert' hidden></p>"
        "<p class='d-note' id='d-trouble' role='status' hidden></p>"
        "<p class='d-note quiet' id='grid-line' hidden></p>"
        "</div><div class='sv-in'>"
        "<button class='tb' id='preview-btn' type='button' disabled>" + html.escape(PREVIEW) + "</button>"
        "<label class='hint'><input type='checkbox' id='gridcrop' aria-label='" + html.escape(GRID_CROP, quote=True) + "'> " + html.escape(GRID_CROP) + "</label>"
        "<button class='tb main' id='save-slides' type='button' disabled>" + html.escape(SAVE_SLIDES) + "</button>"
        "<span class='gline' id='save-line' role='status'></span>"
        "<button class='tb main sv-ans' id='save-yes' type='button' hidden>" + html.escape(SAVE_ANYWAY) + "</button>"
        "<button class='tb sv-ans' id='save-no' type='button' hidden>" + html.escape(GO_BACK) + "</button>"
        # the folder button and what pressing it brings: the answer is a small note right over the button,
        # so its coming never moves the button from under the pointer
        "<span class='sv-open sv-ans' id='open-wrap' hidden><button class='tb' id='open-carousel' type='button'>" + html.escape(OPEN_CAROUSEL) + "</button>"
        "<span class='sv-bub' id='open-line' role='status'></span></span>"
        "</div></div>"
        "</div>"
    )
    scripts = "".join("<script>" + src + "</script>" for _, src in SCRIPTS) + "<script>" + DESIGN_START_JS + "</script>"
    return _shell(brand.title("Carousel designer"), attrs, inner, scripts)


if __name__ == "__main__":
    print(len(page_html("A kit")), "characters")
