#!/usr/bin/env python3
"""The Studio Manager, safety core: copy a card (or any folder) to the session drive, optionally to a second place,
check every file against the original, and write the morning report. Never deletes. Never moves. Stops on trouble.

  python3 backup.py --source "/path/to/card" --dest "/path/to/Sessions drive" --name "Johnson family beach"
                    [--second "/path/to/cloud folder"] [--date 2026-10-23] [--dry-run]

Writes <dest>/<date> <name>/ with the files in their original folders, plus _studio/manifest.json and
_studio/morning-report.md. A second copy goes to <second>/<date> <name>/ with its own check.
Safe to run again: files already copied and verified are skipped, nothing is overwritten.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

CHUNK = 8 * 1024 * 1024
MEDIA = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".tif", ".tiff", ".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf",
         ".rw2", ".mov", ".mp4", ".m4v", ".mxf", ".wav"}
SKIP_DIRS = {".fseventsd", ".Spotlight-V100", ".Trashes", ".TemporaryItems", "System Volume Information", "_studio"}


def say(msg):
    print(msg, flush=True)


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
    os.replace(tmp, dst)          # the file only gets its real name once every byte is on disk
    shutil.copystat(src, dst, follow_symlinks=False)
    return h.hexdigest(), sha256_of(dst)


def inventory(root):
    """Every file worth copying, plus a count of the hidden Mac system files
    (._ sidecars, .DS_Store) left behind on purpose, so the report's numbers
    match what she sees in Finder."""
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
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except OSError:
        return None


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
                                "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
            d = json.loads(r.stdout or "{}").get("format", {})
            if d.get("duration"):
                out["seconds"] = round(float(d["duration"]), 1)
            if d.get("tags", {}).get("creation_time"):
                out["taken"] = d["tags"]["creation_time"]
        elif ext in MEDIA and shutil.which("identify"):
            r = subprocess.run(["identify", "-format", "%[EXIF:DateTimeOriginal]|%[EXIF:Model]|%[EXIF:LensModel]|%wx%h",
                                str(path) + "[0]"], capture_output=True, text=True, timeout=60)
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
        key = str(rel)
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
        if dst.exists() and not rec:
            # something is already there that we did not write: never overwrite, compare instead
            try:
                if dst.stat().st_size == size and sha256_of(dst) == (entry.get("sha256") or sha256_of(p)):
                    entry["sha256"] = entry.get("sha256") or sha256_of(p)
                    entry[label] = {"ok": True, "note": "already there, identical"}
                    done += 1
                    continue
            except OSError:
                pass
            problems.append(f"{rel} already exists at the destination and is different. Not overwritten; check it by hand.")
            entry[label] = {"ok": False, "note": "exists and differs"}
            continue
        try:
            src_hash, dst_hash = copy_with_hash(p, dst)
        except OSError as e:
            problems.append(f"{rel} would not copy ({e.__class__.__name__}: {e}). Stopped this copy.")
            entry[label] = {"ok": False, "note": str(e)}
            break
        entry["sha256"] = src_hash
        if src_hash != dst_hash:
            problems.append(f"{rel} copied but the check failed (the copy does not match the original). Stopped.")
            entry[label] = {"ok": False, "note": "hash mismatch"}
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--dest", required=True, help="the session drive or folder")
    ap.add_argument("--second", default=None, help="the second copy (cloud drive folder)")
    ap.add_argument("--name", required=True, help="session name, e.g. 'Johnson family beach'")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=None, help="seconds to work before pausing cleanly (run again to continue)")
    a = ap.parse_args()

    src = Path(a.source).expanduser()
    if not src.is_dir():
        say(f"STOP: I can't find the source at {src}. Is the card in?")
        sys.exit(2)
    date = a.date or datetime.now().strftime("%Y-%m-%d")
    folder = f"{date} {a.name.strip()}"
    dest = Path(a.dest).expanduser() / folder
    second = Path(a.second).expanduser() / folder if a.second else None

    files, skipped = inventory(src)
    total_bytes = sum(s for _, s in files if s > 0)
    media = [p for p, s in files if p.suffix.lower() in MEDIA]
    say(f"Source: {src}\n  {len(files)} files, {human(total_bytes)}, {len(media)} photos or clips")
    if not files:
        say("STOP: the card looks empty. Nothing to copy.")
        sys.exit(2)

    problems = []
    for label, root in (("dest", dest.parent), ("second", second.parent if second else None)):
        if root is None:
            continue
        if not root.exists():
            problems.append(f"The {'session drive' if label == 'dest' else 'second copy'} folder {root} is not there. Is the drive plugged in?")
            continue
        fb = free_bytes(root)
        if fb is not None and fb < total_bytes * 1.05:
            problems.append(f"Not enough room on {root}: {human(fb)} free, {human(total_bytes)} needed.")
    if problems:
        for p in problems:
            say("STOP: " + p)
        sys.exit(2)

    if a.dry_run:
        say(f"Would copy to {dest}" + (f" and {second}" if second else "") + ". Nothing done (dry run).")
        return

    studio = dest / "_studio"
    studio.mkdir(parents=True, exist_ok=True)
    mpath = studio / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {"session": folder, "source": str(src), "files": {}}
    manifest["source"] = str(src)
    manifest["dest"] = str(dest)
    manifest["second"] = str(second) if second else None
    manifest["skipped_system_files"] = skipped
    manifest["started"] = manifest.get("started") or datetime.now().isoformat(timespec="seconds")

    t0 = time.time()
    save = lambda: mpath.write_text(json.dumps(manifest, indent=1))
    say(f"Copying to {dest}")
    problems += run_copy("dest", files, src, dest, manifest, False, save, a.budget)
    save()
    if second and not problems:
        say(f"Second copy to {second}")
        (second / "_studio").mkdir(parents=True, exist_ok=True)
        left = (a.budget - (time.time() - t0)) if a.budget else None
        problems += run_copy("second", files, src, second, manifest, False, save, left if (left is None or left > 5) else 5)
        save()
        (second / "_studio" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if "PAUSED" in problems:
        done = sum(1 for e in manifest["files"].values() if e.get("dest", {}).get("ok"))
        say(f"PAUSED after {time.time() - t0:.0f} s: {done} of {len(files)} files copied and checked. Run the same command again to continue.")
        sys.exit(3)

    # what's on it, for the report
    kinds = {}
    for p, s in files:
        kinds[p.suffix.lower() or "(none)"] = kinds.get(p.suffix.lower() or "(none)", 0) + 1
    sample = [p for p in media[:3]] + ([media[-1]] if len(media) > 3 else [])
    infos = {str(p.relative_to(src)): media_info(p) for p in sample}
    taken = sorted(v["taken"] for v in infos.values() if v.get("taken"))

    ok_dest = sum(1 for e in manifest["files"].values() if e.get("dest", {}).get("ok"))
    ok_second = sum(1 for e in manifest["files"].values() if e.get("second", {}).get("ok")) if second else None
    elapsed = time.time() - t0
    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    manifest["problems"] = problems
    manifest["taken"] = (f"{taken[0]} to {taken[-1]}" if len(taken) >= 2 else taken[0]) if taken else None
    manifest["work_seconds"] = manifest.get("work_seconds", 0) + elapsed  # across resumed runs
    mpath.write_text(json.dumps(manifest, indent=1))

    lines = [f"# Morning report · {folder}", ""]
    if problems:
        lines += ["## Needs you first", ""] + [f"- {p}" for p in problems] + [""]
        lines += [f"**Not finished.** {ok_dest} of {len(files)} files are copied and checked on the session drive. The card has not been touched; run it again when the problem is fixed and it picks up where it left off.", ""]
    else:
        lines += [f"**All {len(files)} files ({human(total_bytes)}) have been safely backed up and verified.** Every one was checked against the card, byte for byte."
                  + (" They are on your drive and in your second copy." if second else ""), ""]
    skipped_note = f" ({skipped} hidden Mac system file{'s' if skipped != 1 else ''} left behind, as they should be)" if skipped else ""
    lines += ["## What's on it", "",
              f"- {len(media)} photos or clips, " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda t: -t[1])) + skipped_note,
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
    lines += ["", "## The card", "", "Untouched. " + ("It is safe to format when you're ready." if not problems else "Keep it."),
              "", f"_{len(files)} files · {human(total_bytes)} · {elapsed:.0f} seconds · nothing deleted, nothing moved, nothing posted._"]
    report = "\n".join(lines) + "\n"
    (studio / "morning-report.md").write_text(report)
    # the index (when each photo was taken, which camera) and the same report as a
    # page she can look at; neither may ever break the backup
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
