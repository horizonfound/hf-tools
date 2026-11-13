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
    its words. Speed and Zoom are grey with no clip picked (hers are chips; ours are two small menus, see the
    end of these notes); badges "1.5x", "Punch in", "Slow zoom";
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

Ours, on top of hers (Dustin, Nov 12: "I held down Command and clicked another one... that's how other video
editors work"): SEVERAL CLIPS PICKED AT ONCE. Everything for it is marked "several" below and sits beside her
one-clip code, never inside it: with one clip picked not one line of hers runs differently, and what is saved is
byte for byte what it was (tests/talking_multi_check.py holds that). To take it out: MORE stays empty.
  - Command-click a clip (Ctrl-click on a PC) adds it to what is picked, or takes it out. Shift-click picks every
    clip from the one last clicked to this one (with Command or Ctrl as well, it adds them). Neither moves the
    line or starts a scrub. A plain press picks just that clip, as ever; Escape lets go of several.
  - what is picked is still WORDS, looked up afresh every time: SELW is a word of the clip clicked last, MORE a
    word of each other one. A clip whose words were cut meanwhile just drops out.
  - Slow zoom: each run of picked clips that sit side by side on the reel gets ONE zoom, from the run's first word
    to its last (the cut words between them included, which is how one zoom already carries on across a closed
    pause). Picked clips that do not touch get a zoom each. Whatever zoom was on those words is replaced (a zoom
    that sat only on cut words between two picked clips goes with it; Undo brings it back); a zoom that reaches
    past the picked clips is trimmed to what is left outside, never lost (T.setRange, as one clip's press has
    always done). A run that already sits whole inside one slow zoom is left alone (inSlowZoom): pressing Slow zoom
    on clips of a long zoom never breaks it up. (ONE clip picked is hers and does break it, as it always has.)
  - Punch in: the run's words are cleared the same way, then each picked clip gets its own punch in. None: the
    run's words are cleared (so no stray zoom is left on cut words between two picked clips).
  - Speed: each picked clip, exactly as a press on each in turn. Delete (the button or the key): every picked
    clip's words are cut. The little round x is not drawn while several are picked (an x on one clip that took
    three would surprise). Split is as ever: the clip under the line, whatever is picked, and then only the new
    clip is picked.
  - one press is ONE save, so one step of Undo and one of Redo.
  - nothing new is asked of the Assistant's side: a press sends {zooms}, {speeds} or {cut} as one clip's does, and
    talking_rec checks them as ever. T.setRange keeps zooms from overlapping.

Ours, in place of her chips (Dustin, Nov 13: "C is the best. By far... any user interface that can be cleaner and
still have everything necessary is fantastic"): TWO SMALL MENUS. Her bar had the word Speed and four chips, the
word Zoom and three; the bare words looked pressable and were not, and turning a zoom off meant finding None. Now
Speed and Zoom are one button each ("Speed: 1× ▾", "Zoom: Slow zoom ▾") and a press opens a short list at the
button with her own words for every item, the choice the picked clip has checked.
  - choosing an item calls speedClip(v) or zoomClip(kind), the functions her chips called: the save is byte for
    byte the same, one save and one Undo step, and everything about several clips above is unchanged;
  - ours (Dustin, Nov 13, his pick of three drawings: presets, no sliders): under the Zoom menu's three items and a
    hairline, How much (Subtle | Medium | Strong) and How fast (a slow zoom: Quick | Whole clip; a punch in:
    Instant | Quick push), shown only while a picked clip has a zoom. A choice saves at once and the menu stays
    open; the button's words do not change. See menuRow, zoomRows and zoomSet;
  - the button looks on (filled) when a picked clip has a zoom, or a speed that is not 1×; with several picked
    that do not agree it reads Mixed and no item is checked; with no clip picked both are grey, as the chips were;
  - the list opens above its button (the bar sits on the timeline) and under it only with no room above, always
    whole inside the window; one open at a time; it closes on a press anywhere else, on choosing, when the other
    opens, when the window is resized or loses the keyboard, and on Escape, which closes the menu FIRST and leaves
    what is picked alone (the next Escape lets go of several, as ever);
  - keys: Enter, Space, Down or Up on the button open it; the arrows, Home and End move; Enter or Space choose;
    the button has the keyboard again afterwards. role menu and menuitemradio, aria-checked, aria-expanded.
  - the review round (Nov 13): each button's words have the room of their longest (Delete clip's too), so no
    button in the bar moves when another clip is picked or a choice is made; Undo and Redo wrap as a pair;
    Backspace and Delete do nothing inside an open list; an item is shaded only under the pointer or the
    keyboard's ring.

