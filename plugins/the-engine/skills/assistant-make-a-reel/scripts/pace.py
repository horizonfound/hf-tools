#!/usr/bin/env python3
"""The Studio by Horizon Found. How long each photo stays up, counted in beats, so
every cut lands on the beat. Four feels the photographer picks from:

  calm    every photo about two seconds; room to look
  fast    about half a second a photo; quick and punchy (best with more photos)
  build   starts calm, quickens toward the end, lands on the last photo
  mixed   a little of everything: some quick, some long, never a formula

How "mixed" stays musical rather than random: the reel starts on the first beat
of a bar, the song is counted in phrases of two bars (bars of 4 beats, or of 3
for a waltz or a 6/8 feel), and the cuts inside each phrase follow one of a set of shapes a video
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

# Songs in 4 (most pop, folk, electronic): one phrase = two bars = 8 units, one bar = 4 units.
SHAPES = [
    [8], [4, 4], [2, 2, 4], [4, 2, 2], [2, 4, 2], [2, 2, 2, 2], [3, 1, 4], [4, 3, 1],
    [1, 1, 2, 4], [2, 1, 1, 4], [4, 1, 1, 2], [1, 1, 2, 2, 2], [2, 2, 1, 1, 2],
    [1, 1, 1, 1, 4], [1, 1, 1, 1, 2, 2], [2, 1, 1, 1, 1, 2], [4, 1, 1, 1, 1], [4, 2, 1, 1],
]
BAR_SHAPES = [[4], [2, 2], [1, 1, 2], [2, 1, 1], [3, 1], [1, 1, 1, 1]]
# Songs in 3 (waltzes, many ballads, 6/8 feels): one phrase = two bars = 6 units, one bar = 3 units.
SHAPES_3 = [
    [6], [3, 3], [3, 1, 1, 1], [1, 1, 1, 3], [2, 1, 3], [3, 2, 1], [1, 2, 3], [3, 1, 2],
    [1, 1, 1, 1, 2], [2, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1],
]
BAR_SHAPES_3 = [[3], [1, 1, 1], [2, 1], [1, 2]]
FEELS = ("mixed", "calm", "fast", "build", "steady")


def _closest(period, target, options, floor):
    best = min(options, key=lambda b: abs(b * period - target))
    if best * period < floor:
        bigger = [b for b in sorted(options) if b * period >= floor]
        best = bigger[0] if bigger else max(options) * 2
    return best


def _opts(meter):
    """Holds that keep the cuts in step with the bar: in 4, 1 2 4 8 beats; in 3, 1 3 6 12."""
    if meter == 3:
        return {"unit": (1, 3, 6), "calm": (3, 6, 12), "fast": (1, 3), "long": (3, 6, 12)}
    return {"unit": (1, 2, 4), "calm": (2, 4, 8), "fast": (1, 2), "long": (2, 4, 8)}


def unit_beats(period, meter=4):
    """The base hold: whole beats closest to about a second a photo, never faster than half a second."""
    return _closest(period, 1.1, _opts(meter)["unit"], 0.5)


def holds(n, period, feel="mixed", energy=None, hints=None, seed=0, meter=4):
    """Beats each of n photos holds, counted from the first beat of a bar. energy: loudness per beat from
    there on (or None). hints: per photo "+", "-" or None. meter: beats in a bar (3 or 4)."""
    if n <= 0:
        return []
    o = _opts(meter)
    hints = (hints or []) + [None] * n
    if n == 1:
        return [_closest(period, 3.0, o["long"] + (o["long"][-1] * 2,), 1.5)]
    if feel == "calm":
        c = _closest(period, 2.0, o["calm"], 1.4)
        out = [c] * n
        out[-1] = 2 * c
        return land(out, meter)
    if feel == "fast":
        f = _closest(period, 0.55, o["fast"], 0.35)
        out = [f] * n
        out[0] = _closest(period, 1.6, o["long"], 1.0)
        out[-1] = _closest(period, 2.0, o["long"], 1.4)
        return land(out, meter)
    if feel == "build":
        k = unit_beats(period, meter)
        quick = _closest(period, 0.55, o["fast"], 0.35)
        calm = max(_closest(period, 1.8, o["calm"], 1.2), 2 * k)   # clearly slower than the middle, so it builds
        if quick >= k:
            quick = 1
        third = max(1, (n - 1) // 3)
        out = []
        for i in range(n - 1):
            out.append(calm if i < third else quick if i >= n - 1 - third else k)
        out.append(_closest(period, 2.2, o["long"], 1.5))
        return land(out, meter)
    if feel == "steady":
        k = unit_beats(period, meter)
        out = [k] * n
        out[0] = out[-1] = 2 * k
        return land(out, meter)
    return _mixed(n, period, energy, hints, seed, meter)


def land(out, meter):
    """Let the last photo arrive on the first beat of a bar: stretch the photo before it if needed."""
    if len(out) >= 2:
        before = sum(out[:-1])
        if before % meter:
            out[-2] += meter - before % meter
    return out


def _mixed(n, period, energy, hints, seed, meter=4):
    if meter == 3:
        shapes, bar_shapes, bar, phrase = SHAPES_3, BAR_SHAPES_3, 3, 6
        u = 1 if period >= 0.3 else 2
    else:
        shapes, bar_shapes, bar, phrase = SHAPES, BAR_SHAPES, 4, 8
        u = max(1, unit_beats(period, 4) // 2)   # beats in one unit: a quick photo is one unit
    rng = random.Random(seed)
    any_quick = "-" in hints[:n]
    phrase_beats = phrase * u
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
        for shape in shapes + bar_shapes:
            if len(shape) > r:
                continue
            if first and shape[0] < bar:      # the opener gets a whole bar: the hook sits on it
                continue
            s = -4.0 * abs(len(shape) / sum(shape) - want)
            if sum(shape) == bar:
                s -= 0.3                      # mostly two-bar phrases, sometimes one bar
            for j, slot in enumerate(shape):
                h = hints[i + j]
                if h == "+":
                    s += 2.0 if slot >= bar else -3.0
                elif h == "-":
                    s += 1.8 if slot <= 1 else (-0.2 if slot == 2 else -2.5)
                elif slot == phrase:
                    s -= 1.5                  # a whole phrase on one photo only when asked for
                elif slot == 1 and any_quick:
                    s -= 0.6                  # Claude marked the ones to fly by; keep the quick spots for them
            run = 0                           # quick photos in a row, counting the end of what's placed
            for x in reversed(units):
                if x != 1:
                    break
                run += 1
            longest = 0
            for j, slot in enumerate(shape):
                if slot == 1:
                    run += 1
                    if hints[i + j] != "-":
                        longest = max(longest, run)
                else:
                    run = 0
            if longest > 3:
                s -= 3.0                      # a burst is two to four quick photos, not a whole run of them
            if shape == last and len(shape) > 1:
                s -= 2.0                      # the same pattern twice running (one long hold is not a pattern)
            elif last and len(shape) == len(last):
                s -= 0.4
            if r - len(shape) == 0 and shape[-1] >= bar:
                s -= 0.5                      # leave the long landing to the closer
            s += rng.uniform(0, 0.6)          # no formula
            if s > best_score:
                best, best_score = shape, s
        units += best
        i += len(best)
        last = best
        first = False
    long_close = hints[n - 1] == "+" and phrase * u * period <= 4.0
    units.append(phrase if long_close else bar)   # the closer lands on a bar; a "+" closer lingers, up to 4 s
    return [x * u for x in units]


def describe(beats, period, feel):
    """Words for the feel, and the shortest and longest hold among the middle photos (the first and last
    always linger a little)."""
    mid = beats[1:-1] if len(beats) > 2 else beats
    secs = [b * period for b in mid]
    words = {"mixed": "a little of everything", "calm": "calm", "fast": "fast", "build": "building",
             "steady": "steady"}[feel]
    return words, round(min(secs), 1), round(max(secs), 1)
