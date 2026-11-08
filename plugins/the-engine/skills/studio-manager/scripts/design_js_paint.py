#!/usr/bin/env python3
"""The carousel designer's page: ONE way to draw a layout on a canvas.

DESIGN_PAINT_JS (put on the page by design_page.py after the text and brand-color scripts) makes
Designer.paint. A saved slide, the swipe preview and the little pictures in the "New design" gallery are all
drawn by the same function from the same layout, with the same rules the strip itself is drawn by:

    the background; then everything that reaches into the part being drawn, in list order (the last on top)
    a photo clipped to its frame and laid out by DesignModel.layoutImg from the LOADED picture's own size
    (the very function the strip uses), from the smallest made copy at least as large as it will be drawn
    a frame's border line, inside its edge, over the photo
    words by Designer.type.drawText (the same lines, at the same places, as the strip shows)

    Designer.paint.shelf()                      a place pictures are kept while something is drawn from them
    Designer.paint.slide(ctx, st, k, o)         slide k (from 0) -> a promise, kept when it is drawn
    Designer.paint.strip(ctx, st, o)            the whole strip (the gallery's little pictures)
    Designer.paint.keys(st, k, out, cap)        which pictures slide k is drawn from
    Designer.paint.letGo(shelf, keep)           let pictures go (all of them, or all but the ones in keep)

o: {out: canvas pixels for one slide pixel (1 for a saved slide), shelf, cap: the largest copy to ask for,
    soft: true = a photo that can't be read is drawn as a plain box instead of stopping the drawing,
    holes: true = empty frames are drawn as boxes (the gallery; a saved slide leaves them as background),
    seams: true = a thin line where one slide ends and the next begins (the gallery),
    fonts: false = the caller has already waited for the fonts (Save slides does, and asks about any that
    could not be loaded), text: false = the words are left out (a first look, while their fonts arrive)}

A picture that can't be loaded fails the drawing with {photo: its number} (unless soft). Nothing here waits on
a timer, keeps anything in the browser, or puts words on the page.
"""

