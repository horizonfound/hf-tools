#!/usr/bin/env python3
"""See everything in it (Nicole's v29, 1.6; stage 11): the vault's own page, /vault.html. Tap a clip to play it,
Use it in a reel, Remove from my vault and Put it back.

    python3 tests/guard.py 3000 python3 tests/vault_everything_check.py [--port 9965] [--work <folder under /private/tmp>]
    python3 tests/guard.py 800  python3 tests/vault_everything_check.py --no-chrome     (everything but the page in a browser)

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME; never the real
~/.studio, no drive, no CapCut; STUDIO_NO_WINDOWS_FOR_TESTS, so no folder window is ever shown). The videos are
tiny clips it makes itself with the Mac's own video tools (tests/vault_reel_check.py's world: two shoots with
footage and named clips, a third without, the vault with a video of its own), plus one photo put in the vault's
own Photos folder and one photo with a description.

  * the vault's post kit strip now shows See everything in it →, a link to /vault.html;
  * the page by request: her words, the path at the top back to the vault's post kit, no path anywhere; what it
    draws and searches (GET /vault-data: names, numbers and ids only), never for another website;
  * Remove from my vault (POST /vault-remove): ONLY the vault's own vault.json is written (every other post kit,
    and the vault's own Photos and Footage folders, hashed before and after), the version before kept; twice
    changes nothing; the photo's number is retired and comes back to it; another Origin, a wrong shape, a field
    too many, a photo or clip that is not in the vault: refused, nothing changed;
  * a clip taken out is left out of the vault's lists (the reel page's panel, `vault.py find`) and comes back;
  * a reel that used a removed photo shows it as a gone photo (it drops out of the reel's order, as today);
  * the chat: `vault.py out`, `vault.py out --photo N`, `vault.py back --photo N`, the same writes;
  * in a hidden Chrome: the tabs and counts; "me with my camera" finds the named clips; a tap opens the viewer
    with the label, shoot, date and seconds and a video pointed at the vault's own route, which really plays
    between its start and end; Use it in a reel is a link to the vault's reel page and picks nothing; Remove
    takes the tile away and says the line with Put it back beside it; the fold at the bottom lists it; Put it
    back brings it back under the same number; + Add clips or photos offers the two adds;
  * her words both ways when her handoff is here.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. A Mac
(the pretend photos are drawn with sips, the clips made with AVFoundation); anywhere else it says SKIP and exits 0.
"""
import argparse
import html as html_mod
import json
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
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
import vault_core_check as core  # noqa: E402
import vault_reel_check as vr  # noqa: E402
from vault_core_check import A, B, C, case, group, tree  # noqa: E402
from vault_reel_check import VQ, flat, no_path, sha, skip  # noqa: E402

CAMERA = {"id": "m2-eeeeee", "video": "Footage/SAME.MOV", "start": 0.5, "end": 3.5, "label": "Walking into the frame with my camera", "photo": None, "keep": True}
TAGS = {"beach-002.jpg": ["green", "outdoor"]}
WORDS_1 = "Mom laughing with the kids at the water"

# Lines of her vault-preview.html that are NOT on ours, on purpose, and why.
HERS_NOT_OURS = {
    "←": "her Back pill's arrow; ours is the path at the top",
    "My vault post kit": "her Back pill; ours is the path at the top, whose step says the same words",
    "The Assistant": "the bar's wordmark (brand.py)", "by Horizon Found": "the bar's wordmark (brand.py)",
    "Preview: everything in your vault. Tap a clip to watch it, use it in a reel, or take it out of your vault.": "her preview banner (test-only)",
    "In the real version, this adds your behind-the-scenes clips, or a folder of edited photos from any shoot.": "test-only",
    "×": "the close button's mark (ours is the same mark; its name for a screen reader is her Close)",
}
# How each of her lines stands in her own file (some are built in her script).
HERS_AS_WRITTEN = {
    "title": "What's in <em>my vault.</em>", "tab_clips": "`Clips ${CLIPS.length}`", "tab_photos": "`Photos ${PHOTOS.length}`",
    "search": 'placeholder="Search: me with my camera, laughing, beach, kitchen"', "search_aria": 'aria-label="Search your vault"',
    "every_shoot": "'Every shoot'", "group": "${esc(it.short)} · ${esc(niceDay(it.date))}", "nothing": "Nothing matches that yet.",
    "meta": "` · ${Math.round(it.len)} seconds`", "close": 'aria-label="Close"', "loading": "Loading&hellip;",
    "cant_reach": "I can\\'t reach your shoots right now.",
}


def her_page():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for d in sorted(r.glob("nicole-handoff-v29-*/unpacked/Carousel designer and reel picker/pages")) + sorted(r.glob("nicole-handoff-v29-*/Carousel designer and reel picker/pages")):
            if (d / "vault-preview.html").is_file():
                return d / "vault-preview.html"
    return None


def mods(s):
    vr.rp(s)
    import vault
    import vault_page
    return vault, vault_page


