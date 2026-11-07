#!/usr/bin/env python3
"""The Assistant by Horizon Found. How long each piece of a reel stays on screen: Nicole's timing engine
(her bts_reel.py, handoff v19, Nov 6, 2026), written as plain code that reel.py calls. Photos and video
clips alike, every vibe, with a song or without.

Her rules, in her words where she gave them:
  - Every cut lands on a whole beat, whichever vibe they pick. "The a little bit of everything is awesome. I
    love how some are short and fast, but they still need to land on the beat... And that goes for calm and
    build."
  - Every photo stays at least one whole beat and about half a second (MIN_SHOW): no half-beat cuts. On one of
    her test reels the half-beat pairs were 0.3 s a photo: "so fast it like disappears before you even see anything".
    Quicker means the shortest: one beat. The last photo always gets at least two beats.
  - The vibes are not fixed templates: "those are not set in stone templates. Those should change for every
    single thing that's made." One search over the whole reel (dynamic programming) picks every length
    together: each piece has a natural length for the vibe and a few others it may take at a small cost; cuts
    land where the song really hits (its onset strength there); a long hold or a clip ends on the 1 of a bar
    when it can; everything fits in the song.
  - Nothing is ever left out to fit: "you shouldn't be removing" photos or footage. When the song is short the
    longer holds shrink (and they are told kindly, kind_note); when even one beat each can't fit, nothing is
    made and they are told exactly why (the STOP line).
  - A clip runs whole beats, never longer than its card or what is left of its video. An opening clip is 3 to 4 seconds and never under 3;
    later clips may shrink to 2 seconds on a short song; a card they made longer than 4.2 s keeps its length,
    give or take a beat.
  - "A little of everything" is mixed differently for every reel: seeded by the file names, the vibe and how
    many reels were already made with the same choices (variation), so Make my reel again gives a fresh mix,
    and the same choices give the same reel on any computer.

How it counts (as hers): the song's beats and the points halfway between them make one grid, counted in half
beats. Every length below is in half beats, and every length a piece may take is a whole number of beats, so
every cut sits on a beat; the half points only carry the vibe's targets and how loud the song is there.

Plain Python, the same on a Mac and a PC: the song is heard by beats_lite.py (sound.py underneath), nothing
else is read or run here.
"""
import math
import os
import random
import zlib

import beats_lite

VIBES = ("beat", "mixed", "calm", "build")
# The vibe a reel gets when nobody picked one, and the one the reel page marks Recommended (decision 7 of the v19
# plan: Nicole's On every beat, in place of "a little of everything"; Dustin to confirm). Change it here only.
DEFAULT_PACE = "beat"
# The old pace names still work (reel.py --pace): "fast" was about half a second a photo, and Nicole's answer to
# "too slow" was one photo on every beat ("that's it", Nov 5), so fast is On every beat; "steady" was about a
# second a photo, even, which is what Calm's two beats come to at an everyday tempo.
OLD_NAMES = {"fast": "beat", "steady": "calm"}
NAMES = {"beat": "On every beat", "mixed": "A little of everything", "calm": "Calm", "build": "Build"}
WORDS = {"beat": "one photo on every beat", "mixed": "a little of everything", "calm": "calm", "build": "building"}

EVEN_BPM = 100.0          # no song: an even 100 beats a minute (the footage keeps its own sound)
MIN_SHOW = 0.45           # no photo on screen for less than about half a second (on a very fast song: two beats)
W_HIT, W_DOWN = 0.6, 0.35  # landing on a hit; a long hold or a clip ending on the 1 of a bar


def vibe_of(name):
    """The engine's vibe for a pace name, old or new; None if it is neither."""
    name = (name or "").strip().lower()
    name = OLD_NAMES.get(name, name)
    return name if name in VIBES else None


# ---------------------------------------------------------------- the grid

class Grid:
    """The song's beats and the points halfway between them.
    T: the time of every grid point; P: its place in the bar (1, 2, 3, 4; 0 for a half point);
    HIT: how hard the song hits there and ENERGY: how loud that beat is, each ranked 0 (weakest) to 1;
    period: one beat in seconds; info: the half-point grid as beats_lite.best_start reads it."""

    def __init__(self, T, P, HIT, ENERGY, period, tempo, meter, info, song, beats_from=None):
        self.T, self.P, self.HIT, self.ENERGY = T, P, HIT, ENERGY
        self.period, self.half = period, period / 2
        self.tempo, self.meter, self.info, self.song, self.beats_from = tempo, meter, info, song, beats_from


