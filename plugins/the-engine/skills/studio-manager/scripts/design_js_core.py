#!/usr/bin/env python3
"""The carousel designer's page: the part every other part hangs on (design_page.py puts it on the page).

DESIGN_CORE_JS makes window.Designer (D below): the state the Assistant sent, the open design's layout, what
is selected, ONE way to change the layout (D.setState), ONE drawing pass (D.render), ONE save queue (D.save),
Undo, and the places later parts add themselves:

    D.WORDS                         every line of words the page itself says, in one place
    D.setState(change, o)           change = a new layout, or function(layout) -> a new layout (the same one,
                                    or nothing, when there is no change). o: {undo: false | true | 'a key' (a run
                                    of changes with the same key is one Undo step), fresh: true (start a new run),
                                    save: false, sel: an id or null, adjust: true | false}
    D.select(id), D.selected()      what is selected on the strip
    D.undo(), D.canUndo()
    D.render()                      draws everything again from D.st; D.on('render', fn) adds a drawing step
    D.on(name, fn)                  'adopt' (a state arrived), 'design' (a design was opened), 'photos' (the
                                    small copies moved on), 'change' (the layout changed), 'render', 'saved'
    D.save.queue() / .flush()       save soon / save now (a promise: true once nothing is unsaved)
    D.save.fields.push(fn)          fn(body) may add to what a save sends (stage D: the design's name)
    D.blockTypes[kind]              how one kind of block is drawn and handled (design_js_edit.py adds 'photo'
                                    and a plain stand-in 'other'; stage C adds 'text')
    D.hints[kind]                   function(block) -> the line of help for a selected block of that kind
    D.tools.group(id, label, row)   a new group of buttons in a toolbar row ('tools-designs' or 'tools-main')
    D.selbar.group(id, label, when) a new group in the bar for the selected thing; when(kind, block) -> shown?
    D.quiet.push(fn)                fn() true while a pop-up is open: the strip's keys are then left alone
    D.load(id)                      open another of this shoot's designs (saves the open one first)

Nothing that matters is kept in the browser: the layout is saved by POST /design about 0.7 s after a change
(and at once when the page is hidden or left), one save at a time, with the counter the Assistant gave.
"""

