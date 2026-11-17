#!/usr/bin/env python3
"""The carousel designer's page: the Crop window (Nicole's v27, Nov 14: "we don't have an actual cropping tool on the photo").

DESIGN_CROP_JS (put on the page by design_page.py after the designs and save parts, which give it Designer.modals and
the selection bar's Crop group) adds the Crop button to that group, between Show the whole photo and Move photo
inside, and the window it opens: the whole photo with a box over it. Drag a corner to cut off the edges, drag inside
the box to move it; only what is inside the box shows on the slide. "Keep the frame's shape" (on to start with) keeps
the box the frame's shape, corners only; unticked, eight handles, and the frame on the slide takes the box's shape
inside the space it had. "Show the whole photo" sets the box to as much of the photo as the shape allows. Done maps
the box onto the frame's zoom and crop (DesignModel.cropApply: the zoom can go past the Zoom slider's 300%, up to a
box 4% of the photo), one Undo step and one save, and says her line. Cancel, Escape, and a press beside the window
leave the photo as it was.

The maths are the model's (cropFromBlock, cropResize, cropMove, fitLocked, cropApply), proved without a browser; this
file only draws the box and listens. The picture is the Assistant's own made copy, by its number (Designer.photoUrl):
never a path. Her window reads the small copy and swaps in the full one; ours draws the sharper made copy (1600 on
its long edge), which is sharper than the window ever shows it. Nothing here keeps anything in the browser.

    Designer.crop.open()       what the Crop button does (design_js_edit.py hands the press here)
    Designer.crop.isOpen()
    Designer.crop.box()        the box now, as fractions of the photo (for the tests), or null
"""

