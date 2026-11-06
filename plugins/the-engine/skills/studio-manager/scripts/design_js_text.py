#!/usr/bin/env python3
"""The carousel designer's page: words on the slides, their fonts, and the font list.

DESIGN_TEXT_JS (put on the page by design_page.py after the strip's script) adds, through the places the core
keeps for it:

    "+ Add text": a text box in the middle of the slide in view, typed in the box in the bar for the selected
    thing (a double-click on the words puts the cursor there). Drag to move; a corner changes the box's WIDTH
    (its handles sit on its two sides) and its height follows the lines. Layering, Duplicate, Remove, Undo, the arrow keys and snapping are the
    strip's own and work on a text box as on a photo.
    Style: font, size (slider and number), bold, italic, all capitals, left / center / right, space between
    letters, space between lines, color.
    The font list: the Assistant's list in Serif / Sans / Script, each name in its own face (loaded as the list
    is opened or scrolled, never all at once), a search box that loads any Google Font by name, and "Yours".

SAME ON SCREEN AND SAVED. The lines come from DesignType.layout (design_js_type.py), measured on a canvas with
the box's own font and letter spacing. On screen every line is its own piece of the page, put at the measured
place at full slide size, and the whole box is scaled down to the strip; the browser never wraps a line itself.
Designer.type.drawText(ctx, block, offsetX) draws the very same lines on a canvas for a saved slide.

FONTS. A family the plugin carries is loaded from the Assistant itself (/design-font-file) and works with no
internet. Any other is asked of Google Fonts with a stylesheet <link> (the one thing this page may load from
the internet). A font's name is checked (DesignType.fontOk) before it goes into an address or a font string.
Nothing is drawn in a font before it has loaded; a font that cannot be loaded is drawn in Georgia and one plain
line on the page says so. Designer.type.fonts.ready() tells the saving part when every font is in, and which
fell back.

Nothing here waits on a timer to do its work (the one timer is a safety net that gives up on a font after
twelve seconds). Words are only ever put on the page with textContent.

For the next part (Save slides, templates):
    Designer.type.layout(b)              {lines: [{t, w, x}], lh, h, base}: the lines as drawn
    Designer.type.drawText(ctx, b, offsetX, offsetY)   draws block b on a canvas whose left edge is strip x = offsetX
    Designer.type.fit(st)                the layout with every text box's height made right (the same object
                                         when nothing changes); boxes whose font is still loading are left
    Designer.type.fonts.ready(st, {retry}) -> promise of {ready: true, fellBack: ['Lobster', ...]}
    Designer.type.edit(patch, o)         change the selected text box (used by the brand colors)
"""

