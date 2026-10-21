#!/usr/bin/env python3
"""The Assistant by Horizon Found: grades a finished reel the way a picky editor would.

Reads one short vertical reel (mp4/mov) with ffmpeg + numpy and checks the things a viewer notices:
  - do the cuts land on the beat (against the song's own beat grid when the plan is next to the file,
    otherwise against beats heard in the reel's audio)
  - does the opening hold long enough
  - does the sound click, pop, clip or distort anywhere
  - do the photos move smoothly, or do they jitter
  - is the on-screen text readable against what is behind it
PASS exits 0, FAIL exits 1, a broken file exits 2. Taste is not graded; that is the photographer's call.

    python3 grade_reel.py reel.mp4 [--json out.json] [--fps-tolerance 2]
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SMALL_W, SMALL_H = 72, 128        # cut detection resolution
AUDIO_SR, HOP = 16000, 320        # 20 ms hops
FULL_W, FULL_H = 1080, 1920


def run(cmd):
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def probe(path):
    out = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    video = next((s for s in out["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError("no video stream found")
    num, den = video["r_frame_rate"].split("/")
    return {
        "duration": float(out["format"]["duration"]),
        "width": int(video["width"]), "height": int(video["height"]),
        "fps": float(num) / float(den or 1),
        "has_audio": any(s["codec_type"] == "audio" for s in out["streams"]),
    }


def decode_gray(path, w, h, start=None, seconds=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", path]
    if seconds:
        cmd += ["-t", f"{seconds:.3f}"]
    cmd += ["-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = np.frombuffer(run(cmd), dtype=np.uint8)
    return raw[: len(raw) // (w * h) * w * h].reshape(-1, h, w)


def find_cuts(frames, fps):
    """Mean absolute frame difference; a cut is a spike above mean + 3*std."""
    if len(frames) < 3:
        return []
    diff = np.abs(frames[1:].astype(np.int16) - frames[:-1].astype(np.int16)).mean(axis=(1, 2))
    thresh = diff.mean() + 3 * diff.std()
    cuts, last = [], -99
    for i in np.flatnonzero(diff > thresh):
        if i - last >= 8:
            cuts.append(round((i + 1) / fps, 3))
        last = i
    return cuts


def find_onsets(path):
    """Beats heard in the reel's own audio: RMS envelope, positive difference, peaks above mean + 2*std."""
    pcm = np.frombuffer(run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-f", "s16le",
                             "-ac", "1", "-ar", str(AUDIO_SR), "-"]), dtype=np.int16)
    if len(pcm) < 2 * HOP:
        return [], None
    n = len(pcm) // HOP
    rms = np.sqrt((pcm[: n * HOP].astype(np.float64) ** 2).reshape(n, HOP).mean(axis=1))
    strength = np.maximum(np.diff(rms), 0)
    thresh = strength.mean() + 2 * strength.std()
    gap = int(0.25 / (HOP / AUDIO_SR))
    onsets = []
    for i in np.argsort(strength)[::-1]:
        if strength[i] <= thresh:
            break
        t = (i + 1) * HOP / AUDIO_SR
        if all(abs(t - o) >= gap * HOP / AUDIO_SR for o in onsets):
            onsets.append(round(t, 3))
    onsets.sort()
    bpm = None
    if len(onsets) >= 4:
        beat = float(np.median(np.diff(onsets)))
        while beat and 60 / beat > 180:
            beat *= 2
        while beat and 60 / beat < 60:
            beat /= 2
        bpm = round(60 / beat) if beat else None
    return onsets, bpm


def beats_from_plan(path):
    """If the reel sits in <session>/_assistant/reel-x/ next to its plan, grade against the song's real beat grid."""
    folder = Path(path).resolve().parent
    plan_file = folder / "plan.json"
    if not plan_file.exists():
        return None, None, None
    try:
        plan = json.loads(plan_file.read_text())
        import beats as beatlib
        song = plan.get("song")
        if not song:
            return None, None, plan
        session = folder.parent.parent
        song_path = session / song
        if not song_path.exists():
            return None, None, plan
        info = beatlib.analyze(song_path)
        if not info.get("ok"):
            return None, None, plan
        start = float(plan.get("song_start") or 0.0)
        grid = [round(b - start, 3) for b in info["beats"] if b - start >= -0.001]
        return grid, info.get("tempo"), plan
    except Exception:
        return None, None, None


