#!/usr/bin/env python3
"""Rename a shoot that the sorter has already placed: the folder and every
photo in it take their name, keeping the running number and the original
filename. This is their one decision on the first look, made real.

    python3 rename_shoot.py "<session>" --shoot s2 --name "Brittan sunset palms"
    python3 rename_shoot.py "<session>" --from-names        apply _studio/names.json to every shoot whose name differs
    ...  --dry-run                                           show the plan, touch nothing

Same promises as the sorter: only the copy on their drive, never the card;
a destination that exists stops it; renames on the same drive only; every
move written to _studio/rename-log.json before it happens; every renamed
photo re-read against the backup's hash for its original frame. The
`original` path kept in index.json is what makes this safe to do any
number of times.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sort import safe_folder, slug, sha256_of, load, say  # noqa: E402
import studio_file  # noqa: E402
from sneak_peeks import TOOL as STUDIO_TOOL  # noqa: E402
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

NUMBERED = re.compile(r"^(?P<prefix>.+?)_(?P<n>\d{4})_(?P<orig>.+)$")


def on_disk(p):
    """True only when a file (or folder) by exactly this name, letter for letter, is in its folder. The drive
    may ignore upper and lower case, so Path.exists() says yes to "black-sand-beach_0001.CR2" when the file on
    disk is "Black-sand-beach_0001.CR2"; this does not. A Mac's older drives (Mac OS Extended) store an
    accented letter in pieces (the é of "Côte" as e plus an accent) and list it that way, so on a Mac the two
    spellings of the same letter count as the same; a PC's drives keep a name exactly as it was written."""
    try:
        names = os.listdir(p.parent)
    except OSError:
        return False
    if p.name in names:
        return True
    if this_computer.WINDOWS:  # unproven on a real PC
        return False
    want = unicodedata.normalize("NFC", p.name)
    return any(unicodedata.normalize("NFC", n) == want for n in names)


def top(rel):
    """The shoot's own folder, from a file's place in the records: the first folder on the way. A shoot with
    photos and clips keeps them in Photos and Videos inside it (Dustin, Nov 11), so a file's own folder is not
    always the shoot's; a shoot of one kind is flat, and this is then the file's folder, as it always was."""
    return Path(Path(rel).parts[0])


def inside(rel):
    """A file's place inside its shoot's folder: "Photos/Smith_0001_IMG_1.CR3", or just its name in a flat shoot."""
    return Path(*Path(rel).parts[1:])


def same_text(a, b):
    """Two paths spelled exactly alike, letter for letter. On a PC, Python's own path comparison ignores upper
    and lower case (as the drive does), which would hide a rename that only changes the case; this never does.
    On a Mac it is the same as comparing the paths, as before."""
    return Path(a).as_posix() == Path(b).as_posix()


def studio_wrote(sidecar):
    """True for a sidecar the Studio itself wrote (the sneak-peek keyword), by its own signature."""
    try:
        return STUDIO_TOOL in sidecar.read_text(errors="replace", encoding="utf-8")
    except OSError:
        return False


def follow_sneak_peeks(studio, new_path):
    """After a rename, the sneak-peeks list and their report previews follow the photos to their new names."""
    pj = studio / "sneak-peeks.json"
    if not pj.exists():
        return
    try:
        d = json.loads(pj.read_text(encoding="utf-8"))
    except ValueError:
        return
    changed = False
    for pk in d.get("picks", []):
        to = new_path.get(pk.get("file"))
        if not to:
            continue
        old_pv = studio / "sneak-peeks" / (Path(pk["file"]).stem + ".jpg")
        new_pv = studio / "sneak-peeks" / (Path(to).stem + ".jpg")
        if on_disk(old_pv) and not same_text(old_pv, new_pv) and (not new_pv.exists() or case_twin(old_pv, new_pv)):
            try:
                this_computer.rename(old_pv, new_pv)
            except OSError:  # only the report's small copy; the photo and its record matter, and they move on
                pass
        pk["file"] = to
        changed = True
    if changed:
        pj.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def case_twin(a, b):
    """a and b are the same path apart from upper and lower case: on this kind of drive, the same file,
    and renaming one to the other just changes the letters."""
    return not same_text(a, b) and a.as_posix().lower() == b.as_posix().lower()


