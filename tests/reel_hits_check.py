#!/usr/bin/env python3
"""Every vibe lands on the song's real hits (Nicole's handoff v25, Nov 13, section 9), checked on OUR code
(timing.py, called by reel.py): the three steps, each with a check that fails when the step is taken out.

    python3 tests/reel_hits_check.py

Nicole: "The little bit of everything was terrible. It didn't even fall in the beats." Then: "Can you make sure
that this applies to all edits? They all have to land on beats and have to actually listen to the song. It can't
be auto or random, it has to actually work for each individual song."

  1. the hits you can hear (timing.audible_hits): a jump in the sound that stands out 0.8 standard deviations
     above the music 1.5 s either side of it, never two closer than 0.2 s (the louder is kept);
  2. each grid tick moves onto the hit nearest it, when one is within a sixth of a beat and 0.09 s at the most
     (timing.onto_hits); a tick with no hit near it is marked (Grid.ON);
  3. in the one search, a cut on a tick with no hit costs W_EMPTY (0.9).

Her 22 acceptance lines, re-recorded for this, are in tests/reel_timing_check.py. Here:
  - steps 1 and 2 on made-up numbers, where the right answer can be worked by hand;
  - a LOOSE SONG made here (a plain .wav written by this test: about 100 beats a minute, every second beat a
    little early or late, every fifth beat silent), where this test knows exactly when the song hits. In every
    vibe, with the three steps, at least as many cuts land within 60 ms of a real hit as on the plain grid (her
    own measure), and more of them over all; with step 3 taken out (W_EMPTY 0), or step 2 (no ticks moved), the
    counts drop, so each step is seen to matter;
  - the same loose song under a perfectly even grid (her case: "the ticks drift off what you hear"): with the
    ticks moved, the cuts sit right on the thumps; with the ticks left where they were, fewer do;
  - the steady 60-second test beat: ticks move by a few hundredths of a second at the most;
  - "No song" works in every vibe, photos only and with clips (her v25 fix: it had crashed);
  - CapCut's times stay on whole frames: every cut on the frame at or just before its (moved) beat;
  - a song with too few hits to tell keeps its plain grid, exactly;
  - a song from CapCut's own music (a made-up CapCut beat list over the loose song): its beats stay exactly on
    CapCut's marks, the marks with no hit are still marked, and every vibe plans (review, Nov 14);
  - reel.py make --dry-run (the chat's reel maker) goes through the same three steps and says so in her line:
    "Real hits: 13 of 14 cuts land on a hit you can hear.";
  - the reel page's line for A little of everything is hers (v25);
  - timing.py stays plain Python: no numpy, no ffmpeg, nothing run.

Nothing outside a scratch folder made here is touched. Every line says PASS or FAIL. Exit 1 when something FAILED.
"""
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
MANAGER = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
BEAT60 = ROOT / "tests" / "fixtures" / "test-beat-60s.wav"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RESULTS = {"PASS": 0, "FAIL": 0}


def check(name, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f"\n      {detail}"), flush=True)


def loose_song(path, secs=30.0, bpm=100.0, sway=0.05, skip=5, seed=25, rate=22050):
    """A song with a loose beat, written as a plain .wav: a low thump on every beat, every second one up to
    `sway` seconds early or late, every `skip`-th beat silent, over a quiet steady tone. Returns the times the
    song really hits."""
    rnd = random.Random(seed)
    n = int(secs * rate)
    a = [0.0] * n
    hits, k, t = [], 0, 0.3
    while t < secs - 0.5:
        if k % skip != skip - 1:
            at = t + (rnd.uniform(-sway, sway) if k % 2 else 0.0)
            hits.append(at)
            i0 = int(at * rate)
            f = 110.0 if k % 2 == 0 else 220.0
            for i in range(int(0.09 * rate)):
                if i0 + i < n:
                    a[i0 + i] += (0.8 * math.exp(-i / (0.02 * rate)) * math.sin(2 * math.pi * f * i / rate)
                                  + 0.25 * math.exp(-i / (0.004 * rate)) * (rnd.random() * 2 - 1))
        k += 1
        t += 60.0 / bpm
    for i in range(n):
        a[i] += 0.04 * math.sin(2 * math.pi * 330.0 * i / rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(v * 26000)))) for v in a))
    return hits


