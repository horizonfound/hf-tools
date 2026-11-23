#!/usr/bin/env python3
"""Join two or more shoots of ONE backup into one shoot folder (Nicole, Nov 23: "Joining two shoots into one,
and naming shoots after the backup: both needed for launch"; her "These are mini sessions. Keep them in one
folder.").

    python3 join_shoots.py "<backup>" --list                          this backup's shoots, by id
    python3 join_shoots.py "<backup>" --shoots s1 s2 [--name "Mini sessions"]
    python3 join_shoots.py "<backup>" --all [--name "Mini sessions"]  every shoot of the backup into one
    ...  --dry-run                                                     show the plan, touch nothing
    ...  --deep                                                        read every moved file in full afterwards

What it does: every photo and video clip of the chosen shoots goes into one folder, named for the joined shoot
the way their folders are named (the Studio File's pattern, dated by the earliest photo). The photos are numbered
on in shooting order across the whole joined shoot, each named <first word of the name>_<NNNN>_<the camera's own
name> (sort.prefix_for), or left under the camera's own name when that is how they keep them. A sidecar (.xmp)
travels with its photo under the same new stem. Photos and clips together become Photos and Videos inside the
folder, each numbered on its own; one kind only stays one flat folder.

The same promises as the sorter and the renamer, in code:

  - only the copy on their drive, never the card
  - the whole plan is checked before the first move: every source there, no two files landing on one name,
    nothing in the way (names are read from each folder's own listing, never a case-blind exists())
  - the log first: records/join-log.json holds every move, with each file's identity on the drive and its hash,
    before anything moves
  - moves are renames on the same drive only, never copy-and-delete; nothing is ever written over or deleted
  - every file goes first into a new folder nobody else has ("<the new name> (joining)"), so no file can land
    on another on the way; when all are in, the emptied shoot folders come down (only when truly empty; the
    computer's own hidden notes are set aside in the records, never deleted) and that folder takes its name
  - afterwards every moved file is proved the same file by its identity on the drive (inode, size, modified
    time), and read in full against its hash when identity cannot prove it. Nothing passes without one or the other
  - safe to run twice (the second run says "Already joined"); a run cut off at any point is finished by the next
    run of this script, of rename_shoot.py, or of the Name your shoots page's job, from the log
  - every record follows: index.json, groups.json, shoots.json (the joined-away shoots are kept under "joined"
    on the one that stays), names.json, the first-look picks and their small pictures, the editing queue's list

Not joined, and said so in plain words: shoots from two different backups (not built); a shoot that is in the
editing queue with a due date or already delivered, or that a post kit was made from (REFUSE_IF_IN_USE).

Exit codes: 0 joined (or already) · 1 stopped part way or problems (the log says how far; run again) ·
2 refused, nothing changed.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sort import safe_folder, prefix_for, sha256_of, load, say  # noqa: E402
from rename_shoot import on_disk, top, inside, same_text  # noqa: E402
import rename_shoot  # noqa: E402
import studio_file  # noqa: E402
import clips  # noqa: E402  (which files are video, the count in words, and the Photos and Videos folders)
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

LOG = "join-log.json"
STAGING_TAIL = " (joining)"      # the folder the joined shoot is gathered in until it can take its name
ASIDE = "from-joined"            # in the records: the computer's own hidden notes found in an emptied shoot folder
MINI_NAME = "Mini sessions"      # her mock-up's name for a joined card nobody named
STUCK_AFTER = 2                  # a join or rename that has stopped this many times is not "run it again": the Assistant looks
REFUSE_IF_IN_USE = True          # a shoot with a due date, delivered, or with a post kit made from it is not joined
HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
LOCK = HOME / "shoot-files.lock"  # one join (or one Name your shoots job) at a time on this computer
LOCK_HELD = "STUDIO_SHOOT_LOCK_HELD"   # set by the Name your shoots job for the scripts it runs: it holds the lock itself

# Our words (drafts for Dustin and Nicole): what a refusal says. Plain, no paths.
WORDS = {
    "need_two": "Joining needs two or more shoots.",
    "no_shoot": "I can't find a shoot called {id} in that backup.",
    "not_sorted": "{name} has not been put in its folder yet, so it can't be joined.",
    "not_verified": "That backup is not fully checked yet, so nothing is joined.",
    "in_queue": ("{name} is in your editing queue with a due date. Take it out of your queue first, then join them."),
    "delivered": "{name} is marked as delivered, so it stays its own shoot. Nothing was joined.",
    "has_kit": "You already made a post kit from {name}, so it stays its own shoot. Nothing was joined.",
    "name_taken": "There is already a folder called {folder} next to these shoots. Pick another name for the joined shoot.",
    "extras": ("{folder} has things in it that I didn't put there ({names}). Move them out, or give the joined shoot "
               "another name, and I'll join them."),
    "two_same": "Two photos would get the same name ({name}), so nothing was joined.",
    "no_record": "I have no checked record for {name}, so nothing was joined.",
    "missing": "{name} is not where the backup's records say it is, so nothing was joined.",
    "busy": "A rename or a join is already at work. Try again when it's done.",
    "second_copy": "A second copy of this backup is being made right now. Try this again when it's done.",
    "two_backups": "Those shoots came from two different backups. I can only join shoots from the same backup.",
    "too_long": ("The joined shoot's name would make a photo's place longer than {app} can open (260 characters, counting "
                 "the drive and every folder on the way). A shorter name fixes it."),
    "already": "Already joined: {name}. Nothing to do.",
    "left": "{folder} is still there because it has things in it that I didn't put there. Nothing in it was touched.",
}


class Stop(Exception):
    """Refused before anything moved. str() is plain words for the photographer."""


def now():
    return datetime.now().isoformat(timespec="seconds")


def write_json(path, obj):
    """Whole or not at all: a scratch name of this program's own, then put in place."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        this_computer.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()        # our own scratch copy, never the real file
        except OSError:
            pass
        raise


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def fold(name):
    """A name as a drive that ignores capitals and spells accents two ways would compare it."""
    return unicodedata.normalize("NFC", name).casefold()


