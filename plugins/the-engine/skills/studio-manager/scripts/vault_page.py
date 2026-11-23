#!/usr/bin/env python3
"""
My vault on the pages (Nicole's v29, section 1.3; her pages make-posts-preview.html and vault-kit-preview.html).

Two places:
  * the post kits list (home_base.py, /make-posts): My vault is always the first card, dark, on a row of its
    own. Its words are in home_base.WORDS; this file answers its one press.
  * the vault's own post kit page (kit.build_page's vault branch): her lede, the strip of what is in the vault
    with + Add a shoot and + Add clips, her three card lines and her "Tell your assistant what this reel is"
    box. Everything else on that page is the kit page's own.

The routes, each a POST behind the pickers' same-page-only guard (arrange.guard), each with the body {}:
    POST /vault-open    make the vault if there is none, bring its list up to date, answer its page's address
    POST /vault-add     + Add a shoot: the computer's own choose-folder window, then `vault.py add "<folder>"`
                        as a background job (vault.py: checked copies, the originals only read)
    POST /vault-clips   + Add clips: open the vault's own Footage folder in a window (no video is copied)
    GET  /vault-add-status   what the page follows while the copy runs: {state, words, done, of}

And a third place since stage 11: See everything in it (/vault.html, her vault-preview.html), at the end of this
file with its own routes (GET /vault.html, /vault-data, /vault-clip, /vault-out-photo; POST /vault-remove).

No page is ever sent a path: the vault is "the vault", a shoot is its folder name, and what a press did comes
back as plain words.
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
import vault  # noqa: E402

POST_CAP = 200                  # every body is {}
CHIPS_MOST = 12                 # shoots drawn as chips in the strip; the rest are counted ("+ 8 more")

# Nicole's, from pages/vault-kit-preview.html (v29), whole. The three examples are one line of hers, as she wrote it.
WORDS = {
    "eyebrow": "Post kit",
    "h1": "My vault<em>.</em>",
    "lede": "The post kit for all your shoots at once. Make reels and carousels that mix shoots: your favorites from the year, a few weddings in one, or behind the scenes you haven't used yet.",
    "back": "My post kits",                 # her way back, drawn as a step of the path at the top
    "count": "{photos} photos · {clips} clips",
    "add_shoot": "+ Add a shoot",
    "add_clips": "+ Add clips",
    "everything": "See everything in it",
    "reel_sub": "The same reel maker as every post kit: the Assistant picks, orders and cuts on the beat of your song, and it opens in CapCut. The only difference is it picks from every shoot in your vault.",
    "ask_h": "Tell the Assistant what this reel is",
    "ask_p": "\"My favorite maternity photos this year\" · \"Behind the scenes at the beach\" · \"Moms laughing, from any shoot\"",
    "carousel_sub": "The same carousel designer, with photos from any shoot: a year of favorites, or three families in one post.",
    "stories_sub": "Stories from any shoot: a throwback, a this-or-that, or behind the scenes from a few sessions.",
}

# Ours, where hers has none (her buttons only said "In the real version, ..."). Each is a draft for Dustin and
# Nicole. The lines an add ends with are vault.ADD_WORDS.
OUR_WORDS = {
    "count_one_photo": "1 photo",           # one of a thing is singular (hers is a template that always says "photos")
    "count_one_clip": "1 clip",
    "more_shoots": "+ {n} more",
    "no_shoots": "No shoots in it yet. Every post kit you make joins it by itself.",
    "picking": "Pick the folder in the window that just opened…",
    "no_folder": "No folder chosen.",
    "no_window": "The folder window didn't open. Tell the Assistant which folder to add, and it'll copy the photos for you.",
    "no_vault": "Your vault isn't there right now. Is the drive plugged in?",
    "cant_start": "The copy couldn't start. Tell the Assistant, and it'll sort it out.",
    "clips_opened": "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them.",
    "clips_behind": " It's behind this window: click {app} in {bar} to see it.",
    "clips_cant": "The folder for your videos didn't open. Tell the Assistant, and it'll open it for you.",
    "not_running": "The Assistant isn't running right now. Ask the Assistant to show your vault.",
    "didnt_work": "That didn't work. Try again in a moment.",
    "opening": "Opening your vault…",
}

# Her style lines for the strip and the box (pages/vault-kit-preview.html), and ours after them: a long shoot name
# breaks inside its chip, and the line that says what a press did sits right under the strip's buttons.
CSS = """.inv{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;background:var(--paper);border-radius:18px;padding:.9rem 1.1rem;box-shadow:0 1px 0 var(--line);margin-top:.4rem}
.inv .sh{display:flex;gap:.5rem;flex-wrap:wrap;min-width:0}
.inv .sh span{display:inline-flex;align-items:center;gap:.4rem;font:600 13px/1.2 var(--sans);background:var(--cream);border-radius:999px;padding:4px 10px 4px 4px;min-width:0;overflow-wrap:anywhere}
.inv .sh span.more,.inv .sh span.none{padding:8px 10px;color:var(--ink-2);font-weight:500}
.inv .sh img,.inv .sh i{width:26px;height:26px;border-radius:50%;object-fit:cover;background:var(--sand-l);flex:none;display:block}
.inv .ct{font:500 14px/1.3 var(--sans);color:var(--ink-2)}
.inv .acts{margin-left:auto;display:flex;gap:.4rem;flex-wrap:wrap}
.inv .went{flex-basis:100%;margin:0;text-align:right;color:var(--coral-2);font:600 13px/1.4 var(--sans)}
.inv .went:empty{display:none}
@media(max-width:560px){.inv .acts{margin-left:0}.inv .went{text-align:left}}
.ask{display:block;border:1.5px solid var(--coral-l);background:#FFF9F6;border-radius:14px;padding:.8rem .95rem;margin:.2rem 0 .9rem}
.ask .k{display:block;font:600 10px/1.2 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--coral-2);margin-bottom:.45rem}
.ask .p{display:block;margin:0;font-size:14px;color:var(--ink)}
"""

SCRIPT = r"""
(function(){
const live = location.protocol.indexOf('http') === 0;
const W = JSON.parse(document.getElementById('vault-words').textContent);
const went = document.getElementById('invWent');
function say(t){ if (went) went.textContent = t || ''; }
function post(path){
  return fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(function(r){ return r.json(); });
}
// the strip drawn again from the page as the Assistant builds it now (new counts after photos came in)
function redraw(){
  return fetch(location.href, {cache: 'no-store'}).then(function(r){ return r.text(); }).then(function(t){
    const d = new DOMParser().parseFromString(t, 'text/html');
    ['invShoots', 'invCount'].forEach(function(id){
      const now = d.getElementById(id), old = document.getElementById(id);
      if (now && old && old.outerHTML !== now.outerHTML) old.replaceWith(document.importNode(now, true));
    });
  }).catch(function(){});
}
let following = null;
function follow(btn){
  if (following) clearInterval(following);
  following = setInterval(function(){
    fetch('/vault-add-status', {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
      if (j.words) say(j.words);
      if (j.state !== 'working') { clearInterval(following); following = null; if (btn) btn.disabled = false; redraw(); }
    }).catch(function(){});
  }, 700);
}
const add = document.getElementById('vaultAdd'), clips = document.getElementById('vaultClips');
if (add) add.addEventListener('click', function(){
  if (!live) { say(W.not_running); return; }
  add.disabled = true; say(W.picking);
  post('/vault-add').then(function(j){
    say(j.words || '');
    if (j.ok && j.state === 'working') follow(add); else add.disabled = false;
  }).catch(function(){ add.disabled = false; say(W.not_running); });
});
if (clips) clips.addEventListener('click', function(){
  if (!live) { say(W.not_running); return; }
  clips.disabled = true;
  post('/vault-clips').then(function(j){ say(j.words || ''); }).catch(function(){ say(W.not_running); })
    .then(function(){ clips.disabled = false; });
});
// a copy still running when the page is opened again: pick it up
if (live) fetch('/vault-add-status', {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
  if (j.state === 'working') { if (add) add.disabled = true; say(j.words || ''); follow(add); }
}).catch(function(){});
})();
"""


def W(key):
    return WORDS[key] if key in WORDS else OUR_WORDS[key]


def count_words(photos, clips):
    """Hers: "295 photos · 21 clips"; ours for one of a thing."""
    a = OUR_WORDS["count_one_photo"] if photos == 1 else f"{photos:,} photos"
    b = OUR_WORDS["count_one_clip"] if clips == 1 else f"{clips:,} clips"
    if photos != 1 and clips != 1:
        return WORDS["count"].format(photos=f"{photos:,}", clips=f"{clips:,}")
    return f"{a} · {b}"


def strip_facts(vault_kit):
    """What the strip shows: the shoots that have photos in the vault (newest first; a folder's name and the
    shoot's own name, never a path), how many photos are on the vault's list, and how many clips are in it: the
    same clips See everything in it lists (a stretch made on a reel page, not a video file; none that was taken
    out), so the two pages never disagree."""
    groups = vault.rows_by_group(vault_kit)
    shoots = [{"folder": g["kit"], "name": g["name"]} for g in groups if g["group"] == "kit"]
    photos = sum(len(g["rows"]) for g in groups)
    try:
        clips = len(vault.catalog(vault_kit, photos=False)["clips"])
    except (Exception, SystemExit):  # noqa: BLE001  (a reel record that can't be read: the strip still draws)
        clips = 0
    return {"shoots": shoots, "photos": photos, "clips": clips}


def strip_html(vault_kit):
    """Her strip (.inv): one chip per shoot with its small picture, the counts, + Add a shoot, + Add clips, and
    See everything in it only when its page exists (vault.EVERYTHING, which stage 11 turns on). The line that
    says what a press did is inside the strip, right under the buttons."""
    e = html.escape
    f = strip_facts(vault_kit)
    chips = []
    for s in f["shoots"][:CHIPS_MOST]:
        src = "/kit-thumb?kit=" + quote(s["folder"], safe="") + "&i=1"
        chips.append(f"<span><img src='{e(src, quote=True)}' alt='' loading='lazy' onerror=\"this.replaceWith(document.createElement('i'))\">{e(s['name'])}</span>")
    extra = len(f["shoots"]) - CHIPS_MOST
    if extra > 0:
        chips.append(f"<span class='more'>{e(OUR_WORDS['more_shoots'].format(n=extra))}</span>")
    if not f["shoots"]:
        chips.append(f"<span class='none'>{e(OUR_WORDS['no_shoots'])}</span>")
    everything = ""
    if getattr(vault, "EVERYTHING", False):
        everything = (f"<a class='go' id='vaultEverything' href='/vault.html'>{e(WORDS['everything'])} &rarr;</a>")
    return ("<div class='inv' id='inv'>"
            f"<div class='sh' id='invShoots'>{''.join(chips)}</div>"
            f"<span class='ct' id='invCount'>{e(count_words(f['photos'], f['clips']))}</span>"
            f"<span class='acts'><button class='go' type='button' id='vaultAdd'>{e(WORDS['add_shoot'])}</button>"
            f"<button class='go' type='button' id='vaultClips'>{e(WORDS['add_clips'])}</button>{everything}</span>"
            "<p class='went' id='invWent' role='status'></p></div>")


def ask_html():
    """Her box on the Reels card. The card is a link, so the box is spans, never a block inside an <a>'s <p>."""
    e = html.escape
    return f"<span class='ask'><span class='k'>{e(WORDS['ask_h'])}</span><span class='p'>{e(WORDS['ask_p'])}</span></span>"


def page_words():
    keys = ("picking", "not_running", "didnt_work")
    return json.dumps({k: OUR_WORDS[k] for k in keys}, ensure_ascii=True).replace("<", "\\u003c")


def page_address(vault_kit):
    return "/content/" + quote(Path(vault_kit).name, safe="") + "/Post%20kit.html"


def card_facts():
    """What the My vault card on the post kits list shows, without making anything: how many photos (the vault's
    own list once there is one; before that, what every post kit's list holds), and up to three shoots whose
    small pictures it borrows. Folder names and numbers only."""
    v = vault.find()
    mem = vault.members(v)
    if v is not None:
        photos = sum(len(g["rows"]) for g in vault.rows_by_group(v))      # what was taken out is not counted
        try:
            if vault.changed(v)["changed"]:              # its list is behind: the count it will have once opened
                own = len(vault._own_photos(v))
                gone = len(vault.out(v)["photos"])
                photos = max(photos, sum(m["photos"] for m in mem) + own - gone)
        except (OSError, vault.Trouble):
            pass
    else:
        photos = sum(m["photos"] for m in mem)
    return {"photos": photos, "made": v is not None, "thumbs": [m["folder"] for m in mem if m["photos"]][:3]}


# ---------- the routes ----------

GET_ROUTES = ("/vault-add-status", "/vault.html", "/vault-data", "/vault-clip", "/vault-out-photo")
POST_ROUTES = ("/vault-open", "/vault-add", "/vault-clips", "/vault-remove")
EVERY_GET = ("/vault.html", "/vault-data", "/vault-clip", "/vault-out-photo")


def _send(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        pass


def _cross_site(handler):
    return (handler.headers.get("Sec-Fetch-Site") or "").strip().lower() == "cross-site"


def _log(msg):
    try:
        print("vault: " + msg, flush=True)
    except (BrokenPipeError, OSError):
        pass


def handle_get(handler, path, query):
    try:
        if _cross_site(handler) and path != "/vault.html":       # (the page itself may be opened from anywhere; what it asks for may not)
            return _send(handler, {"ok": False}, 403)
        if path in EVERY_GET:
            return handle_every_get(handler, path, query)
        v = vault.find()
        if v is None:
            return _send(handler, {"ok": True, "state": "none", "words": "", "done": 0, "of": 0})
        j = vault.add_job(v)
        return _send(handler, {"ok": True, "state": j["state"], "words": j["words"], "done": j["done"], "of": j["of"]})
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"GET {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "state": "none", "words": ""}, 500)


def _start_add(v, folder):
    """`vault.py add "<folder>" --job`, detached so it outlives this request (and the page server). Its own lock
    keeps two apart; its record is what the page follows."""
    vault._job_write(v, state="working", words=vault.ADD_WORDS["starting"], done=0, of=0)
    logs = vault.HOME / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with open(logs / "vault-add.log", "ab") as out:
        job = this_computer.popen_detached([sys.executable, str(HERE / "vault.py"), "add", str(folder), "--job"],
                                           stdin=subprocess.DEVNULL, stdout=out, stderr=out)
    vault._job_write_pid(v, job.pid)
    return job


def handle_post(handler, path, query):
    """Every press is checked the way arrange.py checks its own: this server's name in Host, its own Origin when
    one is sent, JSON, a short body that is exactly {} (/vault-remove: exactly {what, id, on}). Whatever goes wrong, plain words and the server stays up."""
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", REMOVE_CAP if path == "/vault-remove" else POST_CAP, path)
        if refused is None and _cross_site(handler):
            refused = (403, arrange.NOT_UNDERSTOOD)
        if refused:
            arrange._drain(handler)
            return _send(handler, {"ok": False, "words": refused[1]}, refused[0])
        n = int(handler.headers.get("Content-Length"))
        try:
            body = json.loads(handler.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)
        if path == "/vault-remove":
            v = vault.find()
            if v is None:
                return _send(handler, {"ok": False, "words": OUR_WORDS["no_vault"]})
            code, answer = remove_from_page(v, body)
            return _send(handler, answer, code)
        if body != {}:
            return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 400)

        if path == "/vault-open":
            try:
                v, made = vault.ensure()
                try:
                    vault.relist(v, quick=True)
                except vault.Trouble:
                    pass                                    # another look is listing it right now: the page opens all the same
            except vault.Trouble as t:
                return _send(handler, {"ok": False, "words": str(t)})
            if made:
                _log(f"made the vault ({v.name})")
            return _send(handler, {"ok": True, "url": page_address(v), "made": made})

        v = vault.find()
        if v is None:
            return _send(handler, {"ok": False, "words": OUR_WORDS["no_vault"]})

        if path == "/vault-clips":
            import finder
            folder = v / "Footage"
            folder.mkdir(exist_ok=True)                     # the vault's own folder (made with it; here in case it was tidied away)
            ok, why = finder.open_folder(folder)
            if not ok:
                _log(f"couldn't open the vault's Footage folder ({why})")
                return _send(handler, {"ok": False, "words": OUR_WORDS["clips_cant"]})
            words = OUR_WORDS["clips_opened"]
            if why == "behind":
                words += OUR_WORDS["clips_behind"].format(app=this_computer.FILES_APP, bar=this_computer.APP_BAR)
            return _send(handler, {"ok": True, "words": words})

        if path == "/vault-add":
            if vault.add_job(v)["state"] == "working":
                return _send(handler, {"ok": True, "state": "working", "words": vault.ADD_WORDS["busy"]})
            folder, why = this_computer.pick_folder("Pick the folder of finished photos to add to your vault. The Assistant copies the photos; nothing is moved.")
            if not folder:
                return _send(handler, {"ok": False, "words": OUR_WORDS["no_folder"] if why == "cancelled" else OUR_WORDS["no_window"]})
            no = vault.add_refusal(v, folder)
            if no:
                return _send(handler, {"ok": False, "words": vault.ADD_WORDS[no]})
            try:
                _start_add(v, folder)
            except OSError as e:
                _log(f"couldn't start the copy ({e.__class__.__name__})")
                vault._job_write(v, state="stopped", words=OUR_WORDS["cant_start"])
                return _send(handler, {"ok": False, "words": OUR_WORDS["cant_start"]})
            return _send(handler, {"ok": True, "state": "working", "words": vault.ADD_WORDS["starting"]})

        return _send(handler, {"ok": False, "words": arrange.NOT_UNDERSTOOD}, 404)
    except (Exception, SystemExit) as e:  # noqa: BLE001
        _log(f"POST {path} failed: {e.__class__.__name__}: {str(e)[:200]}")
        return _send(handler, {"ok": False, "words": OUR_WORDS["didnt_work"]}, 500)


# =====================================================================================================================
# See everything in it (Nicole's v29, 1.6; her page vault-preview.html, screenshot 09): /vault.html
#
# "Nothing gets picked on this page. Making happens in the post kit." The page is for looking through and tidying:
# the clips and photos of every shoot, grouped by shoot, found with her search rule (vault.py) and the shoot chips.
# A tap on a clip plays it right there, looped between its start and end, from the reel page's own /reel-video
# route (the vault and the video's key); a photo opens big from /kit-photo. Use it in a reel is a plain link to the
# vault's reel page. Remove from my vault writes one entry in the vault's own vault.json (vault.in_or_out) and
# nothing else: no photo, no video, no shoot's post kit. Put it back undoes it (hers has no way back).
#
#   GET  /vault.html        the page (never makes the vault)
#   GET  /vault-data        {shoots, clips, photos, out, ...}: names, numbers and ids only, never a path
#   GET  /vault-clip?id=    one clip's video as the vault lists it: {key, play, state}; a shoot's video that needs
#                           a small copy to play is got ready here, the first time it is asked for
#   GET  /vault-out-photo?n=  the small copy of a photo that was taken out (the vault's own copy, by its number)
#   POST /vault-remove      {what: "photo" | "clip", id, on}: on false takes it out, on true puts it back
# =====================================================================================================================

REMOVE_CAP = 1200               # {what, id, on}: a clip's id carries its shoot's folder name

# Nicole's, from pages/vault-preview.html (v29), whole.
EVERY_WORDS = {
    "title": "What's in <em>my vault.</em>",
    "lede": "Your clips and photos from every shoot. Add more, or look up a clip you remember.",
    "tab_clips": "Clips",
    "tab_photos": "Photos",
    "add": "+ Add clips or photos",
    "search": "Search: me with my camera, laughing, beach, kitchen",
    "search_aria": "Search your vault",
    "every_shoot": "Every shoot",
    "group": "{shoot} · {date}",
    "nothing": "Nothing matches that yet.",
    "meta": "{shoot} · {date} · {n} seconds",
    "use": "Use it in a reel",
    "remove": "Remove from my vault",
    "close": "Close",                       # the × button's name for a screen reader
    "loading": "Loading…",
    "cant_reach": "I can't reach your shoots right now.",
}

# Ours, where hers has none (her Remove and + Add only said "In the real version, ..."). Each is a draft for
# Dustin and Nicole. What a Remove or a Put it back answers is vault.OUT_WORDS.
EVERY_OUR_WORDS = {
    "crumb": "Everything in it",
    "tab_title": "My vault",
    "one_second": "1 second",               # hers is a template that always says "seconds"
    "added": vault.OUT_WORDS["added"],      # hers, from the vault's reel page: what was added to the vault itself
    "photo_from": "A photo from {shoot}",   # a photo's heading (hers: "Photo {id}")
    "photo_added": "A photo you added to your vault",
    "put_back": "Put it back",
    "out_fold": "Taken out of my vault ({n})",
    "out_say": "These are still in their shoots. Nothing was deleted.",
    "out_photo": "A photo",
    "add_photos": "Add a folder of finished photos",
    "add_videos": "Add videos",
    "add_say": "Photos are copied into your vault and your originals aren't moved. Videos go in the folder that opens.",
    "getting_clip": "Getting this clip ready to play…",
    "cant_play": "This clip can't be played here right now. It is still in its shoot.",
    "no_vault": "Your vault isn't made yet. Open My vault from your post kits, then come back here.",
    "no_vault_go": "My post kits",
    "empty_clips": "No clips in your vault yet. Clips you make on a reel page show up here.",
    "empty_photos": "No photos in your vault yet. Every post kit you make joins it by itself.",
}

# Her style lines for this page (pages/vault-preview.html), in the look's own names, without her dead tray and
# "Used" badge; ours after them (the add row, the line a press answers with, the fold of what was taken out).
EVERY_CSS = r"""
.tabs{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:1rem 0 .6rem}
.tab{font:600 14px/1 var(--sans);padding:10px 16px;border-radius:999px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer}
.tab.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.tabs .add{margin-left:auto}
.tools{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:.4rem}
.tools input{flex:1;min-width:220px;font:500 15px/1 var(--sans);padding:12px 14px;border-radius:14px;border:1.5px solid var(--line);background:var(--paper);color:var(--ink)}
.tools input:focus{outline:none;border-color:var(--coral)}
#chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font:600 12.5px/1 var(--sans);padding:8px 12px;border-radius:999px;border:1.5px solid var(--line);background:none;color:var(--ink-2);cursor:pointer;max-width:100%;overflow-wrap:anywhere}
.chip.on{border-color:var(--coral);color:var(--coral-2);background:var(--coral-l)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:.8rem 0 2rem}
.t{position:relative;border:0;padding:0;background:none;text-align:left;cursor:pointer;font:inherit;color:inherit;min-width:0}
.t .im{position:relative;aspect-ratio:9/16;border-radius:12px;overflow:hidden;background:var(--sand-l)}
.t.ph .im{aspect-ratio:4/5}
.t img{width:100%;height:100%;object-fit:cover;display:block}
.t .len{position:absolute;right:6px;bottom:6px;font:600 11px/1 var(--sans);color:#fff;background:rgba(20,22,30,.6);padding:4px 6px;border-radius:6px}
.t .len::before{content:'\25B6  ';font-size:9px}
.t b{display:block;margin-top:6px;font:500 13px/1.3 var(--sans);overflow-wrap:anywhere}
.t small{display:block;color:var(--ink-2);font-size:12px;margin-top:2px;overflow-wrap:anywhere}
.t:focus-visible .im{box-shadow:0 0 0 3px var(--coral)}
h3.month{grid-column:1/-1;margin:.8rem 0 0;font:600 13px/1.3 var(--sans);color:var(--ink-2)}
.grid .empty{grid-column:1/-1}
.msg{font:500 13px/1.4 var(--sans);color:var(--ink-2);margin:.2rem 0 0}
.msg:empty{display:none}
.view{position:fixed;inset:0;z-index:40;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(31,36,48,.55)}
.view[hidden]{display:none}
.vbox{position:relative;display:flex;gap:1.2rem;background:var(--paper);border-radius:20px;padding:1rem;max-width:720px;width:100%;flex-wrap:wrap;max-height:calc(100vh - 32px);overflow:auto}
.vmedia{width:270px;max-width:100%;aspect-ratio:9/16;border-radius:14px;overflow:hidden;background:#111;flex:none}
.vmedia.ph{aspect-ratio:4/5}
.vmedia video,.vmedia img{width:100%;height:100%;object-fit:cover;display:block}
.vinfo{flex:1;min-width:220px;display:grid;gap:.4rem;align-content:start;padding-top:.4rem;padding-right:1.6rem}
.vinfo b{font:600 19px/1.25 var(--sans);overflow-wrap:anywhere}.vinfo small{color:var(--ink-2);font-size:13.5px}
.vinfo .desc{margin:0;font-size:14.5px;color:var(--ink)}.vinfo .desc:empty{display:none}
.vacts{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.6rem}
.vacts [hidden]{display:none}
.vx{position:absolute;right:10px;top:8px;border:0;background:none;font-size:24px;line-height:1;color:var(--ink-2);cursor:pointer}
.addrow{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin:0 0 .6rem;padding:.8rem 1rem;border-radius:14px;background:var(--paper);box-shadow:0 1px 0 var(--line)}
.addrow[hidden]{display:none}
.addrow .msg{flex-basis:100%}
.went{flex-basis:100%;margin:0;color:var(--coral-2);font:600 13px/1.4 var(--sans)}.went:empty{display:none}
.vsay{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}.vsay[hidden]{display:none}
.vsay .msg{color:var(--ink);margin:0}
details.outs{margin:1rem 0 3rem}details.outs[hidden]{display:none}
details.outs summary{cursor:pointer;font:600 14px/1.3 var(--sans);color:var(--ink-2)}
.outs .row{display:flex;gap:.7rem;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--line);min-width:0}
.outs .row img,.outs .row i{width:44px;height:44px;border-radius:8px;object-fit:cover;background:var(--sand-l);flex:none;display:block}
.outs .row span{flex:1;min-width:0;font-size:14px;overflow-wrap:anywhere}.outs .row span small{display:block;color:var(--ink-2);font-size:12.5px}
"""

EVERY_SCRIPT = r"""
(function(){
'use strict';
var W = JSON.parse(document.getElementById('every-words').textContent);
var $ = function(id){ return document.getElementById(id); };
var live = location.protocol.indexOf('http') === 0;
var DATA = null, kind = 'clips', only = null, open = null, tries = {};
function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function fill(t, o){ return String(t).replace(/\{(\w+)\}/g, function(m, k){ return (o && k in o) ? o[k] : m; }); }
function many(n){ return Number(n).toLocaleString('en-US'); }
function q(){ return 'kit=' + encodeURIComponent(DATA.vault); }
// the search rule, hers (vault.py): lower case, accents off, anything not a letter or a number is a space
function fold(t){ return String(t || '').normalize('NFKD').toLowerCase().replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' '); }
function words(){
  var drop = DATA.everyday, out = [];
  fold($('q').value).split(' ').forEach(function(w){ if (w && drop.indexOf(w) < 0 && out.indexOf(w) < 0) out.push(w); });
  return out;
}
function shootOf(kit){ for (var i = 0; i < DATA.shoots.length; i++) if (DATA.shoots[i].kit === kit) return DATA.shoots[i]; return {kit: kit, name: kit, date: ''}; }
function shown(){
  var ws = words(), list = kind === 'clips' ? DATA.clips : DATA.photos;
  return list.filter(function(it){ return (only === null || it.kit === only) && ws.every(function(w){ return it.text.indexOf(w) > -1; }); });
}
function mmss(len){ var s = Math.max(1, Math.round(len)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function stillUrl(c){ return '/reel-vault-still?' + q() + '&from=' + encodeURIComponent(c.kit) + '&id=' + encodeURIComponent(c.cid); }
function photoUrl(p, size){ return '/kit-photo?' + q() + '&n=' + p.n + '&size=' + size; }
// a picture that is still being made is asked for again a few times, never for ever
function picture(src, key){
  var img = el('img'); img.alt = ''; img.loading = 'lazy'; img.src = src;
  img.onerror = function(){
    tries[key] = (tries[key] || 0) + 1;
    if (tries[key] > 12 || !img.isConnected) { img.onerror = null; img.style.visibility = 'hidden'; return; }
    setTimeout(function(){ if (img.isConnected) img.src = src + '&again=' + tries[key]; }, 1500);
  };
  return img;
}
function heading(s){ return s.date ? fill(W.group, {shoot: s.name, date: s.date}) : s.name; }
function tile(it){
  var b = el('button', 't' + (kind === 'photos' ? ' ph' : '')); b.type = 'button';
  var im = el('div', 'im'), s = shootOf(it.kit);
  if (kind === 'clips') {
    b.dataset.id = it.id;
    im.appendChild(picture(stillUrl(it), 'c' + it.id)); im.appendChild(el('span', 'len', mmss(it.len)));
    b.appendChild(im); b.appendChild(el('b', '', it.label)); b.appendChild(el('small', '', s.name));
  } else {
    b.dataset.n = it.n;
    im.appendChild(picture(photoUrl(it, 's'), 'p' + it.n));
    b.appendChild(im); b.appendChild(el('small', '', s.name));
    b.setAttribute('aria-label', it.words || fill(it.kit ? W.photo_from : W.photo_added, {shoot: s.name}));
  }
  b.addEventListener('click', function(){ openView(kind === 'clips' ? 'clip' : 'photo', it); });
  return b;
}
function render(){
  $('tClips').textContent = W.tab_clips + ' ' + many(DATA.clips.length);
  $('tPhotos').textContent = W.tab_photos + ' ' + many(DATA.photos.length);
  $('tClips').classList.toggle('on', kind === 'clips'); $('tPhotos').classList.toggle('on', kind === 'photos');
  $('tClips').setAttribute('aria-pressed', kind === 'clips'); $('tPhotos').setAttribute('aria-pressed', kind === 'photos');
  var chips = $('chips'); chips.textContent = '';
  if (only !== null && !DATA.shoots.some(function(s){ return s.kit === only; })) only = null;
  [null].concat(DATA.shoots.map(function(s){ return s.kit; })).forEach(function(k){
    var c = el('button', 'chip' + (only === k ? ' on' : ''), k === null ? W.every_shoot : shootOf(k).name); c.type = 'button';
    c.setAttribute('aria-pressed', only === k);
    c.addEventListener('click', function(){ only = k; render(); });
    chips.appendChild(c);
  });
  var grid = $('grid'), list = shown(), all = kind === 'clips' ? DATA.clips : DATA.photos; grid.textContent = '';
  if (!list.length) grid.appendChild(el('p', 'empty', all.length ? W.nothing : (kind === 'clips' ? W.empty_clips : W.empty_photos)));
  DATA.shoots.forEach(function(s){
    var mine = list.filter(function(it){ return it.kit === s.kit; });
    if (!mine.length) return;
    grid.appendChild(el('h3', 'month', heading(s)));
    mine.forEach(function(it){ grid.appendChild(tile(it)); });
  });
  var outs = $('outs'), rows = $('outRows'); outs.hidden = !DATA.out.length; rows.textContent = '';
  $('outSum').textContent = fill(W.out_fold, {n: many(DATA.out.length)});
  DATA.out.forEach(function(o){
    var r = el('div', 'row'); r.dataset.what = o.what; r.dataset.id = o.id;
    var pic = o.what === 'clip' ? picture('/reel-vault-still?' + q() + '&from=' + encodeURIComponent(o.kit) + '&id=' + encodeURIComponent(o.cid), 'oc' + o.id)
                                : picture('/vault-out-photo?n=' + o.id, 'op' + o.id);
    var sp = el('span', '', o.label || (o.what === 'clip' ? '' : W.out_photo)); sp.appendChild(el('small', '', o.shoot));
    var back = el('button', 'btn', W.put_back); back.type = 'button';
    back.addEventListener('click', function(){ back.disabled = true; change(o.what, o.id, true, function(j){ $('outWent').textContent = j.words || ''; }); });
    r.appendChild(pic); r.appendChild(sp); r.appendChild(back); rows.appendChild(r);
  });
}
function load(then){
  return fetch('/vault-data', {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
    if (!j || !j.ok) throw new Error('no');
    DATA = j; render(); if (then) then();
  }).catch(function(){ if (!DATA) { $('grid').textContent = ''; $('grid').appendChild(el('p', 'empty', W.cant_reach)); } });
}
// ---- the viewer: a clip plays right there, looped between its start and end; a photo opens big
var pollClip = null;
function closeView(){
  if (pollClip) { clearTimeout(pollClip); pollClip = null; }
  var v = $('vmedia').querySelector('video'); if (v) { try { v.pause(); } catch (e) {} v.removeAttribute('src'); }
  $('vmedia').textContent = ''; $('view').hidden = true; open = null;
}
function openView(what, it){
  closeView();
  open = {what: what, id: what === 'clip' ? it.id : it.n, out: false};
  var s = shootOf(it.kit), m = $('vmedia');
  m.className = 'vmedia' + (what === 'photo' ? ' ph' : '');
  $('vsay').hidden = true; $('vmsg').textContent = ''; $('vnote').textContent = '';
  $('vrm').hidden = false; $('vrm').disabled = false; $('vdesc').textContent = '';
  if (what === 'clip') {
    $('vlabel').textContent = it.label;
    var n = Math.max(1, Math.round(it.len));
    var meta = fill(W.meta, {shoot: s.name, date: s.date, n: n});
    if (n === 1) meta = meta.replace(/1 seconds$/, W.one_second);
    if (!s.date) meta = meta.replace(' ·  · ', ' · ');
    $('vmeta').textContent = meta;
    $('vuse').hidden = false;
    m.appendChild(picture(stillUrl(it), 'v' + it.id));
    var asked = 0, mine = open;
    (function ask(){
      fetch('/vault-clip?id=' + encodeURIComponent(it.id), {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
        if (open !== mine) return;
        if (j.ok && j.play) {
          var v = document.createElement('video');
          v.muted = true; v.autoplay = true; v.playsInline = true; v.setAttribute('playsinline', ''); v.preload = 'auto';
          v.dataset.start = it.start; v.dataset.end = it.end;
          v.src = '/reel-video?' + q() + '&key=' + encodeURIComponent(j.key) + '#t=' + it.start + ',' + it.end;
          v.addEventListener('loadedmetadata', function(){ try { v.currentTime = it.start; } catch (e) {} });
          v.addEventListener('timeupdate', function(){ if (v.currentTime >= it.end || v.currentTime < it.start - 0.3) { v.currentTime = it.start; var p = v.play(); if (p && p.catch) p.catch(function(){}); } });
          v.addEventListener('ended', function(){ v.currentTime = it.start; var p = v.play(); if (p && p.catch) p.catch(function(){}); });
          m.textContent = ''; m.appendChild(v); $('vnote').textContent = '';
          var p = v.play(); if (p && p.catch) p.catch(function(){});
        } else if (j.ok && j.wait && asked++ < 60) {
          $('vnote').textContent = W.getting_clip; pollClip = setTimeout(ask, 1500);
        } else { $('vnote').textContent = W.cant_play; }
      }).catch(function(){ if (open === mine) $('vnote').textContent = W.cant_play; });
    })();
  } else {
    $('vlabel').textContent = it.kit ? s.name : W.added;
    $('vmeta').textContent = s.date || '';
    $('vdesc').textContent = it.words || '';
    $('vuse').hidden = true;
    var big = el('img'); big.alt = it.words || ''; big.src = photoUrl(it, 'l');
    big.onerror = function(){ big.onerror = null; big.src = photoUrl(it, 's'); };
    m.appendChild(big);
  }
  $('view').hidden = false; $('vx').focus();
}
// ---- Remove from my vault, and Put it back
function change(what, id, on, said){
  return fetch('/vault-remove', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({what: what, id: id, on: on})})
    .then(function(r){ return r.json(); }).then(function(j){
      if (j && j.data) { DATA = j.data; render(); }
      if (said) said(j || {});
      return j;
    }).catch(function(){ if (said) said({ok: false, words: W.didnt_work}); });
}
$('vrm').addEventListener('click', function(){
  if (!open) return;
  var mine = open; $('vrm').disabled = true;
  change(mine.what, mine.id, false, function(j){
    if (open !== mine) return;
    $('vmsg').textContent = j.words || ''; $('vsay').hidden = false;
    if (j.ok) { mine.out = true; $('vrm').hidden = true; $('vuse').hidden = true; $('vback').hidden = false; $('vback').disabled = false; }
    else { $('vrm').disabled = false; $('vback').hidden = true; }
  });
});
$('vback').addEventListener('click', function(){
  if (!open) return;
  var mine = open; $('vback').disabled = true;
  change(mine.what, mine.id, true, function(j){
    if (open !== mine) return;
    $('vmsg').textContent = j.words || '';
    if (j.ok) { mine.out = false; $('vback').hidden = true; $('vrm').hidden = false; $('vrm').disabled = false; $('vuse').hidden = mine.what !== 'clip'; }
    else $('vback').disabled = false;
  });
});
$('vx').addEventListener('click', closeView);
$('view').addEventListener('click', function(e){ if (e.target === $('view')) closeView(); });
document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && !$('view').hidden) closeView(); });
$('tClips').addEventListener('click', function(){ kind = 'clips'; render(); });
$('tPhotos').addEventListener('click', function(){ kind = 'photos'; render(); });
$('q').addEventListener('input', function(){ if (DATA) render(); });
// ---- + Add clips or photos: the two adds of the vault's post kit (the folder picker for photos, the Footage folder for videos)
var went = $('addWent'), following = null;
function post(path){ return fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(function(r){ return r.json(); }); }
function follow(btn){
  if (following) clearInterval(following);
  following = setInterval(function(){
    fetch('/vault-add-status', {cache: 'no-store'}).then(function(r){ return r.json(); }).then(function(j){
      if (j.words) went.textContent = j.words;
      if (j.state !== 'working') { clearInterval(following); following = null; btn.disabled = false; load(); }
    }).catch(function(){});
  }, 700);
}
$('add').addEventListener('click', function(){ var r = $('addRow'); r.hidden = !r.hidden; $('add').setAttribute('aria-expanded', !r.hidden); });
$('addPhotos').addEventListener('click', function(){
  var b = $('addPhotos'); b.disabled = true; went.textContent = W.picking;
  post('/vault-add').then(function(j){ went.textContent = j.words || ''; if (j.ok && j.state === 'working') follow(b); else b.disabled = false; })
    .catch(function(){ b.disabled = false; went.textContent = W.not_running; });
});
$('addVideos').addEventListener('click', function(){
  var b = $('addVideos'); b.disabled = true;
  post('/vault-clips').then(function(j){ went.textContent = j.words || ''; }).catch(function(){ went.textContent = W.not_running; }).then(function(){ b.disabled = false; });
});
window.VaultPage = {data: function(){ return DATA; }, reload: load};
if (!live) { $('grid').textContent = ''; $('grid').appendChild(el('p', 'empty', W.not_running)); return; }
var q0 = new URLSearchParams(location.search).get('q'); if (q0) $('q').value = q0;
load();
})();
"""


def _nice_day(iso):
    """Hers (niceDay): "Sep 23, 2026". "" for anything that is not a day."""
    from datetime import date
    try:
        return this_computer.strftime(date.fromisoformat(str(iso)[:10]), "%b %-d, %Y")
    except (ValueError, TypeError):
        return ""


def every_data(vault_kit):
    """What /vault.html draws and searches, with no place on this computer in it: the vault's folder name (what
    the picture and video routes are asked by), the shoots, every clip and photo, what was taken out, and the
    search's everyday words. A clip's id is "<its shoot's folder>:<its own id>"; a photo's is its vault number.
    "text" is already folded the way search compares it (vault.fold)."""
    vault_kit = Path(vault_kit)
    cat = vault.catalog(vault_kit)
    added = EVERY_OUR_WORDS["added"]
    shoots = [{"kit": s["kit"], "name": s["name"] if s["group"] != "added" else added, "date": _nice_day(s["date"]),
               "own": s["group"] == "added"} for s in cat["shoots"] if s["photos"] or s["clips"]]
    clips = [{"id": vault.clip_out_key(c["kit"], c["id"]), "kit": c["kit"], "cid": c["id"], "label": c["label"],
              "named": bool(c["named"]), "start": c["start"], "end": c["end"], "len": round(float(c["end"]) - float(c["start"]), 1),
              "text": vault.fold(c["text"])} for c in cat["clips"]]
    photos = [{"n": p["n"], "kit": p["kit"], "words": p.get("words") or "", "text": vault.fold(p["text"])} for p in cat["photos"]]
    outs = []
    for o in vault.out_list(vault_kit):
        one = {"what": o["what"], "id": o["id"], "kit": o["kit"], "shoot": o["shoot"] or added, "label": o["label"]}
        if o["what"] == "clip":
            one["cid"] = str(o["id"]).rpartition(":")[2]
        outs.append(one)
    return {"ok": True, "vault": vault_kit.name, "shoots": shoots, "clips": clips, "photos": photos, "out": outs,
            "everyday": sorted(vault.EVERYDAY)}


def every_words():
    w = {k: re.sub(r"</?em>", "", v) for k, v in EVERY_WORDS.items()}
    w.update(EVERY_OUR_WORDS)
    w.update({k: OUR_WORDS[k] for k in ("picking", "not_running", "didnt_work")})
    return json.dumps(w, ensure_ascii=True).replace("<", "\\u003c")


def every_html(vault_kit):
    """The page. With no vault it says so and makes nothing (the vault is made by a guarded press or a command)."""
    import brand
    import home_base
    import look
    e = html.escape
    H, O = EVERY_WORDS, EVERY_OUR_WORDS
    if vault_kit is None:
        trail = [(O["no_vault_go"], "/make-posts"), (O["crumb"], None)]
        body = (f"<header class='head'><h1>{H['title']}</h1><p class='lede'>{e(O['no_vault'])}</p></header>"
                f"<p><a class='btn solid' href='/make-posts'>{e(O['no_vault_go'])} &rarr;</a></p>")
        script = ""
    else:
        name = Path(vault_kit).name
        trail = look.kit_trail(name) + [(O["crumb"], None)]
        reel = "/reel.html?kit=" + quote(name, safe="")
        body = (
            f"<header class='head'><h1>{H['title']}</h1><p class='lede'>{e(H['lede'])}</p></header>"
            "<div class='tabs'>"
            f"<button class='tab on' type='button' id='tClips' aria-pressed='true'>{e(H['tab_clips'])}</button>"
            f"<button class='tab' type='button' id='tPhotos' aria-pressed='false'>{e(H['tab_photos'])}</button>"
            f"<button class='btn add' type='button' id='add' aria-expanded='false' aria-controls='addRow'>{e(H['add'])}</button></div>"
            "<div class='addrow' id='addRow' hidden>"
            f"<button class='btn' type='button' id='addPhotos'>{e(O['add_photos'])}</button>"
            f"<button class='btn' type='button' id='addVideos'>{e(O['add_videos'])}</button>"
            f"<p class='msg'>{e(O['add_say'])}</p><p class='went' id='addWent' role='status'></p></div>"
            "<div class='tools'>"
            f"<input type='search' id='q' placeholder='{e(H['search'], quote=True)}' aria-label='{e(H['search_aria'], quote=True)}'>"
            "<span id='chips'></span></div>"
            f"<div class='grid' id='grid'><p class='empty'>{e(H['loading'])}</p></div>"
            "<details class='outs' id='outs' hidden><summary id='outSum'></summary>"
            f"<p class='msg'>{e(O['out_say'])}</p><p class='went' id='outWent' role='status'></p><div id='outRows'></div></details>"
            "<div class='view' id='view' hidden><div class='vbox' role='dialog' aria-modal='true' aria-labelledby='vlabel'>"
            f"<button class='vx' type='button' id='vx' aria-label='{e(H['close'], quote=True)}'>&times;</button>"
            "<div class='vmedia' id='vmedia'></div>"
            "<div class='vinfo'><b id='vlabel'></b><small id='vmeta'></small><p class='desc' id='vdesc'></p>"
            f"<div class='vacts'><a class='btn solid' href='{e(reel, quote=True)}' id='vuse'>{e(H['use'])}</a>"
            f"<button class='btn' type='button' id='vrm'>{e(H['remove'])}</button></div>"
            "<div class='vsay' id='vsay' hidden><p class='msg' id='vmsg' role='status'></p>"
            f"<button class='btn' type='button' id='vback' hidden>{e(O['put_back'])}</button></div>"
            "<p class='msg' id='vnote'></p></div></div></div>")
        script = f"<script type='application/json' id='every-words'>{every_words()}</script><script>{EVERY_SCRIPT}</script>"
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{e(brand.title(O['tab_title']))}</title><style>{look.head_css()}{home_base.CSS}{EVERY_CSS}</style></head><body>"
            f"<div class='wrap'><div class='bar'>{look.crumbs(trail)}{brand.bar()}</div>{body}</div>{script}</body></html>")


