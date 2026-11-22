#!/usr/bin/env python3
"""Bringing reels and talking reels made on the older pages into their post kits (bring_older.py, Nov 18).

    python3 tests/bring_older_check.py
    python3 tests/bring_older_check.py --scripts <a copy of studio-manager/scripts>     (to try a guard taken out)

The older records here are hand-built in the older pages' shape (nothing of the prototype is run or copied):
<The Assistant>/.studio/reel-pages/<shoot>.json, talking/<shoot>.json and cache/photos/<mark>/photos.json.

What it holds:
  look            changes nothing at all (every file under the scratch folder, byte for byte), and says what it
                  would do: the kit, each reel, every photo number both ways, what can't be brought
  an empty kit    two reels of one shoot become its reels, under their names, the open one open; numbers that
                  differ between the two numberings land on the same FILE NAMES; the photos are numbered first
                  through kit.py's own sheet; the assistant's pick goes to kit.json only when there was none; the
                  song by our id; clips only for a video that is there; a made reel only when CapCut has it
  a kit with a    hers is ADDED under a free name; the reel that was there is exactly as it was, still open; the
  reel already    version before is kept; kit.json (its own pick) is byte for byte the same; a sheet with a gap and
                  a retired number
  not provable    a number the older list doesn't have stops only that reel; no older list: asks, and with
                  --photos-unchanged goes by name order, unless a photo is newer than the reel
  talking reels   brought with the script tied to the video by OUR key; a fixed word becomes a fix; photo numbers
                  turned; added beside a talking reel already there; a video saved again is not brought; a video
                  that already has a script here is not written over
  twice           a second bring writes nothing; a run cut off at three points is finished by the next
  after review    name order is never proof (a photo added later on the older pages went at the END): bring wants
  (Nov 18)        --names-confirmed; a reel record here that can't be read, or is cut short, is never taken for
                  empty; a reel keeps its older id (a queued post says which reel by it), and a taken id is said;
                  two older talking reels on one video with two scripts: one comes; a record with only clips
                  taken out is not empty; one that was only opened is; one odd older record stops only its shoot;
                  a photo in the folder with no number yet is numbered first; "Let my assistant choose" with
                  another order showing comes as their own order; and a check for each smaller guard
  the older       unchanged byte for byte at the end
  records
  our readers     reel_page.state, reels.listed, talking_rec show and state_for_page read what was brought

Nothing here touches the real ~/.studio, a real kit, a drive, CapCut or a window: a scratch folder only.
Python 3.9, standard library only.
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--scripts", default=str(ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"))
ARGS = ap.parse_args()
SCRIPTS = Path(ARGS.scripts).resolve()

TMP = Path(tempfile.mkdtemp(prefix="bring-older-")).resolve()
STUDIO = TMP / "studio"
HOME = TMP / "The Assistant"
CONTENT = HOME / "Your Content"
OLD = HOME / ".studio"
STORE = TMP / "capcut"
os.environ.update(STUDIO_HOME=str(STUDIO), STUDIO_NO_WINDOWS_FOR_TESTS="1", ASSISTANT_TEST_TALKING_STORE=str(STORE),
                  PYTHONIOENCODING="utf-8")
os.environ.pop("ASSISTANT_TEST_BRING_STOP", None)
sys.path.insert(0, str(SCRIPTS))

PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   [{str(detail)[:900]}]"), flush=True)


def run(*args, stop=None, fail=None):
    env = dict(os.environ)
    env.pop("ASSISTANT_TEST_BRING_RAISE", None)
    if stop:
        env["ASSISTANT_TEST_BRING_STOP"] = stop
    if fail:
        env["ASSISTANT_TEST_BRING_RAISE"] = fail
    r = subprocess.run([sys.executable, str(SCRIPTS / "bring_older.py"), *args], capture_output=True, encoding="utf-8",
                       errors="replace", env=env, timeout=300)
    return r.returncode, r.stdout + r.stderr


def tree(folder):
    """{relative path: sha1 of its bytes} for every file under a folder."""
    out = {}
    for d, _dirs, files in os.walk(folder):
        for f in files:
            p = Path(d) / f
            out[str(p.relative_to(folder))] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def changed(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def strings(x):
    """Every string inside a JSON value (keys too)."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings(k)
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def no_path(obj, folder):
    """No string in it holds this folder's path (compared as text, so a PC's backslashes count too)."""
    return not any(str(folder) in s or Path(folder).as_posix() in s for s in strings(obj))


def sect(out, name):
    """What the output says about one shoot (from its heading to the next shoot's)."""
    mark = f"(the older records are named \"{name}\")"
    if mark not in out:
        return ""
    rest = out.split(mark, 1)[1]
    return rest.split("(the older records are named", 1)[0]


def jpeg(path, w=1200, h=1800):
    path.write_bytes(b"\xff\xd8\xff\xc0\x00\x11\x08" + struct.pack(">HH", h, w) + b"\x03" + bytes(9) + b"\xff\xd9" + path.name.encode("utf-8"))


def old_time(path, ago):
    t = time.time() - ago
    os.utime(path, (t, t))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_kit(folder, photos, sheet=None, retired=(), extra=()):
    k = CONTENT / folder
    for d in (".kit", "Photos", "Music", "Footage", "Talking"):
        (k / d).mkdir(parents=True)
    for f in list(photos) + list(extra):
        jpeg(k / "Photos" / f)
        old_time(k / "Photos" / f, 40 * 86400)
    write(k / ".kit" / "kit.json", {"name": folder.split(" ", 1)[1], "folder": folder})
    if sheet:
        write(k / ".kit" / "sheet.json", {"folder": str(k / "Photos"),
                                          "photos": [{"n": n, "file": str(k / "Photos" / f), "w": 1200, "h": 1800, "way": "tall"} for n, f in sheet],
                                          "retired": [{"n": n, "file": f} for n, f in retired]})
    return k


def old_list(shoot, names):
    mark = hashlib.sha1(shoot.encode("utf-8")).hexdigest()[:12]
    write(OLD / "cache" / "photos" / mark / "photos.json",
          [{"n": i, "src": f"/photo/{i}", "w": 1200, "h": 1800, "file": f, "way": "tall"} for i, f in enumerate(names, 1)])


def video(path, ago=30 * 86400):
    path.write_bytes(b"not really a video: " + path.name.encode("utf-8") * 40)
    old_time(path, ago)


def order(text):
    out = []
    for tok in text.split(","):
        h = tok[-1] if tok[-1] in "+-" else ""
        out.append({"n": int(tok.rstrip("+-")), "h": h})
    return out


def names_of(kit, lst):
    """The file names a list of {n} of OUR record means, by the kit's numbered list."""
    by = {x["n"]: Path(x["file"]).name for x in read(kit / ".kit" / "sheet.json")["photos"]}
    return [by.get(x["n"] if isinstance(x, dict) else x) for x in lst]


SAID = "OK so um we were at the beach. And when when the kids ran in it was awesome.".split()


def old_words(fix=None):
    ws = [{"w": w, "start": round(i * 0.5, 3), "end": round(i * 0.5 + 0.25, 3), "conf": 0.9} for i, w in enumerate(SAID)]
    if fix:
        i, text = fix
        ws[i] = dict(ws[i], w=text, w0=ws[i]["w"])
    return ws


