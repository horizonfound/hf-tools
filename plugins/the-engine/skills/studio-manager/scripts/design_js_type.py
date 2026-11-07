#!/usr/bin/env python3
"""The carousel designer's rules for words, as one script with no page in it (design_page.py puts it on the page).

DESIGN_TYPE_JS makes window.DesignType (T): where the lines of a text box break, where each line sits, how tall
the box is, what a font's name may look like, the font string a browser is given, the address of a Google
Fonts stylesheet, a new text box, and the tidying of typed words. Nothing here touches a document: the one
thing it needs from a browser, how wide a run of letters is, is handed in as a function (measure). So
tests/design_check.py runs it by itself under the Mac's own JavaScript engine with a pretend ruler.

ONE function decides the line breaks, T.wrapLines. The screen and the saved slide both go through T.layout,
which calls it, so the words break in the same places in both.

    T.fontOk(name)                 letters, digits and single spaces, at most 50: the only names ever put in a
                                   font string or an address
    T.fontString(b, size)          'italic 700 96px "Playfair Display", Georgia, serif' (Georgia alone when the
                                   name is not a font's name)
    T.googleHref(base, name, weights)   the stylesheet's address, or '' when the name or the weights are not right
    T.tidyName(typed)              what they typed in the font search, as a font's name is written
    T.cleanText(typed)             line breaks made plain, tabs made spaces, other control characters dropped
    T.shown(b)                     the words as drawn (capitals when the box says so)
    T.wrapLines(text, width, measure) -> [{t, w}]
    T.layout(b, measure) -> {lines: [{t, w, x}], lh, h}     x = where the line starts inside the box
    T.baseline(lh, ascent, descent)     how far below a line's top its letters stand
    T.newText(id, slide, bg, defaults)  the box "+ Add text" makes
    T.freeSpot(b, others, height)  the y a new text box takes so it is never exactly on top of another
    T.style(b, key, value)         one change to a box's style, held inside the limits; null when it is not one
    T.sig(b)                       everything about a box that decides its lines, as one string
"""

