#!/usr/bin/env python3
"""The carousel designer's FIRST design for a shoot: an example laid out like a magazine story (Nicole, Nov 23).

Nicole, asked what the designer should open with the first time: "open with a first carousel as an example. Give
the carousel variety and make it engaging. Don't crop any heads. Center images so they look beautiful and really
tell a story like a magazine editorial would."

Before this the first visit made one photo per slide, each filling its slide. Now design.ensure_design asks
first_state() here, and gets a layout with a mix across its slides: a full-slide opener, two photos together, a
photo across two slides, a photo with a white border, a smaller photo on a quiet last slide. It is an EXAMPLE and
nothing more: a design like any other, changed and saved like any other; an existing design is never rebuilt, and
"+ New design" keeps its own choices (Blank, One photo per slide, the templates).

EVERYTHING HERE IS A RULE. Nothing looks at a photo by eye, and no words are put on a slide (rule 11). The rules:

  * Which photos. The carousel picker's order when the shoot has one (theirs, or the Assistant's pick when they
    asked for one): its first photos, and its last photo as the closer. With no order yet, POOL_MOST photos spread
    evenly from the first to the last of the shoot, so the example runs from the start of the shoot to its end.
  * Shapes. A photo is tall, wide or square by its own width and height (SQUARE says how near to square counts).
  * No head is cut (her "Don't crop any heads"). On a Mac the faces in each photo's small copy are found by
    faces.py (the Mac's own Vision, the 520 px copy only). Around each face a HEAD box is drawn with headroom
    (HEAD_TOP above, HEAD_SIDE each side, HEAD_BELOW under). A frame that shows only part of its photo is used
    only when every head box lies wholly inside what the frame shows; the photo is centered in its frame, and
    moved off center only as far as it must be to keep a head in. When that can't be had, the photo gets a frame of
    its own shape, which shows the whole photo. A photo across two slides is never used when a head would lie on
    the seam between the two slides.
  * A crop is also never a big one: a frame must show at least FULL_SHOWS of its photo each way.
  * Variety. No two slides next to each other are laid out the same way (CYCLE is the order the layouts are
    tried in, and the one just used is skipped).
  * How many. Up to SLIDES_MOST slides; fewer photos make fewer slides (one photo: one slide).

A PC HAS NO FACE FINDER, and a Mac whose Vision does not answer is the same: where nobody could look, cutting into
a photo would be a guess, so the photo is shown whole (a frame of its own shape) unless the frame would keep at
least GUESS_SHOWS of it, and no photo is laid across two slides (the seam would be a guess too). The example is
then made of whole photos: bordered, in pairs, and small on the last slide.

    python3 design_first.py plan "<kit folder name>"     print the example that would be made (changes nothing)

Python 3.9, standard library only.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import this_computer  # noqa: E402
this_computer.utf8_output()

W, H = 1080, 1350                   # one slide (design.py's own; checked against it by the test)
SLIDES_MOST = 10                    # "about 6 to 10 slides" (the brief); fewer photos make fewer
POOL_MOST = 12                      # the most photos the example draws from (a pair takes two)
SQUARE = 0.13                       # a photo within this of square (w / h between 0.87 and 1.15) is "square"
HEAD_TOP, HEAD_SIDE, HEAD_BELOW = 0.6, 0.3, 0.25    # headroom round a face box, as parts of the face's own size
FULL_SHOWS = 0.75                   # a frame that cuts into its photo must still show this much of it, each way
GUESS_SHOWS = 0.93                  # nobody could look for faces: only a crop that keeps this much is not a guess
SPREADS_MOST = 2                    # photos laid across two slides, at the most
SPREAD_NEEDS_FACES = True           # with no face finder no photo goes across two slides (the seam would be a guess)
MARGIN, GAP = 70, 24                # design.py's starters' own margin and gap
BORDER_BOX = (90, 110, 900, 1130)   # "One with a border" (design.SINGLES cs-border): a photo with white round it
INSET_BOX = (190, 235, 700, 880)    # the same idea, smaller, so two bordered slides in a row never look alike
CLOSER_BOX = (230, 290, 620, 770)   # the last slide: one smaller photo, whole, in the middle of the slide
CYCLE = ("pair", "spread", "border", "full", "inset")       # the order the layouts are tried in for the middle slides
MAKE_WAIT = 25.0                    # seconds, in all, the first open may spend making small copies to look at
PLAIN_FOR_TESTS = "STUDIO_FIRST_DESIGN_FOR_TESTS"   # set to "plain" ONLY by tests that need the old one-photo-per-slide start


def plain_for_tests():
    return os.environ.get(PLAIN_FOR_TESTS) == "plain"


def can_look():
    """Can this computer find faces? A Mac: yes (Vision, through faces.py). A PC: no. In a test, whatever
    FACES_PRETEND says ("none": a computer with no face finder)."""
    pretend = os.environ.get("FACES_PRETEND")
    if pretend:
        return pretend != "none"
    return bool(this_computer.MAC)


# ---------- the rules, as plain functions (no file is read below this line until gather) ----------

def shape(a):
    """"tall", "wide" or "square" from a photo's width / height; None when its size is not known."""
    if not a or a <= 0:
        return None
    if a > 1 + SQUARE + 0.02:
        return "wide"
    if a < 1 - SQUARE:
        return "tall"
    return "square"


