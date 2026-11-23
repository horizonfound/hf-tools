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
    check("folders named for the shoot then the date (Aurora_11-22-26), photos named for the shoot",
          n.get("folder_pattern") == "{shoot}_{date}" and n.get("date_format") == "%m-%d-%y" and n.get("file_names") == "shoot"
          and n.get("since"), str(n))
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
    check("the glance still answers 'what are my settings?'", code == 0 and "A second copy is yours to ask for after each backup, on its report" in out
          and "No second copy" not in out and "Smith Family_10-18-26" in out, out)


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
    check("defaults and a dry run say SET (exit 0)",
          all(c == 0 and o.startswith("SET:") and "Other" in o for c, o in (outs[0], outs[3])), str(outs))
    check("defaults --drive <another drive> and --computer say SET-OTHER and exit 6, so it can't be read as 'saved, go on'",
          all(c == 6 and o.startswith("SET-OTHER:") and "NOTHING CHANGED" in o and "studio_file.py set --drive" in o
              for c, o in (outs[1], outs[2])), str(outs))
    code, out = t.run("studio_file.py", "defaults", "--drive", base / "drives" / "Other", env=env)
    check("defaults --drive naming the drive that is on file is plain SET", code == 0 and out.startswith("SET:"), out)
    check("and the Studio File is byte for byte unchanged",
          (home / "studio.json").read_bytes() == before and (home / "studio-file.md").read_bytes() == md)
    check("no Shoots folder was made in Pictures", not (base / "folders" / "Pictures" / "Shoots").exists())

    print("A naming on file but no drive yet")
    base, home, env = world(work, "naming", [("Big Kahuna", 4000)])
    t.run("studio_file.py", "set", "--offered", "2", "--file-names", "original", env=env)
    code, out = t.run("studio_file.py", "defaults", env=env)
    n = sf(home)["naming"]
    check("the drive is chosen and their naming is left alone",
          code == 0 and "CHOSE:" in out and n.get("folder_pattern") == "{date} {shoot}" and n.get("file_names") == "original", str(n))


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


# ---------------------------------------------------------------- the Nov 19 review of the zero-questions backup

def world2(work, name, rows_):
    """As world(), with each drive's row given whole: (name, total GB, free GB, removable)."""
    base, home, env = world(work, name, [])
    rows = []
    for dname, total, free, removable in rows_:
        p = base / "drives" / dname
        p.mkdir(parents=True)
        rows.append({"path": str(p), "name": dname, "shown": dname, "total": total * GB, "free": int(free * GB),
                     "system": False, "removable": removable, "id": None})
    (base / "drives.json").write_text(json.dumps(rows), encoding="utf-8")
    return base, home, env


def plug_in(base, dname, total=4000, free=2000):
    p = base / "drives" / dname
    p.mkdir(parents=True)
    rows = json.loads((base / "drives.json").read_text(encoding="utf-8"))
    rows.append({"path": str(p), "name": dname, "shown": dname, "total": total * GB, "free": free * GB,
                 "system": False, "removable": False, "id": None})
    (base / "drives.json").write_text(json.dumps(rows), encoding="utf-8")
    return p


