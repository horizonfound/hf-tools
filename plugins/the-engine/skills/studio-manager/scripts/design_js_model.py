#!/usr/bin/env python3
"""The carousel designer's rules, as one script with no page in it (design_page.py puts it on the page).

DESIGN_MODEL_JS makes window.DesignModel: where a photo sits inside its frame, what a move, a resize or a
nudge may do, snapping (edges, and the centers: M.move's mid, M.centered, M.midWords), the one-click layouts (Show the whole photo among them: act 'whole', given the photo's own size), the Crop window's box and what Done makes of it (cropFromBlock, cropResize, cropApply), which slide a thing is on, adding and swapping photos, the
undo list, slides as things (insert, remove, the pieces a strip comes in and moving one), several things at once (evenOut, sameSize, lineTops, removeMany, moveMany), which made copy of a photo to draw from. Every function takes a layout and returns a new one (or
the very same one when nothing changes) and touches no document, so tests/design_check.py runs it by itself
under the Mac's own JavaScript engine.

A layout is {slides, bg, blocks}. Strip pixels: slide k spans x = k*1080 to (k+1)*1080, height 1350 (a story,
in the stories designer: 1080 by 1920). The size comes from window.DESIGN_LIMITS, which design_page.py writes into
the page from design.limits_for before any script runs; with none (the tests' own engine) it is a carousel's.
A frame is {id, n | null, x, y, w, h, ox, oy, zoom}; a text box has type "text". STACKING IS LIST ORDER:
the last block is on top. There is no z.
"""

