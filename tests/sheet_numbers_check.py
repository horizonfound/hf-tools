#!/usr/bin/env python3
"""Photo numbers stay fixed when photos are added (Nicole's v27, Nov 14: "+ Add photos"; her prepare() and
photo_times()). The numbered list is made in ONE place, reel.py sheet; kit.py sheet hands it the list from last
time (the kit's .kit/sheet.json), and then:
  - every photo on that list keeps its number;
  - a new photo takes the next number after the highest ever given (new photos in name order);
  - a photo that is gone keeps its number unused, so no number ever means another photo (hers numbered the
    kept photos again from 1, so a photo gone shifted every one after it: fixed, not copied);
  - a first list, with nothing before, numbers by name from 1, as always;
  - whoever asked can learn what changed: the list's "added" and "gone" (numbers only) and two plain lines.
Every picker, designer and reel reads that list by number (arrange.sheet_rows, reel.kit_numbers), so picks,
reels and designs never point at the wrong photo after "+ Add photos".

    python3 tests/sheet_numbers_check.py
    /usr/bin/python3 tests/sheet_numbers_check.py        (Apple's own Python: no Pillow)

A scratch STUDIO_HOME and a pretend kit of tiny PNGs drawn here; nothing outside the scratch folder is touched,
no window is opened. Plain Python: the same on a Mac and a PC. Every line says PASS or FAIL; exit 1 only when
something FAILED.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
R = ROOT / "plugins" / "the-engine" / "skills" / "assistant-make-a-reel" / "scripts"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RESULTS = {"PASS": 0, "FAIL": 0}


def check(name, ok, detail=""):
    RESULTS["PASS" if ok else "FAIL"] += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else "\n      " + str(detail)[:600]), flush=True)


def png(path, w, h, shade):
    """A tiny grey PNG, drawn in plain Python (reel.py reads a PNG's size from its header)."""
    raw = b"".join(b"\x00" + bytes([shade]) * w for _ in range(h))

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def run(env, script, *args):
    r = subprocess.run([sys.executable, str(script)] + [str(a) for a in args], capture_output=True,
                       encoding="utf-8", errors="replace", env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def rows_of(kit):
    d = json.loads((kit / ".kit" / "sheet.json").read_text(encoding="utf-8"))
    return d, {Path(x["file"]).name: x["n"] for x in d["photos"]}, [x["n"] for x in d["photos"]]


def main():
    work = Path(tempfile.mkdtemp(prefix="sheet-numbers-"))
    try:
        return _main(work)
    finally:
        if RESULTS["FAIL"]:
            print("(the scratch folder is kept: %s)" % work)
        else:
            shutil.rmtree(work, ignore_errors=True)


def _main(work):
    studio, home = work / "studio", work / "The Assistant"
    studio.mkdir()
    env = dict(os.environ, STUDIO_HOME=str(studio), HOME=str(work / "home"), USERPROFILE=str(work / "home"),
               STUDIO_NO_WINDOWS_FOR_TESTS="1", PYTHONIOENCODING="utf-8")
    (work / "home").mkdir()
    code, out = run(env, S / "posts.py", "setup", "--home", home)
    check("a scratch Assistant folder (posts.py setup)", code == 0, out[-300:])
    kit = home / "Your Content" / "2026-11-02 Numbers"
    (kit / ".kit").mkdir(parents=True)
    (kit / "Photos").mkdir()
    names = ["IMG_0%d.png" % k for k in (10, 20, 30, 40, 50, 60)]       # six photos, in name order
    for k, nm in enumerate(names):
        png(kit / "Photos" / nm, 30 + k, 40, 90 + 10 * k)                 # all tall
    (kit / ".kit" / "kit.json").write_text(json.dumps({"name": "Numbers", "date": "2026-11-02", "folder": kit.name,
                                                        "source": "drop", "photos": names}), encoding="utf-8")

    print("-- the first list: by name from 1, as always")
    code, out = run(env, S / "kit.py", "sheet", kit)
    check("kit.py sheet, the first time: it runs", code == 0, out[-400:])
    d, by, ns = rows_of(kit)
    check("six photos numbered 1 to 6 by name", ns == [1, 2, 3, 4, 5, 6] and [by[n] for n in names] == [1, 2, 3, 4, 5, 6], str(by))
    check("a first list says nothing of added or gone (there was no list before)", "added" not in d and "gone" not in d, str(list(d)))
    check("... and the chat is not told of a change", "since the last list" not in out and "same photos" not in out, out[-300:])
    rec = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))
    check("the kit record's count is 6", rec.get("numbered") == 6, str(rec.get("numbered")))

    print("\n-- photos added: every photo keeps its number, the new ones take the next, in name order")
    png(kit / "Photos" / "AAA_first_by_name.png", 50, 30, 10)      # would sort FIRST by name
    png(kit / "Photos" / "ZZZ_last_by_name.png", 30, 50, 200)
    sys.path.insert(0, str(S))
    sys.path.insert(0, str(R))
    import arrange
    stamp0 = arrange.sheet_stamp(kit)
    code, out = run(env, S / "kit.py", "sheet", kit)
    check("kit.py sheet again, two photos added: it runs", code == 0, out[-400:])
    d, by, ns = rows_of(kit)
    check("the six keep 1 to 6 (the one that sorts first by name did NOT push them along)", [by[n] for n in names] == [1, 2, 3, 4, 5, 6], str(by))
    check("the new ones are 7 and 8, in name order, at the end", by.get("AAA_first_by_name.png") == 7 and by.get("ZZZ_last_by_name.png") == 8 and ns == list(range(1, 9)), str(by))
    check("the list says what was added: \"added\" [7, 8] and \"gone\" []", d.get("added") == [7, 8] and d.get("gone") == [], str({k: d.get(k) for k in ("added", "gone")}))
    check("the chat is told: \"New since the last list: 2 photos, numbered 7 to 8. Every other photo keeps its number.\"",
          "New since the last list: 2 photos, numbered 7 to 8. Every other photo keeps its number." in out, out[-400:])
    check("the stamp a page watches changed (so an open page learns there is more)", arrange.sheet_stamp(kit) != stamp0 and arrange.sheet_stamp(kit))
    rec = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))
    check("the kit record's count is 8", rec.get("numbered") == 8, str(rec.get("numbered")))
    check("a wide new photo is listed wide, a tall one tall (the sizes are read as ever)",
          next(x for x in d["photos"] if x["n"] == 7)["way"] == "wide" and next(x for x in d["photos"] if x["n"] == 8)["way"] == "tall", str(d["photos"][-2:]))

    print("\n-- a photo gone keeps its number unused; the next photo in never takes it")
    (kit / "Photos" / names[2]).unlink()                           # photo 3 is taken out of the folder (the test's scratch copy)
    code, out = run(env, S / "kit.py", "sheet", kit)
    check("kit.py sheet with a photo gone: it runs", code == 0, out[-400:])
    d, by, ns = rows_of(kit)
    check("3 is not on the list and every other number is what it was", ns == [1, 2, 4, 5, 6, 7, 8] and by[names[3]] == 4 and by["ZZZ_last_by_name.png"] == 8, str(by))
    check("the list says \"gone\" [3] and \"added\" []", d.get("gone") == [3] and d.get("added") == [], str({k: d.get(k) for k in ("added", "gone")}))
    check("the chat is told: \"Gone since the last list: 1 photo (number 3); that number stays unused.\"",
          "Gone since the last list: 1 photo (number 3); that number stays unused." in out, out[-400:])
    rec = json.loads((kit / ".kit" / "kit.json").read_text(encoding="utf-8"))
    check("the kit record's count is 7 (a count, not the highest number)", rec.get("numbered") == 7, str(rec.get("numbered")))
    png(kit / "Photos" / "IMG_0035.png", 30, 40, 55)
    code, out = run(env, S / "kit.py", "sheet", kit)
    d, by, ns = rows_of(kit)
    check("another photo in after that: it is 9, never 3 (a number is never reused)", code == 0 and by.get("IMG_0035.png") == 9 and 3 not in ns and d.get("added") == [9], str(by))
    import reel
    check("reel.kit_numbers (what a chat reel's numbers mean) reads the kept numbers, gap and all",
          sorted(x["n"] for x in reel.kit_numbers(str(kit), str(kit / "Photos"))) == [1, 2, 4, 5, 6, 7, 8, 9])
    check("arrange.sheet_rows (what every page reads) has the same numbers", [x["n"] for x in arrange.sheet_rows(kit)] == [1, 2, 4, 5, 6, 7, 8, 9])
    code, out = run(env, S / "kit.py", "picks", kit, "--carousel", "1,3,9")
    check("kit.py picks with the gone number 3: refused in plain words, nothing saved", code != 0 and "no photo numbered 3 on the sheet" in out, out[-300:])
    code, out = run(env, S / "kit.py", "picks", kit, "--carousel", "1,9,4")
    check("kit.py picks with 1, 9 and 4: accepted", code == 0, out[-300:])

    print("\n-- the same photos again, a re-exported photo, and nothing changed")
    png(kit / "Photos" / names[3], 60, 40, 120)                     # photo 4 exported again, now wide
    code, out = run(env, S / "kit.py", "sheet", kit)
    d, by, ns = rows_of(kit)
    four = next(x for x in d["photos"] if x["n"] == 4)
    check("a photo exported again under the same name keeps its number and shows its new size",
          code == 0 and by[names[3]] == 4 and four["way"] == "wide" and four["w"] == 60, str(four))
    check("the chat is told the list is the same: \"The same photos as the last list, with the same numbers.\"",
          "The same photos as the last list, with the same numbers." in out and d.get("added") == [] and d.get("gone") == [], out[-300:])
    code, out = run(env, S / "kit.py", "sheet", kit)
    _, _, ns2 = rows_of(kit)
    check("kit.py sheet twice with nothing changed: the same list", code == 0 and ns2 == ns, str(ns2))

    print("\n-- an older kit's list, with gaps and in any order, is read and kept as it is")
    old = {"folder": str(kit / "Photos"), "photos": [{"n": 40, "file": str(kit / "Photos" / names[0]), "w": 1, "h": 2, "way": "tall"},
                                                      {"n": 12, "file": str(kit / "Photos" / names[1]), "w": 1, "h": 2, "way": "tall"},
                                                      {"n": 12, "file": str(kit / "Photos" / names[4]), "w": 1, "h": 2, "way": "tall"}]}
    (kit / ".kit" / "sheet.json").write_text(json.dumps(old), encoding="utf-8")
    code, out = run(env, S / "kit.py", "sheet", kit)
    d, by, ns = rows_of(kit)
    check("photos on it keep 40 and 12; the number two rows shared stays with the first of them; the rest are new from 41",
          code == 0 and by[names[0]] == 40 and by[names[1]] == 12 and ns == sorted(ns) and min(n for n in ns if n not in (12, 40)) == 41
          and by[names[4]] >= 41, str(by))
    check("... and the new ones are counted as added, in name order", d.get("added") == list(range(41, 41 + 6)) and d.get("gone") == [], str(d.get("added")))

    print("\n-- reel.py sheet by itself (a chat reel with no kit): the old way, unless a list before is handed to it")
    folder = kit / "Photos"
    code, out = run(env, R / "reel.py", "sheet", "--folder", folder, "--shoot", "Loose")
    lst = json.loads(Path(out.split("List: ", 1)[1].strip().splitlines()[0]).read_text(encoding="utf-8"))
    check("reel.py sheet with no --before: numbered by name from 1, and no \"added\" key", code == 0 and [x["n"] for x in lst["photos"]] == list(range(1, 9)) and "added" not in lst, out[-300:])
    bad = work / "not-a-list.json"
    bad.write_text("{", encoding="utf-8")
    code, out = run(env, R / "reel.py", "sheet", "--folder", folder, "--shoot", "Loose", "--before", bad)
    lst = json.loads(Path(out.split("List: ", 1)[1].strip().splitlines()[0]).read_text(encoding="utf-8"))
    check("reel.py sheet --before a file that can't be read: a first list by name, no stop", code == 0 and [x["n"] for x in lst["photos"]] == list(range(1, 9)), out[-300:])
    code, out = run(env, R / "reel.py", "sheet", "--folder", folder, "--shoot", "Loose", "--before", work / "missing.json")
    check("reel.py sheet --before a file that isn't there: the same", code == 0, out[-300:])
    sheets = [ln for ln in out.splitlines() if ln.startswith("Sheet: ")]
    check("the contact sheet is still drawn (or said to be missing in plain words), the list first",
          bool(sheets) or "could not draw the sheet" in out, out[-300:])
    check("no window was opened and nothing outside the scratch folder was written (the real home is never used)",
          not (Path.home() / ".studio" / "reels" / "loose").exists() or str(Path.home()).startswith(str(work)))

    print("\n%d passed, %d failed." % (RESULTS["PASS"], RESULTS["FAIL"]))
    return 1 if RESULTS["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
