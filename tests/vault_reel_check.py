#!/usr/bin/env python3
"""The vault's reel page (Nicole's v29, 1.5): the four kinds, clips from every shoot, clip search (stage 9, part
`clips`); the photos step folded by shoot, photo search, "Pick my reel photos from my vault" (stage 10, part `photos`).

    python3 tests/guard.py 3000 python3 tests/vault_reel_check.py photos [--port 9985] [--no-chrome]

    python3 tests/guard.py 3000 python3 tests/vault_reel_check.py clips [--port 9985] [--work <folder under /private/tmp>]
    python3 tests/guard.py 800  python3 tests/vault_reel_check.py clips --no-chrome      (everything but the page in a browser)
    python3 tests/guard.py 3000 python3 tests/vault_reel_check.py empty [--port 9985] [--no-chrome]

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME; never the real
~/.studio, no drive, no real CapCut: a pretend CapCut folder under the run's own HOME; STUDIO_NO_WINDOWS_FOR_TESTS,
so no folder window is ever shown). The videos are tiny clips it makes itself with the Mac's own video tools (as
tests/video_check.py does). Two of the shoots each hold IMG_1234.MOV (two different videos) and SAME.MOV (the very
same file, same size and time), with named clips, as a footage look leaves them.

Part `clips`:
  * the chooser's words (hers) in the vault, and a plain post kit's chooser as it was;
  * each kind's steps, the same steps a plain post kit's kind shows;
  * the vault lists its own videos first, then both shoots' same-named videos apart, each with a key of its own
    (video.key alone would give the two SAME.MOV one key); a shoot's video is got ready only once it is wanted;
  * what the panel searches (no path), her search rule on it;
  * add-from: the shoot's clip in the open vault reel with its start, end and name, by you, named, from {kit, id};
    twice changes nothing; refused: a kit that is not in the vault, an id that is not a clip, a wrong shape, a field
    too many, another Origin, a plain post kit, a reel the page no longer shows; x takes it out and Undo puts it
    back; a tile's still is the vault's own;
  * the chat: `vault.py clips` (the note, every clip, the unnamed ones apart) and `vault.py use-clips`;
  * B-roll in the vault: a test make gets each clip's own video path, Save my video saves the MP4 in the vault's
    own Reels folder, and Add to my queue takes it;
  * Talking to camera opens the talking page for the vault (what it shows is said, pass or not);
  * EVERY OTHER POST KIT'S RECORDS AND FOLDERS ARE BYTE FOR BYTE UNCHANGED after all of it;
  * in a hidden Chrome: "laughing" opens only the shoot with a match with "1 found", leaves the other shut and
    Added to my vault open; + Add puts the clip in the reel with its name and the tile says ✓ Added; x takes it
    out; a reload keeps it; the ask box is saved with the reel; her words both ways when her handoff is here.

Part `photos` (three pretend shoots, one named for a person; pretend tags through PHOTO_WORDS_PRETEND and words
through `photo_words.py describe`; the page server itself has no pretend classifier, so nothing starts by itself):
  * her words on the vault's photos step, and both ways against her page when her handoff is here; our search
    placeholder, never her mock-up's "Search by shoot";
  * what the step searches (GET /reel-vault-photos: no path, no file name; only the vault; never cross-site);
  * the chat: `reel_page.py note "My vault"`, `vault.py find --photos`, `vault.py relist --sheets --only`, the pick
    saved with `kit.py picks --reel`, and the strip of vault numbers;
  * in a hidden Chrome: Added to my vault open on top with her line and + Add photos, each shoot folded shut with
    its picture, name and count; her progress line on the shoot still being looked at, gone once it is done;
    "laugh" opens only the shoots with a match and says how many; "hannah laughing" finds across the name and the
    words; nothing found says her line; a tap adds the photo to the order under its vault number, and a test make
    hands the reel script that photo's own path; a note changes the line to copy; a photo put in the vault's own
    Photos folder shows up under Added to my vault;
  * a plain post kit's photos page has none of it; EVERY OTHER POST KIT IS BYTE FOR BYTE UNCHANGED.

Part `empty` (a vault with video clips and NO photo at all: Nicole's B-roll-from-clips case; no other post kit):
  * the vault's list reads and is empty, and its reel page opens all the same: the chooser, the B-roll page with
    its own steps, its state (no photos), its videos, a new reel, clips made from its video, a save;
  * the watch step's preview, a test make ("2 clips and 0 photos"), Save my video into the vault's own Reels
    folder, Add to my queue;
  * the kinds that need photos say so in plain words: a make or a preview with no photos answers her "Pick a few
    photos for the reel first.", the photos step shows her "Photos you add to your vault show up here, open and
    ready." with + Add photos and Make my reel off, the talking page says our line (VAULT_OUR_WORDS);
  * the chat: `reel_page.py open`, `show` and `note`, `vault.py clips`, `talking_page.py open`;
  * a plain post kit whose list is empty is still told it isn't ready, on every route (only the vault changed);
  * a shoot that arrives afterwards joins the open reel page by itself, the B-roll reel's clips still there;
  * in a hidden Chrome: the B-roll page with its clips, the preview on the phone, Save my video pressed; the
    photos kind's page with her line and Make my reel off.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. A Mac
(the pretend photos are drawn with sips, the clips made with AVFoundation); anywhere else it says SKIP and exits 0.
"""
import argparse
import hashlib
import html as html_mod
import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
import vault_core_check as core  # noqa: E402
from vault_core_check import A, B, case, group, tree  # noqa: E402

VQ = "My%20vault"
BEAT60 = HERE / "fixtures" / "test-beat-60s.wav"
LIGHT = ("--single-process", "--disable-component-extensions-with-background-pages", "--enable-features=NetworkServiceInProcess2",
         "--disable-features=Translate,MediaRouter,OptimizationHints,DialMediaRouteProvider,SpareRendererForSitePerProcess,"
         "IsolateOrigins,site-per-process,WebUIOmniboxPopup,OmniboxWebUIPopup,WebUIOmniboxFullPopup,AimServerEligibility")

# the clips each shoot has, as a footage look (m...) and the photographer (u...) leave them in its reel record
A_CLIPS = [{"id": "m1-aaaaaa", "video": "Footage/IMG_1234.MOV", "start": 1.0, "end": 4.0, "label": "Laughing on the way back from the water", "photo": None, "keep": True},
           {"id": "u1-bbbbbb", "video": "IMG_1234.MOV", "start": 0.5, "end": 2.5, "label": "Your pick at 0:00.5", "photo": None, "keep": True, "by": "you"}]
B_CLIPS = [{"id": "m1-cccccc", "video": "Footage/IMG_1234.MOV", "start": 2.0, "end": 5.0, "label": "Walking in with the camera", "photo": None, "keep": True},
           {"id": "m2-dddddd", "video": "Footage/SAME.MOV", "start": 0.0, "end": 3.0, "label": "In the kitchen, pouring coffee", "photo": None, "keep": True}]

# Lines of her vault-reel-preview.html that are NOT on ours, on purpose, and why.
HERS_NOT_OURS = {
    "← My vault post kit": "her Back pill; ours is the path at the top (Home › My vault post kit › Reels)",
    "My vault post kit": "her Back pill; ours is the path at the top, which says the same words as its own step",
    "The Assistant": "the bar's wordmark (brand.py)", "by Horizon Found": "the bar's wordmark (brand.py)",
    "Preview: the reel page inside your vault post kit. The same four reels as every post kit; the difference is you can search your whole vault for clips and photos.": "her preview banner (test-only)",
    "In the real version, this is the talking reel page, using your vault's photos below.": "test-only",
    "The same as every reel.": "her placeholder for our real steps (song, vibe, watch)",
    "Add your song": "our real step's own heading", "Pick the vibe": "our real step's own heading",
    "Watch your reel before you make it": "our real step's own heading",
}
# Her lines that her page builds in its script (so they are not in her markup): typed here, each checked to be in
# her file as she wrote it and to be one of ours.
HERS_IN_SCRIPT = ["Every shoot", "Added to my vault ", "Clips you add to your vault show up here, open and ready.", "From its post kit · ",
                  " found", "+ Add", "✓ Added", " added", "Add clips from your search above.",
                  "Nothing matches that yet. Try other words, or tell your assistant what to look for.", "Copied"]


def skip(line):
    print("SKIP  " + line, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def no_path(obj):
    return not re.search(r"/private/|/Users/|/Volumes/|[A-Za-z]:\\\\|\.kit/", obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))


def her_page():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for d in sorted(r.glob("nicole-handoff-v29-*/unpacked/Carousel designer and reel picker/pages")) + sorted(r.glob("nicole-handoff-v29-*/Carousel designer and reel picker/pages")):
            if (d / "vault-reel-preview.html").is_file():
                return d / "vault-reel-preview.html"
    return None


def flat(markup):
    markup = re.sub(r"<(script|style)\b.*?</\1>", "", markup, flags=re.S)
    return [re.sub(r"\s+", " ", t).strip() for t in html_mod.unescape(re.sub(r"<[^>]+>", "¦", re.sub(r"</?(em|b)>", "", markup))).split("¦") if t.strip()]


def rp(s):
    os.environ["STUDIO_HOME"] = str(s.studio)
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import reel_page
    return reel_page


