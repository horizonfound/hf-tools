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

No page is ever sent a path: the vault is "the vault", a shoot is its folder name, and what a press did comes
back as plain words.
"""
import html
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

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
    "reel_sub": "The same reel maker as every post kit: your assistant picks, orders and cuts on the beat of your song, and it opens in CapCut. The only difference is it picks from every shoot in your vault.",
    "ask_h": "Tell your assistant what this reel is",
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
    "no_window": "The folder window didn't open. Tell your assistant which folder to add, and it'll copy the photos for you.",
    "no_vault": "Your vault isn't there right now. Is the drive plugged in?",
    "cant_start": "The copy couldn't start. Tell your assistant, and it'll sort it out.",
    "clips_opened": "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them.",
    "clips_behind": " It's behind this window: click {app} in {bar} to see it.",
    "clips_cant": "The folder for your videos didn't open. Tell your assistant, and it'll open it for you.",
    "not_running": "The Assistant isn't running right now. Ask your assistant to show your vault.",
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
    shoot's own name, never a path), how many photos are on the vault's list, how many videos it can draw from."""
    groups = vault.rows_by_group(vault_kit)
    shoots = [{"folder": g["kit"], "name": g["name"]} for g in groups if g["group"] == "kit"]
    photos = sum(len(g["rows"]) for g in groups)
    return {"shoots": shoots, "photos": photos, "clips": vault.clip_count(vault_kit)}


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
        photos = len(vault._rows(Path(v) / ".kit" / "sheet.json"))
        try:
            if vault.changed(v)["changed"]:              # its list is behind: the count it will have once opened
                own = len(vault._own_photos(v))
                photos = max(photos, sum(m["photos"] for m in mem) + own)
        except (OSError, vault.Trouble):
            pass
    else:
        photos = sum(m["photos"] for m in mem)
    return {"photos": photos, "made": v is not None, "thumbs": [m["folder"] for m in mem if m["photos"]][:3]}


# ---------- the routes ----------

GET_ROUTES = ("/vault-add-status",)
POST_ROUTES = ("/vault-open", "/vault-add", "/vault-clips")


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
        if _cross_site(handler):
            return _send(handler, {"ok": False}, 403)
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
    one is sent, JSON, a short body that is exactly {}. Whatever goes wrong, plain words and the server stays up."""
    import arrange
    try:
        refused = arrange.guard(handler, "application/json", POST_CAP, path)
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
