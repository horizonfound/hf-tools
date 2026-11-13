#!/usr/bin/env python3
"""Checks on a talking reel made in CapCut: capcut.build_talking (the project), talking_make.py (the maker) and
the make's own job in talking_rec.py (Nicole's handoffs v23 and v24, stage D of the build, done our way).

    python3 tests/talking_capcut_check.py

Runs in a throwaway folder with its own pretend Assistant (STUDIO_HOME), its own pretend CapCut projects folder
(--store, --ignore-open; in the job, ASSISTANT_TEST_TALKING_STORE) and a pretend home folder, so CapCut is never
started or asked after and no project of anyone's is near. Starts no server. Makes and plays no video: the only
video is the tiny tests/fixtures/loud-tone-3s.mp4, copied in and only ever read by its header (one copy has the
"turned" mark written into its header by this test, the way a phone stores a video held upright).

What it cannot prove: that CapCut opens what is written. Nobody has opened one of these projects yet.

Every line must say PASS (or SKIP). Python 3.9, standard library only, a Mac or a PC.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "the-engine" / "skills"
SCRIPTS = SKILLS / "studio-manager" / "scripts"
REEL = SKILLS / "assistant-make-a-reel" / "scripts"
MAKER = REEL / "talking_make.py"
CLIP = ROOT / "tests" / "fixtures" / "loud-tone-3s.mp4"
HERS = ROOT.parent / "hf-tools" / "reference-private" / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker"
if not HERS.is_dir():
    HERS = ROOT / "reference-private" / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker"
fails = 0

REAL = Path.home() / (".stu" + "dio")       # only ever listed, to prove this test leaves it alone
REAL_CAPCUT = Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def listing(d):
    try:
        return sorted((p.name, p.stat().st_mtime_ns) for p in d.iterdir())
    except OSError:
        return None


REAL_BEFORE, CAPCUT_BEFORE = listing(REAL), listing(REAL_CAPCUT)

TMP = Path(tempfile.mkdtemp(prefix="talking-capcut-check-")).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
CONTENT = HOME / "Your Content"
STORE = TMP / "capcut store"
os.environ["STUDIO_HOME"] = str(STUDIO)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["ASSISTANT_TEST_TALKING_STORE"] = str(STORE)       # the job's maker writes here, and never asks after CapCut
os.environ["HOME"] = os.environ["USERPROFILE"] = str(TMP / "pretend home")   # so "CapCut's own folder" is a pretend one too
os.environ["LOCALAPPDATA"] = str(TMP / "pretend home" / "AppData" / "Local")
ENV = dict(os.environ)
US = 1_000_000


def check(name, cond, got=None):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond or got is None else f"\n        got: {got!r}"))
    fails += 0 if cond else 1


def skip(name, why):
    print(f"SKIP  {name} ({why})")


def png(path, w, h):
    """A plain grey PNG of that size, written by hand (nothing installed)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x80" * w for _ in range(h))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def turned(src, dst):
    """A copy of a video with the quarter-turn mark in its header: how a phone stores a video held upright."""
    b = bytearray(Path(src).read_bytes())
    done, at = 0, 0
    while True:
        at = b.find(b"tkhd", at)
        if at < 0:
            break
        body = at + 4
        mo = body + (52 if b[body] == 1 else 40)
        if struct.unpack_from(">II", b, mo + 36) != (0, 0):          # the picture's track (the sound's has no size)
            struct.pack_into(">9i", b, mo, 0, 0x10000, 0, -0x10000, 0, 0, 0, 0, 0x40000000)
            done += 1
        at += 4
    Path(dst).write_bytes(bytes(b))
    return done


def maker(*args, env=None):
    return subprocess.run([sys.executable, str(MAKER), "make", *args], capture_output=True, text=True, encoding="utf-8", env=env or ENV)


def projects():
    return sorted(p.name for p in STORE.iterdir()) if STORE.is_dir() else []


def draft_of(name):
    d = STORE / name
    f = d / ("draft_content.json" if os.name == "nt" else "draft_info.json")
    return json.loads(f.read_text(encoding="utf-8"))


def frame(us):
    """Is this time on a whole 30 fps frame, the way capcut.py writes one?"""
    return int(round(round(us * 30 / US) * US / 30.0)) == us


def end(t):
    return t["start"] + t["duration"]


def near(a, b, tol=2e-6):
    return abs(a - b) <= tol


# ---- the zoom checks' own fixed pretend plan (Nov 13): seven pieces one after another on the reel. Pieces 1, 2, 3
# are zoom 0 (the middle one at 1.5x; the last after a closed pause in the video), piece 5 is zoom 1.
# tests/fixtures/talking-zoom-before.json is what the builder made of it BEFORE zooms got an amount and a pace.
ZOOM_BEFORE = ROOT / "tests" / "fixtures" / "talking-zoom-before.json"
ID = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")


def zoom_pieces():
    spec = [(1.0, 2.0, 1.0, None), (2.0, 3.3, 1.0, 0), (3.3, 4.8, 1.5, 0), (6.0, 7.7, 1.0, 0), (7.7, 8.4, 1.0, None),
            (9.0, 11.6, 1.0, 1), (11.6, 12.5, 1.0, None)]
    out, at = [], 0.0
    for k, (a, b, sp, z) in enumerate(spec):
        dur = round((b - a) / sp, 3)
        out.append({"from": a, "to": b, "speed": sp, "zoom": z, "sentence": k, "at": round(at, 3), "dur": dur})
        at += dur
    return out


def zoom_plan(zooms):
    return {"name": "Zoom check talking reel", "photos": [], "song": None, "hook": None, "files": ["/nowhere/talk.mp4"], "cover": None,
            "video": {"path": "/nowhere/talk.mp4", "w": 1080, "h": 1920, "length": 60.0},
            "pieces": zoom_pieces(), "zooms": zooms, "shots": [], "captions": None, "cap_pos": None, "cap_size": 1}


def scrub(x, seen):
    """A project with every id replaced by its order of appearance, so two builds can be compared whole."""
    if isinstance(x, dict):
        return {k: scrub(v, seen) for k, v in x.items()}
    if isinstance(x, list):
        return [scrub(v, seen) for v in x]
    if isinstance(x, str) and ID.match(x):
        return "id-%d" % seen.setdefault(x, len(seen))
    return x


def zoom_layer(capcut, parts, *zooms):
    d, _ = capcut.build_talking(zoom_plan(list(zooms)), parts, None)
    return d["tracks"][0]["segments"]


def keys_of(seg):
    """A piece's zoom keyframes as (seconds on the reel, value); [] for none."""
    out = []
    for k in (seg.get("common_keyframes") or [{"keyframe_list": []}])[0]["keyframe_list"]:
        t = seg["target_timerange"]["start"] + (k["time_offset"] - seg["source_timerange"]["start"]) / seg["speed"]
        out.append((t / US, k["values"][0]))
    return out


def make_kit(folder, photos):
    k = CONTENT / folder
    (k / ".kit").mkdir(parents=True)
    (k / "Photos").mkdir()
    (k / "Talking").mkdir()
    (k / "Footage").mkdir()
    rows = []
    for i, (w, h, sized) in enumerate(photos, 1):
        png(k / "Photos" / f"IMG_{i:04d}.png", w, h)
        rows.append(dict({"n": i, "file": f"IMG_{i:04d}.png"}, **({"w": w, "h": h} if sized else {})))
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": folder.split(" ", 1)[1]}), encoding="utf-8")
    (k / ".kit" / "sheet.json").write_text(json.dumps({"photos": rows}), encoding="utf-8")
    return k


def words_every(n, step, long, pause_at=None, ends=()):
    out = []
    for i in range(n):
        t = i * step + (1.0 if pause_at is not None and i >= pause_at else 0.0)
        out.append({"w": f"w{i}" + ("." if i in ends else ""), "start": round(t, 3), "end": round(t + long, 3), "conf": 0.9})
    return out


SHOOT, SHORT = "2026-09-23 Hannah & Zoë's beach", "Hannah & Zoë's beach"
# six photos: 1 to 3 and 5 tall (40x60), 6 wide (60x40), 4 tall with no size on the sheet (read from the file)
PHOTOS = [(40, 60, True), (40, 60, True), (40, 60, True), (40, 60, False), (40, 60, True), (60, 40, True)]

