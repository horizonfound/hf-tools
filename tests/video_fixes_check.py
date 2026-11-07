#!/usr/bin/env python3
"""The video helper after its reviewers (v19 review of stages b1 to b4, Nov 7), on a Mac, on clips this test makes
itself (10 s at most, 720 x 404, H.264; never a client's, never HEVC, never 4K).

    python3 tests/video_fixes_check.py [--work <scratch folder>]

Run it under the memory guard (it touches video). STUDIO_HOME is set to the scratch folder, so the computer-wide
video lock it tries is the test's own. What it checks, each a fault the reviewers found:
  1. this_computer.stop_scripts() stops a JavaScript program this process started (a page server calls it before
     it starts over: exec keeps the process's number, and the old program would carry on);
  2. the video lock is held by the running video program itself: the Python that started it is killed, and the
     lock stays held until that program ends;
  3. a video program stops by itself when the Python that started it is gone (stills: it stops part way);
  4. a server killed in the middle of making a copy: its program goes, and the next copy is made with no
     half-copy left beside it; a half-copy a stopped run left is taken away in the next copy's turn;
  5. a server that starts over in the same process number never takes its old half-copy's name;
  6. two page servers asked for the same video's preview at once: never two video programs at a time, one strip,
     one copy, no half-copies;
  7. Use this moment while a long copy is being made: the press doesn't wait for it, and the card's still is made
     afterwards, in its turn;
  8. a video still being copied into Footage is left alone (no facts kept, nothing made) until it is whole;
  9. afconvert has a time limit (sound.AFCONVERT_TIMEOUT), and says so in plain words when it runs out.
Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is kept then.
"""
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(REEL))
sys.path.insert(0, str(SCRIPTS))

RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(what, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:500]}]" if detail and not ok else ""), flush=True)
    return ok


def skip(what, why):
    RESULTS["SKIP"] += 1
    print(f"SKIP  {what}   [{why}]", flush=True)


def kids(pid, name="osascript"):
    """The programs called `name` whose parent is pid."""
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,comm="], capture_output=True, text=True).stdout
    got = []
    for ln in out.splitlines():
        a = ln.split(None, 2)
        if len(a) == 3 and a[1] == str(pid) and name in a[2]:
            got.append(int(a[0]))
    return got


def alive(pid):
    return subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode == 0


def child(code, *args):
    """A Python of its own (as a page server would be), with this test's paths and STUDIO_HOME."""
    pre = ("import sys, time, json\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\n" % (str(REEL), str(SCRIPTS)))
    return subprocess.Popen([sys.executable, "-c", pre + code, *[str(a) for a in args]])


def wait_for(fn, secs, every=0.005):
    end = time.time() + secs
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(every)
    return None


