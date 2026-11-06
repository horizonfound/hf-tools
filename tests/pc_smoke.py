#!/usr/bin/env python3
"""The parts of the Assistant that should already work on a Windows PC, tried for real.

Runs the same on a Mac and on Windows, in scratch folders it makes itself (never the real ~/.studio,
never a real drive). GitHub runs it on a real Windows machine on every push (.github/workflows/
check-pc.yml), which is how a PC gets tested without anyone here owning one: no screen, no card, no
CapCut, no Claude app, but real Windows.

    python3 tests/pc_smoke.py        Pillow is the only add-on it uses, and only for the checks that need it

The pretend photos are drawn here in plain Python, so it runs on the Mac's own Python 3.9 with nothing
installed (the Mac way: sips). A check that needs Pillow and does not have it says SKIP and why; so does any
check this computer cannot do. Every line says PASS, FAIL or SKIP; INFO lines are only information (what
Windows' own Media Foundation made of a song, until it has passed once). Exit 1 only when something FAILED.

Every script is started the way Claude starts it: with this test's own environment as it was when the test
started (so on a PC, not in UTF-8 mode unless the script asks for it itself: on Python 3.9 to 3.14 that is the
PC's older code page). A script that hangs is stopped after 10 minutes and its check FAILs.
    ASSISTANT_SMOKE_DIR=<folder>    where the scratch folder goes (default: this computer's temporary folder)
    ASSISTANT_SMOKE_KEEP=<folder>   when something FAILED, the scratch folder is also copied here (GitHub uploads it)
    ASSISTANT_STRICT_MF=1           hold Windows' own Media Foundation to PASS or FAIL like the other ways

What it tries:
  - the helper that knows both computers: dates in words, safe names, names Windows keeps for itself, long
    paths, room on a drive, the list of drives;
  - a whole copy-and-check of a pretend card with an accent and a colon in its name; the records and the
    report page written as UTF-8; a name with an emoji in the Studio File and the editing queue; the walk-away
    check; hiding the records folder; and, with Pillow hidden, the walk-away check stopping in plain words;
  - a page server started in the background outliving the command that started it once that command is swept
    away (on a Mac its process group killed; on Windows its process group sent Ctrl+Break), against a stand-in
    started the plain way that must not survive; saving over a file another program has open;
  - moving a folder while a photo in it is held open: the move waits, then goes through once it is let go,
    or stops with the plain words (on Windows for real; elsewhere the waiting itself, with a stand-in);
  - small pictures the PC way (sips switched off): a made-up TIFF-style RAW with a JPEG strip and an
    orientation tag, a made-up CR3-style file with its preview box, a JPEG turned by its Exif orientation, a
    PNG that is partly see-through, a fake iPhone HEIC; make_jpeg, thumb_rows and size_of on each, and the
    plain words when Pillow is missing;
  - the reel's sound: the length of every test song in tests/fixtures, hearing the WAV (always) and the MP3
    and M4A songs when this computer has a way to (which way is printed; with none, SKIP, never FAIL);
  - a whole backup start to finish (copy and check, index, groups and contact sheet, the look, the sort, the
    sneak-peek pages, the pick, the sneak peeks, the settle), every photo checked against the card, the card
    unchanged, the records hidden, then a rename to an accented name and two renames of capital letters only.
    On a Mac it runs twice: the Mac's own way, and the PC way (the JPEG inside each photo, and Pillow). On
    Windows the settle and a rename also run while another program holds a photo open.

What it does NOT try: the beat of each song (tests/fixtures/check_sound.py), made-up RAW files from six makers
(tests/pc_pictures.py), the page servers (tests/pc_servers.py), the backup's own promises in depth
(tests/backup_safety.py), CapCut. docs/pc-readiness-2026-11-06.md has the list.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
# How this test itself was started, before this_computer.py (imported next) switches UTF-8 mode on for the
# scripts it starts. Each script here is started the way Claude starts it on a PC: with nothing set, so on
# Python 3.9 to 3.14 it runs in the PC's own older code page (cp1252) unless it asks for UTF-8 itself (Nov 6
# review: passing UTF-8 mode on to every script meant the accent and emoji checks never tried that case).
_UTF8_AT_START = os.environ.get("PYTHONUTF8")
sys.path.insert(0, str(SCRIPTS))
import this_computer as tc  # noqa: E402
import pictures  # noqa: E402

tc.utf8_output()
results, skipped = [], []
_tag = [""]          # "(the PC way) " while the second whole backup runs on a Mac, so its lines can be told apart
STEP_TIMEOUT = 600   # seconds: a script that hangs (a pipe held open, a Windows call that never answers) is a FAIL,
                     # never six hours of GitHub's time


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + _tag[0] + what + (f"   [{detail}]" if detail and not ok else ""), flush=True)


def skip(what, why):
    skipped.append(what)
    print(f"SKIP  {_tag[0]}{what}   [{why}]", flush=True)


def info(what, detail):
    """A line that is only information (neither PASS nor FAIL): something this computer did that has never been
    seen before, printed so it can be read."""
    print(f"INFO  {_tag[0]}{what}   [{detail}]", flush=True)


def child_env(env=None):
    """The environment a script is started with: this test's own, as it was before this_computer.py changed it,
    plus `env`. PYTHONUTF8 only when `env` sets it (or the test itself was started with it)."""
    e = dict(os.environ)
    if _UTF8_AT_START is None:
        e.pop("PYTHONUTF8", None)
    else:
        e["PYTHONUTF8"] = _UTF8_AT_START
    e.update(env or {})
    return e


def run_python(args, env=None, timeout=STEP_TIMEOUT):
    """(exit code, everything printed). A run that takes longer than `timeout` is stopped and comes back as exit
    124 with the words TIMED OUT, so the check it belongs to FAILs and says why."""
    try:
        r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, encoding="utf-8", errors="replace",
                           env=child_env(env), timeout=timeout)
    except subprocess.TimeoutExpired as e:
        def text(b):
            return b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")
        return 124, text(e.stdout) + text(e.stderr) + f"\nTIMED OUT after {timeout} s"
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run(script, *args, env=None):
    return run_python([SCRIPTS / script, *args], env=env)


@contextlib.contextmanager
def environ(**env):
    """These environment settings for the length of a with-block, in this process; put back afterwards."""
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def pillow_here():
    return pictures._pillow() is not None


# ---------------------------------------------------------------- pretend photos, drawn in plain Python
#
# A small baseline JPEG writer: each 8x8 block is one flat colour (only its average is stored), which is all a
# pretend photo needs and takes milliseconds. So no add-on draws the photos, and the Mac's own Python 3.9, which
# has no Pillow, runs the whole backup the Mac way. Every JPEG reader takes these (checked with Pillow and sips).

def _huffman(bits, values):
    codes, code, k = {}, 0, 0
    for length in range(1, 17):
        for _ in range(bits[length - 1]):
            codes[values[k]] = (code, length)
            code += 1
            k += 1
        code <<= 1
    return codes


_DC_BITS, _DC_VALUES = (0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0), tuple(range(12))   # the standard DC table
_AC_BITS, _AC_VALUES = (1,) + (0,) * 15, (0,)                                                # only "end of block"
_DC, _EOB = _huffman(_DC_BITS, _DC_VALUES), _huffman(_AC_BITS, _AC_VALUES)[0]


class _Bits:
    def __init__(self):
        self.out, self.acc, self.n = bytearray(), 0, 0

    def put(self, code, length):
        self.acc = (self.acc << length) | code
        self.n += length
        while self.n >= 8:
            self.n -= 8
            b = (self.acc >> self.n) & 0xFF
            self.out.append(b)
            if b == 0xFF:
                self.out.append(0)                 # a 0xFF in the picture data is always followed by 0x00
        self.acc &= (1 << self.n) - 1

    def done(self):
        if self.n:
            self.put((1 << (8 - self.n)) - 1, 8 - self.n)
        return bytes(self.out)


def jpeg_bytes(width, height, color, exif=b""):
    """A JPEG width x height (both multiples of 8), block (bx, by) coloured color(bx, by) -> (r, g, b)."""
    bits, prev = _Bits(), [0, 0, 0]
    for by in range(height // 8):
        for bx in range(width // 8):
            r, g, b = color(bx, by)
            ycc = (0.299 * r + 0.587 * g + 0.114 * b, 128 - 0.168736 * r - 0.331264 * g + 0.5 * b,
                   128 + 0.5 * r - 0.418688 * g - 0.081312 * b)
            for c in range(3):
                dc = max(-1024, min(1016, int(round(8 * (ycc[c] - 128)))))
                diff, prev[c] = dc - prev[c], dc
                size = abs(diff).bit_length()
                bits.put(*_DC[size])
                if size:
                    bits.put(diff if diff > 0 else diff + (1 << size) - 1, size)
                bits.put(*_EOB)

    def seg(marker, body):
        return struct.pack(">BBH", 0xFF, marker, len(body) + 2) + body
    out = b"\xff\xd8" + (seg(0xE1, b"Exif\x00\x00" + exif) if exif else b"")
    out += seg(0xDB, b"\x00" + b"\x01" * 64)
    out += seg(0xC0, struct.pack(">BHHB", 8, height, width, 3) + bytes((1, 0x11, 0, 2, 0x11, 0, 3, 0x11, 0)))
    out += seg(0xC4, b"\x00" + bytes(_DC_BITS) + bytes(_DC_VALUES) + b"\x10" + bytes(_AC_BITS) + bytes(_AC_VALUES))
    out += seg(0xDA, bytes((3, 1, 0x00, 2, 0x00, 3, 0x00, 0, 63, 0)))
    return out + bits.done() + b"\xff\xd9"


def exif_blob(taken=None, make="Canon", model="Canon EOS R5", orientation=None):
    """What follows "Exif\\0\\0" in a camera JPEG (little-endian): Make, Model, Orientation if given, and when the
    photo was taken (DateTimeOriginal, in the Exif directory) if given."""
    strings = [s.encode("ascii") + b"\x00" for s in (make, model)]
    dt = taken.strftime("%Y:%m:%d %H:%M:%S").encode("ascii") + b"\x00" if taken else None
    n0 = 2 + (1 if orientation else 0) + (1 if dt else 0)
    data_at = 8 + 2 + 12 * n0 + 4
    blob, offsets = bytearray(), []
    for s in strings:
        offsets.append(data_at + len(blob))
        blob += s + (b"\x00" if len(s) % 2 else b"")
    exif_at = data_at + len(blob)
    entries = [struct.pack("<HHII", 0x010F, 2, len(strings[0]), offsets[0]),
               struct.pack("<HHII", 0x0110, 2, len(strings[1]), offsets[1])]
    if orientation:
        entries.append(struct.pack("<HHIHH", 0x0112, 3, 1, orientation, 0))
    if dt:
        entries.append(struct.pack("<HHII", 0x8769, 4, 1, exif_at))
    out = b"II*\x00" + struct.pack("<IH", 8, n0) + b"".join(entries) + struct.pack("<I", 0) + bytes(blob)
    if dt:
        out += struct.pack("<H", 1) + struct.pack("<HHII", 0x9003, 2, len(dt), exif_at + 18) + struct.pack("<I", 0) + dt
    return out


def png_rgba(width, height, pixel):
    """A PNG with see-through parts: pixel(x, y) -> (r, g, b, alpha)."""
    raw = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width)) for y in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def tiff_raw(jpeg, orientation):
    """A made-up TIFF-style RAW (the shape of a CR2, NEF or DNG): one directory holding the orientation and one
    strip that is the stored JPEG, then some made-up sensor data."""
    at = 8 + 2 + 12 * 3 + 4
    head = (b"II*\x00" + struct.pack("<IH", 8, 3) + struct.pack("<HHII", 0x0111, 4, 1, at)
            + struct.pack("<HHIHH", 0x0112, 3, 1, orientation, 0) + struct.pack("<HHII", 0x0117, 4, 1, len(jpeg))
            + struct.pack("<I", 0))
    return head + jpeg + bytes(range(256)) * 16


def cr3_file(preview, thumbnail):
    """A made-up CR3-style file: an ftyp box, then THMB and PRVW boxes each holding a JPEG, then made-up data."""
    def box(kind, payload):
        return struct.pack(">I", 8 + len(payload)) + kind + payload
    ftyp = struct.pack(">I4s4sI", 24, b"ftyp", b"crx ", 1) + b"crx isom"
    return ftyp + box(b"THMB", bytes(8) + thumbnail) + box(b"PRVW", bytes(16) + preview) + box(b"mdat", bytes(range(256)) * 16)


def make_card(card, groups=(8,)):
    """A pretend card: JPEGs with camera dates, 45 seconds apart within a group and 40 minutes between groups
    (so the backup finds one shoot per group), plus a camera housekeeping file and a Mac one."""
    d = card / "DCIM" / "100CANON"
    d.mkdir(parents=True)
    (card / "MISC").mkdir()
    (card / "MISC" / "M01.CTG").write_bytes(b"camera housekeeping")
    (d / ".DS_Store").write_bytes(b"x")
    t = datetime(2026, 6, 4, 9, 0, 0)
    n = 0
    for g, count in enumerate(groups):
        if g:
            t += timedelta(minutes=40)
        for i in range(count):
            base = (40 + n * 9, 120 + g * 40, 200 - n * 7)

            def color(bx, by, base=base, i=i):
                return (20, 20, 20) if by < 16 and bx % 8 < 1 + i % 3 else base
            (d / f"IMG_{4471 + n}.JPG").write_bytes(jpeg_bytes(600, 400, color, exif_blob(t)))
            t += timedelta(seconds=45)
            n += 1
    return sorted(d.glob("*.JPG"))


# ---------------------------------------------------------------- checking what came out

def photos_match(root, index, card):
    """Every photo the index knows: under exactly that name in its folder (case and accents as recorded, read
    from the folder's own listing), and byte for byte the card's photo. (problems, how many checked)"""
    bad, n = [], 0
    for p in index.get("photos", []):
        if not p.get("original"):
            continue
        f = root / p["file"]
        try:
            listed = p["file"].rsplit("/", 1)[-1] in os.listdir(f.parent)
            same = listed and sha(f) == p["sha256"] == sha(card / p["original"])
        except OSError:
            same = False
        n += 1
        if not same:
            bad.append(p["file"])
    return bad, n


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def card_snapshot(card):
    return {p.relative_to(card).as_posix(): sha(p) for p in sorted(card.rglob("*")) if p.is_file()}


def hidden(path):
    """True when File Explorer (the hidden mark) or Finder (a name starting with a dot, or the hidden flag) keeps
    this folder out of sight. None on a computer that has neither."""
    path = Path(path)
    if tc.WINDOWS:
        import ctypes
        f = ctypes.windll.kernel32.GetFileAttributesW
        f.argtypes, f.restype = [ctypes.c_wchar_p], ctypes.c_uint32
        attrs = f(str(path))
        return attrs != 0xFFFFFFFF and bool(attrs & 0x2)
    if tc.MAC:
        return path.name.startswith(".") or bool(getattr(os.stat(path), "st_flags", 0) & stat.UF_HIDDEN)
    return None


def held_open_outcome(what, code, out, unchanged, finished):
    """On Windows a folder with a photo in it held open cannot be moved. The script should stop with exit 1 and
    the plain words, the held folder where it was; if this Windows lets the move through anyway, that is safe too, as long as
    the job then finished cleanly. Returns True when it stopped (so the test runs it again)."""
    stopped = code == 1 and tc.HeldOpen.words in out and unchanged()
    went = code == 0 and finished()
    print(f"      ({'Windows refused while the photo was open' if stopped else 'Windows let it through' if went else 'neither'})")
    check(f"{what}: stops with the plain words (the held folder stays put), or finishes cleanly", stopped or went, out[-500:])
    return stopped


# ---------------------------------------------------------------- a folder moved while a photo in it is open

def held_rename_checks(work):
    print("\n-- moving a folder while another program has a photo in it open")
    calls = []

    def refused_three_times():
        calls.append(1)
        if len(calls) <= 3:
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        return "moved"
    got = tc._patient(refused_three_times, ("a", "b"), 3.0)
    check("a move that is refused while a file is open is tried again, and goes through once it is let go",
          got == "moved" and len(calls) == 4, f"{got} after {len(calls)} tries")

    def always_refused():
        raise PermissionError(32, "in use")
    t0 = time.monotonic()
    try:
        tc._patient(always_refused, ("a", "b"), 0.4)
        err = None
    except tc.HeldOpen as e:
        err = e
    took = time.monotonic() - t0
    check("held longer than the wait: it stops with the plain words (still a PermissionError, so callers catch it)",
          isinstance(err, PermissionError) and err is not None and err.words == tc.HeldOpen.words and 0.3 <= took < 3,
          f"{err!r} after {took:.1f} s")
    tries = []

    def taken():
        tries.append(1)
        raise FileExistsError(17, "Cannot create a file when that file already exists")
    try:
        tc._patient(taken, ("a", "b"), 3.0)
        passed_on = False
    except FileExistsError:
        passed_on = True
    check("a name already in use is never tried again or replaced: it is passed straight on", passed_on and len(tries) == 1)

    # the real thing: a photo held open by this very test (Python opens files without letting Windows move them)
    folder, moved = work / "held Côte", work / "held Côte moved"
    folder.mkdir()
    photo = folder / "IMG_0001.JPG"
    photo.write_bytes(b"photo bytes " * 100)
    fh = open(photo, "rb")

    def let_go():
        time.sleep(1.0)
        fh.close()
    t = threading.Thread(target=let_go)
    t.start()
    t0 = time.monotonic()
    try:
        tc.rename(folder, moved)
        err = None
    except OSError as e:
        err = e
    took = time.monotonic() - t0
    t.join()
    fh.close()
    if tc.WINDOWS:
        print(f"      ({'Windows refused while the photo was open; the move waited, then went through' if took >= 0.8 else 'Windows let the move through at once'}: {took:.1f} s)")
    else:
        print(f"      (a {tc.COMPUTER} never refuses: moved at once, {took:.2f} s)")
    check("the folder moves once the photo in it is let go, the photo unchanged",
          err is None and moved.is_dir() and not folder.exists() and (moved / "IMG_0001.JPG").read_bytes() == b"photo bytes " * 100,
          f"{err!r} {took:.1f} s")

    folder2, moved2 = work / "held long", work / "held long moved"
    folder2.mkdir()
    photo2 = folder2 / "IMG_0002.JPG"
    photo2.write_bytes(b"second photo " * 100)
    fh = open(photo2, "rb")
    try:
        try:
            tc.rename(folder2, moved2, wait=1.0)
            err = None
        except OSError as e:
            err = e
        whole = folder2.is_dir() and photo2.read_bytes() == b"second photo " * 100 and not moved2.exists()
    finally:
        fh.close()
    if isinstance(err, tc.HeldOpen):
        check("held past the wait: it stops with the plain words, the folder where it was and whole",
              whole and str(err.words) == tc.HeldOpen.words)
        try:
            tc.rename(folder2, moved2)
            err2 = None
        except OSError as e:
            err2 = e
        check("and once the photo is let go, the same move finishes", err2 is None and moved2.is_dir() and not folder2.exists(), repr(err2))
    else:
        check("held past the wait: this computer let the move through, and it finished cleanly",
              err is None and moved2.is_dir() and not folder2.exists() and (moved2 / "IMG_0002.JPG").read_bytes() == b"second photo " * 100,
              repr(err))

    a, b, c = work / "name a.txt", work / "name b.txt", work / "name c.txt"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    first = tc.rename_new(a, b)
    check("giving a file a name already in use is refused; both files stay as they were",
          first is False and a.read_text(encoding="utf-8") == "a" and b.read_text(encoding="utf-8") == "b", str(first))
    second = tc.rename_new(a, c)
    check("and a name that is free is taken", second is True and c.read_text(encoding="utf-8") == "a" and not a.exists(), str(second))


# ---------------------------------------------------------------- small pictures the PC way

def pictures_checks(work):
    print("\n-- small pictures the PC way (the JPEG inside each RAW, and Pillow; the Mac's sips switched off)")
    d = work / "pictures"
    d.mkdir()
    red, green, magenta = (230, 20, 20), (20, 200, 40), (200, 0, 200)

    def marked(mark):
        def color(bx, by):
            if bx < 6 and by < 6:
                return mark                        # a mark in the top-left corner of the stored pixels
            return (20, 20, 20) if bx % 8 == 0 else (40 + bx * 2, 90 + by, 160)
        return color
    stored = jpeg_bytes(480, 320, marked(red))
    preview = jpeg_bytes(480, 320, marked(green))
    turned, raw, cr3, png, heic = (d / "turned by its Exif.JPG", d / "made-up.DNG", d / "made-up.CR3", d / "see-through.png",
                                   d / "phone.HEIC")
    turned.write_bytes(jpeg_bytes(480, 320, marked(red), exif_blob(orientation=6)))
    raw.write_bytes(tiff_raw(stored, 8))
    cr3.write_bytes(cr3_file(preview, jpeg_bytes(160, 112, lambda bx, by: magenta)))
    png.write_bytes(png_rgba(64, 48, lambda x, y: (255, 0, 0, 0) if x < 32 else (0, 0, 255, 255)))
    heic.write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + bytes(5000))
    before = {p.name: sha(p) for p in (turned, raw, cr3, png, heic)}

    with environ(ASSISTANT_NO_SIPS="1"):
        check("the PC way is what runs here now (sips switched off)", not pictures.use_sips())
        # plain Python, no add-on: the JPEG the camera stored inside each RAW
        check("the JPEG strip inside a TIFF-style RAW is found, byte for byte", pictures.embedded_jpeg(raw) == stored)
        check("the 480 px preview inside a CR3-style file is found, byte for byte (not its thumbnail)",
              pictures.embedded_jpeg(cr3) == preview)

        real = pictures._pillow                      # as on a PC where Pillow was never installed
        pictures._pillow = lambda: None
        try:
            ok, words = pictures.ready()
            out = d / "no pillow.jpg"
            made = pictures.make_jpeg(raw, out, 240)
            why = pictures.why_not(raw)
            rows, size = pictures.thumb_rows(turned, 120), pictures.size_of(turned)
        finally:
            pictures._pillow = real
        check("with no Pillow: plain words naming the add-on and its one command; nothing made, no crash",
              not ok and "Pillow" in words and "pip install pillow" in words and not made and why == words
              and rows is None and size is None and not out.exists() and not list(d.glob("*.part")), words)

        if not pillow_here():
            skip("previews, contact-sheet rows and sizes the PC way (5 kinds of file)",
                 "Pillow is not installed for this Python; the PC way needs it (python -m pip install pillow)")
            check("the photos were only read", {p.name: sha(p) for p in (turned, raw, cr3, png, heic)} == before)
            return
        from PIL import Image

        def pixel(rows_or_image, x, y):
            if isinstance(rows_or_image, list):
                return tuple(rows_or_image[y][3 * x:3 * x + 3])
            return rows_or_image.getpixel((x, y))[:3]

        def looks(c, kind):
            r, g, b = c
            return {"red": r > 150 and g < 90 and b < 90, "green": g > 140 and r < 90 and b < 110,
                    "white": min(c) > 235, "blue": b > 180 and r < 80 and g < 80}[kind]

        def made_jpeg(src, size):
            dst = d / (src.name + f" {size}.jpg")
            if not pictures.make_jpeg(src, dst, size):
                return None
            im = Image.open(dst)
            im.load()
            return im

        # a JPEG turned by its own Exif (6: the camera was held on its side): stored 480 x 320, shown 320 x 480,
        # the mark that is top-left in the stored pixels shows top-right
        im = made_jpeg(turned, 240)
        check("a JPEG turned by its Exif comes out upright: 160 x 240, its mark top-right, nothing left to turn it twice",
              im is not None and im.size == (160, 240) and looks(pixel(im, 148, 10), "red") and not looks(pixel(im, 10, 10), "red")
              and im.getexif().get(0x0112) in (None, 1), f"{im.size if im else None} {pixel(im, 148, 10) if im else ''}")
        t = pictures.thumb_rows(turned, 120)
        check("its contact-sheet rows are upright too (80 x 120, the mark top-right)",
              t is not None and t[:2] == (80, 120) and looks(pixel(t[2], 74, 5), "red"), str(t[:2] if t else None))
        check("and its size is told the right way up (320 x 480)", pictures.size_of(turned) == (320, 480), str(pictures.size_of(turned)))

        # a TIFF-style RAW whose own directory says 8 (turned the other way); the JPEG inside says nothing
        im = made_jpeg(raw, 240)
        check("a TIFF-style RAW turned by its own orientation tag: 160 x 240, the mark bottom-left",
              im is not None and im.size == (160, 240) and looks(pixel(im, 8, 232), "red") and not looks(pixel(im, 150, 8), "red"),
              f"{im.size if im else pictures.why_not(raw)}")
        t = pictures.thumb_rows(raw, 120)
        check("its contact-sheet rows: 80 x 120, the mark bottom-left", t is not None and t[:2] == (80, 120) and looks(pixel(t[2], 5, 114), "red"),
              str(t[:2] if t else None))
        check("its size, the right way up: 320 x 480", pictures.size_of(raw) == (320, 480), str(pictures.size_of(raw)))

        # a CR3-style file: the preview box, never the thumbnail; a preview smaller than asked is kept at its size
        im = made_jpeg(cr3, 700)
        check("a CR3-style file gives its 480 x 320 preview (green mark), kept at its own size, not blown up",
              im is not None and im.size == (480, 320) and looks(pixel(im, 16, 16), "green"), f"{im.size if im else pictures.why_not(cr3)}")
        t = pictures.thumb_rows(cr3, 240)
        check("its contact-sheet rows: 240 x 160, the green mark top-left", t is not None and t[:2] == (240, 160) and looks(pixel(t[2], 8, 8), "green"),
              str(t[:2] if t else None))
        check("its size: 480 x 320", pictures.size_of(cr3) == (480, 320), str(pictures.size_of(cr3)))

        # a PNG that is partly see-through: laid on white, never on whatever colour hides under the clear part
        im = made_jpeg(png, 700)
        check("a see-through PNG becomes a JPEG laid on white (64 x 48; the clear half white, the blue half blue)",
              im is not None and im.size == (64, 48) and im.mode == "RGB" and looks(pixel(im, 10, 24), "white") and looks(pixel(im, 54, 24), "blue"),
              f"{im.size if im else None} {pixel(im, 10, 24) if im else ''}")
        t = pictures.thumb_rows(png, 32)
        check("its contact-sheet rows: 32 x 24, white then blue", t is not None and t[:2] == (32, 24)
              and looks(pixel(t[2], 4, 12), "white") and looks(pixel(t[2], 28, 12), "blue"), str(t[:2] if t else None))
        check("its size: 64 x 48", pictures.size_of(png) == (64, 48), str(pictures.size_of(png)))

        # a fake iPhone photo: no picture and plain words, never a crash or a made-up picture
        out = d / "phone.jpg"
        made = pictures.make_jpeg(heic, out, 240)
        why = pictures.why_not(heic) or ""
        words_ok = ("pillow-heif" in why) if not pictures.heic_ok() else bool(why)
        check("an iPhone photo this computer cannot open: no picture, plain words" + ("" if pictures.heic_ok() else " naming the add-on"),
              not made and not out.exists() and words_ok and pictures.thumb_rows(heic, 120) is None and pictures.size_of(heic) is None, why)
        check("every photo was only read, never changed", {p.name: sha(p) for p in (turned, raw, cr3, png, heic)} == before)
        check("no half-made picture is left behind", not list(d.glob("*.part")))


# ---------------------------------------------------------------- the reel's sound

SONGS = {   # the true lengths (tests/fixtures/README.md)
    "click-100bpm.wav": 10.0, "click-100bpm.aiff": 10.0, "click-100bpm.m4a": 10.0, "click-100bpm-m4a-named.mp3": 10.0,
    "click-100bpm-cbr.mp3": 10.031, "click-100bpm-vbr.mp3": 10.031, "click-100bpm-cbr-noheader.mp3": 10.031,
    "click-100bpm-vbr-noheader.mp3": 10.031}
NOTHING_INSTALLED = {"ASSISTANT_NO_AFCONVERT": "1", "ASSISTANT_NO_FFMPEG": "1"}


def sound_checks():
    print("\n-- the reel's sound: how long each test song is, and hearing it")
    spec = importlib.util.spec_from_file_location("sound", str(REEL / "sound.py"))
    sound = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sound)
    for name, want in SONGS.items():
        got = sound.duration(FIXTURES / name)
        check(f"the length of {name} is read from the file itself ({want:.2f} s)", got is not None and abs(got - want) <= 0.1, f"{got} s")

    def heard(name, env, want_how=None):
        """(heard it, how, whether it sounds right: about the song's length, not silent, the way asked for).
        Heard in a thread of its own: a decoder that never answers (Windows' own, never run on a PC before) is
        left behind after two minutes instead of holding up every check after it."""
        box = {}

        def go():
            try:
                with environ(**env):
                    box["got"] = sound.decode(FIXTURES / name)
            except Exception as e:  # noqa: BLE001  (sound.decode should never raise; if it does, say so)
                box["got"] = (None, f"sound.decode raised {type(e).__name__}: {e}")
        t = threading.Thread(target=go)
        t.daemon = True
        t.start()
        t.join(120)
        if "got" not in box:
            return False, "no answer within 120 s (the decoder hung)", False
        a, how = box["got"]
        if a is None:
            return False, how, False
        secs, peak = len(a) / 11025, (max(max(a), -min(a)) if len(a) else 0)
        good = abs(secs - SONGS[name]) <= 0.15 and peak > 1000 and (want_how is None or how == want_how)
        return True, f"{how}: {secs:.3f} s, loudest {peak}", good

    got, how, good = heard("click-100bpm.wav", {})
    check(f"hearing the WAV song, this computer's own way ({how.split(':')[0] if got else 'nothing'})", good, how)
    for name, kind in (("click-100bpm.wav", "wav"), ("click-100bpm.aiff", "aiff")):
        got, how, good = heard(name, NOTHING_INSTALLED, kind)
        check(f"hearing {name} in plain Python, nothing installed", good, how)

    ways = (["afconvert"] if sound._afconvert_ok() else []) + [h for _, h in sound._ffmpegs()]
    print(f"      (ways to hear an MP3 or M4A here: {', '.join(ways) or 'neither afconvert nor ffmpeg'}"
          + ("; then Windows' own Media Foundation" if tc.WINDOWS else "") + ")")
    # Windows' own Media Foundation has never run on a real PC (Nov 6). Until it has passed once on GitHub, what it
    # gives back is printed as INFO, never PASS or FAIL, so a quirk of it can never hide the checks after it.
    # ASSISTANT_STRICT_MF=1 holds it to the same test as the other ways.
    strict_mf = os.environ.get("ASSISTANT_STRICT_MF") == "1"
    for name in ("click-100bpm.m4a", "click-100bpm-m4a-named.mp3", "click-100bpm-cbr.mp3", "click-100bpm-vbr.mp3"):
        got, how, good = heard(name, {})
        if got and how.startswith("windows") and not strict_mf:
            info(f"hearing {name} through Windows' own Media Foundation, {'about right' if good else 'NOT right'}",
                 how + " (information only until it has passed once; ASSISTANT_STRICT_MF=1 makes it count)")
            continue
        if not got and not ways:
            skip(f"hearing {name}", f"no way to hear it on this computer: {how}"
                 + (" (tests/fixtures/check_sound.py and decode_report.py look closer at Windows' own decoder)" if tc.WINDOWS else ""))
            continue
        check(f"hearing {name} ({how.split(':')[0] if got else 'nothing'})", good, how)


# ---------------------------------------------------------------- with Pillow hidden, the walk-away check

def no_pillow_check(card, drive, env):
    print("\n-- a PC that has no Pillow yet")
    code, _ = run_python(["-S", "-c", "import PIL"], timeout=60)
    if code == 0:
        skip("the walk-away check without Pillow", "Pillow could not be hidden from this Python (it is not in site-packages)")
        return
    before = sorted(os.listdir(drive))
    code, out = run_python(["-S", SCRIPTS / "night.py", "--source", card, "--check"], env=dict(env, ASSISTANT_NO_SIPS="1"))
    check("the walk-away check stops before anything is copied, naming Pillow and its one command (exit 2)",
          code == 2 and "Pillow" in out and "pip install pillow" in out and "Traceback" not in out
          and sorted(os.listdir(drive)) == before, out[-500:])


# ---------------------------------------------------------------- a whole backup

def whole_backup(work, how_pictures):
    """A whole backup, start to finish, the way night.py runs it for a photographer, with Claude's two looks
    answered here (each group its own shoot; the first moments as sneak peeks). Then a rename, and renames that
    change only capital letters. On Windows, the settle and a rename while a photo is held open.
    how_pictures: {} for this computer's own way, or {"ASSISTANT_NO_SIPS": "1"} for the PC way on a Mac."""
    home = work / "studio-home"
    home.mkdir(parents=True)
    env = dict(how_pictures, STUDIO_HOME=str(home))
    with environ(**how_pictures):
        ok, how = pictures.ready()
    if not ok:
        skip("a whole backup", f"this computer cannot make the small pictures yet: {how}")
        return
    print(f"      (small pictures are made with: {how})")
    card = work / "CARD night"
    photos = make_card(card, groups=(7, 6))
    before = card_snapshot(card)
    drive = work / "drive night"
    drive.mkdir()
    run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)
    night = ["night.py", "--source", card, "--name", "Côte card", "--date", "2026-11-06"]
    code, out = run(*night, env=env)
    session = drive / "2026-11-06 Côte card"
    st = session / "_studio"
    check("the backup copies, checks, makes previews and the contact sheet, then asks for the look (exit 4)",
          code == 4 and (st / "groups-sheet.png").is_file() and any((st / "previews").glob("*.jpg")), out[-600:])
    if code != 4:
        return
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    check("two shoots are found by the time between them", len(groups) == 2, str(len(groups)))
    shoots = [{"id": f"s{i}", "suggested": f"Shoot {i}", "groups": [g["id"]], "photos": g.get("count", 0),
               "recap": "Test frames.", "why": "test"} for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    code, out = run(*night, env=env)
    check("it sorts the photos into shoot folders and lays out the sneak-peek pages (exit 7)",
          code == 7 and (st / "peek-sheets.json").is_file() and any((st / "peek-sheets").glob("*.png")), out[-600:])
    if code != 7:
        return
    sheets = json.loads((st / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    spec = []
    for sid, s in sheets.items():
        n = s.get("moments") if isinstance(s.get("moments"), int) else len(s.get("list") or [])
        spec.append(f"{sid}=" + ",".join(str(k) for k in range(1, min(6, n) + 1)))
    code, out = run("peek_sheets.py", "pick", session, *spec, env=env)
    check("the sneak peeks are picked", code == 0, out[-400:])

    index = json.loads((st / "index.json").read_text(encoding="utf-8"))
    first = session / next(p["file"] for p in index["photos"] if p.get("original"))
    if tc.WINDOWS:
        fh = open(first, "rb")   # no FILE_SHARE_DELETE: Windows will not move this file or its folder now
        try:
            code, out = run(*night, env=env)
        finally:
            fh.close()
        held_open_outcome("the settle with a photo held open", code, out, lambda: first.is_file(),
                          lambda: (drive / ".studio" / session.name / "settled.json").is_file())
    code, out = run(*night, env=env)
    records = drive / ".studio" / session.name
    check("the backup finishes: the shoots are moved into place and the day folder is gone (exit 0)",
          code == 0 and (records / "settled.json").is_file() and not session.exists(), out[-600:])
    if not (records / "settled.json").is_file():
        return
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    bad, n = photos_match(drive, index, card)
    check("every photo is in its shoot folder under its exact name, byte for byte the card's", not bad and n == len(photos),
          f"{n} checked, {bad[:3]}")
    check("the sneak peeks have their pictures", any((records / "sneak-peeks").glob("*.jpg")))
    check("the card still holds exactly what it held", card_snapshot(card) == before)
    h = (hidden(drive / ".studio"), hidden(records))
    if h[0] is None:
        skip(f"the records are out of sight in {tc.FILES_APP}", "this computer has no hidden mark to check")
    else:
        check(f"the records are out of sight in {tc.FILES_APP} (the .studio folder and the backup's records folder)", all(h), str(h))

    # ---- a rename (on Windows, first with a photo held open), then renames of capital letters only
    def folder_of(sid):
        sh = json.loads((records / "shoots.json").read_text(encoding="utf-8"))["shoots"]
        return next(s.get("folder") for s in sh if s["id"] == sid)

    old = folder_of("s1")
    want = "2026-06-04 Côte d'Azur"
    rename = ["rename_shoot.py", records, "--shoot", "s1", "--name", "Côte d'Azur"]
    if tc.WINDOWS:
        idx = json.loads((records / "index.json").read_text(encoding="utf-8"))
        held = drive / next(p["file"] for p in idx["photos"] if p.get("original") and p["file"].startswith(old + "/"))
        fh = open(held, "rb")
        try:
            code, out = run(*rename, env=env)
        finally:
            fh.close()
        stopped = held_open_outcome("a rename with a photo held open", code, out,
                                    lambda: old in os.listdir(drive) and held.is_file(), lambda: folder_of("s1") == want)
        if stopped:
            code, out = run(*rename, env=env)
    else:
        code, out = run(*rename, env=env)
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    bad, n = photos_match(drive, index, card)
    check("the rename finishes with the name spelled exactly (accent and apostrophe), every photo checked",
          code == 0 and folder_of("s1") == want and want in os.listdir(drive) and old not in os.listdir(drive)
          and not bad and n == len(photos), f"{code} {folder_of('s1')!r} {bad[:3]} {out[-300:]}")
    code, out = run("rename_shoot.py", records, "--shoot", "s1", "--name", "côte d'azur", env=env)
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    bad, n = photos_match(drive, index, card)
    lower = "2026-06-04 côte d'azur"
    check("a rename of capital letters only is a rename: the folder and every photo take the new spelling",
          code == 0 and folder_of("s1") == lower and lower in os.listdir(drive) and want not in os.listdir(drive)
          and not bad and n == len(photos), f"{code} {folder_of('s1')!r} {os.listdir(drive)} {bad[:3]} {out[-300:]}")
    old2 = folder_of("s2")
    code, out = run("rename_shoot.py", records, "--shoot", "s2", "--name", "shoot 2", env=env)
    index = json.loads((records / "index.json").read_text(encoding="utf-8"))
    bad, n = photos_match(drive, index, card)
    check('the same with plain letters ("Shoot 2" to "shoot 2"), every photo checked against the card',
          code == 0 and folder_of("s2") == "2026-06-04 shoot 2" and "2026-06-04 shoot 2" in os.listdir(drive)
          and old2 not in os.listdir(drive) and not bad and n == len(photos), f"{code} {folder_of('s2')!r} {bad[:3]} {out[-300:]}")
    check("after all of it, the card still holds exactly what it held", card_snapshot(card) == before)


# ---------------------------------------------------------------- a page server outliving its starter

_STARTER = """import subprocess, sys, time
sys.path.insert(0, {scripts!r})
import this_computer as tc
quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tc.popen_detached([sys.executable, "-c", {detached!r}], **quiet)
subprocess.Popen([sys.executable, "-c", {plain!r}], **quiet)
print("started", flush=True)
time.sleep({linger})
"""


def detached_check(work):
    """A page server started with this_computer.popen_detached keeps running when the command that started it is
    swept away, the way a command runner ends a command. Tried against a stand-in started the plain way by the
    same command, which must NOT survive; if it does, this computer gave the test no way to tell the two apart
    and the line says SKIP.

    On a Mac: the command is started in a session of its own; once it has ended, its whole process group is
    killed (what a terminal or a command runner does to a finished command's group).
    On Windows (unproven on a real PC): the command is the root of a process group of its own; while it is still
    running, that group is sent Ctrl+Break, which ends every process in it that shares this console (what
    closing the command's window, or a Ctrl+Break there, does). Not a job object with "kill on close", and not
    taskkill /T: nothing started from inside them can outlive those (a child can only leave a job that allows it,
    and taskkill /T follows every child by its parent), so they would test nothing about popen_detached. (As far
    as is known, and not seen on a PC: Node, which Claude Code runs on, puts the commands it starts in a job that
    lets their own children leave it by themselves, so a job is not what ends a server there.)"""
    print("\n-- a page server started in the background, after the command that started it is swept away")
    marks = {k: work / f"still here {k}.txt" for k in ("detached", "plain")}
    for m in marks.values():
        if m.exists():
            m.unlink()

    def child(mark):
        return ("import time; from pathlib import Path; time.sleep(2.5); "
                f"Path({str(mark)!r}).write_text('yes', encoding='utf-8')")
    code = _STARTER.format(scripts=str(SCRIPTS), detached=child(marks["detached"]), plain=child(marks["plain"]),
                           linger=4 if tc.WINDOWS else 0)
    what = "a page server started in the background outlives the command that started it"
    import signal
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if tc.WINDOWS else {"start_new_session": True}
    errors = work / "starter errors.txt"
    with open(errors, "wb") as err:
        starter = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=err, env=child_env(), **kw)
    line = [""]
    reader = threading.Thread(target=lambda: line.__setitem__(0, starter.stdout.readline().decode("utf-8", "replace")))
    reader.daemon = True
    reader.start()
    reader.join(30)
    if "started" not in line[0]:
        starter.kill()
        try:
            said = errors.read_text(encoding="utf-8", errors="replace")[-400:]
        except OSError:
            said = ""
        check(what, False, "the command that starts it did not get going within 30 s. " + said)
        return
    swept, how = True, ""
    try:
        if tc.WINDOWS:
            os.kill(starter.pid, signal.CTRL_BREAK_EVENT)     # unproven on a real PC
            how = "its process group sent Ctrl+Break while it ran"
            try:
                starter.wait(10)
            except subprocess.TimeoutExpired:
                starter.kill()
        else:
            starter.wait(30)
            os.killpg(starter.pid, signal.SIGKILL)       # the Mac (and Linux) branch of this test
            how = "its process group killed once it had ended"
    except (OSError, subprocess.TimeoutExpired) as e:
        swept, how = False, f"{type(e).__name__}: {e}"
        try:
            starter.kill()
        except OSError:
            pass
    finally:
        try:
            starter.stdout.close()
        except OSError:
            pass
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not marks["detached"].exists():
        time.sleep(0.2)
    time.sleep(0.5)
    survived, control = marks["detached"].exists(), marks["plain"].exists()
    print(f"      (the command {how}; the server kept running: {survived}; the stand-in started the plain way: "
          f"{'kept running' if control else 'ended'})")
    if not swept or control:
        skip(what, "this computer gave the test no way to sweep the command away"
             + (f" ({how})" if not swept else " (the stand-in started the plain way survived too, so the two cannot be told apart)"))
        return
    check(what, survived, how)


def main():
    import locale
    print(f"This is a {tc.COMPUTER}, Python {sys.version.split()[0]}"
          + (", with Pillow" if pillow_here() else ", no Pillow") + ".")
    print(f"Scripts are started the way Claude starts them: UTF-8 mode {'on' if child_env().get('PYTHONUTF8') == '1' else 'off'}, "
          f"this computer's own text encoding {locale.getpreferredencoding(False)}.\n")
    # ASSISTANT_SMOKE_DIR: where the scratch folder goes (default: this computer's own temporary folder). On a PC
    # that is on the computer's own disk, which the backup allows; a pretend card and drive on one other drive
    # would be stopped, rightly, as "the same drive the photos are coming from".
    work = Path(tempfile.mkdtemp(prefix="assistant-pc-smoke-", dir=os.environ.get("ASSISTANT_SMOKE_DIR") or None))
    home = work / "studio-home"
    home.mkdir()
    env = {"STUDIO_HOME": str(home)}

    # ---- the helper
    d = datetime(2026, 10, 4, 9, 5)
    check("a date in words has no leading zero", tc.strftime(d, "%A, %B %-d, %Y · %-I:%M %p") == "Sunday, October 4, 2026 · 9:05 AM",
          tc.strftime(d, "%A, %B %-d, %Y · %-I:%M %p"))
    check("a date object works too", tc.strftime(date(2026, 3, 7), "%b %-d %Y") == "Mar 7 2026")
    check("a name with a colon, a question mark and a dot at the end is made safe",
          tc.safe_name('Card 10:30? "beach". ') == "Card 10 30 beach", tc.safe_name('Card 10:30? "beach". '))
    check("names Windows keeps for itself get an underscore, before any dot",
          tc.safe_name("CON") == "CON_" and tc.unreserved("aux.jpg") == "aux_.jpg" and tc.unreserved("Nul. Family") == "Nul_. Family"
          and tc.not_reserved("aux.jpg") == "aux_.jpg" and tc.unreserved("Beach") == "Beach",
          f'{tc.unreserved("aux.jpg")} {tc.unreserved("Nul. Family")} {tc.not_reserved("aux.jpg")}')
    long_on = tc.long_paths_on()
    print(f"      (long paths switched on here: {long_on})")
    deep = str(work)
    while len(deep) <= 270:
        deep = os.path.join(deep, "a" * 40)
    deep = os.path.join(deep, "IMG_4471.JPG")
    if tc.WINDOWS:
        check("a photo's place over 260 characters is too long for File Explorer, whatever the setting", tc.path_too_long(deep) is True)
        check("the Assistant's own files may go past 260 only where long paths are switched on",
              tc.records_path_too_long(deep) == (not long_on), f"{tc.records_path_too_long(deep)} vs long paths {long_on}")
    else:
        check("a Mac has no 260-character limit", tc.path_too_long(deep) is False and tc.records_path_too_long(deep) is False)
    room = tc.disk(work)
    check("room on a drive can be asked", bool(room) and room[1] > 0, str(room))
    vols = tc.volumes()
    check("the drives plugged in can be listed", len(vols) >= 1 and all(v["total"] > 0 for v in vols), str(vols)[:200])
    own = [v["shown"] for v in vols if v["system"]]
    print(f"      (drives: {', '.join(v['shown'] + (' (this computer)' if v['system'] else '') for v in vols)})")
    if tc.WINDOWS:
        check("exactly one drive is marked as the computer's own disk (the one Windows starts from)", len(own) == 1, str(own))
    else:
        # a Mac lists its Recovery volume beside its own disk; both are on the one disk
        check("the computer's own disk is marked as its own", len(own) >= 1, str(own))
    found = tc.cards()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        check("no memory card is seen where there is none (GitHub's machine has no card reader)", found == [], str(found))
    else:
        print(f"      (memory cards in right now: {', '.join(c['shown'] for c in found) or 'none'})")
        check("the memory cards plugged in can be listed", isinstance(found, list), repr(found))
    pics = tc.known_folder("Pictures")
    check("the Pictures folder is found, and is a folder", pics is not None and Path(pics).is_dir(), str(pics))

    # ---- a whole copy-and-check, with an awkward name
    card = work / "CARD"
    photos = make_card(card)
    card_before = card_snapshot(card)
    drive = work / "drive"
    drive.mkdir()
    code, out = run("backup.py", "--source", card, "--dest", drive, "--name", "Renée's card: 10:30", "--date", "2026-11-06", env=env)
    check("the copy-and-check of a pretend card finishes clean", code == 0, out[-600:])
    session = drive / "2026-11-06 Renée's card 10 30"
    check("the day folder has a name both computers accept", session.is_dir(), str([p.name for p in drive.iterdir()]))
    studio = session / "_studio"
    try:
        manifest = json.loads((studio / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        manifest = {"files": {}}
        check("the records can be read back as UTF-8", False, str(e))
    files = manifest.get("files", {})
    check("every file on the card is in the records and marked checked",
          len(files) == len(photos) + 1 and all(v.get("dest", {}).get("ok") for v in files.values()), f"{len(files)} files")
    check("the records spell paths one way on both computers (forward slashes)", files and not any("\\" in k for k in files), str(list(files)[:2]))
    same = all(sha(p) == sha(session / p.relative_to(card)) for p in photos)
    check("every photo on the drive matches the card byte for byte", same)
    check("the card still holds exactly what it held, byte for byte", card_snapshot(card) == card_before)
    try:
        page = (studio / "report.html").read_bytes().decode("utf-8")
        check("the report page is UTF-8 and carries the accent", "Renée" in page)
    except (OSError, UnicodeDecodeError) as e:
        check("the report page is UTF-8 and carries the accent", False, str(e))
    try:
        index = json.loads((studio / "index.json").read_text(encoding="utf-8"))
        check("the index knows when each photo was taken", sum(1 for p in index["photos"] if p.get("taken")) == len(photos))
    except (OSError, ValueError, KeyError) as e:
        check("the index knows when each photo was taken", False, str(e))
    def copies():
        """Each copied file's identity on the drive: its file number, size and time. A copy made again, or a
        file written over, changes at least one of them."""
        out = {}
        for p in sorted(card.rglob("*")):
            q = session / p.relative_to(card)
            if p.is_file() and q.is_file():
                st = os.stat(q)
                out[q.relative_to(session).as_posix()] = (st.st_ino, st.st_size, st.st_mtime_ns)
        return out
    copies_before = copies()
    code2, out2 = run("backup.py", "--source", card, "--dest", drive, "--name", "Renée's card: 10:30", "--date", "2026-11-06", env=env)
    check("running the same backup again copies nothing and changes nothing (every copy the same file, untouched)",
          code2 == 0 and copies_before and copies() == copies_before
          and all(sha(p) == sha(session / p.relative_to(card)) for p in photos), out2[-300:])
    if tc.WINDOWS:
        check("the records folder is hidden in File Explorer", hidden(studio), str(hidden(studio)))

    # ---- the Studio File, the walk-away check, the queue
    helper = "Shérman 📷"
    code, out = run("studio_file.py", "set", "--drive", drive, "--offered", "2", "--file-names", "shoot", "--name", helper, env=env)
    try:
        kept = helper in (home / "studio.json").read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        kept = False
    check("the Studio File saves a helper's name with an accent and an emoji, exactly (read back as UTF-8)",
          code == 0 and kept, out[-400:])
    code, out = run("studio_file.py", "show", env=env)
    check("and shows it back, accent and emoji and all", code == 0 and helper in out, out[-300:])
    code, out = run("studio_file.py", "render", "Smith Family", "2026-10-04", env=env)
    check('the "Smith Family, Oct 4 2026" folder pattern is written right', out.strip() == "Smith Family, Oct 4 2026", out.strip())
    code, out = run("studio_file.py", "drives", env=env)
    check("the drives command runs", code == 0, out[-300:])
    code, out = run("studio_file.py", "cards", env=env)
    check("the cards command runs", code == 0, out[-300:])
    pictures_ok, pictures_how = pictures.ready()
    if pictures_ok:
        code, out = run("night.py", "--source", card, "--check", env=env)
        check("the walk-away check passes (card readable, room on the drive)", code == 0 and "PREFLIGHT OK" in out, out[-400:])
    else:
        skip("the walk-away check passes", f"this computer cannot make the small pictures yet ({pictures_how}); "
             "that it stops in plain words is checked below")
    shoot = "Garcia family 🌊"
    code, out = run("edit_queue.py", "add-manual", "--name", shoot, "--due", "2w", env=env)
    code_l, out_l = run("edit_queue.py", "list", env=env)
    try:
        kept = shoot in (home / "queue.json").read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        kept = False
    check("the editing queue takes a shoot with an emoji in its name, kept exactly and listed back exactly",
          code == 0 and code_l == 0 and kept and shoot in out_l, (out + out_l)[-400:])
    code, out = run("edit_queue.py", "page", env=env)
    try:
        page = (home / "queue.html").read_bytes().decode("utf-8")
        # the page carries its list as JSON for its own script, where the emoji is written 🌊
        ok = shoot in page or json.dumps(shoot)[1:-1] in page
    except (OSError, UnicodeDecodeError):
        ok = False
    check("and its page is written as UTF-8, the emoji too", code == 0 and ok, out[-300:])
    code, out = run("home.py", "hello", env=env)
    check("the hello check runs", code == 0, out[-300:])
    code, out = run("cards.py", "check", card, env=env)
    check("the card ledger can look at a card", code == 0, out[-300:])
    no_pillow_check(card, drive, env)

    detached_check(work)

    # ---- saving over a file another program has open for a moment
    target = work / "list.json"
    target.write_text("old", encoding="utf-8")

    def hold():
        with open(target, "r", encoding="utf-8") as fh:
            fh.read()
            time.sleep(0.25)
    t = threading.Thread(target=hold)
    t.start()
    time.sleep(0.05)
    tmp = work / "list.json.part"
    tmp.write_text("new", encoding="utf-8")
    try:
        tc.replace(tmp, target)
        ok = target.read_text(encoding="utf-8") == "new"
    except OSError as e:
        ok = False
        print("   ", e)
    t.join()
    check("a list can be saved while another program is reading it", ok)

    held_rename_checks(work)
    pictures_checks(work)
    sound_checks()

    # ---- whole backups: this computer's own way; on a Mac also the PC way
    print("\n-- a whole backup, start to finish" + (" (the Mac's own way: sips)" if pictures.use_sips() else ""))
    whole_backup(work / "whole", {})
    if pictures.use_sips():
        print("\n-- a whole backup again, the PC way on this Mac (sips switched off: the JPEG inside each photo, and Pillow)")
        _tag[0] = "(the PC way) "
        try:
            if pillow_here():
                whole_backup(work / "whole the PC way", {"ASSISTANT_NO_SIPS": "1"})
            else:
                skip("a whole backup", "Pillow is not installed for this Python; the PC way needs it (python -m pip install pillow)")
        finally:
            _tag[0] = ""

    failed = results.count(False)
    print(f"\n{sum(results)} of {len(results)} passed" + (f", {len(skipped)} skipped (each says why above)" if skipped else "") + "."
          + ("" if not failed else f"  {failed} FAILED: see the lines above."))
    if failed:
        print(f"(scratch folder, kept to look at: {work})")
        keep = os.environ.get("ASSISTANT_SMOKE_KEEP")    # GitHub copies it here, then uploads it with the results
        if keep:
            try:
                shutil.copytree(str(work), str(Path(keep) / work.name), symlinks=True)
                print(f"(and copied to {Path(keep) / work.name})")
            except (OSError, shutil.Error) as e:
                print(f"(could not copy it to {keep}: {e})")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
