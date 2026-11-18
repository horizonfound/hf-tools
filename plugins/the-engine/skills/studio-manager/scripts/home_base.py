#!/usr/bin/env python3
"""The home base's two screens, and what they read (Nicole's v26, Nov 13; built Nov 14).

The home page (home.py, /home on the posting server; rebuilt after her v28) has the four steps in the order of the
work. Two of the steps have a screen of their own, and this file is both of them:

    /backups       Back up a card: what a backup does, the two steps, and "Your backups": every card backed up,
                   newest first (the 10 newest, Show older by month, a search by shoot name)
    /make-posts    Make posts from a shoot: what a post kit is ("What's a post kit?", her v27), the three steps
                   (the third happens inside the post kit), and "Your post kits" (the 20 newest, Show older, a
                   search, Archive by hand and Bring it back)

What they show is read fresh, and only read, from what the Assistant already keeps: the editing queue's record
of every backed-up shoot, each backup's own records wherever they are now (before or after it settled:
where.locate), its manifest (is the card safe to format, is there a second copy), the cards of one shoot linked
by shoot_report.py (shoot.json), and the kits in Your Content. Nothing new is stored but one small list:

    ~/.studio/kit-archive.json     {"archived": [kit folder names]}   (kit-archive.prev.json: the list before)

A kit that is archived is only on that list. No kit is ever moved, renamed or deleted.

Routes (all on the posting server, which checks who is asking first):
    GET  /backups, /make-posts     the two screens
    GET  /home-data                what they draw from (JSON; names and numbers, never a path)
    GET  /kit-thumb?kit=&i=        one of a kit's three small pictures, made the first time it is asked for
    POST /kit-archive              {"shoot": "<kit folder>", "archived": true|false}

    python3 home_base.py data      print what /home-data answers (for a look; changes nothing)

Her words are in WORDS, whole (tests/home_base_check.py compares them with her pages both ways). Ours, where
hers has none, are in OUR_WORDS, each a draft for Dustin and Nicole.
"""
import html
import json
import os
import sys
import threading
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import look  # noqa: E402  (the font, the colours and the rules every page shares)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
from where import locate, place_key  # noqa: E402
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
ARCHIVE = HOME / "kit-archive.json"
ARCHIVE_PREV = HOME / "kit-archive.prev.json"
RECENT_BACKUPS = 10
RECENT_KITS = 20
POST_CAP = 2000                 # a press on Archive is a few dozen bytes

# ---------- the words ----------
# Nicole's, from her three pages (pages/home-test.html and backups.html, v26; make-posts.html, v27, Nov 17), whole.
# <em> and <b> are hers too (the accent word, the bold start of a step, "post kit" in the lede). {…} is filled in
# by the page.
WORDS = {
    # the home page itself is home.py's (her v28 words are in home.WORDS); these are the lines its buttons share
    "see_report": "See the report",
    "opening_queue": "Opening your editing queue…",
    "opening": "Opening…",
    "opening_report": "Opening the report…",
    "not_running": "The Assistant isn't running right now. Ask your assistant to show the home page.",
    "copy": "Copy",
    "copied": "Copied",
    "back_home": "Back to home",
    # Back up a card
    "b_eyebrow": "Step 1 of your workflow",
    "b_h1": "Back up <em>a card.</em>",
    "b_lede_1": "This is where your assistant takes everything off your memory card and puts it safely on your hard drive. It copies every photo and double-checks each one against your card, so you know nothing got lost on the way. If your card has more than one shoot on it, it splits them into their own folders and names each one using your naming system, so they sit right next to your other shoots.",
    "b_lede_2": "It also picks six photos from each shoot that would be great to edit first and send your client as sneak peeks, and marks them \"sneak peek\" in Lightroom so they're easy to find. Nothing on your memory card is changed or deleted. Once the report says everything's safe, you can format it.",
    "b_steps": "How to back up a card",
    "b_s1": "<b>Put your memory card in.</b> Shooting with more than one card? Back them up one at a time; they'll show up together below.",
    "b_card_in": "A card is in: {name}, about {files} files.",
    "b_card_out": "No card in yet.",
    "b_s2": "<b>Paste this in the chat:</b>",
    "b_say": "backup now",
    "b_s2_small": "Your assistant asks a quick question or two, then you can walk away. The report is ready when you're back, and it shows up below.",
    "b_h2": "Your backups",
    "b_say_list": "Every card you've backed up, newest first. Open a shoot's folder to start editing, or see its report.",
    "b_find": "Find a shoot by name",
    "loading": "Loading…",
    "b_cant": "I can't reach the Assistant's records right now.",
    "st_waiting": "Waiting to be edited",
    "st_edited": "Edited",
    "st_just": "Just for you",
    "st_due": "To edit, {due}",
    "b_unplugged": "This one's on {drive}. Plug it in to open it.",
    "another_drive": "another drive",
    "b_moved": "I can't find this folder anymore. If you moved or renamed it in Finder, tell your assistant where it went.",
    "open_folder": "Open this folder",
    "card_n": "card {n}",
    "cards_n": "{n} cards",
    "safe": "{card} safe to format",
    "safe_card": "Card",
    "safe_cards": "Cards",
    "needs_look": "Something needs a look: see the report",
    "second_yes": "Second copy made",
    "second_no": "No second copy",
    "not_plugged": "On {drive}, not plugged in",
    "backed_up": "Backed up {day}",
    "b_none": "Nothing backed up yet. Your backups show up here.",
    "b_no_match": "No shoot called \"{q}\" yet.",
    "b_only": "Show only the 10 most recent",
    "b_older": "Show {n} older backup{s}",
    # Make posts from a shoot
    "m_eyebrow": "Step 3 of your workflow",
    "m_h1": "Make posts <em>from a shoot.</em>",
    "m_lede": "When your editing is done, start here. For each shoot you'd like to make posts from, we'll build you a <b>post kit</b>, and together we'll create your reels, carousels, single photos, stories and captions. Whatever you need to support your social media.",
    "m_what_h": "What's a post kit?",
    "m_what_p": "It's one place for everything you'll post from a shoot. Inside your post kit is where you make it all: build your reels, design your carousels and stories, and write your captions. When a piece is ready, it goes to your posting queue. Nothing is ever posted for you.",
    "m_steps": "How to make a post kit from a shoot",
    "m_s1": "<b>Choose the folder with your finished photos.</b>",
    "m_pick": "Select the folder with your finished photos",
    "m_s1_small": "Your assistant makes its own copies of the JPEGs in that folder. Your originals aren't moved or changed.",
    "m_picking": "Pick the folder in the window that just opened…",
    "m_s2": "<b>Then paste this in the chat:</b>",
    "m_say": "make my posts",
    "m_s2_small": "I'll bring your photos in and open your new post kit. You'll find it below any time, too.",
    "m_s3": "<b>Make your posts inside your post kit.</b>",
    "m_s3_small": "Pick what you want to make: a reel, a carousel, stories or a caption. Each one walks you through it.",
    "m_h2": "Your post kits",
    "m_say_list": "Your most recent shoots, newest first. Click one to open its post kit. When a shoot's posts are done, archive it to tidy this list; nothing is deleted.",
    "m_find": "Find a post kit by shoot name",
    "m_cant": "I can't reach your shoots right now.",
    "open_kit": "Open the post kit",
    "archive": "Archive",
    "bring_back": "Bring it back",
    "no_date": "No date",
    "m_no_match": "No post kit called \"{q}\" yet.",
    "m_none": "No post kits yet. Choose a folder of finished photos above to make your first.",
    "m_only": "Show only the 20 most recent",
    "m_older": "Show {n} older post kit{s}",
    "archived_n": "Archived ({n})",
    "didnt_work": "That didn't work.",
    "not_a_kit": "That shoot isn't in your content folder.",
}

