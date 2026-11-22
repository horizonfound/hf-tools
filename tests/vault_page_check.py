#!/usr/bin/env python3
"""My vault on the post kits list, and the vault's own post kit page (Nicole's v29, 1.3): stage 7, vault-page.

    python3 tests/guard.py 3000 python3 tests/vault_page_check.py [--port 9975] [--no-chrome] [--work <folder under /private/tmp>]

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME; never the real
~/.studio, no drive, no CapCut; STUDIO_NO_WINDOWS_FOR_TESTS, so no folder window and no folder picker is ever shown:
the folder the test "chose" comes from STUDIO_PICK_FOLDER_FOR_TESTS).

  * the post kits list: her title, no "Step 3 of your workflow", "What's a post kit?" stays; My vault is the first
    card, alone on its row, with no Archive, and it stays when the search hides every shoot; loading the list
    makes nothing;
  * Open the post kit is a guarded POST: another Origin is refused and makes nothing; the press makes the vault
    once and lands on its page; a second press makes no second vault;
  * the vault's page: her words, the path back to My post kits, the strip's chips and counts, See everything in
    it (drawn by vault.EVERYTHING, on since stage 11), the three cards open the reel page, the designer and the stories
    designer for the vault; no path on either page;
  * her words both ways on both pages when her handoff is on this computer (her test-only lines on HERS_NOT_OURS);
  * `vault.py add` on a pretend folder: copies hash-identical, originals hashed before and after and unchanged,
    heavy files named and left, a second add copies nothing and writes nothing, a clash gets its own name with the
    first file byte for byte as it was, a run cut off is finished (by the same add, and by another one), a post
    kit's own photos are refused, every other post kit is byte for byte unchanged;
  * the page's + Add a shoot (the route starts the same command as a job the page follows) and + Add clips; both
    refuse another Origin.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. A Mac
(the pretend photos are drawn with the Mac's own sips); anywhere else it says SKIP and exits 0.
"""
import argparse
import hashlib
import html as html_mod
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
import vault_core_check as core  # noqa: E402
from vault_core_check import A, B, case, group, tree  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/nicole_nov22.py
import nicole_nov22  # noqa: E402  Nicole, Nov 22: everything is the Assistant

C = "2026-11-01 Third hill"

# Lines of her two preview pages that are NOT on ours, on purpose, and why.
HERS_NOT_OURS = {
    # make-posts-preview.html
    "Preview: your vault is a post kit too, always first in your list.": "her preview banner (test-only)",
    # vault-kit-preview.html
    "Preview: your vault as a post kit. It works like every other post kit, it just draws from all your shoots. Reels opens a preview of its reel page; the other cards don’t open anything yet.": "her preview banner (test-only)",
    "Loading…": "her page draws its cards in the browser; ours comes whole from the Assistant (the list page still says Loading…)",
    "In the real version, this opens the reel page for your vault.": "test-only: ours opens it",
    "In the real version, this opens the carousel designer with every shoot's photos.": "test-only: ours opens it",
    "In the real version, this opens the stories designer with every shoot's photos.": "test-only: ours opens it",
    "In the real version, you pick a shoot (or a folder of edited photos) to add to your vault.": "test-only: ours does it",
    "In the real version, you add your behind-the-scenes clips here.": "test-only: ours opens the folder",
}
# Her lines that her pages build in their scripts (so they are not in her markup): typed here from her pages, each
# checked to be in her file as she wrote it, and to be on ours.
HERS_IN_SCRIPT = {
    "make": ["My vault", "All your shoots in one post kit · ", " photos", "Open the post kit", "Archive", "Bring it back"],
    "vault": ["Make it", "Reels", "Create my reels", "The same reel maker as every post kit: the Assistant picks, orders and cuts on the beat of your song, and it opens in CapCut. The only difference is it picks from every shoot in your vault.",
              "Tell the Assistant what this reel is",
              "\"My favorite maternity photos this year\" · \"Behind the scenes at the beach\" · \"Moms laughing, from any shoot\"",
              "Not made yet", "Carousel", "Design my carousel",
              "The same carousel designer, with photos from any shoot: a year of favorites, or three families in one post.",
              "Stories", "Make my stories",
              "Stories from any shoot: a throwback, a this-or-that, or behind the scenes from a few sessions.",
              "Add to my queue", " photos · ", " clips"],
}


