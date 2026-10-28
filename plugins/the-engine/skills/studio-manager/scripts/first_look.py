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
import json
import sys
from datetime import datetime
from pathlib import Path
import subprocess

CSS = """
.talk{display:grid;grid-template-columns:auto 1fr;gap:1.1rem;align-items:center;background:var(--sun-l);border-radius:var(--r);padding:1.3rem 1.5rem;margin:1.8rem 0 0}
.talk .mic{width:54px;height:54px;border-radius:50%;background:var(--coral);color:#fff;display:grid;place-items:center;flex:none}
.talk .mic svg{width:24px;height:24px}
.talk h3{font:600 18px/1.25 var(--sans);letter-spacing:-.015em;margin-bottom:.25rem}
.talk p{color:var(--ink-2);font-size:15px}
.talk .eg{font:italic 400 17px/1.4 var(--display);color:var(--ink);margin-top:.35rem}
.shoots-head{display:grid;gap:.5rem;padding-top:clamp(2rem,4vw,3rem)}
.shoots-head .h2{font:600 clamp(28px,3.6vw,44px)/1.05 var(--sans);letter-spacing:-.03em;text-wrap:balance}
.shoots{display:grid;gap:1.5rem;padding:1.6rem 0 1rem}
.shoot{display:grid;gap:clamp(1.4rem,3vw,2.2rem);background:var(--paper);border-radius:var(--r);padding:clamp(1.2rem,2.6vw,2rem)}
.shoot .top{display:grid;grid-template-columns:1.05fr 1fr;gap:clamp(1.2rem,3vw,2.4rem);align-items:center}
.shoot:nth-child(even) .top{grid-template-columns:1fr 1.05fr}
.shoot:nth-child(even) .pics{order:2}
.more{display:grid;gap:.6rem}
.more .row{display:grid;grid-template-columns:repeat(5,1fr);gap:clamp(.6rem,1.6vw,1.1rem);padding:.6rem 0 .4rem;align-items:end}
.more .ph{border-radius:18px;overflow:hidden;aspect-ratio:4/5;background:var(--sand-l);transform:rotate(var(--rot,0deg));transition:transform .6s var(--ease),box-shadow .6s var(--ease)}
.more .ph:nth-child(2n){margin-bottom:1.1rem}
.more .ph:hover{transform:rotate(0) translateY(-6px);box-shadow:var(--shadow);z-index:1}
.more img{width:100%;height:100%;object-fit:cover;display:block}
.more .line{font-size:14px;color:var(--ink-2);margin:0}.more .line b{color:var(--ink)}
.shoot .note{margin:0}
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
.name{display:grid;gap:.45rem}
.name label{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.name .field{position:relative}
.name .pen{position:absolute;left:1.05rem;top:50%;transform:translateY(-50%);color:var(--coral);font-size:20px;pointer-events:none}
.name input{font:600 clamp(22px,2.4vw,30px)/1.15 var(--sans);letter-spacing:-.02em;color:var(--ink);background:var(--paper);border:2px dashed var(--coral);border-radius:18px;padding:.75rem 1rem .75rem 2.9rem;width:100%;outline:none;cursor:text;box-shadow:0 10px 24px -18px rgba(240,127,90,.8);transition:border-color .3s,background .3s,box-shadow .3s}
.name input:hover{background:var(--sun-l)}
.name input:focus{border-style:solid;border-color:var(--coral);background:var(--paper);box-shadow:0 0 0 4px rgba(240,127,90,.18)}
.name input::placeholder{color:#9AA0AB;font-weight:400;font-style:italic;font-family:var(--sans);font-size:.72em;letter-spacing:0}
.name small{color:var(--ink-2);font-size:13px}.name small b{color:var(--ink);font-weight:600}
.save{display:flex;flex-wrap:wrap;align-items:center;gap:1rem;padding:1.2rem 0 .6rem}
.btn{display:inline-flex;align-items:center;gap:1.1rem;padding:.7rem .7rem .7rem 1.9rem;border-radius:999px;background:var(--coral);color:#fff;font:600 22px/1 var(--sans);letter-spacing:-.01em;border:1.5px solid var(--coral);cursor:pointer;box-shadow:0 18px 36px -20px rgba(240,127,90,.9);transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.btn:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.btn .arr{width:48px;height:48px;border-radius:50%;background:var(--paper);color:var(--coral);display:grid;place-items:center;font-size:22px}
.toast{font-size:14px;color:var(--ink-2);min-height:1.2em}
.undo{font-size:13px;color:var(--ink-2);max-width:40em;margin-bottom:1.5rem}
@media(max-width:900px){.shoot .top,.shoot:nth-child(even) .top{grid-template-columns:1fr}.shoot:nth-child(even) .pics{order:0}.talk{grid-template-columns:1fr}.more .row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.more .row{grid-template-columns:repeat(2,1fr)}}
"""