class World(vr.World):
    def vjson(self):
        return json.loads((self.vault() / ".kit" / "vault.json").read_text(encoding="utf-8"))

    def data(self):
        return self.get("/vault-data")[1]

    def remove(self, what, ident, on=False, **kw):
        return self.post("/vault-remove", {"what": what, "id": ident, "on": on}, **kw)

    def vault_tree(self):
        """The vault's own folder, hashed, without what a page's own looks make in the background (small copies,
        stills, the photo-words job's notes, logs of jobs)."""
        skip_ = (".kit/previews/", ".kit/footage/", ".kit/reels/", ".kit/photo-words")
        return {k: v for k, v in tree(self.vault()).items() if not k.startswith(skip_)}


def make_world(s, run):
    vr.make_world(s, run)
    # one more named clip in the first shoot, a described photo there, and a photo added to the vault itself
    rec = s.content / A / ".kit" / "reel-page.json"
    d = json.loads(rec.read_text(encoding="utf-8"))
    d["moments"].append(CAMERA)
    rec.write_text(json.dumps(d), encoding="utf-8")
    table = s.work / "pretend-tags.json"
    table.write_text(json.dumps(TAGS), encoding="utf-8")
    tagging = dict(s.env, PHOTO_WORDS_PRETEND=str(table))
    code, out = s.cmd("photo_words.py", "tag", A, env=tagging)
    if code != 0:
        raise RuntimeError("photo_words.py tag: " + out[-300:])
    f = s.work / "words.json"
    f.write_text(json.dumps({"photos": {"1": {"words": WORDS_1}}}), encoding="utf-8")
    code, out = s.cmd("photo_words.py", "describe", A, "--file", str(f), env=tagging)
    if code != 0:
        raise RuntimeError("photo_words.py describe: " + out[-300:])
    v = s.vault()
    shutil.copyfile(s.content / A / "Photos" / "beach-003.jpg", v / "Photos" / "added-one.jpg")
    old = time.time() - 60
    import os
    os.utime(v / "Photos" / "added-one.jpg", (old, old))            # settled: not "still being copied in"
    code, out = s.cmd("vault.py", "relist")
    if code != 0:
        raise RuntimeError("vault.py relist: " + out[-300:])
    s.note()


# ---------- the page and its data, by request ----------

def check_page_by_request(s):
    vault, vp = mods(s)
    case("vault.EVERYTHING is on", vault.EVERYTHING is True)
    code, _, raw = s.get("/content/%s/Post%%20kit.html" % VQ)
    kit_page = raw.decode("utf-8", "replace")
    case("the vault's post kit strip shows See everything in it →, a link to /vault.html",
         code == 200 and "<a class='go' id='vaultEverything' href='/vault.html'>See everything in it &rarr;</a>" in kit_page, code)
    code, _, raw = s.get("/vault.html")
    page = raw.decode("utf-8", "replace")
    lines = flat(page[page.index("<body"):])
    case("the page: her title and lede", code == 200 and "<h1>What's in <em>my vault.</em></h1>" in page
         and "Your clips and photos from every shoot. Add more, or look up a clip you remember." in lines, lines[:12])
    case("her tabs, + Add clips or photos, the search box with her placeholder and its name for a screen reader",
         all(x in lines for x in ("Clips", "Photos", "+ Add clips or photos"))
         and "placeholder='Search: me with my camera, laughing, beach, kitchen' aria-label='Search your vault'" in page, lines)
    case("her viewer: Use it in a reel (a link to the vault's reel page), Remove from my vault, close ×",
         "<a class='btn solid' href='/reel.html?kit=My%20vault' id='vuse'>Use it in a reel</a>" in page
         and "<button class='btn' type='button' id='vrm'>Remove from my vault</button>" in page and "id='vx' aria-label='Close'>&times;</button>" in page)
    crumbs = re.search(r"<nav class='crumbs'.*?</nav>", page, re.S)
    case("the way back is the path at the top: Home › My vault post kit › Everything in it", crumbs is not None
         and flat(crumbs.group(0)) == ["Home", "›", "My vault post kit", "›", "Everything in it"]
         and "href='/content/My%20vault/Post%20kit.html'" in crumbs.group(0), crumbs.group(0) if crumbs else None)
    case("no path on the page, no web font, no Claude, no em dash, no serif", no_path(page) and "fonts.googleapis" not in page
         and "Claude" not in page and "—" not in page and "serif'" not in page.replace("sans-serif", "") and "Fraunces" not in page)
    case("none of her test-only lines or dead code: no Preview banner, no In the real version, no tray, no Used badge, no Photo {id}",
         not any(x in page for x in ("Preview:", "In the real version", "tray", "class=\"used\"", ">Used<", "Photo ${", "testnote")))
    bad = [k for k, v in list(vp.EVERY_WORDS.items()) + list(vp.EVERY_OUR_WORDS.items()) + list(vault.OUT_WORDS.items())
           if "—" in v or "Claude" in v or re.search(r"\b(she|he|her|his)\b", v)]
    case("no em dash, no Claude, no she or he in any of the page's words", not bad, bad)

    code, j, raw = s.get("/vault-data")
    case("GET /vault-data: ok, with no path in it", code == 200 and j and j["ok"] and no_path(raw.decode()) and j["vault"] == "My vault", code)
    shoots = [(x["kit"], x["name"], x["date"]) for x in j["shoots"]]
    case("the shoots: what was added to the vault first, then each shoot by its name with its date as she writes it",
         shoots[0] == ("", "Added to my vault", "") and sorted(shoots[1:]) == sorted([(A, "Fake beach", "Nov 1, 2026"), (B, "Other farm", "Nov 1, 2026"), (C, "Third hill", "Nov 1, 2026")]), shoots)
    case("the clips: all five, each by \"<shoot's folder>:<id>\" with its label, start, end and length",
         sorted((c["id"], c["label"], c["len"]) for c in j["clips"]) == sorted([
             (A + ":m1-aaaaaa", "Laughing on the way back from the water", 3.0), (A + ":u1-bbbbbb", "Not named yet", 2.0),
             (A + ":m2-eeeeee", "Walking into the frame with my camera", 3.0), (B + ":m1-cccccc", "Walking in with the camera", 3.0),
             (B + ":m2-dddddd", "In the kitchen, pouring coffee", 3.0)]), [(c["id"], c["label"], c["len"]) for c in j["clips"]])
    case("the photos: all 26 by their vault numbers, the described one carrying its words", len(j["photos"]) == 26
         and sorted(p["n"] for p in j["photos"]) == sorted(x["n"] for x in s.rows())
         and [p["words"] for p in j["photos"] if p["words"]] == [WORDS_1], len(j["photos"]))
    pw = vault.search_words("me with my camera")
    hit = sorted(c["label"] for c in j["clips"] if vault.found(pw, c["text"]))
    case("her search rule on it: \"me with my camera\" finds the two clips named for the camera", pw == ["camera"]
         and hit == ["Walking in with the camera", "Walking into the frame with my camera"], hit)
    case("...and \"laughing\" finds the described photo by its words", [p["words"] for p in j["photos"] if vault.found(["laughing"], p["text"])] == [WORDS_1])
    case("nothing is taken out to begin with", j["out"] == [] and s.vjson().get("out") in ({}, {"photos": {}, "clips": {}}), s.vjson().get("out"))
    code, j2, _ = s.get("/vault-data", headers={"Sec-Fetch-Site": "cross-site"})
    case("another website is never told what is in the vault", code == 403 and not (j2 or {}).get("clips"), (code, j2))
    code, j3, _ = s.get("/vault-clip?id=" + quote(A + ":m1-aaaaaa"))
    case("GET /vault-clip: the video's key as the vault lists it, never a path", code == 200 and j3["ok"] and re.fullmatch(r"[0-9a-f]{12}", j3["key"] or "") and no_path(j3), j3)
    code, j4, _ = s.get("/vault-clip?id=" + quote(A + ":m9-ffffff"))
    case("...a clip that is not there: no", code == 200 and j4 == {"ok": False}, j4)
    s.untouched("the page and its data by request")
    return j


