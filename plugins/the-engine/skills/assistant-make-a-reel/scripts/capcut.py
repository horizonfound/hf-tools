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
     "song": {"path": "/…/song.m4a", "from": 41.3, "dur": 13.2, "fade_out": 0.6} or null,
     "hook": {"text": "…", "dur": 2.4} or null}

How: every CapCut project is a folder of plain files. This builds one from pieces
CapCut itself wrote (references/capcut/), never edits a project they made, and
never overwrites a folder. If CapCut is open, it only writes the new project's
folder and CapCut picks it up by itself; if CapCut is closed, it also adds the
project to CapCut's list of projects, after keeping a copy of that list.

Exit codes: 0 made · 2 stop (no CapCut found, a photo or the song missing).
"""
import argparse
import copy
import json
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
    the newest is at the top of its list."""
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["open", "-a", "CapCut"], capture_output=True, encoding="utf-8", errors="replace")  # pc-ok: Mac branch
            return (True, "") if r.returncode == 0 else (False, "CapCut isn't installed on this Mac")
        if os.name == "nt":
            for p in _windows_capcut_programs():            # unproven on a real PC
                if p.is_file():
                    os.startfile(str(p))                     # pc-ok: Windows branch; starts it like a double-click
                    return True, ""
            return False, "I couldn't find CapCut on this PC. Open it from the Start menu"
    except OSError as e:
        return False, f"CapCut didn't start ({e})"
    return False, "I can't start CapCut on this computer"


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


def fill_scale(w, h):
    """CapCut fits a photo inside the frame at scale 1. This is the scale that fills the frame instead."""
    if not w or not h:
        return 1.0
    cw, ch = CANVAS
    fit = min(cw / w, ch / h)
    fill = max(cw / w, ch / h)
    return round(fill / fit, 6)


def song_length(path):
    """Length of the song in seconds: read from the file itself (sound.py, the same on a Mac and a PC, and the
    same number the Mac's own afinfo gives for WAV, AIFF, MP3 and Apple's M4A); then afinfo, ffprobe if
    present, or a wav header, for anything sound.py cannot read."""
    p = str(path)
    d = sound.duration(p)
    if d:
        return float(f"{d:f}")      # to the microsecond, written the way afinfo writes it, so records match a Mac's
    if shutil.which("afinfo"):  # pc-ok: only a Mac has afinfo; anything sound.py could not read
        r = subprocess.run(["afinfo", p], capture_output=True, encoding="utf-8", errors="replace")  # pc-ok: only a Mac has afinfo
        m = re.search(r"estimated duration:\s*([\d.]+)", r.stdout)
        if m:
            return float(m.group(1))
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", p], capture_output=True, encoding="utf-8", errors="replace")
        try:
            return float(r.stdout.strip())
        except ValueError:
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


def build(plan, parts, platform):
    draft, meta, P = parts
    d = copy.deepcopy(draft)
    if platform:
        d.update(copy.deepcopy(platform))
    elif os.name == "nt":
        # unproven on a real PC: no project of theirs to copy from, and the pieces were taken from CapCut on a
        # Mac, so at least say which computer this is. CapCut for Windows' own values are not known yet.
        import platform as _platform
        for k in ("platform", "last_modified_platform"):
            if isinstance(d.get(k), dict):
                d[k] = dict(d[k], os="windows", os_version=_platform.version())
    mats = d["materials"]
    draft_id = uid()
    d["id"] = draft_id
    d["name"] = plan["name"]
    d["canvas_config"] = {"background": None, "height": CANVAS[1], "ratio": "original", "width": CANVAS[0]}
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
        w, h = ph.get("w") or 0, ph.get("h") or 0
        if not (w and h):
            w, h = photo_size(ph["path"])
        mat = copy.deepcopy(P["photo_material"])
        mat.update({"id": uid(), "path": native(ph["path"]), "material_name": Path(ph["path"]).stem,
                    "width": w, "height": h, "duration": PHOTO_LENGTH, "type": "photo"})
        mats["videos"].append(mat)
        refs = []
        for ex in P["photo_extras"]:
            item = copy.deepcopy(ex["item"])
            item["id"] = uid()
            mats[ex["list"]].append(item)
            refs.append(item["id"])
        seg = copy.deepcopy(P["photo_segment"])
        s = ph.get("scale") or (fill_scale(w, h) if ph.get("fill", True) else 1.0)
        target = tr_f(ph["start_f"], ph["dur_f"], fps) if "start_f" in ph else tr(ph["start"], ph["dur"])
        seg.update({"id": uid(), "material_id": mat["id"], "extra_material_refs": refs,
                    "target_timerange": target, "source_timerange": {"start": 0, "duration": target["duration"]}})
        seg["clip"]["scale"] = {"x": s, "y": s}
        seg["uniform_scale"] = {"on": True, "value": 1.0}
        vtrack["segments"].append(seg)
        end = max(end, ph["start"] + ph["dur"])
        end_us = max(end_us, target["start"] + target["duration"])
        meta_items.append({"duration": 5 * US, "extra_info": Path(ph["path"]).name, "file_Path": native(ph["path"]),
                           "height": h, "width": w, "metetype": "photo", "t": t0})
    d["tracks"].append(vtrack)

    # the hook, as plain CapCut text they restyle with CapCut's own text styles
    hook = plan.get("hook")
    if hook and hook.get("text"):
        tm = copy.deepcopy(P["text_material"])
        tm["id"] = uid()
        if os.name == "nt" and str(tm.get("font_path", "")).startswith("/Applications/"):
            tm["font_path"] = _windows_default_font()        # unproven on a real PC (row I4)
        content = json.loads(tm["content"])
        style = content["styles"][0]
        style["range"] = [0, len(hook["text"])]
        content["styles"] = [style]
        content["text"] = hook["text"]
        tm["content"] = json.dumps(content, ensure_ascii=False)
        mats["texts"].append(tm)
        ts = copy.deepcopy(P["text_segment"])
        hook_us = us_f(hook["dur_f"], fps) if hook.get("dur_f") else int(round(hook.get("dur", 2.5) * US))
        ts.update({"id": uid(), "material_id": tm["id"], "target_timerange": {"start": 0, "duration": min(hook_us, end_us)}})
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

    m = copy.deepcopy(meta)
    m["draft_id"] = draft_id
    m["draft_name"] = plan["name"]
    m["tm_duration"] = d["duration"]
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
    return d, m


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


