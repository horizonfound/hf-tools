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
    # a FOLDER was backed up (Back up a folder instead): no memory card in any line
    "found_folder": "We found {n} shoots in your folder, sorted by when you took them. Give each one a name, or do it later.",
    "found_one_folder": "We found 1 shoot in your folder. Give it a name, or do it later.",
    "safe_folder": "✓ Every photo is copied and checked on {where}.",
    "safe_folder_and": "✓ Every photo is copied and checked on {where} and {second}.",
    # the name typed in the Back up a card box before the backup, when the card turned out to hold several shoots
    # (so the backup could not know which one it was for): said back, never put on a shoot by guessing
    "typed_before": "Before the backup you typed “{name}”. Put it on the shoot it belongs to.",
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
    "stopped": "This stopped before it was done. Nothing is lost. Press Save the names to try again.",
    "half": "This was cut off part way. Nothing is lost. Press Finish it and it will carry on.",
    "finish": "Finish it",
    "finishing": "Finishing what was cut off.",
    "needs_look": ("This stopped on something I can't sort out from this page. Nothing is lost. "
                   "Tell the Assistant and it will take a look."),
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
let D = null, MINI = false, NAMES = {}, MINI_NAME = '', MINI_TOUCHED = false, FORM = AGAIN, timer = null, SAY = '';

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
  $('sub').textContent = D.shoots.length === 1 ? (D.from_folder ? W.found_one_folder : W.found_one) : fill(D.from_folder ? W.found_folder : W.found, {n: D.shoots.length});
  if (D.typed){ const tp = el('p', 'note', fill(W.typed_before, {name: D.typed})); tp.id = 'typed'; top.appendChild(tp); if (!MINI_NAME && !MINI_TOUCHED) MINI_NAME = D.typed; }
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
    i.oninput = () => { MINI_NAME = i.value; MINI_TOUCHED = true; show(); }; show();
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
  b.appendChild(el('p', '', j.finish ? W.finishing : j.mini ? W.saving_mini : fill(W.saving, {done: j.done, total: j.total})));
  if (!j.mini && !j.finish && j.now) b.appendChild(el('p', '', fill(W.saving_one, {name: j.now})));
  b.appendChild(el('p', 'dest', W.leave));
  top.appendChild(b);
}
function onlyLine(text){
  head(false);
  $('sub').textContent = '';
  const top = $('top'); top.textContent = '';
  const say = el('p', 'say', text); say.id = 'line'; say.setAttribute('role', 'status'); top.appendChild(say);
  return top;
}
function half(){
  // a join or a rename was cut off: the only thing offered is finishing it (the names and the tick box would
  // not be honoured until it is, and the folders the records list are not all there)
  const top = onlyLine(W.half);
  const row = el('div', 'row');
  const b = el('button', 'go', W.finish); b.id = 'finish'; b.type = 'button';
  b.onclick = async () => {
    b.disabled = true;
    try {
      const r = await fetch('/name-shoots-save', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({backup: BACKUP, names: {}, mini: false, mini_name: ''})});
      const j = await r.json();
      if (!j.ok){ $('line').textContent = j.words || W.cant; b.disabled = false; return; }
      FORM = false; SAY = ''; load();
    } catch (e) { $('line').textContent = W.cant; b.disabled = false; }
  };
  row.appendChild(b); top.appendChild(row);
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
  if (D.stuck){ onlyLine(W.needs_look); return; }
  if (D.half){ half(); return; }
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


_FOUND, _FOUND_LOCK, FOUND_FOR = {}, threading.Lock(), 8.0
_WHERE = {}


def find_backup(name):
    """The records of the backup a PAGE asked for by name, or None. Its name is the name of its records folder
    (or the name the backup itself wrote down, or one of its shoots' ids in the editing queue's list); with two
    backups of one name, the newer. Never a path: a name with a slash in it finds nothing."""
    if not isinstance(name, str) or not name or len(name) > 200 or "/" in name or "\\" in name or name in (".", ".."):
        return None
    # the page asks again every second while names are being saved: what was found is kept for a few seconds,
    # as long as that backup's records are still there
    with _FOUND_LOCK:
        hit = _FOUND.get(name)
    if hit and time.time() - hit[1] < FOUND_FOR and (hit[0] / "manifest.json").is_file():
        return hit[0]
    known = known_backups()
    hits = [rec for rec in known if backup_name(rec) == name]
    if not hits:        # by the name the backup itself wrote down (a manifest can be a megabyte: only when needed)
        for rec in known:
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
    best = max(hits, key=when)
    with _FOUND_LOCK:
        if len(_FOUND) > 200:
            _FOUND.clear()
        _FOUND[name] = (best, time.time())
    return best


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
    kept = _WHERE.get(str(root))
    if kept and time.time() - kept[1] < 30:      # asking the computer for its drives can take a moment
        return kept[0]
    out = _where_words(root)
    if len(_WHERE) > 200:
        _WHERE.clear()
    _WHERE[str(root)] = (out, time.time())
    return out


