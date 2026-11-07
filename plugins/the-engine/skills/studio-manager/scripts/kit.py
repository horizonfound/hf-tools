#!/usr/bin/env python3
"""The post kit: everything for one shoot's social posts, in one folder, made at once.

    Your Content/2026-06-24 Beach/
      Photos/                  the finished photos (moved in from the drop box, or left where
                               Lightroom exported them and pointed to; never changed)
      Singles/                 the single posts, sized for Instagram (fit within 1080 x 1350)
      Carousel/                the slides in order, all 1080 x 1350 (padded so they match)
      Stories/                 story frames, 1080 x 1920
      Covers/                  the reel cover
      .kit/                    hidden: the Studio's own files, so the photographer sees only photo
                               folders (Dustin, Oct 30). The kit page (Post kit.html, every piece with
                               a Copy button), Captions and hooks.txt, Reel.txt, and the kit's records.
                               The page is shown through the posting server, never opened as a file.
                               Also here: slides-older/<time>/ (plain carousel slides a new order
                               replaced: moved here, never deleted, with moved.json saying what moved)
                               and slides-new/ (where new slides are made before any goes into Carousel).

Claude does the choosing and the writing; this does the files. Nothing posts.

    python3 kit.py start "beach"                       the kit for a shoot in Content (a few words find it)
    python3 kit.py start --night "<backup>" --shoot s1    a shoot the Studio backed up: finds their export folder,
                                                       makes the kit folder, points Photos at the exports
    python3 kit.py start --folder "<any folder of finished photos>" [--name "..."]
    python3 kit.py told "beach" --text "..."           what they said when asked about the shoot
    python3 kit.py told "beach" --text-file said.txt   the same, from a UTF-8 file (best on a PC: their words never
                                                       pass through the command line, which can change quotes and $)
    python3 kit.py sheet "beach"                       numbered contact sheets of the photos (reel.py's)
    python3 kit.py picks "beach" --singles 3,17,22 --stories 5,9,30,41 --carousel 1,4,8,12,15,19,23 --reel 2,6,... [--cover 2]
    python3 kit.py build "beach"                       Singles, Carousel, Stories from the picks (reel via reel.py)
    python3 kit.py facts "beach"                       what Claude writes the words from (JSON)
    python3 kit.py words "beach" --file words.json     save the hooks, caption, short caption, story lines
    python3 kit.py page "beach"                        rebuild Post kit.html
    python3 kit.py voice --sample-file posted.txt --never-file never.txt --audience both --hashtags "#..."
                                                       how they write for Instagram (asked once; in the Studio File)
    python3 kit.py show "beach"

Exit: 0 done, 1 problem, 2 nothing there, 7 the export folder could not be found (ask).

A Mac and a PC (Nov 6): the pictures are the Mac's own sips on a Mac, exactly as before, and on a PC Pillow
through pictures.py (the photo the right way up, Adobe RGB turned into sRGB, HEIC when pillow-heif is there).
Everything else the two computers do differently (saving over a file, giving a file its name, the lock, "has
that run ended?", how long a path may be) goes through this_computer.py. Every text file is UTF-8 on both.
"""
import argparse
import contextlib
import errno
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exif_read  # noqa: E402
import brand  # noqa: E402
import pictures  # noqa: E402
import posts  # noqa: E402
import studio_file  # noqa: E402
import this_computer  # noqa: E402

REEL_PY = HERE.parent.parent / "assistant-make-a-reel" / "scripts" / "reel.py"
PHOTO = posts.PHOTO
# Instagram's shapes, checked Oct 30, 2026 (Sked Social, posteverywhere.ai): feed posts 4:5 (1080x1350) are the
# safe default; 3:4 is in-app only; the profile grid shows a 3:4 tile cut from the middle of each post, so a 4:5
# post loses a sliver off each side there; every slide of a carousel takes the first slide's shape; stories and
# reels are 9:16 (1080x1920), with the grid showing the middle 3:4 of a reel's cover.
SINGLE = (1080, 1350)        # 4:5
CAROUSEL = (1080, 1350)      # 4:5, every slide the same
STORY = (1080, 1920)         # 9:16
COVER = (1080, 1920)         # the reel cover, 9:16; the grid shows its middle 3:4
GRID = (1080, 1440)          # 3:4, what the profile grid shows of a post
WIDEST = 1.91                # the widest Instagram keeps a feed photo; wider gets trimmed
PAD_DARK = "1A1A1C"
PAD_WHITE = "FFFFFF"
TOP_BIAS = 0.4               # when a tall photo is trimmed to 4:5, take 40% of the cut from the top, 60% from the bottom (faces sit high)
CAROUSEL_MOST = 20           # Instagram's own limit for one carousel (arrange.py's LIMITS says the same to the page)
KINDS = ("reel", "carousel", "singles", "stories")
FONTS = "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=DM+Sans:wght@400;500;600&display=swap"


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only: when whatever reads this output has gone away, Windows' C runtime reports it as "invalid
        # argument" (EINVAL), not as a broken pipe: the pipe's ERROR_NO_DATA is not in its list of errors, and
        # Microsoft's errno docs say an unlisted one becomes EINVAL. The work goes on, as it does on a Mac.
        # A Mac: anything else is raised, exactly as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


# ---------- finding a kit ----------

def rec_path(kit):
    return kit / ".kit" / "kit.json"


def load_rec(kit):
    p = rec_path(kit)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def hidden(kit):
    """The kit's hidden folder, made and hidden if it isn't yet."""
    d = kit / ".kit"
    d.mkdir(exist_ok=True)
    posts.hide(d)
    return d


# The Studio's own files in a kit. They used to sit at the top of the kit folder beside the photo folders;
# since Oct 30 they live in the hidden folder, so the photographer sees only Photos, Singles, Carousel,
# Stories and Covers. A kit made before that is tidied the next time its page is written: each of these
# is moved into the hidden folder (never deleted, never overwritten).
OWN_FILES = ("Post kit.html", "Captions and hooks.txt", "Reel.txt")


def own_file(kit, name):
    return hidden(kit) / name


def page_path(kit):
    return own_file(kit, "Post kit.html")


def tidy_own_files(kit):
    """Move the Studio's own files from the top of the kit into the hidden folder. Returns what moved."""
    moved = []
    for name in OWN_FILES:
        old = kit / name
        if old.is_file():
            new = own_file(kit, name)
            if new.exists():
                new = own_file(kit, f"{Path(name).stem} (older){Path(name).suffix}")
                if new.exists():
                    continue
            try:
                this_computer.rename(old, new)          # a Mac: exactly os.rename; a PC: patient if it is held open
            except (FileExistsError, this_computer.HeldOpen):
                continue        # only ever on a PC (a name taken a moment ago, or the file held open): left where it is, for next time
            moved.append(name)
    return moved


def save_rec(kit, rec):
    d = hidden(kit)
    tmp = d / f"kit.json.{os.getpid()}.tmp"     # a name of this process's own, so two commands never share a half-written file
    try:
        tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, d / "kit.json")
    except BaseException:
        # A save that fails (a full drive; on a PC, kit.json held open by another program) leaves the record as it
        # was, and its scratch copy is dropped: the next try is another process, which would never reuse its name.
        _drop_scratch(tmp)
        raise


def _drop_scratch(tmp):
    """Remove one of the Assistant's own scratch files, made a moment ago by this process; never a real file."""
    try:
        tmp.unlink()
    except OSError:
        pass


