#!/usr/bin/env python3
"""The talking reel page's script, the timeline (Nicole's handoff v24, pages/talking-reel.html, built our way): the
dock across the bottom. The ruler, the photo blocks, the talking clips, the words under them once zoomed in, the
line, scrubbing, a clip's ends (in cuts, out brings back), a photo block's ends, Split, Delete, Speed, Zoom, the
timeline's own zoom, the keys (Undo, Redo, Delete), and Make it in CapCut with its result box. One string of
JavaScript and nothing else. It stands on talking_js_core.py (window.Talk), talking_js_script.py and
talking_js_preview.py.

Hers, kept number for number (each has its check in tests/talking_page_check.py --only timeline):
  - the scale: 12 px of padding each side; it fits when (width - 24) / length, with never under 200 px of room;
    most zoomed in is 240 px a second; the slider runs fit x (max / fit)^(v / 100); the ruler's step is the first
    of 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60 s that is 56 px wide or more; + and - move the slider 15; a wheel with
    Ctrl or Cmd is value - deltaY x 0.4 around the mouse; a plain wheel moves the timeline sideways; the line is
    followed while playing (within 30 px of the left or 60 px of the right it jumps to a quarter in); a clip is
    never under 3 px wide, a photo block never under 18; the time reads "m:ss.t / m:ss.t"; the words show under
    the clips from 55 px a second;
  - picking: a press on a clip picks it and seeks; on a photo block picks it and brings its bar in the script into
    view; on empty track clears. The picked clip's words are outlined in the script. A picked clip or photo block
    has a small round x, and the button reads Delete clip or Delete photo; the x, the button and the Delete or
    Backspace key remove it (the key only with something picked and no words highlighted). Deleting a clip cuts
    its words. Speed and Zoom chips are grey with no clip picked; badges "1.5x", "Punch in", "Slow zoom";
  - a clip's end dragged in cuts to the nearest word edge; dragged out it brings back the cut words touching the
    clip whose time falls within the dragged distance x the clip's speed. A photo block's end goes to the nearest
    KEPT word by the reel's time; it only ever changes which words the photo covers;
  - Split: the gap between two words nearest the line, inside the clip under the line;
  - the keys: Cmd or Ctrl with Z is Undo, with Shift is Redo, with Y is Redo.
Her faults, fixed (the plan, 2c):
  - dragging a VIDEO block's end kept only its photos, spot and place: the video and its start point were lost.
    Ours carries them;
  - nothing here holds a stretch or a clip across a refresh: a photo block is known by its START WORD and a clip by
    its FIRST WORD, looked up again when the press ends and again when the save's turn comes;
  - the keys do nothing while either picker is open (hers only looked at the photo picker).
Ours:
  - everything is put on the page as text and elements, never as HTML from a string;
  - a drag ends, saving nothing, when the button was let go where the page never saw it, on the Mac's own menu,
    or when the window loses the keyboard; a Control-click starts none; the 3-second look waits during a drag;
  - Make it in CapCut is a job of its own on the Assistant's side (talking_rec.start_make): the press waits for
    any save still on its way, then the page asks how the job stands once a second (only that: /talking-state
    with only=make) and shows her result box when it is done, or the reason in plain words. A page opened while a
    make is at work follows it. When the make it follows can no longer be seen (five answers in a row with no
    make in them, or none at all) the button comes back with plain words: the page never stays on "Making it…".
    The record's counter does not move for a make, so Undo is as it was afterwards.

What it gives the other parts: T.pickedWords() (the words of the clip picked, for the script's outline),
T.renderTimeline(), T.tl() (what a test may read: {pps, selw, sel, drag, making}).
"""

