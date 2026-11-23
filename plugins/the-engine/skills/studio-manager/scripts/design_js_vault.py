#!/usr/bin/env python3
"""The designers' photo tray in My vault: grouped by shoot, like the vault's reel page (Nicole, Nov 23).

Nicole, on the vault's photos in the two designers, which were one pile of every photo: "group before launch so
its like the reels page". In My vault's carousel designer and stories designer the tray now is what the vault's
reel page shows in its photos step (reel_page.py, VAULT_PHOTOS_JS): "Added to my vault" open on top, then one fold
per shoot, shut, with the shoot's name and how many photos; a search box that opens only the shoots with a match
("3 found"), the shoot chips ("Every shoot" and one per shoot), her "Getting your photos ready to search" line on a
shoot still being looked at, and her line when nothing matches.

ONE COPY OF THE RULE. Nothing about the grouping or the search is decided here:
  * the data is the reel page's own answer, GET /reel-vault-photos?kit= (reel_page.vault_photos_for_page: the
    shoots, each photo's shoot and its text already folded the way search compares it, the everyday words search
    ignores). No path and no file name is in it;
  * the words are the reel page's own tables (vault_words() below reads them; nothing is spelled out here);
  * the function that turns what was typed into search words is taken out of the reel page's own script as text
    (search_words_js), so the two pages can never disagree about a search.
What is ours is only where the tiles go: the tray's own tiles (the strip part builds them, with their click,
drag, tick and "see it big") are MOVED into the folds, so everything a tile does works as it did.

Only the vault's page gets any of this (design_page.page_html(vault=True): the words, the styles and this script).
A plain shoot's designer is byte for byte what it was.

    Designer.vaultTray.look()      for the tests: what the tray shows, as names and numbers
"""
import re

# the reel page's keys the tray shows (hers, then ours on that page); read from its tables, never copied here
WORD_KEYS = ("vp_added", "vp_added_say", "vp_from", "vp_from_one", "vp_search_ph", "vp_search_label", "vp_loading",
             "vc_every", "vc_found", "vc_nothing", "one_photo", "photos")


def vault_words():
    """The tray's words, from the reel page's own tables (her WORDS, VAULT_CLIP_WORDS and VAULT_PICK_WORDS, our VAULT_PICK_OUR_WORDS)."""
    import reel_page
    w = {}
    for table in (reel_page.WORDS, reel_page.VAULT_CLIP_WORDS, reel_page.VAULT_PICK_WORDS, reel_page.VAULT_PICK_OUR_WORDS):
        w.update({k: table[k] for k in WORD_KEYS if k in table})
    return {k: w[k] for k in WORD_KEYS}


def search_words_js():
    """The reel page's own function that folds what was typed into search words, as text (function words(v){...})."""
    import reel_page
    m = re.search(r"\n  function words\(v\)\{\n.*?\n  \}\n", reel_page.VAULT_PHOTOS_JS, re.S)
    if not m:
        raise RuntimeError("the reel page's search-words function was not found")
    return m.group(0)


DESIGN_VAULT_CSS = r"""
.vfind{display:grid;gap:8px;margin:0 0 8px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
.vfind input[type=search]{width:100%;box-sizing:border-box;font:500 14px/1.2 var(--sans);padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg,#fff);color:var(--ink)}
.vchips{display:flex;gap:6px;flex-wrap:wrap}
.vchips button{border:1px solid var(--line);background:var(--chip);border-radius:999px;padding:5px 11px;font:600 12.5px/1.2 var(--sans);cursor:pointer;color:var(--soft)}
.vchips button.on{border-color:var(--accent);color:var(--accent-d)}
#thumbs.vp{display:block}
#thumbs.vpwait{display:none}
.vfold{border:1px solid var(--line);border-radius:12px;background:var(--panel);margin-top:8px}
.vfold>summary{display:flex;align-items:center;gap:9px;cursor:pointer;list-style:none;padding:8px 12px;font:600 14px/1.2 var(--sans)}
.vfold>summary::-webkit-details-marker{display:none}
.vfold>summary::before{content:'\203A';font-size:20px;line-height:1;color:var(--soft);width:12px;transition:transform .2s}
.vfold[open]>summary::before{transform:rotate(90deg)}
.vfold>summary img{width:30px;height:30px;border-radius:7px;object-fit:cover;background:var(--line)}
.vfold>summary small{font:500 12.5px/1.2 var(--sans);color:var(--soft)}
.vfold>summary .prog{color:var(--accent-d)}
.vfold>summary .hit{margin-left:auto;font:600 12px/1 var(--sans);color:var(--accent-d);border:1px solid var(--accent);border-radius:999px;padding:4px 8px}
.vfold.mine>summary{cursor:default}
.vfold.nohit{opacity:.6}
.vfold .line1{margin:0;padding:0 12px 10px;color:var(--soft);font-size:13px}
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:8px;align-items:start;padding:0 12px 12px}
.vgrid:empty{padding:0}
.vgrid.rest{padding:8px 0 0}
@media(max-width:520px){.vgrid{grid-template-columns:repeat(auto-fill,minmax(68px,1fr));gap:6px}}
.vgrid .th.off{display:none}
#vnone{margin:8px 0 0}
#vnone[hidden],#vwait[hidden],.vfold .line1[hidden],.vfold .hit[hidden]{display:none}
"""

