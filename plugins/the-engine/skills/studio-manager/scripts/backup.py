#!/usr/bin/env python3
"""The Studio Manager, safety core: copy a card (or any folder) to the session drive, optionally to a second place,
check every file against the original, and write the morning report. Never deletes. Never moves. Stops on trouble.

  python3 backup.py --source "/path/to/card" --dest "/path/to/Sessions drive" --name "Johnson family beach"
                    [--second "/path/to/cloud folder"] [--date 2026-10-23] [--dry-run]

Writes <dest>/<date> <name>/ with the files in their original folders, plus _studio/manifest.json and
_studio/morning-report.md. A second copy goes to <second>/<date> <name>/ with its own check.
Safe to run again: files already copied and verified are skipped, nothing is overwritten.
"""
import argparse, errno, hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
import clips  # noqa: E402  (only for the words: "212 photos and 6 clips", never "photos or clips")
this_computer.utf8_output()

CHUNK = 8 * 1024 * 1024
MEDIA = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".tif", ".tiff", ".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf",
         ".rw2", ".mov", ".mp4", ".m4v", ".mxf", ".wav"}
SKIP_DIRS = {".fseventsd", ".Spotlight-V100", ".Trashes", ".TemporaryItems", "System Volume Information", "$RECYCLE.BIN", "_studio"}


def hide(folder):
    """Hide the Studio's own folder in Finder (Mac) or Explorer (Windows). The name stays
    `_studio`, so every script and the report's links keep working; it is just not in their way."""
    this_computer.hide(folder)


def say(msg):
    """Print, but never let a closed pipe (someone ran us through `head`) stop the copy, the check of every file,
    the manifest or the report (the Oct 24 rule). Before Nov 6 a closed pipe stopped the backup part way, on a Mac
    too. What would have been printed goes nowhere from then on, as in sort.py, so the exit code (0 safe,
    1 problems, 2 stop, 3 paused, which night.py reads) is the backup's own and never Python's 120."""
    try:
        print(msg, flush=True)
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except OSError as e:
        # A PC only (as kit.py's say): Windows reports a reader that has gone away as "invalid argument" (EINVAL),
        # not as a broken pipe. A Mac raises anything else, as before. unproven on a real PC
        if not (this_computer.WINDOWS and e.errno == errno.EINVAL):
            raise
        sys.stdout = open(os.devnull, "w", encoding="utf-8")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def copy_with_hash(src, dst):
    """Copy src to dst, hashing the bytes as they are read, then re-read dst from disk and hash that too."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".studio-partial")
    h = hashlib.sha256()
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        for block in iter(lambda: fi.read(CHUNK), b""):
            h.update(block)
            fo.write(block)
        fo.flush()
        os.fsync(fo.fileno())
    # The file only gets its real name once every byte is on disk. On a PC the virus checker often has a file
    # open just after it is written, so the rename waits a moment there rather than stopping the copy.
    this_computer.replace(tmp, dst)
    shutil.copystat(src, dst, follow_symlinks=False)
    return h.hexdigest(), sha256_of(dst)


def inventory(root):
    """Every file worth copying, plus a count of the hidden Mac system files
    (._ sidecars, .DS_Store) left behind on purpose, so the report's numbers
    match what they see in Finder."""
    files = []
    skipped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                skipped += 1
                continue
            if fn.endswith(".studio-partial"):
                continue
            p = Path(dirpath) / fn
            try:
                files.append((p, p.stat().st_size))
            except OSError:
                files.append((p, -1))
    files.sort(key=lambda t: str(t[0]).lower())
    return files, skipped


def free_bytes(path):
    return this_computer.free_bytes(path)


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def media_info(path):
    """Camera, lens, date for photos; duration for video. Best effort, never fatal."""
    ext = path.suffix.lower()
    out = {}
    try:
        if ext in (".mov", ".mp4", ".m4v", ".mxf"):
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags=creation_time",
                                "-of", "json", str(path)], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
            d = json.loads(r.stdout or "{}").get("format", {})
            if d.get("duration"):
                out["seconds"] = round(float(d["duration"]), 1)
            if d.get("tags", {}).get("creation_time"):
                out["taken"] = d["tags"]["creation_time"]
        elif ext in MEDIA and shutil.which("identify"):
            r = subprocess.run(["identify", "-format", "%[EXIF:DateTimeOriginal]|%[EXIF:Model]|%[EXIF:LensModel]|%wx%h",
                                str(path) + "[0]"], capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            parts = (r.stdout.strip().split("|") + ["", "", "", ""])[:4]
            if parts[0]:
                out["taken"] = parts[0]
            if parts[1]:
                out["camera"] = parts[1]
            if parts[2]:
                out["lens"] = parts[2]
            if parts[3]:
                out["size"] = parts[3]
    except Exception:
        pass
    return out


DIFFERS = "exists and differs"   # the record of a file that was already at the destination and is not the card's


def identity(path):
    """[size, modified time, file number] of what is at path now, or None when nothing is there. Kept with a
    failed copy, so a later run can tell its own half-done file from one somebody put there since."""
    try:
        st = os.stat(path)
        return [st.st_size, st.st_mtime_ns, st.st_ino]
    except OSError:
        return None


def ours_to_redo(rec, dst):
    """True only when what is at dst is the backup's own failed copy (a copy that broke off, or one whose check
    failed), which may be written again. Anything else at dst (a file that was there before, or one the backup
    copied and checked that has changed since) is compared and never written over.

    Nov 6 review: a second run used to read the saved "exists and differs" record as "we have been here before"
    and copy the card's file over the one that was there, then report everything safe."""
    if not rec or rec.get("ok") or rec.get("note") == DIFFERS:
        return False
    if "left" in rec:            # written since Nov 6: exactly what the failed copy left behind (None: nothing)
        return rec["left"] is not None and rec["left"] == identity(dst)
    return True                  # an older record of a failed copy: only ever the backup's own file


