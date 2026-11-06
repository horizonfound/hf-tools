#!/usr/bin/env python3
"""The carousel designer's rules for designs, templates and saving, with no page in them.

DESIGN_PLAN_JS makes window.DesignPlan (P): how a template becomes a layout, which photo goes in which
empty frame, what is on each slide, which made copy of a photo a drawing wants, the profile grid's trim,
"edited 5 min ago", the name of one press, and what a swipe in the preview does. Every function takes plain
values and returns plain values and touches no document, so tests/design_check.py runs it by itself under
the Mac's own JavaScript engine (as it does the other two rule scripts).

    P.fillOrder(photos, carousel)     the photos to fill frames from, in order: the carousel's picks first
    P.fill(st, photos, carousel)      every empty frame given the next unused photo whose shape fits
    P.fromTemplate(tpl, fill, photos, carousel)    a template's layout, with this shoot's photos or without
    P.onePerSlide(photos, carousel, bg)
    P.holes(st), P.frames(st)         the empty frames in filling order; how many frames there are
    P.slideBlocks(st, k)              what a saved slide k (from 0) is drawn from, in list order
    P.bareSlides(st), P.holeSlides(st)   slide numbers (from 1) with nothing on them / with an empty frame
    P.copyFor(b, p, out, sizes, cap)  which made copy of photo p frame b wants when drawn `out` times slide size
    P.gridTrim()                      how much of each side of slide 1 the profile grid leaves out
    P.ago(t, now)                     'just now', '5 min ago', '2 hr ago', or null (older: the page shows the day)
    P.token(prefix, now, rnd)         the name of one press, as the Assistant wants it
    P.swipe(i, dx, slides)            the slide showing after a drag of dx screen pixels in the preview
    P.list(numbers)                   '2', '2 and 4', '2, 4 and 5'
"""

