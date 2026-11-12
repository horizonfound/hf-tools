#!/usr/bin/env python3
"""The shoots section of the morning report: what came off the card as
shoots, each with a few previews, a short recap, and a name to give it.
report_page.py includes it between the numbers and the "where" card, so
there is one page, not two. Talking is the way to fill the names in (the
Claude app has the mic); the boxes are there for a spelling.

Reads _studio/groups.json (the time-gap groups and their previews) and
_studio/shoots.json (which groups Claude merged into one shoot, a recap, a
suggested name, and the folder once sorted). Names they lock in are kept
in _studio/names.json by serve_report.py and shown filled in next time.

    python3 first_look.py "<session folder>"     writes a one-line page that just opens report.html
"""
import html
import re
import json
import sys
from datetime import datetime
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
import clips  # noqa: E402  (which files are video, and how to say a count)
this_computer.utf8_output()

CSS = """
.talk{display:grid;grid-template-columns:auto 1fr;gap:1.1rem;align-items:center;background:var(--sun-l);border-radius:var(--r);padding:1.3rem 1.5rem;margin:1.8rem 0 0}
.talk .mic{width:54px;height:54px;border-radius:50%;background:var(--coral);color:#fff;display:grid;place-items:center;flex:none}
.talk .mic svg{width:24px;height:24px}
.talk h3{font:600 18px/1.25 var(--sans);letter-spacing:-.015em;margin-bottom:.25rem}
.talk p{color:var(--ink-2);font-size:15px}
.talk .eg{font:400 17px/1.4 var(--sans);color:var(--ink);margin-top:.35rem}
.shoots-head{display:grid;gap:.5rem;padding-top:clamp(2rem,4vw,3rem)}
.shoots-head .h2{font:600 clamp(28px,3.6vw,44px)/1.05 var(--sans);letter-spacing:-.03em;text-wrap:balance}
.shoots{display:grid;gap:1.5rem;padding:1.6rem 0 1rem}
.shoot{display:grid;gap:clamp(.8rem,1.6vw,1.1rem);background:var(--paper);border-radius:var(--r);padding:clamp(1.2rem,2.6vw,2rem)}
.shoot .top{display:grid;grid-template-columns:1.05fr 1fr;gap:clamp(1.2rem,3vw,2.4rem);align-items:center}
.shoot:nth-child(even) .top{grid-template-columns:1fr 1.05fr}
.shoot:nth-child(even) .gal{order:2}
.gal{display:grid;gap:1.2rem;align-content:start}.gal .peeks-line{padding:0 .3rem}
.pics.six{grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);aspect-ratio:1/1.05;gap:.6rem}
.pics.six .ph:first-child{grid-row:1/3;grid-column:1/3}
.shoot:nth-child(even) .pics.six .ph:first-child{grid-column:2/4}
.more{display:grid;gap:.6rem}
.more .row{display:grid;grid-template-columns:repeat(5,1fr);gap:clamp(.6rem,1.6vw,1.1rem);padding:.6rem 0 .4rem;align-items:end}
.more .ph{border-radius:18px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.more .ph:nth-child(2n){margin-bottom:1.1rem}
.more .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow);z-index:1}
.more img{width:100%;height:100%;object-fit:cover;display:block}
.more .line{font-size:14px;color:var(--ink-2);margin:0}.more .line b{color:var(--ink)}
.shoot .note{margin:0}
.peeks-line{font-size:14px;color:var(--ink-2);margin:0;line-height:1.5}.peeks-line b{color:var(--ink)}
@media(max-width:900px){.pics.six{aspect-ratio:auto}}
.pics{position:relative;display:grid;grid-template-columns:1.35fr 1fr;grid-template-rows:1fr 1fr;gap:.7rem;aspect-ratio:5/4}
.pics .ph{border-radius:20px;overflow:hidden;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.pics .ph:first-child{grid-row:1/3}
.pics .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow);z-index:1}
.pics img{width:100%;height:100%;object-fit:cover}
.pics .chip{z-index:2}
.pics .ph.clip{position:relative}
.pics .ph.clip::after{content:'';position:absolute;left:50%;top:50%;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;background:rgba(20,22,28,.55);pointer-events:none}
.pics .ph.clip::before{content:'';position:absolute;left:50%;top:50%;z-index:1;margin:-11px 0 0 -7px;border-style:solid;border-width:11px 0 11px 18px;border-color:transparent transparent transparent #fff;pointer-events:none}
.pics .ph.clip{cursor:pointer}
.clips-row{display:flex;flex-wrap:wrap;align-items:baseline;gap:.4rem 1rem;padding:0 .3rem;font:500 14.5px/1.4 var(--sans)}
.clips-row .all-clips{color:var(--coral-2,#b9542f);font-weight:600;background:none;border:0;padding:0;cursor:pointer;font:inherit;font-weight:600;text-decoration:underline;text-underline-offset:3px}
.clips-row .clips-hint{color:var(--soft,#7a7067)}
.clips-row .clips-state{flex-basis:100%;color:var(--ink);min-height:1.2em}
.shoot .novid{display:grid;place-items:center;text-align:center;aspect-ratio:5/4;border-radius:20px;background:var(--sand-l);color:var(--soft,#7a7067);font:500 15px/1.4 var(--sans);padding:1.5rem;position:relative}
.copy{display:grid;gap:.9rem}
.copy .n{font:600 40px/1 var(--sans);letter-spacing:-.03em;font-variant-numeric:tabular-nums;color:var(--coral-2)}
.copy .meta{display:flex;flex-wrap:wrap;gap:.45rem}
.tag{font:500 12px/1 var(--sans);padding:.5rem .8rem;border-radius:999px;background:var(--cream)}
.tag.sun{background:var(--sun-l)}.tag.ocean{background:var(--ocean-l)}
.recap{font-size:16.5px;line-height:1.55;color:var(--ink-2);max-width:32em;text-wrap:pretty}
.name{display:grid;gap:.45rem}
.name label{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.name .field{position:relative;display:flex;gap:.6rem;align-items:stretch}
.name .field input{flex:1;min-width:0}
.name .go{flex:none;border:0;border-radius:18px;padding:0 1.3rem;background:var(--coral);color:#fff;font:600 16px/1 var(--sans);cursor:pointer;box-shadow:0 10px 24px -18px rgba(240,127,90,.9);transition:transform .3s var(--ease),opacity .3s}
.name .go:hover{transform:translateY(-1px)}
.name .go:disabled{opacity:.45;cursor:default;transform:none}
.name .state{font-size:13px;color:var(--ink-2);min-height:1.2em}.name .state.on{color:var(--ink)}.name .state.bad{color:#b4472e}
.name .pen{position:absolute;left:1.05rem;top:50%;transform:translateY(-50%);color:var(--coral);font-size:20px;pointer-events:none}
.name input{text-overflow:ellipsis;font:600 clamp(17px,1.7vw,21px)/1.2 var(--sans);letter-spacing:-.01em;color:var(--ink);background:var(--paper);border:2px dashed var(--coral);border-radius:18px;padding:.75rem 1rem .75rem 2.9rem;width:100%;outline:none;cursor:text;box-shadow:0 10px 24px -18px rgba(240,127,90,.8);transition:border-color .3s,background .3s,box-shadow .3s}
.name input:hover{background:var(--sun-l)}
.name input:focus{border-style:solid;border-color:var(--coral);background:var(--paper);box-shadow:0 0 0 4px rgba(240,127,90,.18)}
.name input::placeholder{color:#9AA0AB;font-weight:400;font-style:italic;font-family:var(--sans);font-size:.72em;letter-spacing:0}
.name input.hint::placeholder{color:#B9BEC8;font-weight:600;font-style:normal;font-size:1em;letter-spacing:-.02em}
.name small{color:var(--ink-2);font-size:13px}.name small b{color:var(--ink);font-weight:600}
.queue{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem .8rem;margin-top:.9rem;font-size:14px;color:var(--ink-2)}
.queue .add{font:600 14px/1 var(--sans);padding:.7rem 1.1rem;border-radius:999px;border:1.5px solid var(--coral);background:transparent;color:var(--coral-2);cursor:pointer;transition:background .2s,color .2s}
.queue .add:hover{background:var(--coral);color:#fff}
.queue .queued b{color:var(--ink)}
.queue .change,.queue .never{font:500 13px var(--sans);background:none;border:0;color:var(--ink-2);cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:0}
.queue .change:hover,.queue .never:hover{color:var(--coral-2)}
.queue .queued{display:block;width:100%}
.queue .show-queue{display:inline-flex;align-items:center;gap:.35rem;font:600 12.5px/1 var(--sans);color:var(--coral-2);text-decoration:none;margin:.7rem 0 0;padding:.42rem .75rem;border:1.5px solid rgba(212,100,63,.45);border-radius:999px;white-space:nowrap;transition:background .2s,color .2s,border-color .2s}
.queue .show-queue:hover{background:var(--coral);border-color:var(--coral);color:#fff}
.queue .pick{display:inline-flex;flex-wrap:wrap;align-items:center;gap:.6rem;background:var(--sun-l);border-radius:16px;padding:.55rem .8rem;animation:pop .4s var(--ease)}
.queue .pick[hidden]{display:none}
.queue .pick label{display:inline-flex;align-items:center;gap:.45rem;font:600 13px/1 var(--sans);color:var(--ink-2)}
.queue input[type=date]{font:500 14px var(--sans);border:1.5px solid var(--ink);border-radius:999px;padding:.4rem .8rem;background:var(--paper);color:var(--ink)}
.queue .save{font:600 13px/1 var(--sans);padding:.55rem .9rem;border-radius:999px;border:1.5px solid var(--coral);background:var(--coral);color:#fff;cursor:pointer}
.queue .save:disabled{opacity:.4;cursor:default}
.queue .qstate{font-size:13px;min-height:1.2em}.queue .qstate.bad{color:#b4472e}
@keyframes pop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
.peeks-wrap{display:grid;gap:.6rem;padding:0 .3rem}.peeks-act{display:flex;gap:.5rem;flex-wrap:wrap}
.pk{font:600 13px/1 var(--sans);padding:.5rem .9rem;border-radius:999px;border:1.5px solid var(--ink);background:var(--paper);color:var(--ink);cursor:pointer}
.pk.send,.pk.use{background:var(--coral);border-color:var(--coral);color:#fff}.pk:disabled{opacity:.4;cursor:default}
.peeks-ask{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;background:var(--sun-l);border-radius:16px;padding:.6rem .8rem;animation:pop .4s var(--ease)}.peeks-ask[hidden]{display:none}
.peeks-ask input{flex:1 1 16em;font:500 14px var(--sans);border:1.5px solid var(--sand);border-radius:10px;padding:.5rem .7rem;background:var(--paper)}
.peeks-more{background:var(--sun-l);border-radius:16px;padding:.8rem;animation:pop .4s var(--ease)}.peeks-more[hidden]{display:none}
.peeks-more .hint{margin:0 0 .6rem;font-size:13px;color:var(--ink-2)}
.peeks-more .cands{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:.5rem}
.peeks-more .cand{position:relative;border-radius:10px;overflow:hidden;aspect-ratio:1;background:var(--sand-l);cursor:pointer;outline:3px solid transparent;transition:outline-color .2s}
.peeks-more .cand img{width:100%;height:100%;object-fit:cover;display:block}
.peeks-more .cand.on{outline-color:var(--coral)}.peeks-more .cand .k{position:absolute;top:.35rem;left:.35rem;min-width:1.4rem;height:1.4rem;border-radius:999px;background:var(--coral);color:#fff;font:700 12px/1.4rem var(--sans);text-align:center;display:none;padding:0 .3rem}
.peeks-more .cand.on .k{display:block}
.peeks-more .cand .now{position:absolute;left:.35rem;bottom:.35rem;font:600 10.5px/1 var(--sans);letter-spacing:.01em;background:rgba(31,36,48,.78);color:#fff;padding:4px 7px;border-radius:999px;pointer-events:none}
.peeks-more .cand{transition:outline-color .2s,opacity .25s}.peeks-more .cands.full .cand:not(.on){opacity:.42}
.peeks-more .pfoot .n.warn{color:var(--coral-2);font-weight:600}.peeks-more .pk[hidden]{display:none}
.peeks-more .pfoot{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-top:.7rem;font-size:13px;color:var(--ink-2)}
.peeks-more .hint b{color:var(--ink)}
.peeks-more .slots{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin:.1rem 0 1rem}
.peeks-more .slot{position:relative;aspect-ratio:1;border-radius:12px;background:rgba(255,255,255,.6);outline:2px dashed rgba(31,36,48,.22);outline-offset:-2px;display:grid;place-items:center;transition:transform .15s}
.peeks-more .slot .cand{position:absolute;inset:0;aspect-ratio:auto;border-radius:12px}
.peeks-more .slot>.k{position:absolute;top:.35rem;left:.35rem;min-width:1.4rem;height:1.4rem;border-radius:999px;background:rgba(31,36,48,.45);color:#fff;font:700 12px/1.4rem var(--sans);text-align:center;padding:0 .3rem}
.peeks-more .slot .empty{font-size:12.5px;line-height:1.3;color:var(--ink-2);text-align:center;padding:1.2rem .6rem 0}
.peeks-more .slot.over{outline:3px solid #E9B93B;outline-offset:2px;transform:scale(.95)}
.peeks-more .cand{cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none;outline:0}
.peeks-more .cand img{pointer-events:none;-webkit-user-drag:none}
.peeks-more .cand .k{display:block}
.peeks-more .cand.dragging{opacity:.28}
.peeks-more .cand:hover{box-shadow:0 0 0 3px var(--coral)}
.peeks-more .cands{grid-template-columns:repeat(auto-fill,minmax(128px,1fr));border-radius:12px;max-height:60vh;overflow:auto;padding:3px}
.peeks-more .cands.over{outline:2px dashed var(--coral);outline-offset:3px}
.peeks-more .plabel{margin:0 0 .5rem;font:600 12.5px/1.2 var(--sans);color:var(--ink);display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.peeks-more .plabel .c{font-weight:400;color:var(--ink-2)}
.peeks-more .lk{margin-left:auto;border:0;background:none;padding:0;font:600 12.5px/1.2 var(--sans);color:var(--coral-2);text-decoration:underline;cursor:pointer}
body.pk-drag,body.pk-drag *{cursor:grabbing!important}
.pk-lift{position:fixed;left:0;top:0;z-index:9999;pointer-events:none;border-radius:12px;overflow:hidden;box-shadow:0 0 0 3px #fff,0 24px 48px -12px rgba(31,36,48,.55)}
.pk-lift img{width:100%;height:100%;object-fit:cover;display:block}
.pkbig{position:fixed;inset:0;z-index:9998;background:rgba(20,22,28,.84);display:none;place-items:center;padding:3vh 6vw}
.pkbig.on{display:grid}
.pkbig .box{position:relative;display:grid;gap:.8rem;justify-items:center}
.pkbig img{max-width:min(88vw,900px);max-height:72vh;border-radius:14px;display:block;background:#222}
.pkbig .acts{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;justify-content:center;color:#fff;font:500 14px/1.2 var(--sans)}
.pkbig .acts .sep{margin-left:.7rem;opacity:.75}
.pkbig .pk{background:#fff;border-color:#fff}
.pkbig .pk.spot{min-width:2.3rem;padding:.5rem 0}
.pkbig .pk.spot.cur{background:var(--coral);border-color:var(--coral);color:#fff;opacity:1}
.pkbig .pk.out{margin-left:.7rem;background:transparent;color:#fff}
.pkbig .x,.pkbig .nav{position:absolute;border:0;background:rgba(255,255,255,.94);color:#1F2430;width:2.5rem;height:2.5rem;border-radius:999px;font-size:1.5rem;line-height:1;cursor:pointer}
.pkbig .x{top:-.9rem;right:-.9rem}.pkbig .nav{top:calc(36vh - 1.25rem)}.pkbig .prev{left:-3.2rem}.pkbig .next{right:-3.2rem}
.peeks-more .cand .now{white-space:nowrap}
@media(max-width:700px){.pkbig .prev{left:-.6rem}.pkbig .next{right:-.6rem}}
.peeks-state{font-size:13px;color:var(--ink-2);min-height:1.2em;margin:0}.peeks-state.bad{color:#b4472e}.peeks-state.on{color:var(--ink)}
.save{display:flex;flex-wrap:wrap;align-items:center;gap:1rem;padding:1.2rem 0 .6rem}
.btn{display:inline-flex;align-items:center;gap:1.1rem;padding:.7rem .7rem .7rem 1.9rem;border-radius:999px;background:var(--coral);color:#fff;font:600 22px/1 var(--sans);letter-spacing:-.01em;border:1.5px solid var(--coral);cursor:pointer;box-shadow:0 18px 36px -20px rgba(240,127,90,.9);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.btn:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.btn .arr{width:48px;height:48px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:22px}
.toast{font-size:14px;color:var(--ink-2);min-height:1.2em}
.undo{font-size:13px;color:var(--ink-2);max-width:40em;margin-bottom:1.5rem}
@media(max-width:900px){.shoot .top,.shoot:nth-child(even) .top{grid-template-columns:1fr}.shoot:nth-child(even) .pics{order:0}.talk{grid-template-columns:1fr}.more .row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.more .row{grid-template-columns:repeat(2,1fr)}}
"""

