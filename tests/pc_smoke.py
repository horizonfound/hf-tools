#!/usr/bin/env python3
"""The parts of the Assistant that should already work on a Windows PC, tried for real.

Runs the same on a Mac and on Windows, in scratch folders it makes itself (never the real ~/.studio,
never a real drive). GitHub runs it on a real Windows machine on every push (.github/workflows/
check-pc.yml), which is how a PC gets tested without anyone here owning one: no screen, no card, no
CapCut, no Claude app, but real Windows.

    python3 tests/pc_smoke.py        Pillow is the only add-on it uses, and only for the checks that need it
    python3 tests/pc_smoke.py --only posts      just the posts part (below), in a few seconds
    python3 tests/pc_smoke.py --only followup   just the PC follow-up's part (below), in a few seconds
    python3 tests/pc_smoke.py --only backup     just the whole backups (below)

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
    ASSISTANT_SMOKE_PORT=<port>     the first of five ports for the little servers of the posts part and the
                                    follow-up's part, this one and the four after it (default: ports the computer
                                    hands out as free)

What it tries:
  - the helper that knows both computers: dates in words, safe names, names Windows keeps for itself, long
    paths, room on a drive, the list of drives;
  - a whole copy-and-check of a pretend card with an accent and a colon in its name; the records and the
    report page written as UTF-8; the same card again with nobody reading what backup.py says (a closed pipe:
    on Windows "invalid argument", for real), every file still copied and checked; a name with an emoji in the
    Studio File and the editing queue; the walk-away check; hiding the records folder; and, with Pillow hidden,
    the walk-away check stopping in plain words;
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
  - posts: a post kit started from a folder of finished photos (its folder named with an accent, a curly apostrophe
    and an emoji); what they said kept word for word from a file (with the mark some PC editors put first) and from
    --text; the kit's facts with the day in words; then, the PC way (Pillow; on a Mac with sips switched off), the
    kit built (singles, carousel slides, stories, the reel cover, each its size, and a photo the camera stored
    sideways the right way up in every one), a new carousel order made (the earlier slides set aside, byte for
    byte, under the slides lock), the reel and carousel pickers' small copies (upright, never blown up), and the
    kit's pieces in the posting queue with their small pictures; the posting queue with an emoji and curly quotes
    (rhythm, add, made, ready, the day's reminder once, the page), every file UTF-8; a lock held by one program
    keeping a second one out and let go when the holder dies (this_computer.try_lock, still_running; a computer
    with no lock on its own disk FAILs, never SKIPs); Canva's downloads (canva_kit.py fetch, with Windows' own
    curl.exe on a PC, which must be there) from a stand-in on 127.0.0.1, never the internet: in under their
    names, a fresh export setting the earlier ones aside, a dead link changing nothing; and the posting server
    started in the background, serving the home page, the posting page, a kit page (never its records, its hidden
    folder or a photo; a name with a colon refused, and the folder button opening nothing for one, nor for a
    network path like //computer/share, and saying so at once) and a piece's picture, never the Studio folder's
    own files through a picture folder ("%2e%2e") nor a folder's list, nothing at all for a request naming another
    host, then stopped by its own number (on the port it said); a dead Canva link into a folder the kit didn't
    have leaving no empty folder behind; on a PC the build's "Reel:" line quoted for PowerShell and Git Bash. On a
    computer without Pillow the PC-way part says SKIP;
  - the PC follow-up of Nov 6 (also alone: --only followup): this_computer.run_curl running this computer's own
    curl exactly as given (on a PC one more try, with --ssl-revoke-best-effort, only when Windows can't ask
    whether a certificate was withdrawn; a stand-in curl shows each case on both computers); the Instagram grid's
    list read from a file saved the Windows PowerShell way (UTF-16) or exactly as the browser pane gave it;
    the posting queue and the home page's record saved from six threads at once; this computer's own pages
    opened straight, never through a proxy set in the environment (open_local, home.url, the picker's wait);
    the editing queue's page server (only its own small pictures, never "%2e%2e" or a folder's list, nothing for
    another host, 100 presses at once all answered); CapCut's waiting list (a hand-damaged entry left out, and
    `capcut.py open --closed` adding a waiting reel without asking whether CapCut is open: on a Mac with a
    stand-in for `open`, on a PC with no CapCut installed); the PC folder window's answer read back (a mark in
    front, UTF-16, a line broken in two, a warning after it; on Windows a real Windows PowerShell writing a
    folder named "Café “shoot” 🌊"); the PC quoting of a command's values (kit._pc_arg); the report's own page
    server (serve_report.py) started and stopped by its own number: the page for 127.0.0.1 and localhost, a 403
    for any other host, another port, no port or no Host (nothing handed out, no name saved, no rename asked),
    and report_url() and queue_url() finding running servers with a dead proxy set in the environment; its Open
    photo folder refusing //127.0.0.1/c$ and \\\\127.0.0.1\\c$ as text, never asking Windows about them (real
    on Windows; on a Mac only simulated, this_computer.WINDOWS set in a program of its own), while a report whose
    photos are on a network drive of its own still opens that folder (a pretend share whose lookups are stood
    in) and a look-alike of it is refused; and every say()
    changed on Nov 6 (backup, sort and so rename_shoot, settle, sneak_peeks, posts, return_watch, reel, night)
    carrying on when nobody reads what it prints (on a Mac a broken pipe; on Windows "invalid argument",
    EINVAL, for real);
  - a whole backup start to finish (copy and check, index, groups and contact sheet, the look, the sort, the
    sneak-peek pages, the pick, the sneak peeks, the settle), every photo checked against the card, the card
    unchanged, the records hidden, then a rename to an accented name and two renames of capital letters only.
    Then the same backup twice more, each stopping once settled: once read to the end, once with night.py's
    output read for one line and then closed every time it runs (`| head -1`; the first time with its errors
    down the same pipe), which must finish with the same exit codes and the same records, file for file.
    On a Mac the first backup runs twice: the Mac's own way, and the PC way (the JPEG inside each photo, and
    Pillow). On Windows the settle and a rename also run while another program holds a photo open.

What it does NOT try: the beat of each song (tests/fixtures/check_sound.py), made-up RAW files from six makers
(tests/pc_pictures.py), the page servers (tests/pc_servers.py), the backup's own promises in depth
(tests/backup_safety.py), the pickers' own machinery in depth (tests/pc_arrange.py), CapCut itself, the pickers'
pages in a browser (tests/arrange_check.py, on a Mac), the folder picker's window, Canva itself, Instagram.
docs/pc-readiness-2026-11-06.md has the list.
"""
import base64
import contextlib
import hashlib
import html
import importlib.util
import json
import os
import re
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