def rank(v):
    """Each value's place among all of them, 0 (weakest) to 1 (strongest)."""
    if not v:
        return []
    order = sorted(range(len(v)), key=lambda k: v[k])
    out = [0.0] * len(v)
    for r, k in enumerate(order):
        out[k] = r / max(1, len(v) - 1)
    return out


_GRIDS = {}


def song_grid(path, beat_file=None):
    """(Grid, None) for a song, or (None, the reason in plain words). Heard once per file and kept while this
    program runs (a test or a page making several reels of one song)."""
    try:
        st = os.stat(path)
        key = (str(path), str(beat_file or ""), st.st_size, st.st_mtime_ns)
    except OSError:
        key = None
    if key and key in _GRIDS:
        return _GRIDS[key], None
    i = beats_lite.analyze(str(path), beat_file, keep_onset=True)
    if not i.get("ok"):
        return None, i.get("reason") or "no steady beat"
    b, e = i["beats"], i.get("energy") or []
    bp = i.get("bar_pos") or [(k % 4) + 1 for k in range(len(b))]
    nb, pos, en = [], [], []
    for k, t in enumerate(b):
        nb.append(t)
        pos.append(bp[k])
        if e:
            en.append(e[k])
        if k + 1 < len(b):
            nb.append(round((t + b[k + 1]) / 2, 4))
            pos.append(0)
            if e:
                en.append(e[k])
    o = i.get("onset") or []
    hits = []
    for t in nb:                                       # how hard the song hits at each grid point
        h = int(round(t * beats_lite.FPS))
        hits.append(max(o[max(0, h - 2):h + 3], default=0.0) if o else 0.0)
    half = i["period"] / 2
    info = {"beats": nb, "bar_pos": pos, "energy": en, "duration": i.get("duration", 0), "period": half}
    g = Grid(nb, pos, rank(hits or [0.0] * len(nb)), rank(en or [0.0] * len(nb)), half * 2,
             i.get("tempo") or 0, i.get("meter") or 4, info, str(path), i.get("beats_from"))
    if key:
        _GRIDS[key] = g
    return g, None


