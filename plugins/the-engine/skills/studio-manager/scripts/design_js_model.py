#!/usr/bin/env python3
"""The carousel designer's rules, as one script with no page in it (design_page.py puts it on the page).

DESIGN_MODEL_JS makes window.DesignModel: where a photo sits inside its frame, what a move, a resize or a
nudge may do, snapping, the one-click layouts, which slide a thing is on, adding and swapping photos, the
undo list, which made copy of a photo to draw from. Every function takes a layout and returns a new one (or
the very same one when nothing changes) and touches no document, so tests/design_check.py runs it by itself
under the Mac's own JavaScript engine.

A layout is {slides, bg, blocks}. Strip pixels: slide k spans x = k*1080 to (k+1)*1080, height 1350.
A frame is {id, n | null, x, y, w, h, ox, oy, zoom}; a text box has type "text". STACKING IS LIST ORDER:
the last block is on top. There is no z.
"""

DESIGN_MODEL_JS = r"""
(function(root){
  'use strict';
  var W = 1080, H = 1350;
  // Every number the designer goes by, in one place. The Assistant sends its own limits with the state
  // (useLimits); these are the same numbers, here so the rules can run with no page.
  var RULES = {
    slides: [2, 20],        // fewest and most slides
    frameMin: 60,           // a frame is never smaller than this, either way
    onStrip: 40,            // at least this much of anything stays on the strip
    zoom: [1, 3],           // a photo inside its frame
    blocks: 80,             // photos and text boxes in one design
    idMax: 1000000,
    inset: 70,              // "Add border" pulls each edge in by this much
    dup: 60,                // a duplicate sits this far down and right of its original
    snapPx: 10,             // snapping reaches this many SCREEN pixels
    nudge: 5, nudgeBig: 50, // an arrow key, and with Shift
    undo: 60,               // steps of Undo kept
    wheel: 1.05,            // one turn of the wheel zooms by this much
    view: {min: 90, max: 480, step: 1.25}     // how wide one slide may be drawn on screen, and one press of Smaller / Bigger
  };
  function useLimits(l){
    if (!l) return;
    if (l.slides && l.slides.length === 2) RULES.slides = [l.slides[0], l.slides[1]];
    if (l.frame_min > 0) RULES.frameMin = l.frame_min;
    if (l.on_strip > 0) RULES.onStrip = l.on_strip;
    if (l.zoom && l.zoom.length === 2) RULES.zoom = [l.zoom[0], l.zoom[1]];
    if (l.blocks > 0) RULES.blocks = l.blocks;
  }

  function clamp(v, a, b){ return Math.max(a, Math.min(b, v)); }
  function r2(v){ return Math.round(v * 100) / 100; }
  function r3(v){ return Math.round(v * 1000) / 1000; }
  function r4(v){ return Math.round(v * 10000) / 10000; }
  function isText(b){ return !!b && b.type === 'text'; }
  function isFrame(b){ return !!b && b.type !== 'text'; }
  function isHole(b){ return isFrame(b) && b.n == null; }        // an empty frame: "Drop a photo"
  function typeOf(b){ return isText(b) ? 'text' : 'photo'; }
  function same(a, b){ return a === b || JSON.stringify(a) === JSON.stringify(b); }
  function copy(v){ return JSON.parse(JSON.stringify(v)); }
  function indexOf(st, id){ for (var i = 0; i < st.blocks.length; i++) { if (st.blocks[i].id === id) return i; } return -1; }
  function find(st, id){ var i = indexOf(st, id); return i < 0 ? null : st.blocks[i]; }
  function merge(a, b){ var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
  function withBlocks(st, blocks, more){ var o = merge(st, more || {}); o.blocks = blocks; return o; }
  // A layout as it arrives from the Assistant, made safe to work on: its own copy, every frame with its crop.
  function tidy(state){
    var st = copy(state || {});
    if (!(st.slides >= 1)) st.slides = RULES.slides[0];
    if (typeof st.bg !== 'string') st.bg = '#ffffff';
    if (!Array.isArray(st.blocks)) st.blocks = [];
    st.blocks.forEach(function(b){
      if (isFrame(b)) { if (typeof b.ox !== 'number') b.ox = 0.5; if (typeof b.oy !== 'number') b.oy = 0.5; if (!(b.zoom >= 1)) b.zoom = 1; if (b.n === undefined) b.n = null; }
    });
    return st;
  }
  // One block changed (a new layout; the same one when nothing is different).
  function patch(st, id, p){
    var i = indexOf(st, id);
    if (i < 0 || !p) return st;
    var nb = merge(st.blocks[i], p);
    if (same(nb, st.blocks[i])) return st;
    var blocks = st.blocks.slice();
    blocks[i] = nb;
    return withBlocks(st, blocks);
  }
  function nextId(st){
    var top = 0, used = {}, i;
    for (i = 0; i < st.blocks.length; i++) { used[st.blocks[i].id] = true; if (st.blocks[i].id > top) top = st.blocks[i].id; }
    if (top + 1 <= RULES.idMax) return top + 1;
    for (i = 1; i <= RULES.idMax; i++) { if (!used[i]) return i; }
    return 1;
  }

  // ---- a photo inside its frame: it always covers the frame. pw, ph are the LOADED picture's own size. ----
  function layoutImg(b, pw, ph){
    var zoom = b.zoom >= 1 ? b.zoom : 1, ox = typeof b.ox === 'number' ? b.ox : 0.5, oy = typeof b.oy === 'number' ? b.oy : 0.5;
    if (!(pw > 0 && ph > 0)) { pw = 1; ph = 1; }
    var c = Math.max(b.w / pw, b.h / ph) * zoom, iw = pw * c, ih = ph * c;
    return {iw: iw, ih: ih, left: (b.w - iw) * ox, top: (b.h - ih) * oy};
  }
  // Dragging the photo inside its frame by dx, dy strip pixels.
  function pan(b0, dx, dy, pw, ph){
    var L = layoutImg(b0, pw, ph);
    var ox = typeof b0.ox === 'number' ? b0.ox : 0.5, oy = typeof b0.oy === 'number' ? b0.oy : 0.5;
    if (L.iw > b0.w + 1) ox = clamp(ox - dx / (L.iw - b0.w), 0, 1);
    if (L.ih > b0.h + 1) oy = clamp(oy - dy / (L.ih - b0.h), 0, 1);
    return {ox: r4(ox), oy: r4(oy)};
  }
  function zoomTo(v){ return r3(clamp(Number(v) || 1, RULES.zoom[0], RULES.zoom[1])); }
  function zoomBy(zoom, deltaY){ return zoomTo((zoom >= 1 ? zoom : 1) * (deltaY < 0 ? RULES.wheel : 1 / RULES.wheel)); }

  // ---- where things may be ----
  function slideOf(b, slides){ return clamp(Math.floor((b.x + b.w / 2) / W), 0, slides - 1); }
  function clampXY(x, y, w, h, slides){
    var S = RULES.onStrip;
    return {x: clamp(x, S - w, slides * W - S), y: clamp(y, S - h, H - S)};
  }
  function onStrip(b, slides){
    var S = RULES.onStrip;
    return b.x + b.w >= S && b.x <= slides * W - S && b.y + b.h >= S && b.y <= H - S;
  }

  // ---- snapping: to sixths of a slide, and to the edges of everything else ----
  function lines(st, axis, skipId){
    var out = [], k;
    if (axis === 'x') { for (k = 0; k <= st.slides * 6; k++) out.push(k * W / 6); }
    else { for (k = 0; k <= 6; k++) out.push(k * H / 6); }
    st.blocks.forEach(function(b){
      if (b.id === skipId) return;
      if (axis === 'x') out.push(b.x, b.x + b.w); else out.push(b.y, b.y + b.h);
    });
    return out;
  }
  // How far v is from the nearest line within reach (a signed distance), or null.
  function nearest(v, ls, thr){
    var best = null;
    for (var i = 0; i < ls.length; i++) { var d = ls[i] - v; if (Math.abs(d) <= thr && (best === null || Math.abs(d) < Math.abs(best))) best = d; }
    return best;
  }
  // o: {snap: true | false, thr: reach in strip pixels}
  function move(st, b0, dx, dy, o){
    o = o || {};
    var x = b0.x + dx, y = b0.y + dy, gx = [], gy = [];
    if (o.snap) {
      var lx = lines(st, 'x', b0.id), ly = lines(st, 'y', b0.id);
      var a1 = nearest(x, lx, o.thr), a2 = nearest(x + b0.w, lx, o.thr);
      var ax = a1 === null ? a2 : a2 === null ? a1 : (Math.abs(a1) <= Math.abs(a2) ? a1 : a2);
      if (ax !== null) { x += ax; gx.push(ax === a1 ? x : x + b0.w); }
      var b1 = nearest(y, ly, o.thr), b2 = nearest(y + b0.h, ly, o.thr);
      var ay = b1 === null ? b2 : b2 === null ? b1 : (Math.abs(b1) <= Math.abs(b2) ? b1 : b2);
      if (ay !== null) { y += ay; gy.push(ay === b1 ? y : y + b0.h); }
    }
    var c = clampXY(x, y, b0.w, b0.h, st.slides);
    if (c.x !== x) gx = [];             // a guide line only shows where the thing really sits
    if (c.y !== y) gy = [];
    return {x: r2(c.x), y: r2(c.y), gx: gx, gy: gy};
  }
  // Pulling a corner ('tl', 'tr', 'bl', 'br') by dx, dy. o: {snap, thr, shift: keep the shape, minW, minH,
  // maxH, widthOnly: a text box (only its width changes; its height follows its lines)}.
  function resize(st, b0, corner, dx, dy, o){
    o = o || {};
    var minW = o.minW || RULES.frameMin, minH = o.minH || RULES.frameMin, maxW = st.slides * W, maxH = o.maxH || H, S = RULES.onStrip;
    var left = corner.indexOf('l') >= 0, top = corner.indexOf('t') >= 0, tall = !o.widthOnly;
    var L = b0.x, T = b0.y, R = b0.x + b0.w, B = b0.y + b0.h, gx = [], gy = [], d;
    if (o.shift && tall) {
      // the shape is kept: one number, how much bigger or smaller, held inside every limit at once
      var f = (left ? R - (L + dx) : (R + dx) - L) / b0.w;
      var lo = Math.max(minW / b0.w, minH / b0.h), hi = Math.min(maxW / b0.w, maxH / b0.h);
      lo = Math.max(lo, left ? (R - (maxW - S)) / b0.w : (S - L) / b0.w);
      lo = Math.max(lo, top ? (B - (H - S)) / b0.h : (S - T) / b0.h);
      f = lo > hi ? 1 : clamp(f, lo, hi);
      if (left) L = R - b0.w * f; else R = L + b0.w * f;
      if (top) T = B - b0.h * f; else B = T + b0.h * f;
    } else {
      if (left) L += dx; else R += dx;
      if (tall) { if (top) T += dy; else B += dy; }
      if (o.snap) {
        var lx = lines(st, 'x', b0.id), ly = lines(st, 'y', b0.id);
        if (left) { d = nearest(L, lx, o.thr); if (d !== null) { L += d; gx.push(L); } }
        else { d = nearest(R, lx, o.thr); if (d !== null) { R += d; gx.push(R); } }
        if (tall) {
          if (top) { d = nearest(T, ly, o.thr); if (d !== null) { T += d; gy.push(T); } }
          else { d = nearest(B, ly, o.thr); if (d !== null) { B += d; gy.push(B); } }
        }
      }
      var was;
      if (left) { was = L; L = clamp(L, R - maxW, Math.min(R - minW, maxW - S)); if (L !== was) gx = []; }
      else { was = R; R = clamp(R, Math.max(L + minW, S), L + maxW); if (R !== was) gx = []; }
      if (tall) {
        if (top) { was = T; T = clamp(T, B - maxH, Math.min(B - minH, H - S)); if (T !== was) gy = []; }
        else { was = B; B = clamp(B, Math.max(T + minH, S), T + maxH); if (B !== was) gy = []; }
      }
    }
    return {x: r2(L), y: r2(T), w: r2(R - L), h: r2(B - T), gx: gx, gy: gy};
  }
  function nudge(st, id, dx, dy){
    var b = find(st, id);
    if (!b) return st;
    var c = clampXY(b.x + dx, b.y + dy, b.w, b.h, st.slides);
    return patch(st, id, {x: r2(c.x), y: r2(c.y)});
  }

  // ---- the one-click buttons. Returns {st, sel?, why?}: st is the same layout when nothing changed;
  //      sel is given only when the selection should change; why says what stopped it. ----
  var FRAME_ONLY = {full: 1, span2: 1, top: 1, bottom: 1, left: 1, right: 1, margin: 1, empty: 1};
  function act(st, id, a){
    var i = indexOf(st, id);
    if (i < 0) return {st: st};
    var b = st.blocks[i];
    if (FRAME_ONLY[a] && !isFrame(b)) return {st: st};
    var si = slideOf(b, st.slides), x0 = si * W, m = RULES.inset, blocks, c;
    if (a === 'full') return {st: patch(st, id, {x: x0, y: 0, w: W, h: H})};
    if (a === 'span2') { var s0 = si + 1 < st.slides ? si : si - 1; return {st: patch(st, id, {x: s0 * W, y: 0, w: 2 * W, h: H})}; }
    if (a === 'top') return {st: patch(st, id, {x: x0, y: 0, w: W, h: H / 2})};
    if (a === 'bottom') return {st: patch(st, id, {x: x0, y: H / 2, w: W, h: H / 2})};
    if (a === 'left') return {st: patch(st, id, {x: x0, y: 0, w: W / 2, h: H})};
    if (a === 'right') return {st: patch(st, id, {x: x0 + W / 2, y: 0, w: W / 2, h: H})};
    if (a === 'margin') {
      if (!(b.w > 2 * m + RULES.frameMin && b.h > 2 * m + RULES.frameMin)) return {st: st, why: 'small'};
      c = clampXY(b.x + m, b.y + m, b.w - 2 * m, b.h - 2 * m, st.slides);      // a frame hanging off an edge stays on the strip
      return {st: patch(st, id, {x: r2(c.x), y: r2(c.y), w: r2(b.w - 2 * m), h: r2(b.h - 2 * m)})};
    }
    if (a === 'empty') return {st: patch(st, id, {n: null, ox: 0.5, oy: 0.5, zoom: 1})};
    if (a === 'center') { c = clampXY(x0 + (W - b.w) / 2, b.y, b.w, b.h, st.slides); return {st: patch(st, id, {x: r2(c.x)})}; }
    if (a === 'front' || a === 'back') {
      if ((a === 'front' && i === st.blocks.length - 1) || (a === 'back' && i === 0)) return {st: st};
      blocks = st.blocks.slice();
      blocks.splice(i, 1);
      if (a === 'front') blocks.push(b); else blocks.unshift(b);
      return {st: withBlocks(st, blocks)};
    }
    if (a === 'dup') {
      if (st.blocks.length >= RULES.blocks) return {st: st, why: 'many'};
      c = clampXY(b.x + RULES.dup, b.y + RULES.dup, b.w, b.h, st.slides);
      var nb = merge(b, {id: nextId(st), x: r2(c.x), y: r2(c.y)});
      delete nb.slot;
      return {st: withBlocks(st, st.blocks.concat([nb])), sel: nb.id};
    }
    if (a === 'del') {
      blocks = st.blocks.slice();
      blocks.splice(i, 1);
      return {st: withBlocks(st, blocks), sel: null};
    }
    return {st: st};
  }

  // ---- slides ----
  // What sits on a slide, even partly (and, for the last slide, anything hanging off the end of the strip).
  function onSlide(st, k){
    return st.blocks.filter(function(b){ return b.x + b.w > k * W + 0.5 && (b.x < (k + 1) * W - 0.5 || k === st.slides - 1); });
  }
  function fewerSlides(st){
    if (st.slides <= RULES.slides[0]) return {st: st, why: 'min'};
    if (onSlide(st, st.slides - 1).length) return {st: st, why: 'last', slide: st.slides};
    var left = (st.slides - 1) * W;
    for (var i = 0; i < st.blocks.length; i++) { if (st.blocks[i].w > left) return {st: st, why: 'wide'}; }
    return {st: merge(st, {slides: st.slides - 1})};
  }
  function moreSlides(st){
    if (st.slides >= RULES.slides[1]) return {st: st, why: 'max'};
    return {st: merge(st, {slides: st.slides + 1})};
  }
  function setBg(st, color){
    color = String(color || '').toLowerCase();
    if (!/^#[0-9a-f]{6}$/.test(color) || color === st.bg) return st;
    return merge(st, {bg: color});
  }

  // ---- photos from the tray ----
  function used(st){
    var out = {};
    st.blocks.forEach(function(b){ if (isFrame(b) && b.n != null) out[b.n] = (out[b.n] || 0) + 1; });
    return out;
  }
  // The first slide whose middle no photo covers, or -1.
  function firstEmptySlide(st){
    for (var k = 0; k < st.slides; k++) {
      var cx = (k + 0.5) * W, cy = H / 2, hit = false;
      for (var i = 0; i < st.blocks.length; i++) {
        var b = st.blocks[i];
        if (isFrame(b) && cx > b.x && cx < b.x + b.w && cy > b.y && cy < b.y + b.h) { hit = true; break; }
      }
      if (!hit) return k;
    }
    return -1;
  }
  // The empty frame to fill next: by its slot, then left to right, then top to bottom.
  function nextHole(st){
    var holes = st.blocks.filter(isHole);
    holes.sort(function(a, b){ return (a.slot || 0) - (b.slot || 0) || a.x - b.x || a.y - b.y || a.id - b.id; });
    return holes.length ? holes[0] : null;
  }
  function swapPhoto(st, id, n){
    var b = find(st, id);
    if (!isFrame(b)) return st;
    return patch(st, id, {n: n, ox: 0.5, oy: 0.5, zoom: 1});
  }
  // Add photo n. at = a slide (dropped there): a new frame filling that slide, on top. at = null (clicked):
  // the next empty frame, else the first empty slide, else one more slide. {st, sel} or {st, why: 'full' | 'many'}.
  function addPhoto(st, n, at){
    if (at == null) {
      var hole = nextHole(st);
      if (hole) return {st: swapPhoto(st, hole.id, n), sel: hole.id};
    }
    var slides = st.slides, si = at != null ? clamp(Math.floor(at), 0, slides - 1) : firstEmptySlide(st);
    if (si < 0) {
      if (slides >= RULES.slides[1]) return {st: st, why: 'full'};
      si = slides; slides += 1;
    }
    if (st.blocks.length >= RULES.blocks) return {st: st, why: 'many'};
    var b = {id: nextId(st), n: n, x: si * W, y: 0, w: W, h: H, ox: 0.5, oy: 0.5, zoom: 1};
    return {st: withBlocks(st, st.blocks.concat([b]), {slides: slides}), sel: b.id};
  }
  // A click on a tray photo: it goes into the selected frame, or else is added.
  function clickPhoto(st, sel, n){
    var b = sel != null ? find(st, sel) : null;
    if (isFrame(b)) return {st: swapPhoto(st, b.id, n), sel: b.id};
    return addPhoto(st, n, null);
  }
  // What a photo let go at strip point x, y lands on: the topmost frame there, else the slide. Off the strip: null.
  function dropAt(st, x, y){
    if (!(x >= 0 && y >= 0 && x < st.slides * W && y <= H)) return null;
    for (var i = st.blocks.length - 1; i >= 0; i--) {
      var b = st.blocks[i];
      if (isFrame(b) && x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) return {kind: 'frame', id: b.id};
    }
    return {kind: 'slide', i: clamp(Math.floor(x / W), 0, st.slides - 1)};
  }

  // ---- which made copy of a photo to draw from ----
  // need = the photo's drawn long edge in pixels; photoLong = the photo's own long edge. The first of s, l, x,
  // xx that is at least as large as it will be drawn, or as large as the photo itself; none: xx.
  var ORDER = ['s', 'l', 'x', 'xx'];
  function pickSize(need, photoLong, sizes){
    for (var i = 0; i < ORDER.length; i++) {
      var v = sizes ? sizes[ORDER[i]] : 0;
      if (!(v > 0)) continue;
      if (v >= need || (photoLong > 0 && v >= photoLong)) return ORDER[i];
    }
    return 'xx';
  }
  // On screen only the two copies made ahead are used: the small one until a photo is drawn larger than it.
  function screenCopy(need, photoLong, sizes){ return pickSize(need, photoLong, sizes) === 's' ? 's' : 'l'; }

  // ---- Undo: the layouts before each change, newest last. A run of changes given the same key (a held
  //      arrow key, turns of the wheel) is one step. ----
  function history(max){
    var list = [], lastKey = null;
    max = max || RULES.undo;
    return {
      push: function(snap, key){
        if (key && key === lastKey && list.length) return false;
        list.push(snap);
        if (list.length > max) list.shift();
        lastKey = key || null;
        return true;
      },
      pop: function(){ lastKey = null; return list.length ? list.pop() : null; },
      mark: function(){ lastKey = null; },
      size: function(){ return list.length; },
      clear: function(){ list = []; lastKey = null; }
    };
  }

  // ---- how wide one slide is drawn ----
  // To start with: about three slides across the space there is, and no taller than about a third of the window
  // (the bars of buttons sit above the strip and the photos below it).
  function viewStart(avail, winH){
    var w = Math.min(avail / 3.2, (winH * 0.34) * W / H);
    return clamp(Math.round(w) || 0, RULES.view.min, RULES.view.max);
  }
  function viewStep(cur, dir){
    return clamp(Math.round(dir > 0 ? cur * RULES.view.step : cur / RULES.view.step), RULES.view.min, RULES.view.max);
  }

  root.DesignModel = {
    W: W, H: H, RULES: RULES, useLimits: useLimits,
    clamp: clamp, r2: r2, isText: isText, isFrame: isFrame, isHole: isHole, typeOf: typeOf, same: same, copy: copy,
    indexOf: indexOf, find: find, merge: merge, tidy: tidy, patch: patch, nextId: nextId,
    layoutImg: layoutImg, pan: pan, zoomTo: zoomTo, zoomBy: zoomBy,
    slideOf: slideOf, clampXY: clampXY, onStrip: onStrip,
    lines: lines, nearest: nearest, move: move, resize: resize, nudge: nudge,
    act: act, onSlide: onSlide, fewerSlides: fewerSlides, moreSlides: moreSlides, setBg: setBg,
    used: used, firstEmptySlide: firstEmptySlide, nextHole: nextHole, swapPhoto: swapPhoto, addPhoto: addPhoto,
    clickPhoto: clickPhoto, dropAt: dropAt, pickSize: pickSize, screenCopy: screenCopy,
    history: history, viewStart: viewStart, viewStep: viewStep
  };
})(typeof window !== 'undefined' ? window : this);
"""
