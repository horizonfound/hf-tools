#!/usr/bin/env python3
"""Check the picker pages without a browser: the routes, the records, the commands, and the page's scripts.

    /usr/bin/python3 tests/arrange_check.py                 makes its own pretend kit under /private/tmp
    /usr/bin/python3 tests/arrange_check.py --work /private/tmp/somewhere --port 8841 --photos 14
    /usr/bin/python3 tests/arrange_check.py --only scripts  just the page's scripts (no server, two seconds)
    /usr/bin/python3 tests/arrange_check.py --only carousel just the carousel's slides and their job (its own kit and server)

It makes a pretend Assistant with tests/fake_kit.py in a new folder under /private/tmp (it refuses anywhere
else), points STUDIO_HOME at it, starts the page server on a scratch port, and prints one PASS or FAIL line
per case. A whole run starts its servers, one at a time, on ports from --port up to --port + 16 (or the next
free one after each). It never touches the real ~/.studio and never uses ports 8790, 8765 or 8770. The server it starts
is stopped at the end, whatever happened. The work folder is left in place so a failure can be looked at;
it is this script's own scratch and can be thrown away.

What it cannot do: drive a real pointer in the Claude app's pane. The page's scripts are run here on a
pretend page (below, PAGE_JS) under the Mac's own JavaScript engine, which catches a syntax error, a wrong
name, and a wrong rule, but not how the pane itself treats a press. That part is a person's to try.

Exit 0 when every case passes, 1 otherwise. Python 3.9, standard library only.
"""
import argparse
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts" / "reel.py"
SAFE = Path("/private/tmp")
NEVER_PORTS = (8790, 8765, 8770)
PY = sys.executable

results = []


def case(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + ((" -> " + str(detail)[:300]) if detail and not ok else ""), flush=True)
    return bool(ok)


# ---------- the page's scripts, on a pretend page ----------

