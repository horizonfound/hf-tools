#!/usr/bin/env python3
"""The reel's timing, checked against Nicole's own: her 22 acceptance cases (handoff v19, Nov 6, 2026) run through
OUR code (timing.py, called by reel.py), and every "Beats per piece" line must match hers word for word.

    python3 tests/reel_timing_check.py
    ASSISTANT_HANDOFF=<folder>     where to look for her handoff's two songs, if not in reference-private/

Her cases: two songs from a real shoot and a 60-second test beat, in every vibe (On every beat, A little of
everything, Calm, Build), as Moment first (one clip, then the photos), Back and forth (three clips, two photos
after each) and photos only; one reel too long for its song (her plain STOP line); one second variation.
The expected lines are copied from her acceptance/expected.json, unchanged.

  - The 60-second test beat is synthetic (a drum pattern made for testing) and lives in tests/fixtures/
    (test-beat-60s.wav), so its 9 cases always run.
  - The two real songs are a client's and are never in this repository. They are read from her handoff when it
    is on this computer (reference-private/nicole-handoff-v19-*/, in this checkout or the main one); without
    them their 13 cases say SKIP, plainly.
  - The photos are pretend files (01.jpg to 52.jpg, made here) of the real photos' sizes (numbers only, in
    tests/fixtures/reel-photo-sizes.json). A plan only needs a photo's size and its file name: the mix of
    "A little of everything" is seeded by the file names, so the pretend files carry the same ones.

Then, beyond her 22:
  - every planned case keeps her rules: nothing left out, every cut on a whole beat and on the frame at or just
    before it, every photo at least one beat and about half a second, the last photo at least two beats, a clip
    never longer than its card, an opening clip 3 seconds or more;
  - reel.py make --dry-run, the way Claude runs it (--clips, c1 in --picks, --pace and --vibe, the old names fast
    and steady), prints her lines exactly: Beats per piece, the kind note when the song is short, the STOP line
    when it can't fit; the expected lines for these extra cases came from her own bts_reel.py (Nov 7);
  - a reel with clips and no song (her bts_reel.py stopped there: a name used before it was set);
  - a clip in the CapCut project is a real video: type video, the whole video's length, its sound kept, the clip's
    start in the video, muted under a song and with its own sound when there is no song; its path written the
    way CapCut writes paths on this computer (forward slashes on a PC);
  - --clips refuses what can't be right, in plain words, and makes nothing.

Nothing outside a scratch folder made here is touched; CapCut is never asked about or opened (a pretend projects
folder, --ignore-open). Every line says PASS, FAIL or SKIP. Exit 1 only when something FAILED.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
BEAT60 = FIX / "test-beat-60s.wav"
SIZES = {int(n): wh for n, wh in json.loads((FIX / "reel-photo-sizes.json").read_text(encoding="utf-8"))["sizes"].items()}
VIDEO_NAME = "IMG_0278 4.MOV (not included: a dry run never opens it)"   # her clip's file name: it seeds the mix

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RESULTS = {"PASS": 0, "FAIL": 0, "SKIP": 0}


def check(name, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f"\n      {detail}"))


def skip(name, why):
    RESULTS["SKIP"] += 1
    print(f"SKIP  {name}: {why}")


# ---------------------------------------------------------------- her two songs, when her handoff is here

def handoff_songs():
    """(the 15-second song, the 29-second song) from her handoff, or (None, None)."""
    roots = []
    if os.environ.get("ASSISTANT_HANDOFF"):
        roots.append(Path(os.environ["ASSISTANT_HANDOFF"]))
    roots.append(ROOT / "reference-private")
    try:                                                   # a worktree: the main checkout's reference-private too
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            common = Path(r.stdout.strip())
            common = common if common.is_absolute() else ROOT / common
            roots.append(common.resolve().parent / "reference-private")
    except (OSError, subprocess.SubprocessError):
        pass
    for top in roots:
        if not top.is_dir():
            continue
        folders = [top] + sorted(top.glob("nicole-handoff-v19-*"))
        for f in folders:
            for song_dir in sorted(f.glob("**/examples/*/song")):
                one = sorted(song_dir.glob("*reel song.m4a"))
                two = sorted(song_dir.glob("*(29 s, from a screen recording).m4a"))
                if one and two:
                    return one[0], two[0]
    return None, None


# ---------------------------------------------------------------- her 22 cases (acceptance/run.py), unchanged

PICK14 = "41,10,14-,6,16,34,19+,27,38,42+,45,46-,49,51+"
PICK20 = "41,40,1,2,3,4+,10,14-,6-,16,34,38,19,27,42,21+,45,46,49,51"
PICK10 = "41,10,6,16,34,19+,42+,45,49,51+"

EXPECTED = {   # her acceptance/expected.json, word for word
    "song2 first 14 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song2 first 20 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2",
    "beat60 first 14 beat": "Beats per piece: clip 6, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song1 photos 10 beat": "Beats per piece: 1, 1, 1, 1, 1, 1, 2, 1, 1, 2",
    "beat60 backforth 14 beat": "Beats per piece: clip 6, 2, 2, clip 6, 1, 1, clip 6, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2",
    "song2 first 14 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 2, 1, 4, 1, 1, 1, 4",
    "song2 first 20 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 4, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 2, 2, 1, 3",
    "beat60 first 14 mixed": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 2, 1, 2, 1, 1, 1, 4",
    "song1 photos 10 mixed": "Beats per piece: 2, 1, 1, 1, 2, 2, 2, 1, 1, 3",
    "beat60 backforth 14 mixed": "Beats per piece: clip 6, 1, 1, clip 6, 1, 1, clip 6, 2, 1, 2, 1, 2, 2, 2, 1, 1, 4",
    "song2 first 14 calm": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 2, 4, 2, 2, 4, 2, 1, 2, 3",
    "song2 first 20 calm": "Beats per piece: clip 6, 2, 2, 2, 2, 2, 4, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3",
    "beat60 first 14 calm": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 2, 4, 2, 2, 4, 1, 1, 2, 4",
    "song1 photos 10 calm": "Beats per piece: 2, 2, 2, 2, 2, 2, 1, 1, 2, 3",
    "beat60 backforth 14 calm": "Beats per piece: clip 6, 2, 2, clip 6, 1, 1, clip 6, 2, 2, 4, 2, 2, 4, 1, 1, 2, 4",
    "song2 first 14 build": "Beats per piece: clip 6, 2, 1, 1, 2, 2, 1, 2, 1, 1, 2, 1, 1, 1, 4",
    "song2 first 20 build": "Beats per piece: clip 6, 2, 2, 2, 2, 2, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 4",
    "beat60 first 14 build": "Beats per piece: clip 6, 2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 1, 1, 3",
    "song1 photos 10 build": "Beats per piece: 2, 2, 2, 2, 1, 2, 2, 1, 1, 4",
    "beat60 backforth 14 build": "Beats per piece: clip 6, 2, 2, clip 6, 1, 2, clip 5, 2, 1, 2, 1, 1, 2, 1, 1, 1, 4",
    "song1 first 14 beat (too long for the song)": "STOP: Your song is only 15.4 seconds, and 1 clip and 14 photos need at least 14.2 seconds, even with every photo at one beat. Take a few photos out, or use a longer song.",
    "beat60 first 14 mixed variation 2": "Beats per piece: clip 6, 1, 2, 1, 1, 1, 2, 2, 1, 1, 4, 1, 1, 1, 3",
}

# Beyond her 22: run through reel.py make --dry-run; the expected lines came from her own bts_reel.py (Nov 7,
# a scratch run of her code, dry runs only). Each: (song, song start, vibe, the --picks text, clips, variation,
# the lines her engine printed that ours must print too).
P60 = ",".join(str(n) for n in list(range(1, 53)) + list(range(1, 9)))
P100 = ",".join(str(n) for n in list(range(1, 53)) + list(range(1, 49)))
EXTRA = {
    "60 photos, Calm, on the test beat: the kind note": (
        "beat60", None, "calm", P60, [], 0,
        ["Your song is only 60 seconds, so I kept all 60 photos and made Calm quicker to fit. A longer song, or fewer photos, gives it more room.",
         "Beats per piece: 1, 1, 2, 1, 1, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 1, 1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2, 2, 2, 1, 1, 2"]),
    "a clip and 60 photos, Calm: the kind note says your clip": (
        "beat60", None, "calm", "c1," + P60, [(2.5, 6.5)], 0,
        ["Your song is only 60 seconds, so I kept all 60 photos and your clip and made Calm quicker to fit. A longer song, or fewer photos, gives it more room.",
         "  1. clip from " + VIDEO_NAME + " at 2.5 s, 3.1 s long"]),
    "100 photos, On every beat: too long, her STOP line": (
        "beat60", None, "beat", P100, [], 0,
        ["STOP: Your song is only 60.0 seconds, and 100 photos need at least 63.3 seconds, even with every photo at one beat. Take a few photos out, or use a longer song."]),
    "two clips and 100 photos: too long, select fewer clips": (
        "beat60", None, "beat", "c1,c2," + P100, [(2.5, 6.5), (136.0, 140.0)], 0,
        ["STOP: Your song is only 60.0 seconds, and 2 clips and 100 photos need at least 69.0 seconds, even with every photo at one beat. Select fewer clips, take a few photos out, or use a longer song."]),
    "a 6-second card they made longer keeps its length, a beat less at most": (
        "beat60", None, "mixed", "c1," + PICK10, [(10.0, 16.0)], 0,
        ["  1. clip from " + VIDEO_NAME + " at 10.0 s, 5.6 s long", "Beats per piece: clip 9, 1, 2, 1, 1, 1, 3, 4, 1, 1, 4"]),
    "Bookends, Build: a clip to open and one to close": (
        "beat60", None, "build", "c1," + PICK10 + ",c2", [(2.5, 6.5), (188.0, 192.0)], 0,
        ["  12. clip from " + VIDEO_NAME + " at 188.0 s, 3.8 s long", "Beats per piece: clip 6, 2, 2, 2, 2, 1, 3, 2, 1, 1, 2, clip 6"]),
    "photos only, A little of everything, the song started 30 seconds in": (
        "beat60", 30.0, "mixed", PICK10, [], 0,
        ["Beats per piece: 3, 1, 1, 1, 2, 4, 2, 1, 1, 4"]),
    "photos only, On every beat, variation 3": (
        "beat60", None, "beat", PICK10, [], 3,
        ["Beats per piece: 1, 1, 1, 1, 1, 1, 2, 1, 1, 2"]),
}


def photo(tok, folder):
    n, mark = int(tok.rstrip("+-")), (tok[-1] if tok[-1] in "+-" else "")
    w, h = SIZES[n]
    return {"kind": "photo", "path": str(folder / f"{n:02d}.jpg"), "w": w, "h": h, "mark": mark}


def clip(start, end, folder):
    return {"kind": "clip", "path": str(folder / VIDEO_NAME), "src": start, "seconds": round(end - start, 2),
            "w": 2160, "h": 3840, "length": 420.7767}


def her_cases(folder):
    def first(picks, c=(2.5, 6.5)):
        return [clip(*c, folder)] + [photo(x, folder) for x in picks.split(",")]

    def backforth(picks, clips):
        rest, items = picks.split(","), []
        for c in clips:
            items.append(clip(*c, folder))
            for _ in range(2):
                if rest:
                    items.append(photo(rest.pop(0), folder))
        return items + [photo(x, folder) for x in rest]
    cases = {}
    for v in ("beat", "mixed", "calm", "build"):
        cases[f"song2 first 14 {v}"] = ("song2", 0, v, first(PICK14))
        cases[f"song2 first 20 {v}"] = ("song2", 0, v, first(PICK20))
        cases[f"beat60 first 14 {v}"] = ("beat60", None, v, first(PICK14))
        cases[f"song1 photos 10 {v}"] = ("song1", 0, v, [photo(x, folder) for x in PICK10.split(",")])
        cases[f"beat60 backforth 14 {v}"] = ("beat60", None, v, backforth(PICK14, [(2.5, 6.5), (136.0, 140.0), (188.0, 192.0)]))
    cases["song1 first 14 beat (too long for the song)"] = ("song1", 0, "beat", first(PICK14))
    cases["beat60 first 14 mixed variation 2"] = ("beat60", None, "mixed", first(PICK14), 2)
    return cases


# ---------------------------------------------------------------- her rules, on every planned reel

def rules(name, items, pieces, facts, period):
    """Nothing left out; every cut on a whole beat, on the frame at or just before it; every photo one beat and
    about half a second at least; the last photo two beats; a clip never past its card; an opening clip 3 s."""
    bad = []
    if len(pieces) != len(items):
        bad.append(f"{len(items)} pieces in, {len(pieces)} out")
    steps = facts["beats"]
    if any(not isinstance(b, int) or b < 1 for b in steps):
        bad.append(f"a hold that isn't a whole number of beats: {steps}")
    if any(not (-1e-9 <= e < 1 / 30 + 1e-9) for e in facts["cut_early_by"]):
        bad.append(f"a cut not on the frame at or just before its beat: {facts['cut_early_by']}")
    for k, (x, p, b) in enumerate(zip(items, pieces, steps)):
        if x["kind"] == "photo":
            if b * period < 0.45 - 1e-9:
                bad.append(f"photo {k + 1} on screen {b * period:.2f} s, under about half a second")
            if k == len(items) - 1 and b < 2:
                bad.append("the last photo under two beats")
        else:
            card = float(x["seconds"])
            if b * period > card + 0.02 + 1e-9:
                bad.append(f"clip {k + 1} runs {b * period:.2f} s, longer than its {card} s card")
            if k == 0 and card <= 4.2:
                kmax = max(1, int((card + 0.02) / period))
                if b * period < min(kmax * period, 2.95) - 1e-9:
                    bad.append(f"the opening clip {b * period:.2f} s, under 3 seconds")
            if not p.get("clip") or p["src"] + p["dur"] > float(x["length"]) + 1e-9:
                bad.append(f"clip {k + 1} is not a clip piece inside its video: {p}")
    check(f"{name}: her rules hold", not bad, "; ".join(bad))


# ---------------------------------------------------------------- reel.py make, the way Claude runs it

def run_reel(env, *args):
    r = subprocess.run([sys.executable, str(REEL / "reel.py")] + [str(a) for a in args], capture_output=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    song1, song2 = handoff_songs()
    songs = {"song1": song1, "song2": song2, "beat60": BEAT60}
    if not song1:
        print("NOTE  her handoff's two songs aren't on this computer (they're a client's, never in this repository):\n"
              "      the 13 cases that use them say SKIP. The 9 on the test beat always run.")
    work = Path(tempfile.mkdtemp(prefix="reel-timing-"))
    try:
        return _main(work, songs)
    finally:
        if RESULTS["FAIL"]:
            print(f"(the scratch folder is kept: {work})")
        else:
            shutil.rmtree(work, ignore_errors=True)


def _main(work, songs):
    photos = work / "photos"
    photos.mkdir()
    for n in SIZES:
        (photos / f"{n:02d}.jpg").write_bytes(b"pretend photo")   # a dry run only needs the name and the size
    (work / VIDEO_NAME).write_bytes(b"pretend video")
    studio, home = work / "studio", work / "home"
    home.mkdir()
    os.environ["STUDIO_HOME"] = str(studio)              # before reel.py is loaded: it reads this once
    env = dict(os.environ, STUDIO_HOME=str(studio), HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="utf-8")
    sys.path.insert(0, str(REEL))
    import capcut
    import reel
    import timing

    print("-- her 22 cases, through reel.plan_reel and timing.py")
    for name, case in her_cases(work).items():
        song_key, start, vibe, items = case[:4]
        variation = case[4] if len(case) > 4 else 0
        song = songs[song_key]
        if not song:
            skip(name, "this song is from her handoff, which isn't on this computer")
            continue
        pieces, facts = reel.plan_reel(items, str(song), vibe, start, False, None, variation)
        line = facts["problem"] if pieces is None else facts["beats_line"]
        check(name, line == EXPECTED[name], f"expected: {EXPECTED[name]}\n      got:      {line}")
        if pieces is not None:
            grid, _ = timing.song_grid(str(song))
            rules(name, items, pieces, facts, grid.period)

    print("\n-- reel.py make --dry-run, with --clips and c1 in --picks")
    listing = [{"n": n, "file": str(photos / f"{n:02d}.jpg"), "w": w, "h": h} for n, (w, h) in sorted(SIZES.items())]
    wd = studio / "reels" / "Pretend"
    wd.mkdir(parents=True)
    (wd / "photos.json").write_text(json.dumps({"folder": str(photos), "photos": listing}), encoding="utf-8")

    def clips_file(clips, tag, size=(2160, 3840)):
        f = work / f"clips-{tag}.json"
        f.write_text(json.dumps([{"path": str(work / VIDEO_NAME), "src": s, "seconds": round(e - s, 2), "w": size[0],
                                  "h": size[1], "length": 420.7767} for s, e in clips]), encoding="utf-8")
        return f

    def make(song, vibe, picks, clips=(), variation=0, start=None, flag="--pace", tag="x", extra=(), size=(2160, 3840)):
        args = ["make", "--dry-run", "--folder", photos, "--shoot", "Pretend", "--picks", picks, flag, vibe,
                "--song", song if song else "none", "--variation", variation]
        if clips:
            args += ["--clips", clips_file(clips, tag, size)]
        if start is not None:
            args += ["--song-start", start]
        return run_reel(env, *(args + list(extra)))

    def beats_of(out):
        return next((ln for ln in out.splitlines() if ln.startswith(("Beats per piece", "STOP"))), out.strip()[-300:])

    first14 = "c1," + PICK14
    rest = PICK14.split(",")
    backforth = ",".join(["c1"] + rest[0:2] + ["c2"] + rest[2:4] + ["c3"] + rest[4:])
    bf_clips = [(2.5, 6.5), (136.0, 140.0), (188.0, 192.0)]
    for label, args, want in (
            ("Moment first, --pace fast (the old name for On every beat)", (BEAT60, "fast", first14, [(2.5, 6.5)]), "beat60 first 14 beat"),
            ("Moment first, --vibe beat", (BEAT60, "beat", first14, [(2.5, 6.5)], 0, None, "--vibe"), "beat60 first 14 beat"),
            ("Back and forth, --vibe calm", (BEAT60, "calm", backforth, bf_clips, 0, None, "--vibe"), "beat60 backforth 14 calm"),
            ("Back and forth, --pace steady (the old name for Calm)", (BEAT60, "steady", backforth, bf_clips), "beat60 backforth 14 calm"),
            ("Back and forth, --pace mixed", (BEAT60, "mixed", backforth, bf_clips), "beat60 backforth 14 mixed"),
            ("Moment first, --pace build", (BEAT60, "build", first14, [(2.5, 6.5)]), "beat60 first 14 build"),
            ("Moment first, --pace mixed --variation 2", (BEAT60, "mixed", first14, [(2.5, 6.5)], 2), "beat60 first 14 mixed variation 2")):
        code, out = make(*args)
        check(f"reel.py {label}: her line", code == 0 and beats_of(out) == EXPECTED[want],
              f"exit {code}; expected: {EXPECTED[want]}\n      got:      {beats_of(out)}")
    if songs["song1"]:
        code, out = make(songs["song1"], "beat", first14, [(2.5, 6.5)], start=0)
        want = EXPECTED["song1 first 14 beat (too long for the song)"]
        check("reel.py, too long for the 15-second song: her STOP line, and exit 2", code == 2 and beats_of(out) == want,
              f"exit {code}; got: {beats_of(out)}")
    else:
        skip("reel.py, too long for the 15-second song", "that song is from her handoff, which isn't on this computer")

    for k, (label, (song_key, start, vibe, picks, clips, variation, want)) in enumerate(EXTRA.items()):
        code, out = make(songs[song_key], vibe, picks, clips, variation, start, tag=str(k))
        lines = out.splitlines()
        missing = [w for w in want if w not in lines]
        stop = want[0].startswith("STOP")
        check(f"reel.py, {label}", not missing and code == (2 if stop else 0),
              f"exit {code}; missing: {missing}\n      got: {out[-900:]}")

    code, out = make(None, "beat", "c1," + PICK10, [(2.5, 6.5)], tag="nosong")
    check("reel.py, a clip and no song: planned on an even 100 beats a minute, the footage keeping its sound",
          code == 0 and "the footage keeps its own sound" in out and beats_of(out).startswith("Beats per piece: clip "),
          f"exit {code}: {out[-500:]}")
    code, out = make(BEAT60, "mixed", PICK10)
    check("reel.py, photos only and no --clips: the plan line arrange_check reads, and her beats line",
          code == 0 and out.startswith("Plan: 10 photos") and beats_of(out).startswith("Beats per piece: "), out[-400:])

    print("\n-- what the plan says (the timing reviewers' findings, Nov 7)")
    code, out = make(BEAT60, "mixed", "1,2,3,4,5,6,7,8,9", tag="roomy")
    check("reel.py, 9 photos, A little of everything, on the 60-second test beat (a reel of about 8 seconds): "
          "no \"Your song is only...\" note, since the song had room (her engine said it here)",
          code == 0 and "Your song is only" not in out and beats_of(out).startswith("Beats per piece: "),
          f"exit {code}: {out[-600:]}")
    code, out = make(BEAT60, "beat", "7", tag="one")
    check("reel.py, a one-photo reel: \"Plan: 1 photo,\" (not \"1 photos\")", code == 0 and out.startswith("Plan: 1 photo,"),
          f"exit {code}: {out[:300]}")
    code, out = make(BEAT60, "beat", "21,1,2", tag="widephoto")
    check("reel.py, photos only: the wide photo named by its photo number, as before",
          code == 0 and "Wide photos zoomed to fill the screen: 1 (" in out, f"exit {code}: {out[-500:]}")
    code, out = make(BEAT60, "beat", "c1,1,2,21,3", [(2.5, 6.5)], tag="wideclip", size=(1920, 1080))
    check("reel.py, with a clip first: the wide photo named by its place in the reel (4), and the wide clip named too",
          code == 0 and "Wide photos zoomed to fill the screen, by their place in the reel: 4 (" in out
          and f"The clip at 1 in the reel ({VIDEO_NAME}) is wide" in out, f"exit {code}: {out[-700:]}")
    code, out = make(BEAT60, "beat", "c1,1,2,21,3", [(2.5, 6.5)], tag="wideclipfit", size=(1920, 1080), extra=("--fit",))
    check("reel.py --fit: nothing is zoomed, so no line says it is", code == 0 and "zoomed" not in out,
          f"exit {code}: {out[-500:]}")

    short = [{"kind": "clip", "path": str(work / VIDEO_NAME), "src": 0.0, "seconds": 4.0, "w": 2160, "h": 3840,
              "length": 1.0}] + [photo(x, photos) for x in ("1", "2", "3")]
    pieces, facts = reel.plan_reel(short, str(BEAT60), "beat")
    fits = pieces is not None and pieces[0]["src"] + pieces[0]["dur"] <= 1.0 + 1e-6
    check("plan_reel, a 4-second card on a 1-second video: the clip runs no longer than its video",
          fits, json.dumps(facts if pieces is None else pieces[0]))
    tiny = [{"kind": "clip", "path": str(work / VIDEO_NAME), "src": 0.0, "seconds": 0.2, "w": 2160, "h": 3840,
             "length": 0.2}] + [photo(x, photos) for x in ("1", "2")]
    pieces, facts = reel.plan_reel(tiny, str(BEAT60), "beat")
    check("plan_reel, a video shorter than one beat: STOP in plain words, nothing planned past its end",
          pieces is None and facts["problem"].startswith("STOP:")
          and "only 0.20 seconds of video" in facts["problem"], json.dumps(facts if pieces is None else pieces[0]))

    page = (ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts" / "arrange_page.py").read_text(encoding="utf-8")
    part = (ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "parts" / "arrange.md").read_text(encoding="utf-8")
    check("the reel picker's legend and parts/arrange.md: Longer and Quicker count in every vibe, in Nicole's words",
          "Longer stays on screen about twice as long" in page and "Quicker gets the shortest time, one beat" in page
          and "count when the reel moves" not in page and "only count with" not in part
          and "count with every vibe" in part)

    print("\n-- --clips refuses what can't be right")
    bad = work / "clips-bad.json"
    for label, content, picks, words in (
            ("a clip with no length", [{"path": str(work / VIDEO_NAME), "src": 1.0, "seconds": 4.0}], "c1,1,2", "how long the whole video is"),
            ("a clip that starts past its video's end", [{"path": str(work / VIDEO_NAME), "src": 50.0, "seconds": 4.0, "length": 20.0}], "c1,1,2", "its video is 20 s long"),
            ("a clip that isn't in --picks", [{"path": str(work / VIDEO_NAME), "src": 1.0, "seconds": 4.0, "length": 20.0, "w": 2160, "h": 3840}], "1,2,3", "isn't in --picks"),
            ("c2 when there is one clip", [{"path": str(work / VIDEO_NAME), "src": 1.0, "seconds": 4.0, "length": 20.0, "w": 2160, "h": 3840}], "c1,1,c2", "no clip c2"),
            ("one clip played twice", [{"path": str(work / VIDEO_NAME), "src": 1.0, "seconds": 4.0, "length": 20.0, "w": 2160, "h": 3840}], "c1,1,c1", "more than once"),
            ("a file with no clips", [], "1,2", "has no clips"),
            ("a clip that runs past the end of its video", [{"path": str(work / VIDEO_NAME), "src": 0.0, "seconds": 4.0, "length": 1.0, "w": 2160, "h": 3840}], "c1,1,2", "run past the end of its video"),
            ("a clip with no size (w and h)", [{"path": str(work / VIDEO_NAME), "src": 1.0, "seconds": 4.0, "length": 20.0}], "c1,1,2", "needs its video's size")):
        bad.write_text(json.dumps(content), encoding="utf-8")
        code, out = run_reel(env, "make", "--dry-run", "--folder", photos, "--shoot", "Pretend", "--picks", picks,
                             "--song", "none", "--clips", bad)
        check(f"--clips: {label} stops in plain words", code == 2 and "STOP" in out and words in out, f"exit {code}: {out[-300:]}")

    print("\n-- a clip in the CapCut project is a real video")
    parts = capcut.load_parts()
    for with_song in (True, False):
        plan = {"name": "Pretend reel", "hook": None,
                "photos": [{"path": str(work / VIDEO_NAME), "w": 2160, "h": 3840, "start_f": 0, "dur_f": 105,
                            "start": 0.0, "dur": 3.5, "fill": True, "clip": True, "src": 2.5, "length": 420.7767},
                           {"path": str(photos / "41.jpg"), "w": 3647, "h": 5444, "start_f": 105, "dur_f": 19,
                            "start": 3.5, "dur": 0.6333, "fill": True}],
                "song": ({"path": str(BEAT60), "from": 0.0, "from_f": 0, "fade_out": 0.5, "length": 60.0,
                          "name": BEAT60.name, "capcut_material": None, "capcut_beats": None} if with_song else None)}
        d, m = capcut.build(plan, parts, None)
        vids = {v["id"]: v for v in d["materials"]["videos"]}
        track = next(t for t in d["tracks"] if t["type"] == "video")
        seg_c, seg_p = track["segments"]
        mc, mp = vids[seg_c["material_id"]], vids[seg_p["material_id"]]
        meta = {x["file_Path"]: x for g in m["draft_materials"] for x in g.get("value", [])}
        clip_meta = meta.get(capcut.native(work / VIDEO_NAME), {})
        ok = (mc["type"] == "video" and mc["duration"] == 420776700 and mc["has_audio"] is True
              and mc["path"] == capcut.native(work / VIDEO_NAME) and "\\" not in mc["path"]
              and seg_c["source_timerange"] == {"start": 2500000, "duration": seg_c["target_timerange"]["duration"]}
              and seg_c["volume"] == (0.0 if with_song else 1.0)
              and clip_meta.get("metetype") == "video" and clip_meta.get("duration") == 420776700
              and mp["type"] == "photo" and seg_p["source_timerange"]["start"] == 0 and seg_p["volume"] == 1.0)
        check(f"capcut.build: the clip is a video, from 2.5 s into it, "
              + ("muted under the song" if with_song else "with its own sound (no song)") + "; the photo stays a photo",
              ok, json.dumps({"type": mc["type"], "duration": mc["duration"], "has_audio": mc.get("has_audio"),
                              "path": mc["path"], "src": seg_c["source_timerange"], "volume": seg_c.get("volume"),
                              "meta": {k: clip_meta.get(k) for k in ("metetype", "duration")}}))

    store = work / "CapCut projects"                     # a pretend CapCut projects folder: CapCut itself is never asked
    store.mkdir()
    f = clips_file([(2.5, 6.5)], "made")
    code, out = run_reel(env, "make", "--folder", photos, "--shoot", "Pretend", "--picks", "c1," + PICK10, "--clips", f,
                         "--song", BEAT60, "--store", store, "--ignore-open")
    projects = [p for p in store.iterdir() if p.is_dir()]
    draft = {}
    if projects:
        name = "draft_content.json" if os.name == "nt" else "draft_info.json"
        draft = json.loads((projects[0] / name).read_text(encoding="utf-8"))
    vids = draft.get("materials", {}).get("videos", [])
    check("reel.py make (not a dry run, into a pretend projects folder): one new project, the clip a video, then 10 photos",
          code == 0 and len(projects) == 1 and [v["type"] for v in vids] == ["video"] + ["photo"] * 10,
          f"exit {code}: {out[-400:]}; {[v.get('type') for v in vids]}")

    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed, {RESULTS['SKIP']} skipped.")
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
