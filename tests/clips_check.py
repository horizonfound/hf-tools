#!/usr/bin/env python3
"""Video clips on a memory card (Dustin, Nov 11): a pretend card with photos and clips together, and a second
with clips only, each run through the whole backup the way night.py runs it for a photographer.

What must hold:
  - a shoot with photos and clips gets a Photos and a Videos folder inside its own, each numbered from 0001;
    a shoot of only photos, or only clips, stays one flat folder
  - every file is byte for byte what the card holds, and the card is untouched
  - nothing calls a clip a photo: the report says "N photos and M clips"
  - sneak peeks are photos only; a card of nothing but clips is never asked for picks (no exit 7)
  - a rename carries both folders along, there and back, a second run changes nothing, and a rename cut off
    part way is finished by the next run
  - the backup settles with both folders in place

    python3 tests/clips_check.py            (pretend files in a scratch folder; never the real ~/.studio)
"""
import hashlib
import re
import json
import shutil
import struct
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402  (its pretend card, its runner, its check lines)

SCRIPTS = t.SCRIPTS
CLIP = HERE / "fixtures" / "loud-tone-3s.mp4"
FAILED = []


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {detail}"), flush=True)
    if not ok:
        FAILED.append(what)


def clip_at(dst, when):
    """A copy of the tiny test clip whose own header says it was recorded at `when` (this computer's clock), and
    whose bytes differ from every other copy (so no two clips share a hash)."""
    data = bytearray(CLIP.read_bytes())
    at = data.find(b"mvhd")
    assert at > 0 and data[at + 4] == 0, "the test clip's header is not the kind this test rewrites"
    secs = int((when.astimezone(timezone.utc) - datetime(1904, 1, 1, tzinfo=timezone.utc)).total_seconds())
    struct.pack_into(">II", data, at + 8, secs, secs)
    dst.write_bytes(bytes(data) + b"\0" * (1 + int(when.timestamp()) % 97))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def card_hashes(card):
    return {p.name: sha(p) for p in (card / "DCIM" / "100CANON").iterdir() if p.is_file() and not p.name.startswith(".")}


def listing(folder):
    return sorted(p.relative_to(folder).as_posix() for p in Path(folder).rglob("*") if p.is_file() and not p.name.startswith("."))


def night(card, env, name):
    return t.run("night.py", "--source", card, "--name", name, "--date", "2026-11-11", env=env)


