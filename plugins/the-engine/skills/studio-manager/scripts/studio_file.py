#!/usr/bin/env python3
"""The Studio File: what the Studio knows about the photographer, asked once, on the first
run, and never again. Lives in ~/.studio/ as studio.json (what the scripts
read) with a plain-words mirror in studio-file.md (what they can read).

    python3 studio_file.py show
    python3 studio_file.py drives                         the drives it can see, to pick from
    python3 studio_file.py set --drive "/Volumes/Big Kahuna" [--second "/path"] \
        [--example "2026-10-18 Smith Family" | --folder-pattern "{shoot}, {date}" --date-format "%b %-d %Y"] \
        [--file-names original|shoot]
    python3 studio_file.py pattern "Smith Family - 10.18.26"    show what a pasted example teaches it
    python3 studio_file.py render "Smith Family" 2026-10-18     the folder name their pattern gives

Naming: a folder pattern made of {shoot} and {date}, with a strftime format
for the date, worked out from an example folder name they paste (so their
drive looks the same before and after the Studio) or picked from two
offered patterns. Photos either keep their original frame names or take the
shoot's name with a running number ("shoot").
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JSON = HOME / "studio.json"
MD = HOME / "studio-file.md"

# the same order as the skill offers them: 1 is the recommended one (date first, so folders line up)
OFFERED = [
    {"label": "2026-10-18 Smith Family", "folder_pattern": "{date} {shoot}", "date_format": "%Y-%m-%d"},
    {"label": "Smith Family, Oct 18 2026", "folder_pattern": "{shoot}, {date}", "date_format": "%b %-d %Y"},
]

# date spellings a photographer might use in a folder name, most specific first
DATE_FORMS = [
    (r"(?<![A-Za-z0-9])(\d{4})-(\d{2})-(\d{2})(?![A-Za-z0-9])", "%Y-%m-%d"),
    (r"(?<![A-Za-z0-9])(\d{4})_(\d{2})_(\d{2})(?![A-Za-z0-9])", "%Y_%m_%d"),
    (r"(?<![A-Za-z0-9])(\d{4})\.(\d{2})\.(\d{2})(?![A-Za-z0-9])", "%Y.%m.%d"),
    (r"(?<![A-Za-z0-9])(\d{4})(\d{2})(\d{2})(?![A-Za-z0-9])", "%Y%m%d"),
    (r"(?<![A-Za-z0-9])(\d{1,2})-(\d{1,2})-(\d{4})(?![A-Za-z0-9])", "%m-%d-%Y"),
    (r"(?<![A-Za-z0-9])(\d{1,2})\.(\d{1,2})\.(\d{4})(?![A-Za-z0-9])", "%m.%d.%Y"),
    (r"(?<![A-Za-z0-9])(\d{1,2})_(\d{1,2})_(\d{4})(?![A-Za-z0-9])", "%m_%d_%Y"),
    (r"(?<![A-Za-z0-9])(\d{1,2})-(\d{1,2})-(\d{2})(?![A-Za-z0-9])", "%m-%d-%y"),
    (r"(?<![A-Za-z0-9])(\d{1,2})\.(\d{1,2})\.(\d{2})(?![A-Za-z0-9])", "%m.%d.%y"),
    (r"(?<![A-Za-z0-9])(\d{2})(\d{2})(\d{2})(?![A-Za-z0-9])", "%m%d%y"),
    (r"(?<![A-Za-z0-9])(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})(?![A-Za-z0-9])", "%B %-d, %Y"),
    (r"(?<![A-Za-z0-9])(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}) (\d{4})(?![A-Za-z0-9])", "%B %-d %Y"),
    (r"(?<![A-Za-z0-9])(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.? (\d{1,2}), (\d{4})(?![A-Za-z0-9])", "%b %-d, %Y"),
    (r"(?<![A-Za-z0-9])(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.? (\d{1,2}) (\d{4})(?![A-Za-z0-9])", "%b %-d %Y"),
    (r"(?<![A-Za-z0-9])(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})(?![A-Za-z0-9])", "%-d %b %Y"),
    (r"(?<![A-Za-z0-9])(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})(?![A-Za-z0-9])", "%B %Y"),
    (r"(?<![A-Za-z0-9])(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})(?![A-Za-z0-9])", "%b %Y"),
    (r"(?<![A-Za-z0-9])(\d{4})(?![A-Za-z0-9])", "%Y"),
]


def load():
    if JSON.exists():
        try:
            return json.loads(JSON.read_text())
        except ValueError:
            pass
    return {}


def save(sf):
    HOME.mkdir(parents=True, exist_ok=True)
    sf["updated"] = datetime.now().isoformat(timespec="seconds")
    JSON.write_text(json.dumps(sf, indent=1, ensure_ascii=False))
    MD.write_text(as_markdown(sf))


def as_markdown(sf):
    d, n = sf.get("drives", {}), sf.get("naming", {})
    lines = ["# Studio File", "", "What the Studio knows about you. Asked once; change any line by telling the Studio.", "",
             "## Drives", "",
             f"- Sessions go on: `{d.get('session', '(not set)')}`",
             f"- Second copy: `{d.get('second')}`" if d.get("second") else "- Second copy: none (that's fine)", "",
             "## Naming", ""]
    if n.get("folder_pattern"):
        lines += [f"- Shoot folders look like: **{render(n, 'Smith Family', date(2026, 10, 18))}**",
                  f"- Pattern: `{n['folder_pattern']}` with the date as `{n['date_format']}`"
                  + (f", learned from your example `{n['example']}`" if n.get("example") else "")]
    else:
        lines += ["- Shoot folders: (not set)"]
    lines += [f"- Photos: {'keep their original frame names' if n.get('file_names', 'shoot') == 'original' else 'take the shoot name and a running number, with the original frame name kept at the end'}",
              "", "## Client notes", ""]
    c = sf.get("note", {})
    if not c:
        lines += ["- (not asked yet)"]
    elif not c.get("on"):
        lines += ["- No notes, thanks."]
    else:
        tones = {"warm": "warm and personal", "plain": "short and plain", "playful": "playful"}
        lines += ["- A note to the client is drafted with the sneak peeks, for you to copy and send.",
                  "- Written to match a note you sent before:" if c.get("sample") else f"- Tone: {tones.get(c.get('tone', 'warm'), 'warm and personal')}"]
        if c.get("sample"):
            lines += ["", "  > " + c["sample"].strip().replace("\n", "\n  > "), ""]
        lines += [f"- Signed: {c['sign_off']}" if c.get("sign_off") else "- Sign-off: (not set)"]
    if sf.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {x['on']}: {x['note']}" for x in sf["notes"]]
    lines += ["", f"_Updated {sf.get('updated', '')}_", ""]
    return "\n".join(lines)


PHOTO_EXT = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}
SHOOT_WORDS = ("shoot", "session", "client", "wedding", "photo", "raw", "job", "work")
DATED = re.compile(r"(19|20)\d\d[-._ ]?\d\d[-._ ]?\d\d|\b(19|20)\d\d\b")


def _looks_like_shoot(folder, limit=40):
    """A folder of dated subfolders, or of photos, is a shoot folder. Returns (score, shoots)."""
    dated = photos = subs = 0
    try:
        for i, p in enumerate(folder.iterdir()):
            if i >= limit:
                break
            if p.name.startswith("."):
                continue
            if p.is_dir():
                subs += 1
                if DATED.search(p.name):
                    dated += 1
            elif p.suffix.lower() in PHOTO_EXT:
                photos += 1
    except OSError:
        return 0, 0
    return dated * 3 + (2 if photos >= 5 else 0) + (1 if subs >= 3 else 0), subs


def shoot_folders(drive, limit=2):
    """Top-level folders on a drive that look like where their shoots live, best first, at most `limit`."""
    found = []
    try:
        tops = [p for p in Path(drive).iterdir() if p.is_dir() and not p.name.startswith(".")]
    except OSError:
        return []
    for p in tops[:60]:
        if p.name in ("Backups.backupdb", "System Volume Information", "$RECYCLE.BIN"):
            continue
        score, subs = _looks_like_shoot(p)
        if any(w in p.name.lower() for w in SHOOT_WORDS):
            score += 2
        if score >= 3:
            found.append({"path": str(p), "name": p.name, "shoots": subs, "score": score})
    found.sort(key=lambda f: -f["score"])
    return found[:limit]


def drives():
    """Volumes they might mean; the Mac itself, camera cards, Time Machine and tiny helper volumes left out.
    Each carries its likely shoot folders; the one that already has shoots on it is `recommended`."""
    out = []
    if not Path("/Volumes").is_dir():
        return out
    for v in Path("/Volumes").iterdir():
        try:
            st = os.statvfs(v)
        except OSError:
            continue
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        if total < 8 * 1024 ** 3 or v.name in ("Macintosh HD", "Recovery") or (v / "DCIM").is_dir():
            continue  # too small to be a session drive, the Mac itself, or a camera card
        if (v / "Backups.backupdb").is_dir() or (v / ".com.apple.timemachine.supported").exists():
            continue  # Time Machine
        folders = shoot_folders(v)
        root_score, _ = _looks_like_shoot(v)
        out.append({"path": str(v), "name": v.name, "total_gb": round(total / 1024 ** 3),
                    "free_gb": round(free / 1024 ** 3), "shoot_folders": folders,
                    "has_shoots": bool(folders) or root_score >= 3, "recommended": False})
    out.sort(key=lambda d: (-int(d["has_shoots"]), -d["total_gb"]))
    if out:
        out[0]["recommended"] = True
    return out


def on_internal_disk(path):
    """True when a folder sits on the computer's own built-in disk rather than an external drive.
    Mac: same device as the startup disk (and not under /Volumes). Windows: the system drive letter.
    Used for the teachable moment in setup (Dustin, Oct 30): shoots belong on an external drive."""
    p = Path(path).expanduser()
    try:
        if os.name == "nt":
            sysdrive = (os.environ.get("SystemDrive") or "C:").upper()
            return p.resolve().drive.upper() == sysdrive
        if str(p).startswith("/Volumes/"):
            return False  # an external drive, plugged in or not
        here = p if p.exists() else next((q for q in p.parents if q.exists()), Path("/"))
        if str(here.resolve()).startswith("/Volumes/"):
            return False
        return os.stat(here).st_dev == os.stat("/").st_dev
    except OSError:
        return False


def learn_pattern(example):
    """From a folder name they pasted: where the date is, how it is written, what sits between."""
    ex = example.strip()
    for rx, fmt in DATE_FORMS:
        m = re.search(rx, ex, re.IGNORECASE)
        if not m:
            continue
        try:  # make sure the spelling really parses as that format
            datetime.strptime(m.group(0).replace("Sept", "Sep"), fmt.replace("%-d", "%d"))
        except ValueError:
            continue
        before, after = ex[:m.start()], ex[m.end():]
        words = lambda s: re.search(r"[A-Za-z0-9]", s) is not None  # noqa: E731
        if words(before):
            # the shoot comes first; whatever punctuation sits between it and the date is the separator
            sep = re.search(r"[^A-Za-z0-9]*$", before).group(0)
            shoot = before[:len(before) - len(sep)]
            pat = "{shoot}" + sep + "{date}" + after
        elif words(after):
            sep = re.match(r"^[^A-Za-z0-9]*", after).group(0)
            shoot = after[len(sep):]
            pat = before + "{date}" + sep + "{shoot}"
        else:
            return None
        got = {"folder_pattern": pat, "date_format": fmt, "example": ex, "example_shoot": shoot.strip()}
        if " " not in shoot.strip() and "_" in shoot:
            got["space"] = "_"  # they write Smith_Family, so the Studio does too
        return got
    return None


def render(naming, shoot, when):
    """The folder name their pattern gives this shoot on this date."""
    pat = naming.get("folder_pattern") or "{shoot}, {date}"
    fmt = naming.get("date_format") or "%b %-d %Y"
    if isinstance(when, str):
        when = datetime.fromisoformat(when[:19] if len(when) > 10 else when)
    out = pat.replace("{date}", when.strftime(fmt)).replace("{shoot}", shoot.replace(" ", naming.get("space", " ")))
    return re.sub(r'[\\/:*?"<>|]+', " ", out).strip(" .")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("drives")
    i = sub.add_parser("internal", help="is this folder on the computer's own disk? prints yes or no")
    i.add_argument("path")
    s = sub.add_parser("set")
    s.add_argument("--drive")
    s.add_argument("--second")
    s.add_argument("--no-second", action="store_true")
    s.add_argument("--example", help="a folder name from a past shoot to match")
    s.add_argument("--folder-pattern")
    s.add_argument("--date-format")
    s.add_argument("--offered", type=int, help="1 or 2: one of the two offered patterns")
    s.add_argument("--file-names", choices=["original", "shoot"])
    s.add_argument("--note", help="a line to remember about their setup (e.g. shoots kept on the computer's own disk, said OK)")
    p = sub.add_parser("pattern")
    p.add_argument("example")
    r = sub.add_parser("render")
    r.add_argument("shoot")
    r.add_argument("date")
    a = ap.parse_args()

    if a.cmd == "show":
        sf = load()
        print(as_markdown(sf) if sf else "No Studio File yet. The first 'backup now' sets it up.")
        return
    if a.cmd == "drives":
        found = drives()
        if not found:
            print("No drives plugged in besides the Mac itself.")
        for d in found:
            tag = "   (recommended: already has shoots on it)" if d["recommended"] and d["has_shoots"] else ("   (recommended)" if d["recommended"] else "")
            print(f"{d['path']}   {d['total_gb']:,} GB, {d['free_gb']:,} GB free{tag}")
            for f in d["shoot_folders"]:
                print(f"    shoot folder: {f['name']}   {f['shoots']} folders in there")
        return
    if a.cmd == "internal":
        print("yes" if on_internal_disk(a.path) else "no")
        return
    if a.cmd == "pattern":
        got = learn_pattern(a.example)
        if not got:
            sys.exit("Could not find a date in that name. Ask where the date goes, or offer the two patterns.")
        print(json.dumps(got, indent=1))
        print("Smith Family on Oct 18, 2026 would be:", render(got, "Smith Family", date(2026, 10, 18)))
        return
    if a.cmd == "render":
        print(render(load().get("naming", {}), a.shoot, a.date))
        return

    sf = load()
    d = sf.setdefault("drives", {})
    n = sf.setdefault("naming", {})
    if a.note:
        sf.setdefault("notes", []).append({"on": date.today().isoformat(), "note": a.note})
    if a.drive:
        if not Path(a.drive).is_dir():
            sys.exit(f"STOP: {a.drive} is not a folder I can see.")
        d["session"] = str(Path(a.drive).expanduser().resolve())
    if a.second:
        if not Path(a.second).is_dir():
            sys.exit(f"STOP: {a.second} is not a folder I can see.")
        d["second"] = str(Path(a.second).expanduser().resolve())
    if a.no_second:
        d["second"] = None
    if a.example:
        got = learn_pattern(a.example)
        if not got:
            sys.exit("Could not find a date in that example.")
        n.update(got)
    if a.offered:
        n.update(OFFERED[a.offered - 1])
        n.pop("example", None)
    if a.folder_pattern:
        n["folder_pattern"] = a.folder_pattern
        n.pop("example", None)
    if a.date_format:
        n["date_format"] = a.date_format
    if a.file_names:
        n["file_names"] = a.file_names
    save(sf)
    print(as_markdown(sf))


if __name__ == "__main__":
    main()
