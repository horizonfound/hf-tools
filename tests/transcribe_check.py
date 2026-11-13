#!/usr/bin/env python3
"""Turning a talking video into words (Nicole's handoff v23, built our way): the transcriber interface
(assistant-make-a-reel/scripts/transcribe.py), the sound it listens to (sound.speech_wav), and the job that
does it all (studio-manager/scripts/talking_rec.py: start, job, settle, setup).

    python3 tests/guard.py 800 python3 tests/transcribe_check.py [--work <scratch folder>] [--only <part>]

Run it under the memory guard, ONE video test at a time (it makes and reads video). Parts: rules (no video at
all), sound, job, timing. Without --only, all of them.

THE REAL APP IS NEVER BUILT AND NEVER STARTED HERE, and macOS is never given a reason to ask anything: every
job runs with the pretend transcriber (TALKING_TRANSCRIBER=pretend), TALKING_NO_REAL=1 makes the real builder and
starter refuse outright, and the Mac's own Speech Recognition class (MacSpeech) is only ever driven with a
pretend builder and a pretend "app" (a small Python script that behaves as the app is written to).

The clips are made here with the Mac's own AVFoundation (tests/video_check.py's maker): 6 s, 640 x 360, H.264;
one stored sideways (as a phone held upright), one with no sound, one with clicks at known times. Never a
client's, never HEVC, never 4K. STUDIO_HOME is the scratch folder, so no lock or file lands in the real one
(listed before and after). The one server it starts (to ask for the small copy in pieces) is on port 9610 and is
stopped at the end.

Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is kept then.
Python 3.9, standard library only.
"""
import contextlib
import hashlib
import io
import http.server
import json
import math
import os
import plistlib
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "the-engine" / "skills"
SCRIPTS = SKILLS / "studio-manager" / "scripts"
REEL = SKILLS / "assistant-make-a-reel" / "scripts"
HERS23 = ROOT.parent / "hf-tools" / "reference-private" / "nicole-handoff-v23-2026-11-11" / "Carousel designer and reel picker"
HERS24 = ROOT.parent / "hf-tools" / "reference-private" / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker"
if not HERS23.is_dir():
    HERS23 = ROOT / "reference-private" / "nicole-handoff-v23-2026-11-11" / "Carousel designer and reel picker"
    HERS24 = ROOT / "reference-private" / "nicole-handoff-v24-2026-11-11" / "Carousel designer and reel picker"
PORT = 9610
MAC = sys.platform == "darwin"
SHOOT = "2026-09-23 Hannah & Zoë's beach"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
if "--work" in sys.argv:
    TMP = Path(sys.argv[sys.argv.index("--work") + 1]).resolve()
    TMP.mkdir(parents=True, exist_ok=True)
    TMP = Path(tempfile.mkdtemp(prefix="transcribe-check-", dir=str(TMP))).resolve()
else:
    TMP = Path(tempfile.mkdtemp(prefix="transcribe-check-", dir="/private/tmp" if MAC else None)).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
CONTENT = HOME / "Your Content"
KIT = CONTENT / SHOOT
TALK_HOME = STUDIO / "talking"
PRETEND = TMP / "pretend.json"
SAW = TMP / "saw.json"
os.environ["STUDIO_HOME"] = str(STUDIO)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["TALKING_NO_REAL"] = "1"            # the real app can be neither built nor started, whatever happens
os.environ["TALKING_TRANSCRIBER"] = "pretend"
os.environ["TALKING_PRETEND"] = str(PRETEND)
os.environ["REMINDERS_BACKEND"] = "none"
for k in ("ASSISTANT_NO_AVFOUNDATION", "ASSISTANT_NO_AFCONVERT", "ASSISTANT_TEST_TALK_LIMITS"):
    os.environ.pop(k, None)

REAL = Path.home() / (".stu" + "dio")          # only ever listed, to prove this test leaves it alone


def real_listing():
    try:
        return sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in REAL.iterdir())
    except OSError:
        return None


REAL_BEFORE = real_listing()
RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(what, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:600]}]" if detail != "" and not ok else ""), flush=True)
    return ok


def skip(what, why):
    RESULTS["SKIP"] += 1
    print(f"SKIP  {what}   [{why}]", flush=True)


def part(name):
    return not ONLY or ONLY == name


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wait_for(cond, seconds=60, every=0.1):
    end = time.time() + seconds
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(every)
    return cond()


STUDIO.mkdir(parents=True)
(STUDIO / "studio.json").write_text(json.dumps({"posts": {"home": str(HOME)}}), encoding="utf-8")
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REEL))
import this_computer      # noqa: E402
import arrange            # noqa: E402
import reel_page          # noqa: E402
import talking_rec as TR  # noqa: E402
import transcribe as T    # noqa: E402
import sound              # noqa: E402
import video              # noqa: E402

SAID = "OK so um we were at the beach. And when when the kids ran in it was awesome.".split()
WORDS = [{"w": w, "start": i * 0.3 + 0.1004, "end": i * 0.3 + 0.3449, "conf": 0.912} for i, w in enumerate(SAID)]
TIDY = [{"w": w, "start": round(i * 0.3 + 0.1004, 3), "end": round(i * 0.3 + 0.3449, 3), "conf": 0.91} for i, w in enumerate(SAID)]


def pretend(**spec):
    spec.setdefault("words", WORDS)
    PRETEND.write_text(json.dumps(spec), encoding="utf-8")


def make_kit(folder, photos=6):
    k = CONTENT / folder
    (k / ".kit").mkdir(parents=True)
    (k / "Photos").mkdir()
    (k / "Talking").mkdir()
    (k / ".kit" / "kit.json").write_text(json.dumps({"name": folder.split(" ", 1)[1]}), encoding="utf-8")
    (k / ".kit" / "sheet.json").write_text(json.dumps({"photos": [{"n": i, "file": f"IMG_{i:04d}.jpg"} for i in range(1, photos + 1)]}), encoding="utf-8")
    return k


def rec_of(kit):
    return json.loads((kit / ".kit" / "talking.json").read_text(encoding="utf-8"))


def job_of(kit):
    return TR.read_job(kit) or {}


def wait_done(kit, seconds=90):
    """Until no job is at work on this kit and its record no longer says working."""
    def over():
        st = TR.state_for_page(kit)
        return st if (st.get("ok") and not st["working"] and st["rec"].get("status") != "working") else None
    return wait_for(over, seconds)


# ====================================================================== rules: no video, nothing made but text

