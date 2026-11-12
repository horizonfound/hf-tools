#!/usr/bin/env python3
"""The talking reel page's script, the preview (Nicole's handoff v24, pages/talking-reel.html, built our way): the
tall screen beside the script, playing the cut or the whole video, a photo or a video where it will sit, themselves
in the corner, the zooms, the captions, the phone guides, and step 3's chips. One string of JavaScript and nothing
else. It stands on talking_js_core.py (window.Talk) and talking_js_script.py.

Hers, kept number for number (each has its check in tests/talking_page_check.py --only preview):
  - playing: a press on the preview, the round button on the timeline or the spacebar plays and pauses. "Play the
    cut version" (ticked as the page opens, remembered nowhere) skips what is cut, plays a sped-up piece at its
    speed, and at the end of the reel pauses and goes back to the first piece; unticked, the whole video plays at
    its own speed. The speed is put back to 1 on pause. On a cut word, play starts at the next piece kept;
  - the word being said is lit from its start to 0.05 s past its end; the sentence lit is the piece's own, and
    outside a piece the one from 0.15 s before its first word to 0.3 s past its last;
  - where things sit before they are moved, the same numbers CapCut gets: Center {x .5, y .44, w .704}; Small
    corner w .352, 4.6% from the right, 7.3% from the top; themselves in the corner w .36, 50 px from the left
    and 60 px from the bottom of a 1080x1920 frame; captions at {x .5, y .71};
  - several photos on one stretch flash through it, each for an equal share of the stretch's time on the reel;
    a Footage video plays without its sound, kept in step with the reel (set again when it is 0.35 s out);
  - dragging: under 3 px is a click (it only picks the stretch); a photo moves only in Center and Small corner;
    its round handle makes it bigger or smaller (width .1 to 1.6) with its top left corner staying put;
    themselves in the corner the same (.12 to 1; a box that share of the screen wide AND tall); the caption's
    spot is held to .02 to .98; the caption's handle sizes it by start x (1 + (dx + dy) x 3), held to .4 to 3,
    rounded to .01;
  - a punch in is 1.15; a slow zoom grows by .12 across its whole span (never under .1 s), and shows 1.06 outside
    a piece; neither shows while they are in the corner; the zoom turns around 50% 45% and eases over .25 s (the
    styles);
  - captions: one word at a time, its size the screen's height x .035 x their size; its handle sits on the
    word's bottom right corner and is there only while a word shows; "Put the captions back to how they were"
    shows only when the spot or the size was changed;
  - the phone guides are remembered by this browser under the key talkGuides.
Her faults, fixed (the plan, 2c):
  - nothing here holds a stretch across a refresh: a drag remembers its START WORD, and what to save is built
    when the save's turn comes, from the stretch as it is then. Nothing on the page is changed in place: what a
    drag has in hand (`held`) is drawn over the state until its save's answer is on the page;
  - the spacebar does nothing while either picker is open (hers played the talking video behind the video picker),
    nor while the photo menu is open (the same reason), and it is left to a button, a tick or a slider that was
    reached WITH THE KEYBOARD (the Tab key, with no press of the mouse since), so that one is pressed, as anywhere
    else. After a mouse click on a button it plays and pauses, as hers;
  - a Footage video shorter than the words it sits on stays on its last frame (hers, once the video had ended,
    started it again and threw it back to its end, over and over, until the stretch was done);
  - when the talking video itself runs out in the cut version (the last piece kept goes to its very end), the
    time goes back to the first piece, as at any other end of the reel.
Ours:
  - a drag ends, saving nothing, when the button was let go where the page never saw it, on the Mac's own menu,
    or when the window loses the keyboard; a Control-click starts none; the 3-second look waits during a drag;
  - the press that ended a drag never plays or pauses, and the next press always works (hers could swallow one);
  - a hidden page gets no animation frames: what is cut is still skipped then, on the video's own time events;
  - a photo with no small copy yet, or a Footage video that can't be played, shows nothing rather than a broken
    picture; a Footage video shows its first still until its first frame is there; a video that has gone shows
    nothing. With nothing to show there is no box to move and no handle;
  - a picture or a Footage video that could not be loaded is asked for again, never on every frame: a few
    seconds later (4 s, then 8, 16, 30 at most, while that stretch is the one showing), when the video picker
    closes (it may just have had the small copy made), and on a new state. No reload is needed;
  - the lit word and sentence come back by themselves when the script is drawn again.

What the timeline's part uses from here: T.frame(playing) (it says 'frame' {t, R, playing} to whoever listens:
the time and the line), T.togglePlay(), T.shotNow(), T.shotSpan(x), T.sentenceAt(t), T.zoomSpan(k), T.mediaOf(x, k),
T.defPos(spot, w, h), T.ME, T.CAP, T.previewDrag(). The keys other than the spacebar are the timeline's.
"""

