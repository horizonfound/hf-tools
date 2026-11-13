#!/usr/bin/env python3
"""The arithmetic of a talking-to-camera reel (Nicole's handoffs v23 and v24, Nov 11 and 12, built our way).

A photographer talks to the camera about a shoot, messy, with restarts. Their talking becomes words with the time
of every word; the assistant cuts the script like an editor; photos and videos sit on the words they cover. This
file only works things out from a record: which words are kept, where the sentences end, which stretches of the
video play and when, where each photo lands on the reel, and the captions. It reads no file, writes none and
starts nothing. Standard library only; the same on a Mac and a PC.

The record (her field names; they are the page's contract):
    words      [{"w", "start", "end"}]         every word they said, with its seconds in the video
    sentences  [[first word, last word], ...]
    cut        [[first word, last word], ...]  words taken out
    splits     [word number, ...]              where they split a clip (that word starts a new piece)
    speeds     [{"a", "b", "v"}]               sped-up stretches (1.25, 1.5 or 2)
    zooms      [{"a", "b", "kind"}]            "punch" (a punch in) or "zoom" (a slow zoom); ours, and only when
                                               they chose one (Dustin, Nov 13): "amount" and "pace", see ZOOM_AMOUNT
    shots      [{"a", "b", "ns", "v", "from", "spot", "pos", "me"}]   photos (ns) or one Footage video (v) on words
    moves, photos                              v23's one-per-sentence fields, read only when the newer ones are empty

Her numbers, number for number: a pause over 0.45 s closes by itself; a piece starts 0.08 s before its first word
and ends 0.14 s after its last, or half way to the next kept word when that follows within 0.45 s; no moment plays
twice; a piece of 0.05 s or less is dropped. A sentence ends on . ? ! or at a pause of 1 s or more once it has six
words, unless its last word plainly runs on; thirty words with no end break at the widest pause from the eighth
word on. A caption is one word, on screen from its start to 0.12 s past its end, at least 0.3 s, and each one's
end is moved to the next one's start.

Ours, not hers: anything in a record that can't be read (a cut that isn't two numbers, a word with no time) is
left out instead of stopping everything; and a caption closes up every word that begins with an apostrophe
("you 're" shows as "you're"), where hers closed up only "'s".
"""
import math

VIDEO_EXTS = (".mov", ".mp4", ".m4v")                    # hers
SPOTS = ("full", "pip", "center", "corner")              # hers, v24: Full screen, Full screen you in the corner, Center, Small corner
OLD_SPOTS = {"behind": "full", "top": "center"}          # hers: Behind you and Across the top were dropped (Nicole, Nov 12); read only
MOVES = ("", "punch", "zoom")                            # hers
SPEEDS = (1.0, 1.25, 1.5, 2.0)                           # hers

# How much and how fast a zoom moves (Dustin, Nov 13: the steady zoom felt "robotic", he wanted the amount and the
# speed, and chose presets over sliders: "keep it simple and consistent"). Every number is here and nowhere else:
# the CapCut builder and the page's preview both read these. FIRST VALUES, to be tuned by eye.
#   amount: the scale the zoom ends on. Medium is hers exactly (a slow zoom to 1.12, a punch in at 1.15), and is
#           what a zoom with no "amount" has. A punch in's Subtle is half its extra, its Strong 1.6 times it.
#   pace:   a slow zoom moves across its whole stretch ("whole", hers, the default) or in its first second and
#           then holds ("quick"); a punch in is simply closer from its first frame ("instant", hers, the default)
#           or pushes in over about a third of a second and then holds ("push").
# A default is never written into a record: a zoom nobody set has only a, b and kind, as it always had.
ZOOM_AMOUNT = {"zoom": {"subtle": 1.06, "medium": 1.12, "strong": 1.20},
               "punch": {"subtle": 1.075, "medium": 1.15, "strong": 1.24}}
ZOOM_AMOUNTS = ("subtle", "medium", "strong")            # the order the page shows them in
AMOUNT_DEFAULT = "medium"
ZOOM_PACE = {"zoom": ("quick", "whole"), "punch": ("instant", "push")}       # the order the page shows them in
PACE_DEFAULT = {"zoom": "whole", "punch": "instant"}
MOVE_SECS = {"quick": 1.0, "push": 0.35}                 # how long the move takes (or the whole stretch, if shorter)


