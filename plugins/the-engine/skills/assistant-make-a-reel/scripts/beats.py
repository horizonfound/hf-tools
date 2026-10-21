#!/usr/bin/env python3
"""The Assistant by Horizon Found. Finds the beats in a song so a reel can cut on them.

Usage:
  python3 beats.py song.m4a            prints tempo and beat times
  python3 beats.py song.m4a --json     prints JSON {tempo, beats, duration}

Needs only ffmpeg/ffprobe, Python 3 and numpy. No installs.
"""
import json, os, shutil, subprocess, sys, tempfile

import numpy as np

SR = 16000
HOP = 320  # 20 ms


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration_of(path):
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def load_mono(path):
    """Decode any audio or video file to 16 kHz mono float32 via ffmpeg."""
    tmp = tempfile.NamedTemporaryFile(suffix=".raw", delete=False)
    tmp.close()
    r = _run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn", "-f", "s16le", "-ac", "1", "-ar", str(SR), tmp.name])
    if r.returncode != 0 or not os.path.exists(tmp.name) or os.path.getsize(tmp.name) == 0:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return None
    a = np.fromfile(tmp.name, dtype=np.int16).astype(np.float32) / 32768.0
    os.unlink(tmp.name)
    return a


def onsets(a, min_gap=0.25):
    """Onset times (s) from a positive-difference energy envelope. Simple and dependable on pop and acoustic tracks."""
    n = (len(a) - HOP) // HOP
    if n < 10:
        return []
    env = np.sqrt(np.mean(a[: n * HOP].reshape(n, HOP) ** 2, axis=1))
    env = np.log1p(env * 50)
    d = np.diff(env)
    d[d < 0] = 0
    if d.std() == 0:
        return []
    thr = d.mean() + 1.8 * d.std()
    peaks = []
    last = -1.0
    for i in range(1, len(d) - 1):
        if d[i] > thr and d[i] >= d[i - 1] and d[i] >= d[i + 1]:
            t = (i + 1) * HOP / SR
            if t - last >= min_gap:
                peaks.append(round(t, 3))
                last = t
    return peaks


def tempo_from(times):
    """Median inter-onset interval folded into 60 to 180 bpm. Returns (bpm, beat_period_seconds)."""
    if len(times) < 4:
        return 0.0, 0.0
    gaps = np.diff(times)
    gaps = gaps[(gaps > 0.2) & (gaps < 2.0)]
    if len(gaps) == 0:
        return 0.0, 0.0
    per = float(np.median(gaps))
    bpm = 60.0 / per
    while bpm < 60:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    return round(bpm, 1), 60.0 / bpm


def beat_grid(times, period, duration):
    """Lay a steady grid at the detected period, phase-locked to the strongest run of onsets, so every beat exists
    even where the track is quiet. Returns beat times (s)."""
    if period <= 0 or not times:
        return []
    # choose the phase that lines up with the most onsets
    best_phase, best_hits = 0.0, -1
    for t in times[:40]:
        phase = t % period
        hits = sum(1 for x in times if abs(((x - phase) / period) - round((x - phase) / period)) * period < 0.06)
        if hits > best_hits:
            best_phase, best_hits = phase, hits
    beats = []
    t = best_phase
    while t < duration:
        if t >= 0:
            beats.append(round(t, 3))
        t += period
    return beats


def analyze(path):
    dur = duration_of(path)
    a = load_mono(path)
    if a is None or dur <= 0:
        return {"ok": False, "reason": "could not read the audio", "duration": dur, "tempo": 0, "beats": [], "onsets": []}
    ons = onsets(a)
    bpm, period = tempo_from(ons)
    grid = beat_grid(ons, period, dur) if period else []
    return {"ok": bool(grid), "duration": round(dur, 3), "tempo": bpm, "period": round(period, 4) if period else 0,
            "beats": grid, "onsets": ons}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    if not shutil.which("ffmpeg"):
        print("ffmpeg is not available here, so I can't read the song.")
        sys.exit(1)
    res = analyze(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(res))
    else:
        if not res["ok"]:
            print("No steady beat found:", res.get("reason", "the track may be too quiet or too free-form"))
            sys.exit(1)
        print(f"{res['duration']:.1f} s · tempo ~{res['tempo']:.0f} bpm · {len(res['beats'])} beats")
        print(" ".join(f"{b:.2f}" for b in res["beats"][:40]) + (" ..." if len(res["beats"]) > 40 else ""))