JS = r"""
(function(){
'use strict';
var T = window.Talk, W = T.W, $ = T.$, Q = T.Q;
var vid = $('vid'), track = $('tlTrack');
// hers
var PAD = 12, WORDS_AT = 55, MOST = 240, ROOM = 200, TICK = 56, STEPS = [0.25, 0.5, 1, 2, 5, 10, 15, 30, 60];
var SPEEDS = [1, 1.25, 1.5, 2], MOVES = [['', W.move_none], ['punch', W.punch], ['zoom', W.slow_zoom]];
var CLICK_PX = 3, NUDGE = 15, WHEEL = 0.4, CLIP_MIN = 3, PHOTO_MIN = 18, FOLLOW_L = 30, FOLLOW_R = 60, THUMBS = 10;
var MAKE_EVERY = 1000;         // ours: how often the page asks how its make stands
var MAKE_LOST = 5;             // ours: that many answers in a row with no make in them, and the page stops waiting
var PPS = 20;                  // px a second, as drawn
var SELW = null;               // a word of the clip picked (the clip is looked up from it every time)
var TLSEL = null;              // what is picked on the timeline: 'clip', 'photo' or nothing
var drag = null;               // a press on the track: scrubbing, a clip's end, or a photo block's end
var making = null;             // the make this page follows: its id, or true while the press is on its way

function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function each(sel, fn){ Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }
function cl(v, a, b){ return Math.min(b, Math.max(a, v)); }
function two(n){ return (n < 10 ? '0' : '') + n; }
function fmt(s){ s = Math.round(s * 10) / 10; var r = (s % 60).toFixed(1); return Math.floor(s / 60) + ':' + (r.length < 4 ? '0' + r : r); }
function fmtTick(s){ return Math.floor(s / 60) + ':' + two(Math.floor(s % 60)) + (s % 1 ? '.' + Math.round((s % 1) * 10) : ''); }
function X(R){ return PAD + R * PPS; }
function selPiece(){
  if (SELW == null) return null;
  var ps = T.P();
  for (var i = 0; i < ps.length; i++) if (ps[i].words.indexOf(SELW) >= 0) return ps[i];
  return null;
}
function pieceOf(w0){ var ps = T.P(); for (var i = 0; i < ps.length; i++) if (ps[i].words[0] === w0) return ps[i]; return null; }
function zoomKind(p){ return p && p.zoom != null && T.ZL[p.zoom] ? T.ZL[p.zoom].kind : ''; }
function spotName(s){ return s === 'full' ? W.spot_full : s === 'pip' ? W.spot_pip : s === 'center' ? W.spot_center : s === 'corner' ? W.spot_corner : ''; }
function round_x(title){ var b = el('b', 'tl-x', '×'); b.title = title; b.setAttribute('role', 'button'); b.setAttribute('aria-label', title); return b; }

// ---- drawing ----
function scale(){
  var tot = T.total();
  var fit = Math.max(ROOM, track.clientWidth - PAD * 2) / Math.max(tot, 1), max = Math.max(fit, MOST);
  PPS = fit * Math.pow(max / fit, +$('tlScale').value / 100);
  return tot;
}
function renderTimeline(){
  if ($('tl').hidden) return;
  var ps = T.P(), words = T.REC.words || [], tot = scale(), i;
  $('tlInner').style.width = (tot * PPS + PAD * 2) + 'px';
  // the ruler
  var step = 60;
  for (i = 0; i < STEPS.length; i++) if (STEPS[i] * PPS >= TICK) { step = STEPS[i]; break; }
  var ruler = document.createDocumentFragment();
  for (var s = 0; s <= tot + 0.001; s += step) { var tk = el('span', '', fmtTick(Math.round(s * 100) / 100)); tk.style.left = X(s) + 'px'; ruler.appendChild(tk); }
  $('tlRuler').textContent = ''; $('tlRuler').appendChild(ruler);
  // the photos and the videos, over the words they go with; drag an end to change which words
  var row = document.createDocumentFragment();
  T.SH.forEach(function(x){
    var sp = T.shotSpan(x); if (!sp) return;
    var d = el('div', 'tl-ph' + (x.a === T.SELSHOT ? ' on' : ''));
    d.setAttribute('data-a', x.a);
    d.style.left = X(sp[0]) + 'px'; d.style.width = Math.max(PHOTO_MIN, (sp[1] - sp[0]) * PPS - 2) + 'px';
    d.title = W.tl_photo_title;
    var ha = el('i', 'tl-ph-h'); ha.setAttribute('data-edge', 'a'); d.appendChild(ha);
    if (TLSEL === 'photo' && x.a === T.SELSHOT) d.appendChild(round_x(W.tl_photo_x));
    var label;
    if (x.v) {
      var still = T.stillUrl(x.v.key);
      if (still) d.appendChild(T.picture(still));
      d.appendChild(document.createTextNode('▶'));
      label = T.fill(W.tl_video, {name: x.v.name, spot: spotName(x.spot)});
    } else {
      (x.ns || []).slice(0, THUMBS).forEach(function(n){ if (T.byN[n] && T.byN[n].have) d.appendChild(T.picture(T.photoUrl(n, 's'))); });
      label = x.ns.length > 1 ? T.fill(W.tl_photos, {n: x.ns.length, spot: spotName(x.spot)}) : spotName(x.spot);
    }
    d.appendChild(el('span', '', label));
    var hb = el('i', 'tl-ph-h r'); hb.setAttribute('data-edge', 'b'); d.appendChild(hb);
    row.appendChild(d);
  });
  $('tlPhotos').textContent = ''; $('tlPhotos').appendChild(row);
  // the clips
  var sel = selPiece(), clips = document.createDocumentFragment();
  ps.forEach(function(p){
    var txt = p.words.map(function(j){ return words[j] ? words[j].w : ''; }).join(' '), zk = zoomKind(p);
    var d = el('div', 'tl-clip' + (p === sel ? ' on' : '') + (p.speed !== 1 ? ' fast' : ''));
    d.setAttribute('data-w', p.words[0]);
    d.style.left = X(p.at) + 'px'; d.style.width = Math.max(CLIP_MIN, p.dur * PPS - 2) + 'px';
    d.title = T.fill(W.tl_clip_title, {words: txt});
    var ha = el('i', 'tl-clip-h'); ha.setAttribute('data-cedge', 'a'); d.appendChild(ha);
    if (TLSEL === 'clip' && p === sel) d.appendChild(round_x(W.tl_clip_x));
    if (p.speed !== 1) d.appendChild(el('b', 'bd', T.fill(W.speed_x, {v: p.speed})));
    if (zk) d.appendChild(el('b', 'bd', zk === 'punch' ? W.punch : W.slow_zoom));
    d.appendChild(el('span', '', txt));
    var hb = el('i', 'tl-clip-h r'); hb.setAttribute('data-cedge', 'b'); d.appendChild(hb);
    clips.appendChild(d);
  });
  $('tlClips').textContent = ''; $('tlClips').appendChild(clips);
  // the words, when zoomed in enough to read them
  var show = PPS >= WORDS_AT, under = document.createDocumentFragment();
  if (show) ps.forEach(function(p){
    p.words.forEach(function(j){
      var w = words[j]; if (!w) return;
      var a = Math.max(w.start, p.from), b = Math.min(w.end, p.to), sp = el('span', 'tl-w', w.w);
      sp.style.left = X(p.at + (a - p.from) / p.speed) + 'px'; sp.style.width = Math.max(6, (b - a) / p.speed * PPS) + 'px';
      under.appendChild(sp);
    });
  });
  $('tlWords').classList.toggle('off', !show);
  $('tlWords').textContent = ''; $('tlWords').appendChild(under);
  $('tlHint').textContent = show ? W.tl_hint_words : W.tl_hint;
  toolState();
  var R = T.reelAt(vid.currentTime || 0);
  $('tlTime').textContent = fmt(R) + ' / ' + fmt(tot);
  moveHead(R);
}
// the chips are made once; a press looks up the clip picked at that moment
var speedChips = SPEEDS.map(function(v){
  var b = el('button', 'chip', T.fill(W.speed_x, {v: v}));
  b.type = 'button'; b.disabled = true; b.setAttribute('data-v', v);
  b.addEventListener('click', function(){ speedClip(v); });
  $('tlSpeed').appendChild(b);
  return b;
});
var zoomChips = MOVES.map(function(m){
  var b = el('button', 'chip', m[1]);
  b.type = 'button'; b.disabled = true; b.setAttribute('data-z', m[0]);
  b.addEventListener('click', function(){ zoomClip(m[0]); });
  $('tlZoom').appendChild(b);
  return b;
});
function toolState(){
  var p = selPiece(), zk = zoomKind(p);
  var ph = TLSEL === 'photo' && !!T.findShot(T.SELSHOT);
  $('tlCut').disabled = !(ph || (TLSEL === 'clip' && p));
  $('tlCut').textContent = ph ? W.delete_photo : W.delete_clip;
  speedChips.forEach(function(b, k){
    var on = !!p && p.speed === SPEEDS[k];
    b.disabled = !p; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  zoomChips.forEach(function(b, k){
    var on = !!p && zk === MOVES[k][0];
    b.disabled = !p; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  T.undoButtons();
}
function moveHead(R, playing){
  if ($('tl').hidden) return;
  var x = X(R);
  $('tlHead').style.left = x + 'px';
  if (playing && (x < track.scrollLeft + FOLLOW_L || x > track.scrollLeft + track.clientWidth - FOLLOW_R)) track.scrollLeft = x - track.clientWidth * 0.25;
}
function seekReel(R){
  try { vid.currentTime = T.srcAt(cl(R, 0, Math.max(0, T.total() - 0.02))); } catch (e) {}
  if (vid.paused) T.frame();
}
function reelFromX(cx){ var r = track.getBoundingClientRect(); return (cx - r.left + track.scrollLeft - PAD) / PPS; }
// every word kept, with where it starts and ends on the reel
function keptReel(){
  var words = T.REC.words || [], out = [];
  T.P().forEach(function(p){
    p.words.forEach(function(j){
      var w = words[j]; if (!w) return;
      out.push({i: j, s: p.at + (Math.max(w.start, p.from) - p.from) / p.speed, e: p.at + (Math.min(w.end, p.to) - p.from) / p.speed});
    });
  });
  return out;
}
function picked(){ T.markPicked(); T.markShot(); }

// ---- a press on the track: scrub, pick, or take hold of an end ----
track.addEventListener('pointerdown', function(e){
  if (e.button !== 0 || e.ctrlKey || drag || !T.ready()) return;      // a Control-click is the Mac's right click
  var t = e.target;
  if (!t || !t.closest) return;
  if (t.closest('.tl-x')) { e.preventDefault(); deleteSelected(); return; }      // the little x on what is picked
  var clip = t.closest('.tl-clip'), ph = t.closest('.tl-ph'), edge = t.closest('.tl-ph-h'), cedge = t.closest('.tl-clip-h');
  try { track.setPointerCapture(e.pointerId); } catch (err) {}
  if (cedge && clip) {
    drag = {cedge: cedge.getAttribute('data-cedge'), w0: +clip.getAttribute('data-w'), x: e.clientX, moved: false, id: e.pointerId};
    SELW = drag.w0;
    return;
  }
  if (edge && ph) {
    drag = {edge: edge.getAttribute('data-edge'), a: +ph.getAttribute('data-a'), x: e.clientX, moved: false, id: e.pointerId};
    T.SELSHOT = drag.a; T.markShot();
    return;
  }
  if (clip) { SELW = +clip.getAttribute('data-w'); TLSEL = 'clip'; }
  else if (ph) { SELW = null; TLSEL = 'photo'; }
  else { SELW = null; TLSEL = null; }
  if (ph) {
    T.SELSHOT = +ph.getAttribute('data-a');
    var bar = document.querySelector('#script .seg[data-a="' + T.SELSHOT + '"]');
    if (bar) bar.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }
  drag = {x: e.clientX, moved: false, id: e.pointerId};
  seekReel(reelFromX(e.clientX));
  renderTimeline(); picked();
});
track.addEventListener('pointermove', function(e){
  var d = drag; if (!d) return;
  // the button was let go where the page never heard of it: the drag is over and nothing is saved
  if (e.pointerType === 'mouse' && !(e.buttons & 1)) { endDrag(null, true); return; }
  if (Math.abs(e.clientX - d.x) > CLICK_PX) d.moved = true;
  var R = cl(reelFromX(e.clientX), 0, T.total()), box;
  if (d.cedge) {                                   // the talking: picture and sound together
    var p = pieceOf(d.w0); box = document.querySelector('#tlClips .tl-clip[data-w="' + d.w0 + '"]');
    if (p && box) {
      if (d.cedge === 'a') { box.style.left = X(R) + 'px'; box.style.width = Math.max(4, (p.at + p.dur - R) * PPS) + 'px'; }
      else box.style.width = Math.max(4, (R - p.at) * PPS) + 'px';
    }
  }
  if (d.edge) {                                    // a photo, stretched or shrunk
    var x = T.findShot(d.a), sp = x ? T.shotSpan(x) : null; box = document.querySelector('#tlPhotos .tl-ph[data-a="' + d.a + '"]');
    if (sp && box) {
      if (d.edge === 'a') { box.style.left = X(R) + 'px'; box.style.width = Math.max(10, (sp[1] - R) * PPS) + 'px'; }
      else box.style.width = Math.max(10, (R - sp[0]) * PPS) + 'px';
    }
  }
  seekReel(R);
});
function endDrag(e, cancel){
  var d = drag; drag = null; if (!d) return;
  try { track.releasePointerCapture(d.id); } catch (err) {}
  if (cancel === true) { renderTimeline(); return; }
  var R = reelFromX(e.clientX);
  if (d.cedge) { trimClip(d, R); return; }
  if (!d.edge) return;
  if (!d.moved) { renderTimeline(); return; }
  var x = T.findShot(d.a), kw = keptReel();
  if (!x || !kw.length) { renderTimeline(); return; }
  var at = function(w){ return d.edge === 'a' ? w.s : w.e; };
  var near = kw.reduce(function(best, w){ return Math.abs(at(w) - R) < Math.abs(at(best) - R) ? w : best; }, kw[0]);
  var a = d.edge === 'a' ? near.i : x.a, b = d.edge === 'b' ? near.i : x.b;
  if (a > b) { T.toast(W.no_words_left); renderTimeline(); return; }
  if (a === x.a && b === x.b) { renderTimeline(); return; }
  T.SELSHOT = a;
  T.save(function(){
    var c = T.findShot(d.a); if (!c) return null;                    // the stretch as it is now, by its start word
    var keep = {ns: c.ns, v: c.v, from: c.from, spot: c.spot, pos: c.pos, me: c.me};      // a video keeps its video and its start point
    return {shots: T.shotsOut(T.setRange(T.SH.filter(function(y){ return y.a !== d.a; }), a, b, keep))};
  }).then(function(ok){ if (ok !== true) renderTimeline(); });
  T.toast(T.fill(W.photo_now_on, {words: T.wordsOf(a, b, 40)}));
}
track.addEventListener('pointerup', function(e){ endDrag(e, false); });
track.addEventListener('pointercancel', function(){ endDrag(null, true); });
document.addEventListener('contextmenu', function(){ endDrag(null, true); });
addEventListener('blur', function(){ endDrag(null, true); });
T.busy(function(){ return !!drag; });

// ---- the timeline's own zoom: the spot under the mouse (or the line) stays where it is ----
function zoomTimeline(v, anchorX){
  var r = track.getBoundingClientRect();
  var ax = anchorX == null ? X(T.reelAt(vid.currentTime || 0)) - track.scrollLeft : anchorX - r.left;
  var R = (ax + track.scrollLeft - PAD) / PPS;
  $('tlScale').value = cl(v, 0, 100);
  renderTimeline();
  track.scrollLeft = X(R) - ax;
}
$('tlScale').addEventListener('input', function(){ zoomTimeline(+$('tlScale').value); });
$('tlIn').addEventListener('click', function(){ zoomTimeline(+$('tlScale').value + NUDGE); });
$('tlOut').addEventListener('click', function(){ zoomTimeline(+$('tlScale').value - NUDGE); });
track.addEventListener('wheel', function(e){
  if (e.ctrlKey || e.metaKey) { e.preventDefault(); zoomTimeline(+$('tlScale').value - e.deltaY * WHEEL, e.clientX); }
  else if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); track.scrollLeft += e.deltaY; }      // a plain wheel: sideways
}, {passive: false});

// ---- Split, a clip's ends, Delete, Speed, Zoom ----
$('tlSplit').addEventListener('click', function(){
  var t = vid.currentTime || 0, i = T.pieceAt(t), words = T.REC.words || [];
  if (i < 0) { T.toast(W.split_no_clip); return; }
  var p = T.P()[i];
  if (p.words.length < 2) { T.toast(W.split_one_word); return; }
  var best = null, bd = Infinity;
  for (var j = 1; j < p.words.length; j++) {
    var m = (words[p.words[j - 1]].end + words[p.words[j]].start) / 2, d = Math.abs(m - t);
    if (d < bd) { bd = d; best = p.words[j]; }
  }
  SELW = best;
  T.save(function(){
    var s = (T.REC.splits || []).slice();
    if (s.indexOf(best) < 0) s.push(best);
    return {splits: s};
  });
  T.toast(T.fill(W.split_before, {word: words[best].w}));
});
// words to cut, or to bring back, applied to the cuts as they are when the save's turn comes
function saveCut(list, add){
  return T.save(function(){
    var s = T.cutSet();
    list.forEach(function(i){ if (add) s.add(i); else s['delete'](i); });
    return {cut: T.toRanges(s)};
  });
}
// The sound and the picture are one (Nicole, Nov 11). A clip's end dragged in cuts those words (both); dragged
// out it brings back the cut words next to it. Always to the nearest word.
function trimClip(d, R){
  var p = pieceOf(d.w0);
  if (!d.moved || !p) { renderTimeline(); return; }
  var words = T.REC.words || [], cs = T.cutSet(), end = p.at + p.dur, n = p.words.length, said = [], list = [], j, k;
  var rs = function(i){ return p.at + (Math.max(words[i].start, p.from) - p.from) / p.speed; };      // a word's start on the reel
  var take = function(i){ list.push(i); said.push(words[i].w); };
  if (d.cedge === 'b' && R < end) {                // in from the end: the words after the nearest gap
    k = n;
    for (j = 0; j < n; j++) if (Math.abs(rs(p.words[j]) - R) < Math.abs((k < n ? rs(p.words[k]) : end) - R)) k = j;
    p.words.slice(k).forEach(take);
  } else if (d.cedge === 'a' && R > p.at) {        // in from the start: the words before the nearest gap
    var bnd = function(q){ return q === 0 ? p.at : q < n ? rs(p.words[q]) : end; };
    k = 0;
    for (j = 1; j <= n; j++) if (Math.abs(bnd(j) - R) < Math.abs(bnd(k) - R)) k = j;
    p.words.slice(0, k).forEach(take);
  } else {                                         // out: the cut words right beside it
    var extra = (d.cedge === 'b' ? R - end : p.at - R) * p.speed;
    if (d.cedge === 'b') { for (j = p.words[n - 1] + 1; j < words.length && cs.has(j) && words[j].start <= p.to + extra; j++) take(j); }
    else { var back = []; for (j = p.words[0] - 1; j >= 0 && cs.has(j) && words[j].end >= p.from - extra; j--) back.unshift(j); back.forEach(take); }
    if (!list.length) { T.toast(W.nothing_back); renderTimeline(); return; }
    saveCut(list, false).then(function(ok){ if (ok !== true) renderTimeline(); });
    T.toast(T.fill(W.brought_back, {words: said.join(' ')}));
    return;
  }
  if (!list.length) { renderTimeline(); return; }
  saveCut(list, true).then(function(ok){ if (ok !== true) renderTimeline(); });
  T.toast(T.fill(W.cut_said, {words: said.join(' ')}));
}
function cutClip(){
  var p = selPiece(); if (!p) return;
  var list = p.words.slice();
  SELW = null;
  saveCut(list, true);
  T.toast(W.cut_clip);
}
function deleteSelected(){
  if (TLSEL === 'photo') {
    var a = T.SELSHOT;
    if (!T.findShot(a)) return;
    T.SELSHOT = null; TLSEL = null;
    T.save(function(){ return T.findShot(a) ? {shots: T.shotsOut(T.SH.filter(function(y){ return y.a !== a; }))} : null; });
    T.toast(W.photo_deleted);
    renderTimeline(); picked();
  } else if (TLSEL === 'clip' || selPiece()) {
    cutClip(); TLSEL = null;
    renderTimeline(); picked();
  }
}
$('tlCut').addEventListener('click', deleteSelected);
function speedClip(v){
  var p = selPiece(); if (!p) return;
  var a = p.words[0], b = p.words[p.words.length - 1];
  T.save(function(){
    return {speeds: T.setRange(T.REC.speeds || [], a, b, v === 1 ? null : {v: v}).map(function(r){ return {a: r.a, b: r.b, v: r.v}; })};
  });
}
function zoomClip(kind){
  var p = selPiece(); if (!p) return;
  var a = p.words[0], b = p.words[p.words.length - 1];
  T.save(function(){
    return {zooms: T.setRange(T.ZL, a, b, kind ? {kind: kind} : null).map(function(r){ return {a: r.a, b: r.b, kind: r.kind}; })};
  });
}

// ---- the keys: Undo, Redo, Delete (the spacebar is the preview's) ----
document.addEventListener('keydown', function(e){
  var tg = e.target;
  if (tg && tg.closest && tg.closest('textarea,[contenteditable],select,input:not([type=checkbox]):not([type=range])')) return;
  if ($('editStep').hidden || (T.pickerOpen && T.pickerOpen())) return;      // never behind an open picker
  var mod = e.metaKey || e.ctrlKey, k = String(e.key || '').toLowerCase();
  if (mod && !e.altKey && k === 'z') { e.preventDefault(); if (e.shiftKey) T.redo(); else T.undo(); }
  else if (mod && !e.altKey && k === 'y') { e.preventDefault(); T.redo(); }
  else if ((e.key === 'Delete' || e.key === 'Backspace') && !mod && TLSEL && !T.selectedWords()) { e.preventDefault(); deleteSelected(); }
}, true);

// ---- Make it in CapCut, and the result box ----
function box(lines, bad){
  var r = $('result'), s = el('div', 'step');
  if (bad) { var p = el('p', 'status bad', lines[0]); p.setAttribute('role', 'alert'); s.appendChild(p); }
  else {
    s.appendChild(el('h2', '', W.made_h2));
    lines.forEach(function(t){ s.appendChild(el('p', '', t)); });
    var say = el('p', 'say', W.made_say); say.style.marginTop = '.6rem'; s.appendChild(say);
  }
  r.textContent = ''; r.appendChild(s);
  try { r.scrollIntoView({behavior: 'smooth'}); } catch (e) {}
}
function setMaking(on){
  T.makeReady = !on;
  $('makeBtn').textContent = on ? W.making : W.make;
  T.summary();
}
var watching = null, lost = 0;
// The make this page follows can no longer be seen (its record gone, the shoot's drive unplugged, the Assistant out
// of reach): after a few answers in a row like that the button comes back and plain words say so. Never a page
// left on "Making it…".
function unseen(line){
  if (++lost < MAKE_LOST) return;
  lost = 0; making = null; setMaking(false);
  box([line], true);
}
function watch(){
  if (watching) return;
  watching = setInterval(function(){
    if (making == null || making === true) { if (making == null) { clearInterval(watching); watching = null; } return; }
    var id = making;
    // only how the make stands is asked for: the 3-second look brings everything else, at a calm moment
    T.ask('/talking-state?' + Q + '&only=make').then(function(res){
      if (making !== id) return;
      var m = res.j && res.j.ok !== false ? res.j.make : null;
      if (m && m.id) { lost = 0; showMake(m); }
      else unseen(res.j ? W.make_went_wrong : W.cant_reach);
    }, function(){ if (making === id) unseen(W.cant_reach); });
  }, MAKE_EVERY);
}
function showMake(m){
  if (!m || !m.id || making === true) return;
  var atWork = m.state === 'queued' || m.state === 'running';
  if (making == null) {                            // a page opened while a make is at work follows it
    if (atWork) {
      making = m.id; lost = 0;
      if ($('result').querySelector('.status.bad')) $('result').textContent = '';      // an earlier "couldn't" line is over
      setMaking(true); watch();
    }
    return;
  }
  if (m.id !== making) {                           // a newer make than the one followed: that one is the one to follow, or nothing
    if (atWork) { making = m.id; lost = 0; return; }
    making = null; setMaking(false); return;
  }
  if (atWork) return;
  making = null; setMaking(false);
  if (m.state === 'done') box((m.words || []).map(String), false);
  else box([m.problem || W.make_went_wrong], true);
}
$('makeBtn').addEventListener('click', function(){
  if (making != null || !T.loaded) return;
  making = true; setMaking(true);
  var stop = function(line){ making = null; setMaking(false); box([line], true); };
  // any save still on its way goes first: what is made is what the page shows
  T.save(function(){ return null; }).then(function(){ return T.post('/talking-make', {kit: T.KIT}); }).then(function(res){
    var j = res.j || {};
    if (res.code === 200 && j.ok && j.job && j.job.id) { making = j.job.id; lost = 0; watch(); showMake(j.job); }
    else stop(j.words || W.make_went_wrong);
  }, function(){ stop(W.cant_reach); });
});
T.on('make', showMake);

// ---- the time, the line, a new state, a new size ----
T.on('frame', function(f){
  $('tlTime').textContent = fmt(f.R) + ' / ' + fmt(T.total());
  moveHead(f.R, f.playing);
});
T.on('shot', function(){
  each('#tlPhotos .tl-ph', function(e){ e.classList.toggle('on', +e.getAttribute('data-a') === T.SELSHOT); });
  var x = document.querySelector('#tlPhotos .tl-x');
  // the little x always sits on the stretch that Delete would take
  if (TLSEL === 'photo' && !drag && !(x && +x.parentNode.getAttribute('data-a') === T.SELSHOT)) renderTimeline(); else toolState();
});
var dockWas = 0;
T.on('apply', function(a){
  showMake(T.ST.make);
  if (!a.ready) { if (drag) endDrag(null, true); SELW = null; TLSEL = null; return; }
  if (a.changed || !$('tlClips').firstChild) {
    if (TLSEL === 'photo' && !T.findShot(T.SELSHOT)) TLSEL = null;
    if (drag && (drag.cedge || drag.edge)) toolState(); else renderTimeline();      // never under a held end: drawn at the drop
    T.markPicked();
  } else toolState();
  var h = $('dock').offsetHeight;
  if (h !== dockWas) { dockWas = h; T.sizeDock(); if (vid.paused && T.frame) T.frame(); }
});
T.on('resize', function(){ if (T.ready() && !drag) renderTimeline(); });
T.on('photos', function(){ if (T.ready() && !drag) renderTimeline(); });

T.makeReady = true;
T.pickedWords = function(){ var p = selPiece(); return p ? p.words : []; };
T.renderTimeline = renderTimeline;
T.tl = function(){ return {pps: PPS, selw: SELW, sel: TLSEL, drag: !!drag, making: making}; };
T.tlFmt = fmt; T.tlTick = fmtTick;
})();
"""
