#!/usr/bin/env python3
"""Check the picker pages without a browser: the routes, the records, the commands, and the page's scripts.

    /usr/bin/python3 tests/arrange_check.py                 makes its own pretend kit under /private/tmp
    /usr/bin/python3 tests/arrange_check.py --work /private/tmp/somewhere --port 8841 --photos 14
    /usr/bin/python3 tests/arrange_check.py --only scripts  just the page's scripts (no server, two seconds)

It makes a pretend Assistant with tests/fake_kit.py in a new folder under /private/tmp (it refuses anywhere
else), points STUDIO_HOME at it, starts the page server on a scratch port, and prints one PASS or FAIL line
per case. It never touches the real ~/.studio and never uses ports 8790, 8765 or 8770. The server it starts
is stopped at the end, whatever happened. The work folder is left in place so a failure can be looked at;
it is this script's own scratch and can be thrown away.

What it cannot do: drive a real pointer in the Claude app's pane. The page's scripts are run here on a
pretend page (below, PAGE_JS) under the Mac's own JavaScript engine, which catches a syntax error, a wrong
name, and a wrong rule, but not how the pane itself treats a press. That part is a person's to try.

Exit 0 when every case passes, 1 otherwise. Python 3.9, standard library only.
"""
import argparse
import hashlib
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
document.body.dataset.kit = 'A kit'; document.body.dataset.piece = 'reel';