def named_like(parent, name):
    """Every entry in `parent` a drive could take for `name`: read from the folder's own listing."""
    try:
        return [n for n in os.listdir(parent) if fold(n) == fold(name)]
    except OSError:
        return []


def cut_for_tests(point):
    """Tests only: stop dead at a named point, as a power cut would (nothing flushed, nothing tidied)."""
    if os.environ.get("STUDIO_JOIN_CUT_FOR_TESTS") == point:
        os._exit(70)


def shoot_name(s, names):
    return " ".join(str(names.get(s["id"]) or s.get("name") or s.get("suggested") or s["id"]).split())


def listing(studio):
    """[{id, name, folder, photos, clips}] for --list, the page and the chat."""
    sh = (read_json(Path(studio) / "shoots.json", {}) or {}).get("shoots") or []
    names = read_json(Path(studio) / "names.json", {}) or {}
    groups = {g["id"]: g for g in (read_json(Path(studio) / "groups.json", {}) or {}).get("groups") or []}
    out = []
    for s in sh:
        n_photos, n_clips = clips.count(f for g in s.get("groups", []) if g in groups for f in groups[g].get("files", []))
        out.append({"id": s["id"], "name": shoot_name(s, names), "folder": s.get("folder"), "photos": n_photos, "clips": n_clips})
    return out


# ---------------------------------------------------------------- what stands in the way

def in_use(studio, chosen, names):
    """Plain words for the first shoot that is in the editing queue with a due date, delivered, or has a post kit
    made from it; None when none is. (Dustin and Nicole's to confirm: REFUSE_IF_IN_USE.)"""
    ids = {s["id"]: shoot_name(s, names) for s in chosen}
    try:
        import edit_queue
        for x in edit_queue.load().get("shoots", []):
            if x.get("shoot") in ids and this_computer.same_place(x.get("studio") or "", studio):
                if x.get("status") == "finished":
                    return WORDS["delivered"].format(name=ids[x["shoot"]])
                if x.get("status", "waiting") == "waiting":
                    return WORDS["in_queue"].format(name=ids[x["shoot"]])
    except SystemExit:
        raise Stop("Your editing queue could not be read just now, so nothing was joined.")
    except Exception:  # noqa: BLE001  no queue yet
        pass
    try:
        import posts
        from where import locate
        h = posts.home()
        for k in (posts.kits(h) if h else []):
            rec = read_json(Path(k["path"]) / ".kit" / "kit.json", {}) or {}
            if rec.get("shoot_id") in ids and rec.get("night"):
                try:
                    theirs = locate(rec["night"])[1]
                except (SystemExit, OSError):
                    continue
                if this_computer.same_place(theirs, studio):
                    return WORDS["has_kit"].format(name=ids[rec["shoot_id"]])
    except Stop:
        raise
    except (Exception, SystemExit):  # noqa: BLE001  no content folder, a drive unplugged: no kit can be seen
        pass
    return None


def already_joined(studio, ids):
    """The finished entry of an earlier join that took in every one of these shoots, or None."""
    log = read_json(Path(studio) / LOG, {}) or {}
    for e in reversed(log.get("joins", [])):
        if e.get("finished") and not e.get("problems") and len(ids) > 1 and set(ids) <= set(e.get("ids", [])):
            return e
    return None


# ---------------------------------------------------------------- the plan

