#!/usr/bin/env python3
"""Name your shoots: the page that comes after a backup (Nicole's v31, section 6, screenshots 09 and 10; her
answers of Nov 23: "Joining two shoots into one, and naming shoots after the backup: both needed for launch").

Nothing is asked before the photos are safe. Afterwards this page shows each shoot the sorting found (three
pictures, when it was taken, how many, a name box, the folder name updating as they type), her "These are mini
sessions. Keep them in one folder.", Save the names, Do it later; then her All set screen.

    /name-shoots.html?backup=<the backup's name>      on the posting server (the page)
    /name-shoots-data?backup=...                       what the page draws from, and how the saving stands
    /name-shoots-pic?backup=...&shoot=s1&i=0           one of a shoot's three small pictures
    POST /name-shoots-save {backup, names: {id: name}, mini: bool, mini_name: str}

    python3 name_shoots.py url "<backup: its name, its folder or its records>"   the page's address
    python3 name_shoots.py status "<backup>"                                      how the saving stands
    python3 name_shoots.py job <tag>                                              the Assistant's own (the page starts it)

Our way underneath:
  - A backup is asked for by its NAME (the name of its records folder, as the Back up a card list knows it), a
    shoot by its id. The page never sends or shows a path; a picture is a shoot's id and 0, 1 or 2.
  - Save the names starts ONE background job that outlives the page and the page server: rename_shoot.py for
    each named shoot, one at a time (or join_shoots.py for mini sessions). Its record is written whole after
    every step in <STUDIO_HOME>/name-shoots/, so a reload shows where it stands, and a job whose process died
    is said to have stopped, never "working" for ever. Pressing Save again finishes it (both scripts finish a
    cut-off run from their own logs).
  - Every POST goes through the pickers' same-page-only guard; the GETs that list anything refuse another
    website and any other Host. Names reach the page as text only.
  - Her words are WORDS, whole. Ours are OUR_WORDS, drafts for Dustin and Nicole. Three of hers are not used
    because they are no longer true (HERS_NOT_TRUE says why).
"""
import argparse
import hashlib
import html
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()
import clips  # noqa: E402
import studio_file  # noqa: E402
from sort import safe_folder  # noqa: E402
from where import locate, place_key  # noqa: E402
import join_shoots  # noqa: E402

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JOBS = HOME / "name-shoots"
POST_CAP = 20000
NAME_MAX = 120
MOST_SHOOTS = 200
MARK = "\u0001NAME\u0001"            # stands for the typed name in a folder's pattern (never a letter of a name)
ANOTHER_CARD = "/home#backup"        # where Back up another card goes: the home page, where the backup starts
GET_ROUTES = ("/name-shoots.html", "/name-shoots-data", "/name-shoots-pic")
POST_ROUTES = ("/name-shoots-save",)
STARTING_GRACE = 20                  # seconds a job may take to come up before a missing process means "stopped"

# Hers, whole (v31 section 6 and pages/idea-naming-after-the-backup.html).
WORDS = {
    "title": "Name your <em>shoots</em>",
    "title_done": "All <em>set.</em>",
    "safe": "✓ Every photo is checked and safe on {where}. It's safe to format your card.",
    "safe_and": "✓ Every photo is checked and safe on {where} and {second}. It's safe to format your card.",
    "found": "We found {n} shoots on your card, sorted by when you took them. Give each one a name, or do it later.",
    "mini": "These are mini sessions. Keep them in one folder.",
    "placeholder": "Shoot name",
    "mini_placeholder": "Name the mini sessions",
    "mini_default": "Mini sessions",
    "mini_all": "All {count}, together",
    "folder": "Folder: {name}",
    "save": "Save the names",
    "later": "Do it later",
    "keep_names": "Only the folders get these names. Your photos keep their own names.",
    "another": "Back up another card",
    "another_note": "Got another card from the same day? It goes in with these.",
    "see_all": "See all my backups",
}

# Hers that are no longer true, and what stands in their place.
HERS_NOT_TRUE = {
    "Only the folders get these names. Your photos keep their own names.":
        "photos take the first word of the shoot's name since her Nov 23 answer; shown only to someone who keeps camera names (OUR_WORDS['note'] otherwise)",
    "Each in its own folder, in your editing queue.":
        "new shoots go to Your backups, not the editing queue (her Nov 23 answer): OUR_WORDS['each_own']",
    "In one folder, in your editing queue.": "the same: OUR_WORDS['one_folder']",
}

