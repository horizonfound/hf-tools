"""How early or late a decoded test song's clicks sit against the WAV's, to a tenth of a millisecond.

The beat finder (beats_lite.py) works in steps of 11.6 ms, too coarse to say whether a decoder kept an
encoder's few milliseconds of warm-up at the front. This looks at the samples themselves. Every test song
here is the same click track (make_fixtures.py: 100 beats a minute, the first at 0.25 s), so the WAV says
where each click starts, and a decode of any other file should put its clicks in the same places.
Standard library only. Used by check_sound.py and decode_report.py.
"""
import array
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
RATE = 11025                                    # what sound.decode gives, and what the WAV was written at
BEATS = [0.25 + k * 0.6 for k in range(16)]     # the first 16 clicks


def wav_samples():
    with wave.open(str(HERE / "click-100bpm.wav"), "rb") as w:
        a = array.array("h", w.readframes(w.getnframes()))
    if sys.byteorder == "big":
        a.byteswap()
    return a


def onsets(a):
    """Where each click starts, in samples (with a fraction): the point within 0.1 s either side of each beat
    where its loudness (|x| over about 1 ms) first reaches half that click's loudest. The same rule on the WAV
    and on a decode, so the rule's own bias cancels. None when a click can't be found."""
    out = []
    for t in BEATS:
        lo, hi = max(0, int((t - 0.1) * RATE)), min(len(a), int((t + 0.1) * RATE))
        if hi - lo < 50:
            return None
        env = [abs(x) for x in a[lo:hi]]
        sm = [sum(env[max(0, i - 5):i + 6]) for i in range(len(env))]
        top = max(sm)
        if top <= 0:
            return None
        i = next(i for i, v in enumerate(sm) if v >= top / 2)
        if i == 0:
            out.append(float(lo))
            continue
        prev = sm[i - 1]                         # between samples: where the half-way line was crossed
        out.append(lo + i - 1 + ((top / 2 - prev) / (sm[i] - prev) if sm[i] != prev else 1.0))
    return out


_truth = None


def late_ms(a):
    """How late a decode's clicks are against the WAV's, in milliseconds (the middle of the 16; below 0 is
    early), or None when they can't be measured."""
    global _truth
    if _truth is None:
        _truth = onsets(wav_samples())
    got = onsets(a) if a is not None and len(a) else None
    if not got or not _truth:
        return None
    d = sorted((g - w) * 1000 / RATE for g, w in zip(got, _truth))
    return (d[7] + d[8]) / 2
