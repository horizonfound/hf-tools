#!/usr/bin/env python3
"""The talking reel page's script, part 1 of its files: what every other part stands on (Nicole's handoff v24,
pages/talking-reel.html, built our way). One string of JavaScript and nothing else (the design_js_*.py pattern).

It makes window.Talk (T below), which holds:
  the state      T.ST (what /talking-state answered), T.REC (its record), T.ZL (zooms), T.SH (photo stretches),
                 T.rev and T.mark (the counter and the folders' mark the page holds), T.ready()
  the refresh    every 3 seconds (hers), asking only "has anything moved?" (the counter and the mark go with the
                 question; the whole state comes back only when one has). It runs only while the page is showing
                 and the talking video is PAUSED, and never during a drag, with the photo menu open, or with
                 either picker open (a later part says it is dragging with T.busy(fn)).
  T.on / T.emit  how the parts hear of a new state: 'apply' {changed, ready, how, outside} after every answer.
                 A stretch, a clip or a word is always looked up afresh from T.SH / T.ST at the moment of a
                 click, never kept across a refresh (her stale-object fault).
  T.save         one save at a time, each carrying the counter it was made on; an answer of "something newer"
                 brings that newer state in. Give it a FUNCTION that builds what to save: it runs when the save's
                 turn comes, on the state the save before it left, so two quick edits never wipe each other.
                 A save that changed nothing is no Undo step; an Undo or Redo whose save did not get through
                 keeps its step; a part that throws on 'apply' is told in T.faults and stops nothing; only the
                 newest look's answer is ever taken; a playing talking video is paused when its script goes away. T.UNDO / T.REDO (60 steps, hers) are filled here: a save that is
                 `quiet` (who places the photos) adds no step, and both lists are emptied whenever a refresh brings
                 a change this page did not make (her Undo would wipe the assistant's cut with one press).
  the time sums  hers, number for number: P, total, pieceAt (0.02 s before a piece), reelAt, srcAt (ends at
                 to - 0.02), and the word ranges: cutSet, toRanges, setRange, zoomOf, speedOf, wordsOf
  small things   toast, copy (the older copy call first: the app's pane refuses the newer one), post, ask,
                 fill and rich (a line's blanks, always filled as TEXT), secs, sizeDock, summary

Nothing here writes HTML from a string: every name, file name and word of theirs reaches the page as text.
"""