def make_plan(session, studio, ids, name=None):
    """The whole join, checked, as one log entry; nothing is touched. Raises Stop in plain words."""
    session, studio = Path(session), Path(studio)
    manifest = load(studio, "manifest.json")
    index = load(studio, "index.json")
    groups = {g["id"]: g for g in load(studio, "groups.json")["groups"]}
    sh = load(studio, "shoots.json")["shoots"]
    names = load(studio, "names.json", required=False) or {}
    files = manifest.get("files", {})
    if manifest.get("problems") or any(not v.get("dest", {}).get("ok") for v in files.values()):
        raise Stop(WORDS["not_verified"])

    ids = list(dict.fromkeys(ids))
    by_id = {s["id"]: s for s in sh}
    for i in ids:
        if i not in by_id:
            raise Stop(WORDS["no_shoot"].format(id=i))
    chosen = [s for s in sh if s["id"] in ids]          # in the records' own order (shooting order)
    if len(chosen) < 2:
        raise Stop(WORDS["need_two"])
    for s in chosen:
        if not s.get("folder") or len(Path(s["folder"]).parts) != 1:
            raise Stop(WORDS["not_sorted"].format(name=shoot_name(s, names)))
        if not on_disk(session / s["folder"]) or not (session / s["folder"]).is_dir():
            raise Stop(WORDS["missing"].format(name=s["folder"]))
    if REFUSE_IF_IN_USE:
        why = in_use(studio, chosen, names)
        if why:
            raise Stop(why)
    try:    # a backup that is still sorting or putting these very folders away: wait until it is done
        import backup_lock
        if backup_lock.working_on(studio):
            raise Stop(backup_lock.BEING_MADE)
    except (ImportError, AttributeError):
        pass
    try:    # a join while a second copy reads the same folders could make that copy miss a photo: wait
        import second_copy
        if second_copy.status(studio).get("state") == "copying":
            raise Stop(WORDS["second_copy"])
    except Stop:
        raise
    except Exception:  # noqa: BLE001
        pass

    kept = chosen[0]
    name = " ".join((name or shoot_name(kept, names)).split())
    naming = studio_file.load().get("naming", {})
    keep_names = naming.get("file_names", "shoot") == "original"
    folders = [Path(s["folder"]) for s in chosen]
    photos = [p for p in index["photos"] if p.get("original") and top(p["file"]) in folders]
    # every file the chosen shoots' groups name must be one of those photos: the records and the folders agree
    known = {p["file"] for p in photos}
    for s in chosen:
        for g in s.get("groups", []):
            for f in groups.get(g, {}).get("files", []):
                if f not in known and top(f) in folders:
                    raise Stop(WORDS["no_record"].format(name=Path(f).name))
    # a photo that is no longer in its shoot's folder (deleted or moved by hand since the backup: culling) is left
    # out and said, never a reason to refuse the join; its record stays as it was
    gone = [p["file"] for p in photos if not on_disk(session / p["file"])]
    for f in folders:   # a shoot with not one of its photos left in its folder is not culling: nothing is joined
        mine = [p["file"] for p in photos if top(p["file"]) == f]
        if mine and all(x in gone for x in mine):
            raise Stop(WORDS["missing"].format(name=f))
    photos = [p for p in photos if p["file"] not in gone]
    if not photos:
        raise Stop(WORDS["missing"].format(name=folders[0]))
    photos.sort(key=lambda p: (p.get("taken") or "", p["original"]))
    shoot_date = min((p["taken"] for p in photos if p.get("taken")), default=None)
    final = Path(safe_folder(studio_file.render(naming, name, shoot_date)) if naming.get("folder_pattern") and shoot_date
                 else safe_folder(name))
    staging = Path(safe_folder(final.name[:80 - len(STAGING_TAIL)].rstrip(" .") + STAGING_TAIL))
    prefix = prefix_for(name)

    stills, videos = [p for p in photos if not clips.is_clip(p)], [p for p in photos if clips.is_clip(p)]
    if stills and videos:
        placed = ([(final / clips.PHOTOS_FOLDER, n, p) for n, p in enumerate(stills, 1)]
                  + [(final / clips.VIDEOS_FOLDER, n, p) for n, p in enumerate(videos, 1)])
    else:
        placed = [(final, n, p) for n, p in enumerate(photos, 1)]

    listings = {}

    def names_in(folder):
        if folder not in listings:
            try:
                listings[folder] = os.listdir(session / folder)
            except OSError:
                listings[folder] = []
        return listings[folder]

    moves, planned_from, dests = [], set(), set()
    for into, n, p in placed:
        cur = Path(p["file"])
        orig_name = Path(p["original"]).name
        rec = files.get(p["original"])
        if not rec or not rec.get("sha256"):
            raise Stop(WORDS["no_record"].format(name=cur.name))
        if cur.name not in names_in(cur.parent) and not on_disk(session / cur):
            raise Stop(WORDS["missing"].format(name=cur.name))
        new = into / (orig_name if keep_names else f"{prefix}_{n:04d}_{orig_name}")
        cands = [(cur, new, p["original"], rec["sha256"], None)]
        # its sidecar travels with it under the same new stem: the one the backup copied, the Assistant's own, or
        # one their editing program wrote since. Found in the folder's own listing; hashed now, since an editing
        # program may have changed it after the backup.
        for found in sorted(names_in(cur.parent)):
            fp = Path(found)
            if fp.suffix.lower() == ".xmp" and fold(fp.stem) == fold(cur.stem):
                sc = cur.parent / found
                if sc.as_posix() in planned_from or not (session / sc).is_file():
                    continue
                cands.append((sc, into / f"{new.stem}{fp.suffix}", None, sha256_of(session / sc), "sidecar"))
        for a, b, original, digest, kind in cands:
            key = fold(b.as_posix())
            if key in dests:
                raise Stop(WORDS["two_same"].format(name=b.name))
            dests.add(key)
            planned_from.add(a.as_posix())
            m = {"from": a.as_posix(), "to": b.as_posix(), "sha256": digest}
            if original:
                m["original"] = original
            if kind:
                m["kind"] = kind
            moves.append(m)

    # nothing may be in the way: the name the joined shoot takes, and the folder it is gathered in
    chosen_names = {f.name for f in folders}
    for there in named_like(session, final.name):
        if there not in chosen_names:
            raise Stop(WORDS["name_taken"].format(folder=there))
        # the joined shoot takes the name of one of the shoots being joined: that folder must end up empty
        extras = []
        for dirpath, dirnames, filenames in os.walk(session / there):
            here = Path(dirpath).relative_to(session)
            extras += [(here / fn).as_posix() for fn in filenames
                       if (here / fn).as_posix() not in planned_from and not this_computer.housekeeping_file(fn)]
        if extras:
            raise Stop(WORDS["extras"].format(folder=there, names=", ".join(Path(x).name for x in extras[:3])
                                              + (f" and {len(extras) - 3} more" if len(extras) > 3 else "")))
    if named_like(session, staging.name):
        raise Stop(WORDS["name_taken"].format(folder=named_like(session, staging.name)[0]))   # as the drive spells it
    for m in moves:
        if not (session / m["from"]).is_file():
            raise Stop(WORDS["missing"].format(name=Path(m["from"]).name))
    dev = os.stat(session).st_dev
    for f in folders:
        if os.stat(session / f).st_dev != dev:
            raise Stop("Those shoots are on two different drives, so nothing was joined.")
    long = [m["to"] for m in moves if this_computer.path_too_long(session / m["to"])
            or this_computer.path_too_long(session / staging / inside(m["to"]))]
    if long or this_computer.path_too_long(session / staging, folder=True):
        raise Stop(WORDS["too_long"].format(app=this_computer.FILES_APP))

    return {"ids": [s["id"] for s in chosen], "kept": kept["id"], "name": name,
            "from_names": {s["id"]: shoot_name(s, names) for s in chosen},
            "folders": {s["id"]: s["folder"] for s in chosen},
            "shoots_before": [dict(s) for s in chosen], "names_before": {s["id"]: names.get(s["id"]) for s in chosen},
            "final": final.as_posix(), "staging": staging.as_posix(), "moves": moves,
            "photos": len(stills), "clips": len(videos), "planned": now(), "problems": [],
            **({"gone": gone} if gone else {})}