def _where_words(root):
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
                second = second_copy.drive_name(second_copy.has_second(_json(studio / "manifest.json", {}) or {}))
            except Exception:  # noqa: BLE001
                second = None
        if st.get("folder"):
            safe_line = OUR_WORDS["safe_folder_and"].format(where=where, second=second) if second else OUR_WORDS["safe_folder"].format(where=where)
        else:
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

    by_time = str((_json(studio / "shoots.json", {}) or {}).get("decided_by") or "").startswith("the backup")
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
        # a name they gave: on the report or here (names.json), or typed in the Back up a card box and used by
        # the backup because the card held one shoot ("placeholder": false). Never a stand-in like "Shoot 1".
        given = names.get(s["id"]) or (s.get("suggested") if by_time and s.get("placeholder") is False else "")
        shoots.append({"id": str(s["id"]), "when": when_words(when, ends[-1] if ends else when) if when else "",
                       "count": clips.words(n_p, n_c), "named": " ".join(str(given or "").split()),
                       "folder": str(s["folder"]), "tpl": tpl(when), "pics": len(shoot_pics(studio, s, groups))})
    note = WORDS["keep_names"] if keep_names else OUR_WORDS["note"].format(example=example or "Name_0001_IMG_4471.JPG")
    return {"ok": True, "backup": backup_name(studio), "safe": st.get("safe") is True, "safe_line": safe_line,
            "shoots": shoots, "mark": MARK, "space": naming.get("space", " "), "mini_tpl": tpl(first_when),
            "mini_all": WORDS["mini_all"].format(count=clips.words(total_p, total_c)), "note": note,
            "another": ANOTHER_CARD, "job": job_for_page(studio),
            "from_folder": bool(st.get("folder")), "typed": typed_before(studio, shoots),
            "half": half_done(studio) == "half", "stuck": half_done(studio) == "stuck"}


TYPED_MARK = "Shoot name typed before the backup: "   # night.py's own line in told.json (the by-time backup)


def typed_before(studio, shoots):
    """The name typed in the Back up a card box that the backup could not put on a shoot (the card held several),
    or "" (none typed, or a shoot already carries it)."""
    try:
        text = (_json(Path(studio) / "told.json", {}) or {}).get("text") or ""
    except AttributeError:
        return ""
    name = ""
    for ln in str(text).splitlines():
        if ln.startswith(TYPED_MARK):
            name = " ".join(ln[len(TYPED_MARK):].split())[:NAME_MAX]
    if not name or any(s.get("named") == name for s in shoots):
        return ""
    return name


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


_HALF = {}


def half_done(studio):
    """join_shoots.half_done ("half", "stuck" or None), read again only when one of the two logs has changed
    (the page asks once a second while a job works, and a rename's log of a big shoot is not small)."""
    studio = Path(studio)
    stamp = []
    for name in (join_shoots.LOG, "rename-log.json"):
        try:
            st = os.stat(studio / name)
            stamp.append((st.st_mtime_ns, st.st_size))
        except OSError:
            stamp.append(None)
    had = _HALF.get(str(studio))
    if had and had[0] == stamp:
        return had[1]
    try:
        out = join_shoots.half_done(studio)
    except (Exception, SystemExit):  # noqa: BLE001  a log half written this instant: asked again in a second
        return None
    _HALF[str(studio)] = (stamp, out)
    return out


_PROBE = threading.Lock()


def job_lock_file(tag):
    return JOBS / f"{tag}.lock"


def job_running(tag):
    """Is this backup's job at work right now? Told by the lock the job holds for as long as it lives (the
    computer lets go of it the moment the job dies, however it dies), never by its process number: after a
    power cut and a restart that number belongs to some other program. True, False, or None when this computer
    has no such locks."""
    with _PROBE:
        try:
            f = open(job_lock_file(tag), "ab")
        except OSError:
            return None
        try:
            got = this_computer.try_lock(f)
            if got:
                this_computer.unlock(f)
            return None if got is None else not got
        except OSError:
            return None
        finally:
            f.close()


