#!/usr/bin/env python3
"""The Assistant by Horizon Found: grades a reel's cuts against its beats.

Reads one short vertical reel (mp4/mov), finds every hard cut and every
music beat with ffmpeg + numpy, and reports like an editor would: are the
cuts on the beat, does the hook hold long enough, and is the caption text
clear of the face. PASS exits 0, FAIL exits 1, a broken file exits 2.

    python3 grade_reel.py reel.mp4 [--json out.json] [--fps-tolerance 2]
"""
import argparse, json, subprocess, sys
import numpy as np

try:
    import cv2
except ImportError:  # OpenCV is optional; only the face check needs it
    cv2 = None

SMALL_W, SMALL_H = 72, 128        # cut detection resolution
TEXT_W, TEXT_H = 180, 320         # text / face detection resolution
AUDIO_SR, HOP = 16000, 320        # 20 ms hops


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


def decode_gray(path, w, h, seconds=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
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
        if i - last >= 8:                 # merge spikes closer than 8 frames
            cuts.append(round((i + 1) / fps, 3))
        last = i
    return cuts


def find_onsets(path):
    """RMS envelope, positive difference, peaks above mean + 2*std, 250 ms apart."""
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
    for i in np.argsort(strength)[::-1]:  # strongest first, keep if no neighbour taken
        if strength[i] <= thresh:
            break
        t = (i + 1) * HOP / AUDIO_SR
        if all(abs(t - o) >= gap * HOP / AUDIO_SR for o in onsets):
            onsets.append(round(t, 3))
    onsets.sort()
    bpm = None
    if len(onsets) >= 4:
        beat = float(np.median(np.diff(onsets)))
        while beat and 60 / beat > 180:   # fold into a danceable 60-180 bpm range
            beat *= 2
        while beat and 60 / beat < 60:
            beat /= 2
        bpm = round(60 / beat) if beat else None
    return onsets, bpm


def align(cuts, onsets, fps, tol):
    rows = []
    for c in cuts:
        if not onsets:
            rows.append({"cut": c, "beat": None, "frames_off": None, "ok": False})
            continue
        b = min(onsets, key=lambda o: abs(o - c))
        off = int(round((c - b) * fps))
        rows.append({"cut": c, "beat": b, "frames_off": off, "ok": abs(off) <= tol})
    return rows


def text_band(frames):
    """Rows where near-white, high-contrast pixels persist across >= 80% of 10 sampled frames."""
    if len(frames) == 0:
        return None
    sample = frames[np.linspace(0, len(frames) - 1, min(10, len(frames))).astype(int)]
    hits = np.zeros(TEXT_H)
    for f in sample:
        f = f.astype(np.int16)
        pad = np.pad(f, 2, mode="edge")
        local_min = np.min([pad[dy:dy + TEXT_H, dx:dx + TEXT_W] for dy in range(5) for dx in range(5)], axis=0)
        mask = (f > 235) & (f - local_min > 80)
        hits += mask.sum(axis=1) >= 3        # a text row has several bright strokes
    rows = np.flatnonzero(hits >= 0.8 * len(sample))
    if len(rows) == 0:
        return None
    # take the largest run of rows, allowing small gaps between lines of text
    bands, start = [], rows[0]
    for a, b in zip(rows[:-1], rows[1:]):
        if b - a > TEXT_H * 0.04:
            bands.append((start, a)); start = b
    bands.append((start, rows[-1]))
    top, bot = max(bands, key=lambda s: s[1] - s[0])
    return [round(100 * top / TEXT_H, 1), round(100 * (bot + 1) / TEXT_H, 1)]


def face_band(frames):
    """Face rows (percent of height) in the first shot via OpenCV's Haar cascade, or a reason it was skipped."""
    if cv2 is None:
        return "face check skipped (OpenCV not installed)"
    if not hasattr(cv2, "CascadeClassifier"):
        return "face check skipped (this OpenCV build has no Haar cascade detector)"
    import os
    xml = os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), "haarcascade_frontalface_default.xml")
    if not os.path.exists(xml) or len(frames) == 0:
        return "face check skipped (Haar cascade file not found)"
    cascade = cv2.CascadeClassifier(xml)
    tops, bottoms = [], []
    for f in frames[np.linspace(0, len(frames) - 1, min(5, len(frames))).astype(int)]:
        for (x, y, w, h) in cascade.detectMultiScale(np.ascontiguousarray(f), 1.1, 4, minSize=(30, 30)):
            tops.append(y); bottoms.append(y + h)
    if not tops:
        return []
    return [round(100 * np.median(tops) / TEXT_H, 1), round(100 * np.median(bottoms) / TEXT_H, 1)]