def plan_rename(session, studio, shoot_id, new_name):
    manifest = load(studio, "manifest.json")
    index = load(studio, "index.json")
    sh = load(studio, "shoots.json")
    shoot = next((s for s in sh["shoots"] if s["id"] == shoot_id), None)
    if not shoot:
        sys.exit(f"STOP: no shoot {shoot_id} in shoots.json.")
    if not shoot.get("folder"):
        sys.exit(f"STOP: {shoot_id} has not been sorted yet; run sort.py first.")
    old_folder = Path(shoot["folder"])
    if len(old_folder.parts) != 1:
        sys.exit(f"STOP: {shoot_id}'s folder is recorded as {old_folder}, which is not a shoot folder I made. Nothing renamed.")
    # their naming, from the Studio File: folder pattern, and whether photos keep their frame names
    naming = studio_file.load().get("naming", {})
    keep_names = naming.get("file_names", "shoot") == "original"
    in_folder = [p for p in index["photos"] if old_folder in Path(p["file"]).parents and p.get("original")]
    shoot_date = min((p["taken"] for p in in_folder if p.get("taken")), default=None)
    new_folder = Path(safe_folder(studio_file.render(naming, new_name, shoot_date)) if naming.get("folder_pattern") and shoot_date else safe_folder(new_name))
    prefix = slug(new_name)
    if not (session / old_folder).is_dir():
        sys.exit(f"STOP: the folder {old_folder} is not there. Nothing renamed.")
    if not same_text(new_folder, old_folder) and (session / new_folder).exists() and not case_twin(session / old_folder, session / new_folder):
        sys.exit(f"STOP: a folder named {new_folder} already exists. Nothing renamed.")

    files = manifest["files"]
    listings = {}

    def names_in(folder):
        """The names in one folder of the shoot, by their lower-case spelling (read once per folder)."""
        if folder not in listings:
            try:
                listings[folder] = {n.lower(): n for n in os.listdir(session / folder)}
            except OSError:
                listings[folder] = {}
        return listings[folder]

    moves = []
    for p in in_folder:
        cur = Path(p["file"])
        into = new_folder / inside(cur).parent   # the same place inside the shoot (Photos, Videos, or the top)
        rec = files.get(p["original"])
        if not rec or not rec.get("sha256"):
            sys.exit(f"STOP: no verified record for {p['original']}. Nothing renamed.")
        if keep_names:
            # photos keep their frame names; only the folder changes
            new = into / cur.name
            sidecar_name = lambda ext: cur.with_suffix(ext).name  # noqa: E731
        else:
            m = NUMBERED.match(cur.name)
            if not m:
                sys.exit(f"STOP: {cur.name} is not in the sorter's naming; will not guess. Nothing renamed.")
            new = into / f"{prefix}_{m['n']}_{m['orig']}"
            sidecar_name = lambda ext, m=m: f"{prefix}_{m['n']}_{Path(m['orig']).stem}{ext}"  # noqa: E731
        moves.append({"from": p["file"], "to": new.as_posix(), "original": p["original"], "sha256": rec["sha256"]})
        # the sidecar, if the sorter brought one along: once, by the record the backup verified
        # (the drive ignores upper and lower case, so .xmp and .XMP on disk are one file)
        for ext in (".xmp", ".XMP"):
            sc = cur.with_suffix(ext)
            so = Path(p["original"]).with_suffix(ext).as_posix()
            if so in files and (session / sc).exists():
                if not files[so].get("sha256"):
                    sys.exit(f"STOP: no verified record for {so}. Nothing renamed.")
                moves.append({"from": sc.as_posix(), "to": (into / sidecar_name(ext)).as_posix(),
                              "original": so, "sha256": files[so]["sha256"]})
                break
        else:
            # a sidecar the Studio wrote itself (the sneak-peek keyword) is not in the backup's records;
            # it travels along too, checked against its own hash, so Lightroom keeps pairing it with the photo.
            # Found by name regardless of case, since an older rename could leave its case behind the photo's.
            found = names_in(cur.parent).get((cur.stem + ".xmp").lower())
            if found:
                sc = cur.parent / found
                if studio_wrote(session / sc):
                    moves.append({"from": sc.as_posix(), "to": (into / sidecar_name(Path(found).suffix)).as_posix(),
                                  "original": None, "sha256": sha256_of(session / sc), "studio": True})
    if not moves:
        sys.exit(f"STOP: no sorted photos found in {old_folder}. Nothing renamed.")
    dests = [x["to"].lower() for x in moves]
    if len(set(dests)) != len(dests):
        sys.exit("STOP: two files would get the same new name. Nothing renamed.")
    # nothing may be in the way before the first move happens, so a rename never stops halfway
    for x in moves:
        to_name, from_name = Path(x["to"]).name, Path(x["from"]).name
        if to_name.lower() != from_name.lower() and to_name.lower() in names_in(Path(x["from"]).parent):
            sys.exit(f"STOP: {to_name} is already in {Path(x['from']).parent}. Nothing renamed.")
    if same_text(new_folder, old_folder) and all(Path(x["to"]).name == Path(x["from"]).name for x in moves):
        return shoot, old_folder, new_folder, []
    # on a PC, a place longer than File Explorer can open would stop the rename part way: found now, before anything
    # moves. Three kinds of place: the new folder; each photo's new name in it; and, since the folder takes its new
    # name first, each photo's old name inside the renamed folder, where every photo sits for a moment (a longer
    # folder with a shorter prefix can pass the first two and fail there).
    long = [x["to"] for x in moves if this_computer.path_too_long(session / x["to"])]
    if not same_text(new_folder, old_folder):
        long += [(new_folder / inside(x["from"])).as_posix() for x in moves
                 if this_computer.path_too_long(session / new_folder / inside(x["from"]))]
    if this_computer.path_too_long(session / new_folder, folder=True):
        long.insert(0, new_folder.as_posix())
    # the report's small copies of the sneak peeks take the photos' new names too (follow_sneak_peeks), inside the
    # backup's records, which sit deeper than the photos: the Assistant's own files, held to what Python can make
    if this_computer.WINDOWS:  # unproven on a real PC
        to_of = {x["from"]: x["to"] for x in moves}
        try:
            picks = json.loads((studio / "sneak-peeks.json").read_text(encoding="utf-8")).get("picks", [])
        except (OSError, ValueError):
            picks = []
        for pk in picks:
            to = to_of.get(pk.get("file"))
            if to and this_computer.records_path_too_long(studio / "sneak-peeks" / (Path(to).stem + ".jpg")):
                long.append((studio / "sneak-peeks" / (Path(to).stem + ".jpg")).name)
    if long:
        say(f"  too long for this {this_computer.COMPUTER}: {long[0]}" + (f" (and {len(long) - 1} more)" if len(long) > 1 else ""))
        sys.exit(f"STOP: the new name would make a photo's place longer than {this_computer.FILES_APP} can open "
                 "(260 characters, counting the drive and every folder on the way). Nothing renamed. A shorter name fixes it.")
    return shoot, old_folder, new_folder, moves


