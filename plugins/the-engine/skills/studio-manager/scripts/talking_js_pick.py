#!/usr/bin/env python3
"""The talking reel page's script, the two pickers (Nicole's handoff v24, pages/talking-reel.html, built our way):
the photo picker ("+ Add photos", "Change photos") and the video picker ("+ Add video", "Change video"). One
string of JavaScript and nothing else. It stands on talking_js_core.py and talking_js_script.py (window.Talk).

Hers, kept:
  - the photo picker: every photo of the shoot, numbered as on the sheet; pick one, or several to flash through
    the words in the order they were clicked (the number on each says its turn); "Use this photo" / "Use these N";
    Close, or a press outside the sheet, closes it and changes nothing;
  - a NEW stretch takes the spot, and where they put themselves, of any stretch it lies over; otherwise it is
    Full screen. Changing a stretch's photos keeps its spot, where it sits and where they sit. A new video always
    starts where videos sit by themselves (nothing kept of where a photo was dragged to);
  - the video picker: the videos in the shoot's Footage folder; click one and it plays, muted; "Starts at m:ss.t"
    follows the player; "Use from here" takes the moment the player is on, to a tenth of a second; clicking
    another video starts at 0; "Change video" opens on the video it has, at its start; Open my Footage folder and
    I added videos; Close, or a press outside the sheet;
  - while the picker is open the list is read again every 4 seconds ONLY while some video is still being got
    ready, and the list is never redrawn while the player is open (it would jump under their hand).
Ours:
  - the Footage list is asked for ONLY when the video picker opens (never as the page sits open: asking makes
    the Mac get every Footage video ready), from the reel page's own route with for=talking, which writes nothing;
  - a video is sent as the key the list gave, never a name or a place; a photo by its number;
  - the stretch being changed is looked up again by its start word when Use is pressed;
  - a video that is not ready yet can't be opened (hers opens a player with nothing in it); it can as soon as
    it is ready, the player open or not: what a new read brings changes each card where it is (its line, its
    still, whether it can be pressed) and the list itself is not drawn again. A video that could not be got
    ready says so in this page's own words (OUR_WORDS vp_cant, vp_lowspace), never the reel page's;
  - a photo whose small copy is not made yet: the page looks once more when the picker opens, and the script's
    part keeps looking every few seconds (T.on('photos')); each copy shows in its place when it is made;
  - T.pickerOpen() says whether either picker is open, so the keys (the spacebar, Delete) leave the page behind
    it alone (hers plays the talking video behind the open video picker).
"""

