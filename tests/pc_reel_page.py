#!/usr/bin/env python3
"""The reel page's own machinery (reel_page.py) on a PC, tried for real: written to run on GitHub's Windows
machine, and on a Mac.

    python tests/pc_reel_page.py

tests/reel_page_check.py and tests/reel_fixes_check.py are the full tests of the reel page, but they need a Mac
(sips draws their pretend kit). This one needs nothing installed: its pretend kit is header-only JPEGs with the
numbered list (sheet.json) written by hand, and the test beat WAV. In a scratch folder it makes itself
(STUDIO_HOME points there; nothing else is touched, no port is used, no CapCut, no folder opened):
  1. Make my reel refused, the way the route refuses: no photos, 41 photos, a vibe that isn't hers, a song named
     by a path, a song that isn't the shoot's, a numbered list from before, a kit outside Your Content;
  2. a test make through the job (popen_detached starts it, so on a PC with no window and a group of its own): it
     finishes, with her Plan line and the Beats per piece line, and no path;
  3. a second press while a job is at work is told (409), and the lock probe ("is a job at work?") while the job's
     process waits, then that job stopped outright (this_computer.stop_tree) is told as stopped part way;
  4. the job's one limit: a job that can't get its turn within its time says hers "That took too long";
  5. stop_tree stops a program and the program it started;
  6. a recording's sound made once beside it ("<name> sound.wav" on a PC with no ffmpeg, ".m4a" on a Mac), used
     again, never written over; one beside a recording that can't be read is left as it is, and a new one made
     beside it ("<name> sound 2..."). SKIP when this computer can't take the sound out of a video;
  7. step 1, the footage: header-only videos listed by key, the PC's plain words where a preview would be
     (this_computer.NO_PREVIEW, HEVC_HELP for an iPhone's HEVC), a moment added, changed, removed and put back,
     and a test make with a clip (Bookends, one clip in twice). On a Mac the PC's route is asked for.
  8. the chat's footage look (footage.py) on a PC: scan and close make no sheets and stop with exit 3 in plain
     words (still printing each video's key and facts); moments refused when wrong, written when right, their own
     moment kept first.
Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept (its place is
printed), and cleared away when everything passed.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
FIX = ROOT / "tests" / "fixtures"
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:400]}]" if detail and not ok else ""), flush=True)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


work = Path(tempfile.mkdtemp(prefix="assistant pc reel "))
STUDIO = work / "studio"
STUDIO.mkdir()
os.environ["STUDIO_HOME"] = str(STUDIO)           # before arrange is imported: it reads STUDIO_HOME then
os.environ["ASSISTANT_TEST_OPEN"] = "front"       # no folder is ever opened
os.environ["ASSISTANT_TEST_CAPCUT"] = "1"         # CapCut is never started
sys.path.insert(0, str(SCRIPTS))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import reel_page  # noqa: E402

this_computer.utf8_output()
print(f"This is a {this_computer.COMPUTER}, Python {sys.version.split()[0]}.\n", flush=True)
HOME = work / "The Assistant"
r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--home", str(HOME)], capture_output=True,
                   encoding="utf-8", errors="replace", env=dict(os.environ))
check("a pretend Assistant folder is set up (posts.py setup)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
CONTENT = HOME / "Your Content"
CONTENT.mkdir(parents=True, exist_ok=True)
KIT = "2026-11-04 Zoë’s reel"


def tiny_jpeg(path, w, h):
    """A JPEG with only its header: its size, and nothing to draw (a plan only needs the size)."""
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, h, w, 3) + bytes([1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1])
    path.write_bytes(b"\xff\xd8" + sof + b"\xff\xd9")


def make_kit():
    kit = CONTENT / KIT
    photos = kit / "Photos"
    photos.mkdir(parents=True)
    (kit / ".kit").mkdir()
    rows = []
    for n in range(1, 13):
        w, h = (1600, 1067) if n % 4 == 0 else (1080, 1350)
        f = photos / ("p-%03d.jpg" % n)
        tiny_jpeg(f, w, h)
        rows.append({"n": n, "file": str(f), "w": w, "h": h, "way": "wide" if w > h else "tall"})
    rec = {"name": "Zoë’s reel", "date": "2026-11-04", "folder": KIT, "source": "drop",
           "photos": sorted(p.name for p in photos.iterdir()), "picks": {"reel": [1, 2, 3, 4, 5, 6]}}
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    (kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(photos), "photos": rows}, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
    (kit / "Music").mkdir()
    (kit / "Music" / "Beat.wav").write_bytes((FIX / "test-beat-60s.wav").read_bytes())
    return kit


def picks(nums):
    return [{"n": n, "h": ""} for n in nums]


def song(kit, name):
    return next((x["id"] for x in reel_page.songs_for_page(kit) if x["name"] == name), None)


def body(k, **more):
    b = {"kit": KIT, "stamp": arrange.sheet_stamp(k), "picks": picks([1, 2, 3, 4, 5, 6]), "song": song(k, "Beat"),
         "vibe": "beat", "test": True}
    b.update(more)
    return b


def wait_job(kit, seconds=180):
    end = time.time() + seconds
    while time.time() < end:
        j = reel_page.job_for_page(kit)
        if j and j["state"] in ("done", "problem"):
            return j
        time.sleep(0.3)
    return reel_page.job_for_page(kit)


def no_path(obj):
    raw = json.dumps(obj, ensure_ascii=False)
    return str(work) not in raw and "\\\\" not in raw and "/Users/" not in raw


def refusals(kit):
    cases = {
        "no photos": (body(kit, picks=[]), 400),
        "41 photos": (body(kit, picks=picks(list(range(1, 13)) * 4)[:41]), 400),
        "a vibe that isn't hers": (body(kit, vibe="fast"), 400),
        "a song named by a path": (body(kit, song=str(kit / "Music" / "Beat.wav")), 400),
        "a song that isn't the shoot's": (body(kit, song="0123456789ab"), 400),
        "a numbered list from before": (body(kit, stamp="old"), 409),
        "a kit outside Your Content": (body(kit, kit="..\\Sneaky"), 404),
        "a field it doesn't know": (body(kit, folder="C:\\Windows"), 400),
    }
    for name, (b, want) in cases.items():
        code, j = reel_page.start_make(b)
        check(f"Make my reel refuses {name}", code == want and j.get("ok") is False, (code, j))
    check("nothing was started by the refusals", reel_page.read_job(kit) is None)


def test_make(kit):
    code, j = reel_page.start_make(body(kit))
    check("a test make is started (its own process, popen_detached)", code == 200 and j.get("ok") and j.get("job"), (code, j))
    job = wait_job(kit)
    check("it finishes, nothing made", job and job["state"] == "done" and job["dry"] is True, job)
    words = (job or {}).get("words") or []
    check("its lines are her Plan line, then Beats per piece", words[:1] and words[0].startswith("Plan: 6 photos")
          and any(w.startswith("Beats per piece") for w in words), words)
    check("no Wide line (her page has none), no path", not any(w.startswith("Wide") for w in words) and no_path(job), words)


def hold(path):
    f = open(path, "a", encoding="utf-8")
    got = this_computer.try_lock(f)
    return f, got


def second_press_and_stop(kit):
    f, got = hold(reel_page.MAKE_LOCK)                 # the job waits its turn on this computer's one reel lock
    check("(this test holds the computer's one Make my reel lock)", got is True, got)
    try:
        code, j = reel_page.start_make(body(kit))
        check("a make that has to wait its turn is started", code == 200, (code, j))
        end = time.time() + 30
        rec = {}
        while time.time() < end:
            rec = reel_page.read_job(kit) or {}
            if rec.get("pid"):
                break
            time.sleep(0.1)
        check("its process writes itself down", type(rec.get("pid")) is int, rec)
        check("the lock probe: a job is at work", reel_page.job_running(kit) is True)
        code, j = reel_page.start_make(body(kit))
        check("a second press while it waits is told, with that job to follow (409)", code == 409
              and j.get("words") == reel_page.OUR_WORDS["already_making"] and (j.get("job") or {}).get("id") == rec.get("id"), (code, j))
        check("the probe let go of the job's lock: the job still holds it", reel_page.job_running(kit) is True)
        check("stop_tree stops the job outright", this_computer.stop_tree(rec["pid"]) is True)
        end = time.time() + 20
        while time.time() < end and this_computer.still_running(rec["pid"]):
            time.sleep(0.2)
        job = reel_page.job_for_page(kit)
        check("a job stopped part way is told as one, in plain words", job and job["state"] == "problem"
              and job["problem"] == reel_page.OUR_WORDS["interrupted"], job)
    finally:
        this_computer.unlock(f)
        f.close()


def limit(kit):
    f, got = hold(reel_page.MAKE_LOCK)
    try:
        jid = "e" * 12
        arrange.write_whole(reel_page.job_path(kit), {"id": jid, "state": "queued", "t": time.time(), "dry": True,
                                                       "ask": {"picks": "1,2,3", "song": "", "vibe": "beat", "dry": True,
                                                               "stamp": arrange.sheet_stamp(kit)}})
        t0 = time.time()
        r = subprocess.run([sys.executable, str(SCRIPTS / "reel_page.py"), "job", str(kit), "--id", jid], capture_output=True,
                           encoding="utf-8", errors="replace", env=dict(os.environ, ASSISTANT_TEST_MAKE_LIMIT="3"), timeout=60)
        took = time.time() - t0
        j = reel_page.read_job(kit) or {}
        check("a job that can't get its turn within its time says hers 'That took too long', at its limit",
              j.get("state") == "problem" and (j.get("problem") or "").startswith("That took too long") and took < 20,
              (round(took, 1), j, r.stdout[-200:]))
    finally:
        this_computer.unlock(f)
        f.close()


GRANDCHILD = r"""
import subprocess, sys, time
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
open(sys.argv[1], "w").write(str(p.pid))
time.sleep(120)
"""


def tree():
    note = work / "grandchild.txt"
    p = this_computer.popen_detached([sys.executable, "-c", GRANDCHILD, str(note)], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
    end = time.time() + 20
    while time.time() < end and not (note.is_file() and note.read_text().strip()):
        time.sleep(0.1)
    try:
        gc = int(note.read_text().strip())
    except (OSError, ValueError):
        gc = None
    check("(a program that started a program of its own)", gc and this_computer.still_running(gc), gc)
    check("stop_tree answers", this_computer.stop_tree(p.pid) is True)
    end = time.time() + 20
    while time.time() < end and (this_computer.still_running(p.pid) or (gc and this_computer.still_running(gc))):
        time.sleep(0.2)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    check("stop_tree stopped the program and the one it started", not this_computer.still_running(p.pid)
          and not (gc and this_computer.still_running(gc)), (p.pid, gc))


def sounds(kit):
    music = kit / "Music"
    (music / "Rec.mov").write_bytes((FIX / "click-100bpm.m4a").read_bytes())    # a recording's sound, in a .mov box
    rid = song(kit, "Rec")
    check("a recording is listed once, as a recording", rid and [x["kind"] for x in reel_page.songs_for_page(kit) if x["name"] == "Rec"] == ["video"])
    code, j = reel_page.start_make(body(kit, song=rid))
    job = wait_job(kit)
    made = sorted(f for f in os.listdir(music) if f.startswith("Rec sound"))
    if job and job["state"] == "problem" and not made:
        skip("6: a recording's sound", "this computer can't take the sound out of a video here: " + str(job.get("problem")))
        return
    want = "Rec sound.wav" if this_computer.WINDOWS and not shutil.which("ffmpeg") else "Rec sound.m4a"
    check(f"a test make with a recording makes its sound once, beside it ({want})", job and job["state"] == "done"
          and made == [want], (job, made))
    if made != [want]:
        return
    snd = music / want
    h, m = snd.read_bytes(), snd.stat().st_mtime_ns
    code, j = reel_page.start_make(body(kit, song=rid, vibe="calm"))
    job = wait_job(kit)
    check("the next make uses the same sound: not written over, no second one", job and job["state"] == "done"
          and snd.read_bytes() == h and snd.stat().st_mtime_ns == m
          and sorted(f for f in os.listdir(music) if f.startswith("Rec sound")) == [want], job)
    check("no hidden half-file is left beside it", not [f for f in os.listdir(music) if f.startswith(".") and "part-" in f])
    (music / "Rec2.mov").write_bytes((FIX / "click-100bpm.m4a").read_bytes())
    (music / ("Rec2 sound" + Path(want).suffix)).write_bytes(b"")               # cut off by a make from before
    code, j = reel_page.start_make(body(kit, song=song(kit, "Rec2")))
    job = wait_job(kit)
    spare = music / ("Rec2 sound 2" + Path(want).suffix)
    check("one beside a recording that can't be read is left as it is, and a new one made beside it",
          job and job["state"] == "done" and spare.is_file() and (music / ("Rec2 sound" + Path(want).suffix)).stat().st_size == 0,
          (job, sorted(os.listdir(music))))


def footage(kit):
    """Step 1 on a PC: the videos are header-only (tests/pc_video.py builds them byte by byte), so nothing here ever
    decodes a picture. On a Mac the PC's route is asked for (ASSISTANT_NO_AVFOUNDATION=1)."""
    sys.path.insert(0, str(ROOT / "tests"))
    import pc_video as pv
    import video
    if not this_computer.WINDOWS:
        os.environ[video.NO_AV] = "1"
    try:
        fd = kit / "Footage"
        code, j = reel_page.open_music({"kit": KIT, "what": "footage"})
        check("Add my footage makes the shoot's Footage folder (no folder opened in a test)", code == 200 and j["ok"] and fd.is_dir(), j)
        pv.write(fd, "Phone é.MOV", pv.FTYP, pv.box(b"mdat", pv.DATA), pv.moov(pv.vtrak(rot=90), pv.atrak()))
        pv.write(fd, "iPhone HEVC.mov", pv.FTYP, pv.box(b"mdat", pv.DATA), pv.moov(pv.vtrak(codec=b"hvc1", conf=pv.hvcc(1)), pv.atrak()))
        (fd / "notes.txt").write_text("not a video", encoding="utf-8")
        end = time.time() + 30
        while True:
            f = reel_page.footage_for_page(kit)
            if all(v["preview"] not in ("waiting", "making") for v in f["videos"]) or time.time() > end:
                break
            time.sleep(0.2)
        vids = {v["name"]: v for v in f["videos"]}
        check("the videos listed by name and key, read from their headers (the sideways one shown 360 x 640)",
              sorted(vids) == ["Phone é.MOV", "iPhone HEVC.mov"] and (vids["Phone é.MOV"]["w"], vids["Phone é.MOV"]["h"]) == (360, 640)
              and all(len(v["key"]) == 12 for v in vids.values()) and no_path(f), f)
        hevc = "hevc_pc" if this_computer.WINDOWS else "pc"
        check("no preview on a PC yet: the plain words in its place (NO_PREVIEW; HEVC_HELP for an iPhone's HEVC on a PC)",
              vids["Phone é.MOV"]["preview"] == "pc" and vids["Phone é.MOV"]["words"] == this_computer.NO_PREVIEW
              and vids["iPhone HEVC.mov"]["preview"] == hevc
              and vids["iPhone HEVC.mov"]["words"] == (this_computer.HEVC_HELP if this_computer.WINDOWS else this_computer.NO_PREVIEW), vids)
        key = vids["Phone é.MOV"]["key"]
        code, j = reel_page.change_moments({"kit": KIT, "do": "add", "video": key, "start": 1.0, "seconds": 4})
        check("Use this moment still works (a moment of theirs, saved), with no still on its card", code == 200 and j["moments"][0]["end"] == 5.0
              and reel_page.moment_still_file(kit, j["moments"][0]["id"]) is None, j)
        mid = j["moments"][0]["id"]
        code, j = reel_page.change_moments({"kit": KIT, "do": "update", "id": mid, "end": 5.5})
        check("− and + work", code == 200 and j["moments"][0]["end"] == 5.5, j)
        code, j = reel_page.change_moments({"kit": KIT, "do": "remove", "id": mid})
        code2, j2 = reel_page.change_moments({"kit": KIT, "do": "restore", "id": mid, "at": 0})
        check("Remove and Undo", code == 200 and j["moments"] == [] and code2 == 200 and [m["id"] for m in j2["moments"]] == [mid], (j, j2))
        code, j = reel_page.start_make(body(kit, footage=True, style="bookends", clips=[mid]))
        job = wait_job(kit)
        beats = next((w for w in (job or {}).get("words", []) if w.startswith("Beats per piece")), None)
        check("a test make with the clip (Bookends, one clip in twice): her Plan line with 2 clips, the beats, no path",
              code == 200 and job and job["state"] == "done" and job["words"][0].startswith("Plan: 2 clips and 6 photos")
              and beats and beats.startswith("Beats per piece: clip ") and no_path(job), job)
        clips = json.loads((kit / ".kit" / "reels" / "clips.json").read_text(encoding="utf-8"))["clips"]
        check("clips.json holds the clip twice, from its own video", [c["moment"] for c in clips] == [mid, mid]
              and all(Path(c["path"]).name == "Phone é.MOV" for c in clips), clips)
    finally:
        os.environ.pop(video.NO_AV, None)


