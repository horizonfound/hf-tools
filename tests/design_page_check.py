#!/usr/bin/env python3
"""The carousel designer's PAGE, checked. Run through tests/design_check.py (which calls the two functions here):

    python3 tests/design_check.py --only page                       the scripts by themselves (no server, seconds)
    python3 tests/design_check.py --only browser --port 8945 --work /private/tmp/<new folder>
                                                                    the real page in a hidden Chrome

check_page: what the page is made of (nothing from the internet in its own chrome, nothing the Claude app's
pane cannot do, nothing kept in the browser), every script parsed by the Mac's own JavaScript engine, and the
rules in DESIGN_MODEL_JS run there against numbers worked out by hand (where a photo sits in its frame, every
one-click layout, snapping, the limits a move and a resize are held to, Undo, which copy of a photo to use).

check_browser: the real page, served by the real page server from a pretend kit, driven with real pointer and
key events by tests/chrome_drive.py (a hidden Chrome on a throwaway profile; SKIP when there is no Chrome).
After every change it compares what is on the screen with what is in the design's file on the drive.
It never opens a window, never touches the real ~/.studio, and never presses a button that opens Finder.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
W, H = 1080, 1350

MODEL_TESTS_JS = r"""
(new Function(MODEL_SRC)).call(this);
var M = this.DesignModel, out = [], W = 1080, H = 1350;
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
function near(a, b){ return Math.abs(a - b) < 1e-6; }
function F(id, n, x, y, w, h, more){ var b = {id: id, n: n, x: x, y: y, w: w, h: h, ox: 0.5, oy: 0.5, zoom: 1}; for (var k in (more || {})) b[k] = more[k]; return b; }
function TX(id, x, y, w, h){ return {id: id, type: 'text', text: 'Words', font: 'Inter', size: 96, weight: 400, italic: false, upper: false, al: 'center', ls: 0, lh: 1.15, color: '#2a2622', x: x, y: y, w: w, h: h}; }
function ST(slides, blocks){ return {slides: slides, bg: '#ffffff', blocks: blocks}; }
function pick(o, keys){ var r = {}; keys.forEach(function(k){ r[k] = o[k]; }); return r; }
var full = F(1, 2, 0, 0, W, H);

// ---- a photo inside its frame ----
var L = M.layoutImg(full, 1200, 1800);
t('layout: a tall photo (1200x1800) in a whole slide is as wide as the slide and 1620 tall, centred (top -135)', near(L.iw, 1080) && near(L.ih, 1620) && near(L.left, 0) && near(L.top, -135), L);
L = M.layoutImg(full, 1800, 1200);
t('layout: a wide photo (1800x1200) in a whole slide is as tall as the slide and 2025 wide, centred (left -472.5)', near(L.iw, 2025) && near(L.ih, 1350) && near(L.left, -472.5) && near(L.top, 0), L);
L = M.layoutImg(F(1, 2, 0, 0, W, H, {zoom: 2, ox: 0, oy: 1}), 1200, 1800);
t('layout: zoom 2, held to the left and the bottom: 2160x3240, left 0, top -1890', near(L.iw, 2160) && near(L.ih, 3240) && near(L.left, 0) && near(L.top, -1890), L);
t('layout: the same from a small copy of the same shape (600x900) as from the large one', eq(M.layoutImg(full, 600, 900), M.layoutImg(full, 1200, 1800)));
L = M.layoutImg({x: 0, y: 0, w: 1080, h: 675}, 1200, 1800);
t('layout: a frame with no crop written down is centred at zoom 1 (top half of a slide: 1080x1620, top -472.5)', near(L.iw, 1080) && near(L.ih, 1620) && near(L.top, -472.5), L);
L = M.layoutImg(full, 0, 0);
t('layout: a picture with no size yet does not break the page', isFinite(L.iw) && isFinite(L.left), L);
t('layout: the photo always covers its frame, whatever the shape', [[1200, 1800], [1800, 1200], [1400, 1400], [300, 450], [5000, 700]].every(function(p){
  return [[1080, 1350], [2160, 1350], [1080, 675], [540, 1350], [60, 60]].every(function(f){
    var l = M.layoutImg({w: f[0], h: f[1], ox: 0.3, oy: 0.8, zoom: 1.4}, p[0], p[1]);
    return l.iw >= f[0] - 1e-6 && l.ih >= f[1] - 1e-6 && l.left <= 1e-6 && l.top <= 1e-6 && l.left + l.iw >= f[0] - 1e-6 && l.top + l.ih >= f[1] - 1e-6;
  });
}));
var P = M.pan(full, 0, 27, 1200, 1800);
t('move inside: dragging a tall photo 27 down in a whole slide (270 to spare) takes oy from 0.5 to 0.4; ox stays', eq(P, {ox: 0.5, oy: 0.4}), P);
t('move inside: it stops at the photo\'s own edge', eq(M.pan(full, 0, 1000, 1200, 1800), {ox: 0.5, oy: 0}) && eq(M.pan(full, 0, -1000, 1200, 1800), {ox: 0.5, oy: 1}));
P = M.pan(full, -94.5, 0, 1800, 1200);
t('move inside: a wide photo 94.5 to the left (945 to spare) takes ox from 0.5 to 0.6', eq(P, {ox: 0.6, oy: 0.5}), P);
t('zoom: one turn of the wheel up is 1.05, down from 1 stays 1, and it never passes 3', M.zoomBy(1, -1) === 1.05 && M.zoomBy(1, 1) === 1 && M.zoomBy(2.95, -1) === 3 && M.zoomTo(5) === 3 && M.zoomTo(0.2) === 1 && M.zoomTo(2) === 2, [M.zoomBy(1, -1), M.zoomBy(1, 1), M.zoomBy(2.95, -1)]);

// ---- where things may be ----
t('slide-of: by the middle of the thing', M.slideOf({x: 1000, w: 1080}, 3) === 1 && M.slideOf({x: -500, w: 200}, 3) === 0 && M.slideOf({x: 9000, w: 200}, 3) === 2 && M.slideOf({x: 2300, w: 300}, 5) === 2);
t('clamp: 40 px of a thing always stays on the strip', eq(M.clampXY(-2000, -5000, 1080, 1350, 3), {x: -1040, y: -1310}) && eq(M.clampXY(99999, 5000, 1080, 1350, 3), {x: 3200, y: 1310}) && eq(M.clampXY(500, 20, 200, 200, 3), {x: 500, y: 20}));
t('on the strip: the Assistant\'s own rule', M.onStrip({x: -1040, y: -1310, w: 1080, h: 1350}, 3) && !M.onStrip({x: -1041, y: 0, w: 1080, h: 1350}, 3) && M.onStrip({x: 3200, y: 1310, w: 60, h: 60}, 3) && !M.onStrip({x: 3201, y: 0, w: 60, h: 60}, 3));

// ---- snapping ----
var two = ST(2, [F(1, 2, 0, 0, 500, 500), F(2, 4, 1234.5, 100, 400, 400)]);
var lx = M.lines(two, 'x', 1), ly = M.lines(two, 'y', 1);
t('snap lines: every sixth of every slide, and the other things\' edges (not its own)', lx.length === 15 && lx.indexOf(180) >= 0 && lx.indexOf(2160) >= 0 && lx.indexOf(1234.5) >= 0 && lx.indexOf(1634.5) >= 0 && lx.indexOf(500) < 0 && ly.length === 9 && ly.indexOf(225) >= 0 && ly.indexOf(100) >= 0, [lx.length, ly.length]);
t('nearest: the closest line within reach, as a distance; none in reach is null', M.nearest(175, [0, 180, 360], 10) === 5 && M.nearest(100, [0, 180, 360], 10) === null && M.nearest(183, [180, 185], 10) === 2 && M.nearest(190.5, [180], 10) === null);
var one = ST(3, [F(1, 2, 0, 0, W, H)]);
var mv = M.move(one, one.blocks[0], 123.456, 10, {snap: false});
t('move: no snapping, numbers kept to two places', mv.x === 123.46 && mv.y === 10 && mv.gx.length === 0 && mv.gy.length === 0, mv);
mv = M.move(one, one.blocks[0], 176, 0, {snap: true, thr: 10});
t('move: 4 px short of a sixth of a slide, it snaps there (x 180) and a guide line shows at 180; y snaps to the top edge', mv.x === 180 && eq(mv.gx, [180]) && mv.y === 0 && eq(mv.gy, [0]), mv);
mv = M.move(one, one.blocks[0], 176, 0, {snap: false, thr: 10});
t('move: with Alt held (snap off) it stays at 176', mv.x === 176 && mv.gx.length === 0, mv);
mv = M.move(one, one.blocks[0], 150, 0, {snap: true, thr: 40});
t('move: the reach is in screen pixels, so drawn small it reaches further (30 away, reach 40: snaps)', mv.x === 180, mv);
mv = M.move(two, two.blocks[0], 730, 300, {snap: true, thr: 10});
t('move: its right edge snaps to another photo\'s left edge (1234.5), guide there', mv.x === 734.5 && eq(mv.gx, [1234.5]) && mv.y === 300 && mv.gy.length === 0, mv);
mv = M.move(one, one.blocks[0], -5000, -5000, {snap: true, thr: 10});
t('move: held to the strip, and no guide line shows where it did not stop', mv.x === -1040 && mv.y === -1310 && mv.gx.length === 0 && mv.gy.length === 0, mv);