def skip(line):
    print("SKIP  " + line, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def her_pages():
    for r in (ROOT / "reference-private", ROOT.parent / "hf-tools" / "reference-private"):
        for d in sorted(r.glob("nicole-handoff-v29-*/unpacked/Carousel designer and reel picker/pages")) + sorted(r.glob("nicole-handoff-v29-*/Carousel designer and reel picker/pages")):
            if (d / "make-posts-preview.html").is_file() and (d / "vault-kit-preview.html").is_file():
                return d
    return None


def flat(markup):
    return [re.sub(r"\s+", " ", t).strip() for t in html_mod.unescape(re.sub(r"<[^>]+>", "¦", re.sub(r"</?(em|b)>", "", markup))).split("¦") if t.strip()]


class World(core.Run):
    def __init__(self, work, port):
        super().__init__(work, port)
        self.picked = self.work / "picked" / "Wedding exports"
        self.env["STUDIO_PICK_FOLDER_FOR_TESTS"] = str(self.picked)

    # every other post kit, hashed: all of it but the small copies a kit's OWN page makes of its own photos
    # (.kit/previews: this test opens each shoot's page, and that page starts them in the background)
    def _kits(self):
        return {d.name: {k: v for k, v in tree(d).items() if not k.startswith(".kit/previews")} for d in self.members()}

    def note(self):
        self.before = self._kits()

    def untouched(self, what):
        now = self._kits()
        inner = []
        for k in sorted(set(now) | set(self.before)):
            a, b = self.before.get(k) or {}, now.get(k) or {}
            inner += [k + ": " + f for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)][:6]
        case("every other post kit is byte for byte unchanged after " + what + " (its photos, records and folders; its own page's small copies aside)", not inner, inner)

    def post(self, path, body=None, origin=None, ctype="application/json"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Host": "127.0.0.1:%d" % self.port, "Content-Type": ctype,
             "Origin": origin or ("http://127.0.0.1:%d" % self.port)}
        c.request("POST", path, body=json.dumps({} if body is None else body).encode(), headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw.decode())
        except ValueError:
            return r.status, None

    def page(self, path):
        code, _, raw = self.http("GET", path)
        return code, raw.decode("utf-8", "replace")

    def vaults(self):
        out = []
        for d in sorted(self.content.iterdir()):
            try:
                if json.loads((d / ".kit" / "kit.json").read_text()).get("vault") is True:
                    out.append(d)
            except (OSError, ValueError):
                pass
        return out

    def vault_page(self):
        return "/content/" + quote(self.vault().name, safe="") + "/Post%20kit.html"

    def no_path(self, text):
        """Nothing that looks like a place on this computer: the run's own folder, a home folder, a drive."""
        bad = [w for w in (str(self.work), "/private/tmp", "/Users/", "/Volumes/", str(self.studio)) if w in text]
        return bad

    def folder(self, name, photos, extra=()):
        """A pretend export folder OUTSIDE the Assistant's folder: photos is {relative name: a source photo to copy
        (or bytes)}, extra the names of heavy files to put beside them."""
        d = self.work / "picked" / name
        for rel, src in photos.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(src, bytes):
                p.write_bytes(src)
            else:
                shutil.copyfile(src, p)
        for rel in extra:
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"not a finished photo: " + rel.encode() + b"\0" * 2000)
        return d

    def add(self, folder, env=None):
        e = dict(self.env)
        e.update(env or {})
        return self.cmd("vault.py", "add", str(folder), env=e)

    def adds(self):
        return json.loads((self.vault() / ".kit" / "vault-adds.json").read_text())["adds"]

    def own(self):
        return tree(self.vault() / "Photos")


def pic(s, tag):
    """A pretend finished photo of the test's own: one of the pretend kit's JPEGs with a few bytes after its end,
    so every tag is a different file that still opens as a picture."""
    base = sorted((s.content / A / "Photos").glob("beach-00*.jpg"))[0]
    return base.read_bytes() + b"|" + str(tag).encode()


# ---------- before the vault exists ----------

def check_list_page(s):
    group("the post kits list, before there is a vault")
    listing = sorted(os.listdir(s.content))
    code, page = s.page("/make-posts")
    body = page.split("<script", 1)[0]
    case("the screen's title is hers: Turn your shoots into posts.", code == 200 and "<h1>Turn your shoots <em>into posts.</em></h1>" in body, body[:300])
    case("the Step 3 of your workflow eyebrow is gone, from the page and from the words", "of your workflow" not in page and "Make posts <em>from a shoot" not in page)
    case("the What's a post kit? box stays", "What's a post kit?" in html_mod.unescape(body) and "It's one place for everything you'll post from a shoot." in html_mod.unescape(body))
    case("the vault's row sits between the search box and the shoots", re.search(r"id='find'.*id='vaultRow'.*id='recent'", body, re.S) is not None)
    code, j, _ = s.http("GET", "/home-data")
    v = (j or {}).get("vault") or {}
    case("the list's data carries the vault's card: every post kit's photos counted (8 + 9 + 10), not made yet, three shoots' pictures by folder name",
         code == 200 and v.get("photos") == 27 and v.get("made") is False and sorted(v.get("thumbs") or []) == sorted([A, B, C]), v)
    case("the vault is not one of the shoots on the list", sorted(k["folder"] for k in j["kits"]) == sorted([A, B, C]))
    case("loading the list and its data made nothing: no vault, the same folders", s.vault() is None and sorted(os.listdir(s.content)) == listing)
    case("no path on the list page or in its data", not s.no_path(page) and not s.no_path(json.dumps(j)), s.no_path(page) + s.no_path(json.dumps(j)))


def check_open_guard(s):
    group("Open the post kit is a guarded press")
    listing = sorted(os.listdir(s.content))
    code, j = s.post("/vault-open", origin="http://evil.example")
    case("a press from another Origin is refused (403)", code == 403 and not (j or {}).get("ok"), (code, j))
    code, j = s.post("/vault-open", body={"kit": "x"})
    case("a body that is not {} is refused", code == 400 and not (j or {}).get("ok"), (code, j))
    code, j = s.post("/vault-open", ctype="text/plain")
    case("a press that is not JSON is refused", code == 415, (code, j))
    code, _, _ = s.http("GET", "/vault-open")
    case("it is never a GET (a page load can't make the vault)", code == 404, code)
    for path in ("/vault-add", "/vault-clips"):
        code, j = s.post(path, origin="http://evil.example")
        case(f"{path} from another Origin is refused (403)", code == 403 and not (j or {}).get("ok"), (code, j))
    code, j = s.post("/vault-add")
    case("+ Add a shoot before there is a vault copies nothing and says so in plain words", code == 200 and j.get("ok") is False and "vault" in j.get("words", ""), j)
    case("none of that made a vault or a folder", s.vault() is None and sorted(os.listdir(s.content)) == listing)


