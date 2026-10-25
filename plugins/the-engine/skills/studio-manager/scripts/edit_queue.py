#!/usr/bin/env python3
"""The editing queue: the shoots still to edit, with due dates, in the order
the photographer wants to work on them.

It is the bridge between the night and the reel: a night's shoots are added
when the photographer says so (some shoots are just for them), "I'm done with
the beach shoot" takes one off and starts the next step, and a heads-up comes
three days before anything is due.

Kept in ~/.studio/queue.json with a few thumbnails per shoot copied to
~/.studio/queue-thumbs/, so the page works even when the drive is unplugged.
Nothing here ever touches a photo.

    python3 edit_queue.py add --night "<the night's folder or records>" --shoot s1 --due 2w
    python3 edit_queue.py add-manual --name "Garcia family" --due 2026-11-07 [--shot 2026-10-18]
    python3 edit_queue.py list                      what's waiting, in their order
    python3 edit_queue.py done "beach"              mark finished (a word from the name is enough)
    python3 edit_queue.py undo "beach"
    python3 edit_queue.py due "beach" 1w            a new due date (1w 2w 3w, this-week, or 2026-11-07)
    python3 edit_queue.py move "beach" --to 1       put it first
    python3 edit_queue.py options                   the due choices, their most-picked first
    python3 edit_queue.py reminders [--mark]        due in 3 days or late (--mark: for the daily check)
    python3 edit_queue.py page                      write ~/.studio/queue.html
    python3 edit_queue.py setup --on|--off          keep a queue or not (asked once)
    python3 edit_queue.py status                    on, off, or never asked
    python3 edit_queue.py offers [--mark]           shoots ticked off on the page that still need "want a reel?"
    python3 edit_queue.py serve                     the page, live: check off, drag, change dates
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
QFILE = HOME / "queue.json"
THUMBS = HOME / "queue-thumbs"
PAGE = HOME / "queue.html"
HEADS_UP_DAYS = 3
DUE_CHOICES = {"1w": ("1 week", 7), "2w": ("2 weeks", 14), "3w": ("3 weeks", 21)}


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


# ---------- the list ----------

def load():
    if QFILE.exists():
        try:
            q = json.loads(QFILE.read_text())
            q.setdefault("shoots", [])
            q.setdefault("picks", {})
            q.setdefault("manual_order", False)
            return q
        except ValueError:
            sys.exit(f"STOP: {QFILE} could not be read. Nothing changed.")
    return {"shoots": [], "picks": {}, "manual_order": False}


def save(q):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = QFILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(q, indent=1, ensure_ascii=False))
    os.replace(tmp, QFILE)  # never a half-written list


def today():
    override = os.environ.get("STUDIO_TODAY")  # for tests
    return date.fromisoformat(override) if override else date.today()


def due_date(when, base=None):
    """1w 2w 3w ("1 week", "2 weeks"...), this-week (the coming Friday), or a date."""
    base = base or today()
    w = str(when).strip().lower().replace(" ", "")
    for key, (_, days) in DUE_CHOICES.items():
        if w in (key, key[0] + "week", key[0] + "weeks", key[0] + "wk"):
            return (base + timedelta(days=days)).isoformat(), key
    if w in ("thisweek", "this-week", "friday"):
        return (base + timedelta(days=(4 - base.weekday()) % 7)).isoformat(), "this-week"
    try:
        return date.fromisoformat(str(when).strip()).isoformat(), "date"
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%b %d %Y", "%B %d %Y", "%b %d", "%B %d"):
        try:
            d = datetime.strptime(str(when).strip().replace(",", ""), fmt).date()
            if d.year == 1900:  # no year given: the next one coming
                d = d.replace(year=base.year)
                if d < base:
                    d = d.replace(year=base.year + 1)
            return d.isoformat(), "date"
        except ValueError:
            continue
    sys.exit(f"STOP: I could not read '{when}' as a due date. Try 1w, 2w, 3w, this-week, or a date like 2026-11-07.")


def waiting(q):
    """The shoots still to edit, in the photographer's order (or soonest due, until they move one)."""
    w = [s for s in q["shoots"] if s.get("status") != "finished"]
    if not q.get("manual_order"):
        w.sort(key=lambda s: (s.get("due") or "9999", s.get("added", "")))
    return w


