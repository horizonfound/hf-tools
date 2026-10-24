#!/usr/bin/env python3
"""The first look: _studio/first-look.html. Right after "backup now," while
the copy runs, she sees what came off the card as shoots, each with a few
previews, a short recap, and a name to give it. Talking is the way to fill
it in (the Claude app has the mic); the boxes are there for a spelling.

Reads _studio/groups.json (the time-gap groups and their previews) and
_studio/shoots.json (which groups Claude merged into one shoot, with a recap
and a suggested name). Names she gives are kept in _studio/names.json by
serve_report.py, and shown filled in when the page is opened again.

    python3 first_look.py "<session folder>"
"""
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_page import CSS as BASE_CSS, FONTS  # noqa: E402

CSS = BASE_CSS + """
.hero{padding-bottom:1rem}
.talk{display:grid;grid-template-columns:auto 1fr;gap:1.1rem;align-items:center;background:var(--sun-l);border-radius:var(--r);padding:1.3rem 1.5rem;margin:1.6rem 0 0}
.talk .mic{width:54px;height:54px;border-radius:50%;background:var(--coral);color:#fff;display:grid;place-items:center;flex:none}
.talk .mic svg{width:24px;height:24px}
.talk h3{font:600 18px/1.25 var(--sans);letter-spacing:-.015em;margin-bottom:.25rem}
.talk p{color:var(--ink-2);font-size:15px}
.talk .eg{font:italic 400 17px/1.4 var(--display);color:var(--ink);margin-top:.35rem}
.shoots{display:grid;gap:1.5rem;padding:2rem 0 1rem}
.shoot{display:grid;grid-template-columns:1.05fr 1fr;gap:clamp(1.2rem,3vw,2.4rem);background:var(--paper);border-radius:var(--r);padding:clamp(1.2rem,2.6vw,2rem);align-items:center}
.shoot:nth-child(even){grid-template-columns:1fr 1.05fr}
.shoot:nth-child(even) .pics{order:2}
.pics{position:relative;display:grid;grid-template-columns:1.35fr 1fr;grid-template-rows:1fr 1fr;gap:.7rem;aspect-ratio:5/4}
.pics .ph{border-radius:20px;overflow:hidden;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.pics .ph:first-child{grid-row:1/3}
.pics .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow);z-index:1}
.pics img{width:100%;height:100%;object-fit:cover}
.pics .chip{z-index:2}
.copy{display:grid;gap:.9rem}
.copy .n{font:300 44px/1 var(--display);color:var(--coral-2)}
.copy .meta{display:flex;flex-wrap:wrap;gap:.45rem}
.tag{font:500 12px/1 var(--sans);padding:.5rem .8rem;border-radius:999px;background:var(--cream)}
.tag.sun{background:var(--sun-l)}.tag.ocean{background:var(--ocean-l)}
.recap{font-size:16.5px;line-height:1.55;color:var(--ink-2);max-width:32em;text-wrap:pretty}
.recap b{color:var(--ink)}
.name{display:grid;gap:.45rem}
.name label{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.name .field{position:relative}
.name .pen{position:absolute;left:1.05rem;top:50%;transform:translateY(-50%);color:var(--coral);font-size:20px;pointer-events:none}
.name input{font:600 clamp(22px,2.4vw,30px)/1.15 var(--sans);letter-spacing:-.02em;color:var(--ink);background:var(--paper);border:2px dashed var(--coral);border-radius:18px;padding:.75rem 1rem .75rem 2.9rem;width:100%;outline:none;cursor:text;box-shadow:0 10px 24px -18px rgba(240,127,90,.8);transition:border-color .3s,background .3s,box-shadow .3s}
.name input:hover{background:var(--sun-l)}
.name input:focus{border-style:solid;border-color:var(--coral);background:var(--paper);box-shadow:0 0 0 4px rgba(240,127,90,.18)}
.name input::placeholder{color:#9AA0AB;font-weight:400;font-style:italic;font-family:var(--sans);font-size:.72em;letter-spacing:0}
.name small{color:var(--ink-2);font-size:13px}.name small b{color:var(--ink);font-weight:600}
.save{display:flex;flex-wrap:wrap;align-items:center;gap:1rem;padding:1.6rem 0 2.6rem}
.btn{display:inline-flex;align-items:center;gap:1.1rem;padding:.7rem .7rem .7rem 1.9rem;border-radius:999px;background:var(--coral);color:#fff;font:600 22px/1 var(--sans);letter-spacing:-.01em;border:1.5px solid var(--coral);cursor:pointer;box-shadow:0 18px 36px -20px rgba(240,127,90,.9);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.btn:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.btn .arr{width:48px;height:48px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:22px}
.toast{font-size:14px;color:var(--ink-2);min-height:1.2em}
.undo{font-size:13px;color:var(--ink-2);max-width:40em}
@media(max-width:900px){.shoot,.shoot:nth-child(even){grid-template-columns:1fr}.shoot:nth-child(even) .pics{order:0}.talk{grid-template-columns:1fr}}
"""

MIC = ("<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
       "<rect x='9' y='3' width='6' height='11' rx='3'/><path d='M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8'/></svg>")
ROTS = [-2.5, 2, -1.5]


def clock(iso):
    return datetime.fromisoformat(iso).strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")


def day(iso):
    return datetime.fromisoformat(iso).strftime("%A, %B %-d, %Y")