PICKER = r"""<script>
// "Show me more" (Dustin, Nov 5, third pass). Your six sit in numbered spots, in order. Drag one to move it,
// drag a photo from below onto a spot to swap it in, drag one out to empty its spot. Click any photo to see it
// big; from there it can be put in a spot or taken out without dragging at all.
window.peekPicker=function(more,id,d,say){
 if(more._ac)more._ac.abort();if(more._big)more._big.remove();
 const ac=more._ac=new AbortController(),sig={signal:ac.signal};
 const E=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;};
 let photos=d.photos.slice(),by={};const index=()=>{by={};photos.forEach(p=>{by[p.n]=p;});};index();
 const start=(d.picked||[]).filter(n=>by[n]).slice(0,6);while(start.length<6)start.push(null);
 let slots=start.slice(),showingAll=!d.from_shortlist;
 const pool=()=>photos.filter(p=>!slots.includes(p.n));
 const changed=()=>slots.join()!==start.join();
 more.innerHTML='';
 const hint=E('p','hint'),row=E('div','slots'),lab=E('p','plabel'),grid=E('div','cands'),foot=E('div','pfoot');
 hint.innerHTML='<b>Your six, in order.</b> Drag one to move it. Drag a photo from below onto a spot to swap it in. Click any photo to see it big.';
 foot.innerHTML='<button class="pk use" type="button">Use these</button><button class="pk reset" type="button">Put it back the way it was</button><button class="pk cancel2" type="button">Never mind</button><span class="n"></span>';
 more.append(hint,row,lab,grid,foot);
 const tile=(n,k)=>{const t=E('div','cand');t.dataset.n=n;t.innerHTML='<img src="'+by[n].preview+'" alt="" draggable="false">'+(k?'<span class="k">'+k+'</span>':'')+(k===1?'<span class="now">the big one</span>':'');return t;};
 function draw(){
  row.innerHTML='';
  slots.forEach((n,i)=>{const s=E('div','slot');s.dataset.i=i;if(n!=null)s.appendChild(tile(n,i+1));else s.innerHTML='<span class="k">'+(i+1)+'</span><span class="empty">Drag a photo here</span>';row.appendChild(s);});
  grid.innerHTML='';pool().forEach(p=>grid.appendChild(tile(p.n,0)));
  const extra=d.moments&&d.moments>photos.length&&!showingAll;
  lab.innerHTML=(showingAll?'Every moment from this shoot':'The others I narrowed it to')+' <span class="c">'+pool().length+'</span>'+(extra?'<button class="lk all" type="button">See every moment ('+d.moments+')</button>':'');
  const a=lab.querySelector('.all');if(a)a.addEventListener('click',loadAll);
  const empty=slots.indexOf(null),nn=foot.querySelector('.n');
  nn.textContent=empty>=0?'Spot '+(empty+1)+' is empty. Drag a photo into it.':(changed()?'Happy with these? Press Use these.':'These are the six on the report now.');
  foot.querySelector('.use').disabled=empty>=0||!changed();foot.querySelector('.reset').hidden=!changed();
 }
 async function loadAll(){
  try{const r=await fetch('/peeks-more?shoot='+encodeURIComponent(id)+'&all=1',{cache:'no-store'});if(!r.ok)throw 0;const x=await r.json();photos=x.photos;index();showingAll=true;draw();}
  catch(e){foot.querySelector('.n').textContent='Could not load them all right now.';}}
 // photo n into spot i: from below, whatever was there goes back below; from another spot, the two trade places
 function put(n,i){const j=slots.indexOf(n);if(j===i)return;if(j>=0){slots[j]=slots[i];slots[i]=n;}else slots[i]=n;draw();}
 function takeOut(n){const j=slots.indexOf(n);if(j>=0){slots[j]=null;draw();}}

 // dragging, drawn by the page itself (the app's pane and the browser's own drag do not get along)
 let dg=null;
 const clearMarks=()=>{row.querySelectorAll('.over').forEach(o=>o.classList.remove('over'));grid.classList.remove('over');};
 more.addEventListener('pointerdown',e=>{const t=e.target.closest('.cand');if(!t||e.button)return;dg={t,n:+t.dataset.n,x:e.clientX,y:e.clientY,on:false,to:null};e.preventDefault();},sig);
 document.addEventListener('pointermove',e=>{if(!dg)return;
  if(!dg.on){if(Math.hypot(e.clientX-dg.x,e.clientY-dg.y)<7)return;dg.on=true;const r=dg.t.getBoundingClientRect();dg.ox=dg.x-r.left;dg.oy=dg.y-r.top;
   dg.lift=E('div','pk-lift','<img src="'+by[dg.n].preview+'" alt="">');dg.lift.style.width=r.width+'px';dg.lift.style.height=r.height+'px';document.body.appendChild(dg.lift);
   dg.t.classList.add('dragging');document.body.classList.add('pk-drag');}
  dg.lift.style.transform='translate('+(e.clientX-dg.ox)+'px,'+(e.clientY-dg.oy)+'px) scale(1.06)';
  const u=document.elementFromPoint(e.clientX,e.clientY),s=u&&u.closest('.slot'),g=u&&u.closest('.cands'),from=slots.indexOf(dg.n);
  clearMarks();dg.to=null;
  if(s&&row.contains(s)&&+s.dataset.i!==from){s.classList.add('over');dg.to=+s.dataset.i;}
  else if(g===grid&&from>=0){grid.classList.add('over');dg.to='out';}
 },sig);
 const drop=cancel=>{if(!dg)return;const x=dg;dg=null;document.body.classList.remove('pk-drag');clearMarks();
  if(!x.on){if(!cancel)openBig(x.n);return;}
  x.lift.remove();x.t.classList.remove('dragging');
  if(cancel||x.to==null)return;if(x.to==='out')takeOut(x.n);else put(x.n,x.to);};
 document.addEventListener('pointerup',()=>drop(false),sig);
 document.addEventListener('pointercancel',()=>drop(true),sig);
 window.addEventListener('blur',()=>drop(true),sig);

 // seeing one big, and moving it without dragging
 const big=more._big=E('div','pkbig','<div class="box"><button class="x" type="button" aria-label="Close">&#215;</button><button class="nav prev" type="button" aria-label="Previous">&#8249;</button><img alt=""><button class="nav next" type="button" aria-label="Next">&#8250;</button><div class="acts"></div></div>');
 document.body.appendChild(big);
 let at=null;
 const order=()=>slots.filter(n=>n!=null).concat(pool().map(p=>p.n));
 const spots=cur=>[0,1,2,3,4,5].map(k=>'<button class="pk spot'+(k===cur?' cur':'')+'" type="button" data-k="'+k+'"'+(k===cur?' disabled':'')+'>'+(k+1)+'</button>').join('');
 const closeBig=()=>big.classList.remove('on');
 function openBig(n){at=n;const i=slots.indexOf(n);big.querySelector('img').src=by[n].preview;
  big.querySelector('.acts').innerHTML=i>=0
   ?'<span>Number '+(i+1)+' of your six'+(i===0?', the big one':'')+'.</span><span class="sep">Move it to spot</span>'+spots(i)+'<button class="pk out" type="button">Take it out</button>'
   :'<span>Not one of your six.</span><span class="sep">Put it in spot</span>'+spots(-1);
  big.classList.add('on');}
 big.addEventListener('click',e=>{const b=e.target.closest('button');
  if(!b){if(e.target===big)closeBig();return;}
  if(b.classList.contains('x'))closeBig();
  else if(b.classList.contains('nav')){const o=order(),i=o.indexOf(at);openBig(o[(i+(b.classList.contains('next')?1:-1)+o.length)%o.length]);}
  else if(b.classList.contains('out')){takeOut(at);openBig(at);}
  else if(b.classList.contains('spot')){put(at,+b.dataset.k);openBig(at);}});
 document.addEventListener('keydown',e=>{if(!big.classList.contains('on'))return;
  if(e.key==='Escape'){e.stopPropagation();closeBig();}else if(e.key==='ArrowRight')big.querySelector('.next').click();else if(e.key==='ArrowLeft')big.querySelector('.prev').click();},sig);

 foot.querySelector('.reset').addEventListener('click',()=>{slots=start.slice();draw();});
 foot.querySelector('.cancel2').addEventListener('click',()=>{closeBig();more.hidden=true;});
 foot.querySelector('.use').addEventListener('click',async()=>{
  try{const r=await fetch('/peeks-choose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shoot:id,nums:slots})});if(!r.ok)throw 0;
   closeBig();more.hidden=true;say('Saving your picks...','on');
   const t=setInterval(async()=>{try{const q=await fetch('/picks-status',{cache:'no-store'});const all=await q.json();const s2=all[id];if(!s2)return;say(s2.line,s2.state==='problem'?'bad':'on');
    if(s2.state==='done'||s2.state==='problem'){clearInterval(t);if(s2.state==='done')setTimeout(()=>location.reload(),1200);}}catch(e){}},1200);}
  catch(e){say('Could not reach the Assistant. Tell Claude instead.','bad');}});
 draw();
};
</script>"""