def even_grid(bpm=EVEN_BPM):
    """No song: an even pulse, counted in half beats like the rest, bars of four."""
    period = 60.0 / bpm
    half = period / 2
    T = [k * half for k in range(1200)]
    P = [((k // 2) % 4) + 1 if k % 2 == 0 else 0 for k in range(1200)]
    return Grid(T, P, [0.0] * len(T), [0.5] * len(T), period, bpm, 4, None, None)


# ---------------------------------------------------------------- what each piece may take

def seed_for(items, vibe, variation=0):
    """File names only (never the folders they sit in), so the same reel comes out the same anywhere."""
    return zlib.crc32(("|".join(os.path.basename(str(x["path"])) for x in items) + f"#{vibe}#{variation}").encode())


def _costs(target, choices, k=0.5):
    """Each length it may take and its cost; the natural length (cost 0) first."""
    return sorted(((h, k * abs(h - target) / max(target, 1)) for h in set(choices) | {target}), key=lambda x: x[1])


def _mixed_targets(n, seed):
    """A little of everything: short and long mixed differently for every reel (blocks in a shuffled order).
    Nicole's own example, "1 second, 1 second, 2 seconds, 1 second, 2 seconds", is the first block."""
    blocks = [[2, 2, 4, 2, 4], [2, 2, 4], [2, 4], [4, 2, 2], [2, 2, 2, 4], [2, 4, 2], [2, 2]]
    pick = random.Random(seed)                         # the same reel's targets every time they're asked for
    out, last = [], None
    while len(out) < n:
        b = pick.choice([x for x in blocks if x is not last])
        out += b
        last = b
    return out[:n]


def _whole_beats(c, period):
    """Every length a whole number of beats, and never under about half a second."""
    hmin = 2 * max(1, math.ceil(MIN_SHOW / period))
    out = {}
    for h, k in c:
        h = max(hmin, h + (h % 2))
        out[h] = min(k, out.get(h, k))
    return sorted(out.items(), key=lambda x: x[1])


def candidates(items, grid, vibe, seed, j0=None):
    """For each piece: the lengths it may take (in half beats), and what each costs against its natural length."""
    period = grid.period
    photos = [k for k, x in enumerate(items) if x["kind"] == "photo"]
    n = len(photos)
    mix = _mixed_targets(n, seed)
    out = []
    pk = 0
    at = j0                                                    # roughly where each piece falls in the song
    for idx, x in enumerate(items):
        if x["kind"] == "clip":
            card = float(x["seconds"])
            if x.get("length") is not None:                    # never past the end of its video
                card = max(0.0, min(card, float(x["length"]) - float(x.get("src") or 0.0)))
            kmax = max(1, int((card + 0.02) / period))        # whole beats, never longer than the card
            if card <= 4.2:                                    # the Assistant's length (or shorter): 3 to 4 seconds
                floor_s = 2.95 if idx == 0 else 1.95           # the opening clip never under 3 s; later ones 2 s at the least
                kmin = min(kmax, max(2, math.ceil(floor_s / period)))
            else:                                              # they made it longer: keep it, a beat less at most
                kmin = max(1, kmax - 1)
            out.append([(2 * k, 0.5 * (kmax - k)) for k in range(kmax, kmin - 1, -1)])
            if at is not None:
                at += 2 * kmax
            continue
        last = idx == len(items) - 1
        first = idx == 0
        mark = x.get("mark") or ""
        frac = pk / max(1, n)
        if vibe == "beat":
            t = {"+": 4, "-": 1}.get(mark, 2)
            c = _costs(t, [1, 2, 4, 6] if mark == "+" else [1, 2, 4], 0.8)
        elif vibe == "calm":
            t = {"+": 8, "-": 2}.get(mark, 4)
            c = _costs(t, [2, 4, 6, 8], 1.0)
        elif vibe == "build":
            t = 4 if frac < 1 / 3 else 2
            t = {"+": t * 2, "-": max(2, t // 2)}.get(mark, t)
            c = _costs(t, [1, 2, 4, 6], 1.6)                   # Build keeps its shape: slow, then quick, then it lands
        else:
            t = 4 if first else mix[pk]
            if at is not None and at < len(grid.ENERGY):       # busier music, quicker photos; quieter, longer
                if grid.ENERGY[at] > 0.85 and t == 4:
                    t = 2
                elif grid.ENERGY[at] < 0.25 and t == 1:
                    t = 2
            t = {"+": max(4, t * 2), "-": 1}.get(mark, t)
            c = _costs(t, [1, 2, 4, 6, 8], 0.9)
        if last:                                               # the last photo lands: never under two beats
            t = 4 if vibe == "beat" else 8
            c = _costs(t, [4, 6, 8], 1.0)
        out.append(_whole_beats(c, period))
        pk += 1
        if at is not None:
            at += t
    return out


# ---------------------------------------------------------------- the one search

def plan_holds(items, grid, vibe, seed, j0, j_end):
    """The cheapest way to lay every piece from grid point j0 so the reel ends by j_end, in half beats (every
    one a whole number of beats). None if it can't fit."""
    cand = candidates(items, grid, vibe, seed, j0)
    INF = float("inf")
    HIT, P = grid.HIT, grid.P
    best = {j0: (0.0, None, None)}                             # position -> (cost, previous position, hold)
    layers = [best]
    for i, x in enumerate(items):
        nxt = {}
        for j, (c0, _, _) in best.items():
            for h, hc in cand[i]:
                e = j + h
                if e > j_end:
                    continue
                c = c0 + hc - W_HIT * HIT[e]
                if P[e] == 1 and (h >= 4 or x["kind"] == "clip"):
                    c -= W_DOWN
                if c < nxt.get(e, (INF,))[0]:
                    nxt[e] = (c, j, h)
        best = nxt
        layers.append(best)
        if not best:
            return None
    _, e = min((c, e) for e, (c, _, _) in best.items())
    holds = []
    for layer in reversed(layers[1:]):
        c, j, h = layer[e]
        holds.append(h)
        e = j
    return holds[::-1]


def downbeat_at_or_after(grid, t):
    return next((j for j in range(0, len(grid.T), 2) if grid.P[j] == 1 and grid.T[j] >= t - 0.02), None)


def _what(n_cl, n_ph):
    return (f"{n_cl} clip{'s' if n_cl != 1 else ''} and {n_ph} photo{'s' if n_ph != 1 else ''}"
            if n_cl else f"{n_ph} photos")


def plan(items, grid, vibe, song_start=None, variation=0, song_length=0.0):
    """items: in play order, each {"kind": "photo", "path", "mark": "+" | "-" | ""} or {"kind": "clip", "path",
    "seconds"}. Returns {"ok": True, "holds": [half beats per piece], "j0": the grid point it starts on,
    "squeezed": bool} or {"ok": False, "stop": the STOP line, word for word, "short": True when it was the song
    that was too short (the reel page shows her "Your song is a little short for this" from this, never from the words)}."""
    seed = seed_for(items, vibe, variation)
    song = grid.song
    j_end = len(grid.T) - 2
    natural = sum(c[0][0] for c in candidates(items, grid, vibe, seed))
    if not song:
        j0 = 0
    elif song_start is not None:
        j0 = downbeat_at_or_after(grid, float(song_start))
    else:
        j0 = downbeat_at_or_after(grid, beats_lite.best_start(grid.info, natural * grid.half + grid.period))
    if j0 is None:
        j0 = downbeat_at_or_after(grid, 0) or 0
    holds = plan_holds(items, grid, vibe, seed, j0, j_end) or []
    if not holds and song:
        first_down = downbeat_at_or_after(grid, 0) or 0
        if first_down < j0:
            j0 = first_down
            holds = plan_holds(items, grid, vibe, seed, j0, j_end) or []
    if not holds:                                      # nothing is ever left out to fit (Nicole, Nov 6)
        quickest = sum(min(h for h, _ in c) for c in candidates(items, grid, vibe, seed)) * grid.half
        n_cl = sum(1 for x in items if x["kind"] == "clip")
        what = _what(n_cl, len(items) - n_cl)
        if not song:
            return {"ok": False, "stop": f"STOP: {what} need at least {quickest:.1f} seconds, even with every photo "
                                         f"at one beat, which is longer than a reel can run. Take a few photos out."}
        room = grid.T[j_end] - grid.T[j0]
        return {"ok": False, "short": True, "stop": f"STOP: Your song is only {song_length or room:.1f} seconds, and {what} need at "
                                     f"least {quickest:.1f} seconds, even with every photo at one beat. "
                + ("Select fewer clips, take a few photos out, or use a longer song." if n_cl > 1
                   else "Take a few photos out, or use a longer song.")}
    # The kind note is for a song that really was too short: the vibe's own lengths, from where the reel starts,
    # run past the song's end. Her engine also said it when the search simply chose quicker holds on a song with
    # room to spare (a mixed reel using a third of a 50-second song), which isn't true; the holds are the same.
    here = sum(c[0][0] for c in candidates(items, grid, vibe, seed, j0))
    squeezed = j0 + here > j_end and sum(holds) < 0.85 * natural
    return {"ok": True, "holds": holds, "j0": j0, "squeezed": squeezed}


# ---------------------------------------------------------------- her words

def beats_line(items, holds):
    """'Beats per piece: clip 6, 1, 1, 2, ...' (her dry run's line, word for word)."""
    return "Beats per piece: " + ", ".join(("clip " if x["kind"] == "clip" else "")
                                           + (str(h // 2) if h % 2 == 0 else f"{h / 2:g}") for x, h in zip(items, holds))


def hits_line(grid, j0, holds):
    """How strong the beats the cuts land on are, against every beat in that stretch (a dry run's check)."""
    if not grid.song or not holds:
        return None
    cuts, e = [], j0
    for h in holds:
        e += h
        cuts.append(e)
    beats_only = list(range(j0, cuts[-1] + 1, 2))
    avg = sum(grid.HIT[j] for j in beats_only) / len(beats_only)
    return (f"Hits: the cuts land on beats {sum(grid.HIT[j] for j in cuts) / len(cuts):.2f} strong on average "
            f"(0 weakest, 1 strongest), against {avg:.2f} for every beat in that stretch.")


def kind_note(items, vibe, song, song_length=0.0):
    """When the song is short and the vibe was made quicker to fit, said kindly (her words)."""
    n_ph = sum(1 for x in items if x["kind"] == "photo")
    n_cl = len(items) - n_ph
    what = f"all {n_ph} photos" + (f" and your clip{'s' if n_cl != 1 else ''}" if n_cl else "")
    if song:
        return (f"Your song is only {song_length or 0:.0f} seconds, so I kept {what} and made "
                f"{NAMES.get(vibe, 'the vibe')} quicker to fit. A longer song, or fewer photos, gives it more room.")
    return f"I kept {what} and made it quicker to keep it short."


def describe(items, beats, period, vibe):
    """Words for the vibe, and the shortest and longest photo in the middle of the reel, in seconds (the first
    and last always linger a little; clips are left out)."""
    photo_secs = [b * period for x, b in zip(items, beats) if x["kind"] == "photo"]
    mid = [b * period for k, (x, b) in enumerate(zip(items, beats))
           if x["kind"] == "photo" and 0 < k < len(items) - 1]
    secs = mid or photo_secs or [b * period for b in beats]
    return WORDS[vibe], round(min(secs), 1), round(max(secs), 1)