def clip_for_page(vault_kit, ident):
    """GET /vault-clip?id=<shoot's folder>:<clip id>: the video this clip plays from, as the vault lists it.
    {"ok", "key", "play": it can be played now from /reel-video, "wait": it is being got ready}. A shoot's video
    that needs a small copy to play is got ready here (the copy is the vault's own, in the vault's hidden folder;
    the shoot's video is only read). Never a path."""
    import reel_page
    member, sep, cid = str(ident).rpartition(":")
    if not sep:
        return {"ok": False}
    try:
        _src, vname = reel_page.source_clip(vault_kit, member, cid)
    except (reel_page.Refused, reel_page.NotThere):
        return {"ok": False}
    v = reel_page.video_by_name(vault_kit, vname)
    if v is None or v["facts"].get("refused"):
        return {"ok": False}
    if v["facts"].get("plays_as_is"):
        return {"ok": True, "key": v["key"], "play": True, "wait": False}
    if (reel_page._prev_dir(vault_kit, v["key"]) / "preview.mp4").is_file():
        return {"ok": True, "key": v["key"], "play": True, "wait": False}
    if v.get("member"):
        reel_page.want_video(vault_kit, v["key"])
    st, _words = reel_page.preview_state(vault_kit, v)
    return {"ok": True, "key": v["key"], "play": False, "wait": st in ("waiting", "making", "ready")}


