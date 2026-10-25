#!/usr/bin/env python3
"""The Studio by Horizon Found. Finds the beats in a song so a reel can cut on them,
with nothing to install.

    python3 beats_lite.py song.m4a            tempo and the first beats
    python3 beats_lite.py song.m4a --json     {ok, duration, tempo, period, beats, energy, how}

How it hears the song: the Mac's own afconvert turns it into plain sound samples
(mp3, m4a, aac, wav, aiff all work). On a computer without afconvert it uses
ffmpeg if that happens to be there, and reads a .wav file by itself either way.
Everything after that is plain Python: no numpy, no ffmpeg needed.

How it finds the beat: it listens for the moments the sound jumps (a kick, a
snare, a strum) in a low band and a high band, finds the steady pulse those
jumps repeat at, then walks through the song placing each beat on a real jump
near where the pulse says the next one should be (Ellis's beat tracker, 2007).
So a song that drifts a little stays on the beat all the way through.
"""
import array
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave

SR = 11025          # samples per second we listen at; plenty for rhythm
HOP = 128           # one envelope value every 11.6 ms
FPS = SR / HOP


# ---------------------------------------------------------------- hearing it

def _read_wav(path):
    """Mono 16-bit samples from a .wav file, plus its sample rate."""
    with wave.open(str(path), "rb") as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError("only 16-bit wav")
    a = array.array("h")
    a.frombytes(raw)
    if sys.byteorder == "big":
        a.byteswap()
    if ch > 1:  # average the channels
        a = array.array("h", (sum(a[i:i + ch]) // ch for i in range(0, len(a) - ch + 1, ch)))
    return a, rate


def _resample(a, rate):
    """Crude but fine for rhythm: average blocks down to about SR."""
    if rate == SR:
        return a
    step = rate / SR
    out = array.array("h")
    i = 0.0
    n = len(a)
    while i + step <= n:
        lo, hi = int(i), int(i + step)
        seg = a[lo:hi] or a[lo:lo + 1]
        out.append(sum(seg) // len(seg))
        i += step
    return out


def real_kind(path):
    """The file extension that matches what is inside, from its first bytes, or None.
    CapCut's library songs are saved as M4A with a .mp3 name, and afconvert goes by
    the name, so it cannot open them until it is told the real kind."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return None
    if head[4:8] == b"ftyp":
        return ".m4a"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return ".mp3"
    if head[:4] == b"RIFF":
        return ".wav"
    if head[:4] == b"FORM":
        return ".aiff"
    return None


def decode(path):
    """(samples, how) or (None, reason). Samples are mono 16-bit at SR."""
    path = str(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    alias_dir = None
    try:
        how = None
        if shutil.which("afconvert"):
            src = path
            kind = real_kind(path)
            if kind and not path.lower().endswith(kind) and not (kind == ".aiff" and path.lower().endswith(".aif")):
                # a link with the right name, in a temporary folder; the song itself is untouched
                alias_dir = tempfile.mkdtemp()
                src = os.path.join(alias_dir, "song" + kind)
                os.symlink(os.path.abspath(path), src)
            r = subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SR}", "-c", "1", src, tmp.name],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.getsize(tmp.name) > 44:
                how = "afconvert"
        if not how and shutil.which("ffmpeg"):
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                                "-c:a", "pcm_s16le", tmp.name], capture_output=True, text=True)
            if r.returncode == 0 and os.path.getsize(tmp.name) > 44:
                how = "ffmpeg"
        if how:
            a, rate = _read_wav(tmp.name)
            return _resample(a, rate), how
        if path.lower().endswith(".wav"):
            a, rate = _read_wav(path)
            return _resample(a, rate), "wav"
        return None, "this computer has no way to read that kind of song file (a .wav would work)"
    except (OSError, ValueError, wave.Error, EOFError) as e:
        return None, f"could not read the song ({e})"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        if alias_dir:
            shutil.rmtree(alias_dir, ignore_errors=True)


# ---------------------------------------------------------------- the pulse

CUTS = (120, 300, 700, 1600, 3500)   # band edges in Hz: kick, bass, body, voice/strum, snare, hats


def envelopes(a):
    """Per-hop energy in six bands (kick, bass, body, voice and strums, snare, hats), and overall."""
    k = [1 - math.exp(-2 * math.pi * c / SR) for c in CUTS]
    k0, k1, k2, k3, k4 = k
    y0 = y1 = y2 = y3 = y4 = 0.0
    bands = [[] for _ in range(len(CUTS) + 1)]
    full = []
    n = len(a) // HOP
    for h in range(n):
        e0 = e1 = e2 = e3 = e4 = e5 = ef = 0.0
        for x in a[h * HOP:(h + 1) * HOP]:
            y0 += k0 * (x - y0)
            y1 += k1 * (x - y1)
            y2 += k2 * (x - y2)
            y3 += k3 * (x - y3)
            y4 += k4 * (x - y4)
            b = y1 - y0
            c = y2 - y1
            d = y3 - y2
            e = y4 - y3
            f = x - y4
            e0 += y0 * y0
            e1 += b * b
            e2 += c * c
            e3 += d * d
            e4 += e * e
            e5 += f * f
            ef += x * x
        for i, v in enumerate((e0, e1, e2, e3, e4, e5)):
            bands[i].append(v)
        full.append(ef)
    return bands, full


def onset_strength(bands, lag=2):
    """How much the sound jumps at each moment: the rise in log energy, averaged over the bands."""
    n = len(bands[0])
    o = [0.0] * n
    for e in bands:
        top = max(e) or 1.0
        lg = [math.log1p(1000.0 * v / top) for v in e]
        for i in range(lag, n):
            d = lg[i] - lg[i - lag]
            if d > 0:
                o[i] += d
    # a soft local average taken away, so a loud chorus does not swamp a quiet verse
    w = int(FPS * 1.0)
    pref = [0.0]
    for v in o:
        pref.append(pref[-1] + v)
    out = []
    for i in range(n):
        lo_i, hi_i = max(0, i - w), min(n, i + w + 1)
        v = o[i] - 0.5 * (pref[hi_i] - pref[lo_i]) / (hi_i - lo_i)
        out.append(v if v > 0 else 0.0)
    s = sum(out) / n if n else 0
    sd = math.sqrt(sum((v - s) ** 2 for v in out) / n) if n else 0
    return [v / sd for v in out] if sd > 0 else out


def smooth(o, period):
    """librosa's local score: the onsets blurred by a narrow bell (period/32 wide) so a beat may sit a hop off."""
    half = int(period)
    w = [math.exp(-0.5 * (j * 32.0 / period) ** 2) for j in range(-half, half + 1)]
    w = [(j - half, v) for j, v in enumerate(w) if v > 1e-3]
    n = len(o)
    return [sum(v * o[i + j] for j, v in w if 0 <= i + j < n) for i in range(n)]


def tempo_period(o, lo_bpm=70, hi_bpm=180, prior_bpm=120.0):
    """The steady pulse, in hops, by autocorrelation weighted toward everyday tempos (librosa's prior)."""
    n = len(o)
    if n < FPS * 4:
        return 0.0
    mean = sum(o) / n
    c = [v - mean for v in o]
    lags = range(int(FPS * 60 / hi_bpm), int(FPS * 60 / lo_bpm) + 1)
    best, best_lag, ac = -1e18, 0, {}
    for L in lags:
        s = 0.0
        for i in range(n - L):
            s += c[i] * c[i + L]
        ac[L] = s / (n - L)
    for L, s in ac.items():
        bpm = 60 * FPS / L
        weight = math.exp(-0.5 * (math.log2(bpm / prior_bpm) / 0.75) ** 2)
        if s * weight > best:
            best, best_lag = s * weight, L
    # a fraction of a hop matters over a whole song: interpolate around the peak
    L = best_lag
    if L - 1 in ac and L + 1 in ac:
        y0, y1, y2 = ac[L - 1], ac[L], ac[L + 1]
        den = y0 - 2 * y1 + y2
        if den < 0:
            return L + 0.5 * (y0 - y2) / den
    return float(L)


def track(o, period, tightness=400.0):
    """Ellis's dynamic-programming beat tracker: beats sit on onsets, spaced close to the pulse."""
    n = len(o)
    if period <= 0 or n == 0:
        return []
    lo_off, hi_off = max(1, int(round(period / 2))), int(round(period * 2))
    score = [0.0] * n
    back = [-1] * n
    for t in range(n):
        best, arg = 0.0, -1
        for tau in range(t - hi_off, t - lo_off + 1):
            if tau < 0:
                continue
            gap = (t - tau) / period
            v = score[tau] - tightness * math.log(gap) ** 2
            if arg < 0 or v > best:
                best, arg = v, tau
        score[t] = o[t] + (best if arg >= 0 else 0.0)
        back[t] = arg
    # end on the best-scoring beat in the last stretch
    tail = range(max(0, n - int(period * 2)), n)
    end = max(tail, key=lambda t: score[t])
    beats = []
    t = end
    while t >= 0:
        beats.append(t)
        t = back[t]
    beats.reverse()
    # drop weak beats at the very start and end (silence, a fade)
    strong = sorted(o[b] for b in beats)
    floor = strong[len(strong) // 2] * 0.15 if strong else 0
    while beats and o[beats[0]] < floor:
        beats.pop(0)
    while beats and o[beats[-1]] < floor:
        beats.pop()
    return beats


def fill_gaps(beats, period, n):
    """Where the tracker left a hole (a breakdown), keep the pulse going so every beat exists."""
    if not beats:
        return beats
    out = [beats[0]]
    for b in beats[1:]:
        while b - out[-1] > period * 1.5:
            out.append(out[-1] + period)
        out.append(b)
    # and before the first / after the last, out to the song's edges
    while out[0] - period >= 0:
        out.insert(0, out[0] - period)
    while out[-1] + period < n:
        out.append(out[-1] + period)
    return out


def energy_per_beat(full, beats_hops):
    out = []
    for i, b in enumerate(beats_hops):
        e = beats_hops[i + 1] if i + 1 < len(beats_hops) else b + 20
        seg = full[int(b):int(e)]
        out.append(math.sqrt(sum(seg) / (len(seg) * HOP)) / 32768.0 if seg else 0.0)
    return out


def best_start(info, need):
    """Where to start the song for a reel `need` seconds long: the start of the loudest stretch that fits, on a
    beat, nudged toward a moment the energy jumps (a chorus coming in, a drop). 0 when nothing is clearly better."""
    grid, energy = info.get("beats") or [], info.get("energy") or []
    dur = info.get("duration", 0)
    if not grid or not energy or need <= 0 or dur - need < 2.0:
        return 0.0
    n = len(grid)
    best_i, best_score, first_score = 0, -1.0, None
    for i in range(n):
        if grid[i] + need > dur:
            break
        j = i
        while j < n and grid[j] < grid[i] + need:
            j += 1
        win = energy[i:j]
        if not win:
            continue
        before = sum(energy[max(0, i - 4):i]) / max(1, len(energy[max(0, i - 4):i])) if i > 0 else 0.0
        after = sum(energy[i:i + 4]) / max(1, len(energy[i:i + 4]))
        score = sum(win) / len(win) + 0.6 * max(0.0, after - before)
        if first_score is None:
            first_score = score
        if score > best_score:
            best_i, best_score = i, score
    if first_score is not None and best_score <= first_score * 1.08:
        return 0.0
    return float(grid[best_i])


def analyze(path):
    a, how = decode(path)
    if a is None:
        return {"ok": False, "reason": how, "duration": 0, "tempo": 0, "period": 0, "beats": [], "energy": []}
    dur = len(a) / SR
    bands, full = envelopes(a)
    o = onset_strength(bands)
    period = tempo_period(o)
    if not period:
        return {"ok": False, "reason": "the song is too short to find a beat", "duration": round(dur, 3),
                "tempo": 0, "period": 0, "beats": [], "energy": [], "how": how}
    tracked = track(smooth(o, period), period)
    if len(tracked) < 4:
        return {"ok": False, "reason": "no steady beat (the song may be too quiet or too free-form)",
                "duration": round(dur, 3), "tempo": 0, "period": 0, "beats": [], "energy": [], "how": how}
    gaps = sorted(tracked[i + 1] - tracked[i] for i in range(len(tracked) - 1))
    per = gaps[len(gaps) // 2]
    hops = fill_gaps(tracked, per, len(o))
    beats = [round(h / FPS, 3) for h in hops]
    return {"ok": True, "duration": round(dur, 3), "tempo": round(60 * FPS / per, 1),
            "period": round(per / FPS, 4), "beats": beats, "energy": energy_per_beat(full, hops), "how": how}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    res = analyze(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(res))
        sys.exit(0 if res["ok"] else 1)
    if not res["ok"]:
        print("No beat found:", res.get("reason"))
        sys.exit(1)
    print(f"{res['duration']:.1f} s · about {res['tempo']:.0f} beats a minute · {len(res['beats'])} beats ({res['how']})")
    print(" ".join(f"{b:.2f}" for b in res["beats"][:32]) + (" ..." if len(res["beats"]) > 32 else ""))
