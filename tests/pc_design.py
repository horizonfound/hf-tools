#!/usr/bin/env python3
"""The carousel designer's own machinery (design.py) on a PC, tried for real: written to run on GitHub's Windows
machine, and on a Mac.

    python tests/pc_design.py [--port 9320]
    ASSISTANT_SCRIPTS=<folder>            try the scripts in another folder (a copy with a fault put in, to see a
                                          check FAIL)

tests/design_check.py is the full test of the designer, but it needs a Mac (sips, the Mac's own JavaScript engine)
and Pillow. This one tries the parts of design.py that work differently on a PC, in a scratch folder it makes
itself (STUDIO_HOME points there; nothing else is touched, nothing is deleted outside that folder). No browser. The
plugin's side needs nothing installed: the photos and the finished 1080 x 1350 slides are real JPEGs written here
in plain Python (one flat grey each), so it runs on a Mac's own Python 3.9 and on a PC with no Pillow.
  1. the slides this test sends are real JPEGs (design.py's own check; and Pillow opens one, where Pillow is);
  2. what the page is given (state_for_page): no path in it, no backslash, nothing of the scratch folder;
  3. a design saved while another handle has its file open (a PC waits a moment), and no scratch file left; then
     its file held for longer than that wait (a sync program, the virus checker): the page's words are about the
     Assistant's own files, never "pictures" or a "photo viewer", no scratch copy is left behind however often
     the page tries again, the stored design is whole, and the change is saved once the file is let go (a PC:
     another program really holds it; a Mac: Windows' refusal is pretended at this_computer.replace);
  4. names: an accent, an emoji, a word Windows keeps (CON, aux.final), a dot at the end, the characters Windows
     refuses, 80 letters, 200 letters (refused in plain words): each becomes a slide name this computer takes,
     the slides are saved under it, and the folder lists exactly the names written down; a word Windows keeps, a
     dot and 80 letters in all still gives a name that settles (80 letters, known again afterwards, "Already
     saved" on a second press); half of an emoji is not a name or a text, and leaves nothing behind;
  5. staging and a save from start to finish: the slides in the Carousel folder are byte for byte the ones sent,
     nothing waits in staging, and no record of the save holds a path or a backslash; a design's "earlier" copy
     takes only digits and dashes from a date a hand could have changed;
  6. the save as the page does it: the commit started as a process of its own through this_computer.popen_detached
     (no window on a PC, a session of its own on a Mac), with this process in an old code page and an emoji in the
     design's name, and its answer read back; then the command's own output in that old code page, as bytes;
  7. a save while one slide in the Carousel folder is held open by another program, and while the kit's record is;
     then the one road a held file really changes on a PC: a slide of the set being saved is itself held open, so
     Windows refuses to move it. The save says so in parts/on-a-pc.md's words, the slides before it are in, the
     rest wait, the record says "moving", and the same press finishes it under the same name once the file is
     let go. On a PC another program really holds the file; on a Mac (which never refuses) Windows' refusal is
     pretended at this_computer.rename_new, and said so;
  8. a drive with no hard links (os.link refused): a save still goes in, and a name that is taken is never taken
     again (a PC never links, so there this is the same road as every other save);
  9. two saves at the same moment from two processes, of two designs with the same name: both go in, one as
     "<name>" and one as "<name> (2)", every file the right one, both written in the kit's record;
 10. the locks across programs: 4 processes x 40 bumps under the design lock = 160; a save while another program
     holds the slides lock says "busy" in plain words and changes nothing, then goes in once it lets go;
 11. how long a path may be on a PC: a slide whose address would pass 260 characters is refused in plain words
     BEFORE anything is staged, and a shorter name saves; a kit too deep for the designer's own hidden files is
     refused before a design is made. On a PC the lengths are real (long paths switched off is pretended where
     they are on, and said so); on a Mac the PC's side is switched on for these calls alone and the lengths are
     counted as if the scratch folder were where a PC's is. A Mac itself has no such limit: checked too.
 12. the real page server (posting_queue.py serve) on a scratch port: every refusal of every designer route
     leaves every file byte for byte as it was and gives no path away; the plugin's own font is served as a font;
     then one save through the server, whose commit the server starts itself.
 13. the stories designer (kind "stories"), its machinery as a PC runs it: what the page is given (no path, a
     story's size, the handle), one stories design a shoot, a story's looks kept, a carousel's slide refused as a
     story, a set of 1080 x 1920 stories saved into the Stories folder under names this computer takes (an accent, an
     emoji, a word Windows keeps), byte for byte, the kit's record and kit.stories_shown, "(2)" for a second set,
     and on a PC the 260-character limit said in a story's words.
 14. Nicole's v22: what the page is given (her five templates first, her eight single slides, no path), and Rename on
     one of their own templates: a name with an accent, an emoji and characters a PC refuses in a file's name (it is
     only ever inside the file), the version before kept beside it, no scratch file left, the refusals, and a rename
     while another program has the file open.
Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept (its place is
printed), and cleared away when everything passed.
"""
import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("ASSISTANT_SCRIPTS") or ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts")
FONTS = SCRIPTS.parent.parent.parent / "shared" / "fonts"
WINDOWS = os.name == "nt"
NEVER_PORTS = {8790, 8765, 8770, 8899}
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:600]}]" if detail != "" and not ok else ""), flush=True)
    return bool(ok)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


try:
    from PIL import Image
    HAVE_PIL = True
except Exception:  # noqa: BLE001
    HAVE_PIL = False

PORT = None
if "--port" in sys.argv:
    PORT = int(sys.argv[sys.argv.index("--port") + 1])
    if any(p in NEVER_PORTS for p in range(PORT, PORT + 20)):
        sys.exit("STOP: that port range reaches one the real pages use.")

work = Path(tempfile.mkdtemp(prefix="assistant pc design "))
STUDIO = work / "studio"
STUDIO.mkdir()
os.environ["STUDIO_HOME"] = str(STUDIO)           # before arrange is imported: it reads STUDIO_HOME then
ENV = dict(os.environ)
sys.path.insert(0, str(SCRIPTS))
import this_computer as tc  # noqa: E402
import arrange  # noqa: E402
import kit as kit_mod  # noqa: E402
import design  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_plain_jpeg import jpeg, make_kit as plain_kit  # noqa: E402  (real JPEGs and a pretend kit, in plain Python)

tc.utf8_output()
print(f"This is a {tc.COMPUTER}, Python {sys.version.split()[0]}" + (", with Pillow" if HAVE_PIL else ", no Pillow") + ".\n", flush=True)
HOME = work / "The Assistant"
r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--home", str(HOME)], capture_output=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("a pretend Assistant folder is set up (posts.py setup)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
CONTENT = HOME / "Your Content"
CONTENT.mkdir(parents=True, exist_ok=True)
W, H = design.W, design.H


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(p):
    return sha(Path(p).read_bytes())


def snap(folder):
    """{a file's place under folder, with forward slashes: its hash} for every file there."""
    out = {}
    for base, _, files in os.walk(folder):
        for f in files:
            p = Path(base) / f
            try:
                out[p.relative_to(folder).as_posix()] = file_sha(p)
            except OSError:
                out[p.relative_to(folder).as_posix()] = "unreadable"
    return out


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def no_path(obj):
    """No text in it holds a backslash, a drive letter's colon-slash, or any part of the scratch folder."""
    bad = [s for s in strings(obj) if "\\" in s or str(work) in s or work.name in s or ":/" in s.replace("https://", "")]
    return not bad, bad[:3]


def make_kit(name, photos=6):
    return plain_kit(CONTENT, name, photos)


_n = [0]


def token(prefix="s"):
    _n[0] += 1
    return f"{prefix}{_n[0]:012d}"


PAGE = "pcdesignpage01"


def save(kit, did, name=None, change=None):
    """One save from a page: the stored layout, with one thing changed (the background, by default a new grey)."""
    d = design.load_design(kit, did)
    state = json.loads(json.dumps(d["state"]))
    if change is None:
        _n[0] += 1
        state["bg"] = "#%02x%02x%02x" % ((_n[0] * 7) % 256, (_n[0] * 13) % 256, (_n[0] * 29) % 256)
    else:
        change(state)
    body = {"kit": kit.name, "design": did, "page": PAGE, "base": d["rev"], "stamp": arrange.sheet_stamp(kit), "state": state}
    if name is not None:
        body["name"] = name
    return design.save_from_page(body)


def slides_for(d, tag):
    return [jpeg(W, H, level=i * 3, note=f"{tag} slide {i}") for i in range(1, d["state"]["slides"] + 1)]


def stage(kit, d, tok, slides):
    codes = [design.stage_slide(kit, d["id"], tok, i, len(slides), data)[0] for i, data in enumerate(slides, 1)]
    return codes == [200] * len(slides), codes


