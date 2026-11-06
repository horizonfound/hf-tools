#!/usr/bin/env python3
"""The reel's sound, tried on the test songs in this folder: their lengths, hearing them, finding the beat,
and pulling the sound out of a file. Standard library only; runs the same on a Mac and on Windows.

    python3 tests/fixtures/check_sound.py

Every song here is a synthetic click track: 100 beats a minute, 4 to a bar, 10 seconds, first beat at
0.25 s (make_fixtures.py). So the right answers are known.

On a Mac it tries the Mac's own route (afconvert) and the plain-Python route. On Windows it tries the
plain-Python route and Windows' own Media Foundation, with ffmpeg switched off so that Media Foundation
really runs. A Windows machine without Media Foundation (some server and "N" editions) says SKIP for those
lines, not FAIL. Exit 0 when nothing failed.
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"))
import sound  # noqa: E402
import beats_lite  # noqa: E402

WINDOWS = os.name == "nt"
LENGTHS = {   # the true lengths, in seconds (afinfo gets two wrong: 0.34 for the M4A named .mp3, 11.7 for the
              # variable-rate MP3 with no header; ffmpeg gives 10.000 for the two MP3s with a header)
    "click-100bpm.wav": 10.0, "click-100bpm.aiff": 10.0, "click-100bpm.m4a": 10.0,
    "click-100bpm-m4a-named.mp3": 10.0, "click-100bpm-cbr.mp3": 10.03102, "click-100bpm-vbr.mp3": 10.03102,
    "click-100bpm-cbr-noheader.mp3": 10.031, "click-100bpm-vbr-noheader.mp3": 10.03102}
KINDS = {"click-100bpm.wav": ".wav", "click-100bpm.aiff": ".aiff", "click-100bpm.m4a": ".m4a",
         "click-100bpm-m4a-named.mp3": ".m4a"}
results = []


def check(what, ok, detail=""):
    results.append(ok is not False)
    word = "PASS" if ok is True else ("SKIP" if ok is None else "FAIL")
    print(f"{word}  {what}" + (f"   [{detail}]" if detail else ""), flush=True)


def beats_of(path, env):
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return beats_lite.analyze(str(path))
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    print(f"Python {sys.version.split()[0]} on {'Windows' if WINDOWS else sys.platform}")
    for name, want in LENGTHS.items():
        got = sound.duration(HERE / name)
        check(f"length of {name}", got is not None and abs(got - want) < 0.001, f"{got} s, want {want}")
        kind = KINDS.get(name, ".mp3")
        check(f"{name} is really {kind}", sound.real_kind(HERE / name) == kind, str(sound.real_kind(HERE / name)))

    plain = {"ASSISTANT_NO_AFCONVERT": "1", "ASSISTANT_NO_FFMPEG": "1"}
    truth = None
    for name in ("click-100bpm.wav", "click-100bpm.aiff"):
        r = beats_of(HERE / name, plain)
        ok = r["ok"] and abs(r["tempo"] - 99.4) < 1.5 and len(r["beats"]) == 17 and r.get("meter") == 4
        check(f"the beat of {name}, read in plain Python", ok, f"{r.get('how')}: {r.get('tempo')} bpm, "
              f"{len(r.get('beats', []))} beats, {r.get('meter')} to a bar, {r.get('reason', '')}")
        if ok and truth is None:
            truth = r["beats"]

    routes = []
    if sys.platform == "darwin":
        routes.append(("the Mac's own route", {}))
    if WINDOWS:
        routes.append(("Windows' own Media Foundation", plain))
    for label, env in routes:
        for name in ("click-100bpm.m4a", "click-100bpm-m4a-named.mp3", "click-100bpm-cbr.mp3", "click-100bpm-vbr.mp3"):
            r = beats_of(HERE / name, env)
            if not r["ok"] and "missing Windows' own media parts" in (r.get("reason") or ""):
                check(f"the beat of {name}, {label}", None, "this machine has no Media Foundation")
                continue
            off = (max(abs(a - b) for a, b in zip(r["beats"], truth)) * 1000
                   if r["ok"] and truth and len(r["beats"]) == len(truth) else None)
            # an MP3 decoder may keep or trim the encoder's few milliseconds at the start; 30 ms covers both
            ok = r["ok"] and abs(r["tempo"] - 99.4) < 1.5 and off is not None and off <= (30 if name.endswith("mp3") else 15)
            check(f"the beat of {name}, {label}", ok, f"{r.get('how')}: {r.get('tempo')} bpm, "
                  f"{len(r.get('beats', []))} beats, furthest from the WAV's {off if off is None else round(off)} ms "
                  f"{r.get('reason', '')}")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "pulled sound.m4a"
        env = plain if WINDOWS else {}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            got, how = sound.extract_audio(HERE / "click-100bpm.m4a", out)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        if not got and "missing Windows' own media parts" in how:
            check("pulling the sound out of a file", None, "this machine has no Media Foundation")
        else:
            length = sound.duration(got) if got else None
            check("pulling the sound out of a file", bool(got) and length is not None and abs(length - 10.0) < 0.1,
                  f"{how}: {got.name if got else ''} {length}")
        check("the file it was pulled from is unchanged", sound.duration(HERE / "click-100bpm.m4a") == 10.0)
        again, why = sound.extract_audio(HERE / "click-100bpm.m4a", got) if got else (None, "")
        check("it never writes over a file that is there", again is None and got is not None and got.exists(), why)

    print(f"\n{sum(results)} of {len(results)} passed or skipped." + ("" if all(results) else "  FAILED: see above."))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