def never_saved_before_it_works(work):
    print("Review 1, 11: a drive is never saved before it is known to work")
    if this_computer.WINDOWS or os.geteuid() == 0:
        SKIPPED.append("a read-only drive")
        print("  SKIP  a read-only drive   [a folder cannot be made read-only this way here]", flush=True)
    else:
        base, home, env = world2(work, "stuck", [("Client USB", 500, 250, False)])
        usb = base / "drives" / "Client USB"
        card = base / "CARD"
        t.make_card(card, groups=(3,))
        os.chmod(usb, 0o555)
        try:
            code, out = t.run("studio_file.py", "defaults", "--source", card, env=env)
            check("the only drive cannot be written to: defaults saves nothing and asks instead (exit 4), saying why",
                  code == 4 and "ASK no-drive" in out and "I can't save photos to Client USB: it can be read but not written to." in out
                  and not (home / "studio.json").exists(), out)
            code, out = t.run("night.py", "--source", card, "--check", env=env)
            check("the quiet check asks the one question (exit 5) and saves nothing", code == 5 and not (home / "studio.json").exists(), out)
            code, out = t.run("night.py", "--source", card, env=env)
            check("backup now the same: exit 5, no drive saved, nothing copied",
                  code == 5 and "First backup: your photos go to" not in out and not (home / "studio.json").exists(), out)
            code, out = t.run("studio_file.py", "defaults", "--drive", usb, "--source", card, env=env)
            check("naming that drive as the answer is refused with the reason, nothing saved",
                  code != 0 and "STOP" in out and "can be read but not written to" in out and not (home / "studio.json").exists(), out)
            big = plug_in(base, "Big Kahuna")
            code, out = t.run("studio_file.py", "defaults", "--source", card, env=env)
            check("their real drive plugged in beside it: the which-drive question, with the other one marked as not offered",
                  code == 3 and "ASK which-drive" in out and "NOT OFFERED: Client USB" in out and not (home / "studio.json").exists(), out)
            code, out = t.run("studio_file.py", "defaults", "--drive", big, "--source", card, env=env)
            check("and the answer is saved", code == 0 and "CHOSE:" in out and same(sf(home)["drives"]["session"], big), out)
        finally:
            os.chmod(usb, 0o755)
    base, home, env = world2(work, "full", [("Nearly Full", 500, 1, False)])
    card = base / "CARD"
    t.make_card(card, groups=(3,))
    code, out = t.run("studio_file.py", "defaults", "--source", card, env=env)
    check("the only drive has no room for this card: nothing saved, the question instead, saying why",
          code == 4 and "Nearly Full does not have room for this card" in out and not (home / "studio.json").exists(), out)
    base, home, env = world(work, "late", [("Big Kahuna", 4000)])
    empty = base / "EMPTY CARD"
    (empty / "DCIM").mkdir(parents=True)
    code, out = t.run("night.py", "--source", empty, env=env)
    check("backup now that stops in its own checks (an empty card) has saved no drive: saved only once the checks pass",
          code == 2 and "Nothing on the card to copy" in out and not (home / "studio.json").exists(), out)


def where_on_the_drive(work):
    print("Review 3, 10: where on the drive is never a loose guess")
    for label, top, inside in (("an Apple Photos library", "Photos Library.photoslibrary", ("database", "originals", "resources", "private")),
                               ("Drawings (d-RAW-ings)", "Drawings", ("2019", "sketches", "clients-old")),
                               ("Homework (home-WORK)", "Homework", ("math", "art", "music")),
                               ("a Backups folder of dated folders", "Backups", ("2026-01-01", "2026-02-02")),
                               ("Final Exports, dated", "Final Exports", ("2026-01-10 A", "2026-02-11 B")),
                               ("a folder of dated folders with no shoot word", "Smith Archive", ("2024-01-01 a", "2025-02-02 b", "2026-03-03 c"))):
        base, home, env = world(work, "guess-" + "".join(c for c in top if c.isalnum()), [("My Passport", 2000)])
        drive = base / "drives" / "My Passport"
        for sub in inside:
            (drive / top / sub).mkdir(parents=True)
        (drive / "Movies").mkdir()
        code, out = t.run("studio_file.py", "defaults", "--dry-run", env=env)
        check(f"{label}: photos go right on the drive, never inside it",
              code == 0 and "WOULD CHOOSE:" in out and "| My Passport | right on the drive" in out and out.split("|")[0].strip().endswith("My Passport"), out)
    import studio_file
    base, home, env = world(work, "guess-ok", [("My Passport", 2000)])
    drive = base / "drives" / "My Passport"
    for top in ("Clients", "Photos Library.photoslibrary"):
        for sub in ("2026-01-10 Smith", "2026-02-14 Jones", "2026-03-01 Beach"):
            (drive / top / sub).mkdir(parents=True)
    code, out = t.run("studio_file.py", "defaults", "--dry-run", env=env)
    check("a folder plainly named for shoots, with folders in it, is still used", "| My Passport | in Clients" in out, out)
    with t.environ(**env):
        listed = [x["name"] for x in studio_file.drives()[0]["shoot_folders"]]
    check("and a library package is never even listed as a shoot folder", listed == ["Clients"], str(listed))