def apply(session, studio, shoot, old_folder, new_folder, moves, new_name, dry):
    if not moves:
        say(f"{shoot['id']} is already named \"{new_name}\". Nothing to do.")
        return
    say(f"{shoot['id']}: \"{shoot.get('name') or shoot.get('suggested')}\"  ->  \"{new_name}\"")
    say(f"  {old_folder}/  ->  {new_folder}/   {len(moves)} files")
    say(f"  e.g. {Path(moves[0]['from']).name}  ->  {Path(moves[0]['to']).name}")
    if dry:
        say("  Dry run. Nothing renamed.")
        return
    log_path = studio / "rename-log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {"renames": []}
    entry = {"shoot": shoot["id"], "from_name": shoot.get("name"), "to_name": new_name,
             "started": datetime.now().isoformat(timespec="seconds"), "moves": moves, "verified": 0, "problems": []}
    log["renames"].append(entry)
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")

    t0 = time.time()
    # each file's identity on the drive before anything moves: a rename never rewrites bytes, so the
    # same inode, size and modified time at the new name proves it is the same file
    for m in moves:
        try:
            st = os.stat(session / m["from"])
            m["ident"] = [st.st_ino, st.st_size, st.st_mtime_ns]
        except OSError:
            m["ident"] = None
    folder_moved = same_text(new_folder, old_folder)
    try:
        if not folder_moved:
            this_computer.rename(session / old_folder, session / new_folder)  # one atomic move of the whole folder
            folder_moved = True
        for m in moves:
            src = session / new_folder / inside(m["from"])
            dst = session / m["to"]
            if dst.exists() and not same_text(src, dst) and not case_twin(src, dst):
                entry["problems"].append(f"{m['to']} already exists; not overwritten")
                break
            if not same_text(src, dst):
                try:
                    this_computer.rename(src, dst)  # when only the letters' case changes, this changes just that
                except FileExistsError:  # a PC refuses a name that is there (a Mac is checked just above); unproven on a real PC
                    entry["problems"].append(f"{m['to']} already exists; not overwritten")
                    break
            m["moved"] = True
    except this_computer.HeldOpen as e:
        stopped(session, studio, log, log_path, entry, e, new_folder, moves, folder_moved)
    except OSError as e:
        failed(session, studio, log, log_path, entry, e, new_folder, moves, folder_moved)
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    say(f"  renamed in {time.time() - t0:.0f} s; checking every file is the same file it was...")
    t1 = time.time()
    hashed = 0
    for m in moves:
        dst = session / m["to"]
        if not on_disk(dst):
            entry["problems"].append(f"after the rename, {m['to']} is not there")
            continue
        same = False
        if m.get("ident") and m["ident"][0]:  # a drive that numbers no file (0) proves nothing by it
            st = os.stat(dst)
            same = [st.st_ino, st.st_size, st.st_mtime_ns] == m["ident"]
        if not same:  # could not prove it by identity: read it in full. Never a pass without one or the other.
            if not m["sha256"]:
                entry["problems"].append(f"no hash to check against: {m['to']}")
                continue
            if sha256_of(dst) != m["sha256"]:
                entry["problems"].append(f"hash mismatch after the rename: {m['to']}")
                continue
            hashed += 1
        entry["verified"] += 1
    entry["hashed_in_full"] = hashed
    say(f"  {entry['verified']} of {len(moves)} checked in {time.time() - t1:.0f} s" + (f" ({hashed} read in full)" if hashed else ""))

    write_records(session, studio, shoot["id"], new_folder, moves, new_name)
    entry["finished"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    if entry["problems"]:
        say("  PROBLEMS (every move is in rename-log.json):")
        for p in entry["problems"][:10]:
            say(f"    - {p}")
        sys.exit(1)
    update_queue(session, studio, shoot["id"], new_name, new_folder)
    say("  All done.")


def update_queue(session, studio, shoot_id, new_name, new_folder):
    """The editing queue shows the new name and folder too."""
    try:
        import edit_queue
        q = edit_queue.load()
        for x in q["shoots"]:
            if this_computer.same_place(x.get("studio") or "", studio) and x.get("shoot") == shoot_id:
                x["name"], x["folder"] = new_name, str(session / new_folder)
                edit_queue.save(q)
                edit_queue.write_page(q)
                break
    except Exception:  # noqa: BLE001  the queue is a convenience; the rename is done
        pass


def where_they_are(session, new_folder, moves):
    """Every file's true path after a rename: its new name if that move happened, else its old name
    inside the renamed folder. Records must say where files are, never where they were meant to be."""
    out = {}
    for m in moves:
        if m.get("moved") or on_disk(session / m["to"]):
            out[m["from"]] = m["to"]
        else:
            out[m["from"]] = (new_folder / inside(m["from"])).as_posix()
    return out


def write_records(session, studio, shoot_id, new_folder, moves, new_name=None):
    """The index, the groups, the sneak peeks and the shoot's folder follow the files to where they are now.
    With a new_name the rename is done: the shoot takes the name. Without one, a rename stopped part way
    (only once the folder itself has its new name): every file is recorded where it really is, and the shoot
    keeps its old name until the next run finishes the job."""
    new_path = where_they_are(session, new_folder, moves)
    # a rename that stopped part way recorded some photos in the renamed folder under their old names
    for m in moves:
        between = (new_folder / inside(m["from"])).as_posix()
        if between != m["from"]:
            new_path.setdefault(between, new_path[m["from"]])
    index = load(studio, "index.json")
    for p in index["photos"]:
        p["file"] = new_path.get(p["file"], p["file"])
    (studio / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    g = load(studio, "groups.json")
    for grp in g["groups"]:
        grp["files"] = [new_path.get(f, f) for f in grp["files"]]
    (studio / "groups.json").write_text(json.dumps(g, indent=1), encoding="utf-8")
    follow_sneak_peeks(studio, new_path)
    sh = load(studio, "shoots.json")
    for s in sh["shoots"]:
        if s["id"] == shoot_id:
            s["folder"] = new_folder.as_posix()
            if new_name is not None:
                s["name"] = new_name
    (studio / "shoots.json").write_text(json.dumps(sh, indent=1), encoding="utf-8")
    if new_name is not None:
        names = load(studio, "names.json", required=False) or {}
        names[shoot_id] = new_name
        (studio / "names.json").write_text(json.dumps(names, indent=1, ensure_ascii=False), encoding="utf-8")


def stopped(session, studio, log, log_path, entry, e, new_folder, moves, folder_moved):
    """A PC would not rename the folder or a photo because another program had something in it open
    (this_computer.HeldOpen). The log keeps every move and which ones happened; the entry stays unfinished, so
    the next run of this script finishes it before anything else. Never a problem in the log: it is not one."""
    entry.setdefault("stops", []).append({"when": datetime.now().isoformat(timespec="seconds"),
                                          "file": e.src, "detail": str(e)})
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    if folder_moved:
        write_records(session, studio, entry["shoot"], new_folder, moves)
    say(f"  stopped part way: the {this_computer.COMPUTER} would not rename {Path(e.src).name} ({e.cause}). "
        "Every move so far is in rename-log.json.")
    say(e.words)
    sys.exit(1)


FAILED = ("STOP: the rename stopped part way on something unexpected. Nothing is lost: every photo is still in the "
          "shoot's folder, and the backup's records say where each one is now.")


def failed(session, studio, log, log_path, entry, e, new_folder, moves, folder_moved):
    """A move failed for a reason that is not "another program has it open" and not "something is already there"
    (the drive went away, a name the drive will not take). Stop loudly, never guess (rule 2): the details go in the
    log, the records are written where the files really are (if the folder had already moved, so nothing names a
    folder that is gone), and the entry stays unfinished, so nothing settles and the next run tries to finish it."""
    entry.setdefault("stops", []).append({"when": datetime.now().isoformat(timespec="seconds"), "unexpected": True,
                                          "file": getattr(e, "filename", None), "detail": f"{e.__class__.__name__}: {e}"})
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    if folder_moved:
        write_records(session, studio, entry["shoot"], new_folder, moves)
    say(f"  stopped part way: {e.__class__.__name__}: {e}. Every move so far is in rename-log.json.")
    sys.exit(FAILED)


def resolve_phantoms(session, entry):
    """A phantom is a move an older version planned twice for one sidecar (it saw .xmp and .XMP as two
    files on a drive that ignores case). It never stood for a file of its own, but the old run may have
    written problems about it. A phantom is resolved only with proof: its real twin (same name, any case)
    was moved and checked, exactly one file by that name is on the drive, and that file's hash matches
    the backup's. Then the proof goes in the log and the problems that name only that phantom are
    dropped. Anything short of that and the problems stay. Returns True if the entry changed."""
    moves = entry.get("moves", [])
    phantoms = [m for m in moves if m.get("phantom") and not m.get("resolved")]
    if not phantoms:
        return False
    changed = False
    for ph in phantoms:
        twin = next((m for m in moves if not m.get("phantom") and m["to"].lower() == ph["to"].lower()), None)
        if not twin or not twin.get("moved") or not twin.get("checked") or not twin.get("sha256"):
            continue
        dst = session / twin["to"]
        try:
            on_disk = [n for n in os.listdir(dst.parent) if n.lower() == dst.name.lower()]
        except OSError:
            continue
        if on_disk != [dst.name] or sha256_of(dst) != twin["sha256"]:
            continue
        ph["resolved"] = {"when": datetime.now().isoformat(timespec="seconds"),
                          "why": "the same file as its twin on a drive that ignores case; never a file of its own",
                          "twin": twin["to"], "sha256_matched": twin["sha256"]}
        before = len(entry.get("problems", []))
        entry["problems"] = [p for p in entry.get("problems", []) if ph["to"] not in p]
        entry.setdefault("phantoms_resolved", []).append(
            {"phantom": ph["to"], "twin": twin["to"], "problems_cleared": before - len(entry["problems"]),
             "when": ph["resolved"]["when"]})
        changed = True
    return changed


def finish_unfinished(session, studio):
    """A rename that was cut off (power, a closed pipe, a file in the way) leaves its log entry without
    'finished', or with moves not marked moved. Every move is in that entry, so finish it: move what is
    still waiting under its old name (never over anything), verify every file, update the records.
    Runs before anything new."""
    log_path = studio / "rename-log.json"
    if not log_path.exists():
        return
    log = json.loads(log_path.read_text(encoding="utf-8"))
    for entry in log.get("renames", []):
        moves = entry["moves"]
        # a move planned twice for one file (an older version saw .xmp and .XMP as two files) is a phantom
        lower_to = [m["to"].lower() for m in moves]
        for m in moves:
            if not m.get("sha256") and lower_to.count(m["to"].lower()) > 1:
                m["phantom"] = True
        real = [m for m in moves if not m.get("phantom")]
        pending = [m for m in real if not m.get("moved")]
        if entry.get("finished") and not pending:
            if resolve_phantoms(session, entry):
                log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
                say(f"Cleared {len(entry['phantoms_resolved'])} sidecar(s) the old renamer counted twice "
                    f"({entry.get('to_name')}); each real one matched the backup.")
            continue
        say(f"Finishing a rename that was cut off: {entry.get('from_name')} -> {entry.get('to_name')}")
        new_folder = top(real[0]["to"]) if real else None
        old_folder = top(real[0]["from"]) if real else None
        # the old run's own notes about what it had not got to yet, and about phantoms, are not problems
        phantom_names = [m["to"] for m in moves if m.get("phantom")]
        entry["problems"] = [p for p in entry.get("problems", [])
                             if not p.startswith("after the rename, ") and not any(ph in p for ph in phantom_names)]
        entry["verified"] = 0
        folder_moved = bool(new_folder) and (same_text(new_folder, old_folder) or on_disk(session / new_folder))
        try:
            if new_folder and not folder_moved and on_disk(session / old_folder):
                # it stopped before the folder itself could take the new name (on a PC, something had a photo
                # in it open): the folder goes first, exactly as the first run would have done it
                if (session / new_folder).exists() and not case_twin(session / old_folder, session / new_folder):
                    entry["problems"].append(f"a folder named {new_folder} is in the way of {old_folder}; both left as they are")
                    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
                    say(f"  problems: {entry['problems'][-1:]}")
                    sys.exit(1)
                this_computer.rename(session / old_folder, session / new_folder)
                folder_moved = True
            for m in real:
                dst = session / m["to"]
                src = session / new_folder / inside(m["from"])
                if not m.get("moved") and on_disk(src) and not same_text(src, dst) and (not dst.exists() or case_twin(src, dst)):
                    this_computer.rename(src, dst)
                    m["moved"] = True
        except this_computer.HeldOpen as e:
            stopped(session, studio, log, log_path, entry, e, new_folder, real, folder_moved)
        except OSError as e:
            failed(session, studio, log, log_path, entry, e, new_folder, real, folder_moved)
        for m in real:
            dst = session / m["to"]
            src = session / new_folder / inside(m["from"])
            if on_disk(dst) and not (on_disk(src) and not same_text(src, dst)):
                m["moved"] = True
                if m.get("sha256") and sha256_of(dst) == m["sha256"]:
                    entry["verified"] += 1
                    m["checked"] = True
                else:
                    entry["problems"].append(f"could not verify {m['to']}")
            elif on_disk(src) and on_disk(dst):
                entry["problems"].append(f"{m['to']} is in the way of {src.name}; both left as they are")
            elif on_disk(src):
                entry["problems"].append(f"never moved: {m['from']}")
            else:
                entry["problems"].append(f"missing: {m['from']}")
        checked = {m["to"] for m in real if m.get("checked")}
        tail = " already exists; not overwritten"
        entry["problems"] = [q for q in entry["problems"] if not (q.endswith(tail) and q[:-len(tail)] in checked)]
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
        if new_folder:
            write_records(session, studio, entry["shoot"], new_folder, real, entry["to_name"])
        else:
            names = load(studio, "names.json", required=False) or {}
            names[entry["shoot"]] = entry["to_name"]
            (studio / "names.json").write_text(json.dumps(names, indent=1, ensure_ascii=False), encoding="utf-8")
        resolve_phantoms(session, entry)
        entry["finished"] = datetime.now().isoformat(timespec="seconds") + " (finished on a later run)"
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
        say(f"  {entry['verified']} of {len(real)} verified" + (f"; problems: {entry['problems'][:5]}" if entry["problems"] else ""))
        if entry["problems"]:
            sys.exit(1)
        if entry.get("stops") and new_folder:  # it stopped on a PC (a file held open) and is now done: the queue follows
            update_queue(session, studio, entry["shoot"], entry["to_name"], new_folder)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--shoot", help="shoot id from shoots.json, e.g. s2")
    ap.add_argument("--name", help="the new name")
    ap.add_argument("--from-names", action="store_true", help="apply _studio/names.json to every shoot whose name differs")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    from where import locate
    session, studio = locate(a.session)  # the folder the shoots sit in, and the records (before or after the night settles)
    finish_unfinished(session, studio)

    jobs = []
    if a.from_names:
        names = load(studio, "names.json", required=False) or {}
        sh = load(studio, "shoots.json")
        for s in sh["shoots"]:
            want = (names.get(s["id"]) or "").strip()
            if want and want != (s.get("name") or ""):
                jobs.append((s["id"], want))
        if not jobs:
            say("Every shoot already has the name the photographer gave it. Nothing to do.")
            return
    elif a.shoot and a.name:
        jobs.append((a.shoot, " ".join(a.name.split())))
    else:
        sys.exit("usage: --shoot <id> --name <name>, or --from-names")

    for shoot_id, new_name in jobs:
        shoot, old_folder, new_folder, moves = plan_rename(session, studio, shoot_id, new_name)
        apply(session, studio, shoot, old_folder, new_folder, moves, new_name, a.dry_run)


if __name__ == "__main__":
    main()