// ---- resizing ----
var rz = M.resize(one, one.blocks[0], 'br', -100, -200, {});
t('resize: bottom-right corner in by 100 and up by 200', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 0, y: 0, w: 980, h: 1150}), rz);
rz = M.resize(one, one.blocks[0], 'br', -5000, -5000, {});
t('resize: never smaller than 60 either way', rz.w === 60 && rz.h === 60 && rz.x === 0 && rz.y === 0, rz);
rz = M.resize(one, one.blocks[0], 'tl', 5000, 5000, {});
t('resize: from the top-left it stops 60 short of the far corner', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 1020, y: 1290, w: 60, h: 60}), rz);
rz = M.resize(one, one.blocks[0], 'br', 5000, 500, {});
t('resize: never taller than a slide, never wider than the whole strip', rz.h === 1350 && rz.w === 3240, rz);
var small = ST(3, [F(1, 2, 100, 100, 400, 400)]);
rz = M.resize(small, small.blocks[0], 'tr', -80, 50, {});
t('resize: top-right corner: right edge in by 80, top down by 50', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 100, y: 150, w: 320, h: 350}), rz);
rz = M.resize(small, small.blocks[0], 'bl', -30, 20, {});
t('resize: bottom-left corner: left edge out by 30, bottom down by 20', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 70, y: 100, w: 430, h: 420}), rz);
rz = M.resize(one, one.blocks[0], 'br', -540, 9, {shift: true});
t('resize with Shift: the shape is kept (half as wide, half as tall), whatever the up-and-down travel', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 0, y: 0, w: 540, h: 675}), rz);
rz = M.resize(one, one.blocks[0], 'tl', 540, 0, {shift: true});
t('resize with Shift from the top-left: the bottom-right corner stays put', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 540, y: 675, w: 540, h: 675}), rz);
rz = M.resize(one, one.blocks[0], 'br', -5000, 0, {shift: true});
t('resize with Shift: the small limit keeps the shape too (60 wide, 75 tall)', rz.w === 60 && rz.h === 75, rz);
rz = M.resize(one, one.blocks[0], 'br', 800, 0, {shift: true});
t('resize with Shift: a whole-slide frame cannot grow (it is already as tall as a slide)', rz.w === 1080 && rz.h === 1350, rz);
rz = M.resize(one, one.blocks[0], 'br', -176, 0, {snap: true, thr: 10});
t('resize: the pulled edge snaps (904 to 900) with a guide line there', rz.w === 900 && eq(rz.gx, [900]), rz);
rz = M.resize(one, one.blocks[0], 'br', -176, 0, {snap: true, thr: 10, shift: true});
t('resize with Shift: no snapping (the shape wins)', rz.w === 904 && rz.h === 1130 && rz.gx.length === 0, rz);
var off = ST(3, [F(1, 2, -500, 100, 560, 400)]);
rz = M.resize(off, off.blocks[0], 'br', -100, 0, {});
t('resize: a frame hanging off the left keeps 40 px on the strip (right edge stops at 40)', rz.x === -500 && rz.w === 540, rz);
var offr = ST(3, [F(1, 2, 3000, 100, 400, 400)]);
rz = M.resize(offr, offr.blocks[0], 'tl', 300, 0, {});
t('resize: a frame hanging off the right keeps 40 px on the strip (left edge stops at 3200)', rz.x === 3200 && rz.w === 200, rz);
rz = M.resize(small, small.blocks[0], 'tl', -50, -70, {widthOnly: true, minW: 80});
t('resize, width only (a text box): the height and the top do not move', eq(pick(rz, ['x', 'y', 'w', 'h']), {x: 50, y: 100, w: 450, h: 400}), rz);
rz = M.resize(small, small.blocks[0], 'br', -5000, 0, {widthOnly: true, minW: 80});
t('resize, width only: never narrower than the least given (80)', rz.w === 80 && rz.h === 400, rz);
var allOk = true, seed = 7;
function rnd(){ seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
for (var i = 0; i < 400; i++) {
  var b0 = F(1, 2, Math.round(rnd() * 3000 - 400), Math.round(rnd() * 1200 - 100), 60 + Math.round(rnd() * 1500), 60 + Math.round(rnd() * 1290));
  var c0 = M.clampXY(b0.x, b0.y, b0.w, b0.h, 3); b0.x = c0.x; b0.y = c0.y;
  var s3 = ST(3, [b0, F(2, 4, 700, 300, 333, 444)]);
  var r = M.resize(s3, b0, ['tl', 'tr', 'bl', 'br'][i % 4], rnd() * 6000 - 3000, rnd() * 4000 - 2000, {snap: i % 3 === 0, thr: 30, shift: i % 5 === 0});
  var m2 = M.move(s3, b0, rnd() * 8000 - 4000, rnd() * 4000 - 2000, {snap: i % 2 === 0, thr: 30});
  if (!(r.w >= 60 && r.h >= 60 && r.w <= 3240 && r.h <= 1350 && M.onStrip(r, 3))) { allOk = false; t('resize, case ' + i, false, [b0, r]); break; }
  if (!M.onStrip({x: m2.x, y: m2.y, w: b0.w, h: b0.h}, 3)) { allOk = false; t('move, case ' + i, false, [b0, m2]); break; }
}
t('400 moves and 400 resizes at random: every result is one the Assistant will take (size limits, 40 px on the strip)', allOk);
var nd = M.nudge(one, 1, 5, 0);
t('nudge: an arrow key moves it 5; the layout it was given is not changed', nd.blocks[0].x === 5 && one.blocks[0].x === 0 && nd !== one);
t('nudge: held to the strip like a move', M.nudge(ST(3, [F(1, 2, -1040, 0, W, H)]), 1, -50, 0).blocks[0].x === -1040 && M.nudge(ST(3, [F(1, 2, 0, 1300, W, H)]), 1, 0, 50).blocks[0].y === 1310);
t('nudge: nothing to move gives the same layout back', M.nudge(one, 99, 5, 0) === one && M.nudge(ST(3, [F(1, 2, -1040, 0, W, H)]), 1, -50, 0).blocks.length === 1);

// ---- the one-click buttons ----
var five = ST(5, [F(1, 2, 2300, 400, 300, 300), F(2, 4, 0, 0, W, H), F(3, 6, 4500, 100, 200, 200), TX(4, 1200, 300, 800, 110)]);
function box(st, id){ return pick(M.find(st, id), ['x', 'y', 'w', 'h']); }
var a = M.act(five, 1, 'full');
t('Fill slide: the slide its middle is on (slide 3), whole', eq(box(a.st, 1), {x: 2160, y: 0, w: 1080, h: 1350}) && !('sel' in a) && five.blocks[0].x === 2300, box(a.st, 1));
t('Across 2 slides: that slide and the next', eq(box(M.act(five, 1, 'span2').st, 1), {x: 2160, y: 0, w: 2160, h: 1350}));
t('Across 2 slides, on the last slide: the one before it and the last', eq(box(M.act(five, 3, 'span2').st, 3), {x: 3240, y: 0, w: 2160, h: 1350}));
t('Top half', eq(box(M.act(five, 1, 'top').st, 1), {x: 2160, y: 0, w: 1080, h: 675}));
t('Bottom half', eq(box(M.act(five, 1, 'bottom').st, 1), {x: 2160, y: 675, w: 1080, h: 675}));
t('Left half', eq(box(M.act(five, 1, 'left').st, 1), {x: 2160, y: 0, w: 540, h: 1350}));
t('Right half', eq(box(M.act(five, 1, 'right').st, 1), {x: 2700, y: 0, w: 540, h: 1350}));
t('Add border: every edge comes in by 70', eq(box(M.act(five, 2, 'margin').st, 2), {x: 70, y: 70, w: 940, h: 1210}));
a = M.act(five, 3, 'margin');
t('Add border on a photo too small for one: nothing changes, and it says why', a.st === five && a.why === 'small', a.why);
a = M.act(ST(3, [F(1, 2, 10, 10, 500, 500, {ox: 0.1, oy: 0.9, zoom: 2})]), 1, 'empty');
t('Take the photo out: an empty frame, its crop back to the middle', a.st.blocks[0].n === null && a.st.blocks[0].ox === 0.5 && a.st.blocks[0].oy === 0.5 && a.st.blocks[0].zoom === 1 && a.st.blocks[0].w === 500);
t('Center on slide: left and right only (a 300-wide photo on slide 3 goes to x 2550), up and down kept', eq(box(M.act(five, 1, 'center').st, 1), {x: 2550, y: 400, w: 300, h: 300}));
function ids(st){ return st.blocks.map(function(b){ return b.id; }); }
a = M.act(five, 1, 'front');
t('Bring forward: it becomes the last in the list (on top)', eq(ids(a.st), [2, 3, 4, 1]) && eq(ids(five), [1, 2, 3, 4]));
var back = M.act(five, 3, 'back').st, back2 = M.act(back, 3, 'back'), back3 = M.act(back2.st, 3, 'back');
t('Send back: it becomes the first in the list; again and again changes nothing (there is no number to go below zero)', eq(ids(back), [3, 1, 2, 4]) && back2.st === back && back3.st === back);
t('Bring forward on the top one changes nothing', M.act(five, 4, 'front').st === five);
a = M.act(ST(3, [F(1, 2, 100, 100, 500, 500, {slot: 2, ox: 0.2}), F(7, 4, 0, 0, 50, 50)]), 1, 'dup');
t('Duplicate: a copy 60 down and right, on top, with a new number, and it becomes the selected one', a.st.blocks.length === 3 && eq(pick(a.st.blocks[2], ['id', 'n', 'x', 'y', 'w', 'h', 'ox']), {id: 8, n: 2, x: 160, y: 160, w: 500, h: 500, ox: 0.2}) && a.sel === 8 && !('slot' in a.st.blocks[2]) && a.st.blocks[0].slot === 2, a.st.blocks[2]);
var many = []; for (i = 1; i <= 80; i++) many.push(F(i, 2, 0, 0, 100, 100));
a = M.act(ST(3, many), 5, 'dup');
t('Duplicate with 80 things already: nothing is added, and it says why', a.why === 'many' && a.st.blocks.length === 80);
a = M.act(five, 2, 'del');
t('Remove: gone from the list, nothing selected, the rest in the same order', eq(ids(a.st), [1, 3, 4]) && a.sel === null && five.blocks.length === 4);
t('Center, Bring forward, Send back, Duplicate and Remove work on a text box too', eq(ids(M.act(five, 4, 'back').st), [4, 1, 2, 3]) && M.act(five, 4, 'dup').st.blocks.length === 5 && M.act(five, 4, 'del').st.blocks.length === 3 && M.find(M.act(five, 4, 'center').st, 4).x === 1220);
t('the photo-only buttons leave a text box alone', ['full', 'span2', 'top', 'bottom', 'left', 'right', 'margin', 'empty'].every(function(k){ return M.act(five, 4, k).st === five; }));
t('a button pressed for something that is not there changes nothing', M.act(five, 99, 'full').st === five && M.act(five, 1, 'no-such').st === five);
t('a button that changes nothing gives the very same layout back (so no Undo step, no save)', M.act(ST(3, [F(1, 2, 0, 0, W, H)]), 1, 'full').st.blocks[0] && (function(){ var s = ST(3, [F(1, 2, 0, 0, W, H)]); return M.act(s, 1, 'full').st === s; })());
t('every button\'s result is one the Assistant will take', ['full', 'span2', 'top', 'bottom', 'left', 'right', 'margin', 'center', 'dup'].every(function(k){
  return [five, ST(2, [F(1, 2, 2100, 1300, 60, 60)]), ST(2, [F(1, 2, -1040, -1310, W, H)])].every(function(s){
    return M.act(s, 1, k).st.blocks.every(function(b){ return b.w >= 60 && b.h >= 60 && b.w <= s.slides * W && b.h <= H && M.onStrip(b, s.slides); });
  });
}));

// ---- slides ----
var seven = ST(3, [F(1, 2, 0, 0, W, H), F(2, 4, 1080, 0, W, H), F(3, 6, 2160, 0, W, H)]);
a = M.fewerSlides(seven);
t('Slides minus with a photo on the last slide: refused, and it says which slide', a.st === seven && a.why === 'last' && a.slide === 3, a);
a = M.fewerSlides(ST(3, [F(1, 2, 0, 0, W, H), F(2, 4, 1080, 0, W, H)]));
t('Slides minus with the last slide empty: one fewer', a.st.slides === 2 && !a.why && a.st.blocks.length === 2);
t('Slides minus: a photo that ends exactly where the last slide starts is not on it', M.fewerSlides(ST(3, [F(1, 2, 0, 0, 2160, H)])).st.slides === 2);
t('Slides minus: a photo reaching 1 px into the last slide is on it', M.fewerSlides(ST(3, [F(1, 2, 0, 0, 2161, H)])).why === 'last');
t('Slides minus: something hanging off the end of the strip counts as on the last slide', M.fewerSlides(ST(3, [F(1, 2, 3200, 0, 300, 300)])).why === 'last');
t('Slides minus: a text box on the last slide stops it too', M.fewerSlides(ST(3, [TX(1, 2300, 300, 800, 110)])).why === 'last');
t('Slides minus at 2 slides: refused', M.fewerSlides(ST(2, [])).why === 'min');
t('Slides minus: something wider than the slides that would be left stops it', M.fewerSlides(ST(3, [F(1, 2, -200, 0, 2260, H)])).why === 'wide');
t('Slides plus: one more, up to 20', M.moreSlides(seven).st.slides === 4 && M.moreSlides(ST(20, [])).why === 'max' && M.moreSlides(ST(20, [])).st.slides === 20);
t('Background: a color is taken in small letters; the same color, or something that is not a color, changes nothing', M.setBg(seven, '#F4EFE6').bg === '#f4efe6' && M.setBg(seven, '#ffffff') === seven && M.setBg(seven, 'red') === seven && M.setBg(seven, '#fff') === seven && M.setBg(seven, 'url(x)') === seven);

// ---- photos from the tray ----
t('used: which photos are on the slides, and how often', eq(M.used(ST(3, [F(1, 2, 0, 0, W, H), F(2, 2, 1080, 0, W, H), F(3, null, 0, 0, 100, 100), TX(4, 0, 0, 500, 100)])), {2: 2}));
t('first empty slide: the first whose middle no photo covers', M.firstEmptySlide(ST(3, [F(1, 2, 0, 0, W, H), F(2, 4, 1080, 0, W, H)])) === 2 && M.firstEmptySlide(seven) === -1 && M.firstEmptySlide(ST(3, [F(1, 2, 0, 0, W, 600)])) === 0 && M.firstEmptySlide(ST(2, [TX(1, 0, 0, W, 1350)])) === 0);
var holes = ST(3, [F(1, null, 2160, 0, W, H, {slot: 3}), F(2, null, 1080, 0, W, H, {slot: 1}), F(3, null, 0, 0, W, H, {slot: 2}), F(4, 9, 0, 0, 200, 200)]);
t('next empty frame: by its slot', M.nextHole(holes).id === 2 && M.nextHole(seven) === null);
t('next empty frame, with no slots: left to right', M.nextHole(ST(3, [F(1, null, 2160, 0, W, H), F(2, null, 0, 0, W, H)])).id === 2);
a = M.addPhoto(holes, 12, null);
t('a clicked photo goes into the next empty frame, which becomes the selected one', M.find(a.st, 2).n === 12 && a.sel === 2 && a.st.blocks.length === 4 && M.find(holes, 2).n === null);
a = M.addPhoto(ST(3, [F(1, 2, 0, 0, W, H), F(5, 4, 1080, 0, W, H)]), 12, null);
t('with no empty frame it fills the first empty slide, on top, with the next number', a.st.blocks.length === 3 && eq(pick(a.st.blocks[2], ['id', 'n', 'x', 'y', 'w', 'h', 'ox', 'oy', 'zoom']), {id: 6, n: 12, x: 2160, y: 0, w: 1080, h: 1350, ox: 0.5, oy: 0.5, zoom: 1}) && a.sel === 6 && a.st.slides === 3, a.st.blocks[2]);
a = M.addPhoto(seven, 12, null);
t('with every slide full it adds a slide for it', a.st.slides === 4 && a.st.blocks[3].x === 3240 && a.sel === 4);
var twenty = []; for (i = 0; i < 20; i++) twenty.push(F(i + 1, 2, i * W, 0, W, H));
a = M.addPhoto(ST(20, twenty), 12, null);
t('with 20 full slides nothing is added, and it says why', a.why === 'full' && a.st.blocks.length === 20 && a.st.slides === 20);
t('with 80 things already nothing is added, and it says why', M.addPhoto(ST(3, many), 12, 1).why === 'many');
a = M.addPhoto(holes, 12, 1);
t('a photo dropped on a slide makes a new frame filling THAT slide, even when an empty frame waits elsewhere', a.st.blocks.length === 5 && a.st.blocks[4].x === 1080 && a.st.blocks[4].w === 1080 && a.st.blocks[4].n === 12 && M.find(a.st, 2).n === null && a.sel === a.st.blocks[4].id);
a = M.clickPhoto(ST(3, [F(1, 2, 0, 0, W, H, {ox: 0.1, oy: 0.2, zoom: 2.5})]), 1, 9);
t('a clicked photo with a frame selected goes into that frame, its crop back to the middle', eq(pick(a.st.blocks[0], ['n', 'ox', 'oy', 'zoom', 'w']), {n: 9, ox: 0.5, oy: 0.5, zoom: 1, w: 1080}) && a.sel === 1 && a.st.blocks.length === 1);
a = M.clickPhoto(ST(3, [TX(1, 0, 0, 500, 100)]), 1, 9);
t('a clicked photo with a text box selected is added (the text is left alone)', a.st.blocks.length === 2 && a.st.blocks[0].type === 'text' && a.st.blocks[1].n === 9);
t('swap leaves a text box alone', (function(){ var s = ST(3, [TX(1, 0, 0, 500, 100)]); return M.swapPhoto(s, 1, 9) === s; })());
var stack = ST(3, [F(1, 2, 0, 0, W, H), F(2, 4, 100, 100, 300, 300), TX(3, 150, 150, 200, 100)]);
t('drop: onto the topmost frame under the pointer (a text box over it does not count)', eq(M.dropAt(stack, 200, 200), {kind: 'frame', id: 2}) && eq(M.dropAt(stack, 800, 800), {kind: 'frame', id: 1}));
t('drop: onto a bare part of a slide is that slide', eq(M.dropAt(stack, 1500, 300), {kind: 'slide', i: 1}) && eq(M.dropAt(stack, 3239, 10), {kind: 'slide', i: 2}));
t('drop: off the strip is nowhere', M.dropAt(stack, -1, 10) === null && M.dropAt(stack, 3240, 10) === null && M.dropAt(stack, 10, 1351) === null && M.dropAt(stack, 10, -1) === null);

// ---- which copy of a photo ----
var SZ = {s: 520, l: 1600, x: 2400, xx: 4320};
t('copy: the smallest made copy at least as large as the photo will be drawn', M.pickSize(400, 6000, SZ) === 's' && M.pickSize(520, 6000, SZ) === 's' && M.pickSize(521, 6000, SZ) === 'l' && M.pickSize(1700, 6000, SZ) === 'x' && M.pickSize(2401, 6000, SZ) === 'xx' && M.pickSize(9000, 6000, SZ) === 'xx');
t('copy: never a larger copy than the photo itself has pixels for', M.pickSize(2000, 1500, SZ) === 'l' && M.pickSize(600, 450, SZ) === 's' && M.pickSize(5000, 2400, SZ) === 'x');
t('copy on screen: the 520 one until it is drawn larger than that, then the 1600 one (never a bigger one)', M.screenCopy(520, 1800, SZ) === 's' && M.screenCopy(521, 1800, SZ) === 'l' && M.screenCopy(3000, 6000, SZ) === 'l' && M.screenCopy(900, 450, SZ) === 's');

// ---- Undo ----
var h = M.history(60);
for (i = 1; i <= 61; i++) h.push('s' + i);
t('undo: 60 steps are kept; the oldest goes first', h.size() === 60 && h.pop() === 's61' && h.pop() === 's60' && h.size() === 58);
h.clear();
t('undo: nothing to undo is null', h.size() === 0 && h.pop() === null);
h.push('a', 'zoom:1'); var p2 = h.push('b', 'zoom:1'), p3 = h.push('c', 'zoom:1');
t('undo: a run of changes with the same key is one step, back to before the first of them', p2 === false && p3 === false && h.size() === 1 && h.pop() === 'a');
h.push('a', 'zoom:1'); h.push('b'); h.push('c', 'zoom:1');
t('undo: another change in between ends the run', h.size() === 3);
h.clear(); h.push('a', 'k'); h.mark(); h.push('b', 'k');
t('undo: a new press ends the run (two taps of an arrow key are two steps)', h.size() === 2);
h.clear(); h.push('a', 'k'); h.pop(); h.push('b', 'k');
t('undo: an Undo ends the run', h.size() === 1 && h.pop() === 'b');

// ---- the rest ----
t('view: to start with, about three slides across the space, and no taller than about a third of the window', M.viewStart(1000, 900) === 245 && M.viewStart(300, 800) === 94 && M.viewStart(100, 800) === 90 && M.viewStart(5000, 3000) === 480, [M.viewStart(1000, 900), M.viewStart(300, 800)]);
t('view: Bigger and Smaller go by a quarter, between 90 and 480', M.viewStep(230, 1) === 288 && M.viewStep(230, -1) === 184 && M.viewStep(470, 1) === 480 && M.viewStep(100, -1) === 90);
var td = M.tidy({slides: 3, bg: '#ffffff', blocks: [{id: 1, n: 2, x: 0, y: 0, w: 100, h: 100}, TX(2, 0, 0, 500, 100)]});
t('a layout from the Assistant is given its crop where none is written, and text boxes are left as they are', td.blocks[0].ox === 0.5 && td.blocks[0].oy === 0.5 && td.blocks[0].zoom === 1 && !('ox' in td.blocks[1]));
t('patch: no difference gives the very same layout back', M.patch(one, 1, {x: 0, y: 0}) === one && M.patch(one, 1, {x: 1}) !== one && M.patch(one, 5, {x: 1}) === one);
t('next number: one above the highest in the layout', M.nextId(ST(3, [F(4, 1, 0, 0, 9, 9), F(17, 1, 0, 0, 9, 9)])) === 18 && M.nextId(ST(3, [])) === 1 && M.nextId(ST(3, [F(1000000, 1, 0, 0, 9, 9)])) === 1);
t('kind: a text box is text, anything else a photo frame; an empty frame is a frame with no photo', M.typeOf(TX(1, 0, 0, 9, 9)) === 'text' && M.typeOf(full) === 'photo' && M.isHole(F(1, null, 0, 0, 9, 9)) && !M.isHole(full) && !M.isHole(TX(1, 0, 0, 9, 9)));
M.useLimits({slides: [2, 20], frame_min: 60, on_strip: 40, zoom: [1, 3], blocks: 80});
t('the Assistant\'s own limits are the ones the rules start with', M.RULES.frameMin === 60 && M.RULES.onStrip === 40 && M.RULES.blocks === 80 && eq(M.RULES.slides, [2, 20]) && eq(M.RULES.zoom, [1, 3]));
JSON.stringify(out);
"""


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


def check_page(case, work):
    """The page's own make-up, each script parsed, and the rules run by themselves."""
    sys.path.insert(0, str(SCRIPTS))
    import design_page as dp
    page = dp.page_html("A kit")
    plain = dp.plain_page("I can't find that shoot's posts. Is the drive plugged in?")
    names = [n for n, _ in dp.SCRIPTS]
    src = {n: s for n, s in dp.SCRIPTS}
    all_js = "\n".join(s for _, s in dp.SCRIPTS) + dp.DESIGN_START_JS

    # what the page is made of
    urls = set(re.findall(r"https?://[^\s'\"<>)]+", page))
    case("designer page: no address on the internet in it but Google Fonts (for slide text only)",
         all(u.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")) for u in urls), sorted(urls))
    case("designer page: the page itself names no address on the internet at all (Google's arrives with the state, from the Assistant)", not urls, sorted(urls))
    case("designer page: no script, picture or frame from another address", not re.search(r"<script[^>]*\ssrc=", page) and "@import" not in page and "<img src" not in page and "<iframe" not in page)
    for word in ("draggable", "ondragstart", "dataTransfer", "dragover", "localStorage", "sessionStorage", "indexedDB", "document.cookie",
                 "navigator.clipboard", "innerHTML", "insertAdjacentHTML", "document.write", "eval(", "navigator.onLine"):
        case(f"designer page: no {word}", word not in page)
    case("designer page: only the kit's folder name is put into it", "data-kit='A kit'" in page and page.count("A kit") == 1)
    case("designer page: a kit name is html-escaped on its way in", "data-kit='&lt;b&gt; &amp; &#x27;x&#x27;'" in dp.page_html("<b> & 'x'"))
    case("designer page: the plain page has the Back to home button and the words", "href='/home'" in plain and "Back to home" in plain and "I can&#x27;t find that shoot&#x27;s posts." in plain)
    case("designer page: it has the Back to home button and the brand, like the pickers", "class='homelink' href='/home'" in page and "class='brand'" in page)
    case("designer styles: no backslash, fetch nothing (no url(...), no @font-face), light only",
         "\\" not in dp.DESIGN_CSS and "url(" not in dp.DESIGN_CSS and "@font-face" not in dp.DESIGN_CSS and "prefers-color-scheme" not in dp.DESIGN_CSS)
    case("designer styles: no web font for the page's own chrome (the system's own, as the pickers have it)",
         not re.search(r"Fraunces|DM Sans|Georgia|googleapis|gstatic|font-family", dp.DESIGN_CSS) and "var(--sans)" in dp.DESIGN_CSS)
    case("designer styles: the selected thing is Nicole's blue, on the pickers' own colours", "--sel:#2f7cf6" in dp.DESIGN_CSS and "var(--panel)" in dp.DESIGN_CSS and "var(--accent)" in dp.DESIGN_CSS)
    case("designer page: the scripts go on in order (the rules, the core, the strip, then the later parts) and the page starts last",
         names[:3] == ["DESIGN_MODEL_JS", "DESIGN_CORE_JS", "DESIGN_EDIT_JS"]
         and page.index(src["DESIGN_MODEL_JS"]) < page.index(src["DESIGN_CORE_JS"]) < page.index(src["DESIGN_EDIT_JS"]) < page.index(dp.DESIGN_START_JS)
         and page.rstrip().endswith("</script></body></html>"))
    case("designer page: no script holds a closing script tag", "</script" not in all_js.lower())
    bare = re.sub(r"//[^\n]*", "", src["DESIGN_MODEL_JS"])           # the script without its comments
    case("the rules script has no page in it (no document, no window but the one it hangs itself on)",
         "document" not in bare and bare.count("window") == 2, bare.count("window"))
    # the lines a press brings sit beside the buttons that were pressed
    case("designer page: the line a Slides press brings is inside the Slides group, beside its buttons",
         bool(re.search(r"<div class='group' id='g-slides'>(?:(?!</div>).)*id='slides-plus'(?:(?!</div>).)*id='slides-line'(?:(?!</div>).)*</div>", page, re.S)))
    case("designer page: the line a selection button brings, and the help line, are inside the selection's own bar",
         bool(re.search(r"<div class='d-tools selbar off' id='selbar'>(?:(?!</div>).)*id='selline'(?:(?!</div>).)*id='selhint'(?:(?!</div>).)*</div>", page, re.S)))
    case("designer page: the line a tray click brings is on the tray's own heading line",
         bool(re.search(r"<div class='trayhead'>(?:(?!</div>).)*id='trayname'(?:(?!</div>).)*id='trayline'(?:(?!</div>).)*</div>", page, re.S)))
    case("designer page: the save status sits beside the design's name", bool(re.search(r"id='d-name'></b><span class='savestate' id='d-status'", page)))
    for f in ("design_page.py", "design_js_model.py", "design_js_core.py", "design_js_edit.py"):
        text = (SCRIPTS / f).read_text(encoding="utf-8")
        code_only = "\n".join(ln.split("#")[0] for ln in re.sub(r'"""(?:.|\n)*?"""', '""', text).splitlines())
        case(f"{f}: runs no Mac-only program and uses no Mac-only call", not re.search(r"\b(sips|osascript|chflags|caffeinate|fcntl|subprocess)\b|/Volumes|%-d", code_only))
        case(f"{f}: Python never formats over the JavaScript (the scripts are raw strings, joined as they are)",
             not re.search(r'JS\s*(%|\.format\()', text) and not re.search(r'\bf(r|R)?"""', text) and (f == "design_page.py" or 'JS = r"""' in text))

    # each script parses under the Mac's own JavaScript engine
    probe = work / "design-parse-probe.js"
    for name, s in list(dp.SCRIPTS) + [("DESIGN_START_JS", dp.DESIGN_START_JS)]:
        probe.write_text("var SRC = " + json.dumps(s) + ";\nvar out; try { new Function(SRC); out = 'parses'; } catch (e) { out = 'SYNTAX ERROR: ' + e; }\nout;\n", encoding="utf-8")
        r = osascript(probe)
        case(f"{name} parses under osascript -l JavaScript", r.returncode == 0 and r.stdout.strip() == "parses", r.stdout.strip() or r.stderr.strip())

    # the rules, by themselves
    f = work / "design-model-tests.js"
    f.write_text("var MODEL_SRC = " + json.dumps(dp.DESIGN_MODEL_JS) + ";\n" + MODEL_TESTS_JS, encoding="utf-8")
    r = osascript(f)
    try:
        got = json.loads(r.stdout) if r.returncode == 0 else None
    except ValueError:
        got = None
    if not case("the rules ran to the end under osascript", got is not None and len(got) >= 80, (r.stderr or r.stdout)[-400:]):
        return
    for name, ok, detail in got:
        case("rules: " + name, ok, detail)


# ---------------------------------------------------------------------------------------------------------
# the real page in a hidden Chrome
# ---------------------------------------------------------------------------------------------------------

def check_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the real-browser checks: no Chrome on this computer", flush=True)
        return
    target = work / "browser"
    ok, out = make_kit(target, "Fake beach", 14)
    if not case("browser: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Fake beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs = kit / ".kit" / "designs"
    carousel = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))["picks"]["carousel"]
    rec_before = (kit / ".kit" / "kit.json").read_bytes()
    photos_before = sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (kit / "Photos").iterdir())
    case("browser: before the page is opened the shoot has no design", not designs.exists() or not list(designs.glob("*.json")))

    srv = Server(env, port)
    P = srv.start()
    scratch = work / "chrome"
    scratch.mkdir(parents=True, exist_ok=True)
    tokens = [0]
    try:
        with cd.Chrome(work=scratch, size=(1280, 900)) as c:
            base = [f"http://127.0.0.1:{P}"]

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return J("Designer.st")

            def ready(seconds=15):
                c.wait_for("window.Designer && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")

            def did():
                return c.js("Designer.design.id")

            def disk(i=None):
                return json.loads((designs / f"{i or did()}.json").read_text(encoding="utf-8"))

            def settled(seconds=10):
                """Wait until the page says everything is saved; True when the file on the drive is what is on the page."""
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                return disk()["state"] == st()

            def scale():
                return c.js("Designer.scale")

            def box(i):
                """Where block i is ON SCREEN, turned back into strip pixels."""
                s, sr, r = scale(), c.rect("#strip"), c.rect(f"#strip .blk[data-id='{i}']")
                return {"x": (r["x"] - sr["x"]) / s, "y": (r["y"] - sr["y"]) / s, "w": r["w"] / s, "h": r["h"] / s}

            def blk(state, i):
                return next((b for b in state["blocks"] if b["id"] == i), None)

            def close(a, b, tol=0.15):
                return all(abs(a[k] - b[k]) <= tol for k in ("x", "y", "w", "h"))

            def centre(i, fx=0.5, fy=0.5):
                r = c.rect(f"#strip .blk[data-id='{i}']")
                return (r["x"] + r["w"] * fx, r["y"] + r["h"] * fy)

            def handle(which):
                r = c.rect(f"#over .selbox .h.{which}")
                return (r["cx"], r["cy"])

            def tile(n):
                """The middle of a tray photo, with the page scrolled so it shows under the strip. CALL IT
                BEFORE measuring anything else for the same press: it may scroll the page."""
                c.js("(function(){ var t = document.querySelector(\"#thumbs .th[data-n='%d']\").getBoundingClientRect(); if (t.bottom > innerHeight - 6) window.scrollBy(0, t.bottom - innerHeight + 30); })()" % n)
                r = c.rect(f"#thumbs .th[data-n='{n}']")
                return (r["cx"], r["cy"])

            def press(a):
                c.click(f"#selbar button[data-a='{a}']")

            def fresh(label):
                """A NEW design of this shoot (one photo per slide), made by the Assistant, opened in the page."""
                tokens[0] += 1
                code, out = post(P, "/design-new", {"kit": kit_name, "token": f"browsercheck{tokens[0]:03d}"})
                if code != 200 or not out or not out.get("ok"):
                    case(f"browser [{label}]: a new design was made for this part", False, (code, out))
                    raise RuntimeError("no design")
                c.open(f"{base[0]}/design.html?kit={KQ}&design={out['design']['id']}")
                ready()
                c.wait_for("document.querySelectorAll('#strip .blk img').length >= 3 && Array.prototype.every.call(document.querySelectorAll('#strip .blk img'), function(i){ return i.naturalWidth > 0 || i.getBoundingClientRect().left > innerWidth; })", 15)
                return out["design"]["id"], st()

            # ================= the first visit =================
            c.open(f"{base[0]}/design.html?kit={KQ}")
            ready()
            c.wait_for("Array.prototype.filter.call(document.querySelectorAll('#strip .blk img'), function(i){ return i.naturalWidth > 0; }).length >= 3", 15)
            S0 = st()
            files = sorted(p.name for p in designs.glob("*.json")) if designs.exists() else []
            case("first visit: the Assistant made one design for the shoot, and the page opened it", len(files) == 1 and files[0] == did() + ".json", files)
            case("first visit: one photo per slide, in the carousel's order, each filling its slide",
                 S0["slides"] == len(carousel) and [b["n"] for b in S0["blocks"]] == carousel
                 and all(b["x"] == i * W and b["y"] == 0 and b["w"] == W and b["h"] == H for i, b in enumerate(S0["blocks"])), S0)
            case("first visit: the design's name shows, and the line beside it says Saved", c.text("#d-name") == "Fake beach carousel 1" and c.text("#d-status") == "Saved", (c.text("#d-name"), c.text("#d-status")))
            case("first visit: the shoot's name is the heading", c.text("#title") == "Fake beach", c.text("#title"))
            case("first visit: which design is open is in the address", c.js("location.search") == f"?kit={KQ}&design={did()}", c.js("location.search"))
            case("first visit: the strip has a frame per photo, a label per slide and a seam between slides",
                 c.count("#strip .blk") == 7 and c.count("#labels span") == 7 and c.count("#strip .seam") == 6 and c.text("#labels span", 2) == "Slide 3")
            case("first visit: every photo of the shoot is in the tray, numbered, the ones on the slides ticked",
                 c.count("#thumbs .th") == 14 and c.text("#thumbs .th[data-n='9'] .num") == "#9"
                 and sorted(J("Array.prototype.map.call(document.querySelectorAll('#thumbs .th.used'), function(t){ return +t.dataset.n; })")) == sorted(carousel)
                 and c.text("#trayname") == "All 14 photos")
            try:
                c.wait_for("document.querySelectorAll('#thumbs .th img').length === 14 && document.getElementById('prep').hidden", 30)
            except cd.Timeout:
                pass
            case("first visit: once the small copies are made every tray photo has its picture, and the 'Getting your photos ready' line is gone",
                 c.count("#thumbs .th img") == 14 and c.js("document.getElementById('prep').hidden") is True and c.count("#thumbs .th.cantread") == 0, c.text("#prep"))
            case("first visit: wide photos take two places in the tray", J("Array.prototype.map.call(document.querySelectorAll('#thumbs .th.wide'), function(t){ return +t.dataset.n; })") == [1, 10, 13])
            s = scale()
            sr, stg = c.rect("#strip"), c.rect("#stage")
            case("first visit: the strip is sized to the window (about three slides across, the whole of its height in sight)",
                 abs(s * W - 245) < 1.5 and stg["bottom"] <= 900 and sr["bottom"] <= 900 and abs(sr["w"] - 7 * W * s) < 1, (s * W, stg, sr))
            # the photo covers its frame, laid out from the picture's own size
            b1 = S0["blocks"][0]["id"]
            im = J(f"(function(){{ var i = document.querySelector(\"#strip .blk[data-id='{b1}'] img\"), r = i.getBoundingClientRect(), f = i.parentNode.getBoundingClientRect(); return {{nw: i.naturalWidth, nh: i.naturalHeight, w: r.width, h: r.height, dx: r.left - f.left, dy: r.top - f.top, fw: f.width, fh: f.height, src: i.getAttribute('src')}}; }})()")
            want_h = im["fw"] * im["nh"] / im["nw"]
            case("first visit: a tall photo in a whole slide is as wide as the slide, cut evenly top and bottom, worked out from the picture's own size",
                 im["nw"] > 0 and abs(im["w"] - im["fw"]) < 0.05 and abs(im["h"] - want_h) < 0.05 and abs(im["dx"]) < 0.05 and abs(im["dy"] - (im["fh"] - want_h) / 2) < 0.05, im)
            case("first visit: the photo is the copy the Assistant made (never the original), the small one while it is drawn small",
                 im["src"].startswith("/kit-photo?kit=") and "size=s" in im["src"] and f"&n={carousel[0]}&" in im["src"], im["src"])
            case("first visit: nothing selected: the buttons for a selected photo are greyed, and the help line says how to start",
                 c.js("document.getElementById('selbar').classList.contains('off')") and c.text("#selhint").startswith("Click a photo on the slides"), c.text("#selhint"))
            case("first visit: Undo is off (nothing to undo)", c.js("document.getElementById('undo').disabled") is True)
            case("first visit: the page has no errors and asked nothing of any address but its own", c.page_errors() == [] and c.outside_requests() == [], (c.page_errors(), c.outside_requests()))
            case("first visit: nothing is kept in the browser's own storage", c.js("localStorage.length + sessionStorage.length") == 0 and c.js("document.cookie") == "")

            # ================= select and deselect =================
            c.click(centre(b1))
            case("select: a press on a photo selects it (blue box, four corner handles, its buttons live, the help line names it)",
                 c.js("Designer.sel") == b1 and c.count("#over .selbox.on") == 1 and c.count("#over .selbox .h") == 4
                 and not c.js("document.getElementById('selbar').classList.contains('off')") and c.text("#selhint").startswith(f"Photo {carousel[0]}."), c.text("#selhint"))
            sb, bb = c.rect("#over .selbox"), c.rect(f"#strip .blk[data-id='{b1}']")
            case("select: the blue box sits exactly on the photo", all(abs(sb[k] - bb[k]) < 0.6 for k in ("x", "y", "w", "h")), (sb, bb))
            case("select: a plain press changed nothing and saved nothing", st() == S0 and c.js("Designer.save.idle()") and disk()["rev"] == 0)
            c.key("Escape")
            case("select: Escape deselects", c.js("Designer.sel") is None and c.count("#over .selbox.on") == 0)
            c.click(centre(b1))
            stg = c.rect("#stage")
            c.click((stg["x"] + 8, stg["y"] + 60))
            case("select: a press on the space around the strip deselects", c.js("Designer.sel") is None)

            # ================= move =================
            D1, A = fresh("move")
            ids = [b["id"] for b in A["blocks"]]
            a0 = ids[0]
            rev0 = disk()["rev"]
            x, y = centre(a0)
            c.drag((x, y), (x + 2, y + 1), steps=2, alt=True)
            case("move: a press that travels under 3 px is a click, not a move", st() == A and c.js("Designer.sel") == a0)
            c.drag((x, y), (x + 37, y + 22), steps=6, alt=True, release=False)
            mid = box(a0)
            case("move: while the button is held the photo follows the pointer on screen",
                 abs(mid["x"] - 37 / s) < 0.6 and abs(mid["y"] - 22 / s) < 0.6, mid)
            case("move: ...and the layout is not changed, nothing is saved, Undo is still off (only the dragged thing's own style moved)",
                 st() == A and c.js("Designer.save.idle()") and c.js("document.getElementById('undo').disabled") is True and disk()["rev"] == rev0)
            c.mouse_release()
            now = st()
            case("move: on letting go the layout has the new place, to two decimal places",
                 abs(blk(now, a0)["x"] - round(37 / s, 2)) < 0.011 and abs(blk(now, a0)["y"] - round(22 / s, 2)) < 0.011
                 and blk(now, a0)["w"] == W and [b for b in now["blocks"] if b["id"] != a0] == A["blocks"][1:], blk(now, a0))
            case("move: the numbers in the saved design file match the screen", settled() and close(box(a0), blk(disk()["state"], a0)), (box(a0), blk(disk()["state"], a0)))
            case("move: one save (the counter went up by one) and the version before is kept beside it",
                 disk()["rev"] == rev0 + 1 and json.loads((designs / f"{D1}.prev.json").read_text(encoding="utf-8"))["state"] == A, disk()["rev"])
            case("move: Undo is on now", c.js("document.getElementById('undo').disabled") is False)
            x, y = centre(a0)
            c.drag((x, y), (x + 60, y - 2000), steps=4, alt=True)
            case("move: dragged far off the top, 40 px of it stays on the strip", blk(st(), a0)["y"] == -1310 and settled(), blk(st(), a0))
            c.click("#undo")
            c.click("#undo")
            case("move: Undo twice puts it back where it began, on screen and on the drive", st() == A and settled() and close(box(a0), A["blocks"][0]), st()["blocks"][0])
            # Escape puts a drag back
            x, y = centre(a0)
            c.drag((x, y), (x + 50, y + 40), steps=4, alt=True, release=False)
            moved = box(a0)
            c.key("Escape")
            back = box(a0)
            c.mouse_release()
            case("move: Escape in the middle of a drag puts the photo back, and letting go afterwards does nothing",
                 abs(moved["x"] - 50 / s) < 0.6 and close(back, A["blocks"][0]) and st() == A and c.js("Designer.save.idle()"), (moved, back))
            case("move: no guide line is left behind", c.count("#over .guide") == 0)
            c.drag((x, y), (x + 50, y + 40), steps=4, alt=True, release=False)
            c.js("window.dispatchEvent(new Event('blur'))")
            back = box(a0)
            c.mouse_release()
            case("move: the window losing focus in the middle of a drag puts the photo back", close(back, A["blocks"][0]) and st() == A)
            c.drag((x, y), (x + 50, y + 40), steps=4, alt=True, release=False)
            c.js("document.dispatchEvent(new PointerEvent('pointercancel', {pointerId: 1, bubbles: true}))")
            back = box(a0)
            c.mouse_release()
            case("move: a cancelled pointer in the middle of a drag puts the photo back", close(back, A["blocks"][0]) and st() == A and c.js("Designer.save.idle()"))
            c.drag((x, y), (x + 50, y + 40), steps=4, alt=True, release=False)
            c.js("document.dispatchEvent(new PointerEvent('pointermove', {pointerId: 1, pointerType: 'mouse', buttons: 0, clientX: 5, clientY: 5, bubbles: true}))")
            back = box(a0)
            c.mouse_release()
            case("move: a mouse move with no button held (it was let go where the page never heard) puts the photo back", close(back, A["blocks"][0]) and st() == A)

            # ================= snap =================
            x, y = centre(a0)
            dx = 180 * s - 6            # six screen pixels short of a sixth of a slide
            c.drag((x, y), (x + dx, y), steps=5, release=False)
            g = c.count("#over .guide")
            mid = box(a0)
            c.mouse_release()
            case("snap: let go 6 px short of a sixth of a slide, it lands exactly on it (x 180), with a pink guide line while dragging",
                 blk(st(), a0)["x"] == 180 and blk(st(), a0)["y"] == 0 and g >= 1 and abs(mid["x"] - 180) < 0.2 and c.count("#over .guide") == 0, (blk(st(), a0), g, mid))
            c.click("#undo")
            x, y = centre(a0)
            c.drag((x, y), (x + dx, y), steps=5, alt=True, release=False)
            g = c.count("#over .guide")
            c.mouse_release()
            want = round(dx / s, 2)
            case("snap: with Alt held it stays where it was let go, and no guide line shows", abs(blk(st(), a0)["x"] - want) < 0.011 and blk(st(), a0)["x"] != 180 and g == 0, (blk(st(), a0)["x"], want))
            c.click("#undo")
            c.click("#snap")
            x, y = centre(a0)
            c.drag((x, y), (x + dx, y), steps=5)
            case("snap: with the Snap tick off it does not snap either", abs(blk(st(), a0)["x"] - want) < 0.011, blk(st(), a0)["x"])
            c.click("#undo")
            c.click("#snap")
            case("snap: the tick is on again, and the layout is back", c.js("document.getElementById('snap').checked") is True and st() == A and settled())

            # ================= resize =================
            c.click(centre(a0))
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 50, hy - 80), steps=5, alt=True, release=False)
            mid = box(a0)
            case("resize: while a corner is pulled the frame follows on screen and the layout waits", abs(mid["w"] - (W - 50 / s)) < 0.6 and abs(mid["h"] - (H - 80 / s)) < 0.6 and st() == A, mid)
            im = J(f"(function(){{ var i = document.querySelector(\"#strip .blk[data-id='{a0}'] img\"), r = i.getBoundingClientRect(), f = i.parentNode.getBoundingClientRect(); return {{l: r.left - f.left, t: r.top - f.top, r: r.right - f.right, b: r.bottom - f.bottom}}; }})()")
            case("resize: ...and the photo still covers the frame as it changes", im["l"] <= 0.01 and im["t"] <= 0.01 and im["r"] >= -0.01 and im["b"] >= -0.01, im)
            c.mouse_release()
            r1 = blk(st(), a0)
            case("resize: pulling the bottom-right corner in by 50 and up by 80 screen pixels makes it that much smaller; the top-left stays",
                 r1["x"] == 0 and r1["y"] == 0 and abs(r1["w"] - round(W - 50 / s, 2)) < 0.011 and abs(r1["h"] - round(H - 80 / s, 2)) < 0.011, r1)
            case("resize: the saved design file matches the screen", settled() and close(box(a0), blk(disk()["state"], a0)), (box(a0), blk(disk()["state"], a0)))
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 60, hy + 25), steps=5, shift=True)
            r2 = blk(st(), a0)
            case("resize with Shift: the frame keeps its shape", abs(r2["w"] / r2["h"] - r1["w"] / r1["h"]) < 0.0005 and abs(r2["w"] - (r1["w"] - 60 / s)) < 0.02, (r1, r2))
            hx, hy = handle("tl")
            c.drag((hx, hy), (hx + 30, hy + 20), steps=4, alt=True)
            r3 = blk(st(), a0)
            case("resize from the top-left corner: the bottom-right stays put",
                 abs((r3["x"] + r3["w"]) - (r2["x"] + r2["w"])) < 0.02 and abs((r3["y"] + r3["h"]) - (r2["y"] + r2["h"])) < 0.02 and abs(r3["x"] - 30 / s) < 0.02 and abs(r3["y"] - 20 / s) < 0.02, (r2, r3))
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 900, hy - 900), steps=4, alt=True)
            r4 = blk(st(), a0)
            case("resize: it never goes below 60 by 60", r4["w"] == 60 and r4["h"] == 60, r4)
            case("resize: saved, and the screen matches the file", settled() and close(box(a0), blk(disk()["state"], a0)))
            for _ in range(4):
                c.key("Mod+Z")
            case("resize: Cmd/Ctrl+Z four times puts the layout back", st() == A and settled())

            # ================= the one-click layouts =================
            c.click(centre(a0))
            press("span2")
            now = st()
            case("Across 2 slides: the photo fills slides 1 and 2", {k: blk(now, a0)[k] for k in "xywh"} == {"x": 0, "y": 0, "w": 2160, "h": 1350} and settled() and close(box(a0), blk(now, a0)))
            try:
                c.wait_for(f"(function(){{ var i = document.querySelector(\"#strip .blk[data-id='{a0}'] img\"); return i.getAttribute('src').indexOf('size=l') > 0 && i.naturalWidth > 520; }})()", 10)
                sharp = True
            except cd.Timeout:
                sharp = False
            im = J(f"(function(){{ var i = document.querySelector(\"#strip .blk[data-id='{a0}'] img\"), r = i.getBoundingClientRect(), f = i.parentNode.getBoundingClientRect(); return {{nw: i.naturalWidth, nh: i.naturalHeight, w: r.width, h: r.height, fw: f.width, n: +i.dataset.shown}}; }})()")
            case("Across 2 slides: drawn larger than 520 px now, so the sharper (1600) copy is used, and the layout is worked out from ITS size",
                 sharp and im["nw"] > 520 and abs(im["w"] - im["fw"]) < 0.05 and abs(im["h"] - im["fw"] * im["nh"] / im["nw"]) < 0.05, im)
            other = [c.js(f"document.querySelector(\"#strip .blk[data-id='{i}'] img\").getAttribute('src')") for i in ids[2:3]]
            case("...while a photo still drawn small keeps the small copy", all("size=s" in u for u in other), other)
            # it now lies under the photo of slide 2 (it is earlier in the list)
            under = J(f"(function(){{ var r = document.getElementById('strip').getBoundingClientRect(), s = Designer.scale, e = document.elementFromPoint(r.left + 1620 * s, r.top + 600 * s); e = e && e.closest('.blk'); return e ? +e.dataset.id : null; }})()")
            case("stacking: the wide photo lies under the photo of slide 2 (it comes earlier in the list)", under == ids[1], under)
            press("front")
            under = J(f"(function(){{ var r = document.getElementById('strip').getBoundingClientRect(), s = Designer.scale, e = document.elementFromPoint(r.left + 1620 * s, r.top + 600 * s); e = e && e.closest('.blk'); return e ? +e.dataset.id : null; }})()")
            case("Bring forward: it is on top now (last in the list), on screen and in the file",
                 under == a0 and [b["id"] for b in st()["blocks"]][-1] == a0 and settled() and [b["id"] for b in disk()["state"]["blocks"]][-1] == a0, under)
            for _ in range(3):
                press("back")
            z = c.js(f"getComputedStyle(document.querySelector(\"#strip .blk[data-id='{a0}']\")).zIndex")
            case("Send back three times: it is first in the list, and its place in the stack never goes below the strip", [b["id"] for b in st()["blocks"]][0] == a0 and int(z) >= 1, z)
            c.key("Escape")
            sr = c.rect("#strip")
            c.click((sr["x"] + 400 * s, sr["y"] + 600 * s))
            case("Send back three times: the photo can still be clicked (a press on slide 1 selects it)", c.js("Designer.sel") == a0)
            c.click((sr["x"] + 1620 * s, sr["y"] + 600 * s))
            case("...and a press on slide 2 selects the photo lying over it there", c.js("Designer.sel") == ids[1])
            case("the layouts so far are saved as they show", settled())

            # Top half + Bottom half on one slide
            t0 = ids[2]
            c.click(centre(t0))
            press("top")
            press("dup")
            t1 = c.js("Designer.sel")
            press("bottom")
            now = st()
            case("Top half, Duplicate, Bottom half: two photos share slide 3, one above the other",
                 {k: blk(now, t0)[k] for k in "xywh"} == {"x": 2160, "y": 0, "w": 1080, "h": 675}
                 and {k: blk(now, t1)[k] for k in "xywh"} == {"x": 2160, "y": 675, "w": 1080, "h": 675} and t1 != t0 and blk(now, t1)["n"] == blk(now, t0)["n"], (blk(now, t0), blk(now, t1)))
            case("...on screen as in the file", settled() and close(box(t0), blk(disk()["state"], t0)) and close(box(t1), blk(disk()["state"], t1)))
            press("left")
            l1 = {k: blk(st(), t1)[k] for k in "xywh"}
            press("right")
            l2 = {k: blk(st(), t1)[k] for k in "xywh"}
            press("full")
            l3 = {k: blk(st(), t1)[k] for k in "xywh"}
            press("margin")
            l4 = {k: blk(st(), t1)[k] for k in "xywh"}
            case("Left half, Right half, Fill slide, Add border, one after the other",
                 l1 == {"x": 2160, "y": 0, "w": 540, "h": 1350} and l2 == {"x": 2700, "y": 0, "w": 540, "h": 1350}
                 and l3 == {"x": 2160, "y": 0, "w": 1080, "h": 1350} and l4 == {"x": 2230, "y": 70, "w": 940, "h": 1210}, (l1, l2, l3, l4))
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 2000, hy - 2000), steps=3, alt=True)
            press("margin")
            case("Add border on a photo too small for one: nothing changes, and the line beside the buttons says why",
                 blk(st(), t1)["w"] == 60 and c.text("#selline") == "This photo is too small for a border.", c.text("#selline"))
            press("full")
            case("...and the line goes away with the next change", c.text("#selline") == "")
            c.drag(centre(t1), (centre(t1)[0] - 100, centre(t1)[1] + 30), steps=4, alt=True)
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 150, hy - 150), steps=3, alt=True)
            press("center")
            cx = blk(st(), t1)
            case("Center on slide: left and right only", abs(cx["x"] + cx["w"] / 2 - (2 * W + W / 2)) < 0.02, cx)
            case("all of it saved as it shows", settled() and close(box(t1), blk(disk()["state"], t1)))

            # ================= keys =================
            before = blk(st(), t1)
            c.key("ArrowRight")
            c.key("Shift+ArrowDown")
            c.key("ArrowLeft")
            c.key("Shift+ArrowUp")
            c.key("ArrowRight")
            after = blk(st(), t1)
            case("arrow keys: 5 a press, 50 with Shift", abs(after["x"] - (before["x"] + 5)) < 0.011 and abs(after["y"] - before["y"]) < 0.011 and settled(), (before, after))
            n_before = len(st()["blocks"])
            c.key("Delete")
            case("Delete removes the selected photo; nothing is selected after", len(st()["blocks"]) == n_before - 1 and blk(st(), t1) is None and c.js("Designer.sel") is None and c.count(f"#strip .blk[data-id='{t1}']") == 0)
            c.click(centre(t0))
            c.key("Backspace")
            case("Backspace too", blk(st(), t0) is None)
            c.click(centre(ids[3]))
            press("dup")
            d2 = c.js("Designer.sel")
            case("Duplicate: a copy 60 down and right, on top, selected", d2 not in ids and blk(st(), d2)["x"] == 3 * W + 60 and blk(st(), d2)["y"] == 60 and [b["id"] for b in st()["blocks"]][-1] == d2)
            press("del")
            case("Remove: gone", blk(st(), d2) is None and settled())
            # Undo all the way back to the start
            steps = 0
            while c.js("document.getElementById('undo').disabled") is False and steps < 80:
                c.click("#undo")
                steps += 1
            case(f"Undo, pressed until it goes grey ({steps} times), brings back the design exactly as it opened", st() == A and 20 <= steps <= 60, steps)
            case("...on the drive too, and on screen", settled() and disk()["state"] == A and all(close(box(i), blk(A, i)) for i in ids[:3]))

            # ================= move the photo inside, and zoom =================
            D2, A2 = fresh("inside")
            ids2 = [b["id"] for b in A2["blocks"]]
            p0 = ids2[0]
            c.click(centre(p0))
            press("adjust")
            case("Move photo inside: the button says Done moving, the box turns dashed with no handles, the help line says what to do",
                 c.js("Designer.adjust") is True and c.text("#adjust") == "Done moving" and c.count("#over .selbox.adj") == 1
                 and c.js("getComputedStyle(document.querySelector('#over .selbox .h')).display") == "none" and c.text("#selhint").startswith("Drag to move photo"), c.text("#selhint"))
            x, y = centre(p0)
            c.drag((x, y), (x + 30, y + 20), steps=5, release=False)
            live = J(f"(function(){{ var i = document.querySelector(\"#strip .blk[data-id='{p0}'] img\"), r = i.getBoundingClientRect(), f = i.parentNode.getBoundingClientRect(); return {{t: r.top - f.top, fh: f.height, h: r.height}}; }})()")
            case("move inside: the picture slides inside the frame as it is dragged (20 px down), the frame itself does not move, the layout waits",
                 abs(live["t"] - (-(live["h"] - live["fh"]) / 2 + 20)) < 0.6 and close(box(p0), A2["blocks"][0]) and st() == A2, live)
            c.mouse_release()
            pb = blk(st(), p0)
            slack = (live["h"] - live["fh"]) / s
            want_oy = round(0.5 - (20 / s) / slack, 4)
            case("move inside: on letting go only where the photo sits in its frame changed (a tall photo: up and down only)",
                 abs(pb["oy"] - want_oy) < 0.0002 and pb["ox"] == 0.5 and {k: pb[k] for k in "xywh"} == {"x": 0, "y": 0, "w": W, "h": H}, (pb, want_oy))
            case("move inside: the file matches", settled() and disk()["state"] == st())
            c.set_value("#zoom-img", "200")
            case("Zoom slider at 200: the photo is twice as large inside the same frame, saved", blk(st(), p0)["zoom"] == 2 and settled()
                 and abs(c.rect(f"#strip .blk[data-id='{p0}'] img")["w"] - 2 * c.rect(f"#strip .blk[data-id='{p0}']")["w"]) < 0.02)
            rev_z = disk()["rev"]
            c.wheel(centre(p0), -120)
            c.wheel(centre(p0), -120)
            z = blk(st(), p0)["zoom"]
            case("the wheel zooms while moving inside (two turns: 2 x 1.05 x 1.05)", abs(z - 2.205) < 0.002, z)
            c.click("#undo")
            case("...and a run of wheel turns is one Undo step (back to 2)", blk(st(), p0)["zoom"] == 2)
            c.double_click(centre(ids2[1]))
            case("double-click on another photo: that one is now being moved inside", c.js("Designer.sel") == ids2[1] and c.js("Designer.adjust") is True)
            c.double_click(centre(ids2[1]))
            case("double-click again: done moving", c.js("Designer.adjust") is False and c.text("#adjust") == "Move photo inside")
            c.double_click(centre(ids2[1]))
            c.click(centre(ids2[2]))
            case("a press on another photo ends moving inside", c.js("Designer.adjust") is False and c.js("Designer.sel") == ids2[2])
            case("the wheel does nothing to a photo that is not being moved inside", (c.wheel(centre(ids2[2]), -120), blk(st(), ids2[2])["zoom"])[1] == 1)
            case("saved as it shows", settled())

            # ================= the tray =================
            D3, A3 = fresh("tray")
            ids3 = [b["id"] for b in A3["blocks"]]
            f1 = ids3[0]
            c.click(centre(f1))
            press("adjust")
            x, y = centre(f1)
            c.drag((x, y), (x, y + 25), steps=3)
            c.set_value("#zoom-img", "150")
            c.key("Escape")
            case("tray: (a frame whose photo has been moved and zoomed inside)", blk(st(), f1)["zoom"] == 1.5 and blk(st(), f1)["oy"] != 0.5)
            free = [n for n in range(1, 15) if n not in carousel]
            n1 = free[0]
            tx, ty = tile(n1)
            fx, fy = centre(f1)
            before = st()
            c.drag((tx, ty), (fx, fy), steps=8, release=False)
            say = c.text(".d-lift .say")
            lift = c.rect(".d-lift")
            target = c.js(f"document.querySelector(\"#strip .blk[data-id='{f1}']\").classList.contains('droptarget')")
            case("tray drag: a copy of the photo is lifted and follows the pointer; over a frame it says what a drop will do, and that frame is outlined",
                 lift is not None and lift["x"] < fx < lift["right"] and say == "Put it in this frame" and target is True and st() == before, (say, target))
            c.mouse_release()
            fb = blk(st(), f1)
            case("tray drag onto a frame: that frame now holds the dragged photo, its crop back to the middle; nothing else moved",
                 fb["n"] == n1 and fb["ox"] == 0.5 and fb["oy"] == 0.5 and fb["zoom"] == 1 and {k: fb[k] for k in "xywh"} == {"x": 0, "y": 0, "w": W, "h": H}
                 and len(st()["blocks"]) == 7 and c.count(".d-lift") == 0 and c.count("#strip .droptarget") == 0, fb)
            case("tray drag: the picture on the slide is the new photo, and the tray's ticks follow",
                 f"&n={n1}&" in c.js(f"document.querySelector(\"#strip .blk[data-id='{f1}'] img\").getAttribute('src')")
                 and c.js(f"document.querySelector(\"#thumbs .th[data-n='{n1}']\").classList.contains('used')") is True
                 and c.js(f"document.querySelector(\"#thumbs .th[data-n='{carousel[0]}']\").classList.contains('used')") is False)
            case("tray drag: saved as it shows", settled())
            # an empty part of a slide
            c.click(centre(ids3[1]))
            press("del")
            n2 = free[1]
            tx, ty = tile(n2)
            s = scale()
            sr = c.rect("#strip")
            spot = (sr["x"] + 1620 * s, sr["y"] + 500 * s)
            c.drag((tx, ty), spot, steps=8, release=False)
            say = c.text(".d-lift .say")
            mark = c.rect("#over .slidemark")
            c.mouse_release()
            new = st()["blocks"][-1]
            case("tray drag onto an empty part of a slide: it says 'Add it to slide 2', marks that slide, and the photo is added filling it, on top, selected",
                 say == "Add it to slide 2" and mark and abs(mark["x"] - (sr["x"] + 1080 * s)) < 0.6 and abs(mark["w"] - 1080 * s) < 0.6
                 and new["n"] == n2 and {k: new[k] for k in "xywh"} == {"x": 1080, "y": 0, "w": W, "h": H} and c.js("Designer.sel") == new["id"]
                 and new["id"] not in ids3 and len(st()["blocks"]) == 7, (say, mark, new))
            case("tray drag onto a slide: saved as it shows", settled() and close(box(new["id"]), blk(disk()["state"], new["id"])))
            # let go away from the strip: nothing
            before = st()
            tx, ty = tile(free[2])
            c.drag((tx, ty), (tx + 200, ty + 20), steps=5)
            case("tray drag let go away from the slides: nothing happens", st() == before and c.count(".d-lift") == 0)
            # Escape mid-drag
            c.drag((tx, ty), centre(ids3[2]), steps=5, release=False)
            c.key("Escape")
            gone = c.count(".d-lift") == 0 and c.count("#strip .droptarget") == 0
            c.mouse_release()
            case("tray drag: Escape puts the lifted photo back and nothing changes", gone and st() == before)
            # clicks
            c.click(centre(ids3[2]))
            c.click(tile(free[3]))
            case("tray click with a frame selected: the clicked photo goes into that frame", blk(st(), ids3[2])["n"] == free[3] and c.js("Designer.sel") == ids3[2] and len(st()["blocks"]) == 7)
            press("empty")
            case("Take the photo out: an empty frame, drawn as a striped box that says Drop a photo",
                 blk(st(), ids3[2])["n"] is None and c.count(f"#strip .blk.hole[data-id='{ids3[2]}']") == 1
                 and c.text(f"#strip .blk[data-id='{ids3[2]}'] .drop") == "Drop a photo" and c.count(f"#strip .blk[data-id='{ids3[2]}'] img") == 0
                 and "repeating-linear-gradient" in c.js(f"getComputedStyle(document.querySelector(\"#strip .blk[data-id='{ids3[2]}']\")).backgroundImage")
                 and c.text("#selhint").startswith("An empty frame."), c.text("#selhint"))
            case("...and saved as an empty frame", settled() and blk(disk()["state"], ids3[2])["n"] is None)
            c.key("Escape")
            c.click(tile(free[4]))
            case("tray click with nothing selected: the clicked photo fills the next empty frame", blk(st(), ids3[2])["n"] == free[4] and len(st()["blocks"]) == 7 and c.count("#strip .blk.hole") == 0)
            c.key("Escape")
            c.click(tile(free[5]))
            last = st()["blocks"][-1]
            case("tray click with no empty frame and every slide full: a slide is added for it",
                 st()["slides"] == 8 and last["n"] == free[5] and last["x"] == 7 * W and c.count("#labels span") == 8, (st()["slides"], last))
            vis = c.rect(f"#strip .blk[data-id='{last['id']}']")
            stg = c.rect("#stage")
            case("...and the strip scrolls so the new slide shows", vis["x"] >= stg["x"] - 1 and vis["right"] <= stg["right"] + 1, (vis, stg))
            # a drop onto an empty frame
            c.click(centre(last["id"]))
            press("empty")
            c.key("Escape")
            c.drag(tile(free[0]), centre(last["id"]), steps=8)
            case("tray drag onto an empty frame fills it", blk(st(), last["id"])["n"] == free[0] and settled())
            c.js("document.getElementById('stage').scrollLeft = 0")

            # ================= slides, background, size =================
            D4, A4 = fresh("slides")
            ids4 = [b["id"] for b in A4["blocks"]]
            c.click("#slides-minus")
            case("Slides minus with a photo on the last slide: refused, with a plain line beside the buttons",
                 st() == A4 and c.text("#slides-count") == "7" and c.text("#slides-line") == "Slide 7 still has something on it. Move it or remove it first.", c.text("#slides-line"))
            c.click("#slides-plus")
            case("Slides plus: 8 slides, and the line is gone", st()["slides"] == 8 and c.text("#slides-count") == "8" and c.count("#labels span") == 8 and c.count("#strip .seam") == 7 and c.text("#slides-line") == "")
            case("...the strip is one slide longer, scrolled to show it", abs(c.rect("#strip")["w"] - 8 * W * s) < 1 and c.js("document.getElementById('stage').scrollLeft") > 0)
            c.click("#slides-minus")
            case("Slides minus with the last slide empty: back to 7", st()["slides"] == 7 and settled() and disk()["state"]["slides"] == 7)
            c.js("document.getElementById('stage').scrollLeft = 0")
            c.click("#g-bg .sw[data-c='#111111']")
            case("Background, Black: the strip and the file", st()["bg"] == "#111111" and c.js("getComputedStyle(document.getElementById('strip')).backgroundColor") == "rgb(17, 17, 17)"
                 and c.count("#g-bg .sw.on[data-c='#111111']") == 1 and settled() and disk()["state"]["bg"] == "#111111")
            c.set_value("#bgc", "#aabbcc")
            case("Background, any color from the color box", st()["bg"] == "#aabbcc" and c.count("#g-bg .sw.on") == 0 and settled() and disk()["state"]["bg"] == "#aabbcc")
            for _ in range(14):
                c.click("#slides-plus", check=False)
            case("Slides plus stops at 20 (Instagram's most), and its button goes grey and says why when pointed at",
                 st()["slides"] == 20 and c.js("document.getElementById('slides-plus').disabled") is True
                 and c.js("document.getElementById('slides-plus').title") == "Instagram allows up to 20 slides.", st()["slides"])
            for _ in range(13):
                c.click("#slides-minus")
            case("...and back down to 7, one press a slide (the added ones were empty)", st()["slides"] == 7 and settled())
            c.js("document.getElementById('stage').scrollLeft = 0")
            before, rev_b = st(), disk()["rev"]
            w0 = c.rect("#strip")["w"]
            c.click("#view-bigger")
            w1 = c.rect("#strip")["w"]
            c.click("#view-smaller")
            c.click("#view-smaller")
            w2 = c.rect("#strip")["w"]
            c.click("#view-bigger")
            case("Bigger and Smaller change how large the slides are drawn, and nothing else (no change to the design, nothing saved)",
                 abs(w1 / w0 - 1.25) < 0.01 and w2 < w0 and st() == before and c.js("Designer.save.idle()") and disk()["rev"] == rev_b, (w0, w1, w2))
            s = scale()
            for _ in range(12):
                c.click("#view-bigger", check=False)
            big = scale() * W
            case("Bigger stops at 480 px a slide and its button goes grey", abs(big - 480) < 0.5 and c.js("document.getElementById('view-bigger').disabled") is True, big)
            for _ in range(14):
                c.click("#view-smaller", check=False)
            small = scale() * W
            case("Smaller stops at 90 px a slide and its button goes grey", abs(small - 90) < 0.5 and c.js("document.getElementById('view-smaller').disabled") is True, small)
            case("...and at that size the whole carousel is in sight", c.rect("#strip")["right"] <= c.rect("#stage")["right"])

            # ================= a reload, and a restart on another port =================
            D5, A5 = fresh("reload")
            ids5 = [b["id"] for b in A5["blocks"]]
            c.click(centre(ids5[1]))
            press("top")
            c.drag(tile(1), centre(ids5[0]), steps=6)
            x, y = centre(ids5[2])
            c.drag((x, y), (x + 21, y + 13), steps=3, alt=True)
            case("reload: (a design with three changes, saved)", settled())
            want = st()
            c.reload()
            ready()
            case("reload: the same design opens (it is in the address) with the same layout", did() == D5 and st() == want and c.js("location.search").endswith("&design=" + D5), did())
            case("reload: Undo starts empty again", c.js("document.getElementById('undo').disabled") is True)
            # a change, and the page left at once: the browser delivers it
            c.wait_for(f"document.querySelector(\"#strip .blk[data-id='{ids5[3]}']\") !== null", 5)
            c.js("document.getElementById('stage').scrollLeft = 0")
            x, y = centre(ids5[2])
            c.drag((x, y), (x - 15, y + 9), steps=3, alt=True)
            leaving = st()
            c.open("about:blank")
            try:
                cd.wait_until(lambda: disk(D5)["state"] == leaving, 5, what="the change made just before leaving to reach the drive")
            except Exception:  # noqa: BLE001
                pass
            case("leaving the page straight after a change: the change is on the drive (sent as the page went)", disk(D5)["state"] == leaving)
            srv.stop()
            srv = Server(env, P + 2)
            P2 = srv.start()
            base[0] = f"http://127.0.0.1:{P2}"
            c.open(f"{base[0]}/design.html?kit={KQ}&design={D5}")
            ready()
            case(f"restart: a page server started afresh on another port ({P2}) shows the same layout", P2 != P and st() == leaving and did() == D5)
            c.click(centre(ids5[2]))
            c.key("ArrowDown")
            case("restart: and a change saves there as usual", settled() and disk()["rev"] > 0)
            P = P2

            # ================= changed somewhere else =================
            D6, A6 = fresh("elsewhere")
            ids6 = [b["id"] for b in A6["blocks"]]
            theirs = json.loads(json.dumps(A6))
            theirs["blocks"][3].update(x=3 * W + 100, y=100, w=500, h=500)
            code, out = post(P, "/design", {"kit": kit_name, "design": D6, "stamp": c.js("Designer.S.stamp"), "base": disk()["rev"], "page": "anotherwindow1", "state": theirs})
            case("changed elsewhere: (another window saved a change to this design)", code == 200 and out.get("ok"), (code, out))
            x, y = centre(ids6[0])
            c.drag((x, y), (x + 40, y + 40), steps=3, alt=True)
            try:
                c.wait_for("!document.getElementById('d-note').hidden", 8)
            except cd.Timeout:
                pass
            case("changed elsewhere: this page's next save is refused, the page shows the newest layout and says so",
                 c.text("#d-note span") == "This design was changed somewhere else. Here's the newest." and st() == disk()["state"]
                 and blk(st(), ids6[3])["w"] == 500 and blk(st(), ids6[0])["x"] == 0 and c.text("#d-status") == "Saved", (c.text("#d-note"), st()["blocks"][0]))
            case("changed elsewhere: Undo was emptied (its steps were for the older layout) and no Reload button is shown", c.js("document.getElementById('undo').disabled") is True and c.count("#d-note button") == 0)
            c.click(centre(ids6[1]))
            press("left")
            case("changed elsewhere: carrying on from the newest saves as usual, and the line goes away", settled() and blk(disk()["state"], ids6[1])["w"] == 540 and c.js("document.getElementById('d-note').hidden") is True)

            # ================= a text box among the photos (the text part's own checks are in design_text_check.py) =================
            tokens[0] += 1
            words = {"id": 2, "type": "text", "text": "Your title", "font": "Playfair Display", "size": 150, "weight": 700, "italic": True, "upper": True,
                     "al": "left", "ls": 8, "lh": 1.3, "color": "#2a2622", "x": 1170, "y": 260, "w": 900, "h": 195}
            code, out = post(P, "/design-new", {"kit": kit_name, "token": f"browsercheck{tokens[0]:03d}", "stamp": c.js("Designer.S.stamp"), "name": "With words",
                                                "state": {"slides": 3, "bg": "#f4efe6", "blocks": [{"id": 1, "n": 2, "x": 0, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}, words]}})
            if case("text box: (a design with a photo and a text box was made)", code == 200 and out and out.get("ok"), (code, out)):
                DT = out["design"]["id"]
                c.open(f"{base[0]}/design.html?kit={KQ}&design={DT}")
                ready()
                try:
                    # its font arrives from Google, or is given up on (no internet): either way its lines are then drawn
                    c.wait_for("Designer.type.status(Designer.st.blocks[1]) !== 'wait' && Designer.type.fit(Designer.st) === Designer.st && Designer.save.idle()", 25)
                except cd.Timeout:
                    pass
                T0 = st()
                shown = J("Array.prototype.map.call(document.querySelectorAll(\"#strip .blk.words[data-id='2'] .tx-ln\"), function(e){ return e.textContent; })")
                case("text box: it is drawn by the text part, as its own lines in capitals, where the design says (the stand-in is gone)",
                     c.count("#strip .blk.words[data-id='2']") == 1 and c.count("#strip .blk.other") == 0 and "".join(shown).replace(" ", "") == "YOURTITLE"
                     and close(box(2), blk(T0, 2)) and blk(T0, 2)["h"] == round(len(shown) * 150 * 1.3, 2), (shown, box(2), blk(T0, 2)))
                c.click(centre(2))
                case("text box: selected, it has handles, the text buttons and the buttons every thing has, and not the photo ones",
                     c.js("Designer.sel") == 2 and c.js("getComputedStyle(document.querySelector('#over .selbox .h')).display") != "none"
                     and c.js("document.getElementById('sel-photo').hidden && document.getElementById('sel-crop').hidden && !document.getElementById('sel-all').hidden && !document.getElementById('sel-text').hidden") is True
                     and c.text("#selhint").find("Text. Type in the box") >= 0, c.text("#selhint"))
                x, y = centre(2)
                c.drag((x, y), (x + 20, y + 30), steps=3, alt=True)
                c.wheel(centre(2), -120)
                tb = blk(st(), 2)
                same_but = dict(tb, x=words["x"], y=words["y"])
                case("text box: it can be moved, and every other thing about it is kept exactly (font, size, weight, slant, capitals, side, spacing, color, words)",
                     same_but == blk(T0, 2) and abs(tb["x"] - (1170 + round(20 / scale(), 2))) < 0.011 and abs(tb["y"] - (260 + round(30 / scale(), 2))) < 0.011 and c.js("Designer.adjust") is False, tb)
                case("text box: saved back to the drive with nothing lost", settled() and blk(disk()["state"], 2) == tb and blk(disk()["state"], 1) == T0["blocks"][0])
                press("back")
                press("dup")
                case("text box: Send back and Duplicate work on it", [b["id"] for b in st()["blocks"]][0] == 2 and st()["blocks"][-1]["text"] == "Your title" and settled())
                c.open(f"{base[0]}/design.html?kit={KQ}&design={D6}")
                ready()
                c.wait_for("document.querySelectorAll('#strip .blk img').length >= 3", 10)

            # ================= the Assistant not answering =================
            srv.stop()
            c.click(centre(ids6[2]))
            press("right")
            try:
                c.wait_for("document.getElementById('d-status').textContent === 'Not saved yet. Trying again...'", 8)
                said = True
            except cd.Timeout:
                said = False
            held = st()
            case("no answer from the Assistant: the line says 'Not saved yet. Trying again...', and the change stays on the page", said and blk(held, ids6[2])["w"] == 540, c.text("#d-status"))
            srv = Server(env, P)
            got = srv.start()
            if got == P:
                case("no answer: when the Assistant is back the change saves by itself", settled(15) and disk()["state"] == held)
            else:
                print(f"SKIP  the page server could not take port {P} again (it took {got}); the retry could not be watched", flush=True)

            # ================= nothing waits on a timer =================
            c.hold_timers()
            try:
                D7, A7 = None, None
                tokens[0] += 1
                code, out = post(srv.port, "/design-new", {"kit": kit_name, "token": f"browsercheck{tokens[0]:03d}"})
                D7 = out["design"]["id"]
                c.open(f"http://127.0.0.1:{srv.port}/design.html?kit={KQ}&design={D7}")
                c.wait_for("window.Designer && Designer.st && document.querySelectorAll('#strip .blk img').length >= 3", 15)
                A7 = st()
                ids7 = [b["id"] for b in A7["blocks"]]
                case("timers held: the page still opens and draws (its start waits on no timer)", len(A7["blocks"]) == 7 and c.count("#thumbs .th") == 14)
                s = scale()
                x, y = centre(ids7[0])
                c.drag((x, y), (x + 30, y + 30), steps=3, alt=True)
                press("dup")
                now = st()
                case("timers held: a button pressed straight after a drag is not lost (the move happened, then Duplicate copied the moved photo)",
                     len(now["blocks"]) == 8 and abs(blk(now, ids7[0])["x"] - round(30 / s, 2)) < 0.011 and abs(now["blocks"][-1]["x"] - (blk(now, ids7[0])["x"] + 60)) < 0.011, now["blocks"][-1])
                c.click("#undo")
                case("timers held: Undo pressed straight after that works at once", len(st()["blocks"]) == 7)
                c.key("Escape")
                c.drag(tile(1), centre(ids7[1]), steps=4)
                c.click(tile(3))
                now = st()
                case("timers held: a tray click straight after a tray drag is not lost",
                     blk(now, ids7[1])["n"] == 1 and now["slides"] == 8 and now["blocks"][-1]["n"] == 3, (blk(now, ids7[1]), now["slides"]))
                c.js("document.getElementById('stage').scrollLeft = 0")
                # the strip scrolls under a drag held near its end, moved by the pointer's own moves
                tx, ty = tile(5)
                stg = c.rect("#stage")
                c.drag((tx, ty), (stg["right"] - 12, stg["y"] + stg["h"] / 2), steps=4, release=False)
                time.sleep(0.4)
                for k in range(8):
                    c.mouse_move(stg["right"] - 12 - (k % 2), stg["y"] + stg["h"] / 2 + (k % 3))
                    time.sleep(0.03)
                scrolled = c.js("document.getElementById('stage').scrollLeft")
                c.key("Escape")
                c.mouse_release()
                case("timers held: a photo held near the right end of the strip scrolls it, with every move of the pointer", scrolled > 20, scrolled)
                case("timers held: nothing was saved yet (the save waits its 0.7 s), and the line says Saving...", c.text("#d-status") == "Saving..." and disk(D7)["rev"] == 0, c.text("#d-status"))
                c.run_timers()
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", 8)
                except cd.Timeout:
                    pass
                case("timers let run: everything done meanwhile is saved in one go", disk(D7)["state"] == st() and disk(D7)["rev"] == 1, disk(D7)["rev"])
            finally:
                c.free_timers()

            # ================= a phone's width =================
            c.phone(390, 844)
            try:
                c.open(f"http://127.0.0.1:{srv.port}/design.html?kit={KQ}&design={D6}")
                ready()
                c.wait_for("document.querySelectorAll('#strip .blk img').length >= 2", 10)
                wide = J("({inner: innerWidth, doc: document.documentElement.scrollWidth, body: document.body.scrollWidth})")
                case("phone width (390): the page does not scroll sideways (the strip scrolls inside its own box)", wide["inner"] == 390 and wide["doc"] <= 390 and wide["body"] <= 390, wide)
                case("phone width: the strip's box is narrower than the strip and scrolls by itself", c.js("(function(){ var s = document.getElementById('stage'); return s.scrollWidth > s.clientWidth + 50 && s.clientWidth <= 390; })()"))
                n_before = len(st()["blocks"])
                c.tap(tile(2))
                case("phone width: a finger's tap on a tray photo adds it (a finger never lifts one: it scrolls the page)",
                     len(st()["blocks"]) == n_before + 1 and st()["blocks"][-1]["n"] == 2, st()["blocks"][-1])
                c.wait_for("Designer.save.idle()", 8)
            finally:
                c.desktop()

            # ================= the whole run =================
            case("the page threw no error and logged none, in the whole run", c.page_errors() == [], c.page_errors()[:4])
            # (a text box's font is asked of Google Fonts, by a stylesheet link: the one thing this page may load from outside)
            outside = [u for u in c.outside_requests() if not u.startswith(("https://fonts.googleapis.com/css2?family=", "https://fonts.gstatic.com/"))]
            case("the page made no request to any address but its own and Google Fonts (for a text box's font), in the whole run", outside == [], outside[:4])
            asked = sorted(set(re.sub(r"\?.*", "", re.sub(r"^https?://[^/]+", "", r["url"])) for r in c.requests if "127.0.0.1" in r["url"]))
            case("every request it made was for the page, its state, a made copy of a photo, or a save", set(asked) <= {"/design.html", "/design-state", "/kit-photo", "/design", "/design-font-file", "/favicon.ico"}, asked)
            case("the Finder was never asked for (/open was not requested)", not any("/open" in r["url"] for r in c.requests))
    finally:
        srv.stop()
    case("browser: the kit's own record was not written by any of it", (kit / ".kit" / "kit.json").read_bytes() == rec_before)
    case("browser: no photo was changed", sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (kit / "Photos").iterdir()) == photos_before)
    case("browser: nothing was put in the Carousel folder", not (kit / "Carousel").exists() or not list((kit / "Carousel").iterdir()))
    log = (studio / "arrange.log").read_text(encoding="utf-8", errors="replace") if (studio / "arrange.log").is_file() else ""
    case("browser: the server never fell over (no Python error, no failed route in its log)", "Traceback" not in log and " failed: " not in log, [ln for ln in log.splitlines() if " failed: " in ln or "Traceback" in ln][:3])