SCRIPT = """<script>
const toast=document.getElementById('toast');
async function save(){const names={};for(const i of document.querySelectorAll('.name input')){if(i.value.trim())names[i.name]=i.value.trim();}
 if(!location.protocol.startsWith('http')){toast.textContent='Open this page through the Studio to save names, or just tell Claude.';return;}
 try{const r=await fetch('/names',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(names)});
  toast.textContent=r.ok?(Object.keys(names).length+' name'+(Object.keys(names).length==1?'':'s')+' locked in. I\\'ll rename everything to match.'):'Could not save. Tell Claude the names instead.';}
 catch(e){toast.textContent='Could not save. Tell Claude the names instead.';}}
document.getElementById('save').addEventListener('click',save);
// Enter in a box moves to the next box; only the button saves, so nothing locks in by accident.
const boxes=[...document.querySelectorAll('.name input')];
boxes.forEach((i,k)=>i.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();const nx=boxes[k+1];if(nx)nx.focus();else i.blur();}}));
</script>"""

MIC = ("<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
       "<rect x='9' y='3' width='6' height='11' rx='3'/><path d='M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8'/></svg>")
ROTS = [-2.5, 2, -1.5]


def day(iso):
    return datetime.fromisoformat(iso).strftime("%A, %B %-d, %Y")



def big_preview(studio, g, p):
    """A sharp copy (2000 px) of a group preview for the report's click-to-enlarge view, made once from
    the photo itself with the Mac's own sips into groups/big/. Returns the path to use, or None when the
    photo is not reachable (drive unplugged): the page then just shows the small preview bigger."""
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
    big.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", "-Z", "2000", str(src), "--out", str(big)],
                       capture_output=True)
    return f"groups/big/{p}" if r.returncode == 0 and big.exists() else None


def peeks_by_shoot(studio):
    """{shoot id: [preview file names]} of the sneak peeks that have a preview, in the order they were picked."""
    out = {}
    pj = studio / "sneak-peeks.json"
    if not pj.exists() and (studio / "picks.json").exists():
        pj = studio / "picks.json"
    if not pj.exists():
        return out
    try:
        picks = json.loads(pj.read_text()).get("picks", [])
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
    out = ["<article class='note'>"]
    out.append("<div class='to'><span>Note to your client</span>" + (f"<span>To {e(note['to'])}</span>" if note.get("to") else "<span>[Name] still to fill in</span>") + "</div>")
    if note.get("body"):
        if note.get("subject"):
            out.append(f"<div class='subj'>{e(note['subject'])}</div>")
        out.append(f"<pre class='body'>{e(note['body'].rstrip())}</pre>")
        out.append("<div class='row'><button class='copy' data-what='body'>Copy the note</button>"
                   + ("<button class='copy sub' data-what='subject'>Copy the subject</button>" if note.get("subject") else "")
                   + "<span class='did'></span></div>")
    else:
        out.append("<p class='empty'>Not written yet. Say “write the note for this one” and it'll be here.</p>")
    out.append("</article>")
    return "\n".join(out)