DESIGN_TEXT_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, T = window.DesignType, $ = D.$, el = D.el;

  // Every line of words this part of the page says.
  var TW = D.WORDS.type = {
    addText: '+ Add text',
    group: 'Text', words: 'The words', wordsHint: 'Type your words',
    size: 'Size', sizeLabel: 'Text size', sizeNumber: 'Text size, as a number',
    bold: 'Bold', italic: 'Italic', upper: 'All capitals',
    left: 'Left', center: 'Center', right: 'Right',
    spacing: 'Spacing', spacingLabel: 'Space between letters', lines: 'Lines', linesLabel: 'Space between lines',
    color: 'Color', colorLabel: 'Text color',
    noBold: 'This font has no bold.',
    hint: 'Text. Type in the box next to “Text” here, or double-click the words. Drag to move it, or pull a side to make it wider or narrower.',
    hintFallback: function(font){ return 'This text is showing in Georgia for now, because “' + font + '” couldn’t be loaded. You can still type, move and style it.'; },
    manyTexts: function(k){ return 'A design holds up to ' + k + ' text boxes. Remove one first.'; },
    // the font list
    fontButton: 'Choose a font', search: 'Search, or type any Google font', searchLabel: 'Search fonts',
    yours: 'Yours', ownTag: 'works offline',
    loadFrom: function(name){ return 'Load “' + name + '” from Google Fonts'; },
    loading: 'Loading...',
    notFound: function(name){ return 'Couldn’t find “' + name + '” on Google Fonts. Check the spelling.'; },
    noNet: 'Can’t reach Google Fonts right now. Check the internet and try again.',
    pickerOffline: 'No internet right now. The fonts marked “works offline” still work. The others need the internet.',
    // the line on the page when words are not in their own font
    offline: function(names){ return 'No internet right now, so ' + list(names) + (names.length === 1 ? ' is' : ' are') + ' showing as Georgia. ' + (names.length === 1 ? 'It' : 'They') + ' will come back when you’re online.'; },
    cantLoad: function(names){ return 'Couldn’t load ' + list(names) + ' from Google Fonts, so ' + (names.length === 1 ? 'it is' : 'they are') + ' showing as Georgia. Pick another font for that text.'; },
    fallbackNow: function(names){ return 'Couldn’t load ' + list(names) + ' just now, so ' + (names.length === 1 ? 'it is' : 'they are') + ' showing as Georgia.'; }
  };
  function list(names){
    var q = names.map(function(n){ return '“' + n + '”'; });
    return q.length <= 1 ? q.join('') : q.slice(0, -1).join(', ') + ' and ' + q[q.length - 1];
  }

  // =====================================================================================================
  // fonts
  // =====================================================================================================
  var fam = {};             // family name -> {state: 'loading' | 'ok' | 'failed', bold, google, wait: []}
  var info = {};            // the Assistant's list: name -> {own, weights}
  var ownFaces = {};        // family -> [{weight, style, face}] (the files the plugin carries)
  var registered = false;
  var epoch = 0;            // goes up whenever a font arrives or gives up: measurements made before are thrown away
  var net = null;           // can Google Fonts be reached? null = not known yet
  var netAsking = false;
  var seen = {};            // font strings that have been drawn in their own face
  var tried = {}, nTried = 0;       // (font string + words) -> 'going' | 'done' | 'bad': letters still to arrive
  var GIVE_UP = 12000;      // a font that has said nothing after this long is treated as not loading (a safety net)
  var MC = document.createElement('canvas').getContext('2d');

  function fontsOf(){ return (D.S && D.S.fonts) || {groups: [], yours: [], faces: []}; }
  function learn(){
    info = {};
    (fontsOf().groups || []).forEach(function(g){ (g.fonts || []).forEach(function(f){ if (T.fontOk(f.name)) info[f.name] = {own: f.own === true, weights: typeof f.weights === 'string' ? f.weights : ''}; }); });
    if (registered || !window.FontFace || !document.fonts) return;
    registered = true;
    // the families the plugin carries: declared here from the Assistant's own files, never asked of Google
    (fontsOf().faces || []).forEach(function(f){
      if (!T.fontOk(f.family) || !/^[A-Za-z0-9-]{1,60}$/.test(f.file || '')) return;
      try {
        var face = new FontFace(f.family, 'url("/design-font-file?f=' + f.file + '")', {weight: String(f.weight === 700 ? 700 : 400), style: f.style === 'italic' ? 'italic' : 'normal'});
        document.fonts.add(face);
        (ownFaces[f.family] = ownFaces[f.family] || []).push({weight: f.weight === 700 ? 700 : 400, style: f.style === 'italic' ? 'italic' : 'normal', face: face});
      } catch (e) {}
    });
  }
  function settle(name, f, state, bold){
    if (f.state === state) return;
    if (f.state === 'ok') return;                       // once here, a late "no" changes nothing
    f.state = state;
    if (bold != null) f.bold = bold;
    clearTimeout(f.cap);
    if (state === 'ok' && f.google) net = true;
    var w = f.wait || [];
    f.wait = [];
    bump();
    w.forEach(function(fn){ fn(state); });
  }
  // Does the page now hold a bold face of this family? (Google gives only the weights a family has.)
  function hasFace(name, weight){
    var yes = false;
    try { document.fonts.forEach(function(x){ if (String(x.family).replace(/^["']|["']$/g, '') === name && String(x.weight) === String(weight)) yes = true; }); } catch (e) {}
    return yes;
  }
  function start(name, f){
    f.cap = setTimeout(function(){ if (f.state === 'loading') settle(name, f, 'failed'); }, GIVE_UP);
    // "no" is never said in the same breath as the asking: the asking can come from a drawing step, and a
    // font settling changes the layout
    var no = function(){ Promise.resolve().then(function(){ settle(name, f, 'failed'); }); };
    var i = info[name];
    if (i && i.own) {
      var faces = ownFaces[name] || [];
      var first = faces.filter(function(x){ return x.weight === 400 && x.style === 'normal'; })[0] || faces[0];
      if (!first) { no(); return; }
      first.face.load().then(function(){ settle(name, f, 'ok', faces.some(function(x){ return x.weight === 700; })); }, function(){ settle(name, f, 'failed'); });
      return;
    }
    f.google = true;
    // A family on the Assistant's list is asked for the weights the list gives. One loaded by name is asked
    // for bold as well, and taken without when Google has none for it.
    var asks = i ? [i.weights] : ['400;700', ''];
    (function go(k){
      var href = T.googleHref(fontsOf().google, name, asks[k]);
      if (!href) { no(); return; }
      var l = document.createElement('link');
      l.rel = 'stylesheet'; l.href = href;
      l.onload = function(){
        document.fonts.load('400 40px "' + name + '"', 'Aa').then(function(got){
          if (got && got.length) settle(name, f, 'ok', hasFace(name, 700));
          else { l.remove(); settle(name, f, 'failed'); }
        }, function(){ l.remove(); settle(name, f, 'failed'); });
      };
      l.onerror = function(){ l.remove(); if (k + 1 < asks.length) go(k + 1); else settle(name, f, 'failed'); };
      document.head.appendChild(l);
    })(0);
  }
  // Ask for a family (once). -> 'loading' | 'ok' | 'failed'
  function want(name){
    if (!T.fontOk(name)) return 'failed';
    if (name === T.RULES.fallback) return 'ok';
    var f = fam[name];
    if (!f) { f = fam[name] = {state: 'loading', bold: false, google: false, wait: []}; start(name, f); }
    return f.state;
  }
  function stateOf(name){ return name === T.RULES.fallback ? 'ok' : fam[name] ? fam[name].state : 'none'; }
  function settled(name){
    return new Promise(function(ok){
      var s = want(name);
      if (s !== 'loading') { ok(s); return; }
      fam[name].wait.push(ok);
    });
  }
  function hasBold(name){
    var i = info[name];
    if (i && !i.own) return i.weights.indexOf('700') >= 0;
    if (i && i.own) return (ownFaces[name] || []).some(function(x){ return x.weight === 700; });
    return !!(fam[name] && fam[name].state === 'ok' && fam[name].bold);
  }
  // Forget what could not be loaded, so it is asked for again the next time it is needed.
  function retry(){
    var any = false;
    Object.keys(fam).forEach(function(n){ if (fam[n].state === 'failed') { delete fam[n]; any = true; } });
    Object.keys(tried).forEach(function(k){ if (tried[k] === 'bad') { delete tried[k]; any = true; } });
    if (any) net = null;
    return any;
  }
  // Can Google Fonts be reached at all? A stylesheet that changes nothing on the page (it is for print only)
  // and has an address never asked for before, so no kept copy can answer for it.
  function askNet(){
    if (netAsking) return;
    var href = T.googleHref(fontsOf().google, 'Inter', '');
    if (!href) { net = false; return; }
    netAsking = true;
    var l = document.createElement('link');
    l.rel = 'stylesheet'; l.media = 'print'; l.href = href + '&text=' + Date.now().toString(36);
    var done = function(v){ l.remove(); netAsking = false; net = v; bump(); netWait.splice(0).forEach(function(fn){ fn(v); }); };
    l.onload = function(){ done(true); };
    l.onerror = function(){ done(false); };
    document.head.appendChild(l);
  }
  var netWait = [];
  function reach(){ return new Promise(function(ok){ if (net !== null) { ok(net); return; } netWait.push(ok); askNet(); }); }

  // Is this box's font here, in this weight and slant, for these very letters?
  // 'ready' | 'wait' (nothing is drawn yet) | 'fallback' (Georgia, and the page says so)
  function status(b){
    if (!T.fontOk(b.font)) return 'fallback';
    var s = want(b.font);
    if (s === 'loading') return 'wait';
    if (s === 'failed') return 'fallback';
    if (b.font === T.RULES.fallback) return 'ready';
    var fs = T.fontString(b, 40), text = T.shown(b) || 'Aa', key = fs + '\u0001' + text, ok = true;
    try { ok = document.fonts.check(fs, text); } catch (e) { ok = true; }
    if (ok) { seen[fs] = true; return 'ready'; }
    if (tried[key] === 'bad') return 'fallback';
    if (tried[key] === 'done') { seen[fs] = true; return 'ready'; }
    if (!tried[key]) {
      if (nTried > 300) { tried = {}; nTried = 0; }
      tried[key] = 'going'; nTried += 1;
      document.fonts.load(fs, text).then(function(){ tried[key] = 'done'; bump(); }, function(){ tried[key] = 'bad'; bump(); });
    }
    // already drawn in this face: it stays while a few more letters arrive
    return seen[fs] ? 'ready' : 'wait';
  }
  function fellBack(st){
    var out = [];
    ((st || D.st || {}).blocks || []).forEach(function(b){ if (M.isText(b) && status(b) === 'fallback' && out.indexOf(b.font) < 0) out.push(b.font); });
    return out;
  }
  // For the saving part: every font this layout uses is in, or has been given up on.
  function ready(st, o){
    st = st || D.st;
    if (o && o.retry && retry()) bump();
    var jobs = ((st || {}).blocks || []).filter(M.isText).map(function(b){
      if (!T.fontOk(b.font)) return Promise.resolve();
      return settled(b.font).then(function(s){
        if (s !== 'ok' || b.font === T.RULES.fallback) return null;
        var fs = T.fontString(b, 40), text = T.shown(b) || 'Aa', key = fs + '\u0001' + text;
        return document.fonts.load(fs, text).then(function(){ if (tried[key] !== 'done') { tried[key] = 'done'; } }, function(){ tried[key] = 'bad'; });
      });
    });
    return Promise.all(jobs).then(function(){
      bump();
      return {ready: true, fellBack: fellBack(st)};
    });
  }

  // =====================================================================================================
  // measuring, laying out, drawing
  // =====================================================================================================
  // The canvas is told to kern as the page does. Left to itself ('auto') a canvas skips the kerning between a
  // letter and a space (", " in Inter Bold is 3 pixels wider), and a line would measure wider than it shows.
  function likePage(ctx, b){
    ctx.font = T.fontString(b, b.size);
    try { ctx.letterSpacing = (b.ls || 0) + 'px'; } catch (e) {}
    try { ctx.fontKerning = 'normal'; } catch (e) {}
    // and to shape the words as the page does: left at 'auto' a canvas leaves out the joins a script font
    // makes across a space (a long line in Caveat came out up to 9 pixels wider than the page shows it)
    try { ctx.textRendering = 'optimizeLegibility'; } catch (e) {}
  }
  function measurer(b){
    likePage(MC, b);
    return function(s){ return MC.measureText(s).width; };
  }
  var cache = {}, cacheN = 0, cacheAt = -1;
  // The lines of a box as they are drawn, on screen and in a saved slide. base = how far below each line's
  // top its letters stand (null when this browser cannot say: the middle of the line is used instead).
  function layoutOf(b){
    if (cacheAt !== epoch || cacheN > 400) { cache = {}; cacheN = 0; cacheAt = epoch; }
    var k = T.sig(b), L = cache[k];
    if (L) return L;
    L = T.layout(b, measurer(b));
    var m = MC.measureText('Hg');
    L.base = typeof m.fontBoundingBoxAscent === 'number' && typeof m.fontBoundingBoxDescent === 'number'
      ? T.baseline(L.lh, m.fontBoundingBoxAscent, m.fontBoundingBoxDescent) : null;
    cache[k] = L; cacheN += 1;
    return L;
  }
  function colorOf(b){ return /^#[0-9a-fA-F]{6}$/.test(b.color || '') ? b.color : T.RULES.fresh.dark; }
  // Draw a text box on a canvas: the same lines, at the same places, as the screen shows. The canvas's left
  // edge is strip x = offsetX (a slide's own left edge) and its top is strip y = offsetY (0).
  function drawText(ctx, b, offsetX, offsetY){
    var L = layoutOf(b), x0 = b.x - (offsetX || 0), y0 = b.y - (offsetY || 0);
    ctx.save();
    likePage(ctx, b);
    ctx.fillStyle = colorOf(b);
    ctx.textAlign = 'left';
    ctx.direction = 'ltr';
    ctx.textBaseline = L.base === null ? 'middle' : 'alphabetic';
    L.lines.forEach(function(ln, i){
      if (ln.t) ctx.fillText(ln.t, x0 + ln.x, y0 + i * L.lh + (L.base === null ? L.lh / 2 : L.base));
    });
    ctx.restore();
    return L;
  }
  // Every text box's height made what its lines come to (and kept on the strip). The same layout back when
  // nothing changes. A box whose font is still on its way is left until it arrives.
  function fit(st){
    var out = st;
    st.blocks.forEach(function(b){
      if (!M.isText(b) || status(b) === 'wait') return;
      var h = layoutOf(b).h;
      if (h === b.h) return;
      var c = M.clampXY(b.x, b.y, b.w, h, st.slides);
      out = M.patch(out, b.id, {h: h, x: M.r2(c.x), y: M.r2(c.y)});
    });
    return out;
  }
  function refit(){
    if (!D.st || D.blocked) return false;
    var next = fit(D.st);
    return next !== D.st && D.setState(next, {undo: false});
  }
  // A font arrived or gave up: measure again, set the heights right, draw.
  function bump(){
    epoch += 1;
    if (!D.st) return;
    if (!refit()) D.render();
    if (open) showFaces();
  }
  if (document.fonts && document.fonts.addEventListener) {
    document.fonts.addEventListener('loadingdone', bump);
    document.fonts.addEventListener('loadingerror', bump);
  }
  window.addEventListener('online', function(){ if (retry()) bump(); });

  // ---------- the text kind of block ----------
  var drawn = new WeakMap();        // a box's element -> what its lines were last built from
  D.blockTypes.text = {
    widthOnly: true, minW: T.RULES.wMin,
    make: function(){ var n = el('div', 'blk words'); n.appendChild(el('div', 'tx-in')); return n; },
    // live = true while the box is being dragged or resized: b is then a stand-in the drag made.
    draw: function(node, b, s, live){
      var inner = node.firstChild, state = status(b);
      inner.style.transform = 'scale(' + s + ')';
      node.classList.toggle('blank', !/\S/.test(b.text || ''));
      if (state === 'wait') {
        // its font is on its way: nothing is drawn in another font meanwhile (what was there stays as it was)
        if (!drawn.has(node)) inner.style.visibility = 'hidden';
        return;
      }
      var L = layoutOf(b), key = T.sig(b) + '\u0001' + colorOf(b) + '\u0001' + epoch;
      if (drawn.get(node) !== key) {
        inner.textContent = '';
        var font = T.fontString(b, b.size), color = colorOf(b);
        L.lines.forEach(function(ln, i){
          var e = el('div', 'tx-ln', ln.t);         // textContent: the words are never read as markup
          e.style.font = font;
          e.style.fontKerning = 'normal';
          e.style.lineHeight = L.lh + 'px';
          e.style.letterSpacing = (b.ls || 0) + 'px';
          e.style.color = color;
          e.style.left = ln.x + 'px'; e.style.top = i * L.lh + 'px'; e.style.height = L.lh + 'px';
          inner.appendChild(e);
        });
        drawn.set(node, key);
      }
      inner.style.visibility = '';
      inner.style.width = b.w + 'px'; inner.style.height = L.h + 'px';
      node.style.height = L.h * s + 'px';
      node.classList.toggle('fellback', state === 'fallback');
      if (live) b.h = L.h;            // so the blue box follows the lines while a corner is pulled
    },
    dblclick: function(){ focusWords(); }
  };
  D.hints.text = function(b){ return status(b) === 'fallback' ? TW.hintFallback(b.font) : TW.hint; };

  // A change the strip made (a corner pulled, a duplicate) may leave a text box's height behind its lines:
  // it is put right at once, as part of the same step.
  D.on('change', function(){ refit(); });
  D.on('adopt', function(){ learn(); T.useLimits(D.S.limits); D.blockTypes.text.minW = T.RULES.wMin; setLimits(); });
  D.on('design', function(){ Promise.resolve().then(function(){ refit(); }); });

  // =====================================================================================================
  // the buttons
  // =====================================================================================================
  function selText(){ var b = D.selected(); return b && M.isText(b) ? b : null; }
  // Change the selected text box. p = {key: value, ...}; the height follows in the same step.
  function edit(p, o){
    var b = selText();
    if (!b || D.blocked || !p) return false;
    return D.setState(function(st){ return fit(M.patch(st, b.id, p)); }, o);
  }
  // A run of changes from one control (a slider pulled, words typed) is one Undo step; touching the control
  // again starts a new one.
  var armed = {};
  function arm(name){ armed[name] = true; }
  function run(name){ var b = selText(), fresh = armed[name] !== false; armed[name] = false; return {undo: name + ':' + (b ? b.id : 0), fresh: fresh}; }
  function change(key, value, name){
    var b = selText();
    if (!b) return false;
    var p = T.style(b, key, value);
    return p ? edit(p, name ? run(name) : undefined) : false;
  }

  // + Add text, in the row of tools for the whole carousel, before the Size slider
  var gAdd = D.tools.group('g-text', '', 'tools-main', 'g-view');
  var addBtn = D.tools.button(gAdd, TW.addText, 'add-text');
  // the line a press brings is in the selection bar's first line, with the other lines a press brings
  var addLine = el('span', 'gline'); addLine.id = 'text-line'; addLine.setAttribute('role', 'status');
  D.selbar.cap(addLine, 'line');
  addBtn.addEventListener('click', function(){
    if (!D.st || D.blocked) return;
    D.say(addLine, '');
    if (D.st.blocks.length >= M.RULES.blocks) { D.say(addLine, D.WORDS.many); return; }
    if (D.st.blocks.filter(M.isText).length >= T.RULES.texts) { D.say(addLine, TW.manyTexts(T.RULES.texts)); return; }
    // on the slide of whatever is selected (they are working there), else on the first slide in sight
    var cur = D.selected();
    var b = T.newText(M.nextId(D.st), cur ? D.slideOf(cur) : D.firstSlide(), D.st.bg, D.S.text);
    D.setState(function(st){
      var next = fit(M.merge(st, {blocks: st.blocks.concat([b])})), mine = M.find(next, b.id);
      // never exactly on top of a text box that is already there: under it (above it when there is no room)
      var y = T.freeSpot(mine, st.blocks.filter(M.isText), M.H);
      return y === mine.y ? next : M.patch(next, b.id, {y: y});
    }, {sel: b.id, adjust: false});
    D.reveal(b.id);
    focusWords();
  });
  D.on('change', function(){ D.say(addLine, ''); });
  D.on('render', function(){ addBtn.disabled = !!D.blocked; });

  // the bar for a selected text box
  var isText = function(kind){ return kind === 'text'; };
  var g1 = D.selbar.group('sel-text', TW.group, isText);
  var ta = el('textarea', 'tx-words'); ta.id = 't-words'; ta.rows = 1; ta.spellcheck = true;
  ta.setAttribute('aria-label', TW.words); ta.placeholder = TW.wordsHint;
  g1.appendChild(ta);
  var fp = el('span', 'fp');
  var fontBtn = el('button', 'tb fp-btn'); fontBtn.type = 'button'; fontBtn.id = 'font-btn';
  fontBtn.setAttribute('aria-haspopup', 'listbox'); fontBtn.setAttribute('aria-label', TW.fontButton); fontBtn.title = TW.fontButton;
  var pop = el('div', 'fp-pop'); pop.id = 'font-panel'; pop.hidden = true;
  var search = el('input', 'fp-search'); search.type = 'text'; search.id = 'font-search'; search.maxLength = 60;
  search.placeholder = TW.search; search.setAttribute('aria-label', TW.searchLabel);
  search.autocomplete = 'off'; search.spellcheck = false;
  var popLine = el('p', 'fp-line'); popLine.id = 'font-line'; popLine.setAttribute('role', 'status'); popLine.hidden = true;
  var fontList = el('div', 'fp-list'); fontList.id = 'font-list'; fontList.setAttribute('role', 'listbox');
  // the line sits UNDER the list, so its coming never moves a font's name from under the pointer
  pop.appendChild(search); pop.appendChild(fontList); pop.appendChild(popLine);
  fp.appendChild(fontBtn); fp.appendChild(pop);
  g1.appendChild(fp);
  g1.appendChild(el('span', 'lbl', TW.size));
  function slider(id, label, lo, hi){
    var r = el('input'); r.type = 'range'; r.id = id; r.min = String(lo); r.max = String(hi); r.setAttribute('aria-label', label); r.title = label;
    return r;
  }
  var sizeR = slider('t-size', TW.sizeLabel, T.RULES.sizeSlider[0], T.RULES.sizeSlider[1]);
  var sizeN = el('input', 'tx-num'); sizeN.type = 'number'; sizeN.id = 't-size-n'; sizeN.setAttribute('aria-label', TW.sizeNumber);
  g1.appendChild(sizeR); g1.appendChild(sizeN);

  // (the color comes before the style buttons so the bar is two rows at a usual width, as it is for a photo)
  var g3 = D.selbar.group('sel-color', TW.color, isText);
  var colorIn = el('input'); colorIn.type = 'color'; colorIn.id = 't-color'; colorIn.setAttribute('aria-label', TW.colorLabel); colorIn.title = TW.colorLabel;
  g3.appendChild(colorIn);
  var tBrand = el('span', 'bc-row small'); tBrand.id = 't-brand';       // the brand colors, filled in by their own part
  g3.appendChild(tBrand);

  var g2 = D.selbar.group('sel-style', '', isText);
  function tbtn(text, t, v, label){
    var b = el('button', 'tb', text); b.type = 'button'; b.dataset.t = t;
    if (v) b.dataset.v = v;
    if (label) { b.setAttribute('aria-label', label); b.title = label; }
    g2.appendChild(b);
    return b;
  }
  var boldBtn = tbtn('B', 'weight', '', TW.bold); boldBtn.classList.add('tx-b');
  var italBtn = tbtn('I', 'italic', '', TW.italic); italBtn.classList.add('tx-i');
  var upBtn = tbtn('AA', 'upper', '', TW.upper);
  var alBtns = [tbtn(TW.left, 'al', 'left'), tbtn(TW.center, 'al', 'center'), tbtn(TW.right, 'al', 'right')];
  // each label stays beside its slider when the group wraps on a narrow window (a pair never breaks in two)
  function pair(words, r){ var p = el('span', 'pair'); p.appendChild(el('span', 'lbl', words)); p.appendChild(r); g2.appendChild(p); }
  var lsR = slider('t-ls', TW.spacingLabel, T.RULES.lsSlider[0], T.RULES.lsSlider[1]);
  pair(TW.spacing, lsR);
  var lhR = slider('t-lh', TW.linesLabel, T.RULES.lhSlider[0], T.RULES.lhSlider[1]);
  pair(TW.lines, lhR);

  function setLimits(){
    ta.maxLength = T.RULES.textMax;
    sizeN.min = String(T.RULES.size[0]); sizeN.max = String(T.RULES.size[1]);
  }
  function focusWords(){
    if (!selText()) return;
    arm('type');
    try { ta.focus({preventScroll: false}); ta.select(); } catch (e) {}
  }

  // the words
  ta.addEventListener('focus', function(){ arm('type'); });
  ta.addEventListener('input', function(){
    var clean = T.cleanText(ta.value);
    if (clean !== ta.value) { var at = ta.selectionStart; ta.value = clean; try { ta.setSelectionRange(Math.min(at, clean.length), Math.min(at, clean.length)); } catch (e) {} }
    if (!change('text', clean, 'type')) D.render();
  });
  ta.addEventListener('keydown', function(e){ if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); ta.blur(); } });
  // size, spacing, lines: the words follow the slider as it moves
  [[sizeR, 'size', 1, 'size'], [lsR, 'ls', 1, 'ls'], [lhR, 'lh', 0.01, 'lh']].forEach(function(x){
    var r = x[0];
    r.addEventListener('pointerdown', function(){ arm(x[3]); });
    r.addEventListener('keydown', function(e){ if (!e.repeat) arm(x[3]); });
    r.addEventListener('input', function(){ if (!change(x[1], Number(r.value) * x[2], x[3])) D.render(); });
  });
  sizeN.addEventListener('focus', function(){ arm('sizen'); });
  sizeN.addEventListener('input', function(){
    var v = Number(sizeN.value);
    if (sizeN.value !== '' && v >= T.RULES.size[0] && v <= T.RULES.size[1]) change('size', v, 'sizen');
  });
  sizeN.addEventListener('blur', function(){ D.render(); });
  sizeN.addEventListener('keydown', function(e){ if (e.key === 'Enter' || e.key === 'Escape') { e.preventDefault(); sizeN.blur(); } });
  colorIn.addEventListener('pointerdown', function(){ arm('color'); });
  colorIn.addEventListener('focus', function(){ arm('color'); });
  colorIn.addEventListener('input', function(){ change('color', colorIn.value, 'color'); });
  colorIn.addEventListener('change', function(){ if (!change('color', colorIn.value, 'color')) D.render(); });
  // bold, italic, capitals, left / center / right
  $('selbar').addEventListener('click', function(e){
    var bt = e.target.closest ? e.target.closest('button[data-t]') : null, b = selText();
    if (!bt || !b || bt.disabled) return;
    var t = bt.dataset.t;
    if (t === 'weight') change('weight', b.weight >= 700 ? 400 : 700);
    else if (t === 'italic') change('italic', !b.italic);
    else if (t === 'upper') change('upper', !b.upper);
    else if (t === 'al') change('al', bt.dataset.v);
  });

  // the controls show the selected box
  function setVal(input, v){ v = String(v); if (input.value !== v) input.value = v; }
  var selbox = document.querySelector('#over .selbox');
  D.on('render', function(){
    fontLine();
    var b = selText();
    // a text box changes in width only, so its handles sit on its two sides (the left one and the right one)
    if (selbox) selbox.classList.toggle('tx-sides', !!b);
    if (!b) { if (open) closeFonts(); return; }
    if (ta.value !== b.text) ta.value = b.text;
    setVal(sizeR, M.clamp(Math.round(b.size), T.RULES.sizeSlider[0], T.RULES.sizeSlider[1]));
    if (document.activeElement !== sizeN) setVal(sizeN, b.size);
    setVal(lsR, M.clamp(Math.round(b.ls || 0), T.RULES.lsSlider[0], T.RULES.lsSlider[1]));
    setVal(lhR, M.clamp(Math.round(b.lh * 100), T.RULES.lhSlider[0], T.RULES.lhSlider[1]));
    setVal(colorIn, colorOf(b));
    fontBtn.textContent = b.font + ' ▾';
    fontBtn.setAttribute('aria-label', TW.fontButton + ': ' + b.font);        // its words, and what the press does
    fontBtn.style.fontFamily = stateOf(b.font) === 'ok' ? T.familyString(b.font) : '';
    var bold = b.weight >= 700, can = hasBold(b.font) || bold;
    boldBtn.classList.toggle('on', bold);
    boldBtn.disabled = !can;
    boldBtn.title = can ? TW.bold : TW.noBold;
    italBtn.classList.toggle('on', !!b.italic);
    upBtn.classList.toggle('on', !!b.upper);
    alBtns.forEach(function(x){ x.classList.toggle('on', x.dataset.v === (b.al || 'center')); });
  });

  // The line on the page when some words are not in their own font. It sits with the page's other lines in
  // the bar at the bottom of the window: always in sight, and its coming and going moves no button.
  var lf = el('p', 'd-note'); lf.id = 'l-fonts'; lf.hidden = true; lf.setAttribute('role', 'status');
  var after = $('d-note');
  after.parentNode.insertBefore(lf, after.nextSibling);
  function fontLine(){
    var names = fellBack(D.st), text = '';
    if (names.length) {
      var google = names.some(function(n){ return !(info[n] && info[n].own); });
      if (google && net === null) askNet();
      text = !google ? TW.fallbackNow(names) : net === false ? TW.offline(names) : net === true ? TW.cantLoad(names) : TW.fallbackNow(names);
    }
    if (lf.textContent !== text) lf.textContent = text;
    lf.hidden = !text;
  }

  // =====================================================================================================
  // the font list
  // =====================================================================================================
  var open = false;
  D.quiet.push(function(){ return open; });
  function closeFonts(){ if (!open) return; open = false; pop.hidden = true; }
  function openFonts(){
    if (!selText() || D.blocked) return;
    open = true;
    retry();                      // what could not be loaded before is tried again as it comes into sight
    pop.hidden = false;
    pop.style.left = '0px';
    search.value = '';
    build();
    // kept inside the window at any width
    var r = pop.getBoundingClientRect(), over = r.right - (document.documentElement.clientWidth - 8);
    if (over > 0) pop.style.left = -Math.min(over, Math.max(0, r.left - 8)) + 'px';
    D.focus(search);              // without moving the page
  }
  function build(){
    var q = search.value.replace(/\s+/g, ' ').trim().toLowerCase(), b = selText(), F = fontsOf(), exact = false;
    fontList.textContent = '';
    var groups = [{name: TW.yours, fonts: (F.yours || []).map(function(n){ return {name: n, own: false}; })}].concat(F.groups || []);
    groups.forEach(function(g){
      var hits = (g.fonts || []).filter(function(f){ return T.fontOk(f.name) && (!q || f.name.toLowerCase().indexOf(q) >= 0); });
      if (!hits.length) return;
      fontList.appendChild(el('div', 'fp-grp', g.name));
      hits.forEach(function(f){
        if (f.name.toLowerCase() === q) exact = true;
        var bt = el('button', 'fp-it'); bt.type = 'button'; bt.dataset.font = f.name; bt.setAttribute('role', 'option');
        bt.appendChild(el('span', 'fp-name', f.name));
        if (f.own === true) bt.appendChild(el('span', 'fp-tag', TW.ownTag));
        if (b && b.font === f.name) { bt.classList.add('cur'); bt.setAttribute('aria-selected', 'true'); }
        fontList.appendChild(bt);
      });
    });
    if (q && !exact) {
      var name = T.tidyName(search.value);
      var lb = el('button', 'fp-it fp-load', TW.loadFrom(name)); lb.type = 'button'; lb.dataset.load = name;
      fontList.appendChild(lb);
    }
    showFaces();
  }
  // The names in sight (and a little below) are shown in their own faces. Each family is asked for only when
  // its name first comes into sight, so opening the list never asks for thirty at once.
  function showFaces(){
    if (!open) return;
    var top = fontList.scrollTop, bottom = top + fontList.clientHeight + 110;      // the list is its rows' own frame of reference
    Array.prototype.forEach.call(fontList.querySelectorAll('.fp-it[data-font]'), function(bt){
      var name = bt.dataset.font, y = bt.offsetTop, s = stateOf(name);
      if (s === 'none' && y + bt.offsetHeight >= top && y <= bottom) s = want(name);
      bt.firstChild.style.fontFamily = s === 'ok' ? T.familyString(name) : '';
      bt.classList.toggle('fp-cant', s === 'failed');
    });
    var down = Object.keys(fam).some(function(n){ return fam[n].state === 'failed' && fam[n].google; });
    if (down && net === null) askNet();
    var text = down && net === false ? TW.pickerOffline : '';
    if (popLine.textContent !== text) popLine.textContent = text;
    popLine.hidden = !text;
  }
  function pick(name, id){
    var b = selText();
    if (!b || (id != null && b.id !== id) || !T.fontOk(name)) return;
    closeFonts();
    var p = {font: name};
    if (b.weight >= 700 && !hasBold(name) && (info[name] || stateOf(name) === 'ok')) p.weight = 400;       // a font with no bold
    edit(p);
  }
  // A font loaded by its name: it is used, and kept under "Yours", only once it has really loaded.
  function loadByName(name, bt){
    var b = selText(), id = b ? b.id : null;
    if (!T.fontOk(name)) { bt.textContent = TW.notFound(name); return; }
    bt.disabled = true; bt.textContent = TW.loading;
    if (fam[name] && fam[name].state === 'failed') delete fam[name];
    settled(name).then(function(s){
      if (s === 'ok') {
        fetch('/design-font', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({add: name})})
          .then(function(r){ return r.json(); })
          .then(function(j){
            if (j && Array.isArray(j.yours) && D.S && D.S.fonts) D.S.fonts.yours = j.yours;
            if (j && !j.ok && j.words) { popLine.textContent = j.words; popLine.hidden = false; }
          }).catch(function(){});
        if (open) pick(name, id); else bump();
        return;
      }
      delete fam[name];             // nothing is kept of a name that did not load
      net = null;
      reach().then(function(can){
        bt.disabled = false;
        bt.textContent = can ? TW.notFound(name) : TW.noNet;
      });
    });
  }
  fontBtn.addEventListener('click', function(e){ e.stopPropagation(); if (open) closeFonts(); else openFonts(); });
  search.addEventListener('input', build);
  search.addEventListener('keydown', function(e){
    if (e.key === 'Enter') { e.preventDefault(); var first = fontList.querySelector('.fp-it:not(:disabled)'); if (first) first.click(); }
  });
  fontList.addEventListener('click', function(e){
    var bt = e.target.closest ? e.target.closest('.fp-it') : null;
    if (!bt || bt.disabled) return;
    if (bt.dataset.load) loadByName(bt.dataset.load, bt);
    else if (bt.dataset.font) pick(bt.dataset.font);
  });
  fontList.addEventListener('scroll', showFaces);
  fontList.addEventListener('wheel', showFaces, {passive: true});
  fontList.addEventListener('pointerover', function(e){
    var bt = e.target.closest ? e.target.closest('.fp-it[data-font]') : null;
    if (bt && stateOf(bt.dataset.font) === 'none') want(bt.dataset.font);
  });
  // a press anywhere else, or Escape, closes the list
  document.addEventListener('pointerdown', function(e){ if (open && !fp.contains(e.target)) closeFonts(); }, true);
  document.addEventListener('keydown', function(e){
    if (open && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeFonts(); D.focus(fontBtn); }
  }, true);

  D.type = {
    T: T, WORDS: TW,
    fontString: T.fontString, measure: measurer, layout: layoutOf, drawText: drawText, fit: fit, status: status,
    lines: function(b){ return layoutOf(b).lines.map(function(ln){ return ln.t; }); },
    edit: edit, change: change, selected: selText, focusWords: focusWords,
    fonts: {want: want, state: stateOf, settled: settled, hasBold: hasBold, retry: function(){ if (retry()) bump(); }, ready: ready, fellBack: fellBack,
            reach: reach, net: function(){ return net; }, own: function(name){ return !!(info[name] && info[name].own); }}
  };
})();
"""

# The styles for the words on the strip, their controls and the font list. No font is named here: the faces
# are set by the script, each from a checked name.
DESIGN_TEXT_CSS = """
.blk.words{overflow:visible;background:transparent}
.blk.words.blank{outline:1.5px dashed rgba(120,110,100,.7);outline-offset:-1px}
.tx-in{position:absolute;left:0;top:0;transform-origin:0 0;pointer-events:none}
.selbox.tx-sides .h.tr,.selbox.tx-sides .h.bl{display:none}
.selbox.tx-sides .h.tl{top:calc(50% - 7px);cursor:ew-resize}
.selbox.tx-sides .h.br{bottom:auto;top:calc(50% - 7px);cursor:ew-resize}
.tx-ln{position:absolute;white-space:pre;pointer-events:none;font-kerning:auto}
.tx-words{font:400 14px/1.35 var(--sans);width:220px;max-width:100%;height:26px;min-height:26px;max-height:160px;resize:vertical;border:1px solid var(--line);border-radius:8px;padding:2px 8px;background:#fff;color:var(--ink)}
.tx-num{width:60px;font:400 13.5px/1.2 var(--sans);border:1px solid var(--line);border-radius:8px;padding:3px 6px;background:#fff;color:var(--ink)}
.tx-words:focus,.tx-num:focus,.fp-search:focus{outline:2px solid var(--sel);outline-offset:-1px}
.tb.tx-b{font-weight:800}
.tb.tx-i{font-style:italic}
.group .pair{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.fp{position:relative;display:inline-flex}
.fp-btn{min-width:150px;max-width:230px;text-align:left;font-weight:400;font-size:14px;padding-top:3px;padding-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-pop{position:absolute;top:calc(100% + 6px);left:0;z-index:30000;width:300px;max-width:calc(100vw - 24px);background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.18);padding:8px}
.fp-pop[hidden]{display:none}
.fp-search{width:100%;font:400 14px/1.3 var(--sans);border:1px solid var(--line);border-radius:8px;padding:7px 9px;background:#fff;color:var(--ink);margin-bottom:6px}
.fp-line{margin:8px 4px 2px;font-size:12.5px;line-height:1.35;color:var(--accent-d)}
.fp-list{position:relative;max-height:300px;overflow-y:auto;overscroll-behavior:contain}
.fp-grp{font:600 11px/1.3 var(--sans);color:var(--soft);text-transform:uppercase;letter-spacing:.06em;padding:8px 8px 2px}
.fp-it{display:flex;align-items:center;gap:8px;width:100%;height:38px;text-align:left;border:0;background:none;padding:0 8px;font-size:19px;line-height:38px;border-radius:6px;cursor:pointer;color:var(--ink)}
.fp-it:hover,.fp-it.cur{background:var(--chip)}
.fp-it:focus-visible{outline:2px solid var(--sel);outline-offset:-2px}
.fp-it .fp-name{flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-it .fp-tag{flex:none;font:400 11px/1.2 var(--sans);color:var(--soft);white-space:nowrap}
.fp-it.fp-load{height:auto;min-height:38px;padding:8px;font:600 13px/1.35 var(--sans);color:var(--accent-d);white-space:normal}
.fp-it:disabled{cursor:default;opacity:.7}
"""