def open_by_request(s):
    code, j = s.post("/vault-open")
    case("the press makes the vault and answers its page's address (a path of this server, never a folder)",
         code == 200 and j.get("ok") and j.get("made") is True and j.get("url") == s.vault_page(), j)


def check_made_once(s):
    group("the vault is made once")
    case("there is one vault, a real folder in Your Content with its mark", len(s.vaults()) == 1 and s.vault().name == "My vault")
    code, j = s.post("/vault-open")
    case("a second press makes no second vault and answers the same page", code == 200 and j.get("ok") and j.get("made") is False and j.get("url") == s.vault_page() and len(s.vaults()) == 1, j)
    case("its list holds every post kit's photos (27), and none was copied", len(s.rows()) == 27 and not list((s.vault() / "Photos").iterdir()))
    code, j, _ = s.http("GET", "/home-data")
    case("the card now counts the vault's own list (27), made", j["vault"]["photos"] == 27 and j["vault"]["made"] is True, j["vault"])
    case("the vault is still not one of the shoots on the list", sorted(k["folder"] for k in j["kits"]) == sorted([A, B, C]))


# ---------- the vault's page ----------

def check_vault_page(s):
    group("the vault's own post kit page")
    sys.path.insert(0, str(SCRIPTS))
    import vault_page
    code, page = s.page(s.vault_page())
    body = page.split("<body", 1)[1]
    markup = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    W = vault_page.WORDS
    case("eyebrow Post kit, title My vault., her lede", code == 200 and "<span class='eyebrow'>Post kit</span><h1>My vault<em>.</em></h1>" in markup
         and "<p class='lede'>" + html_mod.escape(W["lede"]) + "</p>" in markup, markup[:600])
    case("the path at the top leads back to the post kits: Home › My post kits › My vault",
         "<a href='/home'>Home</a>" in markup and "<a href='/make-posts#kits'>My post kits</a>" in markup and "<span class='here' aria-current='page'>My vault</span>" in markup)
    names = re.findall(r"<span><img src='/kit-thumb\?kit=([^'&]+)&amp;i=1'[^>]*>([^<]+)</span>", markup)
    case("the strip: one chip per shoot, its small picture by folder name and its name, newest first",
         [(unquote(a), b) for a, b in names] == sorted([(A, "Fake beach"), (B, "Other farm"), (C, "Third hill")], reverse=True), names)
    case("the strip's count: 27 photos · 0 clips", "<span class='ct' id='invCount'>27 photos · 0 clips</span>" in markup, re.findall(r"id='invCount'>[^<]*", markup))
    case("+ Add a shoot and + Add clips are buttons, with the line for what a press did right there in the strip",
         re.search(r"<button class='go' type='button' id='vaultAdd'>\+ Add a shoot</button><button class='go' type='button' id='vaultClips'>\+ Add clips</button>(<a class='go' id='vaultEverything' href='/vault.html'>See everything in it &rarr;</a>)?</span><p class='went' id='invWent' role='status'></p></div>", markup) is not None)
    case("See everything in it → is drawn after the two buttons, a link to its page (stage 11 switched it on)",
         "<a class='go' id='vaultEverything' href='/vault.html'>See everything in it &rarr;</a></span>" in markup)
    case("her three card lines", all(html_mod.escape(W[k]) in markup for k in ("reel_sub", "carousel_sub", "stories_sub")))
    case("the shoot page's own card lines are not on the vault's", "Create as many reels as you like from this shoot" not in markup and "Lay out your slides in the carousel designer" not in markup)
    case("her box on the Reels card: Tell the Assistant what this reel is, with her three examples",
         "<span class='ask'><span class='k'>Tell the Assistant what this reel is</span><span class='p'>" + html_mod.escape(W["ask_p"]) + "</span></span>" in markup)
    kq = quote(s.vault().name)
    hrefs = dict(re.findall(r"<a class='piece' data-piece='(\w+)' href='([^']+)'", markup))
    case("the three cards lead to the reel page, the designer and the stories designer, for the vault",
         html_mod.unescape(hrefs.get("reel", "")).startswith("/reel.html?kit=" + kq) and html_mod.unescape(hrefs.get("carousel", "")).startswith("/design.html?kit=" + kq)
         and "kind=stories" in hrefs.get("stories", "") and kq in hrefs.get("stories", ""), hrefs)
    case("everything else is the kit page's own: Make it, Create my reels, Design my carousel, Make my stories, Not made yet, Add to my queue",
         all(t in markup for t in ("Make it", "Create my reels", "Design my carousel", "Make my stories", "Not made yet", "Add to my queue")))
    case("no path on the vault's page", not s.no_path(page), s.no_path(page))
    for kit in (A, B, C):
        code, raw = s.page("/content/" + quote(kit, safe="") + "/Post%20kit.html")
        ok = code == 200 and "id='inv'" not in raw and "Tell the Assistant what this reel is" not in raw and "Create as many reels as you like from this shoot" in raw and "Open the kit folder" in raw
        if not ok:
            break
    case("a shoot's own post kit page is as it was: no strip, no box, its own lines and folder buttons", ok, kit)
    # clips: a video in a shoot's Footage folder and one in the vault's own
    (s.content / A / "Footage").mkdir(exist_ok=True)
    (s.content / A / "Footage" / "walk.mov").write_bytes(b"\0" * 64)
    (s.vault() / "Footage" / "mine.mp4").write_bytes(b"\0" * 64)
    (s.vault() / "Footage" / ".hidden.mp4").write_bytes(b"\0" * 64)
    (s.vault() / "Footage" / "notes.txt").write_bytes(b"x")
    code, page2 = s.page(s.vault_page())
    # (review fix, Nov 19: the strip counts the clips See everything in it lists, a stretch made on a reel page,
    # never video files, so the two pages one click apart agree)
    case("a video file is not a clip: the count stays 27 photos · 0 clips, as See everything in it lists", "id='invCount'>27 photos · 0 clips</span>" in page2, re.findall(r"id='invCount'>[^<]*", page2))
    (s.content / A / "Footage" / "walk.mov").unlink()       # the test's own pretend video, made a moment ago
    shutil.rmtree(s.content / A / "Footage")                # ... and its folder, so the kit is as fake_kit made it
    case("one of a thing is singular", vault_page.count_words(1, 1) == "1 photo · 1 clip" and vault_page.count_words(295, 21) == "295 photos · 21 clips"
         and vault_page.count_words(1234, 1) == "1,234 photos · 1 clip")
    # See everything in it: drawn by the one switch, which is on since stage 11
    os.environ.update(s.env)
    import kit as kit_mod
    import vault
    was = vault.EVERYTHING
    try:
        vault.EVERYTHING = False
        off = kit_mod.build_page(s.vault())[0]
    finally:
        vault.EVERYTHING = was
    case("See everything in it → follows vault.EVERYTHING, which is on today", was is True and "vaultEverything" not in off and "See everything in it" not in off)