def finished(q):
    return sorted((s for s in q["shoots"] if s.get("status") == "finished"), key=lambda s: s.get("finished_at", ""), reverse=True)


def reorder(q, ids):
    """Put the waiting shoots in this order; finished ones keep their place after them."""
    by_id = {s["id"]: s for s in q["shoots"]}
    head = [by_id[i] for i in ids if i in by_id and by_id[i].get("status") != "finished"]
    rest = [s for s in waiting(q) if s not in head]
    q["shoots"] = head + rest + finished(q)
    q["manual_order"] = True


def find(q, text, include_finished=True):
    pool = q["shoots"] if include_finished else waiting(q)
    t = text.strip().lower()
    exact = [s for s in pool if s["id"] == text or s["name"].lower() == t]
    if exact:
        return exact[0]
    hits = [s for s in pool if t in s["name"].lower()]
    if len(hits) > 1:
        live = [s for s in hits if s.get("status") != "finished"]
        hits = live if len(live) == 1 else hits
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"STOP: nothing in the queue matches '{text}'.")
    sys.exit("STOP: more than one shoot matches '" + text + "': " + "; ".join(s["name"] for s in hits) + ". Say which.")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "shoot"


def new_id(q, name, shot):
    base = f"{slug(name)}-{shot or 'undated'}"
    have = {s["id"] for s in q["shoots"]}
    i, out = 2, base
    while out in have:
        out, i = f"{base}-{i}", i + 1
    return out


def note_pick(q, how):
    if how in DUE_CHOICES:
        q["picks"][how] = q["picks"].get(how, 0) + 1


def place(q, shoot):
    """A new shoot goes where its due date fits, even after they have reordered."""
    w = waiting(q)
    if not q.get("manual_order"):
        q["shoots"].append(shoot)
        return
    pos = next((i for i, s in enumerate(w) if (s.get("due") or "9999") > (shoot.get("due") or "9999")), len(w))
    w.insert(pos, shoot)
    q["shoots"] = w + finished(q)


# ---------- adding ----------