DESIGN_TYPE_JS = r"""
(function(root){
  'use strict';
  var L0 = root && root.DESIGN_LIMITS ? root.DESIGN_LIMITS : null;      // the page's size (a story's: 1080 by 1920)
  var W = L0 && L0.w > 0 ? L0.w : 1080, H = L0 && L0.h > 0 ? L0.h : 1350;
  var FONT = /^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$/;
  var COLOR = /^#[0-9a-f]{6}$/;
  // Every number the words go by, in one place. The Assistant sends its own limits with the state (useLimits).
  var RULES = {
    fontMax: 50,              // letters in a font's name
    fallback: 'Georgia',      // what words are drawn in when their font can't be loaded
    size: [8, 600],           // the size of the letters, in slide pixels
    ls: [-20, 200],           // space between letters, in slide pixels
    lh: [0.5, 3],             // space between lines, times the size
    textMax: 2000,            // letters in one text box
    texts: 40,                // text boxes in one design
    wMin: 80,                 // the narrowest a text box may be
    hMax: 13500,              // the tallest a text box is ever written down as
    fresh: {size: 96, w: 820, y: 0.42, lh: 1.15, light: '#ffffff', dark: '#2a2622'},     // a new text box
    sizeSlider: [16, 400], lsSlider: [-10, 80], lhSlider: [80, 220]                       // what the three sliders reach
  };
  function useLimits(l){
    if (!l) return;
    if (l.size && l.size.length === 2) RULES.size = [l.size[0], l.size[1]];
    if (l.ls && l.ls.length === 2) RULES.ls = [l.ls[0], l.ls[1]];
    if (l.lh && l.lh.length === 2) RULES.lh = [l.lh[0], l.lh[1]];
    if (l.text > 0) RULES.textMax = l.text;
    if (l.texts > 0) RULES.texts = l.texts;
    if (l.text_w_min > 0) RULES.wMin = l.text_w_min;
    if (l.text_h_max > 0) RULES.hMax = l.text_h_max;
  }
  function clamp(v, a, b){ return Math.max(a, Math.min(b, v)); }
  function r2(v){ return Math.round(v * 100) / 100; }
  function r3(v){ return Math.round(v * 1000) / 1000; }

  // ---- a font's name ----
  function fontOk(name){ return typeof name === 'string' && name.length > 0 && name.length <= RULES.fontMax && FONT.test(name); }
  function fontString(b, size){
    var px = Number(size) > 0 ? Number(size) : RULES.fresh.size;
    return (b.italic === true ? 'italic ' : '') + (b.weight >= 700 ? 700 : 400) + ' ' + px + 'px ' +
           (fontOk(b.font) ? '"' + b.font + '", ' : '') + RULES.fallback + ', serif';
  }
  // The family part alone, for showing a font's name in its own face.
  function familyString(name){ return (fontOk(name) ? '"' + name + '", ' : '') + RULES.fallback + ', serif'; }
  function googleHref(base, name, weights){
    if (typeof base !== 'string' || !base || !fontOk(name)) return '';
    if (weights && !/^[1-9]00(?:;[1-9]00)*$/.test(weights)) return '';
    return base + '?family=' + name.replace(/ /g, '+') + (weights ? ':wght@' + weights : '') + '&display=swap';
  }
  // What they typed in the font search, as a font's name is written: single spaces, each word's first letter
  // a capital (the rest left as typed, so "EB Garamond" stays).
  function tidyName(typed){
    return String(typed == null ? '' : typed).replace(/\s+/g, ' ').trim().replace(/(^| )([a-z])/g, function(m, sp, ch){ return sp + ch.toUpperCase(); });
  }

  // ---- the words ----
  function cleanText(v){
    var s = String(v == null ? '' : v).replace(/\r\n?/g, '\n').replace(/\t/g, ' ').replace(/[\u0000-\u0009\u000b-\u001f\u007f]/g, '');
    if (s.length > RULES.textMax) {
      s = s.slice(0, RULES.textMax);
      var last = s.charCodeAt(s.length - 1);
      if (last >= 0xd800 && last <= 0xdbff) s = s.slice(0, -1);       // never half of a two-part letter
    }
    return s;
  }
  function shown(b){ var t = typeof b.text === 'string' ? b.text : ''; return b.upper === true ? t.toUpperCase() : t; }
  // A word's letters, each kept whole (an accent with its letter, an emoji with its parts).
  function letters(word){
    try {
      if (typeof Intl !== 'undefined' && Intl.Segmenter) {
        var out = [], it = new Intl.Segmenter(undefined, {granularity: 'grapheme'}).segment(word)[Symbol.iterator](), n;
        while (!(n = it.next()).done) out.push(n.value.segment);
        if (out.length) return out;
      }
    } catch (e) {}
    return Array.from(word);
  }
  // ONE place decides where lines break, for the screen and for the saved slide. measure(string) -> its
  // width. Words are kept whole and go to the next line when they do not fit; runs of spaces count as one; a
  // line break they typed is kept; a single word wider than the box is cut where it stops fitting.
  function wrapLines(text, width, measure){
    var out = [];
    String(text == null ? '' : text).split('\n').forEach(function(para){
      var words = para.split(/ +/).filter(function(w){ return w !== ''; });
      if (!words.length) { out.push({t: '', w: 0}); return; }
      var cur = '';
      words.forEach(function(word){
        var both = cur ? cur + ' ' + word : word;
        if (measure(both) <= width) { cur = both; return; }
        if (cur) { out.push({t: cur, w: measure(cur)}); cur = ''; }
        if (measure(word) <= width) { cur = word; return; }
        letters(word).forEach(function(ch){
          var more = cur + ch;
          if (!cur || measure(more) <= width) cur = more;
          else { out.push({t: cur, w: measure(cur)}); cur = ch; }
        });
      });
      out.push({t: cur, w: measure(cur)});
    });
    return out;
  }
  function heightOf(lines, b){
    var lh = Number(b.lh) > 0 ? Number(b.lh) : RULES.fresh.lh;
    return r2(clamp(Math.max(1, lines) * b.size * lh, 1, RULES.hMax));
  }
  // The lines of a text box, each with where it starts inside the box, and the box's height.
  function layout(b, measure){
    var lines = wrapLines(shown(b), b.w, measure), lh = b.size * (Number(b.lh) > 0 ? Number(b.lh) : RULES.fresh.lh);
    lines.forEach(function(ln){ ln.x = b.al === 'left' ? 0 : b.al === 'right' ? b.w - ln.w : (b.w - ln.w) / 2; });
    return {lines: lines, lh: lh, h: heightOf(lines.length, b)};
  }
  // How far below the top of its line a line's letters stand: the font's own height sits in the middle of the
  // line, as a browser lays text out. ascent, descent = the font's, at this size.
  function baseline(lh, ascent, descent){ return (lh - (ascent + descent)) / 2 + ascent; }
  function sig(b){
    return [b.font, b.size, b.weight >= 700 ? 700 : 400, b.italic === true ? 1 : 0, b.upper === true ? 1 : 0, b.al, b.ls || 0, b.lh, b.w, b.text].join('\u0001');
  }

  // ---- a new text box, and changes to one ----
  function isDark(color){
    var m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(color || ''));
    if (!m) return false;
    return 0.299 * parseInt(m[1], 16) + 0.587 * parseInt(m[2], 16) + 0.114 * parseInt(m[3], 16) < 128;
  }
  // In the middle of a slide, a little above half way down; white words on a dark background. A story's new text
  // (defaults from the Assistant: size, weight, line height, color, look, box color) starts the way hers does:
  // Classic, bold, size 72, line height 1.3, black on a white box.
  function newText(id, slide, bg, defaults){
    var f = RULES.fresh, d = defaults || {};
    var size = Number(d.size) > 0 ? clamp(Number(d.size), RULES.size[0], RULES.size[1]) : f.size;
    var lh = Number(d.lh) > 0 ? clamp(Number(d.lh), RULES.lh[0], RULES.lh[1]) : f.lh;
    var b = {id: id, type: 'text', text: typeof d.text === 'string' ? cleanText(d.text) : '', font: fontOk(d.font) ? d.font : RULES.fallback,
             size: size, weight: d.weight >= 700 ? 700 : 400, italic: false, upper: false, al: 'center', ls: 0, lh: lh,
             color: COLOR.test(String(d.color || '').toLowerCase()) ? String(d.color).toLowerCase() : isDark(bg) ? f.light : f.dark,
             x: slide * W + (W - f.w) / 2, y: r2(H * f.y), w: f.w, h: r2(size * lh)};
    if (d.look === 'plain' || d.look === 'box' || d.look === 'neon') b.look = d.look;
    if (COLOR.test(String(d.boxColor || '').toLowerCase())) b.boxColor = String(d.boxColor).toLowerCase();
    return b;
  }
  // Where a new text box goes so that it is never exactly on top of one that is already there: under the box
  // in its way (and under the next one, if that spot is taken too), or above them when the slide has no room
  // below. others = the text boxes already there; height = the slide's. -> the new box's y
  function freeSpot(b, others, height){
    var near = 12, y, o, n;
    function hit(at){
      for (var i = 0; i < others.length; i++) { if (Math.abs(others[i].x - b.x) < near && Math.abs(others[i].y - at) < near) return others[i]; }
      return null;
    }
    for (y = b.y, n = 0; (o = hit(y)) && n <= others.length; n++) y = r2(o.y + o.h);
    if (!hit(y) && y + b.h <= height) return y;
    for (y = b.y, n = 0; (o = hit(y)) && n <= others.length; n++) y = r2(o.y - b.h);
    if (!hit(y) && y >= 0) return y;
    return b.y;
  }
  // One change to a box's style: {key: the value held inside its limits}, or null when it is not a change
  // this page makes.
  function style(b, key, value){
    var p = {}, v;
    if (key === 'text') p.text = cleanText(value);
    else if (key === 'font') { if (!fontOk(value)) return null; p.font = value; }
    else if (key === 'size') { v = Number(value); if (!isFinite(v)) return null; p.size = r2(clamp(v, RULES.size[0], RULES.size[1])); }
    else if (key === 'ls') { v = Number(value); if (!isFinite(v)) return null; p.ls = r2(clamp(v, RULES.ls[0], RULES.ls[1])); }
    else if (key === 'lh') { v = Number(value); if (!isFinite(v)) return null; p.lh = r3(clamp(v, RULES.lh[0], RULES.lh[1])); }
    else if (key === 'weight') p.weight = value >= 700 ? 700 : 400;
    else if (key === 'italic') p.italic = value === true;
    else if (key === 'upper') p.upper = value === true;
    else if (key === 'al') { if (value !== 'left' && value !== 'center' && value !== 'right') return null; p.al = value; }
    else if (key === 'color') { v = String(value || '').toLowerCase(); if (!COLOR.test(v)) return null; p.color = v; }
    else if (key === 'boxColor') { v = String(value || '').toLowerCase(); if (!COLOR.test(v)) return null; p.boxColor = v; p.color = contrast(v); }
    else if (key === 'look') return lookChange(b, value);
    else return null;
    return p;
  }

  // ---- a story's text looks (hers, v19): Plain, Box (a rounded box behind each line), Neon (a glow) ----
  // Words that sit on a box of this color: black on a light box, white on a dark one.
  function contrast(c){
    var m = /^#?([0-9a-f]{6})$/i.exec(c || '');
    if (!m) return '#111111';
    var v = parseInt(m[1], 16), y = 0.299 * (v >> 16) + 0.587 * ((v >> 8) & 255) + 0.114 * (v & 255);
    return y > 150 ? '#111111' : '#ffffff';
  }
  // A color mixed toward white by k (the bright core of neon words).
  function lighten(c, k){
    var m = /^#?([0-9a-f]{6})$/i.exec(c || '');
    if (!m) return '#ffffff';
    var v = parseInt(m[1], 16), ch = [v >> 16, (v >> 8) & 255, v & 255].map(function(x){ return Math.round(x + (255 - x) * k); });
    return '#' + ch.map(function(x){ var h = x.toString(16); return h.length < 2 ? '0' + h : h; }).join('');
  }
  function boxPad(b){ return 0.3 * b.size; }
  function boxRad(b){ return 0.22 * b.size; }
  // The three blurs of the neon glow, as parts of the size, and how far toward white its core is.
  var NEON = {blurs: [0.06, 0.18, 0.36], core: 0.65};
  // The change one press of Plain, Box or Neon makes. Like Instagram: turning Box on makes the text's color the
  // box's (white when it was neon) and the words black or white on it; turning it off gives the words the box's color.
  function lookChange(b, look){
    if (look !== 'plain' && look !== 'box' && look !== 'neon') return null;
    var p = {look: look}, was = b.look || 'plain';
    if (look === 'box' && was !== 'box') { p.boxColor = b.color && was !== 'neon' ? String(b.color).toLowerCase() : '#ffffff'; p.color = contrast(p.boxColor); }
    else if (look !== 'box' && was === 'box') p.color = String(b.boxColor || b.color || '#111111').toLowerCase();
    return p;
  }

  root.DesignType = {
    W: W, H: H, RULES: RULES, useLimits: useLimits,
    fontOk: fontOk, fontString: fontString, familyString: familyString, googleHref: googleHref, tidyName: tidyName,
    cleanText: cleanText, shown: shown, letters: letters, wrapLines: wrapLines, heightOf: heightOf, layout: layout,
    baseline: baseline, sig: sig, isDark: isDark, newText: newText, freeSpot: freeSpot, style: style,
    contrast: contrast, lighten: lighten, boxPad: boxPad, boxRad: boxRad, NEON: NEON, lookChange: lookChange
  };
})(typeof window !== 'undefined' ? window : this);
"""