try:
    from backup_lock import BEING_MADE
except ImportError:
    BEING_MADE = "This backup is still being made. Try this again when it's done."


def being_made(studio):
    """Is a backup that is running right now still working on this backup's folders?"""
    try:
        import backup_lock
        return bool(backup_lock.working_on(studio))
    except Exception:  # noqa: BLE001
        return False


def job_state(studio):
    """The job's record as it truly stands: "working" only while the job itself is alive."""
    d = job_read(studio)
    if not d:
        return None
    if d.get("state") == "problem" and BEING_MADE in str(d.get("line") or "") and not being_made(studio):
        return None             # "still being made" is no longer true: the backup is done, so the line goes
    if d.get("state") == "working":
        try:
            young = (datetime.now() - datetime.fromisoformat(d.get("started"))).total_seconds() < STARTING_GRACE
        except (TypeError, ValueError):
            young = False
        running = job_running(tag_of(studio))
        if running is None:      # no locks on this computer: the process number is all there is to go by
            alive = this_computer.still_running(d.get("pid")) if d.get("pid") else None
            dead = alive is False or (not d.get("pid") and not young)
        else:                    # a job that has written its number took the lock first: lock free means it is gone
            dead = not running and (bool(d.get("pid")) or not young)
        if dead:
            # The record and "is it still running?" are two looks, and a job that ended between them had its
            # lock free while the record in hand still said working: it was told as cut off ("Press Finish it")
            # though it had just finished (GitHub's Mac, Nov 23; the same fault mended in the reel and talking
            # jobs on Nov 17). So the record is read again, and only one that STILL says working is a stop.
            again = job_read(studio)
            if again and again.get("state") != "working":
                return job_state(studio)
            d = dict(d, state="stopped")
    if d.get("state") == "stopped":
        # what to do next is read from the drive's own logs now, never promised from memory: finish it, try
        # again, or (stopped on a problem, or twice over) tell the Assistant
        state = half_done(studio)
        d = dict(d, line=OUR_WORDS["needs_look"] if state == "stuck" else OUR_WORDS["half"] if state == "half"
                 else OUR_WORDS["stopped"])
    return d


def job_for_page(studio):
    d = job_state(studio)
    if not d:
        return None
    ask = d.get("ask") or {}
    return {"state": d.get("state"), "done": int(d.get("done") or 0), "total": int(d.get("total") or 0),
            "now": str(d.get("now") or ""), "mini": bool(ask.get("mini")), "finish": bool(ask.get("finish")),
            "line": str(d.get("line") or ""),
            "ask": {"names": ask.get("names") or {}, "mini": bool(ask.get("mini")), "mini_name": ask.get("mini_name") or ""}}


def start(studio, names, mini=False, mini_name="", finish=False):
    """Start the one background job for this backup. {"ok": True} or {"ok": False, "words": plain words}.
    finish: nothing new, only finish a join or a rename that was cut off (join_shoots.py --finish)."""
    studio = Path(studio)
    now_ = job_state(studio)
    if (now_ and now_.get("state") == "working") or job_running(tag_of(studio)):
        return {"ok": False, "words": OUR_WORDS["busy"]}
    if finish:
        names, mini, mini_name = {}, False, ""
    todo = [[i, n] for i, n in names.items()]
    rec = {"state": "working", "backup": backup_name(studio), "records": str(studio),
           "ask": dict({"names": names, "mini": bool(mini), "mini_name": mini_name}, **({"finish": True} if finish else {})),
           "todo": todo, "done": 0, "total": 1 if mini or finish else len(todo), "now": "", "line": "",
           "started": datetime.now().isoformat(timespec="seconds"), "finished": None, "pid": None}
    if not mini and not todo and not finish:
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
    if not why or "/" in why or "\\" in why or ".json" in why or ".py" in why:
        return fallback          # a path, or the name of a file of ours, is never put on a photographer's page
    return why