def align(cuts, beats, fps, tol):
    rows = []
    for c in cuts:
        if not beats:
            rows.append({"cut": c, "beat": None, "frames_off": None, "ok": False})
            continue
        b = min(beats, key=lambda o: abs(o - c))
        off = int(round((c - b) * fps))
        rows.append({"cut": c, "beat": b, "frames_off": off, "ok": abs(off) <= tol})
    return rows


def audio_health(path):
    """Peak level, clipping, and clicks (sample-to-sample jumps a real signal never makes)."""
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "2", "-ar", "48000", "-"])
    st = np.frombuffer(raw, dtype=np.float32)
    st = st[: len(st) // 2 * 2].reshape(-1, 2)
    if len(st) < 4800:
        return {"peak_dbfs": None, "clipped_samples": 0, "clicks_s": [], "silent": True}
    peak = float(np.abs(st).max())
    clipped = int((np.abs(st) >= 0.999).sum())
    a = st.mean(axis=1)
    d = np.abs(np.diff(a))
    idx = np.flatnonzero(d > 0.25)
    # a click is a rare, isolated jump; a second full of jumps is just a harsh, distorted track and not our doing
    per_sec = np.bincount((idx // 48000).astype(int)) if len(idx) else np.zeros(1, dtype=int)
    clicks, last = [], -1.0
    for i in idx:
        sec = int(i // 48000)
        if sec < len(per_sec) and per_sec[sec] > 6:
            continue
        t = i / 48000
        if t - last > 0.05:
            clicks.append(round(t, 2))
        last = t
    return {"peak_dbfs": round(20 * np.log10(peak + 1e-9), 1), "clipped_samples": clipped, "clicks_s": clicks[:20],
            "silent": peak < 0.001}


def _subpix_shift(a, b):
    a = a - a.mean(); b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    FA = np.fft.fft2(a * win); FB = np.fft.fft2(b * win)
    R = FA * np.conj(FB); R /= np.abs(R) + 1e-9
    r = np.fft.fftshift(np.fft.ifft2(R).real)
    cy, cx = np.unravel_index(np.argmax(r), r.shape)

    def para(m1, m0, p1):
        den = 2 * (m1 - 2 * m0 + p1)
        return (m1 - p1) / den if abs(den) > 1e-9 else 0.0
    dy = cy - r.shape[0] // 2 + (para(r[cy - 1, cx], r[cy, cx], r[cy + 1, cx]) if 0 < cy < r.shape[0] - 1 else 0)
    dx = cx - r.shape[1] // 2 + (para(r[cy, cx - 1], r[cy, cx], r[cy, cx + 1]) if 0 < cx < r.shape[1] - 1 else 0)
    return dx, dy


def motion_smoothness(path, start, seconds):
    """How evenly things move inside one hold. Tracks the six most textured patches frame to frame with sub-pixel
    phase correlation; reports the median frame-to-frame change in speed (px/frame). Smooth motion is under 0.15;
    the old zoom filter scored about 0.7 and looked jittery. None when the hold is too short or nothing moves."""
    n = int(seconds * 30)
    if n < 12:
        return None
    f = decode_gray(path, FULL_W, FULL_H, start, seconds).astype(np.float32)
    if len(f) < 12:
        return None
    H, W = f.shape[1:]
    S = 192
    cands = []
    for y in range(120, H - S - 120, 160):
        for x in range(60, W - S - 60, 140):
            if abs(x + S / 2 - W / 2) < 150 and abs(y + S / 2 - H * 0.4) < 200:
                continue
            cands.append((f[0][y:y + S, x:x + S].std(), y, x))
    cands.sort(reverse=True)
    pts = [(y, x) for sd, y, x in cands[:6] if sd > 6]
    if len(pts) < 3:
        return None
    rows = np.array([[_subpix_shift(f[i - 1][y:y + S, x:x + S], f[i][y:y + S, x:x + S]) for (y, x) in pts]
                     for i in range(1, len(f))])
    mag = np.sqrt((rows ** 2).sum(axis=2))
    if mag.mean() < 0.15:
        return {"speed": round(float(mag.mean()), 2), "jitter": 0.0, "still": True}
    d = np.abs(np.diff(mag, axis=0))
    return {"speed": round(float(mag.mean()), 2), "jitter": round(float(np.median(d.mean(axis=0))), 3), "still": False}


def text_legibility(path, plan_folder, hook_end):
    """Contrast between the on-screen text and what sits behind it, measured on the finished frame."""
    hook_png = plan_folder / "work" / "hook.png" if plan_folder else None
    if not hook_png or not hook_png.exists() or not hook_end:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    mask = np.asarray(Image.open(hook_png).convert("RGBA"))[:, :, 3]
    t = max(0.05, hook_end * 0.5)
    frame = decode_gray(path, FULL_W, FULL_H, t, 0.1)
    if len(frame) == 0:
        return None
    g = frame[0].astype(np.float32) / 255.0
    text = mask > 200
    if text.sum() < 200:
        return None
    ys, xs = np.nonzero(text)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    box = np.zeros_like(text)
    box[max(0, y0 - 24):y1 + 24, max(0, x0 - 24):x1 + 24] = True
    around = box & (mask < 120)   # the frame beside the letters, scrim included, with no letter in it
    lt, lb = float(g[text].mean()), float(g[around].mean())
    lt, lb = lt ** 2.2, lb ** 2.2  # roughly linear light, like the WCAG ratio
    ratio = (max(lt, lb) + 0.05) / (min(lt, lb) + 0.05)
    return {"contrast": round(ratio, 1), "band_pct": [round(100 * y0 / FULL_H), round(100 * y1 / FULL_H)]}


def grade(path, tol):
    info = probe(path)
    fps = info["fps"]
    cuts = find_cuts(decode_gray(path, SMALL_W, SMALL_H), fps)
    grid, tempo, plan = beats_from_plan(path)
    source = "song's beat grid"
    if grid:
        beats = grid
    else:
        beats, tempo = find_onsets(path) if info["has_audio"] else ([], None)
        source = "beats heard in the reel"
    rows = align(cuts, beats, fps, tol)
    first_shot_end = cuts[0] if cuts else info["duration"]
    bounds = [0.0] + cuts + [info["duration"]]
    holds = [round(b - a, 2) for a, b in zip(bounds[:-1], bounds[1:])]

    audio = audio_health(path) if info["has_audio"] else None

    # motion: every hold of 0.8 s or more, measured in its middle 80%
    motion = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a >= 0.8:
            m = motion_smoothness(path, a + (b - a) * 0.1, (b - a) * 0.8)
            if m:
                m["at"] = round(a, 2)
                motion.append(m)
    plan_folder = Path(path).resolve().parent if plan else None
    hook_end = float(plan.get("hook_end") or 0) if plan else (first_shot_end if cuts else 0)
    text = text_legibility(path, plan_folder, hook_end)

    problems = []
    if not cuts:
        problems.append("no hard cuts found (one continuous shot)")
    if not beats:
        problems.append("no music beats found" + ("" if info["has_audio"] else " (no audio track)"))
    off = [r for r in rows if not r["ok"]]
    if cuts and beats and off:
        problems.append(f"{len(off)} of {len(cuts)} cuts land more than {tol} frames from a beat: "
                        + ", ".join(f"{r['cut']:.2f}s ({r['frames_off']:+d}f)" for r in off))
    opens_on_clip = (plan["segments"][0]["kind"] == "clip") if (plan and plan.get("segments")) else True
    if opens_on_clip and first_shot_end < 2.5:
        problems.append(f"opening only holds {first_shot_end:.2f} s (needs 2.5 s or more)")
    if plan and plan.get("hook_text") and 0 < hook_end < 2.5:
        problems.append(f"the hook text only holds {hook_end:.2f} s (needs 2.5 s or more to read)")
    if audio:
        if audio["silent"]:
            problems.append("the audio track is silent")
        if audio["clipped_samples"] > 20:
            problems.append(f"audio clips (distorts) in {audio['clipped_samples']} samples, peak {audio['peak_dbfs']} dBFS")
        if audio["clicks_s"]:
            problems.append("audio clicks or pops at " + ", ".join(f"{t:.2f}s" for t in audio["clicks_s"][:6]))
    jittery = [m for m in motion if not m["still"] and m["jitter"] > 0.25]
    if jittery:
        problems.append("photo motion jitters at " + ", ".join(f"{m['at']:.2f}s ({m['jitter']:.2f} px/frame)" for m in jittery[:6]))
    if text and text["contrast"] < 3.0:
        problems.append(f"on-screen text is hard to read: contrast {text['contrast']}:1 against what is behind it (wants 3:1 or more)")

    return {
        "file": path, "duration_s": round(info["duration"], 2), "size": f"{info['width']}x{info['height']}",
        "fps": round(fps, 3), "tolerance_frames": tol, "cuts_s": cuts, "shot_count": len(cuts) + 1,
        "hold_lengths_s": holds, "beats_s": beats, "beats_source": source, "tempo_bpm": tempo, "alignment": rows,
        "hook_hold_s": round(first_shot_end, 2), "audio": audio, "motion": motion, "text": text,
        "problems": problems, "grade": "PASS" if not problems else "FAIL",
    }


def report(r):
    ok = sum(1 for a in r["alignment"] if a["ok"])
    n = len(r["cuts_s"])
    parts = [f"{n} cuts · {ok} of {n} within {r['tolerance_frames']} frames of a beat ({r['beats_source']})" if n else "no cuts",
             f"tempo ~{r['tempo_bpm']:.0f} bpm" if r["tempo_bpm"] else "no beats found",
             f"opening held {r['hook_hold_s']:.2f} s"]
    print(f"{r['file']}\n{r['size']} · {r['fps']:g} fps · {r['duration_s']} s · {r['shot_count']} shot{'s' if r['shot_count'] != 1 else ''}")
    print(" · ".join(parts))
    a = r["audio"]
    if a:
        print(f"sound: peak {a['peak_dbfs']} dBFS · {'no clipping' if a['clipped_samples'] <= 20 else str(a['clipped_samples']) + ' clipped samples'} · "
              + ("no clicks" if not a["clicks_s"] else "clicks at " + ", ".join(f"{t:.2f}s" for t in a["clicks_s"][:6])))
    else:
        print("sound: none")
    moving = [m for m in r["motion"] if not m["still"]]
    if moving:
        worst = max(m["jitter"] for m in moving)
        print(f"motion: {len(moving)} moving holds · smoothness {worst:.2f} px/frame at worst ({'smooth' if worst <= 0.25 else 'jittery'}; under 0.25 is smooth)")
    elif r["motion"]:
        print("motion: photos hold still")
    t = r["text"]
    if t:
        print(f"text: {t['band_pct'][0]}-{t['band_pct'][1]}% down the frame · contrast {t['contrast']}:1 ({'readable' if t['contrast'] >= 3 else 'hard to read'})")
    print(f"shot holds (s): {', '.join(f'{h:.2f}' for h in r['hold_lengths_s'])}")
    if r["beats_s"]:
        print(f"beats (s): {', '.join(f'{o:.2f}' for o in r['beats_s'][:40])}" + (" ..." if len(r["beats_s"]) > 40 else ""))
    if r["alignment"]:
        print(f"\n{'cut (s)':>8} {'beat (s)':>9} {'offset':>7}  result")
        for al in r["alignment"]:
            beat = f"{al['beat']:.2f}" if al["beat"] is not None else "-"
            offs = f"{al['frames_off']:+d}f" if al["frames_off"] is not None else "-"
            print(f"{al['cut']:>8.2f} {beat:>9} {offs:>7}  {'OK' if al['ok'] else 'off'}")
    print(f"\nGRADE: {r['grade']}")
    for p in r["problems"]:
        print(f"  - {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file"); ap.add_argument("--json"); ap.add_argument("--fps-tolerance", type=int, default=2)
    a = ap.parse_args()
    try:
        r = grade(a.file, a.fps_tolerance)
    except (subprocess.CalledProcessError, ValueError, OSError, KeyError) as e:
        detail = e.stderr.decode(errors="ignore").strip() if getattr(e, "stderr", None) else str(e)
        print(f"ERROR: could not read {a.file}: {detail}", file=sys.stderr)
        return 2
    report(r)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(r, fh, indent=2)
    return 0 if r["grade"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