# ---------- Remove from my vault, Put it back ----------

def check_remove(s, data):
    vault, vp = mods(s)
    v = s.vault()
    n = s.n_of(A, "beach-002.jpg")
    key = "%s#%d" % (A, next(x["src"] for x in s.rows() if x["n"] == n))
    file_before = sha(s.content / A / "Photos" / "beach-002.jpg")
    was, was_json = s.vault_tree(), (v / ".kit" / "vault.json").read_bytes()
    photos_before, footage_before = tree(v / "Photos"), tree(v / "Footage")

    # refused, nothing changed
    for name, body, want in (
            ("a field too many", {"what": "photo", "id": n, "on": False, "path": "/x"}, 400), ("a field missing", {"what": "photo", "id": n}, 400),
            ("what is not a photo or a clip", {"what": "song", "id": n, "on": False}, 400), ("on is not true or false", {"what": "photo", "id": n, "on": "false"}, 400),
            ("a photo's id that is not a number", {"what": "photo", "id": str(n), "on": False}, 400), ("a clip's id that is not text", {"what": "clip", "id": 3, "on": False}, 400),
            ("a list in place of the body", [1], 400)):
        code, j = s.post("/vault-remove", body)
        case("refused whole: " + name, code == want and j and j["ok"] is False and (v / ".kit" / "vault.json").read_bytes() == was_json, (code, j))
    code, j = s.remove("photo", n, origin="http://evil.example")
    case("another Origin is refused and changes nothing", code == 403 and (v / ".kit" / "vault.json").read_bytes() == was_json and s.vault_tree() == was, (code, j))
    code, j = s.remove("photo", n, more={"Sec-Fetch-Site": "cross-site"})
    case("a cross-site press is refused and changes nothing", code == 403 and (v / ".kit" / "vault.json").read_bytes() == was_json, (code, j))
    code, j = s.remove("photo", 999)
    case("a photo that is not in the vault: plain words, nothing changed", code == 200 and j["ok"] is False and j["words"] == vault.OUT_WORDS["no_photo"]
         and (v / ".kit" / "vault.json").read_bytes() == was_json, (code, j))
    for bad in (A + ":m9-ffffff", "Nobody:m1-aaaaaa", "m1-aaaaaa", A + ":../x"):
        code, j = s.remove("clip", bad)
        case("a clip that is not in the vault (%s): plain words, nothing changed" % bad[-12:], code == 200 and j["ok"] is False and j["words"] == vault.OUT_WORDS["no_clip"]
             and (v / ".kit" / "vault.json").read_bytes() == was_json, (code, j))

    # the remove itself
    code, j = s.remove("photo", n)
    now = s.vault_tree()
    diff = sorted(k for k in set(now) | set(was) if now.get(k) != was.get(k))
    case("Remove from my vault: ok, with our line", code == 200 and j["ok"] and j["changed"] and j["words"] == "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted.", (code, j and j.get("words")))
    case("...it wrote ONLY the vault's vault.json (and kept the version before beside it)", diff == [".kit/vault.json", ".kit/vault.prev.json"]
         and (v / ".kit" / "vault.prev.json").read_bytes() == was_json, diff)
    case("...one entry on the out list, under the key its number is kept by; the number is still its own", list(s.vjson()["out"]["photos"]) == [key] and s.vjson()["numbers"][key] == n
         and s.vjson()["out"].get("clips", {}) == {}, s.vjson()["out"])
    case("...the vault's own Photos and Footage folders are byte for byte what they were", tree(v / "Photos") == photos_before and tree(v / "Footage") == footage_before)
    case("...the photo itself is where it was, unchanged", sha(s.content / A / "Photos" / "beach-002.jpg") == file_before)
    s.untouched("Remove from my vault")
    case("...the answer's fresh list has 25 photos, none with that number, and the photo in what was taken out", len(j["data"]["photos"]) == 25 and n not in [p["n"] for p in j["data"]["photos"]]
         and [(o["what"], o["id"], o["shoot"]) for o in j["data"]["out"]] == [("photo", n, "Fake beach")] and no_path(j["data"]), j["data"]["out"])
    again = (v / ".kit" / "vault.json").read_bytes()
    code, j = s.remove("photo", n)
    case("twice changes nothing", code == 200 and j["ok"] and j["changed"] is False and (v / ".kit" / "vault.json").read_bytes() == again, (code, j and j.get("words")))

    # the list follows on the next look: the number is retired, never given to another photo
    d = s.data()
    sheet = s.sheet()
    case("on the next look the list leaves it off and keeps its number retired (unused)", n not in [x["n"] for x in sheet["photos"]]
         and [x["n"] for x in sheet.get("retired") or []] == [n] and len(d["photos"]) == 25, sheet.get("retired"))
    code, _, _ = s.get("/kit-photo?kit=%s&n=%d&size=s" % (VQ, n))
    case("...and the vault's photo route no longer serves it", code == 404, code)
    code, out = s.cmd("vault.py", "out")
    case("`vault.py out` lists it, with how to put it back", code == 0 and "Taken out of the vault: 1." in out and ("photo %d | Fake beach" % n) in out and ("vault.py back --photo %d" % n) in out, out)
    s.untouched("the next look")
    return n, key


