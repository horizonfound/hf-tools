#!/usr/bin/env python3
"""The Trash helper (this_computer.trash; Nicole's v27, "Remove this song (two taps, to the Trash)"; Lane E's E11):
nothing of the photographer's is ever deleted, and the one door out is the computer's own Trash.

    python3 tests/trash_check.py [--work <scratch folder>]

No server, no browser, no video, nothing installed. Everything happens in a scratch folder this test makes, with
HOME pointed inside it and the tests' switch STUDIO_TRASH_FOR_TESTS pointed at a folder of its own, so the real
Trash (Recycle Bin) is never touched: not one file of anyone's moves anywhere but inside the scratch folder.
The real Finder and Windows routes are tried with a stand-in in their place that records what it was asked.

What it checks:
  1. the words: the Trash and Put Back on a Mac (Nicole's line), the Recycle Bin and Restore on a PC, never Claude;
  2. with the switch set, a file and a folder of files move whole into the test's trash folder, byte for byte, and
     are gone from where they were; a second and a third item of the same name get " 2" and " 3"; a name with a
     quote, an accent and an emoji works; a file in a folder under the one it is told works too;
  3. refused, and nothing moves: a path that is not there, a link (its target untouched), a path outside the
     folder it is told, that folder itself, a folder that is itself a link, a path with ".." in it, a relative
     path, a trailing slash;
  4. trash_many: every path is checked before the first move (one bad path and nothing moves), all good moves all
     in order, a path given twice counts once, and when the second item cannot be moved the answer names the one
     that moved (on a Mac the second sits in a folder made read-only; on a PC the second is held open);
  5. the real route, with a stand-in: inside a test that set no_windows() and no trash folder, trash() refuses and
     the real route is never asked; without any switch the Mac route asks Finder through osascript with the path
     as an argument (never pasted into the script) and calls it done only when Finder's answer says the item is in
     a .Trash folder and it is gone; a drive with no Trash is refused before anything runs; on a PC the same with
     the Recycle Bin call in place;
  6. the helper's own source names no os.remove, os.unlink, shutil.rmtree, os.rmdir, rm or send2trash;
  7. the hand-run entry, python3 this_computer.py trash <path>, through the switch.
Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED (the scratch folder is kept then).
"""
import argparse
import hashlib
import inspect
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:500]}]" if detail != "" and not ok else ""), flush=True)
    return bool(ok)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--work", help="a scratch folder for this run (made if missing); else a temporary one")
A = ap.parse_args()
if A.work:
    Path(A.work).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="trash ", dir=A.work))
else:
    work = Path(tempfile.mkdtemp(prefix="assistant trash "))
work = Path(os.path.realpath(work))
HOME = work / "home"
HOME.mkdir()
TRASH = work / "test trash"
os.environ["HOME"] = str(HOME)                    # never their ~/.Trash, never their ~/.studio
os.environ["USERPROFILE"] = str(HOME)
os.environ["STUDIO_HOME"] = str(work / "studio")
os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
os.environ["STUDIO_TRASH_FOR_TESTS"] = str(TRASH)
sys.path.insert(0, str(SCRIPTS))
import this_computer as tc  # noqa: E402

tc.utf8_output()
PC = tc.WINDOWS
print(f"This is a {tc.COMPUTER}, Python {sys.version.split()[0]}.\n", flush=True)


# ---------- helpers ----------

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    """Every file under a folder, as (relative path, hash), sorted; the folder's shape and bytes in one list."""
    out = []
    for dp, dn, fn in os.walk(folder):
        for f in fn:
            p = Path(dp) / f
            out.append((str(p.relative_to(folder)), sha(p)))
        for d in dn:
            out.append((str((Path(dp) / d).relative_to(folder)) + "/", ""))
    return sorted(out)


def listing(folder):
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def make_file(p, size=3000):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(os.urandom(size))
    return p


counter = [0]


def fresh(name="Music"):
    """A new 'inside' folder for one part, so parts never see each other's files."""
    counter[0] += 1
    d = work / f"shoot {counter[0]}" / name
    d.mkdir(parents=True)
    return d


# ---------- 1. the words ----------