// ---- a pretend Assistant behind /arrange-state and /arrange, keeping the real rules for the counter ----
// (the counter is the Assistant's: one higher for every change it takes. A change is taken from a page whose
// "base" is the stored counter, or whose own last save, from that same base, is what is stored.)
var SERVER = {mode: 'up', posts: [], gets: 0, from: null,
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
  if (url === '/arrange') {
    var b = JSON.parse(opts.body); SERVER.posts.push(b);
    if (SERVER.mode === 'lost') { SERVER.mode = 'up'; apply(b); return new Now('bad', new Error('answer lost')); }
    if (SERVER.mode === 'photos') return reply(409, {ok: false, why: 'photos', words: 'changed'});
    if (SERVER.mode === 'refuse') return reply(400, {ok: false, words: 'That didn\u2019t arrive the way it should have. Reload the page and try again.'});
    if (SERVER.mode === 'unplugged') return reply(404, {ok: false, words: 'I can\u2019t find that shoot\u2019s posts. Is the drive plugged in?'});
    var st = SERVER.st, same = JSON.stringify(st.now.nums) === JSON.stringify(b.nums) && JSON.stringify(st.now.marks) === JSON.stringify(b.marks);
    var own = !!SERVER.from && SERVER.from.page === b.page && SERVER.from.base === b.base;
    if (!same && b.base !== st.rev && !own) return reply(409, {ok: false, why: 'newer', words: 'newer', state: st});
    if (same) { if (b.done) st.happy = {rev: st.rev}; return reply(200, {ok: true, words: 'Saved', rev: st.rev, job: false}); }
    apply(b);
    return reply(200, {ok: true, words: 'Saved', rev: st.rev, job: false});
  }
  return new Now('bad', new Error('unknown address ' + url));
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
if (SCENARIO === 'down') SERVER.mode = 'down';

// ---- the three scripts, exactly as the page carries them ----
(new Function(MODEL_SRC)).call(this);
(new Function(DRAG_SRC)).call(this);
(new Function(PICKER_SRC)).call(this);

// ---- helpers for the checks ----
var byId = function(id){ return document.getElementById(id); };
var rowEl = byId('row'), poolEl = byId('pool'), panel = byId('panel'), poolSec = byId('poolsec'), wrap = byId('rowwrap');
function rowNums(){ return rowEl.querySelectorAll('.rt').map(function(t){ return Number(t.dataset.n); }); }
function rowTile(n){ return rowEl.querySelectorAll('.rt').filter(function(t){ return Number(t.dataset.n) === n; })[0]; }
function poolTile(n){ return poolEl.querySelectorAll('.pt').filter(function(t){ return Number(t.dataset.n) === n; })[0]; }
function lifted(){ return document.body.querySelectorAll('.arr-lift').length; }
function text(id){ return byId(id).textContent; }
function lastPost(){ return SERVER.posts[SERVER.posts.length - 1]; }
// lay the page out: the sticky panel on top, the row's tiles on lines of `perLine`, the photos below
// (the row's own box is 190 tall unless told otherwise: about one line of photos, as on the real page)
function layout(perLine, boxH){
  boxH = boxH || 190;
  box(panel, 0, 0, 800, 40 + boxH + 100); box(wrap, 10, 40, 780, boxH); box(rowEl, 10, 40, 780, 400); box(poolSec, 0, 360, 800, 3000); box(poolEl, 0, 400, 800, 2900);
  rowEl.querySelectorAll('.rt').forEach(function(t, i){
    var x = 20 + (i % perLine) * 100, y = 50 + Math.floor(i / perLine) * 170;
    box(t, x, y, 90, 160); box(t.querySelector('.ph'), x, y, 90, 132);
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
} else if (SCENARIO === 'down') {
  check('the Assistant not answering at the start: the page says so', text('l-reach') === 'Could not reach the Assistant. Tell Claude instead.' && !byId('l-reach').hidden, text('l-reach'));
  SERVER.mode = 'up'; runTimers();
  check('and it opens by itself once the Assistant is back', eq(rowNums(), [1, 6, 11, 16, 21]) && byId('l-reach').hidden && text('status') === 'Saved', rowNums());
} else {
settle();
check('opens with the Assistant’s pick in the row', eq(rowNums(), [1, 6, 11, 16, 21]), rowNums());
check('every photo of the shoot is below', poolEl.querySelectorAll('.pt').length === 30, poolEl.querySelectorAll('.pt').length);
check('a picked photo below is dimmed and carries its place', poolTile(11).classList.contains('in') && poolTile(11).querySelector('.pos').textContent === '3' && !poolTile(2).classList.contains('in'));
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
// only the row's own box takes a drop: the heading above it and the buttons below it do not
layout(10); was = rowNums();
dragTo(poolTile(9), 400, 300);                               // on the buttons under the row box (the box ends at 230)
check('over the buttons under the row there is no bar', !rowEl.querySelector('.ins').classList.contains('on'));
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
check('a row photo held over the panel\u2019s buttons is not about to be taken out', !poolSec.classList.contains('out'));
release(400, 300);
check('and dropping it there changes nothing', eq(rowNums(), was), rowNums());
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
dragTo(poolTile(13), 400, 300);                              // on its way up: over the buttons under the row box
runFrame(); wait(400); runFrame(); runFrame();
check('carried over the buttons under the row, however slowly: the row does not scroll', wrap.scrollTop === 0, wrap.scrollTop);
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
    plain = ap.plain_page("I can't find that shoot's posts. Is the drive plugged in?")

    # nothing from the internet, nothing the pane cannot do, nothing kept in the browser
    for label, text in (("the picker page", page), ("the plain page", plain)):
        case(f"{label}: no address on the internet anywhere in it", not re.search(r"https?://", text))
        case(f"{label}: no link, font or script from another address", "<link" not in text and not re.search(r"<script[^>]*\ssrc=", text) and "@import" not in text and "<img src" not in text and "<iframe" not in text)
    for word in ('draggable="true"', "draggable='true'", "localStorage", "sessionStorage", "indexedDB", "navigator.clipboard", "ondragstart", "dataTransfer"):
        case(f"the picker page: no {word}", word not in page)
    case("the picker page: only the kit's folder name and the piece are put into it", "data-kit='A kit'" in page and "data-piece='reel'" in page)
    case("a kit name is html-escaped on its way into the page", "data-kit='&lt;b&gt; &amp; &#x27;x&#x27;'" in ap.page_html("<b> & 'x'", "reel"))
    case("the plain page has the Back to home button and the words", "href='/home'" in plain and "Back to home" in plain and "I can&#x27;t find that shoot&#x27;s posts." in plain)
    case("the styles carry no backslash", "\\" not in ap.CSS)
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
    for scenario in ("main", "preparing", "gone", "down"):
        f = work / f"page-{scenario}.js"
        head = "".join(f"var {k} = {json.dumps(v)};\n" for k, v in (("SCENARIO", scenario), ("PAGE_ELS", els), ("MODEL_SRC", ap.MODEL_JS),
                                                                   ("DRAG_SRC", ap.DRAG_JS), ("PICKER_SRC", ap.PICKER_JS)))
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
                    ("size=xl", f"/kit-photo?kit={KQ}&n=3&size=xl"), ("size=x (a later stage)", f"/kit-photo?kit={KQ}&n=3&size=x"),
                    ("no size", f"/kit-photo?kit={KQ}&n=3"), ("no question at all", "/kit-photo")]
        for label, path in refusals:
            code, h, data = ask(P, "GET", path)
            case(f"photo route refuses: {label}", code == 404 and b"\xff\xd8" not in data[:4], code)
        os.symlink(str(kit), str(kit.parent / "A link to the kit"))
        code, h, data = ask(P, "GET", "/kit-photo?kit=A%20link%20to%20the%20kit&n=3&size=s")
        case("photo route refuses: a link to a kit, even inside Your Content", code == 404, code)
        os.unlink(str(kit.parent / "A link to the kit"))           # the link this check made a moment ago
        for path in ("/.kit/", "/previews/", f"/kit-photo/", "/arrange-state/", "/design.html"):
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
                                  ("the carousel (a later stage)", f"/arrange-state?kit={KQ}&page=carousel", 404), ("no page", f"/arrange-state?kit={KQ}", 404)):
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
                                   ("the carousel (a later stage)", f"/arrange.html?kit={KQ}&piece=carousel", "isn&#x27;t ready for this yet"),
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
            ("piece=carousel (a later stage)", 400, dict(nxt, piece="carousel"), J, None),
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
        for path in ("/design", "/design-slide", "/design-commit"):
            code, h, data = ask(P, "POST", path, body=b"{}", headers=J)
            case(f"a later stage's route is not here yet: POST {path} answers 404", code == 404, code)
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
        code, out = run(env, "arrange.py", "open", "Fake beach", "--piece", "carousel")
        case("arrange.py open for a piece with no page yet stops with a plain line", code == 1 and out.startswith("STOP:"), out)

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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", help="a new folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=8841)
    ap.add_argument("--photos", type=int, default=14)
    ap.add_argument("--only", choices=["scripts", "server"])
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
    if (work / "fake").exists() and a.only != "scripts":
        print(f"STOP: {work / 'fake'} is already there. Give a new --work folder.")
        return 2
    # Nothing here may ever look at the real ~/.studio: this process and every command it runs get a
    # STUDIO_HOME inside the work folder (the pretend kit's own, once it is made).
    os.environ["STUDIO_HOME"] = str(work / "no-studio")
    r = subprocess.run([PY, str(ROOT / "tools" / "check_plugin.py")], capture_output=True, text=True)
    case("tools/check_plugin.py prints CLEAN", r.returncode == 0 and "CLEAN" in r.stdout, r.stdout[-300:])
    for f in ("arrange.py", "arrange_page.py", "kit.py", "posting_queue.py", "home.py"):
        r = subprocess.run(["/usr/bin/python3", "-c", "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')", str(SCRIPTS / f)], capture_output=True, text=True)
        case(f"{f} compiles under the Mac's own /usr/bin/python3", r.returncode == 0, r.stderr[-200:])
    if a.only != "server":
        check_scripts(work)
    if a.only != "scripts":
        check_server(work, a.port, a.photos)
    bad = [n for n, ok in results if not ok]
    print()
    print(f"{len(results)} cases, {len(results) - len(bad)} passed, {len(bad)} failed." + (f"  Work folder: {work}" if bad or a.work else f"  Work folder (safe to throw away): {work}"))
    for n in bad:
        print("  FAILED:", n)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
