#!/usr/bin/env python3
"""The Studio by Horizon Found. Writes a reel plan into a new CapCut project, so the
photographer opens CapCut and finds it there: their photos on the beat of their song,
hard cuts, nothing added. The look (text styles, filters, templates) is theirs to
add in CapCut.

    python3 capcut.py where                     where CapCut keeps projects, and whether it is open
    python3 capcut.py songs                     songs from CapCut's own music used in their projects
    python3 capcut.py open                      start CapCut (their newest project is at the top of its list);
                                                first adds any reel still waiting to CapCut's list
    python3 capcut.py write --plan reel.json    make the project
        [--store <projects folder>]             somewhere else (tests)
        [--ignore-open]                         tests only: treat CapCut as closed

On a PC (unproven: nobody here has seen a CapCut project made on Windows; docs/pc-readiness-2026-11-06.md,
rows I1 to I7): the projects are looked for in %LOCALAPPDATA%\\CapCut\\User Data\\Projects\\com.lveditor.draft,
the project file is called draft_content.json instead of draft_info.json, every path inside it is written
with forward slashes (C:/Users/...), and "is CapCut open" asks Windows' tasklist for CapCut.exe. All of
that comes from community notes, never from CapCut itself. If CapCut for Windows locks its project files,
this route cannot work there as built. Only CapCut on a Mac has been seen adding a new project folder to its
list by itself while open, so on a PC a reel made with CapCut open waits and is added to the list the next
time CapCut is closed (the next reel, or `capcut.py open`). Text gets CapCut for Windows' own default font
file when it can be found, else no font path (the template's is the Mac app's).

The plan (reel.py writes it):
    {"name": "Black-sand beach reel",
     "photos": [{"path": "/…/x.jpg", "start": 0.0, "dur": 2.4}, …],      seconds on the reel
                a video clip from their footage is a piece too, with "clip": true, "src" (where in the video it
                starts) and "length" (the whole video's): it goes in as a real video, muted under a song and
                with its own sound when there is no song
     "song": {"path": "/…/song.m4a", "from": 41.3, "dur": 13.2, "fade_out": 0.6} or null,
     "hook": {"text": "…", "dur": 2.4} or null}

A talking reel (talking_make.py writes its plan; Nicole's v23 and v24) is made by a second builder in this file,
build_talking, through the same write(): write(plan, store, builder=build_talking). Its plan is described above
that function. A photo reel's project is exactly what it was before that builder went in
(tests/capcut_even.py keeps the proof).

How: every CapCut project is a folder of plain files. This builds one from pieces
CapCut itself wrote (references/capcut/), never edits a project they made, and
never overwrites a folder. If CapCut is open, it only writes the new project's
folder and CapCut picks it up by itself; if CapCut is closed, it also adds the
project to CapCut's list of projects, after keeping a copy of that list.

Exit codes: 0 made · 2 stop (no CapCut found, a photo or the song missing).
"""
import argparse
import copy
import errno
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "studio-manager" / "scripts"))
import pictures  # noqa: E402  (small pictures and a photo's size, on a Mac or a PC)
import sound  # noqa: E402  (a song's length, on a Mac or a PC)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import talking  # noqa: E402  (a talking reel's arithmetic: how much and how fast a zoom moves, and its one curve)
this_computer.utf8_output()

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "references" / "capcut"
US = 1_000_000
CANVAS = (1080, 1920)
PHOTO_LENGTH = 10_800_000_000   # CapCut gives a still photo three hours of "length" to cut from
QUIT = "close" if this_computer.WINDOWS else "quit"     # what you do to CapCut to make it stop, in their words


def say(msg):
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        pass
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe, and the work goes on, as it does on a Mac. A Mac raises anything else, as before.
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):   # unproven on a real PC
            raise


def uid():
    return str(uuid.uuid4()).upper()


def now_us():
    return int(time.time() * US)


# ---------------------------------------------------------------- where CapCut lives

def default_store():
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    if os.name == "nt":
        # unproven on a real PC: the default place, per community notes [K27]. CapCut's settings may let them
        # move it; if so, `capcut.py where` says "found": false and --store points at the right one.
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return Path.home() / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def capcut_open():
    """True if CapCut is running, False if not, None if we cannot tell."""
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True, encoding="utf-8", errors="replace")  # pc-ok: Mac branch
            return r.returncode == 0
        if os.name == "nt":
            # unproven on a real PC: CapCut's program is believed to be called CapCut.exe (community notes, not
            # seen). tasklist prints in the PC's own code page; the name looked for is plain letters, so any
            # reading of it finds it. CSV with no header: one quoted line per matching program.
            r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/FO", "CSV", "/NH"],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=20,
                               creationflags=0x08000000)            # CREATE_NO_WINDOW
            if r.returncode != 0:
                return None
            return '"capcut.exe"' in (r.stdout or "").lower()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _windows_capcut_programs():
    """Where CapCut's program might be on a PC, likeliest first. Unproven: from community notes, not seen.
    CapCut installs for one person under %LOCALAPPDATA%\\CapCut\\Apps, with a launcher at the top and one
    folder per version; the Start menu has a shortcut."""
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    apps = local / "CapCut" / "Apps"
    out = [apps / "CapCut.exe"]

    def version(p):
        return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", p.parent.name)]
    try:
        out += sorted(apps.glob("*/CapCut.exe"), key=version, reverse=True)
    except OSError:
        pass
    roaming = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    menu = roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    out += [menu / "CapCut" / "CapCut.lnk", menu / "CapCut.lnk"]
    for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if pf:
            out.append(Path(pf) / "CapCut" / "CapCut.exe")
    return out


def launch():
    """Start CapCut. (True, "") or (False, why in plain words). It cannot be told which project to open;
    the newest is at the top of its list. Afterwards launch.slow is True when the Mac's `open` was still
    waiting after 20 seconds: CapCut was there and asked to start, and may yet appear (the first start of a
    newly downloaded CapCut, while the Mac checks it), so the words for that are "taking a while", not "not
    installed"; and launch.missing is True when no CapCut was found to start (the Mac's `open` didn't know it,
    or none was where a PC's CapCut installs itself), so a caller needn't read the words to tell."""
    launch.slow = launch.missing = False
    try:
        if sys.platform == "darwin":
            # open answers within a second; the 20-second limit (the posting page's own, before Nov 6) only keeps
            # a stuck one from holding the button for ever
            r = subprocess.run(["open", "-a", "CapCut"], capture_output=True, encoding="utf-8", errors="replace",  # pc-ok: Mac branch
                               timeout=20)
            if r.returncode == 0:
                return True, ""
            launch.missing = True
            return False, "CapCut isn't installed on this Mac"
        if os.name == "nt":
            for p in _windows_capcut_programs():            # unproven on a real PC
                if p.is_file():
                    os.startfile(str(p))                     # pc-ok: Windows branch; starts it like a double-click
                    return True, ""
            launch.missing = True
            return False, "I couldn't find CapCut on this PC. Open it from the Start menu"
    except subprocess.TimeoutExpired:
        # stopping `open` doesn't stop CapCut starting: it may still appear in a moment
        launch.slow = True
        return False, "CapCut didn't start within 20 seconds; it may still be starting"
    except OSError as e:
        return False, f"CapCut didn't start ({e})"
    return False, "I can't start CapCut on this computer"


launch.slow = launch.missing = False


def _windows_default_font():
    """The font CapCut on a PC puts on new text, as a path written CapCut's way, or "" (let CapCut choose).
    The text piece was taken from CapCut on a Mac and names the Mac app's own font file
    (/Applications/CapCut.app/.../SystemFont/en.ttf), which no PC has. Guessed, unproven: CapCut for Windows
    keeps the same file under its version folder (...\\CapCut\\Apps\\<version>\\Resources\\Font\\SystemFont\\en.ttf);
    if it isn't there, the path is left empty for CapCut to use its own default (readiness row I4)."""
    for prog in _windows_capcut_programs():
        if prog.suffix.lower() != ".exe":
            continue
        font = prog.parent / "Resources" / "Font" / "SystemFont" / "en.ttf"
        try:
            if font.is_file():
                return native(font)
        except OSError:
            pass
    return ""


def draft_file_name():
    # A PC's CapCut is believed to keep draft_content.json (community notes [K27]; one says newer versions keep
    # draft_info.json beside it). Unproven: whether a project with only this file opens there is not known.
    return "draft_content.json" if os.name == "nt" else "draft_info.json"