# Ours, where hers has none. Each is a draft for Dustin and Nicole.
OUR_WORDS = {
    # a sample backup (night.py --sample, for tests) is never called safe to format; the report's own words
    "sample_keep": "Keep the card: this was a sample",
    # a backed-up shoot that holds video clips: a clip is never called a photo (Dustin, Nov 11)
    "clips": "video clip",
    # the home page saved as a file (home.py page), which can't ask the Assistant anything
    "offline": "This is a saved copy. Ask your assistant to “show the Assistant” for the live one.",
    # the phone-width Back to home button, as on every other page
    "home_short": "Home",
}


def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key]


# ---------- the look: Nicole's home-test.css, in the Assistant's own colours and font (look.py) ----------
CSS = r"""
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 4rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand{white-space:nowrap}.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2);text-align:right}
.bar .homelink .short{display:none}@media(max-width:560px){.bar .homelink .long{display:none}.bar .homelink .short{display:inline}}
.head{padding:clamp(2rem,5vw,3.2rem) 0 .8rem;display:grid;gap:.6rem}
h1{margin:0;font:600 clamp(32px,4.6vw,54px)/1.03 var(--sans);letter-spacing:-.035em}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:42em}
.lede.wide{max-width:none}.head .lede+.lede{margin-top:.2rem}
.offline{margin:0;color:var(--coral-2);font-size:14px}
.sec{margin-top:2rem}.sec h2{margin:0 0 .3rem;font:600 13px/1.3 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.sec .say{margin:0;color:var(--ink-2);font-size:14.5px}
.todayl{display:grid;gap:.5rem;margin:.6rem 0 0;padding:0;list-style:none}
.todayl li{display:flex;gap:.6rem;align-items:baseline;font-size:15px;min-width:0}
.todayl li>span{min-width:0;overflow-wrap:anywhere}
.todayl li::before{content:'';width:8px;height:8px;border-radius:50%;background:var(--ocean);flex:none;transform:translateY(-1px)}
.todayl li.late::before{background:#C2412D}.todayl li.soon::before{background:#D9A400}.todayl li.card::before{background:var(--coral)}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:14px;padding:.9rem 0 .4rem}
.item{position:relative;display:grid;gap:.45rem;align-content:start;text-align:left;padding:20px 22px;border:0;border-radius:20px;background:var(--paper);box-shadow:0 1px 0 var(--line);cursor:pointer;font:inherit;color:inherit;text-decoration:none;transition:transform .3s var(--ease),box-shadow .3s var(--ease)}
.item:hover{transform:translateY(-3px);box-shadow:0 0 0 2px var(--coral),0 12px 32px rgba(31,36,48,.10)}
.item .k{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--coral-l);color:var(--coral-2);font:700 12.5px/1 var(--sans)}
.item .n{font:600 20px/1.15 var(--sans);letter-spacing:-.02em}.item .n em{font:inherit;font-style:normal;color:var(--coral-2)}
.item p{margin:0;color:var(--ink-2);font-size:14.5px}
.item .go{font:600 13px/1 var(--sans);color:var(--coral-2);margin-top:.2rem}
.item.minor{background:transparent;box-shadow:inset 0 0 0 1.5px var(--line)}
.btn{display:inline-flex;align-items:center;gap:.4rem;font:600 13px/1 var(--sans);padding:9px 13px;border-radius:999px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer;text-decoration:none}
.btn:hover{border-color:var(--ink)}.btn.solid{background:var(--ink);color:#fff;border-color:var(--ink)}.btn.solid:hover{background:var(--coral-2);border-color:var(--coral-2)}
.btn.coral{background:var(--coral);color:var(--ink);border-color:var(--coral)}.btn[disabled]{opacity:.55;cursor:default}
.whatkit{margin:.4rem 0 1.4rem;padding:1rem 1.2rem;border-radius:18px;background:var(--paper);box-shadow:0 1px 0 var(--line);max-width:52em;min-width:0}
.whatkit .wk-h{margin:0 0 .25rem;font:600 15px/1.3 var(--sans)}
.whatkit p{margin:0;color:var(--ink-2);font-size:15px;line-height:1.55;overflow-wrap:anywhere}
.steps-title{margin:1.6rem 0 0;font:600 13px/1.3 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.steps{border-radius:22px;padding:22px 26px;margin-top:1.2rem;display:grid;gap:1rem;background:var(--paper);color:var(--ink);box-shadow:0 1px 0 var(--line),0 0 0 2px var(--coral-l)}
.steps .st{display:grid;grid-template-columns:32px minmax(0,1fr);gap:.8rem;align-items:start}
.steps .num{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--coral);color:#fff;font:700 14px/1 var(--sans)}
.steps b{color:var(--ink)}.steps p{margin:.1rem 0 .5rem;font-size:15.5px}.steps small{color:var(--ink-2);font-size:13px}
.steps small.block{display:block;margin-top:.5rem}
.steps .status{color:var(--coral-2);font:600 13.5px/1.4 var(--sans);overflow-wrap:anywhere}
.steps .st>div{min-width:0}
.paste{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:.4rem}
.paste .words{font:500 17px/1 var(--sans);background:var(--cream);color:var(--ink);padding:11px 14px;border-radius:12px;border:1.5px solid var(--line)}
.paste .copy{font:600 13px/1 var(--sans);padding:11px 16px;border-radius:999px;border:0;background:var(--ink);color:#fff;cursor:pointer}.paste .copy:hover{background:var(--coral-2)}
.note{display:block;font-size:13px;color:var(--ink-2);margin-top:6px;min-height:1em}.steps .note{color:var(--coral-2)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(240px,100%),1fr));gap:12px;padding:.8rem 0 .4rem}
.shoot{display:grid;gap:.5rem;align-content:start;padding:12px;border-radius:18px;background:var(--paper);box-shadow:0 1px 0 var(--line);min-width:0}
.shoot .ph{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.shoot .ph img,.shoot .ph i{display:block;width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;background:var(--sand-l)}
.shoot b{font:600 15px/1.25 var(--sans);overflow-wrap:anywhere}.shoot small{color:var(--ink-2);font-size:12.5px}
.shoot .acts{display:flex;gap:6px;flex-wrap:wrap}
.backup{background:var(--paper);border-radius:22px;padding:1.1rem 1.2rem 1rem;margin-top:1rem;box-shadow:0 1px 0 var(--line)}
.backup .top{display:flex;align-items:center;justify-content:space-between;gap:.8rem;flex-wrap:wrap}
.backup h3{margin:0;font:600 19px/1.2 var(--sans);letter-spacing:-.01em;overflow-wrap:anywhere}.backup .meta{color:var(--ink-2);font-size:13.5px;overflow-wrap:anywhere}
.backup .top>div{min-width:0}
.backup .cards{grid-template-columns:repeat(auto-fill,minmax(min(220px,100%),1fr))}
.backup .shoot{background:var(--cream);box-shadow:none}
.empty{color:var(--ink-2);font-size:15px;padding:.6rem 0;overflow-wrap:anywhere}
details.arch{margin-top:1.4rem}details.arch summary{cursor:pointer;font:600 14px/1.3 var(--sans);color:var(--ink-2)}
.more{margin-top:.6rem}
.find{margin:.8rem 0 .2rem}.find input{width:100%;max-width:420px;font:500 15px/1.2 var(--sans);padding:.7rem 1rem;border-radius:999px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink)}
.find input:focus{outline:none;border-color:var(--coral)}
.pill{display:inline-block;max-width:100%;font:600 11.5px/1.2 var(--sans);padding:6px 9px;border-radius:999px;background:var(--sand-l);color:var(--ink-2)}
.shoot .pill{width:max-content}
.pill.ok{background:var(--long-l);color:var(--long)}.pill.soon{background:var(--sun-l);color:#8A6A00}.pill.late{background:#F8E1DC;color:#C2412D}
.flags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.acts.stack{flex-direction:column;align-items:stretch}.acts.stack .btn{justify-content:center}
.shoot .warn{margin:0;font-size:13px;color:var(--coral-2);line-height:1.4}
h3.month{margin:1.6rem 0 0;font:600 14px/1.3 var(--sans);color:var(--ink-2)}
"""

