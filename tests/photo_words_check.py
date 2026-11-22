#!/usr/bin/env python3
"""Photo descriptions beside each kit, and the search rule (Nicole's v29, 1.4 and 1.5): stage 8, vault-search.

    python3 tests/guard.py 3000 python3 tests/photo_words_check.py [--port 9981] [--no-chrome] [--work <folder under /private/tmp>]

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME; never the real
~/.studio, no drive; STUDIO_NO_WINDOWS_FOR_TESTS). The classifier is a pretend one (PHOTO_WORDS_PRETEND: a file of
photo name -> tags), so nothing asks the Mac's Vision, except the one last check, which may SKIP.

  * the search rule: her everyday words ignored (and the clip search's extra ones), every other word must match,
    case and accents, "laugh" finds "laughing";
  * the store: written whole, the version before kept, keyed by the photo's size and time so a changed photo is
    done again and its description is flagged; a second run writes nothing;
  * describe: a bad file is refused whole (a number not on the list, two lines, a slash, an extra field, too long,
    too many), a good one saves, twice writes nothing; a vault photo from a shoot is sent to that shoot's kit;
  * the job: started by opening the post kit's page, fills the store in batches, the state counts up and ends
    done; a classifier that does not answer records nothing and is never "done"; nothing starts by itself in a test
    that did not ask; the route refuses another site and an unknown kit;
  * every photo byte for byte unchanged and none renamed, all the way through;
  * the vault: its job writes each shoot's tags into that shoot's own file; the catalog has shoots, photos and
    clips (each clip once, an unnamed one "Not named yet") and no place on this computer in it; `vault.py find`;
  * a pretend PC (no classifier): no job, the PC line on the page, search still finds by shoot name and by
    written words;
  * in a browser: her line shows while the job runs and goes when it is done, the rest of the page works, then
    the line to copy.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. A Mac
(the pretend photos are drawn with the Mac's own sips); anywhere else it says SKIP and exits 0.
"""
import argparse
import hashlib
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
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
import vault_core_check as core  # noqa: E402
from vault_core_check import A, B, case, group, tree  # noqa: E402