# __WORDS_FN__ is the reel page's own function words(v), put in by vault_js().
_JS = r"""
(function(){
  'use strict';
  var D = window.Designer, $ = D.$, el = D.el, W = window.DESIGN_VAULT_WORDS;
  var thumbs = $('thumbs'), tray = $('tray');
  if (!W || !thumbs || !tray) return;
  var Q = 'kit=' + encodeURIComponent(document.body.dataset.kit);
  function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]; }); }
  function fill(s, o){ return String(s).replace(/\{(\w+)\}/g, function(m, k){ return o[k] === undefined ? m : o[k]; }); }
  // the search box and the shoot chips over the tray, her waiting line, and her line when nothing matches under it
  var find = el('div', 'vfind'); find.id = 'vfind';
  var q = document.createElement('input'); q.type = 'search'; q.id = 'vq'; q.autocomplete = 'off';
  q.setAttribute('aria-label', W.vp_search_label); q.placeholder = W.vp_search_ph;
  var chipsEl = el('div', 'vchips'); chipsEl.id = 'vshoots';
  find.appendChild(q); find.appendChild(chipsEl);
  var wait = el('p', 'hint', W.vp_loading); wait.id = 'vwait';
  var none = el('p', 'hint', W.vc_nothing); none.id = 'vnone'; none.hidden = true;
  tray.insertBefore(find, thumbs); tray.insertBefore(wait, thumbs);
  if (thumbs.nextSibling) tray.insertBefore(none, thumbs.nextSibling); else tray.appendChild(none);
  thumbs.classList.add('vpwait');
  var CAT = null, home = {}, text = {}, only = null, open = {}, loading = false, failed = false, laid = '', pollT = null, restTries = 0;
__WORDS_FN__
  function nPhotos(n){ return n === 1 ? W.vp_from_one : fill(W.vp_from, {n: n}); }
  function tilesNow(){ return Array.prototype.slice.call(thumbs.querySelectorAll('.th')); }
  function searching(){ return !!CAT && (words(q.value).length > 0 || only !== null); }
  function fold(key, cls){
    var d = document.createElement('details'); d.className = 'vfold' + (cls || ''); d.dataset.g = key;
    d.appendChild(document.createElement('summary'));
    return d;
  }
  // ---- the folds: built whenever the strip part builds its tiles again, and when the shoots change ----
  function layout(){
    var tiles = tilesNow();
    if (!CAT) {                                   // not read yet: the tiles wait, unseen; never read: the plain tray
      thumbs.classList.toggle('vpwait', !failed); thumbs.classList.remove('vp');
      wait.hidden = failed;
      return;
    }
    var frag = document.createDocumentFragment(), grids = {};
    var mine = fold('', ' mine'); mine.open = true;
    mine.querySelector('summary').innerHTML = esc(W.vp_added) + ' <small class="n"></small>';
    mine.querySelector('summary').onclick = function(e){ e.preventDefault(); };            // always open
    var here = el('p', 'line1', W.vp_added_say); mine.appendChild(here);
    grids[''] = el('div', 'vgrid'); mine.appendChild(grids['']);
    frag.appendChild(mine);
    CAT.shoots.forEach(function(s){
      if (s.kit === '') return;
      var d = fold(s.kit, '');
      d.querySelector('summary').innerHTML = (s.thumb ? '<img src="/kit-photo?' + Q + '&n=' + encodeURIComponent(s.thumb) + '&size=s" alt="">' : '') +
        '<span>' + esc(s.name) + '</span> <small class="n">' + esc(nPhotos(s.photos)) + '</small> <small class="prog"></small><span class="hit" hidden></span>';
      d.querySelector('summary').onclick = function(e){ if (d.classList.contains('nohit')) e.preventDefault(); };   // nothing found in it: it stays shut
      d.addEventListener('toggle', function(){ if (!searching()) open[s.kit] = d.open; });
      var img = d.querySelector('summary img'), tries = 0;
      if (img) img.onerror = function(){ if (++tries > 8) { img.style.visibility = 'hidden'; return; } var src = img.getAttribute('src').split('&t=')[0]; setTimeout(function(){ if (document.body.contains(img)) img.src = src + '&t=' + tries; }, 1500); };
      grids[s.kit] = el('div', 'vgrid'); d.appendChild(grids[s.kit]);
      frag.appendChild(d);
    });
    var rest = el('div', 'vgrid rest');           // a photo newer than what was read: shown, unfolded, until the next read
    tiles.forEach(function(t){ var k = home[+t.dataset.n]; (k !== undefined && grids[k] ? grids[k] : rest).appendChild(t); });
    thumbs.textContent = '';
    thumbs.appendChild(frag);
    if (rest.firstChild) { thumbs.appendChild(rest); if (++restTries <= 5) setTimeout(load, 800); } else restTries = 0;
    thumbs.classList.remove('vpwait'); thumbs.classList.add('vp');
    wait.hidden = true;
    laid = JSON.stringify(CAT.shoots.map(function(s){ return [s.kit, s.name, s.photos, s.thumb]; }));
    filter();
  }
  // ---- the search, the chips, the counts, her progress line ----
  function filter(){
    if (!CAT || !thumbs.classList.contains('vp')) return;
    var qw = words(q.value), on = qw.length > 0 || only !== null, total = 0;
    var chips = '<button type="button" data-s="-1" class="' + (only === null ? 'on' : '') + '">' + esc(W.vc_every) + '</button>' +
      CAT.shoots.map(function(s, i){ return s.kit === '' ? '' : '<button type="button" data-s="' + i + '" class="' + (only === s.kit ? 'on' : '') + '">' + esc(s.name) + '</button>'; }).join('');
    if (chipsEl.dataset.was !== chips) {
      chipsEl.dataset.was = chips; chipsEl.innerHTML = chips;
      chipsEl.querySelectorAll('button').forEach(function(b){ b.onclick = function(){ var i = +b.dataset.s; only = i < 0 ? null : CAT.shoots[i].kit; filter(); }; });
    }
    thumbs.querySelectorAll('details.vfold').forEach(function(d){
      var key = d.dataset.g, s = CAT.shoots.filter(function(x){ return x.kit === key; })[0], n = 0, count = 0;
      d.querySelectorAll('.th').forEach(function(t){
        var num = +t.dataset.n, hit = !on || ((only === null || key === only) && qw.every(function(w){ return (text[num] || '').indexOf(w) >= 0; }));
        t.classList.toggle('off', !hit); if (hit) n++;
        count++;
      });
      total += n;
      if (key === '') {
        d.querySelector('summary .n').textContent = count ? fill(count === 1 ? W.one_photo : W.photos, {n: count}) : '';
        d.querySelector('.line1').hidden = count > 0;
        return;
      }
      var nohit = on && !n, hitEl = d.querySelector('.hit'), prog = d.querySelector('.prog');
      d.classList.toggle('nohit', nohit);
      hitEl.hidden = !on || !n; hitEl.textContent = on && n ? fill(W.vc_found, {n: n}) : '';
      var want = on ? !nohit : !!open[key];
      if (d.open !== want) d.open = want;
      prog.textContent = (s && CAT.can && s.tagged < s.photos) ? fill(CAT.getting, {done: s.tagged, total: s.photos}) : '';
    });
    thumbs.querySelectorAll('.vgrid.rest .th').forEach(function(t){ t.classList.toggle('off', on); });
    none.hidden = !(on && !total);
  }
  function behind(){ return !!CAT && CAT.can && CAT.shoots.some(function(s){ return s.tagged < s.photos; }); }
  function load(){
    if (loading) return;
    loading = true;
    fetch('/reel-vault-photos?' + Q, {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
      loading = false;
      if (!j || !j.ok) { failed = !CAT; layout(); return; }
      failed = false; CAT = j; home = {}; text = {};
      j.photos.forEach(function(p){ home[p.n] = p.kit; text[p.n] = p.text; });
      var now = JSON.stringify(j.shoots.map(function(s){ return [s.kit, s.name, s.photos, s.thumb]; }));
      if (now !== laid || !thumbs.classList.contains('vp') || thumbs.querySelector('.vgrid.rest')) layout(); else filter();
      clearTimeout(pollT);
      if (behind()) pollT = setTimeout(load, 4000);          // her line counts up while the photos are looked at
    }).catch(function(){ loading = false; failed = !CAT; layout(); });
  }
  q.addEventListener('input', filter);
  // the strip part has just built the tray's tiles again (the first look, a new list): fold them, and read again
  D.on('adopt', function(a){ if (a && a.rebuild) { layout(); load(); } });
  // photos that joined the vault: their tiles were put at the end of the tray; they are folded once they are read
  D.on('photos-added', function(){ layout(); load(); });
  setInterval(function(){ if (!document.hidden && D.S && CAT && !behind()) load(); }, 20000);     // a description written from the chat is found without a reload
  D.vaultTray = {
    look: function(){
      return {ready: !!CAT && thumbs.classList.contains('vp'), only: only, photos: CAT ? CAT.photos.length : 0,
              folds: Array.prototype.map.call(thumbs.querySelectorAll('details.vfold'), function(d){
                return {kit: d.dataset.g, open: d.open, nohit: d.classList.contains('nohit'),
                        shown: Array.prototype.filter.call(d.querySelectorAll('.th'), function(t){ return !t.classList.contains('off'); }).map(function(t){ return +t.dataset.n; }),
                        all: d.querySelectorAll('.th').length, hit: d.querySelector('.hit') && !d.querySelector('.hit').hidden ? d.querySelector('.hit').textContent : ''};
              })};
    }
  };
})();
"""


def vault_js():
    """The script, with the reel page's own search-words function in it."""
    return _JS.replace("__WORDS_FN__", search_words_js().strip("\n"))