def run_copy(label, files, src_root, dest_root, manifest, dry, save=None, budget=None):
    """Copy every file into dest_root, verify, and record. Returns a list of problems (strings).
    `save()` is called after every file so progress survives an interruption; `budget` (seconds) makes the run
    stop cleanly after that long, to be continued by running the same command again."""
    problems = []
    t_start = time.time()
    done = 0
    total = len(files)
    t0 = time.time()
    for p, size in files:
        rel = p.relative_to(src_root)
        key = rel.as_posix()  # one spelling in the records on a Mac and a PC, so a drive can move between them
        entry = manifest["files"].setdefault(key, {"size": size})
        dst = dest_root / rel
        if size < 0:
            problems.append(f"Could not read {rel} on the source. Left alone.")
            continue
        if dry:
            done += 1
            continue
        # already copied and verified on a previous run: check size, trust the recorded hash, skip
        rec = entry.get(label)
        if rec and rec.get("ok") and dst.exists() and dst.stat().st_size == size:
            done += 1
            continue
        if dst.exists() and not ours_to_redo(rec, dst):
            # something is already there that is not our own failed copy: never overwrite, compare instead,
            # on every run, so it stays at the top of the report until someone has looked at it
            try:
                if dst.stat().st_size == size and sha256_of(dst) == (entry.get("sha256") or sha256_of(p)):
                    entry["sha256"] = entry.get("sha256") or sha256_of(p)
                    entry[label] = {"ok": True, "note": "already there, identical"}
                    done += 1
                    continue
            except OSError:
                pass
            problems.append(f"{rel} already exists at the destination and is different. Not overwritten; check it by hand.")
            entry[label] = {"ok": False, "note": DIFFERS}
            continue
        try:
            src_hash, dst_hash = copy_with_hash(p, dst)
        except OSError as e:
            problems.append(f"{rel} would not copy ({e.__class__.__name__}: {e}). Stopped this copy.")
            entry[label] = {"ok": False, "note": str(e), "left": identity(dst)}
            break
        entry["sha256"] = src_hash
        if src_hash != dst_hash:
            problems.append(f"{rel} copied but the check failed (the copy does not match the original). Stopped.")
            entry[label] = {"ok": False, "note": "hash mismatch", "left": identity(dst)}
            break
        entry[label] = {"ok": True}
        done += 1
        if save:
            save()
        if done % 25 == 0 or done == total or size > 200 * 1024 * 1024:
            say(f"  {label}: {done}/{total} files, {time.time() - t0:.0f} s")
        if budget and time.time() - t_start > budget:
            problems.append("PAUSED")
            break
    return problems


