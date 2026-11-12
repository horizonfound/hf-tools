#!/usr/bin/env python3
"""Video clips on a memory card (Dustin, Nov 11). Photographers shoot behind-the-scenes clips beside their
photos, and some cards hold nothing but video. One place for what the backup needs to know about a clip:

  - which files are clips (by the file's ending, so an older backup's records read the same way)
  - how to say a count in plain words: "212 photos and 6 video clips", "17 video clips", "1 photo"
  - the two folder names a shoot with both gets: Photos and Videos
  - one still picture of a clip, for the report and the contact sheet (a Mac only for now: the reel's video
    helper has no stills on a PC, so there a clip simply shows no picture)

Nothing here changes a clip; a still is a new small JPEG in the backup's own records.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
VIDEO = {".mov", ".mp4", ".m4v", ".mxf", ".avi"}
PHOTOS_FOLDER, VIDEOS_FOLDER = "Photos", "Videos"   # inside a shoot that holds both (Dustin, Nov 11)


def is_clip(file):
    """True for a video file. Takes a path, or a record from the index."""
    if isinstance(file, dict):
        file = file.get("original") or file.get("file") or ""
    return Path(str(file)).suffix.lower() in VIDEO


def count(files):
    """(photos, clips) among these files or index records."""
    files = list(files)
    c = sum(1 for f in files if is_clip(f))
    return len(files) - c, c


def words(photos, clips):
    """A count the way a photographer would say it. Never calls a clip a photo."""
    p = f"{photos:,} photo{'' if photos == 1 else 's'}"
    c = f"{clips:,} video clip{'' if clips == 1 else 's'}"   # "video clips", not "clips" alone (Dustin, Nov 11)
    if photos and clips:
        return f"{p} and {c}"
    return c if clips else p


def words_for(files):
    return words(*count(files))


def recorded(path):
    """(when, how) for a clip whose date the quick reader could not find: when it was recorded as local time
    ("2026-11-07T07:01:11"), and where that came from: "the clip's header" (read wherever it sits in the file) or
    "the file's own time" (what the camera set on the file, kept by the backup). (None, None) when neither is there."""
    from datetime import datetime
    try:
        video = _video()
        t = video.recorded_local(video.facts(path))
        if t and t.year >= 1990:
            return t.isoformat(timespec="seconds"), "the clip's header"
    except Exception:  # noqa: BLE001
        pass
    try:
        t = datetime.fromtimestamp(Path(path).stat().st_mtime)
        if t.year >= 1990:
            return t.isoformat(timespec="seconds"), "the file's own time"
    except (OSError, OverflowError, ValueError):
        pass
    return None, None


def _video():
    """The reel's video helper (assistant-make-a-reel/scripts/video.py), without leaving its folder at the front
    of Python's search list."""
    d = str(HERE.parent.parent / "assistant-make-a-reel" / "scripts")
    saved = list(sys.path)
    if d not in sys.path:
        sys.path.append(d)
    try:
        import video
        return video
    finally:
        sys.path[:] = saved + [x for x in sys.path if x not in saved]


# Which way up a still is (Dustin, Nov 11: "they need to be upright for sure"). A camera turned on its side to film
# a vertical clip often does not record the turn, so the picture comes out lying down. The Mac's own Vision finds
# the people in the still: how far the biggest face is tipped, or, with no face, which way the line from hips to
# neck runs. Only the STILL is ever turned (the Assistant's own small picture); the clip is never changed.
UPRIGHT_JS = r"""
ObjC.import('Vision'); ObjC.import('Foundation');
// argv: how the pictures are to be read (1 as they are, 6 turned a quarter clockwise, 3 half, 8 three quarters),
// then the pictures. For each: its faces [tip in degrees, how sure, how big, how good a picture of the face it is
// (0 to 1: Apple's own face capture quality; eyes shut, looking down or hair across the face score low)], and its
// bodies [neck minus hips, across and up].
function run(argv) {
  var o = parseInt(argv[0]), all = [];
  for (var a = 1; a < argv.length; a++) {
    var out = {faces: [], bodies: []};
    try {
      var url = $.NSURL.fileURLWithPath(argv[a]);
      var h = $.VNImageRequestHandler.alloc.initWithURLOrientationOptions(url, o, $());
      var face = $.VNDetectFaceCaptureQualityRequest.alloc.init;
      var pose = $.VNDetectHumanBodyPoseRequest.alloc.init;
      h.performRequestsError($([face, pose]), Ref());
      var i, r = face.results;
      if (r && !r.isNil()) for (i = 0; i < r.count; i++) {
        var f = r.objectAtIndex(i);
        if (f.roll && !f.roll.isNil()) out.faces.push([f.roll.doubleValue * 57.2958, f.confidence, f.boundingBox.size.width * f.boundingBox.size.height,
          (f.faceCaptureQuality && !f.faceCaptureQuality.isNil()) ? f.faceCaptureQuality.doubleValue : 0]);
      }
      r = pose.results;
      if (r && !r.isNil()) for (i = 0; i < r.count; i++) {
        var p = r.objectAtIndex(i), e = Ref();
        var n = p.recognizedPointForJointNameError('neck_1_joint', e), ro = p.recognizedPointForJointNameError('root', e);
        if (n && !n.isNil() && ro && !ro.isNil() && n.confidence > 0.3 && ro.confidence > 0.3)
          out.bodies.push([n.location.x - ro.location.x, n.location.y - ro.location.y]);
      }
    } catch (err) {}
    all.push(out);
  }
  return JSON.stringify(all);
}
"""
READ_AS = {0: 1, 90: 6, 180: 3, 270: 8}   # a picture that must turn this far clockwise is read by Vision this way