DESIGN_CORE_JS = r"""
(function(){
  'use strict';
  var M = window.DesignModel;
  var KIT = document.body.dataset.kit, Q = 'kit=' + encodeURIComponent(KIT);
  var $ = function(id){ return document.getElementById(id); };
  var el = function(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  // Every line of words this page says by itself. (What the Assistant refuses with comes with its answer.)
  var WORDS = {
    saved: 'Saved', saving: 'Saving...', retry: 'Not saved yet. Trying again...',
    cantReach: 'Could not reach the Assistant. Tell Claude instead.',
    newer: 'This design was changed somewhere else. Here\'s the newest.',
    photosChanged: 'The photos in this shoot changed since this page opened.',
    reload: 'Reload',
    cantRead: 'Can’t read this photo right now',
    missing: 'Some photos can’t be read right now. Is the drive plugged in?',
    prep: function(made, total){ return 'Getting your photos ready: ' + made + ' of ' + total; },
    dropped: function(k){ return k === 1 ? '1 photo is no longer in this shoot, so its frame is empty now.' : k + ' photos are no longer in this shoot, so their frames are empty now.'; },
    slide: function(k){ return 'Slide ' + k; },
    dropHere: 'Drop a photo',
    allPhotos: function(k){ return 'All ' + k + (k === 1 ? ' photo' : ' photos'); },
    // what the lifted photo says it will do
    intoFrame: 'Put it in this frame',
    ontoSlide: function(k){ return 'Add it to slide ' + k; },
    // the help line beside the buttons for the selected thing
    hintNone: 'Click a photo on the slides to change it. Drag photos from below onto the slides.',
    hintPhoto: function(n){ return 'Photo ' + n + '. Drag to move it, or pull a corner to resize (hold Shift to keep its shape). Double-click to move the photo inside its frame.'; },
    hintInside: function(n){ return 'Drag to move photo ' + n + ' inside its frame, and turn the wheel to zoom. Click outside it when you’re done.'; },
    hintHole: 'An empty frame. Click a photo below, or drag one onto it, to fill it.',
    hintOther: 'A text box. Drag to move it.',
    inside: 'Move photo inside', insideDone: 'Done moving',
    // why a press did nothing
    last: function(k){ return 'Slide ' + k + ' still has something on it. Move it or remove it first.'; },
    wide: 'Something is wider than the slides that would be left. Make it smaller first.',
    min: 'A carousel needs at least 2 slides.',
    max: 'Instagram allows up to 20 slides.',
    small: 'This photo is too small for a border.',
    many: 'A design holds up to 80 photos and text boxes. Remove one first.',
    full: 'Every slide has a photo, and 20 slides is as many as Instagram allows. Drag this photo onto a frame to put it there instead.'
  };
  // a name this page gives itself, new on every load and kept nowhere: it lets the Assistant tell this
  // page's own save (whose answer never arrived) from a change made in another window
  var PAGE = (Math.random().toString(36).slice(2, 12) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '');

  var D = window.Designer = {
    M: M, KIT: KIT, Q: Q, WORDS: WORDS, $: $, el: el,
    S: null,              // the last whole answer from /design-state
    by: {},               // photo number -> its record
    design: null,         // the open design: {id, name, set, unfinished, dropped}
    st: null,             // its layout now: {slides, bg, blocks}
    sel: null,            // the id of the selected block, or null
    adjust: false,        // "Move photo inside" is on for the selected photo
    scale: 230 / M.W,     // screen pixels for one strip pixel
    blocked: false,       // the photos changed under the page: nothing more is saved until a reload
    blockTypes: {}, hints: {}, quiet: []
  };

  var subs = {};
  D.on = function(name, fn){ (subs[name] = subs[name] || []).push(fn); };
  D.emit = function(name, a){ (subs[name] || []).slice().forEach(function(fn){ fn(a); }); };
  D.render = function(){ if (D.st) D.emit('render'); };
  D.typeOf = function(b){ var t = M.typeOf(b); return D.blockTypes[t] ? t : 'other'; };
  D.selected = function(){ return D.st && D.sel != null ? M.find(D.st, D.sel) : null; };
  D.photoUrl = function(n, size){ var p = D.by[n]; return '/kit-photo?' + Q + '&n=' + n + '&size=' + size + '&v=' + encodeURIComponent((p && p.v) || ''); };
  D.keysOff = function(){ for (var i = 0; i < D.quiet.length; i++) { if (D.quiet[i]()) return true; } return false; };

  // ---- one way to change things ----
  var hist = M.history();
  function setSel(id){
    var b = id == null || !D.st ? null : M.find(D.st, id), nid = b ? b.id : null;
    if (nid !== D.sel) D.adjust = false;
    D.sel = nid;
  }
  D.select = function(id, o){
    if (!D.st) return;
    setSel(id);
    if (o && 'adjust' in o) D.adjust = !!o.adjust && D.sel != null;
    D.render();
  };
  D.setState = function(change, o){
    o = o || {};
    if (!D.st || D.blocked) return false;
    var next = typeof change === 'function' ? change(D.st) : change;
    var did = !!next && next !== D.st && !M.same(next, D.st);
    if (did) {
      if (o.fresh) hist.mark();
      if (o.undo === false) hist.mark();
      else hist.push({st: JSON.stringify(D.st), sel: D.sel}, typeof o.undo === 'string' ? o.undo : null);
      D.st = next;
    }
    if ('sel' in o) setSel(o.sel); else if (D.sel != null && !M.find(D.st, D.sel)) setSel(null);
    if ('adjust' in o) D.adjust = !!o.adjust && D.sel != null;
    if (did) D.emit('change');
    D.render();
    if (did && o.save !== false) queue();
    return did;
  };
  D.undo = function(){
    if (!D.st || D.blocked) return false;
    var h = hist.pop();
    if (!h) return false;
    D.st = JSON.parse(h.st);
    D.adjust = false;
    D.sel = h.sel != null && M.find(D.st, h.sel) ? h.sel : (D.sel != null && M.find(D.st, D.sel) ? D.sel : null);
    D.emit('change');
    D.render();
    queue();
    return true;
  };
  D.canUndo = function(){ return hist.size() > 0; };

  // ---- the lines at the top, and the line about a save ----
  function status(text, bad){ var s = $('d-status'); s.textContent = text || ''; s.classList.toggle('bad', !!bad); }
  function note(text, reload){
    var n = $('d-note'); n.textContent = '';
    if (!text) { n.hidden = true; return; }
    n.appendChild(el('span', '', text));
    if (reload) { var b = el('button', 'tb', WORDS.reload); b.type = 'button'; b.addEventListener('click', function(){ location.reload(); }); n.appendChild(b); }
    n.hidden = false;
  }
  function reach(text){ var a = $('l-reach'); a.textContent = text || ''; a.hidden = !text; }
  function topLines(){
    var S = D.S, a = $('l-missing'), b = $('l-dropped'), c = $('prep');
    var miss = S.photos.some(function(p){ return p.missing; });
    a.hidden = !miss; a.textContent = miss ? WORDS.missing : '';
    var k = (D.design && D.design.dropped) || 0;
    b.hidden = !k; b.textContent = k ? WORDS.dropped(k) : '';
    var made = S.photos.filter(function(p){ return p.have; }).length;
    var waiting = S.photos.some(function(p){ return !p.have && !p.missing; });
    c.hidden = !waiting; c.textContent = waiting ? WORDS.prep(made, S.total) : '';
    return waiting;
  }
  D.status = status; D.note = note;

  // ---- saving: one request at a time; the newest layout wins; retried until it lands ----
  var rev = 0;                  // the counter of the newest layout the Assistant has told this page about
  var saving = false, dirty = false, timer = null, retryT = null, waiters = [];
  var SOFT = {many: 1, long: 1, font: 1, name: 1};      // refusals the photographer can put right on the page
  function settle(ok){ if (ok === false || (!saving && !dirty)) { var w = waiters; waiters = []; w.forEach(function(f){ f(ok !== false); }); } }
  function body(){
    var b = {kit: KIT, design: D.design.id, stamp: D.S.stamp, base: rev, page: PAGE, state: D.st};
    D.save.fields.forEach(function(fn){ fn(b); });
    return b;
  }
  function queue(){
    if (D.blocked || !D.st) return;
    dirty = true;
    note('');                   // a line about an earlier save has been read by now, and this change is a new try
    status(WORDS.saving);
    clearTimeout(timer);
    timer = setTimeout(send, 700);
  }
  function send(){
    clearTimeout(timer); clearTimeout(retryT);
    if (saving || D.blocked || !D.st) return;
    if (!dirty) { settle(); return; }
    saving = true; dirty = false;
    var id = D.design.id;
    status(WORDS.saving);
    fetch('/design', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body())})
      .then(function(r){
        // 500 and up is treated like no answer at all (try again), unless the Assistant says the drive would
        // not take the change: then its words say why, and that is what is shown
        if (r.status >= 500) return r.json().then(null, function(){ return null; }).then(function(j){
          if (j && j.why === 'drive' && j.words) return {code: r.status, j: j};
          throw new Error('no answer');
        });
        return r.json().then(function(j){ return {code: r.status, j: j}; });
      })
      .then(function(res){
        saving = false;
        var j = res.j || {};
        if (!D.design || D.design.id !== id) { if (dirty) send(); else settle(); return; }     // another design was opened meanwhile
        if (res.code === 200 && j.ok) {
          if (typeof j.rev === 'number') rev = j.rev;
          D.design.set = j.set || null; D.design.unfinished = !!j.unfinished;
          D.emit('saved', j);
          if (dirty) { send(); return; }
          status(WORDS.saved); settle();
          return;
        }
        if (res.code === 409 && j.why === 'photos') { photosChanged(j.words); return; }
        if (res.code === 409 && j.why === 'newer' && j.design) {
          takeDesign(j.design);
          status(WORDS.saved);
          note(j.words || WORDS.newer, false);
          settle();
          return;
        }
        if (res.code >= 500 && j.why === 'drive') {
          // the drive is full, locked or unplugged: say which, keep trying (the change lands by itself once
          // that is put right), and tell anything waiting on this save that it has not happened
          dirty = true;
          status(j.words, true);
          retryT = setTimeout(send, 2000);
          settle(false);
          return;
        }
        if (res.code === 404 && j.why !== 'design') {
          // the shoot can't be found right now (its drive is unplugged): keep trying, with the question
          // showing, so the change lands by itself when the drive is back
          dirty = true;
          status(j.words || WORDS.cantReach, true);
          retryT = setTimeout(send, 2000);
          return;
        }
        // refused: say so. What they can put right themselves is sent again with their next change; anything
        // else gets the Reload button beside the words.
        dirty = true;
        status('');
        note(j.words || WORDS.cantReach, !SOFT[j.why]);
        settle(false);
      })
      .catch(function(){
        // the Assistant did not answer (it may be starting over after an update): keep trying
        saving = false; dirty = true;
        status(WORDS.retry, true);
        retryT = setTimeout(send, 2000);
      });
  }
  function photosChanged(words){
    D.blocked = true; dirty = false;
    clearTimeout(timer); clearTimeout(retryT);
    status('');
    note(words || WORDS.photosChanged, true);
    settle(false);
    D.render();
  }
  D.photosChanged = photosChanged;
  D.save = {
    fields: [],
    queue: queue,
    flush: function(){
      return new Promise(function(ok){
        if (!dirty && !saving) { ok(true); return; }
        waiters.push(ok);
        if (!saving) send();
      });
    },
    idle: function(){ return !saving && !dirty; },
    rev: function(){ return rev; }
  };
  // The page going out of sight (the pane showing something else) saves at once; the page being left hands
  // the newest layout to the browser to deliver (the same save, so sending it twice is harmless).
  document.addEventListener('visibilitychange', function(){ if (document.hidden && dirty && !saving) send(); });
  window.addEventListener('pagehide', function(){
    if (!D.st || D.blocked || (!dirty && !saving)) return;
    try { navigator.sendBeacon('/design', new Blob([JSON.stringify(body())], {type: 'application/json'})); } catch (e) {}
  });

  // ---- taking a state from the Assistant ----
  function takeDesign(d){
    D.design = {id: d.id, name: d.name, set: d.set || null, unfinished: !!d.unfinished, dropped: d.dropped || 0};
    rev = d.rev;
    D.st = M.tidy(d.state);
    hist.clear();
    D.sel = null; D.adjust = false; dirty = false;
    clearTimeout(timer); clearTimeout(retryT);
    // which design is open lives in the address, so a reload opens the same one
    try { window.history.replaceState(null, '', '/design.html?' + Q + '&design=' + encodeURIComponent(d.id)); } catch (e) {}
    $('d-name').textContent = d.name;
    D.emit('design', d);
    D.render();
  }
  function adopt(j){
    var rebuild = !D.S || D.S.stamp !== j.stamp || D.S.total !== j.total;
    D.S = j; D.by = {};
    j.photos.forEach(function(p){ D.by[p.n] = p; });
    M.useLimits(j.limits);
    D.blocked = false;
    $('title').textContent = j.name;
    var kl = $('kitlink');
    if (j.kit_page) { kl.href = '/content/' + encodeURIComponent(KIT) + '/Post%20kit.html'; kl.hidden = false; } else kl.hidden = true;
    D.emit('adopt', {rebuild: rebuild});
    takeDesign(j.design);
    if (topLines()) poll();
  }
  function wanted(){ var m = /[?&]design=([a-z0-9]{1,40})(?:&|$)/.exec(location.search); return m ? m[1] : ''; }
  function getState(id){
    return fetch('/design-state?' + Q + (id ? '&design=' + encodeURIComponent(id) : ''), {cache: 'no-store'}).then(function(r){ return r.json(); });
  }
  function start(){
    getState(wanted()).then(function(j){
      if (!j || !j.ok) { reach((j && j.words) || WORDS.cantReach); return; }
      reach('');
      adopt(j);
      status(WORDS.saved);
    }).catch(function(){
      reach(WORDS.cantReach);
      setTimeout(start, 2000);
    });
  }
  // Open another of this shoot's designs: the open one is saved first, and nothing is opened if that fails.
  D.load = function(id){
    return D.save.flush().then(function(ok){
      if (!ok) return false;
      return getState(id).then(function(j){
        if (!j || !j.ok) { note((j && j.words) || WORDS.cantReach, true); return false; }
        note('');
        adopt(j);
        status(WORDS.saved);
        return true;
      });
    });
  };
  // while small copies are still being made, ask again every so often and fill the pictures in as they arrive
  var pollT = null;
  function stopPoll(){ if (pollT) { clearInterval(pollT); pollT = null; } }
  function poll(){
    if (pollT) return;
    var tries = 0;
    pollT = setInterval(function(){
      tries += 1;
      getState(D.design.id).then(function(j){
        if (!j || !j.ok || !pollT) return;
        if (j.stamp !== D.S.stamp) { stopPoll(); photosChanged(); return; }
        D.S.photos = j.photos; D.S.previews = j.previews;
        j.photos.forEach(function(p){ D.by[p.n] = p; });
        D.emit('photos');
        D.render();
        if (!topLines() || tries > 500) stopPoll();
      }).catch(function(){});
    }, 1500);
  }

  // ---- places for buttons ----
  D.tools = {
    // a new group of buttons at the end of a toolbar row ('tools-designs' is the top row, 'tools-main' the second)
    group: function(id, label, row){
      var g = el('div', 'group'); g.id = id;
      if (label) g.appendChild(el('span', 'lbl', label));
      $(row || 'tools-main').appendChild(g);
      return g;
    },
    button: function(group, text, id, cls){ var b = el('button', 'tb' + (cls ? ' ' + cls : ''), text); b.type = 'button'; if (id) b.id = id; group.appendChild(b); return b; },
    line: function(text){ $('toolline').textContent = text || ''; }
  };
  var selGroups = [];
  D.selbar = {
    // a new group in the bar for the selected thing. when(kind, block) says whether it shows; with nothing
    // selected it is asked with kind 'photo' and no block, and what shows is greyed out (so the bar never jumps).
    group: function(id, label, when){
      var bar = $('selbar'), g = el('div', 'group needsel'); g.id = id;
      if (label) g.appendChild(el('span', 'lbl', label));
      var all = $('sel-all');
      bar.insertBefore(g, all && id !== 'sel-all' ? all : $('selline'));
      selGroups.push({el: g, when: when});
      return g;
    },
    button: function(group, text, act, title){ var b = el('button', 'tb', text); b.type = 'button'; b.dataset.a = act; if (title) b.title = title; group.appendChild(b); return b; },
    line: function(text){ $('selline').textContent = text || ''; }
  };
  D.on('render', function(){
    var b = D.selected(), kind = b ? D.typeOf(b) : 'photo';
    $('selbar').classList.toggle('off', !b);
    selGroups.forEach(function(g){ g.el.hidden = !g.when(kind, b); });
    var hint = D.hints[b ? kind : 'none'];
    $('selhint').textContent = hint ? hint(b) : '';
  });

  D.start = start;
})();
"""