SCRIPT = """<script>
(()=>{
const states={};
const stateEl=id=>document.querySelector('.state[data-for="'+id+'"]');
function show(id,st){const el=stateEl(id);if(!el)return;el.textContent=st.line||'';el.className='state'+(st.state==='problem'?' bad':(st.state==='done'?' on':''));
 const b=document.querySelector('.go[data-shoot="'+id+'"]');if(b)b.disabled=(st.state==='queued'||st.state==='running');}
async function rename(id){const inp=document.getElementById(id);const name=inp.value.trim()||(inp.dataset.was||'').trim();
 if(name){inp.value=name;inp.dataset.was=name;inp.placeholder=inp.dataset.hint||inp.placeholder;inp.classList.remove('hint');inp.blur();}
 if(!name){show(id,{state:'problem',line:'Type a name first.'});return;}
 if(!location.protocol.startsWith('http')){show(id,{state:'problem',line:'Open this page through the Assistant to rename here, or just tell Claude the name.'});return;}
 try{const r=await fetch('/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shoot:id,name})});
  if(!r.ok)throw 0;show(id,{state:'queued',line:'Renaming...'});poll();}
 catch(e){show(id,{state:'problem',line:'Could not reach the Assistant. Tell Claude the name instead.'});}}
let timer=null;
async function poll(){if(timer)return;timer=setInterval(async()=>{try{const r=await fetch('/rename-status',{cache:'no-store'});const st=await r.json();let busy=false;
 for(const id in st){show(id,st[id]);if(st[id].state==='queued'||st[id].state==='running')busy=true;}
 if(!busy){clearInterval(timer);timer=null;}}catch(e){}},1500);}
document.querySelectorAll('.go').forEach(b=>{b.addEventListener('mousedown',ev=>ev.preventDefault());b.addEventListener('click',()=>rename(b.dataset.shoot));});
document.querySelectorAll('.name input').forEach(i=>{i.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();rename(i.id);}});
 // click in: the box clears and the current name waits underneath in grey; type to replace it, click away to keep it (Dustin, Oct 28)
 i.addEventListener('focus',()=>{if(i.value){i.dataset.was=i.value;if(i.dataset.hint===undefined)i.dataset.hint=i.placeholder;i.placeholder=i.value;i.value='';i.classList.add('hint');}});
 // click away without pressing Rename (or Enter): back to the name it had, typed or not. Only Rename makes a name stick.
 i.addEventListener('blur',ev=>{if(ev.relatedTarget&&ev.relatedTarget.dataset&&ev.relatedTarget.dataset.shoot===i.id)return;
  if(i.dataset.was!==undefined){i.value=i.dataset.was;i.placeholder=i.dataset.hint||'';i.classList.remove('hint');}});});
if(location.protocol.startsWith('http'))poll();
// the editing queue button: a calendar opens right there, they pick a date, it saves (Dustin, Oct 28)
function niceDate(iso){const d=new Date(iso+'T12:00:00');return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'})}
// "Show my editing queue": ask the Assistant for the queue page's address (it starts the page if it isn't up) and open it
async function wireShow(a,st){if(!a)return;a.addEventListener('click',async ev=>{ev.preventDefault();
  if(!location.protocol.startsWith('http')){st.textContent='Ask Claude to show your editing queue.';st.className='qstate bad';return;}
  try{const r=await fetch('/queue-url',{cache:'no-store'});const d=await r.json();if(!d.url)throw 0;location.href=d.url;}
  catch(e){st.textContent='Could not open the queue page. Ask Claude to show your editing queue.';st.className='qstate bad';}});}
document.querySelectorAll('.queue .show-queue').forEach(a=>wireShow(a,a.closest('.queue').querySelector('.qstate')));
// The sneak peeks are a first pass (Dustin, Nov 5): Pick again with a note, or Show me more and choose your own six.
document.querySelectorAll('.peeks-wrap').forEach(w=>{
 const id=w.dataset.shoot,ask=w.querySelector('.peeks-ask'),more=w.querySelector('.peeks-more'),st=w.querySelector('.peeks-state'),inp=ask.querySelector('input');
 const live=location.protocol.startsWith('http');
 const say=(t,c)=>{st.textContent=t;st.className='peeks-state'+(c?' '+c:'')};
 w.querySelector('.again').addEventListener('click',()=>{more.hidden=true;ask.hidden=!ask.hidden;if(!ask.hidden)inp.focus()});
 ask.querySelector('.cancel').addEventListener('click',()=>{ask.hidden=true});
 ask.querySelector('.send').addEventListener('click',async()=>{
  if(!live){say('Open this page through the Assistant for this, or just tell Claude: "pick different sneak peeks for the beach shoot."','bad');return;}
  try{const r=await fetch('/peeks-again',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shoot:id,note:inp.value})});
   if(!r.ok)throw 0;const d=await r.json();ask.hidden=true;say(d.words||'Got it.','on');}
  catch(e){say('Could not reach the Assistant. Tell Claude instead.','bad');}});
 w.querySelector('.more').addEventListener('click',async()=>{
  ask.hidden=true;if(!more.hidden){more.hidden=true;return;}
  if(!live){say('Open this page through the Assistant for this, or tell Claude "show me more from the beach shoot."','bad');return;}
  say('');
  try{const r=await fetch('/peeks-more?shoot='+encodeURIComponent(id),{cache:'no-store'});if(!r.ok)throw 0;const d=await r.json();
   window.peekPicker(more,id,d,say);more.hidden=false;}
  catch(e){say('Could not load more right now. Tell Claude "show me more from this shoot."','bad');}});
});
document.querySelectorAll('.queue').forEach(q=>{
 const id=q.dataset.shoot,pick=q.querySelector('.pick'),inp=q.querySelector('input'),save=q.querySelector('.save'),st=q.querySelector('.qstate');
 const open=()=>{pick.hidden=false;const a=q.querySelector('.add');if(a)a.hidden=true;inp.focus();try{inp.showPicker()}catch(e){}};
 const close=()=>{pick.hidden=true;const a=q.querySelector('.add');if(a)a.hidden=false;};
 q.querySelectorAll('.add,.change').forEach(b=>b.addEventListener('click',open));
 q.querySelector('.never').addEventListener('click',close);
 inp.addEventListener('input',()=>{save.disabled=!inp.value});
 save.addEventListener('click',async()=>{if(!inp.value)return;
  if(!location.protocol.startsWith('http')){st.textContent='Open this page through the Assistant to add it, or just tell Claude.';st.className='qstate bad';return;}
  save.disabled=true;
  try{const r=await fetch('/queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shoot:id,due:inp.value})});
   if(!r.ok)throw 0;const d=await r.json();
   const was=q.querySelector('.queued');if(was)was.remove();const a=q.querySelector('.add');if(a)a.remove();
   pick.hidden=true;
   const span=document.createElement('span');span.className='queued';span.innerHTML='In your editing queue, due <b>'+niceDate(d.due)+'</b>. <button class="change" type="button">Change the date</button> <a class="show-queue" href="#">Show my editing queue <span aria-hidden="true">↗</span></a>';
   q.insertBefore(span,pick);span.querySelector('.change').addEventListener('click',open);wireShow(span.querySelector('.show-queue'),st);
   st.textContent=d.words||'';st.className='qstate';}
  catch(e){st.textContent='Could not add it. Tell Claude instead.';st.className='qstate bad';save.disabled=false;}});
});
})();
</script>"""