class World(core.Run):
    def __init__(self, work, port):
        super().__init__(work, port)
        self.store = self.work / "home" / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"     # a pretend CapCut

    # every other post kit, hashed whole (hidden folders too)
    def note(self):
        self.before = {d.name: tree(d) for d in self.members()}

    def get(self, path, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Host": "127.0.0.1:%d" % self.port}
        h.update(headers or {})
        c.request("GET", path, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            j = json.loads(raw.decode())
        except (ValueError, UnicodeDecodeError):
            j = None
        return r.status, j, raw

    def post(self, path, body, origin=None, more=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Host": "127.0.0.1:%d" % self.port, "Content-Type": "application/json", "Origin": origin or ("http://127.0.0.1:%d" % self.port)}
        h.update(more or {})
        c.request("POST", path, body=json.dumps(body).encode(), headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw.decode())
        except ValueError:
            return r.status, None

    def moment(self, body, **kw):
        return self.post("/reel-moment", dict({"kit": "My vault"}, **body), **kw)

    def state(self):
        return self.get("/reel-state?kit=" + VQ)[1]

    def foot(self, more=""):
        return self.get("/reel-footage?kit=" + VQ + more)[1]

    def record(self):
        try:
            return json.loads((self.vault() / ".kit" / "reel-page.json").read_text())
        except (OSError, ValueError):
            return {}

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def wait(self, fn, seconds=60, every=0.4):
        end = time.time() + seconds
        got = None
        while time.time() < end:
            got = fn()
            if got:
                return got
            time.sleep(every)
        return got


def make_world(s, run):
    """Two shoots with footage and clips, a third with none, the vault with a video of its own."""
    import reel_footage_check as rfc
    s.store.mkdir(parents=True, exist_ok=True)
    s.fake(s.target, "Fake beach", 8)
    s.fake(s.target, "Other farm", 9)
    s.fake(s.target, "Third hill", 8)
    clips = rfc.make_clips(run / "clips")
    for kit, src in ((A, "clip.mov"), (B, "sideways.mov")):
        (s.content / kit / "Footage").mkdir(exist_ok=True)
        shutil.copyfile(clips[src], s.content / kit / "Footage" / "IMG_1234.MOV")       # the same name, two videos
        shutil.copy2(clips["clip.mov"], s.content / kit / "Footage" / "SAME.MOV")        # the same file, name, size and time
    for kit, ms in ((A, A_CLIPS), (B, B_CLIPS)):
        (s.content / kit / ".kit" / "reel-page.json").write_text(json.dumps({"moments": ms, "moments_at": time.time()}), encoding="utf-8")
    code, out = s.cmd("vault.py", "ensure")
    if code != 0:
        raise RuntimeError("vault.py ensure: " + out[-300:])
    v = s.vault()
    shutil.copyfile(clips["clip.mov"], v / "Footage" / "own.mov")
    shutil.copyfile(BEAT60, v / "Music" / "Test beat.wav")
    s.note()
    return clips


# ---------- 1. the words, the kinds ----------

def steps_of(page):
    """The ids of the steps a page shows, in order (a step a kind doesn't use carries data-kind-hidden)."""
    return [m.group(2) for m in re.finditer(r"<section class='step(?: watch)?'( id='([A-Za-z0-9]+)')([^>]*)>", page) if "data-kind-hidden" not in m.group(3)]


def check_words(s):
    R = rp(s)
    code, _, raw = s.get("/reel.html?kit=" + VQ)
    page = raw.decode("utf-8", "replace")
    lines = flat(page)
    K, C = R.VAULT_KIND_WORDS, R.VAULT_CLIP_WORDS
    case("the vault's chooser: her eyebrow, title, lede, question and line", code == 200 and all(x in lines for x in (
        "My vault · Reel", "Make my reel", "From your vault: any clips and photos, from any of your shoots.", "Which reel do you want to create?",
        "The same four reels as every post kit. In your vault, each one can use clips and photos from any of your shoots.")), lines[:14])
    cards = re.findall(r"<a class='kind' id='(\w+)' href='([^']+)'><b>([^<]+)</b><span>([^<]+)</span></a>", page)
    case("her four cards, in her order, each with her vault line", [(c[2], html_mod.unescape(c[3])) for c in cards] == [
        ("Behind the scenes", "Video clips from your vault, mixed with your finished photos."),
        ("Just photos", "Your finished photos from any shoot, cut on the beat."),
        ("Talking to camera", "You talk about your work, and photos from your vault go with what you say."),
        ("B-roll", "Only video clips from your vault, cut on the beat. No photos.")], cards)
    case("each card is a plain link for the vault (the talking page for Talking to camera)", [html_mod.unescape(c[1]) for c in cards] == [
        "/reel.html?kit=My%20vault&kind=bts", "/reel.html?kit=My%20vault&kind=photos", "/talking.html?kit=My%20vault", "/reel.html?kit=My%20vault&kind=broll"], cards)
    case("no path on the vault's chooser", no_path(page))
    for kind in ("bts", "photos", "broll"):
        pv = s.get("/reel.html?kit=%s&kind=%s" % (VQ, kind))[2].decode("utf-8", "replace")
        case("%s in the vault shows only its own steps, in order" % kind, steps_of(pv) == STEPS[kind], steps_of(pv))
        case("...with her eyebrow, title and lede on top, and no path", "<span class='eyebrow'>My vault · Reel</span>" in pv and "<h1 id='title'>Make my reel<em>.</em></h1>" in pv
             and "<p class='lede'>From your vault: any clips and photos, from any of your shoots.</p>" in pv and no_path(re.sub(r"<script>.*?</script>", "", pv, flags=re.S)))
        if kind == "broll":
            case("step 1 is headed Your clips, with her panel above our join line and the footage editor",
                 "</span>Your clips</h2>" in pv and pv.index("id='vcFind'") < pv.index(html_mod.escape(R.VAULT_OUR_WORDS["foot_say2_html"], quote=False)) < pv.index("id='ed'"), None)
            got = flat(pv[pv.index("<div class='row2'>"):pv.index("<div class='vchips'")])
            case("the panel's words are hers: the search, Or tell your assistant, the examples, the line to copy", got == [
                C["vc_search_b"], C["vc_search_s"], C["vc_ask_b"], C["vc_ask_s"], C["vc_line"], "Copy"] and
                "placeholder='me with my camera, laughing, kitchen, beach'" in pv and 'placeholder="Optional: what you&#x27;d like your assistant to find"' in pv.replace("'Optional: what you&#x27;d like your assistant to find'", '"Optional: what you&#x27;d like your assistant to find"'), got)
            case("the reel's own clip cards are headed Your clips for this reel", "<span class='wl'>Your clips for this reel</span><span class='cnt' id='vcCnt'></span>" in pv)
    return page


STEPS = {"bts": ["step0", "step1", "step3", "stepDirect", "stepStyle", "step4", "watch"], "photos": ["step1", "step3", "stepDirect", "step4", "watch"], "broll": ["step0", "step3", "watch"]}


def check_plain(s):
    """Last of all (a plain post kit's own page makes small copies and facts of its own, in its own hidden folder,
    as it always has): a plain post kit's reel page has nothing of the vault's, and lists its videos as before."""
    R = rp(s)
    sys.path.insert(0, str(REEL))
    import video
    code, _, raw = s.get("/reel.html?kit=" + quote(A))
    plain = html_mod.unescape(raw.decode("utf-8", "replace"))
    case("a plain post kit's chooser has none of the vault's words", code == 200 and not any(v in plain for v in R.VAULT_KIND_WORDS.values()) and "this shoot's post kit" in plain)
    for kind in ("bts", "photos", "broll"):
        pa = s.get("/reel.html?kit=%s&kind=%s" % (quote(A), kind))[2].decode("utf-8", "replace")
        case("a plain post kit's %s page shows the same steps as the vault's, has no panel, and is headed as it was" % kind,
             steps_of(pa) == STEPS[kind] and "vcFind" not in pa and "<span class='wl'>Your clips</span>" in pa and "reel-vault" not in pa and "vaultClips" not in pa, steps_of(pa))
    case("a plain post kit lists its own two videos, by their plain names and video.key's keys", [(x["name"], x["key"]) for x in R.list_videos(s.content / A)]
         == [(n, video.key(s.content / A / "Footage" / n)) for n in ("IMG_1234.MOV", "SAME.MOV")])
    f = s.get("/reel-footage?kit=" + quote(A))[1]
    case("...and its page is told of them as before (never \"ask\")", [x["name"] for x in (f or {}).get("videos", [])] == ["IMG_1234.MOV", "SAME.MOV"]
         and all(x["preview"] != "ask" for x in f["videos"]), f)
    code, j = s.post("/reel-moment", {"kit": A, "do": "add-from", "from_kit": B, "from_id": "m1-cccccc"})
    case("add-from on a plain post kit: only in the vault", code == 400 and j["words"] == R.VAULT_OUR_WORDS["vault_only"], (code, j))
    case("a plain post kit has no clips list and no such stills", s.get("/reel-vault-clips?kit=" + quote(A))[0] == 404
         and s.get("/reel-vault-still?kit=%s&from=%s&id=m1-cccccc" % (quote(A), quote(B)))[0] == 404)


def check_her_words(s):
    R = rp(s)
    f = her_page()
    if f is None:
        skip("her words both ways: her v29 handoff isn't on this computer")
        return
    hers_raw = f.read_text(encoding="utf-8")
    hers = flat(hers_raw[hers_raw.index("<body"):])
    ours_tables = dict(R.WORDS)
    ours_tables.update(R.KIND_WORDS)
    ours_tables.update(R.VAULT_KIND_WORDS)
    ours_tables.update(R.VAULT_CLIP_WORDS)
    ours_tables.update(R.VAULT_PICK_WORDS)
    ours = set(html_mod.unescape(re.sub(r"<[^>]+>", "", v)) for v in ours_tables.values())
    ours.add("Make my reel.")
    ours.add(R.VAULT_PICK_WORDS["photo_ask_b"] + R.VAULT_PICK_WORDS["photo_ask_opt"])       # her label, one line once its <b> is gone
    ours.add(R.VAULT_PICK_WORDS["photo_ask_opt"].strip())
    miss = [x for x in hers if x not in ours and x not in HERS_NOT_OURS and x not in ("reel.", "Make my", "←")
            and not re.fullmatch(r"[1-9]", x)]
    case("every line her vault reel page shows is one of ours, whole (her test-only lines named)", not miss, miss)
    case("her title is ours: Make my reel.", "Make my <em>reel.</em>" in hers_raw and R.VAULT_KIND_WORDS["title_vault"] + "." == "Make my reel.")
    not_hers = [k for k, v in list(R.VAULT_KIND_WORDS.items()) + list(R.VAULT_CLIP_WORDS.items())
                if k not in ("title_vault", "vc_add_clips") and v not in hers and html_mod.escape(v, quote=False) not in hers_raw
                and not all(part in hers_raw for part in re.split(r"\{n\}", v) if part)]
    case("every word in VAULT_KIND_WORDS and VAULT_CLIP_WORDS is in her page, word for word", not not_hers, not_hers)
    case("her + Add clips (her script writes \"+ Add ${noun}\" with noun clips)", "+ Add ${noun}" in hers_raw and "'clips'" in hers_raw and R.VAULT_CLIP_WORDS["vc_add_clips"] == "+ Add clips")
    gone = [x for x in HERS_IN_SCRIPT if x not in hers_raw]
    case("the lines her page builds in its script are in her file as typed here", not gone, gone)
    case("none of her placeholder lines is on ours", not any(x in json.dumps(ours_tables, ensure_ascii=False) for x in ("The same as every reel.", "A moment you picked", "In the real version")))
    bad = [k for k, v in list(R.VAULT_OUR_WORDS.items()) + list(R.VAULT_CLIP_WORDS.items()) + list(R.VAULT_KIND_WORDS.items()) if "—" in v or "Claude" in v or re.search(r"\b(she|he|her|his)\b", v)]
    case("no em dash, no Claude, no she or he in any of the vault's words", not bad, bad)


# ---------- 2. the videos across kits ----------

def check_videos(s):
    R = rp(s)
    sys.path.insert(0, str(REEL))
    import video
    v = s.vault()
    f = s.foot()
    vids = (f or {}).get("videos") or []
    names = [x["name"] for x in vids]
    case("the vault lists its own video first, then each shoot's, a shoot's named <its folder>/<file>: both IMG_1234.MOV apart",
         names == ["own.mov", A + "/IMG_1234.MOV", A + "/SAME.MOV", B + "/IMG_1234.MOV", B + "/SAME.MOV"], names)
    case("no path in what the page is told about the videos", no_path(f), None)
    keys = [x["key"] for x in vids]
    same = video.key(s.content / A / "Footage" / "SAME.MOV") == video.key(s.content / B / "Footage" / "SAME.MOV")
    case("(the two SAME.MOV are the same name, size and time, so video.key alone gives them ONE key)", same)
    case("in the vault every video has a key of its own, also those two", len(set(keys)) == 5 and all(re.fullmatch(r"[0-9a-f]{12}", k) for k in keys), keys)
    by = {x["name"]: x for x in vids}
    case("the two IMG_1234.MOV are two videos (one wide, one tall)", (by[A + "/IMG_1234.MOV"]["w"], by[A + "/IMG_1234.MOV"]["h"]) == (640, 360)
         and (by[B + "/IMG_1234.MOV"]["w"], by[B + "/IMG_1234.MOV"]["h"]) == (360, 640), [(x["name"], x["w"], x["h"]) for x in vids])
    case("a shoot's video nothing has asked for is not got ready (\"ask\"); the vault's own is", all(by[n]["preview"] == "ask" for n in names[1:])
         and by["own.mov"]["preview"] != "ask", [(x["name"], x["preview"]) for x in vids])
    ready = s.wait(lambda: next((x for x in (s.foot() or {}).get("videos", []) if x["name"] == "own.mov" and x["preview"] == "ready"), None), 60)
    case("the vault's own video gets its stills, under the vault's own hidden folder", bool(ready) and (v / ".kit" / "footage" / ready["key"] / "preview.json").is_file() if ready else False, ready)
    lv = R.list_videos(v)
    case("list_videos: each shoot's video is read where it is (its own Footage folder), with the shoot's folder as \"member\"",
         [(x["name"], str(x["path"]), x.get("member")) for x in lv][1:] == [(k + "/" + n, str(s.content / k / "Footage" / n), k) for k in (A, B) for n in ("IMG_1234.MOV", "SAME.MOV")], lv)
    case("list_videos(members=False) is the vault's own only (the footage look, the talking page's picker)", [x["name"] for x in R.list_videos(v, members=False)] == ["own.mov"])
    case("a video by name: Footage/<shoot's folder>/<file> finds the shoot's own", str(R.video_by_name(v, "Footage/" + B + "/IMG_1234.MOV")["path"]) == str(s.content / B / "Footage" / "IMG_1234.MOV"))
    facts = json.loads((v / ".kit" / "footage" / "facts.json").read_text())
    case("the facts of all five are kept by the vault (its own .kit/footage/facts.json)", set(keys) <= set(facts), sorted(facts))
    s.untouched("the vault listed their videos")
    return by


# ---------- 3. the panel's catalog, add-from, the chat ----------

def check_catalog(s):
    R = rp(s)
    code, j, _ = s.get("/reel-vault-clips?kit=" + VQ)
    clips = {(c["kit"], c["id"]): c for c in (j or {}).get("clips", [])}
    case("GET /reel-vault-clips: the shoots that have clips, and every clip once", code == 200 and j["ok"] and sorted(x["kit"] for x in j["shoots"]) == sorted([A, B])
         and sorted(clips) == sorted([(A, "m1-aaaaaa"), (A, "u1-bbbbbb"), (B, "m1-cccccc"), (B, "m2-dddddd")]), j)
    case("each shoot with its name, its count and a small picture by number", all(x["clips"] == 2 and isinstance(x["thumb"], int) and x["name"] for x in j["shoots"]), j["shoots"])
    case("a clip: its name, its length, and the text search compares (its name and its shoot's name, folded)",
         clips[(A, "m1-aaaaaa")]["label"] == "Laughing on the way back from the water" and clips[(A, "m1-aaaaaa")]["len"] == 3.0
         and clips[(A, "m1-aaaaaa")]["text"].split() == "laughing on the way back from the water fake beach".split(), clips[(A, "m1-aaaaaa")])
    case("a clip of theirs with no name yet reads Not named yet, found by its shoot only", clips[(A, "u1-bbbbbb")]["label"] == "Not named yet" and clips[(A, "u1-bbbbbb")]["named"] is False
         and "pick" not in clips[(A, "u1-bbbbbb")]["text"], clips[(A, "u1-bbbbbb")])
    case("no path and no video file name in it", no_path(j) and "IMG_1234" not in json.dumps(j), None)
    import vault
    hit = [c for c in j["clips"] if vault.found(vault.search_words("me laughing", clips=True), c["text"])]
    case("her rule on it: \"me laughing\" finds the one clip (me is an everyday word)", [(c["kit"], c["id"]) for c in hit] == [(A, "m1-aaaaaa")] and "me" in j["everyday"], hit)
    code, _, _ = s.get("/reel-vault-clips?kit=" + VQ, headers={"Sec-Fetch-Site": "cross-site"})
    case("another website's page can't read it", code == 403, code)


def check_add(s, vids):
    R = rp(s)
    v = s.vault()
    st = s.state()
    case("(the vault's reel page answers its state)", bool(st and st.get("ok")), st and st.get("words"))
    code, j = s.moment({"do": "add-from", "from_kit": A, "from_id": "m1-aaaaaa"})
    m = ((j or {}).get("moments") or [None])[0]
    case("add-from: the shoot's clip is in the open vault reel with its start, end and name, by you, named, and where it came from",
         code == 200 and j["ok"] and len(j["moments"]) == 1 and len(j["added"]) == 1 and m["start"] == 1.0 and m["end"] == 4.0
         and m["label"] == "Laughing on the way back from the water" and m["by"] == "you" and m["named"] is True and m["from"] == {"kit": A, "id": "m1-aaaaaa"}
         and m["name"] == A + "/IMG_1234.MOV" and m["key"] == vids[A + "/IMG_1234.MOV"]["key"] and re.fullmatch(r"u\d+-[0-9a-f]{6}", m["id"]), (code, j))
    case("no path in the answer", no_path(j))
    rec = s.record()
    rm = (rec.get("moments") or [{}])[0]
    case("the record: the video named Footage/<shoot's folder>/<file>, from {kit, id}", rm.get("video") == "Footage/" + A + "/IMG_1234.MOV"
         and rm.get("from") == {"kit": A, "id": "m1-aaaaaa"} and rm.get("by") == "you" and rm.get("named") is True and rm.get("keep") is True, rm)
    before = sha(v / ".kit" / "reel-page.json")
    code, j = s.moment({"do": "add-from", "from_kit": A, "from_id": "m1-aaaaaa"})
    case("the same add again changes nothing (one card, the record byte for byte)", code == 200 and j["added"] == [] and j["already"] == 1 and len(j["moments"]) == 1
         and sha(v / ".kit" / "reel-page.json") == before, (code, j))
    code, j = s.moment({"do": "add-from", "from_kit": A, "from_id": "u1-bbbbbb"})
    m2 = next((x for x in (j or {}).get("moments", []) if x.get("from", {}).get("id") == "u1-bbbbbb"), {})
    case("a clip the shoot never named comes in unnamed (Your pick at ...), so the page offers to name it", code == 200 and m2.get("label") == "Your pick at 0:00.5"
         and m2.get("named") is False and len(j["moments"]) == 2, (code, j))
    before = sha(v / ".kit" / "reel-page.json")
    bad = [("a kit that is not in the vault", {"from_kit": "Nobody's shoot", "from_id": "m1-aaaaaa"}, 400, R.VAULT_OUR_WORDS["vault_not_in"]),
           ("a path for the kit", {"from_kit": "../" + A, "from_id": "m1-aaaaaa"}, 400, R.VAULT_OUR_WORDS["vault_not_in"]),
           ("the vault's own folder name as the kit", {"from_kit": "My vault", "from_id": "m1-aaaaaa"}, 400, R.VAULT_OUR_WORDS["vault_not_in"]),
           ("an id that is not a clip of that shoot", {"from_kit": A, "from_id": "m1-cccccc"}, 400, R.WORDS["moment_gone"]),
           ("an id of the wrong shape", {"from_kit": A, "from_id": "../../x"}, 400, None),
           ("no id", {"from_kit": A}, 400, None),
           ("the kit as a number", {"from_kit": 7, "from_id": "m1-aaaaaa"}, 400, None),
           ("a field it doesn't know (the page's own words for the clip)", {"from_kit": B, "from_id": "m1-cccccc", "label": "Mine now", "start": 0}, 400, None),
           ("a reel the page no longer shows", {"from_kit": B, "from_id": "m1-cccccc", "reel": "v7"}, 409, None)]
    for what, body, want, words in bad:
        code, j = s.moment(dict({"do": "add-from"}, **body))
        case("add-from refuses " + what, code == want and j and j["ok"] is False and (words is None or j["words"] == words), (code, j))
    code, j = s.moment({"do": "add-from", "from_kit": B, "from_id": "m1-cccccc"}, origin="http://evil.example")
    case("add-from refuses another Origin (403)", code == 403, (code, j))
    case("nothing was written by any refusal", sha(v / ".kit" / "reel-page.json") == before)
    # x takes it out, Undo puts it back, a reload keeps it
    mid = m2.get("id")
    code, j = s.moment({"do": "remove", "id": mid})
    case("the card's own x (remove) takes it out of the reel", code == 200 and [x["from"]["id"] for x in j["moments"]] == ["m1-aaaaaa"], (code, j))
    code, j = s.moment({"do": "restore", "id": mid, "at": 1})
    case("...and Undo puts it back, still knowing where it came from", code == 200 and sorted(x["from"]["id"] for x in j["moments"]) == ["m1-aaaaaa", "u1-bbbbbb"], (code, j))
    s.moment({"do": "remove", "id": mid})
    st = s.state()
    case("the page's state after a reload still has it, with from", [x.get("from") for x in st["moments"]] == [{"kit": A, "id": "m1-aaaaaa"}], st["moments"])
    # the video is now wanted: got ready by the vault, for itself
    got = s.wait(lambda: next((x for x in (s.foot() or {}).get("videos", []) if x["name"] == A + "/IMG_1234.MOV" and x["preview"] == "ready"), None), 90)
    case("the shoot's video a vault clip uses is got ready (stills in the vault's own .kit), the others still wait to be asked",
         bool(got) and (v / ".kit" / "footage" / got["key"] / "preview.json").is_file()
         and all(x["preview"] == "ask" for x in s.foot()["videos"] if x["name"] in (B + "/IMG_1234.MOV", B + "/SAME.MOV")), s.foot()["videos"])
    code, _, raw = s.get("/reel-video?kit=%s&key=%s" % (VQ, vids[A + "/IMG_1234.MOV"]["key"]), headers={"Range": "bytes=0-99"})
    case("the page plays it through the vault (GET /reel-video by the vault's key)", code in (200, 206) and len(raw) > 0, code)
    wk = vids[B + "/SAME.MOV"]["key"]
    s.foot("&want=" + wk)
    got = s.wait(lambda: next((x for x in (s.foot() or {}).get("videos", []) if x["key"] == wk and x["preview"] == "ready"), None), 90)
    case("opening a shoot's video in the editor (want=<key>) gets that one ready too", bool(got), s.foot()["videos"])
    # a tile's still
    def still(k, i):
        return s.get("/reel-vault-still?kit=%s&from=%s&id=%s" % (VQ, quote(k), i))
    got = s.wait(lambda: (lambda r: r if r[0] == 200 else None)(still(B, "m1-cccccc")), 60, 1.0)
    case("a tile's still for a shoot's clip: a picture, made by the vault in its own .kit the first time it is asked for",
         bool(got) and got[2][:2] == b"\xff\xd8" and any((v / ".kit" / "footage" / "moments").glob("x-*/*.jpg")), got and got[0])
    case("a still for a clip that is not there, or a shoot not in the vault: 404", still(B, "m1-aaaaaa")[0] == 404 and still("Nobody", "m1-cccccc")[0] == 404 and still("../" + A, "m1-aaaaaa")[0] == 404)
    s.untouched("add-from, the refusals, the stills and the videos got ready")


def check_chat(s):
    R = rp(s)
    v = s.vault()
    st = s.state()
    code, j = s.post("/reel-save", {"kit": "My vault", "stamp": st["stamp"], "base": st["rev"], "page": "vaultpage1", "saved": {"kind": "broll", "style": "broll", "footage": True,
                                                                                                                 "vault_ask": "Every clip of me walking in with my camera"}})
    case("what they typed in the ask box is saved with the reel (vault_ask), like the footage ask", code == 200 and j["ok"]
         and s.record()["saved"]["vault_ask"] == "Every clip of me walking in with my camera" and s.state()["saved"]["vault_ask"].startswith("Every clip"), (code, j))
    code, j = s.post("/reel-save", {"kit": "My vault", "stamp": st["stamp"], "base": s.state()["rev"], "page": "vaultpage1", "saved": {"vault_ask": "x" * 601}})
    case("an ask longer than the box holds is refused", code == 400, (code, j))
    rc, out = s.cmd("vault.py", "clips")
    case("vault.py clips: their note, the kind of reel, every named clip with its shoot, id, name and length", rc == 0
         and 'What they\'d like you to find (their words, from the box on the reel page): "Every clip of me walking in with my camera"' in out
         and "This reel is B-roll; it plays up to 12 clips." in out and f"{B}:m1-cccccc | Other farm | Walking in with the camera | 0:03" in out
         and f"{A}:m1-aaaaaa | Fake beach | Laughing on the way back from the water | 0:03   (in this reel already)" in out, out)
    case("...the unnamed ones apart, with the offer to name them", "Not named yet (1)" in out and f"Fake beach: {A}:u1-bbbbbb (0:02)   Offer: \"Name my clips for Fake beach\"" in out, out)
    case("...told to choose by words only, and how to add; no path in it", "never watch a video" in out and "use-clips --clips" in out and no_path(out), out)
    before = sha(v / ".kit" / "reel-page.json")
    for what, arg, want in (("a shoot that isn't in the vault", "Nobody:m1-cccccc", R.VAULT_OUR_WORDS["vault_not_in"]), ("a clip that isn't there", f"{B}:m9-ffffff", R.WORDS["moment_gone"]),
                            ("no colon", "m1-cccccc", "is not <shoot's folder>:<clip id>"), ("the same clip twice", f"{B}:m1-cccccc,{B}:m1-cccccc", "named twice"),
                            ("one good and one bad (all or nothing)", f"{B}:m1-cccccc,{B}:m9-ffffff", R.WORDS["moment_gone"])):
        rc, out = s.cmd("vault.py", "use-clips", "--clips", arg)
        case("vault.py use-clips refuses " + what + ", and nothing is written", rc == 2 and want in out and "Nothing was changed." in out and sha(v / ".kit" / "reel-page.json") == before, out)
    rc, out = s.cmd("vault.py", "use-clips", "--clips", f"{B}:m1-cccccc, {B}:m2-dddddd,{A}:m1-aaaaaa")
    ms = s.record().get("moments") or []
    case("vault.py use-clips adds the chosen clips, in the order given, the same add as the page's; one already there is left",
         rc == 0 and "Added 2 clips" in out and "1 was in that reel already" in out and [m["from"]["id"] for m in ms] == ["m1-aaaaaa", "m1-cccccc", "m2-dddddd"]
         and ms[2]["video"] == "Footage/" + B + "/SAME.MOV" and ms[1]["label"] == "Walking in with the camera", (out, ms))
    before = sha(v / ".kit" / "reel-page.json")
    rc, out = s.cmd("vault.py", "use-clips", "--clips", f"{B}:m1-cccccc")
    case("...and run again writes nothing", rc == 0 and "Nothing to add" in out and sha(v / ".kit" / "reel-page.json") == before, out)
    rc, out = s.cmd("vault.py", "use-clips", "--reel", "No such reel", "--clips", f"{B}:m1-cccccc")
    case("a reel that isn't there is refused", rc == 2 and "Nothing was changed." in out, out)
    rc, out = s.cmd("vault.py", "find", "walking", "--clips")
    case("vault.py find lists a clip a vault reel took from a shoot once, under its shoot", rc == 0 and out.count("m1-cccccc") == 1 and "Clips matching \"walking\": 1." in out, out)
    s.untouched("the chat's commands")


# ---------- 4. B-roll in the vault ----------

def wait_job(s, jid, seconds=180):
    end = time.time() + seconds
    while time.time() < end:
        j = s.get("/reel-job?kit=%s&id=%s" % (VQ, jid))[1]
        job = (j or {}).get("job")
        if job and job["state"] in ("done", "problem"):
            return job
        time.sleep(0.4)
    return None


def check_broll(s):
    R = rp(s)
    v = s.vault()
    st = s.state()
    sid = next((x["id"] for x in (s.get("/reel-songs?kit=" + VQ)[1] or {}).get("songs", []) if x["name"] == "Test beat"), None)
    ids = [m["id"] for m in st["moments"]]
    case("(set up: three clips from two shoots in the vault's B-roll reel, the test beat in its Music folder)", len(ids) == 3 and bool(sid), (ids, sid))
    body = {"kit": "My vault", "stamp": st["stamp"], "picks": [], "song": sid, "vibe": "beat", "test": True, "footage": True, "style": "broll", "clips": ids}
    code, j = s.post("/reel-make", body)
    job = wait_job(s, j["job"]["id"]) if code == 200 and (j or {}).get("job") else None
    case("a B-roll test make in the vault makes a plan: her Plan line, 3 clips and 0 photos", bool(job) and job["state"] == "done" and job["words"][0].startswith("Plan: 3 clips and 0 photos"), job or (code, j))
    case("no path in what the page is told", no_path(job or {}), job)
    try:
        cl = json.loads((v / ".kit" / "reels" / "clips.json").read_text())["clips"]
    except (OSError, ValueError, KeyError):
        cl = []
    want = [str(s.content / A / "Footage" / "IMG_1234.MOV"), str(s.content / B / "Footage" / "IMG_1234.MOV"), str(s.content / B / "Footage" / "SAME.MOV")]
    case("the reel script was handed each clip's OWN video: the shoot's file, where it is", [c.get("path") for c in cl] == want, cl)
    rc, out = s.cmd("reel_page.py", "show", "My vault")
    case("reel_page.py show for the vault: B-roll, 3 clips selected, every video listed", rc == 0 and "B-roll (clips only, no photos), 3 clips selected" in out and "5 videos" in out, out[-700:])
    # Save my video: the finished MP4, from the shoots' videos, into the vault's own Reels folder
    code, j = s.post("/reel-video", {"kit": "My vault", "stamp": s.state()["stamp"], "song": sid, "clips": ids, "variation": 0})
    job = wait_job(s, j["job"]["id"], 400) if code == 200 and (j or {}).get("job") else None
    name = "My vault B-roll.mp4"
    case("Save my video in the vault: saved as \"My vault B-roll.mp4\" in the vault's own Reels folder", bool(job) and job["state"] == "done" and job.get("video") == name
         and (v / "Reels" / name).is_file() and sorted(p.name for p in (v / "Reels").iterdir()) == [name], job or (code, j))
    made = [m for m in s.record().get("made") or [] if m.get("video")]
    case("the made entry: the video's file name, footage broll, the three clips, no path", bool(made) and made[-1]["video"] == name and made[-1]["footage"] == "broll"
         and made[-1]["clips"] == ids and no_path(made[-1]), made[-1:])
    case("the page's state says the reel is made", any(s.state()["made"].values()), s.state()["made"])
    code, j = s.post("/words-queue", {"kit": "My vault", "piece": "reel"})
    try:
        pieces = json.loads((s.studio / "posting.json").read_text()).get("pieces", [])
    except (OSError, ValueError):
        pieces = []
    mine = [p for p in pieces if p.get("kind") == "reel" and p.get("shoot_name") == "My vault"]
    case("Add to my queue takes the vault's reel, made from a saved video: the piece is My vault's, ready to post", code == 200 and (j or {}).get("ok") and len(mine) == 1
         and mine[0]["status"] == "green", (code, j, mine))
    s.untouched("a B-roll test make, Save my video and the queue")


# ---------- 5. Talking to camera ----------

def check_talking(s, clips):
    v = s.vault()
    code, _, raw = s.get("/talking.html?kit=" + VQ)
    page = raw.decode("utf-8", "replace")
    case("Talking to camera opens the talking page for the vault (200, its own page)", code == 200 and "talking" in page.lower() and "My vault" in page, code)
    code, j, _ = s.get("/talking-state?kit=" + VQ)
    case("its state answers for the vault, with no path", code == 200 and bool(j) and j.get("ok") is True and no_path(j), (code, j and j.get("words")))
    shutil.copyfile(clips["clip.mov"], v / "Talking" / "talk.mov")
    j2 = s.wait(lambda: (lambda x: x if x and any(t.get("name") == "talk.mov" for t in x.get("videos") or []) else None)(s.get("/talking-state?kit=" + VQ)[1]), 20)
    case("a video put in the vault's Talking folder is listed there", bool(j2), j)
    f = s.get("/reel-footage?kit=%s&for=talking" % VQ)[1]
    case("its Footage picker lists the vault's own videos only (a shoot's videos are not offered to lay over the talk: named in the plan)",
         [x["name"] for x in (f or {}).get("videos", [])] == ["own.mov"], f)
    n = len(s.rows())
    case("the photos it places are the vault's (every shoot's, by the vault's numbers): all %d on its list" % n, n == 25 and len(j.get("photos") or []) == 25, (n, len(j.get("photos") or [])))
    s.untouched("the talking page opened for the vault")


# ---------- 6. the page in a hidden Chrome ----------

def folds(c):
    return c.js("""Array.prototype.map.call(document.querySelectorAll('#vcRes details.vfold'), function(d){
      var s = d.querySelector('summary'); return {open: d.open, mine: d.classList.contains('mine'), nohit: d.classList.contains('nohit'),
        words: s.innerText.replace(/\\s+/g, ' ').trim(), hit: (s.querySelector('.hit') || {}).textContent || '',
        tiles: Array.prototype.map.call(d.querySelectorAll('.vc'), function(b){ return [b.querySelector('b').textContent, b.querySelector('.add').textContent, b.querySelector('.len').textContent]; })}; })""")


def type_in(c, sel, text):
    c.js("(function(){ var el = document.querySelector(%s); el.focus(); el.value = %s; el.dispatchEvent(new Event('input', {bubbles: true})); })()" % (json.dumps(sel), json.dumps(text)))


def cards(c):
    return c.js("Array.prototype.map.call(document.querySelectorAll('#clist .ci'), function(e){ return e.querySelector('b').innerText.replace(/^\\d+/, '').trim(); })")


def check_page(c, s):
    v = s.vault()
    # a reel of its own for the page, so the server parts' clips are not in the way
    code, j = s.post("/reel-version", {"kit": "My vault", "op": "new", "kind": "broll", "name": "Page reel"})
    case("(set up: a new B-roll reel in the vault for the page)", code == 200 and (j or {}).get("ok"), (code, j))
    c.open(s.url("/reel.html?kit=" + VQ))
    case("the chooser in a browser: My vault · Reel, Make my reel., her four cards", c.text(".eyebrow").strip().lower() == "my vault · reel" and c.text("#title").strip() == "Make my reel."
         and c.js("Array.prototype.map.call(document.querySelectorAll('.kind b'), function(b){ return b.textContent; })") == ["Behind the scenes", "Just photos", "Talking to camera", "B-roll"], c.text("#title"))
    c.open(s.url("/reel.html?kit=" + VQ + "&kind=broll"))
    c.wait_for("window.Reel && Reel.state() && Reel.vaultPanel && Reel.vaultPanel().ready", 30)
    nums = c.js("Array.prototype.map.call(document.querySelectorAll('section.step'), function(s){ return s.hidden ? null : [s.id, s.querySelector('.num') ? s.querySelector('.num').textContent : '']; }).filter(Boolean)")
    case("B-roll in the vault: its steps numbered in order, 1 Your clips, 2 the song, 3 watch (no photos step)", nums == [["step0", "1"], ["step3", "2"], ["watch", "3"]]
         and c.text("#step0 h2").replace("1", "").strip() == "Your clips", nums)
    f = folds(c)
    case("Added to my vault is open on top, with her line and + Add clips; each shoot is folded shut with its picture, name and count",
         len(f) == 3 and f[0]["mine"] and f[0]["open"] and f[0]["words"] == "Added to my vault" and c.text("#vcRes .addhere").replace("\n", " ").strip() == "Clips you add to your vault show up here, open and ready. + Add clips"
         and sorted(x["words"] for x in f[1:]) == ["Fake beach From its post kit · 2 clips", "Other farm From its post kit · 2 clips"] and not any(x["open"] or x["tiles"] for x in f[1:])
         and c.count("#vcRes details.vfold summary img") == 2, f)
    got = c.wait_for("Array.prototype.every.call(document.querySelectorAll('#vcRes details.vfold summary img'), function(i){ return i.naturalWidth > 0; })", 40)
    case("each shoot's small picture really loads", bool(got))
    case("the shoot chips: Every shoot, then each shoot", c.js("Array.prototype.map.call(document.querySelectorAll('#vcShoots button'), function(b){ return b.textContent; })")[0] == "Every shoot"
         and c.count("#vcShoots button") == 3 and c.count("#vcShoots button.on") == 1)
    case("the reel's own clips: Your clips for this reel, with her empty line", c.text(".cl-head .wl").strip().lower() == "your clips for this reel" and c.text("#clist").strip() == "Add clips from your search above.", c.text("#clist"))
    type_in(c, "#vcQ", "me laughing")
    c.wait_for("!!document.querySelector('#vcRes .hit')", 5)
    f = folds(c)
    beach = next(x for x in f if x["words"].startswith("Fake beach"))
    farm = next(x for x in f if x["words"].startswith("Other farm"))
    case("\"me laughing\": only the shoot with a match opens, with \"1 found\" and the one tile (+ Add, its length, its name)",
         beach["open"] and beach["hit"] == "1 found" and beach["tiles"] == [["Laughing on the way back from the water", "+ Add", "0:03"]], beach)
    case("...the other shoot stays shut, with nothing found said on it; Added to my vault stays open", not farm["open"] and farm["hit"] == "" and not farm["tiles"] and f[0]["mine"] and f[0]["open"], f)
    c.click("#vcRes details.vfold.nohit summary")
    time.sleep(0.3)
    case("a press on the shut shoot leaves it shut while the search has nothing in it", not next(x for x in folds(c) if x["words"].startswith("Other farm"))["open"])
    type_in(c, "#vcQ", "zebra")
    time.sleep(0.2)
    case("nothing found: her line", "Nothing matches that yet. Try other words, or tell your assistant what to look for." in c.text("#vcRes"), c.text("#vcRes"))
    type_in(c, "#vcQ", "laughing")
    c.wait_for("!!document.querySelector('#vcRes .vc')", 5)
    still_ok = c.wait_for("(function(){ var i = document.querySelector('#vcRes .vc img'); return i && i.naturalWidth > 0; })()", 40)
    case("the tile shows a still of the clip", bool(still_ok))
    c.click("#vcRes .vc")
    c.wait_for("!!document.querySelector('#vcRes .vc.on')", 10)
    case("+ Add: the tile says ✓ Added", [t[0][1] for t in [x["tiles"] for x in folds(c)] if t] == ["✓ Added"], folds(c))
    c.wait_for("document.querySelectorAll('#clist .ci').length === 1", 10)
    case("...and the shoot's clip is in the reel with its name, counted \"1 added\"", cards(c) == ["Laughing on the way back from the water"] and c.text("#vcCnt").strip() == "1 added", (cards(c), c.text("#vcCnt")))
    ms = s.wait(lambda: s.record().get("moments"), 5) or []
    case("the Assistant wrote it from the shoot's own record: its start and end, from {kit, id}", len(ms) == 1 and ms[0]["from"] == {"kit": A, "id": "m1-aaaaaa"} and (ms[0]["start"], ms[0]["end"]) == (1.0, 4.0), ms)
    c.click("#clist .ci .cx")
    c.wait_for("!document.querySelector('#vcRes .vc.on') && document.querySelectorAll('#clist .ci').length === 0", 10)
    case("the card's x takes it out: the tile says + Add again", [t[0][1] for t in [x["tiles"] for x in folds(c)] if t] == ["+ Add"] and not s.record().get("moments"), folds(c))
    c.click("#vcRes .vc")
    c.wait_for("document.querySelectorAll('#clist .ci').length === 1", 10)
    type_in(c, "#vcAsk", "Find me laughing at the beach")
    ok = s.wait(lambda: (s.record().get("saved") or {}).get("vault_ask") == "Find me laughing at the beach" and len(s.record().get("moments") or []) == 1, 8)
    case("what is typed in Or tell your assistant what to look for is saved with this reel", bool(ok), s.record().get("saved"))
    case("the line to copy is hers", c.text("#vcLine").strip() == "Find my clips in my vault" and c.text("#vcCopy").strip() == "Copy")
    c.reload()
    c.wait_for("window.Reel && Reel.state() && Reel.vaultPanel && Reel.vaultPanel().ready && document.querySelectorAll('#clist .ci').length === 1", 30)
    type_in(c, "#vcQ", "laughing")
    c.wait_for("!!document.querySelector('#vcRes .vc')", 5)
    case("a reload keeps it: the card is there, the tile says ✓ Added, the ask box has their words",
         cards(c) == ["Laughing on the way back from the water"] and c.js("document.querySelector('#vcRes .vc .add').textContent") == "✓ Added"
         and c.js("document.querySelector('#vcAsk').value") == "Find me laughing at the beach", cards(c))
    c.click("#vcRes .vc")
    c.wait_for("document.querySelectorAll('#clist .ci').length === 0", 10)
    case("✓ Added pressed again takes it out of this reel", not s.record().get("moments") and c.js("document.querySelector('#vcRes .vc .add').textContent") == "+ Add")
    # the chips, and the editor's drop-down
    type_in(c, "#vcQ", "")
    c.click("#vcShoots button", nth=c.js("Array.prototype.map.call(document.querySelectorAll('#vcShoots button'), function(b){ return b.textContent; }).indexOf('Other farm')"))
    time.sleep(0.3)
    f = folds(c)
    case("a shoot's chip shows that shoot's clips, open, \"2 found\"", next(x for x in f if x["words"].startswith("Other farm"))["hit"] == "2 found" and len(next(x for x in f if x["words"].startswith("Other farm"))["tiles"]) == 2, f)
    names = c.js("Array.prototype.map.call(document.querySelectorAll('#edTabs [data-ek] b'), function(b){ return b.textContent; })")
    case("the editor's Footage drop-down lists the vault's own video first, then each shoot's, the same-named ones apart",
         names == ["own.mov", A + "/IMG_1234.MOV", A + "/SAME.MOV", B + "/IMG_1234.MOV", B + "/SAME.MOV"], names)
    body = c.js("document.body.innerText")
    case("no path anywhere on the page", no_path(body) and no_path(c.js("document.documentElement.outerHTML.replace(/<script[^]*?<\\/script>/g, '')")))
    # a behind-the-scenes page: the panel too
    c.open(s.url("/reel.html?kit=" + VQ))
    s.untouched("the vault's reel page in a browser")


# ====================== part `photos` (stage 10): the photos step folded by shoot, photo search, the chat line ======================

H, F, T = "2026-11-01 Hannah beach", "2026-11-01 Other farm", "2026-11-01 Third hill"
PHOTO_TAGS = {"beach-002.jpg": ["green", "outdoor"], "beach-003.jpg": {"tags": ["sky"], "faces": 2}}
# her lines for the photos step that her page builds in its script
HERS_PHOTO_SCRIPT = ["Added to my vault ", "Photos you add to your vault show up here, open and ready.", "From its post kit · ", " found",
                     "Your assistant will pick these, or tap photos below to add your own.", "+ Add ${noun}", "'photos'",
                     "Nothing matches that yet. Try other words, or tell your assistant what to look for."]


class PhotoWorld(World):
    def __init__(self, work, port):
        super().__init__(work, port)
        self.table = self.work / "pretend-tags.json"
        self.table.write_text(json.dumps(PHOTO_TAGS), encoding="utf-8")
        self.tagging = dict(self.env, PHOTO_WORDS_PRETEND=str(self.table))     # only the test's own commands look at photos
        self.env.pop("PHOTO_WORDS_PRETEND", None)

    def file(self, name, obj):
        f = self.work / name
        f.write_text(json.dumps(obj), encoding="utf-8")
        return str(f)

    def n(self, kit, src):
        return next(x["n"] for x in self.rows() if x["kit"] == kit and x["src"] == src)


def make_photo_world(s):
    """Three shoots, one named for a person. Two are looked at (pretend tags) and have a few descriptions; the
    third has not been looked at yet. Nothing added to the vault itself, to begin with."""
    s.store.mkdir(parents=True, exist_ok=True)
    s.fake(s.target, "Hannah beach", 8)
    s.fake(s.target, "Other farm", 9)
    s.fake(s.target, "Third hill", 8)
    for kit in (H, F):
        code, out = s.cmd("photo_words.py", "tag", kit, env=s.tagging)
        if code != 0:
            raise RuntimeError("photo_words.py tag: " + out[-300:])
    for kit, words in ((H, {"1": "Mom laughing with the kids at the water", "4": "A kiss on the forehead"}),
                       (F, {"5": "Dad laughing by the barn door", "6": "Close-up of the ring"}),
                       (T, {"2": "Zoë on the hill at sunset"})):
        code, out = s.cmd("photo_words.py", "describe", kit, "--file", s.file("words-%s.json" % kit[-4:], {"photos": {k: {"words": v} for k, v in words.items()}}), env=s.tagging)
        if code != 0:
            raise RuntimeError("photo_words.py describe: " + out[-300:])
    code, out = s.cmd("vault.py", "ensure")
    if code != 0:
        raise RuntimeError("vault.py ensure: " + out[-300:])
    shutil.copyfile(BEAT60, s.vault() / "Music" / "Test beat.wav")
    s.note()


def check_photo_words(s):
    R = rp(s)
    code, _, raw = s.get("/reel.html?kit=" + VQ + "&kind=photos")
    page = html_mod.unescape(raw.decode("utf-8", "replace"))
    markup = re.sub(r"<script\b.*?</script>", "", page, flags=re.S)
    drawn = [k for k in R.VAULT_PICK_WORDS if k not in ("vp_talk_h2", "vp_talk_say", "vp_added", "vp_added_say", "vp_add_photos", "vp_from", "photo_for")]
    gone = [k for k in drawn if R.VAULT_PICK_WORDS[k].strip() not in markup]
    case("the vault's Just photos page shows her photos step: her heading, her two choices and their lines, her note and example, her line to copy, her two headings",
         code == 200 and not gone, gone)
    case("the lines the page's script draws are handed to it as words (Added to my vault, her line under it, + Add photos, From its post kit)",
         all(json.dumps(R.VAULT_PICK_WORDS[k], ensure_ascii=False)[1:-1] in page or R.VAULT_PICK_WORDS[k] in page for k in ("vp_added", "vp_added_say", "vp_add_photos", "vp_from")))
    case("the search box says ours (what is in a photo), never her mock-up's \"Search by shoot\"",
         "placeholder='laughing, a kiss, green backdrop, Hannah'" in page and "Search by shoot" not in page, re.findall(r"id='vpQ'[^>]*>", page))
    case("the plain page's own lines for one shoot are not on the vault's (\"What order would you like\", \"this shoot's Photos folder\", \"Only the ones in front of the white backdrop\")",
         not any(x in markup for x in ("What order would you like your photos in", "this shoot's Photos folder", "Only the ones in front of the white backdrop", "All your photos (drag one up")))
    case("the line to copy starts as hers: Pick my reel photos from my vault", "<span id='photoPaste'>Pick my reel photos from my vault</span>" in page)
    case("the step is there once, with the search, the chips and the grid inside All your photos", all(page.count(x) == 1 for x in ("id='vpQ'", "id='vpShoots'", "id='all'", "id='vpEmpty'", "id='photoAskIn'")))
    bro = s.get("/reel.html?kit=" + VQ + "&kind=broll")[2].decode("utf-8", "replace")
    case("a B-roll page in the vault still has no photos step showing", "step1" not in steps_of(bro), steps_of(bro))
    bad = [k for k, v in list(R.VAULT_PICK_WORDS.items()) + list(R.VAULT_PICK_OUR_WORDS.items()) if "—" in v or "Claude" in v or re.search(r"\b(she|he|his)\b", v)]
    case("no em dash, no Claude, no she or he in the photos step's words", not bad, bad)
    f = her_page()
    if f is None:
        skip("her photos step both ways: her v29 handoff isn't on this computer")
        return
    hers_raw = f.read_text(encoding="utf-8")
    body = hers_raw[hers_raw.index("<body"):]
    a0 = body.index('id="stepPhotos"')
    step = body[body.index(">", a0) + 1:body.rindex("<section", 0, body.index('id="stepSong"'))]
    hers = [x for x in flat(step) if not re.fullmatch(r"[1-9]", x) and x != "Copy"]
    ours = set(R.VAULT_PICK_WORDS.values()) | {R.VAULT_PICK_WORDS["photo_ask_b"] + R.VAULT_PICK_WORDS["photo_ask_opt"], R.VAULT_PICK_WORDS["photo_ask_opt"].strip()}
    miss = [x for x in hers if x not in ours]
    case("every line of her photos step is in VAULT_PICK_WORDS, whole", hers and not miss, miss)
    not_hers = [k for k, v in R.VAULT_PICK_WORDS.items() if k != "vp_add_photos" and v.strip() not in hers_raw and html_mod.escape(v.strip(), quote=False) not in hers_raw
                and not all(part in hers_raw for part in re.split(r"\{n\}", v) if part)]
    case("every word in VAULT_PICK_WORDS is in her page, word for word", not not_hers, not_hers)
    gone = [x for x in HERS_PHOTO_SCRIPT if x not in hers_raw]
    case("the photo lines her page builds in its script are in her file as typed here (+ Add photos is her \"+ Add ${noun}\")", not gone and R.VAULT_PICK_WORDS["vp_add_photos"] == "+ Add photos", gone)
    case("her mock-up's search placeholder is hers, and is not on ours on purpose", "Search by shoot: maternity, Hannah, Christmas" in hers_raw and "Search by shoot" not in json.dumps(dict(R.VAULT_PICK_WORDS, **R.VAULT_PICK_OUR_WORDS)))


def check_photo_catalog(s):
    sys.path.insert(0, str(SCRIPTS))
    import vault
    code, j, raw = s.get("/reel-vault-photos?kit=" + VQ)
    j = j or {}
    by = {x["kit"]: x for x in j.get("shoots", [])}
    case("GET /reel-vault-photos: the three shoots with their names, counts and a picture's number; nothing added to the vault yet",
         code == 200 and j.get("ok") and set(by) == {H, F, T} and (by[H]["name"], by[H]["photos"], by[F]["photos"], by[T]["photos"]) == ("Hannah beach", 8, 9, 8)
         and all(type(x["thumb"]) is int for x in by.values()), j.get("shoots"))
    case("...how many of each shoot's photos have been looked at: all of two shoots, none of the third", (by[H]["tagged"], by[F]["tagged"], by[T]["tagged"]) == (8, 9, 0) and j.get("can") is True
         and j.get("getting") == "Getting your photos ready to search: {done} of {total}.", (by, j.get("can")))
    case("...every photo by its vault number and its shoot's folder, 25 in all, and no path or file name in any of it",
         len(j.get("photos", [])) == 25 and sorted(x["n"] for x in j["photos"]) == sorted(x["n"] for x in s.rows()) and no_path(raw.decode()) and "beach-0" not in raw.decode() and ".jpg" not in raw.decode(), raw[:200])
    text = {x["n"]: x["text"] for x in j.get("photos", [])}

    def find(q):
        w = vault.search_words(q)
        return sorted(n for n, t in text.items() if all(x in t for x in w))
    n = s.n
    case("her rule on it: \"laugh\" finds the two laughing photos, one in each of two shoots (a part of a word matches)", find("laugh") == sorted([n(H, 1), n(F, 5)]), find("laugh"))
    case("\"hannah laughing\" finds across the shoot's name and the photo's words: the one photo", find("Hannah laughing") == [n(H, 1)], find("Hannah laughing"))
    case("\"me with the kiss\": everyday words ignored", find("me with the kiss") == [n(H, 4)], find("me with the kiss"))
    case("a tag finds too (\"green\": the photo the computer saw green in, in both looked-at shoots), and \"zoe\" finds Zoë", find("green") == sorted([n(H, 2), n(F, 2)]) and find("zoe") == [n(T, 2)], (find("green"), find("zoe")))
    case("the page's answer and `vault.py find` agree", all(str(x) in s.cmd("vault.py", "find", "laugh", "--photos")[1] for x in find("laugh")), s.cmd("vault.py", "find", "laugh", "--photos")[1])
    case("only the vault has it: a plain post kit gets 404", s.get("/reel-vault-photos?kit=" + quote(H))[0] == 404)
    code, _, _ = s.get("/reel-vault-photos?kit=" + VQ, headers={"Sec-Fetch-Site": "cross-site"})
    case("another website asking is refused", code == 403, code)
    s.untouched("reading what the photos step searches")


def check_photo_chat(s):
    v = s.vault()
    n = s.n
    code, j = s.post("/reel-version", {"kit": "My vault", "op": "new", "kind": "photos", "name": "Moms"})
    case("(set up: a second reel in the vault, a Just photos one called Moms)", code == 200 and (j or {}).get("ok"), (code, j))
    st = s.state()
    code, j = s.post("/reel-save", {"kit": "My vault", "stamp": st["stamp"], "base": st["rev"], "page": "vaultpage2", "reel": st["current"],
                                    "saved": {"kind": "photos", "photo_ask": "Moms laughing, from any shoot."}})
    case("(set up: their note for that reel, saved as the page saves it)", code == 200 and (j or {}).get("ok") and (s.state()["saved"] or {}).get("photo_ask") == "Moms laughing, from any shoot.", (code, j))
    code, out = s.cmd("reel_page.py", "note", "My vault", "--reel", "Moms")
    case("`reel_page.py note \"My vault\" --reel Moms` prints the note word for word and that the pick is for Moms", code == 0 and "Moms laughing, from any shoot." in out and "\"Moms\"" in out, out)
    case("...says it is the vault with its 25 photos, and to narrow with vault.py find, then relist --sheets --only", "This is the vault: 25 photos" in out and "vault.py find" in out and "--photos" in out and "relist --sheets --only" in out, out)
    case("...and prints the command that saves the pick for this reel", "kit.py picks \"My vault\" --reel" in out, out)
    code, out = s.cmd("vault.py", "find", "moms laughing", "--photos")
    case("`vault.py find \"moms laughing\" --photos`: nothing (no description says moms), said plainly", code == 0 and ": 0 " in out and "None." in out, out)
    code, out = s.cmd("vault.py", "find", "laughing", "--photos")
    want = [n(H, 1), n(F, 5)]
    case("`vault.py find \"laughing\" --photos` prints the two photos' vault numbers, by shoot", code == 0 and all(re.search(r"\b%d\b" % x, out) for x in want) and "Hannah beach" in out and "Other farm" in out, out)
    before = sha(v / ".kit" / "sheet.json")
    code, out = s.cmd("vault.py", "relist", "--sheets", "--only", "%d, %d, 999" % (want[0], want[1]))
    sheets = [ln.split("Sheet: ", 1)[1] for ln in out.splitlines() if ln.startswith("Sheet: ")]
    case("`vault.py relist --sheets --only` draws one sheet of the two, in a shortlist folder of the vault's own, and says the number that is not a photo",
         code == 0 and len(sheets) == 1 and Path(sheets[0]).is_file() and Path(sheets[0]).parent == v / ".kit" / "reels" / "shortlist" and "2 photos on this shortlist" in out
         and "25 photos in the vault" in out and "999" in out, out)
    case("...and changes nothing else: the vault's list is byte for byte what it was", sha(v / ".kit" / "sheet.json") == before)
    code, out = s.cmd("vault.py", "relist", "--sheets", "--only", "1 to 3")
    case("a run of numbers (\"1 to 3\") is three photos", code == 0 and "3 photos on this shortlist" in out, out)
    for bad, why in (("abc", "not a number"), ("", "no numbers"), ("5-2", "a run backwards")):
        code, out = s.cmd("vault.py", "relist", "--sheets", "--only", bad)
        case("--only %r is refused (%s), nothing drawn" % (bad, why), code == 2 and "STOP" in out and "Sheet:" not in out, out)
    code, out = s.cmd("vault.py", "relist", "--only", "1")
    case("--only without --sheets is refused", code == 2 and "STOP" in out, out)
    code, out = s.cmd("vault.py", "relist", "--sheets", "--only", "999")
    case("only numbers that are no photo: STOP, said plainly", code == 2 and "none of those numbers" in out, out)
    picks = "%d+,%d" % (want[0], want[1])
    code, out = s.cmd(REEL / "reel.py", "strip", "--kit", str(v), "--folder", str(v / "Photos"), "--shoot", "My vault", "--picks", picks)
    case("the strip draws the pick by vault numbers (--kit the vault, --folder its own Photos folder)", code == 0 and "Strip:" in out, out)
    code, out = s.cmd("kit.py", "picks", "My vault", "--reel", picks, "--for-reel", "Moms")
    st = s.state()
    case("`kit.py picks \"My vault\" --reel ... --for-reel Moms` saves the pick under the vault's numbers, and the page's state has it",
         code == 0 and [(x["n"], x["h"]) for x in st.get("claude") or []] == [(want[0], "+"), (want[1], "")], (out, st.get("claude")))
    # a test make: each picked photo's own path
    body = {"kit": "My vault", "stamp": st["stamp"], "picks": [{"n": want[0], "h": "+"}, {"n": want[1], "h": ""}, {"n": n(T, 2), "h": ""}], "song": "", "vibe": "beat", "test": True}
    code, j = s.post("/reel-make", body)
    job = wait_job(s, j["job"]["id"]) if code == 200 and (j or {}).get("job") else None
    case("a test make of the Moms reel finishes, nothing made", job and job["state"] == "done" and job.get("dry") is True, (code, j, job))
    try:
        paths = [x["path"] for x in json.loads((v / ".kit" / "reels" / "reel.json").read_text())["plan"]["photos"]]
    except (OSError, ValueError, KeyError):
        paths = []
    rows = {x["n"]: x for x in s.rows()}
    want_paths = [str(s.content / k / "Photos" / Path(rows[x]["file"]).name) for k, x in ((H, want[0]), (F, want[1]), (T, n(T, 2)))]
    case("...and the reel script was handed each photo's own path, in its own shoot's Photos folder", paths == want_paths, paths)
    s.untouched("the chat's note, find, shortlist sheets, pick and test make")


def pfolds(c):
    return c.js("""Array.prototype.map.call(document.querySelectorAll('#all details.vfold'), function(d){
      var s = d.querySelector('summary'); return {open: d.open, mine: d.classList.contains('mine'), nohit: d.classList.contains('nohit'),
        name: (s.querySelector('span') || s).textContent.trim(), n: s.querySelector('.n').textContent, prog: (s.querySelector('.prog') || {}).textContent || '',
        hit: (s.querySelector('.hit') && !s.querySelector('.hit').hidden) ? s.querySelector('.hit').textContent : '', img: !!s.querySelector('img'),
        all: d.querySelectorAll('.pick').length,
        seen: Array.prototype.filter.call(d.querySelectorAll('.pick'), function(t){ return d.open && !t.classList.contains('off') && t.getBoundingClientRect().width > 0; }).map(function(t){ return +t.dataset.n; })}; })""")


def pfold(c, name):
    return next(x for x in pfolds(c) if x["name"].startswith(name))


def check_photo_page(c, s):
    v = s.vault()
    n = s.n
    c.open(s.url("/reel.html?kit=" + VQ + "&kind=photos"))
    c.wait_for("window.Reel && Reel.state() && Reel.vaultPhotos && Reel.vaultPhotos.look().ready", 40)
    case("the page is the Moms reel's, a Just photos reel in the vault: Choose your photos is step 1", c.text("#step1 h2").replace("1", "").strip() == "Choose your photos", c.text("#step1 h2"))
    case("a new reel starts on I'll drag them in myself, with her line where its photos will be: Your assistant will pick these, or tap photos below to add your own.",
         c.count("#reel .tile") == 0 and c.js("document.querySelector('#vpEmpty').hidden") is False and c.text("#vpEmpty").strip() == "Your assistant will pick these, or tap photos below to add your own."
         and c.text("#vpCnt").strip() == "", c.text("#vpEmpty"))
    c.click("#useClaude")
    c.wait_for("document.querySelectorAll('#reel .tile').length === 2", 5)
    case("Let my assistant choose shows the assistant's pick for this reel under Your photos for this reel, counted \"2 added\"",
         c.js("Array.prototype.map.call(document.querySelectorAll('#reel .tile'), function(t){ return +t.dataset.n; })") == [n(H, 1), n(F, 5)]
         and c.text(".vp-head .wl").strip().lower() == "your photos for this reel" and c.text("#vpCnt").strip() == "2 added" and c.js("document.querySelector('#vpEmpty').hidden") is True, c.text("#vpCnt"))
    c.js("document.querySelector('#allBox').open = true")
    f = pfolds(c)
    case("Added to my vault is on top and open, with her line and + Add photos",
         f[0]["mine"] and f[0]["open"] and f[0]["name"].startswith("Added to my vault") and f[0]["all"] == 0
         and c.text("#all .vfold.mine .addhere").replace("\n", " ").strip() == "Photos you add to your vault show up here, open and ready. + Add photos", (f[0], c.text("#all .vfold.mine .addhere")))
    case("under it each shoot is folded shut, with its small picture, its name and its count",
         len(f) == 4 and sorted((x["name"], x["n"]) for x in f[1:]) == [("Hannah beach", "From its post kit · 8 photos"), ("Other farm", "From its post kit · 9 photos"), ("Third hill", "From its post kit · 8 photos")]
         and all(x["img"] and not x["open"] and not x["seen"] and not x["mine"] for x in f[1:]), f)
    got = c.wait_for("Array.prototype.every.call(document.querySelectorAll('#all details.vfold summary img'), function(i){ return i.naturalWidth > 0; })", 40)
    case("each shoot's small picture really loads (the vault's own small copy of one of its photos)", bool(got) and c.count("#all details.vfold summary img") == 3)
    case("every photo of every shoot is in its own shoot's fold (8, 9 and 8)", (pfold(c, "Hannah")["all"], pfold(c, "Other")["all"], pfold(c, "Third")["all"]) == (8, 9, 8))
    case("the shoot that has not been looked at yet says her line; the two that have say nothing",
         pfold(c, "Third")["prog"] == "Getting your photos ready to search: 0 of 8." and pfold(c, "Hannah")["prog"] == "" and pfold(c, "Other")["prog"] == "", pfold(c, "Third"))
    case("the shoot chips: Every shoot, then each shoot", c.js("Array.prototype.map.call(document.querySelectorAll('#vpShoots button'), function(b){ return b.textContent; })")[0] == "Every shoot" and c.count("#vpShoots button") == 4)
    c.click("#all details.vfold:not(.mine) summary", nth=0)
    time.sleep(0.3)
    first = pfolds(c)[1]
    case("a tap on a shoot opens it and shows its photos", first["open"] and len(first["seen"]) == first["all"], first)
    c.click("#all details.vfold:not(.mine) summary", nth=0)
    time.sleep(0.3)
    case("...and a tap again shuts it", not pfolds(c)[1]["open"])
    # the search
    type_in(c, "#vpQ", "laugh")
    c.wait_for("document.querySelectorAll('#all .hit:not([hidden])').length === 2", 5)
    hb, of, th = pfold(c, "Hannah"), pfold(c, "Other"), pfold(c, "Third")
    case("\"laugh\" opens only the two shoots with a match, with \"1 found\" on each and only the matching photo showing",
         hb["open"] and hb["hit"] == "1 found" and hb["seen"] == [n(H, 1)] and of["open"] and of["hit"] == "1 found" and of["seen"] == [n(F, 5)], (hb, of))
    if os.environ.get("VAULT_REEL_SHOT"):         # a picture for a look by eye (never on by itself)
        c.js("document.querySelector('#vpFind').scrollIntoView()")
        time.sleep(1.0)
        print("SHOT  " + str(c.screenshot("vault-photos-search.png")), flush=True)
    case("...the shoot with nothing found stays shut and says nothing; Added to my vault stays open", not th["open"] and th["nohit"] and th["hit"] == "" and pfolds(c)[0]["open"], th)
    c.click("#all details.vfold.nohit summary")
    time.sleep(0.3)
    case("a press on the shut shoot leaves it shut while the search has nothing in it", not pfold(c, "Third")["open"])
    type_in(c, "#vpQ", "Hannah laughing")
    c.wait_for("document.querySelectorAll('#all .hit:not([hidden])').length === 1", 5)
    hb, of = pfold(c, "Hannah"), pfold(c, "Other")
    case("\"Hannah laughing\" finds across the shoot's name and the photo's words: one shoot open, \"1 found\", the other shut", hb["open"] and hb["hit"] == "1 found" and hb["seen"] == [n(H, 1)] and not of["open"] and of["nohit"], (hb, of))
    type_in(c, "#vpQ", "zebra")
    time.sleep(0.3)
    case("nothing found: her line, and every shoot shut", c.js("document.querySelector('#vpNone').hidden") is False and c.text("#vpNone").strip() == "Nothing matches that yet. Try other words, or tell your assistant what to look for."
         and not any(x["open"] for x in pfolds(c)[1:]), pfolds(c))
    type_in(c, "#vpQ", "kiss")
    c.wait_for("document.querySelectorAll('#all .hit:not([hidden])').length === 1", 5)
    case("(her line goes when something is found)", c.js("document.querySelector('#vpNone').hidden") is True)
    # a tap adds the photo, under its vault number
    kiss = n(H, 4)
    c.click("#all .pick[data-n='%d']" % kiss, check=False)
    c.wait_for("document.querySelectorAll('#reel .tile').length === 3", 5)
    order = c.js("Array.prototype.map.call(document.querySelectorAll('#reel .tile'), function(t){ return +t.dataset.n; })")
    case("a tap on the found photo adds it to the order under its vault number, counted \"3 added\", and the photo is marked as in", order == [n(H, 1), n(F, 5), kiss] and c.text("#vpCnt").strip() == "3 added"
         and c.js("document.querySelector('#all .pick[data-n=\"%d\"]').classList.contains('in')" % kiss), order)
    ok = s.wait(lambda: [x["n"] for x in ((s.state() or {}).get("saved") or {}).get("picks") or []] == order, 8)
    case("...saved with this reel as their own order", bool(ok) and (s.state()["saved"] or {}).get("mine") is True, (s.state() or {}).get("saved"))
    st = s.state()
    body = {"kit": "My vault", "stamp": st["stamp"], "picks": [{"n": x, "h": ""} for x in order], "song": "", "vibe": "beat", "test": True}
    code, j = s.post("/reel-make", body)
    job = wait_job(s, j["job"]["id"]) if code == 200 and (j or {}).get("job") else None
    try:
        paths = [x["path"] for x in json.loads((v / ".kit" / "reels" / "reel.json").read_text())["plan"]["photos"]]
    except (OSError, ValueError, KeyError):
        paths = []
    rows = {x["n"]: x for x in s.rows()}
    case("a test make of that order hands the reel script the tapped photo's own path, in its own shoot's Photos folder",
         job and job["state"] == "done" and paths and paths[-1] == str(s.content / H / "Photos" / Path(rows[kiss]["file"]).name) and len(paths) == 3, (job, paths))
    c.click("#all .pick[data-n='%d']" % kiss, check=False)
    c.wait_for("document.querySelectorAll('#reel .tile').length === 2", 5)
    case("a tap again takes it out", c.text("#vpCnt").strip() == "2 added")
    # the chips
    type_in(c, "#vpQ", "")
    c.click("#vpShoots button", nth=c.js("Array.prototype.map.call(document.querySelectorAll('#vpShoots button'), function(b){ return b.textContent; }).indexOf('Other farm')"))
    time.sleep(0.3)
    case("a shoot's chip opens that shoot with all its photos, \"9 found\", and leaves the others shut", pfold(c, "Other")["hit"] == "9 found" and len(pfold(c, "Other")["seen"]) == 9 and not pfold(c, "Hannah")["open"], pfolds(c))
    c.click("#vpShoots button", nth=0)
    time.sleep(0.3)
    case("Every shoot: the search is off, every shoot folded shut again", not any(x["open"] or x["hit"] for x in pfolds(c)[1:]), pfolds(c))
    # the note and the line to copy
    case("the line to copy: hers, the reel's name (the vault has two reels), and the note that is saved", c.text("#photoPaste").strip() == "Pick my reel photos from my vault, Moms, and follow my note"
         and c.js("document.querySelector('#photoAskIn').value") == "Moms laughing, from any shoot.", c.text("#photoPaste"))
    type_in(c, "#photoAskIn", "")
    case("with no note the line is hers and the reel's name", c.text("#photoPaste").strip() == "Pick my reel photos from my vault, Moms", c.text("#photoPaste"))
    type_in(c, "#photoAskIn", "My favorite maternity photos from this year.")
    ok = s.wait(lambda: ((s.state() or {}).get("saved") or {}).get("photo_ask") == "My favorite maternity photos from this year.", 8)
    case("a note typed changes the line (\", and follow my note\") and is saved with this reel", c.text("#photoPaste").strip() == "Pick my reel photos from my vault, Moms, and follow my note" and bool(ok), (c.text("#photoPaste"), (s.state() or {}).get("saved")))
    # her progress line goes once the shoot has been looked at
    code, out = s.cmd("photo_words.py", "tag", T, env=s.tagging)
    gone = c.wait_for("(function(){ var p = null; document.querySelectorAll('#all details.vfold').forEach(function(d){ if ((d.querySelector('summary span') || {textContent: ''}).textContent.indexOf('Third') === 0) p = d.querySelector('.prog'); }); return p && p.textContent === ''; })()", 15)
    case("once the third shoot has been looked at, her line goes by itself", code == 0 and bool(gone), (out[-200:], pfold(c, "Third")))
    s.note()             # (the test's own command looked at that shoot's photos: its words file is new)
    type_in(c, "#vpQ", "zoe sunset")
    c.wait_for("document.querySelectorAll('#all .hit:not([hidden])').length === 1", 5)
    case("\"zoe sunset\" finds Zoë's photo in it (accents folded)", pfold(c, "Third")["seen"] == [n(T, 2)], pfold(c, "Third"))
    type_in(c, "#vpQ", "")
    # + Add photos, and a photo put in the vault's own Photos folder
    c.click("#vpAdd")
    said = c.wait_for("document.querySelector('#vpAddSay').textContent.length > 0 && document.querySelector('#vpAddSay').textContent.indexOf('Opening') < 0", 10)
    case("+ Add photos opens the vault's own Photos folder, and says so right beside the button (no window in a test)", bool(said) and no_path(c.text("#vpAddSay")), c.text("#vpAddSay"))
    src = s.content / H / "Photos" / "beach-002.jpg"
    shutil.copyfile(src, v / "Photos" / "dropped.jpg")
    old = time.time() - 60
    os.utime(v / "Photos" / "dropped.jpg", (old, old))
    c.wait_for("!!document.querySelector('#showNew')", 30)
    case("a photo put in the vault's own Photos folder is noticed by the page itself: 1 new photo in", "1 new photo in." in c.text("#addPhotosSay"), c.text("#addPhotosSay"))
    c.click("#showNew")
    c.wait_for("window.Reel && Reel.state() && Reel.vaultPhotos && Reel.vaultPhotos.look().ready && document.querySelectorAll('#all .vfold.mine .pick').length === 1", 40)
    c.js("document.querySelector('#allBox').open = true")
    mine = pfolds(c)[0]
    own = next(x["n"] for x in s.rows() if x["kit"] == "")
    case("...and after Show my new photos it is under Added to my vault, open, counted, with a new number; + Add photos is still there",
         mine["open"] and mine["seen"] == [own] and mine["n"] == "1 photo" and own == max(x["n"] for x in s.rows()) and c.count("#vpAdd") == 1
         and c.js("document.querySelector('#all .vfold.mine .line1').hidden") is True, mine)
    case("the reel kept its order and its note through the reload", c.js("Array.prototype.map.call(document.querySelectorAll('#reel .tile'), function(t){ return +t.dataset.n; })") == [n(H, 1), n(F, 5)]
         and c.js("document.querySelector('#photoAskIn').value") == "My favorite maternity photos from this year.")
    body = c.js("document.body.innerText")
    case("no path anywhere on the page", no_path(body) and no_path(c.js("document.documentElement.outerHTML.replace(/<script[^]*?<\\/script>/g, '')")))
    errs = c.page_errors()
    case("no script error on the page", not errs, errs)
    c.open(s.url("/reel.html?kit=" + VQ))
    time.sleep(1.5)
    s.untouched("the vault's photos step in a browser")


def check_photo_plain(s):
    R = rp(s)
    pa = s.get("/reel.html?kit=%s&kind=photos" % quote(H))[2].decode("utf-8", "replace")
    case("a plain post kit's photos page has none of it: no search box, no folds, its own words, the order script as it was",
         not any(x in pa for x in ("vpQ", "vpFind", "vaultPhotos", "reel-vault-photos", "vp-head", "from my vault")) and R.ORDER_JS in pa
         and "<div id='all'></div>" in pa and html_mod.escape(R.WORDS["order_say"]) in pa and R.ORDER_JS != R.vault_order_js(), "")
    case("...and built twice is the same page, with or without a vault page built in between", R.page_html("K", "K", True, "photos") == (R.page_html("K", "K", True, "photos", True) and R.page_html("K", "K", True, "photos")))


def main_photos(a):
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-reel-photos-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    run = work / time.strftime("run-%H%M%S")
    (run / "home").mkdir(parents=True)
    s = PhotoWorld(run, a.port)
    try:
        group("(making three shoots, two of them looked at and described, and the vault)")
        make_photo_world(s)
        s.start()
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 20 and s.port not in (8790, 8791, 8792, 8799))
        group("her words: Choose your photos, in the vault")
        check_photo_words(s)
        group("what the photos step searches")
        check_photo_catalog(s)
        group("the chat: Pick my reel photos from my vault")
        check_photo_chat(s)
        if a.no_chrome:
            skip("the photos step in a browser: --no-chrome")
        elif not chrome_drive.find_chrome():
            skip("the photos step in a browser: no Chrome on this computer")
        else:
            group("the vault's photos step in a hidden Chrome")
            with chrome_drive.Chrome(work=str(run), size=(1100, 900), extra_args=LIGHT) as c:
                check_photo_page(c, s)
        group("a plain post kit, as it was")
        check_photo_plain(s)
    finally:
        s.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    n, bad = core.COUNT[0], core.FAILED
    print(f"\n{n - len(bad)} of {n} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


# ====================== part `empty`: a vault with video clips and no photo at all (B-roll from clips alone) ======================

PLAIN_EMPTY = "2026-11-02 Nothing yet"       # a plain post kit whose numbered list reads and holds no photo


def make_empty_world(s, run):
    """No shoot at all: the Assistant's folder, the vault, one video and one song of the vault's own. Beside it a
    plain post kit whose list is empty (written by hand, as a list can be left), which must stay "not ready"."""
    import reel_footage_check as rfc
    s.store.mkdir(parents=True, exist_ok=True)
    s.studio.mkdir(parents=True, exist_ok=True)
    code, out = s.cmd("posts.py", "setup", "--home", str(s.target / "The Assistant"))
    if code != 0:
        raise RuntimeError("posts.py setup: " + out[-300:])
    code, out = s.cmd("vault.py", "ensure")
    if code != 0:
        raise RuntimeError("vault.py ensure: " + out[-300:])
    v = s.vault()
    clips = rfc.make_clips(run / "clips")
    shutil.copyfile(clips["clip.mov"], v / "Footage" / "own.mov")
    shutil.copyfile(BEAT60, v / "Music" / "Test beat.wav")
    k = s.content / PLAIN_EMPTY
    for sub in ("Photos", "Footage", ".kit"):
        (k / sub).mkdir(parents=True)
    shutil.copyfile(clips["clip.mov"], k / "Footage" / "theirs.mov")
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": "Nothing yet", "date": "2026-11-02", "folder": PLAIN_EMPTY, "source": "drop"}), encoding="utf-8")
    (k / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(k / "Photos"), "photos": []}), encoding="utf-8")
    s.note()
    return clips


def check_empty_opens(s):
    R = rp(s)
    v = s.vault()
    case("(set up: the vault's list reads and holds no photo; one video in its Footage folder; no shoot in it)",
         s.sheet().get("photos") == [] and s.sheet().get("vault") is True and (v / "Footage" / "own.mov").is_file(), s.sheet())
    case("has_list(): the vault's empty list is a list; a plain post kit's empty list is not", getattr(R, "has_list", lambda k: None)(v) is True and R.has_list(s.content / PLAIN_EMPTY) is False)
    code, _, raw = s.get("/reel.html?kit=" + VQ)
    page = raw.decode("utf-8", "replace")
    cards = re.findall(r"<a class='kind' id='(\w+)' href='([^']+)'><b>([^<]+)</b>", page)
    case("the chooser opens for a vault with clips and no photo: her title and her four cards, not the \"isn't ready\" page",
         code == 200 and R.NOT_READY not in html_mod.unescape(page) and [c[2] for c in cards] == ["Behind the scenes", "Just photos", "Talking to camera", "B-roll"]
         and "Make my reel" in flat(page), (code, flat(page)[:6]))
    pv = s.get("/reel.html?kit=%s&kind=broll" % VQ)[2].decode("utf-8", "replace")
    case("the B-roll page opens with its own steps (clips, song, watch) and her panel", steps_of(pv) == STEPS["broll"] and "id='vcFind'" in pv and "id='ed'" in pv
         and R.NOT_READY not in html_mod.unescape(pv), steps_of(pv))
    st = s.state()
    case("the page's state answers: ok, no photos, the list's own stamp", bool(st) and st.get("ok") is True and st.get("photos") == [] and bool(st.get("stamp"))
         and st["stamp"] == hashlib.sha1((v / ".kit" / "sheet.json").read_bytes()).hexdigest()[:12], st and {k: st.get(k) for k in ("ok", "words", "stamp")})
    case("no path in the state", no_path(st or {}))
    f = s.foot()
    case("its videos are listed: the vault's own first, then a video of a shoot that has no photos yet either",
         bool(f) and f.get("ok") is True and [x["name"] for x in f.get("videos", [])] == ["own.mov", PLAIN_EMPTY + "/theirs.mov"], f)
    key = f["videos"][0]["key"] if f and f.get("videos") else ""
    got = s.wait(lambda: next((x for x in (s.foot("&want=" + key) or {}).get("videos", []) if x["preview"] == "ready"), None), 90)
    case("...and the video is got ready for the editor", bool(got), s.foot())
    code, j = s.post("/reel-version", {"kit": "My vault", "op": "new", "kind": "broll", "name": "Clips only"})
    case("a new B-roll reel is started (POST /reel-version)", code == 200 and (j or {}).get("ok") and j.get("kind") == "broll", (code, j))
    ids = []
    for start in (0.5, 3.0):
        code, j = s.moment({"do": "add", "video": key, "start": start, "seconds": 2.0})
        ok = code == 200 and (j or {}).get("ok")
        case("a clip made in the editor at %.1f s is added to the reel (POST /reel-moment add)" % start, bool(ok), (code, j))
        ids = [m["id"] for m in (j or {}).get("moments", [])] if ok else ids
    st = s.state()
    sid = next((x["id"] for x in (s.get("/reel-songs?kit=" + VQ)[1] or {}).get("songs", []) if x["name"] == "Test beat"), None)
    code, j = s.post("/reel-save", {"kit": "My vault", "stamp": st["stamp"], "base": st["rev"], "page": "emptyvault1", "saved": {"song": sid, "vault_ask": "Anything with the camera"}})
    case("a save from the page is taken (the song, the ask box)", code == 200 and (j or {}).get("ok") and (s.record().get("saved") or {}).get("song") == sid
         and (s.record().get("saved") or {}).get("vault_ask") == "Anything with the camera", (code, j))
    code, j = s.post("/reel-save", {"kit": "My vault", "stamp": "000000000000", "base": s.state()["rev"], "page": "emptyvault1", "saved": {"vibe": "beat"}})
    case("...and a save against another list's stamp is still refused (photos changed)", code == 409 and (j or {}).get("why") == "photos", (code, j))
    return ids, sid


def check_empty_broll(s, ids, sid):
    R = rp(s)
    v = s.vault()
    st = s.state()
    body = {"kit": "My vault", "stamp": st["stamp"], "picks": [], "song": sid, "vibe": "beat", "footage": True, "style": "broll", "clips": ids}
    code, j = s.post("/reel-preview", body)
    case("the watch step's preview: two clips, no photo, the song, her Plan line", code == 200 and (j or {}).get("ok") and [x["kind"] for x in j["pieces"]] == ["clip", "clip"]
         and [x["id"] for x in j["pieces"]] == ids and j["words"][0].startswith("Plan: 2 clips and 0 photos") and j["song"]["id"] == sid and no_path(j), (code, j))
    code, j = s.post("/reel-make", dict(body, test=True))
    job = wait_job(s, j["job"]["id"]) if code == 200 and (j or {}).get("job") else None
    case("a B-roll test make with no photo in the vault makes its plan: 2 clips and 0 photos", bool(job) and job["state"] == "done" and job["words"][0].startswith("Plan: 2 clips and 0 photos")
         and no_path(job), job or (code, j))
    try:
        listing = json.loads((v / ".kit" / "reels" / "photos.json").read_text())["photos"]
        cl = json.loads((v / ".kit" / "reels" / "clips.json").read_text())["clips"]
    except (OSError, ValueError, KeyError):
        listing, cl = None, []
    case("the reel script was handed an empty photo list and the vault's own video for each clip", listing == [] and [c.get("path") for c in cl] == [str(v / "Footage" / "own.mov")] * 2, (listing, cl))
    code, j = s.post("/reel-video", {"kit": "My vault", "stamp": st["stamp"], "song": sid, "clips": ids, "variation": 0})
    job = wait_job(s, j["job"]["id"], 400) if code == 200 and (j or {}).get("job") else None
    name = "My vault B-roll - Clips only.mp4"
    case("Save my video: the finished MP4 in the vault's own Reels folder, from clips alone", bool(job) and job["state"] == "done" and job.get("video") == name
         and (v / "Reels" / name).is_file() and (v / "Reels" / name).stat().st_size > 1000, job or (code, j))
    made = [m for m in s.record().get("made") or [] if m.get("video")]
    case("the made entry: the file's name, footage broll, the two clips, no picks, no path", bool(made) and made[-1]["video"] == name and made[-1]["footage"] == "broll"
         and made[-1]["clips"] == ids and made[-1]["picks"] == "" and no_path(made[-1]), made[-1:])
    case("the page's state says the reel is made", any((s.state().get("made") or {}).values()), s.state().get("made"))
    code, j = s.post("/words-queue", {"kit": "My vault", "piece": "reel", "reel": s.state().get("current")})
    try:
        pieces = json.loads((s.studio / "posting.json").read_text()).get("pieces", [])
    except (OSError, ValueError):
        pieces = []
    mine = [p for p in pieces if p.get("kind") == "reel" and p.get("shoot_name") == "My vault" and p.get("reel_name") == "Clips only"]
    case("Add to my queue takes it: the vault's reel, ready to post", code == 200 and (j or {}).get("ok") and len(mine) == 1 and mine[0]["status"] == "green", (code, j, mine))
    code, _, raw = s.get("/content/%s/Post%%20kit.html" % VQ)
    case("the vault's own post kit page still opens, with no photo in it", code == 200 and "My vault" in raw.decode("utf-8", "replace"), code)


def check_empty_others(s, ids, sid):
    """The kinds that need photos say so in plain words; nothing breaks."""
    R = rp(s)
    v = s.vault()
    st = s.state()
    base = {"kit": "My vault", "stamp": st["stamp"], "song": sid, "vibe": "beat"}
    before = sha(v / ".kit" / "reel-page.json")
    for what, more in (("just photos", {"picks": [], "footage": False}), ("behind the scenes", {"picks": [], "footage": True, "style": "first", "clips": ids})):
        code, j = s.post("/reel-make", dict(base, test=True, **more))
        case("Make my reel for %s with no photo in the vault: her line, Pick a few photos for the reel first." % what, code == 400 and (j or {}).get("words") == R.WORDS["pick_photos"], (code, j))
        code, j = s.post("/reel-preview", dict(base, **more))
        case("...and the watch step's preview says the same", code == 400 and (j or {}).get("words") == R.WORDS["pick_photos"], (code, j))
    code, j = s.post("/reel-make", dict(base, test=True, picks=[{"n": 1, "h": ""}], footage=False))
    case("a photo number that is not on the (empty) list is refused, as ever", code == 400 and (j or {}).get("ok") is False, (code, j))
    case("nothing was written by any of those", sha(v / ".kit" / "reel-page.json") == before)
    for kind in ("photos", "bts"):
        code, _, raw = s.get("/reel.html?kit=%s&kind=%s" % (VQ, kind))
        case("the %s address still opens a page (the open reel is B-roll, so its own kind wins)" % kind, code == 200 and R.NOT_READY not in html_mod.unescape(raw.decode("utf-8", "replace")), code)
    g = s.get("/reel-vault-photos?kit=" + VQ)[1]
    case("what the photos step searches: nothing yet, and it answers", bool(g) and g.get("ok") is True and g.get("photos") == [] and g.get("shoots") == [], g)
    line = R.VAULT_OUR_WORDS.get("talk_no_photos", "(no such line)")
    case("our line for the talking page: plain, your assistant's words, no dash, no Claude", "no photos yet" in line and "B-roll" in line and "—" not in line and "Claude" not in line
         and not re.search(r"\b(she|he|her|his)\b", line), line)
    code, _, raw = s.get("/talking.html?kit=" + VQ)
    page = html_mod.unescape(raw.decode("utf-8", "replace"))
    case("Talking to camera in a vault with no photo: a plain page with that line, never \"make posts from this shoot\"", code == 200 and line in page and "make posts from this shoot" not in page, flat(raw.decode("utf-8", "replace"))[-3:])
    code, j, _ = s.get("/talking-state?kit=" + VQ)
    case("...and the talking page's state says the same line", code == 404 and (j or {}).get("words") == line, (code, j))


def check_empty_chat(s):
    R = rp(s)
    code, out = s.cmd("reel_page.py", "open", "My vault")
    case("reel_page.py open for a vault with no photo: the address, and that B-roll works from clips alone (no STOP)", code == 0 and "STOP" not in out
         and "/reel.html?kit=My%20vault" in out and "No photos in the vault yet" in out and "B-roll" in out, out[-500:])
    code, out = s.cmd("reel_page.py", "show", "My vault")
    case("reel_page.py show: B-roll, 2 clips selected, the saved video", code == 0 and "B-roll (clips only, no photos), 2 clips selected" in out and "My vault B-roll - Clips only.mp4" in out, out[-600:])
    code, out = s.cmd("reel_page.py", "note", "My vault")
    case("reel_page.py note: the vault, 0 photos", code == 0 and "This is the vault: 0 photos" in out, out[-400:])
    code, out = s.cmd("vault.py", "clips")
    case("vault.py clips: the two clips, under Added to my vault", code == 0 and "2 clips in the vault" in out and "Added to my vault" in out, out[-500:])
    code, out = s.cmd("talking_page.py", "open", "My vault")
    case("talking_page.py open: stops with our plain line", code == 1 and "STOP: " + R.VAULT_OUR_WORDS.get("talk_no_photos", "(no such line)") in out and "couldn't number" not in out, out[-400:])


def check_empty_plain(s):
    """Only the vault changed: a plain post kit whose list is empty is told it isn't ready, on every route."""
    R = rp(s)
    q = quote(PLAIN_EMPTY)
    k = s.content / PLAIN_EMPTY
    for path in ("/reel.html?kit=" + q, "/reel.html?kit=%s&kind=broll" % q):
        code, _, raw = s.get(path)
        case("a plain post kit with an empty list: %s is the \"isn't ready\" page, as before" % path.split("?")[0] + ("" if "kind" not in path else " (B-roll)"),
             code == 200 and R.NOT_READY in html_mod.unescape(raw.decode("utf-8", "replace")) and "id='ed'" not in raw.decode("utf-8", "replace"), code)
    code, j, _ = s.get("/reel-state?kit=" + q)
    case("...its state: 404, not ready", code == 404 and (j or {}).get("words") == R.NOT_READY, (code, j))
    code, j, _ = s.get("/reel-footage?kit=" + q)
    case("...its footage: 404, not ready", code == 404 and (j or {}).get("words") == R.NOT_READY, (code, j))
    stamp = hashlib.sha1((k / ".kit" / "sheet.json").read_bytes()).hexdigest()[:12]
    for path, body in (("/reel-version", {"op": "new", "kind": "broll", "name": "No"}),
                       ("/reel-moment", {"do": "add", "video": "0123456789ab", "start": 0.5, "seconds": 2.0}),
                       ("/reel-save", {"stamp": stamp, "base": 0, "page": "plainempty1", "saved": {"vibe": "beat"}}),
                       ("/reel-make", {"stamp": stamp, "picks": [], "song": None, "vibe": "beat", "test": True, "footage": True, "style": "broll", "clips": []}),
                       ("/reel-preview", {"stamp": stamp, "picks": [], "song": None, "vibe": "beat", "footage": True, "style": "broll", "clips": []})):
        code, j = s.post(path, dict({"kit": PLAIN_EMPTY}, **body))
        case("...POST %s: 404, not ready" % path, code == 404 and (j or {}).get("words") == R.NOT_READY, (code, j))
    case("...and nothing was written into it", not (k / ".kit" / "reel-page.json").exists(), sorted(p.name for p in (k / ".kit").iterdir()))
    code, _, raw = s.get("/talking.html?kit=" + q)
    page = html_mod.unescape(raw.decode("utf-8", "replace"))
    case("its talking page is the plain \"isn't ready\" page too, not the vault's line", "make posts from this shoot" in page and R.VAULT_OUR_WORDS.get("talk_no_photos", "(no such line)") not in page, None)


def check_empty_page(c, s, ids):
    R = rp(s)
    v = s.vault()
    W = dict(R.WATCH_WORDS, **R.ONSCREEN_WORDS)
    c.open(s.url("/reel.html?kit=" + VQ))
    case("the chooser in a browser, for a vault with clips and no photo: Make my reel., her four cards", c.text("#title").strip() == "Make my reel."
         and c.js("Array.prototype.map.call(document.querySelectorAll('.kind b'), function(b){ return b.textContent; })") == ["Behind the scenes", "Just photos", "Talking to camera", "B-roll"], c.text("#title"))
    c.click("#" + c.js("Array.prototype.filter.call(document.querySelectorAll('a.kind'), function(a){ return a.querySelector('b').textContent === 'B-roll'; })[0].id"))
    got = True
    try:
        c.wait_for("window.Reel && Reel.state() && Reel.vaultPanel && Reel.vaultPanel().ready", 30)
    except Exception:  # noqa: BLE001
        got = False
    case("the B-roll card opens the B-roll page, and its script runs (state read, the panel ready)", got, c.js("document.body.innerText.slice(0, 200)"))
    nums = c.js("Array.prototype.map.call(document.querySelectorAll('section.step'), function(s){ return s.hidden ? null : s.id; }).filter(Boolean)")
    f = folds(c)
    case("its steps: clips, song, watch; Added to my vault open on top with the two clips made here, no shoot under it", nums == ["step0", "step3", "watch"]
         and len(f) == 1 and f[0]["mine"] and f[0]["open"] and len(f[0]["tiles"]) == 2, (nums, f))
    names = c.js("Array.prototype.map.call(document.querySelectorAll('#edTabs [data-ek] b'), function(b){ return b.textContent; })")
    case("the editor lists the vault's video first, and the reel's two clips are its cards", names[:1] == ["own.mov"] and c.count("#clist .ci") == 2, (names, c.count("#clist .ci")))
    ok = True
    try:
        c.wait_for("document.getElementById('pvWords').textContent.indexOf('B-roll: ') === 0", 60)
    except Exception:  # noqa: BLE001
        ok = False
    words = c.js("document.getElementById('pvWords').textContent")
    case("the watch step plays it: her line (B-roll: N seconds, 2 clips, each cut on the beat.), Make my reel on", ok and bool(re.match(r"B-roll: \d+\.\d seconds, 2 clips, each cut on the beat\.$", words))
         and not c.js("document.getElementById('makeBtn').disabled") and c.text("#sum").strip().startswith("2 clips · B-roll"), (words, c.text("#sum")))
    before = sorted(p.name for p in (v / "Reels").iterdir())
    c.js("document.getElementById('pvSaveVid').scrollIntoView({block: 'center'})")
    time.sleep(0.8)
    c.click("#pvSaveVid")
    new = s.wait(lambda: [n for n in sorted(p.name for p in (v / "Reels").iterdir()) if n not in before and n.endswith(".mp4") and not n.startswith(".")], 400, 1.0)
    done = True
    try:
        c.wait_for("document.getElementById('pvSaved').textContent.trim() !== %s && !document.getElementById('pvSaveVid').disabled" % json.dumps(W["os_saving"]), 60)
    except Exception:  # noqa: BLE001
        done = False
    case("Save my video pressed on the page: a new MP4 in the vault's Reels folder, and the page says it is saved", bool(new) and done
         and (new or [""])[0] in c.js("document.getElementById('pvSaved').textContent"), (new, c.js("document.getElementById('pvSaved').textContent")))
    case("no path anywhere on the page", no_path(c.js("document.body.innerText")))
    # a kind that needs photos: its page opens, says where photos come from, and waits
    code, j = s.post("/reel-version", {"kit": "My vault", "op": "new", "kind": "photos", "name": "Photos later"})
    case("(set up: a new Just photos reel in the vault)", code == 200 and (j or {}).get("ok"), (code, j))
    c.open(s.url("/reel.html?kit=" + VQ + "&kind=photos"))
    got = True
    try:
        c.wait_for("window.Reel && Reel.state() && !!document.querySelector('#vpAdd')", 30)
    except Exception:  # noqa: BLE001
        got = False
    step1 = c.js("document.getElementById('step1').innerText")
    case("Just photos in a vault with no photo: the page opens and its photos step says her line, with + Add photos",
         got and "Photos you add to your vault show up here, open and ready." in step1 and c.text("#vpAdd").strip() == "+ Add photos", step1[-300:])
    case("...Make my reel is off until there are photos, and no step is broken (song and watch are there)", c.js("document.getElementById('makeBtn').disabled") is True
         and c.js("!document.getElementById('step3').hidden && !document.getElementById('watch').hidden"), None)
    case("...and nothing on it says \"isn't ready\"", "isn't ready" not in c.js("document.body.innerText"))


def check_empty_arrives(s, ids):
    """The first photos arrive: a shoot is made, and the open reel page takes them in by itself."""
    s.fake(s.target, "Late shoot", 8)
    late = s.content / "2026-11-01 Late shoot"
    s.note()
    got = s.wait(lambda: (lambda st: st if st and len(st.get("photos") or []) == 8 else None)(s.state()), 40, 1.0)
    case("a shoot that arrives afterwards shows up on the vault's reel page by itself: 8 photos", bool(got), (s.state() or {}).get("photos"))
    code, out = s.cmd("reel_page.py", "reels", "My vault", "--open", "Clips only")
    st = s.state()
    case("...and the B-roll reel still has its two clips", code == 0 and [m["id"] for m in st.get("moments", [])] == ids and st.get("kind") == "broll", (out[-200:], st.get("kind")))
    case("...the new shoot itself was only read", late.is_dir() and not (late / ".kit" / "reel-page.json").exists())


def main_empty(a):
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-reel-empty-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    run = work / time.strftime("run-%H%M%S")
    (run / "home").mkdir(parents=True)
    s = World(run, a.port)
    try:
        group("(making a vault with one video and no photo at all, and a plain post kit with an empty list)")
        make_empty_world(s, run)
        s.start()
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 20 and s.port not in (8790, 8791, 8792, 8799))
        group("a vault with clips and no photo: the reel page opens")
        ids, sid = check_empty_opens(s)
        group("B-roll from clips alone: the watch step, a test make, Save my video, the queue")
        check_empty_broll(s, ids, sid)
        group("the kinds that need photos say so")
        check_empty_others(s, ids, sid)
        group("the chat")
        check_empty_chat(s)
        s.untouched("all of it")
        group("a plain post kit with an empty list, as it was")
        check_empty_plain(s)
        if a.no_chrome:
            skip("the page in a browser: --no-chrome")
        elif not chrome_drive.find_chrome():
            skip("the page in a browser: no Chrome on this computer")
        else:
            group("the pages in a hidden Chrome")
            with chrome_drive.Chrome(work=str(run), size=(1100, 900), extra_args=LIGHT) as c:
                check_empty_page(c, s, ids)
        group("the first photos arrive")
        check_empty_arrives(s, ids)
    finally:
        s.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    n, bad = core.COUNT[0], core.FAILED
    print(f"\n{n - len(bad)} of {n} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("part", nargs="?", default="clips", choices=("clips", "photos", "empty"))
    ap.add_argument("--port", type=int, default=9985)
    ap.add_argument("--work")
    ap.add_argument("--no-chrome", action="store_true")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        skip("the pretend photos are drawn with the Mac's own sips, and the clips made with its video tools: nothing to run on this computer")
        return 0
    if a.port in (8790, 8791, 8792, 8799):
        print("STOP: that port is the real Assistant's.")
        return 2
    if a.part == "photos":
        return main_photos(a)
    if a.part == "empty":
        return main_empty(a)
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-reel-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    run = work / time.strftime("run-%H%M%S")
    (run / "home").mkdir(parents=True)
    s = World(run, a.port)
    try:
        group("(making two shoots with footage and named clips, a third without, and the vault)")
        clips = make_world(s, run)
        s.start()
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 20 and s.port not in (8790, 8791, 8792, 8799))
        group("her words: the chooser and the kinds")
        check_words(s)
        check_her_words(s)
        group("the videos, across the vault's shoots")
        vids = check_videos(s)
        group("what the panel searches")
        check_catalog(s)
        group("add-from: a shoot's clip into the vault's reel")
        check_add(s, vids)
        group("the chat: Find my clips in my vault")
        check_chat(s)
        group("B-roll in the vault: a test make, Save my video, the queue")
        check_broll(s)
        group("Talking to camera, for the vault")
        check_talking(s, clips)
        if a.no_chrome:
            skip("the page in a browser: --no-chrome")
        elif not chrome_drive.find_chrome():
            skip("the page in a browser: no Chrome on this computer")
        else:
            group("the vault's clips step in a hidden Chrome")
            with chrome_drive.Chrome(work=str(run), size=(1100, 900), extra_args=LIGHT) as c:
                check_page(c, s)
        group("a plain post kit, as it was")
        check_plain(s)
    finally:
        s.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    n, bad = core.COUNT[0], core.FAILED
    print(f"\n{n - len(bad)} of {n} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