try:
    STUDIO.mkdir(parents=True)
    STORE.mkdir()
    (STUDIO / "studio.json").write_text(json.dumps({"posts": {"home": str(HOME)}}), encoding="utf-8")
    KIT = make_kit(SHOOT, PHOTOS)
    TALK = KIT / "Talking" / "my talk.mp4"
    check("the test's own turned clip has the quarter-turn mark in its header", turned(CLIP, TALK) == 1)
    shutil.copyfile(CLIP, KIT / "Footage" / "b-roll.mp4")

    sys.path.insert(0, str(SCRIPTS))
    sys.path.insert(0, str(REEL))
    import talking_rec as TR      # noqa: E402
    import arrange                # noqa: E402
    import capcut                 # noqa: E402
    import talking_make as TM     # noqa: E402
    import video                  # noqa: E402
    import capcut_even            # noqa: E402  (beside this file)
    check("the test's own Assistant folder is the scratch one", Path(arrange.HOME) == STUDIO, str(arrange.HOME))
    check("the pretend CapCut is nowhere near the real one", capcut.default_store() != REAL_CAPCUT and str(TMP) in str(capcut.default_store()),
          str(capcut.default_store()))
    f = video.facts(TALK)
    check("the turned clip reads as a phone video held upright: shown 180 wide, 320 tall (9:16), stored the other way",
          (f["w"], f["h"], f["stored_w"], f["stored_h"], f["rotation"]) == (180, 320, 320, 180, 90), f)

    # ================= photo reels are exactly what they were =================
    if os.name == "nt":
        skip("a photo reel's project is the same as before the talking builder went in", "a Mac's project; a PC adds its own name and font")
    else:
        bad, n = capcut_even.compare()
        check(f"today's photo reels: {n} projects (song, hook, clip, CapCut's own song, plain seconds) are what capcut.py wrote "
              f"before its helpers were lifted out, ids evened", not bad and n == 8, bad)

    # ================= her numbers =================
    W, H = capcut.CANVAS
    check("cover_scale is the photo reel's own fill sum under another name (one sum, not two)", capcut.fill_scale is capcut.cover_scale)
    check("cover_scale: a 9:16 picture is 1; a wide 16:9 one fills at 3.160494; a tall 2:3 photo at 1.185185",
          (capcut.cover_scale(1080, 1920), capcut.cover_scale(320, 180), capcut.cover_scale(4000, 6000)) == (1.0, 3.160494, 1.185185))
    check("fit_scale: canvas pixels per picture pixel at CapCut's scale 1", near(capcut.fit_scale(4000, 6000), 0.27) and near(capcut.fit_scale(6000, 4000), 0.18))
    check("box_scale: a tall and a wide photo made 760.32 px across are both 0.704",
          capcut.box_scale(4000, 6000, 0.704 * W) == 0.704 and capcut.box_scale(6000, 4000, 0.704 * W) == 0.704)
    check("canvas_xy: the middle is (0, 0), the top left (-1, 1), the bottom right (1, -1)",
          (capcut.canvas_xy(540, 960), capcut.canvas_xy(0, 0), capcut.canvas_xy(1080, 1920)) == ({"x": 0.0, "y": 0.0}, {"x": -1.0, "y": 1.0}, {"x": 1.0, "y": -1.0}))
    check("Center, before they move it: {0.5, 0.44, 0.704}, for a tall and for a wide photo",
          capcut.default_place("center", 4000, 6000) == capcut.default_place("center", 6000, 4000) == {"x": 0.5, "y": 0.44, "w": 0.704})
    ct, cw_ = capcut.default_place("corner", 4000, 6000), capcut.default_place("corner", 6000, 4000)
    # hers: x = 1 - 0.046 - 0.176; y = 0.073 + h/2 with h = 0.352 * 9/16 * photo height / width
    check("Small corner, a tall photo: x 0.778, y 0.073 + 0.297/2 = 0.2215, w 0.352", near(ct["x"], 0.778) and near(ct["y"], 0.2215) and ct["w"] == 0.352, ct)
    check("Small corner, a wide photo: x 0.778, y 0.073 + 0.132/2 = 0.139, w 0.352", near(cw_["x"], 0.778) and near(cw_["y"], 0.139) and cw_["w"] == 0.352, cw_)
    me = capcut.ME_DEFAULT
    check("themselves in the corner, before they move: at CapCut's (-0.547407, -0.5775), 0.36 wide",
          capcut.canvas_xy(me["x"] * W, me["y"] * H) == {"x": -0.547407, "y": -0.5775} and me["w"] == 0.36, capcut.canvas_xy(me["x"] * W, me["y"] * H))
    check("a punch in is 1.15 and a slow zoom ends at 1.12", (capcut.PUNCH, capcut.ZOOM_TO) == (1.15, 1.12))
    check("a size nobody could read never divides by nothing: scale 1, and a corner photo still gets a place",
          capcut.cover_scale(0, 0) == 1.0 and capcut.box_scale(0, 0, 300) == 1.0 and capcut.fit_scale(0, 5) == 0.0
          and near(capcut.default_place("corner", 0, 0)["y"], 0.073 + 0.352 * 0.5625 / 2))
    parts = capcut.load_parts()
    kf = parts[2]["scale_keyframe"]
    check("the scale keyframe piece: her twelve names, and parts.json says it was never seen written by CapCut",
          sorted(kf["property"]) == ["id", "keyframe_list", "material_id", "property_type"] and kf["property"]["property_type"] == "KFTypeScaleX"
          and sorted(kf["keyframe"]) == ["curveType", "graphID", "id", "left_control", "right_control", "string_value", "time_offset", "values"]
          and kf["keyframe"]["curveType"] == "Line" and "not yet seen written by CapCut" in parts[2]["_about"])

    # ================= the big scene: a 60 s talk (the 3 s clip's header, its length said to be 60 s) =================
    # 40 words, one every half second, 0.3 s long; a full second of quiet before word 30; sentences end at 9, 19, 29, 39.
    WORDS = words_every(40, 0.5, 0.3, pause_at=30, ends=(9, 19, 29, 39))
    TR.put_words(KIT, TALK.name, video.key(TALK), WORDS, {"dur": 60.0, "w": 180, "h": 320}, {"how": "pretend", "ondevice": True})
    EDIT = {
        "cut": [[0, 1], [12, 13]], "splits": [5],
        "speeds": [{"a": 20, "b": 23, "v": 1.5}],
        "zooms": [{"a": 2, "b": 7, "kind": "zoom"}, {"a": 14, "b": 16, "kind": "punch"}],
        "shots": [
            {"a": 3, "b": 4, "ns": [1, 2, 3], "spot": "full", "pos": None, "me": None},                 # three photos flashing
            {"a": 8, "b": 9, "ns": [4], "spot": "pip", "pos": None, "me": None},                       # them in the corner, where it starts
            {"a": 10, "b": 11, "ns": [5], "spot": "center", "pos": None, "me": None},                  # a tall photo, Center
            {"a": 14, "b": 15, "ns": [6], "spot": "corner", "pos": None, "me": None},                  # a wide photo, Small corner
            {"a": 17, "b": 19, "ns": [2], "spot": "corner", "pos": {"x": 0.3, "y": 0.6, "w": 0.5}, "me": None},   # moved and resized
            {"a": 20, "b": 25, "ns": [], "v": "b-roll.mp4", "from": 1.0, "spot": "pip", "pos": None, "me": {"x": 0.7, "y": 0.2, "w": 0.25}},
            {"a": 30, "b": 31, "ns": [], "v": "b-roll.mp4", "from": 2.95, "spot": "center", "pos": None, "me": None},   # starts 0.05 s from its end
        ],
        "captions": True, "cap_pos": None, "cap_size": None,
    }
    TR.change(KIT, lambda rec: rec.update(json.loads(json.dumps(EDIT))))
    eng = TR._engine()
    rec = TR.load(KIT)
    pcs = eng.pieces(rec)
    real_size = TM._shown_size
    TM._shown_size = lambda path, f=None: (1080, 1920, 60.0) if Path(path) == TALK else real_size(path, f)     # this scene only
    plan = TM.plan_for(KIT)
    TM._shown_size = real_size
    check("the plan: the short name and \"talking reel\"; every file it points at named once; a photo for the cover",
          plan["name"] == f"{SHORT} talking reel" and plan["files"] == sorted(set(plan["files"])) and str(TALK) in plan["files"]
          and str(KIT / "Footage" / "b-roll.mp4") in plan["files"] and len(plan["files"]) == 8 and plan["cover"] == str(KIT / "Photos" / "IMG_0001.png"),
          (plan["name"], len(plan["files"]), plan["cover"]))
    check("the plan: a photo with no size on the sheet has its size read from the file",
          plan["shots"][1]["photos"] == [{"path": str(KIT / "Photos" / "IMG_0004.png"), "w": 40, "h": 60}], plan["shots"][1])
    check("the plan: each stretch is where talking.py's own shot_spans puts it (stretches that don't overlap)",
          [(x["at"], x["dur"]) for x in plan["shots"]] == [(s["at"], s["dur"]) for s in eng.shot_spans(rec, pcs)])
    d, m = capcut.build_talking(plan, parts, None)
    mats = d["materials"]
    tracks = d["tracks"]
    check("layers, bottom to top: their talking video, the photos and videos, the corner copies, the captions",
          [t["type"] for t in tracks] == ["video", "video", "video", "text"], [t["type"] for t in tracks])
    main, layer, copies, caps = tracks
    check("...the main layer is flag 0 at render 0; the two above are flag 2, numbered up (render 2 on layer 1, render 3 on layer 2)",
          main["flag"] == 0 and {(s["render_index"], s["track_render_index"]) for s in main["segments"]} == {(0, 0)}
          and layer["flag"] == 2 and {(s["render_index"], s["track_render_index"]) for s in layer["segments"]} == {(2, 1)}
          and copies["flag"] == 2 and {(s["render_index"], s["track_render_index"]) for s in copies["segments"]} == {(3, 2)})
    check("...the captions are text at CapCut's own caption height (render 14000), above everything", {s["render_index"] for s in caps["segments"]} == {14000})
    talk_mats = [x for x in mats["videos"] if x["path"] == capcut.native(TALK)]
    check("ONE material for their talking video, a video with its sound and its real length",
          len(talk_mats) == 1 and talk_mats[0]["type"] == "video" and talk_mats[0]["has_audio"] is True and talk_mats[0]["duration"] == 60 * US
          and (talk_mats[0]["width"], talk_mats[0]["height"]) == (1080, 1920), [(x["type"], x["duration"]) for x in talk_mats])
    vid = talk_mats[0]["id"]
    check("...every piece and every corner copy is a part of it", {s["material_id"] for s in main["segments"] + copies["segments"]} == {vid})
    check("as many main clips as talking.py's pieces, in play order, one after another with no gap",
          len(main["segments"]) == len(pcs) and main["segments"][0]["target_timerange"]["start"] == 0
          and all(end(a["target_timerange"]) == b["target_timerange"]["start"] for a, b in zip(main["segments"], main["segments"][1:])))
    every = [s["target_timerange"] for t in tracks for s in t["segments"]]
    check("every time on the reel, on every layer, is on a whole frame", all(frame(t["start"]) and frame(end(t)) for t in every),
          [t for t in every if not (frame(t["start"]) and frame(end(t)))][:3])
    check("the reel is as long as its main layer", d["duration"] == end(main["segments"][-1]["target_timerange"]) == m["tm_duration"])
    off = max(abs(s["target_timerange"]["start"] / US - p["at"]) for s, p in zip(main["segments"], pcs))
    check("each piece starts within half a frame of where talking.py put it", off <= 0.5 / 30 + 1e-6, off)
    check("each piece shows the video from where talking.py said", all(s["source_timerange"]["start"] == int(round(p["from"] * US)) for s, p in zip(main["segments"], pcs)))
    check("their own sound on every piece; nothing zoomed that they didn't zoom",
          all(s["volume"] == 1.0 for s in main["segments"])
          and all(s["clip"]["scale"] == {"x": 1.0, "y": 1.0} and not s["common_keyframes"] for s, p in zip(main["segments"], pcs) if p["zoom"] is None))

    # a 1.5x piece
    fast = [(s, p) for s, p in zip(main["segments"], pcs) if p["speed"] == 1.5]
    by_id = {x["id"]: x for x in mats["speeds"]}

    def speed_item(s):
        return next(by_id[r] for r in s["extra_material_refs"] if r in by_id)
    check("a 1.5x piece: the clip says 1.5, its own speed item says 1.5, and it shows one and a half times its length of the video",
          len(fast) == 1 and all(s["speed"] == 1.5 and speed_item(s)["speed"] == 1.5
                                 and s["source_timerange"]["duration"] == int(round(s["target_timerange"]["duration"] * 1.5)) for s, _ in fast),
          [(s["speed"], s["source_timerange"], s["target_timerange"]) for s, _ in fast])
    check("...every other piece is at 1 on both, and shows exactly its own length",
          all(s["speed"] == 1.0 and speed_item(s)["speed"] == 1.0 and s["source_timerange"]["duration"] == s["target_timerange"]["duration"]
              for s, p in zip(main["segments"], pcs) if p["speed"] == 1.0))
    # punch
    punched = [s for s, p in zip(main["segments"], pcs) if p["zoom"] == 1]
    check("a punch in: its pieces sit at 1.15, with no keyframes", len(punched) >= 1 and all(s["clip"]["scale"] == {"x": 1.15, "y": 1.15} and not s["common_keyframes"] for s in punched))
    # slow zoom across pieces
    zs = [s for s, p in zip(main["segments"], pcs) if p["zoom"] == 0]
    keys = [s["common_keyframes"][0]["keyframe_list"] for s in zs]
    check("a slow zoom across three pieces (a split and a photo's edges fall inside it): 1.0 at its start, 1.12 at its end",
          len(zs) == 3 and keys[0][0]["values"] == [1.0] and keys[-1][-1]["values"] == [1.12], [[k["values"] for k in ks] for ks in keys])
    check("...the values meet where one piece hands over to the next, and each piece starts at its first value",
          all(a[-1]["values"] == b[0]["values"] for a, b in zip(keys, keys[1:]))
          and all(s["clip"]["scale"]["x"] == ks[0]["values"][0] == s["clip"]["scale"]["y"] for s, ks in zip(zs, keys))
          and all(x["values"][0] < y["values"][0] for ks in keys for x, y in zip(ks, ks[1:])))
    check("...its keyframes are CapCut's uniform-scale kind, the first at the piece's start and the last at its end, timed in the "
          "video's own clock (hers), each later than the one before (ours, Nov 13: more than two, the points of the eased curve)",
          all(s["common_keyframes"][0]["property_type"] == "KFTypeScaleX" and len(ks) >= 2
              and ks[0]["time_offset"] == s["source_timerange"]["start"] and ks[-1]["time_offset"] == end(s["source_timerange"])
              and all(x["time_offset"] < y["time_offset"] for x, y in zip(ks, ks[1:])) for s, ks in zip(zs, keys))
          and capcut.ZOOM_CLOCK == "video")
    capcut.ZOOM_CLOCK = "clip"
    d2, _ = capcut.build_talking(plan, parts, None)
    capcut.ZOOM_CLOCK = "video"
    z2 = [s for s, p in zip(d2["tracks"][0]["segments"], pcs) if p["zoom"] == 0]
    check("...and the one switch times them from the start of each clip instead, should CapCut want that",
          all([k["time_offset"] for k in s["common_keyframes"][0]["keyframe_list"]][::len(s["common_keyframes"][0]["keyframe_list"]) - 1]
              == [0, s["target_timerange"]["duration"]] for s in z2))


    # ================= how much, how fast, and the eased move (Dustin, Nov 13) =================
    eng_z = TR._engine()
    before = json.loads(ZOOM_BEFORE.read_text(encoding="utf-8"))
    Z0, Z1 = {"a": 2, "b": 7, "kind": "zoom"}, {"a": 14, "b": 16, "kind": "zoom"}
    P0, P1 = {"a": 2, "b": 7, "kind": "punch"}, {"a": 14, "b": 16, "kind": "punch"}
    d_p, _ = capcut.build_talking(zoom_plan([P0, P1]), parts, None)
    check("a punch in nobody set makes the very layer it made before zooms had an amount or a pace (the whole main layer, ids aside)",
          json.dumps(scrub(d_p["tracks"][0], {}), sort_keys=True) == json.dumps(before["punch_in"], sort_keys=True))
    check("...and the plan of a record with no amount and no pace carries its zooms exactly as before: a, b and kind, in that order",
          json.dumps(plan["zooms"]) == json.dumps([{"a": 2, "b": 7, "kind": "zoom"}, {"a": 14, "b": 16, "kind": "punch"}]), plan["zooms"])
    check("Medium is the amount there was: the engine's table says a slow zoom 1.12 and a punch in 1.15, and that is what a zoom has by itself",
          eng_z.ZOOM_AMOUNT["zoom"]["medium"] == 1.12 == capcut.ZOOM_TO and eng_z.ZOOM_AMOUNT["punch"]["medium"] == 1.15 == capcut.PUNCH
          and eng_z.AMOUNT_DEFAULT == "medium" and eng_z.PACE_DEFAULT == {"zoom": "whole", "punch": "instant"})
    check("the amounts and the seconds, each in the engine and nowhere else: slow zoom 1.06 / 1.12 / 1.20, punch in 1.075 / 1.15 / 1.24, "
          "Quick 1 s, Quick push 0.35 s",
          eng_z.ZOOM_AMOUNT == {"zoom": {"subtle": 1.06, "medium": 1.12, "strong": 1.20}, "punch": {"subtle": 1.075, "medium": 1.15, "strong": 1.24}}
          and eng_z.MOVE_SECS == {"quick": 1.0, "push": 0.35} and eng_z.ZOOM_PACE == {"zoom": ("quick", "whole"), "punch": ("instant", "push")})
    check("the one curve: 0 at the start, a half at the half, 1 at the end, exactly; slow at both ends; never outside 0 to 1",
          (eng_z.ease(0), eng_z.ease(0.5), eng_z.ease(1)) == (0.0, 0.5, 1.0) and eng_z.ease(0.25) == 0.15625 and eng_z.ease(0.75) == 0.84375
          and eng_z.ease(-3) == 0.0 and eng_z.ease(7) == 1.0 and eng_z.ease(0.1) < 0.1 and eng_z.ease(0.9) > 0.9)

    segs = zoom_layer(capcut, parts, Z0, Z1)
    slow = [s for s in segs if s.get("common_keyframes")]
    kk = [keys_of(s) for s in slow]
    old = before["slow_zoom_ends"]
    check("a slow zoom nobody set (Medium, Whole clip) still starts at 1.0 and ends on 1.12 exactly, on the very keyframe times it had before",
          len(slow) == 4 == len(old)
          and all([k["time_offset"] for k in s["common_keyframes"][0]["keyframe_list"]][::len(s["common_keyframes"][0]["keyframe_list"]) - 1]
                  == [o[1][0], o[2][0]] for s, o in zip(slow, old))
          and kk[0][0][1] == 1.0 == old[0][1][1] and kk[2][-1][1] == 1.12 == old[2][2][1] and kk[3][0][1] == 1.0 and kk[3][-1][1] == 1.12,
          [(k[0], k[-1]) for k in kk])

    def on_curve(ks, t0, move, to, tol=2e-6):
        return all(abs(v - round(1.0 + (to - 1.0) * eng_z.ease((t - t0) / move), 6)) <= tol for t, v in ks)
    run = kk[0] + kk[1] + kk[2]                       # zoom 0: reel 1.0 to 5.0, across a 1.5x piece and a closed pause
    check("...but it eases: every keyframe sits on the engine's curve (not on the straight line), going up all the way",
          on_curve(run, 1.0, 4.0, 1.12) and on_curve(kk[3], 5.7, 2.6, 1.12)
          and all(a[1] <= b[1] for a, b in zip(run, run[1:])) and all(a[1] < b[1] for ks in kk for a, b in zip(ks, ks[1:]))
          and abs(run[len(kk[0])][1] - (1.0 + 0.12 * 1.3 / 4.0)) > 0.005, (kk[0][-1], 1.0 + 0.12 * 1.3 / 4.0))
    check("...ONE curve across a change of speed and a closed pause: each piece starts on the value the one before ended on, "
          "and the clip's own scale is its first keyframe",
          kk[0][-1][1] == kk[1][0][1] and kk[1][-1][1] == kk[2][0][1] and 1.0 < kk[0][-1][1] < kk[1][-1][1] < 1.12
          and all(s["clip"]["scale"] == {"x": ks[0][1], "y": ks[0][1]} for s, ks in zip(slow, kk)), [(k[0][1], k[-1][1]) for k in kk[:3]])
    gaps = [b[0] - a[0] for ks in kk for a, b in zip(ks, ks[1:])]
    check("...written as ordinary keyframes, a point about every 0.15 s of the move (never more than 0.2 s apart here), each later "
          "than the one before in the video's own clock",
          max(gaps) <= 0.2 + 1e-6 and len(run) - 2 >= 5 and all(k["property_type"] == "KFTypeScaleX" for s in slow for k in s["common_keyframes"])
          and all(x["time_offset"] < y["time_offset"] for s in slow for x, y in zip(s["common_keyframes"][0]["keyframe_list"], s["common_keyframes"][0]["keyframe_list"][1:])),
          (max(gaps), len(run)))
    check("...a move has at least five points and a very long one no more than forty-one; a zoom one frame long still has its two ends",
          len(capcut.zoom_points(0, 6, 0, 6, 30.0)) == 5 and len(capcut.zoom_points(0, 9000, 0, 9000, 30.0)) == 41
          and capcut.zoom_points(0, 1, 0, 1, 30.0) == [0, 1] and capcut.zoom_points(10, 300, 100, 130, 30.0)[0] == 100
          and capcut.zoom_points(10, 300, 100, 130, 30.0)[-1] == 130)

    def ends(*zooms):                                  # (scale, first value, last value, how many keyframes) of each zoomed piece
        out = []
        for s in zoom_layer(capcut, parts, *zooms):
            ks = keys_of(s)
            out.append((s["clip"]["scale"]["x"], ks[0][1] if ks else None, ks[-1][1] if ks else None, len(ks)))
        return out
    e_s, e_g = ends(dict(Z0, amount="subtle"), dict(Z1, amount="strong")), ends(dict(P0, amount="subtle"), dict(P1, amount="strong"))
    check("How much reaches the project: a Subtle slow zoom ends on 1.06 and a Strong one on 1.20; a Subtle punch in sits at 1.075 "
          "and a Strong one at 1.24, with no keyframes",
          e_s[1][1] == 1.0 and e_s[3][2] == 1.06 and e_s[5][1:3] == (1.0, 1.2) and [x[0] for x in e_g[1:4]] == [1.075] * 3 and e_g[5] == (1.24, None, None, 0)
          and e_g[0][0] == e_g[4][0] == 1.0, (e_s, e_g))
    check("...and a setting nobody could have chosen is read as the zoom's own (Medium; Whole clip; Instant), never an error",
          ends(dict(Z0, amount="huge", pace="push"), dict(P1, amount=7, pace="whole")) == ends(Z0, P1))

    q = zoom_layer(capcut, parts, dict(Z0, pace="quick", amount="strong"), Z1)
    qk = keys_of(q[1])
    check("Quick: the slow zoom's move takes its first second (eased, on the curve), then HOLDS: the keyframes after it all say the "
          "amount, and the pieces after it sit at the amount with no keyframes",
          qk[0] == (1.0, 1.0) and on_curve([x for x in qk if x[0] <= 2.0 + 1e-6], 1.0, 1.0, 1.2)
          and [v for t, v in qk if t >= 2.0 - 1e-6] == [1.2, 1.2] and abs(qk[-1][0] - 2.3) < 1e-6 and len(qk) >= 6
          and [(s["clip"]["scale"]["x"], len(keys_of(s))) for s in q[2:4]] == [(1.2, 0), (1.2, 0)], qk)
    qq = zoom_layer(capcut, parts, Z0, dict(Z1, pace="quick"))
    check("...Whole clip beside it is unchanged, and a Quick zoom on its own clip ends its move a second in",
          [keys_of(s) for s in qq[1:4]] == kk[:3] and [v for t, v in keys_of(qq[5]) if t >= 6.7 - 1e-6][0] == 1.12
          and max(v for t, v in keys_of(qq[5]) if t < 6.7 - 1e-6) < 1.12)
    pp = zoom_layer(capcut, parts, P0, dict(P1, pace="push", amount="strong"))
    pk = keys_of(pp[5])
    moving = [x for x in pk if x[1] < 1.24]
    check("Quick push: the punch in starts at 1.0, pushes in on the curve over a third of a second (10 frames, five points), then holds "
          "at its amount to the end of the clip; an Instant punch in beside it is as it always was",
          pk[0] == (5.7, 1.0) and pk[-1] == (5.7 + 2.6, 1.24) and len(moving) == 4 and len(pk) == 6 and abs(moving[-1][0] - 5.7) < 10 / 30.0
          and on_curve(pk, 5.7, 10 / 30.0, 1.24) and all(a[1] <= b[1] for a, b in zip(pk, pk[1:]))
          and [(s["clip"]["scale"]["x"], len(keys_of(s))) for s in pp[1:4]] == [(1.15, 0)] * 3, pk)
    check("...a move is never longer than its stretch: Quick on 12 frames and Quick push on 6 take all of them; Whole clip the "
          "stretch; Instant none",
          capcut.zoom_move_frames({"kind": "zoom", "pace": "quick"}, 12, 30.0) == 12 and capcut.zoom_move_frames({"kind": "punch", "pace": "push"}, 6, 30.0) == 6
          and capcut.zoom_move_frames({"kind": "zoom"}, 77, 30.0) == 77 and capcut.zoom_move_frames({"kind": "punch"}, 77, 30.0) == 0
          and capcut.zoom_move_frames({"kind": "zoom", "pace": "quick"}, 300, 30.0) == 30 and capcut.zoom_move_frames({"kind": "punch", "pace": "push"}, 300, 30.0) == 10)
    capcut.ZOOM_CLOCK = "clip"
    ck = zoom_layer(capcut, parts, Z0, Z1)[2]["common_keyframes"][0]["keyframe_list"]
    capcut.ZOOM_CLOCK = "video"
    check("...and with the one switch the same points are timed from the start of each clip (a 1.5x piece: its own length on the reel)",
          ck[0]["time_offset"] == 0 and ck[-1]["time_offset"] == segs[2]["target_timerange"]["duration"]
          and [k["values"] for k in ck] == [k["values"] for k in segs[2]["common_keyframes"][0]["keyframe_list"]])
    # the engine's own function of time is what the builder cut its points from
    check("the engine's function of time (the one the page's preview draws) gives the same values as the project's keyframes",
          all(abs(eng_z.zoom_value(Z0, t - 1.0, 4.0) - v) <= 2e-6 for t, v in run)
          and all(abs(eng_z.zoom_value(dict(Z0, pace="quick", amount="strong"), t - 1.0, 4.0) - v) <= 2e-6 for t, v in qk)
          and eng_z.zoom_value(P1, 0.0, 2.6) == 1.15 == eng_z.zoom_value(P1, 2.0, 2.6)
          and eng_z.zoom_value(dict(P1, pace="push"), 0.0, 2.6) == 1.0 and eng_z.zoom_value(dict(P1, pace="push"), 0.35, 2.6) == 1.15
          and eng_z.zoom_value(dict(Z1, pace="quick"), 0.3, 0.6) == eng_z.zoom_value(Z1, 0.3, 0.6) == 1.06)

    # the photo layer
    starts = {s["target_timerange"]["start"] for s in main["segments"]}
    ends = {end(s["target_timerange"]) for s in main["segments"]}
    by_mat = {x["id"]: x for x in mats["videos"]}
    L = layer["segments"]

    def on(name):
        return [s for s in L if Path(by_mat[s["material_id"]]["path"]).name == name]
    flash = L[:3]
    check("photos flashing: three clips one after another, in the order chosen, from a piece's first frame to a piece's last",
          [Path(by_mat[s["material_id"]]["path"]).name for s in flash] == ["IMG_0001.png", "IMG_0002.png", "IMG_0003.png"]
          and flash[0]["target_timerange"]["start"] in starts and end(flash[2]["target_timerange"]) in ends
          and all(end(a["target_timerange"]) == b["target_timerange"]["start"] for a, b in zip(flash, flash[1:])))
    lens = [s["target_timerange"]["duration"] for s in flash]
    check("...evenly: no photo more than a frame longer than another", max(lens) - min(lens) <= 33334, lens)
    check("...Full screen: each fills the frame (a 2:3 photo at 1.185185), in the middle, as a still photo",
          all(s["clip"]["scale"] == {"x": 1.185185, "y": 1.185185} and s["clip"]["transform"] == {"x": 0.0, "y": 0.0}
              and by_mat[s["material_id"]]["type"] == "photo" and s["source_timerange"]["start"] == 0 for s in flash))
    pip = on("IMG_0004.png")[0]
    check("you in the corner: the photo fills the frame too", pip["clip"]["scale"] == {"x": 1.185185, "y": 1.185185} and pip["clip"]["transform"] == {"x": 0.0, "y": 0.0})
    cen = on("IMG_0005.png")[0]
    # hers: scale = 0.704 x 1080 / (40 x 27) = 0.704; centre y 0.44 x 1920 = 844.8 -> (960 - 844.8) / 960 = 0.12
    check("Center, a tall photo, not moved: 0.704 at CapCut's (0, 0.12)", cen["clip"]["scale"] == {"x": 0.704, "y": 0.704} and cen["clip"]["transform"] == {"x": 0.0, "y": 0.12}, cen["clip"])
    cor = on("IMG_0006.png")[0]
    # hers: x 0.778 x 1080 = 840.24 -> 0.556; y (0.073 + 0.132 / 2) x 1920 = 266.88 -> 0.722; scale 0.352 x 1080 / (60 x 18) = 0.352
    check("Small corner, a wide photo, not moved: 0.352 at CapCut's (0.556, 0.722)", cor["clip"]["scale"] == {"x": 0.352, "y": 0.352} and cor["clip"]["transform"] == {"x": 0.556, "y": 0.722}, cor["clip"])
    moved = [s for s in on("IMG_0002.png") if s not in flash][0]
    # theirs: centre (0.3, 0.6), half the screen wide -> 540 / 1080 = 0.5; x (324 - 540) / 540 = -0.4; y (960 - 1152) / 960 = -0.2
    check("a photo they moved and resized on the preview: 0.5 at CapCut's (-0.4, -0.2)", moved["clip"]["scale"] == {"x": 0.5, "y": 0.5} and moved["clip"]["transform"] == {"x": -0.4, "y": -0.2}, moved["clip"])
    check("no two clips on the photo layer share a moment", all(end(a["target_timerange"]) <= b["target_timerange"]["start"] for a, b in zip(L, L[1:])))
    check("every photo stretch starts on a piece's first frame and ends on a piece's last (the layers meet exactly)",
          all(s["target_timerange"]["start"] in starts for s in L if s not in flash[1:])
          and all(end(s["target_timerange"]) in ends for s in L if s not in flash[:2] and s not in on("b-roll.mp4")))

    # a video on a stretch
    v1, v2 = on("b-roll.mp4")
    vm = by_mat[v1["material_id"]]
    check("a video of theirs on a stretch: a video with its real length and its size as shown, muted, from where they chose",
          vm["type"] == "video" and vm["duration"] == 3 * US and (vm["width"], vm["height"]) == (320, 180)
          and v1["volume"] == 0.0 and v1["source_timerange"]["start"] == 1 * US and v1["speed"] == 1.0)
    check("...it runs as long as the video has left (2 s), not past its end, and never past its stretch",
          v1["source_timerange"]["duration"] == v1["target_timerange"]["duration"] == 2 * US and end(v1["source_timerange"]) <= vm["duration"])
    check("...in \"you in the corner\" it fills the frame (a wide 16:9 video at 3.160494)", v1["clip"]["scale"] == {"x": 3.160494, "y": 3.160494})
    check("a video that starts 0.05 s from its end: started early enough to have 0.1 s, never shorter, never past its end",
          v2["source_timerange"]["start"] == 2_900_000 and v2["target_timerange"]["duration"] == 100_000 and end(v2["source_timerange"]) <= by_mat[v2["material_id"]]["duration"],
          (v2["source_timerange"], v2["target_timerange"]))
    check("...in Center it sits like a photo: 0.704 at (0, 0.12), muted", v2["clip"]["scale"] == {"x": 0.704, "y": 0.704} and v2["clip"]["transform"] == {"x": 0.0, "y": 0.12} and v2["volume"] == 0.0)

    # the corner copies
    C = copies["segments"]
    main_by = {(s["target_timerange"]["start"], s["target_timerange"]["duration"]): s for s in main["segments"]}
    twins = [main_by.get((s["target_timerange"]["start"], s["target_timerange"]["duration"])) for s in C]
    check("the corner copies: each is in step with a main piece, frame for frame, showing the same part of the video at the same speed",
          len(C) >= 3 and all(t is not None and t["source_timerange"] == s["source_timerange"] and t["speed"] == s["speed"]
                              and speed_item(t)["speed"] == speed_item(s)["speed"] for s, t in zip(C, twins)), len(C))
    check("...muted, never zoomed", all(s["volume"] == 0.0 and not s["common_keyframes"] for s in C))
    first = [s for s in C if s["target_timerange"]["start"] == pip["target_timerange"]["start"]]
    check("...where it starts when they haven't moved themselves: 0.36 at (-0.547407, -0.5775)",
          len(first) == 1 and first[0]["clip"]["scale"] == {"x": 0.36, "y": 0.36} and first[0]["clip"]["transform"] == {"x": -0.547407, "y": -0.5775}, first and first[0]["clip"])
    onvid = [s for s in C if v1["target_timerange"]["start"] <= s["target_timerange"]["start"]]
    # theirs: (0.7, 0.2), a quarter wide -> x (756 - 540) / 540 = 0.4; y (960 - 384) / 960 = 0.6
    check("a video stretch in \"you in the corner\" gets its corner copies too, where they put themselves: 0.25 at (0.4, 0.6)",
          len(onvid) == 2 and all(s["clip"]["scale"] == {"x": 0.25, "y": 0.25} and s["clip"]["transform"] == {"x": 0.4, "y": 0.6} for s in onvid),
          [s["clip"] for s in onvid])
    check("...one of them on the sped-up piece, at its speed", sorted(s["speed"] for s in onvid) == [1.0, 1.5])
    mine = [s for s, p in zip(main["segments"], pcs) if 8 <= p["words"][0] <= 9 or 20 <= p["words"][0] <= 25]
    check("...on every piece that lies wholly inside a \"you in the corner\" stretch, and on no other",
          [(s["target_timerange"]["start"], s["target_timerange"]["duration"]) for s in C]
          == [(s["target_timerange"]["start"], s["target_timerange"]["duration"]) for s in mine], (len(C), len(mine)))

    # captions
    K = caps["segments"]
    texts = {x["id"]: json.loads(x["content"])["text"] for x in mats["texts"]}
    want = [c["text"] for c in eng.captions(rec)]
    check("captions: one clip of plain text per caption talking.py gives, in order (cut words have none)",
          [texts[s["material_id"]] for s in K] == want and "w0" not in want and "w12" not in want and len(want) == 36, len(K))
    check("...each stays until the next starts, and the last ends by the end of the reel",
          all(end(a["target_timerange"]) == b["target_timerange"]["start"] for a, b in zip(K, K[1:])) and end(K[-1]["target_timerange"]) <= d["duration"])
    check("...where captions start when they haven't moved them: CapCut's (0.0, -0.42), at size 1",
          all(s["clip"]["transform"] == {"x": 0.0, "y": -0.42} and s["clip"]["scale"] == {"x": 1.0, "y": 1.0} for s in K), K[0]["clip"])
    cap_off = max(abs(s["target_timerange"]["start"] / US - c["start"]) for s, c in zip(K, eng.captions(rec)))
    check("...each within a frame of where talking.py put it", cap_off <= 1 / 30 + 1e-6, cap_off)
    p2 = dict(plan, cap_pos={"x": 0.25, "y": 0.9}, cap_size=1.6)
    d3, _ = capcut.build_talking(p2, parts, None)
    # theirs: (0.25, 0.9) -> x (0.25 - 0.5) x 2 = -0.5; y (0.5 - 0.9) x 2 = -0.8
    check("captions they dragged and resized: every one at CapCut's (-0.5, -0.8), 1.6 times as big",
          all(s["clip"]["transform"] == {"x": -0.5, "y": -0.8} and s["clip"]["scale"] == {"x": 1.6, "y": 1.6} for s in d3["tracks"][-1]["segments"]))
    d4, _ = capcut.build_talking(dict(plan, captions=None), parts, None)
    check("captions off: no caption layer at all, and no text in the project", [t["type"] for t in d4["tracks"]] == ["video", "video", "video"] and not d4["materials"]["texts"])
    d5, m5 = capcut.build_talking(dict(plan, shots=[], captions=None, zooms=[]), parts, None)
    check("no photos, no captions: just their talking video, cut", [t["type"] for t in d5["tracks"]] == ["video"] and len(d5["materials"]["videos"]) == 1)
    bin_ = next(x for x in m["draft_materials"] if x["type"] == 0)["value"]
    check("CapCut's own list of what is in the project: each file once, the videos as videos with their real length (hers: \"photo, 5 s\")",
          sorted(x["extra_info"] for x in bin_) == sorted(Path(f).name for f in plan["files"])
          and {x["extra_info"]: (x["metetype"], x["duration"]) for x in bin_ if x["metetype"] == "video"} == {"my talk.mp4": ("video", 60 * US), "b-roll.mp4": ("video", 3 * US)})
    odd = dict(plan, shots=[{"at": plan["shots"][0]["at"], "dur": plan["shots"][0]["dur"], "spot": "corner", "pos": None, "me": None,
                             "photos": [{"path": str(TMP / "no such photo.tiff"), "w": 0, "h": 0}]}])
    d6, _ = capcut.build_talking(odd, parts, None)
    check("a photo whose size nobody could read: fitted at 1, never a crash", d6["tracks"][1]["segments"][0]["clip"]["scale"] == {"x": 1.0, "y": 1.0})
    many = dict(plan, shots=[{"at": pcs[0]["at"], "dur": 2 / 30, "spot": "full", "pos": None, "me": None,
                              "photos": [{"path": f"/pretend/{i}.jpg", "w": 40, "h": 60} for i in range(5)]}],
                pieces=[dict(pcs[0], dur=2 / 30, to=pcs[0]["from"] + 2 / 30)], captions=None, zooms=[])
    d7, _ = capcut.build_talking(many, parts, None)
    seg7 = d7["tracks"][1]["segments"]
    check("more photos than frames on a stretch: one photo a frame, none of no length, none overlapping",
          len(seg7) == 2 and all(s["target_timerange"]["duration"] > 0 for s in seg7) and end(seg7[0]["target_timerange"]) == seg7[1]["target_timerange"]["start"])
    short_vid = dict(plan, video=dict(plan["video"], length=round(pcs[-1]["to"] - 0.1, 3)), shots=[], captions=None)
    d8, _ = capcut.build_talking(short_vid, parts, None)
    last8 = d8["tracks"][0]["segments"][-1]
    check("the last piece never shows more of the video than there is (the air after the last word can run past a video's end)",
          end(last8["source_timerange"]) <= int(round(short_vid["video"]["length"] * US)) and d8["duration"] == end(last8["target_timerange"]),
          (end(last8["source_timerange"]), short_vid["video"]["length"]))

    # overlapping stretches (her save takes them; the later one has the word)
    over = json.loads(json.dumps(rec))
    over["shots"] = [{"a": 3, "b": 9, "ns": [1], "spot": "full"}, {"a": 5, "b": 6, "ns": [2], "spot": "full"}]
    opcs = eng.pieces(over)
    got = TM.stretches(over, opcs)
    check("stretches that overlap: each gets only the pieces that are its own, so nothing on the photo layer can share a moment",
          [x["ns"] for x, _ in got] == [[1], [2], [1]] and all(near(a["at"] + a["dur"], b["at"], 2e-3) for (_, a), (_, b) in zip(got, got[1:])),
          [(x["ns"], s) for x, s in got])

    # ================= the maker =================
    kit_before = sorted(os.listdir(KIT / ".kit"))
    rec_before = (KIT / ".kit" / "talking.json").read_bytes()
    status = TMP / "status.json"
    status.write_text(json.dumps({"for": "abc123abc123", "pending": True}), encoding="utf-8")
    r = maker("--kit", SHORT, "--dry-run", "--store", str(STORE), "--ignore-open", "--status", str(status))
    st = json.loads(status.read_text(encoding="utf-8"))
    check("a dry run: found from the short name as pasted, says the plan in numbers (hers), and exits 0",
          r.returncode == 0 and r.stdout.splitlines()[-1] == "Dry run: nothing made in CapCut." and r.stdout.startswith(f"Plan: {len(eng.pieces(rec))} pieces of talking, "),
          (r.returncode, r.stdout, r.stderr[-300:]))
    check("...writes nothing: no project, nothing in the shoot's hidden folder, the record untouched",
          projects() == [] and sorted(os.listdir(KIT / ".kit")) == kit_before and (KIT / ".kit" / "talking.json").read_bytes() == rec_before, projects())
    check("...its --status says so, and keeps the mark of the job that asked", st.get("ok") is True and st.get("dry") is True and st.get("project") is None and st.get("for") == "abc123abc123"
          and st["plan"]["photos"] == 7 and st["plan"]["videos"] == 2 and st["plan"]["sped"] == 1 and st["plan"]["zooms"] == 2, st)

    photos_before = sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for d_ in ("Photos", "Talking", "Footage") for p in (KIT / d_).iterdir())
    slim_before = json.loads((KIT / ".kit" / "talking.json").read_text(encoding="utf-8"))
    prev_before = (KIT / ".kit" / "talking.prev.json").read_bytes()
    r = maker("--kit", str(KIT), "--store", str(STORE), "--ignore-open", "--status", str(status))
    slim_after = json.loads((KIT / ".kit" / "talking.json").read_text(encoding="utf-8"))
    check("noting what was made does not move the record's counter, its stamp or its mark, and leaves the version before alone",
          len(slim_after.get("made") or []) == 1 and all(slim_after.get(k) == slim_before.get(k) for k in ("rev", "updated", "from"))
          and {k: v for k, v in slim_after.items() if k != "made"} == {k: v for k, v in slim_before.items() if k != "made"}
          and (KIT / ".kit" / "talking.prev.json").read_bytes() == prev_before,
          {k: (slim_before.get(k), slim_after.get(k)) for k in ("rev", "updated", "from")})
    code_s, ans_s = TR.save_from_page(KIT, {"base": slim_before["rev"], "page": "pageMAKE01", "saved": {"cap_size": 1.3}})
    check("...so the page's next save after Make it in CapCut is taken, not told \"changed somewhere else\" (and its Undo is not emptied)",
          code_s == 200 and ans_s.get("ok") is True and TR.load(KIT).get("cap_size") == 1.3 and len(TR.load(KIT)["made"]) == 1, (code_s, ans_s))
    TR.change(KIT, lambda rec: rec.update(cap_size=None))      # as the scene had it
    NAME = f"{SHORT} talking reel"
    check("a make prints ONE line, hers: Made \"<short> talking reel\" in CapCut. Open CapCut and it's at the top of your projects.",
          r.returncode == 0 and r.stdout.splitlines() == [f"Made \"{NAME}\" in CapCut. Open CapCut and it's at the top of your projects."] and not r.stderr.strip(),
          (r.returncode, r.stdout, r.stderr[-400:]))
    check("...no path in what it prints", "/" not in r.stdout.replace("</", "") and "\\" not in r.stdout and str(TMP) not in r.stdout)
    check("...a new project by that name in CapCut's folder, with nothing half-made left beside it",
          NAME in projects() and not [p for p in projects() if p.startswith(".")], projects())
    dd = draft_of(NAME)
    mat = next(x for x in dd["materials"]["videos"] if x["path"] == capcut.native(TALK))
    check("a phone video stored turned comes out upright and the right size: 180 wide, 320 tall, filling the frame at 1",
          (mat["width"], mat["height"]) == (180, 320) and dd["tracks"][0]["segments"][0]["clip"]["scale"] == {"x": 1.0, "y": 1.0}, (mat["width"], mat["height"]))
    check("...and its real length, read from the file now (3 s), whatever the record's facts say", mat["duration"] == 3 * US)
    files = sorted(p.name for p in (STORE / NAME).iterdir())
    check("the project's files: CapCut's project file, its description, its settings and a cover made from the first photo",
          files == sorted([("draft_content.json" if os.name == "nt" else "draft_info.json"), "draft_meta_info.json", "draft_settings", "draft_cover.jpg"])
          or files == sorted([("draft_content.json" if os.name == "nt" else "draft_info.json"), "draft_meta_info.json", "draft_settings"]), files)
    root = json.loads((STORE / "root_meta_info.json").read_text(encoding="utf-8"))
    check("...and it is in CapCut's list of projects", [x["draft_name"] for x in root["all_draft_store"]] == [NAME])
    st = json.loads(status.read_text(encoding="utf-8"))
    check("its --status names the project and that it is listed", st.get("ok") is True and st.get("project") == NAME and st.get("listed") is True and st.get("dry") is False
          and st.get("line") == r.stdout.strip(), st)
    check("...and no photo had to be left out for want of a frame", st.get("photos_no_frame") == 0, st.get("photos_no_frame"))
    made = TR.load(KIT).get("made")
    check("the record keeps what was made, and when (hers)", isinstance(made, list) and len(made) == 1 and made[0]["project"] == NAME and abs(made[0]["when"] - time.time()) < 60, made)
    check("their photos and videos were only read",
          photos_before == sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for d_ in ("Photos", "Talking", "Footage") for p in (KIT / d_).iterdir()))
    plan_file = json.loads((KIT / ".kit" / "talking-make.json").read_text(encoding="utf-8"))
    check("the plan handed to capcut.py is kept in the shoot's hidden folder (the Assistant's own working file)", plan_file["name"] == NAME and plan_file["video"]["w"] == 180)
    first_bytes = (STORE / NAME / files[1]).read_bytes()
    r = maker("--kit", str(KIT), "--store", str(STORE), "--ignore-open")
    check("a second make is \"<short> talking reel 2\": a new project, the first one untouched",
          r.returncode == 0 and r.stdout.splitlines() == [f"Made \"{NAME} 2\" in CapCut. Open CapCut and it's at the top of your projects."]
          and projects().count(NAME) == 1 and f"{NAME} 2" in projects() and (STORE / NAME / files[1]).read_bytes() == first_bytes, (r.stdout, projects()))
    check("...and the record now holds both", [x["project"] for x in TR.load(KIT)["made"]] == [NAME, f"{NAME} 2"])

    # a wide talking video (not 9:16) fills the frame
    K2 = make_kit("2026-10-01 Wide talk", [(40, 60, True)])
    shutil.copyfile(CLIP, K2 / "Talking" / "wide.mp4")
    W2 = words_every(16, 0.15, 0.1, ends=(7, 15))
    TR.put_words(K2, "wide.mp4", video.key(K2 / "Talking" / "wide.mp4"), W2, {"dur": 3.0, "w": 320, "h": 180}, {"how": "pretend", "ondevice": True})
    TR.change(K2, lambda rec: rec.update(shots=[{"a": 2, "b": 5, "ns": [1], "spot": "pip", "pos": None, "me": None}], captions=False,
                                         zooms=[{"a": 8, "b": 10, "kind": "punch"}, {"a": 11, "b": 14, "kind": "zoom"}]))
    r = maker("--kit", "Wide talk", "--store", str(STORE), "--ignore-open")
    dw = draft_of("Wide talk talking reel")
    FILL = 3.160494
    wsegs = dw["tracks"][0]["segments"]
    wz = [s for s in wsegs if s.get("common_keyframes")]
    wplain = sorted({s["clip"]["scale"]["x"] for s in wsegs if not s.get("common_keyframes")})
    check("a talking video that is not 9:16 (held sideways): it is scaled to fill the frame, as the preview shows it",
          r.returncode == 0 and wplain[0] == FILL and all(s["clip"]["scale"]["x"] == s["clip"]["scale"]["y"] for s in wsegs), r.stdout + r.stderr[-300:])
    check("...a punch in on it is the fill times 1.15 (3.634568), never 1.15 alone",
          wplain == [FILL, round(FILL * 1.15, 6)] and round(FILL * 1.15, 6) == 3.634568, wplain)
    wvals = [k["values"][0] for s in wz for k in s["common_keyframes"][0]["keyframe_list"]]
    check("...and a slow zoom on it runs from the fill to the fill times 1.12 (3.160494 to 3.539753)",
          bool(wz) and min(wvals) == FILL and max(wvals) == round(FILL * 1.12, 6) == 3.539753
          and wz[0]["clip"]["scale"]["x"] == FILL, wvals)
    check("...no piece shows the video past its end (3 s)", all(end(s["source_timerange"]) <= 3 * US for s in dw["tracks"][0]["segments"]),
          max(end(s["source_timerange"]) for s in dw["tracks"][0]["segments"]))
    wcopies = dw["tracks"][2]["segments"]
    check("...its corner copy is 0.36, as hers: the whole video, small (389 px across), never wider than the frame; captions off wrote no caption layer",
          [t["type"] for t in dw["tracks"]] == ["video", "video", "video"] and bool(wcopies) and all(s["clip"]["scale"] == {"x": 0.36, "y": 0.36} for s in wcopies)
          and all(320 * capcut.fit_scale(320, 180) * s["clip"]["scale"]["x"] <= capcut.CANVAS[0] for s in wcopies),
          [s["clip"]["scale"] for s in wcopies])

    # ---- more photos than frames on their words: counted, never a silent loss
    crowd = json.loads(json.dumps(plan))
    one_photo = next(x for x in plan["shots"] if x.get("photos"))["photos"][0]
    crowd["shots"] = [{"at": plan["pieces"][0]["at"], "dur": 2 / 30.0, "spot": "full", "pos": None, "me": None, "photos": [one_photo] * 5}]
    dcrowd, _ = capcut.build_talking(crowd, capcut.load_parts(), capcut.their_platform(STORE))
    shown = len(dcrowd["tracks"][1]["segments"])
    check("five photos on two frames of talking: every frame has a photo, and the ones with no frame are counted (build_talking.no_frame)",
          1 <= shown < 5 and capcut.build_talking.no_frame == 5 - shown, (shown, capcut.build_talking.no_frame))

    # ---- numbers a hand-changed record could hold never reach CapCut as they are
    K4 = make_kit("2026-10-09 By hand", [(40, 60, True)])
    shutil.copyfile(CLIP, K4 / "Talking" / "talk.mp4")
    turned(CLIP, K4 / "Talking" / "talk.mp4")
    TR.put_words(K4, "talk.mp4", video.key(K4 / "Talking" / "talk.mp4"), words_every(16, 0.15, 0.1, ends=(7, 15)), {"dur": 3.0, "w": 180, "h": 320},
                 {"how": "pretend", "ondevice": True})
    TR.change(K4, lambda rec: rec.update(shots=[{"a": 2, "b": 5, "ns": [1], "spot": "pip", "pos": None, "me": {"x": 1e308, "y": -5, "w": 0}},
                                                {"a": 9, "b": 12, "ns": [1], "spot": "center", "pos": {"x": 0.5, "y": float("inf"), "w": 99}, "me": None}],
                                         cap_size=-3, cap_pos={"x": 7, "y": 0.5}))
    r = maker("--kit", str(K4), "--store", str(STORE), "--ignore-open")

    def no_such(c):
        raise ValueError(c)
    try:
        d4 = json.loads((STORE / "By hand talking reel" / ("draft_content.json" if os.name == "nt" else "draft_info.json")).read_text(encoding="utf-8"),
                        parse_constant=no_such)
    except (OSError, ValueError) as e:
        d4 = None
        check("a record changed by hand (a corner box at 1e308, 0 wide; captions -3 big): the project is still one CapCut can read", False, (r.stdout, repr(e)))
    if d4:
        c4 = d4["tracks"][2]["segments"][0]["clip"]
        p4 = [s for s in d4["tracks"][1]["segments"] if s["clip"]["scale"]["x"] != capcut.cover_scale(40, 60)]
        t4 = d4["tracks"][-1]["segments"][0]["clip"]
        check("a record changed by hand (a corner box at 1e308, 0 wide; captions -3 big): every number is held to the page's own limits",
              r.returncode == 0 and c4["scale"] == {"x": 0.08, "y": 0.08} and c4["transform"] == capcut.canvas_xy(1.5 * 1080, -0.5 * 1920)
              and t4["scale"] == {"x": 0.4, "y": 0.4} and t4["transform"] == {"x": 0.96, "y": 0.0}, (c4, t4))
        check("...a box with a place that is no number at all (Infinity) goes back to where the photo sits by itself (Center: 0.704 at y 0.12)",
              len(p4) == 1 and p4[0]["clip"]["transform"] == {"x": 0.0, "y": 0.12} and p4[0]["clip"]["scale"]["x"] == 0.704, [s["clip"] for s in p4])
    check("...and the builder itself holds a box it is handed: Infinity to the default, a width of 99 to 2, of 0 to 0.08",
          capcut._held_box({"x": 0.5, "y": float("inf"), "w": 99}, {"x": 0.5, "y": 0.44, "w": 0.704}) == {"x": 0.5, "y": 0.44, "w": 2.0}
          and capcut._held_box({"x": float("nan"), "y": "a", "w": 0}, capcut.ME_DEFAULT) == dict(capcut.ME_DEFAULT, w=0.08))
    bad_json = TMP / "strict.json"
    try:
        capcut.write_json(bad_json, {"x": float("inf")}, strict=True)
        raised = False
    except ValueError:
        raised = True
    check("capcut.py refuses to write a project file with a number CapCut cannot read (Infinity), and leaves nothing behind",
          raised and not bad_json.exists(), sorted(x.name for x in TMP.iterdir() if "strict" in x.name))
    inf_plan = json.loads(json.dumps(plan))
    inf_plan["pieces"][0]["speed"] = float("inf")           # past every check before it: only the writer can catch it now
    n_store = sorted(os.listdir(STORE))
    try:
        capcut.write(inf_plan, STORE, True, builder=lambda pl, pa, pf: (dict(capcut.build_talking(plan, pa, pf)[0], oops=float("inf")),
                                                                         capcut.build_talking(plan, pa, pf)[1]))
        raised = False
    except ValueError:
        raised = True
    check("capcut.write: a project holding such a number is never written, and its hidden making folder is cleared",
          raised and sorted(os.listdir(STORE)) == n_store, sorted(set(os.listdir(STORE)) - set(n_store)))

    # ---- a shoot's own lists that can't be read: plain words, never a Python error
    def plain_stop(name, line):
        before = projects()
        r = maker("--kit", str(K4), "--store", str(STORE), "--ignore-open")
        check(name, r.returncode == 2 and r.stdout.splitlines() == ["STOP: " + line] and "Traceback" not in r.stderr and not r.stderr.strip()
              and projects() == before, (r.returncode, r.stdout, r.stderr[-300:]))
    kj, sj = K4 / ".kit" / "kit.json", K4 / ".kit" / "sheet.json"
    kj_was, sj_was = kj.read_bytes(), sj.read_bytes()
    kj.write_text("[1,2", encoding="utf-8")
    plain_stop("the shoot's own record (kit.json) damaged: the maker stops in plain words, no Python error, nothing made", TR.TROUBLE)
    kj.write_bytes(kj_was)
    sj.write_text("{not json", encoding="utf-8")
    plain_stop("the numbered photo list (sheet.json) damaged: it never says a photo of theirs has gone", TR.TROUBLE)
    sj.write_bytes(sj_was)

    # ---- --status only ever writes a status file
    photo4 = K4 / "Photos" / "IMG_0001.png"
    photo_was = photo4.read_bytes()
    r = maker("--kit", str(K4), "--dry-run", "--store", str(STORE), "--ignore-open", "--status", str(photo4))
    a_list = TMP / "a list.json"
    a_list.write_text("[1, 2, 3]", encoding="utf-8")
    r2 = maker("--kit", str(K4), "--dry-run", "--store", str(STORE), "--ignore-open", "--status", str(a_list))
    r3 = maker("--kit", str(K4), "--dry-run", "--store", str(STORE), "--ignore-open", "--status", str(kj))
    r4 = maker("--kit", str(K4), "--dry-run", "--store", str(STORE), "--ignore-open", "--status", str(K4 / "Photos" / "new.txt"))
    check("--status pointed at a photo, at the shoot's own kit.json, or at a file that is no status file: nothing is written over, nothing new made",
          r.returncode == 0 and r2.returncode == 0 and r3.returncode == 0 and r4.returncode == 0 and photo4.read_bytes() == photo_was
          and a_list.read_text(encoding="utf-8") == "[1, 2, 3]" and kj.read_bytes() == kj_was and not (K4 / "Photos" / "new.txt").exists())

    # ---- four makes of one shoot at the same moment (the chat and the page's job, say)
    n_before = len(projects())
    procs = [subprocess.Popen([sys.executable, str(MAKER), "make", "--kit", str(K4), "--store", str(STORE), "--ignore-open"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=ENV) for _ in range(4)]
    outs = [(q.communicate(timeout=120), q.returncode) for q in procs]
    won = [o[0].strip() for o, rc in outs if rc == 0]
    lost = [o[0].strip() for o, rc in outs if rc != 0]
    check("four makes of one shoot at once: each either makes a project of its own name or is told her \"still working\" line; none fails half way",
          len(won) >= 1 and len(set(won)) == len(won) and len(projects()) == n_before + len(won)
          and all(x == "STOP: I'm still working on the last one. Give it a minute." for x in lost) and all(rc in (0, 2) for _, rc in outs)
          and not any(o[1].strip() for o, _ in outs), [(o[0].strip()[:90], o[1].strip()[-200:], rc) for o, rc in outs])
    check("...and nothing half-made is left in CapCut's projects folder", not [x for x in os.listdir(STORE) if x.startswith(".") and ".making-" in x],
          [x for x in os.listdir(STORE) if x.startswith(".")])
    held4 = open(K4 / ".kit" / TM.MAKE_LOCK, "ab")
    import this_computer as _tc       # noqa: E402
    if _tc.try_lock(held4):
        t_l = time.time()
        r = maker("--kit", str(K4), "--store", str(STORE), "--ignore-open")
        check("a make while another make of the same shoot is writing: her line, exit 2, nothing made, after a short wait",
              r.returncode == 2 and r.stdout.splitlines() == ["STOP: I'm still working on the last one. Give it a minute."] and time.time() - t_l < 15
              and len(projects()) == n_before + len(won), (r.returncode, r.stdout))
        r = maker("--kit", str(K4), "--dry-run", "--store", str(STORE), "--ignore-open")
        check("...a dry run writes nothing, so it never waits for it", r.returncode == 0, r.stdout)
        _tc.unlock(held4)
    else:
        skip("a make while another make of the same shoot is writing", "no file locks on this scratch drive")
    held4.close()

    # capcut.write: the name taken in the last moment
    real_rename, said = capcut.os.rename, []
    real_say = capcut.say

    def no_rename(a, b):
        raise FileExistsError(17, "File exists", str(b))
    capcut.os.rename, capcut.say = no_rename, said.append
    try:
        capcut.write(plan, STORE, True, builder=capcut.build_talking)
        stopped = None
    except SystemExit as e:
        stopped = e.code
    finally:
        capcut.os.rename, capcut.say = real_rename, real_say
    check("capcut.write: when the project cannot be given its name, its hidden making folder is cleared and the line names no place",
          stopped == 2 and not [x for x in os.listdir(STORE) if ".making-" in x]
          and said == ["STOP: " + TR.OUR_MAKE_WORDS["no_name"][0]], (stopped, said, [x for x in os.listdir(STORE) if x.startswith(".")]))

    # ---- it stops, with nothing written, in plain words
    def stops(kit, line, name):
        before = projects()
        made_before = TR.load(kit).get("made")
        st_f = TMP / "stop-status.json"
        st_f.unlink() if st_f.exists() else None
        r = maker("--kit", str(kit), "--store", str(STORE), "--ignore-open", "--status", str(st_f))
        check(name, r.returncode == 2 and r.stdout.splitlines() == ["STOP: " + line] and projects() == before and TR.load(kit).get("made") == made_before
              and json.loads(st_f.read_text(encoding="utf-8")).get("ok") is False, (r.returncode, r.stdout, r.stderr[-300:]))

    gone_photo = K2 / "Photos" / "IMG_0001.png"
    kept = gone_photo.read_bytes()
    gone_photo.unlink()                                  # the test's own photo
    stops(K2, "A photo in your talking reel isn't in this shoot anymore. Take it off its words or put it back, then make it again.",
          "a photo they placed has gone: it stops before anything is written and says so (hers leaves the stretch out without a word)")
    gone_photo.write_bytes(kept)
    TR.change(K2, lambda rec: rec.update(shots=[{"a": 2, "b": 5, "ns": [9], "spot": "full", "pos": None, "me": None}]))
    stops(K2, TR.OUR_MAKE_WORDS["photo_gone"][0], "a photo number that is no longer on the shoot's numbered list: the same stop")
    TR.change(K2, lambda rec: rec.update(shots=[{"a": 2, "b": 5, "ns": [], "v": "b-roll.mp4", "from": 0, "spot": "full", "pos": None, "me": None}]))
    stops(K2, "A video in your talking reel isn't in the Footage folder anymore. Take it off its words or put it back, then make it again.",
          "a Footage video they placed has gone: it stops and says which kind is missing")
    TR.change(K2, lambda rec: rec.update(shots=[{"a": 20, "b": 30, "ns": [9], "spot": "full", "pos": None, "me": None}], cut=[[2, 3]]))
    r = maker("--kit", str(K2), "--store", str(STORE), "--ignore-open")
    check("a stretch none of whose words is in the reel is simply not in it (as hers), whatever its photo", r.returncode == 0 and "Wide talk talking reel 2" in r.stdout, r.stdout + r.stderr[-300:])
    TR.change(K2, lambda rec: rec.update(shots=[], cut=[[0, 15]]))
    stops(K2, "Everything is cut. Bring some words back first.", "every word cut: her line")
    TR.change(K2, lambda rec: rec.update(cut=[]))
    time.sleep(1.1)                                      # a key is name, size and whole-second time
    turned(CLIP, K2 / "Talking" / "wide.mp4")            # "exported again": the same name, another file
    stops(K2, TR.OUR_JOB_WORDS["changed"][0], "the talking video was exported again since its script was made: refused (every word's time is the old file's)")
    (K2 / "Talking" / "wide.mp4").unlink()               # the test's own copy
    stops(K2, "Your talking video isn't in the Talking folder anymore.", "the talking video has gone from its folder: her line")
    K3 = make_kit("2026-10-08 No script", [(40, 60, True)])
    stops(K3, "Turn your video into a script first.", "no script yet: her line")
    r = maker("--kit", str(KIT), "--store", str(TMP / "no capcut here"), "--ignore-open")
    check("no CapCut projects folder: it stops, nothing is made, and the record notes nothing",
          r.returncode == 2 and r.stdout.startswith("STOP: I can't find CapCut's projects folder") and len(TR.load(KIT)["made"]) == 2, r.stdout)

    # capcut.write itself: the files a plan names must all be there, or nothing is written
    before = projects()
    ghost = dict(plan, files=plan["files"] + [str(TMP / "gone in the last moment.jpg")])
    try:
        capcut.write(ghost, STORE, True, builder=capcut.build_talking)
        stopped = None
    except SystemExit as e:
        stopped = e.code
    check("capcut.write: a file the plan names that is not there stops it before a folder is made", stopped == 2 and projects() == before, (stopped, projects()))
    w = capcut.write
    w.left_to_capcut, w.listed, w.note = True, False, None
    check("the maker's line when CapCut is open on a Mac (it adds the project by itself): hers",
          TM.made_line("X talking reel") == "Made \"X talking reel\" in CapCut. CapCut is open, so it will show up in your projects in a moment; "
          f"if it isn't there, {capcut.QUIT} and reopen CapCut.")
    w.left_to_capcut, w.listed, w.note = False, False, "I couldn't add the reel to CapCut's list of projects just now."
    check("...and when the reel is not in CapCut's list yet, it never says \"at the top of your projects\": the plain fact, then what to do, still one line",
          TM.made_line("X talking reel") == "Made \"X talking reel\" in CapCut. I couldn't add the reel to CapCut's list of projects just now.")
    w.left_to_capcut, w.listed, w.note = False, True, None

    # ================= the make's own job =================
    code, ans = TR.start_make(K3)
    check("Make it in CapCut with no script: refused at once with her line, no job", code == 400 and ans == {"ok": False, "why": "no_script", "words": "Turn your video into a script first."}
          and TR.make_for_page(K3) is None and not (K3 / ".kit" / TR.MAKE_JOB).exists(), (code, ans))
    check("a shoot whose reel was never made from the page has no job to show", TR.make_for_page(K2) is None)

    def wait_make(kit, secs=40):
        t = time.time()
        while time.time() - t < secs:
            j = TR.make_for_page(kit)
            if j and j["state"] in ("done", "problem"):
                return j
            time.sleep(0.1)
        return TR.make_for_page(kit)

    code, ans = TR.start_make(KIT)
    check("Make it in CapCut: a job is started and the page is handed it", code == 200 and ans["ok"] is True and ans["job"]["state"] in ("queued", "running", "done"), (code, ans))
    code2, ans2 = TR.start_make(KIT)
    j = wait_make(KIT)
    check("pressed again while it is at work (or just done): never two at once", code2 in (200, 409) and (code2 == 200 or ans2["words"] == "I'm still working on the last one. Give it a minute."), (code2, ans2))
    j = wait_make(KIT)
    n_now = len(TR.load(KIT)["made"])
    check("the job ends done, with the maker's one line for her result box and the project's name",
          j["state"] == "done" and j["words"] == [f"Made \"{j['project']}\" in CapCut. Open CapCut and it's at the top of your projects."]
          and j["project"].startswith(NAME) and j["project"] in projects() and j["problem"] is None, j)
    check("...it wrote into the pretend CapCut folder, and the record noted it", n_now in (3, 4) and TR.load(KIT)["made"][-1]["project"] == j["project"], n_now)
    check("...nothing the page is handed holds a path or a process number", str(TMP) not in json.dumps(j) and "pid" not in j and "/" not in "".join(j["words"]))
    check("...and the job let go of everything: not running, the computer's one reel-make turn free",
          TR.make_running(KIT) is False and __import__("reel_page")._hold_make_lock(time.time() + 2) not in (None,))
    code, ans = TR.start_make(KIT, dry=True)
    j = wait_make(KIT)
    check("a dry run from the page: done, its two lines, no project, nothing more in CapCut's folder or the record",
          j["state"] == "done" and j["dry"] is True and j["project"] is None and j["words"][-1] == "Dry run: nothing made in CapCut."
          and len(TR.load(KIT)["made"]) == n_now, j)
    (KIT / "Photos" / "IMG_0005.png").rename(KIT / "Photos" / "IMG_0005.away")       # the test's own photo
    code, ans = TR.start_make(KIT)
    j = wait_make(KIT)
    check("a photo gone when the job gets to it: a problem in our plain words, nothing made", j["state"] == "problem" and j["problem"] == TR.OUR_MAKE_WORDS["photo_gone"][0]
          and j["words"] == [] and j["project"] is None and len(TR.load(KIT)["made"]) == n_now, j)
    (KIT / "Photos" / "IMG_0005.away").rename(KIT / "Photos" / "IMG_0005.png")

    os.environ[TR.TEST_STORE] = str(TMP / "no capcut here")
    code, ans = TR.start_make(KIT)
    j = wait_make(KIT)
    os.environ[TR.TEST_STORE] = str(STORE)
    check("no CapCut projects folder when the job gets to it: capcut.py's own plain line, one that is on our list of words, with no place in it",
          j["state"] == "problem" and j["problem"] == TR.OUR_MAKE_WORDS["no_capcut"][0] and str(TMP) not in j["problem"], j)
    cc_src = __import__("re").sub(r" \(\{\w+\}\)", "", (REEL / "capcut.py").read_text(encoding="utf-8"))
    check("each of capcut.py's stops that may reach the page is listed with ours, word for word, with its reason",
          all(TR.OUR_MAKE_WORDS[k][0] in cc_src and TR.OUR_MAKE_WORDS[k][1] for k in TR.CAPCUT_STOPS), [k for k in TR.CAPCUT_STOPS if TR.OUR_MAKE_WORDS[k][0] not in cc_src])
    import reel_page as _rp       # noqa: E402
    real_run = _rp._run_bounded
    _rp._run_bounded = lambda cmd, left, **kw: (2, "STOP: some other trouble capcut.py met.\n", "")
    try:
        res = TR._make_now(KIT, "abcabcabcabc", False, time.time() + 30)
    finally:
        _rp._run_bounded = real_run
    check("...and any other line the maker stops with is told as her \"Something went wrong making it.\" (the detail goes to the log)",
          res == {"state": "problem", "problem": "Something went wrong making it."}, res)

    # a job that died: plain words; unless its project did reach CapCut
    TR.write_make(KIT, {"id": "feedfeedfeed", "state": "running", "t": time.time() - 5, "t0": time.time() - 5, "pid": 2 ** 22 + 12345, "dry": False})
    arrange.write_whole(KIT / ".kit" / TR.MAKE_STATUS, {"for": "feedfeedfeed", "pending": True})
    j = TR.make_for_page(KIT)
    check("a job that says it is at work and is not (stopped, the computer turned off): her \"Something went wrong making it.\", never a page left waiting",
          j["state"] == "problem" and j["problem"] == "Something went wrong making it.", j)
    arrange.write_whole(KIT / ".kit" / TR.MAKE_STATUS, {"for": "feedfeedfeed", "ok": True, "dry": False, "project": "Some reel 9",
                                                        "line": "Made \"Some reel 9\" in CapCut. Open CapCut and it's at the top of your projects."})
    j = TR.make_for_page(KIT)
    check("...but when its project did reach CapCut before it died, it is told as made (never \"went wrong\" about a reel that is there)",
          j["state"] == "done" and j["project"] == "Some reel 9" and j["words"] == ["Made \"Some reel 9\" in CapCut. Open CapCut and it's at the top of your projects."], j)
    arrange.write_whole(KIT / ".kit" / TR.MAKE_STATUS, {"for": "another0job0", "ok": True, "dry": False, "project": "Some reel 9"})
    check("...another job's status is never taken for this one's", TR.make_for_page(KIT)["state"] == "problem")
    code, ans = TR.start_make(KIT)
    check("after a dead job, the next Make it in CapCut goes ahead", code == 200 and ans["ok"] is True and wait_make(KIT)["state"] == "done", (code, ans))

    # one reel of any kind at a time on this computer; a hard limit
    import reel_page              # noqa: E402
    import this_computer          # noqa: E402
    held = open(reel_page.MAKE_LOCK, "a", encoding="utf-8")
    if this_computer.try_lock(held):
        os.environ[reel_page.TEST_LIMIT] = "3"            # the job's own process reads it: three seconds, two of grace
        n_proj = len(projects())
        t = time.time()
        code, ans = TR.start_make(KIT)
        seen = set()
        while time.time() - t < 20:
            j = TR.read_make(KIT) or {}
            seen.add(j.get("state"))
            if j.get("state") in ("done", "problem"):
                break
            time.sleep(0.1)
        os.environ.pop(reel_page.TEST_LIMIT, None)
        j = TR.make_for_page(KIT)
        check("while another reel is being made on this computer (the photo reel's own lock), the talking reel waits its turn and makes nothing",
              "running" not in seen and len(projects()) == n_proj, (seen, projects()))
        check("...and past its time it stops with her \"Something went wrong making it.\"; the wait is never without end",
              j["state"] == "problem" and j["problem"] == "Something went wrong making it." and 2.5 <= time.time() - t < 15, (j, time.time() - t))
        this_computer.unlock(held)
    else:
        skip("the talking reel waits for the computer's one reel-make turn", "no file locks on this scratch drive")
    held.close()

    # ================= her words =================
    if HERS.is_dir():
        hers_cc = (HERS / "talking_capcut.py").read_text(encoding="utf-8")
        hers_srv = (HERS / "server.py").read_text(encoding="utf-8")
        check("the maker's two lines are hers, word for word (talking_capcut.py)",
              "in CapCut. Open CapCut and it's at the top of your projects." in hers_cc and TM.MADE_LISTED.split("\" ", 1)[1] in hers_cc
              and (os.name == "nt" or TM.MADE_OPEN.split("\" ", 1)[1] in hers_cc), TM.MADE_OPEN)
        check("the make's refusals are hers, word for word (server.py)", all(f'"{w}"' in hers_srv for w in TR.MAKE_WORDS.values()),
              [w for w in TR.MAKE_WORDS.values() if f'"{w}"' not in hers_srv])
        check("her numbers are where she has them (talking_capcut.py): 1.15, 1.12, 0.704, 0.44, 0.352, 0.046, 0.073, 0.36, 0.71",
              all(x in hers_cc for x in ("PUNCH, ZOOM_TO = 1.15, 1.12", '"y": 0.44, "w": 0.704', "1 - 0.046 - 0.176", "0.073 + hf / 2", '"w": 0.36}', '"y": 0.71}')))
        ours = [w for w, _ in TR.OUR_MAKE_WORDS.values()]
        check("our lines are in none of her files (they are ours, drafts for Nicole, each with its reason)",
              not [w for w in ours if w in hers_cc or w in hers_srv] and all(len(v) == 2 and v[1] for v in TR.OUR_MAKE_WORDS.values()))
    else:
        skip("her words and numbers compared with her files", "her v24 folder is not beside the repo")
    src = "\n".join(p.read_text(encoding="utf-8") for p in (MAKER, REEL / "capcut.py"))
    check("\"Claude\" is in no line the maker can print", "Claude" not in TM.MADE_LISTED + TM.MADE_OPEN + TM.MADE_ONLY + "".join(TR.MAKE_WORDS.values()) + "".join(w for w, _ in TR.OUR_MAKE_WORDS.values()))
    check("no ffmpeg or ffprobe in the maker, and no spelled-out home folder", "ffmpeg" not in MAKER.read_text(encoding="utf-8") and "ffprobe" not in MAKER.read_text(encoding="utf-8")
          and "expanduser(\"~" not in MAKER.read_text(encoding="utf-8") and (".stu" + "dio") not in MAKER.read_text(encoding="utf-8"))
    check("capcut.py's talking builder never runs a program of its own", "subprocess" not in src[src.index("def build_talking"):src.index("ROOT_ENTRY_KEYS")])

    check("the real Assistant folder was left alone", listing(REAL) == REAL_BEFORE)
    check("the real CapCut projects folder was left alone", listing(REAL_CAPCUT) == CAPCUT_BEFORE)
    check("nothing of theirs is in the Assistant's own folder", not [p for p in STUDIO.rglob("*") if p.suffix.lower() in (".mov", ".mp4", ".png", ".jpg")])
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\n" + ("ALL PASS" if not fails else f"{fails} FAILED"))
sys.exit(1 if fails else 0)