def in_carousel(kit, base, slides):
    """Is every slide of the set in the Carousel folder under its name, byte for byte the one sent?"""
    car = kit / "Carousel"
    try:
        listed = {unicodedata.normalize("NFC", n) for n in os.listdir(car)}
    except OSError:
        return False, "no Carousel folder"
    for i, data in enumerate(slides, 1):
        name = design.SET_NAME.format(base=base, i=i)
        if unicodedata.normalize("NFC", name) not in listed:
            return False, f"{name!r} is not listed: {sorted(listed)[:6]}"
        if file_sha(car / name) != sha(data):
            return False, f"{name!r} is not the slide that was sent"
    return True, ""


def first_design(kit):
    d = design.ensure_design(kit)
    return design.load_design(kit, d["id"]) if d else None


def save_set(kit, d, tag, rev=True):
    """Stage a design's slides and put them in. Returns (the commit's answer, the slides sent)."""
    tok = token()
    slides = slides_for(d, tag)
    ok, codes = stage(kit, d, tok, slides)
    if not ok:
        return {"state": "not staged", "codes": codes}, slides
    return design.commit(kit, d["id"], tok, d["rev"] if rev else None), slides


# ---------------------------------------------------------------- 1: the slides are real
def jpeg_checks():
    data = jpeg(W, H, level=7, note="a slide")
    check("a slide written here is one design.py takes for a finished slide (1080 x 1350, whole)", design.slide_ok(data),
          (len(data), design.jpeg_size(data)))
    check("two slides of one grey still differ (their note)", jpeg(W, H, 7, "a") != jpeg(W, H, 7, "b"))
    if HAVE_PIL:
        import io
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            ok, got = im.size == (W, H), (im.size, im.mode, im.getpixel((500, 700)))
        except Exception as e:  # noqa: BLE001
            ok, got = False, repr(e)
        check("Pillow opens it and reads every block: a real 1080 x 1350 picture", ok, got)
    else:
        skip("Pillow opens the slide written here", "Pillow is not installed for this Python; design.py's own check above still ran")


# ---------------------------------------------------------------- 2: what the page is given
def state_checks(kit):
    st = design.state_for_page(kit)
    check("state_for_page: the shoot's first design is made and given to the page", bool(st) and st.get("ok") and st["design"]["id"], st)
    if not st:
        return
    ok, bad = no_path(st)
    check("state_for_page: no path, no backslash and nothing of the scratch folder in it", ok, bad)
    check("state_for_page: the shoot is named by its folder's name alone", st["kit"] == kit.name)
    check("state_for_page: the fonts the plugin carries are offered as its own", any(f.get("own") for g in st["fonts"]["groups"] for f in g["fonts"]),
          [g["name"] for g in st["fonts"]["groups"]])
    check("the fallback for slide text is a font both computers have (Georgia)", st["fonts"]["fallback"] == "Georgia")


# ---------------------------------------------------------------- 3: saving while the file is open
def held_design_checks(kit):
    d = first_design(kit)
    target = design.design_path(kit, d["id"])
    reader = open(target, "r", encoding="utf-8")
    threading.Timer(0.5, reader.close).start()
    t0 = time.time()
    try:
        code, out = save(kit, d["id"], name="Held open ✓")
        err = None
    except OSError as e:
        code, out, err = None, None, e
    check("a design saved while another handle has its file open: saved (a PC waits a moment)",
          err is None and code == 200 and (design.load_design(kit, d["id"]) or {}).get("name") == "Held open ✓",
          f"{code} {out} {err} after {time.time() - t0:.2f} s")
    left = [n for n in os.listdir(design.designs_dir(kit)) if n.endswith(".tmp")]
    check("and no scratch file is left beside it", not left, left)
    check("the version before the save is kept beside it", design.prev_path(kit, d["id"]).is_file())
    held_record_checks(kit, d["id"])


def held_record_checks(kit, did):
    """The design's own record held for longer than this_computer.replace waits (about three seconds)."""
    target = design.design_path(kit, did)
    stored = design.load_design(kit, did)
    real_replace = tc.replace
    child = None
    if WINDOWS:
        ready = work / f"holding-{time.time_ns()}.txt"
        child = subprocess.Popen([sys.executable, "-c", HOLD_FILE, str(target), str(ready), "120"], env=ENV)
        end = time.time() + 30
        while not ready.exists() and time.time() < end:
            time.sleep(0.05)
        if not check("another program has the design's own record open", ready.exists()):
            child.kill()
            child.wait(timeout=30)
            return
    else:
        print("      (a Mac never refuses to save over an open file: Windows' refusal is pretended at this_computer.replace, "
              "and the words are asked for as a PC gives them)", flush=True)

        def refused(src, dst, tries=25):
            if Path(dst) == target:
                e = PermissionError(13, "The process cannot access the file because it is being used by another process")
                e.winerror = 32
                raise e
            return real_replace(src, dst, tries)

        tc.replace = refused
    errs = []
    try:
        for _ in range(2):                          # the page tries again by itself: twice here
            try:
                got = save(kit, did)
                errs.append(None)
            except OSError as e:
                errs.append(e)
        check("a design's record held longer than the wait: the save is refused (twice), never half done",
              len(errs) == 2 and all(isinstance(e, PermissionError) for e in errs), [repr(e)[:120] for e in errs])
        e = errs[-1]
        if isinstance(e, OSError):
            was_pc, tc.WINDOWS = tc.WINDOWS, True   # the words as a PC gives them (it is one already, on a PC)
            try:
                words = design._drive_words("/design", e)
                kept = design._drive_words("/design-brand", e)
                slide_words = design._drive_words("/design-commit", e)
            finally:
                tc.WINDOWS = was_pc
            ok, bad = no_path({"w": words, "k": kept})
            check("the page's words are about the Assistant's own files: no \"pictures\", no \"photo viewer\", no path",
                  words.startswith(f"Your changes can't be saved right now: something on this {tc.COMPUTER}") and "Assistant's own files" in words
                  and words.endswith("They'll be saved by themselves once that is put right.") and "picture" not in words
                  and "photo viewer" not in words and ok, words)
            check("the same for a brand color, a font or a template (\"That couldn't be saved: ...\")",
                  kept.startswith(f"That couldn't be saved: something on this {tc.COMPUTER}") and "picture" not in kept, kept)
            check("a slide that can't be moved still gets the words about pictures (parts/on-a-pc.md's line)",
                  slide_words.startswith("Couldn't save the slides: another program") and "Nothing was lost" in slide_words, slide_words)
        left = [n for n in os.listdir(design.designs_dir(kit)) if n.endswith(".tmp")]
        check("no scratch copy is left beside the design, however often the page tried", not left, left)
        now = design.load_design(kit, did)
        check("the stored design is whole and unchanged, and the version before is beside it",
              now is not None and now["rev"] == stored["rev"] and now["state"] == stored["state"] and design.prev_path(kit, did).is_file(),
              (now or {}).get("rev"))
    finally:
        tc.replace = real_replace
        if child is not None:
            child.kill()
            child.wait(timeout=30)
    code, out = save(kit, did)
    check("once the record is let go, the change is saved", code == 200 and design.load_design(kit, did)["rev"] == stored["rev"] + 1, (code, out))


# ---------------------------------------------------------------- 4: names
FORBIDDEN = set('\\/:*?"<>|')
NAMES = [
    ("an accent and a curly quote", "Zoë’s café – été"),
    ("an emoji", "Beach day 🌊🐚"),
    ("a word Windows keeps for itself", "CON"),
    ("that word with a dot after it", "aux.final"),
    ("a dot at the end", "Smith family."),
    ("the characters Windows refuses", 'a<b>c:d"e/f\\g|h?i*j'),
    ("80 letters", "L" * 80),
    ("letters that are not Latin", "ビーチの写真 пляж"),
]