def a_card_is_never_the_drive(work):
    print("Review 4: a memory card or a stick is never chosen as the drive by itself")
    base, home, env = world(work, "videocard", [("XQD_VIDEO", 120)])
    (base / "drives" / "XQD_VIDEO" / "PRIVATE" / "M4ROOT" / "CLIP").mkdir(parents=True)
    card = base / "CARD"
    t.make_card(card, groups=(3,))
    code, out = t.run("studio_file.py", "defaults", "--source", card, "--dry-run", env=env)
    check("a video camera's card (no DCIM, its own folders at the top) is not a drive at all", code == 4 and "ASK no-drive" in out, out)
    code, out = t.run("studio_file.py", "drives", env=env)
    check("and is not in the list the report's panels use", "XQD_VIDEO" not in out, out)
    base, home, env = world2(work, "blankcard", [("Untitled", 120, 119, True)])
    blank = base / "drives" / "Untitled"
    card = base / "CARD"
    t.make_card(card, groups=(3,))
    code, out = t.run("studio_file.py", "defaults", "--source", card, env=env)
    check("the only thing plugged in is removable media (a blank card, a stick): asked about, never chosen (exit 3), nothing saved",
          code == 3 and "ASK is-this-the-drive" in out and "Should your photos go on Untitled?" in out
          and not (home / "studio.json").exists(), out)
    code, out = t.run("night.py", "--source", card, env=env)
    check("backup now asks the same one question (exit 5) and copies nothing", code == 5 and not any(blank.iterdir())
          and not (home / "studio.json").exists(), out)
    code, out = t.run("studio_file.py", "defaults", "--drive", card, env=env)
    check("a memory card named as the drive is refused", code != 0 and "That is a memory card" in out and not (home / "studio.json").exists(), out)
    code, out = t.run("studio_file.py", "defaults", "--drive", blank, "--source", card, env=env)
    check("their yes to the removable one is taken (it is their answer)", code == 0 and "CHOSE:" in out, out)


def the_card_answers_first(work):
    print("Review 13: the card is asked whether it answers before anything else looks at it")
    base, home, env = world(work, "quiet", [("Big Kahuna", 4000)])
    card = base / "CARD"
    t.make_card(card, groups=(3,))
    quiet = dict(env, ASSISTANT_CARD_ANSWER_SECONDS="0")
    code, out = t.run("night.py", "--source", card, env=quiet)
    check("a card that does not answer stops the first backup before a drive is worked out or saved",
          code == 2 and "Your memory card has stopped answering" in out and "First backup" not in out
          and not (home / "studio.json").exists(), out)
    code, out = t.run("studio_file.py", "defaults", "--source", card, env=quiet)
    check("defaults --source the same", code != 0 and "Your memory card has stopped answering" in out and not (home / "studio.json").exists(), out)