def check_reel_and_back(s, n, key):
    """A reel that used a removed photo shows it as a gone photo; Put it back brings it back with the same number."""
    vault, vp = mods(s)
    v = s.vault()
    # put it back first (so a reel can use it), by the page's route
    code, j = s.remove("photo", n, on=True)
    case("Put it back: ok, our line, and the photo is on the list again with the SAME number", code == 200 and j["ok"] and j["changed"] and j["words"] == "Back in your vault."
         and n in [p["n"] for p in j["data"]["photos"]] and len(j["data"]["photos"]) == 26 and j["data"]["out"] == [], (code, j and j.get("words")))
    row = next((x for x in s.rows() if x["n"] == n), None)
    case("...the vault's list has it back under that number, pointing at the same photo of the same shoot", row is not None and row["kit"] == A
         and Path(row["file"]).name == "beach-002.jpg" and s.sheet().get("retired") in ([], None) and s.vjson()["out"]["photos"] == {}, row)
    code, j = s.remove("photo", n, on=True)
    case("putting back what is already in: nothing changes", code == 200 and j["ok"] and j["changed"] is False, (code, j and j.get("words")))
    # a reel of the vault that uses it
    other = s.n_of(B, "beach-003.jpg")
    code, j = s.post("/reel-version", {"kit": "My vault", "op": "new", "kind": "photos", "name": "Tidy"})
    case("(set up: a Just photos reel in the vault)", code == 200 and (j or {}).get("ok"), (code, j))
    code, out = s.cmd("kit.py", "picks", "My vault", "--reel", "%d,%d" % (n, other), "--for-reel", "Tidy")
    st = s.state()
    case("(set up: that reel's pick uses the photo)", code == 0 and [x["n"] for x in st.get("claude") or []] == [n, other], (out, st.get("claude")))
    code, j = s.remove("photo", n)
    case("(the photo is taken out again)", code == 200 and j["ok"] and j["changed"], (code, j))
    time.sleep(4.3)                                 # the reel page compares its list at most every 4 seconds
    s.data()
    st = s.wait(lambda: (lambda t: t if t and n not in [p["n"] for p in t.get("photos") or []] else None)(s.state()), 20)
    case("the reel that used it shows it as a gone photo: it is off the reel's photos and out of its order, the other photo stays",
         bool(st) and [x["n"] for x in st.get("claude") or []] == [other], st and st.get("claude"))
    code, out = s.cmd("vault.py", "back", "--photo", str(n))
    case("`vault.py back --photo N` puts it back (the same write)", code == 0 and "Back in your vault." in out and s.vjson()["out"]["photos"] == {}, out)
    code, out = s.cmd("vault.py", "relist")
    row = next((x for x in s.rows() if x["n"] == n), None)
    case("...and after the next list it has the number it had", code == 0 and row is not None and Path(row["file"]).name == "beach-002.jpg" and row["kit"] == A, out)
    code, out = s.cmd("vault.py", "out", "--photo", str(n))
    js = (v / ".kit" / "vault.json").read_bytes()
    code2, out2 = s.cmd("vault.py", "out", "--photo", str(n))
    case("`vault.py out --photo N` takes it out with the same line; twice changes nothing", code == 0 and "Taken out of your vault." in out and list(s.vjson()["out"]["photos"]) == [key]
         and code2 == 0 and "already" in out2 and (v / ".kit" / "vault.json").read_bytes() == js, (out, out2))
    code, out = s.cmd("vault.py", "out", "--photo", "999")
    case("`vault.py out --photo 999`: STOP, not in the vault", code == 2 and "STOP" in out and "isn't in your vault" in out, out)
    s.cmd("vault.py", "back", "--photo", str(n))
    s.cmd("vault.py", "relist")
    # a photo added to the vault itself
    own = next(x["n"] for x in s.rows() if x["kit"] == "")
    own_sha = sha(v / "Photos" / "added-one.jpg")
    code, j = s.remove("photo", own)
    case("a photo added to the vault itself: taken out with its own line, and the file is still in the vault's Photos folder, unchanged",
         code == 200 and j["ok"] and j["words"] == vault.OUT_WORDS["own_photo_out"] and sha(v / "Photos" / "added-one.jpg") == own_sha
         and list(s.vjson()["out"]["photos"]) == ["own:added-one.jpg"], (code, j and j.get("words")))
    code, j = s.remove("photo", own, on=True)
    case("...and it comes back under the same number", code == 200 and j["ok"] and own in [p["n"] for p in j["data"]["photos"]] and next(x for x in s.rows() if x["n"] == own)["kit"] == "", (code, j and j.get("words")))
    s.untouched("the reel, the commands and the vault's own photo")