DESIGN_CROP_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, $ = D.$, el = D.el;
  // her words (pages/carousel-designer.html, v27), whole; in the stories designer "slide" reads "story" (decision 20)
  var CW = D.WORDS.crop = D.storyWords({
    title: 'Crop',
    btn: 'Crop',
    btnTitle: 'See the whole photo and drag the edges to crop it',
    hint: 'Drag a corner to cut off the edges you don\'t want, and drag inside the box to move it. Only what\'s inside the box shows on your slide.',
    lock: 'Keep the frame\'s shape',
    whole: 'Show the whole photo',
    cancel: 'Cancel',
    done: 'Done',
    lockHint: 'Untick Keep the frame\'s shape to crop each side on its own. The frame on your slide changes shape to match.',
    cropped: 'Cropped. Undo takes it back.',
    label: 'Crop the photo'
  });

  // ---------- the window ----------
  var modal = D.modals.make('crop');
  var sheet = el('div', 'dz-sheet cr-sheet'); sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-label', CW.label);
  var wrap = el('div', 'cr-wrap'); wrap.id = 'crop-wrap';
  var img = document.createElement('img'); img.id = 'crop-img'; img.alt = '';        // never dragged by the browser (the styles say so; the page never uses the browser's drag-and-drop)
  var box = el('div', 'cr-box'); box.id = 'crop-box';
  ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'].forEach(function(h){ var i = el('i'); i.dataset.h = h; box.appendChild(i); });
  wrap.appendChild(img); wrap.appendChild(box);
  var bar = el('div', 'cr-bar');
  var lockLab = el('label', 'hint cr-chk'), lock = document.createElement('input');
  lock.type = 'checkbox'; lock.id = 'crop-lock'; lock.checked = true;
  lockLab.appendChild(lock); lockLab.appendChild(document.createTextNode(' ' + CW.lock));
  var allBtn = el('button', 'tb', CW.whole); allBtn.type = 'button'; allBtn.id = 'crop-all';
  var cancelBtn = el('button', 'tb', CW.cancel); cancelBtn.type = 'button'; cancelBtn.id = 'crop-cancel';
  var doneBtn = el('button', 'tb main', CW.done); doneBtn.type = 'button'; doneBtn.id = 'crop-done';
  bar.appendChild(lockLab); bar.appendChild(allBtn); bar.appendChild(el('span', 'cr-sp')); bar.appendChild(cancelBtn); bar.appendChild(doneBtn);
  var lockHint = el('p', 'hint cr-lockhint', CW.lockHint); lockHint.id = 'crop-hint';
  sheet.appendChild(el('h2', '', CW.title)); sheet.appendChild(el('p', 'hint', CW.hint));
  sheet.appendChild(wrap); sheet.appendChild(bar); sheet.appendChild(lockHint);
  modal.appendChild(sheet);

  // The box now: {id, n, pw, ph, ar, x, y, w, h}. pw, ph = the photo's own size; ar = the frame's shape (w / h);
  // x, y, w, h = the box as fractions of the photo. null while the window is closed.
  var CR = null, drag = null;
  function k(){ return M.cropK(CR.ar, CR.pw, CR.ph); }
  function set(r){ CR.x = r.x; CR.y = r.y; CR.w = r.w; CR.h = r.h; }
  function draw(){
    if (!CR) return;
    var bw = img.clientWidth, bh = img.clientHeight;
    box.style.left = CR.x * bw + 'px'; box.style.top = CR.y * bh + 'px';
    box.style.width = CR.w * bw + 'px'; box.style.height = CR.h * bh + 'px';
  }
  function open(){
    var b = D.selected();
    if (!b || D.blocked || D.typeOf(b) !== 'photo' || M.isHole(b) || !D.by[b.n] || !D.by[b.n].have) return;
    // the photo's own shape, as the strip draws it (the loaded picture's; the list's numbers until then)
    var node = document.querySelector('#strip .blk[data-id="' + b.id + '"]'), nat = D.blockTypes.photo.natural(node, b);
    CR = M.merge(M.cropFromBlock(b, nat.w, nat.h), {id: b.id, n: b.n, pw: nat.w, ph: nat.h, ar: b.w / b.h});
    drag = null;
    lock.checked = true; modal.classList.add('locked');
    img.onload = draw;
    var u = D.photoUrl(b.n, 'l');
    if (img.getAttribute('src') !== u) img.setAttribute('src', u);
    D.modals.open(modal, function(){ CR = null; drag = null; });
    draw();
    D.focus(doneBtn);
  }
  function close(){ D.modals.close(modal); }

  // ---------- the box under the hand ----------
  wrap.addEventListener('pointerdown', function(e){
    if (!CR || drag || e.button !== 0 || e.isPrimary === false || !e.target.closest || !e.target.closest('#crop-box')) return;
    e.preventDefault(); e.stopPropagation();
    try { wrap.setPointerCapture(e.pointerId); } catch (x) {}
    drag = {pid: e.pointerId, h: e.target.dataset.h || 'move', sx: e.clientX, sy: e.clientY, o: {x: CR.x, y: CR.y, w: CR.w, h: CR.h}};
  });
  wrap.addEventListener('pointermove', function(e){
    if (!drag || !CR || e.pointerId !== drag.pid) return;
    var bw = img.clientWidth, bh = img.clientHeight;
    if (!(bw > 0 && bh > 0)) return;
    var dx = (e.clientX - drag.sx) / bw, dy = (e.clientY - drag.sy) / bh;
    set(drag.h === 'move' ? M.cropMove(drag.o, dx, dy) : M.cropResize(drag.o, drag.h, dx, dy, lock.checked ? k() : null));
    draw();
  });
  function end(e){ if (drag && (!e || e.pointerId === drag.pid)) drag = null; }
  wrap.addEventListener('pointerup', end); wrap.addEventListener('pointercancel', end);
  window.addEventListener('blur', function(){ drag = null; });
  window.addEventListener('resize', draw);

  lock.addEventListener('change', function(){
    modal.classList.toggle('locked', lock.checked);
    // ticked again: the largest box of the frame's shape around where the box is now
    if (lock.checked && CR) { set(M.fitLocked(k(), CR.x + CR.w / 2, CR.y + CR.h / 2, CR.w)); draw(); }
  });
  allBtn.addEventListener('click', function(){
    if (!CR) return;
    set(lock.checked ? M.fitLocked(k(), 0.5, 0.5, 1) : {x: 0, y: 0, w: 1, h: 1});
    draw();
  });
  cancelBtn.addEventListener('click', close);
  doneBtn.addEventListener('click', function(){
    if (!CR) return;
    var cr = M.merge(CR, {}), locked = lock.checked, b = M.find(D.st, cr.id);
    close();
    if (!b || D.blocked || M.isHole(b)) return;
    var p = M.cropApply(b, cr, cr.pw, cr.ph, D.st.slides, locked);
    if (D.setState(function(st){ return M.patch(st, b.id, p); }, {sel: b.id, adjust: false})) D.selbar.line(CW.cropped);
  });

  // ---------- the button, in the Crop group between Show the whole photo and Move photo inside (her order) ----------
  var group = $('sel-crop'), adj = $('adjust');
  var cropBtn = D.selbar.button(group, CW.btn, 'crop', CW.btnTitle);
  cropBtn.id = 'crop-btn';
  if (adj && adj.parentNode === group) group.insertBefore(cropBtn, adj);
  D.on('render', function(){
    var b = D.selected(), p = b && D.typeOf(b) === 'photo' && !M.isHole(b) ? D.by[b.n] : null;
    cropBtn.disabled = !!b && !(p && p.have);
  });
  // the design changing under the window (another window's save arriving, a reload): the window closes rather than crop a photo that may be gone
  D.on('design', function(){ if (CR) close(); });

  D.crop = {open: open, close: close, isOpen: function(){ return D.modals.isOpen(modal); }, box: function(){ return CR ? M.merge(CR, {}) : null; }};
})();
"""

# The window's styles (her look: the whole photo, a box with a white outline and thirds, 16 px white handles, the rest dimmed).
DESIGN_CROP_CSS = """
.dz-sheet.cr-sheet{width:940px}
.cr-wrap{position:relative;display:block;width:max-content;max-width:100%;margin:10px auto;user-select:none;-webkit-user-select:none;touch-action:none;overflow:hidden;border-radius:6px}
#crop-img{display:block;max-width:100%;max-height:66vh;pointer-events:none;-webkit-user-drag:none}
.cr-box{position:absolute;box-shadow:0 0 0 9999px rgba(0,0,0,.55);outline:2px solid #fff;cursor:move;background-image:linear-gradient(rgba(255,255,255,.35) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.35) 1px,transparent 1px);background-size:33.333% 33.333%;background-position:-1px -1px}
.cr-box i{position:absolute;width:16px;height:16px;margin:-8px 0 0 -8px;background:#fff;border-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.4);touch-action:none}
.cr-box i::after{content:'';position:absolute;top:-6px;right:-6px;bottom:-6px;left:-6px}
.cr-box i[data-h=nw]{left:0;top:0;cursor:nwse-resize}.cr-box i[data-h=ne]{left:100%;top:0;cursor:nesw-resize}
.cr-box i[data-h=sw]{left:0;top:100%;cursor:nesw-resize}.cr-box i[data-h=se]{left:100%;top:100%;cursor:nwse-resize}
.cr-box i[data-h=n]{left:50%;top:0;cursor:ns-resize}.cr-box i[data-h=s]{left:50%;top:100%;cursor:ns-resize}
.cr-box i[data-h=w]{left:0;top:50%;cursor:ew-resize}.cr-box i[data-h=e]{left:100%;top:50%;cursor:ew-resize}
#crop.locked .cr-box i[data-h=n],#crop.locked .cr-box i[data-h=s],#crop.locked .cr-box i[data-h=w],#crop.locked .cr-box i[data-h=e]{display:none}
.cr-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:6px}
.cr-bar .cr-sp{flex:1}
.cr-chk{font-size:13.5px;color:var(--ink)}
.cr-lockhint{margin:6px 0 0}
"""
