#!/usr/bin/env python3
"""Your shoots: the editing queue on top (the shoots still to edit, with due
dates, soonest due always on top) and, below the
line, every shoot the Studio has backed up, newest first, each with a button
that opens its folder. One page; "show my queue" and "show the archive" both
open it.

It is the bridge between the backup and the reel: a backup's shoots are added
when the photographer says so (some shoots are just for them), "I'm done with
the beach shoot" takes one off and starts the next step, and a heads-up comes
three days before anything is due.

Kept in ~/.studio/queue.json with a few thumbnails per shoot copied to
~/.studio/queue-thumbs/, so the page works even when the drive is unplugged.
Nothing here ever touches a photo.

    python3 edit_queue.py add --night "<the night's folder or records>" --shoot s1 --due 2w
    python3 edit_queue.py add-manual --name "Garcia family" [--due 2026-11-07] [--shot 2026-10-18]
    python3 edit_queue.py add-list --file names.txt      a whole list, in their order, no dates needed
    python3 edit_queue.py add-list --names "Cassandra, Toni, Sarah"   (a name can carry a date: "Toni: 2026-11-07")
    python3 edit_queue.py list                      what's waiting, soonest due first
    python3 edit_queue.py done "beach"              mark finished (a word from the name is enough)
    python3 edit_queue.py undo "beach"
    python3 edit_queue.py due "beach" 1w            a new due date (1w 2w 3w, this-week, or 2026-11-07)
    python3 edit_queue.py move "beach" --to 1       put it first among shoots due the same day
    python3 edit_queue.py options                   the due choices, their most-picked first
    python3 edit_queue.py reminders [--mark]        due in 3 days or late (--mark: for the daily check)
    python3 edit_queue.py page                      write ~/.studio/queue.html
    python3 edit_queue.py setup --on|--off          keep a queue or not (asked once)
    python3 edit_queue.py status                    on, off, or never asked
    python3 edit_queue.py offers [--mark]           shoots ticked off on the page that still need "want a reel?"
    python3 edit_queue.py register --night "<night>"  put every shoot of a night in the archive (night.py does this)
    python3 edit_queue.py scan                      find every night the Studio has done and register it (once, to backfill)
    python3 edit_queue.py open "beach"              open that shoot's folder in Finder
    python3 edit_queue.py serve                     the page, live: check off, drag, change dates, open folders

A shoot is "waiting" (in the queue), "finished" (ticked off the queue) or
"archived" (never queued: a shoot that was just for them). Finished and
archived shoots are the archive.
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


def due_date(when, base=None, _quiet=False):
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
    if _quiet:
        return None, None
    sys.exit(f"STOP: I could not read '{when}' as a due date. Try 1w, 2w, 3w, this-week, or a date like 2026-11-07.")


def is_waiting(s):
    return s.get("status", "waiting") == "waiting"


def waiting(q):
    """The shoots still to edit, soonest due always first (Dustin, Oct 24). Shoots due the same
    day keep the order they were dragged into; shoots with no due date come last."""
    w = [s for s in q["shoots"] if is_waiting(s)]
    if not q.get("manual_order"):
        w.sort(key=lambda s: s.get("added", ""))
    w.sort(key=lambda s: s.get("due") or "9999")  # stable: same-day shoots keep their order
    return w


def archive(q):
    """Every shoot not in the queue, newest shoot first (undated ones last)."""
    rest = [s for s in q["shoots"] if not is_waiting(s)]
    return sorted(rest, key=lambda s: (s.get("shot") or "", s.get("finished_at") or s.get("added") or ""), reverse=True)


def finished(q):
    """Shoots ticked off the queue, most recent first."""
    return sorted((s for s in q["shoots"] if s.get("status") == "finished"), key=lambda s: s.get("finished_at", ""), reverse=True)


def reorder(q, ids):
    """Put the waiting shoots in this order; finished ones keep their place after them."""
    by_id = {s["id"]: s for s in q["shoots"]}
    head = [by_id[i] for i in ids if i in by_id and is_waiting(by_id[i])]
    rest = [s for s in waiting(q) if s not in head]
    q["shoots"] = head + rest + archive(q)
    q["manual_order"] = True


def find(q, text, include_finished=True):
    pool = q["shoots"] if include_finished else waiting(q)
    t = text.strip().lower()
    exact = [s for s in pool if s["id"] == text or s["name"].lower() == t]
    if exact:
        return exact[0]
    hits = [s for s in pool if t in s["name"].lower()]
    if len(hits) > 1:
        live = [s for s in hits if is_waiting(s)]
        hits = live if len(live) == 1 else hits
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"STOP: no shoot matches '{text}'.")
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
    q["shoots"] = w + archive(q)


# ---------- adding ----------

def night_shoots(night):
    """(root, studio, shoots, names, groups) for a night, before or after it settled."""
    from where import locate
    root, studio = locate(night)
    shoots = json.loads((studio / "shoots.json").read_text())["shoots"]
    names = json.loads((studio / "names.json").read_text()) if (studio / "names.json").exists() else {}
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text())["groups"]} if (studio / "groups.json").exists() else {}
    return root, studio, shoots, names, groups


def existing(q, studio, shoot_id):
    return next((x for x in q["shoots"] if x.get("studio") == str(studio) and x.get("shoot") == shoot_id), None)


def build_entry(q, root, studio, s, names, groups, status, due=None):
    name = names.get(s["id"]) or s.get("name") or s.get("suggested") or s["id"]
    gs = [groups[g] for g in s.get("groups", []) if g in groups]
    shot = gs[0]["start"][:10] if gs else None
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
    return {"id": sid, "name": name, "shot": shot, "due": due, "count": s.get("photos"),
            "folder": str(root / s["folder"]) if s.get("folder") else None,
            "studio": str(studio), "shoot": s["id"], "thumbs": thumbs, "status": status,
            "added": datetime.now().isoformat(timespec="seconds")}


def add_from_night(q, night, shoot_id, when, name=None):
    root, studio, shoots, names, groups = night_shoots(night)
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        sys.exit(f"STOP: no shoot {shoot_id} in that backup. Its shoots: " + ", ".join(x["id"] for x in shoots))
    if name:
        names = dict(names, **{shoot_id: name})
    due, how = due_date(when)
    note_pick(q, how)
    x = existing(q, studio, shoot_id)
    if x:  # already known (in the archive, finished, or queued): this puts it in the queue with this due date
        was_waiting = is_waiting(x)
        x["due"], x["name"] = due, names.get(shoot_id) or x["name"]
        x["status"] = "waiting"
        for k in ("finished_at", "finished_by", "offered", "reminded"):
            x.pop(k, None)
        if not was_waiting:
            q["shoots"].remove(x)
            place(q, x)
        return x, False
    entry = build_entry(q, root, studio, s, names, groups, "waiting", due)
    place(q, entry)
    return entry, True


def register_night(q, night):
    """Every shoot of a night goes in the archive (shoots already known are left as they are)."""
    root, studio, shoots, names, groups = night_shoots(night)
    added = 0
    for s in shoots:
        x = existing(q, studio, s["id"])
        if x:
            x["name"] = names.get(s["id"]) or s.get("name") or x["name"]
            x["count"] = s.get("photos") or x.get("count")
            continue
        q["shoots"].append(build_entry(q, root, studio, s, names, groups, "archived"))
        added += 1
    return added


def folder_of(s):
    """Where the shoot's photos are right now: read from its night's records, so renames and settling are followed."""
    if s.get("studio"):
        try:
            from where import locate
            root, studio = locate(s["studio"])
            for x in json.loads((studio / "shoots.json").read_text())["shoots"]:
                if x["id"] == s.get("shoot") and x.get("folder"):
                    return root / x["folder"]
        except (SystemExit, OSError, ValueError, KeyError):
            pass
    return Path(s["folder"]) if s.get("folder") else None


def open_folder(s):
    """(ok, words) after asking Finder to open the shoot's folder."""
    f = folder_of(s)
    if not f:
        return False, "I don't know where that shoot's folder is."
    if not f.is_dir():
        drive = f.parts[2] if len(f.parts) > 2 and f.parts[1] == "Volumes" else None
        return False, (f"Plug in {drive} to open this one." if drive else "That folder isn't where it used to be.")
    from finder import open_folder as show_in_finder
    ok, note = show_in_finder(f)
    if not ok:
        return False, f"Couldn't open Finder; the folder is {f}."
    if note == "behind":
        return True, f"Opened {f.name} in Finder, behind this window. Click Finder in the Dock to see it."
    return True, f"Opened {f.name} in Finder."


