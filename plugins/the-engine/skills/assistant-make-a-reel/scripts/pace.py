#!/usr/bin/env python3
"""The Studio by Horizon Found. How long each photo stays up, counted in beats, so
every cut lands on the beat. Four feels the photographer picks from:

  calm    every photo about two seconds; room to look
  fast    about half a second a photo; quick and punchy (best with more photos)
  build   starts calm, quickens toward the end, lands on the last photo
  mixed   a little of everything: some quick, some long, never a formula

How "mixed" stays musical rather than random: the song is counted in phrases of
two bars, and the cuts inside each phrase follow one of a set of shapes a video
editor would use (long-long, quick-quick-long, a burst of four quick then a long
landing, ...). Every phrase starts on a cut, so the changes land where the music
turns over. Which shape each phrase gets depends on:
  - the song: louder, busier stretches get more cuts, quiet ones fewer
  - the photos: Claude marks a photo "+" to linger on it (the emotional peak, a
    wide with a lot to take in) or "-" to pass quickly (details, frames of one
    burst), and the shapes are chosen so those photos land in long or quick spots
  - variety: never the same shape twice in a row
A seed from the photos makes the same picks give the same reel every time;
another "variation" number gives a different mix of the same picks.
"""
import random

# one phrase = 8 units; each number is how many units one photo holds
SHAPES = [
    [8], [4, 4], [2, 2, 4], [4, 2, 2], [2, 4, 2], [2, 2, 2, 2], [3, 1, 4], [4, 3, 1],
    [1, 1, 2, 4], [2, 1, 1, 4], [4, 1, 1, 2], [1, 1, 2, 2, 2], [2, 2, 1, 1, 2],
    [1, 1, 1, 1, 4], [1, 1, 1, 1, 2, 2], [2, 1, 1, 1, 1, 2], [4, 1, 1, 1, 1], [4, 2, 1, 1],
]
# one bar = 4 units: lets a phrase turn over halfway, and lets the end land on a bar
BAR_SHAPES = [[4], [2, 2], [1, 1, 2], [2, 1, 1], [3, 1], [1, 1, 1, 1]]
FEELS = ("mixed", "calm", "fast", "build", "steady")


def _closest(period, target, options, floor):
    best = min(options, key=lambda b: abs(b * period - target))
    while best * period < floor:
        best *= 2
    return best


def unit_beats(period):
    """The base hold: whole beats closest to about a second a photo, never faster than half a second."""
    return _closest(period, 1.1, (1, 2, 4), 0.5)


def holds(n, period, feel="mixed", energy=None, hints=None, seed=0):
    """Beats each of n photos holds. energy: loudness per beat from the reel's first beat on (or None).
    hints: per photo "+", "-" or None."""
    if n <= 0:
        return []
    hints = (hints or []) + [None] * n
    if n == 1:
        return [_closest(period, 3.0, (2, 4, 8, 16), 1.5)]
    if feel == "calm":
        c = _closest(period, 2.0, (2, 4, 8), 1.4)
        out = [c] * n
        out[-1] = 2 * c
        return out
    if feel == "fast":
        f = _closest(period, 0.55, (1, 2), 0.35)
        out = [f] * n
        out[0] = _closest(period, 1.6, (2, 4, 8), 1.0)
        out[-1] = _closest(period, 2.0, (2, 4, 8), 1.4)
        return out
    if feel == "build":
        k = unit_beats(period)
        quick = _closest(period, 0.55, (1, 2), 0.35)
        calm = max(_closest(period, 1.8, (2, 4, 8), 1.2), 2 * k)   # clearly slower than the middle, so it builds
        if quick >= k:
            quick = max(1, k // 2)
        third = max(1, (n - 1) // 3)
        out = []
        for i in range(n - 1):
            out.append(calm if i < third else quick if i >= n - 1 - third else k)
        out.append(_closest(period, 2.2, (2, 4, 8), 1.5))
        return out
    if feel == "steady":
        k = unit_beats(period)
        out = [k] * n
        out[0] = out[-1] = 2 * k
        return out
    return _mixed(n, period, energy, hints, seed)


def _mixed(n, period, energy, hints, seed):
    k = unit_beats(period)
    u = max(1, k // 2)                       # beats in one unit: a quick photo is one unit
    rng = random.Random(seed)
    phrase_beats = 8 * u
    med = sorted(energy)[len(energy) // 2] if energy else 0.0
    units = []
    i = 0
    last = None
    first = True
    while n - 1 - i > 0:                     # photos still to place before the closer
        r = n - 1 - i
        b0 = sum(units) * u
        seg = (energy or [])[b0:b0 + phrase_beats]
        rel = (sum(seg) / len(seg) / med) if seg and med > 0 else 1.0
        want = min(0.8, max(0.2, 0.42 + 0.35 * (rel - 1.0)))   # share of units that are cuts
        best, best_score = None, -1e9
        for shape in SHAPES + BAR_SHAPES:
            if len(shape) > r:
                continue
            if first and shape[0] < 4:        # the opener gets time: the hook sits on it
                continue
            s = -4.0 * abs(len(shape) / sum(shape) - want)
            if sum(shape) == 4:
                s -= 0.3                      # mostly two-bar phrases, sometimes one bar
            for j, slot in enumerate(shape):
                h = hints[i + j]
                if h == "+":
                    s += 2.0 if slot >= 4 else -3.0
                elif h == "-":
                    s += 1.8 if slot <= 1 else (-0.2 if slot == 2 else -2.5)
                elif slot == 8:
                    s -= 1.5                  # a whole phrase on one photo only when asked for
            if shape == last:
                s -= 2.0
            elif last and len(shape) == len(last):
                s -= 0.4
            if r - len(shape) == 0 and shape[-1] >= 4:
                s -= 0.5                      # leave the long landing to the closer
            s += rng.uniform(0, 0.6)          # no formula
            if s > best_score:
                best, best_score = shape, s
        units += best
        i += len(best)
        last = best
        first = False
    units.append(8 if hints[n - 1] == "+" else 4)   # the closer lands, ending on a bar
    return [x * u for x in units]


def describe(beats, period, feel):
    """Words for the feel, and the shortest and longest hold among the middle photos (the first and last
    always linger a little)."""
    mid = beats[1:-1] if len(beats) > 2 else beats
    secs = [b * period for b in mid]
    words = {"mixed": "a little of everything", "calm": "calm", "fast": "fast", "build": "building",
             "steady": "steady"}[feel]
    return words, round(min(secs), 1), round(max(secs), 1)