def decide(st, names):
    groups = json.loads((st / "groups.json").read_text(encoding="utf-8"))["groups"]
    shoots = [{"id": f"s{i}", "suggested": names[i - 1], "groups": [g["id"]], "photos": g["count"],
               "recap": "Test frames.", "why": "test"} for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    return groups


def mixed(work):
    print("\nA card with photos and clips together")
    home, drive, card = work / "home", work / "drive", work / "CARD"
    home.mkdir(); drive.mkdir()
    env = {"STUDIO_HOME": str(home)}
    # shoot 1: 6 photos with 3 clips shot in among them; shoot 2 (40 minutes on): 5 photos, no clips
    t.make_card(card, groups=(6, 5))
    d = card / "DCIM" / "100CANON"
    start = datetime(2026, 6, 4, 9, 0, 0).astimezone()
    for i, secs in enumerate((20, 110, 200)):
        clip_at(d / f"MVI_{9001 + i}.MP4", start + timedelta(seconds=secs))
    (d / "IMG_4471.xmp").write_bytes(b"<x:xmpmeta>a rating from the camera</x:xmpmeta>")
    before = card_hashes(card)
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)

    code, out = night(card, env, "clips card")
    session = drive / "2026-11-11 clips card"
    st = session / "_studio"
    check("the backup copies and checks the card, then asks for the look (exit 4)", code == 4, out[-600:])
    if code != 4:
        return
    check("the rows it prints say clips, never photos, for video", "6 photos and 3 video clips" in out and "photos or clips" not in out.split("NEEDS A LOOK")[-1], out[-700:])
    groups = decide(st, ["Garcia", "Park"])
    check("two shoots, and the first knows its 6 photos and 3 clips", len(groups) == 2 and (groups[0].get("photos"), groups[0].get("clips")) == (6, 3), str(groups[0]))
    check("the previews of a shoot with photos come from its photos, not its clips",
          all("MVI_" not in p for p in groups[0].get("previews", [])) and groups[0].get("previews"), str(groups[0].get("previews")))

    code, out = night(card, env, "clips card")
    check("it sorts, and asks for sneak peeks for the photos (exit 7)", code == 7, out[-600:])
    garcia, park = session / "2026-06-04 Garcia", session / "2026-06-04 Park"
    got = listing(garcia)
    want = ([f"Photos/Garcia_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 7)] + ["Photos/Garcia_0001_IMG_4471.xmp"]
            + [f"Videos/Garcia_{n:04d}_MVI_{9000 + n}.MP4" for n in range(1, 4)])
    check("photos and clips: a Photos and a Videos folder, each numbered from 0001, the sidecar beside its photo", got == sorted(want), str(got))
    check("a shoot of photos only stays one flat folder", listing(park) == [f"Park_{n:04d}_IMG_{4476 + n}.JPG" for n in range(1, 6)], str(listing(park)))
    same = all(sha(p) == before[p.name.split("_", 2)[2]] for p in list(garcia.rglob("*.*")) + list(park.rglob("*.*")) if p.is_file())
    check("every sorted file is byte for byte what the card holds", same)
    sh = json.loads((st / "shoots.json").read_text(encoding="utf-8"))["shoots"]
    check("the shoot's folder on record is its own, not Photos inside it", sh[0].get("folder") == "2026-06-04 Garcia", str(sh[0].get("folder")))
    sheets = json.loads((st / "peek-sheets.json").read_text(encoding="utf-8"))["shoots"]
    check("the sneak-peek pages hold photos only", all(not m["file"].upper().endswith(".MP4") for s in sheets.values() for m in s["list"])
          and sheets["s1"]["photos"] == 6, str({k: v["photos"] for k, v in sheets.items()}))
    code, out = t.run("peek_sheets.py", "closer", session, "s1=1,2,3,4,5,6", "s2=1,2,3,4,5", env=env)
    check("the close look runs (with the face check on a Mac)", code == 0, out[-300:])
    checked = [f"--checked={sid} {n}: eyes open, mouth closed, sharp (a pretend photo)" for sid, nums in (("s1", range(1, 7)), ("s2", range(1, 6))) for n in nums]
    code, out = t.run("peek_sheets.py", "pick", session, "s1=1,2,3,4,5,6", "s2=1,2,3,4,5", *checked, env=env)
    check("the sneak peeks are picked", code == 0, out[-300:])

    # a second sort plans nothing new
    code, out = t.run("sort.py", session, "--dry-run", env=env)
    check("the sorter run again plans nothing (safe to run twice)", code == 0 and "e.g." not in out, out[-400:])

    page = (st / "report.html").read_text(encoding="utf-8")
    check("the report says 11 photos and 3 clips, and 6 photos and 3 clips for the shoot",
          "11 photos and 3 video clips" in page and "6 photos and 3 video clips" in page, "")
    check("the report never says \"photos or clips\", and names the two folders", "photos or clips" not in page and "<b>Photos</b>" in page and "<b>Videos</b>" in page)

    # rename, there and back, before the settle
    snap = {p.name.split("_", 2)[2]: sha(p) for p in garcia.rglob("*.*") if p.is_file()}
    code, out = t.run("rename_shoot.py", session, "--shoot", "s1", "--name", "Garcia family", env=env)
    fam = session / "2026-06-04 Garcia family"
    got = listing(fam) if fam.is_dir() else []
    want2 = ([f"Photos/Garcia-family_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 7)] + ["Photos/Garcia-family_0001_IMG_4471.xmp"]
             + [f"Videos/Garcia-family_{n:04d}_MVI_{9000 + n}.MP4" for n in range(1, 4)])
    extra = [x for x in got if x.endswith(".xmp") and "IMG_4471" not in x]   # the Assistant's own sneak-peek sidecars, if marked yet
    check("a rename carries both folders: every photo and clip takes the new name in its own folder",
          code == 0 and sorted(set(got) - set(extra)) == sorted(want2) and not garcia.exists(), out[-500:] + str(got))
    check("after the rename every file is the same bytes", fam.is_dir() and all(sha(p) == snap[p.name.split("_", 2)[2]] for p in fam.rglob("*.*") if p.is_file() and p.name.split("_", 2)[2] in snap))
    ix = json.loads((st / "index.json").read_text(encoding="utf-8"))["photos"]
    check("the records say where every file is now", all((session / p["file"]).is_file() for p in ix), str([p["file"] for p in ix if not (session / p["file"]).is_file()][:3]))
    code, out = t.run("rename_shoot.py", session, "--shoot", "s1", "--name", "Garcia family", env=env)
    check("the same rename again does nothing", code == 0 and "Nothing to do" in out, out[-300:])

    # a rename cut off after the folder moved and one file was renamed: the next run finishes it
    log_path = st / "rename-log.json"
    files = json.loads((st / "manifest.json").read_text(encoding="utf-8"))["files"]
    moves = []
    for p in ix:
        cur = Path(p["file"])
        new = Path("2026-06-04 Cut off") / cur.parent.name / cur.name.replace("Garcia-family_", "Cut-off_")
        moves.append({"from": p["file"], "to": new.as_posix(), "original": p["original"], "sha256": files[p["original"]]["sha256"]}) if cur.parts[0] == fam.name else None
    cut = session / "2026-06-04 Cut off"
    fam.rename(cut)
    first = moves[0]
    (cut / Path(*Path(first["from"]).parts[1:])).rename(session / first["to"])
    first["moved"] = True
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["renames"].append({"shoot": "s1", "from_name": "Garcia family", "to_name": "Cut off", "started": "2026-11-11T10:00:00",
                           "moves": moves, "verified": 0, "problems": []})
    log_path.write_text(json.dumps(log), encoding="utf-8")
    code, out = t.run("rename_shoot.py", session, "--shoot", "s1", "--name", "Cut off", env=env)
    got = [x for x in listing(cut) if not (x.endswith(".xmp") and "IMG_4471" not in x)]
    want3 = [w.replace("Garcia-family_", "Cut-off_") for w in want2 if not w.endswith(".xmp")]
    check("a rename cut off part way is finished by the next run, in both folders",
          code == 0 and [x for x in got if not x.endswith(".xmp")] == sorted(want3), out[-500:] + str(got))
    ix = json.loads((st / "index.json").read_text(encoding="utf-8"))["photos"]
    check("and the records follow", all((session / p["file"]).is_file() for p in ix))
    code, out = t.run("rename_shoot.py", session, "--shoot", "s1", "--name", "Garcia", env=env)
    check("renamed back to Garcia", code == 0 and garcia.is_dir() and not cut.exists(), out[-400:])

    code, out = night(card, env, "clips card")
    records = drive / ".studio" / session.name
    up = drive / "2026-06-04 Garcia"
    check("the backup finishes and settles (exit 0), both folders in place on the drive",
          code == 0 and (records / "settled.json").is_file() and not session.exists()
          and (up / "Photos").is_dir() and (up / "Videos").is_dir() and len(list((up / "Videos").glob("*.MP4"))) == 3, out[-600:])
    if (records / "settled.json").is_file():
        same = all(sha(p) == before[p.name.split("_", 2)[2]] for f in (up, drive / "2026-06-04 Park") for p in f.rglob("*.*")
                   if p.is_file() and p.name.split("_", 2)[2] in before)
        check("after the settle every photo and clip is byte for byte the card's", same)
        code, out = t.run("rename_shoot.py", records, "--shoot", "s1", "--name", "Garcia beach", env=env)
        beach = drive / "2026-06-04 Garcia beach"
        check("a rename after the settle carries both folders too", code == 0 and (beach / "Photos").is_dir()
              and len(list((beach / "Videos").glob("Garcia-beach_*.MP4"))) == 3 and not up.exists(), out[-400:])
        q = json.loads((home / "queue.json").read_text(encoding="utf-8"))["shoots"]
        x = next((s for s in q if s.get("shoot") == "s1"), {})
        check("your shoots counts 6 photos and 3 clips for it", (x.get("count"), x.get("clips")) == (6, 3), str(x))
    check("the card is exactly as it was", card_hashes(card) == before)


def video_only(work):
    print("\nA card of nothing but clips")
    home, drive, card = work / "home2", work / "drive2", work / "CARD2"
    home.mkdir(); drive.mkdir()
    d = card / "DCIM" / "100CANON"
    d.mkdir(parents=True)
    env = {"STUDIO_HOME": str(home)}
    start = datetime(2026, 6, 5, 14, 0, 0).astimezone()
    for i in range(4):
        clip_at(d / f"MVI_{7001 + i}.MP4", start + timedelta(minutes=2 * i))
    before = card_hashes(card)
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)
    code, out = night(card, env, "video card")
    session = drive / "2026-11-11 video card"
    st = session / "_studio"
    check("the backup asks for the look (exit 4) and its row says 4 clips", code == 4 and "4 video clips" in out.split("NEEDS A LOOK")[-1], out[-600:])
    if code != 4:
        return
    groups = decide(st, ["Video clips"])
    if sys.platform == "darwin":
        pv = groups[0].get("previews", [])
        pages = json.loads((st / "clip-sheets.json").read_text(encoding="utf-8")) if (st / "clip-sheets.json").is_file() else {}
        check("on a Mac the look also gets a clip page: three frames from each of the 4 clips, and says so",
              len(pages.get("clips", [])) == 4 and all(len(m["frames"]) == 3 for m in pages["clips"]) and Path(pages["pages"][0]).stat().st_size > 2000
              and "VIDEO CLIPS: also read this page" in out and "rows 01 to 04" in out, out[-900:])
        check("on a Mac the look gets a still from each clip", len(pv) == 4 and pv == groups[0].get("clip_previews") and all((st / "groups" / p).stat().st_size > 500 for p in pv), str(groups[0].get("previews")))
    code, out = night(card, env, "video card")
    records = drive / ".studio" / session.name
    check("no photos, so no sneak peeks are asked for: it finishes in one go (exit 0, never 7)",
          code == 0 and "only video clips" in out and (records / "settled.json").is_file(), out[-700:])
    flat = drive / "2026-06-05 Video clips"
    check("a shoot of clips only is one flat folder", listing(flat) == [f"Video-clips_{n:04d}_MVI_{7000 + n}.MP4" for n in range(1, 5)] if flat.is_dir() else False, str(listing(flat) if flat.is_dir() else out[-300:]))
    if (records / "report.html").is_file():
        page = (records / "report.html").read_text(encoding="utf-8")
        check("the report says 4 clips and never calls them photos", "4 video clips" in page and "4 photos" not in page and "photos or clips" not in page)
        if sys.platform == "darwin":
            check("the report shows the stills with a play mark", "class='ph clip'" in page)
        check("the report offers the way to every clip, and its folder button says video",
              "See all 4 video clips" in page and "Open video folder" in page and "Where your video clips are" in page and "Open photo folder" not in page)
        if sys.platform == "darwin":
            plays = re.findall(r"data-play='([^']+)'", page)
            ix = {p["file"] for p in json.loads((records / "index.json").read_text(encoding="utf-8"))["photos"]}
            check("each still names the clip a click plays, exactly as the records spell it", plays and all(f in ix and f.endswith(".MP4") for f in plays), str(plays))
        served(records, env)
    check("the card is exactly as it was", card_hashes(card) == before)


def upright_rules(work):
    print("\nWhich way up a still is")
    sys.path.insert(0, str(SCRIPTS))
    import clips
    face = lambda tip, sure=0.9, big=0.03: {"faces": [[tip, sure, big]], "bodies": []}  # noqa: E731
    check("a face tipped a quarter turn one way turns the still 90, the other way 270, upside down 180",
          (clips.turn_for(face(91)), clips.turn_for(face(-88)), clips.turn_for(face(178))) == (90, 270, 180))
    check("an upright face, or a head tipped part way, is left alone", clips.turn_for(face(3)) == 0 and clips.turn_for(face(35)) == 0)
    check("nobody in the picture: never turned on a guess", clips.turn_for({"faces": [], "bodies": []}) == 0 and clips.turn_for(face(90, sure=0.2)) == 0)
    check("the biggest face decides", clips.turn_for({"faces": [[90, 0.9, 0.01], [0, 0.9, 0.05]], "bodies": []}) == 0)
    check("no face: a body lying across the picture turns it", clips.turn_for({"faces": [], "bodies": [[-0.3, 0.05]]}) == 90
          and clips.turn_for({"faces": [], "bodies": [[0.3, 0.05]]}) == 270 and clips.turn_for({"faces": [], "bodies": [[0.0, 0.4]]}) == 0)
    # which moment of a clip becomes its preview
    check("the preview is the moment where the face makes the best picture", clips.best_moment([0.2, 0.0, 0.25, 0.53, 0.3]) == 3)
    check("nobody in any moment: the middle one", clips.best_moment([0, 0, 0, 0, 0]) == 2 and clips.best_moment([]) == 0)
    check("moments as good as each other: the one nearest the middle", clips.best_moment([0.5, 0.2, 0.5, 0.2, 0.5]) == 2)
    check("a face scores by Apple's own number for the biggest sure face; no face, or an unsure one, scores nothing",
          clips.face_score({"faces": [[0, 0.9, 0.01, 0.2], [0, 0.9, 0.05, 0.6]], "bodies": []}) == 0.6
          and clips.face_score({"faces": [], "bodies": [[0, 0.4]]}) == 0 and clips.face_score({"faces": [[0, 0.3, 0.05, 0.9]], "bodies": []}) == 0)
    # a still with nobody in it takes the turn of the clip beside it, once
    folder = work / "turns"
    folder.mkdir()
    for n in ("a.jpg", "b.jpg", "c.jpg"):
        (folder / n).write_bytes(t.jpeg_bytes(60, 40, lambda x, y: (200, 60, 60)))
    clips.note_turn(folder, "a.jpg", 0, False, "nobody to go by")
    clips.note_turn(folder, "b.jpg", 90, True, "the people in it")
    clips.note_turn(folder, "c.jpg", 0, True, "the people in it")
    asked = []
    real, clips.rotate = clips.rotate, lambda pic, turn: asked.append((Path(pic).name, turn)) or True
    try:
        clips.borrow_turns(folder, ["a.jpg", "b.jpg", "c.jpg"])
        clips.borrow_turns(folder, ["a.jpg", "b.jpg", "c.jpg"])
    finally:
        clips.rotate = real
    check("a still with nobody in it takes the turn of the clip beside it, and only once", asked == [("a.jpg", 90)], str(asked))


def turning(work):
    """Sideways clips stand up in the backup copy (Dustin, Nov 11): the orientation note in the clip's own header is
    set on the drive's copy, never on the card; the log is written first; one read proves nothing else changed and
    gives the new hash, kept beside the card's; a second run does nothing; the sort, the settle and a rename still
    prove every file; --undo puts the bytes back exactly; the report says what was turned."""
    print("\nSideways clips turned upright in the backup copy")
    sys.path.insert(0, str(SCRIPTS))
    import clips
    home, drive, card = work / "home3", work / "drive3", work / "CARD3"
    home.mkdir(); drive.mkdir()
    d = card / "DCIM" / "100CANON"
    d.mkdir(parents=True)
    env = {"STUDIO_HOME": str(home)}
    start = datetime(2026, 6, 6, 10, 0, 0).astimezone()
    for i in range(3):
        clip_at(d / f"MVI_{8001 + i}.MP4", start + timedelta(minutes=3 * i))
    before = card_hashes(card)
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)
    code, out = night(card, env, "turn card")
    session = drive / "2026-11-11 turn card"
    st = session / "_studio"
    check("the backup copies the card and asks for the look", code == 4, out[-500:])
    if code != 4:
        return
    decide(st, ["Chair"])
    # nobody is in the test clips, so nothing was turned by the backup itself; now the clip pages say which way up
    # each clip is (as the Mac's look would have), and the turn is asked for by hand
    log = json.loads((st / "clip-rotations.json").read_text(encoding="utf-8")) if (st / "clip-rotations.json").is_file() else {}
    if sys.platform == "darwin":
        check("with nobody in any clip the backup turns nothing and says so in its log",
              log.get("status") == "done" and all(x["status"] == "left" and not x["turn"] for x in log.get("turns", [])), str(log)[:400])
    files = [f"DCIM/100CANON/MVI_{8001 + i}.MP4" for i in range(3)]
    (st / "clip-sheets.json").write_text(json.dumps({"made": 3, "of": 3, "pages": [], "clips": [
        {"n": 1, "file": files[0], "group": "g01", "turn": 90, "sure": True},
        {"n": 2, "file": files[1], "group": "g01", "turn": 0, "sure": False},     # nobody: takes the clip beside it
        {"n": 3, "file": files[2], "group": "g01", "turn": 270, "sure": True}]}), encoding="utf-8")
    code, out = t.run("clips.py", "rotate", session, "--dry-run", env=env)
    check("a dry run says what it would turn and changes nothing", code == 0 and "3 clips would be turned" in out and card_hashes(card) == before
          and all(sha(session / f) == before[Path(f).name] for f in files), out[-500:])
    code, out = t.run("clips.py", "rotate", session, env=env)
    log = json.loads((st / "clip-rotations.json").read_text(encoding="utf-8"))
    by = {x["original"]: x for x in log["turns"]}
    check("the three clips are turned: 90, 90 borrowed from the clip beside it, and 270, each checked",
          code == 0 and [(by[f]["turn"], by[f]["status"]) for f in files] == [(90, "checked"), (90, "checked"), (270, "checked")]
          and by[files[1]]["how"] == "the clip beside it", out[-600:] + str(by)[:300])
    manifest = json.loads((st / "manifest.json").read_text(encoding="utf-8"))["files"]
    ix = {p.get("original") or p["file"]: p for p in json.loads((st / "index.json").read_text(encoding="utf-8"))["photos"]}
    ok = True
    for f, turn in zip(files, (90, 90, 270)):
        tm = clips.track_matrix(session / f)
        now = sha(session / f)
        ok = ok and tm["matrix"] == clips.matrix_for(turn, tm["w"], tm["h"]) and now != before[Path(f).name]
        ok = ok and manifest[f]["sha256"] == now and manifest[f]["card_sha256"] == before[Path(f).name] and manifest[f]["turned"] == turn
        ok = ok and ix[f]["sha256"] == now and ix[f]["card_sha256"] == before[Path(f).name]
        data = bytearray((session / f).read_bytes()); data[tm["at"]:tm["at"] + 36] = clips.IDENTITY
        ok = ok and hashlib.sha256(bytes(data)).hexdigest() == before[Path(f).name]   # only those 36 bytes differ
    check("each clip's header carries its turn, nothing else in the file changed, and the records keep both hashes", ok)
    video = clips._video()
    check("the video reader now sees the turn and the picture standing tall", video.facts(session / files[0])["rotation"] == 90
          and video.facts(session / files[0])["w"] < video.facts(session / files[0])["h"])
    code, out = t.run("clips.py", "rotate", session, env=env)
    log2 = json.loads((st / "clip-rotations.json").read_text(encoding="utf-8"))
    check("run again it does nothing", code == 0 and log2["turns"] == log["turns"] and all(sha(session / f) == manifest[f]["sha256"] for f in files), out[-300:])
    # a run cut off after the log was written and the bytes changed, before the check: the next run finishes it
    log2["turns"][0]["status"] = "written"; log2["turns"][0].pop("sha256", None); log2["status"] = "turning"
    (st / "clip-rotations.json").write_text(json.dumps(log2), encoding="utf-8")
    code, out = t.run("clips.py", "rotate", session, env=env)
    log3 = json.loads((st / "clip-rotations.json").read_text(encoding="utf-8"))
    check("a run cut off before its check is finished by the next run", code == 0 and log3["turns"][0]["status"] == "checked" and log3["status"] == "done", out[-300:])
    # a clip changed on the drive since: refused, nothing written
    bad = session / files[2]
    data = bytearray(bad.read_bytes()); data[-1] ^= 1; bad.write_bytes(bytes(data))
    log3["turns"][2]["status"] = "planned"; log3["turns"][2].pop("sha256", None)
    (st / "clip-rotations.json").write_text(json.dumps(log3), encoding="utf-8")
    code, out = t.run("clips.py", "rotate", session, env=env)
    log4 = json.loads((st / "clip-rotations.json").read_text(encoding="utf-8"))
    check("a clip whose bytes no longer match the backup's record is a problem, said plainly, and the run says so (exit 1)",
          code == 1 and "PROBLEM" in out and "does not match" in out and log4["status"] == "done with problems", out[-400:])
    data[-1] ^= 1; bad.write_bytes(bytes(data))
    log4["turns"][2]["status"] = "checked"; log4["turns"][2].pop("problem", None); log4["status"] = "done"
    log4["turns"][2]["sha256"] = sha(bad)
    (st / "clip-rotations.json").write_text(json.dumps(log4), encoding="utf-8")
    # the rest of the backup: sort, report, settle, all proving the turned files
    code, out = night(card, env, "turn card")
    records = drive / ".studio" / session.name
    flat = drive / "2026-06-06 Chair"
    check("the backup sorts and settles with the turned clips (exit 0), every file proved", code == 0 and (records / "settled.json").is_file()
          and sorted(p.name for p in flat.glob("*.MP4")) == [f"Chair_{n:04d}_MVI_{8000 + n}.MP4" for n in range(1, 4)], out[-700:])
    if (records / "report.html").is_file():
        page = (records / "report.html").read_text(encoding="utf-8")
        check("the report says the 3 clips were turned upright and the card is as it was",
              "3 video clips were filmed with the camera on its side" in page and "memory card is exactly as it was" in page)
    code, out = t.run("rename_shoot.py", records, "--shoot", "s1", "--name", "Green chair", env=env)
    moved = drive / "2026-06-06 Green chair"
    check("a rename after the turn still proves every clip", code == 0 and moved.is_dir() and len(list(moved.glob("*.MP4"))) == 3, out[-400:])
    code, out = t.run("clips.py", "rotate", records, "--undo", env=env)
    manifest = json.loads((records / "manifest.json").read_text(encoding="utf-8"))["files"]
    check("--undo puts every clip back byte for byte as the card has it, and the records say so",
          code == 0 and all(sha(p) == before[p.name.split("_", 2)[2]] for p in moved.glob("*.MP4"))
          and all(manifest[f]["sha256"] == before[Path(f).name] and not manifest[f]["turned"] for f in files), out[-500:])
    log5 = json.loads((records / "clip-rotations.json").read_text(encoding="utf-8"))
    check("after the undo the log holds no turn, so a report rebuilt now says nothing about turning", not clips.turned(records) and log5["status"] == "done")
    check("the card is exactly as it was", card_hashes(card) == before)