def grade(path, tol):
    info = probe(path)
    fps = info["fps"]
    cuts = find_cuts(decode_gray(path, SMALL_W, SMALL_H), fps)
    onsets, bpm = find_onsets(path) if info["has_audio"] else ([], None)
    rows = align(cuts, onsets, fps, tol)
    first_shot_end = cuts[0] if cuts else info["duration"]
    first_shot = decode_gray(path, TEXT_W, TEXT_H, first_shot_end)
    text = text_band(first_shot)
    face = face_band(first_shot)
    bounds = [0.0] + cuts + [info["duration"]]
    holds = [round(b - a, 2) for a, b in zip(bounds[:-1], bounds[1:])]

    problems = []
    if not cuts:
        problems.append("no hard cuts found (one continuous shot)")
    if not onsets:
        problems.append("no music beats found" + ("" if info["has_audio"] else " (no audio track)"))
    off = [r for r in rows if not r["ok"]]
    if cuts and onsets and off:
        problems.append(f"{len(off)} of {len(cuts)} cuts land more than {tol} frames from a beat: "
                        + ", ".join(f"{r['cut']:.2f}s ({r['frames_off']:+d}f)" for r in off))
    if first_shot_end < 2.5:
        problems.append(f"hook only holds {first_shot_end:.2f} s (needs 2.5 s or more)")
    if text and isinstance(face, list) and face and text[0] < face[1] and text[1] > face[0]:
        problems.append(f"caption text ({text[0]}-{text[1]}%) overlaps the face ({face[0]}-{face[1]}%)")

    return {
        "file": path, "duration_s": round(info["duration"], 2), "size": f"{info['width']}x{info['height']}",
        "fps": round(fps, 3), "tolerance_frames": tol, "cuts_s": cuts, "shot_count": len(cuts) + 1,
        "hold_lengths_s": holds, "onsets_s": onsets, "tempo_bpm": bpm, "alignment": rows,
        "hook_hold_s": round(first_shot_end, 2), "speech": "not checked",
        "text_band_pct": text, "face_band_pct": face, "problems": problems, "grade": "PASS" if not problems else "FAIL",
    }


def report(r):
    ok = sum(1 for a in r["alignment"] if a["ok"])
    n = len(r["cuts_s"])
    parts = [f"{n} cuts · {ok} of {n} within {r['tolerance_frames']} frames of a beat" if n else "no cuts",
             f"tempo ~{r['tempo_bpm']} bpm" if r["tempo_bpm"] else "no beats found",
             f"hook held {r['hook_hold_s']:.2f} s"]
    if r["text_band_pct"]:
        t = r["text_band_pct"]; f = r["face_band_pct"]
        where = (f if isinstance(f, str) else
                 "no face found" if not f else
                 f"clear of the face ({f[0]:.0f}-{f[1]:.0f}%)" if t[0] >= f[1] or t[1] <= f[0] else "ON the face")
        parts.append(f"text band {t[0]:.0f}-{t[1]:.0f}% down the frame, {where}")
    else:
        parts.append("no on-screen text found in the first shot")
    print(f"{r['file']}\n{r['size']} · {r['fps']:g} fps · {r['duration_s']} s · {r['shot_count']} shot{'s' if r['shot_count'] != 1 else ''}")
    print(" · ".join(parts))
    print("speech: " + r["speech"])
    print(f"shot holds (s): {', '.join(f'{h:.2f}' for h in r['hold_lengths_s'])}")
    if r["onsets_s"]:
        print(f"beats (s): {', '.join(f'{o:.2f}' for o in r['onsets_s'])}")
    if r["alignment"]:
        print(f"\n{'cut (s)':>8} {'beat (s)':>9} {'offset':>7}  result")
        for a in r["alignment"]:
            beat = f"{a['beat']:.2f}" if a["beat"] is not None else "-"
            offs = f"{a['frames_off']:+d}f" if a["frames_off"] is not None else "-"
            print(f"{a['cut']:>8.2f} {beat:>9} {offs:>7}  {'OK' if a['ok'] else 'off'}")
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
