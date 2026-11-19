#!/usr/bin/env python3
"""The vault (Nicole's v29, 1.3) as a real post kit whose photo list is references: stage 6, vault-core.

    python3 tests/vault_core_check.py [--port 9967] [--work <a folder under /private/tmp to keep the run in>]

On pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME; nothing of a
client's, never the real ~/.studio, no drive, no CapCut, no window). Two of the kits hold photos with the very
same file names (beach-001.jpg and so on), which is the point: in the vault they are two photos, two numbers.

  * `vault.py show` never makes the vault; `ensure` twice, and twice at the same moment, makes one; a shoot
    already called "My vault" leaves the vault as "My vault 2", found by its mark;
  * the list references both kits, nothing is copied, same-named photos are two rows with two numbers;
  * numbers stay when a kit gains a photo, loses one, gets it back, when a third kit is made, when a kit's photos
    can't be reached, and when a photo is taken out of the vault and put back;
  * EVERY OTHER POST KIT IS BYTE FOR BYTE UNCHANGED after every vault command and every page request (each
    kit's whole folder is hashed before and after);
  * the readers: arrange.photo_path, the reel script's kit_numbers, kit.py picks and build (slides land in the
    vault's own Carousel folder, made from the member photos), the record keys that tell same-named photos apart;
  * the vault is not a shoot: absent from posts.kits, home_base.kits, the home page, the Make posts screen and
    the recap's shoots, while a reel made in it still counts in the recap; its "who" reads whole;
  * through the page server (a scratch port, no windows): /kit-photo serves the right photo for each same-named
    one, the picker's and the designer's state list the vault's photos, the first carousel design is blank, a
    photo dropped into the vault's own Photos folder joins the list by itself, and a Just photos test make gets
    each picked photo's own path.

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
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"

A, B, C = "2026-11-01 Fake beach", "2026-11-01 Other farm", "2026-11-01 Third hill"
FAILED = []
COUNT = [0]


def case(name, ok, detail=None):
    COUNT[0] += 1
    if ok:
        print("PASS  " + name, flush=True)
    else:
        FAILED.append(name)
        print("FAIL  " + name + ("   " + repr(detail)[:700] if detail is not None else ""), flush=True)


def group(name):
    print("\n== " + name, flush=True)


def tree(folder):
    """Every file under a folder (hidden ones too) with its hash, and every folder: what "byte for byte" means."""
    out = {}
    folder = Path(folder)
    for root, dirs, files in os.walk(folder):
        rp = Path(root)
        for d in dirs:
            out[(rp / d).relative_to(folder).as_posix() + "/"] = "dir"
        for f in files:
            p = rp / f
            out[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class Run:
    def __init__(self, work, port):
        self.work = Path(work)
        self.target = self.work / "one"
        self.studio = self.target / "studio"
        self.content = self.target / "The Assistant" / "Your Content"
        self.env = dict(os.environ, STUDIO_HOME=str(self.studio), STUDIO_NO_WINDOWS_FOR_TESTS="1",
                        ASSISTANT_TEST_OPEN="front", ASSISTANT_TEST_CAPCUT="1", HOME=str(self.work / "home"))
        self.want, self.port, self.proc = port, None, None
        self.before = {}

    def fake(self, target, name, photos):
        r = subprocess.run([sys.executable, str(HERE / "fake_kit.py"), str(target), "--photos", str(photos), "--name", name],
                           capture_output=True, text=True, env=self.env)
        if r.returncode != 0:
            raise RuntimeError("fake_kit: " + (r.stdout + r.stderr)[-400:])

    def own_picture(self, kit, other):
        """The pretend kits are all drawn alike, so every beach-001.jpg would be the same picture. Part of making
        the pretend kit (before anything is hashed): this kit's beach-001.jpg gets another of its own pictures, and
        the kit's own command lists it again, so the same name is truly a different photo in each kit."""
        shutil.copyfile(self.content / kit / "Photos" / other, self.content / kit / "Photos" / "beach-001.jpg")
        code, out = self.cmd("kit.py", "sheet", str(self.content / kit))
        if code != 0:
            raise RuntimeError("kit.py sheet: " + out[-300:])

    def cmd(self, script, *args, env=None):
        r = subprocess.run([sys.executable, str(script if isinstance(script, Path) else SCRIPTS / script), *args],
                           capture_output=True, text=True, env=env or self.env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def vault(self):
        for d in sorted(self.content.iterdir()):
            try:
                if json.loads((d / ".kit" / "kit.json").read_text()).get("vault") is True:
                    return d
            except (OSError, ValueError):
                pass
        return None

    def sheet(self):
        return json.loads((self.vault() / ".kit" / "sheet.json").read_text())

    def rows(self):
        return self.sheet()["photos"]

    def n_of(self, kit, name):
        return next((x["n"] for x in self.rows() if x["kit"] == kit and Path(x["file"]).name == name), None)

    # ---- the members, hashed
    def members(self):
        return [d for d in sorted(self.content.iterdir()) if d.is_dir() and d != self.vault()]

    def note(self):
        """Remember every other kit as it is now (after something of the TEST's own changed one)."""
        self.before = {d.name: tree(d) for d in self.members()}

    def untouched(self, what):
        now = {d.name: tree(d) for d in self.members()}
        diff = sorted(k for k in set(now) | set(self.before) if now.get(k) != self.before.get(k))
        inner = []
        for k in diff:
            a, b = self.before.get(k) or {}, now.get(k) or {}
            inner += [k + ": " + f for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)][:6]
        case("every other post kit is byte for byte unchanged after " + what, not diff, inner)

    # ---- the page server
    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(self.want)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env)
        line = self.proc.stdout.readline()
        m = re.search(r"127\.0\.0\.1:(\d+)/", line)
        if not m:
            raise RuntimeError("the page server did not start (%r)" % line)
        self.port = int(m.group(1))
        end = time.time() + 10
        while time.time() < end:
            try:
                socket.create_connection(("127.0.0.1", self.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.1)
        threading.Thread(target=lambda: [None for _ in self.proc.stdout], daemon=True).start()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def http(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
            h["Origin"] = "http://127.0.0.1:%d" % self.port
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            j = json.loads(raw.decode())
        except ValueError:
            j = None
        return r.status, j, raw


def check_commands(s):
    group("making the vault")
    s.note()
    code, out = s.cmd("vault.py", "show")
    case("show, with no vault: says so and makes nothing", code == 3 and "NO VAULT" in out and s.vault() is None
         and sorted(d.name for d in s.content.iterdir()) == [A, B], (code, out))
    # twice at the same moment
    ps = [subprocess.Popen([sys.executable, str(SCRIPTS / "vault.py"), "ensure"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, env=s.env) for _ in range(2)]
    outs = [p.communicate()[0] for p in ps]
    marked = [d.name for d in s.content.iterdir() if (d / ".kit" / "kit.json").is_file()
              and json.loads((d / ".kit" / "kit.json").read_text()).get("vault") is True]
    case("ensure, twice at the same moment, makes one vault", marked == ["My vault"] and all(p.returncode == 0 for p in ps)
         and sum("Made the vault" in o for o in outs) == 1, (marked, outs))
    code, out = s.cmd("vault.py", "ensure")
    case("ensure again: already there, and nothing is written", code == 0 and "already there" in out and "Nothing was written" in out, out)
    v = s.vault()
    rec = json.loads((v / ".kit" / "kit.json").read_text())
    case("its record: name My vault, the mark, and its own folders like any kit",
         rec.get("name") == "My vault" and rec.get("vault") is True and all((v / f).is_dir() for f in ("Photos", "Footage", "Music", "Carousel", "Stories", "Reels")), rec)
    s.untouched("show and ensure")

    group("the list is references")
    sh = s.sheet()
    rows = sh["photos"]
    case("the list is marked as the vault's, and holds every photo of both kits (8 + 9)", sh.get("vault") is True and len(rows) == 17, len(rows))
    case("every row names its post kit and that kit's own number", all(x["kit"] in (A, B) and type(x["src"]) is int for x in rows)
         and sorted((x["kit"], x["src"]) for x in rows) == sorted([(A, i) for i in range(1, 9)] + [(B, i) for i in range(1, 10)]))
    case("numbers are 1 to 17, each once", sorted(x["n"] for x in rows) == list(range(1, 18)))
    a1, b1 = s.n_of(A, "beach-001.jpg"), s.n_of(B, "beach-001.jpg")
    case("the two photos called beach-001.jpg are two rows with two numbers", a1 and b1 and a1 != b1, (a1, b1))
    case("no photo was copied: the vault's own Photos folder is empty", not [p for p in (v / "Photos").iterdir() if not p.name.startswith(".")])
    case("each row's file is in its own kit's Photos folder", all(Path(x["file"]).parent == s.content / x["kit"] / "Photos" and Path(x["file"]).is_file() for x in rows))
    code, out = s.cmd("vault.py", "members")
    case("members lists both shoots with their photo counts", code == 0 and A in out and B in out and "8 photos" in out and "9 photos" in out and "My vault" not in out, out)
    code, out = s.cmd("vault.py", "relist", "--sheets")
    sheets = re.findall(r"Sheet: (.+)", out)
    case("relist --sheets draws the numbered sheets inside the vault's own hidden folder", code == 0 and sheets
         and all(Path(p).is_file() and v / ".kit" in Path(p).parents for p in sheets), out)
    s.untouched("members and relist --sheets")
    return {x["n"]: (x["kit"], x["src"], Path(x["file"]).name) for x in rows}


def same_numbers(s, first, what):
    now = {x["n"]: (x["kit"], x["src"], Path(x["file"]).name) for x in s.rows()}
    wrong = {n: (first[n], now.get(n)) for n in first if n in now and now[n] != first[n]}
    case("no number means another photo after " + what, not wrong, wrong)
    return now


def check_numbers(s, first):
    group("numbers never move")
    v = s.vault()
    # a kit gains a photo (the kit's own command lists it; that is the kit changing itself, so it is noted afresh)
    shutil.copyfile(s.content / A / "Photos" / "beach-002.jpg", s.content / A / "Photos" / "zz-new.jpg")
    code, out = s.cmd("kit.py", "sheet", str(s.content / A))
    s.note()
    code2, out2 = s.cmd("vault.py", "show")
    case("show says the list is behind when a kit has a new photo", "behind" in out2, out2)
    code, out = s.cmd("vault.py", "relist")
    now = same_numbers(s, first, "a kit gained a photo")
    new_n = s.n_of(A, "zz-new.jpg")
    case("the new photo takes the next number (18), and the list says added", new_n == 18 and s.sheet().get("added") == [18] and len(now) == 18, (new_n, s.sheet().get("added")))
    case("the list before is kept beside it", len(json.loads((v / ".kit" / "sheet.prev.json").read_text())["photos"]) == 17)
    s.untouched("a relist that added a photo")

    # a kit loses a photo
    away = s.work / "away"
    away.mkdir(exist_ok=True)
    b2 = s.n_of(B, "beach-002.jpg")
    a2 = s.n_of(A, "beach-002.jpg")
    shutil.move(str(s.content / B / "Photos" / "beach-002.jpg"), str(away / "beach-002.jpg"))
    s.cmd("kit.py", "sheet", str(s.content / B))
    s.note()
    s.cmd("vault.py", "relist")
    sh = s.sheet()
    same_numbers(s, first, "a kit lost a photo")
    case("the lost photo's number is gone and retired, never given away", sh.get("gone") == [b2] and b2 not in {x["n"] for x in sh["photos"]}
         and any(r["n"] == b2 and r["kit"] == B for r in sh["retired"]), (b2, sh.get("gone"), sh["retired"]))
    case("the other kit's photo of the same name is still there, with its number", s.n_of(A, "beach-002.jpg") == a2)
    s.untouched("a relist that retired a photo")

    # it comes back
    shutil.move(str(away / "beach-002.jpg"), str(s.content / B / "Photos" / "beach-002.jpg"))
    s.cmd("kit.py", "sheet", str(s.content / B))
    s.note()
    s.cmd("vault.py", "relist")
    sh = s.sheet()
    case("the photo that came back has its old number, and the list says back", s.n_of(B, "beach-002.jpg") == b2 and sh.get("back") == [b2] and not sh["retired"], (sh.get("back"), sh["retired"]))
    same_numbers(s, first, "the photo came back")
    s.untouched("a relist that brought a photo back")

    # a third kit
    s.fake(s.target, "Third hill", 8)
    s.own_picture(C, "beach-003.jpg")
    s.note()
    s.cmd("vault.py", "relist")
    now = same_numbers(s, first, "a third kit was made")
    third = sorted(n for n, (k, _, _) in now.items() if k == C)
    case("the third kit's photos take the next numbers (19 to 26)", third == list(range(19, 27)), third)
    c1 = s.n_of(C, "beach-001.jpg")
    case("three photos called beach-001.jpg now: three numbers", len({s.n_of(A, "beach-001.jpg"), s.n_of(B, "beach-001.jpg"), c1}) == 3)
    s.untouched("a relist that added a third kit")

    # a kit with no list of its own yet is not written into: it waits
    d = s.content / "2026-11-02 No list yet"
    (d / ".kit").mkdir(parents=True)
    (d / "Photos").mkdir()
    shutil.copyfile(s.content / A / "Photos" / "beach-001.jpg", d / "Photos" / "beach-001.jpg")
    (d / ".kit" / "kit.json").write_text(json.dumps({"name": "No list yet", "date": "2026-11-02", "folder": d.name}))
    s.note()
    code, out = s.cmd("vault.py", "relist")
    case("a kit with no numbered list of its own is named as not in yet, and nothing is written into it",
         "Not in yet" in out and d.name in out and not (d / ".kit" / "sheet.json").exists() and len(s.rows()) == 26, out)
    s.untouched("a relist beside a kit with no list")

    # a kit whose photos can't be reached keeps its rows (the test moves its Photos folder away and back)
    stamp = hashlib.sha1((v / ".kit" / "sheet.json").read_bytes()).hexdigest()
    os.rename(s.content / B / "Photos", s.content / B / "Photos away")
    code, out = s.cmd("vault.py", "relist")
    case("a kit whose photos can't be reached keeps every row and number; nothing is retired",
         hashlib.sha1((v / ".kit" / "sheet.json").read_bytes()).hexdigest() == stamp and "Nothing was written" in out, out)
    os.rename(s.content / B / "Photos away", s.content / B / "Photos")
    s.untouched("a relist while a kit's photos were away")
    return now


def check_modules(s, first):
    """The readers, asked in this process (STUDIO_HOME is this run's own, set before anything is imported)."""
    group("the readers")
    os.environ.update({k: s.env[k] for k in ("STUDIO_HOME", "STUDIO_NO_WINDOWS_FOR_TESTS", "ASSISTANT_TEST_OPEN", "ASSISTANT_TEST_CAPCUT", "HOME")})
    sys.path.insert(0, str(SCRIPTS))
    sys.path.append(str(REEL))
    import arrange
    import kit as kit_mod
    import posts
    import vault
    v = s.vault()
    case("find: the vault by its mark; is_vault only for it", vault.find() == v and vault.is_vault(v) and not vault.is_vault(s.content / A)
         and arrange.kit_by_name("My vault") == v)
    rec = kit_mod.load_rec(v)
    rows = {x["n"]: x for x in arrange.sheet_rows(v)}
    a1, b1 = s.n_of(A, "beach-001.jpg"), s.n_of(B, "beach-001.jpg")
    pa, pb = arrange.photo_path(v, rec, rows[a1]), arrange.photo_path(v, rec, rows[b1])
    case("photo_path finds each same-named photo in its own kit", pa == s.content / A / "Photos" / "beach-001.jpg" and pb == s.content / B / "Photos" / "beach-001.jpg", (pa, pb))
    case("a row that names the vault itself as its kit, or a path, finds nothing (one level only)",
         arrange.photo_path(v, rec, dict(rows[a1], kit=v.name)) is None and arrange.photo_path(v, rec, dict(rows[a1], kit="../" + A)) is None)
    case("the key a record keeps for a photo tells the same-named ones apart", arrange.photo_key(rows[a1]) != arrange.photo_key(rows[b1])
         and arrange.photo_name(rows[a1]) == arrange.photo_name(rows[b1]))
    plain = arrange.sheet_rows(s.content / A)[0]
    case("a plain kit's row is keyed by its file name, exactly as before", arrange.photo_key(plain) == arrange.photo_name(plain) and "kit" not in plain)
    import reel
    got = reel.kit_numbers(str(v), str(v / "Photos"))
    by = {x["n"]: x["file"] for x in got or []}
    case("the reel script's list gives each number its own photo's path", got and by[a1] == str(pa) and by[b1] == str(pb) and len(by) == len(rows), (by.get(a1), by.get(b1)))
    got_plain = reel.kit_numbers(str(s.content / A), str(s.content / A / "Photos"))
    case("a plain kit's list, through the reel script, is as before (every name in its one folder)",
         got_plain and all(Path(x["file"]).parent == s.content / A / "Photos" for x in got_plain))
    groups = vault.rows_by_group(v)
    case("rows_by_group: each post kit a group, newest first, every row in one", [g["kit"] for g in groups] == [C, B, A]
         and sum(len(g["rows"]) for g in groups) == len(rows), [g["kit"] for g in groups])

    group("the vault is not a shoot")
    h = posts.home()
    case("posts.kits leaves the vault out", "My vault" not in [k["folder"] for k in posts.kits(h)] and len(posts.kits(h)) == 4, [k["folder"] for k in posts.kits(h)])
    case("posts.kits(h, vault=True) has it, marked", [k.get("vault") for k in posts.kits(h, vault=True) if k["folder"] == "My vault"] == [True])
    import home_base
    case("home_base.kits (the Make posts list) leaves it out", "My vault" not in [k["folder"] for k in home_base.kits()])
    import home
    case("the vault's who reads whole", home.who("My vault") == "My vault" and vault.who("My vault") == "My vault" and vault.who("Katie Austin") is None
         and home.who("Katie Austin Maternity") == "Katie’s")
    import reminders
    import posting_queue
    piece = {"shoot_name": "My vault", "kind": "reel"}
    case("a reminder's title and the queue's piece name read My vault whole",
         reminders.title(piece) == "Post your My vault reel today" and posting_queue.piece_name(piece) == "My vault reel", (reminders.title(piece), posting_queue.piece_name(piece)))

    case("the queue's cover pick names a vault photo by its number, never by a name two shoots share",
         posting_queue.cover_file(v, "reel", "Photos/#%d" % b1, rec) == pb and posting_queue.cover_file(v, "reel", "Photos/#%d" % a1, rec) == pa
         and posting_queue.cover_file(v, "reel", "Photos/beach-001.jpg", rec) is None
         and posting_queue.cover_file(s.content / A, "reel", "Photos/beach-001.jpg") == pa
         and posting_queue.cover_file(s.content / A, "reel", "Photos/#1") is None)

    group("picks and slides in the vault")
    s.note()
    c1 = s.n_of(C, "beach-001.jpg")
    code, out = s.cmd("kit.py", "picks", "My vault", "--carousel", f"{a1},{b1},{c1}", "--reel", f"{a1},{b1},{c1}")
    case("kit.py picks takes vault numbers", code == 0, out)
    plan = kit_mod.carousel_plan(v)
    srcs = [str(plan["src"][n]) for n in plan.get("wanted", [])] if plan.get("ok") else []
    case("the carousel's plan reads each slide from its own kit's photo",
         srcs == [str(s.content / k / "Photos" / "beach-001.jpg") for k in (A, B, C)], srcs)
    # an own photo of the same name must never be taken for a member's
    shutil.copyfile(s.content / A / "Photos" / "beach-003.jpg", v / "Photos" / "beach-001.jpg")
    old = time.time() - 60
    os.utime(v / "Photos" / "beach-001.jpg", (old, old))
    plan = kit_mod.carousel_plan(v)
    case("a photo of the same name in the vault's own Photos folder is never taken for a kit's",
         plan.get("ok") and [str(plan["src"][n]) for n in plan["wanted"]] == srcs)
    code, out = s.cmd("kit.py", "build", "My vault")
    slides = sorted(p.name for p in (v / "Carousel").glob("*.jpg"))
    case("kit.py build writes three slides into the vault's own Carousel folder", code == 0 and len(slides) == 3
         and slides == [f"Slide {i:02d} (beach-001).jpg" for i in (1, 2, 3)], (code, out[-300:], slides))
    sizes = {(v / "Carousel" / n).stat().st_size for n in slides}
    case("the three slides are three different pictures (same name, three photos)", len({hashlib.sha256((v / "Carousel" / n).read_bytes()).hexdigest() for n in slides}) == 3, sizes)
    s.untouched("picks and build in the vault")

    group("taken out, and put back")
    key = vault.photo_out_key(rows[b1])
    case("set_out takes a photo out (only the vault's own record is written)", vault.set_out(v, "photos", key, True) is True and vault.set_out(v, "photos", key, True) is False)
    res = vault.relist(v, quick=True)
    case("the next list leaves it off, its number unused", b1 in res["gone"] and b1 not in {x["n"] for x in arrange.sheet_rows(v)} and vault.out(v)["photos"].get(key))
    vault.set_out(v, "photos", key, False)
    res = vault.relist(v, quick=True)
    case("put back: the same number again", b1 in res["back"] and s.n_of(B, "beach-001.jpg") == b1)
    own = next((x for x in arrange.sheet_rows(v) if x["kit"] == ""), None)
    case("the photo in the vault's own folder is on the list as its own (a fourth beach-001.jpg, a fourth number)",
         own and Path(own["file"]).name == "beach-001.jpg" and own["n"] not in (a1, b1, c1) and arrange.photo_path(v, rec, own) == v / "Photos" / "beach-001.jpg", own)
    case("rows_by_group puts what was added to the vault first", vault.rows_by_group(v)[0]["group"] == "added")
    same_numbers(s, first, "taking out and putting back")
    s.untouched("set_out and relist")

    group("the recap")
    import wrapped
    month = date.today().isoformat()[:7]
    before = wrapped.data(month=month)
    code, out = s.cmd("kit.py", "reel-made", "My vault", "--project", "My vault reel")
    after = wrapped.data(month=month)
    case("a reel made in the vault counts in the recap", code == 0 and after["totals"]["reels"] == before["totals"]["reels"] + 1, (out, before["totals"], after["totals"]))
    case("the vault is never one of the recap's shoots, nor its top shoot", "My vault" not in [x["name"] for x in after["shoots"]] and after["top"] != "My vault"
         and after["totals"]["shared_shoots"] == before["totals"]["shared_shoots"], (after["shoots"], after["top"]))
    return a1, b1, c1


def check_server(s, nums):
    group("through the page server")
    import arrange
    import kit as kit_mod
    a1, b1, c1 = nums
    v = s.vault()
    q = "kit=" + quote("My vault")
    s.note()
    made = arrange.make_previews(v)
    case("the vault makes its own small copies, in its own hidden folder", made["failed"] == 0 and made["missing"] == 0 and (v / ".kit" / "previews").is_dir(), made)
    s.untouched("making the vault's small copies")
    s.start()
    try:
        rec = kit_mod.load_rec(v)
        rows = {x["n"]: x for x in arrange.sheet_rows(v)}
        shas = {}
        for n, k in ((a1, A), (b1, B), (c1, C)):
            code, _, raw = s.http("GET", f"/kit-photo?{q}&n={n}&size=s")
            f = arrange.copy_to_serve(v, rec, rows[n], arrange.SIZES["s"])
            src = s.content / k / "Photos" / "beach-001.jpg"
            # a small copy's name carries its photo's own size and time: that is how it is tied to the right one
            right = f is not None and f.name == arrange.preview_file(v, rows[n], arrange.SIZES["s"], src).name
            case(f"/kit-photo serves photo {n}: the beach-001.jpg of {k}", code == 200 and right and raw == f.read_bytes(), (code, f))
            shas[n] = hashlib.sha256(raw).hexdigest()
        case("the three same-named photos are served as three different pictures", len(set(shas.values())) == 3)
        code, j, _ = s.http("GET", f"/arrange-state?{q}&page=carousel")
        case("the picker's state lists the vault's photos, with no path and no file name", code == 200 and j and len(j.get("photos") or []) == len(rows)
             and "beach-001" not in json.dumps(j) and "/private/" not in json.dumps(j), (code, str(j)[:300]))
        code, j, _ = s.http("GET", f"/design-state?{q}&kind=carousel")
        d = (j or {}).get("design") or {}
        blocks = ((d.get("state") or {}).get("blocks"))
        case("the designer's state lists the vault's photos", code == 200 and len(j.get("photos") or []) == len(rows), (code, str(j)[:300]))
        case("the vault's first carousel design is blank (nothing is picked until they ask)", blocks == [], d)
        code, j, _ = s.http("GET", f"/design-state?kit={quote(A)}&kind=carousel")
        blocks = (((j or {}).get("design") or {}).get("state") or {}).get("blocks")
        case("a plain kit's first design is still one photo a slide", code == 200 and blocks and all(b.get("n") for b in blocks), blocks)
        s.note()            # the designer's first look at kit A made A's own first design: A's own, not the vault's

        # a photo dropped into the vault's own Photos folder joins the list on the reel page's own look
        shutil.copyfile(s.content / A / "Photos" / "beach-004.heic", v / "Photos" / "dropped.heic") if (s.content / A / "Photos" / "beach-004.heic").is_file() \
            else shutil.copyfile(s.content / A / "Photos" / "beach-003.jpg", v / "Photos" / "dropped.jpg")
        name = "dropped.heic" if (v / "Photos" / "dropped.heic").is_file() else "dropped.jpg"
        old = time.time() - 60
        os.utime(v / "Photos" / name, (old, old))
        before = len(rows)
        code, j, _ = s.http("GET", f"/reel-state?{q}")
        now = arrange.sheet_rows(v)
        mine = next((x for x in now if x["kit"] == "" and Path(x["file"]).name == name), None)
        case("a photo dropped into the vault's own Photos folder joins the list by itself, with a new number",
             code == 200 and len(now) == before + 1 and mine and mine["n"] == max(x["n"] for x in now), (code, len(now), mine))
        code, j, _ = s.http("GET", f"/reel-state?{q}")
        case("the reel page's state lists every vault photo", code == 200 and len(j.get("photos") or []) == before + 1, (code, str(j)[:200]))

        # a Just photos test make: each picked photo's own path
        stamp = j["stamp"]
        body = {"kit": "My vault", "stamp": stamp, "picks": [{"n": n, "h": ""} for n in (a1, b1, c1, a1 + 1)], "song": "", "vibe": "beat", "test": True}
        code, j, _ = s.http("POST", "/reel-make", body)
        job = None
        if code == 200 and (j or {}).get("job"):
            end = time.time() + 120
            while time.time() < end:
                _, j2, _ = s.http("GET", f"/reel-job?{q}&id={j['job']['id']}")
                job = (j2 or {}).get("job")
                if job and job["state"] in ("done", "problem"):
                    break
                time.sleep(0.3)
        case("a test make of a Just photos reel in the vault finishes, nothing made", job and job["state"] == "done" and job.get("dry") is True and job.get("project") is None, (code, j, job))
        case("no path reaches the page from the make", job is not None and "/private/" not in json.dumps(job) and "Your Content" not in json.dumps(job), job)
        try:
            plan = json.loads((v / ".kit" / "reels" / "reel.json").read_text())["plan"]["photos"]
            paths = [p["path"] for p in plan]
        except (OSError, ValueError, KeyError):
            paths = []
        want = [str(s.content / k / "Photos" / "beach-001.jpg") for k in (A, B, C)] + [str(Path(rows[a1 + 1]["file"]))]
        case("the reel's plan holds each picked photo's own path, same-named ones from their own kits", paths == want, paths)

        time.sleep(1.5)     # let the page server's own background copies settle
        s.untouched("every page request made of the vault")

        group("the pages that list shoots")
        code, _, raw = s.http("GET", "/home")
        case("the home page never shows the vault as a shoot", code == 200 and b"My vault" not in raw, code)
        code, _, raw = s.http("GET", "/make-posts")
        case("the Make posts screen's list leaves the vault out (its own card is stage 7)", code == 200 and b"My vault" not in raw, code)
        code, j, _ = s.http("GET", "/home-data")
        case("/home-data's kits leave it out", code == 200 and "My vault" not in [k.get("folder") for k in (j or {}).get("kits") or []] and len(j["kits"]) == 4, (code, str(j)[:200]))
        code, _, raw = s.http("GET", "/content/" + quote("My vault") + "/" + quote("Post kit.html"))
        case("the vault's post kit page opens like any kit's", code == 200 and b"Carousel" in raw, (code, raw[:200]))
        # (the home page makes small copies inside the newest shoots' own kits, as it always has: that is those
        # kits' own page at work, not the vault, so nothing is compared after these)
    finally:
        s.stop()


def check_name_taken(s):
    group("a shoot already called My vault")
    two = Run(s.work / "second", s.want)
    two.target = s.work / "two"
    two.studio = two.target / "studio"
    two.content = two.target / "The Assistant" / "Your Content"
    two.env = dict(s.env, STUDIO_HOME=str(two.studio))
    two.fake(two.target, "Fake beach", 8)
    plain = two.content / "My vault"
    (plain / ".kit").mkdir(parents=True)
    (plain / ".kit" / "kit.json").write_text(json.dumps({"name": "My vault", "date": "2026-10-01", "folder": "My vault"}))
    before = tree(plain)
    code, out = two.cmd("vault.py", "ensure")
    v = two.vault()
    case("the vault takes My vault 2, and is found by its mark, never its name", code == 0 and v is not None and v.name == "My vault 2"
         and json.loads((v / ".kit" / "kit.json").read_text())["name"] == "My vault", (code, out))
    case("the shoot called My vault is untouched, and is a member like any other", tree(plain) == before and "My vault |" in two.cmd("vault.py", "members")[1])
    code, out = two.cmd("vault.py", "ensure")
    case("ensure again there: still one vault", code == 0 and "already there" in out
         and sorted(d.name for d in two.content.iterdir()) == ["2026-11-01 Fake beach", "My vault", "My vault 2"], out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=9967)
    ap.add_argument("--work")
    a = ap.parse_args()
    if not Path("/usr/bin/sips").exists():
        print("SKIP  the pretend photos are drawn with the Mac's own sips: nothing to run on this computer")
        return 0
    if a.port in (8790, 8791, 8792, 8799):
        print("STOP: that port is the real Assistant's.")
        return 2
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="hf-vault-core-", dir="/private/tmp"))
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp.")
        return 2
    work.mkdir(parents=True, exist_ok=True)
    (work / "home").mkdir(exist_ok=True)
    s = Run(work, a.port)
    try:
        s.fake(s.target, "Fake beach", 8)
        s.fake(s.target, "Other farm", 9)
        s.own_picture(B, "beach-002.jpg")
        first = check_commands(s)
        first = {**first, **check_numbers(s, first)}
        nums = check_modules(s, first)
        check_server(s, nums)
        check_name_taken(s)
    finally:
        s.stop()
        if not a.work:
            shutil.rmtree(work, ignore_errors=True)     # this run's own scratch folder, made a moment ago
    print(f"\n{COUNT[0] - len(FAILED)} of {COUNT[0]} passed" + (f"; FAILED: {len(FAILED)}" if FAILED else ""))
    for f in FAILED:
        print("  FAILED: " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