MIC = ("<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
       "<rect x='9' y='3' width='6' height='11' rx='3'/><path d='M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8'/></svg>")
ROTS = [-2.5, 2, -1.5]


def day(iso):
    return this_computer.strftime(datetime.fromisoformat(iso), "%A, %B %-d, %Y")



def big_preview(studio, g, p):
    """A sharp copy (2000 px) of a group preview for the report's click-to-enlarge view, made once from
    the photo itself into groups/big/ (the Mac's own sips; on a PC the JPEG the camera stored in the RAW,
    which for a few cameras is smaller than 2000 px). Returns the path to use, or None when the photo is
    not reachable (drive unplugged) or cannot be read here: the page then just shows the small preview bigger."""
    big = studio / "groups" / "big" / p
    if big.exists():
        return f"groups/big/{p}"
    stem = p[:-4].split("_", 1)[-1]  # "g01_062422_2111.jpg" -> "062422_2111", the camera's name kept in the file name
    try:
        from where import locate
        root, _ = locate(studio)
    except Exception:  # noqa: BLE001
        return None
    src = next((root / f for f in g.get("files", []) if Path(f).stem.endswith(stem)), None)
    if not src or not src.is_file():
        return None
    if not pictures.ready()[0]:
        return None
    big.parent.mkdir(parents=True, exist_ok=True)
    return f"groups/big/{p}" if pictures.make_jpeg(src, big, 2000, 82) else None