def nights_known():
    """Every night's records the Studio can find: from the card ledger, and the hidden .studio folders where shoots settle."""
    out = []
    try:
        import cards
        for entry in cards.load().get("cards", {}).values():
            out += [x["folder"] for x in entry.get("sessions", [])]
    except Exception:  # noqa: BLE001
        pass
    try:
        import studio_file
        place_ = studio_file.load().get("drives", {}).get("session")
        if place_ and Path(place_).is_dir():
            recs = Path(place_) / ".studio"
            if recs.is_dir():
                out += [str(r) for r in recs.iterdir() if (r / "shoots.json").exists()]
            out += [str(d) for d in Path(place_).iterdir() if (d / "_studio" / "shoots.json").exists()]
    except Exception:  # noqa: BLE001
        pass
    seen, uniq = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def add_manual(q, name, when=None, shot=None, folder=None):
    due, how = due_date(when) if when else (None, None)
    shot = date.fromisoformat(shot).isoformat() if shot else None
    entry = {"id": new_id(q, name, shot), "name": " ".join(name.split()), "shot": shot, "due": due, "count": None,
             "folder": folder, "studio": None, "shoot": None, "thumbs": [], "status": "waiting",
             "added": datetime.now().isoformat(timespec="seconds")}
    if how:
        note_pick(q, how)
    place(q, entry)
    return entry