def out_photo_file(vault_kit, n_text):
    """The small copy of a photo that was taken out of the vault: the vault's own copy of it, by its vault number
    (made while it was in). None when there is none, or the number is not one that was taken out."""
    if not re.fullmatch(r"[0-9]{1,6}", n_text or ""):
        return None
    n = int(n_text)
    if not any(o["what"] == "photo" and o["id"] == n for o in vault.out_list(vault_kit)):
        return None
    d = Path(vault_kit) / ".kit" / "previews"
    try:
        import arrange
        front = f"{n:04d}-{arrange.SIZES['s']}-"
        hits = sorted((f for f in os.listdir(d) if f.startswith(front) and f.endswith(".jpg")), key=lambda f: (d / f).stat().st_mtime)
    except OSError:
        return None
    return d / hits[-1] if hits else None


def _bring_up_to_date(v):
    """The vault's list follows the shoots (and what was put back) on this page's own look, as the reel page's
    does; and the small copies its tiles show are started. Whatever goes wrong, the page goes on with what it has."""
    try:
        ch = vault.changed(v)
        if ch["changed"] and ch["settled"]:
            vault.relist(v, quick=True)
    except (Exception, SystemExit):  # noqa: BLE001
        pass
    try:
        import arrange
        arrange.start_previews(v)
    except (Exception, SystemExit):  # noqa: BLE001
        pass


