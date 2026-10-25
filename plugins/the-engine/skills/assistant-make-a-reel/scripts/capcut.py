#!/usr/bin/env python3
"""The Studio by Horizon Found. Writes a reel plan into a new CapCut project, so the
photographer opens CapCut and finds it there: their photos on the beat of their song,
hard cuts, nothing added. The look (text styles, filters, templates) is theirs to
add in CapCut.

    python3 capcut.py where                     where CapCut keeps projects, and whether it is open
    python3 capcut.py write --plan reel.json    make the project (CapCut must be closed)
        [--store <projects folder>]             somewhere else (tests)
        [--ignore-open]                         tests only: skip the "is CapCut open" check

The plan (reel.py writes it):
    {"name": "Black-sand beach reel",
     "photos": [{"path": "/…/x.jpg", "start": 0.0, "dur": 2.4}, …],      seconds on the reel
     "song": {"path": "/…/song.m4a", "from": 41.3, "dur": 13.2, "fade_out": 0.6} or null,
     "hook": {"text": "…", "dur": 2.4} or null}

How: every CapCut project is a folder of plain files. This builds one from pieces
CapCut itself wrote (references/capcut/), never edits a project they made, never
overwrites a folder, and adds the new project to CapCut's list of projects after
keeping a copy of that list. CapCut must be closed while it writes, or CapCut may
write its old list back over the new one on quit.

Exit codes: 0 made · 2 stop (no CapCut found, a photo or the song missing) · 8 CapCut is open.
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

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "references" / "capcut"
US = 1_000_000
CANVAS = (1080, 1920)
PHOTO_LENGTH = 10_800_000_000   # CapCut gives a still photo three hours of "length" to cut from


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
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return Path.home() / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def capcut_open():
    """True if CapCut is running, False if not, None if we cannot tell."""
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True, text=True)
            return r.returncode == 0
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe"], capture_output=True, text=True)
            return "CapCut.exe" in r.stdout
    except OSError:
        return None
    return None


def draft_file_name():
    return "draft_content.json" if os.name == "nt" else "draft_info.json"


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
        d = json.loads(best[1].read_text(encoding="utf-8"))
        return {k: d[k] for k in ("platform", "last_modified_platform", "version", "new_version") if k in d}
    except (OSError, ValueError):
        return None   # an unreadable project (a newer CapCut may lock its files) just means we use ours


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
    if shutil.which("sips"):  # HEIC, TIFF and anything else, on a Mac
        r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", f], capture_output=True, text=True)
        w = re.search(r"pixelWidth:\s*(\d+)", r.stdout)
        h = re.search(r"pixelHeight:\s*(\d+)", r.stdout)
        if w and h:
            return int(w.group(1)), int(h.group(1))
    return 0, 0


def fill_scale(w, h):
    """CapCut fits a photo inside the frame at scale 1. This is the scale that fills the frame instead."""
    if not w or not h:
        return 1.0
    cw, ch = CANVAS
    fit = min(cw / w, ch / h)
    fill = max(cw / w, ch / h)
    return round(fill / fit, 6)


def song_length(path):
    """Length of the song in seconds, from the Mac's own afinfo, ffprobe if present, or a wav header."""
    p = str(path)
    if shutil.which("afinfo"):
        r = subprocess.run(["afinfo", p], capture_output=True, text=True)
        m = re.search(r"estimated duration:\s*([\d.]+)", r.stdout)
        if m:
            return float(m.group(1))
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", p], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    if p.lower().endswith(".wav"):
        import wave
        with wave.open(p, "rb") as w:
            return w.getnframes() / w.getframerate()
    return 0.0


# ---------------------------------------------------------------- building it

def load_parts():
    t = json.loads((REF / "draft_info.template.json").read_text(encoding="utf-8"))
    m = json.loads((REF / "draft_meta_info.template.json").read_text(encoding="utf-8"))
    p = json.loads((REF / "parts.json").read_text(encoding="utf-8"))
    return t, m, p


def tr(start, dur):
    return {"start": int(round(start * US)), "duration": int(round(dur * US))}