def footage_look(kit):
    """The chat's footage look (footage.py) on a PC: no stills can be taken from a video there yet (video.py's named
    gap), so scan and close make no sheets and stop with exit 3 in plain words, while the facts are still printed;
    moments works as on a Mac (checked, written under the record's lock, their own moments kept first). On a Mac
    the PC's route is asked for. The videos are part 7's header-only ones."""
    import video
    env = dict(os.environ)
    if not this_computer.WINDOWS:
        env[video.NO_AV] = "1"

    def run(*args):
        r = subprocess.run([sys.executable, str(SCRIPTS / "footage.py"), *args], capture_output=True, encoding="utf-8",
                           errors="replace", env=env, timeout=240)
        return r.returncode, (r.stdout + r.stderr)
    vids = {v["name"]: v for v in reel_page.list_videos(kit)}
    key = vids["Phone é.MOV"]["key"]
    looks = kit / ".kit" / "footage" / "looks"
    code, out = run("scan", KIT)
    pngs = [p.name for p in looks.rglob("*.png")] if looks.is_dir() else []
    check("scan on a PC: no sheets, exit 3, the PC's plain words, nothing drawn", code == 3 and this_computer.NO_PREVIEW in out
          and "no sheets were made" in out and pngs == [], (code, pngs, out[-500:]))
    check("scan on a PC still prints each video by its key, its length and shape (the sideways one 360x640 tall)",
          f"(key {key}): 0:06 long, 360x640 tall" in out and "Their notes for this reel" in out.split("\n")[0], out[:1500])
    check("scan on a PC writes its look in a new folder (look), with scan.json", (looks / "look" / "scan.json").is_file())
    code, out = run("close", KIT, key, "1", "3")
    check("close on a PC: exit 3, in plain words", code == 3 and this_computer.NO_PREVIEW in out, out[-300:])
    rec = kit / ".kit" / "reel-page.json"
    before = rec.read_bytes()
    bad = work / "too many.json"
    bad.write_text(json.dumps({"moments": [{"video": key, "start": k * 0.1, "end": k * 0.1 + 3.5} for k in range(13)]}), encoding="utf-8")
    code, out = run("moments", KIT, "--file", str(bad))
    check("moments on a PC: more than 12 refused, nothing written", code == 1 and "the most I pick is 12" in out and rec.read_bytes() == before, out)
    good = work / "moments.json"
    good.write_text(json.dumps({"moments": [{"video": key, "start": "0:00.5", "end": 4.0, "label": "Zoë laughing"},
                                             {"video": "iPhone HEVC.mov", "start": 2, "end": 5.5, "label": "A look back"}]},
                               ensure_ascii=False), encoding="utf-8")
    code, out = run("moments", KIT, "--file", str(good))
    ms = json.loads(rec.read_text(encoding="utf-8"))["moments"]
    check("moments on a PC: saved through the command, their own moment (part 7) kept first",
          code == 0 and [m.get("by") for m in ms] == ["you", None, None] and [m["label"] for m in ms[1:]] == ["Zoë laughing", "A look back"]
          and (ms[1]["start"], ms[1]["end"]) == (0.5, 4.0), (code, out, ms))
    page = reel_page.footage_for_page(kit)
    check("the page's answer has them, each by its video's key, no path", [m["key"] for m in page["moments"]][1:] == [key, vids["iPhone HEVC.mov"]["key"]]
          and no_path(page), page["moments"])


def part(name, fn, *args):
    print(f"\n-- {name}", flush=True)
    try:
        fn(*args)
    except Exception as e:  # noqa: BLE001
        import traceback
        check(f"{name}: ran to the end", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-600:]}")


kit = make_kit()
part("1: Make my reel refused", refusals, kit)
part("2: a test make through the job", test_make, kit)
part("3: a second press, the lock probe, a job stopped outright", second_press_and_stop, kit)
part("4: the job's one limit", limit, kit)
part("5: stop_tree", tree)
part("6: a recording's sound", sounds, kit)
part("7: step 1, the footage, on a PC (header-only videos)", footage, kit)
part("8: the chat's footage look, on a PC (footage.py)", footage_look, kit)

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