def name_checks(kit):
    d = first_design(kit)
    for what, name in NAMES:
        code, out = save(kit, d["id"], name=name)
        d = design.load_design(kit, d["id"])
        if not check(f"name, {what}: the design takes it as its name", code == 200 and d["name"] == design.clean_name(name), (code, out)):
            continue
        base = design.safe_base(name)
        fine = (base and not (set(base) & FORBIDDEN) and base == base.strip(" .") and len(base) <= design.NAME_MAX
                and tc.unreserved(base) == base and base == design.safe_base(base))
        check(f"name, {what}: the slides' name is one a PC takes ({base!r})", fine, base)
        res, slides = save_set(kit, d, what)
        ok, why = in_carousel(kit, res.get("base") or "", slides) if res.get("state") == "done" else (False, res)
        check(f"name, {what}: its slides are saved under that name, listed exactly as written down",
              ok and res["base"] == base, why or res)
    code, out = save(kit, d["id"], name="N" * 200)
    check("name, 200 letters: refused in plain words, and the design keeps the name it had",
          code == 400 and out.get("words") == design.NAME_BAD and design.load_design(kit, d["id"])["name"] == d["name"], (code, out))
    check("a name of nothing but characters Windows refuses still gives the slides a name", design.safe_base('<>:"/\\|?*') == "Carousel",
          design.safe_base('<>:"/\\|?*'))
    check('a reserved word keeps its underscore before any dot ("aux_.final", "Con_")',
          design.safe_base("aux.final") == "aux_.final" and design.safe_base("Con") == "Con_", (design.safe_base("aux.final"), design.safe_base("Con")))
    # a word Windows keeps, a dot, and 80 letters in all: the underscore must not push the name past 80 (a name that
    # did not settle made a save whose own record was not known again: "Not every slide arrived", then a second set)
    settle = [w + tail for w in ("con", "AUX", "nul", "Prn", "COM1", "lpt1") for tail in ("." + "x" * 80, " ." + "y" * 80)]
    settle = [n[:80] for n in settle]
    unsettled = [(n[:8], len(design.safe_base(n))) for n in settle
                 if len(design.safe_base(n)) > design.NAME_MAX or design.safe_base(design.safe_base(n)) != design.safe_base(n)]
    check("a word Windows keeps, a dot and 80 letters in all: the slides' name is 80 letters at most and settles", not unsettled, unsettled)
    name = "con." + "x" * 76
    code, out = save(kit, d["id"], name=name)
    d = design.load_design(kit, d["id"])
    res, slides = save_set(kit, d, "reserved 80")
    ok, why = in_carousel(kit, res.get("base") or "", slides) if res.get("state") == "done" else (False, res)
    last = design.last_done(kit, d["id"]) or {}
    check("such a design's slides are saved, and the save's own record is known again afterwards",
          code == 200 and ok and len(res["base"]) <= design.NAME_MAX and last.get("base") == res["base"], why or (res, last.get("base")))
    files_before = sorted(os.listdir(kit / "Carousel"))
    res2, _ = save_set(kit, d, "reserved 80 again")
    check("a second press with nothing changed says \"Already saved\" and makes no second set",
          res2.get("state") == "already" and sorted(os.listdir(kit / "Carousel")) == files_before, res2)
    # half of a two-part character (only a made-up request can send one): not a name, not a text, nothing written
    half = json.loads('"Beach \\ud83c"')
    before = snap(design.designs_dir(kit))
    try:
        code, out = save(kit, d["id"], name=half)
        err = None
    except Exception as e:  # noqa: BLE001
        code, out, err = None, None, repr(e)
    check("a name holding half an emoji is refused like any other unusable name (400), and nothing is written or left behind",
          err is None and code == 400 and out.get("words") == design.NAME_BAD and snap(design.designs_dir(kit)) == before, (code, out, err))
    block = {"id": 1, "type": "text", "text": "Hi", "font": "Georgia", "size": 40, "color": "#000000", "x": 100, "y": 100, "w": 300, "h": 60}
    fine = design.validate_state({"slides": 2, "bg": "#ffffff", "blocks": [block]})
    bad = design.validate_state({"slides": 2, "bg": "#ffffff", "blocks": [dict(block, text=half)]})
    check("and words holding half an emoji are refused as text, where the same words whole are taken", fine[0] is not None and bad == (None, "text"), (fine[1], bad))


# ---------------------------------------------------------------- 5: staging and a save, start to finish
def commit_checks(kit):
    d = first_design(kit)
    save(kit, d["id"], name="Start to finish")
    d = design.load_design(kit, d["id"])
    tok = token()
    slides = slides_for(d, "whole")
    before = snap(kit / "Carousel") if (kit / "Carousel").is_dir() else {}
    ok, codes = stage(kit, d, tok, slides)
    check("every slide is taken into staging", ok, codes)
    folder = design.staging_dir(kit) / f"{d['id']}-{tok}"
    staged = sorted(os.listdir(folder)) if folder.is_dir() else []
    check("staging holds exactly slide-01 to slide-NN, each the bytes that were sent",
          staged == [f"slide-{i:02d}.jpg" for i in range(1, len(slides) + 1)]
          and all(file_sha(folder / n) == sha(s) for n, s in zip(staged, slides)), staged)
    check("nothing has reached the Carousel folder yet", (snap(kit / "Carousel") if (kit / "Carousel").is_dir() else {}) == before)
    again = design.stage_slide(kit, d["id"], tok, 1, len(slides), slides[0])[0]
    other = design.stage_slide(kit, d["id"], tok, 1, len(slides), slides[1])[0]
    check("the same slide sent again is fine; a different picture for a slide that has arrived is refused", again == 200 and other == 409, (again, other))
    res = design.commit(kit, d["id"], tok, d["rev"])
    ok, why = in_carousel(kit, res.get("base") or "", slides) if res.get("state") == "done" else (False, res)
    check("the commit puts the set in the Carousel folder, byte for byte the slides sent", ok and res["base"] == "Start to finish", why or res)
    after = snap(kit / "Carousel")
    check("every file that was in the Carousel folder before is still there, unchanged", all(after.get(k) == v for k, v in before.items()))
    check("nothing is left waiting in staging for that set", not folder.exists(), sorted(os.listdir(folder)) if folder.exists() else "")
    j = json.loads(design._journal_path(kit, d["id"], tok).read_text(encoding="utf-8"))
    ok, bad = no_path(j)
    check("the save's record says done, names its files by name only, and holds no path or backslash",
          j["state"] == "done" and ok and all("/" not in f["final"] for f in j["files"]), bad or j["state"])
    rec = kit_mod.load_rec(kit)
    cs = rec.get("carousel_set") or {}
    ok, bad = no_path({"carousel_set": cs, "laid_out": rec.get("laid_out")})
    check("the kit's record names the set shown (carousel_set) and every set (laid_out), with no path",
          cs.get("kind") == "laid-out" and cs.get("base") == res.get("base") and ok
          and any(x.get("token") == tok for x in rec.get("laid_out") or []), bad or cs)
    shown = kit_mod.carousel_shown(kit)
    check("the kit page's rule shows this set as the carousel", shown["kind"] == "laid-out" and len(shown["files"]) == len(slides), shown["kind"])
    lines = [arrange.waiting_line(w) for w in arrange.waiting() if w["kit"] == kit.name and w["piece"] == "design"]
    check("the line for Claude is written", len(lines) == 1 and lines[0].endswith("| Start to finish"), lines)
    twice = design.commit(kit, d["id"], tok, d["rev"])
    check("the same commit again says the same and makes nothing new", twice.get("state") == "done" and snap(kit / "Carousel") == after, twice)
    # a date a hand could have changed never makes folders or a name a PC refuses
    p = design.design_path(kit, d["id"])
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["updated"] = "2025/01:02*x"
    p.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
    code, _ = save(kit, d["id"])
    earlier = design.designs_dir(kit) / "earlier"
    names = sorted(os.listdir(earlier)) if earlier.is_dir() else []
    check("an 'earlier' copy takes only digits and dashes from a date a hand changed (no folder made of a slash)",
          code == 200 and f"{d['id']} 20250102.json" in names and all((earlier / n).is_file() for n in names), names)


# ---------------------------------------------------------------- 6: the commit as a process of its own
OLD_PAGE = {"PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252" if WINDOWS else "latin-1", "PYTHONCOERCECLOCALE": "0"}