# What the home page and both screens share (Nicole's home-test.js, without her test-only lines).
JS_SHARED = r"""
const $ = id => document.getElementById(id);
const live = location.protocol.startsWith('http');
const esc = t => String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const fill = (t, o) => String(t).replace(/\{(\w+)\}/g, (m, k) => (o && k in o) ? o[k] : m);
const many = n => Number(n).toLocaleString('en-US');
// The app's browser pane refuses navigator.clipboard but honors execCommand('copy') from a click (Dustin, Oct 30).
function copyText(t){
  try { const a = document.createElement('textarea'); a.value = t; a.setAttribute('readonly', ''); a.style.cssText = 'position:fixed;top:0;left:0;opacity:0'; document.body.appendChild(a); a.focus(); a.select(); const ok = document.execCommand('copy'); a.remove(); if (ok) return true; } catch (e) {}
  if (navigator.clipboard) { navigator.clipboard.writeText(t).catch(() => {}); return true; }
  return false;
}
function wireCopies(root){
  (root || document).querySelectorAll('.copy').forEach(b => b.onclick = () => { if (copyText(b.dataset.copy)) { b.textContent = W.copied; setTimeout(() => b.textContent = W.copy, 1500); } });
}
function note(el, t){ let m = el.nextElementSibling; if (!m || !m.classList.contains('note')) { m = document.createElement('span'); m.className = 'note'; el.after(m); } m.textContent = t; }
async function assistant(path, el, wait){         // one of the Assistant's own actions (open a folder, a report, pick a folder)
  if (el && wait) note(el, wait);
  if (!live) { if (el) note(el, W.not_running); return; }
  try { const r = await fetch(path, {cache: 'no-store'}); const d = await r.json(); if (d.url) { location.href = d.url; return d; } if (el) note(el, d.words || ''); return d; }
  catch (e) { if (el) note(el, W.not_running); }
}
function clicked(item){ if (!live) return; try { fetch('/clicked', {method: 'POST', keepalive: true, headers: {'Content-Type': 'application/json'}, body: JSON.stringify({item})}).catch(() => {}); } catch (e) {} }
function niceDay(iso){ try { const d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); if (isNaN(d)) return ''; return d.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'}); } catch (e) { return ''; } }
function monthOf(iso){ try { const d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); if (isNaN(d)) return ''; return d.toLocaleDateString('en-US', {month: 'long', year: 'numeric'}); } catch (e) { return ''; } }
// "212 photos and 6 video clips": a clip is never called a photo (clips.words, in the page's own hand)
function countWords(p, c){ p = p || 0; c = c || 0; const a = many(p) + ' photo' + (p === 1 ? '' : 's'), b = many(c) + ' ' + W.clips + (c === 1 ? '' : 's'); return (p && c) ? a + ' and ' + b : (c ? b : a); }
async function homeData(){ const r = await fetch('/home-data', {cache: 'no-store'}); if (!r.ok) throw new Error('no'); return r.json(); }
// When anything the page shows may have changed (a backup lands, a kit is made, a card goes in), ask again.
function watch(stamp, again){ if (!live) return; let last = stamp; setInterval(async () => { try { const r = await fetch('/home-state', {cache: 'no-store'}); const t = (await r.text()).trim(); if (t && last && t !== last) { last = t; again(); } else if (t && !last) last = t; } catch (e) {} }, 4000); }
"""

