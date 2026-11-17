#!/usr/bin/env python3
"""Songs on the reel page, as Nicole's v25 has them (section 5; stage J of the v26 build). Runs on a Mac and on a
PC, with nothing installed: no ffmpeg, no page server, no browser, no port.

    python tests/songs_check.py [--work <a scratch folder>] [--only measure|start|replaced|make|remove]

In a scratch folder it makes itself (STUDIO_HOME and HOME point there; nothing else is touched, no CapCut, no
folder opened, and "the Trash" is a folder of the run through STUDIO_TRASH_FOR_TESTS: the real Trash is never
touched). Every sound is made here: silence, a burst of noise for the glitch, the test beat for the song.

  measure   sound.silences and sound.lead_in: what ffmpeg's silencedetect (-50 dB, 0.3 s) would call a silence,
            measured in plain Python. The last gap that ends in the first 12 seconds; none, the top; a gap still
            going at the end has no end; a song nobody can read starts at the top. When this computer happens to
            have ffmpeg, ours is compared with it (SKIP otherwise: nothing here needs it).
  start     reel_page.short_song_start: only a song under 40 seconds; the top when there is no gap.
  replaced  a recording replaced by a new one of the same name gets its sound taken again ("<name> sound 2"), the
            first never written over; told apart by size, time and a hash of its start, written down in
            .kit/reel-sounds.json (the version before kept); safe to run twice; the song list hides them all.
            Here the taking of the sound is a stand-in (a small WAV), so the deciding is tried on every computer.
  make      through Make my reel's own job, for real: a short song that opens with a glitch and a silence starts
            after them, on a 1 of a bar and a whole frame; a recording replaced gets "sound 2" (SKIP where this
            computer can't take the sound out of a video).
  remove    Remove this song (her v27; Lane E's E12, Nov 17), through POST /reel-song-remove with a stand-in for
            the page server's handler: a recording and every sound taken from it go to the Trash (the run's own
            folder) byte for byte; the open reel's pick is cleared with the counter one higher, a second reel
            that picked it is untouched and says her line when opened; pressed again, a song in the Photos
            folder, an id of no song here, a bad id, another website, a cross-site press, another host, a body
            over the cap: refused, nothing moved; the second of a recording's files failing names the one that
            went; the route's own source has no delete in it; a PC's words.

Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept.
"""
import argparse
import array
import io
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import types
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
FIX = ROOT / "tests" / "fixtures"
BEAT60 = FIX / "test-beat-60s.wav"
results = []


def check(what, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{str(detail)[:500]}]" if detail != "" and not ok else ""), flush=True)
    return bool(ok)


def skip(what, why):
    print(f"SKIP  {what}   [{why}]", flush=True)


ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--work", help="a scratch folder for this run (made if missing); else a temporary one")
ap.add_argument("--only", choices=("measure", "start", "replaced", "make", "remove"))
A = ap.parse_args()
if A.work:
    Path(A.work).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="songs ", dir=A.work))
else:
    work = Path(tempfile.mkdtemp(prefix="assistant songs "))
work = Path(os.path.realpath(work))
STUDIO = work / "studio"
STUDIO.mkdir()
(work / "home").mkdir()
os.environ["STUDIO_HOME"] = str(STUDIO)           # before arrange is imported: it reads STUDIO_HOME then
os.environ["HOME"] = str(work / "home")           # never their CapCut, never their ~/.studio
os.environ["ASSISTANT_TEST_OPEN"] = "front"       # no folder is ever opened
os.environ["ASSISTANT_TEST_CAPCUT"] = "1"         # CapCut is never started
TRASH = work / "trash"
os.environ["STUDIO_TRASH_FOR_TESTS"] = str(TRASH)  # the tests' switch: "the Trash" is this folder; the real one is never touched
sys.path.insert(0, str(SCRIPTS))
sys.path.append(str(REEL))
import this_computer  # noqa: E402
import arrange  # noqa: E402
import reel_page  # noqa: E402
import sound  # noqa: E402

this_computer.utf8_output()
print(f"This is a {this_computer.COMPUTER}, Python {sys.version.split()[0]}.\n", flush=True)

# ---------- sounds made here ----------

RATE = 22050                                       # the test beat's own