def child_checks(kit):
    d = first_design(kit)
    name = "Été 🌊 Zoë’s"
    save(kit, d["id"], name=name)
    d = design.load_design(kit, d["id"])
    tok = token()
    slides = slides_for(d, "child")
    ok, codes = stage(kit, d, tok, slides)
    check("slides staged for the page's own way of saving", ok, codes)
    seen, started = [], []
    real_popen, real_detached = subprocess.Popen, tc.popen_detached

    class Recording(real_popen):
        def __init__(self, *a, **kw):
            seen.append(dict(kw))
            super().__init__(*a, **kw)

    def detached(cmd, **kw):
        started.append(list(cmd))
        return real_detached(cmd, **kw)

    was = {k: os.environ.get(k) for k in OLD_PAGE}
    os.environ.update(OLD_PAGE)                      # the page server in a PC's old code page: its children inherit it
    subprocess.Popen, tc.popen_detached = Recording, detached
    try:
        code, out = design._post_commit({"kit": kit.name, "design": d["id"], "set": tok, "rev": d["rev"], "count": len(slides)})
    finally:
        subprocess.Popen, tc.popen_detached = real_popen, real_detached
        for k, v in was.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    check("the commit is started through this_computer.popen_detached, as a command of its own (design.py commit)",
          len(started) == 1 and "commit" in started[0] and str(kit) in started[0], started)
    kw = seen[-1] if seen else {}
    if WINDOWS:
        check("on a PC it is started with no window (CREATE_NO_WINDOW) and no console to read from",
              bool(kw.get("creationflags", 0) & 0x08000000) and kw.get("stdin") == subprocess.DEVNULL, kw)
    else:
        check("on a Mac it is started in a session of its own, exactly as before", kw.get("start_new_session") is True, kw)
    ok, why = in_carousel(kit, out.get("base") or "", slides) if code == 200 and out.get("ok") else (False, (code, out))
    check("its answer is read back in an old code page: saved, under the name with the accent and the emoji",
          ok and out.get("base") == design.safe_base(name) and out.get("count") == len(slides), why or out)
    ok, bad = no_path(out)
    check("the answer the page gets holds no path", ok, bad)
    env = dict(ENV, **OLD_PAGE)
    r = subprocess.run([sys.executable, str(SCRIPTS / "design.py"), "commit", str(kit), "--design", d["id"], "--set", tok,
                        "--rev", str(d["rev"])], capture_output=True, env=env, timeout=180)
    try:
        text = r.stdout.decode("utf-8")
    except UnicodeDecodeError as e:
        text = f"not UTF-8: {e}"
    res = None
    for line in reversed(text.splitlines()):
        if line.startswith("RESULT: "):
            try:
                res = json.loads(line[8:])
            except ValueError:
                pass
            break
    check("design.py commit in an old code page: exit 0, its output is UTF-8 and names the set with its emoji",
          r.returncode == 0 and design.safe_base(name) in text, (r.returncode, text[-300:], r.stderr[-300:]))
    check("its RESULT line is read back whole (plain ASCII, whatever the name)",
          isinstance(res, dict) and res.get("state") == "done" and res.get("base") == design.safe_base(name), res)
    r = subprocess.run([sys.executable, str(SCRIPTS / "design.py"), "show", str(kit)], capture_output=True, env=env, timeout=180)
    try:
        shown = r.stdout.decode("utf-8")
    except UnicodeDecodeError as e:
        shown = f"not UTF-8: {e}"
    check("design.py show in an old code page: every name comes out, none stops the report", r.returncode == 0 and name in shown,
          (r.returncode, shown[-300:], r.stderr[-300:]))


# ---------------------------------------------------------------- 7: a save while a slide is held open
HOLD_FILE = ("import sys, time\n"
             "f = open(sys.argv[1], 'rb')\n"
             "open(sys.argv[2], 'w', encoding='utf-8').write('ok')\n"
             "time.sleep(float(sys.argv[3]))\n")


def held_slide_checks(kit):
    d = first_design(kit)
    save(kit, d["id"], name="Held slide")
    d = design.load_design(kit, d["id"])
    res1, slides1 = save_set(kit, d, "first")
    if not check("a first set is saved", res1.get("state") == "done" and res1.get("base") == "Held slide", res1):
        return
    held = kit / "Carousel" / design.SET_NAME.format(base="Held slide", i=1)
    ready = work / f"holding-{time.time_ns()}.txt"
    p = subprocess.Popen([sys.executable, "-c", HOLD_FILE, str(held), str(ready), "20"], env=ENV)
    try:
        end = time.time() + 30
        while not ready.exists() and time.time() < end:
            time.sleep(0.05)
        check("another program has slide 01 of that set open", ready.exists())
        save(kit, d["id"])                          # a change, so the next save is a new set
        d = design.load_design(kit, d["id"])
        t0 = time.time()
        res2, slides2 = save_set(kit, d, "second")
        ok, why = in_carousel(kit, res2.get("base") or "", slides2) if res2.get("state") == "done" else (False, res2)
        check("a second save while that slide is held open: saved beside it, as \"Held slide (2)\"",
              ok and res2.get("base") == "Held slide (2)", f"{why or res2} after {time.time() - t0:.1f} s")
        ok, why = in_carousel(kit, "Held slide", slides1)
        check("the first set, the held slide among it, is byte for byte what it was", ok, why)
    finally:
        p.kill()
        p.wait(timeout=30)
    # the kit's own record open in another handle while a save writes it (a PC waits a moment)
    save(kit, d["id"])
    d = design.load_design(kit, d["id"])
    reader = open(kit_mod.rec_path(kit), "r", encoding="utf-8")
    threading.Timer(0.6, reader.close).start()
    res3, slides3 = save_set(kit, d, "third")
    ok, why = in_carousel(kit, res3.get("base") or "", slides3) if res3.get("state") == "done" else (False, res3)
    rec = kit_mod.load_rec(kit)
    check("a save while the kit's record is open in another handle: saved, and the record names it",
          ok and (rec.get("carousel_set") or {}).get("base") == res3.get("base"), why or res3)
    held_move_checks(kit, d)


HELD_WORDS = "Couldn't save the slides: another program has one of these pictures open"     # parts/on-a-pc.md's line


def held_move_checks(kit, d):
    """A slide of the very set being saved is held open by another program while the commit moves it."""
    save(kit, d["id"], name="Held move")
    d = design.load_design(kit, d["id"])
    tok = token()
    slides = slides_for(d, "held move")
    n = len(slides)
    ok, codes = stage(kit, d, tok, slides)
    if not check("a new set is staged for the held move", ok and n >= 3, (codes, n)):
        return
    stag = design.staging_dir(kit) / f"{d['id']}-{tok}"
    held = stag / "slide-03.jpg"
    car = kit / "Carousel"
    before = snap(car)
    real_rename_new, real_plain = tc.rename_new, kit_mod._plain_os
    child = None
    if WINDOWS:
        ready = work / f"holding-{time.time_ns()}.txt"
        child = subprocess.Popen([sys.executable, "-c", HOLD_FILE, str(held), str(ready), "120"], env=ENV)
        end = time.time() + 30
        while not ready.exists() and time.time() < end:
            time.sleep(0.05)
        if not check("another program has slide 03 of the set being saved open (in staging)", ready.exists()):
            child.kill()
            child.wait(timeout=30)
            return
    else:
        print("      (a Mac never refuses to move an open file: Windows' refusal is pretended at this_computer.rename_new, "
              "after its own three seconds of trying again are left out, and the words are asked for as a PC gives them)", flush=True)

        def refused(src, dst, tries=25):
            if Path(src).name == held.name and Path(src).parent == stag:
                e = PermissionError(13, "The process cannot access the file because it is being used by another process")
                e.winerror = 32                     # ERROR_SHARING_VIOLATION, as Windows gives it
                raise e
            return real_rename_new(src, dst, tries)

        def plain_as_a_pc(e):
            was, tc.WINDOWS = tc.WINDOWS, True      # for these words alone
            try:
                return real_plain(e)
            finally:
                tc.WINDOWS = was

        tc.rename_new, kit_mod._plain_os = refused, plain_as_a_pc
    try:
        t0 = time.time()
        res = design.commit(kit, d["id"], tok, d["rev"])
        took = time.time() - t0
        check("a save while a slide of that very set is held open: a problem with the drive, said in the on-a-pc words",
              res.get("state") == "problem" and res.get("why") == "drive" and str(res.get("words", "")).startswith(HELD_WORDS)
              and "Nothing was lost" in res.get("words", "") and "Press Save slides again" in res.get("words", ""), f"{res} after {took:.1f} s")
        ok, bad = no_path(res)
        check("its words hold no path", ok, bad)
        code, told = design._answer_for(res)
        check("the page is told the same (500, why 'drive'), so it shows these words and does not just try again",
              code == 500 and told.get("why") == "drive" and told.get("words") == res.get("words"), (code, told))
        if WINDOWS:
            check("a PC waited a moment for the file to be let go before giving up (about three seconds)", 2.0 <= took <= 30.0, f"{took:.1f} s")
        now = snap(car)
        first_two = {design.SET_NAME.format(base="Held move", i=i): sha(slides[i - 1]) for i in (1, 2)}
        check("slides 01 and 02 are in the Carousel folder, byte for byte; the held one and those after it are not",
              {k: v for k, v in now.items() if k not in before} == first_two, sorted(k for k in now if k not in before))
        check("every file that was in the Carousel folder is unchanged", all(now.get(k) == v for k, v in before.items()))
        left = sorted(os.listdir(stag)) if stag.is_dir() else []
        check("the held slide and the ones after it still wait in staging, each the bytes that were sent",
              left == [f"slide-{i:02d}.jpg" for i in range(3, n + 1)] and all(file_sha(stag / x) == sha(slides[int(x[6:8]) - 1]) for x in left), left)
        j = design._read_json(design._journal_path(kit, d["id"], tok)) or {}
        check("the save's record says \"moving\", under the name it chose (so the next press finishes this save, not a new one)",
              j.get("state") == "moving" and j.get("base") == "Held move", (j.get("state"), j.get("base")))
        rec = kit_mod.load_rec(kit)
        check("the kit's record does not name the half-saved set as the carousel",
              (rec.get("carousel_set") or {}).get("token") != tok and not any(isinstance(x, dict) and x.get("token") == tok for x in rec.get("laid_out") or []))
    finally:
        tc.rename_new, kit_mod._plain_os = real_rename_new, real_plain
        if child is not None:
            child.kill()                            # the other program is closed
            child.wait(timeout=30)
    res2 = design.commit(kit, d["id"], tok, d["rev"])
    ok, why = in_carousel(kit, res2.get("base") or "", slides) if res2.get("state") == "done" else (False, res2)
    check("once the file is let go, the same press finishes the save under the same name: every slide in, byte for byte",
          ok and res2.get("base") == "Held move" and res2.get("count") == n, why or res2)
    now = snap(car)
    check("no second set was made, and nothing that was there was changed",
          sorted(k for k in now if k not in before) == sorted(design.SET_NAME.format(base="Held move", i=i) for i in range(1, n + 1))
          and all(now.get(k) == v for k, v in before.items()), sorted(k for k in now if k not in before))
    check("nothing is left waiting in staging for it", not stag.exists(), sorted(os.listdir(stag)) if stag.exists() else "")
    rec = kit_mod.load_rec(kit)
    check("and the kit's record names it as the carousel now", (rec.get("carousel_set") or {}).get("token") == tok, rec.get("carousel_set"))