def clip_stills(studio, g, most=3):
    """For a group of nothing but video clips that has no pictures yet (a backup made before clips got stills, or
    one whose stills could not be made at the time): a still from up to `most` of its clips, made once into
    groups/ and found again by name after that. Fills g["previews"] and g["clip_previews"] for this page only;
    the records are not rewritten. Nothing when the drive is unplugged or on a PC (no stills there yet)."""
    files = g.get("files", [])
    if g.get("previews") or not files or not all(clips.is_clip(f) for f in files):
        return
    try:
        from where import locate
        root, _ = locate(studio)
    except Exception:  # noqa: BLE001
        return
    if len(files) > most:
        step = (len(files) - 1) / (most - 1)
        files = [files[round(i * step)] for i in range(most)]
    made = []
    for f in files:
        stem = Path(f).stem
        m = re.match(r"^.+?_\d{4}_(.+)$", stem)   # the camera's own name, so a rename finds the same still again
        name = f"{g['id']}_{m.group(1) if m else stem}.jpg"
        if (studio / "groups" / name).exists() or ((root / f).is_file() and clips.still(root / f, studio / "groups" / name)):
            made.append(name)
    clips.borrow_turns(studio / "groups", made)   # a still with nobody in it stands the way its neighbour does
    g["previews"], g["clip_previews"] = made, list(made)


