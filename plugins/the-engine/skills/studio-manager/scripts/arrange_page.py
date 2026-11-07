#!/usr/bin/env python3
"""The picker page: the photos in a reel or a carousel, in order, with every photo of the shoot below.

    page_html(kit_name, piece)     the page (served live by posting_queue.py through arrange.handle_get)
    plain_page(words)              a small page with the Back to home button, for "can't find that shoot"

The page is put together by plain joining. Only the kit's folder name and the piece go into it (html-escaped,
as data- attributes); the script asks /arrange-state for everything else. All JavaScript is in raw strings, so
nothing Python does can change a character of it. Nothing is loaded from the internet: no font link, no
library. Nothing is kept in the browser's storage: every change is saved to the kit by POST /arrange.

The look (Nov 6) follows the picker pages Nicole's own Claude made: the system's own font (a Mac's, a PC's),
warm paper colours, one terracotta accent, same-size tall tiles with the picture cut to fill them, and the two
main buttons in a bar held at the bottom of the window. Light only: no other page of the Assistant goes dark,
so this one does not either. The drag measures real boxes: the row's own box (#rowwrap), each row tile and
its picture (.rt and its .ph, which are the same box now that the Normal / Longer / Quicker bar lies on the
photo), the panel, the photos below (#poolsec), and the bar of buttons (#dock, where a drop does nothing).
One whole line of the row always fits the row's box: a row photo fills its column but is never taller
than --rh, and the box is never shorter than that plus its padding. The panel itself never scrolls; the
row's box is the only scroller in it. The X and (on a narrow or touch screen) the Normal / Longer / Quicker
bar take a press a few pixels outside what is drawn, so a near miss does not open the big view instead.

A Mac and a PC (read through for the PC pass, Nov 6): nothing in the page is Mac-only. No Finder, Dock or
Option words and no key names on the page (Tab, Enter, space, Escape and the arrows, which it answers to, are on
both); every address
is the page server's own, with forward slashes, never a file:// path; the font list names Windows' own (Segoe UI)
beside the Mac's. Not yet seen on a PC: how the Claude app's pane there draws it and passes on the pointer.

Three scripts, in this order on the page:
  MODEL_JS    the row as a list, and where a drop lands. No page in it, so it can be tested by itself.
  DRAG_JS     dragging drawn by the page itself with pointer events and a lifted copy (the browser's own
              drag-and-drop does not work in the Claude app's pane). Modelled on first_look.py's picker.
  PICKER_JS   the page: the row, the photos below, the big view, saving.
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402

CSS = """
:root{--bg:#f6f3ee;--panel:#fffdf9;--ink:#2a2622;--soft:#7a7067;--soft-s:#746a61;--line:#e4ddd3;--chip:#efe9e0;--accent:#c4683f;--accent-d:#a4532f;--accent-l:#f7e8de;--long:#3d7a5a;--quick:#8a6bb0;--shadow:0 1px 3px rgba(0,0,0,.08);
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
--rw:96px;--rh:156px;--pw:110px;--gap:10px;--gut:10px}
@media(max-width:520px){:root{--pw:84px;--gap:8px;--gut:8px}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-padding-bottom:120px}
body{margin:0;background:var(--bg);color:var(--ink);font:400 15px/1.45 var(--sans)}
button{font-family:inherit}
[hidden]{display:none!important}
.wrap{display:flex;flex-direction:column;min-height:100vh;padding:0 16px}
.bar,.head,.panel,.poolsec,.plain{flex:none;width:100%;max-width:1068px;margin-left:auto;margin-right:auto}
.bar{display:flex;align-items:center;flex-wrap:wrap;gap:8px 14px;min-height:52px;padding:8px 0;border-bottom:1px solid var(--line)}
.brand b{font:650 14px/1.1 var(--sans)}.brand small{display:block;margin-top:2px;font:400 11.5px/1.1 var(--sans);color:var(--soft-s)}
.bar .homelink{display:inline-flex;align-items:center;gap:.45em;font:600 13.5px/1.2 var(--sans);color:var(--panel);background:var(--ink);text-decoration:none;padding:8px 14px 8px 11px;border-radius:10px;white-space:nowrap;transition:background .15s}
.bar .homelink:hover{background:#4a433c}.bar .homelink .short{display:none}
@media(max-width:560px){.bar .homelink .long{display:none}.bar .homelink .short{display:inline}}
.bar .kitlink{margin-left:auto;font:600 13.5px/1.2 var(--sans);color:var(--ink);text-decoration:none;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:7px 12px;transition:background .15s}
.bar .kitlink:hover{background:var(--chip)}
.head{padding:18px 0;display:grid;gap:2px}
.eyebrow{font:600 11.5px/1.3 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--soft-s)}
h1{margin:0;font:650 22px/1.25 var(--sans);overflow-wrap:anywhere}
.lede{margin:0;color:var(--soft)}
.topline{justify-self:start;margin:8px 0 0;font-size:14px;color:var(--accent-d);background:var(--accent-l);border-radius:10px;padding:7px 12px}
.plain{margin-top:22px;padding:16px 18px;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
.plain p{margin:0;font-size:16px;max-width:36em}

.panel{position:sticky;top:0;z-index:20;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:0 -14px 0 0 var(--bg),var(--shadow),0 12px 20px -16px rgba(42,38,34,.45);padding:14px}
@media(max-width:520px){.panel{padding:10px;border-radius:12px}}
.phead{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;margin:0 0 10px}
.phead h2,.poolhead h2{margin:0;font:650 16px/1.3 var(--sans)}
.phead .prep{order:1;font-size:13.5px;color:var(--soft)}
.phead .count{order:2;margin-left:auto;font-size:14px;color:var(--soft)}
.phead .advice{order:3;font-size:14px;color:var(--accent-d)}
.phead .advice:empty{display:none}
.rowwrap{min-height:calc(var(--rh) + 12px);max-height:max(calc(var(--rh) + 12px),calc(40vh - 104px));margin:0 calc(0px - var(--gut));overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain}
.row{position:relative;display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--rw),1fr));align-content:start;gap:var(--gap);padding:4px var(--gut) 8px;min-height:calc(var(--rh) + 12px)}
.rowempty{grid-column:1/-1;display:grid;place-items:center;min-height:136px;margin:0;padding:12px;color:var(--soft);text-align:center}
.ins{position:absolute;width:3px;border-radius:3px;background:var(--accent);pointer-events:none;display:none;box-shadow:0 0 0 2px rgba(196,104,63,.22)}
.ins.on{display:block}
.rowline{margin:8px 0 0;font-size:13.5px;color:var(--accent-d)}
.rowline:empty{display:none}
.legend{margin:10px 0 0;font-size:13px;line-height:1.4;color:var(--soft)}