def ease(x):
    """How far along a moving zoom is (0 to 1) when `x` (0 to 1) of its time has gone: slow, quicker, slow again
    (smoothstep), in place of a steady speed. The ONE curve: the page's preview has the same line of arithmetic,
    and the CapCut project is written as points on it. ease(0) is 0, ease(.5) is .5 and ease(1) is 1, exactly."""
    x = min(1.0, max(0.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


def zoom_amount(z):
    """The scale a zoom ends on (ZOOM_AMOUNT). Anything unreadable is Medium, hers."""
    z = z if isinstance(z, dict) else {}
    table = ZOOM_AMOUNT.get(z.get("kind")) or ZOOM_AMOUNT["zoom"]
    a = z.get("amount")
    return table[a] if isinstance(a, str) and a in table else table[AMOUNT_DEFAULT]


def zoom_pace(z):
    """A zoom's pace by name (ZOOM_PACE). Anything unreadable, or a pace of the other kind, is that kind's own."""
    z = z if isinstance(z, dict) else {}
    kind = z.get("kind") if z.get("kind") in ZOOM_PACE else "zoom"
    p = z.get("pace")
    return p if isinstance(p, str) and p in ZOOM_PACE[kind] else PACE_DEFAULT[kind]


def zoom_move(z, span):
    """How long a zoom's move lasts, in the units of `span` when a second is 1 (seconds on the reel): the whole
    stretch for a slow zoom's "whole", MOVE_SECS (or the stretch, if shorter) for "quick" and "push", and 0 for a
    punch in's "instant" (no move: the stretch is simply closer)."""
    pace = zoom_pace(z)
    if pace == "instant":
        return 0.0
    if pace == "whole":
        return float(span)
    return min(float(span), MOVE_SECS[pace])


def zoom_value(z, t, span):
    """THE function of time: a zoom's scale `t` seconds into its stretch of `span` seconds on the reel. 1.0 at the
    start of a move, the amount from the move's end on. The page's preview draws this; CapCut gets points on it."""
    end = zoom_amount(z)
    move = zoom_move(z, span)
    if move <= 0:
        return end
    return 1.0 + (end - 1.0) * ease(t / move)
BIG = 10 ** 12                                           # ours: no word number, photo number or second is ever larger

# hers: a sentence never ends on one of these (the word plainly runs on: "the shoot for / Aurora's family")
CONT = {"for", "the", "a", "an", "to", "and", "of", "with", "at", "in", "on", "my", "her", "his", "their", "our", "your",
        "i", "we", "so", "but", "or", "is", "was", "were", "that", "this", "like"}

# Hers, word for word and line for line (talking.py, v24). Printed by `talking_rec.py show` every time.
RULES = """How to cut a talking reel (Nicole, Nov 11): you're the editor of what they said, never the writer.
  KEEP their words and their order. Cut only: the warm-up and sign-off that aren't the story ("OK so this is my
  test", "the end"), restarts and false starts (keep the LAST, complete take: "Her kids were picking up. Her older
  kids. Her, her, her older kids were picking up the baby" keeps "her older kids were picking up the baby"), words
  said twice ("when when"), and filler that breaks the flow ("um", "uh", "like" when it's filler). Pauses close by
  themselves (anything over 0.45 s), so don't cut for those.
  NEVER cut to change what they meant, never stitch half-sentences into something they didn't say, and never add.
  When in doubt, keep it: they can cut more on the page in one click.
  Then tell them in one line what you took out, and that it's on the page to watch."""

# Hers, word for word and line for line (talking.py, v24). Printed by `talking_rec.py photos` every time.
PHOTO_RULES = """How to place photos in a talking reel (Nicole, Nov 12): choosing and ordering photos is yours; the words are theirs.
  Put each photo with the words it shows when you can ("we were at the beach" -> the beach), otherwise the strongest
  frames, in a flow that changes one thing at a time (the curating rules). Leave the first line on them talking, so
  people meet them before the photos start. Mostly "pip" (full screen, them small in the corner) so they stay in the
  reel, with a few "full" where a photo should land on its own, and "center" now and then for a calmer beat.
  Several photos flashing through ("ns" with 3 to 6) suit a list, a quick run of moments, or a longer stretch.
  Never the same photo twice in a row, and don't use every photo. Cover kept words only, and no two stretches overlap.
  Then tell them in one line what you did, and that they can click any photo on the page to change it."""


# ---------- reading a record that may hold anything ----------

def _num(v):
    """A real, finite number (never True or False), or None."""
    if type(v) is int:
        return v if abs(v) <= BIG else None                 # a whole number too large to be a time or a size: not one
    if type(v) is float and math.isfinite(v):
        return v
    return None


def _d(rec):
    """The record as a dict (anything else reads as an empty one)."""
    return rec if isinstance(rec, dict) else {}


def _list(rec, key):
    """A field that should be a list: the list, or an empty one when the record holds anything else there
    (a number, a word, true). Hers stops on those; a record like that must never stop the page."""
    v = _d(rec).get(key)
    return v if isinstance(v, list) else []


def _whole(v):
    """A whole number from a record: an int, a float with nothing after the point, or a string of digits (with a
    minus). None for anything else. (Hers calls int() and stops on the first value it can't read.)"""
    if type(v) is int:
        return v if abs(v) <= BIG else None
    if type(v) is float and math.isfinite(v) and abs(v) <= BIG and v == int(v):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        body = s[1:] if s.startswith("-") else s
        # the ten plain digits only: "²" and "٣" count as digits to isdigit() and int() then refuses or misreads them
        if body and len(body) <= 12 and all(c in "0123456789" for c in body):
            return int(s)
    return None


def _pair(x):
    """[a, b] as two whole numbers, or None."""
    if isinstance(x, (list, tuple)) and len(x) == 2:
        a, b = _whole(x[0]), _whole(x[1])
        if a is not None and b is not None:
            return a, b
    return None


def _word_ok(x):
    return (isinstance(x, dict) and isinstance(x.get("w"), str) and x["w"].strip() != ""
            and _num(x.get("start")) is not None and _num(x.get("end")) is not None)


def clean(words):
    """The words as they are kept: every entry with a word and two times, times rounded to 3 places and how sure
    the computer was ("conf", 1 when it didn't say) to 2 (hers, when a video has just been turned into words).
    Anything else is left out. Cleaning a clean list changes nothing."""
    out = []
    for x in words if isinstance(words, (list, tuple)) else []:
        if not _word_ok(x):
            continue
        conf = _num(x.get("conf"))
        out.append({"w": x["w"], "start": round(float(x["start"]), 3), "end": round(float(x["end"]), 3),
                    "conf": round(float(1 if conf is None else conf), 2)})
    return out


def _words(rec):
    """The record's words, as they are when every one can be read (so every word keeps its number), else cleaned."""
    w = _d(rec).get("words")
    if isinstance(w, list) and all(_word_ok(x) for x in w):
        return w
    return clean(w)


def _sents(rec, words):
    """The record's sentences when they are whole (pairs that follow one another and cover every word), else
    worked out again from the words."""
    s = _d(rec).get("sentences")
    n = len(words)
    if isinstance(s, list) and s:
        at, ok = 0, True
        for x in s:
            p = _pair(x)
            if p is None or p[0] != at or p[1] < p[0]:
                ok = False
                break
            at = p[1] + 1
        if ok and at == n:
            return [list(_pair(x)) for x in s]
    return sentences(words)


# ---------- the words ----------

def sentences(words):
    """Hers: split the words into sentences, so each holds a whole thought to put a photo with: at . ? ! ; at a
    pause of 1 s or more once there are 6 words, unless the last word plainly runs on; and a very long run (30
    words) splits at its longest pause from the 8th word on. [[first, last], ...]"""
    words = words if isinstance(words, list) and all(_word_ok(x) for x in words) else clean(words)
    out, start = [], 0
    for i, w in enumerate(words):
        last = i == len(words) - 1
        gap = (words[i + 1]["start"] - w["end"]) if not last else 0
        word = w["w"].rstrip()
        runs_on = word.lower().strip(",.") in CONT
        if last or word.endswith((".", "?", "!")) or (gap >= 1.0 and i - start >= 5 and not runs_on):
            out.append([start, i])
            start = i + 1
        elif i - start >= 29:                               # too long: break at its longest pause
            k = max(range(start + 7, i), key=lambda m: words[m + 1]["start"] - words[m]["end"])
            out.append([start, k])
            start = k + 1
    return out


def kept(rec):
    """Hers: which words are kept, every word not inside a cut. [True, False, ...], one per word."""
    rec = _d(rec)
    n = len(_words(rec))
    keep = [True] * n
    for x in _list(rec, "cut"):
        p = _pair(x)
        if p is None:
            continue
        for i in range(max(0, p[0]), min(n - 1, p[1]) + 1):
            keep[i] = False
    return keep


def zooms(rec):
    """Hers: zooms as word ranges [{"a", "b", "kind": "punch" | "zoom"}]. Older records kept one per sentence
    ("moves"), read only when there are no zooms. Ours: "amount" and "pace" come along only when they are set to
    something other than what a zoom has by itself, so a zoom nobody set reads exactly as it always did."""
    rec = _d(rec)
    z = []
    for x in _list(rec, "zooms"):
        if not isinstance(x, dict) or x.get("kind") not in ("punch", "zoom"):
            continue
        a, b = _whole(x.get("a")), _whole(x.get("b"))
        if a is None or b is None:
            continue
        r = {"a": a, "b": b, "kind": x["kind"]}
        am, pc = x.get("amount"), x.get("pace")
        if isinstance(am, str) and am in ZOOM_AMOUNT[r["kind"]] and am != AMOUNT_DEFAULT:
            r["amount"] = am
        if isinstance(pc, str) and pc in ZOOM_PACE[r["kind"]] and pc != PACE_DEFAULT[r["kind"]]:
            r["pace"] = pc
        z.append(r)
    moves = rec.get("moves")
    if not z and isinstance(moves, dict) and moves:
        sents = _list(rec, "sentences")
        for k, v in moves.items():
            i = _whole(k)
            if isinstance(v, str) and v in ("punch", "zoom") and i is not None and 0 <= i < len(sents) and _pair(sents[i]):
                a, b = _pair(sents[i])
                z.append({"a": a, "b": b, "kind": v})
    return z


def _box(v):
    """A {x, y, w} they dragged something to, as it was saved; None for none (or for one that can't be read)."""
    if isinstance(v, dict) and all(_num(v.get(k)) is not None for k in ("x", "y", "w")):
        return {"x": v["x"], "y": v["y"], "w": v["w"]}
    return None


def _video_name(v):
    """A stretch's video: a plain file name (hers: no "/" and no leading dot; ours: no "\\" either), or None."""
    if isinstance(v, str) and v and "/" not in v and "\\" not in v and "\x00" not in v and not v.startswith("."):
        return v
    return None


def shots(rec):
    """Hers: photos as word ranges, in order of their first word:
    [{"a", "b", "ns": [photo numbers, shown one after another], "v": a video in the shoot's Footage folder
    instead (and "from", where it starts, in seconds), "spot", "pos": {x, y, w} or None, "me": {x, y, w} or None}].
    pos is where they put the photo on the screen (its centre and its width, as parts of the screen); me is where
    they put themselves for "you in the corner". Behind you reads as Full screen and Across the top as Center.
    Older records kept one photo per sentence ("photos"), read only when there are no shots."""
    rec = _d(rec)
    out = []
    for x in _list(rec, "shots"):
        if not isinstance(x, dict):
            continue
        a, b = _whole(x.get("a")), _whole(x.get("b"))
        if a is None or b is None:
            continue
        ns = [k for k in (_whole(n) for n in (x.get("ns") if isinstance(x.get("ns"), (list, tuple)) else [])) if k is not None and k >= 0]
        spot = x.get("spot") if isinstance(x.get("spot"), str) else None
        spot = OLD_SPOTS.get(spot, spot)
        v = _video_name(x.get("v"))
        frm = _num(x.get("from"))
        if (ns or v) and spot in SPOTS:
            out.append({"a": a, "b": b, "ns": [] if v else ns, "v": v, "from": float(frm or 0),
                        "spot": spot, "pos": _box(x.get("pos")), "me": _box(x.get("me"))})
    photos = rec.get("photos")
    if not out and isinstance(photos, dict) and photos:
        sents = _list(rec, "sentences")
        old = []
        for k, v in photos.items():
            i = _whole(k)
            n = _whole(v.get("n")) if isinstance(v, dict) else None
            if i is None or n is None or not (0 <= i < len(sents)) or not _pair(sents[i]):
                continue
            old.append((i, n, v.get("spot") if isinstance(v.get("spot"), str) else None))
        for i, n, spot in sorted(old, key=lambda t: t[0]):
            a, b = _pair(sents[i])
            spot = OLD_SPOTS.get(spot, spot) if isinstance(spot, str) and (spot in SPOTS or spot in OLD_SPOTS) else "full"
            out.append({"a": a, "b": b, "ns": [n], "v": None, "from": 0.0, "spot": spot, "pos": None, "me": None})
    return sorted(out, key=lambda x: x["a"])


def shot_spans(rec, pcs):
    """Hers: where each shot is on the reel, [{"at", "dur"} or None], from the pieces (which break at every shot's
    edge). None for a stretch none of whose pieces is left (every word cut)."""
    out = []
    for x in shots(rec):
        on = [p for p in pcs if x["a"] <= p["words"][0] <= x["b"]]
        out.append({"at": on[0]["at"], "dur": round(on[-1]["at"] + on[-1]["dur"] - on[0]["at"], 3)} if on else None)
    return out


def pieces(rec, gap=0.45, pad_in=0.08, pad_out=0.14):
    """Hers: the kept stretches of the video, in play order. A new piece starts where a cut, a pause longer than
    `gap`, a new sentence, a split they made, a change of speed, the edge of a zoom or the edge of a photo stretch
    falls. Each: {"from", "to" (seconds in the video), "speed", "zoom" (its place in zooms(), or None),
    "sentence", "words", "at", "dur" (seconds on the reel)}. A piece takes the speed and zoom of its first word."""
    rec = _d(rec)
    words = _words(rec)
    keep, sents = kept(rec), _sents(rec, words)
    n = len(words)
    sid = {}
    for k, (a, b) in enumerate(sents):
        for i in range(a, b + 1):
            sid[i] = k
    splits = set()
    for x in _list(rec, "splits"):
        if _whole(x) is not None:
            splits.add(_whole(x))
    speed = [1.0] * n
    for r in _list(rec, "speeds"):
        if not isinstance(r, dict):
            continue
        a, b, v = _whole(r.get("a")), _whole(r.get("b")), _num(r.get("v"))
        if a is None or b is None or v is None:
            continue
        for i in range(max(0, a), min(n - 1, b) + 1):
            speed[i] = float(v) if float(v) in SPEEDS else 1.0
    zoom = [None] * n
    for k, r in enumerate(zooms(rec)):
        for i in range(max(0, r["a"]), min(n - 1, r["b"]) + 1):
            zoom[i] = k
    shot = [None] * n                                       # a photo starts or ends: a new piece, so it lands exactly
    for k, r in enumerate(shots(rec)):
        for i in range(max(0, r["a"]), min(n - 1, r["b"]) + 1):
            shot[i] = k                                     # where two overlap, the later one has the word
    out, cur = [], []
    for i, w in enumerate(words):
        if not keep[i]:
            if cur:
                out.append(cur)
                cur = []
            continue
        if cur and (w["start"] - words[cur[-1]]["end"] > gap or sid.get(i) != sid.get(cur[-1]) or i in splits
                    or speed[i] != speed[cur[-1]] or zoom[i] != zoom[cur[-1]] or shot[i] != shot[cur[-1]]):
            out.append(cur)
            cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    res, at = [], 0.0
    for c in out:
        a = max(0.0, words[c[0]]["start"] - pad_in)
        b = words[c[-1]]["end"] + pad_out
        nxt = c[-1] + 1                                     # touching the next kept word: meet it half way, no overlap
        if nxt < n and keep[nxt] and words[nxt]["start"] - words[c[-1]]["end"] <= gap:
            b = (words[c[-1]]["end"] + words[nxt]["start"]) / 2
        if res and a < res[-1]["to"]:                       # never play the same moment twice
            a = res[-1]["to"]
        if b - a > 0.05:
            sp = speed[c[0]]
            res.append({"from": round(a, 3), "to": round(b, 3), "speed": sp, "zoom": zoom[c[0]], "sentence": sid.get(c[0]),
                        "words": c, "at": round(at, 3), "dur": round((b - a) / sp, 3)})
            at += (b - a) / sp
    return res


def _caption_text(ws):
    """The words of one caption: a space between words, none before a word that begins with an apostrophe (ours:
    every such word; hers closed up only "'s"), and none before a comma standing alone (hers)."""
    text = ""
    for w in ws:
        text += w if (not text or w.startswith("'")) else " " + w
    return text.replace(" ,", ",").strip()


def captions(rec, max_words=1):
    """Hers: captions from the kept words, in reel time: [{"text", "start", "end"}]. One word at a time (Nicole,
    Nov 11), each on screen until the next one; a word that begins with an apostrophe stays with the word before
    it, inside one piece only. The last caption's end is left where it falls."""
    words = _words(rec)
    out = []
    for p in pieces(rec):
        line = []

        def on(t, p=p):                                     # a moment in the video -> on the reel
            return p["at"] + (t - p["from"]) / p["speed"]

        for k, i in enumerate(p["words"]):
            line.append(i)
            w = words[i]["w"]
            nxt = words[p["words"][k + 1]]["w"] if k + 1 < len(p["words"]) else ""
            if nxt.startswith("'"):
                continue
            if len(line) >= max_words or w.endswith((".", ",", "?", "!")) or k == len(p["words"]) - 1:
                a = on(max(p["from"], words[line[0]]["start"]))
                b = on(min(p["to"], words[line[-1]]["end"] + 0.12))
                out.append({"text": _caption_text([words[j]["w"] for j in line]), "start": round(a, 3), "end": round(max(b, a + 0.3), 3)})
                line = []
    for k in range(len(out) - 1):                           # no gaps or overlaps between lines
        out[k]["end"] = out[k + 1]["start"]
    return out


def reel_seconds(pcs):
    """How long the reel is: each piece's time on the reel, added up (the number the page shows)."""
    return sum(p["dur"] for p in pcs)
