#!/usr/bin/env python3
"""The carousel designer's page: the strip of slides, the frames on it, and the photos below.

DESIGN_EDIT_JS (put on the page by design_page.py, after the model and the core) draws the strip and handles
everything a hand does on it:

    photos as frames (the picture always covers its frame, laid out from the picture's own size); empty frames
    press to select; drag to move (after 3 px); pull a corner to resize (Shift keeps the shape); both snap to
    sixths of a slide and to other things' edges with pink guide lines (Alt, or the Snap tick, turns it off)
    double-click, or "Move photo inside": drag the picture inside its frame, wheel or slider to zoom
    the one-click buttons, arrow keys, Delete, Cmd/Ctrl+Z, Escape
    the tray: every photo numbered as in the pickers; drag one onto a frame or a slide, or click it
    Slides - / +, the background, the Size slider (how large the slides are drawn), Undo

Dragging is drawn by the page itself with pointer events (the browser's own drag-and-drop does not work in
the Claude app's pane), modelled on arrange_page.DRAG_JS. WHILE A DRAG IS GOING ON ONLY THE DRAGGED THING'S OWN
STYLE CHANGES (and the selection box and guide lines that follow it): the layout, one Undo step and one save
happen when the button is let go. Escape, a cancelled pointer, the window losing focus or a mouse move with no
button held put everything back. Nothing waits on a timer: every change is made in the event's own handler.

Where later parts attach:
    Designer.blockTypes.text = {make, draw, widthOnly: true, minW: 80, ...}       (stage C; until then a text
                               box is drawn by the plain stand-in 'other' below, and kept exactly as it is)
    Designer.selbar.group(...) for the text controls; Designer.tools.group(...) for + Add text, brand colors,
                               + New design, Save as template, Fill empty frames, Preview swipe, Save slides
    Designer.viewSlide()       the slide in the middle of what is showing (where + Add text puts a text box)
    Designer.reveal(id)        scroll the strip so a block shows
"""