def add_from_night(q, night, shoot_id, when, name=None):
    from where import locate
    root, studio = locate(night)
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        sys.exit(f"STOP: no shoot {shoot_id} in that night. Its shoots: " + ", ".join(x["id"] for x in shoots))
    names = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    name = name or names.get(shoot_id) or s.get("name") or s.get("suggested") or shoot_id
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]} if (studio / "groups.json").exists() else {}
    gs = [groups[g] for g in s.get("groups", []) if g in groups]
    shot = (gs[0]["start"][:10] if gs else None)
    due, how = due_date(when)
    # already queued from this night? then this is a new due date, not a second card
    for x in q["shoots"]:
        if x.get("studio") == str(studio) and x.get("shoot") == shoot_id:
            x["due"], x["name"] = due, name
            if x.get("status") == "finished":
                x["status"] = "waiting"
                x.pop("finished_at", None)
            note_pick(q, how)
            return x, False
    sid = new_id(q, name, shot)
    pics = [p for g in gs for p in g.get("previews", [])]
    if len(pics) > 3:
        pics = [pics[len(pics) // 2], pics[0], pics[-1]]
    thumbs = []
    (THUMBS / sid).mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pics):
        src = studio / "groups" / p
        if src.exists():
            dst = THUMBS / sid / f"{i}{src.suffix.lower()}"
            shutil.copyfile(src, dst)  # a copy of a small preview, never the photo
            thumbs.append(dst.relative_to(HOME).as_posix())
    entry = {"id": sid, "name": name, "shot": shot, "due": due, "count": s.get("photos"),
             "folder": str(root / s["folder"]) if s.get("folder") else None,
             "studio": str(studio), "shoot": shoot_id, "thumbs": thumbs, "status": "waiting",
             "added": datetime.now().isoformat(timespec="seconds")}
    note_pick(q, how)
    place(q, entry)
    return entry, True


def add_manual(q, name, when, shot=None, folder=None):
    due, how = due_date(when)
    shot = date.fromisoformat(shot).isoformat() if shot else None
    entry = {"id": new_id(q, name, shot), "name": " ".join(name.split()), "shot": shot, "due": due, "count": None,
             "folder": folder, "studio": None, "shoot": None, "thumbs": [], "status": "waiting",
             "added": datetime.now().isoformat(timespec="seconds")}
    note_pick(q, how)
    place(q, entry)
    return entry


# ---------- words ----------

def nice_day(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%a %b ") + str(d.day)


def due_words(iso):
    if not iso:
        return "no due date"
    n = (date.fromisoformat(iso) - today()).days
    if n < 0:
        return f"{-n} day{'s' if n != -1 else ''} late"
    if n == 0:
        return "due today"
    if n == 1:
        return "due tomorrow"
    if n <= 7:
        return f"due in {n} days"
    return "due " + nice_day(iso)


def heads_up(q):
    """Waiting shoots that are late or due within three days."""
    out = []
    for s in waiting(q):
        if not s.get("due"):
            continue
        n = (date.fromisoformat(s["due"]) - today()).days
        if n <= HEADS_UP_DAYS:
            out.append((n, s))
    return sorted(out, key=lambda t: t[0])


def options(q):
    order = sorted(DUE_CHOICES, key=lambda k: (-q["picks"].get(k, 0), k))
    return [DUE_CHOICES[k][0] for k in order]


# ---------- the page ----------

FONTS = ("https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600"
         "&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&display=swap")

CSS = r"""
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--coral:#F07F5A;--coral-2:#D4643F;--coral-l:#FCE6DD;
--ocean:#5EB5A9;--ocean-l:#DCEFEA;--sun:#F2CF72;--sun-l:#FBF2D6;--sand-l:#ECEAF6;--lime:#CDE9D6;--line:rgba(31,36,48,.12);
--shadow:0 30px 60px -30px rgba(31,36,48,.35);--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue',Arial,sans-serif;
--r:26px;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans);letter-spacing:-.01em}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2)}
.head{padding:clamp(2rem,5vw,3.6rem) 0 1.2rem;display:grid;gap:.7rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(34px,5vw,58px)/1.03 var(--sans);letter-spacing:-.035em;text-wrap:balance}
h1 em{font:italic 400 1.1em/1 var(--display);text-decoration:underline wavy var(--coral);text-decoration-thickness:.06em;text-underline-offset:.12em;letter-spacing:0}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:38em}
.talk{margin-top:.6rem;display:flex;flex-wrap:wrap;gap:.3rem .7rem;align-items:baseline;background:var(--sun-l);border-radius:22px;padding:.65rem 1.1rem;font-size:14px;color:var(--ink-2);width:fit-content;max-width:100%}
.talk i{font:italic 400 16px/1.3 var(--display);color:var(--ink)}
.list{display:grid;gap:1rem;padding:1rem 0 2rem;margin:0;list-style:none}
.card{position:relative;display:grid;grid-template-columns:auto 168px 1fr auto;gap:clamp(.8rem,2vw,1.4rem);align-items:center;background:var(--paper);border-radius:var(--r);padding:1rem 1.2rem 1rem .6rem;box-shadow:0 1px 0 var(--line);transition:transform .45s var(--ease),box-shadow .45s var(--ease),opacity .6s var(--ease),filter .6s var(--ease);user-select:none}
.card:hover{box-shadow:var(--shadow);transform:translateY(-2px)}
.card.dragging{opacity:.45;transform:scale(.98)}
.card.over-top{box-shadow:inset 0 4px 0 var(--coral)}.card.over-bottom{box-shadow:inset 0 -4px 0 var(--coral)}
.grip{cursor:grab;color:#B7BBC4;font-size:20px;line-height:1;padding:.6rem .2rem;letter-spacing:-2px}
.grip:active{cursor:grabbing}
.pics{position:relative;height:104px}
.pics span{position:absolute;top:8px;width:84px;height:88px;border-radius:14px;overflow:hidden;background:var(--sand-l);border:3px solid var(--paper);box-shadow:0 10px 20px -12px rgba(31,36,48,.45);transition:transform .5s var(--ease)}
.pics span:nth-child(1){left:0;transform:rotate(-5deg);z-index:1}
.pics span:nth-child(2){left:42px;transform:rotate(2deg);z-index:2;top:0;width:90px;height:100px}
.pics span:nth-child(3){left:86px;transform:rotate(6deg);z-index:1}
.card:hover .pics span:nth-child(1){transform:rotate(-8deg) translateX(-6px)}.card:hover .pics span:nth-child(3){transform:rotate(9deg) translateX(6px)}
.pics img{width:100%;height:100%;object-fit:cover;display:block}
.pics .none{display:grid;place-items:center;font:italic 400 15px/1.2 var(--display);color:var(--ink-2);background:var(--sand-l);border-radius:14px;height:96px;width:150px}
.info{display:grid;gap:.35rem;min-width:0}
.name{font:600 clamp(19px,2vw,23px)/1.15 var(--sans);letter-spacing:-.02em;overflow-wrap:anywhere}
.meta{display:flex;flex-wrap:wrap;gap:.35rem .7rem;align-items:center;font-size:13.5px;color:var(--ink-2)}
.tag{display:inline-flex;align-items:center;gap:.35rem;padding:.32rem .7rem;border-radius:999px;font:600 12.5px/1 var(--sans);background:var(--sand-l);color:var(--ink)}
.tag.soon{background:var(--sun-l)}.tag.near{background:var(--coral-l);color:var(--coral-2)}.tag.today{background:var(--coral);color:#fff}.tag.late{background:#C8442A;color:#fff}
.n{font:italic 400 30px/1 var(--display);color:#C9CCD3;min-width:1.6em;text-align:right}
.check{display:grid;place-items:center;width:46px;height:46px;border-radius:50%;border:2px solid var(--line);background:var(--paper);cursor:pointer;transition:background .3s var(--ease),border-color .3s var(--ease),transform .3s var(--ease)}
.check:hover{border-color:var(--ocean);transform:scale(1.06)}
.check svg{width:22px;height:22px;stroke:#fff;stroke-width:3;fill:none;opacity:0;transition:opacity .2s}
.card.done{filter:grayscale(1);opacity:.55}.card.done .check{background:var(--ocean);border-color:var(--ocean)}.card.done .check svg{opacity:1}
.card.done .name{text-decoration:line-through;text-decoration-color:var(--ink-2)}
.card.leaving{opacity:0;transform:translateY(12px) scale(.97)}
.right{display:flex;align-items:center;gap:.9rem}
.ask{grid-column:2/-1;display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;padding:.8rem 1rem;margin-top:.2rem;background:var(--sun-l);border-radius:16px;font-size:14px;animation:pop .45s var(--ease)}
.ask b{font-weight:600;margin-right:.3rem}
.ask button{font:600 13px/1 var(--sans);padding:.55rem .9rem;border-radius:999px;border:1.5px solid var(--ink);background:var(--paper);color:var(--ink);cursor:pointer;transition:background .2s,color .2s}
.ask button:hover{background:var(--ink);color:#fff}
.ask label{display:inline-flex;align-items:center;gap:.45rem;font:600 13px/1 var(--sans);color:var(--ink-2)}
.ask button.keep{border-color:transparent;background:transparent;text-decoration:underline;text-underline-offset:3px}
.ask input[type=date]{font:500 14px var(--sans);border:1.5px solid var(--ink);border-radius:999px;padding:.45rem .8rem;background:var(--paper);color:var(--ink)}
.ask .when{display:inline-flex;gap:.5rem;align-items:center}.ask .when[hidden]{display:none}
.ask .go{background:var(--coral);border-color:var(--coral);color:#fff}.ask .go:hover{background:var(--coral-2);border-color:var(--coral-2)}
.ask .go:disabled{opacity:.4;cursor:default;background:var(--coral);color:#fff}
@keyframes pop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
.empty{background:var(--paper);border-radius:var(--r);padding:2.4rem;text-align:center;display:grid;gap:.4rem}
.empty b{font:italic 400 30px/1.1 var(--display)}.empty span{color:var(--ink-2)}
details.fin{margin:0 0 3rem;border-top:1px solid var(--line);padding-top:1rem}
details.fin summary{cursor:pointer;font:600 14px/1 var(--sans);color:var(--ink-2);list-style:none;display:flex;gap:.5rem;align-items:center}
details.fin summary::before{content:"\25B8";transition:transform .3s}details.fin[open] summary::before{transform:rotate(90deg)}
.finlist{list-style:none;margin:.9rem 0 0;padding:0;display:grid;gap:.4rem}
.finlist li{display:flex;gap:.8rem;align-items:baseline;color:var(--ink-2);font-size:14.5px}
.finlist li s{color:var(--ink)}.finlist button{margin-left:auto;font:600 12.5px var(--sans);background:none;border:0;color:var(--coral-2);cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#fff;padding:.7rem 1.2rem;border-radius:999px;font:500 14px var(--sans);opacity:0;transition:opacity .3s,transform .3s;pointer-events:none}
.toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
.offline{background:var(--coral-l);color:var(--coral-2);border-radius:14px;padding:.7rem 1rem;font-size:14px;margin-top:.4rem}
@media (max-width:720px){.card{grid-template-columns:auto 1fr auto;padding:.9rem}.pics{grid-column:2/3;height:96px}.info{grid-column:2/3}.right{grid-row:1/3;grid-column:3}.n{display:none}.ask{grid-column:1/-1}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

SCRIPT = r"""
const LIVE = location.protocol.startsWith('http');
let Q = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);
const TODAY = new Date(Q.today + 'T12:00:00');
function days(iso){return Math.round((new Date(iso + 'T12:00:00') - TODAY) / 864e5)}
function nice(iso){const d = new Date(iso + 'T12:00:00');return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'})}
function dueTag(iso){
  if(!iso) return '<span class="tag">No due date</span>';
  const n = days(iso);
  if(n < 0) return `<span class="tag late">${-n} day${n==-1?'':'s'} late</span>`;
  if(n == 0) return '<span class="tag today">Due today</span>';
  if(n <= 3) return `<span class="tag near">Due in ${n} day${n==1?'':'s'}</span>`;
  if(n <= 7) return `<span class="tag soon">Due in ${n} days</span>`;
  return `<span class="tag">Due ${nice(iso)}</span>`;
}
function esc(s){return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function toast(t){const el = $('#toast');el.textContent = t;el.classList.add('on');clearTimeout(el._t);el._t = setTimeout(() => el.classList.remove('on'), 2200)}
async function send(body){
  if(!LIVE){toast('Open the queue through Claude to save changes');return false}
  try{const r = await fetch('/queue', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      if(!r.ok) throw 0; Q = await r.json(); return true}
  catch(e){toast('That did not save. Try again.');return false}
}
function render(){
  const w = Q.waiting, list = $('#list');
  $('#count').innerHTML = w.length ? `${w.length} shoot${w.length==1?'':'s'} to edit` : 'All caught up';
  $('#next').innerHTML = w.length ? `Next up: <em>${esc(w[0].name)}</em>, ${esc(dueWords(w[0].due))}.` : '';
  list.innerHTML = w.length ? '' : '<li class="empty"><b>Nothing waiting.</b><span>New shoots land here when you add them after a backup.</span></li>';
  w.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'card'; li.dataset.id = s.id; li.draggable = true;
    const pics = s.thumbs.length ? s.thumbs.map(t => `<span><img src="${esc(t)}" alt=""></span>`).join('') : '<div class="none">no previews</div>';
    li.innerHTML = `<span class="grip" title="Drag to reorder">&#8942;&#8942;</span>
      <div class="pics">${pics}</div>
      <div class="info"><div class="name">${esc(s.name)}</div>
        <div class="meta">${dueTag(s.due)}${s.shot ? `<span>Shot ${nice(s.shot)}</span>` : ''}${s.count ? `<span>${s.count.toLocaleString()} photos</span>` : ''}</div></div>
      <div class="right"><span class="n">${String(i + 1).padStart(2, '0')}</span>
        <button class="check" title="Mark finished" aria-label="Mark ${esc(s.name)} finished"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></button></div>`;
    li.querySelector('.check').onclick = () => finish(li, s);
    list.appendChild(li);
  });
  const f = Q.finished;
  $('#fin').hidden = !f.length;
  $('#fincount').textContent = `Finished (${f.length})`;
  $('#finlist').innerHTML = f.slice(0, 20).map(s => `<li><s>${esc(s.name)}</s><span>${s.finished_at ? 'finished ' + nice(s.finished_at.slice(0,10)) : ''}</span><button data-id="${esc(s.id)}">Undo</button></li>`).join('');
  $('#finlist').querySelectorAll('button').forEach(b => b.onclick = async () => {if(await send({action:'undo', id:b.dataset.id})){render();toast('Back in the queue')}});
}
function dueWords(iso){if(!iso) return 'no due date';const n = days(iso);if(n<0) return `${-n} day${n==-1?'':'s'} late`;if(n==0) return 'due today';if(n==1) return 'due tomorrow';if(n<=7) return `due in ${n} days`;return 'due ' + nice(iso)}
async function finish(li, s){
  li.classList.add('done');
  if(!(await send({action:'done', id:s.id}))){li.classList.remove('done');return}
  toast(`${s.name}: finished`);
  setTimeout(() => {li.classList.add('leaving'); setTimeout(render, 600)}, 1400);
}
// drag to reorder
let dragId = null;
document.addEventListener('dragstart', e => {const c = e.target.closest('.card');if(!c) return;dragId = c.dataset.id;c.classList.add('dragging');e.dataTransfer.effectAllowed = 'move'});
document.addEventListener('dragend', e => {document.querySelectorAll('.card').forEach(c => c.classList.remove('dragging','over-top','over-bottom'))});
document.addEventListener('dragover', e => {const c = e.target.closest('.card');if(!c || c.dataset.id == dragId) return;e.preventDefault();
  const r = c.getBoundingClientRect(), top = e.clientY < r.top + r.height / 2;
  document.querySelectorAll('.card').forEach(x => x.classList.remove('over-top','over-bottom'));c.classList.add(top ? 'over-top' : 'over-bottom')});
document.addEventListener('drop', async e => {
  const c = e.target.closest('.card');if(!c || !dragId || c.dataset.id == dragId) return;e.preventDefault();
  const ids = Q.waiting.map(s => s.id), from = ids.indexOf(dragId);
  const r = c.getBoundingClientRect(), top = e.clientY < r.top + r.height / 2;
  ids.splice(from, 1);
  let to = ids.indexOf(c.dataset.id) + (top ? 0 : 1);
  ids.splice(to, 0, dragId);
  const moved = Q.waiting.find(s => s.id == dragId);
  const before = Q.waiting.slice(0, from).map(s => s.id);
  // moved up past a shoot that is due sooner? offer a new due date
  const passed = Q.waiting.filter(s => ids.indexOf(s.id) > ids.indexOf(dragId) && before.includes(s.id));
  const sooner = moved.due && passed.some(s => s.due && s.due < moved.due);
  if(await send({action:'order', ids})){render(); if(sooner) askDue(dragId)}
  dragId = null;
});
function askDue(id){
  const s = Q.waiting.find(x => x.id == id);const li = document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);if(!s || !li) return;
  const box = document.createElement('div');box.className = 'ask';
  box.innerHTML = `<b>Moved up. New due date?</b>
    <button class="keep" data-v="keep">Keep ${esc(nice(s.due))}</button>
    <button class="pick">Pick a date</button>
    <span class="when" hidden><input type="date" min="${Q.today}" value="${esc(s.due)}"><button class="go" disabled>Change date</button></span>`;
  li.appendChild(box);
  const when = box.querySelector('.when'), input = box.querySelector('input'), go = box.querySelector('.go');
  box.querySelector('.keep').onclick = () => box.remove();
  box.querySelector('.pick').onclick = ev => {
    ev.target.hidden = true; when.hidden = false; input.focus();
    try{ input.showPicker() }catch(e){}   // opens the calendar where the browser allows it
  };
  input.oninput = () => { go.disabled = !input.value || input.value == s.due };
  go.onclick = async () => { if(input.value && await send({action:'due', id, due:input.value})){render();toast('Due date changed to ' + nice(input.value))} };
}
if(!LIVE) $('#offline').hidden = false;
render();
"""


def state(q):
    def pub(s):
        return {k: s.get(k) for k in ("id", "name", "shot", "due", "count", "thumbs", "finished_at")}
    return {"today": today().isoformat(), "waiting": [pub(s) for s in waiting(q)], "finished": [pub(s) for s in finished(q)]}


def page_html(q):
    data = json.dumps(state(q)).replace("</", "<\\/")
    when = today().strftime("%A, %B ") + str(today().day)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Editing queue · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body>"
            "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>"
            f"<span class='when'>{html.escape(when)}</span></div>"
            "<header class='head'><span class='eyebrow'>Editing queue</span><h1 id='count'></h1><p class='lede' id='next'></p>"
            "<span class='talk'>Or just tell me: <i>“move the Garcias to the top”</i> <i>“the beach shoot is done”</i></span>"
            "<p class='offline' id='offline' hidden>This is a saved copy. Ask Claude to “pull up my queue” to check things off and reorder.</p></header>"
            "<ol class='list' id='list'></ol>"
            "<details class='fin' id='fin' hidden><summary id='fincount'></summary><ul class='finlist' id='finlist'></ul></details></div>"
            "<div class='toast' id='toast'></div>"
            f"<script type='application/json' id='data'>{data}</script><script>{SCRIPT}</script></body></html>")


def write_page(q):
    HOME.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page_html(q))
    return PAGE


# ---------- the live page ----------

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urlsplit(self.path).path
        if p in ("/", "/queue.html"):
            body = page_html(load()).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if p.startswith("/queue-thumbs/") and ".." not in p:
            return super().do_GET()
        self.send_error(HTTPStatus.NOT_FOUND)  # nothing else in ~/.studio is served

    def do_POST(self):
        if urlsplit(self.path).path != "/queue":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            q = load()
            act = body.get("action")
            if act in ("done", "undo", "due"):
                s = next(x for x in q["shoots"] if x["id"] == body.get("id"))
                if act == "done":
                    s["status"], s["finished_at"] = "finished", datetime.now().isoformat(timespec="seconds")
                    s["finished_by"] = "page"
                elif act == "undo":
                    s["status"] = "waiting"
                    s.pop("finished_at", None)
                    s.pop("finished_by", None)
                else:
                    s["due"], how = due_date(body.get("due"))
                    s.pop("reminded", None)
            elif act == "order":
                reorder(q, [str(i) for i in body.get("ids", [])])
            else:
                raise ValueError(act)
            save(q)
            write_page(q)
        except (StopIteration, ValueError, SystemExit, TypeError) as e:
            self.send_error(HTTPStatus.BAD_REQUEST, str(e)[:200])
            return
        out = json.dumps(state(q)).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, fmt, *args):
        pass


def serve(port):
    HOME.mkdir(parents=True, exist_ok=True)
    for p in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), partial(Handler, directory=str(HOME)))
            break
        except OSError:
            continue
    else:
        sys.exit(f"STOP: no free port between {port} and {port + 19}.")
    url = f"http://127.0.0.1:{p}/queue.html"
    (HOME / "queue-url.txt").write_text(url)
    print(f"Editing queue: {url}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------- commands ----------

def show(q, all_=False):
    w = waiting(q)
    if not w:
        say("Nothing waiting in the editing queue.")
    for i, s in enumerate(w, 1):
        extra = f", {s['count']:,} photos" if s.get("count") else ""
        say(f"{i}. {s['name']}: {due_words(s.get('due'))}{extra}")
    if all_:
        for s in finished(q):
            say(f"   finished: {s['name']} ({(s.get('finished_at') or '')[:10]})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add"); a1.add_argument("--night", required=True); a1.add_argument("--shoot", required=True)
    a1.add_argument("--due", required=True); a1.add_argument("--name")
    a2 = sub.add_parser("add-manual"); a2.add_argument("--name", required=True); a2.add_argument("--due", required=True)
    a2.add_argument("--shot"); a2.add_argument("--folder")
    l = sub.add_parser("list"); l.add_argument("--all", action="store_true")
    for c in ("done", "undo"):
        x = sub.add_parser(c); x.add_argument("which")
    d = sub.add_parser("due"); d.add_argument("which"); d.add_argument("when")
    m = sub.add_parser("move"); m.add_argument("which"); m.add_argument("--to", type=int, required=True)
    sub.add_parser("options")
    r = sub.add_parser("reminders"); r.add_argument("--mark", action="store_true", help="only ones not yet sent today, and remember them")
    sub.add_parser("page")
    st = sub.add_parser("setup"); g = st.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true"); g.add_argument("--off", action="store_true")
    sub.add_parser("status")
    o = sub.add_parser("offers"); o.add_argument("--mark", action="store_true", help="remember they were offered")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8770)
    a = ap.parse_args()

    if a.cmd == "serve":
        write_page(load())
        return serve(a.port)
    q = load()
    if a.cmd == "add":
        entry, new = add_from_night(q, a.night, a.shoot, a.due, a.name)
        save(q)
        write_page(q)
        say(f"{'Added' if new else 'Updated'}: {entry['name']}, {due_words(entry['due'])}.")
    elif a.cmd == "add-manual":
        entry = add_manual(q, a.name, a.due, a.shot, a.folder)
        save(q)
        write_page(q)
        say(f"Added: {entry['name']}, {due_words(entry['due'])}.")
    elif a.cmd == "list":
        show(q, a.all)
    elif a.cmd in ("done", "undo"):
        s = find(q, a.which)
        if a.cmd == "done":
            if s.get("status") == "finished":
                say(f"{s['name']} was already finished.")
                return
            s["status"], s["finished_at"], s["finished_by"] = "finished", datetime.now().isoformat(timespec="seconds"), "claude"
        else:
            s["status"] = "waiting"
            s.pop("finished_at", None)
            s.pop("finished_by", None)
        save(q)
        write_page(q)
        say(f"{'Finished' if a.cmd == 'done' else 'Back in the queue'}: {s['name']}.")
        if a.cmd == "done" and s.get("studio"):
            say(f"night: {Path(s['studio'])}  shoot: {s['shoot']}")  # for the next step (finding the exports)
    elif a.cmd == "due":
        s = find(q, a.which, include_finished=False)
        s["due"], how = due_date(a.when)
        s.pop("reminded", None)
        save(q)
        write_page(q)
        say(f"{s['name']}: now {due_words(s['due'])}.")
    elif a.cmd == "move":
        s = find(q, a.which, include_finished=False)
        ids = [x["id"] for x in waiting(q) if x["id"] != s["id"]]
        ids.insert(max(0, min(len(ids), a.to - 1)), s["id"])
        reorder(q, ids)
        save(q)
        write_page(q)
        show(q)
    elif a.cmd == "options":
        say(json.dumps(options(q)))
    elif a.cmd == "reminders":
        hits = heads_up(q)
        if a.mark:
            stamp = today().isoformat()
            hits = [(n, s) for n, s in hits if s.get("reminded") != stamp]
            for _, s in hits:
                s["reminded"] = stamp
            if hits:
                save(q)
        for n, s in hits:
            say(f"{s['name']} is {due_words(s['due'])}.")
    elif a.cmd == "page":
        say(str(write_page(q)))
    elif a.cmd == "setup":
        q["enabled"] = bool(a.on)
        save(q)
        say("The editing queue is on." if a.on else "No editing queue. Ask any time to turn it on.")
    elif a.cmd == "status":
        say("on" if q.get("enabled") else ("off" if "enabled" in q else "never asked"))
    elif a.cmd == "offers":
        hits = [s for s in finished(q) if s.get("finished_by") == "page" and not s.get("offered")]
        for s in hits:
            say(f"{s['name']}" + (f"  (night: {s['studio']}  shoot: {s['shoot']})" if s.get("studio") else ""))
            if a.mark:
                s["offered"] = datetime.now().isoformat(timespec="seconds")
        if a.mark and hits:
            save(q)


if __name__ == "__main__":
    main()