# Ours: drafts for Dustin and Nicole.
OUR_WORDS = {
    "found_one": "We found 1 shoot on your card. Give it a name, or do it later.",
    "note": ("Each folder gets its name, and the photos in it start with the first word of that name, like "
             "{example}. The camera's own name stays inside."),
    "each_own": "Each in its own folder, in Your backups.",
    "one_folder": "In one folder, in Your backups.",
    "not_safe": "Something in this backup needs a look. See the report before you format your card.",
    "sample": "This was a sample of the card, not all of it. Keep your card.",
    "unknown_safe": "I can't read this backup's records just now, so I can't say whether the card is safe to format.",
    "no_backup": "I can't find that backup. If it is on a drive, plug the drive in and open this again.",
    "no_shoots": "This backup has not been sorted into shoots yet. Ask the Assistant to finish it.",
    "back_home": "Back to home",
    "saving": "Saving the names: {done} of {total}.",
    "saving_one": "Renaming {name} now.",
    "saving_mini": "Putting them in one folder.",
    "leave": "You can leave this page. It carries on.",
    "stopped": "This stopped part way. Nothing is lost. Press Save the names and it will finish.",
    "problem": "{line} Nothing is lost.",
    "cant": "That didn't work just now. Tell the Assistant and it'll sort it out.",
    "busy": "A rename or a join is already at work. Give it a moment.",
    "same_name": ("Two shoots can't both be called {name}: they would share a folder. Give one of them another "
                  "name, or tick mini sessions to keep them in one folder."),
    "taken": "There is already a folder called {folder} next to these. Give {name} another name.",
    "change": "Change the names",
    "current": "the name it has now",
    "one_shoot_join": "There is only one shoot here, so there is nothing to put together.",
    "plug_in": "Plug in {drive} to name these shoots.",
    "not_understood": "That didn't arrive the way it should have. Reload the page and try again.",
    "report_way_in": "Name these shoots, or put them in one folder",
}

# Her popup's look (the home page's v30 look: Helvetica, warm paper, one red-orange), on this page only.
LOOK = r"""
:root{--accent:#D9603A;--cream:#EDEAE4;--paper:#F5F3EF;--card:#fff;--ink:#111;--ink-2:#6E6A64;--line:rgba(17,17,17,.14);
--sans:"Helvetica Neue",Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.5 var(--sans);letter-spacing:-.01em}
.wrap{max-width:780px;margin:0 auto;padding:22px 16px 60px}
.back{display:inline-block;margin:0 0 18px;font-size:13px;color:var(--ink);text-underline-offset:3px}
h1{font:700 30px/1.1 var(--sans);letter-spacing:-.02em;margin:0 0 8px}
h1 em{font-style:normal;color:var(--accent)}
.safe{font-weight:700;margin:0}
.warn{font-weight:700;margin:0;color:#B3402A}
.sub{color:var(--ink-2);margin:2px 0 18px}
.mini{display:flex;align-items:center;gap:10px;margin:0 0 16px;cursor:pointer}
.mini input{accent-color:var(--accent);width:18px;height:18px}
.nshoot{display:grid;grid-template-columns:auto 1fr;gap:14px;background:var(--card);padding:12px;margin:0 0 12px;align-items:center}
.th{display:flex;gap:2px}
.th img,.th i{display:block;width:50px;height:74px;object-fit:cover;background:var(--cream)}
.nshoot small{display:block;color:var(--ink-2);font-size:13px}
.nshoot input{display:block;width:100%;margin:6px 0;padding:10px 12px;font:400 16px/1.3 var(--sans);border:1px solid var(--line);
border-radius:0;background:#fff;color:var(--ink)}
.nshoot input::placeholder{color:var(--ink-2)}
.nshoot .pv{color:var(--ink);font-size:13px;overflow-wrap:anywhere}
.row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin:18px 0 0}
.go{background:var(--accent);color:#fff;border:0;border-radius:0;padding:12px 22px;font:700 16px/1.2 var(--sans);cursor:pointer;text-decoration:none;display:inline-block}
.go[disabled]{opacity:.5;cursor:default}
.lk{background:none;border:0;padding:0;font:400 16px/1.2 var(--sans);color:var(--ink);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.say{margin:10px 0 0;min-height:1.5em;color:#B3402A}
.note{margin:18px 0 0;padding:12px 16px;background:var(--card);border-left:3px solid var(--accent);color:var(--ink-2)}
.named p{display:flex;align-items:center;gap:10px;margin:0 0 4px;padding:12px 14px;background:var(--card);font-weight:700;overflow-wrap:anywhere}
.named p::before{content:"";flex:none;width:18px;height:14px;background:#C9B79A;border-radius:1px}
.dest{color:var(--ink-2);margin:10px 0 0}
.row small{color:var(--ink-2)}
.foot{margin:22px 0 0;padding:0 0 12px;border-bottom:1px solid var(--line);display:flex;gap:18px;flex-wrap:wrap}
.foot a{color:var(--ink);text-underline-offset:3px}
.work{background:var(--card);padding:14px 16px;margin:16px 0 0}
@media(max-width:520px){.nshoot{grid-template-columns:1fr}h1{font-size:25px}}
"""

