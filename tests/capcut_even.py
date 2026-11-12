#!/usr/bin/env python3
"""For the CapCut tests: a CapCut project "with its ids evened out", and the photo-reel plans whose projects were
kept from before the talking reel's builder went into capcut.py (Nicole's v24, stage D).

    python3 tests/capcut_even.py            compare: build the plans with capcut.py as it is now, against the kept file
    python3 tests/capcut_even.py --keep     (only ever run on capcut.py from BEFORE a change to build()) write the kept file

Every id CapCut's files carry is made fresh on every build, and a few fields hold the clock. evened() gives each
id a number by where it first appears in the project and blanks the clock fields, so two builds of the same plan
come out the same text if, and only if, the builder wrote the same project. The kept file
(tests/fixtures/capcut-photo-reels-before-v24.json) was written on Nov 12, 2026 from commit 473f17d, the last one
before `build()` had its shared helpers lifted out: today's reels must still be that, byte for byte.

Nothing here touches a file: the plans name pretend paths, with every size and length given, so build() opens none.
A Mac's project only (on a PC build() adds this computer's name and CapCut's own font file, so there it is a SKIP).
"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REEL = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"
KEPT = ROOT / "tests" / "fixtures" / "capcut-photo-reels-before-v24.json"
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
CLOCK = ("update_time", "create_time", "import_time", "import_time_ms", "tm_draft_create", "tm_draft_modified")


def evened(obj):
    """The project with every id numbered by first appearance and every clock field blanked."""
    seen = {}

    def walk(x, key=None):
        if isinstance(x, dict):
            return {k: walk(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v, key) for v in x]
        if isinstance(x, str) and UUID.match(x):
            return seen.setdefault(x.lower(), f"id-{len(seen) + 1}")
        if key in CLOCK and isinstance(x, (int, float)) and not isinstance(x, bool):
            return 0
        return x
    return walk(copy.deepcopy(obj))


def plans():
    """Photo reels of every kind build() writes: on the frame grid with a song, a hook and a clip; on plain seconds
    with no song; a song from CapCut's own music with its beats; a fitted (not filled) photo and a given scale."""
    ph = [{"path": "/pretend/Photos/a.jpg", "w": 4000, "h": 6000}, {"path": "/pretend/Photos/b wide.jpg", "w": 6000, "h": 4000},
          {"path": "/pretend/Photos/c.png", "w": 1080, "h": 1920}]
    grid = []
    f = 0
    for k, p in enumerate(ph + [{"path": "/pretend/Footage/clip.mov", "w": 1080, "h": 1920, "clip": True, "src": 2.5, "length": 9.25}]):
        n = (24, 12, 30, 45)[k]
        grid.append(dict(p, start=f / 30, dur=n / 30, start_f=f, dur_f=n))
        f += n
    song = {"path": "/pretend/Music/song.m4a", "from": 41.3, "from_f": 1239, "fade_out": 0.5, "length": 180.0, "name": "song.m4a",
            "capcut_material": None, "capcut_beats": None}
    secs = [dict(ph[0], start=0.0, dur=1.5), dict(ph[1], start=1.5, dur=0.75, fill=False), dict(ph[2], start=2.25, dur=2.0, scale=1.3)]
    cc_mat = {"id": "11111111-2222-3333-4444-555555555555", "type": "music", "music_id": "7000000000000000001", "name": "Glow",
              "path": "/pretend/cache/glow.mp3", "duration": 150000000}
    cc_beats = {"id": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "type": "beats", "ai_beats": {"beats_path": "/pretend/cache/glow.json"}}
    return {
        "grid, song, hook, clip": {"name": "Beach reel", "photos": grid, "song": song,
                                   "hook": {"text": "The Garcias, a windy morning", "dur": 0.8, "dur_f": 24}},
        "seconds, no song": {"name": "Quiet reel", "photos": secs, "song": None, "hook": None},
        "seconds, hook, short song": {"name": "Short song reel", "photos": secs,
                                      "song": dict(song, length=44.0, from_f=None, fade_out=0), "hook": {"text": "Hi", "dur": 9.0}},
        "CapCut's own song": {"name": "Glow reel", "photos": grid[:3],
                              "song": dict(song, path="/pretend/cache/glow.mp3", name="Glow", capcut_material=cc_mat, capcut_beats=cc_beats),
                              "hook": None},
    }


def built():
    sys.path.insert(0, str(REEL))
    import capcut
    parts = capcut.load_parts()
    plat = {"platform": {"app_version": "9.6.0", "os": "mac"}, "version": 360000}
    out = {}
    for name, plan in plans().items():
        for label, p in (("", None), (" (their CapCut's version copied)", plat)):
            d, m = capcut.build(copy.deepcopy(plan), parts, p)
            out[name + label] = evened({"draft": d, "meta": m})
    return out


def text(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=False, indent=0)


def mark(obj):
    """A project's whole evened text as one short mark (the kept file holds these, not 250 KB of projects)."""
    return hashlib.sha256(text(obj).encode("utf-8")).hexdigest()


def compare():
    """(the names that differ from the kept ones, how many were compared)."""
    kept = json.loads(KEPT.read_text(encoding="utf-8"))["projects"]
    now = {k: mark(v) for k, v in built().items()}
    return sorted(k for k in set(kept) | set(now) if kept.get(k) != now.get(k)), len(kept)


def main():
    if "--keep" in sys.argv:
        got = {k: mark(v) for k, v in built().items()}
        KEPT.write_text(json.dumps({"about": "sha256 of each photo reel's CapCut project with its ids evened out "
                                    "(tests/capcut_even.py), as capcut.py at commit 473f17d built it",
                                    "projects": got}, indent=1) + "\n", encoding="utf-8")
        print(f"kept {len(got)} projects in {KEPT.name}")
        return 0
    bad, n = compare()
    print(f"the same ({n} projects)" if not bad else f"DIFFERENT: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
