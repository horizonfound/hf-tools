#!/usr/bin/env python3
"""Where a night's photos and records are, before and after it settles.

During the night everything lives in one folder on their drive:
    <their place>/2026-10-24 saturday card/<shoot folders>   and  .../_studio/  (the records)

When the night settles (settle.py), the shoot folders move up into <their place>
and the records move to a hidden folder there, so the day folder disappears:
    <their place>/<shoot folders>
    <their place>/.studio/2026-10-24 saturday card/          (the records)

Every path the records hold (index, groups, shoots, logs) is relative to the
folder the shoots sit in, and that is the same before and after: the shoots
are one level up, and so is the root. So every script asks locate() for
(root, studio) and works the same either way.

    root, studio = locate("<the night's folder, its records folder, or the old day folder>")
"""
import json
import os
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

RECORDS = ".studio"  # the hidden folder in their place that keeps every settled night's records


def place_key(path):
    """A folder path as text, spelled one way, for comparing two paths that were written down at different
    times. On a PC "e:\\photos" and "E:\\Photos" are the same folder (Windows ignores capital letters and takes
    either slash), so the text is evened out there. On a Mac the text is kept exactly as it is, as before."""
    s = str(path)
    if this_computer.WINDOWS:   # unproven on a real PC
        return os.path.normcase(os.path.normpath(s))
    return s


def same_place(a, b):
    """True when two recorded paths name the same folder (see place_key). None or "" never matches."""
    if not a or not b:
        return False
    return place_key(a) == place_key(b)


def locate(arg):
    """(root, studio): the folder the photo paths are relative to, and the records folder."""
    p = Path(arg).expanduser()
    try:
        p = p.resolve()
    except OSError:
        pass
    # a night that has not settled: <day folder>/_studio
    if (p / "_studio" / "manifest.json").exists():
        return p, p / "_studio"
    # a records folder itself: <day folder>/_studio, or <their place>/.studio/<night>
    if (p / "manifest.json").exists():
        if p.name == "_studio":
            return p.parent, p
        if p.parent.name == RECORDS:
            return p.parent.parent, p
        return p.parent, p
    # the old day folder of a night that has settled: its records are in <their place>/.studio/
    recs = p.parent / RECORDS
    if (recs / p.name / "manifest.json").exists():
        return p.parent, recs / p.name
    if recs.is_dir():  # settled under a different name (two nights with the same day name)
        for r in sorted(recs.iterdir()):
            for marker in ("settled.json", "settle-log.json"):
                f = r / marker
                if f.exists():
                    try:
                        if same_place(json.loads(f.read_text(encoding="utf-8")).get("session_was"), p):
                            return p.parent, r
                    except (ValueError, OSError):
                        pass
    raise SystemExit(f"STOP: no Studio records found for {p}")


def settled(studio):
    return (Path(studio) / "settled.json").exists()