def _write_text_whole(path, text):
    """A text file of the kit's, in UTF-8 on both computers, written in full under a scratch name beside it and
    only then put in its place. A failure part way (a full drive, a character the old way could not write) leaves
    the earlier file exactly as it was, never an empty or half-written one."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()        # our own scratch copy, never the real file
        except OSError:
            pass
        raise


def find_kit(words):
    """A kit folder in Content from a few words of its name (or the exact folder name, or a path)."""
    p = Path(words)
    if p.is_dir() and (p / ".kit").is_dir():
        return p
    h = posts.need_home()
    content = h / posts.CONTENT_NAME
    if (content / words).is_dir():
        return content / words
    w = [x for x in re.split(r"[^a-z0-9]+", words.lower()) if x]
    hits = [d for d in content.iterdir() if d.is_dir() and not d.name.startswith(".") and all(x in d.name.lower() for x in w)]
    exact = [d for d in hits if load_rec(d).get("name", "").lower() == words.strip().lower()]
    if len(exact) == 1:
        return exact[0]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        say(f"STOP: nothing in Content matches \"{words}\". (posts.py list shows what's there.)")
        sys.exit(2)
    say(f"STOP: \"{words}\" could mean more than one: " + ", ".join(d.name for d in sorted(hits)) + ". Say which.")
    sys.exit(1)


def photos_dir(kit, rec=None):
    rec = rec or load_rec(kit)
    if rec.get("photos_dir"):
        return Path(rec["photos_dir"])
    return kit / "Photos"


def photo_files(folder):
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO and not p.name.startswith("."))


# ---------- how long a path may be (a PC only) ----------
#
# On a PC a file whose full address (the drive, every folder on the way, its own name) passes 260 characters
# can't be opened in File Explorer, and the Assistant's own hidden files can't pass it either unless long paths
# are switched on. So a kit, or a piece of one, that would be that long is stopped in plain words before
# anything is made or moved. A Mac has no such limit: none of this ever stops anything there.

LONG_WORDS = ("on a PC a file's full address, counting the drive, every folder on the way and its own name, can be "
              "at most 260 characters")


def _scratch(p):
    """The scratch name a picture is written under before it gets its own (see shape())."""
    p = Path(p)
    return p.with_name(f".part-{os.getpid()}-{p.name}")


def _too_long(shown=(), own=()):
    """The paths a PC could not take, from `shown` (files the photographer opens: held to 260 characters, as File
    Explorer is) and `own` (the Assistant's hidden files and scratch pictures: 260 too, unless long paths are on).
    A Mac: none, ever."""
    if not this_computer.WINDOWS:
        return []
    return ([Path(p) for p in shown if this_computer.path_too_long(p)]
            + [Path(p) for p in own if this_computer.records_path_too_long(p)])


# The longest name the photo pickers keep in a kit's hidden folder (.kit/previews): arrange.failed_mark, a photo's
# number, the big copy's size, a six-letter tag, the photo's size in bytes (room for ten digits, up to 9 GB) and its
# time to the billionth of a second (nineteen digits). It does not depend on the photo's own name, so a kit that has
# room for it when it is made has room for every picker record. (arrange.py checks again on its own, in plain words.)
PICKER_LONGEST = f"0000-1600-000000-{'0' * 10}-{'0' * 19}.failed"


def _kit_too_long(kit):
    """On a PC: a kit folder here would sit too deep (its own address, and room for its hidden files: the longest of
    them are the photo pickers' records and a carousel slide being made, which needs room even with the shortest
    photo name there can be). Stopped when the kit is made, rather than later at the picker or the slides. A Mac:
    never."""
    return bool(this_computer.path_too_long(kit, folder=True)
                or _too_long(own=[kit / ".kit" / f".Captions and hooks.txt.{os.getpid()}.tmp",
                                  _scratch(kit / ".kit" / "slides-new" / LONGEST_STAMP / "Slide 01 ().jpg"),
                                  kit / ".kit" / "previews" / PICKER_LONGEST]))


def _stop_kit_too_long(night=False):
    """A PC only. night: the kit is named after the backup's shoot folder (start --night takes no --name)."""
    fix = ("The kit takes its name from the shoot's folder, so a shorter name for the shoot (rename it)"
           if night else "A shorter name for the kit (--name)")
    say(f"STOP: that kit's folder would sit too deep in folders for this {this_computer.COMPUTER}: {LONG_WORDS}, "
        f"and the kit's own files, inside it, need room too. {fix}, or the {brand.short()} folder nearer the top "
        "of the drive, puts it right. Nothing was made.")
    sys.exit(1)


# ---------- start ----------

def start_from_folder(folder, name=None):
    folder = Path(folder)
    if not folder.is_dir():
        say(f"STOP: {folder} isn't a folder I can see.")
        sys.exit(2)
    files = photo_files(folder)
    if not files:
        say(f"STOP: no finished photos (JPEG, HEIC, PNG, TIFF) in {folder}.")
        sys.exit(2)
    h = posts.need_home()
    taken = sorted(t for t in ((exif_read.read(f) or {}).get("taken") for f in files[:200]) if t)
    when = taken[0] if taken else datetime.fromtimestamp(files[0].stat().st_mtime).isoformat()
    nm = posts.clean_name(name or posts.date_name([{"folders": [folder.name]}]))
    folder_name = posts.folder_name(nm, when)
    kit = h / posts.CONTENT_NAME / folder_name
    if kit.exists() and not (kit / ".kit").is_dir():
        say(f"STOP: there's already a folder in Content called \"{folder_name}\" that isn't a kit. Give this one another name.")
        sys.exit(6)
    if not kit.exists() and _kit_too_long(kit):
        _stop_kit_too_long()            # a PC only
    kit.mkdir(parents=True, exist_ok=True)
    rec = load_rec(kit) or {"name": nm, "date": when[:10], "folder": folder_name, "source": "folder", "made": datetime.now().isoformat(timespec="seconds")}
    rec["photos_dir"] = str(folder)
    rec["photos"] = [f.name for f in files]
    save_rec(kit, rec)
    return kit


def start_from_night(night, shoot_id):
    """A shoot the Studio backed up: its edited exports become the kit's photos (left where they are)."""
    from where import locate
    import find_exports
    root, studio = locate(night)
    shoots = json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    s = next((x for x in shoots if x["id"] == shoot_id), None)
    if not s:
        say(f"STOP: no shoot {shoot_id} in that backup.")
        sys.exit(1)
    names = json.loads((studio / "names.json").read_text(encoding="utf-8")) if (studio / "names.json").exists() else {}
    name = names.get(shoot_id) or s.get("name") or s.get("suggested") or shoot_id
    # Fixed Nov 6 (it stopped with an error on every computer since Oct 30): the Studio File may have no export
    # spot saved yet, and find_exports.find gives (shoot, photos, the folders it found, best first). The folder
    # taken is its best one, the same one find_exports.py itself shows and Claude confirms with them.
    remembered = studio_file.load().get("exports") or []
    _, _, found = find_exports.find(root, studio, shoot_id, remembered)
    if not found or not found[0].get("folder"):
        say("STOP: I couldn't find the edited photos for this shoot. Where did you export them? (exit 7)")
        sys.exit(7)
    folder = Path(found[0]["folder"])
    sh_folder = s.get("folder")
    folder_name = Path(sh_folder).name if sh_folder else posts.folder_name(name, s.get("start") or datetime.now().isoformat())
    h = posts.need_home()
    kit = h / posts.CONTENT_NAME / folder_name
    if not kit.exists() and _kit_too_long(kit):
        _stop_kit_too_long(night=True)  # a PC only
    kit.mkdir(parents=True, exist_ok=True)
    rec = load_rec(kit) or {"name": name, "date": (s.get("start") or "")[:10], "folder": folder_name, "source": "backup",
                            "made": datetime.now().isoformat(timespec="seconds")}
    rec.update({"night": str(night), "shoot_id": shoot_id, "photos_dir": str(folder), "photos": [f.name for f in photo_files(folder)]})
    save_rec(kit, rec)
    return kit


# ---------- the sheet and the picks ----------

def sheet(kit):
    rec = load_rec(kit)
    folder = photos_dir(kit, rec)
    r = subprocess.run([sys.executable, str(REEL_PY), "sheet", "--folder", str(folder), "--shoot", rec.get("name", kit.name)],
                       capture_output=True, encoding="utf-8", errors="replace")
    say(r.stdout.strip())
    if r.returncode != 0:
        say(r.stderr.strip())
        return 1
    m = re.search(r"List: (.+)", r.stdout)
    if m and Path(m.group(1).strip()).exists():
        listing = json.loads(Path(m.group(1).strip()).read_text(encoding="utf-8"))
        # whole or not at all: a page that reads the list while it is being re-made must see the old one or
        # the new one, never half of one (arrange.py takes a list it can't read as "not ready")
        tmp = kit / ".kit" / f"sheet.json.{os.getpid()}.tmp"
        try:
            shutil.copyfile(m.group(1).strip(), tmp)
            this_computer.replace(tmp, kit / ".kit" / "sheet.json")
        except BaseException:
            _drop_scratch(tmp)      # the list stays as it was; no scratch copy is left behind (see save_rec)
            raise
        rec["numbered"] = len(listing["photos"])
        save_rec(kit, rec)
    return 0


def numbered(kit):
    p = kit / ".kit" / "sheet.json"
    if not p.exists():
        say("STOP: make the sheet first (kit.py sheet), so the picks have numbers.")
        sys.exit(2)
    return {x["n"]: x for x in json.loads(p.read_text(encoding="utf-8"))["photos"]}


def parse_nums(s):
    return [int(x) for x in re.findall(r"\d+", s or "")]


def parse_reel(s):
    """The reel's picks the way reel.py reads them: a number, then + to linger or - to pass quickly ("19,4,10+,14-").
    Returns the numbers, and the marks as {"10": "+", "14": "-"}."""
    nums, marks = [], {}
    for n, m in re.findall(r"(\d+)([+-]?)", s or ""):
        nums.append(int(n))
        if m:
            marks[str(int(n))] = m
    return nums, marks


def reel_picks_text(rec):
    """The reel's picks as one line for reel.py make --picks, marks in place: 19,4,10+,14-"""
    marks = rec.get("reel_marks") or {}
    return ",".join(f"{n}{marks.get(str(n), '') if marks.get(str(n)) in ('+', '-') else ''}" for n in rec.get("picks", {}).get("reel") or [])


# What a PC's command line reads as its own inside quotes (a command there runs in PowerShell or in Git Bash,
# parts/on-a-pc.md). Inside double quotes: $ and the backtick in both, a double quote (PowerShell takes the curly
# ones for one too), and in Git Bash a backslash. Inside single quotes: only an apostrophe (PowerShell takes the
# curly ones for one too); everything else is read as it is, in both.
_PC_IN_DOUBLE = set('$`"\\“”„')
_PC_IN_SINGLE = set("'‘’‚‛")


def _pc_arg(text):
    """A PC only: one value for a line of a command Claude is handed, quoted so it reaches the script exactly as it
    is in PowerShell or in Git Bash. Double quotes when nothing in it means anything there; else single quotes when
    it holds no apostrophe; else PowerShell's own way, every apostrophe doubled inside single quotes (as on-a-pc.md
    says), which Git Bash would read differently: only for a value with both an apostrophe and a $, a backtick, a
    double quote or a backslash in it, which should be rare (paths come here with forward slashes)."""
    text = str(text)
    if not _PC_IN_DOUBLE.intersection(text):
        return f'"{text}"'
    if not _PC_IN_SINGLE.intersection(text):
        return f"'{text}'"
    return "'" + "".join(c + c if c in _PC_IN_SINGLE else c for c in text) + "'"


def _pc_both_ways(text):
    """True for a value no one way of quoting can carry through both PowerShell and Git Bash (_pc_arg's last case)."""
    text = str(text)
    return bool(_PC_IN_DOUBLE.intersection(text) and _PC_IN_SINGLE.intersection(text))


def set_picks(kit, singles, stories, carousel, reel, cover=None):
    by_n = numbered(kit)
    rec = load_rec(kit)
    picks = rec.get("picks", {})
    for key, val in (("singles", singles), ("stories", stories), ("carousel", carousel), ("reel", reel), ("cover", cover)):
        if val is None:
            continue
        marks = None
        if key == "reel":
            ns, marks = parse_reel(val)
        else:
            ns = parse_nums(val)
        if key == "cover":
            ns = ns[:1]
        bad = [n for n in ns if n not in by_n]
        if bad:
            say(f"STOP: no photo numbered {bad[0]} on the sheet.")
            sys.exit(1)
        if key == "carousel" and len(ns) > CAROUSEL_MOST:
            say(f"STOP: Instagram allows up to {CAROUSEL_MOST} photos in a carousel, and this pick has {len(ns)}. Nothing was changed.")
            sys.exit(1)
        picks[key] = ns         # plain numbers, always; the reel's marks sit beside the picks, never inside
        if marks is not None:
            rec["reel_marks"] = marks       # replaced whole whenever --reel is given
    rec["picks"] = picks
    save_rec(kit, rec)
    return picks


# ---------- building the pieces ----------

def size_of(p):
    """(width, height) of a photo, or None.
    A Mac: the Mac's own sips, the same command as always (pictures.size_of runs it), and its two numbers as they
    are, not turned for a photo shot sideways; Pillow's plain size if sips gave none and Pillow is here, as before.
    A PC: pictures.size_of, the right way up, which is how the PC's pictures are made too (shape())."""
    got = pictures.size_of(p)
    if got or not pictures.use_sips():
        return got
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def _pad_rgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def place(tmp, dst):
    """Give a finished file its final name, only if that name is free. Never writes over anything.
    True if the file now has that name. On a Mac a hard link is tried first, because it fails by itself when the
    name is taken, whatever else is going on; a drive with no hard links (exFAT) gets a look, then a rename. On a
    PC a rename, which Windows itself refuses onto a name that is taken. Both ways are this_computer.rename_new
    (the Mac's is exactly what this did before Nov 6)."""
    return this_computer.rename_new(Path(tmp), Path(dst))


def _finish_shape(tmp, dst, ok, replace):
    """The end of shape(): the scratch file becomes the real one, or is dropped."""
    if ok and replace:
        this_computer.replace(tmp, dst)
        return True
    if ok and place(tmp, dst):
        return True
    try:
        if tmp.exists():
            tmp.unlink()    # our own scratch file: half-made, or made for a name someone took a moment ago
    except OSError:
        pass
    return bool(ok) and dst.is_file()


def shape(src, dst, box, how, pad=PAD_DARK, bias=TOP_BIAS, replace=False):
    """Make the photo fit Instagram's box (w, h) one of three ways, never stretching:
      "fit"   the whole photo inside the box, its own shape, no padding (a tall photo comes out narrower than the box)
      "pad"   the whole photo inside the box, padded to the box with a plain color
      "crop"  the box filled, the extra trimmed (tall photos lose a little top and bottom, more from the bottom)
    A Mac: its own sips does all of it with nothing installed, exactly the command it always ran (a photo shot
    sideways keeps the camera's turn mark, as sips keeps it). A PC: Pillow, through pictures._open, so the photo
    is the right way up, Adobe RGB is turned into sRGB and HEIC opens when pillow-heif is there; the sizes come
    out the same as sips makes them, from the same sums.
    The picture is written under a scratch name beside dst ('.part-<process>-<name>', which every listing
    here skips) and gets its real name only when it is whole, and only if that name is free: a run that is
    cut off leaves no half-made file under a real name, and nothing is ever written over. replace=True is
    for the Assistant's own small thumbnails, which follow the files they are made from."""
    W, H = box
    dst = Path(dst)
    tmp = _scratch(dst)
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if how == "crop":
        scale = max(W / w, H / h)
    else:
        scale = min(W / w, H / h, 1.0)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    cut_y = max(0, nh - H) if how == "crop" else 0
    cut_x = max(0, nw - W) if how == "crop" else 0
    off_y, off_x = round(cut_y * bias), cut_x // 2
    if pictures.use_sips():
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", "--resampleHeightWidth", str(nh), str(nw)]  # pc-ok: a Mac only (pictures.use_sips), the same command as always
        if how == "crop" and (cut_y or cut_x):
            cmd += ["--cropOffset", str(off_y), str(off_x), "--cropToHeightWidth", str(H), str(W)]
        elif how == "pad":
            cmd += ["--padToHeightWidth", str(H), str(W), "--padColor", pad]
        cmd += [str(src), "--out", str(tmp)]
        try:
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
            ok = r.returncode == 0 and tmp.is_file() and tmp.stat().st_size > 0
        except OSError:
            ok = False
        return _finish_shape(tmp, dst, ok, replace)
    try:
        Image = pictures._pillow()
        # Opened at least twice the size it is made at (Pillow's own thumbnail does the same): a big JPEG is
        # read small, many times quicker, with room left for a clean resize.
        im = pictures._open(src, 2 * max(nw, nh)) if Image is not None else None
        if im is None:
            return _finish_shape(tmp, dst, False, replace)
        icc = im.info.get("icc_profile")
        im = im.resize((nw, nh), pictures._const(Image, "Resampling", "LANCZOS"))
        if how == "crop" and (cut_y or cut_x):
            im = im.crop((off_x, off_y, off_x + W, off_y + H))
        elif how == "pad":
            bg = Image.new("RGB", (W, H), _pad_rgb(pad))
            bg.paste(im, ((W - nw) // 2, (H - nh) // 2))
            im = bg
        kw = {"quality": 92}
        if icc:
            kw["icc_profile"] = icc     # the photo's own colours, labelled as sips keeps them
        im.save(tmp, "JPEG", **kw)
        return _finish_shape(tmp, dst, True, replace)
    except Exception:
        return _finish_shape(tmp, dst, False, replace)


def fit(src, dst, box, pad=None):
    """Kept for the Assistant's own thumbnails (the posting queue's, the home page's), which are re-made
    whenever the piece they show changes: fit, padded if a color is given."""
    return shape(src, dst, box, "pad" if pad else "fit", pad or PAD_DARK, replace=True)


def single(src, dst):
    """A single post: tall photos become 4:5 (a little trimmed, more from the bottom); square stays square;
    wide photos keep their shape, trimmed only if wider than Instagram allows."""
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if h > w * 1.05:
        return shape(src, dst, SINGLE, "crop")
    if w > h * WIDEST:
        return shape(src, dst, (1080, round(1080 / WIDEST)), "crop")
    return shape(src, dst, (1080, 1080), "fit")


def slide(src, dst, pad=PAD_WHITE):
    """A carousel slide: every slide 4:5. Tall photos are trimmed to it; square and wide ones sit on a plain
    background (white by default) so the whole photo shows."""
    size = size_of(src)
    if not size:
        return False
    w, h = size
    if h > w * 1.05:
        return shape(src, dst, CAROUSEL, "crop")
    return shape(src, dst, CAROUSEL, "pad", pad)

# ---------- the carousel's plain slides: made new, the earlier ones set aside, never written over ----------
#
# A carousel's slides are files called "Slide 01 (<photo name>).jpg", so a new order means new names. The
# slides a new order needs are made first, in the kit's hidden folder (.kit/slides-new/<time>/). Only when
# every one is whole does anything in the Carousel folder change: what moves, and where, is written down
# (.kit/slides-older/<time>/moved.json) BEFORE the first file moves; the earlier plain slides are moved into
# that folder (a move on the same drive: the same bytes under a new address, checked by hash); the new ones
# are moved into Carousel. A run that is cut off anywhere is finished by the next run, from what was written
# down. Nothing is deleted, nothing is written over, and a file the Assistant did not make stays where it is.

SLIDE_NAME = re.compile(r"^Slide (\d\d) \((.+)\)\.jpg$")
MOVED = "moved.json"
LONGEST_STAMP = "0000-00-00 000000 99"     # as long as a run's own folder name gets (a date, a time, a count): for the PC's length check


def _test_stop(name):
    """For the tests only: stop dead at a named point, the way a power cut or a kill would.
    ARRANGE_TEST_STOP names the point; ARRANGE_TEST_STOP_ONCE (a file to make) limits it to one time."""
    if os.environ.get("ARRANGE_TEST_STOP") != name:
        return
    once = os.environ.get("ARRANGE_TEST_STOP_ONCE")
    if once:
        if os.path.exists(once):
            return
        Path(once).write_text(name, encoding="utf-8")
    os._exit(9)


def _nf(name):
    """A name in one normal form. Drives keep an accented letter in different ways (an HFS+ drive always as
    the plain letter followed by its accent, others as it was typed), so the same name can come back from a
    folder's listing as a different string of letters. Names are compared through this, never letter for letter."""
    return unicodedata.normalize("NFC", name)


def _fold(name):
    """For asking "would a drive that ignores capitals take these two for the same name?"."""
    return _nf(name).casefold()


def _listing(folder):
    """The names in a folder, exactly as the drive lists them."""
    try:
        return set(os.listdir(folder))
    except OSError:
        return set()


def _names(folder):
    """{a name in its normal form: the same name as the drive lists it}. A drive that ignores capitals says
    yes to any spelling; its listing does not, so "is it there" is always asked of the listing."""
    return {_nf(n): n for n in _listing(folder)}


def _has(folder, name):
    return _nf(name) in _names(folder)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_whole(path, obj):
    """A record of the kit's, as JSON in UTF-8, written in full under a scratch name and only then put in place
    (_write_text_whole does the same for its text files, and drops its scratch copy the same way on a failure)."""
    _write_text_whole(path, json.dumps(obj, indent=1, ensure_ascii=False))


@contextlib.contextmanager
def _held(lock_file, wait):
    """Hold a lock on a file for as long as the work takes, across processes; the computer lets go of it even
    if the holder dies. Yields "held" when it is held, "none" when it can't be had at all (a drive with no such
    locks, a folder that isn't there: the work goes on without one), and False when something else kept it
    for longer than `wait` seconds. The lock file's folder is never made here.
    The lock itself is this_computer.try_lock: on a Mac fcntl.flock, exactly as before; on a PC msvcrt.locking
    on the file's first byte (unproven on a real PC)."""
    try:
        f = open(lock_file, "ab")           # never written: only held
    except OSError:
        f = None
    got = "held"
    end = time.time() + wait
    while f is not None:
        mine = this_computer.try_lock(f)
        if mine:
            break
        if mine is False:                   # something else holds it right now
            if time.time() > end:
                got = False
                break
            time.sleep(0.05)
            continue
        f.close()                           # None: no locks on this drive (or this computer)
        f = None
    if f is None:
        got = "none"
    try:
        yield got
    finally:
        if f is not None:
            if got:
                this_computer.unlock(f)
            f.close()


def update_rec(kit, change):
    """Read the kit record, change it (change(rec)), and save it, as one step that no other command of the
    Assistant's can get in the middle of. Every writer that works alongside another (the page's slide job,
    kit.py build, Claude's apply) changes the record this way, and only the keys that are its own, so one
    never puts back an older copy over what another has just written."""
    with _held(kit / ".kit" / "kit.lock", 10.0):
        rec = load_rec(kit)
        change(rec)
        save_rec(kit, rec)
        return rec


def _pid_gone(pid):
    """Has this process ended? Only ever True when the computer says so (this_computer.still_running: on a Mac
    os.kill(pid, 0) as before; on a PC the process is opened just to read whether it has ended)."""
    if pid <= 0:
        return False
    return this_computer.still_running(pid) is False


PART_NAME = re.compile(r"^\.part-(\d+)-")


def _sweep_parts(folder):
    """Drop the Assistant's own half-made scratch pictures ('.part-<process>-...') left in a folder by a run
    that was killed: only ones whose process has ended (on a PC also ones over a day old, since a PC soon gives a
    finished program's number to a new one). They never had a real name; no photo, slide or file of the
    photographer's is ever touched here."""
    for name in _listing(folder):
        m = PART_NAME.match(name)
        if not m:
            continue
        p = Path(folder) / name
        try:
            stale = _pid_gone(int(m.group(1))) or (this_computer.WINDOWS and time.time() - p.stat().st_mtime > 86400)
            if stale and p.is_file() and not p.is_symlink():
                p.unlink()
        except OSError:
            pass


def _sheet_or_none(kit):
    """The numbered photos by number, or None when the list is not there or cannot be read. Never exits."""
    try:
        return {x["n"]: x for x in json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))["photos"]}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _moving(kit):
    """The moves that are written down and not finished (their folders' names), oldest first."""
    older = kit / ".kit" / "slides-older"
    out = []
    for d in sorted(_listing(older)):
        try:
            j = json.loads((older / d / MOVED).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(j, dict) and j.get("state") == "moving":
            out.append(d)
    return out


def carousel_plan(kit, rec=None, nums=None):
    """What a carousel in this order needs done. Reads only; never exits (the page server asks it too).
    nums is the order (photo numbers); left out, it is the kit's own carousel pick.
      {"ok": True, "nums", "wanted": [slide names in order], "src": {name: where its photo is},
       "n_of": {name: photo number}, "make": [wanted names not in Carousel yet],
       "aside": [earlier plain slides that are not wanted now, named as the drive lists them],
       "clash": [files that will still be in Carousel and that the drive would take for a new slide's name],
       "moving": [records of a move that was cut off]}
      {"ok": False, "why": "sheet" | "photo", "photos": [numbers not on the list]}
    An earlier plain slide is a .jpg in Carousel that is not wanted now and is either one this kit's record
    says it made, or is named "Slide NN (<a photo of this shoot>).jpg". Canva's slides and anything else
    that was put there stay. Names are compared in one normal form (_nf), so a drive that keeps accented
    letters its own way is read right."""
    rec = rec if rec is not None else load_rec(kit)
    by_n = _sheet_or_none(kit)
    if not by_n:
        return {"ok": False, "why": "sheet", "photos": []}
    nums = list(nums if nums is not None else (rec.get("picks") or {}).get("carousel") or [])
    bad = [n for n in nums if n not in by_n]
    if bad:
        return {"ok": False, "why": "photo", "photos": bad}
    folder = photos_dir(kit, rec)
    wanted, src, n_of = [], {}, {}
    for i, n in enumerate(nums, 1):
        listed = Path(by_n[n]["file"])
        name = f"Slide {i:02d} ({listed.stem}).jpg"
        here = folder / listed.name        # the folder the kit names now, the file name from the list
        wanted.append(name)
        src[name] = here if here.is_file() else listed
        n_of[name] = n
    have = _names(kit / "Carousel")
    wanted_nf = {_nf(n) for n in wanted}
    ours = {_nf(x) for x in (rec.get("made_pieces") or {}).get("carousel") or []}
    stems = {_nf(Path(x["file"]).stem) for x in by_n.values()}
    aside = []
    for key in sorted(have):
        if key.startswith(".") or not key.endswith(".jpg") or key in wanted_nf or "(Canva)" in key:
            continue
        m = SLIDE_NAME.match(key)
        if key in ours or (m and m.group(2) in stems):
            aside.append(have[key])
    make = [n for n in wanted if _nf(n) not in have]
    # A new slide can only be put in if the drive does not take its name for that of a file that is staying
    # (the Mac's own disk and most photo drives ignore capitals). Found out here, before anything is made or moved.
    staying = {_fold(a): a for a in have.values() if a not in aside}
    clash = [staying[_fold(n)] for n in make if _fold(n) in staying]
    return {"ok": True, "nums": nums, "wanted": wanted, "src": src, "n_of": n_of,
            "make": make, "aside": aside, "clash": clash, "moving": _moving(kit)}


def carousel_in_order(kit, nums):
    """Are the plain slides in the Carousel folder already exactly this order, with the kit's record saying
    the same and no move left unfinished? Reads only; never exits."""
    try:
        rec = load_rec(kit)
        plan = carousel_plan(kit, rec, nums)
        return bool(plan.get("ok") and nums and not plan["make"] and not plan["aside"] and not plan["moving"]
                    and list((rec.get("picks") or {}).get("carousel") or []) == list(nums)
                    and list((rec.get("made_pieces") or {}).get("carousel") or []) == plan["wanted"])
    except (OSError, ValueError, TypeError, KeyError):
        return False


def carousel_shown(kit, rec=None):
    """Which slides are "the carousel" on the kit page and in the posting queue: the one rule for both.
    Reads only; never exits. The Carousel folder can hold plain slides, Canva's slides and any number of
    sets laid out in the designer (design.py), side by side; nothing in it is ever taken away to choose.
      * the newest laid-out set (rec["carousel_set"], kind "laid-out"), when every one of its files is in the
        folder's own listing and no Canva carousel was fetched after it was saved: those files, in order;
      * otherwise today's listing (every .jpg, Canva's first) without any file of any laid-out set.
    A new order from the picker or from kit.py build sets carousel_set back to plain (_finish_move), which
    puts the plain slides back as the ones shown and touches no laid-out file.
    {"kind": "laid-out" | "listing", "files": [paths], "base": the set's name or "", "others": how many other
     pictures are in the folder, "laid_out": how many laid-out slides are in the folder and not shown}"""
    rec = rec if rec is not None else load_rec(kit)
    car = kit / "Carousel"
    have = _names(car)
    sets = [x for x in (rec.get("laid_out") or []) if isinstance(x, dict)]
    cs = rec.get("carousel_set")
    if isinstance(cs, dict) and cs.get("kind") == "laid-out":
        sets = sets + [cs]
    in_sets = {_nf(str(n)) for x in sets for n in (x.get("files") or [])}
    listed = sorted((have[k] for k in have if k.lower().endswith(".jpg") and not k.startswith(".")),
                    key=lambda n: ("(Canva)" not in n, n))
    if isinstance(cs, dict) and cs.get("kind") == "laid-out" and cs.get("files"):
        mine = [_nf(str(n)) for n in cs["files"]]
        fetched = str(((rec.get("canva") or {}).get("fetched") or {}).get("Carousel") or "")
        if all(n in have for n in mine) and not (fetched and fetched > str(cs.get("shown") or cs.get("saved") or "")):
            return {"kind": "laid-out", "files": [car / have[n] for n in mine], "base": str(cs.get("base") or ""),
                    "others": len([n for n in listed if _nf(n) not in set(mine)]), "laid_out": 0}
    plain = [n for n in listed if _nf(n) not in in_sets]
    return {"kind": "listing", "files": [car / n for n in plain], "base": "", "others": 0, "laid_out": len(listed) - len(plain)}


def carousel_files(kit, rec=None):
    """The carousel's slides as the kit page and the posting queue show them, in order (see carousel_shown)."""
    return carousel_shown(kit, rec)["files"]


def canva_behind(rec):
    """Do this kit's Canva carousel slides show an earlier choice of photos than the plain slides do now?
    True only when a Canva carousel is on record AND the carousel has changed since it was made:
      * the Canva record carries the pick it was made from (canva_kit.py note writes it): behind when that
        is not the kit's pick now. No clock comes into it, and going back to that order makes it false again.
      * an older Canva record without one: behind when the plain slides were last changed after it was made."""
    c = (rec.get("canva") or {}).get("carousel")
    if not isinstance(c, dict) or not c:
        return False
    if isinstance(c.get("picks"), list):
        return list(c["picks"]) != list((rec.get("picks") or {}).get("carousel") or [])
    changed, made = rec.get("carousel_changed"), c.get("made")
    if changed and made:
        return str(changed) > str(made)
    return bool(changed)


def _move_one(src, dst):
    """One file to its new address, never over another. "moved", "there" (already done), or a word for
    what is in the way: "clash" (another file has that name), "gone" (it is in neither place)."""
    in_src = _has(src.parent, src.name)
    in_dst = _has(dst.parent, dst.name)
    if in_src and in_dst:
        try:
            same = os.path.samefile(src, dst)
        except OSError:
            same = False
        if not same:
            return "clash"
        os.unlink(src)          # one file under two names (a move cut off half way): drop the old name
        return "moved"
    if in_dst:
        return "there"
    if not in_src:
        return "gone"
    return "moved" if place(src, dst) else "clash"


def _undo_move(kit, stamp, j, blocked):
    """A move that cannot be finished (a file turned up in the Carousel folder under a name a new slide
    needs, or a new slide is no longer where it was made) is put back, so nothing is ever left half way for
    good: the new slides already put in go back to the making folder, and the earlier slides come back from
    the set-aside folder under their own names. Nothing is deleted and nothing is written over; an earlier
    slide whose name has been taken meanwhile stays set aside and is named in the record. The record ends
    as "undone". Safe to cut off: until that is written the record still says "moving", and the next run
    starts again from the top."""
    older = kit / ".kit" / "slides-older" / stamp
    new = kit / ".kit" / "slides-new" / stamp
    car = kit / "Carousel"
    made_sums = j.get("made_sums") or {}
    to = j.get("aside_to") or {}
    for name in j.get("place") or []:
        if _has(car, name) and not _has(new, name):
            # only a file that is the slide this run made goes back (by its hash, written down before the move)
            if made_sums.get(name) and _sha(car / name) == made_sums[name]:
                new.mkdir(parents=True, exist_ok=True)
                _move_one(car / name, new / name)
    left = []
    for name in j.get("aside") or []:
        if _move_one(older / to.get(name, name), car / name) == "clash":
            left.append(name)
    j["state"] = "undone"
    j["blocked_by"] = blocked
    j["left_aside"] = left
    j["finished"] = datetime.now().isoformat(timespec="seconds")
    _write_whole(older / MOVED, j)
    return {"undone": True, "blocked": blocked, "left": left}


def _finish_move(kit, stamp):
    """Carry out (or finish) the move written down in .kit/slides-older/<stamp>/moved.json. Safe to run
    any number of times. It always ends: None when the move is done, or what _undo_move returns when it
    could not be and was put back. Trouble with the drive itself (full, read-only, gone) is raised as OSError
    and leaves the record saying "moving", for the next run."""
    older = kit / ".kit" / "slides-older" / stamp
    new = kit / ".kit" / "slides-new" / stamp
    car = kit / "Carousel"
    j = json.loads((older / MOVED).read_text(encoding="utf-8"))
    sums = j.get("sums") or {}
    made_sums = j.get("made_sums") or {}
    gone = list(j.get("gone") or [])
    differs = list(j.get("differs") or [])
    to = dict(j.get("aside_to") or {})
    for i, name in enumerate(j.get("aside") or []):
        got = _move_one(car / name, older / to.get(name, name))
        if got == "clash":
            # something else has that name in the set-aside folder: the slide goes in beside it under a free
            # name, which is written down before the file moves
            k = 2
            while _has(older, f"{Path(name).stem} ({k}).jpg"):
                k += 1
            to[name] = f"{Path(name).stem} ({k}).jpg"
            j["aside_to"] = to
            _write_whole(older / MOVED, j)
            got = _move_one(car / name, older / to[name])
        if got == "gone":
            if name not in gone:
                gone.append(name)       # someone took it out of the folder themselves; there is nothing to set aside
            continue
        if got == "clash":
            raise OSError(f"could not set {name} aside")
        if sums.get(name) and name not in differs and _sha(older / to.get(name, name)) != sums[name]:
            differs.append(name)        # it was changed between being written down and being moved: kept as it is now, and noted
        if i == 0:
            _test_stop("mid-aside")
    _test_stop("after-aside")
    for i, name in enumerate(j.get("place") or []):
        got = _move_one(new / name, car / name)
        if got == "there" and made_sums.get(name) and _sha(car / name) != made_sums[name]:
            got = "clash"               # a file is there under that name, and it is not the slide this run made
        if got in ("clash", "gone"):
            j["gone"], j["differs"] = gone, differs
            in_way = _names(car).get(_nf(name)) or next((a for a in _listing(car) if _fold(a) == _fold(name)), name)
            return _undo_move(kit, stamp, j, in_way if got == "clash" else "")
        if i == 0:
            _test_stop("mid-place")
    _test_stop("after-place")
    wanted = list(j.get("wanted") or [])
    changed = bool(j.get("place") or j.get("aside"))

    def note(rec):
        made = dict(rec.get("made_pieces") or {})
        made["carousel"] = wanted
        rec["made_pieces"] = made
        if changed:
            rec["carousel_changed"] = datetime.now().isoformat(timespec="seconds")
            if isinstance(rec.get("carousel_set"), dict) and rec["carousel_set"].get("kind") == "laid-out":
                # a new order: the plain slides are the carousel shown again (carousel_shown). The slides laid
                # out in the designer stay in the folder, and in rec["laid_out"], exactly as they are.
                rec["carousel_set"] = {"kind": "plain", "at": rec["carousel_changed"]}

    update_rec(kit, note)
    _test_stop("after-record")
    write_page(kit)
    _refresh_posting(kit)
    j["state"] = "done"
    j["gone"], j["differs"] = gone, differs
    j["finished"] = datetime.now().isoformat(timespec="seconds")
    _write_whole(older / MOVED, j)
    try:
        os.rmdir(new)               # our own making folder, empty now (left alone if anything is still in it)
    except OSError:
        pass
    return None


MAKING_YOUNG = 600.0         # seconds: with no lock to go by, a making folder younger than this may be another run's


def _clear_making(kit, sure=True, only=None):
    """Slides a run made and never put in (a photo failed half way through, or the run was cut off before it
    wrote down a move) are the Assistant's own scratch: they never had a place in the Carousel folder, and
    the next run makes its own afresh from the photos. They are dropped here, so a run that fails again and
    again (a nearly full drive) does not eat what room is left. Only the making folder (.kit/slides-new) is
    looked at, only folders with no move still written down as unfinished, and only files named like a slide
    or like a scratch picture; anything else found there is left. Called by the run that holds the slides
    lock. sure=False (this drive has no locks, so another run could be at work): a folder touched in the
    last ten minutes is left for a later run. only names this run's own making folder, to clear just that."""
    root = kit / ".kit" / "slides-new"
    moving = set(_moving(kit))
    for d in sorted(_listing(root)):
        folder = root / d
        if d in moving or folder.is_symlink() or not folder.is_dir() or (only is not None and d != only):
            continue
        if only is None and not sure:
            try:
                if time.time() - folder.stat().st_mtime < MAKING_YOUNG:
                    continue
            except OSError:
                continue
        for name in _listing(folder):
            p = folder / name
            if (SLIDE_NAME.match(_nf(name)) or PART_NAME.match(name)) and p.is_file() and not p.is_symlink():
                try:
                    p.unlink()
                except OSError:
                    pass
        try:
            os.rmdir(folder)
        except OSError:
            pass


def _refresh_posting(kit):
    """If this kit's carousel is already in the posting queue, its picture there follows the new first slide.
    A nicety: the kit itself is already right, so any trouble here is left for the next time."""
    try:
        import posting_queue as pq
        return pq.refresh_kit_carousel(kit)
    except (Exception, SystemExit):  # noqa: BLE001
        return False


SLIDES_WAIT = 120.0          # seconds to wait for another run that is changing this kit's slides


def _plain_os(e):
    """Trouble with the drive, in a few plain words and never a path."""
    winerror = getattr(e, "winerror", None) if this_computer.WINDOWS else None     # a Mac: always None
    if isinstance(e, this_computer.HeldOpen) or winerror in (32, 33):
        # a PC only (unproven on a real PC): another program has the file open (ERROR_SHARING_VIOLATION 32,
        # ERROR_LOCK_VIOLATION 33)
        return ("another program has one of these pictures open (a photo viewer, or a folder window showing it), "
                "so close that first")
    if winerror == 5:
        # a PC only (unproven on a real PC): ERROR_ACCESS_DENIED, after this_computer's few seconds of trying again.
        # Windows gives it for a folder that truly can't be written to, and also when a file is saved over or moved
        # while another program has it open: Python, and most programs, open a file without letting it be replaced
        # meanwhile, and that is how a replace onto it is refused (kit.json, moved.json, the kit page). Which of the
        # two it was can't be told from here, so the words name the likely one first and the other after it.
        return ("another program may have one of this kit's files open (a photo viewer, or a folder window showing "
                "it), so close that first; if nothing has, a folder in this kit can't be written to")
    if e.errno == errno.ENOSPC:
        return "the drive is full"
    if e.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
        return "a folder in this kit can't be written to"
    if e.errno in (errno.ENOENT, errno.ENOTDIR, errno.EIO, errno.ENXIO):
        return "the kit's folder can't be reached (is the drive plugged in?)"
    return "the drive refused (" + (e.strerror or e.__class__.__name__).lower() + ")"


def rebuild_carousel(kit, nums=None, say_status=None, take=None):
    """One run at a time for a kit's slides, across processes (the page's own job and a command of Claude's
    must never both be moving files): a lock held on .kit/slides.lock for as long as the work takes, which
    the computer lets go of even if the run dies. A drive with no such locks is worked on without one.

    take, when given, is called with that lock still held as soon as the slides are in the order asked for
    ("done" or "same"): it is how the caller writes the order down as the kit's own pick, so the slides and
    the pick change together and no other run can come between the two.

    Trouble with the drive itself (full, read-only, unplugged) never comes out as an error: it is a problem
    like any other, in plain words, with "why": "move" when a move is written down and unfinished (the next
    run finishes it) and "write" when nothing in the Carousel folder had been changed."""
    blank = {"state": "problem", "count": 0, "made": 0, "aside": 0}
    try:
        lock_file = hidden(kit) / "slides.lock"
    except OSError as e:
        return dict(blank, why="write", detail=_plain_os(e))
    with _held(lock_file, SLIDES_WAIT) as mine:
        if not mine:
            return dict(blank, why="busy")
        try:
            res = _rebuild_carousel(kit, nums, say_status, sure=(mine == "held"))
        except OSError as e:
            try:
                moving = bool(_moving(kit)) or not (kit / ".kit").is_dir()
            except OSError:
                moving = True
            return dict(blank, why="move" if moving else "write", detail=_plain_os(e))
        if take is not None and res["state"] in ("done", "same"):
            take()
        return res


def _rebuild_carousel(kit, nums=None, say_status=None, sure=True):
    """Make the plain slides in the Carousel folder match an order: the kit's own carousel pick, or nums.
    The pick itself (rec['picks']) is not written here; whoever chose the order writes it (rebuild_carousel's take).

    In order: finish any move an earlier run was cut off in (or put it back, if it can't be finished); drop
    the scratch of runs that failed; work out what this order needs; if nothing, change nothing; refuse, with
    nothing touched, if a file that is staying has a name a new slide needs; make the new slides in the kit's
    hidden folder; write down what will move; set the earlier plain slides aside and put the new ones in.
    Then the kit's record, the kit page and the posting queue's picture follow. Safe to run twice and safe
    to cut off at any point.

    Returns {"state": "done" | "same" | "none" | "problem", "count", "made", "aside", "why", "photos", "detail",
    "files", "put_back", "left"}. A problem leaves the Carousel folder exactly as it was ("why": "sheet",
    "photo", "make", "clash", "redo", and on a PC only "long" and "tools"; for "clash", "files" names what is in
    the way, and "put_back" says a move had begun and was put back; "redo" is a move put back because a slide
    just made had gone from the hidden folder; "long": a slide's full address would pass what a PC allows,
    "photos" and "files" say which, and "deep": True when only the hidden folders it passes through are too
    long, not its own name in Carousel; "tools": the PC has no way to make pictures yet, "detail" says what to add).
    On a PC "detail" may also carry plain words for "photo" and "make" (pictures.why_not). Only trouble with the
    drive itself leaves a move unfinished (see rebuild_carousel)."""
    out = {"state": "same", "count": 0, "made": 0, "aside": 0}
    finished = 0
    undone = None
    plan = carousel_plan(kit, None, nums)
    if not plan.get("ok") and plan.get("why") == "sheet":
        return dict(out, state="problem", why="sheet")
    older_root = kit / ".kit" / "slides-older"
    for stamp in _moving(kit):
        got = _finish_move(kit, stamp)
        if got:
            undone = got
        finished += 1
    _clear_making(kit, sure)
    rec = load_rec(kit)
    plan = carousel_plan(kit, rec, nums)
    if not plan.get("ok"):
        return dict(out, state="problem", why=plan.get("why"), photos=plan.get("photos") or [])
    wanted = plan["wanted"]
    out["count"] = len(wanted)
    if not wanted:
        return dict(out, state="none")
    if not plan["make"] and not plan["aside"]:
        if list((rec.get("made_pieces") or {}).get("carousel") or []) != wanted:
            def note(r):                                      # the folder is right and only the record was behind
                made = dict(r.get("made_pieces") or {})
                made["carousel"] = wanted
                r["made_pieces"] = made
            update_rec(kit, note)
            write_page(kit)
            finished += 1
        return dict(out, state="done" if finished else "same")
    if plan["clash"]:
        return dict(out, state="problem", why="clash", files=plan["clash"], put_back=bool(undone), left=(undone or {}).get("left") or [])
    need = plan["make"]
    # a PC only, before anything is made: a way to make pictures, and every new slide's full address (in the
    # Carousel folder, in the hidden folders it passes through, under its scratch name) within what a PC allows
    ready, words = pictures.ready() if need else (True, "")
    if not ready:
        return dict(out, state="problem", why="tools", detail=words)
    # Two different troubles, told apart so the words are true: a slide whose own name in the Carousel folder would
    # be too long to open, or (the usual one where long paths are off) a kit that sits too deep for the hidden
    # folders a slide passes through on its way in, under longer names than the one it ends up with ("deep").
    run = kit / ".kit" / "slides-new" / LONGEST_STAMP
    aside_to = kit / ".kit" / "slides-older" / LONGEST_STAMP
    long_shown = [name for name in need if _too_long(shown=[kit / "Carousel" / name])]
    if long_shown:
        return dict(out, state="problem", why="long", photos=[plan["n_of"][name] for name in long_shown], files=long_shown)
    long_own = ([name for name in need if _too_long(own=[run / name, _scratch(run / name)])]
                + [name for name in plan["aside"] if _too_long(own=[aside_to / f"{Path(name).stem} (99).jpg"])])
    if long_own:
        return dict(out, state="problem", why="long", deep=True,
                    photos=[plan["n_of"][name] for name in long_own if name in plan["n_of"]], files=long_own)
    # every photo a new slide needs must be readable BEFORE anything is made
    cant = [plan["n_of"][name] for name in need if not plan["src"][name].is_file() or not size_of(plan["src"][name])]
    if cant:
        first = next(plan["src"][name] for name in need if plan["n_of"][name] == cant[0])
        why_not = pictures.why_not(first) if first.is_file() else None     # None on a Mac: the words stay as they were
        return dict(out, state="problem", why="photo", photos=cant, **({"detail": why_not} if why_not else {}))
    stamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
    k = 1
    while (kit / ".kit" / "slides-new" / stamp).exists() or (older_root / stamp).exists():
        k += 1
        stamp = datetime.now().strftime("%Y-%m-%d %H%M%S") + f" {k}"
    new = kit / ".kit" / "slides-new" / stamp
    hidden(kit)
    new.mkdir(parents=True)
    pad = rec.get("slide_background", PAD_WHITE)
    done = [0]

    def make(name):
        ok = slide(plan["src"][name], new / name, pad)
        done[0] += 1
        if say_status:
            say_status(done[0], len(need))
        return name, ok

    failed = []
    if need:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for name, ok in ex.map(make, need):
                if not ok or not _has(new, name):
                    failed.append(plan["n_of"][name])
    if failed:
        _clear_making(kit, only=stamp)  # the slides that did get made were for nothing: not left behind
        first = next(plan["src"][name] for name in need if plan["n_of"][name] == failed[0])
        why_not = pictures.why_not(first)  # None on a Mac: the words stay as they were
        return dict(out, state="problem", why="make", photos=failed, **({"detail": why_not} if why_not else {}))
    _test_stop("after-make")
    car = kit / "Carousel"
    car.mkdir(exist_ok=True)
    older = older_root / stamp
    older.mkdir(parents=True)
    journal = {"state": "moving", "aside": plan["aside"], "place": need, "wanted": wanted, "picks": plan["nums"],
               "picks_before": list((rec.get("picks") or {}).get("carousel") or []),
               "sums": {name: _sha(car / name) for name in plan["aside"]},
               "made_sums": {name: _sha(new / name) for name in need},
               "at": datetime.now().isoformat(timespec="seconds")}
    _write_whole(older / MOVED, journal)
    _test_stop("after-journal")
    got = _finish_move(kit, stamp)
    if got:
        # it could not be finished and was put back: a file turned up in the way between the look and the
        # move ("clash"), or a slide just made was no longer there to be put in ("redo")
        _clear_making(kit, only=stamp)
        if got.get("blocked"):
            return dict(out, state="problem", why="clash", files=[got["blocked"]], put_back=True, left=got.get("left") or [])
        return dict(out, state="problem", why="redo", left=got.get("left") or [])
    return dict(out, state="done", made=len(need), aside=len(plan["aside"]))


def carousel_trouble(res):
    """A problem from rebuild_carousel, in a line Claude can read."""
    why, photos = res.get("why"), res.get("photos") or []
    which = "photo " + ", ".join(str(n) for n in photos) if photos else "a photo"
    more = f" {res['detail']}" if res.get("detail") and why in ("photo", "make") else ""   # a PC only (pictures.why_not)
    if why == "photo":
        return f"(could not make the carousel slides: {which} can't be read right now. The Carousel folder was left as it was.{more})"
    if why == "make":
        return f"(could not make the carousel slides: {which} couldn't be sized. The Carousel folder was left as it was.{more})"
    if why == "long" and res.get("deep"):
        return (f"(could not make the carousel slides: this kit's folder sits too deep in folders for the slides to be made "
                f"on this {this_computer.COMPUTER}. The new slides are made, and the earlier ones set aside, in the kit's "
                f"hidden folder first, under longer names than the ones in the Carousel folder, and {LONG_WORDS}. The "
                "Carousel folder was left as it was. A shorter name for this kit's folder, shorter photo names, or the "
                f"{brand.short()} folder nearer the top of the drive puts it right.)")
    if why == "long":
        return (f"(could not make the carousel slides: the slide for {which} would have a name too long for this "
                f"{this_computer.COMPUTER} to open: {LONG_WORDS}. The Carousel folder was left as it was. Shorter photo "
                "names, or a shorter name for this kit's folder, put it right.)")
    if why == "tools":
        return f"(could not make the carousel slides: {res.get('detail') or 'pictures cannot be made on this computer yet.'} The Carousel folder was left as it was.)"
    if why == "sheet":
        return "(could not make the carousel slides: the numbered list can't be read. The Carousel folder was left as it was.)"
    if why == "busy":
        return "(the carousel's slides are being changed by something else right now. Nothing was changed; try again in a moment.)"
    if why == "write":
        return f"(could not make the carousel slides: {res.get('detail') or 'the drive refused'}. The Carousel folder was left as it was.)"
    if why == "clash":
        files = ", ".join(f'"{n}"' for n in res.get("files") or []) or "a file"
        left = res.get("left") or []
        if res.get("put_back"):
            return (f"(could not change the carousel slides: {files} is in the Carousel folder under a name a new slide needs. "
                    "The earlier slides were put back, so the Carousel folder is as it was" +
                    (f", except {len(left)} earlier slide{'s' if len(left) != 1 else ''} whose name had been taken, kept in the kit's hidden folder (.kit/slides-older)" if left else "") +
                    ". Ask them to rename or move that file, then run this again.)")
        return (f"(could not make the carousel slides: {files} in the Carousel folder has a name a new slide needs "
                "(this drive takes capital and small letters for the same). The Carousel folder was left as it was. "
                "Ask them to rename or move that file, then run this again.)")
    if why == "redo":
        return ("(the carousel's slides were not changed: a slide that had just been made was no longer in the kit's hidden folder "
                "when it was needed. The earlier slides were put back, so the Carousel folder is as it was. Run this again.)")
    return f"(the carousel's slides were not finished: {res.get('detail') or 'something was in the way'}. Nothing was lost; run this again to finish.)"


def build(kit):
    rec = load_rec(kit)
    picks = rec.get("picks", {})
    if not picks:
        say("STOP: no picks yet (kit.py picks).")
        return 2
    by_n = numbered(kit)
    made = {}
    # the reel cover: 9:16 from the cover pick (or the first reel pick), plus what the grid will show of it
    cover_n = picks.get("cover") or (picks.get("reel") or [None])[:1]
    cover_n = cover_n[0] if isinstance(cover_n, list) else cover_n
    # Before anything is made or moved (both only ever stop a PC; a Mac always has its own sips and no length
    # limit): a way to make pictures at all, and no piece whose full address would be longer than a PC allows
    # (the carousel's slides are checked on their own road, in rebuild_carousel).
    ready, words = pictures.ready()
    if not ready:
        say(f"STOP: {words} Nothing was made.")
        return 1
    planned = [kit / key.capitalize() / f"{prefix} {i:02d} ({Path(by_n[n]['file']).stem}).jpg"
               for key, prefix in (("singles", "Single"), ("stories", "Story"))
               for i, n in enumerate(picks.get(key) or [], 1) if n in by_n]
    if cover_n:
        planned += [kit / "Covers" / "Reel cover.jpg", kit / "Covers" / "Reel cover, as the grid shows it.jpg"]
    names = [p.name for p in planned if _too_long(shown=[p])]
    if names:
        say(f"STOP: {len(names)} of this kit's pictures would have a name too long for this {this_computer.COMPUTER} to "
            f"open (\"{names[0]}\"" + (f" and {len(names) - 1} more" if len(names) > 1 else "") + f"): {LONG_WORDS}. "
            "Shorter photo names, or a shorter name for this kit's folder, put it right. Nothing was made.")
        return 1
    # the picture's own name fits, but the slightly longer name it is made under first does not (long paths off)
    names = [p.name for p in planned if _too_long(own=[_scratch(p)])]
    if names:
        say(f"STOP: this kit's folder sits too deep in folders for its pictures to be made on this {this_computer.COMPUTER} "
            f"(\"{names[0]}\"" + (f" and {len(names) - 1} more" if len(names) > 1 else "") + "): each picture is made "
            f"first under a slightly longer working name, and {LONG_WORDS}. Shorter photo names, a shorter name for this "
            f"kit's folder, or the {brand.short()} folder nearer the top of the drive puts it right. Nothing was made.")
        return 1
    # The carousel first, by its own careful road: a new pick makes new slides and sets the earlier ones
    # aside (they used to be left in the folder, out of date). It reads the kit's pick itself, with the
    # slides lock held, so a pick the page's own job has just written is the one it goes by.
    car = rebuild_carousel(kit) if picks.get("carousel") else None
    makers = {"singles": (lambda a, b: single(a, b), "Single"),
              "stories": (lambda a, b: shape(a, b, STORY, "pad", PAD_DARK), "Story")}
    for key, (maker, prefix) in makers.items():
        ns = picks.get(key) or []
        if not ns:
            continue
        out = kit / key.capitalize()
        out.mkdir(exist_ok=True)
        _sweep_parts(out)
        files = []
        for i, n in enumerate(ns, 1):
            src = Path(by_n[n]["file"])
            dst = out / f"{prefix} {i:02d} ({src.stem}).jpg"
            if dst.exists() or maker(src, dst):
                files.append(dst.name)
            else:
                why_not = pictures.why_not(src) if src.is_file() else None      # None on a Mac: the line stays as it was
                say(f"(could not size {src.name} for {key})" + (f" {why_not}" if why_not else ""))
        made[key] = files
    if cover_n:
        out = kit / "Covers"
        out.mkdir(exist_ok=True)
        _sweep_parts(out)
        src = Path(by_n[cover_n]["file"])
        full, grid = out / "Reel cover.jpg", out / "Reel cover, as the grid shows it.jpg"
        ok = (full.exists() or shape(src, full, COVER, "crop")) and (grid.exists() or shape(full, grid, GRID, "crop", bias=0.5))
        if not ok:
            failed = full if full.exists() else src
            why_not = pictures.why_not(failed) if failed.is_file() else None    # None on a Mac: nothing new is said
            if why_not:
                say(f"(could not make the reel cover from {src.name}) {why_not}")
        made["covers"] = [full.name, grid.name] if ok else []
    # Sizing takes a while, and the page's own job may have written the record meanwhile (a new carousel
    # order, its slides). So the record is read afresh for the save, and only what this run made goes in:
    # the copy read at the start is never put back over anything.
    def note(r):
        r["made_pieces"] = {**r.get("made_pieces", {}), **made}
        r["built"] = datetime.now().isoformat(timespec="seconds")

    rec = update_rec(kit, note)
    lines = {k: f"{k.capitalize()}: {len(fs)} made." for k, fs in made.items()}
    if car is not None:
        if car["state"] == "problem":
            lines["carousel"] = carousel_trouble(car)
        else:
            lines["carousel"] = f"Carousel: {car['count']} made." + (
                f" ({car['aside']} earlier slide{'s' if car['aside'] != 1 else ''} set aside in the kit's hidden folder, not deleted.)" if car.get("aside") else "")
    for k in ("singles", "carousel", "stories", "covers"):
        if k in lines:
            say(lines[k])
    if picks.get("reel"):
        if this_computer.WINDOWS:
            # A PC only (unproven on a real PC): every value quoted so the line works as it is in PowerShell (which
            # cuts a bare comma list into pieces) or in Git Bash, and paths with forward slashes, which every PC
            # takes (parts/on-a-pc.md). A Mac's line, below, is exactly as it always was.
            vals = [Path(photos_dir(kit, rec)).as_posix(), rec.get("name")]
            if rec.get("night"):
                vals += [Path(rec["night"]).as_posix(), rec["shoot_id"]]
            # --shoot only with a name: Windows PowerShell 5.1 drops an empty "" when it starts a program, which
            # would leave --shoot with nothing after it (reel.py treats no --shoot and an empty one the same)
            say("Reel: run reel.py make with these picks: " + _pc_arg(reel_picks_text(rec))
                + f" --folder {_pc_arg(vals[0])}" + (f" --shoot {_pc_arg(vals[1])}" if vals[1] else "")
                + (f" --night {_pc_arg(vals[2])} --shoot-id {_pc_arg(vals[3])}" if rec.get("night") else "")
                + (" (one of these has an apostrophe and also a $, a backtick, a backslash or a quote mark in it, so "
                   "it is written here the PowerShell way; in Git Bash, quote it as on a Mac: parts/on-a-pc.md)"
                   if any(_pc_both_ways(v) for v in vals) else ""))
        else:
            say("Reel: run reel.py make with these picks: " + reel_picks_text(rec) + f" --folder \"{photos_dir(kit, rec)}\" --shoot \"{rec.get('name')}\""
                + (f" --night \"{rec['night']}\" --shoot-id {rec['shoot_id']}" if rec.get("night") else ""))
    write_page(kit)
    return 0


def note_reel(kit, project_name, picks=None, picks_text=None):
    """The kit's record of its reel. picks_text: the order the reel was made in, as reel.py read it ("19,4,10+"),
    when it isn't Claude's pick (the reel page passes the order on the page)."""
    rec = load_rec(kit)
    if picks_text:
        picks = parse_reel(picks_text)[0]
    rec["reel"] = {"project": project_name, "picks": picks or rec.get("picks", {}).get("reel", []), "made": datetime.now().isoformat(timespec="seconds")}
    if picks_text:
        rec["reel"]["picks_text"] = picks_text
    elif not picks:
        rec["reel"]["picks_text"] = reel_picks_text(rec)      # the same picks with Longer (+) and Quicker (-) in place
    save_rec(kit, rec)
    _write_text_whole(own_file(kit, "Reel.txt"), f"The reel for this shoot is the CapCut project \"{project_name}\".\nOpen CapCut, style it the way you like, and export it from there.\n"
                      + ("Photos in it, in order: " + ", ".join(str(n) for n in rec["reel"]["picks"]) + "\n" if rec["reel"]["picks"] else ""))
    write_page(kit)


# ---------- the words ----------

def voice():
    return studio_file.load().get("voice", {})


def set_voice(sample=None, never=None, audience=None, hashtags=None):
    sf = studio_file.load()
    v = sf.setdefault("voice", {})
    if sample is not None:
        v["samples"] = [s.strip() for s in re.split(r"\n\s*\n", sample.strip()) if s.strip()]
    if never is not None:
        v["never"] = [s.strip() for s in re.split(r"\n\s*\n", never.strip()) if s.strip()]
    if audience:
        v["audience"] = audience
    if hashtags is not None:
        v["hashtags"] = hashtags.strip()
    sf["voice"] = v
    studio_file.save(sf)
    return v


def told_text(kit):
    """What they have said about this shoot so far ("" when nothing). An empty told.json counts as nothing said:
    that is what an earlier version left when a write failed part way (an emoji in an old code page)."""
    p = kit / ".kit" / "told.json"
    if not p.exists():
        return ""
    raw = p.read_text(encoding="utf-8")
    return json.loads(raw).get("text", "") if raw.strip() else ""


def told(kit, text):
    p = kit / ".kit" / "told.json"
    old = told_text(kit)
    t = (old + "\n" + text.strip()).strip() if old else text.strip()
    _write_whole(p, {"text": t, "at": datetime.now().isoformat(timespec="seconds")})   # whole or not at all, UTF-8


def time_words(times):
    if not times:
        return ""
    hs = [int(t[11:13]) for t in times]
    mid = sum(hs) / len(hs)
    return "in the morning" if mid < 11 else "around midday" if mid < 14 else "in the afternoon" if mid < 17 else "in the evening"


def facts(kit):
    rec = load_rec(kit)
    folder = photos_dir(kit, rec)
    files = photo_files(folder)
    exifs = [exif_read.read(f) or {} for f in files[:120]]
    times = sorted(e["taken"] for e in exifs if e.get("taken"))
    lenses = sorted({e["lens"] for e in exifs if e.get("lens")})
    cams = sorted({e["camera"] for e in exifs if e.get("camera")})
    out = {
        "name": rec.get("name"), "folder": kit.name, "date": rec.get("date"), "photos": len(files),
        "day": this_computer.strftime(datetime.fromisoformat(times[0]), "%A, %B %-d, %Y") if times else "",
        "time_of_day": time_words(times), "span_minutes": round((datetime.fromisoformat(times[-1]) - datetime.fromisoformat(times[0])).total_seconds() / 60) if len(times) > 1 else 0,
        "lenses": lenses, "cameras": cams,
        "they_said": told_text(kit),
        "picks": rec.get("picks", {}), "numbered_list": str(kit / ".kit" / "sheet.json"),
        "voice": voice(), "client_note_voice": studio_file.load().get("note", {}),
        "existing_words": bool((kit / ".kit" / "words.json").exists()),
    }
    if rec.get("night") and rec.get("shoot_id"):
        try:
            import client_note
            cf = client_note.facts(rec["night"], rec["shoot_id"]) or {}
            out["from_the_backup"] = {k: cf.get(k) for k in ("recap", "they_said", "sneak_peeks", "to", "due_words")}
        except Exception as e:  # the backup's records may be on an unplugged drive
            out["from_the_backup"] = f"(not readable: {e})"
    return out


WORD_SHAPES = {"hooks": "lines", "stories": "lines", "caption": "text", "short": "text", "hashtags": "text", "leaned_on": "text"}


def kept_words(words, strict=True):
    """A kit's words in the shapes the captions file and the kit page read: hooks and stories as lists of lines;
    caption, short, hashtags and leaned_on as text. Words already in those shapes come back exactly as they were.
    The near misses are put right rather than left to stop every later page: hashtags handed over as a list
    become one line with a space between them, a caption written as a list of paragraphs is joined with a blank
    line between, a single hook or story line given as text becomes a list of one, and "nothing" (null) becomes
    empty. Anything else (a number, a list inside a list) raises ValueError in plain words when strict (saving:
    nothing is written then), and is read as empty when not (showing a page from a file already saved)."""
    if not isinstance(words, dict):
        if strict:
            raise ValueError("the words file should hold one set of named pieces (hooks, caption, short, stories, hashtags)")
        return {}
    out = dict(words)
    for k, kind in WORD_SHAPES.items():
        if k not in out:
            continue
        v = out[k]
        if kind == "lines":
            if v is None:
                v = []
            elif isinstance(v, str):
                v = [v] if v.strip() else []
            ok = isinstance(v, list) and all(isinstance(x, str) for x in v)
        else:
            if v is None:
                v = ""
            elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                v = (" " if k == "hashtags" else "\n\n").join(x.strip() for x in v if x.strip())
            ok = isinstance(v, str)
        if not ok:
            if strict:
                raise ValueError(f"\"{k}\" in the words file should be " + ("a list of lines" if kind == "lines" else "text"))
            v = [] if kind == "lines" else ""
        out[k] = v
    return out


def save_words(kit, words):
    words = kept_words(words)           # before anything is written: a wrong shape stops here, with nothing saved
    for k in ("hooks", "caption", "short", "stories"):
        words.setdefault(k, [] if k in ("hooks", "stories") else "")
    words["written"] = datetime.now().isoformat(timespec="seconds")
    _write_whole(kit / ".kit" / "words.json", words)       # whole or not at all, UTF-8
    lines = ["HOOKS (pick one, or write your own)", ""]
    lines += [f"{i}. {h}" for i, h in enumerate(words["hooks"], 1)]
    lines += ["", "CAPTION", "", words["caption"].strip(), ""]
    if words.get("short"):
        lines += ["SHORT CAPTION", "", words["short"].strip(), ""]
    if words.get("stories"):
        lines += ["STORY LINES", ""] + [f"- {s}" for s in words["stories"]] + [""]
    if words.get("hashtags"):
        lines += ["HASHTAGS", "", words["hashtags"].strip(), ""]
    if words.get("leaned_on"):
        lines += ["", f"Written from: {words['leaned_on']}"]
    _write_text_whole(own_file(kit, "Captions and hooks.txt"), "\n".join(lines) + "\n")
    write_page(kit)


# ---------- the page ----------

CSS = """
:root{--cream:#FAFAF6;--paper:#FFFFFF;--ink:#1F2430;--ink-2:#646B78;--coral:#F07F5A;--coral-2:#D4643F;--coral-l:#FCE6DD;--sand-l:#ECEAF6;--line:rgba(31,36,48,.12);
--display:'Fraunces',Georgia,serif;--sans:'DM Sans','Helvetica Neue','Segoe UI',Arial,sans-serif;--ease:cubic-bezier(.2,.7,.2,1)}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:400 16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 clamp(16px,4vw,40px) 4rem}
.bar{display:flex;align-items:center;gap:1rem;min-height:64px;border-bottom:1px solid var(--line)}
.brand b{font:600 16px/1 var(--sans)}.brand small{display:block;margin-top:4px;font:600 10px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
.bar .when{margin-left:auto;font:500 13px/1 var(--sans);color:var(--ink-2)}
.bar .homelink{display:inline-flex;align-items:center;gap:.45em;margin-right:.25rem;font:600 13.5px/1 var(--sans);color:#fff;background:var(--ink);text-decoration:none;padding:10px 16px 10px 13px;border-radius:999px;white-space:nowrap;transition:background .2s}.bar .homelink:hover{background:var(--coral-2)}.bar .homelink .short{display:none}@media(max-width:560px){.bar .homelink .long{display:none}.bar .homelink .short{display:inline}}
body:not(.live) .homelink{display:none}
.head{padding:clamp(2rem,5vw,3.4rem) 0 1rem;display:grid;gap:.6rem}
.eyebrow{font:600 11px/1.3 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--coral-2)}
h1{margin:0;font:600 clamp(32px,4.6vw,54px)/1.03 var(--sans);letter-spacing:-.035em;text-wrap:balance}
h1 em{font:italic 400 1.1em/1 var(--display);color:var(--coral-2);letter-spacing:0}
.lede{margin:0;color:var(--ink-2);font-size:clamp(16px,1.4vw,18px);max-width:40em}
.piece{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:1.4rem;align-items:start;background:var(--paper);border-radius:22px;padding:1.3rem;margin-top:1.2rem;box-shadow:0 1px 0 var(--line)}
.piece h2{margin:0 0 .2rem;font:600 24px/1.1 var(--sans);letter-spacing:-.02em}
.piece .sub{color:var(--ink-2);font-size:14px;margin:0 0 .8rem}
.strip{display:flex;gap:6px;flex-wrap:wrap}.strip img{height:150px;width:auto;border-radius:10px;object-fit:cover;background:var(--sand-l);box-shadow:0 0 0 1px var(--line);cursor:zoom-in;transition:transform .3s var(--ease)}.strip img:hover{transform:translateY(-2px)}
.strip.tall img{height:210px}
.words{display:grid;gap:.8rem}
.w{border:1px solid var(--line);border-radius:14px;padding:.8rem .95rem;position:relative}
.w .k{font:600 10px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--coral-2);margin-bottom:.4rem}
.w p{margin:0;white-space:pre-wrap;font-size:15px}
.w.hook p{font:italic 400 19px/1.3 var(--display)}
.copy{position:absolute;top:.6rem;right:.6rem;border:0;border-radius:999px;padding:.4rem .8rem;font:600 12px/1 var(--sans);background:var(--ink);color:#fff;cursor:pointer;transition:transform .2s var(--ease)}
.copy:hover{transform:scale(1.04)}.copy.done{background:var(--coral)}
.empty{font:italic 400 16px/1.3 var(--display);color:var(--ink-2)}
.lean{font-size:13px;color:var(--ink-2);margin-top:1rem}
.folder{font-size:13px;color:var(--ink-2)}
.go{display:inline-flex;align-items:center;gap:.4rem;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:.5rem .95rem;font:600 13.5px/1 var(--sans);cursor:pointer;transition:all .2s var(--ease)}
.go:hover{border-color:var(--coral);color:var(--coral-2);transform:translateY(-1px)}
a.go{text-decoration:none}
.go.small{padding:.35rem .7rem;font-size:12.5px}.canva-links{display:flex;flex-wrap:wrap;gap:.4rem;margin:.6rem 0 0}
.go.main{background:var(--ink);color:#fff;border-color:var(--ink)}.go.main:hover{background:var(--coral-2);border-color:var(--coral-2);color:#fff}
.went{font-size:13px;color:var(--ink-2);min-height:1.2em;margin:.4rem 0 0}
.piece .top{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.5rem}
.piece .top h2{margin:0}
.ratio{font:600 10px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);border:1px solid var(--line);border-radius:999px;padding:.3em .6em;margin-left:.5rem;vertical-align:middle}
.arr{display:inline-flex;align-items:center;gap:.4rem;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:.5rem .95rem;font:600 13.5px/1 var(--sans);text-decoration:none;cursor:pointer;transition:all .2s var(--ease)}
.arr:hover{border-color:var(--coral);color:var(--coral-2);transform:translateY(-1px)}
body:not(.live) .arr{display:none}
.big{position:fixed;inset:0;background:rgba(20,22,30,.92);display:none;place-items:center;z-index:50;cursor:zoom-out}.big.on{display:grid}.big img{max-width:92vw;max-height:92vh;border-radius:12px}
@media(max-width:760px){.piece{grid-template-columns:1fr}}
"""

SCRIPT = """
document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{const t=b.parentElement.querySelector('p').textContent;
 try{await navigator.clipboard.writeText(t)}catch(e){const r=document.createRange();r.selectNodeContents(b.parentElement.querySelector('p'));const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy')}
 b.textContent='Copied';b.classList.add('done');setTimeout(()=>{b.textContent='Copy';b.classList.remove('done')},1600)});
const live=location.protocol.startsWith('http');if(live)document.body.classList.add('live');const KIT=document.body.dataset.kit;
document.querySelectorAll('.go').forEach(b=>b.onclick=async()=>{const line=b.closest('.piece,header').querySelector('.went');
 if(!live){line.textContent='This is a saved copy. Say “show the '+document.body.dataset.name+' kit” to Claude and the buttons work.';return}
 line.textContent='Opening...';
 try{const r=await fetch('/open?kit='+encodeURIComponent(KIT)+'&sub='+encodeURIComponent(b.dataset.sub||''));const j=await r.json();line.textContent=j.words}
 catch(e){line.textContent='Could not reach the Assistant. Tell Claude instead.'}});
const big=document.getElementById('big');document.querySelectorAll('.strip img').forEach(i=>i.onclick=()=>{big.querySelector('img').src=i.src;big.classList.add('on')});big.onclick=()=>big.classList.remove('on');
"""


LAY_OUT = "Lay out the slides"
LAY_OUT_TITLE = "Put photos side by side, add your own words and colors, and save the finished slides."


def _src(name):
    """A file's name as it goes into a picture's address on the kit page. Only the three characters that
    would cut an address short are changed, so every address written before reads the same."""
    return name.replace("%", "%25").replace("#", "%23").replace("?", "%3F")


def carousel_line(shown, canva):
    """The line under the Carousel heading on the kit page: which slides the page is showing, said truly."""
    if shown["kind"] == "laid-out":
        return (f"The slides you laid out, saved as \u201c{shown['base']}\u201d. They are in the Carousel folder"
                + (", and the other slides in that folder are all still there." if shown["others"] else "."))
    line = ("Made in Canva from your template; the plain slides are there too." if canva
            else "The slides, in order, all the same size. They are in the Carousel folder.")
    if shown["laid_out"]:
        line += " The slides you laid out are in that folder too."
    return line


def rel(kit, p):
    return html.escape(Path(p).relative_to(kit).as_posix()) if str(p).startswith(str(kit)) else html.escape(str(p))


def write_page(kit):
    rec = load_rec(kit)
    words = json.loads((kit / ".kit" / "words.json").read_text(encoding="utf-8")) if (kit / ".kit" / "words.json").exists() else {}
    words = kept_words(words, strict=False)     # a words file saved in a near-miss shape never stops the page
    name = rec.get("name", kit.name)
    when = rec.get("date") or ""
    try:
        when_words = this_computer.strftime(date.fromisoformat(when), "%B %-d, %Y")
    except ValueError:
        when_words = when
    made = rec.get("made_pieces", {})

    def strip(folder_name, tall=False, fs=None):
        d = kit / folder_name
        if not d.is_dir():
            return "<p class='empty'>Not made yet.</p>"
        if fs is None:
            fs = sorted((p for p in d.iterdir() if p.suffix.lower() == ".jpg" and not p.name.startswith(".")), key=lambda p: ("(Canva)" not in p.name, p.name))
        if not fs:
            return "<p class='empty'>Not made yet.</p>"
        return f"<div class='strip{' tall' if tall else ''}'>" + "".join(f"<img src='{html.escape(folder_name)}/{html.escape(_src(f.name))}' alt=''>" for f in fs) + "</div>"

    def wbox(k, text, cls=""):
        return f"<div class='w {cls}'><div class='k'>{html.escape(k)}</div><p>{html.escape(text)}</p><button class='copy'>Copy</button></div>"

    hooks = "".join(wbox(f"Hook {i}", h, "hook") for i, h in enumerate(words.get("hooks", []), 1)) or "<p class='empty'>Not written yet.</p>"
    caption = wbox("Caption", words["caption"]) if words.get("caption") else ""
    short = wbox("Short caption", words["short"]) if words.get("short") else ""
    tags = wbox("Hashtags", words["hashtags"]) if words.get("hashtags") else ""
    story_lines = "".join(wbox(f"Story {i}", s) for i, s in enumerate(words.get("stories", []), 1))
    reel = rec.get("reel")
    reel_html = (f"<p>Your reel is in CapCut, called <b>{html.escape(reel['project'])}</b>. Press Open in CapCut, click that project, style it the way you like, and export it from there.</p>"
                 + (f"<p class='sub'>Photos in it, in order: {', '.join(str(n) for n in reel.get('picks', []))}</p>" if reel.get("picks") else "")) if reel else "<p class='empty'>Not made yet. Say “make the reel” to Claude.</p>"
    lean = f"<p class='lean'>Written from: {html.escape(words['leaned_on'])}</p>" if words.get("leaned_on") else ""

    canva = rec.get("canva", {})
    can_arrange = (kit / ".kit" / "sheet.json").is_file()      # the page that moves photos needs the numbered list
    shown = carousel_shown(kit, rec)                            # which slides are the carousel today

    def sec(title, sub, ratio, body, wrds, folder, piece=None, arrange=None):
        has = (kit / folder).is_dir()
        btn = f"<button class='go' data-sub='{html.escape(folder)}'>Open the {html.escape(folder)} folder</button>" if has else ""
        if arrange == "carousel" and can_arrange:
            # The page where they lay the slides out themselves (design.py): a plain link of class 'arr' too,
            # never 'go'. It is put in first, so it sits after "Change the photos" and before the folder's button.
            btn = (f"<a class='arr' href='/design.html?kit={html.escape(quote(kit.name))}' title='{html.escape(LAY_OUT_TITLE, quote=True)}'>{html.escape(LAY_OUT)}</a> " + btn)
        if arrange and can_arrange and (rec.get("picks") or {}).get(arrange):
            # A plain link to the page where they move the photos themselves. Its class is 'arr', never 'go':
            # every 'go' button asks the Assistant to open a folder in Finder (File Explorer on a PC). Shown only when the page is
            # served live (a saved copy has nowhere to go).
            btn = (f"<a class='arr' href='/arrange.html?kit={html.escape(quote(kit.name))}&amp;piece={arrange}'>Change the photos</a> " + btn)
        cv = canva.get(piece) if piece else None
        if cv and cv.get("edit_url"):
            btn = f"<a class='go' href='{html.escape(cv['edit_url'])}' target='_blank' rel='noopener'>Open in Canva</a> " + btn
        if piece == "cover" and reel:
            # The reel lives in CapCut, so the button opens CapCut (Dustin, Oct 30). CapCut can't be told which
            # project to open from outside, so the line beside the button names it; it's at the top of the list.
            btn = "<button class='go main' data-sub='CapCut'>Open in CapCut</button> " + btn
        return (f"<section class='piece'><div><div class='top'><h2>{html.escape(title)}<span class='ratio'>{ratio}</span></h2><span>{btn}</span></div>"
                f"<p class='went'></p><p class='sub'>{html.escape(sub)}</p>{body}</div><div class='words'>{wrds}</div></section>")

    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(brand.title(name + ' · Post kit'))}</title><link rel='stylesheet' href='{FONTS}'><style>{CSS}</style></head><body data-kit='{html.escape(kit.name)}' data-name='{html.escape(name)}'>"
            f"<div class='wrap'><div class='bar'><a class='homelink' href='/home'><span aria-hidden='true'>&larr;</span><span class='long'>Back to home</span><span class='short'>Home</span></a>{brand.bar()}"
            f"<span class='when'>{html.escape(when_words)}</span></div>"
            f"<header class='head'><span class='eyebrow'>Post kit</span><h1>{html.escape(name)}<em>.</em></h1>"
            f"<p class='lede'>Everything you need to post this shoot, in one place. Copy the captions, grab the photos from the folders, and post when you're ready. Nothing gets posted for you.</p>"
            f"<p class='folder'>In your {html.escape(brand.short())} folder: {html.escape(posts.CONTENT_NAME)} › {html.escape(kit.name)}</p>"
            f"<p><button class='go main' data-sub=''>Open the kit folder</button> <button class='go' data-sub='Photos'>Open the Photos folder</button></p><p class='went'></p></header>"
            + sec("Reel", ("Cut on the beat, in CapCut. The cover was made in Canva from your template." if canva.get("cover") else "Cut on the beat, in CapCut. The cover is in the Covers folder."), "9:16", reel_html + strip("Covers", tall=True), hooks, "Covers", "cover", arrange="reel")
            + sec("Carousel", carousel_line(shown, bool(canva.get("carousel"))), "4:5", strip("Carousel", fs=shown["files"]), caption + tags, "Carousel", "carousel", arrange="carousel")
            + sec("Single posts", "Single photos sized for Instagram, in the Singles folder. On your profile grid Instagram shows only the middle of each one, so keep faces near the middle.", "4:5", strip("Singles"), short or caption or "", "Singles")
            + sec("Stories", ("Made in Canva from your template, with your words on them; the plain ones are there too." if canva.get("stories") else "Photos sized for stories, in the Stories folder. Instagram puts its own buttons over the top and bottom, so the photo sits in the middle."), "9:16",
                  strip("Stories", tall=True) + ("<p class='canva-links'>" + " ".join(f"<a class='go small' href='{html.escape(d['edit_url'])}' target='_blank' rel='noopener'>Story {int(n)} in Canva</a>" for n, d in sorted((canva.get("stories") or {}).items(), key=lambda x: int(x[0])) if d.get("edit_url")) + "</p>" if canva.get("stories") else ""),
                  story_lines or "<p class=empty>Not written yet.</p>", "Stories")
            + f"{lean}</div><div class='big' id='big'><img alt=''></div>"
            f"<script>{SCRIPT}</script></body></html>")
    tidy_own_files(kit)
    _write_text_whole(page_path(kit), page)     # whole or not at all, UTF-8 (the page says charset utf-8)
    return page_path(kit)


