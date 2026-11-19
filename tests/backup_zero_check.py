#!/usr/bin/env python3
"""A backup with no questions before the copy (Dustin, Nov 19). The first backup's setup is chosen by the
Assistant itself: the drive, where on it, the naming. The one question that may still be asked, once ever, is
which drive, and only when it cannot be told (more than one drive, or none).

Everything here is pretend: a scratch STUDIO_HOME, pretend drives (temp folders handed to the scripts through the
tests' switch STUDIO_DRIVES_FOR_TESTS, so the drives really plugged in are never looked at), a pretend Pictures
folder (STUDIO_FOLDERS_FOR_TESTS) and a pretend card (a temp folder with a DCIM). No browser, nothing on the screen.

    python3 tests/backup_zero_check.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pc_smoke as t  # noqa: E402
import this_computer  # noqa: E402  (pc_smoke put the scripts folder on the path)

FAILED = []
SKIPPED = []
GB = 1024 ** 3


def check(what, ok, detail=""):
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-900:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def world(work, name, drives):
    """One pretend computer: its own Studio home, Pictures, and the drives 'plugged in' (name -> total GB)."""
    base = work / name
    home, folders = base / "home", base / "folders"
    home.mkdir(parents=True)
    (folders / "Pictures").mkdir(parents=True)
    rows = []
    for dname, total in drives:
        p = base / "drives" / dname
        p.mkdir(parents=True)
        rows.append({"path": str(p), "name": dname, "shown": dname, "total": total * GB, "free": (total // 2) * GB,
                     "system": False, "removable": False, "id": None})
    listing = base / "drives.json"
    listing.write_text(json.dumps(rows), encoding="utf-8")
    env = {"STUDIO_HOME": str(home), "STUDIO_DRIVES_FOR_TESTS": str(listing),
           "STUDIO_FOLDERS_FOR_TESTS": str(folders), "STUDIO_NO_WINDOWS_FOR_TESTS": "1"}
    return base, home, env


def sf(home):
    return json.loads((home / "studio.json").read_text(encoding="utf-8"))


def same(a, b):
    return Path(a).resolve() == Path(b).resolve()


def can_make_pictures():
    ok, how = t.pictures.ready()
    if not ok:
        SKIPPED.append("the copy itself")
        print(f"  SKIP  the copy itself   [this computer cannot make the small pictures yet: {how}]", flush=True)
    return ok


def one_drive(work, copies):
    print("One drive plugged in: no question at all")
    base, home, env = world(work, "one", [("Big Kahuna", 4000)])
    drive = base / "drives" / "Big Kahuna"
    card = base / "CARD"
    t.make_card(card, groups=(5,))
    before = t.card_snapshot(card)

    code, out = t.run("studio_file.py", "defaults", "--dry-run", env=env)
    check("a dry run says what would be chosen and writes nothing",
          code == 0 and "WOULD CHOOSE:" in out and "Big Kahuna" in out and "right on the drive" in out
          and not (home / "studio.json").exists(), out)
    code, out = t.run("night.py", "--source", card, "--check", env=env)
    check("the quiet check before a first backup says ready, and where the photos would go",
          code == 0 and "PREFLIGHT OK" in out and "would go to Big Kahuna, right on the drive" in out, out)
    check("and writes nothing: no Studio File, nothing on the drive",
          not (home / "studio.json").exists() and not any(drive.iterdir()), str(list(drive.iterdir())))
    if copies:
        code, out = t.run("night.py", "--source", card, "--name", "zero card", "--date", "2026-11-19", env=env)
        session = drive / "2026-11-19 zero card"
        check("backup now with no Studio File copies into the chosen drive and reaches the look (exit 4, where it used to stop with exit 5)",
              code == 4 and (session / "_studio" / "manifest.json").is_file(), out)
        check("it says the one line about where the photos go",
              "First backup: your photos go to Big Kahuna, right on the drive." in out, out[:600])
        m = json.loads((session / "_studio" / "manifest.json").read_text(encoding="utf-8")) if code == 4 else {}
        files = m.get("files", {})
        check("every file on the card was copied and checked, to one place only",
              bool(files) and all(v.get("dest", {}).get("ok") for v in files.values()) and not m.get("second"), str(len(files)))
        check("the card is exactly as it was", t.card_snapshot(card) == before)
    else:
        code, out = t.run("studio_file.py", "defaults", env=env)
        check("the choice is made and written", code == 0 and "CHOSE:" in out, out)
    s = sf(home) if (home / "studio.json").exists() else {}
    n, d = s.get("naming", {}), s.get("drives", {})
    check("the Studio File now has the drive", same(d.get("session", ""), drive), str(d))
    check("year-first folder names, photos named for the shoot",
          n.get("folder_pattern") == "{date} {shoot}" and n.get("date_format") == "%Y-%m-%d" and n.get("file_names") == "shoot", str(n))
    check("no second copy", not d.get("second"), str(d))
    check("and one note saying it was chosen by itself",
          len(s.get("notes", [])) == 1 and "chosen by itself" in s["notes"][0]["note"] and "Big Kahuna" in s["notes"][0]["note"],
          str(s.get("notes")))
    bytes_before = (home / "studio.json").read_bytes()
    code, out = t.run("studio_file.py", "defaults", env=env)
    check("defaults again says SET and writes nothing (run twice, written once)",
          code == 0 and out.startswith("SET:") and "Big Kahuna" in out and (home / "studio.json").read_bytes() == bytes_before, out)
    code, out = t.run("night.py", "--source", card, "--check", env=env)
    check("the next check chooses nothing and changes nothing",
          "First backup" not in out and (home / "studio.json").read_bytes() == bytes_before, out)


def shoot_folder(work):
    print("A drive with an obvious shoot folder")
    base, home, env = world(work, "folder", [("Big Kahuna", 4000)])
    drive = base / "drives" / "Big Kahuna"
    for name in ("2026-01-10 Smith Family", "2026-02-14 Jones Wedding", "2026-03-01 Beach"):
        (drive / "Photo Shoots" / name).mkdir(parents=True)
    (drive / "Movies").mkdir()
    code, out = t.run("studio_file.py", "defaults", env=env)
    check("that folder is the place, said in words",
          code == 0 and "CHOSE:" in out and "| Big Kahuna | in Photo Shoots" in out
          and same(sf(home)["drives"]["session"], drive / "Photo Shoots"), out)
    check("nothing was made on the drive", sorted(p.name for p in drive.iterdir()) == ["Movies", "Photo Shoots"])
    code, out = t.run("studio_file.py", "glance", env=env)
    check("the glance still answers 'what are my settings?'", code == 0 and "No second copy" in out and "2026-10-18 Smith Family" in out, out)


def two_drives(work, copies):
    print("Two drives: the one question")
    base, home, env = world(work, "two", [("Little One", 500), ("Big Kahuna", 4000)])
    big = base / "drives" / "Big Kahuna"
    card = base / "CARD"
    t.make_card(card, groups=(4,))
    code, out = t.run("studio_file.py", "defaults", env=env)
    lines = out.splitlines()
    check("defaults stops with the which-drive words (exit 3)",
          code == 3 and lines[0] == "ASK which-drive" and "Which drive should your photos go on?" in out, out)
    listed = [ln for ln in lines if "GB free" in ln]
    check("both drives are listed by name and free space, the recommended (biggest) first",
          len(listed) == 2 and "Big Kahuna" in listed[0] and "(recommended)" in listed[0] and "Little One" in listed[1], out)
    check("and nothing is written", not (home / "studio.json").exists())
    code, out = t.run("night.py", "--source", card, env=env)
    check("backup now stops the same way: exit 5, the one question, the command that saves the answer",
          code == 5 and "ONE QUESTION" in out and "Which drive should your photos go on?" in out
          and "studio_file.py defaults --drive" in out and "second copy" not in out and "name shoot folders" not in out, out)
    check("still nothing written, nothing on either drive",
          not (home / "studio.json").exists() and not any(big.iterdir()) and not any((base / "drives" / "Little One").iterdir()))
    code, out = t.run("studio_file.py", "defaults", "--drive", base / "drives" / "Nowhere", env=env)
    check("a drive that is not there is refused and nothing is written", code != 0 and "STOP" in out and not (home / "studio.json").exists(), out)
    code, out = t.run("studio_file.py", "defaults", "--drive", big, env=env)
    check("the answer is saved with defaults --drive", code == 0 and "CHOSE:" in out and "| Big Kahuna | right on the drive" in out
          and same(sf(home)["drives"]["session"], big), out)
    if copies:
        code, out = t.run("night.py", "--source", card, "--name", "two card", "--date", "2026-11-19", env=env)
        check("and then the backup runs onto that drive (exit 4, the look)",
              code == 4 and (big / "2026-11-19 two card" / "_studio" / "manifest.json").is_file()
              and not any((base / "drives" / "Little One").iterdir()), out)
    else:
        code, out = t.run("night.py", "--source", card, "--check", env=env)
        check("and then the check says ready", code == 0 and "PREFLIGHT OK" in out, out)
    # the drive that already has shoots on it is the recommended one, whatever its size
    base, home, env = world(work, "two-b", [("Little One", 500), ("Big Kahuna", 4000)])
    for name in ("2026-01-10 A", "2026-02-14 B", "2026-03-01 C"):
        (base / "drives" / "Little One" / "Sessions" / name).mkdir(parents=True)
    code, out = t.run("studio_file.py", "defaults", env=env)
    listed = [ln for ln in out.splitlines() if "GB free" in ln]
    check("the drive that already has shoots on it comes first", code == 3 and listed and "Little One" in listed[0]
          and "already has shoots" in listed[0], out)
    code, out = t.run("studio_file.py", "defaults", "--drive", base / "drives" / "Little One", env=env)
    check("and choosing it uses its shoot folder", "| Little One | in Sessions" in out
          and same(sf(home)["drives"]["session"], base / "drives" / "Little One" / "Sessions"), out)


def no_drive(work):
    print("No external drive")
    base, home, env = world(work, "none", [])
    card = base / "CARD"
    t.make_card(card, groups=(3,))
    pictures = base / "folders" / "Pictures"
    code, out = t.run("studio_file.py", "defaults", env=env)
    check("defaults stops with the no-drive words (exit 4)",
          code == 4 and out.splitlines()[0] == "ASK no-drive" and "I don't see an external drive. Where should your photos go?" in out
          and "I'll plug one in" in out and "for now" in out, out)
    code, out = t.run("night.py", "--source", card, env=env)
    check("backup now stops the same way (exit 5), naming defaults --computer",
          code == 5 and "I don't see an external drive" in out and "studio_file.py defaults --computer" in out, out)
    check("nothing written, no folder made", not (home / "studio.json").exists() and not any(pictures.iterdir()))
    code, out = t.run("studio_file.py", "defaults", "--computer", "--dry-run", env=env)
    check("a dry run of the computer's own disk makes no folder", code == 0 and "WOULD CHOOSE:" in out and not any(pictures.iterdir())
          and not (home / "studio.json").exists(), out)
    code, out = t.run("studio_file.py", "defaults", "--computer", env=env)
    s = sf(home) if (home / "studio.json").exists() else {}
    check("the computer itself: a Shoots folder inside (the pretend) Pictures, made and saved",
          code == 0 and "CHOSE:" in out and (pictures / "Shoots").is_dir() and same(s.get("drives", {}).get("session", ""), pictures / "Shoots"), out)
    check("with a note that they said OK to the computer's own disk",
          len(s.get("notes", [])) == 1 and "own disk" in s["notes"][0]["note"] and "said OK" in s["notes"][0]["note"], str(s.get("notes")))
    code, out = t.run("night.py", "--source", card, "--check", env=env)
    check("and the check then says ready", code == 0 and "PREFLIGHT OK" in out, out)
    # a damaged or missing drive list is no drives at all, never the real ones
    env2 = dict(env, STUDIO_HOME=str(base / "home2"), STUDIO_DRIVES_FOR_TESTS=str(base / "not-there.json"))
    code, out = t.run("studio_file.py", "defaults", env=env2)
    check("the tests' switch with an unreadable list means no drives (the real ones are never looked at)",
          code == 4 and "ASK no-drive" in out, out)


def already_set(work):
    print("A Studio File that is already set")
    base, home, env = world(work, "set", [("Big Kahuna", 4000), ("Other", 2000)])
    mine, second = base / "drives" / "Other" / "My Shoots", base / "Second"
    mine.mkdir()
    second.mkdir()
    t.run("studio_file.py", "set", "--drive", mine, "--second", second, "--offered", "2", "--file-names", "original", env=env)
    before = (home / "studio.json").read_bytes()
    md = (home / "studio-file.md").read_bytes()
    outs = []
    for args in ([], ["--drive", base / "drives" / "Big Kahuna"], ["--computer"], ["--dry-run"]):
        code, out = t.run("studio_file.py", "defaults", *args, env=env)
        outs.append((code, out))
    check("defaults, defaults --drive and defaults --computer all say SET",
          all(c == 0 and o.startswith("SET:") and "Other" in o for c, o in outs), str(outs))
    check("and the Studio File is byte for byte unchanged",
          (home / "studio.json").read_bytes() == before and (home / "studio-file.md").read_bytes() == md)
    check("no Shoots folder was made in Pictures", not (base / "folders" / "Pictures" / "Shoots").exists())

    print("A naming on file but no drive yet")
    base, home, env = world(work, "naming", [("Big Kahuna", 4000)])
    t.run("studio_file.py", "set", "--offered", "2", "--file-names", "original", env=env)
    code, out = t.run("studio_file.py", "defaults", env=env)
    n = sf(home)["naming"]
    check("the drive is chosen and their naming is left alone",
          code == 0 and "CHOSE:" in out and n.get("folder_pattern") == "{shoot}, {date}" and n.get("file_names") == "original", str(n))


def never_the_source(work):
    print("The thing being backed up is never the place it goes")
    base, home, env = world(work, "source", [("Portable", 2000)])
    folder = base / "drives" / "Portable" / "Jones Wedding"
    t.make_card(folder, groups=(3,))
    code, out = t.run("studio_file.py", "defaults", "--source", folder, env=env)
    check("a folder on the only drive: that drive is not chosen for its own backup (the no-drive question instead)",
          code == 4 and "ASK no-drive" in out and not (home / "studio.json").exists(), out)
    code, out = t.run("night.py", "--source", folder, env=env)
    check("and backup now stops with the one question rather than copying a drive onto itself",
          code == 5 and not (home / "studio.json").exists(), out)


def the_switch_and_help():
    print("The tests' switch and the help text")
    work = Path(tempfile.mkdtemp(prefix="backup-zero-switch-"))
    try:
        listing = work / "d.json"
        listing.write_text(json.dumps([{"path": str(work), "name": "Pretend", "total": 10 * GB, "free": GB}]), encoding="utf-8")
        with t.environ(STUDIO_DRIVES_FOR_TESTS=str(listing)):
            got = this_computer.volumes()
        check("with the switch set, the drives are that list and nothing else, in the usual shape",
              len(got) == 1 and got[0]["path"] == str(work) and got[0]["shown"] == "Pretend"
              and set(got[0]) >= {"path", "name", "shown", "total", "free", "system", "removable", "id"}, str(got))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    code, out = t.run("backup.py", "--help")
    line = " ".join(out.split())
    check("backup.py's help calls the second copy a second drive, not a cloud folder",
          "second drive" in line and "cloud drive folder" not in line and "cloud folder\"" not in line, out)
    code, out = t.run("studio_file.py", "defaults", "--help")
    check("the defaults command is there with --drive, --computer and --dry-run",
          code == 0 and all(x in out for x in ("--drive", "--computer", "--dry-run")), out)


def main():
    os.environ.pop("STUDIO_DRIVES_FOR_TESTS", None)
    work = Path(tempfile.mkdtemp(prefix="backup-zero-"))
    try:
        copies = can_make_pictures()
        one_drive(work, copies)
        shoot_folder(work)
        two_drives(work, copies)
        no_drive(work)
        already_set(work)
        never_the_source(work)
        the_switch_and_help()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