DESIGN_PAINT_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, P = window.DesignPlan, W = M.W, H = M.H;
  var COLOR = /^#[0-9a-fA-F]{6}$/;

  function shelf(){ return {map: {}, count: 0, peak: 0}; }
  function drop(sh, key){
    var e = sh.map[key];
    if (!e) return;
    e.img.onload = null; e.img.onerror = null;
    try { e.img.removeAttribute('src'); } catch (x) {}
    delete sh.map[key];
    sh.count -= 1;
  }
  // A made copy of photo n, loaded once for as long as it is on the shelf. -> a promise of the picture
  function picture(sh, n, size){
    var key = n + ':' + size, e = sh.map[key];
    if (e) return e.p;
    e = sh.map[key] = {img: new Image(), p: null};
    sh.count += 1;
    if (sh.count > sh.peak) sh.peak = sh.count;
    e.p = new Promise(function(ok, bad){
      e.img.onload = function(){ if (e.img.naturalWidth > 0) ok(e.img); else { drop(sh, key); bad({photo: n}); } };
      e.img.onerror = function(){ drop(sh, key); bad({photo: n}); };     // off the shelf, so the next try asks afresh
      e.img.src = D.photoUrl(n, size);
    });
    e.p.then(null, function(){});       // whoever waits for it hears of a failure; nothing is left unheard
    return e.p;
  }
  function letGo(sh, keep){
    Object.keys(sh.map).forEach(function(k){ if (!(keep && keep[k])) drop(sh, k); });
  }
  // What a part of the strip is drawn from: [{b, n, size, key}], one for each frame with a photo in it.
  function wanted(blocks, out, cap){
    var sizes = (D.S && D.S.sizes) || {};
    return blocks.filter(function(b){ return M.isFrame(b) && b.n != null; }).map(function(b){
      var size = P.copyFor(b, D.by[b.n], out, sizes, cap);
      return {b: b, n: b.n, size: size, key: b.n + ':' + size};
    });
  }
  function keys(st, k, out, cap){
    var o = {};
    wanted(P.slideBlocks(st, k), out, cap).forEach(function(w){ o[w.key] = true; });
    return o;
  }
  // How far a block's ink can reach. A frame's is its own box (the photo is cut off at its edge). Words are
  // not cut off at their box on the strip, so they are not here either: a word wider than its box, a slanted
  // letter, a line taller than its row all show on whichever slide they run onto, in a saved slide as on screen.
  function inkBox(b){
    if (!M.isText(b)) return b;
    var pad = (b.size > 0 ? b.size : 0) * 0.6, lo = 0, hi = b.w, h = b.h;
    if (D.type) {
      var L = D.type.layout(b);
      L.lines.forEach(function(ln){ if (ln.t) { if (ln.x < lo) lo = ln.x; if (ln.x + ln.w > hi) hi = ln.x + ln.w; } });
      if (L.h > h) h = L.h;
    }
    return {x: b.x + lo - pad, y: b.y - pad, w: hi - lo + 2 * pad, h: h + 2 * pad};
  }
  function reaches(st, x0, width){
    return st.blocks.filter(function(b){ var k = inkBox(b); return k.x + k.w > x0 && k.x < x0 + width && k.y + k.h > 0 && k.y < H; });
  }

  // Everything is drawn in slide pixels; the canvas is told how many of its own pixels one of those is.
  function paint(ctx, st, blocks, pics, x0, width, o){
    ctx.save();
    ctx.setTransform(o.out, 0, 0, o.out, 0, 0);
    ctx.imageSmoothingEnabled = true;
    try { ctx.imageSmoothingQuality = 'high'; } catch (e) {}
    ctx.fillStyle = COLOR.test(st.bg || '') ? st.bg : '#ffffff';
    ctx.fillRect(0, 0, width, H);
    blocks.forEach(function(b){
      if (M.isText(b)) { if (D.type && o.text !== false) D.type.drawText(ctx, b, x0, 0); return; }
      var x = b.x - x0;
      if (b.n == null) {
        if (!o.holes) return;           // an empty frame leaves the background showing
        ctx.save();
        ctx.fillStyle = 'rgba(100,107,120,.22)'; ctx.fillRect(x, b.y, b.w, b.h);
        ctx.lineWidth = Math.max(6, 1.5 / o.out); ctx.strokeStyle = 'rgba(100,107,120,.6)';
        ctx.strokeRect(x + ctx.lineWidth / 2, b.y + ctx.lineWidth / 2, b.w - ctx.lineWidth, b.h - ctx.lineWidth);
        ctx.restore();
        return;
      }
      var img = pics[b.id];
      ctx.save();
      ctx.beginPath(); ctx.rect(x, b.y, b.w, b.h); ctx.clip();
      if (img) {
        // the same rule the strip lays a photo out by, from the loaded picture's own size
        var L = M.layoutImg(b, img.naturalWidth, img.naturalHeight);
        ctx.drawImage(img, x + L.left, b.y + L.top, L.iw, L.ih);
      } else { ctx.fillStyle = '#d9d2c7'; ctx.fillRect(x, b.y, b.w, b.h); }
      if (b.border && b.border.w > 0 && COLOR.test(b.border.color || '')) {
        var bw = Math.min(b.border.w, b.w / 2, b.h / 2);
        ctx.lineWidth = bw; ctx.strokeStyle = b.border.color;
        ctx.strokeRect(x + bw / 2, b.y + bw / 2, b.w - bw, b.h - bw);
      }
      ctx.restore();
    });
    if (o.seams) {
      ctx.fillStyle = 'rgba(47,124,246,.75)';
      var lw = 1.2 / o.out;
      for (var k = Math.floor(x0 / W) + 1; k * W < x0 + width; k++) ctx.fillRect(k * W - x0 - lw / 2, 0, lw, H);
    }
    ctx.restore();
  }
  // Draw the strip from x0, `width` slide pixels of it. The pictures are fetched first, then everything is
  // drawn in one go, in list order.
  function region(ctx, st, x0, width, o){
    o = o || {};
    if (!(o.out > 0)) o.out = 1;
    // the pictures are decided now (a frame's reach is its box); what is drawn is decided again once the fonts
    // are in, because how far words reach depends on the font they are measured in
    var sh = o.shelf || shelf(), want = wanted(reaches(st, x0, width), o.out, o.cap);
    var fonts = o.fonts === false || o.text === false || !D.type || !st.blocks.some(M.isText) ? Promise.resolve() : D.type.fonts.ready(st);
    return fonts.then(function(){
      return Promise.all(want.map(function(w){
        if (!D.by[w.n]) return o.soft ? null : Promise.reject({photo: w.n});
        return picture(sh, w.n, w.size).then(null, function(err){ if (o.soft) return null; throw err; });
      }));
    }).then(function(imgs){
      var pics = {};
      want.forEach(function(w, i){ pics[w.b.id] = imgs[i]; });
      paint(ctx, st, reaches(st, x0, width), pics, x0, width, o);
      return want.map(function(w){ return w.key; });
    });
  }

  D.paint = {
    shelf: shelf, picture: picture, letGo: letGo, keys: keys,
    slide: function(ctx, st, k, o){ return region(ctx, st, k * W, W, o); },
    strip: function(ctx, st, o){ return region(ctx, st, 0, st.slides * W, o); }
  };
})();
"""