def words():
    if PC:
        check("TRASH_WORD is the Recycle Bin on a PC", tc.TRASH_WORD == "the Recycle Bin")
        check("TRASH_BACK is ours for a PC: open the Recycle Bin in File Explorer and choose Restore",
              tc.TRASH_BACK == "open the Recycle Bin in File Explorer and choose Restore")
    else:
        check("TRASH_WORD is the Trash on a Mac", tc.TRASH_WORD == "the Trash")
        check("TRASH_BACK is Nicole's line on a Mac: open the Trash in Finder and choose Put Back",
              tc.TRASH_BACK == "open the Trash in Finder and choose Put Back")
    all_words = [tc.CANT_TRASH, tc.TRASH_GONE, tc.TRASH_LINK, tc.TRASH_OUTSIDE, tc.TRASH_NO_BIN, tc.TRASH_LONG, tc.TRASH_BACK]
    check("CANT_TRASH and TRASH_NO_BIN name the computer's own word for it, and read as a sentence",
          tc.TRASH_WORD in tc.CANT_TRASH and ("has no Recycle Bin to" if PC else "has no Trash to") in tc.TRASH_NO_BIN, (tc.CANT_TRASH, tc.TRASH_NO_BIN))
    check("no line says Claude, and none holds a path", all("Claude" not in w and "/" not in w and "\\" not in w for w in all_words), all_words)
    check("the tests' switch is read from STUDIO_TRASH_FOR_TESTS", tc.trash_for_tests() == str(TRASH))


# ---------- 2. moves through the switch ----------

def moves():
    inside = fresh()
    f = make_file(inside / "Beach song.m4a")
    h = sha(f)
    ok, w = tc.trash(f, inside)
    check("a file: trash() answers (True, '')", ok and w == "", (ok, w))
    check("the file is gone from where it was", not f.exists())
    check("and is in the test's trash folder under its own name, byte for byte", (TRASH / "Beach song.m4a").is_file() and sha(TRASH / "Beach song.m4a") == h)

    folder = inside / "Old takes"
    make_file(folder / "take 1.m4a")
    make_file(folder / "take 2.m4a", 10)
    make_file(folder / "more" / "take 3.wav")
    (folder / "empty").mkdir()
    before = tree(folder)
    ok, w = tc.trash(folder, inside)
    check("a folder of files: trash() answers (True, '')", ok and w == "", (ok, w))
    check("the folder is gone from where it was", not folder.exists())
    check("and is in the test's trash folder whole: every file, every subfolder, byte for byte", (TRASH / "Old takes").is_dir() and tree(TRASH / "Old takes") == before)

    f2 = make_file(inside / "Beach song.m4a", 2000)
    h2 = sha(f2)
    ok, w = tc.trash(f2, inside)
    f3 = make_file(inside / "Beach song.m4a", 1000)
    h3 = sha(f3)
    ok3, w3 = tc.trash(f3, inside)
    check("a second file of the same name goes in as '<name> 2', before the extension, and the first is untouched",
          ok and (TRASH / "Beach song 2.m4a").is_file() and sha(TRASH / "Beach song 2.m4a") == h2 and sha(TRASH / "Beach song.m4a") == h, (ok, w, listing(TRASH)))
    check("a third as '<name> 3'", ok3 and (TRASH / "Beach song 3.m4a").is_file() and sha(TRASH / "Beach song 3.m4a") == h3, (ok3, w3, listing(TRASH)))
    folder2 = inside / "Old takes"
    make_file(folder2 / "x.m4a")
    ok, w = tc.trash(folder2, inside)
    check("a second folder of the same name goes in as '<name> 2'", ok and (TRASH / "Old takes 2").is_dir() and (TRASH / "Old takes 2" / "x.m4a").is_file(), (ok, w, listing(TRASH)))

    odd = make_file(inside / "Nicole's \"café\" 🌊 song.mov")
    ho = sha(odd)
    ok, w = tc.trash(odd, inside)
    check("a name with a quote, an accent and an emoji works", ok and (TRASH / odd.name).is_file() and sha(TRASH / odd.name) == ho, (ok, w))

    deep = make_file(inside / "older" / "deep.m4a")
    ok, w = tc.trash(deep, inside)
    check("a file in a folder under the one it is told is inside it, and moves", ok and (TRASH / "deep.m4a").is_file() and not deep.exists(), (ok, w))
    check("trash_check() on its own moves nothing: a file checked is still there", tc.trash_check(make_file(inside / "stay.m4a"), inside) == (True, "") and (inside / "stay.m4a").is_file())


# ---------- 3. refusals ----------

