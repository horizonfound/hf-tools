#!/usr/bin/env python3
"""The Studio's home page: the first thing a photographer sees, in the Claude app's browser pane.

A visual menu of everything the Studio does (Dustin, Oct 30), so they can see what's available
and explore on their own, plus what matters today and their recent shoots. Served live by the
posting server at /home (posting_queue.py serve), which also opens folders and pages for its
buttons and records which button they pressed.

A click in the pane cannot type into the chat for them, so a button that needs a conversation
(Back up a card, Make posts from a shoot) shows a small card saying what to do and "Tell Claude: go".
The click is kept in ~/.studio/journey.json, so whatever they say next, Claude already knows what
they pressed, whether it is their first time there, and what they did last time in that category:
first time, a short explanation and "want to dive in?"; later, pick up where they left off.

    python3 home.py page            write ~/.studio/home.html (a saved copy; the live page is /home)
    python3 home.py url             the live page's address (starts the posting server if needed)
    python3 home.py pending         clicks Claude hasn't answered yet, with that category's history (JSON)
    python3 home.py seen            mark them answered
    python3 home.py did <category> [--note "..."]   remember something done in a category
    python3 home.py journey         the whole record

Categories: backup, posts, queue, posting, reel, folder.
"""
import argparse
import html
import json
import os
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JOURNEY = HOME / "journey.json"
PAGE = HOME / "home.html"
CATEGORIES = ("backup", "posts", "queue", "posting", "reel", "folder")


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass


def now():
    return datetime.now().isoformat(timespec="seconds")


# ---------- the journey: what they've pressed and done ----------

def load_journey():
    if JOURNEY.exists():
        try:
            return json.loads(JOURNEY.read_text())
        except ValueError:
            pass
    return {"clicks": [], "done": {}}


def save_journey(j):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = JOURNEY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(j, indent=1, ensure_ascii=False))
    tmp.replace(JOURNEY)


def record_click(item):
    if item not in CATEGORIES:
        return False
    j = load_journey()
    j["clicks"].append({"at": now(), "item": item, "seen": False})
    j["clicks"] = j["clicks"][-50:]
    save_journey(j)
    return True


def record_done(category, note=None):
    j = load_journey()
    d = j["done"].setdefault(category, {"first": None, "count": 0})
    d["first"] = d["first"] or now()
    d["last"] = now()
    d["count"] += 1
    if note:
        d["note"] = note
    save_journey(j)
    return d


def pending():
    """Unanswered clicks, newest last, each with what they've done in that category before."""
    j = load_journey()
    out = []
    for c in j["clicks"]:
        if c.get("seen"):
            continue
        d = j["done"].get(c["item"]) or {}
        out.append({"item": c["item"], "at": c["at"], "first_time": not d.get("count"),
                    "times_before": d.get("count", 0), "last_done": d.get("last"), "last_note": d.get("note")})
    return out


def mark_seen():
    j = load_journey()
    for c in j["clicks"]:
        c["seen"] = True
    save_journey(j)


# ---------- what matters today ----------

def card_in():
    """A memory card mounted right now: a volume with a DCIM folder. Name and rough count, or None."""
    vols = Path("/Volumes")
    if not vols.is_dir():
        return None
    for v in vols.iterdir():
        if (v / "DCIM").is_dir():
            n = 0
            for root, _, files in os.walk(v / "DCIM"):
                n += len([f for f in files if not f.startswith(".")])
                if n > 20000:
                    break
            return {"name": v.name, "files": n}
    return None