def peeks_by_shoot(studio):
    """{shoot id: [preview file names]} of the sneak peeks that have a preview, in the order they were picked."""
    out = {}
    pj = studio / "sneak-peeks.json"
    if not pj.exists() and (studio / "picks.json").exists():
        pj = studio / "picks.json"
    if not pj.exists():
        return out
    try:
        picks = json.loads(pj.read_text(encoding="utf-8")).get("picks", [])
    except ValueError:
        return out
    for pk in picks:
        name = Path(pk["file"]).stem + ".jpg"
        if (studio / "sneak-peeks" / name).exists():
            out.setdefault(pk.get("shoot", ""), []).append(name)
    return out


def note_card(note):
    """The note to the client as a card with Copy buttons; None when there is nothing to show."""
    e = html.escape
    if not note or not (note.get("body") or note.get("to")):
        return None
    # the label sits above the box, in the report's coral, a touch larger than an eyebrow (Dustin, Oct 28)
    out = ["<div class='note-wrap'><span class='eyebrow note-label'>Note to your client</span>", "<article class='note'>"]
    out.append("<div class='to'>" + (f"<span>To {e(note['to'])}</span>" if note.get("to") else "<span>[Name] still to fill in</span>") + "</div>")
    if note.get("body"):
        if note.get("subject"):
            out.append(f"<div class='subj'>{e(note['subject'])}</div>")
        out.append(f"<pre class='body'>{e(note['body'].rstrip())}</pre>")
        out.append("<div class='row'><button class='copy' data-what='body'>Copy the note</button>"
                   + ("<button class='copy sub' data-what='subject'>Copy the subject</button>" if note.get("subject") else "")
                   + "<span class='did'></span></div>")
    else:
        out.append("<p class='empty'>Not written yet. Say “write the note for this one” and it'll be here.</p>")
    out.append("</article></div>")
    return "\n".join(out)


def tally(gs):
    """(photos, clips) in these groups. Older records have no count of clips, so the files are counted."""
    photos = clips_ = 0
    for g in gs:
        if "photos" in g and "clips" in g:
            photos, clips_ = photos + g["photos"], clips_ + g["clips"]
        else:
            a, b = clips.count(g.get("files", []))
            photos, clips_ = photos + a, clips_ + b
    return photos, clips_