.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:10px;padding:10px 16px;font:600 15px/1.2 var(--sans);cursor:pointer;transition:background .15s,border-color .15s}
.btn:hover{background:var(--chip)}
a.btn{text-decoration:none}
.btn.main{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.main:hover{background:#b35c36;border-color:#b35c36}
.btn:disabled{opacity:.45;cursor:default}
.btn:disabled:hover{background:var(--panel)}
.btn.main:disabled:hover{background:var(--accent);border-color:var(--accent)}
@media(max-width:520px){.dock .acts .btn{padding:9px 12px;font-size:14px}}

.dock{order:2;flex:none;position:sticky;bottom:0;z-index:30;margin:22px -16px 0;padding:12px 16px;background:var(--panel);border-top:1px solid var(--line)}
.dockin{max-width:1068px;margin:0 auto;text-align:center}
.acts{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:8px 10px}
.side{flex:1 0 100%;display:flex;flex-wrap:wrap;justify-content:center;align-items:baseline;gap:2px 10px;font-size:13px;line-height:1.35}
.why{color:var(--accent-d)}
.why:empty{display:none}
.status{color:var(--soft)}
.status.bad{color:var(--accent-d)}
@media(min-width:640px){
.acts{display:grid;grid-template-columns:1fr auto 1fr}
#back{grid-column:1;grid-row:1;justify-self:end}
#happy{grid-column:2;grid-row:1}
.side{grid-column:3;grid-row:1;justify-self:start;justify-content:flex-start;text-align:left}
}
.donerow{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:0 10px}
.donerow .btn,.note .btn{padding:7px 12px;font-size:13.5px;border-radius:8px}
.donerow .btn{margin-top:8px}
.doneline{margin:8px 0 0;font-size:14px;font-weight:600;color:var(--ink)}
.doneline:empty{display:none}
.doneline.since{font-weight:400;color:var(--accent-d)}
.openline{margin:4px 0 0;font-size:13px;color:var(--soft)}
.openline:empty{display:none}
.canvaline{margin:6px 0 0;font-size:13.5px;color:var(--accent-d)}
.note{margin:8px 0 0;font-size:13.5px;color:var(--accent-d);display:flex;flex-wrap:wrap;gap:8px;justify-content:center;align-items:center}
@media(max-width:520px){.dock{padding-top:10px;padding-bottom:10px}.donerow .btn{margin-top:6px}}

.tile{position:relative;user-select:none;-webkit-user-select:none;cursor:grab;outline:0}
.tile img{position:absolute;top:0;left:0;display:block;width:100%;height:100%;object-fit:cover;pointer-events:none;-webkit-user-drag:none;user-select:none}
.tile.dragging{opacity:.35}
.tile:focus-visible .ph,.pt:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}
.rt{touch-action:none}
.rt .ph{position:relative;width:100%;aspect-ratio:2/3;max-height:var(--rh);border-radius:10px;overflow:hidden;background:var(--line)}
.rt .pos{position:absolute;top:5px;left:5px;padding:1px 6px;border-radius:6px;background:rgba(0,0,0,.65);color:#fff;font:650 11.5px/1.45 var(--sans);white-space:nowrap;pointer-events:none}
.rt .x{position:absolute;top:4px;right:4px;width:22px;height:22px;border:0;border-radius:50%;background:rgba(0,0,0,.6);color:#fff;font:400 15px/22px var(--sans);text-align:center;cursor:pointer;padding:0}
.rt .x:hover{background:var(--accent)}
.rt .x::after{content:'';position:absolute;top:-6px;right:-6px;bottom:-6px;left:-6px}
.rt .mk{position:absolute;left:5px;right:5px;bottom:5px;border:0;border-radius:6px;padding:4px 0;background:rgba(255,255,255,.88);color:#2a2622;font:600 11.5px/1.2 var(--sans);white-space:nowrap;cursor:pointer}
.rt .mk:hover{background:#fff}
.rt .mk.long{background:var(--long);color:#fff}
.rt .mk.quick{background:var(--quick);color:#fff}
@media(max-width:520px),(pointer:coarse){.rt .mk::after{content:'';position:absolute;left:0;right:0;top:-8px;bottom:-5px}}

.poolsec{order:1;flex:1 0 auto;margin-top:22px;border-radius:10px;outline:2px dashed transparent;outline-offset:5px;transition:outline-color .15s,background .15s,box-shadow .15s}
.poolsec.out{outline-color:var(--accent);background:var(--accent-l);box-shadow:0 0 0 5px var(--accent-l)}
.poolhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;margin:0 0 10px}
.pool{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--pw),1fr));gap:var(--gap)}
.pt{aspect-ratio:2/3;border-radius:10px;overflow:hidden;background:var(--line);touch-action:pan-y}
.pt img{transition:opacity .15s}
.pt .num{position:absolute;top:5px;left:5px;padding:1px 6px;border-radius:6px;background:rgba(0,0,0,.6);color:#fff;font:400 12px/1.45 var(--sans);pointer-events:none}
.pt .pos{position:absolute;right:6px;bottom:6px;min-width:24px;height:24px;padding:0 6px;border-radius:999px;background:var(--accent);color:#fff;font:700 12px/24px var(--sans);text-align:center;pointer-events:none;display:none}
.pt.in img{opacity:.45}
.pt.in .pos{display:block}
.pt .cant,.rt .cant{position:absolute;top:0;right:0;bottom:0;left:0;display:none;place-items:center;padding:26px 6px 6px;text-align:center;font-size:11.5px;line-height:1.3;color:var(--ink);pointer-events:none}
.pt.cantread .cant,.rt.cantread .cant{display:grid}

body.arr-dragging,body.arr-dragging *{cursor:grabbing!important;user-select:none!important;-webkit-user-select:none!important}
.arr-lift{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;will-change:transform;transform-origin:0 0}
.arr-lift .pic{width:100%;height:100%;border-radius:10px;overflow:hidden;background:var(--line);box-shadow:0 0 0 3px #fff,0 18px 36px -12px rgba(0,0,0,.5)}
.arr-lift .pic img{display:block;width:100%;height:100%;object-fit:cover}
.arr-lift .say{position:absolute;left:50%;top:100%;transform:translateX(-50%);margin-top:8px;white-space:nowrap;background:var(--ink);color:#fff;font:600 12.5px/1 var(--sans);padding:6px 10px;border-radius:8px;display:none}
.arr-lift .say.on{display:block}

.big{position:fixed;top:0;right:0;bottom:0;left:0;z-index:9000;background:rgba(0,0,0,.85);display:none;place-items:center;padding:16px;overflow:auto}
.big.on{display:grid}
.big .box{position:relative;display:grid;gap:10px;justify-items:center;max-width:100%}
.big .pic{position:relative;display:grid;place-items:center;min-width:120px;min-height:120px}
.big .pic img{display:block;max-width:min(88vw,1000px);max-height:62vh;border-radius:8px;background:#2a2622}
.big .pic .cant,.big .pic .wait{color:#fff;font-size:15px;padding:2rem;display:none}
.big .pic.cantread img,.big .pic.notyet img{display:none}.big .pic.cantread .cant,.big .pic.notyet .wait{display:block}
.big .where{margin:0;color:#fff;font:500 14px/1.3 var(--sans);text-align:center}
.big .bacts{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;align-items:center}
.big .btn{background:#fffdf9;border-color:#fffdf9;color:#2a2622;padding:8px 14px;font-size:14px}
.big .btn:hover{background:#efe9e0;border-color:#efe9e0}
.big .btn.cur{background:var(--accent);border-color:var(--accent);color:#fff}
.big .btn.cur[data-act='mark+']{background:var(--long);border-color:var(--long)}
.big .btn.cur[data-act='mark-']{background:var(--quick);border-color:var(--quick)}
.big .btn.ghost{background:transparent;border-color:rgba(255,255,255,.55);color:#fff}
.big .btn.ghost:hover{background:rgba(255,255,255,.14)}
.big .btn:disabled{opacity:.4}
.big .btn:disabled:hover{background:#fffdf9;border-color:#fffdf9}
.big .gap{width:8px}
.big .bx,.big .nav{position:absolute;border:0;background:rgba(255,253,249,.94);color:#2a2622;width:36px;height:36px;border-radius:50%;font-size:22px;line-height:1;cursor:pointer;z-index:2}
.big .bx{top:-6px;right:-6px}
.big .nav{top:calc(31vh - 18px)}.big .prev{left:-8px}.big .next{right:-8px}
@media(min-width:900px){.big .prev{left:-48px}.big .next{right:-48px}.big .bx{top:-12px;right:-48px}}
"""

MODEL_JS = r"""
// The row is a list of {n: photo number, mark: '' | '+' | '-'} in play order. A photo is in it once; there
// are never holes. Every function here returns a new list (or the same one when nothing changes) and touches
// no page, so the rules can be checked on their own.
(function(root){
  'use strict';
  function indexOf(row, n){ for (var i = 0; i < row.length; i++) { if (row[i].n === n) return i; } return -1; }
  function clampPos(pos, len){ pos = Math.floor(Number(pos)); if (!(pos >= 0)) pos = 0; return pos > len ? len : pos; }
  // Move photo n so it sits in the gap before the photo now at `pos` (pos = length means the end).
  function moveTo(row, n, pos){
    var from = indexOf(row, n);
    if (from < 0) return row;
    pos = clampPos(pos, row.length);
    if (pos === from || pos === from + 1) return row;      // dropped where it already is
    var out = row.slice(), it = out.splice(from, 1)[0];
    if (pos > from) pos -= 1;
    out.splice(pos, 0, it);
    return out;
  }
  // Put photo n into the gap at `pos`. Already in the row: it moves there and keeps its mark. A full row: null.
  function insertAt(row, n, pos, max){
    if (indexOf(row, n) >= 0) return moveTo(row, n, pos);
    if (row.length >= max) return null;
    var out = row.slice();
    out.splice(clampPos(pos, row.length), 0, {n: n, mark: ''});
    return out;
  }
  function takeOut(row, n){
    var i = indexOf(row, n);
    if (i < 0) return row;
    var out = row.slice();
    out.splice(i, 1);
    return out;
  }
  function setMark(row, n, mark){
    var i = indexOf(row, n);
    if (i < 0 || row[i].mark === mark || (mark !== '' && mark !== '+' && mark !== '-')) return row;
    var out = row.slice();
    out[i] = {n: n, mark: mark};
    return out;
  }
  // One press of the bar under a photo: Normal, then Longer, then Quicker, then Normal again.
  function stepMark(row, n){
    var i = indexOf(row, n);
    if (i < 0) return row;
    return setMark(row, n, row[i].mark === '' ? '+' : row[i].mark === '+' ? '-' : '');
  }
  function same(a, b){
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) { if (a[i].n !== b[i].n || a[i].mark !== b[i].mark) return false; }
    return true;
  }
  // Where a drop lands: the first tile for which the pointer is above its bottom edge and left of its
  // middle, or above its top edge altogether. None: the end. rects are the row's tiles in order.
  function landing(rects, x, y){
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if ((y < r.bottom && x < (r.left + r.right) / 2) || y < r.top) return i;
    }
    return rects.length;
  }
  function fromLists(nums, marks){
    var out = [], seen = {};
    for (var i = 0; i < nums.length; i++) {
      if (seen[nums[i]]) continue;
      seen[nums[i]] = true;
      var m = marks && marks[i];
      out.push({n: nums[i], mark: (m === '+' || m === '-') ? m : ''});
    }
    return out;
  }
  root.ArrangeModel = {indexOf: indexOf, moveTo: moveTo, insertAt: insertAt, takeOut: takeOut, setMark: setMark,
                       stepMark: stepMark, same: same, landing: landing, fromLists: fromLists};
})(typeof window !== 'undefined' ? window : this);
"""

DRAG_JS = r"""
// Dragging, drawn by the page itself. The browser's own drag-and-drop does not work in the Claude app's
// pane, so: a press on a tile, 7 px of travel, then a copy of the photo is lifted and follows the pointer.
// The page says what a drop would do (over) and does it (drop). Every way out puts things back: Escape,
// the pointer being cancelled, the window losing focus, a mouse move with no button held.
//
//   var d = arrangeDrag({
//     tileOf(target)   -> the tile under a press, or null
//     canDrag(tile, e) -> false: this press can only ever be a click (a finger on the photos below)
//     picture(tile)    -> the element whose box and image the lifted copy takes
//     over(x, y, tile) -> called as the pointer moves, and again after the row scrolls under it
//     drop(tile), cancel(tile), click(tile)
//     scrollBox        -> an element that scrolls while the pointer rests inside it, near its top or bottom edge
//   });
//   d.say(text)        a short line under the lifted copy ('' hides it)
//   d.active()         true while a photo is lifted
//   d.busy()           true from the press on a tile until it ends (lifted or not)
//   d.justDragged      true for a moment after a drag ends, so a click that follows it can be ignored
window.arrangeDrag = function(o){
  'use strict';
  var START = 7, EDGE = 36, STEP = 12, DWELL = 250;
  var d = null, raf = null, api = {justDragged: false};

  function lift(e){
    var pic = o.picture ? o.picture(d.t) : d.t;
    var r = pic.getBoundingClientRect();
    d.ox = d.x - r.left; d.oy = d.y - r.top;
    var el = document.createElement('div');
    el.className = 'arr-lift';
    el.style.width = r.width + 'px'; el.style.height = r.height + 'px';
    var box = document.createElement('div'); box.className = 'pic';
    var img = pic.querySelector('img');
    if (img && img.getAttribute('src')) { var c = document.createElement('img'); c.alt = ''; c.src = img.getAttribute('src'); box.appendChild(c); }
    var note = document.createElement('span'); note.className = 'say';
    el.appendChild(box); el.appendChild(note);
    document.body.appendChild(el);
    d.lift = el; d.note = note; d.on = true;
    d.t.classList.add('dragging');
    document.body.classList.add('arr-dragging');
    if (!raf) raf = requestAnimationFrame(tick);
  }
  function place(){
    d.lift.style.transform = 'translate(' + (d.lx - d.ox * 1.06) + 'px,' + (d.ly - d.oy * 1.06) + 'px) scale(1.06)';
  }
  // While the pointer RESTS inside the row's box, within 36 px of its top or bottom edge, the row scrolls,
  // and the landing place is worked out again each step. Only inside the box (never from the heading above
  // it or the buttons below it), and only after a quarter of a second there, so a photo carried up through
  // the edge on its way into the row does not move the row out from under it.
  function tick(){
    raf = null;
    if (!d || !d.on) return;
    var box = o.scrollBox;
    if (box && box.scrollHeight > box.clientHeight + 1) {
      var r = box.getBoundingClientRect(), was = box.scrollTop, band = 0;
      if (d.lx >= r.left && d.lx <= r.right && d.ly >= r.top && d.ly <= r.bottom) {
        if (d.ly < r.top + EDGE) band = -1;
        else if (d.ly > r.bottom - EDGE) band = 1;
      }
      if (band !== d.band) { d.band = band; d.bandAt = Date.now(); }
      if (band && Date.now() - d.bandAt >= DWELL) {
        box.scrollTop = band < 0 ? Math.max(0, was - STEP) : Math.min(box.scrollHeight - box.clientHeight, was + STEP);
        if (box.scrollTop !== was) o.over(d.lx, d.ly, d.t);
      }
    }
    raf = requestAnimationFrame(tick);
  }
  function finish(cancel){
    if (!d) return;
    var x = d; d = null;
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    document.body.classList.remove('arr-dragging');
    if (!x.on) { if (!cancel && o.click) o.click(x.t); return; }
    x.lift.remove();
    x.t.classList.remove('dragging');
    api.justDragged = true;
    setTimeout(function(){ api.justDragged = false; }, 0);
    if (cancel) { if (o.cancel) o.cancel(x.t); } else { o.drop(x.t); }
  }

  document.addEventListener('pointerdown', function(e){
    // A new press ends the "just dragged" moment for certain. The timer in finish() can run late (a page
    // that is not in front has its timers slowed to a second or more), and a click on the X must never be lost.
    api.justDragged = false;
    if (d) return;                                         // one pointer at a time; a second finger is ignored
    if (e.isPrimary === false || e.button !== 0) return;   // the main button of the main pointer only
    var t = o.tileOf(e.target);
    if (!t) return;
    // a press on a button inside a tile (the X, the bar under a photo) is that button's, never a drag
    if (e.target.closest && e.target.closest('button,a,input,select,textarea,label')) return;
    var only = o.canDrag ? !o.canDrag(t, e) : false;
    d = {t: t, id: e.pointerId, x: e.clientX, y: e.clientY, lx: e.clientX, ly: e.clientY, on: false, clickOnly: only};
    if (!only) e.preventDefault();                         // no text selection, no browser drag of the picture
  });
  document.addEventListener('pointermove', function(e){
    if (!d || e.pointerId !== d.id) return;
    if (e.pointerType === 'mouse' && e.buttons === 0) { finish(true); return; }   // the button was let go somewhere we never heard about
    d.lx = e.clientX; d.ly = e.clientY;
    if (!d.on) {
      if (Math.sqrt((d.lx - d.x) * (d.lx - d.x) + (d.ly - d.y) * (d.ly - d.y)) < START) return;   // not a drag yet
      if (d.clickOnly) { d = null; return; }               // a finger scrolling the photos below: not a click, not a drag
      lift(e);
    }
    place();
    o.over(d.lx, d.ly, d.t);
  });
  document.addEventListener('pointerup', function(e){ if (d && e.pointerId === d.id) finish(false); });
  document.addEventListener('pointercancel', function(e){ if (d && e.pointerId === d.id) finish(true); });
  window.addEventListener('blur', function(){ finish(true); });
  document.addEventListener('visibilitychange', function(){ if (document.hidden) finish(true); });
  document.addEventListener('keydown', function(e){
    if (d && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finish(true); }
  }, true);

  api.say = function(text){ if (d && d.note) { d.note.textContent = text || ''; d.note.classList.toggle('on', !!text); } };
  api.active = function(){ return !!(d && d.on); };
  api.busy = function(){ return !!d; };
  return api;
};
"""

PICKER_JS = r"""
(function(){
  'use strict';
  var M = window.ArrangeModel;
  var KIT = document.body.dataset.kit, PIECE = document.body.dataset.piece;
  var Q = 'kit=' + encodeURIComponent(KIT);
  var $ = function(id){ return document.getElementById(id); };
  var el = function(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  var WORDS = {
    reel: {
      label: 'Reel', thing: 'reel', rowname: 'Your reel',
      help: 'Your reel, in the order it plays. Drag a photo to move it. Drag one up from below to add it. Click any photo to see it big.',
      legend: 'Under each photo: how long it stays on screen. Normal, Longer or Quicker. Longer stays on screen about twice as long. Quicker gets the shortest time, one beat.',
      few: 'A reel needs at least 2 photos.', full: 'A reel holds up to 60 photos. Take one out first.',
      // v19: the reel page took this picker's place (decision 3); after "done" the order goes onto the reel page,
      // where the song and the vibe are picked (parts/arrange.md). Until v19: "I’ll ask which song to cut it to."
      done: 'Saved. Go back to the chat and say “done”, and I’ll put this order on the reel page, where you add your song and make the reel.',
      doneAgain: 'Saved. Go back to the chat and say “done”, and I’ll put this order on the reel page, where you can make a new reel. The one already in CapCut stays as it is.'
    },
    carousel: {
      label: 'Carousel', thing: 'carousel', rowname: 'Your carousel',
      help: 'Your carousel, in the order people swipe. Drag a photo to move it. Drag one up from below to add it. Click any photo to see it big.',
      legend: 'The first photo is the one people see in their feed, so lead with your strongest.',
      few: 'A carousel needs at least 2', full: 'Instagram allows up to 20. Take one out first.',
      done: 'Saved.', doneAgain: 'Saved.',
      making: 'Making your slides...', same: 'Your slides are already in this order.',
      slow: 'This is taking longer than it should. Tell Claude.',
      canva: 'Your Canva slides still show the old photos. Say “redo the Canva carousel” to Claude.'
    }
  };
  var T = WORDS[PIECE] || WORDS.reel;
  var MARK = {'': 'Normal', '+': 'Longer', '-': 'Quicker'};
  var SAVED = 'Saved', SAVING = 'Saving...', RETRY = 'Not saved yet. Trying again...';
  var CANT_REACH = 'Could not reach the Assistant. Tell Claude instead.';
  var CANT_READ = 'Can’t read this photo right now';
  var SINCE = 'You’ve changed it since. Press the button again when it’s right.';
  var NEWER = 'This order was changed somewhere else. Here’s the newest.';
  // a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this
  // page's own save (whose answer never arrived) from a change made in another window
  var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');
  var TAKE_OUT = 'Drop here to take it out';

  var rowEl = $('row'), wrapEl = $('rowwrap'), panelEl = $('panel'), poolEl = $('pool'), poolSec = $('poolsec'), dockEl = $('dock');
  var insEl = el('div', 'ins'), emptyEl = el('p', 'rowempty', 'Nothing picked yet. Drag photos up from below.');
  var happyBtn = $('happy'), backBtn = $('back');

  var S = null;                 // the last answer from /arrange-state
  var by = {};                  // photo number -> its record
  var row = [], first = [];     // the row now, and the Assistant's first pick
  var rev = 0;                  // the counter of the newest order the Assistant has told this page about
  var happyRev = null;          // the counter of the order they last pressed the final button on
  var blocked = false;          // the photos changed under the page: nothing more is saved until a reload
  var rowNodes = {}, poolNodes = {};
  var saving = false, dirty = false, wantDone = false, timer = null, retryT = null, pollT = null, watchT = null;
  var target = null;            // what a drop would do right now
  // The carousel only: its final button has the slides made, by a job of the Assistant's own.
  var jobWait = null;           // the counter of the order whose slides this page is waiting for
  var jobSince = 0;             // when the waiting began, by the clock (never by counting timer turns)
  var jobWords = '';            // what to show while waiting, when the Assistant gave words for it
  var jobT = null;
  var shown = null;             // the last result: {rev: the order it is about, kind: done | same | problem, line}
  var JOB_LIMIT = 180000;       // three minutes

  $('eyebrow').textContent = T.label;
  $('help').textContent = T.help;
  $('rowname').textContent = T.rowname;
  $('legend').textContent = T.legend;

  function url(p, size){ return '/kit-photo?' + Q + '&n=' + p.n + '&size=' + size + '&v=' + encodeURIComponent(p.v || ''); }
  function ratio(p){ var w = p.w, h = p.h; if (!(w > 0 && h > 0)) return 1; return Math.max(0.5, Math.min(2.2, w / h)); }
  function inRow(n){ return M.indexOf(row, n); }
  function max(){ return (S && S.limits && S.limits.max) || 60; }
  function min(){ return (S && S.limits && S.limits.min) || 2; }

  // ---- drawing ----
  function setPicture(holder, p){
    var img = holder.querySelector('img');
    var tile = holder.closest('.tile');
    if (p.have) {
      if (!img) { img = document.createElement('img'); img.alt = ''; img.decoding = 'async'; if (tile.classList.contains('pt')) img.loading = 'lazy'; holder.insertBefore(img, holder.firstChild); }
      var u = url(p, 's');
      if (img.getAttribute('src') !== u) img.setAttribute('src', u);
    }
    tile.classList.toggle('cantread', !p.have && !!p.missing);
  }
  function poolTile(p){
    var t = el('div', 'tile pt');
    t.dataset.n = p.n; t.tabIndex = 0; t.style.setProperty('--r', ratio(p));
    t.appendChild(el('span', 'num', '#' + p.n));          // the photo's own number, as "#12"
    t.appendChild(el('span', 'pos'));
    t.appendChild(el('span', 'cant', CANT_READ));
    setPicture(t, p);
    return t;
  }
  function rowTile(p){
    var t = el('div', 'tile rt');
    t.dataset.n = p.n; t.tabIndex = 0; t.style.setProperty('--r', ratio(p));
    var ph = el('div', 'ph');
    ph.appendChild(el('span', 'pos'));
    ph.appendChild(el('span', 'cant', CANT_READ));
    var x = el('button', 'x', '×'); x.type = 'button'; x.title = 'Take it out'; x.setAttribute('aria-label', 'Take it out');
    ph.appendChild(x);
    t.appendChild(ph);
    if (PIECE === 'reel') { var mk = el('button', 'mk', MARK['']); mk.type = 'button'; t.appendChild(mk); }
    setPicture(ph, p);
    return t;
  }
  function buildPool(){
    poolEl.textContent = ''; poolNodes = {};
    var frag = document.createDocumentFragment();
    S.photos.forEach(function(p){ var t = poolTile(p); poolNodes[p.n] = t; frag.appendChild(t); });
    poolEl.appendChild(frag);
    $('poolname').textContent = 'All ' + S.total + (S.total === 1 ? ' photo' : ' photos');
  }
  // the row: nodes are moved into order, never rebuilt, so no picture is fetched twice
  function draw(){
    var seen = {};
    row.forEach(function(it, i){
      var t = rowNodes[it.n];
      if (!t) { t = rowTile(by[it.n]); rowNodes[it.n] = t; }
      rowEl.appendChild(t);
      t.querySelector('.pos').textContent = (i + 1) + ' · #' + it.n;      // its place, then its own number
      var mk = t.querySelector('.mk');
      if (mk) { mk.textContent = MARK[it.mark]; mk.className = 'mk' + (it.mark === '+' ? ' long' : it.mark === '-' ? ' quick' : ''); }
      seen[it.n] = true;
    });
    Object.keys(rowNodes).forEach(function(n){ if (!seen[n]) { rowNodes[n].remove(); delete rowNodes[n]; } });
    if (row.length) { if (emptyEl.parentNode) emptyEl.remove(); } else rowEl.appendChild(emptyEl);
    rowEl.appendChild(insEl);
    Object.keys(poolNodes).forEach(function(n){
      var i = inRow(Number(n)), t = poolNodes[n];
      t.classList.toggle('in', i >= 0);
      t.querySelector('.pos').textContent = i >= 0 ? String(i + 1) : '';
    });
    lines();
  }
  function lines(){
    var n = row.length, lim = (S && S.limits) || {best: [8, 14]};
    $('count').textContent = n + (n === 1 ? ' photo' : ' photos');
    var adv = '';
    if (PIECE === 'reel') { if (n < lim.best[0] || n > lim.best[1]) adv = lim.best[0] + ' to ' + lim.best[1] + ' works best'; }
    else if (n < 2) adv = 'A carousel needs at least 2';
    else if (n > lim.best[1]) adv = lim.best[0] + ' to ' + lim.best[1] + ' usually works best';
    $('advice').textContent = adv;
    backBtn.hidden = M.same(row, first);
    // too few, or more than this piece holds (an older pick can be over-long): the button is off, and the
    // line beside it says why and what to do
    happyBtn.disabled = blocked || n < min() || n > max();
    $('why').textContent = n < min() ? T.few : n > max() ? T.full : '';
    var d = $('doneline'), text = '', since = false, folder = false, canva = false;
    if (PIECE === 'carousel') {
      // the line is about the slides: being made, made (with the folder's button beside it), or why not
      if (wantDone) text = '';
      else if (jobWait != null) text = jobWords || T.making;
      else if (shown && shown.rev === rev && !dirty && !saving) {
        text = shown.line;
        folder = shown.kind === 'done' || shown.kind === 'same';
        // S.canva is true only while the Canva slides were made from another order than this one
        canva = folder && !!(S && S.canva);
      }
      else if (shown || (happyRev != null && happyRev !== rev)) { text = SINCE; since = true; }
    } else if (happyRev != null) {
      if (happyRev === rev && !dirty && !saving) text = S && S.reel_made && PIECE === 'reel' ? T.doneAgain : T.done;
      else if (!wantDone) { text = SINCE; since = true; }
    }
    d.textContent = text; d.classList.toggle('since', since);
    var ob = $('openfolder'), ol = $('openline'), cl = $('canvaline'), lo = $('layout');
    if (ob) { ob.hidden = !folder; if (!folder && ol) ol.textContent = ''; }
    // "Lay out the slides": a plain link to this shoot's designer, there whenever the folder's button is
    if (lo) { lo.hidden = !folder; if (folder) lo.href = '/design.html?' + Q; }
    if (cl) { cl.hidden = !canva; cl.textContent = canva ? T.canva : ''; }
  }
  // ---- the carousel's slides being made ----
  function ended(J){ return J.state === 'done' || J.state === 'same' || J.state === 'problem'; }
  // What the Assistant says about its slide-making job, taken in. While this page waits for an order's
  // slides, only that order's result ends the wait (or three minutes by the clock). Not waiting: a result
  // for the order now on the page is shown (the slides may have been made from the chat, or before a
  // reload), and a job at work on it is waited for.
  function takeJob(J){
    if (PIECE !== 'carousel') return;
    if (jobWait != null) {
      if (J && ended(J) && J.rev === jobWait) { shown = {rev: J.rev, kind: J.state, line: J.line}; jobWait = null; stopJobPoll(); return; }
      // The Assistant has moved on to a NEWER order (the button was pressed in another window, or Claude
      // made the slides): no result for the order this page pressed on will ever come, so the wait is over.
      // What is said next is worked out below, and the page takes the newer order as soon as it is idle.
      if (J && typeof J.rev === 'number' && J.rev > jobWait) { jobWait = null; jobWords = ''; stopJobPoll(); }
      else {
        if (Date.now() - jobSince > JOB_LIMIT) { shown = {rev: jobWait, kind: 'slow', line: T.slow}; jobWait = null; stopJobPoll(); }
        return;
      }
    }
    if (!J || J.rev !== rev) return;
    if (ended(J)) shown = {rev: J.rev, kind: J.state, line: J.line};
    // a job still at work on this order is waited for, unless this page has already said it is taking too
    // long (it then stays said, and the result is shown whenever it does arrive)
    else if (!(shown && shown.kind === 'slow' && shown.rev === J.rev)) { jobWait = J.rev; jobSince = Date.now(); jobWords = ''; shown = null; jobPoll(); }
  }
  function jobPoll(){
    if (jobT) return;
    jobT = setInterval(function(){
      if (jobWait == null) { stopJobPoll(); return; }
      getState().then(function(j){
        if (jobWait == null) return;
        if (j && j.ok && j.stamp !== S.stamp) { jobWait = null; stopJobPoll(); photosChanged(); return; }
        // a newer order than this page's (made in another window, or by Claude): taken at once when nothing
        // here is unsaved, exactly as the page's slower look does, so the wait never outlives its order
        if (j && j.ok && j.rev !== rev && idle()) { adopt(j); status(SAVED); return; }
        if (j && j.ok) { S.canva = j.canva; S.job = j.job; }
        takeJob(j && j.ok ? j.job : null);
        lines();
      }).catch(function(){
        // the Assistant is not answering (it may be starting over; the job is a process of its own and goes on)
        takeJob(null); lines();
      });
    }, 1200);
  }
  function stopJobPoll(){ if (jobT) { clearInterval(jobT); jobT = null; } }
  function status(text, bad){ var s = $('status'); s.textContent = text || ''; s.classList.toggle('bad', !!bad); }
  function rowLine(text){ $('rowline').textContent = text || ''; }
  function note(text, reload){
    var n = $('note'); n.textContent = '';
    if (!text) { n.hidden = true; return; }
    n.appendChild(el('span', '', text));
    if (reload) { var b = el('button', 'btn', 'Reload'); b.type = 'button'; b.addEventListener('click', function(){ location.reload(); }); n.appendChild(b); }
    n.hidden = false;
  }
  function topLines(){
    var a = $('l-missing'), b = $('l-dropped'), c = $('prep');
    var miss = S.photos.some(function(p){ return p.missing; });
    a.hidden = !miss; a.textContent = miss ? 'Some photos can’t be read right now. Is the drive plugged in?' : '';
    var k = (S.dropped || []).length;
    b.hidden = !k; b.textContent = k ? (k === 1 ? '1 photo is no longer in this shoot, so it was taken out.' : k + ' photos are no longer in this shoot, so they were taken out.') : '';
    var made = S.photos.filter(function(p){ return p.have; }).length;
    var waiting = S.photos.some(function(p){ return !p.have && !p.missing; });
    c.hidden = !waiting; c.textContent = waiting ? 'Getting your photos ready: ' + made + ' of ' + S.total : '';
    return waiting;
  }

  // ---- taking a state from the Assistant ----
  function adopt(j){
    var rebuild = !S || S.stamp !== j.stamp || S.total !== j.total;
    S = j; by = {};
    j.photos.forEach(function(p){ by[p.n] = p; });
    var known = function(it){ return !!by[it.n]; };
    row = M.fromLists(j.now.nums, j.now.marks).filter(known);
    first = M.fromLists(j.first.nums, j.first.marks).filter(known);
    rev = j.rev; happyRev = j.happy ? j.happy.rev : null;
    jobWait = null; shown = null; jobWords = ''; stopJobPoll();     // worked out again from what the Assistant says now
    takeJob(j.job);
    $('title').textContent = j.name + ' ' + T.thing;
    document.title = j.name + ' ' + T.thing;
    var kl = $('kitlink');
    if (j.kit_page) { kl.href = '/content/' + encodeURIComponent(KIT) + '/Post%20kit.html'; kl.hidden = false; } else kl.hidden = true;
    if (rebuild) { Object.keys(rowNodes).forEach(function(n){ rowNodes[n].remove(); }); rowNodes = {}; buildPool(); }
    else j.photos.forEach(refreshPhoto);
    draw();
    if (showing != null) { if (by[showing]) openBig(showing); else closeBig(); }
    if (topLines()) poll();
  }
  function refreshPhoto(p){
    var was = by[p.n];
    by[p.n] = p;
    if (poolNodes[p.n]) setPicture(poolNodes[p.n], p);
    if (rowNodes[p.n]) setPicture(rowNodes[p.n].querySelector('.ph'), p);
    // the photo open in the big view: when its copy arrives (or it can no longer be read), show that there too
    if (showing === p.n && (!was || was.have !== p.have || was.missing !== p.missing || was.v !== p.v)) openBig(p.n);
  }
  function getState(){
    return fetch('/arrange-state?' + Q + '&page=' + PIECE, {cache: 'no-store'}).then(function(r){ return r.json(); });
  }
  function start(){
    getState().then(function(j){
      $('l-reach').hidden = true;
      if (!j || !j.ok) { var a = $('l-reach'); a.textContent = (j && j.words) || CANT_REACH; a.hidden = false; return; }
      adopt(j);
      status(SAVED);
      watch();
    }).catch(function(){
      var a = $('l-reach'); a.textContent = CANT_REACH; a.hidden = false;
      setTimeout(start, 2000);
    });
  }
  // Nothing unsaved, nothing on its way, no photo pressed or lifted: the page can take a newer order.
  function idle(){ return !!S && !blocked && !saving && !dirty && !wantDone && !drag.busy(); }
  // A state that arrived while the page was idle. A newer order (a fresh pick made in the chat, or a change
  // in another window) is shown at once; nothing of theirs is lost by that, since nothing here was unsaved.
  function follow(j){
    if (j.stamp !== S.stamp) { stopPoll(); photosChanged(); return; }
    if (j.rev !== rev) { adopt(j); status(SAVED); return; }
    var h = j.happy ? j.happy.rev : null;
    if (h !== happyRev || j.reel_made !== S.reel_made) { happyRev = h; S.reel_made = j.reel_made; lines(); }
    if (PIECE === 'carousel') { S.canva = j.canva; S.job = j.job; takeJob(j.job); lines(); }
  }
  // while the page sits open, ask every few seconds, so it follows without a reload
  function watch(){
    if (watchT) return;
    watchT = setInterval(function(){
      if (pollT || jobT || document.hidden || !idle()) return;
      var asked = rev;
      getState().then(function(j){
        if (j && j.ok && idle() && rev === asked) follow(j);
      }).catch(function(){});
    }, 4000);
  }
  // while small copies are still being made, ask again every so often and fill the tiles in as they arrive
  function poll(){
    if (pollT) return;
    var tries = 0;
    pollT = setInterval(function(){
      tries += 1;
      getState().then(function(j){
        if (!j || !j.ok) return;
        if (j.stamp !== S.stamp) { photosChanged(); stopPoll(); return; }
        if (j.rev !== rev && idle()) { adopt(j); status(SAVED); }
        S.photos = j.photos; S.previews = j.previews;
        j.photos.forEach(refreshPhoto);
        if (!topLines() || tries > 500) stopPoll();
      }).catch(function(){});
    }, 1200);
  }
  function stopPoll(){ if (pollT) { clearInterval(pollT); pollT = null; } }
  function photosChanged(){
    blocked = true; dirty = false; wantDone = false;
    jobWait = null; shown = null; stopJobPoll();
    clearTimeout(timer); clearTimeout(retryT);
    status('');
    note('The photos in this shoot changed since this page opened.', true);
    lines();
  }

  // ---- saving: drawn first, then sent; one request at a time; the newest state wins; retried until it lands ----
  function changed(next){
    if (blocked || next === row || next == null) return false;
    row = next;
    rowLine('');
    note('');                   // a line about an earlier save has been read by now, and this change is a new try
    draw();
    dirty = true;
    status(SAVING);
    clearTimeout(timer);
    timer = setTimeout(send, 400);
    lines();
    return true;
  }
  function send(){
    clearTimeout(timer); clearTimeout(retryT);
    if (saving || blocked || !S) return;
    if (wantDone && (row.length < min() || row.length > max())) wantDone = false;
    if (!dirty && !wantDone) return;
    var done = wantDone;
    saving = true; dirty = false;
    // "base" is the counter this page was last told. The Assistant takes a change only from a page that has
    // seen the order it replaces, and answers with the new counter.
    var body = {kit: KIT, piece: PIECE, stamp: S.stamp, base: rev, page: PAGE, done: done,
                nums: row.map(function(it){ return it.n; }), marks: row.map(function(it){ return it.mark; })};
    status(SAVING);
    fetch('/arrange', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(function(r){
        if (r.status >= 500) throw new Error('no answer');      // treated like no answer at all: try again
        return r.json().then(function(j){ return {code: r.status, j: j}; });
      })
      .then(function(res){
        saving = false;
        var j = res.j || {};
        if (res.code === 200 && j.ok) {
          if (typeof j.rev === 'number') rev = j.rev;
          if (done) {
            wantDone = false; happyRev = rev;
            if (PIECE === 'carousel') {
              // the Assistant either set a job to making the slides, or says they are already in this order
              stopJobPoll();
              if (j.job) { jobWait = rev; jobSince = Date.now(); jobWords = j.line || ''; shown = null; jobPoll(); }
              else { jobWait = null; shown = {rev: rev, kind: j.same ? 'same' : 'problem', line: j.line || T.same}; }
            }
          }
          if (dirty || wantDone) { send(); return; }
          status(SAVED); lines();
          return;
        }
        if (res.code === 409 && j.why === 'photos') { photosChanged(); return; }
        if (res.code === 409 && j.why === 'newer' && j.state && j.state.ok) {
          dirty = false; wantDone = false;
          adopt(j.state);
          status(SAVED);
          note(NEWER, false);
          return;
        }
        if (res.code === 404) {
          // the shoot can't be found right now (its drive is unplugged): keep trying, with the question
          // showing, so the change lands by itself when the drive is back
          dirty = true;
          status(j.words || CANT_REACH, true); lines();
          retryT = setTimeout(send, 2000);
          return;
        }
        // refused in a way trying again will not fix: say so, with the Reload button beside the words
        wantDone = false;
        status('');
        note(j.words || CANT_REACH, true); lines();
      })
      .catch(function(){
        // the Assistant did not answer (it may be starting over after an update): keep trying
        saving = false; dirty = true;
        status(RETRY, true); lines();
        retryT = setTimeout(send, 2000);
      });
  }

  // ---- the buttons in the panel ----
  rowEl.addEventListener('click', function(e){
    if (drag.justDragged) return;
    var b = e.target.closest('button'); if (!b) return;
    var t = b.closest('.rt'); if (!t) return;
    var n = Number(t.dataset.n);
    if (b.classList.contains('x')) changed(M.takeOut(row, n));
    else if (b.classList.contains('mk')) changed(M.stepMark(row, n));
  });
  backBtn.addEventListener('click', function(){ changed(first.slice()); });
  happyBtn.addEventListener('click', function(){
    if (blocked || row.length < min() || row.length > max()) return;
    wantDone = true;
    status(SAVING); lines();
    send();
  });

  // "Open the Carousel folder", beside the line that says the slides are there; its answer shows right under it
  var openBtn = $('openfolder');
  if (openBtn) openBtn.addEventListener('click', function(){
    var line = $('openline');
    line.textContent = 'Opening...';
    fetch('/open?' + Q + '&sub=Carousel', {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){ line.textContent = (j && j.words) || CANT_REACH; })
      .catch(function(){ line.textContent = CANT_REACH; });
  });

  // ---- dragging ----
  function clearMarks(){ insEl.classList.remove('on'); poolSec.classList.remove('out'); drag.say(''); }
  function inside(r, x, y){ return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; }
  function showBar(pos, tiles, x, y){
    var rr = rowEl.getBoundingClientRect(), left, top, h;
    if (!tiles.length) { left = 8; top = 8; h = wrapEl.clientHeight > 60 ? Math.min(132, wrapEl.clientHeight - 20) : 96; }
    else {
      var at = pos < tiles.length ? tiles[pos] : null, before = pos > 0 ? tiles[pos - 1] : null, a, useBefore = false;
      if (!at) useBefore = true;
      else if (before) {
        // the gap sits at a line break: draw the bar on the line the pointer is on
        var ar = at.getBoundingClientRect(), br = before.getBoundingClientRect();
        if (ar.top > br.top + 4 && y < ar.top) useBefore = true;
      }
      if (useBefore) { a = before.querySelector('.ph').getBoundingClientRect(); left = a.right - rr.left + 4; }
      else { a = at.querySelector('.ph').getBoundingClientRect(); left = a.left - rr.left - 7; }
      top = a.top - rr.top; h = a.height;
    }
    insEl.style.left = left + 'px'; insEl.style.top = top + 'px'; insEl.style.height = h + 'px';
    insEl.classList.add('on');
  }
  function over(x, y, t){
    clearMarks();
    target = null;
    var n = Number(t.dataset.n), fromRow = t.classList.contains('rt'), at = inRow(n);
    // The bar of buttons at the bottom of the window floats over the photos below (and, in a very short
    // window, over the row): a drop on it does nothing.
    if (dockEl && inside(dockEl.getBoundingClientRect(), x, y)) return;
    // Only the row's own box takes a drop, so the bar is always in sight where the photo would land.
    if (inside(wrapEl.getBoundingClientRect(), x, y)) {
      var tiles = Array.prototype.slice.call(rowEl.querySelectorAll('.rt'));
      var pos = M.landing(tiles.map(function(k){ return k.getBoundingClientRect(); }), x, y);
      if (at >= 0 && (pos === at || pos === at + 1)) return;           // where it already is: nothing to do
      if (at < 0 && row.length >= max()) { target = {kind: 'full'}; drag.say('Take one out first'); return; }
      target = {kind: 'in', pos: pos};
      showBar(pos, tiles, x, y);
      return;
    }
    // The rest of the panel (its heading, the lines under the row) floats over the photos below: a drop there does nothing.
    if (inside(panelEl.getBoundingClientRect(), x, y)) return;
    if (fromRow && inside(poolSec.getBoundingClientRect(), x, y)) {
      target = {kind: 'out'};
      poolSec.classList.add('out');
      drag.say(TAKE_OUT);
    }
  }
  function drop(t){
    var n = Number(t.dataset.n), tg = target;
    target = null; clearMarks();
    if (!tg || blocked) return;
    if (tg.kind === 'full') { rowLine(T.full); return; }
    if (tg.kind === 'out') { changed(M.takeOut(row, n)); return; }
    var next = M.insertAt(row, n, tg.pos, max());
    if (next == null) { rowLine(T.full); return; }
    changed(next);
  }
  var drag = window.arrangeDrag({
    tileOf: function(target){ var t = target && target.closest ? target.closest('.tile') : null; return t && (rowEl.contains(t) || poolEl.contains(t)) ? t : null; },
    canDrag: function(t, e){ return !blocked && !!S && !(e.pointerType === 'touch' && t.classList.contains('pt')); },
    picture: function(t){ return t.classList.contains('rt') ? t.querySelector('.ph') : t; },
    over: over, drop: drop,
    cancel: function(){ target = null; clearMarks(); },
    click: function(t){ openBig(Number(t.dataset.n)); },
    scrollBox: wrapEl
  });

  // ---- one photo big, with everything a drag can do as a button ----
  var big = $('big'), bigPic = big.querySelector('.pic'), bigImg = big.querySelector('img');
  var showing = null;
  function order(){
    var out = row.map(function(it){ return it.n; });
    S.photos.forEach(function(p){ if (inRow(p.n) < 0) out.push(p.n); });
    return out;
  }
  function bbtn(text, act, opts){
    var b = el('button', 'btn' + (opts && opts.cls ? ' ' + opts.cls : ''), text);
    b.type = 'button'; b.dataset.act = act;
    if (opts && opts.off) b.disabled = true;
    return b;
  }
  function bigActs(){
    var n = showing, i = inRow(n), acts = big.querySelector('.bacts'), where = big.querySelector('.where');
    acts.textContent = '';
    if (i >= 0) {
      where.textContent = 'Number ' + (i + 1) + ' of ' + row.length + ' in your ' + T.thing + '.';
      acts.appendChild(bbtn('Move it earlier', 'earlier', {off: i === 0}));
      acts.appendChild(bbtn('Move it later', 'later', {off: i === row.length - 1}));
      acts.appendChild(bbtn('Take it out', 'out', {cls: 'ghost'}));
      if (PIECE === 'reel') {
        acts.appendChild(el('span', 'gap'));
        ['', '+', '-'].forEach(function(m){ acts.appendChild(bbtn(MARK[m], 'mark' + m, {cls: row[i].mark === m ? 'cur' : ''})); });
      }
    } else {
      var full = row.length >= max();
      where.textContent = 'Not in your ' + T.thing + '.' + (full ? ' ' + T.full : '');
      acts.appendChild(bbtn('Add it to the end', 'add', {off: full || blocked}));
    }
  }
  function openBig(n){
    var p = by[n]; if (!p) return;
    showing = n;
    bigPic.classList.toggle('cantread', !p.have && !!p.missing);     // it can't be reached or read
    bigPic.classList.toggle('notyet', !p.have && !p.missing);        // its copy is still being made
    if (p.have) {
      bigImg.setAttribute('src', url(p, 's'));               // the small copy first, at once
      var sharp = new Image();
      sharp.onload = function(){ if (showing === n) bigImg.setAttribute('src', sharp.src); };
      sharp.src = url(p, 'l');                              // then the sharp one when it has arrived
    } else bigImg.removeAttribute('src');
    bigActs();
    big.classList.add('on');
  }
  function closeBig(){ big.classList.remove('on'); showing = null; }
  function step(by1){ var o = order(), i = o.indexOf(showing); if (i < 0 || !o.length) return; openBig(o[(i + by1 + o.length) % o.length]); }
  big.addEventListener('click', function(e){
    var b = e.target.closest('button');
    if (!b) { if (e.target === big || e.target.classList.contains('box')) closeBig(); return; }
    if (b.classList.contains('bx')) { closeBig(); return; }
    if (b.classList.contains('prev')) { step(-1); return; }
    if (b.classList.contains('next')) { step(1); return; }
    var n = showing, i = inRow(n), act = b.dataset.act;
    if (act === 'earlier' && i > 0) changed(M.moveTo(row, n, i - 1));
    else if (act === 'later' && i >= 0 && i < row.length - 1) changed(M.moveTo(row, n, i + 2));
    else if (act === 'out') changed(M.takeOut(row, n));
    else if (act === 'add') { var next = M.insertAt(row, n, row.length, max()); if (next == null) rowLine(T.full); else changed(next); }
    else if (act && act.indexOf('mark') === 0) changed(M.setMark(row, n, act.slice(4)));
    if (showing != null) bigActs();
  });
  document.addEventListener('keydown', function(e){
    if (big.classList.contains('on')) {
      if (e.key === 'Escape') { e.preventDefault(); closeBig(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
      return;
    }
    // a tile reached with the Tab key opens big with Return, so nothing on the page needs a drag
    if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.classList && e.target.classList.contains('tile')) {
      e.preventDefault(); openBig(Number(e.target.dataset.n));
    }
  });

  start();
})();
"""

# The link on the carousel's Done line to the page where the slides are laid out (design.py).
LAY_OUT = "Lay out the slides"
LAY_OUT_TITLE = "Put photos side by side, add your own words and colors, and save the finished slides."

BACK_HOME = ("<a class='homelink' href='/home'><span aria-hidden='true'>&larr;</span>"
             "<span class='long'>Back to home</span><span class='short'>Home</span></a>")


def _shell(title, body_attrs, inner, scripts=""):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>" + html.escape(title) + "</title><style>" + CSS + "</style></head><body" + body_attrs + ">"
            "<div class='wrap'><div class='bar'>" + BACK_HOME + brand.bar()
            + inner + scripts + "</body></html>")


def plain_page(words):
    """A small page for when there is nothing to arrange: the words, and the way back home."""
    inner = ("</div><div class='plain'><p>" + html.escape(words) + "</p></div></div>")
    return _shell(brand.title(), "", inner)


def page_html(kit_name, piece):
    """The picker for one piece of one kit. Everything else arrives by /arrange-state."""
    attrs = " data-kit='" + html.escape(kit_name, quote=True) + "' data-piece='" + html.escape(piece, quote=True) + "'"
    inner = (
        "<a class='kitlink' id='kitlink' hidden>Back to the post kit</a></div>"
        "<header class='head'><span class='eyebrow' id='eyebrow'></span><h1 id='title'></h1>"
        "<p class='lede' id='help'></p>"
        "<p class='topline' id='l-reach' hidden></p><p class='topline' id='l-missing' hidden></p><p class='topline' id='l-dropped' hidden></p>"
        "</header>"
        "<section class='panel' id='panel'>"
        "<div class='phead'><h2 id='rowname'></h2><span class='count' id='count'></span><span class='advice' id='advice'></span><span class='prep' id='prep' hidden></span></div>"
        "<div class='rowwrap' id='rowwrap'><div class='row' id='row'></div></div>"
        "<p class='rowline' id='rowline'></p>"
        "<p class='legend' id='legend'></p>"
        "</section>"
        # The bar of buttons. It comes before the photos below in the page (so the Tab key reaches the
        # buttons before fifty photos) and is drawn after them, held at the bottom of the window. Every
        # line a press brings sits in the bar, under the button that was pressed.
        "<div class='dock' id='dock'><div class='dockin'>"
        "<div class='acts'><button class='btn' id='back' type='button' hidden>Back to my pick</button>"
        "<button class='btn main' id='happy' type='button' disabled>I&rsquo;m happy with this order</button>"
        "<span class='side'><span class='why' id='why'></span><span class='status' id='status'></span></span></div>"
        "<div class='donerow'><p class='doneline' id='doneline'></p>"
        "<button class='btn' id='openfolder' type='button' hidden>Open the Carousel folder</button>"
        "<a class='btn' id='layout' title='" + html.escape(LAY_OUT_TITLE, quote=True) + "' hidden>" + html.escape(LAY_OUT) + "</a></div>"
        "<p class='openline' id='openline'></p>"
        "<p class='canvaline' id='canvaline' hidden></p>"
        "<p class='note' id='note' hidden></p>"
        "</div></div>"
        "<section class='poolsec' id='poolsec'><div class='poolhead'><h2 id='poolname'></h2></div>"
        "<div class='pool' id='pool'></div></section>"
        "</div>"
        "<div class='big' id='big'><div class='box'>"
        "<button class='bx' type='button' aria-label='Close'>&#215;</button>"
        "<button class='nav prev' type='button' aria-label='Previous'>&#8249;</button>"
        "<div class='pic'><img alt=''><span class='cant'>Can&rsquo;t read this photo right now</span>"
        "<span class='wait'>Getting this photo ready...</span></div>"
        "<button class='nav next' type='button' aria-label='Next'>&#8250;</button>"
        "<p class='where'></p><div class='bacts'></div></div></div>"
    )
    scripts = "<script>" + MODEL_JS + "</script><script>" + DRAG_JS + "</script><script>" + PICKER_JS + "</script>"
    return _shell(brand.title("Reel" if piece == "reel" else "Carousel"), attrs, inner, scripts)


if __name__ == "__main__":
    print(len(page_html("A kit", "reel")), "characters")