def refusals():
    inside = fresh()
    other = fresh("Photos")
    keep = make_file(inside / "keep.m4a")
    hk = sha(keep)
    was = listing(TRASH)

    def refused(what, path, folder, words):
        ok, w = tc.trash(path, folder)
        check(f"{what}: refused with the plain words", not ok and w == words, (ok, w))

    refused("a path that is not there", inside / "gone.m4a", inside, tc.TRASH_GONE)
    link = inside / "link.m4a"
    try:
        os.symlink(keep, link)
        refused("a link to a file", link, inside, tc.TRASH_LINK)
        check("the link is still there and its target untouched", link.is_symlink() and keep.is_file() and sha(keep) == hk)
        dlink = inside / "folder link"
        os.symlink(other, dlink)
        refused("a link to a folder", dlink, inside, tc.TRASH_LINK)
        check("the folder it points to is untouched", other.is_dir() and dlink.is_symlink())
        inlink = work / "music link"
        os.symlink(inside, inlink)
        refused("a folder it is told that is itself a link", keep, inlink, tc.TRASH_OUTSIDE)
    except (OSError, NotImplementedError) as e:  # a PC without the right to make links
        skip("links (a link to a file, to a folder, and a folder it is told that is a link)", f"this computer would not make a link: {e}")
    outside = make_file(other / "export.mov")
    refused("a path outside the folder it is told (a sibling folder)", outside, inside, tc.TRASH_OUTSIDE)
    check("and it is still there", outside.is_file())
    refused("the folder it is told, itself", inside, inside, tc.TRASH_OUTSIDE)
    refused("the folder above the one it is told", inside.parent, inside, tc.TRASH_OUTSIDE)
    dotted = str(inside) + os.sep + ".." + os.sep + inside.name + os.sep + "keep.m4a"
    refused("a path with '..' in it, even one that would land inside", dotted, inside, tc.TRASH_OUTSIDE)
    refused("a relative path", "keep.m4a", inside, tc.TRASH_OUTSIDE)
    refused("a path with a slash on the end", str(inside / "keep.m4a") + os.sep, inside, tc.TRASH_OUTSIDE)
    refused("a folder it is told that is not there", keep, inside / "nope", tc.TRASH_OUTSIDE)
    refused("a file as the folder it is told", keep, keep, tc.TRASH_OUTSIDE)
    check("after every refusal the file is exactly where it was", keep.is_file() and sha(keep) == hk)
    check("and nothing new is in the test's trash folder", listing(TRASH) == was, (was, listing(TRASH)))
    if PC:
        longname = inside / ("x" * 240 + ".m4a")
        try:
            make_file(longname)
            refused("a path too long for Windows to move", longname, inside, tc.TRASH_LONG)
        except OSError as e:
            skip("a path too long for Windows", f"could not even make it: {e}")


# ---------- 4. trash_many ----------

def many():
    inside = fresh()
    a, b, c = (make_file(inside / n) for n in ("a.m4a", "b.m4a", "c.m4a"))
    hs = {p.name: sha(p) for p in (a, b, c)}
    was = listing(TRASH)
    ok, w, moved, left = tc.trash_many([a, inside / "missing.m4a", b], inside)
    check("one bad path among several: refused, with its words, and NOTHING moved", not ok and w == tc.TRASH_GONE and moved == [] and left == [str(a), str(inside / "missing.m4a"), str(b)]
          and a.is_file() and b.is_file() and listing(TRASH) == was, (ok, w, moved, left))
    ok, w, moved, left = tc.trash_many([a, outside_file(inside), b], inside)
    check("one path outside among several: the same, nothing moved", not ok and w == tc.TRASH_OUTSIDE and moved == [] and a.is_file() and b.is_file(), (ok, w, moved))
    ok, w, moved, left = tc.trash_many([a, b, str(a), c], inside)
    check("all good: every one moves, in order, a path given twice counted once, nothing left",
          ok and w == "" and moved == [str(a), str(b), str(c)] and left == [] and not a.exists() and not b.exists() and not c.exists(), (ok, w, moved, left))
    check("each is in the test's trash folder byte for byte", all((TRASH / n).is_file() and sha(TRASH / n) == h for n, h in hs.items()))
    ok, w, moved, left = tc.trash_many([], inside)
    check("nothing asked: ok, nothing moved", ok and moved == [] and left == [])

    # the second cannot be moved: the answer names the one that moved and the one left
    d = make_file(inside / "d.m4a")
    if PC:
        e = make_file(inside / "held.m4a")
        with open(e, "rb"):
            ok, w, moved, left = tc.trash_many([d, e], inside)
        check("the second is held open by another program (a PC): the first moved, the second refused in plain words and still there",
              not ok and w == tc.CANT_TRASH and moved == [str(d)] and left == [str(e)] and e.is_file() and not d.exists(), (ok, w, moved, left))
    else:
        held = inside / "held"
        e = make_file(held / "held.m4a")
        os.chmod(held, stat.S_IRUSR | stat.S_IXUSR)
        try:
            ok, w, moved, left = tc.trash_many([d, e], inside)
        finally:
            os.chmod(held, stat.S_IRWXU)
        if os.geteuid() == 0:
            skip("the second cannot be moved (a read-only folder)", "running as root, which a read-only folder does not stop")
        else:
            check("the second sits in a folder made read-only: the first moved, the second refused in plain words and still there",
                  not ok and w == tc.CANT_TRASH and moved == [str(d)] and left == [str(e)] and e.is_file() and not d.exists(), (ok, w, moved, left))