def part_rules():
    src = (REEL / "transcribe.py").read_text(encoding="utf-8")
    rec_src = (SCRIPTS / "talking_rec.py").read_text(encoding="utf-8")
    swift = (REEL / "transcriber" / "transcribe.swift").read_text(encoding="utf-8")

    check("the test's own Assistant folder is the scratch one", Path(arrange.HOME) == STUDIO and TR.TALK_HOME == TALK_HOME, str(TR.TALK_HOME))

    # ---- picking a transcriber
    check("TALKING_TRANSCRIBER=pretend picks the pretend one", T.pick(TALK_HOME).name == "pretend")
    os.environ["TALKING_TRANSCRIBER"] = "none"
    check("=none picks nobody", T.pick(TALK_HOME).name == "none")
    os.environ["TALKING_TRANSCRIBER"] = "mac-speech"
    check("=mac-speech picks the Mac's own", T.pick(TALK_HOME).name == "mac-speech")
    os.environ["TALKING_TRANSCRIBER"] = "whisper-not-there"
    check("a name nobody registered picks nobody (never a guess)", T.pick(TALK_HOME).name == "none")
    os.environ.pop("TALKING_TRANSCRIBER")
    auto = T.pick(TALK_HOME).name
    check("picked by itself it is never the pretend one", auto in ("mac-speech", "none"), auto)
    if MAC:
        check("on this Mac, by itself: the Mac's own when macOS is 13 or newer, else nobody",
              auto == ("mac-speech" if T.macos() >= 13 else "none"), (auto, T.macos()))
    os.environ["ASSISTANT_NO_AVFOUNDATION"] = "1"
    nb = T.pick(TALK_HOME)
    check("a Mac told to answer as a PC: nobody, and its reason is \"pc\"", nb.name == "none" and nb.why() == "pc", (nb.name,))
    for step in ("setup", "run"):
        try:
            getattr(nb, step)(*( (time.time() + 5,) if step == "setup" else ("x.wav", "en-US", time.time() + 5)))
            check(f"nobody's {step} stops with the PC state", False)
        except T.TalkProblem as e:
            check(f"nobody's {step} stops with the PC state", e.state == "pc" and e.words == "")
    os.environ.pop("ASSISTANT_NO_AVFOUNDATION")
    os.environ["TALKING_TRANSCRIBER"] = "pretend"
    real_macos = T.macos
    T.macos = lambda: 12
    try:
        check("MacSpeech says no on a Mac older than macOS 13, before anything is built",
              T.MacSpeech(TALK_HOME).available() is False and (not MAC or T.Nobody(TALK_HOME).why() == "old_mac"))
    finally:
        T.macos = real_macos

    # ---- words as the record keeps them
    got = T.tidy([{"w": "Hi", "start": 0.12349, "end": 0.5551, "conf": 0.987}, {"w": "  ", "start": 1, "end": 2},
                  {"w": "there", "start": "1.5", "end": 2}, {"w": "x", "start": None, "end": 2}, "junk", {"start": 1, "end": 2},
                  {"w": "nan", "start": float("nan"), "end": 1}])
    check("words: times rounded to 3 places, confidence to 2, empty and garbled ones dropped (never a crash)",
          got == [{"w": "Hi", "start": 0.123, "end": 0.555, "conf": 0.99}, {"w": "there", "start": 1.5, "end": 2.0, "conf": 1.0}], got)
    check("words: not a list gives none", T.tidy(None) == [] and T.tidy({"w": 1}) == [])

    # ---- the app's description
    pl = plistlib.loads((REEL / "transcriber" / "Info.plist").read_bytes())
    check("the app's description: her names, no Dock icon, macOS 13, and her sentence word for word",
          pl.get("CFBundleIdentifier") == "found.horizon.assistant.transcriber" and pl.get("CFBundleDisplayName") == "The Assistant"
          and pl.get("CFBundleName") == "Assistant Transcriber" and pl.get("LSUIElement") is True
          and pl.get("LSMinimumSystemVersion") == "13.0" and pl.get("CFBundleExecutable") == T.EXECUTABLE
          and pl.get("NSSpeechRecognitionUsageDescription") == "So your talking video turns into a script you can edit.", pl)
    hers_pl = HERS23 / "transcriber" / "Info.plist"
    if hers_pl.is_file():
        check("the app's description holds exactly her keys and values", plistlib.loads(hers_pl.read_bytes()) == pl)
    else:
        skip("the app's description against hers", "her v23 folder is not beside the repo")

    # ---- the Swift source: her rules, spelled out (read as text; it is never built here)
    flat = re.sub(r"\s+", " ", swift)
    check("swift: punctuation is on (the sentences are found by . ? !)", "req.addsPunctuation = true" in flat)
    check("swift: partial results on (a long recording comes back in pieces)", "req.shouldReportPartialResults = true" in flat)
    check("swift: a piece counts once it has words and EVERY word has a length",
          "!segs.isEmpty && segs.allSatisfy { $0.duration > 0 }" in flat and "filter { !$0.substring.isEmpty }" in flat)
    check("swift: a newer piece replaces every word held from its first word minus 0.01 s on",
          "all.removeAll { $0.start >= first.timestamp - 0.01 }" in flat)
    check("swift: it finishes on the final piece, or on an error with words held",
          "if r.isFinal { finish() }" in flat and "if all.isEmpty { fail(" in flat and "} else { finish() }" in flat)
    check("swift: never Apple's servers (refuses when this Mac can't do it by itself)",
          'guard rec.supportsOnDeviceRecognition else { fail("servers") }' in flat and "req.requiresOnDeviceRecognition = true" in flat)
    check("the page's note about the box's \"sent to Apple\" sentence stands only while the Swift holds both by-itself lines, and the servers line is still there to back it",
          'guard rec.supportsOnDeviceRecognition else { fail("servers") }' in flat and "req.requiresOnDeviceRecognition = true" in flat
          and "I only ask your Mac to do it by itself, and I stop if it can't." in TR.APPLE_NOTE and "servers" in TR.OUR_JOB_WORDS
          and not re.search(r"nothing leaves|never sent|not sent|isn't sent", TR.APPLE_NOTE))
    check("swift: \"can this Mac do it by itself?\" is asked before \"is it available?\" (a Mac that needs Apple's servers, offline, says servers)",
          0 < flat.find("guard rec.supportsOnDeviceRecognition else") < flat.find("guard rec.isAvailable else"))
    check("swift: times rounded to 3 places, confidence to 2", "(x * 1000).rounded() / 1000" in flat and "($0.conf * 100).rounded() / 100" in flat)
    check("swift: the answer is written whole, then given its name", 'let part = path + ".part"' in flat and "rename(part, path)" in flat)
    check("swift: it stops by itself when the alive file goes stale or the deadline passes",
          '> 12 { task?.cancel(); fail("stopped") }' in flat and '> deadline { task?.cancel(); fail("deadline") }' in flat)
    check("swift: it says when macOS is about to ask, with its own process number",
          'state("asking")' in flat and "processIdentifier" in flat and ".notDetermined" in flat)
    check("swift: it answers with codes, never sentences (nothing printed, no sentence in an answer)",
          "print(" not in swift and not re.search(r'fail\("[^"]*\s[^"]*"', swift))
    codes = set(re.findall(r'fail\("([a-z_]+)"', swift)) | {"args"}
    check("every code the app can answer with has a meaning here", codes <= set(T.APP_CODES), sorted(codes - set(T.APP_CODES)))
    check("every state a transcriber can stop with has a line for the page",
          all(s in TR.JOB_WORDS or s in TR.OUR_JOB_WORDS for s in T.STATES) and set(T.APP_CODES.values()) <= set(T.STATES),
          [s for s in T.STATES if s not in TR.JOB_WORDS and s not in TR.OUR_JOB_WORDS])
    hers_sw = HERS23 / "transcriber" / "transcribe.swift"
    if hers_sw.is_file():
        h = re.sub(r"\s+", " ", hers_sw.read_text(encoding="utf-8"))
        check("her piece-keeping lines are in hers as we read them (so ours is checked against the real thing)",
              "segs.allSatisfy { $0.duration > 0 }" in h and "first.timestamp - 0.01" in h and "req.shouldReportPartialResults = true" in h
              and "addsPunctuation = true" in h and "if r.isFinal { finish() }" in h)
    else:
        skip("her Swift rules against her file", "her v23 folder is not beside the repo")

    # ---- never the bare compiler; every program by its full path; the real thing refuses in a test
    for bare in (["swiftc", "-O", "x.swift"], ["codesign", "x"], ["open", "x.app"], []):
        try:
            T._tool(bare, 5)
            check(f"a program called by a bare name is refused before it runs: {bare[:1]}", False)
        except ValueError:
            check(f"a program called by a bare name is refused before it runs: {bare[:1]}", True)
        except Exception as e:  # noqa: BLE001
            check(f"a program called by a bare name is refused before it runs: {bare[:1]}", False, repr(e))
    code_lines = [ln.split("  #", 1)[0] for ln in src.splitlines()]
    heads = [ln for ln in code_lines if re.search(r"""\[\s*["'](swiftc|codesign|xcode-select|xcrun|open|plutil|tccutil)["']""", ln)]
    check("transcribe.py never names one of Apple's tools without its full path", heads == [], heads)
    uses = [i for i, ln in enumerate(code_lines, 1) if re.search(r"subprocess\.(run|Popen|call|check_\w+)\(", ln)]
    owners = []
    for n in uses:
        fn = next((m.group(1) for ln in reversed(src.splitlines()[:n]) for m in [re.match(r"def (\w+)\(", ln)] if m), None)
        owners.append(fn)
    check("transcribe.py starts a program in two places only: _tool (full paths) and real_starter (the Mac's open)",
          sorted(set(owners)) == ["_tool", "real_starter"], owners)
    started = re.findall(r"popen_detached\(\[sys\.executable, str\(HERE / \"talking_rec\.py\"\), \"([a-z-]+)\"", rec_src)
    check("talking_rec.py starts no program itself but its own two jobs (a video into words; stage D's Make it in CapCut, "
          "whose maker is run through the reel page's own time-limited runner)",
          len(re.findall(r"subprocess\.(run|Popen|call)\(", rec_src)) == 0 and rec_src.count("popen_detached(") == 2
          and sorted(started) == ["job", "make-job"] and rec_src.count("_run_bounded(") == 1, started)
    for what, fn in (("the real builder", lambda: T.real_builder(TMP / "nope", {"compiler": "/usr/bin/true", "sdk": "/"})),
                     ("the real starter", lambda: T.real_starter(["/usr/bin/true"])),
                     ("any of Apple's tools", lambda: T._tool(["/usr/bin/true"], 5))):
        try:
            fn()
            check(f"in a test, {what} refuses outright (TALKING_NO_REAL)", False)
        except RuntimeError as e:
            check(f"in a test, {what} refuses outright (TALKING_NO_REAL)", "TALKING_NO_REAL" in str(e))
    check("the refused builder left nothing behind", not (TMP / "nope").exists())
    os.environ.pop("TALKING_NO_REAL")
    try:
        try:
            T._never_real("building the transcriber app")
            belt = "allowed"
        except RuntimeError as e:
            belt = str(e)
        check("a second belt: with the Assistant's own folder moved to a scratch one (every test), the real app is refused even by a test that forgot TALKING_NO_REAL",
              "STUDIO_HOME" in belt and "TALKING_REAL_OK" in belt, belt)
        os.environ["TALKING_REAL_OK"] = "1"
        try:
            T._never_real("x")
            check("...and only TALKING_REAL_OK=1 (the hand step) lets it through there", True)
        except RuntimeError as e:
            check("...and only TALKING_REAL_OK=1 (the hand step) lets it through there", False, e)
    finally:
        os.environ.pop("TALKING_REAL_OK", None)
        os.environ["TALKING_NO_REAL"] = "1"
    e2 = {k: v for k, v in os.environ.items() if k != "TALKING_NO_REAL"}
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "guard.py"), "400", sys.executable, "-c",
                        "import os; print('NO_REAL=' + str(os.environ.get('TALKING_NO_REAL')))"], capture_output=True, text=True, env=e2)
    check("anything run under the memory guard is told the real app may not be built or started", "NO_REAL=1" in r.stdout, r.stdout + r.stderr)

    # ---- how the app is started
    cmd = T.app_command(TALK_HOME / T.APP_NAME, ["a.wav", "en-US", "w.json", "s.json", "alive", "123"])
    check("the app is started only through the Mac's own open -n -g -W <app> --args ...",
          cmd[:6] == ["/usr/bin/open", "-n", "-g", "-W", str(TALK_HOME / T.APP_NAME), "--args"] and cmd[6:] == ["a.wav", "en-US", "w.json", "s.json", "alive", "123"], cmd)
    check("the file inside the app is never in that command", not any("Contents" in c or c.endswith("/" + T.EXECUTABLE) for c in cmd))
    check("a path on a plugged-in drive is known as one", T._on_a_drive("/Volumes/Big Kahuna/x.wav") and not T._on_a_drive(str(TALK_HOME / "x.wav")))

    # ---- built.json, with a pretend builder (nothing is compiled, signed or started)
    home = TMP / "build-home"
    built = []
    tools = lambda: {"dev": "/pretend", "compiler": "/pretend/compiler", "sdk": "/pretend/sdk", "sdk_version": "26.0"}  # noqa: E731

    def builder(scratch, t, deadline=None):
        app = Path(scratch) / T.APP_NAME
        (app / "Contents" / "MacOS").mkdir(parents=True)
        (app / "Contents" / "MacOS" / T.EXECUTABLE).write_text(f"pretend build {len(built) + 1}", encoding="utf-8")
        built.append(str(scratch))
        return app

    ms = T.MacSpeech(home, builder=builder, tools=tools)
    said = []
    if MAC and T.macos() >= 13:
        check("nothing built yet: it needs building", T.needs_build(home) and ms.needs_setup())
        ms.setup(time.time() + 30, said.append)
        exe = home / T.APP_NAME / "Contents" / "MacOS" / T.EXECUTABLE
        b = T.read_built(home)
        check("the first setup says so, builds once, puts the app in place and writes built.json",
              said == ["setup"] and len(built) == 1 and exe.read_text(encoding="utf-8") == "pretend build 1"
              and b.get("source") == T.source_mark() and b.get("chip") and b.get("built"), (said, built, b))
        check("the scratch build folder is gone, and it was inside the Assistant's own folder",
              not Path(built[0]).exists() and Path(built[0]).parent == home)
        ms.setup(time.time() + 30, said.append)
        check("source unchanged: not built again, nothing said (a rebuild is a new app to macOS)",
              len(built) == 1 and said == ["setup"] and not T.needs_build(home))
        real_src, real_pl = T.SOURCE, T.PLIST
        try:
            T.SOURCE = TMP / "changed.swift"
            T.SOURCE.write_text(swift + "\n// one more line\n", encoding="utf-8")
            check("the Swift source changed: it needs building again", T.needs_build(home))
            ms.setup(time.time() + 30, said.append)
            older = sorted((home / "older").glob("*/" + T.APP_NAME + "/Contents/MacOS/" + T.EXECUTABLE))
            check("rebuilt, and the older app is set aside in older/, never deleted",
                  len(built) == 2 and exe.read_text(encoding="utf-8") == "pretend build 2" and len(older) == 1
                  and older[0].read_text(encoding="utf-8") == "pretend build 1" and not T.needs_build(home), older)
            T.SOURCE = real_src
            check("the source back as it was: built.json no longer matches, so it needs building", T.needs_build(home))
            T.SOURCE, T.PLIST = TMP / "changed.swift", TMP / "changed.plist"
            T.PLIST.write_bytes(real_pl.read_bytes().replace(b"So your talking video", b"So that your talking video"))
            check("the app's description text changed: it needs building again", T.needs_build(home))
        finally:
            T.SOURCE, T.PLIST = real_src, real_pl
        ms.setup(time.time() + 30, said.append)
        check("a second older app is set aside beside the first", len(list((home / "older").iterdir())) == 2 and len(built) == 3)
        check("built for another chip: it needs building", T.needs_build(home, chip="some-other-chip") and not T.needs_build(home))
        (home / T.BUILT).unlink()
        check("built.json gone: it needs building (never trusted without it)", T.needs_build(home))

        def no_tools():
            raise T.TalkProblem("no_tools", detail="pretend: no tools")
        try:
            T.MacSpeech(home, builder=builder, tools=no_tools).setup(time.time() + 30, None)
            check("Apple's tools missing: setup stops with that state and builds nothing", False)
        except T.TalkProblem as e:
            check("Apple's tools missing: setup stops with that state and builds nothing", e.state == "no_tools" and len(built) == 3)
        check("a failed build's reason: licence, tools older than macOS, or plain failed",
              T._why_not_built("You have not agreed to the Xcode license agreements.", {}) == "licence"
              and T._why_not_built("error: this SDK is not supported by the compiler", {"sdk_version": "99.0"}) == "old_tools"
              and T._why_not_built("error: something else", {"sdk_version": "99.0"}) == "setup_failed"
              and T._why_not_built("error: compiled module was created by a newer version", {}) == "old_tools")
        real_macos2 = T.macos
        T.macos = lambda: 27
        try:
            check("an SDK numbered below the macOS (27.2 with 26.5: normal, and it builds) is never by itself \"tools older than macOS\"",
                  T._why_not_built("error: x", {"sdk_version": "26.5"}) == "setup_failed"
                  and T._why_not_built("error: x", {"sdk_version": "1.0"}) == "setup_failed"
                  and T._why_not_built("error: this SDK is not supported by the compiler", {"sdk_version": "26.5"}) == "old_tools")
        finally:
            T.macos = real_macos2

        # the setup's deadline reaches the build
        def slow(scratch, t, deadline=None):
            time.sleep(1.5)
            return builder(scratch, t, deadline)
        hd = TMP / "deadline-home"
        n_built = len(built)
        try:
            T.MacSpeech(hd, builder=slow, tools=tools).setup(time.time() + 0.5, None)
            check("a build that ends after the setup's deadline: too long, and it is not put in place", False)
        except T.TalkProblem as e:
            check("a build that ends after the setup's deadline: too long, and it is not put in place",
                  e.state == "too_long" and not (hd / T.APP_NAME).exists() and not (hd / T.BUILT).exists() and not list(hd.glob("build-*")), e)
        del built[n_built:]
        seen_deadline = []
        T.MacSpeech(hd, builder=lambda sc, t, deadline=None: (seen_deadline.append(deadline), builder(sc, t))[1], tools=tools).setup(1e12, None)
        check("the builder is handed the setup's own deadline", seen_deadline == [1e12], seen_deadline)
        del built[n_built:]
        try:
            T._time_left(240, time.time() - 1)
            gone_ok = False
        except T.TalkProblem as e:
            gone_ok = e.state == "too_long"
        check("each of the build's tools gets its own limit or what is left before the deadline, whichever is less; nothing left is too long",
              T._time_left(240, None) == 240 and 3 < T._time_left(240, time.time() + 5) <= 5 and T._time_left(60, time.time() + 500) == 60 and gone_ok)
        rb = src.split("def real_builder(")[1].split("\ndef ")[0]
        check("the real builder gives all three of its tools that time (the compiler, signing, the signature check)",
              rb.count("_tool(") == 3 and rb.count("_time_left(") == 3 and "BUILD_LIMIT)" not in rb.replace("_time_left(BUILD_LIMIT, deadline)", ""), rb.count("_time_left("))

        def failing(scratch, t, deadline=None):
            (Path(scratch) / "half").write_text("x", encoding="utf-8")
            raise T.TalkProblem("licence", detail="pretend")
        try:
            T.MacSpeech(home, builder=failing, tools=tools).setup(time.time() + 30, None)
            check("a build that fails leaves no scratch folder and no app in place", False)
        except T.TalkProblem as e:
            check("a build that fails leaves no scratch folder and no app in place",
                  e.state == "licence" and not list(home.glob("build-*")) and not (home / T.BUILT).exists())
        # two setups at once (the chat's `setup` while a job's first build runs): one build, nothing set aside
        n_built = len(built)

        def slowly(scratch, t, deadline=None):
            time.sleep(1.0)
            return builder(scratch, t, deadline)
        real_tr = TR.transcriber
        TR.transcriber = lambda: T.MacSpeech(TALK_HOME, builder=slowly, tools=tools)
        codes = []
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ts = [threading.Thread(target=lambda: codes.append(TR.cmd_setup())) for _ in range(2)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(60)
        finally:
            TR.transcriber = real_tr
        check("two setups at the same moment: ONE build, one app in place, nothing set aside in older/ (a second build is a new app to macOS)",
              codes == [0, 0] and len(built) - n_built == 1 and (TALK_HOME / T.APP_NAME).is_dir() and not (TALK_HOME / "older").exists(),
              (codes, len(built) - n_built, sorted(os.listdir(TALK_HOME))))
        del built[n_built:]
        shutil.rmtree(TALK_HOME / T.APP_NAME, ignore_errors=True)       # the test's own pretend app
        (TALK_HOME / T.BUILT).unlink()

        # a build stopped part way leaves its scratch folder: the next job (or setup) clears it, and only it
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        old = time.time() - 3600
        names = {"stale": f"build-{dead.pid}-abc123", "alive": f"build-{os.getpid()}-abc123", "young": f"build-{dead.pid}-def456",
                 "other": "build-notes", "odd": f"build-{dead.pid}-xyz"}
        for k, n in names.items():
            (TALK_HOME / n).mkdir(parents=True)
            (TALK_HOME / n / "half").write_text("x", encoding="utf-8")
            if k != "young":
                os.utime(TALK_HOME / n, (old, old))
        got = TR.clear_stale_builds()
        left = sorted(n for n in os.listdir(TALK_HOME) if n.startswith("build-"))
        check("a build folder whose process is gone, older than a build can take, is cleared; one still building, one just made, and any other name are left",
              got == [names["stale"]] and left == sorted(v for k, v in names.items() if k != "stale"), (got, left))
        for k, n in names.items():
            shutil.rmtree(TALK_HOME / n, ignore_errors=True)            # the test's own
        part_fake_app(home, builder, tools)
    else:
        skip("built.json with a pretend builder, and the app's start, wait and stop with a pretend app", "MacSpeech is for a Mac on macOS 13 or newer")

    # ---- the job's limits, as the plan states them
    lim = TR.limits(6)
    check("limits for a 6 s video: copy 120, sound 120, words 300, grace 30, the turn 900 apart",
          (lim["copy"], lim["sound"], lim["words"], lim["grace"], lim["turn"]) == (120, 120, 300, 30, video.TURN_WAIT), lim)
    lim = TR.limits(1800)
    check("limits for 30 minutes: copy 3 x, sound 1 x, words 4 x the length", (lim["copy"], lim["sound"], lim["words"]) == (5400, 1800, 7200), lim)
    check("the ceiling is the sum and a minute", lim["ceiling"] == lim["setup"] + lim["ask"] + 5400 + 1800 + 7200 + 30 + 60, lim)
    check("the Mac's question may wait five minutes", T.ASK_WAIT == 300)

    # ---- the facts that refuse a video before anything is made
    ok = {"has_audio": True, "length": 6.0}
    check("facts: a good video passes; no sound, over 30 minutes, unreadable and empty are each refused by name",
          TR.facts_problem(ok) is None and TR.facts_problem({"has_audio": False, "length": 6}) == "no_talking"
          and TR.facts_problem({"has_audio": True, "length": 1800.5}) == "over_30" and TR.facts_problem({"has_audio": True, "length": 1800}) is None
          and TR.facts_problem({"refused": "x"}) == "unreadable" and TR.facts_problem({"has_audio": True, "length": 0}) == "unreadable"
          and TR.facts_problem(None) == "unreadable")

    # ---- the words
    lines = dict(TR.JOB_WORDS, **{k: v[0] for k, v in TR.OUR_JOB_WORDS.items()})
    check("no line says Claude; none shows a path or a Python word",
          not any(re.search(r"Claude|Traceback|Error\b|/Users/|\.py\b|\.json\b", v) for v in lines.values()),
          [v for v in lines.values() if re.search(r"Claude|Traceback|Error\b|/Users/|\.py\b|\.json\b", v)])
    check("every line of ours has its reason beside it", all(isinstance(v, tuple) and len(v) == 2 and v[0] and v[1] for v in TR.OUR_JOB_WORDS.values()))
    check("the PC line is this_computer's own", TR.line_for("pc") == this_computer.NO_TALKING_PC and "PC" in this_computer.NO_TALKING_PC)
    check("a state nobody planned for gets the plain \"couldn't\" line, never its own name", TR.line_for("zzz") == TR.OUR_JOB_WORDS["failed"][0])
    core = HERS24 / "talking_core.py"
    if core.is_file():
        hers = core.read_text(encoding="utf-8")
        missing = [v for v in TR.JOB_WORDS.values() if v not in hers]
        check("her lines are hers, character for character (talking_core.py)", missing == [], missing)
        check("\"Turn your video into a script first.\" is hers (server.py)", TR.NO_SCRIPT_MAKE in (HERS24 / "server.py").read_text(encoding="utf-8"))
        ours_in_hers = [k for k, v in TR.OUR_JOB_WORDS.items() if v[0] in hers]
        check("no line called ours is really hers", ours_in_hers == [], ours_in_hers)
    else:
        skip("her lines against her file", "her v24 folder is not beside the repo")

    # ---- our way
    for f in (REEL / "transcribe.py", SCRIPTS / "talking_rec.py"):
        s = f.read_text(encoding="utf-8")
        check(f"{f.name}: no home spelled out (the computer's own disk is reached through arrange.HOME)",
              "expanduser" not in s and (".stu" + "dio") not in s and "Path.home" not in s)
    check("transcribe.py and the new sound code never reach for ffmpeg", "ffmpeg" not in src.lower()
          and "ffmpeg" not in (REEL / "sound.py").read_text(encoding="utf-8").split("def speech_wav(")[1].split("\n# -----")[0].replace("no ffmpeg, on purpose", ""))
    pc = (ROOT / "tools" / "check_pc.py").read_text(encoding="utf-8")
    check("the PC check knows Apple's tools: swiftc, codesign, xcode-select, xcrun, plutil, tccutil",
          all(f'("{t}",' in pc for t in ("swiftc", "codesign", "xcode-select", "xcrun", "plutil", "tccutil")))

    # ---- setup, as the assistant runs it
    def cli(*args, **env):
        e = dict(os.environ, **env)
        return subprocess.run([sys.executable, str(SCRIPTS / "talking_rec.py"), *args], capture_output=True, text=True, encoding="utf-8", env=e)
    pretend(needs_setup=True)
    r = cli("setup", "--check")
    check("setup --check says where it stands and sets nothing up", r.returncode == 0 and "pretend" in r.stdout and "Set up" not in r.stdout, r.stdout + r.stderr)
    r = cli("setup")
    check("setup does the setup and says the Mac will ask once", r.returncode == 0 and "Set up." in r.stdout and "ask once" in r.stdout, r.stdout + r.stderr)
    pretend(needs_setup=True, setup="no_tools")
    r = cli("setup")
    check("setup with Apple's tools missing: STOP, our line, and never the install command without their yes",
          r.returncode == 2 and "STOP: " + TR.OUR_JOB_WORDS["no_tools"][0] in r.stdout and "only with their yes" in r.stdout
          and "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr)
    for st in ("setup_failed", "too_long", "a state nobody planned for"):
        pretend(needs_setup=True, setup=st)
        r = cli("setup")
        check(f"setup that can't finish ({st}): STOP, where the Mac's own words are, and never \"Tell your assistant: set up talking reels\" (the command it just ran)",
              r.returncode == 2 and "STOP: " in r.stdout and "Tell your assistant" not in r.stdout and "talking log" in r.stdout
              and "talking.log" in r.stdout and "don't send them round again" in r.stdout and "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr)
    pretend(needs_setup=True)
    TALK_HOME.mkdir(parents=True, exist_ok=True)
    with open(TALK_HOME / TR.TALK_TURN, "ab") as lf:
        this_computer.try_lock(lf)
        real_wait = TR.SETUP_TURN_WAIT
        TR.SETUP_TURN_WAIT = 0.5
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = TR.cmd_setup()
        finally:
            TR.SETUP_TURN_WAIT = real_wait
            this_computer.unlock(lf)
        check("setup while a talking job holds the computer's turn: it waits a moment, then says so and does nothing",
              rc == 3 and "STOP" in buf.getvalue() and "Set up." not in buf.getvalue(), (rc, buf.getvalue()))
    r = cli("setup", "--check", TALKING_TRANSCRIBER="none", ASSISTANT_NO_AVFOUNDATION="1")
    check("setup on a PC: not possible here, with the PC line", r.returncode == 1 and this_computer.NO_TALKING_PC in r.stdout, r.stdout + r.stderr)
    if MAC and T.macos() >= 13:
        r = cli("setup", "--check", TALKING_TRANSCRIBER="mac-speech")
        check("setup --check for the Mac's own: says not built yet, never asked, and builds nothing",
              r.returncode == 0 and "not built yet" in r.stdout and "never asked yet" in r.stdout and not (TALK_HOME / T.APP_NAME).exists(), r.stdout + r.stderr)
        r = cli("setup", TALKING_TRANSCRIBER="mac-speech")
        check("setup for the Mac's own, in a test: refused before any tool runs; no app, no build folder, plain words",
              r.returncode == 2 and "STOP: " in r.stdout and "Traceback" not in r.stdout + r.stderr
              and not (TALK_HOME / T.APP_NAME).exists() and not list(TALK_HOME.glob("build-*")), r.stdout + r.stderr)
    pretend()

    # ---- the job's last save (no video needed: the record and the words file only)
    KA, KB = "a" * 12, "b" * 12
    kv = make_kit("2026-11-01 Two videos")
    TR.put_words(kv, "a.mov", KA, WORDS, {"dur": 6.0})
    TR.change(kv, lambda rec: rec.update(cut=[[1, 2]]))
    TR.put_words(kv, "b.mov", KB, WORDS[:5], {"dur": 6.0})
    r0 = rec_of(kv)
    NEW = [dict(w, w=w["w"].upper()) for w in WORDS]
    TR.put_words(kv, "a.mov", KA, NEW, {"dur": 6.0}, switch=False)
    r1 = rec_of(kv)
    check("the job's save for a video they have since left: the record stays on the video they chose, untouched; the words are kept",
          r0.get("video") == "b.mov" and r1 == r0 and [w["w"] for w in TR.words_for(kv, "a.mov")["words"]] == [w["w"].upper() for w in WORDS], (r1.get("video"), r1.get("rev"), r0.get("rev")))
    back = TR.use_video(kv, "a.mov")
    check("...and coming back to that video finds its new script, ready, the edit made on the old words set aside in \"replaced\"",
          back.get("status") == "ready" and back["words"][0]["w"] == NEW[0]["w"] and not back.get("cut")
          and any(x.get("cut") == [[1, 2]] for x in back.get("replaced") or []), (back.get("status"), back.get("cut")))
    TR.change(kv, lambda rec: rec.update(cut=[[2, 3]]))
    TR.use_video(kv, "b.mov")
    TR.put_words(kv, "a.mov", KA, NEW, {"dur": 6.0}, again=True, switch=False)
    back = TR.use_video(kv, "a.mov")
    check("Edit my video again, finished after they left (the same words back): still on their video meanwhile, and the edit starts afresh when they return",
          not back.get("cut") and any(x.get("cut") == [[2, 3]] for x in back.get("replaced") or []) and back.get("status") == "ready", (back.get("cut"), back.get("replaced")))

    ks = make_kit("2026-11-02 Busy save")
    TR.change(ks, lambda rec: rec.update(video="t.mov", status="working", step="Turning your words into a script…"))
    real_change, n = TR.change, [0]

    def flaky(*a, **k):
        n[0] += 1
        if n[0] <= 2:
            raise TR.Busy(TR.BUSY)
        return real_change(*a, **k)
    TR.change, TR._UNTIL[0] = flaky, time.time() + 600
    try:
        try:
            TR._save_words(ks, "t.mov", KA, WORDS, {"dur": 6.0}, {"how": "pretend"}, False)
            err = None
        except TR.Busy as e:
            err = e
    finally:
        TR.change = real_change
    r = TR.load(ks)
    check("the record busy at the job's last save: it is tried again, and the finished words are not thrown away",
          err is None and n[0] == 3 and r.get("status") == "ready" and r.get("words") == TIDY and r.get("problem") == "", (err, n, r.get("status")))

    kl = make_kit("2026-11-03 Landed")
    TR.change(kl, lambda rec: rec.update(video="t.mov", status="working", step="Turning your words into a script…", cut=[[0, 1]]))
    TR.write_job(kl, {"id": "abcabcabcabc", "state": "problem", "video": "t.mov", "key": KA, "again": True, "t": time.time() - 9,
                      "t0": time.time() - 8, "pid": 0})

    def always_busy(*a, **k):
        raise TR.Busy(TR.BUSY)
    TR.change, TR._UNTIL[0] = always_busy, time.time() + 600
    real_tries = TR.SAVE_TRIES
    TR.SAVE_TRIES = 1
    try:
        try:
            TR._save_words(kl, "t.mov", KA, WORDS, {"dur": 6.0}, {"how": "pretend"}, True)
            err = None
        except TR.Busy as e:
            err = e
    finally:
        TR.change, TR.SAVE_TRIES = real_change, real_tries
    check("(the record stayed busy to the end: the words are in their file, the record still says working)",
          err is not None and rec_of(kl).get("status") == "working" and TR.words_for(kl, "t.mov"))
    changed = TR.settle(kl)
    r = TR.load(kl)
    check("...then the page's next look finishes that save: ready on the new script, no \"I was stopped\" line, the old edit kept in \"replaced\"",
          changed and r.get("status") == "ready" and r.get("problem") == "" and r.get("words") == TIDY and r.get("words_of")
          and not r.get("cut") and any(x.get("cut") == [[0, 1]] for x in r.get("replaced") or []), (changed, r.get("status"), r.get("problem"), r.get("cut")))
    ko = make_kit("2026-11-04 Old script")
    TR.put_words(ko, "t.mov", KA, WORDS, {"dur": 6.0})
    time.sleep(0.05)
    TR.change(ko, lambda rec: rec.update(status="working", step="x"))
    TR.write_job(ko, {"id": "abcabcabcabd", "state": "problem", "video": "t.mov", "key": KA, "again": True, "t": time.time(), "t0": time.time(), "pid": 0})
    TR.settle(ko)
    check("a job that died with only an OLDER script in the file is still told as stopped (never passed off as finished)",
          rec_of(ko).get("problem") == TR.OUR_JOB_WORDS["interrupted"][0], rec_of(ko).get("problem"))

    # ---- staying awake
    if MAC and os.path.exists("/usr/bin/caffeinate"):
        napper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        h = this_computer.awake_while(napper.pid)
        try:
            check("staying awake for as long as a process lives: the Mac's own caffeinate -i -w <its number>, started by its full path",
                  h is not None and h.args == ["/usr/bin/caffeinate", "-i", "-w", str(napper.pid)] and h.poll() is None, getattr(h, "args", None))
        finally:
            napper.kill()
            napper.wait()
        try:
            h.wait(timeout=10)
        except subprocess.TimeoutExpired:
            h.kill()
            check("...and it ends by itself when that process does", False)
        else:
            check("...and it ends by itself when that process does", True)
    else:
        skip("staying awake with the Mac's caffeinate", "a PC asks Windows instead (this_computer.keep_awake)")


FAKE_APP = r'''
import json, os, sys, time
wav, lang, answer, state, alive, deadline = sys.argv[1:7]
mode = os.environ.get("FAKE_APP_MODE", "ok")
mark = os.environ.get("FAKE_APP_MARK")
def put(d, p):
    open(p + ".part", "w").write(json.dumps(d)); os.rename(p + ".part", p)
def gone():
    try:
        return time.time() - os.stat(alive).st_mtime > 3
    except OSError:
        return True
def wait(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if gone() or time.time() > float(deadline):
            if mark: open(mark, "w").write("stopped by itself")
            sys.exit(1)
        time.sleep(0.1)
words = [{"w": "Hello.", "start": 0.1, "end": 0.5, "conf": 0.9}]
if mode.startswith("ask"):
    put({"state": "asking", "pid": os.getpid()}, state)
    wait(1.0 if mode == "ask_ok" else 120)
put({"state": "working", "pid": os.getpid()}, state)
if mode == "slow":
    wait(120)
if mode.startswith("err:"):
    put({"error": mode[4:], "detail": os.environ.get("FAKE_APP_DETAIL", "")}, answer); sys.exit(1)
if mode == "silent":
    sys.exit(0)
put({"ok": True, "words": words, "ondevice": True, "saw": [wav, lang]}, answer)
'''


def part_fake_app(home, builder, tools):
    """MacSpeech.run with a pretend app: a Python script that keeps the app's contract (its arguments, its state
    and answer files, stopping when the alive file goes stale)."""
    fake = TMP / "fake_app.py"
    fake.write_text(FAKE_APP, encoding="utf-8")
    started = []

    def starter(cmd):
        started.append(list(cmd))
        args = cmd[cmd.index("--args") + 1:]
        return subprocess.Popen([sys.executable, str(fake), *args], stdin=subprocess.DEVNULL)

    ms = T.MacSpeech(home, builder=builder, tools=tools, starter=starter)
    ms.setup(time.time() + 30, None)
    work = home / "work" / "aaaaaaaaaaaa"
    work.mkdir(parents=True)
    wav = work / "sound.wav"
    wav.write_bytes(b"RIFF")
    said = []

    def run(mode, deadline=30, **env):
        os.environ["FAKE_APP_MODE"] = mode
        for k, v in env.items():
            os.environ[k] = v
        said.clear()
        try:
            return ms.run(wav, "en-US", time.time() + deadline, said.append), None
        except T.TalkProblem as e:
            return None, e
        finally:
            for k in env:
                os.environ.pop(k, None)

    got, err = run("ok")
    check("pretend app: its words come back, tidied, with how and on-device",
          err is None and got == {"words": [{"w": "Hello.", "start": 0.1, "end": 0.5, "conf": 0.9}], "how": "mac-speech", "ondevice": True}, (got, err))
    c = started[-1]
    check("pretend app: it was handed the sound, the language, and three files beside the sound, all inside the Assistant's own folder",
          c[:6] == ["/usr/bin/open", "-n", "-g", "-W", str(home / T.APP_NAME), "--args"] and c[6] == str(wav) and c[7] == "en-US"
          and all(Path(x).parent == work for x in c[8:11]) and float(c[11]) > time.time(), c)
    check("pretend app: the file inside the app was never handed to anything", not any("Contents" in x for cmd in started for x in cmd))
    check("pretend app: what the Mac said about Speech Recognition is noted (allowed)", (T._read(home / T.PERMISSION) or {}).get("state") == "allowed")
    got, err = run("ask_ok")
    check("pretend app asking, then answered: the page is told it is asking, then that it is working", err is None and said == ["asking", "working"], (said, err))
    for code, state in (("denied", "refused"), ("restricted", "restricted"), ("unavailable", "dictation_off"), ("servers", "servers"),
                        ("no_words", "no_talking"), ("deadline", "too_long"), ("language", "failed"), ("failed", "failed"),
                        ("not_asked", "no_answer"), ("something_new", "failed")):
        got, err = run("err:" + code)
        check(f"pretend app answers \"{code}\": the state is {state}, with no sentence of its own", err is not None and err.state == state and err.words == "", err)
    check("what the Mac last said is noted for setup --check (here: asked, never answered)", (T._read(home / T.PERMISSION) or {}).get("state") == "no_answer")
    run("err:denied")
    check("...and a refusal is noted as one", (T._read(home / T.PERMISSION) or {}).get("state") == "refused")
    got, err = run("err:failed", FAKE_APP_DETAIL="kLSRErrorDomain 201: Siri and Dictation are disabled")
    check("pretend app fails saying Dictation is off: that state", err is not None and err.state == "dictation_off", err)
    for detail in ("kAFAssistantErrorDomain 1110: No speech detected", "kAFAssistantErrorDomain 1110: (null)", "No speech detected."):
        got, err = run("err:failed", FAKE_APP_DETAIL=detail)
        check(f"pretend app fails with the Mac's \"no speech\" error ({detail[:34]}): her \"I couldn't hear any talking\" state",
              err is not None and err.state == "no_talking" and TR.line_for(err.state) == "I couldn't hear any talking in that video.", err)
    got, err = run("err:failed", FAKE_APP_DETAIL="kAFAssistantErrorDomain 203: Retry")
    check("...and any other failure stays the plain \"couldn't\"", err is not None and err.state == "failed", err)
    got, err = run("silent")
    check("pretend app ends with no answer: plain failed, never a crash", err is not None and err.state == "failed", err)
    real_ask = T.ASK_WAIT
    mark = TMP / "fake-stopped.txt"
    try:
        T.ASK_WAIT = 1.0
        t0 = time.time()
        got, err = run("ask_forever", FAKE_APP_MARK=str(mark))
        check("nobody answers the Mac's question: it stops waiting, with that state", err is not None and err.state == "no_answer" and time.time() - t0 < 15, (err, time.time() - t0))
        check("...and the app stopped by itself once nothing touched its alive file", wait_for(mark.is_file, 10))
        check("...and that is noted", (T._read(home / T.PERMISSION) or {}).get("state") == "no_answer")
    finally:
        T.ASK_WAIT = real_ask
    mark.unlink()
    t0 = time.time()
    got, err = run("slow", deadline=1.5, FAKE_APP_MARK=str(mark))
    check("the words take longer than their limit: too long", err is not None and err.state == "too_long" and time.time() - t0 < 15, (err, time.time() - t0))
    check("...and the app stopped by itself", wait_for(mark.is_file, 10))
    n = len(started)
    for bad, why in ((TMP / "elsewhere" / "sound.wav", "outside the Assistant's own folder"),):
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"RIFF")
        try:
            ms.run(bad, "en-US", time.time() + 5, None)
            check(f"a sound file {why} is refused before the app is started", False)
        except T.TalkProblem as e:
            check(f"a sound file {why} is refused before the app is started", e.state == "failed" and len(started) == n)
    os.environ.pop("FAKE_APP_MODE", None)


# ====================================================================== sound: the talking as a small sound file

def tone_file(path, seconds, rate=8000):
    one = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(rate))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for _ in range(int(seconds)):
            w.writeframes(one)


MEASURE = r'''
import json, os, resource, sys
sys.path.insert(0, sys.argv[1])
import sound
got = sound.speech_wav(sys.argv[2], sys.argv[3], timeout=300)
k = 1024 if sys.platform != "darwin" else 1
print(json.dumps({"ok": got[0] is not None, "how": got[1], "self": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * k / 1e6,
                  "children": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * k / 1e6}))
'''


def part_sound():
    if not MAC:
        got = sound.speech_wav(str(ROOT / "tests" / "fixtures" / "loud-tone-3s.mp4"), TMP / "pc.wav")
        check("off a Mac, speech_wav makes nothing and says so in plain words", got[0] is None and "Mac" in got[1] and not (TMP / "pc.wav").exists(), got)
        return
    d = TMP / "sound"
    d.mkdir()
    short, long_ = d / "short.wav", d / "long.wav"
    tone_file(short, 20)
    tone_file(long_, 1200)
    (d / "measure.py").write_text(MEASURE, encoding="utf-8")
    for route, env in (("afconvert", {}), ("avfoundation", {"ASSISTANT_NO_AFCONVERT": "1"})):
        mem = {}
        for name, src, secs in (("short", short, 20), ("long", long_, 1200)):
            out = d / f"{name}-{route}.wav"
            r = subprocess.run([sys.executable, str(d / "measure.py"), str(REEL), str(src), str(out)], capture_output=True, text=True,
                               encoding="utf-8", env=dict(os.environ, **env), timeout=300)
            try:
                m = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                m = {"ok": False, "how": r.stdout + r.stderr}
            mem[name] = m
            lay = None
            if out.is_file():
                with open(out, "rb") as f:
                    lay = sound._wav_layout(f, out.stat().st_size)
            check(f"{route}: {secs} s of sound becomes a 16,000 a second, one channel, 16-bit file of the same length",
                  m.get("ok") and m.get("how") == route and lay is not None and lay[:4] == (1, 1, 16000, 16) and abs(sound.duration(str(out)) - secs) < 0.05,
                  (m, lay))
        if mem["short"].get("ok") and mem["long"].get("ok"):
            grow_self = mem["long"]["self"] - mem["short"]["self"]
            grow_kids = mem["long"]["children"] - mem["short"]["children"]
            check(f"{route}: memory does not grow with the length (20 s against 20 minutes: 38 MB of samples, under 16 MB more held)",
                  grow_self < 8 and grow_kids < 16, (mem["short"], mem["long"]))
        check(f"{route}: no half-made file left beside it", not [p.name for p in d.iterdir() if p.name.startswith(".")], [p.name for p in d.iterdir()])
    seams = []
    for piece in (300, 5, 7):
        p = d / f"seam-{piece}.wav"
        ok, why = sound._speech_reader(str(short), p, 16000, 60, piece=piece)
        seams.append((ok, p.stat().st_size if p.is_file() else 0))
    check("the reader's stretches each start exactly where they belong (the same length whatever the stretch: no drift over a long talk)",
          all(ok for ok, _ in seams) and len({n for _, n in seams}) == 1, seams)
    there = d / "there.wav"
    there.write_bytes(b"mine")
    got = sound.speech_wav(str(short), there)
    check("a file already there is never written over", got[0] is None and there.read_bytes() == b"mine", got)
    txt = d / "not-a-sound.mov"
    txt.write_text("this is not a video", encoding="utf-8")
    got = sound.speech_wav(str(txt), d / "none.wav")
    check("a file that is no video: plain words, nothing made", got[0] is None and not (d / "none.wav").exists() and "Traceback" not in got[1], got)
    src_hash = sha(short)
    check("the sound it listened to was only read", sha(short) == src_hash)
    js = sound.SPEECH_JS
    check("the reader only reads the video and only adds to the one file it is handed",
          "fileHandleForWritingAtPath(out)" in js and "seekToEndOfFile" in js and "removeItem" not in js and "AVAssetWriter" not in js)


# ====================================================================== the clips (AVFoundation, nothing installed)

CLICKS = [0.5, 1.4, 2.3, 3.2, 4.1, 5.0]


def click_wav(path, secs=6.0, rate=48000):
    """Silence with a 5 ms burst of a 2 kHz tone at each of CLICKS."""
    n = int(secs * rate)
    a = [0] * n
    for t in CLICKS:
        s = int(t * rate)
        for i in range(int(0.005 * rate)):
            a[s + i] = int(26000 * math.sin(2 * math.pi * 2000 * i / rate))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<%dh" % n, *a))


def onsets(a, rate):
    """Where each click starts, in seconds: within 0.1 s either side of where it belongs, the point where its
    loudness (|x| over about 1 ms) first reaches half that click's loudest (tests/fixtures/clicks.py's rule)."""
    out = []
    k = max(1, rate // 2000)
    for t in CLICKS:
        lo, hi = max(0, int((t - 0.1) * rate)), min(len(a), int((t + 0.1) * rate))
        env = [abs(x) for x in a[lo:hi]]
        sm = [sum(env[max(0, i - k):i + k + 1]) for i in range(len(env))]
        top = max(sm) if sm else 0
        if top <= 0:
            return None
        out.append((lo + next(i for i, v in enumerate(sm) if v >= top / 2)) / rate)
    return out


def make_clips(folder):
    sys.path.insert(0, str(ROOT / "tests"))
    import video_check as vc
    folder.mkdir(parents=True, exist_ok=True)
    cols = ";".join(",".join(map(str, c)) for c in vc.COLOURS)
    pic = folder / "picture.mov"
    vc.js("picture", str(pic), "640", "360", "6", "30", cols)
    out = {}
    for stem, maker in (("tone", vc.tone_wav), ("click", click_wav)):
        wav = folder / f"{stem}.wav"
        maker(wav)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(folder / f"{stem}.m4a")], capture_output=True, check=True)
    for name, snd, rot in (("upright.mov", "tone.m4a", 90), ("wide.mov", "tone.m4a", 0), ("silent.mov", "-", 0), ("clicks.mov", "click.m4a", 0)):
        vc.js("compose", str(pic), "-" if snd == "-" else str(folder / snd), str(folder / name), str(rot), vc.RECORDED)
        out[name] = folder / name
    return out


