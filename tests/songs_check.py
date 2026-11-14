#!/usr/bin/env python3
"""Songs on the reel page, as Nicole's v25 has them (section 5; stage J of the v26 build). Runs on a Mac and on a
PC, with nothing installed: no ffmpeg, no page server, no browser, no port.

    python tests/songs_check.py [--work <a scratch folder>] [--only measure|start|replaced|make]

In a scratch folder it makes itself (STUDIO_HOME and HOME point there; nothing else is touched, no CapCut, no
folder opened). Every sound is made here: silence, a burst of noise for the glitch, the test beat for the song.

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
And, on every run: Remove a song is NOT built (it waits on Nicole): no word of it on the page, no route.

Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED; the scratch folder is then kept.
"""
import argparse
import array
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
ap.add_argument("--only", choices=("measure", "start", "replaced", "make"))
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


# ---------- Remove a song is not built ----------

def no_remove(kit):
    page = reel_page.page_html(KIT, "Songs shoot")
    src = (SCRIPTS / "reel_page.py").read_text(encoding="utf-8") + (SCRIPTS / "posting_queue.py").read_text(encoding="utf-8")
    check("Remove a song is NOT built (it waits on Nicole): no word of it on the page", "Move to Trash" not in page and "music/remove" not in page
          and "Put Back" not in page)
    check("and no route for it on the page server", "music/remove" not in src and "song-remove" not in src and "send2trash" not in src)


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
if kit is not None:
    part("Remove a song is not built", no_remove, kit)

failed = results.count(False)
print(f"\n{len(results)} checks, {sum(results)} passed, {failed} failed." + (f"  Scratch folder, kept to look at: {work}" if failed else ""))
if not failed:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(1 if failed else 0)