def outside_file(inside):
    p = inside.parent / "Photos" / "out.mov"
    make_file(p)
    return p


# ---------- 5. the real route, with a stand-in ----------

class Recorder:
    """Stands in for subprocess.run (a Mac) or _recycle (a PC): records what it was asked, and does what the
    test tells it: nothing, move the item into a pretend Trash, or move it somewhere that is not a Trash."""

    def __init__(self, does):
        self.does, self.calls = does, []

    def run(self, cmd, **kw):                              # the Mac's osascript
        self.calls.append(list(cmd))
        path = cmd[-1]
        out = ""
        if self.does == "trash":
            dst = HOME / ".Trash" / os.path.basename(path)
            os.rename(path, dst)
            out = str(dst) + "\n"
        elif self.does == "elsewhere":
            dst = work / "elsewhere" / os.path.basename(path)
            dst.parent.mkdir(exist_ok=True)
            os.rename(path, dst)
            out = str(dst) + "\n"
        return subprocess.CompletedProcess(cmd, 0 if self.does != "fail" else 1, out, "" if self.does != "fail" else "execution error: Finder got an error")

    def recycle(self, path):                              # a PC's Recycle Bin call
        self.calls.append([path])
        if self.does == "trash":
            (work / "pretend bin").mkdir(exist_ok=True)
            os.rename(path, work / "pretend bin" / os.path.basename(path))
            return 0
        return 0 if self.does == "nothing" else 1


def real_route():
    inside = fresh()
    f = make_file(inside / "real.m4a")
    hf = sha(f)
    saved = dict(run=tc.subprocess.run, recycle=tc._recycle)
    rec = Recorder("trash")
    try:
        tc.subprocess.run = rec.run
        tc._recycle = rec.recycle
        os.environ.pop("STUDIO_TRASH_FOR_TESTS")
        ok, w = tc.trash(f, inside)
        check("inside a test that set no_windows() and named no trash folder: refused, and the real route never asked",
              not ok and w == tc.CANT_TRASH and rec.calls == [] and f.is_file(), (ok, w, rec.calls))
        os.environ.pop("STUDIO_NO_WINDOWS_FOR_TESTS")
        if not (tc.MAC or PC):
            skip("the real route", "neither a Mac nor a PC: there is no Trash route here")
            return
        if tc.MAC:
            ok, w = tc.trash(f, inside)
            check("the disk the home folder is on, with no ~/.Trash: refused before Finder is asked", not ok and w == tc.TRASH_NO_BIN and rec.calls == [] and f.is_file(), (ok, w, rec.calls))
            (HOME / ".Trash").mkdir()
            ok, w = tc.trash(f, inside)
            check("with a Trash there: Finder is asked once, and the item is in it", ok and w == "" and len(rec.calls) == 1 and not f.exists()
                  and (HOME / ".Trash" / "real.m4a").is_file() and sha(HOME / ".Trash" / "real.m4a") == hf, (ok, w, rec.calls))
            cmd = rec.calls[0]
            script = " ".join(x for x in cmd[:-1] if x != "-e")
            check("it is osascript, with the path as the last argument and nowhere in the script",
                  cmd[0] == "osascript" and cmd[-1] == str(f) and str(f) not in script and "argv" in script, cmd)
            check("the script tells Finder to delete the item and answers with where it went",
                  'tell application "Finder"' in script and "delete" in script and "POSIX path" in script and "rm " not in script, script)
            for does, what in (("nothing", "Finder answers ok but the item is still there"), ("elsewhere", "Finder's answer is a place that is not a Trash"),
                               ("fail", "Finder says no")):
                g = make_file(inside / f"{does}.m4a")
                rec.does, rec.calls = does, []
                ok, w = tc.trash(g, inside)
                stayed = g.is_file() if does != "elsewhere" else (work / "elsewhere" / g.name).is_file()
                check(f"{what}: never called done, the plain words instead" + (" (the item is where the stand-in put it)" if does == "elsewhere" else ", the item still where it was"),
                      not ok and w == tc.CANT_TRASH and len(rec.calls) == 1 and stayed, (ok, w, rec.calls))
            odd = make_file(inside / "it's \"odd\" ☕.m4a")
            rec.does, rec.calls = "trash", []
            ok, w = tc.trash(odd, inside)
            check("a name with quotes is handed over as one argument, exactly", ok and rec.calls[0][-1] == str(odd) and (HOME / ".Trash" / odd.name).is_file(), (ok, w, rec.calls))
        else:
            place = tc._trash_place(str(f))
            if place:
                skip("the drive this test runs on has a $Recycle.Bin", f"it says: {place}")
                return
            ok, w = tc.trash(f, inside)
            check("the Recycle Bin call is asked once, with the full path, and the item is in it", ok and w == "" and rec.calls == [[str(f)]] and not f.exists()
                  and (work / "pretend bin" / "real.m4a").is_file(), (ok, w, rec.calls))
            for does, what in (("nothing", "Windows answers 0 but the item is still there"), ("fail", "Windows says no")):
                g = make_file(inside / f"{does}.m4a")
                rec.does, rec.calls = does, []
                ok, w = tc.trash(g, inside)
                check(f"{what}: never called done, the plain words instead, the item still where it was", not ok and w == tc.CANT_TRASH and len(rec.calls) == 1 and g.is_file(), (ok, w))
    finally:
        tc.subprocess.run = saved["run"]
        tc._recycle = saved["recycle"]
        os.environ["STUDIO_TRASH_FOR_TESTS"] = str(TRASH)
        os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"


