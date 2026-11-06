#!/usr/bin/env python3
"""The backup's promises, run for real on pretend cards: never write over a file, never mix two cards, carry on
a backup that was cut off, and never copy a card onto itself. Runs the same on a Mac and on Windows (GitHub runs
it on a real Windows machine: .github/workflows/check-pc.yml).

    python3 tests/backup_safety.py        needs Pillow, only to draw the pretend photos

In scratch folders it makes itself (never the real ~/.studio, never a real drive). The pretend photos are drawn
here: 13 small JPEGs with camera dates, each a different size. Prints PASS or FAIL per check; exit 0 when all pass.
From the Nov 6 review of the PC build (it was scratchpad/wf/servers-fix/fix_test.py).

What it tries:
  1. a different file already where the backup would put a photo: never written over, run after run; a checked
     copy changed since (edited in place): never written over; the backup's own failed copy: copied again.
  2. two different cards with the same name on the same day: the second is refused, the first untouched; the same
     card with photos added after a finished backup, or taken off it: asked for a name of its own; a backup cut off
     part way: the same command copies the rest.
  3. the backup onto the card itself, into a folder on it, or a second copy onto it: refused, and nothing at all
     written on the card; the drive rule itself, with what a PC would see.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
PY = sys.executable
fails = []
ran = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + (f"   [{detail}]" if detail and not ok else ""), flush=True)
    ran.append(what)
    if not ok:
        fails.append(what)


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def tree(p):
    return sorted(x.relative_to(p).as_posix() for x in Path(p).rglob("*"))


def draw_photos(folder):
    """IMG_4471.JPG to IMG_4483.JPG: small JPEGs with a camera date each (45 seconds apart), every one a different
    size, so no two are alike byte for byte."""
    from PIL import Image
    folder.mkdir(parents=True)
    t0 = datetime(2026, 6, 4, 9, 0, 0)
    for i in range(13):
        im = Image.new("RGB", (480 + i * 16, 320 + i * 8), (30 + i * 15, 110 + (i * 7) % 90, 210 - i * 12))
        for x in range(0, im.width, 40):
            im.paste((20, 20, 20), (x, 0, x + 4 + i, im.height // 3))
        ex = Image.Exif()
        ex[0x010F], ex[0x0110] = "Canon", "Canon EOS R5"
        ex.get_ifd(0x8769)[0x9003] = (t0 + timedelta(seconds=i * 45)).strftime("%Y:%m:%d %H:%M:%S")
        im.save(folder / f"IMG_{4471 + i}.JPG", quality=80, exif=ex)


def main():
    T = Path(tempfile.mkdtemp(prefix="assistant backup safety "))
    C = T / "photos"
    draw_photos(C)
    env = dict(os.environ, STUDIO_HOME=str(T / "home"))
    (T / "home").mkdir()

    def card(name, pairs):
        d = T / name / "DCIM" / "100CANON"
        d.mkdir(parents=True)
        for src, dst in pairs:
            shutil.copy2(C / src, d / dst)
        return T / name

    def run(*a):
        r = subprocess.run([PY, *map(str, a)], capture_output=True, encoding="utf-8", errors="replace", env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    print(f"Python {sys.version.split()[0]} on {'a PC' if os.name == 'nt' else sys.platform}; scratch: {T}\n")
    A3 = [("IMG_4471.JPG", "IMG_4471.JPG"), ("IMG_4472.JPG", "IMG_4472.JPG"), ("IMG_4473.JPG", "IMG_4473.JPG")]
    B3 = [("IMG_4474.JPG", "IMG_4471.JPG"), ("IMG_4475.JPG", "IMG_4472.JPG"), ("IMG_4476.JPG", "IMG_4473.JPG")]

    # ---- 1. a different file already at the destination, the same command twice (and three times)
    cardA = card("cardA", A3)
    drive1 = T / "drive1"
    there = drive1 / "2026-11-07 t1" / "DCIM" / "100CANON" / "IMG_4471.JPG"
    there.parent.mkdir(parents=True)
    shutil.copy2(C / "IMG_4480.JPG", there)
    before = h(there)
    cmd = [S / "backup.py", "--source", cardA, "--dest", drive1, "--name", "t1", "--date", "2026-11-07"]
    c1, o1 = run(*cmd)
    c2, o2 = run(*cmd)
    c3, o3 = run(*cmd)
    check("1a first run stops on the file that was there (exit 1, 'Not overwritten')", c1 == 1 and "Not overwritten" in o1, f"{c1} {o1[-300:]}")
    check("1b second run: still exit 1, still 'Not overwritten'", c2 == 1 and "Not overwritten" in o2, f"{c2} {o2[-300:]}")
    check("1c third run: the same", c3 == 1 and "Not overwritten" in o3, f"{c3}")
    check("1d the file that was there is unchanged after three runs", h(there) == before, f"{before} -> {h(there)}")
    check("1e the report never says all safe", "safely backed up and verified" not in (o2 + o3))
    rep = (drive1 / "2026-11-07 t1" / "_studio" / "morning-report.md").read_text(encoding="utf-8")
    check("1f the problem is at the top of the report after the third run", "Needs you first" in rep and "IMG_4471" in rep)

    # ---- 1g. a file the backup copied and checked, changed at the destination since (a photo edited in place)
    cardG = card("cardG", A3)
    drive_g = T / "driveG"
    drive_g.mkdir()
    cmd = [S / "backup.py", "--source", cardG, "--dest", drive_g, "--name", "tg", "--date", "2026-11-07"]
    c, o = run(*cmd)
    check("1g first run copies all three (exit 0)", c == 0, f"{c} {o[-300:]}")
    edited = drive_g / "2026-11-07 tg" / "DCIM" / "100CANON" / "IMG_4472.JPG"
    edited.write_bytes(edited.read_bytes() + b"edited in place")
    e_before = h(edited)
    c, o = run(*cmd)
    check("1h a checked copy that changed since is not written over (exit 1, 'Not overwritten')", c == 1 and "Not overwritten" in o, f"{c} {o[-300:]}")
    check("1i the changed file is exactly as it was left", h(edited) == e_before)

    # ---- 1j. the backup's own failed copy is still redone (a record of a failed check, then the same command again)
    cardJ = card("cardJ", A3)
    drive_j = T / "driveJ"
    drive_j.mkdir()
    cmd = [S / "backup.py", "--source", cardJ, "--dest", drive_j, "--name", "tj", "--date", "2026-11-07"]
    run(*cmd)
    day = drive_j / "2026-11-07 tj"
    bad = day / "DCIM" / "100CANON" / "IMG_4473.JPG"
    bad.write_bytes(b"half a copy")         # what a broken copy leaves behind
    mpath = day / "_studio" / "manifest.json"
    m = json.loads(mpath.read_text(encoding="utf-8"))
    st = os.stat(bad)
    rec = m["files"]["DCIM/100CANON/IMG_4473.JPG"]
    rec["dest"] = {"ok": False, "note": "hash mismatch", "left": [st.st_size, st.st_mtime_ns, st.st_ino]}
    m["problems"] = ["IMG_4473 copied but the check failed"]
    mpath.write_text(json.dumps(m, indent=1), encoding="utf-8")
    c, o = run(*cmd)
    check("1j our own failed copy (record names what it left) is copied again: exit 0", c == 0, f"{c} {o[-400:]}")
    check("1k and now it is the card's photo", h(bad) == h(cardJ / "DCIM/100CANON/IMG_4473.JPG"))
    # the same, but somebody put a different file there since: never written over
    bad.write_bytes(b"half a copy, again")
    st = os.stat(bad)
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["files"]["DCIM/100CANON/IMG_4473.JPG"]["dest"] = {"ok": False, "note": "hash mismatch", "left": [st.st_size, st.st_mtime_ns, st.st_ino]}
    mpath.write_text(json.dumps(m, indent=1), encoding="utf-8")
    bad.unlink()
    shutil.copy2(C / "IMG_4481.JPG", bad)   # someone else's file now sits where our broken copy was
    other = h(bad)
    c, o = run(*cmd)
    check("1l a file put where our failed copy was is not written over (exit 1)", c == 1 and "Not overwritten" in o and h(bad) == other, f"{c}")
    # an older record (no 'left'): a failed copy of our own, redone as before
    bad.unlink()
    bad.write_bytes(b"half a copy, old record")
    m = json.loads(mpath.read_text(encoding="utf-8"))
    m["files"]["DCIM/100CANON/IMG_4473.JPG"]["dest"] = {"ok": False, "note": "hash mismatch"}
    mpath.write_text(json.dumps(m, indent=1), encoding="utf-8")
    c, o = run(*cmd)
    check("1m an older failed-copy record (before Nov 6) is still redone: exit 0", c == 0 and h(bad) == h(cardJ / "DCIM/100CANON/IMG_4473.JPG"), f"{c} {o[-300:]}")

    # ---- 2. two different cards, same name, same day, the first not finished
    cardA2 = card("cardA2", A3)
    cardB2 = card("cardB2", B3)
    drive2 = T / "drive2"
    drive2.mkdir()
    run(S / "studio_file.py", "set", "--drive", drive2, "--offered", "1", "--file-names", "shoot")

    def night(src, *x):
        return run(S / "night.py", "--source", src, "--name", "saturday card", "--date", "2026-11-07", *x)

    a, oa = night(cardA2)
    check("2a card A stops for the look (exit 4)", a == 4, f"{a} {oa[-300:]}")
    dayf = drive2 / "2026-11-07 saturday card"
    snap = {n: h(dayf / "DCIM/100CANON" / n) for n in ("IMG_4471.JPG", "IMG_4472.JPG", "IMG_4473.JPG")}
    bc, ob = night(cardB2, "--check")
    check("2b night.py --check on card B: exit 2 with plain words", bc == 2 and "different memory card" in ob, f"{bc} {ob[-400:]}")
    b, ob = night(cardB2)
    check("2c night.py on card B: exit 2, nothing taken as copied", b == 2 and "different memory card" in ob and "Already copied" not in ob, f"{b} {ob[-400:]}")
    bb, obb = run(S / "backup.py", "--source", cardB2, "--dest", drive2, "--name", "saturday card", "--date", "2026-11-07")
    check("2d backup.py on card B into that folder: exit 2", bb == 2 and "different memory card" in obb, f"{bb} {obb[-400:]}")
    check("2e card A's copies are untouched", snap == {n: h(dayf / "DCIM/100CANON" / n) for n in snap})
    m = json.loads((dayf / "_studio" / "manifest.json").read_text(encoding="utf-8"))
    check("2f the records still name card A as the source", m["source"] == str(cardA2), m["source"])
    print("    card B was told:", next((ln.strip() for ln in ob.splitlines() if "different memory card" in ln), "?"))
    # the same card again, with one more photo on it, after its backup finished: its own name, never "already copied"
    (cardA2 / "DCIM/100CANON/IMG_4474.JPG").write_bytes((C / "IMG_4474.JPG").read_bytes())
    a2, oa2 = night(cardA2)
    check("2g card A with a photo added after a finished backup: exit 2, its own name", a2 == 2 and "finished backup of this card" in oa2
          and "Already copied" not in oa2 and not (dayf / "DCIM/100CANON/IMG_4474.JPG").exists(), f"{a2} {oa2[-400:]}")
    print("    card A+1 was told:", next((ln.strip() for ln in oa2.splitlines() if "finished backup" in ln), "?"))
    # the same card with a photo taken off it: not the same card any more, so it gets its own name
    (cardA2 / "DCIM/100CANON/IMG_4471.JPG").unlink()
    a3, oa3 = night(cardA2)
    check("2h card A with a copied photo deleted: exit 2 (its own name, please)", a3 == 2 and "different memory card" in oa3, f"{a3} {oa3[-300:]}")

    # ---- 2i. a backup cut off part way (here: paused after the first photo), then the same command again
    cardK = card("cardK", [("IMG_4477.JPG", "IMG_4477.JPG"), ("IMG_4478.JPG", "IMG_4478.JPG"), ("IMG_4479.JPG", "IMG_4479.JPG")])

    def nk(*x):
        return run(S / "night.py", "--source", cardK, "--name", "cut off", "--date", "2026-11-07", *x)

    k1, ok1 = nk("--budget", "0.0001")
    dk = drive2 / "2026-11-07 cut off" / "DCIM" / "100CANON"
    had = sorted(x.name for x in dk.glob("*.JPG")) if dk.is_dir() else []
    check("2i the first run pauses part way (exit 3, not every photo copied)", k1 == 3 and len(had) < 3, f"{k1} {had} {ok1[-300:]}")
    k2, ok2 = nk()
    got = sorted(x.name for x in dk.glob("*.JPG"))
    check("2j the same command again copies the rest (never 'Already copied'), then stops for the look (exit 4)",
          k2 == 4 and "Already copied" not in ok2 and got == ["IMG_4477.JPG", "IMG_4478.JPG", "IMG_4479.JPG"]
          and all(h(dk / n) == h(C / n) for n in got), f"{k2} {got} {ok2[-400:]}")

    # ---- 3. the copy would land on the card itself, or inside it
    self_card = card("selfcard", [("IMG_4482.JPG", "IMG_4482.JPG"), ("IMG_4483.JPG", "IMG_4483.JPG")])
    before_tree = tree(self_card)
    c, o = run(S / "night.py", "--source", self_card, "--dest", self_card, "--name", "same drive", "--check")
    check("3a night.py --check onto the card itself: exit 2", c == 2 and "inside the very folder" in o, f"{c} {o[-300:]}")
    c, o = run(S / "backup.py", "--source", self_card, "--dest", self_card, "--name", "same drive")
    check("3b backup.py onto the card itself: exit 2", c == 2 and "inside the very folder" in o, f"{c} {o[-300:]}")
    c, o = run(S / "backup.py", "--source", self_card, "--dest", self_card / "DCIM", "--name", "inside")
    check("3c backup.py into a folder on the card: exit 2", c == 2, f"{c} {o[-300:]}")
    (T / "drive3").mkdir(exist_ok=True)
    c, o = run(S / "backup.py", "--source", self_card, "--dest", T / "drive3", "--second", self_card, "--name", "second on card")
    check("3d a second copy onto the card itself: exit 2", c == 2 and "second copy" in o.lower(), f"{c} {o[-300:]}")
    check("3e nothing at all was written on the card (not even the test file)", tree(self_card) == before_tree,
          str(sorted(set(tree(self_card)) ^ set(before_tree))[:5]))

    # ---- 3f. the drive rule itself, with what a PC would see (a separate drive, a card at the top of it)
    sys.path.insert(0, str(S))
    import backup  # noqa: E402
    import this_computer  # noqa: E402
    other_place = T / "drive4"
    other_place.mkdir()
    check("3f same disk as the computer's own, not a card: allowed", backup.onto_itself(cardA, other_place, "the backup") is None)
    real_own, real_top, real_label, real_windows = backup._own_disk, backup._top_of_drive, backup._drive_label, this_computer.WINDOWS
    try:
        backup._own_disk = lambda p: False                      # as if both were on one external drive
        backup._drive_label = lambda p: "E:"
        w = backup.onto_itself(cardA, other_place, "the backup")
        check("3g same external drive: stopped", bool(w) and "same drive the photos are coming from (E:)" in w, str(w))
        backup._top_of_drive = lambda p: cardA                   # as if the card were the drive (DCIM at its top)
        w = backup.onto_itself(cardA, other_place, "the backup")
        check("3h the card's own drive: stopped, called the memory card", bool(w) and "memory card itself (E:)" in w, str(w))
        this_computer.WINDOWS = True
        w = backup.onto_itself(cardA, other_place, "the second copy")
        check("3i on a PC the words say a drive can change letters", bool(w) and w.startswith("The second copy") and "different letter" in w, str(w))
    finally:
        this_computer.WINDOWS = real_windows
        backup._own_disk, backup._top_of_drive, backup._drive_label = real_own, real_top, real_label
    print("    words for the card itself:", w)

    print(f"\n{len(ran) - len(fails)} of {len(ran)} passed." + ("" if not fails else "  FAILED: " + ", ".join(fails)))
    if not fails:
        shutil.rmtree(T, ignore_errors=True)
    else:
        print(f"(scratch folder: {T})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