JS_BACKUPS = r"""
wireCopies();
const RECENT = %(recent)d;
const STATUS = {waiting: W.st_waiting, finished: W.st_edited, archived: W.st_just};
let GROUPS = [], showAll = false, got = false;
const seg = t => String(t).split('/').map(encodeURIComponent).join('/');

function shootCard(s, cardLabel){
  const th = (s.thumbs || []).map(t => `<img src="/${esc(seg(t))}" alt="" loading="lazy">`).join('') + '<i></i>'.repeat(Math.max(0, 3 - (s.thumbs || []).length));
  const meta = [s.shot ? niceDay(s.shot) : '', (s.count || s.clips) ? countWords(s.count, s.clips) : '', cardLabel || ''].filter(Boolean).join(' · ');
  // where it stands: waiting to be edited (and when it's due), edited, or just for you
  let st = STATUS[s.status] || '';
  if (s.status === 'waiting' && s.due) st = fill(W.st_due, {due: s.due});
  const stCls = s.late ? 'late' : s.status === 'waiting' ? 'soon' : s.status === 'finished' ? 'ok' : '';
  let acts;
  if (!s.plugged) acts = `<p class="warn">${esc(fill(W.b_unplugged, {drive: s.drive || W.another_drive}))}</p>`;
  else if (!s.found) acts = `<p class="warn">${esc(W.b_moved)}</p>`;
  else acts = `<button class="btn solid" data-open="${esc(s.id)}">${esc(W.open_folder)}</button><button class="btn" data-report="${esc(s.id)}">${esc(W.see_report)}</button>`;
  return `<div class="shoot"><div class="ph">${th}</div><b>${esc(s.name)}</b><small>${esc(meta)}</small>
    ${st ? `<span class="pill ${stCls}">${esc(st)}</span>` : ''}
    <div class="acts stack">${acts}</div></div>`;
}
function groupCard(g){
  const bs = g.backups, first = bs[bs.length - 1];
  const shoots = bs.flatMap(b => b.shoots.map(s => ({s, card: bs.length > 1 ? fill(W.card_n, {n: b.card_no}) : ''})));
  const ph = shoots.reduce((a, x) => a + (x.s.count || 0), 0), cl = shoots.reduce((a, x) => a + (x.s.clips || 0), 0);
  const cards = bs.length > 1 ? fill(W.cards_n, {n: bs.length}) + ' · ' : '';
  // the backup at a glance: is the card safe to format, is there a second copy
  const flags = [];
  if (bs.every(b => b.safe === true)) flags.push(`<span class="pill ok">${esc(fill(W.safe, {card: bs.length > 1 ? W.safe_cards : W.safe_card}))}</span>`);
  else if (bs.some(b => b.safe === false)) flags.push(`<span class="pill late">${esc(W.needs_look)}</span>`);
  if (bs.some(b => b.sample)) flags.push(`<span class="pill soon">${esc(W.sample_keep)}</span>`);        // a sample is never "safe to format"
  if (bs.some(b => b.known)) flags.push(bs.every(b => b.second) ? `<span class="pill ok">${esc(W.second_yes)}</span>` : `<span class="pill">${esc(W.second_no)}</span>`);
  if (!first.plugged) flags.push(`<span class="pill">${esc(fill(W.not_plugged, {drive: first.drive || W.another_drive}))}</span>`);
  return `<div class="backup"><div class="top"><div><h3>${esc(fill(W.backed_up, {day: niceDay(g.added)}))}</h3>
    <span class="meta">${esc(cards)}${shoots.length} shoot${shoots.length === 1 ? '' : 's'} · ${esc(countWords(ph, cl))}</span></div>
    <div class="flags">${flags.join('')}</div></div>
    <div class="cards">${shoots.map(x => shootCard(x.s, x.card)).join('')}</div></div>`;
}
function render(){
  const q = $('find').value.trim().toLowerCase();
  let list = GROUPS;
  if (q) list = GROUPS.map(g => ({...g, backups: g.backups.map(b => ({...b, shoots: b.shoots.filter(s => String(s.name).toLowerCase().includes(q))})).filter(b => b.shoots.length)})).filter(g => g.backups.length);
  if (!GROUPS.length) { $('backups').innerHTML = `<p class="empty">${esc(W.b_none)}</p>`; $('olderBox').innerHTML = ''; return; }
  if (!list.length) { $('backups').innerHTML = `<p class="empty">${esc(fill(W.b_no_match, {q: $('find').value.trim().toLowerCase()}))}</p>`; $('olderBox').innerHTML = ''; return; }
  const shown = (q || showAll) ? list : list.slice(0, RECENT);
  let html = '', lastMonth = '';
  shown.forEach((g, i) => {
    if (i >= RECENT || (q && shown.length > RECENT)) { const m = monthOf(g.added); if (m !== lastMonth) { html += `<h3 class="month">${esc(m)}</h3>`; lastMonth = m; } }
    html += groupCard(g);
  });
  $('backups').innerHTML = html;
  const older = list.length - RECENT;
  $('olderBox').innerHTML = (!q && older > 0) ? `<button class="btn more" id="older">${esc(showAll ? W.b_only : fill(W.b_older, {n: older, s: older === 1 ? '' : 's'}))}</button>` : '';
  if ($('older')) $('older').onclick = () => { showAll = !showAll; render(); };
  document.querySelectorAll('[data-open]').forEach(x => x.onclick = () => assistant('/open-shoot?id=' + encodeURIComponent(x.dataset.open), x, W.opening));
  document.querySelectorAll('[data-report]').forEach(x => x.onclick = () => assistant('/report-url?id=' + encodeURIComponent(x.dataset.report), x, W.opening_report));
}
async function load(){
  let g;
  try { g = await homeData(); } catch (e) { if (!got) $('backups').innerHTML = `<p class="empty">${esc(W.b_cant)}</p>`; return; }
  $('cardStatus').textContent = g.card ? fill(W.b_card_in, {name: g.card.name, files: many(g.card.files)}) : W.b_card_out;
  // the backups could not be read just now: the list as it last was stays, or her "can't reach" line; an empty
  // list here would say "Nothing backed up yet", which is not true
  if (g.problem_backups) { if (!got) { $('backups').innerHTML = `<p class="empty">${esc(W.b_cant)}</p>`; $('olderBox').innerHTML = ''; } return g; }
  got = true;
  GROUPS = g.groups || [];
  render();
  return g;
}
$('find').oninput = render;
load().then(g => watch(g && g.stamp, load));
"""