def head_box(face):
    """A face box [x, y, w, h] (from the top left, parts of the photo) grown to hold the whole head with headroom,
    and kept on the photo (a head the photo itself cuts can't be put back)."""
    x, y, w, h = face
    x0, y0 = max(0.0, x - HEAD_SIDE * w), max(0.0, y - HEAD_TOP * h)
    x1, y1 = min(1.0, x + w + HEAD_SIDE * w), min(1.0, y + h + HEAD_BELOW * h)
    return x0, y0, x1, y1


def _place(v, spans):
    """Where a window v wide (a part of the photo, 0 to 1) starts so that every span (lo, hi) lies inside it: the
    middle when that works, else as near the middle as keeps them all in. None when they can't all be in."""
    if v >= 0.9995:
        return 0.0
    mid = (1 - v) / 2
    if not spans:
        return mid
    lo, hi = min(s[0] for s in spans), max(s[1] for s in spans)
    if hi - lo > v + 1e-9:
        return None
    least, most = max(0.0, hi - v), min(1 - v, lo)
    if least > most + 1e-9:
        return None
    return min(max(mid, least), most)


def shows(fw, fh, a):
    """How much of a photo of shape a (w / h) a frame fw by fh shows when the photo fills it: (across, down)."""
    fa = fw / fh
    return (fa / a, 1.0) if a >= fa else (1.0, a / fa)


def crop(fw, fh, p, seam=None):
    """The crop for photo p filling a frame fw by fh: {"ox", "oy"} (design.py's own crop numbers, zoom 1), or None
    when this frame may not be used for this photo (a head would be cut, too much of the photo would be lost, or
    nobody could look and cutting would be a guess). seam: a place across the frame (0 to 1) where one slide ends
    and the next begins; no head may lie on it."""
    a = p.get("a")
    if not a:
        return None
    vw, vh = shows(fw, fh, a)
    whole = min(vw, vh) >= 0.995
    faces = p.get("faces")
    if faces is None:                           # nobody looked at this photo
        if seam is not None and SPREAD_NEEDS_FACES:
            return None
        return {"ox": 0.5, "oy": 0.5} if (whole or min(vw, vh) >= GUESS_SHOWS) else None
    if not whole and min(vw, vh) < FULL_SHOWS:
        return None
    heads = [head_box(f) for f in faces]
    x0 = _place(vw, [(b[0], b[2]) for b in heads])
    y0 = _place(vh, [(b[1], b[3]) for b in heads])
    if x0 is None or y0 is None:
        return None
    if seam is not None:
        at = x0 + vw * seam                     # the seam, as a place across the photo
        if any(b[0] < at < b[2] for b in heads):
            return None
    ox = round(x0 / (1 - vw), 4) if vw < 0.9995 else 0.5
    oy = round(y0 / (1 - vh), 4) if vh < 0.9995 else 0.5
    return {"ox": min(1.0, max(0.0, ox)), "oy": min(1.0, max(0.0, oy))}


def fit(a, box):
    """A frame of the photo's own shape (so the whole photo shows), as large as fits the box (x, y, w, h) and in its
    middle. A photo whose size is not known takes the box itself."""
    x, y, w, h = box
    if not a:
        return x, y, w, h
    fw, fh = (w, w / a) if w / a <= h else (h * a, h)
    return x + (w - fw) / 2, y + (h - fh) / 2, fw, fh


