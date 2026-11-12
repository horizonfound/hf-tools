#!/usr/bin/env python3
"""The Assistant, by Horizon Found. Turning talking into words: one interface, so the page and the record never
know (or care) what does the listening (Nicole's handoff v23, built our way).

A transcriber is handed a small sound file (16,000 a second, one channel, on the computer's own disk: sound.py's
speech_wav makes it) and gives back every word with its times:

    tr = transcribe.pick(home)             home: the Assistant's own talking folder on this computer's disk
    tr.available()                         can this computer do it this way at all?
    tr.setup(deadline, say)                whatever has to be there first (the first time only)
    tr.run(wav, lang, deadline, say)       {"words": [{"w", "start", "end", "conf"}], "how": ..., "ondevice": bool}

Anything that stops it is a TalkProblem with a `state` (a short code, never a sentence: the page's own lines are
kept with the page's other words, in talking_rec.py) and a `detail` (the real error, for the log only).
`say(code)` is told what is happening when the photographer should know: "setup" (something is being set up,
just this once), "asking" (the Mac is asking them a question).

Three to start:
  MacSpeech   the Mac's own Speech Recognition, inside a small app built on this Mac the first time (from
              transcriber/transcribe.swift and transcriber/Info.plist beside this file). WRITTEN, NEVER RUN:
              the first real build and the first permission box are Dustin's own to do (the plan's hand step).
              (To keep that claim exact: the Swift source was type-checked once with Apple's compiler, which
              makes no program and starts nothing. Two of its lines, the order of the "by itself?" and
              "available?" questions, were swapped after that and have not been through the compiler since.)
  Pretend     answers from the JSON file named in TALKING_PRETEND. Every test uses this one; it is only ever
              picked by name, never by itself.
  Nobody      a PC, or a Mac older than macOS 13: says so, makes nothing.
TALKING_TRANSCRIBER=pretend|none|mac-speech picks one by name; otherwise the first that is available.
TALKING_NO_REAL=1 (every test sets it) makes the real app impossible to build or start, whatever else is asked.
And a second belt, for the test that forgets: when STUDIO_HOME is set (the Assistant's own folder moved somewhere
else, which only a test or the hand step ever does; a photographer's computer never sets it) the real app is
refused too, unless TALKING_REAL_OK=1 says the hand step means it.

MacSpeech, and the rules it keeps:
  * The app is only ever started through the Mac's own `open -n -g -W <app> --args ...`, never by running the
    file inside it: run directly from our Python, macOS would charge the Speech Recognition request to the
    Claude app, which has no description for it (the Calendar boxes on Nov 11 named "claude"). app_command()
    is the one place that command is made.
  * Apple's tools are found without ever calling the bare `swiftc` (on a Mac without them that name pops Apple's
    install window): `xcode-select -p` by its full path, then the compiler by its full path, then an SDK that
    has the Speech framework. Every program here is run by its full path (_tool refuses anything else).
  * The app is built in a scratch folder inside `home`, signed for this Mac only, its signature checked, an
    older app set aside in older/ (never deleted), and the new one moved into place. built.json says what it
    was built from. It is rebuilt ONLY when the Swift source or the app's description (Info.plist) changes:
    to macOS a rebuilt app is a new app, and the permission is asked again.
  * The app is never pointed at the photo drive: the sound, its answer and its other small files are all inside
    `home` (refused otherwise), on the computer's own disk.
  * The app can never run on after the job that started it: the job touches an "alive" file every second and
    the app stops by itself when that stops, or when its deadline passes.
  * It refuses rather than send the sound to Apple's servers (rules 7 and 8): a Mac that can't do it by itself
    says so ("servers").
  * English only for now (en-US, hers).

A PC: nothing here can turn talking into words on a PC with nothing installed. pick() gives Nobody there, which
says so (state "pc"); every Mac-only line is in a Mac branch.

Python 3.9, standard library only.
"""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "studio-manager" / "scripts"))
import this_computer  # noqa: E402