JS_MAKE = r"""
wireCopies();
const RECENT = %(recent)d;
let KITS = [], showAll = false, got = false;
const card = k => {
  const enc = encodeURIComponent(k.folder);
  const th = [1, 2, 3].map(i => `<img src="/kit-thumb?kit=${enc}&i=${i}" alt="" loading="lazy" onerror="this.replaceWith(document.createElement('i'))">`).join('');
  const meta = [k.date ? niceDay(k.date) : '', k.photos ? `${many(k.photos)} photo${k.photos === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ');
  return `<div class="shoot"><div class="ph">${th}</div><b>${esc(k.name)}</b><small>${esc(meta)}</small>
    <div class="acts"><a class="btn solid" href="/content/${enc}/Post%%20kit.html">${esc(W.open_kit)}</a>
    <button class="btn" data-arch="${esc(k.folder)}" data-to="${k.archived ? '0' : '1'}">${esc(k.archived ? W.bring_back : W.archive)}</button></div></div>`;
};
function render(){
  const q = $('find').value.trim().toLowerCase();
  const match = k => !q || String(k.name).toLowerCase().includes(q) || String(k.folder).toLowerCase().includes(q);
  const allLive = KITS.filter(k => !k.archived), live_ = allLive.filter(match), arch = KITS.filter(k => k.archived && match(k));
  const shown = (showAll || q) ? live_ : live_.slice(0, RECENT);
  // the 20 most recent in one grid; older ones (Show older, or a search) under their month (Nicole, Nov 13)
  const first = shown.slice(0, RECENT), rest = shown.slice(RECENT);
  let html = first.length ? `<div class="cards">${first.map(card).join('')}</div>` : '';
  let month = null, buf = [];
  const flush = () => { if (buf.length) { html += `<h3 class="month">${esc(month)}</h3><div class="cards">${buf.map(card).join('')}</div>`; buf = []; } };
  rest.forEach(k => { const m = (k.date && monthOf(k.date)) || W.no_date; if (m !== month) { flush(); month = m; } buf.push(k); });
  flush();
  $('recent').innerHTML = html || `<p class="empty">${esc(q ? fill(W.m_no_match, {q}) : W.m_none)}</p>`;
  const older = live_.length - RECENT;
  $('olderBox').innerHTML = (!q && older > 0) ? `<button class="btn more" id="older">${esc(showAll ? W.m_only : fill(W.m_older, {n: older, s: older === 1 ? '' : 's'}))}</button>` : '';
  if ($('older')) $('older').onclick = () => { showAll = !showAll; render(); };
  $('archBox').hidden = !arch.length;
  $('archSum').textContent = fill(W.archived_n, {n: arch.length});
  $('archived').innerHTML = arch.map(card).join('');
  document.querySelectorAll('[data-arch]').forEach(b => b.onclick = async () => {
    b.disabled = true;
    try {
      const r = await fetch('/kit-archive', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({shoot: b.dataset.arch, archived: b.dataset.to === '1'})}).then(r => r.json());
      if (!r.ok) throw new Error(r.problem || '');
      KITS.forEach(k => k.archived = r.archived.includes(k.folder)); render();
    } catch (e) { b.disabled = false; note(b.closest('.acts') || b, e.message || W.didnt_work); }
  });
}
async function load(){
  let g;
  try { g = await homeData(); } catch (e) { if (!got) $('recent').innerHTML = `<p class="empty">${esc(W.m_cant)}</p>`; return; }
  if (g.problem_kits) { if (!got) { $('recent').innerHTML = `<p class="empty">${esc(W.m_cant)}</p>`; $('olderBox').innerHTML = ''; } return g; }
  got = true;
  KITS = g.kits || []; render();
  return g;
}
$('find').oninput = render;
load().then(g => { if (location.hash === '#kits') $('kits').scrollIntoView(); watch(g && g.stamp, load); });
$('pick').onclick = () => { clicked('posts'); assistant('/pick-folder', $('pick'), W.m_picking); };
"""


def words_js():
    """Every line a page's script may show, as one object. "</" never ends the script early."""
    d = dict(WORDS)
    d.update(OUR_WORDS)
    return "const W = " + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + ";"


def back_home():
    return ("<a class='homelink' href='/home'><span aria-hidden='true'>&larr;</span>"
            f"<span class='long'>{html.escape(W('back_home'))}</span><span class='short'>{html.escape(W('home_short'))}</span></a>")


def today_words():
    try:
        import edit_queue
        d = edit_queue.today()
    except Exception:  # noqa: BLE001
        d = date.today()
    return d.strftime("%A, %B ") + str(d.day)


def _page(title, body, script):
    e = html.escape
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(brand.title(title))}</title><style>{look.head_css()}{CSS}</style></head><body>"
            f"<div class='wrap'><div class='bar'>{back_home()}{brand.bar()}<span class='when'>{e(today_words())}</span></div>"
            f"{body}</div><script>{words_js()}{JS_SHARED}{script}</script></body></html>")


def _paste(words):
    e = html.escape
    return (f"<div class='paste'><span class='words'>{e(words)}</span>"
            f"<button class='copy' data-copy='{e(words, quote=True)}'>{e(W('copy'))}</button></div>")


