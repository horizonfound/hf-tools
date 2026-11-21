#!/usr/bin/env python3
"""The vault's review fixes (Nov 19): what touches files and records on a drive, each finding with its check.

    python3 tests/vault_safety_check.py [--work <a folder under /private/tmp to keep the run in>]

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME and HOME; never
the real ~/.studio, no drive, no port, no page server, no window: STUDIO_NO_WINDOWS_FOR_TESTS).

  * "can't read it" is never "it is empty": with the vault's vault.json unreadable, relist and Remove from my
    vault stop and write nothing; with it damaged, empty or gone, every photo keeps its number (put back from the
    list beside it), what was taken out stays out, and the damaged file is kept;
  * the vault's own record unreadable: no "My vault 2" is made and nothing is copied;
  * the same for each shoot's photo words: an unreadable store stops the save; a damaged one is kept aside and
    the save starts from the version before;
  * + Add a shoot: one file that can't be read is named and left and never stops the others; a copy that did not
    read back as its original is not left among the photos, is not listed, and the next add copies it right; a
    photo saved over between the look and the copy is reported as in the vault (it is); a photo the vault
    already has from a shoot's post kit is not copied a second time (the export folder a kit was made from, and
    the folder above a kit's own export folder);
  * a post kit's folder renamed by hand: its photos keep their vault numbers, what was taken out stays out and
    Put it back works;
  * the strip counts the clips See everything in it lists, never video files; the My vault card does not count
    what was taken out; a relist keeps vault.prev.json; "being copied right now" is exit 2, not 4.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED. Python 3.9, standard library only. A Mac
(the pretend photos are drawn with the Mac's own sips); anywhere else it says SKIP and exits 0.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"

A, B = "2026-11-01 Fake beach", "2026-11-01 Other farm"
FAILED = []
COUNT = [0]


def case(name, ok, detail=None):
    COUNT[0] += 1
    if ok:
        print("PASS  " + name, flush=True)
    else:
        FAILED.append(name)
        print("FAIL  " + name + ("   " + repr(detail)[:700] if detail is not None else ""), flush=True)


def skip(name):
    print("SKIP  " + name, flush=True)


def group(name):
    print("\n== " + name, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    out = {}
    folder = Path(folder)
    for root, _dirs, files in os.walk(folder):
        for f in files:
            p = Path(root) / f
            try:
                out[p.relative_to(folder).as_posix()] = sha(p)
            except OSError:
                out[p.relative_to(folder).as_posix()] = "unread"
    return out


class World:
    def __init__(self, work):
        self.work = Path(work)
        self.target = self.work / "one"
        self.content = self.target / "The Assistant" / "Your Content"
        self.env = dict(os.environ, STUDIO_HOME=str(self.target / "studio"), STUDIO_NO_WINDOWS_FOR_TESTS="1",
                        ASSISTANT_TEST_OPEN="front", ASSISTANT_TEST_CAPCUT="1", HOME=str(self.work / "home"))
        self.env.pop("STUDIO_VAULT_ADD_STOP_FOR_TESTS", None)

    def fake(self, name, photos, photos_from=None):
        args = [sys.executable, str(HERE / "fake_kit.py"), str(self.target), "--name", name]
        args += ["--photos-from", str(photos_from)] if photos_from else ["--photos", str(photos)]
        r = subprocess.run(args, capture_output=True, text=True, env=self.env)
        if r.returncode != 0:
            raise RuntimeError("fake_kit: " + (r.stdout + r.stderr)[-400:])

    def cmd(self, script, *args):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, env=self.env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def pic(self, tag):
        """A pretend finished photo of the test's own: one of the pretend kit's JPEGs with a few bytes after its
        end, so every tag is a different file that still opens as a picture."""
        base = sorted((self.content / B / "Photos").glob("beach-00*.jpg"))[0]
        return base.read_bytes() + b"|" + str(tag).encode()

    def folder(self, name, photos):
        d = self.work / "picked" / name
        for rel, data in photos.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        return d


def rows(v):
    return json.loads((v / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]


def keyed(v):
    """{(kit, src or file name): n}: which photo each number means."""
    return {(x["kit"], x["src"] if x["kit"] else Path(x["file"]).name): x["n"] for x in rows(v)}


def unreadable(p):
    """Make a file unreadable for a moment (the test's own scratch file). False when this user reads it anyway."""
    os.chmod(p, 0)
    try:
        Path(p).read_bytes()
    except OSError:
        return True
    os.chmod(p, 0o644)
    return False


# ---------- the vault's numbers ----------

def check_numbers(w, vault, v):
    group("the vault's numbers: can't read it is never it is empty")
    hid = v / ".kit"
    case("a relist that wrote the numbers kept the version before (vault.prev.json), before anything was taken out",
         (hid / "vault.prev.json").is_file(), sorted(os.listdir(hid)))
    extra = w.folder("Own two", {"own-1.jpg": w.pic("own1"), "own-2.jpg": w.pic("own2")})
    res = vault.add(v, extra)
    case("(two photos added to the vault itself)", res["ok"] and res["copied"] == 2, res)
    n_own = next(x["n"] for x in rows(v) if Path(x["file"]).name == "own-2.jpg")
    vault.in_or_out(v, "photo", 3, False)
    vault.in_or_out(v, "photo", n_own, False)
    vault.relist(v, quick=True)
    good = keyed(v)
    good_sheet, good_state = (hid / "sheet.json").read_bytes(), (hid / "vault.json").read_bytes()
    out_before = vault.out(v)["photos"]
    case("(two photos are out of the vault, and off its list)", len(out_before) == 2 and 3 not in good.values() and n_own not in good.values(), out_before)

    if unreadable(hid / "vault.json"):
        try:
            got = None
            try:
                vault.relist(v, quick=True)
            except vault.Trouble as t:
                got = str(t)
            case("vault.json unreadable: relist stops in plain words", got is not None and "can't read" in got and "/" not in got, got)
            got = None
            try:
                vault.set_out(v, "photos", "own:own-1.jpg", True)
            except vault.Trouble as t:
                got = str(t)
            case("vault.json unreadable: Remove from my vault stops in plain words", got is not None and "can't read" in got, got)
            code, out = w.cmd("vault.py", "relist")
            case("vault.json unreadable: `vault.py relist` says STOP (exit 2) and never \"keeps its number\" over new numbers",
                 code == 2 and "STOP" in out and "keeps its number" not in out, (code, out[-300:]))
        finally:
            os.chmod(hid / "vault.json", 0o644)
        case("... and nothing was written: the list and the numbers are byte for byte what they were",
             (hid / "sheet.json").read_bytes() == good_sheet and (hid / "vault.json").read_bytes() == good_state)
    else:
        skip("vault.json unreadable (this user can read a file with no permissions)")

    for what, damage in (("empty", b""), ("damaged", b'{"numbers": {"2026'), ("not a record", b"[1, 2, 3]")):
        (hid / "vault.json").write_bytes(damage)
        res = vault.relist(v, quick=True)
        now = keyed(v)
        case(f"vault.json {what}: every photo keeps its number", now == good, sorted(set(now.items()) ^ set(good.items()))[:8])
        case(f"vault.json {what}: what was taken out is still out", vault.out(v)["photos"].keys() == out_before.keys(), vault.out(v)["photos"])
        case(f"vault.json {what}: the relist says the numbers were put back", res.get("recovered") is True, res)
        kept = [p for p in hid.glob("vault.damaged-*.json") if p.read_bytes() == damage]
        case(f"vault.json {what}: the damaged file is kept beside it", len(kept) >= 1, sorted(os.listdir(hid)))
    state = json.loads((hid / "vault.json").read_text(encoding="utf-8"))
    case("... and the next number to give is past every number ever given", state["next"] > max(state["numbers"].values()), state["next"])
    os.rename(hid / "vault.json", hid / "vault.json.the-test-moved-it")       # the test's own scratch file: gone
    vault.relist(v, quick=True)
    case("vault.json gone: every photo keeps its number", keyed(v) == good, sorted(set(keyed(v).items()) ^ set(good.items()))[:8])
    # a photo added now gets a number nobody ever had
    more = w.folder("Own third", {"own-3.jpg": w.pic("own3")})
    vault.add(v, more)
    n3 = next(x["n"] for x in rows(v) if Path(x["file"]).name == "own-3.jpg")
    case("a photo added after all that gets a number no photo ever had", n3 > max(list(good.values()) + [3, n_own]), n3)
    vault.in_or_out(v, "photo", n_own, True)
    vault.relist(v, quick=True)
    case("Put it back still gives the photo the number it had", any(x["n"] == n_own and Path(x["file"]).name == "own-2.jpg" for x in rows(v)))


# ---------- the vault's own record ----------

def check_record(w, vault, v):
    group("the vault's own record unreadable: never a second vault")
    rec = v / ".kit" / "kit.json"
    src = w.folder("While unread", {"lost-1.jpg": w.pic("lost1")})
    if not unreadable(rec):
        skip("kit.json unreadable (this user can read a file with no permissions)")
        return
    try:
        got = None
        try:
            vault.ensure()
        except vault.Trouble as t:
            got = str(t)
        case("ensure stops in plain words", got is not None and "can't read" in got and "/" not in got, got)
        code, out = w.cmd("vault.py", "add", str(src))
        case("`vault.py add` says STOP (exit 2) and copies nothing", code == 2 and "STOP" in out and "Copied" not in out, (code, out[-300:]))
    finally:
        os.chmod(rec, 0o644)
    names = sorted(os.listdir(w.content))
    case("no \"My vault 2\" was made", not any(n.startswith("My vault ") for n in names), names)
    case("the photo is in no folder of the Assistant's", not list((w.target / "The Assistant").rglob("lost-1.jpg")))
    case("the vault is still the vault once its record reads again", vault.find() == v, vault.find())


# ---------- + Add a shoot ----------

def check_unread(w, vault, v):
    photos_dir = v / "Photos"
    group("+ Add a shoot: one file that can't be read never stops the others")
    src = w.folder("Some unread", {"ok-a.jpg": w.pic("oka"), "locked-b.jpg": w.pic("lockb"), "ok-c.jpg": w.pic("okc")})
    os.symlink(src / "nowhere.jpg", src / "alias-d.jpg")           # a broken alias
    can = unreadable(src / "locked-b.jpg")
    try:
        res = vault.add(v, src)
        code, out = w.cmd("vault.py", "add", str(src))
    finally:
        os.chmod(src / "locked-b.jpg", 0o644)
    want_unread = {"alias-d.jpg"} | ({"locked-b.jpg"} if can else set())
    case("the photos that can be read are copied", res["copied"] == 3 - (1 if can else 0) and (photos_dir / "ok-a.jpg").is_file() and (photos_dir / "ok-c.jpg").is_file(), res)
    case("the ones that can't are named, and the add is not called clean", set(res["unread"]) == want_unread and set(res["problems"]) == want_unread and res["ok"] is False, res)
    case("the words say so plainly, with no path and no Python error", "could not be read" in res["words"] and "/" not in res["words"] and "Error" not in res["words"], res["words"])
    case("run again from the chat: exit 1, the same file named, no \"running the same command again finishes it\"",
         code == 1 and "Not in the vault: alias-d.jpg" in out and "PermissionError" not in out and "finishes it" not in out, (code, out[-400:]))


def check_bad_copy(w, vault, v):
    import this_computer
    photos_dir, hid = v / "Photos", v / ".kit"
    group("+ Add a shoot: a copy that did not read back as its original")
    src = w.folder("Flaky drive", {"flaky.jpg": w.pic("flaky"), "fine.jpg": w.pic("fine")})
    before = tree(src)
    real, hit = this_computer.rename_new, []

    def bad(part, dst, *a, **k):
        ok = real(part, dst, *a, **k)
        if ok and Path(dst).name == "flaky.jpg" and Path(dst).parent == photos_dir and not hit:
            hit.append(1)                                           # the drive changes four bytes after the copy lands, once
            with open(dst, "r+b") as f:
                f.seek(100)
                f.write(b"\x00\x00\x00\x00")
        return ok
    this_computer.rename_new = bad
    try:
        res = vault.add(v, src)
    finally:
        this_computer.rename_new = real
    case("(the drive fault happened)", hit == [1])
    case("it is named as a problem, and the add is not called clean", res["problems"] == ["flaky.jpg"] and res["ok"] is False and res["copied"] == 1, res)
    case("the words say it is not in the vault", "did not match the original" in res["words"], res["words"])
    names = sorted(n for n in os.listdir(photos_dir) if "flaky" in n)
    case("no file of that photo is left among the vault's photos (and no \"flaky (2).jpg\")", names == [], names)
    aside = sorted(os.listdir(hid / "copies-set-aside")) if (hid / "copies-set-aside").is_dir() else []
    case("the bad copy is kept, set aside in the vault's hidden folder, not deleted", aside == ["flaky.jpg.studio-mismatch"], aside)
    vault.relist(v, quick=True)
    case("the bad copy is not on the vault's list", not [x for x in rows(v) if "flaky" in Path(x["file"]).name])
    res = vault.add(v, src)
    case("adding the same folder again copies it right, under its own name",
         res["ok"] and res["copied"] == 1 and (photos_dir / "flaky.jpg").is_file() and sha(photos_dir / "flaky.jpg") == before["flaky.jpg"], res)
    case("the originals were only read", tree(src) == before)


def check_resave(w, vault, v):
    import posts
    photos_dir, hid = v / "Photos", v / ".kit"
    group("+ Add a shoot: a photo saved over between the look and its copy")
    src = w.folder("Still exporting", {"resaved.jpg": w.pic("resave"), "steady.jpg": w.pic("steady")})
    real_copy = posts.copy_checked

    def resave(s, d, *a, **k):
        if Path(s).name == "resaved.jpg" and not Path(d).exists():
            with open(s, "ab") as f:                                # the export writes the file again
                f.write(b"|exported again")
        return real_copy(s, d, *a, **k)
    posts.copy_checked = resave
    try:
        res = vault.add(v, src)
    finally:
        posts.copy_checked = real_copy
    case("the copy matches the photo as it is now", (photos_dir / "resaved.jpg").is_file() and sha(photos_dir / "resaved.jpg") == sha(src / "resaved.jpg"))
    case("the add says it is in the vault, which it is (no \"not in your vault\")",
         res["ok"] and res["copied"] == 2 and res["problems"] == [] and "not in your vault" not in res["words"], res)
    log = json.loads((hid / "vault-adds.json").read_text(encoding="utf-8"))["adds"][-1]
    line = next(f for f in log["files"] if f["src"] == "resaved.jpg")
    case("the log holds the hash of the bytes that were copied", line["state"] == "copied" and line["sha256"] == sha(photos_dir / "resaved.jpg"), line)
    res = vault.add(v, src)
    case("a second add of that folder copies nothing", res["ok"] and res["copied"] == 0 and res["there"] == 2, res)


def check_twice(w, vault, v):
    photos_dir, hid = v / "Photos", v / ".kit"
    group("+ Add a shoot: a photo the vault already has from a shoot is not copied again")
    a_photos = w.content / A / "Photos"
    in_a = sorted(p for p in a_photos.iterdir() if p.suffix.lower() in (".jpg", ".png") and not p.name.startswith("."))
    src = w.folder("The export A was made from", dict({p.name: p.read_bytes() for p in in_a}, **{"new-one.jpg": w.pic("newone")}))
    own_before = set(os.listdir(photos_dir))
    res = vault.add(v, src)
    case(f"the export folder a post kit was made from: its {len(in_a)} photos count as already in, only the new one is copied",
         res["ok"] and res["copied"] == 1 and res["there"] == len(in_a), {k: res[k] for k in ("ok", "copied", "there", "problems")})
    case("... and none of them is in the vault's own Photos folder", set(os.listdir(photos_dir)) - own_before == {"new-one.jpg"}, sorted(set(os.listdir(photos_dir)) - own_before))
    case("... and the words say so", "Copied 1 finished photo into your vault" in res["words"] and "already in your vault" in res["words"], res["words"])
    log = json.loads((hid / "vault-adds.json").read_text(encoding="utf-8"))["adds"][-1]
    case("the log names a post kit that holds each one (the pretend kits are drawn alike), and no copy's name", all(f.get("in") in (A, B) and f.get("dst") is None for f in log["files"] if f["src"] != "new-one.jpg"), log["files"][:2])
    changed = w.folder("Same name other picture", {in_a[0].name: w.pic("other picture")})
    res = vault.add(v, changed)
    case("the same name with another picture is still copied (it is another photo)", res["ok"] and res["copied"] == 1, res)

    exports = w.work / "exports" / "Final"
    w.folder("../exports/Final/Jones", {"j1.jpg": w.pic("j1"), "j2.jpg": w.pic("j2"), "web/j3.jpg": w.pic("j3")})
    (exports / "loose.jpg").write_bytes(w.pic("loose"))
    w.fake("Jones", 0, photos_from=exports / "Jones")
    jones = next(d for d in w.content.iterdir() if d.name.endswith("Jones"))
    listed = {Path(x["file"]).name for x in json.loads((jones / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]}
    vault.relist(v, quick=True)
    own_before = set(os.listdir(photos_dir))
    res = vault.add(v, exports)
    not_listed = {"j1.jpg", "j2.jpg", "j3.jpg"} - listed
    case("the folder above a post kit's own export folder: the kit's photos are not copied a second time",
         res["ok"] and set(os.listdir(photos_dir)) - own_before == {"loose.jpg"} | not_listed and res["there"] == len(listed),
         (sorted(set(os.listdir(photos_dir)) - own_before), res["there"], sorted(listed)))


# ---------- the counts ----------

def check_counts(w, vault, v):
    import vault_page
    group("the strip, the card, and the busy exit")
    (w.content / A / "Footage").mkdir(exist_ok=True)
    (w.content / A / "Footage" / "raw-take.mp4").write_bytes(b"not a clip: a video file" + b"\0" * 500)
    (v / "Footage" / "mine.MOV").write_bytes(b"not a clip either" + b"\0" * 500)
    facts = vault_page.strip_facts(v)
    listed = len(vault_page.every_data(v)["clips"])
    case("the strip counts the clips See everything in it lists, not video files", facts["clips"] == listed == 0, (facts["clips"], listed))
    case("... and says so (\"0 clips\")", "0 clips" in vault_page.strip_html(v), None)
    vault.relist(v, quick=True)
    ns = [x["n"] for x in rows(v)][:2]
    for n in ns:
        vault.in_or_out(v, "photo", n, False)                       # (no relist: the list is behind, as after a press)
    card, strip = vault_page.card_facts()["photos"], vault_page.strip_facts(v)["photos"]
    case("right after Remove from my vault the My vault card and the strip count the same photos", card == strip, (card, strip))
    for n in ns:
        vault.in_or_out(v, "photo", n, True)
    vault.relist(v, quick=True)
    import kit as kit_mod
    src = w.folder("While busy", {"busy-1.jpg": w.pic("busy1")})
    with kit_mod._held(v / ".kit" / "vault-add.lock", 2.0) as got:
        if got == "held":
            code, out = w.cmd("vault.py", "add", str(src))
            case("another copy running: \"being copied right now\", exit 2 (4 means not a folder to add)",
                 code == 2 and "being copied into your vault right now" in out and not (v / "Photos" / "busy-1.jpg").exists(), (code, out[-300:]))
        else:
            skip("another copy running (this drive has no locks)")


# ---------- the photo words ----------

def check_words(w, vault, v):
    import photo_words
    group("photo words: a save never starts from a file it could not read")
    kit = w.content / B
    store = kit / ".kit" / "photo-words.json"

    def put(n, text):
        def change(photos):
            photos[str(n)] = {"key": f"k{n}", "words": text, "words_by": "assistant", "words_at": "2026-11-19T10:00:00", "words_key": f"k{n}"}
        return photo_words.update(kit, change)
    put(1, "a dog on the sand")
    put(2, "two kids running")
    put(3, "a kite")
    case("(three descriptions saved, the version before kept)", sorted(photo_words.read(kit)) == ["1", "2", "3"] and store.with_name("photo-words.prev.json").is_file())
    good = store.read_bytes()
    if unreadable(store):
        try:
            got = None
            try:
                put(4, "a wave")
            except OSError as e:
                got = e
            case("the store unreadable: the save stops (the caller says nothing was saved)", got is not None, got)
            code, lines = photo_words.describe(kit, _words_file(w, {"4": {"words": "a wave"}}))
            case("... and `describe` says STOP, nothing was saved (never \"Saved 1 description\")",
                 code == 2 and "Nothing was saved" in " ".join(lines) and "Saved 1" not in " ".join(lines), (code, lines))
        finally:
            os.chmod(store, 0o644)
        case("... and the three descriptions are byte for byte what they were", store.read_bytes() == good)
    else:
        skip("the store unreadable (this user can read a file with no permissions)")
    prev_good = store.with_name("photo-words.prev.json").read_bytes()
    bad = b'{"v": 1, "photos": {"1": {"key"'
    store.write_bytes(bad)
    put(4, "a wave")
    now = photo_words.read(kit)
    case("the store damaged: the save starts from the version before, not from nothing", sorted(now) == ["1", "2", "4"], sorted(now))
    kept = [p for p in store.parent.glob("photo-words.damaged-*.json") if p.read_bytes() == bad]
    case("the damaged file is kept beside it under a dated name", len(kept) == 1, sorted(os.listdir(store.parent)))
    case("the version before was not replaced by the damaged bytes", store.with_name("photo-words.prev.json").read_bytes() == prev_good)


def _words_file(w, words):
    p = w.work / "words-4.json"
    p.write_text(json.dumps({"photos": words}), encoding="utf-8")
    return p


# ---------- a post kit's folder renamed by hand ----------

def check_rename(w, vault, v):
    group("a post kit's folder renamed by hand: its photos keep their vault numbers")
    vault.relist(v, quick=True)
    before = keyed(v)
    of_a = {src: n for (k, src), n in before.items() if k == A}
    out_n = sorted(of_a.values())[1]
    vault.in_or_out(v, "photo", out_n, False)
    vault.set_out(v, "clips", vault.clip_out_key(A, "m1-abcdef"), True)
    vault.relist(v, quick=True)
    before = keyed(v)
    of_a = {src: n for (k, src), n in before.items() if k == A}
    b_tree = tree(w.content / B)
    new = "2026-11-01 Renamed by hand"
    os.rename(w.content / A, w.content / new)                       # the photographer's own rename, in Finder
    a_tree = tree(w.content / new)
    res = vault.relist(v, quick=True)
    after = keyed(v)
    of_new = {src: n for (k, src), n in after.items() if k == new}
    case("every photo of that shoot has the number it had", of_new == of_a and of_a, sorted(set(of_new.items()) ^ set(of_a.items()))[:8])
    case("no photo of any other shoot moved", {k: n for k, n in after.items() if k[0] != new} == {k: n for k, n in before.items() if k[0] != A})
    case("no row is left under the old name", not [k for k in after if k[0] == A])
    case("the relist says which kit was followed", res.get("renamed") == {A: new}, res.get("renamed"))
    case("the photo that was taken out is still out, and did not come back under a new number",
         out_n not in after.values() and len(after) == len(before), (len(after), len(before)))
    outs = vault.out_list(v)
    case("the Taken out fold lists it under the kit's name today", any(o["what"] == "photo" and o["id"] == out_n and o["kit"] == new for o in outs), outs)
    case("a clip taken out follows the new name too", vault.clip_out_key(new, "m1-abcdef") in vault.out(v)["clips"], vault.out(v)["clips"])
    res = vault.in_or_out(v, "photo", out_n, True)
    vault.relist(v, quick=True)
    back = [x for x in rows(v) if x["n"] == out_n]
    case("Put it back puts it back, with the number it had", res["changed"] and len(back) == 1 and back[0]["kit"] == new, back)
    case("the vault wrote nothing into the renamed kit or any other", tree(w.content / new) == a_tree and tree(w.content / B) == b_tree)
    again = vault.relist(v, quick=True)
    case("a second relist changes nothing", again["same"] and not again.get("renamed"), again)
    # a kit that was COPIED (two folders say they were the same one) is not followed: neither takes the other's numbers
    shutil.copytree(w.content / B, w.content / "2026-11-01 Copy of farm one")
    shutil.copytree(w.content / B, w.content / "2026-11-01 Copy of farm two")
    before = keyed(v)
    vault.relist(v, quick=True)
    after = keyed(v)
    case("two copies of a kit's folder: the kit itself keeps every number", {k: n for k, n in after.items() if k[0] == B} == {k: n for k, n in before.items() if k[0] == B})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work")
    ap.add_argument("--only", help="parts, by name with commas: numbers,record,unread,bad_copy,resave,twice,counts,words,rename")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the pretend photos are drawn with the Mac's own sips: nothing to run on this computer")
        return 0
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-safety-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    work.mkdir(parents=True, exist_ok=True)
    (work / "home").mkdir(exist_ok=True)
    w = World(work)
    try:
        w.fake("Fake beach", 8)
        w.fake("Other farm", 9)
        os.environ.update({k: w.env[k] for k in ("STUDIO_HOME", "STUDIO_NO_WINDOWS_FOR_TESTS", "ASSISTANT_TEST_OPEN", "ASSISTANT_TEST_CAPCUT", "HOME")})
        os.environ.pop("STUDIO_VAULT_ADD_STOP_FOR_TESTS", None)
        sys.path.insert(0, str(SCRIPTS))
        import vault                                                # after the scratch STUDIO_HOME is set: it reads it once
        v, made = vault.ensure()
        vault.relist(v, quick=True)
        case("(the pretend vault is made over two pretend post kits)", made and len(rows(v)) > 10, len(rows(v)))
        for check in (check_numbers, check_record, check_unread, check_bad_copy, check_resave, check_twice,
                      check_counts, check_words, check_rename):
            if a.only and check.__name__[6:] not in a.only.split(","):
                continue
            try:
                check(w, vault, v)
            except Exception as e:  # noqa: BLE001  (one part falling over is that part's FAIL; the others still run)
                case(f"{check.__name__} ran to its end", False, f"{e.__class__.__name__}: {e}")
    finally:
        for root, dirs, files in os.walk(work):                     # so the scratch folder can be cleared
            for f in files:
                try:
                    if not os.path.islink(os.path.join(root, f)):
                        os.chmod(os.path.join(root, f), 0o644)
                except OSError:
                    pass
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)                 # this run's own scratch folder, made a moment ago
    print(f"\n{COUNT[0] - len(FAILED)} of {COUNT[0]} passed" + (f"; FAILED: {len(FAILED)}" if FAILED else ""))
    for f in FAILED:
        print("  FAILED: " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