def show(kit):
    rec = load_rec(kit)
    say(f"{rec.get('name', kit.name)}  ({kit})")
    say(f"  Photos: {len(photo_files(photos_dir(kit, rec)))}" + (f" at {rec['photos_dir']}" if rec.get("photos_dir") else ""))
    p = rec.get("picks", {})
    if p:
        say("  Picks: " + ", ".join(f"{k} {len(v)}" for k, v in p.items() if v))
    for k, v in rec.get("made_pieces", {}).items():
        say(f"  {k.capitalize()}: {len(v)} made")
    if rec.get("reel"):
        say(f"  Reel: CapCut project \"{rec['reel']['project']}\"")
    say("  Words: " + ("written" if (kit / ".kit" / "words.json").exists() else "not yet"))
    say(f"  Page: {page_path(kit)}" if page_path(kit).exists() else "  Page: not yet")


def read_their_file(path):
    """A file Claude wrote for a command (their words, a caption list): UTF-8, with or without the mark some PC
    editors put at the start ("-sig")."""
    return Path(path).read_text(encoding="utf-8-sig")


def main():
    this_computer.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start"); st.add_argument("words", nargs="?"); st.add_argument("--night"); st.add_argument("--shoot"); st.add_argument("--folder"); st.add_argument("--name")
    t = sub.add_parser("told"); t.add_argument("words")
    tt = t.add_mutually_exclusive_group(required=True)
    tt.add_argument("--text", help="what they said, word for word")
    tt.add_argument("--text-file", help="the same, read from a UTF-8 text file (so on a PC it never passes through "
                                        "the command line, which can change quotes and $)")
    sub.add_parser("sheet").add_argument("words")
    pk = sub.add_parser("picks"); pk.add_argument("words")
    for k in ("singles", "stories", "carousel", "reel", "cover"):
        pk.add_argument(f"--{k}")
    sub.add_parser("build").add_argument("words")
    rl = sub.add_parser("reel-made"); rl.add_argument("words"); rl.add_argument("--project", required=True)
    rl.add_argument("--picks", help="the order it was made in, as reel.py read it (19,4,10+,14-), when not Claude's pick")
    sub.add_parser("facts").add_argument("words")
    w = sub.add_parser("words"); w.add_argument("words"); w.add_argument("--file", required=True)
    sub.add_parser("page").add_argument("words")
    sub.add_parser("show").add_argument("words")
    v = sub.add_parser("voice"); v.add_argument("--sample-file"); v.add_argument("--never-file"); v.add_argument("--audience", choices=["clients", "photographers", "both"]); v.add_argument("--hashtags")
    a = ap.parse_args()

    if a.cmd == "voice":
        sample = read_their_file(a.sample_file) if a.sample_file else None
        never = read_their_file(a.never_file) if a.never_file else None
        vv = set_voice(sample, never, a.audience, a.hashtags)
        say(f"Voice: {len(vv.get('samples', []))} captions of theirs, {len(vv.get('never', []))} they'd never write, for {vv.get('audience', 'both')}"
            + (f", hashtags kept" if vv.get("hashtags") else "") + ".")
        return 0
    if a.cmd == "start":
        if a.night:
            if not a.shoot:
                say("STOP: --night needs --shoot s1.")
                return 1
            kit = start_from_night(a.night, a.shoot)
        elif a.folder:
            kit = start_from_folder(a.folder, a.name)
        elif a.words:
            kit = find_kit(a.words)
            rec = load_rec(kit)
            if not rec.get("photos"):
                rec["photos"] = [f.name for f in photo_files(photos_dir(kit, rec))]
                save_rec(kit, rec)
        else:
            say("STOP: say which shoot (a few words, --night/--shoot, or --folder).")
            return 1
        rec = load_rec(kit)
        say(f"Kit: {kit}")
        say(f"{len(rec.get('photos', []))} photos" + (f" at {rec['photos_dir']}" if rec.get("photos_dir") else "") + ". Next: the question, then kit.py sheet.")
        return 0
    kit = find_kit(a.words)
    if a.cmd == "told":
        said = a.text
        if a.text_file:
            try:
                said = read_their_file(a.text_file)
            except (OSError, UnicodeDecodeError) as e:
                say(f"STOP: I couldn't read {a.text_file} ({e.__class__.__name__}). Nothing kept.")
                return 1
        told(kit, said); say("Kept. It'll shape the captions."); return 0
    if a.cmd == "sheet":
        return sheet(kit)
    if a.cmd == "picks":
        p = set_picks(kit, a.singles, a.stories, a.carousel, a.reel, a.cover)
        say("Picks: " + ", ".join(f"{k} {len(v)}" for k, v in p.items() if v)); return 0
    if a.cmd == "build":
        return build(kit)
    if a.cmd == "reel-made":
        if a.picks and not re.fullmatch(r"\d+[+-]?(,\d+[+-]?)*", a.picks.replace(" ", "")):
            say("STOP: --picks is the photo numbers in order, like 19,4,10+,14-. Nothing was noted."); return 2
        note_reel(kit, a.project, picks_text=(a.picks or "").replace(" ", "") or None); say("Noted. The reel is on the kit page."); return 0
    if a.cmd == "facts":
        say(json.dumps(facts(kit), indent=1, ensure_ascii=False)); return 0
    if a.cmd == "words":
        try:
            given = json.loads(read_their_file(a.file))
        except ValueError as e:
            say(f"STOP: the words file isn't JSON that can be read ({e}). Nothing was saved. Fix the file and run this again.")
            return 1
        try:
            given = kept_words(given)
        except ValueError as e:         # a piece in a shape the page can't show: said before anything is written
            say(f"STOP: {e}. Nothing was saved. Fix the file and run this again.")
            return 1
        save_words(kit, given)
        say(f"Saved. The captions and the kit page are updated: {page_path(kit)}"); return 0
    if a.cmd == "page":
        say(str(write_page(kit))); return 0
    if a.cmd == "show":
        show(kit); return 0


if __name__ == "__main__":
    sys.exit(main())
