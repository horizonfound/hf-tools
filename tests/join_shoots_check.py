#!/usr/bin/env python3
"""Joining two or more shoots of one backup into one folder (join_shoots.py; Nicole, Nov 23: "Joining two shoots
into one ... needed for launch").

It renames files on a drive, so every promise has a check here: the plan checked before the first move, the log
first, nothing overwritten (names read from the folder's own listing), every file proved the same file (by
identity, read in full when identity cannot say), numbered on in shooting order, sidecars travelling, photos and
clips into Photos and Videos, emptied folders removed only when truly empty, safe twice, a run cut off at each
of eight points finished by the next, every record following, and the refusals in plain words.

Everything is pretend: a scratch STUDIO_HOME, pretend drives and cards (temp folders), whole pretend backups made
by night.py itself. No page server, no browser, no window.

    python3 tests/join_shoots_check.py [--only plain,refusals,letters,cut_off,unprovable,with_clips,review_fixes,settle_waits,second_copy_follows]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Nothing here may ever look at the real ~/.studio: even the modules this test imports itself get a scratch home
# (every script it runs gets its own pretend world's on top of this).
os.environ["STUDIO_HOME"] = tempfile.mkdtemp(prefix="scratch-studio-home-")
os.environ["STUDIO_NO_WINDOWS_FOR_TESTS"] = "1"
import report_options_check as r  # noqa: E402  (its pretend world and whole pretend backups)
t = r.t

FAILED = []
N = [0]


def check(what, ok, detail=""):
    N[0] += 1
    print(("  ok    " if ok else "  FAIL  ") + what + ("" if ok or not detail else f"\n        {str(detail)[-900:]}"), flush=True)
    if not ok:
        FAILED.append(what)


def jread(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def listing(folder):
    """Every file and folder under a drive by its exact name, the Assistant's hidden records left out."""
    folder = Path(folder)
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if ".studio" not in p.relative_to(folder).parts
                  and "_studio" not in p.relative_to(folder).parts)


def join(w, b, *args, **env):
    return t.run("join_shoots.py", b["records"], *args, env=dict(w["env"], **env))


def world(work, name, groups=(5, 4, 3), shoots=("Beach", "Palms", "Garden"), file_names="shoot", card=None):
    w = r.new_world(work, name)
    w["drive"] = r.new_drive(w, "Big Kahuna", 2000)
    t.run("studio_file.py", "set", "--drive", w["drive"], "--offered", "1", "--file-names", file_names, env=w["env"])
    if card:
        return w, card(w)
    b = r.a_backup(w, "CARD", "first card", r.DAY1, groups, list(shoots), w["drive"])
    return w, b


def records_right(w, b, what, shoots_left):
    """The records and the drive agree, exactly: every photo the index names is under exactly that name and is
    byte for byte the card's; the groups name the same files; the shoots' folders are there."""
    st = b["records"]
    index = jread(st / "index.json", {})
    bad, n = t.photos_match(w["drive"], index, b["card"])
    check(f"{what}: every photo is byte for byte the card's, under exactly the name the records give ({n})", not bad and n > 0, bad[:5])
    in_index = {p["file"] for p in index.get("photos", [])}
    in_groups = {f for g in jread(st / "groups.json", {}).get("groups", []) for f in g["files"]}
    check(f"{what}: the groups name the same files as the index", in_groups <= in_index, sorted(in_groups - in_index)[:5])
    sh = jread(st / "shoots.json", {}).get("shoots", [])
    check(f"{what}: the shoots left are {shoots_left}", [s["id"] for s in sh] == shoots_left, [s["id"] for s in sh])
    check(f"{what}: each shoot's folder is on the drive under exactly its name",
          all(s["folder"] in os.listdir(w["drive"]) for s in sh), [s["folder"] for s in sh])
    check(f"{what}: the card is exactly as it was", t.card_snapshot(b["card"]) == b["before"])
    return sh


# ---------------------------------------------------------------- the cases