def check_clip_out(s):
    vault, vp = mods(s)
    v = s.vault()
    ident = B + ":m2-dddddd"
    was = s.vault_tree()
    code, j = s.remove("clip", ident)
    now = s.vault_tree()
    diff = sorted(k for k in set(now) | set(was) if now.get(k) != was.get(k))
    case("a clip: Remove writes only vault.json, one entry, with our line", code == 200 and j["ok"] and j["words"] == "Taken out of your vault. The clip itself is still in its shoot, and nothing was deleted."
         and diff == [".kit/vault.json", ".kit/vault.prev.json"] and list(s.vjson()["out"]["clips"]) == [ident], (code, diff))
    case("...the page's list has four clips and names it under what was taken out, by its label and shoot", len(j["data"]["clips"]) == 4
         and [(o["what"], o["id"], o["label"], o["shoot"]) for o in j["data"]["out"]] == [("clip", ident, "In the kitchen, pouring coffee", "Other farm")], j["data"]["out"])
    panel = s.get("/reel-vault-clips?kit=" + VQ)[1]
    case("...it is left out of the vault's lists: the reel page's clips panel, and the shoot's count", ident.split(":")[1] not in [c["id"] for c in panel["clips"] if c["kit"] == B]
         and next(x for x in panel["shoots"] if x["kit"] == B)["clips"] == 1, panel["shoots"])
    code, out = s.cmd("vault.py", "find", "kitchen", "--clips")
    case("...and `vault.py find \"kitchen\" --clips` no longer finds it", code == 0 and ": 0." in out, out)
    code, out = s.cmd("vault.py", "out")
    case("`vault.py out` lists the clip with how to put it back", code == 0 and ("clip %s | Other farm | In the kitchen, pouring coffee" % ident) in out and "vault.py back --clip" in out, out)
    code, out = s.cmd("vault.py", "back", "--clip", ident)
    panel = s.get("/reel-vault-clips?kit=" + VQ)[1]
    case("`vault.py back --clip` puts it back in the lists", code == 0 and "Back in your vault." in out and "m2-dddddd" in [c["id"] for c in panel["clips"] if c["kit"] == B] and s.vjson()["out"]["clips"] == {}, out)
    code, out = s.cmd("vault.py", "back")
    case("`vault.py back` with nothing named: STOP", code == 2 and "STOP" in out, out)
    s.untouched("a clip taken out and put back")


# ---------- her words ----------