class RangeServer:
    """The small copy asked for in pieces, through the page server's own sender (reel_page.send_range)."""

    def __init__(self, path):
        target = str(path)

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                reel_page.send_range(self, target, "video/mp4")

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def get(self, rng=None):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
        c.request("GET", "/copy.mp4", headers={"Range": rng} if rng else {})
        r = c.getresponse()
        body = r.read()
        c.close()
        return r.status, r.getheader("Content-Range"), body

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


# ====================================================================== the job, start to finish, with the pretend transcriber

def part_job(clips):
    kit = make_kit(SHOOT)
    talk = kit / "Talking" / "Hannah talks é.mov"
    shutil.copyfile(clips["upright.mov"], talk)
    before = sha(talk)
    key = video.key(talk)
    photos_before = sorted(os.listdir(kit / "Photos"))

    # ---- refused up front, nothing made
    code, ans = TR.start(kit, "nope.mov")
    check("a video that isn't in the Talking folder: her line, nothing made",
          code == 404 and ans == {"ok": False, "why": "gone", "words": "That video isn't in this shoot's Talking folder."}
          and not (kit / ".kit" / "talking.json").exists() and not TR.job_path(kit).exists(), (code, ans))
    silent = kit / "Talking" / "silent.mov"
    shutil.copyfile(clips["silent.mov"], silent)
    code, ans = TR.start(kit, "silent.mov")
    check("a video with no sound: her line \"I couldn't hear any talking in that video.\" before anything is made",
          ans.get("ok") is False and ans.get("words") == "I couldn't hear any talking in that video."
          and not (kit / ".kit" / "talking.json").exists() and not TR.job_path(kit).exists()
          and not (kit / ".kit" / "talking" / video.key(silent)).exists(), (code, ans))
    silent.unlink()                                     # the test's own copy

    # ---- the whole job
    pretend(saw=str(SAW), sleep=1.5)
    t0 = time.time()
    code, ans = TR.start(kit, key)
    check("Edit my video (by the key the page sends): started", (code, ans) == (200, {"ok": True}), (code, ans))
    r = rec_of(kit)
    check("at once the record is on that video, working, with her line \"Getting your video ready…\"",
          r.get("video") == talk.name and r.get("status") == "working" and r.get("step") == "Getting your video ready…" and r.get("problem") == "", r)
    st = TR.state_for_page(kit)
    check("the page is told it is working, from the first moment", st.get("working") is True and st["rec"]["status"] == "working", (st.get("working"), st["rec"].get("status")))
    code2, ans2 = TR.start(kit, key)
    check("a second press while one runs: her line \"I'm still working on the last one. Give it a minute.\"",
          code2 == 409 and ans2.get("words") == "I'm still working on the last one. Give it a minute." and ans2.get("ok") is False, (code2, ans2))
    jpid = wait_for(lambda: job_of(kit).get("pid"), 20)

    early = set()

    def awake():
        early.add(rec_of(kit).get("step"))              # the page's line meanwhile, so looking here never hides one
        out = subprocess.run(["/bin/ps", "-axo", "command="], capture_output=True, text=True).stdout
        return f"caffeinate -i -w {jpid}" in out
    if MAC and os.path.exists("/usr/bin/caffeinate"):
        check("while the job works the Mac is kept awake for it (so a talk left running does not come back as \"took too long\")", bool(jpid) and wait_for(awake, 5), jpid)
    seen = {x for x in early if x}

    def steps():
        s = TR.state_for_page(kit)
        if s.get("ok") and s["rec"].get("step"):
            seen.add(s["rec"]["step"])
        return s if (s.get("ok") and not s["working"] and s["rec"].get("status") != "working") else None
    st = wait_for(steps, 90, 0.05)
    check("the job finished", bool(st), TR.state_for_page(kit).get("rec", {}).get("status"))
    took = time.time() - t0
    if MAC and os.path.exists("/usr/bin/caffeinate"):
        check("...and that stops when the job ends", wait_for(lambda: not awake(), 10))
    check("while it worked the page saw her two lines", {"Getting your video ready…", "Turning your words into a script…"} <= seen, seen)
    r = TR.load(kit)
    check("then ONE whole save: ready, the words, the sentences, the facts, how, on this Mac, when",
          r.get("status") == "ready" and r.get("step") == "" and r.get("problem") == "" and r.get("words") == TIDY
          and len(r.get("sentences") or []) == 2 and abs((r.get("info") or {}).get("dur", 0) - 6) < 0.2
          and (r["info"].get("w"), r["info"].get("h")) == (360, 640) and r.get("how") == "pretend" and r.get("ondevice") is True
          and isinstance(r.get("transcribed"), float) and r.get("captions") is True,
          {k: r.get(k) for k in ("status", "step", "problem", "info", "how", "ondevice", "transcribed", "captions")})
    check("the record keeps the key the words were made from", r.get("video_key") == key and st["video_state"] == "here", (r.get("video_key"), key))
    check("the page gets the words and pieces in her shape", len(st["rec"]["words"]) == len(SAID) and st["pieces"] and st["rec"]["info"]["dur"])
    j = job_of(kit)
    check("the job is written down as done, and its lock is free", j.get("state") == "done" and not TR.job_running(kit), j)
    copy = TR.preview_path(kit, key)
    check("the small copy is in the kit's hidden folder, under the video's key", copy.is_file() and copy == kit / ".kit" / "talking" / key / "preview.mp4" and TR.preview_for(kit) == copy)
    cf = video.facts(copy)
    check("the small copy is upright (the phone's turn drawn in), 540 or less on its short side, H.264 that plays as it is, with sound",
          cf["rotation"] == 0 and (cf["w"], cf["h"]) == (360, 640) and cf["plays_as_is"] and cf["has_audio"] and abs(cf["length"] - 6) < 0.2, cf)
    saw = json.loads(SAW.read_text(encoding="utf-8"))
    wavp = Path(saw["wav"])
    check("the transcriber was handed 16,000 a second, one channel sound of the whole video, in English",
          saw.get("rate") == 16000 and saw.get("channels") == 1 and saw.get("bits") == 16 and abs(saw.get("seconds", 0) - 6) < 0.2 and saw.get("lang") == "en-US", saw)
    check("that sound was on the computer's own disk, in the job's own scratch folder, never on the photo drive",
          wavp.parent.parent == TALK_HOME / "work" and wavp.parent.name == j.get("id") and str(kit) not in str(wavp), saw["wav"])
    check("the sound is never kept: the job's scratch folder is gone", not wavp.parent.exists() and not list((TALK_HOME / "work").iterdir()))
    check("their video and their photos were only read", sha(talk) == before and sorted(os.listdir(kit / "Photos")) == photos_before
          and sorted(os.listdir(kit / "Talking")) == [talk.name])
    check("nothing of theirs is in the Assistant's own folder (only its locks, its facts and its logs)",
          not [p for p in STUDIO.rglob("*") if p.suffix.lower() in (".mov", ".mp4", ".wav", ".jpg")], [str(p) for p in STUDIO.rglob("*")][:20])
    check("no real app was built or looked for", not (TALK_HOME / T.APP_NAME).exists() and not (TALK_HOME / T.BUILT).exists())
    ok, why = TR.can_make(kit)
    check("it may be made in CapCut now", ok and why == "")
    print(f"      (the whole job on a 6 s clip took {took:.1f} s, 1.5 s of it the pretend transcriber)")

    # ---- the small copy in pieces
    srv = RangeServer(copy)
    try:
        size = copy.stat().st_size
        s1 = srv.get("bytes=0-99")
        s2 = srv.get(f"bytes={size - 200}-")
        s3 = srv.get(f"bytes={size + 10}-")
        s4 = srv.get()
        check("the small copy plays by Range: 206 for a piece at the front and at the end (where its header is), 416 past the end, 200 whole",
              s1[0] == 206 and len(s1[2]) == 100 and s1[1] == f"bytes 0-99/{size}" and s2[0] == 206 and len(s2[2]) == 200
              and s3[0] == 416 and s4[0] == 200 and len(s4[2]) == size, (s1[:2], s2[:2], s3[:2], s4[0]))
    finally:
        srv.stop()

    # ---- run again: the copy is reused, the same words change nothing they did
    TR.change(kit, lambda rec: rec.update(cut=[[1, 2]]))
    copy_time = copy.stat().st_mtime_ns
    pretend()
    code, ans = TR.start(kit, talk.name)
    st = wait_done(kit)
    r = TR.load(kit)
    check("Edit my video again on the same video (by name): the small copy already made is used as it is",
          ans == {"ok": True} and st and r.get("status") == "ready" and copy.stat().st_mtime_ns == copy_time)
    check("...and the edit starts afresh, with what was there kept in \"replaced\"",
          not r.get("cut") and any(x.get("cut") == [[1, 2]] for x in r.get("replaced") or []), (r.get("cut"), r.get("replaced")))

    # ---- every problem a transcriber can stop with: its plain line, never a Python error
    kit2 = make_kit("2026-10-01 Second shoot")
    talk2 = kit2 / "Talking" / "second.mov"
    shutil.copyfile(clips["wide.mov"], talk2)
    cases = [({"error": s}, s) for s in ("refused", "restricted", "dictation_off", "servers", "no_answer", "too_long", "no_talking", "failed")]
    cases += [({"setup": s, "needs_setup": True}, s) for s in ("no_tools", "old_tools", "licence", "setup_failed", "old_mac")]
    cases += [({"crash": True}, "failed"), ({"words": []}, "no_talking"), ({"error": "a state nobody planned for"}, "failed"),
              ({"words": [{"w": " ", "start": 0, "end": 1}]}, "no_talking")]
    for spec, state in cases:
        pretend(**spec)
        code, ans = TR.start(kit2, "second.mov")
        st = wait_done(kit2)
        r = rec_of(kit2)
        want = TR.line_for(state)
        check(f"the transcriber stops ({json.dumps(spec)[:48]}): the page gets its plain line, status \"problem\", no script, never a Python word",
              ans == {"ok": True} and st and r.get("status") == "problem" and r.get("problem") == want and r.get("step") == ""
              and st["rec"]["problem"] == want and not st["rec"]["words"] and "Traceback" not in json.dumps(r)
              and job_of(kit2).get("state") == "problem", (r.get("status"), r.get("problem")))
    log = (STUDIO / "logs" / "talking.log").read_text(encoding="utf-8")
    check("the real error goes only to the log", "something broke that nobody planned for" in log and "pretend run" in log
          and "something broke" not in json.dumps(rec_of(kit2)))
    check("each stopped job tidied its own scratch folder", not list((TALK_HOME / "work").iterdir()), os.listdir(TALK_HOME / "work"))

    # the setup step is told to the page while it lasts
    pretend(needs_setup=True, setup_sleep=1.5)
    TR.start(kit2, "second.mov")
    seen = set()

    def steps2():
        s = TR.state_for_page(kit2)
        if s.get("ok") and s["rec"].get("step"):
            seen.add(s["rec"]["step"])
        return s.get("ok") and not s["working"] and s["rec"].get("status") != "working"
    wait_for(steps2, 60, 0.05)
    check("a first-time setup shows \"Setting up, just this once…\" while it lasts, and the job then goes on to ready",
          TR.OUR_JOB_WORDS["setup"][0] in seen and rec_of(kit2).get("status") == "ready", seen)
    pretend(asking=1.5)
    TR.start(kit2, "second.mov")
    seen.clear()
    wait_for(steps2, 60, 0.05)
    check("while the Mac asks its question the page says so", TR.OUR_JOB_WORDS["asking"][0] in seen, seen)

    # a problem on a video that already has its script: the script is still theirs
    pretend(error="refused")
    TR.start(kit2, "second.mov")
    st = wait_done(kit2)
    r = TR.load(kit2)
    check("a problem on a video that already has a script: the line is there, and the script is still theirs to edit (\"ready\")",
          st and r.get("status") == "ready" and r.get("problem") == TR.line_for("refused") and r.get("words") == TIDY, (r.get("status"), r.get("problem")))

    # ---- what the small copy can say, as this page's own lines (never the footage page's words)
    vm = TR._vm()
    real_copy = vm.preview_copy
    work = TALK_HOME / "work" / "bbbbbbbbbbbb"
    work.mkdir(parents=True)
    pretend()
    try:
        for state, line in (("lowspace", "The photo drive is almost full, so I couldn't make the preview."),
                            ("failed", "I couldn't read that video. Try exporting it again as a regular .mov or .mp4."),
                            ("busy", TR.OUR_JOB_WORDS["waited"][0]),
                            ("pc", this_computer.NO_TALKING_PC), ("hevc_pc", this_computer.NO_TALKING_PC)):
            vm.preview_copy = lambda *a, **k: {"ok": False, "state": state, "words": "THE FOOTAGE PAGE'S WORDS", "detail": ""}  # noqa: B023
            try:
                TR._work(kit2, {"video": "second.mov", "again": False}, work, TR.limits(6))
                check(f"the small copy says \"{state}\": this page's own line", False)
            except TR.JobProblem as e:
                got = TR.line_for(e.code)
                check(f"the small copy says \"{state}\": this page's own line, never the footage page's words", got == line and "FOOTAGE" not in got, got)
        vm.preview_copy = lambda *a, **k: {"ok": False, "state": "failed", "words": "x", "detail": "it took too long"}
        try:
            TR._work(kit2, {"video": "second.mov", "again": False}, work, TR.limits(6))
            check("a small copy that took too long says so", False)
        except TR.JobProblem as e:
            check("a small copy that took too long says so", e.code == "too_long")
        seen_limits = {}

        def spy(path, out, **k):
            seen_limits.update(k)
            return real_copy(path, out, **k)
        vm.preview_copy = spy
        TR._work(kit2, {"video": "second.mov", "again": False}, work, dict(TR.limits(6), copy=123.0))
        check("the small copy is handed its own time limit, and never waits a second time for the turn it is already in",
              seen_limits.get("timeout") == 123.0 and seen_limits.get("wait") == 0, seen_limits)
    finally:
        vm.preview_copy = real_copy
        shutil.rmtree(work, ignore_errors=True)

    # ---- the limits, with a pretend slow step
    kit3 = make_kit("2026-10-08 Third shoot")
    shutil.copyfile(clips["wide.mov"], kit3 / "Talking" / "third.mov")
    os.environ["ASSISTANT_TEST_TALK_LIMITS"] = json.dumps({"words": 1.0})
    pretend(sleep=60)
    t0 = time.time()
    TR.start(kit3, "third.mov")
    st = wait_done(kit3, 60)
    check("the words run past their limit: stopped with our \"took too long\" line, well inside a minute",
          st and rec_of(kit3).get("problem") == TR.OUR_JOB_WORDS["too_long"][0] and time.time() - t0 < 30, (rec_of(kit3).get("problem"), time.time() - t0))
    os.environ["ASSISTANT_TEST_TALK_LIMITS"] = json.dumps({"setup": 1.0})
    pretend(needs_setup=True, setup_sleep=60)
    t0 = time.time()
    TR.start(kit3, "third.mov")
    st = wait_done(kit3, 60)
    check("the setup runs past its limit: the same line", st and rec_of(kit3).get("problem") == TR.OUR_JOB_WORDS["too_long"][0] and time.time() - t0 < 30)

    # the computer's talking turn is somebody else's for longer than the wait
    os.environ["ASSISTANT_TEST_TALK_LIMITS"] = json.dumps({"turn": 1.0})
    pretend()
    with open(TALK_HOME / TR.TALK_TURN, "ab") as lf:
        this_computer.try_lock(lf)
        try:
            t0 = time.time()
            TR.start(kit3, "third.mov")
            st = wait_done(kit3, 60)
        finally:
            this_computer.unlock(lf)
    got = rec_of(kit3).get("problem")
    check("another shoot's talk keeps the computer's turn past the wait: our own line, never her \"I'm still working on the last one\" (not true of this shoot)",
          st and got == TR.OUR_JOB_WORDS["waited"][0] and got != TR.JOB_WORDS["still_working"] and time.time() - t0 < 30, (got, time.time() - t0))
    check("the two waits (the talking turn, the video turn) share one allowance: the job's hard stop is one wait and the work, not two",
          "t0 + lim[\"turn\"] + lim[\"ceiling\"]" in (SCRIPTS / "talking_rec.py").read_text(encoding="utf-8")
          and "lim[\"turn\"] - waited" in (SCRIPTS / "talking_rec.py").read_text(encoding="utf-8"))

    # a step that will not stop: the watchdog
    os.environ["ASSISTANT_TEST_TALK_LIMITS"] = json.dumps({"copy": 3, "sound": 2, "ask": 0, "words": 1, "grace": 1, "spare": 1})
    pretend(hang=120)
    t0 = time.time()
    TR.start(kit3, "third.mov")
    pid = wait_for(lambda: job_of(kit3).get("pid"), 20)
    st = wait_done(kit3, 60)
    j = job_of(kit3)
    check("a step that will not stop: the watchdog stops the job at the sum of its limits, and the page gets \"took too long\"",
          st and rec_of(kit3).get("problem") == TR.OUR_JOB_WORDS["too_long"][0] and j.get("state") == "problem" and 6 < time.time() - t0 < 40,
          (rec_of(kit3).get("problem"), j.get("state"), time.time() - t0))
    check("...and its process is gone, its lock free", wait_for(lambda: not arrange._pid_alive(pid), 10) and not TR.job_running(kit3), pid)
    left = sorted(os.listdir(TALK_HOME / "work"))
    check("...and the watchdog took the job's scratch with it: the sound of their talk is not left on the disk (stage G)", left == [], left)
    os.environ.pop("ASSISTANT_TEST_TALK_LIMITS")
    old = time.time() - 120
    dead = TALK_HOME / "work" / "eeeeeeeeeeee"          # a job that died with no chance to tidy up (a power cut)
    dead.mkdir()
    (dead / "sound.wav").write_bytes(b"RIFF")
    os.utime(dead, (old, old))
    stranger = TALK_HOME / "work" / "not a job"
    stranger.mkdir()
    os.utime(stranger, (old, old))
    young = TALK_HOME / "work" / "cccccccccccc"
    young.mkdir()
    pretend()
    TR.start(kit3, "third.mov")
    wait_done(kit3)
    now = sorted(os.listdir(TALK_HOME / "work"))
    check("the next job clears a dead job's scratch folder, and only that: not a folder by any other name, not one just made",
          rec_of(kit3).get("status") == "ready" and now == ["cccccccccccc", "not a job"], now)
    shutil.rmtree(stranger)
    shutil.rmtree(young)

    # ---- they choose another video while this one is still being turned into words
    other = kit3 / "Talking" / "other.mov"
    shutil.copyfile(clips["upright.mov"], other)
    TR.put_words(kit3, "other.mov", video.key(other), WORDS[:5], {"dur": 6.0})
    TR.use_video(kit3, "third.mov")
    pretend(sleep=3)
    TR.start(kit3, "third.mov")
    wait_for(lambda: rec_of(kit3).get("step") == "Turning your words into a script…", 30)
    TR.use_video(kit3, "other.mov")
    st = TR.state_for_page(kit3)
    check("(mid-job they choose another video: the page shows that one, and still knows a job is at work)",
          st["working"] is True and st["rec"]["video"] == "other.mov", (st["working"], st["rec"].get("video")))
    wait_for(lambda: job_of(kit3).get("state") != "running" and not TR.job_running(kit3), 60)
    r = TR.load(kit3)
    check("when the job finishes the record is NOT dragged back: still on the video they chose, ready, with that video's words",
          job_of(kit3).get("state") == "done" and r.get("video") == "other.mov" and r.get("status") == "ready" and len(r.get("words") or []) == 5,
          (job_of(kit3).get("state"), r.get("video"), r.get("status")))
    r = TR.use_video(kit3, "third.mov")
    check("...and the first video's script is there when they go back to it", r.get("status") == "ready" and r.get("words") == TIDY, r.get("status"))
    other.unlink()                                       # the test's own copy

    # ---- a job killed part way reads as a problem, never "working"
    pretend(sleep=60)
    TR.start(kit3, "third.mov")
    pid = wait_for(lambda: job_of(kit3).get("state") == "running" and os.listdir(TALK_HOME / "work") and job_of(kit3).get("pid"), 20)
    wait_for(lambda: rec_of(kit3).get("step") == "Turning your words into a script…", 20)
    os.kill(pid, signal.SIGKILL)
    wait_for(lambda: not arrange._pid_alive(pid), 10)
    check("(the job was killed while the record still said working)", rec_of(kit3).get("status") == "working")
    killed = sorted(os.listdir(TALK_HOME / "work"))
    old = time.time() - 120
    for n in killed:
        os.utime(TALK_HOME / "work" / n, (old, old))  # as if killed a while ago (one just made is never cleared)
    st = TR.state_for_page(kit3)
    check("a job killed part way: the look that tells the page it stopped also clears its scratch, so the sound of their talk does not wait for the next talking job (stage G)",
          len(killed) == 1 and os.listdir(TALK_HOME / "work") == [], (killed, os.listdir(TALK_HOME / "work")))
    r = rec_of(kit3)
    check("a job killed part way: the page is told it stopped, in plain words, and is not left on \"working\"",
          st["working"] is False and st["rec"]["status"] == "ready" and st["rec"]["problem"] == TR.OUR_JOB_WORDS["interrupted"][0]
          and r.get("step") == "" and r.get("words_of") is not None, (st["working"], st["rec"].get("status"), st["rec"].get("problem")))
    rev = r.get("rev")
    TR.state_for_page(kit3)
    check("asking again changes nothing more", rec_of(kit3).get("rev") == rev)
    check("the script it had before is untouched", TR.load(kit3).get("words") == TIDY)
    pretend()
    code, ans = TR.start(kit3, "third.mov")
    st = wait_done(kit3)
    check("and Edit my video can be pressed again straight away, and finishes", ans == {"ok": True} and st and rec_of(kit3).get("status") == "ready"
          and rec_of(kit3).get("problem") == "", (code, ans))
    dead = TALK_HOME / "work" / "ffffffffffff"
    dead.mkdir()
    left = ["ffffffffffff"]
    check("(a dead job's scratch folder just made is too new to be anyone's to clear yet)", TR.clear_stale_work() == [] and dead.is_dir())
    old = time.time() - 120
    os.utime(dead, (old, old))
    check("clearing by hand names exactly that folder, and a second clearing finds nothing", TR.clear_stale_work() == left and TR.clear_stale_work() == [])

    # a job written down that never started
    kit4 = make_kit("2026-10-15 Fourth shoot")
    shutil.copyfile(clips["wide.mov"], kit4 / "Talking" / "fourth.mov")
    TR.write_job(kit4, {"id": "dddddddddddd", "state": "queued", "t": time.time(), "video": "fourth.mov", "key": "x", "again": False})
    TR.change(kit4, lambda rec: rec.update(video="fourth.mov", status="working", step="Getting your video ready…"))
    check("a job just written down counts as working for its first seconds", TR.state_for_page(kit4)["working"] is True and rec_of(kit4)["status"] == "working")
    TR.write_job(kit4, {"id": "dddddddddddd", "state": "queued", "t": time.time() - 60, "video": "fourth.mov", "key": "x", "again": False})
    st = TR.state_for_page(kit4)
    check("a job that never started: after its seconds, a problem in plain words with no script (\"problem\")",
          st["working"] is False and st["rec"]["status"] == "problem" and st["rec"]["problem"] == TR.OUR_JOB_WORDS["interrupted"][0], st["rec"])
    check("...and the job itself is written down as over, so a process that starts late knows", job_of(kit4).get("state") == "problem", job_of(kit4))
    pretend()
    rc = TR.cmd_job(kit4, "dddddddddddd")
    check("that job's process starting late (a busy Mac, one just woken) makes nothing: the page is not turned \"ready\" minutes after it said stopped",
          rc == 0 and rec_of(kit4).get("status") == "problem" and rec_of(kit4).get("problem") == TR.OUR_JOB_WORDS["interrupted"][0]
          and not list((kit4 / ".kit" / "talking").glob("*/preview.mp4")) and not TR.words_for(kit4, "fourth.mov"), (rc, rec_of(kit4)))
    TR.write_job(kit4, {"id": "dddddddddddf", "state": "queued", "t": time.time(), "video": "fourth.mov", "key": "x", "again": False})
    rc = TR.cmd_job(kit4, "dddddddddddf")
    check("a queued job whose record no longer waits for it (told stopped, or they moved on) makes nothing either, and is written down as over",
          rc == 0 and rec_of(kit4).get("status") == "problem" and job_of(kit4).get("state") == "problem"
          and not list((kit4 / ".kit" / "talking").glob("*/preview.mp4")) and not TR.words_for(kit4, "fourth.mov"), (rc, job_of(kit4)))

    # a small copy that is already there and is no video
    fourth = kit4 / "Talking" / "fourth.mov"
    pv = TR.preview_path(kit4, video.key(fourth))
    for junk, what in ((b"", "an empty file"), (b"not a video at all " * 400, "a file that is no video")):
        if pv.exists():
            pv.unlink()                                  # the test's own
        pv.parent.mkdir(parents=True, exist_ok=True)
        pv.write_bytes(junk)
        before_aside = set(pv.parent.glob("preview.unusable-*.mp4"))
        pretend()
        TR.start(kit4, "fourth.mov")
        st = wait_done(kit4)
        aside = sorted(set(pv.parent.glob("preview.unusable-*.mp4")) - before_aside)
        try:
            good = abs(video.facts(pv)["length"] - 6) < 0.2
        except Exception as e:  # noqa: BLE001
            good = repr(e)
        check(f"a small copy already there that is {what}: set aside beside it (never deleted, never played), and a real one made",
              st and rec_of(kit4).get("status") == "ready" and good is True and len(aside) == 1 and aside[0].read_bytes() == junk
              and TR.preview_for(kit4) == pv, (rec_of(kit4).get("status"), good, [a.name for a in aside]))

    TR.write_job(kit4, {"id": "eeeeeeeeeeee", "state": "running", "t": time.time() - 500, "pid": os.getpid(), "until": time.time() - 100,
                        "video": "fourth.mov"})
    TR.change(kit4, lambda rec: rec.update(status="working", problem=""))
    st = TR.state_for_page(kit4)
    check("a job far past its time is told as too long, whatever else", st["rec"]["problem"] == TR.OUR_JOB_WORDS["too_long"][0], st["rec"].get("problem"))

    # ---- exported again under the same name
    time.sleep(1.1)                                      # a key is name, size and whole-second time
    shutil.copyfile(clips["wide.mov"], talk)             # "exported again": the same name, another file
    key2 = video.key(talk)
    st = TR.state_for_page(kit)
    check("a video exported again under the same name: the page is told its script is for the old file",
          key2 != key and st["video_state"] == "changed" and st["rec"]["status"] == "ready" and len(st["rec"]["words"]) == len(SAID), (key, key2, st["video_state"]))
    ok, why = TR.can_make(kit)
    check("...and the make is refused until Edit my video is pressed again, with our line", ok is False and why == TR.OUR_JOB_WORDS["changed"][0], (ok, why))
    check("...the old small copy is still played meanwhile (the one its script was made from)", TR.preview_for(kit) == TR.preview_path(kit, key))
    TR.change(kit, lambda rec: rec.update(cut=[[0, 1]]))
    pretend()
    code, ans = TR.start(kit, key2)
    st = wait_done(kit)
    r = TR.load(kit)
    new_copy = TR.preview_path(kit, key2)
    check("Edit my video again: a new small copy for the new file, the old one kept, and the record on the new key",
          ans == {"ok": True} and new_copy.is_file() and copy.is_file() and new_copy != copy and r.get("video_key") == key2
          and st["video_state"] == "here" and video.facts(new_copy)["w"] == 640, (ans, r.get("video_key")))
    check("...the old edit is kept in \"replaced\" and the new script starts clean", not r.get("cut") and any(x.get("cut") == [[0, 1]] for x in r.get("replaced") or []))
    check("...and it may be made again", TR.can_make(kit) == (True, ""))
    talk.unlink()                                        # the test's own copy
    ok, why = TR.can_make(kit)
    check("a video taken out of the Talking folder: the make is refused with her line", ok is False and why == "Your talking video isn't in the Talking folder anymore.")
    k5 = make_kit("2026-10-22 Fifth shoot")
    check("no script yet: the make is refused with her line", TR.can_make(k5) == (False, "Turn your video into a script first."))

    # ---- a PC's answer, on this Mac
    os.environ["ASSISTANT_NO_AVFOUNDATION"] = "1"
    os.environ["TALKING_TRANSCRIBER"] = "none"
    before_rec = (kit2 / ".kit" / "talking.json").read_bytes()
    before_job = TR.job_path(kit2).read_bytes()
    code, ans = TR.start(kit2, "second.mov")
    check("answering as a PC: Edit my video gives the PC line at once and makes nothing",
          ans == {"ok": False, "why": "pc", "words": this_computer.NO_TALKING_PC} and (kit2 / ".kit" / "talking.json").read_bytes() == before_rec
          and TR.job_path(kit2).read_bytes() == before_job, (code, ans))
    os.environ.pop("ASSISTANT_NO_AVFOUNDATION")
    os.environ["TALKING_TRANSCRIBER"] = "pretend"

    check("no job is left running", not any(TR.job_running(k) for k in (kit, kit2, kit3, kit4)))
    check("nothing is left in the scratch work folder", not os.listdir(TALK_HOME / "work"), os.listdir(TALK_HOME / "work"))