PAGE_JS = r"""
// A pretend page for the picker's scripts: just enough of a browser to run them with no browser.
// Timers, frames and fetch are run by hand, so every step is in order and nothing is left to chance.
var window = this;
var RESULTS = [];
function check(name, ok, detail){ RESULTS.push([name, !!ok, detail == null ? '' : String(detail)]); }

// ---- timers and frames, run by hand ----
var _timers = [], _tid = 0, _frames = [];
function setTimeout(fn, ms){ _tid += 1; _timers.push({id: _tid, fn: fn, every: false}); return _tid; }
function setInterval(fn, ms){ _tid += 1; _timers.push({id: _tid, fn: fn, every: true}); return _tid; }
function clearTimeout(id){ _timers = _timers.filter(function(t){ return t.id !== id; }); }
var clearInterval = clearTimeout;
function requestAnimationFrame(fn){ _frames.push(fn); return _frames.length; }
function cancelAnimationFrame(){ _frames = []; }
function runTimers(){ var due = _timers.filter(function(t){ return !t.every; }); _timers = _timers.filter(function(t){ return t.every; }); due.forEach(function(t){ t.fn(); }); }
function runIntervals(){ _timers.filter(function(t){ return t.every; }).forEach(function(t){ t.fn(); }); }
function runFrame(){ var f = _frames; _frames = []; f.forEach(function(x){ x(); }); }
function settle(){ for (var i = 0; i < 6; i++) runTimers(); }
// the clock is run by hand too: wait(ms) moves it on
var CLOCK = 1790000000000;
Date.now = function(){ return CLOCK; };
function wait(ms){ CLOCK += ms; }

// ---- a promise that runs at once ----
function Now(state, value){ this.s = state; this.v = value; }
Now.prototype.then = function(ok, bad){
  try {
    if (this.s === 'ok') { if (!ok) return this; var r = ok(this.v); return r instanceof Now ? r : new Now('ok', r); }
    if (!bad) return this;
    var q = bad(this.v); return q instanceof Now ? q : new Now('ok', q);
  } catch (e) { return new Now('bad', e); }
};
Now.prototype.catch = function(bad){ return this.then(null, bad); };

// ---- elements ----
function matchOne(e, sel){
  sel = sel.trim();
  var m = /^([a-zA-Z0-9]*)((?:\.[\w-]+)*)$/.exec(sel);
  if (!m) throw new Error('selector not supported by the pretend page: ' + sel);
  if (m[1] && e.tagName !== m[1].toUpperCase()) return false;
  var cls = m[2] ? m[2].split('.').filter(Boolean) : [];
  for (var i = 0; i < cls.length; i++) if (e._cls.indexOf(cls[i]) < 0) return false;
  return true;
}
function matches(e, sel){ return sel.split(',').some(function(s){ return matchOne(e, s); }); }
function El(tag){
  var self = this;
  this.tagName = String(tag).toUpperCase(); this.children = []; this.parentNode = null; this._cls = [];
  this.dataset = {}; this._attrs = {}; this._on = {}; this._text = ''; this.hidden = false; this.disabled = false;
  this.id = ''; this.rect = {left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0};
  this.scrollTop = 0; this.scrollHeight = 0; this.clientHeight = 0; this.tabIndex = -1;
  this.style = {setProperty: function(k, v){ this[k] = String(v); }};
  this.classList = {
    add: function(c){ if (self._cls.indexOf(c) < 0) self._cls.push(c); },
    remove: function(c){ self._cls = self._cls.filter(function(x){ return x !== c; }); },
    contains: function(c){ return self._cls.indexOf(c) >= 0; },
    toggle: function(c, force){ var has = self._cls.indexOf(c) >= 0; var want = force === undefined ? !has : !!force; if (want && !has) self._cls.push(c); if (!want && has) this.remove(c); return want; }
  };
}
Object.defineProperty(El.prototype, 'className', {get: function(){ return this._cls.join(' '); }, set: function(v){ this._cls = String(v).split(/\s+/).filter(Boolean); }});
Object.defineProperty(El.prototype, 'textContent', {
  get: function(){ return this._text + this.children.map(function(c){ return c.textContent; }).join(''); },
  set: function(v){ this.children.forEach(function(c){ c.parentNode = null; }); this.children = []; this._text = v == null ? '' : String(v); }
});
Object.defineProperty(El.prototype, 'firstChild', {get: function(){ return this.children[0] || null; }});
Object.defineProperty(El.prototype, 'src', {get: function(){ return this._attrs.src || ''; }, set: function(v){ this._attrs.src = String(v); }});
Object.defineProperty(El.prototype, 'href', {get: function(){ return this._attrs.href || ''; }, set: function(v){ this._attrs.href = String(v); }});
El.prototype.appendChild = function(c){
  if (c._fragment) { var kids = c.children.slice(); c.children = []; for (var i = 0; i < kids.length; i++) { kids[i].parentNode = null; this.appendChild(kids[i]); } return c; }
  if (c.parentNode) c.parentNode.children = c.parentNode.children.filter(function(x){ return x !== c; });
  c.parentNode = this; this.children.push(c); return c;
};
El.prototype.insertBefore = function(c, ref){
  if (c.parentNode) c.parentNode.children = c.parentNode.children.filter(function(x){ return x !== c; });
  c.parentNode = this;
  var i = ref ? this.children.indexOf(ref) : -1;
  if (i < 0) this.children.push(c); else this.children.splice(i, 0, c);
  return c;
};
El.prototype.remove = function(){ if (this.parentNode) { var me = this; this.parentNode.children = this.parentNode.children.filter(function(x){ return x !== me; }); this.parentNode = null; } };
El.prototype.contains = function(n){ for (var x = n; x; x = x.parentNode) if (x === this) return true; return false; };
El.prototype.closest = function(sel){ for (var x = this; x && x.tagName; x = x.parentNode) if (matches(x, sel)) return x; return null; };
El.prototype.querySelectorAll = function(sel){ var out = []; (function walk(e){ e.children.forEach(function(c){ if (matches(c, sel)) out.push(c); walk(c); }); })(this); return out; };
El.prototype.querySelector = function(sel){ return this.querySelectorAll(sel)[0] || null; };
El.prototype.setAttribute = function(k, v){ this._attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return k in this._attrs ? this._attrs[k] : null; };
El.prototype.removeAttribute = function(k){ delete this._attrs[k]; };
El.prototype.getBoundingClientRect = function(){ return this.rect; };
El.prototype.addEventListener = function(type, fn, cap){ (this._on[type] = this._on[type] || []).push({fn: fn, cap: !!cap}); };
function box(e, l, t, w, h){ e.rect = {left: l, top: t, right: l + w, bottom: t + h, width: w, height: h}; }

var document = new El('#document');
document.tagName = '';
document.hidden = false; document.title = '';
document.body = new El('body'); document.appendChild(document.body);
document.createElement = function(tag){ return new El(tag); };
document.createDocumentFragment = function(){ var f = new El('#fragment'); f._fragment = true; return f; };
document.getElementById = function(id){ var hit = null; (function walk(e){ e.children.forEach(function(c){ if (!hit && c.id === id) hit = c; if (!hit) walk(c); }); })(document); return hit; };
var _winOn = {};
window.addEventListener = function(type, fn){ (_winOn[type] = _winOn[type] || []).push(fn); };
// send an event the way a browser does: capture listeners on the document first, then up from the target
function fire(target, type, props){
  var ev = {type: type, target: target, _stop: false, defaultPrevented: false,
            preventDefault: function(){ this.defaultPrevented = true; }, stopPropagation: function(){ this._stop = true; }};
  for (var k in (props || {})) ev[k] = props[k];
  (document._on[type] || []).forEach(function(l){ if (l.cap && !ev._stop) l.fn(ev); });
  for (var x = target; x && !ev._stop; x = x.parentNode) (x._on[type] || []).forEach(function(l){ if (!(x === document && l.cap) && !ev._stop) l.fn(ev); });
  return ev;
}
function fireWindow(type){ (_winOn[type] || []).forEach(function(fn){ fn({type: type}); }); }
var location = {reloaded: 0, reload: function(){ this.reloaded += 1; }};
function Image(){ }
Object.defineProperty(Image.prototype, 'src', {get: function(){ return this._src; }, set: function(v){ this._src = v; if (this.onload) this.onload(); }});

// ---- the page's own elements (ids come from the real page) ----
PAGE_ELS.forEach(function(d){ var e = new El(d.tag); e.id = d.id; e.className = d.cls; e.hidden = d.hidden; e.disabled = d.disabled; document.body.appendChild(e); });
(function(){
  var big = document.getElementById('big'), b = new El('div'); b.className = 'box';
  var pic = new El('div'); pic.className = 'pic'; pic.appendChild(new El('img'));
  var where = new El('p'); where.className = 'where';
  var acts = new El('div'); acts.className = 'bacts';
  ['bx', 'nav prev', 'nav next'].forEach(function(c){ var x = new El('button'); x.className = c; b.appendChild(x); });
  b.appendChild(pic); b.appendChild(where); b.appendChild(acts); big.appendChild(b);
  document.getElementById('poolsec').appendChild(document.getElementById('pool'));
  document.getElementById('panel').appendChild(document.getElementById('rowwrap'));
  document.getElementById('rowwrap').appendChild(document.getElementById('row'));
})();
document.body.dataset.kit = 'A kit'; document.body.dataset.piece = PIECE_NAME;

// ---- a pretend Assistant behind /arrange-state and /arrange, keeping the real rules for the counter ----
// (the counter is the Assistant's: one higher for every change it takes. A change is taken from a page whose
// "base" is the stored counter, or whose own last save, from that same base, is what is stored.)
var SERVER = {mode: 'up', posts: [], gets: 0, from: null, opens: [], openAnswer: {ok: true, words: 'Opened Carousel in Finder.'},
  doneAnswer: null,     // the carousel: what the Assistant adds to its answer when the final button is pressed
  st: {ok: true, name: 'Fake beach', piece: 'reel', stamp: 'aaa', rev: 0, total: 30, photos: [],
       first: {nums: [1, 6, 11, 16, 21], marks: ['', '', '', '', '']}, now: {nums: [1, 6, 11, 16, 21], marks: ['', '', '', '', '']},
       happy: null, dropped: [], limits: {min: 2, max: 60, best: [8, 14]}, previews: {made: 30, of: 30}, job: null,
       reel_made: false, canva: false, kit_page: true}};
for (var i = 1; i <= 30; i++) SERVER.st.photos.push({n: i, way: 'tall', w: 1200, h: 1800, v: 'v' + i, missing: false, have: true});
function copy(o){ return JSON.parse(JSON.stringify(o)); }
function reply(code, obj){ return new Now('ok', {status: code, json: function(){ return new Now('ok', copy(obj)); }}); }
function fetch(url, opts){
  if (SERVER.mode === 'down') return new Now('bad', new Error('no answer'));
  if (url.indexOf('/arrange-state') === 0) { SERVER.gets += 1; return reply(200, SERVER.st); }
  if (url.indexOf('/open?') === 0) { SERVER.opens.push(url); return reply(200, SERVER.openAnswer); }
  if (url === '/arrange') {
    var b = JSON.parse(opts.body); SERVER.posts.push(b);
    if (SERVER.mode === 'lost') { SERVER.mode = 'up'; apply(b); return new Now('bad', new Error('answer lost')); }
    if (SERVER.mode === 'photos') return reply(409, {ok: false, why: 'photos', words: 'changed'});
    if (SERVER.mode === 'refuse') return reply(400, {ok: false, words: 'That didn\u2019t arrive the way it should have. Reload the page and try again.'});
    if (SERVER.mode === 'unplugged') return reply(404, {ok: false, words: 'I can\u2019t find that shoot\u2019s posts. Is the drive plugged in?'});
    var st = SERVER.st, same = JSON.stringify(st.now.nums) === JSON.stringify(b.nums) && JSON.stringify(st.now.marks) === JSON.stringify(b.marks);
    var own = !!SERVER.from && SERVER.from.page === b.page && SERVER.from.base === b.base;
    if (!same && b.base !== st.rev && !own) return reply(409, {ok: false, why: 'newer', words: 'newer', state: st});
    if (same) { if (b.done) st.happy = {rev: st.rev}; return reply(200, answer(b, st)); }
    apply(b);
    return reply(200, answer(b, st));
  }
  return new Now('bad', new Error('unknown address ' + url));
}
function answer(b, st){
  var a = {ok: true, words: 'Saved', rev: st.rev, job: false};
  if (b.done && SERVER.doneAnswer) for (var k in SERVER.doneAnswer) a[k] = SERVER.doneAnswer[k];
  return a;
}
function apply(b){ var st = SERVER.st; st.now = {nums: b.nums.slice(), marks: b.marks.slice()}; st.rev += 1; SERVER.from = {page: b.page, base: b.base}; if (b.done) st.happy = {rev: st.rev}; }

// ---- which story this run tells ----
if (SCENARIO === 'preparing') {
  // copies still being made for photos 1 to 10; photo 3 can't be reached and has no copy; photo 4 can't be
  // reached but an older copy of it exists; two photos have left the shoot
  SERVER.st.photos.forEach(function(p){ if (p.n <= 10) p.have = false; });
  SERVER.st.photos[2].missing = true; SERVER.st.photos[3].missing = true; SERVER.st.photos[3].have = true;
  SERVER.st.previews = {made: 21, of: 30}; SERVER.st.dropped = [41, 42]; SERVER.st.kit_page = false; SERVER.st.reel_made = true;
  SERVER.st.happy = {rev: 0};
}
if (SCENARIO === 'gone') SERVER.st = {ok: false, words: 'I can\u2019t find that shoot\u2019s posts. Is the drive plugged in?'};
if (PIECE_NAME === 'carousel') {
  SERVER.st.piece = 'carousel'; SERVER.st.limits = {min: 2, max: 20, best: [5, 8]};
  SERVER.doneAnswer = {job: true, same: false, line: 'Making your slides...'};
}
var DONE5 = 'Done. 5 slides are in your Carousel folder.';
if (SCENARIO === 'carousel-resume') { SERVER.st.happy = {rev: 0}; SERVER.st.job = {state: 'running', line: 'Making your slides...', rev: 0, count: 5}; }
if (SCENARIO === 'carousel-made') { SERVER.st.canva = true; SERVER.st.job = {state: 'done', line: DONE5, rev: 0, count: 5}; }
if (SCENARIO === 'carousel-same') { SERVER.st.canva = true; SERVER.st.job = {state: 'same', line: 'Your slides are already in this order.', rev: 0, count: 5}; }
if (SCENARIO === 'carousel-long') {
  // an older pick of Claude's with more photos than a carousel holds
  var LONG = [], LMARKS = [];
  for (var li = 1; li <= 22; li++) { LONG.push(li); LMARKS.push(''); }
  SERVER.st.first = {nums: LONG.slice(), marks: LMARKS.slice()}; SERVER.st.now = {nums: LONG.slice(), marks: LMARKS.slice()};
}
if (SCENARIO === 'down') SERVER.mode = 'down';

// ---- the three scripts, exactly as the page carries them ----
(new Function(MODEL_SRC)).call(this);
(new Function(DRAG_SRC)).call(this);
(new Function(PICKER_SRC)).call(this);

// ---- helpers for the checks ----
var byId = function(id){ return document.getElementById(id); };
var rowEl = byId('row'), poolEl = byId('pool'), panel = byId('panel'), poolSec = byId('poolsec'), wrap = byId('rowwrap'), dock = byId('dock');
function rowNums(){ return rowEl.querySelectorAll('.rt').map(function(t){ return Number(t.dataset.n); }); }
function rowTile(n){ return rowEl.querySelectorAll('.rt').filter(function(t){ return Number(t.dataset.n) === n; })[0]; }
function poolTile(n){ return poolEl.querySelectorAll('.pt').filter(function(t){ return Number(t.dataset.n) === n; })[0]; }
function lifted(){ return document.body.querySelectorAll('.arr-lift').length; }
function text(id){ return byId(id).textContent; }
function lastPost(){ return SERVER.posts[SERVER.posts.length - 1]; }
// lay the page out: the sticky panel on top, the row's tiles on lines of `perLine`, the photos below, and
// the bar of buttons held at the bottom of the window (here the window is 1100 tall), over the photos below
// (the row's own box is 190 tall unless told otherwise: about one line of photos, as on the real page)
// A row tile and its picture are the same box, 2 wide to 3 tall: the Normal / Longer / Quicker bar lies on
// the photo, not under it. The panel still has 100 px under the row's box: the lines under the row.
function layout(perLine, boxH){
  boxH = boxH || 190;
  box(panel, 0, 0, 800, 40 + boxH + 100); box(wrap, 10, 40, 780, boxH); box(rowEl, 10, 40, 780, 400); box(poolSec, 0, 360, 800, 3000); box(poolEl, 0, 400, 800, 2900);
  box(dock, 0, 1000, 800, 100);
  rowEl.querySelectorAll('.rt').forEach(function(t, i){
    var x = 20 + (i % perLine) * 100, y = 50 + Math.floor(i / perLine) * 170;
    box(t, x, y, 90, 135); box(t.querySelector('.ph'), x, y, 90, 135);
  });
  poolEl.querySelectorAll('.pt').forEach(function(t, i){ box(t, 10 + (i % 7) * 110, 410 + Math.floor(i / 7) * 160, 100, 150); });
}
var PID = 1;
function press(target, x, y, more){ var p = {pointerId: PID, isPrimary: true, button: 0, buttons: 1, pointerType: 'mouse', clientX: x, clientY: y}; for (var k in (more || {})) p[k] = more[k]; return fire(target, 'pointerdown', p); }
function move(x, y, more){ var p = {pointerId: PID, isPrimary: true, button: 0, buttons: 1, pointerType: 'mouse', clientX: x, clientY: y}; for (var k in (more || {})) p[k] = more[k]; return fire(document, 'pointermove', p); }
function release(x, y, more){ var p = {pointerId: PID, isPrimary: true, button: 0, buttons: 0, pointerType: 'mouse', clientX: x, clientY: y}; for (var k in (more || {})) p[k] = more[k]; return fire(document, 'pointerup', p); }
function centre(e){ return [(e.rect.left + e.rect.right) / 2, (e.rect.top + e.rect.bottom) / 2]; }
function dragTo(tile, x, y){ var c = centre(tile); press(tile, c[0], c[1]); move(c[0] + 12, c[1] + 12); move(x, y); }
function clickButton(b){ fire(b, 'click', {}); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }

// ============ the checks ============
if (SCENARIO === 'preparing') {
  check('while copies are being made the page says how many are ready', text('prep') === 'Getting your photos ready: 21 of 30' && !byId('prep').hidden, text('prep'));
  check('a photo that can\u2019t be read says so on its tile', poolTile(3).classList.contains('cantread') && poolTile(3).textContent.indexOf('Can\u2019t read this photo right now') >= 0 && !poolTile(3).querySelector('img'));
  check('a photo that can\u2019t be reached but has a copy still shows', !!poolTile(4).querySelector('img') && !poolTile(4).classList.contains('cantread'));
  check('one line at the top says why', text('l-missing') === 'Some photos can\u2019t be read right now. Is the drive plugged in?' && !byId('l-missing').hidden, text('l-missing'));
  check('photos that left the shoot are named in a line', text('l-dropped') === '2 photos are no longer in this shoot, so they were taken out.' && !byId('l-dropped').hidden, text('l-dropped'));
  check('a tile with no copy yet has no picture', !poolTile(5).querySelector('img') && !rowTile(1).querySelector('img') && !rowTile(1).classList.contains('cantread'));
  check('no link to a kit page that is not there', byId('kitlink').hidden);
  check('a reel that was already made, its new order still waiting for Claude: the other saved line', text('doneline').indexOf('I\u2019ll make a new reel in this order. The one already in CapCut stays as it is.') > 0, text('doneline'));
  layout(10); cc = centre(poolTile(5)); press(poolTile(5), cc[0], cc[1]); release(cc[0], cc[1]);
  var bp = byId('big').querySelector('.pic');
  check('the big view of a photo whose copy is not made yet says it is being got ready, not that it can\u2019t be read', byId('big').classList.contains('on') && bp.classList.contains('notyet') && !bp.classList.contains('cantread') && !bp.querySelector('img').getAttribute('src'));
  SERVER.st.photos.forEach(function(p){ if (p.n >= 5 && p.n <= 10) p.have = true; });
  var gets = SERVER.gets; runIntervals();
  check('and it shows the photo as soon as its copy arrives', !bp.classList.contains('notyet') && !bp.classList.contains('cantread') && (bp.querySelector('img').getAttribute('src') || '').indexOf('n=5&') > 0, bp.querySelector('img').getAttribute('src'));
  fire(document, 'keydown', {key: 'Escape'});
  check('the page asks again and tiles fill in as copies arrive', SERVER.gets === gets + 1 && !!poolTile(5).querySelector('img') && !poolTile(1).querySelector('img') && text('prep') === 'Getting your photos ready: 27 of 30', text('prep'));
  SERVER.st.photos.forEach(function(p){ if (p.n <= 2) p.have = true; });
  runIntervals();
  check('a row tile gets its picture too', !!rowTile(1).querySelector('img'));
  check('when every copy is made the count line goes and the quick asking stops (the slow watch stays)', byId('prep').hidden && _timers.length === 1 && _timers[0].every, text('prep') + ' timers ' + _timers.length);
  check('the row was not disturbed by the asking', eq(rowNums(), [1, 6, 11, 16, 21]));
  layout(10); cc = centre(poolTile(3)); press(poolTile(3), cc[0], cc[1]); release(cc[0], cc[1]);
  check('the big view of a photo that can\u2019t be read says so', byId('big').classList.contains('on') && byId('big').querySelector('.pic').classList.contains('cantread') && !byId('big').querySelector('.pic').classList.contains('notyet'));
} else if (SCENARIO === 'gone') {
  check('a shoot that can\u2019t be found: the page says so in plain words', text('l-reach') === 'I can\u2019t find that shoot\u2019s posts. Is the drive plugged in?' && !byId('l-reach').hidden, text('l-reach'));
  check('and draws nothing', rowNums().length === 0 && byId('happy').disabled);
} else if (SCENARIO === 'carousel-resume') {
  // the page opened (or reloaded) while the slides are being made: it waits, and shows the result
  check('opened while the slides are being made: the line says so', text('doneline') === 'Making your slides...' && byId('openfolder').hidden, text('doneline'));
  var g0 = SERVER.gets; runIntervals();
  check('and it keeps asking', SERVER.gets === g0 + 1 && text('doneline') === 'Making your slides...', SERVER.gets - g0);
  SERVER.st.job = {state: 'done', line: DONE5, rev: 0, count: 5}; runIntervals();
  check('when the job is done the line and the folder button appear', text('doneline') === DONE5 && !byId('openfolder').hidden, text('doneline'));
  check('with no Canva slides there is no Canva line', byId('canvaline').hidden && text('canvaline') === '');
  var t1 = _timers.length; runIntervals();
  check('and the quick asking has stopped (the slow watch stays)', _timers.length === 1 && _timers[0].every, t1 + ' then ' + _timers.length);
} else if (SCENARIO === 'carousel-made') {
  // the page opened with the slides already made for the order it shows (made earlier, or from the chat)
  check('opened with the slides already made for this order: the line and the folder button are there', text('doneline') === DONE5 && !byId('openfolder').hidden, text('doneline'));
  check('and the Canva line, when the kit has Canva slides', !byId('canvaline').hidden && text('canvaline') === 'Your Canva slides still show the old photos. Say “redo the Canva carousel” to Claude.', text('canvaline'));
  check('no asking beyond the slow watch', _timers.length === 1 && _timers[0].every, _timers.length);
  layout(10);
  clickButton(rowTile(16).querySelector('.x')); settle();
  check('a change after that: the line says it has changed since, and the button and the Canva line go', text('doneline') === 'You’ve changed it since. Press the button again when it’s right.' && byId('openfolder').hidden && byId('canvaline').hidden, text('doneline'));
  // a job that finished for some OTHER order says nothing about this one
  SERVER.st.job = {state: 'done', line: 'Done. 9 slides are in your Carousel folder.', rev: 77, count: 9}; runIntervals();
  check('a result for some other order is not shown as this one’s', text('doneline').indexOf('9 slides') < 0, text('doneline'));
  // the slides made from the chat for the order now on the page: the open page shows it by itself
  SERVER.st.job = {state: 'done', line: 'Done. 4 slides are in your Carousel folder.', rev: SERVER.st.rev, count: 4}; runIntervals();
  check('slides made from the chat for the order on the page: the line appears by itself', text('doneline') === 'Done. 4 slides are in your Carousel folder.' && !byId('openfolder').hidden, text('doneline'));
} else if (SCENARIO === 'carousel') {
  settle();
  check('carousel: the heading is the shoot and the piece', text('title') === 'Fake beach carousel' && text('eyebrow') === 'Carousel' && text('rowname') === 'Your carousel', text('title'));
  check('carousel: the help line is the carousel’s', text('help') === 'Your carousel, in the order people swipe. Drag a photo to move it. Drag one up from below to add it. Click any photo to see it big.', text('help'));
  check('carousel: the line under the row is about the first photo', text('legend') === 'The first photo is the one people see in their feed, so lead with your strongest.', text('legend'));
  check('carousel: no Normal / Longer / Quicker bar under a photo, and the X is there', rowEl.querySelectorAll('.mk').length === 0 && !!rowTile(6).querySelector('.x'));
  check('carousel: 5 photos needs no advice', text('count') === '5 photos' && text('advice') === '', text('advice'));
  check('carousel: before the final button there is no line, no folder button, no Canva line', text('doneline') === '' && byId('openfolder').hidden && byId('canvaline').hidden && text('openline') === '');
  check('carousel: and no Lay out the slides link', byId('layout').hidden && byId('layout').href === '');
  layout(10);
  dragTo(poolTile(30), rowTile(21).rect.left - 4, 100); release(rowTile(21).rect.left - 4, 100);
  check('carousel: a photo dragged up lands between the 4th and 5th', eq(rowNums(), [1, 6, 11, 16, 30, 21]), rowNums());
  settle();
  check('carousel: the save names the piece and carries no marks that mean anything', lastPost().piece === 'carousel' && eq(lastPost().nums, [1, 6, 11, 16, 30, 21]) && lastPost().marks.join('') === '' && lastPost().done === false, JSON.stringify(lastPost()));
  layout(10);
  var cc2 = centre(rowTile(11)); press(rowTile(11), cc2[0], cc2[1]); release(cc2[0], cc2[1]);
  var bigc = byId('big');
  check('carousel: the big view says where the photo is in the carousel', bigc.querySelector('.where').textContent === 'Number 3 of 6 in your carousel.', bigc.querySelector('.where').textContent);
  var labels = bigc.querySelectorAll('button').map(function(b){ return b.textContent; }).join('|');
  check('carousel: the big view has no Normal / Longer / Quicker', labels.indexOf('Longer') < 0 && labels.indexOf('Quicker') < 0 && labels.indexOf('Normal') < 0 && labels.indexOf('Move it earlier') >= 0, labels);
  fire(document, 'keydown', {key: 'Escape'});
  // the count line's advice
  [2, 3, 4].forEach(function(n){ dragTo(poolTile(n), 790, 100); release(790, 100); layout(10); });
  check('carousel: over 8 photos the count line says what usually works', text('count') === '9 photos' && text('advice') === '5 to 8 usually works best', text('count') + ' / ' + text('advice'));
  settle();
  [2, 3, 4, 30].forEach(function(n){ clickButton(rowTile(n).querySelector('.x')); layout(10); });
  settle();
  check('carousel: back to five', eq(rowNums(), [1, 6, 11, 16, 21]) && text('advice') === '', rowNums());

  // ---- the final button: the slides are made by the Assistant, and the page waits by asking ----
  var R = SERVER.st.rev;
  clickButton(rowTile(16).querySelector('.x'));                  // an unsaved change is waiting when they press it
  clickButton(byId('happy'));
  check('carousel: the final button sends the change and done together', lastPost().done === true && eq(lastPost().nums, [1, 6, 11, 21]), JSON.stringify(lastPost()));
  settle();
  R = SERVER.st.rev;
  check('carousel: the line reads Making your slides... and there is no folder button yet', text('doneline') === 'Making your slides...' && byId('openfolder').hidden && text('status') === 'Saved', text('doneline'));
  check('carousel: while the slides are being made there is no Lay out the slides link', byId('layout').hidden);
  SERVER.st.job = {state: 'queued', line: 'Making your slides...', rev: R, count: 4};
  var g1 = SERVER.gets; runIntervals();
  check('carousel: the page asks how the slides are getting on', SERVER.gets === g1 + 1 && text('doneline') === 'Making your slides...', SERVER.gets - g1);
  SERVER.st.job = {state: 'running', line: 'Making your slides...', rev: R, count: 4}; runIntervals();
  check('carousel: still being made, still says so', text('doneline') === 'Making your slides...' && byId('openfolder').hidden);
  SERVER.st.job = {state: 'done', line: 'Done. 4 slides are in your Carousel folder.', rev: R, count: 4}; runIntervals();
  check('carousel: done: the result, with Open the Carousel folder on the same line', text('doneline') === 'Done. 4 slides are in your Carousel folder.' && !byId('openfolder').hidden, text('doneline'));
  check('carousel: the folder button sits beside the line it belongs to (same row of the page)', DONE_ROW_HOLDS_BUTTON === true);
  check('carousel: done: Lay out the slides appears with it, a link to this shoot\u2019s designer by the kit\u2019s name only', !byId('layout').hidden && byId('layout').href === '/design.html?kit=A%20kit', byId('layout').href);
  check('carousel: and showing that link asked the Assistant for nothing (no folder is opened)', SERVER.opens.length === 0);
  check('carousel: the quick asking stops once the result is in', _timers.length === 1 && _timers[0].every, _timers.length);
  check('carousel: no Canva line when the kit has no Canva slides', byId('canvaline').hidden);
  clickButton(byId('openfolder'));
  check('carousel: the folder button asks the Assistant to open this kit’s Carousel folder, by name only', SERVER.opens.length === 1 && SERVER.opens[0] === '/open?kit=A%20kit&sub=Carousel', SERVER.opens[0]);
  check('carousel: and its answer shows right under it', text('openline') === 'Opened Carousel in Finder.', text('openline'));
  SERVER.openAnswer = {ok: true, words: 'Opened Carousel in Finder, behind this window. Click Finder in the Dock to see it.'};
  clickButton(byId('openfolder'));
  check('carousel: the other answer (Finder behind the window) shows the same way', text('openline').indexOf('behind this window') > 0, text('openline'));

  // a change afterwards
  layout(10);
  clickButton(rowTile(21).querySelector('.x')); settle();
  check('carousel: a change afterwards: the line says so, and the folder button and its answer go', text('doneline') === 'You’ve changed it since. Press the button again when it’s right.' && byId('openfolder').hidden && text('openline') === '', text('doneline') + ' / ' + text('openline'));
  check('carousel: a change afterwards: the Lay out the slides link goes too', byId('layout').hidden);

  // pressed with the slides already in that order
  SERVER.doneAnswer = {job: false, same: true, line: 'Your slides are already in this order.'};
  clickButton(byId('happy')); settle();
  check('carousel: slides already in this order: the line says so, with the folder button, and nothing is asked', text('doneline') === 'Your slides are already in this order.' && !byId('openfolder').hidden && _timers.length === 1, text('doneline'));
  check('carousel: slides already in this order: the Lay out the slides link is there too', !byId('layout').hidden && byId('layout').href === '/design.html?kit=A%20kit', byId('layout').href);

  // a problem
  SERVER.doneAnswer = {job: true, same: false, line: 'Making your slides...'};
  layout(10);
  dragTo(poolTile(12), 790, 100); release(790, 100); settle();
  clickButton(byId('happy')); settle();
  R = SERVER.st.rev;
  var TROUBLE = 'Couldn’t make the slides: photo 12 can’t be read. Is the drive plugged in? Your Carousel folder was left as it was.';
  SERVER.st.job = {state: 'problem', line: TROUBLE, rev: R, count: 4}; runIntervals();
  check('carousel: a problem shows its plain words, with no folder button', text('doneline') === TROUBLE && byId('openfolder').hidden, text('doneline'));
  check('carousel: a problem: no Lay out the slides link either', byId('layout').hidden);

  // a result for an older order does not end the wait for a newer one
  layout(10);
  clickButton(rowTile(12).querySelector('.x')); settle();
  dragTo(poolTile(13), 790, 100); release(790, 100); settle();
  clickButton(byId('happy')); settle();
  var R2 = SERVER.st.rev;
  SERVER.st.job = {state: 'done', line: 'Done. 4 slides are in your Carousel folder.', rev: R2 - 2, count: 4}; runIntervals();
  check('carousel: a result for an older order does not end the wait', text('doneline') === 'Making your slides...' && byId('openfolder').hidden, text('doneline'));
  // the page's timers running very late (a page that is not in front) must not turn a finished job into a slow one
  wait(600000);
  SERVER.st.job = {state: 'done', line: 'Done. 4 slides are in your Carousel folder.', rev: R2, count: 4}; runIntervals();
  check('carousel: timers ten minutes late, and the job long done: the result is shown, not a complaint', text('doneline') === 'Done. 4 slides are in your Carousel folder.' && !byId('openfolder').hidden, text('doneline'));

  // a job already at work: the Assistant's own words for it
  SERVER.doneAnswer = {job: true, same: false, line: 'Your slides are already being made. One moment.'};
  clickButton(byId('happy')); settle();
  check('carousel: a job already at work: the page says so while it waits', text('doneline') === 'Your slides are already being made. One moment.' && byId('openfolder').hidden, text('doneline'));
  // the Assistant not answering while the page waits: it keeps waiting, and keeps asking
  SERVER.mode = 'down'; runIntervals(); runIntervals();
  check('carousel: the Assistant starting over while the slides are made: the page keeps waiting', text('doneline') === 'Your slides are already being made. One moment.' && _timers.length === 2, text('doneline'));
  SERVER.mode = 'up';
  SERVER.st.job = {state: 'running', line: 'Making your slides...', rev: SERVER.st.rev, count: 4};
  wait(179000); runIntervals();
  check('carousel: just under three minutes: still waiting', text('doneline') === 'Your slides are already being made. One moment.', text('doneline'));
  wait(2000); runIntervals();
  check('carousel: after three minutes with no result it stops asking and says to tell Claude', text('doneline') === 'This is taking longer than it should. Tell Claude.' && byId('openfolder').hidden && _timers.length === 1, text('doneline') + ' timers ' + _timers.length);
  runIntervals(); runIntervals();
  check('carousel: having said that, the page does not go back to saying the slides are being made', text('doneline') === 'This is taking longer than it should. Tell Claude.' && _timers.length === 1, text('doneline'));
  // and if the result turns up later, the page shows it
  SERVER.st.job = {state: 'done', line: 'Done. 4 slides are in your Carousel folder.', rev: SERVER.st.rev, count: 4}; runIntervals();
  check('carousel: a result that turns up after that is still shown', text('doneline') === 'Done. 4 slides are in your Carousel folder.' && !byId('openfolder').hidden, text('doneline'));

  // Canva slides exist: the line under the result
  SERVER.doneAnswer = {job: true, same: false, line: 'Making your slides...'};
  SERVER.st.canva = true;
  layout(10);
  dragTo(poolTile(14), 790, 100); release(790, 100); settle();
  clickButton(byId('happy')); settle();
  SERVER.st.job = {state: 'done', line: DONE5, rev: SERVER.st.rev, count: 5}; runIntervals();
  check('carousel: with Canva slides in the kit, a line under the result says they show the old photos', text('doneline') === DONE5 && !byId('canvaline').hidden && text('canvaline') === 'Your Canva slides still show the old photos. Say “redo the Canva carousel” to Claude.', text('canvaline'));

  // under two photos, and a full carousel
  layout(10);
  rowNums().slice(1).forEach(function(n){ clickButton(rowTile(n).querySelector('.x')); layout(10); });
  check('carousel: with one photo the count line and the reason beside the button both say it needs 2', text('advice') === 'A carousel needs at least 2' && byId('happy').disabled && text('why') === 'A carousel needs at least 2', text('advice') + ' / ' + text('why'));
  settle();
  for (var q = 1; q <= 25 && rowNums().length < 20; q++) { if (rowNums().indexOf(q) < 0) { dragTo(poolTile(q), 790, 100); release(790, 100); layout(10); } }
  check('carousel: twenty photos fit', rowNums().length === 20, rowNums().length);
  var full = rowNums();
  dragTo(poolTile(29), 100, 100);
  check('carousel: a twenty-first shows no bar', !rowEl.querySelector('.ins').classList.contains('on'));
  release(100, 100);
  check('carousel: and is refused with the line under the row', eq(rowNums(), full) && text('rowline') === 'Instagram allows up to 20. Take one out first.', text('rowline'));
  settle();
} else if (SCENARIO === 'carousel-two') {
  // two windows on one carousel: this one presses the button; before it has looked again, the OTHER window
  // presses on a newer order. The Assistant's job goes on to that newer order and never writes a result
  // for this window's, so this window must not go on saying "Making your slides..." for three minutes.
  layout(10);
  clickButton(rowTile(16).querySelector('.x')); settle();
  clickButton(byId('happy')); settle();
  var RA = SERVER.st.rev;
  check('two windows: this one pressed the button and is waiting', text('doneline') === 'Making your slides...' && _timers.length === 2, text('doneline'));
  SERVER.st.now = {nums: [1, 6], marks: ['', '']}; SERVER.st.rev = RA + 1; SERVER.st.happy = {rev: RA + 1}; SERVER.from = {page: 'otherwindow1', base: RA};
  SERVER.st.job = {state: 'running', line: 'Making your slides...', rev: RA + 1, count: 2};
  runIntervals();
  check('two windows: the other one pressed on a newer order: this page takes that order at its next look', eq(rowNums(), [1, 6]), rowNums());
  check('two windows: and says what is true of it: those slides are being made', text('doneline') === 'Making your slides...' && byId('openfolder').hidden, text('doneline'));
  wait(100000);
  SERVER.st.job = {state: 'done', line: 'Done. 2 slides are in your Carousel folder.', rev: RA + 1, count: 2};
  runIntervals();
  check('two windows: when they are made it says so, with the folder button (no three-minute wait, no complaint)', text('doneline') === 'Done. 2 slides are in your Carousel folder.' && !byId('openfolder').hidden, text('doneline'));
  check('two windows: and the quick asking has stopped', _timers.length === 1 && _timers[0].every, _timers.length);
  // the same, when this page cannot take the newer order yet (a photo is lifted): the wait still ends
  SERVER.doneAnswer = {job: true, same: false, line: 'Making your slides...'};
  layout(10);
  dragTo(poolTile(11), 790, 100); release(790, 100); settle();
  clickButton(byId('happy')); settle();
  var RB = SERVER.st.rev;
  check('two windows, again: pressed and waiting', text('doneline') === 'Making your slides...', text('doneline'));
  layout(10);
  dragTo(rowTile(1), 300, 100);                          // a photo is in the air: nothing here may be swapped out
  SERVER.st.now = {nums: [6, 1], marks: ['', '']}; SERVER.st.rev = RB + 1; SERVER.st.happy = {rev: RB + 1}; SERVER.from = {page: 'otherwindow1', base: RB};
  SERVER.st.job = {state: 'done', line: 'Done. 2 slides are in your Carousel folder.', rev: RB + 1, count: 2};
  runIntervals();
  check('two windows, a photo in the air: the row is left alone, and the page stops saying its slides are being made', rowNums().length === 3 && text('doneline') !== 'Making your slides...' && text('doneline').indexOf('taking longer') < 0, text('doneline'));
  check('two windows, a photo in the air: the quick asking has stopped', _timers.filter(function(t){ return t.every; }).length === 1, _timers.length);
} else if (SCENARIO === 'carousel-same') {
  // the slides were already in this order (Claude's apply found nothing to change), and the kit's Canva
  // slides were made from another order: the Canva line belongs with this result too
  check('slides already in this order, Canva slides from another order: the Canva line shows', text('doneline') === 'Your slides are already in this order.' && !byId('openfolder').hidden && !byId('canvaline').hidden && text('canvaline') === 'Your Canva slides still show the old photos. Say “redo the Canva carousel” to Claude.', text('canvaline'));
  SERVER.st.canva = false; runIntervals();
  check('once Claude has filled the template again the Canva line goes by itself, and the result stays', byId('canvaline').hidden && text('canvaline') === '' && text('doneline') === 'Your slides are already in this order.', text('canvaline'));
} else if (SCENARIO === 'carousel-long') {
  // 22 photos in a carousel (an older pick): the button is off and the page says why and what to do
  check('more than a carousel holds: all of them are shown', rowNums().length === 22 && text('count') === '22 photos', text('count'));
  check('more than a carousel holds: the button is off, and the line beside it says why and what to do', byId('happy').disabled && text('why') === 'Instagram allows up to 20. Take one out first.', text('why'));
  var p0 = SERVER.posts.length;
  clickButton(byId('happy')); settle();
  check('more than a carousel holds: pressing the button sends nothing', SERVER.posts.length === p0, SERVER.posts.length - p0);
  layout(10);
  clickButton(rowTile(22).querySelector('.x')); settle();
  check('one taken out (21): that is saved, with no Reload line, and the button is still off', lastPost().nums.length === 21 && lastPost().done === false && byId('note').hidden && text('status') === 'Saved' && byId('happy').disabled && text('why') === 'Instagram allows up to 20. Take one out first.', text('why'));
  layout(10);
  clickButton(rowTile(21).querySelector('.x')); settle();
  check('another taken out (20): the button is on and the line is gone', !byId('happy').disabled && text('why') === '' && rowNums().length === 20, text('why'));
} else if (SCENARIO === 'down') {
  check('the Assistant not answering at the start: the page says so', text('l-reach') === 'Could not reach the Assistant. Tell Claude instead.' && !byId('l-reach').hidden, text('l-reach'));
  SERVER.mode = 'up'; runTimers();
  check('and it opens by itself once the Assistant is back', eq(rowNums(), [1, 6, 11, 16, 21]) && byId('l-reach').hidden && text('status') === 'Saved', rowNums());
} else {
settle();
check('opens with the Assistant’s pick in the row', eq(rowNums(), [1, 6, 11, 16, 21]), rowNums());
check('every photo of the shoot is below', poolEl.querySelectorAll('.pt').length === 30, poolEl.querySelectorAll('.pt').length);
check('a picked photo below is dimmed and carries its place', poolTile(11).classList.contains('in') && poolTile(11).querySelector('.pos').textContent === '3' && !poolTile(2).classList.contains('in'));
check('every photo below carries its own number, as #12', poolTile(12).querySelector('.num').textContent === '#12' && poolTile(11).querySelector('.num').textContent === '#11', poolTile(12).querySelector('.num').textContent);
check('a photo in the row says its place, then its own number', rowTile(11).querySelector('.pos').textContent === '3 \u00b7 #11' && rowTile(1).querySelector('.pos').textContent === '1 \u00b7 #1', rowTile(11).querySelector('.pos').textContent);
check('the heading is the shoot and the piece', text('title') === 'Fake beach reel', text('title'));
check('the count line', text('count') === '5 photos' && text('advice') === '8 to 14 works best', text('count') + ' / ' + text('advice'));
check('status reads Saved on opening', text('status') === 'Saved', text('status'));
check('the final button is on, Back to my pick is hidden', !byId('happy').disabled && byId('back').hidden);
check('the post kit link is set from the kit name', byId('kitlink').href === '/content/A%20kit/Post%20kit.html' && !byId('kitlink').hidden, byId('kitlink').href);
check('each tile asks for its small copy by number only', rowTile(6).querySelector('img').getAttribute('src') === '/kit-photo?kit=A%20kit&n=6&size=s&v=v6', rowTile(6).querySelector('img').getAttribute('src'));

// the X
layout(10);
clickButton(rowTile(16).querySelector('.x'));
check('X takes a photo out and the row closes up', eq(rowNums(), [1, 6, 11, 21]), rowNums());
check('status reads Saving... until it is sent', text('status') === 'Saving...', text('status'));
settle();
check('the change is sent with the counter the page was last told, and the page\u2019s own name', lastPost() && lastPost().base === 0 && /^[a-z0-9]{6,40}$/.test(lastPost().page) && lastPost().rev === undefined && eq(lastPost().nums, [1, 6, 11, 21]) && lastPost().done === false && lastPost().stamp === 'aaa', JSON.stringify(lastPost()));
check('status reads Saved once it landed', text('status') === 'Saved', text('status'));
check('Back to my pick appears once the row differs', !byId('back').hidden);

// the bar under a photo
layout(10);
var mk = rowTile(6).querySelector('.mk');
clickButton(mk); check('one press of the bar: Longer', mk.textContent === 'Longer', mk.textContent);
clickButton(mk); check('two presses: Quicker', mk.textContent === 'Quicker', mk.textContent);
settle();
check('the mark is saved beside its photo', eq(lastPost().marks, ['', '-', '', '']), JSON.stringify(lastPost().marks));
check('the next save carries the counter the Assistant answered with', lastPost().base === 1 && SERVER.st.rev === 2, JSON.stringify(lastPost()));
clickButton(mk); clickButton(mk); settle();
check('three presses is Normal again; the fourth is Longer', mk.textContent === 'Longer' && eq(lastPost().marks, ['', '+', '', '']), mk.textContent);

// drag from below into the row, between the 3rd and 4th
layout(10);
var before = rowNums();                       // [1, 6, 11, 21]
var t30 = poolTile(30);
var c = centre(t30); press(t30, c[0], c[1]);
check('a press alone lifts nothing', lifted() === 0);
move(c[0] + 3, c[1] + 3);
check('under 7 px of travel lifts nothing', lifted() === 0);
move(c[0] + 12, c[1] + 12);
check('past 7 px a copy is lifted and the tile dims', lifted() === 1 && t30.classList.contains('dragging') && document.body.classList.contains('arr-dragging'));
var third = rowTile(11), fourth = rowTile(21);
move(fourth.rect.left - 4, 100);              // in the gap between the 3rd and the 4th
var ins = rowEl.querySelector('.ins');
check('the bar shows in that gap', ins.classList.contains('on') && Math.abs(parseFloat(ins.style.left) - (fourth.rect.left - rowEl.rect.left - 7)) < 0.01, ins.style.left);
release(fourth.rect.left - 4, 100);
check('dropped between the 3rd and 4th, the rest shift along', eq(rowNums(), [1, 6, 11, 30, 21]), rowNums());
check('it comes in as Normal', rowTile(30).querySelector('.mk').textContent === 'Normal');
check('the lifted copy is gone and the bar is hidden', lifted() === 0 && !ins.classList.contains('on') && !t30.classList.contains('dragging') && !document.body.classList.contains('arr-dragging'));
settle();
check('the new order is saved', eq(lastPost().nums, [1, 6, 11, 30, 21]) && text('status') === 'Saved', JSON.stringify(lastPost().nums));

// reorder inside the row
layout(10);
dragTo(rowTile(21), rowTile(1).rect.left + 5, 100);       // the last one to the very front
release(rowTile(1).rect.left + 5, 100);
check('a row photo dragged to the front moves there', eq(rowNums(), [21, 1, 6, 11, 30]), rowNums());
check('and every place on the row is counted again', rowTile(21).querySelector('.pos').textContent === '1 \u00b7 #21' && rowTile(30).querySelector('.pos').textContent === '5 \u00b7 #30' && poolTile(21).querySelector('.pos').textContent === '1', rowTile(21).querySelector('.pos').textContent);
layout(10);
dragTo(rowTile(21), 790, 100);                             // past the end of the line
release(790, 100);
check('dragged past the last photo it goes to the end', eq(rowNums(), [1, 6, 11, 30, 21]), rowNums());
check('a moved photo keeps its mark', rowTile(6).querySelector('.mk').textContent === 'Longer');
layout(10);
var was = rowNums();
dragTo(rowTile(11), rowTile(11).rect.left + 10, 100);      // onto itself
check('over its own place no bar shows', !rowEl.querySelector('.ins').classList.contains('on'));
release(rowTile(11).rect.left + 10, 100);
check('dropped where it already is: nothing changes', eq(rowNums(), was), rowNums());

// a row of two lines: the end of line one, and the start of line two
settle(); layout(3, 360);                                    // 5 photos: 3 on line one, 2 on line two, both in sight
dragTo(poolTile(2), 700, 100);                               // right of the 3rd photo, on line one
var ins2 = rowEl.querySelector('.ins');
check('at the end of a line the bar is drawn on that line', ins2.classList.contains('on') && parseFloat(ins2.style.top) === rowTile(11).rect.top - rowEl.rect.top && parseFloat(ins2.style.left) > rowTile(11).rect.right - rowEl.rect.left, ins2.style.left + ',' + ins2.style.top);
release(700, 100);
check('and the photo lands 4th, before line two', eq(rowNums(), [1, 6, 11, 2, 30, 21]), rowNums());
layout(3, 360);
dragTo(poolTile(3), 30, 300);                                // line two, left of its first photo's middle
release(30, 300);
check('dropped at the start of line two', eq(rowNums(), [1, 6, 11, 3, 2, 30, 21]), rowNums());

// a dimmed photo below moves its place in the row
settle(); layout(10);
dragTo(poolTile(21), rowTile(1).rect.left + 5, 100);
release(rowTile(1).rect.left + 5, 100);
check('a dimmed photo below, dragged up, moves its place in the row', eq(rowNums(), [21, 1, 6, 11, 3, 2, 30]), rowNums());

// row to the photos below: take out
settle(); layout(10);
dragTo(rowTile(3), 400, 900);
check('over the photos below: the outline and the words', poolSec.classList.contains('out') && document.body.querySelector('.arr-lift').querySelector('.say').textContent === 'Drop here to take it out');
release(400, 900);
check('dropped below, it leaves and the row closes up', eq(rowNums(), [21, 1, 6, 11, 2, 30]) && !poolSec.classList.contains('out'), rowNums());
layout(10);
was = rowNums();
dragTo(poolTile(9), 400, 900); release(400, 900);
check('a photo from below dropped below: nothing changes', eq(rowNums(), was));
dragTo(rowTile(2), 900, 100); release(900, 100);
check('dropped outside both: nothing changes', eq(rowNums(), was));
// only the row's own box takes a drop: the heading above it and the lines below it do not
layout(10); was = rowNums();
dragTo(poolTile(9), 400, 300);                               // on the lines under the row box (the box ends at 230)
check('over the lines under the row there is no bar', !rowEl.querySelector('.ins').classList.contains('on'));
release(400, 300);
check('and a photo dropped there is not added', eq(rowNums(), was), rowNums());
dragTo(poolTile(9), 400, 20); release(400, 20);              // on the heading above the row box
check('nor one dropped on the heading above the row', eq(rowNums(), was), rowNums());
layout(3);                                                   // two lines, the second out of sight below the box
dragTo(poolTile(9), 30, 300);                                // where line two would be if it were not clipped
check('no landing place is set in a line that is out of sight', !rowEl.querySelector('.ins').classList.contains('on'));
release(30, 300);
check('so nothing lands where no bar was showing', eq(rowNums(), was), rowNums());
layout(10); box(poolSec, 0, 200, 800, 3000);                 // the page scrolled: the photos below pass under the panel
dragTo(rowTile(2), 400, 300);
check('a row photo held over the lines under the row is not about to be taken out', !poolSec.classList.contains('out'));
release(400, 300);
check('and dropping it there changes nothing', eq(rowNums(), was), rowNums());
layout(10);
// the bar of buttons at the bottom of the window floats over the photos below: a drop on it does nothing
dragTo(rowTile(2), 400, 1050);
check('a row photo held over the bar of buttons at the bottom is not about to be taken out', !poolSec.classList.contains('out') && document.body.querySelector('.arr-lift').querySelector('.say').textContent === '');
release(400, 1050);
check('and dropping it on that bar changes nothing', eq(rowNums(), was) && lifted() === 0, rowNums());
dragTo(rowTile(2), 400, 1050); move(400, 990);               // off the bar again, back over the photos below
check('just above that bar it is the photos below again', poolSec.classList.contains('out'));
fire(document, 'keydown', {key: 'Escape'});
box(dock, 0, 150, 800, 100);                                 // a very short window: the bar lies over the row itself
dragTo(poolTile(9), 400, 200);
check('where the bar of buttons covers the row, no landing place is set', !rowEl.querySelector('.ins').classList.contains('on'));
release(400, 200);
check('so nothing lands under it', eq(rowNums(), was), rowNums());
layout(10);

// every way of cancelling
settle(); layout(10); was = rowNums();
dragTo(rowTile(1), 400, 900);
fire(document, 'keydown', {key: 'Escape'});
check('Escape mid-drag: nothing changed, nothing left lifted', eq(rowNums(), was) && lifted() === 0 && !poolSec.classList.contains('out') && !rowTile(1).classList.contains('dragging'));
release(400, 900);
check('the release after Escape does nothing either', eq(rowNums(), was));
dragTo(rowTile(1), 400, 900); fire(document, 'pointercancel', {pointerId: PID});
check('the pointer being cancelled: nothing changed', eq(rowNums(), was) && lifted() === 0);
dragTo(rowTile(1), 400, 900); fireWindow('blur');
check('the window losing focus: nothing changed', eq(rowNums(), was) && lifted() === 0);
dragTo(rowTile(1), 400, 900); move(410, 900, {buttons: 0});
check('a mouse move with no button held: nothing changed', eq(rowNums(), was) && lifted() === 0);
var cc = centre(rowTile(1)); press(rowTile(1), cc[0], cc[1]); move(cc[0] + 20, cc[1]);
press(rowTile(6), 0, 0, {pointerId: 2, isPrimary: false}); move(400, 900, {pointerId: 2});
check('a second pointer is ignored', lifted() === 1 && rowTile(1).classList.contains('dragging') && !poolSec.classList.contains('out'));
release(400, 900, {pointerId: 2});
check('and its release does not end the drag', lifted() === 1);
fire(document, 'keydown', {key: 'Escape'});
press(rowTile(1), cc[0], cc[1], {button: 2}); move(cc[0] + 30, cc[1]);
check('the other mouse button never starts a drag', lifted() === 0);
release(cc[0] + 30, cc[1]);
settle();
var nPosts = SERVER.posts.length;

// a press that starts on a button inside a tile belongs to the button
layout(10); was = rowNums();
var xb = rowTile(6).querySelector('.x');
var ev = press(xb, 60, 60); move(200, 200); move(400, 900);
check('a press on the X never starts a drag', lifted() === 0 && !ev.defaultPrevented);
release(400, 900);
check('and never opens the big view', !byId('big').classList.contains('on'));
clickButton(xb);
check('the X still takes the photo out', eq(rowNums(), was.filter(function(n){ return n !== 6; })), rowNums());
settle();

// a click on the X straight after a drag still counts, even when the page's timers run late
// (found in the Claude app's pane on Nov 5: a page that is not in front has its timers slowed, and the
// "just dragged" moment outlived the drag, so the next click on an X or a Normal bar was lost)
layout(10); was = rowNums();
var dt = rowTile(was[0]); cc = centre(dt);
dragTo(dt, cc[0] + 3, cc[1] + 2); release(cc[0] + 3, cc[1] + 2);     // a real drag and drop; no timer has run since
layout(10); was = rowNums();
var mkb = rowTile(was[1]).querySelector('.mk'), mkWas = mkb.textContent;
press(mkb, 60, 60); release(60, 60); clickButton(mkb);
var mkNow = rowTile(was[1]).querySelector('.mk').textContent;
check('a click on a button straight after a drag is not lost, even before any timer has run', mkNow !== mkWas && eq(rowNums(), was), mkWas + ' -> ' + mkNow);
// put the bar back where it was (three steps go round), so the checks below start from the same reel
for (var back = 0; back < 3 && rowTile(was[1]).querySelector('.mk').textContent !== mkWas; back++) clickButton(rowTile(was[1]).querySelector('.mk'));
settle();

// a click opens the photo big, and the buttons there do what a drag does
layout(10);
cc = centre(rowTile(11)); press(rowTile(11), cc[0], cc[1]); release(cc[0], cc[1]);
var big = byId('big');
check('a click opens the photo big', big.classList.contains('on') && lifted() === 0);
check('it says where the photo is', big.querySelector('.where').textContent === 'Number 3 of 5 in your reel.', big.querySelector('.where').textContent);
check('the sharp copy replaces the small one', big.querySelector('img').getAttribute('src') === '/kit-photo?kit=A%20kit&n=11&size=l&v=v11', big.querySelector('img').getAttribute('src'));
function bigButton(label){ return big.querySelectorAll('button').filter(function(b){ return b.textContent === label; })[0]; }
clickButton(bigButton('Move it earlier'));
check('Move it earlier', eq(rowNums(), [21, 11, 1, 2, 30]) && big.querySelector('.where').textContent === 'Number 2 of 5 in your reel.', rowNums());
clickButton(bigButton('Move it later')); clickButton(bigButton('Move it later'));
check('Move it later, twice', eq(rowNums(), [21, 1, 2, 11, 30]), rowNums());
clickButton(bigButton('Quicker'));
check('Quicker from the big view', rowTile(11).querySelector('.mk').textContent === 'Quicker' && bigButton('Quicker').classList.contains('cur'));
clickButton(bigButton('Take it out'));
check('Take it out', eq(rowNums(), [21, 1, 2, 30]) && big.querySelector('.where').textContent === 'Not in your reel.', rowNums());
clickButton(bigButton('Add it to the end'));
check('Add it to the end', eq(rowNums(), [21, 1, 2, 30, 11]) && big.querySelector('.where').textContent === 'Number 5 of 5 in your reel.', rowNums());
fire(document, 'keydown', {key: 'ArrowRight'});
check('the arrow key walks on: after the row, the rest by number', big.querySelector('img').getAttribute('src').indexOf('n=3&') > 0, big.querySelector('img').getAttribute('src'));
fire(document, 'keydown', {key: 'ArrowLeft'}); fire(document, 'keydown', {key: 'ArrowLeft'});
check('and back along the row', big.querySelector('img').getAttribute('src').indexOf('n=30&') > 0, big.querySelector('img').getAttribute('src'));
fire(document, 'keydown', {key: 'Escape'});
check('Escape closes the big view', !big.classList.contains('on'));
settle();
check('everything done in the big view was saved', eq(SERVER.st.now.nums, [21, 1, 2, 30, 11]) && eq(SERVER.st.now.marks, ['', '', '', '', '']) && text('status') === 'Saved', JSON.stringify(SERVER.st.now));
check('a photo taken out and added again comes back as Normal', rowTile(11).querySelector('.mk').textContent === 'Normal');

// a finger: on the photos below it scrolls the page and a tap opens the photo; on the row it drags
layout(10);
var tp = poolTile(12), tev = press(tp, 50, 500, {pointerType: 'touch'});
move(50, 460, {pointerType: 'touch'});
check('a finger moving on the photos below is left to scroll the page', !tev.defaultPrevented && lifted() === 0);
release(50, 460, {pointerType: 'touch'});
check('and that is not a tap', !big.classList.contains('on'));
press(tp, 50, 500, {pointerType: 'touch'}); release(50, 500, {pointerType: 'touch'});
check('a tap on a photo below opens it big', big.classList.contains('on') && big.querySelector('.where').textContent === 'Not in your reel.');
fire(big, 'click', {});
check('a click on the dark area closes it', !big.classList.contains('on'));
cc = centre(rowTile(1)); tev = press(rowTile(1), cc[0], cc[1], {pointerType: 'touch'}); move(cc[0] + 20, cc[1], {pointerType: 'touch'});
check('a finger on a row photo drags it', tev.defaultPrevented && lifted() === 1);
fire(document, 'pointercancel', {pointerId: PID});

// the row scrolling inside its panel while a photo is held near its top or bottom
layout(10); wrap.scrollHeight = 600; wrap.clientHeight = 190; wrap.scrollTop = 0;
dragTo(poolTile(13), 400, 300);                              // on its way up: over the lines under the row box
runFrame(); wait(400); runFrame(); runFrame();
check('carried over the lines under the row, however slowly: the row does not scroll', wrap.scrollTop === 0, wrap.scrollTop);
move(400, 215);                                              // inside the row box, 15 px above its bottom edge
runFrame(); wait(100); runFrame();
check('passing through the bottom edge of the row: it does not scroll yet', wrap.scrollTop === 0, wrap.scrollTop);
wait(200); runFrame(); runFrame();
check('resting there a quarter of a second: the row scrolls 12 px a frame', wrap.scrollTop === 24, wrap.scrollTop);
move(400, 50); runFrame();
check('moved to the top edge: it waits again', wrap.scrollTop === 24, wrap.scrollTop);
wait(260); runFrame();
check('held near the top, it scrolls back', wrap.scrollTop === 12, wrap.scrollTop);
move(400, 130); wait(400); runFrame();
check('held in the middle, it stays', wrap.scrollTop === 12, wrap.scrollTop);
move(400, 20); wait(400); runFrame(); runFrame();
check('held over the heading above the row, it stays', wrap.scrollTop === 12, wrap.scrollTop);
move(400, 900); wait(400); runFrame();
check('held over the photos below, it stays', wrap.scrollTop === 12, wrap.scrollTop);
fire(document, 'keydown', {key: 'Escape'}); runFrame(); runFrame();
check('after the drag ends nothing keeps scrolling', wrap.scrollTop === 12 && _frames.length === 0);
wrap.scrollHeight = 0; wrap.clientHeight = 0; wrap.scrollTop = 0;
settle();

// the Assistant not answering: the page keeps trying, and says so
SERVER.mode = 'down'; layout(10);
clickButton(rowTile(2).querySelector('.x'));
runTimers();
check('no answer: the status says so', text('status') === 'Not saved yet. Trying again...', text('status'));
runTimers(); runTimers();
check('still trying, still true', text('status') === 'Not saved yet. Trying again...' && !eq(SERVER.st.now.nums, rowNums()));
SERVER.mode = 'up'; runTimers(); settle();
check('when the Assistant is back the change lands', text('status') === 'Saved' && eq(SERVER.st.now.nums, [21, 1, 30, 11]), JSON.stringify(SERVER.st.now.nums));
// an answer lost on the way back: the change is on disk; the next try must not be mistaken for a clash
SERVER.mode = 'lost'; layout(10);
clickButton(rowTile(30).querySelector('.mk')); runTimers();
check('an answer lost on the way back reads as not saved', text('status') === 'Not saved yet. Trying again...');
clickButton(rowTile(30).querySelector('.mk'));           // and they keep going meanwhile
settle();
check('the retry carries the newest state and is accepted', text('status') === 'Saved' && eq(SERVER.st.now.marks, ['', '', '-', '']) && byId('note').hidden, JSON.stringify(SERVER.st.now.marks) + ' note:' + text('note'));

// Back to my pick
clickButton(byId('back')); settle();
check('Back to my pick puts the first order and marks back, and saves', eq(rowNums(), [1, 6, 11, 16, 21]) && eq(SERVER.st.now.nums, [1, 6, 11, 16, 21]) && eq(SERVER.st.now.marks, ['', '', '', '', '']) && byId('back').hidden, rowNums());

// the final button
layout(10);
clickButton(rowTile(16).querySelector('.x'));                 // an unsaved change is waiting when they press it
check('before the button is pressed there is no line under it', text('doneline') === '');
clickButton(byId('happy'));
check('the final button sends the unsaved change and done together', lastPost().done === true && eq(lastPost().nums, [1, 6, 11, 21]), JSON.stringify(lastPost()));
settle();
check('only then does the line under the button appear', text('doneline').indexOf('Go back to the chat and say') > 0 && text('doneline').indexOf('which song') > 0 && text('status') === 'Saved', text('doneline'));
check('the Assistant recorded it', SERVER.st.happy && SERVER.st.happy.rev === SERVER.st.rev);
check('the reel\u2019s line has no folder button and no Canva line beside it (those are the carousel\u2019s)', byId('openfolder').hidden && byId('canvaline').hidden && SERVER.opens.length === 0);
check('the reel\u2019s line has no Lay out the slides link (that is the carousel\u2019s)', byId('layout').hidden);
clickButton(rowTile(21).querySelector('.mk')); settle();
check('a change afterwards: the line says so', text('doneline') === 'You’ve changed it since. Press the button again when it’s right.', text('doneline'));
clickButton(byId('happy')); settle();
check('pressed again: the saved line is back', text('doneline').indexOf('Go back to the chat') > 0);
SERVER.mode = 'down'; clickButton(rowTile(21).querySelector('.mk')); clickButton(byId('happy')); runTimers();
check('pressed while the Assistant is not answering: no line yet, and it says not saved', text('doneline') === '' && text('status') === 'Not saved yet. Trying again...', text('doneline'));
SERVER.mode = 'up'; settle();
check('and the line appears once it has really landed', text('doneline').indexOf('Go back to the chat') > 0 && lastPost().done === true);

// under two photos the button is off, with the reason beside it
layout(10);
[1, 6, 11].forEach(function(n){ clickButton(rowTile(n).querySelector('.x')); });
check('with one photo the final button is off and says why', byId('happy').disabled && text('why') === 'A reel needs at least 2 photos.', text('why'));
clickButton(rowTile(21).querySelector('.x'));
check('an empty row says how to fill it', rowEl.textContent.indexOf('Nothing picked yet. Drag photos up from below.') >= 0);
settle();
layout(10);
dragTo(poolTile(4), 100, 100); release(100, 100);
dragTo(poolTile(5), 700, 100); release(700, 100);
check('photos dragged into an empty row', eq(rowNums(), [4, 5]) && !byId('happy').disabled && rowEl.textContent.indexOf('Nothing picked yet') < 0, rowNums());
settle();

// a full row refuses, with a line under the row
SERVER.st.limits.max = 3; SERVER.st.rev += 1; SERVER.st.now = {nums: [4, 5, 6], marks: ['', '', '']}; SERVER.from = null;
clickButton(rowTile(4).querySelector('.mk')); settle();     // this save meets an order the page has not seen
check('changed somewhere else: the newest is shown, with a line saying so', eq(rowNums(), [4, 5, 6]) && text('note') === 'This order was changed somewhere else. Here’s the newest.' && !byId('note').hidden && byId('note').querySelectorAll('button').length === 0, rowNums() + ' / ' + text('note'));
layout(10);
dragTo(poolTile(9), 100, 100);
check('a full row shows no bar', !rowEl.querySelector('.ins').classList.contains('on'));
release(100, 100);
check('a full row refuses with a line under the row', eq(rowNums(), [4, 5, 6]) && text('rowline') === 'A reel holds up to 60 photos. Take one out first.', text('rowline'));
dragTo(rowTile(6), rowTile(4).rect.left + 2, 100); release(rowTile(4).rect.left + 2, 100);
check('a full row can still be reordered', eq(rowNums(), [6, 4, 5]), rowNums());
check('the line about the newer order goes with their next change', byId('note').hidden && text('note') === '', text('note'));
settle();
check('and that change is saved from the counter the newer order came with', text('status') === 'Saved' && eq(SERVER.st.now.nums, [6, 4, 5]), JSON.stringify(SERVER.st.now.nums));

// a refusal that trying again will not fix
SERVER.mode = 'refuse';
clickButton(rowTile(4).querySelector('.mk')); settle();
var tries = SERVER.posts.length; settle();
var rnote = byId('note');
check('a refusal: the words, with a Reload button beside them', !rnote.hidden && rnote.textContent.indexOf('That didn\u2019t arrive the way it should have. Reload the page and try again.') === 0 && rnote.querySelectorAll('button').length === 1 && rnote.querySelector('button').textContent === 'Reload', rnote.textContent);
check('and it is not sent again and again, and the status does not say Saved', SERVER.posts.length === tries && text('status') === '', text('status'));
SERVER.mode = 'up';
clickButton(rowTile(4).querySelector('.mk')); settle();
check('the next change saves as usual, and the line goes', text('status') === 'Saved' && byId('note').hidden);

// the shoot's drive unplugged while the page is open: keep trying, and land by itself when it is back
SERVER.mode = 'unplugged';
clickButton(rowTile(4).querySelector('.mk')); settle();
check('the drive unplugged: the status asks about the drive', text('status') === 'I can\u2019t find that shoot\u2019s posts. Is the drive plugged in?', text('status'));
tries = SERVER.posts.length; runTimers(); runTimers();
check('and the page keeps trying', SERVER.posts.length === tries + 2, SERVER.posts.length - tries);
var want = rowTile(4).querySelector('.mk').textContent;
SERVER.mode = 'up'; settle();
check('when the drive is back the change lands by itself', text('status') === 'Saved' && SERVER.st.now.marks[SERVER.st.now.nums.indexOf(4)] === (want === 'Longer' ? '+' : want === 'Quicker' ? '-' : ''), JSON.stringify(SERVER.st.now));

// the page sitting open follows a newer order by itself (a fresh pick made in the chat)
SERVER.st.limits.max = 60;
SERVER.st.rev += 1; SERVER.st.now = {nums: [7, 8, 9], marks: ['', '', '+']}; SERVER.st.first = copy(SERVER.st.now); SERVER.from = null;
var g = SERVER.gets; runIntervals();
check('a fresh pick made in the chat shows up by itself', SERVER.gets === g + 1 && eq(rowNums(), [7, 8, 9]) && rowTile(9).querySelector('.mk').textContent === 'Longer' && text('status') === 'Saved' && byId('back').hidden, rowNums());
check('with no line about it (nothing of theirs was replaced)', byId('note').hidden);
g = SERVER.gets; runIntervals();
check('asking again changes nothing', SERVER.gets === g + 1 && eq(rowNums(), [7, 8, 9]));
layout(10);
clickButton(rowTile(8).querySelector('.x'));                  // a change of their own, not sent yet
SERVER.st.rev += 1; SERVER.st.now = {nums: [1, 2], marks: ['', '']}; SERVER.from = null;
g = SERVER.gets; runIntervals();
check('with a change of their own not yet saved, the page does not ask and is not replaced', SERVER.gets === g && eq(rowNums(), [7, 9]), rowNums());
settle();
check('that change then meets the newer order, and the line says so', eq(rowNums(), [1, 2]) && text('note') === 'This order was changed somewhere else. Here’s the newest.', rowNums() + ' / ' + text('note'));
layout(10);
dragTo(rowTile(1), 400, 900);
SERVER.st.rev += 1; SERVER.st.now = {nums: [3, 4, 5], marks: ['', '', '']}; SERVER.from = null;
g = SERVER.gets; runIntervals();
check('while a photo is held the page does not ask', SERVER.gets === g && eq(rowNums(), [1, 2]) && lifted() === 1);
fire(document, 'keydown', {key: 'Escape'}); runIntervals();
check('once it is let go the newer order arrives', eq(rowNums(), [3, 4, 5]), rowNums());
document.hidden = true; SERVER.st.rev += 1; SERVER.st.now = {nums: [5, 4, 3], marks: ['', '', '']}; g = SERVER.gets; runIntervals();
check('a page that is not in sight does not ask', SERVER.gets === g);
document.hidden = false; runIntervals();
check('and catches up when it is', eq(rowNums(), [5, 4, 3]), rowNums());
// the line under the final button is there only while the order is waiting for Claude
clickButton(byId('happy')); settle();
check('the final button: the line under it', text('doneline').indexOf('Go back to the chat') > 0, text('doneline'));
SERVER.st.happy = null; runIntervals();
check('once Claude has taken the order the line goes', text('doneline') === '', text('doneline'));
layout(10);

// the photos changing under the page
SERVER.mode = 'photos';
clickButton(rowTile(5).querySelector('.mk')); settle();
var note = byId('note');
check('photos changed: the line and a Reload button beside it', !note.hidden && note.textContent.indexOf('The photos in this shoot changed since this page opened.') === 0 && note.querySelectorAll('button').length === 1 && note.querySelector('button').textContent === 'Reload', note.textContent);
check('nothing more is saved, and the final button is off', byId('happy').disabled);
tries = SERVER.posts.length;
clickButton(rowTile(5).querySelector('.x')); settle();
check('a change after that is not drawn or sent', SERVER.posts.length === tries && rowNums().length === 3);
check('the page never reloads itself', location.reloaded === 0);
clickButton(note.querySelector('button'));
check('Reload reloads', location.reloaded === 1);
}

JSON.stringify(RESULTS);
"""