def check_her_words(s):
    vault, vp = mods(s)
    f = her_page()
    if f is None:
        skip("her words both ways: her v29 handoff isn't on this computer")
        return
    hers_raw = f.read_text(encoding="utf-8")
    hers = flat(hers_raw[hers_raw.index("<body"):])
    ours = set(html_mod.unescape(re.sub(r"<[^>]+>", "", v)) for v in vp.EVERY_WORDS.values())
    miss = [x for x in hers if x not in ours and x not in HERS_NOT_OURS]
    case("every line her page shows is one of ours, whole (her test-only lines named)", not miss, miss)
    not_hers = [k for k, v in vp.EVERY_WORDS.items() if HERS_AS_WRITTEN.get(k, v) not in hers_raw]
    case("every word in EVERY_WORDS is in her page as she wrote it", not not_hers, not_hers)
    case("our words table holds none of hers we were told not to copy", not any(x in json.dumps(list(vp.EVERY_OUR_WORDS.values()) + list(vp.EVERY_WORDS.values()))
                                                                                 for x in ("In the real version", "Photo {id}", "Preview:", "Used")))


# ---------- the page in a hidden Chrome ----------

def tiles(c):
    return c.js("""Array.prototype.map.call(document.querySelectorAll('#grid .t'), function(b){
      return {id: b.dataset.id || '', n: b.dataset.n ? Number(b.dataset.n) : null, label: (b.querySelector('b') || {}).textContent || '',
              shoot: (b.querySelector('small') || {}).textContent || '', len: (b.querySelector('.len') || {}).textContent || ''}; })""")


def press_tile(c, sel):
    c.js("document.querySelector(%s).scrollIntoView({block: 'center'})" % json.dumps(sel))
    c.click(sel)


def ready(c):
    c.wait_for("window.VaultPage && VaultPage.data() && document.querySelectorAll('#chips .chip').length > 0", 30)


