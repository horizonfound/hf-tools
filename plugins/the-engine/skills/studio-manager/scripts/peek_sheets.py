#!/usr/bin/env python3
"""Thin a shoot down to its moments and lay them out on numbered pages, so Claude can pick the
sneak peeks with a few looks instead of thousands (rule 6: scripts shortlist, Claude looks).

    python3 peek_sheets.py make "<backup folder or records>" [--gap 3] [--max 100] [--per-page 20]
    python3 peek_sheets.py closer "<backup>" s1=14,3,27,9,41,18,22,5,61,70 [s2=...]
    python3 peek_sheets.py pick "<backup>" s1=14,3,27,9,41,18 [s2=...] [--by "Claude, from the pages"]

make: for every shoot, one frame per burst (a new burst starts after --gap seconds of quiet;
the middle frame of each burst is kept), at most --max moments spread across the shoot, a small
preview of each (the Mac's own sips, nothing installed; on a PC, pictures.py and Pillow) into
records/peeks/<shoot>/, and pages of --per-page numbered thumbnails into
records/peek-sheets/<shoot>-p1.png, -p2.png ...
A list of what is on each page goes in records/peek-sheets.json.

closer: a shortlist (ten or so per shoot) laid out big, four to a page at full preview size, into
records/peek-sheets/<shoot>-close1.png ..., so soft focus, a blink or a half-closed eye and an
awkward expression can be seen before anything is chosen (the small pages hide all three).
On a Mac it first asks the Mac's own Vision about the biggest face in each photo (eyes open or
half-closed, mouth open or closed, facing or turned away) and writes the verdict on the page beside
the number, in red when it is a fault, and into records/peek-faces.json (Dustin, Nov 12: the rule
against half-closed eyes and an open mouth was there and a hero was picked with both; a measured
check comes first now, rule 6). A PC has no Vision: the page says so and only the look remains.

pick: turn the numbers Claude chose (the first is the hero) into records/sneak-peeks.json, in the
shape sneak_peeks.py and the report read. Shoots not mentioned keep what they had. A pick by the
Assistant needs one checked line per photo (--checked "s1 29: eyes open to camera, mouth closed,
sharp, nothing cut off", or --checked-file), each saying what was seen of the eyes and the mouth;
a photo the face check flagged is refused unless its line starts "anyway:" and says why, and the
hero is never a flagged or turned-away face. The photographer's own choice (--by photographer)
needs none of that.
Reads the verified copy only. Nothing on the card is ever opened, nothing is changed anywhere.
Exit codes: 0 done, 1 a problem, 2 nothing to do.
"""
import argparse
import base64
import errno
import json
import struct
import os
from datetime import datetime
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
sys.path.insert(0, str(HERE))
from where import locate  # noqa: E402
import sheet  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import pictures  # noqa: E402  (every small picture, on a Mac or a PC)
this_computer.utf8_output()

PHOTO = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".rw2", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}


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


def preview(src, dst, size):
    """A small JPEG of the photo: the Mac's own sips, or on a PC the JPEG inside the RAW and Pillow."""
    return pictures.make_jpeg(src, dst, size, 80)


def thumb_rows(src, size, tmp):
    """(w, h, rows) for the page: sips to BMP on a Mac, Pillow on a PC (both through sheet.thumb)."""
    return sheet.thumb(src, size, tmp)