def plain(work):
    print("Two of three shoots into one")
    w, b = world(work, "plain")
    if not b:
        return
    st = b["records"]
    before = listing(w["drive"])
    code, out = join(w, b, "--list")
    check("--list names each shoot by id, name, folder and count",
          code == 0 and "s1 | Beach | Beach_06-04-26 | 5 photos" in out and "s3 | Garden | Garden_06-04-26 | 3 photos" in out, out)
    code, out = join(w, b, "--shoots", "s1", "s2", "--dry-run")
    check("a dry run shows the plan and touches nothing", code == 0 and "Dry run. Nothing joined." in out and listing(w["drive"]) == before
          and not (st / "join-log.json").exists(), out)
    # a sidecar their editing program wrote beside a photo since the backup, and the first-look picks
    xmp = w["drive"] / "Palms_06-04-26" / "Palms_0002_IMG_4477.xmp"
    xmp.write_bytes(b"<x:xmpmeta>their own edit</x:xmpmeta>")
    (w["drive"] / "Palms_06-04-26" / ".DS_Store").write_bytes(b"finder")     # the computer's own note in a folder they opened
    (st / "sneak-peeks").mkdir(exist_ok=True)
    picks = []
    for sid, folder, pre, first in (("s1", "Beach_06-04-26", "Beach", 4471), ("s2", "Palms_06-04-26", "Palms", 4476)):
        for k in range(3):
            f = f"{folder}/{pre}_{k + 1:04d}_IMG_{first + k}.JPG"
            (st / "sneak-peeks" / (Path(f).stem + ".jpg")).write_bytes(b"small copy " + f.encode())
            picks.append({"file": f, "shoot": sid, "n": k + 1})
    (st / "sneak-peeks.json").write_text(json.dumps({"picks": picks}), encoding="utf-8")
    code, out = join(w, b, "--shoots", "s1", "s2")
    check("the join finishes (exit 0) and says how many files it checked", code == 0 and "9 of 9" not in out and "10 of 10 files checked" in out and "Joined." in out, out)
    want = [f"Beach_06-04-26/Beach_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 10)]
    got = [x for x in listing(w["drive"]) if x.startswith("Beach_06-04-26/") and x.endswith(".JPG")]
    check("the photos are numbered on in shooting order across the joined shoot, the first word of its name in front, the camera's name inside",
          got == want, got)
    check("the other shoot's folder is gone (it was truly empty), and the third shoot is untouched",
          "Palms_06-04-26" not in os.listdir(w["drive"]) and [x for x in listing(w["drive"]) if x.startswith("Garden")] == [x for x in before if x.startswith("Garden")])
    check("the computer's own hidden note in the emptied folder was set aside in the records, never deleted",
          (st / "from-joined" / "Palms_06-04-26" / ".DS_Store").is_file()
          and (st / "from-joined" / "Palms_06-04-26" / ".DS_Store").read_bytes() == b"finder")
    check("no gathering folder is left behind", not [x for x in os.listdir(w["drive"]) if "(joining)" in x], os.listdir(w["drive"]))
    moved_xmp = w["drive"] / "Beach_06-04-26" / "Beach_0007_IMG_4477.xmp"
    check("the sidecar travelled with its photo under the same new stem, unchanged",
          moved_xmp.is_file() and moved_xmp.read_bytes() == b"<x:xmpmeta>their own edit</x:xmpmeta>" and not xmp.exists())
    sh = records_right(w, b, "after the join", ["s1", "s3"])
    kept = sh[0] if sh else {}
    check("the shoot that stays has both shoots' groups in time order, its count, and remembers what was joined into it",
          kept.get("groups") == ["g01", "g02"] and kept.get("photos") == 9 and kept.get("folder") == "Beach_06-04-26"
          and [j["id"] for j in kept.get("joined", [])] == ["s2"] and kept["joined"][0]["name"] == "Palms"
          and kept["joined"][0]["folder"] == "Palms_06-04-26", kept)
    names = jread(st / "names.json", {})
    check("names.json names the joined shoot and no longer the joined-away one", names.get("s1") == "Beach" and "s2" not in names, names)
    log = jread(st / "join-log.json", {})
    e = (log.get("joins") or [{}])[0]
    check("the log holds every move with its hash and its identity on the drive, and is finished with no problems",
          len(e.get("moves", [])) == 10 and all(m.get("sha256") and m.get("ident") and m.get("moved") and m.get("checked") for m in e["moves"])
          and e.get("finished") and not e.get("problems") and e.get("verified") == 10, {k: v for k, v in e.items() if k != "moves"})
    check("identity proved every file, so none had to be read in full", e.get("hashed_in_full") == 0, e.get("hashed_in_full"))
    pk = jread(st / "sneak-peeks.json", {}).get("picks", [])
    check("the first-look picks follow the photos to their new names, all of them the joined shoot's now",
          all(p["shoot"] == "s1" for p in pk) and all((w["drive"] / p["file"]).is_file() for p in pk), pk)
    check("the picks of the two shoots take turns, so the six shown come from both",
          [p.get("shoot_was", "s1") for p in pk] == ["s1", "s2", "s1", "s2", "s1", "s2"], [p.get("shoot_was", "s1") for p in pk])
    check("a joined-away pick no longer carries a number from the other shoot's own pages", all("n" not in p for p in pk if p.get("shoot_was")), pk)
    check("each pick's small picture took the photo's new name",
          all((st / "sneak-peeks" / (Path(p["file"]).stem + ".jpg")).is_file() for p in pk) and len(list((st / "sneak-peeks").glob("*.jpg"))) == 6,
          sorted(x.name for x in (st / "sneak-peeks").glob("*.jpg")))
    q = jread(w["home"] / "queue.json", {})
    mine = [x for x in q.get("shoots", []) if x.get("shoot") == "s1"]
    check("the list of shoots shows the joined shoot once, with its count and folder; the joined-away line is set aside, not deleted",
          len(mine) == 1 and mine[0]["count"] == 9 and mine[0]["folder"].endswith("Beach_06-04-26")
          and not [x for x in q.get("shoots", []) if x.get("shoot") == "s2"] and [x.get("shoot") for x in q.get("joined", [])] == ["s2"], q)
    page = (st / "report.html").read_text(encoding="utf-8") if (st / "report.html").exists() else ""
    check("the report was built again and shows two shoots", "2 shoots" in page, page[page.find("shoots-head"):][:300])

    print("The same join again, and a rename afterwards")
    after = listing(w["drive"])
    records = {n: (st / n).read_bytes() for n in ("index.json", "groups.json", "shoots.json", "names.json", "join-log.json")}
    code, out = join(w, b, "--shoots", "s1", "s2")
    check("run twice it says Already joined and changes nothing, on the drive or in the records",
          code == 0 and "Already joined" in out and listing(w["drive"]) == after
          and all((st / n).read_bytes() == v for n, v in records.items()), out)
    code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "The Aurora Family", env=w["env"])
    got = [x for x in listing(w["drive"]) if x.startswith("The Aurora Family_06-04-26/") and x.endswith(".JPG")]
    check("the joined shoot renames like any other (folder, photos and the sidecar)",
          code == 0 and got == [f"The Aurora Family_06-04-26/Aurora_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 10)]
          and (w["drive"] / "The Aurora Family_06-04-26" / "Aurora_0007_IMG_4477.xmp").is_file(), out + str(got))
    records_right(w, b, "after the rename", ["s1", "s3"])
    code, out = join(w, b, "--all", "--name", "Mini sessions")
    got = [x for x in listing(w["drive"]) if x.endswith(".JPG")]
    check("--all puts every shoot of the backup in one folder, numbered on across all of them",
          code == 0 and got == [f"Mini sessions_06-04-26/Mini_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 13)]
          and [x for x in os.listdir(w["drive"]) if not x.startswith(".")] == ["Mini sessions_06-04-26"], out + str(got))
    sh = records_right(w, b, "after joining them all", ["s1"])
    check("the one shoot remembers both joins", [j["id"] for j in (sh[0].get("joined") or [])] == ["s2", "s3"] if sh else False, sh)
    code, out = join(w, b, "--all")
    check("--all on a backup that is one shoot already says so and does nothing", code == 0 and "Already joined" in out, out)


def refusals(work):
    print("What is refused, before anything moves")
    w, b = world(work, "refuse")
    if not b:
        return
    st = b["records"]

    def refused(what, args, words, env=None, code_want=2):
        before = listing(w["drive"])
        code, out = join(w, b, *args, **(env or {}))
        check(f"{what}: refused in plain words (exit {code_want}), nothing changed",
              code == code_want and words in out and listing(w["drive"]) == before and not (st / "join-log.json").exists(), out)
        check(f"{what}: the words name no path", str(w["base"]) not in out.split("STOP:")[-1], out)
    refused("one shoot alone", ["--shoots", "s1"], "Joining needs two or more shoots.")
    refused("a shoot this backup does not have (one from another backup)", ["--shoots", "s1", "s9"], "I can't find a shoot called s9 in that backup.")
    (w["drive"] / "Weddings_06-04-26").mkdir()
    refused("a name another folder already has", ["--shoots", "s1", "s2", "--name", "Weddings"],
            "There is already a folder called Weddings_06-04-26 next to these shoots.")
    os.rmdir(w["drive"] / "Weddings_06-04-26")
    (w["drive"] / "weddings_06-04-26 (JOINING)").mkdir()
    refused("the name of the folder the photos are gathered in is taken, in other capitals", ["--shoots", "s1", "s2", "--name", "Weddings"],
            "There is already a folder called weddings_06-04-26 (JOINING) next to these shoots.")
    os.rmdir(w["drive"] / "weddings_06-04-26 (JOINING)")
    theirs = w["drive"] / "Beach_06-04-26" / "my notes.txt"
    theirs.write_text("theirs", encoding="utf-8")
    refused("the folder whose name the joined shoot takes holds something of theirs", ["--shoots", "s1", "s2"],
            "Beach_06-04-26 has things in it that I didn't put there (my notes.txt)")
    theirs.unlink()
    # in the editing queue with a due date; delivered; a post kit made from it
    code, out = t.run("edit_queue.py", "add", "--night", st, "--shoot", "s2", "--due", "1w", env=w["env"])
    refused("a shoot in the editing queue with a due date", ["--shoots", "s1", "s2"], "Palms is in your editing queue with a due date. Take it out of your queue first")
    q = jread(w["home"] / "queue.json")
    for x in q["shoots"]:
        if x.get("shoot") == "s2":
            x["status"], x["finished_at"] = "finished", "2026-11-22T10:00:00"
    (w["home"] / "queue.json").write_text(json.dumps(q), encoding="utf-8")
    refused("a delivered shoot", ["--shoots", "s1", "s2"], "Palms is marked as delivered")
    for x in q["shoots"]:
        if x.get("shoot") == "s2":
            x["status"] = "archived"
            x.pop("due", None)
    (w["home"] / "queue.json").write_text(json.dumps(q), encoding="utf-8")
    assistant = w["base"] / "The Assistant"
    kit = assistant / "Your Content" / "Palms_06-04-26" / ".kit"
    kit.mkdir(parents=True)
    (kit / "kit.json").write_text(json.dumps({"name": "Palms", "folder": "Palms_06-04-26", "source": "backup", "night": str(st), "shoot_id": "s2"}), encoding="utf-8")
    sf = jread(w["home"] / "studio.json")
    sf.setdefault("posts", {})["home"] = str(assistant)
    (w["home"] / "studio.json").write_text(json.dumps(sf), encoding="utf-8")
    refused("a shoot a post kit was made from", ["--shoots", "s2", "s3"], "You already made a post kit from Palms")
    shutil.rmtree(assistant)
    # a backup that is not fully checked
    m = jread(st / "manifest.json")
    keep = json.dumps(m)
    m["problems"] = ["pretend"]
    (st / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    refused("a backup with a problem on record", ["--shoots", "s1", "s2"], "That backup is not fully checked yet")
    (st / "manifest.json").write_text(keep, encoding="utf-8")
    # a photo gone from where the records say it is
    gone = w["drive"] / "Palms_06-04-26" / "Palms_0001_IMG_4476.JPG"
    aside = w["base"] / "aside.JPG"
    os.rename(gone, aside)
    refused("a photo missing from its folder", ["--shoots", "s1", "s2"], "is not where the backup's records say it is")
    os.rename(aside, gone)
    # one join at a time on this computer
    import this_computer
    (w["home"]).mkdir(exist_ok=True)
    with open(w["home"] / "shoot-files.lock", "ab") as f:
        got = this_computer.try_lock(f)
        if got:
            refused("while another rename or join holds the lock", ["--shoots", "s1", "s2"], "A rename or a join is already at work.")
            before = listing(w["drive"])
            code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Aurora", env=dict(w["env"], STUDIO_RENAME_WAIT_FOR_TESTS="1"))
            check("a rename asked while it is held waits its turn, then says so and changes nothing",
                  code == 1 and "A rename or a join is already at work." in out and listing(w["drive"]) == before, out)
            code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Beach", env=dict(w["env"], STUDIO_SHOOT_LOCK_HELD="1"))
            check("the job that holds the lock can still run a rename itself", code == 0 and "Nothing to do" in out, out)
            this_computer.unlock(f)
    # photos that keep the camera's names: two frames with one name would land on one file
    code, out = join(w, b, "--shoots", "s1", "s2")
    check("and with nothing in the way the same join goes through", code == 0 and "Joined." in out, out)

    print("Something of theirs in the other folder: it stays, and so does that folder")
    theirs = w["drive"] / "Garden_06-04-26" / "contract.pdf"
    theirs.write_bytes(b"theirs")
    (w["drive"] / "Garden_06-04-26" / ".DS_Store").write_bytes(b"finder")
    code, out = join(w, b, "--shoots", "s1", "s3")
    check("the join goes through, and says the folder is still there because of what is in it",
          code == 0 and "Garden_06-04-26 is still there because it has things in it that I didn't put there" in out, out)
    check("their file was not touched, and its folder (with the computer's own note in it) was not removed",
          theirs.read_bytes() == b"theirs" and sorted(os.listdir(w["drive"] / "Garden_06-04-26")) == [".DS_Store", "contract.pdf"],
          os.listdir(w["drive"] / "Garden_06-04-26"))
    records_right(w, b, "after it", ["s1"])


def letters(work):
    print("A name that differs only in its capitals, and photos that keep the camera's names")
    w, b = world(work, "case", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        code, out = join(w, b, "--shoots", "s1", "s2", "--name", "beach")
        names = [x for x in os.listdir(w["drive"]) if not x.startswith(".")]
        check("the joined shoot takes the name in the new capitals, read from the drive's own listing",
              code == 0 and names == ["beach_06-04-26"], out + str(names))
        got = sorted(os.listdir(w["drive"] / "beach_06-04-26"))
        check("and so do its photos", got == [f"beach_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 7)], got)
        records_right(w, b, "after it", ["s1"])
    w, b = world(work, "keep", groups=(3, 3), shoots=("Beach", "Palms"), file_names="original")
    if b:
        code, out = join(w, b, "--shoots", "s1", "s2")
        got = sorted(os.listdir(w["drive"] / "Beach_06-04-26")) if (w["drive"] / "Beach_06-04-26").is_dir() else []
        check("photos that keep the camera's names keep them through a join", code == 0 and got == [f"IMG_{4470 + n}.JPG" for n in range(1, 7)], out + str(got))
        records_right(w, b, "after it", ["s1"])


def cut_off(work):
    print("Cut off at each point, as a power cut would, then run again")
    points = ["after-log", "moves:1", "moves:4", "moves:9", "before-take-down", "before-name", "after-name", "before-records", "after-records"]
    for i, point in enumerate(points):
        w, b = world(work, f"cut{i}")
        if not b:
            continue
        st = b["records"]
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_CUT_FOR_TESTS=point)
        log = jread(st / "join-log.json", {})
        e = (log.get("joins") or [{}])[0]
        check(f"cut at {point}: it stopped dead, with the whole plan already in the log (written before the first move)",
              code == 70 and len(e.get("moves", [])) == 9 and not e.get("finished"), f"{code} {out[-300:]}")
        import join_shoots
        check(f"cut at {point}: the backup counts as having an unfinished join (so nothing settles on top of it)", join_shoots.unfinished(st))
        every = [p for p in w["drive"].rglob("*.JPG") if ".studio" not in p.parts]
        check(f"cut at {point}: no photo was lost or doubled on the way (12 on the drive)", len(every) == 12, len(every))
        # the next run of anything that touches these shoots finishes it: the join itself, --finish, or a rename
        how = i % 3
        if how == 0:
            code, out = join(w, b, "--shoots", "s1", "s2")
        elif how == 1:
            code, out = join(w, b, "--finish")
        else:
            code, out = t.run("rename_shoot.py", st, "--shoot", "s3", "--name", "Garden", env=w["env"])
        check(f"cut at {point}: the next run ({['the same join', '--finish', 'a rename of another shoot'][how]}) finishes it (exit 0)",
              code == 0 and "Finishing a join that was cut off" in out, out)
        got = [x for x in listing(w["drive"]) if x.endswith(".JPG") and x.startswith("Beach")]
        check(f"cut at {point}: the joined shoot is whole and in order", got == [f"Beach_06-04-26/Beach_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 10)], got)
        check(f"cut at {point}: no gathering folder and no emptied folder left",
              sorted(x for x in os.listdir(w["drive"]) if not x.startswith(".")) == ["Beach_06-04-26", "Garden_06-04-26"], os.listdir(w["drive"]))
        records_right(w, b, f"cut at {point}", ["s1", "s3"])
        e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
        check(f"cut at {point}: the log is finished, every file checked, no problems; nothing waits any more",
              e.get("finished") and e.get("verified") == 9 and not e.get("problems") and not join_shoots.unfinished(st),
              {k: v for k, v in e.items() if k != "moves"})


def unprovable(work):
    print("When identity cannot prove a file, it is read in full")
    w, b = world(work, "noident", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_NO_IDENT_FOR_TESTS="1")
        e = (jread(b["records"] / "join-log.json", {}).get("joins") or [{}])[0]
        check("a drive that numbers no file: every moved file is read in full against its hash, and passes",
              code == 0 and e.get("hashed_in_full") == 6 and e.get("verified") == 6 and "(6 read in full)" in out, out)
        records_right(w, b, "after it", ["s1"])
    w, b = world(work, "deep", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        code, out = join(w, b, "--shoots", "s1", "s2", "--deep")
        check("--deep reads every file in full too", code == 0 and "(6 read in full)" in out, out)
    w, b = world(work, "changed", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        st = b["records"]
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_CUT_FOR_TESTS="after-name")
        bad = w["drive"] / "Beach_06-04-26" / "Beach_0005_IMG_4475.JPG"
        data = bytearray(bad.read_bytes())
        data[-20] ^= 0xFF
        bad.write_bytes(bytes(data))        # a different file under the right name: its identity no longer matches
        code, out = join(w, b, "--finish")
        e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
        check("a file that is not the one that was moved is caught (identity fails, the full read does not match): exit 1, said, never a pass",
              code == 1 and "not the same file after the join: Beach_06-04-26/Beach_0005_IMG_4475.JPG" in out and e.get("verified") == 5
              and len(e.get("problems", [])) == 1, out)
        import join_shoots
        check("and the backup keeps counting as having a join with a problem", join_shoots.unfinished(st))
    w, b = world(work, "nohash", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        st = b["records"]
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_CUT_FOR_TESTS="after-name", STUDIO_JOIN_NO_IDENT_FOR_TESTS="1")
        log = jread(st / "join-log.json")
        log["joins"][0]["moves"][2]["sha256"] = ""
        (st / "join-log.json").write_text(json.dumps(log), encoding="utf-8")
        code, out = join(w, b, "--finish")
        check("a file with neither identity nor a hash to prove it is a problem, never a pass", code == 1 and "no hash to check against" in out, out)


def with_clips(work):
    print("Photos joined to video clips")
    import clips_check
    w = r.new_world(work, "clips")
    w["drive"] = r.new_drive(w, "Big Kahuna", 2000)
    t.run("studio_file.py", "set", "--drive", w["drive"], "--offered", "1", "--file-names", "shoot", env=w["env"])
    card = w["base"] / "CARD"
    t.make_card(card, groups=(4,))
    d = card / "DCIM" / "100CANON"
    start = datetime(2026, 6, 4, 9, 0, 0).astimezone() + timedelta(minutes=50)
    for i in range(3):
        clips_check.clip_at(d / f"MVI_{9001 + i}.MP4", start + timedelta(minutes=2 * i))
    before = t.card_snapshot(card)
    night = ["night.py", "--source", card, "--name", "clip card", "--date", r.DAY1, "--no-peeks"]
    code, out = t.run(*night, env=w["env"])
    st = w["drive"] / f"{r.DAY1} clip card" / "_studio"
    if code != 4:
        check("the pretend backup with clips reaches the look", False, out)
        return
    groups = jread(st / "groups.json")["groups"]
    rows = [{"id": f"s{i}", "suggested": ["Garcia", "Film"][i - 1], "groups": [g["id"]], "photos": g.get("count", 0), "recap": "Test.", "why": "test"}
            for i, g in enumerate(groups, 1)]
    (st / "shoots.json").write_text(json.dumps({"decided_by": "test", "shoots": rows}), encoding="utf-8")
    code, out = t.run(*night, env=w["env"])
    records = w["drive"] / ".studio" / f"{r.DAY1} clip card"
    b = {"records": records, "card": card, "before": before}
    flat = sorted(x for x in os.listdir(w["drive"]) if not x.startswith("."))
    check("before: a shoot of photos and a shoot of clips, each one flat folder", code == 0 and len(groups) == 2 and flat == ["Film_06-04-26", "Garcia_06-04-26"], out[-400:] + str(flat))
    code, out = join(w, b, "--all", "--name", "Garcia")
    got = listing(w["drive"])
    want = (["Garcia_06-04-26", "Garcia_06-04-26/Photos"] + [f"Garcia_06-04-26/Photos/Garcia_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 5)]
            + ["Garcia_06-04-26/Videos"] + [f"Garcia_06-04-26/Videos/Garcia_{n:04d}_MVI_{9000 + n}.MP4" for n in range(1, 4)])
    check("joined, the photos are in Photos and the clips in Videos, each numbered from 0001", code == 0 and got == want, out + str(got))
    check("and the count never calls a clip a photo", "4 photos and 3 video clips" in out, out)
    bad, n = t.photos_match(w["drive"], jread(records / "index.json"), card)
    check(f"every photo and clip is the card's, byte for byte ({n})", not bad and n == 7, bad)
    check("the card is exactly as it was", t.card_snapshot(card) == before)
    sh = jread(records / "shoots.json")["shoots"]
    check("one shoot, whose folder on record is its top folder", len(sh) == 1 and sh[0]["folder"] == "Garcia_06-04-26", sh)
    code, out = t.run("rename_shoot.py", records, "--shoot", "s1", "--name", "Reyes", env=w["env"])
    got = listing(w["drive"])
    check("and it renames afterwards with Photos and Videos inside",
          code == 0 and "Reyes_06-04-26/Photos/Reyes_0004_IMG_4474.JPG" in got and "Reyes_06-04-26/Videos/Reyes_0003_MVI_9003.MP4" in got, out + str(got))


def review_fixes(work):
    print("A second join into a folder that keeps its name, with the Mac's hidden note written again")
    w, b = world(work, "twice-note")
    if b:
        st = b["records"]
        (w["drive"] / "Beach_06-04-26" / ".DS_Store").write_bytes(b"first note")
        code, out = join(w, b, "--shoots", "s1", "s2")
        check("the first join finishes and sets the note aside", code == 0 and (st / "from-joined" / "Beach_06-04-26" / ".DS_Store").read_bytes() == b"first note", out)
        (w["drive"] / "Beach_06-04-26" / ".DS_Store").write_bytes(b"second note")      # as Finder does when they open the folder
        code, out = join(w, b, "--shoots", "s1", "s3")
        check("the second join into the same folder finishes too (exit 0), never stuck behind the note", code == 0 and "Joined." in out, out)
        aside = st / "from-joined" / "Beach_06-04-26"
        check("both notes are kept in the records, the first one never written over",
              (aside / ".DS_Store").read_bytes() == b"first note" and (aside / ".DS_Store (2)").is_file()
              and (aside / ".DS_Store (2)").read_bytes() == b"second note", sorted(os.listdir(aside)) if aside.is_dir() else None)
        check("one folder on the drive, all twelve photos in it, no gathering folder",
              sorted(x for x in os.listdir(w["drive"]) if not x.startswith(".")) == ["Beach_06-04-26"]
              and sorted(os.listdir(w["drive"] / "Beach_06-04-26")) == [f"Beach_{n:04d}_IMG_{4470 + n}.JPG" for n in range(1, 13)],
              listing(w["drive"]))
        records_right(w, b, "after the second join", ["s1"])
        import join_shoots
        check("and nothing is left waiting", not join_shoots.unfinished(st) and join_shoots.half_done(st) is None)

    print("Their own sidecar, saved again by their editing program between a cut-off join and its finish")
    w, b = world(work, "sidecar-saved")
    if b:
        import join_shoots
        st = b["records"]
        xmp = w["drive"] / "Palms_06-04-26" / "Palms_0002_IMG_4477.xmp"
        xmp.write_bytes(b"<x:xmpmeta>first edit</x:xmpmeta>")
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_CUT_FOR_TESTS="moves:3")
        now_at = [p for p in w["drive"].rglob("*.xmp") if ".studio" not in p.parts]
        check("cut off part way; the sidecar is somewhere on the drive", code == 70 and len(now_at) == 1, f"{code} {now_at}")
        if now_at:
            now_at[0].write_bytes(b"<x:xmpmeta>a second, longer edit, saved while the join was cut off</x:xmpmeta>")
        code, out = join(w, b, "--finish")
        e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
        check("the finish ends clean (exit 0): a sidecar they saved again is theirs, never a problem",
              code == 0 and e.get("finished") and not e.get("problems") and e.get("verified") == 10, out)
        moved = w["drive"] / "Beach_06-04-26" / "Beach_0007_IMG_4477.xmp"
        check("the sidecar is beside its photo under its new name, holding what they saved last",
              moved.is_file() and b"second, longer edit" in moved.read_bytes(), listing(w["drive"]))
        check("the log notes it was saved again, and the plan's own hash is kept as it was",
              [m.get("saved_again") is not None for m in e.get("moves", []) if m.get("kind") == "sidecar"] == [True], e.get("moves", [])[-3:])
        check("nothing waits: the backup may settle, and no later run has anything to finish", not join_shoots.unfinished(st) and join_shoots.half_done(st) is None)
        q = jread(w["home"] / "queue.json", {})
        mine = [x for x in q.get("shoots", []) if Path(x.get("studio", "")).resolve() == Path(st).resolve()]
        check("the editing queue's list shows the joined shoot and no longer the joined-away one",
              sorted(x["shoot"] for x in mine) == ["s1", "s3"] and next(x for x in mine if x["shoot"] == "s1").get("count") == 9, mine)
        records_right(w, b, "after it", ["s1", "s3"])

    print("A join that ends with a real problem at its check")
    w, b = world(work, "real-problem")
    if b:
        import join_shoots
        st = b["records"]
        code, out = join(w, b, "--shoots", "s1", "s2", STUDIO_JOIN_CUT_FOR_TESTS="moves:3")
        hurt = w["drive"] / "Beach_06-04-26 (joining)" / "Beach_0002_IMG_4472.JPG"
        good = hurt.read_bytes() if hurt.is_file() else b""
        check("cut off part way, with a photo in the gathering folder", code == 70 and bool(good), f"{code} {listing(w['drive'])}")
        hurt.write_bytes(good + b" damaged")                    # the photo is no longer the file the plan named
        code, out = join(w, b, "--finish")
        e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
        check("the finish stops loudly (exit 1) with the problem on record", code == 1 and "PROBLEMS" in out and "not the same file after the join" in out
              and e.get("finished") and len(e.get("problems", [])) == 1, out)
        check("nothing settles on top of it", join_shoots.unfinished(st))
        sh = [s_["id"] for s_ in jread(st / "shoots.json", {}).get("shoots", [])]
        q = jread(w["home"] / "queue.json", {})
        mine = [x for x in q.get("shoots", []) if Path(x.get("studio", "")).resolve() == Path(st).resolve()]
        check("the records say where the files are (two shoots now), and the editing queue's list follows them: no shoot is listed in a folder that is gone",
              sh == ["s1", "s3"] and sorted(x["shoot"] for x in mine) == ["s1", "s3"]
              and all(Path(x["folder"]).is_dir() for x in mine) and next(x for x in mine if x["shoot"] == "s1").get("count") == 9, mine)
        code, out = join(w, b, "--finish")
        check("asked again, it still says so (exit 1): a problem is never quietly called finished", code == 1 and "No join is waiting" not in out, out)
        check("a join that ended with a problem does not stand in the way of the next rename", join_shoots.half_done(st) is None)
        code, out = t.run("rename_shoot.py", st, "--shoot", "s3", "--name", "Orchard", env=w["env"])
        check("another shoot of the backup can still be renamed", code == 0 and (w["drive"] / "Orchard_06-04-26").is_dir(), out)
        # the joined shoot is renamed on; the old join's entry must never write its own places back over the records
        code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Family", env=w["env"])
        index_then = (st / "index.json").read_bytes()
        check("so can the joined shoot itself", code == 0 and (w["drive"] / "Family_06-04-26").is_dir(), out)
        code, out = join(w, b, "--finish")
        check("looking at the old join again changes no record (the shoot has moved on since)", (st / "index.json").read_bytes() == index_then and code == 1, out)
        t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Beach", env=w["env"])
        (w["drive"] / "Beach_06-04-26" / "Beach_0002_IMG_4472.JPG").write_bytes(good)     # the photo is put right
        code, out = join(w, b, "--finish")
        e = (jread(st / "join-log.json", {}).get("joins") or [{}])[0]
        check("once every file checks out the problem is cleared (exit 0), what it was kept in the log, and nothing waits any more",
              code == 0 and "checks out now" in out and not e.get("problems") and e.get("problems_were") and not join_shoots.unfinished(st), out)

    print("A rename where two photos share one sidecar (a RAW and its JPEG), camera names kept")
    make = t.make_card

    def with_twins(card, groups=(8,)):
        make(card, groups=groups)
        d = card / "DCIM" / "100CANON"
        shutil.copy2(d / "IMG_4471.JPG", d / "IMG_4471.jpeg")
    t.make_card = with_twins
    try:
        w, b = world(work, "twins", groups=(3, 3), shoots=("Beach", "Palms"), file_names="original")
    finally:
        t.make_card = make
    if b:
        st = b["records"]
        folder = w["drive"] / "Beach_06-04-26"
        check("the shoot holds both photos of the pair", {"IMG_4471.JPG", "IMG_4471.jpeg"} <= set(os.listdir(folder)), os.listdir(folder))
        (folder / "IMG_4471.xmp").write_bytes(b"<x:xmpmeta>one sidecar for the pair</x:xmpmeta>")
        code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Kat", env=w["env"])
        new = w["drive"] / "Kat_06-04-26"
        check("the rename goes through (exit 0), the one sidecar planned once", code == 0 and "All done." in out and new.is_dir(), out)
        check("both photos and their sidecar are in the renamed folder under the camera's names",
              new.is_dir() and {"IMG_4471.JPG", "IMG_4471.jpeg", "IMG_4471.xmp"} <= set(os.listdir(new))
              and (new / "IMG_4471.xmp").read_bytes() == b"<x:xmpmeta>one sidecar for the pair</x:xmpmeta>", os.listdir(new) if new.is_dir() else None)
        e = (jread(st / "rename-log.json", {}).get("renames") or [{}])[-1]
        check("the log has the sidecar once, and no problem", [m["from"] for m in e.get("moves", [])].count("Beach_06-04-26/IMG_4471.xmp") == 1 and not e.get("problems"), e.get("problems"))

    print("Their own sidecar, saved again between a cut-off rename and its finish")
    w, b = world(work, "rename-sidecar", groups=(3, 3), shoots=("Beach", "Palms"))
    if b:
        st = b["records"]
        (w["drive"] / "Beach_06-04-26" / "Beach_0001_IMG_4471.xmp").write_bytes(b"<x:xmpmeta>first</x:xmpmeta>")
        code, out = t.run("rename_shoot.py", st, "--shoot", "s1", "--name", "Aurora", env=w["env"])
        # put the rename back to "cut off before this sidecar was checked", then save the sidecar again
        log = jread(st / "rename-log.json")
        e = log["renames"][-1]
        e.pop("finished", None)
        for m in e["moves"]:
            m.pop("checked", None)
        (st / "rename-log.json").write_text(json.dumps(log), encoding="utf-8")
        xmp = w["drive"] / "Aurora_06-04-26" / "Aurora_0001_IMG_4471.xmp"
        check("the sidecar travelled with its photo", code == 0 and xmp.is_file(), out)
        xmp.write_bytes(b"<x:xmpmeta>saved again, longer than before</x:xmpmeta>")
        code, out = t.run("rename_shoot.py", st, "--shoot", "s2", "--name", "Palms", env=w["env"])
        e = jread(st / "rename-log.json")["renames"][-1]
        check("the finish ends clean: their sidecar as they saved it is not a problem", code == 0 and e.get("finished") and not e.get("problems"), out + str(e.get("problems")))


def settle_waits(work):
    print("A backup does not settle on top of an unfinished join")
    sys.path.insert(0, str(t.SCRIPTS))
    import settle
    d = work / "gate" / "_studio"
    d.mkdir(parents=True)
    (d / "sort-log.json").write_text(json.dumps({"moves": [], "verified": 0, "problems": []}), encoding="utf-8")
    check("with no join on record the gate is open", settle.gates(d) is None, settle.gates(d))
    (d / "join-log.json").write_text(json.dumps({"joins": [{"ids": ["s1", "s2"], "moves": []}]}), encoding="utf-8")
    check("an unfinished join closes it", settle.gates(d) == "a join of two shoots is unfinished or had problems", settle.gates(d))
    (d / "join-log.json").write_text(json.dumps({"joins": [{"ids": ["s1", "s2"], "moves": [], "finished": "x", "problems": ["p"]}]}), encoding="utf-8")
    check("so does one that finished with a problem", settle.gates(d) is not None)
    (d / "join-log.json").write_text(json.dumps({"joins": [{"ids": ["s1", "s2"], "moves": [], "finished": "x", "problems": []}]}), encoding="utf-8")
    check("a finished, clean join opens it again", settle.gates(d) is None)


def second_copy_follows(work):
    print("The second copy is asked to follow (lane B's second_copy.follow), and its absence stops nothing")
    w, b = world(work, "follow", groups=(3, 3), shoots=("Beach", "Palms"))
    if not b:
        return
    # a stand-in second_copy that only notes it was asked, in a folder ahead of the scripts on the path
    stub = w["base"] / "stub"
    stub.mkdir()
    (stub / "sitecustomize.py").write_text(
        "import sys, os\n"
        "class _F:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        return None\n"
        "def _patch():\n"
        "    try:\n"
        "        import second_copy\n"
        "    except Exception:\n"
        "        return\n"
        "    def follow(records):\n"
        "        open(os.environ['FOLLOW_NOTE'], 'a').write(str(records) + '\\n')\n"
        "    second_copy.follow = follow\n"
        "sys.path.insert(0, os.environ['SCRIPTS_FOR_STUB'])\n"
        "_patch()\n", encoding="utf-8")
    note = w["base"] / "follow.txt"
    env = {"PYTHONPATH": str(stub), "FOLLOW_NOTE": str(note), "SCRIPTS_FOR_STUB": str(t.SCRIPTS)}
    code, out = join(w, b, "--shoots", "s1", "s2", **env)
    asked = note.read_text(encoding="utf-8").splitlines() if note.exists() else []
    check("after a join, second_copy.follow is called with this backup's records", code == 0 and [Path(x).resolve() for x in asked] == [Path(b["records"]).resolve()], out + str(asked))
    code, out = t.run("rename_shoot.py", b["records"], "--shoot", "s1", "--name", "Aurora", env=dict(w["env"], **env))
    asked = note.read_text(encoding="utf-8").splitlines() if note.exists() else []
    check("and after a rename", code == 0 and len(asked) == 2, out + str(asked))


def main():
    work = Path(tempfile.mkdtemp(prefix="join-shoots-check-"))
    parts = [plain, refusals, letters, cut_off, unprovable, with_clips, review_fixes, settle_waits, second_copy_follows]
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None     # e.g. --only refusals,cut_off
    try:
        for part in parts:
            if not only or part.__name__ in only:
                part(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{N[0] - len(FAILED)} of {N[0]} passed" + (f"; FAILED: {len(FAILED)}" if FAILED else ""))
    for f in FAILED:
        print("  FAILED: " + f)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