def gather():
    """Everything the page shows, read from what the Studio already keeps. Each part fails soft."""
    g = {"today": date.today().strftime("%A, %B ") + str(date.today().day), "notes": [], "due": [], "tank": None,
         "card": None, "recent": [], "kits": [], "home_folder": None, "setup": False, "done": load_journey()["done"]}
    try:
        import studio_file
        g["setup"] = bool(studio_file.load().get("drives", {}).get("session"))
    except Exception:
        pass
    try:
        import edit_queue
        q = edit_queue.load()
        for n, s in edit_queue.heads_up(q):
            g["notes"].append(("late" if n < 0 else "soon", f"{s['name']}: {edit_queue.due_words(s.get('due'))}"))
        for s in edit_queue.waiting(q)[:4]:
            g["due"].append({"name": s["name"], "due": edit_queue.due_words(s.get("due")), "late": bool(s.get("due")) and s["due"] < date.today().isoformat()})
        shoots = sorted(q["shoots"], key=lambda s: (s.get("shot") or "", s.get("added", "")), reverse=True)
        for s in shoots[:6]:
            g["recent"].append({"id": s["id"], "name": s["name"], "shot": s.get("shot"), "count": s.get("count"),
                                "thumbs": [t for t in (s.get("thumbs") or [])[:3] if (HOME / t).exists()], "status": s.get("status")})
    except Exception:
        pass
    try:
        import posting_queue
        p = posting_queue.load()
        g["tank"] = posting_queue.tank_words(p)
        for r in posting_queue.reminders(p):
            g["notes"].append(("post", r if isinstance(r, str) else r.get("words", "")))
    except Exception:
        pass
    try:
        import posts
        h = posts.home()
        if h:
            g["home_folder"] = str(h)
            g["kits"] = [k for k in posts.kits(h) if k.get("kit")][:6]
    except Exception:
        pass
    try:
        g["card"] = card_in()
    except Exception:
        pass
    return g


# ---------- the page ----------

# The two buttons that start a conversation: what to paste in the chat, and the steps before it.
SAY = {"backup": "backup now", "posts": "I dropped something in"}

MENU = [
    ("backup", "Back up a card",
     "Copies your memory card to your hard drive and double-checks every photo. Then it sorts the photos into shoots, names them, and picks a few to edit first.",
     ["Put your memory card in.", "Paste this in the chat:"], "Nothing on your memory card is changed."),
    ("posts", "Make posts from a shoot",
     "Turns a folder of finished photos into Instagram posts: a reel, a carousel, single photos, stories, and captions written the way you write.",
     ["Drag a folder of your finished photos into the folder called <b>Drop a shoot here</b>. <button class='btn open-inline' data-open='/open-drop'>Open the folder</button>", "Paste this in the chat:"],
     "Nothing is posted. You post it when you're ready."),
    ("queue", "My editing queue", "The shoots you still need to edit, and when each one is due.", None, None),
    ("posting", "My posting queue", "Your reels and posts that are ready, and what your Instagram grid will look like with them in it.", None, None),
    ("folder", "Open my Studio folder", "The folder on your hard drive where your posts are kept.", None, None),
]