def build(studio):
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]}
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    names = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    e = html.escape

    total = sum(s["photos"] for s in shoots)
    days = sorted({groups[g]["start"][:10] for s in shoots for g in s["groups"]})
    named = sum(1 for s in shoots if names.get(s["id"]))

    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>First look · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body>",
           "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>",
           f"<span class='when'>{'All backed up, verified and filed.' if all(s.get('folder') for s in shoots) else 'The copy is running.'} This is what's on the card.</span>"
           + ("<a class='nav' href='report.html'>Show me my report<span class='arr'>&#8599;</span></a>" if (studio / "report.html").exists() else "")
           + "</div></div>"]

    out.append("<section class='wrap hero'><span class='eyebrow'>First look</span>")
    n = len(shoots)
    out.append(f"<h1 class='h1'>{n} shoot{'s' if n != 1 else ''} on this card, <span class='swap'>{total:,} photos.</span></h1>")
    out.append(f"<p class='lede'>Across {len(days)} day{'s' if len(days) != 1 else ''} of shooting. Give each one a name and it's filed, named and ready "
               "for you in the morning. Skip it and they'll be named by date until you get to it.</p>")
    out.append(f"<div class='talk'><span class='mic'>{MIC}</span><div><h3>Just tell me who's who.</h3>"
               "<p>Say it the way you'd say it to a person. I'll sort out which is which and fill the names in.</p>"
               "<p class='eg'>“The big one is the Lani swim shoot, the sunset one is for Kaia, and the yoga day is Marisol's.”</p></div></div>")
    out.append("</section>")

    out.append("<div class='wrap'><div class='shoots'>")
    for i, s in enumerate(shoots, 1):
        gs = [groups[g] for g in s["groups"]]
        start, end = gs[0]["start"], gs[-1]["end"]
        minutes = sum(g["minutes"] for g in gs)
        pics = [p for g in gs for p in g.get("previews", [])]
        # three previews: the hero from the middle of the shoot, two more spread out
        if len(pics) > 3:
            pics = [pics[len(pics) // 2], pics[0], pics[-1]]
        lenses = sorted({l for g in gs for l in g.get("lenses", [])})
        bodies = max(g["bodies"] for g in gs)
        val = names.get(s["id"], "")
        out.append("<article class='shoot'>")
        out.append("<div class='pics'>" + "".join(
            f"<div class='ph' style='--rot:{ROTS[j % len(ROTS)]}deg'><img src='groups/{e(p)}' alt=''></div>" for j, p in enumerate(pics))
            + f"<span class='chip f-sun' style='--rot:-5deg;top:-.6rem;left:-.5rem'>{s['photos']:,} photos</span>"
            + (f"<span class='chip f-ocean' style='--rot:4deg;bottom:-.5rem;right:-.3rem'>{len(gs)} outfits or breaks</span>" if len(gs) > 1 else "")
            + "</div>")
        out.append("<div class='copy'>")
        out.append(f"<span class='n'>{i:02d}</span>")
        out.append("<div class='meta'>"
                   f"<span class='tag sun'>{e(day(start))}</span>"
                   + (f"<span class='tag ocean'>{bodies} cameras</span>" if bodies > 1 else "")
                   + "".join(f"<span class='tag'>{e(l)}</span>" for l in lenses[:2]) + "</div>")
        out.append(f"<p class='recap'>{e(s.get('recap', ''))}</p>")
        out.append(f"<div class='name'><label for='{s['id']}'>What should I call this one?</label>"
                   f"<div class='field'><span class='pen'>&#9998;</span>"
                   f"<input id='{s['id']}' name='{s['id']}' value='{e(val)}' placeholder='Type a name here, or just tell Claude' autocomplete='off'></div>"
                   + (f"<small>Filed as <b>{e(s.get('name') or s.get('suggested', ''))}</b>. Give it a better name and everything gets renamed to match.</small></div>"
                      if s.get("folder") else
                      f"<small>Blank means it's filed as <b>{e(s.get('suggested', ''))}</b> until you say otherwise.</small></div>"))
        out.append("</div></article>")
    out.append("</div>")

    out.append("<div class='save'>"
               "<button class='btn' id='save'>Lock the names in<span class='arr'>&#10003;</span></button>"
               f"<span class='toast' id='toast'>{'All named.' if named == len(shoots) and shoots else (f'{named} of {len(shoots)} named so far.' if named else '')}</span></div>")
    out.append("<p class='undo'>Nothing on the card is ever changed. Names go on the copy on your drive, and you can rename any shoot later by just asking.</p></div>")
    out.append("<footer class='foot'><div class='wrap'>Nothing deleted, nothing moved, nothing posted.</div><div class='wordmark'>The Studio</div></footer>")
    out.append("""<script>
const toast=document.getElementById('toast');
async function save(){const names={};for(const i of document.querySelectorAll('.name input')){if(i.value.trim())names[i.name]=i.value.trim();}
 if(!location.protocol.startsWith('http')){toast.textContent='Open this page through the Studio to save names, or just tell Claude.';return;}
 try{const r=await fetch('/names',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(names)});
  toast.textContent=r.ok?(Object.keys(names).length+' name'+(Object.keys(names).length==1?'':'s')+' locked in. Sleep well.'):'Could not save. Tell Claude the names instead.';}
 catch(e){toast.textContent='Could not save. Tell Claude the names instead.';}}
document.getElementById('save').addEventListener('click',save);
// Enter in a box moves to the next box; only the button at the bottom saves, so nothing locks in by accident.
const boxes=[...document.querySelectorAll('.name input')];
boxes.forEach((i,k)=>i.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();const nx=boxes[k+1];if(nx)nx.focus();else i.blur();}}));
</script></body></html>""")
    return "\n".join(out)


def write_page(session_dir):
    studio = Path(session_dir) / "_studio"
    page = studio / "first-look.html"
    page.write_text(build(studio))
    return page


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: first_look.py <session folder>")
    print(write_page(sys.argv[1]))