def finish(night, env, studio):
    """Do the look for a pretend backup that stopped at exit 4 (one shoot per group) and run it again."""
    groups = json.loads((studio / "groups.json").read_text(encoding="utf-8"))["groups"]
    shoots = [{"id": f"s{i}", "suggested": f"{studio.parent.name[11:]} {i}", "groups": [g["id"]], "photos": g.get("count", 0),
               "recap": "Test frames.", "why": "test"} for i, g in enumerate(groups, 1)]
    (studio / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": shoots}), encoding="utf-8")
    return t.run(*night, env=env)


def other_photos(card, salt):
    for p in (card / "DCIM" / "100CANON").glob("*.JPG"):
        p.write_bytes(p.read_bytes() + salt)


def two_cards_one_day(work):
    print("Review 8: a second card on the same day is never told it is already backed up")
    from datetime import datetime
    base, home, env = world(work, "twocards", [("Big Kahuna", 4000)])
    drive = base / "drives" / "Big Kahuna"
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", env=env)
    a, b = base / "CARD A", base / "CARD B"
    t.make_card(a, groups=(5,))
    t.make_card(b, groups=(4, 3))
    other_photos(b, b"card b")
    day = datetime.now().strftime("%A").lower() + " card"
    D = "2026-11-19"
    night_a = ["night.py", "--source", a, "--date", D, "--no-peeks"]
    code, out = t.run(*night_a, env=env)
    st_a = drive / f"{D} {day}" / "_studio"
    if code != 4:
        check("card A reaches the look", False, out)
        return None
    code, out = finish(night_a, env, st_a)
    rec_a = drive / ".studio" / f"{D} {day}"
    check("card A is backed up under the day's name and settles", code == 0 and (rec_a / "settled.json").is_file(), out)
    ledger = lambda: json.loads((home / "cards.json").read_text(encoding="utf-8"))["cards"]
    n_cards = len(ledger())
    night_b = ["night.py", "--source", b, "--date", D, "--no-peeks"]
    code, out = t.run(*night_b, "--check", env=env)
    check("the quiet check on card B says ready, never 'finished and settled', and puts nothing in the card ledger",
          code == 0 and "PREFLIGHT OK" in out and "finished and settled" not in out and "already safe" not in out
          and len(ledger()) == n_cards, out)
    code, out = t.run(*night_b, env=env)
    st_b = drive / f"{D} {day} 2" / "_studio"
    m = json.loads((st_b / "manifest.json").read_text(encoding="utf-8")) if (st_b / "manifest.json").is_file() else {}
    check("backup now on card B copies it, into a folder of its own with the next name, and says so in one line",
          code == 4 and len(m.get("files", {})) == 8 and all(v.get("dest", {}).get("ok") for v in m["files"].values())
          and f'so this one is "{day} 2"' in out, out)
    code, out = t.run(*night_a, env=env)
    check("card A again is still known as already safe", code == 0 and "already safe" in out, out)
    # card A with photos taken since its backup
    src = sorted((a / "DCIM" / "100CANON").glob("*.JPG"))[0]
    for i in (1, 2):
        (a / "DCIM" / "100CANON" / f"NEW_{i}.JPG").write_bytes(src.read_bytes() + bytes([i]))
    code, out = t.run(*night_a, "--check", env=env)
    check("card A with two new photos is not called finished", code == 0 and "PREFLIGHT OK" in out and "finished and settled" not in out
          and "already safe" not in out, out)
    code, out = t.run(*night_a, env=env)
    m3 = drive / f"{D} {day} 3" / "_studio" / "manifest.json"
    check("and is copied again in full under the next free name, the new photos with it",
          code == 4 and m3.is_file() and "DCIM/100CANON/NEW_2.JPG" in json.loads(m3.read_text(encoding="utf-8"))["files"], out)
    # a name they gave themselves is never changed: it stops
    c = base / "CARD C"
    t.make_card(c, groups=(2,))
    other_photos(c, b"card c")
    before = (home / "cards.json").read_bytes()
    code, out = t.run("night.py", "--source", c, "--date", D, "--name", day, "--check", env=env)
    check("a card given the name of a finished backup of another card stops (exit 2), is not in the ledger, and is not copied",
          code == 2 and "different memory card" in out and (home / "cards.json").read_bytes() == before
          and not (drive / f"{D} {day} 4").exists(), out)
    return {"env": env, "rec_a": rec_a, "st_b": st_b, "night_b": night_b}


def take_cards_apart(got):
    print("Review 7: two backups put on one report can be taken apart again")
    if not got:
        return
    env, rec_a, st_b = got["env"], got["rec_a"], got["st_b"]
    code, out = t.run("shoot_report.py", "link", rec_a, st_b, env=env)
    check("linked (two cards on one report)", code == 0 and (rec_a / "shoot.json").is_file() and (st_b / "shoot.json").is_file(), out)
    linked = (rec_a / "shoot.json").read_bytes()
    photos = sorted(str(p) for p in rec_a.parent.parent.rglob("*.JPG"))
    code, out = t.run("shoot_report.py", "unlink", st_b, env=env)
    check("unlink takes them apart: neither is part of a shoot any more",
          code == 0 and not (rec_a / "shoot.json").exists() and not (st_b / "shoot.json").exists() and "No photo or folder was touched." in out, out)
    kept = list(rec_a.glob("shoot.before-unlink-*.json"))
    check("the record before is kept beside it, byte for byte", len(kept) == 1 and kept[0].read_bytes() == linked
          and len(list(st_b.glob("shoot.before-unlink-*.json"))) == 1, str(kept))
    check("no photo moved", sorted(str(p) for p in rec_a.parent.parent.rglob("*.JPG")) == photos)
    code, out = t.run("shoot_report.py", "show", rec_a, env=env)
    check("show says so", code == 2 and "Not part of a shoot" in out, out)
    code, out = t.run("shoot_report.py", "unlink", st_b, env=env)
    check("run twice: nothing to do (exit 2), nothing more written", code == 2 and len(list(rec_a.glob("shoot.before-unlink-*.json"))) == 1, out)


def second_drive_trouble(work):
    print("Review 2: a second drive with trouble never stops or breaks the backup (since Nov 23: a drive named for that one backup, "
          "copied after the settle with the photo drive's own folders and names; a saved one is no longer used by itself)")
    base, home, env = world(work, "secondtrouble", [("Big Kahuna", 4000), ("LaCie", 2000)])
    drive, lacie = base / "drives" / "Big Kahuna", base / "drives" / "LaCie"
    t.run("studio_file.py", "set", "--drive", drive, "--offered", "1", env=env)
    D = "2026-11-19"

    def backup(name, salt, groups=(3,)):
        card = base / f"CARD {name}"
        t.make_card(card, groups=groups)
        other_photos(card, salt)
        return card, ["night.py", "--source", card, "--date", D, "--name", name, "--no-peeks", "--second", lacie], drive / f"{D} {name}" / "_studio"

    def one_copy(st):
        m = json.loads((st / "manifest.json").read_text(encoding="utf-8")) if (st / "manifest.json").is_file() else {}
        return bool(m.get("files")) and all(v.get("dest", {}).get("ok") for v in m["files"].values()) and not m.get("second") and not m.get("problems")

    # the ordinary case still works: the second copy is made, after the backup is sorted and settled
    card, night, st = backup("good second", b"g")
    code, out = t.run(*night, env=env)
    check("a good second drive: the card is copied and checked first (exit 4, the look), with nothing on the second drive yet",
          code == 4 and one_copy(st) and not any(lacie.iterdir()), out)
    code, out = finish(night, env, st)
    rec = drive / ".studio" / f"{D} good second"
    m = json.loads((rec / "manifest.json").read_text(encoding="utf-8")) if (rec / "manifest.json").is_file() else {}
    folders = sorted(x.name for x in drive.iterdir() if x.is_dir() and not x.name.startswith("."))
    check("it finishes and settles, and then the second copy is made, every file of it checked",
          code == 0 and m.get("second") and all(v.get("second", {}).get("ok") for v in m.get("files", {}).values())
          and out.index("7b. The second copy") > out.index("7. Putting the shoots where they belong"), out[-700:])
    check("the second drive has the photo drive's own shoot folders and nothing of the card's layout (Nicole, Nov 23)",
          folders and sorted(x.name for x in lacie.iterdir() if not x.name.startswith(".")) == folders
          and not (lacie / "DCIM").exists() and not (lacie / f"{D} good second").exists()
          and all(sorted(p.name for p in (lacie / f).iterdir()) == sorted(p.name for p in (drive / f).iterdir()) for f in folders),
          str(sorted(x.name for x in lacie.iterdir())))

    # a folder of theirs with a shoot's name is already on the second drive
    card, night, st = backup("in the way", b"w")
    there = lacie / "in the way 1_06-04-26" / "their own file.jpg"
    there.parent.mkdir(parents=True)
    there.write_bytes(b"something else that was already here")
    code, out = t.run(*night, env=env)
    check("a folder of theirs with the shoot's name on the second drive: the backup is not 'Not finished' (exit 4, the look), one copy, card in the ledger",
          code == 4 and one_copy(st) and "Not finished" not in out and "Traceback" not in out, out)
    code, out = finish(night, env, st)
    rec = drive / ".studio" / f"{D} in the way"
    check("(that is the name the shoot's folder got)", (drive / "in the way 1_06-04-26").is_dir(), str(sorted(x.name for x in drive.iterdir())))
    check("it finishes and settles with one copy (exit 0), and their folder is untouched: nothing was copied into it",
          code == 0 and one_copy(rec) and there.read_bytes() == b"something else that was already here"
          and sorted(x.name for x in there.parent.iterdir()) == ["their own file.jpg"], out[-600:])
    page = (rec / "report.html").read_text(encoding="utf-8") if (rec / "report.html").is_file() else ""
    check("the report calls the card safe, and its top says there is one copy and why, naming the folder, with no path",
          "safe to format" in page and "No second copy yet, so there&#x27;s one copy for now. LaCie already has a folder called in the way 1_06-04-26 that isn&#x27;t part of this second copy." in page
          and str(base) not in page.split("second-missed")[1][:500], page[:200])
    code2, out2 = t.run(*night, env=env)
    check("run again: the same, never a stop", code2 == 0 and one_copy(rec) and there.read_bytes() == b"something else that was already here", out2)

    # no room on the second drive
    rows = json.loads((base / "drives.json").read_text(encoding="utf-8"))
    for r in rows:
        if r["name"] == "LaCie":
            r["free"] = GB // 2
    (base / "drives.json").write_text(json.dumps(rows), encoding="utf-8")
    card, night, st = backup("no room", b"r")
    code, out = t.run(*night, env=env)
    check("no room on the second drive: the backup copies everything to the photo drive (exit 4)", code == 4 and one_copy(st), out)
    code, out = finish(night, env, st)
    rec = drive / ".studio" / f"{D} no room"
    note = json.loads((rec / "second-missed.json").read_text(encoding="utf-8")) if (rec / "second-missed.json").is_file() else {}
    check("and finishes with one copy, the reason on record",
          code == 0 and one_copy(rec) and "Not enough room on LaCie" in note.get("words", ""), out[-600:])
    page = (rec / "report.html").read_text(encoding="utf-8") if (rec / "report.html").is_file() else ""
    check("the report it leaves says at its top that there is one copy and why, by the drive's name, with no path",
          "No second copy yet, so there&#x27;s one copy for now. Not enough room on LaCie" in page and str(base) not in page.split("second-missed")[1][:400], page[:200])
    for r in rows:
        if r["name"] == "LaCie":
            r["free"] = 1000 * GB
    (base / "drives.json").write_text(json.dumps(rows), encoding="utf-8")

    # the second drive can be read but not written to
    if this_computer.WINDOWS or os.geteuid() == 0:
        SKIPPED.append("a read-only second drive")
        print("  SKIP  a read-only second drive   [a folder cannot be made read-only this way here]", flush=True)
        return
    card, night, st = backup("read only", b"o")
    os.chmod(lacie, 0o555)
    try:
        code, out = t.run(*night, env=env)
        check("a second drive that cannot be written to: no Python error, the backup reaches the look with one copy",
              code == 4 and one_copy(st) and "Traceback" not in out and "PermissionError" not in out, out)
        code, out = finish(night, env, st)
        rec = drive / ".studio" / f"{D} read only"
        check("and finishes, sorted and settled, with one copy and no Python error",
              code == 0 and (rec / "settled.json").is_file() and (rec / "sort-log.json").is_file() and one_copy(rec)
              and "Traceback" not in out and "PermissionError" not in out, out[-600:])
    finally:
        os.chmod(lacie, 0o755)
    code, out = t.run("second_copy.py", rec, "--to", lacie, env=env)
    m = json.loads((rec / "manifest.json").read_text(encoding="utf-8"))
    check("once the drive is right again, Make a second copy makes it", code == 0 and m.get("second"), out)

    # a second drive saved for every backup by an earlier version is no longer used by itself
    sf_path = home / "studio.json"
    sf = json.loads(sf_path.read_text(encoding="utf-8"))
    sf["drives"]["second"], sf["drives"]["second_label"] = str(lacie), "LaCie"
    sf_path.write_text(json.dumps(sf), encoding="utf-8")
    held = sorted(x.name for x in lacie.iterdir())
    card = base / "CARD saved"
    t.make_card(card, groups=(2,))
    other_photos(card, b"s")
    night = ["night.py", "--source", card, "--date", D, "--name", "saved", "--no-peeks"]
    st = drive / f"{D} saved" / "_studio"
    code, out = t.run(*night, env=env)
    code, out = finish(night, env, st)
    rec = drive / ".studio" / f"{D} saved"
    check("a saved second drive (plugged in) gets no copy by itself any more (Nicole, Nov 23: ask each time): one copy, nothing new on it",
          code == 0 and one_copy(rec) and sorted(x.name for x in lacie.iterdir()) == held and "7b. The second copy" not in out, out[-500:])


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
        never_saved_before_it_works(work)
        where_on_the_drive(work)
        a_card_is_never_the_drive(work)
        the_card_answers_first(work)
        if copies:
            take_cards_apart(two_cards_one_day(work))
            second_drive_trouble(work)
        the_switch_and_help()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{'ALL OK' if not FAILED else str(len(FAILED)) + ' FAILED'}" + (f" ({len(SKIPPED)} skipped)" if SKIPPED else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