JS = r"""
(function(){
'use strict';
var T = window.Talk, W = T.W, $ = T.$, Q = T.Q;
var vid = $('vid'), bv = $('bvid'), sc = $('screen'), wrap = $('phFront'), img = wrap.querySelector('img'), capEl = $('cap');
// hers, the same numbers CapCut gets
var ME = {x: (50 + 1080 * 0.36 / 2) / 1080, y: (1920 - 60 - 1920 * 0.36 / 2) / 1920, w: 0.36};     // them, small, bottom left
var CAP = {x: 0.5, y: 0.71};
var CLICK_PX = 3, PUNCH = 1.15, SLOW = 0.12, SLOW_OUTSIDE = 1.06, RESEEK = 0.35, CAP_SHARE = 0.035;
var pdrag = null;              // a drag on the preview
var held = null;               // what that drag has in hand: {a, pos} | {a, me} | {cap_pos} | {cap_size}
var swallow = false;           // the press that just ended was a drag's: its click neither plays nor pauses
var ticking = false;
var RETRY_MS = 4000, RETRY_MOST = 30000;
var bad = {};                  // an address that could not be loaded: {n, until}; asked for again after `until`
// a button, a tick or a slider: the spacebar is its own when it was reached with the keyboard
var PRESSED_BY_SPACE = 'button,summary,input[type=checkbox],input[type=range]';

function ratio(p){ return p && p.w > 0 && p.h > 0 ? p.h / p.w : 1; }
function defPos(spot, w, h){            // where a photo sits before it is moved
  if (spot === 'center') return {x: 0.5, y: 0.44, w: 0.704};
  var hf = 0.352 * 9 / 16 * ratio({w: w, h: h});
  return {x: 1 - 0.046 - 0.176, y: 0.073 + hf / 2, w: 0.352};
}
function cl(v, a, b){ return Math.min(b, Math.max(a, v)); }
function r4(v){ return Math.round(v * 10000) / 10000; }

// ---- what shows for a stretch: one of its photos, or its video ----
function mediaOf(x, k){
  if (x.v) {
    if (x.v.gone || !x.v.key) return null;
    // its shape: the state's own first (it rides on the stretch, so a wide video is drawn wide from the first
    // frame after a reload: the Footage list is only asked for when the picker opens), then the list, then the video
    var w = +x.v.w || 0, h = +x.v.h || 0, vs = T.vids ? T.vids() : [];
    if (!(w > 0 && h > 0)) for (var i = 0; i < vs.length; i++) if (vs[i].key === x.v.key) { w = vs[i].w; h = vs[i].h; }
    if (!(w > 0 && h > 0) && bv.dataset.key === x.v.key && bv.videoWidth) { w = bv.videoWidth; h = bv.videoHeight; }
    return {video: true, key: x.v.key, w: w > 0 ? w : 1080, h: h > 0 ? h : 1920};
  }
  var n = (x.ns || [])[k || 0], p = T.byN[n];
  return p && !p.missing ? {n: n, w: p.w, h: p.h, have: !!p.have} : null;
}
function boxOf(x, p){ return (held && held.a === x.a && held.pos) || x.pos || defPos(x.spot, p.w, p.h); }
function meOf(x){ return (held && held.a === x.a && held.me) || x.me || ME; }
function capPos(){ return (held && held.cap_pos) || T.REC.cap_pos || CAP; }
function capSize(){ return (held && held.cap_size) || T.REC.cap_size || 1; }

// ---- time (hers) ----
function sentenceAt(t){
  var ws = T.REC.words || [], ss = T.REC.sentences || [];
  for (var k = 0; k < ss.length; k++) {
    var a = ws[ss[k][0]], b = ws[ss[k][1]];
    if (a && b && t >= a.start - 0.15 && t <= b.end + 0.3) return k;
  }
  return -1;
}
function shotSpan(x){
  var on = T.P().filter(function(p){ return p.words[0] >= x.a && p.words[0] <= x.b; });
  return on.length ? [on[0].at, on[on.length - 1].at + on[on.length - 1].dur] : null;
}
function shotAt(i){ for (var k = 0; k < T.SH.length; k++) if (i >= T.SH[k].a && i <= T.SH[k].b) return T.SH[k]; return null; }
// the stretch showing now, and which of its photos
function shotNow(){
  var t = vid.currentTime || 0, i = T.pieceAt(t), x;
  if (i >= 0) {
    x = shotAt(T.P()[i].words[0]);
    if (!x) return null;
    var n = (x.ns || []).length || 1, sp = shotSpan(x), R = T.reelAt(t);
    if (!sp) return {x: x, k: 0};
    return {x: x, k: Math.max(0, Math.min(n - 1, Math.floor((R - sp[0]) / ((sp[1] - sp[0]) / n))))};
  }
  var ws = T.REC.words || [];
  for (var j = 0; j < ws.length; j++) if (t >= ws[j].start - 0.1 && t <= ws[j].end + 0.3) { x = shotAt(j); return x ? {x: x, k: 0} : null; }
  return null;
}
function zoomSpan(k){
  var a = Infinity, b = -Infinity;
  T.P().forEach(function(p){ if (p.zoom === k) { a = Math.min(a, p.at); b = Math.max(b, p.at + p.dur); } });
  return [a, b];
}

// ---- the preview: everything where it will be ----
function mark(sel, want, cls){
  Array.prototype.forEach.call(document.querySelectorAll(sel), function(e){ if (e !== want) e.classList.remove(cls); });
  if (want && !want.classList.contains(cls)) want.classList.add(cls);
}
function place(el, l, t, w, h){ el.style.left = l * 100 + '%'; el.style.top = t * 100 + '%'; el.style.width = w * 100 + '%'; el.style.height = h * 100 + '%'; }
function knob(id, cx, cy){ var e = $(id); e.style.display = 'block'; e.style.left = cx * 100 + '%'; e.style.top = cy * 100 + '%'; }
// ---- what could not be loaded: nothing shows, and it is asked for again at a calm moment ----
function isBad(u){ var b = bad[u]; return !!b && Date.now() < b.until; }
function failed(u){
  if (!u) return;
  var b = bad[u] || {n: 0};
  b.n++; b.until = Date.now() + Math.min(RETRY_MOST, RETRY_MS * Math.pow(2, b.n - 1)); bad[u] = b;
  setTimeout(function(){ if (T.ready() && vid.paused && !pdrag) frame(); }, b.until - Date.now() + 30);
}
function forgive(){ bad = {}; }
// true when there is a picture to show (it may still be on its way)
function picture(src){
  if (!src || isBad(src)) { img.style.display = 'none'; return false; }
  if (img.getAttribute('src') !== src || img.dataset.failed) { delete img.dataset.failed; img.src = src; }
  img.style.display = 'block';
  return true;
}
img.addEventListener('error', function(){
  failed(img.getAttribute('src') || '');
  img.dataset.failed = '1'; img.style.display = 'none';
  if (T.ready() && vid.paused) frame();
});
bv.addEventListener('error', function(){
  var u = bv.dataset.src;
  if (!u) return;
  failed(u);
  delete bv.dataset.src; delete bv.dataset.key;
  bv.removeAttribute('src');
  try { bv.load(); } catch (e) {}
  if (T.ready() && vid.paused) frame();
});
function quietVideo(){ if (!bv.paused) { try { bv.pause(); } catch (e) {} } }

function frame(playing){
  if (!T.ready()) return;
  var t = vid.currentTime || 0, ps = T.P(), i = T.pieceAt(t), pc = i >= 0 ? ps[i] : null, R = T.reelAt(t);
  var ws = T.REC.words || [], wi = -1, j;
  for (j = 0; j < ws.length; j++) if (t >= ws[j].start && t <= ws[j].end + 0.05) { wi = j; break; }
  var k = pc ? pc.sentence : sentenceAt(t);
  mark('#script .words span.speaking', wi >= 0 ? T.wordEl(wi) : null, 'speaking');
  mark('#script .sent.now', k >= 0 ? document.querySelector('#script .sent[data-k="' + k + '"]') : null, 'now');

  // the photo or the video: where it sits, and where they put it
  var cur = shotNow(), x = cur && cur.x, p = x ? mediaOf(x, cur.k) : null;
  sc.classList.remove('pip');
  wrap.style.display = 'none'; $('phKnob').style.display = 'none'; $('meKnob').style.display = 'none';
  wrap.classList.remove('movable'); vid.classList.remove('movable');
  vid.style.left = vid.style.top = vid.style.width = vid.style.height = '';
  if (p) {
    var shown;                                       // is there anything to show for it?
    if (p.video) {                                   // their footage, without its sound, in step with the reel
      var url = '/reel-video?' + Q + '&key=' + encodeURIComponent(p.key);
      if (bv.dataset.src !== url && !isBad(url)) { bv.dataset.src = url; bv.dataset.key = p.key; bv.src = url; }
      var mine = bv.dataset.src === url, there = mine && bv.readyState >= 2;
      bv.style.display = there ? 'block' : 'none';
      shown = picture(there ? null : T.stillUrl(p.key)) || there;     // its first still until its first frame is there
      if (mine) {
        var sp = shotSpan(x), target = (x.from || 0) + Math.max(0, R - (sp ? sp[0] : R)), over = false;
        if (bv.duration > 0.1) { over = target >= bv.duration - 0.05; target = Math.min(target, bv.duration - 0.05); }
        var out = Math.abs(bv.currentTime - target) > RESEEK;
        if (bv.readyState > 0 && out) { try { bv.currentTime = target; } catch (e) {} }
        // shorter than the words it sits on: it stays on its last frame (never started again from its beginning)
        if (over || (bv.ended && !out)) quietVideo();
        else if (!vid.paused && bv.paused && bv.readyState > 0) { var pl = bv.play(); if (pl && pl.then) pl.then(null, function(){}); }
        if (vid.paused) quietVideo();
      } else quietVideo();
    } else {
      bv.style.display = 'none'; quietVideo();
      shown = picture(p.have ? T.photoUrl(p.n, 'l') : null);
    }
    if (shown) {                                     // with nothing to show there is no box to move and no handle
      wrap.style.display = 'block';
      if (x.spot === 'center' || x.spot === 'corner') {
        var bx = boxOf(x, p), hf = bx.w * 9 / 16 * ratio(p);
        place(wrap, bx.x - bx.w / 2, bx.y - hf / 2, bx.w, hf);
        wrap.classList.add('movable'); knob('phKnob', bx.x + bx.w / 2, bx.y + hf / 2);
      } else place(wrap, 0, 0, 1, 1);
    }
    if (x.spot === 'pip') {                          // themselves, small, over the photo: that share of the screen wide AND tall
      var m = meOf(x);
      sc.classList.add('pip'); vid.classList.add('movable');
      place(vid, m.x - m.w / 2, m.y - m.w / 2, m.w, m.w);
      knob('meKnob', m.x + m.w / 2, m.y + m.w / 2);
    }
  } else quietVideo();

  // the zoom (never while they are in the corner)
  var z = 1, zk = pc ? pc.zoom : null, kind = zk != null && T.ZL[zk] ? T.ZL[zk].kind : (pc ? '' : T.zoomOf(wi));
  if (kind === 'punch') z = PUNCH;
  if (kind === 'zoom') {
    var zs = zk != null ? zoomSpan(zk) : [NaN, NaN];
    z = isFinite(zs[0]) ? 1 + SLOW * Math.min(1, Math.max(0, (R - zs[0]) / Math.max(0.1, zs[1] - zs[0]))) : SLOW_OUTSIDE;
  }
  vid.style.transform = sc.classList.contains('pip') ? '' : 'scale(' + z + ')';

  // the caption: one word, where they put it, the same share of the screen as in CapCut
  var c = null, caps = T.REC.captions !== false ? (T.ST.captions || []) : [];
  for (j = 0; j < caps.length; j++) if (R >= caps[j].start && R < caps[j].end) { c = caps[j]; break; }
  var text = c ? String(c.text) : '';
  if (capEl.textContent !== text) capEl.textContent = text;
  var cp = capPos();
  capEl.style.left = cp.x * 100 + '%'; capEl.style.top = cp.y * 100 + '%';
  capEl.style.fontSize = (sc.clientHeight * CAP_SHARE * capSize()) + 'px';
  if (text) {                                        // its handle sits on the word's bottom right corner
    var r = capEl.getBoundingClientRect(), s0 = sc.getBoundingClientRect();
    if (s0.width && s0.height) knob('capKnob', (r.right - s0.left) / s0.width, (r.bottom - s0.top) / s0.height);
  } else $('capKnob').style.display = 'none';
  T.emit('frame', {t: t, R: R, playing: !!playing});
}

// ---- playing ----
function nextPiece(t){ var ps = T.P(); for (var i = 0; i < ps.length; i++) if (ps[i].from > t) return ps[i]; return null; }
function togglePlay(){
  if (!vid.getAttribute('src') || !T.ready()) return;
  if (!vid.paused) { vid.pause(); return; }
  var ps = T.P();
  if ($('cutMode').checked && ps.length && T.pieceAt(vid.currentTime) < 0) {      // on a cut word: the next piece kept
    try { vid.currentTime = (nextPiece(vid.currentTime) || ps[0]).from; } catch (e) {}
  }
  var p = vid.play();
  if (p && p.then) p.then(null, function(){});
}
// skip what is cut, play a sped-up piece faster, and stop at the end
function step(){
  if (vid.paused) return;
  var t = vid.currentTime, ps = T.P();
  if ($('cutMode').checked && ps.length) {
    var i = T.pieceAt(t);
    if (i < 0) {
      var nx = nextPiece(t);
      try { if (nx) vid.currentTime = nx.from; else { vid.pause(); vid.currentTime = ps[0].from; } } catch (e) {}
    } else if (vid.playbackRate !== ps[i].speed) vid.playbackRate = ps[i].speed;
  } else if (vid.playbackRate !== 1) vid.playbackRate = 1;
}
function tick(){
  if (vid.paused) { ticking = false; return; }
  step(); frame(true);
  requestAnimationFrame(tick);
}
vid.addEventListener('play', function(){
  var b = $('tlPlay'); b.textContent = '❚❚'; b.setAttribute('aria-label', W.pause);
  if (!ticking) { ticking = true; requestAnimationFrame(tick); }
});
vid.addEventListener('pause', function(){
  var b = $('tlPlay'); b.textContent = '▶'; b.setAttribute('aria-label', W.play);
  vid.playbackRate = 1;
  frame();
});
// the talking video itself ran out before a time outside a piece was ever seen: the cut version goes back to the first piece
vid.addEventListener('ended', function(){
  var ps = T.P();
  if ($('cutMode').checked && ps.length) { try { vid.currentTime = ps[0].from; } catch (e) {} }
});
// a page that is not showing gets no animation frames: what is cut is still skipped, on the video's own clock
vid.addEventListener('timeupdate', function(){ if (!vid.paused && document.hidden) step(); });
vid.addEventListener('seeked', function(){ if (vid.paused) frame(); });
vid.addEventListener('loadedmetadata', function(){ if (vid.paused) frame(); });
['loadedmetadata', 'loadeddata', 'seeked'].forEach(function(ev){ bv.addEventListener(ev, function(){ if (vid.paused) frame(); }); });
$('tlPlay').addEventListener('click', togglePlay);
sc.addEventListener('click', function(){
  if (swallow) { swallow = false; return; }
  togglePlay();
});
// the spacebar plays and pauses (the timeline's part has the other keys); never while typing, never with a picker
// or the photo menu open, and never taken from a button, a tick or a slider that was reached with the keyboard
// (the browser's own :focus-visible can't say: Chrome turns it on for a clicked button at the first key pressed)
var tabbed = false;            // the last of {the Tab key, a press of the mouse or a finger} was the Tab key
document.addEventListener('pointerdown', function(){ tabbed = false; }, true);
document.addEventListener('keydown', function(e){ if (e.key === 'Tab') tabbed = true; }, true);
function byKeys(el){
  try { return tabbed && !!el && el.matches(PRESSED_BY_SPACE); } catch (e) { return false; }
}
document.addEventListener('keydown', function(e){
  if (e.code !== 'Space' || e.metaKey || e.ctrlKey || e.altKey) return;
  var tg = e.target;
  if (tg && tg.closest && tg.closest('textarea,[contenteditable],select,input:not([type=checkbox]):not([type=range])')) return;
  if ($('editStep').hidden || (T.pickerOpen && T.pickerOpen())) return;
  if (byKeys(document.activeElement)) return;        // the spacebar presses that one, as anywhere else
  e.preventDefault();
  if (e.repeat || $('pmenu').classList.contains('open')) return;      // never playing behind the open menu
  if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
  togglePlay();
}, true);

// ---- dragging on the preview: a photo, themselves in the corner, the caption, and their round handles ----
sc.addEventListener('pointerdown', function(e){
  swallow = false;
  if (pdrag || e.button !== 0 || e.ctrlKey || !T.ready()) return;      // a Control-click is the Mac's right click
  var t = e.target, kind = null;
  if (t.id === 'phKnob') kind = 'size';
  else if (t.id === 'meKnob') kind = 'mesize';
  else if (t.closest && t.closest('#phFront') && wrap.classList.contains('movable')) kind = 'move';
  else if (t === vid && sc.classList.contains('pip')) kind = 'memove';
  else if (t.id === 'cap') kind = 'cap';
  else if (t.id === 'capKnob') kind = 'capsize';
  if (!kind) return;
  var onShot = kind !== 'cap' && kind !== 'capsize', cur = onShot ? shotNow() : null, x = cur && cur.x, p = x ? mediaOf(x, cur.k) : null;
  if (onShot && !p) return;
  e.preventDefault();
  var st = kind === 'capsize' ? capSize() : kind === 'cap' ? capPos() : (kind === 'memove' || kind === 'mesize') ? meOf(x) : boxOf(x, p);
  pdrag = {kind: kind, a: onShot ? x.a : null, ratio: ratio(p), start: typeof st === 'number' ? st : {x: st.x, y: st.y, w: st.w},
           sx: e.clientX, sy: e.clientY, r: sc.getBoundingClientRect(), moved: false, id: e.pointerId, live: null};
  if (onShot) T.SELSHOT = x.a;
  try { sc.setPointerCapture(e.pointerId); } catch (err) {}
});
sc.addEventListener('pointermove', function(e){
  var d = pdrag; if (!d) return;
  // the button was let go where the page never heard of it: the drag is over and nothing is saved
  if (e.pointerType === 'mouse' && !(e.buttons & 1)) { endDrag(true); return; }
  if (!d.moved && Math.abs(e.clientX - d.sx) + Math.abs(e.clientY - d.sy) > CLICK_PX) d.moved = true;
  if (!d.moved || !d.r.width || !d.r.height) return;
  var dx = (e.clientX - d.sx) / d.r.width, dy = (e.clientY - d.sy) / d.r.height, st = d.start, w;
  if (d.kind === 'move' || d.kind === 'memove') d.live = {x: r4(st.x + dx), y: r4(st.y + dy), w: st.w};
  else if (d.kind === 'size') {                     // the top left corner stays put
    w = cl(st.w + dx, 0.1, 1.6);
    var r = 9 / 16 * d.ratio;
    d.live = {x: r4(st.x - st.w / 2 + w / 2), y: r4(st.y - st.w * r / 2 + w * r / 2), w: r4(w)};
  } else if (d.kind === 'mesize') {
    w = cl(st.w + dx, 0.12, 1);
    d.live = {x: r4(st.x - st.w / 2 + w / 2), y: r4(st.y - st.w / 2 + w / 2), w: r4(w)};
  } else if (d.kind === 'cap') d.live = {x: r4(cl(st.x + dx, 0.02, 0.98)), y: r4(cl(st.y + dy, 0.02, 0.98))};
  else if (d.kind === 'capsize') d.live = Math.round(cl(st * (1 + (dx + dy) * 3), 0.4, 3) * 100) / 100;      // right or down: bigger
  held = d.kind === 'cap' ? {cap_pos: d.live} : d.kind === 'capsize' ? {cap_size: d.live}
       : (d.kind === 'move' || d.kind === 'size') ? {a: d.a, pos: d.live} : {a: d.a, me: d.live};
  frame();
});
function endDrag(cancel){
  var d = pdrag; pdrag = null; if (!d) return;
  try { sc.releasePointerCapture(d.id); } catch (e) {}
  swallow = true;                // the click that may follow this press neither plays nor pauses (the next press clears it)
  if (cancel === true) { held = null; frame(); return; }
  if (!d.moved || d.live == null) { held = null; if (d.a != null) T.markShot(); return; }
  var mine = held, key = (d.kind === 'move' || d.kind === 'size') ? 'pos' : 'me';
  T.save(function(){
    if (d.kind === 'cap') return {cap_pos: d.live};
    if (d.kind === 'capsize') return {cap_size: d.live};
    var c = T.findShot(d.a); if (!c) return null;           // the stretch as it is now, by its start word
    return {shots: T.shotsOut(T.SH.map(function(y){
      if (y !== c) return y;
      var n = {a: y.a, b: y.b, ns: y.ns, v: y.v, from: y.from, spot: y.spot, pos: y.pos, me: y.me};
      n[key] = d.live;
      return n;
    }))};
  }).then(function(){ if (held === mine) { held = null; if (vid.paused) frame(); } });
}
sc.addEventListener('pointerup', function(){ endDrag(false); });
sc.addEventListener('pointercancel', function(){ endDrag(true); });
document.addEventListener('contextmenu', function(){ endDrag(true); });
addEventListener('blur', function(){ endDrag(true); });
T.busy(function(){ return !!pdrag; });

// ---- phone guides, and the cut version ----
try { $('guidesOn').checked = localStorage.getItem('talkGuides') === '1'; } catch (e) { $('guidesOn').checked = false; }
$('guides').hidden = !$('guidesOn').checked;
$('guidesOn').addEventListener('change', function(){
  $('guides').hidden = !$('guidesOn').checked;
  try { localStorage.setItem('talkGuides', $('guidesOn').checked ? '1' : '0'); } catch (e) {}
});
$('cutMode').checked = true;                         // ticked as the page opens, remembered nowhere
$('cutMode').addEventListener('change', function(){ if (vid.paused) frame(); });

// ---- step 3: captions ----
function capChips(){
  var on = T.REC.captions !== false;
  $('capOn').classList.toggle('on', on); $('capOn').setAttribute('aria-pressed', on ? 'true' : 'false');
  $('capOff').classList.toggle('on', !on); $('capOff').setAttribute('aria-pressed', on ? 'false' : 'true');
  $('capReset').hidden = !T.REC.cap_pos && !(T.REC.cap_size && T.REC.cap_size !== 1);
}
$('capOn').addEventListener('click', function(){ T.save({captions: true}); });
$('capOff').addEventListener('click', function(){ T.save({captions: false}); });
$('capReset').addEventListener('click', function(){ T.save({cap_pos: null, cap_size: 1}); });

// ---- a new state, a new size, a script drawn again ----
T.on('apply', function(a){
  capChips();
  if (a.changed) forgive();                          // a new state: what could not be loaded is asked for again
  if (!a.ready) { if (pdrag) endDrag(true); held = null; return; }
  if (vid.paused) frame();
});
T.on('resize', function(){ if (T.ready()) frame(); });
T.on('photos', function(){ forgive(); if (T.ready() && vid.paused) frame(); });
if (window.MutationObserver)                         // the lit word and sentence, back on a script drawn again
  new MutationObserver(function(){ if (T.ready() && vid.paused) frame(); }).observe($('script'), {childList: true});

if (window.MutationObserver)                         // the video picker closed: it may just have had a small copy made
  new MutationObserver(function(){
    if ($('vpick').classList.contains('open')) return;
    forgive();
    if (T.ready() && vid.paused) frame();
  }).observe($('vpick'), {attributes: true, attributeFilter: ['class']});

T.frame = frame; T.togglePlay = togglePlay; T.shotNow = shotNow; T.shotSpan = shotSpan; T.sentenceAt = sentenceAt;
T.zoomSpan = zoomSpan; T.mediaOf = mediaOf; T.defPos = defPos; T.ME = ME; T.CAP = CAP;
T.previewDrag = function(){ return pdrag; };
T.previewHeld = function(){ return held; };
T.previewBad = function(){ return Object.keys(bad).filter(isBad); };
})();
"""