# ---------------------------------------------------------------- carrying it out (the first run and every later one)

def proved(path, m, deep=False):
    """(is it the very file the plan named, was it read in full). Identity first: a rename on one drive never
    rewrites a byte, so the same inode, size and modified time is the same file. Read in full against its hash
    when identity cannot say (a drive that numbers no file, a drive that renumbered it), or with deep."""
    try:
        st = os.stat(path)
    except OSError:
        return False, False
    ident = m.get("ident")
    if not deep and ident and ident[0] and [st.st_ino, st.st_size, st.st_mtime_ns] == ident:
        return True, False
    if not m.get("sha256"):
        return False, False          # no hash to check against: must never pass silently
    try:
        return sha256_of(path) == m["sha256"], True
    except OSError:
        return False, False


def where_now(session, entry):
    """{a file's place before the join (and its place in the gathering folder): where it really is now}."""
    staging = Path(entry["staging"])
    named = bool(entry.get("named"))
    out = {}
    for m in entry["moves"]:
        between = (staging / inside(m["to"])).as_posix()
        if named:
            here = m["to"]
        elif on_disk(session / between):
            here = between
        else:
            here = m["from"]
        out[m["from"]] = here
        out.setdefault(between, here)
    return out


def write_places(studio, new_path):
    """The index and the groups say where every file is now (never where it was meant to go)."""
    index = load(studio, "index.json")
    for p in index["photos"]:
        p["file"] = new_path.get(p["file"], p["file"])
    write_json(studio / "index.json", index)
    g = load(studio, "groups.json")
    for grp in g["groups"]:
        grp["files"] = [new_path.get(f, f) for f in grp["files"]]
    write_json(studio / "groups.json", g)


def follow_picks(studio, entry, new_path):
    """The first-look picks (the six photos a shoot shows) and their small pictures follow the photos; the picks
    of a joined-away shoot become the joined shoot's, taken in turn so the six shown come from every shoot."""
    pj = studio / "sneak-peeks.json"
    d = read_json(pj)
    if not isinstance(d, dict):
        return
    gone = set(entry["ids"]) - {entry["kept"]}
    for pk in d.get("picks", []):
        to = new_path.get(pk.get("file"))
        if to and to != pk["file"]:
            old_pv = studio / "sneak-peeks" / (Path(pk["file"]).stem + ".jpg")
            new_pv = studio / "sneak-peeks" / (Path(to).stem + ".jpg")
            if on_disk(old_pv) and not same_text(old_pv, new_pv) and not named_like(new_pv.parent, new_pv.name):
                try:
                    this_computer.rename(old_pv, new_pv)
                except OSError:      # only the report's small copy; the photo and its record matter
                    pass
            pk["file"] = to
        if pk.get("shoot") in gone:
            pk["shoot_was"], pk["shoot"] = pk["shoot"], entry["kept"]
            if "n" in pk:            # its number was a place on the joined-away shoot's own pages
                pk["n_was"] = pk.pop("n")
    picks = d.get("picks", [])
    mine = [p for p in picks if p.get("shoot") == entry["kept"]]
    if any(p.get("shoot_was") for p in mine):
        rows, order = {}, []
        for p in mine:
            k = p.get("shoot_was") or entry["kept"]
            if k not in rows:
                rows[k] = []
                order.append(k)
            rows[k].append(p)
        turn = []
        while any(rows.values()):
            for k in order:
                if rows[k]:
                    turn.append(rows[k].pop(0))
        it = iter(turn)
        d["picks"] = [next(it) if p.get("shoot") == entry["kept"] else p for p in picks]
    write_json(pj, d)