# ====================================================================== timing: the sound, the small copy and the clip agree

def part_timing(clips):
    d = TMP / "timing"
    d.mkdir()
    clip = clips["clicks.mov"]
    truth_a, truth_rate = sound._read_wav(str(clips["clicks.mov"].parent / "click.wav"))
    truth = onsets(truth_a, truth_rate)
    wav, how = sound.speech_wav(str(clip), d / "speech.wav")
    check("the clicks clip's talking sound was made", wav is not None, how)
    r = video.preview_copy(clip, d / "copy.mp4")
    check("the clicks clip's small copy was made", r.get("ok"), r)
    if wav is None or not r.get("ok"):
        return
    a, rate = sound._read_wav(str(wav))
    sp = onsets(a, rate)
    cwav, how2 = sound.speech_wav(str(d / "copy.mp4"), d / "copy.wav")
    b, rate2 = sound._read_wav(str(cwav)) if cwav else (None, 0)
    cp = onsets(b, rate2) if b is not None else None
    check("every click is found in the sound and in the small copy", bool(truth and sp and cp), (truth, sp, cp))
    if not (truth and sp and cp):
        return
    off_sp = max(abs(x - t) for x, t in zip(sp, truth))
    off_cp = max(abs(x - t) for x, t in zip(cp, truth))
    apart = max(abs(x - y) for x, y in zip(sp, cp))
    print(f"      (clicks: the sound is within {off_sp * 1000:.1f} ms of where they were put, the small copy within {off_cp * 1000:.1f} ms; "
          f"the two are {apart * 1000:.1f} ms apart at most; the sound came through {how})")
    check("the click times in the sound the words are made from and in the small copy the page plays agree within 20 ms", apart < 0.020, apart)
    check("...and both are within 20 ms of where the clicks really are", off_sp < 0.020 and off_cp < 0.020, (off_sp, off_cp))
    os.environ["ASSISTANT_NO_AFCONVERT"] = "1"
    try:
        wav2, how3 = sound.speech_wav(str(clip), d / "speech-reader.wav")
    finally:
        os.environ.pop("ASSISTANT_NO_AFCONVERT")
    if wav2 is not None:
        a2, r2 = sound._read_wav(str(wav2))
        s2 = onsets(a2, r2)
        apart2 = max(abs(x - y) for x, y in zip(s2, cp)) if s2 else 9
        print(f"      (through AVFoundation's reader instead: {apart2 * 1000:.1f} ms apart at most)")
        check("the other route (AVFoundation's reader) agrees with the small copy within 20 ms too", how3 == "avfoundation" and apart2 < 0.020, (how3, apart2))
    else:
        check("the other route (AVFoundation's reader) reads the clip", False, how3)


def main():
    clips = None
    try:
        if part("rules"):
            part_rules()
        if part("sound"):
            part_sound()
        if part("job") or part("timing"):
            if not video.avfoundation_here():
                skip("the whole job on a self-made clip, and the timing check", "clips are made with the Mac's own AVFoundation; tests/pc_talking.py covers a PC")
            else:
                clips = make_clips(TMP / "clips")
                if part("job"):
                    part_job(clips)
                if part("timing"):
                    part_timing(clips)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check(f"the test itself ran to its end ({e.__class__.__name__})", False, str(e))
    check("no half-made app, build folder or permission note in the test's own Assistant folder beyond the pretend ones",
          not (TALK_HOME / T.APP_NAME).exists() and not list(TALK_HOME.glob("build-*")) if TALK_HOME.is_dir() else True)
    check("the real Assistant folder on this computer was not touched", real_listing() == REAL_BEFORE)
    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed, {RESULTS['SKIP']} skipped")
    if RESULTS["FAIL"]:
        print(f"scratch folder kept: {TMP}")
        return 1
    shutil.rmtree(TMP, ignore_errors=True)
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