# A click on a clip's still plays the clip in the computer's own video player; "See all N video clips" opens their
# folder. Both ask the report's server (a page cannot open a file itself), and what happened is said right under the
# pictures. Opened as a plain file, with no server, the line says how to get there instead.
CLIPS_SCRIPT = """<script>(()=>{
const say=(row,m)=>{const t=row&&row.querySelector('.clips-state');if(t)t.textContent=m||''};
const rowOf=id=>document.querySelector(".clips-row[data-shoot='"+id+"']");
const ask=async(row,url)=>{
 if(!location.protocol.startsWith('http')){say(row,'Ask Claude to show the report, and this will work.');return}
 try{const r=await fetch(url,{cache:'no-store'});const j=await r.json();say(row,j.words||(j.ok?'':'Could not open it.'))}
 catch(e){say(row,'The Assistant is not running right now. Ask Claude to show the report, then try again.')}};
document.querySelectorAll('.ph.clip[data-play]').forEach(p=>{
 const go=()=>{const row=rowOf(p.dataset.shoot);say(row,'Opening it...');ask(row,'/play?file='+encodeURIComponent(p.dataset.play))};
 p.addEventListener('click',go);p.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go()}})});
document.querySelectorAll('.clips-row .all-clips').forEach(b=>b.addEventListener('click',()=>{
 const row=b.closest('.clips-row');say(row,'Opening the folder...');ask(row,'/open-clips?shoot='+encodeURIComponent(row.dataset.shoot))}));
})();</script>"""


def nice_date(iso):
    d = datetime.fromisoformat(iso)
    return d.strftime("%a, %b ") + str(d.day)


def both_folders(s, groups):
    """True when this shoot's photos and clips were filed in Photos and Videos inside its folder."""
    want = {clips.PHOTOS_FOLDER, clips.VIDEOS_FOLDER}
    seen = {Path(f).parts[1] for g in s.get("groups", []) if g in groups for f in groups[g].get("files", []) if len(Path(f).parts) > 2}
    return want <= seen


def today_iso():
    return datetime.now().date().isoformat()