SOURCE = HERE / "transcriber" / "transcribe.swift"
PLIST = HERE / "transcriber" / "Info.plist"
APP_NAME = "Assistant Transcriber.app"       # hers
APP_ID = "found.horizon.assistant.transcriber"
EXECUTABLE = "transcribe"                    # CFBundleExecutable (hers)
BUILT = "built.json"
PERMISSION = "permission.json"               # what the Mac last said about Speech Recognition, for `setup --check`
MIN_MACOS = 13                               # hers: macOS 13 or later
LANG = "en-US"                               # hers: the only language asked for
ASK_WAIT = 300.0                             # seconds the Mac's question may go unanswered
ALIVE_EVERY = 1.0                            # how often the job touches the "alive" file (the app gives up after 12 s without)
BUILD_LIMIT = 240.0                          # seconds the compiler may take
NO_AV = "ASSISTANT_NO_AVFOUNDATION"          # tests: a Mac answers the way a PC does (video.py's switch)
NO_REAL = "TALKING_NO_REAL"                  # tests: the real app can be neither built nor started
REAL_OK = "TALKING_REAL_OK"                  # the hand step only: the real app may be built and started in a scratch STUDIO_HOME
SCRATCH_HOME = "STUDIO_HOME"                 # set only by a test or the hand step, never on a photographer's computer
PICK = "TALKING_TRANSCRIBER"
PRETEND = "TALKING_PRETEND"

# What the app's answer codes mean here (the app answers with codes, never sentences).
APP_CODES = {"denied": "refused", "restricted": "restricted", "not_asked": "no_answer", "unavailable": "dictation_off",
             "servers": "servers", "no_words": "no_talking", "deadline": "too_long", "language": "failed",
             "failed": "failed", "stopped": "failed", "args": "failed"}
STATES = ("pc", "old_mac", "no_tools", "old_tools", "licence", "setup_failed", "no_answer", "refused", "restricted",
          "dictation_off", "servers", "no_talking", "too_long", "failed")


class TalkProblem(Exception):
    """Talking could not be turned into words. state: one of STATES. words: left empty by every transcriber
    here (the page's lines are the page's); detail: the real error, for the log only, never shown."""

    def __init__(self, state, words="", detail=""):
        super().__init__(f"{state}: {detail}" if detail else state)
        self.state, self.words, self.detail = state, words, str(detail or "")[:2000]


def as_pc():
    """True on a PC, and on a Mac told to answer the way a PC does."""
    return not this_computer.MAC or bool(os.environ.get(NO_AV))


def macos():
    """This Mac's macOS as a number (13, 14, 15, 26...), or 0."""
    try:
        return int((platform.mac_ver()[0] or "0").split(".")[0])
    except ValueError:
        return 0


def _never_real(what):
    if os.environ.get(NO_REAL):
        raise RuntimeError(f"{NO_REAL} is set: {what} is not allowed here (a test must use the pretend transcriber)")
    if os.environ.get(SCRATCH_HOME) and os.environ.get(REAL_OK) != "1":
        raise RuntimeError(f"{SCRATCH_HOME} is set and {REAL_OK} is not 1: {what} is not allowed in a scratch home "
                           f"(a test must use the pretend transcriber; only the hand step sets {REAL_OK}=1)")


def _time_left(limit, deadline):
    """How long one of the build's tools may take: its own limit, or what is left before `deadline` if that is
    less. TalkProblem("too_long") when nothing is left."""
    if deadline is None:
        return float(limit)
    left = float(deadline) - time.time()
    if left <= 0:
        raise TalkProblem("too_long", detail="the setup's time was up before the build finished")
    return min(float(limit), left)