def photos(n, marked):
    return [{"kind": "photo", "path": f"/pretend/{k + 1:02d}.jpg", "w": 4000, "h": 6000,
             "mark": ("+" if k % 3 == 0 else "-" if k % 4 == 1 else "") if marked else ""} for k in range(n)]


def a_clip():
    return {"kind": "clip", "path": "/pretend/clip.mov", "src": 2.5, "seconds": 4.0, "w": 2160, "h": 3840, "length": 60.0}


def main():
    work = Path(tempfile.mkdtemp(prefix="reel-hits-"))
    try:
        return _main(work)
    finally:
        if RESULTS["FAIL"]:
            print(f"(the scratch folder is kept: {work})")
        else:
            shutil.rmtree(work, ignore_errors=True)


def _main(work):
    studio, home = work / "studio", work / "home"
    home.mkdir()
    os.environ["STUDIO_HOME"] = str(studio)              # before reel.py is loaded: it reads this once
    env = dict(os.environ, STUDIO_HOME=str(studio), HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="utf-8")
    sys.path.insert(0, str(REEL))
    import beats_lite
    import reel
    import timing

    FPS = beats_lite.FPS

    # ------------------------------------------------------------ step 1, on made-up numbers
    print("-- step 1: the hits you can hear (made-up numbers)")

    def env_with(peaks, secs=8.0):
        """How much the sound jumps, FPS values a second: a quiet ripple (real music is never perfectly flat) with
        a jump of the given size at each given moment."""
        o = [0.1 + 0.01 * math.sin(k / 2.0) for k in range(int(secs * FPS))]
        for t, v in peaks:
            o[int(round(t * FPS))] = v
        return o

    every = [(0.5 + k, 5.0) for k in range(8)]                    # a jump every second, so every 3 s has music to stand out from
    got = timing.audible_hits(env_with(every))
    check("eight clear jumps in the sound, a second apart: eight hits, at their own moments, in time order",
          [round(t, 1) for t, _ in got] == [t for t, _ in every] and all(v == 5.0 for _, v in got), str(got))
    got = timing.audible_hits(env_with(every + [(2.0, 0.3), (4.0, 0.3)]))
    check("a small bump between them that doesn't stand out from the music around it is not a hit",
          [round(t, 1) for t, _ in got] == [t for t, _ in every], str(got))
    got = timing.audible_hits(env_with(every + [(2.0, 3.0)]))
    check("... and one that does stand out is", [round(t, 1) for t, _ in got] == sorted([t for t, _ in every] + [2.0]), str(got))
    got = timing.audible_hits(env_with(every + [(2.6, 7.0)]))
    check("two jumps a tenth of a second apart (2.5 and 2.6): one hit, the louder (never two closer than 0.2 s)",
          len(got) == 8 and [round(t, 1) for t, v in got if v == 7.0] == [2.6] and not any(abs(t - 2.5) < 0.02 for t, _ in got), str(got))
    got = timing.audible_hits(env_with(every + [(2.75, 5.0)]))
    check("two jumps a quarter of a second apart: two hits", len(got) == 9, str(got))
    check("silence, and a sound too short to judge: no hits, nothing breaks",
          timing.audible_hits([0.0] * 500) == [] and timing.audible_hits([]) == [] and timing.audible_hits([1.0, 2.0]) == [])
    # The music "either side" runs from 1.5 s before the jump up to, not counting, 1.5 s after it (hers: the far
    # end is left out). A very loud moment exactly at either end shows which values are read.
    win, at = int(timing.HIT_AROUND * FPS), int(round(4.5 * FPS))
    base = [0.1 + 0.01 * math.sin(k / 2.0) for k in range(int(9.0 * FPS))]
    base[at] = 1.0

    def is_hit(extra):
        o = list(base)
        o[extra] = 1000.0
        return any(abs(t - at / FPS) < 1e-9 for t, _ in timing.audible_hits(o))
    check("the music around a jump: the moment exactly 1.5 s before it is counted, the moment exactly 1.5 s after "
          "it is not (as hers), and one step nearer on that side is",
          is_hit(at + win) and not is_hit(at - win) and not is_hit(at + win - 1) and is_hit(at - win - 1),
          f"{is_hit(at + win)} {is_hit(at - win)} {is_hit(at + win - 1)} {is_hit(at - win - 1)}")
    check("her numbers: 0.8 standard deviations, 1.5 s either side, 0.2 s apart, a sixth of a beat, 0.09 s, 0.9",
          (timing.HIT_STANDS_OUT, timing.HIT_AROUND, timing.HIT_APART, timing.SNAP_PART, timing.SNAP_MOST, timing.W_EMPTY)
          == (0.8, 1.5, 0.2, 6, 0.09, 0.9))

    # ------------------------------------------------------------ step 2, on made-up numbers
    print("\n-- step 2: each tick onto the hit nearest it (made-up numbers)")
    T = [0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8]
    ON = timing.onto_hits(T, [0.02, 0.65, 1.3, 1.795], 0.6)       # a beat of 0.6 s: a sixth is 0.1, so 0.09 is the most
    check("a beat of 0.6 s: ticks within 0.09 s of a hit move onto it and are marked; the others stay and are marked empty",
          T == [0.02, 0.3, 0.65, 0.9, 1.2, 1.5, 1.795] and ON == [1, 0, 1, 0, 0, 0, 1], f"{T} {ON}")
    T = [0.0, 0.15, 0.3, 0.45, 0.6]
    ON = timing.onto_hits(T, [0.04, 0.36], 0.3)                    # a fast song: a sixth of a beat is 0.05 s
    check("a fast song (a beat of 0.3 s): a hit 0.04 s away moves its tick, one 0.06 s away does not (a sixth of a beat)",
          T == [0.04, 0.15, 0.3, 0.45, 0.6] and ON == [1, 0, 0, 0, 0], f"{T} {ON}")
    T = [0.0, 1.0, 2.0]
    ON = timing.onto_hits(T, [0.095, 1.089], 2.0)                  # a slow song: a sixth would be 0.33 s; 0.09 s is the most
    check("a slow song: 0.09 s is the most a tick ever moves (0.089 moves, 0.095 does not)",
          T == [0.0, 1.089, 2.0] and ON == [0, 1, 0], f"{T} {ON}")
    T = [0.0, 0.05, 0.1, 0.15]
    ON = timing.onto_hits(T, [0.07], 0.6)
    check("the grid never folds over: every tick still after the one before it", all(a < b for a, b in zip(T, T[1:])), str(T))
    check("no hits at all: nothing moves, every tick marked empty",
          timing.onto_hits([0.0, 0.5], [], 0.5) == [0, 0])

    # ------------------------------------------------------------ the loose song
    print("\n-- a loose song made here: every second beat early or late, every fifth beat silent")
    song = work / "loose song.wav"
    real = loose_song(song)

    def grid_of(path, **change):
        """The song's grid with a number of timing.py changed for this one reading (a step taken out)."""
        saved = {k: getattr(timing, k) for k in change}
        timing._GRIDS.clear()
        for k, v in change.items():
            setattr(timing, k, v)
        try:
            g, why = timing.song_grid(str(path))
        finally:
            for k, v in saved.items():
                setattr(timing, k, v)
            timing._GRIDS.clear()
        return g, why

    g, why = grid_of(song)
    plain, _ = grid_of(song, HITS_AT_LEAST=10 ** 9)                # step 2 taken out: the even grid
    ok = g is not None and plain is not None
    check("the loose song has a beat our plain-Python listening finds", ok, str(why))
    if not ok:
        return 1
    beats = list(range(0, len(g.T), 2))
    near_real = [h for h in g.hits if any(abs(h - r) <= 0.03 for r in real)]
    check(f"step 1 on the song: the hits it finds ({len(g.hits)}) are the thumps this test wrote ({len(real)}), each within "
          f"0.03 s, none made up and at most two missed",
          len(near_real) == len(g.hits) and len(real) - 2 <= len(g.hits) <= len(real), f"{len(near_real)} near, {len(g.hits)} found")
    on_beats = sum(g.ON[j] for j in beats)
    check(f"step 2 on the song: most beats sit on a hit ({on_beats} of {len(beats)}), and the silent ones are marked "
          f"empty ({len(beats) - on_beats}; every fifth beat was left silent)",
          0.7 * len(beats) <= on_beats and 0.12 * len(beats) <= len(beats) - on_beats, f"{on_beats} of {len(beats)}")
    moved = [abs(a - b) for a, b in zip(g.T, plain.T)]
    most = min(timing.SNAP_MOST, g.period / timing.SNAP_PART)
    check(f"... no tick moved by more than a sixth of a beat or 0.09 s (the most here: {max(moved):.3f} s; our listening "
          f"already follows this song's beats closely), and only marked ticks moved",
          max(moved) <= most + 1e-9 and all(m == 0 or g.ON[j] for j, m in enumerate(moved)), f"most {most:.3f}, moved {max(moved):.3f}")
    check("... every marked tick sits exactly on a hit, and the grid still runs forward",
          all(g.T[j] in g.hits for j in range(len(g.T)) if g.ON[j]) and all(a < b for a, b in zip(g.T, g.T[1:])))
    check("... without step 2 (the even grid) every tick counts as heard and there are no hits to speak of",
          set(plain.ON) == {1} and plain.hits == [])
    check("how hard the song hits at each tick is read where the even grid put it, the same with or without the move",
          g.HIT == plain.HIT and g.ENERGY == plain.ENERGY and g.P == plain.P)
    check("the grid the song's start is chosen from is the moved one (one list, as hers)", g.info["beats"] is g.T)

    def cuts_on_hits(vibe, items, **change):
        """(cuts within 60 ms of a real hit, cuts in all, the facts) for one reel on the loose song."""
        saved = {k: getattr(timing, k) for k in change}
        timing._GRIDS.clear()
        for k, v in change.items():
            setattr(timing, k, v)
        try:
            pieces, facts = reel.plan_reel(items, str(song), vibe, 0)
        finally:
            for k, v in saved.items():
                setattr(timing, k, v)
            timing._GRIDS.clear()
        if pieces is None:
            return None, None, facts
        t0 = facts["song_from"]
        cuts = [t0 + p["start"] + p["dur"] for p in pieces[:-1]]   # a cut sits on the frame at or just before its beat
        return sum(1 for c in cuts if any(-0.06 - 1 / 30 <= c - r <= 0.06 for r in real)), len(cuts), facts

    print("\n-- step 3, and all three together: every vibe, cuts within 60 ms of a hit you can hear (her measure)")
    totals = {"with": 0, "no3": 0, "no2": 0, "cuts": 0}
    worse, lines, said = [], [], []
    for label, items in (("14 photos, marked", photos(14, True)), ("10 photos, no marks", photos(10, False)),
                         ("a clip and 12 photos, marked", [a_clip()] + photos(12, True))):
        for vibe in timing.VIBES:
            w, n, facts = cuts_on_hits(vibe, items)
            no3, _, _ = cuts_on_hits(vibe, items, W_EMPTY=0.0)
            no2, _, facts2 = cuts_on_hits(vibe, items, HITS_AT_LEAST=10 ** 9)
            if None in (w, no3, no2):
                worse.append(f"{label}, {vibe}: not planned")
                continue
            totals["with"] += w
            totals["no3"] += no3
            totals["no2"] += no2
            totals["cuts"] += n
            lines.append(f"{label}, {timing.NAMES[vibe]}: {w} of {n} (without step 3: {no3}; on the plain grid: {no2})")
            if w < no2 or w < no3:
                worse.append(lines[-1])
            m = re.match(r"Real hits: (\d+) of (\d+) cuts land on a hit you can hear\.$", facts.get("real_hits_line") or "")
            if not m or int(m.group(2)) != n or not (w - 1 <= int(m.group(1)) <= n) or facts2.get("real_hits_line") is not None:
                said.append(f"{label}, {vibe}: {facts.get('real_hits_line')!r} / {facts2.get('real_hits_line')!r}")
    for ln in lines:
        print("      " + ln)
    check("in every vibe and every reel tried, at least as many cuts land on a real hit as on the plain grid, and as "
          "without step 3", not worse, "; ".join(worse))
    check(f"over all of them: {totals['with']} of {totals['cuts']} cuts on a real hit with the three steps, "
          f"{totals['no3']} with step 3 taken out, {totals['no2']} on the plain grid: clearly more with",
          totals["with"] >= totals["no3"] + 6 and totals["with"] >= totals["no2"] + 6 and totals["with"] >= 0.9 * totals["cuts"],
          str(totals))
    check("her dry-run line counts them (\"Real hits: N of M cuts land on a hit you can hear.\", the reel's end not "
          "counted), and is not said on a grid with no hits to speak of", not said, "; ".join(said))

    its = photos(14, True)
    g, _ = grid_of(song)
    timing._GRIDS.clear()
    seed = timing.seed_for(its, "mixed")
    holds = timing.plan_holds(its, g, "mixed", seed, 0, len(g.T) - 2)
    saved, g.ON = g.ON, [1] * len(g.T)
    holds_plain = timing.plan_holds(its, g, "mixed", seed, 0, len(g.T) - 2)
    g.ON = [0] * len(g.T)
    holds_none = timing.plan_holds(its, g, "mixed", seed, 0, len(g.T) - 2)
    g.ON = saved

    def empties(hs):
        e, n = 0, 0
        for h in hs[:-1]:
            e += h
            n += 0 if g.ON[e] else 1
        return n
    timing._GRIDS.clear()
    _, one = reel.plan_reel(photos(1, False), str(song), "beat", 0)
    timing._GRIDS.clear()
    check("a reel of one photo has no cut to count, so the line is not said (hers would say \"0 of 0\")",
          one.get("real_hits_line") is None and one.get("beats_line", "").startswith("Beats per piece: "), str(one)[:200])
    check(f"the one search itself, same grid, A little of everything: {empties(holds)} cuts on a beat with no hit "
          f"when empty beats cost 0.9, {empties(holds_plain)} when they cost nothing",
          holds is not None and holds_plain is not None and empties(holds) < empties(holds_plain), f"{holds} / {holds_plain}")
    check("when no beat has a hit (or every one does) the cost is the same everywhere, so the plan is the plain one",
          holds_none == holds_plain)

    # ------------------------------------------------------------ step 2 on an even grid
    # Her case in one picture: "Every vibe placed cuts on an evenly spaced beat grid. On a song with a loose beat, the
    # ticks drift off what you hear." Our own listening follows this made-up song's beats closely, so here the song
    # is given a perfectly even grid (what a beat list from elsewhere, CapCut's for one, can be) and the ticks have
    # to move to reach the thumps. Counted tightly: a cut within 20 ms of a real thump (and a frame early at most).
    print("\n-- step 2 where it shows: the same loose song under a perfectly even grid")
    real_analyze, real_onto = beats_lite.analyze, timing.onto_hits

    def even_analyze(path, beat_file=None, keep_onset=False):
        i = dict(real_analyze(path, beat_file, keep_onset))
        if i.get("ok"):
            i["beats"] = [round(i["beats"][0] + k * 0.6, 3) for k in range(len(i["beats"]))]
            i["period"] = 0.6
        return i

    def marks_only(T, hit_times, period, move=True):               # step 2 taken out: the marks, but no tick moved
        return real_onto(list(T), hit_times, period)

    def tight(vibe, items, move=True):
        timing._GRIDS.clear()
        beats_lite.analyze, timing.onto_hits = even_analyze, (real_onto if move else marks_only)
        try:
            pieces, facts = reel.plan_reel(items, str(song), vibe, 0)
            grid, _ = timing.song_grid(str(song))
        finally:
            beats_lite.analyze, timing.onto_hits = real_analyze, real_onto
            timing._GRIDS.clear()
        if pieces is None:
            return None, None, grid
        t0 = facts["song_from"]
        cuts = [t0 + p["start"] + p["dur"] for p in pieces[:-1]]
        return sum(1 for c in cuts if any(-0.02 - 1 / 30 <= c - r <= 0.02 for r in real)), len(cuts), grid
    tot, worse, lines = {"with": 0, "without": 0, "cuts": 0}, [], []
    eg = None
    for label, items in (("14 photos, marked", photos(14, True)), ("10 photos, no marks", photos(10, False))):
        for vibe in timing.VIBES:
            w, n, eg = tight(vibe, items)
            wo, _, flat = tight(vibe, items, move=False)
            if w is None or wo is None:
                worse.append(f"{label}, {vibe}: not planned")
                continue
            tot["with"] += w
            tot["without"] += wo
            tot["cuts"] += n
            lines.append(f"{label}, {timing.NAMES[vibe]}: {w} of {n} right on a thump (ticks not moved: {wo})")
            if w < wo:
                worse.append(lines[-1])
    for ln in lines:
        print("      " + ln)
    moved = [abs(a - b) for a, b in zip(eg.T, flat.T)] if eg and flat else [0]
    check(f"under the even grid the ticks really move (the most by {max(moved):.3f} s; {sum(m > 0.02 for m in moved)} by "
          f"more than 0.02 s), never by more than a sixth of a beat or 0.09 s",
          0.03 < max(moved) <= min(timing.SNAP_MOST, 0.6 / timing.SNAP_PART) + 1e-9 and sum(m > 0.02 for m in moved) >= 5, str(max(moved)))
    check(f"every vibe: at least as many cuts right on a thump with the ticks moved, and more over all "
          f"({tot['with']} of {tot['cuts']} against {tot['without']})",
          not worse and tot["with"] >= tot["without"] + 5 and tot["with"] >= 0.9 * tot["cuts"], f"{tot}; {worse}")

    # ------------------------------------------------------------ frames
    print("\n-- CapCut's times stay on whole frames (the October lesson)")
    bad = []
    for vibe in timing.VIBES:
        timing._GRIDS.clear()
        pieces, facts = reel.plan_reel([a_clip()] + photos(12, True), str(song), vibe, 0)
        if pieces is None:
            bad.append(f"{vibe}: {facts}")
            continue
        at = 0
        for p in pieces:
            if not (isinstance(p["start_f"], int) and isinstance(p["dur_f"], int) and p["start_f"] == at and p["dur_f"] >= 1):
                bad.append(f"{vibe}: {p}")
            at += p["dur_f"]
        if any(not (-1e-9 <= e < 1 / 30 + 1e-9) for e in facts["cut_early_by"]) or not isinstance(facts["song_from_f"], int):
            bad.append(f"{vibe}: early by {facts['cut_early_by']}")
        if any(not isinstance(b, int) or b < 1 for b in facts["beats"]):
            bad.append(f"{vibe}: beats {facts['beats']}")
    check("on the loose song, every vibe: each piece starts on a whole frame where the one before ended, every cut on "
          "the frame at or just before its (moved) beat, never after, and every hold a whole number of beats", not bad, "; ".join(bad[:3]))

    # ------------------------------------------------------------ the steady test beat
    print("\n-- the steady 60-second test beat")
    timing._GRIDS.clear()
    g60, _ = timing.song_grid(str(BEAT60))
    p60, _ = grid_of(BEAT60, HITS_AT_LEAST=10 ** 9)
    timing._GRIDS.clear()
    moved = [abs(a - b) for a, b in zip(g60.T, p60.T)]
    b60 = list(range(0, len(g60.T), 2))
    check(f"its ticks move a few hundredths of a second at the most ({max(moved):.3f} s), and most of its beats sit on "
          f"a hit ({sum(g60.ON[j] for j in b60)} of {len(b60)}); her 9 lines on it are unchanged (reel_timing_check.py)",
          max(moved) <= min(timing.SNAP_MOST, g60.period / timing.SNAP_PART) + 1e-9 and sum(g60.ON[j] for j in b60) >= 0.6 * len(b60),
          f"{max(moved)}; {sum(g60.ON[j] for j in b60)} of {len(b60)}")

    # ------------------------------------------------------------ too few hits
    print("\n-- a song with too few hits to tell")
    few, _ = grid_of(song, HIT_STANDS_OUT=50.0)                  # nothing stands out that far: under eight hits
    check("fewer than eight hits: the plain grid, exactly, every tick counted as heard (as hers)",
          few is not None and few.T == plain.T and set(few.ON) == {1} and few.hits == [] and timing.HITS_AT_LEAST == 8)

    # ------------------------------------------------------------ no song
    print("\n-- \"No song\" works in every vibe (her v25 fix)")
    bad = []
    for label, items in (("photos only", photos(12, True)), ("a clip and photos", [a_clip()] + photos(10, False)),
                         ("one photo", photos(1, False))):
        for vibe in timing.VIBES:
            try:
                pieces, facts = reel.plan_reel(items, None, vibe)
            except Exception as e:                                # her crash was a name used before it was set
                bad.append(f"{label}, {vibe}: {type(e).__name__}: {e}")
                continue
            if (pieces is None or len(pieces) != len(items) or facts.get("real_hits_line") is not None
                    or any(not isinstance(b, int) or b < 1 for b in facts["beats"])):
                bad.append(f"{label}, {vibe}: {facts}")
    even = timing.even_grid()
    check("no song, every vibe, photos only, with a clip, and one photo alone: planned, nothing left out, whole beats, "
          "and no line about hits", not bad, "; ".join(bad[:3]))
    check("the even grid with no song: every tick counts as heard, so nothing costs extra anywhere",
          set(even.ON) == {1} and len(even.ON) == len(even.T) and even.hits == [])

    # ------------------------------------------------------------ the chat's reel maker
    print("\n-- reel.py make --dry-run (the reel maker the chat runs) goes through the same steps")
    folder = work / "photos"
    folder.mkdir()
    listing = []
    for n in range(1, 15):
        (folder / f"{n:02d}.jpg").write_bytes(b"pretend photo")
        listing.append({"n": n, "file": str(folder / f"{n:02d}.jpg"), "w": 4000, "h": 6000})
    wd = studio / "reels" / "Pretend"
    wd.mkdir(parents=True)
    import json
    (wd / "photos.json").write_text(json.dumps({"folder": str(folder), "photos": listing}), encoding="utf-8")
    picks = "1+,2-,3,4+,5,6-,7+,8,9,10+,11-,12,13,14+"

    def run(song_arg, vibe):
        r = subprocess.run([sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(folder),
                            "--shoot", "Pretend", "--picks", picks, "--vibe", vibe, "--song", str(song_arg),
                            "--song-start", "0"] if song_arg != "none" else
                           [sys.executable, str(REEL / "reel.py"), "make", "--dry-run", "--folder", str(folder),
                            "--shoot", "Pretend", "--picks", picks, "--vibe", vibe, "--song", "none"],
                           capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=300)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    bad, seen = [], []
    for vibe in timing.VIBES:
        code, out = run(song, vibe)
        m = re.search(r"^Real hits: (\d+) of 13 cuts land on a hit you can hear\.$", out, re.M)
        if code != 0 or not m or int(m.group(1)) < 11 or "Beats per piece: " not in out:
            bad.append(f"{vibe}: exit {code}: {out[-300:]}")
        else:
            seen.append(f"{timing.NAMES[vibe]} {m.group(1)} of 13")
        lines_ = out.splitlines()
        if m and not (lines_.index(m.group(0)) < next(k for k, x in enumerate(lines_) if x.startswith("Beats per piece"))):
            bad.append(f"{vibe}: the Real hits line comes after the beats line")
    check("on the loose song, every vibe: her line \"Real hits: N of 13 cuts land on a hit you can hear.\" with 11 or more "
          "of 13 (" + "; ".join(seen) + "), before the beats line", not bad, "; ".join(bad[:2]))
    bad = []
    for vibe in timing.VIBES:
        code, out = run("none", vibe)
        if code != 0 or "Real hits" in out or "Beats per piece: " not in out or "Traceback" in out:
            bad.append(f"{vibe}: exit {code}: {out[-300:]}")
    check("with no song, every vibe: a plan, her beats line, and nothing said about hits", not bad, "; ".join(bad[:2]))

    # ------------------------------------------------------------ a song from CapCut's own music
    print("\n-- a song from CapCut's own music: CapCut's beat marks stay where CapCut put them")
    import json
    marks = [300 + 600 * k for k in range(48)]                 # CapCut's list: perfectly even, in thousandths of a second
    beat_file = work / "capcut beats.json"
    beat_file.write_text(json.dumps({"time": marks, "value": [(k % 4) + 1 for k in range(48)]}), encoding="utf-8")

    def capcut_grid(**change):
        saved = {k: getattr(timing, k) for k in change}
        timing._GRIDS.clear()
        for k, v in change.items():
            setattr(timing, k, v)
        try:
            return timing.song_grid(str(song), str(beat_file))[0]
        finally:
            for k, v in saved.items():
                setattr(timing, k, v)
            timing._GRIDS.clear()
    cg, moved_g = capcut_grid(), capcut_grid(ON_CAPCUT_MARKS=False)
    cb = list(range(0, len(cg.T), 2))
    check("its beats are CapCut's own, to the thousandth of a second: not one moved, and the grid runs forward",
          cg.beats_from == "capcut" and [round(cg.T[j] * 1000) for j in cb] == marks
          and all(abs(cg.T[j] - marks[n] / 1000.0) < 1e-9 for n, j in enumerate(cb)) and all(a < b for a, b in zip(cg.T, cg.T[1:])),
          str([round(cg.T[j], 4) for j in cb][:8]))
    check(f"... the marks with a hit within reach are marked as heard ({sum(cg.ON[j] for j in cb)} of {len(cb)}), the "
          f"silent ones as empty, and the hits are kept for the Real hits line",
          0.6 * len(cb) <= sum(cg.ON[j] for j in cb) < len(cb) and len(cg.hits) >= timing.HITS_AT_LEAST,
          f"{sum(cg.ON[j] for j in cb)} of {len(cb)}, {len(cg.hits)} hits")
    drift = [abs(a - b) for a, b in zip(moved_g.T, cg.T)]
    check(f"... the same marks as when the ticks do move (the switch, ON_CAPCUT_MARKS, off: {sum(d > 1e-9 for d in drift)} "
          f"ticks move, the most by {max(drift):.3f} s), so only the moving is left out",
          moved_g.ON == cg.ON and sum(d > 1e-9 for d in drift) >= 10 and timing.ON_CAPCUT_MARKS is True,
          f"{sum(d > 1e-9 for d in drift)} moved")
    T = [0.0, 0.3, 0.6, 0.9, 1.2]
    check("step 2 asked only to mark: the same marks, and no tick moves",
          timing.onto_hits(T, [0.05, 0.58, 1.0], 0.6, move=False) == timing.onto_hits([0.0, 0.3, 0.6, 0.9, 1.2], [0.05, 0.58, 1.0], 0.6)
          and T == [0.0, 0.3, 0.6, 0.9, 1.2])
    bad, seen = [], []
    for vibe in timing.VIBES:
        timing._GRIDS.clear()
        pieces, facts = reel.plan_reel(photos(14, True), str(song), vibe, None, beat_file=str(beat_file))
        m = re.match(r"Real hits: (\d+) of 13 cuts land on a hit you can hear\.$", (facts or {}).get("real_hits_line") or "")
        if not pieces or len(pieces) != 14 or not m:
            bad.append(f"{vibe}: {str(facts)[:200]}")
            continue
        seen.append(f"{timing.NAMES[vibe]} {m.group(1)} of 13")
        g2 = timing.song_grid(str(song), str(beat_file))[0]
        if [round(g2.T[j] * 1000) for j in range(0, len(g2.T), 2)] != marks:
            bad.append(f"{vibe}: the beats moved off CapCut's marks")
    timing._GRIDS.clear()
    check("every vibe plans on it, all 14 photos, with her Real hits line (" + "; ".join(seen) + ")", not bad, "; ".join(bad[:2]))

    # ------------------------------------------------------------ words, and plain Python
    print("\n-- the page's words, and plain Python")
    sys.path.insert(0, str(MANAGER))
    import reel_page
    hers = "Some quick, some longer, and every change lands on a beat you can hear in your song."
    check("the reel page's line under A little of everything is hers (v25), word for word, and the line it replaced is gone",
          reel_page.WORDS.get("vibe_mixed_s") == hers
          and "changing where the music turns over" not in (MANAGER / "reel_page.py").read_text(encoding="utf-8"),
          str(reel_page.WORDS.get("vibe_mixed_s")))
    check("... no dash of the long kind in it, and it never says Claude", "—" not in hers and "Claude" not in hers)
    src = (REEL / "timing.py").read_text(encoding="utf-8")
    imports = sorted(set(re.findall(r"^(?:import|from)\s+(\w+)", src, re.M)))
    check("timing.py reads the song only through our own plain-Python listening: it imports nothing but Python's own "
          "parts and beats_lite, and runs nothing (no numpy, no ffmpeg)",
          imports == ["beats_lite", "math", "os", "random", "zlib"] and "subprocess" not in src and "numpy" not in src, str(imports))
    check("her hit-to-hit cutting (HITGRID), which she tried and left switched off, is not built",
          "def plan_hits" not in src and "HITGRID = " not in src)

    print(f"\n{RESULTS['PASS']} passed, {RESULTS['FAIL']} failed.")
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
