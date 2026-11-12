#!/usr/bin/env python3
"""The talking reel page's script, step 1 (Nicole's handoff v24): Add my video, the videos in the Talking folder,
Edit my video, the status line, who places the photos, and the lines to copy into the chat. One string of
JavaScript and nothing else. It stands on talking_js_core.py (window.Talk).

Hers, kept:
  - the button always says Edit my video. On the video that is already edited it takes them to the edit; on
    another video it asks ONCE, on the page (never a browser pop-up: the app's pane shows none), and the second
    press goes ahead. The 3-second refresh never writes over that question while it shows.
  - the status line: the job's step and "A minute of video takes about a minute."; a problem in red; else
    "<video>: N words, X s of video, Y s after the cuts."
  - "Cut my talking reel for <short>" shows once there is a script the assistant has not cut ("cut" means the
    record's claude_cut is a list, even an empty one). With My assistant places them chosen and nothing cut yet,
    ONE line does both ("Cut my talking reel and place the photos for <short>") and the cut line hides.
Ours:
  - a video is chosen by its NAME and its key is looked up at the press (a file exported again has a new key);
  - a different video picked while the question shows takes the question away (in hers it stayed armed, and the
    next press on the first video went ahead without asking);
  - Edit my video on a video whose script is no longer ready (a problem, or the file exported again since) starts
    it again instead of scrolling to an edit that is not there;
  - a long refusal (a PC, the Mac's permission, no sound) stays in the status line until they do something,
    instead of a toast gone in 2.6 seconds; her two short ones are toasts, as hers;
  - choosing who places the photos is no Undo step;
  - a video still being copied into the folder is named under the row and can't be picked until it is whole.
"""