def _read_json(path):
    """CapCut's own JSON, or an error. utf-8-sig: the same as utf-8 for every file a Mac's CapCut writes, and
    it also takes a byte-order mark, which Windows programs sometimes put at the front."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def their_platform(store):
    """The CapCut version they have, read from their newest project, so ours matches it."""
    best = None
    for d in store.iterdir() if store.is_dir() else []:
        for name in ("draft_info.json", "draft_content.json"):
            f = d / name
            if f.is_file():
                try:
                    mt = f.stat().st_mtime
                    if not best or mt > best[0]:
                        best = (mt, f)
                except OSError:
                    pass
    if not best:
        return None
    try:
        d = _read_json(best[1])
        return {k: d[k] for k in ("platform", "last_modified_platform", "version", "new_version") if k in d}
    except (OSError, ValueError, AttributeError, TypeError):
        return None   # an unreadable project (a newer CapCut may lock its files) just means we use ours


def _project_drafts(store):
    """(modified time, project folder, draft json) for each project, newest first."""
    out = []
    for d in store.iterdir() if store.is_dir() else []:
        if not d.is_dir() or d.name.startswith("."):
            continue
        cands = [d / "draft_info.json", d / "draft_content.json"] + sorted((d / "Timelines").glob("*/draft_info.json"))
        files = [f for f in cands if f.is_file()]
        if files:
            f = max(files, key=lambda f: f.stat().st_mtime)
            out.append((f.stat().st_mtime, d, f))
    return sorted(out, reverse=True)


def capcut_songs(store):
    """Songs from CapCut's own music library used in their projects, newest project first, one per song.
    Each: name, seconds, path (in CapCut's cache), present (file still there), project, material, beats."""
    found, seen = [], set()
    for mt, folder, f in _project_drafts(store):
        try:
            d = _read_json(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        mats = d.get("materials", {})
        by_id = {x.get("id"): (k, x) for k, v in mats.items() if isinstance(v, list) for x in v if isinstance(x, dict)}
        for t in d.get("tracks", []):
            if t.get("type") != "audio":
                continue
            for seg in t.get("segments", []):
                k, m = by_id.get(seg.get("material_id"), (None, None))
                if k != "audios" or m.get("type") != "music" or not m.get("music_id"):
                    continue
                if m["music_id"] in seen:
                    continue
                seen.add(m["music_id"])
                beats = next((x for r in seg.get("extra_material_refs", [])
                              for kk, x in [by_id.get(r, (None, None))] if kk == "beats"), None)
                found.append({"name": m.get("name") or "Untitled", "seconds": (m.get("duration") or 0) / US,
                              "path": m.get("path", ""), "present": bool(m.get("path")) and Path(m["path"]).is_file(),
                              "project": d.get("name") or folder.name, "folder": folder.name,
                              "material": m, "beats": beats})
    return found


# ---------------------------------------------------------------- photos

def _jpeg_size(f):
    """(width, height, orientation) from a JPEG's own header, or None."""
    with open(f, "rb") as fh:
        if fh.read(2) != b"\xff\xd8":
            return None
        orient = 1
        while True:
            b = fh.read(1)
            while b and b != b"\xff":
                b = fh.read(1)
            while b == b"\xff":
                b = fh.read(1)
            if not b:
                return None
            marker = b[0]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            seg_len = struct.unpack(">H", fh.read(2))[0]
            data = fh.read(seg_len - 2)
            if marker == 0xE1 and data[:6] == b"Exif\x00\x00":
                orient = _exif_orientation(data[6:]) or 1
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[1:5])
                return w, h, orient
            if marker == 0xDA:
                return None


def _exif_orientation(t):
    try:
        e = "<" if t[:2] == b"II" else ">"
        off = struct.unpack(e + "I", t[4:8])[0]
        n = struct.unpack(e + "H", t[off:off + 2])[0]
        for i in range(n):
            p = off + 2 + 12 * i
            tag, typ, cnt = struct.unpack(e + "HHI", t[p:p + 8])
            if tag == 0x0112:
                return struct.unpack(e + "H", t[p + 8:p + 10])[0]
    except struct.error:
        return None
    return None


def photo_size(f):
    """Width and height as the photo is seen (turned the right way up), or (0, 0) if unknown."""
    f = str(f)
    try:
        if f.lower().endswith((".jpg", ".jpeg")):
            r = _jpeg_size(f)
            if r:
                w, h, o = r
                return (h, w) if o in (5, 6, 7, 8) else (w, h)
        if f.lower().endswith(".png"):
            with open(f, "rb") as fh:
                head = fh.read(24)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
    except OSError:
        pass
    # HEIC, TIFF and anything else: the Mac's own sips, as always; on a PC, Pillow (pictures.py), turned the
    # right way up. Without Pillow on a PC this is "unknown" and the photo is fitted, not filled.
    got = pictures.size_of(f)
    return (int(got[0]), int(got[1])) if got else (0, 0)


def cover_scale(w, h):
    """CapCut fits a picture (a photo or a video) inside the frame at scale 1. This is the scale that fills the
    frame instead. 1 for a size nobody could read."""
    if not w or not h:
        return 1.0
    cw, ch = CANVAS
    fit = min(cw / w, ch / h)
    fill = max(cw / w, ch / h)
    return round(fill / fit, 6)


fill_scale = cover_scale        # its name since October (reel.py and the photo reel's build() use it)


def song_length(path):
    """Length of the song in seconds: read from the file itself (sound.py, the same on a Mac and a PC, and the
    same number the Mac's own afinfo gives for WAV, AIFF, MP3 and Apple's M4A); then afinfo, ffprobe if
    present, or a wav header, for anything sound.py cannot read."""
    p = str(path)
    d = sound.duration(p)
    if d:
        return float(f"{d:f}")      # to the microsecond, written the way afinfo writes it, so records match a Mac's
    if shutil.which("afinfo"):  # pc-ok: only a Mac has afinfo; anything sound.py could not read
        try:
            r = subprocess.run(["afinfo", p], capture_output=True, encoding="utf-8", errors="replace", timeout=60)  # pc-ok: only a Mac has afinfo
        except subprocess.TimeoutExpired:
            r = None                # a length nobody can read in a minute is "unknown", never a wait without end
        m = re.search(r"estimated duration:\s*([\d.]+)", r.stdout) if r else None
        if m:
            return float(m.group(1))
    if shutil.which("ffprobe"):
        try:
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "default=nw=1:nk=1", p], capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            return float(r.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            pass
    if p.lower().endswith(".wav"):
        import wave
        try:
            with wave.open(p, "rb") as w:
                return w.getnframes() / w.getframerate()
        except (OSError, EOFError, wave.Error, ZeroDivisionError, RuntimeError, struct.error):
            pass                    # (Python 3.9's wave raises RuntimeError for a WAV with damaged chunk names)
    return 0.0


# ---------------------------------------------------------------- building it

def load_parts():
    t = json.loads((REF / "draft_info.template.json").read_text(encoding="utf-8"))
    m = json.loads((REF / "draft_meta_info.template.json").read_text(encoding="utf-8"))
    p = json.loads((REF / "parts.json").read_text(encoding="utf-8"))
    return t, m, p


def tr(start, dur):
    return {"start": int(round(start * US)), "duration": int(round(dur * US))}


def us_f(frames, fps=30.0):
    """A whole number of frames as CapCut writes it in microseconds (1 frame at 30 fps = 33333 or 33334)."""
    return int(round(frames * US / fps))


def tr_f(start_f, dur_f, fps=30.0):
    a, b = us_f(start_f, fps), us_f(start_f + dur_f, fps)
    return {"start": a, "duration": b - a}


def _start_draft(plan, parts, platform):
    """A new, empty project from CapCut's own pieces: (the draft, its id). Their CapCut's version is copied in
    when there is a project of theirs to read it from."""
    d = copy.deepcopy(parts[0])
    if platform:
        d.update(copy.deepcopy(platform))
    elif os.name == "nt":
        # unproven on a real PC: no project of theirs to copy from, and the pieces were taken from CapCut on a
        # Mac, so at least say which computer this is. CapCut for Windows' own values are not known yet.
        import platform as _platform
        for k in ("platform", "last_modified_platform"):
            if isinstance(d.get(k), dict):
                d[k] = dict(d[k], os="windows", os_version=_platform.version())
    draft_id = uid()
    d["id"] = draft_id
    d["name"] = plan["name"]
    d["canvas_config"] = {"background": None, "height": CANVAS[1], "ratio": "original", "width": CANVAS[0]}
    return d, draft_id


def _segment(P, mats, material_id, target, source, scale=1.0):
    """One clip on a picture track, with the six companions CapCut gives every clip (its speed item among them):
    where it sits on the reel (target), which part of its file it shows (source), and how big."""
    refs = []
    for ex in P["photo_extras"]:
        item = copy.deepcopy(ex["item"])
        item["id"] = uid()
        mats[ex["list"]].append(item)
        refs.append(item["id"])
    seg = copy.deepcopy(P["photo_segment"])
    seg.update({"id": uid(), "material_id": material_id, "extra_material_refs": refs,
                "target_timerange": target, "source_timerange": source})
    seg["clip"]["scale"] = {"x": scale, "y": scale}
    seg["uniform_scale"] = {"on": True, "value": 1.0}
    return seg


def _text(P, mats, text, target):
    """Plain CapCut text they restyle with CapCut's own text styles: its material goes in, its clip comes back."""
    tm = copy.deepcopy(P["text_material"])
    tm["id"] = uid()
    if os.name == "nt" and str(tm.get("font_path", "")).startswith("/Applications/"):
        tm["font_path"] = _windows_default_font()        # unproven on a real PC (row I4)
    content = json.loads(tm["content"])
    style = content["styles"][0]
    style["range"] = [0, len(text)]
    content["styles"] = [style]
    content["text"] = text
    tm["content"] = json.dumps(content, ensure_ascii=False)
    mats["texts"].append(tm)
    ts = copy.deepcopy(P["text_segment"])
    ts.update({"id": uid(), "material_id": tm["id"], "target_timerange": target})
    return ts


def _finish_meta(meta, draft_id, name, duration, meta_items):
    """The project's own description (draft_meta_info.json), with what was put in it listed the way CapCut lists it."""
    m = copy.deepcopy(meta)
    m["draft_id"] = draft_id
    m["draft_name"] = name
    m["tm_duration"] = duration
    first = next((x for x in m["draft_materials"] if x["type"] == 0), None)
    if first is not None:
        for it in meta_items:
            first["value"].append({
                "ai_group_type": "", "create_time": it["t"], "duration": it["duration"], "enter_from": 0,
                "extra_info": it["extra_info"], "file_Path": it["file_Path"], "height": it["height"],
                "id": str(uuid.uuid4()), "import_time": it["t"], "import_time_ms": it["t"] * US,
                "item_source": 1, "material_color_tag": "", "md5": "", "metetype": it["metetype"],
                "roughcut_time_range": {"duration": -1, "start": -1},
                "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": it["width"]})
    return m


def build(plan, parts, platform):
    draft, meta, P = parts
    d, draft_id = _start_draft(plan, parts, platform)
    mats = d["materials"]
    meta_items = []
    t0 = int(time.time())

    # photos, one after another, hard cuts
    vtrack = copy.deepcopy(P["video_track"])
    vtrack["id"] = uid()
    vtrack["segments"] = []
    end = 0.0
    end_us = 0
    fps = float(d.get("fps") or 30.0)
    for ph in plan["photos"]:
        is_clip = bool(ph.get("clip"))
        w, h = ph.get("w") or 0, ph.get("h") or 0
        if not (w and h) and not is_clip:          # (a video's size comes with the clip; sips can't read one)
            w, h = photo_size(ph["path"])
        mat = copy.deepcopy(P["photo_material"])
        mat.update({"id": uid(), "path": native(ph["path"]), "material_name": Path(ph["path"]).stem,
                    "width": w, "height": h, "duration": PHOTO_LENGTH, "type": "photo"})
        if is_clip:                                # a video clip: the whole video is the material, the clip a part of it
            mat.update({"type": "video", "duration": int(round(float(ph["length"]) * US)), "has_audio": True})
        mats["videos"].append(mat)
        s = ph.get("scale") or (fill_scale(w, h) if ph.get("fill", True) else 1.0)
        target = tr_f(ph["start_f"], ph["dur_f"], fps) if "start_f" in ph else tr(ph["start"], ph["dur"])
        seg = _segment(P, mats, mat["id"], target, {"start": 0, "duration": target["duration"]}, s)
        if is_clip:                                # from where the clip starts; muted under a song, its own sound with none
            seg["source_timerange"] = {"start": int(round(float(ph["src"]) * US)), "duration": target["duration"]}
            seg["volume"] = 0.0 if plan.get("song") else 1.0
        vtrack["segments"].append(seg)
        end = max(end, ph["start"] + ph["dur"])
        end_us = max(end_us, target["start"] + target["duration"])
        meta_items.append({"duration": int(round(float(ph["length"]) * US)) if is_clip else 5 * US,
                           "extra_info": Path(ph["path"]).name, "file_Path": native(ph["path"]),
                           "height": h, "width": w, "metetype": "video" if is_clip else "photo", "t": t0})
    d["tracks"].append(vtrack)

    # the hook, as plain CapCut text they restyle with CapCut's own text styles
    hook = plan.get("hook")
    if hook and hook.get("text"):
        hook_us = us_f(hook["dur_f"], fps) if hook.get("dur_f") else int(round(hook.get("dur", 2.5) * US))
        ts = _text(P, mats, hook["text"], {"start": 0, "duration": min(hook_us, end_us)})
        tt = copy.deepcopy(P["text_track"])
        tt.update({"id": uid(), "segments": [ts]})
        d["tracks"].append(tt)

    # the song, starting where it picks up, ending with the last photo
    song = plan.get("song")
    if song:
        length = song.get("length") or song_length(song["path"])
        dur = min(end, max(0.0, length - song.get("from", 0.0))) if length else end
        aid = uid()
        refs = []
        if song.get("capcut_material"):
            # a song from CapCut's own music: carried over as CapCut saved it, so it stays CapCut's library song
            m = copy.deepcopy(song["capcut_material"])
            m["id"] = aid
            mats["audios"].append(m)
            wanted = ("speeds", "placeholder_infos", "sound_channel_mappings", "vocal_separations")
            for ex in P["photo_extras"]:
                if ex["list"] in wanted:
                    item = copy.deepcopy(ex["item"])
                    item["id"] = uid()
                    mats[ex["list"]].append(item)
                    refs.append(item["id"])
            if song.get("capcut_beats"):
                b = copy.deepcopy(song["capcut_beats"])
                b["id"] = uid()
                mats["beats"].append(b)
                refs.insert(2, b["id"])
        else:
            mats["audios"].append({
                "app_id": 0, "category_id": "", "category_name": "local", "check_flag": 1,
                "copyright_limit_type": "none", "duration": int(round((length or end) * US)), "effect_id": "",
                "formula_id": "", "id": aid, "intensifies_path": "", "is_ai_clone_tone": False,
                "is_text_edit_overdub": False, "is_ugc": False, "local_material_id": aid.lower(),
                "music_id": aid.lower(), "name": Path(song["path"]).name, "path": native(song["path"]), "query": "",
                "request_id": "", "resource_id": "", "search_id": "", "source_from": "", "source_platform": 0,
                "team_id": "", "text_id": "", "tone_category_id": "", "tone_category_name": "", "tone_effect_id": "",
                "tone_effect_name": "", "tone_platform": "", "tone_second_category_id": "",
                "tone_second_category_name": "", "tone_speaker": "", "tone_type": "", "type": "extract_music",
                "video_id": "", "wave_points": []})
            for ex in P["photo_extras"]:
                if ex["list"] in ("speeds", "sound_channel_mappings", "vocal_separations", "loudnesses"):
                    item = copy.deepcopy(ex["item"])
                    item["id"] = uid()
                    mats[ex["list"]].append(item)
                    refs.append(item["id"])
        if song.get("fade_out"):
            fid = uid()
            mats["audio_fades"].append({"fade_in_duration": 0, "fade_out_duration": int(song["fade_out"] * US),
                                        "fade_type": 0, "id": fid, "type": "audio_fade"})
            refs.append(fid)
        aseg = copy.deepcopy(P["photo_segment"])
        src0 = us_f(song["from_f"], fps) if song.get("from_f") is not None else int(round(song.get("from", 0.0) * US))
        a_dur = min(end_us, int(round(dur * US))) if length else end_us
        aseg.update({"id": uid(), "material_id": aid, "extra_material_refs": refs, "clip": None,
                     "hdr_settings": None, "uniform_scale": None, "render_index": 0, "track_render_index": 0,
                     "target_timerange": {"start": 0, "duration": a_dur},
                     "source_timerange": {"start": src0, "duration": a_dur},
                     "volume": 1.0, "enable_lut": False, "enable_adjust": False})
        d["tracks"].append({"attribute": 0, "flag": 0, "id": uid(), "is_default_name": True, "name": "",
                            "segments": [aseg], "type": "audio"})
        meta_items.append({"duration": int(round((length or end) * US)),
                           "extra_info": song.get("name") or Path(song["path"]).name,
                           "file_Path": native(song["path"]), "height": 0, "width": 0, "metetype": "music", "t": t0})

    d["duration"] = end_us
    d["update_time"] = now_us()
    return d, _finish_meta(meta, draft_id, plan["name"], d["duration"], meta_items)


# ---------------------------------------------------------------- a talking reel (Nicole's handoffs v23 and v24)
#
# Their talking-to-camera video, cut where they cut it, with their photos and videos where they put them, as a new
# CapCut project. Her numbers, each in one place. NOBODY HAS OPENED ONE OF THESE IN CAPCUT YET (Nicole's own were
# written into a scratch folder and never opened; docs/handoff-v24-build-2026-11-12.md, section 5): the layer
# flags and order, the speed item, the keyframes and the moved text all come from her reading of her own
# projects, not from a project CapCut wrote. Until a person opens one, every line below is "written, not seen".
#
# The plan (talking_make.py writes it; every path is real and stays on this side):
#     {"name": "Hannah talking reel", "photos": [], "song": None, "hook": None,
#      "files": [every file the project points at], "cover": a photo for the project's cover or None,
#      "video": {"path", "w", "h" (as it is SHOWN: a phone video held upright is stored turned), "length"},
#      "pieces": [{"from", "to" (seconds in the video), "speed", "zoom" (a place in "zooms" or None),
#                  "at", "dur" (seconds on the reel)}, …]                            talking.pieces(), in play order
#      "zooms": [{"a", "b", "kind": "punch" | "zoom", and only when set: "amount", "pace"}],   talking.zooms()
#      "shots": [{"at", "dur" (on the reel), "spot": "full" | "pip" | "center" | "corner",
#                 "pos": {x, y, w} or None, "me": {x, y, w} or None,
#                 "photos": [{"path", "w", "h"}, …]  or  "video": {"path", "w", "h", "length", "from"}}, …],
#      "captions": [{"text", "start", "end"}, …] or None (captions off), "cap_pos": {x, y} or None, "cap_size": 1}
#
# Layers, bottom to top, hers: the talking video (the main track); the photos and videos (flag 2); the small
# copies of the talking clip for "you in the corner" (flag 2, muted); the captions (text).
#
# The 30 fps grid (a deliberate difference from hers): CapCut moves every time onto whole frames when it opens a
# project, and in October that put every cut of a photo reel a frame late. So each piece's edges are put on whole
# frames here, and the photo, corner-copy and caption times are taken from those same edges, so the layers meet
# exactly. A sped-up piece shows its frame length times its speed of the video (one rule, for the main piece and
# its corner copy). A piece differs from hers by at most half a frame.

PUNCH = talking.ZOOM_AMOUNT["punch"]["medium"]      # hers: a punch in is the piece at 1.15 (Medium; talking.ZOOM_AMOUNT)
ZOOM_TO = talking.ZOOM_AMOUNT["zoom"]["medium"]     # hers: a slow zoom goes from 1.0 to 1.12 across its words (Medium)
ME_DEFAULT = {"x": (50 + CANVAS[0] * 0.36 / 2) / CANVAS[0],          # hers: them, small, bottom left
              "y": (CANVAS[1] - 60 - CANVAS[1] * 0.36 / 2) / CANVAS[1], "w": 0.36}
CAP_DEFAULT = {"x": 0.5, "y": 0.71}                                   # hers: captions low in the middle
MIN_VIDEO_STRETCH = 0.1     # hers: a video on a stretch is never shorter than this
SLACK = 1e-3                # hers: 1 ms of slack when asking whether a piece lies inside a stretch
# The slow zoom's two keyframes are timed in the VIDEO's own clock (hers: "timed in the clip's own source time").
# Other accounts of CapCut's files time them from the start of the clip. Nothing here was ever written by CapCut
# itself, so this is one switch in one function (_zoom_times): "video" (hers) or "clip".
# Judged by eye on Nov 12, 2026 (Dustin, CapCut 9.6.0, a steady clip): "really smooth... I didn't see any
# jittering", and a zoom across a closed pause carries on as one zoom (1.0 -> 1.1128, then 1.1128 -> 1.12). So
# "video" stays. As hers, and on the owners' list: two separate slow zooms side by side snap back to 1.0 at the
# cut, and a short stretch makes the fixed 12% look faster.
ZOOM_CLOCK = "video"
# A moving zoom EASES (Dustin, Nov 13: the steady one felt "robotic"): slow, quicker, slow again, on the one curve
# talking.ease. CapCut's own curve fields are unproven from outside, so the curve is written as several ordinary
# straight-line keyframes of the kind above, a point about every ZOOM_STEP seconds of the move, never fewer than
# ZOOM_MIN_STEPS + 1 points for a whole move nor more than ZOOM_MAX_STEPS + 1. The points are counted across the
# WHOLE move, so a zoom cut into pieces (a closed pause, a split, a change of speed, a joined run of clips) is
# still one curve: each piece starts on the value the one before ended on. NOBODY HAS WATCHED ONE IN CAPCUT YET.
ZOOM_STEP = 0.15
ZOOM_MIN_STEPS = 4
ZOOM_MAX_STEPS = 40


def fit_scale(w, h):
    """How many canvas pixels one pixel of a picture takes at CapCut's scale 1 (the picture fitted inside the
    frame). 0 for a size nobody could read."""
    if not w or not h:
        return 0.0
    return min(CANVAS[0] / w, CANVAS[1] / h)


def box_scale(w, h, across):
    """Hers: the scale that makes a picture `across` canvas pixels wide. 1 for a size nobody could read (the
    picture is fitted; never a division by nothing)."""
    f = fit_scale(w, h)
    if not f or not across:
        return 1.0
    return round(across / (w * f), 6)


def canvas_xy(cx, cy):
    """Hers: CapCut's position for something centred at canvas pixel (cx, cy) counted from the top left. CapCut
    counts from the middle, in half-canvases, up is positive."""
    cw, ch = CANVAS
    return {"x": round((cx - cw / 2) / (cw / 2), 6), "y": round((ch / 2 - cy) / (ch / 2), 6)}


def default_place(spot, w, h):
    """Hers (the page uses the same numbers): where a photo sits before they move it, as its centre and its width
    in parts of the screen. Center: 70% wide, a little above the middle. Small corner: 35% wide, top right."""
    if spot == "center":
        return {"x": 0.5, "y": 0.44, "w": 0.704}
    tall = 0.352 * (CANVAS[0] / CANVAS[1]) * (h / w if w and h else 1.0)       # its height, as a part of the screen
    return {"x": 1 - 0.046 - 0.176, "y": 0.073 + tall / 2, "w": 0.352}


# The page's own limits (talking_rec's save holds every box and size to these). A record changed by hand could hold
# anything, so the builder holds them too: a number that is no number falls back to where the thing sits by itself.
BOX_LIMITS = {"x": (-0.5, 1.5), "y": (-0.5, 1.5), "w": (0.08, 2.0)}
CAP_LIMITS = (0.02, 0.98)
SIZE_LIMITS = (0.4, 3.0)


def _held(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):
        return default
    return min(hi, max(lo, v))


def _held_box(box, default):
    """A {x, y, w} they dragged something to, held to the page's limits; `default` when there is none."""
    if not isinstance(box, dict):
        return dict(default)
    return {k: _held(box.get(k), BOX_LIMITS[k][0], BOX_LIMITS[k][1], default[k]) for k in ("x", "y", "w")}


def _zoom_times(source, target):
    """When a piece's two zoom keyframes fall, in microseconds: (at its start, at its end). See ZOOM_CLOCK."""
    if ZOOM_CLOCK == "clip":
        return 0, target["duration"]
    return source["start"], source["start"] + source["duration"]


def zoom_keyframes(P, t0, t1, v0, v1, between=()):
    """A zoom on one clip: CapCut's scale keyframes, v0 at t0 and v1 at t1, a straight line from each to the next
    (hers; the piece is typed from her field list, see parts.json's _about). `between` is more (time, value)
    points of the same kind, in order: how an eased zoom is written (see ZOOM_STEP)."""
    prop = copy.deepcopy(P["scale_keyframe"]["property"])
    prop["id"] = uid()
    for t, v in [(t0, v0)] + list(between) + [(t1, v1)]:
        k = copy.deepcopy(P["scale_keyframe"]["keyframe"])
        k.update({"id": uid(), "time_offset": int(t), "values": [v]})
        prop["keyframe_list"].append(k)
    return [prop]


def zoom_move_frames(z, span, fps):
    """How many frames a zoom's move lasts, of the `span` frames its whole stretch has on the reel: 0 for a punch
    in that is simply closer (no move), else at least 1 (talking.zoom_move, on the frame grid)."""
    secs = talking.zoom_move(z, span / fps)
    if secs <= 0:
        return 0
    return max(1, min(int(span), int(round(secs * fps))))


def zoom_points(za, move, a, b, fps):
    """The frames a piece's zoom keyframes sit on. The piece runs a..b on the reel; the zoom's move starts at
    frame za and lasts `move` frames. Always a and b; between them the points of the WHOLE move's own grid (so
    every piece of one zoom is cut from the same curve), and the frame the move ends on, after which it holds."""
    steps = max(ZOOM_MIN_STEPS, min(ZOOM_MAX_STEPS, int(math.ceil(move / fps / ZOOM_STEP))))
    steps = max(1, min(steps, move))
    grid = {za + int(round(i * move / steps)) for i in range(steps + 1)}
    return sorted({a, b} | {f for f in grid if a < f < b})


def zoom_scale(z, f, za, move):
    """A zoom's scale at reel frame f, before the video's own fill: 1.0 where its move starts (frame za), the
    amount from the move's end on, and talking.ease between."""
    end = talking.zoom_amount(z)
    if move <= 0 or f >= za + move:
        return end
    return 1.0 + (end - 1.0) * talking.ease((f - za) / move)


def overlay_track(P, segs, k):
    """Hers: a layer above the main one, the way CapCut writes them in the photographer's own projects: flag 2,
    its clips in time order, numbered by layer (the k-th layer up: render_index k + 1, track_render_index k)."""
    t = copy.deepcopy(P["video_track"])
    t["id"] = uid()
    t["flag"] = 2
    t["segments"] = sorted(segs, key=lambda x: x["target_timerange"]["start"])
    for sg in t["segments"]:
        sg["render_index"] = k + 1
        sg["track_render_index"] = k
    return t


def _set_speed(seg, mats, speed):
    """Hers: a sped-up clip says so twice, on the clip and on its own speed item."""
    if speed == 1.0:
        return
    seg["speed"] = speed
    for sp in mats.get("speeds", []):
        if sp["id"] in seg["extra_material_refs"]:
            sp["speed"] = speed


def _piece_speed(p):
    try:
        v = float(p.get("speed") or 1.0)
    except (TypeError, ValueError):
        return 1.0
    return v if v > 0 else 1.0


def talking_grid(pieces, fps=30.0, length=0.0):
    """Each piece's place on the reel in whole frames: [(first frame, the frame after its last)], one after
    another with no gap. A piece is never under one frame, and never shows more of the video than there is (the
    last piece's 0.14 s of air after the last word can run past the end of a video that stops on that word)."""
    out, at = [], 0
    for p in pieces:
        b = max(at + 1, int(round((float(p["at"]) + float(p["dur"])) * fps)))
        if length:
            room = int((float(length) - float(p["from"])) / _piece_speed(p) * fps + 1e-6)
            b = min(b, at + max(1, room))
        out.append((at, b))
        at = b
    return out


def _on_grid(t, pieces, grid):
    """A moment on the reel (as talking.py counted it) as a whole frame on the grid: a piece's own edge exactly,
    a moment inside a piece in proportion."""
    for p, (a, b) in zip(pieces, grid):
        s, e = float(p["at"]), float(p["at"]) + float(p["dur"])
        if t <= s + SLACK:
            return a
        if t < e - SLACK:
            return a + int(round((t - s) / (e - s) * (b - a)))
    return grid[-1][1] if grid else 0


def build_talking(plan, parts, platform):
    """A talking reel's project (see the plan above). capcut.write(plan, store, builder=build_talking).
    Afterwards build_talking.no_frame says how many photos could not be shown: a stretch with more photos than
    frames (30 photos on half a second) has no frame for the rest; every photo gets one whenever there is one."""
    draft, meta, P = parts
    d, draft_id = _start_draft(plan, parts, platform)
    mats = d["materials"]
    fps = float(d.get("fps") or 30.0)
    cw, ch = CANVAS
    t0 = int(time.time())
    V = plan["video"]
    vw, vh, length = int(V.get("w") or 0), int(V.get("h") or 0), float(V.get("length") or 0)
    pieces = list(plan["pieces"])
    zooms = plan.get("zooms") or []
    grid = talking_grid(pieces, fps, length)
    total = grid[-1][1] if grid else 0
    meta_items, listed = [], set()

    def note(path, w, h, kind, dur_us):               # CapCut's own list of what is in the project, each file once
        if native(path) not in listed:
            listed.add(native(path))
            meta_items.append({"duration": dur_us, "extra_info": Path(path).name, "file_Path": native(path),
                               "height": h, "width": w, "metetype": kind, "t": t0})

    def material(path, w, h, video_length=None):
        mat = copy.deepcopy(P["photo_material"])
        mat.update({"id": uid(), "path": native(path), "material_name": Path(path).stem, "width": w, "height": h,
                    "duration": PHOTO_LENGTH, "type": "photo"})
        if video_length is not None:
            mat.update({"type": "video", "duration": int(round(video_length * US)), "has_audio": True})
        mats["videos"].append(mat)
        note(path, w, h, "photo" if video_length is None else "video",
             5 * US if video_length is None else int(round(video_length * US)))
        return mat

    # ONE material for their talking video (hers made one per piece): every piece and every corner copy is a part of it
    vmat = material(V["path"], vw, vh, length)
    fill = cover_scale(vw, vh)                         # 1 for a 9:16 video; a video that is not 9:16 fills the frame

    def frames(z):                                     # a zoom's whole stretch on the reel, in frames
        on = [g for p, g in zip(pieces, grid) if p.get("zoom") == z]
        return min(a for a, _ in on), max(b for _, b in on)

    main = copy.deepcopy(P["video_track"])
    main["id"] = uid()
    main["segments"] = []
    spans = []                                         # each piece's (target, source, speed), for its corner copy
    for p, (a, b) in zip(pieces, grid):
        sp = _piece_speed(p)
        target = tr_f(a, b - a, fps)
        source = {"start": int(round(float(p["from"]) * US)), "duration": int(round(target["duration"] * sp))}
        spans.append((target, source, sp))
        seg = _segment(P, mats, vmat["id"], target, source, fill)
        seg["volume"] = 1.0
        _set_speed(seg, mats, sp)
        zi = p.get("zoom")
        z = zooms[zi] if type(zi) is int and 0 <= zi < len(zooms) and isinstance(zooms[zi], dict) else None
        if z and z.get("kind") in ("punch", "zoom"):
            # how much and how fast are the zoom's own (talking.ZOOM_AMOUNT); a zoom nobody set is hers: a punch
            # in simply sits at 1.15, a slow zoom runs 1.0 to 1.12 across its whole stretch, piece by piece
            za, zb = frames(zi)
            move = zoom_move_frames(z, zb - za, fps)
            if move <= 0 or a >= za + move:            # no move in this piece: it sits at the amount, no keyframes
                s = round(fill * talking.zoom_amount(z), 6)
                seg["clip"]["scale"] = {"x": s, "y": s}
            else:                                      # the eased move, as points on its one curve
                t_a, t_b = _zoom_times(source, target)
                pts = [(t_a + int(round((t_b - t_a) * (f - a) / max(1, b - a))), round(fill * zoom_scale(z, f, za, move), 6))
                       for f in zoom_points(za, move, a, b, fps)]
                seg["clip"]["scale"] = {"x": pts[0][1], "y": pts[0][1]}
                seg["common_keyframes"] = zoom_keyframes(P, t_a, t_b, pts[0][1], pts[-1][1], pts[1:-1])
        main["segments"].append(seg)
    d["tracks"].append(main)

    photos, copies = [], []
    build_talking.no_frame = 0                         # photos left out because their stretch has fewer frames than photos
    for sh in plan.get("shots") or []:
        fa, fb = _on_grid(float(sh["at"]), pieces, grid), _on_grid(float(sh["at"]) + float(sh["dur"]), pieces, grid)
        if fb <= fa:
            continue
        spot = sh.get("spot")

        def placed(w, h, sh=sh, spot=spot):            # (scale, position): hers
            if spot in ("full", "pip"):
                return cover_scale(w, h), None         # Full screen and "you in the corner" fill the frame
            box = _held_box(sh.get("pos"), default_place(spot, w, h))
            return box_scale(w, h, box["w"] * cw), canvas_xy(box["x"] * cw, box["y"] * ch)

        v = sh.get("video")
        if v:                                          # a video of theirs instead: muted, from where they chose
            w, h, vlen = int(v.get("w") or 0), int(v.get("h") or 0), float(v.get("length") or 0)
            start = min(max(0.0, float(v.get("from") or 0)), max(0.0, vlen - MIN_VIDEO_STRETCH))
            n = min(fb - fa, max(int(round(MIN_VIDEO_STRETCH * fps)), int((vlen - start) * fps + 1e-6)))
            target = tr_f(fa, n, fps)
            s, xy = placed(w, h)
            seg = _segment(P, mats, material(v["path"], w, h, vlen)["id"], target,
                           {"start": int(round(start * US)), "duration": target["duration"]}, s)
            seg["volume"] = 0.0
            if xy:
                seg["clip"]["transform"] = xy
            photos.append(seg)
        else:                                          # photos, one after another, evenly across the stretch
            ps = [x for x in (sh.get("photos") or []) if isinstance(x, dict) and x.get("path")]
            for j, ph in enumerate(ps):
                a = fa + int(round(j * (fb - fa) / len(ps)))
                b = fa + int(round((j + 1) * (fb - fa) / len(ps)))
                if b <= a:
                    build_talking.no_frame += 1        # more photos than frames: this one has no frame to be on
                    continue
                w, h = ph.get("w") or 0, ph.get("h") or 0
                if not (w and h):
                    w, h = photo_size(ph["path"])
                target = tr_f(a, b - a, fps)
                s, xy = placed(w, h)
                seg = _segment(P, mats, material(ph["path"], w, h)["id"], target, {"start": 0, "duration": target["duration"]}, s)
                if xy:
                    seg["clip"]["transform"] = xy
                photos.append(seg)
        if spot == "pip":                              # themselves, small, on top: on each piece wholly inside the stretch
            me = _held_box(sh.get("me"), ME_DEFAULT)
            lo, hi = float(sh["at"]) - SLACK, float(sh["at"]) + float(sh["dur"]) + SLACK
            for p, (target, source, sp) in zip(pieces, spans):
                if float(p["at"]) >= lo and float(p["at"]) + float(p["dur"]) <= hi:
                    # at scale me.w, as hers (NOT times the fill: CapCut cannot crop, so a sideways video's copy
                    # "filling" its box would be wider than the whole frame). For a 9:16 video the two are the same.
                    seg = _segment(P, mats, vmat["id"], dict(target), dict(source), round(me["w"], 6))
                    seg["clip"]["transform"] = canvas_xy(me["x"] * cw, me["y"] * ch)
                    seg["volume"] = 0.0                # the sound is the main piece's; no zoom on the copy (hers)
                    _set_speed(seg, mats, sp)
                    copies.append(seg)
    k = 1
    for segs in (photos, copies):
        if segs:
            d["tracks"].append(overlay_track(P, segs, k))
            k += 1

    # the captions: plain text they restyle in CapCut, where they dragged them and as big as they made them.
    # None (captions off) writes no caption layer at all.
    caps = [c for c in (plan.get("captions") or []) if isinstance(c, dict) and str(c.get("text") or "").strip()]
    if caps:
        cp = plan.get("cap_pos") if isinstance(plan.get("cap_pos"), dict) else {}
        cp = {k: _held(cp.get(k), CAP_LIMITS[0], CAP_LIMITS[1], CAP_DEFAULT[k]) for k in ("x", "y")}
        cs = _held(plan.get("cap_size") or 1, SIZE_LIMITS[0], SIZE_LIMITS[1], 1.0)
        where = {"x": round((cp["x"] - 0.5) * 2, 6), "y": round((0.5 - cp["y"]) * 2, 6)}
        starts = []
        for c in caps:                                 # each on its own frame, in order
            a = _on_grid(float(c["start"]), pieces, grid)
            if starts and a <= starts[-1][0]:
                a = starts[-1][0] + 1
            if a < total:
                starts.append((a, c))
        tt = copy.deepcopy(P["text_track"])
        tt.update({"id": uid(), "segments": []})
        for i, (a, c) in enumerate(starts):            # hers: each stays until the next; the last ends where it ends
            b = starts[i + 1][0] if i + 1 < len(starts) else max(a + 1, min(total, _on_grid(float(c["end"]), pieces, grid)))
            ts = _text(P, mats, str(c["text"]), tr_f(a, b - a, fps))
            if ts.get("clip"):
                ts["clip"]["transform"] = dict(where)
                ts["clip"]["scale"] = {"x": cs, "y": cs}
            tt["segments"].append(ts)
        if tt["segments"]:
            d["tracks"].append(tt)

    d["duration"] = us_f(total, fps)
    d["update_time"] = now_us()
    return d, _finish_meta(meta, draft_id, plan["name"], d["duration"], meta_items)

ROOT_ENTRY_KEYS = {
    "cloud_draft_cover": False, "cloud_draft_sync": False, "draft_cloud_last_action_download": False,
    "draft_cloud_purchase_info": "", "draft_cloud_template_id": "", "draft_cloud_tutorial_info": "",
    "draft_cloud_videocut_purchase_info": "", "draft_is_ai_shorts": False, "draft_is_cloud_temp_draft": False,
    "draft_is_infinite_canvas_draft": False, "draft_is_invisible": False, "draft_is_pippit_draft": False,
    "draft_is_web_article_video": False, "draft_new_version": "", "draft_timeline_materials_size": 0,
    "draft_type": "", "draft_web_article_video_enter_from": "", "pippit_avatar_url": "", "pippit_extra_info": "",
    "pippit_id": "", "pippit_user_name": "", "streaming_edit_draft_ready": True, "tm_draft_cloud_completed": "",
    "tm_draft_cloud_entry_id": -1, "tm_draft_cloud_modified": 0, "tm_draft_cloud_parent_entry_id": -1,
    "tm_draft_cloud_space_id": -1, "tm_draft_cloud_user_id": -1, "tm_draft_removed": 0}


def _not_reserved_windows(name):
    """A name Windows keeps for itself (CON, AUX, NUL, COM1, LPT1...) gets an underscore straight after that
    word, before any dot: Windows reads "Con.Beach reel" as CON too, so "Con.Beach reel_" would still fail and
    "Con_.Beach reel" doesn't. (this_computer.unreserved does exactly this now, for every script.)"""
    return this_computer.unreserved(name)


def folder_name(store, name):
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", name)        # characters Mac or Windows won't take in a folder name
    base = re.sub(r"\s+", " ", base).strip().lstrip(".").strip() or "Studio reel"
    if this_computer.WINDOWS:
        # unproven on a real PC. A PC drops a dot or space at the end of a folder name, and refuses its few
        # reserved names; and it stops at 260 characters for a whole path unless long paths were switched on,
        # while CapCut's own folder is already about 90 deep (C:\Users\<name>\AppData\Local\CapCut\User Data\...)
        base = _not_reserved_windows(base.strip(" .") or "Studio reel")
        base = base[:80].rstrip(" .") or "Studio reel"
    cand, n = base, 2
    while (store / cand).exists():
        cand = f"{base} {n}"
        n += 1
    return cand


def write_json(path, obj, strict=False):
    """`strict`: a number CapCut could not read (Infinity, NaN) raises ValueError before anything is written,
    rather than going into the file (for a valid project the bytes are the same either way)."""
    tmp = path.with_name(path.name + ".studio-tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=not strict), encoding="utf-8")
    try:
        this_computer.replace(tmp, path)     # on a PC, waits a moment if another program has the file open
    except OSError:
        try:
            tmp.unlink()                     # our own half-step; the file it was to replace is untouched
        except OSError:
            pass
        raise


def file_hash(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def native(p):
    """A path the way CapCut writes it on this computer."""
    return str(p).replace("\\", "/") if os.name == "nt" else str(p)


def write(plan, store, ignore_open=False, builder=None):
    """Returns (project folder, draft). `builder` makes the project from the plan (build, a photo reel, when
    none is given; build_talking for a talking reel). A plan may also name every other file its project points
    at ("files": all of them must be there, or nothing is written) and the photo for the cover ("cover"). With CapCut open, only the new project's own folder is written and
    CapCut adds it to its list by itself (seen on Dustin's Mac, CapCut 9.6, Oct 25: within two seconds, twice);
    CapCut's list file is left alone, since an open CapCut writes its own copy of it. With CapCut closed, the
    project is added to the list too, after a copy of the list is kept.
    Afterwards: write.listed (in CapCut's list now), write.left_to_capcut (a Mac's open CapCut adds it),
    write.waiting (noted in root_meta_info.studio-waiting.json, to be added the next time CapCut is closed:
    on a PC whenever CapCut was open, since a PC's CapCut hasn't been seen adding folders by itself, and on
    either computer when the list couldn't be saved), write.note (plain words to pass on, or None)."""
    is_open = False if ignore_open else bool(capcut_open())
    if not store.is_dir():
        say(f"STOP: I can't find CapCut's projects folder ({store}). Is CapCut installed, and has it been opened once?")
        sys.exit(2)
    missing = [p["path"] for p in plan["photos"] if not Path(p["path"]).is_file()]
    if plan.get("song") and not Path(plan["song"]["path"]).is_file():
        missing.append(plan["song"]["path"])
    missing += [str(f) for f in plan.get("files") or [] if not Path(f).is_file()]
    if missing:
        say("STOP: these files are not where the plan says: " + ", ".join(missing[:5]))
        sys.exit(2)

    write.left_to_capcut, write.note = is_open, None
    write.waiting = write.listed = False
    fold = folder_name(store, plan["name"])
    dest = store / fold
    # Made under a hidden name in CapCut's projects folder and given its real name only once every file is in it
    # (v19 review): a make stopped part way (a job past its time, the power) leaves no half-made project under a
    # name CapCut would list. Everything written inside names the real folder, since that is where it ends up.
    # (That CapCut leaves a folder whose name starts with a dot alone is not proven; it would have no project file.)
    part = store / f".{fold}.making-{os.getpid()}-{uid()[:8]}"
    try:
        part.mkdir()
    except OSError as e:
        say(f"STOP: I couldn't make the project's folder in CapCut's projects folder ({e}). Nothing was written.")
        sys.exit(2)
    # A song file goes INTO the project's own folder, and the project points at that copy. CapCut can always
    # open its own folder; it cannot always open where the song was (Nicole's first reel, Nov 5: the song sat
    # in her Music folder, CapCut showed "File not accessible" and asked her to link it by hand). It also means
    # nothing done to the original afterwards (moved, renamed, tidied) can break the reel.
    song = plan.get("song")
    if song and not song.get("capcut_material"):
        src = Path(song["path"])
        kept = part / src.name
        try:
            shutil.copyfile(src, kept)
            same = kept.stat().st_size == src.stat().st_size and file_hash(kept) == file_hash(src)
        except OSError as e:
            same = False
            say(f"STOP: I couldn't put the song into the CapCut project ({e}).")
        if not same:
            try:
                kept.unlink(missing_ok=True)       # our own half-made copy, in the hidden folder we just made
                part.rmdir()
            except OSError:
                pass
            say("STOP: the song's copy inside the CapCut project didn't match the original, so I made nothing. Try again.")
            sys.exit(2)
        plan = dict(plan, song=dict(song, path=native(dest / src.name), name=song.get("name") or src.name, original=str(src)))
    try:
        draft, meta = (builder or build)(plan, load_parts(), their_platform(store))
        draft["name"] = meta["draft_name"] = fold
        t = now_us()
        meta.update({"draft_fold_path": native(dest), "draft_root_path": native(store),
                     "tm_draft_create": t, "tm_draft_modified": t})
        json.dumps([draft, meta], allow_nan=False)     # a number CapCut could not read (Infinity, NaN) stops it here
        write_json(part / draft_file_name(), draft)
        write_json(part / "draft_meta_info.json", meta)
    except Exception:
        shutil.rmtree(part, ignore_errors=True)        # our own hidden making folder: only files this run wrote
        raise
    (part / "draft_settings").write_text(
        f"[General]\ndraft_create_time={t // US}\ndraft_last_edit_time={t // US}\nreal_edit_keys=0\nreal_edit_seconds=0\n",
        encoding="utf-8")
    cover = dest / "draft_cover.jpg"           # where it will be; it is made in the hidden folder
    made_cover = part / "draft_cover.jpg"
    # the cover is a photo, never a video: the one the plan names, else the reel's first photo
    first = plan.get("cover") or next((p["path"] for p in plan["photos"] if not p.get("clip")), None)
    if first and pictures.use_sips():
        subprocess.run(["sips", "-Z", "720", "-s", "format", "jpeg", first, "--out", str(made_cover)], capture_output=True)  # pc-ok: Mac branch
    elif first and pictures.make_jpeg(first, made_cover, 720):
        pass                                 # a PC: the same small cover, made with Pillow
    elif first and str(first).lower().endswith((".jpg", ".jpeg")) and os.path.getsize(first) < 4_000_000:
        shutil.copyfile(first, made_cover)
    # Every file is in: the folder takes its real name, never over a folder that is there (a rename onto an empty
    # folder would replace it on a Mac, so the name is looked at first; Windows refuses a name that is there).
    try:
        if os.path.lexists(dest):
            raise FileExistsError(str(dest))
        os.rename(part, dest)
    except OSError:
        # (another make took the name in the same moment, most likely.) The hidden making folder holds only files
        # this run wrote: it is cleared, so nothing half-made is left in CapCut's projects folder. No place is named.
        shutil.rmtree(part, ignore_errors=True)
        say("STOP: I couldn't give the CapCut project its name. Nothing was added to CapCut. Try again.")
        sys.exit(2)

    entry = dict(ROOT_ENTRY_KEYS)
    entry.update({"draft_cover": native(cover), "draft_fold_path": native(dest), "draft_id": draft["id"],
                  "draft_json_file": native(dest / draft_file_name()), "draft_name": fold,
                  "draft_root_path": native(store), "tm_draft_create": t, "tm_draft_modified": t,
                  "tm_duration": draft["duration"]})
    if is_open:
        if this_computer.WINDOWS:
            # unproven on a real PC (row I7): only CapCut on a Mac has been seen adding a new project folder to
            # its list by itself. So on a PC the reel waits, and is added to the list the next time this runs
            # with CapCut closed (the next reel, or `capcut.py open`, which adds it and then starts CapCut).
            write.left_to_capcut = False
            if _wait(store, entry):
                write.waiting = True
                write.note = ("CapCut is open, so I didn't touch its list of projects; it may add the reel by itself "
                              "in a moment. If it isn't there, close CapCut and I'll add it.")
            else:
                write.note = (f"CapCut is open, so I didn't touch its list of projects. If the reel isn't in CapCut "
                              f"in a moment, {QUIT} and reopen CapCut.")
        return dest, draft
    listed, write.note = add_to_list(store, [entry])
    write.listed = listed
    if not listed and write.note is None:
        # something (on a PC, most likely CapCut itself) had the list open: their list stays as it was
        write.waiting = _wait(store, entry)
        write.note = ("I couldn't add the reel to CapCut's list of projects just now (another program had the list "
                      "open), so I left the list as it was."
                      + (" Open CapCut; if the reel isn't at the top, " + QUIT + " CapCut and I'll add it."
                         if write.waiting else f" Open CapCut; if the reel isn't at the top, {QUIT} and reopen CapCut once."))
    return dest, draft


WAITING = "root_meta_info.studio-waiting.json"      # reels made while the list couldn't be written, to add later
WAITING_HINT = ("NOTE: once CapCut is closed, `capcut.py open` adds the waiting reel to CapCut's list of projects "
                "and then starts CapCut.")


def _is_number(t):
    return isinstance(t, (int, float)) and not isinstance(t, bool)


def _waiting(store):
    try:
        got = _read_json(store / WAITING)
        # A draft id is always text (uid()) and a time always a number (write()): an entry with anything else in
        # a hand-damaged list is left out, never a crash, and never copied into CapCut's own list, which then
        # only ever gets what this script wrote.
        return [x for x in got if isinstance(x, dict) and x.get("draft_id") and isinstance(x["draft_id"], str)
                and ("tm_draft_create" not in x or _is_number(x["tm_draft_create"]))] \
            if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def waiting(store=None):
    """The reels still waiting to be added to CapCut's list of projects (made while CapCut was open on a PC, or
    while the list couldn't be saved): a list of CapCut's own list entries, [] when none. For other scripts
    (the posting page's "Open in CapCut"); never raises for a damaged or missing list."""
    return _waiting(Path(store) if store else default_store())


def _wait(store, entry):
    """Note a reel that isn't in CapCut's list yet, to add it next time. True when noted."""
    try:
        write_json(store / WAITING, [x for x in _waiting(store) if x.get("draft_id") != entry["draft_id"]] + [entry])
        return True
    except OSError:
        return False


def _made_when(w):
    """When a waiting reel was made, for putting them in order: 0 for anything that isn't a number (a list
    damaged by hand), so the sort never meets text beside a number. A number sorts exactly as before."""
    t = w.get("tm_draft_create")
    return t if isinstance(t, (int, float)) else 0


def add_to_list(store, entries):
    """Add these reels, and any still waiting from before, to CapCut's list of projects (newest at the top),
    after keeping a copy of the list as it was. CapCut must be closed. (True, None) when the list was saved;
    (False, None) when it couldn't be saved; (False, plain words) when the list was left alone on purpose.
    A waiting reel whose folder is gone, or that CapCut already lists, is not added again."""
    root = store / "root_meta_info.json"
    if root.is_file():
        try:
            r = _read_json(root)
            if not isinstance(r, dict):
                raise ValueError("not a list of projects")
        except (OSError, ValueError):
            # their list is in a form this can't read (a newer CapCut may lock it): it is left exactly as it is
            return False, ("CapCut's own list of projects is in a form I can't read, so I left it alone. If the "
                           f"reel isn't in CapCut when you open it, {QUIT} and reopen CapCut once.")
        try:
            first_backup = store / "root_meta_info.before-studio.json"
            if not first_backup.exists():
                shutil.copyfile(root, first_backup)
            shutil.copyfile(root, store / "root_meta_info.studio-backup.json")
        except OSError:
            return False, None                       # no copy kept, so the list isn't touched
    else:
        r = {"all_draft_store": [], "draft_ids": 0, "root_path": native(store)}
    waiting = _waiting(store)
    listed = r.setdefault("all_draft_store", [])
    have = {x.get("draft_id") for x in listed if isinstance(x, dict)}
    mine = {e["draft_id"] for e in entries}
    late = [w for w in waiting if w["draft_id"] not in mine and w["draft_id"] not in have
            and Path(str(w.get("draft_json_file", ""))).is_file()]
    for e in sorted(late, key=_made_when) + list(entries):   # oldest first, so the newest ends on top
        if e["draft_id"] not in have:
            listed.insert(0, e)
            r["draft_ids"] = int(r.get("draft_ids") or 0) + 1
    try:
        write_json(root, r)
    except OSError:
        return False, None
    if waiting:
        try:
            write_json(store / WAITING, [])           # all of them are in CapCut's list now (or gone)
        except OSError:
            pass
    return True, None


OPENED = "Opened CapCut. The newest project is at the top of its list."   # open_capcut's words when it worked
# What the photographer reads after pressing Open CapCut on the reel page (decision 24 of the v19 plan: Nicole's
# words, word for word from her server.py). The kit page still says its own line until it is rebuilt as her cards.
OPEN_WORDS = "CapCut is opening. Your newest reel is at the top of your projects."


def open_capcut(store=None, closed=False):
    """Start CapCut, first adding any reel still waiting to its list (made while CapCut was open on a PC, or
    while the list couldn't be saved) when CapCut is surely closed. (True, words) or (False, "STOP: ...").
    On success the words are OPENED, then one sentence about a waiting reel if there was one to add.
    closed=True: the photographer has said CapCut is closed (`capcut.py open --closed`), so this computer isn't
    asked, for when it couldn't tell (open_capcut.unsure).

    Afterwards, for a caller that wants to know without reading the words:
      open_capcut.added    True: a waiting reel was added to CapCut's list just now. False: it was tried and
                           couldn't be. None: nothing was tried (nothing waiting, or CapCut was open or unsure).
      open_capcut.running  True when a reel was waiting and CapCut was already open, so it wasn't added. Else False.
      open_capcut.unsure   True when a reel was waiting but whether CapCut was open couldn't be told (on a PC,
                           Windows' tasklist didn't answer), so nothing was added: pressing again won't help;
                           the reel goes in with `capcut.py open --closed` once they say CapCut is closed. Else False.
      open_capcut.waiting  the reels still waiting afterwards (as waiting() gives them)."""
    store = Path(store) if store else default_store()
    added = ""
    open_capcut.added, open_capcut.unsure, open_capcut.running = None, False, False
    if _waiting(store):
        running = False if closed else capcut_open()
        open_capcut.running = running is True
        if running is False:
            ok, why = add_to_list(store, [])
            open_capcut.added = ok
            added = (" The reel that was waiting is in its list now." if ok else
                     " " + (why or "I still couldn't add the waiting reel to CapCut's list of projects."))
        elif running is None:
            open_capcut.unsure = True
    open_capcut.waiting = _waiting(store)
    ok, why = launch()
    return (True, OPENED + added) if ok else (False, f"STOP: {why}.")


open_capcut.added, open_capcut.unsure, open_capcut.running, open_capcut.waiting = None, False, False, []

# For Claude, after `capcut.py open`, when a waiting reel is still waiting (never part of open_capcut's own
# words, which the posting page passes on to the photographer)
STILL_WAITING_UNSURE = ("NOTE: a reel is still waiting to go into CapCut's list of projects. I couldn't tell whether "
                        "CapCut was already open, so I left it (CapCut can undo a change to its list made while it is "
                        f"open). Ask them to {QUIT} CapCut, and once they say it's closed, run `capcut.py open --closed`: "
                        "it adds the waiting reel, then starts CapCut again.")
STILL_WAITING_RUNNING = ("NOTE: a reel is still waiting to go into CapCut's list of projects: CapCut was already open, "
                         f"so I left it. Ask them to {QUIT} CapCut, then run `capcut.py open` again.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("where")
    w.add_argument("--store")
    sg = sub.add_parser("songs", help="songs from CapCut's music used in their projects")
    sg.add_argument("--store")
    wr = sub.add_parser("write")
    wr.add_argument("--plan", required=True)
    wr.add_argument("--store")
    wr.add_argument("--ignore-open", action="store_true")
    op = sub.add_parser("open", help="start CapCut (first adding any reel still waiting to its list)")
    op.add_argument("--store")
    op.add_argument("--closed", action="store_true",
                    help="they've said CapCut is closed: add a waiting reel without asking this computer")
    a = ap.parse_args()
    store = Path(a.store).expanduser() if a.store else default_store()
    if a.cmd == "open":
        ok, words = open_capcut(store, closed=a.closed)
        say(words)
        if ok and open_capcut.waiting and open_capcut.unsure:
            say(STILL_WAITING_UNSURE)
        elif ok and open_capcut.waiting and open_capcut.running:
            say(STILL_WAITING_RUNNING)
        sys.exit(0 if ok else 2)
    if a.cmd == "where":
        open_ = capcut_open()
        n = len([p for p in store.iterdir() if p.is_dir() and not p.name.startswith(".")]) if store.is_dir() else 0
        plat = their_platform(store) if store.is_dir() else None
        ver = (plat or {}).get("platform", {}).get("app_version", "unknown")
        say(json.dumps({"store": str(store), "found": store.is_dir(), "projects": n, "capcut_version": ver,
                        "capcut_open": open_}, indent=1))
        return
    if a.cmd == "songs":
        for x in capcut_songs(store):
            say(f"{x['name']}  ({int(x['seconds'] // 60)}:{int(x['seconds'] % 60):02d})  in \"{x['project']}\""
                + ("" if x["present"] else "  (not downloaded right now)"))
        return
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    dest, draft = write(plan, store, a.ignore_open)
    secs = draft["duration"] / US
    n_cl = sum(1 for p in plan["photos"] if p.get("clip"))
    n = len(plan["photos"]) - n_cl
    what = (f"{n_cl} clip{'s' if n_cl != 1 else ''} and {n} photo{'s' if n != 1 else ''}" if n_cl else f"{n} photos")
    say(f"Made \"{dest.name}\" in CapCut: {what}, {secs:.1f} seconds"
        + (f", on the beat of {plan['song'].get('name') or Path(plan['song']['path']).name}" if plan.get("song") else "")
        + (". Open CapCut and it's at the top of your projects." if write.listed else "."))
    if write.left_to_capcut:
        say(f"CapCut is open, so it will add it to your projects by itself in a moment. If it isn't there, {QUIT} and reopen CapCut.")
    if write.note:
        say(write.note)
    if write.waiting:
        say(WAITING_HINT)


if __name__ == "__main__":
    main()
