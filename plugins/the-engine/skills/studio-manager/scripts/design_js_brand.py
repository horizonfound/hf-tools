#!/usr/bin/env python3
"""The carousel designer's page: the brand colors.

DESIGN_BRAND_JS (put on the page by design_page.py after the text script) adds a "Brand colors" group beside
Background: the colors the photographer has saved, shared by every shoot.

    The label always reads "Brand colors": with a text box selected the group's tooltip and its name for a screen
    reader say "Brand colors (for the text)" (the longer words in the row itself used to push Undo onto a new row).
    "+" opens the color box; the color chosen there is saved (POST /design-brand {add}), up to the number the
    Assistant allows (16), with a plain line at the limit.
    A click on a color colors the background, or, when a text box is selected, that text. The same colors
    sit in a small row beside the text color.
    The small x on a color (it shows when the pointer is over the color, or the color has the keyboard's
    attention, and always on a touch screen) takes it off the list (POST /design-brand {remove}). The Assistant
    keeps what was taken off in its own file, and "Put it back" beside the line that follows puts it back.

The list lives with the Assistant (brand.json), never in the browser: it arrives with the page's state and
every answer to a change carries the list as it now stands.
"""

DESIGN_BRAND_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, $ = D.$, el = D.el;
  var COLOR = /^#[0-9a-f]{6}$/;

  // Every line of words this part of the page says.
  var BW = D.WORDS.brand = {
    label: 'Brand colors', labelText: 'Brand colors (for the text)',
    none: 'none yet',
    add: 'Save a brand color', addTitle: 'Pick a color and it is kept here, for every shoot',
    useBg: function(c){ return 'Use ' + c + ' for the background'; },
    useText: function(c){ return 'Use ' + c + ' for the selected text'; },
    off: function(c){ return 'Take ' + c + ' off your brand colors'; },
    saved: 'Saved. It’s here for every shoot.',
    took: 'Taken off your brand colors.', back: 'Put it back',
    // the Assistant's own words for this, so the page and a refusal say the same thing
    full: function(k){ return 'You\'ve saved ' + k + ' brand colors, which is as many as fit. Take one off first.'; }
  };

  var g = D.tools.group('g-brand', '', 'tools-main');
  var bg = $('g-bg');
  if (bg && bg.parentNode) bg.parentNode.insertBefore(g, bg.nextSibling);       // beside Background
  var label = el('span', 'lbl', BW.label); label.id = 'brand-label';
  g.setAttribute('role', 'group'); g.setAttribute('aria-label', BW.label);
  var row = el('span', 'bc-row'); row.id = 'brand-row';
  var addBtn = el('button', 'tb', '+'); addBtn.type = 'button'; addBtn.id = 'brand-add';
  addBtn.setAttribute('aria-label', BW.add); addBtn.title = BW.addTitle;
  var picker = el('input', 'bc-pick'); picker.type = 'color'; picker.id = 'brand-pick'; picker.tabIndex = -1;
  picker.setAttribute('aria-hidden', 'true');
  // the line a press brings (Saved. / Taken off... Put it back / as many as fit) is in the selection bar's first
  // line, with the other lines a press brings, so it never lies over words or covers a button
  var line = el('span', 'gline'); line.id = 'brand-line'; line.setAttribute('role', 'status');
  g.appendChild(label); g.appendChild(row); g.appendChild(addBtn); g.appendChild(picker);
  D.selbar.cap(line, 'line');

  function colors(){ var b = D.S && D.S.brand; return b && Array.isArray(b.colors) ? b.colors.filter(function(c){ return COLOR.test(c); }) : []; }
  function most(){ var b = D.S && D.S.brand; return b && b.max > 0 ? b.max : 16; }
  function selText(){ var b = D.selected(); return b && M.isText(b) ? b : null; }

  function say(text, undoColor){
    line.textContent = '';
    line.removeAttribute('title');
    if (!text) return;
    line.title = text;
    line.appendChild(el('span', '', text));
    if (undoColor) {
      var b = el('button', 'tb', BW.back); b.type = 'button'; b.id = 'brand-back';
      b.addEventListener('click', function(){ send({add: undoColor}, ''); });
      line.appendChild(document.createTextNode(' '));
      line.appendChild(b);
    }
  }
  // One change to the list, saved by the Assistant; the answer is the list as it now stands.
  var busy = false;
  function send(body, done, undoColor){
    if (busy) return;
    busy = true;
    fetch('/design-brand', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(function(r){ return r.json(); })
      .then(function(j){
        busy = false;
        if (j && Array.isArray(j.colors) && D.S) D.S.brand = {colors: j.colors, max: most()};
        if (j && j.ok) say(done, undoColor); else say((j && j.words) || D.WORDS.cantReach);
        draw();
      })
      .catch(function(){ busy = false; say(D.WORDS.cantReach); });
  }
  function use(c){
    if (!D.st || D.blocked || !COLOR.test(c)) return;
    say('');
    var t = selText();
    // a story's text on a box: a brand color colors the box, and the words go black or white on it (hers)
    if (t && D.STORY && D.type.look(t) === 'box') D.type.change('boxColor', c);
    else if (t) D.type.edit({color: c});
    else D.setState(function(st){ return M.setBg(st, c); });
  }

  var shownKey = '';
  function fill(box, big, text){
    box.textContent = '';
    var list = colors();
    if (!list.length) { if (big) box.appendChild(el('span', 'hint', BW.none)); return; }
    list.forEach(function(c){
      var w = el('span', 'bc'), s = el('button', 'bc-sw');
      s.type = 'button'; s.dataset.c = c; s.style.background = c;
      s.title = text ? BW.useText(c) : BW.useBg(c); s.setAttribute('aria-label', s.title);
      w.appendChild(s);
      if (big) {
        var x = el('button', 'bc-off', '×'); x.type = 'button'; x.dataset.off = c;
        x.title = BW.off(c); x.setAttribute('aria-label', x.title);
        w.appendChild(x);
      }
      box.appendChild(w);
    });
  }
  function draw(){
    var text = !!selText(), key = colors().join(',') + '|' + text;
    // the label's words never change length (a longer label pushed the buttons after it onto another row): with
    // a text box selected the group says so in its tooltip and its name for a screen reader, and each color's
    // own name says what a press does
    label.title = text ? BW.labelText : '';
    g.setAttribute('aria-label', text ? BW.labelText : BW.label);
    if (key === shownKey) return;
    shownKey = key;
    fill(row, true, text);
    var small = $('t-brand');
    if (small) fill(small, false, true);
  }
  D.on('render', draw);
  D.on('adopt', function(){ shownKey = ''; say(''); });

  function onClick(e){
    var t = e.target.closest ? e.target.closest('button') : null;
    if (!t) return;
    if (t.dataset.off) { send({remove: t.dataset.off}, BW.took, t.dataset.off); return; }
    if (t.dataset.c) use(t.dataset.c);
  }
  row.addEventListener('click', onClick);
  var small = $('t-brand');
  if (small) small.addEventListener('click', onClick);

  addBtn.addEventListener('click', function(){
    if (!D.st) return;
    if (colors().length >= most()) { say(BW.full(most())); return; }
    say('');
    var b = selText(), start = b ? b.color : D.st.bg;
    if (COLOR.test(String(start || '').toLowerCase())) picker.value = start;
    try { if (picker.showPicker) picker.showPicker(); else picker.click(); } catch (x) { try { picker.click(); } catch (y) {} }
  });
  // the color box was closed on a color: that color is saved
  picker.addEventListener('change', function(){
    var c = String(picker.value || '').toLowerCase();
    if (!COLOR.test(c)) return;
    if (colors().indexOf(c) >= 0) { say(BW.saved); return; }
    if (colors().length >= most()) { say(BW.full(most())); return; }
    send({add: c}, BW.saved);
  });
})();
"""

DESIGN_BRAND_CSS = """
.bc-row{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center}
/* in the slides' row (from 768 px up, where it is a row) the swatches take the room their group has and no more:
   more colors than fit on one line wrap under the first, with the label and + staying beside them */