def check_her_words(s):
    group("her words, both ways")
    d = her_pages()
    if not d:
        skip("her words compared with her own two pages, both ways: her v29 handoff is not on this computer")
        return
    sys.path.insert(0, str(SCRIPTS))
    import home_base
    import kit as kit_mod
    import vault_page
    pages = {"make": (d / "make-posts-preview.html", s.page("/make-posts")[1], list(home_base.WORDS.values())),
             "vault": (d / "vault-kit-preview.html", s.page(s.vault_page())[1], list(vault_page.WORDS.values()) + list(kit_mod.KIT_WORDS.values()) + ["My post kits", "See everything in it →"])}
    seen_left = set()
    for key, (f, ours_page, ours_words) in pages.items():
        raw = nicole_nov22.read(f)   # Nicole, Nov 22: everything is the Assistant
        plain = html_mod.unescape(raw).replace("\\'", "'")
        body = raw.split("<body", 1)[1].split("<script", 1)[0]
        theirs = flat(body) + [t for t in HERS_IN_SCRIPT[key]] + [t for t in HERS_NOT_OURS if t.startswith("In the real version") and key == "vault"]
        ours = "¦" + "¦".join(flat(re.sub(r"<script.*?</script>", "", ours_page.split("<body", 1)[1], flags=re.S)) + flat("¦".join(ours_words))) + "¦"
        ours_text = html_mod.unescape(re.sub(r"<[^>]+>", "", ours_page)) + "¦".join(ours_words)
        gone = []
        for t in theirs:
            if t in HERS_NOT_OURS:
                seen_left.add(t)
            elif t == "Archived" and "Archived ({n})" in ours_words:
                continue                                    # her markup's word before her script writes "Archived (2)"; ours is that line
            elif re.fullmatch(r"[\d\W]+", t) or ("¦" + t + "¦") in ours or (t in HERS_IN_SCRIPT[key] and t in ours_text):
                continue
            else:
                gone.append(t)
        case(f"{f.name}: every line her page shows is on ours, whole, but for the ones left out on purpose ({len(theirs)} lines of hers)", not gone, gone[:6])
        missing = [t for t in HERS_IN_SCRIPT[key] if t not in plain]
        case(f"{f.name}: the lines typed here from her page's script are in her file as she wrote them", not missing, missing)
        if key == "vault":
            lost = [k for k, v in vault_page.WORDS.items() if k != "count" and re.sub(r"</?em>", "", v) not in plain and v not in raw]
            case("every line of vault_page.WORDS is on her vault page, word for word (%d lines)" % len(vault_page.WORDS), not lost, lost)
            case("... and her count line is ours: {photos} photos · {clips} clips", "} photos · ${clips.length} clips`" in raw and vault_page.WORDS["count"] == "{photos} photos · {clips} clips")
        else:
            mine = {k: home_base.WORDS[k] for k in ("m_h1", "m_lede", "m_steps", "m_s1", "m_pick", "m_s1_small", "m_s2", "m_say", "m_s2_small", "m_s3", "m_s3_small",
                                                    "m_h2", "m_say_list", "m_find", "open_kit", "v_name", "archive", "bring_back")}
            lost = [k for k, v in mine.items() if v not in raw and v not in plain]
            case("every line of the post kits list on ours is on her page, word for word (%d lines)" % len(mine), not lost, lost)
            case("... and her vault card's line is ours: All your shoots in one post kit · {n} photos",
                 "All your shoots in one post kit · ${" in raw and home_base.WORDS["v_small"] == "All your shoots in one post kit · {n} photos")
        on_ours = [t for t in HERS_NOT_OURS if t != "Loading…" and (t in ours_page or t.replace("’", "'") in html_mod.unescape(ours_page))]
        case(f"{f.name}: none of her test-only lines is on ours (no Preview banner, no In the real version, no animation samples)",
             not on_ours and "Trying ideas" not in ours_page and "animation samples" not in ours_page and "testnote" not in ours_page, on_ours)
    case("... and the lines left out are exactly the named ones, each really in her pages", seen_left == set(HERS_NOT_OURS), sorted(set(HERS_NOT_OURS) ^ seen_left))