def write_records(session, studio, entry):
    """Every record follows the files. Built from what the log wrote down before the join (never from what the
    records say now), so writing them twice gives the same records."""
    new_path = where_now(session, entry)
    write_places(studio, new_path)
    follow_picks(studio, entry, new_path)
    groups = {g["id"]: g for g in load(studio, "groups.json")["groups"]}
    before = {s["id"]: s for s in entry["shoots_before"]}
    kept_before = before[entry["kept"]]
    gone = [i for i in entry["ids"] if i != entry["kept"]]
    sh = load(studio, "shoots.json")
    out = []
    for s in sh["shoots"]:
        if s["id"] in gone:
            continue
        if s["id"] == entry["kept"]:
            s = dict(kept_before)
            gs = [g for i in entry["ids"] for g in before[i].get("groups", [])]
            s["groups"] = sorted(dict.fromkeys(gs), key=lambda g: (groups.get(g, {}).get("start") or "", g))
            s["name"], s["folder"] = entry["name"], entry["final"]
            if "photos" in kept_before:
                s["photos"] = sum(int(before[i].get("photos") or 0) for i in entry["ids"])
            s["joined"] = list(kept_before.get("joined") or []) + [
                {"id": i, "name": entry["from_names"].get(i), "folder": entry["folders"].get(i),
                 "groups": before[i].get("groups", []), "recap": before[i].get("recap"), "when": entry.get("started")}
                for i in gone]
        out.append(s)
    sh["shoots"] = out
    write_json(studio / "shoots.json", sh)
    names = load(studio, "names.json", required=False) or {}
    names[entry["kept"]] = entry["name"]
    for i in gone:
        names.pop(i, None)          # what each was called is in the log and under "joined" on the shoot that stays
    write_json(studio / "names.json", names)


def update_queue(session, studio, entry):
    """The editing queue's list: the shoot that stays shows the joined shoot; the joined-away shoots' lines are
    kept under "joined" in the same file, out of every list."""
    try:
        import edit_queue
        q = edit_queue.load()
        gone = set(entry["ids"]) - {entry["kept"]}
        changed, stay = False, []
        for x in q["shoots"]:
            mine = this_computer.same_place(x.get("studio") or "", studio)
            if mine and x.get("shoot") == entry["kept"]:
                x["name"], x["folder"] = entry["name"], str(session / entry["final"])
                x["count"], x["clips"] = entry.get("photos", x.get("count")), entry.get("clips", x.get("clips", 0))
                changed = True
            elif mine and x.get("shoot") in gone:
                q.setdefault("joined", []).append(dict(x, joined_into=entry["kept"], joined_at=now()))
                changed = True
                continue
            stay.append(x)
        if changed:
            q["shoots"] = stay
            edit_queue.save(q)
            edit_queue.write_page(q)
    except (Exception, SystemExit):  # noqa: BLE001  the queue is a convenience; the join is done
        pass


def after(session, studio, second=True):
    """The report shows the joined shoot, and a second copy on another drive is brought in line (lane B)."""
    try:
        subprocess.run([sys.executable, str(HERE / "report_page.py"), str(studio)],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=300,
                       **({"creationflags": 0x08000000} if this_computer.WINDOWS else {}))
    except (OSError, subprocess.SubprocessError):
        pass
    if second:
        follow_second(studio)


def follow_second(studio):
    try:
        import second_copy
        second_copy.follow(str(studio))
    except (ImportError, AttributeError):
        pass
    except (Exception, SystemExit) as e:  # noqa: BLE001  the second copy is its own job; the join is done
        say(f"  (the second copy could not be brought in line just now: {e.__class__.__name__})")


def stop_part_way(session, studio, log, log_path, entry, words, detail=None):
    entry.setdefault("stops", []).append({"when": now(), "detail": detail or words})
    write_json(log_path, log)
    try:
        write_places(studio, where_now(session, entry))     # the records say where each file really is
    except (OSError, SystemExit):
        pass
    say(f"  stopped part way: {words} Every move so far is in {LOG}; nothing is lost. Run this again to finish it.")
    sys.exit(1)