def check_page(c, s):
    vault, vp = mods(s)
    v = s.vault()
    reel_before = sha(v / ".kit" / "reel-page.json")
    c.open(s.url("/content/%s/Post%%20kit.html" % VQ))
    c.wait_for("!!document.getElementById('vaultEverything')", 20)
    c.click("#vaultEverything")
    c.wait_for("location.pathname === '/vault.html'", 10)
    ready(c)
    case("See everything in it → on the vault's post kit opens the page; its title is hers", c.text("h1").strip() == "What's in my vault.", c.text("h1"))
    case("the tabs and their counts: Clips 5 (on), Photos 26", c.text("#tClips").strip() == "Clips 5" and c.text("#tPhotos").strip() == "Photos 26"
         and c.js("document.getElementById('tClips').classList.contains('on') && !document.getElementById('tPhotos').classList.contains('on')"), (c.text("#tClips"), c.text("#tPhotos")))
    chips = c.js("Array.prototype.map.call(document.querySelectorAll('#chips .chip'), function(b){ return b.textContent; })")
    case("the chips: Every shoot (on), then each shoot's name", chips[0] == "Every shoot" and sorted(chips[1:]) == ["Added to my vault", "Fake beach", "Other farm", "Third hill"]
         and c.js("document.querySelector('#chips .chip.on').textContent") == "Every shoot", chips)
    heads = c.js("Array.prototype.map.call(document.querySelectorAll('#grid h3.month'), function(h){ return h.textContent; })")
    t = tiles(c)
    case("the clips are grouped by shoot under \"{shoot} · {date}\"", sorted(heads) == ["Fake beach · Nov 1, 2026", "Other farm · Nov 1, 2026"] and len(t) == 5, heads)
    case("a clip's tile: its label, its shoot, its length as ▶ 0:03", {"id": A + ":m1-aaaaaa", "n": None, "label": "Laughing on the way back from the water", "shoot": "Fake beach", "len": "0:03"} in t
         and c.js("getComputedStyle(document.querySelector('#grid .t .len'), '::before').content").replace("\\25B6", "▶").find("▶") > -1, t)
    got = c.wait_for("Array.prototype.every.call(document.querySelectorAll('#grid .t img'), function(i){ return i.naturalWidth > 0; })", 90)
    case("every clip's still really loads (the vault's own stills)", bool(got))
    vr.type_in(c, "#q", "me with my camera")
    time.sleep(0.2)
    t = tiles(c)
    case("\"me with my camera\" finds the named clips, and only those", sorted(x["label"] for x in t) == ["Walking in with the camera", "Walking into the frame with my camera"], t)
    vr.type_in(c, "#q", "zebra")
    time.sleep(0.2)
    case("nothing found: her line", c.text("#grid").strip() == "Nothing matches that yet.", c.text("#grid"))
    vr.type_in(c, "#q", "")
    c.click("#chips .chip", nth=chips.index("Other farm"))
    time.sleep(0.2)
    t = tiles(c)
    case("a shoot's chip shows only that shoot's clips", len(t) == 2 and {x["shoot"] for x in t} == {"Other farm"}, t)
    c.click("#chips .chip", nth=0)
    time.sleep(0.2)

    # tap a clip: it plays right there
    sel = "#grid .t[data-id=%s]" % json.dumps(A + ":m1-aaaaaa")
    press_tile(c, sel)
    c.wait_for("!document.getElementById('view').hidden", 5)
    case("a tap opens the viewer with the clip's label as the heading", c.text("#vlabel").strip() == "Laughing on the way back from the water", c.text("#vlabel"))
    case("...and what it is: the shoot, the date and how long it is", c.text("#vmeta").strip() == "Fake beach · Nov 1, 2026 · 3 seconds", c.text("#vmeta"))
    got = c.wait_for("!!document.querySelector('#vmedia video')", 90)
    src = c.js("(document.querySelector('#vmedia video') || {}).getAttribute ? document.querySelector('#vmedia video').getAttribute('src') : ''") if got else ""
    case("a video element pointed at the vault's own route, by the video's key", bool(re.fullmatch(r"/reel-video\?kit=My%20vault&key=[0-9a-f]{12}#t=1,4", src or "")), src)
    played = c.wait_for("(function(){ var v = document.querySelector('#vmedia video'); return v && v.readyState >= 2 && v.currentTime >= 0.9 && v.currentTime <= 4.2 && v.videoWidth > 0; })()", 60)
    case("...which really plays, between the clip's start and end", bool(played), c.js("(function(){ var v = document.querySelector('#vmedia video'); return v ? [v.readyState, v.currentTime, v.error && v.error.code] : null; })()"))
    c.js("(function(){ var v = document.querySelector('#vmedia video'); v.currentTime = 3.95; })()")
    looped = c.wait_for("(function(){ var v = document.querySelector('#vmedia video'); return v.currentTime >= 0.9 && v.currentTime < 3.0; })()", 20)
    case("...and loops: past its end it goes back to its start", bool(looped), c.js("document.querySelector('#vmedia video').currentTime"))
    case("Use it in a reel is a link to the vault's reel page; Remove from my vault beside it; Put it back not yet",
         c.js("document.getElementById('vuse').getAttribute('href')") == "/reel.html?kit=My%20vault" and not c.js("document.getElementById('vuse').hidden")
         and c.text("#vrm").strip() == "Remove from my vault" and c.js("document.getElementById('vsay').hidden"))
    case("nothing was picked: the vault's reel record is byte for byte what it was", sha(v / ".kit" / "reel-page.json") == reel_before)

    # Remove from my vault, right there
    c.click("#vrm")
    c.wait_for("!document.getElementById('vsay').hidden && !document.getElementById('vback').hidden", 10)
    case("Remove: our line right there, with Put it back beside it", c.text("#vmsg").strip() == "Taken out of your vault. The clip itself is still in its shoot, and nothing was deleted."
         and c.text("#vback").strip() == "Put it back" and c.js("document.getElementById('vrm').hidden"), c.text("#vmsg"))
    case("...the tile goes, and the tab counts four clips", not c.count(sel) and c.text("#tClips").strip() == "Clips 4" and list(s.vjson()["out"]["clips"]) == [A + ":m1-aaaaaa"], c.text("#tClips"))
    case("...the fold at the bottom says Taken out of my vault (1)", not c.js("document.getElementById('outs').hidden") and c.text("#outSum").strip() == "Taken out of my vault (1)", c.text("#outSum"))
    c.click("#vback")
    c.wait_for("!document.getElementById('vrm').hidden", 10)
    case("Put it back, right there: the tile is back, five clips, the fold gone", c.count(sel) == 1 and c.text("#tClips").strip() == "Clips 5" and c.text("#vmsg").strip() == "Back in your vault."
         and c.js("document.getElementById('outs').hidden") and s.vjson()["out"]["clips"] == {}, c.text("#tClips"))
    c.key("Escape")
    case("Escape closes the viewer and the video is let go", c.js("document.getElementById('view').hidden") and not c.count("#vmedia video"))

    # the photos
    c.click("#tPhotos")
    c.wait_for("document.querySelectorAll('#grid .t.ph').length === 26", 10)
    heads = c.js("Array.prototype.map.call(document.querySelectorAll('#grid h3.month'), function(h){ return h.textContent; })")
    case("Photos: 26 tiles, grouped by shoot, what was added to the vault first", heads[0] == "Added to my vault" and sorted(heads[1:]) == ["Fake beach · Nov 1, 2026", "Other farm · Nov 1, 2026", "Third hill · Nov 1, 2026"], heads)
    got = c.wait_for("Array.prototype.filter.call(document.querySelectorAll('#grid .t.ph img'), function(i){ return i.naturalWidth > 0; }).length >= 20", 120)
    case("the photos' small pictures load from the vault's own photo route", bool(got) and c.js("document.querySelector('#grid .t.ph img').getAttribute('src')").startswith("/kit-photo?kit=My%20vault&n="))
    vr.type_in(c, "#q", "laughing")
    time.sleep(0.2)
    t = tiles(c)
    n1 = s.n_of(A, "beach-001.jpg")
    case("the search finds a photo by its description", [x["n"] for x in t] == [n1], t)
    psel = "#grid .t.ph[data-n='%d']" % n1
    press_tile(c, psel)
    c.wait_for("!document.getElementById('view').hidden", 5)
    case("a photo opens big, headed by its shoot's name with its own description (never \"Photo 12\"); no Use it in a reel",
         c.text("#vlabel").strip() == "Fake beach" and c.text("#vdesc").strip() == WORDS_1 and c.text("#vmeta").strip() == "Nov 1, 2026"
         and c.js("document.getElementById('vuse').hidden") and (c.js("document.querySelector('#vmedia img').getAttribute('src')") or "").startswith("/kit-photo?kit=My%%20vault&n=%d&size=" % n1), (c.text("#vlabel"), c.text("#vdesc")))
    members_before = {d.name: tree(d) for d in s.members()}
    c.click("#vrm")
    c.wait_for("!document.getElementById('vsay').hidden && !document.getElementById('vback').hidden", 10)
    case("Remove a photo: our line, the tile goes, Photos 25", c.text("#vmsg").strip() == "Taken out of your vault. The photo itself is still in its shoot, and nothing was deleted."
         and not c.count(psel) and c.text("#tPhotos").strip() == "Photos 25", (c.text("#vmsg"), c.text("#tPhotos")))
    case("...and no shoot's post kit was touched by it", {d.name: tree(d) for d in s.members()} == members_before)
    c.click("#vx")
    vr.type_in(c, "#q", "")
    c.js("document.getElementById('outs').open = true; document.getElementById('outs').scrollIntoView({block: 'center'})")
    row = c.js("(function(){ var r = document.querySelector('#outRows .row'); return r ? [r.dataset.what, Number(r.dataset.id), r.querySelector('span').childNodes[0].textContent, r.querySelector('small').textContent, r.querySelector('button').textContent] : null; })()")
    case("the fold lists what was removed: the photo by its description and shoot, with Put it back", c.text("#outSum").strip() == "Taken out of my vault (1)"
         and row == ["photo", n1, WORDS_1, "Fake beach", "Put it back"], row)
    c.click("#outRows .row button")
    c.wait_for("document.getElementById('outs').hidden", 10)
    c.wait_for("document.querySelectorAll('#grid .t.ph').length === 26", 10)
    case("Put it back in the fold brings the photo back with the same number", c.count("#grid .t.ph[data-n='%d']" % n1) == 1 and c.text("#tPhotos").strip() == "Photos 26"
         and next(x for x in s.rows() if x["n"] == n1)["kit"] == A and s.vjson()["out"]["photos"] == {}, c.text("#tPhotos"))

    # + Add clips or photos: the two adds of the vault's post kit
    c.js("window.scrollTo(0, 0)")
    case("the two adds are folded away until asked for", c.js("document.getElementById('addRow').hidden"))
    c.click("#add")
    case("+ Add clips or photos offers a folder of finished photos and videos", not c.js("document.getElementById('addRow').hidden")
         and c.text("#addPhotos").strip() == "Add a folder of finished photos" and c.text("#addVideos").strip() == "Add videos")
    c.click("#addVideos")
    c.wait_for("document.getElementById('addWent').textContent.length > 0", 10)
    case("Add videos opens the vault's Footage folder and says where they show up (the line is stage 7's)", c.text("#addWent").strip().startswith(vp.OUR_WORDS["clips_opened"]), c.text("#addWent"))
    body = c.js("document.body.innerText")
    case("no path anywhere on the page", no_path(body) and no_path(c.js("document.documentElement.outerHTML.replace(/<script[^]*?<\\/script>/g, '')")))
    errs = [e for e in c.page_errors() if "favicon" not in str(e)]
    case("the page raised no error of its own", not errs, errs[:3])
    outside = c.outside_requests()
    case("nothing was asked of the internet", not outside, outside[:3])
    # a phone's width
    c.phone()
    c.reload()
    ready(c)
    case("at a phone's width nothing scrolls sideways", c.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), c.js("[document.documentElement.scrollWidth, window.innerWidth]"))
    c.desktop()
    s.untouched("the page in a browser")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=9965)
    ap.add_argument("--work")
    ap.add_argument("--no-chrome", action="store_true")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        skip("the pretend photos are drawn with the Mac's own sips, and the clips made with its video tools: nothing to run on this computer")
        return 0
    if a.port in (8790, 8791, 8792, 8799):
        print("STOP: that port is the real Assistant's.")
        return 2
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-everything-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    run = work / time.strftime("run-%H%M%S")
    (run / "home").mkdir(parents=True)
    s = World(run, a.port)
    try:
        group("(making two shoots with footage and named clips, a third without, a described photo, and the vault with a photo of its own)")
        make_world(s, run)
        s.start()
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 20 and s.port not in (8790, 8791, 8792, 8799))
        group("the page and what it draws, by request")
        data = check_page_by_request(s)
        check_her_words(s)
        group("Remove from my vault: only the vault's own vault.json")
        n, key = check_remove(s, data)
        group("a reel that used it, Put it back, the commands")
        check_reel_and_back(s, n, key)
        group("a clip taken out and put back")
        check_clip_out(s)
        if a.no_chrome:
            skip("the page in a browser: --no-chrome")
        elif not chrome_drive.find_chrome():
            skip("the page in a browser: no Chrome on this computer")
        else:
            group("See everything in it, in a hidden Chrome")
            with chrome_drive.Chrome(work=str(run), size=(1100, 900), extra_args=vr.LIGHT) as c:
                check_page(c, s)
    finally:
        s.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    n_, bad = core.COUNT[0], core.FAILED
    print(f"\n{n_ - len(bad)} of {n_} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
