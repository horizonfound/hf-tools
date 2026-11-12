#!/usr/bin/env python3
"""The face check before the sneak peeks, and the pick that demands a checked line per photo (Dustin, Nov 12:
a hero with half-closed eyes and an open mouth got through the close look).

    python3 tests/peek_check.py

A pretend backup (tests/fake_night.py, needs Pillow), pretend faces handed to the check through
PEEK_FACES_PRETEND (so no Vision is needed; on a Mac one real Vision run is tried too), then every refusal
of the pick by request. Nothing under ~/.studio is touched (STUDIO_HOME points at a scratch folder).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/the-engine/skills/studio-manager/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
import peek_sheets  # noqa: E402
import sheet  # noqa: E402
import this_computer  # noqa: E402

PASSED, FAILED = 0, []


def check(what, ok, more=""):
    global PASSED
    if ok:
        PASSED += 1
    else:
        FAILED.append(what + (f"  [{more}]" if more else ""))
        print("FAIL:", what, more)


def run(*args, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable, str(SCRIPTS / args[0]), *args[1:]], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------- judge(): the verdict in words
def judging():
    clean = {"face": 0.05, "eyes": 0.27, "mouth": 0.02, "yaw": 0.0, "pitch": 5.0, "quality": 0.6}
    v = peek_sheets.judge(clean)
    check("a clean face: eyes open, mouth closed, facing, no flags", v["judged"] and not v["flags"] and not v["notes"] and v["words"] == "eyes open · mouth closed · facing", v["words"])
    v = peek_sheets.judge(dict(clean, eyes=0.15))
    check("half-closed eyes are a flag, in capitals", v["flags"] == ["eyes half-closed, shut or down"] and "EYES HALF-CLOSED OR DOWN" in v["words"], v["words"])
    v = peek_sheets.judge(dict(clean, mouth=0.4))
    check("an open mouth is a flag", v["flags"] == ["mouth open"] and "MOUTH OPEN" in v["words"], v["words"])
    v = peek_sheets.judge(dict(clean, eyes=0.2))
    check("heavy eyes are a note, not a flag", not v["flags"] and v["notes"] == ["eyes a little heavy"], v["words"])
    v = peek_sheets.judge(dict(clean, yaw=35.0))
    check("a face turned past 30 degrees is 'looking away', still judged", not v["flags"] and "looking away" in v["notes"] and "eyes open" in v["words"], v["words"])
    v = peek_sheets.judge(dict(clean, yaw=-50.0, eyes=0.1, mouth=0.5))
    check("past 40 degrees the eyes and mouth are not judged (a profile distorts them)", not v["flags"] and v["words"].startswith("turned away") and "looking away" in v["notes"], v["words"])
    v = peek_sheets.judge(dict(clean, pitch=25.0))
    check("looking down is a note", v["notes"] == ["looking down"], v["words"])
    v = peek_sheets.judge(dict(clean, pitch=-25.0))
    check("looking up is a note", v["notes"] == ["looking up"], v["words"])
    v = peek_sheets.judge(dict(clean, face=0.001))
    check("a tiny face is not judged", not v["judged"] and v["words"] == "face too small to judge" and not v["flags"])
    v = peek_sheets.judge(None)
    check("no face: not judged, no flags", not v["judged"] and v["words"] == "no face found" and not v["flags"])
    v = peek_sheets.judge(dict(clean, eyes=None, mouth=None))
    check("landmarks missing: said, not flagged", not v["flags"] and "eyes not found" in v["words"] and "mouth not found" in v["words"], v["words"])


# ---------------------------------------------------------------- measure(): Vision's raw answer to numbers
def measuring():
    import base64
    import struct
    def b64(points):
        return base64.b64encode(b"".join(struct.pack("<dd", x, y) for x, y in points)).decode()
    # a face box 100 px square in a 500x500 picture; eyes 40 px wide and 11 px tall; inner lips 30 wide, 1 tall
    box = [0.3, 0.3, 0.2, 0.2]
    eye = [(0.1, 0.5), (0.2, 0.555), (0.4, 0.555), (0.5, 0.5), (0.4, 0.445), (0.2, 0.445)]
    lips = [(0.35, 0.2), (0.5, 0.205), (0.65, 0.2), (0.65, 0.2), (0.5, 0.195), (0.35, 0.2)]
    raw = {"size": [500, 500], "faces": [{"conf": 1.0, "box": box, "leftEye": b64(eye), "rightEye": b64(eye), "innerLips": b64(lips)}],
           "pose": [{"box": box, "yaw": 12.0, "pitch": -3.0, "roll": 0.0}], "quality": [{"box": box, "quality": 0.7}]}
    m = peek_sheets.measure(raw)
    check("measure: the face's share, eye and mouth ratios in pixels, pose and quality", m and m["face"] == 0.04 and abs(m["eyes"] - 0.275) < 0.01 and abs(m["mouth"] - 0.033) < 0.01 and m["yaw"] == 12.0 and m["pitch"] == -3.0 and m["quality"] == 0.7, str(m))
    tall = dict(raw, size=[250, 1000])
    m2 = peek_sheets.measure(tall)
    # the same box in a 250x1000 picture is 50 px wide and 200 tall: the eye is 20 px wide and 22 tall
    check("measure works in pixels, so a picture's shape is taken into account", m2 and abs(m2["eyes"] - 1.1) < 0.02, str(m2))
    small = {"size": [500, 500], "faces": [{"conf": 1.0, "box": box, "leftEye": None, "rightEye": None, "innerLips": None}], "pose": [], "quality": []}
    m3 = peek_sheets.measure(small)
    check("no landmarks: eyes and mouth None, the face still measured", m3 and m3["eyes"] is None and m3["mouth"] is None and m3["face"] == 0.04, str(m3))
    two = dict(raw, faces=[dict(raw["faces"][0], box=[0.0, 0.0, 0.05, 0.05], conf=1.0), raw["faces"][0]])
    check("the biggest face is the one judged", peek_sheets.measure(two)["face"] == 0.04)
    unsure = dict(raw, faces=[dict(raw["faces"][0], conf=0.2)])
    check("a face Vision is not sure of does not count", peek_sheets.measure(unsure) is None)
    check("no faces at all: None", peek_sheets.measure({"size": [500, 500], "faces": [], "pose": [], "quality": []}) is None)


# ---------------------------------------------------------------- the pages and the pick, on a pretend backup
def picking(work):
    import fake_night
    night = work / "night"
    fake_night.main(str(night))
    studio = night / "_studio"
    sheets = json.loads((studio / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    check("the pretend backup has two shoots on the pages", set(sheets) == {"s1", "s2"})
    clean = {"face": 0.05, "eyes": 0.27, "mouth": 0.02, "yaw": 0.0, "pitch": 5.0, "quality": 0.6}
    pretend = {"s1/001.jpg": clean, "s1/002.jpg": dict(clean, eyes=0.15), "s1/003.jpg": dict(clean, mouth=0.4),
               "s1/004.jpg": dict(clean, yaw=50.0), "s1/005.jpg": dict(clean, eyes=0.2, yaw=35.0), "s1/006.jpg": dict(clean, face=0.001),
               "s1/007.jpg": None, "s1/008.jpg": clean, "s1/009.jpg": clean, "s1/010.jpg": clean, "s1/011.jpg": clean, "s1/012.jpg": clean}
    for n in range(1, 11):
        pretend[f"s2/{n:03d}.jpg"] = None   # a landscape shoot: nobody in it
    pf = work / "pretend-faces.json"
    pf.write_text(json.dumps(pretend), encoding="utf-8")
    env = {"PEEK_FACES_PRETEND": str(pf), "STUDIO_HOME": str(work / "studio-home")}

    code, out = run("peek_sheets.py", "closer", str(night), "s1=1,2,3,4,5,6,7,8,9,10,11,12", "s2=1,2,3,4,5,6,7,8,9,10", env=env)
    check("closer runs with the face check", code == 0, out[-400:])
    faces = json.loads((studio / "peek-faces.json").read_text(encoding="utf-8"))
    check("the verdicts are in peek-faces.json, by shoot and number", faces["s1"]["1"]["words"] == "eyes open · mouth closed · facing" and faces["s1"]["2"]["flags"] == ["eyes half-closed, shut or down"]
          and faces["s1"]["7"]["words"] == "no face found" and faces["s2"]["3"]["words"] == "no face found", json.dumps(faces["s1"]["1"]))
    check("closer prints the verdicts, a fault in capitals", "2: EYES HALF-CLOSED OR DOWN" in out and "3: " in out and "MOUTH OPEN" in out and "1: eyes open · mouth closed · facing" in out, out[-600:])
    check("the close-look pages are written", (studio / "peek-sheets" / "s1-close1.png").is_file() and (studio / "peek-sheets" / "s2-close3.png").is_file())
    # the label on the page: the number's row holds coloured pixels past the number, where the words go
    import struct as st
    import zlib
    png = (studio / "peek-sheets" / "s1-close1.png").read_bytes()
    w, h = st.unpack(">II", png[16:24])
    idat = b"".join(png[i + 8:i + 8 + st.unpack(">I", png[i:i + 4])[0]] for i in [png.find(b"IDAT") - 4])
    raw = zlib.decompress(idat)
    def row_px(y):
        r = raw[y * (w * 3 + 1) + 1:][: w * 3]
        return [r[i:i + 3] for i in range(0, len(r), 3)]
    # the first label bar starts at y=10 and its words at y=17, seven glyph rows two pixels tall each: row 24 is mid-word
    check("the first label carries green words (a clean face) past the number", any(p == bytes((150, 200, 150)) for p in row_px(24)[60:400]), "")
    # the second row of photos (3 and 4) has its bar at y = 10 + 700 + 28 + 10 = 748; photo 3 is flagged: MOUTH OPEN in red
    check("a flagged photo's label is red", any(p == bytes((235, 90, 80)) for p in row_px(748 + 14)[60:400]), "")

    # the pick: every refusal by request
    pj = studio / "sneak-peeks.json"
    before = pj.read_text(encoding="utf-8")
    L = lambda sid, n, words="eyes open, mouth closed, sharp": f"--checked={sid} {n}: {words}"
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,8,9,10,11,12", env=env)
    check("no checked lines: refused, naming every photo", code == 1 and out.count("no checked line") == 6, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,8,9,10,11,12", *[L("s1", n) for n in (1, 8, 9, 10, 11)], env=env)
    check("one line missing: refused, naming that photo only", code == 1 and out.count("no checked line") == 1 and "s1 12: no checked line" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,8,9,10,11,12", *[L("s1", n) for n in (1, 8, 9, 10, 11)], L("s1", 12, "eyes open, sharp"), env=env)
    check("a line that says nothing of the mouth: refused", code == 1 and "must say what you saw of the eyes and the mouth" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=2,8,9,10,11,12", *[L("s1", n) for n in (2, 8, 9, 10, 11, 12)], env=env)
    check("a flagged hero: refused, whatever the line says", code == 1 and "s1 2 is the hero" in out and "never a flagged face" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=2,8,9,10,11,12", L("s1", 2, "anyway: eyes shut on purpose, mouth closed, laughing"), *[L("s1", n) for n in (8, 9, 10, 11, 12)], env=env)
    check("'anyway' never rescues the hero", code == 1 and "s1 2 is the hero" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=4,8,9,10,11,12", *[L("s1", n) for n in (4, 8, 9, 10, 11, 12)], env=env)
    check("a hero turned away: refused", code == 1 and "s1 4 is the hero and is looking away" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=6,8,9,10,11,12", *[L("s1", n) for n in (6, 8, 9, 10, 11, 12)], env=env)
    check("a hero too small to judge, in a shoot with faces: refused", code == 1 and "s1 6 is the hero" in out and "could not judge" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=7,8,9,10,11,12", *[L("s1", n) for n in (7, 8, 9, 10, 11, 12)], env=env)
    check("a hero with no face, in a shoot with faces: refused", code == 1 and "s1 7 is the hero" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,3,9,10,11,12", *[L("s1", n) for n in (1, 3, 9, 10, 11, 12)], env=env)
    check("a flagged photo that is not the hero: refused, with the way to say anyway", code == 1 and "s1 3: the face check found mouth open" in out and "anyway:" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,13,9,10,11,12", *[L("s1", n) for n in (1, 13, 9, 10, 11, 12)], env=env)
    check("a photo that was never on the close-look pages: refused (on a Mac)", (code == 1 and "s1 13: not on the close-look pages" in out) if this_computer.MAC else code == 0, out[-300:])
    check("a refused pick writes nothing", pj.read_text(encoding="utf-8") == before)
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,3,9,10,11,12", "s2=1,2,3,4,5,6", *[L("s1", n) for n in (1, 9, 10, 11, 12)], L("s1", 3, "anyway: a laugh, mouth open on purpose, eyes open"),
                    *[L("s2", n, "no face: a landscape, no eyes or mouth to see, sharp") for n in (1, 2, 3, 4, 5, 6)], env=env)
    check("a clean hero, a flagged photo said anyway, and a landscape shoot with no faces: accepted", code == 0 and "s1: 6 sneak peeks" in out and "s2: 6 sneak peeks" in out, out[-300:])
    picks = json.loads(pj.read_text(encoding="utf-8"))
    s1 = [p for p in picks["picks"] if p["shoot"] == "s1"]
    check("the records carry each photo's checked line and what the check saw", s1[0]["checked"].startswith("eyes open") and s1[0]["seen"] == "eyes open · mouth closed · facing" and s1[1].get("anyway") is True and "MOUTH OPEN" in s1[1]["seen"], json.dumps(s1[:2]))
    code, out = run("peek_sheets.py", "pick", str(night), "s1=8,9,10,11,12,1", "--checked=1: eyes open, mouth closed", env=env)
    check("with one shoot in the pick, a bare number is enough on a line", code == 1 and "s1 8: no checked line" in out and "s1 1: no checked line" not in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=8,9,10,11,12,1", "s2=1,2,3,4,5,6", "--checked=1: eyes open, mouth closed", env=env)
    check("with two shoots, a bare number is refused", code == 1 and "needs the shoot too" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=8,9,10,11,12,1", "--checked=s1-8: eyes open, mouth closed", *[L("s1", n) for n in (9, 10, 11, 12, 1)], env=env)
    check("'s1-8:' is read the same as 's1 8:'", code == 0, out[-300:])
    cf = work / "checked.txt"
    cf.write_text("# the beach\ns1 1: eyes open, mouth closed, sharp\n\ns1 8: eyes open, mouth closed\ns1 9: eyes open, mouth closed\ns1 10: eyes open, mouth closed\ns1 11: eyes open, mouth closed\ns1 12: eyes open, mouth closed\n", encoding="utf-8")
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,8,9,10,11,12", "--checked-file", str(cf), env=env)
    check("the lines can come from a file (comments and blank lines skipped)", code == 0, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=2,3,4,5,6,7", "--by", "photographer", env=env)
    check("the photographer's own choice needs no lines and may hold anything", code == 0, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,8,9,10,11,12", "--checked=s1 1 eyes open mouth closed", env=env)
    check("a line without a colon is refused with the shape to use", code == 1 and "needs a photo number, a colon" in out, out[-300:])
    code, out = run("peek_sheets.py", "faces", str(night), "s1=1,2,7", env=env)
    check("the faces command prints the verdicts without drawing pages", code == 0 and "s1 1: eyes open" in out and "s1 2: EYES" in out and "s1 7: no face found" in out, out[-300:])

    # closer again on a shorter shortlist keeps the earlier verdicts for the shoot
    code, out = run("peek_sheets.py", "closer", str(night), "s1=1,2", env=env)
    faces = json.loads((studio / "peek-faces.json").read_text(encoding="utf-8"))
    check("a second closer keeps the shoot's earlier verdicts beside the new", code == 0 and "12" in faces["s1"] and "1" in faces["s1"])

    # no face check at all (a PC, or Vision failing): the lines are still demanded, nothing is flagged
    (studio / "peek-faces.json").unlink()
    env2 = {"PEEK_FACES_PRETEND": str(work / "nowhere.json"), "STUDIO_HOME": str(work / "studio-home")}
    code, out = run("peek_sheets.py", "closer", str(night), "s1=1,2,3", env=env2)
    check("closer with no face check says so and still draws the pages", code == 0 and "no face check on this computer" in out, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,2,3,8,9,10", *[L("s1", n) for n in (1, 2, 3, 8, 9, 10)], env=env2)
    if this_computer.MAC:
        check("on a Mac, a pick with no face check for the shoot is refused: the close look was skipped", code == 1 and "close look was skipped" in out, out[-300:])
    else:
        check("off a Mac, the lines are all that is asked", code == 0, out[-300:])
    code, out = run("peek_sheets.py", "pick", str(night), "s1=1,2,3,8,9,10", env=env2)
    check("... and no lines is still refused", code == 1 and "no checked line" in out, out[-300:])


# ---------------------------------------------------------------- the real Vision, on this Mac only
def real_vision(work):
    if not this_computer.MAC:
        return
    night = work / "night"
    studio = night / "_studio"
    peeks = sorted((studio / "peeks" / "s1").glob("*.jpg"))[:3]
    raw = peek_sheets.look_at_faces(peeks)
    check("the Mac's Vision answers for the pretend photos (no faces in them)", isinstance(raw, list) and len(raw) == 3 and all(r.get("size") for r in raw), str(raw)[:200])
    check("... and finds no face in a white ellipse", all(peek_sheets.measure(r) is None for r in raw))


# ---------------------------------------------------------------- the font
def lettering():
    cv = sheet.Canvas(400, 20)
    cv.text(2, 2, "Eyes open · mouth closed", scale=2, color=(1, 2, 3))
    lit = sum(1 for r in cv.rows for i in range(0, len(r), 3) if r[i:i + 3] == bytes((1, 2, 3)))
    check("the page's font draws letters and the dot", lit > 200, str(lit))
    cv2 = sheet.Canvas(400, 20)
    cv2.text(2, 2, "eyes", scale=2, color=(1, 2, 3))
    cv3 = sheet.Canvas(400, 20)
    cv3.text(2, 2, "EYES", scale=2, color=(1, 2, 3))
    check("lowercase is drawn as capitals", cv2.rows == cv3.rows)
    check("every letter is 5 by 7", all(len(g) == 7 and all(len(r) == 5 for r in g) for g in sheet.LETTERS.values()))


def main():
    judging()
    measuring()
    lettering()
    with tempfile.TemporaryDirectory(prefix="peek-check-") as d:
        work = Path(d)
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("(no Pillow here: the pretend backup cannot be made, the pick checks are skipped)")
        else:
            picking(work)
            real_vision(work)
    print(f"{PASSED} passed, {len(FAILED)} failed")
    if FAILED:
        for f in FAILED:
            print("  ", f)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