CSS_EXTRA = r"""
.menu{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;padding:1rem 0 .4rem}
.item{position:relative;display:grid;gap:.5rem;align-content:start;text-align:left;padding:22px 22px 20px;border:0;border-radius:var(--r);background:var(--paper);box-shadow:0 1px 0 var(--line);cursor:pointer;font:inherit;color:inherit;transition:transform .35s var(--ease),box-shadow .35s var(--ease)}
.item:hover{transform:translateY(-3px);box-shadow:var(--shadow)}
.item .n{font:600 20px/1.15 var(--sans);letter-spacing:-.02em}.item .n em{font:italic 400 1.05em/1 var(--display);color:var(--coral-2)}
.item p{margin:0;color:var(--ink-2);font-size:14.5px}
.item.open{box-shadow:inset 0 0 0 2px var(--ink),var(--shadow)}.item.open .n em{color:var(--coral-2)}
.howto{grid-column:1/-1;display:none;gap:.5rem;padding:22px 26px;border-radius:18px;background:var(--ink);color:#F4F1EA;box-shadow:var(--shadow)}
.howto ol li::marker{color:var(--coral);font-weight:600}.howto b{color:#fff}
.howto .open-inline{background:transparent;color:#F4F1EA;border-color:rgba(255,255,255,.35)}.howto .open-inline:hover{border-color:#fff}
.howto .note{color:rgba(244,241,234,.7)}.howto small{color:rgba(244,241,234,.6)}
.howto .paste .words{background:#2A3040;color:#fff;border-color:rgba(255,255,255,.12)}
.howto .paste .copy{background:var(--coral);color:#1F2430}.howto .paste .copy:hover{background:#F79672}
.howto.show{display:grid}.howto ol{margin:0;padding-left:1.2em;font-size:15.5px;display:grid;gap:.3rem}.howto ol li{padding-left:.2em}.howto .open-inline{margin-left:8px;vertical-align:middle;background:transparent;color:#F4F1EA;border-color:rgba(255,255,255,.4)}
.paste{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:.2rem 0 .1rem}.paste .words{font:500 17px/1 var(--sans);background:var(--cream);padding:11px 14px;border-radius:12px;border:1.5px solid var(--line)}
.paste .copy{font:600 13px/1 var(--sans);padding:11px 16px;border-radius:999px;border:0;background:var(--ink);color:#fff;cursor:pointer}
.howto small{color:var(--ink-2);font-size:13px}
.todayl{display:grid;gap:.5rem;margin:.6rem 0 0;padding:0;list-style:none}
.todayl li{display:flex;gap:.6rem;align-items:baseline;font-size:15px}.todayl li::before{content:'';width:8px;height:8px;border-radius:50%;background:var(--ocean);flex:none;transform:translateY(-1px)}
.todayl li.late::before{background:var(--red)}.todayl li.soon::before{background:var(--yellow)}.todayl li.card::before{background:var(--coral)}
.recent{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;padding:.8rem 0 2rem}
.shoot{display:grid;gap:.5rem;padding:12px;border-radius:18px;background:var(--paper);box-shadow:0 1px 0 var(--line)}
.shoot .ph{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}.shoot .ph img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;background:var(--sand-l);display:block}
.shoot .ph i{display:block;aspect-ratio:1;border-radius:8px;background:var(--sand-l)}
.shoot b{font:600 15px/1.2 var(--sans)}.shoot small{color:var(--ink-2);font-size:12.5px}
.shoot .acts{display:flex;gap:6px;flex-wrap:wrap}
.btn{font:600 12.5px/1 var(--sans);padding:8px 11px;border-radius:999px;border:1.5px solid var(--line);background:transparent;color:var(--ink);cursor:pointer;text-decoration:none}
.btn:hover{border-color:var(--ink)}.btn.solid{background:var(--ink);color:#fff;border-color:var(--ink)}
.said{font-size:13px;color:var(--ink-2);min-height:1.2em;margin:0}.note{display:block;font-size:13px;color:var(--ink-2);margin-top:6px}.howto .note{display:inline;margin-left:8px}
.empty{padding:1rem 0 2rem;color:var(--ink-2);font-size:15px}
"""

SCRIPT = r"""
const live=location.protocol.startsWith('http');
const $=s=>document.querySelector(s);
function say(t){const e=$('#said');e.textContent=t||'';}
// The Claude app's browser pane refuses navigator.clipboard.writeText (tested on Dustin's Mac, Oct 30) but honors the
// older execCommand('copy') from a click, so that goes first; the modern call is the fallback for other browsers.
function copyText(t){try{const a=document.createElement('textarea');a.value=t;a.setAttribute('readonly','');a.style.cssText='position:fixed;top:0;left:0;opacity:0';document.body.appendChild(a);a.focus();a.select();const ok=document.execCommand('copy');a.remove();if(ok)return true;}catch(e){}
  if(navigator.clipboard){navigator.clipboard.writeText(t).catch(()=>{});return true;}return false;}
async function clicked(item){if(!live)return;try{await fetch('/clicked',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({item})});}catch(e){}}
function note(b,t){if(!b){say(t);return;}let n=b.nextElementSibling;if(!n||!n.classList.contains('note')){n=document.createElement('span');n.className='note';b.after(n);}n.textContent=t;}
async function openPath(q,b){if(!live){note(b,'Ask Claude to open this.');return;}try{const r=await fetch(q);const d=await r.json();note(b,d.words||'');}catch(e){note(b,'The Studio isn\'t running right now. Ask Claude to open it.');}}
document.querySelectorAll('.item').forEach(b=>{b.addEventListener('click',async()=>{
  const item=b.dataset.item;clicked(item);
  document.querySelectorAll('.item').forEach(x=>x.classList.toggle('open',x===b));
  document.querySelectorAll('.howto').forEach(h=>h.classList.toggle('show',h.dataset.for===item));
  if(item==='queue'){if(!live){say('Ask Claude: show my editing queue');return;}try{const r=await fetch('/queue-url');const d=await r.json();if(d.url){location.href=d.url;}else say(d.words||'Ask Claude: show my editing queue');}catch(e){say('Ask Claude: show my editing queue');}}
  else if(item==='posting'){if(live)location.href='/posting.html';else say('Ask Claude: show my posting queue');}
  else if(item==='folder'){openPath('/open-home',b.querySelector('p'));}
});});
document.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>openPath(b.dataset.open,b)));
document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{if(copyText(b.dataset.copy)){b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1500);}else{b.textContent='Select it and copy';}}));
if(!live){$('#offline').hidden=false;}
"""