def add_list(q, names):
    """A whole editing list at once (Dustin, Oct 31: a student keeps hers as a checklist in Apple Notes,
    twenty first names in a row). Each line is a name, in their order; a line may end with a date after a
    colon ("Toni: 2026-11-07", or 1w/2w/3w). Undated shoots keep that order below any dated ones (the
    page's rule: soonest due on top). The same name twice makes two shoots; the caller says so."""
    added = []
    for raw in names:
        raw = " ".join(str(raw).split()).strip(" -*\u2022\u25cb\u25cf\u2610\u2611")
        if not raw:
            continue
        name, when = raw, None
        if ":" in raw:
            a, b = raw.rsplit(":", 1)
            if b.strip() and due_date(b.strip(), _quiet=True)[0]:
                name, when = a.strip(), b.strip()
        if not name:
            continue
        seen = [s for s in q["shoots"] if s["name"].lower() == name.lower()]
        entry = add_manual(q, name, when)
        entry["dup_of"] = len(seen)  # how many of this name were already there (reported, not stored for long)
        added.append(entry)
    return added


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
.bar .homelink{margin-left:auto;font:600 13px/1 var(--sans);color:var(--coral-2);text-decoration:none;padding:8px 12px;border-radius:999px;border:1.5px solid var(--coral-l)}.bar .homelink+.when{margin-left:0}
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
.addrow{margin-top:1rem}.addbtn{font:600 14px/1 var(--sans);padding:.65rem 1.1rem;border-radius:999px;border:1.5px solid var(--ink);background:var(--paper);color:var(--ink);cursor:pointer;display:inline-flex;align-items:center;gap:.5rem}.addbtn:hover{background:var(--ink);color:#fff}.addbtn .plus{font-size:18px;line-height:1}
.addform{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;padding:.9rem 1rem;background:var(--sun-l);border-radius:16px;animation:pop .45s var(--ease)}.addform[hidden]{display:none}
.addform input[type=text]{flex:1 1 14em;font:500 15px/1.2 var(--sans);padding:.55rem .8rem;border:1.5px solid var(--sand);border-radius:10px;background:var(--paper)}.addform input[type=date]{font:500 14px/1.2 var(--sans);padding:.5rem .7rem;border:1.5px solid var(--sand);border-radius:10px;background:var(--paper)}
.addform .go{font:600 13px/1 var(--sans);padding:.6rem 1rem;border-radius:999px;border:0;background:var(--coral);color:#fff;cursor:pointer}.addform .go:disabled{opacity:.45;cursor:default}.addform .cancel{font:600 13px/1 var(--sans);padding:.6rem .9rem;border-radius:999px;border:1.5px solid var(--ink);background:transparent;color:var(--ink);cursor:pointer}
.addform .hint{flex-basis:100%;font-size:13px;color:var(--ink-2)}.added{margin:.5rem 0 0;font-size:14px;color:var(--ink-2);min-height:1em}
.setdue{font:600 12.5px/1 var(--sans);padding:.32rem .7rem;border-radius:999px;border:1.5px solid var(--sand);background:transparent;color:var(--ink-2);cursor:pointer}.setdue:hover{border-color:var(--ink);color:var(--ink)}
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
.line{display:flex;align-items:center;gap:1rem;margin:1.6rem 0 0;color:var(--ink-2)}
.line::before,.line::after{content:"";flex:1;height:1px;background:var(--line)}
.line span{font:600 11px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase}
.arch-head{display:flex;flex-wrap:wrap;gap:.8rem 1rem;align-items:center;justify-content:space-between;padding:1.2rem 0 .2rem}
.arch-head .count{font:500 14px/1.4 var(--sans);color:var(--ink-2)}
.search{display:flex;align-items:center;gap:.5rem;background:var(--paper);border:1.5px solid var(--line);border-radius:999px;padding:.45rem .9rem;min-width:min(280px,100%);transition:border-color .2s}
.search:focus-within{border-color:var(--coral)}
.search input{border:0;outline:0;background:transparent;font:500 14px var(--sans);color:var(--ink);width:100%}
.search svg{width:16px;height:16px;stroke:var(--ink-2);fill:none;stroke-width:2;flex:none}
.month{font:italic 400 17px/1 var(--display);color:var(--ink-2);margin:1.4rem 0 .5rem;padding-left:.2rem}
.alist{display:block;margin:0;padding:0 0 3rem;list-style:none}
.acard{display:grid;grid-template-columns:78px 1fr auto;gap:1rem;align-items:center;background:var(--paper);padding:.6rem 1rem .6rem .8rem;border-bottom:1px solid var(--line);transition:background .25s}
.acard:hover{background:#FFFDF8}
.month + .acard{border-top-left-radius:16px;border-top-right-radius:16px}
.acard:has(+ .month),.acard:last-child{border-bottom:0;border-bottom-left-radius:16px;border-bottom-right-radius:16px;margin-bottom:.2rem}
.acard .pics{height:52px}
.acard .pics span{width:40px;height:44px;top:5px;border-width:2px;border-radius:9px;box-shadow:0 6px 12px -8px rgba(31,36,48,.45)}
.acard .pics span:nth-child(1){left:0}.acard .pics span:nth-child(2){left:20px;width:44px;height:50px;top:0}.acard .pics span:nth-child(3){left:38px}
.acard:hover .pics span:nth-child(1){transform:rotate(-7deg) translateX(-3px)}.acard:hover .pics span:nth-child(3){transform:rotate(8deg) translateX(3px)}
.acard .pics .none{height:46px;width:70px;font-size:11px;border-radius:9px}
.acard .info{display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .9rem}
.acard .name{font:600 15.5px/1.3 var(--sans);letter-spacing:-.01em}
.acard .meta{font-size:13px;gap:.2rem .7rem}
.acts{display:flex;align-items:center;gap:1rem}
.open-folder{font:600 13px/1 var(--sans);color:var(--coral-2);background:transparent;border:1.5px solid var(--coral);border-radius:999px;padding:.5rem .85rem;cursor:pointer;white-space:nowrap;transition:background .2s,color .2s}
.open-folder:hover{background:var(--coral);color:#fff}
.requeue{font:500 12.5px var(--sans);background:none;border:0;color:var(--ink-2);cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:0;white-space:nowrap}
.requeue:hover{color:var(--coral-2)}
.tag.edited{background:var(--ocean-l);color:#2F6F6B;padding:.25rem .55rem;font-size:11.5px}
.nomatch{color:var(--ink-2);padding:1rem 0 3rem}
.acard.fresh{animation:pop .6s var(--ease)}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);background:var(--ink);color:#fff;padding:.7rem 1.2rem;border-radius:999px;font:500 14px var(--sans);opacity:0;transition:opacity .3s,transform .3s;pointer-events:none}
.toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
.offline{background:var(--coral-l);color:var(--coral-2);border-radius:14px;padding:.7rem 1rem;font-size:14px;margin-top:.4rem}
@media (max-width:720px){.card{grid-template-columns:auto 1fr auto;padding:.9rem}.card .pics{grid-column:2/3;height:96px}.card .info{grid-column:2/3}.right{grid-row:1/3;grid-column:3}.n{display:none}.ask{grid-column:1/-1}.acard{grid-template-columns:84px 1fr;column-gap:.7rem;row-gap:.45rem;padding:.7rem .8rem}.acard .pics{grid-column:1;grid-row:1/3;align-self:start}.acard .info{grid-column:2}.acard .acts{grid-column:2;flex-wrap:wrap;gap:.4rem .9rem}.search{min-width:0;width:100%}}
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
function render(order){
  // order: ids to show while a moved shoot waits for its new due date (nothing is saved until a date is picked)
  const w = order ? order.map(id => Q.waiting.find(s => s.id == id)) : Q.waiting, list = $('#list'), first = Q.waiting[0];
  $('#count').innerHTML = w.length ? `${w.length} shoot${w.length==1?'':'s'} to edit` : 'All caught up';
  $('#next').innerHTML = first ? `Next up: <em>${esc(first.name)}</em>, ${esc(dueWords(first.due))}.` : '';
  list.innerHTML = w.length ? '' : '<li class="empty"><b>Nothing waiting.</b><span>Shoots land here when you add them after a backup. Already have a list of clients to edit? Send Claude a screenshot of it, or type the names, and say "add these to my editing queue."</span></li>';
  w.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'card'; li.dataset.id = s.id; li.draggable = true;
    const pics = s.thumbs.length ? s.thumbs.map(t => `<span><img src="${esc(t)}" alt=""></span>`).join('') : '<div class="none">no previews</div>';
    li.innerHTML = `<span class="grip" title="Drag to reorder">&#8942;&#8942;</span>
      <div class="pics">${pics}</div>
      <div class="info"><div class="name">${esc(s.name)}</div>
        <div class="meta">${dueTag(s.due)}<button class="setdue" type="button">${s.due ? 'Change the date' : 'Set a due date'}</button>${s.shot ? `<span>Shot ${nice(s.shot)}</span>` : ''}${s.count ? `<span>${s.count.toLocaleString()} photos</span>` : ''}</div></div>
      <div class="right"><span class="n">${String(i + 1).padStart(2, '0')}</span>
        <button class="check" title="Mark finished" aria-label="Mark ${esc(s.name)} finished"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></button></div>`;
    li.querySelector('.check').onclick = () => finish(li, s);
    li.querySelector('.setdue').onclick = () => pickDue(li, s);
    list.appendChild(li);
  });
  renderArchive();
}
let FILTER = '';
function renderArchive(fresh){
  const a = Q.archive, box = $('#alist');
  $('#acount').textContent = a.length ? `${a.length} shoot${a.length==1?'':'s'}, newest first` : 'Shoots land here after a backup, and when you finish editing one.';
  const f = FILTER.trim().toLowerCase();
  const shown = f ? a.filter(s => s.name.toLowerCase().includes(f)) : a;
  let html = '', month = null;
  shown.forEach(s => {
    const m = s.shot ? new Date(s.shot + 'T12:00:00').toLocaleDateString('en-US', {month:'long', year:'numeric'}) : 'No date';
    if(m != month){ html += `<li class="month">${esc(m)}</li>`; month = m }
    const pics = s.thumbs.length ? s.thumbs.map(t => `<span><img src="${esc(t)}" alt="" loading="lazy"></span>`).join('') : '<div class="none">no previews</div>';
    html += `<li class="acard${fresh == s.id ? ' fresh' : ''}" data-id="${esc(s.id)}"><div class="pics">${pics}</div>
      <div class="info"><div class="name">${esc(s.name)}</div>
        <div class="meta">${s.status == 'finished' ? `<span class="tag edited">Edited${s.finished_at ? ' ' + nice(s.finished_at.slice(0,10)) : ''}</span>` : ''}${s.shot ? `<span>Shot ${nice(s.shot)}</span>` : ''}${s.count ? `<span>${s.count.toLocaleString()} photos</span>` : ''}</div></div>
      <div class="acts">${s.has_folder ? `<button class="open-folder" data-id="${esc(s.id)}">Open photo folder</button>` : ''}
        <button class="requeue" data-id="${esc(s.id)}">Put back in the queue</button></div></li>`;
  });
  box.innerHTML = html || (a.length ? '' : '');
  $('#nomatch').hidden = !(f && !shown.length);
  box.querySelectorAll('.open-folder').forEach(b => b.onclick = () => openFolder(b.dataset.id));
  box.querySelectorAll('.requeue').forEach(b => b.onclick = async () => {
    if(await send({action:'requeue', id:b.dataset.id})){render(); toast('Back in the queue, no due date yet'); window.scrollTo({top:0, behavior:'smooth'})}});
}
async function openFolder(id){
  if(!LIVE){toast('Ask Claude to “show my shoots” to open folders from here');return}
  try{const r = await fetch('/open?id=' + encodeURIComponent(id)); const j = await r.json(); toast(j.words)}
  catch(e){toast('Could not open that folder.')}
}
function dueWords(iso){if(!iso) return 'no due date';const n = days(iso);if(n<0) return `${-n} day${n==-1?'':'s'} late`;if(n==0) return 'due today';if(n==1) return 'due tomorrow';if(n<=7) return `due in ${n} days`;return 'due ' + nice(iso)}
async function finish(li, s){
  li.classList.add('done');
  if(!(await send({action:'done', id:s.id}))){li.classList.remove('done');return}
  toast(`${s.name}: finished, moved to your shoots below`);
  setTimeout(() => {li.classList.add('leaving'); setTimeout(() => {render(); renderArchive(s.id)}, 600)}, 1400);
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
  const old = Q.waiting.map(s => s.id), at = ids.indexOf(dragId);
  // moved past a deadline that is now out of order? offer the moved shoot a new due date:
  // up past a shoot due sooner (theirs may need to come earlier), or down past one due later (theirs may need to move out)
  const wentUp = Q.waiting.filter(s => old.indexOf(s.id) < from && ids.indexOf(s.id) > at);
  const wentDown = Q.waiting.filter(s => old.indexOf(s.id) > from && ids.indexOf(s.id) < at);
  // the soonest due date is always on top, so a move across another shoot's date only sticks with a new date
  const key = s => s.due || '9999';
  const dir = wentUp.some(s => key(s) < key(moved)) ? 'up'
    : wentDown.some(s => key(s) > key(moved)) ? 'down' : null;
  const id = dragId; dragId = null;
  if(dir){ render(ids); askDue(id, dir); return }   // shown where they dropped it; Keep slides it back
  if(await send({action:'order', ids})) render();
});
function askDue(id, dir){
  const s = Q.waiting.find(x => x.id == id);const li = document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);if(!s || !li) return;
  const box = document.createElement('div');box.className = 'ask';
  box.innerHTML = `<b>Moved ${dir == 'down' ? 'down' : 'up'}. New due date?</b>
    <button class="keep" data-v="keep">Keep ${s.due ? esc(nice(s.due)) : 'no due date'}</button>
    <button class="pick">Pick a date</button>
    <span class="when" hidden><input type="date" min="${Q.today}" value="${esc(s.due || '')}"><button class="go" disabled>Change date</button></span>`;
  li.appendChild(box);
  const when = box.querySelector('.when'), input = box.querySelector('input'), go = box.querySelector('.go');
  box.querySelector('.keep').onclick = () => { render(); toast(`Kept the date, so ${s.name} goes back in due-date order`) };
  box.querySelector('.pick').onclick = ev => {
    ev.target.hidden = true; when.hidden = false; input.focus();
    try{ input.showPicker() }catch(e){}   // opens the calendar where the browser allows it
  };
  input.oninput = () => { go.disabled = !input.value || input.value == s.due };
  go.onclick = async () => { if(input.value && await send({action:'due', id, due:input.value})){render();toast('Due date changed to ' + nice(input.value))} };
  li.scrollIntoView({block:'nearest', behavior:'smooth'});
}
function pickDue(li, s){
  // "Set a due date" on a card (Dustin, Oct 31): the calendar opens right there; a date moves the shoot into date order.
  if(li.querySelector('.ask')) return;
  const box = document.createElement('div');box.className = 'ask';
  box.innerHTML = `<b>${s.due ? 'New due date for ' + esc(s.name) + '?' : 'When is ' + esc(s.name) + ' due?'}</b>
    <span class="when"><input type="date" min="${Q.today}" value="${esc(s.due || '')}"><button class="go" disabled>${s.due ? 'Change date' : 'Save'}</button></span>
    <button class="keep">${s.due ? 'Keep ' + esc(nice(s.due)) : 'Not now'}</button>`;
  li.appendChild(box);
  const input = box.querySelector('input'), go = box.querySelector('.go');
  input.focus(); try{ input.showPicker() }catch(e){}
  input.oninput = () => { go.disabled = !input.value || input.value == s.due };
  go.onclick = async () => { if(input.value && await send({action:'due', id:s.id, due:input.value})){render();toast(esc(s.name) + ' due ' + nice(input.value))} };
  box.querySelector('.keep').onclick = () => box.remove();
  li.scrollIntoView({block:'nearest', behavior:'smooth'});
}
// "Add a shoot" (Dustin, Oct 31): a name and an optional date, right under the heading. No photos behind it yet.
$('#addbtn').onclick = () => { const f = $('#addform'); f.hidden = !f.hidden; if(!f.hidden){ $('#addname').focus() } };
$('#addcancel').onclick = () => { $('#addform').hidden = true; $('#addname').value = ''; $('#adddue').value = '' };
$('#addform').onsubmit = async e => {
  e.preventDefault(); const name = $('#addname').value.trim(), due = $('#adddue').value;
  if(!name){ $('#addname').focus(); return }
  if(!LIVE){ $('#added').textContent = 'This is a saved copy. Ask Claude to pull up your queue, then add it there.'; return }
  if(await send({action:'add', name, due})){ render(); $('#addname').value = ''; $('#adddue').value = '';
    $('#added').textContent = name + (due ? ' added, due ' + nice(due) + '.' : ' added, no due date yet.'); toast(name + ' is in your queue'); $('#addname').focus() }
  else $('#added').textContent = 'Could not add it. Tell Claude instead.';
};
$('#q').addEventListener('input', e => {FILTER = e.target.value; renderArchive()});
if(!LIVE) $('#offline').hidden = false;
render();
if(location.hash == '#archive') setTimeout(() => document.getElementById('archive').scrollIntoView({behavior:'smooth'}), 200);
"""


def state(q):
    def pub(s):
        d = {k: s.get(k) for k in ("id", "name", "shot", "due", "count", "thumbs", "finished_at", "status")}
        d["has_folder"] = bool(s.get("studio") or s.get("folder"))
        return d
    return {"today": today().isoformat(), "waiting": [pub(s) for s in waiting(q)], "archive": [pub(s) for s in archive(q)]}



def home_link():
    """A Home link to the Studio's home page, when its server has run (home.py; the address is kept in posting-url.txt)."""
    try:
        f = HOME / "posting-url.txt"
        if f.exists():
            return f"<a class='homelink' href='{f.read_text().strip().rsplit('/', 1)[0]}/home'>Home</a>"
    except OSError:
        pass
    return ""