def see(pictures, turn=0):
    """What Vision finds in each picture (read as if already turned `turn` degrees clockwise): a list, one
    {"faces": [[tip, how sure, how big, how good]], "bodies": [[across, up]]} per picture. [] on a PC or when
    anything goes wrong."""
    try:
        r = this_computer.mac_javascript(UPRIGHT_JS, [READ_AS.get(turn, 1), *[str(q) for q in pictures]], timeout=60)
        if not r or r[0] != 0:
            return []
        return json.loads(r[1])
    except Exception:  # noqa: BLE001
        return []


def face_score(seen):
    """How good a picture of a person this is, 0 to 1: Apple's own score for the biggest face that is surely a
    face. 0 with no face (a back to the camera, hair across the face, an empty chair)."""
    faces = [f for f in seen.get("faces", []) if f[1] >= 0.5]
    if not faces:
        return 0.0
    big = max(faces, key=lambda f: f[2])
    return float(big[3]) if len(big) > 3 else 0.0


def is_sure(seen):
    return bool([f for f in seen.get("faces", []) if f[1] >= 0.5] or seen.get("bodies"))


def best_moment(scores):
    """Which of a clip's moments makes the best picture: the highest face score; with nothing to choose between
    them (nobody in any), the middle one. `scores` is one number per moment, in clip order. Returns its place."""
    if not scores:
        return 0
    mid = (len(scores) - 1) / 2
    top = max(scores)
    if top <= 0:
        return len(scores) // 2
    return min((i for i, x in enumerate(scores) if x >= top - 0.02), key=lambda i: abs(i - mid))


def turn_for(seen):
    """How far clockwise (0, 90, 180 or 270 degrees) a picture must turn to stand upright, from what Vision saw in
    it: {"faces": [[tip in degrees, how sure, how big]], "bodies": [[neck minus hips, across and up]]}. 0 whenever
    it cannot tell (nobody in the picture, or a head tipped part way): a picture is never turned on a guess."""
    faces = [f for f in seen.get("faces", []) if f[1] >= 0.5]
    if faces:
        tip = max(faces, key=lambda f: f[2])[0]
        if 60 <= tip <= 120:
            return 90
        if -120 <= tip <= -60:
            return 270
        if abs(tip) >= 150:
            return 180
        return 0
    for dx, dy in seen.get("bodies", [])[:1]:
        if abs(dx) > 2 * abs(dy) and abs(dx) > 0.1:      # the body lies across the picture
            return 90 if dx < 0 else 270
        if dy < 0 and abs(dy) > 2 * abs(dx) and abs(dy) > 0.1:
            return 180
    return 0


def look(picture):
    """(turn, sure) for one picture: how far clockwise it must turn to stand upright, and whether a person was
    found to judge by. (0, False) on a PC, with nobody in the picture, or when anything goes wrong."""
    seen = see([picture])
    if not seen:
        return 0, False
    return turn_for(seen[0]), is_sure(seen[0])


def rotate(picture, turn):
    """Turn one of the Assistant's own stills clockwise by 90, 180 or 270 degrees. True when it was turned."""
    if not turn or not this_computer.MAC:
        return False
    try:
        done = subprocess.run(["sips", "-r", str(turn), str(picture)], capture_output=True, timeout=30)  # pc-ok: a Mac only
        return done.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def turns_file(folder):
    return Path(folder) / "clip-turns.json"


