#!/usr/bin/env python3
"""The carousel designer's page: the designs of a shoot, new designs, templates, and the shoot menu.

DESIGN_DESIGNS_JS (put on the page by design_page.py after the drawing script) adds, in the top row:

    Shoot             every shoot with its photo and design counts; choosing one goes to that shoot's own designer
    the design's name a box: type to rename it (saved with the design, about 0.7 s after typing stops)
    My designs        this shoot's designs, newest first, with slide counts and "edited 5 min ago"; click to open
    Duplicate design  a copy, made by the Assistant ("<name> copy"), opened at once
    + New design      the gallery: Blank, One photo per slide, your own templates, the starter templates, each a
                      little picture drawn with this shoot's photos, and the tick "Put this shoot's photos in the
                      frames for me". IT ALWAYS MAKES A NEW DESIGN; the open one is saved first and stays as it is.
    Save as template  the layout with its photos taken out (the Assistant does the taking out), for any shoot
    Fill N empty frames   every empty frame given the next unused photo whose shape fits

There is no way to delete a design or a template here, on purpose.

Nothing is kept in the browser. A design or a template is known by the id the Assistant made, a shoot by its
kit folder's name; a press that makes something carries a name of its own (a token), so a press whose answer
was lost and is sent again never makes two. Names and words only ever go on the page as text.

For the saving part: Designer.post(path, body, tries), Designer.newToken(prefix), Designer.modals.
"""