@media(min-width:768px){#brand-row{flex:1 1 0;max-width:max-content}}
.bc{position:relative;display:inline-flex}
.bc-sw{width:24px;height:24px;border-radius:6px;border:1px solid rgba(0,0,0,.2);padding:0;cursor:pointer}
.bc-sw:focus-visible{outline:2px solid var(--sel);outline-offset:1px}
.bc-row.small{gap:4px}
.bc-row.small .bc-sw{width:18px;height:18px}
.bc-off{position:absolute;top:-7px;right:-7px;width:16px;height:16px;border-radius:50%;border:0;padding:0;background:var(--ink);color:#fff;font:700 11px/16px var(--sans);text-align:center;cursor:pointer;display:none}
.bc:hover .bc-off,.bc:focus-within .bc-off{display:block}
@media(hover:none){.bc-off{display:block}}
@media(hover:none) and (pointer:coarse){.bc-row{gap:14px}.bc-row .bc-sw{width:32px;height:32px}.bc-off{width:22px;height:22px;top:-10px;right:-10px;font:700 14px/22px var(--sans)}}
.group input.bc-pick{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;border:0;padding:0}
#g-brand{position:relative}
#brand-line{display:inline-flex;gap:6px;align-items:center}
#brand-line>span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#brand-line .tb{flex:none}
#brand-line:empty{display:none}
"""
