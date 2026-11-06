#!/usr/bin/env python3
"""The carousel designer's page: Preview swipe, the profile grid's crop lines, and Save slides.

DESIGN_SAVE_JS (put on the page last, by design_page.py) works the bar at the bottom of the window:

    Preview swipe       a phone-shaped box showing one slide at a time, drawn from the same layout by the same
                        function that draws a saved slide. Arrows, dots, "3 of 7", a drag past 40 px, the arrow
                        keys, Escape. No Instagram name or logo on it.
    Profile grid crop   shades what the profile grid leaves out of each side of slide 1 (worked out in
                        DesignPlan.gridTrim: 33.75 px a side). Only a way of looking; nothing is saved of it.
    Save slides         every slide drawn at 1080 by 1350 and handed to the Assistant, which puts the whole set
                        into the Carousel folder under a name of its own. Nothing is ever replaced.

SAVE SLIDES, IN ORDER (every line it says is beside the button):
    1. every font is waited for, the design itself is saved, and the Assistant says what is already saved
    2. a save that was cut off part way is finished first, under the name it had
    3. nothing changed since the last set: "Already saved as ...", and nothing is drawn. "Nothing changed"
       is the Assistant's word (the same layout, name and edit of every photo, every file still there) plus
       the page's own: the same fonts are missing now as then. A photo exported again since this page opened
       stops the save before anything is drawn, with Reload just above the button, in the same bar.
    4. an empty frame or a bare slide is asked about IN THE PAGE (Save anyway / Go back); so is a text box
       that still says the words the Assistant put there to start it off ("Your words here", a starter's
       "Your title": words they never wrote must not land on a finished slide unasked); so is a font that
       could not be loaded (those words would be saved in Georgia)
    5. each slide: one canvas, the background, everything on that slide in list order (Designer.paint), JPEG
       at 0.93, sent to staging, one at a time, "Making slide 3 of 7..."; pictures the next slide does not
       need are let go, so twenty slides never pile up in memory
    6. one commit, asked again with the SAME name for the press if the connection drops, so one set finishes
       under one name
The button is off while this runs. A change to the design while it runs stops it before anything is added.

The timers here are waits between tries (a slide or a commit the Assistant did not answer), never something
the page's state depends on.
"""