# ---------------------------------------------------------------- 8: a drive with no hard links
def no_links_checks(kit):
    d = first_design(kit)
    save(kit, d["id"], name="No links")
    d = design.load_design(kit, d["id"])
    real_link = os.link
    calls = []

    def refused(src, dst, *a, **kw):
        calls.append(dst)
        raise OSError(45 if sys.platform == "darwin" else 95, "Operation not supported")

    os.link = refused
    try:
        res, slides = save_set(kit, d, "nolinks")
        ok, why = in_carousel(kit, res.get("base") or "", slides) if res.get("state") == "done" else (False, res)
        check("no hard links on this drive (os.link refused): the save still goes in, every slide the one sent", ok and res.get("base") == "No links", why or res)
        if WINDOWS:
            check("a PC never asks for a link (Windows' own rename refuses a name that is taken)", not calls, calls[:2])
        else:
            check("a Mac asked for a link first and fell back to a look and a rename", len(calls) >= len(slides), len(calls))
        taken = kit / "Carousel" / design.SET_NAME.format(base="No links", i=1)
        was = file_sha(taken)
        scratch = kit / "Carousel" / ".part-pc-design-test.jpg"
        scratch.write_bytes(jpeg(W, H, 9, "an intruder"))
        got = kit_mod.place(scratch, taken)
        check("with no links, a name that is taken is still never taken again (the file there is unchanged)",
              got is False and file_sha(taken) == was and scratch.is_file(), got)
        try:
            scratch.unlink()                        # this test's own scratch file
        except OSError:
            pass
    finally:
        os.link = real_link


# ---------------------------------------------------------------- 9: two saves at the same moment
def race_checks(kit):
    for round_no in (1, 2, 3):
        name = f"Twin {round_no}"
        sets = []
        for _ in range(2):
            code, out = design.new_design(kit, name=name, token=token("n"))
            d = design.load_design(kit, out["design"]["id"]) if code == 200 else None
            if d is None:
                check(f"round {round_no}: two designs of one name are made", False, (code, out))
                return
            tok = token()
            slides = slides_for(d, f"twin {round_no} {d['id']}")
            ok, codes = stage(kit, d, tok, slides)
            sets.append((d, tok, slides))
        ps = [subprocess.Popen([sys.executable, str(SCRIPTS / "design.py"), "commit", str(kit), "--design", d["id"], "--set", tok,
                                "--rev", str(d["rev"])], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV)
              for d, tok, _ in sets]
        outs = [p.communicate(timeout=240)[0].decode("utf-8", "replace") for p in ps]
        got = []
        for text in outs:
            res = None
            for line in reversed(text.splitlines()):
                if line.startswith("RESULT: "):
                    res = json.loads(line[8:])
                    break
            got.append(res or {"state": "no result", "out": text[-300:]})
        bases = sorted(str(g.get("base")) for g in got)
        check(f"round {round_no}: two commits at the same moment both go in, as \"{name}\" and \"{name} (2)\"",
              [p.returncode for p in ps] == [0, 0] and [g.get("state") for g in got] == ["done", "done"] and bases == [name, f"{name} (2)"], got)
        right = [in_carousel(kit, g.get("base") or "", slides) for g, (_, _, slides) in zip(got, sets)]
        check(f"round {round_no}: each set's files are that design's own slides, none mixed or lost", all(ok for ok, _ in right), right)
        rec = kit_mod.load_rec(kit)
        toks = {x.get("token") for x in rec.get("laid_out") or [] if isinstance(x, dict)}
        check(f"round {round_no}: the kit's record has both saves (neither wrote over the other)", {t for _, t, _ in sets} <= toks, sorted(toks)[-4:])


# ---------------------------------------------------------------- 10: the locks across programs
HOLD_LOCK = ("import sys, time; sys.path.insert(0, sys.argv[1]); import kit as kit_mod; from pathlib import Path\n"
             "with kit_mod._held(Path(sys.argv[2]), 5.0) as mine:\n"
             "    Path(sys.argv[3]).write_text('yes' if mine == 'held' else str(mine), encoding='utf-8')\n"
             "    time.sleep(float(sys.argv[4]))\n")


def lock_checks(kit):
    counter = work / "design-counter.txt"
    counter.write_text("0", encoding="utf-8")
    bump = ("import sys, os; sys.path.insert(0, sys.argv[1]); import arrange, design; from pathlib import Path\n"
            "kit, c = Path(sys.argv[2]), Path(sys.argv[3])\n"
            "for _ in range(40):\n"
            "    with arrange.locked(design.design_lock(kit)):\n"
            "        n = int(c.read_text(encoding='utf-8')); c.write_text(str(n + 1), encoding='utf-8')\n")
    ps = [subprocess.Popen([sys.executable, "-c", bump, str(SCRIPTS), str(kit), str(counter)], env=ENV) for _ in range(4)]
    codes = [p.wait(timeout=240) for p in ps]
    check("4 processes x 40 bumps under the design lock give 160", codes == [0] * 4 and counter.read_text(encoding="utf-8") == "160",
          f"{codes} {counter.read_text(encoding='utf-8')}")
    d = first_design(kit)
    save(kit, d["id"], name="Busy")
    d = design.load_design(kit, d["id"])
    tok = token()
    slides = slides_for(d, "busy")
    stage(kit, d, tok, slides)
    ready = work / f"lock-{time.time_ns()}.txt"
    p = subprocess.Popen([sys.executable, "-c", HOLD_LOCK, str(SCRIPTS), str(kit / ".kit" / "slides.lock"), str(ready), "30"], env=ENV)
    real_wait = kit_mod.SLIDES_WAIT
    try:
        end = time.time() + 30
        while not ready.exists() and time.time() < end:
            time.sleep(0.05)
        said = ready.read_text(encoding="utf-8") if ready.exists() else "never"
        if said != "yes":
            skip("a save while another program holds the slides lock", f"this drive has no such locks here ({said})")
            return
        before = snap(kit)
        kit_mod.SLIDES_WAIT = 1.0
        res = design.commit(kit, d["id"], tok, d["rev"])
        check("a save while another program holds the slides lock: \"busy\", in plain words", res.get("state") == "problem"
              and res.get("why") == "busy" and res.get("words") == design.BUSY, res)
        check("clearing the waiting slides meanwhile is refused too (tidy says it could not look)", design.tidy(kit, 0.0, wait=0.3) is None)
        after = snap(kit)
        check("and nothing in the kit was changed (every file byte for byte)", after == before,
              sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))[:5])
    finally:
        kit_mod.SLIDES_WAIT = real_wait
        p.kill()                                  # no clean let-go: the computer lets go of a dead program's lock
        p.wait(timeout=30)
    end = time.time() + 20
    res = {}
    while time.time() < end:
        res = design.commit(kit, d["id"], tok, d["rev"])
        if res.get("why") != "busy":
            break
        time.sleep(0.3)
    ok, why = in_carousel(kit, res.get("base") or "", slides) if res.get("state") == "done" else (False, res)
    check("once that program is gone (killed outright), the same save goes in", ok and res.get("base") == "Busy", why or res)


# ---------------------------------------------------------------- 11: how long a path may be on a PC
PC_TEMP = 97            # how long ...\Your Content is on a PC's own scratch folder; a Mac's lengths are counted from it


class FakeHandler:
    """Just enough of a request for design._get_state: where the answer goes."""
    def __init__(self):
        self.status, self.body, self.headers = None, b"", {}
        self.wfile = self

    def send_response(self, code):
        self.status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def write(self, data):
        self.body += data


