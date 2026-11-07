#!/usr/bin/env python3
"""The chat's footage look (studio-manager/scripts/footage.py), on small clips this test makes itself, and the
reel page showing its moments in a HIDDEN Chrome.

    python3 guard.py 800 /usr/bin/python3 tests/footage_look_check.py --work /private/tmp/somewhere [--port 9340]
        [--only scan|moments|page]

It touches video, so it runs under the 800 MB memory guard and keeps itself small: a 12-photo pretend kit
(tests/fake_kit.py) with capture times written into five of its photos, three clips made with the Mac's own
AVFoundation as tests/video_check.py makes them (an 8-second tall one, stored sideways like a phone, with the
phone's own recording time; a 6-second wide MP4 with an accent and a space in its name; a 2-second one), all
640 x 360 H.264, one solid colour a second, a tone that turns loud part way. Never a client's clip, never HEVC,
4K or anything longer.

What it checks:
  * scan: their notes and feel printed ahead of the rules; the sheets made with nothing installed (no Pillow, no
    ffmpeg or ffprobe on the way: a blocker refuses those imports and every program started is written down);
    her layout (7 across in tall cells, 4 across in wide ones), the right time on each still (each cell's colour
    is the colour of its second, its label drawn as the time AVFoundation returned), the sideways clip upright;
    the loud stretch; the photos taken while the tall clip was recording (5 s either side), and not the others;
    every look in a new folder, the first look left byte for byte as it was;
  * close: a still every half second in a new folder, the finished photo first with --photo, refusals;
  * moments: written through the command only, refused with nothing written when wrong (more than 12, a first
    moment under 3 s, a moment over 4 s, past the video's end, a video key it doesn't know, a photo not on the
    list, an order of other photos, a field it doesn't know); their own moments kept first; a style's selection
    carried to the same moment's new id, a gone one taken out; the moments of the earlier look kept in the
    record; the version before kept; Claude's footage order written;
  * the page shows the moments by itself (no reload), their own first;
  * the PC route (ASSISTANT_NO_AVFOUNDATION=1): facts, sound and clock matches, no sheets, exit 3;
  * nothing of theirs changed: the videos, the photos and kit.json are byte for byte what they were.

Every line says PASS, FAIL or SKIP; exit 1 only when something FAILED.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import zlib
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
sys.path.insert(0, str(HERE))
import chrome_drive  # noqa: E402
from chrome_drive import case, group  # noqa: E402
import reel_page_check as rpc  # noqa: E402

rpc.PHOTOS = PHOTOS = 12
KIT = rpc.KIT
KQ = KIT.replace(" ", "%20")
# the lightest hidden Chrome (tests/reel_footage_check.py's, measured there at about 600 MB by the guard's count)
LIGHT = ("--single-process", "--disable-component-extensions-with-background-pages", "--enable-features=NetworkServiceInProcess2",
         "--disable-features=Translate,MediaRouter,OptimizationHints,DialMediaRouteProvider,SpareRendererForSitePerProcess,"
         "IsolateOrigins,site-per-process,WebUIOmniboxPopup,OmniboxWebUIPopup,WebUIOmniboxFullPopup,AimServerEligibility")
ASK = "Find me lining up the shot, then the laugh at the end."
FEEL = "fun"
NOT_PREVIEW = "I can't take stills from a video on this PC yet, so I can't look through footage here."   # this_computer.NO_LOOK_CHAT

# the blocker: no Pillow (or anything like it) may be imported, and every program started is written down
BLOCKER = r'''
import os, sys
_LOG = os.environ.get("FOOT_TOOLS_LOG")
class _No:
    BANNED = ("PIL", "numpy", "cv2", "imageio", "av", "moviepy")
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.BANNED:
            if _LOG:
                with open(_LOG, "a") as f:
                    f.write("IMPORT " + name + "\n")
            raise ImportError("not installed here: " + name)
        return None
sys.meta_path.insert(0, _No())
import subprocess
_orig = subprocess.Popen.__init__
def _init(self, args, *a, **k):
    try:
        first = args if isinstance(args, str) else args[0]
        if _LOG:
            with open(_LOG, "a") as f:
                f.write("RUN " + os.path.basename(str(first)) + "\n")
    except Exception:
        pass
    _orig(self, args, *a, **k)
subprocess.Popen.__init__ = _init
'''


def vc():
    import video_check
    return video_check


def video():
    sys.path.insert(0, str(REEL))
    import video as v
    return v


def footage_mod():
    sys.path.insert(0, str(SCRIPTS))
    import footage
    return footage


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    folder = Path(folder)
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}


# ---------- the clips and the pretend photos' clocks ----------

def make_clips(folder):
    V = vc()
    folder.mkdir(parents=True, exist_ok=True)
    cols = ";".join(",".join(map(str, c)) for c in V.COLOURS)
    out = {}
    for name, secs, loud_at, rot, when in (("tall.mov", 8, 5.0, 90, V.RECORDED), ("Wide é.mp4", 6, 3.0, 0, "-"),
                                           ("short.mov", 2, 1.0, 0, "-")):
        pic = folder / ("picture-%d.mov" % secs)
        if not pic.exists():
            V.js("picture", str(pic), "640", "360", str(secs), "30", cols)
        wav = folder / ("tone-%s.wav" % name)
        V.tone_wav(wav, secs=float(secs), loud_at=loud_at)
        m4a = folder / ("tone-%s.m4a" % name)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], capture_output=True, check=True)
        V.js("compose", str(pic), str(m4a), str(folder / name), str(rot), when)
        out[name] = folder / name
    return out


def exif_jpeg(path, when):
    """Write a camera clock (DateTimeOriginal) into one of the test's own pretend photos: an Exif APP1 segment
    right after the JPEG's start, the rest of the file as it was."""
    stamp = when.strftime("%Y:%m:%d %H:%M:%S").encode() + b"\x00"
    tiff = b"II*\x00" + struct.pack("<I", 8)
    tiff += struct.pack("<H", 1) + struct.pack("<HHII", 0x8769, 4, 1, 26) + struct.pack("<I", 0)        # IFD0 -> Exif IFD
    tiff += struct.pack("<H", 1) + struct.pack("<HHII", 0x9003, 2, len(stamp), 44) + struct.pack("<I", 0)
    tiff += stamp
    seg = b"Exif\x00\x00" + tiff
    data = Path(path).read_bytes()
    assert data[:2] == b"\xff\xd8"
    Path(path).write_bytes(data[:2] + b"\xff\xe1" + struct.pack(">H", len(seg) + 2) + seg + data[2:])