# ---------- + Add a shoot: the copy ----------

def check_add(s):
    group("vault.py add: a folder's finished photos, copied and checked")
    s.note()
    src = s.folder("Final Exports", {"smith-01.jpg": pic(s, "s1"), "smith-02.jpg": pic(s, "s2"), "smith-03.jpg": pic(s, "s3"),
                                     "more/smith-04.jpg": pic(s, "s4"), "more/smith-05.JPG": pic(s, "s5"), "more/pic.png": pic(s, "png")},
                   extra=("layers.psd", "flat.tif", "more/IMG_0001.CR3", "more/clip.mp4", "notes.txt"))
    before = tree(src)
    code, out = s.add(src)
    case("it says, in the page's own words: Copied 6 finished photos into your vault. Your originals weren't moved. 5 files left where they are: not finished photos.",
         code == 0 and "Copied 6 finished photos into your vault. Your originals weren't moved. 5 files left where they are: not finished photos." in out, (code, out[-500:]))
    case("... and names what was left by kind", all(t in out for t in ("1 Photoshop file", "1 TIFF", "1 RAW file", "1 video", "1 other file")), out[-400:])
    own = s.own()
    want = {Path(k).name: v for k, v in before.items() if v != "dir" and Path(k).suffix.lower() in (".jpg", ".png")}
    case("six copies in the vault's own Photos folder, each hash-identical to its original, and nothing else there", own == want, sorted(set(own) ^ set(want)))
    case("the originals are byte for byte what they were (every file of the folder hashed before and after)", tree(src) == before)
    case("no heavy file came along, and no unfinished copy is left", not [n for n in os.listdir(s.vault() / "Photos") if not n.lower().endswith((".jpg", ".png"))])
    run = s.adds()[-1]
    case("the log has the run: done, each file's name in its folder, size, time and hash, and the name it got",
         run["status"] == "done" and len(run["files"]) == 6 and all(f["done"] and f["sha256"] == before[f["src"]] and f["size"] > 0 and f["mtime"] > 0 and f["dst"] == Path(f["src"]).name for f in run["files"]), run)
    case("the new photos are on the vault's list as its own, with new numbers, and every older number is where it was",
         len(s.rows()) == 33 and sorted(x["n"] for x in s.rows() if x["kit"] == "") == list(range(28, 34)) and sorted(x["n"] for x in s.rows() if x["kit"]) == list(range(1, 28)),
         [(x["n"], x["kit"]) for x in s.rows()][-8:])
    s.untouched("vault.py add")

    group("a second add of the same folder copies nothing")
    log_before = (s.vault() / ".kit" / "vault-adds.json").read_bytes()
    sheet_before = (s.vault() / ".kit" / "sheet.json").read_bytes()
    code, out = s.add(src)
    case("it says so: Those photos are already in your vault. Nothing was copied.", code == 0 and "Those photos are already in your vault. Nothing was copied." in out, (code, out[-300:]))
    case("the Photos folder, the log and the list are byte for byte what they were", s.own() == own and (s.vault() / ".kit" / "vault-adds.json").read_bytes() == log_before
         and (s.vault() / ".kit" / "sheet.json").read_bytes() == sheet_before)
    case("the originals are still untouched", tree(src) == before)

    group("a name that is already there")
    clash = s.folder("Other exports", {"smith-01.jpg": pic(s, "another picture"), "smith-02.jpg": pic(s, "s2"), "new-one.jpg": pic(s, "new")})
    cb = tree(clash)
    first = sha(s.vault() / "Photos" / "smith-01.jpg")
    code, out = s.add(clash)
    now = s.own()
    case("different bytes under a name already there: the copy gets a number after its name, smith-01 (2).jpg", now.get("smith-01 (2).jpg") == cb["smith-01.jpg"], sorted(now))
    case("... and the first file is byte for byte what it was (nothing is ever written over)", sha(s.vault() / "Photos" / "smith-01.jpg") == first == now["smith-01.jpg"])
    case("the same bytes under the same name are already there: no second copy", "smith-02 (2).jpg" not in now and now["smith-02.jpg"] == cb["smith-02.jpg"])
    case("it says what it did: Copied 2 finished photos... 1 was already in your vault.", code == 0 and "Copied 2 finished photos into your vault. Your originals weren't moved. 1 was already in your vault." in out, out[-300:])
    case("the original was not renamed or changed", tree(clash) == cb)
    code, out = s.add(clash)
    case("that folder again: nothing copied, no smith-01 (3).jpg", code == 0 and "Nothing was copied" in out and s.own() == now, (out[-200:], sorted(s.own())))

    group("a copy cut off part way is finished")
    cut = s.folder("Cut off", {"cut-%02d.jpg" % i: pic(s, "cut%d" % i) for i in range(5)})
    ct = tree(cut)
    code, out = s.add(cut, env={"STUDIO_VAULT_ADD_STOP_FOR_TESTS": "2"})
    got = {k: v for k, v in s.own().items() if k.startswith("cut-")}
    run = s.adds()[-1]
    case("the run is cut after two copies (as if the power went): two are in, each identical; the log still says copying, with the whole plan",
         code == 9 and len(got) == 2 and all(ct[k] == v for k, v in got.items()) and run["status"] == "copying" and len(run["files"]) == 5
         and sum(1 for f in run["files"] if f["done"]) == 2 and all(f["sha256"] == ct[f["src"]] and f["dst"] for f in run["files"]), (code, sorted(got), run["status"]))
    code, out = s.add(cut)
    got = {k: v for k, v in s.own().items() if k.startswith("cut-")}
    run = [r for r in s.adds() if r["from"].endswith("Cut off")]
    case("the same add again finishes it: all five in, each identical, nothing copied twice, one run in the log, done",
         code == 0 and got == ct and len(run) == 1 and run[0]["status"] == "done" and "Copied 3 finished photos into your vault. Your originals weren't moved. 2 were already in your vault." in out,
         (code, out[-300:], sorted(got)))
    cut2 = s.folder("Cut again", {"again-%02d.jpg" % i: pic(s, "again%d" % i) for i in range(4)})
    c2 = tree(cut2)
    code, _ = s.add(cut2, env={"STUDIO_VAULT_ADD_STOP_FOR_TESTS": "1"})
    other = s.folder("Later", {"later-01.jpg": pic(s, "later")})
    code2, out = s.add(other)
    got = {k: v for k, v in s.own().items() if k.startswith("again-")}
    run = [r for r in s.adds() if r["from"].endswith("Cut again")]
    case("a run cut off is finished by the NEXT add, whatever folder that is", code == 9 and code2 == 0 and got == c2 and len(run) == 1 and run[0]["status"] == "done"
         and "later-01.jpg" in s.own(), (code, code2, sorted(got), [r["status"] for r in run]))
    case("the originals of both are untouched", tree(cut) == ct and tree(cut2) == c2)
    case("no unfinished copy is left in the vault's Photos folder", not [n for n in os.listdir(s.vault() / "Photos") if "partial" in n])

    group("what is never copied")
    now = s.own()
    for what, folder in (("a post kit's own Photos folder", s.content / A / "Photos"), ("a post kit's folder", s.content / B)):
        code, out = s.add(folder)
        case(f"{what}: That shoot is already in your vault, from its post kit.", code == 4 and "That shoot is already in your vault, from its post kit." in out and s.own() == now, (code, out[-200:]))
    code, out = s.add(s.vault() / "Photos")
    case("the vault's own Photos folder: nothing copied", code == 4 and s.own() == now, (code, out[-200:]))
    code, out = s.add(s.content)
    case("Your Content itself: nothing copied", code == 4 and s.own() == now, (code, out[-200:]))
    code, out = s.add(s.work / "picked" / "no such folder")
    case("a folder that isn't there: nothing copied, plain words", code == 4 and "can't see that folder" in out and s.own() == now, (code, out[-200:]))
    empty = s.folder("Only raws", {}, extra=("a.CR3", "b.psd"))
    code, out = s.add(empty)
    case("a folder with no finished photos: No finished photos (JPEGs) in that folder. Nothing was copied. 2 files left where they are: not finished photos.",
         code == 0 and "No finished photos (JPEGs) in that folder. Nothing was copied. 2 files left where they are: not finished photos." in out and s.own() == now, (code, out[-300:]))
    case("no line the command prints for a result names a place on this computer", not s.no_path(out), out[-300:])
    s.untouched("every add")
    case("exactly one vault all along", len(s.vaults()) == 1)