def page_html(q):
    data = json.dumps(state(q)).replace("</", "<\\/")
    when = today().strftime("%A, %B ") + str(today().day)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Your shoots · The Studio</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body>"
            "<div class='wrap'><div class='bar'><span class='brand'><b>The Studio</b><small>by Horizon Found</small></span>"
            f"{home_link()}<span class='when'>{html.escape(when)}</span></div>"
            "<header class='head'><span class='eyebrow'>Editing queue</span><h1 id='count'></h1><p class='lede' id='next'></p>"
            "<span class='talk'>The soonest due date is always on top. Shoots with no date keep the order you put them in. Press Set a due date on any shoot, or drag one up or down.</span>"
            "<div class='addrow'><button class='addbtn' id='addbtn' type='button'><span class='plus'>+</span> Add a shoot</button>"
            "<form class='addform' id='addform' hidden><input type='text' id='addname' placeholder='Client or shoot name' maxlength='80' autocomplete='off'>"
            "<input type='date' id='adddue' title='Due date (optional)'><button type='submit' class='go'>Add to the queue</button><button type='button' class='cancel' id='addcancel'>Cancel</button>"
            "<span class='hint'>The date is optional. A shoot added here has no photos behind it yet, so its card shows no previews.</span></form><p class='added' id='added'></p></div>"
            "<p class='offline' id='offline' hidden>This is a saved copy. Ask Claude to “pull up my queue” to check things off and change dates.</p></header>"
            "<ol class='list' id='list'></ol>"
            "<div class='line' id='archive'><span>Your shoots</span></div>"
            "<div class='arch-head'><span class='count' id='acount'></span>"
            "<label class='search'><svg viewBox='0 0 24 24'><circle cx='11' cy='11' r='7'/><path d='M20 20l-3.5-3.5'/></svg>"
            "<input id='q' type='search' placeholder='Find a shoot' autocomplete='off'></label></div>"
            "<ul class='alist' id='alist'></ul><p class='nomatch' id='nomatch' hidden>No shoot by that name.</p></div>"
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
        if p == "/open":
            from urllib.parse import parse_qs
            sid = parse_qs(urlsplit(self.path).query).get("id", [""])[0]
            s = next((x for x in load()["shoots"] if x["id"] == sid), None)  # only a shoot's own folder, never a path from the page
            ok, words = open_folder(s) if s else (False, "I don't know that shoot.")
            out = json.dumps({"ok": ok, "words": words}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)
            return
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
            if act in ("done", "undo", "due", "requeue"):
                s = next(x for x in q["shoots"] if x["id"] == body.get("id"))
                if act == "done":
                    s["status"], s["finished_at"] = "finished", datetime.now().isoformat(timespec="seconds")
                    s["finished_by"] = "page"
                elif act in ("undo", "requeue"):
                    s["status"] = "waiting"
                    for k in ("finished_at", "finished_by", "offered", "reminded"):
                        s.pop(k, None)
                    if act == "requeue":
                        s["due"] = body.get("due") and due_date(body["due"])[0]
                    q["shoots"].remove(s)
                    place(q, s)
                else:
                    s["due"], how = due_date(body.get("due"))
                    s.pop("reminded", None)
            elif act == "order":
                reorder(q, [str(i) for i in body.get("ids", [])])
            elif act == "add":
                name = " ".join(str(body.get("name", "")).split())
                if not name:
                    raise ValueError("a name is needed")
                add_manual(q, name, body.get("due") or None)
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
        a = archive(q)
        say(f"Your shoots ({len(a)}):")
        for s in a:
            say(f"   {s.get('shot') or 'no date'}  {s['name']}" + ("  (edited)" if s.get("status") == "finished" else ""))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add"); a1.add_argument("--night", required=True); a1.add_argument("--shoot", required=True)
    a1.add_argument("--due", required=True); a1.add_argument("--name")
    a2 = sub.add_parser("add-manual"); a2.add_argument("--name", required=True); a2.add_argument("--due")
    a2.add_argument("--shot"); a2.add_argument("--folder")
    a3 = sub.add_parser("add-list"); a3.add_argument("--file", help="one name per line"); a3.add_argument("--names", help="names separated by commas")
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
    rg = sub.add_parser("register"); rg.add_argument("--night", required=True)
    sub.add_parser("scan")
    op = sub.add_parser("open"); op.add_argument("which")
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
    elif a.cmd == "add-list":
        names = Path(a.file).read_text().splitlines() if a.file else [n for n in (a.names or "").split(",")]
        added = add_list(q, names)
        if not added:
            sys.exit("STOP: I didn't find any names in that list.")
        save(q)
        write_page(q)
        say(f"Added {len(added)} shoot{'s' if len(added) != 1 else ''} to the editing queue, in this order:")
        for e in added:
            twin = f"  (there was already a {e['name']}; this is a second one)" if e.pop("dup_of", 0) else ""
            say(f"  {e['name']}" + (f", {due_words(e['due'])}" if e.get("due") else "") + twin)
        save(q)
        dated = [e for e in added if e.get("due")]
        if len(dated) < len(added):
            say("No due dates yet on the rest; they sit in this order below anything with a date. Set one on the page (Set a due date on the shoot) or just say it: \"Cassandra's due Friday.\"")
    elif a.cmd == "list":
        show(q, a.all)
    elif a.cmd in ("done", "undo"):
        s = find(q, a.which)
        if a.cmd == "done":
            if not is_waiting(s):
                say(f"{s['name']} was already finished.")
                return
            s["status"], s["finished_at"], s["finished_by"] = "finished", datetime.now().isoformat(timespec="seconds"), "claude"
        else:
            s["status"] = "waiting"
            for k in ("finished_at", "finished_by", "offered", "reminded"):
                s.pop(k, None)
            q["shoots"].remove(s)
            place(q, s)
        save(q)
        write_page(q)
        say(f"{'Finished' if a.cmd == 'done' else 'Back in the queue'}: {s['name']}.")
        if a.cmd == "done" and s.get("studio"):
            say(f"backup: {Path(s['studio'])}  shoot: {s['shoot']}")  # for the next step (finding the exports)
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
        want = max(0, min(len(ids), a.to - 1))
        ids.insert(want, s["id"])
        reorder(q, ids)
        save(q)
        write_page(q)
        w = waiting(q)
        at = [x["id"] for x in w].index(s["id"])
        if at != want:  # soonest due is always on top, so a move across due dates needs a new date
            other = w[want]
            say(f"{s['name']} is {due_words(s.get('due'))} and {other['name']} is {due_words(other.get('due'))}, "
                f"so the soonest stays on top. To move {s['name']} there, give it a new due date.")
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
    elif a.cmd == "register":
        n = register_night(q, a.night)
        save(q)
        write_page(q)
        say(f"{n} shoot{'s' if n != 1 else ''} added to your shoots." if n else "Those shoots were already there.")
    elif a.cmd == "scan":
        total = 0
        for night in nights_known():
            try:
                total += register_night(q, night)
            except (SystemExit, OSError, ValueError, KeyError):
                continue  # a night that never finished, or a drive that is not plugged in
        save(q)
        write_page(q)
        say(f"Found {total} shoot{'s' if total != 1 else ''} not in your shoots yet; added. {len(archive(q))} in all, {len(waiting(q))} in the queue.")
    elif a.cmd == "open":
        ok, words = open_folder(find(q, a.which))
        say(words)
        if not ok:
            sys.exit(1)
    elif a.cmd == "offers":
        hits = [s for s in finished(q) if s.get("finished_by") == "page" and not s.get("offered")]
        for s in hits:
            say(f"{s['name']}" + (f"  (backup: {s['studio']}  shoot: {s['shoot']})" if s.get("studio") else ""))
            if a.mark:
                s["offered"] = datetime.now().isoformat(timespec="seconds")
        if a.mark and hits:
            save(q)


if __name__ == "__main__":
    main()