try:
    STUDIO.mkdir(parents=True)
    STORE.mkdir()
    write(STUDIO / "studio.json", {"posts": {"home": str(HOME)}})
    (HOME / "Drop a shoot here").mkdir(parents=True)
    CONTENT.mkdir()

    # ----- Katie: an empty kit, no numbered list yet, two reels in the older record -----
    KATIE = "2026-10-02 Katie Austin Maternity"
    K_OLD = ["B_002.jpg", "a_001.jpg", "c_003.jpg", "d_004.jpg", "e_005.jpg"]          # the older order: capitals first
    katie = make_kit(KATIE, K_OLD, extra=["a_000.png"])                                # ours: a_000.png is 1, a_001 2, B_002 3...
    old_list(KATIE, K_OLD)
    (katie / "Music" / "song.mp3").write_bytes(b"ID3" + bytes(4000))
    video(katie / "Footage" / "bts.mov")
    (STORE / "Katie reel").mkdir()
    write(OLD / "reel-pages" / f"{KATIE}.json", {
        # the open reel ("White Backdrop", v2) is at the top; "Fun Maternity" (v1) waits in its data
        "versions": [{"id": "v1", "name": "Fun Maternity", "data": {
            "claude": order("1,2+,3-"),
            "saved": {"picks": order("1,2+,3-"), "mine": False, "mine_picks": None, "song": "Music/song.mp3", "vibe": "calm",
                      "footage": True, "style": "reveal", "sel": {"reveal": ["m1-aaaaaa", "m2-bbbbbb"]}, "ask": "the laughing",
                      "feel": "fun", "photo_ask": "outdoors only", "updated": 1763000000.5},
            "moments": [{"id": "m1-aaaaaa", "video": "Footage/bts.mov", "start": 1.0, "end": 4.5, "label": "Twirl", "photo": 1, "keep": True, "about": "she spins"},
                        {"id": "m2-bbbbbb", "video": "Footage/gone.mov", "start": 2.0, "end": 5.0, "label": "Gone", "photo": None, "keep": True}],
            "claude_bts": order("1,3"),
        }}, {"id": "v2", "name": "White Backdrop"}],
        "current": "v2",
        "claude": order("4,5"),
        "saved": {"picks": order("5+,4,1"), "mine": True, "mine_picks": order("5+,4,1"), "song": "Music/not-there.mp3", "vibe": "beat",
                  "footage": False, "style": "first", "sel": {}, "ask": "", "feel": "", "updated": 1763000100.0,
                  "onscreen": {"text": "Hello", "font": "georgia", "style": "white", "pos": "top", "hold": "3"}},
        "moments": [],
        "made": [{"project": "Katie reel", "picks": "1,2+,3-", "vibe": "calm", "version": "v1", "footage": "reveal", "song": "/Volumes/Somewhere/secret/song.mp3", "when": 1763000200.0},
                 {"project": "Katie reel 2", "picks": "5+,4,1", "vibe": "beat", "version": "v2", "footage": None, "song": "", "when": 1763000300.0}],
    })
    write(OLD / "reel-pages" / f"{KATIE}.prev.json", {"saved": {"picks": order("5")}})

    # ----- Hannah: a kit with a reel, a pick and a talking reel of its own; a list with a gap and a retired number -----
    HANNAH = "2026-09-23 Hannah"
    H_NOW = ["h1.jpg", "h2.jpg", "h4.jpg", "h5.jpg"]
    hannah = make_kit(HANNAH, H_NOW, sheet=[(1, "h1.jpg"), (2, "h2.jpg"), (4, "h4.jpg"), (5, "h5.jpg")], retired=[(3, "h3.jpg")])
    old_list(HANNAH, H_NOW)                                 # the older list numbered them again from 1: h4 is 3, h5 is 4
    import arrange, reel_page, reels, talking_rec as TR     # noqa: E401,E402
    stamp = arrange.sheet_stamp(hannah)
    write(hannah / ".kit" / "kit.json", dict(read(hannah / ".kit" / "kit.json"), picks={"reel": [5, 1]}, reel_marks={"5": "+"}))
    write(hannah / ".kit" / "reel-page.json", {"v": 1, "rev": 3, "stamp": stamp, "names": {"1": "h1.jpg", "2": "h2.jpg"},
                                                "saved": {"picks": order("2,1"), "mine": True, "mine_picks": order("2,1"), "song": None, "vibe": "beat",
                                                          "footage": False, "style": "first", "ask": "", "feel": "", "sel": {}, "kind": "photos",
                                                          "updated": 1763100000.0}})
    write(OLD / "reel-pages" / f"{HANNAH}.json", {
        "claude": order("3,4"),
        "saved": {"picks": order("4,3-,1"), "mine": False, "mine_picks": None, "song": "", "vibe": "build", "footage": False,
                  "style": "first", "updated": 1763000000.0},
        "made": [{"project": "Hannah reel", "picks": "4,3-,1", "vibe": "build", "song": "", "when": 1763000001.0}],
    })
    video(hannah / "Talking" / "talk.mov")
    video(hannah / "Talking" / "mine.mov")
    video(hannah / "Footage" / "walk.mov")
    T_MADE = (hannah / "Talking" / "talk.mov").stat().st_mtime + 3600
    TR.put_words(hannah, "mine.mov", TR._key_of(hannah / "Talking" / "mine.mov"),
                 [{"w": w, "start": i * 0.4, "end": i * 0.4 + 0.3, "conf": 1} for i, w in enumerate("this one is mine".split())])
    write(OLD / "talking" / f"{HANNAH}.json", {
        "video": "talk.mov", "status": "ready", "step": "", "words": old_words(fix=(2, "uh")), "sentences": [[0, 7], [8, 17]],
        "info": {"w": 1080, "h": 1920, "dur": 9.5}, "transcribed": T_MADE, "cut": [[0, 2], [9, 9], [40, 44]],
        "claude_cut": [[0, 2]], "claude_why": ["warm-up"], "splits": [8], "speeds": [{"a": 3, "b": 5, "v": 1.5}],
        "zooms": [{"a": 10, "b": 12, "kind": "punch"}],
        "shots": [{"a": 3, "b": 5, "ns": [3, 4], "v": None, "from": 0, "spot": "behind", "pos": None, "me": None},
                  {"a": 10, "b": 12, "ns": [], "v": "walk.mov", "from": 1.5, "spot": "full", "pos": None, "me": None},
                  {"a": 14, "b": 15, "ns": [], "v": "lost.mov", "from": 0, "spot": "full", "pos": None, "me": None}],
        "moves": {}, "photos": {}, "captions": False, "cap_pos": {"x": 0.5, "y": 0.8}, "cap_size": 1.4, "photo_mode": "me",
        "made": [{"project": "Hannah talking reel", "when": 1763000002.0}], "updated": T_MADE + 50,
    })

    # ----- Aurora: one reel with a number the older list doesn't have, one that is fine; a video saved again -----
    AURORA = "2026-09-30 Aurora"
    A_NOW = ["x1.jpg", "x2.jpg", "x3.jpg"]
    aurora = make_kit(AURORA, A_NOW, sheet=[(1, "x1.jpg"), (2, "x2.jpg"), (3, "x3.jpg")])
    old_list(AURORA, A_NOW + ["x4-taken-out.jpg"])
    write(OLD / "reel-pages" / f"{AURORA}.json", {
        "versions": [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 2", "data": {"saved": {"picks": order("2,1"), "mine": True, "song": None, "vibe": "beat"}}},
                     {"id": "v3", "name": "Reel 3", "data": {"saved": {"picks": order("1,4"), "mine": True, "song": None, "vibe": "beat"}}}],
        "current": "v1", "saved": {"picks": order("3,9"), "mine": True, "song": None, "vibe": "beat"}})
    video(aurora / "Talking" / "again.mov", ago=3600)
    write(OLD / "talking" / f"{AURORA}.json", {
        "video": "again.mov", "status": "ready", "words": old_words(), "info": {"w": 1080, "h": 1920, "dur": 9.5},
        "transcribed": time.time() - 20 * 86400, "cut": [], "shots": []})

    # ----- Nolist: the older list of photos is gone -----
    NOLIST = "2026-10-05 Nolist"
    nolist = make_kit(NOLIST, ["Z9.jpg", "b2.jpg", "a1.jpg"], sheet=[(1, "a1.jpg"), (2, "b2.jpg"), (3, "Z9.jpg"), (4, "A0.png")], extra=["A0.png"])
    write(OLD / "reel-pages" / f"{NOLIST}.json", {"saved": {"picks": order("1,2"), "mine": True, "song": None, "vibe": "mixed"}})
    old_time(OLD / "reel-pages" / f"{NOLIST}.json", 5 * 86400)        # last saved five days ago

    # ----- Cut: for the run cut off part way -----
    CUT = "2026-10-10 Cut"
    cut = make_kit(CUT, ["c1.jpg", "c2.jpg"])
    old_list(CUT, ["c1.jpg", "c2.jpg"])
    video(cut / "Talking" / "say.mov")
    write(OLD / "reel-pages" / f"{CUT}.json", {"claude": order("2,1"), "saved": {"picks": order("2,1"), "mine": False, "song": None, "vibe": "beat"}})
    write(OLD / "talking" / f"{CUT}.json", {"video": "say.mov", "status": "ready", "words": old_words(), "info": {"dur": 9.5},
                                            "transcribed": time.time() - 86400, "cut": [[0, 1]], "shots": [{"a": 3, "b": 4, "ns": [2], "spot": "full"}]})

    # ----- Pick: no reel here yet, but the kit has a reel pick of its own -----
    PICK = "2026-10-12 Pick"
    pick = make_kit(PICK, ["p1.jpg", "p2.jpg"], sheet=[(1, "p1.jpg"), (2, "p2.jpg")])
    old_list(PICK, ["p1.jpg", "p2.jpg"])
    write(pick / ".kit" / "kit.json", dict(read(pick / ".kit" / "kit.json"), picks={"reel": [2]}, reel_marks={}))
    write(OLD / "reel-pages" / f"{PICK}.json", {"claude": order("1,2"), "saved": {"picks": order("1,2"), "mine": False, "song": None, "vibe": "beat"}})

    # ----- Ghost: an older record with no post kit -----
    write(OLD / "reel-pages" / "2026-01-01 Ghost.json", {"saved": {"picks": order("1"), "mine": True}})

    # ================= fixtures for the review's findings (Nov 18) =================
    def reel_rec(kit, **more):
        d = {"v": 1, "rev": 1, "stamp": arrange.sheet_stamp(kit)}
        d.update(more)
        return d

    def plain(n, **more):
        return [(i, f"{more.get('stem', 'p')}{i}.jpg") for i in range(1, n + 1)]

    OWN = {"picks": [], "mine": True, "mine_picks": [], "song": None, "vibe": "beat", "footage": None, "style": "first",
           "ask": "", "feel": "", "sel": {}, "updated": 1763100000.0}

    # ----- Late: a photo was added on the older page AFTER its first numbering, so it sat at the end there -----
    LATE = "2026-10-14 Late"
    late = make_kit(LATE, ["b1.jpg", "c1.jpg", "a_added.jpg"], sheet=[(1, "a_added.jpg"), (2, "b1.jpg"), (3, "c1.jpg")])
    write(OLD / "reel-pages" / f"{LATE}.json", {"saved": {"picks": order("3,1"), "mine": True, "song": None, "vibe": "beat"}})   # there: a_added, b1
    old_time(OLD / "reel-pages" / f"{LATE}.json", 5 * 86400)

    # ----- Retired: no older list, and a photo has left this shoot since it was numbered -----
    RETIRED = "2026-10-15 Retired"
    retired = make_kit(RETIRED, ["r1.jpg", "r3.jpg"], sheet=[(1, "r1.jpg"), (3, "r3.jpg")], retired=[(2, "r2.jpg")])
    write(OLD / "reel-pages" / f"{RETIRED}.json", {"saved": {"picks": order("1"), "mine": True, "song": None, "vibe": "beat"}})
    old_time(OLD / "reel-pages" / f"{RETIRED}.json", 5 * 86400)

    # ----- Torn: this kit's own reel record is cut short, with a good earlier version beside it -----
    TORN = "2026-10-16 Torn"
    torn = make_kit(TORN, ["p1.jpg", "p2.jpg"], sheet=plain(2))
    old_list(TORN, ["p1.jpg", "p2.jpg"])
    (torn / ".kit" / "reel-page.json").write_bytes(b'{"v": 1, "rev": 7, "saved": {"pi')
    write(torn / ".kit" / "reel-page.prev.json", reel_rec(torn, rev=6, saved=dict(OWN, picks=order("2,1"), mine_picks=order("2,1"))))
    write(OLD / "reel-pages" / f"{TORN}.json", {"saved": {"picks": order("1,2"), "mine": True, "song": None, "vibe": "beat"}})

    # ----- Locked: this kit's own reel record can't be read at the moment of the bring -----
    LOCKED = "2026-10-17 Locked"
    locked = make_kit(LOCKED, ["p1.jpg", "p2.jpg"], sheet=plain(2))
    old_list(LOCKED, ["p1.jpg", "p2.jpg"])
    write(locked / ".kit" / "reel-page.json", reel_rec(locked, rev=7, saved=dict(OWN, picks=order("2,1"), mine_picks=order("2,1"))))
    write(OLD / "reel-pages" / f"{LOCKED}.json", {"saved": {"picks": order("1,2"), "mine": True, "song": None, "vibe": "beat"}})

    # ----- Queue: a kit with a reel of its own and posts in the queue; the older record has v1 and v2 -----
    QUEUE = "2026-10-18 Queue"
    queue = make_kit(QUEUE, ["p1.jpg", "p2.jpg", "p3.jpg"], sheet=plain(3))
    old_list(QUEUE, ["p1.jpg", "p2.jpg", "p3.jpg"])
    write(queue / ".kit" / "reel-page.json", reel_rec(queue, rev=2, saved=dict(OWN, picks=order("3"), mine_picks=order("3"))))
    write(OLD / "reel-pages" / f"{QUEUE}.json", {
        "versions": [{"id": "v1", "name": "Fun Maternity", "data": {"saved": {"picks": order("1,2"), "mine": True, "song": None, "vibe": "beat"}}},
                     {"id": "v2", "name": "White Backdrop"}],
        "current": "v2", "saved": {"picks": order("2,3"), "mine": True, "song": None, "vibe": "beat"}})
    write(STUDIO / "posting.json", {"pieces": [
        {"id": "kit:2026-10-18-queue-reel", "kit": str(queue), "shoot_name": "Queue", "kind": "reel", "status": "green"},
        {"id": "kit:2026-10-18-queue-reel-v2", "kit": str(queue), "shoot_name": "Queue", "kind": "reel", "status": "green", "reel_name": "White Backdrop"}],
        "interval": None, "reminded": {}})

    # ----- Twotalk: two older talking reels on ONE video, each with a script of its own -----
    TWO = "2026-10-19 Twotalk"
    two = make_kit(TWO, ["p1.jpg"], sheet=plain(1))
    old_list(TWO, ["p1.jpg"])
    video(two / "Talking" / "talk.mov")
    two_made = (two / "Talking" / "talk.mov").stat().st_mtime + 3600
    heard_again = old_words()
    heard_again[4] = dict(heard_again[4], w="or")                # the second time, one word was heard differently
    write(OLD / "talking" / f"{TWO}.json", {
        "versions": [{"id": "v1", "name": "Talking reel 1", "data": {"video": "talk.mov", "status": "ready", "words": old_words(),
                                                                       "info": {"dur": 9.5}, "transcribed": two_made, "cut": [[0, 2]]}},
                     {"id": "v2", "name": "Short one"}],
        "current": "v2", "video": "talk.mov", "status": "ready", "words": heard_again, "info": {"dur": 9.5},
        "transcribed": two_made, "cut": [[5, 11]]})

    # ----- Undo: a record here that holds only a clip they took out, and an earlier pick -----
    UNDO = "2026-10-20 Undo"
    undo = make_kit(UNDO, ["p1.jpg", "p2.jpg"], sheet=plain(2))
    old_list(UNDO, ["p1.jpg", "p2.jpg"])
    GONE_CLIP = {"id": "u1-abcdef", "video": "Footage/x.mov", "start": 1.0, "end": 3.0, "label": "The twirl", "by": "you"}
    write(undo / ".kit" / "reel-page.json", reel_rec(undo, rev=5, moments=[], removed=[GONE_CLIP], claude_earlier=["2,1"]))
    write(OLD / "reel-pages" / f"{UNDO}.json", {"saved": {"picks": order("1,2"), "mine": True, "song": None, "vibe": "beat"}})

    # ----- Touched: the reel page here was only opened (its choices at their starting values) -----
    TOUCHED = "2026-10-21 Touched"
    touched = make_kit(TOUCHED, ["p1.jpg", "p2.jpg"], sheet=plain(2))
    old_list(TOUCHED, ["p1.jpg", "p2.jpg"])
    write(touched / ".kit" / "reel-page.json", reel_rec(touched, saved=dict(OWN, kind="photos")))
    write(OLD / "reel-pages" / f"{TOUCHED}.json", {
        "versions": [{"id": "v1", "name": "Fun Maternity", "data": {"saved": {"picks": order("1"), "mine": True, "song": None, "vibe": "beat"}}},
                     {"id": "v2", "name": "White Backdrop"}],
        "current": "v2", "saved": {"picks": order("2"), "mine": True, "song": None, "vibe": "beat"}})

    # ----- Abad and Deep: older records that are odd -----
    ABAD = "2026-10-22 Abad"
    abad = make_kit(ABAD, ["p1.jpg"], sheet=plain(1))
    old_list(ABAD, ["p1.jpg"])
    write(OLD / "reel-pages" / f"{ABAD}.json", {"saved": {"picks": order("1"), "mine": True, "song": None, "vibe": "beat", "sel": {"first": [["x"]]}},
                                                "moments_found": [{"id": "m1-aaaaaa", "video": "Footage/none.mov", "start": 1, "end": 2, "label": [[["deep"]]]}]})
    DEEP = "2026-10-23 Deep"
    deep = make_kit(DEEP, ["p1.jpg"], sheet=plain(1))
    (OLD / "reel-pages" / f"{DEEP}.json").write_text("[" * 20000 + "]" * 20000, encoding="utf-8")

    # ----- Behind: a photo is in the Photos folder and not on this shoot's numbered list yet -----
    BEHIND = "2026-10-24 Behind"
    behind = make_kit(BEHIND, ["p1.jpg", "p2.jpg", "p3.jpg"], sheet=plain(2))
    old_list(BEHIND, ["p1.jpg", "p2.jpg", "p3.jpg"])
    write(OLD / "reel-pages" / f"{BEHIND}.json", {"saved": {"picks": order("3,1"), "mine": True, "song": None, "vibe": "beat"}})

    # ----- Stale: "Let my assistant choose" there, with an order on the page that is not the pick as it stands -----
    STALE = "2026-10-25 Stale"
    stale = make_kit(STALE, ["p1.jpg", "p2.jpg", "p3.jpg", "p4.jpg"], sheet=plain(4))
    old_list(STALE, ["p1.jpg", "p2.jpg", "p3.jpg", "p4.jpg"])
    write(OLD / "reel-pages" / f"{STALE}.json", {"claude": order("1,2,3"), "saved": {"picks": order("1+,2,4"), "mine": False, "mine_picks": None,
                                                                                    "song": None, "vibe": "beat"}})

    # ----- Samevid: the older talking reel's video is already the video of a talking reel here (same script) -----
    SAMEVID = "2026-10-26 Samevid"
    samevid = make_kit(SAMEVID, ["p1.jpg"], sheet=plain(1))
    old_list(SAMEVID, ["p1.jpg"])
    video(samevid / "Talking" / "same.mov")
    TR.put_words(samevid, "same.mov", TR._key_of(samevid / "Talking" / "same.mov"), old_words())
    write(OLD / "talking" / f"{SAMEVID}.json", {"video": "same.mov", "status": "ready", "words": old_words(), "info": {"dur": 9.5},
                                                "transcribed": time.time() - 86400, "cut": [[0, 1]]})

    # ----- Talks: three older talking reels, each short of something -----
    TALKS = "2026-10-27 Talks"
    talks = make_kit(TALKS, ["p1.jpg"], sheet=plain(1))
    old_list(TALKS, ["p1.jpg"])
    for f in ("a.mov", "b.mov", "c.mov", "d.mov"):
        video(talks / "Talking" / f)
    t_ok = time.time() - 86400
    no_times = old_words()
    no_times[3] = {"w": "were"}
    late_words = [dict(w, start=w["start"] + 60, end=w["end"] + 60) for w in old_words()]
    write(OLD / "talking" / f"{TALKS}.json", {
        "versions": [{"id": "v1", "name": "No date"},
                     {"id": "v2", "name": "Not finished", "data": {"video": "b.mov", "status": "working", "words": old_words(), "transcribed": t_ok}},
                     {"id": "v3", "name": "A word short", "data": {"video": "c.mov", "status": "ready", "words": no_times, "info": {"dur": 9.5}, "transcribed": t_ok}},
                     {"id": "v4", "name": "Too long", "data": {"video": "d.mov", "status": "ready", "words": late_words, "info": {"dur": 9.5}, "transcribed": t_ok}}],
        "current": "v1", "video": "a.mov", "status": "ready", "words": old_words(), "info": {"dur": 9.5}})

    # ----- Many: more photos in one reel than a reel here holds -----
    MANY = "2026-10-28 Many"
    MOST = reel_page.MAX_PICKS + 1
    many = make_kit(MANY, [f"m{i:02d}.jpg" for i in range(1, MOST + 1)], sheet=[(i, f"m{i:02d}.jpg") for i in range(1, MOST + 1)])
    old_list(MANY, [f"m{i:02d}.jpg" for i in range(1, MOST + 1)])
    write(OLD / "reel-pages" / f"{MANY}.json", {"saved": {"picks": order(",".join(str(i) for i in range(1, MOST + 1))), "mine": True, "song": None, "vibe": "beat"}})

    OLD_BEFORE = tree(OLD)

    # ================= look =================
    before = tree(TMP)
    code, out = run("look")
    after = tree(TMP)
    check("look: changes nothing at all (every file under the scratch folder, byte for byte)", not changed(before, after), changed(before, after))
    check("look: says some can't be brought (exit 1) and that nothing was changed", code == 1 and "Nothing was changed" in out and "Traceback" not in out, (code, out[-600:]))
    check("look: names the kit each shoot matched, and the shoot with no kit", f"Post kit: \"{KATIE}\"" in out and "No post kit by that name" in out, out[:800])
    check("look: how the numbers were checked (the older page's own list, by file name)", "older page's own numbered list" in out and "by its file name" in out, out)
    check("look: every photo number both ways (older 1 is B_002.jpg, 3 here)", "photo 1 there is \"B_002.jpg\", number 3 here" in out
          and "photo 5 there is \"e_005.jpg\", number 6 here" in out, out)
    check("look: a kit with no numbers yet is told so, numbers shown as they will be", "no numbers here yet" in out, out)
    check("look: Hannah's gap (older 3 is h4.jpg, 4 here; older 4 is h5.jpg, 5 here)", "photo 3 there is \"h4.jpg\", number 4 here" in out
          and "photo 4 there is \"h5.jpg\", number 5 here" in out, out)
    check("look: a reel beside one already here is added under a free name", "\"Reel 1 (older)\" because \"Reel 1\" is taken" in out and "beside the 1 already here" in out, out)
    check("look: the reel with a number the older list lacks can't be brought, and says which", "Reel \"Reel 1\": can't be brought: photo 9" in out, out)
    check("look: a photo that has left the shoot stops only its reel", "photo 4 (\"x4-taken-out.jpg\") is not among this shoot's photos now" in out
          and "Reel \"Reel 2\": can be brought" in out, out)
    check("look: no older list: asks whether photos changed, guesses nothing", "can't be checked" in out and "--photos-unchanged" in out
          and "Reel \"Reel 1\": can't be brought: the older page's own list" in out, out)
    check("look: a talking video saved again can't be brought", "\"again.mov\" was saved again after its script was made" in out, out)
    check("look: what is left out is named (a song that is gone, a video that is gone, a project CapCut hasn't)",
          "the song \"not-there.mp3\"" in out and "\"gone.mov\"" in out and "\"Katie reel 2\" as made" in out and "\"lost.mov\"" in out, out)
    check("look: no path of the scratch folder in what it says", str(TMP) not in out, out)
    # --- after the review (Nov 18)
    check("look: with no older list it asks whether photos were EVER added there, not only since the reel", "did you ever add photos" in out
          and "since you made the reel" not in out, out)
    check("look: a clip's description is named as left out", "the clips' descriptions" in sect(out, KATIE), sect(out, KATIE))
    check("look: an older record that can't even be parsed stops only its own shoot", "STOP" not in out and "the older record can't be read" in sect(out, DEEP)
          and f"Post kit: \"{MANY}\"" in out, sect(out, DEEP))
    check("look: an odd list inside an older record is read past (the shoot can still be brought)", "Reel \"Reel 1\": can be brought" in sect(out, ABAD), sect(out, ABAD))
    code2, out2 = run("look", fail="Katie")
    check("look: a shoot that fails in a way nobody foresaw is left as it is, and the shoots after it carry on",
          code2 == 1 and "STOP" not in out2 and "couldn't make sense of this shoot's older records" in out2 and f"Post kit: \"{HANNAH}\"" in out2, (code2, out2[:900]))
    check("look: this kit's own reel record cut short is never taken for empty", "Reel \"Reel 1\": can't be brought: this shoot's own reel record here is there but can't be read" in sect(out, TORN), sect(out, TORN))
    check("look: an older id that is taken here: the queued post to check is named",
          "Check: a post in the posting queue (\"Queue reel\") belongs to the reel \"Reel 1\" that is already here" in sect(out, QUEUE)
          and "it was meant for \"Fun Maternity\"" in sect(out, QUEUE) and sect(out, QUEUE).count("Check:") == 1, sect(out, QUEUE))
    check("look: two older talking reels on one video with two scripts: only the open one can come",
          "Talking reel \"Talking reel 1\": can't be brought" in sect(out, TWO) and "with a different script" in sect(out, TWO)
          and "Talking reel \"Short one\": can be brought" in sect(out, TWO), sect(out, TWO))
    check("look: a record here with only a clip taken out is a reel (the older one goes beside it)", "added as another reel" in sect(out, UNDO)
          and "beside the 1 already here" in sect(out, UNDO), sect(out, UNDO))
    check("look: a reel page here that was only opened is no reel (the older ones become its reels)",
          "Reel \"Fun Maternity\": can be brought: becomes this shoot's reel" in sect(out, TOUCHED) and "beside" not in sect(out, TOUCHED)
          and "(older)" not in sect(out, TOUCHED), sect(out, TOUCHED))
    check("look: a photo in the folder with no number here yet is not called missing; its number is shown as it will be",
          "have no number here yet" in sect(out, BEHIND) and "photo 3 there is \"p3.jpg\", number 3 here" in sect(out, BEHIND)
          and "can be brought" in sect(out, BEHIND) and "not among" not in sect(out, BEHIND), sect(out, BEHIND))
    check("look: \"Let the Assistant choose\" with another order showing: said", "comes over as their own order" in sect(out, STALE), sect(out, STALE))
    check("look: a video that is already a talking reel's here (same script) is left alone", "is already the video of a talking reel here" in sect(out, SAMEVID), sect(out, SAMEVID))
    check("look: a talking reel with no date for its script; one never finished; one with a word short; one whose words run past the video",
          "doesn't say when" in sect(out, TALKS) and "was never turned into a script" in sect(out, TALKS)
          and "some of its words can't be read" in sect(out, TALKS) and "run past the end of the video" in sect(out, TALKS)
          and "can be brought" not in sect(out, TALKS), sect(out, TALKS))
    check("look: a reel with more photos than a reel here holds", f"more than {reel_page.MAX_PICKS} photos" in sect(out, MANY), sect(out, MANY))
    code, out2 = run("look", "--shoot", "nolist", "--photos-unchanged")
    check("look --photos-unchanged: name order, capitals first, JPEGs only (older 1 is Z9.jpg, 3 here; the png has no number there)",
          code == 0 and "photo 1 there is \"Z9.jpg\", number 3 here" in out2 and "name order" in out2 and "A0.png" not in out2, (code, out2))
    check("...and it says this is NOT checked, and what bring will want", "NOT checked" in out2 and "--names-confirmed" in out2, out2)
    code, out2 = run("look", "--shoot", "late", "--photos-unchanged")
    check("look --photos-unchanged: the photo names are there to be read back (here they are the WRONG ones: a photo was added later there)",
          "photo 3 there is \"c1.jpg\"" in out2 and "NOT checked" in out2, (code, out2))
    code, out2 = run("bring", "--shoot", "late", "--photos-unchanged")
    check("bring --photos-unchanged alone brings nothing: name order is not proof", code == 1 and "not proof" in out2 and "--names-confirmed" in out2
          and not (late / ".kit" / "reel-page.json").exists() and not (late / ".kit" / "brought-older.json").exists(), (code, out2))
    code, out2 = run("look", "--shoot", "retired", "--photos-unchanged")
    check("look --photos-unchanged: a photo has left this shoot since it was numbered, and name order is refused",
          code == 1 and "taken out of this shoot since it was first numbered" in out2, (code, out2))
    jpeg(nolist / "Photos" / "added-later.jpg")
    code, out2 = run("look", "--shoot", "nolist", "--photos-unchanged")
    check("look --photos-unchanged: a photo newer than the reel, and it is not trusted", code == 1 and "added or saved again after" in out2, (code, out2))
    (nolist / "Photos" / "added-later.jpg").unlink()
    code, out2 = run("look", "--shoot", "nobody at all")
    check("look: a shoot nobody has: stop (exit 2)", code == 2 and "STOP" in out2, (code, out2))
    code, out2 = run("look", "--from", str(TMP / "nowhere"))
    check("look: no older folder: stop (exit 2), plain words", code == 2 and "STOP" in out2 and "Traceback" not in out2, (code, out2))
    check("look (all of it): still nothing changed", not changed(before, tree(TMP)), changed(before, tree(TMP)))

    # ================= a run cut off part way (Cut) =================
    code, out = run("bring", "--shoot", "Cut", stop="after-journal")
    j = read(cut / ".kit" / "brought-older.json") if (cut / ".kit" / "brought-older.json").is_file() else {"runs": [{"state": "", "items": []}]}
    check("cut off after the note: what was about to be written is written down first, nothing else yet",
          code == 9 and j["runs"][-1]["state"] == "started" and len(j["runs"][-1]["items"]) == 2
          and not (cut / ".kit" / "reel-page.json").exists() and not (cut / ".kit" / "talking.json").exists(), (code, j))
    check("the note holds names only, never a path of the older folder", no_path(j, OLD) and not any("/" in i["file"] or "\\" in i["file"] for i in j["runs"][-1]["items"]), j)
    code, out = run("bring", "--shoot", "Cut", stop="after-pick")
    check("cut off after the pick: the pick is in kit.json (kit.py's own writer), no reel record yet",
          code == 9 and read(cut / ".kit" / "kit.json").get("picks", {}).get("reel") == [2, 1] and not (cut / ".kit" / "reel-page.json").exists(), (code, out))
    code, out = run("bring", "--shoot", "Cut", stop="after-words")
    check("cut off after the words: the reel is in, the script is kept, the talking record not yet",
          code == 9 and (cut / ".kit" / "reel-page.json").exists() and "say.mov" in read(cut / ".kit" / "talking-words.json")["videos"]
          and not (cut / ".kit" / "talking.json").exists(), (code, out))
    code, out = run("bring", "--shoot", "Cut")
    crec, ctalk = read(cut / ".kit" / "reel-page.json"), read(cut / ".kit" / "talking.json")
    check("the next run finishes it: the reel once, the talking reel in, exit 0",
          code == 0 and "already brought" in out and "versions" not in crec and ctalk.get("video") == "say.mov" and ctalk.get("status") == "ready"
          and ctalk.get("cut") == [[0, 1]] and read(cut / ".kit" / "brought-older.json")["runs"][-1]["state"] == "finished", (code, out, ctalk))
    check("...the pick was not written twice (no earlier pick kept beside it)", "reel_earlier" not in read(cut / ".kit" / "kit.json"), read(cut / ".kit" / "kit.json"))
    check("...\"Let the Assistant choose\" stays, since the kit's pick is the older one", crec["saved"]["mine"] is False and reel_page.assistant_pick(cut, crec) == order("2,1"), crec)

    # ================= bring, all of it =================
    hannah_kit_json = (hannah / ".kit" / "kit.json").read_bytes()
    hannah_reel = (hannah / ".kit" / "reel-page.json").read_bytes()
    hannah_talk = (hannah / ".kit" / "talking.json").read_bytes()
    hannah_sheet = (hannah / ".kit" / "sheet.json").read_bytes()
    hannah_words = read(hannah / ".kit" / "talking-words.json")
    samevid_before = tree(samevid / ".kit")
    torn_rec, torn_prev = (torn / ".kit" / "reel-page.json").read_bytes(), (torn / ".kit" / "reel-page.prev.json").read_bytes()
    locked_rec = (locked / ".kit" / "reel-page.json").read_bytes()
    touched_rec = (touched / ".kit" / "reel-page.json").read_bytes()
    os.chmod(locked / ".kit" / "reel-page.json", 0)
    cant_read = not os.access(locked / ".kit" / "reel-page.json", os.R_OK)       # not so on a PC, or as root
    try:
        code, out = run("bring")
    finally:
        os.chmod(locked / ".kit" / "reel-page.json", 0o644)
    check("bring: done, some could not be (exit 1), plain words", code == 1 and "Traceback" not in out and "STOP" not in out and str(TMP) not in out, (code, out[-900:]))

    # --- Katie: an empty kit
    rec = read(katie / ".kit" / "reel-page.json")
    check("empty kit: the photos were numbered first, through kit.py's sheet (the png is 1)",
          names_of(katie, [1, 2, 3, 6]) == ["a_000.png", "a_001.jpg", "B_002.jpg", "e_005.jpg"], names_of(katie, [1, 2, 3, 6]))
    check("empty kit: both reels are its reels, under their names, the open one open",
          reels.listed(rec, reel_page.REEL_FIRST) == [{"id": "v1", "name": "Fun Maternity"}, {"id": "v2", "name": "White Backdrop"}]
          and reels.current(rec, reel_page.REEL_FIRST) == "v2", rec.get("versions"))
    v1 = reels.data_of(rec, "v1", reel_page.REEL_LIVE, reel_page.REEL_FIRST)
    check("numbers that differ land on the same file names (open reel: e_005, d_004, B_002)",
          names_of(katie, rec["saved"]["picks"]) == ["e_005.jpg", "d_004.jpg", "B_002.jpg"] and [x["h"] for x in rec["saved"]["picks"]] == ["+", "", ""], rec["saved"])
    check("...and the other reel's (B_002, a_001 Longer, c_003 Quicker), the clip's photo, the footage order",
          names_of(katie, v1["saved"]["picks"]) == ["B_002.jpg", "a_001.jpg", "c_003.jpg"] and [x["h"] for x in v1["saved"]["picks"]] == ["", "+", "-"]
          and names_of(katie, [v1["moments"][0]["photo"]]) == ["B_002.jpg"] and names_of(katie, v1["claude_bts"]) == ["B_002.jpg", "c_003.jpg"], v1)
    check("the record's names are stamped for every number it mentions", rec.get("stamp") == arrange.sheet_stamp(katie)
          and rec["names"].get("3") == "B_002.jpg" and rec["names"].get("6") == "e_005.jpg", rec.get("names"))
    check("the first reel's assistant pick went to kit.json (there was none); the later reel's is in the record",
          read(katie / ".kit" / "kit.json")["picks"]["reel"] == [3, 2, 4] and read(katie / ".kit" / "kit.json")["reel_marks"] == {"2": "+", "4": "-"}
          and names_of(katie, rec["claude"]) == ["d_004.jpg", "e_005.jpg"] and "claude" not in v1, (read(katie / ".kit" / "kit.json"), rec.get("claude")))
    check("the song by our id; one that is gone is left unpicked", v1["saved"]["song"] == reel_page.song_id("Music", "song.mp3") and rec["saved"]["song"] is None, (v1["saved"]["song"], rec["saved"]["song"]))
    check("pace, style, notes come over as they were", v1["saved"]["vibe"] == "calm" and v1["saved"]["style"] == "reveal" and v1["saved"]["ask"] == "the laughing"
          and v1["saved"]["feel"] == "fun" and v1["saved"]["photo_ask"] == "outdoors only" and v1["saved"]["mine"] is False and v1["saved"]["footage"] is True, v1["saved"])
    check("a clip whose video is gone is left out, and out of the chosen clips", [m["id"] for m in v1["moments"]] == ["m1-aaaaaa"] and v1["saved"]["sel"] == {"reveal": ["m1-aaaaaa"]}, v1)
    check("the words on screen pass our check (the place starts at the usual spot)", rec["saved"].get("onscreen", {}).get("text") == "Hello"
          and rec["saved"]["onscreen"]["pos"] == "custom" and rec["saved"]["onscreen"]["font"] == "georgia", rec["saved"].get("onscreen"))
    check("a made reel only when CapCut has the project; numbers turned; marked as its reel's",
          [(m["project"], m["picks"], m.get("version")) for m in rec.get("made", [])] == [("Katie reel", "3,2+,4-", "v1")], rec.get("made"))
    check("each reel says where it came from: a file's name and an id, never a path",
          {k: (v["file"], v["id"]) for k, v in rec["brought_from"].items()} == {"v1": (f"{KATIE}.json", "v1"), "v2": (f"{KATIE}.json", "v2")}
          and no_path(rec, TMP), rec.get("brought_from"))
    check("the older .prev.json beside a record is not taken for a shoot", "Katie Austin Maternity.prev" not in out, out)
    st = reel_page.state(katie)
    check("our reader (reel_page.state): both reels, the open one's photos, the pick", st and [v["name"] for v in st["versions"]] == ["Fun Maternity", "White Backdrop"]
          and st["current"] == "v2" and [x["n"] for x in st["saved"]["picks"]] == [6, 5, 3] and st["made"] == {"v1": True, "v2": False}, st and (st["versions"], st["saved"], st["made"]))
    st1 = reel_page.state(katie, "v1")
    check("our reader, the other reel: its clip by a key, its song among the songs", st1["moments"][0]["key"] and st1["saved"]["song"] in [s["id"] for s in st1["songs"]]
          and [x["n"] for x in st1["claude"]] == [3, 2, 4] and st1["kind"] == "bts", (st1["moments"], st1["saved"]))

    # --- Hannah: a kit that already had a reel, a pick and a talking reel
    rec = read(hannah / ".kit" / "reel-page.json")
    was = json.loads(hannah_reel)
    check("a kit with a reel: hers is ADDED, under a free name; theirs is still the open one",
          reels.listed(rec, reel_page.REEL_FIRST) == [{"id": "v1", "name": "Reel 1"}, {"id": "v2", "name": "Reel 1 (older)"}]
          and reels.current(rec, reel_page.REEL_FIRST) == "v1", rec.get("versions"))
    check("...the reel that was there is exactly as it was", rec["saved"] == was["saved"] and rec["rev"] == was["rev"] + 1, rec["saved"])
    check("...the version before is kept, byte for byte (the record's own way)", (hannah / ".kit" / "reel-page.prev.json").read_bytes() == hannah_reel)
    check("...kit.json (its own reel pick) and the numbered list are byte for byte the same",
          (hannah / ".kit" / "kit.json").read_bytes() == hannah_kit_json and (hannah / ".kit" / "sheet.json").read_bytes() == hannah_sheet)
    v2 = reels.data_of(rec, "v2", reel_page.REEL_LIVE, reel_page.REEL_FIRST)
    check("a list with a gap and a retired number: older 4,3,1 are h5, h4, h1 (5, 4, 1 here)",
          names_of(hannah, v2["saved"]["picks"]) == ["h5.jpg", "h4.jpg", "h1.jpg"] and [x["n"] for x in v2["saved"]["picks"]] == [5, 4, 1]
          and names_of(hannah, v2["claude"]) == ["h4.jpg", "h5.jpg"] and v2["saved"]["song"] == "" and v2["saved"]["vibe"] == "build", v2)
    check("a made reel CapCut doesn't have is left out", not rec.get("made"), rec.get("made"))
    talk = read(hannah / ".kit" / "talking.json")
    was = json.loads(hannah_talk)
    check("a kit with a talking reel: hers is added, theirs is still open and as it was",
          reels.listed(talk, TR.TALK_FIRST) == [{"id": "v1", "name": "Talking reel 1"}, {"id": "v2", "name": "Talking reel 1 (older)"}]
          and reels.current(talk, TR.TALK_FIRST) == "v1" and talk["video"] == "mine.mov" and talk["words_of"] == was["words_of"]
          and (hannah / ".kit" / "talking.prev.json").read_bytes() == hannah_talk, talk)
    words = read(hannah / ".kit" / "talking-words.json")
    check("...their own script is exactly as it was; hers is kept beside it, tied to the video by OUR key",
          words["videos"]["mine.mov"] == hannah_words["videos"]["mine.mov"]
          and words["videos"]["talk.mov"]["key"] == TR._key_of(hannah / "Talking" / "talk.mov") and len(words["videos"]["talk.mov"]["words"]) == len(SAID), words["videos"].keys())
    t2 = TR.load(hannah, "v2")
    check("a word fixed on the older page: the script keeps what was heard, the fix is a fix",
          words["videos"]["talk.mov"]["words"][2]["w"] == "um" and "w0" not in words["videos"]["talk.mov"]["words"][2]
          and t2["fixes"] == {"2": "uh"} and t2["words"][2]["w"] == "uh" and t2["words"][2]["w0"] == "um", t2.get("fixes"))
    check("the edit through our checks: a cut past the last word is left out; the rest as it was",
          t2["cut"] == [[0, 2], [9, 9]] and t2["splits"] == [8] and t2["speeds"] == [{"a": 3, "b": 5, "v": 1.5}]
          and t2["zooms"] == [{"a": 10, "b": 12, "kind": "punch"}] and t2["captions"] is False and t2["cap_size"] == 1.4
          and t2["cap_pos"] == {"x": 0.5, "y": 0.8} and t2["photo_mode"] == "me" and t2["claude_cut"] == [[0, 2]], {k: t2.get(k) for k in ("cut", "splits", "speeds", "zooms")})
    check("a talking reel's photos by file name (older 3, 4 are h4, h5: 4, 5 here); behind reads full; a video stretch by name; a gone one left out",
          [(s["ns"], s["v"], s["spot"]) for s in t2["shots"]] == [([4, 5], None, "full"), ([], "walk.mov", "full")], t2["shots"])
    check("the script's mark belongs to its words (the next change will not start the edit afresh)",
          t2["words_of"] == words["videos"]["talk.mov"]["id"] and t2["status"] == "ready" and t2["brought_from"]["file"] == f"{HANNAH}.json", (t2.get("words_of"), t2.get("status")))
    check("a talking reel made in CapCut is left out when CapCut has no such project", not t2.get("made") and "\"Hannah talking reel\" as made" in out, t2.get("made"))
    r = subprocess.run([sys.executable, str(SCRIPTS / "talking_rec.py"), "show", HANNAH, "--reel", "Talking reel 1 (older)"],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    check("our reader (talking_rec.py show): the script, the fixed word, the cuts, and not \"exported again\"",
          r.returncode == 0 and "2:uh" in r.stdout and "Already cut" in r.stdout and "0-2" in r.stdout and "exported again" not in r.stdout, r.stdout[-700:] + r.stderr[-300:])
    check("our reader: where the video stands is \"here\"", TR.video_state(hannah, t2) == "here", TR.video_state(hannah, t2))
    stp = TR.state_for_page(hannah)
    check("our reader (state_for_page): the page still shows their own reel, with both listed", stp.get("ok") and stp["current"] == "v1"
          and [v["name"] for v in stp["versions"]] == ["Talking reel 1", "Talking reel 1 (older)"] and stp["rec"]["video"] == "mine.mov", {k: stp.get(k) for k in ("ok", "current", "versions")})

    # --- Pick: a kit whose own reel pick is another one
    rec = read(pick / ".kit" / "reel-page.json")
    check("a reel pick already in kit.json is never replaced; the older order comes over as their own, so the page shows it",
          read(pick / ".kit" / "kit.json")["picks"]["reel"] == [2] and "reel_earlier" not in read(pick / ".kit" / "kit.json")
          and rec["saved"]["mine"] is True and [x["n"] for x in rec["saved"]["picks"]] == [1, 2]
          and [x["n"] for x in reel_page.state(pick)["saved"]["picks"]] == [1, 2] and "that one is never replaced" in out, (read(pick / ".kit" / "kit.json"), rec["saved"]))

    check("a made reel's song is kept as a file's name, never a path from the older record", read(katie / ".kit" / "reel-page.json")["made"][0]["song"] == "song.mp3", read(katie / ".kit" / "reel-page.json").get("made"))

    # --- Aurora: only the reels that can be proven
    rec = read(aurora / ".kit" / "reel-page.json")
    v2 = reels.data_of(rec, "v2", reel_page.REEL_LIVE, reel_page.REEL_FIRST)
    check("an unprovable photo stops only that reel: \"Reel 2\" is in, \"Reel 1\" and \"Reel 3\" are not",
          [v["name"] for v in reels.listed(rec, reel_page.REEL_FIRST)] == ["Reel 1", "Reel 2"] and names_of(aurora, v2["saved"]["picks"]) == ["x2.jpg", "x1.jpg"]
          and set(rec["brought_from"]) == {"v2"}, rec)
    check("...and \"Reel 2\" keeps the id it had there (v2): a queued post \"...-reel-v2\" still means it; an empty reel holds v1's place",
          rec["brought_from"]["v2"]["id"] == "v2" and reels.current(rec, reel_page.REEL_FIRST) == "v2"
          and not reels.data_of(rec, "v1", reel_page.REEL_LIVE, reel_page.REEL_FIRST).get("saved", {}).get("picks")
          and "An empty reel called \"Reel 1\" stays" in sect(out, AURORA), (rec.get("versions"), rec.get("brought_from")))

    # --- after the review (Nov 18)
    check("a reel record here that is cut short: nothing written, the record and its good earlier version byte for byte as they were",
          (torn / ".kit" / "reel-page.json").read_bytes() == torn_rec and (torn / ".kit" / "reel-page.prev.json").read_bytes() == torn_prev
          and "can't be read right now" in sect(out, TORN) and not (torn / ".kit" / "brought-older.json").exists(), sect(out, TORN))
    if cant_read:
        check("a reel record here that can't be read at that moment: nothing written, no earlier version made, the record as it was",
              (locked / ".kit" / "reel-page.json").read_bytes() == locked_rec and not (locked / ".kit" / "reel-page.prev.json").exists()
              and "can't be read right now" in sect(out, LOCKED), sect(out, LOCKED))
    else:
        print("SKIP  a reel record that can't be read (this computer lets the file be read whatever its permissions)", flush=True)
    code2, out2 = run("bring", "--shoot", "Locked")
    rec = read(locked / ".kit" / "reel-page.json")
    check("...and once it can be read again the older reel goes beside it, the version before kept",
          code2 == 0 and [v["name"] for v in reels.listed(rec, reel_page.REEL_FIRST)] == ["Reel 1", "Reel 1 (older)"]
          and (locked / ".kit" / "reel-page.prev.json").read_bytes() == locked_rec and rec["saved"] == json.loads(locked_rec)["saved"], (code2, out2[-400:]))

    rec = read(queue / ".kit" / "reel-page.json")
    ids = {v["name"]: v["id"] for v in reels.listed(rec, reel_page.REEL_FIRST)}
    check("older ids are kept when free: \"White Backdrop\" is v2 here as there; \"Fun Maternity\" (v1 is theirs) gets an id past both",
          ids == {"Reel 1": "v1", "White Backdrop": "v2", "Fun Maternity": "v3"} and reels.current(rec, reel_page.REEL_FIRST) == "v1"
          and {k: v["id"] for k, v in rec["brought_from"].items()} == {"v2": "v2", "v3": "v1"}, (ids, rec.get("brought_from")))
    import posting_queue as PQ      # noqa: E402
    piece = [x for x in read(STUDIO / "posting.json")["pieces"] if x["id"].endswith("-reel-v2")][0]
    check("...so the post queued for \"...-reel-v2\" still shows White Backdrop's photos (p2, p3), and their own reel is as it was",
          names_of(queue, reel_page.order_for_kit_page(queue, reel=PQ.reel_version(piece))) == ["p2.jpg", "p3.jpg"]
          and [x["n"] for x in rec["saved"]["picks"]] == [3], reel_page.order_for_kit_page(queue, reel=PQ.reel_version(piece)))
    check("...and bring names the queued post to check", "Check: a post in the posting queue" in sect(out, QUEUE), sect(out, QUEUE))

    talk = read(two / ".kit" / "talking.json")
    t = TR.load(two)
    check("two older talking reels on one video: only the open one came, with ITS script and ITS cuts (nothing replaced)",
          [v["name"] for v in reels.listed(talk, TR.TALK_FIRST)] == ["Short one"] and t["cut"] == [[5, 11]] and t["words"][4]["w"] == "or"
          and not t.get("replaced") and "Talking reel \"Talking reel 1\": can't be brought" in sect(out, TWO), (talk.get("versions"), t.get("cut")))

    rec = read(undo / ".kit" / "reel-page.json")
    v1 = reels.data_of(rec, "v1", reel_page.REEL_LIVE, reel_page.REEL_FIRST)
    check("a record with only a clip they took out: it is kept (the clip can still be put back), the older reel beside it",
          v1.get("removed") == [GONE_CLIP] and v1.get("claude_earlier") == ["2,1"] and reels.current(rec, reel_page.REEL_FIRST) == "v1"
          and [v["name"] for v in reels.listed(rec, reel_page.REEL_FIRST)] == ["Reel 1", "Reel 1 (older)"], rec)

    rec = read(touched / ".kit" / "reel-page.json")
    check("a reel page that was only opened: the older reels are its reels, under their ids and names, the older open one open",
          reels.listed(rec, reel_page.REEL_FIRST) == [{"id": "v1", "name": "Fun Maternity"}, {"id": "v2", "name": "White Backdrop"}]
          and reels.current(rec, reel_page.REEL_FIRST) == "v2" and [x["n"] for x in rec["saved"]["picks"]] == [2]
          and (touched / ".kit" / "reel-page.prev.json").read_bytes() == touched_rec, rec)

    rec = read(abad / ".kit" / "reel-page.json") if (abad / ".kit" / "reel-page.json").exists() else {}
    check("an odd list inside an older record: the reel comes, the odd part does not", [x["n"] for x in rec.get("saved", {}).get("picks", [])] == [1]
          and not any(rec["saved"].get("sel", {}).values()) and "moments_found" not in rec, rec)
    check("an older record that can't be parsed: nothing for that shoot", not (deep / ".kit" / "reel-page.json").exists())

    rec = read(behind / ".kit" / "reel-page.json") if (behind / ".kit" / "reel-page.json").exists() else {"saved": {"picks": []}}
    check("a photo with no number yet: the list is made first (it is 3), then the reel comes by file name (p3, p1)",
          names_of(behind, rec["saved"]["picks"]) == ["p3.jpg", "p1.jpg"] and names_of(behind, [3]) == ["p3.jpg"], rec.get("saved"))

    rec = read(stale / ".kit" / "reel-page.json")
    check("\"Let the Assistant choose\" with another order showing: the post kit shows the order the older page showed (1 Longer, 2, 4), the pick kept too",
          reel_page.order_for_kit_page(stale) == order("1+,2,4") and rec["saved"]["mine"] is True and read(stale / ".kit" / "kit.json")["picks"]["reel"] == [1, 2, 3],
          (reel_page.order_for_kit_page(stale), rec["saved"]))

    check("a video that is already a talking reel's here: nothing of that kit changed", not changed(samevid_before, tree(samevid / ".kit")), changed(samevid_before, tree(samevid / ".kit")))
    check("talking reels short of something: none brought", not (talks / ".kit" / "talking.json").exists() and not (talks / ".kit" / "talking-words.json").exists())
    check("a reel with too many photos: not brought", not (many / ".kit" / "reel-page.json").exists())
    check("name order nobody confirmed, and a retired number: nothing brought", not (late / ".kit" / "reel-page.json").exists() and not (retired / ".kit" / "reel-page.json").exists())
    check("a talking video saved again: nothing was brought for it", not (aurora / ".kit" / "talking.json").exists() and not (aurora / ".kit" / "talking-words.json").exists())
    check("no older list and nobody asked: nothing was brought", not (nolist / ".kit" / "reel-page.json").exists())

    # ================= twice =================
    before = tree(TMP)
    code, out = run("bring")
    after = tree(TMP)
    left = [k for k in changed(before, after) if not k.endswith("brought-older.json")]
    check("a second bring writes nothing (no record, no list, no kit.json; no note either, with nothing to do)",
          not changed(before, after) and out.count("already brought") >= 6, (changed(before, after), left, out[-500:]))
    code, out = run("bring", "--shoot", "Katie")
    check("...and with nothing left to bring for a shoot it says so (exit 0)", code == 0 and "Done: 0 brought." in out, (code, out[-300:]))

    # ================= a video that already has a script here =================
    write(OLD / "talking" / f"{AURORA}.json", dict(read(OLD / "talking" / f"{AURORA}.json"), transcribed=time.time() + 60))
    TR.put_words(aurora, "again.mov", TR._key_of(aurora / "Talking" / "again.mov"), [{"w": "ours", "start": 0, "end": 1, "conf": 1}])
    mine = tree(aurora / ".kit")
    code, out = run("bring", "--shoot", "Aurora")
    check("a video that already has a script here is never written over", "already has a script here" in out and not changed(mine, tree(aurora / ".kit")), (out[-500:], changed(mine, tree(aurora / ".kit"))))
    OLD_BEFORE[f"talking/{AURORA}.json".replace("/", os.sep)] = tree(OLD)[f"talking/{AURORA}.json".replace("/", os.sep)]      # the test's own edit

    # ================= --photos-unchanged, for real =================
    code, out = run("bring", "--shoot", "Nolist", "--photos-unchanged")
    check("--photos-unchanged without their yes to the names: nothing brought", code == 1 and not (nolist / ".kit" / "reel-page.json").exists(), (code, out))
    code, out = run("bring", "--shoot", "Nolist", "--photos-unchanged", "--names-confirmed")
    rec = read(nolist / ".kit" / "reel-page.json")
    check("--photos-unchanged --names-confirmed: brought by name order, capitals first (older 1, 2 are Z9, a1)", code == 0 and names_of(nolist, rec["saved"]["picks"]) == ["Z9.jpg", "a1.jpg"]
          and rec["saved"]["vibe"] == "mixed", (code, rec["saved"]))

    # ================= the older records =================
    check("the older records are unchanged, byte for byte, and nothing was added beside them", not changed(OLD_BEFORE, tree(OLD)), changed(OLD_BEFORE, tree(OLD)))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
sys.exit(1 if FAILED else 0)