DESIGN_EDIT_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, W = M.W, H = M.H, $ = D.$, el = D.el, WORDS = D.WORDS;
  var stage = $('stage'), wrap = $('stripwrap'), strip = $('strip'), over = $('over'), labels = $('labels'), thumbs = $('thumbs');
  // A photo added by a CLICK in the tray becomes the selected one (as in Nicole's page), so the next click
  // swaps it rather than filling the next empty spot. One place to change that.
  var CLICK_ADD_SELECTS = true;
  var MOVE_START = 3, TRAY_START = 7;       // pixels of travel before a press becomes a drag
  var EDGE = 40, STEP = 14, DWELL = 250;    // the strip scrolls sideways while a drag rests this near its ends

  var nodes = {};       // block id -> its element on the strip (kept between draws, so no picture is fetched twice)
  var seams = [], guides = [], tiles = {};
  // The selection box: a ring (the outline) and four handles. The ring is cut off at the strip's edges, so a
  // frame pulled past the top or bottom is not drawn over the slide labels or the page; a handle whose corner
  // is off the strip is not drawn either, while one on the strip's very edge shows whole.
  var selbox = el('div', 'selbox'), ring = el('i', 'ring'), handles = [];
  selbox.appendChild(ring);
  ['tl', 'tr', 'bl', 'br'].forEach(function(c){ var h = el('div', 'h ' + c); h.dataset.h = c; selbox.appendChild(h); handles.push(h); });
  var slidemark = el('div', 'slidemark');
  over.appendChild(slidemark); over.appendChild(selbox);
  var G = null;         // the press or drag in hand
  var view = 0;         // how wide one slide is drawn, in screen pixels (0 until the first state arrives)

  // ---------- the photo kind of block ----------
  var ready = {}, asked = {};       // 'n:l' -> the sharper copy has loaded in this page / has been asked for
  function dpr(){ return Math.min(2, window.devicePixelRatio || 1); }
  // The picture's OWN size once it has loaded (whichever copy is showing); the list's numbers until then.
  function natural(node, b){
    var img = node ? node.querySelector('img') : null, p = D.by[b.n];
    if (img && img.naturalWidth > 0 && Number(img.dataset.shown) === b.n) return {w: img.naturalWidth, h: img.naturalHeight};
    return {w: (p && p.w) || 3, h: (p && p.h) || 2};
  }
  function setSrc(img, n, size){
    var u = D.photoUrl(n, size);
    if (img.getAttribute('src') !== u) img.setAttribute('src', u);
    img.dataset.size = size;
  }
  function sharper(n){
    var k = n + ':l';
    if (asked[k]) return;
    asked[k] = true;
    var im = new Image();
    im.onload = function(){ ready[k] = true; D.render(); };
    im.onerror = function(){ asked[k] = false; };
    im.src = D.photoUrl(n, 'l');
  }
  function relayout(node){
    if (G && G.on && G.node === node) return;           // it is being dragged: the drag draws it
    var b = D.st ? M.find(D.st, Number(node.dataset.id)) : null;
    if (b && D.typeOf(b) === 'photo') D.blockTypes.photo.draw(node, b, D.scale, false);
  }
  D.blockTypes.photo = {
    pan: true,
    natural: natural,
    make: function(){ return el('div', 'blk'); },
    // live = true while this block is being dragged (nothing is fetched then)
    draw: function(node, b, s, live){
      var p = b.n == null ? null : D.by[b.n];
      var img = node.querySelector('img'), drop = node.querySelector('.drop'), cant = node.querySelector('.cant'), bd = node.querySelector('.bd');
      node.classList.toggle('hole', !p);
      if (!p) {
        // an empty frame
        if (img) img.remove();
        if (cant) cant.remove();
        if (!drop) { drop = el('span', 'drop', WORDS.dropHere); node.appendChild(drop); }
        drop.style.fontSize = Math.max(10, 34 * s) + 'px';
        drop.hidden = !(s > 0.1) || b.w * s < 70;
      } else {
        if (drop) drop.remove();
        if (img && Number(img.dataset.n) !== b.n) { img.remove(); img = null; }      // another photo now: never show the old one stretched
        if (!img && p.have) {
          img = document.createElement('img');
          img.alt = ''; img.dataset.n = b.n; img.decoding = 'async';
          img.addEventListener('load', function(){ this.dataset.shown = this.dataset.n; relayout(node); });
          node.insertBefore(img, node.firstChild);
          setSrc(img, b.n, ready[b.n + ':l'] ? 'l' : 's');
        }
        var nat = natural(node, b), L = M.layoutImg(b, nat.w, nat.h);
        if (img) {
          img.style.width = L.iw * s + 'px'; img.style.height = L.ih * s + 'px';
          img.style.left = L.left * s + 'px'; img.style.top = L.top * s + 'px';
          // the small copy until the photo is drawn larger than it; then the sharper one, once it has arrived
          if (!live && img.dataset.size !== 'l' && M.screenCopy(Math.max(L.iw, L.ih) * s * dpr(), Math.max(p.w, p.h), D.S.sizes) === 'l') {
            if (ready[b.n + ':l']) setSrc(img, b.n, 'l'); else sharper(b.n);
          }
        }
        var bad = !p.have && !!p.missing;
        if (bad && !cant) node.appendChild(el('span', 'cant', WORDS.cantRead));
        if (!bad && cant) cant.remove();
      }
      // a line drawn inside the frame's edge, over the photo (kept by the Assistant; no button sets one yet)
      if (b.border && b.border.w > 0 && /^#[0-9a-fA-F]{6}$/.test(b.border.color || '')) {
        if (!bd) { bd = el('i', 'bd'); node.appendChild(bd); }
        bd.style.boxShadow = 'inset 0 0 0 ' + Math.max(1, b.border.w * s) + 'px ' + b.border.color;
      } else if (bd) bd.remove();
    }
  };
  // A stand-in for any kind of block this page has no drawing for yet (a text box, until the text part is
  // on the page): its words in a dashed box. It can be selected, moved, stacked, duplicated and removed, and
  // is saved back exactly as it came.
  D.blockTypes.other = {
    fixed: true,
    make: function(){ return el('div', 'blk other'); },
    draw: function(node, b, s){
      node.textContent = typeof b.text === 'string' ? b.text : '';
      node.style.fontSize = Math.max(9, Math.min(60, (b.size || 60) * 0.5) * s) + 'px';
    }
  };
  D.hints.none = function(){ return WORDS.hintNone; };
  D.hints.photo = function(b){ return M.isHole(b) ? WORDS.hintHole : D.adjust ? WORDS.hintInside(b.n) : WORDS.hintPhoto(b.n); };
  D.hints.other = function(){ return WORDS.hintOther; };

  // ---------- drawing the strip ----------
  function place(node, b, s){
    node.style.left = b.x * s + 'px'; node.style.top = b.y * s + 'px';
    node.style.width = b.w * s + 'px'; node.style.height = b.h * s + 'px';
  }
  // The selection box around b: its ring stops at the strip's edges (3 px outside the box where the box's own
  // edge is on the strip, so the 2 px outline shows), and a handle is drawn only where its corner is on the strip.
  // A text box's two handles sit at mid-height on its sides.
  function placeSel(b, s){
    place(selbox, b, s);
    var sw = D.st.slides * W, T = D.blockTypes[D.typeOf(b)];
    var cut = function(v){ return (v > 0 ? v * s : -3) + 'px'; };
    ring.style.clipPath = 'inset(' + cut(-b.y) + ' ' + cut(b.x + b.w - sw) + ' ' + cut(b.y + b.h - H) + ' ' + cut(-b.x) + ')';
    handles.forEach(function(h){
      var c = h.dataset.h, px = c.charAt(1) === 'l' ? b.x : b.x + b.w, py = T.widthOnly ? b.y + b.h / 2 : (c.charAt(0) === 't' ? b.y : b.y + b.h);
      h.classList.toggle('out', px < -0.5 || px > sw + 0.5 || py < -0.5 || py > H + 0.5);
    });
  }
  function clearGuides(){ guides.forEach(function(g){ g.remove(); }); guides = []; }
  function showGuides(gx, gy){
    clearGuides();
    var s = D.scale;
    (gx || []).forEach(function(x){ var e = el('div', 'guide'); e.style.left = x * s + 'px'; e.style.top = '0'; e.style.width = '1px'; e.style.height = '100%'; over.appendChild(e); guides.push(e); });
    (gy || []).forEach(function(y){ var e = el('div', 'guide'); e.style.top = y * s + 'px'; e.style.left = '0'; e.style.height = '1px'; e.style.width = '100%'; over.appendChild(e); guides.push(e); });
  }
  function clearDropMarks(){
    slidemark.style.display = 'none';
    Object.keys(nodes).forEach(function(id){ nodes[id].classList.remove('droptarget'); });
  }
  // What a thing on the strip is called for someone who cannot see it: "Photo 5 on slide 2".
  function slideOf(b){ return M.clamp(Math.floor((b.x + b.w / 2) / W), 0, D.st.slides - 1) + 1; }
  function blockName(b){
    var k = slideOf(b);
    if (M.isText(b)) return WORDS.nameText(String(b.text || '').replace(/\s+/g, ' ').trim().slice(0, 60), k);
    return M.isHole(b) ? WORDS.nameHole(k) : WORDS.namePhoto(b.n, k);
  }
  function draw(){
    var st = D.st, s = D.scale;
    strip.style.width = st.slides * W * s + 'px';
    strip.style.height = H * s + 'px';
    strip.style.background = st.bg;
    var seen = {};
    st.blocks.forEach(function(b, i){
      var kind = D.typeOf(b), T = D.blockTypes[kind], node = nodes[b.id];
      if (node && node.dataset.kind !== kind) { node.remove(); node = null; }
      if (!node) {
        node = T.make(b); node.dataset.id = b.id; node.dataset.kind = kind; nodes[b.id] = node; strip.appendChild(node);
        // each thing on the strip can be reached with the Tab key, and says what it is
        node.tabIndex = 0; node.setAttribute('role', 'button');
      }
      var name = blockName(b);
      if (node.getAttribute('aria-label') !== name) node.setAttribute('aria-label', name);
      node.style.zIndex = i + 1;          // stacking is the order of the list: the last is on top
      place(node, b, s);
      T.draw(node, b, s, false);
      node.classList.toggle('sel', b.id === D.sel);
      node.classList.toggle('adj', b.id === D.sel && D.adjust);
      seen[b.id] = true;
    });
    Object.keys(nodes).forEach(function(id){ if (!seen[id]) { nodes[id].remove(); delete nodes[id]; } });
    while (seams.length > st.slides - 1) seams.pop().remove();
    while (seams.length < st.slides - 1) { var sm = el('div', 'seam'); strip.appendChild(sm); seams.push(sm); }
    seams.forEach(function(sm, i){ sm.style.left = (i + 1) * W * s + 'px'; });
    while (labels.children.length > st.slides) labels.lastChild.remove();
    while (labels.children.length < st.slides) labels.appendChild(el('span', '', WORDS.slide(labels.children.length + 1)));
    for (var k = 0; k < st.slides; k++) labels.children[k].style.left = (k + 0.5) * W * s + 'px';
    var b = D.selected();
    if (b) {
      placeSel(b, s);
      selbox.className = 'selbox on' + (D.adjust ? ' adj' : '') + (D.blockTypes[D.typeOf(b)].fixed ? ' fixed' : '');
    } else selbox.className = 'selbox';
    if (!G || !G.on) { clearGuides(); clearDropMarks(); }
    else if (G.redo) G.redo();          // a drag is going on: what it shows is drawn again over the fresh strip
  }
  D.on('render', draw);

  // ---------- the bars of buttons ----------
  var g1 = D.selbar.group('sel-photo', 'Selected photo', function(kind){ return kind === 'photo'; });
  [['Fill slide', 'full'], ['Across 2 slides', 'span2'], ['Top half', 'top'], ['Bottom half', 'bottom'], ['Left half', 'left'],
   ['Right half', 'right'], ['Add border', 'margin']].forEach(function(x){ D.selbar.button(g1, x[0], x[1]); });
  var g2 = D.selbar.group('sel-crop', 'Crop', function(kind){ return kind === 'photo'; });
  var adjBtn = D.selbar.button(g2, WORDS.inside, 'adjust');
  adjBtn.id = 'adjust';
  g2.appendChild(el('span', 'lbl', 'Zoom'));
  var zoomImg = el('input'); zoomImg.type = 'range'; zoomImg.id = 'zoom-img'; zoomImg.min = '100'; zoomImg.max = '300'; zoomImg.value = '100';
  zoomImg.setAttribute('aria-label', 'Zoom the photo inside its frame');
  g2.appendChild(zoomImg);
  D.selbar.button(g2, 'Take the photo out', 'empty', 'Takes the photo out and leaves an empty frame');
  // HOOK (stage C): the text controls are groups added here, before this last one, with Designer.selbar.group(...)
  var g3 = D.selbar.group('sel-all', '', function(){ return true; });
  [['Center on slide', 'center'], ['Bring forward', 'front'], ['Send back', 'back'], ['Duplicate', 'dup'], ['Remove', 'del']].forEach(function(x){ D.selbar.button(g3, x[0], x[1]); });

  function lines(which, text){
    D.say($('slides-line'), which === 'slides' ? text : '');
    D.selbar.line(which === 'sel' ? text : '');
    $('trayline').textContent = which === 'tray' ? text : '';
  }
  D.on('change', function(){ lines('', ''); });
  D.on('design', function(){ lines('', ''); });
  function why(r){ var w = WORDS[r.why]; return typeof w === 'function' ? w(r.slide) : (w || ''); }

  function doAct(a){
    var b = D.selected();
    if (!b) return;
    if (a === 'adjust') {
      if (D.typeOf(b) === 'photo' && !M.isHole(b)) D.select(b.id, {adjust: !D.adjust});
      return;
    }
    var r = M.act(D.st, b.id, a);
    if (r.why) { lines('sel', why(r)); return; }
    var o = {};
    if ('sel' in r) o.sel = r.sel;
    if (a === 'empty') o.adjust = false;
    if (!D.setState(r.st, o)) lines('', '');
    if (a === 'dup' && r.sel != null) reveal(r.sel);
  }
  $('selbar').addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('button[data-a]') : null;
    if (!b || !D.st || D.blocked) return;
    doAct(b.dataset.a);
  });
  // the Zoom slider: the picture follows it as it moves; the layout changes once, when it is let go
  zoomImg.addEventListener('input', function(){
    var b = D.selected();
    if (!b || D.typeOf(b) !== 'photo' || M.isHole(b) || !nodes[b.id]) return;
    D.blockTypes.photo.draw(nodes[b.id], M.merge(b, {zoom: M.zoomTo(zoomImg.value / 100)}), D.scale, true);
  });
  zoomImg.addEventListener('change', function(){
    var b = D.selected();
    if (!b || D.typeOf(b) !== 'photo' || M.isHole(b)) { D.render(); return; }
    var z = M.zoomTo(zoomImg.value / 100);
    if (!D.setState(function(st){ return M.patch(st, b.id, {zoom: z}); })) D.render();
  });

  $('slides-minus').addEventListener('click', function(){
    if (!D.st || D.blocked) return;
    var r = M.fewerSlides(D.st);
    if (r.why) { lines('slides', why(r)); return; }
    D.setState(r.st);
  });
  $('slides-plus').addEventListener('click', function(){
    if (!D.st || D.blocked) return;
    var r = M.moreSlides(D.st);
    if (r.why) { lines('slides', why(r)); return; }
    D.setState(r.st);
    stage.scrollLeft = stage.scrollWidth;       // the new slide is at the end: bring it into sight
  });
  Array.prototype.forEach.call(document.querySelectorAll('#g-bg .sw'), function(b){
    b.addEventListener('click', function(){ D.setState(function(st){ return M.setBg(st, b.dataset.c); }); });
  });
  var bgc = $('bgc');
  bgc.addEventListener('input', function(){ if (D.st && /^#[0-9a-fA-F]{6}$/.test(bgc.value)) strip.style.background = bgc.value; });
  bgc.addEventListener('change', function(){ if (!D.setState(function(st){ return M.setBg(st, bgc.value); })) D.render(); });
  bgc.addEventListener('blur', function(){ D.render(); });
  $('undo').addEventListener('click', function(){ D.undo(); });

  // ---------- how large the slides are drawn: the Size slider ----------
  // From every slide fitting across the window (its small end, which follows the window and the number of
  // slides) up to large. Dragging it draws the strip at that size at once, keeping the middle of what is showing
  // in the middle; its arrow keys step by a quarter (what Smaller and Bigger did), Home and End go to its ends.
  var sizeR = $('view-size');
  function room(){ return stage.clientWidth - 2 * wrap.offsetLeft; }        // the room across the stage, inside its padding
  function viewLow(){ return M.viewLow(room(), D.st ? D.st.slides : M.RULES.slides[0]); }
  function syncSize(){
    var lo = viewLow(), hi = M.RULES.view.max;
    if (Number(sizeR.min) !== lo) sizeR.min = String(lo);
    if (Number(sizeR.max) !== hi) sizeR.max = String(hi);
    var v = String(M.clamp(Math.round(view), lo, hi));
    if (sizeR.value !== v) sizeR.value = v;
  }
  function setView(px){
    if (!D.st || !(px > 0) || px === view) return;
    var old = D.scale, mid = stage.scrollLeft + stage.clientWidth / 2 - wrap.offsetLeft;
    view = px; D.scale = px / W;
    D.render();
    stage.scrollLeft = Math.max(0, mid * (D.scale / old) - stage.clientWidth / 2 + wrap.offsetLeft);
  }
  sizeR.addEventListener('input', function(){ setView(M.clamp(Number(sizeR.value) || view, M.RULES.view.min, M.RULES.view.max)); });
  sizeR.addEventListener('keydown', function(e){
    if (e.metaKey || e.ctrlKey || e.altKey || !D.st) return;
    var lo = viewLow(), to = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'PageUp') to = M.viewStep(view, 1, lo);
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown' || e.key === 'PageDown') to = M.viewStep(view, -1, lo);
    else if (e.key === 'Home') to = lo;
    else if (e.key === 'End') to = M.RULES.view.max;
    if (to === null) return;
    e.preventDefault();
    setView(to);
    syncSize();
  });
  window.addEventListener('resize', function(){ if (D.st) syncSize(); });
  D.setView = setView;
  D.view = function(){ return view; };
  function snapOn(){ return $('snap').checked; }

  D.on('render', function(){
    var st = D.st, b = D.selected(), off = D.blocked;
    $('slides-count').textContent = st.slides;
    $('slides-minus').disabled = off || st.slides <= M.RULES.slides[0];
    $('slides-plus').disabled = off || st.slides >= M.RULES.slides[1];
    $('slides-minus').title = '';     // at one slide the button is simply off (hers): one slide is a single post
    $('slides-plus').title = st.slides >= M.RULES.slides[1] ? WORDS.max : '';
    Array.prototype.forEach.call(document.querySelectorAll('#g-bg .sw'), function(x){ x.classList.toggle('on', x.dataset.c === st.bg); });
    if (document.activeElement !== bgc) bgc.value = st.bg;
    $('undo').disabled = off || !D.canUndo();
    syncSize();
    D.label(adjBtn, D.adjust ? WORDS.insideDone : WORDS.inside);
    adjBtn.classList.toggle('on', D.adjust);
    var photo = !!b && D.typeOf(b) === 'photo' && !M.isHole(b);
    adjBtn.disabled = !!b && !photo;
    zoomImg.disabled = !!b && !photo;
    zoomImg.value = String(Math.round((photo ? (b.zoom || 1) : 1) * 100));
    var u = M.used(st);
    Object.keys(tiles).forEach(function(n){ tiles[n].classList.toggle('used', !!u[n]); });
  });

  // ---------- where the strip is on screen ----------
  function stripPoint(cx, cy){ var r = strip.getBoundingClientRect(); return {x: (cx - r.left) / D.scale, y: (cy - r.top) / D.scale}; }
  function inside(r, x, y){ return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom; }
  function reveal(id){
    var b = D.st ? M.find(D.st, id) : null;
    if (!b) return;
    var s = D.scale, left = wrap.offsetLeft + b.x * s, right = wrap.offsetLeft + (b.x + b.w) * s;
    if (right - left > stage.clientWidth - 48 || left < stage.scrollLeft + 24) stage.scrollLeft = Math.max(0, left - 24);
    else if (right > stage.scrollLeft + stage.clientWidth - 24) stage.scrollLeft = right - stage.clientWidth + 24;
  }
  D.reveal = reveal;
  // The first slide that is wholly in sight (the one in the middle of what shows when none is): where a new
  // text box goes when nothing is selected.
  D.firstSlide = function(){
    if (!D.st) return 0;
    var one = W * D.scale, from = stage.scrollLeft - wrap.offsetLeft, k = Math.max(0, Math.ceil(from / one - 0.02));
    if (k > D.st.slides - 1 || (k + 1) * one > from + stage.clientWidth + 1) return D.viewSlide();
    return k;
  };
  D.slideOf = function(b){ return slideOf(b) - 1; };
  D.viewSlide = function(){
    if (!D.st) return 0;
    return M.clamp(Math.floor((stage.scrollLeft + stage.clientWidth / 2 - wrap.offsetLeft) / (W * D.scale)), 0, D.st.slides - 1);
  };

  // ---------- one press or drag at a time ----------
  // g: {start: pixels before it is a drag, lift(), move(), drop(), click(), clean(), redo(), clickOnly}
  var raf = null;
  function begin(e, g){
    G = g;
    G.pid = e.pointerId; G.cx0 = G.cx = e.clientX; G.cy0 = G.cy = e.clientY;
    G.alt = e.altKey; G.shift = e.shiftKey; G.on = false; G.band = 0; G.bandAt = 0;
  }
  // The strip scrolls sideways while a drag rests near either end of what is showing.
  function edge(){
    if (!G || !G.on || stage.scrollWidth <= stage.clientWidth + 1) return false;
    var r = stage.getBoundingClientRect(), band = 0, now = Date.now();
    if (G.cy >= r.top && G.cy <= r.bottom && G.cx >= r.left - 24 && G.cx <= r.right + 24) {
      if (G.cx < r.left + EDGE) band = -1; else if (G.cx > r.right - EDGE) band = 1;
    }
    if (band !== G.band) { G.band = band; G.bandAt = now; }
    if (!band || now - G.bandAt < DWELL || now - (G.scrolledAt || 0) < 12) return false;
    var was = stage.scrollLeft;
    stage.scrollLeft = was + band * STEP;
    G.scrolledAt = now;
    return stage.scrollLeft !== was;
  }
  // A resting pointer sends no moves, so the scrolling is also kept going frame by frame where frames run.
  // Where they do not (a page that is not in front), it still moves with every move of the pointer.
  function tick(){
    raf = null;
    if (!G || !G.on) return;
    if (edge()) G.move();
    raf = requestAnimationFrame(tick);
  }
  function finish(cancel){
    if (!G) return;
    var g = G; G = null;
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    document.body.classList.remove('d-dragging');
    if (g.clean) g.clean();
    if (!g.on) { if (!cancel && g.click) g.click(); return; }
    if (cancel) D.render(); else g.drop();
  }
  document.addEventListener('pointermove', function(e){
    if (!G || e.pointerId !== G.pid) return;
    if (e.pointerType === 'mouse' && e.buttons === 0) { finish(true); return; }     // the button was let go somewhere we never heard about
    G.cx = e.clientX; G.cy = e.clientY; G.alt = e.altKey; G.shift = e.shiftKey;
    if (!G.on) {
      var dx = G.cx - G.cx0, dy = G.cy - G.cy0;
      if (Math.sqrt(dx * dx + dy * dy) < G.start) return;                           // not a drag yet
      if (G.clickOnly) { var g = G; G = null; if (g.clean) g.clean(); return; }     // a finger scrolling the photos: not a click, not a drag
      G.on = true;
      document.body.classList.add('d-dragging');
      if (G.lift) G.lift();
      if (!raf) raf = requestAnimationFrame(tick);
    }
    G.move();
    if (edge()) G.move();
  });
  document.addEventListener('pointerup', function(e){ if (G && e.pointerId === G.pid) finish(false); });
  document.addEventListener('pointercancel', function(e){ if (G && e.pointerId === G.pid) finish(true); });
  window.addEventListener('blur', function(){ finish(true); });
  document.addEventListener('visibilitychange', function(){ if (document.hidden) finish(true); });
  document.addEventListener('keydown', function(e){
    if (G && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finish(true); }
  }, true);

  // ---------- the strip: select, move, resize, move the photo inside ----------
  stage.addEventListener('pointerdown', function(e){
    if (G || e.isPrimary === false || e.button !== 0 || !D.st || D.blocked) return;
    var hd = e.target.closest ? e.target.closest('.h') : null, bd = e.target.closest ? e.target.closest('.blk') : null;
    if (!hd && !bd) {
      // the bare strip, or the space around it: nothing is selected any more (the scroll bar is left alone)
      var sr = stage.getBoundingClientRect();
      if (e.clientY - sr.top > stage.clientTop + stage.clientHeight) return;
      if (D.sel != null) D.select(null);
      return;
    }
    e.preventDefault();                 // no text selection, no browser drag of the picture
    if (document.activeElement && document.activeElement !== document.body && document.activeElement.blur) document.activeElement.blur();
    var id = hd ? D.sel : Number(bd.dataset.id), b = M.find(D.st, id);
    if (!b) return;
    if (D.sel !== id) D.select(id);
    var kind = D.typeOf(b), T = D.blockTypes[kind], node = nodes[id];
    var mode = hd ? 'resize' : (D.adjust && T.pan && !M.isHole(b) ? 'pan' : 'move');
    var corner = hd ? hd.dataset.h : '', b0 = M.merge(b, {}), p0 = stripPoint(e.clientX, e.clientY), res = null;
    function show(){
      if (!res) return;
      var live = M.merge(b0, res);
      place(node, live, D.scale);
      T.draw(node, live, D.scale, true);
      placeSel(live, D.scale);
      showGuides(res.gx, res.gy);
    }
    begin(e, {
      start: MOVE_START, node: node,
      move: function(){
        var p = stripPoint(G.cx, G.cy), dx = p.x - p0.x, dy = p.y - p0.y;
        var o = {snap: snapOn() && !G.alt, thr: M.RULES.snapPx / D.scale, shift: G.shift, widthOnly: !!T.widthOnly, minW: T.minW, minH: T.minH, maxH: T.maxH};
        if (mode === 'move') res = M.move(D.st, b0, dx, dy, o);
        else if (mode === 'resize') res = M.resize(D.st, b0, corner, dx, dy, o);
        else { var nat = T.natural(node, b0); res = M.pan(b0, dx, dy, nat.w, nat.h); }
        show();
      },
      redo: show,
      clean: clearGuides,
      drop: function(){
        if (!res) { D.render(); return; }
        var p = mode === 'pan' ? {ox: res.ox, oy: res.oy} : mode === 'move' ? {x: res.x, y: res.y} : {x: res.x, y: res.y, w: res.w, h: res.h};
        if (!D.setState(function(st){ return M.patch(st, b0.id, p); })) D.render();
      }
    });
  });
  // Reached with the Tab key, a thing on the strip is selected, so its buttons and the arrow keys work on it
  // with no mouse. Return does what a double-click does: on a text box it puts the cursor in its words, on a
  // photo it turns "Move photo inside" on or off.
  strip.addEventListener('focusin', function(e){
    var bd = e.target.closest ? e.target.closest('.blk') : null;
    if (!bd || G || !D.st || D.blocked) return;
    var id = Number(bd.dataset.id);
    if (D.sel !== id && M.find(D.st, id)) { D.select(id); reveal(id); }
  });
  strip.addEventListener('keydown', function(e){
    if (e.key !== 'Enter' || e.metaKey || e.ctrlKey || e.altKey || !D.st || D.blocked || D.keysOff()) return;
    var bd = e.target.closest ? e.target.closest('.blk') : null, b = bd ? M.find(D.st, Number(bd.dataset.id)) : null;
    if (!b) return;
    var T = D.blockTypes[D.typeOf(b)];
    if (T.dblclick) { e.preventDefault(); D.select(b.id); T.dblclick(b); }
    else if (T.pan && !M.isHole(b)) { e.preventDefault(); D.select(b.id, {adjust: !D.adjust}); }
  });
  strip.addEventListener('dblclick', function(e){
    if (!D.st || D.blocked) return;
    var bd = e.target.closest ? e.target.closest('.blk') : null;
    var b = bd ? M.find(D.st, Number(bd.dataset.id)) : D.selected();
    if (!b) return;
    var kind = D.typeOf(b), T = D.blockTypes[kind];
    if (T.dblclick) { D.select(b.id); T.dblclick(b); return; }      // HOOK (stage C): a text box puts the cursor in its words
    if (!T.pan || M.isHole(b)) return;
    D.select(b.id, {adjust: D.sel === b.id ? !D.adjust : true});
  });
  // the wheel zooms the photo while it is being moved inside its frame (a run of turns is one Undo step)
  strip.addEventListener('wheel', function(e){
    var b = D.selected();
    if (!D.adjust || !b || D.typeOf(b) !== 'photo' || M.isHole(b) || D.blocked) return;
    e.preventDefault();
    if (!e.deltaY) return;
    D.setState(function(st){ return M.patch(st, b.id, {zoom: M.zoomBy(b.zoom, e.deltaY)}); }, {undo: 'zoom:' + b.id});
  }, {passive: false});

  // ---------- keys ----------
  document.addEventListener('keydown', function(e){
    if (G || !D.st || D.keysOff()) return;
    var t = e.target, tag = (t && t.tagName) || '', type = (t && t.type) || '';
    var range = tag === 'INPUT' && type === 'range';
    if (tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable) || (tag === 'INPUT' && !/^(range|checkbox|radio|color|button)$/.test(type))) return;
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && (e.key === 'z' || e.key === 'Z')) { e.preventDefault(); D.undo(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    // a tray photo reached with the Tab key is put in with Return, so nothing here needs a mouse
    if ((e.key === 'Enter' || e.key === ' ') && t && t.classList && t.classList.contains('th')) { e.preventDefault(); clickPhoto(Number(t.dataset.n)); return; }
    var b = D.selected();
    if (!b || D.blocked) return;
    if (e.key === 'Escape') { D.select(null); return; }
    if (range) return;                                  // the slider's own keys
    if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); doAct('del'); return; }
    var step = e.shiftKey ? M.RULES.nudgeBig : M.RULES.nudge;
    var mv = {ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step]}[e.key];
    if (!mv) return;
    e.preventDefault();
    // a key held down is one Undo step; each new press is its own
    D.setState(function(st){ return M.nudge(st, b.id, mv[0], mv[1]); }, {undo: 'nudge:' + b.id + ':' + e.key, fresh: !e.repeat});
  });
  // ---------- the tray ----------
  function tilePic(t, p){
    var img = t.querySelector('img');
    if (p.have) {
      if (!img) { img = document.createElement('img'); img.alt = ''; img.decoding = 'async'; img.loading = 'lazy'; t.insertBefore(img, t.firstChild); }
      var u = D.photoUrl(p.n, 's');
      if (img.getAttribute('src') !== u) img.setAttribute('src', u);
    }
    t.classList.toggle('cantread', !p.have && !!p.missing);
  }
  function buildTray(){
    thumbs.textContent = ''; tiles = {};
    var frag = document.createDocumentFragment();
    D.S.photos.forEach(function(p){
      var t = el('div', 'th' + (p.way === 'wide' ? ' wide' : ''));
      t.dataset.n = p.n; t.tabIndex = 0;
      t.setAttribute('role', 'button'); t.setAttribute('aria-label', 'Photo ' + p.n);
      t.appendChild(el('span', 'num', '#' + p.n));          // the photo's own number, as in the pickers
      t.appendChild(el('span', 'cant', WORDS.cantRead));
      t.appendChild(el('span', 'tick', '✓'));
      tilePic(t, p);
      tiles[p.n] = t;
      frag.appendChild(t);
    });
    thumbs.appendChild(frag);
    $('trayname').textContent = WORDS.allPhotos(D.S.total);
  }
  D.on('adopt', function(a){
    if (a.rebuild) { Object.keys(nodes).forEach(function(id){ nodes[id].remove(); }); nodes = {}; ready = {}; asked = {}; buildTray(); }
    else D.S.photos.forEach(function(p){ if (tiles[p.n]) tilePic(tiles[p.n], p); });
    if (!view) {
      // the first look: a slide about a third of the window tall, however many slides there are
      view = M.viewStart(room(), window.innerHeight);
      D.scale = view / W;
    }
  });
  D.on('photos', function(){ D.S.photos.forEach(function(p){ if (tiles[p.n]) tilePic(tiles[p.n], p); }); });

  function clickPhoto(n){
    if (!D.st || D.blocked || !D.by[n]) return;
    var r = M.clickPhoto(D.st, D.sel, n);
    if (r.why) { lines('tray', why(r)); return; }
    var added = D.sel == null || r.sel !== D.sel;
    if (!D.setState(r.st, {sel: added && !CLICK_ADD_SELECTS ? null : r.sel})) lines('', '');
    reveal(r.sel);
  }
  thumbs.addEventListener('pointerdown', function(e){
    if (G || e.isPrimary === false || e.button !== 0 || !D.st) return;
    var t = e.target.closest ? e.target.closest('.th') : null;
    if (!t) return;
    var n = Number(t.dataset.n), touch = e.pointerType === 'touch', lift = null, say = null, target = null, ox = 0, oy = 0;
    if (!D.by[n]) return;
    if (!touch) e.preventDefault();     // no text selection, no browser drag of the picture
    function show(){
      lift.style.transform = 'translate(' + (G.cx - ox * 1.06) + 'px,' + (G.cy - oy * 1.06) + 'px) scale(1.06)';
      clearDropMarks();
      target = null;
      var text = '';
      if (inside(stage.getBoundingClientRect(), G.cx, G.cy)) {
        var p = stripPoint(G.cx, G.cy);
        target = M.dropAt(D.st, p.x, p.y);
        if (target && target.kind === 'frame' && nodes[target.id]) { nodes[target.id].classList.add('droptarget'); text = WORDS.intoFrame; }
        else if (target) {
          slidemark.style.left = target.i * W * D.scale + 'px'; slidemark.style.width = W * D.scale + 'px'; slidemark.style.display = 'block';
          text = WORDS.ontoSlide(target.i + 1);
        }
      }
      say.textContent = text; say.classList.toggle('on', !!text);
    }
    begin(e, {
      // a finger on the tray scrolls the page, so a finger can only tap a photo, never lift it
      start: TRAY_START, clickOnly: touch || D.blocked,
      lift: function(){
        var r = t.getBoundingClientRect();
        ox = G.cx0 - r.left; oy = G.cy0 - r.top;
        lift = el('div', 'd-lift');
        lift.style.width = r.width + 'px'; lift.style.height = r.height + 'px';
        var pic = el('div', 'pic'), src = t.querySelector('img');
        if (src && src.getAttribute('src')) { var c = document.createElement('img'); c.alt = ''; c.src = src.getAttribute('src'); pic.appendChild(c); }
        say = el('span', 'say');
        lift.appendChild(pic); lift.appendChild(say);
        document.body.appendChild(lift);
        t.classList.add('dragging');
      },
      move: show, redo: show,
      clean: function(){ if (lift) lift.remove(); t.classList.remove('dragging'); clearDropMarks(); },
      click: function(){ clickPhoto(n); },
      drop: function(){
        if (!target || D.blocked) { D.render(); return; }
        if (target.kind === 'frame') {
          // onto a frame: that frame's photo is swapped for this one, its crop back to the middle
          if (!D.setState(function(st){ return M.swapPhoto(st, target.id, n); })) D.render();
          return;
        }
        var r = M.addPhoto(D.st, n, target.i);
        if (r.why) { lines('tray', why(r)); D.render(); return; }
        D.setState(r.st, {sel: r.sel});
      }
    });
  });

})();
"""
