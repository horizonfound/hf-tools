#!/usr/bin/env python3
"""The talking reel page's styles (Nicole's handoff v24, pages/talking-reel.html), on top of look.py.

One string of CSS and nothing else (the design_js_*.py pattern); talking_page.page_html() puts it after
look.head_css().

STYLE is her stylesheet as she wrote it, with these changes:
  - the Google Fonts link, her colour names and the rules every page shares are gone: look.py has them
    (Dustin, Nov 7: no serif; the lines to copy and the quoted words in the photo menu are DM Sans, still slanted);
  - the styles of what she turned down or left behind are NOT here (the plan, 2a): .shot, .shot .sw, .pthumb,
    .dragghost, .words span.hl, .words span.drop, .screen.behind, the tag on the screen, the photo strip above a
    sentence (.strip, .grp, .addph) and the photo frame behind the video.
Her pitfalls, kept as rules (tests/talking_page_check.py checks each):
  - the class names "bar" and "sel" belong to the top bar and the highlight bar and are used for nothing else
    (a photo's bar above its words is .seg);
  - the talking video's styles name #vid, never "video" (or the corner styles would hit a Footage video too);
  - the preview's box (.phone) is sticky and the page itself scrolls; the script has no scroll frame of its own;
  - a sentence with no photo has the normal line height: the room above the words is only in .sent.hasph.
OUR_CSS adds what ours needs and hers lacks.
"""

VARS = ":root{--violet:#7A6FC9;--blue:#2F6F8F;--dock:300px}"