def handle_every_get(handler, path, query):
    import arrange
    q = parse_qs(query or "", keep_blank_values=True)
    v = vault.find()
    if path == "/vault.html":
        return arrange._send_page(handler, every_html(v))
    if v is None:
        if path == "/vault-out-photo":
            return handler.send_error(404)
        return _send(handler, {"ok": False, "words": OUR_WORDS["no_vault"]}, 404)
    if path == "/vault-data":
        _bring_up_to_date(v)
        return _send(handler, every_data(v))
    if path == "/vault-clip":
        return _send(handler, clip_for_page(v, arrange._one(q, "id")))
    if path == "/vault-out-photo":
        f = out_photo_file(v, arrange._one(q, "n"))
        if f is None:
            return handler.send_error(404)
        try:
            data = f.read_bytes()
        except OSError:
            return handler.send_error(404)
        if data[:2] != b"\xff\xd8":
            return handler.send_error(404)
        handler.send_response(200)
        handler.send_header("Content-Type", "image/jpeg")
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Cache-Control", "private, max-age=3600")
        handler.send_header("Cross-Origin-Resource-Policy", "same-origin")
        handler.end_headers()
        handler.wfile.write(data)
        return None
    return handler.send_error(404)


def remove_from_page(v, body):
    """POST /vault-remove {what, id, on}: exactly those three fields, each of its own shape; anything else is
    refused whole. on False: Remove from my vault. on True: Put it back (and the list is brought up to date, so a
    photo is back on it with the number it had). (status, answer)."""
    import arrange
    if not isinstance(body, dict) or set(body) != {"what", "id", "on"} or body["what"] not in ("photo", "clip") or type(body["on"]) is not bool:
        return 400, {"ok": False, "words": arrange.NOT_UNDERSTOOD}
    ident = body["id"]
    if body["what"] == "photo" and type(ident) is not int:
        return 400, {"ok": False, "words": arrange.NOT_UNDERSTOOD}
    if body["what"] == "clip" and not (isinstance(ident, str) and 1 <= len(ident) <= 400):
        return 400, {"ok": False, "words": arrange.NOT_UNDERSTOOD}
    try:
        res = vault.in_or_out(v, body["what"], ident, body["on"])
    except vault.Trouble as t:
        return 200, {"ok": False, "words": str(t), "data": every_data(v)}
    if body["on"] and res["changed"] and body["what"] == "photo":
        try:
            vault.relist(v, quick=True)
        except vault.Trouble:
            pass                                    # another look is listing it right now: it is back on the next one
    if res["changed"]:
        _log(("put back in" if body["on"] else "took out of") + f" the vault: {body['what']} {str(ident)[:80]}")
    return 200, {"ok": True, "changed": res["changed"], "words": res["words"], "data": every_data(v)}