# ---------- 6. the source ----------

def source():
    fns = (tc.trash, tc.trash_many, tc.trash_check, tc._trash_mac, tc._trash_pc, tc._recycle, tc._into_test_trash, tc._trash_place, tc.main_trash)
    src = "\n".join(inspect.getsource(fn) for fn in fns)
    bad = [x for x in ("os.remove", "os.unlink", "rmtree", "os.rmdir", '"rm"', "'rm'", "rm -", "send2trash", "unlink(", "remove(") if x in src]
    check("the helper's source (every function of it) names no os.remove, os.unlink, rmtree, rmdir, rm or send2trash", not bad, bad)
    whole = (SCRIPTS / "this_computer.py").read_text(encoding="utf-8")
    check("nothing in this_computer.py names send2trash (nothing installed)", "send2trash" not in whole)
    check("trash() goes through trash_check() first, and trash_many() checks every path before the first move",
          "ok, words = trash_check(path, inside)" in inspect.getsource(tc.trash) and inspect.getsource(tc.trash_many).index("trash_check(") < inspect.getsource(tc.trash_many).index("= trash("))
    check("trash() never calls an item done while it is still where it was", "if os.path.lexists(path):" in inspect.getsource(tc.trash))
    check("the Mac route calls it done only when Finder's answer names a .Trash or .Trashes folder", '"/.Trash/" in out or "/.Trashes/" in out' in inspect.getsource(tc._trash_mac))
    check("the PC route asks for Undo (the Recycle Bin), no box, no question", all(x in inspect.getsource(tc._recycle) for x in ("FOF_ALLOWUNDO", "FOF_NOCONFIRMATION", "FOF_NOERRORUI", "FOF_SILENT", "FO_DELETE")))


# ---------- 7. the hand-run entry ----------

def hand_run():
    inside = fresh()
    f = make_file(inside / "by hand.m4a")
    h = sha(f)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "this_computer.py"), "trash", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
    check("python3 this_computer.py trash <path> says where it went, in the computer's own words", r.returncode == 0 and f"In {tc.TRASH_WORD} now" in r.stdout and tc.TRASH_BACK in r.stdout, (r.returncode, r.stdout, r.stderr[-300:]))
    check("and through the switch the file is in the test's trash folder, byte for byte", not f.exists() and (TRASH / "by hand.m4a").is_file() and sha(TRASH / "by hand.m4a") == h)
    r = subprocess.run([sys.executable, str(SCRIPTS / "this_computer.py"), "trash", str(inside / "nope.m4a")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
    check("a path that is not there: exit 1 and the plain words", r.returncode == 1 and tc.TRASH_GONE in r.stdout, (r.returncode, r.stdout))


def part(name, fn):
    print(f"\n-- {name}", flush=True)
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        import traceback
        check(f"{name}: ran to the end", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-700:]}")


part("the words", words)
part("moves, through the tests' switch", moves)
part("refusals: nothing moves", refusals)
part("trash_many: every path checked before the first move", many)
part("the real route, with a stand-in for Finder (the Recycle Bin on a PC)", real_route)
part("the source: never a delete", source)
part("the hand-run entry", hand_run)

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)   # the test's own scratch folder, nothing of anyone's
sys.exit(1 if failed else 0)