def _frame(p, x, y, w, h, c=None):
    c = c or {"ox": 0.5, "oy": 0.5}
    return {"n": p["n"], "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2), "ox": c["ox"], "oy": c["oy"], "zoom": 1}


def _whole(kind, p, box):
    return {"kind": kind, "slides": 1, "photos": [p["n"]], "frames": [_frame(p, *fit(p.get("a"), box))]}


def unit(kind, ps, room, spreads=0):
    """One layout for the photos at the front of ps, or None when it does not suit them. A unit is {"kind", "slides",
    "photos": the numbers it uses, "frames": frames on a strip that starts at 0}. room: slides still free."""
    if not ps or room < 1:
        return None
    p = ps[0]
    if kind == "full":
        c = crop(W, H, p)
        return {"kind": kind, "slides": 1, "photos": [p["n"]], "frames": [_frame(p, 0, 0, W, H, c)]} if c else None
    if kind == "spread":
        if room < 2 or spreads >= SPREADS_MOST or shape(p.get("a")) != "wide":
            return None
        c = crop(2 * W, H, p, seam=0.5)
        return {"kind": kind, "slides": 2, "photos": [p["n"]], "frames": [_frame(p, 0, 0, 2 * W, H, c)]} if c else None
    if kind == "pair":
        if len(ps) < 2:
            return None
        q = ps[1]
        sp, sq = shape(p.get("a")), shape(q.get("a"))
        if sp is None or sq is None or (sp == "wide") != (sq == "wide"):
            return None
        if sp == "wide":                        # two wide photos, one over the other (design.SINGLES cs-2t's boxes)
            hh = H / 2 - 1.5 * MARGIN
            boxes = [(MARGIN, MARGIN, W - 2 * MARGIN, hh), (MARGIN, H / 2 + MARGIN / 2, W - 2 * MARGIN, hh)]
        else:                                   # two tall photos side by side
            ww = (W - 2 * MARGIN - GAP) / 2
            boxes = [(MARGIN, MARGIN, ww, H - 2 * MARGIN), (MARGIN + ww + GAP, MARGIN, ww, H - 2 * MARGIN)]
        return {"kind": kind, "slides": 1, "photos": [p["n"], q["n"]],
                "frames": [_frame(p, *fit(p["a"], boxes[0])), _frame(q, *fit(q["a"], boxes[1]))]}
    if kind == "border":
        return _whole(kind, p, BORDER_BOX)
    if kind == "inset":
        return _whole(kind, p, INSET_BOX)
    if kind == "closer":
        return _whole(kind, p, CLOSER_BOX)
    return None


def plan(photos, ours=False):
    """The example's layouts, in order, for these photos [{"n", "a": w / h or None, "faces": [[x, y, w, h], ...] or
    None when nobody looked}], which are already the ones to use, in order. ours: the order is not the
    photographer's (the shoot has no carousel order), so the first photo that can fill a slide may open it."""
    ps = list(photos)[:POOL_MOST]
    if not ps:
        return []
    if ours:
        for i, p in enumerate(ps[:-1] if len(ps) > 1 else ps):
            if unit("full", [p], 1):
                ps.insert(0, ps.pop(i))
                break
    units = [unit("full", ps[:1], 1) or unit("border", ps[:1], 1)]
    ps = ps[1:]
    last = ps.pop() if ps else None
    room = SLIDES_MOST - 1 - (1 if last else 0)
    turn, spreads = 0, 0
    while ps and room > 0:
        before = units[-1]["kind"]
        got = None
        for k in range(len(CYCLE)):
            kind = CYCLE[(turn + k) % len(CYCLE)]
            if kind == before:
                continue
            got = unit(kind, ps, room, spreads)
            if got:
                turn = (turn + k + 1) % len(CYCLE)
                break
        if got is None:                         # can't happen (border and inset always suit); kept so nothing ever stops here
            got = unit("inset" if before == "border" else "border", ps, room)
        units.append(got)
        ps = ps[len(got["photos"]):]
        room -= got["slides"]
        spreads += 1 if got["kind"] == "spread" else 0
    if last:
        units.append(unit("closer", [last], 1))
    return units


def state_of(units, bg="#ffffff"):
    """The layout design.py stores, from the units: frames numbered and placed slide after slide. None for no units."""
    blocks, at = [], 0
    for u in units:
        for f in u["frames"]:
            blocks.append(dict(f, id=len(blocks) + 1, x=round(f["x"] + at * W, 2), slot=len(blocks) + 1))
        at += u["slides"]
    if not blocks:
        return None
    return {"slides": at, "bg": bg, "blocks": blocks}


def pool(order, on_sheet):
    """Which photos the example draws from, and whether the choice is ours. order: the carousel picker's order;
    on_sheet: every photo number of the shoot, in the list's order."""
    have = set(on_sheet)
    order = [n for i, n in enumerate(order) if n in have and n not in order[:i]]
    if order:
        if len(order) > POOL_MOST:
            order = order[:POOL_MOST - 1] + [order[-1]]
        return order, False
    nums = list(on_sheet)
    if len(nums) > POOL_MOST:
        step = (len(nums) - 1) / (POOL_MOST - 1)
        nums = [nums[int(round(i * step))] for i in range(POOL_MOST)]
        nums = [n for i, n in enumerate(nums) if n not in nums[:i]]
    return nums, True


# ---------- the photos themselves: their shapes, and where the faces are ----------

def gather(kit, rec, rows, nums):
    """What the rules need about each photo: [{"n", "a", "faces"}], in nums' order. On a computer that can look for
    faces, a photo whose small copy is not made yet has it made now (the picker's own copy, arrange.make_one; at
    most MAKE_WAIT seconds in all), then every one is looked at in one go (faces.for_kit, which keeps what it
    finds). "faces" is None for a photo nobody could look at."""
    import arrange
    by = {r["n"]: r for r in rows}
    found = {}
    if can_look():
        try:
            import faces
            end = time.time() + MAKE_WAIT
            for n in nums:
                if time.time() > end:
                    break
                try:
                    if arrange.copy_to_serve(kit, rec, by[n], arrange.SIZES["s"]) is None:
                        arrange.make_one(kit, by[n], arrange.SIZES["s"], rec=rec)
                except (Exception, SystemExit):  # noqa: BLE001
                    pass
            found = faces.for_kit(kit, nums)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            arrange.log(f"first design: the faces couldn't be looked for: {e.__class__.__name__}: {str(e)[:160]}")
            found = {}
    out = []
    for n in nums:
        r, f = by[n], found.get(n)
        a = (r["w"] / r["h"]) if (r.get("w") or 0) > 0 and (r.get("h") or 0) > 0 else None
        if f and f.get("w") and f.get("h"):
            fa = f["w"] / f["h"]
            if a is None or (a > 1) != (fa > 1):    # the list's size was read sideways (a turn mark): the look is upright
                a = fa
        out.append({"n": n, "a": a, "faces": list(f["faces"]) if f else None})
    return out


def first_state(kit, rec, order, rows, bg="#ffffff"):
    """The example for this shoot: (layout, facts) or (None, None) when the shoot has no photo to lay out. facts:
    {"looked": how many photos' faces could be looked for, "of": how many photos are used, "kinds": the layouts in
    order}; kept with the design so the Assistant can say what was made."""
    nums, ours = pool(list(order or []), [r["n"] for r in rows])
    if not nums:
        return None, None
    photos = gather(kit, rec, rows, nums)
    units = plan(photos, ours)
    st = state_of(units, bg)
    if st is None:
        return None, None
    used = {n for u in units for n in u["photos"]}
    return st, {"by": "rule", "looked": sum(1 for p in photos if p["n"] in used and p["faces"] is not None), "of": len(used),
                "kinds": [u["kind"] for u in units]}


def main():
    import arrange
    import kit as kit_mod
    if len(sys.argv) != 3 or sys.argv[1] != "plan":
        print(__doc__.split("\n\n")[-2].strip())
        return 2
    kit = arrange.kit_by_name(sys.argv[2])
    if kit is None:
        print("STOP: no post kit by that folder name.")
        return 1
    rows = arrange.sheet_rows(kit)
    rec = kit_mod.load_rec(kit)
    _, p = arrange.sync(kit, "carousel")
    st, facts = first_state(kit, rec, list(p["now"]["nums"]) if p else [], rows)
    print(json.dumps({"facts": facts, "state": st}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
