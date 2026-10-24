#!/usr/bin/env python3
"""The card ledger: recognize a card the Studio has already backed up, before
a byte is copied, so "backup now" twice is harmless. ~/.studio/cards.json
maps a card's fingerprint to the session(s) that hold its photos.

A fingerprint is what the card itself tells us, read in a second or two:
the volume's UUID (when the Mac reports one), the number of files, their
total size, the first and last file names, and the first megabyte of a
handful of files hashed. Add or remove one photo and it is a different card
as far as the ledger is concerned, which is what we want: a card reused
with new photos on it must be backed up again.

    python3 cards.py fingerprint /Volumes/EOS_DIGITAL
    python3 cards.py check /Volumes/EOS_DIGITAL          prints the session that holds it, or "new"
    python3 cards.py register /Volumes/EOS_DIGITAL "<session folder>"
"""
import argparse
import hashlib
import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
LEDGER = HOME / "cards.json"
SKIP_DIRS = {".fseventsd", ".Spotlight-V100", ".Trashes", ".TemporaryItems", "System Volume Information", "_studio"}


def volume_uuid(path):
    try:
        out = subprocess.run(["diskutil", "info", "-plist", str(path)], capture_output=True, timeout=10).stdout
        return plistlib.loads(out).get("VolumeUUID")
    except Exception:  # noqa: BLE001  (not a Mac, not a volume, diskutil missing)
        return None


def files_on(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            p = Path(dirpath) / fn
            try:
                files.append((p.relative_to(root).as_posix(), p.stat().st_size))
            except OSError:
                pass
    files.sort()
    return files


def fingerprint(root):
    root = Path(root)
    files = files_on(root)
    if not files:
        return None
    sample = [files[0], files[len(files) // 2], files[-1]] + files[1:4]
    h = hashlib.sha256()
    for rel, size in sample:
        h.update(rel.encode())
        h.update(str(size).encode())
        try:
            with open(root / rel, "rb") as f:
                h.update(f.read(1024 * 1024))
        except OSError:
            pass
    return {
        "uuid": volume_uuid(root),
        "name": root.name,
        "count": len(files),
        "bytes": sum(s for _, s in files),
        "first": files[0][0],
        "last": files[-1][0],
        "sample": h.hexdigest()[:24],
    }


def key(fp):
    return f"{fp['count']}:{fp['bytes']}:{fp['sample']}"


def load():
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text())
        except ValueError:
            pass
    return {"cards": {}}


def save(ledger):
    HOME.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1))


def check(root):
    """The session that already holds this card's photos and is still on disk, or None."""
    fp = fingerprint(root)
    if not fp:
        return None, None
    entry = load()["cards"].get(key(fp))
    if not entry:
        return fp, None
    from where import locate
    live = []
    for s in entry.get("sessions", []):
        try:
            root, studio = locate(s["folder"])  # still on disk, before or after the night settled
        except SystemExit:
            continue
        live.append(dict(s, root=str(root), studio=str(studio)))
    return fp, (live[-1] if live else None)


def register(root, session):
    fp = fingerprint(root)
    if not fp:
        sys.exit("STOP: nothing on that card to fingerprint.")
    ledger = load()
    entry = ledger["cards"].setdefault(key(fp), {"fingerprint": fp, "sessions": []})
    entry["fingerprint"] = fp
    folder = str(Path(session).resolve())
    if not any(s["folder"] == folder for s in entry["sessions"]):
        entry["sessions"].append({"folder": folder, "when": datetime.now().isoformat(timespec="seconds")})
    save(ledger)
    return fp


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fingerprint")
    f.add_argument("card")
    c = sub.add_parser("check")
    c.add_argument("card")
    r = sub.add_parser("register")
    r.add_argument("card")
    r.add_argument("session")
    a = ap.parse_args()
    if a.cmd == "fingerprint":
        print(json.dumps(fingerprint(a.card), indent=1))
    elif a.cmd == "check":
        fp, held = check(a.card)
        if not fp:
            print("empty")
        elif held:
            print(f"already safe in {held['folder']} (backed up {held['when'][:16].replace('T', ' ')})")
        else:
            print("new")
    else:
        fp = register(a.card, a.session)
        print(f"registered: {fp['count']} files, {fp['bytes'] / 1e9:.1f} GB -> {a.session}")


if __name__ == "__main__":
    main()