DESIGN_PLAN_JS = r"""
(function(root){
  'use strict';
  var W = 1080, H = 1350;
  // Every number these rules go by, in one place.
  var RULES = {
    wide: 1.15,             // a frame wider than this (width over height) wants a wide photo
    tall: 0.9,              // a frame narrower than this wants a tall one
    seedMost: 8,            // "One photo per slide" when the shoot has no carousel order yet
    slides: [2, 20],
    grid: 3 / 4,            // the tile Instagram's profile grid shows, width over height
    swipe: 40,              // a drag in the preview turns the slide once it has gone this many pixels
    order: ['s', 'l', 'x', 'xx']
  };
  function clamp(v, a, b){ return Math.max(a, Math.min(b, v)); }
  function copy(v){ return JSON.parse(JSON.stringify(v)); }
  function isText(b){ return !!b && b.type === 'text'; }
  function isFrame(b){ return !!b && b.type !== 'text'; }
  function isHole(b){ return isFrame(b) && b.n == null; }

  // ---- filling frames ----
  // The empty frames in the order they are filled: by slot, then left to right, then top to bottom.
  function holes(st){
    var hs = st.blocks.filter(isHole);
    hs.sort(function(a, b){ return (a.slot || 0) - (b.slot || 0) || a.x - b.x || a.y - b.y || a.id - b.id; });
    return hs;
  }
  function frames(st){ return st.blocks.filter(isFrame).length; }
  function wants(b){ var ar = b.w / b.h; return ar > RULES.wide ? 'wide' : ar < RULES.tall ? 'tall' : null; }
  // The photos frames are filled from, in order: the carousel's own picks first (they were chosen for this),
  // then every other photo by its number. A photo that can't be read right now is left out.
  function fillOrder(photos, carousel){
    var by = {}, out = [], seen = {};
    (photos || []).forEach(function(p){ if (p && !p.missing) by[p.n] = p; });
    (carousel || []).forEach(function(n){ if (by[n] && !seen[n]) { seen[n] = true; out.push(by[n]); } });
    (photos || []).forEach(function(p){ if (p && by[p.n] && !seen[p.n]) { seen[p.n] = true; out.push(p); } });
    return out;
  }
  // Every empty frame is given the next unused photo whose shape fits: wide to wide, tall to tall. When no
  // photo of the right shape is left, a wide frame takes a square one before a tall one; then anything.
  // No photo is used twice; frames stay empty when the photos run out. The same layout back when nothing changes.
  function fill(st, photos, carousel){
    var used = {}, hs = holes(st);
    if (!hs.length) return st;
    st.blocks.forEach(function(b){ if (isFrame(b) && b.n != null) used[b.n] = true; });
    var free = fillOrder(photos, carousel).filter(function(p){ return !used[p.n]; });
    if (!free.length) return st;
    var give = {};
    hs.forEach(function(b){
      var want = wants(b), i = -1, k;
      if (want) { for (k = 0; k < free.length; k++) { if (free[k].way === want) { i = k; break; } } }
      if (i < 0 && want === 'wide') { for (k = 0; k < free.length; k++) { if (free[k].way !== 'tall') { i = k; break; } } }
      if (i < 0 && free.length) i = 0;
      if (i >= 0) { give[b.id] = free[i].n; free.splice(i, 1); }
    });
    var blocks = st.blocks.map(function(b){
      if (!(b.id in give)) return b;
      var nb = copy(b);
      nb.n = give[b.id]; nb.ox = 0.5; nb.oy = 0.5; nb.zoom = 1;
      return nb;
    });
    var out = {}, key;
    for (key in st) out[key] = st[key];
    out.blocks = blocks;
    return out;
  }
  // A template (the Assistant's shape: a layout whose frames are all empty) as a layout for this shoot.
  function fromTemplate(tpl, doFill, photos, carousel){
    var st = {slides: clamp(Math.round(tpl.slides) || RULES.slides[0], RULES.slides[0], RULES.slides[1]),
              bg: typeof tpl.bg === 'string' ? tpl.bg : '#ffffff', blocks: copy(tpl.blocks || [])};
    st.blocks.forEach(function(b){ if (isFrame(b)) { b.n = null; b.ox = 0.5; b.oy = 0.5; b.zoom = 1; } });
    return doFill ? fill(st, photos, carousel) : st;
  }
  // One photo per slide, each filling its slide: the carousel's order, or the first few photos when the
  // shoot has no order yet. (What the Assistant itself makes for a shoot's first design.)
  function onePerSlide(photos, carousel, bg){
    var by = {}, nums = [];
    (photos || []).forEach(function(p){ by[p.n] = p; });
    (carousel || []).forEach(function(n){ if (by[n] && nums.length < RULES.slides[1]) nums.push(n); });
    if (!nums.length) nums = (photos || []).slice(0, RULES.seedMost).map(function(p){ return p.n; });
    return {slides: clamp(nums.length, RULES.slides[0], RULES.slides[1]), bg: typeof bg === 'string' ? bg : '#ffffff',
            blocks: nums.map(function(n, i){ return {id: i + 1, n: n, x: i * W, y: 0, w: W, h: H, ox: 0.5, oy: 0.5, zoom: 1, slot: i + 1}; })};
  }

  // ---- what is on each slide ----
  // What saved slide k (from 0) is drawn from: everything that reaches into it, in list order (the last on top).
  function slideBlocks(st, k){
    var x0 = k * W, x1 = x0 + W;
    return st.blocks.filter(function(b){ return b.x + b.w > x0 && b.x < x1 && b.y + b.h > 0 && b.y < H; });
  }
  function slideOf(b, slides){ return clamp(Math.floor((b.x + b.w / 2) / W), 0, slides - 1); }
  // Slide numbers (from 1) that nothing at all reaches into: they would be saved as plain background.
  function bareSlides(st){
    var out = [];
    for (var k = 0; k < st.slides; k++) { if (!slideBlocks(st, k).length) out.push(k + 1); }
    return out;
  }
  // The empty frames: how many, and the slide numbers (from 1) they sit on (the slide under each one's middle).
  function holeSlides(st){
    var seen = {}, out = [], hs = st.blocks.filter(isHole);
    hs.forEach(function(b){ var k = slideOf(b, st.slides) + 1; if (!seen[k]) { seen[k] = true; out.push(k); } });
    out.sort(function(a, b){ return a - b; });
    return {count: hs.length, slides: out};
  }

  // ---- which made copy of a photo a drawing wants ----
  // b = the frame; p = the photo's record ({w, h}); out = how large the slide is drawn (1 for a saved slide,
  // less for the preview and the little pictures in the gallery); sizes = {s, l, x, xx}; cap = the largest
  // copy to ask for (the preview never asks for one that has to be made first). The smallest copy at least
  // as large as the photo will be drawn, or as large as the photo itself.
  function copyFor(b, p, out, sizes, cap){
    var pw = p && p.w > 0 ? p.w : 3, ph = p && p.h > 0 ? p.h : 2, zoom = b.zoom >= 1 ? b.zoom : 1;
    var c = Math.max(b.w / pw, b.h / ph) * zoom, need = Math.max(pw * c, ph * c) * (out > 0 ? out : 1), long = Math.max(pw, ph);
    var pick = RULES.order[RULES.order.length - 1], i;
    for (i = 0; i < RULES.order.length; i++) {
      var v = sizes ? sizes[RULES.order[i]] : 0;
      if (!(v > 0)) continue;
      if (v >= need || v >= long) { pick = RULES.order[i]; break; }
    }
    if (cap && RULES.order.indexOf(pick) > RULES.order.indexOf(cap)) pick = cap;
    return pick;
  }

  // ---- the profile grid ----
  // The grid shows a 3:4 tile cut from the middle of the first slide. A slide is 4:5 (1080 by 1350), so its
  // whole height shows and 1350 * 3/4 = 1012.5 of its width: (1080 - 1012.5) / 2 = 33.75 is left out each side.
  function gridTrim(){ return Math.max(0, (W - H * RULES.grid) / 2); }

  // ---- small things ----
  // t, now = seconds since 1970. Older than a day: null (the page shows the day).
  function ago(t, now){
    var s = now - t;
    if (!(t > 0) || !isFinite(s)) return null;
    if (s < 60) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min ago';
    if (s < 86400) return Math.round(s / 3600) + ' hr ago';
    return null;
  }
  // The name of one press (a new design, a template, a set of slides): 8 to 24 small letters and digits.
  function token(prefix, now, rnd){
    var p = String(prefix || 's').toLowerCase().replace(/[^a-z]/g, '').slice(0, 2) || 's';
    var r = Math.floor((rnd >= 0 && rnd < 1 ? rnd : 0) * 1679616).toString(36), t = Math.max(0, Math.floor(now) || 0).toString(36);
    while (r.length < 4) r = '0' + r;
    while (t.length < 8) t = '0' + t;
    return (p + t.slice(-18) + r).slice(0, 24);
  }
  // The preview: the slide showing after a drag of dx pixels (to the left = the next one).
  function swipe(i, dx, slides){ return clamp(dx < -RULES.swipe ? i + 1 : dx > RULES.swipe ? i - 1 : i, 0, slides - 1); }
  // How wide the preview's slide is drawn, in a window this large.
  function phoneWidth(winW, winH){ return Math.round(clamp(Math.min(380, winW - 48, (winH - 190) * W / H), 160, 380)); }
  // How large a whole strip is drawn in one of the gallery's little pictures (a number to times the strip by).
  function cardScale(slides, maxW, maxH){ return Math.min(maxH / H, maxW / (slides * W)); }
  function list(nums){
    var a = (nums || []).map(String);
    return a.length <= 1 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1];
  }

  root.DesignPlan = {
    W: W, H: H, RULES: RULES,
    holes: holes, frames: frames, wants: wants, fillOrder: fillOrder, fill: fill, fromTemplate: fromTemplate, onePerSlide: onePerSlide,
    slideBlocks: slideBlocks, bareSlides: bareSlides, holeSlides: holeSlides, copyFor: copyFor, gridTrim: gridTrim,
    ago: ago, token: token, swipe: swipe, phoneWidth: phoneWidth, cardScale: cardScale, list: list
  };
})(typeof window !== 'undefined' ? window : this);
"""