def not_this_card(manifest, src, files, name):
    """None when the backup these records describe was made from this card; otherwise plain words saying it was
    not. Every file the records say was copied must still be on the card at the size it had, and the three
    smallest photos among them must still read the same, byte for byte (about a second). A card with photos
    added since passes only when that backup was cut off part way (it carries on and copies them); after a
    finished backup, which may already be sorted into shoots, the card gets a backup of its own.

    Nov 6 review: two cards backed up on the same day under the same name land in one folder (with no name given,
    both are "<weekday> card"). When the first card's backup had not finished, the second card was taken for it:
    nothing of the second card was copied, and the report said the photos were safe, so the second card could have
    been formatted with its photos on it alone."""
    if manifest.get("sample"):
        files = list(files)[:manifest["sample"].get("kept", 0)]   # a sample backup only ever holds its sample
    copied = {k: e for k, e in (manifest.get("files") or {}).items()
              if any((e.get(label) or {}).get("ok") for label in ("dest", "second"))}
    if not copied:
        return None
    on_card = {p.relative_to(src).as_posix(): (p, s) for p, s in files}
    off = [k for k, e in copied.items() if k not in on_card or on_card[k][1] != e.get("size")]
    if not off:
        hashed = [k for k in copied if copied[k].get("sha256")]
        photos = [k for k in hashed if Path(k).suffix.lower() in MEDIA] or hashed
        for k in sorted(photos, key=lambda k: (copied[k].get("size") or 0, k))[:3]:
            try:
                if sha256_of(on_card[k][0]) != copied[k]["sha256"]:
                    off.append(k)
            except OSError:
                off.append(k)
    folder = manifest.get("session") or "that folder"
    again = f"Give this card its own name, like \"{name.strip()} 2\", and run it again."
    if off:
        return (f"The folder \"{folder}\" on the drive already holds a backup made from a different memory card (or from this "
                f"card before photos on it were deleted or changed). So photos from two cards never get mixed up, I won't put "
                f"this card in there. {again}")
    # The same card with photos taken since. A backup that was cut off part way just carries on and copies them;
    # one that had finished may already be sorted into shoots, so the new photos get a backup of their own.
    if manifest.get("finished") and not manifest.get("problems") and any(k not in manifest["files"] for k in on_card):
        return (f"The folder \"{folder}\" on the drive already holds a finished backup of this card, from before its newest "
                f"photos were taken. So nothing gets mixed up, I won't add to it. {again} Everything on the card is copied there.")
    return None


def whole_records(records):
    """True when the records in this folder describe a whole backup: every file copied and checked, no problems,
    and no sample marker left, or one that covered the whole card (asked for more files than the card held),
    which is dropped here. A sample of part of a card stays a sample: False."""
    mp = Path(records) / "manifest.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    files = manifest.get("files") or {}
    ok = bool(files) and not manifest.get("problems") and all((v.get("dest") or {}).get("ok") for v in files.values())
    if not ok:
        return False
    smp = manifest.get("sample")
    if smp:
        if smp.get("kept", 0) < smp.get("of", 0):
            return False
        manifest.pop("sample")
        tmp = mp.with_name(mp.name + ".tmp")
        tmp.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        this_computer.replace(tmp, mp)
    return True


def not_copied(manifest, src, files, sampling=True):
    """The files on this card that the records do not have as copied and checked: on the drive, and in the second
    copy when there is one. Empty when the backup of this card is whole."""
    have = manifest.get("files") or {}
    if sampling and manifest.get("sample"):
        files = list(files)[:manifest["sample"].get("kept", 0)]   # a sample backup is whole once its sample is
    labels = ("dest", "second") if manifest.get("second") else ("dest",)
    return [k for k in (p.relative_to(src).as_posix() for p, _ in files)
            if not all(((have.get(k) or {}).get(label) or {}).get("ok") for label in labels)]


