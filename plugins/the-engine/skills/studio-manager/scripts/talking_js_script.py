#!/usr/bin/env python3
"""The talking reel page's script, step 2's script column (Nicole's handoff v24, pages/talking-reel.html, built our
way): the sentences, a click on a word, the highlight bar, the Move row, the bars above the words (a photo
stretch, or a video's), dragging a bar, and a bar's menu. One string of JavaScript and nothing else. It stands on
talking_js_core.py (window.Talk); the two pickers are talking_js_pick.py.

Hers, kept (each has its check in tests/talking_page_check.py --only script):
  - a sentence is a box of words; a cut word is crossed out, a punch in underlined, a slow zoom dashed, a sped-up
    word blue; a sentence that is all cut is faint and has no Move row;
  - a click on a word jumps to 0.05 s before it and plays (in the cut version, a cut word starts at the next
    piece kept); it does nothing while words are highlighted, or when it lands on a bar;
  - highlight words and the bar comes up above them: + Add photos, + Add video | Cut, Bring back | Punch in,
    Slow zoom, No zoom. Adding is ONLY from there: no plus, no "add" that shows on hover;
  - under a sentence the only row is Move: None / Punch in / Slow zoom, with "on part of it". No Photo row;
  - a photo stretch (or a video) is a bar lying over its words: 44 px of room above the words ONLY in a sentence
    that has one; the bar's pieces bridge the spaces; up to 8 small photos and the spot's short name on its first
    piece, again at each sentence it runs into; handles only at its true ends. A video's bar is blue-green, with
    its first still and "▶ name";
  - press a bar: under 5 px is a click and opens its menu; an end snaps to the nearest word (sideways distance
    plus three times the up-and-down distance; a start to a word's left edge, an end to its right edge, a move to
    its middle); a start never passes the end nor an end the start; a move keeps the length and stops at the first
    and last word; dropped onto another stretch it trims or splits that one (setRange); the toast says where;
  - the menu: the words in quotes (70 characters), the four spots, Change, Remove (this one / all N), and "Put it
    back" only when it was moved. It opens under the bar, or above it when it would go under the dock; it closes
    on Escape, on a press anywhere outside it and outside a bar, and when a bar drag starts.
Her pitfalls, kept as rules:
  - a stretch is always looked up by its START WORD at the moment of a press (findShot), never kept across a
    refresh: every save here is a function that builds what to save when its turn comes;
  - a refresh never redraws the script while words are highlighted (the highlight bar would vanish under the
    cursor): it is drawn once the highlight is let go;
  - the 3-second look waits during a bar drag (T.busy) and while the menu is open (talking_js_core.py's quiet).
Ours:
  - everything is put on the page as text and elements, never as HTML from a string;
  - the Move chips are real buttons; a small photo or a still that is not there yet shows nothing, not a broken
    picture, and a photo's small copy that was not made when the page opened shows by itself once it is
    (lookForCopies: the whole state is asked for every few seconds only while one on the page is missing);
  - a bar drag ends, saving nothing, when the button turns out to have been let go where the page did not see
    it (a move with no button held, the Mac's own menu, the window losing the keyboard); a Control-click starts
    none; and the menu opens beside the bar as it is at the release, even if the script was drawn again since
    the press.

What the later parts use from here: T.SELSHOT (the start word of the stretch picked, or null) and T.markShot()
(it also says 'shot' to whoever listens: the timeline marks its block); T.pickedWords (a function the timeline
may set: the words of the clip picked there) and T.markPicked(); T.jumpToWord(i); T.togglePlay() (the plain one
here; the preview's part puts its own in its place) and T.frame (the preview's, called when there is one);
T.selectedWords(), T.findShot(a), T.shotsOut(list), T.thumbs(x, box, max), T.photoUrl(n, size), T.stillUrl(key),
T.renderScript(), T.closeMenu(), T.spotShort.
"""