def take_down(session, studio, entry):
    """The shoot folders the photos left: the computer's own hidden notes are set aside in the records (never
    deleted), then each folder comes down only if it is truly empty (rmdir refuses anything else)."""
    left = []
    for folder in dict.fromkeys(entry["folders"].values()):
        root = session / folder
        if not on_disk(root):
            continue
        for d in sorted([p for p in root.rglob("*") if p.is_dir()] + [root], key=lambda p: -len(p.parts)):
            try:
                entries = list(d.iterdir())
            except OSError:
                continue
            if entries and all(x.is_file() and this_computer.housekeeping_file(x.name) for x in entries):
                for x in entries:
                    dst = studio / ASIDE / x.relative_to(session)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    k = 1
                    while named_like(dst.parent, dst.name):
                        # an earlier join set a note of this name aside from a folder of this name (the Mac
                        # writes a new one whenever they open the folder): that one is kept, and this one goes
                        # beside it under the next free name. Never written over, never left in the way.
                        k += 1
                        dst = dst.with_name(f"{x.name} ({k})")
                    this_computer.rename(x, dst)
                    entry.setdefault("aside", []).append(x.relative_to(session).as_posix())
            try:
                this_computer.rmdir(d)
            except this_computer.HeldOpen:
                raise
            except OSError:
                pass
        if on_disk(root):
            left.append(folder)
    entry["left"] = left


def carry_out(session, studio, log, log_path, entry, deep=False):
    """Do the join the entry describes, from wherever it stands: the same steps on the first run and on a run
    that finishes a cut-off one. Each step looks at the drive, not at what an earlier run hoped."""
    session, studio = Path(session), Path(studio)
    final, staging, moves = Path(entry["final"]), Path(entry["staging"]), entry["moves"]
    st, fin = session / staging, session / final
    entry["problems"] = []
    if not entry.get("started"):
        # each file's identity on the drive, on record before anything moves
        for m in moves:
            try:
                s = os.stat(session / m["from"])
                m["ident"] = [s.st_ino, s.st_size, s.st_mtime_ns]
                if os.environ.get("STUDIO_JOIN_NO_IDENT_FOR_TESTS"):   # tests only: a drive that numbers no file
                    m["ident"][0] = 0
            except OSError:
                m["ident"] = None
        entry["started"] = now()
        write_json(log_path, log)
    cut_for_tests("after-log")

    if not entry.get("named") and not on_disk(st):
        # No gathering folder: either nothing has happened yet, or the folder already took its name and the
        # power went before the log could say so. Told apart by where the files are: named, every file is under
        # its new name and none is left under an old one (an old name that is also some file's new name says
        # nothing, so it is not asked). Whether each is the very file it should be is proved below, never here.
        new_names = {m["to"] for m in moves}
        olds = [m for m in moves if m["from"] not in new_names]
        all_there = all(on_disk(session / m["to"]) for m in moves)
        if all_there and olds and not any(on_disk(session / m["from"]) for m in olds):
            entry["named"] = True
            write_json(log_path, log)
        elif any(not on_disk(session / m["from"]) for m in moves):
            entry["problems"].append("some photos are not where the log says they were, and the joined folder is not whole; nothing more was moved")
            write_json(log_path, log)
            say(f"  PROBLEMS: {entry['problems'][0]}")
            sys.exit(1)

    try:
        if not entry.get("named"):
            if not on_disk(st):
                if named_like(session, staging.name):
                    stop_part_way(session, studio, log, log_path, entry, f"a folder called {staging.name} is in the way.")
                st.mkdir()
            if os.stat(st).st_dev != os.stat(session).st_dev:
                stop_part_way(session, studio, log, log_path, entry, "the folders are on two different drives; refusing to copy and delete.")
            done = 0
            for m in moves:
                a, b = session / m["from"], st / inside(m["to"])
                if on_disk(b):
                    m["moved"] = True           # an earlier run got this far; the check below proves it
                    done += 1
                    continue
                if not on_disk(a):
                    entry["problems"].append(f"missing: {m['from']}")
                    break
                if named_like(b.parent, b.name):
                    entry["problems"].append(f"{b.name} is already there; not overwritten")
                    break
                b.parent.mkdir(parents=True, exist_ok=True)
                if os.stat(a).st_dev != os.stat(b.parent).st_dev:
                    entry["problems"].append(f"{m['from']}: on a different drive; refusing to copy and delete")
                    break
                try:
                    this_computer.rename(a, b)
                except FileExistsError:     # a PC refuses a name that is there; unproven on a real PC
                    entry["problems"].append(f"{b.name} is already there; not overwritten")
                    break
                m["moved"] = True
                done += 1
                if done % 200 == 0:
                    write_json(log_path, log)
                    say(f"  {done} of {len(moves)} moved")
                cut_for_tests(f"moves:{done}")
            write_json(log_path, log)
            if entry["problems"]:
                stop_part_way(session, studio, log, log_path, entry, entry["problems"][-1] + ".")
            cut_for_tests("before-take-down")
            take_down(session, studio, entry)
            write_json(log_path, log)
            cut_for_tests("before-name")
            if named_like(session, final.name):
                stop_part_way(session, studio, log, log_path, entry,
                              f"{final.name} still has something in it, so the joined shoot is waiting in \"{staging.name}\".")
            this_computer.rename(st, fin)
            cut_for_tests("after-name")
            entry["named"] = True
            write_json(log_path, log)
    except this_computer.HeldOpen as e:
        stop_part_way(session, studio, log, log_path, entry,
                      f"the {this_computer.COMPUTER} would not move {Path(e.src).name} ({e.cause}). " + e.words, str(e))
    except OSError as e:
        stop_part_way(session, studio, log, log_path, entry, f"{e.__class__.__name__}.", f"{e.__class__.__name__}: {e}")

    # every file: there under exactly its name, and the same file it was
    checked = hashed = 0
    for m in moves:
        dst = session / m["to"]
        if not on_disk(dst):
            entry["problems"].append(f"after the join, {m['to']} is not there")
            continue
        same, read = proved(dst, m, deep=deep)
        if not same and m.get("kind") == "sidecar" and not m.get("original") and dst.is_file():
            # Their own sidecar (not one the backup copied): its hash was only taken at the plan to prove the
            # move, and their editing program may save it again at any moment (a join cut off, an edit, then
            # the finish). It is under exactly its new name beside its photo, so it is where it belongs; what it
            # holds now is theirs. Noted in the log, never a problem.
            if not m.get("saved_again"):
                m["saved_again"] = now()
            same, read = True, False
        if not same:
            entry["problems"].append(f"not the same file after the join: {m['to']}" if m.get("sha256")
                                     else f"no hash to check against: {m['to']}")
            continue
        m["checked"] = True
        checked += 1
        hashed += 1 if read else 0
    entry["verified"], entry["hashed_in_full"] = checked, hashed
    write_json(log_path, log)
    cut_for_tests("before-records")
    write_records(session, studio, entry)
    cut_for_tests("after-records")
    entry["finished"] = now()
    write_json(log_path, log)
    say(f"  {checked} of {len(moves)} files checked" + (f" ({hashed} read in full)" if hashed else ""))
    again = sum(1 for m in moves if m.get("saved_again"))
    if again:
        say(f"  ({again} sidecar{'s were' if again != 1 else ' was'} saved again by an editing program since the plan; "
            f"{'each is' if again != 1 else 'it is'} beside its photo under its new name)")
    # The files are where the records now say, problem or not, so everything that shows the shoots follows them:
    # the editing queue's list and the report. (Before, a problem at the check left both showing the joined-away
    # shoots, with folders that were gone, for good.)
    update_queue(session, studio, entry)
    if entry["problems"]:
        after(session, studio, second=False)   # the second copy is not brought in line with a join that has a problem
        say(f"  PROBLEMS (every move is in {LOG}):")
        for p in entry["problems"][:10]:
            say(f"    - {p}")
        sys.exit(1)
    for folder in entry.get("left") or []:
        say("  " + WORDS["left"].format(folder=folder))
    after(session, studio)
    return True