def run_job(tag):
    """The job itself: one shoot at a time, the record written whole after every step. It holds its own lock
    file for as long as it lives (job_running), and it writes how it ended ONCE, as the last thing it does: until
    then the record says "working", so a Save pressed while it winds up (the report being built again) is told to
    wait, never taken and then lost under this job's last write."""
    f = JOBS / f"{tag}.json"
    rec = _json(f)
    if not isinstance(rec, dict) or rec.get("state") != "working":
        return 0
    studio = Path(rec["records"])
    try:
        mine = open(job_lock_file(tag), "ab")
    except OSError:
        mine = None
    if mine is not None:
        end = time.time() + 10
        while True:
            got = this_computer.try_lock(mine)      # someone asking "is it at work?" holds it for an instant
            if got or got is None or time.time() > end:
                break
            time.sleep(0.05)
        if got is False:
            return 0                                # another job for this backup is alive: this one is not needed

    def note(**k):
        rec.update(k)
        join_shoots.write_json(f, rec)
    note(pid=os.getpid())
    quiet = {"creationflags": 0x08000000} if this_computer.WINDOWS else {}
    end_as = {}
    with join_shoots.held() as got:
        if not got:
            note(state="problem", line=OUR_WORDS["busy"], finished=datetime.now().isoformat(timespec="seconds"))
            return 1
        env = dict(os.environ, **{join_shoots.LOCK_HELD: "1"})
        ask = rec.get("ask") or {}

        def run(script, *args):
            r = subprocess.run([sys.executable, str(HERE / script), str(studio), *args],
                               capture_output=True, encoding="utf-8", errors="replace", env=env, **quiet)
            sys.stdout.write(r.stdout + r.stderr)
            sys.stdout.flush()
            if r.returncode == 0:
                return True
            # Refused in plain words before anything moved: that line. Anything else stopped part way: what to
            # do about it (finish it, try again, tell the Assistant) is read from the logs when the page asks.
            why = plain(r.stdout + r.stderr, "")
            end_as.update({"state": "problem", "line": OUR_WORDS["problem"].format(line=why)} if why
                          else {"state": "stopped", "line": ""})
            return False

        if ask.get("finish"):
            if run("join_shoots.py", "--finish"):
                note(done=1)
        elif ask.get("mini"):
            name = ask.get("mini_name") or WORDS["mini_default"]
            note(now=name)
            if run("join_shoots.py", "--all", "--name", name):
                note(done=1)
        else:
            for n, (sid, name) in enumerate(rec.get("todo") or []):
                note(now=name)
                if not run("rename_shoot.py", "--shoot", sid, "--name", name):
                    break
                note(done=n + 1)
        if not ask.get("mini"):
            try:    # the report shows the new names (a join builds it again itself)
                subprocess.run([sys.executable, str(HERE / "report_page.py"), str(studio)], capture_output=True,
                               encoding="utf-8", errors="replace", timeout=300, env=env, **quiet)
            except (OSError, subprocess.SubprocessError):
                pass
        cut_for_tests("before-last-write")
        note(**(end_as or {"state": "done", "now": ""}), finished=datetime.now().isoformat(timespec="seconds"))
    sys.stdout.flush()
    return 1 if end_as else 0


def cut_for_tests(point):
    """Tests only: hold the job at a named point for a few seconds (STUDIO_NAME_JOB_HOLD_FOR_TESTS=point:seconds)."""
    want = os.environ.get("STUDIO_NAME_JOB_HOLD_FOR_TESTS") or ""
    if want.partition(":")[0] == point:
        time.sleep(float(want.partition(":")[2] or 3))


# ---------------------------------------------------------------- the page

def page_html(backup):
    e = html.escape
    words = {k: W(k) for k in ("title", "title_done", "found", "found_one", "mini", "placeholder", "mini_placeholder",
                               "mini_default", "folder", "save", "later", "another", "another_note", "see_all",
                               "each_own", "one_folder", "saving", "saving_one", "saving_mini", "leave", "cant", "change", "half", "finish", "finishing",
                               "needs_look", "found_folder", "found_one_folder", "typed_before")}
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
        if being_made(studio):
            # refused here, as a passing line, with no job started and no record written (Nov 23 review: the job
            # was started, refused, and left "still being made" on the page long after the backup was done)
            return _answer(handler, {"ok": False, "words": OUR_WORDS["problem"].format(line=BEING_MADE)})
        with _SAVING:
            state = half_done(studio)
            if state == "stuck":
                return _answer(handler, {"ok": False, "words": OUR_WORDS["needs_look"]})
            if state == "half":
                # a join or a rename of this backup was cut off: whatever this page asked for, the one thing
                # done is finishing it (the page shows only Finish it; a page a step behind may still send names)
                return _answer(handler, start(studio, {}, finish=True))
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