STYLE = r"""
body{padding-bottom:90px}
[hidden]{display:none!important}
.wrap{max-width:1180px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.head{padding:1.1rem 0 .2rem;display:grid;gap:.35rem}
h1{margin:0;font:600 clamp(22px,2.6vw,30px)/1.1 var(--sans);letter-spacing:-.03em}
.lede{margin:0;color:var(--ink-2);font-size:14.5px;max-width:52em}
.step{background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.1rem;box-shadow:0 1px 0 var(--line)}
.step h2{display:flex;align-items:center;gap:.6rem;margin:0 0 .3rem;font:600 21px/1.2 var(--sans);letter-spacing:-.02em}
.num{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--ink);color:#fff;font:600 14px/1 var(--sans)}
.say{margin:.2rem 0 .8rem;color:var(--ink-2);font-size:15px;max-width:52em}
.btn{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:999px;padding:.55rem 1rem;font:600 14px/1 var(--sans);cursor:pointer}
.btn:hover{border-color:var(--coral)}.btn.main{background:var(--ink);color:#fff;border-color:var(--ink)}.btn.main:hover{background:var(--coral-2);border-color:var(--coral-2)}
.btn.small{padding:.38rem .75rem;font-size:13px}.btn[disabled]{opacity:.4;cursor:default}.btn[disabled]:hover{border-color:var(--line)}
.vids{display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0}
.vid{border:1.5px solid var(--line);border-radius:12px;padding:.55rem .8rem;background:var(--paper);cursor:pointer;font-size:14px}
.vid.on{border-color:var(--coral-2);background:#FFF6F2}
.status{font-size:14.5px;color:var(--ink-2);margin:.4rem 0 0}.status b{color:var(--ink)}
.status.bad{color:#a33}
.line{display:flex;align-items:center;gap:.8rem;flex-wrap:wrap;background:#FFF6F2;border:1.5px solid var(--coral-l);border-radius:14px;padding:.7rem .95rem;margin:.5rem 0 .2rem}
.line span{font:italic 400 16px/1.35 var(--sans);flex:1 1 220px}
.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:-.3rem 0 .9rem}
.legend span{padding-bottom:2px}
.edit{display:grid;grid-template-columns:auto minmax(0,1fr);gap:1.4rem;align-items:start}
@media(max-width:820px){.edit{grid-template-columns:1fr}}
.phone{position:sticky;top:12px}
.screen{position:relative;height:min(600px,calc(100vh - var(--dock) - 70px));min-height:320px;aspect-ratio:9/16;margin:0 auto;background:#111;border-radius:22px;overflow:hidden;box-shadow:0 12px 30px -12px rgba(31,36,48,.45);cursor:pointer}
.screen #vid{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform-origin:50% 45%;transition:transform .25s var(--ease);z-index:2}
.screen .phw{position:absolute;z-index:3;display:none}
.screen .phw img{display:block;width:100%;height:100%;object-fit:cover;pointer-events:none}
.screen .phw video{display:none;width:100%;height:100%;object-fit:cover;pointer-events:none}
.screen .phw.movable img{border-radius:4px}
.screen.pip #vid{inset:auto;border-radius:10px;z-index:4;box-shadow:0 6px 18px rgba(0,0,0,.4)}
.screen .movable{cursor:move;outline:1.5px dashed transparent;outline-offset:1px}
.screen:hover .movable{outline-color:rgba(255,255,255,.8)}
.screen .knob{position:absolute;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;background:#fff;border:2.5px solid var(--coral-2);z-index:9;display:none;cursor:nwse-resize;box-shadow:0 1px 4px rgba(0,0,0,.4)}
.screen .cap{position:absolute;left:50%;top:71%;transform:translate(-50%,-50%);z-index:7;text-align:center;color:#fff;font:800 21px/1.15 var(--sans);text-shadow:0 1px 4px rgba(0,0,0,.75);white-space:nowrap;padding:2px 6px;border-radius:6px;cursor:move;outline:1.5px dashed transparent}
.screen:hover .cap{outline-color:rgba(255,255,255,.8)}
.screen .cap:empty{display:none}
/* phone guides: roughly what Instagram covers on a reel, so photos and captions stay clear of it */
.guides{position:absolute;inset:0;z-index:8;pointer-events:none;color:#fff;font:600 11px/1.2 var(--sans)}
.g-top{position:absolute;left:0;right:0;top:0;height:10%;background:rgba(0,0,0,.42);display:flex;align-items:flex-end;justify-content:space-between;padding:0 6% 2.2%}
.g-top b{font:700 16px/1 var(--sans)}.g-top svg{width:20px;height:20px}
.g-side{position:absolute;right:0;top:50%;bottom:9%;width:14%;background:rgba(0,0,0,.42);display:flex;flex-direction:column;align-items:center;justify-content:space-evenly}
.g-side span{display:grid;justify-items:center;gap:2px}.g-side svg{width:19px;height:19px}.g-side i{font-style:normal;font-size:9px}
.g-sq{width:19px;height:19px;border-radius:5px;border:2px solid #fff}
.g-bottom{position:absolute;left:0;right:14%;bottom:7%;height:15%;background:rgba(0,0,0,.42);padding:0 5% 7px;display:flex;flex-direction:column;justify-content:flex-end;gap:5px}
.g-user{display:flex;align-items:center;gap:6px}.g-av{width:22px;height:22px;border-radius:50%;background:#ddd;display:inline-block}
.g-user em{font-style:normal;border:1px solid rgba(255,255,255,.8);border-radius:6px;padding:2px 6px;font-size:10px}
.g-cap{height:7px;border-radius:4px;background:rgba(255,255,255,.75);width:85%}.g-cap.s{width:55%}
.g-audio{font-size:10px;opacity:.9}
.g-nav{position:absolute;left:0;right:0;bottom:0;height:7%;background:rgba(0,0,0,.6)}
.controls{display:flex;gap:.9rem;align-items:center;justify-content:center;margin-top:.6rem;flex-wrap:wrap;font-size:13.5px;color:var(--ink-2)}
.script{display:grid;gap:.8rem}
.sent{border:1px solid var(--line);border-radius:14px;padding:.75rem .9rem;background:var(--paper)}
.sent.now{border-color:var(--coral);box-shadow:0 0 0 2px var(--coral-l)}
.sent.allcut{opacity:.55}
.words{font-size:16.5px;line-height:1.75;user-select:text}
.words span{cursor:pointer;border-radius:4px;padding:0 1px;background-repeat:no-repeat;background-position:0 100%}
.words span:hover{background-color:var(--sand-l)}
.words span.cut{text-decoration:line-through;color:#a7a2a0;text-decoration-color:#d4643f}
.words span.speaking{background-color:#FCE6DD}
.words span.picked{outline:1.5px solid var(--coral);outline-offset:0}
.z-punch{background-image:linear-gradient(var(--coral),var(--coral));background-size:100% 2.5px;background-repeat:no-repeat;background-position:0 100%}
.z-zoom{background-image:linear-gradient(90deg,var(--violet) 60%,transparent 0);background-size:6px 2.5px;background-repeat:repeat-x!important;background-position:0 100%}
.fast{color:var(--blue);font-weight:600}
.tools{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center;margin-top:.55rem;font-size:13px;color:var(--ink-2)}
.tools .lbl{font-weight:600;color:var(--ink);margin-right:.1rem}
.chip{border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:.3rem .65rem;font:600 12.5px/1 var(--sans);cursor:pointer;color:var(--ink)}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.chip[disabled]{opacity:.4;cursor:default}
.s1{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,380px);gap:1.2rem;align-items:start}
.s1step{padding:1rem 1.1rem}
.say.sm{font-size:13.5px;margin:.15rem 0 .55rem}
.s1-row{display:flex;flex-wrap:wrap;gap:.45rem;align-items:center}
.s1-row .vids{margin:0}
.who-row{display:grid;grid-template-columns:1fr 1fr;gap:.45rem}
.who-row .opt{margin-top:.35rem}
@media(max-width:820px){.s1{grid-template-columns:1fr}}
.who{background:#F7F5FC;border-radius:14px;padding:.7rem .8rem}
.who-h{font:600 15px/1.2 var(--sans)}
.opt{display:block;width:100%;text-align:left;border:1.5px solid var(--line);background:var(--paper);border-radius:12px;padding:.6rem .8rem;margin-top:.45rem;cursor:pointer;font:inherit;color:var(--ink)}
.opt b{display:block;font:600 13.5px/1.25 var(--sans)}.opt span{display:block;font-size:12px;color:var(--ink-2);margin-top:2px;line-height:1.35}
.opt:hover{border-color:var(--violet)}.opt.on{border-color:var(--violet);box-shadow:0 0 0 2px #E2DEF4}
.sent.hasph .words span[data-i]{display:inline-block;position:relative;padding-top:44px;background-clip:content-box}
.seg{position:absolute;left:0;right:-.32em;top:3px;height:37px;background:#E6E0F8;box-shadow:inset 0 1px 0 rgba(122,111,201,.5),inset 0 -1px 0 rgba(122,111,201,.5);cursor:grab;z-index:1;font-style:normal}
.seg.st{border-top-left-radius:8px;border-bottom-left-radius:8px;box-shadow:inset 1px 1px 0 rgba(122,111,201,.5),inset 0 -1px 0 rgba(122,111,201,.5);z-index:2}
.seg.en{right:0;border-top-right-radius:8px;border-bottom-right-radius:8px}
.seg.vid{background:#D9EEF0}
.seg.hov{background:#DCD4F5}.seg.vid.hov{background:#C9E6E9}
.seg.on{background:#CFC5F2}.seg.vid.on{background:#B9DDE1}
.sthumbs{position:absolute;left:5px;top:3px;display:flex;gap:2px;align-items:center;white-space:nowrap;pointer-events:none}
.sthumbs img{width:25px;height:31px;object-fit:cover;border-radius:4px;display:block}
.sthumbs em{font:700 9.5px/1 var(--sans);font-style:normal;color:#4A408F;margin-left:4px;background:rgba(255,255,255,.75);padding:2px 4px;border-radius:4px}
.seg .sh{position:absolute;top:0;bottom:0;width:9px;cursor:ew-resize;background:var(--violet);opacity:0;transition:opacity .15s}
.seg .sh.l{left:0;border-radius:8px 0 0 8px}.seg .sh.r{right:0;border-radius:0 8px 8px 0}
.seg:hover .sh,.seg.hov .sh,.seg.on .sh{opacity:.85}
.words span.ghost{background-color:#E2DCF6}
.vlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-top:.6rem}
.vcard{border:1.5px solid var(--line);border-radius:12px;background:var(--paper);padding:6px;cursor:pointer;text-align:left;font:inherit;color:var(--ink)}
.vcard:hover{border-color:var(--coral)}.vcard.on{border-color:var(--coral-2);box-shadow:0 0 0 2px var(--coral-l)}
.vcard .vs{aspect-ratio:9/16;max-height:150px;width:100%;border-radius:8px;background:#222 center/cover no-repeat;display:grid;place-items:center;color:#fff;font-size:22px}
.vcard b{display:block;font:600 12px/1.25 var(--sans);margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vcard span{font-size:11.5px;color:var(--ink-2)}
.vplayer{margin-top:.8rem}.vplayer video{width:100%;max-height:46vh;border-radius:12px;background:#111}
.pmenu{position:fixed;z-index:65;background:var(--paper);border-radius:14px;padding:.6rem .7rem;box-shadow:0 0 0 1px var(--line),0 14px 34px -12px rgba(31,36,48,.45);width:300px;display:none}
.pmenu.open{display:block}
.pmenu .pm-w{font:italic 400 14px/1.3 var(--sans);margin:0 0 .45rem}
.pmenu .pm-s{display:flex;flex-wrap:wrap;gap:.3rem}
.pmenu .pm-a{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.55rem;padding-top:.5rem;border-top:1px solid var(--line)}
.hintsm{font-size:12.5px;color:var(--ink-2)}
.sel{position:fixed;z-index:50;display:none;gap:5px;align-items:center;background:var(--ink);padding:6px;border-radius:999px;box-shadow:0 8px 22px rgba(0,0,0,.25)}
.sel button{border:0;border-radius:999px;padding:.4rem .75rem;font:600 13px/1 var(--sans);cursor:pointer;background:#fff;color:var(--ink);white-space:nowrap}
.sel button:hover{background:var(--coral-l)}
.sel i{width:1px;height:20px;background:rgba(255,255,255,.3);margin:0 2px}
.modal{position:fixed;inset:0;background:rgba(20,22,28,.5);z-index:60;display:none;align-items:center;justify-content:center;padding:20px}
.modal.open{display:flex}
.sheet{background:var(--cream);border-radius:18px;max-width:900px;width:100%;max-height:86vh;overflow:auto;padding:1.1rem 1.2rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin-top:.7rem}
.pk{position:relative;cursor:pointer}
.pk img{display:block;width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:8px;box-shadow:0 0 0 1px var(--line)}
.pk:hover img{box-shadow:0 0 0 3px var(--coral)}
.pk.on img{box-shadow:0 0 0 3px var(--coral-2)}
.pk b{position:absolute;top:6px;right:6px;width:24px;height:24px;border-radius:50%;background:var(--coral-2);color:#fff;font:700 12.5px/1 var(--sans);display:none;place-items:center}
.pk.on b{display:grid}
.pickfoot{position:sticky;bottom:-1.1rem;background:var(--cream);display:flex;gap:.8rem;align-items:center;justify-content:flex-end;padding:.8rem 0 .2rem;margin-top:.6rem}
/* the dock: the timeline, then the make bar, fixed across the bottom */
.dock{position:fixed;left:0;right:0;bottom:0;z-index:40;box-shadow:0 -6px 20px -12px rgba(31,36,48,.25)}
.tl{background:#F3F1EB;border-top:1px solid var(--line)}
.tl-in{max-width:1180px;margin:0 auto;padding:.55rem clamp(16px,4vw,40px) .35rem}
.tl-row{display:flex;align-items:center;gap:.45rem;flex-wrap:wrap}
.tl-play{width:40px;height:40px;border-radius:50%;border:0;background:var(--ink);color:#fff;font-size:14px;cursor:pointer;flex:none}
.tl-play:hover{background:var(--coral-2)}
.tl-time{font:600 13.5px/1 var(--sans);font-variant-numeric:tabular-nums;min-width:104px;color:var(--ink)}
.tl-sep{width:1px;height:24px;background:var(--line);margin:0 .2rem}
.tl-group{display:inline-flex;align-items:center;gap:.3rem;font-size:12.5px;color:var(--ink-2)}
.tl-group .lbl{font-weight:600;color:var(--ink);margin-right:.1rem}
.tl-scale{margin-left:auto;display:inline-flex;align-items:center;gap:.35rem;font-size:12.5px;color:var(--ink-2)}
.tl-scale input{width:110px;accent-color:var(--coral-2)}
.tl-scale button{width:26px;height:26px;border-radius:50%;border:1px solid var(--line);background:var(--paper);cursor:pointer;font:600 15px/1 var(--sans);color:var(--ink)}
.tl-track{position:relative;overflow-x:auto;overflow-y:hidden;margin-top:.5rem;background:var(--paper);border-radius:12px;box-shadow:0 0 0 1px var(--line);user-select:none;touch-action:pan-x;cursor:col-resize}
.tl-inner{position:relative;min-width:100%}
.tl-ruler{position:relative;height:18px;border-bottom:1px solid var(--line);font:500 10px/18px var(--sans);color:var(--ink-2)}
.tl-ruler span{position:absolute;top:0;padding-left:3px;border-left:1px solid var(--line);height:100%;white-space:nowrap}
.tl-photos{position:relative;height:30px}
.tl-ph{position:absolute;top:3px;bottom:2px;border-radius:6px;background:var(--sand-l);display:flex;align-items:center;gap:2px;overflow:hidden;font:600 10.5px/1 var(--sans);color:var(--ink-2);white-space:nowrap;cursor:pointer;box-shadow:inset 0 0 0 1px rgba(122,111,201,.3);padding:0 9px}
.tl-ph img{height:100%;width:17px;object-fit:cover;flex:none}
.tl-ph span{margin-left:4px}
.tl-ph:hover{box-shadow:inset 0 0 0 1.5px var(--violet)}
.tl-ph.on{box-shadow:inset 0 0 0 2.5px var(--violet);background:#E2DEF4}
.tl-ph-h{position:absolute;top:0;bottom:0;left:0;width:8px;cursor:ew-resize;background:rgba(122,111,201,.4);z-index:2}
.tl-ph-h.r{left:auto;right:0}
.tl-ph-h:hover{background:var(--violet)}
.tl-clips{position:relative;height:44px}
.tl-clip{position:absolute;top:3px;bottom:3px;border-radius:7px;background:var(--coral-l);box-shadow:inset 0 0 0 1px rgba(212,100,63,.35);overflow:hidden;padding:4px 6px;font:500 11.5px/1.25 var(--sans);color:var(--ink);white-space:nowrap;cursor:pointer}
.tl-clip span{display:block;overflow:hidden;text-overflow:ellipsis}
.tl-x{position:absolute;top:2px;right:10px;width:18px;height:18px;border-radius:50%;background:var(--ink);color:#fff;font:700 13px/18px var(--sans);text-align:center;cursor:pointer;z-index:4}
.tl-x:hover{background:var(--coral-2)}
.tl-clip-h{position:absolute;top:0;bottom:0;left:0;width:8px;cursor:ew-resize;background:rgba(212,100,63,.45);z-index:2;opacity:0;transition:opacity .15s}
.tl-clip-h.r{left:auto;right:0}
.tl-clip:hover .tl-clip-h{opacity:1}.tl-clip-h:hover{background:var(--coral-2)}
.tl-clip .bd{display:inline-block;font:700 9.5px/1 var(--sans);background:rgba(31,36,48,.75);color:#fff;border-radius:4px;padding:2px 4px;margin:0 3px 3px 0}
.tl-clip.fast{background:repeating-linear-gradient(135deg,#DDEBF2 0 6px,#EAF3F7 6px 12px);box-shadow:inset 0 0 0 1px rgba(47,111,143,.35)}
.tl-clip.on{box-shadow:inset 0 0 0 2.5px var(--coral-2);background:#FFD9CB}
.tl-clip.fast.on{background:repeating-linear-gradient(135deg,#CFE2EC 0 6px,#E0EDF3 6px 12px)}
.tl-words{position:relative;height:22px;border-top:1px dashed var(--line)}
.tl-words.off{display:none}
.tl-w{position:absolute;top:3px;font:500 11px/16px var(--sans);white-space:nowrap;overflow:hidden;color:var(--ink);border-left:1px solid rgba(31,36,48,.15);padding-left:2px}
.tl-head{position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;background:var(--coral-2);pointer-events:none;z-index:5}
.tl-head::before{content:"";position:absolute;top:0;left:-5px;width:12px;height:12px;border-radius:0 0 6px 6px;background:var(--coral-2)}
.tl-hint{font-size:12px;color:var(--ink-2);margin-top:.35rem}
.make{background:var(--paper);border-top:1px solid var(--line)}
.make .in{max-width:1180px;margin:0 auto;padding:.7rem clamp(16px,4vw,40px);display:flex;gap:1rem;align-items:center;justify-content:space-between;flex-wrap:wrap}
.make .sum{font-size:14px;color:var(--ink-2)}.make .sum b{color:var(--ink)}
.result{margin-top:1rem}
.result p{margin:.2rem 0}
.toast{position:fixed;left:50%;top:18px;transform:translateX(-50%);background:var(--ink);color:#fff;padding:.6rem 1rem;border-radius:999px;font-size:14px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:70;max-width:90vw;text-align:center}
.toast.on{opacity:1}
"""