JS = r"""
(function(){
'use strict';
var T = window.Talk, W = T.W, $ = T.$;
var chosen = null;       // the NAME of the video picked in the row
var swapAsk = null;      // the name the "Edit ... instead?" question is about, while it shows
var said = null;         // a refusal from Edit my video that stays in the status line
var troubled = null;     // the Assistant could not be reached, or the record not read, before anything was shown

function hasWords(){ return !!(T.REC.words && T.REC.words.length); }
function wasCut(){ return Array.isArray(T.REC.claude_cut); }      // a list, even an empty one: the assistant has cut
function names(){ return (T.ST.videos || []).map(function(v){ return v.name; }); }
function keyOf(name){ var v = (T.ST.videos || []).filter(function(x){ return x.name === name; })[0]; return v ? v.key : null; }
function toEdit(){ $('editStep').scrollIntoView({behavior: 'smooth', block: 'start'}); }

function showVideos(){
  var st = T.ST, rec = T.REC, all = names(), box = $('vids');
  if (chosen == null || all.indexOf(chosen) < 0) chosen = all.indexOf(rec.video) >= 0 ? rec.video : (all[0] || null);
  if (swapAsk && (swapAsk !== chosen || swapAsk === rec.video || all.indexOf(swapAsk) < 0)) swapAsk = null;
  box.textContent = '';
  if (!all.length) { var none = document.createElement('span'); none.className = 'say'; none.textContent = W.no_videos; box.appendChild(none); }
  all.forEach(function(name){
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'vid' + (name === chosen ? ' on' : ''); b.textContent = name;
    b.setAttribute('aria-pressed', name === chosen ? 'true' : 'false');
    b.addEventListener('click', function(){ chosen = name; said = null; showVideos(); });
    box.appendChild(b);
  });
  var coming = $('coming'), late = st.coming || [];
  coming.textContent = '';
  late.forEach(function(c, i){ if (i) coming.appendChild(document.createElement('br')); coming.appendChild(document.createTextNode(T.fill(W.coming, {name: c.name}))); });
  coming.hidden = !late.length;
  $('startBtn').disabled = !chosen || !!st.working;
  var s = $('status');
  s.classList.remove('bad');
  if (swapAsk) T.rich(s, W.swap_ask, {'new': swapAsk, old: rec.video});       // never written over by a refresh
  // ours: while the Mac is asking its question the line is only that (her "a minute of video" would read oddly after it)
  else if ((st.working || rec.status === 'working') && rec.step === W.job_asking) T.rich(s, '{b}{step}{eb}', {step: rec.step});
  else if (st.working || rec.status === 'working') T.rich(s, W.status_working, {step: rec.step || W.working});
  else if (said) { s.textContent = said; s.classList.add('bad'); }
  // a job that stopped: its line, in red. (When this video had a script already, that script is still theirs to
  // edit and the record stays ready; the line is shown all the same, until Edit my video is pressed again.)
  else if (rec.status === 'problem' || rec.problem) { s.textContent = rec.problem || W.didnt_work; s.classList.add('bad'); }
  else if (hasWords() && st.video_state === 'changed') { s.textContent = W.job_changed; s.classList.add('bad'); }
  else if (hasWords())
    T.rich(s, W.status_ready + (T.P().length ? W.status_after : '.'),
           {video: rec.video, n: rec.words.length, dur: T.secs((rec.info || {}).dur || 0), after: T.secs(T.total())});
  else if (troubled) { s.textContent = troubled; s.classList.add('bad'); }
  else s.textContent = '';
}

function showWho(){
  var m = T.REC.photo_mode || '', cutFirst = hasWords() && !wasCut();
  $('whoMe').classList.toggle('on', m === 'me'); $('whoMe').setAttribute('aria-pressed', m === 'me' ? 'true' : 'false');
  $('whoAsst').classList.toggle('on', m === 'assistant'); $('whoAsst').setAttribute('aria-pressed', m === 'assistant' ? 'true' : 'false');
  $('placeAsk').hidden = m !== 'assistant';
  $('placeLine').textContent = T.fill(cutFirst ? W.cut_place_line : W.place_line, {short: T.DATA.short});
  $('placeSay').textContent = hasWords() ? W.place_say : W.place_say_wait;
  // the cut line: once there is a script the assistant has not cut; hidden when one line does both
  $('askCut').hidden = !hasWords() || wasCut() || (m === 'assistant' && cutFirst);
}

T.on('apply', function(){ troubled = null; if (T.ST.working) said = null; showVideos(); showWho(); });
T.on('trouble', function(words){ if (!T.loaded) { troubled = words; showVideos(); } });

$('addVideo').addEventListener('click', function(){
  T.post('/talking-open', {kit: T.KIT}).then(function(res){ T.toast((res.j && res.j.words) || W.didnt_work); },
                                              function(){ T.toast(W.cant_reach); });
});

$('startBtn').addEventListener('click', function(){
  if (!chosen || T.ST.working || !T.loaded) return;
  var rec = T.REC, done = hasWords(), same = done && rec.video === chosen;
  if (same && rec.status === 'ready' && T.ST.video_state !== 'changed') { toEdit(); return; }
  if (done && !same && swapAsk !== chosen) { swapAsk = chosen; said = null; showVideos(); return; }     // asked once, on the page
  var key = keyOf(chosen);                    // looked up now, never kept across a refresh
  if (!key) return;
  swapAsk = null; said = null;
  $('startBtn').disabled = true;
  T.post('/talking-start', {kit: T.KIT, video: key}).then(function(res){
    var j = res.j || {};
    if (j.ok) {
      if (!j.already && !j.back) $('status').textContent = W.job_ready_video;      // plain, as hers; the look that follows draws the step line
      return T.poll(true).then(function(){ if (j.already || j.back) toEdit(); });
    }
    if (j.why === 'gone' || j.why === 'working') T.toast(j.words || W.didnt_work);     // her two short lines
    else said = j.words || W.didnt_work;
    showVideos();
    return T.poll(true);
  }, function(){ T.toast(W.cant_reach); showVideos(); });
});

$('whoMe').addEventListener('click', function(){
  if (!T.loaded) return;                          // nothing can be chosen before the page has its state
  var off;
  T.save(function(){ off = T.REC.photo_mode === 'me'; return {photo_mode: off ? '' : 'me'}; }, {quiet: true})
    .then(function(ok){ if (ok === true && !off) T.toast(W.who_me_toast); });      // her toast only once it is saved
});
$('whoAsst').addEventListener('click', function(){            // click again to close
  if (!T.loaded) return;
  T.save(function(){ return {photo_mode: T.REC.photo_mode === 'assistant' ? '' : 'assistant'}; }, {quiet: true});
});
$('copyPlace').addEventListener('click', function(){ T.copy($('placeLine').textContent); });
$('copyCut').addEventListener('click', function(){ T.copy($('cutLine').textContent); });
T.step1 = {show: showVideos, chosen: function(){ return chosen; }};
})();
"""