def main():
    import this_computer
    if not this_computer.MAC:
        skip("everything", "this needs a Mac (AVFoundation)")
        return 0
    if "--work" in sys.argv:
        work = Path(sys.argv[sys.argv.index("--work") + 1]).resolve()
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="assistant video fixes "))
    os.environ["STUDIO_HOME"] = str(work / "studio")
    import video
    import sound
    import video_check as vc
    if not video.avfoundation_here():
        skip("everything", "AVFoundation is switched off here (ASSISTANT_NO_AVFOUNDATION)")
        return 0
    lock = video.lock_path()
    check("the video lock is the test's own (in its STUDIO_HOME)", str(lock).startswith(str(work)), lock)

    # ---- the clip: 10 s, 720 x 404, 60 a second, with sound
    cols = ";".join(",".join(map(str, c)) for c in vc.COLOURS)
    pic = work / "picture.mov"
    vc.js("picture", str(pic), "720", "404", "10", "60", cols, timeout=300)
    wav = work / "tone.wav"
    vc.tone_wav(wav, secs=10, loud_at=5)
    m4a = work / "tone.m4a"
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], capture_output=True, check=True)
    clip = work / "clip.mov"
    vc.js("compose", str(pic), str(m4a), str(clip), "0", vc.RECORDED, timeout=300)
    check(f"made clip.mov ({clip.stat().st_size} bytes)", clip.stat().st_size > 1000)

    # ---- 1. stop_scripts
    box = {}

    def long_one():
        t0 = time.time()
        try:
            box["r"] = this_computer.mac_javascript("function run(){ delay(6); return 'slept' }", timeout=30)
        except Exception as e:  # noqa: BLE001
            box["r"] = e
        box["t"] = time.time() - t0
    th = threading.Thread(target=long_one)
    th.start()
    wait_for(lambda: kids(os.getpid()), 5)
    this_computer.stop_scripts()
    th.join(5)
    check("stop_scripts() stops a JavaScript program this process started (it had 6 s to go)",
          not th.is_alive() and box.get("t", 99) < 3 and not (isinstance(box.get("r"), tuple) and "slept" in box["r"][1]), box)

    # ---- 2. the lock is held by the program itself
    p = child("import video, this_computer\n"
              "with video.turn() as ok:\n"
              "    this_computer.mac_javascript(\"function run(){ delay(3); return 'x' }\", pass_fds=(video._HELD.f.fileno(),))\n")
    kid = wait_for(lambda: kids(p.pid), 10)
    os.kill(p.pid, signal.SIGKILL)
    p.wait()
    f = open(lock, "a", encoding="utf-8")
    held = this_computer.try_lock(f)
    check("its Python killed, the video lock stays held while the program it started still runs", kid and alive(kid[0]) and held is False,
          (kid, held))
    if held:
        this_computer.unlock(f)
    gone = wait_for(lambda: not alive(kid[0]), 8) if kid else None
    free = wait_for(lambda: this_computer.try_lock(f) is True, 3)
    check("and is free again the moment that program ends", gone and free, (gone, free))
    this_computer.unlock(f)
    f.close()

    # ---- 3. a video program stops by itself when its Python is gone
    orph = work / "orphan stills"
    times = ",".join("%.3f" % (k * 0.05) for k in range(150))
    p = child("import video\nvideo.stills(sys.argv[1], sys.argv[2].split(','), sys.argv[3], edge=720)\n", clip, times, orph)
    kid = wait_for(lambda: kids(p.pid), 10)
    wait_for(lambda: (orph / "look").is_dir() and any(n.endswith(".jpg") for n in os.listdir(orph / "look")), 15, 0.002)
    os.kill(p.pid, signal.SIGKILL)
    p.wait()
    t_kill = time.time()
    gone = wait_for(lambda: not alive(kid[0]), 5) if kid else None
    took = time.time() - t_kill
    time.sleep(1)
    n = len([x for x in os.listdir(orph / "look") if x.endswith(".jpg")]) if (orph / "look").is_dir() else -1
    batch = video._batch_size(video.facts(clip), 720)
    check(f"stills: the program stops by itself when its Python is gone ({n} of the first {batch} taken, gone in {took:.2f} s)",
          kid and gone and 0 < n < batch - 5, (kid, gone, n, batch, took))

    # ---- 4. a server killed in the middle of a copy
    out = work / "copy" / "preview.mp4"
    p = child("import video\nvideo.preview_copy(sys.argv[1], sys.argv[2])\n", clip, out)
    kid = wait_for(lambda: kids(p.pid), 10, 0.002)
    os.kill(p.pid, signal.SIGKILL)
    p.wait()
    gone = wait_for(lambda: not alive(kid[0]), 5) if kid else None
    check("a copy: its program goes too when its Python is killed, and nothing is under the copy's real name",
          kid and gone and not out.exists(), (kid, gone))
    stale = out.with_name(".preview.part-99999-abcdef.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"half a copy from a run that was stopped")
    theirs = out.with_name("preview notes.txt")
    theirs.write_text("not ours", encoding="utf-8")
    r = video.preview_copy(clip, out)
    left = sorted(os.listdir(out.parent))
    check("the next copy is made, in its turn, with every half-copy a stopped run left taken away (and nothing else)",
          r.get("made") and left == ["preview notes.txt", "preview.mp4"], (r, left))

    # ---- 5. a restart in the same process number never shares a half-copy's name
    spec = importlib.util.spec_from_file_location("video_again", str(REEL / "video.py"))
    again = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(again)
    a, b = video.copy_name(out), again.copy_name(out)
    check("the hidden name of a copy differs between two starts of the same process number (%s, %s)" % (a.name, b.name),
          a != b and str(os.getpid()) in a.name and str(os.getpid()) in b.name)

    # ---- 6. two page servers, one video, at once
    kit = work / "kit two"
    (kit / ".kit").mkdir(parents=True)
    go = time.time() + 2.0
    code = ("import reel_page, os\n"
            "kit = __import__('pathlib').Path(sys.argv[1]); clip = sys.argv[2]\n"
            "vm = reel_page._video()\n"
            "f = dict(vm.facts(clip), plays_as_is=False, codec='hvc1')\n"
            "v = {'key': 'abcabcabcabc', 'name': 'clip.mov', 'path': __import__('pathlib').Path(clip), 'size': os.path.getsize(clip), 'facts': f}\n"
            "while time.time() < float(sys.argv[3]): time.sleep(0.002)\n"
            "reel_page._make_preview(kit, v)\n")
    ps = [child(code, kit, clip, go) for _ in range(2)]
    most = 0
    while any(x.poll() is None for x in ps):
        most = max(most, sum(len(kids(x.pid)) for x in ps))
        time.sleep(0.01)
    d = kit / ".kit" / "footage" / "abcabcabcabc"
    names = sorted(os.listdir(d)) if d.is_dir() else []
    rec = json.loads((d / "preview.json").read_text(encoding="utf-8")) if (d / "preview.json").is_file() else {}
    check("two servers, one video's preview at once: never two video programs at a time (at most %d)" % most, most == 1, most)
    check("one strip and one copy, no half-copies, and the preview ready", names == ["preview.json", "preview.mp4", "strip"]
          and rec.get("state") == "ready" and rec.get("strip") == "strip", (names, rec))

    # ---- 7. Use this moment while a long copy is being made
    import reel_page
    held = threading.Event()
    let_go = threading.Event()

    def holder():
        with video.turn() as ok:
            held.set() if ok else None
            let_go.wait(30)
    th = threading.Thread(target=holder)
    th.start()
    held.wait(5)
    kit3 = work / "kit three"
    (kit3 / ".kit").mkdir(parents=True)
    v = {"key": "defdefdefdef", "name": "clip.mov", "path": clip, "size": clip.stat().st_size, "facts": video.facts(clip)}
    t0 = time.time()
    reel_page._moment_still(kit3, "u1-aaaaaa", v, 3.5)
    took = time.time() - t0
    md = kit3 / ".kit" / "footage" / "moments" / "u1-aaaaaa"
    check(f"Use this moment while another video program has the turn: the press waits only {reel_page.MOMENT_WAIT} s "
          f"({took:.1f} s) and makes nothing beside it", held.is_set() and took < reel_page.MOMENT_WAIT + 2 and not md.exists(),
          (took, md.exists()))
    let_go.set()
    th.join(5)
    got = wait_for(lambda: md.is_dir() and [x for x in os.listdir(md) if x.endswith(".jpg")], 20, 0.1)
    check("and the card's still is made afterwards, in its turn, by the preview worker", bool(got), got)

    # ---- 8. a video still being copied into Footage
    kit4 = work / "kit four"
    (kit4 / ".kit").mkdir(parents=True)
    (kit4 / "Footage").mkdir()
    whole = clip.read_bytes()
    dst = kit4 / "Footage" / "Copying.mov"
    states = []
    for part in (len(whole) // 3, 2 * len(whole) // 3, len(whole)):
        dst.write_bytes(whole[:part])
        coming = []
        vids = reel_page.list_videos(kit4, coming)
        states.append(([v["name"] for v in vids], [c["name"] for c in coming]))
    facts_kept = json.loads((kit4 / ".kit" / "footage" / "facts.json").read_text(encoding="utf-8"))
    check("a video copied in three steps: 'still coming in' twice, then listed once it is whole", states ==
          [([], ["Copying.mov"]), ([], ["Copying.mov"]), (["Copying.mov"], [])], states)
    check("and only the whole video's facts are kept (one record, not one for each size it passed)",
          len(facts_kept) == 1 and not any("refused" in x for x in facts_kept.values()), facts_kept)
    page = reel_page.videos_for_page(kit4, [], [{"name": "Copying.mov", "size": 12_000_000}])
    check("the page lists it by name with our line and no key", page == [{"key": "", "name": "Copying.mov", "length": 0,
          "w": 0, "h": 0, "mb": 12, "preview": "coming", "words": reel_page.OUR_WORDS["coming"].replace("{name}", "Copying.mov"),
          "strip": []}], page)
    broken = kit4 / "Footage" / "Old cut off.mov"
    broken.write_bytes(whole[: len(whole) // 2])
    old = time.time() - 3600
    os.utime(broken, (old, old))
    vids = {v["name"]: v for v in reel_page.list_videos(kit4, [])}
    check("a video cut off long ago is not 'coming': it is listed, and refused in plain words, as before",
          "Old cut off.mov" in vids and "cut off" in vids["Old cut off.mov"]["facts"].get("refused", ""), vids.keys())
    # wait for the preview worker (started by part 7's still) to have nothing left, so nothing runs past the test
    wait_for(lambda: reel_page._PREV_Q is None or reel_page._PREV_Q.empty(), 20, 0.1)

    # ---- 9. afconvert's time limit
    saved = sound.AFCONVERT_TIMEOUT
    sound.AFCONVERT_TIMEOUT = 0.0001
    try:
        a, how = sound.decode(wav, rate=8000)
    finally:
        sound.AFCONVERT_TIMEOUT = saved
    check("afconvert stops at its time limit and says so in plain words", a is None and "took too long" in how, how)
    a, how = sound.decode(wav, rate=8000)
    check("and with the usual limit it reads the sound", a is not None and how == "afconvert" and len(a) > 70000, how)

    # nothing left running
    check("no video program of this test is still running", not kids(os.getpid()))
    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed, {RESULTS['SKIP']} skipped.")
    if RESULTS["FAIL"]:
        print("Kept for a look:", work)
        return 1
    if "--work" not in sys.argv:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