def wait_job(s, seconds=40):
    end = time.time() + seconds
    j = {}
    while time.time() < end:
        _, j, _ = s.http("GET", "/vault-add-status")
        if (j or {}).get("state") != "working":
            return j
        time.sleep(0.2)
    return j


def check_routes(s):
    group("+ Add a shoot and + Add clips, by request")
    picked = s.folder("Wedding exports", {"wed-01.jpg": pic(s, "w1"), "wed-02.jpg": pic(s, "w2")}, extra=("wed.psd",))
    pt = tree(picked)
    code, j = s.post("/vault-add")
    case("the press starts the copy as a job the page follows", code == 200 and j.get("ok") and j.get("state") == "working", j)
    j = wait_job(s)
    case("the job ends with the line for beside the button: Copied 2 finished photos into your vault. Your originals weren't moved. 1 file left where it is: not finished photos.",
         j.get("state") == "done" and j.get("words") == "Copied 2 finished photos into your vault. Your originals weren't moved. 1 file left where it is: not finished photos.", j)
    own = s.own()
    case("the two photos are in, identical, and the originals untouched", own.get("wed-01.jpg") == pt["wed-01.jpg"] and own.get("wed-02.jpg") == pt["wed-02.jpg"] and tree(picked) == pt)
    case("the status the page follows carries no path", not s.no_path(json.dumps(j)), j)
    code, j = s.post("/vault-add")
    j2 = wait_job(s)
    case("the same folder picked again: nothing copied, and it says so", j2.get("state") == "done" and "already in your vault" in j2.get("words", "") and s.own() == own, j2)
    code, j = s.post("/vault-clips")
    case("+ Add clips answers with the line for right beside it: Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them.",
         code == 200 and j.get("ok") and j.get("words") == "Put your videos in the folder that just opened. They show up in your vault's reel page, where you make clips from them.", j)
    case("... and copied no video and made nothing new in the vault's Photos folder", s.own() == own)
    for path in ("/vault-add", "/vault-clips", "/vault-open"):
        code, j = s.post(path, origin="http://evil.example")
        if code != 403:
            break
    case("all three presses still refuse another Origin", code == 403, (path, code))
    code, j, _ = s.http("GET", "/vault-add")
    case("+ Add a shoot is never a GET", code == 404, code)