D = "2026-11-01 Zoë's hill"                 # the kit whose page is opened by request (26 photos: three batches)
E = "2026-11-01 Long day"                   # the kit whose page is opened in the browser
HER_LINE = re.compile(r"Getting your photos ready to search: (\d+) of (\d+)\.")
TABLE = {
    "beach-001.jpg": [["sand", 0.5], ["Beach", 0.9], "outdoor", "blue_sky"],
    "beach-002.jpg": {"tags": ["ring", "jewelry"], "faces": 1},
    "beach-003.jpg": {"tags": ["Café_table"], "faces": 3},
    "beach-005.png": None,                  # a picture that can't be read
    "BEACH-007.JPG": ["x" * 60, "a/b", "green", "green", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11", "t12", "t13"],
}


def skip(line):
    print("SKIP  " + line, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class World(core.Run):
    def __init__(self, work, port):
        super().__init__(work, port)
        self.table = self.work / "pretend-tags.json"
        self.table.write_text(json.dumps(TABLE), encoding="utf-8")
        self.env["PHOTO_WORDS_PRETEND"] = str(self.table)
        self.env["STUDIO_PHOTO_WORDS_PAUSE_FOR_TESTS"] = "1.6"
        self.quick = dict(self.env)
        self.quick.pop("STUDIO_PHOTO_WORDS_PAUSE_FOR_TESTS")
        self.pc = dict(self.quick, PHOTO_WORDS_PRETEND="none")
        self.quiet = dict(self.quick)
        self.quiet.pop("PHOTO_WORDS_PRETEND")           # a test that did not ask: nothing may start by itself
        self.broken = dict(self.quick, PHOTO_WORDS_PRETEND=str(self.work / "no-such-table.json"))

    def fake(self, target, name, photos):
        env, self.env = self.env, self.quiet            # making a pretend kit asks for no photo words
        try:
            super().fake(target, name, photos)
        finally:
            self.env = env

    def kit(self, name):
        return self.content / name

    def store(self, name):
        return self.kit(name) / ".kit" / "photo-words.json"

    def words(self, name):
        try:
            return json.loads(self.store(name).read_text(encoding="utf-8"))["photos"]
        except (OSError, ValueError):
            return {}

    def rows_of(self, name):
        return json.loads((self.kit(name) / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]

    def n(self, name, file):
        return str(next(x["n"] for x in self.rows_of(name) if Path(x["file"]).name == file))

    def photos(self, name):
        """A kit's photos: every name and its hash."""
        return {p.name: sha(p) for p in sorted((self.kit(name) / "Photos").iterdir()) if p.is_file()}

    def state(self, name, origin=None, extra=""):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Host": "127.0.0.1:%d" % self.port}
        if origin:
            h["Sec-Fetch-Site"] = origin
        c.request("GET", "/photo-words-state?kit=" + quote(name, safe="") + extra, headers=h)
        r = c.getresponse()
        raw = r.read().decode("utf-8", "replace")
        c.close()
        try:
            return r.status, json.loads(raw), raw
        except ValueError:
            return r.status, None, raw

    def kit_page(self, name):
        return "/content/" + quote(name, safe="") + "/Post%20kit.html"

    def no_path(self, text):
        return [w for w in (str(self.work), "/private/tmp", "/Users/", "/Volumes/", str(self.studio)) if w in text]

    def py(self, code, env=None):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r)\n" % str(SCRIPTS) + code],
                           capture_output=True, text=True, env=env or self.quick)
        return r.returncode, (r.stdout + r.stderr).strip()

    def file(self, name, obj):
        p = self.work / name
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
        return str(p)


def check_rule(s):
    group("the search rule (hers), in one place")
    code, out = s.py("""
import json, vault
w, f = vault.search_words, vault.found
print(json.dumps({
  "everyday": w("Me with my camera on the beach, and a kiss at the END"),
  "all_everyday": w("me my on the a an of with at in and I to"),
  "clip_extra": w("Find every clip of me editing from any shoot", clips=True),
  "photo_keeps": w("find every clip from any"),
  "split": w("green-backdrop/ring_close.up  2nd"),
  "accent": w("Zoë CAFÉ"),
  "every": [f(w("mom laughing"), "Mom laughing with the kids"), f(w("mom kiss"), "Mom laughing with the kids")],
  "part": f(w("laugh"), "people LAUGHING"),
  "accents": [f(w("zoe cafe"), "Café table Zoë's hill"), f(w("Zoë"), "zoe")],
  "empty": f([], "anything"),
  "together": f(w("Hannah laughing beach"), "outdoor beach Mom laughing at the water Hannah Maternity"),
  "sets": [sorted(vault.EVERYDAY), sorted(vault.CLIP_EVERYDAY - vault.EVERYDAY)],
}))""")
    try:
        q = json.loads(out.splitlines()[-1])
    except (ValueError, IndexError):
        q = {}
    case("everyday words are ignored: me, my, on, the, a, an, of, with, at, in, and, i, to (and only those)",
         q.get("everyday") == ["camera", "beach", "kiss", "end"] and q.get("all_everyday") == []
         and q.get("sets", [None])[0] == sorted("me my on the a an of with at in and i to".split()), out[-600:])
    case("the clip search also ignores find, every, clip, clips, from, any; the photo search keeps them",
         q.get("clip_extra") == ["editing", "shoot"] and q.get("photo_keeps") == ["find", "every", "clip", "from", "any"]
         and q.get("sets", [None, None])[1] == sorted("find every clip clips from any".split()), q)
    case("split on anything that is not a letter or a number, lower case", q.get("split") == ["green", "backdrop", "ring", "close", "up", "2nd"], q.get("split"))
    case("every word left must be found, and a part of a word finds it (\"laugh\" finds \"laughing\")", q.get("every") == [True, False] and q.get("part") is True, q)
    case("case and accents: zoe finds Zoë, cafe finds Café, and the other way round", q.get("accent") == ["zoe", "cafe"] and q.get("accents") == [True, True], q)
    case("tags, words and the shoot's name are searched together (\"Hannah laughing beach\"), and no words finds everything", q.get("together") is True and q.get("empty") is True, q)


def check_store(s):
    group("the store: this computer's tags, written whole, the version before kept")
    before = s.photos(A)
    case("before anything: no photo words file, and the kit's state is 0 of 8, not running",
         not s.store(A).exists() and json.loads(s.cmd("photo_words.py", "state", A, env=s.quick)[1]) == {"done": 0, "total": 8, "running": False, "can": True, "described": 0})
    code, out = s.cmd("photo_words.py", "tag", A, env=s.quick)
    w = s.words(A)
    n1, n2, n3, n5, n7 = (s.n(A, f) for f in ("beach-001.jpg", "beach-002.jpg", "beach-003.jpg", "beach-005.png", "BEACH-007.JPG"))
    case("the tags are saved for all 8 photos, by number", code == 0 and len(w) == 8 and "8 of 8 photos done" in out, out)
    case("labels: underscores to spaces, lower case, the surest first", w.get(n1, {}).get("tags") == ["outdoor", "blue sky", "beach", "sand"], w.get(n1))
    case("one face adds \"one person\", several add \"people\"", w.get(n2, {}).get("tags") == ["ring", "jewelry", "one person"] and w.get(n3, {}).get("tags") == ["people"], (w.get(n2), w.get(n3)))
    t7 = w.get(n7, {}).get("tags") or []
    case("at most 12 labels a photo, each once, plain words only (no slash, nothing overlong)", len(t7) == 12 and t7[0] == "green" and len(set(t7)) == 12 and all(re.fullmatch(r"[a-z0-9 ]{1,40}", t) for t in t7), t7)
    case("a picture that can't be read is marked looked at, with no tags, and never tried on every page load", w.get(n5, {}).get("unread") is True and w.get(n5, {}).get("tags") == [])
    src = s.kit(A) / "Photos" / "beach-002.jpg"
    st = src.stat()
    case("each entry carries the photo's name-size-time key, who wrote the tags and when",
         w[n2]["key"] == "%s-%d-%d" % (hashlib.sha1(b"beach-002.jpg").hexdigest()[:6], st.st_size, st.st_mtime_ns) and w[n2]["tags_by"] == "mac" and re.match(r"\d{4}-\d\d-\d\dT", w[n2]["tags_at"]), w.get(n2))
    case("the file is whole JSON, and no scratch copy is left beside it", json.loads(s.store(A).read_text())["v"] == 1
         and not [x for x in os.listdir(s.kit(A) / ".kit") if x.endswith(".tmp")], os.listdir(s.kit(A) / ".kit"))
    raw, at = s.store(A).read_bytes(), s.store(A).stat().st_mtime_ns
    code, out = s.cmd("photo_words.py", "tag", A, env=s.quick)
    case("a second run writes nothing", code == 0 and s.store(A).read_bytes() == raw and s.store(A).stat().st_mtime_ns == at, out)
    # your assistant's words, then the photo is exported again
    code, out = s.cmd("photo_words.py", "describe", A, "--file", s.file("w1.json", {"photos": {n2: {"words": "Close-up of  the ring on a hand"}, n3: {"words": "Mom laughing with the kids at the water"}}}), env=s.quick)
    w2 = s.words(A)
    case("describe saves the words beside the tags (one plain line, spaces tidied), who and when, and the photo it was written for",
         code == 0 and "Saved 2 descriptions" in out and w2[n2]["words"] == "Close-up of the ring on a hand" and w2[n2]["words_by"] == "assistant"
         and w2[n2]["words_key"] == w2[n2]["key"] and w2[n2]["tags"] == w[n2]["tags"] and "words" not in w2[n1], out)
    case("the version before is kept beside it, byte for byte", (s.kit(A) / ".kit" / "photo-words.prev.json").read_bytes() == raw)
    raw2 = s.store(A).read_bytes()
    shutil.copyfile(s.kit(A) / "Photos" / "beach-003.jpg", src)        # the test's own pretend photo, "exported again"
    os.utime(src, (time.time() + 5, time.time() + 5))
    before["beach-002.jpg"] = sha(src)
    st1 = json.loads(s.cmd("photo_words.py", "state", A, env=s.quick)[1])
    case("a photo exported again is not done any more: 7 of 8", st1["done"] == 7 and st1["total"] == 8 and st1["described"] == 2, st1)
    table = dict(TABLE, **{"beach-002.jpg": ["kiss"]})
    s.table.write_text(json.dumps(table), encoding="utf-8")
    code, out = s.cmd("photo_words.py", "tag", A, env=s.quick)
    w3 = s.words(A)
    case("it is looked at again: new key, new tags, its description kept", code == 0 and w3[n2]["key"] != w2[n2]["key"] and w3[n2]["tags"] == ["kiss"]
         and w3[n2]["words"] == "Close-up of the ring on a hand" and w3[n2]["words_key"] == w2[n2]["key"], w3.get(n2))
    case("and the version before that change is the one kept", (s.kit(A) / ".kit" / "photo-words.prev.json").read_bytes() == raw2)
    code, out = s.cmd("photo_words.py", "status", A, env=s.quick)
    case("status says which numbers have no description, and which were described before the photo was exported again",
         code == 0 and "6 with no description yet" in out and ("exported again (worth another look): %s." % n2) in out, out)
    case("every photo of the kit is byte for byte what it was, and none was renamed", s.photos(A) == before, sorted(set(s.photos(A)) ^ set(before)))
    return before


def check_describe(s, before):
    group("describe: the whole file is checked before anything is saved")
    raw = s.store(A).read_bytes()
    n1 = s.n(A, "beach-001.jpg")
    bad = [
        ("a number not on the list", {"photos": {n1: {"words": "fine"}, "999": {"words": "not there"}}}, "no photo numbered 999"),
        ("two lines", {"photos": {n1: {"words": "one line\nand another"}}}, "more than one line"),
        ("a place on the computer in the words", {"photos": {n1: {"words": "the one in /Users/me/Pictures"}}}, "slash"),
        ("a backslash", {"photos": {n1: {"words": "C:\\photos"}}}, "slash"),
        ("an extra field on a photo", {"photos": {n1: {"words": "fine", "tags": ["x"]}}}, "a field I don't know"),
        ("an extra field on the file", {"photos": {n1: {"words": "fine"}}, "kit": "x"}, "the file needs"),
        ("more than 140 letters", {"photos": {n1: {"words": "w" * 141}}}, "longer than 140"),
        ("no words", {"photos": {n1: {"words": "   "}}}, "needs its words"),
        ("a number that is not a number", {"photos": {"../" + n1: {"words": "fine"}}}, "isn't a photo number"),
        ("words that are not text", {"photos": {n1: {"words": 12}}}, "needs its words"),
        ("more than 2,000 photos", {"photos": {str(i): {"words": "x"} for i in range(1, 2002)}}, "more than 2,000"),
        ("a file that is not JSON", "{not json", "couldn't read the file"),
    ]
    for what, obj, say in bad:
        code, out = s.cmd("photo_words.py", "describe", A, "--file", s.file("bad.json", obj), env=s.quick)
        case(f"refused whole: {what} (nothing saved, not even the good photo beside it)", code == 2 and say in out and "Nothing was saved." in out and s.store(A).read_bytes() == raw, out[-300:])
    good = {"photos": {n1: {"words": "Wide shot of the beach, a green backdrop"}}}
    code, out = s.cmd("photo_words.py", "describe", A, "--file", s.file("good.json", good), env=s.quick)
    raw2, at = s.store(A).read_bytes(), s.store(A).stat().st_mtime_ns
    case("a good file saves, and says no photo was touched or renamed", code == 0 and "Saved 1 description." in out and "No photo was touched or renamed" in out and raw2 != raw, out)
    code, out = s.cmd("photo_words.py", "describe", A, "--file", s.file("good.json", good), env=s.quick)
    case("the same file twice writes nothing", code == 0 and "Nothing was written." in out and s.store(A).read_bytes() == raw2 and s.store(A).stat().st_mtime_ns == at, out)
    code, out = s.cmd("photo_words.py", "sheets", A, env=s.quick)
    case("sheets prints the kit's numbered contact sheet and the numbers with no description", code == 0 and re.search(r"Sheet: .+\.png", out)
         and "5 with no description yet" in out and "never photo by photo" in out, out[-500:])
    case("the photos are still byte for byte what they were", s.photos(A) == before)


def wait_done(s, name, seconds=60):
    seen, end = [], time.time() + seconds
    while time.time() < end:
        code, j, _ = s.state(name)
        if j:
            seen.append((j["done"], j["total"], j["running"]))
            if not j["running"] and j["total"] > 0 and j["done"] == j["total"]:
                break
        time.sleep(0.15)
    return seen


def check_job(s):
    group("the job: started by opening the post kit's page, followed at /photo-words-state")
    before, whole = s.photos(D), {k: v for k, v in tree(s.kit(D)).items() if not k.startswith(".kit/")}
    code, j, raw = s.state(D)
    case("before the page is opened: 0 of 26, not running, and nothing is written by asking", code == 200 and j == {"ok": True, "done": 0, "total": 26, "running": False, "can": True, "described": 0}
         and not s.store(D).exists(), raw)
    case("the answer has no place on this computer in it", not s.no_path(raw), raw)
    code, _, _ = s.state(D, origin="cross-site")
    case("another website's ask is refused", code == 403)
    case("an unknown kit, a path for a kit, or an extra field: not found", s.state("No such kit")[0] == 404 and s.state("../" + D)[0] == 404 and s.state(D, extra="&x=1")[0] == 404)
    code, _, raw = s.http("GET", s.kit_page(D))
    page = raw.decode("utf-8", "replace")
    case("the post kit's page carries the line's place, hidden, and the line to copy with the shoot's own name",
         code == 200 and "id='pwGetting' role='status' hidden" in page and "Describe my photos for Zoë&#x27;s hill" in page and "id='pwMore' hidden" in page, page[page.find("id='pw'"):][:500])
    seen = wait_done(s, D)
    dones = [d for d, _, _ in seen]
    case("the job runs by itself once the page is opened, and the state says so", any(r for _, _, r in seen), seen[:8])
    case("the count goes up in batches (0, 12, 24, 26) and never down", dones == sorted(dones) and len({d for d in dones if 0 < d < 26}) >= 1 and {d for d in dones} <= {0, 12, 24, 26}, sorted(set(dones)))
    code, j, _ = s.state(D)
    case("it ends done: 26 of 26, not running", j and j["done"] == 26 and j["total"] == 26 and j["running"] is False, j)
    w = s.words(D)
    case("the store has every photo, with the pretend classifier's tags", len(w) == 26 and w[s.n(D, "beach-001.jpg")]["tags"] == ["outdoor", "blue sky", "beach", "sand"], len(w))
    after = {k: v for k, v in tree(s.kit(D)).items() if not k.startswith(".kit/")}
    case("every photo is byte for byte unchanged and none was renamed; nothing outside the kit's hidden folder changed", s.photos(D) == before and after == whole,
         sorted(k for k in set(after) | set(whole) if after.get(k) != whole.get(k))[:6])
    raw_store = s.store(D).read_bytes()
    s.http("GET", s.kit_page(D))
    time.sleep(1.0)
    code, j, _ = s.state(D)
    case("opening the page again starts nothing and writes nothing", j and not j["running"] and s.store(D).read_bytes() == raw_store, j)

    group("a classifier that does not answer; a test that did not ask")
    code, out = s.cmd("photo_words.py", "tag", B, env=s.broken)
    stb = json.loads(s.cmd("photo_words.py", "state", B, env=s.broken)[1])
    case("the classifier does not answer: nothing is recorded as looked at, and the kit is not \"done\"", code == 1 and not s.store(B).exists() and stb["done"] == 0 and stb["total"] == 9 and not stb["running"], (out, stb))
    code, out = s.py("import photo_words, kit; from pathlib import Path\nk = Path(%r)\nprint(photo_words.auto(), photo_words.opened(k), photo_words.running(k))" % str(s.kit(B)), env=s.quiet)
    case("inside a test that set no pretend classifier, nothing starts by itself (so no test asks the real Vision by accident)", out.splitlines()[-1:] == ["False False False"] and not s.store(B).exists(), out)
    code, out = s.py("import photo_words; from pathlib import Path\nprint(photo_words.auto(), photo_words.here())", env=s.quick)
    case("with the pretend classifier set, a job may start", out.splitlines()[-1:] == ["True True"], out)


def check_vault(s):
    group("the vault: each shoot's words in that shoot's own file; the catalog; find")
    v = s.vault()
    own = v / "Photos" / "added-001.jpg"
    shutil.copyfile(s.kit(A) / "Photos" / "beach-003.jpg", own)        # a photo added to the vault itself (the test's own)
    os.utime(own, (time.time() - 30, time.time() - 30))
    code, out = s.cmd("vault.py", "relist", env=s.quiet)
    photos_before = {k: s.photos(k) for k in (A, B, D)}
    table = json.loads(s.table.read_text())
    table["added-001.jpg"] = ["cake"]
    s.table.write_text(json.dumps(table), encoding="utf-8")
    code, out = s.cmd("photo_words.py", "tag", v.name, env=s.quick)
    rows = s.rows()
    own_n = str(next(x["n"] for x in rows if x["kit"] == ""))
    vw = json.loads((v / ".kit" / "photo-words.json").read_text())["photos"]
    case("the vault's job looks at every photo on its list", code == 0 and ("%d of %d photos done" % (len(rows), len(rows))) in out, out)
    case("the vault's own file holds only the photo added to the vault itself", list(vw) == [own_n] and vw[own_n]["tags"] == ["cake"], vw)
    case("a shoot's photos are in that shoot's own file, under its own numbers (the farm's 9, tagged through the vault)", len(s.words(B)) == 9 and s.words(B)[s.n(B, "beach-002.jpg")]["tags"] == ["kiss"], s.words(B))
    case("no photo of any shoot was touched or renamed", {k: s.photos(k) for k in (A, B, D)} == photos_before)
    # a description for the vault's own photo; a shoot's photo is sent to its own kit
    bn = str(s.n_of(B, "beach-002.jpg"))
    code, out = s.cmd("photo_words.py", "describe", v.name, "--file", s.file("v1.json", {"photos": {bn: {"words": "x"}}}), env=s.quick)
    case("describing a shoot's photo through the vault is refused, with the kit and the number to use there", code == 2 and ("is in the post kit \"%s\" (its number there is %s)" % (B, s.n(B, "beach-002.jpg"))) in out, out)
    code, out = s.cmd("photo_words.py", "describe", v.name, "--file", s.file("v2.json", {"photos": {own_n: {"words": "Cutting the cake in the kitchen"}}}), env=s.quick)
    case("the vault's own photo takes a description", code == 0 and "Saved 1 description." in out, out)
    code, out = s.cmd("photo_words.py", "describe", B, "--file", s.file("b1.json", {"photos": {s.n(B, "beach-003.jpg"): {"words": "Dad lifting the baby by the barn"}}}), env=s.quick)
    code, out = s.cmd("photo_words.py", "status", v.name, env=s.quick)
    case("status for the vault says how many have no description, shoot by shoot, with the command for each",
         code == 0 and re.search(r"In the vault: \d+ photos, \d+ with no description yet, in 3 post kits\.", out) and ("  %s: 8 of 9 photos with no description" % B) in out
         and "photo_words.py sheets \"%s\"" % D in out, out)
    # clips: one named, one not, one in two reels, in a shoot's reel record (the test's own pretend record)
    m1 = {"id": "u1-81563a", "video": "Footage/walk.mov", "start": 1.0, "end": 4.5, "by": "you", "label": "Walking into the frame with my camera"}
    m2 = {"id": "u2-0a0a0a", "video": "Footage/walk.mov", "start": 69.6, "end": 72.0, "by": "you", "label": "Your pick at 1:09.6"}
    m3 = {"id": "m1-abcdef", "video": "Footage/cake.mov", "start": 0.0, "end": 3.0, "by": "assistant", "label": "Laughing with the cupcake and knife"}
    (s.kit(A) / ".kit" / "reel-page.json").write_text(json.dumps({"v": 1, "moments": [m1, m2], "current": "v1", "versions": [
        {"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2", "data": {"moments": [m1, m3]}}]}), encoding="utf-8")
    code, out = s.py("import json, vault\nprint(json.dumps(vault.catalog(vault.find())))")
    try:
        cat = json.loads(out.splitlines()[-1])
    except (ValueError, IndexError):
        cat = {"shoots": [], "photos": [], "clips": []}
    case("the catalog has no place on this computer in it, and no file name of a photo", not s.no_path(out) and "beach-001" not in out and ".jpg" not in out, s.no_path(out))
    sh = {x["kit"]: x for x in cat["shoots"]}
    case("the catalog's shoots: what was added first, then each shoot with its name, counts and a picture's number",
         cat.get("vault") is True and cat["shoots"][0]["group"] == "added" and cat["shoots"][0]["photos"] == 1 and set(sh) == {"", A, B, D}
         and sh[A]["name"] == "Fake beach" and sh[A]["photos"] == 8 and sh[A]["clips"] == 3 and sh[B]["clips"] == 0 and type(sh[B]["thumb"]) is int, cat["shoots"])
    ph = {x["n"]: x for x in cat["photos"]}
    farm = ph[s.n_of(B, "beach-003.jpg")]
    case("a photo's text is its tags, its words and its shoot's name together", farm["kit"] == B and farm["text"] == "people Dad lifting the baby by the barn Other farm"
         and ph[int(own_n)]["text"] == "cake Cutting the cake in the kitchen" and len(cat["photos"]) == len(rows), (farm, ph[int(own_n)]))
    cl = {x["id"]: x for x in cat["clips"]}
    case("every clip of every reel, each once; an unnamed one is \"Not named yet\" with only its shoot's name to find",
         len(cat["clips"]) == 3 and cl["u1-81563a"]["text"] == "Walking into the frame with my camera Fake beach" and cl["u1-81563a"]["video"] == "walk.mov"
         and cl["u2-0a0a0a"]["label"] == "Not named yet" and cl["u2-0a0a0a"]["named"] is False and cl["u2-0a0a0a"]["text"] == "Fake beach"
         and cl["m1-abcdef"]["by"] == "assistant" and all(c["kit"] == A for c in cat["clips"]), cat["clips"])
    code, out = s.py("import json, vault\nfrom pathlib import Path\nprint(json.dumps(vault.catalog(Path(%r))))" % str(s.kit(B)))
    one = json.loads(out.splitlines()[-1])
    case("a shoot's own post kit has a catalog too: one shoot, its photos by its own numbers", one["vault"] is False and [x["kit"] for x in one["shoots"]] == [B] and len(one["photos"]) == 9
         and not s.no_path(out), one["shoots"])
    # find, for the chat
    code, out = s.cmd("vault.py", "find", "the FARM, lifting a baby", env=s.quick)
    case("find: photos by words and shoot name together, everyday words ignored", code == 0 and "Photos matching \"farm lifting baby\": 1" in out and ("  Other farm: %d" % s.n_of(B, "beach-003.jpg")) in out, out)
    code, out = s.cmd("vault.py", "find", "Find every clip of me with my camera", "--clips", env=s.quick)
    case("find --clips: the clip search's own everyday words, the clip by its name, its shoot and where it is in its video",
         code == 0 and "Clips matching \"camera\": 1." in out and "u1-81563a | Fake beach | Walking into the frame with my camera | walk.mov 1 to 4.5 s" in out and "Photos" not in out, out)
    code, out = s.cmd("vault.py", "find", "cake", env=s.quick)
    case("find: a photo added to the vault itself, and a clip (\"cake\" is in \"cupcake\"), by one word", "  Added to my vault: %s" % own_n in out and "m1-abcdef" in out and "Clips matching \"cake\": 1." in out, out)
    code, out = s.cmd("vault.py", "find", "laughing", "--clips", env=s.quick)
    case("find: \"laughing\" finds the clip the Assistant named", "m1-abcdef | Fake beach | Laughing with the cupcake and knife" in out, out)
    code, out = s.cmd("vault.py", "find", "beach", "--clips", env=s.quick)
    case("find: a shoot's name finds its clips, the unnamed one too, as Not named yet", "Clips matching \"beach\": 3." in out and "u2-0a0a0a | Fake beach | Not named yet" in out, out)
    code, out = s.cmd("vault.py", "find", "me with the", env=s.quick)
    case("find: only everyday words is no search, said plainly", code == 0 and "no word to search by" in out, out)
    case("find's lines have no place on this computer in them", not s.no_path(out))
    case("still no photo touched or renamed", {k: s.photos(k) for k in (A, B, D)} == photos_before)


def check_pc(s):
    group("a pretend PC: no classifier")
    code, out = s.py("import photo_words, kit; from pathlib import Path\nk = Path(%r)\nprint(photo_words.here(), photo_words.opened(k), photo_words.state(k)['can'])" % str(s.kit(E)), env=s.pc)
    case("no classifier here: nothing starts, and the state says so", out.splitlines()[-1:] == ["False False False"] and not s.store(E).exists(), out)
    code, out = s.cmd("photo_words.py", "tag", E, env=s.pc)
    case("asked for tags from the chat, it says the PC line and writes nothing", code == 3 and "On a PC, search finds your photos by shoot name and by anything the Assistant has described." in out and not s.store(E).exists(), out)
    code, out = s.py("import kit; from pathlib import Path\nprint(kit.page_html(Path(%r)))" % str(s.kit(E)), env=s.pc)
    case("the post kit page carries the PC line with the line to copy, and not the Mac's line",
         "On a PC, search finds your photos by shoot name and by anything the Assistant has described. To have them described, copy this into the chat:" in out
         and "Describe my photos for Long day" in out and "Want search to find more" not in out, out[out.find("id='pw'"):][:400])
    code, out = s.py("import kit; from pathlib import Path\nprint(kit.page_html(Path(%r)))" % str(s.kit(E)), env=s.quick)
    case("on a Mac the same page carries the Mac's quiet line instead", "Want search to find more, like &quot;laughing&quot; or &quot;a kiss&quot;? Copy this into the chat:" in out and "On a PC" not in out)
    code, out = s.cmd("photo_words.py", "describe", E, "--file", s.file("pc.json", {"photos": {"1": {"words": "A kiss under the oak tree"}}}), env=s.pc)
    case("descriptions are saved on a PC all the same", code == 0 and s.words(E)["1"]["words"] == "A kiss under the oak tree" and "tags" not in s.words(E)["1"], out)
    code, out = s.cmd("vault.py", "relist", env=s.pc)
    code, out = s.cmd("vault.py", "find", "kiss oak", "--photos", env=s.pc)
    case("search still finds by written words", code == 0 and "Photos matching \"kiss oak\": 1" in out and "  Long day: " in out, out)
    code, out = s.cmd("vault.py", "find", "long day", "--photos", env=s.pc)
    case("and by the shoot's name", code == 0 and "Photos matching \"long day\": 26" in out, out)


def check_browser(c, s):
    group("the post kit page in a browser: her line while the job runs")
    base = "http://127.0.0.1:%d" % s.port
    before = s.photos(E)
    raw = s.store(E).read_bytes()
    c.open(base + s.kit_page(E) + "?fan=0")
    c.wait_for("(() => { const g = document.getElementById('pwGetting'); return !!g && !g.hidden && /of 26\\.$/.test(g.textContent); })()", 20,
               tell="document.getElementById('pw') && document.getElementById('pw').outerHTML")
    q = c.js("""(() => { const g = document.getElementById('pwGetting'), r = g.getBoundingClientRect(), p = document.getElementById('pieces').getBoundingClientRect();
      return {text: g.textContent, shown: r.height > 0 && r.width > 0, above: r.bottom <= p.top + 1, more: document.getElementById('pwMore').hidden,
        cards: [...document.querySelectorAll('a.piece')].map(a => a.dataset.piece), sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}; })()""")
    m = HER_LINE.fullmatch(q["text"])
    case("her line shows while the photos are looked at: \"Getting your photos ready to search: N of 26.\"", bool(m) and int(m.group(2)) == 26 and int(m.group(1)) < 26 and q["shown"], q)
    case("it sits above the cards, the line to copy is not shown yet, and nothing scrolls sideways", q["above"] and q["more"] is True and q["sw"] <= q["cw"], q)
    seen = set()
    end = time.time() + 40
    while time.time() < end:
        t = c.js("(() => { const g = document.getElementById('pwGetting'); return g.hidden ? '' : g.textContent; })()")
        if not t:
            break
        mm = HER_LINE.fullmatch(t)
        if mm:
            seen.add(int(mm.group(1)))
        time.sleep(0.2)
    case("the count goes up on the page while everything else is there to use (the three cards)", len(seen) >= 2 and q["cards"] == ["reel", "carousel", "stories"], sorted(seen))
    c.wait_for("document.getElementById('pwGetting').hidden && !document.getElementById('pwMore').hidden", 20, tell="document.getElementById('pw').outerHTML")
    q = c.js("""(() => { const m = document.getElementById('pwMore'), b = document.getElementById('pwCopy').getBoundingClientRect(), l = document.getElementById('pwLine').getBoundingClientRect();
      return {getting: document.getElementById('pwGetting').textContent, said: m.querySelector('p').textContent, line: document.getElementById('pwLine').textContent,
        copy: document.getElementById('pwCopy').textContent, beside: Math.abs(b.top - l.top) < 30 && b.left >= l.right - 1, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth}; })()""")
    case("when it is done her line is gone, and the quiet line shows with the words to copy and a Copy button right beside them",
         q["getting"] == "" and q["said"] == "Want search to find more, like \"laughing\" or \"a kiss\"? Copy this into the chat:" and q["line"] == "Describe my photos for Long day"
         and q["copy"] == "Copy" and q["beside"] and q["sw"] <= q["cw"], q)
    c.click("#pwCopy")
    c.wait_for("document.getElementById('pwWent').textContent !== ''", 10)
    case("Copy says what happened right beside the button", c.js("document.getElementById('pwWent').textContent") in ("Copied. Paste it into the chat.", "Couldn't copy that. Select the line and copy it yourself."),
         c.js("document.getElementById('pwWent').textContent"))
    w = s.words(E)
    case("the store was filled while the page was open (26 photos), the description from before kept", len(w) == 26 and w["1"]["words"] == "A kiss under the oak tree" and "tags_at" in w["1"] and s.store(E).read_bytes() != raw, len(w))
    case("every photo byte for byte unchanged, none renamed", s.photos(E) == before)
    case("nothing on the page names a place on this computer", not s.no_path(c.js("document.documentElement.outerHTML")), s.no_path(c.js("document.documentElement.outerHTML")))
    # all 26 described: nothing to offer any more
    code, out = s.cmd("photo_words.py", "describe", E, "--file", s.file("all.json", {"photos": {str(x["n"]): {"words": "Photo of the long day"} for x in s.rows_of(E)}}), env=s.quick)
    c.open(base + s.kit_page(E) + "?fan=0")
    c.wait_for("document.body.classList.contains('live') || document.readyState === 'complete'", 15)
    time.sleep(1.0)
    q = c.js("({g: document.getElementById('pwGetting').hidden, m: document.getElementById('pwMore').hidden})")
    case("once every photo has a description, neither line shows", code == 0 and q == {"g": True, "m": True}, (q, out))
    c.open(base + "/content/" + quote(s.vault().name, safe="") + "/Post%20kit.html?fan=0")
    c.wait_for("!!document.getElementById('pwLine')", 15)
    c.wait_for("document.getElementById('pwGetting').hidden", 60)
    case("on the vault's page the line to copy is \"Describe the photos in my vault\"", c.js("document.getElementById('pwLine').textContent") == "Describe the photos in my vault")
    case("no error on these pages", not c.errors, c.errors[:3])


def check_real(s):
    group("the Mac's own classifier, once (may SKIP)")
    if sys.platform != "darwin":
        skip("Apple's image classifier: not a Mac")
        return
    pic = s.kit(A) / "Photos" / "beach-001.jpg"
    env = dict(s.quiet)
    code, out = s.py("import json, photo_words\nprint(json.dumps(photo_words.classify([(%r, 'x.jpg'), (%r, 'gone.jpg')])))" % (str(pic), str(s.work / "gone.jpg")), env=env)
    try:
        got = json.loads(out.splitlines()[-1])
    except (ValueError, IndexError):
        got = None
    if got is None:
        skip("Apple's image classifier did not answer through the Mac's scripting on this computer: " + out[-200:])
        return
    case("Apple's classifier answers through the Mac's scripting: a list of plain labels for a picture (maybe none), and \"could not be read\" for a file that is not there",
         isinstance(got, list) and len(got) == 2 and isinstance(got[0], list) and all(re.fullmatch(r"[a-z0-9 ]{1,40}", t) for t in got[0]) and got[1] is None, got)
    case("the real look changed nothing in the kit", sha(pic) == s.photos(A)["beach-001.jpg"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=9981)
    ap.add_argument("--work")
    ap.add_argument("--no-chrome", action="store_true", help="everything but the page in a browser")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        skip("the pretend photos are drawn with the Mac's own sips: nothing to run on this computer")
        return 0
    if a.port in (8790, 8791, 8792, 8799) or a.port in getattr(chrome_drive, "NEVER_PORTS", ()):
        print("STOP: that port is the real Assistant's.")
        return 2
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-photo-words-", dir="/private/tmp")).resolve()
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
        s.fake(s.target, "Zoë's hill", 26)
        case("making the pretend kits started no job and wrote no photo words (this test's kit.py sheet runs ask for none)",
             not any((s.kit(k) / ".kit" / "photo-words.json").exists() or (s.kit(k) / ".kit" / "photo-words-job.json").exists() for k in (A, B, D)))
        check_rule(s)
        before = check_store(s)
        check_describe(s, before)
        s.start()
        case("the page server is this test's own, on a scratch port and a scratch home", s.port not in (8790, 8791, 8792, 8799) and str(s.studio).startswith(str(work)))
        check_job(s)
        code, out = s.cmd("vault.py", "ensure", env=s.quiet)
        check_vault(s)
        s.fake(s.target, "Long day", 26)                # made now, so the vault's job above never looked at it
        check_pc(s)
        browser = None if a.no_chrome else chrome_drive.find_chrome()
        if browser:
            with chrome_drive.Chrome(work=str(work), size=(1280, 1000)) as c:
                check_browser(c, s)
        else:
            skip("the post kit page in a browser: " + ("not asked for" if a.no_chrome else "no Chrome on this computer"))
        check_real(s)
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