JS = r"""
(function(){
'use strict';
var T = window.Talk, W = T.W, $ = T.$, Q = T.Q;
var SPOTS = [['full', W.spot_full], ['pip', W.spot_pip], ['center', W.spot_center], ['corner', W.spot_corner]];
var SPOT_SHORT = {full: W.spot_full, pip: W.spot_short_pip, center: W.spot_center, corner: W.spot_short_corner};
var MOVES = [['', W.move_none], ['punch', W.punch], ['zoom', W.slow_zoom]];
var CLICK_PX = 5;              // hers: a press on a stretch that moves less than this is a click
var stale = false;             // a new state came while words were highlighted: the script is drawn when they let go
var gdrag = null;              // a stretch being dragged
T.SELSHOT = null; T.PHOTOS = []; T.byN = {}; T.STILLS = {};

function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function each(sel, fn){ Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }
function findShot(a){ for (var k = 0; k < T.SH.length; k++) if (T.SH[k].a === a) return T.SH[k]; return null; }
// a stretch as a save takes it (hers: a, b, ns, v, from, spot, pos, me); a video goes back as the key it came with
function shotOut(x){
  return {a: x.a, b: x.b, ns: x.v ? [] : (x.ns || []).slice(), v: x.v ? {key: x.v.key, name: x.v.name} : null,
          from: x.v ? (x.from || 0) : 0, spot: x.spot, pos: x.pos || null, me: x.me || null};
}
function shotsOut(list){ return list.map(shotOut); }
function photoUrl(n, size){ var p = T.byN[n]; return '/kit-photo?' + Q + '&n=' + n + '&size=' + (size || 's') + '&v=' + encodeURIComponent((p && p.v) || ''); }
function stillUrl(key){ var n = T.STILLS[key]; return n == null ? null : '/reel-strip?' + Q + '&key=' + encodeURIComponent(key) + '&n=' + encodeURIComponent(n); }
function picture(src){
  var i = el('img'); i.alt = ''; i.draggable = false;
  i.addEventListener('error', function(){ if (i.parentNode) i.parentNode.removeChild(i); });      // not made yet: nothing, never a broken picture
  i.src = src;
  return i;
}
// what a stretch shows of itself: its photos (up to `max`) and the spot's short name; a video's first still and its name
function thumbs(x, box, max){
  if (x.v) {
    var s = stillUrl(x.v.key);
    if (s) box.appendChild(picture(s));
    box.appendChild(el('em', '', '▶ ' + String(x.v.name || '').replace(/\.[^.]+$/, '')));
    return;
  }
  (x.ns || []).slice(0, max || 8).forEach(function(n){ if (T.byN[n] && T.byN[n].have) box.appendChild(picture(photoUrl(n, 's'))); });   // not made yet: it comes by itself (lookForCopies)
  box.appendChild(el('em', '', SPOT_SHORT[x.spot] || ''));
}

// ---- the script ----
function segFor(x, i, a, b){
  var st = i === x.a || i === a, en = i === x.b || i === b;         // a stretch that runs into the next sentence starts again there
  var g = el('i', 'seg' + (st ? ' st' : '') + (en ? ' en' : '') + (x.v ? ' vid' : '') + (x.a === T.SELSHOT ? ' on' : ''));
  g.setAttribute('data-a', x.a);
  if (st) {
    var th = el('span', 'sthumbs'); thumbs(x, th, 8); g.appendChild(th);
    if (i === x.a) g.appendChild(el('b', 'sh l'));                   // handles only at its true ends
  }
  if (i === x.b) g.appendChild(el('b', 'sh r'));
  return g;
}
function renderScript(){
  stale = false;
  var words = T.REC.words || [], cs = T.cutSet(), shotAt = {}, frag = document.createDocumentFragment();
  T.SH.forEach(function(x){ for (var i = x.a; i <= x.b; i++) shotAt[i] = x; });
  (T.REC.sentences || []).forEach(function(se, k){
    var a = se[0], b = se[1], all = true, has = false, i;
    for (i = a; i <= b; i++) if (!cs.has(i)) { all = false; break; }
    var over = T.ZL.filter(function(r){ return r.a <= b && r.b >= a; });
    var whole = over.length === 1 && over[0].a <= a && over[0].b >= b;
    var mv = !over.length ? '' : whole ? over[0].kind : 'part';
    var ws = el('div', 'words');
    for (i = a; i <= b; i++) {
      if (!words[i]) continue;
      var z = T.zoomOf(i), x = shotAt[i], sp = el('span');
      sp.className = [cs.has(i) ? 'cut' : '', z === 'punch' || z === 'zoom' ? 'z-' + z : '', T.speedOf(i) !== 1 ? 'fast' : ''].join(' ').trim();
      sp.setAttribute('data-i', i);
      if (x) { has = true; sp.appendChild(segFor(x, i, a, b)); }
      sp.appendChild(document.createTextNode(words[i].w));
      if (ws.firstChild) ws.appendChild(document.createTextNode(' '));
      ws.appendChild(sp);
    }
    var sent = el('div', 'sent' + (all ? ' allcut' : '') + (has ? ' hasph' : ''));
    sent.setAttribute('data-k', k);
    sent.appendChild(ws);
    if (!all) {                                                      // the only row under a sentence: Move
      var tools = el('div', 'tools');
      tools.appendChild(el('span', 'lbl', W.move));
      MOVES.forEach(function(m){
        var c = el('button', 'chip' + (mv === m[0] ? ' on' : ''), m[1]);
        c.type = 'button'; c.setAttribute('data-move', m[0]); c.setAttribute('data-k', k);
        c.setAttribute('aria-pressed', mv === m[0] ? 'true' : 'false');
        tools.appendChild(c);
      });
      if (mv === 'part') tools.appendChild(el('span', '', W.move_part));
      sent.appendChild(tools);
    }
    frag.appendChild(sent);
  });
  var box = $('script');
  box.textContent = '';
  box.appendChild(frag);
  rects = null;
  markPicked();
}
// the words of the clip picked on the timeline are outlined (the timeline's part says which: T.pickedWords)
function markPicked(){
  var on = T.pickedWords ? (T.pickedWords() || []) : [];
  each('#script .words span.picked', function(e){ e.classList.remove('picked'); });
  on.forEach(function(i){ var s = wordEl(i); if (s) s.classList.add('picked'); });
}
function markShot(){
  each('#script .seg', function(e){ e.classList.toggle('on', +e.getAttribute('data-a') === T.SELSHOT); });
  T.emit('shot', T.SELSHOT);
}
function wordEl(i){ return document.querySelector('#script .words span[data-i="' + (+i) + '"]'); }

// ---- playing from a word (the preview's part brings the real player; this is the plain press) ----
function jumpToWord(i){
  var w = (T.REC.words || [])[i], vid = $('vid');
  if (!w) return;
  try { vid.currentTime = Math.max(0, w.start - 0.05); } catch (e) {}
  if (vid.paused && T.frame) T.frame();
}
if (!T.togglePlay) T.togglePlay = function(){
  var vid = $('vid'), ps = T.P();
  if (!vid.getAttribute('src')) return;
  if (!vid.paused) { vid.pause(); return; }
  if ($('cutMode').checked && ps.length && T.pieceAt(vid.currentTime) < 0) {     // on a cut word: the next piece kept
    var nx = ps.filter(function(p){ return p.from > vid.currentTime; })[0] || ps[0];
    try { vid.currentTime = nx.from; } catch (e) {}
  }
  var p = vid.play();
  if (p && p.then) p.then(null, function(){});
};

// ---- highlighted words, and the bar that comes up above them ----
function selectedWords(){
  var sel = window.getSelection();
  if (!sel || !sel.rangeCount || sel.isCollapsed) return null;
  var box = $('script');
  if (!sel.containsNode(box, true)) return null;
  var spans = box.querySelectorAll('.words span[data-i]'), first = null, last = null;
  for (var k = 0; k < spans.length; k++) if (sel.containsNode(spans[k], true)) { if (first == null) first = +spans[k].getAttribute('data-i'); last = +spans[k].getAttribute('data-i'); }
  return first == null ? null : [first, last];
}
function placeBar(){
  var r = selectedWords(), bar = $('selBar');
  if (!r) {
    bar.style.display = 'none';
    if (stale && T.ready()) renderScript();          // what arrived while they were highlighting
    return;
  }
  var rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
  bar.style.display = 'flex';
  var w = bar.offsetWidth;
  bar.style.left = Math.min(innerWidth - w - 8, Math.max(8, rect.left + rect.width / 2 - w / 2)) + 'px';
  bar.style.top = Math.max(8, rect.top - 48) + 'px';
}
document.addEventListener('selectionchange', placeBar);
addEventListener('scroll', function(){ if ($('selBar').style.display === 'flex') placeBar(); }, true);
function doneSel(){ window.getSelection().removeAllRanges(); $('selBar').style.display = 'none'; }
function changeCut(add){
  var r = selectedWords(); if (!r) return;
  doneSel();
  T.save(function(){
    var s = T.cutSet();
    for (var i = r[0]; i <= r[1]; i++) { if (add) s.add(i); else s['delete'](i); }
    return {cut: T.toRanges(s)};
  });
}
function zoomsOut(list){ return list.map(function(z){ return {a: z.a, b: z.b, kind: z.kind}; }); }
function zoomWords(kind){
  var r = selectedWords(); if (!r) return;
  doneSel();
  T.save(function(){ return {zooms: zoomsOut(T.setRange(T.ZL, r[0], r[1], kind ? {kind: kind} : null))}; });
  T.toast(kind === 'punch' ? W.zoom_punch_toast : kind === 'zoom' ? W.zoom_slow_toast : W.zoom_none_toast);
}
// a press, not a click: the press must not take the highlight away before it is read
function onBar(id, fn){ $(id).addEventListener('mousedown', function(e){ e.preventDefault(); fn(); }); }
onBar('selPhoto', function(){ var r = selectedWords(); if (!r) return; doneSel(); if (T.openPick) T.openPick(r[0], r[1]); });
onBar('selVideo', function(){ var r = selectedWords(); if (!r) return; doneSel(); if (T.openVPick) T.openVPick(r[0], r[1]); });
onBar('selCut', function(){ changeCut(true); });
onBar('selBack', function(){ changeCut(false); });
onBar('selPunch', function(){ zoomWords('punch'); });
onBar('selZoom', function(){ zoomWords('zoom'); });
onBar('selNoZoom', function(){ zoomWords(''); });

// ---- a click in the script: a Move chip, or a word ----
$('script').addEventListener('click', function(e){
  var t = e.target;
  if (!t || !t.closest) return;
  var c = t.closest('[data-move]');
  if (c) {
    var k = +c.getAttribute('data-k'), kind = c.getAttribute('data-move');
    T.save(function(){
      var se = (T.REC.sentences || [])[k];           // the sentence as it is now
      return se ? {zooms: zoomsOut(T.setRange(T.ZL, se[0], se[1], kind ? {kind: kind} : null))} : null;
    });
    return;
  }
  var s = t.closest('span[data-i]');
  if (!s || t.closest('.seg') || String(window.getSelection()).trim()) return;
  jumpToWord(+s.getAttribute('data-i'));
  if ($('vid').paused) T.togglePlay();
});
// hover: the whole stretch lights up, in every sentence it runs through
$('script').addEventListener('mouseover', function(e){
  var g = e.target.closest && e.target.closest('.seg'); if (!g) return;
  var a = g.getAttribute('data-a');
  each('#script .seg', function(x){ x.classList.toggle('hov', x.getAttribute('data-a') === a); });
});
$('script').addEventListener('mouseout', function(e){
  var g = e.target.closest && e.target.closest('.seg'); if (!g) return;
  var to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.seg');
  if (to && to.getAttribute('data-a') === g.getAttribute('data-a')) return;
  each('#script .seg.hov', function(x){ x.classList.remove('hov'); });
});

// ---- drag a stretch: its ends stretch or shrink it, its middle moves it; a click opens its menu ----
var rects = null;              // where every word is, read once per drag (a long script has thousands)
function readRects(){
  rects = {sx: window.scrollX, sy: window.scrollY, list: []};
  each('#script .words span[data-i]', function(e){ var r = e.getBoundingClientRect(); rects.list.push([+e.getAttribute('data-i'), r.left, r.right, r.top, r.bottom]); });
}
function nearestWord(cx, cy, side){
  if (!rects) readRects();
  var dx = window.scrollX - rects.sx, dy = window.scrollY - rects.sy, best = null, bd = Infinity;
  cx += dx; cy += dy;
  rects.list.forEach(function(r){
    var x = side === 'a' ? r[1] : side === 'b' ? r[2] : (r[1] + r[2]) / 2;
    var d = Math.abs(cx - x) + Math.max(0, r[3] - cy, cy - r[4]) * 3;
    if (d < bd) { bd = d; best = r[0]; }
  });
  return best;
}
function ghost(cur){
  each('#script .words span.ghost', function(s){ s.classList.remove('ghost'); });
  if (cur) for (var i = cur.a; i <= cur.b; i++) { var s = wordEl(i); if (s) s.classList.add('ghost'); }
}
$('script').addEventListener('pointerdown', function(e){
  var g = e.target.closest && e.target.closest('.seg');
  if (!g || e.button !== 0 || e.ctrlKey) return;      // a Control-click is the Mac's right click: its release may never come
  e.preventDefault();
  var x = findShot(+g.getAttribute('data-a')); if (!x) return;
  var h = e.target.closest('.sh');
  rects = null;
  gdrag = {a: x.a, b: x.b, el: g, mode: h ? (h.classList.contains('l') ? 'a' : 'b') : 'move', anchor: nearestWord(e.clientX, e.clientY, 'mid'),
           sx: e.clientX, sy: e.clientY, moved: false, cur: {a: x.a, b: x.b}};
});
document.addEventListener('pointermove', function(e){
  var d = gdrag; if (!d) return;
  // the button was let go where the page never heard of it (over a menu of the Mac's, another window): the drag
  // is over and nothing is saved; never a stretch that follows a hand holding nothing
  if (e.pointerType === 'mouse' && !(e.buttons & 1)) { dropDrag(null, true); return; }
  if (!d.moved && Math.abs(e.clientX - d.sx) + Math.abs(e.clientY - d.sy) > CLICK_PX) { d.moved = true; closeMenu(); }
  if (!d.moved) return;
  var n = (T.REC.words || []).length, w = nearestWord(e.clientX, e.clientY, d.mode);
  if (w == null) return;
  if (d.mode === 'a') d.cur = {a: Math.min(w, d.b), b: d.b};                  // the start can't pass the end
  else if (d.mode === 'b') d.cur = {a: d.a, b: Math.max(w, d.a)};             // nor the end the start
  else { var len = d.b - d.a, a = Math.max(0, Math.min(n - 1 - len, d.a + w - d.anchor)); d.cur = {a: a, b: a + len}; }
  ghost(d.cur);
});
function dropDrag(e, cancel){
  var d = gdrag; gdrag = null; if (!d) return;
  ghost(null); rects = null;
  if (cancel === true || (e && e.type === 'pointercancel')) return;
  if (!d.moved) {
    // the script may have been drawn again since the press (a save's answer, a look): the bar as it is NOW
    var g = d.el.isConnected ? d.el : document.querySelector('#script .seg[data-a="' + d.a + '"]');
    if (g) openMenu(d.a, 0, g);
    return;
  }
  var a = d.cur.a, b = d.cur.b;
  if (a === d.a && b === d.b) return;
  T.SELSHOT = a;
  T.save(function(){
    var x = findShot(d.a); if (!x) return null;         // as it is now, by its start word
    var keep = {ns: x.ns, v: x.v, from: x.from, spot: x.spot, pos: x.pos, me: x.me};
    return {shots: shotsOut(T.setRange(T.SH.filter(function(y){ return y.a !== d.a; }), a, b, keep))};
  });
  T.toast(T.fill(W.now_on, {words: T.wordsOf(a, b, 40)}));
}
document.addEventListener('pointerup', dropDrag);
document.addEventListener('pointercancel', dropDrag);
document.addEventListener('contextmenu', function(){ dropDrag(null, true); });
addEventListener('blur', function(){ dropDrag(null, true); });
T.busy(function(){ return !!gdrag; });

// ---- a stretch's menu ----
function button(cls, text, fn){ var b = el('button', cls, text); b.type = 'button'; b.addEventListener('click', fn); return b; }
function openMenu(a, j, anchor){
  var x = findShot(a); if (!x) return;
  T.SELSHOT = a; markShot();
  var m = $('pmenu'), r = anchor.getBoundingClientRect(), many = !x.v && (x.ns || []).length > 1;
  // every press looks the stretch up again by its start word: the page reads the record afresh every few seconds
  var swap = function(change){
    return function(){
      var c = findShot(a); if (!c) return null;
      return {shots: shotsOut(T.SH.map(function(y){ if (y !== c) return y; var n = change(y); n.a = y.a; n.b = y.b; return n; }))};
    };
  };
  var without = function(){ return {shots: shotsOut(T.SH.filter(function(y){ return y.a !== a; }))}; };
  m.textContent = '';
  m.appendChild(el('p', 'pm-w', T.fill(W.pm_words, {words: T.wordsOf(x.a, x.b, 70)})));
  var spots = el('div', 'pm-s');
  SPOTS.forEach(function(s){
    var b = button('chip' + (x.spot === s[0] ? ' on' : ''), s[1], function(){
      closeMenu();
      T.save(swap(function(y){ return {ns: y.ns, v: y.v, from: y.from, spot: s[0], pos: null, me: y.me}; }));      // a new spot: where it sits starts afresh, they stay where they put themselves
    });
    b.setAttribute('data-mspot', s[0]);
    spots.appendChild(b);
  });
  m.appendChild(spots);
  var acts = el('div', 'pm-a');
  var ch = button('btn small', x.v ? W.change_video : many ? W.change_photos : W.change_photo, function(){
    closeMenu();
    var c = findShot(a); if (!c) return;
    if (c.v) { if (T.openVPick) T.openVPick(c.a, c.b, c); } else if (T.openPick) T.openPick(c.a, c.b, c);
  });
  ch.setAttribute('data-m', 'change'); acts.appendChild(ch);
  var rm = button('btn small', many ? W.remove_one : W.remove, function(){
    closeMenu();
    var c = findShot(a); if (!c) return;
    if (!c.v && (c.ns || []).length > 1)
      T.save(swap(function(y){ return {ns: y.ns.filter(function(_, k){ return k !== j; }), v: y.v, from: y.from, spot: y.spot, pos: y.pos, me: y.me}; }));
    else { T.SELSHOT = null; T.save(without); }
    T.toast(W.removed);
  });
  rm.setAttribute('data-m', 'remove'); acts.appendChild(rm);
  if (many) {
    var ra = button('btn small', T.fill(W.remove_all, {n: x.ns.length}), function(){
      closeMenu();
      if (!findShot(a)) return;
      T.SELSHOT = null; T.save(without); T.toast(W.removed_many);
    });
    ra.setAttribute('data-m', 'removeall'); acts.appendChild(ra);
  }
  if (x.pos || x.me) {
    var rs = button('btn small', W.put_back, function(){
      closeMenu();
      T.save(swap(function(y){ return {ns: y.ns, v: y.v, from: y.from, spot: y.spot, pos: null, me: null}; }));
    });
    rs.setAttribute('data-m', 'reset'); acts.appendChild(rs);
  }
  m.appendChild(acts);
  m.classList.add('open');
  // below the stretch, or above it when it would go under the dock; always on the screen
  var top = r.bottom + 8 + m.offsetHeight > innerHeight - $('dock').offsetHeight ? r.top - m.offsetHeight - 8 : r.bottom + 8;
  m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.left)) + 'px';
  m.style.top = Math.max(8, top) + 'px';
}
function closeMenu(){ $('pmenu').classList.remove('open'); }
document.addEventListener('pointerdown', function(e){
  if (!$('pmenu').classList.contains('open') || !e.target.closest) return;
  if (!e.target.closest('#pmenu') && !e.target.closest('.seg')) closeMenu();
});
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeMenu(); });

// ---- a photo's small copy that is not made yet (a page opened seconds after the shoot was made) ----
// The 3-second look gets the short answer while nothing in the record moves, so it never hears that a copy got
// made. While a photo on a stretch (or any photo, with the photo picker open) is still without its copy, the
// whole state is asked for every few seconds and ONLY its photos are taken: the bars and the picker then show
// them by themselves. It gives up after a while with nothing new (a copy that never comes).
function takePhotos(list){ T.PHOTOS = list; T.byN = {}; list.forEach(function(p){ T.byN[p.n] = p; }); }
function haveMark(){ return T.PHOTOS.map(function(p){ return p.n + ':' + p.v + ':' + (p.have ? 1 : 0); }).join(','); }
function wanting(){
  var open = $('pick').classList.contains('open');
  return T.PHOTOS.some(function(p){
    if (p.have || p.missing) return false;
    return open || T.SH.some(function(x){ return !x.v && (x.ns || []).indexOf(p.n) >= 0; });
  });
}
var copyLooks = 0, copyAsking = false;
function lookForCopies(){
  var held = !!selectedWords() || !!gdrag || $('pmenu').classList.contains('open');
  if (stale && !held && T.loaded && T.ready()) renderScript();          // what a look brought while their hand was on the script
  if (held) return;
  if (copyAsking || !T.loaded || !T.ready() || document.hidden || !wanting() || copyLooks >= (T.DATA.copiesTries || 90)) return;
  copyAsking = true; copyLooks++;
  T.ask('/talking-state?' + Q).then(function(res){
    copyAsking = false;
    var st = res.j, was = haveMark();
    if (!st || !Array.isArray(st.photos)) return;
    takePhotos(st.photos);
    if (was === haveMark()) return;
    copyLooks = 0;
    if (selectedWords() || gdrag || $('pmenu').classList.contains('open')) stale = true;      // never under their hand: drawn at the next tick
    else if (T.ready()) renderScript();
    T.emit('photos');
  }, function(){ copyAsking = false; });
}
T.copiesTimer = setInterval(lookForCopies, T.DATA.copiesEvery || 4000);

// ---- a new state ----
T.on('apply', function(a){
  var st = T.ST;
  if (Array.isArray(st.photos)) takePhotos(st.photos);
  if (st.stills && typeof st.stills === 'object') { for (var k in st.stills) T.STILLS[k] = st.stills[k]; }
  if (!a.ready) { closeMenu(); $('selBar').style.display = 'none'; return; }
  if (T.SELSHOT != null && !findShot(T.SELSHOT)) T.SELSHOT = null;
  if (!a.changed && !stale) return;
  if (selectedWords()) { stale = true; return; }      // never under their cursor: drawn when the highlight is let go
  renderScript();
});

T.findShot = findShot; T.shotsOut = shotsOut; T.photoUrl = photoUrl; T.stillUrl = stillUrl; T.thumbs = thumbs; T.picture = picture;
T.renderScript = renderScript; T.markPicked = markPicked; T.markShot = markShot; T.jumpToWord = jumpToWord;
T.selectedWords = selectedWords; T.doneSel = doneSel; T.openMenu = openMenu; T.closeMenu = closeMenu;
T.spotShort = SPOT_SHORT; T.wordEl = wordEl; T.scriptStale = function(){ return stale; };
})();
"""