# Ours. A video's chip is a real button (hers: a span), so it needs a button's own font and colour put back (the
# same for a photo in the picker and a Move chip); a stretch's bar is never text to highlight; a video in the
# picker that is not ready yet looks it; a
# long name (a shoot, a video) breaks instead of pushing a phone sideways; the line for a video still copying in;
# and a ring for the keyboard.
OUR_CSS = r"""
.vid{font:inherit;font-size:14px;color:var(--ink);max-width:100%;overflow-wrap:anywhere;text-align:left}
.vid:disabled{opacity:.5;cursor:default}
h1,.status,.line span,.say,.opt b,.opt span{overflow-wrap:anywhere}
.line span{min-width:0}
.s1>div{min-width:0}
.coming{font-size:13px;color:var(--ink-2);margin:.35rem 0 0}
.btn:focus-visible,.vid:focus-visible,.opt:focus-visible,.chip:focus-visible{outline:2px solid var(--coral-2);outline-offset:2px}
.tl-time{white-space:nowrap}
@media(max-width:520px){.who-row{grid-template-columns:1fr}.tl-scale{margin-left:0}}
.pk{display:block;width:100%;border:0;background:none;padding:0;font:inherit;color:inherit}
.pk:focus-visible,.vcard:focus-visible{outline:2px solid var(--coral-2);outline-offset:2px}
.vcard:disabled{opacity:.55;cursor:default}.vcard:disabled:hover{border-color:var(--line)}
.vcard b{overflow-wrap:anywhere}
.tools .chip{font-family:inherit}
.seg{user-select:none;-webkit-user-select:none;touch-action:none}
.sthumbs{user-select:none;-webkit-user-select:none}
.pmenu{max-width:calc(100vw - 16px)}
"""


def css():
    """Everything after look.head_css() in the page's <style>."""
    return VARS + STYLE + OUR_CSS