def long_checks(kit):
    if not WINDOWS:
        check("a Mac has no such limit: nothing is measured, nothing refused", design.cant_save(kit, "L" * 80) is None and design.too_deep(kit) is None)
    real = (tc.WINDOWS, tc.path_too_long, tc.records_path_too_long, list(tc._LONG_PATHS))
    here = len(str(CONTENT))
    room = (here if WINDOWS else PC_TEMP)
    if 165 - room - 1 < 12:
        skip("how long a path may be", f"this computer's scratch folder is already {here} characters deep")
        return
    name_kit = make_kit("N" + "a" * (165 - room - 2))          # ...\Your Content\<this> is 165 characters
    deep_kit = make_kit("D" + "e" * (200 - room - 2))          # and this one 200
    d = first_design(name_kit)
    save(name_kit, d["id"], name="Short")
    d = design.load_design(name_kit, d["id"])
    tok = token()
    slides = slides_for(d, "long")
    staged_short, _ = stage(name_kit, d, tok, slides)           # staged while the name is short
    if WINDOWS:
        pretend = "the lengths are real"
        if tc.long_paths_on():
            tc._LONG_PATHS[:] = [False]
            pretend += "; long paths are on here, so 'off' is pretended for the designer's own files"
    else:
        shift = PC_TEMP - here

        def as_on_a_pc(path, folder=False):
            return len(str(path)) + shift > (tc.WINDOWS_FOLDER_LIMIT if folder else tc.WINDOWS_FILE_LIMIT)

        tc.WINDOWS, tc.path_too_long, tc.records_path_too_long = True, as_on_a_pc, as_on_a_pc
        pretend = "a Mac: the PC's side switched on for these calls alone, lengths counted as from a PC's scratch folder"
    print(f"      ({pretend})", flush=True)
    try:
        check("a kit 165 characters deep is not too deep for the designer's own files", design.too_deep(name_kit) is None, design.too_deep(name_kit))
        check("a short design name fits there", design.cant_save(name_kit, "Short") is None, design.cant_save(name_kit, "Short"))
        long_name = "L" * 80
        cant = design.cant_save(name_kit, long_name)
        check("an 80-letter name would put a slide past 260 characters: said in plain words, with the fix",
              bool(cant) and cant[0] == "long" and "260 characters" in cant[1] and "shorter name" in cant[1]
              and tc.COMPUTER in cant[1] and "\\" not in cant[1] and str(work) not in cant[1], cant)
        # the design is renamed to the long name (a page's save), then its slides are sent
        real_w = tc.WINDOWS
        tc.WINDOWS = real[0]                      # the save itself takes this computer's own kind of lock
        code, _ = save(name_kit, d["id"], name=long_name)
        tc.WINDOWS = real_w
        d2 = design.load_design(name_kit, d["id"])
        before = snap(name_kit)
        tok2 = token()
        got = design.stage_slide(name_kit, d2["id"], tok2, 1, len(slides), slides[0])
        check("the first slide of such a save is refused BEFORE anything is staged (409, why 'long', the plain words)",
              code == 200 and got[0] == 409 and got[1].get("why") == "long" and got[1].get("words") == cant[1], got)
        check("nothing was staged and nothing in the kit changed", not (design.staging_dir(name_kit) / f"{d2['id']}-{tok2}").exists()
              and snap(name_kit) == before)
        if staged_short:
            # slides that arrived while the name was short: the page's commit, and the command, refuse them too
            code2, out2 = design._post_commit({"kit": name_kit.name, "design": d2["id"], "set": tok, "rev": d2["rev"], "count": len(slides)})
            check("slides staged before the name grew: the page's commit is refused in the same words, nothing started",
                  code2 == 409 and out2.get("why") == "long" and out2.get("words") == cant[1] and snap(name_kit) == before, (code2, out2))
            if WINDOWS:
                res = design.commit(name_kit, d2["id"], tok, None)
                check("and so is the command (design.py commit with no --rev), before anything is written down or moved",
                      res.get("state") == "problem" and res.get("why") == "long" and not (name_kit / "Carousel").exists()
                      and not design._journal_path(name_kit, d2["id"], tok).exists(), res)
            else:
                skip("the command's own refusal (design.commit) for a name grown too long",
                     "it takes the slides lock first, which on a Mac can only be the Mac's own; run for real on a PC")
        # the kit too deep for the designer's own files
        words = design.too_deep(deep_kit)
        check("a kit 200 characters deep is too deep for the designer's own hidden files: plain words, no path",
              bool(words) and "260 characters" in words and tc.COMPUTER in words and "\\" not in words and str(work) not in words, words)
        before = snap(deep_kit)
        code, out = design.new_design(deep_kit, token=token("n"))
        check("no design is made there (409, why 'deep')", code == 409 and out.get("why") == "deep" and out.get("words") == words, (code, out))
        code, out = design.save_from_page({"kit": deep_kit.name, "design": "d" + "0" * 12, "page": PAGE, "base": 0,
                                           "stamp": arrange.sheet_stamp(deep_kit), "state": {"slides": 2, "bg": "#ffffff", "blocks": []}})
        check("no save is taken there", code == 409 and out.get("why") == "deep", (code, out))
        h = FakeHandler()
        design._get_state(h, {"kit": [deep_kit.name]})
        try:
            told = json.loads(h.body.decode("utf-8"))
        except ValueError:
            told = {}
        check("the page's first look is told the same, and makes nothing", h.status == 409 and told.get("words") == words, (h.status, told))
        check("nothing was written into that kit: no designs folder, every file as it was",
              not design.designs_dir(deep_kit).exists() and snap(deep_kit) == before)
    finally:
        tc.WINDOWS, tc.path_too_long, tc.records_path_too_long = real[0], real[1], real[2]
        tc._LONG_PATHS[:] = real[3]
    # and with the limit out of the way again (a Mac), or a short name (a PC), the same kit saves
    tc.WINDOWS = real[0]
    code, _ = save(name_kit, d["id"], name="Short again")
    d3 = design.load_design(name_kit, d["id"])
    res, slides3 = save_set(name_kit, d3, "short again")
    ok, why = in_carousel(name_kit, res.get("base") or "", slides3) if res.get("state") == "done" else (False, res)
    check("with a short name again, the same deep kit saves its slides", code == 200 and ok and res.get("base") == "Short again", why or res)