def shoots_section(studio):
    """(html, script) for the shoots, or None when the card has not been grouped and decided yet.
    Each shoot is one block that builds downward: three photos framing the recap and the name box, then the
    rest of its sneak peeks in a row, then the note to the client (Dustin, Oct 28)."""
    if not (studio / "groups.json").exists() or not (studio / "shoots.json").exists():
        return None
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]}
    shoots = json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    names = json.loads((studio / "names.json").read_text(encoding="utf-8")) if (studio / "names.json").exists() else {}
    e = html.escape
    counts = {s["id"]: tally([groups[g] for g in s["groups"] if g in groups]) for s in shoots}
    total = clips.words(sum(a for a, _ in counts.values()), sum(b for _, b in counts.values()))
    days = sorted({groups[g]["start"][:10] for s in shoots for g in s["groups"]})
    named = sum(1 for s in shoots if names.get(s["id"]))
    filed = all(s.get("folder") for s in shoots)
    n = len(shoots)
    peeks = peeks_by_shoot(studio)
    try:
        from client_note import all_notes
        notes = all_notes(studio)
    except ImportError:
        notes = {}
    queued = {}   # shoot id -> due date (ISO), for shoots already in the editing queue
    try:
        import edit_queue
        for x in edit_queue.load()["shoots"]:
            if this_computer.same_place(x.get("studio") or "", studio) and x.get("shoot") and edit_queue.is_waiting(x):
                queued[x["shoot"]] = x.get("due")
    except Exception:  # noqa: BLE001  the queue is a convenience; the report still builds without it
        pass

    out = ["<div class='wrap'><div class='shoots-head'><span class='eyebrow'>What's on the card</span>",
           f"<h2 class='h2'>{n} shoot{'s' if n != 1 else ''}, <span class='swap'>{total}</span>, across {len(days)} day{'s' if len(days) != 1 else ''} of shooting.</h2>",
           f"<p class='lede'>{'Each one is already in its own folder, named by date. Give it a better name and everything is renamed to match.' if filed else 'Give each one a name and it is filed, named and ready for you.'}</p>",
           f"<div class='talk'><span class='mic'>{MIC}</span><div><h3>Just tell me who's who.</h3>"
           "<p>Say it the way you'd say it to a person. I'll sort out which is which and fill the names in.</p>"
           "<p class='eg'>“The big one is the Lani swim shoot, the sunset one is for Kaia, and the yoga day is Marisol's.”</p></div></div>",
           "</div><div class='shoots'>"]
    for i, s in enumerate(shoots, 1):
        gs = [groups[g] for g in s["groups"]]
        start = gs[0]["start"]
        for g in gs:
            clip_stills(studio, g)
        mine = peeks.get(s["id"], [])
        if len(mine) >= 6:   # the six sneak peeks as one mosaic: the hero, two beside it, three under
            pics = [(p, None) for p in mine[:6]]
            rest = []
        elif len(mine) >= 3:   # fewer than six: three frame the card, the rest go in a row under it
            pics = [(p, None) for p in mine[:3]]
            rest = mine[3:6]
        else:                # not picked yet: three previews spread across the shoot
            pics = [(p, g) for g in gs for p in g.get("previews", [])]
            if pics and all(p in g.get("clip_previews", []) for p, g in pics):
                # stills from clips: the three where the face makes the best picture, the best one biggest
                # (Dustin, Nov 11: the preview "should at least look semi-decent")
                score = clips.turns(studio / "groups")
                pics = sorted(pics, key=lambda pg: -(score.get(pg[0], {}).get("face") or 0))[:3]
            elif len(pics) > 3:  # the hero from the middle of the shoot, two more spread out
                pics = [pics[len(pics) // 2], pics[0], pics[-1]]
            rest = []
        lenses = sorted({l for g in gs for l in g.get("lenses", [])})
        bodies = max(g["bodies"] for g in gs)
        # the box always shows the shoot's current name (locked in, or the suggested one it was filed under), so
        # clicking clears it and shows that name underneath in grey (Dustin, Oct 28: a fresh backup showed an empty box)
        val = names.get(s["id"]) or s.get("name") or s.get("suggested", "")
        n_photos, n_clips = counts[s["id"]]
        how_many = clips.words(n_photos, n_clips)

        def img(p, g):
            if g is None:
                return f"<img src='sneak-peeks/{e(p)}' alt=''>"
            if is_still(p, g):   # a still from a video clip: shown as it is (there is no bigger photo behind it)
                return f"<img src='groups/{e(p)}' alt='A still from a video clip. Click to play the clip.'>"
            big = big_preview(studio, g, p)
            return f"<img src='groups/{e(p)}' alt=''" + (f" data-big='{e(big)}'" if big else "") + ">"

        def is_still(p, g):
            return g is not None and p in g.get("clip_previews", [])

        def clip_of(p, g):
            """The clip a still came from, as the records spell it (the still's name ends with the camera's name)."""
            cam = p[:-4].split("_", 1)[-1]
            return next((f for f in g.get("files", []) if clips.is_clip(f) and Path(f).stem.endswith(cam)), "")

        def tile(j, p, g):
            rot = f"style='--rot:{ROTS[j % len(ROTS)]}deg'"
            if is_still(p, g):   # a still from a clip: a click plays the clip (it has a play mark on it, so it must)
                return (f"<div class='ph clip' data-play='{e(clip_of(p, g))}' data-shoot='{e(s['id'])}' {rot} role='button' tabindex='0' "
                        f"title='Play this video clip'>{img(p, g)}</div>")
            return f"<div class='ph' data-g='{e(s['id'])}' {rot} title='Click to see it bigger'>{img(p, g)}</div>"
        out.append("<article class='shoot'><div class='top'>")
        out.append("<div class='gal'>")   # the gallery, with the sneak-peeks line under it (Dustin, Oct 28)
        out.append(f"<div class='pics{' six' if len(pics) == 6 else ''}'>" + "".join(
            tile(j, p, g) for j, (p, g) in enumerate(pics))
            + ("" if pics else f"<div class='novid'>Video clips don't show a picture here yet.<br>{'All ' + format(n_clips, ',') + ' are' if n_clips > 1 else 'It is'} in the folder, copied and checked.</div>"
               if n_clips and not n_photos else "")
            + f"<span class='chip f-sun' style='--rot:-5deg;top:-1.55rem;left:-.7rem'>{how_many}</span>"
            + "</div>")   # no "outfits or breaks" chip: a nice touch, not needed (Dustin, Oct 28)
        if len(pics) == 6:
            out.append(f"<div class='peeks-wrap' data-shoot='{e(s['id'])}'>"
                       "<p class='peeks-line'><b>I pulled six to get things rolling.</b> Not feeling them? Just say what you'd rather see. They're marked “sneak peek” in Lightroom.</p>"
                       "<div class='peeks-act'><button class='pk again' type='button'>Pick again</button><button class='pk more' type='button'>Show me more</button></div>"
                       "<div class='peeks-ask' hidden><input type='text' maxlength='300' placeholder='What would you rather see? (more wide shots, more of the kids, nothing backlit...)'>"
                       "<button class='pk send' type='button'>Pick again</button><button class='pk cancel' type='button'>Never mind</button></div>"
                       "<div class='peeks-more' hidden></div>"
                       "<p class='peeks-state'></p></div>")
        if n_clips:
            # a way to reach every clip, and the line that says what a click did, right under the pictures
            shown = sum(1 for p, g in pics if is_still(p, g))
            link = (f"See all {n_clips:,} video clips" if n_clips > 1 else "Open the folder this video clip is in")
            hint = "Click a picture to play that clip." if shown else ""
            out.append(f"<div class='clips-row' data-shoot='{e(s['id'])}'><button class='all-clips' type='button'>{link} <span aria-hidden='true'>↗</span></button>"
                       + (f"<span class='clips-hint'>{hint}</span>" if hint else "") + "<span class='clips-state' aria-live='polite'></span></div>")
        out.append("</div>")   # gal
        out.append("<div class='copy'>")
        out.append(f"<span class='n'>{i:02d}</span>")
        out.append("<div class='meta'>"
                   f"<span class='tag sun'>{e(day(start))}</span>"
                   + (f"<span class='tag ocean'>{bodies} cameras</span>" if bodies > 1 else "")
                   + "".join(f"<span class='tag'>{e(l)}</span>" for l in lenses[:2]) + "</div>")
        out.append(f"<p class='recap'>{e(s.get('recap', ''))}</p>")
        out.append(f"<div class='name'><label for='{s['id']}'>What should I call this one?</label>"
                   f"<div class='field'><span class='pen'>&#9998;</span>"
                   f"<input id='{s['id']}' name='{s['id']}' value='{e(val)}' title='{e(val)}' placeholder='Type a name here, or just tell Claude' autocomplete='off'>"
                   f"<button class='go' type='button' data-shoot='{e(s['id'])}'>Rename</button></div>"
                   f"<span class='state' data-for='{e(s['id'])}'></span>"
                   + (f"<small>Filed as <b>{e(s.get('name') or s.get('suggested', ''))}</b>. Give it a better name and everything gets renamed to match."
                      + (f" Inside its folder, your photos are in <b>{clips.PHOTOS_FOLDER}</b> and your video clips in <b>{clips.VIDEOS_FOLDER}</b>." if both_folders(s, groups) else "")
                      + "</small></div>"
                      if s.get("folder") else
                      f"<small>Blank means it's filed as <b>{e(s.get('suggested', ''))}</b> until you say otherwise.</small></div>"))
        # the editing queue, one button: click, pick a date on the calendar, done (Dustin, Oct 28)
        due = queued.get(s["id"])
        out.append(f"<div class='queue' data-shoot='{e(s['id'])}'>"
                   + (f"<span class='queued'>In your editing queue, due <b>{e(nice_date(due))}</b>. <button class='change' type='button'>Change the date</button> <a class='show-queue' href='#'>Show my editing queue <span aria-hidden='true'>↗</span></a></span>" if due
                      else "<button class='add' type='button'>Add to my editing queue</button>")
                   + f"<span class='pick' hidden><label>Due <input type='date' min='{e(today_iso())}'></label><button class='save' type='button' disabled>Save</button><button class='never' type='button'>Never mind</button></span>"
                   "<span class='qstate'></span></div>")
        out.append("</div></div>")   # copy, top
        if mine:
            out.append("<div class='more'>")
            if rest:
                out.append("<span class='eyebrow'>Sneak peeks</span>"
                           f"<p class='line'><b>These {len(mine[:6])}, to edit first.</b> Picked for variety and flow, so they look good together. "
                           "In Lightroom, filter by the keyword “sneak peek” to find them.</p>")
            if rest:
                out.append("<div class='row'>" + "".join(
                    f"<div class='ph' data-g='{e(s['id'])}' style='--rot:{ROTS[(j + 3) % len(ROTS)]}deg' title='Click to see it bigger'><img src='sneak-peeks/{e(p)}' alt=''></div>"
                    for j, p in enumerate(rest)) + "</div>")
            out.append("</div>")
        card = note_card(notes.get(s["id"]))
        if card:
            out.append(card)
        out.append("</article>")
    out.append("</div>")   # no how-to paragraph under the shoots: not needed (Dustin, Oct 28)
    return "\n".join(out), PICKER + SCRIPT + CLIPS_SCRIPT


def write_page(session_dir):
    """Kept so older links still work: first-look.html now just opens the report."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from where import locate
    _, studio = locate(session_dir)
    page = studio / "first-look.html"
    page.write_text("<!doctype html><meta http-equiv='refresh' content='0; url=report.html'><a href='report.html'>The report</a>", encoding="utf-8")
    return page


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: first_look.py <session folder>")
    print(write_page(sys.argv[1]))