def kit_thumbs(k):
    """Three small previews of a kit's photos, in ~/.studio/home-thumbs/, made once."""
    try:
        import kit as kit_mod
        kd = Path(k["path"])
        rec = kit_mod.load_rec(kd)
        photos = kit_mod.photo_files(kit_mod.photos_dir(kd, rec))[:3]
        out = []
        (HOME / "home-thumbs").mkdir(parents=True, exist_ok=True)
        for i, src in enumerate(photos, 1):
            dst = HOME / "home-thumbs" / f"{k['folder']}-{i}.jpg"
            if not dst.exists() and not kit_mod.fit(Path(src), dst, (240, 240)):
                continue
            out.append(dst.relative_to(HOME).as_posix())
        return out
    except Exception:
        return []


def page_html():
    import posting_queue
    g = gather()
    e = html.escape
    done = g["done"]

    # today
    today_items = []
    if g["card"]:
        today_items.append(("card", f"A card is in: {g['card']['name']}, about {g['card']['files']:,} files. Ready when you are."))
    for kind, words in g["notes"][:5]:
        today_items.append((kind, e(words)))
    if g["tank"]:
        today_items.append(("post", e(g["tank"])))
    if not today_items:
        today_items.append(("", "Nothing due and nothing waiting."))
    today_html = "".join(f"<li class='{k}'>{w}</li>" for k, w in today_items)

    # menu
    menu = []
    for key, name, blurb, steps, note in MENU:
        first, rest = name.split(" ", 1)
        menu.append(f"<button class='item' data-item='{key}'><span class='n'>{e(first)} <em>{e(rest)}</em></span><p>{e(blurb)}</p></button>")
        if steps:
            words = SAY[key]
            step_html = "".join(f"<li>{t}</li>" for t in steps)
            menu.append(f"<div class='howto' data-for='{key}'><ol>{step_html}</ol>"
                        f"<div class='paste'><span class='words'>{e(words)}</span><button class='copy' data-copy='{e(words)}'>Copy</button></div>"
                        f"<small>{e(note)}</small></div>")
    menu_html = "".join(menu)

    # recent shoots and kits
    kits_by_name = {k["name"].lower(): k for k in g["kits"]}
    recent = []
    for s in g["recent"]:
        ph = "".join(f"<img src='{e(t)}' alt=''>" for t in s["thumbs"]) + "<i></i>" * (3 - len(s["thumbs"]))
        when = ""
        if s.get("shot"):
            try:
                when = date.fromisoformat(s["shot"][:10]).strftime("%b ") + str(int(s["shot"][8:10]))
            except ValueError:
                when = ""
        meta = " · ".join(x for x in (when, f"{s['count']:,} photos" if s.get("count") else "", {"waiting": "to edit", "finished": "edited", "archived": "just for you"}.get(s.get("status"), "")) if x)
        acts = f"<button class='btn' data-open='/open-shoot?id={e(s['id'])}'>Open photo folder</button>"
        k = kits_by_name.get(s["name"].lower())
        if k:
            acts += f"<a class='btn solid' href='/content/{e(k['folder'])}/Post%20kit.html'>Open the post kit</a>"
        recent.append(f"<div class='shoot'><div class='ph'>{ph}</div><b>{e(s['name'])}</b><small>{e(meta)}</small><div class='acts'>{acts}</div></div>")
    for k in g["kits"]:
        if k["name"].lower() in {s["name"].lower() for s in g["recent"]}:
            continue
        th = "".join(f"<img src='{e(t)}' alt=''>" for t in kit_thumbs(k))
        th += "<i></i>" * (3 - th.count("<img"))
        recent.append(f"<div class='shoot'><div class='ph'>{th}</div><b>{e(k['name'])}</b><small>{k['photos']} photos · post kit</small>"
                      f"<div class='acts'><a class='btn solid' href='/content/{e(k['folder'])}/Post%20kit.html'>Open the post kit</a></div></div>")
    recent_html = "".join(recent[:8]) if recent else ""
    recent_block = (f"<section class='sec'><h2>Your recent shoots</h2></section><div class='recent'>{recent_html}</div>" if recent_html
                    else "<section class='sec'><h2>Your shoots</h2></section><p class='empty'>Nothing here yet. Your shoots show up here after your first backup.</p>")

    head_h1 = "Welcome <em>back.</em>" if g["setup"] else "Welcome to <em>The Studio.</em>"
    lede = "Here's where things stand. Click anything below to see what it does." if g["setup"] else \
        "Click anything below to see what it does. When you're ready, put a memory card in and we'll start there."
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>The Studio</title><link rel='stylesheet' href='{posting_queue.FONTS}'><style>{posting_queue.CSS}{CSS_EXTRA}</style></head><body>"
            "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>"
            f"<span class='when'>{e(g['today'])}</span></div>"
            f"<header class='head'><span class='eyebrow'>Home</span><h1>{head_h1}</h1><p class='lede'>{lede}</p>"
            "<p class='offline' id='offline' hidden>This is a saved copy. Ask Claude to “show the Studio” for the live one.</p></header>"
            f"<section class='sec'><h2>Today</h2><ul class='todayl'>{today_html}</ul></section>"
            f"<section class='sec'><h2>What the Studio does</h2><p>Click one.</p></section><div class='menu'>{menu_html}</div><p class='said' id='said'></p>"
            f"{recent_block}"
            f"</div><script>{SCRIPT}</script></body></html>")