def served(records, env):
    """The report's server: a click plays a clip the records list and nothing else; See all opens the clips' folder.
    The opener itself is swapped for a recorder, so no player and no folder window ever opens in a test."""
    import importlib
    import threading
    import urllib.request
    from functools import partial
    from urllib.parse import quote
    sys.path.insert(0, str(SCRIPTS))
    with t.environ(**env):
        sr = importlib.import_module("serve_report")
    opened = []
    sr.open_in_player = lambda p: opened.append(("play", Path(p).name)) or (True, "")
    sr.show_in_finder = lambda p: opened.append(("folder", Path(p).name)) or (True, "")
    sr.Handler.studio = str(records)
    sr.Handler.last_open = {}
    srv = sr.fresh.Server(("127.0.0.1", 0), partial(sr.Handler, directory=str(records)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def get(path):
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
        return json.loads(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10).read().decode("utf-8"))
    try:
        ix = json.loads((records / "index.json").read_text(encoding="utf-8"))["photos"]
        clip = ix[0]["file"]
        r = get("/play?file=" + quote(clip))
        check("a click on a still plays that clip in the computer's player", r["ok"] and opened == [("play", Path(clip).name)], str((r, opened)))
        r = get("/play?file=" + quote("../../etc/passwd"))
        r2 = get("/play?file=" + quote(str(records / "manifest.json")))
        check("anything that is not a clip the records list is refused", not r["ok"] and not r2["ok"] and len(opened) == 1, str(opened))
        r = get("/open-clips?shoot=s1")
        check("See all opens the folder the shoot's clips are in", r["ok"] and opened[-1] == ("folder", "2026-06-05 Video clips"), str((r, opened)))
        r = get("/open-clips?shoot=nope")
        check("a shoot the report does not know opens nothing", not r["ok"] and len(opened) == 2, str(opened))
    finally:
        srv.shutdown()
        srv.server_close()


def quiet_card(work):
    print("\nA card that has stopped answering")
    sys.path.insert(0, str(SCRIPTS))
    import time
    import cards
    card = work / "CARD quiet"
    t.make_card(card, groups=(3,))
    check("a card that answers passes, and the probe reads the front of its files",
          cards.answers(card) and cards.probe(card) == 3)
    t0 = time.time()
    quiet = cards.answers(card, limit=2, cmd=[sys.executable, "-c", "import time; time.sleep(120)"])
    check("a card whose read never comes back is given up on at the time limit, not waited for", quiet is False and time.time() - t0 < 6, f"{time.time() - t0:.1f} s")
    # the backup itself: with the card reader swapped for one that never answers, it stops in plain words
    home, drive = work / "home quiet", work / "drive quiet"
    home.mkdir(); drive.mkdir()
    env = {"STUDIO_HOME": str(home)}
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", "--file-names", "shoot", env=env)
    stub = work / "stub"
    stub.mkdir()
    (stub / "sitecustomize.py").write_text(
        "import cards_never\n", encoding="utf-8")
    (stub / "cards_never.py").write_text(
        "import sys\n"
        "if len(sys.argv) > 2 and sys.argv[0].endswith('cards.py') and sys.argv[1] == 'probe':\n"
        "    import time; time.sleep(120)\n", encoding="utf-8")
    import os
    env2 = dict(env, PYTHONPATH=str(stub) + os.pathsep + os.environ.get("PYTHONPATH", ""), ASSISTANT_CARD_ANSWER_SECONDS="2")
    t0 = time.time()
    code, out = t.run("night.py", "--source", card, "--check", env=env2)
    check("the check stops within seconds and says so in plain words (exit 2), with nothing copied",
          code == 2 and "stopped answering" in out and "Take the card out" in out and time.time() - t0 < 15 and not any(drive.iterdir()),
          f"exit {code} after {time.time() - t0:.1f} s: {out[-300:]}")
    code, out = t.run("night.py", "--source", card, "--check", env=env)
    check("the same card, answering, passes the check", code == 0 and "PREFLIGHT OK" in out, out[-300:])


def undated(work):
    print("\nVideo clips whose date is hard to find")
    sys.path.insert(0, str(SCRIPTS))
    import os
    import exif_read
    import index as index_mod
    session = work / "undated"
    (session / "_studio").mkdir(parents=True)
    (session / "_studio" / "manifest.json").write_text(json.dumps({"session": "undated", "files": {}}), encoding="utf-8")
    d = session / "DCIM" / "100CANON"
    d.mkdir(parents=True)
    data = CLIP.read_bytes()
    # 1. the header at the end of a big file, where the quick reader does not look (phones write clips this way)
    ftyp_len = struct.unpack(">I", data[:4])[0]
    pad = 1_300_000
    far = data[:ftyp_len] + struct.pack(">I", pad) + b"free" + b"\0" * (pad - 8) + data[ftyp_len:] + struct.pack(">I", pad) + b"free" + b"\0" * (pad - 8)
    (d / "PHONE_1.MP4").write_bytes(far)
    # 2. no date in the header at all: the file's own time is what is left
    blank = bytearray(data)
    at = blank.find(b"mvhd")
    struct.pack_into(">II", blank, at + 8, 0, 0)
    (d / "NODATE_2.MP4").write_bytes(bytes(blank))
    when = datetime(2026, 5, 2, 16, 30, 0).timestamp()
    os.utime(d / "NODATE_2.MP4", (when, when))
    check("the quick reader finds no date in either (which is why they used to be set aside)",
          not exif_read.read(d / "PHONE_1.MP4").get("taken") and not exif_read.read(d / "NODATE_2.MP4").get("taken"))
    ix = index_mod.build(session)
    by = {Path(p["file"]).name: p for p in ix["photos"]}
    a, b = by["PHONE_1.MP4"], by["NODATE_2.MP4"]
    check("a clip with its header at the end of the file gets its date from the header", a.get("taken", "").startswith("2026-11-07T") and a.get("taken_from") == "the clip's header", str(a))
    check("a clip with no date in its header gets the file's own time", b.get("taken") == "2026-05-02T16:30:00" and b.get("taken_from") == "the file's own time", str(b))
    check("so neither is left out of the shoots", ix["no_date"] == [], str(ix["no_date"]))


def main():
    work = Path(tempfile.mkdtemp(prefix="clips-check-"))
    try:
        ok, how = t.pictures.ready()
        if not ok:
            print(f"SKIP: this computer cannot make the small pictures yet: {how}")
            return 0
        mixed(work)
        video_only(work)
        upright_rules(work)
        turning(work)
        quiet_card(work)
        undated(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