def backups_html():
    e = html.escape
    body = (f"<header class='head'><span class='eyebrow'>{e(W('b_eyebrow'))}</span><h1>{W('b_h1')}</h1>"
            f"<p class='lede wide'>{e(W('b_lede_1'))}</p><p class='lede wide'>{e(W('b_lede_2'))}</p></header>"
            f"<p class='steps-title'>{e(W('b_steps'))}</p><div class='steps light'>"
            f"<div class='st'><span class='num'>1</span><div><p>{W('b_s1')}</p><span class='status' id='cardStatus'></span></div></div>"
            f"<div class='st'><span class='num'>2</span><div><p>{W('b_s2')}</p>{_paste(W('b_say'))}<small>{e(W('b_s2_small'))}</small></div></div></div>"
            f"<section class='sec'><h2>{e(W('b_h2'))}</h2><p class='say'>{e(W('b_say_list'))}</p>"
            f"<div class='find'><input id='find' type='search' placeholder='{e(W('b_find'), quote=True)}' aria-label='{e(W('b_find'), quote=True)}'></div>"
            f"<div id='backups'><p class='empty'>{e(W('loading'))}</p></div><div id='olderBox'></div></section>")
    return _page("Back up a card", body, JS_BACKUPS % {"recent": RECENT_BACKUPS})


def make_posts_html():
    e = html.escape
    body = (f"<header class='head'><span class='eyebrow'>{e(W('m_eyebrow'))}</span><h1>{W('m_h1')}</h1>"
            f"<p class='lede wide'>{W('m_lede')}</p></header>"
            f"<div class='whatkit'><p class='wk-h'>{e(W('m_what_h'))}</p><p>{e(W('m_what_p'))}</p></div>"
            f"<p class='steps-title'>{e(W('m_steps'))}</p><div class='steps light'>"
            f"<div class='st'><span class='num'>1</span><div><p>{W('m_s1')}</p>"
            f"<button class='btn coral' id='pick'>{e(W('m_pick'))}</button><small class='block'>{e(W('m_s1_small'))}</small></div></div>"
            f"<div class='st'><span class='num'>2</span><div><p>{W('m_s2')}</p>{_paste(W('m_say'))}<small>{e(W('m_s2_small'))}</small></div></div>"
            f"<div class='st'><span class='num'>3</span><div><p>{W('m_s3')}</p><small>{e(W('m_s3_small'))}</small></div></div></div>"
            f"<section class='sec' id='kits'><h2>{e(W('m_h2'))}</h2><p class='say'>{e(W('m_say_list'))}</p>"
            f"<div class='find'><input id='find' type='search' placeholder='{e(W('m_find'), quote=True)}' aria-label='{e(W('m_find'), quote=True)}'></div>"
            f"<div id='recent'><p class='empty'>{e(W('loading'))}</p></div><div id='olderBox'></div>"
            f"<details class='arch' id='archBox' hidden><summary id='archSum'>{e(W('archived_n').format(n=0))}</summary><div class='cards' id='archived'></div></details></section>")
    return _page("Make posts", body, JS_MAKE % {"recent": RECENT_KITS})


# ---------- what the screens read ----------

def records_of(spelled):
    """The records folder of a backup, wherever it is now (before or after it settled), or None when it can't be
    found (the drive unplugged, the records gone)."""
    if not spelled:
        return None
    p = Path(spelled)
    for cand in ([p, p.parent] if p.name == "_studio" else [p]):
        try:
            return locate(cand)[1]
        except (SystemExit, OSError):
            continue
    return None


def drive_here(path):
    """(the drive's name, is it plugged in) for a folder that isn't there. A folder on no named drive (the
    computer's own disk) is (None, True): it was moved or renamed, not unplugged."""
    try:
        name = this_computer.drive_words(path)
    except Exception:  # noqa: BLE001
        name = None
    if not name:
        return None, True
    p = Path(path)
    try:
        if this_computer.WINDOWS and p.drive:
            return name, os.path.exists(p.drive + "\\")
        parts = p.parts
        return name, Path(parts[0], parts[1], parts[2]).is_dir()
    except (OSError, IndexError):
        return name, False


_STATUS = {}                    # a manifest read once per change (it can be a megabyte for a full card)
_STATUS_LOCK = threading.Lock()


def backup_status(studio):
    """How a backup stands, from its own manifest: {"known", "safe", "second", "sample"}.
    safe: True only when it finished with no problems, every file's copy checked (the second copy too, when there
    is one), and it was not a sample; False when it has not finished or something went wrong; None for a sample
    that is otherwise fine (a sample is never called safe to format), and when the manifest can't be read."""
    f = Path(studio) / "manifest.json"
    try:
        st = f.stat()
        key = (str(f), st.st_mtime_ns, st.st_size)
    except OSError:
        return {"known": False, "safe": None, "second": False, "sample": False}
    with _STATUS_LOCK:
        if key in _STATUS:
            return dict(_STATUS[key])
    out = {"known": False, "safe": None, "second": False, "sample": False}
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
        files = m.get("files") or {}
        second = bool(m.get("second"))
        good = (bool(m.get("finished")) and not m.get("problems") and bool(files)
                and all((v.get("dest") or {}).get("ok") for v in files.values())
                and (not second or all((v.get("second") or {}).get("ok") for v in files.values())))
        sample = bool(m.get("sample"))
        out = {"known": True, "safe": (None if sample else True) if good else False,
               "second": second and all((v.get("second") or {}).get("ok") for v in files.values()) and bool(files),
               "sample": sample}
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    with _STATUS_LOCK:
        if len(_STATUS) > 2000:
            _STATUS.clear()
        _STATUS[key] = dict(out)
    return out


def _thumb_ok(t):
    """A shoot's small picture as the queue itself writes it ("queue-thumbs/<id>/0.jpg"), and nothing else: never
    an absolute path, never ".." (a queue file changed by hand must not put a path on the page)."""
    if not isinstance(t, str) or not t.startswith("queue-thumbs/") or "\\" in t:
        return False
    parts = t.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    try:
        return (HOME / t).is_file()
    except (OSError, ValueError):
        return False


def _due(edit_queue, iso):
    """A due date in the queue's own words; None for none, and for one that is not a day (a shoot is still shown)."""
    try:
        return edit_queue.due_words(iso) if iso else None
    except (ValueError, TypeError):
        return None


_RANK = {"waiting": 0, "finished": 1, "archived": 2}