def look_again(session, studio, log, log_path, entry):
    """A join that ended with a problem at its check: look at its files once more, changing nothing. Only when
    every file is under exactly its joined name and proved the same file is the problem cleared and the join's
    last steps (the second copy) done. Otherwise everything is left exactly as it is: no record is written from
    this entry (a later rename may have moved the shoot on since), and the problem stays on record."""
    session = Path(session)
    for m in entry.get("moves", []):
        dst = session / m["to"]
        if not on_disk(dst):
            return False
        same, _ = proved(dst, m)
        if not same and not (m.get("kind") == "sidecar" and not m.get("original") and dst.is_file()):
            return False
    for m in entry["moves"]:
        m["checked"] = True
    entry["problems_were"], entry["problems"] = entry.get("problems"), []
    entry["verified"], entry["looked_again"] = len(entry["moves"]), now()
    write_json(log_path, log)
    say(f"A join that ended with a problem checks out now: {entry.get('name')}")
    update_queue(session, Path(studio), entry)
    after(session, Path(studio))
    return True


def finish_unfinished(session, studio):
    """A join that was cut off (the power, a file held open on a PC) left its entry without 'finished'. Every
    move is in that entry, so finish it before anything new. Returns True when one was finished."""
    log_path = Path(studio) / LOG
    log = read_json(log_path)
    if not isinstance(log, dict):
        return False
    did = False
    for entry in log.get("joins", []):
        if entry.get("finished") and not entry.get("problems"):
            continue
        if entry.get("finished"):
            # It ended with a problem at its check. Looked at again on every later run: when the check now
            # passes (a drive that misread once, a file put back) the problem is cleared and the join's last
            # steps are done; when it does not, the problem stays on record (so nothing settles) and this run
            # carries on with what it was asked, since every file is where the records say.
            if look_again(session, studio, log, log_path, entry):
                did = True
            continue
        say(f"Finishing a join that was cut off: {entry.get('name')}")
        carry_out(session, studio, log, log_path, entry)
        did = True
    return did


def half_done(studio):
    """What the next run would have to finish before anything new, for the Name your shoots page:
    "half" (a join or a rename was cut off and the next run finishes it), "stuck" (it has stopped on a problem,
    or twice over, so running it again is not the answer: the Assistant has to look), or None."""
    studio = Path(studio)
    out = None
    for e in (read_json(studio / LOG, {}) or {}).get("joins", []):
        if not isinstance(e, dict) or e.get("finished"):
            continue                                   # finished with a problem does not stand in a later run's way
        if e.get("problems") or len(e.get("stops") or []) >= STUCK_AFTER:
            return "stuck"
        out = "half"
    for e in (read_json(studio / "rename-log.json", {}) or {}).get("renames", []):
        if not isinstance(e, dict):
            continue
        tos = [str(m.get("to", "")).lower() for m in e.get("moves", [])]
        real = [m for m in e.get("moves", [])     # a move an old version planned twice for one sidecar is no move
                if not m.get("phantom") and not (not m.get("sha256") and tos.count(str(m.get("to", "")).lower()) > 1)]
        if e.get("finished") and all(m.get("moved") or m.get("gone") for m in real):     # (gone: a photo they deleted; noted, not waited for)
            continue
        if e.get("problems") or len(e.get("stops") or []) >= STUCK_AFTER:
            return "stuck"
        out = "half"
    return out