JS = r"""
const W = JSON.parse(document.getElementById('words').textContent);
const BACKUP = JSON.parse(document.getElementById('backup').textContent);
const AGAIN = new URLSearchParams(location.search).get('again') === '1';
const $ = id => document.getElementById(id);
const fill = (t, o) => String(t).replace(/\{(\w+)\}/g, (m, k) => (k in o ? o[k] : m));
const q = '?backup=' + encodeURIComponent(BACKUP);
let D = null, MINI = false, NAMES = {}, MINI_NAME = '', FORM = AGAIN, timer = null, SAY = '';

function el(tag, cls, text){ const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function clean(n){ return String(n).replace(/[\\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim(); }
function folderFor(tpl, name, space){
  let n = clean(name); if (space && space !== ' ') n = n.split(' ').join(space);
  return tpl.split(D.mark).join(n).replace(/^[ .]+|[ .]+$/g, '').slice(0, 80).replace(/[ .]+$/, '');
}
function head(done){
  $('title').innerHTML = done ? W.title_done : W.title;        // her two titles, fixed words of ours and hers only
  const s = $('safe'); s.className = D.safe ? 'safe' : 'warn'; s.textContent = D.safe_line;
}
function pics(s, only){
  const th = el('div', 'th');
  const n = only ? 1 : 3;
  for (let i = 0; i < n; i++){
    if (i < s.pics){ const im = el('img'); im.alt = ''; im.src = '/name-shoots-pic' + q + '&shoot=' + encodeURIComponent(s.id) + '&i=' + i; th.appendChild(im); }
    else if (!only) th.appendChild(el('i'));
  }
  return th;
}
function form(){
  head(false);
  const top = $('top'); top.textContent = '';
  $('sub').textContent = D.shoots.length === 1 ? W.found_one : fill(W.found, {n: D.shoots.length});
  if (D.shoots.length > 1){
    const l = el('label', 'mini'), c = el('input'); c.type = 'checkbox'; c.id = 'mini'; c.checked = MINI;
    c.onchange = () => { MINI = c.checked; SAY = ''; form(); };
    l.appendChild(c); l.appendChild(el('span', '', W.mini)); top.appendChild(l);
  }
  if (MINI){
    const b = el('div', 'nshoot'), th = el('div', 'th');
    D.shoots.forEach(s => { const one = pics(s, true); while (one.firstChild) th.appendChild(one.firstChild); });
    const r = el('div'); r.appendChild(el('small', '', D.mini_all));
    const i = el('input'); i.id = 'name-mini'; i.maxLength = 120; i.placeholder = W.mini_placeholder; i.value = MINI_NAME; i.setAttribute('aria-label', W.mini_placeholder);
    const pv = el('small', 'pv');
    const show = () => { pv.textContent = fill(W.folder, {name: folderFor(D.mini_tpl, i.value.trim() || W.mini_default, D.space)}); };
    i.oninput = () => { MINI_NAME = i.value; show(); }; show();
    r.appendChild(i); r.appendChild(pv); b.appendChild(th); b.appendChild(r); top.appendChild(b);
  } else {
    D.shoots.forEach(s => {
      const b = el('div', 'nshoot'); b.dataset.shoot = s.id;
      b.appendChild(pics(s));
      const r = el('div'); r.appendChild(el('small', '', s.when + ' · ' + s.count));
      const i = el('input'); i.id = 'name-' + s.id; i.maxLength = 120; i.placeholder = W.placeholder; i.setAttribute('aria-label', W.placeholder);
      i.value = (s.id in NAMES) ? NAMES[s.id] : s.named;
      const pv = el('small', 'pv');
      const show = () => { pv.textContent = fill(W.folder, {name: clean(i.value) ? folderFor(s.tpl, i.value, D.space) : s.folder}); };
      i.oninput = () => { NAMES[s.id] = i.value; show(); }; show();
      r.appendChild(i); r.appendChild(pv); b.appendChild(r); top.appendChild(b);
    });
  }
  const row = el('div', 'row');
  const save = el('button', 'go', W.save); save.id = 'save'; save.type = 'button'; save.onclick = send;
  const later = el('a', 'lk', W.later); later.id = 'later'; later.href = '/home';
  row.appendChild(save); row.appendChild(later); top.appendChild(row);
  const say = el('p', 'say', SAY); say.id = 'line'; say.setAttribute('role', 'status'); top.appendChild(say);
  top.appendChild(el('p', 'note', D.note));
}
function working(){
  head(false);
  $('sub').textContent = '';
  const top = $('top'); top.textContent = '';
  const b = el('div', 'work'); b.id = 'work';
  const j = D.job;
  b.appendChild(el('p', '', j.mini ? W.saving_mini : fill(W.saving, {done: j.done, total: j.total})));
  if (!j.mini && j.now) b.appendChild(el('p', '', fill(W.saving_one, {name: j.now})));
  b.appendChild(el('p', 'dest', W.leave));
  top.appendChild(b);
}
function allSet(){
  head(true);
  $('sub').textContent = '';
  const top = $('top'); top.textContent = '';
  const list = el('div', 'named'); list.id = 'named';
  D.shoots.forEach(s => list.appendChild(el('p', '', s.folder)));
  top.appendChild(list);
  top.appendChild(el('p', 'dest', D.shoots.length === 1 && D.job && D.job.mini ? W.one_folder : W.each_own));
  const row = el('div', 'row');
  const again = el('a', 'go', W.another); again.id = 'another'; again.href = D.another;
  row.appendChild(again); row.appendChild(el('small', '', W.another_note)); top.appendChild(row);
  const foot = el('p', 'foot');
  const all = el('a', '', W.see_all); all.href = '/backups'; all.id = 'seeAll';
  const ch = el('a', '', W.change); ch.href = '/name-shoots.html' + q + '&again=1'; ch.id = 'change';
  foot.appendChild(all); foot.appendChild(ch); top.appendChild(foot);
}
function draw(){
  clearTimeout(timer);
  const st = D.job ? D.job.state : 'none';
  if (st === 'working'){ working(); timer = setTimeout(load, 1000); return; }
  if (st === 'done' && !FORM){ allSet(); return; }
  if ((st === 'problem' || st === 'stopped') && !SAY){
    SAY = D.job.line || W.cant;
    if (D.job.ask){ MINI = !!D.job.ask.mini && D.shoots.length > 1; MINI_NAME = D.job.ask.mini_name || ''; Object.assign(NAMES, D.job.ask.names || {}); }
  }
  form();
}
async function load(){
  try {
    const r = await fetch('/name-shoots-data' + q, {cache: 'no-store'}); const j = await r.json();
    if (!j.ok){ $('sub').textContent = j.words || W.cant; return; }
    D = j; draw();
  } catch (e) { timer = setTimeout(load, 2000); }
}
async function send(){
  const b = $('save'); b.disabled = true; SAY = ''; $('line').textContent = '';
  const names = {};
  if (!MINI) D.shoots.forEach(s => { const v = $('name-' + s.id).value.trim(); if (v) names[s.id] = v; });
  try {
    const r = await fetch('/name-shoots-save', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({backup: BACKUP, names: names, mini: MINI, mini_name: MINI ? $('name-mini').value.trim() : ''})});
    const j = await r.json();
    if (!j.ok){ SAY = j.words || W.cant; $('line').textContent = SAY; b.disabled = false; return; }
    FORM = false; SAY = ''; load();
  } catch (e) { SAY = W.cant; $('line').textContent = SAY; b.disabled = false; }
}
if (BACKUP !== null) load();
"""