def backups(q=None):
    """Every backup the editing queue knows, as the Back up a card screen shows them: the cards of one shoot
    together (linked by shoot_report.py, never by name), newest first. Names and numbers only, never a path.
    A backup is its records folder as it is found NOW: two queue records that spell one backup's records two ways
    (the day folder it settled out of, and where it settled to) are one backup, never "2 cards". One odd record
    in the queue is left out; it never takes the other backups with it."""
    import edit_queue
    import shoot_report
    q = q or edit_queue.load()
    today = edit_queue.today().isoformat()
    by, found_at = {}, {}
    for s in q.get("shoots") or []:
        try:
            if not isinstance(s, dict) or not s.get("studio") or not isinstance(s["studio"], str):
                continue
            if s["studio"] not in found_at:                     # each spelling looked up once
                found_at[s["studio"]] = records_of(s["studio"])
            rec = found_at[s["studio"]]
            try:
                folder = edit_queue.folder_of(s)
            except Exception:  # noqa: BLE001
                folder = None
            found = bool(folder) and folder.is_dir()
            drive, plugged = (None, True) if found else drive_here(folder or s.get("folder") or s["studio"])
            st = s.get("status", "waiting")
            st = st if st in ("waiting", "finished") else "archived"
            due = s.get("due") if (st == "waiting" and isinstance(s.get("due"), str)) else None
            shoot = {
                "id": str(s["id"]), "name": str(s.get("name") or ""), "shot": s.get("shot") if isinstance(s.get("shot"), str) else None,
                "count": s.get("count") if isinstance(s.get("count"), int) else 0, "clips": s.get("clips") if isinstance(s.get("clips"), int) else 0,
                "status": st, "due": _due(edit_queue, due), "late": bool(due) and due < today,
                "thumbs": [t for t in (s.get("thumbs") or [])[:3] if _thumb_ok(t)],
                "drive": drive, "plugged": plugged, "found": found}
            added = s.get("added") if isinstance(s.get("added"), str) else ""
        except Exception:  # noqa: BLE001
            continue
        b = by.setdefault(place_key(rec or s["studio"]), {"studio": s["studio"], "rec": rec, "added": "", "shoots": [], "_ids": {}})
        b["added"] = max(b["added"], added)
        # the same shoot of the same backup listed twice in the queue (once per spelling) shows once: the one
        # still to edit, else the delivered one, else the first
        sid = s.get("shoot")
        if rec and isinstance(sid, str) and sid in b["_ids"]:
            at = b["_ids"][sid]
            if _RANK[shoot["status"]] < _RANK[b["shoots"][at]["status"]]:
                b["shoots"][at] = shoot
            continue
        if rec and isinstance(sid, str):
            b["_ids"][sid] = len(b["shoots"])
        b["shoots"].append(shoot)
    groups = {}
    for b in by.values():
        rec = b.pop("rec")
        b.pop("_ids", None)
        key, card_no = place_key(rec or b["studio"]), 1
        if rec:
            b.update(backup_status(rec))
            b["drive"], b["plugged"] = None, True
            try:
                link = shoot_report.read(rec, heal=False)
            except Exception:  # noqa: BLE001
                link = None
            if link:
                # one shoot on several cards: every card of it carries the same list, so the first card's own
                # records (wherever they are now) name the group
                me = next((c for c in link["cards"] if c.get("found") and place_key(c["found"]) == place_key(rec)), None)
                first = min(link["cards"], key=lambda c: c.get("card") or 0)
                if me:
                    card_no = int(me.get("card") or 1)
                    key = "shoot:" + place_key(first.get("found") or first.get("records") or rec)
        else:
            b.update({"known": False, "safe": None, "second": False, "sample": False})
            b["drive"], b["plugged"] = drive_here(b["studio"])
        b["card_no"] = card_no
        g = groups.setdefault(key, {"added": "", "backups": []})
        g["added"] = max(g["added"], b["added"])
        g["backups"].append(b)
    out = []
    for g in groups.values():
        g["backups"].sort(key=lambda b: (b["card_no"], b["added"]))
        for b in g["backups"]:
            b.pop("studio", None)
        out.append(g)
    out.sort(key=lambda g: g["added"], reverse=True)
    return out


def kits():
    """Every shoot folder in Your Content that holds a kit record, newest first, with whether it is archived.
    A kit whose page was never written is listed too (the page is built when it is opened)."""
    import posts
    h = posts.home()
    if not h:
        return []
    arch = archived()
    out = []
    for k in posts.kits(h):
        d = Path(k["path"])
        if d.is_symlink() or not (d / ".kit" / "kit.json").is_file():
            continue                                    # not a kit the page could open
        try:                                            # pictures only (a stray text file in Photos is no photo), and
            import kit as kit_mod                       # a kit that points at the folder Lightroom exported to
            photos = len(kit_mod.photo_files(kit_mod.photos_dir(d)))
        except (Exception, SystemExit):  # noqa: BLE001
            photos = 0
        day = k.get("date") if isinstance(k.get("date"), str) else ""
        out.append({"folder": k["folder"], "name": str(k.get("name") or k["folder"]), "date": day or "", "photos": photos,
                    "archived": k["folder"] in arch})
    out.sort(key=lambda k: (k["date"], k["folder"]), reverse=True)
    return out


def data():
    """What /home-data answers. Each part fails soft, like the home page."""
    import home
    out = {"ok": True, "today": today_words(), "card": None, "groups": [], "kits": [], "stamp": ""}
    try:
        out["card"] = home.card_in()
    except Exception:  # noqa: BLE001
        pass
    try:
        out["groups"] = backups()
    except (Exception, SystemExit) as e:  # noqa: BLE001  (an unreadable queue.json ends edit_queue.load with SystemExit)
        out["problem_backups"] = e.__class__.__name__       # the Back up a card screen then says it can't reach them,
    try:                                                    # never "Nothing backed up yet"; the kits still show
        out["kits"] = kits()
    except (Exception, SystemExit) as e:  # noqa: BLE001
        out["problem_kits"] = e.__class__.__name__
    try:
        out["stamp"] = home.fingerprint()
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------- the kit archive: one small list, kits never moved ----------

_ARCHIVE_LOCK = threading.Lock()


def _archive_read():
    """The archived list as saved: a list of names, or None when the file is there and is not
    {"archived": [names]} (damaged, or changed by hand into something else). No file: an empty list."""
    try:
        raw = ARCHIVE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(d, dict) or not isinstance(d.get("archived"), list) or not all(isinstance(x, str) for x in d["archived"]):
        return None
    return d["archived"]


