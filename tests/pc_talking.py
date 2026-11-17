#!/usr/bin/env python3
"""Talking reels on a PC (and on a Mac told to answer as one): turning talking into words is a named gap there,
so Edit my video answers with the PC line at once and makes nothing.

    python3 tests/pc_talking.py

On a Mac this sets ASSISTANT_NO_AVFOUNDATION=1 (video.py's switch), so the Mac answers the way a PC does. No clip
is made on either computer: the one video is the tiny tests/fixtures/loud-tone-3s.mp4, copied into a pretend
shoot's Talking folder and only ever read by its header. STUDIO_HOME is a scratch folder; the real app is never
built or started (TALKING_NO_REAL=1). Starts no server.

Every line says PASS (or SKIP). Python 3.9, standard library only, a Mac or a PC.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "the-engine" / "skills"
SCRIPTS = SKILLS / "studio-manager" / "scripts"
REEL = SKILLS / "assistant-make-a-reel" / "scripts"
CLIP = ROOT / "tests" / "fixtures" / "loud-tone-3s.mp4"
SHOOT = "2026-09-23 Hannah & Zoë's beach"
fails = 0

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

TMP = Path(tempfile.mkdtemp(prefix="pc-talking-")).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
KIT = HOME / "Your Content" / SHOOT
os.environ["STUDIO_HOME"] = str(STUDIO)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["ASSISTANT_NO_AVFOUNDATION"] = "1"
os.environ["TALKING_NO_REAL"] = "1"
for k in ("TALKING_TRANSCRIBER", "TALKING_PRETEND"):
    os.environ.pop(k, None)

REAL = Path.home() / (".stu" + "dio")


def real_listing():
    try:
        return sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in REAL.iterdir())
    except OSError:
        return None


REAL_BEFORE = real_listing()


def check(name, cond, got=None):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond or got is None else f"\n        got: {got!r}"), flush=True)
    fails += 0 if cond else 1


def tree(root):
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*"))


try:
    STUDIO.mkdir(parents=True)
    (STUDIO / "studio.json").write_text(json.dumps({"posts": {"home": str(HOME)}}), encoding="utf-8")
    (KIT / ".kit").mkdir(parents=True)
    (KIT / "Photos").mkdir()
    (KIT / "Talking").mkdir()
    (KIT / ".kit" / "kit.json").write_text(json.dumps({"name": "Hannah & Zoë's beach"}), encoding="utf-8")
    (KIT / ".kit" / "sheet.json").write_text(json.dumps({"photos": [{"n": 1, "file": "IMG_0001.jpg"}]}), encoding="utf-8")
    shutil.copyfile(CLIP, KIT / "Talking" / "talk.mp4")

    sys.path.insert(0, str(SCRIPTS))
    sys.path.insert(0, str(REEL))
    import this_computer      # noqa: E402
    import talking_rec as TR  # noqa: E402
    import transcribe as T    # noqa: E402
    import sound              # noqa: E402

    check("this computer answers as a PC", T.as_pc())
    tr = T.pick(TR.TALK_HOME)
    check("picked by itself, the transcriber is nobody, and its reason is \"pc\"", tr.name == "none" and tr.why() == "pc", (tr.name,))
    check("the Mac's own Speech Recognition says it is not available here", T.MacSpeech(TR.TALK_HOME).available() is False)
    os.environ["TALKING_TRANSCRIBER"] = "mac-speech"
    try:
        T.pick(TR.TALK_HOME).setup(time.time() + 5, None)
        check("even asked for by name, the Mac's own stops with the PC state and builds nothing", False)
    except T.TalkProblem as e:
        check("even asked for by name, the Mac's own stops with the PC state and builds nothing", e.state == "pc" and not TR.TALK_HOME.exists())
    os.environ.pop("TALKING_TRANSCRIBER")

    before_kit, before_studio = tree(KIT), tree(STUDIO)
    t0 = time.time()
    code, ans = TR.start(KIT, "talk.mp4")
    took = time.time() - t0
    check("Edit my video answers the PC line at once", ans == {"ok": False, "why": "pc", "words": this_computer.NO_TALKING_PC} and took < 2, (code, ans, took))
    check("the PC line is the plan's, and says what does work here",
          this_computer.NO_TALKING_PC == "Talking reels aren't on a PC yet: turning your talking into words needs a part only a Mac has today. "
                                         "Your photo reel, carousel and stories all work here.")
    time.sleep(0.5)
    check("...and makes nothing: no record, no job, no small copy, no scratch", tree(KIT) == before_kit and tree(STUDIO) == before_studio
          and not TR.job_running(KIT), (tree(KIT), tree(STUDIO)))
    code, ans = TR.start(KIT, "not-there.mp4")
    check("the PC line comes before anything else is looked at", ans.get("why") == "pc")

    st = TR.state_for_page(KIT)
    check("the page's state still opens: the video is listed, nothing is working, no script",
          st.get("ok") and [v["name"] for v in st["videos"]] == ["talk.mp4"] and st["working"] is False and st["rec"]["words"] == [], st)
    check("no make without a script", TR.can_make(KIT)[0] is False)

    env = dict(os.environ)
    r = subprocess.run([sys.executable, str(SCRIPTS / "talking_rec.py"), "setup", "--check"], capture_output=True, text=True, encoding="utf-8", env=env)
    check("setup --check says it is not possible here, with the PC line, and no Python error",
          r.returncode == 1 and this_computer.NO_TALKING_PC in r.stdout and "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(SCRIPTS / "talking_rec.py"), "setup"], capture_output=True, text=True, encoding="utf-8", env=env)
    check("setup itself says the same and sets nothing up", r.returncode == 1 and this_computer.NO_TALKING_PC in r.stdout and not TR.TALK_HOME.exists(), r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(SCRIPTS / "talking_rec.py"), "status", SHOOT], capture_output=True, text=True, encoding="utf-8", env=env)
    check("the chat's status command still works here", r.returncode == 0 and "talk.mp4" in r.stdout, r.stdout + r.stderr)

    # Open CapCut (v27) on a PC: the talking page's route goes through posting_queue.open_capcut, whose PC words
    # name this PC and the Start menu; they pass through whole. Her "this Mac" line is a Mac's only.
    import talking_page as tp
    import posting_queue
    TR.note_made(KIT, "Hannah talking reel")
    real_open, real_mac, real_win = posting_queue.open_capcut, this_computer.MAC, this_computer.WINDOWS
    answers = {}
    try:
        this_computer.MAC, this_computer.WINDOWS = False, True
        for name, line in (("cant", "I couldn't open CapCut on this PC. Open it from the Start menu, then click “Hannah talking reel” in its project list (near the top, newest first). CapCut is free from capcut.com."),
                           ("missing", "CapCut doesn't seem to be installed on this PC. It's free from capcut.com."),
                           ("slow", "CapCut is taking a while to start on this PC. Give it a moment, then click “Hannah talking reel” in its project list (near the top, newest first).")):
            posting_queue.open_capcut = (lambda l: lambda rec, ok_words=None, button="Open in CapCut": (False, l))(line)
            answers[name] = (line, tp.open_capcut_for_page({"kit": SHOOT}))
        posting_queue.open_capcut = lambda rec, ok_words=None, button="Open in CapCut": (True, ok_words)
        answers["ok"] = tp.open_capcut_for_page({"kit": SHOOT})
    finally:
        posting_queue.open_capcut, this_computer.MAC, this_computer.WINDOWS = real_open, real_mac, real_win
    check("Open CapCut on a PC: posting_queue's own words pass through whole (this PC, the Start menu), never her Mac line, never Finder or Applications",
          all(ans == (200, {"ok": False, "words": line}) for line, ans in answers.values() if isinstance(ans, tuple) and line)
          and all(not any(x in line for x in ("Mac", "Finder", "Applications")) for line, _a in (v for k, v in answers.items() if k != "ok")), answers)
    check("...a PC with no CapCut keeps posting_queue's PC line (her \"this Mac\" line is said on a Mac only)",
          answers["missing"][1][1]["words"] == "CapCut doesn't seem to be installed on this PC. It's free from capcut.com.", answers["missing"])
    check("...and when it opened, her line is the one said", answers["ok"] == (200, {"ok": True, "words": tp.WORDS["capcut_opening_say"]}), answers["ok"])
    check("the kit's record now notes the make, under the reel being worked on", TR.last_made(KIT) == "Hannah talking reel")

    # + Add more photos (v27) on a PC: the button's title and her two Finder lines read File Explorer (reel_page.pc_words,
    # as every Finder line of this page does); her "plugged in" line names no app. On a Mac the PC is pretended here
    # (WINDOWS and the files app's name); a real PC runs it as it is.
    real_win, real_app = this_computer.WINDOWS, this_computer.FILES_APP
    try:
        this_computer.WINDOWS, this_computer.FILES_APP = True, "File Explorer"
        pw = tp.page_words()
    finally:
        this_computer.WINDOWS, this_computer.FILES_APP = real_win, real_app
    pc_lines = {k: pw[k] for k in ("add_photos_title", "add_photos_opening", "add_photos_open")}
    check("+ Add more photos on a PC: the title and her two Finder lines read File Explorer, never Finder (her words otherwise)",
          all("File Explorer" in v and "Finder" not in v and v == tp.WORDS[k].replace("Finder", "File Explorer") for k, v in pc_lines.items())
          and pw["add_photos_cant"] == tp.WORDS["add_photos_cant"] == "Could not open the folder. Is the photo drive plugged in?"
          and pw["add_photos"] == "+ Add more photos", pc_lines)

    if not this_computer.MAC:
        got = sound.speech_wav(str(KIT / "Talking" / "talk.mp4"), TMP / "speech.wav")
        check("off a Mac the talking's sound file is not made, in plain words", got[0] is None and not (TMP / "speech.wav").exists() and "Mac" in got[1], got)
        check("a job started by hand on a PC stops with the PC line too",
              TR.line_for(T.Nobody(TR.TALK_HOME).why()) == this_computer.NO_TALKING_PC)
    else:
        print("SKIP  off a Mac the talking's sound file is not made   [this is a Mac: afconvert is here; GitHub's Windows machine runs it]")
    check("the real Assistant folder on this computer was not touched", real_listing() == REAL_BEFORE)
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    check(f"the test ran to its end ({e.__class__.__name__}: {e})", False)

if fails:
    print(f"\n{fails} FAILED   (scratch folder kept: {TMP})")
    sys.exit(1)
shutil.rmtree(TMP, ignore_errors=True)
print("\nALL PASS")