DESIGN_SAVE_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, P = window.DesignPlan, $ = D.$, el = D.el, W = M.W, H = M.H;

  // Every line of words this part of the page says. (What the Assistant answers with is shown as it comes.)
  var SW = D.WORDS.save = {
    starting: 'Getting ready...',
    making: function(i, n){ return 'Making slide ' + i + ' of ' + n + '...'; },
    placing: 'Putting the slides in your Carousel folder...',
    saveAnyway: 'Save anyway', goBack: 'Go back',
    holes: function(k, slides){
      return k === 1 ? 'The frame on slide ' + slides[0] + ' is still empty. It will be left as plain background.'
                     : k + ' frames are still empty (' + (slides.length === 1 ? 'slide ' : 'slides ') + P.list(slides) + '). They will be left as plain background.';
    },
    bare: function(slides){
      return slides.length === 1 ? 'Slide ' + slides[0] + ' has nothing on it. It will be saved as a plain slide.'
                                 : 'Slides ' + P.list(slides) + ' have nothing on them. They will be saved as plain slides.';
    },
    // a text box that still says what the Assistant put there to start it off
    standIn: function(found){
      if (found.length === 1) return 'The text on slide ' + found[0].slide + ' still says “' + found[0].text + '”, the words it started with. It will be saved like that.';
      var slides = []; found.forEach(function(f){ if (slides.indexOf(f.slide) < 0) slides.push(f.slide); });
      return found.length + ' text boxes still say the words they started with (' + (slides.length === 1 ? 'slide ' : 'slides ') + P.list(slides) + '). They will be saved like that.';
    },
    fellBack: function(names){
      var q = names.map(function(n){ return '“' + n + '”'; });
      var list = q.length <= 1 ? q.join('') : q.slice(0, -1).join(', ') + ' and ' + q[q.length - 1];
      return list + ' couldn’t be loaded, so that text will be saved in Georgia.';
    },
    stopped: function(i){ return 'Stopped at slide ' + i + '. Nothing was added to your Carousel folder. Press Save slides to try again.'; },
    photo: function(n){ return 'Photo ' + n + ' can’t be read. Is the drive plugged in? Nothing was added to your Carousel folder.'; },
    notSaved: 'Your design couldn’t be saved just now, so no slides were made. Nothing was added to your Carousel folder.',
    cantReach: 'Can’t reach the Assistant right now, so no slides were made. Nothing was added to your Carousel folder. Press Save slides to try again.',
    late: 'Couldn’t reach the Assistant to finish saving. Nothing was lost. Press Save slides again and it will finish.',
    // the Assistant's own words for these two, for when the page knows before it has to ask
    changed: 'The design changed while its slides were being made. Nothing was added to your Carousel folder. Press Save slides again.',
    photoNewer: 'A photo on these slides was exported again since this page opened, so no slides were made. Nothing was added to your Carousel folder. Press Reload, then Save slides again.',
    already: function(base){ return 'Already saved as "' + base + '". Change something to save a new set.'; },
    cantOpen: 'Couldn’t open the folder from here. Ask Claude to open your Carousel folder.',
    // the preview
    previewLabel: 'Preview', count: function(i, n){ return i + ' of ' + n; },
    prev: 'Previous slide', next: 'Next slide', close: 'Close',
    previewHint: 'Swipe, use the arrows, or the arrow keys.',
    gridTitle: 'Your profile grid shows the first slide a little narrower. The striped edges on slide 1 are what it leaves out.'
  };
  var TRIES = 3, WAIT = 2000, FLUSH_WAIT = 20000, COMMIT_WAIT = 75000, QUALITY = 0.93;

  var saveBtn = $('save-slides'), prevBtn = $('preview-btn'), line = $('save-line'), yes = $('save-yes'), no = $('save-no');
  var openBtn = $('open-carousel'), openWrap = $('open-wrap'), openLine = $('open-line'), grid = $('gridcrop');
  var busy = false, asking = null, changed = false;
  var marks = null;       // each photo in use -> its mark on the drive now, from the Assistant's answer to the last save of the design
  D.on('saved', function(j){ marks = (j && j.marks) || null; });
  D.on('design', function(){ marks = null; });
  // What a set of slides is drawn from: the mark this page has for each photo in use (the picture it shows
  // and draws), and the fonts that could not be loaded. The Assistant writes it down with the set.
  function drawnFrom(st, fell){
    var photos = {};
    st.blocks.forEach(function(b){ if (M.typeOf(b) === 'photo' && b.n != null) photos[String(b.n)] = (D.by[b.n] && D.by[b.n].v) || ''; });
    return {photos: photos, fell: (fell || []).slice().sort()};
  }
  function sameList(a, b){ a = (a || []).slice().sort(); b = (b || []).slice().sort(); return a.length === b.length && a.every(function(x, i){ return x === b[i]; }); }
  function stale(drawn){
    if (!marks) return false;
    for (var k in drawn.photos) { if (Object.prototype.hasOwnProperty.call(marks, k) && marks[k] !== drawn.photos[k]) return true; }
    return false;
  }
  var stats = {held: 0, peak: 0, slides: 0, ms: 0, runs: 0};      // what the last save held and took (for the checks)

  function say(text){ if (line.textContent !== (text || '')) line.textContent = text || ''; }
  // The text boxes that still say, letter for letter, words the Assistant put there: what "+ Add text"
  // starts a box with, and the words in the starter templates. -> [{slide, text}], in reading order
  function standIns(st){
    var theirs = {};
    var add = function(s){ s = typeof s === 'string' ? s.trim() : ''; if (s) theirs[s] = true; };
    add(D.S && D.S.text && D.S.text.text);
    ((D.S && D.S.starters) || []).forEach(function(t){ ((t && t.template && t.template.blocks) || []).forEach(function(b){ if (M.isText(b)) add(b.text); }); });
    return st.blocks.filter(function(b){ return M.isText(b) && Object.prototype.hasOwnProperty.call(theirs, String(b.text || '').trim()); })
      .map(function(b){ return {slide: M.clamp(Math.floor((b.x + b.w / 2) / W), 0, st.slides - 1) + 1, text: String(b.text).trim(), x: b.x, y: b.y}; })
      .sort(function(a, b){ return a.slide - b.slide || a.y - b.y || a.x - b.x; });
  }
  function showOpen(on){ openWrap.hidden = !on; openLine.textContent = ''; }
  function wait(ms){ return new Promise(function(ok){ setTimeout(ok, ms); }); }
  // A question, in the page, beside the button -> a promise of true (Save anyway) or false (Go back).
  function ask(text){
    say(text);
    yes.hidden = false; no.hidden = false;
    return new Promise(function(ok){
      asking = function(v){ asking = null; yes.hidden = true; no.hidden = true; ok(v); };
    });
  }
  yes.addEventListener('click', function(){ if (asking) asking(true); });
  no.addEventListener('click', function(){ if (asking) asking(false); });
  // The design changing answers a question with "go back", stops a save that is running, and takes away a
  // line about a save that is no longer what is on the slides.
  function moved(){
    if (asking) asking(false);
    else if (busy) changed = true;
    else { say(''); showOpen(false); }
  }
  D.on('change', moved);
  D.on('design', moved);

  // ---------- Save slides ----------
  function toBlob(cv){
    return new Promise(function(ok, bad){
      try { cv.toBlob(function(b){ if (b && b.size > 0) ok(b); else bad(new Error('no picture')); }, 'image/jpeg', QUALITY); } catch (e) { bad(e); }
    });
  }
  // One finished slide to the Assistant's waiting place. Sent again when no answer comes (the same picture
  // twice is fine there). -> {ok} or {ok: false, words}
  async function sendSlide(id, token, i, of, blob){
    var url = '/design-slide?' + D.Q + '&design=' + encodeURIComponent(id) + '&set=' + encodeURIComponent(token) + '&i=' + i + '&of=' + of;
    for (var t = 0; t < TRIES; t++) {
      try {
        var r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'image/jpeg'}, body: blob});
        var j = await r.json();
        if (j && j.ok) return {ok: true};
        if (r.status >= 500 && !(j && j.why)) throw new Error('no answer');
        return {ok: false, words: (j && j.words) || ''};
      } catch (e) {
        if (t + 1 < TRIES) await wait(WAIT);
      }
    }
    return {ok: false, words: ''};
  }
  // The whole set into the Carousel folder. Asked again under the SAME name while the Assistant is still at
  // it, or does not answer, so one press ends as one set under one name.
  async function commit(id, token, rev, count, drawn){
    var o = {kit: D.KIT, design: id, set: token, rev: rev, count: count};
    if (drawn) o.drawn = drawn;
    var body = JSON.stringify(o);
    var until = Date.now() + COMMIT_WAIT, again = 0;
    for (;;) {
      var j = null;
      try {
        var r = await fetch('/design-commit', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: body});
        j = await r.json();
      } catch (e) { j = null; }
      if (j && j.ok) return {ok: true, already: !!j.already, base: j.base, count: j.count, words: j.words || ''};
      var why = (j && j.why) || '';
      var named = why === 'clash' || why === 'redo';              // a name was in the way: the next try takes the next free one
      if (named) again += 1;
      var more = !j || why === 'still' || why === 'busy' || (named && again <= 3);
      if (!more || Date.now() > until) return {ok: false, why: why, words: (j && j.words) || SW.late};
      await wait(named ? 300 : WAIT);
    }
  }
  function finished(res, fell){
    say(res.words || SW.already(res.base));
    showOpen(true);
    if (D.design) {
      D.design.unfinished = false;
      D.design.set = {base: res.base, count: res.count, same: true, fell: (fell || []).slice(), words: SW.already(res.base)};
      (D.S.designs || []).forEach(function(d){ if (d.id === D.design.id) d.set = res.base; });
    }
  }
  function late(p, ms){
    return Promise.race([p, wait(ms).then(function(){ return 'late'; })]);
  }
  async function run(){
    if (!D.st || !D.design || D.blocked) return;
    var id = D.design.id, t0 = Date.now();
    say(SW.starting);
    // 1. every font in (or given up on), the design itself saved, and the Assistant's word on what is saved
    var fonts = D.type ? await D.type.fonts.ready(D.st, {retry: true}) : {fellBack: []};
    D.save.queue();
    var ok = await late(D.save.flush(), FLUSH_WAIT);
    if (ok !== true || !D.design || D.design.id !== id || D.blocked) { say(ok === 'late' ? SW.cantReach : SW.notSaved); return; }
    var st = M.copy(D.st), rev = D.save.rev(), n = st.slides, token = D.newToken('s');
    var drawn = drawnFrom(st, fonts.fellBack);
    changed = false;
    // a photo exported again since this page opened: what this page shows, and would draw, is the old edit
    if (stale(drawn)) { say(SW.photoNewer); D.photosChanged(); return; }
    // 2. a save that was cut off part way is finished first, under the name it had
    if (D.design.unfinished) {
      say(SW.placing);
      var first = await commit(id, token, rev, n);
      if (first.ok) { finished(first, D.design.set && D.design.set.fell); return; }
      if (first.why !== 'missing') { say(first.words); return; }
    } else if (D.design.set && D.design.set.same && sameList(D.design.set.fell, drawn.fell)) {
      // 3. nothing has changed since the last set: nothing is drawn or sent, and the line is said at once.
      // The Assistant is still told (and not waited for), so that this set is the one the kit page shows
      // again if other slides had taken its place since (a new order of the plain slides, a Canva carousel).
      say(D.design.set.words || SW.already(D.design.set.base));
      showOpen(true);
      commit(id, token, rev, n).catch(function(){});
      return;
    }
    // 4. the questions, in the page
    var hs = P.holeSlides(st), bare = P.bareSlides(st), q = [];
    if (hs.count) q.push(SW.holes(hs.count, hs.slides));
    if (bare.length) q.push(SW.bare(bare));
    var kept = standIns(st);
    if (kept.length) q.push(SW.standIn(kept));
    if (q.length && !(await ask(q.join(' ')))) { say(''); return; }
    if (fonts.fellBack && fonts.fellBack.length && !(await ask(SW.fellBack(fonts.fellBack)))) { say(''); return; }
    if (changed) { say(''); return; }
    // 5. the slides, one at a time
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d'), sh = D.paint.shelf(), i = 0;
    try {
      for (i = 1; i <= n; i++) {
        if (changed) { say(SW.changed); return; }
        say(SW.making(i, n));
        await D.paint.slide(ctx, st, i - 1, {out: 1, shelf: sh, fonts: false});
        var blob = await toBlob(cv);
        if (sh.count > stats.held) stats.held = sh.count;
        D.paint.letGo(sh, i < n ? D.paint.keys(st, i, 1) : null);       // only what the next slide is drawn from is kept
        var sent = await sendSlide(id, token, i, n, blob);
        blob = null;
        if (!sent.ok) { say(sent.words || SW.stopped(i)); return; }
      }
    } catch (e) {
      say(e && e.photo ? SW.photo(e.photo) : SW.stopped(i));
      return;
    } finally {
      stats.peak = sh.peak;
      D.paint.letGo(sh, null);
      cv.width = 1; cv.height = 1;
    }
    if (changed) { say(SW.changed); return; }
    // 6. the whole set into the Carousel folder
    say(SW.placing);
    var res = await commit(id, token, rev, n, drawn);
    if (res.ok) { finished(res, drawn.fell); stats.slides = n; stats.ms = Date.now() - t0; }
    else { say(res.words); if (res.why === 'photos') D.photosChanged(); }
  }
  saveBtn.addEventListener('click', function(){
    if (busy || !D.st || !D.design || D.blocked) return;
    busy = true; changed = false;
    saveBtn.disabled = true;
    showOpen(false);
    stats.held = 0; stats.peak = 0; stats.slides = 0; stats.ms = 0;
    var end = function(){ busy = false; saveBtn.disabled = !!D.blocked; stats.runs += 1; };
    run().then(end, function(){ say(SW.stopped(1)); end(); });
  });
  // "Open the Carousel folder": the kit's own folder, through the Assistant; its answer shows right here
  openBtn.addEventListener('click', function(){
    openLine.textContent = '';
    fetch('/open?' + D.Q + '&sub=Carousel', {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        var words = (j && j.words) || D.WORDS.cantReach;
        // this page never shows where a folder is on the computer: an answer that spells a path out is
        // said in the page's own words instead
        if (!(j && j.ok) && /[\/\\]/.test(words)) words = SW.cantOpen;
        openLine.textContent = words;
      }, function(){ openLine.textContent = D.WORDS.cantReach; });
  });
  // the answer has been read by the next press or key anywhere else: it goes, so it never sits over anything
  document.addEventListener('pointerdown', function(e){ if (openLine.textContent && !(e.target && openWrap.contains(e.target))) openLine.textContent = ''; }, true);
  document.addEventListener('keydown', function(){ if (openLine.textContent) openLine.textContent = ''; }, true);
  D.on('render', function(){ if (!busy) saveBtn.disabled = D.blocked; prevBtn.disabled = !D.st; });

  // ---------- the profile grid's crop, on slide 1 ----------
  var over = $('over'), cropL = el('div', 'sv-crop sv-l'), cropR = el('div', 'sv-crop sv-r');
  over.appendChild(cropL); over.appendChild(cropR);
  // what the tick shows is said in words in the bar for as long as it is on (a title alone is never seen by
  // a finger or a keyboard)
  var gridLine = $('grid-line');
  grid.parentNode.title = SW.gridTitle;
  grid.addEventListener('change', function(){ D.render(); });
  D.on('render', function(){
    var on = grid.checked && !!D.st, s = D.scale, trim = P.gridTrim();
    cropL.classList.toggle('on', on); cropR.classList.toggle('on', on);
    if (gridLine.hidden !== !on) { gridLine.textContent = on ? SW.gridTitle : ''; gridLine.hidden = !on; }
    if (!on) return;
    cropL.style.left = '0px'; cropL.style.width = trim * s + 'px';
    cropR.style.left = (W - trim) * s + 'px'; cropR.style.width = trim * s + 'px';
  });

  // ---------- Preview swipe ----------
  var modal = D.modals.make('preview');
  var phone = el('div', 'pv-phone'); phone.setAttribute('role', 'dialog'); phone.setAttribute('aria-label', SW.previewLabel);
  var view = el('div', 'pv-view'); view.id = 'pv-view';
  var count = el('span', 'pv-count'); count.id = 'pv-count';
  var bPrev = el('button', 'pv-nav pv-l', '‹'); bPrev.type = 'button'; bPrev.id = 'pv-prev'; bPrev.setAttribute('aria-label', SW.prev);
  var bNext = el('button', 'pv-nav pv-r', '›'); bNext.type = 'button'; bNext.id = 'pv-next'; bNext.setAttribute('aria-label', SW.next);
  var track = el('div', 'pv-track'); track.id = 'pv-track';
  view.appendChild(count); view.appendChild(bPrev); view.appendChild(bNext); view.appendChild(track);
  var dots = el('div', 'pv-dots'); dots.id = 'pv-dots';
  var foot = el('div', 'pv-foot'), bClose = el('button', 'tb', SW.close); bClose.type = 'button'; bClose.id = 'pv-close';
  foot.appendChild(el('span', '', SW.previewHint)); foot.appendChild(bClose);
  phone.appendChild(view); phone.appendChild(dots); phone.appendChild(foot);
  modal.appendChild(phone);
  var pv = {open: false, i: 0, w: 360, st: null, shelf: null, cvs: [], drawn: {}, drag: null};

  function drawOne(k){
    if (!pv.open || k < 0 || k >= pv.st.slides || pv.drawn[k]) return;
    pv.drawn[k] = true;
    var cv = pv.cvs[k];
    // the same drawing as a saved slide, only smaller, from copies that are already made
    D.paint.slide(cv.getContext('2d'), pv.st, k, {out: cv.width / W, cap: 'l', soft: true, shelf: pv.shelf}).then(null, function(){});
  }
  function place(dx){ track.style.transform = 'translateX(' + (-pv.i * pv.w + (dx || 0)) + 'px)'; }
  function go(i){
    pv.i = M.clamp(i, 0, pv.st.slides - 1);
    place(0);
    Array.prototype.forEach.call(dots.children, function(d, k){ d.classList.toggle('on', k === pv.i); });
    count.textContent = SW.count(pv.i + 1, pv.st.slides);
    bPrev.style.visibility = pv.i > 0 ? 'visible' : 'hidden';
    bNext.style.visibility = pv.i < pv.st.slides - 1 ? 'visible' : 'hidden';
    drawOne(pv.i); drawOne(pv.i + 1); drawOne(pv.i - 1);
  }
  function closePreview(){ D.modals.close(modal); }
  prevBtn.addEventListener('click', function(){
    if (!D.st || pv.open) return;
    var st = M.copy(D.st), dpr = Math.min(2, window.devicePixelRatio || 1);
    pv.st = st; pv.shelf = D.paint.shelf(); pv.cvs = []; pv.drawn = {}; pv.drag = null;
    pv.w = P.phoneWidth(document.documentElement.clientWidth, window.innerHeight);
    var h = Math.round(pv.w * H / W);
    view.style.width = pv.w + 'px'; view.style.height = h + 'px';
    track.textContent = ''; dots.textContent = '';
    track.classList.add('pv-held');           // it is put in place, not slid there
    for (var k = 0; k < st.slides; k++) {
      var cv = document.createElement('canvas');
      cv.width = Math.round(pv.w * dpr); cv.height = Math.round(h * dpr);
      cv.style.left = k * pv.w + 'px'; cv.style.width = pv.w + 'px'; cv.style.height = h + 'px';
      var ctx = cv.getContext('2d');
      ctx.fillStyle = /^#[0-9a-fA-F]{6}$/.test(st.bg || '') ? st.bg : '#ffffff';
      ctx.fillRect(0, 0, cv.width, cv.height);
      track.appendChild(cv); pv.cvs.push(cv);
      dots.appendChild(el('b'));
    }
    pv.open = true;
    D.modals.open(modal, function(){
      pv.open = false; pv.drag = null;
      if (pv.shelf) D.paint.letGo(pv.shelf, null);
      pv.shelf = null; pv.cvs = []; track.textContent = '';
      D.focus(prevBtn);
    });
    go(0);
    track.getBoundingClientRect();            // the first place is taken at once; the slide comes with later moves
    track.classList.remove('pv-held');
    D.focus(bClose);
  });
  bClose.addEventListener('click', closePreview);
  bPrev.addEventListener('click', function(){ if (pv.open) go(pv.i - 1); });
  bNext.addEventListener('click', function(){ if (pv.open) go(pv.i + 1); });
  // a drag turns the slide once it has gone far enough (drawn by the page itself; pointer events only)
  view.addEventListener('pointerdown', function(e){
    if (!pv.open || pv.drag || e.button !== 0 || (e.target.closest && e.target.closest('.pv-nav'))) return;
    pv.drag = {id: e.pointerId, x: e.clientX, dx: 0};
    track.classList.add('pv-held');
    try { view.setPointerCapture(e.pointerId); } catch (x) {}
    e.preventDefault();
  });
  view.addEventListener('pointermove', function(e){
    if (!pv.drag || e.pointerId !== pv.drag.id) return;
    pv.drag.dx = e.clientX - pv.drag.x;
    place(pv.drag.dx);
  });
  function endDrag(e, cancel){
    if (!pv.drag || (e && e.pointerId !== pv.drag.id)) return;
    var dx = pv.drag.dx;
    pv.drag = null;
    track.classList.remove('pv-held');
    if (pv.open) go(cancel ? pv.i : P.swipe(pv.i, dx, pv.st.slides));
  }
  view.addEventListener('pointerup', function(e){ endDrag(e, false); });
  view.addEventListener('pointercancel', function(e){ endDrag(e, true); });
  window.addEventListener('blur', function(){ endDrag(null, true); });
  document.addEventListener('keydown', function(e){
    if (!pv.open) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault(); e.stopPropagation();
      go(pv.i + (e.key === 'ArrowRight' ? 1 : -1));
    }
  }, true);

  D.saver = {stats: stats, busy: function(){ return busy; }, asking: function(){ return !!asking; }, preview: pv};
})();
"""

# The styles of the bar at the bottom of the window, the profile grid's crop and the preview.
DESIGN_SAVE_CSS = """
.sv-bar{flex:none;position:sticky;bottom:0;z-index:25;margin:0 -16px;padding:10px 16px;background:var(--panel);border-top:1px solid var(--line);box-shadow:0 -6px 16px -12px rgba(42,38,34,.4)}
.sv-notes{max-width:var(--wide);margin:0 auto}
.sv-in{max-width:var(--wide);margin:0 auto;display:flex;flex-wrap:nowrap;gap:8px;align-items:flex-end;min-height:34px}
.sv-in>*{flex:none}
.sv-in>label{padding-bottom:8px}
.sv-in>.gline{flex:0 1 auto;min-width:0;padding-bottom:7px;overflow-wrap:break-word}
.sv-open{position:relative;display:inline-flex}
.sv-open[hidden]{display:none}
.sv-bub{position:absolute;bottom:calc(100% + 8px);left:0;right:0;background:var(--ink);color:#fff;font:600 12.5px/1.35 var(--sans);padding:7px 10px;border-radius:8px;box-shadow:0 8px 20px -8px rgba(0,0,0,.5);white-space:normal;overflow-wrap:anywhere}
.sv-bub:empty{display:none}
@media(max-width:900px){.sv-in{flex-wrap:wrap-reverse;align-items:flex-start;align-content:flex-start}.sv-in>.sv-ans{order:2}.sv-in>.gline{order:3;flex:1 1 100%;padding-bottom:0}.sv-in>.sv-open{order:4;flex:1 1 100%}.sv-bub{right:auto;width:max-content;max-width:min(420px,calc(100vw - 32px))}}
.sv-crop{position:absolute;top:0;bottom:0;display:none;background:repeating-linear-gradient(135deg,rgba(200,40,40,.62) 0 4px,rgba(255,255,255,.55) 4px 8px);pointer-events:none}
.sv-crop.on{display:block}
.sv-crop.sv-l{border-right:1px solid rgba(220,60,60,.85)}
.sv-crop.sv-r{border-left:1px solid rgba(220,60,60,.85)}
.pv-phone{background:#fff;color:#111;border-radius:18px;overflow:hidden;max-width:100%;box-shadow:0 10px 40px rgba(0,0,0,.4)}
.pv-view{position:relative;overflow:hidden;touch-action:pan-y;user-select:none;-webkit-user-select:none;cursor:grab;background:var(--line)}
.pv-track{position:absolute;left:0;top:0;height:100%;transition:transform .32s ease}
.pv-track.pv-held{transition:none}
.pv-track canvas{position:absolute;top:0;display:block}
.pv-dots{display:flex;justify-content:center;flex-wrap:wrap;gap:5px;padding:10px}
.pv-dots b{width:6px;height:6px;border-radius:50%;background:#cfcfcf}
.pv-dots b.on{background:var(--sel)}
.pv-nav{position:absolute;top:50%;transform:translateY(-50%);width:32px;height:32px;border-radius:50%;border:0;background:rgba(255,255,255,.88);color:#111;font-size:18px;line-height:1;padding:0;z-index:5;cursor:pointer}
.pv-nav.pv-l{left:8px}
.pv-nav.pv-r{right:8px}
.pv-count{position:absolute;top:10px;right:10px;z-index:5;background:rgba(0,0,0,.6);color:#fff;font-size:12px;border-radius:999px;padding:2px 8px;pointer-events:none}
.pv-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:0 12px 12px;font-size:12.5px;color:#555}
"""