# ---------- in a browser ----------

def check_browser_list(c, s):
    group("the post kits list in a browser")
    base = "http://127.0.0.1:%d" % s.port
    c.open(base + "/make-posts")
    c.wait_for("document.getElementById('vaultCard') && document.querySelectorAll('#recent .shoot').length === 3", 15)
    q = c.js("""(() => { const kits = document.getElementById('kits'), cards = [...kits.querySelectorAll('.shoot')], v = document.getElementById('vaultCard');
      const r = v.getBoundingClientRect(), others = cards.filter(x => x !== v).map(x => x.getBoundingClientRect());
      return {first: cards[0] === v, inRow: document.getElementById('vaultRow').children.length, name: v.querySelector('b').textContent, small: v.querySelector('small').textContent,
        buttons: [...v.querySelectorAll('button, a')].map(b => b.textContent.trim()), alone: others.every(o => o.top >= r.bottom - 1),
        bg: getComputedStyle(v).backgroundColor, ink: getComputedStyle(document.documentElement).getPropertyValue('--ink').trim(),
        h1: document.querySelector('h1').innerText, shoots: cards.length - 1, archive: [...document.querySelectorAll('#recent [data-arch]')].length,
        sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}; })()""")
    case("My vault is the first card, alone on its own row above the shoots", q["first"] and q["inRow"] == 1 and q["alone"] and q["shoots"] == 3, q)
    case("it reads My vault / All your shoots in one post kit · 27 photos, with one button, Open the post kit, and no Archive",
         q["name"] == "My vault" and q["small"] == "All your shoots in one post kit · 27 photos" and q["buttons"] == ["Open the post kit"] and q["archive"] == 3, q)
    case("it is the dark card", q["bg"] not in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)") and sum(int(x) for x in re.findall(r"\d+", q["bg"])[:3]) < 200, q["bg"])
    case("the title on the screen: Turn your shoots into posts.", q["h1"].replace("\n", " ") == "Turn your shoots into posts.", q["h1"])
    c.js("(() => { const f = document.getElementById('find'); f.value = 'zzz no such shoot'; f.dispatchEvent(new Event('input')); })()")
    q = c.js("({v: !!document.getElementById('vaultCard'), shown: document.getElementById('vaultCard').getBoundingClientRect().height > 50, shoots: document.querySelectorAll('#recent .shoot').length, empty: document.querySelector('#recent .empty').textContent})")
    case("a search that hides every shoot leaves My vault where it is", q["v"] and q["shown"] and q["shoots"] == 0 and "No post kit called" in q["empty"], q)
    c.js("(() => { const f = document.getElementById('find'); f.value = 'vault'; f.dispatchEvent(new Event('input')); })()")
    case("... and searching for the word vault finds no shoot (the vault is not one), with the card still there",
         c.js("document.querySelectorAll('#recent .shoot').length === 0 && !!document.getElementById('vaultCard')"))
    c.js("(() => { const f = document.getElementById('find'); f.value = ''; f.dispatchEvent(new Event('input')); })()")
    case("still no vault on the disk: looking at the list made nothing", s.vault() is None)
    c.click("#vaultOpen")
    c.wait_for("location.pathname.indexOf('Post%20kit.html') > 0 && document.readyState === 'complete' && !!document.getElementById('inv')", 20)
    case("Open the post kit makes the vault and lands on its page", s.vault() is not None and len(s.vaults()) == 1 and c.js("decodeURIComponent(location.pathname)") == "/content/My vault/Post kit.html"
         and c.js("document.querySelector('h1').innerText") == "My vault.", c.js("location.href"))
    case("no error on the way", not c.errors, c.errors[:3])