def run_nobody_reading(args, env, errors_to=None):
    """(exit code, what could be seen) of a script started the way Claude starts it, whose output is read for one line
    and then closed, the way `| head -1` leaves it once it has its line: everything the script says after that has
    nobody to read it (on a Mac a broken pipe; on Windows "invalid argument"). errors_to: a file its error output
    goes to, read back afterwards; None sends its errors down the same pipe (`2>&1 | head -1`), lost with the rest."""
    err = open(errors_to, "wb") if errors_to else None
    try:
        p = subprocess.Popen([sys.executable, *map(str, args)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=err if err else subprocess.STDOUT, env=child_env(env))
    finally:
        if err:
            err.close()
    first = [b""]
    reader = threading.Thread(target=lambda: first.__setitem__(0, p.stdout.readline()))
    reader.daemon = True
    reader.start()
    reader.join(STEP_TIMEOUT)
    if reader.is_alive():                # it said nothing within the time a step may take: stopped, a FAIL
        p.kill()
        reader.join(30)
    p.stdout.close()                     # the reader has gone away
    try:
        code = p.wait(STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        code = 124
    said = first[0].decode("utf-8", "replace")
    if errors_to:
        said += Path(errors_to).read_bytes().decode("utf-8", "replace")
    return code, said + (f"\nTIMED OUT after {STEP_TIMEOUT} s" if code == 124 else f"\n(exit {code})")


def whole_backup(work, how_pictures, nobody_reading=None):
    """A whole backup, start to finish, the way night.py runs it for a photographer, with Claude's two looks
    answered here (each group its own shoot; the first moments as sneak peeks). Then a rename, and renames that
    change only capital letters. On Windows, the settle and a rename while a photo is held open.
    how_pictures: {} for this computer's own way, or {"ASSISTANT_NO_SIPS": "1"} for the PC way on a Mac.
    nobody_reading: None for all of that. True or False for one of two twins that stop once the backup has finished
    (no renames, nothing held open), to be compared (nobody_reading_checks): True with night.py's output read for one
    line and then closed every time it runs; False read to the end. Returns True when the backup finished."""
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
    unseen = []                          # what night.py said where nobody was reading, but it could still be seen

    def run_night():
        """night.py, run the way this backup runs it."""
        if not nobody_reading:
            return run(*night, env=env)
        n = len(unseen)
        # the first time as `2>&1 | head -1` (its errors gone with the rest); after that `| head -1`, its errors in a file
        code, said = run_nobody_reading([SCRIPTS / night[0], *night[1:]], env,
                                        errors_to=None if n == 0 else work / f"night {n + 1} errors.txt")
        unseen.append(said)
        return code, said
    code, out = run_night()
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
    code, out = run_night()
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
    if tc.WINDOWS and nobody_reading is None:
        fh = open(first, "rb")   # no FILE_SHARE_DELETE: Windows will not move this file or its folder now
        try:
            code, out = run(*night, env=env)
        finally:
            fh.close()
        held_open_outcome("the settle with a photo held open", code, out, lambda: first.is_file(),
                          lambda: (drive / ".studio" / session.name / "settled.json").is_file())
    code, out = run_night()
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
    if nobody_reading is not None:
        if nobody_reading:
            gone = [s for s in unseen if "Traceback" in s]
            check("and nothing went wrong out of sight (no Traceback on the error output it still had)", not gone,
                  (gone[0] if gone else "")[-500:])
        return True

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


_CLOCK = re.compile(r"\d{4}-\d\d-\d\d[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:[+-]\d\d:?\d\d|Z)?")
_FILE_NUMBERS = {"ino", "inode", "dev", "device", "mtime", "mtime_ns", "ctime", "ctime_ns", "atime", "atime_ns",
                 "birthtime", "identity", "ident", "file_id", "volume_uuid", "uuid"}
_HOW_LONG = re.compile(r"second|took|elapsed|duration")          # keys of a number that says how long something took
_TEXTS = (".json", ".html", ".htm", ".md", ".txt", ".xmp", ".csv", ".log")
_WORDS_CLOCK = [   # the clock in a page's words: "Friday, November 6 · 5:00 pm", "3 sec", "2 min"
    (re.compile(r"\b(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day, (?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December) \d{1,2}\b"), "<DAY>"),
    (re.compile(r"\b\d{1,2}:\d\d ?(?:am|pm|AM|PM)\b"), "<TIME>"),
    (re.compile(r"\b\d+(?:\.\d+)? (?:seconds?|sec|minutes?|min|hours?|hrs)\b"), "<TOOK>")]


def _clock(m):
    """A time written by the clock of this run (today, give or take a day) is taken out; any other time is kept (when
    each photo was taken is part of the records, and has to be the same in both)."""
    try:
        d = date.fromisoformat(m.group(0)[:10])
    except ValueError:
        return m.group(0)
    return "<CLOCK>" if abs((d - date.today()).days) <= 1 else m.group(0)


def run_view(root):
    """What a backup left on its drive, put so two runs can be compared: {place: what is there}. Photos and pictures
    by their bytes; records and pages as text, with what differs between any two runs taken out: the run's own
    folder, this run's clock (never when a photo was taken), how long a step took, and the drive's file numbers."""
    root = Path(root)
    forms = set()
    for p in (root, root.resolve()):
        for f in (str(p), p.as_posix(), p.as_uri()):     # as_uri: a page's link to a folder (file:///...%20...)
            forms.update((f, json.dumps(f)[1:-1], html.escape(f), html.escape(json.dumps(f)[1:-1])))
    forms = sorted(forms, key=len, reverse=True)
    flags = re.IGNORECASE if tc.WINDOWS else 0          # a PC's paths ignore upper and lower case

    def text(t):
        for f in forms:
            t = re.sub(re.escape(f), "<RUN>", t, flags=flags)
        return _CLOCK.sub(_clock, t)

    def value(x, key=None):
        if key in _FILE_NUMBERS:
            return "<N>"
        if isinstance(x, dict):
            return {text(k): value(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [value(v, key) for v in x]
        if isinstance(x, str):
            return text(x)
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            if x > 1_000_000_000 or (key and _HOW_LONG.search(key)):
                return "<N>"                             # a time in seconds since 1970, a file number, how long it took
        return x
    import unicodedata
    out = {}
    drive = root / "drive night"
    for p in sorted(drive.rglob("*")):
        if not p.is_file():
            continue
        place = unicodedata.normalize("NFC", p.relative_to(drive).as_posix())
        data = p.read_bytes()
        if p.suffix.lower() not in _TEXTS:
            out[place] = hashlib.sha256(data).hexdigest()
            continue
        t = data.decode("utf-8", "replace")
        try:
            t = json.dumps(value(json.loads(t)), sort_keys=True, ensure_ascii=False) if p.suffix.lower() == ".json" else None
        except ValueError:
            t = None
        if t is None:                                    # a page, or a record that isn't JSON
            t = text(data.decode("utf-8", "replace"))
            for rx, said in _WORDS_CLOCK:
                t = rx.sub(said, t)
        out[place] = t
    return out


def records_differ(a, b):
    """Plain words for every difference between what two backups left on their drives; empty when there is none."""
    va, vb = run_view(a), run_view(b)
    said = [f"only in the {'first' if k in va else 'second'}: {k}" for k in sorted(set(va) ^ set(vb))]
    for k in sorted(set(va) & set(vb)):
        if va[k] != vb[k]:
            if len(va[k]) == 64 and len(vb[k]) == 64 and "<" not in va[k]:
                said.append(f"{k}: not the same bytes")
                continue
            at = next((i for i, (x, y) in enumerate(zip(va[k], vb[k])) if x != y), min(len(va[k]), len(vb[k])))
            said.append(f"{k}: {va[k][max(0, at - 60):at + 60]!r} vs {vb[k][max(0, at - 60):at + 60]!r}")
    return said


def nobody_reading_checks(work):
    """The same backup twice more, each stopping once it has finished: once read to the end, once with night.py's
    output read for one line and then closed every time it runs (`| head -1`). Nov 6, closing the last gaps: before,
    on a Mac too, the copy stopped at its first line (exit 120) with the card not copied."""
    print("\n-- the same backup twice more: once read to the end, once with nobody reading what it says after its first "
          "line (`| head -1`)")
    done = {}
    for nobody, name in ((False, "twin, read"), (True, "twin, nobody reading")):
        _tag[0] = "(nobody reading) " if nobody else "(read to the end) "
        try:
            done[nobody] = whole_backup(work / name, {}, nobody_reading=nobody)
        finally:
            _tag[0] = ""
    if not (done.get(False) and done.get(True)):
        return                           # the line that says why has FAILED above
    diffs = records_differ(work / "twin, read", work / "twin, nobody reading")
    check("with nobody reading, the backup finishes with the same records as the one read to the end: the same files in the "
          "same places, photos and pictures byte for byte, every record and page the same (the run's own folder, the clock "
          "and file numbers aside)", not diffs, f"{len(diffs)} differences: " + "; ".join(diffs[:5]))


# ---------------------------------------------------------------- posts: a post kit, the pickers, the posting queue, Canva

KIT_NAME = "Zoë’s beach 🌊"                 # an accent, a curly apostrophe and an emoji, in a folder name too
POSTS_SHOOT = "Zoë’s “golden hour” 🌊"      # the same, with curly double quotes
RED = (230, 20, 20)


def smoke_ports(n):
    """n ports for this test's own little servers: ASSISTANT_SMOKE_PORT and the ones after it when that is set,
    otherwise ports the computer hands out as free right now."""
    import socket
    base = os.environ.get("ASSISTANT_SMOKE_PORT")
    if base:
        return [int(base) + i for i in range(n)]
    out, held = [], []
    try:
        for _ in range(n):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", 0))
            held.append(s)
            out.append(s.getsockname()[1])
    finally:
        for s in held:
            s.close()
    return out


def kit_photos(folder):
    """Three finished photos, taken Monday June 1, 2026 in the evening: a wide one, a tall one, and one the camera
    stored sideways (600 x 400 in the file, Exif orientation 6: it shows 400 x 600). The sideways one has a red block
    in the top-left corner of its stored pixels, which shows top-right once it is the right way up."""
    folder.mkdir(parents=True)
    t = datetime(2026, 6, 1, 17, 30)

    def marked(bx, by):
        return RED if bx < 20 and by < 20 else (40 + bx * 2, 90 + by, 160)
    (folder / "Beach 01.jpg").write_bytes(jpeg_bytes(600, 400, lambda bx, by: (40, 120, 200), exif_blob(t)))
    (folder / "Beach 02.jpg").write_bytes(jpeg_bytes(400, 600, lambda bx, by: (200, 160, 40), exif_blob(t + timedelta(minutes=5))))
    (folder / "Beach 03 sideways.jpg").write_bytes(jpeg_bytes(600, 400, marked, exif_blob(t + timedelta(minutes=9), orientation=6)))


def _is_red(c):
    r, g, b = c[:3]
    return r > 150 and g < 90 and b < 90


def red_corners(path, pad=None):
    """Which corners of the photo inside a picture are red: a set of "top-left", "top-right", "bottom-left",
    "bottom-right". pad: the colour a padded picture is filled with, so the photo inside it is found first."""
    from PIL import Image
    try:
        with Image.open(path) as im0:
            im = im0.convert("RGB")
    except Exception:  # noqa: BLE001
        return set()
    w, h = im.size
    x0, y0, x1, y1 = 0, 0, w, h
    if pad:
        def is_pad(c):
            return all(abs(a - b) <= 12 for a, b in zip(c, pad))
        xs = [x for x in range(0, w, 2) if not is_pad(im.getpixel((x, h // 2)))]
        ys = [y for y in range(0, h, 2) if not is_pad(im.getpixel((w // 2, y)))]
        if not xs or not ys:
            return set()
        x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    bw, bh = x1 - x0, y1 - y0
    spots = {"top-left": (0.08, 0.08), "top-right": (0.92, 0.08), "bottom-left": (0.08, 0.92), "bottom-right": (0.92, 0.92)}
    return {k for k, (fx, fy) in spots.items() if _is_red(im.getpixel((x0 + int(fx * bw), y0 + int(fy * bh))))}


def size_on_disk(path):
    """(width, height) of a picture, or None when it is not one this test can open."""
    from PIL import Image
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001  (a picture that can't be opened FAILs its check; it never stops the test)
        return None


def content_box(path, pad):
    """(width, height) of the photo inside a padded picture."""
    from PIL import Image
    try:
        with Image.open(path) as im0:
            im = im0.convert("RGB")
    except Exception:  # noqa: BLE001
        return (0, 0)
    w, h = im.size

    def is_pad(c):
        return all(abs(a - b) <= 12 for a, b in zip(c, pad))
    xs = [x for x in range(w) if not is_pad(im.getpixel((x, h // 2)))]
    ys = [y for y in range(h) if not is_pad(im.getpixel((w // 2, y)))]
    return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) if xs and ys else (0, 0)


def half_made(folder):
    """Scratch pictures left anywhere under a folder: kit.py's '.part-<process>-<name>', pictures.make_jpeg's
    '<name>.part', and the pickers' PC-way '.p-<tag>.jpg' (arrange.py). Empty when there are none."""
    return sorted(p.name for p in folder.rglob("*")
                  if p.name.startswith((".part", ".p-")) or p.name.endswith(".part"))


def shows(page, name):
    """Whether a page carries a name: as it is, as the page's HTML writes it, or inside the JSON its script reads."""
    return any(form in page for form in (name, html.escape(name), json.dumps(name)[1:-1]))


def listing(folder):
    """The names in a folder as Windows or the Mac keeps them, accents written one way (NFC)."""
    import unicodedata
    try:
        return sorted(unicodedata.normalize("NFC", n) for n in os.listdir(folder))
    except OSError:
        return []


class _StandIn:
    """A stand-in for Canva's download links: a little server on 127.0.0.1 that hands out the bytes it is given
    for each path, and 404 for anything else. Nothing here goes near the internet."""

    def __init__(self, port):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        files, seen = {}, []

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.split("?", 1)[0]
                seen.append(self.path)
                body = files.get(path)
                self.send_response(200 if body is not None else 404)
                self.send_header("Content-Type", "image/jpeg" if body is not None else "text/plain")
                self.send_header("Content-Length", str(len(body or b"")))
                self.end_headers()
                self.wfile.write(body or b"")

            def log_message(self, *a):
                pass
        self.files, self.seen = files, seen
        self.srv = HTTPServer(("127.0.0.1", port), H)
        self.port = self.srv.server_address[1]
        self.thread = threading.Thread(target=self.srv.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def url(self, path, sig):
        return f"http://127.0.0.1:{self.port}{path}?X-Amz-Signature={sig}"

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()


def ask(port, method, path, host=None, body=None, no_host=False):
    """(status, body) of one request to a page server of the Assistant's on 127.0.0.1, sent exactly as given: the
    address is not tidied (so "%2e%2e" arrives as written), and Host is this one when given (a page on another site
    that has been pointed at this computer still carries its own name there); no_host: no Host line at all.
    (None, why) when nothing answered."""
    import http.client
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        if not no_host:
            c.putheader("Host", host or f"127.0.0.1:{port}")
        if body is not None:
            b = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            c.putheader("Content-Type", "application/json")
            c.putheader("Content-Length", str(len(b)))
            c.endheaders(b)
        else:
            c.endheaders()
        r = c.getresponse()
        return r.status, r.read()
    except OSError as e:
        return None, str(e).encode("utf-8", "replace")
    finally:
        c.close()


def lock_checks(work):
    """A lock held by one program keeps a second one out, and is let go when the holder dies: this_computer.try_lock
    (the Mac's fcntl.flock; on a PC msvcrt.locking), what kit.py and arrange.py hold while slides are changed."""
    print("\n-- a lock held by one program, across two programs")
    folder = work / "lock Côte"
    folder.mkdir()
    lock = folder / "slides.lock"
    code = ("import sys, time\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import this_computer as tc\n"
            f"f = open({str(lock)!r}, 'a+b')\n"
            "got = tc.try_lock(f)\n"
            "print('held' if got is True else 'not held: %r' % (got,), flush=True)\n"
            "time.sleep(120)\n")
    holder = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=child_env())
    line = [""]
    reader = threading.Thread(target=lambda: line.__setitem__(0, holder.stdout.readline().decode("utf-8", "replace")))
    reader.daemon = True
    reader.start()
    reader.join(30)
    f2 = None
    try:
        if line[0].strip() != "held":
            # Never a SKIP (Nov 6, test review): this folder is the test's own scratch folder on the computer's own
            # disk (NTFS on a PC, APFS on a Mac), which always has locks. None there means the lock code itself went
            # wrong (on a PC: msvcrt.locking raised something other than "busy"), and kit.py and arrange.py would
            # then change slides with no lock at all.
            why = line[0].strip() or "no answer within 30 s"
            if "not held: None" in why:
                why = (f"try_lock said None on this computer's own disk ({work}), which always has locks"
                       + ("; ASSISTANT_SMOKE_DIR points somewhere else: try a folder on this computer's own disk"
                          if os.environ.get("ASSISTANT_SMOKE_DIR") else ""))
            check("the first program takes the lock", False, why)
            return
        f2 = open(lock, "a+b")
        second = tc.try_lock(f2)
        check("while one program holds the lock, a second one is kept out (try_lock says busy)", second is False, repr(second))
        if second is True:
            tc.unlock(f2)
        alive = tc.still_running(holder.pid)
        check("and the holder is seen as still running", alive is True, repr(alive))
        holder.kill()
        holder.wait(30)
        got, t0 = None, time.monotonic()
        while time.monotonic() - t0 < 15:          # Windows lets go of a dead program's locks "depending on resources"
            got = tc.try_lock(f2)
            if got is True:
                break
            time.sleep(0.2)
        check("once the holder has died, the lock is let go and the second program takes it", got is True,
              f"{got!r} after {time.monotonic() - t0:.1f} s")
        if got is True:
            tc.unlock(f2)
        gone = tc.still_running(holder.pid)
        check("and the holder is seen as ended", gone is False, repr(gone))
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(30)
        try:
            holder.stdout.close()
        except OSError:
            pass
        if f2 is not None:
            f2.close()


def posts_checks(work):
    """A post kit made and built (the PC way: Pillow, the photo the right way up), its words, the picker's small
    copies, the posting queue with an emoji and curly quotes, a lock across two programs, Canva's downloads from a
    stand-in on 127.0.0.1, and the posting server started, serving the home page, and stopped."""
    print("\n-- posts: a post kit, the picker's small copies, the posting queue, Canva, the posting server")
    home = work / "posts studio-home"
    home.mkdir()
    pc_way = {"ASSISTANT_NO_SIPS": "1"} if pictures.use_sips() else {}
    can_build = pillow_here()
    env = dict(pc_way, STUDIO_HOME=str(home)) if can_build else {"STUDIO_HOME": str(home)}
    photos = work / "kit photos"
    kit_photos(photos)
    photos_before = {p.name: sha(p) for p in photos.iterdir()}
    (work / "kit drive").mkdir()
    code, out = run("posts.py", "setup", "--home", work / "kit drive" / "The Assistant", env=env)
    check("the folder for their posts is made (posts.py setup)", code == 0, out[-300:])
    code, out = run("kit.py", "start", "--folder", photos, "--name", KIT_NAME, env=env)
    content = work / "kit drive" / "The Assistant" / "Your Content"
    want = "2026-06-01 " + KIT_NAME
    check("a post kit is started from a folder of finished photos, its folder named exactly (accent, curly apostrophe, emoji)",
          code == 0 and want in listing(content), f"{code} {listing(content)} {out[-300:]}")
    if code != 0:
        return
    kit = content / want
    said = work / "said by them.txt"
    said.write_bytes("\ufeffThe Garcias 🌊, a “windy” morning\n".encode("utf-8"))   # with the mark some PC editors put first
    code, out = run("kit.py", "told", "beach", "--text-file", said, env=env)
    code2, out2 = run("kit.py", "told", "beach", "--text", "and a lot of laughing 😄", env=env)
    try:
        told = json.loads((kit / ".kit" / "told.json").read_bytes().decode("utf-8"))["text"]
    except (OSError, ValueError, KeyError) as e:
        told = f"(unreadable: {e})"
    check("what they said about the shoot is kept word for word from a file (emoji, curly quotes; the mark at the start dropped)",
          code == 0 and told.startswith("The Garcias 🌊, a “windy” morning"), f"{code} {told!r} {out[-200:]}")
    check("and from --text, an emoji and all, added after it", code2 == 0 and told == "The Garcias 🌊, a “windy” morning\nand a lot of laughing 😄",
          f"{code2} {told!r} {out2[-200:]}")
    code, out = run("kit.py", "facts", "beach", env=env)
    try:
        facts = json.loads(out[out.find("{"):out.rfind("}") + 1])   # the JSON alone, whatever a newer Python warns about
    except ValueError:
        facts = {}
    check('the kit\'s facts give the day in words, with no leading zero ("Monday, June 1, 2026")',
          code == 0 and facts.get("day") == "Monday, June 1, 2026" and facts.get("photos") == 3, f"{facts.get('day')!r} {out[-300:]}")
    check("and what they said, exactly", facts.get("they_said") == told, repr(facts.get("they_said")))

    built = False
    if not can_build:
        skip("a post kit built the PC way, the picker's small copies, and the posting queue's kit pictures",
             "Pillow is not installed for this Python; the PC way needs it (python -m pip install pillow)")
    else:
        built = build_checks(kit, env)
    posting_checks(home, env)
    lock_checks(work)
    canva_checks(work, kit, env, built)
    server_checks(work, home, kit, env, built)
    check("the finished photos were only ever read", {p.name: sha(p) for p in photos.iterdir()} == photos_before)


def build_checks(kit, env):
    """The kit's pieces made the PC way, sizes checked and the sideways photo upright; a new carousel order made;
    the picker's small copies; the kit's pieces in the posting queue. True when the kit was built."""
    code, out = run("kit.py", "sheet", "beach", env=env)
    check("the kit's numbered sheet is made the PC way", code == 0 and (kit / ".kit" / "sheet.json").is_file(), out[-300:])
    code, out = run("kit.py", "picks", "beach", "--singles", "1,2,3", "--stories", "3,1", "--carousel", "3,1,2",
                    "--reel", "1,2,3+", "--cover", "3", env=env)
    check("the picks are kept", code == 0, out[-300:])
    code, out = run("kit.py", "build", "beach", env=env)
    check("the kit is built: singles, a carousel, stories and the reel cover",
          code == 0 and "Singles: 3 made." in out and "Carousel: 3 made." in out and "Stories: 2 made." in out
          and "Covers: 2 made." in out, out[-500:])
    if code != 0:
        return False
    if tc.WINDOWS:
        # the line Claude is handed for the reel: PowerShell cuts a bare comma list into pieces, so on a PC the picks
        # are in double quotes, and the folder is written with forward slashes, which every PC takes (kit._pc_arg)
        reel = next((ln for ln in out.splitlines() if ln.startswith("Reel: ")), "")
        folder = reel.split(" --folder ", 1)[1].split(" --shoot ", 1)[0] if " --folder " in reel else ""
        check("(a PC) the build's Reel line has the picks in double quotes and the folder with forward slashes only",
              ': "1,2,3+" --folder "' in reel and folder and "\\" not in folder, reel)
    sideways = "Beach 03 sideways"
    sing, car, sto, cov = kit / "Singles", kit / "Carousel", kit / "Stories", kit / "Covers"
    wide = size_on_disk(sing / "Single 01 (Beach 01).jpg") or (1, 1)
    check("a wide photo's single keeps its own shape (3:2), within 1080 x 1350 and never blown up",
          wide[0] <= 1080 and wide[1] <= 1350 and abs(wide[0] / wide[1] - 1.5) < 0.01, str(wide))
    check("a tall photo's single is 1080 x 1350", size_on_disk(sing / "Single 02 (Beach 02).jpg") == (1080, 1350),
          str(size_on_disk(sing / "Single 02 (Beach 02).jpg")))
    s3 = sing / f"Single 03 ({sideways}).jpg"
    check("the sideways photo's single is 1080 x 1350 and the right way up (its red corner top-right)",
          size_on_disk(s3) == (1080, 1350) and red_corners(s3) == {"top-right"}, f"{size_on_disk(s3)} {red_corners(s3)}")
    slides = [n for n in listing(car) if not n.startswith(".")]
    check("every carousel slide is 1080 x 1350, in the order picked",
          slides == [f"Slide 01 ({sideways}).jpg", "Slide 02 (Beach 01).jpg", "Slide 03 (Beach 02).jpg"]
          and all(size_on_disk(car / n) == (1080, 1350) for n in slides), str(slides))
    check("the sideways photo's slide is the right way up", red_corners(car / f"Slide 01 ({sideways}).jpg") == {"top-right"},
          str(red_corners(car / f"Slide 01 ({sideways}).jpg")))
    st1 = sto / f"Story 01 ({sideways}).jpg"
    dark = (0x1A, 0x1A, 0x1C)
    box = content_box(st1, dark)
    stories = [n for n in listing(sto) if not n.startswith(".")]
    check("both stories are there, in the order picked, each 1080 x 1920",     # never all() of an empty folder
          stories == [f"Story 01 ({sideways}).jpg", "Story 02 (Beach 01).jpg"]
          and all(size_on_disk(sto / n) == (1080, 1920) for n in stories),
          str([(n, size_on_disk(sto / n)) for n in listing(sto)]))
    check("the sideways photo's story stands upright (taller than wide, its red corner top-right)",
          box[1] > box[0] > 0 and red_corners(st1, pad=dark) == {"top-right"}, f"{box} {red_corners(st1, pad=dark)}")
    check("the reel cover is 1080 x 1920, upright, and the grid's view of it 1080 x 1440",
          size_on_disk(cov / "Reel cover.jpg") == (1080, 1920) and red_corners(cov / "Reel cover.jpg") == {"top-right"}
          and size_on_disk(cov / "Reel cover, as the grid shows it.jpg") == (1080, 1440),
          f"{size_on_disk(cov / 'Reel cover.jpg')} {red_corners(cov / 'Reel cover.jpg')}")

    # a new carousel order: new slides made first in the kit's hidden folder, the earlier ones set aside (never
    # deleted, never written over), under the slides lock (on a PC msvcrt.locking, and a rename that refuses a name
    # already taken)
    earlier = {n: sha(car / n) for n in slides}
    code, out = run("kit.py", "picks", "beach", "--carousel", "2,3", env=env)
    code2, out2 = run("kit.py", "build", "beach", env=env)
    now = [n for n in listing(car) if not n.startswith(".")]
    aside = {}
    for p in (kit / ".kit" / "slides-older").rglob("*.jpg"):
        aside[p.name] = sha(p)
    check("a new carousel order: the new slides in place, the earlier ones set aside in the kit's hidden folder, byte for byte",
          code == 0 and code2 == 0 and "Carousel: 2 made." in out2
          and now == ["Slide 01 (Beach 02).jpg", f"Slide 02 ({sideways}).jpg"]
          and all(size_on_disk(car / n) == (1080, 1350) for n in now) and aside == earlier,
          f"{now} {sorted(aside)} {out2[-300:]}")
    check("no half-made picture is left anywhere in the kit", not half_made(kit), str(half_made(kit)))

    # the picker's small copies (arrange.py): the PC way, upright, never blown up
    code, out = run("arrange.py", "previews", "beach", env=env)
    prev = kit / ".kit" / "previews"
    big = sorted(prev.glob("0003-1600-*.jpg"))
    small = sorted(prev.glob("0003-520-*.jpg"))
    sizes = [size_on_disk(p) for p in big + small]
    check("the picker's small copies are made (two for each of the 3 photos)",
          code == 0 and len(list(prev.glob("*.jpg"))) == 6, f"{code} {listing(prev)} {out[-300:]}")
    check("and no half-made copy is left behind (the PC way's own .p- scratch names too)", not half_made(kit),
          str(half_made(kit)))
    check("the sideways photo's copies stand upright: 400 x 600 (never blown up) and 347 x 520, red corner top-right",
          sizes == [(400, 600), (347, 520)] and all(red_corners(p) == {"top-right"} for p in big + small),
          f"{sizes} {[red_corners(p) for p in big + small]}")

    # the kit's pieces in the posting queue, each with its own small picture (on a PC "kit_..." in the file name,
    # since Windows takes no colon in one)
    code, out = run("posting_queue.py", "add", "--kit", "beach", env=env)
    try:
        pieces = [x for x in json.loads((Path(env["STUDIO_HOME"]) / "posting.json").read_bytes().decode("utf-8"))["pieces"]
                  if x.get("id", "").startswith("kit:")]
    except (OSError, ValueError, KeyError):
        pieces = []
    thumbs = [Path(env["STUDIO_HOME"]) / x["thumb"] for x in pieces if x.get("thumb")]
    check("the kit's pieces go in the posting queue (reel, carousel, three singles), each with a small picture",
          code == 0 and len(pieces) == 5 and len(thumbs) == 5 and all(p.is_file() and sha(p) for p in thumbs)
          and all(max(size_on_disk(p) or (999, 999)) <= 450 and (size_on_disk(p) or (999,))[0] <= 360 for p in thumbs), f"{code} {len(pieces)} {out[-300:]}")
    if tc.WINDOWS:
        check("on a PC no picture's file name has a colon in it", not any(":" in p.name for p in thumbs), str([p.name for p in thumbs]))
    return True


def posting_checks(home, env):
    """The posting queue with an emoji and curly quotes in a shoot's name: interval, add, made, ready, reminders,
    the page; every file it writes UTF-8."""
    code, out = run("edit_queue.py", "add-manual", "--name", POSTS_SHOOT, "--due", "2w", env=env)
    check("a shoot with an emoji and curly quotes goes in the editing queue", code == 0, out[-300:])
    code, out = run("posting_queue.py", "interval", "3 a week", env=env)
    check("the posting rhythm is kept (3 a week)", code == 0 and "3 a week" in out, out[-300:])
    code, out = run("posting_queue.py", "add", "--shoot", "golden", env=env)
    check("the shoot's reel and carousel go in the posting queue", code == 0 and "2 pieces waiting" in out and POSTS_SHOOT in out, out[-300:])
    code, out = run("posting_queue.py", "made", "golden reel", "--where", POSTS_SHOOT + " reel", env=env)
    try:
        reel = next(x for x in json.loads((home / "posting.json").read_bytes().decode("utf-8"))["pieces"]
                    if x.get("shoot_name") == POSTS_SHOOT and x.get("kind") == "reel")
    except (OSError, ValueError, KeyError, StopIteration):
        reel = {}
    check("the reel is marked made (in progress, where it is kept)", code == 0 and "in progress" in out
          and reel.get("status") == "yellow", f"{reel.get('status')} {out[-300:]}")
    code, out = run("posting_queue.py", "ready", "golden reel", env=env)
    check("and ready to post, with a date", code == 0 and "ready to post, down for" in out, out[-300:])
    try:
        raw = (home / "posting.json").read_bytes().decode("utf-8")
        green = [x for x in json.loads(raw)["pieces"] if x["status"] == "green"]
    except (OSError, ValueError, KeyError) as e:
        raw, green = f"(unreadable: {e})", []
    check("the posting queue's file is UTF-8 and keeps the name exactly", POSTS_SHOOT in raw and len(green) == 1
          and green[0]["shoot_name"] == POSTS_SHOOT and green[0].get("date"), raw[:300])
    if not green:
        return
    day = green[0]["date"]
    code, out = run("posting_queue.py", "reminders", "--mark", env=dict(env, STUDIO_TODAY=day))
    code2, out2 = run("posting_queue.py", "reminders", "--mark", env=dict(env, STUDIO_TODAY=day))
    check("on its day a reminder names the post exactly, once a day",
          code == 0 and f"Today's post: the {POSTS_SHOOT} reel." in out and code2 == 0 and "Today's post" not in out2,
          (out + " | " + out2)[-400:])
    code, out = run("posting_queue.py", "page", env=env)
    try:
        page = (home / "posting.html").read_bytes().decode("utf-8")
        ok = shows(page, POSTS_SHOOT)
    except (OSError, UnicodeDecodeError):
        ok = False
    check("the posting page is written as UTF-8, the name with it", code == 0 and ok, out[-300:])


def canva_checks(work, kit, env, built):
    """canva_kit.py fetch from a stand-in for Canva's download links on 127.0.0.1 (never the internet): the files go
    in under their Canva names, a fresh export sets the earlier ones aside, a dead link changes nothing."""
    own_curl = Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "curl.exe"
    curl_here = own_curl.is_file() if tc.WINDOWS else shutil.which("curl")
    if not curl_here:
        if tc.WINDOWS:
            # Windows 10 (1803 on) and 11 come with it, and canva_kit.py asks for it by this full path: missing here
            # means the test or canva_kit.curl() looks in the wrong place, never a PC to skip (Nov 6, test review)
            check("Windows' own curl.exe is where canva_kit.py looks for it", False, str(own_curl))
        else:
            skip("Canva's downloads into a kit", "this computer has no curl, which canva_kit.py uses")
        return
    print("\n-- Canva's downloads into the kit, from a stand-in on 127.0.0.1 (never the internet)")
    # which curl canva_kit.py runs: on a PC Windows' own, by its full path (never a curl.exe in the current folder,
    # nor another one earlier on the PATH, like Git's); on a Mac the one on the PATH, as always
    code, out = run_python(["-c", f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import canva_kit; print(canva_kit.curl())"], env=env)
    want = str(own_curl) if tc.WINDOWS else str(curl_here)
    said = out.strip().splitlines()[-1] if out.strip() else ""
    check("canva_kit.py runs " + ("Windows' own curl.exe, by its full path" if tc.WINDOWS else "the curl on the PATH"),
          code == 0 and os.path.normcase(said) == os.path.normcase(want), f"{code} {said!r}, wanted {want!r}")
    stand_in = _StandIn(smoke_ports(1)[0])
    car = kit / "Carousel"
    plain = {n: sha(car / n) for n in listing(car) if "(Canva)" not in n and not n.startswith(".")} if built else {}
    env = dict(env, NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    try:
        v1 = [jpeg_bytes(64, 80, lambda bx, by, k=k: (30 * k, 90, 200 - 30 * k)) for k in (1, 2)]
        v2 = [jpeg_bytes(64, 80, lambda bx, by, k=k: (200 - 30 * k, 60, 30 * k)) for k in (1, 2)]
        stand_in.files.update({"/export/a1.jpg": v1[0], "/export/a2.jpg": v1[1], "/export/b1.jpg": v2[0], "/export/b2.jpg": v2[1]})
        links = work / "links one.json"
        links.write_bytes(("\ufeff" + json.dumps([stand_in.url("/export/a1.jpg", "one"), stand_in.url("/export/a2.jpg", "two")])).encode("utf-8"))
        code, out = run("canva_kit.py", "fetch", "beach", "--into", "Carousel", "--urls", links, env=env)
        got = {n: sha(car / n) for n in ("Slide 01 (Canva).jpg", "Slide 02 (Canva).jpg") if n in listing(car)}   # exact names
        check("Canva's downloads go into the kit's Carousel folder under their Canva names, byte for byte (links read from a file)",
              code == 0 and got == {"Slide 01 (Canva).jpg": hashlib.sha256(v1[0]).hexdigest(),
                                    "Slide 02 (Canva).jpg": hashlib.sha256(v1[1]).hexdigest()}, f"{code} {listing(car)} {out[-300:]}")
        links2 = work / "links two.json"
        links2.write_text(json.dumps({"urls": [stand_in.url("/export/b1.jpg", "three"), stand_in.url("/export/b2.jpg", "four")]}), encoding="utf-8")
        code, out = run("canva_kit.py", "fetch", "beach", "--into", "Carousel", "--urls", links2, env=env)
        aside = {p.name: sha(p) for p in (kit / ".kit" / "canva-older").rglob("*.jpg")} if (kit / ".kit" / "canva-older").is_dir() else {}
        now = {n: sha(car / n) for n in ("Slide 01 (Canva).jpg", "Slide 02 (Canva).jpg") if n in listing(car)}
        check("a fresh export takes the same names, and the earlier Canva files are set aside in the kit's hidden folder, not deleted",
              code == 0 and now == {"Slide 01 (Canva).jpg": hashlib.sha256(v2[0]).hexdigest(), "Slide 02 (Canva).jpg": hashlib.sha256(v2[1]).hexdigest()}
              and sorted(aside.values()) == sorted(hashlib.sha256(b).hexdigest() for b in v1), f"{code} {sorted(aside)} {out[-300:]}")
        before = {n: sha(car / n) for n in listing(car)}
        links3 = work / "links three.json"
        links3.write_text(json.dumps([stand_in.url("/export/b1.jpg", "five"), stand_in.url("/export/gone.jpg", "six")]), encoding="utf-8")
        code, out = run("canva_kit.py", "fetch", "beach", "--into", "Carousel", "--urls", links3, env=env)
        check("a dead link stops it with plain words, and the Carousel folder is exactly as it was",
              code == 1 and "STOP" in out and {n: sha(car / n) for n in listing(car)} == before, f"{code} {listing(car)} {out[-300:]}")
        if built:
            check("the kit's own plain slides were never touched", {n: sha(car / n) for n in plain if (car / n).is_file()} == plain)
        asked = [s.split("?", 1)[0] for s in stand_in.seen]
        check("each link was asked of the stand-in on 127.0.0.1 once, in order (the dead one last)",
              asked == ["/export/a1.jpg", "/export/a2.jpg", "/export/b1.jpg", "/export/b2.jpg", "/export/b1.jpg", "/export/gone.jpg"],
              str(asked))
        # a dead link into a folder the kit doesn't have yet: the folder this run made is taken away again, so "nothing
        # in the kit changed" is true (Nov 6 follow-up: an empty Stories folder was left, and the kit page then
        # offered to open it)
        # (a kit of its own, one photo, never built, so it has no Stories folder whatever this computer could build)
        one = work / "fresh photos"
        one.mkdir()
        (one / "Fresh 01.jpg").write_bytes(jpeg_bytes(64, 48, lambda bx, by: (90, 140, 60), exif_blob(datetime(2026, 6, 2, 10, 0))))
        code, out = run("kit.py", "start", "--folder", one, "--name", "Fresh one", env=env)
        fresh_kit = kit.parent / "2026-06-02 Fresh one"
        links4 = work / "links four.json"
        links4.write_text(json.dumps([stand_in.url("/export/gone.jpg", "seven")]), encoding="utf-8")
        before_kit = listing(fresh_kit)
        code2, out2 = run("canva_kit.py", "fetch", "fresh one", "--into", "Stories", "--urls", links4, env=env)
        check("a dead link into a folder the kit didn't have yet (Stories): plain words, and no empty folder left behind",
              code == 0 and before_kit and "Stories" not in before_kit and code2 == 1 and "STOP" in out2
              and listing(fresh_kit) == before_kit, f"{code} {code2} {before_kit} -> {listing(fresh_kit)} {(out + out2)[-300:]}")
    finally:
        stand_in.stop()


def server_checks(work, home, kit, env, built):
    """The posting server (the home page's own) started in the background the way the Assistant starts it, serving
    the home page, the posting page, a kit page and a piece's picture, then stopped by its own number."""
    print("\n-- the posting server (the home page's own)")
    import urllib.error
    import urllib.request
    from urllib.parse import quote
    code, out = run("kit.py", "page", "beach", env=env)
    try:
        page = (kit / ".kit" / "Post kit.html").read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        page = ""
    check('the kit page is written as UTF-8, with the kit\'s name and its day in words ("June 1, 2026")',
          code == 0 and shows(page, KIT_NAME) and "June 1, 2026" in page, out[-300:])
    port = smoke_ports(2)[1]
    url_file = home / "posting-url.txt"
    if url_file.exists():
        url_file.unlink()
    log_path = work / "posting server.log"
    log = open(log_path, "wb")
    srv = tc.popen_detached([sys.executable, str(SCRIPTS / "posting_queue.py"), "serve", "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=child_env(env))
    from urllib.parse import urlsplit
    served_on = port
    try:
        base = None
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30 and srv.poll() is None:
            try:
                said = url_file.read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            if said:              # an empty file is one caught mid-write: wait for the address itself
                base = said.rsplit("/", 1)[0]
                break
            time.sleep(0.2)
        check("the posting server starts in the background and says its address", bool(base) and srv.poll() is None,
              log_path.read_bytes().decode("utf-8", "replace")[-400:])
        if not base:
            return
        # the port it really took: serve moves up to the next free one when the asked port is busy (Nov 6, test
        # review: the last check knocked on the asked port, so a moved server was never knocked on at all)
        try:
            served_on = urlsplit(base).port or port
        except ValueError:
            served_on = port
        if served_on != port:
            info("the posting server took another port", f"asked for {port}, it said {served_on}")

        def get(path):
            try:
                with urllib.request.urlopen(base + path, timeout=20) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, b""
            except OSError as e:
                return None, str(e).encode()
        code, body = get("/home")
        text = body.decode("utf-8", "replace")
        check("it serves the home page (UTF-8, the shoot's name on it)",
              code == 200 and "/home-state" in text and shows(text, POSTS_SHOOT), f"{code} {text[:200]}")
        code, body = get("/posting.html")
        text = body.decode("utf-8", "replace")
        check("and the posting page", code == 200 and "Back to home" in text and shows(text, POSTS_SHOOT),
              f"{code} {text[:200]}")
        code, body = get("/content/" + quote(kit.name) + "/" + quote("Post kit.html"))
        check("and the kit's page, read-only from Your Content", code == 200 and b"<html" in body[:400].lower(), f"{code} {body[:200]!r}")
        code, body = get("/content/" + quote(kit.name) + "/" + quote("kit.json"))
        check("but never the kit's own records", code == 404, str(code))
        # nor its hidden folder, nor the photos themselves (Nov 6, test review: only kit.json was asked for)
        refused = {}
        for rel in (".kit/kit.json", ".kit/told.json", ".kit/Post kit.html"):
            refused[rel] = get("/content/" + quote(kit.name) + "/" + quote(rel))[0]
        # this kit points at the folder it was started from; a kit made from the drop box keeps its photos in its
        # own Photos folder, so one is put there (a copy) to make sure a real photo at that address is refused
        own_photos = kit / "Photos"
        if not sorted(own_photos.glob("*.jpg")):
            own_photos.mkdir(exist_ok=True)
            shutil.copyfile(work / "kit photos" / "Beach 01.jpg", own_photos / "Beach 01.jpg")
        photo = sorted(own_photos.glob("*.jpg"))[0]
        refused["Photos/" + photo.name] = get("/content/" + quote(kit.name) + "/Photos/" + quote(photo.name))[0]
        check("nor anything in the kit's hidden folder, nor a photo itself", all(c == 404 for c in refused.values()),
              str(refused))
        # a colon in a name: on a PC another drive or a hidden stream inside a file, refused before the drive is
        # looked at (posting_queue.py serve_content and open_kit_folder). Asked on both computers; on a Mac no such
        # kit is there either, so only a PC tries the refusal itself. Neither ever opens a window.
        code, body = get("/content/" + quote(kit.name + ":x") + "/" + quote("Post kit.html"))
        code2, body2 = get("/content/" + quote(kit.name) + "/Carousel/" + quote("x:Slide 01.jpg"))
        check("a kit or picture name with a colon in it is refused", code == 404 and code2 == 404, f"{code} {code2}")
        opened = {}
        for k in (r"C:\Windows", kit.name + ":x"):
            c, b = get("/open?kit=" + quote(k, safe=""))
            try:
                opened[k] = (c, json.loads(b.decode("utf-8")).get("ok"))
            except (ValueError, UnicodeDecodeError, AttributeError):
                opened[k] = (c, b[:80])
        check("and the folder button refuses a drive or a colon name, opening nothing",
              all(v == (200, False) for v in opened.values()), str(opened))
        # a network path (on a PC, looking one up reaches out to that computer first), a slash or a dot name: refused
        # as words, at once, before any folder is looked up (Nov 6 follow-up)
        at_once = {}
        for k in ("//127.0.0.1/c$", "\\\\127.0.0.1\\c$", "a/b", ".kit", "..", "."):
            t0 = time.monotonic()
            c, b = get("/open?kit=" + quote(k, safe=""))
            took = time.monotonic() - t0
            try:
                said = json.loads(b.decode("utf-8"))
                at_once[k] = (c, said.get("ok"), said.get("words"), round(took, 1))
            except (ValueError, UnicodeDecodeError, AttributeError):
                at_once[k] = (c, None, b[:80], round(took, 1))
        check("and refuses a network path, a slash or a dot name at once, in plain words",
              all(c == 200 and ok is False and w == "That isn't a folder this kit names." and t < 5
                  for c, ok, w, t in at_once.values()), str(at_once))
        # the picture folders serve pictures only: never the Studio folder's own files through "%2e%2e" (the same two
        # dots, written the way addresses may write them), never a folder's list, never a HEAD for anything else; and
        # nothing at all for a request naming another host (Nov 6 follow-up: before, all of these were answered)
        leaks = {}
        for path in ("/feed/%2e%2e/studio.json", "/posting-thumbs/%2e%2e/posting.json", "/home-thumbs/%2e%2e/studio.json",
                     "/queue-thumbs/%2e%2e/queue.json", "/feed/", "/posting-thumbs/", "/feed/older/"):
            c, b = ask(served_on, "GET", path)
            leaks["GET " + path] = (c, b"pieces" in b or b"posts" in b)
        for path in ("/studio.json", "/posting.json"):
            leaks["HEAD " + path] = (ask(served_on, "HEAD", path)[0], False)
        check("the picture folders never hand out the Studio folder's own files or a folder's list (%2e%2e, a folder's address, HEAD)",
              all(c == 404 and not leaked for c, leaked in leaks.values()), str(leaks))
        c, b = ask(served_on, "GET", "/feed/%2e%2e/studio.json", host=f"evil.example:{served_on}")
        c2, _ = ask(served_on, "GET", "/home", host=f"evil.example:{served_on}")
        c3, _ = ask(served_on, "GET", "/home", host=f"localhost:{served_on}")
        check("a request naming another host is refused (403), and the page still answers to localhost",
              c == 403 and c2 == 403 and c3 == 200 and b"posts" not in b, f"{c} {c2} {c3}")
        if built:
            pieces = json.loads((home / "posting.json").read_bytes().decode("utf-8"))["pieces"]
            thumb = next((x["thumb"] for x in pieces if x.get("id", "").startswith("kit:") and x.get("thumb")), None)
            code, body = get("/" + quote(thumb)) if thumb else (None, b"")
            check("and a kit piece's small picture", code == 200 and body[:2] == b"\xff\xd8", f"{thumb} {code}")
    finally:
        srv.terminate()
        try:
            srv.wait(15)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(15)
        log.close()
    import socket
    try:
        with socket.create_connection(("127.0.0.1", served_on), timeout=2):
            answered = True
    except OSError:
        answered = False
    check("and once stopped by its own number, nothing answers on its port", not answered, f"port {served_on}")


# ---------------------------------------------------------------- the PC follow-up of Nov 6

def followup_checks(work):
    """The PC follow-up of Nov 6, where a machine with no screen can see it. Each part's fault FAILs that part
    only; the parts after it still run."""
    print("\n-- the PC follow-up: curl, the grid's list from a PC file, saving from six threads, never through a proxy, "
          "the queue's page server, CapCut's waiting list, the folder window's answer, quoting for a PC, the report's "
          "page server, its folder button and a network path, every say() with nobody reading")
    home = work / "follow-up studio-home"
    home.mkdir()
    env = {"STUDIO_HOME": str(home)}
    ports = smoke_ports(5)
    for part in (curl_checks, feed_checks, saving_checks, proxy_checks, queue_server_checks, capcut_checks,
                 picker_answer_checks, quoting_checks, report_server_checks, report_open_checks, say_checks):
        try:
            part(work, home, env, ports)
        except Exception:  # noqa: BLE001  (a fault in one part FAILs here; the next part still runs)
            import traceback
            check(f"{part.__name__} ran to the end", False, traceback.format_exc()[-1500:])


def curl_checks(work, home, env, ports):
    """this_computer.run_curl (canva_kit.py and the Instagram grid's pictures go through it): on a Mac exactly the
    command it is given, run once; on a PC one more try, with --ssl-revoke-best-effort, only when Windows couldn't
    ask whether the site's certificate was withdrawn; never --ssl-no-revoke."""
    import types
    data = os.urandom(70_000)
    f = work / "curl-picture.bin"
    f.write_bytes(data)
    if tc.WINDOWS:
        own = Path(os.environ.get("SystemRoot") or r"C:\Windows") / "System32" / "curl.exe"
        prog = str(own) if own.is_file() else None
    else:
        prog = shutil.which("curl")
    if prog:
        cmd = [prog, "-sS", f.as_uri()]
        r = tc.run_curl(cmd, capture_output=True, timeout=60)
        check("run_curl runs this computer's own curl on a local file exactly as it is given, once: every byte comes back",
              r.returncode == 0 and r.stdout == data and list(r.args) == cmd,
              f"{r.returncode} {len(r.stdout or b'')} bytes {r.args} {(r.stderr or b'')[:200]!r}")
    elif tc.WINDOWS:
        check("Windows' own curl.exe is there for run_curl", False, "no System32\\curl.exe")
    else:
        skip("run_curl with this computer's own curl", "this computer has no curl")
    # every case, with a stand-in for curl's answers (this process only): which command ran, how many times
    calls, answers = [], []

    def stand_in(cmd, **kw):
        calls.append((list(cmd), dict(kw)))
        code, err = answers.pop(0) if answers else (0, "")    # a try nobody expected: answered, so its check FAILs
        return subprocess.CompletedProcess(cmd, code, b"", err.encode("utf-8"))
    cmd = ["curl", "-sS", "--fail", "-o", "-", "https://pictures.example.invalid/a.jpg"]
    kw = {"capture_output": True, "timeout": 25}
    cant_ask = ("curl: (35) schannel: next InitializeSecurityContext failed: Unknown error (0x80092012) - The revocation "
                "function was unable to check revocation for the certificate.")
    real_sub, real_win = tc.subprocess, tc.WINDOWS
    tc.subprocess = types.SimpleNamespace(run=stand_in)
    try:
        tc.WINDOWS = False
        calls.clear()
        answers[:] = [(35, cant_ask)]
        r = tc.run_curl(cmd, **kw)
        check("a Mac: run_curl runs exactly the command and settings it is given, once, whatever curl answers",
              calls == [(cmd, kw)] and r.returncode == 35, str(calls))
        tc.WINDOWS = True
        calls.clear()
        answers[:] = [(35, cant_ask), (0, "")]
        r = tc.run_curl(cmd, **kw)
        check("a PC whose network won't let curl ask whether the certificate was withdrawn: one more try, with "
              "--ssl-revoke-best-effort right after the program, the same settings",
              [c for c, _ in calls] == [cmd, cmd[:1] + ["--ssl-revoke-best-effort"] + cmd[1:]]
              and all(k == kw for _, k in calls) and r.returncode == 0, str(calls))
        calls.clear()
        # withdrawn, and (for another certificate in the chain) "couldn't ask" in the same words: withdrawn wins
        answers[:] = [(35, "curl: (35) schannel: next InitializeSecurityContext failed: CRYPT_E_REVOKED (0x80092010) - "
                           "The certificate is revoked. (CERT_TRUST_IS_REVOKED, CERT_TRUST_REVOCATION_STATUS_UNKNOWN)")]
        r = tc.run_curl(cmd, **kw)
        check("a PC: a certificate that HAS been withdrawn stops it at once, never a second try (even beside \"couldn't ask\")",
              len(calls) == 1 and r.returncode == 35, str(calls))
        calls.clear()
        answers[:] = [(35, cant_ask), (2, "curl: option --ssl-revoke-best-effort: is unknown\ncurl: try 'curl --help' for more information")]
        r = tc.run_curl(cmd, **kw)
        check("a PC with an older curl.exe that doesn't know that option: the first answer (curl's own reason) is the one given back",
              len(calls) == 2 and r.returncode == 35 and b"0x80092012" in r.stderr, f"{calls} {r.returncode}")
        calls.clear()
        answers[:] = [(6, "curl: (6) Could not resolve host: pictures.example.invalid")]
        r = tc.run_curl(cmd, **kw)
        check("a PC: any other failure is given back as it came, never tried again", len(calls) == 1 and r.returncode == 6, str(calls))
        check("and nothing ever runs it with --ssl-no-revoke", not any("--ssl-no-revoke" in c for c, _ in calls))
    finally:
        tc.subprocess, tc.WINDOWS = real_sub, real_win


def feed_checks(work, home, env, ports):
    """posting_queue.py feed --import, from the kinds of file Claude may save the snippet's answer in. The tiles here
    carry their pictures in the file itself (data: addresses), so nothing is fetched and the internet is never asked."""
    jpg = jpeg_bytes(64, 64, lambda bx, by: (40, 90, 160))
    data = "data:image/jpeg;base64," + base64.b64encode(jpg).decode("ascii")
    tiles = [{"href": "/someone/p/AAA111/", "data": data, "pinned": True}, {"href": "/someone/reel/BBB_22-x/", "data": data, "reel": True}]

    def posts():
        try:
            return [p["id"] for p in json.loads((home / "feed.json").read_bytes().decode("utf-8"))["posts"]]
        except (OSError, ValueError, KeyError, TypeError):
            return None
    f16 = work / "grid saved by PowerShell.json"
    f16.write_bytes(json.dumps({"handle": "someone", "tiles": tiles}).encode("utf-16"))   # a mark first, as PowerShell 5.1's ">" saves it
    code, out = run("posting_queue.py", "feed", "--import", f16, env=env)
    got = (home / "feed" / "AAA111.jpg").read_bytes() if (home / "feed" / "AAA111.jpg").is_file() else b""
    check("the grid's list read from a file saved the Windows PowerShell way (UTF-16 with its mark): both pictures in",
          code == 0 and posts() == ["AAA111", "BBB_22-x"] and got == jpg, f"{code} {posts()} {out[-300:]}")
    fq = work / "grid as the pane gave it.json"
    fq.write_text(json.dumps(json.dumps({"handle": "someone", "tiles": tiles[:1] + ["not a tile", 5]})), encoding="utf-8")
    code, out = run("posting_queue.py", "feed", "--import", fq, env=env)
    check("and saved exactly as the browser pane's tool gave it (one quoted string), anything that isn't a tile left out",
          code == 0 and posts() == ["AAA111"] and "Traceback" not in out, f"{code} {posts()} {out[-300:]}")
    before = (home / "feed.json").read_bytes()
    fb = work / "not the list.json"
    fb.write_bytes(b"\xff\x00 not a list at all")
    code, out = run("posting_queue.py", "feed", "--import", fb, env=env)
    check("a file that isn't the list: a plain STOP, nothing changed, no traceback",
          code == 1 and "STOP: that file isn't the list the snippet returned" in out and "Traceback" not in out
          and (home / "feed.json").read_bytes() == before, f"{code} {out[-300:]}")


_SIX_THREADS = """import json, sys, threading
sys.path.insert(0, {scripts!r})
import {module} as m
errors = []
def go(n):
    for i in range(40):
        try:
            {call}
        except Exception as e:
            errors.append(type(e).__name__ + ": " + str(e)[:80])
ts = [threading.Thread(target=go, args=(n,)) for n in range(6)]
for t in ts:
    t.start()
for t in ts:
    t.join()
print("ERRORS " + json.dumps(errors[:3]) + " " + str(len(errors)))
"""


def saving_checks(work, home, env, ports):
    """The posting queue and the home page's record, each saved from six threads at once (the page server answers two
    presses at once; a command can save while a page does): every save goes through, the file reads back whole, and
    no scratch copy is left behind. Before Nov 6 the threads shared one scratch name and took each other's away."""
    for module, call, name, what in (
            ("posting_queue", "m.save({{'pieces': [], 'interval': n, 'reminded': {{}}, 'i': i}})", "posting.json",
             "the posting queue"),
            ("home", "m.record_click('posts') if i % 2 else m.record_done('reel', note=str(n) + '-' + str(i))",
             "journey.json", "the home page's record of what was pressed and done")):
        code, out = run_python(["-c", _SIX_THREADS.format(scripts=str(SCRIPTS), module=module, call=call.format())], env=env)
        line = next((ln for ln in out.splitlines() if ln.startswith("ERRORS ")), "")
        try:
            whole = json.loads((home / name).read_bytes().decode("utf-8")) is not None
        except (OSError, ValueError):
            whole = False
        left = sorted(p.name for p in home.iterdir() if p.name.startswith(name) and p.name.endswith(".tmp"))
        check(f"{what}, saved from six threads at once 240 times: every save goes through, the file whole, no scratch copy left",
              code == 0 and line == "ERRORS [] 0" and whole and not left, f"{code} {line or out[-300:]} left {left}")


_PROXY_CHILD = """import json, sys, time
sys.path.insert(0, {scripts!r})
import fresh
def no_server(*a, **k):
    raise OSError("this test starts no page server")
fresh.start_server = no_server
import home, arrange
from pathlib import Path
t0 = time.time()
u = home.url()
t1 = time.time()
a = arrange.page_address(Path("2026-06-01 Kit"), "reel")
print("ANSWER " + json.dumps({{"url": u, "url_s": round(t1 - t0, 2), "address": a, "address_s": round(time.time() - t1, 2)}}))
"""


def proxy_checks(work, home, env, ports):
    """this computer's own pages are never asked for through a proxy (this_computer.open_local, and home.url and the
    picker's wait, which use it). Python's own fetch takes the proxy from the environment, and on a PC from Windows'
    own settings, where 127.0.0.1 is not left out; a proxy can't see this computer's pages, so the Assistant would
    think its page server was down and start another. A stand-in proxy on 127.0.0.1 counts what it is sent."""
    import urllib.error
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer
    seen = []

    class Proxy(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass
    proxy = HTTPServer(("127.0.0.1", ports[4]), Proxy)
    t = threading.Thread(target=proxy.serve_forever)
    t.daemon = True
    t.start()
    page = _StandIn(ports[3])
    page.files["/home"] = b"<title>The Assistant</title>"
    url = f"http://127.0.0.1:{page.port}/home"
    proxy_at = f"http://127.0.0.1:{proxy.server_address[1]}"
    names = ("http_proxy", "HTTP_PROXY", "no_proxy", "NO_PROXY", "all_proxy", "ALL_PROXY")
    kept = {k: os.environ.get(k) for k in names}
    try:
        for k in names:
            os.environ.pop(k, None)
        os.environ["http_proxy"] = proxy_at
        try:
            # a fresh opener, as a program just started has: urlopen's own is made once and keeps the proxies it saw then
            with urllib.request.build_opener().open(url, timeout=10) as r:
                plain = r.status
        except urllib.error.HTTPError as e:
            plain = e.code
        except OSError as e:
            plain = str(e)
        if not seen:
            skip("this computer's own pages never go through a proxy",
                 f"this Python's own fetch didn't use the proxy set in the environment either ({plain}), so there is nothing to show")
            return
        seen.clear()
        try:
            with tc.open_local(url, timeout=10) as r:
                st, body = r.status, r.read()
        except Exception as e:  # noqa: BLE001
            st, body = repr(e)[:200], b""
        check("this_computer.open_local opens a page of this computer's own straight, never through a proxy in the environment",
              st == 200 and body == b"<title>The Assistant</title>" and not seen, f"{st} {body[:60]!r} the proxy was sent {seen}")
        # home.url and the picker's address, in a program of their own, with the proxy set the same way: they find the
        # page server already answering (posting-url.txt points at the stand-in) and start nothing
        (home / "posting-url.txt").write_text(url, encoding="utf-8")
        seen.clear()
        code, out = run_python(["-c", _PROXY_CHILD.format(scripts=str(SCRIPTS))], env=dict(env, http_proxy=proxy_at))
        line = next((ln for ln in out.splitlines() if ln.startswith("ANSWER ")), "")
        try:
            got = json.loads(line[len("ANSWER "):])
        except ValueError:
            got = {}
        check("home.url finds this computer's own page server through a proxy set in the environment, and starts no other",
              code == 0 and got.get("url") == url and not seen, f"{code} {got} the proxy was sent {seen} {out[-300:]}")
        check("and the picker's address comes back at once (no waiting on a proxy that can't see the page)",
              str(got.get("address", "")).startswith(url.rsplit("/", 1)[0] + "/arrange.html?") and got.get("address_s", 99) < 5,
              str(got))
    finally:
        for k in names:
            os.environ.pop(k, None)
        for k, v in kept.items():
            if v is not None:
                os.environ[k] = v
        proxy.shutdown()
        proxy.server_close()
        page.stop()
        try:
            (home / "posting-url.txt").unlink()
        except OSError:
            pass


def queue_server_checks(work, home, env, ports):
    """The editing queue's page server (edit_queue.py serve), started and stopped by its own number: only its own
    small pictures, never the Studio File through "%2e%2e" or a folder's list, nothing for a request naming another
    host, and two presses at once both answered (Nov 6 follow-up: one in three was dropped)."""
    qhome = work / "queue studio-home"
    (qhome / "queue-thumbs" / "smith-2026-10-24").mkdir(parents=True)
    thumb = jpeg_bytes(16, 16, lambda bx, by: (200, 120, 40))
    (qhome / "queue-thumbs" / "smith-2026-10-24" / "0.jpg").write_bytes(thumb)
    (qhome / "studio.json").write_text('{"secret": "the Studio File"}', encoding="utf-8")
    q = {"shoots": [{"id": "smith-2026-10-24", "name": "Smith family 🌊", "shot": "2026-10-24", "due": "2026-11-20", "count": 12,
                     "folder": None, "studio": None, "shoot": None, "thumbs": ["queue-thumbs/smith-2026-10-24/0.jpg"],
                     "status": "waiting", "added": "2026-10-24T10:00:00"}], "picks": {}, "manual_order": False}
    (qhome / "queue.json").write_text(json.dumps(q, ensure_ascii=False), encoding="utf-8")
    log = open(work / "queue server.log", "wb")
    srv = subprocess.Popen([sys.executable, str(SCRIPTS / "edit_queue.py"), "serve", "--port", str(ports[2])],
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                           env=child_env({"STUDIO_HOME": str(qhome)}))
    try:
        port, t0 = None, time.monotonic()
        while time.monotonic() - t0 < 30 and srv.poll() is None:
            try:
                said = (qhome / "queue-url.txt").read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            if said:
                from urllib.parse import urlsplit
                port = urlsplit(said).port
                if ask(port, "GET", "/nothing-here")[0] is not None:
                    break
            time.sleep(0.2)
        check("the editing queue's page server starts and says its address", port is not None and srv.poll() is None,
              (work / "queue server.log").read_bytes().decode("utf-8", "replace")[-300:])
        if port is None:
            return
        st, b = ask(port, "GET", "/queue-thumbs/smith-2026-10-24/0.jpg")
        check("it serves a queued shoot's small picture", st == 200 and b == thumb, str(st))
        leaks = {}
        for path in ("/queue-thumbs/%2e%2e/studio.json", "/queue-thumbs/%2e%2e/queue.json", "/queue-thumbs/",
                     "/queue-thumbs/smith-2026-10-24/", "/queue-thumbs/%2e%2e/",
                     "/queue-thumbs/smith-2026-10-24/%2e%2e/%2e%2e/studio.json"):
            st, b = ask(port, "GET", path)
            leaks["GET " + path] = (st, b"secret" in b or b"shoots" in b)
        for path in ("/studio.json", "/queue.json"):
            leaks["HEAD " + path] = (ask(port, "HEAD", path)[0], False)
        check("never the Studio folder's own files or a folder's list (%2e%2e, a folder's address, HEAD)",
              all(st == 404 and not leaked for st, leaked in leaks.values()), str(leaks))
        st, b = ask(port, "GET", "/queue-thumbs/%2e%2e/studio.json", host=f"evil.example:{port}")
        st2, _ = ask(port, "POST", "/queue", host=f"evil.example:{port}", body={"action": "done", "id": "smith-2026-10-24"})
        saved = json.loads((qhome / "queue.json").read_bytes().decode("utf-8"))
        st3, _ = ask(port, "GET", "/queue.html", host=f"localhost:{port}")
        check("a request naming another host is refused (403) and changes nothing; the page still answers to localhost",
              st == 403 and b"secret" not in b and st2 == 403 and saved["shoots"][0]["status"] == "waiting" and st3 == 200,
              f"{st} {st2} {saved['shoots'][0]['status']} {st3}")
        answered, errors = [0], []
        lock = threading.Lock()

        def presses(n):
            for i in range(25):
                st, _ = ask(port, "POST", "/queue", body={"action": "due", "id": "smith-2026-10-24",
                                                         "due": f"2026-12-{(n * 25 + i) % 28 + 1:02d}"})
                with lock:
                    if st == 200:
                        answered[0] += 1
                    else:
                        errors.append(st)
        ts = [threading.Thread(target=presses, args=(n,)) for n in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        try:
            whole = json.loads((qhome / "queue.json").read_bytes().decode("utf-8"))["shoots"][0]["name"] == "Smith family 🌊"
        except (OSError, ValueError, KeyError, IndexError):
            whole = False
        left = sorted(p.name for p in qhome.iterdir() if p.name.endswith(".tmp"))
        check("100 presses at once: every one answered, the queue whole (its emoji too), no scratch copy left",
              answered[0] == 100 and not errors and whole and not left, f"{answered[0]} answered, {errors[:5]} {left}")
    finally:
        srv.terminate()
        try:
            srv.wait(15)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(15)
        log.close()


def capcut_checks(work, home, env, ports):
    """CapCut's waiting list (reels made while CapCut's own list couldn't be written): an entry damaged by hand is
    left out; `capcut.py open --closed` adds a waiting reel to a pretend CapCut list without asking whether CapCut is
    open. Never the real CapCut: on a Mac a stand-in for `open` (and for `pgrep`, which must not be asked), on a PC
    only where no CapCut is installed (else SKIP), and the list is a pretend one in this test's folder."""
    if str(REEL) not in sys.path:
        sys.path.insert(0, str(REEL))
    import capcut
    store = work / "pretend CapCut store"
    (store / "Reel A").mkdir(parents=True)
    (store / "Reel A" / "draft_info.json").write_text("{}", encoding="utf-8")
    good = {"draft_id": "AAA-1", "draft_json_file": str(store / "Reel A" / "draft_info.json"), "draft_name": "Reel A",
            "tm_draft_create": 1700000000000000}
    (store / capcut.WAITING).write_text(json.dumps([good, dict(good, draft_id="BBB-2", tm_draft_create="soon")]), encoding="utf-8")
    waiting = getattr(capcut, "waiting", None) or (lambda s: capcut._waiting(Path(s)))   # (an older capcut.py: its own)
    got = [x.get("draft_id") for x in waiting(store)]
    check("CapCut's waiting list: an entry damaged by hand (its time not a number) is left out", got == ["AAA-1"], str(got))
    child = {}
    stub_log = work / "stand-in tools.log"
    if tc.MAC:
        stubs = work / "stand-in tools"
        stubs.mkdir()
        for tool in ("open", "pgrep"):
            (stubs / tool).write_text(f"#!/bin/sh\nprintf '{tool} %s\\n' \"$*\" >> \"$STAND_IN_LOG\"\nexit {0 if tool == 'open' else 1}\n",
                                      encoding="utf-8")
            os.chmod(stubs / tool, 0o755)
        child = {"PATH": str(stubs) + os.pathsep + os.environ.get("PATH", ""), "STAND_IN_LOG": str(stub_log)}
        want_code, want_words = 0, "The reel that was waiting is in its list now."
    elif tc.WINDOWS:
        if any(p.is_file() for p in capcut._windows_capcut_programs()):
            skip("capcut.py open --closed", "CapCut is installed on this PC, and this would start it")
            return
        want_code, want_words = 2, "couldn't find CapCut"
    else:
        skip("capcut.py open --closed", "neither a Mac nor a PC")
        return
    code, out = run_python([REEL / "capcut.py", "open", "--closed", "--store", store], env=dict(env, **child))
    try:
        listed = [x.get("draft_id") for x in json.loads((store / "root_meta_info.json").read_bytes().decode("utf-8"))["all_draft_store"]]
    except (OSError, ValueError, KeyError, TypeError):
        listed = None
    tools = stub_log.read_text(encoding="utf-8").splitlines() if stub_log.is_file() else []
    check("`capcut.py open --closed` adds the waiting reel (only the good one) to CapCut's list without asking whether "
          "CapCut is open, then starts it" + (" (a stand-in for the Mac's open)" if tc.MAC else " (none here: it says so)"),
          code == want_code and want_words in out and listed == ["AAA-1"] and waiting(store) == []
          and (not tc.MAC or tools == ["open -a CapCut"]), f"{code} {listed} {tools} {out[-300:]}")


def picker_answer_checks(work, home, env, ports):
    """What a PC's folder window answers, read back (this_computer._picked): the folder comes back as base64 of its
    UTF-8 bytes, so a name with an accent, curly quotes and an emoji comes back exactly whatever Windows PowerShell
    does to its output. On Windows, a real Windows PowerShell writes it (the window itself needs a screen)."""
    d = work / "pick" / "Café “shoot” 🌊"
    d.mkdir(parents=True)
    b64 = base64.b64encode(str(d).encode("utf-8")).decode("ascii")
    line = ("::folder::" + b64 + "\r\n").encode("ascii")
    for name, out in (("as it is", line), ("a byte-order mark in front", b"\xef\xbb\xbf" + line),
                      ("in UTF-16", ("\ufeff::folder::" + b64 + "\r\n").encode("utf-16-le")),
                      ("a line broken in two", line[:25] + b"\r\n" + line[25:]),
                      ("a warning printed after it", line + b"WARNING: something to say\r\n")):
        got = tc._picked(0, out)
        check(f"the folder window's answer is read back exactly: {name}", got == (str(d), ""), repr(got))
    got = tc._picked(0, b"::cancelled::\r\n")
    check("closing the folder window reads as cancelled", got == (None, "cancelled"), repr(got))
    if not tc.WINDOWS:
        skip("a real Windows PowerShell writing the folder's name", f"this is a {tc.COMPUTER}")
        return
    ps = "Write-Output ('::folder::' + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:ASSISTANT_PICK_TEST)))"
    for name, cmd in (("as it comes", ps), ("with a warning after it", ps + "; Write-Warning 'something to say'")):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=120,
                               env=dict(os.environ, ASSISTANT_PICK_TEST=str(d)))
            got, raw, err = tc._picked(r.returncode, r.stdout), r.stdout[:120], r.stderr[:200]
        except (OSError, subprocess.SubprocessError) as e:
            got, raw, err = None, b"", str(e)
        check(f"(a PC) Windows PowerShell's own output, {name}, gives the folder back exactly", got == (str(d), ""),
              f"{got!r} out={raw!r} err={err!r}")


_QUOTING_CHILD = """import json, sys
sys.path.insert(0, {scripts!r})
import kit
print("ANSWER " + json.dumps([kit._pc_arg(v) for v in json.loads(sys.argv[1])]))
"""


def quoting_checks(work, home, env, ports):
    """How a value is quoted in a line of a command Claude is handed on a PC (kit._pc_arg): PowerShell cuts a bare
    comma list into pieces, and reads $ and backticks inside double quotes."""
    want = {"1,2,3+": '"1,2,3+"', "Zoë’s beach 🌊": '"Zoë’s beach 🌊"', "C:/Users/Zoë/Your Content": '"C:/Users/Zoë/Your Content"',
            "Smith $5 shoot": "'Smith $5 shoot'", "Bob's $5": "'Bob''s $5'"}
    code, out = run_python(["-c", _QUOTING_CHILD.format(scripts=str(SCRIPTS)), json.dumps(list(want))], env=env)
    line = next((ln for ln in out.splitlines() if ln.startswith("ANSWER ")), "")
    try:
        got = dict(zip(want, json.loads(line[len("ANSWER "):])))
    except ValueError:
        got = {}
    check("on a PC each value of a command line is quoted so it arrives whole in PowerShell or Git Bash "
          "(a comma list in double quotes; a $ in single ones; an apostrophe beside a $ doubled)", got == want, f"{got} {out[-300:]}")


def dead_port(port):
    """A port where nothing listens, for a proxy that is set but dead: (a socket holding it, or None; whether it is
    dead). Held bound, never listening, when it can be, so nothing else starts listening there meanwhile; when it
    can't be (a moment after another server let go of it), only checked."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return s, True
    except OSError:
        s.close()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return None, False          # something answers there: not a dead proxy
    except OSError:
        return None, True


_REPORT_PROXY_CHILD = """import json, sys, urllib.request
sys.path.insert(0, {scripts!r})
import fresh
started = []
def no_server(cmd, *a, **k):
    started.append([str(x) for x in cmd][1:3])
    raise OSError("this test starts no page server")
fresh.start_server = no_server
import serve_report
try:   # a fresh opener, as a program just started has: does this Python's own fetch really take the proxy?
    urllib.request.build_opener().open({which!r}, timeout=5).read(1)
    plain = "answered"
except Exception as e:
    plain = type(e).__name__
r = serve_report.report_url({studio!r})
q = serve_report.queue_url()
print("ANSWER " + json.dumps({{"report": r, "queue": q, "started": started, "plain": plain}}))
"""


def report_server_checks(work, home, env, ports):
    """The report's own page server (serve_report.py), started the way the Assistant starts it and stopped by its own
    number: it answers to its own name only (127.0.0.1 or localhost, and its port), and refuses any other Host before
    anything is looked at or changed; and report_url() and queue_url() find a running server with a dead proxy set in
    the environment, starting no other (Nov 6, closing the last gaps: before, another host got every page and could
    press Rename, and a proxy made both look for, and start, servers that were already up)."""
    rs = work / "report server"
    session = rs / "2026-11-06 Côte card"
    studio = session / "_studio"
    studio.mkdir(parents=True)
    (studio / "manifest.json").write_text(json.dumps({"source": str(work / "report server card"), "dest": str(rs),
                                                      "files": {}}), encoding="utf-8")
    page = "<!doctype html><meta charset='utf-8'><title>Côte card</title><p>The report for Côte card</p>".encode("utf-8")
    (studio / "report.html").write_bytes(page)
    qhome = work / "report server studio-home"
    qhome.mkdir()
    queue_page = _StandIn(ports[1])                   # a queue page already up, for queue_url() to find
    queue_page.files["/queue.html"] = b"<title>Editing queue</title>"
    queue_at = f"http://127.0.0.1:{queue_page.port}/queue.html"
    (qhome / "queue-url.txt").write_text(queue_at + "\n", encoding="utf-8")
    log = open(work / "report server.log", "wb")
    srv = subprocess.Popen([sys.executable, str(SCRIPTS / "serve_report.py"), str(session), "--port", str(ports[0])],
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                           env=child_env({"STUDIO_HOME": str(qhome)}))
    port, said = None, ""
    try:
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30 and srv.poll() is None:
            try:
                said = (studio / "report-url.txt").read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            if said:
                from urllib.parse import urlsplit
                port = urlsplit(said).port
                if ask(port, "GET", "/which")[0] is not None:
                    break
            time.sleep(0.2)
        check("the report's page server starts and says its address", port is not None and srv.poll() is None,
              (work / "report server.log").read_bytes().decode("utf-8", "replace")[-300:])
        if port is None:
            return
        mine = {h: ask(port, "GET", "/report.html", host=h) for h in (f"127.0.0.1:{port}", f"localhost:{port}")}
        check("it answers to its own name: the report page, byte for byte, for 127.0.0.1 and for localhost (with its port)",
              all(st == 200 and b == page for st, b in mine.values()), str({h: (st, b[:60]) for h, (st, b) in mine.items()}))
        refused = {}
        for host in (f"evil.example:{port}", "127.0.0.1:1", "127.0.0.1", None):
            for method, path, body in (("GET", "/report.html", None), ("GET", "/which", None), ("GET", "/manifest.json", None),
                                       ("GET", "/rename-status", None), ("HEAD", "/report.html", None),
                                       ("POST", "/names", {"s1": "hacked"}), ("POST", "/rename", {"shoot": "s1", "name": "hacked"})):
                st, b = ask(port, method, path, host=host, body=body, no_host=host is None)
                refused[f"{host or 'no Host'} {method} {path}"] = (st, "Côte" in b.decode("utf-8", "replace") or b"files" in b)
        st, b = ask(port, "GET", "/rename-status")
        check("a request naming another host (another name, another port, no port, or no Host at all) is refused (403), "
              "nothing handed out and nothing changed (no names saved, no rename asked)",
              all(s == 403 and not leaked for s, leaked in refused.values()) and not (studio / "names.json").exists()
              and st == 200 and json.loads(b.decode("utf-8") or "{}") == {},
              str({k: v for k, v in refused.items() if v[0] != 403 or v[1]}) + f" names.json: {(studio / 'names.json').exists()} "
              f"rename-status: {st} {b[:80]!r}")
        st, b = ask(port, "POST", "/names", body={"s1": "Beach day"})
        try:
            kept = json.loads((studio / "names.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            kept = None
        check("and the page's own button still saves when it is asked by the server's own name", st == 200 and kept == {"s1": "Beach day"},
              f"{st} {kept}")
        # report_url() and queue_url(), in a program of their own with a proxy set that nothing answers
        holder, dead = dead_port(ports[4])
        try:
            if not dead:
                skip("report_url() and queue_url() with a dead proxy set", f"something answers on port {ports[4]}, so it is no dead proxy")
            else:
                proxy_at = f"http://127.0.0.1:{ports[4]}"
                penv = {"STUDIO_HOME": str(qhome), "no_proxy": "", "NO_PROXY": ""}
                penv.update({k: proxy_at for k in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY")})
                code, out = run_python(["-c", _REPORT_PROXY_CHILD.format(scripts=str(SCRIPTS), studio=str(studio),
                                                                         which=f"http://127.0.0.1:{port}/which")], env=penv)
                line = next((ln for ln in out.splitlines() if ln.startswith("ANSWER ")), "")
                try:
                    got = json.loads(line[len("ANSWER "):])
                except ValueError:
                    got = {}
                if got.get("plain") == "answered":
                    skip("report_url() and queue_url() with a dead proxy set",
                         "this Python's own fetch didn't use the proxy set in the environment, so there is nothing to show")
                else:
                    check("report_url() and queue_url() find this computer's own running servers with a dead proxy set in "
                          "the environment, and start no other",
                          code == 0 and got.get("report") == said and got.get("queue") == queue_at and got.get("started") == [],
                          f"{code} {got} wanted {said} and {queue_at} {out[-300:]}")
        finally:
            if holder is not None:
                holder.close()
    finally:
        srv.terminate()
        try:
            srv.wait(15)
        except subprocess.TimeoutExpired:
            srv.kill()
            srv.wait(15)
        log.close()
        queue_page.stop()
    if port is not None:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                answered = True
        except OSError:
            answered = False
        check("and once stopped by its own number, nothing answers on its port", not answered, f"port {port}")


_REPORT_OPEN_CHILD = """import http.client, json, os, pathlib, sys, threading, time, urllib.parse
from functools import partial
from http.server import ThreadingHTTPServer
sys.path.insert(0, {scripts!r})
import this_computer
if {simulate!r}:
    this_computer.WINDOWS = True     # simulated: a Mac pretending, its paths still the Mac's
import ntpath, serve_report
asked, stood = [], []
OWN = ntpath.normcase(ntpath.normpath({own!r}))   # the report's own network share: its lookups are stood in, never asked
def watch(cls, name):
    real = getattr(cls, name)
    def looked(self, *a, **k):
        s = str(self)
        if "127.0.0.1" in s:
            if ntpath.splitdrive(ntpath.normcase(ntpath.normpath(s)))[0] == OWN:
                stood.append(name + " " + s)
                if name == "resolve":   # as this computer would (Windows never climbs above a share with "..")
                    return type(self)(os.path.normpath(s))
                if name == "absolute":
                    return self
                if name in ("is_dir", "exists"):
                    return True
                raise OSError("stood in: nothing is asked of another computer here")
            asked.append(name + " " + s)
        return real(self, *a, **k)
    setattr(cls, name, looked)
own = type(pathlib.Path("."))
for name in ("resolve", "is_dir", "exists", "stat", "absolute"):
    if hasattr(pathlib.Path, name):
        watch(pathlib.Path, name)
    if own is not pathlib.Path and name in own.__dict__:
        watch(own, name)
opened = []
serve_report.show_in_finder = lambda p: (opened.append(str(p)), (True, ""))[1]   # never Finder or File Explorer
serve_report.Handler.allowed = ({allowed!r}, {own_folder!r})
serve_report.Handler.studio = {studio!r}
srv = None
for port in {ports!r}:
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), partial(serve_report.Handler, directory={studio!r}))
        break
    except OSError:
        continue
threading.Thread(target=srv.serve_forever, daemon=True).start()
out = {{}}
for want in json.loads(sys.argv[1]):
    before, stood_before, t0 = len(asked), len(stood), time.monotonic()
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=60)
    c.request("GET", "/open?path=" + urllib.parse.quote(want, safe=""))
    r = c.getresponse()
    said = json.loads(r.read().decode("utf-8"))
    c.close()
    out[want] = {{"status": r.status, "ok": said.get("ok"), "words": said.get("words"), "looked up": asked[before:],
                 "stood in": stood[stood_before:], "took": round(time.monotonic() - t0, 2)}}
srv.shutdown()
print("ANSWER " + json.dumps({{"answers": out, "opened": opened}}))
"""


def report_open_checks(work, home, env, ports):
    """The report's "Open photo folder" (/open) on a PC refuses a network path (//computer/share, \\\\computer\\share)
    as text, before Windows is asked about it: asking reaches out to that computer first. Every lookup of a path naming
    127.0.0.1 is recorded, and File Explorer and Finder are stood in. Real on Windows; on a Mac only simulated
    (this_computer.WINDOWS set in a program of its own, whose paths are still the Mac's).
    And a report whose photos are on a network drive of its own (a NAS, given a letter or not: once the backup has
    settled, Windows writes it as \\\\computer\\share\\...) still opens that folder: the share is a pretend one on
    127.0.0.1 whose every lookup is stood in, so not even this computer is asked anything by its address, while a
    look-alike next to it ("...X", a ".." out of the folder) is refused with nothing looked up."""
    allowed = work / "report open" / "2026-06-04 Shoot 1"
    allowed.mkdir(parents=True)
    studio = work / "report open" / "_studio"
    studio.mkdir()
    simulate = not tc.WINDOWS
    how = "(a PC)" if tc.WINDOWS else "(simulated on this Mac: this_computer.WINDOWS set in a program of its own)"
    # the report's own network folder, written the way the records hold it on a PC; with forward slashes on a Mac,
    # whose paths can only be taken apart at those
    sep = "\\" if tc.WINDOWS else "/"
    share = sep * 2 + "127.0.0.1" + sep + "photos"
    own_folder = share + sep + "The Assistant"
    own_want = own_folder + sep + "2026-06-04 Shoot 1"
    look_alikes = [share + sep + "The AssistantX", own_folder + sep + ".." + sep + ".." + sep + "c$"]
    wants = ["//127.0.0.1/c$", "\\\\127.0.0.1\\c$", "\\??\\UNC\\127.0.0.1\\c$", str(allowed), own_want] + look_alikes
    code, out = run_python(["-c", _REPORT_OPEN_CHILD.format(scripts=str(SCRIPTS), simulate=simulate, allowed=str(allowed.parent),
                                                            own=share, own_folder=own_folder, studio=str(studio),
                                                            ports=[ports[2], ports[3]]), json.dumps(wants)],
                           env=env)
    line = next((ln for ln in out.splitlines() if ln.startswith("ANSWER ")), "")
    try:
        got = json.loads(line[len("ANSWER "):])
    except ValueError:
        got = {}
    answers = got.get("answers") or {}

    def refused(a):   # at once, in plain words, nothing looked up and nothing even stood in
        return (a and a["status"] == 200 and a["ok"] is False and a["words"] == "That isn't a folder this report names."
                and a["looked up"] == [] and a["stood in"] == [] and a["took"] < 5)
    net = {w: answers.get(w) for w in wants[:3]}
    check(f"{how} the report's Open photo folder refuses //127.0.0.1/c$, \\\\127.0.0.1\\c$ and \\??\\UNC\\127.0.0.1\\c$ at once, in plain words, "
          "without asking Windows about them",
          code == 0 and all(refused(a) for a in net.values()), f"{code} {net} {out[-300:]}")
    mine = answers.get(wants[3]) or {}
    opened = got.get("opened") or []
    check(f"{how} and a folder the report names still opens (Finder and File Explorer stood in)",
          mine.get("ok") is True and str(mine.get("words", "")).startswith("Opened ") and opened[:1] == [str(allowed)],
          f"{mine} {opened}")
    theirs = answers.get(own_want) or {}
    stood = theirs.get("stood in") or []
    check(f"{how} and a report whose photos are on a network drive of its own opens that folder ({own_want}), its "
          "lookups stood in, nothing asked of any computer",
          theirs.get("ok") is True and str(theirs.get("words", "")).startswith("Opened ") and theirs.get("looked up") == []
          and any(s.startswith("resolve ") for s in stood) and any(s.startswith("is_dir ") for s in stood)
          and opened.count(own_want) == 1, f"{theirs} {opened}")
    odd = {w: answers.get(w) for w in look_alikes}
    check(f"{how} while a look-alike of that folder (another name starting the same, a '..' out of it) is refused at once, "
          "nothing looked up", code == 0 and all(refused(a) for a in odd.values()), f"{odd}")


_SAY_CHILD = """import errno, json, os, sys
r, w = os.pipe()
os.close(r)                 # nobody will ever read this pipe: a `| head` that has read enough
os.dup2(w, 1)
os.close(w)
try:                        # what this computer says when nobody reads: a Mac a broken pipe; Windows "invalid argument"
    os.write(1, b"probe\\n")
    probe = "written"
except OSError as e:
    probe = errno.errorcode.get(e.errno, str(e.errno))
os.write(2, ("PROBE " + probe + "\\n").encode("utf-8"))
sys.path[:0] = [{scripts!r}, {reel!r}]
import {module} as m
for i in range(3):
    m.say("line %d, with nobody reading" % i{extra})
os.write(2, b"CARRIED ON\\n")
os._exit(0)
"""
SAY_MODULES = ("backup", "sort", "settle", "sneak_peeks", "posts", "return_watch", "reel", "night")


def say_checks(work, home, env, ports):
    """Every say() changed on Nov 6 carries on when nobody reads what it prints (sort.py's is rename_shoot.py's too):
    a pipe whose reading end is closed, the way `| head -1` leaves it once it has its line. On a Mac that is a broken
    pipe; on Windows it is "invalid argument" (EINVAL), for real, which is the PC branch of each say()."""
    log = work / "return_watch said.log"
    for module in SAY_MODULES:
        extra = f", log={str(log)!r}" if module == "return_watch" else ""
        code, out = run_python(["-c", _SAY_CHILD.format(scripts=str(SCRIPTS), reel=str(REEL), module=module, extra=extra)], env=env)
        lines = out.splitlines()
        line = "CARRIED ON" in lines
        probe = next((ln[len("PROBE "):] for ln in lines if ln.startswith("PROBE ")), None)
        said = {"EPIPE": "a broken pipe", "EINVAL": "Windows' \"invalid argument\" (EINVAL), for real"}.get(probe, probe or "?")
        extra_ok = True
        if module == "return_watch":
            try:
                extra_ok = len(log.read_text(encoding="utf-8").splitlines()) == 3
            except OSError:
                extra_ok = False
        check(f"{module}.py's say() carries on when nobody reads what it prints ({said})"
              + (", its log keeping every line" if module == "return_watch" else ""),
              code == 0 and line and "Traceback" not in out and extra_ok, out[-400:])
        if tc.WINDOWS and probe not in ("EINVAL", None):
            info(f"what this PC said to {module}.py when nobody read", f"{probe}, not EINVAL: the PC branch was not the one tried")


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
    if ONLY == "posts":
        try:
            posts_checks(work)
        except Exception:  # noqa: BLE001
            import traceback
            check("the posts checks ran to the end", False, traceback.format_exc()[-1500:])
        return finish(work)
    if ONLY == "followup":
        followup_checks(work)
        return finish(work)
    if ONLY == "backup":
        whole_backups(work)
        return finish(work)

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

    # ---- the same card, with nobody reading what the backup says (a `| head` that has read enough), backup.py run on
    # its own, not through night.py. On a Mac each line fails as a broken pipe; on Windows as "invalid argument" (EINVAL,
    # CPython bpo-35754). Either way every file is copied and checked, the records and the report are written, and the
    # exit code is the backup's own. Its own drive folder, so the checks after it are unchanged.
    quiet_drive = work / "drive, nobody reading"
    quiet_drive.mkdir()
    gone_r, gone_w = os.pipe()
    os.close(gone_r)
    try:
        r = subprocess.run([sys.executable, str(SCRIPTS / "backup.py"), "--source", str(card), "--dest", str(quiet_drive),
                            "--name", "nobody reading", "--date", "2026-11-06"], stdout=gone_w,
                           stderr=subprocess.PIPE, env=child_env(env), timeout=STEP_TIMEOUT)
        code3, said = r.returncode, r.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        code3, said = 124, "TIMED OUT"
    finally:
        os.close(gone_w)
    quiet = quiet_drive / "2026-11-06 nobody reading"
    try:
        m = json.loads((quiet / "_studio" / "manifest.json").read_text(encoding="utf-8"))
        first = json.loads((studio / "manifest.json").read_text(encoding="utf-8"))
        whole = (bool(m.get("finished")) and not m.get("problems") and len(m["files"]) == len(first["files"])
                 and all(e.get("dest", {}).get("ok") for e in m["files"].values())
                 and (quiet / "_studio" / "morning-report.md").is_file()
                 and all(sha(p) == sha(quiet / p.relative_to(card)) for p in photos))
    except (OSError, ValueError, KeyError):
        whole = False
    check("a backup with nobody reading what it says still copies and checks every file and writes the report (exit 0)",
          code3 == 0 and whole, f"exit {code3} {said[-300:]}")

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
    try:
        posts_checks(work)
    except Exception:  # noqa: BLE001  (a fault in one check FAILs here and the whole backups still run)
        import traceback
        check("the posts checks ran to the end", False, traceback.format_exc()[-1500:])
    followup_checks(work)
    whole_backups(work)
    return finish(work)


def whole_backups(work):
    """Whole backups: this computer's own way; then the same twice more, read to the end and with nobody reading;
    on a Mac also the PC way."""
    print("\n-- a whole backup, start to finish" + (" (the Mac's own way: sips)" if pictures.use_sips() else ""))
    whole_backup(work / "whole", {})
    try:
        nobody_reading_checks(work)
    except Exception:  # noqa: BLE001  (a fault here FAILs; the PC way's backup still runs)
        import traceback
        check("the backup with nobody reading ran to the end", False, traceback.format_exc()[-1500:])
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


def finish(work):
    """The count, and the scratch folder: kept (and copied for GitHub) when something FAILED, else cleared away."""
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


# python3 tests/pc_smoke.py --only posts: just the post kit, the pickers, the posting queue, Canva and the posting
# server (a minute, not ten), for trying a change to those. --only followup: just the PC follow-up's part.
# --only backup: just the whole backups (this computer's own way, the two twins, and on a Mac the PC way).
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv[1:-1] else None

if __name__ == "__main__":
    if ONLY not in (None, "posts", "followup", "backup"):
        sys.exit("--only takes: posts, followup, backup")
    sys.exit(main())