def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key]


# ---------------------------------------------------------------- which backup

def backup_name(studio):
    """A backup's name: the name of its records folder (the day folder's name before it settles)."""
    studio = Path(studio)
    return studio.parent.name if studio.name == "_studio" else studio.name


def known_backups():
    """Every backup's records the Assistant can find right now (the editing queue's list, the card ledger, the
    place shoots settle), each once."""
    out, seen = [], set()
    spelled = []
    try:
        import edit_queue
        spelled += [s.get("studio") for s in edit_queue.load().get("shoots", []) if isinstance(s, dict) and s.get("studio")]
        spelled += edit_queue.nights_known()
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    for sp in spelled:
        if not isinstance(sp, str):
            continue
        p = Path(sp)
        for cand in ([p, p.parent] if p.name == "_studio" else [p]):
            try:
                rec = locate(cand)[1]
            except (SystemExit, OSError):
                continue
            k = place_key(rec)
            if k not in seen:
                seen.add(k)
                out.append(rec)
            break
    return out


def find_backup(name):
    """The records of the backup a PAGE asked for by name, or None. Its name is the name of its records folder
    (or the name the backup itself wrote down, or one of its shoots' ids in the editing queue's list); with two
    backups of one name, the newer. Never a path: a name with a slash in it finds nothing."""
    if not isinstance(name, str) or not name or len(name) > 200 or "/" in name or "\\" in name or name in (".", ".."):
        return None
    hits = []
    for rec in known_backups():
        if backup_name(rec) == name:
            hits.append(rec)
            continue
        try:
            if (json.loads((rec / "manifest.json").read_text(encoding="utf-8")).get("session") or "") == name:
                hits.append(rec)
        except (OSError, ValueError, AttributeError):
            pass
    if not hits:
        try:
            import edit_queue
            import home_base
            for s in edit_queue.load().get("shoots", []):
                if isinstance(s, dict) and s.get("id") == name and s.get("studio"):
                    rec = home_base.records_of(s["studio"])
                    if rec:
                        hits.append(rec)
        except (Exception, SystemExit):  # noqa: BLE001
            pass
    if not hits:
        return None

    def when(rec):
        try:
            return (rec / "manifest.json").stat().st_mtime
        except OSError:
            return 0
    return max(hits, key=when)


def tag_of(studio):
    return hashlib.sha1(place_key(Path(studio)).encode("utf-8", "replace")).hexdigest()[:16]


# ---------------------------------------------------------------- what the page draws from

def _json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def when_words(start, end):
    """ "Saturday 9:04 to 10:12 am", "Saturday 11:30 am to 12:15 pm", "Saturday 9:04 am" for one moment."""
    try:
        a = datetime.fromisoformat(start[:19])
        b = datetime.fromisoformat((end or start)[:19])
    except (TypeError, ValueError):
        return ""
    t = lambda d: this_computer.strftime(d, "%-I:%M")  # noqa: E731
    ap = lambda d: "am" if d.hour < 12 else "pm"  # noqa: E731
    day = a.strftime("%A")
    if a.date() != b.date():
        return f"{day} {t(a)} {ap(a)} to {b.strftime('%A')} {t(b)} {ap(b)}"
    if (a.hour, a.minute) == (b.hour, b.minute):
        return f"{day} {t(a)} {ap(a)}"
    if ap(a) == ap(b):
        return f"{day} {t(a)} to {t(b)} {ap(b)}"
    return f"{day} {t(a)} {ap(a)} to {t(b)} {ap(b)}"


