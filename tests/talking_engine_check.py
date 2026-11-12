#!/usr/bin/env python3
"""Checks on talking.py, the arithmetic of a talking-to-camera reel (Nicole's handoffs v23 and v24).

    python3 tests/talking_engine_check.py

We may not run her code, so every expected row below was worked by hand from her arithmetic (talking_core.py,
v24) and is written out with its working beside it: a reviewer can redo each sum from her file without running
anything. Her numbers: a pause OVER 0.45 s starts a new piece; a piece starts 0.08 s before its first word and
ends 0.14 s after its last, or half way to the next kept word when that follows within 0.45 s; a piece never
starts before the one before it ended; a piece of 0.05 s or less is dropped; "at" adds up unrounded and each
value shown is rounded to 3 places. A caption runs from its word's start to 0.12 s past its end (never past its
piece), at least 0.3 s, and then every caption but the last ends where the next begins.

No file is written, no server started. Every line must say PASS. Python 3.9, standard library only, a Mac or a PC.
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"))
import talking as T  # noqa: E402

fails = 0


def check(name, cond, got=None):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond or got is None else f"\n        got: {got!r}"))
    fails += 0 if cond else 1


def W(*rows):
    return [{"w": w, "start": s, "end": e} for w, s, e in rows]


def near(a, b):
    """The same, numbers within a millionth (every expected number is one her code rounds to 3 places)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(near(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(near(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-6
    return a == b


def P(frm, to, words, at, dur, sentence=0, speed=1.0, zoom=None):
    return {"from": frm, "to": to, "speed": speed, "zoom": zoom, "sentence": sentence, "words": words, "at": at, "dur": dur}


def C(text, start, end):
    return {"text": text, "start": start, "end": end}


# Five words, each 0.25 s long, one every half second (so 0.25 s between words), the last ending the sentence.
FIVE = W(("a", 0.0, 0.25), ("b", 0.5, 0.75), ("c", 1.0, 1.25), ("d", 1.5, 1.75), ("e.", 2.0, 2.25))

# ---------------------------------------------------------------- pieces and captions, row by row
CASES = [
    # One piece. from = 1.0 - 0.08 = 0.92; to = 2.5 + 0.14 = 2.64 (no next word); dur = 1.72.
    # Captions: a: 1.0 - 0.92 = 0.08 to (1.25 + 0.12) - 0.92 = 0.45; b: 0.58 to 0.95; c.: 1.08 to (2.62 - 0.92) = 1.70.
    # Then each end moves to the next start: a ends 0.58, b ends 1.08; the last stays 1.70.
    ("one piece: 0.08 before, 0.14 after",
     {"words": W(("a", 1.0, 1.25), ("b", 1.5, 1.75), ("c.", 2.0, 2.5))},
     [P(0.92, 2.64, [0, 1, 2], 0.0, 1.72)],
     [C("a", 0.08, 0.58), C("b", 0.58, 1.08), C("c.", 1.08, 1.70)]),

    # The 0.45 s pause, both sides. a to b is 0.5 (over: new piece). b to c is 0.45 (not over: same piece).
    # c to d is 0.46 (over: new piece).
    # [a]: 0 (never below 0) to 0.25 + 0.14 = 0.39 (b is 0.5 away, further than 0.45, so no meeting half way).
    # [b, c]: 0.75 - 0.08 = 0.67 to 1.75 + 0.14 = 1.89 (d is 0.46 away); dur 1.22; at 0.39.
    # [d.]: 2.21 - 0.08 = 2.13 to 2.5 + 0.14 = 2.64; dur 0.51; at 0.39 + 1.22 = 1.61.
    ("a pause of 0.5 and of 0.46 start a piece; a pause of 0.45 does not",
     {"words": W(("a", 0.0, 0.25), ("b", 0.75, 1.0), ("c", 1.45, 1.75), ("d.", 2.21, 2.5))},
     [P(0.0, 0.39, [0], 0.0, 0.39), P(0.67, 1.89, [1, 2], 0.39, 1.22), P(2.13, 2.64, [3], 1.61, 0.51)],
     None),

    # A new sentence starts a piece, and the two meet half way: "Hi." ends 0.5, "there" starts 0.75 (0.25 apart,
    # within 0.45), so the first piece ends at (0.5 + 0.75) / 2 = 0.625.
    # [there friend.]: 0.75 - 0.08 = 0.67 (after 0.625, so it stands) to 2.0 + 0.14 = 2.14; dur 1.47; at 0.625.
    ("a new sentence starts a piece; touching pieces meet half way",
     {"words": W(("Hi.", 0.0, 0.5), ("there", 0.75, 1.25), ("friend.", 1.5, 2.0))},
     [P(0.0, 0.625, [0], 0.0, 0.625, sentence=0), P(0.67, 2.14, [1, 2], 0.625, 1.47, sentence=1)],
     None),

    # Never the same moment twice: "One." ends 0.5, "two." starts 0.6. Half way is 0.55. The second piece would
    # start at 0.6 - 0.08 = 0.52, before 0.55, so it starts at 0.55. It ends 1.0 + 0.14 = 1.14; dur 0.59.
    ("no moment plays twice: a piece never starts before the last one ended",
     {"words": W(("One.", 0.0, 0.5), ("two.", 0.6, 1.0))},
     [P(0.0, 0.55, [0], 0.0, 0.55, sentence=0), P(0.55, 1.14, [1], 0.55, 0.59, sentence=1)],
     None),

    # The 0.05 s drop. "go." 0 to 1.0; "x." 1.0 to 1.02; "on." 1.04 to 2.0. Three sentences, three would-be pieces.
    # [go.]: 0 to half way to x. = (1.0 + 1.0) / 2 = 1.0.
    # [x.]: starts 1.0 - 0.08 = 0.92, moved up to 1.0; ends half way to on. = (1.02 + 1.04) / 2 = 1.03. That is
    #       0.03 s, not over 0.05: dropped, and word 1 then sits on no piece.
    # [on.]: 1.04 - 0.08 = 0.96, moved up to the last piece KEPT (1.0); ends 2.0 + 0.14 = 2.14; dur 1.14; at 1.0.
    # Captions: go.: 0 to min(1.0, 1.12) = 1.0; on.: 1.0 + (1.04 - 1.0) = 1.04 to 1.0 + (2.12 - 1.0) = 2.12.
    # go.'s end then moves to 1.04.
    ("a piece of 0.05 s or less is dropped, and its word sits on no piece",
     {"words": W(("go.", 0.0, 1.0), ("x.", 1.0, 1.02), ("on.", 1.04, 2.0))},
     [P(0.0, 1.0, [0], 0.0, 1.0, sentence=0), P(1.0, 2.14, [2], 1.0, 1.14, sentence=2)],
     [C("go.", 0.0, 1.04), C("on.", 1.04, 2.12)]),

    # A cut in the middle of a sentence: c is cut. [a, b]: 0 to 0.75 + 0.14 = 0.89 (the next word is cut, so no
    # meeting half way). [d, e.]: 1.5 - 0.08 = 1.42 to 2.25 + 0.14 = 2.39; dur 0.97; at 0.89.
    ("a cut in the middle of a sentence makes two pieces, with no half-way meeting across the cut",
     {"words": FIVE, "cut": [[2, 2]]},
     [P(0.0, 0.89, [0, 1], 0.0, 0.89), P(1.42, 2.39, [3, 4], 0.89, 0.97)],
     None),

    # A split at word 3: that word starts a piece. [a, b, c]: 0 to half way to d = (1.25 + 1.5) / 2 = 1.375.
    # [d, e.]: 1.42 to 2.39; dur 0.97; at 1.375.
    ("a split: the split word starts the piece",
     {"words": FIVE, "splits": [3]},
     [P(0.0, 1.375, [0, 1, 2], 0.0, 1.375), P(1.42, 2.39, [3, 4], 1.375, 0.97)],
     None),

    # A change of speed: d and e. at 2x. Same two stretches as the split, but the second lasts 0.97 / 2 = 0.485.
    # Captions in the first piece (at 0, speed 1): a 0 to 0.37; b 0.5 to 0.87; c 1.0 to min(1.375, 1.37) = 1.37.
    # In the second (at 1.375, speed 2): d starts 1.375 + (1.5 - 1.42) / 2 = 1.415 and would end
    # 1.375 + (1.87 - 1.42) / 2 = 1.6, but a caption lasts at least 0.3 s: 1.715. e. starts
    # 1.375 + (2.0 - 1.42) / 2 = 1.665 and would end 1.375 + (2.37 - 1.42) / 2 = 1.85; at least 0.3 s: 1.965.
    # Then ends move to the next start: a 0.5, b 1.0, c 1.415, d 1.665; the last stays 1.965.
    ("a change of speed starts a piece, which takes the speed of its first word",
     {"words": FIVE, "speeds": [{"a": 3, "b": 4, "v": 2}]},
     [P(0.0, 1.375, [0, 1, 2], 0.0, 1.375), P(1.42, 2.39, [3, 4], 1.375, 0.485, speed=2.0)],
     [C("a", 0.0, 0.5), C("b", 0.5, 1.0), C("c", 1.0, 1.415), C("d", 1.415, 1.665), C("e.", 1.665, 1.965)]),

    # A speed that is not 1.25, 1.5 or 2 reads as 1: nothing changes, one piece, 0 to 2.25 + 0.14 = 2.39.
    ("a speed that isn't one of hers reads as 1",
     {"words": FIVE, "speeds": [{"a": 3, "b": 4, "v": 3}]},
     [P(0.0, 2.39, [0, 1, 2, 3, 4], 0.0, 2.39)],
     None),

    # The edges of a zoom on b and c. [a]: 0 to half way to b = (0.25 + 0.5) / 2 = 0.375.
    # [b, c]: 0.5 - 0.08 = 0.42 to half way to d = 1.375; dur 0.955; at 0.375; zoom 0 (the first in zooms()).
    # [d, e.]: 1.42 to 2.39; dur 0.97; at 0.375 + 0.955 = 1.33.
    ("the edges of a zoom start pieces, which carry the zoom's place in zooms()",
     {"words": FIVE, "zooms": [{"a": 1, "b": 2, "kind": "punch"}]},
     [P(0.0, 0.375, [0], 0.0, 0.375), P(0.42, 1.375, [1, 2], 0.375, 0.955, zoom=0), P(1.42, 2.39, [3, 4], 1.33, 0.97)],
     None),

    # The edges of a photo stretch on b and c: the same three pieces as the zoom, with no zoom.
    ("the edges of a photo stretch start pieces",
     {"words": FIVE, "shots": [{"a": 1, "b": 2, "ns": [5], "spot": "pip"}]},
     [P(0.0, 0.375, [0], 0.0, 0.375), P(0.42, 1.375, [1, 2], 0.375, 0.955), P(1.42, 2.39, [3, 4], 1.33, 0.97)],
     None),

    # Two stretches that overlap (0 to 3, then 2 to 4): the later one has each word they share, so a and b are
    # the first stretch's and c, d, e. the second's. [a, b]: 0 to half way to c = (0.75 + 1.0) / 2 = 0.875.
    # [c, d, e.]: 1.0 - 0.08 = 0.92 to 2.39; dur 1.47; at 0.875.
    ("two photo stretches that overlap: the later one has the words they share",
     {"words": FIVE, "shots": [{"a": 0, "b": 3, "ns": [1], "spot": "full"}, {"a": 2, "b": 4, "ns": [2], "spot": "center"}]},
     [P(0.0, 0.875, [0, 1], 0.0, 0.875), P(0.92, 2.39, [2, 3, 4], 0.875, 1.47)],
     None),

    # Words that begin with an apostrophe join the word before them (ours: every one; hers showed "you 're").
    # One piece, 0 (never below 0) to 2.5 + 0.14 = 2.64. "you're": 0 to 0.5 + 0.12 = 0.62; "Aurora's": 0.75 to
    # 1.37; "do": 1.5 to 1.87; "n't" (no apostrophe at its start, so it stands alone, as hers): 1.75 to 2.12;
    # "ok.": 2.25 to 2.62. Ends move to the next start: 0.75, 1.5, 1.75, 2.25; the last stays 2.62.
    ("captions: a word that begins with an apostrophe closes up to the word before (\"you're\", \"Aurora's\")",
     {"words": W(("you", 0.0, 0.25), ("'re", 0.25, 0.5), ("Aurora", 0.75, 1.0), ("'s", 1.0, 1.25), ("do", 1.5, 1.75),
                 ("n't", 1.75, 2.0), ("ok.", 2.25, 2.5))},
     [P(0.0, 2.64, [0, 1, 2, 3, 4, 5, 6], 0.0, 2.64)],
     [C("you're", 0.0, 0.75), C("Aurora's", 0.75, 1.5), C("do", 1.5, 1.75), C("n't", 1.75, 2.25), C("ok.", 2.25, 2.62)]),

    # The join happens only inside one piece (hers): a split between "Aurora" and "'s." keeps them apart.
    # [Aurora]: 0 to half way = (0.25 + 0.25) / 2 = 0.25. ['s.]: 0.25 - 0.08 = 0.17, moved up to 0.25; ends
    # 0.5 + 0.14 = 0.64; dur 0.39; at 0.25. "Aurora": 0 to 0.25, at least 0.3 s: 0.3, then moved to the next
    # start, 0.25. "'s.": 0.25 to 0.25 + (0.62 - 0.25) = 0.62.
    ("captions: the join is only inside one piece",
     {"words": W(("Aurora", 0.0, 0.25), ("'s.", 0.25, 0.5)), "splits": [1]},
     [P(0.0, 0.25, [0], 0.0, 0.25), P(0.25, 0.64, [1], 0.25, 0.39)],
     [C("Aurora", 0.0, 0.25), C("'s.", 0.25, 0.62)]),
]

for name, rec, want_p, want_c in CASES:
    before = copy.deepcopy(rec)
    got = T.pieces(rec)
    check("pieces: " + name, near(got, want_p), got)
    if want_c is not None:
        got = T.captions(rec)
        check("captions: " + name, near(got, want_c), got)
    check("  ... and the record is left as it was", rec == before)

# the last caption's end is not snapped, and a lone comma closes up (hers)
got = T.captions({"words": W(("well", 0.0, 0.25), (",", 0.25, 0.3), ("yes.", 0.5, 0.75))}, max_words=3)
# One piece 0 to 0.89. With three words to a line: "well" then "," ends the line (a comma ends one): "well ," reads
# "well,": 0 to 0.3 + 0.12 = 0.42. "yes.": 0.5 to 0.87. The first end moves to 0.5.
check("captions: a comma standing alone closes up (hers), with more than one word to a line",
      near(got, [C("well,", 0.0, 0.5), C("yes.", 0.5, 0.87)]), got)

# ---------------------------------------------------------------- kept
check("kept: every word not inside a cut", T.kept({"words": FIVE, "cut": [[1, 2], [4, 9]]}) == [True, False, False, True, False])
check("kept: no cuts keeps everything", T.kept({"words": FIVE}) == [True] * 5)

# ---------------------------------------------------------------- where each stretch is on the reel
rec = {"words": FIVE, "shots": [{"a": 1, "b": 2, "ns": [5], "spot": "pip"}]}
got = T.shot_spans(rec, T.pieces(rec))
# its piece is [b, c]: at 0.375 for 0.955
check("shot_spans: a stretch is where its pieces are", near(got, [{"at": 0.375, "dur": 0.955}]), got)
rec = {"words": FIVE, "shots": [{"a": 1, "b": 2, "ns": [5], "spot": "pip"}], "cut": [[1, 2]]}
got = T.shot_spans(rec, T.pieces(rec))
check("shot_spans: a stretch every word of which is cut is nowhere (None)", got == [None], got)
rec = {"words": FIVE, "shots": [{"a": 0, "b": 3, "ns": [1], "spot": "full"}, {"a": 2, "b": 4, "ns": [2], "spot": "center"}]}
got = T.shot_spans(rec, T.pieces(rec))
# Hers: a stretch has every piece whose FIRST word is inside it. The first (0 to 3) has both pieces, so it runs
# from 0 for 0.875 + 1.47 = 2.345; the second (2 to 4) has the second piece: at 0.875 for 1.47.
check("shot_spans: overlapping stretches, as hers works them out", near(got, [{"at": 0.0, "dur": 2.345}, {"at": 0.875, "dur": 1.47}]), got)

# ---------------------------------------------------------------- sentences


def run(n, long=None, words=None, step=0.5, length=0.25):
    """n words "w0".."w(n-1)", each `length` long, 0.25 s apart, except the pause after word k is long[k]."""
    out, t = [], 0.0
    for i in range(n):
        out.append({"w": (words or {}).get(i, f"w{i}"), "start": t, "end": t + length})
        t += length + (long or {}).get(i, step - length)
    return out


# Six words, then a pause of exactly 1.0 s (word 5 ends 2.75, word 6 starts 3.75): the sentence ends there.
check("sentences: a 1.0 s pause after six words ends a sentence", T.sentences(run(8, {5: 1.0})) == [[0, 5], [6, 7]], T.sentences(run(8, {5: 1.0})))
check("sentences: the same pause after five words does not", T.sentences(run(8, {4: 1.0})) == [[0, 7]])
check("sentences: a pause of 0.99 s does not", T.sentences(run(8, {5: 0.99})) == [[0, 7]])
check("sentences: nor when the word before the pause runs on (\"for\")", T.sentences(run(8, {5: 1.0}, {5: "for"})) == [[0, 7]])
check("sentences: ... or runs on with a comma (\"and,\")", T.sentences(run(8, {5: 1.0}, {5: "And,"})) == [[0, 7]])
check("sentences: . ? and ! end one", T.sentences(run(6, None, {1: "what?", 2: "no!", 4: "so."})) == [[0, 1], [2, 2], [3, 4], [5, 5]])
check("sentences: the last word always ends one", T.sentences(run(3)) == [[0, 2]])
check("sentences: no words, no sentences", T.sentences([]) == [])
# Thirty words with no end (31 here): at the 30th word (number 29) the run breaks at its widest pause, looked for
# from the 8th word (number 7) to number 28. The pause after word 12 is 0.75 s; the wider one after word 3 (0.9 s)
# is before the 8th word and doesn't count. So [0, 12], and the rest runs to the last word.
check("sentences: thirty words with no end break at the widest pause from the 8th word on",
      T.sentences(run(31, {3: 0.9, 12: 0.75})) == [[0, 12], [13, 30]], T.sentences(run(31, {3: 0.9, 12: 0.75})))
# Every pause the same: the first of them from the 8th word wins (number 7).
check("sentences: ... and at the 8th word when every pause is the same", T.sentences(run(31)) == [[0, 7], [8, 30]], T.sentences(run(31)))
check("sentences: twenty-nine words with no end are one sentence", T.sentences(run(29)) == [[0, 28]])

# ---------------------------------------------------------------- zooms, shots, and the older fields
z = T.zooms({"zooms": [{"a": 0, "b": 1, "kind": "punch"}, {"a": 2, "b": 2, "kind": "spin"}, {"a": 3, "b": 4, "kind": "zoom", "extra": 1}]})
check("zooms: punch and zoom only, as {a, b, kind}", z == [{"a": 0, "b": 1, "kind": "punch"}, {"a": 3, "b": 4, "kind": "zoom"}], z)
old = {"sentences": [[0, 1], [2, 4]], "moves": {"1": "zoom", "0": "", "7": "punch"}}
check("zooms: v23's moves (one per sentence) are read when there are no zooms", T.zooms(old) == [{"a": 2, "b": 4, "kind": "zoom"}], T.zooms(old))
check("zooms: ... and not when there are", T.zooms(dict(old, zooms=[{"a": 0, "b": 0, "kind": "punch"}])) == [{"a": 0, "b": 0, "kind": "punch"}])

s = T.shots({"shots": [{"a": 3, "b": 4, "ns": [2, "7", "x", True], "spot": "behind"},
                       {"a": 0, "b": 1, "ns": [1], "spot": "top", "pos": {"x": 0.5, "y": 0.4, "w": 0.6}},
                       {"a": 2, "b": 2, "ns": [9], "spot": "sideways"},
                       {"a": 5, "b": 6, "ns": [], "spot": "full"},
                       {"a": 7, "b": 8, "ns": [4], "v": "clip one.mov", "from": 2.5, "spot": "corner", "me": {"x": 0.8, "y": 0.2, "w": 0.3}},
                       {"a": 9, "b": 9, "ns": [4], "v": "../etc/passwd", "spot": "full"},
                       {"a": 10, "b": 10, "v": ".hidden.mov", "spot": "full"}]})
want = [{"a": 0, "b": 1, "ns": [1], "v": None, "from": 0.0, "spot": "center", "pos": {"x": 0.5, "y": 0.4, "w": 0.6}, "me": None},
        {"a": 3, "b": 4, "ns": [2, 7], "v": None, "from": 0.0, "spot": "full", "pos": None, "me": None},
        {"a": 7, "b": 8, "ns": [], "v": "clip one.mov", "from": 2.5, "spot": "corner", "pos": None, "me": {"x": 0.8, "y": 0.2, "w": 0.3}},
        {"a": 9, "b": 9, "ns": [4], "v": None, "from": 0.0, "spot": "full", "pos": None, "me": None}]
check("shots: in order of first word; Behind you reads as Full screen, Across the top as Center", s[:2] == want[:2], s[:2])
check("shots: a spot that isn't one, and a stretch with no photo and no video, are left out", len(s) == 4, s)
check("shots: a video stretch keeps its name and start, and no photos", s[2] == want[2], s[2])
check("shots: a video name that is a path or a hidden file is not a video (photos, if any, stand)", s[3] == want[3], s[3])
check("SPOTS are her four; behind and top are only read", set(T.SPOTS) == {"full", "pip", "center", "corner"} and T.OLD_SPOTS == {"behind": "full", "top": "center"})
oldp = {"sentences": [[0, 1], [2, 4], [5, 5]], "photos": {"1": {"n": 4, "spot": "behind"}, "0": {"n": "9", "spot": "weird"}, "2": {"n": 3, "spot": "top"}, "8": {"n": 1}}}
got = T.shots(oldp)
check("shots: v23's photos (one per sentence) are read when there are no shots",
      [(x["a"], x["b"], x["ns"], x["spot"]) for x in got] == [(0, 1, [9], "full"), (2, 4, [4], "full"), (5, 5, [3], "center")], got)
check("shots: ... and not when there are", len(T.shots(dict(oldp, shots=[{"a": 0, "b": 0, "ns": [1], "spot": "pip"}]))) == 1)
check("MOVES, SPEEDS, VIDEO_EXTS are hers", T.MOVES == ("", "punch", "zoom") and T.SPEEDS == (1.0, 1.25, 1.5, 2.0) and T.VIDEO_EXTS == (".mov", ".mp4", ".m4v"))
check("CONT: her 28 run-on words", len(T.CONT) == 28 and {"for", "the", "like", "i"} <= T.CONT)

# ---------------------------------------------------------------- clean
got = T.clean([{"w": "Hi", "start": 0.12345, "end": 0.5, "conf": 0.987}, {"w": "  ", "start": 1, "end": 2}, {"w": "no time"},
               "x", None, {"w": "there", "start": 1, "end": 1.5}, {"w": "bad", "start": "1", "end": 2}, {"w": 5, "start": 1, "end": 2}])
check("clean: times to 3 places, sureness to 2 (1 when unsaid); anything without a word and two times is left out",
      got == [{"w": "Hi", "start": 0.123, "end": 0.5, "conf": 0.99}, {"w": "there", "start": 1.0, "end": 1.5, "conf": 1.0}], got)
check("clean: cleaning a clean list changes nothing", T.clean(got) == got)
check("clean: nothing in, nothing out", T.clean(None) == [] and T.clean("words") == [])

# ---------------------------------------------------------------- a record that holds anything: never a crash
junk = {"words": FIVE + [{"w": "broken"}, 7],
        "sentences": "all of it",
        "cut": [[1], "x", [0, "a"], None, [9, 9], [1, 1], {"a": 1}],
        "splits": ["x", None, 3, 3.0, [1]],
        "speeds": [None, {"a": 0}, {"a": 0, "b": 0, "v": "fast"}, {"a": 3, "b": 4, "v": 2}],
        "zooms": ["x", {"kind": "punch"}, {"a": 0, "b": 0, "kind": "zoom"}],
        "shots": [3, {"a": "q", "b": 1, "ns": [1], "spot": "full"}, {"a": 1, "b": 2, "ns": [5], "spot": "pip", "pos": "left", "from": "x"}],
        "moves": "x", "photos": [1, 2]}
try:
    k, pcs, cps, zs, sh = T.kept(junk), T.pieces(junk), T.captions(junk), T.zooms(junk), T.shots(junk)
    sp = T.shot_spans(junk, pcs)
    ok = True
except Exception as e:  # noqa: BLE001
    ok, k, pcs = False, repr(e), None
check("a record full of things that can't be read never stops the engine", ok, k)
if ok:
    check("  ... the unreadable words are left out and the rest keep their numbers", len(k) == 5 and k == [True, False, True, True, True], k)
    check("  ... what can be read is used: the cut, the split, the speed, the zoom, the photo",
          [p["words"] for p in pcs] == [[0], [2], [3, 4]] and pcs[2]["speed"] == 2.0 and pcs[0]["zoom"] == 0
          and zs == [{"a": 0, "b": 0, "kind": "zoom"}] and len(sh) == 1 and sh[0]["pos"] is None and sh[0]["from"] == 0.0, pcs)
for empty in ({}, {"words": []}, {"words": None, "cut": None, "shots": None}):
    try:
        ok = T.pieces(empty) == [] and T.captions(empty) == [] and T.kept(empty) == [] and T.shots(empty) == [] and T.zooms(empty) == []
    except Exception as e:  # noqa: BLE001
        ok = False
    check(f"an empty record gives nothing, quietly ({empty!r})", ok)

# the wrong KIND of thing in a field (a number or true where a list belongs, a digit int() can't read): never a crash
for name, bad in (("cut is a number", {"cut": 5}), ("cut is true", {"cut": True}), ("splits is a number", {"splits": 7}),
                  ("speeds is true", {"speeds": True}), ("zooms is a number", {"zooms": 5}), ("shots is a number", {"shots": 5}),
                  ("shots is a word", {"shots": "full"}), ("a cut of '²'", {"cut": [["²", 3]]}), ("a split of '٣'", {"splits": ["٣"]}),
                  ("a photo number of '²'", {"shots": [{"a": 0, "b": 1, "ns": ["²", 2], "spot": "full"}]}),
                  ("v23 moves with sentences a number", {"moves": {"0": "punch"}, "sentences": 5}),
                  ("v23 photos with sentences a dict", {"photos": {"0": {"n": 1}}, "sentences": {"0": [0, 1]}}),
                  ("v23 photos with a spot that is a list", {"photos": {"0": {"n": 1, "spot": ["pip"]}}, "sentences": [[0, 4]]}),
                  ("a zoom whose kind is a list", {"zooms": [{"a": 0, "b": 1, "kind": ["zoom"]}]}),
                  ("a number too large to be one", {"cut": [[10 ** 400, 2]], "speeds": [{"a": 0, "b": 1, "v": 10 ** 400}], "splits": [10 ** 400]}),
                  ("words is a number", {"words": 5})):
    r = dict({"words": FIVE}, **bad)
    try:
        got = (T.kept(r), T.pieces(r), T.captions(r), T.zooms(r), T.shots(r), T.shot_spans(r, T.pieces(r)))
        ok = True
    except Exception as e:  # noqa: BLE001
        ok, got = False, repr(e)
    check(f"the wrong kind of thing never stops the engine: {name}", ok, got)
r = {"words": FIVE, "cut": 5, "splits": 7, "speeds": True, "zooms": 5, "shots": "full"}
check("  ... and reads as if that field were empty", T.pieces(r) == T.pieces({"words": FIVE}) and T.kept(r) == [True] * 5)
check("  ... a photo number int() can't read is left out, the rest of the stretch kept",
      T.shots({"words": FIVE, "shots": [{"a": 0, "b": 1, "ns": ["²", 2, "3"], "spot": "full"}]})[0]["ns"] == [2, 3])
for nothing in (None, 5, "x", [1]):
    try:
        ok = T.pieces(nothing) == [] and T.kept(nothing) == [] and T.shots(nothing) == [] and T.zooms(nothing) == [] and T.captions(nothing) == []
    except Exception as e:  # noqa: BLE001
        ok = False
    check(f"a record that is not a record at all gives nothing, quietly ({nothing!r})", ok)

# sentences in the record that don't cover the words are worked out again
got = T.pieces({"words": FIVE, "sentences": [[0, 1]]})
check("sentences that don't cover every word are worked out again from the words", [p["words"] for p in got] == [[0, 1, 2, 3, 4]], got)
got = T.pieces({"words": FIVE, "sentences": [[0, 1], [2, 4]]})
check("sentences that do are used as they are", [(p["words"], p["sentence"]) for p in got] == [([0, 1], 0), ([2, 3, 4], 1)], got)

# reel_seconds: the reel's length is each piece's time on the reel, added up (sped-up pieces count for less)
rec = {"words": FIVE, "speeds": [{"a": 3, "b": 4, "v": 2}]}
check("reel_seconds: the reel's own length (1.375 + 0.485 = 1.86), not the video's seconds (2.345)",
      abs(T.reel_seconds(T.pieces(rec)) - 1.86) < 1e-6, T.reel_seconds(T.pieces(rec)))

# her rules are text and start as hers do
check("RULES and PHOTO_RULES are her two blocks", T.RULES.startswith("How to cut a talking reel (Nicole, Nov 11)") and T.RULES.count("\n") == 8
      and T.PHOTO_RULES.startswith("How to place photos in a talking reel (Nicole, Nov 12)") and T.PHOTO_RULES.count("\n") == 7)

# standard library only, and it starts nothing
src = (ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts" / "talking.py").read_text(encoding="utf-8")
check("talking.py imports only math, opens nothing and starts nothing",
      [ln for ln in src.splitlines() if ln.startswith(("import ", "from "))] == ["import math"]
      and "open(" not in src and "subprocess" not in src and "expanduser" not in src)

print()
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