def save_json(path, data, **kw):
    """Written whole, then given its name, so the report's page server never reads half a list. The scratch
    name is this process's and this thread's own, so two saves at once (the page and a command) never mix."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}-{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, **kw), encoding="utf-8")
    this_computer.replace(tmp, path)


def seconds(iso):
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError, OSError, OverflowError):   # OSError: a PC refuses times before 1970 (a camera clock never set)
        return None


def moments(photos, gap):
    """One photo per burst: a burst is frames less than `gap` seconds apart; keep the middle frame."""
    out, burst = [], []
    last = None
    for p in photos:
        t = p["_t"]
        if last is not None and t - last > gap and burst:
            out.append(burst[len(burst) // 2])
            burst = []
        burst.append(p)
        last = t
    if burst:
        out.append(burst[len(burst) // 2])
    return out


def spread(items, n):
    if len(items) <= n:
        return items
    step = (len(items) - 1) / (n - 1)
    return [items[round(i * step)] for i in range(n)]


def make(night, gap, cap, per_page, size):
    ok, words = pictures.ready()
    if not ok:
        say(f"STOP: {words}")
        return 1
    root, studio = locate(night)
    index = json.loads((studio / "index.json").read_text(encoding="utf-8"))
    groups = {g["id"]: g for g in json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]}
    shoots = json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    by_file = {p["file"]: p for p in index["photos"]}
    out_dir = studio / "peek-sheets"
    out_dir.mkdir(exist_ok=True)
    tmp = out_dir / ".tmp.bmp"
    result = {"gap_seconds": gap, "per_page": per_page, "shoots": {}}
    cols, rows_per = 5, max(1, per_page // 5)
    cell_w, cell_h, pad, label_h = size, int(size * 1.0), 8, 26
    for s in shoots:
        files = [f for g in s.get("groups", []) if g in groups for f in groups[g].get("files", [])]
        photos = []
        for f in files:
            p = by_file.get(f)
            if not p or Path(f).suffix.lower() not in PHOTO:
                continue
            t = seconds(p.get("taken"))
            if t is None:
                continue
            photos.append({"file": f, "taken": p["taken"], "_t": t})
        photos.sort(key=lambda p: (p["_t"], p["file"]))
        chosen = spread(moments(photos, gap), cap)
        pdir = studio / "peeks" / s["id"]
        pdir.mkdir(parents=True, exist_ok=True)
        listed, unshown = [], []
        for i, p in enumerate(chosen, 1):
            dst = pdir / f"{i:03d}.jpg"
            if dst.exists() or preview(root / p["file"], dst, 700):
                listed.append({"n": i, "file": p["file"], "taken": p["taken"], "preview": f"peeks/{s['id']}/{dst.name}"})
            else:
                why = pictures.why_not(root / p["file"])
                if why:
                    unshown.append(why)
        pages = []
        for pi in range(0, len(listed), per_page):
            chunk = listed[pi:pi + per_page]
            W = cols * (cell_w + pad) + pad
            H = rows_per * (cell_h + label_h + pad) + pad
            cv = sheet.Canvas(W, H)
            for j, m in enumerate(chunk):
                cx, cy = j % cols, j // cols
                x = pad + cx * (cell_w + pad)
                y = pad + cy * (cell_h + label_h + pad)
                cv.rect(x, y, cell_w, label_h, (40, 40, 40))
                cv.text(x + 6, y + 4, f"{m['n']}", scale=2, color=(240, 127, 90))
                t = thumb_rows(studio / m["preview"], size, tmp)
                if not t:
                    continue
                w, h, rws = t
                if h > cell_h:
                    rws = rws[(h - cell_h) // 2:(h - cell_h) // 2 + cell_h]
                    h = cell_h
                cv.paste(x + max(0, (cell_w - w) // 2), y + label_h + max(0, (cell_h - h) // 2), w, h, rws)
            page = out_dir / f"{s['id']}-p{pi // per_page + 1}.png"
            sheet.write_png(page, W, H, cv.rows)
            pages.append(str(page))
        result["shoots"][s["id"]] = {"name": s.get("name") or s.get("suggested", ""), "photos": len(photos),
                                     "moments": len(listed), "pages": pages, "list": listed}
        say(f"{s['id']} {s.get('name') or s.get('suggested', '')}: {len(photos):,} photos, {len(listed)} moments on {len(pages)} page(s)")
        for why in sorted(set(unshown)):
            say(f"   {unshown.count(why)} could not be shown here: {why}")
    if tmp.exists():
        tmp.unlink()
    save_json(studio / "peek-sheets.json", result, indent=1, ensure_ascii=False)
    return 0


# ---------------------------------------------------------------- the face check (a Mac; nothing on a PC yet)
# The Mac's own Vision, asked about each shortlist photo: the biggest face's eye and mouth landmarks, how far it is
# turned (yaw) and tipped (pitch), and Apple's face capture quality. Landmark points come back as raw bytes (the
# JavaScript bridge cannot index a C array, but NSData can wrap one), decoded here. Only the Assistant's own small
# previews are ever read.
FACES_JS = r"""
ObjC.import('Vision'); ObjC.import('Foundation'); ObjC.import('AppKit');
function region(r) {
  if (!r || r.isNil()) return null;
  var n = r.pointCount; if (!n) return null;
  var d = $.NSData.dataWithBytesLength(r.normalizedPoints, n * 16);
  return ObjC.unwrap(d.base64EncodedStringWithOptions(0));
}
function deg(x) { return (x && !x.isNil()) ? x.doubleValue * 57.2958 : null; }
function box(b) { return [b.origin.x, b.origin.y, b.size.width, b.size.height]; }
function run(argv) {
  var all = [];
  for (var a = 0; a < argv.length; a++) {
    var out = {size: null, faces: [], pose: [], quality: []};
    try {
      var url = $.NSURL.fileURLWithPath(argv[a]);
      var rep = $.NSImageRep.imageRepWithContentsOfURL(url);
      if (rep && !rep.isNil()) out.size = [rep.pixelsWide, rep.pixelsHigh];
      var h = $.VNImageRequestHandler.alloc.initWithURLOptions(url, $());
      var lm = $.VNDetectFaceLandmarksRequest.alloc.init;
      var rc = $.VNDetectFaceRectanglesRequest.alloc.init; rc.revision = 3;
      var q = $.VNDetectFaceCaptureQualityRequest.alloc.init;
      h.performRequestsError($([lm, rc, q]), Ref());
      var r = lm.results, i;
      if (r && !r.isNil()) for (i = 0; i < r.count; i++) {
        var f = r.objectAtIndex(i), L = f.landmarks, ok = (L && !L.isNil());
        out.faces.push({conf: f.confidence, box: box(f.boundingBox),
          leftEye: ok ? region(L.leftEye) : null, rightEye: ok ? region(L.rightEye) : null, innerLips: ok ? region(L.innerLips) : null});
      }
      r = rc.results;
      if (r && !r.isNil()) for (i = 0; i < r.count; i++) { var g = r.objectAtIndex(i);
        out.pose.push({box: box(g.boundingBox), yaw: deg(g.yaw), pitch: deg(g.pitch), roll: deg(g.roll)}); }
      r = q.results;
      if (r && !r.isNil()) for (i = 0; i < r.count; i++) { var g2 = r.objectAtIndex(i);
        out.quality.push({box: box(g2.boundingBox), quality: (g2.faceCaptureQuality && !g2.faceCaptureQuality.isNil()) ? g2.faceCaptureQuality.doubleValue : null}); }
    } catch (err) { out.err = String(err); }
    all.push(out);
  }
  return JSON.stringify(all);
}
"""
FACES = "peek-faces.json"
SMALL_FACE = 0.004      # a face under this share of the picture is too small to judge (about 6% of each side)
EYES_SHUT = 0.185       # eye height over width, both eyes averaged: below this the eyes are half-closed, shut or down
EYES_HEAVY = 0.215      # ... below this they look a little heavy (said, not a fault)
MOUTH_OPEN = 0.25       # inner-lip height over width: above this the mouth is open
TURNED = 30.0           # degrees of yaw past which the face is looking away (said; the hero may not)
TURNED_TOO_FAR = 40.0   # ... past which the eye and mouth measurements are not trusted
TIPPED = 20.0           # degrees of pitch past which the face is looking down (+) or up (-)
# Calibrated once, on the 16-photo palm grove shortlist of Nov 12 (open eyes 0.22 to 0.28, half-closed 0.13 to
# 0.17; an open mouth 0.44, closed under 0.1). First numbers, to be moved as real shoots show where they belong.


def _points(b64):
    if not b64:
        return None
    raw = base64.b64decode(b64)
    return [struct.unpack("<dd", raw[i:i + 16]) for i in range(0, len(raw) - 15, 16)]


def _ratio(pts, box, size, corners, pairs):
    """Height over width of a landmark region, in pixels: the points are fractions of the face box, the box a
    fraction of the (oriented) picture. corners: the two end points; pairs: top/bottom point pairs."""
    if not pts or max(max(corners), max(max(p) for p in pairs)) >= len(pts):
        return None
    W, H = size
    px = [((box[0] + x * box[2]) * W, (box[1] + y * box[3]) * H) for x, y in pts]
    d = lambda a, b: ((px[a][0] - px[b][0]) ** 2 + (px[a][1] - px[b][1]) ** 2) ** 0.5
    w = d(*corners)
    if w <= 0:
        return None
    return sum(d(a, b) for a, b in pairs) / len(pairs) / w


def measure(raw):
    """What Vision measured on the biggest face in one picture, as plain numbers: {"face": share of the picture,
    "eyes": openness, "mouth": openness, "yaw", "pitch", "quality"}; None when there is no face."""
    if not raw or not raw.get("size") or not raw.get("faces"):
        return None
    size = [float(raw["size"][0]), float(raw["size"][1])]
    if size[0] <= 0 or size[1] <= 0:
        return None
    faces = [f for f in raw["faces"] if f.get("conf", 0) >= 0.5 and f.get("box")]
    if not faces:
        return None
    f = max(faces, key=lambda x: x["box"][2] * x["box"][3])
    box = f["box"]
    # Vision's eye: 6 points, the corners first and fourth, two along the top then two along the bottom.
    # Its inner lips: 6 points, left corner, top middle, right corner (twice), bottom middle, left corner.
    left = _ratio(_points(f.get("leftEye")), box, size, (0, 3), [(1, 5), (2, 4)])
    right = _ratio(_points(f.get("rightEye")), box, size, (0, 3), [(1, 5), (2, 4)])
    eyes = [e for e in (left, right) if e is not None]
    mouth = _ratio(_points(f.get("innerLips")), box, size, (0, 3), [(1, 4)])

    def nearest(items):
        best, dist = None, 9e9
        for it in items:
            b = it.get("box") or [0, 0, 0, 0]
            dd = (b[0] - box[0]) ** 2 + (b[1] - box[1]) ** 2
            if dd < dist:
                best, dist = it, dd
        return best
    pose = nearest(raw.get("pose") or []) or {}
    qual = nearest(raw.get("quality") or []) or {}
    return {"face": round(box[2] * box[3], 4), "eyes": round(sum(eyes) / len(eyes), 3) if eyes else None,
            "mouth": round(mouth, 3) if mouth is not None else None,
            "yaw": round(pose["yaw"], 1) if pose.get("yaw") is not None else None,
            "pitch": round(pose["pitch"], 1) if pose.get("pitch") is not None else None,
            "quality": round(qual["quality"], 3) if qual.get("quality") is not None else None}


def judge(m):
    """The verdict on one measured face, in plain words: {"flags": faults that refuse the photo, "notes": things
    worth knowing, "words": the line for the page, "judged": whether the face was big enough to judge}."""
    if m is None:
        return {"judged": False, "flags": [], "notes": [], "words": "no face found"}
    if m["face"] < SMALL_FACE:
        return {"judged": False, "flags": [], "notes": [], "words": "face too small to judge"}
    flags, notes, words = [], [], []
    yaw = m.get("yaw")
    turned = yaw is not None and abs(yaw) > TURNED_TOO_FAR
    if turned:
        words.append("turned away, eyes and mouth not judged")
        notes.append("looking away")
    else:
        e = m.get("eyes")
        if e is None:
            words.append("eyes not found")
        elif e < EYES_SHUT:
            flags.append("eyes half-closed, shut or down"); words.append("EYES HALF-CLOSED OR DOWN")
        elif e < EYES_HEAVY:
            notes.append("eyes a little heavy"); words.append("eyes a little heavy")
        else:
            words.append("eyes open")
        mo = m.get("mouth")
        if mo is None:
            words.append("mouth not found")
        elif mo > MOUTH_OPEN:
            flags.append("mouth open"); words.append("MOUTH OPEN")
        else:
            words.append("mouth closed")
        if yaw is not None and abs(yaw) > TURNED:
            notes.append("looking away"); words.append("looking away")
        elif yaw is not None:
            words.append("facing")
    pitch = m.get("pitch")
    if pitch is not None and pitch > TIPPED:
        notes.append("looking down"); words.append("looking down")
    elif pitch is not None and pitch < -TIPPED:
        notes.append("looking up"); words.append("looking up")
    return {"judged": True, "flags": flags, "notes": notes, "words": " · ".join(words)}


def look_at_faces(paths):
    """Vision's raw answer for each picture (a Mac), or None when this computer cannot ask (a PC, or Vision
    failing). PEEK_FACES_PRETEND=<json file> (tests only) answers from a file instead: {"s1/001.jpg": measured
    numbers or null}, handed straight to judge()."""
    pretend = os.environ.get("PEEK_FACES_PRETEND")
    if pretend:
        try:
            table = json.loads(Path(pretend).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return [{"pretend": table.get(f"{Path(p).parent.name}/{Path(p).name}", table.get(Path(p).name, "missing"))} for p in paths]
    if not this_computer.MAC:
        return None
    try:
        r = this_computer.mac_javascript(FACES_JS, [str(p) for p in paths], timeout=120)
        if not r or r[0] != 0:
            return None
        got = json.loads(r[1])
        return got if isinstance(got, list) and len(got) == len(paths) else None
    except Exception:  # noqa: BLE001
        return None


def faces_file(studio):
    return studio / FACES


def read_faces(studio):
    f = faces_file(studio)
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        return {}


def check_faces(studio, sid, moments):
    """Ask about these moments of one shoot and record the verdicts in records/peek-faces.json under the shoot
    (earlier verdicts for other photos of the shoot are kept). Returns {n: verdict}, or {} when this computer
    could not ask."""
    paths = [studio / m["preview"] for m in moments]
    raw = look_at_faces(paths)
    if raw is None:
        return {}
    out = {}
    for m, r in zip(moments, raw):
        if "pretend" in r:
            measured = None if r["pretend"] in (None, "missing") else r["pretend"]
        else:
            measured = measure(r)
        v = judge(measured)
        v["measured"] = measured
        out[str(m["n"])] = v
    all_faces = read_faces(studio)
    all_faces.setdefault(sid, {}).update(out)
    all_faces["checked_on"] = datetime.now().isoformat(timespec="seconds")
    save_json(faces_file(studio), all_faces, indent=1, ensure_ascii=False)
    return out


def closer(night, picks):
    """The shortlist, big: two columns, each photo at its full 700 px preview size, four to a page, with the face
    check's verdict beside each number."""
    ok, words = pictures.ready()
    if not ok:
        say(f"STOP: {words}")
        return 1
    root, studio = locate(night)
    sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    out_dir = studio / "peek-sheets"
    tmp = out_dir / ".tmp.bmp"
    cols, per_page, cell, pad, label_h = 2, 4, 700, 10, 28
    short_f = studio / "peek-shortlist.json"
    try:
        shortlist = json.loads(short_f.read_text(encoding="utf-8")) if short_f.exists() else {}
    except ValueError:
        shortlist = {}
    for spec in picks:
        sid, _, nums = spec.partition("=")
        if sid not in sheets:
            say(f"STOP: no shoot {sid} on the pages.")
            return 1
        by_n = {m["n"]: m for m in sheets[sid]["list"]}
        want = []
        for n in [x.strip() for x in nums.split(",") if x.strip()]:
            m = by_n.get(int(n)) if n.isdigit() else None
            if not m:
                say(f"STOP: {sid} has no photo numbered {n}.")
                return 1
            want.append(m)
        shortlist[sid] = [m["n"] for m in want]   # kept, so "Show me more" on the report can offer them
        save_json(short_f, shortlist, indent=1)
        verdicts = check_faces(studio, sid, want)
        if not verdicts:
            say(f"{sid}: no face check on this computer (the Mac's Vision is not here); the look is all there is.")
        pages = []
        for pi in range(0, len(want), per_page):
            chunk = want[pi:pi + per_page]
            rows_per = (len(chunk) + cols - 1) // cols
            W = cols * (cell + pad) + pad
            H = rows_per * (cell + label_h + pad) + pad
            cv = sheet.Canvas(W, H)
            for j, m in enumerate(chunk):
                cx, cy = j % cols, j // cols
                x = pad + cx * (cell + pad)
                y = pad + cy * (cell + label_h + pad)
                cv.rect(x, y, cell, label_h, (40, 40, 40))
                cv.text(x + 6, y + 4, f"{m['n']}", scale=3, color=(240, 127, 90))
                v = verdicts.get(str(m["n"]))
                if v:
                    color = (235, 90, 80) if v["flags"] else (235, 190, 90) if v["notes"] else (150, 200, 150) if v["judged"] else (160, 160, 160)
                    label = v["words"]
                else:
                    color, label = (160, 160, 160), "no face check on this computer"
                cv.text(x + 6 + len(str(m["n"])) * 18 + 14, y + 7, label[:52], scale=2, color=color)
                t = thumb_rows(studio / m["preview"], cell, tmp)
                if not t:
                    continue
                w, h, rws = t
                cv.paste(x + max(0, (cell - w) // 2), y + label_h + max(0, (cell - h) // 2), w, h, rws)
            page = out_dir / f"{sid}-close{pi // per_page + 1}.png"
            sheet.write_png(page, W, H, cv.rows)
            pages.append(str(page))
        say(f"{sid}: {len(want)} up close on {len(pages)} page(s)")
        for pg in pages:
            say(f"   {pg}")
        if verdicts:
            say(f"   The Mac's face check, {sid} (the same words are on the pages; a line in capitals is a fault that pick will refuse):")
            for m in want:
                v = verdicts.get(str(m["n"]))
                if v:
                    say(f"      {m['n']}: {v['words']}")
    if tmp.exists():
        tmp.unlink()
    return 0


def current_path(studio, f):
    """The photo's path now, if a rename moved it since the pages were made: same shoot number and
    camera frame name, read from the index (which every rename keeps up to date)."""
    try:
        index = json.loads((studio / "index.json").read_text(encoding="utf-8"))["photos"]
    except (OSError, ValueError):
        return f
    stem = Path(f).stem
    tail = "_".join(stem.split("_")[-3:]) if stem.count("_") >= 2 else stem  # NNNN_<camera frame>
    for p in index:
        if p["file"] == f:
            return f
    for p in index:
        if Path(p["file"]).stem.endswith(tail):
            return p["file"]
    return f


def candidates(night, sid, everything=False):
    """For the report's "Show me more": the close-look shortlist for a shoot (or, before one exists or when
    they ask to see every moment, all of its pages), each with its number and its preview path."""
    root, studio = locate(night)
    sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    if sid not in sheets:
        return None
    short_f = studio / "peek-shortlist.json"
    try:
        short = json.loads(short_f.read_text(encoding="utf-8")).get(sid) if short_f.exists() else None
    except ValueError:
        short = None
    by_n = {m["n"]: m for m in sheets[sid]["list"]}
    nums = ([] if everything else [n for n in (short or []) if n in by_n]) or sorted(by_n)
    pj = studio / "sneak-peeks.json"
    picked = []
    if pj.exists():
        picked = [p["n"] for p in json.loads(pj.read_text(encoding="utf-8")).get("picks", []) if p.get("shoot") == sid and "n" in p]
    for n in picked:   # the current picks are always offered, even if the shortlist was drawn before them
        if n in by_n and n not in nums:
            nums.append(n)
    return {"shoot": sid, "picked": picked, "from_shortlist": bool(short) and not everything, "moments": len(by_n),
            "photos": [{"n": n, "preview": by_n[n]["preview"], "taken": by_n[n].get("taken")} for n in nums]}


def taste_file():
    return HOME / "taste-notes.md"


def add_taste_note(line):
    """One line into the photographer's taste notes (Claude reads them before every pick)."""
    f = taste_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_text("# Taste notes\n\nWhat you've told the Assistant about the photos you like, one line a time. It reads this before picking sneak peeks.\n\n", encoding="utf-8")
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(f"- {datetime.now().strftime('%Y-%m-%d')}: {line.strip()}\n")


def ask_again(night, sid, note):
    """The report's "Pick again": remember the ask (Claude does the re-pick when they next talk) and keep
    the note as taste."""
    root, studio = locate(night)
    f = studio / "peeks-asks.json"
    try:
        asks = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except ValueError:
        asks = []
    asks = [a for a in asks if a.get("shoot") != sid]
    asks.append({"shoot": sid, "note": note.strip(), "at": datetime.now().isoformat(timespec="seconds"), "done": False})
    save_json(f, asks, indent=1, ensure_ascii=False)
    if note.strip():
        shoots = {}
        try:
            shoots = {x["id"]: x for x in json.loads((studio / "shoots.json").read_text(encoding="utf-8"))["shoots"]}
        except (OSError, ValueError, KeyError):
            pass
        name = shoots.get(sid, {}).get("name") or sid
        add_taste_note(f"{name}: asked for different sneak peeks: \"{note.strip()}\"")
    return len(asks)


def pending_asks(night):
    root, studio = locate(night)
    f = studio / "peeks-asks.json"
    try:
        asks = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except ValueError:
        asks = []
    return [a for a in asks if not a.get("done")]


def mark_asked_done(night, sid):
    root, studio = locate(night)
    f = studio / "peeks-asks.json"
    try:
        asks = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except ValueError:
        return
    for a in asks:
        if a.get("shoot") == sid:
            a["done"] = True
    save_json(f, asks, indent=1, ensure_ascii=False)


def checked_lines(lines, text_file, shoots):
    """The Assistant's checked lines, one per photo: "s1 29: eyes open to camera, mouth closed, sharp" (also
    "s1-29:"; just "29:" when the pick names one shoot). {(sid, n): words}, or a STOP line as a string."""
    raw = list(lines or [])
    if text_file:
        try:
            raw += Path(text_file).read_text(encoding="utf-8-sig").splitlines()
        except OSError as e:
            return f"STOP: could not read the checked lines: {e}"
    out = {}
    for line in raw:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head, sep, words = line.partition(":")
        if not sep:
            return f"STOP: a checked line needs a photo number, a colon, then what you saw: {line[:60]}"
        head = head.strip().replace("-", " ").replace("\u00b7", " ").split()
        if len(head) == 2 and head[1].isdigit():
            sid, n = head[0], int(head[1])
        elif len(head) == 1 and head[0].isdigit() and len(shoots) == 1:
            sid, n = next(iter(shoots)), int(head[0])
        elif len(head) == 1 and head[0].isdigit():
            return f"STOP: the pick names {len(shoots)} shoots, so each checked line needs the shoot too (s1 {head[0]}: ...)."
        else:
            return f"STOP: a checked line starts with the shoot and the photo number (s1 29: ...): {line[:60]}"
        out[(sid, n)] = words.strip()
    return out


def pick(night, picks, by, checked=None, checked_file=None):
    root, studio = locate(night)
    sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    pj = studio / "sneak-peeks.json"
    existing = json.loads(pj.read_text(encoding="utf-8")).get("picks", []) if pj.exists() else []
    chosen_shoots = set()
    new = []
    for spec in picks:
        sid, _, nums = spec.partition("=")
        if sid not in sheets:
            say(f"STOP: no shoot {sid} on the pages.")
            return 1
        by_n = {m["n"]: m for m in sheets[sid]["list"]}
        for n in [x.strip() for x in nums.split(",") if x.strip()]:
            m = by_n.get(int(n)) if n.isdigit() else None
            if not m:
                say(f"STOP: {sid} has no photo numbered {n}.")
                return 1
            new.append({"file": current_path(studio, m["file"]), "shoot": sid, "n": m["n"]})
        chosen_shoots.add(sid)
    if by != "photographer":
        # The Assistant's own pick: the close look cannot be skipped (Dustin, Nov 12). One checked line per photo
        # saying what was seen of the eyes and the mouth; nothing the face check flagged, unless the line starts
        # "anyway:" and says why; the hero never flagged, never turned away.
        lines = checked_lines(checked, checked_file, chosen_shoots)
        if isinstance(lines, str):
            say(lines)
            return 1
        faces = read_faces(studio)
        problems = []
        for i, pk in enumerate(new):
            key = (pk["shoot"], pk["n"])
            name = f"{pk['shoot']} {pk['n']}"
            words = lines.get(key)
            if not words:
                problems.append(f"{name}: no checked line. Look at it up close and say what you saw (eyes, mouth, focus, edges, crew).")
                continue
            low = words.lower()
            if "eye" not in low or "mouth" not in low:
                problems.append(f"{name}: the checked line must say what you saw of the eyes and the mouth ({words[:50]}).")
            anyway = low.startswith("anyway")
            shoot_faces = faces.get(pk["shoot"])
            v = (shoot_faces or {}).get(str(pk["n"]))
            if this_computer.MAC and shoot_faces is None:
                problems.append(f"{name}: the close look was skipped (no face check for {pk['shoot']}). Run closer on your shortlist first.")
            elif this_computer.MAC and v is None:
                problems.append(f"{name}: not on the close-look pages (no face check). Put it through closer first.")
            hero = (i == 0 or new[i - 1]["shoot"] != pk["shoot"])
            if v and v["flags"]:
                what = ", ".join(v["flags"])
                if hero:
                    problems.append(f"{name} is the hero and the face check found: {what}. The hero is never a flagged face; choose another.")
                elif not anyway:
                    problems.append(f"{name}: the face check found {what}. Choose another, or start its line with \"anyway:\" and say why.")
            if v and hero and v["judged"] and "looking away" in v["notes"]:
                problems.append(f"{name} is the hero and is looking away. The hero faces the camera; choose another.")
            if hero and v is not None and not v["judged"]:
                judged_any = any(x.get("judged") for k, x in (faces.get(pk["shoot"]) or {}).items() if isinstance(x, dict))
                if judged_any:
                    problems.append(f"{name} is the hero and the face check could not judge it ({v['words']}). This shoot has faces, so the hero needs a clean one; choose another.")
            pk["checked"] = words
            if v:
                pk["seen"] = v["words"]
            if anyway and v and v["flags"]:
                pk["anyway"] = True
        if problems:
            say("STOP: this pick is refused. Fix these and pick again:")
            for pr in problems:
                say(f"   {pr}")
            return 1
    kept = [p for p in existing if p.get("shoot") not in chosen_shoots]
    if by == "photographer":
        for sid in chosen_shoots:
            before = [p["n"] for p in existing if p.get("shoot") == sid and "n" in p]
            after = [p["n"] for p in new if p["shoot"] == sid]
            if before and before != after:
                name = sheets[sid].get("name") or sid
                add_taste_note(f"{name}: chose their own sneak peeks; kept {sorted(set(before) & set(after))}, dropped {sorted(set(before) - set(after))}, added {sorted(set(after) - set(before))} (numbers on that shoot's pages; look at those frames to see what they went for)")
            mark_asked_done(night, sid)
    save_json(pj, {"picks": kept + new, "picked_by": by}, indent=1, ensure_ascii=False)
    for sid in chosen_shoots:
        say(f"{sid}: {sum(1 for p in new if p['shoot'] == sid)} sneak peeks")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("night")
    m.add_argument("--gap", type=float, default=3.0, help="seconds of quiet that end a burst")
    m.add_argument("--max", type=int, default=100, help="most moments per shoot")
    m.add_argument("--per-page", type=int, default=20)
    m.add_argument("--thumb", type=int, default=240)
    c = sub.add_parser("closer"); c.add_argument("night"); c.add_argument("picks", nargs="+", help="s1=14,3,27,9,41,18,22,5 (the shortlist)")
    k = sub.add_parser("pick"); k.add_argument("night"); k.add_argument("picks", nargs="+", help="s1=14,3,27,9,41,18 (hero first)")
    k.add_argument("--by", default="Claude, from the pages")
    k.add_argument("--checked", action="append", help='one per photo: "s1 29: eyes open to camera, mouth closed, sharp, nothing cut off"')
    k.add_argument("--checked-file", help="the same lines in a file, one per line")
    fc = sub.add_parser("faces", help="the face check on a shortlist, without drawing pages (a Mac)"); fc.add_argument("night"); fc.add_argument("picks", nargs="+")
    c2 = sub.add_parser("candidates", help="the shortlist for one shoot, as JSON (for the report's Show me more)"); c2.add_argument("night"); c2.add_argument("shoot")
    q = sub.add_parser("ask", help="the report's Pick again: remember it and keep the note as taste"); q.add_argument("night"); q.add_argument("--shoot", required=True); q.add_argument("--note", default="")
    sub.add_parser("asks", help="pick-again asks not yet done, as JSON").add_argument("night")
    d = sub.add_parser("asked-done"); d.add_argument("night"); d.add_argument("--shoot", required=True)
    t = sub.add_parser("taste", help="add a line to the taste notes, or print them"); t.add_argument("--add")
    a = ap.parse_args()
    if a.cmd == "make":
        return make(a.night, a.gap, a.max, a.per_page, a.thumb)
    if a.cmd == "closer":
        return closer(a.night, a.picks)
    if a.cmd == "candidates":
        c = candidates(a.night, a.shoot)
        say(json.dumps(c, ensure_ascii=False) if c else json.dumps({"error": "no such shoot on the pages"}))
        return 0 if c else 1
    if a.cmd == "ask":
        ask_again(a.night, a.shoot, a.note); say("Noted. Pick again when they next talk."); return 0
    if a.cmd == "asks":
        say(json.dumps(pending_asks(a.night), ensure_ascii=False)); return 0
    if a.cmd == "asked-done":
        mark_asked_done(a.night, a.shoot); return 0
    if a.cmd == "taste":
        if a.add:
            add_taste_note(a.add)
        f = taste_file()
        say(f.read_text(encoding="utf-8") if f.exists() else "(no taste notes yet)")
        return 0
    if a.cmd == "faces":
        root, studio = locate(a.night)
        sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
        for spec in a.picks:
            sid, _, nums = spec.partition("=")
            by_n = {m["n"]: m for m in sheets.get(sid, {}).get("list", [])}
            want = [by_n[int(n)] for n in nums.split(",") if n.strip().isdigit() and int(n) in by_n]
            got = check_faces(studio, sid, want)
            if not got:
                say(f"{sid}: no face check on this computer.")
            for m in want:
                v = got.get(str(m["n"]))
                if v:
                    say(f"{sid} {m['n']}: {v['words']}")
        return 0
    return pick(a.night, a.picks, a.by, a.checked, a.checked_file)


if __name__ == "__main__":
    sys.exit(main())