JS = r"""
(function(){
'use strict';
var DATA = JSON.parse(document.getElementById('talkData').textContent);
var W = DATA.words, KIT = DATA.kit, Q = 'kit=' + encodeURIComponent(KIT);
var $ = function(id){ return document.getElementById(id); };
// a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this page's own
// save (whose answer never arrived) from a save made in another window
var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');
var T = window.Talk = {DATA: DATA, W: W, KIT: KIT, Q: Q, $: $, PAGE: PAGE, ST: {}, REC: {}, ZL: [], SH: [],
                       UNDO: [], REDO: [], faults: [], rev: null, mark: null, loaded: false, makeReady: false};
var heard = {}, busy = [];
T.on = function(what, fn){ (heard[what] = heard[what] || []).push(fn); };
// one part's fault never stops the others, the refresh or a save (it is still told, so a test sees it)
T.emit = function(what, a){
  (heard[what] || []).forEach(function(fn){ try { fn(a); } catch (e) { console.error(e); T.faults.push(String(e && e.message || e)); } });
};
T.busy = function(fn){ busy.push(fn); };

// ---- words: a line's blanks are filled as text, and {b} {eb} {br} are her bold and her line break ----
function fill(t, o){ return String(t).replace(/\{(\w+)\}/g, function(m, k){ return o && o[k] != null ? o[k] : m; }); }
function rich(el, t, o){
  el.textContent = '';
  var cur = el;
  String(t).split(/(\{\w+\})/).forEach(function(p){
    if (p === '{b}') { cur = document.createElement('b'); el.appendChild(cur); }
    else if (p === '{eb}') cur = el;
    else if (p === '{br}') el.appendChild(document.createElement('br'));
    else if (p) { var m = /^\{(\w+)\}$/.exec(p); cur.appendChild(document.createTextNode(m && o && o[m[1]] != null ? String(o[m[1]]) : p)); }
  });
}
function toast(t){
  var e = $('toast'); e.textContent = t; e.classList.add('on');
  clearTimeout(toast.t); toast.t = setTimeout(function(){ e.classList.remove('on'); }, DATA.toastMs);
}
// Copy: the page's own copy first (the Claude app's pane allows it from a press and refuses the newer way), the
// newer way only if that failed.
function copyText(t){
  var ok = false, was = document.activeElement;
  try {
    var ta = document.createElement('textarea');
    ta.value = t; ta.setAttribute('readonly', ''); ta.setAttribute('aria-hidden', 'true');
    ta.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;min-height:0;opacity:0';
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, t.length);
    ok = !!t && document.execCommand('copy');
    document.body.removeChild(ta);
    if (was && was.focus && was !== document.body) was.focus();
  } catch (e) { ok = false; }
  if (ok) return Promise.resolve(true);
  if (t && navigator.clipboard && navigator.clipboard.writeText)
    return navigator.clipboard.writeText(t).then(function(){ return true; }, function(){ return false; });
  return Promise.resolve(false);
}
function copy(t){ T.lastCopied = t; return copyText(t).then(function(ok){ toast(ok ? W.copied : W.copy_failed); return ok; }); }
function answer(r){ return r.json().then(function(j){ return {code: r.status, j: j}; }, function(){ return {code: r.status, j: null}; }); }
function ask(path){ return fetch(path, {cache: 'no-store'}).then(answer); }
function post(path, body){
  return fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}).then(answer);
}

// ---- the reel's time and the video's time (hers, number for number) ----
function P(){ return T.ST.pieces || []; }
function total(){ return P().reduce(function(a, p){ return Math.max(a, p.at + p.dur); }, 0); }
function secs(t){ return fill(W.secs, {t: Math.round(t * 10) / 10}); }
function pieceAt(t){ var ps = P(); for (var i = 0; i < ps.length; i++) if (t >= ps[i].from - 0.02 && t < ps[i].to) return i; return -1; }
function reelAt(t){
  var ps = P();
  for (var i = 0; i < ps.length; i++) { var p = ps[i]; if (t < p.from) return p.at; if (t < p.to) return p.at + (t - p.from) / p.speed; }
  return total();
}
function srcAt(R){
  var ps = P();
  for (var i = 0; i < ps.length; i++) if (R < ps[i].at + ps[i].dur) return ps[i].from + Math.max(0, R - ps[i].at) * ps[i].speed;
  var l = ps[ps.length - 1];
  return l ? l.to - 0.02 : 0;
}

// ---- ranges by word: cuts, speeds, zooms, photo stretches (hers) ----
function cutSet(){ var s = new Set(); (T.REC.cut || []).forEach(function(r){ for (var i = r[0]; i <= r[1]; i++) s.add(i); }); return s; }
function toRanges(set){
  var a = Array.from(set).sort(function(x, y){ return x - y; }), out = [];
  a.forEach(function(i){ if (out.length && out[out.length - 1][1] === i - 1) out[out.length - 1][1] = i; else out.push([i, i]); });
  return out;
}
function same(o, more){ var n = {}, k; for (k in o) n[k] = o[k]; for (k in (more || {})) n[k] = more[k]; return n; }
// words a..b get `extra` ({kind}, {v}, a photo stretch), or nothing; whatever was there is trimmed around it
function setRange(list, a, b, extra){
  var out = [];
  list.forEach(function(r){
    if (r.b < a || r.a > b) { out.push(same(r)); return; }
    if (r.a < a) out.push(same(r, {b: a - 1}));
    if (r.b > b) out.push(same(r, {a: b + 1}));
  });
  if (extra) out.push(same(extra, {a: a, b: b}));
  return out.sort(function(x, y){ return x.a - y.a; });
}
function zoomOf(i){ for (var k = 0; k < T.ZL.length; k++) if (i >= T.ZL[k].a && i <= T.ZL[k].b) return T.ZL[k].kind; return ''; }
function speedOf(i){ var s = T.REC.speeds || []; for (var k = 0; k < s.length; k++) if (i >= s[k].a && i <= s[k].b) return s[k].v; return 1; }
function wordsOf(a, b, max){
  var t = (T.REC.words || []).slice(a, b + 1).map(function(w){ return w.w; }).join(' ').replace(/ '/g, "'");
  max = max || 60;
  return t.length > max ? t.slice(0, max) + '…' : t;
}
T.ready = function(){ return !!(T.REC.words && T.REC.words.length) && T.REC.status === 'ready'; };

// ---- saving, and Undo's two lists ----
function clone(x){ return JSON.parse(JSON.stringify(x)); }
function snap(){
  var r = T.REC;
  return clone({cut: r.cut || [], splits: r.splits || [], speeds: r.speeds || [], zooms: T.ZL,
                shots: T.SH.map(function(x){ return {a: x.a, b: x.b, ns: x.ns || [], v: x.v || null, from: x.from || 0, spot: x.spot, pos: x.pos || null, me: x.me || null}; }),
                cap_pos: r.cap_pos || null, cap_size: r.cap_size || 1, captions: r.captions !== false});
}
var chain = Promise.resolve(), saving = 0, seq = 0;
function undoButtons(){ $('tlUndo').disabled = !T.UNDO.length; $('tlRedo').disabled = !T.REDO.length; }
function forget(){ T.UNDO = []; T.REDO = []; undoButtons(); }
// opt.quiet: a choice that is no edit (who places the photos): no Undo step. opt.undo: an Undo or a Redo itself.
// `body` is what to save, or better a FUNCTION that builds it: the function runs when this save's turn comes,
// after every earlier save's answer is on the page, so two quick presses (two Cuts, a held Delete key) each
// build on the one before and neither wipes the other. It may return null: nothing to save after all. The Undo
// step is taken at that same moment, and only when the save really changed the record (the counter moved).
// The promise answers true, false, or 'newer' (refused: something newer was stored, and is on the page now).
function save(body, opt){
  opt = opt || {};
  if (!T.loaded) return Promise.resolve(false);
  saving++; seq++;
  var done = false, over = function(){ if (!done) { done = true; saving--; } };
  var run = function(){
    var before, sent, base = T.rev;
    try { before = opt.before || snap(); sent = typeof body === 'function' ? body() : body; }
    catch (e) { console.error(e); T.faults.push(String(e && e.message || e)); over(); return false; }
    if (!sent) { over(); return false; }
    return post('/talking-save', {kit: KIT, base: base, page: PAGE, saved: sent}).then(function(res){
      over();
      var j = res.j || {};
      if (res.code === 200 && j.ok && j.rec) {
        if (!opt.undo && !opt.quiet && j.rev !== base) { T.UNDO.push(before); if (T.UNDO.length > DATA.undoSteps) T.UNDO.shift(); T.REDO = []; }
        apply(j, 'save');
        return true;
      }
      var newer = j.why === 'newer' && j.state && j.state.ok && j.state.rec;
      if (newer) { forget(); apply(j.state, 'newer'); }
      toast(j.words || W.didnt_work);
      return newer ? 'newer' : false;
    }, function(){ over(); toast(W.cant_reach); return false; });
  };
  var fail = function(e){ over(); console.error(e); return false; };
  chain = chain.then(run, run).then(null, fail);
  return chain;
}
// Undo and Redo: the step leaves its list only when its save got through. A save that did not (the Assistant
// busy or out of reach) leaves both lists as they were, so "try again" undoes the SAME step, not the one before.
function undo(){
  if (!T.UNDO.length) { toast(W.nothing_undo); return Promise.resolve(false); }
  var back, now;
  return save(function(){
    if (!T.UNDO.length) return null;
    back = T.UNDO[T.UNDO.length - 1]; now = snap();
    return back;
  }, {undo: true}).then(function(ok){
    if (ok === true && T.UNDO[T.UNDO.length - 1] === back) { T.UNDO.pop(); T.REDO.push(now); toast(W.undone); }
    undoButtons(); return ok === true;
  });
}
function redo(){
  if (!T.REDO.length) { toast(W.nothing_redo); return Promise.resolve(false); }
  var fwd, now;
  return save(function(){
    if (!T.REDO.length) return null;
    fwd = T.REDO[T.REDO.length - 1]; now = snap();
    return fwd;
  }, {undo: true}).then(function(ok){
    if (ok === true && T.REDO[T.REDO.length - 1] === fwd) { T.REDO.pop(); T.UNDO.push(now); toast(W.redone); }
    undoButtons(); return ok === true;
  });
}

// ---- the make bar's line, and the room the dock takes ----
function summary(){
  var ph = T.SH.reduce(function(a, x){ return a + (x.ns || []).length; }, 0), nv = T.SH.filter(function(x){ return x.v; }).length;
  var mv = T.ZL.length, fast = P().filter(function(p){ return p.speed !== 1; }).length;
  if (T.REC.words && T.REC.words.length)
    rich($('sum'), W.sum, {t: secs(total()),
      photos: fill(ph === 1 ? W.sum_photo : W.sum_photos, {n: ph}) + (nv ? fill(nv === 1 ? W.sum_video : W.sum_videos, {n: nv}) : ''),
      zooms: fill(mv === 1 ? W.sum_zoom : W.sum_zooms, {n: mv}) + (fast ? fill(W.sum_fast, {n: fast}) : '') + (T.REC.captions === false ? W.sum_caps_off : W.sum_caps_on)});
  else $('sum').textContent = W.sum_empty;
  // Make it in CapCut stays off until the part that makes it work says so (T.makeReady)
  $('makeBtn').disabled = !(P().length && T.makeReady);
}
function sizeDock(){
  var h = $('dock').offsetHeight;
  document.documentElement.style.setProperty('--dock', h + 'px');
  document.body.style.paddingBottom = (h + 24) + 'px';
}
addEventListener('resize', function(){ sizeDock(); T.emit('resize'); });

// ---- a new state ----
// how: 'load' (the first look, or one the page asked for after its own press), 'poll' (the 3-second look),
// 'save' (the answer to this page's own save), 'newer' (a save was refused: this is what is stored now)
function apply(st, how){
  var moved = T.rev !== st.rev || T.mark !== st.mark;
  var outside = T.loaded && how !== 'save' && T.rev !== st.rev;      // a change this page's own save did not make
  T.ST = st; T.REC = st.rec || {}; T.rev = st.rev; T.mark = st.mark; T.ZL = st.zooms || []; T.SH = st.shots || [];
  if (outside) forget();
  T.loaded = true;
  var ready = T.ready();
  $('editStep').hidden = $('capStep').hidden = $('tl').hidden = !ready;
  sizeDock();
  if (!ready) {
    // steps 2 and 3 are hidden now: nothing plays unseen, and the 3-second look (which waits while the talking
    // video plays) can run again, or the page would sit on "Getting your video ready…" until the video ended
    ['vid', 'bvid'].forEach(function(id){ var v = $(id); if (v && !v.paused) { try { v.pause(); } catch (e) {} } });
  }
  if (ready) {
    // the talking video's small copy; a new address only when it is another video or its script was made again
    var src = '/talking-video?' + Q + '&v=' + encodeURIComponent((T.REC.video || '') + (T.REC.transcribed || ''));
    var vid = $('vid');
    if (vid.dataset.src !== src) { vid.dataset.src = src; vid.src = src; }
  }
  T.emit('apply', {changed: how !== 'poll' || moved, ready: ready, how: how, outside: outside});
  summary(); undoButtons();
}
// the short answer: nothing moved; only whether a video is being worked on, and how Make it in CapCut stands
function small(st){
  var was = T.ST.working, wasMake = JSON.stringify(T.ST.make || null);
  var stepMoved = typeof st.step === 'string' && T.REC && (T.REC.step || '') !== st.step;
  T.ST.working = st.working; T.ST.make = st.make;
  if (stepMoved) T.REC.step = st.step;                // the job's step, so the status line follows it
  if (was !== st.working || stepMoved) T.emit('apply', {changed: false, ready: T.ready(), how: 'poll', outside: false});
  if (wasMake !== JSON.stringify(st.make || null)) T.emit('make', st.make);
}
var asking = false, looks = 0;
function poll(force){
  if (asking && !force) return Promise.resolve();
  var mine = seq, look = ++looks;                    // only the newest look's answer is ever taken
  asking = true;
  return ask('/talking-state?' + Q + (!force && T.loaded ? '&rev=' + T.rev + '&mark=' + encodeURIComponent(T.mark) : '')).then(function(res){
    if (look !== looks) return;                      // a newer look went out since: this is the older picture
    asking = false;
    var st = res.j;
    if (mine !== seq || saving) return;              // a save went out meanwhile: its answer is the newer one
    if (!st || st.ok === false) { T.emit('trouble', (st && st.words) || W.cant_reach); return; }
    if (st.rec) apply(st, force ? 'load' : 'poll'); else small(st);
  }, function(){ if (look !== looks) return; asking = false; T.emit('trouble', W.cant_reach); });
}
// May the 3-second look run now? Only while the page is showing and the talking video is paused; never with the
// photo menu or a picker open, never during a drag.
function quiet(){
  if (document.hidden || !$('vid').paused) return false;
  if ($('pick').classList.contains('open') || $('vpick').classList.contains('open') || $('pmenu').classList.contains('open')) return false;
  for (var i = 0; i < busy.length; i++) if (busy[i]()) return false;
  return true;
}
$('tlUndo').addEventListener('click', undo);
$('tlRedo').addEventListener('click', redo);

T.fill = fill; T.rich = rich; T.toast = toast; T.copy = copy; T.ask = ask; T.post = post;
T.P = P; T.total = total; T.secs = secs; T.pieceAt = pieceAt; T.reelAt = reelAt; T.srcAt = srcAt;
T.cutSet = cutSet; T.toRanges = toRanges; T.setRange = setRange; T.zoomOf = zoomOf; T.speedOf = speedOf; T.wordsOf = wordsOf;
T.snap = snap; T.save = save; T.undo = undo; T.redo = redo; T.forget = forget; T.undoButtons = undoButtons;
T.summary = summary; T.sizeDock = sizeDock; T.apply = apply; T.poll = poll; T.quiet = quiet;
T.start = function(){
  sizeDock();
  poll(true);
  T.timer = setInterval(function(){ if (quiet()) poll(false); }, DATA.lookEvery);
};
})();
"""
