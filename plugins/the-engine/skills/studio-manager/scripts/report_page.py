#!/usr/bin/env python3
"""Turn a session's _studio/manifest.json into a page the photographer can look at:
_studio/report.html. One file, no account; opens in the Claude desktop app or
any browser. Problems first, then the good news, then a few teasers from the
shoot itself (from _studio/previews/, picked in _studio/teasers.json).

The look follows the reel page (Dustin, Nov 7): cream desk, coral accent, rounded
cards, a few things tilted, and DM Sans for every word, no serif. The colours, the
font and the shared rules come from look.py; the font is the plugin's own, served by
the report's server (/look-font), so nothing loads from the internet. Opened as a
plain file with no server, the page falls back to the system's sans font.

Run on its own:  python3 report_page.py "<session folder>"
backup.py calls write_page() at the end of every run.
"""
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MEDIA = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff",
         ".mov", ".mp4", ".mxf", ".avi"}

CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
img{max-width:100%;display:block}h1,h2,h3,p{margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:0 clamp(16px,3vw,32px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:baseline;gap:.6rem;white-space:nowrap}
.brand b{font:600 16px/1 var(--sans);letter-spacing:-.01em}
.brand small{font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2);white-space:nowrap}
.bar .homelink{display:inline-flex;align-items:center;gap:.45em;margin-right:.25rem;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px;white-space:nowrap;transition:background .2s}.bar .homelink:hover{background:var(--coral-2)}.bar .homelink .short{display:none}@media(max-width:560px){.bar .homelink .long{display:none}.bar .homelink .short{display:inline}}
.bar .nav{display:inline-flex;align-items:center;gap:.8rem;font:600 16px/1 var(--sans);color:#fff;text-decoration:none;padding:.5rem .5rem .5rem 1.3rem;border-radius:999px;background:var(--coral);border:1.5px solid var(--coral);white-space:nowrap;box-shadow:0 14px 28px -18px rgba(240,127,90,.9);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.bar .nav .arr{width:34px;height:34px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:15px;transition:transform .35s var(--ease)}
.bar .nav:hover{transform:translateY(-2px);box-shadow:var(--shadow)}.bar .nav:hover .arr{transform:translate(2px,-2px)}
@media(max-width:600px){.bar .nav{font-size:14px;padding-left:1rem}}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.h1{font:600 clamp(36px,5.4vw,64px)/1.02 var(--sans);letter-spacing:-.035em;text-wrap:balance;max-width:14em}
.h1.bad{max-width:16em}
.lede{font-size:clamp(16px,1.4vw,19px);color:var(--ink-2);max-width:36em;text-wrap:pretty}
.hero{display:grid;gap:1.2rem;padding:clamp(2.2rem,5vw,4rem) 0 clamp(1.6rem,3vw,2.4rem)}
.pill{display:inline-flex;align-items:center;gap:.7rem;padding:.4rem 1.2rem .4rem .45rem;border-radius:999px;font:500 14px/1 var(--sans);background:var(--paper);border:1.5px solid var(--ink);white-space:nowrap;width:max-content}
@media(max-width:420px){.pill{white-space:normal;width:auto;max-width:100%;line-height:1.3;justify-self:start}.pill .dot{flex:none}}
.pill .dot{width:30px;height:30px;border-radius:50%;background:var(--lime);display:grid;place-items:center;flex:none;color:var(--ink)}
.pill.bad{background:var(--coral);border-color:var(--coral);color:#fff}.pill.bad .dot{background:var(--paper);color:var(--coral)}
.pill.wait{background:var(--sun-l);border-color:var(--sun)}.pill.wait .dot{background:var(--sun)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.stat{padding:1.5rem 1.2rem;border-left:1px solid var(--line)}.stat:first-child{border-left:0}
.stat b{display:block;font:600 clamp(34px,4.2vw,54px)/1 var(--sans);letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.stat span{display:block;margin-top:.6rem}
.problems{background:var(--coral);color:#fff;border-radius:var(--r);padding:clamp(1.4rem,3vw,2.2rem);display:grid;gap:.8rem;margin-top:1.4rem}
.problems .eyebrow{color:#fff;opacity:.85}.problems h2{font:600 clamp(22px,2.4vw,30px)/1.15 var(--sans);letter-spacing:-.02em}
.problems ul{margin:0;padding-left:1.2rem;display:grid;gap:.4rem;font-size:16px}.problems p{opacity:.92}
.teasers{position:relative;display:grid;grid-template-columns:repeat(6,1fr);gap:clamp(.6rem,1.6vw,1.2rem);padding:clamp(2.4rem,5vw,3.6rem) 0 clamp(1.8rem,3vw,2.6rem);align-items:end}
.teasers .ph{border-radius:22px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.teasers .ph:hover{transform:rotate(0) translateY(-8px);box-shadow:var(--shadow)}
.teasers .ph img{width:100%;height:100%;object-fit:cover}
.teasers .ph:nth-child(2n){margin-bottom:1.6rem}
.chip{position:absolute;padding:.55rem 1rem;border-radius:999px;font:500 13px/1 var(--sans);color:var(--ink);border:3px solid var(--paper);box-shadow:0 12px 26px -12px rgba(31,36,48,.4);transform:rotate(var(--rot,0deg));z-index:2}
.f-sun{background:var(--sun-l)}.f-ocean{background:var(--ocean-l)}.f-lime{background:var(--lime)}.f-sand{background:var(--sand-l)}.f-paper{background:var(--paper)}
.teaser-note{font-size:13px;color:var(--ink-2);margin-top:-.6rem}
.peeks{padding:clamp(1.6rem,3vw,2.4rem) 0 .4rem}
.peeks .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:clamp(.6rem,1.6vw,1.1rem);margin-top:1rem;align-items:end}
.peeks .ph{border-radius:18px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease);position:relative}
.peeks .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow)}
.peeks .ph img{width:100%;height:100%;object-fit:cover;display:block}
.peeks .ph small{position:absolute;left:.6rem;bottom:.5rem;font-size:11px;color:#fff;background:rgba(0,0,0,.42);padding:.15rem .5rem;border-radius:999px;backdrop-filter:blur(4px)}
.peeks .lede{margin-top:.4rem}
.ph[data-g]{cursor:zoom-in}
.big{position:fixed;inset:0;z-index:50;background:transparent;display:none;align-items:center;justify-content:center;cursor:zoom-out;padding:4vh 4vw}
.big.on{display:flex}.big .card{position:relative;background:var(--paper);border-radius:22px;padding:14px;box-shadow:0 40px 100px -24px rgba(31,36,48,.45),0 0 0 1px var(--line);cursor:default}
.big img{max-width:86vw;max-height:84vh;object-fit:contain;border-radius:12px;display:block}
.big .x{position:absolute;top:-14px;right:-14px;width:36px;height:36px;font:600 16px/1 var(--sans);color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:50%;box-shadow:var(--shadow);cursor:pointer}
.big .nav{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;font:400 26px/1 var(--sans);color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:50%;box-shadow:var(--shadow);cursor:pointer;opacity:.9}.big .nav:hover{opacity:1}.big .prev{left:-22px}.big .next{right:-22px}
.big small{position:absolute;bottom:-26px;left:50%;transform:translateX(-50%);color:var(--ink-2);font:500 12px var(--sans)}
.notes{padding:clamp(1.2rem,2.6vw,2rem) 0 .6rem}
.notes .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:1rem;margin-top:1rem}
.note{background:#fff;border:1px solid var(--line,#e6e0d6);border-radius:22px;padding:1.4rem 1.5rem 1.2rem;display:flex;flex-direction:column;gap:.7rem}
.open-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#fff;padding:.7rem 1.2rem;border-radius:999px;font:500 14px var(--sans);opacity:0;transition:opacity .3s,transform .3s;pointer-events:none;z-index:60;max-width:90vw;text-align:center}.open-toast.on{opacity:1;transform:translateX(-50%) translateY(0)}.note-wrap{display:flex;flex-direction:column;gap:.55rem}.note-label{font-size:13px;letter-spacing:.12em}.note .to{font-size:13px;color:var(--ink-2);display:flex;justify-content:flex-end;gap:1rem;align-items:baseline}
.note .subj{font-weight:600;font-size:15px}
.note .body{white-space:pre-wrap;font-size:15px;line-height:1.55;margin:0;font-family:inherit}
.note .row{display:flex;gap:.6rem;align-items:center;margin-top:.3rem;flex-wrap:wrap}
.note .copy{border:0;border-radius:999px;padding:.6rem 1.1rem;background:var(--ink,#1e1e22);color:#fff;font:inherit;font-size:14px;cursor:pointer}
.note .copy.sub{background:transparent;color:var(--ink,#1e1e22);border:1px solid var(--line,#d8d1c6)}
.note .did{font-size:13px;color:var(--ink-2);opacity:0;transition:opacity .3s}
.note .did.on{opacity:1}
.note .empty{font-size:14px;color:var(--ink-2)}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;padding:1rem 0 clamp(2.5rem,5vw,4rem)}
.where-card{justify-content:center}
.where-card .path{font:400 14px/1.45 var(--sans);color:var(--ink-2);word-break:break-all;background:var(--paper);border-radius:14px;padding:.75rem .9rem}
a.go{display:inline-flex;align-items:center;gap:.9rem;align-self:flex-start;padding:.5rem .5rem .5rem 1.4rem;border-radius:999px;background:var(--coral);color:#fff;font:500 17px/1 var(--sans);text-decoration:none;border:1.5px solid var(--coral);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
a.go:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
a.go .arr{width:38px;height:38px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:17px;transition:transform .35s var(--ease)}
a.go:hover .arr{transform:translate(2px,-2px)}
.where-card .also{font-size:13px;color:var(--ink-2);word-break:break-all}
.card{border-radius:var(--r);padding:1.6rem;background:var(--paper);display:flex;flex-direction:column;gap:.8rem;min-height:220px}
.card h3{font:600 20px/1.25 var(--sans);letter-spacing:-.015em}
.card p{color:var(--ink-2);font-size:15px}.card p b{color:var(--ink);font-weight:600}
.bar-k{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--sand-l)}.bar-k span{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--ink-2);font-size:13.5px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.row{display:grid;gap:.15rem;padding:.7rem 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0;padding-top:0}
.row b{font-size:13px;font-weight:600}.row span{color:var(--ink-2);font-size:14px;word-break:break-all}
.card.f-lime p,.card.f-sun p{color:var(--ink)}
.big-ok{font:600 clamp(24px,2.4vw,30px)/1.15 var(--sans);letter-spacing:-.02em;text-wrap:balance}
.foot{background:var(--ink);color:var(--cream);overflow:hidden;margin-top:1rem}
.foot .wrap{padding-top:2rem;font-size:14px;text-align:center;opacity:.9}
.wordmark{font:600 clamp(40px,11.2vw,144px)/.78 var(--sans);letter-spacing:-.04em;white-space:nowrap;text-transform:uppercase;text-align:center;margin:1.2rem 0 -.22em;color:var(--coral)}
@media(max-width:900px){.stats{grid-template-columns:1fr 1fr}.stat:nth-child(3){border-left:0}.stat:nth-child(n+3){border-top:1px solid var(--line)}
.teasers{grid-template-columns:repeat(3,1fr)}.cards{grid-template-columns:1fr}}
@media(max-width:600px){.teasers{grid-template-columns:repeat(2,1fr)}.bar .when{display:none}}
"""

sys.path.insert(0, str(Path(__file__).resolve().parent))
from first_look import CSS as SHOOTS_CSS, shoots_section  # noqa: E402
import first_look  # noqa: E402
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import clips  # noqa: E402  (which files are video, and how to say a count)
this_computer.utf8_output()

PALETTE = ["#F07F5A", "#5EB5A9", "#F2CF72", "#9C8BD6", "#2F6F6B", "#CDE9D6"]
ROTS = [-3, 2, -1.5, 2.5, -2, 1.5]



# The backup, played back (Nicole, v28, Nov 17): on a report where everything is safe, photos "falling from the sky",
# twinkling, fly "into where it says 233 files" while the numbers count up from zero. It only replays what already
# happened: the numbers in the page as written are the real ones, a screen reader is given the real ones the whole
# time, and they are put back exactly as written when it ends, is cut short, or cannot run. Nothing here loads
# anything but the report's own small pictures, by the same relative addresses the rest of the page uses.
FALL_WORDS = {"again": "Play it again"}   # hers
FALL_MOST = 40                            # the most pictures handed to the page (hers flies 24 to 40 photos)
FALL_CSS = """
.fallp{position:fixed;left:0;top:0;height:92px;border-radius:6px;overflow:hidden;pointer-events:none;z-index:60;will-change:transform,opacity;box-shadow:0 0 0 2px rgba(255,255,255,.9),0 0 18px rgba(255,236,190,.75),0 10px 22px rgba(31,36,48,.25)}
.fallp img{height:100%;width:auto;max-width:none;display:block}
.twk{position:fixed;left:0;top:0;width:14px;height:14px;pointer-events:none;z-index:61;will-change:transform,opacity}
.twk::before,.twk::after{content:'';position:absolute;left:50%;top:50%;background:#fff;border-radius:2px;box-shadow:0 0 8px 2px rgba(255,214,140,.9)}
.twk::before{width:2px;height:14px;margin:-7px 0 0 -1px}.twk::after{width:14px;height:2px;margin:-1px 0 0 -7px}
.stats.falls{position:relative}.stats.falls .stat{transition:background .4s}
.stats.falls .stat.catch{animation:statpop .32s var(--ease)}@keyframes statpop{50%{transform:scale(1.06)}}
.stats.falls .stat.glow{background:linear-gradient(180deg,rgba(242,207,114,.22),rgba(242,207,114,0))}
.stats.falls .stat b span{display:inline;margin:0}
.stats.falls .stat b .fall-real{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap}
.fall-again{position:absolute;right:0;top:100%;margin-top:4px;font:600 12px/1 var(--sans);color:var(--ink-2);background:none;border:0;cursor:pointer;padding:8px 2px;visibility:hidden;opacity:0;transition:opacity .4s}
.fall-again.on{visibility:visible;opacity:1}.fall-again:hover{color:var(--ink)}
"""
FALL_JS = r"""<script>
(function(){
  var D=__FALL__, box=document.querySelector('.stats');
  if(!box||!D.pics.length||!window.IntersectionObserver||!Element.prototype.animate||!window.matchMedia) return;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;   // the real numbers are already on the page
  const bs=[...box.querySelectorAll('.stat b')], target=box.querySelector('.stat'), finals=bs.map(b=>b.textContent);
  if(!target) return;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  let run=0, playing=false, ticks=null, good=[];
  // the words stay, the numbers count, keeping their decimals ("7.8 GB" passes "2.4 GB", never "2 GB")
  const at=(text,f)=>text.split(/(\d[\d,]*\.?\d*)/).map((x,i)=>{ if(i%2===0) return x;
    const dec=(x.split('.')[1]||'').length, n=parseFloat(x.replace(/,/g,''))*f;
    return dec?n.toFixed(dec):Math.round(n).toLocaleString('en-US'); }).join('');
  // while a number counts, what is drawn is hidden from a screen reader and the real number sits beside it for one
  function zero(){ box.style.minHeight=box.offsetHeight+'px';   // the row keeps its height while the numbers are short
    ticks=bs.map((b,k)=>{ b.textContent='';
    const t=document.createElement('span'); t.setAttribute('aria-hidden','true'); t.textContent=at(finals[k],0);
    const r=document.createElement('span'); r.className='fall-real'; r.textContent=finals[k];
    b.appendChild(t); b.appendChild(r); return t; }); }
  function settle(){ ticks=null; bs.forEach((b,k)=>{ b.textContent=finals[k]; }); box.style.minHeight=''; }   // exactly as the page was written
  function stop(){ run++; playing=false; document.querySelectorAll('.fallp,.twk').forEach(n=>n.remove());
    target.classList.remove('catch','glow'); settle(); btn.classList.add('on'); }
  box.classList.add('falls');
  const btn=document.createElement('button'); btn.className='fall-again'; btn.type='button';
  btn.textContent='↻ '+D.again; box.appendChild(btn);
  function twinkle(x,y){ const s=document.createElement('i'); s.className='twk'; s.setAttribute('aria-hidden','true'); document.body.appendChild(s);
    const a=s.animate([{transform:'translate('+x+'px,'+y+'px) scale(0) rotate(0)',opacity:0},
      {transform:'translate('+x+'px,'+y+'px) scale(1) rotate(45deg)',opacity:1,offset:.4},
      {transform:'translate('+x+'px,'+(y+30)+'px) scale(0) rotate(90deg)',opacity:0}],{duration:900,easing:'ease-out'});
    a.onfinish=a.oncancel=()=>s.remove(); }
  async function fly(i,N,dur,me){
    await sleep(i*(dur*.62/N)+Math.random()*120); if(me!==run) return;
    const W=innerWidth, H=innerHeight, tr=target.getBoundingClientRect(), tx=tr.left+tr.width*.35, ty=tr.top+tr.height*.4;
    const el=document.createElement('div'); el.className='fallp'; el.setAttribute('aria-hidden','true');
    const im=document.createElement('img'); im.alt=''; im.src=good[i%good.length]; el.appendChild(im); document.body.appendChild(el);
    const x0=W*(.06+Math.random()*.88), y0=-120-Math.random()*80, yMid=H*(.18+Math.random()*.22), sw=24+Math.random()*40,
      ph=Math.random()*6.28, spin=(Math.random()-.5)*50, flip=(Math.random()<.5?-1:1)*(18+Math.random()*28), f=[], Q=40;
    for(let q=0;q<=Q;q++){ const t=q/Q; let x,y,rz,ry,sc,op;
      if(t<.62){ const u=t/.62;                        // drifting down from above, with a sway and a gentle turn
        x=x0+Math.sin(ph+u*5)*sw; y=y0+(yMid-y0)*u; rz=spin*Math.sin(ph+u*4); ry=flip*Math.sin(ph+u*3); sc=1; op=Math.min(1,u*3); }
      else{ const u=(t-.62)/.38, g=u*u*(3-2*u), xs=x0+Math.sin(ph+5)*sw;   // then a curve into the files box, shrinking
        x=xs+(tx-xs)*g; y=yMid+(ty-yMid)*g-Math.sin(u*Math.PI)*60; rz=spin*(1-u); ry=flip*Math.sin(ph+3)*(1-u); sc=1-.78*g; op=u>.92?(1-u)/.08:1; }
      f.push({transform:'translate('+x.toFixed(1)+'px,'+y.toFixed(1)+'px) rotate('+rz.toFixed(1)+'deg) rotateY('+ry.toFixed(1)+'deg) scale('+sc.toFixed(3)+')',opacity:op,offset:t}); }
    const d=2600+Math.random()*700, a=el.animate(f,{duration:d,easing:'linear',fill:'forwards'});
    for(let k=1;k<=3;k++) setTimeout(()=>{ if(me!==run||!el.isConnected) return; const r=el.getBoundingClientRect();
      if(r.width) twinkle(r.left+Math.random()*r.width,r.top+Math.random()*r.height); },d*(k*.18));
    try{ await a.finished; }catch(e){}
    el.remove(); if(me!==run) return;
    target.classList.remove('catch'); void target.offsetWidth; target.classList.add('catch','glow');
    clearTimeout(target._g); target._g=setTimeout(()=>target.classList.remove('glow'),500);
    twinkle(tx+(Math.random()-.5)*40,ty-10);
  }
  async function play(){
    if(playing||!good.length) return;
    playing=true; const me=++run; btn.classList.remove('on'); if(!ticks) zero();
    const N=Math.min(40,Math.max(24,good.length*2)), dur=4200, t0=performance.now();
    (function tick(){ if(me!==run||!ticks) return;      // every number climbs from zero together, about 5 seconds
      const f=Math.min(1,(performance.now()-t0)/(dur+900)), e=f<.5?2*f*f:1-Math.pow(-2*f+2,2)/2;
      ticks.forEach((t,k)=>{ t.textContent=at(finals[k],e); });
      if(f<1) requestAnimationFrame(tick); else settle(); })();
    try{ await Promise.all(Array.from({length:N},(_,i)=>fly(i,N,dur,me))); if(me===run) await sleep(900); }catch(e){}
    if(me===run) stop();
  }
  btn.addEventListener('click',play);
  // a page put behind something, or printed, never sits on half-counted numbers
  document.addEventListener('visibilitychange',()=>{ if(document.hidden&&(playing||ticks)) stop(); });
  window.addEventListener('beforeprint',()=>{ if(playing||ticks) stop(); });
  // the report reloads itself when it is rebuilt (a rename, a note written): that is not a fresh look, so it does
  // not play again by itself; the button is there
  let nav='navigate'; try{ nav=(performance.getEntriesByType('navigation')[0]||{}).type||'navigate'; }catch(e){}
  const load=()=>Promise.all(D.pics.map(u=>{ const i=new Image(); i.src=u; return i.decode().then(()=>{ if(i.naturalWidth) good.push(u); },()=>{}); }));
  if(nav!=='navigate'||document.hidden){ load().then(()=>{ if(good.length) btn.classList.add('on'); }); return; }
  zero();
  Promise.race([load(),sleep(4000)]).then(()=>{
    if(!good.length||document.hidden){ if(ticks&&!playing) settle(); if(good.length) btn.classList.add('on'); return; }   // no picture could be read: the numbers simply show
    const io=new IntersectionObserver(es=>{ if(es.some(e=>e.isIntersecting)){ io.disconnect(); setTimeout(()=>{ if(!document.hidden) play(); },350); } },{threshold:.6});
    io.observe(box);
  });
})();
</script>"""


def fall_pictures(studio, most=FALL_MOST):
    """The small pictures the backup animation flies, as addresses beside the report (the same folders the page
    already shows pictures from, so the report's server already serves them and a report opened as a file finds
    them too): each group's previews, then the sneak peeks, and only when neither gave any, the card's own
    previews. No more than `most`, spread evenly. [] when there is no picture: then there is no animation."""
    import urllib.parse as up
    studio = Path(studio)
    out, seen = [], set()

    def take(folder, name):
        name = str(name)
        if "/" in name or "\\" in name or not name.lower().endswith((".jpg", ".jpeg")) or (folder, name) in seen:
            return
        if (studio / folder / name).is_file():
            seen.add((folder, name))
            out.append(folder + "/" + up.quote(name))

    try:
        groups = json.loads((studio / "groups.json").read_text(encoding="utf-8")).get("groups", [])
    except (ValueError, OSError, AttributeError):
        groups = []
    for g in groups if isinstance(groups, list) else []:
        if isinstance(g, dict):
            for name in list(g.get("previews") or []) + list(g.get("clip_previews") or []):
                take("groups", name)
    if not out and (studio / "groups").is_dir():       # an older backup's stills, made but not listed
        for f in sorted((studio / "groups").glob("g*.jpg")):
            take("groups", f.name)
    try:
        for pv, _ in sneak_peeks(studio)[0]:
            take("sneak-peeks", pv.name)
    except (KeyError, TypeError, AttributeError):
        pass
    if not out and (studio / "previews").is_dir():
        for f in sorted((studio / "previews").glob("*.jpg")):
            take("previews", f.name)
    if len(out) > most:
        step = (len(out) - 1) / (most - 1)
        out = [out[round(i * step)] for i in range(most)]
    return out


def fall_script(manifest, studio, all_good, card=None):
    """The animation's script for this report, or "". Only a whole backup where everything is safe, with pictures:
    never a sample, never a backup with a problem or not finished, never one card inside a shoot's page (each
    card's report sits in a frame there; several playing at once inside frames would look broken)."""
    if not all_good or manifest.get("sample") or card or not manifest.get("files"):
        return ""
    pics = fall_pictures(studio)
    if not pics:
        return ""
    data = json.dumps({"pics": pics, "again": FALL_WORDS["again"]}).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return FALL_JS.replace("__FALL__", data)


def human(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


def nice_time(iso):
    try:
        d = datetime.fromisoformat(iso)
        return this_computer.strftime(d, "%A, %B %-d · %-I:%M %p").replace("AM", "am").replace("PM", "pm")
    except (TypeError, ValueError):
        return ""


def seconds_text(s):
    if s < 90:
        return f"{s:.0f} sec"
    if s < 5400:
        return f"{s / 60:.0f} min"
    return f"{s / 3600:.1f} hrs"


def duration(start, end):
    try:
        return seconds_text((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
    except (TypeError, ValueError):
        return ""


def sort_aside(studio):
    """Files the sorter set aside in _studio/from-the-card (camera housekeeping, undated files)."""
    p = studio / "sort-log.json"
    if not p.exists():
        return []
    try:
        return [a["from"] for a in json.loads(p.read_text(encoding="utf-8")).get("set_aside", [])]
    except (ValueError, OSError):
        return []


def index_facts(studio):
    """When it was taken and on what, from index.json, in plain words."""
    p = studio / "index.json"
    if not p.exists():
        return None
    try:
        ix = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not ix.get("first"):
        return None

    def day(iso):
        return this_computer.strftime(datetime.fromisoformat(iso), "%b %-d, %Y")

    def clock(iso):
        return this_computer.strftime(datetime.fromisoformat(iso), "%-I:%M %p").replace("AM", "am").replace("PM", "pm")

    first, last = ix["first"], ix["last"]
    if first[:10] == last[:10]:
        span = f"{day(first)}, {clock(first)} to {clock(last)}"
    else:
        span = f"{day(first)} to {day(last)}"
    ndays = len(ix.get("days", {}))
    days = f" · {ndays} days of shooting" if ndays > 1 else ""
    cams = ix.get("cameras", {})
    bodies = ix.get("bodies", 0)
    cam_text = ", ".join(f"{c} ({n:,})" for c, n in cams.items()) if len(cams) > 1 else next(iter(cams), "")
    if bodies > 1:
        cam_text += f" · {bodies} camera bodies"
    return {"span": span, "days": days, "cameras": cam_text}


def teasers(studio):
    """Up to six previews: the ones picked in teasers.json if it exists, else an even spread."""
    folder = studio / "previews"
    if not folder.is_dir():
        return [], ""
    picks, note = [], ""
    tj = studio / "teasers.json"
    if tj.exists():
        try:
            d = json.loads(tj.read_text(encoding="utf-8"))
            picks = [folder / f for f in d.get("files", []) if (folder / f).exists()]
            note = d.get("picked_by", "")
        except (ValueError, OSError):
            picks = []
    if not picks:
        allp = sorted(p for p in folder.glob("*.jpg"))
        if len(allp) > 6:
            step = (len(allp) - 1) / 5
            allp = [allp[round(i * step)] for i in range(6)]
        picks, note = allp, "evenly across the shoot; the good ones get chosen later"
    return picks[:6], note


def sneak_peeks(studio):
    """The sneak peeks for the top of the report: [(preview path, shoot name or '')], and who picked them."""
    folder = studio / "sneak-peeks"
    pj = studio / "sneak-peeks.json"
    if not pj.exists() and (studio / "picks.json").exists():
        pj = studio / "picks.json"
    if not pj.exists() or not folder.is_dir():
        return [], ""
    try:
        d = json.loads(pj.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return [], ""
    names = {}
    try:
        if (studio / "shoots.json").exists():
            given = json.loads((studio / "names.json").read_text(encoding="utf-8")) if (studio / "names.json").exists() else {}
            for sh in json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]:
                names[sh["id"]] = given.get(sh["id"]) or sh.get("name") or sh.get("suggested", "")
    except (ValueError, OSError, KeyError):
        pass
    out = []
    for pk in d.get("picks", []):
        pv = folder / (Path(pk["file"]).stem + ".jpg")
        if pv.exists():
            out.append((pv, names.get(pk.get("shoot", ""), "")))
    return out, d.get("picked_by", "")


def client_notes(studio):
    """[(shoot name, note)] for every note written for this night, in shoot order."""
    try:
        from client_note import all_notes, shoot_names
    except ImportError:
        return []
    names = shoot_names(studio)
    notes = all_notes(studio)
    order = list(names) + [k for k in notes if k not in names]
    return [(names.get(k, k), notes[k]) for k in order if k in notes]


PEEK_SCRIPT = """<div class='big' id='big'><div class='card'><button class='x' aria-label='Close'>&#215;</button><button class='nav prev' aria-label='Previous'>&#8249;</button><img alt=''><button class='nav next' aria-label='Next'>&#8250;</button><small></small></div></div>
<script>(()=>{const all=[...document.querySelectorAll('.ph[data-g] img')],big=document.getElementById('big'),img=big.querySelector('img'),cap=big.querySelector('small');let pics=[],at=0;
const show=i=>{at=(i+pics.length)%pics.length;img.src=pics[at].dataset.big||pics[at].src;cap.textContent=(at+1)+' of '+pics.length;big.classList.add('on')};
all.forEach(p=>p.parentElement.addEventListener('click',()=>{pics=all.filter(q=>q.parentElement.dataset.g===p.parentElement.dataset.g);show(pics.indexOf(p))}));
big.querySelector('.x').onclick=()=>big.classList.remove('on');
big.querySelector('.prev').onclick=ev=>{ev.stopPropagation();show(at-1)};big.querySelector('.next').onclick=ev=>{ev.stopPropagation();show(at+1)};
big.addEventListener('click',ev=>{if(ev.target===big)big.classList.remove('on')});
document.addEventListener('keydown',ev=>{if(!big.classList.contains('on'))return;if(ev.key==='Escape')big.classList.remove('on');if(ev.key==='ArrowLeft')show(at-1);if(ev.key==='ArrowRight')show(at+1)});
// for the setup guide's screenshots only: ?show=big opens the first sneak peek big, ?show=calendar opens the queue calendar on the first shoot
const q=new URLSearchParams(location.search).get('show');
if(q==='big'&&pics.length){pics=all.filter(x=>x.parentElement.dataset.g===all[0].parentElement.dataset.g);show(0)}
if(q==='calendar'){const a=document.querySelector('.queue .add');if(a){a.click();}}
})();</script>"""

NOTES_SCRIPT = """
<script>
(function(){
  function copyText(t){
    if(navigator.clipboard && navigator.clipboard.writeText){ return navigator.clipboard.writeText(t); }
    return new Promise(function(ok, bad){
      var ta=document.createElement('textarea'); ta.value=t; ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.focus(); ta.select();
      try{ document.execCommand('copy') ? ok() : bad(); } catch(e){ bad(e); } document.body.removeChild(ta);
    });
  }
  document.querySelectorAll('.note').forEach(function(card){
    var body=card.querySelector('.body'), subj=card.querySelector('.subj'), did=card.querySelector('.did');
    function flash(msg){ did.textContent=msg; did.classList.add('on'); setTimeout(function(){did.classList.remove('on')}, 2200); }
    card.querySelectorAll('.copy').forEach(function(b){
      b.onclick=function(){
        var t = b.dataset.what==='subject' ? subj.textContent : body.textContent;
        copyText(t).then(function(){ flash(b.dataset.what==='subject' ? 'Subject copied.' : 'Copied. Paste it into your email.'); },
                         function(){ flash('Select the text and copy it.'); });
      };
    });
  });
})();
</script>
"""


# When the page is served by serve_report.py, it notices the report being rebuilt (a name locked in, a note
# written) and reloads itself, so what Claude just did shows up without anyone pressing refresh.
REFRESH_SCRIPT = """
<script>
(function(){
  if(location.protocol!=='http:' && location.protocol!=='https:') return;
  var seen=null;
  function check(){
    fetch(location.href,{method:'HEAD',cache:'no-store'}).then(function(r){
      var m=r.headers.get('Last-Modified'); if(!m) return;
      if(seen===null){ seen=m; return; }
      if(m!==seen && !document.activeElement.matches('input,textarea')){ location.reload(); }
    }).catch(function(){});
  }
  setInterval(check, 4000);
})();
</script>
"""


def home_link():
    """A Home link to the Studio's home page, when its server has run (home.py keeps the address in posting-url.txt)."""
    try:
        f = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio")) / "posting-url.txt"
        if f.exists():
            return f"<a class='homelink' href='{f.read_text(encoding='utf-8').strip().rsplit('/', 1)[0]}/home'><span aria-hidden='true'>&larr;</span><span class='long'>Back to home</span><span class='short'>Home</span></a>"
    except OSError:
        pass
    return ""


# One card of a shoot, shown inside the shoot's page (shoot_report.py): the card page sits in a frame sized to its
# content, so anything it pins to its own window (the enlarged photo, the Show me more grid, the folder button's
# line) would sit in the middle of the whole card, often off screen. This puts those on the part of the frame that is
# in view, and keeps them there as the page scrolls. Same page, same address family, so same origin.
CARD_SCRIPT = """
<script>
(function(){
  if(window===window.parent||!window.frameElement) return;
  var sel='.big,.pkbig,.open-toast';
  function place(){
    var r=window.frameElement.getBoundingClientRect(), top=Math.max(0,-r.top), h=parent.innerHeight;
    document.querySelectorAll(sel).forEach(function(el){
      var on=el.classList.contains('open-toast')?el.classList.contains('on'):getComputedStyle(el).display!=='none';
      if(!on){ el.style.top=''; el.style.height=''; el.style.bottom=''; return; }
      if(el.classList.contains('open-toast')){ el.style.top=(top+h-70)+'px'; el.style.bottom='auto'; }
      else { el.style.top=top+'px'; el.style.height=h+'px'; el.style.bottom='auto'; }
    });
  }
  new MutationObserver(place).observe(document.documentElement,{attributes:true,subtree:true,attributeFilter:['style','class']});
  parent.addEventListener('scroll',place,{passive:true}); parent.addEventListener('resize',place);
})();
</script>
"""

CARD_CSS = ".card-hero{padding-top:1.2rem;padding-bottom:1rem}.card-hero .h1{font-size:clamp(26px,3.6vw,40px)}"


def build(manifest, studio, card=None):
    """The report of one backup. card={"n": 2, "of": 3, "shoot": "Smith wedding"}: the same report as one card of a
    shoot, for the shoot's page (no top bar, no footer, "Card 2 of 3" on the hero, the fixes a frame needs)."""
    files = manifest.get("files", {})
    total = len(files)
    total_bytes = sum(e.get("size", 0) for e in files.values() if e.get("size", 0) > 0)
    ok_dest = sum(1 for e in files.values() if e.get("dest", {}).get("ok"))
    second = manifest.get("second")
    ok_second = sum(1 for e in files.values() if e.get("second", {}).get("ok")) if second else None
    problems = manifest.get("problems") or []
    kinds = Counter(Path(k).suffix.lower().lstrip(".") or "other" for k in files)
    media = sum(n for k, n in kinds.items() if f".{k}" in MEDIA)
    n_clips = sum(n for k, n in kinds.items() if f".{k}" in clips.VIDEO)
    media_words = clips.words(media - n_clips, n_clips)   # "212 photos and 6 clips": a clip is never called a photo
    skipped = manifest.get("skipped_system_files", 0)
    session = manifest.get("session", "Session")
    name = session.split(" ", 1)[1] if session[:10].count("-") == 2 and " " in session else session
    finished = manifest.get("finished")
    work = manifest.get("work_seconds")
    took = seconds_text(work) if work else duration(manifest.get("started"), finished)
    all_good = not problems and ok_dest == total and (ok_second == total if second else True)
    pics, pick_note = teasers(studio)
    peeks, _ = sneak_peeks(studio)
    notes = client_notes(studio)
    e = html.escape

    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>{e(brand.title(name))}</title><style>{look.head_css()}{CSS}{SHOOTS_CSS}{CARD_CSS if card else FALL_CSS}</style></head><body>"]
    if not card:
        out.append(f"<div class='wrap'><div class='bar'>{home_link()}{brand.bar()}"
                   f"<span class='when'>{e(nice_time(finished)) if finished else 'Still running'}</span>"
                   + "</div></div>")

    # hero: the one line they need
    out.append("<section class='wrap hero card-hero'>" if card else "<section class='wrap hero'>")
    if card:
        out.append(f"<span class='eyebrow'>Card {int(card['n'])} of {int(card['of'])} · {e(name)}"
                   + (f" · {e(nice_time(finished))}" if finished else "") + "</span>")
    else:
        out.append(f"<span class='eyebrow'>Backup report · {e(name)}</span>")
    if problems:
        out.append(f"<h1 class='h1 bad'>Something needs you before this is <span class='swap'>safe.</span></h1>")
        out.append(f"<p class='lede'>{ok_dest:,} of {total:,} files are copied and checked. Nothing on the memory card has been changed; "
                   "fix what's below, run it again, and it picks up where it left off.</p>")
        out.append("<span class='pill bad'><span class='dot'>!</span>Not finished</span>")
        out.append("<div class='problems'><span class='eyebrow'>Needs you first</span><h2>What stopped it</h2><ul>"
                   + "".join(f"<li>{e(p)}</li>" for p in problems) + "</ul></div>")
    elif all_good and manifest.get("sample"):
        # a sample for a test (Dustin, Nov 11): never a word that could be read as "the card is safe"
        smp = manifest["sample"]
        out.append(f"<h1 class='h1'>A sample: {total:,} of the {smp.get('of', 0):,} files on the card, copied and <span class='swap'>verified.</span></h1>")
        out.append(f"<p class='lede'>This was a test run on part of the card. The other {max(0, smp.get('of', 0) - total):,} files were not copied, "
                   "so the card is not backed up and is not safe to format. Nothing on the memory card has been changed.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the card: this was a sample</span>")
    elif all_good:
        where = "your drive and your second copy" if second else "your drive"
        out.append(f"<h1 class='h1'>All {total:,} files, safely backed up and <span class='swap'>verified.</span></h1>")
        out.append(f"<p class='lede'>Every {'video clip' if n_clips and media == n_clips else 'photo and video clip' if n_clips else 'photo'} was copied to {where} and checked against the card, byte for byte. "
                   "Your memory card is exactly as it was: nothing on it was changed, renamed or deleted.</p>")
        out.append("<span class='pill'><span class='dot'>&#10003;</span>The card is safe to format when you're ready</span>")
    else:
        out.append(f"<h1 class='h1'>Not finished <span class='swap'>yet.</span></h1>")
        out.append(f"<p class='lede'>{ok_dest:,} of {total:,} files are copied and checked so far. Run it again to continue.</p>")
        out.append("<span class='pill wait'><span class='dot'>…</span>Keep the card for now</span>")
    out.append("</section>")

    # the numbers
    out.append("<div class='wrap'><div class='stats'>"
               f"<div class='stat'><b>{total:,}</b><span class='eyebrow'>files</span></div>"
               f"<div class='stat'><b>{e(human(total_bytes))}</b><span class='eyebrow'>copied</span></div>"
               f"<div class='stat'><b>{ok_dest:,}</b><span class='eyebrow'>checked byte for byte</span></div>"
               f"<div class='stat'><b>{e(took) or '—'}</b><span class='eyebrow'>to finish</span></div>"
               "</div></div>")
    # the backup played back (Nicole, v28): only when everything is safe and there are pictures; the numbers above
    # are the real ones whether or not it plays
    fall = fall_script(manifest, studio, all_good, card)
    if fall:
        out.append(fall)

    # the shoots, with their previews, recaps and name boxes (one page, not two)
    # (one card of a shoot leaves the next-step line to the shoot's page, which says it once for every card)
    shoots_html, shoots_script = (shoots_section(studio, closing=not card) or (None, ""))
    if shoots_html:
        out.append(shoots_html)
    # with no shoots decided yet (and no sneak peeks), a few teasers from the card instead
    elif pics and not peeks:
        out.append("<div class='wrap'><div class='teasers'>")
        for i, p in enumerate(pics):
            out.append(f"<div class='ph' style='--rot:{ROTS[i % len(ROTS)]}deg'><img src='previews/{e(p.name)}' alt=''></div>")
        chips = [("f-sun", "-6deg", "top:1.2rem;left:-.4rem", media_words),
                 ("f-ocean", "5deg", "top:.6rem;right:-.2rem", "a few from the shoot"),
                 ("f-lime", "-4deg", "bottom:.8rem;right:12%", "safe to format" if all_good and not manifest.get("sample") else "keep the card")]
        for cls, rot, pos, text in chips:
            out.append(f"<span class='chip {cls}' style='--rot:{rot};{pos}'>{e(text)}</span>")
        out.append("</div>")
        if pick_note:
            out.append(f"<p class='teaser-note'>Teasers picked {e(pick_note)}.</p>")
        out.append("</div>")

    # the sneak peeks and the note live inside each shoot's block now (Dustin, Oct 28)

    # the details
    out.append("<div class='wrap'><div class='cards'>")
    out.append("<div class='card'><span class='eyebrow'>What's on it</span>"
               f"<h3>{media_words}</h3>")
    if total:
        parts = kinds.most_common()
        out.append("<div class='bar-k'>" + "".join(
            f"<span style='width:{100 * n / total:.2f}%;background:{PALETTE[i % len(PALETTE)]}' title='{e(k)}: {n:,}'></span>"
            for i, (k, n) in enumerate(parts)) + "</div>")
        out.append("<div class='legend'>" + "".join(
            f"<span><i style='background:{PALETTE[i % len(PALETTE)]}'></i>{n:,} .{e(k)}</span>" for i, (k, n) in enumerate(parts)) + "</div>")
    ix = index_facts(studio)
    if ix:
        out.append(f"<p>Taken: <b>{e(ix['span'])}</b>{e(ix['days'])}</p>")
        out.append(f"<p>{e(ix['cameras'])}</p>")
    else:
        out.append("<p>Taken: dates will show here once the index is built.</p>")
    if skipped:
        mac = "Mac " if this_computer.MAC else ""   # "hidden Mac system files" on a Mac, as always; on a PC just "hidden system files"
        out.append(f"<p>{skipped} hidden {mac}system file{'s' if skipped != 1 else ''} left behind, as they should be.</p>")
    aside = sort_aside(studio)
    if aside:
        out.append(f"<p>{len(aside)} file{'s that are' if len(aside) != 1 else ' that is'} not a photo or a video clip "
                   f"({', '.join(sorted({Path(a).suffix.lower().lstrip('.') for a in aside}))}) set aside, not deleted.</p>")
    turned = clips.turned_words(studio)   # sideways clips turned upright in the backup copy (Dustin, Nov 11)
    if turned:
        out.append(f"<p>{e(turned)}</p>")
    out.append("</div>")

    def photos_folder(root):
        """The folder the photos actually sit in (e.g. .../DCIM/100EOSR5), not the top of the drive."""
        if not root:
            return root
        # after the sorter has run, index.json carries the new paths; before it, the manifest's card layout
        paths = list(files)
        ixp = studio / "index.json"
        if ixp.exists():
            try:
                paths = [p["file"] for p in json.loads(ixp.read_text(encoding="utf-8")).get("photos", [])] or paths
            except (ValueError, OSError):
                pass
        parents = {Path(k).parent for k in paths if Path(k).suffix.lower() in MEDIA}
        if not parents:
            return root
        common = Path(*os.path.commonprefix([list(p.parts) for p in parents])) if len(parents) > 1 else parents.pop()
        return str(Path(root) / common) if str(common) not in (".", "") else root

    # one card, one button: where the photos ended up, and a way to go there.
    # Opens the folder in Finder (File Explorer on a PC): from Safari on its own, or via serve_report.py inside the app.
    where = photos_folder(manifest.get("dest", ""))
    url = Path(where).as_uri() + "/" if where else ""
    only_clips = bool(n_clips) and media == n_clips
    both = bool(n_clips) and media > n_clips
    where_title = "Where your video clips are" if only_clips else "Where your photos and video clips are" if both else "Where your photos are"
    where_button = "Open video folder" if only_clips else "Open photo folder"
    out.append(f"<div class='card f-sand where-card'><span class='eyebrow'>{where_title}</span>")
    out.append(f"<p class='path'>{e(where)}</p>")
    if url:
        # On a PC the folder also rides along as it is written there (E:\...), because the file:// address of a
        # drive letter does not turn back into a folder by itself (unproven on a real PC). A Mac's page is as before.
        plain = f" data-path='{e(str(where))}'" if this_computer.WINDOWS else ""
        out.append(f"<a class='go where' href='{e(url)}'{plain} title='Open this folder in {this_computer.FILES_APP}'>{where_button}"
                   "<span class='arr'>&#8599;</span></a>")
    if second:
        tail = "" if ok_second == total else f" ({ok_second:,} of {total:,} checked)"
        out.append(f"<p class='also'>Second copy{e(tail)}: {e(photos_folder(second))}</p>")
    if not all_good:
        out.append("<p class='also'>Nothing on the memory card was changed. Keep it until this report says every file is checked.</p>")
    out.append("</div>")
    out.append("</div></div>")

    if not card:
        out.append("<footer class='foot'><div class='wrap'>Your memory card is exactly as it was.</div>"
                   f"<div class='wordmark'>{e(brand.name())}</div></footer>")
    # Served from localhost (inside the Claude app), a page may not open file:// links itself,
    # so ask serve_report.py to open the folder in Finder. Opened as a file in Safari, the links work as they are.
    # The button says what happened, every time: opened, or why not (the drive unplugged, the Studio not running).
    out.append("<div class='open-toast' id='open-toast'></div>"
               "<script>if(location.protocol.startsWith('http')){let last=0;const t=document.getElementById('open-toast');"
               "const tell=m=>{t.textContent=m;t.classList.add('on');clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('on'),3200)};"
               "for(const a of document.querySelectorAll('a.where')){"
               "a.addEventListener('click',async ev=>{ev.preventDefault();ev.stopPropagation();const now=Date.now();if(now-last<800)return;last=now;"
               "const p=" + ("a.dataset.path||" if this_computer.WINDOWS else "") + "decodeURIComponent(a.getAttribute('href').replace(/^file:\\/\\//,'').replace(/\\/$/,''));"
               "try{const r=await fetch('open?path='+encodeURIComponent(p),{cache:'no-store'});const j=await r.json();tell(j.words||(j.ok?'Opened in " + this_computer.FILES_APP + ".':'Could not open it.'));}"
               "catch(e){tell('" + e(brand.name()).replace("'", "\\\\'") + " isn\\'t running right now, so this button can\\'t open " + this_computer.FILES_APP + ". Ask your assistant to show the report, or open the folder yourself: '+p);}});}}</script>")
    out.append(shoots_script + (NOTES_SCRIPT if notes else "") + (PEEK_SCRIPT if (peeks or shoots_html) else "") + REFRESH_SCRIPT
               + (CARD_SCRIPT if card else "") + "</body></html>")
    return "\n".join(out)


def write_page(session_dir):
    """The report, report.html in the records. A backup that is one card of a shoot (shoot_report.py: shoot.json in
    the records) also gets report-card.html, the same report as a card, and the shoot's own page is rebuilt for
    every card of the shoot, so a rename or a new pick on one card shows on the shoot's page at once."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from where import locate
    _, studio = locate(session_dir)
    manifest = json.loads((studio / "manifest.json").read_text(encoding="utf-8"))
    page = studio / "report.html"
    page.write_text(build(manifest, studio), encoding="utf-8")
    import shoot_report
    card = shoot_report.card_of(studio)
    if card:
        (studio / "report-card.html").write_text(build(manifest, studio, card=card), encoding="utf-8")
        shoot_report.write_pages(studio)
    return page


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: report_page.py <session folder>")
    print(write_page(sys.argv[1]))