def beat(seconds):
    """The first seconds of the test beat, as samples."""
    with wave.open(str(BEAT60), "rb") as w:
        a = array.array("h")
        a.frombytes(w.readframes(int(w.getframerate() * seconds)))
    if sys.byteorder == "big":
        a.byteswap()
    # the test beat is clicks with true silence between them; a real song has sound all the way through, so a quiet
    # bed (about -40 dB) is laid under it. Without it every pause between two clicks would be a "gap".
    for i in range(len(a)):
        a[i] = max(-32768, min(32767, a[i] + (330 if (i // 25) % 2 == 0 else -330)))
    return a


def quiet(seconds):
    return array.array("h", [0] * int(RATE * seconds))


def glitch(seconds, seed=7):
    r = random.Random(seed)
    return array.array("h", [r.randint(-9000, 9000) or 1 for _ in range(int(RATE * seconds))])


def hum(seconds, peak):
    """A steady tone whose every sample is exactly +peak or -peak: its loudness is never in doubt."""
    return array.array("h", [peak if (i // 20) % 2 == 0 else -peak for i in range(int(RATE * seconds))])


def write_wav(path, *parts, rate=RATE):
    a = array.array("h")
    for p in parts:
        a.extend(p)
    if sys.byteorder == "big":
        a.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(a.tobytes())
    return path


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- measure ----------

def measure():
    lim = (10 ** (-50 / 20.0)) * 32767            # 103.6: quieter than this is silent
    r = 1000
    got = sound.silences([0] * 300 + [500] * 10, r)
    check("a silence of 0.3 s is a gap, and it ends at the first sample that isn't silent", got == [(0.0, 0.3)], got)
    check("0.299 s of silence is not a gap (hers: d=0.3)", sound.silences([0] * 299 + [500] * 10, r) == [], sound.silences([0] * 299 + [500] * 10, r))
    check("-50 dB is the line: a sample of 103 is silent, 104 is not (ffmpeg: strictly inside)",
          sound.silences([103, -103] * 200 + [104], r) == [(0.0, 0.4)] and sound.silences([104, -104] * 200 + [2000], r) == [], int(lim))
    got = sound.silences([900] * 100 + [0] * 400 + [900] * 50 + [0] * 350 + [900], r)
    check("every gap is found, each from its first silent sample to the sound after it", got == [(0.1, 0.5), (0.55, 0.9)], got)
    got = sound.silences([900] * 100 + [0] * 500, r)
    check("a gap still going at the last sample has a start and no end", got == [(0.1, None)], got)
    check("no samples: no gaps", sound.silences([], r) == [])

    d = work / "measure"
    d.mkdir()
    song = beat(14)
    cases = {
        "a glitch, 1.3 s of silence, then the song: the music starts 1.5 s in": ((glitch(0.2), quiet(1.3), song), 1.5),
        "a song with no gap starts at the top": ((song,), 0.0),
        "two gaps: the LAST one that ends in the first 12 seconds": ((glitch(0.2), quiet(0.5), glitch(0.1), quiet(2.0), song), 2.8),
        "silence from the very first sample counts as a gap": ((quiet(0.8), song), 0.8),
        "a gap that ends after 12 seconds is not counted": ((hum(11.9, 3000), quiet(0.5), song), 0.0),
        "a gap that ends at exactly 12 seconds is": ((hum(11.5, 3000), quiet(0.5), hum(3, 3000)), 12.0),
        "a hum at -42 dB is sound, not silence": ((hum(2.0, 260), song), 0.0),
        "a hum at -56 dB is silence": ((glitch(0.2), hum(1.0, 50), hum(6, 3000)), 1.2),
        "a pause of a quarter second is not a gap": ((hum(1.0, 3000), quiet(0.25), hum(5, 3000)), 0.0),
        "a song that is silent to its end has no gap with an end: the top": ((glitch(0.2), quiet(6)), 0.0),
    }
    files = {}
    for k, (name, (parts, want)) in enumerate(cases.items()):
        f = write_wav(d / ("m%02d.wav" % k), *parts)
        files[name] = f
        got = sound.lead_in(f)
        check("lead_in: " + name, abs(got - want) <= 0.011 and (want != 0.0 or got == 0.0), (got, want))
    got = sound.lead_in(files["two gaps: the LAST one that ends in the first 12 seconds"])
    check("the answer is to a hundredth of a second (hers)", round(got, 2) == got, got)
    junk = d / "not a song.wav"
    junk.write_bytes(b"this is not a song at all")
    check("a song nobody can read starts at the top (never a stopped reel)", sound.lead_in(junk) == 0.0 and sound.lead_in(d / "nothing here.wav") == 0.0)
    before = {f.name: sha(f) for f in d.iterdir()}
    for f in list(files.values())[:3]:
        sound.lead_in(f)
    check("the songs are only read: none changed, nothing left beside them", {f.name: sha(f) for f in d.iterdir()} == before)
    check("her numbers, each in one place", (sound.LEAD_NOISE_DB, sound.LEAD_GAP, sound.LEAD_WITHIN, sound.LEAD_LISTEN) == (-50.0, 0.3, 12.0, 14.0))
    r = subprocess.run([sys.executable, str(REEL / "sound.py"), "--lead-in", str(files["a glitch, 1.3 s of silence, then the song: the music starts 1.5 s in"])],
                       capture_output=True, encoding="utf-8", errors="replace")
    check("sound.py --lead-in says it in a line", r.returncode == 0 and "the music starts 1.50 s in" in r.stdout, r.stdout + r.stderr)

    # the Mac's own way of hearing a compressed song (afconvert): the same answer
    if shutil.which("afconvert") and not this_computer.WINDOWS:
        src = files["a glitch, 1.3 s of silence, then the song: the music starts 1.5 s in"]
        m4a = d / "glitch.m4a"
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(src), str(m4a)], capture_output=True, timeout=60)  # pc-ok: a Mac only
        got = sound.lead_in(m4a) if m4a.is_file() else None
        check("the same song as an M4A: the same start, within three hundredths", got is not None and abs(got - 1.5) <= 0.03, got)
    else:
        skip("the same song as an M4A", "no afconvert on this computer")
    ff = shutil.which("ffmpeg") or next((x for x in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg") if Path(x).exists()), None)
    if not ff:
        skip("ours beside ffmpeg's silencedetect", "this computer has no ffmpeg (nothing here needs it)")
        return
    import re
    worst = 0.0
    for name, f in files.items():
        r = subprocess.run([ff, "-v", "info", "-t", "14", "-i", str(f), "-af", "silencedetect=noise=-50dB:d=0.3", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
        ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r.stderr)]
        ends = [e for e in ends if e <= 12]
        hers = round(ends[-1], 2) if ends else 0
        if "silent to its end" in name:
            continue        # ffmpeg ends a silence at the end of the file; ours has no end there (a choice, in the plan)
        worst = max(worst, abs(hers - sound.lead_in(f)))
    check("on every sound above, ours and ffmpeg's silencedetect agree to a hundredth", worst <= 0.011, worst)


# ---------- the kit ----------

HOME = work / "The Assistant"
KIT = "2026-11-14 Songs shoot"


def tiny_jpeg(path, w, h):
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, h, w, 3) + bytes([1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1])
    path.write_bytes(b"\xff\xd8" + sof + b"\xff\xd9")


def make_kit():
    r = subprocess.run([sys.executable, str(SCRIPTS / "posts.py"), "setup", "--home", str(HOME)], capture_output=True,
                       encoding="utf-8", errors="replace", env=dict(os.environ))
    check("(a pretend Assistant folder is set up)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
    kit = HOME / "Your Content" / KIT
    photos = kit / "Photos"
    photos.mkdir(parents=True)
    (kit / ".kit").mkdir()
    rows = []
    for n in range(1, 9):
        f = photos / ("p-%03d.jpg" % n)
        tiny_jpeg(f, 1080, 1350)
        rows.append({"n": n, "file": str(f), "w": 1080, "h": 1350, "way": "tall"})
    rec = {"name": "Songs shoot", "date": "2026-11-14", "folder": KIT, "source": "drop",
           "photos": sorted(p.name for p in photos.iterdir())}
    (kit / ".kit" / "kit.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    (kit / ".kit" / "sheet.json").write_text(json.dumps({"folder": str(photos), "photos": rows}, indent=1), encoding="utf-8")
    (kit / "Music").mkdir()
    return kit


def song_id(kit, name):
    return next((x["id"] for x in reel_page.songs_for_page(kit) if x["name"] == name), None)


def names(kit):
    return [x["name"] for x in reel_page.songs_for_page(kit)]


# ---------- start ----------

def start(kit):
    d = work / "start"
    d.mkdir()
    opening = (glitch(0.3), quiet(4.0))
    short = write_wav(d / "short.wav", *opening, beat(14))
    clean = write_wav(d / "clean.wav", beat(14))
    long = write_wav(d / "long.wav", *opening, beat(41))
    check("a short song that opens with a glitch and a silence starts after them (4.3 s)", abs((reel_page.short_song_start(short, 18.3) or 0) - 4.3) <= 0.011,
          reel_page.short_song_start(short, 18.3))
    check("a short song with no gap starts at the top: 0.0, not left to where it picks up", reel_page.short_song_start(clean, 14.0) == 0.0,
          reel_page.short_song_start(clean, 14.0))
    check("a song of 40 seconds or more is left alone (None: it starts where it picks up), glitch or not",
          reel_page.short_song_start(long, 45.3) is None and reel_page.short_song_start(long, 40.0) is None and reel_page.short_song_start(short, 39.9) is not None)
    check("a song whose length nobody could read is left alone (hers: 99)", reel_page.short_song_start(short, None) is None and reel_page.short_song_start(short, 0) is None)
    check("a song that can't be heard starts at the top", reel_page.short_song_start(d / "gone.wav", 12.0) == 0.0)
    check("the line is still 40 seconds, in its one place", reel_page.SHORT_SONG_FROM_TOP == 40)


# ---------- replaced (the taking of the sound is a stand-in) ----------

def fake_recording(path, fill, size=300_000):
    """A file that stands for a recording: its bytes are all that matter to telling one from another."""
    path.write_bytes(bytes([fill]) * size)


def replaced(kit):
    music = kit / "Music"
    real_extract = sound.extract_audio
    taken = []

    def stand_in(video, out, timeout=600):
        out = Path(out)
        if out.exists():
            return None, "there is already a file called %s there" % out.name
        taken.append(out.name)
        write_wav(out, hum(1.0, 3000 + 100 * len(taken)))        # a small WAV under the .m4a name: read by what is inside
        return out, "stand-in"

    sound.extract_audio = stand_in
    notes = kit / ".kit" / "reel-sounds.json"
    prev = kit / ".kit" / "reel-sounds.prev.json"
    try:
        rec = music / "Take.mov"
        fake_recording(rec, 1)
        s = {"path": rec, "where": "Music"}
        got, why = reel_page.sound_for(kit, s)
        first = music / "Take sound.m4a"
        check("a recording's sound is taken once, as \"<name> sound.m4a\" beside it", got == first and first.is_file() and taken == ["Take sound.m4a"], (got, why, taken))
        h1 = sha(first)
        d = json.loads(notes.read_text(encoding="utf-8"))
        note = (d.get("sounds") or {}).get("Music/Take sound.m4a") or {}
        check("which recording it came from is written down: its name, size, time and a hash of its start",
              note.get("of") == "Take.mov" and note.get("size") == 300_000 and note.get("time") == rec.stat().st_mtime
              and len(note.get("head") or "") == 64 and note.get("how") == "made", note)
        raw = notes.read_text(encoding="utf-8")
        check("the note names files only: no path in it", str(work) not in raw and "/Users/" not in raw and "\\\\" not in raw, raw[:300])
        before = notes.read_bytes()
        got, _ = reel_page.sound_for(kit, s)
        check("asked again: the same sound, nothing taken, the note not written again (safe to run twice)",
              got == first and taken == ["Take sound.m4a"] and notes.read_bytes() == before and sha(first) == h1)

        # the recording replaced by a new one of the same name (a different size)
        fake_recording(rec, 2, size=310_000)
        got, why = reel_page.sound_for(kit, s)
        second = music / "Take sound 2.m4a"
        check("the recording replaced by a new one of the same name: its sound is taken again, as \"<name> sound 2.m4a\" (hers)",
              got == second and second.is_file() and taken == ["Take sound.m4a", "Take sound 2.m4a"], (got, why, taken))
        check("the first sound is never written over: exactly as it was", sha(first) == h1)
        check("the notes' version before is kept beside them", prev.is_file() and prev.read_bytes() == before)
        d = json.loads(notes.read_text(encoding="utf-8"))["sounds"]
        check("both sounds are noted, each with its own recording", d["Music/Take sound.m4a"]["size"] == 300_000 and d["Music/Take sound 2.m4a"]["size"] == 310_000, d)
        got, _ = reel_page.sound_for(kit, s)
        check("the next make uses \"sound 2\": no third one", got == second and len(taken) == 2, taken)
        check("the song list shows the recording once and hides every sound of it", names(kit) == ["Take"], names(kit))

        # a new one of the SAME size: told apart by its start, not its size
        t_old = rec.stat().st_mtime
        fake_recording(rec, 3, size=310_000)
        os.utime(rec, (t_old + 50, t_old + 50))
        got, _ = reel_page.sound_for(kit, s)
        third = music / "Take sound 3.m4a"
        check("a new recording of the very same size and name is still told apart (the hash of its start): \"sound 3\"",
              got == third and taken[-1] == "Take sound 3.m4a" and len(taken) == 3, (got, taken))

        # the same recording, only its time moved (copied to another drive, touched): nothing is taken again
        before = notes.read_bytes()
        t = rec.stat().st_mtime
        os.utime(rec, (t + 500, t + 500))
        got, _ = reel_page.sound_for(kit, s)
        d = json.loads(notes.read_text(encoding="utf-8"))["sounds"]
        check("the same recording with only its time moved is the same recording: no new sound",
              got == third and len(taken) == 3 and not (music / "Take sound 4.m4a").exists(), (got, taken))
        check("and its new time is noted, so the next look needs no hash", d["Music/Take sound 3.m4a"]["time"] == rec.stat().st_mtime
              and d["Music/Take sound 3.m4a"]["head"] == json.loads(before)["sounds"]["Music/Take sound 3.m4a"]["head"], d["Music/Take sound 3.m4a"])
        check("same_recording: size, then time, then the start", reel_page.same_recording(d["Music/Take sound 3.m4a"], rec)[0] is True
              and reel_page.same_recording(d["Music/Take sound 2.m4a"], rec)[0] is False
              and reel_page.same_recording(d["Music/Take sound.m4a"], rec)[0] is False and reel_page.same_recording(None, rec)[0] is False)

        # a longer recording that opens exactly like the one before (the same first megabyte): told apart by its size
        big = music / "Long.mov"
        big.write_bytes(b"\x09" * 1_200_000)
        sb = {"path": big, "where": "Music"}
        got_a, _ = reel_page.sound_for(kit, sb)
        big.write_bytes(b"\x09" * 1_200_000 + b"\x0a" * 400_000)
        got_b, _ = reel_page.sound_for(kit, sb)
        check("a new recording whose first megabyte is the same but which is longer is told apart (its size): \"sound 2\"",
              got_a == music / "Long sound.m4a" and got_b == music / "Long sound 2.m4a", (got_a, got_b))

        # the first recording put back, byte for byte: its own first sound is used again
        fake_recording(rec, 1)
        got, _ = reel_page.sound_for(kit, s)
        check("the first recording put back: its own first sound is used again, nothing taken", got == first and "Take sound 4.m4a" not in taken, (got, taken))
        check("every earlier sound is still there, none changed", sha(first) == h1 and second.is_file() and third.is_file())

        # no note (a sound from before this, or a note that couldn't be written): her rule, the files' times
        old = music / "Before.mov"
        fake_recording(old, 5)
        snd = write_wav(music / "Before sound.m4a", hum(1.0, 2000))
        t = time.time() - 1000
        os.utime(old, (t, t)); os.utime(snd, (t + 10, t + 10))
        hb = sha(snd)
        got, _ = reel_page.sound_for(kit, {"path": old, "where": "Music"})
        d = json.loads(notes.read_text(encoding="utf-8"))["sounds"]
        check("a sound with no note that is newer than its recording is that recording's (hers): used as it is, and noted",
              got == snd and sha(snd) == hb and d.get("Music/Before sound.m4a", {}).get("how") == "found" and "Before sound" not in " ".join(taken), (got, d.keys()))
        stale = music / "Stale.mov"
        fake_recording(stale, 6)
        snd2 = write_wav(music / "Stale sound.m4a", hum(1.0, 2000))
        os.utime(snd2, (t, t)); os.utime(stale, (t + 10, t + 10))
        hs = sha(snd2)
        got, _ = reel_page.sound_for(kit, {"path": stale, "where": "Music"})
        check("a sound with no note that is OLDER than its recording came from an earlier one (hers): left as it is, \"sound 2\" made",
              got == music / "Stale sound 2.m4a" and sha(snd2) == hs and taken[-1] == "Stale sound 2.m4a", (got, taken))

        # one that can't be read is still left as it is (v19), now beside the rule above
        cut = music / "Cut.mov"
        fake_recording(cut, 7)
        (music / "Cut sound.m4a").write_bytes(b"")
        got, _ = reel_page.sound_for(kit, {"path": cut, "where": "Music"})
        check("a sound that can't be read is left as it is and a new one made beside it, as before",
              got == music / "Cut sound 2.m4a" and (music / "Cut sound.m4a").stat().st_size == 0, got)

        # the list hides any number (hers), and only beside its own recording
        write_wav(music / "Take sound 12.m4a", hum(1.0, 2000))
        write_wav(music / "Lonely sound 2.m4a", hum(1.0, 2000))
        got = names(kit)
        check("the song list hides \"<name> sound 12\" too (hers: any number)", "Take sound 12" not in got and got.count("Take") == 1, got)
        check("a song that only happens to be called \"... sound 2\", with no recording of that name, is still listed", "Lonely sound 2" in got, got)
        check("the most kept for one name is 99 (ours; hers has no end)", reel_page.SOUND_SPARES == 98)
        check("no hidden half-file and nothing unexpected is left in the Music folder",
              not [f for f in os.listdir(music) if f.startswith(".")], sorted(os.listdir(music)))

        # a note that can't be written never stops a make
        (kit / ".kit" / "reel-sounds.lock").unlink() if (kit / ".kit" / "reel-sounds.lock").exists() else None
        keep = reel_page.arrange.write_whole

        def no_write(path, obj):
            if Path(path).name == "reel-sounds.json":
                raise OSError("the drive is full")
            return keep(path, obj)

        reel_page.arrange.write_whole = no_write
        try:
            nn = music / "No note.mov"
            fake_recording(nn, 8)
            got, why = reel_page.sound_for(kit, {"path": nn, "where": "Music"})
            got2, _ = reel_page.sound_for(kit, {"path": nn, "where": "Music"})
        finally:
            reel_page.arrange.write_whole = keep
        check("a note that can't be written never stops the sound: it is made, and used again by the files' times",
              got == music / "No note sound.m4a" and got2 == got and not (music / "No note sound 2.m4a").exists(), (got, why, got2))
    finally:
        sound.extract_audio = real_extract


# ---------- make: through the job, for real ----------

def wait_job(kit, seconds=180):
    end = time.time() + seconds
    while time.time() < end:
        j = reel_page.job_for_page(kit)
        if j and j["state"] in ("done", "problem"):
            return j
        time.sleep(0.3)
    return reel_page.job_for_page(kit)


def body(kit, song, **more):
    b = {"kit": KIT, "stamp": arrange.sheet_stamp(kit), "picks": [{"n": n, "h": ""} for n in (1, 2, 3, 4, 5, 6)], "song": song,
         "vibe": "beat", "test": True}
    b.update(more)
    return b


def plan_facts(kit):
    try:
        return json.loads((kit / ".kit" / "reels" / "reel.json").read_text(encoding="utf-8"))["facts"]
    except (OSError, ValueError, KeyError):
        return {}


def make(kit):
    music = kit / "Music"
    write_wav(music / "Glitchy.wav", glitch(0.3), quiet(4.0), beat(14))     # 18.3 s: a short song
    write_wav(music / "Plain.wav", beat(14))
    lead = sound.lead_in(music / "Glitchy.wav")
    check("(the short song's music starts 4.3 s in)", abs(lead - 4.3) <= 0.011, lead)
    code, j = reel_page.start_make(body(kit, song_id(kit, "Glitchy")))
    job = wait_job(kit)
    f = plan_facts(kit)
    start_at = f.get("song_from")
    check("a test make with the short song finishes", code == 200 and job and job["state"] == "done", (code, j, job))
    check("the reel starts after the glitch and the silence, never in them",
          isinstance(start_at, (int, float)) and start_at >= lead - 0.02 - 1 / 30.0, (start_at, lead))
    check("and on the first 1 of a bar after them, not somewhere later in the song", isinstance(start_at, (int, float)) and start_at <= lead + 3.5, (start_at, lead))
    ff = f.get("song_from_f")
    check("on a whole frame (CapCut's 30 a second)", isinstance(ff, int) and isinstance(start_at, (int, float)) and abs(ff / 30.0 - start_at) < 0.001, (ff, start_at))
    words = (job or {}).get("words") or []
    check("her Plan line says where: \"starting the song N seconds in\"", words and words[0].startswith("Plan:")
          and ("starting the song %.0f seconds in" % (start_at or 0)) in words[0], words[:1])
    raw = json.dumps(job)
    check("the job says nothing of a path", str(work) not in raw and "/Users/" not in raw and "\\\\" not in raw, raw[:300])
    code, j = reel_page.start_make(body(kit, song_id(kit, "Plain")))
    job = wait_job(kit)
    top = plan_facts(kit).get("song_from")
    check("a short song with no gap starts at the top, on its first 1, as before", job and job["state"] == "done" and isinstance(top, (int, float)) and top < 2.6, (top, job))

    # a recording replaced by a new one of the same name, with the real taking of its sound
    one = (FIX / "click-100bpm.m4a").read_bytes()
    rec = music / "Rec.mov"
    rec.write_bytes(one)                                    # a recording's sound, in a .mov box
    rid = song_id(kit, "Rec")
    code, j = reel_page.start_make(body(kit, rid))
    job = wait_job(kit)
    made = sorted(x for x in os.listdir(music) if x.startswith("Rec sound"))
    if job and job["state"] == "problem" and not made:
        skip("a replaced recording, for real", "this computer can't take the sound out of a video here: " + str(job.get("problem")))
        return
    ext = Path(made[0]).suffix if made else ".m4a"
    first = music / ("Rec sound" + ext)
    check("a test make with a recording takes its sound once", job and job["state"] == "done" and made == [first.name], (job, made))
    if not first.is_file():
        return
    h1, m1 = sha(first), first.stat().st_mtime_ns
    rec.write_bytes(one + b"\x00\x00\x00\x10free" + b"\x00" * 8)     # a new recording under the same name (a little longer file)
    check("(the new recording keeps its name, so the page still has the same song picked)", song_id(kit, "Rec") == rid)
    code, j = reel_page.start_make(body(kit, rid, vibe="calm"))
    job = wait_job(kit)
    second = music / ("Rec sound 2" + ext)
    check("the recording replaced: the next make takes its sound again, as \"Rec sound 2\"", job and job["state"] == "done" and second.is_file()
          and second.stat().st_size > 2000, (job, sorted(os.listdir(music))))
    check("the first sound is exactly as it was: not written over, not touched", sha(first) == h1 and first.stat().st_mtime_ns == m1)
    h2, m2 = (sha(second), second.stat().st_mtime_ns) if second.is_file() else (None, None)
    code, j = reel_page.start_make(body(kit, rid, vibe="build"))
    job = wait_job(kit)
    check("the make after that uses \"sound 2\" again: no third, nothing written over", job and job["state"] == "done"
          and sorted(x for x in os.listdir(music) if x.startswith("Rec sound")) == sorted([first.name, second.name])
          and second.is_file() and (sha(second), second.stat().st_mtime_ns) == (h2, m2), sorted(os.listdir(music)))
    check("the song list shows the recording once, neither sound", names(kit).count("Rec") == 1 and not [n for n in names(kit) if n.startswith("Rec sound")], names(kit))
    check("the recording itself is only read", rec.read_bytes() == one + b"\x00\x00\x00\x10free" + b"\x00" * 8)
    check("no hidden half-file is left beside it", not [x for x in os.listdir(music) if x.startswith(".") and "part-" in x])


# ---------- Remove this song (her v27, section 2, step 3; her v25 /music/remove; Lane E's E12, Nov 17) ----------
# Through the route itself: reel_page.handle_post with a stand-in for the page server's request handler, so the
# guard (the host, the Origin, the body's cap) and the cross-site check are tried too, with no port listening.
# The tests' switch STUDIO_TRASH_FOR_TESTS points at a folder of this run (set at the top): the real Trash is
# never touched, and what "went to the Trash" can be read back byte for byte.

PORT = 8850                      # the stand-in's own port (Lane E's range, 8850 to 8859); nothing listens on it
PAGE = "songs12345"


class Handler:
    """A stand-in for the page server's request handler: exactly what reel_page.handle_post reads and writes."""

    def __init__(self, body=None, raw=None, headers=None):
        raw = json.dumps(body).encode("utf-8") if raw is None else raw
        self.headers = {"Host": "127.0.0.1:%d" % PORT, "Content-Type": "application/json", "Content-Length": str(len(raw))}
        self.headers.update(headers or {})
        self.rfile, self.wfile = io.BytesIO(raw), io.BytesIO()
        self.server = types.SimpleNamespace(server_address=("127.0.0.1", PORT))
        self.code = None

    def send_response(self, code):
        self.code = code

    def send_header(self, k, v):
        pass

    def end_headers(self):
        pass


def post(body=None, raw=None, headers=None, path="/reel-song-remove"):
    h = Handler(body, raw, headers)
    reel_page.handle_post(h, path, "")
    try:
        j = json.loads(h.wfile.getvalue().decode("utf-8"))
    except ValueError:
        j = None
    return h.code, j


def rm(kit, sid, **kw):
    return post({"kit": KIT, "song": sid}, **kw)


def rec_of(kit):
    return json.loads((kit / ".kit" / "reel-page.json").read_text(encoding="utf-8"))


def save_song(kit, sid):
    st = reel_page.state(kit)
    return reel_page.save_from_page({"kit": KIT, "stamp": st["stamp"], "base": st["rev"], "page": PAGE, "saved": {"song": sid}})


def trashed():
    return sorted(os.listdir(TRASH)) if TRASH.is_dir() else []


def remove(kit):
    import inspect
    import reels
    music = kit / "Music"
    notes = kit / ".kit" / "reel-sounds.json"
    prev = kit / ".kit" / "reel-sounds.prev.json"
    W = reel_page.WORDS
    # ---- the words
    check("her four page lines are in WORDS, word for word", (W.get("song_remove"), W.get("song_sure"), W.get("song_removing"), W.get("song_trashed")) ==
          ("Remove this song", "Move it to the Trash?", "Removing…", "Moved to the Trash. To get it back, open the Trash in Finder and choose Put Back."))
    check("her two server lines are there too", W.get("song_not_here") == "That song isn't in this shoot's folder anymore."
          and W.get("song_cant_trash") == "I couldn't move that song to the Trash. Drag it out of the shoot's Music folder in Finder instead.")
    page = reel_page.page_html(KIT, "Songs shoot")
    check("the page carries them for the drop-down's button (the button itself is Lane A's)", "Remove this song" in page and "Move it to the Trash?" in page)
    check("the route is in the reel page's list and on the posting server's reel line", "/reel-song-remove" in reel_page.POST_PATHS
          and '"/reel-song-remove"' in (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8"))
    tc = this_computer
    keep = (tc.WINDOWS, tc.TRASH_WORD, tc.TRASH_BACK, tc.FILES_APP)
    try:                             # a Mac pretending to be a PC: the words a PC sets at import, set by hand
        tc.WINDOWS, tc.TRASH_WORD, tc.TRASH_BACK, tc.FILES_APP = True, "the Recycle Bin", "open the Recycle Bin in File Explorer and choose Restore", "File Explorer"
        pc = (reel_page.trash_words(W["song_trashed"]), reel_page.trash_words(W["song_sure"]), reel_page.pc_words(reel_page.trash_words(W["song_cant_trash"])))
    finally:
        tc.WINDOWS, tc.TRASH_WORD, tc.TRASH_BACK, tc.FILES_APP = keep
    check("a PC reads the Recycle Bin, File Explorer and Restore in her lines (trash_words)",
          pc == ("Moved to the Recycle Bin. To get it back, open the Recycle Bin in File Explorer and choose Restore.", "Move it to the Recycle Bin?",
                 "I couldn't move that song to the Recycle Bin. Drag it out of the shoot's Music folder in File Explorer instead."), pc)
    here_trashed = reel_page.pc_words(reel_page.trash_words(W["song_trashed"]))      # what this computer says

    # ---- a recording with two sounds beside it (one noted, one by name only), a plain song, a link named like a sound
    rec = music / "Gone.mov"
    fake_recording(rec, 11)
    s1 = write_wav(music / "Gone sound.m4a", hum(1.0, 2500))
    write_wav(music / "Gone sound 2.m4a", hum(1.0, 2600))
    reel_page._note_sound(kit, s1, rec, "made")
    other = write_wav(music / "Other.wav", hum(1.0, 2000))
    link = music / "Gone sound 3.m4a"
    try:
        os.symlink(str(other), str(link))
        linked = True
    except (OSError, NotImplementedError, AttributeError):
        linked = False
    before = {f: sha(music / f) for f in os.listdir(music) if not (music / f).is_symlink()}
    gid, oid = song_id(kit, "Gone"), song_id(kit, "Other")
    check("(the recording is listed once, its sounds hidden, the link not listed)", gid and oid and names(kit).count("Gone") == 1
          and not [n for n in names(kit) if n.startswith("Gone sound")], names(kit))
    code, j = reel_page.version_from_page({"kit": KIT, "op": "new"})
    check("(a second reel is started)", code == 200 and j.get("current") == "v2", (code, j))
    code, j = save_song(kit, gid)
    check("(reel 2 picks the recording)", code == 200, (code, j))
    reel_page.version_from_page({"kit": KIT, "op": "switch", "id": "v1"})
    code, j = save_song(kit, gid)
    r0 = rec_of(kit)
    check("(reel 1 picks it too, and is the open one)", code == 200 and r0.get("current") == "v1" and r0["saved"]["song"] == gid, (code, j, r0.get("saved")))
    rev0, rec_before, notes_before = r0["rev"], (kit / ".kit" / "reel-page.json").read_bytes(), notes.read_bytes()

    # ---- the press
    code, j = rm(kit, gid)
    check("Remove this song answers ok, her \"Moved to the Trash\" line, the list without it, and that the open reel's pick was cleared",
          code == 200 and j and j.get("ok") is True and j.get("words") == here_trashed and j.get("cleared") is True
          and "Gone" not in [x["name"] for x in j.get("songs") or []], (code, j))
    went = {"Gone.mov", "Gone sound.m4a", "Gone sound 2.m4a"}
    check("the recording and both its sounds are in the Trash, byte for byte, and gone from the Music folder",
          set(trashed()) == went and all(sha(TRASH / f) == before[f] for f in went) and not any((music / f).exists() for f in went), trashed())
    check("the other song is exactly where it was", other.is_file() and sha(other) == before["Other.wav"])
    if linked:
        check("a link named like one of its sounds stays where it is, and its target is untouched (nothing is followed)",
              link.is_symlink() and other.is_file() and sha(other) == before["Other.wav"])
    else:
        skip("a link named like one of its sounds stays where it is", "this computer makes no links here")
    r1 = rec_of(kit)
    check("the open reel's pick is \"no song picked yet\", the counter one higher (a page a step behind is told), \"from\" dropped",
          r1["saved"]["song"] is None and r1["rev"] == rev0 + 1 and "from" not in r1, (r1["saved"].get("song"), r1["rev"], rev0))
    check("the record's version before is kept beside it", (kit / ".kit" / "reel-page.prev.json").read_bytes() == rec_before)
    v2 = reels.data_of(r1, "v2", reel_page.REEL_LIVE, reel_page.REEL_FIRST)
    check("reel 2, which picked the same song, is not touched", (v2.get("saved") or {}).get("song") == gid, v2.get("saved"))
    d = json.loads(notes.read_text(encoding="utf-8"))["sounds"]
    check("the sounds' lines are out of reel-sounds.json, the version before kept", "Music/Gone sound.m4a" not in d and prev.read_bytes() == notes_before, list(d))
    reel_page.version_from_page({"kit": KIT, "op": "switch", "id": "v2"})
    st = reel_page.state(kit)
    code, j = reel_page.start_make(body(kit, gid))
    check("reel 2 opened: its pick is the gone song, and Make my reel says her \"That song isn't there anymore\" line (as hers)",
          st["current"] == "v2" and st["saved"]["song"] == gid and code == 400 and j.get("words") == W["song_gone"], (st["saved"], code, j))
    reel_page.version_from_page({"kit": KIT, "op": "switch", "id": "v1"})

    # ---- refused, nothing moved
    t1 = trashed()
    code, j = rm(kit, gid)
    check("the same press again: her \"isn't in this shoot's folder anymore\" line, nothing moved",
          code == 400 and j.get("ok") is False and j.get("words") == W["song_not_here"] and trashed() == t1, (code, j))
    exp = write_wav(kit / "Photos" / "Export.wav", hum(1.0, 2100))
    eid = song_id(kit, "Export")
    code, j = rm(kit, eid)
    check("a song in the Photos folder (a folder of theirs) is refused with our line and stays",
          eid and code == 400 and j.get("words") == reel_page.OUR_WORDS["song_in_photos_stays"] and exp.is_file() and trashed() == t1, (code, j))
    bad = [("an id that is none of this shoot's songs", rm(kit, reel_page.song_id("Music", "nothing.wav")), 400, W["song_not_here"]),
           ("an id that isn't one", rm(kit, "../x"), 400, reel_page.NOT_UNDERSTOOD),
           ("a field the route doesn't take (a path)", post({"kit": KIT, "song": oid, "path": "x"}), 400, reel_page.NOT_UNDERSTOOD),
           ("a shoot that isn't in Your Content", post({"kit": "2026-01-01 Not here", "song": oid}), 404, reel_page.CANT_FIND),
           ("another website (Origin)", rm(kit, oid, headers={"Origin": "https://example.com"}), 403, reel_page.NOT_UNDERSTOOD),
           ("a cross-site press", rm(kit, oid, headers={"Sec-Fetch-Site": "cross-site", "Origin": "http://127.0.0.1:%d" % PORT}), 403, reel_page.NOT_UNDERSTOOD),
           ("another host's name", rm(kit, oid, headers={"Host": "evil.example"}), 403, reel_page.NOT_UNDERSTOOD),
           ("a body over the cap", post(raw=b"x" * 70000), 413, reel_page.NOT_UNDERSTOOD)]
    for what, (code, j), want, words in bad:
        check(f"refused ({want}): {what}; nothing moved", code == want and j and j.get("ok") is False and j.get("words") == words and trashed() == t1 and other.is_file(), (code, j))

    # ---- the second of a recording's files can't be moved: her line, then which one went
    half = music / "Half.mov"
    fake_recording(half, 12)
    hs = write_wav(music / "Half sound.m4a", hum(1.0, 2700))
    hid = song_id(kit, "Half")
    save_song(kit, hid)
    real, calls = this_computer._into_test_trash, []

    def second_fails(path, folder):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("pretend: the drive refused")
        return real(path, folder)

    this_computer._into_test_trash = second_fails
    try:
        code, j = rm(kit, hid)
    finally:
        this_computer._into_test_trash = real
    want = reel_page.pc_words(reel_page.trash_words(W["song_cant_trash"])) + " " + reel_page.trash_words(reel_page.OUR_WORDS["song_part_moved"]).replace("{names}", "Half.mov")
    check("when the second file can't be moved: her \"I couldn't move that song\" line, then which one went; the recording is in the Trash, its sound still in Music",
          code == 400 and j.get("ok") is False and j.get("words") == want and j.get("why") == this_computer.CANT_TRASH
          and (TRASH / "Half.mov").is_file() and hs.is_file() and not half.exists(), (code, j, trashed()))
    check("the recording's pick is cleared all the same (it is gone from the list)", j.get("cleared") is True and rec_of(kit)["saved"]["song"] is None)
    sid2 = song_id(kit, "Half sound")
    check("the sound left behind is listed as a song of its own now (honestly: it is a file in Music)", sid2 is not None, names(kit))
    code, j = rm(kit, sid2)
    check("and can be removed on its own", code == 200 and j.get("ok") is True and (TRASH / "Half sound.m4a").is_file() and not hs.exists(), (code, j))
    fake_recording(music / "Gone.mov", 13)
    code, j = rm(kit, song_id(kit, "Gone"))
    check("a second Gone.mov sent later sits beside the first in the Trash as \"Gone 2.mov\": nothing written over",
          code == 200 and (TRASH / "Gone 2.mov").is_file() and sha(TRASH / "Gone.mov") == before["Gone.mov"], trashed())

    # ---- the one door
    src = "".join(inspect.getsource(f) for f in (reel_page.remove_song, reel_page.sounds_of_recording, reel_page._drop_sound_notes, reel_page._clear_song))
    check("the route's own source names no os.remove, unlink, rmtree, osascript or send2trash: this_computer's trash_many is the one door",
          not any(x in src for x in ("os.remove", "unlink(", "rmtree", "send2trash", "osascript")) and "trash_many" in src)
    check("nothing but the removed files is in the test's Trash, and the kit's hidden folder is whole",
          not [f for f in trashed() if f.startswith(".")] and (kit / ".kit" / "reel-page.json").is_file() and notes.is_file())
    raw = json.dumps(post({"kit": KIT, "song": song_id(kit, "Other")})[1])
    check("the answer names no path", str(work) not in raw and "/Users/" not in raw and "\\\\" not in raw, raw[:300])


def part(name, fn, *args):
    print(f"\n-- {name}", flush=True)
    try:
        fn(*args)
    except Exception as e:  # noqa: BLE001
        import traceback
        check(f"{name}: ran to the end", False, f"{e.__class__.__name__}: {e} | {traceback.format_exc()[-700:]}")


kit = None
if A.only in (None, "measure"):
    part("measure: what a silence is, and where the music starts", measure)
if A.only != "measure":
    kit = make_kit()
if A.only in (None, "start"):
    part("start: only a short song", start, kit)
if A.only in (None, "replaced"):
    part("replaced: a recording replaced by a new one of the same name", replaced, kit)
if A.only in (None, "make"):
    part("make: through Make my reel's own job", make, kit)
if A.only in (None, "remove"):
    part("remove: Remove this song, to the computer's own Trash", remove, kit)

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
