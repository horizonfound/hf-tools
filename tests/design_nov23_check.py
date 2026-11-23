#!/usr/bin/env python3
"""Nicole's Nov 23 answers, the designers (Lane E): the first carousel design is an example laid out by rule, and
My vault's photo tray in both designers is grouped by shoot like the vault's reel page.

    python3 tests/design_nov23_check.py rules                      (no browser, no kit: the rules alone)
    python3 tests/design_nov23_check.py first [--port 9940] [--no-chrome]
    python3 tests/design_nov23_check.py vault [--port 9940] [--no-chrome]
    python3 tests/design_nov23_check.py all   [--port 9940] [--no-chrome]

The parts with a hidden Chrome run under the guard, one at a time on the whole Mac:
    python3 tests/guard.py 3000 python3 tests/design_nov23_check.py all

Everything is on pretend post kits it makes itself (tests/fake_kit.py, under /private/tmp; a scratch STUDIO_HOME;
never the real ~/.studio, no drive, never ports 8790 to 8792 or 8799; STUDIO_NO_WINDOWS_FOR_TESTS, so no window is
ever shown). The faces are PRETEND ones (FACES_PRETEND: a table the test writes, or "none" for a computer with no
face finder), so the Mac's own Vision is never asked and the run is the same on every computer.

Part `rules` (design_first.py's plain functions):
  * shapes, the head box with its headroom, where a crop sits (the middle; moved only to keep a head in; refused
    when a head can't be kept, when too much would be lost, or when nobody could look and it would be a guess);
  * the seam of a photo across two slides never lies on a head;
  * the example: a full-slide opener, a mix after it, a small photo on the last slide; no two slides next to each
    other alike; never more than ten slides; fewer photos, fewer slides; every photo once; no words;
  * FOR 300 MADE-UP SHOOTS: every head box lies inside what its frame shows, the layout passes design.py's own
    check, and nothing is laid out the same way twice running;
  * a computer with no face finder: every frame shows (nearly) the whole photo, and no photo lies across two slides.

Part `first` (a pretend kit, design.py itself, then the real page in a hidden Chrome):
  * the first visit makes "<Shoot> carousel 1" as the example, from the carousel's order, with what was done
    written in the record ("example"); a second visit makes nothing and changes nothing;
  * a design that was already there is never rebuilt (an old one-photo-per-slide first design stays byte for byte);
  * "+ New design" with no layout sent is still one photo per slide; the vault's first design is still blank;
    stories still start with one empty story;
  * with no face finder the example is whole photos, and `design.py open` says so; with one it says EXAMPLE and
    that nobody looked at it by eye; a second open says THEIRS;
  * a shoot with no carousel order: photos spread from the first to the last of the shoot;
  * in Chrome: the page opens the example with no error of its own, every photo is drawn, and by the page's OWN
    crop arithmetic (Designer.M.layoutImg) every pretend head lies inside its frame; Save slides saves one
    1080 by 1350 JPEG a slide.

Part `vault` (three pretend shoots and the vault, as tests/vault_reel_check.py makes them):
  * one copy of the rule: the tray's words are the reel page's own tables, its search-words function is the reel
    page's own text, its data is GET /reel-vault-photos;
  * a plain shoot's designer page has none of it (no search box, the tray one flat list);
  * in Chrome, the carousel designer AND the stories designer in My vault: Added to my vault open on top with her
    line, each shoot folded shut with its picture, name and count, the chips; "laugh" opens only the shoots with a
    match and says how many; nothing found says her line; a shoot's chip shows that shoot; a click on a photo in an
    open shoot puts it on the slide and ticks it; a drag from a fold onto a slide adds it; a photo added to the
    vault itself shows under Added to my vault;
  * EVERY OTHER POST KIT IS BYTE FOR BYTE UNCHANGED.

Python 3.9, standard library only. No Pillow.
"""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
sys.path.insert(0, str(HERE))
import vault_core_check as core  # noqa: E402
from vault_core_check import case, group  # noqa: E402

NEVER = {8790, 8791, 8792, 8799, 8765}
W, H = 1080, 1350


def skip(line):
    print("SKIP  " + line, flush=True)


def finish():
    n, bad = core.COUNT[0], core.FAILED
    print(f"\n{n - len(bad)} of {n} passed" + (f"; FAILED: {len(bad)}" if bad else ""))
    for f in bad:
        print("  FAILED: " + f)
    return 1 if bad else 0


# ---------- what a frame shows, worked out here from design.py's own crop numbers (not with design_first's code) ----------

def window(b, a):
    """The part of a photo of shape a (w / h) that frame b shows: (x0, y0, x1, y1) as parts of the photo. The page's
    rule (design_js_model.py layoutImg): the photo fills the frame, times zoom; ox, oy say where the spare goes."""
    c = max(b["w"] / a, b["h"] / 1.0) * b.get("zoom", 1)
    iw, ih = a * c, c
    vw, vh = b["w"] / iw, b["h"] / ih
    x0, y0 = b.get("ox", 0.5) * (1 - vw), b.get("oy", 0.5) * (1 - vh)
    return x0, y0, x0 + vw, y0 + vh


def heads_in(b, p, F):
    x0, y0, x1, y1 = window(b, p["a"])
    e = 0.002
    for f in p["faces"] or []:
        hx0, hy0, hx1, hy1 = F.head_box(f)
        if hx0 < x0 - e or hy0 < y0 - e or hx1 > x1 + e or hy1 > y1 + e:
            return False
    return True