def where_words(root):
    """ "G PAPA › CLIENT WORK": the drive by its name, then the folders down to where the shoots are."""
    root = Path(root)
    best = None
    try:
        for v in this_computer.volumes():
            vp = Path(v["path"])
            try:
                rel = root.resolve().relative_to(vp.resolve())
            except (ValueError, OSError):
                continue
            if v.get("system") and best is not None:
                continue
            if best is None or len(vp.parts) > len(best[0].parts):
                best = (vp, v.get("name") or vp.name, rel, bool(v.get("system")))
    except Exception:  # noqa: BLE001
        best = None
    if best and not best[3]:
        return " › ".join([best[1]] + list(best[2].parts))
    name = this_computer.drive_words(root)
    if name:
        parts = root.parts
        return " › ".join([name] + list(parts[3:] if len(parts) > 3 and parts[1] == "Volumes" else []))
    return f"this {this_computer.COMPUTER} › " + root.name if root.name else f"this {this_computer.COMPUTER}"


def shoot_pics(studio, s, groups):
    """Up to three small pictures of a shoot, as paths inside the records: its first-look picks when it has
    them, else three previews spread across it (the middle one first), as the report shows."""
    studio = Path(studio)
    out = []
    picks = (_json(studio / "sneak-peeks.json") or _json(studio / "picks.json") or {}).get("picks") or []
    for pk in picks:
        if isinstance(pk, dict) and pk.get("shoot") == s["id"] and pk.get("file"):
            f = studio / "sneak-peeks" / (Path(str(pk["file"])).stem + ".jpg")
            if f.is_file():
                out.append(f)
    if len(out) < 3:
        pv = [studio / "groups" / p for g in s.get("groups", []) if g in groups for p in groups[g].get("previews", [])
              if isinstance(p, str) and "/" not in p and "\\" not in p]
        pv = [f for f in pv if f.is_file()]
        if len(pv) > 3:
            pv = [pv[len(pv) // 2], pv[0], pv[-1]]
        out = pv if not out else out + [f for f in pv if f not in out]
    return out[:3]


def facts(studio):
    """Everything the page shows for one backup. Names and numbers only, never a path."""
    studio = Path(studio)
    root = locate(studio)[0]
    import home_base
    st = home_base.backup_status(studio)
    manifest = _json(studio / "manifest.json", {}) or {}
    sh = (_json(studio / "shoots.json", {}) or {}).get("shoots") or []
    groups = {g["id"]: g for g in (_json(studio / "groups.json", {}) or {}).get("groups") or [] if isinstance(g, dict) and g.get("id")}
    names = _json(studio / "names.json", {}) or {}
    naming = studio_file.load().get("naming", {}) or {}
    keep_names = naming.get("file_names", "shoot") == "original"
    where = where_words(root)
    if st.get("safe") is True:
        second = None
        if st.get("second"):
            try:
                import second_copy
                second = second_copy.drive_name(second_copy.has_second(manifest))
            except Exception:  # noqa: BLE001
                second = None
        safe_line = WORDS["safe_and"].format(where=where, second=second) if second else WORDS["safe"].format(where=where)
    elif st.get("sample"):
        safe_line = OUR_WORDS["sample"]
    elif not st.get("known"):
        safe_line = OUR_WORDS["unknown_safe"]
    else:
        safe_line = OUR_WORDS["not_safe"]

    def tpl(when):
        if naming.get("folder_pattern") and when:
            try:
                return studio_file.render(dict(naming, space=" "), MARK, when)
            except (ValueError, TypeError):
                pass
        return MARK

    shoots, total_p, total_c, first_when, example = [], 0, 0, None, None
    for s in sh:
        if not isinstance(s, dict) or not s.get("id") or not s.get("folder"):
            continue
        gs = [groups[g] for g in s.get("groups", []) if g in groups]
        starts = sorted(str(g.get("start") or "") for g in gs if g.get("start"))
        ends = sorted(str(g.get("end") or g.get("start") or "") for g in gs if g.get("start"))
        n_p, n_c = clips.count(f for g in gs for f in g.get("files", []))
        total_p, total_c = total_p + n_p, total_c + n_c
        when = starts[0] if starts else None
        if when and (first_when is None or when < first_when):
            first_when = when
        if example is None:
            f = next((f for g in gs for f in g.get("files", []) if not clips.is_clip(f)), None)
            if f:
                parts = Path(f).name.split("_", 2)
                example = "Name_0001_" + (parts[2] if len(parts) == 3 and parts[1].isdigit() else Path(f).name)
        shoots.append({"id": str(s["id"]), "when": when_words(when, ends[-1] if ends else when) if when else "",
                       "count": clips.words(n_p, n_c), "named": " ".join(str(names.get(s["id"]) or "").split()),
                       "folder": str(s["folder"]), "tpl": tpl(when), "pics": len(shoot_pics(studio, s, groups))})
    note = WORDS["keep_names"] if keep_names else OUR_WORDS["note"].format(example=example or "Name_0001_IMG_4471.JPG")
    return {"ok": True, "backup": backup_name(studio), "safe": st.get("safe") is True, "safe_line": safe_line,
            "shoots": shoots, "mark": MARK, "space": naming.get("space", " "), "mini_tpl": tpl(first_when),
            "mini_all": WORDS["mini_all"].format(count=clips.words(total_p, total_c)), "note": note,
            "another": ANOTHER_CARD, "job": job_for_page(studio)}


def folder_for(naming, name, when):
    return safe_folder(studio_file.render(naming, name, when)) if naming.get("folder_pattern") and when else safe_folder(name)


def clashes(studio, names):
    """Plain words when the typed names can't all be given: two shoots that would share a folder, or a folder
    of that name already next to them. None when they can."""
    studio = Path(studio)
    root = locate(studio)[0]
    sh = [s for s in (_json(studio / "shoots.json", {}) or {}).get("shoots") or [] if isinstance(s, dict) and s.get("folder")]
    groups = {g["id"]: g for g in (_json(studio / "groups.json", {}) or {}).get("groups") or [] if isinstance(g, dict) and g.get("id")}
    naming = studio_file.load().get("naming", {}) or {}
    mine = {join_shoots.fold(str(s["folder"])) for s in sh}
    will = {}
    for s in sh:
        starts = sorted(str(groups[g].get("start") or "") for g in s.get("groups", []) if g in groups and groups[g].get("start"))
        new = names.get(s["id"])
        folder = folder_for(naming, new, starts[0] if starts else None) if new else str(s["folder"])
        k = join_shoots.fold(folder)
        if k in will and (new or will[k][1]):
            return OUR_WORDS["same_name"].format(name=new or will[k][1])
        will[k] = (s["id"], new)
        there = join_shoots.named_like(root, folder) if new and k not in mine else []
        if there:
            return OUR_WORDS["taken"].format(folder=there[0], name=new)     # the folder as it is spelled on the drive
    return None


# ---------------------------------------------------------------- the job that saves the names

def job_file(studio):
    return JOBS / f"{tag_of(studio)}.json"


def job_read(studio):
    d = _json(job_file(studio))
    return d if isinstance(d, dict) else None


def job_write(studio, rec):
    JOBS.mkdir(parents=True, exist_ok=True)
    join_shoots.write_json(job_file(studio), rec)


def job_state(studio):
    """The job's record as it truly stands: "working" only while its process is alive."""
    d = job_read(studio)
    if not d:
        return None
    if d.get("state") == "working":
        alive = this_computer.still_running(d.get("pid")) if d.get("pid") else None
        try:
            young = (datetime.now() - datetime.fromisoformat(d.get("started"))).total_seconds() < STARTING_GRACE
        except (TypeError, ValueError):
            young = False
        if alive is False or (not d.get("pid") and not young):
            d = dict(d, state="stopped", line=OUR_WORDS["stopped"])
    return d


def job_for_page(studio):
    d = job_state(studio)
    if not d:
        return None
    ask = d.get("ask") or {}
    return {"state": d.get("state"), "done": int(d.get("done") or 0), "total": int(d.get("total") or 0),
            "now": str(d.get("now") or ""), "mini": bool(ask.get("mini")), "line": str(d.get("line") or ""),
            "ask": {"names": ask.get("names") or {}, "mini": bool(ask.get("mini")), "mini_name": ask.get("mini_name") or ""}}


def start(studio, names, mini=False, mini_name=""):
    """Start the one background job for this backup. {"ok": True} or {"ok": False, "words": plain words}."""
    studio = Path(studio)
    now_ = job_state(studio)
    if now_ and now_.get("state") == "working":
        return {"ok": False, "words": OUR_WORDS["busy"]}
    todo = [[i, n] for i, n in names.items()]
    rec = {"state": "working", "backup": backup_name(studio), "records": str(studio),
           "ask": {"names": names, "mini": bool(mini), "mini_name": mini_name},
           "todo": todo, "done": 0, "total": 1 if mini else len(todo), "now": "", "line": "",
           "started": datetime.now().isoformat(timespec="seconds"), "finished": None, "pid": None}
    if not mini and not todo:
        job_write(studio, dict(rec, state="done", finished=rec["started"]))
        return {"ok": True, "state": "done"}
    job_write(studio, rec)
    logs = HOME / "logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / "name-shoots.log", "ab") as out:
            p = this_computer.popen_detached([sys.executable, str(HERE / "name_shoots.py"), "job", tag_of(studio)],
                                             stdin=subprocess.DEVNULL, stdout=out, stderr=out)
    except OSError:
        job_write(studio, dict(rec, state="problem", line=OUR_WORDS["cant"]))
        return {"ok": False, "words": OUR_WORDS["cant"]}
    # the job writes its own number into the record as it comes up (never written from here: the job may
    # already be a step further on); until then a record with no number is given STARTING_GRACE seconds
    return {"ok": True, "state": "working"}


def plain(out, fallback):
    """The last line a script said, when it is plain words (no path in it); else the fallback."""
    lines = [ln.strip() for ln in (out or "").strip().splitlines() if ln.strip()]
    stop = next((ln for ln in reversed(lines) if ln.startswith("STOP: ")), "")
    why = stop.replace("STOP: ", "")
    if not why or "/" in why or "\\" in why:
        return fallback
    return why


def run_job(tag):
    """The job itself: one shoot at a time, the record written whole after every step."""
    f = JOBS / f"{tag}.json"
    rec = _json(f)
    if not isinstance(rec, dict) or rec.get("state") != "working":
        return 0
    studio = Path(rec["records"])

    def note(**k):
        rec.update(k)
        join_shoots.write_json(f, rec)
    note(pid=os.getpid())
    quiet = {"creationflags": 0x08000000} if this_computer.WINDOWS else {}
    with join_shoots.held() as got:
        if not got:
            note(state="problem", line=OUR_WORDS["busy"], finished=datetime.now().isoformat(timespec="seconds"))
            return 1
        env = dict(os.environ, **{join_shoots.LOCK_HELD: "1"})
        ask = rec.get("ask") or {}
        ok = True
        if ask.get("mini"):
            name = ask.get("mini_name") or WORDS["mini_default"]
            note(now=name)
            r = subprocess.run([sys.executable, str(HERE / "join_shoots.py"), str(studio), "--all", "--name", name],
                               capture_output=True, encoding="utf-8", errors="replace", env=env, **quiet)
            sys.stdout.write(r.stdout + r.stderr)
            if r.returncode == 0:
                note(done=1)
            else:
                ok = False
                note(state="problem" if r.returncode == 2 else "stopped",
                     line=(OUR_WORDS["problem"].format(line=plain(r.stdout + r.stderr, OUR_WORDS["cant"])) if r.returncode == 2
                           else OUR_WORDS["stopped"]))
        else:
            for n, (sid, name) in enumerate(rec.get("todo") or []):
                note(now=name)
                r = subprocess.run([sys.executable, str(HERE / "rename_shoot.py"), str(studio), "--shoot", sid, "--name", name],
                                   capture_output=True, encoding="utf-8", errors="replace", env=env, **quiet)
                sys.stdout.write(r.stdout + r.stderr)
                if r.returncode != 0:
                    ok = False
                    why = plain(r.stdout + r.stderr, "")
                    note(state="problem" if why else "stopped",
                         line=OUR_WORDS["problem"].format(line=why) if why else OUR_WORDS["stopped"])
                    break
                note(done=n + 1)
            try:    # the report shows the new names
                subprocess.run([sys.executable, str(HERE / "report_page.py"), str(studio)], capture_output=True,
                               encoding="utf-8", errors="replace", timeout=300, env=env, **quiet)
            except (OSError, subprocess.SubprocessError):
                pass
        if ok:
            note(state="done", now="", finished=datetime.now().isoformat(timespec="seconds"))
        else:
            note(finished=datetime.now().isoformat(timespec="seconds"))
    sys.stdout.flush()
    return 0 if ok else 1


# ---------------------------------------------------------------- the page

def page_html(backup):
    e = html.escape
    words = {k: W(k) for k in ("title", "title_done", "found", "found_one", "mini", "placeholder", "mini_placeholder",
                               "mini_default", "folder", "save", "later", "another", "another_note", "see_all",
                               "each_own", "one_folder", "saving", "saving_one", "saving_mini", "leave", "cant", "change")}
    data = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")  # noqa: E731
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Name your shoots</title><style>{LOOK}</style></head>
<body><div class="wrap">
<a class="back" href="/home">&larr; {e(OUR_WORDS['back_home'])}</a>
<h1 id="title">{WORDS['title']}</h1>
<p id="safe" class="safe"></p>
<p id="sub" class="sub">{'' if backup is not None else e(OUR_WORDS['no_backup'])}</p>
<div id="top"></div>
</div>
<script type="application/json" id="words">{data(words)}</script>
<script type="application/json" id="backup">{data(backup)}</script>
<script>{JS}</script>
</body></html>"""


def _send(handler, body, ctype, code=200, cache="no-store"):
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", cache)
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _answer(handler, obj, code=200):
    _send(handler, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", code)


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _log(msg):
    try:
        sys.stderr.write(f"name-shoots: {msg}\n")
    except OSError:
        pass


def _one(q, key):
    v = q.get(key) or []
    return v[0] if len(v) == 1 else None


def _unplugged(name):
    """Words for a backup the queue knows by this name whose drive is not there, or None."""
    try:
        import edit_queue
        for s in edit_queue.load().get("shoots", []):
            sp = s.get("studio") if isinstance(s, dict) else None
            if sp and name in (Path(sp).name, Path(sp).parent.name):
                drive = this_computer.drive_words(sp)
                if drive:
                    return OUR_WORDS["plug_in"].format(drive=drive)
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    return None


def handle_get(handler, path, query):
    """Every GET of this page. The posting server has already checked the Host. Whatever goes wrong, an answer."""
    import arrange
    try:
        try:
            q = parse_qs(query or "", keep_blank_values=True)
        except ValueError:
            q = {}
        name = _one(q, "backup")
        if path == "/name-shoots.html":
            studio = find_backup(name) if name else None
            if studio is None:
                return _send(handler, page_html(None).encode("utf-8"), "text/html; charset=utf-8", 404)
            return _send(handler, page_html(name).encode("utf-8"),
                         "text/html; charset=utf-8")
        if not arrange.our_host(handler) or _cross_site(handler):
            return _answer(handler, {"ok": False}, 403)
        studio = find_backup(name) if name else None
        if studio is None:
            return _answer(handler, {"ok": False, "words": (_unplugged(name) if name else None) or OUR_WORDS["no_backup"]}, 404)
        if path == "/name-shoots-data":
            d = facts(studio)
            if not d["shoots"]:
                return _answer(handler, {"ok": False, "words": OUR_WORDS["no_shoots"]})
            d["backup"] = name
            return _answer(handler, d)
        if path == "/name-shoots-pic":
            sid, i = _one(q, "shoot"), _one(q, "i")
            if not sid or i not in ("0", "1", "2"):
                return handler.send_error(404)
            sh = (_json(studio / "shoots.json", {}) or {}).get("shoots") or []
            s = next((x for x in sh if isinstance(x, dict) and x.get("id") == sid), None)
            if not s:
                return handler.send_error(404)
            groups = {g["id"]: g for g in (_json(studio / "groups.json", {}) or {}).get("groups") or [] if isinstance(g, dict) and g.get("id")}
            pics = shoot_pics(studio, s, groups)
            if int(i) >= len(pics):
                return handler.send_error(404)
            return _send(handler, pics[int(i)].read_bytes(), "image/jpeg", cache="private, max-age=60")
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _answer(handler, {"ok": False, "words": OUR_WORDS["cant"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


_SAVING = threading.Lock()


def check_ask(studio, body):
    """(names, mini, mini_name) from a page's ask, every field checked; None when it is not one of ours."""
    if not isinstance(body, dict) or set(body) != {"backup", "names", "mini", "mini_name"}:
        return None
    names, mini, mini_name = body["names"], body["mini"], body["mini_name"]
    if not isinstance(names, dict) or not isinstance(mini, bool) or not isinstance(mini_name, str) or len(mini_name) > NAME_MAX:
        return None
    if len(names) > MOST_SHOOTS:
        return None
    ids = {s["id"] for s in (_json(Path(studio) / "shoots.json", {}) or {}).get("shoots") or []
           if isinstance(s, dict) and s.get("id") and s.get("folder")}
    out = {}
    for k, v in names.items():
        if k not in ids or not isinstance(v, str) or len(v) > NAME_MAX:
            return None
        v = " ".join(v.split())
        if v:
            out[k] = v
    return out, mini, " ".join(mini_name.split())


def handle_post(handler, path, query):
    """POST /name-shoots-save: only from this server's own page (the pickers' guard), every field checked, only
    a backup the Assistant knows and only that backup's own shoots."""
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
        if refused is None and _cross_site(handler):
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _answer(handler, {"ok": False, "words": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
        if path != "/name-shoots-save":
            return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 404)
        name = body.get("backup") if isinstance(body, dict) else None
        studio = find_backup(name) if isinstance(name, str) else None
        if studio is None:
            return _answer(handler, {"ok": False, "words": OUR_WORDS["no_backup"]}, 404)
        ask = check_ask(studio, body)
        if ask is None:
            return _answer(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
        names, mini, mini_name = ask
        with _SAVING:
            if mini:
                listed = join_shoots.listing(studio)
                if len([s for s in listed if s.get("folder")]) < 2:
                    return _answer(handler, {"ok": False, "words": OUR_WORDS["one_shoot_join"]})
                names = {}
            else:
                why = clashes(studio, names)
                if why:
                    return _answer(handler, {"ok": False, "words": why})
            return _answer(handler, start(studio, names, mini, mini_name))
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _answer(handler, {"ok": False, "words": OUR_WORDS["cant"]}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def url_for(studio, again=False):
    """The page's address for a backup, the posting server started if it is not up; None in a test or when it
    can't be started."""
    if this_computer.no_windows():
        return None
    try:
        import edit_queue
        base = edit_queue.posting_up()
    except (Exception, SystemExit):  # noqa: BLE001
        base = None
    if not base:
        return None
    return f"{base}/name-shoots.html?backup={quote(backup_name(studio), safe='')}" + ("&again=1" if again else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("url"); u.add_argument("backup")
    s = sub.add_parser("status"); s.add_argument("backup")
    j = sub.add_parser("job"); j.add_argument("tag")
    a = ap.parse_args()
    if a.cmd == "job":
        sys.exit(run_job(a.tag))
    try:
        studio = locate(a.backup)[1]
    except SystemExit:
        studio = find_backup(a.backup)
        if studio is None:
            sys.exit("STOP: " + OUR_WORDS["no_backup"])
    if a.cmd == "url":
        url = url_for(studio, again=True)
        if not url:
            sys.exit("STOP: the Assistant's page server could not be started.")
        print(url)
    elif a.cmd == "status":
        d = job_state(studio)
        print(json.dumps({k: v for k, v in (d or {"state": "none"}).items() if k != "records"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