DESIGN_DESIGNS_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, P = window.DesignPlan, $ = D.$, el = D.el;

  // Every line of words this part of the page says.
  var DW = D.WORDS.designs = {
    shoot: 'Shoot', shootsHead: 'Your shoots', shootsLabel: 'Your shoots',
    shootSub: function(photos, designs, open){
      return photos + (photos === 1 ? ' photo' : ' photos') + ' · ' + designs + (designs === 1 ? ' design' : ' designs') + (open ? ' · open now' : '');
    },
    nameLabel: 'The name of this design. Type to change it.',
    myDesigns: 'My designs', designsLabel: 'This shoot’s designs',
    designsHead: function(shoot){ return shoot + ' designs'; },
    designSub: function(slides, when, open){ return slides + ' slides' + (when ? ' · edited ' + when : '') + (open ? ' · open now' : ''); },
    dup: 'Duplicate design', dupTitle: 'Makes a copy of this design and opens it. This one stays as it is.',
    newDesign: '+ New design', newTitle: 'Start another design for this shoot. The one you have open stays as it is.',
    galleryTitle: 'New design',
    gallerySub: function(shoot){ return 'Pick a starting point for ' + shoot + '. This makes a new design. The one you have open stays as it is.'; },
    fillTick: 'Put this shoot’s photos in the frames for me',
    close: 'Close', use: 'Use', making: 'Making your new design...',
    makeLate: 'Can’t reach the Assistant right now, so no new design was made. Your open design is still here. Try again in a moment.',
    makeSlow: 'The Assistant is taking a long time. Look in My designs in a moment: your new design may be there.',
    secFresh: 'Start fresh', secMine: 'Your templates', secStarters: 'Starter templates',
    blank: 'Blank', blankSub: function(k){ return k + ' empty slides'; },
    onePer: 'One photo per slide', slidesSub: function(k){ return k + ' slides'; },
    tplSub: function(slides, frames, from){
      return slides + ' slides' + (frames ? ' · room for ' + frames + (frames === 1 ? ' photo' : ' photos') : '') + (from ? ' · from ' + from : '');
    },
    noneYet: 'None yet. Open a design you like and press “Save as template”.',
    saveTpl: 'Save as template', tplTitle: 'Save as template',
    tplHint: 'This keeps the layout: the frames, the text, the background and the number of slides. You can use it with any shoot. The photos aren’t kept in it, so each frame waits for that shoot’s photos.',
    tplName: 'Template name', tplSave: 'Save template', cancel: 'Cancel',
    // the Assistant's own words for these two, so the page says the same thing before it has to ask
    tplEmpty: 'Add some photos or text first, then save it as a template.',
    nameBad: 'Give it a name, up to 80 letters.',
    fill: function(k){ return k ? 'Fill ' + k + (k === 1 ? ' empty frame' : ' empty frames') : 'Fill empty frames'; },
    fillTitle: 'Puts photos you haven’t used yet into the empty frames',
    fillNone: 'Every photo in this shoot is already on a slide.',
    fillSome: function(k){ return 'There weren’t enough unused photos, so ' + k + (k === 1 ? ' frame is' : ' frames are') + ' still empty.'; },
    fellBack: 'That design isn’t here, so this is your newest one.'
  };
  var NAME_MAX = 80;

  // ---------- small things other parts use too ----------
  function button(text, id, cls){ var b = el('button', 'tb' + (cls ? ' ' + cls : ''), text); b.type = 'button'; if (id) b.id = id; return b; }
  function newToken(prefix){ return P.token(prefix, Date.now(), Math.random()); }
  // One POST to the Assistant -> a promise of {code, j}. When no answer comes, the very same body is sent
  // again (it carries the press's own name, so a press never counts twice); j is null when none ever came.
  function post(path, body, tries){
    var text = JSON.stringify(body);
    return new Promise(function(done){
      (function go(left){
        fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: text})
          .then(function(r){ return r.json().then(function(j){ return {code: r.status, j: j}; }); })
          .then(done, function(){ if (left > 1) setTimeout(function(){ go(left - 1); }, 2000); else done({code: 0, j: null}); });
      })(tries > 0 ? tries : 3);
    });
  }
  D.post = post; D.newToken = newToken;
  function cleanName(v){ return String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, NAME_MAX).trim(); }

  // ---------- pop-ups under a button, and the larger sheets over the page ----------
  var pops = [], modals = [];
  function closePop(p){ if (!p.open) return; p.open = false; p.pop.hidden = true; p.btn.setAttribute('aria-expanded', 'false'); }
  function closePops(){ pops.forEach(closePop); }
  function fitPop(p){
    p.pop.style.left = '0px';
    var r = p.pop.getBoundingClientRect(), over = r.right - (document.documentElement.clientWidth - 8);
    if (over > 0) p.pop.style.left = -Math.min(over, Math.max(0, r.left - 8)) + 'px';
  }
  function openPop(p){
    if (!D.S || !D.design) return;
    closePops();
    p.open = true; p.pop.hidden = false; p.btn.setAttribute('aria-expanded', 'true');
    p.build();
    fitPop(p);
    // what another window has done since this page opened is asked for, and shown if it is any different
    refresh().then(function(changed){ if (changed && p.open) { p.build(); fitPop(p); } });
  }
  function makePop(btn, id, label, build){
    var wrap = el('span', 'dz-popwrap'), pop = el('div', 'dz-pop');
    pop.id = id; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', label);
    btn.parentNode.insertBefore(wrap, btn);
    wrap.appendChild(btn); wrap.appendChild(pop);
    btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false');
    var p = {btn: btn, pop: pop, wrap: wrap, open: false, build: build};
    btn.addEventListener('click', function(e){ e.stopPropagation(); if (p.open) closePop(p); else openPop(p); });
    pops.push(p);
    return p;
  }
  D.modals = {
    make: function(id){
      var m = el('div', 'dz-modal'); m.id = id; m.hidden = true;
      document.body.appendChild(m);
      m.addEventListener('pointerdown', function(e){ if (e.target === m) D.modals.close(m); });      // a press beside the sheet
      return m;
    },
    open: function(m, onClose){
      closePops();
      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
      modals.push({el: m, onClose: onClose || null});
      m.hidden = false;
    },
    close: function(m){
      for (var i = modals.length - 1; i >= 0; i--) {
        if (modals[i].el !== m) continue;
        var x = modals.splice(i, 1)[0];
        m.hidden = true;
        if (x.onClose) x.onClose();
        return;
      }
    },
    isOpen: function(m){ return modals.some(function(x){ return x.el === m; }); },
    any: function(){ return modals.length > 0; }
  };
  D.quiet.push(function(){ return modals.length > 0 || pops.some(function(p){ return p.open; }); });
  // a press anywhere else closes a pop-up; Escape closes whatever is on top
  document.addEventListener('pointerdown', function(e){ pops.forEach(function(p){ if (p.open && !p.wrap.contains(e.target)) closePop(p); }); }, true);
  document.addEventListener('keydown', function(e){
    if (e.key !== 'Escape') return;
    var open = pops.filter(function(p){ return p.open; });
    if (open.length) {
      e.preventDefault(); e.stopPropagation();
      open.forEach(function(p){ closePop(p); try { p.btn.focus(); } catch (x) {} });
      return;
    }
    if (modals.length) { e.preventDefault(); e.stopPropagation(); D.modals.close(modals[modals.length - 1].el); }
  }, true);

  // ---------- what this page knows about the shoot's designs ----------
  function entry(){
    var id = D.design && D.design.id, list = (D.S && D.S.designs) || [];
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) return list[i]; }
    return null;
  }
  // the open design's own line in the list is kept as this page has it (it is the newest there is)
  function mine(t){
    var e = entry();
    if (!e || !D.st) return;
    e.name = D.design.name; e.slides = D.st.slides;
    if (t > 0) e.t = t;
  }
  function lists(){
    return JSON.stringify([(D.S.designs || []).map(function(d){ return [d.id, d.name, d.slides, Math.round(d.t || 0)]; }),
                           (D.S.shoots || []).map(function(s){ return [s.kit, s.name, s.photos, s.designs]; }),
                           (D.S.templates || []).map(function(t){ return [t.id, t.name]; })]);
  }
  // Ask the Assistant for the lists as they are now (designs, shoots, templates). -> a promise: did anything differ?
  function refresh(){
    if (!D.S || !D.design) return Promise.resolve(false);
    var id = D.design.id, stamp = D.S.stamp, was = lists();
    return fetch('/design-state?' + D.Q + '&design=' + encodeURIComponent(id), {cache: 'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(j){
        if (!j || !j.ok || !D.design || D.design.id !== id || !D.S || D.S.stamp !== stamp || j.stamp !== stamp) return false;
        var t = (entry() || {}).t;
        if (Array.isArray(j.designs)) D.S.designs = j.designs;
        if (Array.isArray(j.shoots)) D.S.shoots = j.shoots;
        if (Array.isArray(j.templates)) D.S.templates = j.templates;
        var e = entry();
        mine(e && t > (e.t || 0) ? t : 0);
        return lists() !== was;
      })
      .then(null, function(){ return false; });
  }
  D.on('change', function(){ mine(Date.now() / 1000); });
  D.on('saved', function(j){
    var e = entry();
    if (!e) return;
    mine(typeof j.t === 'number' ? j.t : 0);
    if (typeof j.rev === 'number') e.rev = j.rev;
    if (j.set && j.set.base) e.set = j.set.base;
  });

  // ---------- the shoot menu ----------
  var gShoot = el('div', 'group'); gShoot.id = 'g-shoot';
  gShoot.appendChild(el('span', 'lbl', DW.shoot));
  var shootBtn = button('', 'shoot-btn', 'dz-strong');
  gShoot.appendChild(shootBtn);
  var gDesign = $('g-design');
  gDesign.parentNode.insertBefore(gShoot, gDesign);
  var going = false;
  var pShoots = makePop(shootBtn, 'shoot-pop', DW.shootsLabel, function(){
    var pop = pShoots.pop;
    pop.textContent = '';
    pop.appendChild(el('div', 'dz-pophead', DW.shootsHead));
    var list = el('div', 'dz-list');
    (D.S.shoots || []).forEach(function(s){
      if (typeof s.kit !== 'string' || !s.kit) return;
      var open = s.kit === D.KIT, a = el('a', 'dz-item' + (open ? ' cur' : ''));
      // a shoot is its kit folder's name; each shoot is a page of its own
      a.href = '/design.html?kit=' + encodeURIComponent(s.kit);
      a.dataset.open = open ? '1' : '';
      a.appendChild(el('b', '', s.name || s.kit));
      a.appendChild(el('small', '', DW.shootSub(s.photos || 0, s.designs || 0, open)));
      if (open) a.setAttribute('aria-current', 'page');
      list.appendChild(a);
    });
    pop.appendChild(list);
  });
  pShoots.pop.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a.dz-item') : null;
    if (!a) return;
    e.preventDefault();
    closePop(pShoots);
    if (a.dataset.open || going) return;
    // the open design is saved before the page is left (the browser is also handed it as the page goes)
    going = true;
    var href = a.getAttribute('href'), went = false;
    var go = function(){ if (went) return; went = true; window.location.assign(href); };
    D.save.flush().then(go, go);
    setTimeout(go, 4000);
  });

  // ---------- the design's name ----------
  var nameShow = $('d-name');
  var nameBox = el('input', 'dz-name'); nameBox.type = 'text'; nameBox.id = 'd-name-box';
  nameBox.maxLength = NAME_MAX; nameBox.spellcheck = false; nameBox.autocomplete = 'off';
  nameBox.setAttribute('aria-label', DW.nameLabel); nameBox.title = DW.nameLabel;
  nameBox.disabled = true;            // until a design is open
  nameShow.hidden = true;
  nameShow.parentNode.insertBefore(nameBox, nameShow.nextSibling);
  var nameAtFocus = null;
  // the name goes with every save of the design
  D.save.fields.push(function(body){ if (D.design && typeof D.design.name === 'string' && D.design.name) body.name = D.design.name; });
  function rename(name){
    if (!D.design || D.blocked || !name || name === D.design.name) return;
    D.design.name = name;
    nameShow.textContent = name;
    mine(Date.now() / 1000);
    D.save.queue();
  }
  nameBox.addEventListener('focus', function(){ nameAtFocus = D.design ? D.design.name : null; });
  nameBox.addEventListener('input', function(){ rename(cleanName(nameBox.value)); });       // an empty box changes nothing
  nameBox.addEventListener('blur', function(){ if (D.design) nameBox.value = D.design.name; nameAtFocus = null; });
  nameBox.addEventListener('keydown', function(e){
    if (e.key === 'Enter') { e.preventDefault(); nameBox.blur(); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (nameAtFocus) rename(nameAtFocus); nameBox.blur(); }
  });
  D.on('design', function(d){
    if (document.activeElement !== nameBox || nameBox.value === '') nameBox.value = d.name;
    nameBox.disabled = false;
    shootBtn.textContent = ((D.S && D.S.name) || D.KIT) + ' ▾';
    say('');
    if (D.S && D.S.fell_back) { D.S.fell_back = false; D.note(DW.fellBack, false); }
  });

  // ---------- My designs, Duplicate ----------
  var designsBtn = button(DW.myDesigns + ' ▾', 'designs-btn');
  var dupBtn = button(DW.dup, 'dup-design'); dupBtn.title = DW.dupTitle;
  gDesign.appendChild(designsBtn); gDesign.appendChild(dupBtn);
  function when(t){
    if (!(t > 0)) return '';
    var a = P.ago(t, Date.now() / 1000);
    if (a) return a;
    try { return new Date(t * 1000).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}); } catch (e) { return ''; }
  }
  var pDesigns = makePop(designsBtn, 'designs-pop', DW.designsLabel, function(){
    var pop = pDesigns.pop;
    pop.textContent = '';
    pop.appendChild(el('div', 'dz-pophead', DW.designsHead(D.S.name || '')));
    var list = el('div', 'dz-list');
    (D.S.designs || []).slice().sort(function(a, b){ return (b.t || 0) - (a.t || 0); }).forEach(function(d){
      if (typeof d.id !== 'string' || !/^[a-z0-9]{1,40}$/.test(d.id)) return;
      var open = d.id === D.design.id, bt = el('button', 'dz-item' + (open ? ' cur' : ''));
      bt.type = 'button'; bt.dataset.design = d.id;
      bt.appendChild(el('b', '', d.name));
      bt.appendChild(el('small', '', DW.designSub(d.slides, when(d.t), open)));
      list.appendChild(bt);
    });
    pop.appendChild(list);
  });
  var busy = false;         // a design is being opened or made
  function setBusy(on){ busy = on; dupBtn.disabled = on; newBtn.disabled = on; }
  pDesigns.pop.addEventListener('click', function(e){
    var bt = e.target.closest ? e.target.closest('button.dz-item') : null;
    if (!bt) return;
    closePop(pDesigns);
    if (busy || !D.design || bt.dataset.design === D.design.id) return;
    setBusy(true);
    var done = function(){ setBusy(false); };
    D.load(bt.dataset.design).then(done, done);
  });
  // A NEW design from the Assistant, then opened. body = what /design-new is sent (the token is added here).
  // -> a promise of '' when it opened, 'unsaved' or 'gone' when it was not made and nothing more is to be
  // said, or the words to show when it did not open.
  // A press is given up on after MAKE_WAIT, or when its gallery is closed (giveUp): from then on nothing it
  // was waiting for can make or open a design, so one never appears by itself long after the press.
  var MAKE_WAIT = 20000, making = 0;
  function giveUp(){ making += 1; }
  function makeDesign(body){
    var mine = ++making, sent = false;
    var gone = function(){ return mine !== making; };
    var work = D.save.flush().then(function(ok){
      if (gone()) return 'gone';
      if (!ok) return 'unsaved';        // the open design could not be saved: the line at the bottom of the window says why
      body.kit = D.KIT; body.token = newToken('n');
      sent = true;
      return post('/design-new', body, 3).then(function(res){
        if (gone()) return 'gone';
        var j = res.j;
        if (j && j.ok && j.design && typeof j.design.id === 'string') return D.load(j.design.id).then(function(){ return ''; });
        if (j && j.why === 'photos') { D.note(j.words || D.WORDS.photosChanged, true); return 'unsaved'; }
        return (j && j.words) || D.WORDS.cantReach;
      });
    });
    var late = new Promise(function(ok){ setTimeout(ok, MAKE_WAIT); }).then(function(){
      if (gone()) return 'gone';
      giveUp();
      return sent ? DW.makeSlow : DW.makeLate;
    });
    return Promise.race([work, late]).then(function(words){ if (!gone()) giveUp(); return words; });
  }
  dupBtn.addEventListener('click', function(){
    if (busy || !D.design || D.blocked) return;
    setBusy(true);
    var done = function(){ setBusy(false); };
    makeDesign({copy: D.design.id}).then(function(words){ if (words && words !== 'unsaved' && words !== 'gone') D.note(words, false); }).then(done, done);
  });

  // ---------- + New design, Save as template, Fill empty frames ----------
  var gNew = D.tools.group('g-new', '', 'tools-designs');
  var newBtn = D.tools.button(gNew, DW.newDesign, 'new-design'); newBtn.title = DW.newTitle;
  var tplBtn = D.tools.button(gNew, DW.saveTpl, 'save-template');
  var fillBtn = D.tools.button(gNew, DW.fill(0), 'fill-holes'); fillBtn.title = DW.fillTitle; fillBtn.disabled = true;
  var line = el('span', 'gline'); line.id = 'designs-line'; line.setAttribute('role', 'status');
  gNew.appendChild(line);
  function say(text){ line.textContent = text || ''; }
  D.on('change', function(){ say(''); });
  fillBtn.addEventListener('click', function(){
    if (!D.st || D.blocked) return;
    var next = P.fill(D.st, D.S.photos, D.S.carousel);
    if (next === D.st) { say(DW.fillNone); return; }
    var left = P.holes(next).length;
    D.setState(next);
    say(left ? DW.fillSome(left) : '');         // said after the change, which wipes the line of the press before
  });
  D.on('render', function(){
    var k = P.holes(D.st).length, text = DW.fill(k);
    if (fillBtn.textContent !== text) fillBtn.textContent = text;
    fillBtn.disabled = D.blocked || !k;
    tplBtn.disabled = D.blocked;
    if (!busy) { newBtn.disabled = D.blocked; dupBtn.disabled = D.blocked; }
  });

  // the gallery
  var gallery = D.modals.make('gallery');
  var sheet = el('div', 'dz-sheet'); sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-label', DW.galleryTitle);
  var top = el('div', 'dz-top'), head = el('div');
  head.appendChild(el('h2', '', DW.galleryTitle));
  var gSub = el('p', 'hint'); gSub.id = 'gallery-sub'; head.appendChild(gSub);
  var acts = el('div', 'dz-acts'), tickLabel = el('label', 'hint'), tick = el('input');
  tick.type = 'checkbox'; tick.id = 'gallery-fill'; tick.checked = true;
  tickLabel.appendChild(tick); tickLabel.appendChild(document.createTextNode(' ' + DW.fillTick));
  var gClose = button(DW.close, 'gallery-close');
  acts.appendChild(tickLabel); acts.appendChild(gClose);
  top.appendChild(head); top.appendChild(acts);
  var gLine = el('p', 'dz-say'); gLine.id = 'gallery-line'; gLine.setAttribute('role', 'status');
  sheet.appendChild(top); sheet.appendChild(gLine);
  var secs = {};
  [['fresh', DW.secFresh], ['mine', DW.secMine], ['starters', DW.secStarters]].forEach(function(x){
    sheet.appendChild(el('div', 'dz-sec', x[1]));
    var g = el('div', 'dz-grid'); g.id = 'gallery-' + x[0];
    sheet.appendChild(g);
    secs[x[0]] = g;
  });
  gallery.appendChild(sheet);
  var cards = [], cardShelf = null;
  // One card: a little picture of the layout, its name, what it holds, and Use.
  function card(box, name, sub, layout, start){
    var c = el('div', 'dz-card'), pic = el('div', 'dz-pic'), cv = document.createElement('canvas');
    var dpr = Math.min(2, window.devicePixelRatio || 1), s = P.cardScale(layout.slides, 256, 96);
    var w = Math.max(1, Math.round(layout.slides * M.W * s)), h = Math.max(1, Math.round(M.H * s));
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    cv.style.width = w + 'px'; cv.style.height = h + 'px';
    pic.appendChild(cv); c.appendChild(pic);
    var cap = el('div', 'dz-cap'), left = el('div');
    left.appendChild(el('b', '', name)); left.appendChild(el('small', '', sub));
    var use = button(DW.use, '', 'dz-use'); use.dataset.card = String(cards.length);
    use.setAttribute('aria-label', DW.use + ': ' + name);
    cap.appendChild(left); cap.appendChild(use); c.appendChild(cap);
    box.appendChild(c);
    cards.push(start);
    // drawn by the same function that draws a saved slide, from the small copies of this shoot's photos.
    // A layout with words is shown without them at once, and with them when their fonts are in.
    var ctx = cv.getContext('2d'), out = cv.width / (layout.slides * M.W), sh = cardShelf;
    var draw = function(words){
      return D.paint.strip(ctx, layout, {out: out, cap: 's', soft: true, holes: true, seams: true, shelf: sh, text: words}).then(null, function(){});
    };
    if (layout.blocks.some(M.isText)) draw(false).then(function(){ draw(true); }); else draw(true);
  }
  function buildGallery(){
    var S = D.S, fill = tick.checked;
    gSub.textContent = DW.gallerySub(S.name || '');
    cards = [];
    if (cardShelf) D.paint.letGo(cardShelf, null);
    cardShelf = D.paint.shelf();
    Object.keys(secs).forEach(function(k){ secs[k].textContent = ''; });
    var blank = M.tidy(S.blank || {slides: 5, bg: '#ffffff', blocks: []});
    card(secs.fresh, DW.blank, DW.blankSub(blank.slides), blank, function(){ return {stamp: S.stamp, state: blank}; });
    var one = P.onePerSlide(S.photos, S.carousel, S.slide_bg);
    card(secs.fresh, DW.onePer, DW.slidesSub(one.slides), one, function(){ return {}; });      // the Assistant makes this one itself
    var tpl = function(box, t, from){
      if (!t || !t.template || !Array.isArray(t.template.blocks)) return;
      var shown = P.fromTemplate(t.template, fill, S.photos, S.carousel);
      card(box, t.name || '', DW.tplSub(shown.slides, P.frames(shown), from), shown, function(){
        return {stamp: S.stamp, state: P.fromTemplate(t.template, tick.checked, S.photos, S.carousel)};
      });
    };
    if (!(S.templates || []).length) secs.mine.appendChild(el('p', 'hint', DW.noneYet));
    (S.templates || []).forEach(function(t){ tpl(secs.mine, t, typeof t.from === 'string' ? t.from : ''); });
    (S.starters || []).forEach(function(t){ tpl(secs.starters, t, ''); });
  }
  function closeGallery(){ D.modals.close(gallery); }
  newBtn.addEventListener('click', function(){
    if (busy || !D.S || !D.design || D.blocked) return;
    gLine.textContent = '';
    sheet.classList.remove('dz-busy');
    D.modals.open(gallery, function(){
      // closed while a new design was still being asked for: that press is given up on, and the buttons work again
      if (busy) { giveUp(); setBusy(false); sheet.classList.remove('dz-busy'); }
      if (cardShelf) { D.paint.letGo(cardShelf, null); cardShelf = null; }
      Object.keys(secs).forEach(function(k){ secs[k].textContent = ''; });
      try { newBtn.focus(); } catch (e) {}
    });
    buildGallery();
    sheet.scrollTop = 0;
    try { gClose.focus(); } catch (e) {}
    refresh().then(function(changed){ if (changed && D.modals.isOpen(gallery) && !busy) buildGallery(); });
  });
  gClose.addEventListener('click', closeGallery);
  tick.addEventListener('change', function(){ if (D.modals.isOpen(gallery) && !busy) buildGallery(); });
  sheet.addEventListener('click', function(e){
    var bt = e.target.closest ? e.target.closest('button.dz-use') : null;
    if (!bt || busy || bt.disabled) return;
    var start = cards[Number(bt.dataset.card)];
    if (!start) return;
    setBusy(true);
    sheet.classList.add('dz-busy');
    gLine.textContent = DW.making;
    var done = function(){ setBusy(false); sheet.classList.remove('dz-busy'); };
    makeDesign(start()).then(function(words){
      if (words === 'gone') return false;       // given up on (the gallery was closed): another press may be at work by now
      if (!words || words === 'unsaved') { closeGallery(); return true; }
      gLine.textContent = words;          // it could not be made: the gallery stays, with the reason
      return true;
    }).then(function(mine){ if (mine) done(); }, done);
  });

  // Save as template
  var tplModal = D.modals.make('tpl-dialog');
  var tSheet = el('div', 'dz-sheet dz-small'); tSheet.setAttribute('role', 'dialog'); tSheet.setAttribute('aria-label', DW.tplTitle);
  tSheet.appendChild(el('h2', '', DW.tplTitle));
  tSheet.appendChild(el('p', 'hint', DW.tplHint));
  var tRow = el('div', 'dz-fields');
  var tName = el('input', 'dz-in'); tName.type = 'text'; tName.id = 'tpl-name'; tName.maxLength = NAME_MAX; tName.autocomplete = 'off';
  tName.placeholder = DW.tplName; tName.setAttribute('aria-label', DW.tplName);
  var tSave = button(DW.tplSave, 'tpl-save', 'main'), tCancel = button(DW.cancel, 'tpl-cancel');
  tRow.appendChild(tName); tRow.appendChild(tSave); tRow.appendChild(tCancel);
  var tLine = el('p', 'dz-say'); tLine.id = 'tpl-line'; tLine.setAttribute('role', 'status');
  tSheet.appendChild(tRow); tSheet.appendChild(tLine);
  tplModal.appendChild(tSheet);
  var tBusy = false;
  tplBtn.addEventListener('click', function(){
    if (!D.st || !D.design || D.blocked) return;
    var empty = !D.st.blocks.length;
    tName.value = D.design.name || '';
    tName.disabled = empty; tSave.disabled = empty;
    tCancel.textContent = empty ? DW.close : DW.cancel;
    tLine.textContent = empty ? DW.tplEmpty : '';
    D.modals.open(tplModal, function(){ try { tplBtn.focus(); } catch (e) {} });
    try { if (empty) tCancel.focus(); else { tName.focus(); tName.select(); } } catch (e) {}
  });
  tCancel.addEventListener('click', function(){ D.modals.close(tplModal); });
  function saveTemplate(){
    if (tBusy || tSave.disabled || !D.st) return;
    var name = cleanName(tName.value);
    if (!name) { tLine.textContent = DW.nameBad; return; }
    tBusy = true; tSave.disabled = true; tLine.textContent = '';
    // the layout as it is on the page now; the Assistant takes the photos out and numbers the frames
    post('/design-template', {kit: D.KIT, token: newToken('t'), name: name, state: D.st}, 3).then(function(res){
      var j = res.j;
      tBusy = false;
      if (j && j.ok) {
        if (Array.isArray(j.templates) && D.S) D.S.templates = j.templates;
        tLine.textContent = j.words || '';
        tName.disabled = true;
        tCancel.textContent = DW.close;         // saved: nothing more to do here but close
        try { tCancel.focus(); } catch (e) {}
        return;
      }
      tSave.disabled = false;
      tLine.textContent = (j && j.words) || D.WORDS.cantReach;
    });
  }
  tSave.addEventListener('click', saveTemplate);
  tName.addEventListener('keydown', function(e){ if (e.key === 'Enter') { e.preventDefault(); saveTemplate(); } });

  D.designs = {refresh: refresh, cleanName: cleanName, closePops: closePops};
})();
"""

# The styles of the designs part: the name box, the pop-up lists, the sheets over the page, the gallery's cards.
DESIGN_DESIGNS_CSS = """
.dz-name{font:650 14.5px/1.3 var(--sans);width:200px;max-width:100%;border:1px solid var(--line);border-radius:8px;padding:6px 8px;background:#fff;color:var(--ink)}
.dz-name:focus,.dz-in:focus{outline:2px solid var(--sel);outline-offset:-1px}
.tb.dz-strong{font-weight:650;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dz-popwrap{position:relative;display:inline-flex;max-width:100%}
.dz-pop{position:absolute;top:calc(100% + 6px);left:0;z-index:30000;width:330px;max-width:calc(100vw - 24px);background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.18);padding:8px}
.dz-pop[hidden]{display:none}
.dz-pophead{font:600 11px/1.3 var(--sans);color:var(--soft);text-transform:uppercase;letter-spacing:.06em;padding:4px 8px 6px}
.dz-list{max-height:340px;overflow-y:auto;overscroll-behavior:contain}
.dz-item{display:block;width:100%;text-align:left;border:0;background:none;padding:8px;border-radius:8px;cursor:pointer;color:var(--ink);font:400 14px/1.35 var(--sans);text-decoration:none}
.dz-item:hover{background:var(--chip)}
.dz-item:focus-visible{outline:2px solid var(--sel);outline-offset:-2px}
.dz-item.cur{background:var(--chip);box-shadow:inset 3px 0 0 var(--sel)}
.dz-item b{display:block;font-weight:650;overflow-wrap:anywhere}
.dz-item small{color:var(--soft);font-size:12.5px}
.dz-modal{position:fixed;top:0;right:0;bottom:0;left:0;z-index:20000;background:rgba(42,38,34,.72);display:flex;align-items:center;justify-content:center;padding:16px}
.dz-modal[hidden]{display:none}
.dz-sheet{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:14px;width:1040px;max-width:100%;max-height:92vh;overflow:auto;overscroll-behavior:contain;padding:18px 20px;box-shadow:0 10px 40px rgba(0,0,0,.4)}
.dz-sheet.dz-small{width:500px}
.dz-sheet h2{margin:0 0 4px;font:650 19px/1.3 var(--sans)}
.dz-sheet .hint{font-size:13.5px}
.dz-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px 14px;flex-wrap:wrap}
.dz-top>div:first-child{flex:1 1 300px;min-width:0}
.dz-acts{display:flex;flex:0 1 auto;gap:10px;align-items:center;flex-wrap:wrap}
.dz-say{min-height:20px;margin:6px 0 2px;font-size:13.5px;line-height:20px;color:var(--accent-d)}
.dz-sec{font:650 12px/1.3 var(--sans);color:var(--soft);text-transform:uppercase;letter-spacing:.06em;margin-top:10px}
.dz-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:6px 0 12px}
@media(max-width:520px){.dz-grid{grid-template-columns:1fr}.dz-sheet{padding:14px}}
.dz-card{border:1px solid var(--line);border-radius:12px;padding:10px;background:var(--bg);display:flex;flex-direction:column;gap:8px;min-width:0}
.dz-pic{height:96px;display:flex;align-items:center;overflow:hidden;border-radius:6px;background:var(--line)}
.dz-pic canvas{display:block;flex:none}
.dz-cap{display:flex;justify-content:space-between;align-items:center;gap:8px}
.dz-cap b{display:block;font-weight:650;overflow-wrap:anywhere}
.dz-cap small{color:var(--soft);font-size:12.5px}
.dz-busy .dz-use{opacity:.4;pointer-events:none}
.dz-in{font:400 14px/1.3 var(--sans);border:1px solid var(--line);border-radius:8px;padding:8px 9px;background:#fff;color:var(--ink);width:240px;max-width:100%}
.dz-fields{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
"""