def rows_of(s):
    return {x["n"]: x for x in json.loads((s.kit / ".kit" / "sheet.json").read_text())["photos"]}


# ---------- reading our own PNGs back ----------

def png_pixels(path):
    d = Path(path).read_bytes()
    assert d[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(d):
        n, kind = struct.unpack_from(">I4s", d, pos)
        body = d[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h = struct.unpack_from(">II", body)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    rows = []
    for y in range(h):
        assert raw[y * stride] == 0
        rows.append(raw[y * stride + 1:(y + 1) * stride])
    return w, h, rows


def px(rows, x, y):
    return tuple(rows[y][x * 3:x * 3 + 3])


# ---------- running the command the way Claude does ----------

class Run:
    def __init__(self, s, run):
        self.s = s
        self.block = run / "blocker"
        self.block.mkdir(parents=True, exist_ok=True)
        (self.block / "sitecustomize.py").write_text(BLOCKER)
        self.log = run / "tools.log"

    def __call__(self, *args, **env):
        e = dict(self.s.env, PATH="/usr/bin:/bin:/usr/sbin:/sbin", PYTHONPATH=str(self.block), FOOT_TOOLS_LOG=str(self.log),
                 PYTHONDONTWRITEBYTECODE="1")
        e.update(env)
        r = subprocess.run(["/usr/bin/python3", str(SCRIPTS / "footage.py"), *map(str, args)], capture_output=True, text=True, env=e,
                           timeout=300)
        return r.returncode, (r.stdout + r.stderr).strip()

    def tools(self):
        try:
            return self.log.read_text().split("\n")
        except OSError:
            return []


def record(s):
    return s.record() or {}


def rec_bytes(s):
    p = s.kit / ".kit" / "reel-page.json"
    return p.read_bytes() if p.exists() else b""


def foot(s):
    return s.http("GET", "/reel-footage?kit=" + KQ)[1] or {}


def moments_file(run, name, d):
    p = run / name
    p.write_text(json.dumps(d, ensure_ascii=False))
    return p


# ---------- 1. scan ----------

def check_out_of_time(s, run, ftool, clips):
    """Run last (it makes a look of its own): a scan whose stills run out of time."""
    n_vids = len(clips)
    # a look that runs out of time says so plainly, from where (v19 review: a cut-off look read as a whole one)
    wrap = run / "out of time.py"
    wrap.write_text(
        "import runpy, sys, time\n"
        "sys.path.insert(0, %r)\nsys.path.insert(0, %r)\n"
        "import video\n"
        "real = video._stills_now\n"
        "video._stills_now = lambda path, want, into, name, edge, quality, f, deadline, t0: real(path, want, into, name, edge, quality, f, time.time() + 0.5, t0)\n"
        "sys.argv = [%r] + sys.argv[1:]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n" % (str(REEL), str(SCRIPTS), str(SCRIPTS / "footage.py")), encoding="utf-8")
    e = dict(s.env, PATH="/usr/bin:/bin:/usr/sbin:/sbin", PYTHONPATH=str(ftool.block), FOOT_TOOLS_LOG=str(ftool.log), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(["/usr/bin/python3", str(wrap), "scan", KIT], capture_output=True, text=True, env=e, timeout=300)
    o2 = r.stdout + r.stderr
    late = json.loads(sorted((s.kit / ".kit" / "footage" / "looks").glob("*/scan.json"), key=lambda p: p.stat().st_mtime)[-1].read_text())
    case("a look that ran out of time says so for each video, from where, and how to get the rest; no sheets, exit 3",
         r.returncode == 3 and o2.count("NOTE: I ran out of time on this video from 0:00") == n_vids and "close looks from 0:00" in o2
         and all(v.get("out_of_time_from") == 0.0 for v in late["videos"]), (r.returncode, o2[-800:]))


def check_scan(s, run, ftool, clips, keys, during_want):
    F = footage_mod()
    V = vc()
    code, out = ftool("scan", KIT)
    lines = out.split("\n")
    case("scan: done (exit 0)", code == 0, out[-600:])

    def at(prefix):
        return next((i for i, x in enumerate(lines) if x.startswith(prefix)), -1)
    i_notes, i_feel, i_rules = at("Their notes for this reel"), at("They want it to feel"), at("How to choose")
    i_vid = at("1. ")
    case("their notes first, word for word, then the feel, then the rules, then the videos",
         0 <= i_notes < i_feel < i_rules < i_vid and lines[i_notes].endswith(": " + ASK) and lines[i_feel].startswith("They want it to feel fun."),
         lines[:6])
    case("the reel's photo pick is printed, the same with footage or without", "The reel's photo pick (the same with footage or without):" in out, out[:900])
    n_vids = len(clips)
    case("a line as it starts each video (v19 review: a long look said nothing until each video was done)",
         all(("(Looking at video %d of %d: " % (k, n_vids)) in out for k in range(1, n_vids + 1)), out[:1500])
    tools = ftool.tools()
    ran = sorted({x[4:] for x in tools if x.startswith("RUN ")})
    case("nothing installed: no Pillow (or anything like it) was imported", not any(x.startswith("IMPORT") for x in tools), [x for x in tools if x.startswith("IMPORT")])
    case("nothing installed: no ffmpeg or ffprobe was started, only the Mac's own tools (%s)" % ", ".join(ran),
         ran and not any("ffmpeg" in x or "ffprobe" in x for x in ran) and set(ran) <= {"sips", "osascript", "afconvert", "afinfo", "sw_vers"}, ran)
    look = s.kit / ".kit" / "footage" / "looks" / "look"
    case("the look is in a new folder of its own, with scan.json", (look / "scan.json").is_file(), sorted(os.listdir(look.parent)) if look.parent.exists() else None)
    rep = json.loads((look / "scan.json").read_text())
    by = {v["name"]: v for v in rep["videos"]}
    case("every video, in name order", [v["name"] for v in rep["videos"]] == ["Wide é.mp4", "short.mov", "tall.mov"], list(by))
    case("each video by its key, the one the page knows", all(by[n]["key"] == keys[n] for n in keys), {n: by[n]["key"] for n in by})
    tall, wide, short = by["tall.mov"], by["Wide é.mp4"], by["short.mov"]
    case("the tall clip (stored sideways) is seen upright: 360 x 640, tall, her tall layout 7 across in 216 x 384 cells",
         (tall["w"], tall["h"], tall["shape"], tall["layout"]) == (360, 640, "tall", [7, 216, 384, 14]), (tall["w"], tall["h"], tall["layout"]))
    case("the wide clip: her wide layout, 4 across in 384 x 216 cells", wide["layout"] == [4, 384, 216, 20], wide["layout"])
    case("a still every second for a short video (her every_for): 8, 6 and 2 stills",
         (len(tall["stills"]), len(wide["stills"]), len(short["stills"])) == (8, 6, 2) and tall["every"] == 1,
         (len(tall["stills"]), len(wide["stills"]), len(short["stills"])))
    case("the stills fill their cells, upright (the tall clip's 216 x 384)",
         all((x["w"], x["h"]) == (216, 384) for x in tall["stills"]) and all((x["w"], x["h"]) == (384, 216) for x in wide["stills"]),
         [(x["w"], x["h"]) for x in tall["stills"][:2] + wide["stills"][:2]])
    case("each still labelled with the time AVFoundation returned: 0:00 to 0:07",
         [x["label"] for x in tall["stills"]] == ["0:%02d" % k for k in range(8)] and all(abs(x["at"] - x["asked"]) < 0.04 for x in tall["stills"]),
         [(x["asked"], x["at"], x["label"]) for x in tall["stills"]])
    sheets_ok, colours_ok, labels_ok, bad = True, True, True, []
    for v, size in ((tall, (1560, 786)), (wide, (1566, 450)), (short, (1566, 228))):
        if len(v["sheets"]) != 1:
            sheets_ok = False
            bad.append((v["name"], "sheets", len(v["sheets"])))
            continue
        p = look / v["sheets"][0]["file"]
        w, h, rows = png_pixels(p)
        if (w, h) != size:
            sheets_ok = False
            bad.append((v["name"], "size", (w, h), size))
        for c in v["sheets"][0]["cells"]:
            pl = c["place"]
            col = px(rows, pl["x"] + pl["w"] // 2, pl["y"] + pl["h"] // 2)
            want = V.COLOURS[int(math.floor(c["at"] + 1e-6)) % len(V.COLOURS)]
            if not V.near(col, want):
                colours_ok = False
                bad.append((v["name"], c["label"], col, want))
            bw, bh = F.label_box(c["label"])
            ref = F.sheet.Canvas(bw, bh, bg=F.LABEL_BG)
            F.draw_text(ref, 6, 4, c["label"])
            for yy in range(bh):
                if rows[pl["y"] + yy][pl["x"] * 3:(pl["x"] + bw) * 3] != bytes(ref.rows[yy]):
                    labels_ok = False
                    bad.append((v["name"], "label", c["label"]))
                    break
    case("one sheet per video, a PNG of her size (1,560 px wide for tall cells, 1,566 for wide)", sheets_ok, bad)
    case("the right time on every still: each cell is the colour of its second", colours_ok, bad[:6])
    case("each cell's label on the sheet is its time, in a dark box at its top left", labels_ok, bad[:6])
    case("the sheets' file names say which video they are", tall["sheets"][0]["file"] == "03 tall - sheet 01.png"
         and wide["sheets"][0]["file"] == "01 Wide é - sheet 01.png", [v["sheets"][0]["file"] for v in (wide, short, tall)])
    case("the scan prints each sheet with the stretch it covers", "  sheet, 0:00 to 0:07: " + str(look / tall["sheets"][0]["file"]) in out, out[-900:])
    loud_t = [x["at"] for x in tall["loud"]]
    loud_w = [x["at"] for x in wide["loud"]]
    case("the loud stretch: where the tall clip's tone turns loud (5 s), within half a second", any(abs(x - 5.0) <= 0.5 for x in loud_t), loud_t)
    case("the loud stretch: the wide clip's (3 s)", any(abs(x - 3.0) <= 0.5 for x in loud_w), loud_w)
    got = {x["photo"]: x["at"] for x in tall["photos_during"]}
    case("photos taken while the tall clip was recording, 5 s either side: the three within, at their times, not the two outside",
         set(got) == set(during_want) and all(abs(got[n] - during_want[n]) < 0.15 for n in got), (got, during_want))
    case("said in plain words: the photo at 0:03, the one just before it started, the one just after it ended",
         ("photo %d at 0:03" % s.jpgs[0]) in out and ("photo %d just before it started (4 s)" % s.jpgs[1]) in out
         and ("photo %d just after it ended" % s.jpgs[2]) in out,
         [x for x in lines if "Photos taken" in x])
    case("no photo is matched to the clips the pretend photos weren't taken during", not wide["photos_during"] and not short["photos_during"],
         (wide.get("recorded"), wide["photos_during"]))
    return look


# ---------- 2. close ----------

def check_close(s, ftool, keys):
    V = vc()
    code, out = ftool("close", KIT, keys["tall.mov"], "2", "4")
    look = s.kit / ".kit" / "footage" / "looks" / "close"
    case("close: done, in a new folder of its own", code == 0 and (look / "close.json").is_file(), out[-400:])
    j = json.loads((look / "close.json").read_text()) if (look / "close.json").is_file() else {"sheets": []}
    cells = [c for x in j["sheets"] for c in x["cells"]]
    case("a still every half second, 0:02 to 0:04", [c["label"] for c in cells] == ["0:02", "0:02.5", "0:03", "0:03.5", "0:04"], [c["label"] for c in cells])
    ok = True
    if j["sheets"]:
        w, h, rows = png_pixels(look / j["sheets"][0]["file"])
        for c in cells:
            pl = c["place"]
            col = px(rows, pl["x"] + pl["w"] // 2, pl["y"] + pl["h"] // 2)
            if not V.near(col, V.COLOURS[int(math.floor(c["at"] + 1e-6)) % len(V.COLOURS)]):
                ok = False
    case("each close still is the colour of its second", ok and bool(cells))
    kept = tree(look)
    code, out = ftool("close", KIT, "tall.mov", "0:01", "0:03", "--photo", "2")
    look2 = s.kit / ".kit" / "footage" / "looks" / "close 2"
    j2 = json.loads((look2 / "close.json").read_text()) if (look2 / "close.json").is_file() else {"sheets": []}
    first = j2["sheets"][0]["cells"][0] if j2["sheets"] else {}
    case("close --photo 2 (by the file name this time): a second new folder, the finished photo first, labelled PHOTO 2",
         code == 0 and first.get("label") == "PHOTO 2" and first.get("photo") == 2 and first.get("place", {}).get("shown"), (code, first, out[-300:]))
    case("the first close look is left as it was", tree(look) == kept)
    code, out = ftool("close", KIT, "0123456789ab", "1", "2")
    case("close: a video it doesn't know is refused in plain words", code == 1 and "STOP: there's no video \"0123456789ab\"" in out, out)
    code, out = ftool("close", KIT, keys["tall.mov"], "9", "10")
    case("close: past the video's end is refused", code == 1 and "only 0:08 long" in out, out)


# ---------- 3. moments ----------

def check_moments(s, run, ftool, keys, pick):
    T, Wd, Sh = keys["tall.mov"], keys["Wide é.mp4"], keys["short.mov"]
    before = rec_bytes(s)

    def refused(what, d, words):
        code, out = ftool("moments", KIT, "--file", moments_file(run, "bad.json", d))
        case("moments refused: %s (nothing written)" % what, code == 1 and words in out and "Nothing was saved." in out and rec_bytes(s) == before,
             (code, out[-300:]))
    ok3 = {"video": T, "start": 1.0, "end": 4.5, "label": "x"}
    refused("13 moments, more than 12", {"moments": [dict(ok3, start=k * 0.1, end=k * 0.1 + 3.5) for k in range(13)]}, "the most I pick is 12")
    refused("a first moment under 3 s", {"moments": [{"video": T, "start": 1.0, "end": 3.5}]}, "never under 3 seconds")
    refused("a moment over 4 s", {"moments": [ok3, {"video": Wd, "start": 0, "end": 5}]}, "save each moment 3 to 4 seconds long")
    refused("a moment past the video's end", {"moments": [ok3, {"video": T, "start": 6.0, "end": 9.5}]}, "runs past the end of tall.mov")
    refused("a video key it doesn't know", {"moments": [{"video": "0123456789ab", "start": 0, "end": 3}]}, "there's no video \"0123456789ab\"")
    refused("a photo not on the numbered list", {"moments": [dict(ok3, photo=99)]}, "photo 99 isn't on this shoot's numbered list")
    refused("the 2-second clip, whole, as the first moment", {"moments": [{"video": Sh, "start": 0, "end": 2}]}, "never under 3 seconds")
    other = ([n for n in range(1, PHOTOS + 1) if n not in pick] or pick[:-1])[:len(pick)]
    refused("an order of other photos than the reel's pick", {"moments": [ok3], "order": ",".join(map(str, other))}, "aren't the photos picked for the reel")
    refused("an order with one of the reel's photos left out", {"moments": [ok3], "order": ",".join(map(str, pick[1:]))}, "aren't the photos picked for the reel")
    refused("a field it doesn't know", {"moments": [dict(ok3, path="/Users/x/clip.mov")]}, "nothing else")
    refused("the same moment twice", {"moments": [ok3, dict(ok3)]}, "the same as an earlier one")

    # their own moment first, from the page
    code, j, _ = s.http("POST", "/reel-moment", {"kit": KIT, "do": "add", "video": Wd, "start": 1.0, "seconds": 4})
    own = (j or {}).get("moments", [{}])[0]
    case("(their own moment, added on the page)", code == 200 and own.get("by") == "you", j)
    w1 = {"moments": [{"video": T, "start": 1.0, "end": 5.0, "label": "Lining up the shot"},
                      {"video": Wd, "start": "0:02", "end": "0:05", "label": "A laugh"},
                      {"video": Sh, "start": 0, "end": 2, "label": "A quick look back"}]}
    code, out = ftool("moments", KIT, "--file", moments_file(run, "w1.json", w1))
    rec = record(s)
    ms = rec.get("moments") or []
    case("moments saved through the command", code == 0 and "Saved 3 moments for the reel page, after their own 1." in out, out)
    case("their own moment stays first, then Claude's in its order", [m.get("by") for m in ms] == ["you", None, None, None]
         and [m.get("label") for m in ms[1:]] == ["Lining up the shot", "A laugh", "A quick look back"], [(m.get("id"), m.get("label")) for m in ms])
    case("Claude's moments: her id shape (m1-..., m2-...), 3 to 4 s, the 2-second clip used whole (not first)",
         all(re.fullmatch(r"m%d-[0-9a-f]{6}" % k, ms[k]["id"]) for k in (1, 2, 3))
         and [(m["start"], m["end"]) for m in ms[1:]] == [(1.0, 5.0), (2.0, 5.0), (0.0, 2.0)], [(m["id"], m["start"], m["end"]) for m in ms])
    case("each moment names its video by file name in the record, as the page's own do", [m["video"] for m in ms] == ["Wide é.mp4", "tall.mov", "Wide é.mp4", "short.mov"],
         [m["video"] for m in ms])
    stills = [s.kit / ".kit" / "footage" / "moments" / m["id"] for m in ms[1:]]
    case("each card's still is made, in a folder of its own", all(d.is_dir() and any(f.endswith(".jpg") for f in os.listdir(d)) for d in stills),
         [sorted(os.listdir(d)) if d.is_dir() else None for d in stills])
    page = foot(s).get("moments") or []
    case("the page's footage answer has them, each video by its key, no path",
         [m["key"] for m in page] == [Wd, T, Wd, Sh] and rpc.no_path(page),
         page)
    case("the version before is kept beside the record", (s.kit / ".kit" / "reel-page.prev.json").is_file())
    case("no footage order was written (the page uses the reel's photo pick)", "claude_bts" not in rec, rec.get("claude_bts"))

    # their selection, then a second look: carried over where it is the same moment, gone where it is not
    m1, m2, m3 = ms[1]["id"], ms[2]["id"], ms[3]["id"]
    st = s.state()
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(st, {"sel": {"first": [m1], "backforth": [m1, m2], "bookends": [own["id"], m3]}}))
    case("(their selection saved on the page)", code == 200 and (j or {}).get("ok"), j)
    rev0 = record(s).get("rev")
    order = ",".join(str(n) for n in reversed(pick))
    w2 = {"moments": [{"video": "Wide é.mp4", "start": 2.0, "end": 5.0, "label": "A laugh"},
                      {"video": T, "start": 4.0, "end": 8.0, "label": "Walking back in"}], "order": order + "+"}
    code, out = ftool("moments", KIT, "--file", moments_file(run, "w2.json", w2))
    rec = record(s)
    ms2 = rec.get("moments") or []
    case("a second look: their own still first, then the new moments", code == 0 and [m.get("label") for m in ms2][1:] == ["A laugh", "Walking back in"]
         and ms2[0]["id"] == own["id"], (out, [(m["id"], m["label"]) for m in ms2]))
    sel = (rec.get("saved") or {}).get("sel") or {}
    case("their selection: the same moment carried to its new id, a gone one taken out, a style left with none back to its default",
         sel.get("backforth") == [ms2[1]["id"]] and sel.get("bookends") == [own["id"]] and "first" not in sel and ms2[1]["id"] != m2, (sel, ms2[1]["id"], m2))
    case("the record's counter moved on once, so an open page takes the new selection", rec.get("rev") == rev0 + 1, (rev0, rec.get("rev")))
    case("Claude's moments from the first look are kept in the record, not lost", [m["id"] for m in (rec.get("earlier_looks") or [{}])[-1].get("moments", [])] == [m1, m2, m3],
         rec.get("earlier_looks"))
    case("the footage order is written as her claude_bts (the same photos as the reel's pick)",
         [x["n"] for x in rec.get("claude_bts") or []] == list(reversed(pick)) and rec["claude_bts"][-1]["h"] == "+", rec.get("claude_bts"))
    return own


# ---------- 4. the page shows them by itself ----------

def check_page(c, s, run, ftool, keys, own):
    st = s.state()
    code, j, _ = s.http("POST", "/reel-save", rpc.save_body(st, {"footage": True}))
    c.open(s.page_url())
    ok = rpc_wait(c, "document.querySelectorAll('#moments .mom').length === 3", 25)
    labels = "Array.from(document.querySelectorAll('#moments .mom .tx > b')).map(function(b){ return b.textContent; })"
    case("the page shows the moments: their own first, then Claude's", ok and c.js(labels) == [own["label"], "A laugh", "Walking back in"], c.js(labels))
    case("their own card says Your pick", c.js("!!document.querySelector('#moments .mom .yours')") and
         c.js("document.querySelector('#moments .mom').dataset.id") == own["id"])
    w3 = {"moments": [{"video": keys["tall.mov"], "start": 0.5, "end": 4.0, "label": "Walking into the frame"},
                      {"video": keys["Wide é.mp4"], "start": 1.5, "end": 4.5, "label": "Showing the back of the camera"},
                      {"video": keys["tall.mov"], "start": 4.5, "end": 8.0, "label": "The laugh at the end"}]}
    t0 = time.time()
    code, out = ftool("moments", KIT, "--file", moments_file(run, "w3.json", w3))
    ok = rpc_wait(c, "document.querySelectorAll('#moments .mom').length === 4", 15)
    took = time.time() - t0
    case("a look saved while the page is open shows up by itself, no reload (%.1f s)" % took,
         code == 0 and ok and c.js(labels) == [own["label"], "Walking into the frame", "Showing the back of the camera", "The laugh at the end"], c.js(labels))
    case("the cards' still pictures load", rpc_wait(c, "Array.from(document.querySelectorAll('#moments .mom .th img')).filter(function(i){ return i.complete && i.naturalWidth > 0; }).length === 4", 15),
         c.js("Array.from(document.querySelectorAll('#moments .mom .th img')).map(function(i){ return i.naturalWidth; })"))
    case("their count line: 3 I found and 1 you picked", "3 I found and 1 you picked." in c.js("document.getElementById('momentsSay').textContent"),
         c.js("document.getElementById('momentsSay').textContent"))
    case("no path anywhere on the page", not re.search(r"/private/|/Users/|\.kit/", c.js("document.body.innerHTML")))


def rpc_wait(c, cond, seconds):
    try:
        c.wait_for(cond, seconds)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------- 5. a second look, and the PC route ----------

def check_again(s, ftool, first_look, first_tree):
    code, out = ftool("scan", KIT)
    again = s.kit / ".kit" / "footage" / "looks" / "look 2"
    case("a second look goes in a new folder (look 2)", code == 0 and (again / "scan.json").is_file(), sorted(os.listdir(again.parent)))
    case("the first look is left byte for byte as it was", tree(first_look) == first_tree, set(tree(first_look)) ^ set(first_tree))
    case("the second look's sheets are its own (new files beside the first look's, none shared)",
         set(os.listdir(again)) >= {"scan.json", "03 tall - sheet 01.png"} and (again / "03 tall - sheet 01.png").stat().st_ino != (first_look / "03 tall - sheet 01.png").stat().st_ino)
    case("the look after their moments says their own stay first", "Their own moments, already on the page" in out, out[:1500])
    code, out = ftool("scan", KIT, ASSISTANT_NO_AVFOUNDATION="1")
    pc = s.kit / ".kit" / "footage" / "looks" / "look 3"
    pngs = [f for f in os.listdir(pc) if f.endswith(".png")] if pc.is_dir() else None
    case("the PC route: no sheets, exit 3, in plain words", code == 3 and NOT_PREVIEW in out and "no sheets were made" in out and pngs == [], (code, pngs, out[-400:]))
    case("the PC route still gives the facts, the loud moments and the photos taken while recording",
         "(key %s)" % s.keys["tall.mov"] in out and "Loudest moments" in out and ("photo %d at 0:03" % s.jpgs[0]) in out, out[-1200:])
    code, out = ftool("close", KIT, s.keys["tall.mov"], "1", "2", ASSISTANT_NO_AVFOUNDATION="1")
    case("the PC route: close says why and stops (exit 3)", code == 3 and NOT_PREVIEW in out, out)
    code, out = s.cmd("reel_page.py", "show", str(s.kit))
    case("reel_page.py show counts the looks and Claude's moments on the page", "Footage looks (footage.py scan): 3; Claude's moments on the page: 3" in out, out[-600:])


def check_skill_text():
    reel = (ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "SKILL.md").read_text()
    parts = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager"
    arr = (parts / "parts" / "arrange.md").read_text()
    pc = (parts / "parts" / "on-a-pc.md").read_text()
    core = (parts / "SKILL.md").read_text()
    sec = reel.split("## Behind-the-scenes footage", 1)[-1].split("\n## ", 1)[0]
    case("the reel skill has the footage look: the line they copy, scan, close, moments, and the page showing them by itself",
         all(x in sec for x in ("\"Look through my footage for <shoot>\"", "\" and follow my notes\"", "footage.py scan \"<kit>\"",
                                "footage.py close \"<kit>\" <key> <from> <to>", "footage.py moments \"<kit>\" --file",
                                "The page shows the moments by itself")), sec[:300])
    case("her footage rules are in it: photos first and the same with footage or without, never matched or limited to the footage's setting",
         all(x in sec for x in ("the same with footage or without", "Never choose, leave out or move a photo because of a clip",
                                "never limit the photos to the setting the footage shows")))
    case("... the best moments, up to 12; judged on how they look, no banned kinds; their notes first; the feel steers; 3 to 4 s, the first never under 3",
         all(x in sec for x in ("up to 12", "Judge each moment on how it looks", "no banned kinds of moment", "Their notes come first",
                                "The feel steers", "3 to 4 seconds", "never under 3 seconds")))
    case("... how many looks: the sheets once each, a handful of close looks, never frame by frame",
         "Read every sheet once" in sec and "a handful at most" in sec and "never at frames one by one" in sec)
    case("the skill names no photographer \"she\" or \"he\"", not re.search(r"\b(she|he)\b", sec, re.I), re.findall(r"\b(she|he)\b", sec, re.I)[:5])
    case("parts/arrange.md sends the footage look to the reel skill (no \"not built yet\" left)",
         "not built yet" not in arr and "Behind-the-scenes footage" in arr and "footage.py moments" in arr)
    case("parts/on-a-pc.md says what to do on a PC (exit 3, no sheets, never choose without seeing)", "stops with exit 3" in pc and "Never choose moments without seeing them" in pc)
    case("the core table routes \"look through my footage\" (and \"... and follow my notes\")", "\"look through my footage for <shoot>\" (and \"... and follow my notes\")" in core)


def check_untouched(s, before):
    now = {p.name: sha(p) for p in (s.kit / "Footage").iterdir() if p.is_file()}
    case("the videos are byte for byte what was dropped in", now == before["footage"], set(now) ^ set(before["footage"]))
    photos = {p.name: sha(p) for p in (s.kit / "Photos").iterdir() if p.is_file()}
    case("the photos are byte for byte what they were (the look only reads them)", photos == before["photos"])
    case("kit.json is byte for byte what it was (commands write it, never the look)", s.kit_hash() == before["kit"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", required=True, help="a folder under /private/tmp for this run (made if missing)")
    ap.add_argument("--port", type=int, default=9340)
    ap.add_argument("--only", choices=("scan", "moments", "page"))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if Path("/private/tmp") not in work.parents:
        print("STOP: --work must be under /private/tmp")
        return 2
    group("the skill text", check_skill_text)
    if not Path("/usr/bin/sips").exists():
        print("SKIP  everything: the clips and the pretend kit are made with the Mac's own tools", flush=True)
        return 0
    run = work / time.strftime("look-%H%M%S")
    run.mkdir(parents=True)
    clips = make_clips(run / "clips")
    V = video()
    s = rpc.Setup(run, a.port)
    s.make()
    rows = rows_of(s)
    start = V.recorded_local(V.facts(clips["tall.mov"]))
    # five of the pretend kit's plain JPEGs get a camera clock, in seconds from when the tall clip started (8 s long):
    # 3 s in, 4 s before, 4 s after its end (all three within 5 s), 8 s before and 7 s after its end (neither)
    jpgs = [n for n, r in sorted(rows.items()) if Path(r["file"]).suffix.lower() in (".jpg", ".jpeg")
            and "sideways" not in r["file"] and "small" not in r["file"]][:5]
    for n, off in zip(jpgs, (3, -4, 12, -8, 15)):
        exif_jpeg(s.kit / "Photos" / Path(rows[n]["file"]).name, start + timedelta(seconds=off))
    during_want = {jpgs[0]: 3.0, jpgs[1]: -4.0, jpgs[2]: 12.0}
    s.jpgs = jpgs
    ftool = Run(s, run)
    s.start()
    try:
        case("the page server is on a port of this test's own (%d)" % s.port, a.port <= s.port < a.port + 10)
        code, out = s.cmd("reel_page.py", "open", str(s.kit))
        case("(set up: the page's small copies made first)", code == 0, out[-200:])
        code, out = ftool("scan", KIT)
        case("scan before there is any footage: STOP, in plain words", code == 1 and "STOP: there's no footage yet." in out, out)
        s.http("POST", "/reel-open", {"kit": KIT, "what": "footage"})
        for name, p in clips.items():
            shutil.copy(p, s.kit / "Footage" / name)
        s.keys = keys = {v["name"]: v["key"] for v in (foot(s).get("videos") or [])}
        case("(the three clips are in the Footage folder, each with its key)", sorted(keys) == sorted(clips), keys)
        st = s.state()
        code, j, _ = s.http("POST", "/reel-save", rpc.save_body(st, {"ask": ASK, "feel": FEEL}))
        case("(their notes and feel saved on the page)", code == 200 and (j or {}).get("ok"), j)
        before = {"footage": {p.name: sha(p) for p in (s.kit / "Footage").iterdir() if p.is_file()},
                  "photos": {p.name: sha(p) for p in (s.kit / "Photos").iterdir() if p.is_file()}, "kit": s.kit_hash()}
        pick = json.loads((s.kit / ".kit" / "kit.json").read_text())["picks"]["reel"]
        first_look = group("scan", check_scan, s, run, ftool, clips, keys, during_want)
        first_tree = tree(first_look) if first_look else {}
        if a.only == "scan":
            return rpc.summary()
        group("close looks", check_close, s, ftool, keys)
        own = group("moments", check_moments, s, run, ftool, keys, pick)
        if a.only == "moments":
            return rpc.summary()
        if not chrome_drive.find_chrome():
            print("SKIP  the page in a browser: no Chrome on this computer", flush=True)
        elif own:
            with chrome_drive.Chrome(work=str(run), size=(820, 900), extra_args=LIGHT) as c:
                group("the page shows them by itself", check_page, c, s, run, ftool, keys, own)
        if a.only == "page":
            return rpc.summary()
        if first_look:
            group("a second look, and the PC route", check_again, s, ftool, first_look, first_tree)
        group("a look that runs out of time", check_out_of_time, s, run, ftool, clips)
        group("nothing of theirs changed", check_untouched, s, before)
    finally:
        s.stop()
    return rpc.summary()


if __name__ == "__main__":
    sys.exit(main())
