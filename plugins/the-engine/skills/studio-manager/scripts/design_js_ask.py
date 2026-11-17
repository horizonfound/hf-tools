#!/usr/bin/env python3
"""The designer's page: "Let my assistant choose the photos" (Nicole's v26, Nov 13, on stories; her v27, Nov 14, on
carousels too).

DESIGN_ASK_JS (put on the page by design_page.py, last) works the button beside the photos' heading and the box it
opens. The box and every word in it are written into the page by design_page.py (her words, whole, worded for
stories or for slides by the kind of page).

    the note      "Tell your assistant what you want", optional, up to 600 letters. It is kept with the open set of
                  stories, or the open carousel design, as "ask": it rides on the design's own save
                  (Designer.save.fields), about 0.7 s after typing stops, and comes back with the design
                  (Designer.design.ask). It is never part of the layout, so it changes no story, no slide, no Undo
                  step and no "Already saved".
    the line      "Pick my story photos for <shoot>" ("Pick my carousel photos for <shoot>"), with ", and follow my
                  note" only while there is a note (hers). The shoot's name goes on the page as text.
    Copy          copies the line (the older copy call: the Claude app's pane refuses the newer one), says
                  "Copied" for a moment, tells the Assistant which set was asked about (POST /design-asked: a time
                  noted with the set, nothing else), and from then on, for ten minutes, the page looks every few seconds for the
                  assistant's pick: when the set on the Assistant's side is newer than this page's and nothing here
                  is unsaved, in the middle of a drag, under an open window or being typed into a box, the page takes it (Designer.load), so
                  the stories fill in beside the chat without a reload.

+ ADD PHOTOS (hers, v27, beside the button): opens the shoot's Photos folder through the Assistant (GET /open, sub Photos) and
says her line under the photos' heading ("Your Photos folder is open in Finder. Drag your finished photos in, and they show up
here at the end."; File Explorer on a PC: the three lines come from design_page.py as data on the line). From then on, while
that line is showing and the page is in sight, every 4 seconds the page asks the Assistant (POST /design-photos) whether
photos have joined the folder; when the list's stamp has moved and every photo kept its number, the page takes the new list
(Designer.takePhotos) and the new photos join the END of the tray with the next numbers, with her "3 new photos in, at the end
of your photos (#168–170)." A photo gone or renamed still asks for a Reload, as it always has.

Nothing is kept in the browser.
"""