# ---------------------------------------------------------------- 12: the real page server
def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def server_checks(kit):
    port = PORT or free_port()
    url_file = STUDIO / "posting-url.txt"
    log_path = work / "posting server.log"
    log = open(log_path, "wb")
    srv = tc.popen_detached([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=ENV)
    try:
        said, t0 = "", time.monotonic()
        while time.monotonic() - t0 < 40 and srv.poll() is None:
            try:
                said = url_file.read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            if said:
                break
            time.sleep(0.2)
        if not check("the page server starts and says its address", bool(said) and srv.poll() is None,
                     log_path.read_bytes().decode("utf-8", "replace")[-400:]):
            return
        port = int(said.split("127.0.0.1:")[1].split("/")[0])
        bodies = []

        def ask(method, path, body=None, headers=None, timeout=120):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
            try:
                c.request(method, path, body=body, headers=headers or {})
                resp = c.getresponse()
                data = resp.read()
                bodies.append((method + " " + path.split("?")[0], data))
                return resp.status, {k.lower(): v for k, v in resp.getheaders()}, data
            finally:
                c.close()

        def post(path, obj=None, raw=None, headers=None, kind="application/json"):
            h = {"Content-Type": kind}
            h.update(headers or {})
            code, _, data = ask("POST", path, body=raw if raw is not None else json.dumps(obj).encode("utf-8"), headers=h)
            try:
                return code, json.loads(data)
            except ValueError:
                return code, {}

        Q = "kit=" + quote(kit.name)
        code, _, data = ask("GET", "/design-state?" + Q)
        try:
            st = json.loads(data)
        except ValueError:
            st = {}
        check("GET /design-state through the server: the shoot's design", code == 200 and st.get("ok") and st.get("kit") == kit.name, (code, data[:200]))
        if not st.get("ok"):
            return
        ok, bad = no_path(st)
        check("and nothing in it is a path: no backslash, nothing of the scratch folder", ok and str(work).encode("utf-8") not in data
              and b"\\\\" not in data, bad)
        did, rev, stamp, state, n = st["design"]["id"], st["design"]["rev"], st["stamp"], st["design"]["state"], st["design"]["state"]["slides"]
        good = {"kit": kit.name, "design": did, "page": PAGE, "base": rev, "stamp": stamp, "state": state}
        slide = jpeg(W, H, 11, "a refused slide")
        tok = token()
        sq = f"/design-slide?{Q}&design={did}&set={tok}"
        (STUDIO / "design-templates").mkdir(exist_ok=True)
        before_kit, before_studio = snap(kit), {k: v for k, v in snap(STUDIO).items() if k.startswith(("design-", "brand"))}
        other_state = dict(state, bg="#123456")
        refusals = [
            ("a save sent to another name for this computer (Host)", lambda: post("/design", good, headers={"Host": "evil.example"}), 403),
            ("a save from another website (Origin)", lambda: post("/design", good, headers={"Origin": "http://evil.example"}), 403),
            ("a save that is not JSON by its type", lambda: post("/design", good, kind="text/plain"), 415),
            ("a save larger than a save may be", lambda: post("/design", raw=b"{" + b" " * 300000 + b"}"), 413),
            ("a save that is not JSON at all", lambda: post("/design", raw=b"not json"), 400),
            ("a save for a shoot that is not there", lambda: post("/design", dict(good, kit="No such shoot")), 404),
            ("a save whose shoot is a path with ..", lambda: post("/design", dict(good, kit="../" + kit.name)), 404),
            ("a save whose shoot is this kit's full address", lambda: post("/design", dict(good, kit=str(kit))), 404),
            ("a save whose shoot is a PC address", lambda: post("/design", dict(good, kit="C:\\Users\\Public\\" + kit.name)), 404),
            ("a save whose shoot is another computer's shared folder", lambda: post("/design", dict(good, kit="\\\\server\\share\\" + kit.name)), 404),
            ("a save whose design is a path", lambda: post("/design", dict(good, design="../" + did, state=other_state)), 400),
            ("a save for photos that have changed", lambda: post("/design", dict(good, stamp="000000000000", state=other_state)), 409),
            ("a save from a page that has not seen the newest", lambda: post("/design", dict(good, base=rev + 5, state=other_state)), 409),
            ("a save with 99 slides", lambda: post("/design", dict(good, state=dict(state, slides=99))), 400),
            ("a save with a 200-letter name", lambda: post("/design", dict(good, name="N" * 200)), 400),
            ("a new design with a made-up token", lambda: post("/design-new", {"kit": kit.name, "token": "BAD TOKEN"}), 400),
            ("a copy of a design named by a path", lambda: post("/design-new", {"kit": kit.name, "copy": "../../x"}), 400),
            ("a template with no name", lambda: post("/design-template", {"kit": kit.name, "name": "", "state": state}), 400),
            ("a brand color that is not one", lambda: post("/design-brand", {"add": "red"}), 400),
            ("a font name that is a path", lambda: post("/design-font", {"add": "../../etc/passwd"}), 400),
            ("a slide that is not a picture", lambda: post(f"{sq}&i=1&of={n}", raw=b"x" * 5000, kind="image/jpeg"), 400),
            ("slide 3 of 2", lambda: post(f"/design-slide?{Q}&design={did}&set={tok}&i=3&of=2", raw=slide, kind="image/jpeg"), 400),
            ("a slide for a design that is not there", lambda: post(f"/design-slide?{Q}&design=d00000000000&set={tok}&i=1&of={n}", raw=slide, kind="image/jpeg"), 404),
            ("a slide for a different number of slides", lambda: post(f"{sq}&i=1&of={n + 1 if n < 20 else n - 1}", raw=slide, kind="image/jpeg"), 409),
            ("a slide whose set is a path", lambda: post(f"/design-slide?{Q}&design={did}&set=..%2F..%2Fx&i=1&of={n}", raw=slide, kind="image/jpeg"), 400),
            ("a commit of slides that never arrived", lambda: post("/design-commit", {"kit": kit.name, "design": did, "set": token(), "rev": rev, "count": n}), 400),
            ("a commit for a design changed since", lambda: post("/design-commit", {"kit": kit.name, "design": did, "set": token(), "rev": rev + 3, "count": n}), 409),
            ("a commit that is not one", lambda: post("/design-commit", {"kit": kit.name, "design": did, "set": "x", "rev": "1"}), 400),
            ("a designer route that does not exist", lambda: post("/design-nothing", {"kit": kit.name}), 404),
        ]
        for what, send, want in refusals:
            try:
                code, out = send()
            except OSError as e:
                code, out = None, repr(e)
            check(f"refused: {what} ({want})", code == want, (code, out))
        code, _, data = ask("GET", "/design-state?kit=No%20such%20shoot")
        check("refused: the state of a shoot that is not there (404)", code == 404, (code, data[:120]))
        code, _, data = ask("GET", "/design-state?" + Q, headers={"Sec-Fetch-Site": "cross-site"})
        check("refused: the state asked for by another website through the browser (403)", code == 403, (code, data[:120]))
        code, _, data = ask("GET", "/design-state?" + Q, headers={"Host": "evil.example"})
        check("refused: the state asked for under another name for this computer (403)", code == 403, code)
        for bad in ("../../../.kit/kit.json", "Inter-Regular.ttf", "..%5C..%5Ckit", "C:%5CWindows%5Cwin.ini", ""):
            code, _, data = ask("GET", "/design-font-file?f=" + bad)
            check(f"refused: a font file named {bad!r} (404)", code == 404, code)
        code, _, data = ask("GET", "/design.html?kit=No%20such%20shoot")
        check("a shoot that is not there gets the small page with the way home, not the designer",
              code == 200 and b"Is the drive plugged in?" in data and b"d-tools" not in data, (code, data[:200]))
        after_kit, after_studio = snap(kit), {k: v for k, v in snap(STUDIO).items() if k.startswith(("design-", "brand"))}
        check("after every refusal, every file of the kit is byte for byte what it was", after_kit == before_kit,
              sorted(k for k in set(before_kit) | set(after_kit) if before_kit.get(k) != after_kit.get(k))[:6])
        check("and so are the templates, the brand colors and the font list", after_studio == before_studio,
              sorted(set(before_studio) ^ set(after_studio))[:6])
        leaked = [what for what, data in bodies if what.split(" ")[1].startswith("/design") and (str(work).encode("utf-8") in data or work.name.encode("utf-8") in data)]
        check("no answer of a designer route gave away where anything is on this computer", not leaked, leaked[:4])
        # the plugin's own font, as a font
        own = next((f for f in design.OWN_FILES if (FONTS / f"{f}.ttf").is_file()), None)
        if own:
            code, heads, data = ask("GET", "/design-font-file?f=" + own)
            check("the plugin's own font file is served as a font (font/ttf), byte for byte",
                  code == 200 and heads.get("content-type") == "font/ttf" and data == (FONTS / f"{own}.ttf").read_bytes(), (code, heads.get("content-type"), len(data)))
        else:
            skip("the plugin's own font file is served as a font", "this copy of the plugin carries no font files")
        # one save through the server: its commit is a process the server starts itself (no window on a PC)
        code, out = post("/design", dict(good, name="Through the server ✓", state=other_state))
        check("a save through the server", code == 200 and out.get("ok"), (code, out))
        rev2 = out.get("rev", rev)
        slides = [jpeg(W, H, i * 2, f"server slide {i}") for i in range(1, n + 1)]
        tok = token()
        codes = [post(f"/design-slide?{Q}&design={did}&set={tok}&i={i}&of={n}", raw=s, kind="image/jpeg")[0] for i, s in enumerate(slides, 1)]
        check("its slides are taken in", codes == [200] * n, codes)
        code, out = post("/design-commit", {"kit": kit.name, "design": did, "set": tok, "rev": rev2, "count": n})
        ok, why = in_carousel(kit, out.get("base") or "", slides) if code == 200 and out.get("ok") else (False, (code, out))
        check("Save slides through the server: the commit it starts itself puts the set in, byte for byte",
              ok and out.get("base") == design.safe_base("Through the server ✓"), why or out)
        ok, bad = no_path(out)
        check("and its answer holds no path", ok, bad)
        code, _, data = ask("GET", "/open?" + Q + "&sub=Nothing")
        try:
            told = json.loads(data)
        except ValueError:
            told = {}
        check("the folder button's route refuses a folder the kit does not name, in words with no path (nothing is opened)",
              code == 200 and told.get("ok") is False and "\\" not in told.get("words", "") and "/" not in told.get("words", ""), (code, told))
    finally:
        srv.terminate()
        try:
            srv.wait(15)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(15)
        log.close()
    check("the page server is stopped", srv.poll() is not None)


def stories_checks(kit):
    st = design.state_for_page(kit, kind="stories")
    check("stories: the page is given the shoot's one stories design, empty, white, 1080 x 1920", bool(st) and st["design"]["state"] == {"slides": 1, "bg": "#ffffff", "blocks": []}
          and st["limits"]["h"] == 1920 and st["kind"] == "stories", st and st.get("design"))
    ok, bad = no_path(st)
    check("stories: no path, no backslash and nothing of the scratch folder in what the page is given", ok, bad)
    check("stories: the preview's name is \"yourname\" (no handle known)", st["handle"] == "yourname")
    code, out = design.new_design(kit, kind="stories")
    check("stories: a second stories design is refused", code == 409 and out.get("why") == "one", (code, out))
    did = st["design"]["id"]
    d = design.load_design(kit, did, "stories")
    state = {"slides": 3, "bg": "#ffffff", "blocks": [
        {"id": 1, "n": 1, "x": 0, "y": 0, "w": 1080, "h": 1920, "ox": 0.5, "oy": 0.5, "zoom": 1},
        {"id": 2, "type": "text", "text": "Zoë’s day 🌊", "font": "Figtree", "size": 72, "weight": 700, "italic": False, "upper": False, "al": "center",
         "ls": 0, "lh": 1.3, "color": "#111111", "x": 130, "y": 806.4, "w": 820, "h": 93.6, "look": "box", "boxColor": "#ffffff"}]}
    body = {"kit": kit.name, "kind": "stories", "design": did, "page": PAGE, "base": d["rev"], "stamp": arrange.sheet_stamp(kit), "state": state, "name": "CON"}
    code, out = design.save_from_page(body)
    check("stories: a story's layout and a name Windows keeps for itself are saved; its text keeps its look", code == 200
          and design.load_design(kit, did, "stories")["state"]["blocks"][1]["look"] == "box", (code, out))
    d = design.load_design(kit, did, "stories")
    tok = token()
    code, out = design.stage_slide(kit, did, tok, 1, 3, jpeg(1080, 1350, level=3, note="a carousel slide"), "stories")
    check("stories: a carousel's 1080 x 1350 slide is refused as a story", code == 400, (code, out))
    sent = [jpeg(1080, 1920, level=i * 4, note=f"story {i}") for i in (1, 2, 3)]
    codes = [design.stage_slide(kit, did, tok, i, 3, data, "stories")[0] for i, data in enumerate(sent, 1)]
    res = design.commit(kit, did, tok, d["rev"], kind="stories")
    base = res.get("base") or ""
    folder = kit / "Stories"
    listed = {unicodedata.normalize("NFC", n) for n in os.listdir(folder)} if folder.is_dir() else set()
    names = [design.STORY_SET_NAME.format(base=base, i=i) for i in (1, 2, 3)]
    check("stories: the set goes into the Stories folder under a name this computer takes (\"CON\" made safe), byte for byte",
          codes == [200] * 3 and res["state"] == "done" and base == tc.safe_name("CON", limit=80) and all(unicodedata.normalize("NFC", n) in listed for n in names)
          and all(file_sha(folder / n) == sha(x) for n, x in zip(names, sent)), (codes, res, sorted(listed)[:6]))
    rec = kit_mod.load_rec(kit)
    shown = kit_mod.stories_shown(kit)
    check("stories: the kit's record names the set, and kit.stories_shown shows it", rec.get("stories_set", {}).get("base") == base and [p.name for p in shown["files"]] == names
          and "carousel_set" not in rec, (rec.get("stories_set"), shown))
    jfiles = list(design.sets_dir(kit, "stories").glob("*.json"))
    check("stories: the save's record holds no path and no backslash", jfiles and all("\\" not in f.read_text(encoding="utf-8") and str(work) not in f.read_text(encoding="utf-8") for f in jfiles))
    code, out = design.save_from_page(dict(body, base=design.load_design(kit, did, "stories")["rev"], state=dict(state, bg="#111111")))
    d = design.load_design(kit, did, "stories")
    tok = token()
    for i, data in enumerate(sent, 1):
        design.stage_slide(kit, did, tok, i, 3, data, "stories")
    res2 = design.commit(kit, did, tok, d["rev"], kind="stories")
    check("stories: a second set after a change is \"<name> (2)\", and the first is untouched", res2.get("base") == base + " (2)"
          and all(file_sha(folder / n) == sha(x) for n, x in zip(names, sent)), res2)
    if not WINDOWS:
        check("stories: a Mac has no length limit for a story either", design.cant_save(kit, "L" * 80, kind="stories") is None)
    else:
        cant = design.cant_save(kit, "L" * 80, kind="stories")
        check("stories: on a PC a long name is measured in the Stories folder, said in a story's words (or fits)", cant is None or ("stor" in cant[1] and "slide" not in cant[1]), cant)


def v22_checks(kit):
    st = design.state_for_page(kit)
    check("v22: the page is given the eleven starters (her five first) and her eight single slides, no words in any, no path",
          [t["id"] for t in st["starters"]][:5] == ["tp-postcard", "tp-layered", "tp-overlay-frames", "tp-seam-editorial", "tp-gallery"] and len(st["starters"]) == 11
          and [t["id"] for t in st["singles"]] == ["cs-border", "cs-2t", "cs-three", "cs-4", "cs-9", "cs-mosaic", "cs-mood", "cs-overlap"]
          and not any(b.get("type") == "text" for t in st["starters"] + st["singles"] for b in t["template"]["blocks"]) and no_path(st)[0],
          [t["id"] for t in st["starters"]])
    state = {"slides": 2, "bg": "#f4efe6", "blocks": [{"id": 1, "n": 1, "x": 0, "y": 0, "w": 1080, "h": 1350, "ox": 0.5, "oy": 0.5, "zoom": 1},
                                                      {"id": 2, "n": 2, "x": 1170, "y": 110, "w": 900, "h": 1130, "ox": 0.5, "oy": 0.5, "zoom": 1}]}
    code, out = design.save_template("Beach", state, "Zoë’s beach 🌊", token("t"))
    tid = out.get("template", {}).get("id")
    f = design.TEMPLATES / f"{tid}.json"
    first = f.read_bytes() if tid else b""
    check("v22: a template of their own is saved", code == 200 and bool(tid), (code, out))
    code, out = design.rename_template(tid, "Zoë’s days 🌊: CON / aux?")
    now = json.loads(f.read_text(encoding="utf-8"))
    prev = design.template_prev_path(tid)
    check("v22: Rename with an accent, an emoji and characters a PC refuses in a file's name: the name is only ever inside the file, so it is kept as typed",
          code == 200 and out["template"]["name"] == "Zoë’s days 🌊: CON / aux?" and now["name"] == "Zoë’s days 🌊: CON / aux?" and now["template"] == json.loads(first)["template"], (code, out))
    check("v22: Rename: the version before is kept beside it, byte for byte, and is not listed as a template", prev.is_file() and prev.read_bytes() == first
          and [t["id"] for t in design.list_templates()].count(tid) == 1 and len(design.list_templates()) == 1)
    check("v22: Rename: no scratch file is left in the templates folder", sorted(os.listdir(design.TEMPLATES)) == sorted([f.name, prev.name]), sorted(os.listdir(design.TEMPLATES)))
    ok, bad = no_path(out)
    check("v22: Rename: no path and no backslash in the answer", ok, bad)
    good = f.read_bytes()
    for what, args, want in (("half of an emoji", (tid, "\ud83c"), 400), ("an empty name", (tid, "  "), 400), ("81 letters", (tid, "x" * 81), 400),
                             ("an id with a backslash", ("..\\" + str(tid), "A"), 400), ("an id with a drive letter", ("C:" + str(tid), "A"), 400),
                             ("a template that is not there", ("t" + "z" * 12, "A"), 404)):
        code, out = design.rename_template(*args)
        check(f"v22: Rename refused ({what}), and the template is as it was", code == want and out.get("ok") is False and f.read_bytes() == good, (code, out))
    # while another program has the template's file open (a PC waits a moment; a Mac never minds)
    with open(f, "rb"):
        try:
            code, out = design.rename_template(tid, "Held open")
        except OSError as e:
            code, out = 0, {"err": str(e)[:80]}
    name_now = json.loads(f.read_text(encoding="utf-8"))["name"]
    check("v22: Rename while another program reads the template's file: it is renamed, or left whole as it was (never half written)",
          (code == 200 and name_now == "Held open") or name_now == "Zoë’s days 🌊: CON / aux?", (code, out, name_now))


def part(name, fn, *args):
    """One part; a fault in it FAILs here and never stops the parts after it."""
    print(f"\n-- {name}", flush=True)
    try:
        fn(*args)
    except Exception as e:  # noqa: BLE001
        import traceback
        check(f"{name}: ran to the end", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-900:]}")