def turns(folder):
    """{still's name: {"turn": 0|90|180|270, "sure": a person was found, "from": how it was decided}} for the clip
    stills in this folder. What has been done to each still, so nothing is ever turned twice."""
    try:
        return json.loads(turns_file(folder).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def note_turn(folder, name, turn, sure, how, **more):
    d = turns(folder)
    d[name] = dict(d.get(name, {}), turn=turn, sure=sure, **{"from": how}, **more)
    tmp = turns_file(folder).with_name(turns_file(folder).name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
    this_computer.replace(tmp, turns_file(folder))


def borrow_turns(folder, names):
    """Stills with nobody in them (an empty chair, a back to the camera) take the turn of the nearest clip in
    shooting order where a person was found: the camera was most likely still held the same way. `names` are the
    stills of one group, in shooting order. A still is only ever turned once (clip-turns.json remembers)."""
    d = turns(folder)
    sure = [i for i, n in enumerate(names) if d.get(n, {}).get("sure")]
    for i, n in enumerate(names):
        rec = d.get(n)
        if not rec or rec.get("sure") or rec.get("from") == "the clip beside it" or not sure:
            continue
        near = names[min(sure, key=lambda j: abs(j - i))]
        turn = d[near]["turn"]
        if turn and not rotate(Path(folder) / n, turn):
            continue
        note_turn(folder, n, turn, False, "the clip beside it")


MOMENTS = (0.12, 0.22, 0.32, 0.42, 0.5, 0.58, 0.68, 0.78, 0.88)   # where in a clip a preview may come from


def _grab(video, src, f, times, scratch, name, edge):
    """Stills of the clip at these times, in a scratch folder of its own: ([a picture or None per time], folder)."""
    r = video.stills(src, list(times), scratch, name=name, edge=edge, f=f, wait=120)
    got = (r.get("stills") or []) if r.get("ok") else []
    out = []
    for x in got:
        q = Path(x["file"]) if x.get("file") else None
        if q is not None and not q.is_absolute():
            q = Path(r["folder"]) / q
        out.append(q if q is not None and q.is_file() else None)
    out += [None] * (len(times) - len(out))
    return out, r.get("folder")


def still(src, dst, edge=1000):
    """One still of a clip for the report and the contact sheet, saved as dst (a JPEG): a good moment, standing
    upright. True when it was made. The clip is only read and never changed. Never writes over a file: a dst that
    is there is left and counts as made. False on a PC, for a video the Mac cannot read, or when anything at all
    goes wrong (a picture is a nicety, never a stop).

    A good moment (Dustin, Nov 11: the middle of one clip was someone looking down behind a cup, "not flattering
    at all"): nine moments across the clip are looked at small, and the one where the face makes the best picture
    is kept (Apple's own face score: eyes shut, looking down or a hidden face score low). Nobody in any of them:
    the middle.
    Upright (Dustin, Nov 11): a camera held on its side often does not record the turn. The still is turned by the
    people found in any of those moments; failing that, borrow_turns() goes by the clip beside it."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        return True
    try:
        video = _video()
        f = video.facts(src)
        length = f.get("length") or 0
        scratch = dst.parent / ".stills"
        name = dst.stem[:40] or "clip"
        times = [length * m for m in MOMENTS] if length >= 3 else [length / 2]
        small, sfolder = _grab(video, src, f, times, scratch, name + " moments", 480)
        have = [(t, q) for t, q in zip(times, small) if q]
        turn, sure, how, score, at = 0, False, "nobody to go by", 0.0, (times[len(times) // 2])
        if have:
            seen = see([q for _, q in have])
            if len(seen) == len(have):
                # which way up: the biggest sure face among the moments decides, else the first body found
                faces = [(max((x for x in sn["faces"] if x[1] >= 0.5), key=lambda x: x[2])[2], turn_for(sn)) for sn in seen
                         if [x for x in sn["faces"] if x[1] >= 0.5]]
                bodies = [turn_for(sn) for sn in seen if not sn["faces"] and sn["bodies"]]
                if faces:
                    turn, sure, how = max(faces)[1], True, "the people in it"
                elif bodies:
                    turn, sure, how = bodies[0], True, "the people in it"
                if turn:                      # judge the faces the right way up
                    again = see([q for _, q in have], turn)
                    seen = again if len(again) == len(have) else seen
                scores = [face_score(sn) for sn in seen]
                i = best_moment(scores)
                at, score = have[i][0], scores[i]
        if sfolder:
            shutil.rmtree(sfolder, ignore_errors=True)
        made, folder = _grab(video, src, f, [at], scratch, name, edge)
        made = made[0]
        if not made:
            if folder:
                shutil.rmtree(folder, ignore_errors=True)
            return False
        if turn:
            rotate(made, turn)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(folder, ignore_errors=True)
            return True
        made.replace(dst)
        note_turn(dst.parent, dst.name, turn, sure, how, at=round(at, 2), face=round(score, 2))
        shutil.rmtree(folder, ignore_errors=True)   # our own scratch folder, made a moment ago
        try:
            scratch.rmdir()
        except OSError:
            pass
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- the clip pages: what happens in each clip
# (Dustin, Nov 11: "look at a frame in the beginning, the middle, and the end, and try to figure out what's going
# on, and then use that information to name what the clip is.") Three frames from each clip, upright, a dozen clips
# to a page, so Claude sees what happens across every clip in one look per page (rule 6: the script does the heavy
# part). Only for groups made of nothing but clips: clips shot with photos take the photo shoot's name.
SHEET_CLIPS_MOST = 96     # clips looked at on one card (8 pages); a group's clips are thinned evenly beyond that
SHEET_PER_PAGE = 12
SHEET_CELL = 240


def _three(video, src, into, name):
    """Three stills of one clip: near the start, the middle, near the end. ([pictures], their folder, its length)."""
    f = video.facts(src)
    length = f.get("length") or 0
    times = [min(1.0, length * 0.1), length / 2, max(0.0, length - max(0.5, min(1.5, length * 0.1)))]
    r = video.stills(src, times, into, name=name, edge=480, f=f, wait=120)
    out = []
    for x in (r.get("stills") or []) if r.get("ok") else []:
        if x.get("file"):
            q = Path(x["file"])
            out.append(q if q.is_absolute() else Path(r["folder"]) / q)
    return out, r.get("folder"), length


def sheets(night):
    """Make the clip pages for a backup: <records>/clip-sheets/clips-p1.png ... and clip-sheets.json (which
    numbered row is which clip). 0 done, 2 nothing to make (no group of only clips, or a PC), 1 a problem."""
    from where import locate
    import sheet
    root, records = locate(night)
    groups = json.loads((records / "groups.json").read_text(encoding="utf-8"))["groups"]
    only = [g for g in groups if g.get("files") and all(is_clip(f) for f in g["files"])]
    if not only or not this_computer.MAC:
        return 2
    try:
        video = _video()
    except Exception:  # noqa: BLE001
        return 1
    out_dir = records / "clip-sheets"
    out_dir.mkdir(exist_ok=True)
    per_group = max(2, SHEET_CLIPS_MOST // len(only))
    rows = []
    for g in only:
        files = g["files"]
        if len(files) > per_group:
            step = (len(files) - 1) / (per_group - 1)
            files = [files[round(i * step)] for i in range(per_group)]
        mine = []
        for f in files:
            n = len(rows) + len(mine) + 1
            try:
                pics, folder, length = _three(video, root / f, out_dir, f"{n:03d}")
            except Exception:  # noqa: BLE001
                pics, folder, length = [], None, 0
            turn, sure = 0, False
            for q in (pics[1:2] + pics[:1] + pics[2:]):     # the middle first, then the start, then the end
                turn, sure = look(q)
                if sure:
                    break
            mine.append({"n": n, "file": f, "group": g["id"], "seconds": round(length), "frames": [str(q) for q in pics],
                         "turn": turn if sure else 0, "sure": sure})
        known = [i for i, m in enumerate(mine) if m["sure"]]       # nobody in a clip: stand the way its neighbour does
        for i, m in enumerate(mine):
            if not m["sure"] and known:
                m["turn"] = mine[min(known, key=lambda j: abs(j - i))]["turn"]
            for q in m["frames"]:
                rotate(q, m["turn"])
        rows += mine
    cell, pad, label = SHEET_CELL, 6, 56
    block = label + 3 * (cell + pad)
    tmp = out_dir / ".tmp.bmp"
    pages = []
    for start in range(0, len(rows), SHEET_PER_PAGE):
        chunk = rows[start:start + SHEET_PER_PAGE]
        lines = (len(chunk) + 1) // 2
        W, H = 2 * block + 3 * pad, lines * (cell + pad) + pad
        cv = sheet.Canvas(W, H)
        for j, m in enumerate(chunk):
            x0, y0 = pad + (j % 2) * (block + pad), pad + (j // 2) * (cell + pad)
            cv.rect(x0, y0, label - pad, cell, (40, 40, 40))
            cv.text(x0 + 4, y0 + 10, f"{m['n']:02d}", scale=3, color=(240, 127, 90))
            for k, q in enumerate(m["frames"][:3]):
                t = sheet.thumb(Path(q), cell, tmp)
                if not t:
                    continue
                w, h, rws = t
                x = x0 + label + k * (cell + pad)
                cv.paste(x + max(0, (cell - w) // 2), y0 + max(0, (cell - h) // 2), w, min(h, cell), rws[:cell])
        page = out_dir / f"clips-p{start // SHEET_PER_PAGE + 1}.png"
        sheet.write_png(page, W, H, cv.rows)
        pages.append(str(page))
    if tmp.exists():
        tmp.unlink()
    for m in rows:
        m["frames"] = [Path(q).relative_to(records).as_posix() for q in m["frames"]]
    listed = {"made": len(rows), "of": sum(len(g["files"]) for g in only), "pages": pages, "clips": rows}
    tmpj = out_dir.parent / "clip-sheets.json.tmp"
    tmpj.write_text(json.dumps(listed, indent=1), encoding="utf-8")
    this_computer.replace(tmpj, records / "clip-sheets.json")
    return 0


def sheet_words(records):
    """The lines the backup prints at the look: which page shows which clips, group by group. [] when no pages."""
    try:
        d = json.loads((Path(records) / "clip-sheets.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not d.get("clips"):
        return []
    out = ["   VIDEO CLIPS: also read " + ("this page" if len(d["pages"]) == 1 else "these pages") + ". Each numbered row is one clip, three frames across it:",
           "   near its start, its middle, near its end."]
    out += [f"      {pg}" for pg in d["pages"]]
    by = {}
    for m in d["clips"]:
        by.setdefault(m["group"], []).append(m)
    for gid, ms in by.items():
        out.append(f"      {gid}: rows {ms[0]['n']:02d} to {ms[-1]['n']:02d}  (" + ", ".join(f"{m['seconds']} s" for m in ms) + ")")
    if d["made"] < d["of"]:
        out.append(f"      ({d['made']} of the card's {d['of']} clips are shown, spread evenly.)")
    out += ["   From the three frames, work out what is going on in each clip (someone talking direct to camera (a talking head), a walk-through,",
            "   setting up, a detail, behind the scenes) and name each shoot of clips for that and the place: \"Garden interview\",",
            "   \"Studio, direct to camera\", \"Venue walk-through\". The recap says what happens in them, in a sentence or two.",
            "   A person talking to the lens is \"direct to camera\" or a \"talking head\", never \"talking takes\".",
            "   A clip that watches someone at work from the outside (photographing a family, setting up) is \"behind the scenes\" or \"B-roll\".",
            "   Say only what the frames show: never a person's name, and never what a clip is about beyond what is on screen."]
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "upright":
        # A backup whose clip stills were made before stills stood upright: each is made again from its clip (the
        # earlier still is set aside in groups/older/, never deleted). Only groups made of nothing but clips.
        from where import locate
        root, records = locate(sys.argv[2])
        for g in json.loads((records / "groups.json").read_text(encoding="utf-8"))["groups"]:
            if not g.get("files") or not all(is_clip(f) for f in g["files"]):
                continue
            done = []
            for f in g["files"]:
                cam = Path(f).stem.split("_", 2)[-1] if Path(f).stem.count("_") >= 2 else Path(f).stem
                pic = records / "groups" / f"{g['id']}_{cam}.jpg"
                if not pic.exists():
                    continue
                if "face" not in turns(pic.parent).get(pic.name, {}) and (root / f).is_file():
                    (pic.parent / "older").mkdir(exist_ok=True)
                    aside = pic.parent / "older" / pic.name
                    k = 2
                    while aside.exists():
                        aside = pic.parent / "older" / f"{pic.stem} ({k}).jpg"
                        k += 1
                    pic.rename(aside)
                    if not still(root / f, pic):
                        aside.rename(pic)   # could not make a new one: the earlier still goes back
                done.append(pic.name)
            borrow_turns(records / "groups", done)
            for n in done:
                t = turns(records / "groups").get(n, {})
                print(f"{n}: " + (f"turned {t['turn']} degrees" if t.get("turn") else "not turned") + f" ({t.get('from', 'not looked at')}); "
                      f"taken {t.get('at', '?')} s in, face score {t.get('face', '?')}")
    elif len(sys.argv) == 3 and sys.argv[1] == "sheets":
        code = sheets(sys.argv[2])
        if code == 0:
            from where import locate
            print("\n".join(sheet_words(locate(sys.argv[2])[1])))
        elif code == 2:
            print("No pages to make: no group of only clips, or no stills on this computer yet.")
        sys.exit(code)
    elif len(sys.argv) == 3:
        print("made" if still(sys.argv[1], sys.argv[2]) else "no still")
    else:
        sys.exit("usage: clips.py <video> <still.jpg>   |   clips.py upright <a backup's records>   |   clips.py sheets <a backup>")