def slide_marks(st):
    """How each slide is laid out, as a mark: the frames that start on it, by place and size (rounded)."""
    out = [[] for _ in range(st["slides"])]
    for b in st["blocks"]:
        k = min(st["slides"] - 1, max(0, int((b["x"] + 0.5) // W)))
        out[k].append((round(b["x"] - k * W), round(b["y"]), round(b["w"]), round(b["h"])))
    return [tuple(sorted(x)) for x in out]


# ====================== part `rules` ======================

def part_rules():
    os.environ.setdefault("STUDIO_HOME", tempfile.mkdtemp(prefix="hf-nov23-rules-", dir="/private/tmp"))
    os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
    sys.path.insert(0, str(SCRIPTS))
    import design
    import design_first as F
    group("the rules: shapes, heads, crops")
    case("one slide is design.py's own size", (F.W, F.H) == (design.W, design.H) == (W, H))
    case("the borders are design.py's own single \"One with a border\"",
         any(s["id"] == "cs-border" and [s["template"]["blocks"][0][k] for k in "xywh"] == list(F.BORDER_BOX) for s in design.SINGLES))
    case("a photo is tall, wide or square by its own shape", [F.shape(a) for a in (0.667, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, None, 0)]
         == ["tall", "tall", "square", "square", "square", "wide", "wide", None, None])
    hb = F.head_box([0.4, 0.3, 0.2, 0.2])
    case("a head box has headroom: more above the face than beside or under it", abs(hb[0] - 0.34) < 1e-9 and abs(hb[1] - 0.18) < 1e-9 and abs(hb[2] - 0.66) < 1e-9 and abs(hb[3] - 0.55) < 1e-9, hb)
    case("...and never reaches off the photo", F.head_box([0.0, 0.01, 0.3, 0.3])[:2] == (0.0, 0.0) and F.head_box([0.8, 0.8, 0.2, 0.2])[2:] == (1.0, 1.0))
    tall = {"n": 1, "a": 2 / 3, "faces": []}
    case("a tall photo with nobody in it fills a slide from its middle", F.crop(W, H, tall) == {"ox": 0.5, "oy": 0.5})
    top = {"n": 1, "a": 2 / 3, "faces": [[0.4, 0.03, 0.2, 0.12]]}
    c = F.crop(W, H, top)
    case("a face at the very top: the photo is moved just far enough to keep the whole head in (Don't crop any heads)",
         c is not None and c["oy"] < 0.5 and heads_in(dict(x=0, y=0, w=W, h=H, zoom=1, **c), top, F) and not heads_in(dict(x=0, y=0, w=W, h=H, zoom=1, ox=0.5, oy=0.5), top, F), c)
    mid = {"n": 1, "a": 2 / 3, "faces": [[0.4, 0.4, 0.2, 0.12]]}
    case("a face in the middle: the photo stays in the middle of its frame (centered unless a head needs it)", F.crop(W, H, mid) == {"ox": 0.5, "oy": 0.5})
    both = {"n": 1, "a": 2 / 3, "faces": [[0.4, 0.02, 0.2, 0.1], [0.4, 0.88, 0.2, 0.1]]}
    case("heads at the top AND the bottom can't both be kept in a slide-shaped cut: that frame is refused", F.crop(W, H, both) is None)
    wide = {"n": 1, "a": 1.5, "faces": []}
    case("a wide photo is never cut down to fill one slide (too much of it would be lost)", F.crop(W, H, wide) is None and F.unit("full", [wide], 1) is None)
    case("...it may lie across two slides, nearly whole", F.crop(2 * W, H, wide, seam=0.5) == {"ox": 0.5, "oy": 0.5} and F.shows(2 * W, H, 1.5)[1] > 0.9)
    seam = {"n": 1, "a": 1.5, "faces": [[0.45, 0.3, 0.1, 0.15]]}
    case("a head on the seam between the two slides: no photo across two slides", F.crop(2 * W, H, seam, seam=0.5) is None and F.unit("spread", [seam], 5) is None)
    off = {"n": 1, "a": 1.5, "faces": [[0.15, 0.3, 0.1, 0.15]]}
    case("a head well to one side of the seam: across two slides is fine", F.unit("spread", [off], 5) is not None and F.unit("spread", [off], 1) is None)
    blind = {"n": 1, "a": 2 / 3, "faces": None}
    case("nobody could look (a PC): cutting a tall photo to fill a slide would be a guess, so it is refused", F.crop(W, H, blind) is None)
    case("...a photo already the slide's shape loses nothing, so it may fill it", F.crop(W, H, {"n": 1, "a": 0.8, "faces": None}) == {"ox": 0.5, "oy": 0.5})
    case("...and no photo goes across two slides (the seam would be a guess too)", F.crop(2 * W, H, {"n": 1, "a": 1.5, "faces": None}, seam=0.5) is None)
    x, y, w, h = F.fit(1.5, F.BORDER_BOX)
    case("a whole-photo frame has the photo's own shape and sits in the middle of its box", abs(w / h - 1.5) < 1e-6 and abs((x + w / 2) - (90 + 450)) < 1e-6 and abs((y + h / 2) - (110 + 565)) < 1e-6 and w <= 900 and h <= 1130, (x, y, w, h))

    group("the rules: the example")
    mix = [{"n": i + 1, "a": a, "faces": f} for i, (a, f) in enumerate([
        (2 / 3, []), (1.5, []), (1.5, []), (1.5, []), (2 / 3, [[0.4, 0.3, 0.2, 0.15]]), (2 / 3, []), (2 / 3, []),
        (1.5, [[0.1, 0.3, 0.1, 0.1]]), (1.0, []), (2 / 3, []), (1.5, []), (2 / 3, [])])]
    units = F.plan(mix)
    kinds = [u["kind"] for u in units]
    st = F.state_of(units)
    case("the example opens with a photo filling its slide and ends with a small photo on a quiet slide", kinds[0] == "full" and kinds[-1] == "closer", kinds)
    case("...with a mix between: two photos together, a photo across two slides, a bordered photo", {"pair", "spread", "border"} <= set(kinds), kinds)
    case("...never more than ten slides", st["slides"] <= F.SLIDES_MOST == 10 and st["slides"] == sum(u["slides"] for u in units), st["slides"])
    case("...no two slides next to each other laid out the same way", all(a != b for a, b in zip(kinds, kinds[1:])), kinds)
    used = [n for u in units for n in u["photos"]]
    case("...every photo at most once, in the order given", used == sorted(set(used), key=used.index) and used[:-1] == [p["n"] for p in mix][:len(used) - 1] and used[-1] == 12, used)
    case("...and not one word on it (rule 11: no text is invented)", all(b.get("type") != "text" for b in st["blocks"]))
    clean, why = design.validate_state(st, {p["n"] for p in mix})
    case("...and it is a layout design.py takes as it is", clean is not None and why is None, why)
    last = st["blocks"][-1]
    case("the last slide's photo is whole, in the middle of its slide", abs((last["x"] - (st["slides"] - 1) * W) + last["w"] / 2 - W / 2) < 1 and abs(last["y"] + last["h"] / 2 - H / 2) < 1, last)
    for n, want in ((0, (0,)), (1, (1,)), (2, (2,)), (3, (3, 4))):
        u = F.plan(mix[:n])
        s = F.state_of(u)
        case(f"{n} photo{'s' if n != 1 else ''}: {' or '.join(str(x) for x in want)} slide{'s' if want != (1,) else ''} (fewer photos, fewer slides)", (s["slides"] if s else 0) in want, [x["kind"] for x in u])
    six = F.state_of(F.plan(mix[:7]))
    case("seven photos: about six slides, not ten", 4 <= six["slides"] <= 7, six["slides"])
    order, ours = F.pool([5, 3, 9, 3, 99], [1, 2, 3, 4, 5, 6, 7, 8, 9])
    case("the photos are the carousel's own order when there is one (a number twice or not in the shoot is dropped)", order == [5, 3, 9] and ours is False)
    order, ours = F.pool(list(range(1, 31)), list(range(1, 41)))
    case("a long order: its first eleven and its last photo", order == list(range(1, 12)) + [30] and ours is False, order)
    order, ours = F.pool([], list(range(1, 61)))
    case("no order yet: twelve photos spread from the first of the shoot to the last", ours is True and len(order) == 12 and order[0] == 1 and order[-1] == 60 and order == sorted(order), order)
    led = F.plan([{"n": 1, "a": 1.5, "faces": []}, {"n": 2, "a": 2 / 3, "faces": []}, {"n": 3, "a": 1.5, "faces": []}], ours=True)
    case("...and then the first photo that can fill a slide opens it", led[0]["kind"] == "full" and led[0]["photos"] == [2], [(u["kind"], u["photos"]) for u in led])
    kept = F.plan([{"n": 1, "a": 1.5, "faces": []}, {"n": 2, "a": 2 / 3, "faces": []}, {"n": 3, "a": 1.5, "faces": []}], ours=False)
    case("their own order is never changed: a wide first photo opens with a border instead", kept[0]["kind"] == "border" and kept[0]["photos"] == [1], [(u["kind"], u["photos"]) for u in kept])

    group("the rules, on 300 made-up shoots")
    rnd = random.Random(1123)
    bad_head, bad_valid, bad_same, bad_many, bad_big, spreads, fulls = [], [], [], [], [], 0, 0
    for t in range(300):
        ps = []
        for i in range(rnd.randint(1, 16)):
            a = rnd.choice([2 / 3, 2 / 3, 1.5, 1.5, 1.0, 0.8, 0.75, 16 / 9, 1.25])
            faces = []
            for _ in range(rnd.choice([0, 0, 1, 1, 2, 4])):
                fw = rnd.uniform(0.05, 0.3)
                fh = fw * a * rnd.uniform(1.0, 1.3)
                if fh < 0.9:
                    faces.append([round(rnd.uniform(0, 1 - fw), 3), round(rnd.uniform(0, 1 - fh), 3), round(fw, 3), round(fh, 3)])
            ps.append({"n": i + 1, "a": a, "faces": faces})
        us = F.plan(ps, ours=rnd.random() < 0.5)
        s = F.state_of(us)
        by = {p["n"]: p for p in ps}
        if any(not heads_in(b, by[b["n"]], F) for b in s["blocks"]):
            bad_head.append(t)
        if design.validate_state(s, set(by))[0] is None:
            bad_valid.append(t)
        marks = slide_marks(s)
        ks = [u["kind"] for u in us]
        if any(a == b for a, b in zip(ks, ks[1:])) or any(a == b and a for a, b in zip(marks, marks[1:])):
            bad_same.append(t)
        if s["slides"] > 10 or len({b["n"] for b in s["blocks"]}) != len(s["blocks"]):
            bad_many.append(t)
        for b in s["blocks"]:
            x0, y0, x1, y1 = window(b, by[b["n"]]["a"])
            if min(x1 - x0, y1 - y0) < F.FULL_SHOWS - 0.005:
                bad_big.append(t)
        spreads += ks.count("spread")
        fulls += ks.count("full")
    case("every head box lies inside what its frame shows, in every one of them", not bad_head, bad_head[:5])
    case("every layout is one design.py takes as it is", not bad_valid, bad_valid[:5])
    case("no two slides next to each other are laid out alike, by kind or by where the frames sit", not bad_same, bad_same[:5])
    case("never more than ten slides, never a photo twice", not bad_many, bad_many[:5])
    case("no frame ever shows less than three quarters of its photo", not bad_big, bad_big[:5])
    case("(the made-up shoots did use photos across two slides and full slides, so the checks above bit)", spreads > 20 and fulls > 300, (spreads, fulls))

    group("the rules, with no face finder (a PC)")
    rnd = random.Random(7)
    worst, any_spread, bad_same = 1.0, 0, 0
    for t in range(200):
        ps = [{"n": i + 1, "a": rnd.choice([2 / 3, 1.5, 1.0, 0.8, 16 / 9]), "faces": None} for i in range(rnd.randint(1, 14))]
        us = F.plan(ps, ours=rnd.random() < 0.5)
        s = F.state_of(us)
        by = {p["n"]: p for p in ps}
        for b in s["blocks"]:
            x0, y0, x1, y1 = window(b, by[b["n"]]["a"])
            worst = min(worst, x1 - x0, y1 - y0)
        ks = [u["kind"] for u in us]
        any_spread += ks.count("spread")
        bad_same += sum(1 for a, b in zip(ks, ks[1:]) if a == b)
    case("every frame shows the whole photo, or all but a sliver of it (never a guess)", worst >= F.GUESS_SHOWS - 0.005, worst)
    case("no photo is laid across two slides", any_spread == 0, any_spread)
    case("and still no two slides next to each other alike", bad_same == 0, bad_same)
    return finish()


# ====================== part `first` ======================

KIT = "2026-11-01 Fake beach"


def table_for(arrange, kit, kit_mod, faces_by_n):
    """A FACES_PRETEND table for a kit: {small copy's file name: {w, h, faces}} (every photo looked at; faces only
    where given)."""
    rec = kit_mod.load_rec(kit)
    out = {}
    for r in arrange.sheet_rows(kit):
        src = arrange.photo_path(kit, rec, r)
        name = arrange.preview_file(kit, r, arrange.SIZES["s"], src).name
        w, h = r["w"], r["h"]
        out[name] = {"w": w, "h": h, "faces": faces_by_n.get(r["n"], [])}
    return out


def part_first(a):
    work = Path(tempfile.mkdtemp(prefix="hf-nov23-first-", dir="/private/tmp"))
    run = core.Run(work, a.port)
    run.env.pop("STUDIO_FIRST_DESIGN_FOR_TESTS", None)
    try:
        group("(making the pretend kits)")
        run.fake(run.target, "Fake beach", 14)
        run.fake(run.target, "No finder", 10)
        run.fake(run.target, "Old design", 8)
        run.fake(run.target, "No order", 30)
        os.environ["STUDIO_HOME"] = str(run.studio)
        os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
        os.environ.pop("STUDIO_FIRST_DESIGN_FOR_TESTS", None)
        sys.path.insert(0, str(SCRIPTS))
        import arrange
        import design
        import design_first as F
        import kit as kit_mod
        kit = arrange.kit_by_name(KIT)
        arrange.make_previews(kit)
        rows = {r["n"]: r for r in arrange.sheet_rows(kit)}
        order = design.carousel_order(kit)
        tall = [n for n in order if rows[n]["h"] > rows[n]["w"]]
        wide = [n for n in order if rows[n]["w"] > rows[n]["h"]]
        # pretend faces: the first tall photo of the order has a face at the very top; the first wide one has a face
        # in its middle (so it can't lie across two slides)
        pretend = {}
        if tall:
            pretend[tall[0]] = [[0.4, 0.03, 0.2, 0.12]]
        if len(tall) > 1:
            pretend[tall[1]] = [[0.3, 0.3, 0.15, 0.12], [0.55, 0.33, 0.15, 0.12]]
        if wide:
            pretend[wide[0]] = [[0.45, 0.3, 0.1, 0.15]]
        tfile = work / "faces.json"
        tfile.write_text(json.dumps(table_for(arrange, kit, kit_mod, pretend)), encoding="utf-8")
        os.environ["FACES_PRETEND"] = str(tfile)

        group("the first visit makes the example")
        designs = kit / ".kit" / "designs"
        case("before the first visit the shoot has no design", not designs.exists() or not list(designs.glob("*.json")))
        st = design.state_for_page(kit)
        d = st["design"]
        on_disk = json.loads((designs / (d["id"] + ".json")).read_text(encoding="utf-8"))
        ex = on_disk.get("example") or {}
        case("it is named \"<Shoot> carousel 1\", and it is the only design", d["name"] == "Fake beach carousel 1" and len(st["designs"]) == 1, d["name"])
        case("the record says how it was made: by rule, how many photos' faces were looked for, the layouts in order",
             ex.get("by") == "rule" and ex.get("looked") == ex.get("of") and ex.get("of", 0) >= 4 and ex.get("kinds") and ex["kinds"][-1] == "closer", ex)
        case("what the page is sent says nothing of that (it is the Assistant's own note)", "example" not in d)
        s = d["state"]
        used = [b["n"] for b in s["blocks"]]
        case("its photos are the carousel's own picks, in that order, each once", used == [n for n in order if n in used] and len(set(used)) == len(used) and set(used) <= set(order), (used, order))
        marks = slide_marks(s)
        case("it is not one photo filling every slide any more: the slides are a mix", len(set(marks)) >= 3 and not all(m == ((0, 0, W, H),) for m in marks), marks)
        case("no two slides next to each other are laid out alike", all(x != y for x, y in zip(ex["kinds"], ex["kinds"][1:])) and all(x != y for x, y in zip(marks, marks[1:])), ex["kinds"])
        case("the first slide is a photo filling it (a full-slide opener)", marks[0] == ((0, 0, W, H),), marks[0])
        case("no words are on it", all(b.get("type") != "text" for b in s["blocks"]))
        ph = {n: {"n": n, "a": rows[n]["w"] / rows[n]["h"], "faces": pretend.get(n, [])} for n in used}
        case("every pretend head lies inside what its frame shows", all(heads_in(b, ph[b["n"]], F) for b in s["blocks"]), [b for b in s["blocks"] if not heads_in(b, ph[b["n"]], F)])
        if tall and tall[0] in used:
            b = next(x for x in s["blocks"] if x["n"] == tall[0])
            case("the photo with a face at its very top was moved in its frame to keep the head, or shown whole",
                 (round(b["w"]) == W and round(b["h"]) == H and b["oy"] < 0.5) or abs(b["w"] / b["h"] - ph[tall[0]]["a"]) < 0.01, b)
        if wide and wide[0] in used:
            b = next(x for x in s["blocks"] if x["n"] == wide[0])
            case("the wide photo with a face in its middle does not lie across two slides", b["w"] < 2 * W - 1, b)
        before = {p.name: p.read_bytes() for p in designs.glob("*.json")}
        st2 = design.state_for_page(kit)
        case("a second visit makes no second design and changes nothing on the drive", st2["design"]["id"] == d["id"] and {p.name: p.read_bytes() for p in designs.glob("*.json")} == before)
        code, out = design.new_design(kit)
        ns = out["design"]["state"] if code == 200 else {}
        case("\"+ New design\" with no layout sent is still one photo per slide, named with the next number",
             code == 200 and out["design"]["name"] == "Fake beach carousel 2" and [b["n"] for b in ns["blocks"]] == order
             and all(b["x"] == i * W and b["y"] == 0 and b["w"] == W and b["h"] == H for i, b in enumerate(ns["blocks"])), out)
        sst = design.state_for_page(kit, kind=design.STORIES)
        case("stories still start with one empty white story", sst["design"]["state"] == {"slides": 1, "bg": "#ffffff", "blocks": []})

        group("a design that was already there is never rebuilt")
        old = arrange.kit_by_name("2026-11-01 Old design")
        os.environ["STUDIO_FIRST_DESIGN_FOR_TESTS"] = "plain"          # the first design as it was before Nov 23
        o1 = design.state_for_page(old)["design"]
        os.environ.pop("STUDIO_FIRST_DESIGN_FOR_TESTS")
        odir = old / ".kit" / "designs"
        was = {p.name: p.read_bytes() for p in odir.glob("*.json")}
        oorder = design.carousel_order(old)
        case("(the old first design: one photo filling each slide, in the carousel's order)", [b["n"] for b in o1["state"]["blocks"]] == oorder
             and all(b["w"] == W and b["h"] == H for b in o1["state"]["blocks"]) and "example" not in json.loads(next(iter(was.values())).decode()))
        o2 = design.state_for_page(old)["design"]
        case("opening that shoot again today: the same design, byte for byte, and no new one", o2["id"] == o1["id"] and o2["state"] == o1["state"] and {p.name: p.read_bytes() for p in odir.glob("*.json")} == was)

        group("a shoot with no carousel order yet")
        noord = arrange.kit_by_name("2026-11-01 No order")
        rf = noord / ".kit" / "kit.json"
        rec = json.loads(rf.read_text(encoding="utf-8"))
        rec.get("picks", {}).pop("carousel", None)                      # the test's own kit: as a shoot nobody has picked for
        rf.write_text(json.dumps(rec), encoding="utf-8")
        arrange.make_previews(noord)
        (work / "faces2.json").write_text(json.dumps(table_for(arrange, noord, kit_mod, {})), encoding="utf-8")
        os.environ["FACES_PRETEND"] = str(work / "faces2.json")
        case("(it has no order)", design.carousel_order(noord) == [])
        n1 = design.state_for_page(noord)["design"]["state"]
        nums = sorted(b["n"] for b in n1["blocks"])
        alln = [r["n"] for r in arrange.sheet_rows(noord)]
        case("the example draws from the whole shoot, first photo to last, not its first few", nums[0] <= alln[2] and nums[-1] == alln[-1] and 6 <= n1["slides"] <= 10 and len(nums) <= 12, (nums, n1["slides"]))

        group("a computer with no face finder (a PC)")
        os.environ["FACES_PRETEND"] = "none"
        nof = arrange.kit_by_name("2026-11-01 No finder")
        nst = design.state_for_page(nof)["design"]
        nrec = json.loads(next(p for p in (nof / ".kit" / "designs").glob("*.json") if ".prev" not in p.name).read_text(encoding="utf-8"))
        nrows = {r["n"]: r for r in arrange.sheet_rows(nof)}
        worst = min(min(x1 - x0, y1 - y0) for x0, y0, x1, y1 in (window(b, nrows[b["n"]]["w"] / nrows[b["n"]]["h"]) for b in nst["state"]["blocks"]))
        case("every photo is shown whole (or all but a sliver), and none lies across two slides",
             worst >= F.GUESS_SHOWS - 0.005 and all(b["w"] <= W for b in nst["state"]["blocks"]) and nrec["example"]["looked"] == 0, (worst, nrec.get("example")))
        case("...still a mix, no two slides next to each other alike", all(x != y for x, y in zip(slide_marks(nst["state"]), slide_marks(nst["state"])[1:])), slide_marks(nst["state"]))

        group("the tests' own switch, and the fallback")
        case("STUDIO_FIRST_DESIGN_FOR_TESTS=plain is the only thing that brings back the old first design", F.plain_for_tests() is False and F.PLAIN_FOR_TESTS == "STUDIO_FIRST_DESIGN_FOR_TESTS")
        src = (SCRIPTS / "design.py").read_text(encoding="utf-8")
        case("design.py asks for the example only from the first visit (ensure_design), and falls back to one photo per slide if the rules ever fail",
             "new_design(kit, kind=kind, first=True)" in src and src.count("first=True") == 1 and "if state is None:\n                    state = seed_state(rec, carousel_order(kit), rows)" in src)

        group("what the Assistant is told (design.py open), and the vault")
        env = dict(run.env, FACES_PRETEND=str(tfile))
        run.env = env
        run.start()
        case("the page server is on a port of this test's own", run.port not in NEVER, run.port)
        run.fake(run.target, "Open me", 9)
        code, out = run.cmd("design.py", "open", "2026-11-01 Open me", env=dict(env, FACES_PRETEND="none"))
        lines = [ln for ln in out.splitlines() if ln.strip()]
        case("design.py open, no face finder: NEW, an EXAMPLE, every photo shown whole, nobody looked at it by eye",
             code == 0 and lines[-2].startswith("NEW:") and "EXAMPLE" in lines[-2] and "shown whole" in lines[-2] and "nobody has looked at it by eye" in lines[-2]
             and "no words on it" in lines[-2] and "one photo on each slide" not in out, out[-600:])
        code, out2 = run.cmd("design.py", "open", "2026-11-01 Open me", env=env)
        l2 = [ln for ln in out2.splitlines() if ln.strip()]
        case("design.py open again: THEIRS, the same address", code == 0 and l2[-2].startswith("THEIRS:") and l2[-1] == lines[-1], out2[-300:])
        run.fake(run.target, "Open two", 9)
        two = arrange.kit_by_name("2026-11-01 Open two")
        arrange.make_previews(two)
        (work / "faces3.json").write_text(json.dumps(table_for(arrange, two, kit_mod, {})), encoding="utf-8")
        code, out3 = run.cmd("design.py", "open", "2026-11-01 Open two", env=dict(env, FACES_PRETEND=str(work / "faces3.json")))
        l3 = [ln for ln in out3.splitlines() if ln.strip()]
        case("design.py open where photos could be looked at: NEW, an EXAMPLE laid out by rule so that no head is cut, nobody looked at it by eye",
             code == 0 and l3[-2].startswith("NEW:") and "EXAMPLE" in l3[-2] and "no head is cut" in l3[-2] and "nobody has looked at it by eye" in l3[-2]
             and "shown whole" not in l3[-2] and "a photo filling its slide" in l3[-2], out3[-600:])
        code, out = run.cmd("vault.py", "ensure")
        v = run.vault()
        os.environ["FACES_PRETEND"] = str(tfile)
        vst = design.state_for_page(v) if v else None
        case("the vault's first carousel design is still blank (nothing is picked there until they ask)", bool(vst) and vst["design"]["state"]["blocks"] == [], vst and vst["design"]["state"])

        if a.no_chrome:
            skip("the example on the real page: --no-chrome")
        else:
            import chrome_drive
            if not chrome_drive.find_chrome():
                skip("the example on the real page: no Chrome on this computer")
            else:
                group("the example on the real page, in a hidden Chrome")
                with chrome_drive.Chrome(work=str(work), size=(1280, 900)) as c:
                    c.open("http://127.0.0.1:%d/design.html?kit=%s&design=%s" % (run.port, quote(KIT), d["id"]))
                    c.wait_for("window.Designer && Designer.st && Designer.design && Designer.design.id === '%s'" % d["id"], 40)
                    case("the page opens the example: the same slides and frames the Assistant made", c.js("Designer.st.slides") == s["slides"] and c.js("Designer.st.blocks.length") == len(s["blocks"]))
                    ok = c.wait_for("Array.prototype.every.call(document.querySelectorAll('#strip img'), function(i){ return i.complete && i.naturalWidth > 0; }) && document.querySelectorAll('#strip img').length >= %d" % len(s["blocks"]), 60)
                    case("every photo of it is drawn on the strip", bool(ok))
                    faces = json.dumps({str(n): f for n, f in pretend.items()})
                    top, side, below = F.HEAD_TOP, F.HEAD_SIDE, F.HEAD_BELOW
                    bad = c.js("""(function(){
                      var D = Designer, faces = %s, bad = [];
                      D.st.blocks.forEach(function(b){
                        var p = D.by[b.n], fs = faces[b.n] || [];
                        if (!p || !fs.length) return;
                        var L = D.M.layoutImg(b, p.w, p.h);
                        fs.forEach(function(f){
                          var x0 = Math.max(0, f[0] - %f * f[2]), y0 = Math.max(0, f[1] - %f * f[3]), x1 = Math.min(1, f[0] + f[2] + %f * f[2]), y1 = Math.min(1, f[1] + f[3] + %f * f[3]);
                          var l = L.left + x0 * L.iw, t = L.top + y0 * L.ih, r = L.left + x1 * L.iw, bt = L.top + y1 * L.ih;
                          if (l < -2 || t < -2 || r > b.w + 2 || bt > b.h + 2) bad.push([b.n, l, t, r, bt, b.w, b.h]);
                        });
                      });
                      return bad; })()""" % (faces, side, top, side, below))
                    case("by the page's own crop arithmetic every pretend head lies inside its frame", bad == [] and len(pretend) >= 2, bad)
                    case("the page raised no error of its own", not c.page_errors(), c.page_errors()[:3])
                    car = kit / "Carousel"
                    had = set(os.listdir(car)) if car.is_dir() else set()
                    c.wait_for("!document.getElementById('save-slides').disabled", 30)
                    c.click("#save-slides")
                    new = core_wait(lambda: sorted(set(os.listdir(car)) - had) if car.is_dir() and len(set(os.listdir(car)) - had) >= s["slides"] else None, 90)
                    sizes = [design.jpeg_size((car / f).read_bytes()) for f in (new or [])]
                    case("Save slides saves the example: one 1080 by 1350 JPEG a slide, named for the design",
                         bool(new) and len(new) == s["slides"] and all(f.startswith("Fake beach carousel 1 - slide ") for f in new) and all(z == (W, H) for z in sizes), (new, sizes, c.text("#save-line") if c.count("#save-line") else ""))
    finally:
        run.stop()
        shutil.rmtree(work, ignore_errors=True)      # this run's own scratch folder, made a moment ago
    return finish()


def core_wait(fn, seconds=30, every=0.3):
    end = time.time() + seconds
    got = None
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(every)
    return got


# ====================== part `vault` ======================

VQ = "My%20vault"
TRAY = """(function(){ return Array.prototype.map.call(document.querySelectorAll('#thumbs details.vfold'), function(d){
  var s = d.querySelector('summary'); return {open: d.open, mine: d.classList.contains('mine'), nohit: d.classList.contains('nohit'),
    name: ((s.querySelector('span:not(.hit)') || s).textContent || '').trim(), n: s.querySelector('.n').textContent,
    hit: (s.querySelector('.hit') && !s.querySelector('.hit').hidden) ? s.querySelector('.hit').textContent : '', img: !!s.querySelector('img'),
    line: d.querySelector('.line1') && !d.querySelector('.line1').hidden ? d.querySelector('.line1').textContent : '',
    all: d.querySelectorAll('.th').length,
    seen: Array.prototype.filter.call(d.querySelectorAll('.th'), function(t){ return d.open && !t.classList.contains('off') && t.getBoundingClientRect().width > 0; }).map(function(t){ return +t.dataset.n; })}; }); })()"""


def type_in(c, sel, text):
    c.js("(function(){ var q = document.querySelector(%s); q.value = %s; q.dispatchEvent(new Event('input', {bubbles: true})); })()" % (json.dumps(sel), json.dumps(text)))
    time.sleep(0.25)


def tray_checks(c, s, kind, vr):
    H_, F_, T_ = vr.H, vr.F, vr.T
    n = s.n
    what = "stories designer" if kind else "carousel designer"
    c.open(s.url("/design.html?kit=" + VQ + ("&kind=stories" if kind else "")))
    c.wait_for("window.Designer && Designer.st && Designer.vaultTray && Designer.vaultTray.look().ready", 60)
    if kind:                            # a set of stories with nothing on it opens on Add stories: close that window
        time.sleep(0.5)
        c.key("Escape")
        time.sleep(0.4)
    f = c.js(TRAY)
    case(f"{what}: Added to my vault is on top and open, with her line while nothing has been added",
         f[0]["mine"] and f[0]["open"] and f[0]["name"].startswith("Added to my vault") and f[0]["all"] == 0 and f[0]["line"] == "Photos you add to your vault show up here, open and ready.", f[0])
    case(f"{what}: under it each shoot is folded shut, with its small picture, its name and its count",
         len(f) == 4 and sorted((x["name"], x["n"]) for x in f[1:]) == [("Hannah beach", "From its post kit · 8 photos"), ("Other farm", "From its post kit · 9 photos"), ("Third hill", "From its post kit · 8 photos")]
         and all(x["img"] and not x["open"] and not x["seen"] and not x["mine"] for x in f[1:]), f)
    case(f"{what}: every photo of the vault has its tile, in one fold or another, and the heading still counts them all",
         sum(x["all"] for x in f) == 25 and c.count("#thumbs .th") == 25 and "25" in c.text("#trayname"), (sum(x["all"] for x in f), c.text("#trayname")))
    chips = c.js("Array.prototype.map.call(document.querySelectorAll('#vshoots button'), function(b){ return b.textContent; })")
    case(f"{what}: the shoot chips, as on the reel page: Every shoot, then each shoot", chips[0] == "Every shoot" and sorted(chips[1:]) == ["Hannah beach", "Other farm", "Third hill"], chips)
    case(f"{what}: the search box says what to try (the reel page's own words)", c.js("document.querySelector('#vq').placeholder") == "laughing, a kiss, green backdrop, Hannah"
         and c.js("document.querySelector('#vq').getAttribute('aria-label')") == "Search your photos")
    type_in(c, "#vq", "laugh")
    f = {x["name"]: x for x in c.js(TRAY)}
    case(f"{what}: \"laugh\" opens only the shoots with a match, each saying how many, and shows only those photos",
         f["Hannah beach"]["open"] and f["Hannah beach"]["hit"] == "1 found" and f["Hannah beach"]["seen"] == [n(H_, 1)]
         and f["Other farm"]["open"] and f["Other farm"]["hit"] == "1 found" and f["Other farm"]["seen"] == [n(F_, 5)]
         and not f["Third hill"]["open"] and f["Third hill"]["nohit"] and f["Third hill"]["hit"] == "", f)
    type_in(c, "#vq", "hannah laughing")
    f = {x["name"]: x for x in c.js(TRAY)}
    case(f"{what}: \"hannah laughing\" finds across the shoot's name and the photo's words", f["Hannah beach"]["seen"] == [n(H_, 1)] and not f["Other farm"]["open"], f)
    type_in(c, "#vq", "zebra")
    case(f"{what}: nothing found says her line, and every shoot stays shut", c.js("document.querySelector('#vnone').hidden") is False
         and c.text("#vnone").strip() == "Nothing matches that yet. Try other words, or tell the Assistant what to look for." and not any(x["open"] for x in c.js(TRAY)[1:]))
    type_in(c, "#vq", "")
    f = c.js(TRAY)
    case(f"{what}: with the search cleared every shoot is shut again and her line is gone", not any(x["open"] for x in f[1:]) and c.js("document.querySelector('#vnone').hidden") is True, f)
    c.click("#vshoots button", nth=chips.index("Other farm"))
    time.sleep(0.3)
    f = {x["name"]: x for x in c.js(TRAY)}
    case(f"{what}: a shoot's chip shows that shoot's photos, open, \"9 found\", and no other shoot's",
         f["Other farm"]["open"] and f["Other farm"]["hit"] == "9 found" and len(f["Other farm"]["seen"]) == 9 and not f["Hannah beach"]["open"] and not f["Third hill"]["open"], f)
    c.click("#vshoots button", nth=0)
    time.sleep(0.2)
    return chips


def part_vault(a):
    import vault_reel_check as vr
    work = Path(tempfile.mkdtemp(prefix="hf-nov23-vault-", dir="/private/tmp"))
    run = work / "run"
    (run / "home").mkdir(parents=True)
    s = vr.PhotoWorld(run, a.port)
    s.env["STUDIO_FIRST_DESIGN_FOR_TESTS"] = "plain"      # the shoots' own first designs are not this part's business
    try:
        group("(making three shoots, two of them looked at and described, and the vault)")
        vr.make_photo_world(s)
        os.environ["STUDIO_HOME"] = str(s.studio)
        os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
        sys.path.insert(0, str(SCRIPTS))
        import design_js_vault as V
        import design_page
        import reel_page
        group("one copy of the rule")
        w = V.vault_words()
        tables = {}
        for t in (reel_page.WORDS, reel_page.VAULT_CLIP_WORDS, reel_page.VAULT_PICK_WORDS, reel_page.VAULT_PICK_OUR_WORDS):
            tables.update(t)
        case("the tray's words are the reel page's own tables, every one", set(w) == set(V.WORD_KEYS) and all(w[k] == tables[k] for k in w), w)
        src = (SCRIPTS / "design_js_vault.py").read_text(encoding="utf-8")
        case("...and none of them is spelled out in the designer's own file", not any(v in src.split('"""', 2)[2] for v in w.values() if len(v) > 12), [v for v in w.values() if len(v) > 12 and v in src.split('"""', 2)[2]])
        fn = V.search_words_js()
        case("the function that turns what was typed into search words is the reel page's own text, put into the tray's script as it is",
             fn in reel_page.VAULT_PHOTOS_JS and fn.strip("\n") in V.vault_js() and "function words(v){" in fn and V.vault_js().count("function words(v){") == 1)
        case("the tray reads what the reel page's photos step reads (GET /reel-vault-photos), and no route of its own was added",
             "fetch('/reel-vault-photos?'" in V.vault_js() and "reel-vault" not in (SCRIPTS / "design.py").read_text(encoding="utf-8").split("GET_PATHS = ")[1].split("\n\n")[0])
        plain, vault = design_page.page_html("A kit"), design_page.page_html("A kit", vault=True)
        case("a plain shoot's designer page has none of it: the vault's page is that page plus the one part, before the page starts",
             "DESIGN_VAULT_WORDS" not in plain and "vfold" not in plain and vault == plain.replace("<script>" + design_page.DESIGN_START_JS, design_page.vault_part() + "<script>" + design_page.DESIGN_START_JS)
             and vault != plain)
        splain, svault = design_page.page_html("A kit", "stories"), design_page.page_html("A kit", "stories", vault=True)
        case("...the same for the stories designer", "DESIGN_VAULT_WORDS" not in splain and "DESIGN_VAULT_WORDS" in svault)

        s.start()
        case("the page server is on a port of this test's own (%d)" % s.port, s.port not in NEVER)
        code, _, raw = s.get("/design.html?kit=" + VQ)
        page = raw.decode("utf-8", "replace")
        code2, _, raw2 = s.get("/design.html?kit=" + quote(vr.H))
        code3, _, raw3 = s.get("/design.html?kit=" + VQ + "&kind=stories")
        case("the Assistant puts the vault's part on My vault's designer pages only (carousel and stories), never on a shoot's",
             code == 200 and "DESIGN_VAULT_WORDS" in page and code2 == 200 and b"DESIGN_VAULT_WORDS" not in raw2 and code3 == 200 and b"DESIGN_VAULT_WORDS" in raw3)
        case("no path on the vault's page", vr.no_path(re.sub(r"<script\b.*?</script>", "", page, flags=re.S)))
        code, j, _ = s.get("/reel-vault-photos?kit=" + VQ)
        case("(what the tray reads: 3 shoots, 25 photos, no path)", code == 200 and j and len(j["shoots"]) == 3 and len(j["photos"]) == 25 and vr.no_path(j))

        if a.no_chrome:
            skip("the vault's tray in a browser: --no-chrome")
        else:
            import chrome_drive
            if not chrome_drive.find_chrome():
                skip("the vault's tray in a browser: no Chrome on this computer")
            else:
                group("My vault's designers in a hidden Chrome")
                with chrome_drive.Chrome(work=str(run), size=(1280, 900), extra_args=vr.LIGHT) as c:
                    tray_checks(c, s, "", vr)
                    group("the stories designer in My vault")
                    tray_checks(c, s, "stories", vr)
                    case("the page raised no error of its own", not c.page_errors(), c.page_errors()[:3])
                    group("My vault's carousel designer: putting photos on a slide from the folds")
                    c.open(s.url("/design.html?kit=" + VQ))
                    c.wait_for("window.Designer && Designer.st && Designer.vaultTray && Designer.vaultTray.look().ready", 60)
                    # a click on a photo in an open shoot puts it on the slide
                    case("carousel designer: the vault's first design is blank, as before", c.js("Designer.st.blocks.length") == 0)
                    c.js("(function(){ var d = Array.prototype.filter.call(document.querySelectorAll('#thumbs details.vfold'), function(x){ return x.querySelector('summary span') && x.querySelector('summary span').textContent === 'Hannah beach'; })[0]; d.open = true; })()")
                    time.sleep(0.3)
                    f = {x["name"]: x for x in c.js(TRAY)}
                    case("carousel designer: a shoot opened by hand shows all its photos", f["Hannah beach"]["open"] and len(f["Hannah beach"]["seen"]) == 8, f["Hannah beach"])
                    n1, n2 = s.n(vr.H, 1), s.n(vr.H, 2)
                    c.click("#thumbs .th[data-n='%d']" % n1)
                    c.wait_for("Designer.st.blocks.length === 1", 10)
                    case("carousel designer: a click on a photo in an open shoot puts it on the slide, and its tile is ticked",
                         c.js("Designer.st.blocks[0].n") == n1 and c.js("document.querySelector(\"#thumbs .th[data-n='%d']\").classList.contains('used')" % n1) is True)
                    c.drag("#thumbs .th[data-n='%d']" % n2, "#strip [data-id]", steps=14)
                    ok = True
                    try:
                        c.wait_for("Designer.st.blocks.length === 1 && Designer.st.blocks[0].n === %d" % n2, 10)
                    except Exception:  # noqa: BLE001
                        ok = False
                    case("carousel designer: a photo dragged out of a fold onto the frame on the strip takes that frame (the tray's own drag, as ever)", ok, c.js("Designer.st.blocks.map(function(b){ return b.n; })"))
                    c.double_click("#thumbs .th[data-n='%d']" % s.n(vr.H, 3))
                    try:
                        c.wait_for("Designer.big && Designer.big.isOpen()", 5)
                        big = c.js("Designer.big.n()")
                    except Exception:  # noqa: BLE001
                        big = None
                    case("carousel designer: a double-click on a tile in a fold still shows that photo big", big == s.n(vr.H, 3), big)
                    c.key("Escape")
                    core_wait(lambda: c.js("Designer.save.idle()"), 10)
                    case("the page raised no error of its own", not c.page_errors(), c.page_errors()[:3])
                    # a photo added to the vault itself
                    shutil.copyfile(s.content / vr.H / "Photos" / "beach-002.jpg", s.vault() / "Photos" / "added-by-me.jpg")
                    code, out = s.cmd("vault.py", "relist")
                    c.reload()
                    c.wait_for("window.Designer && Designer.st && Designer.vaultTray && Designer.vaultTray.look().ready", 60)
                    f = c.js(TRAY)
                    case("a photo put in the vault's own Photos folder shows under Added to my vault, open, counted, her line gone",
                         code == 0 and f[0]["mine"] and f[0]["open"] and f[0]["all"] == 1 and f[0]["n"] == "1 photo" and f[0]["line"] == "" and len(f[0]["seen"]) == 1, (out[-200:], f[0]))
                    case("...and the design made before is as it was left (the one photo on it)", c.js("Designer.st.blocks.length") == 1 and c.js("Designer.st.blocks[0].n") == n2)
                    s.untouched("the vault's designers in a browser")
                    group("a plain shoot's designer, as it was")
                    c.open(s.url("/design.html?kit=" + quote(vr.H)))
                    c.wait_for("window.Designer && Designer.st && document.querySelectorAll('#thumbs .th').length === 8", 60)
                    case("a plain shoot's tray is one flat list of its photos: no folds, no search box, no chips",
                         c.count("#thumbs > .th") == 8 and c.count("#thumbs details") == 0 and c.count("#vq") == 0 and c.count("#vshoots") == 0 and c.js("!!Designer.vaultTray") is False)
        if a.no_chrome:
            s.untouched("the vault's designer pages by request")
    finally:
        s.stop()
        shutil.rmtree(work, ignore_errors=True)      # this run's own scratch folder, made a moment ago
    return finish()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("part", choices=["rules", "first", "vault", "all"])
    ap.add_argument("--port", type=int, default=9940)
    ap.add_argument("--no-chrome", action="store_true")
    a = ap.parse_args()
    if any(p in NEVER for p in range(a.port, a.port + 40)):
        print("STOP: that port range reaches one the real pages use.")
        return 2
    if a.part == "all":
        # each part in a process of its own: each imports the Assistant's scripts against its own scratch STUDIO_HOME
        rc = 0
        for i, part in enumerate(("rules", "first", "vault")):
            cmd = [sys.executable, str(Path(__file__).resolve()), part, "--port", str(a.port + 20 * (i > 1))] + (["--no-chrome"] if a.no_chrome else [])
            rc = subprocess.call(cmd) or rc
        return rc
    if a.part == "rules":
        return part_rules()
    if a.part == "first":
        return part_first(a)
    return part_vault(a)


if __name__ == "__main__":
    sys.exit(main())