def shoots_section(studio):
    """(html, script) for the shoots, or None when the card has not been grouped and decided yet.
    Each shoot is one block that builds downward: three photos framing the recap and the name box, then the
    rest of its sneak peeks in a row, then the note to the client (Dustin, Oct 28)."""
    if not (studio / "groups.json").exists() or not (studio / "shoots.json").exists():
        return None
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]}
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    names = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    e = html.escape
    total = sum(s["photos"] for s in shoots)
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

    out = ["<div class='wrap'><div class='shoots-head'><span class='eyebrow'>What's on the card</span>",
           f"<h2 class='h2'>{n} shoot{'s' if n != 1 else ''}, <span class='swap'>{total:,} photos</span>, across {len(days)} day{'s' if len(days) != 1 else ''} of shooting.</h2>",
           f"<p class='lede'>{'Each one is already in its own folder, named by date. Give it a better name and everything is renamed to match.' if filed else 'Give each one a name and it is filed, named and ready for you.'}</p>",
           f"<div class='talk'><span class='mic'>{MIC}</span><div><h3>Just tell me who's who.</h3>"
           "<p>Say it the way you'd say it to a person. I'll sort out which is which and fill the names in.</p>"
           "<p class='eg'>“The big one is the Lani swim shoot, the sunset one is for Kaia, and the yoga day is Marisol's.”</p></div></div>",
           "</div><div class='shoots'>"]
    for i, s in enumerate(shoots, 1):
        gs = [groups[g] for g in s["groups"]]
        start = gs[0]["start"]
        mine = peeks.get(s["id"], [])
        if len(mine) >= 3:   # the sneak peeks frame the card: the first is the hero, the next two beside it
            pics = [(p, None) for p in mine[:3]]
            rest = mine[3:8]
        else:                # not picked yet: three previews spread across the shoot
            pics = [(p, g) for g in gs for p in g.get("previews", [])]
            if len(pics) > 3:  # the hero from the middle of the shoot, two more spread out
                pics = [pics[len(pics) // 2], pics[0], pics[-1]]
            rest = []
        lenses = sorted({l for g in gs for l in g.get("lenses", [])})
        bodies = max(g["bodies"] for g in gs)
        val = names.get(s["id"], "")
        def img(p, g):
            if g is None:
                return f"<img src='sneak-peeks/{e(p)}' alt=''>"
            big = big_preview(studio, g, p)
            return f"<img src='groups/{e(p)}' alt=''" + (f" data-big='{e(big)}'" if big else "") + ">"
        out.append("<article class='shoot'><div class='top'>")
        out.append("<div class='pics'>" + "".join(
            f"<div class='ph' data-g='{e(s['id'])}' style='--rot:{ROTS[j % len(ROTS)]}deg' title='Click to see it bigger'>{img(p, g)}</div>"
            for j, (p, g) in enumerate(pics))
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
        out.append("</div></div>")   # copy, top
        if mine:
            out.append("<div class='more'><span class='eyebrow'>Sneak peeks</span>"
                       f"<p class='line'><b>{len(mine[:8])} to edit first.</b> Picked for variety and flow, so they look good together: "
                       "the three above and these. In Lightroom they're one filter away, the keyword “sneak peek”. Edit these, send a few with the note, and the rest can wait.</p>")
            if rest:
                out.append("<div class='row'>" + "".join(
                    f"<div class='ph' data-g='{e(s['id'])}' style='--rot:{ROTS[(j + 3) % len(ROTS)]}deg' title='Click to see it bigger'><img src='sneak-peeks/{e(p)}' alt=''></div>"
                    for j, p in enumerate(rest)) + "</div>")
            out.append("</div>")
        card = note_card(notes.get(s["id"]))
        if card:
            out.append(card)
        out.append("</article>")
    out.append("</div>")
    out.append("<div class='wrap'><div class='save'>"
               "<button class='btn' id='save'>Lock the names in<span class='arr'>&#10003;</span></button>"
               f"<span class='toast' id='toast'>{'All named.' if named == n and shoots else (f'{named} of {n} named so far.' if named else '')}</span></div>"
               "<p class='undo'>Nothing on the card is ever changed. Names go on the copy on your drive, and you can rename any shoot later by just asking.</p></div>")
    return "\n".join(out), SCRIPT


def write_page(session_dir):
    """Kept so older links still work: first-look.html now just opens the report."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from where import locate
    _, studio = locate(session_dir)
    page = studio / "first-look.html"
    page.write_text("<!doctype html><meta http-equiv='refresh' content='0; url=report.html'><a href='report.html'>The report</a>")
    return page


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: first_look.py <session folder>")
    print(write_page(sys.argv[1]))