def build(plan, parts, platform):
    draft, meta, P = parts
    d = copy.deepcopy(draft)
    if platform:
        d.update(copy.deepcopy(platform))
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
    for ph in plan["photos"]:
        w, h = ph.get("w") or 0, ph.get("h") or 0
        if not (w and h):
            w, h = photo_size(ph["path"])
        mat = copy.deepcopy(P["photo_material"])
        mat.update({"id": uid(), "path": ph["path"], "material_name": Path(ph["path"]).stem,
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
        seg.update({"id": uid(), "material_id": mat["id"], "extra_material_refs": refs,
                    "target_timerange": tr(ph["start"], ph["dur"]), "source_timerange": tr(0, ph["dur"])})
        seg["clip"]["scale"] = {"x": s, "y": s}
        seg["uniform_scale"] = {"on": True, "value": 1.0}
        vtrack["segments"].append(seg)
        end = max(end, ph["start"] + ph["dur"])
        meta_items.append({"duration": 5 * US, "extra_info": Path(ph["path"]).name, "file_Path": ph["path"],
                           "height": h, "width": w, "metetype": "photo", "t": t0})
    d["tracks"].append(vtrack)

    # the hook, as plain CapCut text they restyle with CapCut's own text styles
    hook = plan.get("hook")
    if hook and hook.get("text"):
        tm = copy.deepcopy(P["text_material"])
        tm["id"] = uid()
        content = json.loads(tm["content"])
        style = content["styles"][0]
        style["range"] = [0, len(hook["text"])]
        content["styles"] = [style]
        content["text"] = hook["text"]
        tm["content"] = json.dumps(content, ensure_ascii=False)
        mats["texts"].append(tm)
        ts = copy.deepcopy(P["text_segment"])
        ts.update({"id": uid(), "material_id": tm["id"], "target_timerange": tr(0, min(hook.get("dur", 2.5), end))})
        tt = copy.deepcopy(P["text_track"])
        tt.update({"id": uid(), "segments": [ts]})
        d["tracks"].append(tt)

    # the song, starting where it picks up, ending with the last photo
    song = plan.get("song")
    if song:
        length = song.get("length") or song_length(song["path"])
        dur = min(end, max(0.0, length - song.get("from", 0.0))) if length else end
        aid = uid()
        mats["audios"].append({
            "app_id": 0, "category_id": "", "category_name": "local", "check_flag": 1,
            "copyright_limit_type": "none", "duration": int(round((length or end) * US)), "effect_id": "",
            "formula_id": "", "id": aid, "intensifies_path": "", "is_ai_clone_tone": False,
            "is_text_edit_overdub": False, "is_ugc": False, "local_material_id": aid.lower(),
            "music_id": aid.lower(), "name": Path(song["path"]).name, "path": song["path"], "query": "",
            "request_id": "", "resource_id": "", "search_id": "", "source_from": "", "source_platform": 0,
            "team_id": "", "text_id": "", "tone_category_id": "", "tone_category_name": "", "tone_effect_id": "",
            "tone_effect_name": "", "tone_platform": "", "tone_second_category_id": "",
            "tone_second_category_name": "", "tone_speaker": "", "tone_type": "", "type": "extract_music",
            "video_id": "", "wave_points": []})
        refs = []
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
        aseg.update({"id": uid(), "material_id": aid, "extra_material_refs": refs, "clip": None,
                     "hdr_settings": None, "uniform_scale": None, "render_index": 0, "track_render_index": 0,
                     "target_timerange": tr(0, dur), "source_timerange": tr(song.get("from", 0.0), dur),
                     "volume": 1.0, "enable_lut": False, "enable_adjust": False})
        d["tracks"].append({"attribute": 0, "flag": 0, "id": uid(), "is_default_name": True, "name": "",
                            "segments": [aseg], "type": "audio"})
        meta_items.append({"duration": int(round((length or end) * US)), "extra_info": Path(song["path"]).name,
                           "file_Path": song["path"], "height": 0, "width": 0, "metetype": "music", "t": t0})

    d["duration"] = int(round(end * US))
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


def folder_name(store, name):
    base = re.sub(r"[^\w\- ]+", "", name).strip() or "Studio reel"
    cand, n = base, 2
    while (store / cand).exists():
        cand = f"{base} {n}"
        n += 1
    return cand


def write_json(path, obj):
    tmp = path.with_name(path.name + ".studio-tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def native(p):
    """A path the way CapCut writes it on this computer."""
    return str(p).replace("\\", "/") if os.name == "nt" else str(p)


def write(plan, store, ignore_open=False):
    if not ignore_open and capcut_open():
        say("CapCut is open. Close it first (CapCut menu, Quit CapCut), then tell me and I'll finish.")
        sys.exit(8)
    if not store.is_dir():
        say(f"STOP: I can't find CapCut's projects folder ({store}). Is CapCut installed, and has it been opened once?")
        sys.exit(2)
    missing = [p["path"] for p in plan["photos"] if not Path(p["path"]).is_file()]
    if plan.get("song") and not Path(plan["song"]["path"]).is_file():
        missing.append(plan["song"]["path"])
    if missing:
        say("STOP: these files are not where the plan says: " + ", ".join(missing[:5]))
        sys.exit(2)

    draft, meta = build(plan, load_parts(), their_platform(store))
    fold = folder_name(store, plan["name"])
    dest = store / fold
    dest.mkdir()
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
    if first and shutil.which("sips"):
        subprocess.run(["sips", "-Z", "720", "-s", "format", "jpeg", first, "--out", str(cover)], capture_output=True)
    elif first and str(first).lower().endswith((".jpg", ".jpeg")) and os.path.getsize(first) < 4_000_000:
        shutil.copyfile(first, cover)

    # add it to CapCut's list of projects, keeping a copy of the list as it was
    root = store / "root_meta_info.json"
    if root.is_file():
        r = json.loads(root.read_text(encoding="utf-8"))
        first_backup = store / "root_meta_info.before-studio.json"
        if not first_backup.exists():
            shutil.copyfile(root, first_backup)
        shutil.copyfile(root, store / "root_meta_info.studio-backup.json")
    else:
        r = {"all_draft_store": [], "draft_ids": 0, "root_path": native(store)}
    entry = dict(ROOT_ENTRY_KEYS)
    entry.update({"draft_cover": native(cover), "draft_fold_path": native(dest), "draft_id": draft["id"],
                  "draft_json_file": native(dest / draft_file_name()), "draft_name": fold,
                  "draft_root_path": native(store), "tm_draft_create": t, "tm_draft_modified": t,
                  "tm_duration": draft["duration"]})
    r.setdefault("all_draft_store", []).insert(0, entry)
    r["draft_ids"] = int(r.get("draft_ids") or 0) + 1
    write_json(root, r)
    return dest, draft


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("where")
    w.add_argument("--store")
    wr = sub.add_parser("write")
    wr.add_argument("--plan", required=True)
    wr.add_argument("--store")
    wr.add_argument("--ignore-open", action="store_true")
    a = ap.parse_args()
    store = Path(a.store).expanduser() if a.store else default_store()
    if a.cmd == "where":
        open_ = capcut_open()
        n = len([p for p in store.iterdir() if p.is_dir() and not p.name.startswith(".")]) if store.is_dir() else 0
        plat = their_platform(store) if store.is_dir() else None
        ver = (plat or {}).get("platform", {}).get("app_version", "unknown")
        say(json.dumps({"store": str(store), "found": store.is_dir(), "projects": n, "capcut_version": ver,
                        "capcut_open": open_}, indent=1))
        return
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    dest, draft = write(plan, store, a.ignore_open)
    secs = draft["duration"] / US
    n = len(plan["photos"])
    say(f"Made \"{dest.name}\" in CapCut: {n} photos, {secs:.1f} seconds"
        + (f", on the beat of {Path(plan['song']['path']).name}" if plan.get("song") else "")
        + ". Open CapCut and it's at the top of your projects.")


if __name__ == "__main__":
    main()