What it gives the other parts: T.pickedWords() (the words of the clip or clips picked, for the script's outline),
T.renderTimeline(), T.tl() (what a test may read: {pps, selw, sel, drag, making, more, picked, menu, menuUp}),
T.tlRuns (a test).
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
var MORE = [];                 // several: a word of each OTHER clip picked along with SELW's (empty: hers, exactly)
var ANCHOR = null;             // several: a word of the clip a Shift-click reaches from (the one clicked last)
var PC = !!T.DATA.pc;          // several: the key that adds a clip is Command on a Mac and Ctrl on a PC
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
// ---- several clips picked at once (ours) ----
function pieceIx(w){ var ps = T.P(); for (var i = 0; i < ps.length; i++) if (ps[i].words.indexOf(w) >= 0) return i; return -1; }
// every clip picked, in play order, looked up afresh from the words held
function selPieces(){
  var ps = T.P(), on = {}, out = [];
  (SELW == null ? [] : [SELW]).concat(MORE).forEach(function(w){ var i = pieceIx(w); if (i >= 0) on[i] = true; });
  ps.forEach(function(p, i){ if (on[i]) out.push(p); });
  return out;
}
// the clips picked when there are two or more, else null (and then everything below is hers, untouched)
function many(){
  if (!MORE.length || TLSEL !== 'clip') return null;
  var l = selPieces();
  return l.length > 1 ? l : null;
}
// a clip whose words were cut meanwhile drops out; if that was the one clicked last, another takes its place
function tidy(){
  if (!MORE.length) return;
  var k0 = SELW == null ? -1 : pieceIx(SELW), seen = {}, keep = [];
  MORE.forEach(function(w){ var i = pieceIx(w); if (i >= 0 && i !== k0 && !seen[i]) { seen[i] = true; keep.push(w); } });
  if (k0 < 0 && keep.length && TLSEL === 'clip') SELW = keep.pop();
  MORE = keep;
}
function letGo(){ MORE = []; ANCHOR = null; }
// Command-click (Ctrl on a PC): in or out. Shift-click: every clip from the one clicked last to this one.
function pickMore(w0, add, range){
  var ps = T.P(), k = pieceIx(w0), on = {}, first = k, i;
  if (k < 0) return;
  if (TLSEL === 'clip') (SELW == null ? [] : [SELW]).concat(MORE).forEach(function(w){ var j = pieceIx(w); if (j >= 0) on[j] = true; });
  if (range) {
    var a = ANCHOR != null ? pieceIx(ANCHOR) : -1;
    if (a < 0 && TLSEL === 'clip' && SELW != null) a = pieceIx(SELW);
    if (a < 0) a = k;
    if (!add) on = {};
    for (i = Math.min(a, k); i <= Math.max(a, k); i++) on[i] = true;
    ANCHOR = ps[a].words[0];
  } else if (on[k]) { delete on[k]; first = -1; ANCHOR = null; }
  else { on[k] = true; ANCHOR = ps[k].words[0]; }
  var list = Object.keys(on).map(Number).sort(function(x, y){ return x - y; });
  if (!list.length) { SELW = null; MORE = []; TLSEL = null; }
  else {
    if (first < 0) first = list[list.length - 1];
    SELW = ps[first].words[0]; TLSEL = 'clip';
    MORE = list.filter(function(j){ return j !== first; }).map(function(j){ return ps[j].words[0]; });
  }
  renderTimeline(); picked();
}
// picked clips that sit side by side on the reel, as runs: [{a: the run's first word, b: its last, clips: [[a, b], ...]}]
function runsOf(list){
  var ps = T.P(), runs = [], prev = null;
  list.forEach(function(p){
    var i = ps.indexOf(p), a = p.words[0], b = p.words[p.words.length - 1], q = prev == null ? null : ps[prev];
    if (q && i === prev + 1 && Math.abs(q.at + q.dur - p.at) < 0.002) { var r = runs[runs.length - 1]; r.b = b; r.clips.push([a, b]); }
    else runs.push({a: a, b: b, clips: [[a, b]]});
    prev = i;
  });
  return runs;
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
  tidy();
  var sel = selPiece(), clips = document.createDocumentFragment(), mny = many();
  ps.forEach(function(p){
    var txt = p.words.map(function(j){ return words[j] ? words[j].w : ''; }).join(' '), zk = zoomKind(p);
    var d = el('div', 'tl-clip' + (p === sel || (mny && mny.indexOf(p) >= 0) ? ' on' : '') + (p.speed !== 1 ? ' fast' : ''));
    d.setAttribute('data-w', p.words[0]);
    d.style.left = X(p.at) + 'px'; d.style.width = Math.max(CLIP_MIN, p.dur * PPS - 2) + 'px';
    d.title = T.fill(W.tl_clip_title, {words: txt});
    var ha = el('i', 'tl-clip-h'); ha.setAttribute('data-cedge', 'a'); d.appendChild(ha);
    if (TLSEL === 'clip' && p === sel && !mny) d.appendChild(round_x(W.tl_clip_x));
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
// ---- the two small menus (Dustin, Nov 13: Speed and Zoom are one button each, with a short list at the button) ----
// A menu is made once; choosing an item is a press on what was that chip: speedClip(v) or zoomClip(kind) look up
// the clip picked at that moment, exactly as the chips did. Only how a choice is pressed is new.
var OPEN = null;               // menus: the one that is open (never two), or null
var MENU_GAP = 6, MENU_EDGE = 6;
function makeMenu(id, name, attr, items, choose){
  var host = $(id), btn = el('button', 'btn small tl-mb'), val = el('span', 'val'), car = el('span', 'car', '▾'), list = el('div', 'tl-ml');
  var m = {id: id, btn: btn, val: val, list: list, items: [], cur: -1};
  btn.type = 'button'; btn.disabled = true; btn.id = id + 'Btn'; list.id = id + 'List';
  btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', list.id);
  car.setAttribute('aria-hidden', 'true');
  // the value's room is as wide as the longest thing it can say (every item, and Mixed), each laid unseen in the
  // same spot, so the bar never changes shape, and Undo and Redo never move, when the choice or the picked clip
  // changes (review, Nov 13). The unseen words are drawn by the styles from data-w: text, never HTML, in no name.
  var room = el('span', 'vw'); room.appendChild(val);
  items.map(function(it){ return it[1]; }).concat([W.mixed]).forEach(function(s){
    var z = el('span', 'sz'); z.setAttribute('aria-hidden', 'true'); z.setAttribute('data-w', s); room.appendChild(z);
  });
  btn.appendChild(el('span', 'nm', T.fill(W.menu_label, {name: name}))); btn.appendChild(room); btn.appendChild(car);
  list.setAttribute('role', 'menu'); list.setAttribute('aria-label', name); list.hidden = true;
  items.forEach(function(it, k){
    var d = el('div', 'tl-mi'), tick = el('span', 'tick', '✓');
    tick.setAttribute('aria-hidden', 'true');
    d.setAttribute('role', 'menuitemradio'); d.setAttribute('aria-checked', 'false'); d.setAttribute('data-' + attr, it[0]); d.tabIndex = -1;
    d.appendChild(tick); d.appendChild(el('span', 't', it[1]));
    // choosing: the menu closes, the button has the keyboard again, and then the press is the chip's own
    d.addEventListener('click', function(){ if (OPEN !== m || btn.disabled) return; closeMenu(true); choose(it[0]); });
    list.appendChild(d); m.items.push(d);
  });
  btn.addEventListener('click', function(){ if (OPEN === m) closeMenu(true); else openMenu(m, 'cur'); });
  host.appendChild(btn); host.appendChild(list);
  return m;
}
// Ours (Dustin, Nov 13: "let's do A and keep it simple and consistent"): under the Zoom menu's three items and a
// hairline, two rows of joined choices for the picked clips' zoom: How much (Subtle | Medium | Strong) and How fast
// (a slow zoom: Quick | Whole clip; a punch in: Instant | Quick push). They show only while a picked clip has a
// zoom. Choosing one saves at once (one save, one step of Undo) and the menu STAYS OPEN, so both can be set.
// Each row is a named radio group (role radiogroup, its choices role radio); the arrows reach them like the items above.
function menuRow(m, name, attr, opts, choose){
  var g = el('div', 'tl-mg'), lb = el('span', 'lb', name), seg = el('div', 'tl-seg'), row = {g: g, items: [], attr: attr};
  lb.setAttribute('aria-hidden', 'true');
  g.setAttribute('role', 'radiogroup'); g.setAttribute('aria-label', name);
  opts.forEach(function(o){
    var d = el('div', 'tl-so', o[1]);
    d.setAttribute('role', 'radio'); d.setAttribute('aria-checked', 'false'); d.setAttribute('data-' + attr, o[0]); d.tabIndex = -1;
    d.addEventListener('click', function(){ if (OPEN !== m || m.btn.disabled || g.hidden || m.more.hidden) return; choose(o[0]); });
    seg.appendChild(d); row.items.push(d);
  });
  g.appendChild(lb); g.appendChild(seg); m.more.appendChild(g);
  return row;
}
// what the arrows walk through: the menu's items, then the choices of whichever rows are showing
function menuStops(m){
  var out = m.items.slice();
  if (m.rows && !m.more.hidden) m.rows.forEach(function(r){ if (!r.g.hidden) out = out.concat(r.items); });
  return out;
}
// where the list goes: above its button (below it would lie over the clips being changed), under it only when
// there is no room above; always whole inside the window, whatever the dock or the window's edge
function placeMenu(m){
  var l = m.list, r = m.btn.getBoundingClientRect(), de = document.documentElement;
  l.style.minWidth = Math.round(r.width) + 'px';
  var h = l.offsetHeight, w = l.offsetWidth, top = r.top - MENU_GAP - h;
  m.up = top >= MENU_EDGE;
  if (!m.up) top = r.bottom + MENU_GAP;
  l.style.top = cl(top, MENU_EDGE, Math.max(MENU_EDGE, de.clientHeight - h - MENU_EDGE)) + 'px';
  l.style.left = cl(r.left, MENU_EDGE, Math.max(MENU_EDGE, de.clientWidth - w - MENU_EDGE)) + 'px';
}
function openMenu(m, at){
  if (m.btn.disabled) return;
  if (OPEN) closeMenu(false);
  OPEN = m;
  m.list.hidden = false; m.btn.setAttribute('aria-expanded', 'true');
  placeMenu(m);
  var k = at === 'last' ? m.items.length - 1 : m.cur >= 0 ? m.cur : 0;
  m.items[k].focus({preventScroll: true});
  if (m.rows) placeMenu(m);
}
function closeMenu(back){
  var m = OPEN; if (!m) return;
  OPEN = null;
  m.list.hidden = true; m.btn.setAttribute('aria-expanded', 'false');
  if (back && !m.btn.disabled) m.btn.focus({preventScroll: true});
}
// what a menu's button says and which item is checked: text is the one choice every picked clip agrees on (or
// Mixed), cur its place in the list (-1: none checked), lit whether the button looks on. True when its words changed.
function menuState(m, off, text, cur, lit){
  var was = m.val.textContent;
  m.btn.disabled = off; m.cur = cur;
  m.btn.classList.toggle('on', lit);
  if (was !== text) m.val.textContent = text;
  m.items.forEach(function(d, k){ d.setAttribute('aria-checked', k === cur ? 'true' : 'false'); });
  if (off && OPEN === m) closeMenu(false);
  return was !== text;
}
// the Delete button's words change too (Delete clip, Delete photo, Delete 3 clips): the same unseen words hold
// its room, so picking several clips never pushes the buttons after it along (up to nine clips; more is a digit wider)
var cutVal = el('span', 'val', $('tlCut').textContent);
(function(){
  var b = $('tlCut'), room = el('span', 'vw');
  b.textContent = ''; room.appendChild(cutVal);
  [W.delete_clip, W.delete_photo, T.fill(W.delete_clips, {n: 8})].forEach(function(s){
    var z = el('span', 'sz'); z.setAttribute('aria-hidden', 'true'); z.setAttribute('data-w', s); room.appendChild(z);
  });
  b.appendChild(room);
})();
var speedMenu = makeMenu('tlSpeed', W.speed, 'v', SPEEDS.map(function(v){ return [v, T.fill(W.speed_x, {v: v})]; }), function(v){ speedClip(v); });
var zoomMenu = makeMenu('tlZoom', W.zoom, 'z', MOVES, function(kind){ zoomClip(kind); });
var ZS = T.ZS;
var AMT_W = {subtle: W.amt_subtle, medium: W.amt_medium, strong: W.amt_strong};
var PACE_W = {quick: W.pace_quick, whole: W.pace_whole, instant: W.pace_instant, push: W.pace_push};
zoomMenu.more = el('div', 'tl-mx'); zoomMenu.more.hidden = true; zoomMenu.list.appendChild(zoomMenu.more);
zoomMenu.rowAmount = menuRow(zoomMenu, W.how_much, 'amount', ZS.amounts.map(function(a){ return [a, AMT_W[a]]; }), function(v){ zoomSet('amount', v); });
function paceRow(kind){             // How fast has a row for each kind of zoom; the one of the picked zooms' kind shows
  var r = menuRow(zoomMenu, W.how_fast, 'pace', ZS.pace[kind].map(function(p){ return [p, PACE_W[p]]; }), function(v){ zoomSet('pace', v); });
  r.g.setAttribute('data-kind', kind);
  return r;
}
zoomMenu.rowPace = {zoom: paceRow('zoom'), punch: paceRow('punch')};
zoomMenu.rows = [zoomMenu.rowAmount, zoomMenu.rowPace.zoom, zoomMenu.rowPace.punch];
// the picked clips' zooms, each once (a slow zoom joined across clips is ONE zoom: it has one setting)
function pickedZooms(){
  var all = many() || (selPiece() ? [selPiece()] : []), ks = [];
  all.forEach(function(q){ if (q.zoom != null && T.ZL[q.zoom] && ks.indexOf(q.zoom) < 0) ks.push(q.zoom); });
  return ks.map(function(k){ return T.ZL[k]; });
}
// the rows follow what is picked: there only with a zoom; a choice is lit only when every picked zoom agrees; How
// fast is the row of the picked zooms' kind, and is not shown when a punch in and a slow zoom are picked together
function zoomRows(){
  var m = zoomMenu, zs = pickedZooms(), was = [m.more.hidden, m.rowPace.zoom.g.hidden, m.rowPace.punch.g.hidden].join();
  var kind = zs.length && zs.every(function(z){ return z.kind === zs[0].kind; }) ? zs[0].kind : '';
  var agreed = function(f){ return zs.length && zs.every(function(z){ return f(z) === f(zs[0]); }) ? f(zs[0]) : ''; };
  var amount = agreed(T.zoomAmountName), pace = kind ? agreed(T.zoomPace) : '';
  m.more.hidden = !zs.length;
  m.rowAmount.items.forEach(function(d){ d.setAttribute('aria-checked', d.getAttribute('data-amount') === amount ? 'true' : 'false'); });
  ['zoom', 'punch'].forEach(function(k){
    m.rowPace[k].g.hidden = kind !== k;
    m.rowPace[k].items.forEach(function(d){ d.setAttribute('aria-checked', kind === k && d.getAttribute('data-pace') === pace ? 'true' : 'false'); });
  });
  if (OPEN === m && was !== [m.more.hidden, m.rowPace.zoom.g.hidden, m.rowPace.punch.g.hidden].join()) {
    if (menuStops(m).indexOf(document.activeElement) < 0) m.items[m.cur >= 0 ? m.cur : 0].focus({preventScroll: true});
    placeMenu(m);
  }
}
// a press anywhere else closes the open menu (and still does whatever it was a press on)
function outsideMenu(e){ if (OPEN && !OPEN.list.contains(e.target) && !OPEN.btn.contains(e.target)) closeMenu(false); }
document.addEventListener('pointerdown', outsideMenu, true);
document.addEventListener('mousedown', outsideMenu, true);
addEventListener('blur', function(){ closeMenu(false); });
// the keys, heard before anyone else's (so Escape closes the menu FIRST and what is picked stays picked; the next
// Escape is the timeline's, as ever): on a menu's button Enter, Space, Down and Up open it; in it the arrows, Home
// and End move, Enter and Space choose, Escape closes with the button focused again, Tab closes and moves on
addEventListener('keydown', function(e){
  var k = e.key, m = OPEN, stop = function(){ e.preventDefault(); e.stopImmediatePropagation(); };
  if (!m) {
    var b = e.target === speedMenu.btn ? speedMenu : e.target === zoomMenu.btn ? zoomMenu : null;
    if (b && !e.metaKey && !e.ctrlKey && !e.altKey && (k === 'Enter' || k === ' ' || k === 'ArrowDown' || k === 'ArrowUp')) { stop(); openMenu(b, k === 'ArrowUp' ? 'last' : 'cur'); }
    return;
  }
  var st = menuStops(m), i = st.indexOf(document.activeElement), n = st.length, inRow = i >= m.items.length;
  if (k === 'Escape') { stop(); closeMenu(true); }
  else if (k === 'Tab') closeMenu(false);
  else if (k === 'ArrowDown' || (inRow && k === 'ArrowRight')) { stop(); st[(i + 1) % n].focus({preventScroll: true}); }
  else if (k === 'ArrowUp' || (inRow && k === 'ArrowLeft')) { stop(); st[(i <= 0 ? n : i) - 1].focus({preventScroll: true}); }
  else if (k === 'Home') { stop(); st[0].focus({preventScroll: true}); }
  else if (k === 'End') { stop(); st[n - 1].focus({preventScroll: true}); }
  else if (k === 'Enter' || k === ' ') { stop(); if (i >= 0) st[i].click(); else closeMenu(true); }      // never playing behind the open menu
  else if ((k === 'Delete' || k === 'Backspace') && !e.metaKey && !e.ctrlKey) stop();      // never deleting the picked clip from inside an open list
}, true);
// ours: the line under the timeline keeps the room of its longest words at this width, so the bar and the timeline
// do not move up when a second clip is picked and the line grows from one row to two. Measured on a copy nobody
// sees or hears; measured again only when the line's width changes (or the fonts arrive).
var multiW = -1;
function multiRoom(){
  var el = $('tlMulti'), wd = el.clientWidth;
  if (!wd || wd === multiW) return;
  multiW = wd;
  var c = el.cloneNode(false), tall = 0;
  c.removeAttribute('id'); c.removeAttribute('aria-live'); c.setAttribute('aria-hidden', 'true');
  c.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none;min-height:0;width:' + wd + 'px';
  el.parentNode.appendChild(c);
  [W.multi_hint, T.fill(W.multi_selected, {n: 88})].forEach(function(words){ c.textContent = words; tall = Math.max(tall, c.offsetHeight); });
  el.parentNode.removeChild(c);
  if (el.style.minHeight !== tall + 'px') {
    el.style.minHeight = tall + 'px';
    var dh = $('dock').offsetHeight;
    if (dh !== dockWas) { dockWas = dh; T.sizeDock(); }
  }
}
try { document.fonts.ready.then(function(){ multiW = -1; multiRoom(); }); } catch (e) {}
function toolState(){
  multiRoom();
  var p = selPiece(), zk = zoomKind(p), mny = many();
  var ph = TLSEL === 'photo' && !!T.findShot(T.SELSHOT);
  $('tlCut').disabled = !(ph || (TLSEL === 'clip' && p));
  cutVal.textContent = ph ? W.delete_photo : mny ? T.fill(W.delete_clips, {n: mny.length}) : W.delete_clip;
  $('tlCut').title = mny && !ph ? W.delete_title_many : W.delete_title;
  // several: our line under her help line. It holds the room of its longest words (multiRoom), so the dock should
  // not grow; its room is measured again all the same
  var ml = mny ? T.fill(W.multi_selected, {n: mny.length}) : W.multi_hint;
  if ($('tlMulti').textContent !== ml) {
    $('tlMulti').textContent = ml;
    var dh = $('dock').offsetHeight;
    if (dh !== dockWas) { dockWas = dh; T.sizeDock(); }
  }
  // menus: an item is checked on the rule that lit its chip (several: only when every picked clip agrees; when
  // they do not, the button reads Mixed and nothing is checked). The Speed button looks on when a picked clip is
  // not at 1×, the Zoom button when one has a zoom. Nothing picked: both grey, as the chips were.
  var sAt = -1, zAt = -1;
  SPEEDS.forEach(function(v, k){
    var on = mny ? mny.every(function(q){ return q.speed === SPEEDS[k]; }) : !!p && p.speed === SPEEDS[k];
    if (on) sAt = k;
  });
  MOVES.forEach(function(mv, k){
    var on = mny ? mny.every(function(q){ return zoomKind(q) === MOVES[k][0]; }) : !!p && zk === MOVES[k][0];
    if (on) zAt = k;
  });
  var all = mny || (p ? [p] : []);
  var sSame = all.every(function(q){ return q.speed === all[0].speed; });
  var grew = menuState(speedMenu, !p, !p ? T.fill(W.speed_x, {v: 1}) : !sSame ? W.mixed : T.fill(W.speed_x, {v: all[0].speed}), sAt,
                       all.some(function(q){ return q.speed !== 1; }));
  grew = menuState(zoomMenu, !p, !p ? MOVES[0][1] : zAt < 0 ? W.mixed : MOVES[zAt][1], zAt, all.some(function(q){ return !!zoomKind(q); })) || grew;
  // a button whose words changed can wrap the bar at a narrow width: the dock's room is measured again
  if (grew) {
    var dh2 = $('dock').offsetHeight;
    if (dh2 !== dockWas) { dockWas = dh2; T.sizeDock(); }
    if (OPEN) placeMenu(OPEN);
  }
  zoomRows();
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
  if (e.button !== 0 || drag || !T.ready()) return;
  var t = e.target;
  if (!t || !t.closest) return;
  // several: Command-click (Ctrl-click on a PC) or Shift-click ON A CLIP; anywhere else the press is hers
  var mclip = (PC || !e.ctrlKey) && !t.closest('.tl-x') ? t.closest('.tl-clip') : null;
  if (mclip && ((PC ? e.ctrlKey : e.metaKey) || e.shiftKey)) {
    e.preventDefault();
    pickMore(+mclip.getAttribute('data-w'), PC ? e.ctrlKey : e.metaKey, e.shiftKey);
    return;
  }
  if (e.ctrlKey) return;                                              // a Control-click is the Mac's right click
  if (t.closest('.tl-x')) { e.preventDefault(); deleteSelected(); return; }      // the little x on what is picked
  var clip = t.closest('.tl-clip'), ph = t.closest('.tl-ph'), edge = t.closest('.tl-ph-h'), cedge = t.closest('.tl-clip-h');
  try { track.setPointerCapture(e.pointerId); } catch (err) {}
  if (cedge && clip) {
    drag = {cedge: cedge.getAttribute('data-cedge'), w0: +clip.getAttribute('data-w'), x: e.clientX, moved: false, id: e.pointerId};
    SELW = drag.w0; letGo();
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
  letGo(); if (clip) ANCHOR = SELW;                                   // several: a plain press picks just this one
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
  SELW = best; letGo();
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
// several: every picked clip's words, in one save (one step of Undo)
function cutClips(mny){
  var list = [];
  mny.forEach(function(p){ list = list.concat(p.words); });
  SELW = null; letGo();
  saveCut(list, true);
  T.toast(T.fill(W.cut_clips, {n: mny.length}));
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
    var mny = many();
    if (mny) cutClips(mny); else cutClip();
    TLSEL = null;
    renderTimeline(); picked();
  }
}
$('tlCut').addEventListener('click', deleteSelected);
// several: each picked clip, as a press on each in turn, in one save
function speedClips(mny, v){
  var rs = mny.map(function(p){ return [p.words[0], p.words[p.words.length - 1]]; });
  T.save(function(){
    var s = T.REC.speeds || [];
    rs.forEach(function(r){ s = T.setRange(s, r[0], r[1], v === 1 ? null : {v: v}); });
    return {speeds: s.map(function(r){ return {a: r.a, b: r.b, v: r.v}; })};
  });
}
// several: one slow zoom across each run of clips side by side; a punch in on each clip; None clears each run.
// A run that already sits whole inside ONE slow zoom is left as it is: Slow zoom is already what those clips have
// (the chip is lit), and replacing it would break a long zoom into separate ones on clips nobody picked.
function inSlowZoom(r){ return T.ZL.some(function(q){ return q.kind === 'zoom' && q.a <= r.a && q.b >= r.b; }); }
function zoomClips(mny, kind){
  var runs = runsOf(mny);
  if (kind === 'zoom') runs = runs.filter(function(r){ return !inSlowZoom(r); });
  if (!runs.length) return;                                           // every picked clip is in a slow zoom already
  var joined = runs.filter(function(r){ return r.clips.length > 1; });
  T.save(function(){
    var z = T.ZL, now = kind === 'zoom' ? runs.filter(function(r){ return !inSlowZoom(r); }) : runs;
    if (!now.length) return null;
    now.forEach(function(r){
      z = T.setRange(z, r.a, r.b, kind === 'zoom' ? {kind: 'zoom'} : null);
      if (kind === 'punch') r.clips.forEach(function(c){ z = T.setRange(z, c[0], c[1], {kind: 'punch'}); });
    });
    return {zooms: z.map(T.zoomOut)};
  });
  if (kind === 'zoom' && joined.length)
    T.toast(runs.length === 1 ? T.fill(W.zoom_joined, {n: runs[0].clips.length}) : joined.length < runs.length ? W.zoom_some_joined : W.zoom_all_joined);
}
function speedClip(v){
  var mny = many(); if (mny) { speedClips(mny, v); return; }
  var p = selPiece(); if (!p) return;
  var a = p.words[0], b = p.words[p.words.length - 1];
  T.save(function(){
    return {speeds: T.setRange(T.REC.speeds || [], a, b, v === 1 ? null : {v: v}).map(function(r){ return {a: r.a, b: r.b, v: r.v}; })};
  });
}
function zoomClip(kind){
  var mny = many(); if (mny) { zoomClips(mny, kind); return; }
  var p = selPiece(); if (!p) return;
  var a = p.words[0], b = p.words[p.words.length - 1];
  T.save(function(){
    // the kind the clip already has, chosen again, keeps how much and how fast it had; a new kind starts as made
    var was = T.zoomAt(a), put = kind ? {kind: kind} : null;
    if (put && was && was.kind === kind) { if (was.amount) put.amount = was.amount; if (was.pace) put.pace = was.pace; }
    return {zooms: T.setRange(T.ZL, a, b, put).map(T.zoomOut)};
  });
}
// How much / How fast, from the Zoom menu's rows: every picked clip's zoom gets the choice, in one save. What a
// zoom has by itself (Medium; Whole clip; Instant) is never written. A zoom is found again by its words when the
// save's turn comes; one that is gone by then is simply not changed.
function zoomSet(field, v){
  var want = pickedZooms().map(function(z){ return z.a + ':' + z.b + ':' + z.kind; });
  if (!want.length) return;
  T.save(function(){
    var hit = false, out = T.ZL.map(function(z){
      var o = T.zoomOut(z);
      if (want.indexOf(z.a + ':' + z.b + ':' + z.kind) < 0) return o;
      if (field === 'amount' ? !Object.prototype.hasOwnProperty.call(ZS.amount[z.kind], v) : ZS.pace[z.kind].indexOf(v) < 0) return o;
      var was = JSON.stringify(o);
      delete o[field];
      if (v !== (field === 'amount' ? ZS.amountDefault : ZS.paceDefault[z.kind])) o[field] = v;
      o = T.zoomOut(o);
      if (JSON.stringify(o) !== was) hit = true;       // the choice it already has: nothing to save
      return o;
    });
    return hit ? {zooms: out} : null;
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
  // several: Escape lets go of them (with one clip picked, or a menu open, Escape is as it was)
  else if (e.key === 'Escape' && !mod && many() && !$('pmenu').classList.contains('open')) { SELW = null; TLSEL = null; letGo(); renderTimeline(); picked(); }
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
  if (!a.ready) { if (drag) endDrag(null, true); SELW = null; TLSEL = null; letGo(); return; }
  if (a.changed || !$('tlClips').firstChild) {
    if (TLSEL === 'photo' && !T.findShot(T.SELSHOT)) TLSEL = null;
    if (drag && (drag.cedge || drag.edge)) toolState(); else renderTimeline();      // never under a held end: drawn at the drop
    T.markPicked();
  } else toolState();
  var h = $('dock').offsetHeight;
  if (h !== dockWas) { dockWas = h; T.sizeDock(); if (vid.paused && T.frame) T.frame(); }
});
T.on('resize', function(){ closeMenu(false); if (T.ready() && !drag) renderTimeline(); });
T.on('photos', function(){ if (T.ready() && !drag) renderTimeline(); });

T.makeReady = true;
T.pickedWords = function(){
  var mny = many();
  if (mny) { var all = []; mny.forEach(function(q){ all = all.concat(q.words); }); return all; }
  var p = selPiece(); return p ? p.words : [];
};
T.renderTimeline = renderTimeline;
T.tl = function(){
  return {pps: PPS, selw: SELW, sel: TLSEL, drag: !!drag, making: making, more: MORE.slice(), menu: OPEN ? OPEN.id : null, menuUp: OPEN ? !!OPEN.up : null,
          picked: (TLSEL === 'clip' ? selPieces() : []).map(function(p){ return p.words[0]; })};
};
T.tlRuns = function(){ return runsOf(selPieces()); };
T.tlFmt = fmt; T.tlTick = fmtTick;
})();
"""