DESIGN_ASK_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, $ = D.$;
  var btn = $('ask-pick'), box = $('ask-box');
  if (!btn || !box) return;
  var note = $('ask-note'), words = $('ask-words'), copyBtn = $('ask-copy'), said = $('ask-said');
  // Hers, but for the last one (ours: hers has no line for the moment the pick arrives).
  var AW = D.WORDS.ask = {
    line: words.textContent,                // "Pick my story photos" / "Pick my carousel photos" (written into the page, hers)
    forShoot: function(shoot){ return ' for ' + shoot; }, withNote: ', and follow my note',
    copy: copyBtn.textContent, copied: 'Copied',
    arrived: D.STORY ? 'Your assistant’s pick is in your stories.' : 'Your assistant’s pick is in your slides.'
  };
  var MAX = Number(note.getAttribute('maxlength')) || 600;
  var WATCH = 10 * 60 * 1000, EVERY = 4000;

  function shoot(){ return (D.S && D.S.name) || 'this shoot'; }
  function ask(){ return (D.design && typeof D.design.ask === 'string') ? D.design.ask : ''; }
  function line(){ return AW.line + AW.forShoot(shoot()) + (ask().trim() ? AW.withNote : ''); }
  function show(){ words.textContent = line(); }

  // the note rides on every save of the set or the design
  D.save.fields.push(function(body){ if (D.design && typeof D.design.ask === 'string') body.ask = D.design.ask; });

  btn.addEventListener('click', function(){
    box.hidden = !box.hidden;
    btn.setAttribute('aria-expanded', box.hidden ? 'false' : 'true');
    if (box.hidden) return;
    note.value = ask();
    show();
    D.focus(note);
  });
  note.addEventListener('input', function(){
    if (!D.design || D.blocked) return;
    var v = note.value.trim().slice(0, MAX);
    if (v === ask()) { show(); return; }
    D.design.ask = v;
    show();
    D.save.queue();
  });
  // a set or a design was opened (or the newest came from the Assistant): its own note, unless they are typing one right now
  D.on('design', function(){
    if (document.activeElement !== note) note.value = ask();
    else if (D.design && !D.blocked && note.value.trim().slice(0, MAX) !== ask()) {
      // they are typing a note right now: theirs stays, in the box and with the set, and is saved like any typing
      D.design.ask = note.value.trim().slice(0, MAX);
      D.save.queue();
    }
    note.disabled = false;
    said.textContent = '';
    show();
  });
  D.on('render', function(){ note.disabled = !!D.blocked; copyBtn.disabled = !D.design; });

  var backT = null;
  copyBtn.addEventListener('click', function(){
    var t = line();
    try {
      var a = document.createElement('textarea');
      a.value = t; a.setAttribute('readonly', ''); a.style.cssText = 'position:fixed;left:0;top:0;opacity:0';
      document.body.appendChild(a); a.select();
      document.execCommand('copy');
      a.remove();
    } catch (e) {}
    D.focus(copyBtn);
    copyBtn.textContent = AW.copied;
    clearTimeout(backT);
    backT = setTimeout(function(){ copyBtn.textContent = AW.copy; }, 1500);
    said.textContent = '';
    // which set or design they asked about: the line they paste names none, so the Assistant is told it is this one
    // (only a time is noted with it; nothing about its stories or slides changes). No answer is waited for.
    if (D.design) {
      try {
        fetch('/design-asked', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({kit: D.KIT, kind: D.STORY ? 'stories' : 'carousel', design: D.design.id})}).then(null, function(){});
      } catch (e) {}
    }
    watch();
  });

  // ---- after Copy: look for the assistant's pick, and take it when it is there ----
  var until = 0, timer = null, asking = false;
  function stop(){ if (timer) { clearInterval(timer); timer = null; } }
  function watch(){
    until = Date.now() + WATCH;
    if (!timer) timer = setInterval(look, EVERY);
  }
  // Are they typing in a box (a story's words, the set's name, a size)? Then the pick waits until they leave it:
  // taking it would close the box under their hands and lose what they type next. The note's own box does not count.
  function typing(){
    var a = document.activeElement, tag = (a && a.tagName) || '', type = String((a && a.type) || '').toLowerCase();
    if (!a || a === note) return false;
    return tag === 'TEXTAREA' || a.isContentEditable || (tag === 'INPUT' && /^(text|number|search|)$/.test(type));
  }
  function busy(){
    return typing() || D.blocked || !D.save.idle() || (D.modals && D.modals.any()) || document.body.classList.contains('d-dragging') || document.hidden;
  }
  function look(){
    if (Date.now() > until || !D.design) { stop(); return; }
    if (asking || busy()) return;
    var id = D.design.id;
    asking = true;
    fetch('/design-state?' + D.Q + D.KQ + '&design=' + encodeURIComponent(id), {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        asking = false;
        if (!j || !j.ok || !j.design || j.design.id !== id || !D.design || D.design.id !== id || busy()) return;
        if (!(j.design.rev > D.save.rev())) return;
        // something newer is on the Assistant's side and nothing here is unsaved: take it
        return D.load(id).then(function(ok){ if (ok) said.textContent = AW.arrived; });
      })
      .then(null, function(){ asking = false; });
  }
  D.ask = {line: line, watching: function(){ return !!timer; }, look: look, typing: typing, EVERY: EVERY};

  // ---- + Add photos (hers, v27) ----
  var addBtn = $('add-photos'), addLine = $('add-photos-line');
  if (!addBtn || !addLine) return;
  var APW = D.WORDS.addPhotos = {
    opening: addLine.dataset.opening, open: addLine.dataset.open, cant: addLine.dataset.cant,       // hers, in this computer's words
    joined: function(k, first, last){ return k + ' new photo' + (k === 1 ? '' : 's') + ' in, at the end of your photos (#' + first + (k > 1 ? '\u2013' + last : '') + ').'; }
  };
  var ADD_EVERY = 4000, addT = null, addBusy = false;
  function addSay(text){ addLine.hidden = false; addLine.textContent = text; }
  addBtn.addEventListener('click', function(){
    addSay(APW.opening);
    fetch('/open?' + D.Q + '&sub=Photos', {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        if (!(j && j.ok)) { addSay(APW.cant); return; }
        // the Assistant may add that the window is behind this one (ours); never a path
        var m = /It's behind this window[^.]*\./.exec(String((j && j.words) || ''));
        addSay(APW.open + (m && !/[\/\\]/.test(m[0]) ? ' ' + m[0] : ''));
      }, function(){ addSay(APW.cant); });
    watchPhotos();
  });
  function watchPhotos(){ if (!addT) addT = setInterval(lookPhotos, ADD_EVERY); }
  function lookPhotos(){
    if (addLine.hidden || document.hidden || addBusy || !D.S || !D.design || D.blocked) return;
    addBusy = true;
    fetch('/design-photos', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kit: D.KIT, kind: D.STORY ? 'stories' : 'carousel'})})
      .then(function(r){ return r.json(); })
      .then(function(j){
        if (!j || !j.ok || !D.S || j.stamp === D.S.stamp) { addBusy = false; return; }
        if (j.kept === false) { addBusy = false; D.photosChanged(); return; }          // a photo gone or renamed: the Reload path, as always
        return fetch('/design-state?' + D.Q + D.KQ + '&design=' + encodeURIComponent(D.design.id), {cache: 'no-store'})
          .then(function(r){ return r.json(); })
          .then(function(s){
            addBusy = false;
            var fresh = D.takePhotos(s);
            if (fresh && fresh.length) addSay(APW.joined(fresh.length, fresh[0].n, fresh[fresh.length - 1].n));
            else if (fresh === null && s && s.ok && s.stamp !== D.S.stamp && D.save.idle()) D.photosChanged();     // not a plain addition
          });
      })
      .then(null, function(){ addBusy = false; });
  }
  document.addEventListener('visibilitychange', function(){ if (!document.hidden && addT) lookPhotos(); });
  D.addPhotos = {watching: function(){ return !!addT; }, look: lookPhotos, EVERY: ADD_EVERY};
})();
"""

# The styles of the box (the page's own colours and font; the dashed line to copy is the home page's "paste this").
DESIGN_ASK_CSS = """
.trayhead .tray-btns{margin-left:auto;display:inline-flex;gap:8px;flex-wrap:wrap;align-items:center}
.trayhead .add-photos{border-radius:999px;padding:6px 14px;background:var(--panel)}
.trayhead .ask-btn{background:var(--ink);border-color:var(--ink);color:#fff;border-radius:999px;padding:6px 14px}
#add-photos-line{margin:2px 0 8px}
.trayhead .ask-btn:hover{background:var(--accent);border-color:var(--accent)}
.ask-box{margin:8px 0 12px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
.ask-box[hidden]{display:none}
.ask-box label{display:block;font-size:13.5px}
.ask-box label b{font-weight:600}
.ask-box .ask-ex{display:block;color:var(--soft);font-size:12.5px;margin-top:3px}
.ask-box textarea{display:block;width:100%;box-sizing:border-box;margin-top:6px;font:400 14px/1.4 var(--sans);padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);resize:vertical}
.ask-box textarea:focus{outline:2px solid var(--sel);outline-offset:-1px}
.ask-box p{margin:8px 0 6px;font-size:13px}
.ask-line{display:flex;align-items:center;justify-content:space-between;gap:10px;border:1.5px dashed var(--accent);border-radius:12px;padding:8px 8px 8px 12px;max-width:560px}
.ask-line span{font-style:italic;font-size:15px;overflow-wrap:anywhere;min-width:0}
.ask-line .tb{flex:none;background:var(--ink);border-color:var(--ink);color:#fff;border-radius:999px;padding:6px 13px}
.ask-box .gline{margin:8px 0 0}
"""