part("1: the slides this test sends are real", jpeg_checks)
KIT = make_kit("2026-11-01 Zoë’s beach 🌊")
part("2: what the page is given", state_checks, KIT)
part("3: a design saved while its file is open", held_design_checks, KIT)
part("4: names", name_checks, make_kit("2026-11-02 Names"))
part("5: staging and a save, start to finish", commit_checks, make_kit("2026-11-03 Whole"))
part("6: the commit as a process of its own, in an old code page", child_checks, KIT)
part("7: a save while a slide is held open by another program", held_slide_checks, make_kit("2026-11-04 Held"))
part("8: a drive with no hard links", no_links_checks, make_kit("2026-11-05 No links"))
part("9: two saves at the same moment, from two processes", race_checks, make_kit("2026-11-06 Twins"))
part("10: the locks across programs", lock_checks, make_kit("2026-11-07 Locks"))
part("11: how long a path may be on a PC", long_checks, KIT)
part("12: the real page server: refusals change nothing, a save goes through", server_checks, make_kit("2026-11-08 Server"))
part("13: the stories designer", stories_checks, make_kit("2026-11-09 Zoë’s stories 🌊"))
part("14: Nicole's v22: her starters and single slides, and Rename on a template", v22_checks, make_kit("2026-11-10 Rename"))

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