def write_page():
    HOME.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page_html())
    return PAGE


def url():
    """The live home page: on the posting server, started if it isn't running."""
    import urllib.request
    f = HOME / "posting-url.txt"
    def alive(u):
        try:
            urllib.request.urlopen(u, timeout=1).read(1)
            return True
        except Exception:  # noqa: BLE001
            return False
    if f.exists():
        base = f.read_text().strip().rsplit("/", 1)[0]
        if alive(base + "/home"):
            return base + "/home"
    HOME.mkdir(parents=True, exist_ok=True)
    log = open(HOME / "posting-serve.log", "a")
    subprocess.Popen([sys.executable, str(HERE / "posting_queue.py"), "serve"], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        if f.exists():
            base = f.read_text().strip().rsplit("/", 1)[0]
            if alive(base + "/home"):
                return base + "/home"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("page"); sub.add_parser("url"); sub.add_parser("pending"); sub.add_parser("seen"); sub.add_parser("journey")
    d = sub.add_parser("did"); d.add_argument("category", choices=CATEGORIES); d.add_argument("--note")
    c = sub.add_parser("click"); c.add_argument("item", choices=CATEGORIES)
    a = ap.parse_args()
    if a.cmd == "page":
        say(str(write_page()))
    elif a.cmd == "url":
        u = url()
        if not u:
            say("STOP: couldn't start the Studio's page server.")
            return 2
        say(u)
    elif a.cmd == "pending":
        say(json.dumps(pending(), indent=1))
    elif a.cmd == "seen":
        mark_seen(); say("ok")
    elif a.cmd == "did":
        say(json.dumps(record_done(a.category, a.note)))
    elif a.cmd == "click":
        record_click(a.item); say("ok")
    elif a.cmd == "journey":
        say(json.dumps(load_journey(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