def check_browser_vault(c, s):
    group("the vault's page in a browser")
    base = "http://127.0.0.1:%d" % s.port
    here = base + s.vault_page()
    c.open(here + "?fan=0")
    c.wait_for("!!document.getElementById('inv') && document.body.classList.contains('live')", 15)
    q = c.js("""(() => { const inv = document.getElementById('inv'), acts = inv.querySelector('.acts').getBoundingClientRect(), went = document.getElementById('invWent');
      return {chips: [...document.querySelectorAll('#invShoots span')].map(x => x.textContent), count: document.getElementById('invCount').textContent,
        btns: [...inv.querySelectorAll('button, a')].map(b => b.textContent.trim()), crumbs: document.querySelector('.crumbs').innerText.replace(/\\s+/g, ' '),
        cards: [...document.querySelectorAll('a.piece')].map(a => a.dataset.piece), ask: document.querySelector("a.piece[data-piece='reel'] .ask").innerText.replace(/\\s+/g, ' '),
        folders: document.querySelectorAll('.folders').length, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}; })()""")
    case("the strip shows the three shoots, the count, its two buttons and See everything in it", len(q["chips"]) == 3 and set(q["chips"]) == {"Fake beach", "Other farm", "Third hill"}
         and re.fullmatch(r"\d+ photos · 0 clips", q["count"]) and q["btns"] == ["+ Add a shoot", "+ Add clips", "See everything in it →"], q)
    case("the path reads Home › My post kits › My vault, and the box on the Reels card is hers", q["crumbs"] == "Home › My post kits › My vault" and q["ask"].upper().startswith("TELL THE ASSISTANT WHAT THIS REEL IS") and "Moms laughing, from any shoot" in q["ask"], q)
    case("the three cards, and no sideways scroll", q["cards"] == ["reel", "carousel", "stories"] and q["sw"] <= q["cw"], q)
    before = int(q["count"].split(" ")[0])
    # + Add clips: the line shows inside the strip, right under the buttons
    c.click("#vaultClips")
    c.wait_for("document.getElementById('invWent').textContent.indexOf('Put your videos in the folder that just opened.') === 0", 15)
    q = c.js("""(() => { const w = document.getElementById('invWent').getBoundingClientRect(), b = document.getElementById('vaultClips').getBoundingClientRect(), inv = document.getElementById('inv').getBoundingClientRect();
      return {under: w.top >= b.bottom - 2 && w.top - b.bottom < 40, inside: w.bottom <= inv.bottom + 1 && w.top >= inv.top}; })()""")
    case("+ Add clips: its line shows right under the buttons, inside the strip", q["under"] and q["inside"], q)
    # + Add a shoot: a new folder is "chosen" (the test's switch), the page follows the job, the count follows
    shutil.rmtree(s.picked, ignore_errors=True)             # the test's own pretend folder, made by this test
    s.folder("Wedding exports", {"page-01.jpg": pic(s, "p1"), "page-02.jpg": pic(s, "p2"), "page-03.jpg": pic(s, "p3")})
    c.click("#vaultAdd")
    c.wait_for("document.getElementById('invWent').textContent.indexOf('Copied 3 finished photos into your vault.') === 0", 40, tell="document.getElementById('invWent').textContent")
    c.wait_for("parseInt(document.getElementById('invCount').textContent) === %d && !document.getElementById('vaultAdd').disabled" % (before + 3), 15, tell="document.getElementById('invCount').textContent")
    case("+ Add a shoot: the line beside the button ends Copied 3 finished photos into your vault. Your originals weren't moved., and the strip's count went up by three",
         c.js("document.getElementById('invWent').textContent") == "Copied 3 finished photos into your vault. Your originals weren't moved." and all(n in s.own() for n in ("page-01.jpg", "page-02.jpg", "page-03.jpg")))
    case("nothing on the page names a place on this computer", not s.no_path(c.js("document.documentElement.outerHTML")), s.no_path(c.js("document.documentElement.outerHTML")))
    # the three cards
    for piece, want in (("reel", "/reel.html"), ("carousel", "/design.html"), ("stories", "/design.html")):
        c.open(here + "?fan=0")
        c.wait_for("!!document.querySelector(\"a.piece[data-piece='%s']\")" % piece, 15)
        c.click("a.piece[data-piece='%s'] .cta" % piece)
        c.wait_for("location.pathname === '%s' && document.readyState === 'complete'" % want, 20, tell="location.href")
        q = c.js("({kit: new URLSearchParams(location.search).get('kit'), kind: new URLSearchParams(location.search).get('kind'), text: document.body.innerText.slice(0, 4000)})")
        case(f"the {piece} card opens {want} for the vault" + (" (stories)" if piece == "stories" else ""),
             q["kit"] == "My vault" and (piece != "stories" or q["kind"] == "stories") and "can't reach" not in q["text"].lower(), {k: q[k] for k in ("kit", "kind")})
    c.open(here + "?fan=0")
    c.wait_for("!!document.querySelector('.crumbs a[href=\"/make-posts#kits\"]')", 15)
    c.click(".crumbs a[href='/make-posts#kits']")
    c.wait_for("location.pathname === '/make-posts' && !!document.getElementById('vaultCard')", 15)
    q = c.js("({small: document.querySelector('#vaultCard small').textContent, n: document.querySelectorAll('#recent .shoot').length})")
    case("the path leads back to the post kits, where My vault is still first and the shoots are still three", re.fullmatch(r"All your shoots in one post kit · \d+ photos", q["small"]) and q["n"] == 3, q)
    case("no error on any of these pages", not c.errors, c.errors[:3])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=9975)
    ap.add_argument("--work")
    ap.add_argument("--no-chrome", action="store_true", help="everything but the pages in a browser")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        skip("the pretend photos are drawn with the Mac's own sips: nothing to run on this computer")
        return 0
    if a.port in (8790, 8791, 8792, 8799) or a.port in getattr(chrome_drive, "NEVER_PORTS", ()):
        print("STOP: that port is the real Assistant's.")
        return 2
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-page-", dir="/private/tmp")).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    work.mkdir(parents=True, exist_ok=True)
    (work / "home").mkdir(exist_ok=True)
    s = World(work, a.port)
    os.environ.update(STUDIO_HOME=str(s.studio), STUDIO_NO_WINDOWS_FOR_TESTS="1", HOME=str(work / "home"))
    try:
        s.fake(s.target, "Fake beach", 8)
        s.fake(s.target, "Other farm", 9)
        s.fake(s.target, "Third hill", 10)
        s.own_picture(B, "beach-002.jpg")
        s.start()
        case("the page server is this test's own, on a scratch port and a scratch home", s.port not in (8790, 8791, 8792, 8799) and str(s.studio).startswith(str(work)))
        check_list_page(s)
        check_open_guard(s)
        browser = None if a.no_chrome else chrome_drive.find_chrome()
        if browser:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                check_browser_list(c, s)
        else:
            skip("the post kits list in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
            open_by_request(s)
        check_made_once(s)
        check_vault_page(s)
        check_her_words(s)
        check_add(s)
        check_routes(s)
        if browser:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                check_browser_vault(c, s)
        else:
            skip("the vault's page in a browser")
    finally:
        s.stop()
        chrome_drive.stop_all()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    n, bad = core.COUNT[0], core.FAILED
    print(f"\n{n - len(bad)} of {n} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