def _tool(cmd, timeout):
    """Run one of the Mac's own programs BY ITS FULL PATH and give (exit code, what it printed). A bare name is
    refused before anything runs: the bare compiler's name pops Apple's install window on a Mac without it."""
    if not cmd or not os.path.isabs(str(cmd[0])):
        raise ValueError(f"a program is only ever run by its full path here, never as {(cmd or [''])[0]!r}")
    _never_real("running " + os.path.basename(str(cmd[0])))
    r = subprocess.run([str(c) for c in cmd], stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,  # pc-ok: only MacSpeech, on a Mac, gets here
                       encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


# ---------------------------------------------------------------- the registry

_KINDS = {}        # name -> (class, picked by itself?)
_ORDER = []


def register(name, cls, auto=True):
    """A way of turning talking into words. auto=False: only ever picked by name (the pretend one)."""
    _KINDS[name] = (cls, auto)
    if name not in _ORDER:
        _ORDER.append(name)


def pick(home=None):
    """The transcriber for this computer: the one named in TALKING_TRANSCRIBER, else the first that is
    available (never the pretend one by itself). Always answers with one: Nobody when nothing else can."""
    want = (os.environ.get(PICK) or "").strip().lower()
    if want:
        cls = _KINDS.get(want, (Nobody, False))[0]
        return cls(home)
    for name in _ORDER:
        cls, auto = _KINDS[name]
        if auto:
            tr = cls(home)
            if tr.available():
                return tr
    return Nobody(home)


class Transcriber:
    name = ""

    def __init__(self, home=None):
        self.home = Path(home) if home else None

    def available(self):
        return False

    def needs_setup(self):
        return False

    def setup(self, deadline, say=None):
        return None

    def run(self, wav, lang, deadline, say=None):
        raise TalkProblem("failed")

    def report(self):
        """A few plain facts for `talking_rec.py setup --check` (for the assistant, never a page)."""
        return {"how": self.name, "available": self.available()}


# ---------------------------------------------------------------- nobody (a PC, an older Mac)

class Nobody(Transcriber):
    name = "none"

    def available(self):
        return True

    def why(self):
        if as_pc():
            return "pc"
        if macos() and macos() < MIN_MACOS:
            return "old_mac"
        return "pc" if not this_computer.MAC else "failed"

    def setup(self, deadline, say=None):
        raise TalkProblem(self.why())

    def run(self, wav, lang, deadline, say=None):
        raise TalkProblem(self.why())

    def report(self):
        return {"how": self.name, "available": False, "why": self.why()}


# ---------------------------------------------------------------- the pretend one (every test)

class Pretend(Transcriber):
    """Answers from the JSON file named in TALKING_PRETEND:
      {"words": [{"w", "start", "end", "conf"}, ...], "ondevice": true,
       "needs_setup": true          setup says "setup" first (as a first build would)
       "setup_sleep": seconds, "setup": "<state>"      setup is slow / stops with that problem
       "asking": seconds            run says "asking" and waits that long first
       "sleep": seconds, "error": "<state>", "crash": true     run is slow / stops with that problem / breaks
       "hang": seconds              run sleeps that long whatever its deadline says (a step that will not stop)
       "saw": "<file>"}             run writes what it was handed there (the sound's place, rate, channels, length)
    Sleeping is in small steps and stops at the deadline with "too_long", as a real one would."""
    name = "pretend"

    def spec(self):
        p = os.environ.get(PRETEND)
        if not p:
            raise TalkProblem("failed", detail="TALKING_PRETEND names no file")
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise TalkProblem("failed", detail=f"the pretend answer can't be read: {e}")
        return d if isinstance(d, dict) else {}

    def available(self):
        return True

    def needs_setup(self):
        return bool(self.spec().get("needs_setup"))

    @staticmethod
    def _sleep(seconds, deadline):
        end = time.time() + float(seconds or 0)
        while time.time() < end:
            if deadline is not None and time.time() > deadline:
                raise TalkProblem("too_long", detail="pretend: past its deadline")
            time.sleep(0.05)

    def setup(self, deadline, say=None):
        s = self.spec()
        if s.get("needs_setup") and say:
            say("setup")
        self._sleep(s.get("setup_sleep"), deadline)
        if s.get("setup"):
            raise TalkProblem(str(s["setup"]), detail="pretend setup")

    def run(self, wav, lang, deadline, say=None):
        s = self.spec()
        if s.get("saw"):
            saw = {"wav": str(wav), "lang": lang}
            try:
                import sound                           # its header reader takes the "extensible" WAV afconvert writes
                with open(str(wav), "rb") as f:
                    lay = sound._wav_layout(f, os.fstat(f.fileno()).st_size)
                code, ch, rate, bits, align, _per, _start, data = lay
                saw.update(rate=rate, channels=ch, bits=bits, plain=code == 1, seconds=round(data / float(align * rate or 1), 3))
            except (OSError, TypeError, ValueError) as e:
                saw["error"] = str(e)
            Path(s["saw"]).write_text(json.dumps(saw), encoding="utf-8")
        if s.get("asking"):
            if say:
                say("asking")
            self._sleep(s["asking"], deadline)
        self._sleep(s.get("sleep"), deadline)
        if s.get("hang"):
            time.sleep(float(s["hang"]))
        if s.get("crash"):
            raise RuntimeError("pretend: something broke that nobody planned for")
        if s.get("error"):
            raise TalkProblem(str(s["error"]), detail="pretend run")
        return {"words": tidy(s.get("words")), "how": self.name, "ondevice": s.get("ondevice", True) is not False}


def tidy(words):
    """A transcriber's words as the record keeps them (hers): empty words dropped, times rounded to 3 places,
    confidence to 2. Anything that isn't a word with two times is left out, never a crash."""
    out = []
    for x in words if isinstance(words, list) else []:
        if not isinstance(x, dict) or not str(x.get("w", "")).strip():
            continue
        try:
            a, b = float(x["start"]), float(x["end"])
            c = float(x.get("conf", 1))
        except (KeyError, TypeError, ValueError):
            continue
        if not (a == a and b == b and c == c) or abs(a) > 1e7 or abs(b) > 1e7:     # not a number, or absurd
            continue
        out.append({"w": str(x["w"]), "start": round(a, 3), "end": round(b, 3), "conf": round(c, 2)})
    return out


# ---------------------------------------------------------------- the Mac's own Speech Recognition

def source_mark():
    """What the app is built from: a hash of the Swift source and of the app's description, together."""
    h = hashlib.sha256()
    for p in (SOURCE, PLIST):
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def read_built(home):
    try:
        d = json.loads((Path(home) / BUILT).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def needs_build(home, mark=None, chip=None):
    """Does the app have to be built (again)? Yes when it isn't there, when built.json is missing or names
    another source, or when it was built for another chip. Otherwise NO: a rebuild is a new app to macOS, and
    the permission would be asked again."""
    home = Path(home)
    b = read_built(home)
    if not (home / APP_NAME / "Contents" / "MacOS" / EXECUTABLE).is_file():
        return True
    return b.get("source") != (mark or source_mark()) or b.get("chip") != (chip or platform.machine())


def place_app(home, new_app, mark=None, chip=None, more=None):
    """Put a freshly built app in place: an app already there is set aside in older/<date-time>/ (never
    deleted), the new one is moved in, and built.json is written last (so an app with no built.json, or an old
    one, is simply built again). Returns the app's path."""
    home = Path(home)
    app = home / APP_NAME
    if os.path.lexists(app):
        older = home / "older"
        older.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for k in range(1, 100):
            dst = older / (stamp + ("" if k == 1 else f"-{k}"))
            if not os.path.lexists(dst):
                dst.mkdir()
                os.rename(app, dst / APP_NAME)
                break
        else:
            raise OSError("no free name to set the older app aside under")
    try:
        (home / BUILT).unlink()
    except OSError:
        pass
    os.rename(new_app, app)
    built = dict(more or {}, source=mark or source_mark(), chip=chip or platform.machine(),
                 built=time.strftime("%Y-%m-%d %H:%M:%S"))
    tmp = home / f".{BUILT}.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(built, indent=1), encoding="utf-8")
    os.replace(tmp, home / BUILT)
    return app


def find_tools():
    """Apple's own tools on this Mac: {"dev", "compiler", "sdk", "sdk_version"}, every one a full path that is
    really there. TalkProblem("no_tools") when they aren't. Nothing is installed and no window is opened:
    xcode-select -p only prints where the tools are."""
    try:
        code, out = _tool(["/usr/bin/xcode-select", "-p"], 20)  # pc-ok: only MacSpeech, on a Mac, gets here
    except (OSError, subprocess.SubprocessError) as e:
        raise TalkProblem("no_tools", detail=f"Apple's tools could not be asked after: {e}")
    dev = Path((out.splitlines() or [""])[-1].strip())
    if code != 0 or not dev.is_absolute() or not dev.is_dir():
        raise TalkProblem("no_tools", detail=f"asked where Apple's tools are, the Mac said: {out[:300]}")
    compilers = [dev / "usr" / "bin" / "swiftc",  # pc-ok: a full path on a Mac, never the bare name
                 dev / "Toolchains" / "XcodeDefault.xctoolchain" / "usr" / "bin" / "swiftc"]  # pc-ok: the same, inside Xcode
    sdks = [dev / "SDKs" / "MacOSX.sdk", dev / "Platforms" / "MacOSX.platform" / "Developer" / "SDKs" / "MacOSX.sdk"]
    comp = next((c for c in compilers if c.is_file() and os.access(c, os.X_OK)), None)
    sdk = next((s for s in sdks if (s / "System" / "Library" / "Frameworks" / "Speech.framework").is_dir()), None)
    if comp is None or sdk is None:
        raise TalkProblem("no_tools", detail=f"in {dev}: compiler {'found' if comp else 'missing'}, "
                                             f"an SDK with Speech {'found' if sdk else 'missing'}")
    version = ""
    try:
        version = str(json.loads((sdk / "SDKSettings.json").read_text(encoding="utf-8")).get("Version") or "")
    except (OSError, ValueError):
        pass
    return {"dev": str(dev), "compiler": str(comp), "sdk": str(sdk), "sdk_version": version}


def _why_not_built(out, tools):
    """Which of our lines a failed build gets: the licence never accepted, tools older than this macOS, or
    simply failed. "Older tools" ONLY when the compiler's own words say so: an SDK numbered below the macOS is
    normal and harmless (macOS 27.2 with SDK 26.5 builds fine), so the numbers alone prove nothing and are never
    a reason to send anyone to Software Update. The compiler's own words go to the log only."""
    low = out.lower()
    if "license" in low and ("agree" in low or "accept" in low):
        return "licence"
    if "sdk is not supported by the compiler" in low or "built with a newer version" in low \
            or "compiled module was created by a" in low:
        return "old_tools"
    return "setup_failed"


def real_builder(scratch, tools, deadline=None):
    """Build and sign the app in `scratch` (a new folder inside home); return the built app's path.
    WRITTEN, NEVER RUN (the plan's hand step). Signed for this Mac only ("-"), then the signature is checked.
    Each tool gets its own limit or what is left before `deadline`, whichever is less."""
    _never_real("building the transcriber app")
    app = Path(scratch) / APP_NAME
    (app / "Contents" / "MacOS").mkdir(parents=True)
    shutil.copyfile(PLIST, app / "Contents" / "Info.plist")
    exe = app / "Contents" / "MacOS" / EXECUTABLE
    chip = "arm64" if platform.machine() == "arm64" else "x86_64"
    code, out = _tool([tools["compiler"], "-O", "-swift-version", "5", "-sdk", tools["sdk"],
                       "-target", f"{chip}-apple-macos{MIN_MACOS}.0", str(SOURCE), "-o", str(exe)], _time_left(BUILD_LIMIT, deadline))
    if code != 0 or not exe.is_file():
        raise TalkProblem(_why_not_built(out, tools), detail=f"the compiler said: {out[-1500:]}")
    code, out = _tool(["/usr/bin/codesign", "--force", "--sign", "-", str(app)], _time_left(60, deadline))  # pc-ok: only on a Mac
    if code != 0:
        raise TalkProblem("setup_failed", detail=f"signing said: {out[-800:]}")
    code, out = _tool(["/usr/bin/codesign", "--verify", "--strict", str(app)], _time_left(60, deadline))  # pc-ok: only on a Mac
    if code != 0:
        raise TalkProblem("setup_failed", detail=f"the signature did not check: {out[-800:]}")
    return app


def app_command(app, args):
    """THE one way the app is started: the Mac's own open, which makes macOS start the app itself (so the
    Speech Recognition question belongs to the app, by its own name), and waits for it to end.
    -n a new copy of it, -g never brought to the front, -W wait. Never the file inside the app."""
    return ["/usr/bin/open", "-n", "-g", "-W", str(app), "--args", *[str(a) for a in args]]  # pc-ok: only on a Mac


def real_starter(cmd):
    """Start the command app_command() made. WRITTEN, NEVER RUN (the plan's hand step)."""
    _never_real("starting the transcriber app")
    if not os.path.isabs(cmd[0]):
        raise ValueError("a program is only ever run by its full path here")
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # pc-ok: only on a Mac


def _on_a_drive(path):
    """Is this path on a drive that was plugged in (a Mac mounts those under its Volumes folder)?"""
    p = os.path.realpath(str(path))
    return p.startswith("/Volumes/")  # pc-ok: the Mac branch; a PC never gets here


def _no_speech(detail):
    """Is this the Mac saying it heard no speech? Apple reports a recording with sound and no talking as an
    error with no words ("No speech detected", kAFAssistantErrorDomain 1110), which the app answers as "failed".
    Read here, in Python, so the Swift stays frozen. UNPROVEN until the hand step tries a silent clip."""
    low = str(detail or "").lower()
    return "no speech" in low or bool(re.search(r"\bkafassistanterrordomain 1110\b", low))


def _read(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


class MacSpeech(Transcriber):
    """The Mac's own Speech Recognition. WRITTEN, NEVER RUN until the hand step (see the notes at the top).
    `builder` and `starter` are the two things that touch the real app; a test hands in pretend ones."""
    name = "mac-speech"

    def __init__(self, home=None, builder=None, starter=None, tools=None):
        super().__init__(home)
        self.builder = builder or real_builder
        self.starter = starter or real_starter
        self.tools = tools or find_tools

    def available(self):
        return not as_pc() and macos() >= MIN_MACOS and self.home is not None

    def app(self):
        return self.home / APP_NAME

    def needs_setup(self):
        return needs_build(self.home)

    def setup(self, deadline, say=None):
        if not self.available():
            raise TalkProblem(Nobody(self.home).why())
        if not self.needs_setup():
            return None
        if say:
            say("setup")
        return self.build(deadline)

    def build(self, deadline=None):
        """Build the app and put it in place. Only called when needs_build() says so. `deadline` is handed to the
        builder (builder(scratch, tools, deadline)); a build that ends after it is not put in place: too long."""
        home = self.home
        if _on_a_drive(home):
            raise TalkProblem("setup_failed", detail="the app is never built on a plugged-in drive")
        tools = self.tools()
        home.mkdir(parents=True, exist_ok=True)
        scratch = home / f"build-{os.getpid()}-{os.urandom(3).hex()}"
        scratch.mkdir()
        try:
            try:
                new_app = self.builder(scratch, tools, deadline)
            except subprocess.TimeoutExpired as e:
                late = deadline is not None and time.time() >= float(deadline) - 1
                raise TalkProblem("too_long" if late else "setup_failed", detail=f"the build took too long: {e}")
            except OSError as e:
                raise TalkProblem("setup_failed", detail=f"the build could not run: {e}")
            if deadline is not None and time.time() > float(deadline):
                raise TalkProblem("too_long", detail="the build ended after the setup's time was up; it was not put in place")
            return place_app(home, new_app, more={"compiler": tools.get("compiler"), "sdk_version": tools.get("sdk_version"),
                                                  "macos": platform.mac_ver()[0]})
        finally:
            shutil.rmtree(scratch, ignore_errors=True)       # ours: made a moment ago, by this run, by this name

    def note_permission(self, state):
        try:
            tmp = self.home / f".{PERMISSION}.{os.getpid()}.tmp"
            tmp.write_text(json.dumps({"state": state, "when": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
            os.replace(tmp, self.home / PERMISSION)
        except OSError:
            pass

    def run(self, wav, lang, deadline, say=None):
        """Start the app on `wav` and wait for its answer. The time the Mac spends asking its question (at most
        ASK_WAIT) is not counted against `deadline`."""
        wav = Path(wav)
        work = wav.parent
        home = os.path.realpath(str(self.home))
        if _on_a_drive(wav) or os.path.commonpath([home, os.path.realpath(str(work))]) != home:
            raise TalkProblem("failed", detail="the app is only ever handed files inside the Assistant's own talking folder")
        app = self.app()
        if not (app / "Contents" / "MacOS" / EXECUTABLE).is_file():
            raise TalkProblem("setup_failed", detail="the app is not built")
        answer, state, alive = work / "words.json", work / "state.json", work / "alive"
        for p in (answer, state):
            try:
                p.unlink()
            except OSError:
                pass
        alive.write_text("", encoding="utf-8")
        hard = float(deadline) + ASK_WAIT                     # what the app itself is told: it never outlives this
        cmd = app_command(app, [wav, lang or LANG, answer, state, alive, f"{hard:.0f}"])
        try:
            p = self.starter(cmd)
        except OSError as e:
            raise TalkProblem("failed", detail=f"the app could not be started: {e}")
        asked_at, asked_for, told = None, 0.0, False
        try:
            while p.poll() is None:
                time.sleep(min(ALIVE_EVERY, 0.25))
                now = time.time()
                try:
                    os.utime(alive, None)
                except OSError:
                    pass
                st = (_read(state) or {}).get("state")
                if st == "asking":
                    if asked_at is None:
                        asked_at = now
                        self.note_permission("asking")
                    if not told and say:
                        say("asking")
                        told = True
                    if now - asked_at > ASK_WAIT:
                        self.note_permission("no_answer")
                        raise TalkProblem("no_answer", detail="nobody answered the Mac's question in time")
                elif asked_at is not None and not asked_for:
                    asked_for = now - asked_at                # answered: that wait is not counted
                    if say:
                        say("working")
                if st != "asking" and now > float(deadline) + asked_for:
                    raise TalkProblem("too_long", detail="the words took longer than their limit")
        finally:
            if p.poll() is None:
                # the app stops by itself once "alive" goes stale (nothing touches it from here on)
                try:
                    alive.unlink()
                except OSError:
                    pass
                try:
                    p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    p.kill()
        got = _read(answer)
        if got is None:
            raise TalkProblem("failed", detail=f"the app gave no answer (open ended with {p.returncode})")
        if got.get("error"):
            code = str(got["error"])
            detail = str(got.get("detail") or "")
            st = APP_CODES.get(code, "failed")
            if st == "failed" and ("dictation" in detail.lower() or "siri" in detail.lower()):
                st = "dictation_off"
            elif code == "failed" and _no_speech(detail):
                st = "no_talking"                             # the Mac heard sound and no speech in it (hers: her line)
            if st in ("refused", "restricted", "no_answer"):
                self.note_permission(st)
            raise TalkProblem(st, detail=f"the app said {code}: {detail}")
        self.note_permission("allowed")
        return {"words": tidy(got.get("words")), "how": self.name, "ondevice": got.get("ondevice") is not False}

    def report(self):
        out = {"how": self.name, "available": self.available(), "macos": platform.mac_ver()[0],
               "built": not needs_build(self.home) if self.home else False,
               "app_there": bool(self.home and self.app().is_dir()),
               "permission": (_read(self.home / PERMISSION) or {}) if self.home else {}}
        try:
            t = self.tools()
            out["tools"] = {"found": True, "sdk_version": t.get("sdk_version")}
        except TalkProblem as e:
            out["tools"] = {"found": False, "why": e.state}
        except RuntimeError as e:                              # TALKING_NO_REAL
            out["tools"] = {"found": None, "why": str(e)}
        return out


register("mac-speech", MacSpeech)
register("pretend", Pretend, auto=False)
register("none", Nobody)