def archived():
    return set(_archive_read() or [])


def set_archived(folder, on):
    """Put a kit on the archived list, or take it off. The sorted list afterwards. A press that changes nothing
    writes nothing (safe to press twice). The list is saved whole, and the list before is kept beside it."""
    with _ARCHIVE_LOCK:
        now = archived()
        if (folder in now) == bool(on):
            return sorted(now)
        new = set(now)
        (new.add if on else new.discard)(folder)
        HOME.mkdir(parents=True, exist_ok=True)
        if ARCHIVE.is_file() and _archive_read() is None:
            # a list that can't be read is set aside under a name of its own, never copied over the last good
            # list before (kit-archive.prev.json) and never written over
            n = 1
            while True:
                aside = ARCHIVE.with_name(f"kit-archive.unreadable-{date.today().isoformat()}-{n}.json")
                if not aside.exists():
                    break
                n += 1
            aside.write_bytes(ARCHIVE.read_bytes())
        elif ARCHIVE.is_file():
            tmp = ARCHIVE_PREV.with_name(f"{ARCHIVE_PREV.name}.{os.getpid()}-{threading.get_ident()}.tmp")
            tmp.write_bytes(ARCHIVE.read_bytes())
            this_computer.replace(tmp, ARCHIVE_PREV)
        tmp = ARCHIVE.with_name(f"{ARCHIVE.name}.{os.getpid()}-{threading.get_ident()}.tmp")
        try:
            tmp.write_text(json.dumps({"archived": sorted(new)}, indent=1, ensure_ascii=False), encoding="utf-8")
            this_computer.replace(tmp, ARCHIVE)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
        return sorted(new)


# ---------- a kit's three small pictures ----------

_THUMB_LOCK = threading.Lock()


def kit_thumb(name, i):
    """The i-th (1 to 3) small picture of a kit, in ~/.studio/home-thumbs/, made the first time it is asked
    for (one at a time). None when there is no such kit or photo. The kit is found only by its exact folder
    name in Your Content (arrange.kit_by_name), never by a path."""
    import arrange
    import kit as kit_mod
    kit = arrange.kit_by_name(name)
    if kit is None or i not in (1, 2, 3):
        return None
    dst = HOME / "home-thumbs" / f"{kit.name}-{i}.jpg"
    if dst.is_file():
        return dst
    with _THUMB_LOCK:
        if dst.is_file():
            return dst
        try:
            photos = kit_mod.photo_files(kit_mod.photos_dir(kit, kit_mod.load_rec(kit)))[:3]
            if i > len(photos):
                return None
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not kit_mod.fit(Path(photos[i - 1]), dst, (240, 240)):
                return None
        except (Exception, SystemExit):  # noqa: BLE001
            return None
    return dst if dst.is_file() else None


# ---------- the routes ----------

GET_ROUTES = ("/backups", "/make-posts", "/home-data", "/kit-thumb")
POST_ROUTES = ("/kit-archive",)


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _send(handler, body, ctype, code=200, cache="no-store"):
    try:                # a page left while its pictures load closes the line: nothing to say, nothing to log
        handler.send_response(code)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", cache)
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _json(handler, obj, code=200):
    _send(handler, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", code)


def handle_get(handler, path, query):
    """Every GET for the two screens. The posting server has already checked the Host. Whatever goes wrong, the
    server answers and stays up."""
    try:
        if path == "/backups":
            return _send(handler, backups_html().encode("utf-8"), "text/html; charset=utf-8")
        if path == "/make-posts":
            return _send(handler, make_posts_html().encode("utf-8"), "text/html; charset=utf-8")
        if _cross_site(handler):                        # what the screens draw from is for the screens only
            return _json(handler, {"ok": False}, 403)
        if path == "/home-data":
            return _json(handler, data())
        if path == "/kit-thumb":
            try:
                q = parse_qs(query or "", keep_blank_values=True)
            except ValueError:
                return handler.send_error(404)
            names, nums = q.get("kit") or [], q.get("i") or []
            if len(names) != 1 or len(nums) != 1 or nums[0] not in ("1", "2", "3"):
                return handler.send_error(404)
            f = kit_thumb(names[0], int(nums[0]))
            if not f:
                return handler.send_error(404)
            return _send(handler, f.read_bytes(), "image/jpeg", cache="private, max-age=300")
        return handler.send_error(404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _json(handler, {"ok": False}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def handle_post(handler, path, query):
    """POST /kit-archive {"shoot": "<kit folder>", "archived": true|false}: only from this server's own page
    (the pickers' guard: Host, Origin, type, length), every field checked, only a kit that is in Your Content
    right now. Answers {"ok": true, "archived": [...]} or {"ok": false, "problem": plain words}."""
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
        if refused is None and _cross_site(handler):
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _json(handler, {"ok": False, "problem": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _json(handler, {"ok": False, "problem": arrange.NOT_UNDERSTOOD}, 400)
        if (not isinstance(body, dict) or set(body) != {"shoot", "archived"} or not isinstance(body["shoot"], str)
                or not 1 <= len(body["shoot"]) <= 200 or not isinstance(body["archived"], bool)):
            return _json(handler, {"ok": False, "problem": arrange.NOT_UNDERSTOOD}, 400)
        kit = arrange.kit_by_name(body["shoot"])
        if kit is None:
            return _json(handler, {"ok": False, "problem": W("not_a_kit")}, 400)
        try:
            now = set_archived(kit.name, body["archived"])
        except OSError as e:
            _log(f"kit-archive: couldn't save the list ({e.__class__.__name__})")
            return _json(handler, {"ok": False, "problem": W("didnt_work")}, 500)
        return _json(handler, {"ok": True, "archived": now})
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        try:
            _json(handler, {"ok": False, "problem": W("didnt_work")}, 500)
        except (Exception, SystemExit):  # noqa: BLE001
            pass


def _log(msg):
    try:
        print("home base: " + msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def main():
    if sys.argv[1:] == ["data"]:
        print(json.dumps(data(), indent=1, ensure_ascii=False))
        return 0
    print(__doc__.split("\n\n")[0])
    return 2


if __name__ == "__main__":
    sys.exit(main())