def page_elements(page):
    """Every element of the real page that has an id, with its tag, classes, and whether it starts hidden or off."""
    out = []
    for tag, attrs in re.findall(r"<(\w+)((?:\s+[\w-]+(?:='[^']*')?)*)\s*>", page):
        m = re.search(r"\bid='([\w-]+)'", attrs)
        if m:
            c = re.search(r"\bclass='([^']*)'", attrs)
            out.append({"id": m.group(1), "tag": tag, "cls": c.group(1) if c else "",
                        "hidden": bool(re.search(r"\shidden\b", attrs)), "disabled": bool(re.search(r"\sdisabled\b", attrs))})
    return out


def osascript(js_file):
    return subprocess.run(["osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


def check_scripts(work):
    sys.path.insert(0, str(SCRIPTS))
    import arrange_page as ap
    page = ap.page_html("A kit", "reel")
    car_page = ap.page_html("A kit", "carousel")
    plain = ap.plain_page("I can't find that shoot's posts. Is the drive plugged in?")

    # nothing from the internet, nothing the pane cannot do, nothing kept in the browser
    for label, text in (("the picker page", page), ("the carousel's picker page", car_page), ("the plain page", plain)):
        case(f"{label}: no address on the internet anywhere in it", not re.search(r"https?://", text))
        case(f"{label}: no link, font or script from another address", "<link" not in text and not re.search(r"<script[^>]*\ssrc=", text) and "@import" not in text and "<img src" not in text and "<iframe" not in text)
    for word in ('draggable="true"', "draggable='true'", "localStorage", "sessionStorage", "indexedDB", "navigator.clipboard", "ondragstart", "dataTransfer"):
        case(f"the picker page: no {word}", word not in page and word not in car_page)
    case("the carousel's page: only the kit's folder name and the piece are put into it", "data-kit='A kit'" in car_page and "data-piece='carousel'" in car_page)
    untitled = lambda t: re.sub(r"<title>.*?</title>", "", t, count=1)      # noqa: E731
    case("the two pages are the same page but for the piece and the title", untitled(car_page).replace("data-piece='carousel'", "data-piece='reel'") == untitled(page) and car_page != page)
    # the on-screen rule: the folder's button is on the same line as the words about the folder, and its
    # answer is the very next thing under them
    beside = bool(re.search(r"<div class='donerow'><p class='doneline' id='doneline'></p><button class='btn' id='openfolder' type='button' hidden>Open the Carousel folder</button><a class='btn' id='layout' title='[^'<>]+' hidden>Lay out the slides</a></div><p class='openline' id='openline'></p>", car_page))
    case("the carousel's page: Open the Carousel folder sits on the result's own line, its answer directly under", beside)
    lay = re.search(r"<a ([^>]*)>Lay out the slides</a>", car_page)
    case("the carousel's page: 'Lay out the slides' is a plain link on that same line, hidden until the slides are made, with no address written into the page",
         beside and bool(lay) and "id='layout'" in lay.group(1) and " hidden" in lay.group(1) and "href" not in lay.group(1) and "draggable" not in lay.group(1))
    case("the styles: a link that looks like a button is not underlined", "a.btn{text-decoration:none}" in ap.CSS)
    case("the picker page: only the kit's folder name and the piece are put into it", "data-kit='A kit'" in page and "data-piece='reel'" in page)
    case("a kit name is html-escaped on its way into the page", "data-kit='&lt;b&gt; &amp; &#x27;x&#x27;'" in ap.page_html("<b> & 'x'", "reel"))
    case("the plain page has the Back to home button and the words", "href='/home'" in plain and "Back to home" in plain and "I can&#x27;t find that shoot&#x27;s posts." in plain)
    case("the styles carry no backslash", "\\" not in ap.CSS)
    # the look (Nov 6): the system's own font, a PC's as well as a Mac's; no web font; light only
    case("the styles name the system font for a Mac and for a PC, and no web font",
         '-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif' in ap.CSS
         and not re.search(r"Fraunces|DM Sans|Iowan|Palatino|Georgia|serif|googleapis|gstatic", ap.CSS.replace("sans-serif", "")))
    case("the styles are light only (no dark version switches itself on)", "prefers-color-scheme" not in ap.CSS and "data-theme" not in ap.CSS and "color-scheme" not in ap.CSS)
    # one whole line of the row always fits the row's own box, so the Normal / Longer / Quicker bar on the
    # first line is never cut off: a row photo is never taller than --rh, the box never shorter than that
    # plus its padding, and the panel itself never scrolls (the row's box is the only scroller in it)
    panel_rule = re.search(r"\n\.panel\{([^}]*)\}", ap.CSS)
    case("the styles: a row photo is never taller than the row's own box, and the panel is not a second scroller",
         ".rt .ph{position:relative;width:100%;aspect-ratio:2/3;max-height:var(--rh);" in ap.CSS
         and ".rowwrap{min-height:calc(var(--rh) + 12px);max-height:max(calc(var(--rh) + 12px)," in ap.CSS
         and bool(panel_rule) and "position:sticky" in panel_rule.group(1)
         and "overflow" not in panel_rule.group(1) and "max-height" not in panel_rule.group(1))
    # the bar of buttons is drawn at the bottom of the window but comes before the photos below in the page,
    # so the Tab key reaches the buttons first; every line a press brings is inside that bar
    dock = re.search(r"<div class='dock' id='dock'>(.*?)<section class='poolsec'", page, re.S)
    case("the picker page: the bar of buttons comes before the photos below in the page, and after the row",
         bool(dock) and page.index("id='rowwrap'") < page.index("id='dock'") < page.index("id='pool'"))
    case("the picker page: both buttons, and every line a press brings, are inside that bar",
         bool(dock) and all(f"id='{i}'" in dock.group(1) for i in ("back", "happy", "why", "status", "doneline", "openfolder", "layout", "openline", "canvaline", "note")))
    case("the picker page: the row's own lines stay in the row's panel",
         bool(re.search(r"<section class='panel' id='panel'>(?:(?!</section>).)*id='rowwrap'(?:(?!</section>).)*id='rowline'(?:(?!</section>).)*id='legend'(?:(?!</section>).)*</section>", page, re.S)))
    case("the styles fetch nothing (no url(...), no @font-face)", "url(" not in ap.CSS and "@font-face" not in ap.CSS)

    # each script parses under the Mac's own JavaScript engine
    probe = work / "parse-probe.js"
    for name in ("MODEL_JS", "DRAG_JS", "PICKER_JS"):
        probe.write_text("var SRC = " + json.dumps(getattr(ap, name)) + ";\nvar out; try { new Function(SRC); out = 'parses'; } catch (e) { out = 'SYNTAX ERROR: ' + e; }\nout;\n", encoding="utf-8")
        r = osascript(probe)
        case(f"{name} parses under osascript -l JavaScript", r.returncode == 0 and r.stdout.strip() == "parses", r.stdout.strip() or r.stderr.strip())
    probe.write_text("var SRC = 'var x = ;';\nvar out; try { new Function(SRC); out = 'parses'; } catch (e) { out = 'SYNTAX ERROR: ' + e; }\nout;\n", encoding="utf-8")
    r = osascript(probe)
    case("the parse check does catch a broken script", r.stdout.strip().startswith("SYNTAX ERROR"), r.stdout.strip())

    # the scripts run, on a pretend page, through each story
    els = page_elements(page)
    case("the pretend page is built from the real page's own elements", len(els) >= 20 and any(e["id"] == "happy" and e["tag"] == "button" and e["disabled"] for e in els), len(els))
    for scenario in ("main", "preparing", "gone", "down", "carousel", "carousel-resume", "carousel-made", "carousel-two", "carousel-same", "carousel-long"):
        f = work / f"page-{scenario}.js"
        piece = "carousel" if scenario.startswith("carousel") else "reel"
        head = "".join(f"var {k} = {json.dumps(v)};\n" for k, v in (("SCENARIO", scenario), ("PIECE_NAME", piece), ("DONE_ROW_HOLDS_BUTTON", beside),
                                                                   ("PAGE_ELS", page_elements(car_page) if piece == "carousel" else els),
                                                                   ("MODEL_SRC", ap.MODEL_JS), ("DRAG_SRC", ap.DRAG_JS), ("PICKER_SRC", ap.PICKER_JS)))
        f.write_text(head + PAGE_JS, encoding="utf-8")
        r = osascript(f)
        if r.returncode != 0:
            case(f"page scripts [{scenario}]: ran to the end", False, r.stderr.strip())
            continue
        try:
            got = json.loads(r.stdout)
        except ValueError:
            case(f"page scripts [{scenario}]: ran to the end", False, r.stdout[:300])
            continue
        case(f"page scripts [{scenario}]: ran to the end ({len(got)} checks)", len(got) > 0)
        for name, ok, detail in got:
            case(f"page [{scenario}]: {name}", ok, detail)


# ---------- the server ----------

class Server:
    def __init__(self, env, port):
        self.env, self.want, self.port, self.proc = env, port, None, None

    def start(self):
        if self.want in NEVER_PORTS or any(p in NEVER_PORTS for p in range(self.want, self.want + 20)):
            raise SystemExit("STOP: that port range reaches one the real pages use.")
        self.proc = subprocess.Popen([PY, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env)
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise SystemExit(f"STOP: the page server did not start ({line.strip()!r}).")
        self.port = int(m.group(1))
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                return self.port
            except OSError:
                time.sleep(0.1)
        raise SystemExit("STOP: the page server did not answer.")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


def ask(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()
    finally:
        c.close()


def raw(port, text):
    """Send bytes exactly as written (for a request with no length, or a nonsense one). The status line back."""
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        s.sendall(text.encode())
        s.settimeout(5)
        got = b""
        while b"\r\n" not in got:
            more = s.recv(4096)
            if not more:
                break
            got += more
        return got.split(b"\r\n")[0].decode(errors="replace")
    except socket.timeout:
        return "(no answer: the server hung)"
    finally:
        s.close()


def run(env, script, *args):
    r = subprocess.run([PY, str(script if isinstance(script, Path) else SCRIPTS / script), *args], capture_output=True, text=True, env=env, timeout=300)
    return r.returncode, (r.stdout + r.stderr).strip()


PAGE_SAVE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import arrange
kit = arrange.kit_by_name(sys.argv[2])
data, p = arrange.sync(kit, 'reel')
nums = json.loads(sys.argv[3])
body = {'kit': sys.argv[2], 'piece': 'reel', 'stamp': p['stamp'], 'base': p['now']['rev'], 'page': 'checkpage1',
        'nums': nums, 'marks': [''] * len(nums), 'done': False}
print(arrange.save_from_page(body)[0])
"""

# apply, stopped right after it has written the kit record, while a real save from the page is sent to the
# server. With the kit's arrangement held by apply, that save must wait, land afterwards, and still be waiting.
RACE = r"""
import json, sys, threading, time, http.client
sys.path.insert(0, sys.argv[1])
import arrange, kit as kit_mod
port, name, body = int(sys.argv[2]), sys.argv[3], sys.argv[4].encode()
kit = arrange.kit_by_name(name)
out = {'answered_while_apply_held_it': None, 'code': None}
def send():
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
    c.request('POST', '/arrange', body=body, headers={'Content-Type': 'application/json'})
    r = c.getresponse(); out['code'] = r.status; out['answer'] = json.loads(r.read()); c.close()
real = kit_mod.save_rec
def slow(k, rec):
    real(k, rec)
    out['kit_written'] = True
    t = threading.Thread(target=send); t.start(); out['t'] = t
    time.sleep(1.2)
    out['answered_while_apply_held_it'] = out['code'] is not None
kit_mod.save_rec = slow
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = arrange.apply_reel(kit)
out['apply'] = [code, buf.getvalue().strip()]
t = out.pop('t', None)
if t: t.join(20)
print(json.dumps(out))
"""


def jpeg_size(data):
    """(width, height) from a JPEG's own header, or None."""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7 or m == 0xFF:
            i += 2 if m != 0xFF else 1
            continue
        n = struct.unpack(">H", data[i + 2:i + 4])[0]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        if m == 0xDA:
            return None
        i += 2 + n
    return None


def folder_print(folder):
    """Every file in a folder with its hash: to prove a folder was not changed."""
    out = {}
    for p in sorted(Path(folder).iterdir()):
        if p.is_file():
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def check_server(work, port, photos):
    target = work / "fake"
    r = subprocess.run([PY, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", str(photos)], capture_output=True, text=True, timeout=600)
    if not case("the pretend kit was made (tests/fake_kit.py)", r.returncode == 0, (r.stdout + r.stderr)[-300:]):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    kit_name = "2026-11-01 Fake beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    photos_dir = kit / "Photos"
    arr = kit / ".kit" / "arrange.json"
    rec_file = kit / ".kit" / "kit.json"
    sheet = json.loads((kit / ".kit" / "sheet.json").read_text())["photos"]
    by_name = {Path(x["file"]).name: x for x in sheet}
    total = len(sheet)
    before = folder_print(photos_dir)
    rec_at_start = rec_file.read_bytes()
    rec = json.loads(rec_at_start)
    pick = rec["picks"]["reel"]

    case("the pretend kit: every photo is on the numbered list", total == photos, total)
    side = next((x for n, x in by_name.items() if "sideways" in n), None)
    case("the pretend kit: the photo stored sideways is listed tall", side is not None and side["way"] == "tall" and side["h"] > side["w"], side)
    code, out = run(env, "kit.py", "show", kit_name)
    case("kit.py show prints the kit", code == 0 and "Fake beach" in out and "Picks:" in out, out)
    code, out = run(env, "arrange.py", "show", "Fake beach")
    case("arrange.py show: the name, the count and a stamp", code == 0 and f"numbered list: {total}" in out and re.search(r"Stamp: [0-9a-f]{12}", out), out)

    # ---- stage 0: the copies ----
    code, out = run(env, "arrange.py", "previews", "Fake beach")
    case(f"previews: first run prints 'made {total}' and a time", code == 0 and re.search(rf"^made {total} in [\d.]+ s", out), out)
    t0 = time.time()
    code, out = run(env, "arrange.py", "previews", "Fake beach")
    case(f"previews: second run prints 'already there {total}' in under a second", code == 0 and out.startswith(f"already there {total}") and time.time() - t0 < 1.5, out)
    prev = kit / ".kit" / "previews"
    names = sorted(os.listdir(prev))
    case("previews: two copies of every photo, and no half-made file left", len([n for n in names if n.endswith(".jpg") and not n.startswith(".")]) == 2 * total and not [n for n in names if n.startswith(".")], len(names))
    small = by_name[next(n for n in by_name if "small" in n)]
    dims = [jpeg_size((prev / n).read_bytes()) for n in names if n.startswith(f"{small['n']:04d}-")]
    case("previews: a small photo's copies are its own size, not blown up", len(dims) == 2 and all(d == (small["w"], small["h"]) for d in dims), dims)
    for ext in (".heic", ".png", ".tif"):
        x = by_name[next(n for n in by_name if n.endswith(ext))]
        copies = [n for n in names if n.startswith(f"{x['n']:04d}-")]
        case(f"previews: the {ext} photo has two copies and both are JPEGs", len(copies) == 2 and all((prev / n).read_bytes()[:2] == b"\xff\xd8" for n in copies), copies)
    plain = next(x for x in sheet if x["n"] == 3)
    dims = sorted(max(jpeg_size((prev / n).read_bytes())) for n in names if n.startswith("0003-"))
    case("previews: an ordinary photo's copies are 520 and its own size or 1600 on the long edge", dims == [520, min(1600, max(plain["w"], plain["h"]))], dims)
    case("previews: nothing in the Photos folder was changed or added", folder_print(photos_dir) == before)

    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (page server on port {P}, STUDIO_HOME={studio})", flush=True)

        # ---- stage 0: the photo route ----
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n=3&size=s")
        case("photo route: one photo as a JPEG, 520 on its long edge", code == 200 and h.get("content-type") == "image/jpeg" and max(jpeg_size(data) or (0, 0)) == 520, (code, h.get("content-type"), jpeg_size(data)))
        case("photo route: it carries its length and may be kept a week", h.get("content-length") == str(len(data)) and h.get("cache-control") == "private, max-age=604800", h)
        code, h, big = ask(P, "GET", f"/kit-photo?kit={KQ}&n=3&size=l&v=anything")
        case("photo route: the larger copy, v ignored", code == 200 and max(jpeg_size(big) or (0, 0)) == min(1600, max(plain["w"], plain["h"])), (code, jpeg_size(big)))
        orig = (photos_dir / Path(plain["file"]).name).read_bytes()
        case("photo route: what is sent is a copy, never the photo itself", data != orig and big != orig)
        heic = by_name[next(n for n in by_name if n.endswith(".heic"))]
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n={heic['n']}&size=s")
        case("photo route: a HEIC photo arrives as a JPEG", code == 200 and data[:2] == b"\xff\xd8")
        refusals = [("kit=..", f"/kit-photo?kit=..&n=3&size=s"), ("kit=%2e%2e", f"/kit-photo?kit=%2e%2e&n=3&size=s"),
                    ("kit=<kit>/../x", f"/kit-photo?kit={KQ}/../x&n=3&size=s"), ("kit=%2FUsers", "/kit-photo?kit=%2FUsers&n=3&size=s"),
                    ("kit=.kit", "/kit-photo?kit=.kit&n=3&size=s"), ("kit=Your Content old", "/kit-photo?kit=Your%20Content%20old&n=3&size=s"),
                    ("kit=../Your Content old/Sneaky", "/kit-photo?kit=..%2FYour%20Content%20old%2FSneaky&n=3&size=s"),
                    ("kit empty", "/kit-photo?kit=&n=3&size=s"), ("the kit name in other capitals", f"/kit-photo?kit={quote(kit_name.upper())}&n=3&size=s"),
                    ("the kit's full path", f"/kit-photo?kit={quote(str(kit), safe='')}&n=3&size=s"),
                    ("n=0", f"/kit-photo?kit={KQ}&n=0&size=s"), ("n=-1", f"/kit-photo?kit={KQ}&n=-1&size=s"),
                    ("n=9999", f"/kit-photo?kit={KQ}&n=9999&size=s"), ("n=abc", f"/kit-photo?kit={KQ}&n=abc&size=s"),
                    ("n=3.0", f"/kit-photo?kit={KQ}&n=3.0&size=s"), ("a file name for n", f"/kit-photo?kit={KQ}&n=beach-003.jpg&size=s"),
                    ("size=xl", f"/kit-photo?kit={KQ}&n=3&size=xl"), ("size=xxx (x and xx are the designer's larger copies; tests/design_check.py has those)", f"/kit-photo?kit={KQ}&n=3&size=xxx"),
                    ("no size", f"/kit-photo?kit={KQ}&n=3"), ("no question at all", "/kit-photo")]
        for label, path in refusals:
            code, h, data = ask(P, "GET", path)
            case(f"photo route refuses: {label}", code == 404 and b"\xff\xd8" not in data[:4], code)
        os.symlink(str(kit), str(kit.parent / "A link to the kit"))
        code, h, data = ask(P, "GET", "/kit-photo?kit=A%20link%20to%20the%20kit&n=3&size=s")
        case("photo route refuses: a link to a kit, even inside Your Content", code == 404, code)
        os.unlink(str(kit.parent / "A link to the kit"))           # the link this check made a moment ago
        for path in ("/.kit/", "/previews/", f"/kit-photo/", "/arrange-state/", "/design-staging/"):
            code, h, data = ask(P, "GET", path)
            case(f"nothing lists a folder or answers at {path}", code == 404, code)

        # ---- stage 1: the state ----
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("state: the first pick and the current one are the kit's pick", code == 200 and st["ok"] and st["first"]["nums"] == pick and st["now"]["nums"] == pick and st["rev"] == 0, st.get("now"))
        text = data.decode()
        leaks = [w for w in ("/private", "/Volumes", "/Users", ".jpg", ".JPG", ".heic", ".png", ".tif", "beach-", "BEACH-", str(target)) if w in text]
        case("state: no path and no file name anywhere in it", not leaks, leaks)
        case("state: every photo, its shape, and whether its copy is ready", st["total"] == total and len(st["photos"]) == total and all(p["have"] and not p["missing"] for p in st["photos"]) and st["previews"] == {"made": total, "of": total})
        case("state: the limits and the advice range", st["limits"] == {"min": 2, "max": 60, "best": [8, 14]} and st["happy"] is None and st["job"] is None)
        case("state: not kept by the browser", h.get("cache-control") == "no-store")
        for label, path, want in (("an unknown kit", "/arrange-state?kit=Nope&page=reel", 404), ("kit=..", "/arrange-state?kit=..&page=reel", 404),
                                  ("a piece that has no page (singles)", f"/arrange-state?kit={KQ}&page=singles", 404), ("the designer (a later stage)", f"/arrange-state?kit={KQ}&page=design", 404),
                                  ("no page", f"/arrange-state?kit={KQ}", 404)):
            code, h, data = ask(P, "GET", path)
            try:
                j = json.loads(data)
            except ValueError:
                j = {}
            case(f"state refuses {label} in plain words", code == want and j.get("ok") is False and j.get("words"), (code, data[:80]))
        stamp = st["stamp"]

        # ---- stage 1: the page ----
        code, h, data = ask(P, "GET", f"/arrange.html?kit={KQ}&piece=reel")
        page = data.decode()
        case("the picker page is served, not kept by the browser", code == 200 and "data-kit='2026-11-01 Fake beach'" in page and "data-piece='reel'" in page and h.get("cache-control") == "no-store", code)
        case("the served page: no address on the internet, no browser storage, no clipboard, no draggable",
             not re.search(r"https?://", page) and "localStorage" not in page and "navigator.clipboard" not in page and 'draggable="true"' not in page)
        case("the served page: no path and no file name in it", str(target) not in page and "beach-0" not in page)
        for label, path, words in (("an unknown shoot", "/arrange.html?kit=Nope&piece=reel", "I can&#x27;t find that shoot&#x27;s posts."),
                                   ("a path for a kit", f"/arrange.html?kit={quote(str(kit), safe='')}&piece=reel", "I can&#x27;t find that shoot&#x27;s posts."),
                                   ("a piece that has no page (stories)", f"/arrange.html?kit={KQ}&piece=stories", "isn&#x27;t ready for this yet"),
                                   ("no piece", f"/arrange.html?kit={KQ}", "isn&#x27;t ready for this yet")):
            code, h, data = ask(P, "GET", path)
            t = data.decode()
            case(f"a small plain page, never an error page, for {label}", code == 200 and words in t and "Back to home" in t and "<script" not in t, (code, t[-200:]))

        # ---- stage 1: saving ----
        J = {"Content-Type": "application/json"}

        def post(body, headers=None, raw_body=None):
            b = raw_body if raw_body is not None else json.dumps(body).encode()
            code, h, data = ask(P, "POST", "/arrange", body=b, headers=headers if headers is not None else J)
            try:
                return code, json.loads(data)
            except ValueError:
                return code, {}

        def now():
            return json.loads(arr.read_text())["reel"]["now"]

        # a body that never arrives, on a request that is being refused: asked now, looked at further down
        # (the server gives a body 15 seconds; this must not hold up the other cases)
        hung = {}

        def never_sends():
            t0 = time.time()
            sk = socket.create_connection(("127.0.0.1", P), timeout=5)
            try:
                sk.sendall(f"POST /arrange HTTP/1.0\r\nHost: 127.0.0.1:{P}\r\nContent-Type: text/plain\r\nContent-Length: 500\r\n\r\n".encode())
                sk.settimeout(25)
                hung["line"] = sk.recv(200).split(b"\r\n")[0].decode(errors="replace")
            except socket.timeout:
                hung["line"] = "(no answer after 25 s: the thread is still held)"
            except OSError as e:
                hung["line"] = f"(closed: {e})"
            finally:
                hung["seconds"] = round(time.time() - t0, 1)
                sk.close()
        hung_thread = threading.Thread(target=never_sends)
        hung_thread.start()

        a, b, c, d = pick[0], pick[1], pick[2], pick[3]
        order = [b, a, c, d]
        PG, OTHER = "pageaaaa01", "pagebbbb02"            # two open pages (two windows)
        good = {"kit": kit_name, "piece": "reel", "stamp": stamp, "base": 0, "page": PG, "nums": order, "marks": ["", "+", "-", ""], "done": False}
        code, j = post(good)
        case("save: a new order with the right stamp, from the counter the page was told", code == 200 and j.get("ok") and j.get("rev") == 1 and now()["nums"] == order and now()["marks"] == ["", "+", "-", ""] and now()["rev"] == 1 and now()["by"] == "you", (code, j))
        saved = arr.read_bytes()
        code, j = post(good)
        case("save: the same save again answers ok with the same counter and writes nothing", code == 200 and j.get("ok") and j.get("rev") == 1 and arr.read_bytes() == saved, (code, j))
        code, j = post(dict(good, page=OTHER, nums=[a, b], marks=["", ""]))
        case("save: another window that has not seen the stored order is told there is something newer, and given it", code == 409 and j.get("why") == "newer" and j.get("state", {}).get("now", {}).get("nums") == order and j["state"]["rev"] == 1, (code, j.get("why")))
        code, j = post(dict(good, page=OTHER, base=3, nums=[a, b], marks=["", ""]))
        case("save: a counter that has run ahead does not get past that (it never saw the stored order)", code == 409 and j.get("why") == "newer" and arr.read_bytes() == saved, (code, j.get("why")))
        for big in (2 ** 53, 10 ** 30):
            code, j = post(dict(good, page=OTHER, base=big, nums=[a, b], marks=["", ""]))
            case(f"save: a counter of {big:.0e} is told the same, and nothing is stored", code == 409 and arr.read_bytes() == saved, code)
        # the page's own save whose answer never arrived: it carries on from the counter it knows
        code, j = post(dict(good, nums=[a, b, c], marks=["", "", ""]))
        case("save: the same page, carrying on from the same counter after a lost answer, is taken", code == 200 and j.get("rev") == 2 and now()["nums"] == [a, b, c], (code, j))
        code, j = post(dict(good, page=OTHER, nums=[c, d], marks=["", ""]))
        case("save: but another window from that same counter is not", code == 409 and now()["nums"] == [a, b, c], code)
        code, j = post(dict(good, base=2))
        case("save: and on from the counter the answer gave", code == 200 and j.get("rev") == 3 and now()["nums"] == order and now()["rev"] == 3, (code, j))
        good = dict(good, base=3)        # the body that is stored now; sent again below it changes nothing
        code, j = post(dict(good, stamp="000000000000"))
        case("save: a wrong stamp is told the photos changed", code == 409 and j.get("why") == "photos" and "changed" in j.get("words", ""), (code, j))

        import importlib
        sys.path.insert(0, str(SCRIPTS))
        arrange = importlib.import_module("arrange")      # only to read whether the Origin rule is switched on
        enforced = arrange.ORIGIN_ENFORCED
        nxt = dict(good, nums=[d, c, b, a], marks=["", "", "", ""])       # a real change, were it let in
        refuse = [
            ("Content-Type text/plain", 415, nxt, {"Content-Type": "text/plain"}, None),
            ("no Content-Type", 415, nxt, {}, None),
            ("Host: evil.example", 403, nxt, {"Content-Type": "application/json", "Host": "evil.example"}, None),
            ("Host with another port", 403, nxt, {"Content-Type": "application/json", "Host": "127.0.0.1:1"}, None),
            ("a 70,000-byte body", 413, None, J, json.dumps({"pad": "x" * 70000}).encode()),
            ("a number twice", 400, dict(nxt, nums=[a, a], marks=["", ""]), J, None),
            ("a number not on the sheet", 400, dict(nxt, nums=[a, 9999], marks=["", ""]), J, None),
            ("a number as text", 400, dict(nxt, nums=[str(a), b], marks=["", ""]), J, None),
            ("true for a number", 400, dict(nxt, nums=[True, b], marks=["", ""]), J, None),
            ("61 numbers for a reel", 400, dict(nxt, nums=list(range(1, 62)), marks=[""] * 61), J, None),
            ("marks of the wrong length", 400, dict(nxt, nums=[a, b], marks=[""]), J, None),
            ("a mark of 'x'", 400, dict(nxt, nums=[a, b], marks=["", "x"]), J, None),
            ("no marks at all", 400, {k: v for k, v in nxt.items() if k != "marks"}, J, None),
            ("done with one photo", 400, dict(nxt, nums=[a], marks=[""], done=True), J, None),
            ("done that is not yes or no", 400, dict(nxt, done="yes"), J, None),
            ("piece=singles", 400, dict(nxt, piece="singles"), J, None),
            ("piece=stories", 400, dict(nxt, piece="stories"), J, None),
            ("piece=design (a later stage)", 400, dict(nxt, piece="design"), J, None),
            ("a counter that is not a number", 400, dict(nxt, base="3"), J, None),
            ("a counter below zero", 400, dict(nxt, base=-1), J, None),
            ("true for a counter", 400, dict(nxt, base=True), J, None),
            ("a counter with a decimal point", 400, dict(nxt, base=3.0), J, None),
            ("no counter", 400, {k: v for k, v in nxt.items() if k != "base"}, J, None),
            ("no page name", 400, {k: v for k, v in nxt.items() if k != "page"}, J, None),
            ("a page name with a slash in it", 400, dict(nxt, page="../../etc"), J, None),
            ("a page name 200 letters long", 400, dict(nxt, page="a" * 200), J, None),
            ("kit=../x", 404, dict(nxt, kit="../x"), J, None),
            ("a path for the kit", 404, dict(nxt, kit=str(kit)), J, None),
            ("not JSON", 400, None, J, b"hello"),
            ("JSON that is a list", 400, None, J, b"[1,2]"),
        ]
        saved_before_refusals = arr.read_bytes()
        for label, want, body, headers, rb in refuse:
            code, j = post(body, headers, rb)
            case(f"save refuses: {label} ({want})", code == want and j.get("ok") is False and j.get("words"), (code, j))
        line = raw(P, f"POST /arrange HTTP/1.0\r\nHost: 127.0.0.1:{P}\r\nContent-Type: application/json\r\n\r\n")
        case("save refuses: no Content-Length, without hanging", " 400 " in line, line)
        line = raw(P, f"POST /arrange HTTP/1.0\r\nHost: 127.0.0.1:{P}\r\nContent-Type: application/json\r\nContent-Length: -1\r\n\r\n")
        case("save refuses: Content-Length -1, without hanging", " 400 " in line, line)
        line = raw(P, f"POST /arrange HTTP/1.0\r\nHost: 127.0.0.1:{P}\r\nContent-Type: application/json\r\nContent-Length: 0\r\n\r\n")
        case("save refuses: an empty body", " 400 " in line, line)
        code, h, data = ask(P, "OPTIONS", "/arrange")
        case("an OPTIONS request to /arrange answers 404 (so another website's request stops there)", code == 404, code)
        for path, want in (("/design", 404), ("/design-slide", 415), ("/design-commit", 404)):
            # the designer's routes (design.py; tests/design_check.py has their own cases): an empty request is refused
            code, h, data = ask(P, "POST", path, body=b"{}", headers=J)
            case(f"the designer's route refuses an empty request: POST {path} answers {want}", code == want and b'"ok": false' in data, (code, data[:80]))
        case("after the refusals the record is unchanged", arr.read_bytes() == saved_before_refusals)
        code, j = post(good, {"Content-Type": "application/json", "Origin": "http://evil.example"})
        if enforced:
            case("save refuses: Origin http://evil.example (403)", code == 403, code)
        else:
            case("the Origin rule is in LOG-ONLY mode: another Origin is let through for now, and written down", code == 200 and "Origin='http://evil.example'" in (studio / "arrange.log").read_text() and "would-pass=NO" in (studio / "arrange.log").read_text(), code)
        code, j = post(good, {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{P}"})
        case("this server's own Origin is accepted", code == 200, code)
        code, j = post(good, {"Content-Type": "application/json; charset=utf-8", "Origin": f"http://localhost:{P}", "Host": f"localhost:{P}"})
        case("localhost and a charset on the type are accepted", code == 200, (code, j))
        case("and none of those wrote anything (they carried what is already stored)", arr.read_bytes() == saved_before_refusals)

        # ---- reads keep the same rule as saves: only this server's own name ----
        for label, path in (("a photo", f"/kit-photo?kit={KQ}&n=3&size=l"), ("the state", f"/arrange-state?kit={KQ}&page=reel"),
                            ("the picker page", f"/arrange.html?kit={KQ}&piece=reel"), ("the home page", "/home"),
                            ("the posting page", "/posting.html"), ("a kit page", f"/content/{KQ}/Post%20kit.html")):
            code, h, data = ask(P, "GET", path, headers={"Host": f"evil.example:{P}"})
            case(f"a read that names another host is refused: {label}", code == 403 and b"\xff\xd8" not in data[:4] and b"beach" not in data.lower(), code)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel", headers={"Host": f"127.0.0.1:{P + 1}"})
        case("a read that names another port is refused", code == 403, code)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel", headers={"Host": f"localhost:{P}"})
        case("a read by the name localhost is answered", code == 200 and json.loads(data).get("ok") is True, code)
        code, h, data = ask(P, "GET", "/home")
        case("the home page still opens by this server's own name", code == 200 and b"<html" in data[:200].lower(), code)
        code, h, data = ask(P, "OPTIONS", "/feed", headers={"Host": f"evil.example:{P}"})
        case("and so is an OPTIONS request that names another host", code == 403, code)
        case("the kit record was never written by the server", rec_file.read_bytes() == rec_at_start)

        # ---- stage 1: Back to the first pick keeps what it replaced ----
        code, j = post(dict(good, nums=pick, marks=[""] * len(pick)))       # stored: counter 3; this makes it 4
        rec_now = json.loads(arr.read_text())["reel"]
        case("going back to the first pick keeps the order it replaced", code == 200 and rec_now["now"]["by"] == "assistant" and rec_now["earlier"] and rec_now["earlier"][-1]["nums"] == order and rec_now["earlier"][-1]["marks"] == ["", "+", "-", ""], rec_now.get("earlier"))

        # ---- stage 1: the final button, and the hand-back to Claude ----
        code, out = run(env, "home.py", "pending")
        case("before the final button, home.py pending has no ARRANGED line", code == 0 and "ARRANGED" not in out, out)
        final = [c, a, b, d] + pick[4:]
        fmarks = ["+", "", "-", ""] + [""] * (len(pick) - 4)
        code, j = post(dict(good, base=4, nums=final, marks=fmarks, done=True))
        rec_now = json.loads(arr.read_text())["reel"]
        case("the final button: saved, and marked as the order they are happy with", code == 200 and j.get("ok") and j.get("rev") == 5 and rec_now["happy"]["rev"] == 5 and rec_now["now"]["nums"] == final, (code, j))
        w = json.loads((studio / "arrange-waiting.json").read_text())
        case("the final button: the kit is named in arrange-waiting.json", len(w) == 1 and w[0]["kit"] == kit_name and w[0]["piece"] == "reel" and w[0]["count"] == len(final), w)
        code, j = post(dict(good, base=4, nums=final, marks=fmarks, done=True))
        case("the final button pressed twice by a retry: still one entry", code == 200 and j.get("rev") == 5 and len(json.loads((studio / "arrange-waiting.json").read_text())) == 1)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        case("state: happy carries the counter it was pressed at", json.loads(data)["happy"] == {"rev": 5} and json.loads(data)["rev"] == 5)

        # ---- the numbered list not readable for a moment: nothing may be taken for an empty shoot ----
        held = arr.read_bytes()
        sheet_file = kit / ".kit" / "sheet.json"
        sheet_aside = work / "sheet-aside.json"
        shutil.move(str(sheet_file), str(sheet_aside))
        try:
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
            case("the list can't be read: the state says not ready", code == 404 and json.loads(data).get("ok") is False, code)
            code, j = post(dict(good, base=5, nums=[a, b], marks=["", ""]))
            case("the list can't be read: a save is not taken", code == 404 and j.get("ok") is False, (code, j))
            code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel")
            case("the list can't be read: apply stops, and says nothing was changed", code == 2 and out.startswith("STOP:") and "Nothing was changed" in out, out)
            case("the list can't be read: the order on record is exactly as it was", arr.read_bytes() == held)
            sheet_file.write_text("{ this is half a fi", encoding="utf-8")
            code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel", "--dry")
            case("a list that is only half there is treated the same way", code == 2 and arr.read_bytes() == held, out)
            shutil.move(str(sheet_file), str(work / "sheet-half.json"))
        finally:
            shutil.move(str(sheet_aside), str(sheet_file))
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("the list back: the same order, the same counter, still waiting", code == 200 and st["now"]["nums"] == final and st["rev"] == 5 and st["happy"] == {"rev": 5} and arr.read_bytes() == held, (code, st.get("now")))
        code, out = run(env, "home.py", "pending")
        want_line = f"ARRANGED: {kit_name} | reel | {len(final)} photos"
        case("home.py pending prints the ARRANGED line, after its list", code == 0 and out.strip().splitlines()[-1] == want_line and out.lstrip().startswith("["), out[-200:])
        code, out = run(env, "arrange.py", "waiting")
        case("arrange.py waiting prints the same line", code == 0 and out.strip() == want_line, out)

        # the cover is made once; so the record must stay true of it when the opener changes
        code, out = run(env, "kit.py", "build", kit_name)
        case("kit.py build makes the pieces, and its reel line carries the picks", code == 0 and (kit / "Covers" / "Reel cover.jpg").is_file() and "Reel: run reel.py make with these picks: " + ",".join(map(str, pick)) + " --folder" in out, out[-300:])
        # ---- the kit page's own address serves the kit page and its pieces, and nothing else ----
        code, h, data = ask(P, "GET", f"/content/{KQ}/Post%20kit.html")
        case("the kit page still opens", code == 200 and b"Post kit" in data and h.get("content-type", "").startswith("text/html"), code)
        cover = quote("Reel cover.jpg")
        code, h, data = ask(P, "GET", f"/content/{KQ}/Covers/{cover}")
        case("and its pictures still load (a piece the Assistant made)", code == 200 and data[:2] == b"\xff\xd8", code)
        one_photo = quote(Path(plain["file"]).name)
        look_alike = "Your%20Content%20old/Sneaky"
        for label, path in (("the numbered list (it holds folder paths)", f"/content/{KQ}/.kit/sheet.json"),
                            ("the kit record", f"/content/{KQ}/.kit/kit.json"),
                            ("the arrangement", f"/content/{KQ}/.kit/arrange.json"),
                            ("a small copy, by its file name", f"/content/{KQ}/.kit/previews/{quote(sorted(os.listdir(prev))[0])}"),
                            ("the photo itself", f"/content/{KQ}/Photos/{one_photo}"),
                            ("the hidden folder written with %2e", f"/content/{KQ}/%2ekit/kit.json"),
                            ("the kit's folder itself", f"/content/{KQ}/"),
                            ("a look-alike beside Your Content, by %2e%2e", f"/content/%2e%2e/{look_alike}/.kit/kit.json"),
                            ("the same with a kit page's name", f"/content/%2e%2e/{look_alike}/Post%20kit.html"),
                            ("the same by ..%2F", f"/content/..%2F{look_alike}%2FPost%20kit.html"),
                            ("a file that is not a picture in a piece folder", f"/content/{KQ}/Covers/..%2F.kit%2Fkit.json"),
                            ("a path from the top of the disk", "/content/%2Fetc%2Fhosts")):
            code, h, data = ask(P, "GET", path)
            case(f"the kit page's address refuses: {label}", code == 404 and b"folder" not in data and data[:2] != b"\xff\xd8", (code, data[:60]))
        (target / "The Assistant" / "Your Content old" / "Sneaky" / "Post kit.html").write_text("<p>sneaky</p>")     # this check's own file, in its own scratch
        os.symlink(str(target / "The Assistant" / "Your Content old" / "Sneaky"), str(kit.parent / "Linked kit"))
        code, h, data = ask(P, "GET", "/content/Linked%20kit/Post%20kit.html")
        case("the kit page's address refuses: a link out of Your Content", code == 404 and b"sneaky" not in data, (code, data[:40]))
        os.unlink(str(kit.parent / "Linked kit"))                  # the link this check made a moment ago
        case("re-numbering left no half-written list behind", not [x for x in os.listdir(kit / ".kit") if x.endswith(".tmp")], os.listdir(kit / ".kit"))

        rec_before = rec_file.read_bytes()
        code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel", "--dry")
        want_text = ",".join(f"{n}{m}" for n, m in zip(final, fmarks))
        case("arrange.py apply --dry prints the picks and writes nothing", code == 0 and out.strip() == "Reel picks: " + want_text and rec_file.read_bytes() == rec_before, out)
        code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel")
        rec2 = json.loads(rec_file.read_text())
        case("arrange.py apply prints 'Reel picks: ...' with + and - in place", code == 0 and out.strip() == "Reel picks: " + want_text and "+" in want_text and "-" in want_text, out)
        case("apply: the kit record has plain numbers, and the marks beside them", rec2["picks"]["reel"] == final and rec2["reel_marks"] == {str(c): "+", str(b): "-"}, (rec2["picks"]["reel"], rec2.get("reel_marks")))
        case("apply: the old opener is written down as the cover pick, since the cover file is not re-made", rec2["picks"].get("cover") == [pick[0]], rec2["picks"].get("cover"))
        case("apply: the other picks are as they were", rec2["picks"]["carousel"] == rec["picks"]["carousel"])
        code, out = run(env, "home.py", "pending")
        case("apply: the ARRANGED line is gone", "ARRANGED" not in out, out)
        both = rec_file.read_bytes() + arr.read_bytes()
        code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel")
        case("apply twice: the same line, and nothing changes", code == 0 and out.strip() == "Reel picks: " + want_text and rec_file.read_bytes() + arr.read_bytes() == both, out)
        code, out = run(env, "kit.py", "show", kit_name)
        case("kit.py show still prints", code == 0 and f"reel {len(final)}" in out, out)
        code, out = run(env, "kit.py", "build", kit_name)
        case("kit.py build's reel line carries the marks", code == 0 and "with these picks: " + want_text + " --folder" in out, out[-300:])
        code, out = run(env, REEL, "make", "--dry-run", "--folder", str(photos_dir), "--shoot", "Fake beach", "--pace", "mixed", "--picks", want_text)
        case("reel.py make --dry-run accepts that text", code == 0 and out.startswith(f"Plan: {len(final)} photos"), out[:200])
        try:
            durs = [p["dur"] for p in json.loads((studio / "reels" / "Fake-beach" / "reel.json").read_text())["plan"]["photos"]]
            case("in that plan the Longer photo is held longer than the Quicker one", durs[final.index(c)] > durs[final.index(b)], durs)
        except (OSError, KeyError, ValueError) as e:
            case("in that plan the Longer photo is held longer than the Quicker one", False, e)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("after apply the page still shows their order, and the first pick is still the Assistant's", st["now"]["nums"] == final and st["first"]["nums"] == pick and st["rev"] == 5)
        case("after apply nothing is waiting, so the page is not told to show the line under the final button", st["happy"] is None, st["happy"])
        code, out = run(env, "arrange.py", "took", "Fake beach")
        case("arrange.py took with nothing waiting says so", code == 0 and "Nothing was waiting" in out, out)
        code, j = post(dict(good, base=5, nums=final, marks=fmarks, done=True))
        code2, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        code3, out = run(env, "arrange.py", "waiting")
        case("the final button pressed again on the same order after apply: it is waiting again", code == 200 and json.loads(data)["happy"] == {"rev": 5} and out.strip() == want_line, (code, out))
        code, out = run(env, "arrange.py", "took", "Fake beach", "--piece", "reel")
        code2, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        case("took (\"Not now\"): cleared, the order stays, and the line is not shown again", code == 0 and out.strip() == "Cleared." and json.loads(data)["happy"] is None and json.loads(data)["now"]["nums"] == final, out)

        # ---- apply and a save from the page at the same moment ----
        late = [d, c, b, a]
        code, j = post(dict(good, base=5, nums=[a, b, c, d], marks=["", "", "", ""]))          # counter 6: something for apply to take
        body = json.dumps(dict(good, base=6, nums=late, marks=["", "", "", ""], done=True))
        r = subprocess.run([PY, "-c", RACE, str(SCRIPTS), str(P), kit_name, body], capture_output=True, text=True, env=env, timeout=120)
        try:
            got = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            got = {"error": (r.stdout + r.stderr)[-300:]}
        case("apply holds the kit's arrangement: a save sent while it works waits for it", got.get("kit_written") is True and got.get("answered_while_apply_held_it") is False and got.get("apply", [None])[0] == 0, got)
        rec_now = json.loads(arr.read_text())["reel"]
        case("and then lands whole: the page was told Saved and its order is the one on record", got.get("code") == 200 and rec_now["now"]["nums"] == late and rec_now["now"]["rev"] == 7 and rec_now["happy"]["rev"] == 7, (got.get("code"), rec_now["now"]))
        code, out = run(env, "arrange.py", "waiting")
        case("and it is waiting for Claude (apply did not clear what arrived after it)", out.strip() == f"ARRANGED: {kit_name} | reel | 4 photos", out)
        case("apply itself took the order that was there when it started", got.get("apply", [0, ""])[1] == "Reel picks: " + ",".join(map(str, [a, b, c, d])) and json.loads(rec_file.read_text())["picks"]["reel"] == [a, b, c, d], got.get("apply"))
        code, out = run(env, "arrange.py", "apply", "Fake beach", "--piece", "reel")
        case("the next apply takes the later order and clears the line", code == 0 and out.strip() == "Reel picks: " + ",".join(map(str, late)) and "ARRANGED" not in run(env, "home.py", "pending")[1], out)
        # a command that finds the arrangement held for too long says so and changes nothing
        holder = subprocess.Popen([PY, "-c", "import sys, time; sys.path.insert(0, sys.argv[1]); import arrange\nk = arrange.kit_by_name(sys.argv[2])\nwith arrange.locked(arrange.kit_lock(k)):\n    print('held', flush=True); time.sleep(4)", str(SCRIPTS), kit_name],
                                  stdout=subprocess.PIPE, text=True, env=env)
        holder.stdout.readline()
        t0 = time.time()
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        waited = time.time() - t0
        holder.wait(timeout=20)
        case("the server waits for a command that holds the arrangement, then answers", code == 200 and 2.0 < waited < 9.0, (code, round(waited, 1)))
        final, fmarks, want_text = late, ["", "", "", ""], ",".join(map(str, late))

        # ---- stage 1: a fresh pick from Claude wins, and nothing is lost ----
        code, out = run(env, "kit.py", "picks", kit_name, "--reel", "5,6,7+")
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("a fresh pick replaces the page's order (5, 6, 7 with 7 on Longer)", st["now"] == {"nums": [5, 6, 7], "marks": ["", "", "+"]} and st["first"]["nums"] == [5, 6, 7] and st["happy"] is None and st["rev"] == 8, (st["now"], st["rev"]))
        code, out = run(env, "arrange.py", "earlier", "Fake beach", "--piece", "reel")
        case("arrange.py earlier prints the arrangement that was replaced", code == 0 and want_text in out and "a fresh pick replaced it" in out, out)
        code, j = post(dict(good, base=7, nums=[5, 7], marks=["", ""]))
        case("a page still on the old order is told there is something newer", code == 409 and j.get("why") == "newer" and j["state"]["now"]["nums"] == [5, 6, 7], code)

        hung_thread.join(40)
        case("a refused request whose body never arrives is answered and let go (it used to hold a thread for ever)", " 415 " in hung.get("line", "") and hung.get("seconds", 99) < 22, hung)

        # ---- stage 1: surviving a restart, on another port ----
        code, j = post(dict(good, base=8, nums=[7, 5, 6], marks=["+", "", ""]))
        srv.stop()
        code_down = None
        try:
            ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        except OSError:
            code_down = "refused"
        srv2 = Server(env, port + 4)
        P = srv2.start()
        srv = srv2
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("after a stop and a start on another port the same row comes back", code_down == "refused" and st["now"] == {"nums": [7, 5, 6], "marks": ["+", "", ""]} and st["rev"] == 9, (P, st["now"]))

        # ---- stage 1: arrange.py open ----
        code, out = run(env, "arrange.py", "open", "Fake beach", "--piece", "reel")
        addr = out.strip().splitlines()[-1] if out.strip() else ""
        case("arrange.py open prints the page's address on the running server", code == 0 and addr == f"http://127.0.0.1:{P}/arrange.html?kit={KQ}&piece=reel", out)
        code, h, data = ask(P, "GET", addr.split(f":{P}", 1)[1]) if addr else (0, {}, b"")
        case("and the page is there", code == 200 and b"data-piece='reel'" in data, code)
        code, out = run(env, "arrange.py", "open", "Fake beach", "--piece", "singles")
        case("arrange.py open for a piece with no page stops with a plain line", code == 1 and out.startswith("STOP:"), out)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        case("the reel has no slide-making job: its state carries none", json.loads(data).get("job") is None and not (kit / ".kit" / "arrange-job.json").exists())

        # ---- stage 1: the photos changing under an open page ----
        stamp = st["stamp"]
        extra = photos_dir / "aaa-extra.jpg"                   # sorts first, so every number moves along by one
        shutil.copyfile(photos_dir / Path(plain["file"]).name, extra)
        code, out = run(env, "kit.py", "sheet", kit_name)
        code, j = post(dict(good, stamp=stamp, base=9, nums=[5, 7], marks=["", ""]))
        case("photos changed under an open page: a save is told so", code == 409 and j.get("why") == "photos", (code, j))
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("after a reload the same photos are in the row, found again by name though their numbers moved", st["now"] == {"nums": [8, 6, 7], "marks": ["+", "", ""]} and st["stamp"] != stamp and st["total"] == total + 1 and st["dropped"] == [], st["now"])
        rec_now = json.loads(arr.read_text())["reel"]
        case("the record's names follow the new numbers", rec_now["names"].get("8") == Path(next(x for x in sheet if x["n"] == 7)["file"]).name, rec_now["names"])
        ask(P, "GET", f"/arrange.html?kit={KQ}&piece=reel")           # opening the page starts the copies being made
        made = 0
        for _ in range(100):
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
            made = json.loads(data)["previews"]["made"]
            if made == total + 1:
                break
            time.sleep(0.3)
        case("opening the page gets the missing copies made, off the request, and the count climbs to all", made == total + 1, made)
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n=1&size=s")
        case("the new photo's copy is served", code == 200 and data[:2] == b"\xff\xd8", code)

        # ---- stage 1: a photo that has gone missing ----
        stamp = st["stamp"]
        aside = work / "moved-aside"
        aside.mkdir(exist_ok=True)
        gone_name = Path(next(x for x in sheet if x["n"] == 7)["file"]).name       # photo 8 now, and in the row
        shutil.move(str(photos_dir / gone_name), str(aside / gone_name))
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        p8 = next(p for p in st["photos"] if p["n"] == 8)
        case("a photo moved out of the folder: the state marks it, and its copy still shows", p8["missing"] is True and p8["have"] is True and st["now"]["nums"] == [8, 6, 7], p8)
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n=8&size=s")
        case("and its older copy is still served", code == 200 and data[:2] == b"\xff\xd8", code)
        copies8 = [n for n in os.listdir(prev) if n.startswith("0008-")]
        for n in copies8:
            shutil.move(str(prev / n), str(aside / n))
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        p8 = next(p for p in json.loads(data)["photos"] if p["n"] == 8)
        code, h, data = ask(P, "GET", f"/kit-photo?kit={KQ}&n=8&size=s")
        case("with no copy either: marked missing with nothing to show, and the picture answers 404", p8["missing"] is True and p8["have"] is False and code == 404, (p8, code))
        code, out = run(env, "arrange.py", "previews", "Fake beach")
        case("previews says how many can't be reached right now", "can't be reached right now: 1" in out, out)
        for n in copies8:
            shutil.move(str(aside / n), str(prev / n))
        shutil.move(str(aside / gone_name), str(photos_dir / gone_name))
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        p8 = next(p for p in json.loads(data)["photos"] if p["n"] == 8)
        case("put back: it is whole again", p8["missing"] is False and p8["have"] is True, p8)

        # ---- stage 1: a photo that has left the shoot ----
        shutil.move(str(photos_dir / gone_name), str(aside / gone_name))
        code, out = run(env, "kit.py", "sheet", kit_name)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        case("a photo no longer in the shoot is taken out of the row and counted", st["now"] == {"nums": [6, 7], "marks": ["", ""]} and len(st["dropped"]) == 1 and st["total"] == total, (st["now"], st["dropped"]))
        case("and the record names it", json.loads(arr.read_text())["reel"]["dropped"] == [gone_name])
        last = (json.loads(arr.read_text())["reel"].get("earlier") or [{}])[-1]
        case("and the order as it was is kept, by file name, with its marks", last.get("why") == "photos left the shoot" and last.get("was", [None])[0] == gone_name + "+" and len(last.get("was", [])) == 3 and last.get("nums") == [6, 7], last)
        code, out = run(env, "arrange.py", "earlier", "Fake beach", "--piece", "reel")
        case("arrange.py earlier prints it", code == 0 and "photos left the shoot; it was: " + gone_name + "+" in out, out[-300:])
        shutil.move(str(aside / gone_name), str(photos_dir / gone_name))
        run(env, "kit.py", "sheet", kit_name)

        # ---- stage 1: a file that is there but is not a picture ----
        broken = photos_dir / "zzz-broken.jpg"
        broken.write_bytes(b"this is not a photo" * 40)
        run(env, "kit.py", "sheet", kit_name)
        code, out = run(env, "arrange.py", "previews", "Fake beach")
        case("previews says so when a photo can't be read, and exits 1", code == 1 and "couldn't be read: 1" in out, out)
        code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=reel")
        st = json.loads(data)
        last = st["photos"][-1]
        case("a photo that can't be read is marked for the page, with nothing to show", last["missing"] is True and last["have"] is False and st["previews"]["made"] == st["previews"]["of"] - 1, last)
        kids = len(subprocess.run(["pgrep", "-f", "arrange.py previews"], capture_output=True, text=True).stdout.split())
        ask(P, "GET", f"/arrange.html?kit={KQ}&piece=reel")
        time.sleep(0.4)
        kids2 = len(subprocess.run(["pgrep", "-f", "arrange.py previews"], capture_output=True, text=True).stdout.split())
        case("and opening the page does not keep trying to copy it", kids2 <= kids, (kids, kids2))
        shutil.move(str(broken), str(aside / broken.name))
        run(env, "kit.py", "sheet", kit_name)

        # ---- the whole time ----
        after = folder_print(photos_dir)
        case("the photos themselves: not one changed (only the test's own extra photo was added)", {k: v for k, v in after.items() if k != "aaa-extra.jpg"} == before)
        case("nothing was left in the Photos folder that is not a photo", all(not n.startswith(".") for n in os.listdir(photos_dir)), os.listdir(photos_dir)[:3])
        log_text = (studio / "arrange.log").read_text() if (studio / "arrange.log").exists() else ""
        case("the log wrote down what Origin each kind of request carried", "origin: POST /arrange Origin=None" in log_text and "Origin='http://127.0.0.1:" in log_text, log_text[-300:])
        case("nothing went wrong inside a route (no 'failed' line in the log)", " failed: " not in log_text, [x for x in log_text.splitlines() if " failed: " in x][:2])
    finally:
        srv.stop()
    check_cover(work)
    check_carousel(work, port + 8)
    check_carousel_fixes(work, port + 16)


def check_cover(work):
    """The reel cover is made once. When the reel's first photo changes afterwards and no cover pick is
    written down, apply writes down the photo the cover was made from: the kit's OWN first photo before
    this apply. Two fresh kits, no server (a page's save is made by calling the same function the route calls)."""
    def fresh(label):
        target = work / f"fake-{label}"
        r = subprocess.run([PY, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", "10"], capture_output=True, text=True, timeout=600)
        env = dict(os.environ, STUDIO_HOME=str(target / "studio"))
        kit = target / "The Assistant" / "Your Content" / "2026-11-01 Fake beach"
        return r.returncode == 0, env, kit

    def page(env, nums):
        r = subprocess.run([PY, "-c", PAGE_SAVE, str(SCRIPTS), "2026-11-01 Fake beach", json.dumps(nums)], capture_output=True, text=True, env=env, timeout=60)
        return r.stdout.strip()

    def picks(kit):
        return json.loads((kit / ".kit" / "kit.json").read_text())["picks"]

    # (a) the cover was made AFTER the page had already changed the opener; a later change keeps that opener
    ok, env, kit = fresh("cover-a")
    if case("cover case (a): a fresh pretend kit", ok):
        run(env, "kit.py", "picks", "Fake beach", "--reel", "1,2,3")
        got = [page(env, [2, 1, 3]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        case("cover (a): page order 2,1,3 taken; no cover yet, so no cover pick is written", got == ["200", "Reel picks: 2,1,3"] and not picks(kit).get("cover"), (got, picks(kit)))
        code, out = run(env, "kit.py", "build", "Fake beach")
        case("cover (a): the cover is then made (from photo 2, the opener)", code == 0 and (kit / "Covers" / "Reel cover.jpg").is_file(), out[-200:])
        got = [page(env, [2, 3, 1]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        case("cover (a): the order changes but the opener does not: still no cover pick (it used to write photo 1, which the cover was not made from)", got == ["200", "Reel picks: 2,3,1"] and not picks(kit).get("cover"), (got, picks(kit).get("cover")))
        got = [page(env, [3, 2, 1]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        case("cover (a): now the opener changes: the cover pick is the photo the cover was made from", got == ["200", "Reel picks: 3,2,1"] and picks(kit).get("cover") == [2], (got, picks(kit).get("cover")))
        got = [page(env, [1, 2, 3]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        case("cover (a): and a cover pick, once written, is left alone", picks(kit).get("cover") == [2], picks(kit).get("cover"))
    # (b) a photo was added on the page before the cover was made; then the opener changes
    ok, env, kit = fresh("cover-b")
    if case("cover case (b): a fresh pretend kit", ok):
        run(env, "kit.py", "picks", "Fake beach", "--reel", "1,2,3")
        got = [page(env, [1, 2, 3, 4]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        code, out = run(env, "kit.py", "build", "Fake beach")
        case("cover (b): page order 1,2,3,4 taken, then the cover made (from photo 1)", got == ["200", "Reel picks: 1,2,3,4"] and (kit / "Covers" / "Reel cover.jpg").is_file() and not picks(kit).get("cover"), (got, out[-200:]))
        got = [page(env, [4, 1, 2, 3]), run(env, "arrange.py", "apply", "Fake beach")[1]]
        case("cover (b): the opener changes from 1 to 4: the cover pick is photo 1 (it used to write nothing)", got == ["200", "Reel picks: 4,1,2,3"] and picks(kit).get("cover") == [1], (got, picks(kit).get("cover")))

# ---------- stage 2: the carousel's slides, and the job that makes them ----------

# A pretend sips for one case: asked for a size it answers as the real one does; asked to write a picture,
# it writes half a file and dies the way a killed process does.
SIPS_SHIM = """#!/bin/sh
case " $* " in
  *" --out "*) for last; do :; done; printf 'half a picture' > "$last"; kill -9 $$ ;;
  *) exec /usr/bin/sips "$@" ;;
esac
"""

SHAPE_KILLED = r"""
import os, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import kit
out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
dst = out / "Slide 01 (test).jpg"
print(kit.slide(Path(sys.argv[2]), dst), dst.exists(), sorted(n for n in os.listdir(out) if not n.startswith(".")))
"""


# Claude's own apply for the carousel, with the page's final button pressed on a NEWER order while it is at
# work (sent to the real server from inside apply, right after its slides are made and while it still holds
# the job's lock). The server must leave that press to whoever is at work, and apply must hand it on.
CAR_RACE = r"""
import contextlib, io, json, sys, http.client
sys.path.insert(0, sys.argv[1])
import arrange, kit as kit_mod
port, name, body = int(sys.argv[2]), sys.argv[3], sys.argv[4].encode()
kit = arrange.kit_by_name(name)
real, out = kit_mod.rebuild_carousel, {}
def with_a_press(k, nums=None, say_status=None, take=None):
    res = real(k, nums, say_status, take)
    kit_mod.rebuild_carousel = real
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
    c.request('POST', '/arrange', body=body, headers={'Content-Type': 'application/json'})
    r = c.getresponse(); out['code'] = r.status; out['answer'] = json.loads(r.read()); c.close()
    return res
kit_mod.rebuild_carousel = with_a_press
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = arrange.apply_carousel(kit)
out['apply'] = [code, buf.getvalue().strip()]
print(json.dumps(out))
"""

# Where the Mac's own locks can't be used (a drive without them), whether a job is at work is told from the
# job's own process number instead, for at most five minutes.
NO_LOCKS = r"""
import json, os, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
import arrange
arrange.fcntl = None
kit = arrange.kit_by_name(sys.argv[2])
was = arrange.job_path(kit).read_bytes()
gone = subprocess.Popen([sys.executable, '-c', 'pass']); gone.wait()
out = []
for state, pid, age in (('running', os.getpid(), 0), ('running', gone.pid, 0), ('running', os.getpid(), 400), ('queued', None, 0), ('done', os.getpid(), 0)):
    arrange.write_whole(arrange.job_path(kit), {'state': state, 'line': 'x', 'rev': 1, 'count': 2, 'pid': pid, 'at': 'x', 't': time.time() - age})
    out.append(arrange.job_running(kit))
arrange.job_path(kit).write_bytes(was)        # this check's own stand-in records; the real one goes back
print(json.dumps(out))
"""


def tree_print(folder):
    """Every file under a folder with its hash, by its path from that folder."""
    out = {}
    for root, _, files in os.walk(folder):
        for f in files:
            pth = Path(root) / f
            out[pth.relative_to(folder).as_posix()] = hashlib.sha256(pth.read_bytes()).hexdigest()
    return out


def wait_job(P, KQ, rev, seconds=60):
    """Ask the state, as the page does, until the slide job for this counter has ended. The job as last seen."""
    end, job = time.time() + seconds, None
    while time.time() < end:
        try:
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=carousel")
            job = json.loads(data).get("job")
        except (OSError, ValueError):
            job = None
        if job and job.get("rev") == rev and job.get("state") in ("done", "same", "problem"):
            return job
        time.sleep(0.25)
    return job or {}


def check_carousel(work, port):
    """The carousel picker's server side, on a kit of its own: saving, the final button and its job, what
    happens to the files (counted and hashed), a job cut off at each stop and finished by the next run,
    a run with nothing to change, a photo gone missing, a server that stops in the middle, the kit page."""
    target = work / "fake-carousel"
    r = subprocess.run([PY, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", "24"], capture_output=True, text=True, timeout=600)
    if not case("carousel: a pretend kit of its own was made", r.returncode == 0, (r.stdout + r.stderr)[-300:]):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    env.pop("ARRANGE_TEST_STOP", None)
    env.pop("ARRANGE_TEST_STOP_ONCE", None)
    kit_name = "2026-11-01 Fake beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    photos_dir, car, hid = kit / "Photos", kit / "Carousel", kit / ".kit"
    rec_file, arr, job_file = hid / "kit.json", hid / "arrange.json", hid / "arrange-job.json"
    sheet = json.loads((hid / "sheet.json").read_text())["photos"]
    stem_of = {x["n"]: Path(x["file"]).stem for x in sheet}
    name_of = {x["n"]: Path(x["file"]).name for x in sheet}
    pick = json.loads(rec_file.read_text())["picks"]["carousel"]
    photos_before = folder_print(photos_dir)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    arrange = importlib.import_module("arrange")          # only for its words
    EXTRA = ["Slide 01 (Canva).jpg", "my own.jpg"]        # in the Carousel folder, and not the Assistant's plain slides
    floor = Counter()                                     # every picture ever seen in the kit, by its bytes: how many copies at most

    def slide_names(order):
        return [f"Slide {i:02d} ({stem_of[n]}).jpg" for i, n in enumerate(order, 1)]

    def pictures():
        """Every picture in the kit (wherever it is: Photos, Carousel, set aside), counted by its bytes.
        Not counted: scratch files (names starting with a dot), the small copies the page shows, and the
        making folder (.kit/slides-new), where slides are made before any has a place in the Carousel
        folder: a slide that was made there and never put in is scratch, and a later run clears it."""
        return Counter(v for k, v in tree_print(kit).items()
                       if k.lower().endswith((".jpg", ".heic", ".png", ".tif")) and not Path(k).name.startswith(".")
                       and not k.startswith(".kit/previews/") and not k.startswith(".kit/slides-new/"))

    def remember():
        now_ = pictures()
        for h_, c in now_.items():
            floor[h_] = max(floor[h_], c)

    def nothing_lost():
        """Pictures of which there are now fewer copies than there once were. A move keeps the count; only a
        delete or a write-over lowers it."""
        now_ = pictures()
        return [h_[:10] for h_, c in floor.items() if now_[h_] < c]

    def journals():
        d = hid / "slides-older"
        return [json.loads((d / x / "moved.json").read_text())["state"] for x in sorted(os.listdir(d))] if d.is_dir() else []

    def settled(order):
        """Is the kit exactly as it should be for this order? An empty list, or what is wrong."""
        wrong = []
        names = sorted(n for n in os.listdir(car))
        if names != sorted(slide_names(order) + EXTRA):
            wrong.append(("the Carousel folder", names))
        if any(jpeg_size((car / n).read_bytes()) != (1080, 1350) for n in slide_names(order) if (car / n).is_file()):
            wrong.append("a slide is not 1080 x 1350")
        if any(st != "done" for st in journals()):
            wrong.append(("a move left unfinished", journals()))
        rec = json.loads(rec_file.read_text())
        if rec.get("made_pieces", {}).get("carousel") != slide_names(order):
            wrong.append(("the kit's record of its slides", rec.get("made_pieces", {}).get("carousel")))
        if nothing_lost():
            wrong.append(("lost", nothing_lost()))
        if folder_print(photos_dir) != photos_before:
            wrong.append("the Photos folder changed")
        return wrong

    code, out = run(env, "arrange.py", "previews", kit_name)
    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (carousel: page server on port {P}, STUDIO_HOME={studio})", flush=True)
        J = {"Content-Type": "application/json"}

        def post(body):
            code, h, data = ask(P, "POST", "/arrange", body=json.dumps(body).encode(), headers=J)
            try:
                return code, json.loads(data)
            except ValueError:
                return code, {}

        def state():
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=carousel")
            return json.loads(data), data.decode()

        def now():
            return json.loads(arr.read_text())["carousel"]["now"]

        # the folder button's own route, where it cannot open anything: this kit has no Carousel folder yet
        code, h, data = ask(P, "GET", f"/open?kit={KQ}&sub=Carousel")
        case("carousel: the folder button's route says so in plain words when there is no Carousel folder yet", code == 200 and json.loads(data) == {"ok": False, "words": "There's no Carousel folder yet."}, data[:120])

        # ---- 2.1: the slides are written under a scratch name first ----
        code, out = run(env, "kit.py", "build", kit_name)
        case("kit.py build makes the plain slides, named by place and photo", code == 0 and "Carousel: 7 made." in out and sorted(os.listdir(car)) == sorted(slide_names(pick)), (out[-200:], sorted(os.listdir(car)) if car.is_dir() else None))
        case("every slide is 1080 x 1350", all(jpeg_size((car / n).read_bytes()) == (1080, 1350) for n in os.listdir(car)))
        case("build left no half-made or scratch file in any folder it writes to", not [n for d in ("Carousel", "Covers") for n in os.listdir(kit / d) if n.startswith(".")])
        shim = work / "shim"
        shim.mkdir(exist_ok=True)
        (shim / "sips").write_text(SIPS_SHIM)
        os.chmod(shim / "sips", 0o755)
        shim_env = dict(env, PATH=f"{shim}:{os.environ.get('PATH', '/usr/bin:/bin')}")
        r = subprocess.run([PY, "-c", SHAPE_KILLED, str(SCRIPTS), str(photos_dir / name_of[1]), str(work / "shape-out")], capture_output=True, text=True, env=shim_env, timeout=60)
        case("sips killed while it writes a slide: no file appears under the slide's real name", r.stdout.strip() == "False False []", (r.stdout + r.stderr)[-200:])
        r = subprocess.run([PY, "-c", SHAPE_KILLED, str(SCRIPTS), str(photos_dir / name_of[1]), str(work / "shape-out")], capture_output=True, text=True, env=env, timeout=60)
        made_once = (work / "shape-out" / "Slide 01 (test).jpg").read_bytes() if (work / "shape-out" / "Slide 01 (test).jpg").is_file() else b""
        case("with the real sips the same call makes it", r.stdout.strip() == "True True ['Slide 01 (test).jpg']" and jpeg_size(made_once) == (1080, 1350), r.stdout)
        r = subprocess.run([PY, "-c", SHAPE_KILLED, str(SCRIPTS), str(photos_dir / name_of[2]), str(work / "shape-out")], capture_output=True, text=True, env=env, timeout=60)
        case("a name that is taken is never written over (asked to make another photo's slide under it)", (work / "shape-out" / "Slide 01 (test).jpg").read_bytes() == made_once and not [n for n in os.listdir(work / "shape-out") if n.startswith(".")], r.stdout)

        # things in the Carousel folder that are not the Assistant's plain slides (this check's own files)
        shutil.copyfile(car / slide_names(pick)[0], car / EXTRA[0])
        (car / EXTRA[1]).write_bytes(b"a file the photographer dropped in themselves")
        code, out = run(env, "posting_queue.py", "add", "--kit", kit_name)
        posting = json.loads((studio / "posting.json").read_text())
        thumb = studio / next(x for x in posting["pieces"] if x["kind"] == "carousel")["thumb"]
        thumb_before = thumb.stat().st_mtime_ns

        # ---- the page and its state ----
        code, h, data = ask(P, "GET", f"/arrange.html?kit={KQ}&piece=carousel")
        page = data.decode()
        case("carousel: the picker page is served for piece=carousel", code == 200 and "data-piece='carousel'" in page and "data-kit='2026-11-01 Fake beach'" in page and h.get("cache-control") == "no-store", code)
        case("carousel: the served page has no address on the internet, no browser storage, no path", not re.search(r"https?://", page) and "localStorage" not in page and str(target) not in page and "beach-0" not in page)
        st, text = state()
        case("carousel state: the first pick and the current one are the kit's carousel pick", st["ok"] and st["piece"] == "carousel" and st["first"]["nums"] == pick and st["now"]["nums"] == pick and st["rev"] == 0, st.get("now"))
        case("carousel state: at most 20, at least 2, 5 to 8 works best; no job yet", st["limits"] == {"min": 2, "max": 20, "best": [5, 8]} and st["job"] is None and st["happy"] is None, (st["limits"], st["job"]))
        leaks = [w for w in ("/private", "/Volumes", "/Users", ".jpg", ".JPG", ".heic", ".png", ".tif", "beach-", "BEACH-", str(target)) if w in text]
        case("carousel state: no path and no file name anywhere in it", not leaks, leaks)
        stamp = st["stamp"]
        remember()
        before = tree_print(kit)
        car_before = folder_print(car)

        # ---- saving, without the final button ----
        base = {"kit": kit_name, "piece": "carousel", "stamp": stamp, "page": "carouselpg01", "done": False}
        swapped = [pick[1], pick[0]] + pick[2:]
        code, j = post(dict(base, base=0, nums=swapped, marks=["+"] * len(swapped)))
        case("carousel save: a new order is taken, and Longer or Quicker mean nothing here (stored as plain)", code == 200 and j.get("rev") == 1 and j.get("job") is False and now()["nums"] == swapped and set(now()["marks"]) == {""}, (code, j))
        code, j = post(dict(base, base=1, nums=list(range(1, 21))))
        case("carousel save: twenty photos are taken, with no marks sent at all", code == 200 and j.get("rev") == 2 and len(now()["nums"]) == 20, (code, j))
        code, j = post(dict(base, base=2, nums=list(range(1, 22))))
        case("carousel save refuses: a twenty-first photo (400)", code == 400 and j.get("ok") is False and now()["rev"] == 2, (code, j))
        code, j = post(dict(base, base=2, nums=[pick[0]], done=True))
        case("carousel save refuses: the final button with one photo (400)", code == 400 and now()["rev"] == 2, (code, j))
        older_before = sorted(os.listdir(hid / "slides-older"))        # the first build's own record of placing its slides
        case("a save without the final button starts no job and moves no slide", not job_file.exists() and folder_print(car) == car_before and len(older_before) == 1 and tree_print(kit).keys() == before.keys())
        code, out = run(env, "home.py", "pending")
        case("and nothing is waiting for Claude", "ARRANGED" not in out, out[-120:])

        # ---- the final button: reorder, take one out, add one ----
        new_order = [pick[1], pick[0]] + [n for n in pick[2:] if n != pick[3]] + [1]
        wanted = slide_names(new_order)
        code, j = post(dict(base, base=2, nums=new_order, done=True))
        rev = j.get("rev")
        case("the final button: saved, and a job is set to making the slides", code == 200 and j.get("ok") and j.get("job") is True and j.get("same") is False and j.get("line") == "Making your slides..." and rev == 3, (code, j))
        job = wait_job(P, KQ, rev)
        case("the job ends on 'Done. N slides are in your Carousel folder.', for the order the button was pressed on", job == {"state": "done", "line": f"Done. {len(wanted)} slides are in your Carousel folder.", "rev": rev, "count": len(wanted)}, job)
        after = tree_print(kit)
        case("the Carousel folder holds exactly the wanted slides, plus the Canva one and the hand-dropped file", sorted(os.listdir(car)) == sorted(wanted + EXTRA), sorted(os.listdir(car)))
        case("each wanted slide is 1080 x 1350", all(jpeg_size((car / n).read_bytes()) == (1080, 1350) for n in wanted))
        kept = [n for n in wanted if n in car_before]
        made_new = [n for n in wanted if n not in car_before]
        aside = sorted(n for n in car_before if n not in wanted and n not in EXTRA)
        case("a slide that keeps its place and photo is left exactly as it was", kept and all(after["Carousel/" + n] == car_before[n] for n in kept), kept)
        older = [d for d in sorted(os.listdir(hid / "slides-older")) if d not in older_before]
        od = hid / "slides-older" / (older[0] if older else "none")
        got_aside = {n: v for n, v in (folder_print(od) if od.is_dir() else {}).items() if n != "moved.json"}
        case("the earlier slides are in the kit's hidden folder (slides-older, in a folder named for the time), byte for byte", len(older) == 1 and aside and got_aside == {n: car_before[n] for n in aside}, (older, sorted(got_aside)))
        mj = json.loads((od / "moved.json").read_text()) if (od / "moved.json").is_file() else {}
        case("with a record of what moved, written down and marked done", mj.get("state") == "done" and sorted(mj.get("aside", [])) == aside and mj.get("place") == made_new and mj.get("wanted") == wanted and mj.get("picks") == new_order and mj.get("sums") == {n: car_before[n] for n in aside}, {k: v for k, v in mj.items() if k != "sums"})
        new_paths = sorted(set(after) - set(before))
        expect_new = sorted(["Carousel/" + n for n in made_new] + [f".kit/slides-older/{od.name}/{n}" for n in aside]
                            + [f".kit/slides-older/{od.name}/moved.json", ".kit/arrange-job.json", ".kit/arrange-job.lock"])
        case("the files that are new: the new slides, the earlier ones at their new address, and three small records", new_paths == expect_new, [x for x in new_paths if x not in expect_new] + [x for x in expect_new if x not in new_paths])
        case("the files no longer where they were: only the earlier slides (moved, not deleted)", sorted(set(before) - set(after)) == sorted("Carousel/" + n for n in aside), sorted(set(before) - set(after)))
        case("the count of files in the kit went up by exactly the new slides and those three records", len(after) == len(before) + len(made_new) + 3, (len(before), len(after), len(made_new)))
        pics_before = Counter(v for k, v in before.items() if k.lower().endswith((".jpg", ".heic", ".png", ".tif")))
        pics_after = Counter(v for k, v in after.items() if k.lower().endswith((".jpg", ".heic", ".png", ".tif")))
        case("every picture that was in the kit is still in it, the same bytes, as many copies", not (pics_before - pics_after), len(pics_before - pics_after))
        case("the Photos folder: not one photo changed, none added", folder_print(photos_dir) == photos_before)
        case("the Canva slide and the hand-dropped file are untouched", all(after["Carousel/" + n] == car_before[n] for n in EXTRA))
        case("nothing half-made is left in the Carousel folder or the making folder", not [n for n in os.listdir(car) if n.startswith(".")] and os.listdir(hid / "slides-new") == [], os.listdir(hid / "slides-new"))
        rec = json.loads(rec_file.read_text())
        case("the kit's own carousel pick is now their order, and its record of the slides matches", rec["picks"]["carousel"] == new_order and rec["made_pieces"]["carousel"] == wanted and rec["picks"]["reel"], rec["picks"].get("carousel"))
        st, text = state()
        case("the page's state: their order, with the Assistant's first pick kept for Back to my pick", st["now"]["nums"] == new_order and st["first"]["nums"] == pick and st["rev"] == rev and st["happy"] == {"rev": rev}, (st["now"], st["first"], st["rev"]))
        case("the job in the state names no process, no path and no file", set(st["job"]) == {"state", "line", "rev", "count"} and not [w for w in ("/private", ".jpg", "beach-", "pid") if w in text], st["job"])
        code, out = run(env, "home.py", "pending")
        want_line = f"ARRANGED: {kit_name} | carousel | {len(new_order)} photos"
        case("home.py pending prints the ARRANGED line for the carousel", code == 0 and out.strip().splitlines()[-1] == want_line, out[-200:])
        code, h, data = ask(P, "GET", f"/content/{KQ}/Post%20kit.html")
        kit_page = data.decode()
        case("the kit page was written again: it shows the new slides and none of the earlier ones", code == 200 and all(n in kit_page for n in wanted) and not any(n in kit_page for n in aside), [n for n in aside if n in kit_page])
        links = re.findall(r"<a class='arr' href='([^']+)'>(?:Change the photos|Create my reel →|Make a new version →)</a>", kit_page)
        case("the kit page has the reel's link in the Reel section (the reel page, decision 3; her 'Create my reel') and 'Change the photos' in the Carousel section", links == [f"/reel.html?kit={KQ}", f"/arrange.html?kit={KQ}&amp;piece=carousel"], links)
        tags = re.findall(r"<a [^>]*>(?:Change the photos|Create my reel →|Make a new version →)</a>", kit_page)
        case("those are plain links of class 'arr', never 'go' (every 'go' button asks for a folder to be opened)", len(tags) == 2 and all("class='arr'" in t and "go" not in t.split("href")[0] and "data-sub" not in t for t in tags) and "body:not(.live) .arr{display:none}" in kit_page, tags)
        code, h, data = ask(P, "GET", html.unescape(links[1])) if len(links) == 2 else (0, {}, b"")
        case("the Carousel section's link opens the carousel's picker", code == 200 and b"data-piece='carousel'" in data, code)
        code, h, data = ask(P, "GET", html.unescape(links[0])) if len(links) == 2 else (0, {}, b"")
        case("the Reel section's link opens the reel page (her reel maker)", code == 200 and "Put your photos in order".encode() in data, code)
        opened = tree_print(kit)
        case("opening the reel page added only its own lock to the kit (an empty file every writer of its record holds)",
             sorted(set(opened) - set(after)) == [".kit/reel-page.lock"] and all(opened[k] == v for k, v in after.items()), sorted(set(opened) ^ set(after)))
        after = opened
        code, h, data = ask(P, "GET", f"/content/{KQ}/Carousel/{quote(wanted[0])}")
        case("and the kit page's pictures of the new slides load", code == 200 and jpeg_size(data) == (1080, 1350), code)
        case("the posting queue's picture of the carousel was made again from the folder as it is now", thumb.stat().st_mtime_ns > thumb_before and thumb.read_bytes()[:2] == b"\xff\xd8")
        remember()

        # ---- pressed again with nothing changed ----
        times = {k: os.stat(kit / k).st_mtime_ns for k in after if k.startswith("Carousel/") or k.startswith(".kit/slides-older/") or k == ".kit/kit.json"}
        code, j = post(dict(base, base=rev, nums=new_order, done=True))
        case("pressed again with nothing changed: 'Your slides are already in this order.', and no job", code == 200 and j.get("same") is True and j.get("job") is False and j.get("line") == "Your slides are already in this order." and j.get("rev") == rev, (code, j))
        time.sleep(0.6)
        case("and no file's time changed, nothing new was set aside", times == {k: os.stat(kit / k).st_mtime_ns for k in times} and len(os.listdir(hid / "slides-older")) == 2 and sorted(tree_print(kit)) == sorted(after))
        st, text = state()
        case("the state says the same", st["job"] == {"state": "same", "line": "Your slides are already in this order.", "rev": rev, "count": len(new_order)}, st["job"])

        # ---- two presses close together: the slides end as the LAST order pressed ----
        first_o = new_order[::-1]
        second_o = [new_order[2], new_order[0], new_order[1]] + new_order[3:]
        code, ja = post(dict(base, base=rev, nums=first_o, done=True))
        code, jb = post(dict(base, base=ja.get("rev"), nums=second_o, done=True))
        rev = jb.get("rev")
        job = wait_job(P, KQ, rev)
        case("two presses close together: the second is answered with a job at work", jb.get("job") is True and jb.get("line") in ("Making your slides...", "Your slides are already being made. One moment."), jb)
        case("and the slides end as the last order pressed, nothing lost on the way", job.get("state") in ("done", "same") and job.get("rev") == rev and not settled(second_o) and json.loads(rec_file.read_text())["picks"]["carousel"] == second_o, (job, settled(second_o)))
        remember()

        # ---- Claude's apply after the button was pressed, when they have moved photos since and not pressed again ----
        moved = second_o[::-1]
        code, j = post(dict(base, base=rev, nums=moved))
        rev = j.get("rev")
        code, out = run(env, "home.py", "pending")
        case("pressed, then photos moved without pressing again: what is waiting for Claude is still the order the button was pressed on", out.strip().splitlines()[-1] == f"ARRANGED: {kit_name} | carousel | {len(second_o)} photos", out[-160:])
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        lines = out.strip().splitlines()
        case("Claude's apply then makes the order the button was pressed ON, not what was moved afterwards", code == 0 and lines and lines[0] == "Carousel picks: " + ",".join(map(str, second_o)) and not settled(second_o) and json.loads(rec_file.read_text())["picks"]["carousel"] == second_o, (out[-300:], settled(second_o)))
        case("and says so, and what they moved since is still on the page, unmade", any(x.startswith("Page: they have moved photos on the page since they pressed the button") for x in lines) and now()["nums"] == moved and now()["rev"] == rev, (lines, now()))
        code, out = run(env, "home.py", "pending")
        case("and the waiting line is cleared", "ARRANGED" not in out, out[-120:])
        st, text = state()
        case("the page is not told 'Done' for the order it shows (that one was never made)", st["now"]["nums"] == moved and not (st["job"] and st["job"]["rev"] == st["rev"]), (st["job"], st["rev"]))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel", "--as-it-is")
        case("apply --as-it-is (they say 'use it as it is now') makes the order on the page", code == 0 and out.startswith("Carousel picks: " + ",".join(map(str, moved))) and not settled(moved), (out[-200:], settled(moved)))
        remember()

        # ---- Claude's own command, cut off at each stop and finished by the next run ----
        order = second_o
        for stop, untouched in (("after-make", True), ("after-journal", True), ("mid-aside", False), ("after-aside", False), ("mid-place", False), ("after-place", False), ("after-record", False)):
            order = order[1:] + order[:1]
            code, j = post(dict(base, base=rev, nums=order))
            rev = j.get("rev")
            car_mid = folder_print(car)
            code, out = run(dict(env, ARRANGE_TEST_STOP=stop), "arrange.py", "apply", str(kit), "--piece", "carousel")
            still = folder_print(car) == car_mid
            case(f"cut off at '{stop}': the run stops dead" + (", and the Carousel folder is exactly as it was" if untouched else ", and nothing is lost"), code == 9 and (still if untouched else True) and not nothing_lost(), (code, nothing_lost()))
            remember()
            code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
            lines = out.strip().splitlines()
            case(f"cut off at '{stop}': the next run finishes it: the order printed, the slides right, nothing twice, nothing lost", code == 0 and lines and lines[0] == "Carousel picks: " + ",".join(map(str, order)) and not settled(order), (out[-200:], settled(order)))
            case(f"cut off at '{stop}': and no slide that was made and never put in is left behind in the making folder", os.listdir(hid / "slides-new") == [], os.listdir(hid / "slides-new"))
            remember()
        code, out = run(env, "home.py", "pending")
        case("Claude's apply clears the line that was waiting", "ARRANGED" not in out, out[-120:])
        st, text = state()
        case("and an open page is told the same true thing: done, for the order it shows", st["job"]["state"] in ("done", "same") and st["job"]["rev"] == st["rev"] == rev and st["happy"] is None, (st["job"], st["rev"]))
        # a run with nothing to change
        whole = tree_print(kit)
        times = {k: os.stat(kit / k).st_mtime_ns for k in whole if k.startswith("Carousel/") or k.startswith(".kit/slides-older/") or k in (".kit/kit.json", ".kit/arrange.json", ".kit/Post kit.html")}
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("apply again with nothing to change: says so, and not one of those files is touched", code == 0 and "were already in this order. Nothing was changed." in out and times == {k: os.stat(kit / k).st_mtime_ns for k in times}, out)
        code, out = run(env, "kit.py", "build", kit_name)
        case("kit.py build with nothing to change leaves the slides alone too", code == 0 and f"Carousel: {len(order)} made." in out and "set aside" not in out and {k: v for k, v in tree_print(kit).items() if k.startswith("Carousel/")} == {k: v for k, v in whole.items() if k.startswith("Carousel/")}, out[:200])
        whole = tree_print(kit)
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel", "--dry")
        case("apply --dry prints the order and writes nothing", code == 0 and out.startswith("Carousel picks: ") and tree_print(kit) == whole, out)

        # ---- Claude's apply at work, and the page's button pressed on a newer order meanwhile ----
        code, j = post(dict(base, base=rev, nums=order[::-1]))
        rev = j.get("rev")
        newer = order[1:] + order[:1]
        body = json.dumps(dict(base, base=rev, nums=newer, done=True))
        r = subprocess.run([PY, "-c", CAR_RACE, str(SCRIPTS), str(P), kit_name, body], capture_output=True, text=True, env=env, timeout=120)
        try:
            got = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            got = {"error": (r.stdout + r.stderr)[-300:]}
        ans = got.get("answer") or {}
        case("the button pressed while Claude's apply is at work: the page is told its slides are already being made, and no second job starts beside it",
             got.get("code") == 200 and ans.get("job") is True and ans.get("line") == "Your slides are already being made. One moment." and got.get("apply", [1])[0] == 0, got)
        rev = ans.get("rev")
        job = wait_job(P, KQ, rev)
        case("and apply hands the newer order on: its slides are made next, by the page's own job", job.get("state") == "done" and job.get("rev") == rev and not settled(newer) and json.loads(rec_file.read_text())["picks"]["carousel"] == newer, (job, settled(newer)))
        code, out = run(env, "arrange.py", "waiting")
        case("and that newer order is still waiting for Claude (apply did not clear what arrived after it began)", out.strip() == f"ARRANGED: {kit_name} | carousel | {len(newer)} photos", out)
        code, out = run(env, "arrange.py", "took", kit_name, "--piece", "carousel")
        remember()
        order = newer
        r = subprocess.run([PY, "-c", NO_LOCKS, str(SCRIPTS), kit_name], capture_output=True, text=True, env=env, timeout=60)
        case("on a drive with no locks, a job is told from its process: at work, ended, too old to believe, just queued, finished", r.stdout.strip() == "[true, false, false, true, false]", (r.stdout + r.stderr)[-200:])

        # ---- the page's own job killed half way, then the button pressed again ----
        srv.stop()
        once = work / "stop-once"
        srv = Server(dict(env, ARRANGE_TEST_STOP="mid-place", ARRANGE_TEST_STOP_ONCE=str(once)), port + 4)
        P = srv.start()
        order = order[::-1]
        code, j = post(dict(base, base=rev, nums=order, done=True))
        rev = j.get("rev")
        job = wait_job(P, KQ, rev)
        case("the page's job killed half way: the page is told so in plain words, with what to do", once.exists() and job == {"state": "problem", "line": arrange.JOB_STOPPED, "rev": rev, "count": len(order)}, job)
        case("at that moment a move is written down as unfinished, and nothing is lost", "moving" in journals() and not nothing_lost(), (journals(), nothing_lost()))
        remember()
        code, j = post(dict(base, base=rev, nums=order, done=True))
        case("the button pressed again: a job is started again", code == 200 and j.get("job") is True and j.get("rev") == rev, (code, j))
        job = wait_job(P, KQ, rev)
        case("and it finishes: Done, the slides right, nothing twice, nothing lost", job.get("state") == "done" and job.get("line") == f"Done. {len(order)} slides are in your Carousel folder." and not settled(order), (job, settled(order)))
        remember()

        # ---- the page server stopped the moment the button is pressed ----
        order = order[2:] + order[:2]
        code, j = post(dict(base, base=rev, nums=order, done=True))
        rev = j.get("rev")
        srv.stop()                                         # at once; the job is a process of its own
        srv = Server(env, port + 6)
        P = srv.start()
        job = wait_job(P, KQ, rev)
        case("the page server stopped in the middle and started again on another port: the job finished by itself", j.get("job") is True and job.get("state") == "done" and job.get("rev") == rev and not settled(order), (job, settled(order)))
        remember()

        # ---- a picked photo gone missing ----
        spare = next(n for n in range(2, 25) if n not in order)
        aside_dir = work / "carousel-aside"
        aside_dir.mkdir(exist_ok=True)
        shutil.move(str(photos_dir / name_of[spare]), str(aside_dir / name_of[spare]))
        car_mid = folder_print(car)
        picks_mid = json.loads(rec_file.read_text())["picks"]["carousel"]
        with_spare = order[:-1] + [spare]
        code, j = post(dict(base, base=rev, nums=with_spare, done=True))
        rev = j.get("rev")
        job = wait_job(P, KQ, rev)
        case("a picked photo gone missing: the line names the photo and says the Carousel folder was left as it was",
             job == {"state": "problem", "line": f"Couldn't make the slides: photo {spare} can't be read. Is the drive plugged in? Your Carousel folder was left as it was.", "rev": rev, "count": len(with_spare)}, job)
        case("and it was: the folder is byte for byte the same, and the kit's own pick is unchanged", folder_print(car) == car_mid and json.loads(rec_file.read_text())["picks"]["carousel"] == picks_mid and all(s_ == "done" for s_ in journals()))
        shutil.move(str(aside_dir / name_of[spare]), str(photos_dir / name_of[spare]))
        code, j = post(dict(base, base=rev, nums=with_spare, done=True))
        job = wait_job(P, KQ, rev)
        case("the photo put back and the button pressed again: Done", j.get("job") is True and job.get("state") == "done" and not settled(with_spare), (job, settled(with_spare)))
        remember()
        order = with_spare

        # ---- sips failing while a slide is made: nothing in the Carousel folder changes ----
        car_mid = folder_print(car)
        code, out = run(env, "kit.py", "picks", kit_name, "--carousel", f"{order[1]},{order[0]},{order[2]}")
        code, out = run(shim_env, "kit.py", "build", kit_name)
        case("sips dying while a new slide is made: build says so, and the Carousel folder is left as it was", "could not make the carousel slides" in out and "left as it was" in out and folder_print(car) == car_mid, out[:300])

        # ---- a fresh pick from Claude: the new slides are made, the earlier ones set aside, none left out of date ----
        code, out = run(env, "kit.py", "build", kit_name)
        fresh_pick = [order[1], order[0], order[2]]
        case("a fresh pick from Claude, then kit.py build: new slides made, earlier ones set aside, none left behind out of date", code == 0 and "Carousel: 3 made. (" in out and "set aside in the kit's hidden folder, not deleted.)" in out and not settled(fresh_pick), (out[:200], settled(fresh_pick)))
        st, text = state()
        last = (json.loads(arr.read_text())["carousel"].get("earlier") or [{}])[-1]
        case("the page follows the fresh pick, and their own order is kept, not thrown away", st["now"]["nums"] == fresh_pick and st["first"]["nums"] == fresh_pick and last.get("nums") == order and last.get("why") == "a fresh pick replaced it", (st["now"], last))
        remember()

        # ---- a kit that has Canva slides: Claude is told, and so is the page ----
        rec = json.loads(rec_file.read_text())
        rec["canva"] = {"carousel": {"design_id": "DAtest", "edit_url": "", "template": "T"}}       # this check's own kit record
        rec_file.write_text(json.dumps(rec, indent=1))
        st, text = state()
        code, j = post(dict(base, base=st["rev"], nums=fresh_pick[::-1]))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        st, text = state()
        case("a kit with Canva slides: apply says they still show the earlier photos, and the page is told too", code == 0 and "Canva: this kit's Canva slides were made from the earlier photos" in out and st["canva"] is True and not settled(fresh_pick[::-1]), (out, settled(fresh_pick[::-1])))

        # ---- the whole time ----
        case("carousel: the Photos folder at the end: not one photo changed, none added", folder_print(photos_dir) == photos_before)
        case("carousel: the Canva slide and the hand-dropped file at the end: untouched", all(folder_print(car).get(n) == car_before[n] for n in EXTRA))
        case("carousel: every picture ever in the kit is still in it, as many copies as there ever were (set aside, never deleted)", not nothing_lost() and sum(floor.values()) > 60, (sum(floor.values()), nothing_lost()))
        case("carousel: no scratch file was left in the Carousel folder", not [n for n in os.listdir(car) if n.startswith(".")])
        log_text = (studio / "arrange.log").read_text() if (studio / "arrange.log").exists() else ""
        case("carousel: the log names each job and how it ended, and nothing failed inside a route or a job", "slide job for 2026-11-01 Fake beach: done" in log_text and " failed: " not in log_text, [x for x in log_text.splitlines() if " failed: " in x][:2])

        # ---- the photos numbered again after the button was pressed: the numbers it was pressed on mean other photos now ----
        st, text = state()
        pressed = [fresh_pick[2], fresh_pick[0], fresh_pick[1]]
        code, j = post(dict(base, base=st["rev"], nums=pressed, done=True))
        job = wait_job(P, KQ, j.get("rev"))
        slides_then = sorted(n for n in os.listdir(car) if n not in EXTRA)
        shutil.copyfile(photos_dir / name_of[1], photos_dir / "aaa-extra.jpg")       # this check's own extra photo: it sorts first, so every number moves along by one
        code, out = run(env, "kit.py", "sheet", kit_name)
        code, out = run(env, "arrange.py", "apply", str(kit), "--piece", "carousel", "--job")
        st, text = state()
        case("photos numbered again after the button was pressed: a job makes the same photos' slides (found again by name), never the old numbers' photos",
             job.get("state") == "done" and code == 0 and sorted(n for n in os.listdir(car) if n not in EXTRA) == slides_then and st["now"]["nums"] == [n + 1 for n in pressed]
             and json.loads(rec_file.read_text())["picks"]["carousel"] == [n + 1 for n in pressed] and not nothing_lost(), (job, code, st["now"], sorted(os.listdir(car))))
    finally:
        srv.stop()
        subprocess.run(["pkill", "-f", f"arrange.py apply {kit}"], capture_output=True)      # a job of this check's own, if one is somehow still at work


# ---------- stage 2, the fix pass: faults the reviewers found, each with a case that fails without its fix ----------

# A drive that keeps accented letters its own way (an HFS+ photo drive lists "ë" as "e" followed by its accent,
# whatever was typed): every folder listing in this process comes back that way, as it does on such a drive.
NFD_DRIVE = r"""
import json, os, sys, unicodedata
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import kit
real = os.listdir
os.listdir = lambda *a: [unicodedata.normalize('NFD', n) if isinstance(n, str) else n for n in real(*a)]
res = kit.rebuild_carousel(Path(sys.argv[2]), json.loads(sys.argv[3]))
print(json.dumps({k: res.get(k) for k in ('state', 'why', 'made', 'aside', 'photos', 'files', 'detail')}))
"""

# kit.rebuild_carousel straight, for an order given by hand (no page, no pick written)
REBUILD = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import kit
res = kit.rebuild_carousel(Path(sys.argv[2]), json.loads(sys.argv[3]))
print(json.dumps({k: res.get(k) for k in ('state', 'why', 'made', 'aside', 'photos', 'files', 'detail', 'put_back', 'left')}))
"""

# A save from the carousel's page, without the final button (and so without a job being started).
CAR_SAVE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import arrange
kit = arrange.kit_by_name(sys.argv[2])
data, p = arrange.sync(kit, 'carousel')
nums = json.loads(sys.argv[3])
body = {'kit': sys.argv[2], 'piece': 'carousel', 'stamp': p['stamp'], 'base': p['now']['rev'], 'page': 'fixespage01', 'nums': nums, 'done': False}
code, out = arrange.save_from_page(body)
print(json.dumps([code, out.get('rev')]))
"""

# kit.py build, with the page's order made into slides (start to finish, as a process of its own) while build
# is in the middle of sizing the single posts. build read the kit record before that; it must not put that
# older copy back over what was written meanwhile.
BUILD_MID = r"""
import contextlib, io, json, subprocess, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import kit as kit_mod
kit = Path(sys.argv[2])
real, out = kit_mod.single, {}
def single(a, b):
    if 'meanwhile' not in out:
        r = subprocess.run([sys.executable, str(Path(sys.argv[1]) / 'arrange.py'), 'apply', str(kit), '--piece', 'carousel'], capture_output=True, text=True)
        out['meanwhile'] = [r.returncode, (r.stdout + r.stderr).strip()[-300:]]
    return real(a, b)
kit_mod.single = single
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    out['build'] = kit_mod.build(kit)
out['said'] = buf.getvalue().strip()[-400:]
print(json.dumps(out))
"""

# The page's slide job, with kit.py build arriving at the worst moment: the new slides are in the folder and
# the order has not yet been written down as the kit's own pick. build must wait for that, not go by the old pick.
JOB_THEN_BUILD = r"""
import json, subprocess, sys, time
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import arrange
kit = arrange.kit_by_name(sys.argv[2])
real, out, held = arrange._take_carousel, {}, []
def slow_take(k, nums):
    if not held:
        b = subprocess.Popen([sys.executable, str(Path(sys.argv[1]) / 'kit.py'), 'build', str(k)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        held.append(b)
        time.sleep(4)
        out['build_waited'] = b.poll() is None
    return real(k, nums)
arrange._take_carousel = slow_take
out['job'] = arrange.run_carousel_job(kit)
out['build'] = [x for x in held[0].communicate(timeout=200)[0].splitlines() if x.startswith('Carousel') or x.startswith('(')] if held else None
print(json.dumps(out))
"""

# The kit's folder is not where it was (renamed, or its drive gone) while a job is at work: nothing of the
# Assistant's may make a folder of that name at the old address.
GHOST = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import arrange, kit as kit_mod
ghost, out = Path(sys.argv[2]), {}
try:
    arrange.write_job(ghost, 'problem', 'x', 3)
    out['status'] = 'written'
except OSError:
    out['status'] = 'refused'
try:
    with arrange.locked(arrange.kit_lock(ghost)):
        out['lock'] = 'went on without one'
    with arrange._job_hold(ghost, 0.2) as mine:
        out['hold'] = bool(mine)
    out['previews'] = arrange.make_previews(ghost)['made']
    res = kit_mod.rebuild_carousel(ghost, [1, 2])
    out['rebuild'] = [res.get('state'), res.get('why')]
except Exception as e:
    out['error'] = e.__class__.__name__ + ': ' + str(e)[:120]
out['there'] = ghost.exists()
print(json.dumps(out))
"""

# The posting queue's picture of the carousel being made again, with a piece marked "ready to post" from the
# posting page at just that moment (while the picture is being made). That mark must still be there afterwards.
POSTING_MID = r"""
import json, subprocess, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import kit as kit_mod
import posting_queue as pq
real, out = kit_mod.fit, {}
def fit(src, dst, box, pad=None):
    if 'ready' not in out:
        r = subprocess.run([sys.executable, str(Path(sys.argv[1]) / 'posting_queue.py'), 'ready', sys.argv[3]], capture_output=True, text=True)
        out['ready'] = [r.returncode, (r.stdout + r.stderr).strip()[-200:]]
    return real(src, dst, box, pad)
kit_mod.fit = fit
out['refreshed'] = kit_mod._refresh_posting(Path(sys.argv[2]))
out['status'] = next(x['status'] for x in pq.load()['pieces'] if x['id'] == sys.argv[3])
print(json.dumps(out))
"""

# A pretend sips that cannot write a picture from ONE photo (named in SIPS_FAIL_ON) and is the real one otherwise.
SIPS_ONE_FAILS = """#!/bin/sh
case " $* " in
  *"$SIPS_FAIL_ON"*" --out "*) exit 1 ;;
  *) exec /usr/bin/sips "$@" ;;
esac
"""


def check_carousel_fixes(work, port):
    """Faults found in review of the carousel's slides, on a kit of its own: a photo with an accented name on
    a drive that keeps accents its own way; a name clash found before anything moves, and a move that cannot
    be finished put back; kit.py build and the page's job on the kit record; scratch not left behind; a kit
    folder that has gone away; the posting queue; a folder that can't be written; the Canva line; a job that
    fails before it has read its order; an order longer than a carousel holds."""
    import unicodedata
    target = work / "fake-fixes"
    r = subprocess.run([PY, str(ROOT / "tests" / "fake_kit.py"), str(target), "--photos", "22"], capture_output=True, text=True, timeout=600)
    if not case("fixes: a pretend kit of its own was made", r.returncode == 0, (r.stdout + r.stderr)[-300:]):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    env.pop("ARRANGE_TEST_STOP", None)
    env.pop("ARRANGE_TEST_STOP_ONCE", None)
    kit_name = "2026-11-01 Fake beach"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    photos_dir, car, hid = kit / "Photos", kit / "Carousel", kit / ".kit"
    rec_file, arr, job_file = hid / "kit.json", hid / "arrange.json", hid / "arrange-job.json"
    aside_dir = work / "fixes-aside"                      # where this check puts its own stand-in files when it is done with them
    aside_dir.mkdir(exist_ok=True)
    nfc = lambda t: unicodedata.normalize("NFC", t)
    sys.path.insert(0, str(SCRIPTS))
    import importlib
    arrange = importlib.import_module("arrange")          # only for its words

    # this check's own extra photo, with an accented letter in its name, and the photos numbered again
    accent = "Zoë-day.jpg"
    shutil.copyfile(photos_dir / "beach-001.jpg", photos_dir / accent)
    code, out = run(env, "kit.py", "sheet", kit_name)
    sheet = json.loads((hid / "sheet.json").read_text())["photos"]
    n_of = {nfc(Path(x["file"]).name): x["n"] for x in sheet}
    stem_of = {x["n"]: nfc(Path(x["file"]).stem) for x in sheet}
    Z = n_of.get(nfc(accent))
    p = {i: n_of[f"beach-{i:03d}.jpg"] for i in (1, 2, 3, 9, 10, 11, 12, 13)}
    if not case("fixes: the photo with an accent in its name is on the numbered list", bool(Z) and len(sheet) == 23, (Z, len(sheet))):
        return
    photos_before = folder_print(photos_dir)

    def slide_names(order):
        return [f"Slide {i:02d} ({stem_of[n]}).jpg" for i, n in enumerate(order, 1)]

    def plain(folder=None):
        """The plain slides in the Carousel folder (or another), names in one normal form."""
        d = folder or car
        return sorted(nfc(n) for n in os.listdir(d) if n.endswith(".jpg") and not n.startswith(".")) if d.is_dir() else []

    def journals():
        d = hid / "slides-older"
        return [json.loads((d / x / "moved.json").read_text())["state"] for x in sorted(os.listdir(d))] if d.is_dir() else []

    def making():
        return sorted(os.listdir(hid / "slides-new")) if (hid / "slides-new").is_dir() else []

    def kept():
        """Every picture in the Carousel folder and in the set-aside folders, counted by its bytes."""
        return Counter(v for k, v in tree_print(kit).items() if k.endswith(".jpg") and (k.startswith("Carousel/") or k.startswith(".kit/slides-older/")))

    def record():
        return json.loads(rec_file.read_text())

    def script(src, *args, env_=None):
        r = subprocess.run([PY, "-c", src, str(SCRIPTS), *[a if isinstance(a, str) else json.dumps(a) for a in args]], capture_output=True, text=True, env=env_ or env, timeout=300)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"error": (r.stdout + r.stderr)[-400:]}

    def page_save(order):
        return script(CAR_SAVE, kit_name, order)

    # ---- more photos than a carousel holds: stopped where the pick is made ----
    too_many = [x["n"] for x in sheet][:21]
    code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, too_many)))
    case("kit.py picks refuses a carousel of 21 photos, and says Instagram's limit", code == 1 and "STOP: Instagram allows up to 20 photos in a carousel, and this pick has 21." in out, out[-200:])
    O1 = [Z, p[1], p[2], p[3]]
    code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, O1)), "--singles", f"{p[1]},{p[2]}")
    case("fixes: the kit's carousel pick has the accented photo first", code == 0 and record()["picks"]["carousel"] == O1, out[-200:])

    # ---- a photo with an accented name, on a drive that keeps accents its own way ----
    got = script(NFD_DRIVE, str(kit), O1)
    case("accented photo name, drive that lists accents its own way: the slides are made (not 'couldn't be sized')", got.get("state") == "done" and got.get("made") == 4 and plain() == sorted(slide_names(O1)), (got, plain()))
    case("and nothing is left stranded in the making folder", making() == [], making())
    got = script(NFD_DRIVE, str(kit), O1)
    case("the same again: nothing to change, and it says so", got.get("state") == "same" and got.get("made") == 0, got)
    O2 = [p[1], Z, p[2]]
    got = script(NFD_DRIVE, str(kit), O2)
    older = sorted(os.listdir(hid / "slides-older"))
    case("a new order there: the earlier slides (the accented one too) are set aside, the kept one stays, nothing lost",
         got.get("state") == "done" and got.get("made") == 2 and got.get("aside") == 3 and plain() == sorted(slide_names(O2))
         and nfc("Slide 01 (Zoë-day).jpg") in plain(hid / "slides-older" / older[-1]) and all(s_ == "done" for s_ in journals()), (got, plain(), journals()))
    code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, O2)))
    code, out = run(env, "kit.py", "build", kit_name)
    case("fixes: kit.py build agrees (the pick and the slides are the same order), and the singles are made", code == 0 and "Carousel: 3 made." in out and "set aside" not in out and "Singles: 2 made." in out, out[:300])

    # ---- kit.py build and the page's job, both at the kit record ----
    code, out = run(env, "kit.py", "picks", kit_name, "--singles", f"{p[1]},{p[2]},{p[3]},{p[9]}")      # two more singles for build to size
    X = [p[2], Z, p[1]]
    case("fixes: an order saved from the page (no button)", page_save(X) and record()["picks"]["carousel"] == O2, record()["picks"]["carousel"])
    got = script(BUILD_MID, str(kit))
    rec = record()
    case("the page's order made into slides while kit.py build is sizing singles: build does not put the older pick back",
         got.get("build") == 0 and (got.get("meanwhile") or [1])[0] == 0 and rec["picks"]["carousel"] == X and [nfc(n) for n in rec["made_pieces"]["carousel"]] == slide_names(X) and plain() == sorted(slide_names(X)),
         (got, rec["picks"]["carousel"], rec["made_pieces"].get("carousel")))
    case("and build's own work is in the record too: all four singles", len(rec["made_pieces"].get("singles") or []) == 4 and len(plain(kit / "Singles")) == 4, rec["made_pieces"].get("singles"))
    st_after = json.loads(arr.read_text())["carousel"]
    case("and the page's record still calls that order theirs (not a fresh pick of Claude's)", st_after["now"]["nums"] == X and st_after["now"].get("by") == "you", st_after["now"])
    Y = [Z, p[2], p[1], p[3]]
    page_save(Y)
    got = script(JOB_THEN_BUILD, kit_name)
    rec = record()
    case("kit.py build arriving just as the job has put its new slides in: build waits for the pick to be written",
         got.get("build_waited") is True and got.get("job") == 0 and got.get("build") == ["Carousel: 4 made."], got)
    case("and the folder, the pick and the page's line all say the same order afterwards", rec["picks"]["carousel"] == Y and plain() == sorted(slide_names(Y))
         and (json.loads(job_file.read_text()).get("state"), json.loads(job_file.read_text()).get("line")) == ("done", "Done. 4 slides are in your Carousel folder.") and all(s_ == "done" for s_ in journals()),
         (rec["picks"]["carousel"], plain(), json.loads(job_file.read_text())))

    # ---- the posting queue: a mark made while the carousel's picture is re-made is not lost ----
    code, out = run(env, "posting_queue.py", "add", "--kit", kit_name)
    posting = json.loads((studio / "posting.json").read_text())
    single_id = next(x["id"] for x in posting["pieces"] if x["kind"] == "single")
    got = script(POSTING_MID, str(kit), single_id)
    case("a piece marked ready to post while the carousel's picture is being re-made stays ready to post", got.get("refreshed") is True and (got.get("ready") or [1])[0] == 0 and got.get("status") == "green", got)
    code, out = run(env, "posting_queue.py", "unready", single_id)

    # ---- scratch is not left behind ----
    shim = work / "shim-one"
    shim.mkdir(exist_ok=True)
    (shim / "sips").write_text(SIPS_ONE_FAILS)
    os.chmod(shim / "sips", 0o755)
    car_mid, kept_mid = folder_print(car), kept()
    W = [p[9], p[10], p[11], p[12]]
    got = script(REBUILD, str(kit), W, env_=dict(env, PATH=f"{shim}:{os.environ.get('PATH', '/usr/bin:/bin')}", SIPS_FAIL_ON="beach-010"))
    case("sips failing on one photo of four: the problem names that photo, and the Carousel folder is as it was", got.get("state") == "problem" and got.get("why") == "make" and got.get("photos") == [p[10]] and folder_print(car) == car_mid, got)
    case("and the three slides that did get made are not left behind in the making folder", making() == [], making())
    gone = subprocess.Popen([PY, "-c", "pass"])
    gone.wait()
    dead, alive = kit / "Singles" / f".part-{gone.pid}-Single 09 (x).jpg", kit / "Singles" / f".part-{os.getpid()}-Single 09 (y).jpg"
    dead.write_bytes(b"this check's own stand-in for a half-made picture left by a run that was killed")
    alive.write_bytes(b"this check's own stand-in for a picture a run that is still alive is writing")
    code, out = run(env, "kit.py", "build", kit_name)
    case("a half-made scratch picture left in Singles by a run that was killed is cleared by the next build; one whose run is alive is not", code == 0 and not dead.exists() and alive.exists() and len(plain(kit / "Singles")) == 4, (dead.exists(), alive.exists()))
    shutil.move(str(alive), str(aside_dir / "alive.part"))

    # ---- a name clash is found BEFORE anything moves (a drive that ignores capitals) ----
    ignores_caps = (car / slide_names(Y)[0].upper()).exists()
    V = [p[9], p[2], Z]
    stranger = "slide 01 (BEACH-009).jpg"                 # a file of the photographer's own: not a slide of this shoot by its name, and a new slide's name to this drive
    if not ignores_caps:
        print("      (this drive tells capitals apart, so a clash of names that differ only in capitals cannot happen here: those cases are not run)", flush=True)
    else:
        (car / stranger).write_bytes(b"a file of the photographer's own, dropped in the Carousel folder")
        page_save(V)
        car_mid, kept_mid, older_mid = folder_print(car), kept(), sorted(os.listdir(hid / "slides-older"))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("a file in the way of a new slide's name: apply stops BEFORE moving anything, and names the file",
             code == 1 and f'STOP: could not make the carousel slides: "{stranger}" in the Carousel folder has a name a new slide needs' in out and "The Carousel folder was left as it was." in out and "Traceback" not in out, out[-400:])
        case("and it was: the Carousel folder byte for byte, nothing set aside, nothing made, no move left unfinished",
             folder_print(car) == car_mid and sorted(os.listdir(hid / "slides-older")) == older_mid and making() == [] and all(s_ == "done" for s_ in journals()), (plain(), journals(), making()))
        code, out = run(env, "arrange.py", "apply", str(kit), "--piece", "carousel", "--job")
        job = json.loads(job_file.read_text())
        case("the page's own job says the same in plain words, with no file name", code == 1 and job.get("state") == "problem" and job.get("line") == arrange.IN_THE_WAY == "Couldn't make the slides: a file in your Carousel folder has a name one of the new slides needs. Your Carousel folder was left as it was. Tell Claude and it'll sort it out." and folder_print(car) == car_mid, job)

        # ---- a move that cannot be finished is put back, never left half way for good ----
        shutil.move(str(car / stranger), str(aside_dir / stranger))
        car_clean = folder_print(car)
        code, out = run(dict(env, ARRANGE_TEST_STOP="after-aside"), "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("fixes: a run cut off with the earlier slides set aside and the new ones not yet in", code == 9 and "moving" in journals() and plain() == [nfc(n) for n in slide_names(Y) if nfc(n) in [nfc(m) for m in slide_names(V)]], (code, journals(), plain()))
        shutil.copyfile(aside_dir / stranger, car / stranger)          # the file turns up in the way while the move is half done
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("a file turned up in the way of a half-done move: the next run puts the earlier slides back and says so, naming the file",
             code == 1 and f'STOP: could not change the carousel slides: "{stranger}" is in the Carousel folder under a name a new slide needs. The earlier slides were put back, so the Carousel folder is as it was.' in out and "Traceback" not in out, out[-400:])
        case("and it is: every earlier slide back under its own name, byte for byte; the move is closed as 'undone'; nothing stranded, nothing lost",
             {k: v for k, v in folder_print(car).items() if k != stranger} == car_clean and journals()[-1] == "undone" and "moving" not in journals() and making() == [] and not (kept_mid - kept()),
             (plain(), journals(), making()))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("run again with the file still there: the same plain stop, and still nothing moved", code == 1 and "has a name a new slide needs" in out and {k: v for k, v in folder_print(car).items() if k != stranger} == car_clean and "moving" not in journals(), out[-300:])
        shutil.move(str(car / stranger), str(aside_dir / (stranger + ".2")))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("the file moved out of the way: the same command now finishes", code == 0 and plain() == sorted(slide_names(V)) and record()["picks"]["carousel"] == V and "moving" not in journals(), (out[-300:], plain()))

    # ---- three more things that used to stop a move for good, all in one cut-off move ----
    E1 = [p[10], p[11], p[12]]                            # every slide new, every earlier one to be set aside
    page_save(E1)
    code, out = run(dict(env, ARRANGE_TEST_STOP="after-journal"), "arrange.py", "apply", kit_name, "--piece", "carousel")
    moving_dirs = [d for d in sorted(os.listdir(hid / "slides-older")) if json.loads((hid / "slides-older" / d / "moved.json").read_text())["state"] == "moving"]
    if case("fixes: a run cut off with its move written down and nothing moved yet", code == 9 and len(moving_dirs) == 1, (code, moving_dirs)):
        od = hid / "slides-older" / moving_dirs[0]
        mj = json.loads((od / "moved.json").read_text())
        a0, a1 = mj["aside"][0], mj["aside"][1]
        (od / a0).write_bytes(b"this check's own file: something else already has that name in the set-aside folder")
        with open(car / a1, "ab") as f:
            f.write(b"this check's own change: the slide was saved over by hand between the record and the move")
        sum_a0, sum_a1 = hashlib.sha256((car / a0).read_bytes()).hexdigest(), hashlib.sha256((car / a1).read_bytes()).hexdigest()
        shutil.move(str(hid / "slides-new" / moving_dirs[0] / mj["place"][0]), str(aside_dir / "a-new-slide-taken-away.jpg"))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        mj = json.loads((od / "moved.json").read_text())
        case("a name already taken in the set-aside folder, a slide changed by hand, a new slide gone: the move is put back and made afresh in the same run",
             code == 0 and plain() == sorted(slide_names(E1)) and record()["picks"]["carousel"] == E1 and "moving" not in journals() and making() == [], (out[-300:], plain(), journals(), making()))
        case("the first move's record is closed as 'undone' and says what it met", mj.get("state") == "undone" and list(mj.get("aside_to") or {}) == [a0] and mj.get("differs") == [a1], {k: mj.get(k) for k in ("state", "aside_to", "differs", "blocked_by")})
        have = kept()
        case("nothing lost on the way: the slide changed by hand is kept as it was changed, and the one whose name was taken is kept too", have[sum_a0] >= 1 and have[sum_a1] >= 1 and (od / a0).read_bytes().startswith(b"this check's own file"), (have[sum_a0], have[sum_a1]))

    # ---- a folder that can't be written: a plain stop, never an error full of paths ----
    now_order = record()["picks"]["carousel"]
    U = [Z, p[9]] if now_order != [Z, p[9]] else [p[9], Z]
    page_save(U)
    kept_mid = kept()
    os.chmod(car, 0o555)
    try:
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
    finally:
        os.chmod(car, 0o755)
    case("the Carousel folder can't be written to: apply stops in plain words, says nothing was lost, and shows no error or path",
         code == 1 and "STOP: the carousel's slides were not finished: a folder in this kit can't be written to. Nothing was lost; run this again to finish." in out and "Traceback" not in out and str(target) not in out and not (kept_mid - kept()), out[-400:])
    code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
    case("writable again: the same command finishes what was begun", code == 0 and plain() == sorted(slide_names(U)) and all(s_ in ("done", "undone") for s_ in journals()) and not (kept_mid - kept()), (out[-300:], plain(), journals()))

    # ---- the kit's folder gone while a job is at work: no look-alike is made at its old address ----
    ghost = kit.parent / "2026-11-01 Gone away"
    got = script(GHOST, str(ghost))
    case("a kit folder that is not there: nothing of the Assistant's makes a folder of that name", got.get("there") is False and not ghost.exists() and got.get("status") == "refused" and got.get("hold") is True and (got.get("rebuild") or [None])[0] == "problem" and "error" not in got, got)

    srv = Server(env, port)
    try:
        P = srv.start()
        print(f"      (fixes: page server on port {P}, STUDIO_HOME={studio})", flush=True)
        J = {"Content-Type": "application/json"}

        def post(body):
            code, h, data = ask(P, "POST", "/arrange", body=json.dumps(body).encode(), headers=J)
            try:
                return code, json.loads(data)
            except ValueError:
                return code, {}

        def state():
            code, h, data = ask(P, "GET", f"/arrange-state?kit={KQ}&page=carousel")
            return json.loads(data)

        st = state()
        base = {"kit": kit_name, "piece": "carousel", "stamp": st["stamp"], "page": "fixespage02", "done": False}

        # ---- the Canva line is only shown while it is true ----
        code, out = run(env, "canva_kit.py", "note", kit_name, "--piece", "carousel", "--design-id", "DAfixes", "--edit-url", "", "--template", "T")
        st = state()
        case("Canva slides just made from the order as it is: the page is not told they show old photos", code == 0 and st["canva"] is False and st["now"]["nums"] == U, (out[-120:], st["canva"]))
        N1 = [p[9], Z, p[1]]
        code, j = post(dict(base, base=st["rev"], nums=N1, done=True))
        job = wait_job(P, KQ, j.get("rev"))
        st = state()
        case("the order changed on the page after that: now the page is told the Canva slides show the old photos", job.get("state") == "done" and st["canva"] is True and plain() == sorted(slide_names(N1)), (job, st["canva"]))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("Claude's apply, with the slides already made by the page: it still prints the Canva line, so the question gets asked",
             code == 0 and "were already in this order. Nothing was changed." in out and "Canva: this kit's Canva slides were made from the earlier photos and still show them." in out, out[-300:])
        st = state()
        case("and the page still has it to show beside 'already in this order'", st["canva"] is True and st["job"]["state"] == "same" and st["job"]["rev"] == st["rev"], (st["canva"], st["job"]))
        code, out = run(env, "canva_kit.py", "note", kit_name, "--piece", "carousel", "--design-id", "DAfixes2", "--edit-url", "", "--template", "T")
        st = state()
        case("the Canva carousel filled again from the new order: the line is gone, for the page and for Claude", st["canva"] is False and st["job"]["rev"] == st["rev"], (st["canva"], st["job"]))
        code, out = run(env, "arrange.py", "apply", kit_name, "--piece", "carousel")
        case("and apply no longer prints it", code == 0 and "Canva:" not in out, out[-200:])
        code, j = post(dict(base, base=st["rev"], nums=U, done=True))
        job = wait_job(P, KQ, j.get("rev"))
        code, j2 = post(dict(base, base=j.get("rev"), nums=N1, done=True))
        job = wait_job(P, KQ, j2.get("rev"))
        st = state()
        case("changed and then put back to the order the Canva slides were made from: no Canva line", job.get("state") == "done" and st["canva"] is False and plain() == sorted(slide_names(N1)), (job, st["canva"]))
        code, out = run(env, "arrange.py", "took", kit_name, "--piece", "carousel")

        # ---- a job that fails before it has read its order still tells the page that is waiting ----
        st = state()
        R = st["rev"]
        job_file.write_text(json.dumps({"state": "queued", "line": "Making your slides...", "rev": R, "count": 3, "pid": None, "at": "x", "t": time.time()}))   # as the server writes it at the press
        shutil.move(str(hid / "sheet.json"), str(aside_dir / "sheet.json"))
        try:
            code, out = run(env, "arrange.py", "apply", str(kit), "--piece", "carousel", "--job")
        finally:
            shutil.move(str(aside_dir / "sheet.json"), str(hid / "sheet.json"))
        job = json.loads(job_file.read_text())
        case("a job that cannot even read its order: its problem carries the counter the page is waiting for (not -1)", code == 1 and job.get("state") == "problem" and job.get("rev") == R and "Couldn't make the slides." in job.get("line", ""), job)
        st = state()
        case("so the waiting page is told", st["job"]["state"] == "problem" and st["job"]["rev"] == st["rev"] == R, st["job"])

        # ---- an order longer than a carousel holds (an older pick): the page can bring it down ----
        rec = record()
        long_pick = [x["n"] for x in sheet][:22]
        rec["picks"]["carousel"] = long_pick               # this check's own kit record: a pick from before the limit was kept at the source
        rec_file.write_text(json.dumps(rec, indent=1))
        st = state()
        case("fixes: the page shows an over-long pick as it is", len(st["now"]["nums"]) == 22 and st["limits"]["max"] == 20, len(st["now"]["nums"]))
        code, j = post(dict(base, base=st["rev"], nums=long_pick[::-1]))
        case("an over-long order can be re-ordered on the page (no 'Reload the page' circle)", code == 200 and j.get("ok") is True, (code, j))
        code, j2 = post(dict(base, base=j.get("rev"), nums=long_pick[::-1], done=True))
        case("its final button is refused with the reason: Instagram allows up to 20", code == 400 and j2.get("words") == "Instagram allows up to 20. Take one out first." and not json.loads((studio / "arrange-waiting.json").read_text() if (studio / "arrange-waiting.json").exists() else "[]"), (code, j2))
        code, j3 = post(dict(base, base=j.get("rev"), nums=long_pick[:21]))
        case("one taken out (21) is saved", code == 200 and j3.get("ok") is True, (code, j3))
        code, j4 = post(dict(base, base=j3.get("rev"), nums=long_pick))
        case("but it can never be made longer again (22 after 21 is refused)", code == 400, (code, j4))
        code, j5 = post(dict(base, base=j3.get("rev"), nums=long_pick[:20]))
        case("and twenty is saved", code == 200 and j5.get("ok") is True and len(state()["now"]["nums"]) == 20, (code, j5))
        code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, N1)))

        # ---- the kit's words in a near-miss shape (hashtags as a list) never stop the kit page or the slides ----
        words_file, captions, page_file = hid / "words.json", hid / "Captions and hooks.txt", hid / "Post kit.html"
        given = work / "fixes-words.json"

        def text_of(f):
            try:
                return f.read_text(encoding="utf-8")
            except OSError:
                return ""

        given.write_text(json.dumps({"hooks": ["One", "Two", "Three"], "caption": "A windy morning.", "hashtags": ["#harbor", "#windy"]}), encoding="utf-8")
        code, out = run(env, "kit.py", "words", kit_name, "--file", str(given))
        kept = json.loads(words_file.read_text(encoding="utf-8")) if words_file.exists() else {}
        case("words: hashtags handed over as a list are saved as one line, not a crash", code == 0 and kept.get("hashtags") == "#harbor #windy" and "Traceback" not in out, (code, out[-200:]))
        case("words: the captions file and the kit page both show them", "#harbor #windy" in text_of(captions) and "<p>#harbor #windy</p>" in text_of(page_file))
        was = words_file.read_bytes() if words_file.exists() else b""
        given.write_text(json.dumps({"hooks": ["One"], "caption": 7}), encoding="utf-8")
        code, out = run(env, "kit.py", "words", kit_name, "--file", str(given))
        case("words: a caption that is not text is refused in plain words, with nothing saved", code == 1 and "STOP:" in out and "Nothing was saved" in out and "Traceback" not in out and words_file.read_bytes() == was, (code, out[-200:]))
        given.write_text("not json", encoding="utf-8")
        code, out = run(env, "kit.py", "words", kit_name, "--file", str(given))
        case("words: a file that is not JSON is refused the same way", code == 1 and "STOP:" in out and "Traceback" not in out and words_file.read_bytes() == was, (code, out[-200:]))
        # a words file an earlier version saved with the list in it (this check's own kit): every later page still works
        words_file.write_text(json.dumps(dict(kept, hashtags=["#older", "#list"], stories="One line"), indent=1), encoding="utf-8")
        code, out = run(env, "kit.py", "page", kit_name)
        case("words: a words file already saved with a list in it no longer stops the kit page", code == 0 and "<p>#older #list</p>" in text_of(page_file) and "Traceback" not in out, (code, out[-200:]))
        code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, N1[::-1])))
        code2, out2 = run(env, "kit.py", "build", kit_name)
        case("words: nor kit.py build after a new order", code == 0 and code2 == 0 and "Traceback" not in out2, (code, code2, out2[-200:]))
        code, out = run(env, "kit.py", "picks", kit_name, "--carousel", ",".join(map(str, N1)))

        case("fixes: the Photos folder at the end: not one photo changed, none added", folder_print(photos_dir) == photos_before)
        log_text = (studio / "arrange.log").read_text() if (studio / "arrange.log").exists() else ""
        case("fixes: nothing failed inside a route or a job", " failed: " not in log_text, [x for x in log_text.splitlines() if " failed: " in x][:2])
    finally:
        srv.stop()
        subprocess.run(["pkill", "-f", f"arrange.py apply {kit}"], capture_output=True)      # a job of this check's own, if one is somehow still at work


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a new folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=8841)
    ap.add_argument("--photos", type=int, default=14)
    ap.add_argument("--only", choices=["scripts", "server", "carousel"])
    a = ap.parse_args()
    if not Path("/usr/bin/osascript").exists() or not Path("/usr/bin/sips").exists():
        print("STOP: this needs a Mac (osascript and sips).")
        return 2
    if a.work:
        work = Path(a.work).resolve()
        if SAFE not in work.parents:
            print(f"STOP: {work} is not under {SAFE}.")
            return 2
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="hf-arrange-check-", dir=str(SAFE)))
    if ((work / "fake").exists() and a.only not in ("scripts", "carousel")) or (((work / "fake-carousel").exists() or (work / "fake-fixes").exists()) and a.only != "scripts"):
        print(f"STOP: {work} already holds a pretend kit from an earlier run. Give a new --work folder.")
        return 2
    # Nothing here may ever look at the real ~/.studio: this process and every command it runs get a
    # STUDIO_HOME inside the work folder (the pretend kit's own, once it is made).
    os.environ["STUDIO_HOME"] = str(work / "no-studio")
    r = subprocess.run([PY, str(ROOT / "tools" / "check_plugin.py")], capture_output=True, text=True)
    case("tools/check_plugin.py prints CLEAN", r.returncode == 0 and "CLEAN" in r.stdout, r.stdout[-300:])
    for f in ("arrange.py", "arrange_page.py", "kit.py", "posting_queue.py", "home.py"):
        r = subprocess.run(["/usr/bin/python3", "-c", "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')", str(SCRIPTS / f)], capture_output=True, text=True)
        case(f"{f} compiles under the Mac's own /usr/bin/python3", r.returncode == 0, r.stderr[-200:])
    if a.only not in ("server", "carousel"):
        check_scripts(work)
    if a.only == "carousel":
        check_carousel(work, a.port + 8)
        check_carousel_fixes(work, a.port + 16)
    elif a.only != "scripts":
        check_server(work, a.port, a.photos)
    bad = [n for n, ok in results if not ok]
    print()
    print(f"{len(results)} cases, {len(results) - len(bad)} passed, {len(bad)} failed." + (f"  Work folder: {work}" if bad or a.work else f"  Work folder (safe to throw away): {work}"))
    for n in bad:
        print("  FAILED:", n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