JS = r"""
(function(){
'use strict';
var T = window.Talk, W = T.W, $ = T.$, Q = T.Q;
var DONE = T.DATA.previewDone || ['ready'];     // the states in which a Footage video is no longer being got ready
var PICK = null;               // the photo picker: {a, b, old: the start word of the stretch being changed, ns: [photo numbers, in the order clicked]}
var VP = null;                 // the video picker: {a, b, old, v: the NAME of the video chosen, from}
var VIDS = [], looks = 0;

function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function isOpen(id){ return $(id).classList.contains('open'); }
function over(a, b){ for (var k = 0; k < T.SH.length; k++) if (T.SH[k].a <= b && T.SH[k].b >= a) return T.SH[k]; return null; }
T.pickerOpen = function(){ return isOpen('pick') || isOpen('vpick'); };

// ---------- the photo picker ----------
function showable(p){ return p.have || !p.missing; }
function pickGrid(){
  var g = $('pickGrid'); g.textContent = '';
  T.PHOTOS.filter(showable).forEach(function(p){
    var d = el('button', 'pk'); d.type = 'button'; d.setAttribute('data-n', p.n);
    var i = el('img'); i.alt = T.fill(W.pick_alt, {n: p.n}); i.loading = 'lazy'; i.draggable = false;
    if (p.have) i.src = T.photoUrl(p.n, 's');          // not made yet: asked for when it is (pickFresh), never a broken picture
    d.appendChild(i); d.appendChild(el('b'));
    d.addEventListener('click', function(){
      if (!PICK) return;
      var k = PICK.ns.indexOf(p.n);
      if (k >= 0) PICK.ns.splice(k, 1); else PICK.ns.push(p.n);
      pickMarks();
    });
    g.appendChild(d);
  });
  PICK.drawn = photoMark();
  pickMarks();
}
function photoMark(){ return T.PHOTOS.map(function(p){ return p.n + ':' + p.v + ':' + (p.have ? 1 : 0); }).join(','); }
// small copies made since the grid was drawn: each shows in its place, nothing is redrawn under their hand
function pickFresh(){
  if (!PICK || !isOpen('pick')) return;
  var same = T.PHOTOS.filter(showable).map(function(p){ return p.n; }).join(',') ===
             Array.prototype.map.call($('pickGrid').querySelectorAll('.pk'), function(d){ return d.getAttribute('data-n'); }).join(',');
  if (!same) { pickGrid(); return; }
  Array.prototype.forEach.call($('pickGrid').querySelectorAll('.pk'), function(d){
    var n = +d.getAttribute('data-n'), p = T.byN[n], i = d.querySelector('img'), src = p && p.have ? T.photoUrl(n, 's') : null;
    if (src && i.getAttribute('src') !== src) i.src = src;
  });
  PICK.drawn = photoMark();
}
T.on('photos', pickFresh);
function pickMarks(){
  Array.prototype.forEach.call($('pickGrid').querySelectorAll('.pk'), function(d){
    var k = PICK.ns.indexOf(+d.getAttribute('data-n'));
    d.classList.toggle('on', k >= 0);
    d.setAttribute('aria-pressed', k >= 0 ? 'true' : 'false');
    d.querySelector('b').textContent = k >= 0 ? k + 1 : '';
  });
  var n = PICK.ns.length;
  $('pickCount').textContent = n > 1 ? T.fill(W.pick_count, {n: n}) : '';
  $('pickUse').disabled = !n;
  $('pickUse').textContent = n > 1 ? T.fill(W.pick_use_many, {n: n}) : W.pick_use;
}
function openPick(a, b, old){
  PICK = {a: a, b: b, old: old ? old.a : null, ns: old ? (old.ns || []).slice() : []};
  $('pickHead').textContent = T.fill(W.pick_for, {words: T.wordsOf(a, b, 70)});
  pickGrid();
  $('pick').classList.add('open');
  // a small copy that was not made when the page last looked: one more look, now (the 3-second one waits while this is open)
  if (T.PHOTOS.some(function(p){ return !p.have && !p.missing; }))
    T.poll(true).then(pickFresh);
}
function closePick(){ $('pick').classList.remove('open'); PICK = null; }
$('pickUse').addEventListener('click', function(){
  var p = PICK;
  if (!p || !p.ns.length) return;
  closePick();
  T.SELSHOT = p.a;
  T.save(function(){
    var old = p.old != null ? T.findShot(p.old) : null;          // as it is now (the page re-reads every few seconds)
    var near = old || over(p.a, p.b);
    var keep = old ? {spot: old.spot, pos: old.pos, me: old.me} : {spot: near ? near.spot : 'full', pos: null, me: near ? near.me : null};
    var base = old ? T.SH.filter(function(x){ return x !== old; }) : T.SH;
    return {shots: T.shotsOut(T.setRange(base, p.a, p.b, {ns: p.ns.slice(), v: null, from: 0, spot: keep.spot, pos: keep.pos, me: keep.me}))};
  });
});
$('pickClose').addEventListener('click', closePick);
$('pick').addEventListener('click', function(e){ if (e.target === $('pick')) closePick(); });

// ---------- the video picker: the shoot's Footage folder ----------
function mmss(t){ t = Math.max(0, +t || 0); var s = Math.floor(t % 60); return Math.floor(t / 60) + ':' + (s < 10 ? '0' : '') + s; }
function waiting(v){ return DONE.indexOf(v.preview) < 0; }
function vidBy(name){ for (var k = 0; k < VIDS.length; k++) if (VIDS[k].name === name) return VIDS[k]; return null; }
function strip0(v){ return v.strip && v.strip[0] ? '/reel-strip?' + Q + '&key=' + encodeURIComponent(v.key) + '&n=' + encodeURIComponent(v.strip[0].n) : null; }
// an address inside a style: a shoot's name may hold a quote or a bracket (encodeURIComponent leaves ' ( ) as they are)
function cssUrl(u){ return 'url("' + String(u).replace(/["'()\\\s]/g, function(ch){ return '%' + ('0' + ch.charCodeAt(0).toString(16)).slice(-2).toUpperCase(); }) + '")'; }
function loadVids(){
  var mine = ++looks;
  return T.ask('/reel-footage?' + Q + '&for=talking').then(function(res){
    if (mine !== looks || !res.j || !Array.isArray(res.j.videos)) return false;
    VIDS = res.j.videos;
    var fresh = false;
    VIDS.forEach(function(v){ if (v.key && v.strip && v.strip[0] && T.STILLS[v.key] !== v.strip[0].n) { T.STILLS[v.key] = v.strip[0].n; fresh = true; } });
    if (fresh && VP) VP.stills = true;
    return true;
  }, function(){ return false; });
}
// a card as its video stands now: whether it can be opened, its line, its still, whether it is the one chosen.
// The line is this page's own (never the reel page's, whose words for a video that could not be got ready say
// its moments and the reel still work: not so here).
function paint(c, v){
  var ready = v.preview === 'ready' && !!v.key, still = strip0(v), vs = c.querySelector('.vs'), line = c.querySelector('span');
  var say = ready ? mmss(v.length) : T.fill(waiting(v) ? W.vp_wait : v.preview === 'lowspace' ? W.vp_lowspace : W.vp_cant, {length: mmss(v.length)});
  c.classList.toggle('on', !!(VP && VP.v === v.name));
  if (c.disabled !== !ready) c.disabled = !ready;
  if (line.textContent !== say) line.textContent = say;
  var bg = still ? cssUrl(still) : '';
  if (c.getAttribute('data-still') !== bg) {
    c.setAttribute('data-still', bg);
    vs.style.backgroundImage = bg; vs.textContent = still ? '' : '▶';
  }
}
function vpList(){
  var box = $('vpList'); box.textContent = '';
  if (!VIDS.length) { var none = el('p', 'say sm'); T.rich(none, W.vp_none); box.appendChild(none); return; }
  VIDS.forEach(function(v){
    var c = el('button', 'vcard'); c.type = 'button'; c.setAttribute('data-name', v.name);
    c.appendChild(el('div', 'vs')); c.appendChild(el('b', '', v.name)); c.appendChild(el('span'));
    c.addEventListener('click', function(){ choose(v.name); });
    paint(c, v);
    box.appendChild(c);
  });
}
// what a new read of the folder brought, without redrawing the list: each card changes where it is (a video that
// is ready now can be pressed, even with the player open). Only when the videos themselves are others is the
// list drawn again, and never by itself under an open player.
function vpFresh(mayRedraw){
  var cards = $('vpList').querySelectorAll('.vcard');
  var same = cards.length === VIDS.length && VIDS.length > 0 && VIDS.every(function(v, k){ return cards[k].getAttribute('data-name') === v.name; });
  if (same) { VIDS.forEach(function(v, k){ paint(cards[k], v); }); return; }
  if (mayRedraw) vpList();
}
function choose(name){
  var v = vidBy(name), pv = $('vpVid');
  if (!VP || !v || v.preview !== 'ready' || !v.key) return;
  if (VP.v !== v.name) VP.from = 0;                    // another video: from its beginning
  VP.v = v.name;
  vpFresh(true);
  var url = '/reel-video?' + Q + '&key=' + encodeURIComponent(v.key), from = VP.from || 0;
  $('vpPlayer').hidden = false;
  pv.muted = true;
  if (pv.dataset.src !== url) {
    pv.dataset.src = url; pv.src = url;
    pv.onloadedmetadata = function(){ try { pv.currentTime = from; } catch (e) {} showAt(); };
  } else { try { pv.currentTime = from; } catch (e) {} }
  showAt();
}
function at(){ var pv = $('vpVid'); return pv.readyState >= 1 ? pv.currentTime : ((VP && VP.from) || 0); }
function showAt(){ var t = at(); $('vpAt').textContent = T.fill(W.vp_at, {t: mmss(t) + '.' + Math.floor((t % 1) * 10)}); }
function openVPick(a, b, old){
  VP = {a: a, b: b, old: old ? old.a : null, v: old && old.v ? old.v.name : null, from: old ? old.from || 0 : 0};
  $('vpHead').textContent = T.fill(W.vp_for, {words: T.wordsOf(a, b, 60)});
  $('vpPlayer').hidden = true;
  try { $('vpVid').pause(); } catch (e) {}
  $('vpList').textContent = '';
  $('vpick').classList.add('open');
  var mine = VP;
  return loadVids().then(function(){
    if (VP !== mine || !isOpen('vpick')) return;
    vpList();
    if (VP.v) choose(VP.v);          // "Change video": the video it has, at its start point
  });
}
function closeVPick(){
  try { $('vpVid').pause(); } catch (e) {}
  $('vpick').classList.remove('open');
  var fresh = VP && VP.stills;
  VP = null;
  // a video's first still that was not known before: its bar in the script can show it now
  if (fresh && T.ready() && !T.selectedWords() && T.SH.some(function(x){ return x.v; })) T.renderScript();
}
$('vpVid').addEventListener('timeupdate', showAt);
$('vpVid').addEventListener('seeked', showAt);
$('vpClose').addEventListener('click', closeVPick);
$('vpick').addEventListener('click', function(e){ if (e.target === $('vpick')) closeVPick(); });
$('vpOpen').addEventListener('click', function(){
  // the reel page's own route; her line for THIS page is the short one (ours beside it when the folder opened behind the window)
  T.post('/reel-open', {kit: T.KIT, what: 'footage'}).then(function(res){
    var j = res.j || {};
    T.toast(j.ok ? W.footage_open + (String(j.words || '').indexOf(W.behind) >= 0 ? W.behind : '') : (j.words ? W.cant_open : W.didnt_work));
  }, function(){ T.toast(W.cant_reach); });
});
$('vpRefresh').addEventListener('click', function(){ var mine = VP; loadVids().then(function(){ if (VP === mine && isOpen('vpick')) vpList(); }); });
$('vpUse').addEventListener('click', function(){
  var p = VP, v = p && p.v && vidBy(p.v);
  if (!v || !v.key) return;
  var from = Math.round(at() * 10) / 10, sent = {key: v.key, name: v.name};
  closeVPick();
  T.SELSHOT = p.a;
  T.save(function(){
    var old = p.old != null ? T.findShot(p.old) : null;
    var near = old || over(p.a, p.b);
    var base = old ? T.SH.filter(function(x){ return x !== old; }) : T.SH;
    return {shots: T.shotsOut(T.setRange(base, p.a, p.b, {ns: [], v: sent, from: from, spot: near ? near.spot : 'full', pos: null, me: near ? near.me : null}))};
  }).then(function(ok){ if (ok === true) T.jumpToWord(p.a); });
});
// while the picker is open, videos show as they get ready; never under an open player
T.vpTimer = setInterval(function(){
  if (!isOpen('vpick') || !VIDS.some(waiting)) return;
  var mine = VP;
  loadVids().then(function(got){ if (got && VP === mine && isOpen('vpick')) vpFresh($('vpPlayer').hidden); });
}, T.DATA.footageEvery || 4000);

T.openPick = openPick; T.openVPick = openVPick; T.closePick = closePick; T.closeVPick = closeVPick;
T.vids = function(){ return VIDS; };
})();
"""
