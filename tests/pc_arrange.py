#!/usr/bin/env python3
"""The photo pickers' own machinery (arrange.py) on a PC, tried for real: written to run on GitHub's Windows
machine, and on a Mac.

    python tests/pc_arrange.py
    ASSISTANT_NO_SIPS=1 python3 tests/pc_arrange.py     on a Mac: the PC's way of making pictures (Pillow), so
                                                        parts 9 and 11 run there too
    ASSISTANT_SCRIPTS=<folder>                          try the scripts in another folder (a copy with a fault
                                                        put in, to see a check FAIL)

tests/arrange_check.py is the full test of the pickers, but it needs a Mac (sips, osascript). This one tries the
parts of arrange.py that work differently on a PC, in a scratch folder it makes itself (STUDIO_HOME points there;
nothing else is touched, no port is used, nothing is deleted outside that folder):
  1. the small copies (make_previews) from photos drawn here with Pillow: counts, sizes (never larger than the
     photo), a photo shot sideways comes out the right way up, a second run makes nothing new;
  2. an iPhone photo (HEIC) a PC can't open without its add-on (pillow-heif): no ".failed" mark, the add-on's
     words, and the page state calls it "can't be shown" (a Mac, or a PC with the add-on: a real mark);
  3. a photo that really can't be read gets its mark, and is not tried again on the next run;
  4. one writer at a time across processes: 4 processes x 50 bumps of one counter under arrange.locked() = 200;
  5. "is a slide job still at work?" (job_running) while another process holds the job's lock, after it lets go,
     and after it is killed outright; and _pid_alive for this process and for one that has ended;
  6. a previews child started by a process that ends at once still finishes its work (popen_detached);
  7. a record saved (write_whole) while another handle has it open for reading;
  8. a kit too deep in folders for Windows' 260 characters (long paths off): plain words, nothing made or marked.
     Skipped where long paths are on, and on a Mac (no such limit).
  9. a new copy something holds (the virus checker) for longer than this_computer.replace waits: on a PC it is
     "later" (no mark, tried again a moment on, made then or left for the next run), at either of the two places
     a copy is put in place (pictures.make_jpeg's own step and arrange's last one); a Mac raises it, as before.
     Run on the PC way of making pictures only (a PC, or a Mac with ASSISTANT_NO_SIPS=1, where the PC's side of
     arrange is switched on for these calls alone); the refusal itself is pretended (this_computer.replace).
 10. a background run's output on a PC: Windows hands the run the server's handle with no "add at the end" of
     its own, so a run that writes through it writes over lines the server added meanwhile. Shown with such a
     handle (made the same way on a Mac), and shown put right by arrange._own_output.
 11. a kit's drive that is full when copies come back "later" (a PC only): said so ("full"), no waiting, no mark.
     Run the same way as 9; the full drive itself is pretended (this_computer.free_bytes).
 12. (inside 1 to 3) a computer that can't make pictures right now: photos whose two page copies are there still
     count as there; and (inside 9) the designer's larger copy held at its last step is tried again (big_copy).
Parts 1 to 3, 6, 9 and 11 draw photos with Pillow (the PC's one add-on); without it they say SKIP and why, and the
rest (the lock, the job check, saving a record, a background run's lines) still runs, as on a Mac's own Python 3.9.
Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept (its place is
printed), and cleared away when everything passed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("ASSISTANT_SCRIPTS") or ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts")
WINDOWS = os.name == "nt"
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{detail}]" if detail and not ok else ""), flush=True)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


try:
    from PIL import Image, ImageOps
    HAVE_PIL = True
except Exception:  # noqa: BLE001
    HAVE_PIL = False
NO_PIL = "Pillow is not installed for this Python (python -m pip install pillow); this part draws its photos with it"

work = Path(tempfile.mkdtemp(prefix="assistant pc arrange "))
STUDIO = work / "studio"
STUDIO.mkdir()
os.environ["STUDIO_HOME"] = str(STUDIO)           # before arrange is imported: it reads STUDIO_HOME then
ENV = dict(os.environ)
sys.path.insert(0, str(SCRIPTS))
import this_computer  # noqa: E402
import pictures  # noqa: E402
import arrange  # noqa: E402

this_computer.utf8_output()
print(f"This is a {this_computer.COMPUTER}, Python {sys.version.split()[0]}" + (", with Pillow" if HAVE_PIL else ", no Pillow")
      + f"; small pictures made {'the Mac way (sips)' if pictures.use_sips() else 'the PC way (Pillow)'}.\n", flush=True)
HOME = work / "The Assistant"
r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--home", str(HOME)], capture_output=True,
                   encoding="utf-8", errors="replace", env=ENV)
check("a pretend Assistant folder is set up (posts.py setup)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
CONTENT = HOME / "Your Content"
CONTENT.mkdir(parents=True, exist_ok=True)


def draw(path, w, h, colour, exif6=False):
    """A photo: a colour, with a white band along the top of the picture as it should be SEEN. exif6: stored turned
    (the camera's "shot sideways" note, orientation 6), so only a reader that follows the note shows it upright."""
    im = Image.new("RGB", (w, h), colour)
    im.paste((255, 255, 255), (0, 0, w, max(8, h // 12)))
    if exif6:
        stored = im.transpose(Image.ROTATE_90)          # orientation 6 turns it back (ROTATE_270) when shown
        ex = Image.Exif()
        ex[0x0112] = 6
        stored.save(path, "JPEG", quality=90, exif=ex.tobytes())
    else:
        fmt = {".png": "PNG", ".tif": "TIFF"}.get(path.suffix.lower(), "JPEG")
        im.save(path, fmt, **({"quality": 90} if fmt == "JPEG" else {}))
    return w, h


def bare_kit(name):
    """A kit folder with only its records (no photos): enough for the locks, the job check and saving a record,
    so those run on a computer without Pillow too."""
    kit = CONTENT / name
    (kit / ".kit").mkdir(parents=True)
    rec = {"name": name, "date": "2026-11-01", "folder": name, "source": "drop", "photos": []}
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    return kit


def make_kit(name):
    """A kit folder in Your Content with N photos, kit.json and sheet.json written by hand (the shapes kit.py
    writes), so this test does not lean on kit.py's own numbering."""
    kit = CONTENT / name
    (kit / ".kit").mkdir(parents=True)
    photos = kit / "Photos"
    photos.mkdir()
    specs = [("p-001.jpg", 1200, 1800, (200, 60, 40), False), ("p-002.jpg", 1800, 1200, (40, 160, 60), False),
             ("p-003.png", 1400, 1400, (60, 60, 200), False), ("p-004-small.jpg", 300, 450, (120, 120, 0), False),
             ("p-005-sideways.jpg", 800, 1200, (0, 120, 140), True), ("p-006.tif", 1200, 1800, (140, 0, 140), False)]
    rows = []
    for i, (fname, w, h, col, turned) in enumerate(specs, 1):
        draw(photos / fname, w, h, col, turned)
        rows.append({"n": i, "file": str(photos / fname), "w": w, "h": h, "way": "tall" if h > w else ("wide" if w > h else "square")})
    (photos / "p-007.heic").write_bytes(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 200)   # not a real HEIC: can't be read
    rows.append({"n": 7, "file": str(photos / "p-007.heic"), "w": 0, "h": 0, "way": ""})
    (photos / "p-008-broken.jpg").write_bytes(b"\xff\xd8\xff\xe0 this is not a picture")
    rows.append({"n": 8, "file": str(photos / "p-008-broken.jpg"), "w": 1200, "h": 1800, "way": "tall"})
    rec = {"name": name, "date": "2026-11-01", "folder": name, "source": "drop", "photos": sorted(p.name for p in photos.iterdir())}
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    (kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(photos), "photos": rows}, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
    return kit, specs


def shown(p):
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im)
        top = im.getpixel((im.width // 2, 2))
        return im.size, top


# ---------------------------------------------------------------- 1 to 3: the small copies
def copies_checks(kit, specs):
    got = arrange.make_previews(kit, retry=True)
    pc_way = not pictures.use_sips()
    addon_missing = pc_way and not pictures.heic_ok()
    check("make_previews: every drawn photo has both copies", got["made"] == 6 and got["of"] == 8, got)
    check("make_previews: the HEIC and the broken photo are counted as not read", got["failed"] == 2, got)
    prev = arrange.previews_dir(kit)
    names = sorted(p.name for p in prev.iterdir())
    for i, (fname, w, h, _, turned) in enumerate(specs, 1):
        src = kit / "Photos" / fname
        for size in (1600, 520):
            f = arrange.preview_file(kit, {"n": i}, size, src)
            if not f.is_file():
                check(f"photo {i} has its {size} copy", False, names)
                continue
            (sw, sh), top = shown(f)
            want = min(size, max(w, h))
            check(f"photo {i} ({fname}) at {size}: long edge {want}, the right way up", max(sw, sh) == want
                  and (sh > sw) == (h > w) and (sw > sh) == (w > h) and min(top) > 200, f"{sw}x{sh} top {top}")
    heic_mark = arrange.failed_mark(kit, {"n": 7}, 1600, kit / "Photos" / "p-007.heic")
    broken_mark = arrange.failed_mark(kit, {"n": 8}, 1600, kit / "Photos" / "p-008-broken.jpg")
    if addon_missing:
        check("HEIC without its add-on: no mark, so it is tried again once the add-on is there", not heic_mark.exists(), names)
        check("HEIC without its add-on: the add-on's words are given", "pillow-heif" in (got.get("why") or ""), got.get("why"))
    else:
        check("HEIC that can't be read (a Mac, or a PC with the add-on): it gets its mark", heic_mark.exists(), names)
    check("a photo that really can't be read gets its mark", broken_mark.exists(), names)
    check("nothing half-made is left in the previews folder", not [n for n in names if n.startswith(".")], names)
    st = arrange.state_for_page(kit, "reel")
    by_n = {x["n"]: x for x in st["photos"]}
    check("page state: the HEIC and the broken photo are 'can't be shown', the rest are there",
          by_n[7]["missing"] and by_n[8]["missing"] and all(by_n[n]["have"] for n in range(1, 7)), st["photos"])
    check("page state: no path or file name in it", "Photos" not in json.dumps(st) and ".jpg" not in json.dumps(st))
    calls = []
    real_make = pictures.make_jpeg
    pictures.make_jpeg = lambda *a, **k: calls.append(a[0]) or real_make(*a, **k)
    try:
        again = arrange.make_previews(kit)                       # what open and the page do (retry off)
    finally:
        pictures.make_jpeg = real_make
    check("a second run makes nothing and tries no photo again", again["made"] == 0 and again["there"] == 6 and not calls,
          f"{again} tried {calls}")
    # A PC that can't make pictures right now (Pillow gone after a Python update): the photos whose two page copies
    # are already there still count as there. The designer's two larger sizes (2400, 4320) are only made when a
    # finished slide asks for one, so their absence must never turn a ready kit into "needs an add-on".
    real_ready = pictures.ready
    pictures.ready = lambda: (False, "This computer needs one free add-on first.")
    try:
        cant = arrange.make_previews(kit)
    finally:
        pictures.ready = real_ready
    big = [s for s in arrange.SIZES.values() if s > 1600]
    none_big = not any(arrange.preview_file(kit, {"n": i}, s, kit / "Photos" / spec[0]).is_file()
                       for i, spec in enumerate(specs, 1) for s in big)
    check("a computer that can't make pictures right now: photos whose two page copies are there still count as there "
          "(the designer's larger copies are not asked for)", cant["there"] == 6 and cant["made"] == 0 and none_big, f"{cant} big sizes {big}")


# ---------------------------------------------------------------- 4: one writer at a time, across processes
def lock_checks(kit):
    counter = work / "counter.txt"
    counter.write_text("0", encoding="utf-8")
    bump = ("import sys, os; sys.path.insert(0, sys.argv[1]); import arrange; from pathlib import Path\n"
            "kit, c = Path(sys.argv[2]), Path(sys.argv[3])\n"
            "for _ in range(50):\n"
            "    with arrange.locked(arrange.kit_lock(kit)):\n"
            "        n = int(c.read_text(encoding='utf-8')); c.write_text(str(n + 1), encoding='utf-8')\n")
    ps = [subprocess.Popen([sys.executable, "-c", bump, str(SCRIPTS), str(kit), str(counter)], env=ENV) for _ in range(4)]
    codes = [p.wait(timeout=120) for p in ps]
    check("4 processes x 50 bumps under arrange.locked() give 200", codes == [0] * 4 and counter.read_text(encoding="utf-8") == "200",
          f"{codes} {counter.read_text(encoding='utf-8')}")


# ---------------------------------------------------------------- 5: is a job at work?
HOLD = ("import sys, time; sys.path.insert(0, sys.argv[1]); import arrange; from pathlib import Path\n"
        "kit, ready = Path(sys.argv[2]), Path(sys.argv[3])\n"
        "with arrange._job_hold(kit, 3.0) as mine:\n"
        "    ready.write_text('yes' if mine else 'no', encoding='utf-8')\n"
        "    time.sleep(float(sys.argv[4]))\n")


def job_checks(kit):
    def holder(secs):
        ready = work / f"ready-{time.time_ns()}.txt"
        p = subprocess.Popen([sys.executable, "-c", HOLD, str(SCRIPTS), str(kit), str(ready), str(secs)], env=ENV)
        end = time.time() + 30
        while not ready.exists() and time.time() < end:
            time.sleep(0.05)
        return p, ready.read_text(encoding="utf-8") if ready.exists() else "never"

    def settles(want, secs=15.0):        # Windows lets go of a dead program's lock "depending on resources"
        end = time.time() + secs
        while time.time() < end:
            if arrange.job_running(kit) == want:
                return True
            time.sleep(0.1)
        return arrange.job_running(kit) == want

    p, said = holder(2.0)
    check("job_running: True while another process holds the job's lock", said == "yes" and arrange.job_running(kit) is True, said)
    check("job_running: asking does not take the lock away (still True)", arrange.job_running(kit) is True)
    p.wait(timeout=30)
    check("job_running: False once that process has let go and ended", settles(False))
    p, said = holder(60.0)
    try:
        check("job_running: True again under a second holder", said == "yes" and arrange.job_running(kit) is True, said)
    finally:
        p.kill()                                              # TerminateProcess on Windows: no clean let-go
        p.wait(timeout=30)
    check("job_running: False after the holder is killed outright", settles(False))
    check("_pid_alive: this process is alive", arrange._pid_alive(os.getpid()) is True)
    q = subprocess.Popen([sys.executable, "-c", "pass"], env=ENV)
    q.wait(timeout=30)
    time.sleep(0.5)
    check("_pid_alive: a process that has ended is not", arrange._pid_alive(q.pid) is False)


# ---------------------------------------------------------------- 6: a previews child outlives its starter
def child_checks():
    kit2, _ = make_kit("2026-11-02 Second")
    starter = ("import sys; sys.path.insert(0, sys.argv[1]); import arrange; from pathlib import Path\n"
               "print('started' if arrange.start_previews(Path(sys.argv[2])) else 'not started')\n")
    r = subprocess.run([sys.executable, "-c", starter, str(SCRIPTS), str(kit2)], capture_output=True, encoding="utf-8",
                       errors="replace", env=ENV, timeout=60)
    check("start_previews: the starter starts a child and ends at once", r.returncode == 0 and "started" in r.stdout, r.stdout + r.stderr)
    end = time.time() + 90
    have = []
    while time.time() < end:
        have = [p for p in arrange.previews_dir(kit2).glob("*.jpg")] if arrange.previews_dir(kit2).is_dir() else []
        if len(have) >= 12:
            break
        time.sleep(0.5)
    check("the previews child finished its work after its starter had gone (12 copies)", len(have) == 12, len(have))
    log = STUDIO / "arrange.log"
    check("the child's output went to STUDIO_HOME/arrange.log", log.is_file())


# ---------------------------------------------------------------- 7: saving while a reader has the record open
def save_checks(kit):
    target = kit / ".kit" / "arrange.json"
    arrange.write_whole(target, {"v": 1, "x": "before"})
    reader = open(target, "r", encoding="utf-8")
    threading.Timer(0.5, reader.close).start()
    t0 = time.time()
    err = None
    try:
        arrange.write_whole(target, {"v": 1, "x": "after ✓"})
    except OSError as e:
        err = e
    check("write_whole while another handle has the record open: saved (a PC waits a moment)",
          err is None and json.loads(target.read_text(encoding="utf-8"))["x"] == "after ✓", f"{err} after {time.time() - t0:.2f} s")
    check("write_whole leaves no scratch file behind", not [n for n in os.listdir(kit / ".kit") if n.endswith(".tmp")])


# ---------------------------------------------------------------- 8: too deep for Windows' 260 characters
def deep_checks(kit):
    if WINDOWS and not this_computer.long_paths_on():
        if not HAVE_PIL:
            skip("too deep for 260 characters", NO_PIL)
            return
        # a kit folder of 205 characters: its photos (about 26 more) and kit.py's own hidden files (39 more) fit under
        # 260, the copies' marks (about 66 more: .kit\previews\NNNN-1600-<6>-<bytes>-<19 digits>.failed) do not
        name_len = 205 - len(str(CONTENT)) - 1
        deep, _ = make_kit("D" + "e" * max(1, name_len - 1))
        g = arrange.make_previews(deep, retry=True)
        check("too deep: plain words, and nothing made or marked", g.get("cant_kind") == "deep" and g["made"] == 0
              and not arrange.previews_dir(deep).exists() and "260 characters" in (g.get("cant") or ""), g)
    else:
        skip("too deep for 260 characters", "long paths are on here" if WINDOWS else "not a PC")
        check("no such limit here: cant_make says nothing", arrange.cant_make(kit, arrange.sheet_rows(kit)) is None)


# ---------------------------------------------------------------- 9 and 11: a copy something holds ("later"), a full drive
def held_checks():
    real_replace, real_win, real_deep = this_computer.replace, this_computer.WINDOWS, arrange._too_deep
    real_waits, real_free = getattr(arrange, "LATER_WAITS", None), this_computer.free_bytes
    held = {"name": None, "left": 0}

    def holding(src, dst, tries=25):
        """this_computer.replace, with one name refused the way a PC refuses a file another program holds."""
        if held["name"] and held["name"](Path(dst).name) and held["left"] > 0:
            held["left"] -= 1
            raise PermissionError(13, "The process cannot access the file because it is being used by another process")
        return real_replace(src, dst, tries)

    def hold(test, times):
        held["name"], held["left"] = test, times

    def mp(k, **kw):
        """make_previews, with anything it raises turned into a result the checks below can show."""
        try:
            return arrange.make_previews(k, **kw)
        except Exception as e:  # noqa: BLE001
            return {"raised": repr(e)[:200], "made": -1, "failed": -1, "there": -1}

    this_computer.replace = holding
    this_computer.WINDOWS = True            # on a PC already; on a Mac, the PC's side of arrange for these calls alone
    arrange._too_deep = lambda *a, **k: False   # this test's own folders may be deeper than 260 on a Mac
    arrange.LATER_WAITS = (0.2, 0.4)        # the pauses, made short for the test
    try:
        kit3, _ = make_kit("2026-11-03 Held")
        prev3 = arrange.previews_dir(kit3)
        p1 = kit3 / "Photos" / "p-001.jpg"
        p2 = kit3 / "Photos" / "p-002.jpg"

        def marks():
            return sorted(n for n in os.listdir(prev3) if n.endswith(".failed")) if prev3.is_dir() else []

        def scratch():
            return sorted(n for n in os.listdir(prev3) if n.startswith(".")) if prev3.is_dir() else []

        # (a) arrange's last step refused once: made on the next try, no mark
        hold(lambda n: n.startswith("0001-1600-"), 1)
        g = mp(kit3, retry=True)
        check("held once at the last step: made on the next try", g["made"] == 6 and not g.get("later")
              and arrange.preview_file(kit3, {"n": 1}, 1600, p1).is_file(), g)
        check("held once: no mark for it (the broken photo keeps its own)", not any(m.startswith("0001-") for m in marks())
              and any(m.startswith("0008-") for m in marks()), marks())
        # (b) a new photo, its last step refused every time: "later", no mark, nothing half-made left
        draw(kit3 / "Photos" / "p-002.jpg", 1700, 1100, (10, 20, 30))      # exported again: new copies wanted
        hold(lambda n: n.startswith("0002-1600-"), 99)
        g = mp(kit3, retry=True)
        check("held every time: 'later', counted as such, not as unreadable", g.get("later") == 1 and g["failed"] == 2, g)
        check("held every time: no mark, so the next run tries it", not any(m.startswith("0002-") for m in marks()), marks())
        check("held every time: our own scratch copies are cleared", not scratch(), scratch())
        check("held every time, with room on the drive: not called a full drive", not g.get("full"), g)
        this_computer.WINDOWS = real_win    # the page's state takes the kit's lock: this computer's own kind
        st = arrange.state_for_page(kit3, "reel")
        this_computer.WINDOWS = True
        by3 = {x["n"]: x for x in st["photos"]}
        check("held every time: the page says 'getting this photo ready', not 'can't be shown'",
              not by3[2]["have"] and not by3[2]["missing"], by3[2])
        hold(None, 0)
        g = mp(kit3)                                   # what the page and open do (retry off)
        check("the next run, nothing held: it is made (it had no mark to skip it)", g["made"] == 1 and not g.get("later")
              and arrange.preview_file(kit3, {"n": 2}, 520, p2).is_file(), g)
        # (c) pictures.make_jpeg's own step refused every time (its new picture into our scratch name)
        draw(kit3 / "Photos" / "p-001.jpg", 1300, 1900, (200, 90, 40))
        hold(lambda n: n.startswith(".p-"), 99)
        g = mp(kit3, retry=True)
        check("held inside make_jpeg: 'later', no mark (the photo itself opens)", g.get("later") == 1
              and not any(m.startswith("0001-") for m in marks()), f"{g} {marks()}")
        check("held inside make_jpeg: nothing half-made left", not scratch(), scratch())
        hold(None, 0)
        # (11) the drive is full when a copy comes back "later": said so, and nothing waits
        draw(kit3 / "Photos" / "p-002.jpg", 1650, 1100, (30, 20, 10))
        hold(lambda n: n.startswith("0002-1600-"), 99)
        this_computer.free_bytes = lambda path: 1_000_000          # 1 MB left on the kit's drive
        arrange.LATER_WAITS = (3.0, 3.0)                           # long enough that a wait would show
        t0 = time.time()
        g = mp(kit3, retry=True)
        took = time.time() - t0
        check("a full drive: the copy is 'later' and 'full' is said, with no wait before it", g.get("later") == 1
              and g.get("full") is True and took < 2.5, f"{g} in {took:.1f} s")
        check("a full drive: no mark, so the copy is made once there is room", not any(m.startswith("0002-") for m in marks()), marks())
        this_computer.free_bytes = real_free
        arrange.LATER_WAITS = (0.2, 0.4)
        hold(None, 0)
        # (e) the designer's larger copy (2400), made when a finished slide asks for it (big_copy): held once at its
        # last step it is tried again, as the pickers' copies are; held every time it is not there yet, with no mark
        rows3 = {x["n"]: x for x in arrange.sheet_rows(kit3)}
        rec3 = arrange.kit_mod.load_rec(kit3)
        hold(lambda n: n.startswith("0001-2400-"), 1)
        f = arrange.big_copy(kit3, rec3, rows3[1], 2400)
        check("the designer's larger copy, held once at its last step: tried again and made (never 'can't be read')",
              f is not None and f.is_file() and f.name.startswith("0001-2400-"), f)
        hold(lambda n: n.startswith("0002-2400-"), 99)
        f = arrange.big_copy(kit3, rec3, rows3[2], 2400)
        check("the designer's larger copy, held every time: not there yet, no mark, nothing half-made left",
              f is None and not any(m.startswith("0002-") for m in marks()) and not scratch(), f"{f} {marks()} {scratch()}")
        hold(None, 0)
        f = arrange.big_copy(kit3, rec3, rows3[2], 2400)
        check("and once it is let go, the next ask makes it", f is not None and f.is_file(), f)
        # (d) a Mac never gets "later": a refusal at the last step is raised, as it always was
        if WINDOWS:
            skip("a Mac: a refusal at the last step is raised, as before", "this is a PC; that is the Mac's side, tried on a Mac")
        else:
            this_computer.WINDOWS = False
            draw(kit3 / "Photos" / "p-001.jpg", 1250, 1900, (190, 90, 40))
            hold(lambda n: n.startswith("0001-1600-"), 99)
            try:
                arrange.make_previews(kit3, retry=True)
                raised = False
            except PermissionError:
                raised = True
            check("a Mac: a refusal at the last step is raised, as before (never hidden)", raised)
    finally:
        hold(None, 0)
        this_computer.replace, this_computer.WINDOWS, arrange._too_deep = real_replace, real_win, real_deep
        arrange.LATER_WAITS, this_computer.free_bytes = real_waits, real_free


# ---------------------------------------------------------------- 10: a background run's lines on a PC
CHILD_LOG = getattr(arrange, "CHILD_LOG", "ASSISTANT_ARRANGE_OWN_LOG")
CHILD = ("import os, sys, time; from pathlib import Path; sys.path.insert(0, sys.argv[1]); import arrange, this_computer\n"
         "this_computer.WINDOWS = True\n"           # on a PC already; on a Mac, so _own_output does its PC work
         "getattr(arrange, '_own_output', lambda: None)()\n"
         "go = Path(sys.argv[2])\n"
         "for i in range(3):\n"
         "    print(f'child line {i}', flush=True)\n"
         "    end = time.time() + 30\n"
         "    while not (go / str(i)).exists() and time.time() < end:\n"
         "        time.sleep(0.02)\n")
WHOLE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} server line ([0-9])")


def lines_after(own):
    """Run the child above with a handle to arrange.log that has no 'add at the end' (what a PC's run is given),
    adding a line of the server's own after each of its lines. Returns the log's lines."""
    log = STUDIO / "arrange.log"
    log.write_text("start\n", encoding="utf-8")
    go = work / f"go-{time.time_ns()}"
    go.mkdir()
    fd = os.open(log, os.O_WRONLY | getattr(os, "O_BINARY", 0))
    os.lseek(fd, 0, os.SEEK_END)
    env = dict(ENV)
    env.pop(CHILD_LOG, None)
    if own:
        env[CHILD_LOG] = "1"
    p = subprocess.Popen([sys.executable, "-c", CHILD, str(SCRIPTS), str(go)], stdout=fd, stderr=subprocess.STDOUT, env=env)
    os.close(fd)
    for i in range(3):
        end = time.time() + 30
        while f"child line {i}" not in log.read_text(encoding="utf-8", errors="replace") and time.time() < end:
            time.sleep(0.02)
        arrange.log(f"server line {i}")
        (go / str(i)).touch()
    p.wait(timeout=60)
    return log.read_text(encoding="utf-8", errors="replace").splitlines()


def log_checks():
    got_old = lines_after(own=False)
    lost = [f"server line {i}" for i in range(3) if not any(WHOLE.fullmatch(x) and x.endswith(f" {i}") for x in got_old)]
    check("without its own handle, a run writes over the server's lines (the PC fault this test is for)", lost, got_old)
    got_new = lines_after(own=True)
    want = ["start"] + [x for i in range(3) for x in (f"child line {i}", f"server line {i}")]
    check("with arrange._own_output: every line of both is there, whole and in order",
          [x if x.startswith(("start", "child")) else (x.split(" ", 1)[1] if WHOLE.fullmatch(x) else x) for x in got_new] == want, got_new)


def part(name, fn, *args):
    """One part; a fault in it FAILs here and never stops the parts after it."""
    print(f"\n-- {name}", flush=True)
    try:
        fn(*args)
    except Exception as e:  # noqa: BLE001
        import traceback
        check(f"{name}: ran to the end", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-600:]}")


if HAVE_PIL:
    kit, specs = make_kit("2026-11-01 Zoë’s beach")
    part("1 to 3: the small copies", copies_checks, kit, specs)
else:
    kit = bare_kit("2026-11-01 Zoë’s beach")
    skip("1 to 3: the small copies (sizes, upright, the HEIC and a broken photo)", NO_PIL)
part("4: one writer at a time, across processes", lock_checks, kit)
part("5: is a slide job at work?", job_checks, kit)
if HAVE_PIL:
    part("6: a previews child outlives its starter", child_checks)
else:
    skip("6: a previews child outlives its starter", NO_PIL)
part("7: saving a record while it is open", save_checks, kit)
part("8: too deep for 260 characters", deep_checks, kit)
if not HAVE_PIL:
    skip("9 and 11: a copy something holds, a full drive", NO_PIL)
elif pictures.use_sips():
    skip("9 and 11: a copy something holds ('later'), a full drive",
         "this is the Mac's way of making pictures (sips); run with ASSISTANT_NO_SIPS=1 to try the PC's")
else:
    part("9 and 11: a copy something holds ('later'), a full drive", held_checks)
part("10: a background run's lines on a PC", log_checks)

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