DESIGN_MODEL_JS = r"""
(function(root){
  'use strict';
  var L0 = root && root.DESIGN_LIMITS ? root.DESIGN_LIMITS : null;
  var W = L0 && L0.w > 0 ? L0.w : 1080, H = L0 && L0.h > 0 ? L0.h : 1350;
  var KIND = L0 && L0.kind === 'stories' ? 'stories' : 'carousel';
  // Every number the designer goes by, in one place. The Assistant sends its own limits with the state
  // (useLimits); these are the same numbers, here so the rules can run with no page.
  var RULES = {
    slides: [1, 20],        // fewest and most slides (one slide on its own is a single post)
    frameMin: 60,           // a frame is never smaller than this, either way
    onStrip: 40,            // at least this much of anything stays on the strip
    zoom: [1, 25],          // a photo inside its frame: the Crop window reaches 25 (a box 4% of the photo; hers the same)
    zoomHand: 3,            // the Zoom slider's and the wheel's own top: a turn of the wheel never passes it by itself
    cropMin: 0.04,          // the Crop window's box is never smaller than this much of the photo, either way (hers)
    blocks: 80,             // photos and text boxes in one design
    idMax: 1000000,
    inset: 70,              // "Add border" pulls each edge in by this much
    dup: 60,                // a duplicate sits this far down and right of its original
    snapPx: 10,             // snapping reaches this many SCREEN pixels
    centerPx: 14,           // and the middle of a slide, a seam or half way up reaches this many (hers)
    centerFlash: 1400,      // after an arrow key: how long the centered lines show, in ms (hers)
    nudge: 5, nudgeBig: 50, // an arrow key, and with Shift
    undo: 60,               // steps of Undo kept
    seam: 20,               // a thing within this many strip pixels of an edge does not stretch across it (hers)
    wheel: 1.05,            // one turn of the wheel zooms by this much
    // how wide one slide may be drawn on screen: the Size slider runs from "every slide fits across the window"
    // (never under min, and never over few when there are only a few slides) up to max; one keyboard step of the
    // slider is step; the strip starts with a slide about a third of the window tall, between start[0] and
    // start[1] pixels tall
    view: {min: 40, max: 480, step: 1.25, few: 140, start: [230, 460]}
  };
  if (L0 && L0.slides && L0.slides.length === 2) RULES.slides = [L0.slides[0], L0.slides[1]];
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
  // One turn of the wheel. It never passes zoomHand by itself; a zoom the Crop window set past it can be wound down,
  // and up again as far as it was.
  function zoomBy(zoom, deltaY){
    zoom = zoom >= 1 ? zoom : 1;
    var top = Math.min(RULES.zoom[1], Math.max(RULES.zoomHand, zoom));
    return r3(clamp(zoom * (deltaY < 0 ? RULES.wheel : 1 / RULES.wheel), RULES.zoom[0], top));
  }

  // ---- Crop (hers, v27): a box over the whole photo, kept as fractions of the photo {x, y, w, h}, which maps straight
  //      onto the frame's zoom and crop: the frame shows exactly what is inside the box. With "Keep the frame's shape"
  //      on, the box keeps the frame's shape (its corners only); off, the frame takes the box's shape, inside the space
  //      it had, around the same middle. pw, ph are the photo's own size. ----
  // The box a frame shows now (what the window opens with).
  function cropFromBlock(b, pw, ph){
    var L = layoutImg(b, pw, ph), w = Math.min(1, b.w / L.iw), h = Math.min(1, b.h / L.ih);
    return {x: r4(clamp(-L.left / L.iw, 0, 1 - w)), y: r4(clamp(-L.top / L.ih, 0, 1 - h)), w: r4(w), h: r4(h)};
  }
  // The box's own shape, w / h in photo fractions, for a frame of ar = w / h strip pixels.
  function cropK(ar, pw, ph){ return ar * ph / pw; }
  // The largest box of shape k (cropK) that fits the photo, w wide if it can be, centred on cx, cy.
  function fitLocked(k, cx, cy, w){
    var h = w / k;
    if (h > 1) { h = 1; w = k; }
    if (w > 1) { w = 1; h = 1 / k; }
    return {w: r4(w), h: r4(h), x: r4(clamp(cx - w / 2, 0, 1 - w)), y: r4(clamp(cy - h / 2, 0, 1 - h))};
  }
  // The box o dragged by dx, dy (fractions of the photo): it stays on the photo.
  function cropMove(o, dx, dy){
    return {x: r4(clamp(o.x + dx, 0, 1 - o.w)), y: r4(clamp(o.y + dy, 0, 1 - o.h)), w: o.w, h: o.h};
  }
  // A handle ('nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w') of the box o pulled by dx, dy. Each side stays on the photo
  // and never nearer than cropMin to its opposite. With k (the frame's shape; corners only), the box keeps that shape
  // and the opposite corner stays put.
  function cropResize(o, handle, dx, dy, k){
    var MIN = RULES.cropMin, l = o.x, t = o.y, r = o.x + o.w, btm = o.y + o.h, hw = handle.indexOf('w') >= 0, he = handle.indexOf('e') >= 0, hn = handle.indexOf('n') >= 0, hs = handle.indexOf('s') >= 0;
    if (hw) l = Math.min(r - MIN, Math.max(0, o.x + dx));
    if (he) r = Math.max(l + MIN, Math.min(1, r + dx));
    if (hn) t = Math.min(btm - MIN, Math.max(0, o.y + dy));
    if (hs) btm = Math.max(t + MIN, Math.min(1, btm + dy));
    if (k > 0) {
      var w = r - l, h = btm - t;
      if (w / h > k) w = h * k; else h = w / k;
      var ax = hw ? o.x + o.w : o.x, ay = hn ? o.y + o.h : o.y;
      var maxW = hw ? ax : 1 - ax, maxH = hn ? ay : 1 - ay;
      if (w > maxW) { w = maxW; h = w / k; }
      if (h > maxH) { h = maxH; w = h * k; }
      return {x: r4(hw ? ax - w : ax), y: r4(hn ? ay - h : ay), w: r4(w), h: r4(h)};
    }
    return {x: r4(l), y: r4(t), w: r4(r - l), h: r4(btm - t)};
  }
  // Done: the frame b showing exactly what is inside the box CR -> {x, y, w, h, zoom, ox, oy}. Unlocked, the frame
  // takes the box's shape inside the space it had, around the same middle. Ours: the frame is never under frameMin
  // and stays on the strip (fitFrame), and the zoom never past the most (hers could leave a sliver or run off).
  function cropApply(b, CR, pw, ph, slides, locked){
    var x = b.x, y = b.y, w = b.w, h = b.h;
    if (!locked) {
      var ar = (CR.w * pw) / (CR.h * ph);
      if (ar < w / h) { var nw = h * ar; x += (w - nw) / 2; w = nw; }
      else { var nh = w / ar; y += (h - nh) / 2; h = nh; }
    }
    var fr = fitFrame({x: x, y: y, w: w, h: h}, w, h, slides);
    var c = fr.w / (CR.w * pw), cover = Math.max(fr.w / pw, fr.h / ph);
    var zoom = zoomTo(c / cover), L = layoutImg(merge(fr, {zoom: zoom}), pw, ph);
    var vw = fr.w / L.iw, vh = fr.h / L.ih;
    var ox = vw < 0.999 ? clamp(CR.x / (1 - vw), 0, 1) : 0.5, oy = vh < 0.999 ? clamp(CR.y / (1 - vh), 0, 1) : 0.5;
    return merge(fr, {zoom: zoom, ox: r4(ox), oy: r4(oy)});
  }

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
  // ---- centered (hers, v22): the middle of a slide, a seam the thing sits across, and half way up ----
  // The slides a thing at x, w wide, is on: {slide: the first (from 0), span: how many}.
  function onSlides(x, w, slides){
    var first = clamp(Math.floor((x + 1) / W), 0, slides - 1), last = Math.max(first, clamp(Math.floor((x + w - 1) / W), 0, slides - 1));
    return {slide: first, span: last - first + 1};
  }
  // What the blue lines and the label are drawn from: x = where the upright line is (null: none), y = where the
  // level one is (null: none), cx, cy = the thing's middle (where the label sits), seam = the upright line is a
  // seam, slide and span = the slides the level line runs over.
  function midOf(x, y, w, h, slides, onX, onY, seam){
    var on = onSlides(x, w, slides);
    return {x: onX ? x + w / 2 : null, y: onY ? H / 2 : null, cx: x + w / 2, cy: y + h / 2, seam: !!seam, slide: on.slide, span: on.span};
  }
  // The label on the blue pill: her five.
  function midWords(mid){
    if (!mid || (mid.x == null && mid.y == null)) return '';
    if (mid.x != null && mid.y != null) return mid.seam ? 'Centered on the seam, and up and down' : 'Centered';
    if (mid.x != null) return mid.seam ? 'Centered on the seam' : 'Centered side to side';
    return 'Centered up and down';
  }
  // Is b centered where it sits now (within a pixel)? What the flash after an arrow key shows, or null.
  function centered(st, b){
    if (!b) return null;
    var cx = b.x + b.w / 2, cy = b.y + b.h / 2, r = ((cx - W / 2) % W + W) % W;
    var onMid = (r < 1 || W - r < 1) && cx > 0 && cx < st.slides * W;
    var q = (cx % W + W) % W;
    var onSeam = (q < 1 || W - q < 1) && cx > 1 && cx < st.slides * W - 1 && Math.floor((b.x + 1) / W) !== Math.floor((b.x + b.w - 1) / W);
    var onY = Math.abs(cy - H / 2) < 1;
    if (!onMid && !onSeam && !onY) return null;
    return midOf(b.x, b.y, b.w, b.h, st.slides, onMid || onSeam, onY, onSeam && !onMid);
  }
  // o: {snap: true | false, thr: reach in strip pixels, cthr: the reach of the centers, in strip pixels (0 or
  // none: no centering)}. The middle is tried first; the edges snap only on an axis the middle did not.
  function move(st, b0, dx, dy, o){
    o = o || {};
    var x = b0.x + dx, y = b0.y + dy, gx = [], gy = [], mid = null, dcx = null, dcy = null, seam = false;
    if (o.snap) {
      if (o.cthr > 0) {
        var mids = [], across = [], k;
        for (k = 0; k < st.slides; k++) mids.push(k * W + W / 2);
        // only a seam the thing actually sits across
        for (k = 1; k < st.slides; k++) { if (x < k * W - 1 && x + b0.w > k * W + 1) across.push(k * W); }
        var cx0 = x + b0.w / 2, dm = nearest(cx0, mids, o.cthr), ds = across.length ? nearest(cx0, across, o.cthr) : null;
        dcx = dm === null ? ds : ds === null ? dm : (Math.abs(dm) <= Math.abs(ds) ? dm : ds);
        dcy = nearest(y + b0.h / 2, [H / 2], o.cthr);
        seam = dcx !== null && dcx === ds && ds !== dm;
        if (dcx !== null) x += dcx;
        if (dcy !== null) y += dcy;
      }
      var lx = lines(st, 'x', b0.id), ly = lines(st, 'y', b0.id);
      if (dcx === null) {
        var a1 = nearest(x, lx, o.thr), a2 = nearest(x + b0.w, lx, o.thr);
        var ax = a1 === null ? a2 : a2 === null ? a1 : (Math.abs(a1) <= Math.abs(a2) ? a1 : a2);
        if (ax !== null) { x += ax; gx.push(ax === a1 ? x : x + b0.w); }
      }
      if (dcy === null) {
        var b1 = nearest(y, ly, o.thr), b2 = nearest(y + b0.h, ly, o.thr);
        var ay = b1 === null ? b2 : b2 === null ? b1 : (Math.abs(b1) <= Math.abs(b2) ? b1 : b2);
        if (ay !== null) { y += ay; gy.push(ay === b1 ? y : y + b0.h); }
      }
    }
    var c = clampXY(x, y, b0.w, b0.h, st.slides);
    if (c.x !== x) { gx = []; dcx = null; }     // a guide line only shows where the thing really sits
    if (c.y !== y) { gy = []; dcy = null; }
    if (dcx !== null || dcy !== null) mid = midOf(c.x, c.y, b0.w, b0.h, st.slides, dcx !== null, dcy !== null, seam);
    return {x: r2(c.x), y: r2(c.y), gx: gx, gy: gy, mid: mid};
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

  // A frame of w by h strip pixels, centred where the frame of b was, never under frameMin on either side (a side
  // that would be is brought to frameMin, and the photo covers the frame as ever, so a sliver of it is cut off rather
  // than a frame too small to take hold of), and on the strip. -> {x, y, w, h}
  function fitFrame(b, w, h, slides){
    w = Math.max(RULES.frameMin, w); h = Math.max(RULES.frameMin, h);
    var c = clampXY(b.x + (b.w - w) / 2, b.y + (b.h - h) / 2, w, h, slides);
    return {x: r2(c.x), y: r2(c.y), w: r2(w), h: r2(h)};
  }

  // ---- the one-click buttons. Returns {st, sel?, why?}: st is the same layout when nothing changed;
  //      sel is given only when the selection should change; why says what stopped it. ----
  //      o: {pw, ph}: the photo's own size, which 'whole' (Show the whole photo) needs.
  var FRAME_ONLY = {full: 1, span2: 1, top: 1, bottom: 1, left: 1, right: 1, margin: 1, empty: 1, whole: 1};
  function act(st, id, a, o){
    var i = indexOf(st, id);
    if (i < 0) return {st: st};
    var b = st.blocks[i];
    if (FRAME_ONLY[a] && !isFrame(b)) return {st: st};
    var si = slideOf(b, st.slides), x0 = si * W, m = RULES.inset, blocks, c;
    if (a === 'whole') {
      // Show the whole photo (hers, v27): the frame shrinks to the photo's own shape inside the space it had, centred,
      // the crop back to the middle at zoom 1, so the whole photo shows with the background around it. An empty frame
      // is left alone. Ours: never under frameMin (hers could leave a sliver of a very tall photo in a wide short frame).
      var pw = o && o.pw > 0 ? o.pw : 0, ph = o && o.ph > 0 ? o.ph : 0;
      if (isHole(b) || !(pw && ph)) return {st: st};
      var ar = pw / ph, wide = ar > b.w / b.h, nw = wide ? b.w : b.h * ar, nh = wide ? b.w / ar : b.h;
      return {st: patch(st, id, merge(fitFrame(b, nw, nh, st.slides), {ox: 0.5, oy: 0.5, zoom: 1}))};
    }
    if (a === 'full') return {st: patch(st, id, {x: x0, y: 0, w: W, h: H})};
    if (a === 'span2') {
      // on a single post (one slide) the second slide is added in the same step, so one Undo takes both back (hers)
      var two = st.slides < 2 ? merge(st, {slides: 2}) : st, s0 = si + 1 < two.slides ? si : si - 1;
      return {st: patch(two, id, {x: s0 * W, y: 0, w: 2 * W, h: H})};
    }
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
  // ---- slides as things (hers, v26 for stories, v27 for both kinds) ----
  // The seam rule, in one place: does anything stretch across the edge before slide k (from 0; k = slides is the
  // end)? A thing that only touches the edge (within seam strip pixels) does not count, so a photo that fills its
  // slide to the pixel never blocks the edge beside it.
  function crosses(st, k){
    var e = k * W, s = RULES.seam;
    return st.blocks.some(function(b){ return b.x < e - s && b.x + b.w > e + s; });
  }
  // Take out slide k (from 0) and everything on it: whatever has its middle there (a photo whose middle is there goes
  // with it even when it stretches into the next slide: hers), and whatever stretches across either of its edges by
  // the seam rule (ours: hers leaves such a photo lying where it was, and the slide that moves up lands under it).
  // The slides after it move up. At one slide nothing changes: {st, why: 'one'}. (removeStory: the same, by its v26 name.)
  function removeSlide(st, k){
    if (st.slides <= 1) return {st: st, why: 'one'};
    k = clamp(Math.floor(Number(k) || 0), 0, st.slides - 1);
    var lo = k * W, hi = lo + W, s = RULES.seam;
    var goes = function(b){ var m = b.x + b.w / 2; return (m >= lo && m < hi) || (b.x < lo - s && b.x + b.w > lo + s) || (b.x < hi - s && b.x + b.w > hi + s); };
    var blocks = st.blocks.filter(function(b){ return !goes(b); })
      .map(function(b){ return b.x >= hi - s ? merge(b, {x: r2(b.x - W)}) : b; });
    return {st: withBlocks(st, blocks, {slides: st.slides - 1}), sel: null};
  }
  // A new blank slide at position `at` (from 0; at = slides puts it at the end): everything from there on moves
  // one slide along, ids and text boxes with it. Refused past the most slides ({st, why: 'most'}) and at a spot
  // something stretches across ({st, why: 'across'}). -> {st, sel: null, at}
  function insertSlide(st, at){
    if (st.slides >= RULES.slides[1]) return {st: st, why: 'most'};
    at = clamp(Math.floor(Number(at) || 0), 0, st.slides);
    if (crosses(st, at)) return {st: st, why: 'across'};
    var e = at * W - RULES.seam;
    var blocks = st.blocks.map(function(b){ return b.x >= e ? merge(b, {x: r2(b.x + W)}) : b; });
    return {st: withBlocks(st, blocks, {slides: st.slides + 1}), sel: null, at: at};
  }
  // The pieces a strip comes in: runs of slides cut wherever nothing stretches across the edge between them.
  // -> [[first, last], ...] (slides from 0, both ends in). Slides that share a stretched photo are one piece.
  function slideGroups(st){
    var g = [], a = 0;
    for (var k = 1; k <= st.slides; k++) { if (k === st.slides || !crosses(st, k)) { g.push([a, k - 1]); a = k; } }
    return g;
  }
  // Move piece `from` (an index into slideGroups) so that it lands at `to` (where among the pieces it goes: 0 to
  // the number of pieces; to = from or from + 1 is where it already is). Everything on each piece goes with it,
  // by the slide its middle is on (text boxes too). -> the new layout, or null when nothing changes.
  function moveGroup(st, from, to){
    var g = slideGroups(st);
    from = Math.floor(Number(from)); to = Math.floor(Number(to));
    if (!(from >= 0 && from < g.length && to >= 0 && to <= g.length)) return null;
    var order = g.map(function(x, i){ return i; }), m = order.splice(from, 1)[0];
    order.splice(to > from ? to - 1 : to, 0, m);
    if (order.every(function(x, i){ return x === i; })) return null;
    var shift = {}, at = 0;
    order.forEach(function(i){ shift[i] = (at - g[i][0]) * W; at += g[i][1] - g[i][0] + 1; });
    var piece = function(b){ var k = slideOf(b, st.slides); for (var i = 0; i < g.length; i++) { if (k >= g[i][0] && k <= g[i][1]) return i; } return -1; };
    var blocks = st.blocks.map(function(b){ var i = piece(b); return i >= 0 && shift[i] ? merge(b, {x: r2(b.x + shift[i])}) : b; });
    return withBlocks(st, blocks);
  }
  function setBg(st, color){
    color = String(color || '').toLowerCase();
    if (!/^#[0-9a-f]{6}$/.test(color) || color === st.bg) return st;
    return merge(st, {bg: color});
  }

  // ---- several things at once (hers, v27, Nov 14: "I can't even it out because I can't select them all") ----
  // ids: the selected things, in the order they were selected. Each returns a new layout, or the very same one when
  // nothing changes; none touches what it is given.
  var EVEN = {margin: 40, gap: 24};         // Even them out: the room left around the edge of the slide, and between photos (hers)
  function members(st, ids){
    var out = [], seen = {};
    (ids || []).forEach(function(id){ var b = find(st, id); if (b && !seen[b.id]) { seen[b.id] = true; out.push(b); } });
    return out;
  }
  function manyPatch(st, changes){
    var blocks = st.blocks, did = false;
    Object.keys(changes).forEach(function(id){
      var i = indexOf(st, Number(id));
      if (i < 0) return;
      var nb = merge(blocks[i], changes[id]);
      if (same(nb, blocks[i])) return;
      if (!did) { blocks = blocks.slice(); did = true; }
      blocks[i] = nb;
    });
    return did ? withBlocks(st, blocks) : st;
  }
  // A photo's own shape (w / h): aspects[id] when the page knows the loaded picture's, else the frame's own shape.
  function aspectOf(b, aspects){ var a = aspects && aspects[b.id]; return a > 0 ? a : b.w / b.h; }
  // Even them out: the photos among ids laid out tidily on the slide the first of them (by slide, then top to bottom,
  // then left to right) is on, in the number of columns that makes them come out biggest, every photo whole at its own
  // shape, the rows centred up and down and each row centred side to side; the crop back to the middle at zoom 1. Text
  // boxes are left where they are (hers). No column count that leaves a cell under frameMin is tried.
  function evenOut(st, ids, aspects){
    var ph = members(st, ids).filter(isFrame);
    if (!ph.length) return st;
    ph = ph.slice().sort(function(a, b){ return slideOf(a, st.slides) - slideOf(b, st.slides) || a.y - b.y || a.x - b.x; });
    var slide = slideOf(ph[0], st.slides), n = ph.length, m = EVEN.margin, g = EVEN.gap, best = null, c;
    for (c = 1; c <= n; c++) {
      var r = Math.ceil(n / c), cw = (W - 2 * m - (c - 1) * g) / c, ch = (H - 2 * m - (r - 1) * g) / r;
      if (cw < RULES.frameMin || ch < RULES.frameMin) continue;
      var sizes = ph.map(function(b){ var a = aspectOf(b, aspects), w = Math.min(cw, ch * a); return [w, w / a]; });
      var area = sizes.reduce(function(t, s){ return t + s[0] * s[1]; }, 0);
      if (!best || area > best.area) best = {c: c, cw: cw, sizes: sizes, area: area};
    }
    if (!best) return st;
    var cols = best.c, cw2 = best.cw, rows = [], i;
    for (i = 0; i < n; i += cols) rows.push(ph.slice(i, i + cols).map(function(b, k){ return [b, best.sizes[i + k]]; }));
    var rowH = rows.map(function(row){ return Math.max.apply(null, row.map(function(x){ return x[1][1]; })); });
    var y = (H - (rowH.reduce(function(t, h){ return t + h; }, 0) + (rows.length - 1) * g)) / 2, changes = {};
    rows.forEach(function(row, ri){
      var off = (cols - row.length) * (cw2 + g) / 2;
      row.forEach(function(x, k){
        var b = x[0], w = x[1][0], h = x[1][1];
        changes[b.id] = {x: r2(slide * W + m + off + k * (cw2 + g) + (cw2 - w) / 2), y: r2(y + (rowH[ri] - h) / 2), w: r2(w), h: r2(h), ox: 0.5, oy: 0.5, zoom: 1};
      });
      y += rowH[ri] + g;
    });
    return manyPatch(st, changes);
  }
  // Same size: every one among ids as wide as the reference, a photo keeping its own shape (its crop back to the middle),
  // a text box only its width (its height follows its lines). The reference is refId when that is a photo among them,
  // else the first photo among them (ours: hers took a text box as the reference and gave photos its width). o: {textMin:
  // the narrowest a text box may be}. Each stays on the strip.
  function sameSize(st, ids, refId, o){
    var list = members(st, ids), ref = null, i;
    for (i = 0; i < list.length; i++) { if (list[i].id === refId && isFrame(list[i])) ref = list[i]; }
    if (!ref) { for (i = 0; i < list.length && !ref; i++) { if (isFrame(list[i])) ref = list[i]; } }
    if (!ref) return st;
    var tmin = o && o.textMin > 0 ? o.textMin : RULES.frameMin, changes = {};
    list.forEach(function(b){
      if (b === ref) return;
      var w = ref.w, h = isText(b) ? b.h : Math.max(RULES.frameMin, ref.w / (b.w / b.h)), p;
      if (isText(b)) w = Math.max(tmin, w);
      var c = clampXY(b.x, b.y, w, h, st.slides);
      p = {x: r2(c.x), y: r2(c.y), w: r2(w)};
      if (!isText(b)) { p.h = r2(h); p.ox = 0.5; p.oy = 0.5; p.zoom = 1; }
      changes[b.id] = p;
    });
    return manyPatch(st, changes);
  }
  // Line up tops: every one among ids (text boxes too) moved up or down to the highest of them (hers).
  function lineTops(st, ids){
    var list = members(st, ids);
    if (list.length < 2) return st;
    var top = Math.min.apply(null, list.map(function(b){ return b.y; })), changes = {};
    list.forEach(function(b){ changes[b.id] = {y: r2(top)}; });
    return manyPatch(st, changes);
  }
  // Remove them: every one among ids taken out.
  function removeMany(st, ids){
    var gone = {};
    members(st, ids).forEach(function(b){ gone[b.id] = true; });
    var blocks = st.blocks.filter(function(b){ return !gone[b.id]; });
    return blocks.length === st.blocks.length ? st : withBlocks(st, blocks);
  }
  // Drag any of them and they all move (hers): every one among ids by the same dx, dy, as far as every one of them
  // stays on the strip (ours: hers let a group be dragged off the strip altogether). No snapping (hers).
  function moveMany(st, ids, dx, dy){
    var list = members(st, ids);
    if (!list.length) return st;
    var S = RULES.onStrip, sw = st.slides * W;
    list.forEach(function(b){
      dx = clamp(dx, (S - b.w) - b.x, (sw - S) - b.x);
      dy = clamp(dy, (S - b.h) - b.y, (H - S) - b.y);
    });
    var changes = {};
    list.forEach(function(b){ changes[b.id] = {x: r2(b.x + dx), y: r2(b.y + dy)}; });
    return manyPatch(st, changes);
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
  // Where the strip starts: a slide about a third of the window tall (between 230 and 460 px), however many
  // slides there are and however wide the window is; the strip scrolls sideways for the rest. -> the slide's width
  function viewStart(avail, winH){
    var h = clamp((Number(winH) || 0) / 3, RULES.view.start[0], RULES.view.start[1]);
    return clamp(Math.round(h * W / H) || 0, RULES.view.min, RULES.view.max);
  }
  // The small end of the Size slider: every slide fits across the room there is (avail screen pixels), but never
  // under min, and never over few (a design of two slides would otherwise have no small end at all).
  function viewLow(avail, slides){
    return clamp(Math.floor((Number(avail) || 0) / Math.max(1, slides || 1)), RULES.view.min, RULES.view.few);
  }
  // One step of the slider's keys: a quarter bigger or smaller, between lo (the slider's small end) and max.
  function viewStep(cur, dir, lo){
    return clamp(Math.round(dir > 0 ? cur * RULES.view.step : cur / RULES.view.step), lo > 0 ? lo : RULES.view.min, RULES.view.max);
  }

  root.DesignModel = {
    W: W, H: H, KIND: KIND, RULES: RULES, useLimits: useLimits,
    crosses: crosses, removeSlide: removeSlide, removeStory: removeSlide, insertSlide: insertSlide, slideGroups: slideGroups, moveGroup: moveGroup,
    clamp: clamp, r2: r2, isText: isText, isFrame: isFrame, isHole: isHole, typeOf: typeOf, same: same, copy: copy,
    indexOf: indexOf, find: find, merge: merge, tidy: tidy, patch: patch, nextId: nextId,
    layoutImg: layoutImg, pan: pan, zoomTo: zoomTo, zoomBy: zoomBy,
    cropFromBlock: cropFromBlock, cropK: cropK, fitLocked: fitLocked, cropMove: cropMove, cropResize: cropResize, cropApply: cropApply,
    slideOf: slideOf, clampXY: clampXY, onStrip: onStrip,
    lines: lines, nearest: nearest, move: move, centered: centered, midWords: midWords, onSlides: onSlides, resize: resize, nudge: nudge,
    act: act, fitFrame: fitFrame, onSlide: onSlide, fewerSlides: fewerSlides, moreSlides: moreSlides, setBg: setBg,
    EVEN: EVEN, members: members, evenOut: evenOut, sameSize: sameSize, lineTops: lineTops, removeMany: removeMany, moveMany: moveMany,
    used: used, firstEmptySlide: firstEmptySlide, nextHole: nextHole, swapPhoto: swapPhoto, addPhoto: addPhoto,
    clickPhoto: clickPhoto, dropAt: dropAt, pickSize: pickSize, screenCopy: screenCopy,
    history: history, viewStart: viewStart, viewLow: viewLow, viewStep: viewStep
  };
})(typeof window !== 'undefined' ? window : this);
"""