def write_json(path, obj):
    tmp = path.with_name(path.name + ".studio-tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
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


def write(plan, store, ignore_open=False):
    """Returns (project folder, draft). With CapCut open, only the new project's own folder is written and
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
    if missing:
        say("STOP: these files are not where the plan says: " + ", ".join(missing[:5]))
        sys.exit(2)

    write.left_to_capcut, write.note = is_open, None
    write.waiting = write.listed = False
    fold = folder_name(store, plan["name"])
    dest = store / fold
    try:
        dest.mkdir()
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
        kept = dest / src.name
        try:
            shutil.copyfile(src, kept)
            same = kept.stat().st_size == src.stat().st_size and file_hash(kept) == file_hash(src)
        except OSError as e:
            same = False
            say(f"STOP: I couldn't put the song into the CapCut project ({e}).")
        if not same:
            try:
                kept.unlink(missing_ok=True)       # our own half-made copy, in the folder we just made
                dest.rmdir()
            except OSError:
                pass
            say("STOP: the song's copy inside the CapCut project didn't match the original, so I made nothing. Try again.")
            sys.exit(2)
        plan = dict(plan, song=dict(song, path=native(kept), name=song.get("name") or src.name, original=str(src)))
    draft, meta = build(plan, load_parts(), their_platform(store))
    draft["name"] = meta["draft_name"] = fold
    t = now_us()
    meta.update({"draft_fold_path": native(dest), "draft_root_path": native(store),
                 "tm_draft_create": t, "tm_draft_modified": t})
    write_json(dest / draft_file_name(), draft)
    write_json(dest / "draft_meta_info.json", meta)
    (dest / "draft_settings").write_text(
        f"[General]\ndraft_create_time={t // US}\ndraft_last_edit_time={t // US}\nreal_edit_keys=0\nreal_edit_seconds=0\n",
        encoding="utf-8")
    cover = dest / "draft_cover.jpg"
    first = plan["photos"][0]["path"] if plan["photos"] else None
    if first and pictures.use_sips():
        subprocess.run(["sips", "-Z", "720", "-s", "format", "jpeg", first, "--out", str(cover)], capture_output=True)  # pc-ok: Mac branch
    elif first and pictures.make_jpeg(first, cover, 720):
        pass                                 # a PC: the same small cover, made with Pillow
    elif first and str(first).lower().endswith((".jpg", ".jpeg")) and os.path.getsize(first) < 4_000_000:
        shutil.copyfile(first, cover)

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


def _waiting(store):
    try:
        got = _read_json(store / WAITING)
        return [x for x in got if isinstance(x, dict) and x.get("draft_id")] if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def _wait(store, entry):
    """Note a reel that isn't in CapCut's list yet, to add it next time. True when noted."""
    try:
        write_json(store / WAITING, [x for x in _waiting(store) if x.get("draft_id") != entry["draft_id"]] + [entry])
        return True
    except OSError:
        return False


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
    for e in sorted(late, key=lambda w: w.get("tm_draft_create") or 0) + list(entries):   # oldest first, so
        if e["draft_id"] not in have:                                                      # the newest ends on top
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


def open_capcut(store=None):
    """Start CapCut, first adding any reel still waiting to its list (made while CapCut was open on a PC, or
    while the list couldn't be saved) when CapCut is surely closed. (True, words) or (False, "STOP: ...")."""
    store = Path(store) if store else default_store()
    added = ""
    if _waiting(store) and capcut_open() is False:
        ok, why = add_to_list(store, [])
        added = (" The reel that was waiting is in its list now." if ok else
                 " " + (why or "I still couldn't add the waiting reel to CapCut's list of projects."))
    ok, why = launch()
    return (True, "Opened CapCut. The newest project is at the top of its list." + added) if ok else (False, f"STOP: {why}.")


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
    a = ap.parse_args()
    store = Path(a.store).expanduser() if a.store else default_store()
    if a.cmd == "open":
        ok, words = open_capcut(store)
        say(words)
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
    n = len(plan["photos"])
    say(f"Made \"{dest.name}\" in CapCut: {n} photos, {secs:.1f} seconds"
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
