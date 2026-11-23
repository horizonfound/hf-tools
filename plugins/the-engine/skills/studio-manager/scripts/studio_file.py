#!/usr/bin/env python3
"""The Studio File: what the Studio knows about the photographer, asked once, on the first
run, and never again. Lives in ~/.studio/ as studio.json (what the scripts
read) with a plain-words mirror in studio-file.md (what they can read).

    python3 studio_file.py show
    python3 studio_file.py drives                         the drives it can see, to pick from
    python3 studio_file.py defaults [--drive "<path>"] [--computer] [--dry-run]
                                                          the first backup's setup, chosen by itself (asks nothing)
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
import this_computer  # noqa: E402  (the Mac way and the PC way of everything, in one place)
this_computer.utf8_output()

HOME = Path(os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
JSON = HOME / "studio.json"
MD = HOME / "studio-file.md"

# The two ways offered. 1 is the one every new backup gets (Nicole and Dustin, Nov 22 to 23: the shoot's name,
# then the date, no periods: "Aurora_11-22-26"); 2 is year first, for anyone who wants folders in date order.
OFFERED = [
    {"label": "Smith Family_10-18-26", "folder_pattern": "{shoot}_{date}", "date_format": "%m-%d-%y"},
    {"label": "2026-10-18 Smith Family", "folder_pattern": "{date} {shoot}", "date_format": "%Y-%m-%d"},
]
# What was offered before Nov 23. A Studio File still on one of these moves to OFFERED[0] once, for its next
# backups (Nicole, Nov 23: "all new name"). Folders already on a drive are never renamed by this.
OFFERED_BEFORE = [
    ("{date} {shoot}", "%Y-%m-%d"),
    ("{shoot}, {date}", "%b %-d %Y"),
]
NAMING_SINCE = 9   # the version whose naming a Studio File has been brought to (so a later choice is never undone)

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


def newer_naming(sf):
    """Bring a Studio File's naming to today's, once. True when something changed. A naming that was one of the
    two offered before Nov 23 becomes OFFERED[0]; a way of their own (learned from a folder they pasted) is left
    exactly as it is. Either way the file is marked, so choosing year first later on the report sticks."""
    n = sf.get("naming")
    if not isinstance(n, dict) or not n.get("folder_pattern") or n.get("since"):
        return False
    if (n.get("folder_pattern"), n.get("date_format")) in OFFERED_BEFORE:
        n.update(OFFERED[0])
        n.pop("example", None)
        sf.setdefault("notes", []).append({"on": date.today().isoformat(), "note":
                                           "Folders for new backups are now named like Smith Family_10-18-26. "
                                           "Folders already on your drive keep their names."})
    n["since"] = NAMING_SINCE
    return True


def load():
    if JSON.exists():
        try:
            sf = json.loads(JSON.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        if isinstance(sf, dict) and newer_naming(sf):
            try:
                save(sf)
            except OSError:
                pass     # a Studio File that can't be written today is still read the new way
        return sf
    return {}


def save(sf):
    HOME.mkdir(parents=True, exist_ok=True)
    sf["updated"] = datetime.now().isoformat(timespec="seconds")
    if isinstance(sf.get("naming"), dict) and sf["naming"].get("folder_pattern"):
        sf["naming"].setdefault("since", NAMING_SINCE)
    JSON.write_text(json.dumps(sf, indent=1, ensure_ascii=False), encoding="utf-8")
    MD.write_text(as_markdown(sf), encoding="utf-8")


CLIENT_NOTES = False   # True puts "Client notes written ..." back in the glance (notes to clients were taken out Nov 23)


def as_markdown(sf):
    d, n = sf.get("drives", {}), sf.get("naming", {})
    import brand
    who = brand.name()
    lines = ["# Studio File", "", f"What {who} knows about you. Asked once; change any line by telling {who}.", ""]
    if sf.get("name"):
        lines += [f"- You call your helper **{sf['name']}**.", ""]
    lines += [
             "## Drives", "",
             f"- Sessions go on: `{d.get('session', '(not set)')}`" + (f" ({d['session_label']})" if d.get("session_label") else ""),
             (f"- Second copy: `{d.get('second')}`" + (f" ({d['second_label']})" if d.get("second_label") else ""))
             if d.get("second") else "- Second copy: none (that's fine)", "",
             "## Naming", ""]
    if n.get("folder_pattern"):
        lines += [f"- Shoot folders look like: **{render(n, 'Smith Family', date(2026, 10, 18))}**",
                  f"- Pattern: `{n['folder_pattern']}` with the date as `{n['date_format']}`"
                  + (f", learned from your example `{n['example']}`" if n.get("example") else "")]
    else:
        lines += ["- Shoot folders: (not set)"]
    lines += [f"- Photos: {'keep their original frame names' if n.get('file_names', 'shoot') == 'original' else 'take the shoot name and a running number, with the original frame name kept at the end'}",
              ]
    # Notes to clients are no longer written with a backup (Nicole and Dustin, Nov 23), so nothing about them is
    # shown unless this photographer had set up how they write before; that is kept, never thrown away.
    c = sf.get("note", {})
    if c and c.get("on"):
        lines += ["", "## Client notes", ""]
        tones = {"warm": "warm and personal", "plain": "short and plain", "playful": "playful"}
        lines += ["- How you write to clients, kept from before (notes to clients are no longer written with a backup).",
                  "- Written to match a note you sent before:" if c.get("sample") else f"- Tone: {tones.get(c.get('tone', 'warm'), 'warm and personal')}"]
        if c.get("sample"):
            lines += ["", "  > " + c["sample"].strip().replace("\n", "\n  > "), ""]
        lines += [f"- Signed: {c['sign_off']}" if c.get("sign_off") else "- Sign-off: (not set)"]
    if sf.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {x['on']}: {x['note']}" for x in sf["notes"]]
    lines += ["", f"_Updated {sf.get('updated', '')}_", ""]
    return "\n".join(lines)


PHOTO_EXT = {".cr2", ".cr3", ".arw", ".nef", ".dng", ".raf", ".orf", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}
# Whole words only (Nov 19 review: as letters inside a word, "raw" made Drawings a shoot folder, "work" Homework
# and "photo" an Apple Photos library).
SHOOT_WORDS = re.compile(r"(?<![a-z])(photo ?shoots?|shoots?|sessions?|clients?|weddings?|photos?|photography|raws?|jobs?)(?![a-z])")
# Never where shoots go, whatever is inside: a package (Finder shows it as one file, so nothing put inside it can
# be browsed), and folders named for something else that often holds dated folders too.
PACKAGES = (".photoslibrary", ".photolibrary", ".aplibrary", ".lrlibrary", ".lrdata", ".lrcat-data", ".cocatalog",
            ".cosessiondb", ".fcpbundle", ".imovielibrary", ".tvlibrary", ".musiclibrary", ".app", ".sparsebundle",
            ".backupbundle", ".bundle", ".pkg", ".framework", ".logicx", ".band", ".dvdmedia")
NOT_SHOOTS = re.compile(r"(?<![a-z])(backups?|back ?ups?|time machine|exports?|exported|delivered|deliver(y|ies)|finals?|"
                        r"edit(s|ed)?|librar(y|ies)|catalogs?|trash|downloads?|installers?|applications?)(?![a-z])")
# A memory card is never a drive, whichever camera wrote it: these sit at the top of a card.
CARD_FOLDERS = ("DCIM", "PRIVATE/M4ROOT", "PRIVATE/AVCHD", "PRIVATE/SONY", "AVCHD", "M4ROOT", "XDROOT", "CONTENTS/CLIPS001",
                "MP_ROOT", "AVF_INFO")
# a year-first date, a bare year, or the date our own folders end in since Nov 23 ("Aurora_11-22-26")
DATED = re.compile(r"(19|20)\d\d[-._ ]?\d\d[-._ ]?\d\d|\b(19|20)\d\d\b|(?<![0-9])\d{1,2}-\d{1,2}-\d{2}(?![0-9])")


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
        low = p.name.lower()
        if low.endswith(PACKAGES) or p.is_symlink():
            continue   # a package or a link: never offered, never chosen
        score, subs = _looks_like_shoot(p)
        named = bool(SHOOT_WORDS.search(low))
        if named:
            score += 2
        if score >= 3:
            # sure: sure enough to be chosen with nobody asked (the first backup, and the report's next drive).
            # It must be named for shoots, not named for something else, and have folders in it. Anything less
            # is only ever a suggestion beside a question; unasked, photos go right on the drive, in plain sight.
            found.append({"path": str(p), "name": p.name, "shoots": subs, "score": score,
                          "sure": named and not NOT_SHOOTS.search(low) and subs >= 2})
    found.sort(key=lambda f: -f["score"])
    return found[:limit]


def looks_like_card(top):
    """True when this folder is the top of a memory card: one of the folders a camera makes sits there. A card
    formatted on the computer and never put in a camera has none of them; see maybe_card in drives()."""
    top = Path(top)
    for rel in CARD_FOLDERS:
        try:
            if top.joinpath(*rel.split("/")).is_dir():
                return True
        except OSError:
            return True    # it will not even say: never treated as a drive
    return False


def card_above(path):
    """The top of the memory card a folder is on (the folder itself, or one above it, up to the top of its
    drive), or None when it is not on a card."""
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        p = Path(path).expanduser()
    for q in (p, *p.parents):
        if q == q.parent:
            break          # the very top of the computer's own disk is never a card
        if looks_like_card(q):
            return q
        try:
            if os.path.ismount(str(q)):
                break
        except OSError:
            break
    return None


def can_write(folder):
    """Can a file be made in this folder right now? (A drive a Mac can only read, such as one formatted for
    Windows, or one that came back read-only after a bad eject, says no.) The test file is ours and is removed."""
    probe = Path(folder) / ".studio-write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
    except OSError:
        return False
    try:
        probe.unlink()
    except OSError:
        pass
    return True


def room_needed(source):
    """Bytes a backup of this card or folder needs on a drive (its files, 5% and 2 GB to spare, as the backup's
    own check asks), or None when it cannot be told."""
    try:
        import cards
        return sum(s for _, s in cards.files_on(Path(source))) * 1.05 + 2 * 1024 ** 3
    except Exception:  # noqa: BLE001
        return None


def cannot_use(place, need=None, found=None):
    """Plain words when photos cannot go here today (it cannot be written to, or has no room for this card);
    None when they can. Asked BEFORE a drive is ever saved (Nov 19 review: the first backup saved its drive
    first and checked afterwards, so a drive that could not be used stayed on file and stopped every backup)."""
    place = Path(place)
    found = drives() if found is None else found
    row = next((x for x in found if _inside(place, x["path"])), None)
    name = row["name"] if row else (this_computer.drive_words(place) or f"this {this_computer.COMPUTER}")
    if not place.is_dir():
        return f"{name} is not there right now."
    if not can_write(place):
        return f"I can't save photos to {name}: it can be read but not written to."
    if need:
        free = row["free"] if row and row.get("free") else this_computer.free_bytes(place)
        if free is not None and free < need:
            return (f"{name} does not have room for this card: about {need / 1e9:.0f} GB is needed and "
                    f"{free / 1e9:.0f} GB is free.")
    return None


def drives():
    """Volumes they might mean; the computer's own disk, camera cards, Time Machine and tiny helper volumes left out.
    Each carries its likely shoot folders; the one that already has shoots on it is `recommended`. maybe_card:
    the computer says it is removable media (a card in a reader, or a USB stick), so it is never chosen with
    nobody asked."""
    out = []
    for vol in this_computer.volumes():   # /Volumes on a Mac, drive letters on a PC
        v = Path(vol["path"])
        total, free = vol["total"], vol["free"]
        try:
            if total < 8 * 1024 ** 3 or vol["system"] or looks_like_card(v):
                continue  # too small to be a session drive, the computer itself, or a camera card
            if (v / "Backups.backupdb").is_dir() or (v / ".com.apple.timemachine.supported").exists():
                continue  # Time Machine
        except OSError:
            continue
        folders = shoot_folders(v)
        root_score, _ = _looks_like_shoot(v)
        out.append({"path": str(v), "name": vol["shown"], "total_gb": round(total / 1024 ** 3),
                    "free_gb": round(free / 1024 ** 3), "free": free, "shoot_folders": folders,
                    "maybe_card": this_computer.removable(vol) is True,
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
    pretend = this_computer._pretend_volumes()   # the tests' switch: the drives are the pretend ones, and
    if pretend is not None:                      # anything not on one of them is the computer's own disk
        return not any(_inside(p, v["path"]) for v in pretend if not v.get("system"))
    try:
        if os.name == "nt":
            sysdrive = (os.environ.get("SystemDrive") or "C:").upper()
            return p.resolve().drive.upper() == sysdrive
        if str(p).startswith("/Volumes/"):  # pc-ok: the Mac branch; a PC returned above
            return False  # an external drive, plugged in or not
        here = p if p.exists() else next((q for q in p.parents if q.exists()), Path("/"))
        if str(here.resolve()).startswith("/Volumes/"):  # pc-ok: the Mac branch
            return False
        return os.stat(here).st_dev == os.stat("/").st_dev
    except OSError:
        return False


# ---------------------------------------------------------------- a PC's drive letters move

def _letter(path):
    """The drive letter a PC path starts with ("E" for "E:\\Photo Shoots"), or None."""
    m = re.match(r"\s*([A-Za-z]):", str(path or ""))
    return m.group(1).upper() if m else None


def drive_facts(path):
    """(the drive's name, its own number) for the drive a saved folder is on. Only on a PC, where the Studio File
    keeps the drive by its letter and Windows hands letters out as things are plugged in, so another day the
    memory card can get the letter the photo drive had. A Mac's drive name is in the path itself: (None, None)."""
    if not this_computer.WINDOWS:
        return None, None
    letter = _letter(path)
    for v in this_computer.volumes() if letter else []:   # unproven on a real PC
        if _letter(v["path"]) == letter:
            return v.get("name"), v.get("id")
    return None, None


def keep_drive_facts(d, key):
    """Saved beside drives[key] at setup, on a PC only: which drive that letter was (its name and number)."""
    for k in (f"{key}_label", f"{key}_id"):
        d.pop(k, None)
    if this_computer.WINDOWS and d.get(key):
        label, vid = drive_facts(d[key])
        if label:
            d[f"{key}_label"] = label
        if vid:
            d[f"{key}_id"] = vid


def drive_moved(d, key):
    """On a PC, plain words when the drive at the saved letter today is not the drive saved at setup (the card,
    or another drive, took its letter); None when it is the same drive, when nothing was saved to compare with
    (a Studio File from before Nov 6), or on a Mac. Never a guess: a drive is the same only when its own number
    matches. A drive that is simply not plugged in is left to the preflight, which says so."""
    if not this_computer.WINDOWS:
        return None
    saved, path = d.get(f"{key}_id"), d.get(key)
    letter = _letter(path)
    if not saved or not letter:
        return None
    vols = this_computer.volumes()   # unproven on a real PC
    here = next((v for v in vols if _letter(v["path"]) == letter), None)
    if here and here.get("id") == saved:
        return None
    elsewhere = next((v for v in vols if v.get("id") == saved), None)
    if here is None and elsewhere is None:
        return None
    name = d.get(f"{key}_label") or ("your photo drive" if key == "session" else "your second-copy drive")
    there = f"{name} is {_letter(elsewhere['path'])}: now" if elsewhere else f"{name} isn't plugged in"
    if here:
        try:
            card = (Path(here["path"]) / "DCIM").is_dir()
        except OSError:
            card = False
        now = f"{letter}: is {'the memory card' if card else here.get('name') or 'another drive'} today"
    else:
        now = f"nothing is at {letter}: today"
    return (f"Windows gave your drives different letters today: {there}, and {now}. I won't start until we're sure "
            "where your photos are going.")


def set_drive(d, key, path):
    """Save a drive (or a folder on one) as drives[key]: the one way it is ever written, by `set --drive`,
    `set --second` and the first backup's own choice alike, so a PC's drive facts are always kept beside it.
    False, and nothing changed, when the folder is not there. drive_root: on a PC a bare "E:" means the top of
    drive E (Python alone would read it as wherever it last was on E); on a Mac it is the path as given."""
    root = this_computer.drive_root(path)
    if not root.is_dir():
        return False
    d[key] = str(root.expanduser().resolve())
    keep_drive_facts(d, key)   # a PC: which drive that letter is (its name and number); a Mac: nothing
    return True


# ---------------------------------------------------------------- the first backup chooses by itself

# Dustin, Nov 19: nothing is asked before the copy. The one question that may be asked, once ever, is which
# drive, and only when it cannot be told. These are that question's two shapes, for the assistant to ask.
SHOOTS_ON_COMPUTER = "Shoots"     # the folder made inside Pictures when they choose the computer itself (a draft)


def skipped_lines(skipped):
    out = []
    for x in skipped or ():
        out.append(f"NOT OFFERED: {x['name']}: {x['why']}  (say this in one plain line only if they ask about that drive)")
    return out


def ask_words(state, found=(), skipped=()):
    """What the assistant is told when the drive cannot be chosen: the one question, and the command that
    saves the answer. `state` is "ask-which" (more than one drive) or "ask-none" (no external drive)."""
    if state == "ask-which":
        lines = ["ASK which-drive",
                 "More than one drive is plugged in, so this is the one question, asked once ever:",
                 '  "Which drive should your photos go on?"  One button per drive, by its name and free space, '
                 "the recommended one first:"]
        lines += drive_lines(found)
        lines += skipped_lines(skipped)
        lines += ['Then save it:  studio_file.py defaults --drive "<that drive\'s path>"   and run the backup again. '
                  "Ask nothing else."]
        return lines
    if state == "ask-sure":
        d = found[0]
        return ["ASK is-this-the-drive",
                f"One thing is plugged in besides the card, {d['name']}, and it may be a memory card or a USB stick "
                "rather than a photo drive, so it is not chosen by itself. This is the one question, asked once ever:",
                f'  "Should your photos go on {d["name"]}?"  [Yes, on {d["name"]}]  [No, I\'ll plug my drive in]',
                f'Yes:  studio_file.py defaults --drive "{d["path"]}"   and run the backup again.',
                "No: wait for them to say it is in, then run the backup again. Ask nothing else."]
    here = this_computer.COMPUTER
    if skipped:
        x = skipped[0]
        return ["ASK no-drive",
                f"The only drive plugged in cannot be used today. Say this first, as it is: \"{x['why']}\"",
                "Nothing was saved. Then the one question, asked once ever:",
                f'  "Where should your photos go?"  [I\'ll plug another drive in]  [On this {here} for now]',
                "Plug one in: wait for them to say it is in, then run the backup again.",
                f"On this {here} for now:  studio_file.py defaults --computer   and run the backup again."]
    return ["ASK no-drive",
            "No external drive is plugged in, so this is the one question, asked once ever:",
            f'  "I don\'t see an external drive. Where should your photos go?"  [I\'ll plug one in]  [On this {here} for now]',
            "Plug one in: wait for them to say it is in, then run the backup again.",
            f"On this {here} for now:  studio_file.py defaults --computer   and run the backup again. "
            "No speech about external drives now; the report says one quiet line afterwards."]


def drive_lines(found):
    """The drives as `studio_file.py drives` prints them."""
    out = []
    for d in found:
        tag = "   (recommended: already has shoots on it)" if d["recommended"] and d["has_shoots"] else ("   (recommended)" if d["recommended"] else "")
        out.append(f"{d['path']}   {d['name']}   {d['total_gb']:,} GB, {d['free_gb']:,} GB free{tag}")
        for f in d["shoot_folders"]:
            out.append(f"    shoot folder: {f['name']}   {f['shoots']} folders in there")
    return out


def _same(a, b):
    try:
        return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()
    except OSError:
        return False


def _inside(inner, outer):
    """True when `inner` is `outer` or sits somewhere inside it."""
    try:
        i, o = Path(inner).expanduser().resolve(), Path(outer).expanduser().resolve()
    except OSError:
        return False
    return i == o or o in i.parents


def _where_words(place, found):
    """(the drive's name, where on it in words) for a place: ("Big Kahuna", "in Photo Shoots") or
    ("Big Kahuna", "right on the drive")."""
    for d in found:
        if _same(place, d["path"]):
            return d["name"], "right on the drive"
    for d in found:
        if _inside(place, d["path"]):
            return d["name"], f"in {Path(place).name}"
    drive = this_computer.drive_words(place)
    if drive:
        return drive, ("right on the drive" if len(Path(place).parts) <= 3 else f"in {Path(place).name}")
    return f"this {this_computer.COMPUTER}", f"in {Path(place).name}"


def place_on(drive):
    """Where on a drive shoots go: the drive's one obvious shoot folder when it has one, else right on the
    drive. A folder inside a drive is taken as given. The one place rule, for the first backup's own choice and
    for the report's "Use a different drive next time" alike."""
    root = this_computer.drive_root(drive)
    top = next((x for x in drives() if _same(root, x["path"])), None)
    return sure_place(top) if top else root


def sure_place(row):
    """A drive (a row of drives()) -> the folder on it shoots go in with nobody asked: its one sure shoot folder
    (shoot_folders: named for shoots, with folders in it), else the top of the drive, where they will see it."""
    sure = [f for f in row["shoot_folders"] if f.get("sure")]
    return Path(sure[0]["path"]) if sure else Path(row["path"])


def use_next(drive=None, computer=False):
    """The report's "Use a different drive next time" (Dustin, Nov 19): where the NEXT backup goes. Only the
    Studio File changes; no photo is moved, and the backups already made stay where they are. Returns a dict:
    state "saved" (written), "same" (backups already go on that drive: nothing written), "second" (that drive
    is where second copies go, so it cannot also be the first place: nothing written), or "stop" (`why`).
    With a choice: place, drive (its name), where (in words). Run twice it writes once."""
    sf = load()
    d = sf.setdefault("drives", {})
    now = d.get("session")
    if computer:
        place = this_computer.known_folder("Pictures") / SHOOTS_ON_COMPUTER
        name, where = f"this {this_computer.COMPUTER}", f"in {SHOOTS_ON_COMPUTER}, inside Pictures"
        if now and on_internal_disk(now):
            return {"state": "same", "place": now, "drive": name, "where": where}
    else:
        root = this_computer.drive_root(drive or "")
        if not drive or not root.is_dir():
            return {"state": "stop", "why": "That drive is not plugged in right now."}
        if now and _inside(now, root):
            n, w = _where_words(now, drives())
            return {"state": "same", "place": now, "drive": n, "where": w}
        place = place_on(root)
        name, where = _where_words(place, drives())
        if d.get("second") and (_inside(d["second"], root) or _inside(place, d["second"])):
            return {"state": "second", "place": str(place), "drive": name, "where": where}
        why = cannot_use(place)
        if why:
            return {"state": "stop", "why": why, "cannot": True}
    if computer:
        place.mkdir(parents=True, exist_ok=True)
    if not set_drive(d, "session", place):
        return {"state": "stop", "why": "That drive is not plugged in right now."}
    sf.setdefault("notes", []).append({"on": date.today().isoformat(), "note":
                                       (f"Shoots are kept on this {this_computer.COMPUTER}'s own disk, in {SHOOTS_ON_COMPUTER} inside Pictures; "
                                        "chosen on the report." if computer else
                                        f"Photos go onto {name}, {where}, from now on: chosen on the report.")})
    save(sf)
    return {"state": "saved", "place": d["session"], "drive": name, "where": where}


def set_backup_place(place, source=None, need=None, computer=False):
    """The Back up a card popup's own writer (Nicole's v31; built Nov 23): where backups go from now on is EXACTLY
    the folder picked there, a drive AND a folder on it. Nothing is guessed and nothing is swapped in: not the
    top of the drive (use_next cuts a pick down to it), not the drive's likely shoot folder (place_on). Called
    only when Start the backup is pressed, never while they are still picking.

    Returns {"state": "saved" | "same" | "stop", "place", "why"}. "stop", and nothing written, when the folder is
    not there, is on a memory card, would put the copy on or inside what is being backed up (backup.onto_itself),
    cannot be written to, or has no room for this card (cannot_use). "same": backups already go exactly there.
    computer: they chose the computer itself (no external drive): <Pictures>/Shoots, made if missing.
    It never touches drives.second, and leaves a naming on file alone. Run twice it writes once."""
    if computer:
        folder = this_computer.known_folder("Pictures") / SHOOTS_ON_COMPUTER
    else:
        folder = Path(str(place or "")).expanduser()
        if not place or not folder.is_absolute() or not folder.is_dir():
            return {"state": "stop", "why": "That folder is not there right now."}
    if card_above(folder if folder.is_dir() else folder.parent) is not None:
        return {"state": "stop", "why": "That is a memory card. Photos belong on a drive that never gets formatted."}
    if source:
        if _inside(source, folder) or _inside(folder, source):
            return {"state": "stop", "why": "That is where the photos are coming from. Pick a different place."}
        try:
            import backup
            why = backup.onto_itself(source, folder, "the backup")
        except Exception:  # noqa: BLE001  (the backup itself asks again before it copies a byte)
            why = None
        if why:
            return {"state": "stop", "why": why}
    if computer:
        folder.mkdir(parents=True, exist_ok=True)
    why = cannot_use(folder, need)
    if why:
        return {"state": "stop", "why": why}
    sf = load()
    d = sf.setdefault("drives", {})
    try:
        exact = str(folder.resolve())
    except OSError:
        exact = str(folder)
    n = sf.setdefault("naming", {})
    named = bool(n.get("folder_pattern"))
    if d.get("session") == exact and named:
        return {"state": "same", "place": exact}
    if not set_drive(d, "session", folder):
        return {"state": "stop", "why": "That folder is not there right now."}
    if not named:                            # only when no naming is on file (as the first backup's own choice)
        n.update(OFFERED[0])
        n.pop("example", None)
        n.setdefault("file_names", "shoot")
    sf.setdefault("notes", []).append({"on": date.today().isoformat(), "note":
                                       f"Backups go into {place_words(d['session'])}: picked on the home page."})
    save(sf)
    return {"state": "saved", "place": d["session"]}


def set_offered(n):
    """Save one of the two offered ways of naming shoot folders for every backup from now on (the popup's
    "named Shoot name_Date · Change"; the report's naming option does the same for its own backup). True when
    the Studio File changed; ValueError for anything but 1 or 2. Folders already on a drive are not renamed."""
    if type(n) is not int or not 1 <= n <= len(OFFERED):
        raise ValueError("not one of the offered ways")
    sf = load()
    now, way = sf.setdefault("naming", {}), OFFERED[n - 1]
    if now.get("folder_pattern") == way["folder_pattern"] and now.get("date_format") == way["date_format"]:
        return False
    now.update(way)
    now.pop("example", None)
    now.setdefault("file_names", "shoot")
    save(sf)
    return True


def choose_defaults(drive=None, computer=False, write=True, source=None, need=None):
    """The first backup's setup, done by the Assistant itself (Dustin, Nov 19: zero questions before the copy).
    Returns a dict: state "set" (a drive is already on file: nothing is changed, ever), "set-other" (a drive is
    on file and a DIFFERENT one was named here: nothing changed; changing it is `set --drive`), "chose" (chosen
    and written), "would" (chosen, write=False: nothing written, nothing made), "ask-which" (more than one
    drive and none named: `drives` holds them), "ask-sure" (one drive, and it may be a memory card or a stick),
    "ask-none" (no external drive, or the only one cannot be used today: `skipped` says why), or "stop" (`why`:
    a named place that is not there or cannot be used). With a choice: place (the folder shoots go in), drive
    (its name), where (in words).

    drive: the answer to the one question, a drive's path (its sure shoot folder is used when it has one) or a
    folder inside a drive (taken as given). computer: they chose the computer itself; <Pictures>/Shoots, made
    if missing. source: the card or folder about to be backed up; a drive that holds it is never the choice.
    need: the room the backup needs, in bytes (worked out from source when not given).

    A drive is only ever chosen, and only ever saved, when photos can go on it today: it can be written to and,
    when the card is known, has room for it (cannot_use). Chosen with nobody asked only when it is the one drive
    plugged in. Run twice it writes once. It never touches drives.second, and leaves a naming on file alone."""
    sf = load()
    d = sf.get("drives") or {}
    if d.get("session"):
        name, where = _where_words(d["session"], drives())
        other = False
        if computer:
            other = not on_internal_disk(d["session"])
        elif drive:
            root = this_computer.drive_root(drive)
            other = not (_inside(d["session"], root) or _inside(root, d["session"]))
        return {"state": "set-other" if other else "set", "place": d["session"], "drive": name, "where": where}
    found = drives()
    if source:
        found = [x for x in found if not _inside(source, x["path"])]
        if found and not any(x["recommended"] for x in found):
            found[0]["recommended"] = True
        if need is None and not computer:
            need = room_needed(source)
    note = None
    if computer:
        place = this_computer.known_folder("Pictures") / SHOOTS_ON_COMPUTER
        name, where = f"this {this_computer.COMPUTER}", f"in {SHOOTS_ON_COMPUTER}, inside Pictures"
        note = (f"Shoots are kept on this {this_computer.COMPUTER}'s own disk, in {SHOOTS_ON_COMPUTER} inside Pictures; "
                "said OK on the first backup.")
    elif drive:
        root = this_computer.drive_root(drive)
        if not root.is_dir():
            return {"state": "stop", "why": f"{drive} is not a folder I can see."}
        if card_above(root) is not None:
            return {"state": "stop", "why": "That is a memory card. Photos belong on a drive that never gets formatted."}
        if source and (_inside(source, root) or _inside(root, source)):
            return {"state": "stop", "why": "That is where the photos are coming from. Pick a different drive."}
        place = place_on(root)
        name, where = _where_words(place, drives())
        why = cannot_use(place, need)
        if why:
            return {"state": "stop", "why": why}
    elif len(found) == 1:
        only = found[0]
        place = sure_place(only)
        name, where = _where_words(place, found)
        why = cannot_use(place, need, found)
        if why:
            return {"state": "ask-none", "drives": [], "skipped": [{"name": only["name"], "why": why}]}
        if only.get("maybe_card"):
            return {"state": "ask-sure", "drives": found}
    else:
        skipped = []
        for x in found:
            why = cannot_use(sure_place(x), need, found)
            if why:
                skipped.append({"name": x["name"], "why": why})
        return {"state": "ask-which" if found else "ask-none", "drives": found, "skipped": skipped}
    got = {"state": "chose" if write else "would", "place": str(place), "drive": name, "where": where}
    if not write:
        return got
    if computer:
        place.mkdir(parents=True, exist_ok=True)
    d = sf.setdefault("drives", {})
    if not set_drive(d, "session", place):
        return {"state": "stop", "why": f"{place} is not a folder I can see."}
    got["place"] = d["session"]
    n = sf.setdefault("naming", {})
    if not n.get("folder_pattern"):          # only when no naming is on file
        n.update(OFFERED[0])
        n.pop("example", None)
        n.setdefault("file_names", "shoot")
    sf.setdefault("notes", []).append({"on": date.today().isoformat(), "note": note or
                                       f"Photos go onto {name}, {where}: chosen by itself on the first backup."})
    save(sf)
    return got


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
    out = pat.replace("{date}", this_computer.strftime(when, fmt)).replace("{shoot}", shoot.replace(" ", naming.get("space", " ")))
    out = re.sub(r'[\\/:*?"<>|]+', " ", out).strip(" .")
    return this_computer.unreserved(out)   # "Nul_. Family", not "Nul. Family_" (which Windows still reads as NUL)


def place_words(path):
    """A folder the way a photographer would say it: "Big Kahuna", or "Photo Shoots on Big Kahuna"; a folder on
    the computer itself by its name ("Pictures on this Mac")."""
    if not path:
        return ""
    path = Path(path)
    drive = this_computer.drive_words(path)
    if not drive:
        return f"{path.name or path} on this {this_computer.COMPUTER}"
    here = path.name
    return drive if (not here or here == drive or len(path.parts) <= 3) else f"{here} on {drive}"


def glance(sf=None):
    """The usual, to glance at before a backup (Dustin, Nov 11: from the second backup on, "a quick little list for
    them to glance at so they can see all of the settings up front", then Looks good or Change something).
    (lines, one line): each setting as a short plain line, and all of them in one line for the question itself.
    ([], "") when there is no setup yet."""
    sf = load() if sf is None else sf
    drives_ = (sf or {}).get("drives", {})
    if not drives_.get("session"):
        return [], ""
    naming = sf.get("naming", {})
    lines = [("Photos go onto " + place_words(drives_["session"]), "photos onto " + place_words(drives_["session"]))]
    second = drives_.get("second")
    lines.append(("A second copy goes onto " + place_words(second), "a second copy onto " + place_words(second)) if second
                 else ("No second copy", "no second copy"))
    label = naming.get("label")
    if not label and naming.get("folder_pattern"):
        try:
            label = render(naming, "Smith Family", "2026-10-18T10:00:00")
        except Exception:  # noqa: BLE001
            label = None
    if label:
        lines.append((f"Folders named like \u201c{label}\u201d", f"folders like \u201c{label}\u201d"))
    if naming.get("file_names", "shoot") == "original":
        lines.append(("Photos keep the camera's own names", "photos keep the camera's names"))
    else:
        lines.append(("Photos named after the shoot, with the camera's number kept", "photos named after the shoot"))
    note = sf.get("note") or {}
    if CLIENT_NOTES and note.get("on"):
        how = "the way you write" if note.get("sample") else {"warm": "warm and personal", "plain": "short and plain",
                                                             "playful": "playful"}.get(note.get("tone"), "in your voice")
        sign = " / ".join(x.strip() for x in (note.get("sign_off") or "").splitlines() if x.strip())
        lines.append((f"Client notes written {how}" + (f", signed \u201c{sign}\u201d" if sign else ""), f"client notes {how}"))
    try:   # how often they post, from the posting queue's own record
        import json as _json
        import os as _os
        home = Path(_os.environ.get("STUDIO_HOME", Path.home() / ".studio"))
        per_week = _json.loads((home / "posting.json").read_text(encoding="utf-8")).get("interval")
        if per_week:
            import posting_queue
            words = posting_queue.interval_words(per_week)
            lines.append((f"Posts lined up at {words}", f"posts at {words}"))
    except Exception:  # noqa: BLE001  (no posting record yet, or it cannot be read: the line is simply left out)
        pass
    one = "; ".join(short for _, short in lines)
    return [long for long, _ in lines], one[:1].upper() + one[1:] + "."


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("glance", help="the usual, as short plain lines to glance at before a backup, and as one line for the question")
    sub.add_parser("drives")
    sub.add_parser("cards", help="memory cards in right now: one line each, the path first")
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
    s.add_argument("--name", help='what they call their helper ("Sherman"); every page and message uses it. "" to go back to the product\'s name')
    df = sub.add_parser("defaults", help="the first backup's setup, chosen by itself: the drive, where on it, the naming. Asks nothing")  # pc-ok: our own command's name, not the Mac's `defaults` tool
    df.add_argument("--drive", help="the answer to the one question: the drive (or a folder on one) their photos go on")
    df.add_argument("--computer", action="store_true", help="they chose the computer itself: a Shoots folder inside Pictures")
    df.add_argument("--source", help="the card or folder about to be backed up; a drive that holds it is never chosen")
    df.add_argument("--dry-run", action="store_true", help="say what would be chosen; write nothing")
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
    if a.cmd == "glance":
        lines, one = glance()
        if not lines:
            print("No setup yet. The first 'backup now' sets it up by itself.")
            return
        print("THE USUAL (say these to them, one short line each, exactly as written):")
        for ln in lines:
            print(ln)
        print("ONE LINE (put this in the question itself):")
        print(one)
        return
    if a.cmd == "defaults":
        if a.source:
            # the card is asked whether it answers before anything looks at it (as night.py does): a card that
            # has gone quiet stops here in half a minute, never a silent wait
            import cards
            if not cards.answers(a.source):
                sys.exit(f"STOP: {cards.QUIET_CARD}")
        got = choose_defaults(drive=a.drive, computer=a.computer, write=not a.dry_run, source=a.source)
        if got["state"] == "set":
            print(f"SET: {got['place']} | {got['drive']}")
            print("A drive is already on file. Nothing changed.")
        elif got["state"] == "set-other":
            print(f"SET-OTHER: {got['place']} | {got['drive']}")
            print(f"A different place is already on file ({got['drive']}, {got['where']}), so NOTHING CHANGED and their photos "
                  "would still go there. This command never changes a drive that is on file.")
            print('If they mean this as where their photos go from now on:  studio_file.py set --drive "<path>"')
            print('If it is for this one backup only:  night.py --source "<card>" --dest "<path>"')
            sys.exit(6)
        elif got["state"] in ("chose", "would"):
            print(f"{'CHOSE' if got['state'] == 'chose' else 'WOULD CHOOSE'}: {got['place']} | {got['drive']} | {got['where']}")
            if got["state"] == "would":
                print("Nothing written (dry run).")
        elif got["state"] == "stop":
            sys.exit(f"STOP: {got['why']}")
        else:
            print("\n".join(ask_words(got["state"], got.get("drives", ()), got.get("skipped", ()))))
            sys.exit(4 if got["state"] == "ask-none" else 3)
        return
    if a.cmd == "cards":
        found = this_computer.cards()
        if not found:
            print("No memory card in right now.")
        for c in found:
            print(f"{c['path']}   {c['shown']}")
        return
    if a.cmd == "drives":
        found = drives()
        if not found:
            print(f"No drives plugged in besides the {this_computer.COMPUTER} itself.")
        for ln in drive_lines(found):
            print(ln)
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
    if a.name is not None:
        sf["name"] = " ".join(a.name.split())[:40]
    # drive_root: on a PC a bare "E:" means the top of drive E (Python alone would read it as wherever it last
    # was on E). On a Mac it is the path as given, exactly as before.
    if a.drive and not set_drive(d, "session", a.drive):
        sys.exit(f"STOP: {a.drive} is not a folder I can see.")
    if a.second and not set_drive(d, "second", a.second):
        sys.exit(f"STOP: {a.second} is not a folder I can see.")
    if a.no_second:
        d["second"] = None
        keep_drive_facts(d, "second")
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