def _nearest(path):
    """The folder itself, or the nearest folder above it that is there."""
    p = Path(path)
    for q in (p, *p.parents):
        try:
            if q.exists():
                return q
        except OSError:
            continue
    return None


def _top_of_drive(path):
    p = Path(path)
    while p != p.parent and not os.path.ismount(str(p)):
        p = p.parent
    return p


def _own_disk(path):
    """True when a folder is on the computer's own disk, which is never formatted like a card."""
    if this_computer.WINDOWS:
        # unproven on a real PC: the drive Windows itself is on (C: nearly always)
        return os.path.splitdrive(str(path))[0].upper() == (os.environ.get("SystemDrive") or "C:").upper()
    return this_computer.drive_words(path) is None   # a Mac puts every other drive under /Volumes


def _drive_label(path):
    if this_computer.WINDOWS:
        letter = os.path.splitdrive(str(path))[0]
        if letter:
            return letter.upper()
    return this_computer.drive_words(path) or _top_of_drive(path).name or str(_top_of_drive(path))


def onto_itself(src, target, what):
    """Plain words when a copy would land on the drive it is copied from: the memory card itself, the same
    external drive, or inside the folder being copied. None when it goes somewhere else (or the place is not
    there at all, which is said elsewhere). `what` is "the backup" or "the second copy".

    Nov 6 review: on a PC the Studio File keeps the photo drive as a letter (E:\\), and Windows hands letters out
    in the order things are plugged in, so another day the card itself can be E:. The card was then copied onto
    itself, the check passed (both copies were on the card) and the report said it was safe to format. A Mac
    names the drive in the path, so there this only happens when the card itself was picked as the drive.
    The computer's own disk is allowed (a folder there backed up to a folder there): it is never formatted."""
    try:
        s = Path(src).expanduser().resolve()
        t = _nearest(Path(target).expanduser())
        if t is None:
            return None
        t = t.resolve()
        key = lambda p: os.path.normcase(str(p))   # on a PC, "E:\Card" and "e:\card" are one folder; a Mac: as is
        if any(key(q) == key(s) for q in (t, *t.parents)):
            return f"{what.capitalize()} would go inside the very folder being backed up. Pick a folder outside it."
        if os.stat(s).st_dev != os.stat(t).st_dev:
            return None
        card = (_top_of_drive(s) / "DCIM").is_dir()
        if not card and _own_disk(s):
            return None
        label = _drive_label(s)
    except (OSError, ValueError, RuntimeError):
        return None   # a card or drive that cannot be read is stopped by the checks beside this one
    hint = (" Is your photo drive plugged in? On a PC a drive can get a different letter from one day to the next."
            if this_computer.WINDOWS else " Pick the drive the photos should go to.")
    if card:
        return (f"{what.capitalize()} would go onto the memory card itself ({label}). I won't copy a card onto itself: "
                f"once the card is formatted, both copies would be gone.{hint}")
    return (f"{what.capitalize()} would go onto the same drive the photos are coming from ({label}). A copy there is not "
            f"a second place: if that drive fails, both are gone.{hint}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--dest", required=True, help="the session drive or folder")
    ap.add_argument("--second", default=None, help="the second copy (cloud drive folder)")
    ap.add_argument("--name", required=True, help="session name, e.g. 'Johnson family beach'")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=None, help="seconds to work before pausing cleanly (run again to continue)")
    ap.add_argument("--sample", type=int, default=None, help="a TEST only: copy just the first N files of the card (in path order). "
                    "The records say it was a sample, the report says the card is not backed up, and the card is never marked safe.")
    a = ap.parse_args()

    # drive_root: on a PC a bare "E:" means the top of drive E (Python alone reads it as wherever it last was on E).
    # On a Mac it is Path() exactly.
    src = this_computer.drive_root(a.source).expanduser()
    if not src.is_dir():
        say(f"STOP: I can't find the source at {src}. Is the card in?")
        sys.exit(2)
    date = a.date or datetime.now().strftime("%Y-%m-%d")
    folder = this_computer.safe_name(f"{date} {a.name.strip()}", limit=120)
    dest = this_computer.drive_root(a.dest).expanduser() / folder
    second = this_computer.drive_root(a.second).expanduser() / folder if a.second else None

    files, skipped = inventory(src)
    all_files = files
    sample = None
    if a.sample and a.sample < len(files):     # a sample that covers the whole card is simply the whole card
        # a sample for a test (Dustin, Nov 11: a two-card rehearsal without burning through space). Only the first
        # N files are copied; everything that follows reads "sample" in the records, and the card is never called safe.
        if a.sample < 1:
            say("STOP: --sample needs a number of files, 1 or more.")
            sys.exit(2)
        sample = {"kept": min(a.sample, len(files)), "of": len(files)}
        files = files[:sample["kept"]]
        say(f"A SAMPLE, for a test: the first {sample['kept']} of the card's {sample['of']} files. The card will NOT be backed up or marked safe.")
    total_bytes = sum(s for _, s in files if s > 0)
    media = [p for p, s in files if p.suffix.lower() in MEDIA]
    say(f"Source: {src}\n  {len(files)} files, {human(total_bytes)}, {clips.words_for(media)}")
    if not files:
        say("STOP: the card looks empty. Nothing to copy.")
        sys.exit(2)

    problems = []
    # never onto the card itself, and never into a folder that already holds another card's backup: both are
    # found here, before anything is written anywhere
    for what, place in (("the backup", dest), ("the second copy", second)):
        why = onto_itself(src, place, what) if place is not None else None
        if why:
            problems.append(why)
    mpath = dest / "_studio" / "manifest.json"
    if mpath.exists():
        why = not_this_card(json.loads(mpath.read_text(encoding="utf-8")), src, files, a.name)
        if why:
            problems.append(why)
    roots = [("dest", dest.parent)] + ([("second", second.parent)] if second else [])
    need_by_device = {}  # two folders on one physical drive need room for both copies
    for label, root in roots:
        if not root.exists():
            problems.append(f"The {'session drive' if label == 'dest' else 'second copy'} folder {root} is not there. Is the drive plugged in?")
            continue
        try:
            dev = os.stat(root).st_dev
        except OSError:
            dev = label
        need_by_device.setdefault(dev, {"roots": [], "need": 0})
        need_by_device[dev]["roots"].append(root)
        need_by_device[dev]["need"] += total_bytes * 1.05 + 2 * 1024 ** 3
    for d in need_by_device.values():
        fb = free_bytes(d["roots"][0])
        if fb is not None and fb < d["need"]:
            where = " and ".join(str(r) for r in d["roots"])
            problems.append(f"Not enough room on {where}: {human(fb)} free, about {human(d['need'])} needed "
                            f"(the card holds {human(total_bytes)}). Free up about {human(d['need'] - fb)} or pick another drive.")
    if problems:
        for p in problems:
            say("STOP: " + p)
        sys.exit(2)

    if a.dry_run:
        say(f"Would copy to {dest}" + (f" and {second}" if second else "") + ". Nothing done (dry run).")
        return

    studio = dest / "_studio"
    studio.mkdir(parents=True, exist_ok=True)
    hide(studio)  # out of sight in Finder; they ask Claude for the report
    mpath = studio / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {"session": folder, "source": str(src), "files": {}}
    manifest["source"] = str(src)
    manifest["dest"] = str(dest)
    manifest["second"] = str(second) if second else None
    manifest["skipped_system_files"] = skipped
    if sample:
        manifest["sample"] = sample
    elif a.sample:
        manifest.pop("sample", None)           # asked for more than the card holds: a whole backup
    manifest["started"] = manifest.get("started") or datetime.now().isoformat(timespec="seconds")

    t0 = time.time()
    save = lambda: mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    say(f"Copying to {dest}")
    problems += run_copy("dest", files, src, dest, manifest, False, save, a.budget)
    save()
    if second and not problems:
        say(f"Second copy to {second}")
        (second / "_studio").mkdir(parents=True, exist_ok=True)
        hide(second / "_studio")
        left = (a.budget - (time.time() - t0)) if a.budget else None
        problems += run_copy("second", files, src, second, manifest, False, save, left if (left is None or left > 5) else 5)
        save()
        (second / "_studio" / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    if "PAUSED" in problems:
        done = sum(1 for e in manifest["files"].values() if e.get("dest", {}).get("ok"))
        say(f"PAUSED after {time.time() - t0:.0f} s: {done} of {len(files)} files copied and checked. Run the same command again to continue.")
        sys.exit(3)

    # what's on it, for the report
    kinds = {}
    for p, s in files:
        kinds[p.suffix.lower() or "(none)"] = kinds.get(p.suffix.lower() or "(none)", 0) + 1
    sample = [p for p in media[:3]] + ([media[-1]] if len(media) > 3 else [])
    infos = {p.relative_to(src).as_posix(): media_info(p) for p in sample}
    taken = sorted(v["taken"] for v in infos.values() if v.get("taken"))

    ok_dest = sum(1 for e in manifest["files"].values() if e.get("dest", {}).get("ok"))
    ok_second = sum(1 for e in manifest["files"].values() if e.get("second", {}).get("ok")) if second else None
    elapsed = time.time() - t0
    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    manifest["problems"] = problems
    if manifest.get("sample") and not a.sample and not not_copied(manifest, src, all_files, sampling=False):
        manifest.pop("sample")                 # run again without --sample, it copied the rest: a whole backup now
    manifest["taken"] = (f"{taken[0]} to {taken[-1]}" if len(taken) >= 2 else taken[0]) if taken else None
    manifest["work_seconds"] = manifest.get("work_seconds", 0) + elapsed  # across resumed runs
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    lines = [f"# Report · {folder}", ""]
    if problems:
        lines += ["## Needs you first", ""] + [f"- {p}" for p in problems] + [""]
        lines += [f"**Not finished.** {ok_dest} of {len(files)} files are copied and checked on the session drive. Nothing on the memory card has been changed; run it again when the problem is fixed and it picks up where it left off.", ""]
    else:
        lines += [f"**All {len(files)} files ({human(total_bytes)}) have been safely backed up and verified.** Every one was checked against the card, byte for byte."
                  + (" They are on your drive and in your second copy." if second else ""), ""]
    mac = "Mac " if this_computer.MAC else ""   # "hidden Mac system file" on a Mac, word for word as before; "hidden system file" on a PC
    skipped_note = f" ({skipped} hidden {mac}system file{'s' if skipped != 1 else ''} left behind, as they should be)" if skipped else ""
    lines += ["## What's on it", "",
              f"- {clips.words_for(media)}, " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda t: -t[1])) + skipped_note,
              f"- Taken: {taken[0]} to {taken[-1]}" if len(taken) >= 2 else (f"- Taken: {taken[0]}" if taken else "- Taken: (no dates found yet)")]
    cams = sorted({v["camera"] for v in infos.values() if v.get("camera")})
    if cams:
        lines.append(f"- Camera: {', '.join(cams)}")
    secs = [v["seconds"] for v in infos.values() if v.get("seconds")]
    if secs:
        lines.append(f"- Clips sampled: {', '.join(f'{s:.0f}s' for s in secs)}")
    lines += ["", "## Where", "", f"- Session drive: `{dest}`"]
    if second:
        lines.append(f"- Second copy: `{second}`" + ("" if ok_second == len(files) else f" ({ok_second} of {len(files)} checked)"))
    lines += ["", "## The card", "", "Nothing on it was changed. " + ("It is safe to format when you're ready." if not problems else "Keep it."),
              "", f"_{len(files)} files · {human(total_bytes)} · {elapsed:.0f} seconds · your memory card is exactly as it was._"]
    report = "\n".join(lines) + "\n"
    (studio / "morning-report.md").write_text(report, encoding="utf-8")
    # the index (when each photo was taken, which camera) and the same report as a
    # page they can look at; neither may ever break the backup
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        if not problems and not a.dry_run:
            from index import build as build_index
            build_index(dest)
        from report_page import write_page
        page = write_page(dest)
    except Exception as e:  # noqa: BLE001
        page = None
        say(f"(could not write report.html: {e.__class__.__name__}: {e})")
    say("")
    say(report)
    if page:
        say(f"Open it: {page}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