def unfinished(studio):
    """True when this backup has a join that has not finished, or finished with problems (settle waits for it)."""
    log = read_json(Path(studio) / LOG, {}) or {}
    return any(not e.get("finished") or e.get("problems") for e in log.get("joins", []))


class held:
    """Hold the one lock for the length of the work, unless the job that started us holds it already. Waits up
    to `wait` seconds for whoever has it; False from the with-line when they kept it longer."""
    def __init__(self, wait=2.0):
        self.wait = wait

    def __enter__(self):
        self.f = None
        if os.environ.get(LOCK_HELD):
            return True
        try:
            HOME.mkdir(parents=True, exist_ok=True)
            self.f = open(LOCK, "ab")
        except OSError:
            return True                      # no lock to be had: carry on without one, as before
        end = time.time() + self.wait
        while True:
            got = this_computer.try_lock(self.f)
            if got or got is None:
                return True
            if time.time() > end:
                self.f.close()
                self.f = None
                return False
            time.sleep(0.05)

    def __exit__(self, *exc):
        if self.f is not None:
            try:
                this_computer.unlock(self.f)
            except OSError:
                pass
            self.f.close()
        return False


def join(session, studio, ids, name=None, dry=False, deep=False):
    """Plan and carry out one join. Raises Stop (nothing changed); exits 1 through carry_out on a stop part way."""
    session, studio = Path(session), Path(studio)
    rename_shoot.finish_unfinished(session, studio)
    finish_unfinished(session, studio)
    done = already_joined(studio, ids)
    if done and (not name or " ".join(name.split()) == done.get("name")):
        say(WORDS["already"].format(name=done.get("name")))
        return done
    entry = make_plan(session, studio, ids, name)
    say(f"Joining {len(entry['ids'])} shoots into \"{entry['name']}\":")
    for i in entry["ids"]:
        say(f"  {i}  {entry['from_names'][i]}   ({entry['folders'][i]})")
    say(f"  ->  {entry['final']}/   {clips.words(entry['photos'], entry['clips'])}, {len(entry['moves'])} files")
    first = entry["moves"][0]
    say(f"  e.g. {first['from']}  ->  {first['to']}")
    if entry.get("gone"):
        n = len(entry["gone"])
        say(f"  ({n} of these shoots' photos {'is' if n == 1 else 'are'} no longer in {'its' if n == 1 else 'their'} folder "
            "(deleted or moved since the backup); left out, the rest are joined.)")
    if dry:
        say("  Dry run. Nothing joined.")
        return entry
    log_path = studio / LOG
    log = read_json(log_path) or {"joins": []}
    log["joins"].append(entry)
    write_json(log_path, log)               # on record before anything moves
    carry_out(session, studio, log, log_path, entry, deep=deep)
    say("  Joined.")
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("backup", help="the backup: its folder, its records, or where it was")
    ap.add_argument("--list", action="store_true", help="this backup's shoots, by id")
    ap.add_argument("--shoots", nargs="+", help="the ids of the shoots to join, e.g. s1 s2")
    ap.add_argument("--all", action="store_true", help="every shoot of this backup into one")
    ap.add_argument("--name", help="what the joined shoot is called (the first shoot's name when left out)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deep", action="store_true", help="read every moved file in full instead of the identity check")
    ap.add_argument("--finish", action="store_true", help="only finish a join that was cut off")
    a = ap.parse_args()
    from where import locate
    session, studio = locate(a.backup)
    if a.list:
        for s in listing(studio):
            say(f"{s['id']} | {s['name']} | {s['folder'] or 'not in a folder yet'} | {clips.words(s['photos'], s['clips'])}")
        return
    with held() as got:
        if not got:
            say("STOP: " + WORDS["busy"])
            sys.exit(2)
        if a.finish:
            rename_shoot.finish_unfinished(session, studio)
            if not finish_unfinished(session, studio) and not unfinished(studio):
                say("No join is waiting to be finished.")
            if unfinished(studio):
                sys.exit(1)                  # one that ended with a problem is still on record
            return
        ids = a.shoots or []
        if a.all:
            ids = [s["id"] for s in listing(studio)]
            if len(ids) == 1:
                rename_shoot.finish_unfinished(session, studio)
                finish_unfinished(session, studio)
                log = read_json(studio / LOG, {}) or {}
                done = any(e.get("finished") and e.get("kept") == ids[0] for e in log.get("joins", []))
                say(WORDS["already"].format(name=listing(studio)[0]["name"]) if done else "This backup has one shoot. Nothing to join.")
                return
        if not ids:
            sys.exit("usage: --shoots <id> <id> [...] [--name <name>], or --all, or --list")
        try:
            join(session, studio, ids, a.name, dry=a.dry_run, deep=a.deep)
        except Stop as e:
            say(f"STOP: {e}")
            sys.exit(2)


if __name__ == "__main__":
    main()
