#!/usr/bin/env python3
"""The carousel designer's page: See a photo big (Nicole's v27, Nov 14: "they're so small").

DESIGN_VIEW_JS (put on the page by design_page.py after the designs part, which gives it Designer.modals, and after the
strip part, whose tray tiles and click it uses) opens any tray photo big: a double-click on its tile, or its small ⤢
button, opens a dark window with the photo, its number, "already in this design" when it is, ‹ › and the arrow keys to
browse the shoot's photos in the tray's order (wrapping round), and one button that puts it in: "Use this photo" with
nothing selected (it goes in the next empty frame, or on the first empty slide), "Put it in the selected frame" with a
frame selected (that frame's photo is swapped). Close, Escape and a press beside the window change nothing. Nothing on
the strip moves while the window is open: the page's keys are off behind any sheet (Designer.quiet).

The picture is the Assistant's own made copy by its number (Designer.photoUrl, the 1600 copy): never a path, and
nothing is fetched that the Assistant does not already make. A single click on a tile waits 230 ms (hers) before it
puts the photo in, so a double-click does not also put it in; that wait is the strip part's (design_js_edit.py).

    Designer.big.open(n)       show photo n big
    Designer.big.close()
    Designer.big.isOpen()
    Designer.big.n()           the photo showing, or null
"""

DESIGN_VIEW_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, M = D.M, $ = D.$, el = D.el, WORDS = D.WORDS;

  // ---------- the window ----------
  var modal = D.modals.make('view');
  var prev = el('button', 'vw-arrow vw-l', '‹'); prev.type = 'button'; prev.id = 'view-prev'; prev.setAttribute('aria-label', WORDS.viewPrev);
  var next = el('button', 'vw-arrow vw-r', '›'); next.type = 'button'; next.id = 'view-next'; next.setAttribute('aria-label', WORDS.viewNext);
  var box = el('div', 'vw-box'); box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', WORDS.viewLabel);
  var img = document.createElement('img'); img.id = 'view-img'; img.alt = '';
  var bar = el('div', 'vw-bar');
  var num = el('b', '', ''); num.id = 'view-num';
  var used = el('span', '', ''); used.id = 'view-used';
  var useBtn = el('button', 'tb main', WORDS.viewUse); useBtn.type = 'button'; useBtn.id = 'view-use';
  var closeBtn = el('button', 'tb', WORDS.viewClose); closeBtn.type = 'button'; closeBtn.id = 'view-close';
  bar.appendChild(num); bar.appendChild(used); bar.appendChild(useBtn); bar.appendChild(closeBtn);
  box.appendChild(img); box.appendChild(bar);
  modal.appendChild(prev); modal.appendChild(box); modal.appendChild(next);

  var VIEW = null;        // the photo showing, or null
  function words(n){
    num.textContent = WORDS.viewNum(n);
    var inIt = D.st.blocks.some(function(b){ return M.isFrame(b) && b.n === n; });
    used.textContent = inIt ? WORDS.viewUsed : '';
    var b = D.selected();
    D.label(useBtn, b && M.isFrame(b) ? WORDS.viewPut : WORDS.viewUse);
  }
  function open(n){
    var p = D.by[n];
    if (!D.st || !p || !p.have) return;
    VIEW = n;
    var u = D.photoUrl(n, 'l');
    if (img.getAttribute('src') !== u) img.setAttribute('src', u);
    words(n);
    if (!D.modals.isOpen(modal)) D.modals.open(modal, function(){ VIEW = null; });
    D.focus(useBtn);
  }
  function close(){ D.modals.close(modal); }
  // the next or the previous photo, in the tray's order, round and round (hers)
  function step(d){
    if (VIEW == null || !D.S) return;
    var list = D.S.photos, i = -1, k;
    for (k = 0; k < list.length; k++) { if (list[k].n === VIEW) i = k; }
    if (i < 0 || !list.length) return;
    for (k = 1; k <= list.length; k++) {
      var q = list[((i + d * k) % list.length + list.length) % list.length];
      if (q && q.have) { open(q.n); return; }
    }
  }
  prev.addEventListener('click', function(){ step(-1); });
  next.addEventListener('click', function(){ step(1); });
  closeBtn.addEventListener('click', close);
  useBtn.addEventListener('click', function(){
    var n = VIEW;
    close();
    if (n != null && D.clickPhoto) D.clickPhoto(n);
  });
  // the arrow keys browse while the window is open (Escape closes it, as every sheet); the strip's keys are off meanwhile
  document.addEventListener('keydown', function(e){
    if (VIEW == null || !D.modals.isOpen(modal)) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); e.stopImmediatePropagation(); step(e.key === 'ArrowLeft' ? -1 : 1); }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);
  // the design changing under the window (another window's save arriving, a reload): the window closes
  D.on('design', function(){ if (D.modals.isOpen(modal)) close(); });
  D.on('photos', function(){ if (VIEW != null && D.by[VIEW] && !D.by[VIEW].have) close(); });

  D.big = {open: open, close: close, isOpen: function(){ return D.modals.isOpen(modal); }, n: function(){ return D.modals.isOpen(modal) ? VIEW : null; }};
})();
"""

# The window's styles (her look: a dark window, the photo as large as fits, the round arrows at the window's sides, white
# pill buttons) and the small ⤢ on every tray tile (shown while the pointer is over the tile, or when it has the keyboard).
DESIGN_VIEW_CSS = """
.th .see{position:absolute;right:4px;top:4px;width:24px;height:24px;border:0;border-radius:6px;background:rgba(0,0,0,.55);color:#fff;font:600 14px/24px var(--sans);cursor:zoom-in;opacity:0;transition:opacity .15s;padding:0}
.th:hover .see,.th .see:focus-visible{opacity:1}
@media(pointer:coarse){.th .see{opacity:1}}
#view.dz-modal{background:rgba(12,12,14,.92);padding:16px 72px}
.vw-box{position:relative;display:flex;flex-direction:column;align-items:center;gap:10px;max-width:100%}
#view-img{display:block;max-width:min(92vw,1400px);max-height:80vh;border-radius:8px;box-shadow:0 10px 40px rgba(0,0,0,.5);background:#222;-webkit-user-drag:none}
.vw-bar{display:flex;align-items:center;gap:10px;color:#fff;font-size:14px;flex-wrap:wrap;justify-content:center}
.vw-bar .tb{border:0;border-radius:999px;padding:8px 14px;font:600 13.5px/1 var(--sans);background:rgba(255,255,255,.14);color:#fff}
.vw-bar .tb.main{background:var(--accent)}
.vw-arrow{position:fixed;top:50%;transform:translateY(-50%);width:52px;height:52px;border-radius:50%;border:0;background:rgba(255,255,255,.14);color:#fff;font:400 30px/52px var(--sans);cursor:pointer;padding:0}
.vw-arrow.vw-l{left:12px}.vw-arrow.vw-r{right:12px}
.vw-arrow:hover,.vw-bar .tb:hover{background:rgba(255,255,255,.26)}
.vw-bar .tb.main:hover{background:var(--accent-d)}
"""
